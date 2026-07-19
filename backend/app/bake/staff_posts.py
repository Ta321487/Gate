"""四类角色中的岗位：子管理(clerk) / 业务员工(worker)。全领域通用框架，岗位按域配置。"""

from __future__ import annotations

from typing import Any

# 办理岗：裁剪 Admin 菜单 key
PACK_ADMIN_MENUS: dict[str, frozenset[str]] = {
    "ticket_ops": frozenset({"dashboard", "ticket_pending", "ticket_records", "deadline"}),
    "order_ops": frozenset({"dashboard", "orders"}),
    "slot_ops": frozenset({"dashboard", "reservations"}),
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
    "DOM-MEDIA": [_clerk("editor", "运营编辑", "ticket_ops")],
    "DOM-MUSIC": [_clerk("editor", "运营编辑", "ticket_ops")],
    "DOM-FORUM": [_clerk("moderator", "版主", "ticket_ops")],
    "DOM-BLOG": [_clerk("editor", "编辑", "ticket_ops")],
    "DOM-GENERIC": [_clerk("clerk", "业务办理员", "ticket_ops")],
}


def staff_posts_for_domain(domain: str, archetype: str | None = None) -> list[dict[str, Any]]:
    if domain == "DOM-GENERIC":
        arch = (archetype or "ARCH-CRUD").upper()
        if "TRADE" in arch:
            return [
                _clerk("order_clerk", "订单办理员", "order_ops"),
                _worker("rider", "配送员", "order_work"),
            ]
        if "RESERVE" in arch:
            return [_clerk("booking_clerk", "预约办理员", "slot_ops")]
        if "FLOW" in arch or "STOCK" in arch or "CONTENT" in arch:
            return [_clerk("clerk", "业务办理员", "ticket_ops")]
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


def attach_staff_posts(schema: dict[str, Any], domain: str, archetype: str | None = None) -> dict[str, Any]:
    """写入 roles.staff_posts；有 clerk 时同步 subadmin（兼容旧前端），否则去掉。"""
    posts = staff_posts_for_domain(domain, archetype)
    for e in validate_staff_posts(posts):
        raise ValueError(f"{domain}: {e}")
    roles = dict(schema.get("roles") or {})
    roles["staff_posts"] = posts
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


def domain_has_workers(domain: str, archetype: str | None = None) -> bool:
    return any(p.get("kind") == "worker" for p in staff_posts_for_domain(domain, archetype))


def append_staff_seed_sql(sql: str, domain: str, archetype: str | None = None) -> str:
    """幂等补岗位种子：有 clerk 则绑定 subadmin；worker 岗各一账号；无岗位则跳过。"""
    posts = staff_posts_for_domain(domain, archetype)
    clerks = [p for p in posts if p.get("kind") == "clerk"]
    workers = [p for p in posts if p.get("kind") == "worker"]
    if not clerks and not workers:
        return sql
    lines = [
        "",
        "-- staff posts (clerk / worker)",
        "UPDATE sys_user SET staff_post='', staff_kind='' WHERE super_admin=1;",
    ]
    if clerks:
        c0 = clerks[0]
        cid = str(c0["id"])
        clabel = str(c0.get("label") or cid).replace("'", "''")
        lines.append(
            "UPDATE sys_user SET staff_post="
            f"'{cid}', staff_kind='clerk', nickname='{clabel}' "
            "WHERE username='subadmin' AND role='admin' AND IFNULL(super_admin,0)=0;"
        )
    phone_base = 13800000010
    for i, w in enumerate(workers):
        wid = str(w["id"])
        wlabel = str(w.get("label") or wid).replace("'", "''")
        pwd = f"{wid}123"
        phone = str(phone_base + i)
        lines.append(
            "INSERT INTO sys_user "
            "(username, password, role, nickname, phone, profile_json, "
            "super_admin, profile_editable, enabled, staff_post, staff_kind) "
            f"VALUES ('{wid}', '{pwd}', 'admin', '{wlabel}', '{phone}', '{{}}', "
            f"0, 1, 1, '{wid}', 'worker') "
            "ON DUPLICATE KEY UPDATE nickname=VALUES(nickname), "
            "staff_post=VALUES(staff_post), staff_kind=VALUES(staff_kind), "
            "role='admin', super_admin=0;"
        )
    return sql.rstrip() + "\n" + "\n".join(lines) + "\n"
