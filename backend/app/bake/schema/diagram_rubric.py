"""论文图老师 rubric 确定性闸：结构 ⊆ 包 / 可复现规矩；红则禁可交导出。

真源：docs/thesis-diagram-export.md §4。LLM 不进本模块。
"""

from __future__ import annotations

from typing import Any

_SEQ_SLOTS = ("actor", "page", "controller", "db")
_ACT_LANES = ("user", "system", "db")


def _finding(
    level: str,
    msg: str,
    *,
    where: str,
    fix: str = "",
    goto: str = "",
) -> dict[str, str]:
    row: dict[str, str] = {"level": level, "msg": str(msg)[:240], "where": where}
    if fix:
        row["fix"] = str(fix)[:160]
    if goto:
        row["goto"] = str(goto)[:64]
    return row


def _menu_key_set(menus: dict[str, Any], side: str) -> set[str]:
    raw = menus.get(side) or []
    keys: set[str] = set()
    if not isinstance(raw, list):
        return keys
    for item in raw:
        if isinstance(item, dict) and item.get("key"):
            keys.add(str(item.get("key")).strip())
        elif isinstance(item, str) and item.strip():
            keys.add(item.strip())
    return keys


def _is_auth_like_case(case: dict[str, Any]) -> bool:
    """登录/注册不是交付菜单项，不得报「不在菜单」。"""
    source = str(case.get("source") or "").lower()
    kind = str(case.get("kind") or "").lower()
    key = str(case.get("menu_key") or "").strip().lower()
    if "auth" in source or kind.startswith("auth_"):
        return True
    return key in ("auth", "login", "register")


def _clean_actor_lab(lab: str) -> str:
    s = str(lab or "").strip()
    if not s:
        return ""
    # 去括号说明，与 usecase_descriptions._clean_role_lab 同口径
    import re

    return re.sub(r"[（(][^）)]*[）)]", "", s).strip()


def _staff_post_menu_keys(
    roles: dict[str, Any],
    menus: dict[str, Any],
    *,
    actor_label: str,
) -> set[str] | None:
    """若执行者对应某 staff_post，返回该岗 pack ∩ admin 菜单；否则 None。

    有 staff_posts 时 menus.subadmin 常为空，办理岗走 admin 菜单裁剪，不得再按 subadmin 空表误杀。
    """
    lab = _clean_actor_lab(actor_label)
    if not lab:
        return None
    posts = roles.get("staff_posts") if isinstance(roles.get("staff_posts"), list) else []
    if not posts:
        return None
    try:
        from app.bake.staff_posts import PACK_ADMIN_MENUS
    except Exception:
        return None
    admin_keys = _menu_key_set(menus, "admin")
    for p in posts:
        if not isinstance(p, dict):
            continue
        plab = _clean_actor_lab(str(p.get("label") or ""))
        if not plab or plab != lab:
            continue
        allowed: set[str] = set()
        for pk in p.get("packs") or []:
            if isinstance(pk, str) and pk.strip() in PACK_ADMIN_MENUS:
                allowed |= set(PACK_ADMIN_MENUS[pk.strip()])
        # 办理岗实际可进 = pack ∩ 已交付 admin（dashboard 可放宽）
        return {k for k in allowed if k == "dashboard" or k in admin_keys}
    return None


