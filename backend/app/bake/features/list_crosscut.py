"""§0 X-LIST：档案列表扫词横切。

XL-01：组合筛选 / 导出列 / 顶栏搜索。
XL-02：回收站视图 / 档案批量删除 / 单据批量通过驳回。
仍留后波：Excel 二进制导入、素材库、一级佣金。

硬约束：禁止 *_thicken / 具名 DOM 专线；学生包禁止工厂腔。
"""

from __future__ import annotations

from typing import Any

from app.bake.proposal_lexicon import keyword_mentioned

_FILTER_TERMS = (
    "高级筛选",
    "组合筛选",
    "多条件筛选",
    "多条件查询",
    "组合查询",
)
_EXPORT_COL_TERMS = (
    "导出字段",
    "导出列",
    "选择导出",
    "勾选导出",
)
_SEARCH_TERMS = (
    "全局搜索",
    "全站搜索",
    "顶栏搜索",
    "站内搜索",
    "顶部搜索",
    "检索功能",
    "书目检索",
    "商品搜索",
    "搜索商品",
    "搜索图书",
)
# 开题不写「回收站」；写软删除 / 逻辑删除 / 删除后恢复。回收站只是按钮文案。
_RECYCLE_TERMS = (
    "软删除",
    "逻辑删除",
    "删除后恢复",
    "删除后可恢复",
    "删除可恢复",
    "误删恢复",
    "回收站",
)
_BATCH_DELETE_TERMS = (
    "批量删除",
    "批量下架",
)
_BATCH_REVIEW_TERMS = (
    "批量通过",
    "批量驳回",
    "批量审核",
)

_LABELS_FILTER = {
    "listFilterStatus": "状态",
    "listFilterStatusAll": "全部状态",
    "listFilterStatusOn": "在用",
    "listFilterStatusOff": "停用",
    "listFilterFrom": "开始日期",
    "listFilterTo": "结束日期",
}
_LABELS_EXPORT = {
    "exportColumnsTitle": "选择导出列",
    "exportColumnsConfirm": "导出",
}
_LABELS_SEARCH = {
    "topSearchPlaceholder": "搜索名称",
}
_LABELS_RECYCLE = {
    "recycleBinLabel": "回收站",
    "recycleBinBack": "返回列表",
    "recycleBinEmpty": "回收站是空的",
}
_LABELS_BATCH_DELETE = {
    "batchDeleteLabel": "批量删除",
}
_LABELS_BATCH_REVIEW = {
    "batchHireLabel": "批量通过",
    "batchRejectLabel": "批量驳回",
}


def _blob(text: str, title: str = "") -> str:
    return f"{title or ''}\n{text or ''}"


def _hit(blob: str, terms: tuple[str, ...]) -> bool:
    return any(keyword_mentioned(blob, kw, ignore_contrast=True) for kw in terms)


def resolve_list_crosscut_flags(text: str, title: str = "") -> dict[str, bool]:
    blob = _blob(text, title)
    return {
        "advancedFilter": _hit(blob, _FILTER_TERMS),
        "exportColumns": _hit(blob, _EXPORT_COL_TERMS),
        "globalSearch": _hit(blob, _SEARCH_TERMS),
        "recycle": _hit(blob, _RECYCLE_TERMS),
        "batchDelete": _hit(blob, _BATCH_DELETE_TERMS),
        "batchReview": _hit(blob, _BATCH_REVIEW_TERMS),
    }


def apply_list_crosscut_to_spec(spec: dict[str, Any], proposal_text: str = "") -> dict[str, Any]:
    """扫词横切；顶栏检索：扫词命中或优先域+archive 时开启，占位跟域/软皮。无新菜单。"""
    from app.bake.shell_face import should_enable_global_search, top_search_placeholder

    title = str(spec.get("title") or "")
    domain = str(spec.get("domain") or "")
    flags = resolve_list_crosscut_flags(proposal_text or "", title)
    caps = list(spec.get("capabilities") or [])
    if not caps:
        sch0 = spec.get("schema") if isinstance(spec.get("schema"), dict) else {}
        caps = list(sch0.get("capabilities") or [])
    flags["globalSearch"] = should_enable_global_search(
        domain, caps, bool(flags.get("globalSearch"))
    )
    schema = dict(spec.get("schema") or {})
    labels = dict(schema.get("labels") or {})

    def apply_block(want: bool, block: dict[str, str]) -> None:
        if want:
            for key, val in block.items():
                labels.setdefault(key, val)
        else:
            for key in block:
                labels.pop(key, None)

    apply_block(flags["advancedFilter"], _LABELS_FILTER)
    apply_block(flags["exportColumns"], _LABELS_EXPORT)
    if flags["globalSearch"]:
        labels["topSearchPlaceholder"] = top_search_placeholder(
            domain, title, proposal_text or ""
        )
    else:
        labels.pop("topSearchPlaceholder", None)
    entities = schema.get("entities") if isinstance(schema.get("entities"), dict) else {}
    entities = dict(entities)
    archive = entities.get("archive") if isinstance(entities.get("archive"), dict) else {}
    archive = dict(archive)
    recycle_ui = bool(flags["recycle"] or archive.get("softDelete"))
    apply_block(recycle_ui, _LABELS_RECYCLE)
    apply_block(flags["batchDelete"], _LABELS_BATCH_DELETE)
    if flags["batchReview"]:
        for key, val in _LABELS_BATCH_REVIEW.items():
            labels.setdefault(key, val)
        ticket = schema.get("ticket") if isinstance(schema.get("ticket"), dict) else {}
        ticket = dict(ticket)
        ticket["allowBatchHire"] = True
        schema["ticket"] = ticket
    schema["labels"] = labels
    schema["listCrosscut"] = dict(flags)
    if flags["recycle"]:
        archive["softDelete"] = True
        entities["archive"] = archive
        schema["entities"] = entities
    return {**spec, "schema": schema}
