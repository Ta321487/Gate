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
    r"""StatusChip|<el-tag\b|class=["'][^"']*\bstatus\b|class=["'][^"']*\bchip\b"""
    r"""|class=["'][^"']*\bstage-chip\b""",
    re.I,
)
# 列表/工具条「按钮个数」仍只计 el-button（原生 button 另由绝对定位纪律管，避免把上传/分页钮当操作堆）
_BTN = re.compile(r"""<el-button\b""", re.I)
_FLEX_WRAP = re.compile(
    r"""flex-wrap\s*:\s*wrap|class=["'][^"']*\bflex-wrap\b|class=["'][^"']*\bwrap\b""",
    re.I,
)
_CARD_ARTICLE = re.compile(
    r"""<article\b([^>]*\bclass=["'][^"']*\bcard\b[^"']*["'][^>]*)>([\s\S]*?)</article>""",
    re.I,
)
_SIDE_RAIL_REL = re.compile(
    r"""(?:^|/)components/PortalSideRail\.vue$""",
    re.I,
)
_TABLE_OPS = re.compile(
    r"""class=["'][^"']*\btable-ops\b|class=["'][^"']*\brow-actions\b""",
    re.I,
)
_MORE_BTN = re.compile(r"""更多|more-actions|actions-more""", re.I)
# 主 CTA：el-button type=primary，或原生 button.submit / type=submit（工厂常混用）
_PRIMARY_ABS = re.compile(
    r"""<el-button\b[^>]*\btype=["']primary["'][^>]*\bstyle=["'][^"']*position\s*:\s*absolute"""
    r"""|<el-button\b[^>]*\bstyle=["'][^"']*position\s*:\s*absolute[^"']*["'][^>]*\btype=["']primary["']"""
    r"""|<button\b[^>]*(?:\btype=["']submit["']|\bclass=["'][^"']*\bsubmit\b)[^>]*\bstyle=["'][^"']*position\s*:\s*absolute"""
    r"""|<button\b[^>]*\bstyle=["'][^"']*position\s*:\s*absolute[^"']*["'][^>]*(?:\btype=["']submit["']|\bclass=["'][^"']*\bsubmit\b)""",
    re.I | re.S,
)
_BTN_ABS = re.compile(
    r"""<(?:el-button|button)\b[^>]*\bstyle=["'][^"']*position\s*:\s*absolute""",
    re.I | re.S,
)
# 工厂可点控件：Element 钮 + 原生 button（换头像等）；不扫裸 <a> 以免顶栏绝对定位误杀
_BTN_OPEN = re.compile(r"""<(?:el-button|button)\b([^>]*)/?>""", re.I)
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


def _classes_from_css_body(
    css: str, body_pred
) -> set[str]:
    """选择器最右简单段上、声明满足 body_pred 的 class 名。"""
    out: set[str] = set()
    if not css or not css.strip():
        return out
    cleaned = _CSS_COMMENT.sub("", css)
    for sel, body in _CSS_RULE.findall(cleaned):
        if not body_pred(body):
            continue
        for part in sel.split(","):
            part = part.strip()
            if not part or part.startswith("@"):
                continue
            last = re.split(r"""[\s>+~]+""", part)[-1]
            for cm in re.finditer(r"""\.([A-Za-z_][\w-]*)""", last):
                out.add(cm.group(1))
    return out


def _classes_with_out_of_flow(css: str) -> set[str]:
    """选择器最右简单段上、声明了 position:absolute|fixed 的 class 名。

    只取最右 compound（如 `.card .float-cta` → `float-cta`），避免容器 class 误杀。
    装饰点/轨道等非 el-button 挂载时不会红。
    """
    return _classes_from_css_body(css, lambda body: bool(_POS_OUT.search(body)))


def _classes_with_flex_wrap(css: str) -> set[str]:
    """companion/SFC CSS 里写了 flex-wrap:wrap 的 class（如 ArchiveBrowse `.row`）。

    结构闸必须认 CSS 别名，不能只认模板字面 `flex-wrap`。
    """
    return _classes_from_css_body(
        css, lambda body: bool(re.search(r"""flex-wrap\s*:\s*wrap\b""", body, re.I))
    )


