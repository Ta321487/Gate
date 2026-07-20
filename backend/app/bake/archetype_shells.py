"""未命中具体 DOM-* 时：按 ARCH-*（可多条）绑定运行时壳。"""

from __future__ import annotations

import re
from typing import Any

from app.bake.gate_contracts import gate_archive_ticket, gate_order_shell, gate_slot_shell
from app.bake.schema_templates import product_name_from_title

ARCH_CAPABILITIES: dict[str, list[str]] = {
    "ARCH-CRUD": ["archive", "content", "org_users"],
    "ARCH-CONTENT": ["archive", "ticket_flow", "content", "org_users", "recommend"],
    "ARCH-FLOW": ["archive", "ticket_flow", "quota", "content", "org_users"],
    "ARCH-STOCK": ["archive", "ticket_flow", "quota", "content", "org_users"],
    "ARCH-TRADE": ["archive", "order_lines", "quota", "content", "org_users"],
    "ARCH-RESERVE": ["archive", "slot_reserve", "content", "org_users"],
}

_FLOW_FAMILY = frozenset({"ARCH-FLOW", "ARCH-STOCK", "ARCH-CONTENT"})
_PATH_ORDER = ("ARCH-RESERVE", "ARCH-TRADE", "ARCH-FLOW", "ARCH-STOCK", "ARCH-CONTENT", "ARCH-CRUD")


def normalize_archetype(archetype: str | None) -> str:
    a = (archetype or "ARCH-CRUD").strip()
    return a if a in ARCH_CAPABILITIES else "ARCH-CRUD"


def normalize_archetypes(archetypes: list[str] | str | None, primary: str | None = None) -> list[str]:
    if isinstance(archetypes, str):
        raw = [archetypes]
    else:
        raw = list(archetypes or [])
    if primary:
        raw.insert(0, primary)
    out: list[str] = []
    for a in raw:
        n = normalize_archetype(a)
        if n not in out:
            out.append(n)
    if not out:
        out = ["ARCH-CRUD"]
    # 稳定排序：主路径优先级，便于 SQL/展示
    rank = {k: i for i, k in enumerate(_PATH_ORDER)}
    out.sort(key=lambda x: rank.get(x, 99))
    return out


def path_flags(archetypes: list[str] | str | None) -> tuple[bool, bool, bool]:
    arches = normalize_archetypes(archetypes)
    need_flow = any(a in _FLOW_FAMILY for a in arches)
    need_trade = "ARCH-TRADE" in arches
    need_reserve = "ARCH-RESERVE" in arches
    return need_flow, need_trade, need_reserve


def shell_capabilities(archetype: str | None = None, archetypes: list[str] | None = None) -> list[str]:
    arches = normalize_archetypes(archetypes, primary=archetype)
    caps: list[str] = []
    for a in arches:
        for c in ARCH_CAPABILITIES[a]:
            if c not in caps:
                caps.append(c)
    return caps


def shell_sql_filename(archetype: str | None = None, archetypes: list[str] | None = None) -> str:
    """单路径仍指向原模板名（兼容）；多路径由 compose 处理，此名仅作标记。"""
    need_flow, need_trade, need_reserve = path_flags(normalize_archetypes(archetypes, primary=archetype))
    n = sum([need_flow, need_trade, need_reserve])
    if n <= 1:
        if need_trade:
            return "DOM-GENERIC-TRADE.sql"
        if need_reserve:
            return "DOM-GENERIC-RESERVE.sql"
        if need_flow:
            return "DOM-GENERIC-FLOW.sql"
        return "DOM-GENERIC.sql"
    return "DOM-GENERIC-COMPOSED.sql"


def entity_noun(title: str) -> str:
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


