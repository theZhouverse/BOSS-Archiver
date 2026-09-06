"""parsing / models 的纯逻辑测试。"""
from boss_archiver.models import Job, dedupe_jobs
from boss_archiver.parsing import extract_jobs, is_success

from samples import fulltime_job, intern_job, nested_brand_job, no_salary_job, payload


def test_is_success_only_dict_code0():
    assert is_success(payload([])) is True
    assert is_success(payload([], code=10001)) is False
    assert is_success("html string") is False
    assert is_success(None) is False


def test_extract_fulltime_fields():
    jobs = extract_jobs(payload([fulltime_job()]))
    assert len(jobs) == 1
    job = jobs[0]
    assert job.name == "示例职位"
    assert job.salary == "15-20K"
    assert job.degree == "本科"
    assert job.requirement == "全职，要求3-5年"
    assert job.company == "示例公司"
    assert job.address == "杭州-西湖区-文三路"
    assert job.job_id == "J0001"
    assert job.link == "https://www.zhipin.com/job_detail/J0001.html"
    assert job.description == ""


def test_extract_intern_requirement():
    jobs = extract_jobs(payload([intern_job()]))
    assert jobs[0].requirement == "实习，5天/周，6个月"


def test_extract_nested_brand_and_missing_salary():
    jobs = extract_jobs(payload([nested_brand_job(), no_salary_job()]))
    assert len(jobs) == 2
    assert jobs[0].company == "嵌套品牌公司"
    assert jobs[1].salary == ""


def test_skip_non_job_nodes_and_failures():
    assert extract_jobs(payload([{"somethingElse": 1}])) == []
    assert extract_jobs(payload([])) == []
    assert extract_jobs(payload([fulltime_job()], code=403)) == []
    assert extract_jobs({"zpData": {}}) == []
    assert extract_jobs("not a dict") == []


def test_dedupe_jobs():
    a = Job(name="职位A", company="公司X", job_id="ID1")
    dup = Job(name="职位A", company="公司X", job_id="ID1")
    b = Job(name="职位B", company="公司Y", job_id="ID2")
    no_id_a = Job(name="职位C", company="公司Z", job_id="")
    no_id_b = Job(name="职位C", company="公司Z", job_id="")
    result = dedupe_jobs([a, dup, b, no_id_a, no_id_b])
    assert [j.job_id for j in result] == ["ID1", "ID2", ""]
    assert len(result) == 3
