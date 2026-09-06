"""浏览器适配器：DrissionPage 启动、登录态、页面操作原语。

依赖方向（SPEC §4.3）：adapter 依赖 config/domain；其余模块不得 import DrissionPage。
浏览器用户数据目录默认 .runtime/browser_profile，扫码一次后登录态长期复用（SPEC D4）。
"""
from __future__ import annotations

import json
import logging
import time

from DrissionPage import ChromiumOptions, ChromiumPage

from .config import (
    FILTER_FIELD_TO_CATEGORY,
    JOB_DETAIL_URL_TPL,
    JOBLIST_LISTENER_KEYWORD,
    LOGIN_URL,
    Settings,
)
from .errors import ChallengeError, LoginError
from .risk import STATE_CHALLENGE, STATE_LOGIN, classify_page, describe

logger = logging.getLogger(__name__)

# 登录态标志 Cookie（存在即视为已登录）
LOGIN_COOKIE_NAMES = {"wt2", "__zp_stoken__"}

# 搜索触发脚本：优先点搜索按钮，其次对输入框派发回车。
# __QUERY__ 占位符会被替换为 JSON 字面量（仅当非空时写入搜索框）。
SEARCH_JS = r"""
(function () {
    var q = __QUERY__;
    var input = document.querySelector('input[name="query"]')
        || document.querySelector('.ipt-search')
        || document.querySelector('input[placeholder*="搜索"]');
    if (q && input) {
        input.value = q;
        input.dispatchEvent(new Event('input', { bubbles: true }));
    }
    var btn = document.querySelector('.search-btn')
        || document.querySelector('.btn-search')
        || document.querySelector('button[type="submit"]')
        || document.querySelector('.search-form button');
    if (btn) { btn.click(); return; }
    if (input) {
        input.dispatchEvent(new KeyboardEvent('keydown', {
            key: 'Enter', code: 'Enter', keyCode: 13, which: 13, bubbles: true
        }));
    }
})();
"""


