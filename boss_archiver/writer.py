"""CSV 写出（UTF-8-SIG，Excel 直接打开不乱码）。"""
from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path

from .models import CSV_HEADERS, Job

_INVALID_FILENAME_CHARS = '<>:"/\\|?*'


def sanitize_filename(text: str, placeholder: str = "_") -> str:
    """去掉文件名非法字符与首尾空白，用于拼接输出文件名。"""
    cleaned = "".join(placeholder if ch in _INVALID_FILENAME_CHARS else ch for ch in text)
    return cleaned.strip() or "全部职位"


def default_output_path(out_dir: Path, city: str, query: str) -> Path:
    """默认输出：out/boss直聘_{城市}_{关键词}_{时间戳}.csv"""
    query_part = sanitize_filename(query) if query else "全部职位"
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return out_dir / f"boss直聘_{sanitize_filename(city)}_{query_part}_{stamp}.csv"


def write_csv(jobs: list[Job], path: Path) -> int:
    """写 CSV（utf-8-sig），返回写入行数；父目录不存在时自动创建。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(CSV_HEADERS)
        for job in jobs:
            writer.writerow(job.to_row())
    return len(jobs)
