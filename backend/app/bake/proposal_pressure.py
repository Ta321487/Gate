"""测试开题「真单压力」档：把对照表扫词开叶子写成可命中词。

默认厚稿已按角色写模块；pressure=True 时再注入本域扫词开触发词，
便于空窗期模拟「真开题写全可选能力」时的匹配/挂载。

约束
----
- 只用 features/* · scene_scan 已收录的正向词；不支持项不进。
- 措辞须避开会逼降 DOM-GENERIC 的抢拱词（如图书裸「预约」→ 用「到书通知」）。
- 本模块只改开题正文素材，不新增 bake 能力。
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Callable

from app.bake.proposal_role_modules import RoleTree, _m

# (cap 或语义键, 写入开题的触发短句)
PressureLeaf = tuple[str, str]

# 域 → 压力叶子（对照 opening-feature-delivery-map 扫词开）
_PRESSURE_LEAVES: dict[str, list[PressureLeaf]] = {
    "DOM-LIBRARY": [
        ("loan_renew", "续借功能"),
        ("book_suggest", "图书荐购"),
        ("book_hold", "到书通知"),
    ],
    "DOM-EQUIP": [
        ("loan_renew", "续借功能"),
    ],
    "DOM-ASSET": [
        ("stock_count", "库存盘点"),
        ("stock_scrap", "报废"),
    ],
    "DOM-DORM": [
        ("staff_roster", "维修排班"),
    ],
    "DOM-PROPERTY": [
        ("staff_roster", "维修排班"),
    ],
    "DOM-IT": [
        ("staff_roster", "维修排班"),
    ],
    "DOM-ACTIVITY": [
        ("waitlist", "候补队列"),
    ],
    "DOM-COURSE": [
        ("waitlist", "候补队列"),
    ],
    "DOM-SHOP": [
        ("flash_price", "限时购"),
        ("product_spec", "规格说明"),
        ("order_review", "商品评价"),
        ("favorites", "商品收藏"),
        ("dm", "与商家在线沟通"),
        ("marketplace", "商家入驻"),
    ],
    "DOM-FOOD": [
        ("order_review", "餐品评价"),
        ("dm", "与商家在线沟通"),
        ("rider", "配送员"),
    ],
    "DOM-FORUM": [
        ("post_like", "帖子点赞"),
        ("content_report", "举报"),
        ("post_mute", "禁言"),
        ("dm", "私信"),
    ],
    "DOM-DATING": [
        ("content_report", "举报"),
    ],
    "DOM-MEETING": [
        ("room_equipment", "设备清单"),
    ],
    "DOM-SALON": [
        ("staff_roster", "技师排班"),
    ],
    "DOM-HOTEL": [
        ("order_review", "服务评价"),
    ],
    "DOM-CARRENT": [
        ("order_review", "服务评价"),
    ],
    "DOM-INTERN": [
        ("e_sign", "电子签"),
    ],
    "DOM-CONTRACT": [
        ("e_sign", "电子签"),
    ],
    "DOM-VISITOR": [
        ("code_qr", "通行码二维码"),
    ],
    "DOM-PARCEL": [
        ("code_qr", "取件码二维码"),
    ],
    "DOM-CARPASS": [
        ("code_qr", "通行码二维码"),
    ],
    "DOM-MEDIA": [
        ("item_comment", "片下评论"),
        ("user_publish", "用户投稿"),
        ("post_like", "点赞"),
        ("dm", "站内私信"),
    ],
    "DOM-MUSIC": [
        ("item_comment", "曲下评论"),
        ("user_publish", "用户上传"),
        ("post_like", "点赞"),
        ("dm", "站内私信"),
    ],
    "DOM-BLOG": [
        ("item_comment", "文下评论"),
        ("user_publish", "读者投稿"),
        ("post_like", "点赞"),
        ("content_report", "举报"),
        ("post_mute", "禁言"),
        ("dm", "私信"),
    ],
    # OA / 申请流：横切扫词（树已写「材料写到则启用」；压力稿注入触发词）
    "DOM-SEAL": [
        ("message_template", "消息模板"),
        ("audit_log", "操作日志"),
        ("deadline", "催办"),
        ("require_attach", "上传附件"),
        ("multi_approve", "三级审批"),
    ],
    "DOM-CERT": [
        ("message_template", "消息模板"),
        ("audit_log", "操作日志"),
        ("deadline", "催办"),
        ("require_attach", "上传附件"),
        ("multi_approve", "三级审批"),
    ],
    "DOM-EXPENSE": [
        ("message_template", "消息模板"),
        ("audit_log", "操作日志"),
        ("deadline", "催办"),
        ("require_attach", "上传附件"),
        ("multi_approve", "三级审批"),
    ],
    "DOM-PROMO": [
        ("message_template", "消息模板"),
        ("audit_log", "操作日志"),
        ("deadline", "催办"),
        ("require_attach", "上传附件"),
    ],
    "DOM-TRIP": [
        ("message_template", "消息模板"),
        ("audit_log", "操作日志"),
        ("deadline", "催办"),
        ("require_attach", "上传附件"),
    ],
    "DOM-ACAD": [
        ("message_template", "消息模板"),
        ("audit_log", "操作日志"),
        ("deadline", "催办"),
        ("require_attach", "上传材料"),
        ("multi_approve", "三级审批"),
    ],
    "DOM-FLEET": [
        ("message_template", "消息模板"),
        ("audit_log", "操作日志"),
        ("deadline", "催办"),
    ],
    "DOM-CONTRACT": [
        ("e_sign", "电子签"),
        ("message_template", "消息模板"),
        ("audit_log", "操作日志"),
        ("require_attach", "上传附件"),
    ],
}


def pressure_leaves_for(domain: str) -> list[PressureLeaf]:
    return list(_PRESSURE_LEAVES.get(str(domain or "").strip().upper()) or [])


def pressure_phrases_for(domain: str) -> list[str]:
    return [phrase for _, phrase in pressure_leaves_for(domain)]


def inject_pressure_into_tree(
    roles: list[RoleTree],
    domain: str,
) -> list[RoleTree]:
    """在首个角色下追加「材料命中能力」模块；无叶子则原样返回。"""
    phrases = pressure_phrases_for(domain)
    if not phrases or not roles:
        return roles
    out = deepcopy(roles)
    detail = "、".join(phrases)
    mods = list(out[0].get("modules") or [])
    mods.append(
        _m(
            "材料命中能力模块",
            f"本期开题写明并实现：{detail}（开题命中即挂载，未写则不出现）",
        )
    )
    out[0]["modules"] = mods
    return out


def expected_capability_ids(domain: str) -> list[str]:
    """压力叶子 → merge_proposal_capabilities 后应出现的能力 id（不含岗位/schema 开关语义键）。"""
    skip = {"marketplace", "rider", "user_publish", "require_attach"}
    return [key for key, _ in pressure_leaves_for(domain) if key not in skip]


def expected_scan_checks(domain: str) -> list[tuple[str, Callable[[str], bool]]]:
    """供测试：压力稿应命中的扫词检查器（有则返回）。"""
    from app.bake.features.book_hold import scan_book_hold
    from app.bake.features.book_suggest import scan_book_suggest
    from app.bake.features.code_qr import scan_code_qr
    from app.bake.features.core_cap_scan import scan_loan_renew
    from app.bake.features.dm import scan_dm, scan_dm_merchant_peers
    from app.bake.features.e_sign import scan_e_sign
    from app.bake.features.favorites import scan_content_report, scan_favorites, scan_post_like
    from app.bake.features.order_extras import scan_flash_price, scan_order_review
    from app.bake.features.post_mute import scan_post_mute
    from app.bake.features.product_spec import scan_product_spec
    from app.bake.features.room_equipment import scan_room_equipment
    from app.bake.features.staff_roster import scan_staff_roster
    from app.bake.features.stock_scrap import scan_stock_count, scan_stock_scrap
    from app.bake.features.ticket_flow_opts import scan_waitlist
    from app.bake.features.item_comment import scan_item_comment
    from app.bake.features.user_publish import scan_user_publish
    from app.bake.features.message_template import scan_message_template
    from app.bake.features.audit_log import scan_audit_log
    from app.bake.features.core_cap_scan import scan_loan_deadline, scan_ticket_sla
    from app.bake.features.ticket_flow_opts import (
        scan_require_attach,
        scan_three_level,
        scan_two_level,
    )
    from app.bake.scene_scan import scan_shop_marketplace
    from app.bake.staff_posts import food_wants_rider

    mapping: dict[str, Callable[[str], bool]] = {
        "loan_renew": scan_loan_renew,
        "book_suggest": scan_book_suggest,
        "book_hold": scan_book_hold,
        "stock_count": scan_stock_count,
        "stock_scrap": scan_stock_scrap,
        "staff_roster": scan_staff_roster,
        "waitlist": scan_waitlist,
        "flash_price": scan_flash_price,
        "product_spec": scan_product_spec,
        "order_review": scan_order_review,
        "favorites": scan_favorites,
        "dm": lambda t: scan_dm(t) or scan_dm_merchant_peers(t),
        "marketplace": lambda t: scan_shop_marketplace("", t) or scan_shop_marketplace(t, t),
        "rider": food_wants_rider,
        "post_like": scan_post_like,
        "content_report": scan_content_report,
        "post_mute": scan_post_mute,
        "room_equipment": scan_room_equipment,
        "e_sign": scan_e_sign,
        "code_qr": scan_code_qr,
        "user_publish": lambda t: scan_user_publish(t),
        "item_comment": scan_item_comment,
        "message_template": scan_message_template,
        "audit_log": scan_audit_log,
        "deadline": lambda t: scan_loan_deadline(t) or scan_ticket_sla(t),
        "require_attach": scan_require_attach,
        "multi_approve": lambda t: scan_three_level(t) or scan_two_level(t),
    }
    out: list[tuple[str, Callable[[str], bool]]] = []
    for key, _phrase in pressure_leaves_for(domain):
        fn = mapping.get(key)
        if fn:
            out.append((key, fn))
    return out