def _generic_flow_copy(title: str, noun: str) -> dict[str, Any]:
    """GENERIC 审核流：按题名润色请假/考勤等常见壳，避免一律「业务对象」。"""
    t = title or ""
    if any(k in t for k in ("请假", "销假")):
        return {
            "user_label": "员工",
            "admin_label": "人事主管（总管）",
            "subadmin_label": "考勤员",
            "archive_label": "假种",
            "archive_fields": [
                {"key": "title", "label": "假种名称", "type": "string"},
                {"key": "author", "label": "说明", "type": "string"},
                {"key": "isbn", "label": "规则备注", "type": "string"},
                {"key": "category", "label": "分类", "type": "select"},
                {"key": "stock", "label": "可申请", "type": "number"},
            ],
            "ticket_label": "请假单",
            "ticket_plural": "请假",
            "verbs": {
                "apply": "提交请假",
                "approve": "批准",
                "reject": "驳回",
                "return": "销假",
                "remind": "催办",
            },
            "states": {
                "pending": "待审批",
                "approved": "已批准",
                "rejected": "已驳回",
                "returned": "已销假",
                "overdue": "已失效",
            },
            "archive_menu_admin": "假种管理",
            "archive_menu_user": "假种说明",
            "my_tickets_label": "我的请假",
            "pending_label": "请假审批",
            "records_label": "请假记录",
            "auth_eyebrow": "请假管理",
            "auth_lead": "验证码登录；选择假种提交请假，人事审批后生效。",
            "auth_points": ["验证码登录", "提交请假", "审批进度"],
            "register_hint": "注册后可在线请假",
            "notice_title": "请假须知",
            "notice_body": "请提前申请并等待审批；紧急情况请先口头报备再补单。",
            "require_remark": True,
            "remark_label": "请假事由",
            "pick_date_range": True,
        }
    if any(k in t for k in ("考勤", "打卡", "出勤")):
        return {
            "user_label": "员工",
            "admin_label": "人事主管（总管）",
            "subadmin_label": "考勤员",
            "archive_label": "班次",
            "archive_fields": [
                {"key": "title", "label": "班次名称", "type": "string"},
                {"key": "author", "label": "时段说明", "type": "string"},
                {"key": "isbn", "label": "地点/备注", "type": "string"},
                {"key": "category", "label": "分类", "type": "select"},
                {"key": "stock", "label": "可登记", "type": "number"},
            ],
            "ticket_label": "考勤单",
            "ticket_plural": "考勤",
            "verbs": {
                "apply": "提交登记",
                "approve": "确认",
                "reject": "驳回",
                "return": "完结",
                "remind": "催办",
            },
            "states": {
                "pending": "待确认",
                "approved": "已确认",
                "rejected": "已驳回",
                "returned": "已完结",
                "overdue": "已失效",
            },
            "archive_menu_admin": "班次管理",
            "archive_menu_user": "班次说明",
            "my_tickets_label": "我的考勤",
            "pending_label": "考勤确认",
            "records_label": "考勤记录",
            "auth_eyebrow": "考勤管理",
            "auth_lead": "验证码登录；按班次提交出勤登记，人事确认后入档。",
            "auth_points": ["验证码登录", "出勤登记", "人事确认"],
            "register_hint": "注册后可登记出勤",
            "notice_title": "考勤须知",
            "notice_body": "请按班次如实登记；异常出勤须备注原因。",
        }
    if any(k in t for k in ("人事", "员工档案", "人力资源", "HR")):
        return {
            "user_label": "员工",
            "admin_label": "人事主管（总管）",
            "subadmin_label": "人事专员",
            "archive_label": "人事事项",
            "archive_fields": [
                {"key": "title", "label": "事项名称", "type": "string"},
                {"key": "author", "label": "负责人", "type": "string"},
                {"key": "isbn", "label": "说明", "type": "string"},
                {"key": "category", "label": "分类", "type": "select"},
                {"key": "stock", "label": "可办理", "type": "number"},
            ],
            "ticket_label": "人事单",
            "ticket_plural": "办理",
            "verbs": {
                "apply": "提交申请",
                "approve": "通过",
                "reject": "驳回",
                "return": "完结",
                "remind": "催办",
            },
            "states": {
                "pending": "待审核",
                "approved": "办理中",
                "rejected": "已驳回",
                "returned": "已完结",
                "overdue": "已失效",
            },
            "archive_menu_admin": "事项管理",
            "archive_menu_user": "可办事项",
            "my_tickets_label": "我的申请",
            "pending_label": "人事审核",
            "records_label": "办理记录",
            "auth_eyebrow": "人事管理",
            "auth_lead": "验证码登录；浏览可办事项并提交申请，人事审核办理。",
            "auth_points": ["验证码登录", "事项浏览", "申请审核"],
            "register_hint": "注册后可办理人事事项",
            "notice_title": "人事须知",
            "notice_body": "请按流程提交材料；审核结果将站内通知。",
        }
    return {
        "user_label": "用户",
        "admin_label": "管理员（总管）",
        "subadmin_label": "审核员",
        "archive_label": noun,
        "archive_fields": [
            {"key": "title", "label": f"{noun}名称", "type": "string"},
            {"key": "author", "label": "摘要/责任人", "type": "string"},
            {"key": "isbn", "label": "编号/说明", "type": "string"},
            {"key": "category", "label": "分类", "type": "select"},
            {"key": "stock", "label": "可申请数", "type": "number"},
        ],
        "ticket_label": "申请单",
        "ticket_plural": "申请",
        "verbs": {
            "apply": "提交申请",
            "approve": "通过",
            "reject": "驳回",
            "return": "完结",
            "remind": "提醒",
        },
        "states": {
            "pending": "待审核",
            "approved": "进行中",
            "rejected": "已驳回",
            "returned": "已完结",
            "overdue": "已逾期",
        },
        "archive_menu_admin": f"{noun}管理",
        "archive_menu_user": f"{noun}检索",
        "my_tickets_label": "我的申请",
        "pending_label": "待审申请",
        "records_label": "申请记录",
        "auth_eyebrow": product_name_from_title(title),
        "auth_lead": f"验证码登录；浏览{noun}并办理相关业务。",
        "auth_points": ["验证码登录", f"{noun}检索", "业务办理"],
        "register_hint": "注册后即可使用",
        "notice_title": "办理须知",
        "notice_body": "请按菜单完成申请、预约或下单等操作。",
    }


