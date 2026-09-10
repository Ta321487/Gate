"""论文用例图（与模块图/测例同级必有交付物）。

优先解析开题「{身份}功能模块划分为…」作为一级用例骨架，再用交付 menus/岗位 pack
挂二级并做溯源；无材料枚举时回落 menus 归桶。

画法硬约束按客户样式卡死（见 usecase_style.py，默认可切换）：
1. 椭圆同尺寸；一/二级圆心各自共一条竖线
2. 一级↔二级虚线箭头 + <<include>>（条件扩展可用 <<extend>>，UML 方向）
3. 描述若写序号，须与图中一级用例一一对应（几个一级就几个序号；现客户一级固定 5）
4. 描述为段落形式
5. 全部二级用例动词开头
禁止菜单外 key；管理端/岗位不得挂「进行支付」。
一级名禁止「综合功能/综合业务」空壳：合并时保留主业务名。
明年换校：在 USECASE_STYLE_PROFILES 增 profile，或在 spec.usecase_style 指定。
"""

from __future__ import annotations

import json
import re
import uuid
from pathlib import Path
from typing import Any

from app.bake.schema.modules import (
    _SKIP_MENU_KEYS,
    _biz_id_for_item,
    _menu_label,
    _role_slot_label,
    looks_latin,
    parse_identity_modules,
)
from app.bake.schema.usecase_style import (
    resolve_usecase_style,
    style_public_view,
)
from app.bake.staff_posts import PACK_ADMIN_MENUS, PACK_WORK_PAGES

# 几何/数量默认取自当前客户样式（断言与布局以此为准）
_STYLE = resolve_usecase_style()
_LEVEL1_COUNT = int(_STYLE["level1_count"])
_UC_W = float(_STYLE["ellipse_w"])
_UC_H = float(_STYLE["ellipse_h"])

# 员工端页面 id → 可落到 admin 菜单的候选 key（不发明菜单外功能）
_WORK_PAGE_MENU_KEYS: dict[str, tuple[str, ...]] = {
    "tickets": ("ticket_pending", "ticket_records"),
    "orders": ("orders",),
    "slots": ("reservations", "slots"),
}

_WORK_PAGE_LABEL: dict[str, str] = {
    "tickets": "办理工单",
    "orders": "处理订单",
    "slots": "办理预约",
}

_VERB_PREFIX_RE = re.compile(
    r"^(查看|进行|编辑|提交|管理|选择|确认|登录|注册|充值|反馈|审核|"
    r"办理|预约|取消|支付|导出|催办|评价|驳回|通过|填写|检索|打开|结束|"
    r"切换|连接|打卡|签到|开门|补缴|申请|下单|收藏|浏览|进入|使用|参加|参与|收发|查阅|联系|发表|加入)"
)

_EXTEND_KEY_HINTS = frozenset(
    {
        "coupons",
        "order_reviews",
    }
)
_EXTEND_LABEL_RE = re.compile(
    r"充值|补缴|取消|催办|导出|驳回|退款|优惠券|催收|投诉"
)

# 开题一级模块归并亲和（凑满 5 个时同组优先合并）
_MAT_AFFINITY: tuple[tuple[str, ...], ...] = (
    ("登录", "注册"),
    ("个人中心", "个人信息", "店铺信息", "修改密码", "头像"),
    ("商品", "农产品", "浏览", "库存"),
    ("购物车", "支付", "订单", "售后", "退货"),
    ("留言", "客服", "评价", "沟通"),
    ("活动", "公告", "促销", "资讯"),
    ("用户管理", "商家管理", "分类", "数据分析", "审核"),
)

# menus 回落合并优先级：越靠后越先被并入
_MERGE_TAIL_ORDER = (
    "extra",
    "admin",
    "e_sign",
    "stock_io",
    "timebank",
    "doclib",
    "dm",
    "guestbook",
    "content",
    "favorite",
    "cart",
    "seat_select",
    "vote",
    "survey",
    "exam",
    "archive",
    "ticket",
    "order",
    "slot",
    "messages",
    "profile",
)

_BIZ_L1_TEMPLATE: dict[str, str] = {
    "auth": "登录注册",
    "profile": "管理个人中心",
    "messages": "查看通知",
    "slot": "进行预约",
    "order": "管理订单",
    "ticket": "办理申请",
    "archive": "浏览业务资料",
    "cart": "管理购物车",
    "favorite": "管理收藏",
    "exam": "参加考试",
    "survey": "填写问卷",
    "vote": "参与投票",
    "content": "查看公告",
    "guestbook": "提交留言",
    "doclib": "查阅文档",
    "timebank": "管理时间账户",
    "seat_select": "选择座位",
    "stock_io": "办理出入库",
    "e_sign": "办理电子签",
    "dm": "收发私信",
    "admin": "管理系统配置",
    "extra": "查看其它业务",
    "user": "管理个人中心",
}


