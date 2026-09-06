"""合成测试数据：模拟 BOSS 直聘列表接口的 JSON 结构（全部为虚构职位，非真实数据）。"""


def job(**overrides):
    base = {
        "jobName": "示例职位",
        "salaryDesc": "15-20K",
        "jobDegree": "本科",
        "jobExperience": "3-5年",
        "brandName": "示例公司",
        "cityName": "杭州",
        "areaDistrict": "西湖区",
        "businessDistrict": "文三路",
        "encryptJobId": "J0001",
    }
    base.update(overrides)
    return base


def payload(jobs, code=0):
    return {"code": code, "zpData": {"jobList": jobs}}


def fulltime_job(overrides=None):
    data = job() if not overrides else job(**overrides)
    return data


def intern_job(overrides=None):
    fields = {"jobExperience": "", "daysPerWeekDesc": "5天/周", "leastMonthDesc": "6个月"}
    if overrides:
        fields.update(overrides)
    return job(**fields)


def nested_brand_job():
    data = job(encryptJobId="J0002")
    data.pop("brandName")  # 只保留嵌套位置，验证 $..brandName 递归兜底
    data["brand"] = {"brandName": "嵌套品牌公司"}
    return data


def no_salary_job():
    data = job(encryptJobId="J0003")
    data.pop("salaryDesc")
    return data
