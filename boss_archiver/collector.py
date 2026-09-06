"""用例编排：检索 → 自动分页 → 详情抓取 → 结果统计。

属于应用层：只依赖 domain（models/parsing/pacing/risk）与 browser 适配器的公开方法，
不直接 import DrissionPage（SPEC §4.3）。
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field

from .browser import BrowserSession
from .config import Settings
from .errors import ChallengeError, CollectorError, LoginError
from .models import Job, dedupe_jobs
from .pacing import PacingPolicy
from .parsing import extract_jobs
from .risk import STATE_CHALLENGE, STATE_LOGIN, classify_page, describe

logger = logging.getLogger(__name__)


@dataclass
class CollectorResult:
    jobs: list[Job] = field(default_factory=list)
    pages_fetched: int = 0
    detail_fetched: int = 0
    detail_failures: int = 0


class Collector:
    """一次检索归档任务的编排入口。"""

    def __init__(self, settings: Settings):
        settings.validate()
        self.settings = settings
        self.page_pacer = PacingPolicy(
            settings.min_page_interval_s, settings.page_interval_jitter_s
        )
        self.detail_pacer = PacingPolicy(
            settings.min_detail_interval_s, settings.detail_interval_jitter_s
        )

    # ---- 对外入口 ----
    def run(self) -> CollectorResult:
        with BrowserSession(self.settings) as browser:
            browser.ensure_login()
            return self._collect(browser)

    # ---- 内部 ----
    def _assert_safe(self, browser: BrowserSession) -> None:
        """风险熔断：验证码/安全校验立即停；登录失效给出明确提示。"""
        state = classify_page(browser.url, browser.title)
        if state == STATE_CHALLENGE:
            raise ChallengeError(describe(state))
        if state == STATE_LOGIN:
            raise LoginError(describe(state))

    def _next_payload(self, browser: BrowserSession, timeout_s: float):
        """等待窗口期内第一个含职位数据的成功响应；返回 (payload, jobs)。"""
        for body in browser.iter_joblist_responses(timeout_s):
            jobs = extract_jobs(body)
            if jobs:
                return body, jobs
        return None, []

    def _collect(self, browser: BrowserSession) -> CollectorResult:
        s = self.settings
        browser.start_listening()

        # ---- 首屏与（可选的）人工筛选 ----
        logger.info("打开检索页：%s", s.list_url())
        browser.goto_job_list()
        if s.refine_filters:
            browser.trigger_search(s.query)
            if not browser.wait_filter_bar(3.0):
                logger.warning("未等到筛选栏（css:.search-condition），继续尝试抓取…")
            print(">>> 请在浏览器中按需微调筛选条件（薪资/学历/城市等），确认后回到控制台按回车开始抓取…")
            try:
                input()
            except EOFError:
                pass
            browser.trigger_search(s.query)
            payload, first_jobs = self._next_payload(browser, timeout_s=12.0)
        else:
            payload, first_jobs = self._next_payload(browser, timeout_s=8.0)
            if payload is None:
                logger.info("首屏未捕获职位数据，强制触发一次搜索…")
                browser.trigger_search(s.query)
                payload, first_jobs = self._next_payload(browser, timeout_s=12.0)
        if payload is None:
            raise CollectorError(
                "未捕获到职位数据：请确认已扫码登录、城市与关键词正确；"
                "若刚触发过安全校验请稍后再试并降低 --pages"
            )

        # ---- 分页收集（含去重） ----
        collected: dict[str, Job] = {}
        for job in first_jobs:
            collected[job.dedupe_key()] = job
        pages_fetched = 1
        logger.info("第 1 页完成，累计 %d 条", len(collected))

        while pages_fetched < s.pages:
            self._assert_safe(browser)
            self.page_pacer.wait()
            browser.scroll_bottom()
            _, new_jobs = self._next_payload(browser, timeout_s=5.0)
            if not new_jobs:
                self.page_pacer.wait()  # 节拍后重试一次
                browser.scroll_bottom()
                _, new_jobs = self._next_payload(browser, timeout_s=5.0)
            if not new_jobs:
                logger.info("未捕获到新一页数据（可能已到末页或被限流），停止翻页")
                break
            before = len(collected)
            for job in new_jobs:
                collected[job.dedupe_key()] = job
            pages_fetched += 1
            added = len(collected) - before
            logger.info("第 %d 页完成，新增 %d 条（累计 %d）", pages_fetched, added, len(collected))
            if added == 0:
                logger.info("新页数据与已收集内容完全重复，停止翻页")
                break

        jobs = dedupe_jobs(list(collected.values()))

        # ---- 详情抓取（默认关闭；开启时串行 + 节拍 + 单轮上限） ----
        detail_fetched = 0
        detail_failures = 0
        if s.fetch_details:
            budget = s.max_details_per_run
            logger.info(
                "开始抓取职位描述：串行、间隔 >=%.1fs、单轮上限 %d 次",
                s.min_detail_interval_s, budget,
            )
            for job in jobs:
                if not job.job_id:
                    continue
                if detail_fetched + detail_failures >= budget:
                    logger.info("已达单轮详情上限 %d 次，停止详情抓取", budget)
                    break
                self._assert_safe(browser)
                self.detail_pacer.wait()
                try:
                    job.description = browser.fetch_job_detail(job.job_id)
                    detail_fetched += 1
                except ChallengeError:
                    raise
                except Exception as exc:
                    detail_failures += 1
                    logger.warning("详情抓取失败（%s）：%s", job.name or job.job_id, exc)
                if (detail_fetched + detail_failures) % 5 == 0:
                    logger.info("详情进度：成功 %d，失败 %d", detail_fetched, detail_failures)
            logger.info("详情抓取结束：成功 %d，失败 %d", detail_fetched, detail_failures)

        return CollectorResult(
            jobs=jobs,
            pages_fetched=pages_fetched,
            detail_fetched=detail_fetched,
            detail_failures=detail_failures,
        )
