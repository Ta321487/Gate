"""学生包可交互控件闸 · C1/C2/C3 契约。

真源：docs/form-controls.md
- C1 §2：下拉禁 allow-create
- C2 §1.1：日期/时刻/数字禁 el-input 手填
- C3 §1：档案字段循环须走 ArchiveFieldControl（映射见 form_controls_widget）

扫 baseline views/layouts/components 源码；不跑浏览器、本刀不改学生页消红。
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from app.bake.layout_inventory import frontend_src, list_vue_rel

PATTERN_IDS: tuple[str, ...] = (
    "no_select_allow_create",
    "no_input_handfill_temporal",
    "no_input_handfill_numeric",
    "archive_field_loop_uses_control",
)

_ALLOW_CREATE = re.compile(r"""\ballow-create\b|\ballowCreate\b""", re.I)
_V_MODEL = re.compile(
    r"""\bv-model(?:\s*:\s*[\w-]+)?\s*=\s*["']([^"']+)["']""",
    re.I,
)
_MODEL_VALUE = re.compile(
    r"""(?::model-value|v-model(?:\s*:\s*[\w-]+)?)\s*=\s*["']([^"']+)["']""",
    re.I,
)
_EL_SELECT_OPEN = re.compile(r"""<el-select\b""", re.I)
# el-input，排除 el-input-number
_EL_INPUT_OPEN = re.compile(r"""<el-input(?!-number)\b""", re.I)
_TYPE_ATTR = re.compile(r"""\btype\s*=\s*["']([^"']+)["']""", re.I)
_PLACEHOLDER = re.compile(r"""placeholder\s*=\s*["']([^"']*)["']""", re.I)
_FORM_ITEM = re.compile(
    r"""<el-form-item\b([^>]*)>([\s\S]*?)</el-form-item>""",
    re.I,
)
_LABEL_ATTR = re.compile(r"""\blabel\s*=\s*["']([^"']+)["']""", re.I)

# 禁 On$：会误杀 reason / location / Question
_DATE_LEAF = re.compile(
    r"(At|Date|Time|Day)$|^(expireAt|deadline|dayKey|onDate|visitOn|workDate|"
    r"stayFrom|stayTo|dateFrom|dateTo|paidAt|dealAt|openAt|closeAt|returnDate)$",
)
_NUM_LEAF = re.compile(
    r"(Yuan|Qty|Stock|Hours|Km|Fee|Score|Rate|Amount|Price|Minutes|Days|Attempts)$"
    r"|^(qty|stock|hours|amount|price|fee|rate|score)$",
)
_PH_DATE = re.compile(r"yyyy|YYYY|HH:mm|日期|时刻", re.I)
_LABEL_DATE = re.compile(r"日期|时间|过期|截止|时刻|时段")
_LABEL_NUM = re.compile(r"金额|数量|库存|单价|总价|押金|费率|分数|学时|里程")
_HAS_TEMPORAL_WIDGET = re.compile(
    r"""<el-date-picker\b|<el-time-picker\b""",
    re.I,
)
_HAS_NUM_WIDGET = re.compile(r"""<el-input-number\b""", re.I)

# 档案 schema 字段循环（不含资料页 basicFields/bizFields/visibleFields）
_ARCHIVE_FIELD_LOOP = re.compile(
    r"""v-for\s*=\s*["']f\s+in\s+(logFields|extraFields)["']""",
    re.I,
)
_ARCHIVE_CONTROL = re.compile(r"""<ArchiveFieldControl\b""", re.I)
_PLAIN_INPUT = re.compile(r"""<el-input(?!-number)\b""", re.I)


@dataclass(frozen=True)
class ControlFinding:
    pattern_id: str
    vue: str
    message: str
    detail: str = ""

    def key(self) -> tuple[str, str, str]:
        return (self.pattern_id, self.vue, self.detail)

    def __str__(self) -> str:
        base = f"[{self.pattern_id}] {self.vue}: {self.message}"
        return f"{base} ({self.detail})" if self.detail else base


def _strip_template(text: str) -> str:
    m = re.search(r"""<template\b[^>]*>([\s\S]*)</template>""", text, re.I)
    return m.group(1) if m else text


def _select_attr_span(template: str, allow_pos: int) -> tuple[int, int] | None:
    before = template[:allow_pos]
    last_open = -1
    for m in _EL_SELECT_OPEN.finditer(before):
        last_open = m.start()
    if last_open < 0:
        return None
    gt = template.find(">", last_open)
    if gt < 0 or gt < allow_pos:
        return None
    return last_open, gt + 1


def _input_open_attrs(template: str, start: int) -> str | None:
    gt = template.find(">", start)
    if gt < 0:
        return None
    return template[start : gt + 1]


def _leaf_from_bind(bind: str) -> str:
    leaf = bind.split(".")[-1].strip()
    leaf = re.sub(r"[^\w].*$", "", leaf)
    return leaf


def _skip_input_attrs(attrs: str) -> bool:
    if re.search(r"""\btype\s*=\s*["']textarea["']""", attrs, re.I):
        return True
    if re.search(r"""\btype\s*=\s*["']password["']""", attrs, re.I):
        return True
    if re.search(r"\bdisabled\b", attrs, re.I):
        return True
    return False


