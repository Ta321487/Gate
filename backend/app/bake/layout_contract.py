"""起包前 UI 布局闸 · D2 结构契约。

真源：docs/ui-layout-prebake-gate.md §3.2 + §0.0a。
扫 baseline views/layouts/components 源码结构；不跑浏览器、不改学生页。
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from app.bake.layout_inventory import frontend_src, list_vue_rel

# 一排操作硬塞上限（超此数须 flex-wrap / 分区 /「更多」）
_ACTIONS_HARD_CAP = 5

_STATUS_MARK = re.compile(
    r"""StatusChip|<el-tag\b|class=["'][^"']*\bstatus\b|class=["'][^"']*\bchip\b""",
    re.I,
)
_BTN = re.compile(r"""<el-button\b""", re.I)
_FLEX_WRAP = re.compile(
    r"""flex-wrap\s*:\s*wrap|class=["'][^"']*\bflex-wrap\b|class=["'][^"']*\bwrap\b""",
    re.I,
)
_TABLE_OPS = re.compile(
    r"""class=["'][^"']*\btable-ops\b|class=["'][^"']*\brow-actions\b""",
    re.I,
)
_MORE_BTN = re.compile(r"""更多|more-actions|actions-more""", re.I)
_PRIMARY_ABS = re.compile(
    r"""<el-button\b[^>]*\btype=["']primary["'][^>]*\bstyle=["'][^"']*position\s*:\s*absolute"""
    r"""|<el-button\b[^>]*\bstyle=["'][^"']*position\s*:\s*absolute[^"']*["'][^>]*\btype=["']primary["']""",
    re.I | re.S,
)
_BTN_ABS = re.compile(
    r"""<el-button\b[^>]*\bstyle=["'][^"']*position\s*:\s*absolute""",
    re.I | re.S,
)
_BTN_OPEN = re.compile(r"""<el-button\b([^>]*)/?>""", re.I)
_CLASS_ATTR = re.compile(r"""\bclass\s*=\s*["']([^"']*)["']""", re.I)
_STYLE_BLOCK = re.compile(r"""<style\b[^>]*>([\s\S]*?)</style>""", re.I)
_CSS_COMMENT = re.compile(r"""/\*[\s\S]*?\*/""")
_CSS_RULE = re.compile(r"""([^{}@]+)\{([^{}]*)\}""")
_POS_OUT = re.compile(r"""position\s*:\s*(absolute|fixed)\b""", re.I)
_TOOLBAR_OPEN = re.compile(r"""<div\b[^>]*\bclass=["'][^"']*\btoolbar\b[^"']*["'][^>]*>""", re.I)
_SCROLL_HINT = re.compile(
    r"""\b(table-scroll|dialog-scroll|overflow|overflow-y|body-scroll)\b""",
    re.I,
)


@dataclass(frozen=True)
class ContractFinding:
    pattern_id: str
    defect_class: str
    vue: str
    message: str
    detail: str = ""

    def key(self) -> tuple[str, str, str]:
        return (self.pattern_id, self.vue, self.detail)

    def __str__(self) -> str:
        base = f"[{self.pattern_id}/{self.defect_class}] {self.vue}: {self.message}"
        return f"{base} ({self.detail})" if self.detail else base


def _strip_sfc_blocks(text: str) -> str:
    """只留 template 大致范围，去掉 script/style 噪声。"""
    m = re.search(r"""<template\b[^>]*>([\s\S]*)</template>""", text, re.I)
    return m.group(1) if m else text


def _extract_style_css(text: str) -> str:
    """SFC `<style>` 正文。"""
    return "\n".join(m.group(1) for m in _STYLE_BLOCK.finditer(text or ""))


def _companion_css(src: Path, vue_rel: str) -> str:
    """同页 companion `.css`（不含 .vue 内 style；由 _extract_style_css 另取）。"""
    vue_path = src / vue_rel
    stem = vue_path.with_suffix("")
    side = Path(str(stem) + ".css")
    if side.is_file():
        return side.read_text(encoding="utf-8")
    return ""


def _classes_with_out_of_flow(css: str) -> set[str]:
    """选择器最右简单段上、声明了 position:absolute|fixed 的 class 名。

    只取最右 compound（如 `.card .float-cta` → `float-cta`），避免容器 class 误杀。
    装饰点/轨道等非 el-button 挂载时不会红。
    """
    out: set[str] = set()
    if not css or not css.strip():
        return out
    cleaned = _CSS_COMMENT.sub("", css)
    for sel, body in _CSS_RULE.findall(cleaned):
        if not _POS_OUT.search(body):
            continue
        for part in sel.split(","):
            part = part.strip()
            if not part or part.startswith("@"):
                continue
            last = re.split(r"""[\s>+~]+""", part)[-1]
            for cm in re.finditer(r"""\.([A-Za-z_][\w-]*)""", last):
                out.add(cm.group(1))
    return out