def shell_runtime(archetype: str | None = None, archetypes: list[str] | None = None) -> dict[str, Any]:
    arches = normalize_archetypes(archetypes, primary=archetype)
    need_flow, need_trade, need_reserve = path_flags(arches)
    base: dict[str, Any] = {
        "register_role": "user",
        "archive_category_table": "category",
        "archive_item_table": "biz_item",
        "enable_ticket": False,
        "use_quota": False,
        "use_deadline": False,
    }
    if need_flow:
        base.update(
            {
                "enable_ticket": True,
                "ticket_mode": "archive",
                "ticket_table": "biz_ticket",
                "use_quota": "ARCH-CONTENT" not in arches or need_trade or len(arches) > 1,
                "use_deadline": False,
            }
        )
        if arches == ["ARCH-CONTENT"]:
            base["use_quota"] = False
    if need_trade:
        base.update(
            {
                "order_cart_table": "cart_line",
                "order_table": "biz_order",
                "order_line_table": "order_line",
                "use_quota": True,
            }
        )
    if need_reserve:
        base.update(
            {
                "slot_table": "resource_slot",
                "reservation_table": "reservation",
            }
        )
    return base


def _merge_gate_dicts(parts: list[dict[str, Any]]) -> dict[str, Any]:
    routes: list[dict] = []
    seen_seg: set[str] = set()
    files: list[str] = []
    seen_f: set[str] = set()
    flow_api: dict[str, Any] = {}
    inv: dict[str, Any] = {
        "require_super_auth": True,
        "master_kind": "archive",
        "master_menus": ["archive", "category"],
        "super_menus": ["users", "content", "archive", "category"],
    }
    for g in parts:
        for r in g.get("routes") or []:
            seg = r.get("seg")
            if seg and seg not in seen_seg:
                seen_seg.add(seg)
                routes.append(r)
        for f in g.get("files") or []:
            if f not in seen_f:
                seen_f.add(f)
                files.append(f)
        flow_api.update(g.get("flow_api") or {})
        ai = g.get("admin_invariants") or {}
        for k in ("master_menus", "super_menus"):
            if ai.get(k):
                inv[k] = list(dict.fromkeys(list(inv.get(k) or []) + list(ai[k])))
    return {
        "routes": routes,
        "files": files,
        "flow_api": flow_api,
        "admin_invariants": inv,
    }


