"""四类角色中的岗位：子管理(clerk) / 业务员工(worker)。全领域通用框架，岗位按域配置。"""

from __future__ import annotations

from typing import Any

# 办理岗：裁剪 Admin 菜单 key
PACK_ADMIN_MENUS: dict[str, frozenset[str]] = {
    "ticket_ops": frozenset({"dashboard", "ticket_pending", "ticket_records", "deadline"}),
    "order_ops": frozenset({"dashboard", "orders"}),
    "slot_ops": frozenset({"dashboard", "reservations"}),
    # 内容流编辑：维护档案与公告（无单据审核队列）
    "content_ops": frozenset({"dashboard", "archive", "content"}),
}

# 作业岗：员工端页面 id（前端路由用）
PACK_WORK_PAGES: dict[str, frozenset[str]] = {
    "ticket_work": frozenset({"tickets"}),
    "order_work": frozenset({"orders"}),
    "slot_work": frozenset({"slots"}),
}

CLERK_PACKS = frozenset(PACK_ADMIN_MENUS)
WORKER_PACKS = frozenset(PACK_WORK_PAGES)
ALL_PACKS = CLERK_PACKS | WORKER_PACKS


def _post(pid: str, label: str, kind: str, packs: list[str]) -> dict[str, Any]:
    return {"id": pid, "label": label, "kind": kind, "packs": list(packs)}


def _clerk(pid: str, label: str, *packs: str) -> dict[str, Any]:
    return _post(pid, label, "clerk", list(packs))


def _worker(pid: str, label: str, *packs: str) -> dict[str, Any]:
    return _post(pid, label, "worker", list(packs))


# 岗位按域配置：clerk / worker 均可选；无岗位 = 仅门户用户 + 总管
STAFF_POSTS_BY_DOMAIN: dict[str, list[dict[str, Any]]] = {
    "DOM-LIBRARY": [_clerk("librarian", "馆员", "ticket_ops")],
    "DOM-EQUIP": [_clerk("keeper", "器材管理员", "ticket_ops")],
    "DOM-ASSET": [_clerk("storekeeper", "库管员", "ticket_ops")],
    "DOM-CRM": [_clerk("account_mgr", "客户经理", "ticket_ops")],
    "DOM-DORM": [
        _clerk("dorm_mgr", "楼管", "ticket_ops"),
        _worker("repairer", "维修员", "ticket_work"),
    ],
    "DOM-PROPERTY": [
        _clerk("dispatcher", "物业调度", "ticket_ops"),
        _worker("repairer", "维修员", "ticket_work"),
    ],
    "DOM-IT": [_clerk("ops", "运维员", "ticket_ops")],
    "DOM-ACTIVITY": [_clerk("assistant", "活动助理", "ticket_ops")],
    "DOM-LOST": [_clerk("claim_clerk", "招领管理员", "ticket_ops")],
    "DOM-COURSE": [_clerk("course_clerk", "选课管理员", "ticket_ops")],
    "DOM-SHOP": [
        _clerk("order_clerk", "订单管理员", "order_ops"),
        _worker("picker", "拣货员", "order_work"),
    ],
    "DOM-FOOD": [
        _clerk("counter", "档口店员", "order_ops"),
        _worker("rider", "骑手", "order_work"),
    ],
    "DOM-HOSPITAL": [_clerk("registrar", "挂号员", "slot_ops")],
    "DOM-PARKING": [_clerk("lot_clerk", "车场管理员", "slot_ops")],
    "DOM-MEETING": [_clerk("booking_clerk", "预约管理员", "slot_ops")],
    "DOM-SALON": [
        _clerk("front", "前台", "slot_ops"),
        _worker("stylist", "技师", "slot_work"),
    ],
    "DOM-HOTEL": [
        _clerk("front", "前台", "slot_ops", "order_ops"),
        _worker("housekeeping", "客房服务", "slot_work"),
    ],
    "DOM-MEDIA": [_clerk("editor", "运营编辑", "content_ops")],
    "DOM-MUSIC": [_clerk("editor", "运营编辑", "content_ops")],
    "DOM-FORUM": [_clerk("moderator", "版主", "ticket_ops")],
    "DOM-BLOG": [_clerk("editor", "编辑", "content_ops")],
    "DOM-GENERIC": [_clerk("clerk", "业务办理员", "ticket_ops")],
}

# 门户身份强绑定（患者/车主/顾客等）：岗位靠种子账号，禁止把业务用户「任命」成岗
NO_APPOINT_FROM_USERS: frozenset[str] = frozenset({
    "DOM-HOSPITAL",
    "DOM-PARKING",
    "DOM-MEETING",
    "DOM-SALON",
    "DOM-HOTEL",
    "DOM-SHOP",
    "DOM-FOOD",
})