def _actor_menu_mismatch(
    *,
    actor: str,
    menu_key: str,
    side: str,
    menus: dict[str, Any],
    roles: dict[str, Any],
    title: str,
    where: str,
    fix: str,
    goto: str,
) -> dict[str, str] | None:
    """执行者 ↔ 交付菜单不一致时返回 finding；一致或无法判定则 None。"""
    if not actor or not menu_key or not menus:
        return None
    post_keys = _staff_post_menu_keys(roles, menus, actor_label=actor)
    if post_keys is not None:
        if menu_key in post_keys:
            return None
        return _finding(
            "error",
            f"「{title}」以「{actor}」为执行者使用 {menu_key}，"
            f"但该办理岗 pack 与交付 admin 菜单的交集未含该项",
            where=where,
            fix=fix,
            goto=goto,
        )
    sub = roles.get("subadmin") if isinstance(roles.get("subadmin"), dict) else {}
    sub_lab = _clean_actor_lab(str(sub.get("label") or ""))
    if sub_lab and actor == sub_lab and menu_key not in _menu_key_set(menus, "subadmin"):
        return _finding(
            "error",
            f"「{title}」以「{actor}」为执行者使用 {menu_key}，"
            f"但交付的 subadmin（{sub_lab}）菜单未含该项，与交付角色菜单不一致",
            where=where,
            fix=fix,
            goto=goto,
        )
    # 普通侧：menu_key 须在 side 菜单
    side_n = (side or "user").strip() or "user"
    if menu_key not in _menu_key_set(menus, side_n):
        present = [
            s
            for s in ("user", "admin", "subadmin", "staff")
            if menu_key in _menu_key_set(menus, s)
        ]
        if present:
            msg = (
                f"「{title}」使用 menu_key={menu_key}（侧 {side_n}），"
                f"但该 key 不在 {side_n} 交付菜单，而在 {'/'.join(present)}"
            )
        else:
            msg = (
                f"「{title}」使用 menu_key={menu_key}，"
                f"交付的 {side_n} 菜单未包含该项"
            )
        return _finding("error", msg, where=where, fix=fix, goto=goto)
    return None


def audit_er_rubric(
    model: dict[str, Any] | None,
    *,
    mode: str | None = None,
    entity: str | None = None,
) -> list[dict[str, str]]:
    """E-R：总图概念实体清单；分图自身属性不得含 FK。"""
    model = model if isinstance(model, dict) else {}
    findings: list[dict[str, str]] = []
    mode_n = (mode or model.get("er_mode") or "total").strip().lower()
    if mode_n not in ("total", "part"):
        mode_n = "total"

    tables = [t for t in (model.get("tables") or []) if isinstance(t, dict) and t.get("name")]
    conceptual = [
        str(x).strip()
        for x in (model.get("conceptual_entities") or [])
        if str(x).strip()
    ]
    by_name = {str(t.get("name")): t for t in tables}

    if mode_n == "total":
        if tables and not conceptual:
            findings.append(
                _finding(
                    "error",
                    "E-R 总图缺 conceptual_entities（概念实体清单为空）",
                    where="er.conceptual_entities",
                )
            )
        for name in conceptual:
            t = by_name.get(name)
            if not t:
                findings.append(
                    _finding(
                        "error",
                        f"概念实体「{name}」不在 tables 中",
                        where=f"er.entity.{name}",
                    )
                )
                continue
            if t.get("assoc_link"):
                findings.append(
                    _finding(
                        "error",
                        f"纯 M:N 中间表「{name}」不应进概念实体/属性图清单",
                        where=f"er.entity.{name}",
                    )
                )
        # 张数口径：非 assoc、非 role_of 的表应能出属性图
        expect_parts = [
            str(t.get("name"))
            for t in tables
            if not t.get("assoc_link") and not t.get("role_of")
        ]
        missing = [n for n in expect_parts if n not in set(conceptual)]
        if missing and conceptual:
            findings.append(
                _finding(
                    "warn",
                    f"有 {len(missing)} 张可属性图表未进 conceptual_entities（如 {missing[0]}）",
                    where="er.conceptual_entities",
                )
            )
        return findings

    # part
    ent = (entity or str(model.get("er_entity") or "")).strip()
    if not ent:
        findings.append(
            _finding("error", "实体属性图未指定实体", where="er.entity")
        )
        return findings
    t = by_name.get(ent)
    if not t:
        findings.append(
            _finding("error", f"实体属性图实体「{ent}」不在 schema", where=f"er.entity.{ent}")
        )
        return findings
    if t.get("assoc_link"):
        findings.append(
            _finding(
                "error",
                f"中间表「{ent}」不应出实体属性图",
                where=f"er.entity.{ent}",
            )
        )
    for c in t.get("own_columns") or []:
        if isinstance(c, dict) and c.get("fk"):
            findings.append(
                _finding(
                    "error",
                    f"实体属性图 own_columns 含外键列 {c.get('name')}（老师：只画自身属性）",
                    where=f"er.part.{ent}",
                )
            )
    # 若无 own_columns，导出会滤 fk；但 columns 里标了 fk 的不得被误当自身属性名集合
    own = t.get("own_columns")
    if isinstance(own, list) and own:
        for c in own:
            if not isinstance(c, dict):
                continue
            name = str(c.get("name") or "").strip()
            if not name:
                continue
            # 对照全量 columns：同名且 fk=True 则 own 污染
            for full in t.get("columns") or []:
                if (
                    isinstance(full, dict)
                    and str(full.get("name") or "") == name
                    and full.get("fk")
                ):
                    findings.append(
                        _finding(
                            "error",
                            f"实体属性图把外键列 {name} 收进自身属性",
                            where=f"er.part.{ent}",
                        )
                    )
                    break
    return findings


