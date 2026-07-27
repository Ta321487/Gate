"""领域目录 — 影院选座购票（C-15）。"""

from __future__ import annotations

from app.bake.gate_contracts import gate_order_shell

DOMAINS: dict = {
    "DOM-CINEMA": {
        "label": "影院选座",
        "keywords": [
            "选座购票",
            "影院选座",
            "电影票选座",
            "在线选座",
            "座位图购票",
            "影院售票",
            "电影院购票",
            "场次选座",
            "影院票务选座",
            "观影选座",
        ],
        "match_hint": (
            "适用：影院/演出场次座位图选座并下单购票（占座，无真锁座高并发）。"
            "勿与影视点播收藏（影视综）、活动报名领票占名额、图书馆自习座位时段预约混淆。"
        ),
        "entities": ["Archive", "Category", "Order", "Seat", "Notice"],
        "roles": ["user", "admin", "subadmin"],
        "flows": ["选场次 → 座位图选座 → 下单占座 → 我的订单"],
        "features": [
            {"name": "登录", "status": "baseline"},
            {"name": "个人资料与头像", "status": "baseline"},
            {"name": "管理端工作台", "status": "module"},
            {"name": "场次管理", "status": "domain"},
            {"name": "分类管理", "status": "module"},
            {"name": "用户管理", "status": "module"},
            {"name": "选座购票", "status": "flow"},
            {"name": "我的订单", "status": "module"},
            {"name": "订单管理", "status": "module"},
            {"name": "公告管理", "status": "module"},
            {"name": "真锁座高并发", "status": "out_of_mvp"},
            {"name": "真支付对接", "status": "out_of_mvp"},
        ],
        "out_of_mvp": ["真锁座高并发", "真支付对接", "第三方票务接口"],
        "themes": [
            {"id": "cinema-night", "label": "影院午夜"},
            {"id": "cinema-amber", "label": "暖幕琥珀"},
            {"id": "cinema-teal", "label": "荧幕青绿"},
            {"id": "cinema-sand", "label": "影院暖沙"},
        ],
        "gate": gate_order_shell(
            archive_feature="场次管理",
            cart_feature="选座购票",
            orders_feature="订单管理",
            users_feature="用户管理",
        ),
        "portal_banners": True,
        "runtime": {
            "enable_ticket": False,
            "register_role": "user",
            "archive_category_table": "category",
            "archive_item_table": "cinema_show",
            "order_cart_table": "cart_line",
            "order_table": "biz_order",
            "order_line_table": "order_line",
            "use_quota": True,
        },
    },
}
