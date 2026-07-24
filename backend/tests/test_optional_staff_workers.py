"""可选 worker：默认不挂；开题写到才挂（keyword_mentioned）。"""

from app.bake.staff_posts import food_wants_rider, staff_posts_for_domain


def _ids(domain: str, text: str = "") -> list[str]:
    return [
        p["id"]
        for p in staff_posts_for_domain(domain, proposal_text=text)
    ]


def test_food_default_no_rider():
    assert _ids("DOM-FOOD") == ["counter"]


def test_food_rider_when_opening_wants_delivery():
    text = "点餐下单、档口接单，以及骑手配送到宿舍。"
    assert food_wants_rider(text)
    assert _ids("DOM-FOOD", text) == ["counter", "rider"]


def test_food_rider_via_waimai_peisong():
    """反向：写外卖配送、未写「骑手」也应挂。"""
    assert _ids("DOM-FOOD", "食堂点餐支持外卖配送到宿舍楼下。") == [
        "counter",
        "rider",
    ]


def test_food_no_rider_when_oos_only():
    text = (
        "主要功能：点餐下单、档口接单与取餐。\n"
        "三、非本期\n真支付、骑手实时调度不在本期。\n"
    )
    assert not food_wants_rider(text)
    assert _ids("DOM-FOOD", text) == ["counter"]


def test_food_weak_peisong_alone_no_rider():
    """反向边界：光杆「配送服务」太泛，不挂骑手。"""
    assert _ids("DOM-FOOD", "本系统提供配送服务。") == ["counter"]


def test_shop_default_no_picker():
    assert _ids("DOM-SHOP") == ["order_clerk"]


def test_shop_picker_when_opening_wants():
    text = "二手商城：购物车下单，仓库拣货员配货后发货。"
    assert _ids("DOM-SHOP", text) == ["order_clerk", "picker"]


def test_shop_picker_via_peihuo():
    """反向：写配货、未写拣货员。"""
    assert _ids("DOM-SHOP", "下单后仓库配货发货。") == ["order_clerk", "picker"]


def test_salon_default_no_stylist_login():
    assert _ids("DOM-SALON") == ["front"]


def test_salon_stylist_when_opening_wants():
    text = "美发预约选时段，技师到店服务办结。"
    assert _ids("DOM-SALON", text) == ["front", "stylist"]


def test_salon_stylist_via_faxingshi():
    assert _ids("DOM-SALON", "预约发型师造型。") == ["front", "stylist"]


def test_hotel_default_no_housekeeping():
    assert _ids("DOM-HOTEL") == ["front"]


def test_hotel_housekeeping_when_opening_wants():
    text = "民宿客房预订入住，客房保洁与客房服务跟进。"
    assert _ids("DOM-HOTEL", text) == ["front", "housekeeping"]


def test_hotel_housekeeping_via_zhengli():
    assert _ids("DOM-HOTEL", "每日客房整理。") == ["front", "housekeeping"]


def test_dorm_default_no_repairer():
    """缩样只写管理员派单时不空挂维修员。"""
    assert _ids("DOM-DORM") == ["dorm_mgr"]
    assert _ids("DOM-PROPERTY") == ["dispatcher"]


def test_dorm_repairer_when_opening_wants():
    assert _ids("DOM-DORM", "宿舍报修，维修员上门维修。") == [
        "dorm_mgr",
        "repairer",
    ]
    assert _ids("DOM-PROPERTY", "物业派单给维修师傅处理。") == [
        "dispatcher",
        "repairer",
    ]


def test_corpus_samples_no_orphan_workers():
    """近五年缩样（未写现场岗）不应挂可选 worker。"""
    import json
    from pathlib import Path

    corp = json.loads(
        Path(__file__).resolve().parent.joinpath(
            "fixtures/domain_opening_corpus.json"
        ).read_text(encoding="utf-8")
    )
    for s in corp["samples"]:
        workers = [
            p["id"]
            for p in staff_posts_for_domain(s["domain"], proposal_text=s["text"])
            if p.get("kind") == "worker"
        ]
        assert workers == [], f"{s['domain']} orphan workers={workers}"
