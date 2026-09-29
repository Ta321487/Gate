"""单据/档案提示文案 + 页面级话术槽位（bake 期解析，运行时只读）。

两层职责：

1. **话术槽位层（L2）**：把「分类轴 / 单据名词」这类页面级话术收敛到唯一来源，
   供 `followup_domain_schema()` 写进 ``schema["lex"]``，再由各处页面文案消费。
   解析优先级（设计稿 §5.2）：
   开题抽取（须落在本域允许集内）→ 域词表/域默认 override（实体标签）→ 通用兜底。
2. **既有单据提示文案**：库存扣尽与不可用标签。

本模块是叶子模块（不 import 本仓其它模块），避免与 shells / followup_presets 成环。
"""

from __future__ import annotations

import re
from typing import Any, Iterable

# --- 话术槽位 ---------------------------------------------------------------

# slot -> 同义簇（有序；只处理同义簇内的用词差异，不做自然语言理解）
SLOT_CLUSTERS: dict[str, tuple[str, ...]] = {
    "category_axis": ("分级", "等级", "评级", "星级", "档位", "标签", "类目", "分类", "类别"),
    "ticket_noun": (
        "上报",
        "填报",
        "打卡",
        "申报",
        "申请",
        "报修",
        "登记",
        "诉求",
        "预约",
        "借阅",
        "借用",
        "取件",
        "领用",
        "投递",
        "周报",
        "跟进",
        "续借",
        "签到",
    ),
}

# 通用兜底（四级解析的最后一级）
SLOT_FALLBACKS: dict[str, str] = {"category_axis": "分类", "ticket_noun": "记录"}

# 页面文案里的槽位占位符：{category_axis} / {ticket_noun} / {archive_plural} ...
SLOT_TOKEN_RE = re.compile(r"\{([a-z][a-z0-9_]*)\}")

_TICKET_SHELL_PRESET_KEYS = (
    "my_tickets_label",
    "my_tickets_page_lead",
    "my_tickets_empty",
    "pending_label",
    "records_label",
)

_TICKET_LABEL_SUFFIXES = ("单", "记录", "表")


def _noun_from_ticket_label(label: str) -> str:
    """「上报单」→上报 / 「跟进单」→跟进 / 「周报」→周报。"""
    s = (label or "").strip()
    for suf in _TICKET_LABEL_SUFFIXES:
        if len(s) > len(suf) + 1 and s.endswith(suf):
            return s[: -len(suf)]
    return s


def _archive_category_label(archive: dict[str, Any]) -> str:
    fields = archive.get("fields") or archive.get("archive_fields") or []
    for f in fields:
        if isinstance(f, dict) and f.get("key") == "category":
            label = str(f.get("label") or "").strip()
            if label:
                return label
    return ""


def preset_slots(preset: dict[str, Any]) -> dict[str, str]:
    """从预设/覆盖（域默认 override 层）解析槽位值——实体标签为单一真源。

    单据名词例外：若域自己的单据壳话术（`my_tickets_*` 等）用了另一个复合词
    （查寝域写「归寝登记」而票据标签叫「归寝签到」），以**话术**为准——否则会把
    域精心区分的两个概念（登记 vs 口令签到）压成一个。
    """
    archive_label = str(preset.get("archive_label") or "").strip()
    ticket_label = str(preset.get("ticket_label") or "").strip()
    noun = _noun_from_ticket_label(ticket_label)
    return {
        "entity_label": archive_label,
        "entity_plural": str(preset.get("archive_plural") or archive_label).strip(),
        "ticket_label": ticket_label,
        "ticket_plural": str(preset.get("ticket_plural") or ticket_label).strip(),
        "category_axis": _archive_category_label(preset) or str(preset.get("category_axis") or "").strip(),
        "ticket_noun": _noun_from_shell_copy(preset, noun) or noun,
    }


def _noun_from_shell_copy(preset: dict[str, Any], derived: str) -> str:
    """域话术里是否把「票据标签前缀 + 另一个簇词」写成了复合名词（归寝+登记）。

    只在**票据标签自带前缀**的前提下比对，避免把「晚归/我的/右上角」这类
    偶然相邻的字误当名词前缀（那会造出「晚归登记」「我的预约」）。
    """
    prefix, tail = _split_axis(derived, SLOT_CLUSTERS["ticket_noun"])
    if not prefix:
        return derived
    texts = [
        str(preset.get(k))
        for k in _TICKET_SHELL_PRESET_KEYS
        if isinstance(preset.get(k), str) and preset.get(k)
    ]
    for word in SLOT_CLUSTERS["ticket_noun"]:
        if word == tail:
            continue
        cand = f"{prefix}{word}"
        if any(cand in text for text in texts):
            return cand
    return derived


