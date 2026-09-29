"""跨域专属名词表 + 可见面口径规则（C 批门禁数据源，error 级）。

设计稿 §7/§0.2：门禁必须**数据驱动、覆盖全部域**，禁止逐个 case 硬编码。

三条规则（全部确定性，不依赖 LLM）：

1. :func:`cross_domain_findings` —— 其它域的招牌词出现在本域页面可见文案，且不在
   本域自有实体词里（词表 = ``_NOUN_OWNERS`` 反向下发 forbidden）。
2. :func:`slot_divergence_findings` —— 同一 slot（``ticket_noun`` / ``category_axis``）
   在页面可见面出现同义簇内的第二个词（口径分叉）；槽位值由
   :mod:`app.bake.ticket_copy_text` 从实体标签解析，bake 期同一份结果落 ``schema["lex"]``。
3. :func:`render_guard_findings` —— 通用页**展示面**渲染域外字段（数量/到期/罚金/在借保留）
   必须落在 ``allow*`` / ``hasCap`` / 值守卫分支内（脚本取值、``v-model`` 表单输入、
   能力专属页不判）。

词表为人工复核过的初稿：从各域 ``proposal_packs_data`` 关键词与 ``domains.py`` 词表汇总后
按「像主叙事的招牌词」筛选，不收通用词（报名/公告/登录等）。
"""

from __future__ import annotations

import re
from typing import Any, Iterable

from app.bake.ticket_copy_text import (
    SLOT_CLUSTERS,
    cluster_hits,
    schema_slots,
)

# 招牌词 -> 归属域（该词作为本域主张时出现的域；不是穷举，只收互斥性强的词）
_NOUN_OWNERS: dict[str, tuple[str, ...]] = {
    "借阅": ("DOM-LIBRARY", "DOM-DOCLIB"),
    "续借": ("DOM-LIBRARY", "DOM-EQUIP"),
    "还书": ("DOM-LIBRARY",),
    "挂号": ("DOM-HOSPITAL",),
    "门诊": ("DOM-HOSPITAL",),
    "排课": ("DOM-COURSE", "DOM-GRADE"),
    "评教": ("DOM-EVAL",),
    "房源": ("DOM-LISTING", "DOM-PROPERTY"),
    "挂牌": ("DOM-LISTING", "DOM-PROCURE"),
    "客房": ("DOM-HOTEL",),
    "退房": ("DOM-HOTEL",),
    "查寝": ("DOM-CHECKIN", "DOM-BED"),
    "归寝": ("DOM-CHECKIN",),
    "点餐": ("DOM-FOOD",),
    "选座": ("DOM-CINEMA",),
    "取件": ("DOM-PARCEL",),
    "寄件": ("DOM-PARCEL",),
    "领养": ("DOM-LOST",),
    "寄养": ("DOM-HOTEL", "DOM-SALON"),
    "约拍": ("DOM-SALON",),
    "工时": ("DOM-INTERN", "DOM-LABOR"),
    "周报": ("DOM-INTERN",),
    "投递": ("DOM-RECRUIT",),
    "面试": ("DOM-RECRUIT",),
    "投票": ("DOM-VOTE",),
    "问卷": ("DOM-SURVEY",),
}

# 可见面口径分叉只在这些页面级槽位上判（避免把 archive_log「健康打卡」误判为单据名词分叉）
_TICKET_SHELL_KEYS = ("myTicketsEmpty", "myTicketsPageLead", "myTicketsEmptyArchive")
_TICKET_SHELL_MENUS = ("my_tickets",)


def _covered(word: str, slot_value: str) -> bool:
    """簇词被槽位值覆盖（同词或其组成部分，如「分级」⊂「客户分级」）。"""
    sv = (slot_value or "").strip()
    return bool(sv) and word in sv