def _btn_class_names(attrs: str) -> set[str]:
    names: set[str] = set()
    for m in _CLASS_ATTR.finditer(attrs or ""):
        for tok in m.group(1).split():
            # 跳过 Vue 绑定残留；静态 class 才参与
            if tok.startswith(":") or "{{" in tok:
                continue
            names.add(tok)
    return names


def _btns_with_abs_class(
    template: str, abs_classes: set[str]
) -> list[tuple[str, set[str], bool]]:
    """[(snippet, hit_classes, is_primary), ...]"""
    if not abs_classes:
        return []
    hits: list[tuple[str, set[str], bool]] = []
    for m in _BTN_OPEN.finditer(template):
        attrs = m.group(1)
        owned = _btn_class_names(attrs)
        hit = owned & abs_classes
        if not hit:
            continue
        is_primary = bool(re.search(r"""type\s*=\s*["']primary["']""", attrs, re.I))
        hits.append((m.group(0)[:100], hit, is_primary))
    return hits


def _find_flex_wrap_regions(template: str) -> list[str]:
    """粗切：带 flex-wrap 的开标签起，做简单深度配对，取内部 HTML。"""
    regions: list[str] = []
    for m in re.finditer(r"""<([a-zA-Z0-9-]+)([^>]*)>""", template):
        tag, attrs = m.group(1), m.group(2)
        if tag.lower() in {"script", "style", "template"}:
            continue
        blob = attrs + ("" if "flex-wrap" in attrs else "")
        # class 或 style 含 wrap
        if not (
            re.search(r"""flex-wrap\s*:\s*wrap""", attrs, re.I)
            or re.search(r"""\bflex-wrap\b""", attrs, re.I)
            or (
                re.search(r"""\bclass=["'][^"']*\bwrap\b""", attrs, re.I)
                and "flex" in attrs.lower()
            )
        ):
            # 也认 class="... wrap" 且同标签有 display:flex / d-flex / flex
            if not (
                re.search(r"""class=["'][^"']*\bwrap\b""", attrs, re.I)
                and re.search(r"""\bflex\b""", attrs, re.I)
            ):
                continue
        start = m.end()
        depth = 1
        i = start
        open_re = re.compile(rf"""<{tag}\b""", re.I)
        close_re = re.compile(rf"""</{tag}\s*>""", re.I)
        while i < len(template) and depth > 0:
            mo = open_re.search(template, i)
            mc = close_re.search(template, i)
            if mc is None:
                break
            if mo and mo.start() < mc.start():
                depth += 1
                i = mo.end()
            else:
                depth -= 1
                if depth == 0:
                    regions.append(template[start : mc.start()])
                i = mc.end()
        _ = blob  # keep linter calm
    return regions


def check_no_status_acts_same_wrap(vue_rel: str, template: str) -> list[ContractFinding]:
    out: list[ContractFinding] = []
    for i, region in enumerate(_find_flex_wrap_regions(template)):
        if _STATUS_MARK.search(region) and _BTN.search(region):
            # 区内若已有 table-ops 单独包按钮、状态在外——仍可能同 wrap 根；本模式禁同根
            out.append(
                ContractFinding(
                    "no_status_acts_same_wrap",
                    "wrap_mess",
                    vue_rel,
                    "状态标记与操作按钮同处 flex-wrap 根",
                    f"region#{i}",
                )
            )
    return out


def check_toolbar_layers(vue_rel: str, template: str) -> list[ContractFinding]:
    """toolbar 根闭合后仅空白就开下一个 toolbar → 无间隔堆叠（深度配对；detail=after#序）。"""
    out: list[ContractFinding] = []
    for idx, m in enumerate(_TOOLBAR_OPEN.finditer(template)):
        start = m.end()
        depth = 1
        i = start
        while i < len(template) and depth:
            mo = re.search(r"""<div\b""", template[i:], re.I)
            mc = re.search(r"""</div\s*>""", template[i:], re.I)
            if not mc:
                break
            open_at = mo.start() if mo else None
            close_at = mc.start()
            if open_at is not None and open_at < close_at:
                depth += 1
                i += mo.end()
            else:
                depth -= 1
                i += mc.end()
                if depth == 0:
                    rest = template[i : i + 160]
                    nxt = re.match(
                        r"""\s*<div\b([^>]*\bclass=["'][^"']*\btoolbar\b[^"']*["'][^>]*)>""",
                        rest,
                        re.I,
                    )
                    if nxt:
                        out.append(
                            ContractFinding(
                                "toolbar_layers",
                                "gap_chaos",
                                vue_rel,
                                "多段 toolbar 无间隔紧挨堆叠",
                                f"after#{idx}",
                            )
                        )
                    break
    return out


