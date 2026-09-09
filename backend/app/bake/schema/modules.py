"""论文功能模块图（与 E-R 同口径）。

默认「按身份」：优先解析开题/任务书等材料里的「{身份}功能模块划分为…」；
找不到再回落交付 roles + menus（界面小字提示，字不进 SVG）。
「按业务」：menus 按业务家族归类（对照用）。
细节开关：【】（）内子项默认不进图；展开后挂在一级模块下。
身份名不写死：从材料解析；回落用 schema.roles 动态 label。
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

_MODULE_LABELS_REL = Path("islands") / "module_labels.json"

# home / dashboard = 门户首页与管理端落地页，不是论文功能模块叶子
_SKIP_MENU_KEYS = frozenset({"home", "dashboard"})

# identity=按登录身份（默认）；biz=按业务；side 兼容旧参 → identity
MODULE_LAYOUTS = ("identity", "biz")
DEFAULT_MODULE_LAYOUT = "identity"

_SCHEMA_LEAF_NOTE = "以下模块名由交付菜单推断，非开题原文，仅供参考"

# 材料枚举：{身份}功能模块划分为：… / {身份}端主要包括：… 等
_IDENTITY_SECTION_RE = re.compile(
    r"(?P<label>"
    r"[^\s：:，,。；;\n]{1,16}?"
    r")"
    r"(?:端)?"
    r"(?:"
    r"功能模块划分为|"
    r"功能模块(?:主要)?(?:包括|包含|如下|为)|"
    r"功能(?:主要)?(?:包括|包含|如下|划分为|为)|"
    r"模块划分为|"
    r"主要功能(?:模块)?(?:包括|包含|如下|为)"
    r")"
    r"[：:]\s*",
)

# 前台/后台是叙述口径，框上改成身份名（有 schema 则用 roles）
_END_JARGON_USER = frozenset({"前台", "前台功能", "前台模块", "门户", "客户端", "顾客端"})
_END_JARGON_ADMIN = frozenset({"后台", "后台功能", "后台管理", "后台模块", "管理端"})

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
_EXAM_KEYS = frozenset(
    {
        "exam_papers",
        "exam_attempts",
        "exam_practice",
        "exam_rank",
        "exam_wrongbook",
        "exam_questions",
    }
)
_SURVEY_KEYS = frozenset(
    {
        "survey_forms",
        "survey_fill",
        "survey_mine",
        "survey_stats",
    }
)
_VOTE_KEYS = frozenset(
    {
        "vote_campaigns",
        "vote_cast",
        "vote_mine",
        "vote_candidates",
        "vote_results",
    }
)
_TIMEBANK_KEYS = frozenset(
    {
        "tb_account",
        "tb_ledger",
        "tb_accounts",
        "tb_ledger_admin",
    }
)
_SEAT_SELECT_KEYS = frozenset(
    {
        "seat_shows",
        "seat_map",
    }
)
_STOCK_IO_KEYS = frozenset(
    {
        "stock_moves",
        "stock_ledger",
    }
)
_E_SIGN_KEYS = frozenset(
    {
        "e_sign_mine",
        "e_sign_admin",
    }
)
_DOCLIB_KEYS = frozenset(
    {
        "doc_browse",
        "doc_mine",
        "doc_files",
        "doc_logs",
    }
)
_DM_KEYS = frozenset({"dm"})
_ADMIN_KEYS = frozenset({"dashboard", "users", "category", "lookup_site", "lookup_type", "deadline"})

# 从子菜单文案抽组名时用的词根（命中多数叶子才采用）
_BIZ_CORES: dict[str, tuple[str, ...]] = {
    "order": ("订单", "购物", "收货"),
    "ticket": ("申请", "报修", "工单", "待办", "跟进", "回复", "认领", "报名", "选课", "借阅", "申领"),
    "favorite": ("收藏",),
    "slot": ("预订", "预约", "时段", "挂号"),
    "content": ("公告", "资讯"),
    "guestbook": ("留言",),
    "exam": ("考试", "题库", "试卷", "成绩", "刷题", "错题"),
    "survey": ("问卷", "调研", "答卷", "回收"),
    "vote": ("投票", "评选", "选票", "计票", "十佳"),
    "dm": ("私信", "聊天"),
    "archive_log": ("打卡", "随访", "监测", "晨检"),
    "cart": ("购物车", "购物"),
}

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
    """与 er_labels.looks_latin 同口径：允许 AI/FAQ 等缩写混中文。"""
    from app.bake.schema.er_labels import looks_latin as _er_looks_latin

    return _er_looks_latin(text)


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
    if k in _EXAM_KEYS or k.startswith("exam_"):
        return "exam"
    if k in _SURVEY_KEYS or k.startswith("survey_"):
        return "survey"
    if k in _VOTE_KEYS or k.startswith("vote_"):
        return "vote"
    if k in _DOCLIB_KEYS or k.startswith("doc_"):
        return "doclib"
    if k in _TIMEBANK_KEYS or k.startswith("tb_"):
        return "timebank"
    if k in _SEAT_SELECT_KEYS or k.startswith("seat_"):
        return "seat_select"
    if k in _STOCK_IO_KEYS or k.startswith("stock_"):
        return "stock_io"
    if k in _E_SIGN_KEYS or k.startswith("e_sign"):
        return "e_sign"
    if k in _DM_KEYS:
        return "dm"
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


def _role_slot_label(roles: dict[str, Any], slot: str, fallback: str) -> str:
    """交付 roles 槽位显示名 → 身份框短名（不去「端」以外的硬编码业务词）。"""
    role = roles.get(slot) if isinstance(roles.get(slot), dict) else {}
    lab = str(role.get("label") or "").strip()
    if lab and not looks_latin(lab):
        lab = re.sub(r"[（(][^）)]*[）)]", "", lab).strip()
        if lab.endswith("端"):
            lab = lab[:-1]
        # 过长岗位名收成身份：含「管理」→ 管理员
        if len(lab) > 6 and ("管理" in lab or "主管" in lab or "总管" in lab):
            return "管理员"
        return lab or fallback
    return fallback


def _branch_label(roles: dict[str, Any], side: str) -> str:
    """兼容旧按端命名；按身份回落改用 _identity_label_from_slot。"""
    if side == "user":
        return _role_slot_label(roles, "user", "用户")
    return _role_slot_label(roles, "admin", "管理员")


def _identity_label_from_slot(roles: dict[str, Any], slot: str) -> str:
    if slot == "user":
        return _role_slot_label(roles, "user", "用户")
    if slot == "admin":
        return _role_slot_label(roles, "admin", "管理员")
    return _role_slot_label(roles, slot, slot)


def normalize_module_layout(layout: str | None) -> str:
    raw = str(layout or DEFAULT_MODULE_LAYOUT).strip().lower()
    if raw == "side":
        return "identity"
    return raw if raw in MODULE_LAYOUTS else DEFAULT_MODULE_LAYOUT


def _strip_identity_head(raw: str) -> str:
    lab = (raw or "").strip()
    lab = re.sub(r"^(?:本系统|系统的|系统|本)", "", lab)
    for suf in ("功能模块", "功能", "模块", "端"):
        if lab.endswith(suf) and len(lab) > len(suf):
            lab = lab[: -len(suf)]
    return lab.strip("的之 \t") or (raw or "").strip()


def _remap_end_jargon(label: str, schema: dict[str, Any] | None) -> str:
    """前台/后台不进身份框；映射到交付角色名或中性「用户/管理员」。"""
    lab = (label or "").strip()
    roles = schema.get("roles") if isinstance(schema, dict) and isinstance(schema.get("roles"), dict) else {}
    if lab in _END_JARGON_USER or lab.endswith("前台"):
        return _identity_label_from_slot(roles, "user")
    if lab in _END_JARGON_ADMIN or lab.endswith("后台"):
        return _identity_label_from_slot(roles, "admin")
    return lab


_BRACKET_OPEN = "【（("
_BRACKET_CLOSE = "】）)"
_BRACKET_PAIR = {"】": "【", "）": "（", ")": "("}


def _split_detail_items(detail: str) -> list[str]:
    """括号内顿号不切；顶层顿号/分号才切开。"""
    text = (detail or "").strip().strip("，,。；;、")
    if not text:
        return []
    out: list[str] = []
    buf: list[str] = []
    depth = 0

    def flush() -> None:
        nonlocal buf
        p = "".join(buf).strip().strip("。．.")
        buf = []
        if p and p not in out:
            out.append(p[:24])

    for ch in text:
        if ch in _BRACKET_OPEN:
            depth += 1
            buf.append(ch)
            continue
        if ch in _BRACKET_CLOSE and depth > 0:
            depth -= 1
            buf.append(ch)
            continue
        if depth == 0 and ch in "、；;，,\n":
            flush()
            continue
        buf.append(ch)
    flush()
    return out


def _peel_module_brackets(raw: str) -> tuple[str, list[str]]:
    """深度配对剥【】（）()；嵌套括号不误切。半角/全角闭括号可混用。"""
    text = (raw or "").strip().strip("，,。；;")
    if not text:
        return "", []
    details: list[str] = []
    name_chars: list[str] = []
    i = 0
    n = len(text)

    def _closes(opener: str, ch: str) -> bool:
        if opener == "【":
            return ch == "】"
        # （ 与 ( 互通
        return ch in "）)"

    while i < n:
        ch = text[i]
        if ch not in _BRACKET_OPEN:
            name_chars.append(ch)
            i += 1
            continue
        stack = [ch]
        j = i + 1
        while j < n and stack:
            c = text[j]
            if c in _BRACKET_OPEN:
                stack.append(c)
            elif _closes(stack[-1], c):
                stack.pop()
            elif c in _BRACKET_CLOSE and stack:
                # 开题常写「（…)」混用；任意闭括号弹出一层
                stack.pop()
            j += 1
        if not stack:
            inner = text[i + 1 : j - 1]
            details.extend(_split_detail_items(inner))
            i = j
        else:
            name_chars.append(ch)
            i += 1
    name = "".join(name_chars).strip().strip("，,。；;")
    return name, details


_MAX_MODULE_LABEL_LEN = 18  # 一级模块名；更长多半是吃进了后文章节


def _truncate_module_enum_body(body: str) -> str:
    """枚举句在首个顶层句号结束；避免末段身份吞掉后文「2.1.2 文献研究法…」。"""
    text = body or ""
    if not text:
        return ""
    depth = 0
    for i, ch in enumerate(text):
        if ch in _BRACKET_OPEN:
            depth += 1
            continue
        if ch in _BRACKET_CLOSE and depth > 0:
            depth -= 1
            continue
        if depth != 0:
            continue
        if ch in "。．":
            return text[:i]
        # 无句号时：章节号 + 研究/章节 起头也截断
        if ch.isdigit() and i + 2 < len(text) and text[i + 1] == ".":
            j = i
            while j < len(text) and (text[j].isdigit() or text[j] == "."):
                j += 1
            tail = text[j : j + 8]
            if j > i + 1 and any(k in tail for k in ("研究", "章", "节", "方法", "技术")):
                return text[:i]
    m = re.search(r"(?:模块|管理|分析|购物车|申请售后)[）】)]?[。．]?(\d+\.\d+)", text)
    if m:
        return text[: m.start(1)]
    return text


def _split_top_modules(body: str) -> list[tuple[str, list[str]]]:
    """一级模块名 + 括号细节；括号内不拆成并列一级。"""
    text = re.sub(r"\s+", "", _truncate_module_enum_body(body or ""))
    text = text.rstrip("。．.;；")
    if not text:
        return []
    items: list[tuple[str, list[str]]] = []
    buf: list[str] = []
    depth = 0

    def flush() -> None:
        nonlocal buf
        raw = "".join(buf).strip().strip("，,。；;")
        buf = []
        if not raw:
            return
        name, details = _peel_module_brackets(raw)
        if not name:
            return
        # 过长名 = 枚举越界吃进正文，丢弃
        if len(name) > _MAX_MODULE_LABEL_LEN:
            return
        items.append((name, details))

    for ch in text:
        if ch in _BRACKET_OPEN:
            depth += 1
            buf.append(ch)
            continue
        if ch in _BRACKET_CLOSE and depth > 0:
            depth -= 1
            buf.append(ch)
            continue
        if depth == 0 and ch in "、；;":
            flush()
            continue
        buf.append(ch)
    flush()
    return items


def parse_identity_modules(
    text: str,
    *,
    schema: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """从材料正文抽「身份 → 一级模块」；身份名不写死业务词表。"""
    raw = (text or "").replace("\r\n", "\n").replace("\r", "\n")
    if not raw.strip():
        return []
    # 换行常打断词，枚举段内去空白便于切分；匹配仍用去空白副本定位
    flat = re.sub(r"[ \t]+", "", raw)
    flat_one = re.sub(r"\n+", "", flat)
    matches = list(_IDENTITY_SECTION_RE.finditer(flat_one))
    if not matches:
        return []

    sections: list[dict[str, Any]] = []
    seen_lab: set[str] = set()
    for i, m in enumerate(matches):
        head = _strip_identity_head(m.group("label") or "")
        if not head or len(head) > 12:
            continue
        # 排除「系统功能模块划分为」这类无身份头
        if head in ("系统", "本系统", "总体", "整体"):
            continue
        label = _remap_end_jargon(head, schema)
        if not label or label in seen_lab:
            continue
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(flat_one)
        # 截到句号段末（下一段身份已由 matches 切开；末段另截后文）
        body = _truncate_module_enum_body(flat_one[start:end])
        mods = _split_top_modules(body)
        if not mods:
            continue
        seen_lab.add(label)
        sections.append(
            {
                "label": label,
                "modules": [{"label": n, "details": d} for n, d in mods],
            }
        )
    return sections


def apply_proposal_hints(model: dict[str, Any], proposal_text: str = "") -> dict[str, Any]:
    """用开题词微调「按业务」一级分支称呼（不增删节点；不改按身份框名）。"""
    if str(model.get("layout") or "") == "identity":
        return model
    text = proposal_text or ""
    root = model.get("root") if isinstance(model.get("root"), dict) else {}
    roots = root.get("children") or []
    if not isinstance(roots, list):
        return model
    for r in roots:
        if not isinstance(r, dict):
            continue
        rid = str(r.get("id") or "")
        if rid == "biz:user":
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
    """兼容旧调用：等价于按身份的 schema 回落。"""
    return _model_by_identity_from_schema(schema, title=title)


def _module_leaf_nodes(
    modules: list[dict[str, Any]],
    *,
    branch_id: str,
    source: str,
    expand_details: bool,
) -> list[dict]:
    out: list[dict] = []
    for i, mod in enumerate(modules):
        if not isinstance(mod, dict):
            continue
        lab = str(mod.get("label") or "").strip()
        if not lab:
            continue
        mid = f"{branch_id}:m{i}"
        details = [str(d).strip() for d in (mod.get("details") or []) if str(d).strip()]
        if expand_details and details:
            kids = [
                _node(f"{mid}:d{j}", d, source=f"{source}:detail")
                for j, d in enumerate(details)
            ]
            for k in kids:
                k["orient"] = "v"
            node = _node(mid, lab, source=source, children=kids)
            # 有子层时一级模块横排，细节竖排
        else:
            node = _node(mid, lab, source=source)
            node["orient"] = "v"
        out.append(node)
    return out


def _model_from_parsed_identities(
    sections: list[dict[str, Any]],
    *,
    title: str,
    expand_details: bool,
    leaf_source: str,
) -> dict[str, Any]:
    roots: list[dict] = []
    for i, sec in enumerate(sections):
        lab = str(sec.get("label") or "").strip()
        if not lab:
            continue
        bid = f"identity:{i}"
        kids = _module_leaf_nodes(
            list(sec.get("modules") or []),
            branch_id=bid,
            source=leaf_source,
            expand_details=expand_details,
        )
        if not kids:
            continue
        roots.append(_node(bid, lab, source="identity", children=kids))
    note = _SCHEMA_LEAF_NOTE if leaf_source == "schema" else ""
    return {
        "title": title,
        "layout": "identity",
        "leaf_source": leaf_source,
        "leaf_source_note": note,
        "expand_details": bool(expand_details),
        "root": _node("root", title, source="system", children=roots),
    }


def _menu_as_identity_modules(menus: list[Any], *, side: str) -> list[dict[str, Any]]:
    """menus → 一级模块；登录注册合成一项以贴近论文口径。"""
    nodes = _menu_nodes(menus, side=side)
    mods: list[dict[str, Any]] = []
    if side == "user" and nodes:
        mods.append({"label": "登录注册模块", "details": []})
    elif side == "admin" and nodes:
        mods.append({"label": "登录模块", "details": []})
    for n in nodes:
        lab = str(n.get("label") or "").strip()
        if not lab:
            continue
        if not lab.endswith("模块") and lab not in ("购物车", "数据分析", "申请售后", "售后管理"):
            lab = f"{lab}模块" if len(lab) <= 8 else lab
        mods.append({"label": lab, "details": []})
    return mods


def _model_by_identity_from_schema(
    schema: dict[str, Any],
    *,
    title: str,
    expand_details: bool = False,
) -> dict[str, Any]:
    roles = schema.get("roles") if isinstance(schema.get("roles"), dict) else {}
    menus = schema.get("menus") if isinstance(schema.get("menus"), dict) else {}
    caps = {str(c) for c in (schema.get("capabilities") or [])}
    user_menus = menus.get("user") or []
    admin_menus = menus.get("admin") or []
    has_user = bool(user_menus) or "org_users" in caps

    sections: list[dict[str, Any]] = []
    if has_user:
        sections.append(
            {
                "label": _identity_label_from_slot(roles, "user"),
                "modules": _menu_as_identity_modules(user_menus, side="user"),
            }
        )
    if admin_menus:
        sections.append(
            {
                "label": _identity_label_from_slot(roles, "admin"),
                "modules": _menu_as_identity_modules(admin_menus, side="admin"),
            }
        )

    model = _model_from_parsed_identities(
        sections,
        title=title,
        expand_details=expand_details,
        leaf_source="schema",
    )
    model["capabilities"] = list(schema.get("capabilities") or [])
    return model


def _model_by_identity(
    schema: dict[str, Any],
    *,
    title: str,
    proposal_text: str = "",
    expand_details: bool = False,
) -> dict[str, Any]:
    sections = parse_identity_modules(proposal_text, schema=schema)
    if sections:
        model = _model_from_parsed_identities(
            sections,
            title=title,
            expand_details=expand_details,
            leaf_source="materials",
        )
        model["capabilities"] = list(schema.get("capabilities") or [])
        return model
    return _model_by_identity_from_schema(
        schema, title=title, expand_details=expand_details
    )


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
        "leaf_source": "schema",
        "leaf_source_note": "",
        "expand_details": False,
        "root": _node("root", title, source="system", children=roots),
        "capabilities": list(schema.get("capabilities") or []),
    }


def module_model(
    schema: dict[str, Any] | None,
    *,
    proposal_text: str = "",
    title_fallback: str = "管理系统",
    layout: str = DEFAULT_MODULE_LAYOUT,
    expand_details: bool = False,
) -> dict[str, Any]:
    schema = schema if isinstance(schema, dict) else {}
    labels = schema.get("labels") if isinstance(schema.get("labels"), dict) else {}
    title = (
        str(labels.get("appName") or "").strip()
        or str(schema.get("title") or "").strip()
        or title_fallback
    )
    layout_n = normalize_module_layout(layout)
    if layout_n == "identity":
        model = _model_by_identity(
            schema,
            title=title,
            proposal_text=proposal_text,
            expand_details=expand_details,
        )
    else:
        model = _model_by_biz(schema, title=title)
    return apply_proposal_hints(model, proposal_text)


def build_module_model(
    workspace: Path,
    *,
    with_label_patch: bool = True,
    proposal_text: str = "",
    layout: str = DEFAULT_MODULE_LAYOUT,
    expand_details: bool = False,
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
        expand_details=expand_details,
    )
    if with_label_patch:
        model = apply_module_label_patch(model, load_module_label_patch(workspace))
    return model


def load_module_model(
    workspace: Path,
    *,
    proposal_text: str = "",
    layout: str = DEFAULT_MODULE_LAYOUT,
    expand_details: bool = False,
) -> dict[str, Any] | None:
    return build_module_model(
        workspace,
        with_label_patch=True,
        proposal_text=proposal_text,
        layout=layout,
        expand_details=expand_details,
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
_VBOX_W = 30.0
_GAP_X = 14.0
_GAP_Y = 52.0
_PAD = 28.0


def _box_w(label: str, *, orient: str = "h") -> float:
    if orient == "v":
        return _VBOX_W
    return max(72.0, _text_w(label, 12) + 28)


def _box_h(label: str, *, orient: str = "h") -> float:
    if orient == "v":
        n = max(1, len(label or ""))
        return max(56.0, n * 14.0 + 20.0)
    return _BOX_H


def _node_orient(node: dict) -> str:
    return "v" if str(node.get("orient") or "") == "v" else "h"


def _subtree_width(node: dict) -> float:
    kids = [c for c in (node.get("children") or []) if isinstance(c, dict)]
    self_w = _box_w(str(node.get("label") or ""), orient=_node_orient(node))
    if not kids:
        return self_w
    return max(self_w, sum(_subtree_width(c) for c in kids) + _GAP_X * (len(kids) - 1))


def _layout(node: dict, cx: float, top: float, positions: dict[str, dict]) -> None:
    label = str(node.get("label") or "")
    nid = str(node.get("id") or "")
    orient = _node_orient(node)
    w = _box_w(label, orient=orient)
    h = _box_h(label, orient=orient)
    positions[nid] = {
        "id": nid,
        "label": label,
        "orient": orient,
        "x": cx - w / 2,
        "y": top,
        "w": w,
        "h": h,
        "cx": cx,
        "cy": top + h / 2,
        "source": str(node.get("source") or ""),
    }
    kids = [c for c in (node.get("children") or []) if isinstance(c, dict)]
    if not kids:
        return
    widths = [_subtree_width(c) for c in kids]
    total = sum(widths) + _GAP_X * (len(kids) - 1)
    x = cx - total / 2
    child_top = top + h + _GAP_Y
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


def _vtext(label: str, cx: float, y0: float, h: float) -> str:
    """竖排：逐字自上而下。"""
    chars = list(label or "")
    if not chars:
        return ""
    step = (h - 16.0) / max(1, len(chars))
    start = y0 + 10.0 + step * 0.55
    parts = []
    for i, ch in enumerate(chars):
        parts.append(
            f'<text x="{_f(cx)}" y="{_f(start + i * step)}" text-anchor="middle" '
            f'font-size="12" font-family="Microsoft YaHei, SimSun, serif" '
            f'fill="#000">{_esc(ch)}</text>'
        )
    return "".join(parts)


def render_module_svg(model: dict[str, Any] | None) -> str:
    layout_tag = str((model or {}).get("layout") or "")
    if not model or not isinstance(model.get("root"), dict):
        return _svg_wrap(
            320,
            120,
            '<text x="24" y="64" fill="#000">暂无模块数据</text>',
            layout=layout_tag,
        )

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
        if p.get("orient") == "v":
            text = _vtext(str(p["label"]), p["cx"], p["y"], p["h"])
        else:
            text = (
                f'<text x="{_f(p["cx"])}" y="{_f(p["cy"] + 4)}" text-anchor="middle" '
                f'font-size="12" font-family="Microsoft YaHei, SimSun, serif" '
                f'fill="#000">{_esc(p["label"])}</text>'
            )
        node_parts.append(
            f'<g class="mod-node er-node" data-id="{_esc(p["id"])}" data-kind="module" '
            f'transform="translate(0,0)">'
            f'<rect x="{_f(p["x"])}" y="{_f(p["y"])}" width="{_f(p["w"])}" height="{_f(p["h"])}" '
            f'rx="0" ry="0" fill="#fff" stroke="#000" stroke-width="{sw}"/>'
            f"{text}</g>"
        )

    inner = (
        '<g class="mod-edges er-edges">'
        + "".join(edge_parts)
        + "</g>"
        + '<g class="mod-nodes er-nodes">'
        + "".join(node_parts)
        + "</g>"
    )
    return _svg_wrap(W, H, inner, layout=layout_tag)


def _f(n: float) -> str:
    return f"{n:.1f}"


def _svg_wrap(w: int, h: int, inner: str, *, layout: str = "") -> str:
    layout_attr = f' data-gf-layout="{_esc(layout)}"' if layout else ""
    return (
        f'<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
        f'viewBox="0 0 {w} {h}" class="module-diagram"{layout_attr}>'
        f'<rect class="er-paper" width="100%" height="100%" fill="#fff"/>'
        f"{inner}</svg>\n"
    )