def audit_sequence_rubric(model: dict[str, Any] | None) -> list[dict[str, str]]:
    """序列图：每张须四槽位；消息端点 ∈ 参与者；有交付菜单时核对执行者侧。"""
    model = model if isinstance(model, dict) else {}
    findings: list[dict[str, str]] = []
    diagrams = [d for d in (model.get("diagrams") or []) if isinstance(d, dict)]
    _seq_fix = "论文材料 → 系统设计 → 系统序列图"
    _seq_goto = "sequence"
    if not diagrams:
        findings.append(
            _finding(
                "error",
                "序列图无 diagrams",
                where="sequence.diagrams",
                fix=_seq_fix,
                goto=_seq_goto,
            )
        )
        return findings

    menus_raw = model.get("delivery_menus")
    if not isinstance(menus_raw, dict):
        menus_raw = model.get("menus") if isinstance(model.get("menus"), dict) else {}
    menus: dict[str, Any] = menus_raw if isinstance(menus_raw, dict) else {}
    roles = model.get("roles") if isinstance(model.get("roles"), dict) else {}

    for d in diagrams:
        idx = d.get("index", "?")
        where = f"sequences[{idx}]"
        parts = [p for p in (d.get("participants") or []) if isinstance(p, dict)]
        ids = {str(p.get("id") or "") for p in parts if p.get("id")}
        for slot in _SEQ_SLOTS:
            if slot not in ids:
                findings.append(
                    _finding(
                        "error",
                        f"序列图缺四槽位「{slot}」",
                        where=where,
                        fix=_seq_fix,
                        goto=_seq_goto,
                    )
                )
        for m in d.get("messages") or []:
            if not isinstance(m, dict):
                continue
            frm = str(m.get("from") or "")
            to = str(m.get("to") or "")
            if frm and frm not in ids:
                findings.append(
                    _finding(
                        "error",
                        f"消息 from={frm} 不在参与者中",
                        where=where,
                        fix=_seq_fix,
                        goto=_seq_goto,
                    )
                )
            if to and to not in ids:
                findings.append(
                    _finding(
                        "error",
                        f"消息 to={to} 不在参与者中",
                        where=where,
                        fix=_seq_fix,
                        goto=_seq_goto,
                    )
                )
            text = str(m.get("text") or "").strip()
            if not text:
                findings.append(
                    _finding(
                        "warn",
                        "存在空消息文案",
                        where=where,
                        fix=_seq_fix,
                        goto=_seq_goto,
                    )
                )

        menu_key = str(d.get("menu_key") or "").strip()
        side = str(d.get("side") or "user").strip() or "user"
        actor = _clean_actor_lab(str(d.get("actor_label") or ""))
        title = str(d.get("figure_title") or "").strip() or f"序列图[{idx}]"
        kind = str(d.get("kind") or "")

        # 评价菜单却订单操作文案占优 → 规则红（不依赖交付 menus；不靠 LLM）
        is_review = (
            "review" in menu_key.lower()
            or "review" in kind.lower()
            or ("评价" in title and "登录" not in title)
        )
        if is_review:
            texts = [
                str(m.get("text") or "")
                for m in (d.get("messages") or [])
                if isinstance(m, dict)
            ]
            orderish = sum(
                1
                for t in texts
                if ("订单" in t and "评价" not in t)
                or t in ("提交订单", "保存订单信息", "分页查询订单", "选择订单")
            )
            reviewish = sum(
                1
                for t in texts
                if ("评价" in t or "评论" in t) and "订单" not in t
            )
            if orderish >= 2 and orderish > reviewish:
                findings.append(
                    _finding(
                        "error",
                        f"图题「{title}」为评价流程，但消息多为订单操作文案，"
                        f"与 menu_key={menu_key or kind} 不符",
                        where=where,
                        fix=_seq_fix,
                        goto=_seq_goto,
                    )
                )

        # 执行者 / 菜单侧对齐（有 staff_posts 时按岗 pack，不误杀空 subadmin）
        if not menus:
            continue
        if not menu_key or _is_auth_like_case(
            {"menu_key": menu_key, "kind": kind, "source": str(d.get("source") or "")}
        ):
            continue
        bad = _actor_menu_mismatch(
            actor=actor,
            menu_key=menu_key,
            side=side,
            menus=menus,
            roles=roles,
            title=title,
            where=where,
            fix=_seq_fix,
            goto=_seq_goto,
        )
        if bad:
            findings.append(bad)

    # 材料缺词：有句式形状但材料没给实体/动作词 → 图内降级骨架，去资产台补词
    for gap in (model.get("material_gaps") or [])[:6]:
        if not isinstance(gap, dict):
            continue
        findings.append(
            _finding(
                "warn",
                f"材料缺词：{gap.get('reason') or '实体/动作词为空'}",
                where=f"sequences[{gap.get('index', '?')}].material",
                fix="资产台 → 实体动作词（factory_diagram_verb）补词，或补材料 entities.verbs",
                goto="diagram_verbs",
            )
        )
    return findings


