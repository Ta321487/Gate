"""未命中具体 DOM-* 时：按 ARCH-* 绑定运行时壳，避免误落 LIBRARY / 空 CRUD。"""

from __future__ import annotations

import copy
import re
from typing import Any

from app.bake.gate_contracts import gate_archive_ticket, gate_order_shell, gate_slot_shell
from app.bake.schema_templates import product_name_from_title

# archetype → 能力积木（GENERIC 专用）
ARCH_CAPABILITIES: dict[str, list[str]] = {
    "ARCH-CRUD": ["archive", "content", "org_users"],
    "ARCH-CONTENT": ["archive", "ticket_flow", "content", "org_users", "recommend"],
    "ARCH-FLOW": ["archive", "ticket_flow", "quota", "content", "org_users"],
    "ARCH-STOCK": ["archive", "ticket_flow", "quota", "content", "org_users"],
    "ARCH-TRADE": ["archive", "order_lines", "quota", "content", "org_users"],
    "ARCH-RESERVE": ["archive", "slot_reserve", "content", "org_users"],
}

# bake SQL 模板名（相对 bake/sql/）
ARCH_SQL: dict[str, str] = {
    "ARCH-CRUD": "DOM-GENERIC.sql",
    "ARCH-CONTENT": "DOM-GENERIC-FLOW.sql",
    "ARCH-FLOW": "DOM-GENERIC-FLOW.sql",
    "ARCH-STOCK": "DOM-GENERIC-FLOW.sql",
    "ARCH-TRADE": "DOM-GENERIC-TRADE.sql",
    "ARCH-RESERVE": "DOM-GENERIC-RESERVE.sql",
}


def normalize_archetype(archetype: str | None) -> str:
    a = (archetype or "ARCH-CRUD").strip()
    return a if a in ARCH_CAPABILITIES else "ARCH-CRUD"


def shell_capabilities(archetype: str | None) -> list[str]:
    return list(ARCH_CAPABILITIES[normalize_archetype(archetype)])


def shell_sql_filename(archetype: str | None) -> str:
    return ARCH_SQL[normalize_archetype(archetype)]


def entity_noun(title: str) -> str:
    """开题标题 → 档案实体短名（去掉系统/平台等后缀）。"""
    name = product_name_from_title(title or "")
    name = re.sub(
        r"(的设计与实现|系统设计|的实现|的设计|管理系统|管理平台|信息平台|系统|平台|管理)\s*$",
        "",
        name,
    ).strip("的与及 ")
    if len(name) < 2:
        return "业务对象"
    if len(name) > 16:
        name = name[:16]
    return name


def shell_runtime(archetype: str | None) -> dict[str, Any]:
    a = normalize_archetype(archetype)
    base = {
        "register_role": "user",
        "archive_category_table": "category",
        "archive_item_table": "biz_item",
        "enable_ticket": False,
        "use_quota": False,
        "use_deadline": False,
    }
    if a in ("ARCH-FLOW", "ARCH-STOCK", "ARCH-CONTENT"):
        base.update(
            {
                "enable_ticket": True,
                "ticket_mode": "archive",
                "ticket_table": "biz_ticket",
                "use_quota": a != "ARCH-CONTENT",
                "use_deadline": False,
            }
        )
    elif a == "ARCH-TRADE":
        base.update(
            {
                "order_cart_table": "cart_line",
                "order_table": "biz_order",
                "order_line_table": "order_line",
                "use_quota": True,
            }
        )
    elif a == "ARCH-RESERVE":
        base.update(
            {
                "slot_table": "resource_slot",
                "reservation_table": "reservation",
                "use_quota": False,
            }
        )
    return base


def shell_gate(archetype: str | None, noun: str) -> dict[str, Any]:
    a = normalize_archetype(archetype)
    if a == "ARCH-TRADE":
        return gate_order_shell(
            archive_feature=f"{noun}浏览",
            cart_feature="购物车下单",
            orders_feature="订单管理",
        )
    if a == "ARCH-RESERVE":
        return gate_slot_shell(
            archive_feature=f"{noun}检索",
            reserve_feature="时段预约",
        )
    if a in ("ARCH-FLOW", "ARCH-STOCK", "ARCH-CONTENT"):
        return gate_archive_ticket(
            archive_feature=f"{noun}检索",
            flow_feature="申请 → 审核",
            records_feature="业务记录",
            users_feature="用户管理",
            with_deadline=False,
        )
    # CRUD：无专用 gate 契约（仅基线页）
    return {
        "routes": [
            {"seg": "archive", "from_feature": f"{noun}检索"},
            {"seg": "admin/archive", "from_feature": f"{noun}管理"},
            {"seg": "admin/users", "from_feature": "用户管理"},
            {"seg": "profile", "from_baseline": "profile"},
            {"seg": "register", "from_baseline": "register"},
        ],
        "files": [
            "backend/src/main/java/com/thesis/capability/ArchiveStore.java",
            "frontend/src/views/user/ArchiveBrowse.vue",
            "frontend/src/views/admin/ArchiveAdmin.vue",
            "sql/schema.sql",
        ],
        "flow_api": {},
        "admin_invariants": {
            "require_super_auth": True,
            "master_kind": "archive",
            "master_menus": ["archive", "category"],
            "super_menus": ["users", "content", "archive", "category"],
        },
    }