def shell_gate(
    archetype: str | None = None,
    noun: str = "业务对象",
    archetypes: list[str] | None = None,
) -> dict[str, Any]:
    arches = normalize_archetypes(archetypes, primary=archetype)
    need_flow, need_trade, need_reserve = path_flags(arches)
    parts: list[dict[str, Any]] = []
    if need_flow:
        parts.append(
            gate_archive_ticket(
                archive_feature=f"{noun}检索",
                flow_feature="申请 → 审核",
                records_feature="业务记录",
                users_feature="用户管理",
                with_deadline=False,
            )
        )
    if need_trade and not need_reserve:
        parts.append(
            gate_order_shell(
                archive_feature=f"{noun}浏览",
                cart_feature="购物车下单",
                orders_feature="订单管理",
            )
        )
    if need_reserve:
        parts.append(
            gate_slot_shell(
                archive_feature=f"{noun}检索",
                reserve_feature="时段预约",
                with_orders=need_trade,
            )
        )
    if need_trade and need_reserve:
        # slot gate 已含 orders；补 cart 段
        parts.append(
            {
                "routes": [
                    {"seg": "cart", "from_feature": "购物车下单"},
                ],
                "files": [
                    "frontend/src/views/user/Cart.vue",
                ],
                "flow_api": {},
                "admin_invariants": {},
            }
        )
    if not parts:
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
    return _merge_gate_dicts(parts)


def shell_features(
    archetype: str | None = None,
    noun: str = "业务对象",
    archetypes: list[str] | None = None,
) -> list[dict[str, str]]:
    arches = normalize_archetypes(archetypes, primary=archetype)
    need_flow, need_trade, need_reserve = path_flags(arches)
    feats = [
        {"name": "登录", "status": "baseline"},
        {"name": "个人资料与头像", "status": "baseline"},
        {"name": "管理端工作台", "status": "module"},
        {"name": f"{noun}检索", "status": "domain"},
        {"name": "分类管理", "status": "module"},
        {"name": "用户管理", "status": "module"},
        {"name": "公告管理", "status": "module"},
    ]
    if need_flow:
        feats += [
            {"name": "申请 → 审核", "status": "flow"},
            {"name": "业务记录", "status": "module"},
        ]
    if need_trade:
        feats += [
            {"name": "购物车下单", "status": "flow"},
            {"name": "订单管理", "status": "flow"},
        ]
    if need_reserve:
        feats.append({"name": "时段预约", "status": "flow"})
    if not (need_flow or need_trade or need_reserve):
        feats.append({"name": f"{noun}管理", "status": "module"})
    return feats


def _ensure_menu(menus: list[dict], key: str, item: dict, *, before_key: str | None = None) -> None:
    if any(m.get("key") == key for m in menus):
        return
    if before_key:
        for i, m in enumerate(menus):
            if m.get("key") == before_key:
                menus.insert(i, item)
                return
    menus.append(item)