def audit_activity_rubric(model: dict[str, Any] | None) -> list[dict[str, str]]:
    """活动图：须覆盖用户/控制器/数据库泳道（键 user/system/db）；有起止。"""
    from app.bake.schema.activity import (
        audit_activity_edges,
        audit_activity_labels,
        audit_activity_nodes,
    )

    model = model if isinstance(model, dict) else {}
    findings: list[dict[str, str]] = []
    diagrams = [d for d in (model.get("diagrams") or []) if isinstance(d, dict)]
    if not diagrams:
        findings.append(
            _finding("error", "活动图无 diagrams", where="activity.diagrams")
        )
        return findings
    for d in diagrams:
        idx = d.get("index", "?")
        where = f"activity[{idx}]"
        nodes = [n for n in (d.get("nodes") or []) if isinstance(n, dict)]
        lanes = {str(n.get("lane") or "") for n in nodes if n.get("lane")}
        for lane in _ACT_LANES:
            if lane not in lanes:
                findings.append(
                    _finding(
                        "error",
                        f"活动图缺泳道「{lane}」",
                        where=where,
                    )
                )
        kinds = {str(n.get("kind") or "") for n in nodes}
        if "start" not in kinds:
            findings.append(_finding("error", "活动图缺开始节点", where=where))
        if "end" not in kinds:
            findings.append(_finding("error", "活动图缺结束节点", where=where))
        # 版面几何：是/否 与判断条件不压线、不出泳道；折线不穿节点框
        svg = str(d.get("svg") or "")
        if svg:
            for msg in audit_activity_labels(svg)[:3]:
                findings.append(
                    _finding(
                        "warn",
                        f"活动图标签压线：{msg}",
                        where=f"{where}.svg",
                        fix="重出图（activity.py 标签锚点/避让）",
                        goto="activities",
                    )
                )
            for msg in audit_activity_edges(svg)[:3]:
                findings.append(
                    _finding(
                        "warn",
                        f"活动图连线穿框：{msg}",
                        where=f"{where}.svg",
                        fix="重出图（activity.py 回边折点）",
                        goto="activities",
                    )
                )
            for msg in audit_activity_nodes(svg)[:3]:
                findings.append(
                    _finding(
                        "warn",
                        f"活动图节点跨泳道：{msg}",
                        where=f"{where}.svg",
                        fix="重出图（activity.py 节点/泳道自适应宽）",
                        goto="activities",
                    )
                )
    return findings