class BrowserSession:
    """持有 ChromiumPage，提供采集所需的浏览器原语。"""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.page: ChromiumPage | None = None

    # ---- 生命周期 ----
    def start(self) -> "BrowserSession":
        settings = self.settings
        options = ChromiumOptions()
        options.set_argument("--start-maximized")
        if settings.headless:
            options.set_argument("--headless=new")
        settings.profile_dir.parent.mkdir(parents=True, exist_ok=True)
        if hasattr(options, "set_user_data_path"):
            options.set_user_data_path(str(settings.profile_dir))
        else:
            options.set_argument(f"--user-data-dir={settings.profile_dir}")
        self.page = ChromiumPage(options)
        logger.info("浏览器已启动（用户数据目录：%s）", settings.profile_dir)
        return self

    def stop(self) -> None:
        page, self.page = self.page, None
        if page is not None:
            try:
                page.quit()
            except Exception as exc:  # 关闭失败不掩盖主流程结果
                logger.debug("浏览器退出异常（忽略）：%s", exc)

    def __enter__(self) -> "BrowserSession":
        return self.start()

    def __exit__(self, *exc_info) -> None:
        self.stop()

    # ---- 只读视图 ----
    @property
    def url(self) -> str:
        return self.page.url if self.page is not None else ""

    @property
    def title(self) -> str:
        return self.page.title if self.page is not None else ""

    # ---- 登录 ----
    def _login_cookies_present(self) -> bool:
        """存在平台登录标志 Cookie 即视为已登录（API 异常时保守返回 False）。"""
        try:
            names = set()
            for cookie in self.page.cookies():
                if isinstance(cookie, dict):
                    name = cookie.get("name")
                else:
                    name = getattr(cookie, "name", None)
                if name:
                    names.add(str(name))
            return bool(names & LOGIN_COOKIE_NAMES)
        except Exception as exc:
            logger.debug("读取 Cookie 失败：%s", exc)
            return False

    def ensure_login(self) -> None:
        """登录态有效直接返回；否则打开登录页等待人工扫码（最长 login_timeout_s）。

        先加载一次职位列表页让 profile 内 Cookie 就绪，避免浏览器刚启动
        （尚未加载任何同域页面）时把“已登录”误判为“未登录”而多走一次登录页。
        """
        page = self.page
        if page is None:
            raise LoginError("浏览器尚未启动")
        page.get(self.settings.list_url())
        if self._login_cookies_present():
            logger.info("登录态有效，直接复用")
            return
        logger.warning("未检测到登录态，打开登录页等待扫码…")
        page.get(LOGIN_URL)
        deadline = time.monotonic() + self.settings.login_timeout_s
        prompted = False
        while time.monotonic() < deadline:
            state = classify_page(page.url, page.title)
            if state == STATE_CHALLENGE:
                raise ChallengeError("登录过程出现安全校验，请手动完成后重试（不做自动绕过）")
            if self._login_cookies_present() or state not in (STATE_LOGIN,):
                logger.info("登录成功（Cookie=%s state=%s）", self._login_cookies_present(), state)
                return
            if not prompted:
                print(f">>> 请在浏览器窗口扫码登录（最长等待 {self.settings.login_timeout_s:.0f} 秒）…")
                prompted = True
            time.sleep(2)
        raise LoginError("登录超时：请在弹出浏览器中完成扫码后重新运行")

    # ---- 采集原语 ----
    def start_listening(self) -> None:
        self.page.listen.start(JOBLIST_LISTENER_KEYWORD)

    def restart_listener(self) -> None:
        """重启监听以丢弃旧缓冲响应：筛选条件变化后必须调用，否则会捕获到旧请求。"""
        try:
            self.page.listen.stop()
        except Exception as exc:
            logger.debug("停止监听异常（忽略）：%s", exc)
        self.page.listen.start(JOBLIST_LISTENER_KEYWORD)

    def goto_job_list(self) -> None:
        self.page.get(self.settings.list_url())

    def goto_url(self, url: str) -> None:
        self.page.get(url)

    def trigger_search(self, query: str = "") -> None:
        """在检索页执行搜索：填充关键词并点击搜索（query 为空则只点击）。"""
        literal = json.dumps(query or "")
        script = SEARCH_JS.replace("__QUERY__", literal)
        self.page.run_js(script)

    def scroll_bottom(self) -> None:
        """滚动到底部，触发列表懒加载分页请求。"""
        self.page.run_js("window.scrollTo(0, document.body.scrollHeight);")

    def iter_joblist_responses(self, timeout_s: float):
        """在窗口期内产出业务成功（code==0）的监听响应体；异常时安全结束。"""
        if self.page is None:
            return
        try:
            for data in self.page.listen.steps(timeout=timeout_s):
                body = data.response.body
                if isinstance(body, dict) and body.get("code") == 0:
                    yield body
        except Exception as exc:
            logger.debug("监听窗口结束：%s", exc)

    # ---- 自动筛选（替代人工微调步骤） ----
    def ensure_filter_bar(self, timeout_s: float = 15.0) -> bool:
        """等待筛选下拉（.condition-filter-select）渲染；不存在返回 False。"""
        try:
            self.page.wait.ele_displayed("css:.condition-filter-select", timeout=timeout_s)
            return True
        except Exception:
            return False

    def _filter_blocks(self) -> list:
        """当前渲染的筛选块（优先可见块）。"""
        try:
            blocks = self.page.eles("css:.condition-filter-select", timeout=2)
        except Exception:
            return []
        visible: list = []
        for block in blocks:
            try:
                if block.states.is_displayed:
                    visible.append(block)
            except Exception:
                visible.append(block)
        return visible or list(blocks)

    def select_filter(self, field: str, label: str) -> bool:
        """在筛选面板点击选项（li[ka="sel-job-rec-{field}-{code}"] + 页面文本）。

        生效确认不在本层：由 collector 通过 URL 参数（filter_params_in_url）校验。
        """
        prefix = f"sel-job-rec-{field}-"
        category = FILTER_FIELD_TO_CATEGORY.get(field, field)
        available: list[str] = []
        for block in self._filter_blocks():
            try:
                options = block.eles("css:.filter-select-dropdown li", timeout=3)
            except Exception:
                options = []
            for option in options:
                ka = ""
                try:
                    ka = option.attr("ka") or ""
                except Exception:
                    pass
                if not ka.startswith(prefix):
                    continue
                try:
                    text = (option.text or "").strip()
                except Exception:
                    text = ""
                available.append(text)
                if text != label:
                    continue
                # 展开类别下拉后再点击选项
                try:
                    head = block.ele("css:.current-select", timeout=1)
                    if head is not None and label not in (head.text or ""):
                        head.click()
                        time.sleep(0.8)
                except Exception:
                    pass
                try:
                    option.click()
                except Exception as exc:
                    logger.debug("筛选选项点击失败：%s", exc)
                    return False
                logger.info("筛选「%s」= %s 已点击", category, label)
                return True
        logger.warning("筛选类别「%s」未找到选项「%s」，现有：%s", category, label, "、".join(available))
        return False

    def fetch_job_detail(self, job_id: str) -> str:
        """新开标签页抓职位描述，读取后关闭；描述缺失返回空串。

        触发安全校验时抛 ChallengeError（熔断由上层处理）。
        """
        tab = None
        try:
            tab = self.page.new_tab(JOB_DETAIL_URL_TPL.format(job_id=job_id))
            if classify_page(tab.url, tab.title) == STATE_CHALLENGE:
                raise ChallengeError("打开职位详情页时检测到安全校验，已熔断停止")
            try:
                tab.wait.ele_displayed("css:.job-sec-text", timeout=2.5)
            except Exception:
                pass
            try:
                element = tab.ele("css:.job-sec-text", timeout=0.5) or tab.ele("css:.job-detail", timeout=0.5)
            except Exception:
                element = None
            if element is None:
                return ""
            return element.text.replace("\n", " ").strip()
        finally:
            if tab is not None:
                try:
                    tab.close()
                except Exception:
                    pass