def _scan_allow_create(rel: str, tpl: str) -> list[ControlFinding]:
    out: list[ControlFinding] = []
    seen: set[str] = set()
    for m in _ALLOW_CREATE.finditer(tpl):
        span = _select_attr_span(tpl, m.start())
        if span is None:
            continue
        attrs = tpl[span[0] : span[1]]
        vm = _V_MODEL.search(attrs)
        detail = vm.group(1).strip() if vm else "allow-create"
        if detail in seen:
            continue
        seen.add(detail)
        out.append(
            ControlFinding(
                pattern_id="no_select_allow_create",
                vue=rel,
                message="下拉禁止 allow-create / 手填造值",
                detail=detail,
            )
        )
    return out


def _classify_input_handfill(attrs: str) -> tuple[str, str] | None:
    """返回 (pattern_id, detail) 或 None。"""
    if _skip_input_attrs(attrs):
        return None
    tm = _TYPE_ATTR.search(attrs)
    typ = (tm.group(1) if tm else "").lower()
    vm = _MODEL_VALUE.search(attrs)
    bind = vm.group(1).strip() if vm else ""
    leaf = _leaf_from_bind(bind) if bind else ""
    phm = _PLACEHOLDER.search(attrs)
    placeholder = phm.group(1) if phm else ""

    if typ in ("date", "time", "datetime-local"):
        return ("no_input_handfill_temporal", bind or f"type={typ}")
    if typ == "number":
        return ("no_input_handfill_numeric", bind or "type=number")
    if leaf and _DATE_LEAF.search(leaf):
        return ("no_input_handfill_temporal", bind)
    if leaf and _NUM_LEAF.search(leaf):
        return ("no_input_handfill_numeric", bind)
    if _PH_DATE.search(placeholder):
        return ("no_input_handfill_temporal", bind or f"ph:{placeholder[:40]}")
    return None


def _scan_input_binds(rel: str, tpl: str) -> list[ControlFinding]:
    out: list[ControlFinding] = []
    seen: set[tuple[str, str]] = set()
    for m in _EL_INPUT_OPEN.finditer(tpl):
        attrs = _input_open_attrs(tpl, m.start())
        if not attrs:
            continue
        hit = _classify_input_handfill(attrs)
        if not hit:
            continue
        pid, detail = hit
        key = (pid, detail)
        if key in seen:
            continue
        seen.add(key)
        msg = (
            "日期/时刻禁止用文本框手填"
            if pid == "no_input_handfill_temporal"
            else "数量/金额等禁止用文本框手填"
        )
        out.append(ControlFinding(pattern_id=pid, vue=rel, message=msg, detail=detail))
    return out


def _scan_form_item_labels(rel: str, tpl: str) -> list[ControlFinding]:
    """标签写日期/金额，体内却是裸 el-input（无对应选择器）。"""
    out: list[ControlFinding] = []
    seen: set[tuple[str, str]] = set()
    for im in _FORM_ITEM.finditer(tpl):
        attrs, body = im.group(1), im.group(2)
        lm = _LABEL_ATTR.search(attrs)
        if not lm:
            continue
        label = lm.group(1).strip()
        # 体内已有正确控件 → 放过（含只读展示旁的 date-picker 分支）
        has_input = bool(_EL_INPUT_OPEN.search(body))
        if not has_input:
            continue
        # 若该 item 内所有 el-input 都 disabled，放过（只读展示）
        any_editable = False
        for om in _EL_INPUT_OPEN.finditer(body):
            ia = _input_open_attrs(body, om.start())
            if ia and not _skip_input_attrs(ia):
                any_editable = True
                break
        if not any_editable:
            continue

        if _LABEL_DATE.search(label) and not _HAS_TEMPORAL_WIDGET.search(body):
            pid, detail = "no_input_handfill_temporal", f"label:{label}"
        elif _LABEL_NUM.search(label) and not _HAS_NUM_WIDGET.search(body):
            pid, detail = "no_input_handfill_numeric", f"label:{label}"
        else:
            continue
        key = (pid, detail)
        if key in seen:
            continue
        seen.add(key)
        # 若同 item 内已有 v-model 级 finding，detail 用 bind 更稳；这里补标签面
        msg = (
            "日期/时刻标签旁禁止文本框手填"
            if pid == "no_input_handfill_temporal"
            else "数量/金额标签旁禁止文本框手填"
        )
        out.append(ControlFinding(pattern_id=pid, vue=rel, message=msg, detail=detail))
    return out