def audit_usecase_desc_rubric(model: dict[str, Any] | None) -> list[dict[str, str]]:
    """用例描述表：默认张数、表题后缀、步骤/菜单对齐。

    有 ``delivery_menus``（或 ``menus``）时，**穷尽**核对每条用例的 menu_key
    与执行者侧交付菜单，一次列全，不依赖 LLM。
    """
    model = model if isinstance(model, dict) else {}
    findings: list[dict[str, str]] = []
    cases = [c for c in (model.get("cases") or []) if isinstance(c, dict)]
    requested = int(model.get("requested_count") or 4)
    cand_n = int(model.get("candidate_count") or 0)
    count = int(model.get("count") or len(cases))
    _ucd_fix = "论文材料 → 需求分析 → 用例描述表 → 手调文字 / 重选主路径"
    _ucd_goto = "usecase_desc"
    if cand_n >= requested and count < requested:
        findings.append(
            _finding(
                "error",
                f"用例描述表应有 {requested} 个主路径，实际 {count}",
                where="usecase_desc.count",
                fix=_ucd_fix,
                goto=_ucd_goto,
            )
        )
    if count == 0:
        findings.append(
            _finding(
                "error",
                "用例描述表无用例",
                where="usecase_desc.cases",
                fix=_ucd_fix,
                goto=_ucd_goto,
            )
        )
    md = str(model.get("markdown") or "")
    if cases and "用例描述表" not in md:
        findings.append(
            _finding(
                "error",
                "用例描述表 Markdown 缺「用例描述表」表题后缀",
                where="usecase_desc.markdown",
                fix=_ucd_fix,
                goto=_ucd_goto,
            )
        )

    menus_raw = model.get("delivery_menus")
    if not isinstance(menus_raw, dict):
        menus_raw = model.get("menus") if isinstance(model.get("menus"), dict) else {}
    menus: dict[str, Any] = menus_raw if isinstance(menus_raw, dict) else {}
    roles = model.get("roles") if isinstance(model.get("roles"), dict) else {}

    for i, c in enumerate(cases):
        name = str(c.get("name") or "").strip()
        where = f"usecase_desc[{i}]"
        if name and f"（{i + 1}）" not in md and f"({i + 1})" not in md:
            # 正文引用句：（1）xxx …见表
            findings.append(
                _finding(
                    "warn",
                    f"Markdown 可能缺序号引用 （{i + 1}）",
                    where=where,
                    fix=_ucd_fix,
                    goto=_ucd_goto,
                )
            )
        flow = c.get("flow") or []
        if not flow:
            findings.append(
                _finding(
                    "error",
                    f"用例「{name or i}」缺基本事件流",
                    where=where,
                    fix=_ucd_fix,
                    goto=_ucd_goto,
                )
            )
        menu_key = str(c.get("menu_key") or "").strip()
        source = str(c.get("source") or "")
        side = str(c.get("side") or "").strip() or "user"
        actor = _clean_actor_lab(str(c.get("actor") or ""))
        if not menu_key and source not in ("auth", "profile", "builtin") and not _is_auth_like_case(c):
            findings.append(
                _finding(
                    "error",
                    f"用例「{name or i}」无 menu_key，无法对交付菜单",
                    where=where,
                    fix=_ucd_fix,
                    goto=_ucd_goto,
                )
            )
            continue
        if not menus or not menu_key or _is_auth_like_case(c):
            continue
        # 办理岗写在 admin 菜单上：按 staff_posts pack 校验，勿用空 subadmin 误杀
        if side == "admin" and _staff_post_menu_keys(roles, menus, actor_label=actor) is not None:
            bad = _actor_menu_mismatch(
                actor=actor,
                menu_key=menu_key,
                side=side,
                menus=menus,
                roles=roles,
                title=f"用例描述「{name or i}」",
                where=where,
                fix=_ucd_fix,
                goto=_ucd_goto,
            )
            if bad:
                findings.append(bad)
            continue
        side_keys = _menu_key_set(menus, side)
        if menu_key not in side_keys:
            present = [
                s
                for s in ("user", "admin", "subadmin", "staff")
                if menu_key in _menu_key_set(menus, s)
            ]
            if present:
                msg = (
                    f"用例描述「{name or i}」使用 menu_key={menu_key}（执行者侧 {side}），"
                    f"但该 key 不在 {side} 交付菜单中，而在 {'/'.join(present)} 菜单下"
                )
            else:
                msg = (
                    f"用例描述「{name or i}」使用 menu_key={menu_key}，"
                    f"交付的 {side} 菜单未包含该项（写了交付菜单没有的操作）"
                )
            findings.append(
                _finding(
                    "error",
                    msg,
                    where=where,
                    fix=_ucd_fix,
                    goto=_ucd_goto,
                )
            )
            continue
        bad = _actor_menu_mismatch(
            actor=actor,
            menu_key=menu_key,
            side=side,
            menus=menus,
            roles=roles,
            title=f"用例描述「{name or i}」",
            where=where,
            fix=_ucd_fix,
            goto=_ucd_goto,
        )
        if bad:
            findings.append(bad)
    return findings