# 域外字段 -> 需要的开关（前端渲染缺 allow* 分支即 error）
_GUARDED_FIELDS: dict[str, tuple[str, ...]] = {
    "dueAt": ("allowRenew", "pickLoanPeriod", "showDueCols"),
    "dueLabel": ("allowRenew", "pickLoanPeriod", "showDueCols"),
    "renewCount": ("allowRenew",),
    "qty": ("allowQty",),
    "actualQty": ("allowQty",),
    "holdExpireAt": ("allowBookHold", "book_hold"),
    "holdCountdownText": ("allowBookHold", "book_hold"),
    "hold_ready": ("allowBookHold", "book_hold"),
    "fineYuan": ("showFineCols", "fineLabel"),
    "fineStatus": ("showFineCols", "fineLabel"),
}
_GUARD_RE = re.compile(r"\ballow[A-Z][A-Za-z0-9]*\b|hasCap\s*\(|hasTrait\s*\(")
# 值守卫：字段不存在就不渲染，与 allow* 等效（如 `v-if="row.actualQty != null"`）
_VALUE_GUARD_RE = re.compile(r"!==?\s*(null|undefined)")
# 展示面：只有插值/表格列/绑定属性的行才是「渲染」；`v-model` 是表单输入，不是渲染域外字段
_DISPLAY_RE = re.compile(r"\{\{|prop\s*=|:label\s*=|:value\s*=|v-text|v-html")

# 能力专属页：菜单由能力挂载（见 app/bake/menu_routes.py 的能力→路由表），
# 页面主字段就是该字段，不属于「域外字段无条件渲染」，不纳入通用页判据。
# 这些文件里的 qty/dueAt 是页面自己的业务字段（表单输入、订单行数量、库存数量、台账主字段）。
_CAPABILITY_OWNED_PAGES: tuple[tuple[str, str], ...] = (
    ("views/admin/OverdueAdmin.vue", "deadline 能力页：dueAt/dueLabel 即页面主字段"),
    ("views/admin/StockLedgerAdmin.vue", "stock_ledger 能力页：qty 是库存数量"),
    ("views/admin/StockMovesAdmin.vue", "stock_moves 能力页：qty 是出入库数量（表单）"),
    ("views/admin/BalanceAccountsAdmin.vue", "balance_accounts 能力页：qty 是管理端表单输入"),
    ("views/admin/TicketRecordsAdmin.vue", "ticket_records 能力页：actualQty 已有值守卫"),
    ("views/user/Cart.vue", "购物车页：qty 是用户输入数量"),
    ("views/user/MyOrders.vue", "订单页：qty 是订单行数量"),
)
_CAPABILITY_OWNED = {path for path, _ in _CAPABILITY_OWNED_PAGES}


def _template_line_mask(lines: list[str]) -> list[bool]:
    """标记哪些行落在 `<template>` 渲染面内（含内联单行 template）。

    规则③只审渲染面：`<script>` 里的 `res.data?.dueAt`、`function holdCountdownText(row)`
    属于数据映射/工具函数，任何域都要能取值，不是「无条件渲染」。
    """
    mask: list[bool] = []
    depth = 0
    for line in lines:
        opens = len(re.findall(r"<template\b", line, re.I))
        closes = len(re.findall(r"</template>", line, re.I))
        mask.append(depth > 0 or opens > 0)
        depth = max(0, depth + opens - closes)
    return mask


def render_guard_findings(files: dict[str, Any], *, window: int = 6) -> list[dict[str, str]]:
    """规则③：通用页**渲染**域外字段必须落在 allow*/hasCap（或值）开关分支内。

    三条边界，避免误报：
    1. 只审 `.vue` 的 `<template>` 渲染面（脚本内取值/工具函数不是渲染）；
    2. 只审展示（`{{ }}` / `prop=` / `:label=`），`v-model` 表单输入不算；
    3. 能力专属页（菜单由能力挂载、该字段即页面主字段）与已有值守卫的行不判。
    """
    findings: list[dict[str, str]] = []
    for rel, body in (files or {}).items():
        if not isinstance(body, str) or not body or not rel.endswith(".vue"):
            continue
        norm = rel.replace("\\", "/")
        if any(norm.endswith(path) for path in _CAPABILITY_OWNED):
            continue
        lines = body.splitlines()
        in_template = _template_line_mask(lines)
        for field, guards in _GUARDED_FIELDS.items():
            hits = [
                i
                for i, line in enumerate(lines)
                if in_template[i]
                and _DISPLAY_RE.search(line)
                and "v-model" not in line
                and re.search(rf"\b{field}\b", line)
            ]
            if not hits:
                continue
            for i in hits:
                window_text = "\n".join(lines[max(0, i - window) : i + 1])
                if _GUARD_RE.search(window_text) or _VALUE_GUARD_RE.search(window_text):
                    continue
                if any(g in window_text for g in guards):
                    continue
                findings.append(
                    {
                        "level": "error",
                        "msg": f"{field} 渲染缺 allow* 开关分支（域外字段不得无条件渲染）",
                        "where": rel,
                    }
                )
                break
    return findings


