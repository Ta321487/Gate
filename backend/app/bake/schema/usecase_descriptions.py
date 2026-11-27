"""论文用例描述表：从交付 schema + 开题材料推导（与用例图/测例同口径）。

真相来源：
- domain.schema.json 的 menus / roles / entities / labels / capabilities
- 开题/任务书合并正文（仅用于选哪 4 个、命名对齐；禁止发明菜单外功能）

每张表：用例名称 / 执行者 / 简要说明 / 基本事件流。
事件流模板只描述已交付菜单对应的真实操作路径（登录→点菜单→填表→提交→提示）。
默认阐述 4 个用例（篇幅限制）；不足 4 个时有多少交多少，绝不凑假用例。
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from app.bake.schema.diagram_svg_util import read_json_dict
from app.bake.schema.modules import (
    _SKIP_MENU_KEYS,
    _archive_biz_label,
    _menu_label,
    looks_latin,
    parse_identity_modules,
)
from app.bake.schema.testcases import (
    _app_title,
    _entity_label,
    _kind,
    _role_label,
)

DEFAULT_DESC_COUNT = 4
DEFAULT_TABLE_START = "3.1"

# 菜单 kind → 优先级（越大越优先入选）；仅用于排序，不发明功能
_KIND_PRIORITY: dict[str, int] = {
    "auth_login": 100,
    "auth_register": 92,
    # 选座购票：演艺/影院主路径，须压过通用购物车（禁再落成 open 冒烟）
    "seat_shows": 95,
    "my_tickets": 88,
    "reserve_user": 87,
    "cart": 86,
    "my_orders": 84,
    "archive_user": 82,
    "ticket_pending": 80,
    "orders": 78,
    "reservations": 77,
    "archive_admin": 74,
    "guestbook_user": 70,
    "favorites": 68,
    "dm": 66,
    "content_user": 60,
    "profile": 55,
    "messages": 50,
    "users": 48,
    "category": 46,
    "content_admin": 44,
    "ticket_records": 42,
    "guestbook_admin": 40,
    "addresses": 38,
    "lookup": 36,
    "open": 20,
    "blind_pools": 36,
    "group_campaigns": 36,
    "delivery_slots": 36,
    "price_spans": 36,
    "purchase_permits": 36,
    "my_permits": 36,
    "line_specs": 36,
    "lost_clues": 36,
    "consigns": 36,
    "my_consigns": 36,
    "my_archive": 72,
    "peer_tickets": 79,
    "fund_publicity_mine": 58,
    "fund_publicity_admin": 45,
    "fund_disburse_admin": 45,
    "grade_scores_mine": 58,
    "grade_scores_admin": 45,
    "listing_deal_admin": 45,
}


def _fmt(tpl: str, ctx: dict[str, str]) -> str:
    out = tpl or ""
    for k, v in ctx.items():
        out = out.replace("{" + k + "}", v)
    return out


def _read_json(path):
    return read_json_dict(path, missing={}) or {}


def normalize_desc_count(n: int | str | None) -> int:
    try:
        v = int(n)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return DEFAULT_DESC_COUNT
    return v if 1 <= v <= 8 else DEFAULT_DESC_COUNT


def normalize_table_start(raw: str | None) -> str:
    s = str(raw or "").strip() or DEFAULT_TABLE_START
    if not re.fullmatch(r"\d+(\.\d+)?", s):
        return DEFAULT_TABLE_START
    return s


def _next_table_no(start: str, index: int) -> str:
    """表号：3.1 → 3.2 …；非整段小数则退回 3.{index+1}。"""
    if index == 0:
        return start
    m = re.fullmatch(r"(\d+)\.(\d+)", start)
    if m:
        return f"{m.group(1)}.{int(m.group(2)) + index}"
    return f"3.{index + 1}"


def _reservation_stem(schema: dict[str, Any], label: str) -> str:
    entities = schema.get("entities") if isinstance(schema.get("entities"), dict) else {}
    res = entities.get("reservation") if isinstance(entities.get("reservation"), dict) else {}
    lab = str(res.get("label") or "").strip()
    if lab and not looks_latin(lab):
        return lab
    stem = (
        label.replace("我的", "")
        .replace("管理", "")
        .replace("记录", "")
        .replace("列表", "")
        .strip()
    )
    return stem or label


def _ticket_stem(label: str) -> str:
    return label.replace("我的", "").replace("申请", "").strip() or label


def _clean_role_lab(lab: str) -> str:
    lab = re.sub(r"[（(][^）)]*[）)]", "", str(lab or "")).strip()
    return lab


def _cinema_face(schema: dict[str, Any] | None) -> str | None:
    """``performance`` | ``cinema`` | None。真源 schema.cinemaFace / labels.cinemaFace。"""
    if not isinstance(schema, dict):
        return None
    labels = schema.get("labels") if isinstance(schema.get("labels"), dict) else {}
    face = str(schema.get("cinemaFace") or labels.get("cinemaFace") or "").strip()
    if face in ("performance", "cinema"):
        return face
    return None


def _cinema_role_polish(lab: str, *, side: str, schema: dict[str, Any]) -> str:
    """仅补空壳；材料已写的称呼（用户/主办方商家/平台管理员）原样保留。

    旧逻辑把「用户→观众」「商家→主办方」会盖掉开题身份段，论文用例与材料打架。
    """
    face = _cinema_face(schema)
    if not face:
        return lab
    labels = schema.get("labels") if isinstance(schema.get("labels"), dict) else {}
    org = str(labels.get("seatOrgNoun") or "").strip() or "主办方"
    cleaned = _clean_role_lab(lab)
    if side == "user":
        if cleaned:
            return cleaned
        return "观众" if face == "performance" else "观影者"
    if not cleaned:
        return org if side == "staff" else cleaned
    # 光杆电商壳且材料未写成复合名时，才收成场馆侧主办名词
    if cleaned in ("商家", "商户") and cleaned == lab:
        return org
    if cleaned in ("管理员", "总管"):
        return "平台管理员"
    return cleaned


def _post_pack_menu_keys(post: dict[str, Any]) -> set[str]:
    from app.bake.staff_posts import PACK_ADMIN_MENUS

    allowed: set[str] = set()
    for pk in post.get("packs") or []:
        if isinstance(pk, str) and pk.strip() in PACK_ADMIN_MENUS:
            allowed |= set(PACK_ADMIN_MENUS[pk.strip()])
    return allowed


def _resolve_case_actor(
    schema: dict[str, Any],
    *,
    side: str,
    menu_key: str = "",
    menu_item: dict[str, Any] | None = None,
) -> str:
    """候选执行者（全领域通用，不绑某一业务场景）：

    - user 菜单 → roles.user.label
    - admin 菜单且 superOnly → roles.admin.label
    - admin 菜单被某 staff_post 的 pack 覆盖 → 该岗位 label
    - 否则若 subadmin 挂了 staffPostId 且称呼不同于 admin → subadmin.label
    - 否则 → roles.admin.label
    """
    if side == "user":
        lab = _clean_role_lab(_role_label(schema, "user")) or "用户"
        return _cinema_role_polish(lab, side="user", schema=schema)

    item = menu_item if isinstance(menu_item, dict) else {}
    if bool(item.get("superOnly")):
        lab = _clean_role_lab(_role_label(schema, "admin")) or "管理员"
        return _cinema_role_polish(lab, side="admin", schema=schema)

    roles = schema.get("roles") if isinstance(schema.get("roles"), dict) else {}
    posts = roles.get("staff_posts") if isinstance(roles.get("staff_posts"), list) else []
    key = str(menu_key or "").strip()
    for p in posts:
        if not isinstance(p, dict):
            continue
        if key and key in _post_pack_menu_keys(p):
            lab = _clean_role_lab(str(p.get("label") or "").strip())
            if lab:
                return _cinema_role_polish(lab, side="staff", schema=schema)

    sub = roles.get("subadmin") if isinstance(roles.get("subadmin"), dict) else {}
    sub_lab = _clean_role_lab(str(sub.get("label") or "").strip())
    admin_lab = _clean_role_lab(_role_label(schema, "admin"))
    post_id = str(sub.get("staffPostId") or sub.get("staff_post") or "").strip()
    if post_id and sub_lab and sub_lab != admin_lab:
        return _cinema_role_polish(sub_lab, side="staff", schema=schema)

    return _cinema_role_polish(admin_lab or "管理员", side="admin", schema=schema)


def _ctx_for(
    schema: dict[str, Any],
    *,
    side: str,
    label: str,
    menu_key: str = "",
    menu_item: dict[str, Any] | None = None,
) -> dict[str, str]:
    user = _cinema_role_polish(
        _clean_role_lab(_role_label(schema, "user")) or "用户",
        side="user",
        schema=schema,
    )
    admin = _cinema_role_polish(
        _clean_role_lab(_role_label(schema, "admin")) or "管理员",
        side="admin",
        schema=schema,
    )
    actor = _resolve_case_actor(
        schema, side=side, menu_key=menu_key, menu_item=menu_item
    )
    entity = _entity_label(schema)
    return {
        "user": user,
        "admin": admin,
        "actor": actor,
        "label": label,
        "entity": entity,
        "ticket_stem": _ticket_stem(label),
        "reserve_stem": _reservation_stem(schema, label),
        "app": _app_title(schema),
    }


def _flow_spec(kind: str, schema: dict[str, Any] | None = None) -> dict[str, Any]:
    """返回 name/summary/flow 模板；真源 factory_usecase_flow（种子 usecase_flows.json）。

    传入 schema 时按 cinemaFace 选 face 行（performance/cinema），缺则回落 *。
    渲染器不得再内置业务事件流整句。
    """
    from app.services import usecase_flows as uf

    face = _cinema_face(schema) or uf.WILDCARD
    return uf.resolve_flow_spec(kind, face=face)


def _proposal_hit_terms(proposal_text: str, schema: dict[str, Any]) -> set[str]:
    """从开题正文与身份模块枚举抽出可用于加分的中文词（不做功能发明）。"""
    terms: set[str] = set()
    prop = (proposal_text or "").strip()
    if not prop:
        return terms
    try:
        sections = parse_identity_modules(prop, schema=schema)
        for sec in sections or []:
            for m in sec.get("modules") or []:
                name = str(m.get("name") or m.get("label") or "").strip()
                if name and not looks_latin(name) and len(name) >= 2:
                    terms.add(name)
    except Exception:
        pass
    # 再扫交付菜单/实体标签是否出现在开题中
    menus = schema.get("menus") if isinstance(schema.get("menus"), dict) else {}
    for side in ("user", "admin"):
        for raw in menus.get(side) or []:
            if not isinstance(raw, dict):
                continue
            lab = _menu_label(raw)
            if lab and len(lab) >= 2 and lab in prop:
                terms.add(lab)
    ent = _archive_biz_label(schema)
    if ent and len(ent) >= 2 and ent.replace("模块", "") in prop:
        terms.add(ent.replace("模块", ""))
    entity = _entity_label(schema)
    if entity and len(entity) >= 2 and entity in prop:
        terms.add(entity)
    for word in (
        "盲盒",
        "拼团",
        "成团",
        "配送时段",
        "送达时段",
        "节日加价",
        "节日涨价",
        "限购",
        "购买审核",
        "寄卖",
        "寄售",
        "刻字",
        "规格",
        "线索",
        "选座",
        "购票",
        "演出",
        "场次",
        "剧目",
        "票务",
        "影票",
        "观演",
        "观影",
    ):
        if word in prop:
            terms.add(word)
    return terms


def _score_candidate(
    *,
    kind: str,
    label: str,
    name: str,
    side: str,
    hit_terms: set[str],
    schema: dict[str, Any] | None = None,
) -> int:
    score = int(_KIND_PRIORITY.get(kind, 20))
    # 用户端主路径略优先于管理端同档
    if side == "user":
        score += 3
    # 影院/演艺皮：选座+场次维护+核销压过购物车（购物车多为卖品加购，不占主 4 席）
    face = _cinema_face(schema)
    if face:
        if kind == "seat_shows":
            score += 25
        elif kind == "archive_admin":
            score += 22
        elif kind == "orders":
            score += 18
        elif kind == "cart":
            score -= 20
    blob = f"{label}{name}"
    for t in hit_terms:
        if t and t in blob:
            score += 40
            break
    for t in hit_terms:
        if t and (t in label or label in t):
            score += 20
            break
    return score


_DEDICATED_MENU_KINDS = frozenset(
    {
        "seat_shows",
        "my_archive",
        "peer_tickets",
        "fund_publicity_mine",
        "fund_publicity_admin",
        "fund_disburse_admin",
        "grade_scores_mine",
        "grade_scores_admin",
        "listing_deal_admin",
    }
)


def _case_kind(key: str, side: str) -> str:
    """用例描述用 kind；评价按端拆开；域专菜单不得再落成 open 冒烟。"""
    if key == "order_reviews":
        return "order_reviews_user" if side == "user" else "order_reviews_admin"
    if key in _DEDICATED_MENU_KINDS:
        return key
    return _kind(key, side)


def _trade_flow_notes(schema: dict[str, Any], kind: str) -> list[str]:
    """主路径被选进论文时，补上已挂能力的规则，不另造菜单。"""
    notes: list[str] = []
    # 影院/演艺票务：禁叠电商配送·发货·盲盒腔
    if _cinema_face(schema):
        if kind == "seat_shows":
            notes.append("选座确认后即时占座；过开场时间不可售；柜台取票，无物流发货")
        return notes
    if kind == "cart" and schema.get("deliveryWindow"):
        notes.append("结算时选择配送日期和仍有余量的时段，节日加价按下单当日计入本单")
    if kind == "cart" and schema.get("purchaseGate"):
        notes.append("需审核的商品要先通过，才能加购和下单")
    if kind == "cart" and schema.get("lineCustom"):
        notes.append("定制文字和所选规格记在本单明细上")
    if kind in ("orders", "my_orders") and schema.get("blindBox"):
        notes.append("若买的是盲盒，付款买的是盒子，开出奖品后才扣奖品库存")
    if kind in ("orders", "my_orders") and schema.get("groupBuy"):
        notes.append("拼团订单为待成团，人齐后才能发货，过期未齐则取消并退回余额")
    if kind in ("orders", "my_orders") and schema.get("consign"):
        notes.append("寄卖商品质检通过后才可购买，完成后按当时抽成记账")
    if kind in ("orders", "my_orders") and schema.get("lineCustomPlaceConfirmed"):
        notes.append("下单后为待制作，制作完成再发货")
    ticket = (schema.get("entities") or {}).get("ticket") if isinstance(schema.get("entities"), dict) else None
    if (
        kind in ("my_tickets", "ticket_pending")
        and isinstance(ticket, dict)
        and ticket.get("requireClaimProof")
    ):
        notes.append("认领先填说明，进入待交凭证后补交凭证，核验通过才能办结")
    return notes


def _build_case(
    *,
    schema: dict[str, Any],
    kind: str,
    side: str,
    key: str,
    label: str,
    source: str,
    menu_item: dict[str, Any] | None = None,
) -> dict[str, Any]:
    ctx = _ctx_for(
        schema,
        side=side,
        label=label,
        menu_key=key,
        menu_item=menu_item,
    )
    spec = _flow_spec(kind, schema)
    name = _fmt(str(spec["name"]), ctx)
    summary = _fmt(str(spec["summary"]), ctx)
    flow = [_fmt(str(step), ctx) for step in (spec.get("flow") or [])]
    flow.extend(_trade_flow_notes(schema, kind))
    return {
        "name": name,
        "actor": ctx["actor"],
        "summary": summary,
        "flow": flow,
        "menu_key": key,
        "side": side,
        "kind": kind,
        "source": source,
        "label": label,
    }


def build_usecase_description_candidates(
    schema: dict[str, Any],
    *,
    proposal_text: str = "",
) -> list[dict[str, Any]]:
    """枚举全部可描述候选（仅交付菜单 + 登录/注册），带评分。"""
    schema = schema if isinstance(schema, dict) else {}
    menus = schema.get("menus") if isinstance(schema.get("menus"), dict) else {}
    caps = {str(c) for c in (schema.get("capabilities") or [])}
    has_user = bool(menus.get("user")) or "org_users" in caps
    hit_terms = _proposal_hit_terms(proposal_text, schema)
    source_base = "menu"
    if hit_terms:
        source_base = "proposal+menu"

    out: list[dict[str, Any]] = []
    if has_user:
        login = _build_case(
            schema=schema,
            kind="auth_login",
            side="user",
            key="auth",
            label="登录",
            source="auth" if not hit_terms else "proposal+auth",
        )
        login["score"] = _score_candidate(
            kind="auth_login",
            label=login["label"],
            name=login["name"],
            side="user",
            hit_terms=hit_terms,
            schema=schema,
        )
        out.append(login)
        # 注册：开题写到才优先；否则不占 4 席（避免挤掉业务主路径）
        prop = (proposal_text or "")
        if "注册" in prop or "register" in prop.lower():
            reg = _build_case(
                schema=schema,
                kind="auth_register",
                side="user",
                key="auth",
                label="注册",
                source="proposal+auth",
            )
            reg["score"] = _score_candidate(
                kind="auth_register",
                label=reg["label"],
                name=reg["name"],
                side="user",
                hit_terms=hit_terms,
                schema=schema,
            )
            out.append(reg)

    seen: set[tuple[str, str]] = set()
    for side in ("user", "admin"):
        for raw in menus.get(side) or []:
            if not isinstance(raw, dict):
                continue
            key = str(raw.get("key") or "").strip()
            if not key or key in _SKIP_MENU_KEYS:
                continue
            pair = (side, key)
            if pair in seen:
                continue
            seen.add(pair)
            label = _menu_label(raw)
            kind = _case_kind(key, side)
            case = _build_case(
                schema=schema,
                kind=kind,
                side=side,
                key=key,
                label=label,
                source=source_base,
                menu_item=raw,
            )
            case["score"] = _score_candidate(
                kind=kind,
                label=label,
                name=case["name"],
                side=side,
                hit_terms=hit_terms,
                schema=schema,
            )
            out.append(case)
    return out


def select_usecase_descriptions(
    candidates: list[dict[str, Any]],
    *,
    count: int = DEFAULT_DESC_COUNT,
) -> list[dict[str, Any]]:
    """登录固定优先占一席；其余按评分填充。禁止重复 name / 同菜单重复。"""
    n = normalize_desc_count(count)
    ranked = sorted(
        candidates,
        key=lambda c: (-int(c.get("score") or 0), str(c.get("side") or ""), str(c.get("menu_key") or "")),
    )
    picked: list[dict[str, Any]] = []
    used_names: set[str] = set()
    used_keys: set[tuple[str, str]] = set()

    def _try_add(c: dict[str, Any]) -> bool:
        if len(picked) >= n:
            return False
        name = str(c.get("name") or "").strip()
        key = str(c.get("menu_key") or "")
        side = str(c.get("side") or "")
        kind = str(c.get("kind") or "")
        dedupe = ("auth", kind) if key == "auth" else (side, key)
        if dedupe in used_keys or name in used_names:
            return False
        used_keys.add(dedupe)
        used_names.add(name)
        picked.append(c)
        return True

    # 登录几乎总是论文必备；有则先占一席
    for c in ranked:
        if c.get("kind") == "auth_login":
            _try_add(c)
            break
    for c in ranked:
        if len(picked) >= n:
            break
        _try_add(c)
    return picked


def render_usecase_description_markdown(
    *,
    title: str,
    cases: list[dict[str, Any]],
    table_start: str = DEFAULT_TABLE_START,
) -> str:
    names = [str(c.get("name") or "") for c in cases]
    name_list = "、".join(names) if names else "（暂无）"
    lines = [
        f"## {title} — 用例描述表",
        "",
        f"由于内容篇幅限制，本次仅针对{name_list}这{len(cases) or 0}个用例进行阐述。",
        "",
    ]
    for i, c in enumerate(cases):
        tno = _next_table_no(table_start, i)
        name = str(c.get("name") or "")
        actor = str(c.get("actor") or "")
        summary = str(c.get("summary") or "")
        flow = c.get("flow") or []
        # Markdown 表格内多行仍用 <br>（GFM）；贴 Word 走前端 htmlForWord 段落换行，禁止软回车
        from app.bake.schema.zh_copy import squeeze_cjk_alnum_spaces

        flow_text = "<br>\n".join(
            f"{idx}. {step}" for idx, step in enumerate(flow, 1)
        )
        cap = squeeze_cjk_alnum_spaces(
            f"（{i + 1}）{name}功能的用例说明，{name}的用例描述表见表{tno}所示。"
        )
        title = squeeze_cjk_alnum_spaces(f"表{tno} “{name}”的用例描述表")
        lines.extend(
            [
                cap,
                "",
                title,
                "",
                "| 项目 | 内容 |",
                "| --- | --- |",
                f"| 用例名称 | {name.replace('|', '\\|')} |",
                f"| 执行者 | {actor.replace('|', '\\|')} |",
                f"| 简要说明 | {summary.replace('|', '\\|')} |",
                f"| 基本事件流 | {flow_text.replace('|', '\\|')} |",
                "",
            ]
        )
    return "\n".join(lines)


def _candidate_stable_id(c: dict[str, Any]) -> str:
    from app.bake.schema.sequence import candidate_id

    return candidate_id(c)


def _pick_usecase_desc_by_ids(
    candidates: list[dict[str, Any]], ids: list[str], *, count: int
) -> list[dict[str, Any]] | None:
    """按稳定 id 勾选；非法/不足则 None（回落默认挑选）。"""
    by_id = {_candidate_stable_id(c): c for c in candidates if isinstance(c, dict)}
    picked: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw in ids:
        sid = str(raw or "").strip()
        if not sid or sid in seen:
            continue
        if sid not in by_id:
            return None
        seen.add(sid)
        picked.append(by_id[sid])
        if len(picked) >= count:
            break
    return picked if picked else None


def usecase_description_model(
    schema: dict[str, Any] | None,
    *,
    proposal_text: str = "",
    count: int = DEFAULT_DESC_COUNT,
    table_start: str = DEFAULT_TABLE_START,
    title_fallback: str = "管理系统",
    selection: list[str] | None = None,
) -> dict[str, Any]:
    schema = schema if isinstance(schema, dict) else {}
    title = _app_title(schema, title_fallback)
    n = normalize_desc_count(count)
    tstart = normalize_table_start(table_start)
    candidates = build_usecase_description_candidates(
        schema, proposal_text=proposal_text
    )
    selected: list[dict[str, Any]] | None = None
    if selection:
        selected = _pick_usecase_desc_by_ids(candidates, selection, count=n)
    if not selected:
        selected = select_usecase_descriptions(candidates, count=n)
    from app.bake.schema.zh_copy import squeeze_cjk_alnum_spaces

    cases_out: list[dict[str, Any]] = []
    for i, c in enumerate(selected):
        cases_out.append(
            {
                "id": f"UCD-{i + 1:03d}",
                "stable_id": _candidate_stable_id(c),
                "table_no": _next_table_no(tstart, i),
                "name": squeeze_cjk_alnum_spaces(str(c["name"] or "")),
                "actor": squeeze_cjk_alnum_spaces(str(c["actor"] or "")),
                "summary": squeeze_cjk_alnum_spaces(str(c["summary"] or "")),
                "flow": [
                    squeeze_cjk_alnum_spaces(str(s))
                    for s in (c.get("flow") or [])
                ],
                "menu_key": c.get("menu_key"),
                "side": c.get("side"),
                "kind": c.get("kind"),
                "source": c.get("source"),
                "score": c.get("score"),
            }
        )
    names = [c["name"] for c in cases_out]
    intro = squeeze_cjk_alnum_spaces(
        f"由于内容篇幅限制，本次仅针对{'、'.join(names)}这{len(cases_out)}个用例进行阐述。"
        if cases_out
        else "当前交付菜单不足以生成用例描述表。"
    )
    source_note = (
        "由交付 menus/roles/entities 推导事件流；开题正文仅影响选用与加分，不发明未交付功能"
        if (proposal_text or "").strip()
        else "由交付 menus/roles/entities 推导；未提供开题正文时按主路径优先级选用"
    )
    cand_out: list[dict[str, Any]] = []
    for c in candidates:
        if not isinstance(c, dict):
            continue
        cand_out.append(
            {
                "stable_id": _candidate_stable_id(c),
                "name": c.get("name"),
                "actor": c.get("actor"),
                "menu_key": c.get("menu_key"),
                "side": c.get("side"),
                "kind": c.get("kind"),
                "score": c.get("score"),
            }
        )
    return {
        "title": title,
        "intro": intro,
        "source_note": source_note,
        "count": len(cases_out),
        "requested_count": n,
        "table_start": tstart,
        "cases": cases_out,
        "selected_ids": [str(c.get("stable_id") or "") for c in cases_out],
        "candidates": cand_out,
        "candidate_count": len(candidates),
        "markdown": render_usecase_description_markdown(
            title=title, cases=cases_out, table_start=tstart
        ),
    }


def load_usecase_description_model(
    workspace: Path,
    *,
    proposal_text: str = "",
    count: int = DEFAULT_DESC_COUNT,
    table_start: str = DEFAULT_TABLE_START,
    selection: list[str] | None = None,
) -> dict[str, Any] | None:
    schema = _read_json(workspace / "domain.schema.json")
    if not schema:
        return None
    spec = _read_json(workspace / "spec.json")
    title_fb = str(spec.get("title") or "管理系统")
    sel = selection
    if sel is None:
        try:
            from app.bake.overrides import resolve_override_selection

            sel = resolve_override_selection(workspace, "usecase_desc")
        except Exception:  # noqa: BLE001
            sel = None
    model = usecase_description_model(
        schema,
        proposal_text=proposal_text,
        count=count,
        table_start=table_start,
        title_fallback=title_fb,
        selection=sel,
    )
    try:
        from app.bake.overrides import (
            apply_usecase_desc_cell_overrides,
            load_overrides_mirror,
        )

        mirror = load_overrides_mirror(workspace)
        block = (mirror or {}).get("usecase_desc") if isinstance(mirror, dict) else None
        cells = (block or {}).get("cell_overrides") if isinstance(block, dict) else None
        if cells:
            model = apply_usecase_desc_cell_overrides(model, cells)
    except Exception:  # noqa: BLE001
        pass
    return model