# schema.roles 元数据键 / 门户别名（与 user 同槽，禁止并列进 Spec）
_ROLE_META_KEYS = frozenset({"staff_posts", "allowAppointFromUsers"})
_PORTAL_ROLE_ALIASES = frozenset({"reader", "student", "patient", "buyer"})


def roles_for_spec(domain_roles: list | None, schema: dict | None) -> list[str]:
    """以 schema.roles 的 user/admin 为准；展开 staff_posts；去掉与 user 重复的门户别名。"""
    schema_roles = schema.get("roles") if isinstance(schema, dict) else None
    keys = list(schema_roles.keys()) if isinstance(schema_roles, dict) else []
    posts = schema_roles.get("staff_posts") if isinstance(schema_roles, dict) else None
    posts_declared = isinstance(posts, list)
    has_user_slot = isinstance(schema_roles, dict) and isinstance(
        schema_roles.get("user"), dict
    )
    out: list[str] = []
    for r in domain_roles or []:
        if not r:
            continue
        if posts_declared and str(r) == "subadmin":
            continue
        if has_user_slot and str(r) in _PORTAL_ROLE_ALIASES:
            continue
        if str(r) not in out:
            out.append(str(r))
    if posts_declared:
        for p in posts:
            if isinstance(p, dict) and p.get("id"):
                pid = str(p["id"])
                if pid not in out:
                    out.append(pid)
    for r in keys:
        if r in _ROLE_META_KEYS or r == "subadmin":
            continue
        val = schema_roles.get(r) if isinstance(schema_roles, dict) else None
        if not isinstance(val, dict):
            continue
        if r and r not in out:
            out.append(str(r))
    if not posts_declared and isinstance(schema_roles, dict) and "subadmin" in schema_roles:
        if "subadmin" not in out:
            out.append("subadmin")
    return out or ["user", "admin"]


def _generic_arch_flags(
    archetype: str | None = None,
    archetypes: list[str] | None = None,
) -> tuple[bool, bool, bool]:
    """GENERIC 按能力路径取岗位；交叉并集，不抄行业域的 worker。"""
    from app.bake.archetype_shells import path_flags

    return path_flags(list(archetypes or ([archetype] if archetype else ["ARCH-CRUD"])))


def allow_appoint_from_users(
    domain: str,
    archetype: str | None = None,
    archetypes: list[str] | None = None,
) -> bool:
    """是否允许把门户业务用户升为岗位；无岗位表时亦为 False。"""
    if domain in NO_APPOINT_FROM_USERS:
        return False
    if domain == "DOM-GENERIC":
        _flow, need_trade, need_reserve = _generic_arch_flags(archetype, archetypes)
        if need_trade or need_reserve:
            return False
    return bool(staff_posts_for_domain(domain, archetype, archetypes))


def staff_posts_for_domain(
    domain: str,
    archetype: str | None = None,
    archetypes: list[str] | None = None,
) -> list[dict[str, Any]]:
    if domain == "DOM-GENERIC":
        need_flow, need_trade, need_reserve = _generic_arch_flags(archetype, archetypes)
        posts: list[dict[str, Any]] = []
        # 按路径并集挂 clerk；配送员/骑手等 worker 只在具体行业域（FOOD/SHOP…）
        if need_flow:
            posts.append(_clerk("clerk", "业务办理员", "ticket_ops"))
        if need_trade:
            posts.append(_clerk("order_clerk", "订单办理员", "order_ops"))
        if need_reserve:
            posts.append(_clerk("booking_clerk", "预约办理员", "slot_ops"))
        if posts:
            return posts
        return [_clerk("operator", "业务员")]  # packs 空 → 仅工作台
    # 未登记域：默认无岗位（仅总管 + 门户），避免强塞子管理
    return list(STAFF_POSTS_BY_DOMAIN.get(domain) or [])