def shell_features(archetype: str | None, noun: str) -> list[dict[str, str]]:
    a = normalize_archetype(archetype)
    common = [
        {"name": "登录", "status": "baseline"},
        {"name": "个人资料与头像", "status": "baseline"},
        {"name": "管理端工作台", "status": "module"},
        {"name": f"{noun}检索", "status": "domain"},
        {"name": "分类管理", "status": "module"},
        {"name": "用户管理", "status": "module"},
        {"name": "公告管理", "status": "module"},
    ]
    if a == "ARCH-TRADE":
        return common + [
            {"name": "购物车下单", "status": "flow"},
            {"name": "订单管理", "status": "flow"},
        ]
    if a == "ARCH-RESERVE":
        return common + [{"name": "时段预约", "status": "flow"}]
    if a in ("ARCH-FLOW", "ARCH-STOCK", "ARCH-CONTENT"):
        return common + [
            {"name": "申请 → 审核", "status": "flow"},
            {"name": "业务记录", "status": "module"},
        ]
    return common + [{"name": f"{noun}管理", "status": "module"}]


def build_generic_shell_schema(title: str, archetype: str | None) -> dict[str, Any]:
    """GENERIC + ARCH-* → 像正经毕设的文案壳（仍用固定档案列）。"""
    from app.bake.schema_templates import _order_shell_schema, _slot_shell_schema, _archive_ticket_schema

    a = normalize_archetype(archetype)
    noun = entity_noun(title)
    caps = shell_capabilities(a)
    app = product_name_from_title(title)

    if a == "ARCH-TRADE":
        schema = _order_shell_schema(
            title,
            domain="DOM-GENERIC",
            user_role_id="user",
            user_label="用户",
            admin_label="管理员（总管）",
            subadmin_label="业务员",
            archive_key="item",
            archive_label=noun,
            archive_plural=noun,
            archive_fields=[
                {"key": "title", "label": f"{noun}名称", "type": "string"},
                {"key": "author", "label": "单价(元)/摘要", "type": "string"},
                {"key": "isbn", "label": "编号/说明", "type": "string"},
                {"key": "category", "label": "分类", "type": "string"},
                {"key": "stock", "label": "库存/数量", "type": "number"},
            ],
            archive_menu_admin=f"{noun}管理",
            archive_menu_user=f"{noun}浏览",
            users_menu="用户管理",
            cart_label="购物车",
            my_orders_label="我的订单",
            orders_admin_label="订单管理",
            auth_eyebrow=app,
            auth_lead=f"验证码登录；浏览{noun}、加入购物车并提交订单（演示无真支付）。",
            auth_points=["验证码登录", f"{noun}浏览", "购物车与订单"],
            register_hint="注册后即可使用",
            notice_title="使用须知",
            notice_body=f"本系统用于{noun}相关业务演示；下单流程无真支付。",
            notice_page_title="公告",
        )
    elif a == "ARCH-RESERVE":
        schema = _slot_shell_schema(
            title,
            domain="DOM-GENERIC",
            user_role_id="user",
            user_label="用户",
            admin_label="管理员（总管）",
            subadmin_label="业务员",
            archive_key="item",
            archive_label=noun,
            archive_plural=noun,
            archive_fields=[
                {"key": "title", "label": f"{noun}名称", "type": "string"},
                {"key": "author", "label": "费用/负责人", "type": "string"},
                {"key": "isbn", "label": "位置/说明", "type": "string"},
                {"key": "category", "label": "分类", "type": "string"},
            ],
            archive_menu_admin=f"{noun}管理",
            archive_menu_user=f"选{noun}",
            users_menu="用户管理",
            my_resv_label="我的预约",
            resv_admin_label="预约记录",
            auth_eyebrow=app,
            auth_lead=f"验证码登录；选择{noun}与时段占坑预约。",
            auth_points=["验证码登录", f"{noun}检索", "时段预约"],
            register_hint="注册后即可预约",
            notice_title="预约须知",
            notice_body="请按时使用；取消预约将释放时段名额。",
            notice_page_title="公告",
        )
    elif a in ("ARCH-FLOW", "ARCH-STOCK", "ARCH-CONTENT"):
        schema = _archive_ticket_schema(
            title,
            domain="DOM-GENERIC",
            user_role_id="user",
            user_label="用户",
            admin_label="管理员（总管）",
            subadmin_label="审核员",
            archive_key="item",
            archive_label=noun,
            archive_plural=noun,
            archive_fields=[
                {"key": "title", "label": f"{noun}名称", "type": "string"},
                {"key": "author", "label": "摘要/责任人", "type": "string"},
                {"key": "isbn", "label": "编号/说明", "type": "string"},
                {"key": "category", "label": "分类", "type": "string"},
                {"key": "stock", "label": "可申请数", "type": "number"},
            ],
            ticket_key="ticket",
            ticket_label="申请单",
            ticket_plural="申请",
            verbs={
                "apply": "提交申请",
                "approve": "通过",
                "reject": "驳回",
                "return": "完结",
                "remind": "提醒",
            },
            states={
                "pending": "待审核",
                "approved": "进行中",
                "rejected": "已驳回",
                "returned": "已完结",
                "overdue": "已逾期",
            },
            archive_menu_admin=f"{noun}管理",
            archive_menu_user=f"{noun}检索",
            users_menu="用户管理",
            auth_eyebrow=app,
            auth_lead=f"验证码登录；浏览{noun}并提交申请，管理员审核处理。",
            auth_points=["验证码登录", f"{noun}检索", "申请与审核"],
            register_hint="注册后可提交申请",
            notice_title="办理须知",
            notice_body="请如实填写申请说明；审核结果可在站内消息中查看。",
            notice_page_title="公告",
            my_tickets_label="我的申请",
            pending_label="待审申请",
            records_label="申请记录",
            with_deadline=False,
            stock_display="count" if a != "ARCH-CONTENT" else "available",
        )
    else:
        # 纯档案 CRUD
        schema = {
            "version": 1,
            "title": title,
            "capabilities": caps,
            "roles": {
                "user": {"id": "user", "label": "用户"},
                "admin": {"id": "admin", "label": "管理员（总管）"},
                "subadmin": {"id": "subadmin", "label": "业务员"},
            },
            "entities": {
                "archive": {
                    "key": "item",
                    "label": noun,
                    "labelPlural": noun,
                    "fields": [
                        {"key": "title", "label": f"{noun}名称", "type": "string"},
                        {"key": "author", "label": "摘要", "type": "string"},
                        {"key": "isbn", "label": "编号/说明", "type": "string"},
                        {"key": "category", "label": "分类", "type": "string"},
                        {"key": "stock", "label": "数量", "type": "number"},
                    ],
                    "stockDisplay": "count",
                },
            },
            "menus": {
                "admin": [
                    {"key": "dashboard", "label": "工作台"},
                    {"key": "archive", "label": f"{noun}管理", "superOnly": True},
                    {"key": "category", "label": "分类管理", "superOnly": True},
                    {"key": "users", "label": "用户管理", "superOnly": True},
                    {"key": "content", "label": "公告管理", "superOnly": True},
                ],
                "user": [
                    {"key": "archive", "label": f"{noun}浏览"},
                    {"key": "content", "label": "公告"},
                    {"key": "profile", "label": "个人资料"},
                ],
            },
            "labels": {
                "appName": app,
                "authEyebrow": app,
                "authLead": f"验证码登录；维护与查询{noun}信息。",
                "authPoints": ["验证码登录", f"{noun}浏览", "分类管理"],
                "registerRoleHint": "注册后即可使用",
                "noticePageTitle": "公告",
                "noticePageLead": "通知与须知，点击条目阅读全文。",
            },
            "seeds": {
                "noticeTitle": "系统公告",
                "noticeBody": f"{app}已就绪，可开始维护{noun}数据。",
            },
        }

    schema["capabilities"] = caps
    # _order/_slot/_archive helpers 会从 DOMAIN_CAPABILITIES["DOM-GENERIC"] 读旧 caps，这里强制覆盖
    schema["capabilities"] = caps
    return schema