def _scan_archive_field_loops(rel: str, tpl: str) -> list[ControlFinding]:
    """logFields / extraFields 循环须挂 ArchiveFieldControl，禁止一律 el-input。"""
    out: list[ControlFinding] = []
    seen: set[str] = set()
    for m in _ARCHIVE_FIELD_LOOP.finditer(tpl):
        name = m.group(1)
        if name in seen:
            continue
        # 窗口盖住 el-form-item 体；过短会漏，过长易跨到下一表单项
        window = tpl[m.start() : m.start() + 1800]
        if _ARCHIVE_CONTROL.search(window):
            continue
        if not _PLAIN_INPUT.search(window):
            continue
        seen.add(name)
        out.append(
            ControlFinding(
                pattern_id="archive_field_loop_uses_control",
                vue=rel,
                message="档案字段循环须用 ArchiveFieldControl，禁止一律文本框",
                detail=name,
            )
        )
    return out


def scan_file_controls(rel: str, text: str) -> list[ControlFinding]:
    """扫单文件 template；rel 用正斜杠相对 frontend/src。"""
    rel = rel.replace("\\", "/")
    tpl = _strip_template(text or "")
    findings = (
        _scan_allow_create(rel, tpl)
        + _scan_input_binds(rel, tpl)
        + _scan_form_item_labels(rel, tpl)
        + _scan_archive_field_loops(rel, tpl)
    )
    seen: set[tuple[str, str, str]] = set()
    out: list[ControlFinding] = []
    for f in findings:
        k = f.key()
        if k in seen:
            continue
        seen.add(k)
        out.append(f)
    return out


def scan_form_controls(
    root: Path | None = None,
    *,
    src: Path | None = None,
) -> list[ControlFinding]:
    fe = frontend_src(root, src=src)
    rels: list[str] = []
    for part in ("views", "layouts", "components"):
        rels.extend(list_vue_rel(fe, part))
    findings: list[ControlFinding] = []
    for rel in rels:
        path = fe / rel
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        findings.extend(scan_file_controls(rel.replace("\\", "/"), text))
    seen: set[tuple[str, str, str]] = set()
    out: list[ControlFinding] = []
    for f in findings:
        k = f.key()
        if k in seen:
            continue
        seen.add(k)
        out.append(f)
    return out


# 基线真阳性记账（不改页消红）。(pattern_id, vue, detail)
BASELINE_KNOWN_CONTROLS: frozenset[tuple[str, str, str]] = frozenset(
    {
        # C1 allow-create
        ("no_select_allow_create", "views/user/Addresses.vue", "form.tag"),
        ("no_select_allow_create", "views/admin/FundDisburseAdmin.vue", "form.ticketId"),
        ("no_select_allow_create", "views/admin/FundPublicityAdmin.vue", "form.ticketId"),
        ("no_select_allow_create", "views/admin/ListingDealAdmin.vue", "form.ticketId"),
        ("no_select_allow_create", "views/admin/TicketsAdmin.vue", "audit.skillFilter"),
        ("no_select_allow_create", "views/admin/TicketsAdmin.vue", "reassign.skillFilter"),
        ("no_select_allow_create", "views/admin/ArchiveAdmin.vue", "form.startCampus"),
        ("no_select_allow_create", "views/admin/ArchiveAdmin.vue", "form.endCampus"),
        ("no_select_allow_create", "views/admin/StaffRosterAdmin.vue", "form.username"),
        ("no_select_allow_create", "components/RepairFinishDialog.vue", "form.faultReason"),
        ("no_select_allow_create", "views/user/Cart.vue", "form.tag"),
        ("no_select_allow_create", "views/user/Cart.vue", "form.couponCode"),
        ("no_select_allow_create", "views/user/ArchiveBrowse.vue", "collegeFilter"),
        ("no_select_allow_create", "views/user/MyTickets.vue", "returnDlg.faultReason"),
        ("no_select_allow_create", "views/user/MyTickets.vue", "form.remark"),
        ("no_select_allow_create", "views/user/MyTickets.vue", "form.location"),
        ("no_select_allow_create", "views/user/SlotBook.vue", "extra.patientName"),
        ("no_select_allow_create", "views/user/SlotBook.vue", "extra.preferredStylist"),
        # C2 手填：优惠券过期（v-model + 标签各一条）
        ("no_input_handfill_temporal", "views/admin/CouponsAdmin.vue", "form.expireAt"),
        ("no_input_handfill_temporal", "views/admin/CouponsAdmin.vue", "label:过期时间"),
        # C3：日志字段循环一律文本框，未走 ArchiveFieldControl
        (
            "archive_field_loop_uses_control",
            "views/user/ArchiveBrowse.vue",
            "logFields",
        ),
    }
)


def assert_form_controls_ok(
    *,
    known: set[tuple[str, str, str]] | frozenset[tuple[str, str, str]] | None = None,
    root: Path | None = None,
    src: Path | None = None,
) -> list[ControlFinding]:
    """非 known 的 finding → 断言失败。"""
    findings = scan_form_controls(root, src=src)
    allow = known if known is not None else BASELINE_KNOWN_CONTROLS
    unexpected = [f for f in findings if f.key() not in allow]
    if unexpected:
        preview = "\n".join(str(f) for f in unexpected[:40])
        more = f"\n... (+{len(unexpected) - 40})" if len(unexpected) > 40 else ""
        raise AssertionError(
            f"控件契约红灯 {len(unexpected)} 条:\n{preview}{more}"
        )
    return findings