def _esc(s: str) -> str:
    return (
        (s or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _new_id(prefix: str = "id") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}"


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def ensure_verb_prefix(label: str, *, default_verb: str = "进行") -> str:
    lab = re.sub(r"\s+", "", str(label or "").strip())
    if not lab:
        return f"{default_verb}操作"
    for suf in ("功能模块", "模块"):
        if lab.endswith(suf) and len(lab) > len(suf):
            lab = lab[: -len(suf)]
    if _VERB_PREFIX_RE.match(lab):
        # 「评价管理」「售后管理」等：名义以管理收尾，统一成「管理评价」
        if default_verb == "管理" and lab.endswith("管理") and not lab.startswith("管理"):
            stem = lab[:-2]
            if stem:
                return f"管理{stem}"
        return _dedupe_verb_noun_tail(lab, default_verb)
    if default_verb and lab.startswith(default_verb):
        return _dedupe_verb_noun_tail(lab, default_verb)
    # 「农产品浏览」+查看 →「浏览农产品」；「确认」+「农产品管理」→「确认农产品」
    if lab.endswith("浏览") and len(lab) > 2 and default_verb in ("查看", "浏览", "进行"):
        return f"浏览{lab[:-2]}"
    if default_verb == "确认" and lab.endswith("管理") and len(lab) > 2:
        return f"确认{lab[:-2]}"
    noun_suffixes = ("管理", "列表", "中心", "记录", "信息", "浏览")
    if default_verb and any(lab.endswith(suf) and len(lab) > len(suf) for suf in noun_suffixes):
        for suf in noun_suffixes:
            if lab.endswith(suf) and len(lab) > len(suf):
                stem = lab[: -len(suf)]
                if suf == "管理" and default_verb == "管理":
                    return f"{default_verb}{stem}"
                if suf == "浏览" and default_verb in ("查看", "浏览"):
                    return f"浏览{stem}"
                break
    return _dedupe_verb_noun_tail(f"{default_verb}{lab}", default_verb)


def _dedupe_verb_noun_tail(lab: str, verb: str = "") -> str:
    """去掉「管理xxx管理」「查看xxx查看」叠字。"""
    s = lab or ""
    for v in (verb, "管理", "查看", "提交", "办理", "确认"):
        if not v or len(s) <= len(v) * 2:
            continue
        if s.startswith(v) and s.endswith(v):
            mid = s[len(v) : -len(v)]
            if mid:
                return f"{v}{mid}"
    return s


def _is_extend(key: str, label: str, *, side: str = "user") -> bool:
    """可选扩展：用户侧的支付/评价等；管理侧的驳回/导出等。禁止给管理端挂「支付」。"""
    k = str(key or "").strip()
    lab = str(label or "")
    if side != "user":
        # 管理/岗位：仅次要办理分支
        if k.endswith("_reviews") or "export" in k:
            return True
        if re.search(r"驳回|导出|催办|评价", lab):
            return True
        return False
    if k in _EXTEND_KEY_HINTS:
        return True
    if k.endswith("_reviews") or "cancel" in k or "refund" in k:
        return True
    if _EXTEND_LABEL_RE.search(lab):
        return True
    return False


def _bucket_primary_biz(items: list[dict[str, Any]], fallback: str = "extra") -> str:
    counts: dict[str, int] = {}
    for it in items:
        b = str(it.get("biz") or "extra").split(":")[0]
        if b.startswith("leaf"):
            b = "extra"
        counts[b] = counts.get(b, 0) + 1
    if not counts:
        return fallback.split(":")[0] if fallback else "extra"
    return max(counts.items(), key=lambda x: (x[1], -_biz_merge_rank(x[0])))[0]


def _should_attach_pay_extend(*, side: str, items: list[dict[str, Any]]) -> bool:
    """仅用户门户、且本桶主业务是下单/预约类时，才挂「进行支付」扩展。"""
    if side != "user":
        return False
    primary = _bucket_primary_biz(items)
    if primary not in ("order", "cart", "slot", "seat_select"):
        return False
    keys = [str(x.get("key") or "") for x in items]
    labs = [str(x.get("label") or "") for x in items]
    return any(
        k in ("my_orders", "orders", "cart", "my_reservations", "reservations", "slots")
        or k.startswith("order")
        for k in keys
    ) or any(any(w in x for w in ("订单", "预约", "预订", "购物车")) for x in labs)

def _actor_label(schema: dict[str, Any], side: str) -> str:
    roles = schema.get("roles") if isinstance(schema.get("roles"), dict) else {}
    if side == "user":
        return _role_slot_label(roles, "user", "用户")
    if side == "admin":
        return _role_slot_label(roles, "admin", "管理员")
    if side == "subadmin":
        return _role_slot_label(roles, "subadmin", "经办员")
    if side.startswith("staff:"):
        pid = side.split(":", 1)[1]
        posts = roles.get("staff_posts") if isinstance(roles.get("staff_posts"), list) else []
        for p in posts:
            if isinstance(p, dict) and str(p.get("id") or "") == pid:
                lab = str(p.get("label") or pid).strip()
                return lab or pid
        return pid
    return side


def _normalize_actor_id(actor: str) -> str:
    raw = str(actor or "user").strip()
    low = raw.lower()
    if low in ("user", "admin", "subadmin"):
        return low
    if low.startswith("staff:"):
        return f"staff:{raw.split(':', 1)[1].strip()}"
    return raw


def _find_staff_post(schema: dict[str, Any], actor_id: str) -> dict[str, Any] | None:
    if not actor_id.startswith("staff:"):
        return None
    pid = actor_id.split(":", 1)[1]
    roles = schema.get("roles") if isinstance(schema.get("roles"), dict) else {}
    posts = roles.get("staff_posts") if isinstance(roles.get("staff_posts"), list) else []
    for p in posts:
        if isinstance(p, dict) and str(p.get("id") or "") == pid:
            return p
    return None


def _pack_allowed_keys(packs: list[Any]) -> set[str]:
    allowed: set[str] = set()
    for pk in packs or []:
        if not isinstance(pk, str) or not pk.strip():
            continue
        p = pk.strip()
        if p in PACK_ADMIN_MENUS:
            allowed |= set(PACK_ADMIN_MENUS[p])
        if p in PACK_WORK_PAGES:
            for page in PACK_WORK_PAGES[p]:
                for mk in _WORK_PAGE_MENU_KEYS.get(page, (page,)):
                    allowed.add(mk)
                allowed.add(page)
    return allowed


def _admin_menu_by_key(schema: dict[str, Any]) -> dict[str, dict[str, Any]]:
    menus = schema.get("menus") if isinstance(schema.get("menus"), dict) else {}
    out: dict[str, dict[str, Any]] = {}
    for raw in menus.get("admin") or []:
        if not isinstance(raw, dict):
            continue
        key = str(raw.get("key") or "").strip()
        if key:
            out[key] = raw
    return out


def _staff_menu_items(schema: dict[str, Any], post: dict[str, Any]) -> list[dict[str, Any]]:
    """按岗位 packs 裁剪 admin 菜单 / 映射员工页，不发明菜单外 key。"""
    packs = list(post.get("packs") or [])
    allowed = _pack_allowed_keys(packs)
    admin_map = _admin_menu_by_key(schema)
    out: list[dict[str, Any]] = []
    seen: set[str] = set()

    # 1) 办理岗：按 pack 允许的 admin 菜单（含 dashboard）
    for key in sorted(allowed):
        if key in _SKIP_MENU_KEYS and key != "dashboard":
            continue
        raw = admin_map.get(key)
        if not raw:
            continue
        if key in seen:
            continue
        seen.add(key)
        lab = _menu_label(raw)
        biz = _biz_id_for_item(key, lab)
        if biz == "user":
            biz = "profile"
        out.append({"key": key, "label": lab, "biz": biz})

    # 2) 作业岗页面：admin 无对应 key 时，若页面能映射到已有 admin 菜单则补上
    for pk in packs:
        if not isinstance(pk, str) or pk not in PACK_WORK_PAGES:
            continue
        for page in PACK_WORK_PAGES[pk]:
            mapped = _WORK_PAGE_MENU_KEYS.get(page, ())
            hit = False
            for mk in mapped:
                if mk in seen:
                    hit = True
                    break
                raw = admin_map.get(mk)
                if raw:
                    seen.add(mk)
                    lab = _menu_label(raw)
                    biz = _biz_id_for_item(mk, lab)
                    out.append({"key": mk, "label": lab, "biz": biz})
                    hit = True
                    break
            if not hit and page not in seen:
                # 仅当 schema.staffPackPages 声明了该页，用页标签；menu_keys 仍用 mapped 中存在于 admin 的，否则空+用 page 仅当 admin 有同名
                if page in admin_map:
                    seen.add(page)
                    lab = _menu_label(admin_map[page])
                    out.append({"key": page, "label": lab, "biz": _biz_id_for_item(page, lab)})
                elif any(m in admin_map for m in mapped):
                    continue
                else:
                    # 员工页存在于交付 staffPackPages，标签固定；key 取 mapped 首选且必须之后 invariants 放行 page
                    # 为可验证：只在 schema 的 staffPackPages 含该 page 时使用 page 作 key，并加入 allowed 集
                    lab = _WORK_PAGE_LABEL.get(page, page)
                    seen.add(page)
                    out.append({"key": page, "label": lab, "biz": "extra"})
    return out


def _subadmin_menu_items(schema: dict[str, Any]) -> list[dict[str, Any]]:
    """无 staff_posts 时的兼容：子管用 roles.subadmin.staffPostId 或整表 admin 精简。"""
    roles = schema.get("roles") if isinstance(schema.get("roles"), dict) else {}
    sub = roles.get("subadmin") if isinstance(roles.get("subadmin"), dict) else {}
    spid = str(sub.get("staffPostId") or "").strip()
    posts = roles.get("staff_posts") if isinstance(roles.get("staff_posts"), list) else []
    for p in posts:
        if isinstance(p, dict) and str(p.get("id") or "") == spid:
            return _staff_menu_items(schema, p)
    # 回落：ticket_ops ∪ order_ops ∪ slot_ops 与 admin 交集
    fake = {"id": "subadmin", "kind": "clerk", "packs": ["ticket_ops", "order_ops", "slot_ops"]}
    items = _staff_menu_items(schema, fake)
    if items:
        return items
    return _side_menu_items(schema, "admin")


def _side_menu_items(schema: dict[str, Any], side: str) -> list[dict[str, Any]]:
    menus = schema.get("menus") if isinstance(schema.get("menus"), dict) else {}
    raw_list = menus.get(side) or []
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw in raw_list:
        if not isinstance(raw, dict):
            continue
        key = str(raw.get("key") or "").strip()
        if not key or key in _SKIP_MENU_KEYS or key in seen:
            continue
        seen.add(key)
        lab = _menu_label(raw)
        biz = _biz_id_for_item(key, lab)
        # 个人中心与消息拆开，便于凑满一级用例
        if biz == "user":
            biz = "messages" if key == "messages" else "profile"
        out.append({"key": key, "label": lab, "biz": biz})
    return out


def _side_has_portal(schema: dict[str, Any], side: str) -> bool:
    menus = schema.get("menus") if isinstance(schema.get("menus"), dict) else {}
    raw_list = menus.get(side) or []
    return any(isinstance(x, dict) and str(x.get("key") or "").strip() for x in raw_list)


def _resolve_actor_items(
    schema: dict[str, Any], actor_id: str
) -> tuple[str, str, list[dict[str, Any]]]:
    """返回 (portal_side_for_verbs, actor_label, menu_items)。portal_side: user|admin。"""
    aid = _normalize_actor_id(actor_id)
    if aid == "user":
        return "user", _actor_label(schema, "user"), _side_menu_items(schema, "user")
    if aid == "admin":
        return "admin", _actor_label(schema, "admin"), _side_menu_items(schema, "admin")
    if aid == "subadmin":
        return "admin", _actor_label(schema, "subadmin"), _subadmin_menu_items(schema)
    post = _find_staff_post(schema, aid)
    if post:
        lab = str(post.get("label") or aid).strip() or aid
        return "admin", lab, _staff_menu_items(schema, post)
    raise ValueError(f"usecase: 未知角色 {actor_id}")


def _l1_label_for_biz(biz: str, items: list[dict[str, Any]], side: str) -> str:
    bizs = {
        str(it.get("biz") or "extra").split(":")[0]
        for it in items
        if not str(it.get("biz") or "").startswith("auth")
    }
    bizs = {b for b in bizs if b and not b.startswith("leaf")}
    # 跨业务合并桶：跟主业务命名，禁止「综合功能」空壳
    if len(bizs) > 1:
        root = _bucket_primary_biz(items, next(iter(bizs)))
    else:
        root = (biz or "extra").split(":")[0]
        if root.startswith("leaf"):
            root = _bucket_primary_biz(items, "extra")

    if root in _BIZ_L1_TEMPLATE:
        base = _BIZ_L1_TEMPLATE[root]
        if root == "auth":
            return base
        if len(items) == 1:
            leaf = str(items[0].get("label") or "").strip()
            if leaf and not looks_latin(leaf):
                if side == "admin":
                    return ensure_verb_prefix(leaf, default_verb="管理")
                return ensure_verb_prefix(
                    leaf, default_verb="进行" if root in ("slot", "ticket") else "查看"
                )
        # 多叶同桶：用模板业务名（如管理订单），勿用首叶「留言」带飞
        return base if _VERB_PREFIX_RE.match(base) else ensure_verb_prefix(
            base, default_verb="管理" if side == "admin" else "查看"
        )
    if items:
        return ensure_verb_prefix(
            str(items[0].get("label") or "功能"),
            default_verb="管理" if side == "admin" else "查看",
        )
    return "查看其它功能" if side == "user" else "管理其它功能"


_AFFINITY_GROUPS: tuple[frozenset[str], ...] = (
    frozenset({"order", "cart", "favorite", "slot", "seat_select"}),
    frozenset({"content", "guestbook", "dm", "doclib"}),
    frozenset({"exam", "survey", "vote"}),
    frozenset({"ticket", "archive", "admin", "stock_io", "e_sign", "timebank"}),
    frozenset({"profile", "messages", "user"}),
)


def _biz_root(biz: str) -> str:
    r = str(biz or "extra").split(":")[0]
    return "extra" if r.startswith("leaf") else r


def _merge_affinity(a: str, b: str) -> int:
    """越小越优先合并；同族 0，同亲和组 1，其它 5。"""
    ra, rb = _biz_root(a), _biz_root(b)
    if ra == rb:
        return 0
    for g in _AFFINITY_GROUPS:
        if ra in g and rb in g:
            return 1
    return 5


def _bucket_items(items: list[dict[str, Any]]) -> list[tuple[str, list[dict[str, Any]]]]:
    """保持菜单出现顺序的业务桶。"""
    order: list[str] = []
    buckets: dict[str, list[dict[str, Any]]] = {}
    for it in items:
        biz = str(it.get("biz") or "extra")
        if biz not in buckets:
            buckets[biz] = []
            order.append(biz)
        buckets[biz].append(it)
    return [(b, buckets[b]) for b in order]


def _biz_merge_rank(biz: str) -> int:
    root = str(biz or "extra").split(":")[0]
    if root.startswith("leaf"):
        root = "extra"
    try:
        return _MERGE_TAIL_ORDER.index(root)
    except ValueError:
        return len(_MERGE_TAIL_ORDER)


def _merge_buckets(
    buckets: list[tuple[str, list[dict[str, Any]]]],
    *,
    target: int,
) -> list[tuple[str, list[dict[str, Any]]]]:
    cur = list(buckets)
    while len(cur) > target:
        idxs = [i for i, (biz, _) in enumerate(cur) if not str(biz).startswith("auth")]
        if not idxs:
            break

        victim_i = max(idxs, key=lambda i: (_biz_merge_rank(cur[i][0]), i))
        dest_candidates = [
            i for i in range(len(cur)) if i != victim_i and not str(cur[i][0]).startswith("auth")
        ]
        if not dest_candidates:
            break
        # 优先同亲和组，再比邻接距离
        dest_i = min(
            dest_candidates,
            key=lambda i: (
                _merge_affinity(cur[victim_i][0], cur[i][0]),
                abs(i - victim_i),
                i,
            ),
        )
        _vb, vitems = cur.pop(victim_i)
        if victim_i < dest_i:
            dest_i -= 1
        db, ditems = cur[dest_i]
        # 合并后桶名跟主业务，避免 guestbook 名带飞订单
        merged = ditems + vitems
        primary = _bucket_primary_biz(merged, db)
        cur[dest_i] = (primary, merged)
    return cur


_SPLIT_STAGE_VERBS_USER = ("查看", "选择", "确认", "提交", "浏览")
_SPLIT_STAGE_VERBS_ADMIN = ("查看", "管理", "审核", "编辑", "导出")


def _split_buckets(
    buckets: list[tuple[str, list[dict[str, Any]]]],
    *,
    target: int,
    side: str,
) -> list[tuple[str, list[dict[str, Any]]]]:
    cur = list(buckets)
    guard = 0
    verbs = _SPLIT_STAGE_VERBS_ADMIN if side == "admin" else _SPLIT_STAGE_VERBS_USER
    while len(cur) < target and guard < 60:
        guard += 1
        # 0) 用户端把认证拆成登录 / 注册两个一级
        auth_idxs = [i for i, (biz, _) in enumerate(cur) if biz == "auth"]
        if auth_idxs and side == "user":
            i = auth_idxs[0]
            cur[i] = (
                "auth:login",
                [{"key": "", "label": "登录", "biz": "auth", "_auth_part": "login"}],
            )
            cur.insert(
                i + 1,
                (
                    "auth:register",
                    [{"key": "", "label": "注册", "biz": "auth", "_auth_part": "register"}],
                ),
            )
            continue
        if auth_idxs and side == "admin" and len(cur) < target:
            i = auth_idxs[0]
            cur[i] = (
                "auth:login",
                [{"key": "", "label": "登录", "biz": "auth", "_auth_part": "login"}],
            )
            cur.insert(
                i + 1,
                (
                    "auth:enter",
                    [{"key": "", "label": "进入系统", "biz": "auth", "_auth_part": "enter"}],
                ),
            )
            continue

        # 1) 拆多叶桶
        multi = [
            (i, len(items))
            for i, (biz, items) in enumerate(cur)
            if not str(biz).startswith("auth") and len(items) > 1
        ]
        if multi:
            i, _ = max(multi, key=lambda x: x[1])
            biz, items = cur[i]
            leaf = items[-1]
            cur[i] = (biz, items[:-1])
            cur.insert(i + 1, (f"leaf:{leaf['key']}", [leaf]))
            continue

        # 2) 单叶按阶段动词拆（同源 menu key，不发明功能）
        stageable = [
            i
            for i, (biz, items) in enumerate(cur)
            if not str(biz).startswith("auth")
            and len(items) == 1
            and int(items[0].get("_stage") or 0) < len(verbs) - 1
        ]
        if not stageable:
            break
        i = stageable[0]
        biz, items = cur[i]
        it = dict(items[0])
        stage = int(it.get("_stage") or 0)
        left = {**it, "_split": "stage", "_stage": stage, "_verb": verbs[stage]}
        right = {
            **it,
            "_split": "stage",
            "_stage": stage + 1,
            "_verb": verbs[stage + 1],
        }
        cur[i] = (f"{biz}:s{stage}", [left])
        cur.insert(i + 1, (f"{biz}:s{stage+1}", [right]))
    return cur


def _normalize_five(
    buckets: list[tuple[str, list[dict[str, Any]]]],
    *,
    side: str,
) -> list[tuple[str, list[dict[str, Any]]]]:
    cur = list(buckets)
    if len(cur) > _LEVEL1_COUNT:
        cur = _merge_buckets(cur, target=_LEVEL1_COUNT)
    if len(cur) < _LEVEL1_COUNT:
        cur = _split_buckets(cur, target=_LEVEL1_COUNT, side=side)
    if len(cur) != _LEVEL1_COUNT:
        raise ValueError(
            f"usecase:{side}: 无法归一为 {_LEVEL1_COUNT} 个一级用例（当前 {len(cur)}）"
        )
    return cur


def _build_l2_for_bucket(
    biz: str,
    items: list[dict[str, Any]],
    *,
    side: str,
    l1_id: str,
) -> list[dict[str, Any]]:
    includes: list[dict[str, Any]] = []

    # 认证拆分后的一级：每个只要一个二级
    if items and items[0].get("_auth_part"):
        part = str(items[0].get("_auth_part") or "")
        label_map = {
            "login": "进行登录",
            "register": "进行注册",
            "enter": "进入管理系统",
        }
        includes.append(
            {
                "id": f"{l1_id}:{part or 'auth'}",
                "label": label_map.get(part, "进行登录"),
                "relation": "include",
                "menu_keys": [],
                "source": "auth",
            }
        )
        # 管理端进入系统时可挂 dashboard
        if part == "enter" and side == "admin":
            return includes
        if part == "login" and side == "admin":
            return includes
        if part in ("login", "register"):
            # 再挂一个同源固定子步，满足「每 L1 至少一个 L2」已满足；补第二步避免过瘦
            alt = "进行注册" if part == "login" else "进行登录"
            # 用户端登录一级只含登录，注册一级只含注册（不交叉发明）
            return includes
        return includes

    if biz == "auth" or (items and items[0].get("biz") == "auth" and not items[0].get("_auth_part")):
        if side == "user":
            includes.append(
                {
                    "id": f"{l1_id}:login",
                    "label": "进行登录",
                    "relation": "include",
                    "menu_keys": [],
                    "source": "auth",
                }
            )
            includes.append(
                {
                    "id": f"{l1_id}:register",
                    "label": "进行注册",
                    "relation": "include",
                    "menu_keys": [],
                    "source": "auth",
                }
            )
        else:
            includes.append(
                {
                    "id": f"{l1_id}:login",
                    "label": "进行登录",
                    "relation": "include",
                    "menu_keys": [],
                    "source": "auth",
                }
            )
        return includes

    # 拆分叶：用 _verb
    if len(items) == 1 and items[0].get("_split"):
        it = items[0]
        verb = str(it.get("_verb") or "查看")
        raw_lab = str(it.get("label") or "功能")
        lab = ensure_verb_prefix(raw_lab, default_verb=verb)
        rel = "extend" if _is_extend(str(it.get("key") or ""), str(it.get("label") or ""), side=side) else "include"
        includes.append(
            {
                "id": f"{l1_id}:0",
                "label": lab,
                "relation": rel,
                "menu_keys": [str(it["key"])] if it.get("key") else [],
                "source": f"menu:{side}",
            }
        )
        return includes

    if not items:
        raise ValueError(f"usecase: 空桶 {biz}")

    for idx, it in enumerate(items):
        key = str(it.get("key") or "")
        lab_raw = str(it.get("label") or key or "功能")
        default_verb = "管理" if side == "admin" else "查看"
        lab = ensure_verb_prefix(lab_raw, default_verb=default_verb)
        rel = "extend" if _is_extend(key, lab_raw, side=side) else "include"
        includes.append(
            {
                "id": f"{l1_id}:{idx}",
                "label": lab,
                "relation": rel,
                "menu_keys": [key] if key else [],
                "source": f"menu:{side}",
            }
        )

    # 仅用户端、下单/预约主桶：挂「进行支付」扩展（管理端/商家/馆员绝不挂支付）
    # 即使已有其它 extend（如评价），支付仍可并列挂上
    if _should_attach_pay_extend(side=side, items=items) and not any(
        x.get("label") == "进行支付" for x in includes
    ):
        keys = [str(x.get("key") or "") for x in items if x.get("key")]
        includes.append(
            {
                "id": f"{l1_id}:pay",
                "label": "进行支付",
                "relation": "extend",
                "menu_keys": keys[:1],
                "source": f"menu:{side}",
            }
        )

    if len(items) == 1 and len(includes) == 1 and includes[0]["relation"] == "include":
        it = items[0]
        key = str(it.get("key") or "")
        lab_raw = str(it.get("label") or "功能")
        includes.append(
            {
                "id": f"{l1_id}:confirm",
                "label": ensure_verb_prefix(lab_raw, default_verb="确认"),
                "relation": "include",
                "menu_keys": [key] if key else [],
                "source": f"menu:{side}",
            }
        )

    if not includes:
        raise ValueError(f"usecase: L1 {biz} 无二级用例")
    return includes


def _description_paragraph(actor: str, level1: list[dict[str, Any]]) -> str:
    """客户要求：段落形式；若写序号则与一级个数严格一致。"""
    parts: list[str] = []
    for i, uc in enumerate(level1, start=1):
        lab = str(uc.get("label") or "")
        kids = uc.get("includes") or []
        if kids:
            rel_bits = []
            for k in kids:
                if not isinstance(k, dict):
                    continue
                tag = "包含" if k.get("relation") == "include" else "扩展"
                rel_bits.append(f"{tag}「{k.get('label')}」")
            detail = "，".join(rel_bits)
            parts.append(f"（{i}）{actor}可通过「{lab}」完成相关操作，其中{detail}。")
        else:
            parts.append(f"（{i}）{actor}可通过「{lab}」完成相关操作。")
    # 段落：单行连贯，不用换行拆成列表
    return "".join(parts)


def _strip_module_word(name: str) -> str:
    lab = re.sub(r"\s+", "", str(name or "").strip())
    for suf in ("功能模块", "模块"):
        if lab.endswith(suf) and len(lab) > len(suf):
            lab = lab[: -len(suf)]
    return lab.strip("的之") or str(name or "").strip()


def _mat_affinity(a: str, b: str) -> int:
    sa, sb = _strip_module_word(a), _strip_module_word(b)
    if sa == sb:
        return 0
    for group in _MAT_AFFINITY:
        hit_a = any(t in sa for t in group)
        hit_b = any(t in sb for t in group)
        if hit_a and hit_b:
            return 1
    return 5


def _mat_label_priority(name: str) -> int:
    """越小越适合保留为一级圈名（合并时跟主业务，禁止改成综合*）。"""
    sa = _strip_module_word(name)
    # 登录类尽量不当整桶标题（除非只剩登录）
    if any(t in sa for t in ("登录", "注册")):
        return 90
    ranks: tuple[tuple[str, int], ...] = (
        ("订单", 0),
        ("购物车", 1),
        ("支付", 2),
        ("商品", 3),
        ("农产品", 3),
        ("预约", 4),
        ("售后", 5),
        ("退货", 5),
        ("评价", 6),
        ("活动", 7),
        ("公告", 7),
        ("促销", 7),
        ("客服", 8),
        ("留言", 9),
        ("用户管理", 10),
        ("商家管理", 10),
        ("分类", 11),
        ("数据分析", 12),
        ("个人中心", 20),
        ("个人信息", 20),
    )
    for token, rank in ranks:
        if token in sa:
            return rank
    return 40


def _mat_pick_keep_label(a: str, b: str) -> str:
    """合并后一级名：跟优先级更高的那块，绝不改成综合业务。"""
    pa, pb = _mat_label_priority(a), _mat_label_priority(b)
    if pb < pa:
        return _strip_module_word(b) or b
    if pa < pb:
        return _strip_module_word(a) or a
    # 同级：更短、更像业务核的优先
    sa, sb = _strip_module_word(a), _strip_module_word(b)
    if len(sb) < len(sa):
        return sb or sa
    return sa or sb


def _l1_label_from_material(name: str, *, side: str) -> str:
    raw = _strip_module_word(name)
    if not raw:
        return "查看其它功能" if side == "user" else "管理其它功能"
    if raw in ("登录注册", "登录", "注册") or ("登录" in raw and "注册" in raw):
        return "登录注册" if side == "user" else "登录系统"
    if raw in ("注册",) and side == "user":
        return "进行注册"
    # 历史兜底名若仍流入，按主业务语义拆掉（断言也会拦）
    if any(t in raw for t in ("综合业务", "综合功能")):
        return "管理订单" if side == "admin" else "查看订单"
    if any(t in raw for t in ("购物车",)):
        return "管理购物车"
    if any(t in raw for t in ("支付",)):
        return "进行支付"
    if any(t in raw for t in ("订单",)):
        return "管理订单" if side == "admin" else "查看订单"
    if any(t in raw for t in ("售后", "退货")):
        return "申请售后" if side == "user" else "管理售后"
    if any(t in raw for t in ("留言",)):
        return "提交留言" if side == "user" else "管理留言反馈"
    if any(t in raw for t in ("客服",)):
        return "联系客服" if side == "user" else "管理客服"
    if any(t in raw for t in ("评价",)):
        return "管理评价" if side == "admin" else ("查看评价" if side == "user" else "管理评价")
    if any(t in raw for t in ("活动", "公告", "促销")):
        return "管理活动" if side == "admin" else "查看活动"
    if any(t in raw for t in ("数据分析", "统计")):
        return "查看数据分析"
    if any(t in raw for t in ("分类",)):
        return "管理分类"
    if any(t in raw for t in ("用户管理", "商家管理")):
        return ensure_verb_prefix(raw, default_verb="管理")
    if any(t in raw for t in ("商品", "农产品")):
        return "管理农产品" if side == "admin" else "浏览商品"
    if any(t in raw for t in ("个人中心", "个人信息")):
        return "管理个人中心"
    if _VERB_PREFIX_RE.match(raw):
        return _dedupe_verb_noun_tail(raw)
    return ensure_verb_prefix(raw, default_verb="管理" if side == "admin" else "查看")


def _match_section_for_actor(
    sections: list[dict[str, Any]],
    *,
    actor_id: str,
    actor_lab: str,
) -> dict[str, Any] | None:
    if not sections:
        return None
    aid = _normalize_actor_id(actor_id)
    lab = (actor_lab or "").strip()

    def score(sec_lab: str) -> int:
        s = _strip_module_word(sec_lab)
        sc = 0
        if lab and (lab in s or s in lab):
            sc += 10
        if aid == "user" and any(t in s for t in ("用户", "买家", "读者", "学生", "住客", "顾客", "会员")):
            sc += 8
        if aid == "admin" and any(t in s for t in ("管理员", "平台", "总管", "馆长", "主管")):
            sc += 8
        if aid.startswith("staff:") or aid == "subadmin":
            if any(t in s for t in ("商家", "商户", "店家", "馆员", "前台", "店员", "骑手", "专员")):
                sc += 8
            if lab and any(t in s for t in (lab,)):
                sc += 6
        return sc

    ranked = sorted(sections, key=lambda sec: -score(str(sec.get("label") or "")))
    best = ranked[0]
    if score(str(best.get("label") or "")) <= 0:
        # 回落：user→首段非管理/商家；admin→含管理；staff→含商家等
        for sec in sections:
            s = str(sec.get("label") or "")
            if aid == "user" and not any(t in s for t in ("管理", "商家")):
                return sec
            if aid == "admin" and "管理" in s:
                return sec
            if (aid.startswith("staff:") or aid == "subadmin") and any(
                t in s for t in ("商家", "商户", lab)
            ):
                return sec
        return None
    return best


def _normalize_material_modules(
    modules: list[dict[str, Any]],
    *,
    side: str,
) -> list[dict[str, Any]]:
    """开题一级模块 → 恰好 5 个（保留开题名，合并时带上 details）。"""
    cur: list[dict[str, Any]] = []
    for m in modules:
        if not isinstance(m, dict):
            continue
        name = _strip_module_word(str(m.get("label") or ""))
        if not name:
            continue
        details = [str(d).strip() for d in (m.get("details") or []) if str(d).strip()]
        cur.append({"label": name, "details": details, "merged_from": [name]})

    guard = 0
    while len(cur) > _LEVEL1_COUNT and guard < 40:
        guard += 1
        # 合并亲和最高的一对（非登录优先被并）
        best = None
        for i in range(len(cur)):
            for j in range(i + 1, len(cur)):
                aff = _mat_affinity(cur[i]["label"], cur[j]["label"])
                # 登录类尽量不吞别人
                pen = 0
                if any(t in cur[i]["label"] for t in ("登录", "注册")) or any(
                    t in cur[j]["label"] for t in ("登录", "注册")
                ):
                    pen = 3
                key = (aff + pen, -len(cur[i]["details"]) - len(cur[j]["details"]), i, j)
                if best is None or key < best[0]:
                    best = (key, aff, i, j)
        if not best:
            break
        _key, _aff, i, j = best
        a, b = cur[i], cur[j]
        keep_label = _mat_pick_keep_label(a["label"], b["label"])
        sa = _strip_module_word(a["label"])
        sb = _strip_module_word(b["label"])
        if keep_label in (sa, a["label"]):
            keep, drop = a, b
        elif keep_label in (sb, b["label"]):
            keep, drop = b, a
        elif _mat_label_priority(a["label"]) <= _mat_label_priority(b["label"]):
            keep, drop = a, b
        else:
            keep, drop = b, a
        drop_lab = str(drop["label"] or "").strip()
        details = list(keep.get("details") or [])
        if drop_lab and drop_lab not in details and drop_lab != keep_label:
            details.append(drop_lab)
        details.extend(list(drop.get("details") or []))
        keep = {
            "label": keep_label,
            "details": details,
            "merged_from": list(keep.get("merged_from") or [keep["label"]])
            + list(drop.get("merged_from") or [drop["label"]]),
        }
        cur = [x for k, x in enumerate(cur) if k not in (i, j)]
        cur.insert(min(i, j), keep)

    while len(cur) < _LEVEL1_COUNT and guard < 80:
        guard += 1
        # 拆 details 最多的
        multi = [(i, len(m.get("details") or [])) for i, m in enumerate(cur)]
        multi = [x for x in multi if x[1] > 0]
        if not multi:
            # 拆 merged_from
            multi2 = [
                (i, len(m.get("merged_from") or []))
                for i, m in enumerate(cur)
                if len(m.get("merged_from") or []) > 1
            ]
            if not multi2:
                break
            i, _ = max(multi2, key=lambda x: x[1])
            m = cur[i]
            names = list(m["merged_from"])
            left, right = names[0], names[-1]
            cur[i] = {"label": left, "details": [], "merged_from": [left]}
            cur.insert(i + 1, {"label": right, "details": [], "merged_from": [right]})
            continue
        i, _ = max(multi, key=lambda x: x[1])
        m = cur[i]
        details = list(m["details"])
        leaf = details.pop()
        cur[i] = {**m, "details": details}
        cur.insert(
            i + 1,
            {"label": _strip_module_word(leaf)[:12] or leaf, "details": [], "merged_from": [leaf]},
        )

    if len(cur) != _LEVEL1_COUNT:
        raise ValueError(f"usecase:materials: 无法归一为 {_LEVEL1_COUNT} 个一级（{len(cur)}）")
    return cur


def _menu_keys_matching(text: str, menu_items: list[dict[str, Any]]) -> list[str]:
    blob = text or ""
    hits: list[str] = []
    for it in menu_items:
        lab = str(it.get("label") or "")
        key = str(it.get("key") or "")
        if not key:
            continue
        stem = lab.replace("管理", "").replace("我的", "").replace("浏览", "")
        if stem and stem in blob:
            hits.append(key)
        elif lab and lab in blob:
            hits.append(key)
        elif key in ("cart",) and "购物车" in blob:
            hits.append(key)
        elif key in ("orders", "my_orders") and "订单" in blob:
            hits.append(key)
        elif key in ("guestbook",) and "留言" in blob:
            hits.append(key)
        elif key in ("content",) and any(t in blob for t in ("活动", "公告", "促销")):
            hits.append(key)
        elif key in ("archive",) and any(t in blob for t in ("商品", "农产品", "档案")):
            hits.append(key)
        elif key in ("profile",) and "个人" in blob:
            hits.append(key)
        elif key in ("addresses",) and "地址" in blob:
            hits.append(key)
        elif key in ("category",) and "分类" in blob:
            hits.append(key)
        elif key in ("users",) and "用户" in blob:
            hits.append(key)
    # 去重保序
    out: list[str] = []
    seen: set[str] = set()
    for k in hits:
        if k not in seen:
            seen.add(k)
            out.append(k)
    return out


def _l2_from_material_module(
    mod: dict[str, Any],
    *,
    side: str,
    l1_id: str,
    menu_items: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    name = str(mod.get("label") or "")
    details = [str(d).strip() for d in (mod.get("details") or []) if str(d).strip()]
    merged = [str(x) for x in (mod.get("merged_from") or []) if str(x).strip()]
    kids: list[dict[str, Any]] = []

    # 认证
    if any(t in name for t in ("登录", "注册")):
        if side == "user":
            if "注册" in name and "登录" in name:
                kids.append(
                    {"id": f"{l1_id}:login", "label": "进行登录", "relation": "include", "menu_keys": [], "source": "auth"}
                )
                kids.append(
                    {"id": f"{l1_id}:register", "label": "进行注册", "relation": "include", "menu_keys": [], "source": "auth"}
                )
            elif "注册" in name:
                kids.append(
                    {"id": f"{l1_id}:register", "label": "进行注册", "relation": "include", "menu_keys": [], "source": "auth"}
                )
            else:
                kids.append(
                    {"id": f"{l1_id}:login", "label": "进行登录", "relation": "include", "menu_keys": [], "source": "auth"}
                )
        else:
            kids.append(
                {"id": f"{l1_id}:login", "label": "进行登录", "relation": "include", "menu_keys": [], "source": "auth"}
            )
            # dashboard 在 _side_menu_items 会被 skip，这里按 admin 菜单原文判断
            has_dash = any(str(it.get("key") or "") == "dashboard" for it in menu_items)
            if not has_dash and side == "admin":
                has_dash = True  # 管理端登录后默认进工作台（交付必有 dashboard）
            if has_dash:
                kids.append(
                    {
                        "id": f"{l1_id}:dash",
                        "label": "查看工作台",
                        "relation": "include",
                        "menu_keys": ["dashboard"],
                        "source": "menu:admin",
                    }
                )
        return kids

    # details / 被合并模块名 → L2
    seeds: list[str] = []
    for d in details:
        # 括号细节可能很长，截短
        piece = d.split("（")[0].split("(")[0].strip()
        if piece and piece not in seeds:
            seeds.append(piece)
    for m in merged:
        if m != name and m not in seeds:
            seeds.append(_strip_module_word(m))

    if not seeds:
        seeds = [_strip_module_word(name)]

    for idx, seed in enumerate(seeds[:6]):
        seed = _strip_module_word(seed)
        if not seed:
            continue
        verb = "管理" if side == "admin" else "查看"
        if any(t in seed for t in ("支付",)):
            continue
        if any(t in seed for t in ("新增", "编辑", "上下架", "发货", "审核", "删除")):
            lab = ensure_verb_prefix(seed, default_verb="进行" if side == "user" else "管理")
        elif any(t in seed for t in ("浏览", "搜索")):
            stem = seed.replace("浏览", "").replace("搜索", "").strip() or seed
            lab = f"浏览{stem}" if not stem.startswith("浏览") else stem
            lab = ensure_verb_prefix(lab, default_verb="浏览")
        elif seed.endswith("管理") and not seed.startswith("管理"):
            lab = ensure_verb_prefix(seed, default_verb="管理")
        elif any(t in seed for t in ("收藏",)):
            lab = "管理收藏" if side == "admin" else "进行收藏"
        elif seed in ("评价",) or (seed.endswith("评价") and len(seed) <= 4):
            lab = "发表评价" if side == "user" else "管理评价"
        elif "加入购物车" in seed:
            lab = "加入购物车"
            if not _VERB_PREFIX_RE.match(lab):
                lab = "进行加购"
        else:
            lab = ensure_verb_prefix(seed, default_verb=verb)
        if lab.startswith("确认") and "浏览" in lab:
            lab = f"查看{lab[2:].replace('浏览', '')}" or "查看详情"
        if not _VERB_PREFIX_RE.match(lab):
            lab = ensure_verb_prefix(lab, default_verb=verb)
        keys = _menu_keys_matching(seed + name, menu_items)
        rel = "include"
        if side == "user" and any(t in seed for t in ("评价", "取消", "售后申请")):
            rel = "extend"
        kids.append(
            {
                "id": f"{l1_id}:{idx}",
                "label": lab,
                "relation": rel,
                "menu_keys": keys,
                "source": "materials" if not keys else f"menu:{side}",
            }
        )

    # 用户：仅当一级模块名本身属购物/支付/订单时挂支付扩展（细节里「加入购物车」不算）
    blob_mods = name + " ".join(merged)
    if side == "user" and any(t in blob_mods for t in ("购物车", "支付", "订单")):
        if not any(k.get("label") == "进行支付" for k in kids):
            pay_keys = _menu_keys_matching(blob_mods, menu_items) or [
                str(it["key"])
                for it in menu_items
                if it.get("key") in ("cart", "my_orders", "orders")
            ][:1]
            kids.append(
                {
                    "id": f"{l1_id}:pay",
                    "label": "进行支付",
                    "relation": "extend",
                    "menu_keys": pay_keys[:1],
                    "source": f"menu:{side}",
                }
            )

    if not kids:
        keys = _menu_keys_matching(name, menu_items)
        kids.append(
            {
                "id": f"{l1_id}:0",
                "label": ensure_verb_prefix(name, default_verb="管理" if side == "admin" else "查看"),
                "relation": "include",
                "menu_keys": keys,
                "source": "materials",
            }
        )
    return kids


def _level1_from_materials(
    section: dict[str, Any],
    *,
    side: str,
    actor_id: str,
    menu_items: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    mods = _normalize_material_modules(list(section.get("modules") or []), side=side)
    level1: list[dict[str, Any]] = []
    for i, mod in enumerate(mods):
        l1_id = f"{actor_id}:uc{i+1}".replace(":", "_")
        label = _l1_label_from_material(str(mod.get("label") or ""), side=side)
        # 支付不宜单独占一级：若归一后仍叫进行支付，并入订单语义
        if label == "进行支付":
            label = "管理购物车" if side == "user" else "管理订单"
        kids = _l2_from_material_module(mod, side=side, l1_id=l1_id, menu_items=menu_items)
        keys: list[str] = []
        for k in kids:
            keys.extend(k.get("menu_keys") or [])
        # 去重
        seen: set[str] = set()
        menu_keys = []
        for k in keys:
            if k and k not in seen:
                seen.add(k)
                menu_keys.append(k)
        level1.append(
            {
                "id": l1_id,
                "label": label,
                "menu_keys": menu_keys,
                "source": "materials",
                "includes": kids,
            }
        )
    return level1


def list_usecase_actors(schema: dict[str, Any]) -> list[dict[str, str]]:
    """门户 user/admin + staff_posts（馆员/前台/骑手等）；subadmin 仅在无岗位表时兼容列出。"""
    out: list[dict[str, str]] = []
    for side in ("user", "admin"):
        if _side_has_portal(schema, side):
            out.append({"id": side, "label": _actor_label(schema, side)})
    roles = schema.get("roles") if isinstance(schema.get("roles"), dict) else {}
    posts = roles.get("staff_posts") if isinstance(roles.get("staff_posts"), list) else []
    seen_ids = {a["id"] for a in out}
    for post in posts:
        if not isinstance(post, dict):
            continue
        pid = str(post.get("id") or "").strip()
        if not pid:
            continue
        aid = f"staff:{pid}"
        if aid in seen_ids:
            continue
        lab = str(post.get("label") or pid).strip() or pid
        out.append({"id": aid, "label": lab})
        seen_ids.add(aid)
    # 无岗位表时才单独挂 subadmin，避免与 clerk 重复
    if not posts:
        sub = roles.get("subadmin") if isinstance(roles.get("subadmin"), dict) else None
        if sub and str(sub.get("label") or "").strip() and "subadmin" not in seen_ids:
            out.append({"id": "subadmin", "label": _actor_label(schema, "subadmin")})
    return out


def usecase_model(
    schema: dict[str, Any],
    *,
    actor: str = "user",
    proposal_text: str = "",
    title_fallback: str = "管理系统",
    style: dict[str, Any] | None = None,
    style_id: str | None = None,
    spec: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """生成单角色用例图模型；失败抛 ValueError。

    画法由 usecase_style 决定（现客户硬约束为默认）；换校时改 profile / spec.usecase_style。
    """
    st = style or resolve_usecase_style(style_id, spec=spec)
    aid = _normalize_actor_id(actor)
    if not isinstance(schema, dict) or not schema:
        raise ValueError("usecase: 缺少 schema")

    known = {a["id"] for a in list_usecase_actors(schema)}
    if aid not in known:
        raise ValueError(f"usecase: 角色 {actor} 不在交付角色集中")

    side_verb, actor_lab, items = _resolve_actor_items(schema, aid)
    source_note = "由交付菜单/岗位 pack 归纳；身份名来自 roles / staff_posts"
    level1: list[dict[str, Any]] | None = None

    # 材料优先：开题「身份功能模块划分为」→ 一级用例
    prop = proposal_text or ""
    if prop.strip():
        try:
            sections = parse_identity_modules(prop, schema=schema)
            sec = _match_section_for_actor(sections, actor_id=aid, actor_lab=actor_lab)
            if sec and (sec.get("modules") or []):
                level1 = _level1_from_materials(
                    sec, side=side_verb, actor_id=aid, menu_items=items
                )
                source_note = (
                    f"一级对齐开题「{sec.get('label')}」功能模块枚举；"
                    "二级来自开题细节/合并项，菜单 key 仅作溯源"
                )
        except ValueError:
            level1 = None

    if level1 is not None:
        labels = schema.get("labels") if isinstance(schema.get("labels"), dict) else {}
        title = str(labels.get("appName") or "").strip() or title_fallback
        model = {
            "title": title,
            "actor": {"id": aid, "label": actor_lab},
            "level1": level1,
            "description": _description_paragraph(actor_lab, level1),
            "source_note": source_note,
            "style": style_public_view(st),
            "capabilities": {"include": True, "extend": True, "staruml_mdj": True},
        }
        assert_usecase_invariants(model, schema=schema, actor=aid, style=st)
        return model

    buckets: list[tuple[str, list[dict[str, Any]]]] = []
    if side_verb == "user":
        buckets.append(("auth", [{"key": "", "label": "登录注册", "biz": "auth"}]))
    else:
        buckets.append(("auth", [{"key": "", "label": "登录", "biz": "auth"}]))

    if items:
        buckets.extend(_bucket_items(items))
    else:
        raise ValueError(f"usecase:{aid}: 跳过门户后无业务菜单，无法归纳用例")

    buckets = _normalize_five(buckets, side=side_verb)

    level1 = []
    for i, (biz, b_items) in enumerate(buckets):
        l1_id = f"{aid}:uc{i+1}".replace(":", "_")
        auth_part = ""
        if b_items and b_items[0].get("_auth_part"):
            auth_part = str(b_items[0].get("_auth_part") or "")
        if biz == "auth" or str(biz).startswith("auth:"):
            if auth_part == "login":
                label = "进行登录"
            elif auth_part == "register":
                label = "进行注册"
            elif auth_part == "enter":
                label = "进入管理系统"
            else:
                label = "登录注册" if side_verb == "user" else "登录系统"
        else:
            root = biz.split(":")[0]
            if biz.startswith("leaf:"):
                root = "extra"
            label = _l1_label_for_biz(root, b_items, side_verb)
            if not _VERB_PREFIX_RE.match(label) and label not in ("登录注册", "登录系统"):
                label = ensure_verb_prefix(label)
        menu_keys = [str(x["key"]) for x in b_items if x.get("key")]
        if biz.startswith("leaf:"):
            biz_for_l2 = "extra"
        elif str(biz).startswith("auth"):
            biz_for_l2 = "auth"
        else:
            biz_for_l2 = biz.split(":")[0]
        kids = _build_l2_for_bucket(biz_for_l2, b_items, side=side_verb, l1_id=l1_id)
        if auth_part == "enter" and side_verb == "admin":
            menus = schema.get("menus") if isinstance(schema.get("menus"), dict) else {}
            has_dash = any(
                isinstance(x, dict) and str(x.get("key") or "") == "dashboard"
                for x in (menus.get("admin") or [])
            )
            # 岗位允许 dashboard 时才挂
            if has_dash and (
                aid == "admin"
                or "dashboard" in menu_keys
                or any(k.get("key") == "dashboard" for k in items)
            ):
                kids.append(
                    {
                        "id": f"{l1_id}:dash",
                        "label": "查看工作台",
                        "relation": "include",
                        "menu_keys": ["dashboard"],
                        "source": "menu:admin",
                    }
                )
        if (biz == "auth" or str(biz).startswith("auth")) and side_verb == "admin" and not auth_part:
            kids = [
                {
                    "id": f"{l1_id}:login",
                    "label": "进行登录",
                    "relation": "include",
                    "menu_keys": [],
                    "source": "auth",
                }
            ]
            menus = schema.get("menus") if isinstance(schema.get("menus"), dict) else {}
            has_dash = any(
                isinstance(x, dict) and str(x.get("key") or "") == "dashboard"
                for x in (menus.get("admin") or [])
            )
            staff_allows_dash = aid == "admin" or any(
                str(it.get("key") or "") == "dashboard" for it in items
            )
            if has_dash and staff_allows_dash:
                kids.append(
                    {
                        "id": f"{l1_id}:dash",
                        "label": "查看工作台",
                        "relation": "include",
                        "menu_keys": ["dashboard"],
                        "source": "menu:admin",
                    }
                )
            else:
                kids.append(
                    {
                        "id": f"{l1_id}:enter",
                        "label": "进入管理系统",
                        "relation": "include",
                        "menu_keys": [],
                        "source": "auth",
                    }
                )
        if not kids:
            raise ValueError(f"usecase: {label} 缺少二级用例")
        level1.append(
            {
                "id": l1_id,
                "label": label,
                "menu_keys": menu_keys,
                "source": "auth" if str(biz).startswith("auth") else f"menu:{aid}",
                "includes": kids,
            }
        )

    labels = schema.get("labels") if isinstance(schema.get("labels"), dict) else {}
    title = str(labels.get("appName") or "").strip() or title_fallback
    desc = _description_paragraph(actor_lab, level1)
    model = {
        "title": title,
        "actor": {"id": aid, "label": actor_lab},
        "level1": level1,
        "description": desc,
        "source_note": source_note,
        "style": style_public_view(st),
        "capabilities": {"include": True, "extend": True, "staruml_mdj": True},
    }
    assert_usecase_invariants(model, schema=schema, actor=aid, style=st)
    return model


# ----- 几何 / SVG / MDJ -----
# 椭圆宽高取客户样式；布局函数内再读一次以防测试 monkeypatch style
# _UC_W / _UC_H 已在模块顶由 resolve_usecase_style 初始化
_PAD_X = 36.0
_PAD_Y = 28.0
_ACTOR_X = 70.0
_L1_CX = 280.0
_L2_CX = 520.0
_ROW_GAP = 72.0


def layout_usecase(model: dict[str, Any]) -> dict[str, Any]:
    """计算布局；椭圆同尺寸，L1/L2 各自竖线对齐。"""
    level1 = list(model.get("level1") or [])
    # 按 L2 行数分配纵向：每个 L1 占 max(1, n_l2) 行高
    rows: list[dict[str, Any]] = []
    y = _PAD_Y + _UC_H / 2
    l1_nodes: list[dict[str, Any]] = []
    l2_nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []

    for uc in level1:
        kids = [k for k in (uc.get("includes") or []) if isinstance(k, dict)]
        n = max(1, len(kids))
        block_h = (n - 1) * _ROW_GAP
        l1_y = y + block_h / 2
        l1_nodes.append(
            {
                "id": uc["id"],
                "label": uc["label"],
                "cx": _L1_CX,
                "cy": l1_y,
                "w": _UC_W,
                "h": _UC_H,
                "kind": "l1",
            }
        )
        if not kids:
            y += _ROW_GAP
            continue
        for j, kid in enumerate(kids):
            ky = y + j * _ROW_GAP
            l2_nodes.append(
                {
                    "id": kid["id"],
                    "label": kid["label"],
                    "cx": _L2_CX,
                    "cy": ky,
                    "w": _UC_W,
                    "h": _UC_H,
                    "kind": "l2",
                    "relation": kid.get("relation") or "include",
                    "parent": uc["id"],
                }
            )
            rel = kid.get("relation") or "include"
            if rel == "extend":
                # 扩展用例 → 基用例
                edges.append(
                    {
                        "kind": "extend",
                        "from": kid["id"],
                        "to": uc["id"],
                        "label": "<<extend>>",
                    }
                )
            else:
                edges.append(
                    {
                        "kind": "include",
                        "from": uc["id"],
                        "to": kid["id"],
                        "label": "<<include>>",
                    }
                )
        y += block_h + _ROW_GAP

    actor_cy = (_PAD_Y + _UC_H / 2 + y - _ROW_GAP) / 2 if level1 else 100.0
    if l1_nodes:
        actor_cy = sum(n["cy"] for n in l1_nodes) / len(l1_nodes)

    assoc = [{"kind": "assoc", "from": "actor", "to": n["id"]} for n in l1_nodes]
    height = max(y + _PAD_Y, actor_cy + 80, 320)
    width = _L2_CX + _UC_W / 2 + _PAD_X + 40

    return {
        "width": width,
        "height": height,
        "uc_w": _UC_W,
        "uc_h": _UC_H,
        "actor": {
            "id": "actor",
            "label": (model.get("actor") or {}).get("label") or "用户",
            "cx": _ACTOR_X,
            "cy": actor_cy,
        },
        "l1": l1_nodes,
        "l2": l2_nodes,
        "edges": edges,
        "assoc": assoc,
    }


def _ellipse_svg(cx: float, cy: float, w: float, h: float, label: str) -> str:
    rx, ry = w / 2, h / 2
    return (
        f'<ellipse cx="{cx:.1f}" cy="{cy:.1f}" rx="{rx:.1f}" ry="{ry:.1f}" '
        f'fill="#fff" stroke="#000" stroke-width="1.2"/>'
        f'<text x="{cx:.1f}" y="{cy:.1f}" text-anchor="middle" dominant-baseline="middle" '
        f'font-size="12" font-family="Microsoft YaHei,SimSun,sans-serif">{_esc(label)}</text>'
    )


def _actor_svg(cx: float, cy: float, label: str) -> str:
    # 简易火柴人
    head_r = 10
    return (
        f'<circle cx="{cx:.1f}" cy="{cy-28:.1f}" r="{head_r}" fill="none" stroke="#000" stroke-width="1.2"/>'
        f'<line x1="{cx:.1f}" y1="{cy-18:.1f}" x2="{cx:.1f}" y2="{cy+4:.1f}" stroke="#000" stroke-width="1.2"/>'
        f'<line x1="{cx-16:.1f}" y1="{cy-8:.1f}" x2="{cx+16:.1f}" y2="{cy-8:.1f}" stroke="#000" stroke-width="1.2"/>'
        f'<line x1="{cx:.1f}" y1="{cy+4:.1f}" x2="{cx-14:.1f}" y2="{cy+28:.1f}" stroke="#000" stroke-width="1.2"/>'
        f'<line x1="{cx:.1f}" y1="{cy+4:.1f}" x2="{cx+14:.1f}" y2="{cy+28:.1f}" stroke="#000" stroke-width="1.2"/>'
        f'<text x="{cx:.1f}" y="{cy+46:.1f}" text-anchor="middle" font-size="12" '
        f'font-family="Microsoft YaHei,SimSun,sans-serif">{_esc(label)}</text>'
    )


def _edge_points(layout: dict[str, Any], fid: str, tid: str) -> tuple[float, float, float, float]:
    nodes = {n["id"]: n for n in layout["l1"] + layout["l2"]}
    if fid == "actor":
        a = layout["actor"]
        x1, y1 = a["cx"] + 20, a["cy"]
    else:
        a = nodes[fid]
        x1, y1 = a["cx"] + a["w"] / 2, a["cy"]
    b = nodes[tid]
    x2, y2 = b["cx"] - b["w"] / 2, b["cy"]
    return x1, y1, x2, y2


def render_usecase_svg(model: dict[str, Any]) -> str:
    lay = layout_usecase(model)
    parts: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{lay["width"]:.0f}" height="{lay["height"]:.0f}" '
        f'viewBox="0 0 {lay["width"]:.1f} {lay["height"]:.1f}">',
        "<defs>"
        '<marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
        '<path d="M 0 0 L 10 5 L 0 10 z" fill="#000"/></marker>'
        "</defs>",
        '<rect width="100%" height="100%" fill="#fff"/>',
    ]
    parts.append(_actor_svg(lay["actor"]["cx"], lay["actor"]["cy"], lay["actor"]["label"]))

    for e in lay["assoc"]:
        x1, y1, x2, y2 = _edge_points(lay, e["from"], e["to"])
        parts.append(
            f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
            f'stroke="#000" stroke-width="1" marker-end="url(#arrow)"/>'
        )

    for e in lay["edges"]:
        x1, y1, x2, y2 = _edge_points(lay, e["from"], e["to"])
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2 - 8
        parts.append(
            f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
            f'stroke="#000" stroke-width="1" stroke-dasharray="6 4" marker-end="url(#arrow)"/>'
        )
        parts.append(
            f'<text x="{mx:.1f}" y="{my:.1f}" text-anchor="middle" font-size="11" '
            f'font-family="Microsoft YaHei,SimSun,sans-serif">{_esc(e["label"])}</text>'
        )

    for n in lay["l1"] + lay["l2"]:
        parts.append(_ellipse_svg(n["cx"], n["cy"], n["w"], n["h"], n["label"]))

    parts.append("</svg>")
    return "".join(parts)


def export_staruml_mdj(model: dict[str, Any]) -> str:
    """生成 StarUML 可打开的 .mdj（UMLUseCaseDiagram + Include/Extend）。"""
    lay = layout_usecase(model)
    actor_lab = lay["actor"]["label"]
    title = str(model.get("title") or "用例图")

    def oid() -> str:
        return _new_id("AAAAA")

    project_id = oid()
    model_id = oid()
    diagram_id = oid()
    actor_id = oid()

    owned: list[dict[str, Any]] = []
    views: list[dict[str, Any]] = []

    # Actor
    owned.append({"_type": "UMLActor", "_id": actor_id, "_parent": {"$ref": model_id}, "name": actor_lab})
    views.append(
        {
            "_type": "UMLActorView",
            "_id": oid(),
            "_parent": {"$ref": diagram_id},
            "model": {"$ref": actor_id},
            "left": int(lay["actor"]["cx"] - 30),
            "top": int(lay["actor"]["cy"] - 40),
            "width": 60,
            "height": 70,
        }
    )

    uc_ids: dict[str, str] = {}
    for n in lay["l1"] + lay["l2"]:
        uid = oid()
        uc_ids[n["id"]] = uid
        owned.append(
            {
                "_type": "UMLUseCase",
                "_id": uid,
                "_parent": {"$ref": model_id},
                "name": n["label"],
            }
        )
        views.append(
            {
                "_type": "UMLUseCaseView",
                "_id": oid(),
                "_parent": {"$ref": diagram_id},
                "model": {"$ref": uid},
                "left": int(n["cx"] - n["w"] / 2),
                "top": int(n["cy"] - n["h"] / 2),
                "width": int(n["w"]),
                "height": int(n["h"]),
            }
        )

    # associations actor-l1
    for n in lay["l1"]:
        assoc_id = oid()
        end1 = oid()
        end2 = oid()
        owned.append(
            {
                "_type": "UMLAssociation",
                "_id": assoc_id,
                "_parent": {"$ref": model_id},
                "end1": {
                    "_type": "UMLAssociationEnd",
                    "_id": end1,
                    "_parent": {"$ref": assoc_id},
                    "reference": {"$ref": actor_id},
                },
                "end2": {
                    "_type": "UMLAssociationEnd",
                    "_id": end2,
                    "_parent": {"$ref": assoc_id},
                    "reference": {"$ref": uc_ids[n["id"]]},
                },
            }
        )
        views.append(
            {
                "_type": "UMLAssociationView",
                "_id": oid(),
                "_parent": {"$ref": diagram_id},
                "model": {"$ref": assoc_id},
                "tail": {"$ref": actor_id},
                "head": {"$ref": uc_ids[n["id"]]},
            }
        )

    for e in lay["edges"]:
        rel_id = oid()
        src = uc_ids[e["from"]]
        dst = uc_ids[e["to"]]
        if e["kind"] == "extend":
            owned.append(
                {
                    "_type": "UMLExtend",
                    "_id": rel_id,
                    "_parent": {"$ref": model_id},
                    "source": {"$ref": src},
                    "target": {"$ref": dst},
                }
            )
            vtype = "UMLExtendView"
        else:
            owned.append(
                {
                    "_type": "UMLInclude",
                    "_id": rel_id,
                    "_parent": {"$ref": model_id},
                    "source": {"$ref": src},
                    "target": {"$ref": dst},
                }
            )
            vtype = "UMLIncludeView"
        views.append(
            {
                "_type": vtype,
                "_id": oid(),
                "_parent": {"$ref": diagram_id},
                "model": {"$ref": rel_id},
                "tail": {"$ref": src},
                "head": {"$ref": dst},
            }
        )

    uml_model = {
        "_type": "UMLModel",
        "_id": model_id,
        "_parent": {"$ref": project_id},
        "name": "UseCaseModel",
        "ownedElements": owned
        + [
            {
                "_type": "UMLUseCaseDiagram",
                "_id": diagram_id,
                "_parent": {"$ref": model_id},
                "name": f"{actor_lab}用例图",
                "ownedViews": views,
            }
        ],
    }
    doc = {
        "_type": "Project",
        "_id": project_id,
        "name": title,
        "ownedElements": [uml_model],
    }
    return json.dumps(doc, ensure_ascii=False, indent=2)


# ----- 不变量（客户硬约束，按 usecase_style 卡死）-----

def assert_usecase_invariants(
    model: dict[str, Any] | None,
    *,
    schema: dict[str, Any] | None = None,
    actor: str | None = None,
    style: dict[str, Any] | None = None,
) -> None:
    """强制校验客户画法；不满足直接抛错，禁止出残图。"""
    st = style or resolve_usecase_style()
    n_l1 = int(st.get("level1_count") or _LEVEL1_COUNT)
    if not isinstance(model, dict):
        raise ValueError("usecase: 模型为空")
    side = actor or str((model.get("actor") or {}).get("id") or "")
    level1 = model.get("level1")
    if not isinstance(level1, list) or len(level1) != n_l1:
        raise ValueError(f"usecase: 一级用例须为 {n_l1} 个，实际 {len(level1) if isinstance(level1, list) else None}")

    # 约束3+4：段落描述 + 序号与图中一级用例一一对应（几个一级就几个序号）
    desc = str(model.get("description") or "")
    if not desc.strip():
        raise ValueError("usecase: 缺少文字描述")
    if st.get("description_form") == "paragraph" and "\n" in desc.strip():
        raise ValueError("usecase: 描述须为段落形式（不得换行拆条）")
    if st.get("description_numbers_match_l1"):
        # 与图上一级个数严格对上：不多不少、各恰好一次
        for i in range(1, n_l1 + 1):
            if desc.count(f"（{i}）") != 1:
                raise ValueError(
                    f"usecase: 描述序号（{i}）须恰好出现一次，并与一级用例个数 {n_l1} 一一对应"
                )
        if f"（{n_l1 + 1}）" in desc:
            raise ValueError(
                f"usecase: 描述序号超出图中一级用例个数（图有 {n_l1} 个一级，不得出现（{n_l1 + 1}））"
            )

    allowed_keys: set[str] = set()
    if isinstance(schema, dict):
        aid = _normalize_actor_id(side)
        if aid in ("user", "admin"):
            menus = schema.get("menus") if isinstance(schema.get("menus"), dict) else {}
            for raw in menus.get(aid) or []:
                if isinstance(raw, dict):
                    k = str(raw.get("key") or "").strip()
                    if k:
                        allowed_keys.add(k)
            if aid == "admin":
                allowed_keys.add("dashboard")
        elif aid == "subadmin" or aid.startswith("staff:"):
            try:
                _, _, items = _resolve_actor_items(schema, aid)
            except ValueError:
                items = []
            for it in items:
                k = str(it.get("key") or "").strip()
                if k:
                    allowed_keys.add(k)
            allowed_keys.add("dashboard")
            post = _find_staff_post(schema, aid) if aid.startswith("staff:") else None
            if post:
                for pk in post.get("packs") or []:
                    if isinstance(pk, str) and pk in PACK_WORK_PAGES:
                        allowed_keys |= set(PACK_WORK_PAGES[pk])
            pages = schema.get("staffPackPages") if isinstance(schema.get("staffPackPages"), dict) else {}
            for _pack, plist in pages.items():
                if isinstance(plist, list):
                    allowed_keys |= {str(x) for x in plist if x}

    for uc in level1:
        if not isinstance(uc, dict):
            raise ValueError("usecase: 一级用例结构错误")
        lab = str(uc.get("label") or "")
        if looks_latin(lab):
            raise ValueError(f"usecase: 一级用例拉丁文标签 {lab}")
        if any(t in lab for t in ("综合功能", "综合业务")):
            raise ValueError(f"usecase: 一级禁止空壳名 {lab}（合并须保留主业务名）")
        kids = uc.get("includes") or []
        if not isinstance(kids, list) or not kids:
            raise ValueError(f"usecase: {lab} 缺少二级用例")
        has_include = False
        for k in uc.get("menu_keys") or []:
            if allowed_keys and k and k not in allowed_keys:
                raise ValueError(f"usecase: 发明菜单 key {k}")
        for kid in kids:
            if not isinstance(kid, dict):
                raise ValueError("usecase: 二级用例结构错误")
            klab = str(kid.get("label") or "")
            if looks_latin(klab):
                raise ValueError(f"usecase: 二级用例拉丁文标签 {klab}")
            # 约束5：二级动词开头
            if st.get("l2_verb_required") and not _VERB_PREFIX_RE.match(klab):
                raise ValueError(f"usecase: 二级用例须动词开头: {klab}")
            if re.match(r"^管理.+管理$", klab) or re.match(r"^查看.+查看$", klab):
                raise ValueError(f"usecase: 标签叠字 {klab}")
            rel = kid.get("relation")
            if rel not in ("include", "extend"):
                raise ValueError(f"usecase: 非法 relation {rel}")
            if rel == "include":
                has_include = True
            if rel == "extend" and not st.get("allow_extend"):
                raise ValueError("usecase: 当前客户样式不允许 <<extend>>")
            aid = _normalize_actor_id(side)
            if aid != "user" and klab == "进行支付":
                raise ValueError("usecase: 非用户角色不得挂进行支付")
            for mk in kid.get("menu_keys") or []:
                if allowed_keys and mk and mk not in allowed_keys:
                    raise ValueError(f"usecase: 发明菜单 key {mk}")
        # 约束2：每个一级至少一条 include
        if st.get("require_include_dashed") and not has_include:
            raise ValueError(f"usecase: {lab} 至少须有一条 <<include>>")
        if re.match(r"^管理.+管理$", lab):
            raise ValueError(f"usecase: 一级标签叠字 {lab}")

    # 约束1：同尺寸 + 两列竖线对齐
    lay = layout_usecase(model)
    ew, eh = float(st.get("ellipse_w") or _UC_W), float(st.get("ellipse_h") or _UC_H)
    if st.get("same_size_ellipses"):
        if abs(lay["uc_w"] - ew) > 0.1 or abs(lay["uc_h"] - eh) > 0.1:
            raise ValueError("usecase: 椭圆尺寸与客户样式不一致")
        for n in lay["l1"] + lay["l2"]:
            if abs(float(n["w"]) - ew) > 0.1 or abs(float(n["h"]) - eh) > 0.1:
                raise ValueError("usecase: 存在不同尺寸的用例椭圆")
    if st.get("l1_column_align"):
        l1xs = {round(n["cx"], 1) for n in lay["l1"]}
        if len(l1xs) != 1:
            raise ValueError(f"usecase: 一级圆心未对齐同一竖线 {l1xs}")
    if st.get("l2_column_align") and lay["l2"]:
        l2xs = {round(n["cx"], 1) for n in lay["l2"]}
        if len(l2xs) != 1:
            raise ValueError(f"usecase: 二级圆心未对齐同一竖线 {l2xs}")
    for e in lay["edges"]:
        if e["kind"] == "include":
            if not any(n["id"] == e["from"] for n in lay["l1"]):
                raise ValueError("usecase: include 箭头方向错误（须一级→二级）")
            if e["label"] != "<<include>>":
                raise ValueError("usecase: include 标注错误")
        elif e["kind"] == "extend":
            if not any(n["id"] == e["from"] for n in lay["l2"]):
                raise ValueError("usecase: extend 箭头方向错误（须扩展→一级）")
            if e["label"] != "<<extend>>":
                raise ValueError("usecase: extend 标注错误")


def load_usecase_model(
    workspace: Path,
    *,
    actor: str = "user",
    proposal_text: str = "",
) -> dict[str, Any] | None:
    schema = _read_json(workspace / "domain.schema.json")
    if not schema:
        return None
    spec = _read_json(workspace / "spec.json")
    title_fb = str(spec.get("title") or "管理系统")
    st = resolve_usecase_style(spec=spec if isinstance(spec, dict) else None)
    return usecase_model(
        schema,
        actor=actor,
        proposal_text=proposal_text,
        title_fallback=title_fb,
        style=st,
        spec=spec if isinstance(spec, dict) else None,
    )


def assert_workspace_usecases(workspace: Path, *, proposal_text: str = "") -> None:
    """bake/校验：每个有门户的角色都必须能出合法用例图。"""
    schema = _read_json(workspace / "domain.schema.json")
    if not schema:
        raise ValueError("usecase: 缺少 domain.schema.json")
    actors = list_usecase_actors(schema)
    if not actors:
        raise ValueError("usecase: 无角色门户")
    for a in actors:
        model = load_usecase_model(workspace, actor=a["id"], proposal_text=proposal_text)
        if not model:
            raise ValueError(f"usecase: {a['id']} 生成失败")
        svg = render_usecase_svg(model)
        has_inc = "<<include>>" in svg or "&lt;&lt;include&gt;&gt;" in svg
        has_ext = "<<extend>>" in svg or "&lt;&lt;extend&gt;&gt;" in svg
        if not has_inc and not has_ext:
            raise ValueError("usecase: SVG 缺少关系标注")
        mdj = export_staruml_mdj(model)
        json.loads(mdj)