# 种子公告（sys_notice 正文）判据：只在「名词位置」判分叉，避免把动词用法误杀
# （「如实登记联系结果」「预约面试」不是单据名词）
_SLOT_POSITION_PATTERNS: dict[str, tuple[str, ...]] = {
    "ticket_noun": (
        "提交{0}",
        "我的{0}",
        "{0}单",
        "{0}记录",
        "{0}列表",
        "办理{0}",
        "{0}已开放",
        "{0}通过后",
        "还没有{0}",
    ),
    "category_axis": ("按{0}浏览", "按{0}筛选", "{0}管理", "{0}分类"),
}

_NOTICE_RE = re.compile(
    r"INSERT INTO sys_notice[\s\S]{0,120}?SELECT '((?:[^']|'')*)', '((?:[^']|'')*)'"
)


def seed_notices(sql: str) -> list[tuple[str, str]]:
    """从生成的学生包 SQL 里抽出 (标题, 正文)。"""
    return [(m.group(1), m.group(2)) for m in _NOTICE_RE.finditer(sql or "")]


# 已知待迁移（当前为空）：公告正文若由 f-string/banner 拼出、无法直接改字面量，
# 先把 (域, 簇词) 登记在这里，C2 迁移时删掉即会被门禁要求一致。
SEED_NOTICE_KNOWN_PENDING: frozenset[tuple[str, str]] = frozenset()


def notice_slot_findings(
    sql: str, schema: dict[str, Any], *, domain: str = ""
) -> list[dict[str, str]]:
    """规则②/① 的种子公告版：SQL 公告正文与实体口径分叉、或串了别域招牌词。

    种子公告由 `sql/domain_scene_seed.py` 等手写、随 DDL 插进学生包，
    属可见文案的第四个来源；此前没有门禁盯它。
    """
    lex = schema.get("lex") if isinstance(schema.get("lex"), dict) else {}
    slots = schema_slots(schema)
    findings: list[dict[str, str]] = []
    for title, body in seed_notices(sql):
        text = f"{title} {body}"
        for slot, patterns in _SLOT_POSITION_PATTERNS.items():
            slot_value = str(lex.get(slot) or slots.get(slot) or "").strip()
            if not any(w in slot_value for w in SLOT_CLUSTERS.get(slot, ())):
                continue
            for word in cluster_hits(text, slot):
                if word in slot_value:
                    continue
                if (domain, word) in SEED_NOTICE_KNOWN_PENDING:
                    continue
                hit = next((p.format(word) for p in patterns if p.format(word) in text), "")
                if not hit:
                    continue
                findings.append(
                    {
                        "level": "error",
                        "msg": (
                            f"种子公告「{title}」口径分叉：槽位是「{slot_value}」，"
                            f"正文出现「{hit}」"
                        ),
                        "where": "sql/sys_notice",
                    }
                )
                break
        if domain:
            exempt: set[str] = own_vocabulary(schema)
            exempt.update(str(v) for v in list(slots.values()) + list(lex.values()) if v)
            for word in forbidden_words(domain):
                if word in text and not any(word in tok for tok in exempt):
                    findings.append(
                        {
                            "level": "error",
                            "msg": (
                                f"种子公告「{title}」串了跨域专属名词「{word}」"
                                f"（归属域：{'/'.join(exclusive_owners(word))}）"
                            ),
                            "where": "sql/sys_notice",
                        }
                    )
    return findings


def lexicon_findings(
    schema: dict[str, Any],
    *,
    domain: str = "",
    files: dict[str, Any] | None = None,
    title: str = "",
    seed_sql: str = "",
) -> list[dict[str, str]]:
    """三条规则的统一入口（供交付质量摘要 p3q 直接消费）。

    `seed_sql`：学生包 SQL（含 sys_notice 种子公告）原文，用于第四条判据
    ——公告正文与实体口径分叉 / 串跨域词。
    """
    out: list[dict[str, str]] = []
    out.extend(slot_divergence_findings(schema))
    out.extend(cross_domain_findings(schema, domain, title=title))
    out.extend(render_guard_findings(files or {}))
    if seed_sql:
        out.extend(notice_slot_findings(seed_sql, schema, domain=domain))
    return out