def _attr_class_tokens(attrs: str) -> set[str]:
    names: set[str] = set()
    for m in _CLASS_ATTR.finditer(attrs or ""):
        for tok in m.group(1).split():
            if tok.startswith(":") or "{{" in tok:
                continue
            names.add(tok)
    return names


def _strip_class_subtrees(html: str, class_names: set[str]) -> str:
    """粗剥带指定 class 的一级开标签子树（深度配对），用于看槽外是否还剩按钮。"""
    if not html or not class_names:
        return html
    out = html
    # 多轮：嵌套槽少见，两轮够用
    for _ in range(3):
        changed = False
        for m in list(re.finditer(r"""<([a-zA-Z0-9-]+)([^>]*)>""", out)):
            tag, attrs = m.group(1), m.group(2)
            if tag.lower() in {"script", "style", "template"}:
                continue
            if not (_attr_class_tokens(attrs) & class_names):
                continue
            start = m.start()
            depth = 1
            i = m.end()
            open_re = re.compile(rf"""<{tag}\b""", re.I)
            close_re = re.compile(rf"""</{tag}\s*>""", re.I)
            end = None
            while i < len(out) and depth > 0:
                mo = open_re.search(out, i)
                mc = close_re.search(out, i)
                if mc is None:
                    break
                if mo and mo.start() < mc.start():
                    depth += 1
                    i = mo.end()
                else:
                    depth -= 1
                    if depth == 0:
                        end = mc.end()
                    i = mc.end()
            if end is None:
                continue
            out = out[:start] + out[end:]
            changed = True
            break
        if not changed:
            break
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


def _is_primary_clickable_attrs(attrs: str) -> bool:
    if re.search(r"""type\s*=\s*["']primary["']""", attrs, re.I):
        return True
    if re.search(r"""type\s*=\s*["']submit["']""", attrs, re.I):
        return True
    if re.search(r"""\bclass=["'][^"']*\b(?:submit|el-button--primary)\b""", attrs, re.I):
        return True
    return False


def _btns_with_abs_class(
    template: str, abs_classes: set[str]
) -> list[tuple[str, set[str], bool]]:
    """[(snippet, hit_classes, is_primary), ...] — el-button 与原生 button。"""
    if not abs_classes:
        return []
    hits: list[tuple[str, set[str], bool]] = []
    for m in _BTN_OPEN.finditer(template):
        attrs = m.group(1)
        owned = _btn_class_names(attrs)
        hit = owned & abs_classes
        if not hit:
            continue
        hits.append((m.group(0)[:100], hit, _is_primary_clickable_attrs(attrs)))
    return hits


def _is_wrap_open_attrs(attrs: str, wrap_classes: set[str]) -> bool:
    """模板字面 flex-wrap / wrap+flex，或 class 命中 CSS 别名。"""
    if re.search(r"""flex-wrap\s*:\s*wrap""", attrs, re.I):
        return True
    if re.search(r"""\bflex-wrap\b""", attrs, re.I):
        return True
    if re.search(r"""class=["'][^"']*\bwrap\b""", attrs, re.I) and re.search(
        r"""\bflex\b""", attrs, re.I
    ):
        return True
    if wrap_classes and (_attr_class_tokens(attrs) & wrap_classes):
        return True
    return False


_ACTS_SLOT_CLASSES = frozenset(
    {"card-acts", "table-ops", "row-actions", "toolbar", "edit-moves"}
)


def _find_flex_wrap_regions(
    template: str, wrap_classes: set[str] | None = None
) -> list[tuple[set[str], str]]:
    """粗切：带 flex-wrap（含 CSS class 别名）的开标签 → (开标签 class 集, 内部 HTML)。"""
    wrap_classes = wrap_classes or set()
    regions: list[tuple[set[str], str]] = []
    for m in re.finditer(r"""<([a-zA-Z0-9-]+)([^>]*)>""", template):
        tag, attrs = m.group(1), m.group(2)
        if tag.lower() in {"script", "style", "template"}:
            continue
        if not _is_wrap_open_attrs(attrs, wrap_classes):
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
                    regions.append((_attr_class_tokens(attrs), template[start : mc.start()]))
                i = mc.end()
    return regions