def copy_authoritative_noun(preset: dict[str, Any]) -> str:
    """域自己话术里写明的复合单据名词（「归寝登记」），没有则返回空串。

    这类名词视为权威：材料里的通用簇词（签到/申请）不得把它压回单字概念。
    """
    if not isinstance(preset, dict):
        return ""
    derived = _noun_from_ticket_label(str(preset.get("ticket_label") or ""))
    cand = _noun_from_shell_copy(preset, derived)
    return cand if cand and cand != derived else ""


def schema_slots(schema: dict[str, Any]) -> dict[str, str]:
    """从已组装 schema 解析槽位值（与 :func:`preset_slots` 同口径，供门禁复核）。"""
    ents = schema.get("entities") if isinstance(schema.get("entities"), dict) else {}
    archive = ents.get("archive") if isinstance(ents.get("archive"), dict) else {}
    ticket = ents.get("ticket") if isinstance(ents.get("ticket"), dict) else {}
    cat = ents.get("category") if isinstance(ents.get("category"), dict) else {}
    axis = _archive_category_label(archive) or str(cat.get("label") or "").strip()
    return {
        "entity_label": str(archive.get("label") or "").strip(),
        "entity_plural": str(archive.get("labelPlural") or "").strip(),
        "ticket_label": str(ticket.get("label") or "").strip(),
        "ticket_plural": str(ticket.get("labelPlural") or "").strip(),
        "category_axis": axis,
        "ticket_noun": _noun_from_ticket_label(str(ticket.get("label") or "")),
    }


def cluster_hits(text: str, slot: str) -> list[str]:
    """text 里出现的 slot 同义簇词（去重，保持簇内顺序）。"""
    if not isinstance(text, str) or not text:
        return []
    return [w for w in SLOT_CLUSTERS.get(slot, ()) if w in text]


def allowed_cluster_words(slot: str, texts: Iterable[str]) -> set[str]:
    """本域允许集：出现在本域自有话术里的簇词（域词表的 bake 期投影）。"""
    out: set[str] = set()
    for t in texts or ():
        out.update(cluster_hits(t, slot))
    return out


def _proposal_pick(text: str, slot: str, allowed: set[str]) -> str:
    """开题抽取：命中的簇词须在本域允许集内；取正文里最早出现的一个。"""
    if not text or not allowed:
        return ""
    try:  # 复用开题的否定/对比/文献转述仲裁，勿退回裸子串
        from app.bake.proposal_lexicon import keyword_mentioned
    except Exception:  # noqa: BLE001 - 独立使用时退化为子串
        keyword_mentioned = None  # type: ignore[assignment]
    best_pos = -1
    best = ""
    for word in SLOT_CLUSTERS.get(slot, ()):
        if word not in allowed:
            continue
        pos = text.find(word)
        if pos < 0:
            continue
        if keyword_mentioned is not None and not keyword_mentioned(text, word):
            continue
        if best_pos < 0 or pos < best_pos:
            best_pos, best = pos, word
    return best


def page_copy_texts(obj: Any) -> list[str]:
    """收集页面级话术文本（域词表投影用）：所有字符串值，递归。"""
    out: list[str] = []

    def _walk(node: Any) -> None:
        if isinstance(node, str):
            out.append(node)
        elif isinstance(node, dict):
            for v in node.values():
                _walk(v)
        elif isinstance(node, (list, tuple)):
            for v in node:
                _walk(v)

    _walk(obj)
    return out


def _split_axis(value: str, cluster: tuple[str, ...]) -> tuple[str, str]:
    """把分类轴名拆成「域限定前缀 + 同义簇词」，如 客户分级 → (客户, 分级)。"""
    for word in cluster:
        if value.endswith(word) and len(value) > len(word):
            return value[: -len(word)], word
    if value in cluster:
        return "", value
    return value, ""


