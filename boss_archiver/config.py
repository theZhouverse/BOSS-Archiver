"""配置与常量（Settings Schema 是配置的唯一权威位置，规范 §12.1）。

运行参数由 cli.py 解析后构造 Settings；校验失败抛 UsageError。
"""
from __future__ import annotations

import urllib.parse
from dataclasses import dataclass
from pathlib import Path

from .errors import UsageError

# ---- 站点常量 ----
BASE_URL = "https://www.zhipin.com"
LOGIN_URL = BASE_URL + "/web/user/?ka=header-login"
JOB_LIST_URL = BASE_URL + "/web/geek/job"
JOB_DETAIL_URL_TPL = BASE_URL + "/job_detail/{job_id}.html"
# 网络监听关键词：命中该 URL 片段的响应会被捕获（与页面懒加载接口一致）
JOBLIST_LISTENER_KEYWORD = "joblist"

# 常用城市码表（据公开资料整理；个别城市码可能随平台调整，
# 以浏览器地址栏 ?city= 实际值为准。可用 --list-cities 查看本表）
CITY_CODES: dict[str, str] = {
    "北京": "101010100",
    "上海": "101020100",
    "天津": "101030100",
    "重庆": "101040100",
    "哈尔滨": "101050100",
    "长春": "101060100",
    "沈阳": "101070100",
    "大连": "101070200",
    "石家庄": "101090100",
    "太原": "101100100",
    "西安": "101110100",
    "济南": "101120100",
    "青岛": "101120200",
    "乌鲁木齐": "101130100",
    "西宁": "101150100",
    "兰州": "101160100",
    "银川": "101170100",
    "郑州": "101180100",
    "南京": "101190100",
    "无锡": "101190200",
    "苏州": "101190400",
    "常州": "101191100",
    "南通": "101190500",
    "武汉": "101200100",
    "杭州": "101210100",
    "宁波": "101210400",
    "温州": "101210300",
    "合肥": "101220100",
    "福州": "101230100",
    "厦门": "101230200",
    "南昌": "101240100",
    "长沙": "101250100",
    "贵阳": "101260100",
    "成都": "101270100",
    "广州": "101280100",
    "深圳": "101280600",
    "珠海": "101280700",
    "佛山": "101280800",
    "惠州": "101280300",
    "东莞": "101281600",
    "中山": "101281700",
    "南宁": "101300100",
    "海口": "101310100",
    "昆明": "101290100",
}


def resolve_city_code(value: str) -> str:
    """城市入参解析：支持城市名（自动去掉「市」后缀）或数字 code。"""
    text = (value or "").strip()
    if not text:
        raise UsageError("城市不能为空，示例：--city 杭州 或 --city 101210100")
    if text.isdigit():
        return text
    name = text[:-1] if text.endswith("市") else text
    code = CITY_CODES.get(name)
    if code is None:
        sample = "、".join(list(CITY_CODES)[:12])
        raise UsageError(f"未收录城市「{value}」。可用 --list-cities 查看内置城市，或直接传城市 code（如 101210100）；本表外的城市请以浏览器地址栏 ?city= 为准")
    return code


@dataclass
class Settings:
    """运行配置。validate() 必须在使用前调用。"""

    # 检索条件
    city: str = "杭州"
    query: str = ""
    # 采集控制
    pages: int = 2  # 期望页数，1 <= pages <= max_pages
    fetch_details: bool = False  # 默认只导列表；职位描述需 --detail 显式开启
    refine_filters: bool = True  # 抓取前暂停，允许人工微调页面筛选条件
    # 风控节拍（保守默认值，2026-09-07 经用户确认收敛；下调需人工批准，见 AGENTS.md）
    min_page_interval_s: float = 4.0
    page_interval_jitter_s: float = 2.0
    min_detail_interval_s: float = 3.0
    detail_interval_jitter_s: float = 2.0
    max_pages: int = 4  # 页数硬上限（防呆兜底）
    max_details_per_run: int = 10  # 单轮详情抓取次数上限（成功+失败，保守）
    # 浏览器与输出
    profile_dir: Path = Path(".runtime") / "browser_profile"
    out_dir: Path = Path("out")
    output_path: Path | None = None
    headless: bool = False
    verbose: bool = False
    login_timeout_s: float = 180.0

    def validate(self) -> None:
        if not isinstance(self.pages, int) or not (1 <= self.pages <= self.max_pages):
            raise UsageError(f"页数需为 1~{self.max_pages} 的整数，收到：{self.pages!r}")
        if not isinstance(self.max_details_per_run, int) or self.max_details_per_run < 1:
            raise UsageError(f"单轮详情次数上限需为 >=1 的整数，收到：{self.max_details_per_run!r}")
        if self.min_page_interval_s < 0.5 or self.min_detail_interval_s < 0.3:
            raise UsageError("节拍间隔低于护栏下限（翻页 >=0.5s、详情 >=0.3s），不允许")
        self.query = (self.query or "").strip()
        # 尽早暴露城市问题
        resolve_city_code(self.city)

    def city_code(self) -> str:
        return resolve_city_code(self.city)

    def list_url(self) -> str:
        """职位列表页 URL（城市 + 关键词）。"""
        url = f"{JOB_LIST_URL}?city={self.city_code()}"
        if self.query:
            url += "&query=" + urllib.parse.quote(self.query)
        return url
