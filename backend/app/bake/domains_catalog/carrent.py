"""领域目录 — 四轮商业租车（P-32 · 神州/一嗨式按日租）。"""

from __future__ import annotations

from app.bake.gate_contracts import gate_slot_shell

DOMAINS: dict = {
    "DOM-CARRENT": {
        "label": "汽车租赁",
        "keywords": [
            "汽车租赁",
            "租车",
            "网约租车",
            "按日租车",
            "取车还车",
            "车型租赁",
            "新能源汽车租赁",
            "租车管理系统",
            "汽车租赁系统",
            "自驾租车",
            "门店取车",
            "租车下单",
        ],
        "match_hint": (
            "适用：四轮商业租车（神州/一嗨式）——车型档案、按日租期下单、门店取车/还车办结（无真支付/GPS）。"
            "勿与公务用车申请审批、校园器材/电动车借用审核、车位预约、车辆通行证、拼车结伴、客房预订混淆；"
            "亦勿与哈啰式共享电单车/扫码开锁物联网混淆（不在本域）。"
        ),
        "entities": ["Vehicle", "Booking", "Order"],
        "roles": ["user", "admin", "subadmin"],
        "flows": ["选车 → 选租期 → 下单 → 取车/还车"],
        "features": [
            {"name": "登录", "status": "baseline"},
            {"name": "个人资料与头像", "status": "baseline"},
            {"name": "管理端工作台", "status": "module"},
            {"name": "车型浏览", "status": "domain"},
            {"name": "租车订单", "status": "flow"},
            {"name": "用户管理", "status": "module"},
            {"name": "公告管理", "status": "module"},
            {"name": "真支付对接", "status": "out_of_mvp"},
            {"name": "GPS轨迹/调度地图", "status": "out_of_mvp"},
            {"name": "配件商城双订单", "status": "out_of_mvp"},
            {"name": "共享电单车扫码开锁", "status": "out_of_mvp"},
        ],
        "out_of_mvp": [
            "真支付对接",
            "GPS轨迹",
            "调度地图",
            "配件商城双订单",
            "共享电单车扫码开锁",
            "物联网开锁",
        ],
        "themes": [
            {"id": "carrent-teal", "label": "租车青绿"},
            {"id": "carrent-sand", "label": "租车暖沙"},
            {"id": "carrent-slate", "label": "租车灰青"},
            {"id": "carrent-night", "label": "租车深色"},
        ],
        "gate": gate_slot_shell(
            archive_feature="车型浏览",
            reserve_feature="租车订单",
            with_orders=True,
        ),
        "runtime": {
            "enable_ticket": False,
            "register_role": "user",
            "archive_category_table": "category",
            "archive_item_table": "vehicle",
            "slot_table": "resource_slot",
            "reservation_table": "reservation",
            "order_cart_table": "cart_line",
            "order_table": "biz_order",
            "order_line_table": "order_line",
            "use_quota": False,
        },
    },
}