def resolve_slots(
    preset: dict[str, Any],
    *,
    domain: str = "",
    proposal_text: str = "",
    allowed_texts: Iterable[str] | None = None,
) -> dict[str, str]:
    """四级解析：开题抽取 → 域词表/域默认 override → 通用兜底。

    ``category_axis`` 只跟随开题的**簇词**，域限定前缀保留（客户分级 + 开题「评级」
    → 客户评级）；轴名不含簇词（专有轴名）时不做抽取，避免造词。
    """
    _ = domain  # 域身份已经在 preset/overrides 里体现；签名保留供调用方语义自述
    slots = preset_slots(preset if isinstance(preset, dict) else {})
    texts = list(allowed_texts or ())
    for slot, cluster in SLOT_CLUSTERS.items():
        base = str(slots.get(slot) or "").strip() or SLOT_FALLBACKS[slot]
        allowed = allowed_cluster_words(slot, texts)
        allowed.add(base)
        if slot == "category_axis":
            prefix, tail = _split_axis(base, cluster)
            if not tail:
                slots[slot] = base
                continue
            # 分类轴是同义簇内的维度名：开题任一簇词都在本域允许集内（域限定前缀保留）
            picked = _proposal_pick(proposal_text or "", slot, set(cluster))
            slots[slot] = f"{prefix}{picked}" if picked else base
            continue
        if slot == "ticket_noun" and copy_authoritative_noun(preset):
            slots[slot] = base  # 域话术已写明复合名词（归寝登记），材料通用词不得覆盖
            continue
        picked = _proposal_pick(proposal_text or "", slot, allowed)
        slots[slot] = picked or base
    return slots


def fill_slots(obj: Any, lex: dict[str, str]) -> Any:
    """把页面文案里的 ``{slot}`` 占位符换成解析后的槽位值（原地，递归）。"""
    if isinstance(obj, str):
        if "{" not in obj:
            return obj
        return SLOT_TOKEN_RE.sub(lambda m: lex.get(m.group(1)) or m.group(0), obj)
    if isinstance(obj, dict):
        for k, v in list(obj.items()):
            obj[k] = fill_slots(v, lex)
        return obj
    if isinstance(obj, list):
        return [fill_slots(v, lex) for v in obj]
    return obj


def empty_state_text(ticket_noun: str, apply_verb: str = "提交") -> str:
    """列表空状态：单据名词随槽位走。"""
    noun = (ticket_noun or SLOT_FALLBACKS["ticket_noun"]).strip() or "记录"
    verb = (apply_verb or "提交").strip() or "提交"
    return f"还没有{noun}记录，点击右上角{verb}。"


def category_browse_lead(category_axis: str, plural: str) -> str:
    """「按分级浏览客户」类导语：分类轴名随槽位走。"""
    axis = (category_axis or SLOT_FALLBACKS["category_axis"]).strip() or "分类"
    who = (plural or "").strip()
    return f"按{axis}浏览{who}。" if who else f"按{axis}浏览。"


def normalize_slot_words(value: str, slot: str, slot_value: str) -> str:
    """把页面文案里同簇的其它词统一成解析值（同一 slot 只有一个话术来源）。

    邻近还有别的簇词、或前后缀已含解析值首尾时不动——避免造出「归寝归寝签到」
    「借阅借阅」这类叠词。"""
    if not value or not any(w in slot_value for w in SLOT_CLUSTERS.get(slot, ())):
        return value
    head = slot_value[:2]
    tail = slot_value[-2:]
    out = value
    for word in [w for w in SLOT_CLUSTERS[slot] if w != slot_value]:
        if word in slot_value or slot_value in word:
            continue  # 已被槽位值覆盖（分级 ⊂ 客户分级），无需替换
        idx = 0
        while True:
            i = out.find(word, idx)
            if i < 0:
                break
            near = out[max(0, i - 2) : i] + out[i + len(word) : i + len(word) + 2]
            left = out[max(0, i - 2) : i]
            right = out[i + len(word) : i + len(word) + 2]
            if (
                any(h in near for h in SLOT_CLUSTERS[slot])
                or slot_value in near
                or left.endswith(head)   # 「归寝」+「登记」→ 已是复合词，别叠成「归寝归寝签到」
                or right.startswith(tail)
            ):
                idx = i + len(word)
                continue
            out = f"{out[:i]}{slot_value}{out[i + len(word):]}"
            idx = i + len(slot_value)
    return out


def sibling_reject_tip(archive_label: str, apply_verb: str) -> str:
    """库存扣尽时自动驳回同对象待审的说明。"""
    noun = (archive_label or "项目").strip() or "项目"
    v = apply_verb or ""
    if "认领" in v:
        tip = "已确认认领"
    elif "借阅" in v or "借用" in v:
        tip = "已借完"
    elif "申领" in v:
        tip = "已申领完毕"
    elif "选课" in v or "报名" in v:
        tip = "名额已满"
    else:
        tip = "已无法再申请"
    return f"「{noun}」{tip}，系统自动驳回"


def stock_unavailable_label(stock_label: str) -> str:
    """available 模式下库存为 0 的标签：可认领→已认领。"""
    s = (stock_label or "可用").strip() or "可用"
    if s.startswith("可"):
        return "已" + s[1:]
    return f"暂无{s}"