def check_primary_cta_in_slot(
    vue_rel: str, template: str, css: str = ""
) -> list[ContractFinding]:
    out: list[ContractFinding] = []
    for m in _PRIMARY_ABS.finditer(template):
        out.append(
            ContractFinding(
                "primary_cta_in_slot",
                "misaligned",
                vue_rel,
                "主 CTA（type=primary）带 position:absolute 漂出文档流",
                m.group(0)[:80],
            )
        )
    abs_cls = _classes_with_out_of_flow(css)
    for snippet, hit, is_primary in _btns_with_abs_class(template, abs_cls):
        if not is_primary:
            continue
        # inline 已报过的同钮跳过（detail 不同也无妨；按 snippet 粗去重）
        out.append(
            ContractFinding(
                "primary_cta_in_slot",
                "misaligned",
                vue_rel,
                "主 CTA（type=primary）经 CSS class position:absolute|fixed 漂出文档流",
                f"class={','.join(sorted(hit))} | {snippet[:60]}",
            )
        )
    return out


def check_row_actions_column(vue_rel: str, template: str) -> list[ContractFinding]:
    """表格列槽内状态+按钮未进独立 actions 槽（无 table-ops/row-actions）。"""
    out: list[ContractFinding] = []
    for m in re.finditer(
        r"""<el-table-column\b([^>]*)>([\s\S]*?)</el-table-column>""",
        template,
        re.I,
    ):
        attrs, body = m.group(1), m.group(2)
        # 自闭合 <el-table-column ... /> 的 attrs 以 / 结尾；禁止把后续列吞进 body
        if attrs.rstrip().endswith("/"):
            continue
        if not (_STATUS_MARK.search(body) and _BTN.search(body)):
            continue
        if _TABLE_OPS.search(body):
            continue
        out.append(
            ContractFinding(
                "row_actions_column",
                "overlap",
                vue_rel,
                "表格列内状态与操作同槽且无 table-ops/row-actions 分区",
                (attrs[:60] or "column").strip(),
            )
        )
    return out


def check_actions_may_wrap_or_menu(vue_rel: str, template: str) -> list[ContractFinding]:
    out: list[ContractFinding] = []
    for m in re.finditer(
        r"""<div\b([^>]*\b(?:table-ops|row-actions)\b[^>]*)>([\s\S]*?)</div>""",
        template,
        re.I,
    ):
        attrs, body = m.group(1), m.group(2)
        n = len(_BTN.findall(body))
        if n < _ACTIONS_HARD_CAP:
            continue
        if _FLEX_WRAP.search(attrs) or _FLEX_WRAP.search(body[:200]):
            continue
        if _MORE_BTN.search(body):
            continue
        out.append(
            ContractFinding(
                "actions_may_wrap_or_menu",
                "crushed",
                vue_rel,
                f"操作区 {n} 个按钮单行硬塞（≥{_ACTIONS_HARD_CAP} 须 wrap/更多）",
                f"n={n}",
            )
        )
    return out


def check_no_orphan_absolute_btn(
    vue_rel: str, template: str, css: str = ""
) -> list[ContractFinding]:
    out: list[ContractFinding] = []
    for m in _BTN_ABS.finditer(template):
        # primary 已由 primary_cta_in_slot 报，这里报其余业务钮
        snippet = m.group(0)
        if re.search(r"""type=["']primary["']""", snippet, re.I):
            continue
        out.append(
            ContractFinding(
                "no_orphan_absolute_btn",
                "misaligned",
                vue_rel,
                "业务按钮 inline position:absolute 脱离文档流",
                snippet[:80],
            )
        )
    abs_cls = _classes_with_out_of_flow(css)
    for snippet, hit, is_primary in _btns_with_abs_class(template, abs_cls):
        if is_primary:
            continue
        out.append(
            ContractFinding(
                "no_orphan_absolute_btn",
                "misaligned",
                vue_rel,
                "业务按钮经 CSS class position:absolute|fixed 脱离文档流",
                f"class={','.join(sorted(hit))} | {snippet[:60]}",
            )
        )
    return out


def check_dialog_body_scroll(vue_rel: str, template: str) -> list[ContractFinding]:
    """对话框内直接塞 el-table 且无滚动容器暗示 → overflow 风险。"""
    out: list[ContractFinding] = []
    for m in re.finditer(
        r"""<(el-dialog|el-drawer)\b([^>]*)>([\s\S]*?)</\1>""",
        template,
        re.I,
    ):
        tag, attrs, body = m.group(1), m.group(2), m.group(3)
        if not re.search(r"""<el-table\b""", body, re.I):
            continue
        if _SCROLL_HINT.search(body) or _SCROLL_HINT.search(attrs):
            continue
        vm = re.search(r"""v-model=["']([^"']+)["']""", attrs)
        out.append(
            ContractFinding(
                "dialog_body_scroll",
                "overflow",
                vue_rel,
                f"{tag} 内含表格但无滚动容器 class（table-scroll/overflow 等）",
                vm.group(1) if vm else tag.lower(),
            )
        )
    return out


