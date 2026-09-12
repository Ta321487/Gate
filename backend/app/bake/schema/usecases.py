"""论文用例图（与模块图/测例同级必有交付物）。

优先解析开题「{身份}功能模块划分为…」作为一级用例骨架，再用交付 menus/岗位 pack
挂二级并做溯源；无材料枚举时回落 menus 归桶。

画法硬约束按客户样式卡死（见 usecase_style.py，默认可切换）：
1. 椭圆同尺寸；一/二级圆心各自共一条竖线
2. 一级↔二级虚线箭头 + <<include>>（条件扩展可用 <<extend>>，UML 方向）
3. 描述若写序号，须与图中一级用例一一对应（段落到（n）则一级圈为 n；不是写死 5）
4. 描述为段落形式；须引用图上全部一级/二级用例名；禁止空壳「完成相关操作」与凑数「确认×」
5. 全部二级用例动词开头；二级不得与一级同名
禁止菜单外 key；管理端/岗位不得挂「进行支付」。
一级名禁止「综合功能/综合业务」空壳：合并时保留主业务名；开题模块优先保留独立一级。
描述可经 LLM 润色目的语（见 agents_usecase），但圈名与序号以确定性模型为准。
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
    l1_count_bounds,
    resolve_usecase_style,
    style_public_view,
)
from app.bake.staff_posts import PACK_ADMIN_MENUS, PACK_WORK_PAGES

# 几何/数量默认取自当前客户样式（断言与布局以此为准）
_STYLE = resolve_usecase_style()
_L1_MIN, _L1_MAX, _L1_PREFERRED = l1_count_bounds(_STYLE)
# 兼容旧测试：preferred 作软默认，不再表示「必须恰好 N」
_LEVEL1_COUNT = _L1_PREFERRED
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
    r"切换|连接|打卡|签到|开门|补缴|申请|下单|收藏|浏览|进入|使用|参加|参与|收发|查阅|联系|发表|加入|"
    r"添加|修改|删除|回复|新增|干预|选购)"
)

# 开题细节里常见的「动作尾巴」，作名词干时要剥掉
_ACTION_TAIL_RE = re.compile(
    r"(新增|添加|编辑|修改|删除|审核|发货|上下架|操作|预警|状态)$"
)
_MATERIAL_FILLER_RE = re.compile(r"(操作)?等$")

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
    ("留言", "客服", "沟通"),
    ("评价",),
    ("活动", "公告", "促销", "资讯"),
    # 用户/商家/分类分属不同域，禁止同组硬并（否则出现「管理分类」吞用户）
    ("用户管理", "用户"),
    ("商家管理", "商家", "商户"),
    ("分类", "类目"),
    ("数据分析", "统计", "报表"),
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
    """去掉「管理xxx管理」「查看xxx查看」叠字，以及「管理添加/管理编辑」类叠动词。"""
    s = lab or ""
    for v in (verb, "管理", "查看", "提交", "办理", "确认", "编辑", "添加", "新增", "修改"):
        if not v or len(s) <= len(v) * 2:
            continue
        if s.startswith(v) and s.endswith(v):
            mid = s[len(v) : -len(v)]
            if mid:
                return f"{v}{mid}"
    # 「管理添加促销信息」「管理编辑店铺」→ 去掉外层管理，保留内层动作
    m = re.match(
        r"^管理(新增|添加|编辑|修改|删除|审核|查看|回复|办理|上下架)(.+)$",
        s,
    )
    if m:
        return f"{m.group(1)}{m.group(2)}"
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
                return _user_l1_from_leaf(leaf, root)
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


# 阶段拆分禁止用空壳「确认」；须是可落在同一菜单上的真实动作语义
_SPLIT_STAGE_VERBS_USER = ("查看", "选择", "提交", "浏览", "办理")
_SPLIT_STAGE_VERBS_ADMIN = ("查看", "管理", "审核", "编辑", "导出")


def _strip_leading_verb(lab: str) -> str:
    s = re.sub(r"\s+", "", str(lab or "").strip())
    m = _VERB_PREFIX_RE.match(s)
    if not m:
        return s
    rest = s[m.end() :]
    # 整词既是动词又是业务名（预约/评价/收藏/登录…）时保留，禁止掏空成「业务」
    if not rest:
        return s
    return rest


def _noun_stem(lab: str) -> str:
    """去掉动词前缀与常见后缀/动作尾，得到业务名词干。"""
    s = _strip_module_word(lab)
    # 「评价管理」「用户管理」：先去尾「管理」，避免「评价」被当成动词前缀掏空
    if s.endswith("管理") and len(s) > 2:
        head = s[:-2]
        if head and head not in ("查看", "进行", "编辑"):
            s = head
    raw_keep = s
    stem = _strip_leading_verb(s)
    for _ in range(3):
        m = _ACTION_TAIL_RE.search(stem)
        if not m or len(stem) <= len(m.group(1)):
            break
        stem = stem[: -len(m.group(1))]
    for suf in ("功能", "管理", "列表", "中心", "信息", "记录", "模块", "浏览", "检索", "查询"):
        if stem.endswith(suf) and len(stem) > len(suf):
            stem = stem[: -len(suf)]
            break
    stem = stem.replace("我的", "") or stem
    if not stem or stem in ("管理", "查看", "进行", "编辑", "办理"):
        # 回落业务名本身（预约/评价），勿统一成「业务」
        if raw_keep and raw_keep not in ("管理", "查看", "进行", "编辑", "办理"):
            return raw_keep
        return "业务"
    return stem


def _scrub_material_seed(seed: str) -> str:
    """开题括号细节清洗：去权限腔/CRUD/等，收束以及/或。"""
    s = re.sub(r"\s+", "", str(seed or "").strip())
    if not s:
        return ""
    s = s.split("（")[0].split("(")[0].strip()
    s = _MATERIAL_FILLER_RE.sub("", s)
    # 权限/属性腔 → 不是用例动作
    s = re.sub(r"拥有最高权限|最高权限|全局", "", s)
    s = re.sub(r"增删改查|增删改|CRUD", "", s)
    s = s.replace("分别", "")
    # 「长期或短期座位预约」→ 整段预约语义，勿被「或」拆碎
    if re.search(r"(长期|短期).{0,8}预约", s) or re.search(r"座位预约", s):
        s = "座位预约"
    # 「库存以及库存预警」→ 取更具体的后段
    elif "以及" in s or re.search(r"(?<!以)及(?!其)", s):
        parts = [p for p in re.split(r"以及|(?<!以)及(?!其)", s) if p]
        if len(parts) >= 2:
            s = max(parts, key=lambda p: (len(p), p))
    # 「修改或查看订单状态」→ 优先「动词+宾语」完整段
    if "或" in s and "预约" not in s:
        parts = [p for p in s.split("或") if p]
        if len(parts) >= 2:
            scored: list[tuple[int, int, str]] = []
            for p in parts:
                has_verb = bool(_VERB_PREFIX_RE.match(p))
                has_obj = len(_strip_leading_verb(p)) >= 2 and _strip_leading_verb(p) != p
                rank = 0 if has_verb and has_obj else (1 if has_verb else 2)
                scored.append((rank, -len(p), p))
            scored.sort()
            s = scored[0][2]
    return s.strip("的之与和，,") or ""


def _polish_usecase_label(lab: str) -> str:
    """二级/细节标签终洗：禁 CRUD 堆砌、禁权限腔残留。"""
    s = re.sub(r"\s+", "", str(lab or "").strip())
    if not s:
        return s
    s = re.sub(r"拥有最高权限|最高权限|全局", "", s)
    s = re.sub(r"增删改查|增删改|CRUD", "", s)
    s = s.replace("分别", "")
    s = _dedupe_verb_noun_tail(s)
    if not s or s in ("管理", "查看", "进行"):
        return "管理业务"
    # 「管理商品信息」已够，勿再叠「信息信息」
    s = s.replace("信息信息", "信息")
    return s


def _infer_biz_from_module_name(name: str) -> str:
    n = _strip_module_word(name)
    if any(t in n for t in ("个人", "店铺", "中心", "资料")):
        return "profile"
    if any(t in n for t in ("订单", "购物车", "发货")):
        return "order"
    if any(t in n for t in ("公告", "活动", "资讯", "促销")):
        return "content"
    if any(t in n for t in ("客服", "沟通")):
        return "dm"
    if any(t in n for t in ("评价",)):
        return "extra"
    if any(t in n for t in ("用户",)):
        return "user"
    if any(t in n for t in ("农产品", "商品", "图书", "档案")):
        return "archive"
    if any(t in n for t in ("售后", "工单", "借阅", "申请")):
        return "ticket"
    if any(t in n for t in ("预约", "挂号", "选座")):
        return "slot"
    return "extra"


def _as_view_if_noun_phrase(s: str) -> str | None:
    """「预约记录」「评价信息」等：前缀碰巧是动词，实为名词短语 → 查看…"""
    m = _VERB_PREFIX_RE.match(s)
    if not m:
        return None
    rest = s[m.end() :]
    if not rest:
        return None
    if s.startswith(
        (
            "查看",
            "浏览",
            "管理",
            "编辑",
            "提交",
            "填写",
            "进行",
            "办理",
            "添加",
            "修改",
            "删除",
            "新增",
            "选购",
            "回复",
            "审核",
            "导出",
        )
    ):
        return None
    if rest in ("记录", "信息", "通知", "列表", "详情", "消息", "动态", "内容") or rest.endswith(
        ("记录", "通知", "列表", "消息")
    ):
        return f"查看{s}"
    return None


def _label_from_material_seed(seed: str, *, side: str, parent: str = "") -> str:
    """开题细节 → 可读的二级用例名（禁止权限腔/CRUD 堆砌/叠动词）。"""
    raw_seed = str(seed or "")
    s = _scrub_material_seed(seed)
    parent_stem = _noun_stem(parent) if parent else "业务"
    parent_blob = parent or ""

    # 洗空后的权限-only 细节：按父模块落成真正动作
    if not s:
        if "订单" in parent_blob or "订单" in raw_seed:
            return "干预订单状态"
        if any(t in parent_blob for t in ("商品", "农产品")):
            return "管理商品信息"
        return "查看详情" if side == "user" else "管理业务"

    if "沟通" in s or (s.startswith("与") and "商家" in s):
        return "联系用户与商家"
    if "审核" in s and any(t in s + parent_blob for t in ("商品", "图片", "内容", "农产品")):
        # 「最高权限审核商品内容与图片」→ 审核商品内容与图片
        tail = re.sub(r"^.*?审核", "审核", s)
        if not tail.startswith("审核"):
            tail = f"审核{s}"
        return _polish_usecase_label(tail)
    if s in ("权限", "信息") or s.endswith("权限"):
        if "订单" in parent_blob:
            return "干预订单状态"
        return f"管理{parent_stem}" if parent_stem != "业务" else "管理业务"

    # 名词短语误命中动词前缀（预约记录）须先改写
    nounish = _as_view_if_noun_phrase(s)
    if nounish:
        return _polish_usecase_label(nounish)

    # 已是动宾
    if _VERB_PREFIX_RE.match(s):
        return _polish_usecase_label(_dedupe_verb_noun_tail(s))

    # 纯动作词 / 常见开题动宾碎片
    if s in ("上下架",):
        return "办理上下架"
    if s in ("发货", "发货操作"):
        return "办理发货"
    if "库存" in s:
        return "查看库存预警" if "预警" in s else "查看库存"
    if "支付" in s or "扫码支付" in s:
        return "进行支付"
    if s.endswith("充值") or s == "充值" or "余额充值" in s:
        return "进行充值"
    if "补缴" in s:
        return "进行补缴"
    if s.startswith("选购") or "选购" in s:
        stem = s.replace("选购", "", 1) if s.startswith("选购") else re.sub(r"^.*选购", "", s)
        stem = stem or "套餐"
        return _polish_usecase_label(f"选购{stem}")
    if "座位预约" in s or (s.endswith("预约") and "预约" in parent_blob):
        return "进行预约"
    if s.endswith("预约") and len(s) > 2:
        return _polish_usecase_label(f"进行{s}" if not s.startswith("进行") else s)

    # 「名词+动作」倒装：农产品商品新增 / 信息编辑 / 退货审核 / 店铺信息编辑
    m = re.match(
        r"^(.+?)(新增|添加|编辑|修改|删除|审核|发货|上下架)$",
        s,
    )
    if m:
        noun, act = m.group(1), m.group(2)
        noun = noun.replace("商品商品", "商品")
        if act == "上下架":
            return "办理上下架"
        if act == "发货":
            return "办理发货"
        if act in ("新增", "添加"):
            if noun.endswith("商品") and len(noun) > 2:
                noun = noun[:-2] or noun
            noun = noun or parent_stem
            return _polish_usecase_label(f"{act}{noun}")
        if act == "编辑":
            if not noun or noun in ("信息",) or noun.endswith("信息"):
                stem = parent_stem if parent_stem != "业务" else _noun_stem(noun) or "信息"
                if stem.endswith("信息"):
                    return _polish_usecase_label(f"编辑{stem}")
                return _polish_usecase_label(f"编辑{stem}信息")
            return _polish_usecase_label(f"编辑{noun}")
        if act == "审核":
            return _polish_usecase_label(f"审核{noun}" if noun else "审核申请")
        if act == "修改":
            return _polish_usecase_label(f"修改{noun}" if noun else "修改信息")
        if act == "删除":
            return _polish_usecase_label(f"删除{noun}" if noun else "删除记录")

    if "回复" in s and "评价" in s:
        return "回复用户评价"
    if "评价" in s:
        return "管理评价" if side != "user" else "查看评价"
    # 「商品信息」类名词：管理端写管理×，勿再拼 CRUD
    if any(t in s for t in ("商品信息", "商品", "农产品")) and side != "user":
        stem = _noun_stem(s) or "商品"
        return _polish_usecase_label(f"管理{stem}信息" if "信息" not in stem else f"管理{stem}")

    default_verb = "管理" if side == "admin" else "查看"
    return _polish_usecase_label(ensure_verb_prefix(s, default_verb=default_verb))


def _user_l1_from_leaf(leaf: str, root: str) -> str:
    """用户端一级名：避免「查看图书检索」类叠义，优先动宾清楚。"""
    raw = _strip_module_word(leaf)
    if not raw:
        tpl = _BIZ_L1_TEMPLATE.get(root)
        return tpl if tpl and _VERB_PREFIX_RE.match(tpl) else "查看其它业务"
    if _VERB_PREFIX_RE.match(raw):
        return _dedupe_verb_noun_tail(raw)
    if raw.endswith("检索") and len(raw) > 2:
        return f"检索{raw[:-2]}"
    if raw.endswith("查询") and len(raw) > 2:
        return f"查询{raw[:-2]}"
    if "选医生" in raw or (raw.startswith("选") and "医" in raw):
        return "选择医生"
    if raw.endswith("浏览") and len(raw) > 2:
        return f"浏览{raw[:-2]}"
    if any(t in raw for t in ("公告", "资讯", "通知")):
        return "查看公告"
    if any(t in raw for t in ("个人", "资料", "中心", "画像")):
        return "查看个人资料"
    if raw.startswith("我的"):
        return f"查看{raw}"
    if root in ("slot", "ticket") or any(t in raw for t in ("预约", "借阅", "申请", "挂号")):
        return ensure_verb_prefix(raw, default_verb="进行")
    if root in _BIZ_L1_TEMPLATE and root not in ("extra", "auth", "user"):
        tpl = _BIZ_L1_TEMPLATE[root]
        if _VERB_PREFIX_RE.match(tpl) or tpl in ("登录注册", "登录系统"):
            # 单叶且叶子比模板更贴菜单时，用叶子动宾
            if len(raw) >= 2 and raw not in tpl:
                return ensure_verb_prefix(
                    raw, default_verb="进行" if root in ("slot", "ticket") else "查看"
                )
            return tpl if _VERB_PREFIX_RE.match(tpl) else ensure_verb_prefix(tpl, default_verb="查看")
    return ensure_verb_prefix(raw, default_verb="查看")


def _semantic_l2_pair(
    *,
    side: str,
    lab_raw: str,
    key: str,
    biz: str,
) -> tuple[str, str]:
    """单菜单桶的两个 include：有语义、互异、不与空壳「确认」凑数。"""
    stem = _noun_stem(lab_raw)
    blob = f"{lab_raw}|{key}|{biz}"
    if side != "user":
        if biz == "profile" or any(t in blob for t in ("个人", "店铺", "中心", "资料")):
            return ("查看资料信息", "编辑店铺资料")
        if any(t in blob for t in ("数据", "分析", "统计")):
            return ("查看统计报表", "导出分析数据")
        if biz == "dm" or any(t in blob for t in ("客服", "沟通")):
            return ("查看客服会话", "回复用户消息")
        if "评价" in blob or stem in ("评价",):
            return ("查看评价列表", "管理评价")
        if biz == "slot" or "预约" in blob or stem in ("预约",):
            return ("查看预约列表", "办理预约")
        if any(t in blob for t in ("content", "公告", "资讯", "活动")):
            return ("查看公告列表", "编辑公告")
        if any(t in blob for t in ("user", "读者", "用户")) and "dashboard" not in key:
            return ("查看用户列表", "编辑用户信息")
        if stem in ("管理", "业务"):
            stem = _noun_stem(lab_raw) if _noun_stem(lab_raw) not in ("管理", "业务") else "业务"
        return (f"查看{stem}列表", f"编辑{stem}信息")

    if biz == "content" or any(t in blob for t in ("content", "公告", "资讯", "通知")):
        return ("浏览公告列表", "查看公告详情")
    if biz == "profile" or key == "profile" or any(t in blob for t in ("个人", "资料", "中心")):
        return ("浏览资料信息", "编辑个人资料")
    if any(t in blob for t in ("选医生", "医生")):
        return ("浏览医生列表", "查看医生详情")
    if biz == "archive" or "检索" in lab_raw or "查询" in lab_raw or "lookup" in key:
        noun = stem or "资料"
        return (f"浏览{noun}列表", f"查看{noun}详情")
    if biz == "ticket" or any(t in blob for t in ("借阅", "申请", "工单")):
        if "借阅" in blob:
            return ("查看借阅列表", "查看借阅详情")
        noun = stem or "申请"
        return (f"查看{noun}列表", f"查看{noun}详情")
    if biz == "slot" or any(t in blob for t in ("预约", "挂号", "选座")):
        noun = stem if stem not in ("业务", "") else "预约"
        return (f"查看{noun}列表", f"提交{noun}")
    if biz in ("order", "cart") or any(t in blob for t in ("订单", "购物车")):
        return ("查看订单列表", "查看订单详情")
    if "评价" in blob or stem == "评价":
        return ("查看评价列表", "发表评价")
    if "收藏" in blob:
        return ("查看收藏列表", "管理收藏")
    if "留言" in blob:
        return ("查看留言列表", "填写留言内容")
    if any(t in blob for t in ("商品", "农产品", "图书")):
        return (f"浏览{stem}列表", f"查看{stem}详情")
    return (f"查看{stem}列表", f"查看{stem}详情")


def _mint_distinct_l2(l1_label: str, used: set[str]) -> str:
    stem = _noun_stem(l1_label)
    s = str(l1_label or "")
    preferred: tuple[str, ...] = ()
    if "登录" in s and "注册" not in s:
        preferred = ("提交登录信息", "填写账号密码")
    elif "注册" in s:
        preferred = ("填写注册信息", "提交注册申请")
    for cand in preferred + (
        f"查看{stem}详情",
        f"浏览{stem}列表",
        f"编辑{stem}信息",
        f"提交{stem}",
        f"办理{stem}",
        f"管理{stem}",
    ):
        lab = cand if _VERB_PREFIX_RE.match(cand) else ensure_verb_prefix(cand, default_verb="查看")
        if lab not in used and lab != l1_label:
            return lab
    return ensure_verb_prefix(f"{stem}补充", default_verb="查看")


def _finalize_includes(l1_label: str, kids: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """禁止 L2 与 L1 同名、禁止桶内 L2 互撞；必要时改写标签（不改 menu_keys）。"""
    used: set[str] = {str(l1_label or "").strip()}
    out: list[dict[str, Any]] = []
    for kid in kids:
        if not isinstance(kid, dict):
            continue
        row = dict(kid)
        lab = str(row.get("label") or "").strip()
        nounish = _as_view_if_noun_phrase(lab)
        if nounish:
            lab = nounish
        if not lab or lab in used:
            lab = _mint_distinct_l2(l1_label, used)
        if not _VERB_PREFIX_RE.match(lab):
            lab = ensure_verb_prefix(lab, default_verb="查看")
        if lab in used or lab == l1_label:
            lab = _mint_distinct_l2(l1_label, used)
        lab = _polish_usecase_label(lab)
        if not lab or lab in used or lab == l1_label:
            lab = _mint_distinct_l2(l1_label, used)
        row["label"] = lab
        used.add(lab)
        out.append(row)
    return out


def _purpose_clause(lab: str) -> str:
    """一级用例的目的短句（接在「可通过「L1」」之后，不再写空壳「完成相关操作」）。"""
    s = str(lab or "").strip()
    if s in ("登录注册",) or ("登录" in s and "注册" in s):
        return "完成身份认证"
    if s in ("登录系统", "进行登录", "登录") or (s.endswith("登录") and "注册" not in s):
        return "完成系统登录"
    if "注册" in s and "登录" not in s:
        return "完成账号注册"
    if s.startswith("进入"):
        return "进入系统开展后续管理"
    if any(t in s for t in ("个人", "资料", "中心", "店铺")):
        return "维护账号与资料信息"
    if s.startswith("管理") or s.startswith("办理"):
        stem = _noun_stem(s)
        return f"完成{stem}管理"
    if any(t in s for t in ("图书", "馆藏")) and any(t in s for t in ("检索", "查询", "浏览")):
        return "查询馆藏信息"
    if any(t in s for t in ("检索", "查询", "浏览")) and not any(
        t in s for t in ("公告", "个人", "资料")
    ):
        return "查询业务资料"
    if "借阅" in s:
        return "办理借阅业务"
    if any(t in s for t in ("预约", "挂号", "申请")):
        return "办理相关业务"
    if any(t in s for t in ("公告", "资讯", "通知")):
        return "了解最新通知"
    if any(t in s for t in ("订单", "购物车", "支付")):
        return "完成交易相关操作"
    if any(t in s for t in ("评价", "留言", "收藏")):
        return "完成互动反馈"
    if "选择" in s or "选医" in s:
        return "选择业务对象"
    if any(t in s for t in ("数据", "分析", "统计")):
        return "查看经营数据"
    stem = _noun_stem(s)
    return f"完成{stem}相关业务"


def _join_usecase_quotes(names: list[str]) -> str:
    """「A」与「B」；三项及以上用顿号，末项用与。"""
    cleaned = [str(n).strip() for n in names if str(n).strip()]
    if not cleaned:
        return ""
    if len(cleaned) == 1:
        return f"「{cleaned[0]}」"
    if len(cleaned) == 2:
        return f"「{cleaned[0]}」与「{cleaned[1]}」"
    head = "、".join(f"「{n}」" for n in cleaned[:-1])
    return f"{head}与「{cleaned[-1]}」"


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


def _normalize_l1_buckets(
    buckets: list[tuple[str, list[dict[str, Any]]]],
    *,
    side: str,
    style: dict[str, Any] | None = None,
) -> list[tuple[str, list[dict[str, Any]]]]:
    """菜单回落：一级个数落在 [min,max]；已在区间内则不硬凑 preferred。"""
    mn, mx, pref = l1_count_bounds(style)
    cur = list(buckets)
    if len(cur) > mx:
        cur = _merge_buckets(cur, target=mx)
    if len(cur) < mn:
        cur = _split_buckets(cur, target=mn, side=side)
    # 仍少于 min：再朝 preferred 拆（可读性）
    if len(cur) < mn:
        cur = _split_buckets(cur, target=pref, side=side)
    if not (mn <= len(cur) <= mx):
        raise ValueError(
            f"usecase:{side}: 一级用例个数须在 {mn}–{mx}（当前 {len(cur)}）"
        )
    return cur


def _normalize_five(
    buckets: list[tuple[str, list[dict[str, Any]]]],
    *,
    side: str,
) -> list[tuple[str, list[dict[str, Any]]]]:
    """兼容旧名：等价于 _normalize_l1_buckets。"""
    return _normalize_l1_buckets(buckets, side=side)


def _build_l2_for_bucket(
    biz: str,
    items: list[dict[str, Any]],
    *,
    side: str,
    l1_id: str,
) -> list[dict[str, Any]]:
    includes: list[dict[str, Any]] = []

    # 认证拆分后的一级：L2 须与 L1 异名（L1 多为「进行登录/进行注册」）
    if items and items[0].get("_auth_part"):
        part = str(items[0].get("_auth_part") or "")
        label_map = {
            "login": "提交登录信息",
            "register": "填写注册信息",
            "enter": "进入管理系统",
        }
        includes.append(
            {
                "id": f"{l1_id}:{part or 'auth'}",
                "label": label_map.get(part, "提交登录信息"),
                "relation": "include",
                "menu_keys": [],
                "source": "auth",
            }
        )
        return includes

    if biz == "auth" or (items and items[0].get("biz") == "auth" and not items[0].get("_auth_part")):
        if side == "user":
            includes.append(
                {
                    "id": f"{l1_id}:login",
                    "label": "登录",
                    "relation": "include",
                    "menu_keys": [],
                    "source": "auth",
                }
            )
            includes.append(
                {
                    "id": f"{l1_id}:register",
                    "label": "注册",
                    "relation": "include",
                    "menu_keys": [],
                    "source": "auth",
                }
            )
        else:
            includes.append(
                {
                    "id": f"{l1_id}:login",
                    "label": "登录",
                    "relation": "include",
                    "menu_keys": [],
                    "source": "auth",
                }
            )
        return includes

    # 拆分叶：用 _verb（单独占一级时允许仅 1 个 include，禁止再挂空壳「确认」）
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

    # 单菜单桶：一对有语义的 include，禁止「查看X + 确认X」
    if len(items) == 1:
        it = items[0]
        key = str(it.get("key") or "")
        lab_raw = str(it.get("label") or key or "功能")
        a, b = _semantic_l2_pair(side=side, lab_raw=lab_raw, key=key, biz=biz)
        includes.append(
            {
                "id": f"{l1_id}:0",
                "label": a,
                "relation": "include",
                "menu_keys": [key] if key else [],
                "source": f"menu:{side}",
            }
        )
        includes.append(
            {
                "id": f"{l1_id}:1",
                "label": b,
                "relation": "include",
                "menu_keys": [key] if key else [],
                "source": f"menu:{side}",
            }
        )
        if _should_attach_pay_extend(side=side, items=items):
            includes.append(
                {
                    "id": f"{l1_id}:pay",
                    "label": "进行支付",
                    "relation": "extend",
                    "menu_keys": [key] if key else [],
                    "source": f"menu:{side}",
                }
            )
        return includes

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

    if not includes:
        raise ValueError(f"usecase: L1 {biz} 无二级用例")
    return includes


def _description_paragraph(actor: str, level1: list[dict[str, Any]]) -> str:
    """客户要求：段落形式；序号与一级个数严格一致；引用图上真实 L1/L2 名。"""
    parts: list[str] = []
    for i, uc in enumerate(level1, start=1):
        lab = str(uc.get("label") or "")
        kids = [k for k in (uc.get("includes") or []) if isinstance(k, dict)]
        includes = [k for k in kids if k.get("relation") == "include"]
        extends = [k for k in kids if k.get("relation") == "extend"]
        purpose = _purpose_clause(lab)
        bit = f"（{i}）{actor}可通过「{lab}」{purpose}"
        if includes:
            names = [str(k.get("label") or "") for k in includes]
            bit += f"，其中包含{_join_usecase_quotes(names)}"
        if extends:
            enames = [str(k.get("label") or "") for k in extends]
            bit += f"，并可扩展{_join_usecase_quotes(enames)}"
        bit += "。"
        parts.append(bit)
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
    """合并后一级名：跟优先级更高的那块，绝不改成综合业务；分类不吞用户/商品。"""
    sa, sb = _strip_module_word(a), _strip_module_word(b)
    weak = ("分类", "类目", "数据分析")
    strong = ("用户", "商家", "商户", "商品", "农产品", "订单", "售后", "评价", "活动")
    if any(t in sa for t in weak) and any(t in sb for t in strong):
        return sb or sa
    if any(t in sb for t in weak) and any(t in sa for t in strong):
        return sa or sb
    pa, pb = _mat_label_priority(a), _mat_label_priority(b)
    if pb < pa:
        return sb or b
    if pa < pb:
        return sa or a
    # 同级：保留更具体（更长）的业务名，避免「分类」吞「用户管理」
    if len(sb) > len(sa):
        return sb or sa
    return sa or sb


def _l1_label_from_material(name: str, *, side: str) -> str:
    raw = _strip_module_word(name)
    if not raw:
        return "查看其它功能" if side == "user" else "管理其它功能"
    if raw in ("登录注册", "登录", "注册") or ("登录" in raw and "注册" in raw):
        return "登录注册" if side == "user" else "登录系统"
    if raw in ("注册",) and side == "user":
        return "注册"
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
    style: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """开题一级模块 → 落在 [min,max]；区间内原样保留，禁止为凑 preferred 吞掉业务名。"""
    mn, mx, _pref = l1_count_bounds(style)
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
    # 仅当超出 max 才合并；优先并亲和组（客服+留言），避免农产品并进订单
    while len(cur) > mx and guard < 40:
        guard += 1
        best = None
        for i in range(len(cur)):
            for j in range(i + 1, len(cur)):
                aff = _mat_affinity(cur[i]["label"], cur[j]["label"])
                pen = 0
                if any(t in cur[i]["label"] for t in ("登录", "注册")) or any(
                    t in cur[j]["label"] for t in ("登录", "注册")
                ):
                    pen = 3
                # 跨业务主桶额外惩罚：用户/商家/分类/商品互不吞并
                cross_pen = 0
                labs = cur[i]["label"] + cur[j]["label"]
                buckets_hit = [
                    any(t in labs for t in ("用户",)),
                    any(t in labs for t in ("商家", "商户")),
                    any(t in labs for t in ("分类", "类目")),
                    any(t in labs for t in ("农产品", "商品", "图书")),
                    any(t in labs for t in ("订单",)),
                    any(t in labs for t in ("售后", "退货")),
                    any(t in labs for t in ("客服", "留言", "沟通")),
                    any(t in labs for t in ("活动", "公告")),
                    any(t in labs for t in ("数据", "分析")),
                    any(t in labs for t in ("评价",)),
                ]
                if sum(1 for x in buckets_hit if x) >= 2:
                    cross_pen = 5
                elif aff >= 5 and any(t in labs for t in ("个人", "中心", "店铺")) and any(
                    t in labs for t in ("农产品", "商品", "订单", "活动", "数据", "评价")
                ):
                    cross_pen = 5
                elif aff >= 5 and any(t in labs for t in ("农产品", "商品", "图书")) and any(
                    t in labs for t in ("订单", "售后", "活动", "数据", "用户", "商家")
                ):
                    cross_pen = 4
                key = (
                    aff + pen + cross_pen,
                    -len(cur[i]["details"]) - len(cur[j]["details"]),
                    i,
                    j,
                )
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

    # 仅当少于 min 才拆；不要为了凑到 preferred=5 而拆碎
    while len(cur) < mn and guard < 80:
        guard += 1
        multi = [(i, len(m.get("details") or [])) for i, m in enumerate(cur)]
        multi = [x for x in multi if x[1] > 0]
        if not multi:
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

    if not (mn <= len(cur) <= mx):
        raise ValueError(
            f"usecase:materials: 一级个数须在 {mn}–{mx}（当前 {len(cur)}）"
        )
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
                    {"id": f"{l1_id}:login", "label": "登录", "relation": "include", "menu_keys": [], "source": "auth"}
                )
                kids.append(
                    {"id": f"{l1_id}:register", "label": "注册", "relation": "include", "menu_keys": [], "source": "auth"}
                )
            elif "注册" in name:
                kids.append(
                    {"id": f"{l1_id}:register", "label": "注册", "relation": "include", "menu_keys": [], "source": "auth"}
                )
            else:
                kids.append(
                    {"id": f"{l1_id}:login", "label": "登录", "relation": "include", "menu_keys": [], "source": "auth"}
                )
        else:
            kids.append(
                {"id": f"{l1_id}:login", "label": "登录", "relation": "include", "menu_keys": [], "source": "auth"}
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
                        # 登录后可进可不进工作台 → extend，非必含 include
                        "relation": "extend",
                        "menu_keys": ["dashboard"],
                        "source": "menu:admin",
                    }
                )
        return kids

    # details / 被合并模块名 → L2
    seeds: list[str] = []
    for d in details:
        piece = _scrub_material_seed(d)
        if piece and piece not in seeds:
            seeds.append(piece)
    for m in merged:
        if m != name and m not in seeds:
            mm = _strip_module_word(m)
            if mm and mm not in seeds:
                seeds.append(mm)

    if not seeds:
        seeds = [_strip_module_word(name)]

    for idx, seed in enumerate(seeds[:6]):
        seed_raw = seed
        seed = _scrub_material_seed(seed) or _strip_module_word(seed)
        if not seed and not seed_raw:
            continue
        # 支付细节 → 用户侧挂 extend，不丢开题
        if any(t in (seed or seed_raw) for t in ("支付", "在线支付", "扫码支付")):
            if side == "user" and not any(k.get("label") == "进行支付" for k in kids):
                kids.append(
                    {
                        "id": f"{l1_id}:pay{idx}",
                        "label": "进行支付",
                        "relation": "extend",
                        "menu_keys": _menu_keys_matching(seed_raw + name, menu_items)[:1],
                        "source": "materials",
                    }
                )
            continue
        if not seed:
            continue
        lab = _label_from_material_seed(seed, side=side, parent=name)
        if lab.startswith("确认") and "浏览" in lab:
            lab = f"查看{lab[2:].replace('浏览', '')}" or "查看详情"
        if not _VERB_PREFIX_RE.match(lab):
            lab = ensure_verb_prefix(
                lab, default_verb="管理" if side == "admin" else "查看"
            )
        lab = _polish_usecase_label(_dedupe_verb_noun_tail(lab))
        keys = _menu_keys_matching(seed + name, menu_items)
        rel = "include"
        if lab == "进行支付":
            rel = "extend"
        elif side == "user" and any(t in seed for t in ("评价", "取消", "售后申请")):
            if not any(t in name for t in ("评价", "售后")):
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

    # 用户：仅当本模块名或细节明确写支付/下单/预约主路径时挂支付扩展
    # （禁止因「预约记录」等字样误挂到通知桶）
    pay_hint = any(t in name for t in ("购物车", "支付", "订单", "预约")) or any(
        ("支付" in d) or ("扫码" in d) for d in details
    )
    if side == "user" and pay_hint:
        if not any(k.get("label") == "进行支付" for k in kids):
            pay_keys = _menu_keys_matching(name + " ".join(details), menu_items) or [
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
    # 每个一级至少一条 include（校规虚线 <<include>>）
    if not any(k.get("relation") == "include" for k in kids):
        kids[0]["relation"] = "include"
    if len([k for k in kids if k.get("relation") == "include"]) == 1:
        only = next(k for k in kids if k.get("relation") == "include")
        key0 = ""
        mks = only.get("menu_keys") or []
        if mks:
            key0 = str(mks[0] or "")
        cur_lab = str(only.get("label") or "")
        used = {cur_lab, name}
        # 材料已给出清楚动宾：只补第二步，禁止整段换成泛化「查看业务列表」
        specific = bool(
            cur_lab
            and _VERB_PREFIX_RE.match(cur_lab)
            and "业务" not in cur_lab
            and not re.match(r"^查看.+列表$", cur_lab)
        )
        if specific:
            second = _mint_distinct_l2(name or cur_lab, used)
            kids.append(
                {
                    "id": f"{l1_id}:detail",
                    "label": second,
                    "relation": "include",
                    "menu_keys": list(mks),
                    "source": str(only.get("source") or "materials"),
                }
            )
        else:
            a, b = _semantic_l2_pair(
                side=side,
                lab_raw=name or cur_lab,
                key=key0,
                biz=_infer_biz_from_module_name(name),
            )
            only["label"] = a
            kids.append(
                {
                    "id": f"{l1_id}:detail",
                    "label": b,
                    "relation": "include",
                    "menu_keys": list(mks),
                    "source": str(only.get("source") or "materials"),
                }
            )
    return kids


def _level1_from_materials(
    section: dict[str, Any],
    *,
    side: str,
    actor_id: str,
    menu_items: list[dict[str, Any]],
    style: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    mods = _normalize_material_modules(
        list(section.get("modules") or []), side=side, style=style
    )
    level1: list[dict[str, Any]] = []
    for i, mod in enumerate(mods):
        l1_id = f"{actor_id}:uc{i+1}".replace(":", "_")
        label = _l1_label_from_material(str(mod.get("label") or ""), side=side)
        # 支付不宜单独占一级：若归一后仍叫进行支付，并入订单语义
        if label == "进行支付":
            label = "管理购物车" if side == "user" else "管理订单"
        kids = _l2_from_material_module(mod, side=side, l1_id=l1_id, menu_items=menu_items)
        kids = _finalize_includes(label, kids)
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
                    sec,
                    side=side_verb,
                    actor_id=aid,
                    menu_items=items,
                    style=st,
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

    buckets = _normalize_l1_buckets(buckets, side=side_verb, style=st)

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
                        "relation": "extend",
                        "menu_keys": ["dashboard"],
                        "source": "menu:admin",
                    }
                )
        if (biz == "auth" or str(biz).startswith("auth")) and side_verb == "admin" and not auth_part:
            kids = [
                {
                    "id": f"{l1_id}:login",
                    "label": "登录",
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
                        "relation": "extend",
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
        kids = _finalize_includes(label, kids)
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
        # 略低于一级圆心均值，减少 Actor→上部模块连线交叉
        ys = [float(n["cy"]) for n in l1_nodes]
        mean_y = sum(ys) / len(ys)
        span = max(ys) - min(ys) if len(ys) > 1 else 0.0
        actor_cy = mean_y + span * 0.18

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
    mn, mx, _pref = l1_count_bounds(st)
    if not isinstance(model, dict):
        raise ValueError("usecase: 模型为空")
    side = actor or str((model.get("actor") or {}).get("id") or "")
    level1 = model.get("level1")
    if not isinstance(level1, list) or not level1:
        raise ValueError("usecase: 缺少一级用例")
    n_l1 = len(level1)
    if n_l1 < mn or n_l1 > mx:
        raise ValueError(f"usecase: 一级用例个数须在 {mn}–{mx}，实际 {n_l1}")

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
        if "完成相关操作" in desc:
            raise ValueError("usecase: 描述禁止空壳「完成相关操作」")
        for uc in level1:
            if not isinstance(uc, dict):
                continue
            ulab = str(uc.get("label") or "")
            if ulab and f"「{ulab}」" not in desc:
                raise ValueError(f"usecase: 描述未引用一级用例「{ulab}」")
            for kid in uc.get("includes") or []:
                if not isinstance(kid, dict):
                    continue
                klab = str(kid.get("label") or "")
                if klab and f"「{klab}」" not in desc:
                    raise ValueError(f"usecase: 描述未引用二级用例「{klab}」")

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
            if "等" in klab:
                raise ValueError(f"usecase: 二级禁止残留开题语气词 {klab}")
            if any(t in klab for t in ("增删改查", "最高权限", "拥有最高权限")):
                raise ValueError(f"usecase: 二级禁止权限腔/CRUD 堆砌 {klab}")
            if re.match(r"^管理(新增|添加|编辑|修改|删除|审核|查看|回复|办理)", klab):
                raise ValueError(f"usecase: 二级禁止叠动词 {klab}")
            if re.search(r"编辑.+编辑", klab) or re.search(r"查看.+编辑列表", klab):
                raise ValueError(f"usecase: 二级名词干未清洗 {klab}")
            if klab in ("查看管理列表", "编辑管理信息"):
                raise ValueError(f"usecase: 二级名词干退化 {klab}")
            if klab == lab:
                raise ValueError(f"usecase: 二级不得与一级同名 {klab}")
            if klab.startswith("确认") and any(
                isinstance(x, dict)
                and str(x.get("label") or "").startswith("查看")
                and _noun_stem(str(x.get("label") or "")) == _noun_stem(klab)
                for x in kids
            ):
                raise ValueError(f"usecase: 禁止凑数二级 {klab}")
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
