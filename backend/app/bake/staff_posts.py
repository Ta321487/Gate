"""四类角色中的岗位：子管理(clerk) / 业务员工(worker)。全领域通用框架，岗位按域配置。"""

from __future__ import annotations

from typing import Any

# 办理岗：裁剪 Admin 菜单 key
PACK_ADMIN_MENUS: dict[str, frozenset[str]] = {
    "ticket_ops": frozenset({"dashboard", "ticket_pending", "ticket_records", "deadline", "archive_logs"}),
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
    "DOM-EVENT": [_clerk("duty_clerk", "值班员", "ticket_ops")],
    "DOM-ATTEND": [_clerk("attend_clerk", "考勤员", "ticket_ops")],
    "DOM-RECRUIT": [_clerk("hr_clerk", "HR专员", "ticket_ops")],
    "DOM-GRADE": [_clerk("grade_clerk", "教务员", "ticket_ops")],
    "DOM-INTERN": [_clerk("intern_tutor", "实习辅导员", "ticket_ops")],
    "DOM-PARCEL": [_clerk("parcel_clerk", "驿站店员", "ticket_ops")],
    "DOM-DORM": [
        _clerk("dorm_mgr", "楼管", "ticket_ops"),
        # 维修员：默认不挂；开题写到才追加（与骑手/拣货同口径）
    ],
    "DOM-PROPERTY": [
        _clerk("dispatcher", "物业调度", "ticket_ops"),
        # 维修员：默认不挂；开题写到才追加
    ],
    "DOM-IT": [_clerk("ops", "运维员", "ticket_ops")],
    "DOM-ACTIVITY": [_clerk("assistant", "活动助理", "ticket_ops")],
    "DOM-LOST": [_clerk("claim_clerk", "招领管理员", "ticket_ops")],
    "DOM-COURSE": [_clerk("course_clerk", "选课管理员", "ticket_ops")],
    "DOM-SHOP": [
        _clerk("order_clerk", "订单管理员", "order_ops"),
        # 拣货员：默认不挂；开题写到才追加（见 _OPTIONAL_WORKERS）
    ],
    "DOM-FOOD": [
        _clerk("counter", "档口店员", "order_ops"),
        # 骑手：默认不挂；开题写到才追加
    ],
    "DOM-HOSPITAL": [_clerk("registrar", "挂号员", "slot_ops")],
    "DOM-PARKING": [_clerk("lot_clerk", "车场管理员", "slot_ops")],
    "DOM-MEETING": [_clerk("booking_clerk", "预约管理员", "slot_ops")],
    "DOM-SALON": [
        _clerk("front", "前台", "slot_ops"),
        # 技师：默认不挂；开题写到才追加（预约「偏好技师」文案仍可有，≠员工账号）
    ],
    "DOM-HOTEL": [
        _clerk("front", "前台", "slot_ops", "order_ops"),
        # 客房服务：默认不挂；开题写到才追加
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

# 可选 worker：默认不进岗位表；开题命中词才追加（keyword_mentioned，同 guestbook/loyalty）
# 现场岗易空挂：报修维修员 / 骑手 / 拣货 / 技师 / 客房 — 均开题写到才挂
_OPTIONAL_WORKERS: dict[str, list[tuple[dict[str, Any], tuple[str, ...]]]] = {
    "DOM-FOOD": [
        (
            _worker("rider", "骑手", "order_work"),
            ("骑手", "配送员", "外卖配送", "送餐上门", "配送到寝", "配送到宿舍"),
        ),
    ],
    "DOM-SHOP": [
        (
            _worker("picker", "拣货员", "order_work"),
            ("拣货员", "配货员", "仓库拣货", "拣配", "拣货", "配货"),
        ),
    ],
    "DOM-SALON": [
        (
            _worker("stylist", "技师", "slot_work"),
            ("发型师", "美发师", "美容师", "理发师", "造型师", "技师"),
        ),
    ],
    "DOM-HOTEL": [
        (
            _worker("housekeeping", "客房服务", "slot_work"),
            ("客房服务", "客房保洁", "客房打扫", "客房整理", "楼层服务员", "保洁员"),
        ),
    ],
    "DOM-DORM": [
        (
            _worker("repairer", "维修员", "ticket_work"),
            ("维修员", "维修师傅", "维修人员", "维修班组", "上门维修"),
        ),
    ],
    "DOM-PROPERTY": [
        (
            _worker("repairer", "维修员", "ticket_work"),
            ("维修员", "维修师傅", "维修人员", "维修班组", "上门维修"),
        ),
    ],
}


def _proposal_wants_any(proposal_text: str, hints: tuple[str, ...]) -> bool:
    from app.bake.proposal_lexicon import keyword_mentioned

    raw = proposal_text or ""
    return any(keyword_mentioned(raw, h) for h in hints)


def _pick_label_from_proposal(
    proposal_text: str,
    aliases: tuple[str, ...],
    *,
    min_len: int = 2,
) -> str | None:
    """开题正向命中的称呼原样作 label；按 aliases 声明顺序优先（非新匹配旁路）。"""
    raw = proposal_text or ""
    if not raw or not aliases:
        return None
    for alias in aliases:
        a = str(alias or "").strip()
        if len(a) < min_len:
            continue
        if _proposal_wants_any(raw, (a,)):
            return a[:24]
    return None


# 已挂岗位的显示名：开题写到的称呼原样替换目录默认（禁光杆「导师」等开题套话）
_POST_LABEL_ALIASES: dict[str, tuple[str, ...]] = {
    "intern_tutor": (
        "企业导师",
        "校内导师",
        "实习导师",
        "指导教师",
        "指导老师",
        "实习辅导员",
        "辅导员",
    ),
    "duty_clerk": (
        "随访员",
        "随访专员",
        "晨检员",
        "网格员",
        "流调员",
        "防控专员",
        "值班员",
        "卫生员",
    ),
    "attend_clerk": ("辅导员", "班主任", "考勤管理员", "考勤员"),
    "hr_clerk": ("招聘专员", "人事专员", "HR专员", "HR"),
    "grade_clerk": ("成绩管理员", "教务员", "任课教师"),
    "parcel_clerk": ("驿站管理员", "驿站店员", "取件员"),
    "dorm_mgr": ("宿舍管理员", "楼管", "宿管"),
    "dispatcher": ("物业管理员", "物业调度", "客服"),
    "counter": ("档口店员", "窗口服务员", "食堂窗口", "档口"),
    "order_clerk": ("订单管理员", "店铺管理员", "客服"),
    "front": ("前台接待", "前台", "接待员"),
    "registrar": ("挂号员", "导诊", "分诊台"),
    "librarian": ("图书管理员", "馆员"),
    "keeper": ("器材管理员", "器材员"),
    "storekeeper": ("库管员", "仓管"),
    "account_mgr": ("客户经理", "客户专员"),
    "ops": ("运维员", "运维工程师"),
    "assistant": ("活动助理", "活动管理员"),
    "claim_clerk": ("招领管理员", "失物管理员"),
    "course_clerk": ("选课管理员", "教务员"),
    "booking_clerk": ("预约管理员", "预约办理员"),
    "editor": ("运营编辑", "内容编辑", "编辑"),
    "moderator": ("版主", "论坛管理员"),
    "clerk": ("业务办理员", "经办员", "业务员"),
}

# 门户 user 槽：开题写到才替换（短泛词如「学生」不进表，避免开题套话误伤）
_USER_LABEL_ALIASES: dict[str, tuple[str, ...]] = {
    "DOM-INTERN": ("实习生", "实习学生"),
    "DOM-EVENT": ("随访对象", "上报人", "居民"),
    "DOM-FOOD": ("就餐用户", "就餐者"),
    "DOM-HOSPITAL": ("患者", "就诊人"),
    "DOM-PARKING": ("车主",),
    "DOM-RECRUIT": ("求职者", "应聘者"),
    "DOM-ATTEND": ("考勤对象", "员工"),
    "DOM-DORM": ("宿舍学生", "住户"),
    "DOM-PROPERTY": ("业主", "住户"),
}


def _catalog_default_label(domain: str, post_id: str) -> str | None:
    for p in STAFF_POSTS_BY_DOMAIN.get(domain) or []:
        if isinstance(p, dict) and str(p.get("id")) == post_id:
            lab = str(p.get("label") or "").strip()
            return lab or None
    for post, _hints in _OPTIONAL_WORKERS.get(domain) or []:
        if isinstance(post, dict) and str(post.get("id")) == post_id:
            lab = str(post.get("label") or "").strip()
            return lab or None
    return None


def food_wants_rider(proposal_text: str = "") -> bool:
    """兼容旧测试名；等价于 FOOD 可选骑手扫词。"""
    for post, hints in _OPTIONAL_WORKERS.get("DOM-FOOD") or []:
        if post.get("id") == "rider":
            return _proposal_wants_any(proposal_text, hints)
    return False


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
    *,
    proposal_text: str = "",
) -> bool:
    """是否允许把门户业务用户升为岗位；无岗位表时亦为 False。"""
    if domain in NO_APPOINT_FROM_USERS:
        return False
    if domain == "DOM-GENERIC":
        _flow, need_trade, need_reserve = _generic_arch_flags(archetype, archetypes)
        if need_trade or need_reserve:
            return False
    return bool(
        staff_posts_for_domain(
            domain, archetype, archetypes, proposal_text=proposal_text
        )
    )


def staff_posts_for_domain(
    domain: str,
    archetype: str | None = None,
    archetypes: list[str] | None = None,
    *,
    proposal_text: str = "",
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
        if not posts:
            posts = [_clerk("operator", "业务员")]  # packs 空 → 仅工作台
        return _apply_post_labels_from_proposal(posts, domain, proposal_text)
    posts = [dict(p) for p in (STAFF_POSTS_BY_DOMAIN.get(domain) or []) if isinstance(p, dict)]
    have = {str(p.get("id")) for p in posts if p.get("id")}
    for post, hints in _OPTIONAL_WORKERS.get(domain) or []:
        pid = str(post.get("id") or "")
        if not pid or pid in have:
            continue
        if _proposal_wants_any(proposal_text, hints):
            row = dict(post)
            # 可选岗：命中词里最长称呼作显示名（写「配送员」就显示配送员）
            picked = _pick_label_from_proposal(proposal_text, hints)
            if picked:
                row["label"] = picked
            posts.append(row)
            have.add(pid)
    return _apply_post_labels_from_proposal(posts, domain, proposal_text)


def _apply_post_labels_from_proposal(
    posts: list[dict[str, Any]],
    domain: str,
    proposal_text: str,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for p in posts:
        if not isinstance(p, dict) or not p.get("id"):
            continue
        row = dict(p)
        pid = str(row["id"])
        aliases = _POST_LABEL_ALIASES.get(pid) or ()
        picked = _pick_label_from_proposal(proposal_text, aliases)
        if picked:
            row["label"] = picked
        out.append(row)
    return out


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
    *,
    proposal_text: str = "",
) -> dict[str, Any]:
    """写入 roles.staff_posts；有 clerk 时同步 subadmin（兼容旧前端），否则去掉。

    开题扫到的称呼原样进 label；重绑时保留 Island/先前已定文案（勿被目录默认盖掉）。
    """
    prev_roles = dict(schema.get("roles") or {})
    prev_posts = {
        str(p.get("id")): p
        for p in (prev_roles.get("staff_posts") or [])
        if isinstance(p, dict) and p.get("id")
    }
    posts = staff_posts_for_domain(
        domain, archetype, archetypes, proposal_text=proposal_text
    )
    merged_posts: list[dict[str, Any]] = []
    for p in posts:
        row = dict(p)
        pid = str(row.get("id") or "")
        old = prev_posts.get(pid)
        old_lab = str((old or {}).get("label") or "").strip()
        new_lab = str(row.get("label") or "").strip()
        default_lab = _catalog_default_label(domain, pid) or ""
        # 开题未改 label（仍是目录默认）且先前已有非默认文案 → 保留先前
        if (
            old_lab
            and old_lab != new_lab
            and (not new_lab or new_lab == default_lab)
        ):
            row["label"] = old_lab
        merged_posts.append(row)
    for e in validate_staff_posts(merged_posts):
        raise ValueError(f"{domain}: {e}")
    roles = dict(prev_roles)
    roles["staff_posts"] = merged_posts
    roles["allowAppointFromUsers"] = allow_appoint_from_users(
        domain, archetype, archetypes, proposal_text=proposal_text
    )
    # 门户 user：开题写到才替换；否则保留 schema 原 label
    user_aliases = _USER_LABEL_ALIASES.get(domain) or ()
    user_picked = _pick_label_from_proposal(proposal_text, user_aliases)
    if user_picked and isinstance(roles.get("user"), dict):
        roles["user"] = {**roles["user"], "label": user_picked}
    clerks = [p for p in merged_posts if p.get("kind") == "clerk"]
    if clerks:
        first = clerks[0]
        prev_sub = prev_roles.get("subadmin") if isinstance(prev_roles.get("subadmin"), dict) else {}
        # 子管文案：优先本轮 clerk label；若 clerk 仍是默认且 subadmin 曾被 Island 改过则保留
        clerk_lab = str(first.get("label") or "").strip()
        default_clerk = _catalog_default_label(domain, str(first.get("id") or "")) or ""
        prev_sub_lab = str(prev_sub.get("label") or "").strip()
        if (
            prev_sub_lab
            and clerk_lab == default_clerk
            and prev_sub_lab != default_clerk
            and not _pick_label_from_proposal(
                proposal_text, _POST_LABEL_ALIASES.get(str(first.get("id") or ""), ())
            )
        ):
            sub_lab = prev_sub_lab
            # 与保留的子管文案对齐，避免 SQL 种子 nickname 再盖回目录默认
            for p in merged_posts:
                if p.get("id") == first.get("id"):
                    p["label"] = sub_lab
                    break
        else:
            sub_lab = clerk_lab or prev_sub_lab or "经办员"
        roles["subadmin"] = {
            "id": "subadmin",
            "label": sub_lab,
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
    *,
    proposal_text: str = "",
) -> bool:
    return any(
        p.get("kind") == "worker"
        for p in staff_posts_for_domain(
            domain, archetype, archetypes, proposal_text=proposal_text
        )
    )


def append_staff_seed_sql(
    sql: str,
    domain: str,
    archetype: str | None = None,
    archetypes: list[str] | None = None,
    *,
    proposal_text: str = "",
    posts: list[dict[str, Any]] | None = None,
) -> str:
    """幂等补岗位种子：首个 clerk 绑 subadmin；其余 clerk / 全部 worker 各一账号。

    posts 优先用 schema.roles.staff_posts（含开题/Island 文案）；缺省再按域+开题合成。
    """
    if isinstance(posts, list) and posts:
        use_posts = [dict(p) for p in posts if isinstance(p, dict) and p.get("id")]
    else:
        use_posts = staff_posts_for_domain(
            domain, archetype, archetypes, proposal_text=proposal_text
        )
    clerks = [p for p in use_posts if p.get("kind") == "clerk"]
    workers = [p for p in use_posts if p.get("kind") == "worker"]
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