def audit_class_rubric(model: dict[str, Any] | None) -> list[dict[str, str]]:
    """类图：关系端点必须落在 classes。"""
    model = model if isinstance(model, dict) else {}
    findings: list[dict[str, str]] = []
    classes = [c for c in (model.get("classes") or []) if isinstance(c, dict) and c.get("id")]
    ids = {str(c.get("id")) for c in classes}
    if not classes:
        findings.append(_finding("error", "类图无 classes", where="classes"))
        return findings
    for i, a in enumerate(model.get("associations") or []):
        if not isinstance(a, dict):
            continue
        frm = str(a.get("from") or a.get("source") or "")
        to = str(a.get("to") or a.get("target") or "")
        where = f"classes.assoc[{i}]"
        if frm and frm not in ids:
            findings.append(
                _finding("error", f"关系 from={frm} 不在类集合", where=where)
            )
        if to and to not in ids:
            findings.append(
                _finding("error", f"关系 to={to} 不在类集合", where=where)
            )
    return findings


def audit_usecase_rubric(model: dict[str, Any] | None) -> list[dict[str, str]]:
    """用例图：须有角色与至少一个一级用例；include 不得串业务家族。"""
    model = model if isinstance(model, dict) else {}
    findings: list[dict[str, str]] = []
    _uc_fix = "论文材料 → 需求分析 → 用例图"
    _uc_goto = "usecase"
    actor = model.get("actor") if isinstance(model.get("actor"), dict) else {}
    if not actor.get("id"):
        findings.append(_finding("error", "用例图缺角色", where="usecase.actor"))
    level1 = [u for u in (model.get("level1") or []) if isinstance(u, dict) and u.get("id")]
    if not level1:
        findings.append(
            _finding("error", "用例图无一级用例", where="usecase.level1")
        )
    try:
        from app.bake.schema.modules import _biz_id_for_item
    except Exception:
        _biz_id_for_item = None  # type: ignore[assignment]
    # 支付扩展允许挂在订单；其它 include 的 menu_keys 须与父用例主 biz 同族
    _cross_ok = frozenset({("order", "order"), ("cart", "cart")})
    for u in level1:
        lab = str(u.get("label") or "").strip()
        if not lab:
            findings.append(
                _finding(
                    "error",
                    f"用例 {u.get('id')} 缺显示名",
                    where=f"usecase.{u.get('id')}",
                )
            )
        if _biz_id_for_item is None:
            continue
        parent_keys: list[str] = []
        kids = [k for k in (u.get("includes") or []) if isinstance(k, dict)]
        for k in kids:
            for mk in k.get("menu_keys") or []:
                if mk:
                    parent_keys.append(str(mk))
        parent_bizs = {_biz_id_for_item(k) for k in parent_keys if k}
        # 父级主 biz：出现最多的；排除 pay 扩展标签
        for k in kids:
            kid_lab = str(k.get("label") or "")
            if kid_lab == "进行支付":
                continue
            mks = [str(x) for x in (k.get("menu_keys") or []) if x]
            if not mks or not parent_bizs:
                continue
            kid_bizs = {_biz_id_for_item(m) for m in mks}
            # include 的 biz 与同级多数 biz 无关 → 串菜单
            if parent_bizs and kid_bizs and kid_bizs.isdisjoint(parent_bizs):
                findings.append(
                    _finding(
                        "error",
                        f"用例「{lab}」的 include「{kid_lab}」菜单 {','.join(mks)} "
                        f"与同级其它菜单业务家族不一致",
                        where=f"usecases.{u.get('id')}",
                        fix=_uc_fix,
                        goto=_uc_goto,
                    )
                )
            # 购物车父节点下挂订单/评价等
            if "购物车" in lab:
                bad_mk = [
                    m
                    for m in mks
                    if _biz_id_for_item(m) in ("order", "review", "address")
                ]
                if bad_mk or any(t in kid_lab for t in ("订单", "支付", "评价", "地址")):
                    if kid_lab != "结算下单" and "购物车" not in kid_lab:
                        findings.append(
                            _finding(
                                "error",
                                f"用例「{lab}」下挂「{kid_lab}」，与购物车菜单语义不符",
                                where=f"usecases.{u.get('id')}",
                                fix=_uc_fix,
                                goto=_uc_goto,
                            )
                        )
            if "订单" in lab and "评价" not in lab:
                if any(_biz_id_for_item(m) in ("review", "address") for m in mks) or any(
                    t in kid_lab for t in ("评价", "地址")
                ):
                    findings.append(
                        _finding(
                            "error",
                            f"用例「{lab}」下挂「{kid_lab}」，与订单菜单语义不符",
                            where=f"usecases.{u.get('id')}",
                            fix=_uc_fix,
                            goto=_uc_goto,
                        )
                    )
    return findings


