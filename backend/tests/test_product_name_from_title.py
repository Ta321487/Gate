"""product_name_from_title：窄栏友好的短产品名。"""

from app.bake.schema.shells import product_name_from_title


def test_empty_falls_back():
    assert product_name_from_title("") == "业务系统"
    assert product_name_from_title("   ") == "业务系统"


def test_design_suffix_extracts_core():
    assert (
        product_name_from_title("基于 Spring Boot 的高校宿舍归寝签到管理系统的设计与实现")
        == "高校宿舍归寝签到"
    )


def test_strips_generic_system_suffix_when_long():
    assert product_name_from_title("高校宿舍归寝签到管理系统") == "高校宿舍归寝签到"
    assert product_name_from_title("校医院门诊挂号预约系统") == "校医院门诊挂号预约"


def test_keeps_short_names_intact():
    assert product_name_from_title("校园招聘") == "校园招聘"
    assert product_name_from_title("宿舍报修") == "宿舍报修"


def test_caps_extremely_long_core():
    long = "一二三四五六七八九十一二三四五六七八九十系统"
    out = product_name_from_title(long)
    assert len(out) <= 18
    assert "系统" not in out or len(out) <= 10
