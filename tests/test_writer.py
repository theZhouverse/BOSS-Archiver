"""CSV 写出测试。"""
import csv
from pathlib import Path

from boss_archiver.models import CSV_HEADERS, Job
from boss_archiver.writer import default_output_path, sanitize_filename, write_csv


def _two_jobs():
    return [
        Job(name="职位A", salary="15-20K", degree="本科", requirement="全职，要求3-5年",
            company="甲公司", city="杭州", district="西湖区", business_district="文三路",
            job_id="ID1", description="岗位职责描述"),
        Job(name="职位B", job_id="ID2"),
    ]


def test_sanitize_filename():
    assert sanitize_filename('a<b>:c') == "a_b__c"
    assert sanitize_filename("") == "全部职位"
    assert sanitize_filename("   ") == "全部职位"


def test_default_output_path_pattern():
    path = default_output_path(Path("out"), "杭州", "Java开发")
    assert path.parent == Path("out")
    assert "杭州" in path.name and "Java开发" in path.name
    assert path.suffix == ".csv"


def test_write_csv_roundtrip(tmp_path):
    target = tmp_path / "子目录" / "result.csv"
    count = write_csv(_two_jobs(), target)
    assert count == 2
    with target.open("r", encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.reader(fh))
    assert rows[0] == CSV_HEADERS
    assert len(rows) == 3
    assert rows[1][0] == "职位A"
    assert rows[1][6] == "岗位职责描述"
    assert rows[1][7] == "https://www.zhipin.com/job_detail/ID1.html"
    assert rows[2][7] == "https://www.zhipin.com/job_detail/ID2.html"
