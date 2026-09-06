"""配置校验与城市解析测试。"""
import pytest

from boss_archiver.config import CITY_CODES, Settings, resolve_city_code
from boss_archiver.errors import UsageError


def test_resolve_by_name_and_code():
    assert resolve_city_code("杭州") == "101210100"
    assert resolve_city_code("杭州市") == "101210100"
    assert resolve_city_code("101210100") == "101210100"
    assert resolve_city_code(" 杭州 ") == "101210100"


def test_resolve_unknown_city_lists_usage():
    with pytest.raises(UsageError) as exc:
        resolve_city_code("不存在的城市")
    assert "--list-cities" in str(exc.value)
    with pytest.raises(UsageError):
        resolve_city_code("")


def test_settings_pages_bounds():
    good = Settings(pages=4)
    good.validate()
    for bad in (0, 5, -1):
        with pytest.raises(UsageError):
            Settings(pages=bad).validate()


def test_settings_detail_defaults_and_budget():
    settings = Settings()
    assert settings.fetch_details is False  # 保守默认：只导列表
    assert settings.max_details_per_run == 10
    Settings(max_details_per_run=1).validate()
    for bad in (0, -1):
        with pytest.raises(UsageError):
            Settings(max_details_per_run=bad).validate()


def test_settings_interval_guard():
    with pytest.raises(UsageError):
        Settings(min_page_interval_s=0.1).validate()
    with pytest.raises(UsageError):
        Settings(min_detail_interval_s=0.1).validate()


def test_settings_trims_query_and_validates_city():
    settings = Settings(city="杭州", query="  Java开发  ")
    settings.validate()
    assert settings.query == "Java开发"


def test_filter_choices_validation():
    Settings(job_type="全职").validate()
    Settings(salary="10-20K").validate()
    Settings(experience="3-5年", degree="本科").validate()
    for bad in (("job_type", "非全职"), ("salary", "100K"),
                ("experience", "随便"), ("degree", "博士后")):
        with pytest.raises(UsageError):
            Settings(**{bad[0]: bad[1]}).validate()


def test_filter_pairs_order():
    s = Settings(job_type="全职", salary="10-20K", experience="3-5年", degree="本科")
    assert s.filter_pairs() == [
        ("jobType", "全职"), ("salary", "10-20K"), ("exp", "3-5年"), ("degree", "本科"),
    ]
    assert Settings().filter_pairs() == []
    assert Settings().has_filters() is False
    assert s.has_filters() is True


def test_filter_params_missing():
    from boss_archiver.config import filter_params_missing

    filters = [("jobType", "全职"), ("salary", "10-20K"), ("exp", "3-5年"), ("degree", "本科")]
    url = "https://www.zhipin.com/web/geek/jobs?city=1&jobType=1901&salary=405&experience=105&degree=203&query=x"
    assert filter_params_missing(filters, url) == []
    assert filter_params_missing(filters, "https://www.zhipin.com/web/geek/jobs?city=1") == [
        "jobType", "salary", "exp", "degree",
    ]
    # exp 的别名兜底
    assert filter_params_missing([("exp", "3-5年")], "https://x/?exp=105") == []


def test_list_url_contains_city_and_query():
    settings = Settings(city="杭州", query="Java开发")
    url = settings.list_url()
    assert "city=101210100" in url
    assert "query=Java%E5%BC%80%E5%8F%91" in url


def test_city_table_contains_hangzhou():
    assert CITY_CODES["杭州"] == "101210100"
