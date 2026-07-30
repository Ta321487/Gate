"""领域目录 — SHOP/FOOD。"""

from __future__ import annotations

from app.bake.gate_contracts import (
    gate_order_shell,
)

DOMAINS: dict = {
    "DOM-SHOP": {
        "label": "商城",
        "keywords": [
            "商城", "商品", "购物车", "下单", "电商", "网购", "二手", "校园商城", "二手交易", "在线商城",
            "二手教材", "闲置交易", "跳蚤市场",
            "文印", "打印店", "打印订单",
            "农资", "特产", "鲜花", "零售商城",
            "积分兑换", "积分商城",
            "跑腿代买", "校园跑腿", "代买订单",
        ],
        "match_hint": (
            "适用：商品浏览、购物车下单交易；校园二手/闲置、文印打印、农资特产鲜花零售、"
            "积分兑换商城、校园跑腿代买（订单向）亦挂本域。"
            "勿与点餐（食堂菜品）、客房预订、快递驿站取件（包裹核销）或旅行社线路报名混淆。"
        ),
        "entities": ["Product", "Category", "Order", "Cart", "Guestbook", "Notice"],
        "roles": ["user", "admin", "subadmin"],
        "flows": ["加购 → 下单 → 发货"],
        "features": [
            {"name": "用户登录", "status": "baseline"},
            {"name": "个人资料与头像", "status": "baseline"},
            {"name": "管理端工作台", "status": "module"},
            {"name": "商品浏览", "status": "domain"},
            {"name": "购物车下单", "status": "flow"},
            {"name": "订单管理", "status": "flow"},
            {"name": "用户管理", "status": "module"},
            {"name": "公告管理", "status": "module"},
            {"name": "访客留言", "status": "module"},
            {"name": "推荐算法", "status": "out_of_mvp"},
        ],
        "out_of_mvp": ["推荐算法"],
        "themes": [
            {"id": "shop-coral", "label": "促销珊瑚"},
            {"id": "shop-ocean", "label": "清仓海蓝"},
            {"id": "shop-lime", "label": "生鲜青绿"},
            {"id": "shop-gold", "label": "会员金"},
            {"id": "shop-night", "label": "夜间闪购"},
        ],
        "gate": gate_order_shell(
            archive_feature="商品浏览",
            cart_feature="购物车下单",
            orders_feature="订单管理",
        ),
        "runtime": {
            "enable_ticket": False,
            "register_role": "user",
            "archive_category_table": "category",
            "archive_item_table": "product",
            "order_cart_table": "cart_line",
            "order_table": "biz_order",
            "order_line_table": "order_line",
            "use_quota": True,
        },
    },
    "DOM-FOOD": {
        "label": "点餐",
        "keywords": ["点餐", "订餐", "食堂", "饭堂", "外卖", "菜品", "餐厅", "奶茶", "快餐", "食堂点餐", "档口"],
        "match_hint": (
            "适用：点餐/订餐下单；奶茶/档口/食堂场景均挂本域。"
            "餐饮食品安全排查、追溯上报选事件上报，不要选本域。"
            "校园跑腿代买若主写下单选商城，勿与驿站取件混淆。"
        ),
        "entities": ["Dish", "Order", "Category", "Guestbook", "Notice"],
        "roles": ["user", "admin", "subadmin"],
        "flows": ["选菜 → 下单 → 堂食/自取"],
        "features": [
            {"name": "登录", "status": "baseline"},
            {"name": "个人资料与头像", "status": "baseline"},
            {"name": "管理端工作台", "status": "module"},
            {"name": "菜品浏览", "status": "domain"},
            {"name": "下单取餐", "status": "flow"},
            {"name": "订单管理", "status": "flow"},
            {"name": "用户管理", "status": "module"},
            {"name": "公告管理", "status": "module"},
            {"name": "访客留言", "status": "module"},
        ],
        "out_of_mvp": [],
        "themes": [
            {"id": "food-chili", "label": "食堂红"},
            {"id": "food-bamboo", "label": "清新竹绿"},
            {"id": "food-sesame", "label": "暖米褐"},
            {"id": "food-berry", "label": "果饮紫"},
            {"id": "food-night", "label": "夜宵档"},
        ],
        "gate": gate_order_shell(
            archive_feature="菜品浏览",
            cart_feature="下单取餐",
            orders_feature="订单管理",
        ),
        "runtime": {
            "enable_ticket": False,
            "register_role": "user",
            "archive_category_table": "category",
            "archive_item_table": "dish",
            "order_cart_table": "cart_line",
            "order_table": "biz_order",
            "order_line_table": "order_line",
            "use_quota": True,
        },
    }
}