def validate_staff_posts(posts: list[dict[str, Any]]) -> list[str]:
    """返回错误列表；空列表合法（该项目无子管理/员工岗）。"""
    errs: list[str] = []
    if not posts:
        return errs
    ids: set[str] = set()
    for p in posts:
        if not isinstance(p, dict):
            errs.append("staff_post 须为对象")
            continue
        pid = str(p.get("id") or "").strip()
        kind = str(p.get("kind") or "").strip()
        label = str(p.get("label") or "").strip()
        packs = p.get("packs") or []
        if not pid:
            errs.append("staff_post 缺少 id")
        elif pid in ids:
            errs.append(f"重复 staff_post id: {pid}")
        else:
            ids.add(pid)
        if kind not in ("clerk", "worker"):
            errs.append(f"staff_post {pid}: kind 须为 clerk|worker")
        if not label:
            errs.append(f"staff_post {pid}: 缺少 label")
        if not isinstance(packs, list):
            errs.append(f"staff_post {pid}: packs 须为数组")
            continue
        allowed = CLERK_PACKS if kind == "clerk" else WORKER_PACKS
        for pk in packs:
            if pk not in ALL_PACKS:
                errs.append(f"staff_post {pid}: 未知 pack {pk}")
            elif pk not in allowed:
                errs.append(f"staff_post {pid}: pack {pk} 与 kind={kind} 不匹配")
    return errs


def attach_staff_posts(
    schema: dict[str, Any],
    domain: str,
    archetype: str | None = None,
    archetypes: list[str] | None = None,
) -> dict[str, Any]:
    """写入 roles.staff_posts；有 clerk 时同步 subadmin（兼容旧前端），否则去掉。"""
    posts = staff_posts_for_domain(domain, archetype, archetypes)
    for e in validate_staff_posts(posts):
        raise ValueError(f"{domain}: {e}")
    roles = dict(schema.get("roles") or {})
    roles["staff_posts"] = posts
    roles["allowAppointFromUsers"] = allow_appoint_from_users(
        domain, archetype, archetypes
    )
    clerks = [p for p in posts if p.get("kind") == "clerk"]
    if clerks:
        first = clerks[0]
        roles["subadmin"] = {
            "id": "subadmin",
            "label": first.get("label") or "经办员",
            "staffPostId": first.get("id"),
        }
    else:
        roles.pop("subadmin", None)
    schema["roles"] = roles
    schema["staffPackMenus"] = {k: sorted(v) for k, v in PACK_ADMIN_MENUS.items()}
    schema["staffPackPages"] = {k: sorted(v) for k, v in PACK_WORK_PAGES.items()}
    return schema


def domain_has_workers(
    domain: str,
    archetype: str | None = None,
    archetypes: list[str] | None = None,
) -> bool:
    return any(
        p.get("kind") == "worker"
        for p in staff_posts_for_domain(domain, archetype, archetypes)
    )


def append_staff_seed_sql(
    sql: str,
    domain: str,
    archetype: str | None = None,
    archetypes: list[str] | None = None,
) -> str:
    """幂等补岗位种子：首个 clerk 绑 subadmin；其余 clerk / 全部 worker 各一账号。"""
    posts = staff_posts_for_domain(domain, archetype, archetypes)
    clerks = [p for p in posts if p.get("kind") == "clerk"]
    workers = [p for p in posts if p.get("kind") == "worker"]
    if not clerks and not workers:
        return sql
    lines = [
        "",
        "-- staff posts (clerk / worker)",
        "UPDATE sys_user SET staff_post='', staff_kind='' WHERE super_admin=1;",
    ]
    phone_base = 13800000010
    phone_i = 0

    def _insert_staff(pid: str, label: str, kind: str) -> None:
        nonlocal phone_i
        safe = str(label or pid).replace("'", "''")
        pwd = f"{pid}123"
        phone = str(phone_base + phone_i)
        phone_i += 1
        lines.append(
            "INSERT INTO sys_user "
            "(username, password, role, nickname, phone, profile_json, "
            "super_admin, profile_editable, enabled, staff_post, staff_kind) "
            f"VALUES ('{pid}', '{pwd}', 'admin', '{safe}', '{phone}', '{{}}', "
            f"0, 1, 1, '{pid}', '{kind}') "
            "ON DUPLICATE KEY UPDATE nickname=VALUES(nickname), "
            "staff_post=VALUES(staff_post), staff_kind=VALUES(staff_kind), "
            "role='admin', super_admin=0;"
        )

    if clerks:
        c0 = clerks[0]
        cid = str(c0["id"])
        clabel = str(c0.get("label") or cid).replace("'", "''")
        lines.append(
            "UPDATE sys_user SET staff_post="
            f"'{cid}', staff_kind='clerk', nickname='{clabel}' "
            "WHERE username='subadmin' AND role='admin' AND IFNULL(super_admin,0)=0;"
        )
        for c in clerks[1:]:
            _insert_staff(str(c["id"]), str(c.get("label") or c["id"]), "clerk")
    for w in workers:
        _insert_staff(str(w["id"]), str(w.get("label") or w["id"]), "worker")
    return sql.rstrip() + "\n" + "\n".join(lines) + "\n"