def exclusive_owners(word: str) -> tuple[str, ...]:
    """该招牌词的归属域（空表示通用词，不做跨域判定）。"""
    return _NOUN_OWNERS.get(word) or ()


def forbidden_words(domain: str) -> tuple[str, ...]:
    """本域产物不得出现的「其它域招牌词」（反向下发）。"""
    own = str(domain or "")
    return tuple(sorted(w for w, owners in _NOUN_OWNERS.items() if owners and own not in owners))


def _iter_str(node: Any) -> Iterable[str]:
    if isinstance(node, str):
        yield node
    elif isinstance(node, dict):
        for v in node.values():
            yield from _iter_str(v)
    elif isinstance(node, (list, tuple)):
        for v in node:
            yield from _iter_str(v)


def own_vocabulary(schema: dict[str, Any]) -> set[str]:
    """本域自有实体词（豁免集）：实体/字段/选项/状态/动词/归档类型标签。"""
    ents = schema.get("entities") if isinstance(schema.get("entities"), dict) else {}
    out: set[str] = set()
    for ent in ents.values():
        if not isinstance(ent, dict):
            continue
        for key in ("label", "labelPlural"):
            val = str(ent.get(key) or "").strip()
            if val:
                out.add(val)
        for f in ent.get("fields") or []:
            if not isinstance(f, dict):
                continue
            for key in ("label",):
                val = str(f.get(key) or "").strip()
                if val:
                    out.add(val)
            for opt in f.get("options") or []:
                if isinstance(opt, str) and opt.strip():
                    out.add(opt.strip())
        for opt in ent.get("typeOptions") or []:
            if isinstance(opt, dict) and str(opt.get("label") or "").strip():
                out.add(str(opt["label"]).strip())
    return out


def visible_copy_items(schema: dict[str, Any]) -> list[tuple[str, str]]:
    """页面可见文案（学生/管理端都能看到的话术），(where, text)。"""
    out: list[tuple[str, str]] = []
    labels = schema.get("labels") if isinstance(schema.get("labels"), dict) else {}
    for key, val in labels.items():
        if isinstance(val, str) and val.strip():
            out.append((f"labels.{key}", val))
    menus = schema.get("menus") if isinstance(schema.get("menus"), dict) else {}
    for side, items in menus.items():
        if not isinstance(items, list):
            continue
        for m in items:
            if isinstance(m, dict) and str(m.get("label") or "").strip():
                out.append((f"menus.{side}.{m.get('key')}", str(m["label"])))
    banners = schema.get("portalBanners") if isinstance(schema.get("portalBanners"), list) else []
    for i, b in enumerate(banners):
        if not isinstance(b, dict):
            continue
        text = f"{b.get('title') or ''} {b.get('lead') or ''}".strip()
        if text:
            out.append((f"portalBanners[{i}]", text))
    seeds = schema.get("seeds") if isinstance(schema.get("seeds"), dict) else {}
    for key, val in seeds.items():
        if isinstance(val, str) and val.strip():
            out.append((f"seeds.{key}", val))
    return out


def ticket_shell_items(schema: dict[str, Any]) -> list[tuple[str, str]]:
    """单据壳页面文案（单据名词槽位的可见面）。"""
    out: list[tuple[str, str]] = []
    labels = schema.get("labels") if isinstance(schema.get("labels"), dict) else {}
    for key in _TICKET_SHELL_KEYS:
        val = labels.get(key)
        if isinstance(val, str) and val.strip():
            out.append((f"labels.{key}", val))
    menus = schema.get("menus") if isinstance(schema.get("menus"), dict) else {}
    for side, items in menus.items():
        if not isinstance(items, list):
            continue
        for m in items:
            if isinstance(m, dict) and str(m.get("key") or "") in _TICKET_SHELL_MENUS:
                if str(m.get("label") or "").strip():
                    out.append((f"menus.{side}.{m.get('key')}", str(m["label"])))
    return out