def check_no_status_acts_same_wrap(
    vue_rel: str, template: str, css: str = ""
) -> list[ContractFinding]:
    """状态+按钮同处 wrap 根 → wrap_mess。

    wrap 根 = 模板字面 flex-wrap **或** 同页/companion CSS 上 flex-wrap:wrap 的 class 别名
   （农产货架卡曾用 class=row + ArchiveBrowse.css .row{flex-wrap} 逃过字面扫描）。
    操作槽自身（card-acts 等）允许内部 wrap；状态+按钮同槽缠行才红。
    """
    out: list[ContractFinding] = []
    wrap_classes = _classes_with_flex_wrap(css)
    for i, (classes, region) in enumerate(
        _find_flex_wrap_regions(template, wrap_classes)
    ):
        # 操作槽根上的 wrap（多按钮换行）合法；挤破由 actions_may_wrap_or_menu 管
        if classes & _ACTS_SLOT_CLASSES:
            continue
        if not (_STATUS_MARK.search(region) and _BTN.search(region)):
            continue
        stripped = _strip_class_subtrees(region, set(_ACTS_SLOT_CLASSES))
        if not (_BTN.search(stripped) and _STATUS_MARK.search(stripped)):
            continue
        out.append(
            ContractFinding(
                "no_status_acts_same_wrap",
                "wrap_mess",
                vue_rel,
                "状态标记与操作按钮同处 flex-wrap 根（含 CSS 别名）",
                f"region#{i}",
            )
        )
    return out


def check_list_card_partition(vue_rel: str, template: str) -> list[ContractFinding]:
    """列表卡 article.card：有状态又有操作时，按钮必须落在 card-acts。

    挡「CSS 已写 card-foot/card-acts、模板仍把库存标签和加购揉进 .row」这类 DOM/CSS 脱节。
    状态可在 hd / card-meta；不要求每卡都有 card-meta。
    """
    out: list[ContractFinding] = []
    for i, m in enumerate(_CARD_ARTICLE.finditer(template)):
        region = m.group(2)
        if not (_STATUS_MARK.search(region) and _BTN.search(region)):
            continue
        if not re.search(r"""\bcard-acts\b""", region):
            out.append(
                ContractFinding(
                    "list_card_partition",
                    "wrap_mess",
                    vue_rel,
                    "列表卡同时有状态标记与操作按钮，但缺少 card-acts 操作槽",
                    f"article.card#{i}",
                )
            )
            continue
        leaked = _strip_class_subtrees(
            region, {"card-acts", "table-ops", "row-actions", "toolbar"}
        )
        if _BTN.search(leaked):
            out.append(
                ContractFinding(
                    "list_card_partition",
                    "wrap_mess",
                    vue_rel,
                    "列表卡操作按钮落在 card-acts 外（状态与操作易缠行）",
                    f"article.card#{i}",
                )
            )
    return out