def _augment_menus_for_paths(schema: dict[str, Any], *, need_flow: bool, need_trade: bool, need_reserve: bool) -> None:
    admin = schema.setdefault("menus", {}).setdefault("admin", [])
    user = schema.setdefault("menus", {}).setdefault("user", [])
    if need_flow:
        _ensure_menu(user, "my_tickets", {"key": "my_tickets", "label": "我的申请"}, before_key="content")
        _ensure_menu(
            admin, "ticket_pending", {"key": "ticket_pending", "label": "待审申请"}, before_key="users"
        )
        _ensure_menu(
            admin, "ticket_records", {"key": "ticket_records", "label": "申请记录"}, before_key="users"
        )
    if need_trade:
        _ensure_menu(user, "cart", {"key": "cart", "label": "购物车"}, before_key="content")
        _ensure_menu(user, "my_orders", {"key": "my_orders", "label": "我的订单"}, before_key="content")
        # 收货地址：仅交易路径（点餐/商城同类），预约壳不挂
        _ensure_menu(user, "addresses", {"key": "addresses", "label": "收货地址"}, before_key="content")
        _ensure_menu(admin, "orders", {"key": "orders", "label": "订单管理"}, before_key="users")
    if need_reserve:
        _ensure_menu(user, "slots", {"key": "slots", "label": "时段预约"}, before_key="content")
        _ensure_menu(user, "my_reservations", {"key": "my_reservations", "label": "我的预约"}, before_key="content")
        _ensure_menu(admin, "reservations", {"key": "reservations", "label": "预约记录"}, before_key="users")


def build_generic_shell_schema(
    title: str,
    archetype: str | None = None,
    archetypes: list[str] | None = None,
) -> dict[str, Any]:
    """GENERIC + ARCH-*（可多条）→ 文案壳；菜单按路径并集补齐。"""
    from app.bake.schema_templates import _archive_ticket_schema, _order_shell_schema, _slot_shell_schema

    arches = normalize_archetypes(archetypes, primary=archetype)
    need_flow, need_trade, need_reserve = path_flags(arches)
    noun = entity_noun(title)
    caps = shell_capabilities(archetypes=arches)
    app = product_name_from_title(title)
    primary = arches[0]

    # 实体/文案：优先用「最重」单壳模板，再补菜单（避免三套 schema 复制）
    if need_flow:
        fc = _generic_flow_copy(title, noun)
        schema = _archive_ticket_schema(
            title,
            domain="DOM-GENERIC",
            user_role_id="user",
            user_label=fc["user_label"],
            admin_label=fc["admin_label"],
            subadmin_label=fc["subadmin_label"],
            archive_key="item",
            archive_label=fc["archive_label"],
            archive_plural=fc["archive_label"],
            archive_fields=fc["archive_fields"],
            ticket_key="ticket",
            ticket_label=fc["ticket_label"],
            ticket_plural=fc["ticket_plural"],
            verbs=fc["verbs"],
            states=fc["states"],
            archive_menu_admin=fc["archive_menu_admin"],
            archive_menu_user=fc["archive_menu_user"],
            users_menu="用户管理",
            auth_eyebrow=fc["auth_eyebrow"],
            auth_lead=fc["auth_lead"],
            auth_points=fc["auth_points"],
            register_hint=fc["register_hint"],
            notice_title=fc["notice_title"],
            notice_body=fc["notice_body"],
            notice_page_title="公告",
            my_tickets_label=fc["my_tickets_label"],
            pending_label=fc["pending_label"],
            records_label=fc["records_label"],
            with_deadline=False,
            stock_display="count",
            require_remark=bool(fc.get("require_remark")),
            remark_label=str(fc.get("remark_label") or "说明"),
            pick_date_range=bool(fc.get("pick_date_range")),
        )
    elif need_reserve:
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
                {"key": "author", "label": "费用(元)", "type": "number"},
                {"key": "isbn", "label": "位置/说明", "type": "string"},
                {"key": "category", "label": "分类", "type": "select"},
            ],
            archive_menu_admin=f"{noun}管理",
            archive_menu_user=f"选{noun}",
            users_menu="用户管理",
            my_resv_label="我的预约",
            resv_admin_label="预约记录",
            auth_eyebrow=app,
            auth_lead=f"验证码登录；选择{noun}办理预约等业务。",
            auth_points=["验证码登录", f"{noun}检索", "时段预约"],
            register_hint="注册后即可预约",
            notice_title="预约须知",
            notice_body="请按时使用；取消预约将释放时段名额。",
            notice_page_title="公告",
            with_orders=need_trade,
        )
    elif need_trade:
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
                {"key": "author", "label": "单价(元)", "type": "number"},
                {"key": "isbn", "label": "编号/说明", "type": "string"},
                {"key": "category", "label": "分类", "type": "select"},
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
    else:
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
                        {"key": "category", "label": "分类", "type": "select"},
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
                "messagesPageLead": "审核结果与系统通知。",
            },
            "seeds": {
                "noticeTitle": "系统公告",
                "noticeBody": f"{app}已就绪，可开始维护{noun}数据。",
            },
        }

    _augment_menus_for_paths(schema, need_flow=need_flow, need_trade=need_trade, need_reserve=need_reserve)
    points = list((schema.get("labels") or {}).get("authPoints") or [])
    if need_flow and "申请与审核" not in "".join(points):
        points.append("申请与审核")
    if need_trade and "订单" not in "".join(points):
        points.append("购物车与订单")
    if need_reserve and "预约" not in "".join(points):
        points.append("时段预约")
    schema.setdefault("labels", {})["authPoints"] = list(dict.fromkeys(points))[:5]
    schema["capabilities"] = caps
    schema["archetypes"] = arches
    schema["primaryArchetype"] = primary
    return schema


