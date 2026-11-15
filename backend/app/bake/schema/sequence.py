"""论文「系统序列图」：固定 3 张，画法对齐六条规则。

真源：bake workspace 的 domain.schema.json（交付 menus/roles/entities）
     + 可选 bake 包 *Controller.java / Vue 按钮文案。
禁止：kind 中文句库、长句槽位模板、示例「自习室」题材。
左侧角色名取交付岗位；页面/控制器/数据库为四槽位层名。
"""

from __future__ import annotations

import html
import json
import re
from pathlib import Path
from typing import Any

from app.bake.schema.testcases import _entity_label, _role_label
from app.bake.schema.usecase_descriptions import (
    build_usecase_description_candidates,
)

SEQUENCE_COUNT = 3

# 序列图默认选题：每张业务图已内嵌登录，不再单占一席画「纯登录」
_SEQUENCE_SKIP_KINDS = frozenset({"auth_login", "auth_register"})
# 壳/辅助菜单：有主路径时让位
_SEQUENCE_DEMOTE_KINDS = frozenset(
    {
        "users",
        "profile",
        "messages",
        "banners",
        "online_sessions",
        "schedule_jobs",
        "site_stat",
        "open",
        "content_user",
        "content_admin",
        "addresses",
        "lookup",
    }
)
# 答辩主链路加分（跨域：单据/交易/预约/评价）
_SEQUENCE_CORE_BOOST: dict[str, int] = {
    "cart": 42,
    "my_orders": 40,
    "orders": 34,
    "my_tickets": 40,
    "ticket_pending": 36,
    "ticket_records": 24,
    "reserve_user": 38,
    "reservations": 32,
    "order_reviews_user": 30,
    "order_reviews_admin": 22,
    "order_reviews": 28,
    "archive_user": 18,
    "archive_admin": 16,
    "guestbook_user": 14,
    "favorites": 12,
    "dm": 10,
    "category": 8,
}

_PARTICIPANTS = ("actor", "page", "controller", "db")
_PARTICIPANT_LABELS = {
    "page": "页面",
    "controller": "控制器",
    "db": "数据库",
}

# 英文方法名 → 中文动词（词级映射，不拼整句模板）
_METHOD_VERB_ZH: dict[str, str] = {
    "login": "验证",
    "register": "注册",
    "list": "查询",
    "page": "分页查询",
    "get": "查询",
    "detail": "查询详情",
    "find": "查询",
    "save": "保存",
    "create": "保存",
    "add": "新增",
    "insert": "保存",
    "update": "更新",
    "edit": "更新",
    "delete": "删除",
    "remove": "删除",
    "approve": "审核通过",
    "reject": "驳回",
    "confirm": "确认",
    "confirmreceive": "确认收货",
    "cancel": "取消",
    "submit": "提交",
    "complete": "办结",
    "ship": "发货",
}

_OP_SUMMARY_RE = re.compile(
    r'@Operation\s*\(\s*(?:[^)]*?summary\s*=\s*"([^"]+)"|summary\s*=\s*"([^"]+)")',
    re.S,
)
_MAPPING_RE = re.compile(
    r'@(?:Get|Post|Put|Delete|Patch|Request)Mapping\b[^;{]*?\b(?:public|protected)\s+\S+\s+(\w+)\s*\(',
    re.S,
)
_METHOD_PUBLIC_RE = re.compile(
    r'(?:public|protected)\s+(?:static\s+)?[\w.<>,\s\[\]]+\s+(\w+)\s*\([^;{]*\)\s*(?:throws\s+[^{]+)?\{',
)
_VUE_BTN_RE = re.compile(
    r">\s*([^<>{%]{2,24})\s*(?:<span\b[^>]*>.*?</span>\s*)?</(?:el-button|button|n-button|a)\b",
    re.I | re.S,
)
# 按钮文案走 {{ labelVar }} 时：从图侧按 schema.labels / verbs 解析，禁止写死域词进 Vue
# 后缀放宽到 48：兼容「{{ batchHireLabel }}（{{ selectedIds.length }}）」一类数量徽标
_VUE_MUSTACHE_BTN_RE = re.compile(
    r">\s*\{\{\s*([\w.$]+)\s*\}\}([^<]{0,48})</(?:el-button|button|n-button|a)\b",
    re.I,
)
# mustache 变量 → (labels键, verbs键, 无配置时的图面兜底；兜底仅扫图用，界面仍跟 labels)
_VUE_MUSTACHE_BTN_RESOLVE: dict[str, tuple[str, str, str]] = {
    "batchHireLabel": ("batchHireLabel", "", "批量录用"),
    "batchRejectLabel": ("batchRejectLabel", "", "批量淘汰"),
    "renewVerb": ("renewVerb", "renew", "续借"),
    "fineWaiveLabel": ("fineWaiveLabel", "", "罚款减免"),
    "lostVerb": ("bookLostVerb", "reportLost", "申报丢失"),
    "claimHoldVerb": ("bookHoldClaimVerb", "claimHold", "确认借阅"),
}
_SKIP_METHODS = {
    "toString",
    "hashCode",
    "equals",
    "builder",
    "main",
    "init",
    "afterPropertiesSet",
}


def _esc(s: str) -> str:
    return html.escape(str(s or ""), quote=True)


def _f(v: float) -> str:
    return f"{v:.1f}"


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return data if isinstance(data, dict) else None


def _short_role(label: str, *, side: str) -> str:
    lab = re.sub(r"[（(][^）)]*[）)]", "", str(label or "")).strip()
    if lab:
        return lab
    return "用户" if side == "user" else "管理员"


def candidate_id(case: dict[str, Any]) -> str:
    side = str(case.get("side") or "user")
    key = str(case.get("menu_key") or "")
    kind = str(case.get("kind") or "")
    return f"{side}::{key}::{kind}"


def list_sequence_candidates(
    schema: dict[str, Any],
    *,
    proposal_text: str = "",
) -> list[dict[str, Any]]:
    raw = build_usecase_description_candidates(schema, proposal_text=proposal_text)
    out: list[dict[str, Any]] = []
    for c in raw:
        if not isinstance(c, dict):
            continue
        cid = candidate_id(c)
        side = str(c.get("side") or "user")
        actor = _short_role(str(c.get("actor") or ""), side=side)
        out.append(
            {
                "id": cid,
                "side": side,
                "menu_key": str(c.get("menu_key") or ""),
                "kind": str(c.get("kind") or ""),
                "label": str(c.get("label") or ""),
                "name": str(c.get("name") or ""),
                "actor": actor,
                "score": int(c.get("score") or 0),
            }
        )
    return out


def default_sequence_selection(candidates: list[dict[str, Any]]) -> list[str]:
    """序列图默认 3 席：主链路优先，跳过纯登录（业务图已带登录序幕）。"""
    ranked: list[tuple[int, dict[str, Any]]] = []
    for c in candidates:
        if not isinstance(c, dict):
            continue
        kind = str(c.get("kind") or "").strip()
        if kind in _SEQUENCE_SKIP_KINDS:
            continue
        score = int(c.get("score") or 0) + int(_SEQUENCE_CORE_BOOST.get(kind, 0))
        if kind in _SEQUENCE_DEMOTE_KINDS:
            score -= 45
        ranked.append((score, c))
    ranked.sort(
        key=lambda x: (
            -x[0],
            0 if str(x[1].get("side") or "") == "user" else 1,
            str(x[1].get("menu_key") or ""),
        )
    )

    picked: list[dict[str, Any]] = []
    used_keys: set[tuple[str, str]] = set()
    used_kinds: set[str] = set()

    def _try(c: dict[str, Any]) -> bool:
        if len(picked) >= SEQUENCE_COUNT:
            return False
        side = str(c.get("side") or "")
        key = str(c.get("menu_key") or "")
        kind = str(c.get("kind") or "")
        dedupe = (side, key)
        if dedupe in used_keys or kind in used_kinds:
            return False
        used_keys.add(dedupe)
        used_kinds.add(kind)
        picked.append(c)
        return True

    for _sc, c in ranked:
        _try(c)
        if len(picked) >= SEQUENCE_COUNT:
            break

    # 若三席全是同一端，尝试用另一端高分候选换掉末席
    if len(picked) == SEQUENCE_COUNT:
        sides = {str(c.get("side") or "") for c in picked}
        if len(sides) == 1:
            want = "admin" if "user" in sides else "user"
            for _sc, c in ranked:
                if str(c.get("side") or "") != want:
                    continue
                kind = str(c.get("kind") or "")
                if kind in used_kinds:
                    continue
                dedupe = (str(c.get("side") or ""), str(c.get("menu_key") or ""))
                if dedupe in used_keys:
                    continue
                # 换掉得分最低的一席（列表末）
                drop = picked[-1]
                used_keys.discard(
                    (str(drop.get("side") or ""), str(drop.get("menu_key") or ""))
                )
                used_kinds.discard(str(drop.get("kind") or ""))
                picked[-1] = c
                used_keys.add(dedupe)
                used_kinds.add(kind)
                break

    if len(picked) < SEQUENCE_COUNT:
        # 候选不足时回补（含曾跳过的），避免打不开
        for c in candidates:
            if not isinstance(c, dict):
                continue
            _try(c)
            if len(picked) >= SEQUENCE_COUNT:
                break

    return [candidate_id(c) for c in picked[:SEQUENCE_COUNT]]


