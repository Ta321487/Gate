"""从交付 schema 画论文功能模块图（与 E-R 同口径）。

真相来源：domain.schema.json 的 menus（唯一叶子来源）。
spec features 是接题/门禁清单，不另画「其它功能」——避免与菜单重复。
按业务拆：薄 key→家族归类；组是否出现、顺序、叶子文案都跟交付走。
开题材料只辅助中文命名（module_labels 补丁），不发明模块。
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

_MODULE_LABELS_REL = Path("islands") / "module_labels.json"

# home / dashboard = 门户首页与管理端落地页，不是论文功能模块叶子
_SKIP_MENU_KEYS = frozenset({"home", "dashboard"})

# 论文常用：按业务拆（biz）；工厂对照：按端拆（side）
MODULE_LAYOUTS = ("biz", "side")
DEFAULT_MODULE_LAYOUT = "biz"

# 仅「key → 业务家族」薄归类；叶子文案 / 组是否出现 / 组顺序均来自交付 menus。
# 未知 key 进 extra，不在这里发明中文名。
# 分类管理归管理员（教材「系统管理」口径）；收藏审批流按文案进收藏族。
_USER_KEYS = frozenset({"profile", "messages"})
_ARCHIVE_KEYS = frozenset({"archive", "browse_history", "my_archive", "archive_logs"})
_FAVORITE_KEYS = frozenset({"favorites"})
_CART_KEYS = frozenset({"cart"})
_ORDER_KEYS = frozenset({"my_orders", "orders", "addresses", "coupons", "order_reviews"})
_TICKET_KEYS = frozenset({"my_tickets", "ticket_pending", "ticket_records", "week_calendar"})
_SLOT_KEYS = frozenset({"slots", "my_reservations", "reservations"})
_CONTENT_KEYS = frozenset({"content"})
_GUESTBOOK_KEYS = frozenset({"guestbook"})
_ADMIN_KEYS = frozenset({"dashboard", "users", "category", "lookup_site", "lookup_type", "deadline"})

# 从子菜单文案抽组名时用的词根（命中多数叶子才采用）
_BIZ_CORES: dict[str, tuple[str, ...]] = {
    "order": ("订单", "购物", "收货"),
    "ticket": ("申请", "报修", "工单", "待办", "跟进", "回复", "认领", "报名", "选课", "借阅", "申领"),
    "favorite": ("收藏",),
    "slot": ("预订", "预约", "时段", "挂号"),
    "content": ("公告", "资讯"),
    "guestbook": ("留言",),
    "archive_log": ("打卡", "随访", "监测", "晨检"),
    "cart": ("购物车", "购物"),
}

_LATIN_RE = re.compile(r"[A-Za-z]")
_LABEL_NOISE = ("我的", "管理", "浏览", "待办", "办理", "时段", "催办", "字典")


def _esc(s: str) -> str:
    return (
        (s or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _text_w(s: str, px: float = 12.0) -> float:
    w = 0.0
    for ch in s or "":
        w += px if ord(ch) > 127 else px * 0.55
    return w


def looks_latin(text: str) -> bool:
    return bool(_LATIN_RE.search(text or ""))


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def module_labels_path(workspace: Path) -> Path:
    return workspace / _MODULE_LABELS_REL


def load_module_label_patch(workspace: Path) -> dict[str, Any]:
    return _read_json(module_labels_path(workspace))


def save_module_label_patch(workspace: Path, patch: dict[str, Any]) -> None:
    path = module_labels_path(workspace)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(patch, ensure_ascii=False, indent=2), encoding="utf-8")


def _menu_label(item: dict[str, Any]) -> str:
    """叶子名以交付 label 为准；拉丁文留给 module_labels 补丁，不在此硬编码中文表。"""
    lab = str(item.get("label") or "").strip()
    key = str(item.get("key") or "").strip()
    # 待办菜单「××确认」在论文里写成「××审核」更顺
    if key == "ticket_pending" and lab.endswith("确认"):
        lab = lab[:-2] + "审核"
    if lab and not looks_latin(lab):
        return lab
    return lab or key or "模块"


def _biz_id_for_item(key: str, label: str = "") -> str:
    """按菜单 key 归家族；收藏类审批流看文案，避免进泛化工单块。"""
    k = str(key or "").strip()
    lab = str(label or "")
    if not k:
        return "extra"
    if k in _USER_KEYS:
        return "user"
    if k in _FAVORITE_KEYS or (k in _TICKET_KEYS and "收藏" in lab):
        return "favorite"
    if k in _ARCHIVE_KEYS:
        return "archive"
    if k in _CART_KEYS:
        return "cart"
    if k in _ORDER_KEYS or k.startswith("order_"):
        return "order"
    if k in _TICKET_KEYS or "ticket" in k:
        return "ticket"
    if k in _SLOT_KEYS or "reserv" in k:
        return "slot"
    if k in _CONTENT_KEYS:
        return "content"
    if k in _GUESTBOOK_KEYS:
        return "guestbook"
    if k in _ADMIN_KEYS or k.startswith("lookup_"):
        return "admin"
    return "extra"


def _biz_id_for_key(key: str) -> str:
    return _biz_id_for_item(key, "")


def _node(nid: str, label: str, *, source: str, children: list[dict] | None = None) -> dict:
    out: dict[str, Any] = {"id": nid, "label": label, "source": source}
    if children:
        out["children"] = children
    return out


def _menu_nodes(menus: list[Any], *, side: str) -> list[dict]:
    out: list[dict] = []
    seen: set[str] = set()
    for raw in menus or []:
        if not isinstance(raw, dict):
            continue
        key = str(raw.get("key") or "").strip()
        if not key or key in _SKIP_MENU_KEYS or key in seen:
            continue
        seen.add(key)
        out.append(_node(f"{side}:{key}", _menu_label(raw), source=f"menu:{side}"))
    return out


def _branch_label(roles: dict[str, Any], side: str) -> str:
    if side == "user":
        role = roles.get("user") if isinstance(roles.get("user"), dict) else {}
        lab = str(role.get("label") or "").strip()
        if lab and not looks_latin(lab):
            return f"{lab}端" if not lab.endswith("端") else lab
        return "用户端"
    role = roles.get("admin") if isinstance(roles.get("admin"), dict) else {}
    lab = str(role.get("label") or "").strip()
    if lab and not looks_latin(lab):
        # 「商城主管（总管）」→ 管理端，避免过长
        if "管" in lab or "管理员" in lab:
            return "管理端"
        return f"{lab}" if lab.endswith("端") else "管理端"
    return "管理端"


def normalize_module_layout(layout: str | None) -> str:
    raw = str(layout or DEFAULT_MODULE_LAYOUT).strip().lower()
    return raw if raw in MODULE_LAYOUTS else DEFAULT_MODULE_LAYOUT


def apply_proposal_hints(model: dict[str, Any], proposal_text: str = "") -> dict[str, Any]:
    """用开题词微调一级分支称呼（不增删节点）。"""
    text = proposal_text or ""
    root = model.get("root") if isinstance(model.get("root"), dict) else {}
    roots = root.get("children") or []
    if not isinstance(roots, list):
        return model
    for r in roots:
        if not isinstance(r, dict):
            continue
        rid = str(r.get("id") or "")
        if rid == "branch:user":
            if re.search(r"前台|门户|顾客端|客户端", text):
                r["label"] = "前台功能"
            elif re.search(r"学生端|读者端|用户端", text):
                r["label"] = "用户端"
        elif rid == "branch:admin":
            if re.search(r"后台管理|后台功能|管理端", text):
                r["label"] = "后台管理"
            elif re.search(r"管理员模块", text):
                r["label"] = "管理员模块"
        elif rid == "branch:extra":
            if re.search(r"扩展功能|辅助功能", text):
                r["label"] = "扩展功能"
        elif rid == "biz:user":
            if re.search(r"用户模块|注册登录", text):
                r["label"] = "用户模块"
        elif rid == "biz:admin":
            if re.search(r"管理员模块|系统管理", text):
                r["label"] = "管理员模块"
        elif rid == "biz:extra":
            if re.search(r"扩展功能|辅助功能", text):
                r["label"] = "扩展功能"
    return model


def _index_menu_items(menus: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    """menu key → 各端出现的叶子（同 key 不同 label 都保留，如浏览/管理）。"""
    indexed: dict[str, list[dict[str, Any]]] = {}
    seen_pair: set[tuple[str, str]] = set()
    for side in ("user", "admin"):
        for raw in menus.get(side) or []:
            if not isinstance(raw, dict):
                continue
            key = str(raw.get("key") or "").strip()
            if not key or key in _SKIP_MENU_KEYS:
                continue
            lab = _menu_label(raw)
            pair = (key, lab)
            if pair in seen_pair:
                continue
            seen_pair.add(pair)
            indexed.setdefault(key, []).append(
                _node(f"{side}:{key}", lab, source=f"menu:{side}")
            )
    return indexed


def _archive_biz_label(schema: dict[str, Any]) -> str:
    entities = schema.get("entities") if isinstance(schema.get("entities"), dict) else {}
    ent = entities.get("archive") if isinstance(entities.get("archive"), dict) else {}
    lab = str(ent.get("label") or "").strip()
    if lab and not looks_latin(lab):
        return lab if lab.endswith("模块") else f"{lab}模块"
    return "业务模块"


def _strip_label_noise(lab: str) -> str:
    out = lab
    for a in _LABEL_NOISE:
        out = out.replace(a, "")
    return out.strip() or lab


def _infer_biz_label(biz_id: str, kids: list[dict], schema: dict[str, Any]) -> str:
    """组名：档案跟实体；用户/管理员固定；其余从交付子菜单文案推断。"""
    if biz_id == "archive":
        return _archive_biz_label(schema)
    if biz_id == "user":
        return "用户模块"
    if biz_id == "admin":
        return "管理员模块"
    if biz_id == "favorite":
        return "收藏模块"
    if biz_id == "extra":
        return "其它功能"

    non_auth = [c for c in kids if str(c.get("source") or "") != "auth"]
    labs = [str(c.get("label") or "").strip() for c in non_auth]
    labs = [x for x in labs if x]
    if not labs:
        return "功能模块"
    if len(labs) == 1:
        return labs[0]

    cores = _BIZ_CORES.get(biz_id) or ()
    need = max(1, (len(labs) + 1) // 2)
    for core in cores:
        if sum(1 for lab in labs if core in lab) >= need:
            return core if core.endswith("模块") else f"{core}模块"

    stems = [_strip_label_noise(x) for x in labs]
    # 最短且出现在全部原文中的词干
    for stem in sorted({s for s in stems if s}, key=len):
        if all(stem in lab for lab in labs):
            return stem if stem.endswith("模块") else f"{stem}模块"

    stem0 = stems[0] if stems else labs[0]
    return stem0 if stem0.endswith("模块") else f"{stem0}模块"


def _merge_slot_order_buckets(
    buckets: dict[str, list[dict]],
    biz_order: list[str],
) -> None:
    """酒店等同时有号源预订与订单壳时，合并为一支，避免预订+订单并立。"""
    if "slot" not in buckets or "order" not in buckets:
        return
    buckets["slot"].extend(buckets.pop("order"))
    if "order" in biz_order:
        biz_order.remove("order")


def _auth_nodes() -> list[dict]:
    return [
        _node("auth:register", "注册", source="auth"),
        _node("auth:login", "登录", source="auth"),
    ]


def _menu_keys_in_order(menus: dict[str, Any]) -> list[str]:
    """用户端 → 管理端出现顺序，决定业务块先后。"""
    out: list[str] = []
    seen: set[str] = set()
    for side in ("user", "admin"):
        for raw in menus.get(side) or []:
            if not isinstance(raw, dict):
                continue
            key = str(raw.get("key") or "").strip()
            if not key or key in _SKIP_MENU_KEYS or key in seen:
                continue
            seen.add(key)
            out.append(key)
    return out


def _reorder_biz_ids(biz_ids: list[str]) -> list[str]:
    """用户靠前、管理员与其它靠后；中间保持菜单首现顺序。"""
    head = [b for b in biz_ids if b == "user"]
    mid = [b for b in biz_ids if b not in ("user", "admin", "extra")]
    tail = [b for b in biz_ids if b == "admin"]
    extra = [b for b in biz_ids if b == "extra"]
    return head + mid + tail + extra


def _model_by_side(schema: dict[str, Any], *, title: str) -> dict[str, Any]:
    roles = schema.get("roles") if isinstance(schema.get("roles"), dict) else {}
    menus = schema.get("menus") if isinstance(schema.get("menus"), dict) else {}
    caps = {str(c) for c in (schema.get("capabilities") or [])}
    user_kids = _menu_nodes(menus.get("user") or [], side="user")
    admin_kids = _menu_nodes(menus.get("admin") or [], side="admin")
    has_user_surface = bool(user_kids) or "org_users" in caps

    roots: list[dict] = []
    if has_user_surface:
        roots.append(
            _node(
                "branch:user",
                _branch_label(roles, "user"),
                source="branch",
                children=_auth_nodes() + user_kids,
            )
        )
    if admin_kids:
        roots.append(
            _node(
                "branch:admin",
                _branch_label(roles, "admin"),
                source="branch",
                children=admin_kids,
            )
        )

    return {
        "title": title,
        "layout": "side",
        "root": _node("root", title, source="system", children=roots),
        "capabilities": list(schema.get("capabilities") or []),
    }


def _model_by_biz(schema: dict[str, Any], *, title: str) -> dict[str, Any]:
    menus = schema.get("menus") if isinstance(schema.get("menus"), dict) else {}
    caps = {str(c) for c in (schema.get("capabilities") or [])}
    indexed = _index_menu_items(menus)
    has_user_surface = bool(menus.get("user")) or "org_users" in caps

    buckets: dict[str, list[dict]] = {}
    biz_order: list[str] = []

    def _ensure(biz_id: str) -> list[dict]:
        if biz_id not in buckets:
            buckets[biz_id] = []
            biz_order.append(biz_id)
        return buckets[biz_id]

    if has_user_surface:
        _ensure("user").extend(_auth_nodes())

    for key in _menu_keys_in_order(menus):
        for item in indexed.get(key) or []:
            lab = str(item.get("label") or "")
            _ensure(_biz_id_for_item(key, lab)).append(item)

    _merge_slot_order_buckets(buckets, biz_order)

    roots: list[dict] = []
    for biz_id in _reorder_biz_ids(biz_order):
        kids = buckets.get(biz_id) or []
        if not kids:
            continue
        group_lab = _infer_biz_label(biz_id, kids, schema)
        # 单叶子且与组名相同 → 一级叶子（如「购物车」）
        if len(kids) == 1 and str(kids[0].get("label") or "") == group_lab:
            leaf = dict(kids[0])
            leaf["id"] = f"biz:{biz_id}"
            leaf["source"] = "biz"
            roots.append(leaf)
        else:
            roots.append(_node(f"biz:{biz_id}", group_lab, source="biz", children=kids))

    return {
        "title": title,
        "layout": "biz",
        "root": _node("root", title, source="system", children=roots),
        "capabilities": list(schema.get("capabilities") or []),
    }


def module_model(
    schema: dict[str, Any] | None,
    *,
    proposal_text: str = "",
    title_fallback: str = "管理系统",
    layout: str = DEFAULT_MODULE_LAYOUT,
) -> dict[str, Any]:
    schema = schema if isinstance(schema, dict) else {}
    labels = schema.get("labels") if isinstance(schema.get("labels"), dict) else {}
    title = (
        str(labels.get("appName") or "").strip()
        or str(schema.get("title") or "").strip()
        or title_fallback
    )
    layout_n = normalize_module_layout(layout)
    if layout_n == "side":
        model = _model_by_side(schema, title=title)
    else:
        model = _model_by_biz(schema, title=title)
    return apply_proposal_hints(model, proposal_text)


def build_module_model(
    workspace: Path,
    *,
    with_label_patch: bool = True,
    proposal_text: str = "",
    layout: str = DEFAULT_MODULE_LAYOUT,
) -> dict[str, Any] | None:
    schema = _read_json(workspace / "domain.schema.json")
    if not schema:
        return None
    spec = _read_json(workspace / "spec.json")
    title_fb = str(spec.get("title") or "管理系统")
    model = module_model(
        schema,
        proposal_text=proposal_text,
        title_fallback=title_fb,
        layout=layout,
    )
    if with_label_patch:
        model = apply_module_label_patch(model, load_module_label_patch(workspace))
    return model


def load_module_model(
    workspace: Path,
    *,
    proposal_text: str = "",
    layout: str = DEFAULT_MODULE_LAYOUT,
) -> dict[str, Any] | None:
    return build_module_model(
        workspace,
        with_label_patch=True,
        proposal_text=proposal_text,
        layout=layout,
    )


def iter_nodes(model: dict[str, Any] | None) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []

    def walk(n: dict | None) -> None:
        if not isinstance(n, dict):
            return
        out.append(n)
        for c in n.get("children") or []:
            if isinstance(c, dict):
                walk(c)

    if isinstance(model, dict):
        walk(model.get("root") if isinstance(model.get("root"), dict) else None)
    return out


def collect_module_label_gaps(model: dict[str, Any] | None) -> list[dict[str, str]]:
    gaps: list[dict[str, str]] = []
    for n in iter_nodes(model):
        lab = str(n.get("label") or "")
        if looks_latin(lab):
            gaps.append(
                {
                    "id": str(n.get("id") or ""),
                    "label": lab,
                    "source": str(n.get("source") or ""),
                }
            )
    return gaps


def sanitize_module_label_patch(
    data: dict | None,
    gaps: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    data = data or {}
    allowed = {g["id"] for g in (gaps or [])} if gaps is not None else None
    raw_nodes = data.get("nodes")
    if isinstance(raw_nodes, dict):
        items = raw_nodes
    else:
        items = {k: v for k, v in data.items() if k not in ("mode", "nodes")}
    nodes_out: dict[str, str] = {}
    for k, v in items.items():
        key = str(k).strip()
        if not key or (allowed is not None and key not in allowed):
            continue
        lab = str(v or "").strip().replace("\n", "")
        lab = re.sub(r"\s+", "", lab)
        if not lab or looks_latin(lab):
            continue
        nodes_out[key] = lab[:16]
    return {"nodes": nodes_out}


def apply_module_label_patch(model: dict[str, Any], patch: dict | None) -> dict[str, Any]:
    clean = sanitize_module_label_patch(patch)
    nmap = clean.get("nodes") or {}
    if not nmap:
        return model

    def walk(n: dict) -> None:
        nid = str(n.get("id") or "")
        if nid in nmap:
            n["label"] = nmap[nid]
        for c in n.get("children") or []:
            if isinstance(c, dict):
                walk(c)

    root = model.get("root")
    if isinstance(root, dict):
        walk(root)
        model["title"] = str(root.get("label") or model.get("title") or "")
    return model


# —— SVG 树形功能模块图 ——

_BOX_H = 34.0
_GAP_X = 14.0
_GAP_Y = 52.0
_PAD = 28.0


def _box_w(label: str) -> float:
    return max(72.0, _text_w(label, 12) + 28)


def _subtree_width(node: dict) -> float:
    kids = [c for c in (node.get("children") or []) if isinstance(c, dict)]
    self_w = _box_w(str(node.get("label") or ""))
    if not kids:
        return self_w
    return max(self_w, sum(_subtree_width(c) for c in kids) + _GAP_X * (len(kids) - 1))


def _layout(node: dict, cx: float, top: float, positions: dict[str, dict]) -> None:
    label = str(node.get("label") or "")
    nid = str(node.get("id") or "")
    w = _box_w(label)
    positions[nid] = {
        "id": nid,
        "label": label,
        "x": cx - w / 2,
        "y": top,
        "w": w,
        "h": _BOX_H,
        "cx": cx,
        "cy": top + _BOX_H / 2,
        "source": str(node.get("source") or ""),
    }
    kids = [c for c in (node.get("children") or []) if isinstance(c, dict)]
    if not kids:
        return
    widths = [_subtree_width(c) for c in kids]
    total = sum(widths) + _GAP_X * (len(kids) - 1)
    x = cx - total / 2
    child_top = top + _BOX_H + _GAP_Y
    for c, cw in zip(kids, widths):
        child_cx = x + cw / 2
        _layout(c, child_cx, child_top, positions)
        x += cw + _GAP_X


def _edges(node: dict) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    nid = str(node.get("id") or "")
    for c in node.get("children") or []:
        if not isinstance(c, dict):
            continue
        cid = str(c.get("id") or "")
        if nid and cid:
            out.append((nid, cid))
        out.extend(_edges(c))
    return out


def render_module_svg(model: dict[str, Any] | None) -> str:
    if not model or not isinstance(model.get("root"), dict):
        return _svg_wrap(320, 120, '<text x="24" y="64" fill="#000">暂无模块数据</text>')

    root = model["root"]
    positions: dict[str, dict] = {}
    tree_w = _subtree_width(root)
    _layout(root, tree_w / 2 + _PAD, _PAD, positions)

    max_r = 0.0
    max_b = 0.0
    for p in positions.values():
        max_r = max(max_r, p["x"] + p["w"])
        max_b = max(max_b, p["y"] + p["h"])
    W = int(max_r + _PAD)
    H = int(max_b + _PAD)

    edge_parts: list[str] = []
    for a, b in _edges(root):
        pa, pb = positions.get(a), positions.get(b)
        if not pa or not pb:
            continue
        x1, y1 = pa["cx"], pa["y"] + pa["h"]
        x2, y2 = pb["cx"], pb["y"]
        mid_y = (y1 + y2) / 2
        edge_parts.append(
            f'<path class="mod-edge" d="M {_f(x1)} {_f(y1)} V {_f(mid_y)} H {_f(x2)} V {_f(y2)}" '
            f'fill="none" stroke="#000" stroke-width="1"/>'
        )

    node_parts: list[str] = []
    for p in positions.values():
        is_root = p["id"] == "root"
        sw = "1.5" if is_root else "1"
        node_parts.append(
            f'<g class="mod-node er-node" data-id="{_esc(p["id"])}" data-kind="module" '
            f'transform="translate(0,0)">'
            f'<rect x="{_f(p["x"])}" y="{_f(p["y"])}" width="{_f(p["w"])}" height="{_f(p["h"])}" '
            f'rx="0" ry="0" fill="#fff" stroke="#000" stroke-width="{sw}"/>'
            f'<text x="{_f(p["cx"])}" y="{_f(p["cy"] + 4)}" text-anchor="middle" '
            f'font-size="12" font-family="Microsoft YaHei, SimSun, serif" '
            f'fill="#000">{_esc(p["label"])}</text></g>'
        )

    inner = (
        '<g class="mod-edges er-edges">'
        + "".join(edge_parts)
        + "</g>"
        + '<g class="mod-nodes er-nodes">'
        + "".join(node_parts)
        + "</g>"
    )
    return _svg_wrap(W, H, inner)


def _f(n: float) -> str:
    return f"{n:.1f}"


def _svg_wrap(w: int, h: int, inner: str) -> str:
    return (
        f'<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
        f'viewBox="0 0 {w} {h}" class="module-diagram">'
        f'<rect class="er-paper" width="100%" height="100%" fill="#fff"/>'
        f"{inner}</svg>\n"
    )