def audit_architecture_rubric(model: dict[str, Any] | None) -> list[dict[str, str]]:
    model = model if isinstance(model, dict) else {}
    findings: list[dict[str, str]] = []
    roles = [r for r in (model.get("roles") or []) if isinstance(r, dict) and r.get("id")]
    if not roles:
        findings.append(
            _finding("error", "逻辑架构图无交付角色", where="architecture.roles")
        )
    return findings


def audit_modules_rubric(model: dict[str, Any] | None) -> list[dict[str, str]]:
    """模块图：有 root；叶子须有 id（文案细则仍走 label_gate）。"""
    model = model if isinstance(model, dict) else {}
    findings: list[dict[str, str]] = []
    root = model.get("root")
    if not isinstance(root, dict) or not root.get("id"):
        findings.append(_finding("error", "功能模块图缺 root", where="modules.root"))
    return findings


_AUDITORS = {
    "er": audit_er_rubric,
    "sequences": audit_sequence_rubric,
    "sequence": audit_sequence_rubric,
    "activities": audit_activity_rubric,
    "activity": audit_activity_rubric,
    "usecase_desc": audit_usecase_desc_rubric,
    "classes": audit_class_rubric,
    "usecases": audit_usecase_rubric,
    "architecture": audit_architecture_rubric,
    "modules": audit_modules_rubric,
}


def audit_rubric(
    kind: str,
    model: dict[str, Any] | None,
    **opts: Any,
) -> list[dict[str, str]]:
    fn = _AUDITORS.get((kind or "").strip().lower())
    if not fn:
        return []
    if kind in ("er",) or fn is audit_er_rubric:
        return audit_er_rubric(
            model,
            mode=opts.get("mode"),
            entity=opts.get("entity"),
        )
    return fn(model)


def attach_rubric_gate(
    model: dict[str, Any],
    *,
    kind: str,
    **opts: Any,
) -> dict[str, Any]:
    """挂 rubric_gate；error 级 → ok=False（禁可交导出）。"""
    findings = audit_rubric(kind, model, **opts)
    errors = [f for f in findings if f.get("level") == "error"]
    ok = not errors
    note = ""
    if not ok:
        first = str(errors[0].get("msg") or "论文图规则未通过")
        note = f"论文图规则检查红 {len(errors)} 处 · {first}"
    model["rubric_gate"] = {
        "ok": ok,
        "kind": kind,
        "findings": findings[:60],
        "note": note,
    }
    return model


def export_blocked_reason(model: dict[str, Any] | None) -> str | None:
    """可交导出阻断原因：rubric_gate 或模块 label_gate。"""
    if not isinstance(model, dict):
        return None
    rg = model.get("rubric_gate") if isinstance(model.get("rubric_gate"), dict) else {}
    if rg.get("ok") is False:
        return str(rg.get("note") or "论文图规则检查未通过")
    lg = model.get("label_gate") if isinstance(model.get("label_gate"), dict) else {}
    if lg.get("ok") is False:
        return str(lg.get("note") or "模块图文案红，不可导出")
    return None


def raise_if_export_blocked(model: dict[str, Any] | None) -> None:
    reason = export_blocked_reason(model)
    if reason:
        raise ValueError(reason)


__all__ = [
    "attach_rubric_gate",
    "audit_activity_rubric",
    "audit_architecture_rubric",
    "audit_class_rubric",
    "audit_er_rubric",
    "audit_modules_rubric",
    "audit_rubric",
    "audit_sequence_rubric",
    "audit_usecase_desc_rubric",
    "audit_usecase_rubric",
    "export_blocked_reason",
    "raise_if_export_blocked",
]