def parse_selection_ids(raw: str | list[str] | None) -> list[str] | None:
    if raw is None:
        return None
    if isinstance(raw, list):
        ids = [str(x).strip() for x in raw if str(x).strip()]
    else:
        ids = [x.strip() for x in str(raw).split(",") if x.strip()]
    return ids or None


def _validate_selection(ids: list[str], candidates: list[dict[str, Any]]) -> list[str]:
    if len(ids) != SEQUENCE_COUNT:
        raise ValueError(f"序列图须恰好选择 {SEQUENCE_COUNT} 个交付功能，当前 {len(ids)} 个")
    known = {str(c["id"]) for c in candidates}
    bad = [i for i in ids if i not in known]
    if bad:
        raise ValueError(f"未知功能 id：{', '.join(bad)}")
    if len(set(ids)) != SEQUENCE_COUNT:
        raise ValueError("所选功能不可重复")
    return ids


def _method_verb(name: str) -> str:
    n = str(name or "").strip()
    low = n.lower()
    for key, verb in _METHOD_VERB_ZH.items():
        if low == key or low.startswith(key):
            return verb
    # camelCase 首段
    m = re.match(r"^([A-Za-z]+)", n)
    if m:
        head = m.group(1).lower()
        if head in _METHOD_VERB_ZH:
            return _METHOD_VERB_ZH[head]
    return ""


def _scan_controllers(workspace: Path) -> list[dict[str, Any]]:
    root = workspace / "backend" / "src" / "main" / "java"
    if not root.is_dir():
        return []
    out: list[dict[str, Any]] = []
    for path in root.rglob("*Controller.java"):
        try:
            src = path.read_text(encoding="utf-8")
        except Exception:
            continue
        class_m = re.search(r"\bclass\s+(\w+Controller)\b", src)
        cname = class_m.group(1) if class_m else path.stem
        ops: list[dict[str, str]] = []
        # @Operation 紧邻的方法
        for m in re.finditer(
            r'@Operation\s*\((.*?)\)\s*(?:@[A-Za-z][\w.]*\s*(?:\([^)]*\))?\s*)*'
            r'(?:public|protected)\s+[\w.<>,\s\[\]]+\s+(\w+)\s*\(',
            src,
            re.S,
        ):
            args, meth = m.group(1), m.group(2)
            if meth in _SKIP_METHODS:
                continue
            sm = re.search(r'summary\s*=\s*"([^"]+)"', args)
            summary = (sm.group(1).strip() if sm else "") or ""
            verb = _method_verb(meth)
            ops.append(
                {
                    "method": meth,
                    "summary": summary,
                    "verb": verb,
                    "source": "controller",
                }
            )
        if not ops:
            for m in _MAPPING_RE.finditer(src):
                meth = m.group(1)
                if meth in _SKIP_METHODS:
                    continue
                ops.append(
                    {
                        "method": meth,
                        "summary": "",
                        "verb": _method_verb(meth),
                        "source": "controller",
                    }
                )
        if not ops:
            for m in _METHOD_PUBLIC_RE.finditer(src):
                meth = m.group(1)
                if meth in _SKIP_METHODS or meth[0].isupper():
                    continue
                verb = _method_verb(meth)
                if not verb:
                    continue
                ops.append(
                    {
                        "method": meth,
                        "summary": "",
                        "verb": verb,
                        "source": "controller",
                    }
                )
        out.append({"class": cname, "path": str(path), "ops": ops, "src_lower": src.lower()})
    return out


# 菜单 kind → 优先扫描的 Vue 文件名片段（正匹配；无匹配则不用 Vue 按钮）
_VUE_FILE_HINTS: dict[str, tuple[str, ...]] = {
    "auth_login": ("Login", "Auth"),
    "auth_register": ("Register", "Auth"),
    "archive_user": ("ArchiveBrowse", "Archive"),
    "archive_admin": ("ArchiveAdmin", "ArchiveManage", "Archive"),
    "cart": ("Cart",),
    "my_orders": ("MyOrders", "Order"),
    "orders": ("OrderAdmin", "Orders", "Order"),
    "addresses": ("Address",),
    "profile": ("Profile",),
    "messages": ("Message",),
    "content_user": ("Notice", "Content"),
    "content_admin": ("NoticeAdmin", "ContentAdmin", "Notice"),
    "my_tickets": ("Ticket", "MyTicket"),
    "ticket_pending": ("TicketPending", "TicketAdmin", "Ticket"),
    "ticket_records": ("TicketRecord", "Ticket"),
    "reserve_user": ("Reserv", "Booking"),
    "reservations": ("Reserv", "Booking"),
    "guestbook_user": ("Guestbook",),
    "guestbook_admin": ("Guestbook",),
    "favorites": ("Favorite",),
    "users": ("UserAdmin", "Users"),
    "category": ("Category",),
    "dm": ("Dm", "Chat"),
    "order_reviews_user": ("OrderReview", "Review", "MyReview"),
    "order_reviews_admin": ("OrderReview", "ReviewAdmin", "Review"),
}

# 仅当所在 Vue 文件已命中本功能时，才允许这些短操作词入选
_SHORT_ACTION_BTNS = frozenset(
    {
        "保存",
        "提交",
        "确认",
        "新增",
        "编辑",
        "删除",
        "查询",
        "登录",
        "注册",
        "发布",
        "通过",
        "驳回",
        "导出清单",
        "复制清单",
        "取消收藏",
    }
)