def apply_generic_shell(spec: dict[str, Any]) -> dict[str, Any]:
    """当 domain=DOM-GENERIC 时，按 archetypes 并集写入 runtime/gate/features/schema。"""
    if (spec.get("domain") or "") != "DOM-GENERIC":
        return spec
    spec = dict(spec)
    arches = normalize_archetypes(spec.get("archetypes"), primary=spec.get("archetype"))
    title = spec.get("title") or "毕设系统"
    noun = entity_noun(title)
    caps = shell_capabilities(archetypes=arches)
    primary = arches[0]
    spec["archetype"] = primary
    spec["archetypes"] = arches
    spec["archetype_label"] = "+".join(
        {
            "ARCH-CRUD": "纯管理",
            "ARCH-FLOW": "审核流",
            "ARCH-STOCK": "进销存",
            "ARCH-CONTENT": "内容流",
            "ARCH-TRADE": "交易流",
            "ARCH-RESERVE": "预约流",
        }.get(a, a)
        for a in arches
    )
    spec["capabilities"] = caps
    spec["runtime"] = shell_runtime(archetypes=arches)
    spec["gate"] = shell_gate(noun=noun, archetypes=arches)
    spec["features"] = shell_features(noun=noun, archetypes=arches)
    flow_bits = []
    if any(a in _FLOW_FAMILY for a in arches):
        flow_bits.append("提交申请 → 审核 → 完结")
    if "ARCH-TRADE" in arches:
        flow_bits.append("加购 → 下单 → 履约")
    if "ARCH-RESERVE" in arches:
        flow_bits.append("选资源 → 占坑预约 → 取消")
    if not flow_bits:
        flow_bits = ["新增 → 编辑 → 查询"]
    spec["flows"] = flow_bits
    spec["entities"] = [noun, "Category", "Notice"]
    spec["domain_label"] = product_name_from_title(title)
    spec["industry"] = spec["domain_label"]
    from app.bake.profile_fields import attach_profile_fields

    schema = build_generic_shell_schema(title, archetypes=arches)
    spec["schema"] = attach_profile_fields(schema, "DOM-GENERIC")
    return spec