def check_side_rail_align(
    vue_rel: str, template: str, css: str = ""
) -> list[ContractFinding]:
    """市集右侧栏：图标须进固定 mark 槽；编辑行须 grid 两栏（防大空白缝）。"""
    rel = vue_rel.replace("\\", "/")
    if not _SIDE_RAIL_REL.search(rel):
        return []
    out: list[ContractFinding] = []
    if not re.search(r"""class=["'][^"']*\brail-mark\b""", template):
        out.append(
            ContractFinding(
                "side_rail_align",
                "misaligned",
                vue_rel,
                "PortalSideRail 外侧入口缺少 rail-mark 图标槽（图标光心易飘）",
                "rail-mark",
            )
        )
    if not re.search(r"""\bedit-row\b""", template):
        out.append(
            ContractFinding(
                "side_rail_align",
                "gap_chaos",
                vue_rel,
                "PortalSideRail 编辑列表缺少 edit-row",
                "edit-row",
            )
        )
    elif not re.search(
        r"""\.edit-row\b[^{]*\{[^}]*grid-template-columns\s*:""",
        css or "",
        re.I,
    ):
        out.append(
            ContractFinding(
                "side_rail_align",
                "gap_chaos",
                vue_rel,
                "PortalSideRail 编辑行未用 grid-template-columns（易出现勾选区与箭头大空白缝）",
                "edit-row-grid",
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
                "主 CTA（primary/submit）带 position:absolute 漂出文档流",
                m.group(0)[:80],
            )
        )
    abs_cls = _classes_with_out_of_flow(css)
    for snippet, hit, is_primary in _btns_with_abs_class(template, abs_cls):
        if not is_primary:
            continue
        out.append(
            ContractFinding(
                "primary_cta_in_slot",
                "misaligned",
                vue_rel,
                "主 CTA（primary/submit）经 CSS class position:absolute|fixed 漂出文档流",
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
        if _is_primary_clickable_attrs(snippet):
            continue
        out.append(
            ContractFinding(
                "no_orphan_absolute_btn",
                "misaligned",
                vue_rel,
                "业务按钮（el-button/原生 button）inline position:absolute 脱离文档流",
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
                "业务按钮（el-button/原生 button）经 CSS class position:absolute|fixed 脱离文档流",
                f"class={','.join(sorted(hit))} | {snippet[:60]}",
            )
        )
    return out


_SLOT_SELF_SIZED = re.compile(
    r"""align-self\s*:\s*(?:flex-start|start|center)"""
    r"""|height\s*:\s*fit-content"""
    r"""|width\s*:\s*max-content""",
    re.I,
)


def _class_rule_bodies(css: str, class_name: str) -> list[str]:
    """某 class 在 CSS 中各条规则声明体（粗切）。"""
    if not css or not class_name:
        return []
    cleaned = _CSS_COMMENT.sub("", css)
    out: list[str] = []
    for sel, body in _CSS_RULE.findall(cleaned):
        if re.search(rf"""\.{re.escape(class_name)}\b""", sel):
            out.append(body)
    return out


def check_abs_in_stretch_slot(
    vue_rel: str, template: str, css: str = ""
) -> list[ContractFinding]:
    """通用：flex stretch 下，装着「贴边 absolute 可点」的 relative 槽必须自限高。

    反例类：身份栏 stretch 把槽拉高 → absolute 底边钮掉到条底，远离槽内文档流内容
    （换头像只是首发样例，禁止再为每个控件单开模式）。
    """
    css = css or ""
    if not re.search(r"""align-items\s*:\s*stretch\b""", css, re.I):
        return []
    # 贴底 absolute（勿匹配 padding-bottom / border-bottom）
    _ABS_BOTTOM = re.compile(r"""(?<![\w-])bottom\s*:""", re.I)
    abs_edge = _classes_from_css_body(
        css,
        lambda body: bool(_POS_OUT.search(body)) and bool(_ABS_BOTTOM.search(body)),
    )
    if not abs_edge:
        return []
    rel_classes = _classes_from_css_body(
        css, lambda body: bool(re.search(r"""position\s*:\s*relative\b""", body, re.I))
    )
    if not rel_classes:
        return []
    # 轮播台/横幅等故意拉满的媒体槽：有明确高度/inset，不要求 align-self
    _SLOT_MEDIA_FILL = re.compile(
        r"""aspect-ratio\s*:|inset\s*:|min-height\s*:"""
        r"""|height\s*:\s*(?!fit-content|auto)[^;]+"""
        r"""|flex\s*:\s*[1-9]""",
        re.I,
    )

    def _slot_ok(cls: str) -> bool:
        bodies = _class_rule_bodies(css, cls)
        if not bodies:
            return False
        if any(_SLOT_SELF_SIZED.search(b) for b in bodies):
            return True
        if any(_SLOT_MEDIA_FILL.search(b) for b in bodies):
            return True
        return False

    out: list[ContractFinding] = []
    for m in re.finditer(r"""<([a-zA-Z0-9-]+)([^>]*)>""", template):
        tag, attrs = m.group(1), m.group(2)
        if tag.lower() in {"script", "style", "template"}:
            continue
        owned = _attr_class_tokens(attrs)
        slot_hit = owned & rel_classes
        if not slot_hit:
            continue
        start = m.end()
        depth = 1
        i = start
        open_re = re.compile(rf"""<{tag}\b""", re.I)
        close_re = re.compile(rf"""</{tag}\s*>""", re.I)
        end = None
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
                    end = mc.start()
                i = mc.end()
        if end is None:
            continue
        body = template[start:end]
        if not re.search(r"""<(?:el-button|button)\b""", body, re.I):
            continue
        if not any(re.search(rf"""\b{re.escape(c)}\b""", body) for c in abs_edge):
            continue
        unsized = [cls for cls in sorted(slot_hit) if not _slot_ok(cls)]
        if not unsized:
            continue
        out.append(
            ContractFinding(
                "abs_in_stretch_slot",
                "misaligned",
                vue_rel,
                "stretch 布局下 relative 槽内有贴底 absolute 可点控件，但槽未自限高"
                "（align-self/fit-content/max-content）；钮易掉到条底远离文档流内容",
                ",".join(unsized),
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


_CSS_AWARE_CHECKERS = frozenset(
    {
        check_no_status_acts_same_wrap,
        check_primary_cta_in_slot,
        check_no_orphan_absolute_btn,
        check_side_rail_align,
        check_abs_in_stretch_slot,
    }
)

_CHECKERS = (
    check_no_status_acts_same_wrap,
    check_list_card_partition,
    check_side_rail_align,
    check_toolbar_layers,
    check_primary_cta_in_slot,
    check_row_actions_column,
    check_actions_may_wrap_or_menu,
    check_no_orphan_absolute_btn,
    check_dialog_body_scroll,
    check_abs_in_stretch_slot,
)

PATTERN_IDS: tuple[str, ...] = tuple(
    {
        "no_status_acts_same_wrap",
        "list_card_partition",
        "side_rail_align",
        "toolbar_layers",
        "primary_cta_in_slot",
        "row_actions_column",
        "actions_may_wrap_or_menu",
        "no_orphan_absolute_btn",
        "dialog_body_scroll",
        "abs_in_stretch_slot",
    }
)

def load_global_styles_css(src: Path) -> str:
    """工厂全局皮：styles/**/*.css（含 accountFace / themes / chrome）。

    结构闸必须扫到，禁止只认 SFC + companion 而漏 stretch/绝对定位写在全局皮里。
    """
    styles = src / "styles"
    if not styles.is_dir():
        return ""
    chunks: list[str] = []
    for p in sorted(styles.rglob("*.css")):
        if p.is_file():
            chunks.append(p.read_text(encoding="utf-8"))
    return "\n".join(chunks)


def scan_file_contracts(
    vue_rel: str, raw: str, *, extra_css: str = ""
) -> list[ContractFinding]:
    template = _strip_sfc_blocks(raw)
    css = "\n".join(p for p in (_extract_style_css(raw), extra_css) if p)
    findings: list[ContractFinding] = []
    for fn in _CHECKERS:
        if fn in _CSS_AWARE_CHECKERS:
            findings.extend(fn(vue_rel, template, css))
        else:
            findings.extend(fn(vue_rel, template))
    return findings


def scan_layout_contracts(
    root: Path | None = None, *, src: Path | None = None
) -> list[ContractFinding]:
    src = frontend_src(root, src=src)
    global_css = load_global_styles_css(src)
    findings: list[ContractFinding] = []
    for part in ("views", "layouts", "components"):
        for vue_rel in list_vue_rel(src, part):
            vue_path = src / vue_rel
            text = vue_path.read_text(encoding="utf-8") if vue_path.is_file() else ""
            side_css = _companion_css(src, vue_rel)
            extra = "\n".join(p for p in (side_css, global_css) if p)
            findings.extend(scan_file_contracts(vue_rel, text, extra_css=extra))
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
# 2026-10-25：共享管理页结构债已消；空集 = 无登记例外。
BASELINE_KNOWN_CONTRACTS: frozenset[tuple[str, str, str]] = frozenset()


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