def _schema_labels(schema: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(schema, dict):
        return {}
    labels = schema.get("labels")
    return labels if isinstance(labels, dict) else {}


def _schema_verbs(schema: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(schema, dict):
        return {}
    verbs = schema.get("verbs")
    if isinstance(verbs, dict):
        return verbs
    labels = _schema_labels(schema)
    nested = labels.get("verbs")
    return nested if isinstance(nested, dict) else {}


def _resolve_mustache_btn(var_name: str, schema: dict[str, Any] | None) -> str:
    """把 Vue {{ batchHireLabel }} 解成当前域文案（优先 schema，再 verbs，最后图面兜底）。"""
    key = str(var_name or "").split(".")[-1].strip()
    spec = _VUE_MUSTACHE_BTN_RESOLVE.get(key)
    if not spec:
        return ""
    lab_key, verb_key, fallback = spec
    labels = _schema_labels(schema)
    verbs = _schema_verbs(schema)
    if lab_key:
        got = str(labels.get(lab_key) or "").strip()
        if got:
            return got
    if verb_key:
        got = str(verbs.get(verb_key) or "").strip()
        if got:
            return got
    return fallback


def _schema_demo_actions(schema: dict[str, Any] | None) -> dict[str, str]:
    """当前域演示动作文案（供 prefer_submit，跟 labels 走）。"""
    return {
        "batch_hire": _resolve_mustache_btn("batchHireLabel", schema),
        "batch_reject": _resolve_mustache_btn("batchRejectLabel", schema),
        "renew": _resolve_mustache_btn("renewVerb", schema),
        "fine_waive": _resolve_mustache_btn("fineWaiveLabel", schema),
        "lost": _resolve_mustache_btn("lostVerb", schema),
        "claim_hold": _resolve_mustache_btn("claimHoldVerb", schema),
    }


def _vue_path_score(path: Path, *, menu_key: str, kind: str, menu_label: str) -> int:
    """按文件名/路径与 kind、menu 的正相关性打分；无关页自然为 0，不采。"""
    name = path.stem
    blob = str(path).replace("\\", "/")
    score = 0
    hints = list(_VUE_FILE_HINTS.get(kind) or ())
    if menu_key:
        camel = "".join(p.capitalize() for p in menu_key.split("_") if p)
        if camel:
            hints.append(camel)
        hints.append(menu_key.replace("_", ""))
    for h in hints:
        if h and h.lower() in name.lower():
            score += 20
        if h and h.lower() in blob.lower():
            score += 8
    if menu_label and menu_label in name:
        score += 15
    return score


def _btn_fits_feature(
    lab: str,
    *,
    menu_label: str,
    entity: str,
    kind: str = "",
    extra_short: frozenset[str] | set[str] | None = None,
) -> bool:
    """按钮是否属于当前勾选功能：含本菜单/实体名，或为本功能页上的短操作词。

    不含菜单/实体的长复合按钮（任意其它能力页上的「提交xxx」）一律不收——
    不靠领域黑名单堵串台。
    """
    del kind  # 保留形参与调用方一致；归属靠文案与菜单/实体对齐
    lab = str(lab or "").strip()
    if not lab:
        return False
    menu_label = str(menu_label or "").strip()
    entity = str(entity or "").strip()
    shorts = set(_SHORT_ACTION_BTNS)
    if extra_short:
        shorts |= {str(x).strip() for x in extra_short if str(x).strip()}
    if lab in shorts:
        return True
    if menu_label and menu_label in lab:
        return True
    if entity and entity in lab:
        return True
    return False


def _scan_vue_buttons(
    workspace: Path,
    menu_label: str,
    *,
    menu_key: str = "",
    kind: str = "",
    entity: str = "",
    schema: dict[str, Any] | None = None,
) -> list[str]:
    """只从文件名已命中本功能的 Vue 页取按钮；扫不到则空列表（退回 schema 文案）。"""
    fe = workspace / "frontend" / "src"
    if not fe.is_dir():
        return []
    needle = (menu_label or "").strip()
    entity = (entity or "").strip()
    demo = _schema_demo_actions(schema)
    extra_short = {v for v in demo.values() if v}
    ranked: list[tuple[int, Path]] = []
    for path in fe.rglob("*.vue"):
        if "views" not in str(path).replace("\\", "/"):
            continue
        sc = _vue_path_score(path, menu_key=menu_key, kind=kind, menu_label=needle)
        # 必须靠 kind/menu 文件名命中；禁止仅因正文偶尔出现实体词就收整页按钮
        if sc < 20:
            continue
        if needle:
            try:
                head = path.read_text(encoding="utf-8")[:4000]
            except Exception:
                head = ""
            if needle in head:
                sc += 12
            if entity and entity in head:
                sc += 6
        ranked.append((sc, path))
    ranked.sort(key=lambda x: (-x[0], str(x[1])))
    hits: list[str] = []
    seen: set[str] = set()

    def _push(lab: str) -> bool:
        lab = re.sub(r"\s+", "", str(lab or "").strip())
        # 截掉数量后缀：xxx（3）→ xxx
        lab = re.sub(r"[（(]\d+[）)]$", "", lab)
        if not lab or lab in seen or len(lab) > 20:
            return False
        if any(x in lab for x in ("{{", "v-", "el-", "n-", "http")):
            return False
        if not _btn_fits_feature(
            lab,
            menu_label=needle,
            entity=entity,
            kind=kind,
            extra_short=extra_short,
        ):
            return False
        seen.add(lab)
        hits.append(lab)
        return len(hits) >= 6

    for _sc, path in ranked[:6]:
        try:
            text = path.read_text(encoding="utf-8")
        except Exception:
            continue
        # 先收 schema 解析的 mustache（域演示动作），再收字面按钮，避免「通过/提交」占满 6 格
        for m in _VUE_MUSTACHE_BTN_RE.finditer(text):
            key = str(m.group(1) or "").strip().split(".")[-1]
            zh = _resolve_mustache_btn(key, schema)
            if not zh:
                continue
            if _push(zh):
                return hits
        for m in _VUE_BTN_RE.finditer(text):
            if _push(m.group(1)):
                return hits
    return hits


# 仅浏览、默认不画写路径的 kind（与 _build_business_phase.need_write 黑名单对齐）
BROWSE_SEQUENCE_KINDS = frozenset(
    {
        "archive_user",
        "content_user",
        "messages",
        # my_orders 含确认收货/支付写路径，不进纯浏览
        "ticket_records",
        "favorites",
        "browse_history",
    }
)


def _ent_label(entities: dict[str, Any], key: str) -> str:
    e = entities.get(key)
    if isinstance(e, dict):
        return str(e.get("label") or "").strip()
    return ""


# 与 usecase_descriptions._flow_spec 对齐的短相位（序列四槽位用，禁止容器套话）
# 缺省 kind 走 _phases_from_flow_spec / 通用兜底，换域不加专线也能像样。
_KIND_WRITE_PHASES: dict[str, dict[str, str]] = {
    "cart": {
        "select": "核对商品与数量",
        "confirm": "去结算",
        "submit": "提交结算",
        "save": "保存订单与明细",
        "ok": "结算成功",
    },
    "order_reviews_user": {
        "select": "选择已购商品",
        "confirm": "填写评价内容",
        "submit": "提交评价",
        "save": "保存评价信息",
        "ok": "评价提交成功",
    },
    "order_reviews": {
        "select": "选择已购商品",
        "confirm": "填写评价内容",
        "submit": "提交评价",
        "save": "保存评价信息",
        "ok": "评价提交成功",
    },
    "order_reviews_admin": {
        "select": "选择待处理评价",
        "confirm": "处理评价",
        "submit": "提交评价处理",
        "save": "保存评价信息",
        "ok": "评价处理成功",
    },
    # 买家订单默认画确认收货（与 MyOrders「确认收货」按钮、参考答辩口径一致）
    "my_orders": {
        "select": "选择已发货订单",
        "confirm": "确认收货",
        "submit": "提交确认收货",
        "save": "更新订单为已完成",
        "ok": "确认收货成功",
    },
    "my_orders_pay": {
        "select": "选择待支付订单",
        "confirm": "确认支付",
        "submit": "提交支付",
        "save": "更新订单为已支付",
        "ok": "支付成功",
    },
    "orders": {
        "select": "选择待发货订单",
        "confirm": "办理发货",
        "submit": "提交发货",
        "save": "更新订单为已发货",
        "ok": "发货成功",
    },
    "addresses": {
        "select": "选择收货地址",
        "confirm": "编辑地址信息",
        "submit": "保存地址",
        "save": "保存地址信息",
        "ok": "地址保存成功",
    },
    "dm": {
        "select": "选择会话",
        "confirm": "填写消息内容",
        "submit": "发送私信",
        "save": "保存消息",
        "ok": "发送成功",
    },
    "guestbook_user": {
        "select": "填写留言内容",
        "confirm": "确认留言",
        "submit": "提交留言",
        "save": "保存留言信息",
        "ok": "留言提交成功",
    },
    "guestbook_admin": {
        "select": "选择留言",
        "confirm": "回复留言",
        "submit": "提交回复",
        "save": "保存留言状态",
        "ok": "留言处理成功",
    },
    "favorites": {
        "select": "选择收藏项",
        "confirm": "取消或管理收藏",
        "submit": "更新收藏",
        "save": "保存收藏信息",
        "ok": "收藏更新成功",
    },
    "reserve_user": {
        "select": "选择可预约项或时段",
        "confirm": "填写预约信息",
        "submit": "提交预约",
        "save": "保存预约信息",
        "ok": "预约提交成功",
    },
    "reservations": {
        "select": "选择预约记录",
        "confirm": "办理预约",
        "submit": "提交办理",
        "save": "更新预约状态",
        "ok": "预约办理成功",
    },
    "my_tickets": {
        "select": "填写申请表单",
        "confirm": "核对申请信息",
        "submit": "提交申请",
        "save": "保存单据信息",
        "ok": "申请提交成功",
    },
    "ticket_pending": {
        "select": "选择待办单据",
        "confirm": "审核通过或驳回",
        "submit": "提交审核结果",
        "save": "更新单据状态",
        "ok": "审核完成",
    },
    "ticket_records": {
        "select": "选择办理记录",
        "confirm": "查看办理详情",
        "submit": "查询记录",
        "save": "读取办理数据",
        "ok": "查询完成",
    },
    "archive_admin": {
        "select": "选择主数据记录",
        "confirm": "填写或编辑必填项",
        "submit": "保存主数据",
        "save": "写入主数据",
        "ok": "主数据保存成功",
    },
    "archive_user": {
        "select": "浏览或检索列表",
        "confirm": "打开详情",
        "submit": "查询详情",
        "save": "读取详情数据",
        "ok": "展示详情",
    },
    "content_user": {
        "select": "选择公告",
        "confirm": "阅读正文",
        "submit": "打开公告",
        "save": "读取公告内容",
        "ok": "展示公告",
    },
    "content_admin": {
        "select": "新建公告",
        "confirm": "填写标题与正文",
        "submit": "发布公告",
        "save": "保存公告",
        "ok": "公告发布成功",
    },
    "profile": {
        "select": "打开个人资料",
        "confirm": "修改可编辑字段",
        "submit": "保存资料",
        "save": "写入个人资料",
        "ok": "资料保存成功",
    },
    "messages": {
        "select": "选择消息",
        "confirm": "打开消息详情",
        "submit": "标记已读",
        "save": "更新消息状态",
        "ok": "消息已读",
    },
    "users": {
        "select": "选择用户",
        "confirm": "启用停用或重置密码",
        "submit": "提交用户管理",
        "save": "更新用户状态",
        "ok": "用户管理成功",
    },
    "category": {
        "select": "选择分类",
        "confirm": "编辑分类信息",
        "submit": "保存分类",
        "save": "写入分类数据",
        "ok": "分类保存成功",
    },
    "lookup": {
        "select": "选择字典项",
        "confirm": "编辑字典项",
        "submit": "保存字典项",
        "save": "写入字典数据",
        "ok": "字典保存成功",
    },
    "coupons": {
        "select": "选择优惠券",
        "confirm": "领取或查看券",
        "submit": "领取优惠券",
        "save": "保存领券记录",
        "ok": "领券成功",
    },
    "browse_history": {
        "select": "查看足迹列表",
        "confirm": "打开浏览记录",
        "submit": "查询足迹",
        "save": "读取足迹数据",
        "ok": "展示足迹",
    },
    "week_calendar": {
        "select": "切换日期",
        "confirm": "查看当日安排",
        "submit": "查询日程",
        "save": "读取日程数据",
        "ok": "展示日程",
    },
    "deadline": {
        "select": "选择催办记录",
        "confirm": "查看逾期详情",
        "submit": "查询催办",
        "save": "读取催办数据",
        "ok": "展示催办",
    },
    "archive_logs": {
        "select": "打开监测表单",
        "confirm": "填写监测字段",
        "submit": "提交监测记录",
        "save": "保存监测数据",
        "ok": "监测提交成功",
    },
    "blind_pools": {
        "select": "打开盲盒奖池",
        "confirm": "填写奖品权重与隐藏款",
        "submit": "保存奖池",
        "save": "写入奖池配置",
        "ok": "奖池保存成功",
    },
    "group_campaigns": {
        "select": "选择拼团活动",
        "confirm": "设置成团人数与截止",
        "submit": "保存拼团",
        "save": "写入拼团配置",
        "ok": "拼团保存成功",
    },
    "delivery_slots": {
        "select": "选择配送时段",
        "confirm": "填写余量与达达类型",
        "submit": "保存时段",
        "save": "写入时段配置",
        "ok": "时段保存成功",
    },
    "price_spans": {
        "select": "选择加价区间",
        "confirm": "填写日期与倍率",
        "submit": "保存加价规则",
        "save": "写入加价配置",
        "ok": "加价规则保存成功",
    },
    "purchase_permits": {
        "select": "选择待审申请",
        "confirm": "通过或驳回",
        "submit": "提交审核结果",
        "save": "更新审核状态",
        "ok": "审核完成",
    },
    "my_permits": {
        "select": "打开购买审核表单",
        "confirm": "上传审核资料",
        "submit": "提交购买申请",
        "save": "保存待审申请",
        "ok": "申请已提交",
    },
    "line_specs": {
        "select": "选择规格项",
        "confirm": "新增或停用规格",
        "submit": "保存规格选项",
        "save": "写入规格名单",
        "ok": "规格保存成功",
    },
    "lost_clues": {
        "select": "选择线索留言",
        "confirm": "查看线索内容",
        "submit": "打开线索",
        "save": "读取线索数据",
        "ok": "展示线索",
    },
    "consigns": {
        "select": "选择待质检寄卖",
        "confirm": "通过上架或驳回",
        "submit": "提交质检结果",
        "save": "更新寄卖状态",
        "ok": "质检完成",
    },
    "my_consigns": {
        "select": "打开寄卖表单",
        "confirm": "填写名称期望价与成色",
        "submit": "提交寄卖",
        "save": "保存待质检寄卖",
        "ok": "寄卖已提交",
    },
    "open": {
        "select": "查看主列表或主表单",
        "confirm": "完成页面主操作",
        "submit": "提交操作",
        "save": "保存业务数据",
        "ok": "操作成功",
    },
}


def _shorten_flow_action(line: str, *, menu_label: str = "") -> str:
    """从用例描述长句抽短操作，供序列自调用/提交用。"""
    s = str(line or "").strip()
    if not s:
        return ""
    # 去掉角色前缀「买家/管理员…」
    s = re.sub(r"^\{[^}]+\}", "", s)
    s = re.sub(r"^(买家|商家|管理员|平台管理员|读者|用户|馆员|经办员|员工)", "", s)
    s = s.strip(" ，,。；;")
    ml = (menu_label or "").strip()
    if ml:
        s = s.replace(f"「{ml}」", "").replace(ml, "")
    # 常见长句压缩
    for pat, repl in (
        (r".*核对(商品与数量|商品).*", "核对商品与数量"),
        (r".*选择可预约项或时段.*", "选择可预约项或时段"),
        (r".*填写申请表单.*", "填写申请表单"),
        (r".*填写评分与评价.*", "填写评价内容"),
        (r".*执行通过/?同意或驳回.*", "审核通过或驳回"),
        (r".*执行确认、发货.*", "办理发货"),
        (r".*新增或编辑.*并填写必填项.*", "填写或编辑必填项"),
        (r".*选择或新建会话.*发送私信.*", "发送私信"),
        (r".*填写留言正文并提交.*", "填写留言内容"),
        (r".*打开一条待办.*", "选择待办单据"),
        (r".*打开待处理订单.*", "选择待处理订单"),
        (r".*点击保存.*", "点击保存"),
        (r".*点击提交.*", "点击提交"),
        (r".*点击发布或保存.*", "发布或保存"),
    ):
        m = re.match(pat, s)
        if m:
            return repl if isinstance(repl, str) else (m.group(1) if m.lastindex else s)
    # 截到约 16 字，避免长叙述进序列框
    s = re.sub(r"^(在|进入|打开|点击)", "", s).strip()
    if len(s) > 16:
        for sep in ("并", "，", ",", "后", "，"):
            if sep in s:
                left = s.split(sep, 1)[0].strip()
                if 4 <= len(left) <= 16:
                    s = left
                    break
        if len(s) > 16:
            s = s[:16]
    return s


def _phases_from_flow_spec(
    kind: str,
    *,
    stem: str,
    menu_label: str,
) -> dict[str, str] | None:
    """用用例描述 flow 抽 select/confirm/submit，与材料表同源。"""
    try:
        from app.bake.schema.usecase_descriptions import _flow_spec
    except Exception:
        return None
    spec = _flow_spec(kind)
    if not isinstance(spec, dict):
        return None
    flow = [str(x).strip() for x in (spec.get("flow") or []) if str(x).strip()]
    if not flow:
        return None
    # 跳过登录/转至界面句，取操作句
    actions: list[str] = []
    for line in flow:
        if any(
            x in line
            for x in (
                "登录成功",
                "打开系统登录",
                "系统转至",
                "系统展示",
                "系统保存",
                "系统更新",
                "系统按",
                "系统提示",
                "系统同步",
                "校验通过",
            )
        ):
            # 系统句有时可作 save/ok，先跳过当 select
            continue
        short = _shorten_flow_action(line, menu_label=menu_label)
        if short and short not in actions:
            actions.append(short)
    if not actions:
        return None
    st = (stem or menu_label or "业务").strip()
    ml = (menu_label or "").strip()
    select = actions[0]
    confirm = actions[1] if len(actions) > 1 else actions[0]
    submit = actions[-1] if len(actions) > 2 else (
        "提交" + (st if st and st not in confirm else "操作")
    )
    # 若仍像容器套话则放弃，交给上层其它兜底
    if _is_container_template_phrase(select, stem=st, menu_label=ml):
        return None
    return {
        "select": select,
        "confirm": confirm,
        "submit": submit if not _is_container_template_phrase(submit, stem=st, menu_label=ml) else f"提交{st}变更",
        "save": f"保存{st}信息" if st else "保存业务数据",
        "ok": f"{ml or st}成功" if (ml or st) else "操作成功",
    }


def _my_orders_write_phases(vue_btns: list[str] | None = None) -> dict[str, str]:
    """买家订单：有「确认收货」或未单独强调支付时走收货；仅支付按钮则走支付。"""
    btns = [str(b or "") for b in (vue_btns or [])]
    has_recv = any("收货" in b for b in btns)
    has_pay = any("支付" in b for b in btns)
    if has_pay and not has_recv:
        return dict(_KIND_WRITE_PHASES["my_orders_pay"])
    return dict(_KIND_WRITE_PHASES["my_orders"])


def _kind_write_fallbacks(
    kind: str,
    *,
    stem: str,
    menu_label: str,
    side: str = "user",
    vue_btns: list[str] | None = None,
) -> dict[str, str]:
    """无可用 Vue/Controller 文案时的写路径措辞。

    优先显式相位表 → 用例描述 flow 同源 → 子串别名 → 禁容器套话的通用兜底。
    """
    k = (kind or "").strip().lower()
    ml = (menu_label or "").strip()
    st = (stem or ml or "记录").strip()
    side_n = (side or "user").strip().lower() or "user"
    adminish = side_n == "admin" or k.endswith("_admin") or k in ("orders",)

    # 侧别优先：同名 kind 在用户侧走用户相位（如 reservations 作座位预约入口）
    if k == "reservations" and not adminish:
        return dict(_KIND_WRITE_PHASES["reserve_user"])
    if k == "guestbook" and not adminish:
        return dict(_KIND_WRITE_PHASES["guestbook_user"])

    if k == "my_orders":
        return _my_orders_write_phases(vue_btns)

    if k in _KIND_WRITE_PHASES:
        row = dict(_KIND_WRITE_PHASES[k])
        if k == "archive_admin" and st and st not in ("记录", "主数据"):
            row["select"] = f"选择{st}"
            row["confirm"] = f"编辑{st}信息"
            row["submit"] = f"保存{st}"
            row["save"] = f"保存{st}信息"
            row["ok"] = f"{ml or st}成功"
        return row

    # 别名 / 子串
    if "review" in k:
        key = "order_reviews_admin" if adminish else "order_reviews_user"
        return dict(_KIND_WRITE_PHASES[key])
    if k in ("my_orders",) or (
        "order" in k and "review" not in k and k != "cart" and not adminish
    ):
        return _my_orders_write_phases(vue_btns)
    if k == "orders" or ("order" in k and "review" not in k and adminish):
        return dict(_KIND_WRITE_PHASES["orders"])
    if "guestbook" in k:
        key = "guestbook_admin" if adminish else "guestbook_user"
        return dict(_KIND_WRITE_PHASES[key])
    if "reserve" in k or "slot" in k:
        key = "reservations" if adminish else "reserve_user"
        return dict(_KIND_WRITE_PHASES.get(key) or _KIND_WRITE_PHASES["reserve_user"])
    if "ticket" in k:
        if "pending" in k:
            return dict(_KIND_WRITE_PHASES["ticket_pending"])
        if "record" in k:
            return dict(_KIND_WRITE_PHASES["ticket_records"])
        return dict(_KIND_WRITE_PHASES["my_tickets"])
    if "archive" in k:
        key = "archive_admin" if adminish else "archive_user"
        row = dict(_KIND_WRITE_PHASES[key])
        if key == "archive_admin" and st:
            row["select"] = f"选择{st}"
            row["confirm"] = f"编辑{st}信息"
            row["submit"] = f"保存{st}"
            row["save"] = f"保存{st}信息"
            row["ok"] = f"{ml or st}成功"
        return row
    if "content" in k:
        key = "content_admin" if adminish else "content_user"
        return dict(_KIND_WRITE_PHASES[key])

    from_flow = _phases_from_flow_spec(k, stem=st, menu_label=ml)
    if from_flow:
        return from_flow

    # 通用：容器名（车/单/夹）勿拼「选择购物车」
    if st and any(ch in st for ch in ("车", "单", "夹", "篮", "箱")) and len(st) <= 6:
        return {
            "select": "选择记录",
            "confirm": "确认操作",
            "submit": "提交变更",
            "save": "保存变更",
            "ok": f"{ml or st}成功",
        }
    return dict(_KIND_WRITE_PHASES["open"])


def _is_container_template_phrase(text: str, *, stem: str, menu_label: str = "") -> bool:
    """识别「选择购物车 / 确认我的订单 / 新增购物车信息」一类套话。"""
    t = str(text or "").strip()
    if not t:
        return False
    nouns = [n for n in ((stem or "").strip(), (menu_label or "").strip()) if n]
    for noun in nouns:
        for verb in ("选择", "确认", "新增", "提交", "保存"):
            if t == f"{verb}{noun}" or t == f"{verb}{noun}信息":
                return True
    return False


def _feature_entity(schema: dict[str, Any], *, kind: str, menu_label: str = "") -> str:
    """按功能 kind 解析本图应用的业务实体中文名，禁止无脑用全局 archive 串台。

    例：favorites → 收藏；my_tickets → 报名单/借阅单；archive_* 才用影片/图书等。
    """
    entities = schema.get("entities") if isinstance(schema.get("entities"), dict) else {}
    menu_label = str(menu_label or "").strip()
    archive = _entity_label(schema)

    if kind.startswith("auth_"):
        return ""

    # 须先于 order 子串：order_reviews_* 含 "order"，否则整图文案变成「订单」
    if "review" in kind or kind.endswith("_reviews"):
        return _ent_label(entities, "review") or "评价"

    if (
        ("order" in kind and "review" not in kind)
        or kind in ("cart", "my_orders", "orders")
    ):
        if kind == "cart":
            return _ent_label(entities, "cart") or "购物车"
        return _ent_label(entities, "order") or menu_label or archive

    if "reserve" in kind or kind == "reservations":
        return _ent_label(entities, "reservation") or menu_label or archive

    if kind in ("my_tickets", "ticket_pending", "ticket_records") or "ticket" in kind:
        return _ent_label(entities, "ticket") or menu_label or archive

    if kind == "favorites":
        return _ent_label(entities, "favorites") or "收藏"

    if kind in ("content_user", "content_admin"):
        return _ent_label(entities, "content") or "公告"

    if kind == "messages":
        return "消息"

    if kind in ("guestbook_user", "guestbook_admin"):
        return _ent_label(entities, "guestbook") or "留言"

    if kind == "addresses":
        return "地址"

    if kind == "profile":
        return "资料"

    if kind == "users":
        return "用户"

    if kind == "category":
        return _ent_label(entities, "category") or "分类"

    if kind == "dm":
        return "私信"

    if "archive" in kind:
        return archive

    # 未知 kind：优先菜单名，最后才 archive（避免收藏类功能落到片单/点播）
    return menu_label or archive


def _pick_controller(
    controllers: list[dict[str, Any]],
    *,
    kind: str,
    menu_key: str,
    menu_label: str,
    entity: str,
) -> dict[str, Any] | None:
    if not controllers:
        return None
    # order_reviews* 不得吃到 OrderController（"order" 子串误匹配）
    is_review = "review" in (kind or "").lower() or "review" in (menu_key or "").lower()
    keys = [
        menu_key.lower().replace("_", ""),
        re.sub(r"[^a-z0-9]", "", menu_label.lower()) if menu_label.isascii() else "",
        "auth" if kind.startswith("auth_") else "",
        "review" if is_review else "",
        "orderreview" if is_review else "",
        (
            "order"
            if (not is_review and ("order" in kind or "cart" in kind))
            else ""
        ),
        "reserv" if "reserve" in kind else "",
        "ticket" if "ticket" in kind else "",
        "favorite" if kind == "favorites" else "",
        "user" if kind == "users" else "",
        "product" if "archive" in kind else "",
        "archive" if "archive" in kind else "",
        "notice" if "content" in kind else "",
        "message" if kind == "messages" else "",
    ]
    keys = [k for k in keys if k]
    file_hints = [h.lower() for h in (_VUE_FILE_HINTS.get(kind) or ()) if h]

    def score(c: dict[str, Any]) -> int:
        blob = (c["class"] + c.get("src_lower", "")).lower()
        cname = str(c.get("class") or "").lower()
        s = 0
        for k in keys:
            if k and k in blob:
                s += 10
        for h in file_hints:
            if h and h in cname:
                s += 18
            if h and h in blob:
                s += 8
        if entity and entity in c.get("src_lower", ""):
            s += 5
        if kind.startswith("auth_") and "auth" in cname:
            s += 20
        return s

    ranked = sorted(controllers, key=lambda c: (-score(c), c["class"]))
    best = ranked[0]
    # 零分禁止回落到无关 Controller（曾导致收藏图吃到 ArchiveController）
    if score(best) <= 0 and not kind.startswith("auth_"):
        return None
    return best


def _collapse_dup_zh(text: str) -> str:
    """折叠「登录登录」「查询查询」等连续重复词（2～6 字）。"""
    t = str(text or "").strip()
    if not t:
        return t
    prev = None
    while prev != t:
        prev = t
        t = re.sub(r"([\u4e00-\u9fff]{2,6})\1+", r"\1", t)
    return t


def _leaks_code_ident(text: str) -> bool:
    """文案是否夹带英文标识符（方法名/驼峰），论文序列图禁止出现。"""
    return bool(re.search(r"[A-Za-z]{2,}", str(text or "")))


def _join_verb_noun(verb: str, noun: str) -> str:
    """动词 + 名词，避免叠词；任一段含代码标识则整段不可用。"""
    v = str(verb or "").strip()
    n = str(noun or "").strip()
    if _leaks_code_ident(v) or _leaks_code_ident(n):
        # 名词侧若是交付中文可保留；动词侧是代码名则丢掉动词
        if _leaks_code_ident(v):
            v = ""
        if _leaks_code_ident(n):
            n = ""
    if not v:
        return _collapse_dup_zh(n)
    if not n:
        return _collapse_dup_zh(v)
    if n in v or v.endswith(n):
        return _collapse_dup_zh(v)
    if v in n:
        return _collapse_dup_zh(n)
    return _collapse_dup_zh(f"{v}{n}")


def _op_text(op: dict[str, str], *, entity: str, menu_label: str) -> str:
    """Controller 操作 → 中文短句。无中文摘要且方法名无法映射为中文动词时返回空，由调用方用菜单/实体兜底。

    禁止把 suggest/getList 等英文方法名直接拼进图（如 suggest图书）。
    """
    noun = (entity or menu_label or "").strip()
    if _leaks_code_ident(noun):
        noun = (menu_label or entity or "").strip()
        if _leaks_code_ident(noun):
            noun = ""

    summary = str(op.get("summary") or "").strip().rstrip("()（）")
    if summary and not _leaks_code_ident(summary):
        return _collapse_dup_zh(summary)

    verb = str(op.get("verb") or "").strip()
    # verb 只来自词表映射，应是中文；再防一手
    if verb and not _leaks_code_ident(verb):
        out = _join_verb_noun(verb, noun) if noun else verb
        if out and not _leaks_code_ident(out):
            return _collapse_dup_zh(out)

    # 不再用 raw method 名拼文案
    return ""


def _msg(
    *,
    seq: int,
    frm: str,
    to: str,
    direction: str,
    text: str,
    phase: str,
    text_source: str,
) -> dict[str, Any]:
    return {
        "seq": seq,
        "from": frm,
        "to": to,
        "dir": direction,  # request | response | self
        "text": text,
        "phase": phase,
        "text_source": text_source,
    }


def _ensure_request_parens_display(text: str, *, is_request: bool) -> str:
    t = str(text or "").strip()
    if not is_request:
        return t.rstrip("()（）").strip()
    if t.endswith("()") or t.endswith("（）"):
        return t
    return f"{t}()"


def _build_login_phase(
    *,
    seq0: int,
    actor: str,
    auth_ops: list[dict[str, str]],
    vue_btns: list[str],
) -> list[dict[str, Any]]:
    """登录阶段：文案尽量来自 Auth Controller / 登录页按钮，避免固定示例句。"""
    msgs: list[dict[str, Any]] = []
    seq = seq0
    phase = "login"

    enter = next((b for b in vue_btns if "登录" in b or "登陆" in b), "")
    if enter:
        user_act = enter
        src = "vue"
    else:
        user_act = f"{actor}登录"
        src = "schema_label"
    seq += 1
    msgs.append(_msg(seq=seq, frm="actor", to="page", direction="request", text=user_act, phase=phase, text_source=src))

    verify = ""
    verify_src = "schema_label"
    for op in auth_ops:
        t = _op_text(op, entity="", menu_label="登录")
        if t:
            verify = t
            verify_src = "controller" if op.get("summary") or op.get("method") else "schema_label"
            break
    if not verify:
        verify = "验证账号密码"
        verify_src = "schema_label"
    verify = _collapse_dup_zh(verify)
    seq += 1
    msgs.append(_msg(seq=seq, frm="page", to="controller", direction="request", text=verify, phase=phase, text_source=verify_src))

    seq += 1
    msgs.append(_msg(seq=seq, frm="controller", to="db", direction="request", text=f"查询{actor}账号", phase=phase, text_source="schema_label"))
    seq += 1
    msgs.append(_msg(seq=seq, frm="db", to="controller", direction="response", text=f"返回{actor}资料", phase=phase, text_source="schema_label"))
    seq += 1
    msgs.append(_msg(seq=seq, frm="controller", to="page", direction="response", text="进入系统首页", phase=phase, text_source="schema_label"))
    seq += 1
    msgs.append(_msg(seq=seq, frm="page", to="actor", direction="response", text="登录成功", phase=phase, text_source="schema_label"))
    return msgs


def _classify_ops(ops: list[dict[str, str]]) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    reads: list[dict[str, str]] = []
    writes: list[dict[str, str]] = []
    for op in ops:
        verb = (op.get("verb") or "").lower()
        meth = (op.get("method") or "").lower()
        summary = (op.get("summary") or "")
        is_write = any(
            x in verb or x in meth or x in summary
            for x in ("保存", "新增", "更新", "删除", "提交", "审核", "驳回", "确认", "发货", "save", "create", "add", "update", "delete", "submit", "approve")
        )
        is_read = any(
            x in verb or x in meth or x in summary
            for x in ("查询", "分页", "详情", "list", "page", "get", "detail", "find")
        )
        if is_write:
            writes.append(op)
        elif is_read:
            reads.append(op)
        else:
            reads.append(op)
    return reads, writes


def _pick_vue_btn(
    vue_btns: list[str],
    *,
    menu_label: str,
    entity: str,
    kind: str,
    prefer_substrings: tuple[str, ...],
    extra_short: frozenset[str] | set[str] | None = None,
) -> str:
    for b in vue_btns:
        if not _btn_fits_feature(
            b,
            menu_label=menu_label,
            entity=entity,
            kind=kind,
            extra_short=extra_short,
        ):
            continue
        if any(x in b for x in prefer_substrings if x):
            return b
    return ""


def _build_business_phase(
    *,
    seq0: int,
    actor: str,
    menu_label: str,
    entity: str,
    ops: list[dict[str, str]],
    vue_btns: list[str],
    kind: str,
    schema: dict[str, Any] | None = None,
    side: str = "user",
) -> list[dict[str, Any]]:
    msgs: list[dict[str, Any]] = []
    seq = seq0
    phase = "biz"
    reads, writes = _classify_ops(ops)
    demo = _schema_demo_actions(schema)
    extra_short = {v for v in demo.values() if v}
    stem_early = entity or menu_label
    # 只保留与本菜单/实体对齐的按钮；无关复合文案自然被拒
    vue_btns = [
        b
        for b in (vue_btns or [])
        if _btn_fits_feature(
            b,
            menu_label=menu_label,
            entity=entity,
            kind=kind,
            extra_short=extra_short,
        )
    ]
    kind_fb = _kind_write_fallbacks(
        kind,
        stem=stem_early,
        menu_label=menu_label,
        side=side,
        vue_btns=vue_btns,
    )

    open_btn = _pick_vue_btn(
        vue_btns,
        menu_label=menu_label,
        entity=entity,
        kind=kind,
        prefer_substrings=(menu_label,) if menu_label else (),
        extra_short=extra_short,
    )
    if not open_btn and menu_label:
        open_btn = next((b for b in vue_btns if menu_label in b), "")
    open_text = open_btn or (
        f"进入{menu_label}" if menu_label else f"进入{entity or '功能页'}"
    )
    open_src = "vue" if open_btn else "schema_label"
    seq += 1
    msgs.append(_msg(seq=seq, frm="actor", to="page", direction="request", text=open_text, phase=phase, text_source=open_src))

    read_op = None
    page_ctrl = ""
    for op in reads:
        t = _op_text(op, entity=entity, menu_label=menu_label)
        if t:
            read_op = op
            page_ctrl = t
            break
    if page_ctrl:
        pc_src = "controller"
    else:
        page_ctrl = f"查询{menu_label or entity}" if (menu_label or entity) else "查询"
        pc_src = "schema_label"
    seq += 1
    msgs.append(_msg(seq=seq, frm="page", to="controller", direction="request", text=page_ctrl, phase=phase, text_source=pc_src))

    stem = entity or menu_label
    db_q = f"查询{stem}" if stem else "查询数据"
    seq += 1
    msgs.append(_msg(seq=seq, frm="controller", to="db", direction="request", text=db_q, phase=phase, text_source="schema_label"))
    seq += 1
    msgs.append(
        _msg(
            seq=seq,
            frm="db",
            to="controller",
            direction="response",
            text=f"返回{stem}列表" if stem else "返回查询结果",
            phase=phase,
            text_source="schema_label",
        )
    )
    seq += 1
    msgs.append(
        _msg(
            seq=seq,
            frm="controller",
            to="page",
            direction="response",
            text=f"返回{stem}列表" if stem else "返回查询结果",
            phase=phase,
            text_source="schema_label",
        )
    )

    # 写路径（有写操作或非纯浏览 kind；收藏夹有导出/复制清单时也画分享写路径）
    need_write = bool(writes) or kind not in BROWSE_SEQUENCE_KINDS
    if kind == "favorites" and any(
        x in vue_btns for x in ("导出清单", "复制清单")
    ):
        need_write = True
    if kind == "my_orders" and any(
        any(k in b for k in ("收货", "支付")) for b in vue_btns
    ):
        need_write = True
    if need_write:
        # 自调用优先用本功能菜单/实体措辞，不用跨页按钮
        prefer_select = ("选择", "核对", "填写", "编辑", "新增")
        if kind == "cart":
            prefer_select = ("核对", "改数量", "选择商品", "填写", "编辑")
        elif kind == "my_orders":
            prefer_select = ("选择已发货", "选择订单", "选择", "核对")
        elif "review" in kind:
            prefer_select = ("填写评价", "选择", "填写", "编辑")
        pick = _pick_vue_btn(
            vue_btns,
            menu_label=menu_label,
            entity=entity,
            kind=kind,
            prefer_substrings=prefer_select,
        )
        if pick and not (
            (entity and entity in pick)
            or (menu_label and menu_label in pick)
            or pick in ("新增", "编辑", "填写", "核对商品与数量", "去结算", "确认收货")
            or any(x in pick for x in ("核对", "结算", "评价", "支付", "收货", "留言", "预约"))
        ):
            # 「选择xxx」若不含本实体名，改用 kind 兜底
            pick = ""
        if pick and _is_container_template_phrase(
            pick, stem=stem, menu_label=menu_label
        ):
            pick = ""
        self1 = pick or kind_fb["select"]
        seq += 1
        msgs.append(
            _msg(
                seq=seq,
                frm="page",
                to="page",
                direction="self",
                text=self1,
                phase=phase,
                text_source="vue" if pick else "schema_label",
            )
        )

        prefer_submit = ("保存", "提交", "确认", "预约", "下单", "发布", "结算", "支付")
        if kind == "ticket_pending":
            prefer_submit = tuple(
                x
                for x in (demo.get("batch_hire"), "通过", "保存", "提交", "确认")
                if x
            )
        elif kind == "favorites":
            prefer_submit = ("导出清单", "复制清单", "取消收藏", "保存", "提交")
        elif kind == "my_tickets":
            prefer_submit = tuple(
                x for x in (demo.get("renew"), "提交", "确认", "保存") if x
            )
        elif kind == "ticket_records":
            prefer_submit = tuple(
                x for x in (demo.get("fine_waive"), "保存", "提交", "确认") if x
            )
        elif kind == "cart":
            prefer_submit = ("去结算", "结算", "下单", "提交", "确认")
        elif "review" in kind:
            prefer_submit = ("提交评价", "发表评价", "保存", "提交", "确认")
        elif kind == "my_orders" or (
            "order" in kind and "review" not in kind and kind != "orders" and side != "admin"
        ):
            prefer_submit = ("确认收货", "收货", "支付", "确认支付", "保存", "提交", "确认")
        elif kind in ("orders",) or (
            "order" in kind and "review" not in kind
        ):
            prefer_submit = ("发货", "配送", "保存", "提交", "确认")
        submit_btn = _pick_vue_btn(
            vue_btns,
            menu_label=menu_label,
            entity=entity,
            kind=kind,
            prefer_substrings=prefer_submit,
            extra_short=extra_short,
        )
        # 必须是短操作词/域演示动作，或文案里带本菜单/实体；否则退回 schema 措辞
        allowed_short = set(_SHORT_ACTION_BTNS) | extra_short | {
            "去结算",
            "结算",
            "确认支付",
            "确认收货",
            "提交评价",
            "发表评价",
            "核对商品与数量",
            "发货",
        }
        if submit_btn and submit_btn not in allowed_short and not (
            (entity and entity in submit_btn) or (menu_label and menu_label in submit_btn)
        ):
            submit_btn = ""
        if submit_btn and _is_container_template_phrase(
            submit_btn, stem=stem, menu_label=menu_label
        ):
            submit_btn = ""
        # 待办审单：schema 开了批量动作且页面有该按钮时优先画（文案跟 labels）
        batch_lab = str(demo.get("batch_hire") or "").strip()
        if kind == "ticket_pending" and batch_lab and batch_lab in vue_btns:
            submit_btn = batch_lab
        # 通用「保存/提交/确认」让位给 kind 相位（如确认收货/去结算），避免盖住业务动词
        _generic_submit = frozenset({"保存", "提交", "确认", "确定"})
        phase_confirm = str(kind_fb.get("confirm") or "").strip()
        if (
            submit_btn in _generic_submit
            and phase_confirm
            and phase_confirm not in _generic_submit
        ):
            submit_btn = ""
        # 页面上有更贴相位的按钮时仍用按钮
        if not submit_btn and phase_confirm:
            hit = next(
                (
                    b
                    for b in vue_btns
                    if phase_confirm in b or b in phase_confirm
                ),
                "",
            )
            if hit:
                submit_btn = hit
        self2 = submit_btn or phase_confirm or kind_fb["confirm"]
        seq += 1
        msgs.append(
            _msg(
                seq=seq,
                frm="page",
                to="page",
                direction="self",
                text=self2,
                phase=phase,
                text_source="vue" if submit_btn else "schema_label",
            )
        )

        write_op = None
        submit = ""
        for op in writes:
            t = _op_text(op, entity=entity, menu_label=menu_label)
            if t and not _is_container_template_phrase(
                t, stem=stem, menu_label=menu_label
            ):
                write_op = op
                submit = t
                break
        if submit:
            sub_src = "controller"
        else:
            submit = kind_fb["submit"]
            sub_src = "schema_label"
        seq += 1
        msgs.append(_msg(seq=seq, frm="page", to="controller", direction="request", text=submit, phase=phase, text_source=sub_src))

        save_t = kind_fb["save"]
        seq += 1
        msgs.append(_msg(seq=seq, frm="controller", to="db", direction="request", text=save_t, phase=phase, text_source="schema_label"))
        db_ok = f"{stem}已更新" if stem else "写入成功"
        seq += 1
        msgs.append(_msg(seq=seq, frm="db", to="controller", direction="response", text=db_ok, phase=phase, text_source="schema_label"))
        ok = kind_fb["ok"]
        seq += 1
        msgs.append(_msg(seq=seq, frm="controller", to="page", direction="response", text=ok, phase=phase, text_source="schema_label"))
        seq += 1
        msgs.append(_msg(seq=seq, frm="page", to="actor", direction="response", text=ok, phase=phase, text_source="schema_label"))
    else:
        seq += 1
        msgs.append(
            _msg(
                seq=seq,
                frm="page",
                to="actor",
                direction="response",
                text=f"展示{stem}" if stem else "展示结果",
                phase=phase,
                text_source="schema_label",
            )
        )
    return msgs


def build_diagram_messages(
    case: dict[str, Any],
    schema: dict[str, Any],
    workspace: Path | None,
) -> tuple[list[dict[str, Any]], list[str]]:
    """返回 (messages, phases)。"""
    kind = str(case.get("kind") or "")
    side = str(case.get("side") or "user")
    menu_label = str(case.get("label") or "").strip()
    actor = _short_role(str(case.get("actor") or _role_label(schema, side)), side=side)
    entity = _feature_entity(schema, kind=kind, menu_label=menu_label)

    controllers = _scan_controllers(workspace) if workspace else []
    vue_btns = (
        _scan_vue_buttons(
            workspace,
            menu_label,
            menu_key=str(case.get("menu_key") or ""),
            kind=kind,
            entity=entity,
            schema=schema,
        )
        if workspace
        else []
    )

    auth_ctrl = _pick_controller(controllers, kind="auth_login", menu_key="auth", menu_label="登录", entity=actor)
    auth_ops = list(auth_ctrl["ops"]) if auth_ctrl else []

    biz_ctrl = _pick_controller(
        controllers,
        kind=kind,
        menu_key=str(case.get("menu_key") or ""),
        menu_label=menu_label,
        entity=entity,
    )
    biz_ops = list(biz_ctrl["ops"]) if biz_ctrl else []

    msgs: list[dict[str, Any]] = []
    phases: list[str] = []
    if kind == "auth_login":
        phases.append("login")
        msgs.extend(_build_login_phase(seq0=0, actor=actor, auth_ops=auth_ops or biz_ops, vue_btns=vue_btns))
    elif kind == "auth_register":
        phases.append("biz")
        # 注册：用业务相位，菜单名来自候选
        msgs.extend(
            _build_business_phase(
                seq0=0,
                actor=actor,
                menu_label=menu_label or "注册",
                entity=actor,
                ops=biz_ops or auth_ops,
                vue_btns=vue_btns,
                kind=kind,
                schema=schema,
                side=side,
            )
        )
    else:
        phases.append("login")
        phases.append("biz")
        login_msgs = _build_login_phase(seq0=0, actor=actor, auth_ops=auth_ops, vue_btns=vue_btns)
        msgs.extend(login_msgs)
        msgs.extend(
            _build_business_phase(
                seq0=len(login_msgs),
                actor=actor,
                menu_label=menu_label,
                entity=entity,
                ops=biz_ops,
                vue_btns=vue_btns,
                kind=kind,
                schema=schema,
                side=side,
            )
        )
    # 重排序号，并折叠叠词（防「登录登录」）
    for i, m in enumerate(msgs, 1):
        m["seq"] = i
        m["text"] = _collapse_dup_zh(str(m.get("text") or ""))
    return msgs, phases


def build_sequence_diagram(
    case: dict[str, Any],
    schema: dict[str, Any],
    workspace: Path | None,
    *,
    index: int,
) -> dict[str, Any]:
    side = str(case.get("side") or "user")
    actor = _short_role(str(case.get("actor") or _role_label(schema, side)), side=side)
    name = str(case.get("name") or case.get("label") or "功能").strip()
    messages, phases = build_diagram_messages(case, schema, workspace)
    return {
        "id": candidate_id(case),
        "index": index,
        "figure_title": f"{name}序列图",
        "kind": str(case.get("kind") or ""),
        "menu_key": str(case.get("menu_key") or ""),
        "side": side,
        "actor_label": actor,
        "participants": [
            {"id": "actor", "label": actor, "stick": True},
            {"id": "page", "label": "页面", "stick": False},
            {"id": "controller", "label": "控制器", "stick": False},
            {"id": "db", "label": "数据库", "stick": False},
        ],
        "messages": messages,
        "phases": phases,
    }


def sequence_model(
    schema: dict[str, Any],
    workspace: Path | None = None,
    *,
    proposal_text: str = "",
    selection: list[str] | None = None,
    title_fallback: str = "管理系统",
) -> dict[str, Any]:
    from app.bake.schema.testcases import _app_title

    candidates = list_sequence_candidates(schema, proposal_text=proposal_text)
    if selection is None:
        selected = default_sequence_selection(candidates)
    else:
        selected = _validate_selection(selection, candidates)

    by_id = {c["id"]: c for c in candidates}
    # 恢复完整 case 字段供 build（candidates 已含 name/label/actor/kind）
    diagrams: list[dict[str, Any]] = []
    for i, sid in enumerate(selected):
        c = by_id[sid]
        diagrams.append(build_sequence_diagram(c, schema, workspace, index=i))

    title = _app_title(schema, title_fallback)
    from app.bake.schema.sequence_workflow import attach_workflow_to_diagrams

    model = {
        "title": title,
        "figure_title": "系统序列图",
        "candidates": candidates,
        "selected": selected,
        "diagrams": diagrams,
        "source_note": (
            "功能取自交付 menus；角色与步骤文案取自 bake 包 Controller/页面/交付中文名；"
            "示例图仅定画法；禁止模板套话。"
        ),
        "rules_zh": [
            "恰好 3 张核心功能序列图，可从交付功能勾选",
            "四槽位：交付角色、页面、控制器、数据库；角色旁火柴人",
            "生命线虚线；激活条按操作阶段断开且长短随活跃跨度变化",
            "往数据库方向实线且文字带 ()；往角色方向虚线且文字不带 ()",
            "相邻对象阶梯传递并带序号",
        ],
    }
    return attach_workflow_to_diagrams(model)


def load_sequence_model(
    workspace: Path,
    *,
    proposal_text: str = "",
    selection: list[str] | None = None,
    title_fallback: str = "管理系统",
) -> dict[str, Any] | None:
    schema = _read_json(workspace / "domain.schema.json")
    if not schema:
        return None
    spec = _read_json(workspace / "spec.json") or {}
    fb = str(spec.get("title") or "").strip() or title_fallback
    sel = selection
    if sel is None:
        try:
            from app.bake.overrides import resolve_override_selection

            sel = resolve_override_selection(workspace, "sequence")
        except Exception:  # noqa: BLE001
            sel = None
    try:
        model = sequence_model(
            schema,
            workspace,
            proposal_text=proposal_text,
            selection=sel,
            title_fallback=fb,
        )
    except ValueError:
        # 失效勾选 → 回落默认，不挡打开
        model = sequence_model(
            schema,
            workspace,
            proposal_text=proposal_text,
            selection=None,
            title_fallback=fb,
        )
    try:
        from app.bake.overrides import (
            apply_sequence_label_overrides,
            override_labels_map,
        )

        model = apply_sequence_label_overrides(
            model, override_labels_map(workspace, "sequence")
        )
    except Exception:  # noqa: BLE001
        pass
    from app.bake.schema.sequence_workflow import attach_workflow_to_diagrams

    return attach_workflow_to_diagrams(model)


# —— SVG ——
_PAD_X = 36.0
_PAD_Y = 28.0
_BOX_W = 88.0
_BOX_H = 36.0
_COL_GAP = 150.0
_ROW_H = 36.0
_ACT_W = 10.0
_FONT = "Microsoft YaHei, SimSun, serif"
_STROKE = 1.2


def _stick_figure(cx: float, top: float) -> str:
    """火柴人：头 + 躯干 + 四肢，画在角色框左侧。"""
    head_r = 5.0
    hy = top + 8
    return (
        f'<circle cx="{_f(cx)}" cy="{_f(hy)}" r="{_f(head_r)}" fill="none" stroke="#000" stroke-width="1.2"/>'
        f'<line x1="{_f(cx)}" y1="{_f(hy + head_r)}" x2="{_f(cx)}" y2="{_f(hy + 22)}" stroke="#000" stroke-width="1.2"/>'
        f'<line x1="{_f(cx - 8)}" y1="{_f(hy + 14)}" x2="{_f(cx + 8)}" y2="{_f(hy + 14)}" stroke="#000" stroke-width="1.2"/>'
        f'<line x1="{_f(cx)}" y1="{_f(hy + 22)}" x2="{_f(cx - 7)}" y2="{_f(hy + 32)}" stroke="#000" stroke-width="1.2"/>'
        f'<line x1="{_f(cx)}" y1="{_f(hy + 22)}" x2="{_f(cx + 7)}" y2="{_f(hy + 32)}" stroke="#000" stroke-width="1.2"/>'
    )


def _marker_defs() -> str:
    # 对齐示例图：空心箭头（>），非实心三角
    return (
        "<defs>"
        '<marker id="seq-solid" viewBox="0 0 12 10" refX="11" refY="5" '
        'markerWidth="9" markerHeight="8" orient="auto" markerUnits="strokeWidth">'
        '<path d="M0,0 L10,5 L0,10" fill="none" stroke="#000" stroke-width="1.2"/>'
        "</marker>"
        '<marker id="seq-dash" viewBox="0 0 12 10" refX="11" refY="5" '
        'markerWidth="9" markerHeight="8" orient="auto" markerUnits="strokeWidth">'
        '<path d="M0,0 L10,5 L0,10" fill="none" stroke="#000" stroke-width="1.2"/>'
        "</marker>"
        "</defs>"
    )


def _activation_spans(
    messages: list[dict[str, Any]],
    participant: str,
) -> list[tuple[str, int, int]]:
    """按 phase 收集该参与者涉及消息的起止下标（含），用于变长激活条。"""
    spans: list[tuple[str, int, int]] = []
    cur_phase = ""
    start = -1
    end = -1
    for i, m in enumerate(messages):
        involved = m.get("from") == participant or m.get("to") == participant
        phase = str(m.get("phase") or "")
        if involved:
            if start < 0 or phase != cur_phase:
                if start >= 0:
                    spans.append((cur_phase, start, end))
                cur_phase = phase
                start = i
                end = i
            else:
                end = i
        else:
            if start >= 0 and phase != cur_phase:
                spans.append((cur_phase, start, end))
                start = -1
                end = -1
                cur_phase = ""
    if start >= 0:
        spans.append((cur_phase, start, end))
    return spans


def render_sequence_svg(diagram: dict[str, Any] | None) -> str:
    if not diagram or not isinstance(diagram.get("messages"), list):
        body = '<text x="24" y="40" font-family="Microsoft YaHei, SimSun, serif">暂无序列图</text>'
        return (
            '<?xml version="1.0" encoding="UTF-8"?>'
            f'<svg xmlns="http://www.w3.org/2000/svg" width="320" height="80" viewBox="0 0 320 80">{body}</svg>'
        )

    participants = diagram.get("participants") or []
    labels = []
    for p in _PARTICIPANTS:
        found = next((x for x in participants if isinstance(x, dict) and x.get("id") == p), None)
        if p == "actor":
            labels.append(str((found or {}).get("label") or diagram.get("actor_label") or "角色"))
        else:
            labels.append(_PARTICIPANT_LABELS[p])

    messages = [m for m in diagram["messages"] if isinstance(m, dict)]
    n = max(1, len(messages))
    stick_w = 40.0
    origin_x = _PAD_X + stick_w
    xs = [origin_x + i * (_BOX_W + _COL_GAP) + _BOX_W / 2 for i in range(4)]
    box_x = [origin_x + i * (_BOX_W + _COL_GAP) for i in range(4)]

    title = str(diagram.get("figure_title") or "序列图")
    title_h = 22.0
    y_box = _PAD_Y + title_h
    life_top = y_box + _BOX_H
    msg_y0 = life_top + 28.0
    life_bot = msg_y0 + n * _ROW_H + 24.0

    total_w = origin_x + 4 * _BOX_W + 3 * _COL_GAP + _PAD_X + 40
    total_h = life_bot + _PAD_Y

    parts: list[str] = [_marker_defs()]
    parts.append(
        f'<text x="{_f(total_w / 2)}" y="{_f(_PAD_Y + 14)}" text-anchor="middle" '
        f'font-size="14" font-family="{_FONT}" font-weight="700" fill="#000">{_esc(title)}</text>'
    )
    # 火柴人（角色左侧）
    parts.append(_stick_figure(origin_x - 22, y_box - 2))

    for i, lab in enumerate(labels):
        parts.append(
            f'<rect x="{_f(box_x[i])}" y="{_f(y_box)}" width="{_f(_BOX_W)}" height="{_f(_BOX_H)}" '
            f'fill="#fff" stroke="#000" stroke-width="{_STROKE}"/>'
            f'<text x="{_f(xs[i])}" y="{_f(y_box + _BOX_H / 2 + 5)}" text-anchor="middle" '
            f'font-size="13" font-family="{_FONT}" fill="#000">{_esc(lab)}</text>'
        )
        parts.append(
            f'<line x1="{_f(xs[i])}" y1="{_f(life_top)}" x2="{_f(xs[i])}" y2="{_f(life_bot)}" '
            f'stroke="#000" stroke-width="1" stroke-dasharray="4 3"/>'
        )

    idx = {p: i for i, p in enumerate(_PARTICIPANTS)}

    # 变长激活条
    for pi, pid in enumerate(_PARTICIPANTS):
        for _phase, a, b in _activation_spans(messages, pid):
            y1 = msg_y0 + a * _ROW_H - 8
            y2 = msg_y0 + b * _ROW_H + 8
            h = max(14.0, y2 - y1)
            parts.append(
                f'<rect x="{_f(xs[pi] - _ACT_W / 2)}" y="{_f(y1)}" width="{_f(_ACT_W)}" height="{_f(h)}" '
                f'fill="#fff" stroke="#000" stroke-width="1"/>'
            )

    for m in messages:
        seq = int(m.get("seq") or 0)
        frm = str(m.get("from") or "")
        to = str(m.get("to") or "")
        direction = str(m.get("dir") or "request")
        is_req = direction in ("request", "self")
        raw_text = str(m.get("text") or "")
        body = _ensure_request_parens_display(raw_text, is_request=is_req)
        label = f"{seq}、{body}"
        yi = max(0, seq - 1)
        y = msg_y0 + yi * _ROW_H
        fi = idx.get(frm, 0)
        ti = idx.get(to, 0)

        if direction == "self" or frm == to:
            # 自调用：直角回路（右→下→左回激活条），空心箭头；对齐示例非贝塞尔
            x0 = xs[fi] + _ACT_W / 2
            x1 = x0 + 28.0
            y0 = y - 8.0
            y1 = y + 10.0
            parts.append(
                f'<polyline points="{_f(x0)},{_f(y0)} {_f(x1)},{_f(y0)} {_f(x1)},{_f(y1)} {_f(x0)},{_f(y1)}" '
                f'fill="none" stroke="#000" stroke-width="1.2" marker-end="url(#seq-solid)"/>'
            )
            parts.append(
                f'<text x="{_f(x1 + 6)}" y="{_f((y0 + y1) / 2 + 4)}" text-anchor="start" '
                f'font-size="11" font-family="{_FONT}" fill="#000">{_esc(label)}</text>'
            )
            continue

        x1, x2 = xs[fi], xs[ti]
        # 箭头避开激活条边缘
        if x2 > x1:
            x1a, x2a = x1 + _ACT_W / 2 + 1, x2 - _ACT_W / 2 - 1
        else:
            x1a, x2a = x1 - _ACT_W / 2 - 1, x2 + _ACT_W / 2 + 1
        if is_req:
            parts.append(
                f'<line x1="{_f(x1a)}" y1="{_f(y)}" x2="{_f(x2a)}" y2="{_f(y)}" '
                f'stroke="#000" stroke-width="1.2" marker-end="url(#seq-solid)"/>'
            )
        else:
            parts.append(
                f'<line x1="{_f(x1a)}" y1="{_f(y)}" x2="{_f(x2a)}" y2="{_f(y)}" '
                f'stroke="#000" stroke-width="1.2" stroke-dasharray="5 3" marker-end="url(#seq-dash)"/>'
            )
        mid = (x1a + x2a) / 2
        parts.append(
            f'<text x="{_f(mid)}" y="{_f(y - 5)}" text-anchor="middle" '
            f'font-size="11" font-family="{_FONT}" fill="#000">{_esc(label)}</text>'
        )

    inner = "".join(parts)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{int(total_w)}" height="{int(total_h)}" '
        f'viewBox="0 0 {_f(total_w)} {_f(total_h)}" data-figure="sequence">'
        f"{inner}</svg>"
    )
