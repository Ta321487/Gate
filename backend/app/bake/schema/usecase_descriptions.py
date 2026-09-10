"""论文用例描述表：从交付 schema + 开题材料推导（与用例图/测例同口径）。

真相来源：
- domain.schema.json 的 menus / roles / entities / labels / capabilities
- 开题/任务书合并正文（仅用于选哪 4 个、命名对齐；禁止发明菜单外功能）

每张表：用例名称 / 执行者 / 简要说明 / 基本事件流。
事件流模板只描述已交付菜单对应的真实操作路径（登录→点菜单→填表→提交→提示）。
默认阐述 4 个用例（篇幅限制）；不足 4 个时有多少交多少，绝不凑假用例。
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

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
}


def _fmt(tpl: str, ctx: dict[str, str]) -> str:
    out = tpl or ""
    for k, v in ctx.items():
        out = out.replace("{" + k + "}", v)
    return out


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


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


def _ctx_for(
    schema: dict[str, Any],
    *,
    side: str,
    label: str,
) -> dict[str, str]:
    user = _role_label(schema, "user")
    admin = _role_label(schema, "admin")
    actor = user if side == "user" else admin
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


def _flow_spec(kind: str) -> dict[str, Any]:
    """返回 name/summary/flow 模板；未知 kind 用 open 冒烟，不编业务规则。"""
    specs: dict[str, dict[str, Any]] = {
        "auth_login": {
            "name": "{user}登录系统",
            "summary": "{user}使用账号密码登录本系统。",
            "flow": [
                "{user}打开系统登录界面",
                "系统展示用户名与密码登录表单",
                "{user}输入正确的用户名与密码，点击「登录」",
                "系统校验账号信息",
                "校验通过后进入系统主界面，完成登录",
            ],
        },
        "auth_register": {
            "name": "{user}注册账号",
            "summary": "{user}在注册页填写信息并完成账号注册。",
            "flow": [
                "{user}打开系统注册界面",
                "系统展示注册表单",
                "{user}填写必填注册信息，点击提交注册",
                "系统校验并保存账号信息",
                "注册成功后可使用新账号登录系统",
            ],
        },
        "archive_user": {
            "name": "{actor}浏览{entity}",
            "summary": "{actor}在「{label}」中浏览并查看{entity}信息。",
            "flow": [
                "{actor}登录成功后进入系统主界面，点击「{label}」",
                "系统转至「{label}」列表界面",
                "{actor}浏览或检索{entity}列表",
                "{actor}点击选定记录，系统展示详情信息",
                "系统展示的数据与后台保存内容一致",
            ],
        },
        "archive_admin": {
            "name": "{actor}管理{entity}",
            "summary": "{actor}在「{label}」中新增或维护{entity}主数据。",
            "flow": [
                "{actor}登录成功后进入管理端，点击「{label}」",
                "系统转至「{label}」管理界面",
                "{actor}点击新增或打开编辑，填写必填项",
                "{actor}点击保存",
                "系统保存{entity}信息，列表中可见更新结果",
            ],
        },
        "reserve_user": {
            "name": "{actor}提交{reserve_stem}",
            "summary": "{actor}在「{label}」中选择可预约项并提交{reserve_stem}。",
            "flow": [
                "{actor}登录成功后进入系统主界面，点击「{label}」",
                "系统转至「{label}」相关界面",
                "{actor}选择可预约项或时段，并填写页面必填信息",
                "{actor}点击确认或提交",
                "系统保存{reserve_stem}信息，提示提交成功，并可在列表中查看",
            ],
        },
        "reservations": {
            "name": "{actor}办理{reserve_stem}记录",
            "summary": "{actor}在「{label}」中查看并办理{reserve_stem}记录。",
            "flow": [
                "{actor}登录成功后进入管理端，点击「{label}」",
                "系统转至「{label}」界面并展示记录列表",
                "{actor}打开一条记录查看详情",
                "{actor}按页面提供的办理操作执行办结或处理",
                "系统更新记录状态，列表展示最新结果",
            ],
        },
        "my_tickets": {
            "name": "{actor}提交{ticket_stem}",
            "summary": "{actor}在「{label}」中填写并提交申请。",
            "flow": [
                "{actor}登录成功后进入系统主界面，点击「{label}」",
                "系统转至「{label}」界面",
                "{actor}填写申请表单必填项",
                "{actor}点击提交",
                "系统保存申请信息，提示提交成功，列表出现新单据",
            ],
        },
        "ticket_pending": {
            "name": "{actor}审核{ticket_stem}",
            "summary": "{actor}在「{label}」中对待办单据进行通过或驳回。",
            "flow": [
                "{actor}登录成功后进入管理端，点击「{label}」",
                "系统转至待办列表界面",
                "{actor}打开一条待办单据查看详情",
                "{actor}执行通过/同意或驳回操作",
                "系统更新单据状态，待办列表同步变化",
            ],
        },
        "ticket_records": {
            "name": "{actor}查询{label}",
            "summary": "{actor}在「{label}」中按条件查看办理记录。",
            "flow": [
                "{actor}登录成功后进入管理端，点击「{label}」",
                "系统转至记录列表界面",
                "{actor}按条件查看办理记录",
                "系统展示符合条件的记录列表",
            ],
        },
        "cart": {
            "name": "{actor}使用购物车",
            "summary": "{actor}将商品加入购物车并在「{label}」中核对。",
            "flow": [
                "{actor}登录成功后在商品相关页面选择商品并加入购物车",
                "系统提示加入成功",
                "{actor}点击「{label}」进入购物车界面",
                "{actor}核对商品与数量",
                "系统展示购物车中的已选商品信息",
            ],
        },
        "my_orders": {
            "name": "{actor}查看{label}",
            "summary": "{actor}在「{label}」中查看本人订单及状态。",
            "flow": [
                "{actor}登录成功后进入系统主界面，点击「{label}」",
                "系统转至订单列表界面",
                "{actor}查看订单状态或打开详情",
                "系统展示本人订单信息与当前状态",
            ],
        },
        "orders": {
            "name": "{actor}处理订单",
            "summary": "{actor}在「{label}」中对待处理订单执行办理操作。",
            "flow": [
                "{actor}登录成功后进入管理端，点击「{label}」",
                "系统转至订单管理界面",
                "{actor}打开待处理订单",
                "{actor}执行确认、发货等办理操作",
                "系统按办理结果更新订单状态",
            ],
        },
        "addresses": {
            "name": "{actor}维护收货地址",
            "summary": "{actor}在「{label}」中新增或编辑收货地址。",
            "flow": [
                "{actor}登录成功后进入系统主界面，点击「{label}」",
                "系统转至地址管理界面",
                "{actor}新增或编辑地址并填写必填项",
                "{actor}点击保存",
                "系统保存地址信息，列表中可见该地址",
            ],
        },
        "profile": {
            "name": "{actor}维护个人资料",
            "summary": "{actor}在「{label}」中查看并保存个人资料。",
            "flow": [
                "{actor}登录成功后进入系统主界面，点击「{label}」",
                "系统转至个人资料界面并展示当前资料",
                "{actor}修改允许编辑的字段",
                "{actor}点击保存",
                "系统保存成功，页面展示更新后的资料",
            ],
        },
        "messages": {
            "name": "{actor}查看站内消息",
            "summary": "{actor}在「{label}」中查看系统消息。",
            "flow": [
                "{actor}登录成功后进入系统主界面，点击「{label}」",
                "系统转至消息列表界面",
                "{actor}查看消息列表或打开一条消息",
                "系统展示消息内容或空状态提示",
            ],
        },
        "content_user": {
            "name": "{actor}查看公告",
            "summary": "{actor}在「{label}」中阅读公告内容。",
            "flow": [
                "{actor}登录成功后进入系统主界面，点击「{label}」",
                "系统转至公告列表界面",
                "{actor}点击一条公告",
                "系统展示公告标题与正文",
            ],
        },
        "content_admin": {
            "name": "{actor}发布公告",
            "summary": "{actor}在「{label}」中新建并发布公告。",
            "flow": [
                "{actor}登录成功后进入管理端，点击「{label}」",
                "系统转至公告管理界面",
                "{actor}新建公告并填写标题与正文",
                "{actor}点击发布或保存",
                "系统保存公告，用户端可查看",
            ],
        },
        "users": {
            "name": "{actor}管理用户",
            "summary": "{actor}在「{label}」中查看用户并进行启用/停用等管理。",
            "flow": [
                "{actor}登录成功后进入管理端，点击「{label}」",
                "系统转至用户列表界面",
                "{actor}查看用户列表并执行启用/停用或重置密码等管理操作",
                "系统按操作更新用户状态",
            ],
        },
        "category": {
            "name": "{actor}维护{label}",
            "summary": "{actor}在「{label}」中新增或编辑分类信息。",
            "flow": [
                "{actor}登录成功后进入管理端，点击「{label}」",
                "系统转至分类管理界面",
                "{actor}新增或编辑分类并填写必填项",
                "{actor}点击保存",
                "系统保存分类，列表中可见更新结果",
            ],
        },
        "guestbook_user": {
            "name": "{actor}提交留言",
            "summary": "{actor}在「{label}」中填写并提交留言。",
            "flow": [
                "{actor}登录成功后进入系统主界面，点击「{label}」",
                "系统转至留言界面",
                "{actor}填写留言正文并提交",
                "系统保存留言，列表中可见该留言",
            ],
        },
        "guestbook_admin": {
            "name": "{actor}管理留言",
            "summary": "{actor}在「{label}」中回复或处理留言。",
            "flow": [
                "{actor}登录成功后进入管理端，点击「{label}」",
                "系统转至留言管理界面",
                "{actor}打开一条留言，执行回复或删除",
                "系统更新留言状态，用户端可见相应结果",
            ],
        },
        "dm": {
            "name": "{actor}收发私信",
            "summary": "{actor}在「{label}」中发送并查看私信。",
            "flow": [
                "{actor}登录成功后进入系统主界面，点击「{label}」",
                "系统转至私信界面",
                "{actor}选择或新建会话对象并发送私信",
                "系统保存消息，会话中可见发送内容",
            ],
        },
        "favorites": {
            "name": "{actor}管理收藏",
            "summary": "{actor}收藏业务对象并在「{label}」中查看或取消。",
            "flow": [
                "{actor}登录成功后在详情页点击收藏",
                "系统提示收藏成功",
                "{actor}进入「{label}」查看收藏列表",
                "{actor}可取消收藏",
                "系统同步更新收藏列表",
            ],
        },
        "browse_history": {
            "name": "{actor}查看浏览足迹",
            "summary": "{actor}在「{label}」中查看最近浏览记录。",
            "flow": [
                "{actor}登录成功后进入系统主界面，点击「{label}」",
                "系统转至足迹列表界面",
                "{actor}查看最近浏览记录",
                "系统展示与浏览行为一致的足迹列表",
            ],
        },
        "coupons": {
            "name": "{actor}使用优惠券",
            "summary": "{actor}在「{label}」中领取或查看优惠券。",
            "flow": [
                "{actor}登录成功后进入系统主界面，点击「{label}」",
                "系统转至优惠券界面",
                "{actor}领取或查看可用优惠券",
                "系统展示券列表，可按实现用于下单",
            ],
        },
        "order_reviews": {
            "name": "{actor}评价订单",
            "summary": "{actor}在「{label}」或订单详情中提交评价。",
            "flow": [
                "{actor}登录成功后进入「{label}」或可评价订单详情",
                "系统展示评价表单",
                "{actor}填写评分与评价并提交",
                "系统保存评价信息",
            ],
        },
        "week_calendar": {
            "name": "{actor}查看{label}",
            "summary": "{actor}在「{label}」中查看日程安排。",
            "flow": [
                "{actor}登录成功后进入系统主界面，点击「{label}」",
                "系统转至周历界面",
                "{actor}切换日期查看安排",
                "系统展示本人相关安排",
            ],
        },
        "deadline": {
            "name": "{actor}查看{label}",
            "summary": "{actor}在「{label}」中查看逾期或催办记录。",
            "flow": [
                "{actor}登录成功后进入系统主界面，点击「{label}」",
                "系统转至催办/逾期列表界面",
                "{actor}查看相关记录",
                "系统展示逾期或催办信息",
            ],
        },
        "lookup": {
            "name": "{actor}维护{label}",
            "summary": "{actor}在「{label}」中维护字典项。",
            "flow": [
                "{actor}登录成功后进入管理端，点击「{label}」",
                "系统转至字典维护界面",
                "{actor}新增或编辑字典项并保存",
                "系统保存字典项，列表可见更新结果",
            ],
        },
        "archive_logs": {
            "name": "{actor}进行{label}",
            "summary": "{actor}在「{label}」相关入口提交或查看监测记录。",
            "flow": [
                "{actor}登录成功后进入系统，打开「{label}」或相关详情",
                "系统展示可操作表单或记录列表",
                "{actor}按页面字段提交或查看记录",
                "系统保存或展示与操作一致的结果",
            ],
        },
        "open": {
            "name": "{actor}使用{label}",
            "summary": "{actor}打开「{label}」并完成页面主操作。",
            "flow": [
                "{actor}登录成功后进入系统，点击「{label}」",
                "系统转至「{label}」界面",
                "{actor}查看页面主列表或主表单并完成可用操作",
                "系统按页面实现反馈操作结果",
            ],
        },
    }
    return specs.get(kind) or specs["open"]


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
    return terms


def _score_candidate(
    *,
    kind: str,
    label: str,
    name: str,
    side: str,
    hit_terms: set[str],
) -> int:
    score = int(_KIND_PRIORITY.get(kind, 20))
    # 用户端主路径略优先于管理端同档
    if side == "user":
        score += 3
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


def _build_case(
    *,
    schema: dict[str, Any],
    kind: str,
    side: str,
    key: str,
    label: str,
    source: str,
) -> dict[str, Any]:
    ctx = _ctx_for(schema, side=side, label=label)
    spec = _flow_spec(kind)
    name = _fmt(str(spec["name"]), ctx)
    summary = _fmt(str(spec["summary"]), ctx)
    flow = [_fmt(str(step), ctx) for step in (spec.get("flow") or [])]
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
            kind = _kind(key, side)
            case = _build_case(
                schema=schema,
                kind=kind,
                side=side,
                key=key,
                label=label,
                source=source_base,
            )
            case["score"] = _score_candidate(
                kind=kind,
                label=label,
                name=case["name"],
                side=side,
                hit_terms=hit_terms,
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
        flow_text = "<br>".join(
            f"{idx}. {step}" for idx, step in enumerate(flow, 1)
        )
        lines.extend(
            [
                f"（{i + 1}）{name}功能的用例说明，{name}的用例描述表见表 {tno} 所示。",
                "",
                f"表 {tno} “{name}”的用例描述表",
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


def usecase_description_model(
    schema: dict[str, Any] | None,
    *,
    proposal_text: str = "",
    count: int = DEFAULT_DESC_COUNT,
    table_start: str = DEFAULT_TABLE_START,
    title_fallback: str = "管理系统",
) -> dict[str, Any]:
    schema = schema if isinstance(schema, dict) else {}
    title = _app_title(schema, title_fallback)
    n = normalize_desc_count(count)
    tstart = normalize_table_start(table_start)
    candidates = build_usecase_description_candidates(
        schema, proposal_text=proposal_text
    )
    selected = select_usecase_descriptions(candidates, count=n)
    cases_out: list[dict[str, Any]] = []
    for i, c in enumerate(selected):
        cases_out.append(
            {
                "id": f"UCD-{i + 1:03d}",
                "table_no": _next_table_no(tstart, i),
                "name": c["name"],
                "actor": c["actor"],
                "summary": c["summary"],
                "flow": list(c.get("flow") or []),
                "menu_key": c.get("menu_key"),
                "side": c.get("side"),
                "kind": c.get("kind"),
                "source": c.get("source"),
                "score": c.get("score"),
            }
        )
    names = [c["name"] for c in cases_out]
    intro = (
        f"由于内容篇幅限制，本次仅针对{'、'.join(names)}这{len(cases_out)}个用例进行阐述。"
        if cases_out
        else "当前交付菜单不足以生成用例描述表。"
    )
    source_note = (
        "由交付 menus/roles/entities 推导事件流；开题正文仅影响选用与加分，不发明未交付功能"
        if (proposal_text or "").strip()
        else "由交付 menus/roles/entities 推导；未提供开题正文时按主路径优先级选用"
    )
    return {
        "title": title,
        "intro": intro,
        "source_note": source_note,
        "count": len(cases_out),
        "requested_count": n,
        "table_start": tstart,
        "cases": cases_out,
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
) -> dict[str, Any] | None:
    schema = _read_json(workspace / "domain.schema.json")
    if not schema:
        return None
    spec = _read_json(workspace / "spec.json")
    title_fb = str(spec.get("title") or "管理系统")
    return usecase_description_model(
        schema,
        proposal_text=proposal_text,
        count=count,
        table_start=table_start,
        title_fallback=title_fb,
    )