def apply_generic_shell(spec: dict[str, Any]) -> dict[str, Any]:
    """当 domain=DOM-GENERIC 时，按 archetype 写入 runtime/gate/features/schema。"""
    if (spec.get("domain") or "") != "DOM-GENERIC":
        return spec
    spec = dict(spec)
    arch = normalize_archetype(spec.get("archetype"))
    title = spec.get("title") or "毕设系统"
    noun = entity_noun(title)
    caps = shell_capabilities(arch)
    spec["archetype"] = arch
    spec["capabilities"] = caps
    spec["runtime"] = shell_runtime(arch)
    spec["gate"] = shell_gate(arch, noun)
    spec["features"] = shell_features(arch, noun)
    spec["flows"] = {
        "ARCH-TRADE": ["加购 → 下单 → 履约"],
        "ARCH-RESERVE": ["选资源 → 占坑预约 → 取消"],
        "ARCH-FLOW": ["提交申请 → 审核 → 完结"],
        "ARCH-STOCK": ["领用申请 → 审核 → 完结"],
        "ARCH-CONTENT": ["浏览 → 收藏/申请 → 审核"],
        "ARCH-CRUD": ["新增 → 编辑 → 查询"],
    }.get(arch, ["新增 → 编辑 → 查询"])
    spec["entities"] = [noun, "Category", "Notice"]
    # 展示用：不要叫「通用」
    spec["domain_label"] = product_name_from_title(title)
    spec["industry"] = spec["domain_label"]
    from app.bake.profile_fields import attach_profile_fields

    schema = build_generic_shell_schema(title, arch)
    spec["schema"] = attach_profile_fields(schema, "DOM-GENERIC")
    return spec