_CHECKERS = (
    check_no_status_acts_same_wrap,
    check_toolbar_layers,
    check_primary_cta_in_slot,
    check_row_actions_column,
    check_actions_may_wrap_or_menu,
    check_no_orphan_absolute_btn,
    check_dialog_body_scroll,
)

PATTERN_IDS: tuple[str, ...] = tuple(
    {
        "no_status_acts_same_wrap",
        "toolbar_layers",
        "primary_cta_in_slot",
        "row_actions_column",
        "actions_may_wrap_or_menu",
        "no_orphan_absolute_btn",
        "dialog_body_scroll",
    }
)


def scan_file_contracts(
    vue_rel: str, raw: str, *, extra_css: str = ""
) -> list[ContractFinding]:
    template = _strip_sfc_blocks(raw)
    css = "\n".join(p for p in (_extract_style_css(raw), extra_css) if p)
    findings: list[ContractFinding] = []
    for fn in _CHECKERS:
        if fn in (check_primary_cta_in_slot, check_no_orphan_absolute_btn):
            findings.extend(fn(vue_rel, template, css))
        else:
            findings.extend(fn(vue_rel, template))
    return findings


def scan_layout_contracts(
    root: Path | None = None, *, src: Path | None = None
) -> list[ContractFinding]:
    src = frontend_src(root, src=src)
    findings: list[ContractFinding] = []
    for part in ("views", "layouts", "components"):
        for vue_rel in list_vue_rel(src, part):
            vue_path = src / vue_rel
            text = vue_path.read_text(encoding="utf-8") if vue_path.is_file() else ""
            side_css = _companion_css(src, vue_rel)
            findings.extend(scan_file_contracts(vue_rel, text, extra_css=side_css))
    # 稳定去重
    seen: set[tuple[str, str, str]] = set()
    out: list[ContractFinding] = []
    for f in findings:
        k = f.key()
        if k in seen:
            continue
        seen.add(k)
        out.append(f)
    return findings


# 基线真阳性记账（不改页消红）。工厂摘要与 D2 测共用。(pattern_id, vue, detail)
BASELINE_KNOWN_CONTRACTS: frozenset[tuple[str, str, str]] = frozenset(
    {
        ("actions_may_wrap_or_menu", "views/admin/ArchiveAdmin.vue", "n=9"),
        ("dialog_body_scroll", "views/admin/ArchiveAdmin.vue", "snackVisible"),
        ("dialog_body_scroll", "views/admin/GradeScoresAdmin.vue", "historyOpen"),
        ("actions_may_wrap_or_menu", "views/admin/OrdersAdmin.vue", "n=19"),
        ("toolbar_layers", "views/admin/OverdueAdmin.vue", "after#0"),
        ("actions_may_wrap_or_menu", "views/admin/ReservationsAdmin.vue", "n=20"),
        ("actions_may_wrap_or_menu", "views/admin/TicketRecordsAdmin.vue", "n=14"),
        ("toolbar_layers", "views/admin/TicketsAdmin.vue", "after#1"),
        ("toolbar_layers", "views/admin/TicketsAdmin.vue", "after#2"),
        ("actions_may_wrap_or_menu", "views/admin/TicketsAdmin.vue", "n=7"),
        ("dialog_body_scroll", "views/admin/TicketsAdmin.vue", "evalCollege.visible"),
        ("actions_may_wrap_or_menu", "views/admin/UsersAdmin.vue", "n=9"),
    }
)


def assert_layout_contracts_ok(
    *,
    known: set[tuple[str, str, str]] | frozenset[tuple[str, str, str]] | None = None,
    root: Path | None = None,
    src: Path | None = None,
) -> list[ContractFinding]:
    """非 known 的 finding → 断言失败。known 项为 (pattern_id, vue, detail)。"""
    findings = scan_layout_contracts(root, src=src)
    allow = known if known is not None else BASELINE_KNOWN_CONTRACTS
    unexpected = [f for f in findings if f.key() not in allow]
    if unexpected:
        preview = "\n".join(str(f) for f in unexpected[:40])
        more = f"\n... (+{len(unexpected) - 40})" if len(unexpected) > 40 else ""
        raise AssertionError(
            f"布局结构契约红灯 {len(unexpected)} 条:\n{preview}{more}"
        )
    return findings
