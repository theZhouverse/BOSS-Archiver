"""领域模型（纯数据，无 I/O）：一条职位记录。

字段语义权威位置：本文件 + parsing.py 的解析映射；docs/SPEC.md 只引用不复制。
"""
from __future__ import annotations

from dataclasses import dataclass

JOB_DETAIL_URL = "https://www.zhipin.com/job_detail/{job_id}.html"

CSV_HEADERS = [
    "工作名称",
    "薪资待遇",
    "学历要求",
    "全职/实习要求",
    "企业名称",
    "地址",
    "职位描述",
    "职位链接",
]


@dataclass
class Job:
    """BOSS 直聘职位列表中的一条记录。"""

    name: str = ""
    salary: str = ""
    degree: str = ""
    requirement: str = ""  # 如「全职，要求3-5年」/「实习，5天/周，6个月」
    company: str = ""
    city: str = ""
    district: str = ""
    business_district: str = ""
    job_id: str = ""  # 列表接口的 encryptJobId，详情页链接依据
    description: str = ""

    @property
    def address(self) -> str:
        return "-".join(x for x in (self.city, self.district, self.business_district) if x)

    @property
    def link(self) -> str:
        return JOB_DETAIL_URL.format(job_id=self.job_id) if self.job_id else ""

    def to_row(self) -> list[str]:
        return [
            self.name,
            self.salary,
            self.degree,
            self.requirement,
            self.company,
            self.address,
            self.description,
            self.link,
        ]

    def dedupe_key(self) -> str:
        """去重键：优先职位 ID；无 ID 时退化为 公司|名称。"""
        return self.job_id or f"{self.company}|{self.name}"


def dedupe_jobs(jobs: list[Job]) -> list[Job]:
    """按 dedupe_key 稳定去重，保留首次出现顺序。"""
    seen: set[str] = set()
    result: list[Job] = []
    for job in jobs:
        key = job.dedupe_key()
        if key in seen:
            continue
        seen.add(key)
        result.append(job)
    return result