def category_copy_items(schema: dict[str, Any]) -> list[tuple[str, str]]:
    """分类轴槽位的可见面：分类菜单 + 门户 banner + 含簇词的 labels。"""
    out: list[tuple[str, str]] = []
    menus = schema.get("menus") if isinstance(schema.get("menus"), dict) else {}
    for side, items in menus.items():
        if not isinstance(items, list):
            continue
        for m in items:
            if isinstance(m, dict) and str(m.get("key") or "") == "category":
                if str(m.get("label") or "").strip():
                    out.append((f"menus.{side}.category", str(m["label"])))
    banners = schema.get("portalBanners") if isinstance(schema.get("portalBanners"), list) else []
    for i, b in enumerate(banners):
        if not isinstance(b, dict):
            continue
        text = f"{b.get('title') or ''} {b.get('lead') or ''}".strip()
        if text and cluster_hits(text, "category_axis"):
            out.append((f"portalBanners[{i}]", text))
    labels = schema.get("labels") if isinstance(schema.get("labels"), dict) else {}
    for key, val in labels.items():
        # 只审「分类轴」自己的 label（categoryXxx）；勿把等级/类型等其它维度算进来
        if "categor" not in str(key).lower():
            continue
        if isinstance(val, str) and cluster_hits(val, "category_axis"):
            out.append((f"labels.{key}", val))
    return out


def slot_divergence_findings(schema: dict[str, Any]) -> list[dict[str, str]]:
    """规则②：同一 slot 在可见面上不得出现槽位值之外的簇词。

    本域自有实体词（如「安全等级」「客户分级」）不算分叉——它们是同一域的另一种维度。
    """
    slots = schema_slots(schema)
    lex = schema.get("lex") if isinstance(schema.get("lex"), dict) else {}
    own_words = own_vocabulary(schema)
    findings: list[dict[str, str]] = []
    scopes = (
        ("ticket_noun", ticket_shell_items(schema), lex.get("ticket_noun")),
        ("category_axis", category_copy_items(schema), lex.get("category_axis")),
    )
    for slot, items, lex_value in scopes:
        slot_value = str(lex_value or slots.get(slot) or "").strip()
        if not any(w in slot_value for w in SLOT_CLUSTERS.get(slot, ())):
            continue  # 槽位值不含簇词（专有名词）时不做簇内分叉判定
        for where, text in items:
            bad = [
                w
                for w in cluster_hits(text, slot)
                if not _covered(w, slot_value)
                and not any(w in token for token in own_words)
            ]
            if not bad:
                continue
            findings.append(
                {
                    "level": "error",
                    "msg": (
                        f"{slot} 口径分叉：槽位是「{slot_value}」，"
                        f"{where} 出现「{'/'.join(bad)}」"
                    ),
                    "where": where,
                }
            )
    return findings


def cross_domain_findings(
    schema: dict[str, Any], domain: str, *, title: str = ""
) -> list[dict[str, str]]:
    """规则①：其它域招牌词出现在本域页面可见文案。

    豁免：本域自有实体词/槽位值、项目题名（材料用词）、带划界否定的语境。
    """
    own = str(domain or "")
    exempt: set[str] = own_vocabulary(schema)
    for value in list(schema_slots(schema).values()) + list(
        (schema.get("lex") or {}).values() if isinstance(schema.get("lex"), dict) else []
    ):
        token = str(value or "").strip()
        if token:
            exempt.add(token)
    findings: list[dict[str, str]] = []
    for word in forbidden_words(own):
        if word in (title or ""):
            continue
        if any(word in token for token in exempt):
            continue
        for where, text in visible_copy_items(schema):
            idx = text.find(word)
            if idx < 0:
                continue
            window = text[max(0, idx - 12) : idx + len(word) + 12]
            if re.search(r"(≠|不是|非|勿|禁止|易混|不做|不接)", window):
                continue
            findings.append(
                {
                    "level": "error",
                    "msg": (
                        f"跨域专属名词「{word}」出现在 {own or '本域'} 交付文案"
                        f"（归属域：{'/'.join(exclusive_owners(word))}）"
                    ),
                    "where": where,
                }
            )
            break
    return findings
