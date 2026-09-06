"""响应解析（纯函数，无 I/O，可单测）。

把 BOSS 直聘职位列表接口的 JSON 响应解析为 Job 列表。
解析映射是本模块的事实主体；接口字段命名差异用多路径兜底。
"""
from __future__ import annotations

from typing import Any

from jsonpath import jsonpath

from .models import Job


def is_success(payload: Any) -> bool:
    """接口业务成功：code == 0。非 dict（HTML/异常体）一律视为失败。"""
    return isinstance(payload, dict) and payload.get("code") == 0


def _find(node: Any, *paths: str) -> Any:
    """按多个 JSONPath 依次取值，返回第一个命中值；未命中返回空串。"""
    for path in paths:
        try:
            result = jsonpath(node, path)
        except Exception:
            result = None
        if result:
            return result[0]
    return ""


def _raw_list(payload: dict) -> list:
    for path in ("$.zpData.jobList", "$.zpData.joblist", "$..jobList", "$..joblist"):
        result = jsonpath(payload, path)
        if result:
            value = result[0]
            if isinstance(value, list):
                return value
    return []


def _text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _requirement(item: dict) -> str:
    """全职/实习判定：有经验字段按全职；否则同时有每周天数+最少月数判为实习。"""
    experience = _text(_find(item, "$..jobExperience"))
    if experience:
        return f"全职，要求{experience}"
    days = _text(_find(item, "$..daysPerWeekDesc"))
    months = _text(_find(item, "$..leastMonthDesc"))
    if days and months:
        return f"实习，{days}，{months}"
    return "无明确要求"


def extract_jobs(payload: Any) -> list[Job]:
    """从接口响应提取职位列表；响应非成功或无职位数据时返回空列表。"""
    if not is_success(payload):
        return []
    jobs: list[Job] = []
    for item in _raw_list(payload):
        if not isinstance(item, dict):
            continue
        name = _text(_find(item, "$..jobName", "$..job_name"))
        if not name:
            continue  # 该节点不是职位项
        jobs.append(
            Job(
                name=name,
                salary=_text(_find(item, "$..salaryDesc", "$..salary_desc")),
                degree=_text(_find(item, "$..jobDegree")),
                requirement=_requirement(item),
                company=_text(_find(item, "$..brandName", "$..brand.name")),
                city=_text(_find(item, "$..cityName", "$..cityname")),
                district=_text(_find(item, "$..areaDistrict")),
                business_district=_text(_find(item, "$..businessDistrict")),
                job_id=_text(_find(item, "$..encryptJobId", "$..jobId")),
            )
        )
    return jobs
