"""工厂字段控件语义台：标签/键启发式 → widget。

真源：factory_widget_hint。种子仅 asset_seeds/widget_hints.json。
类型直映仍在 form_controls_widget；本台只维护可扩的标签启发式。

工厂台可保留 match_scope / 正则；bake 经 project_student_rules 投影为
学生包 fieldWidgetRules.js（关键词表，无厂词汇）。门禁：台匹配 + 投影等价。
"""

from __future__ import annotations

import json
import re
import threading
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

SOURCES = frozenset({"migrated", "scan", "manual"})
BAKE_SOURCES = frozenset({"migrated", "scan", "manual"})
MATCH_SCOPES = frozenset({"label_exact", "label_contains", "label_regex", "key"})
# 空串 = 不限类型；与档案字段 type 对齐的有限集
WHEN_TYPES = frozenset({"", "string", "number"})
WHEN_TYPE_LABELS_ZH = {
    "string": "字符串",
    "number": "数字",
}
MATCH_SCOPE_LABELS_ZH = {
    "label_exact": "标签精确",
    "label_contains": "标签包含",
    "label_regex": "标签正则",
    "key": "字段键",
}
WIDGET_KINDS = frozenset(
    {
        "switch",
        "select",
        "datetime",
        "date",
        "time",
        "number",
        "money",
        "url",
        "textarea",
        "richtext",
        "text",
        "hidden",
    }
)
WIDGET_LABELS_ZH = {
    "text": "单行文本",
    "textarea": "多行文本",
    "richtext": "富文本",
    "number": "数字",
    "money": "金额",
    "switch": "开关",
    "select": "下拉选择",
    "date": "日期",
    "datetime": "日期时间",
    "time": "时刻",
    "url": "链接",
    "hidden": "隐藏",
}

_lock = threading.RLock()
_rows_cache: list[dict[str, Any]] | None = None


def _norm(s: str | None) -> str:
    return (s or "").strip()


def row_to_dict(row: Any) -> dict[str, Any]:
    return {
        "id": int(row.id),
        "rule_key": _norm(row.rule_key),
        "match_scope": _norm(row.match_scope) or "label_contains",
        "match_pattern": str(row.match_pattern or ""),
        "when_type": _norm(row.when_type),
        "widget": _norm(row.widget) or "text",
        "note_zh": _norm(row.note_zh),
        "sort": int(row.sort or 0),
        "enabled": bool(row.enabled),
        "source": str(row.source or "manual"),
        "updated_at": row.updated_at.isoformat() if getattr(row, "updated_at", None) else None,
    }


def invalidate_cache() -> None:
    global _rows_cache
    with _lock:
        _rows_cache = None


def _seed_payload() -> list[dict[str, Any]]:
    from app.services.asset_seeds import load_seed_json

    return list(load_seed_json("widget_hints"))


def bootstrap_from_seed() -> None:
    rows = _seed_payload()
    with _lock:
        global _rows_cache
        _rows_cache = rows


async def load_all_rows(db: AsyncSession) -> list[dict[str, Any]]:
    global _rows_cache
    from app.models import FactoryWidgetHint

    result = await db.execute(
        select(FactoryWidgetHint).order_by(FactoryWidgetHint.sort, FactoryWidgetHint.id)
    )
    rows = [row_to_dict(r) for r in result.scalars().all()]
    with _lock:
        _rows_cache = rows
    return list(rows)


async def migrate_seed_if_empty(db: AsyncSession) -> dict[str, int]:
    from app.models import FactoryWidgetHint

    key_rows = await db.execute(select(FactoryWidgetHint.rule_key))
    have = {_norm(a) for (a,) in key_rows.all()}
    inserted = 0
    for item in _seed_payload():
        rk = _norm(item.get("rule_key"))
        if not rk or rk in have:
            continue
        db.add(
            FactoryWidgetHint(
                rule_key=rk,
                match_scope=_norm(item.get("match_scope")) or "label_contains",
                match_pattern=str(item.get("match_pattern") or ""),
                when_type=_norm(item.get("when_type")),
                widget=_norm(item.get("widget")) or "text",
                note_zh=_norm(item.get("note_zh")),
                sort=int(item.get("sort") or 0),
                enabled=bool(item.get("enabled", True)),
                source=_norm(item.get("source")) or "migrated",
            )
        )
        inserted += 1
        have.add(rk)
    if inserted:
        await db.commit()
    invalidate_cache()
    rows = await load_all_rows(db)
    return {"inserted": inserted, "total": len(rows)}


def _rows_or_seed(rows: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    data = rows
    if data is None:
        with _lock:
            data = list(_rows_cache) if _rows_cache is not None else None
    if not data:
        return _seed_payload()
    return list(data)


def export_hints(*, rows: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    """工厂形精简规则表（门禁 / 匹配真源；不直接进学生 ZIP）。"""
    out: list[dict[str, Any]] = []
    for r in sorted(_rows_or_seed(rows), key=lambda x: int(x.get("sort") or 0)):
        if _norm(r.get("source")) not in BAKE_SOURCES:
            continue
        if not bool(r.get("enabled", True)):
            continue
        pat = str(r.get("match_pattern") or "").strip()
        widget = _norm(r.get("widget"))
        scope = _norm(r.get("match_scope")) or "label_contains"
        if not pat or widget not in WIDGET_KINDS or scope not in MATCH_SCOPES:
            continue
        out.append(
            {
                "match_scope": scope,
                "match_pattern": pat,
                "when_type": _norm(r.get("when_type")),
                "widget": widget,
                "sort": int(r.get("sort") or 0),
            }
        )
    return out


_REGEX_META = re.compile(r"[.\\^$*+?{}\[\]()]")


def _split_plain_alts(pat: str) -> list[str] | None:
    """仅 lit|lit|…（无其它正则元字符）→ 词表；否则 None。"""
    parts = [p for p in str(pat or "").split("|")]
    if not parts:
        return None
    out: list[str] = []
    for p in parts:
        if _REGEX_META.search(p):
            return None
        t = p.strip()
        if t:
            out.append(t)
    return out or None


def _simplify_regex_branch(branch: str) -> str | None:
    """把常见可选括号 / \\s* 剥掉，收成学生可读关键词。"""
    s = str(branch or "")
    s = re.sub(r"\\s\*", "", s)
    s = re.sub(r"\\s", "", s)
    s = re.sub(r"\[（\(]\?", "", s)
    s = re.sub(r"\[）\)]\?", "", s)
    s = re.sub(r"[.\\^$*+?\\\[\]()（）]", "", s)
    s = s.strip()
    return s or None


def _regex_to_label_words(pat: str) -> list[str]:
    plain = _split_plain_alts(pat)
    if plain is not None:
        return plain
    words: list[str] = []
    for branch in str(pat or "").split("|"):
        w = _simplify_regex_branch(branch)
        if w and w not in words:
            words.append(w)
    return words


def project_student_rules(
    *,
    rows: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """工厂规则 → 学生包关键词表（无 match_scope / 正则厂词汇）。"""
    out: list[dict[str, Any]] = []
    for rule in export_hints(rows=rows):
        scope = rule["match_scope"]
        pat = str(rule["match_pattern"] or "").strip()
        widget = rule["widget"]
        field_type = _norm(rule.get("when_type"))
        item: dict[str, Any] = {"widget": widget}
        if field_type:
            item["fieldType"] = field_type
        if scope == "key":
            item["keys"] = [pat]
        elif scope == "label_exact":
            alts = [a.strip() for a in pat.split("|") if a.strip()]
            item["labelIsAny"] = alts or [pat]
        elif scope == "label_contains":
            item["labelHasAny"] = [pat]
        elif scope == "label_regex":
            words = _regex_to_label_words(pat)
            if not words:
                continue
            item["labelHasAny"] = words
        else:
            continue
        out.append(item)
    return out


def student_rule_matches(
    rule: dict[str, Any],
    *,
    field_type: str,
    key: str,
    label: str,
) -> bool:
    ft = _norm(rule.get("fieldType") or rule.get("field_type"))
    if ft and ft != field_type:
        return False
    keys = rule.get("keys")
    if isinstance(keys, list) and keys:
        if key in [str(k) for k in keys]:
            return True
        # 本条以键匹配为主；未命中则不再用标签
        return False
    exact = rule.get("labelIsAny") or rule.get("label_is_any")
    if isinstance(exact, list) and exact:
        return label in [str(x) for x in exact]
    has_any = rule.get("labelHasAny") or rule.get("label_has_any")
    if isinstance(has_any, list) and has_any:
        return any(str(w) and str(w) in label for w in has_any)
    return False


def match_student_widget_hint(
    *,
    field_type: str,
    key: str,
    label: str,
    rows: list[dict[str, Any]] | None = None,
    only_widgets: frozenset[str] | None = None,
) -> str | None:
    for rule in project_student_rules(rows=rows):
        widget = str(rule.get("widget") or "")
        if only_widgets is not None and widget not in only_widgets:
            continue
        if student_rule_matches(rule, field_type=field_type, key=key, label=label):
            return widget
    return None


def rule_matches(
    rule: dict[str, Any],
    *,
    field_type: str,
    key: str,
    label: str,
) -> bool:
    when = _norm(rule.get("when_type"))
    if when and when != field_type:
        return False
    scope = _norm(rule.get("match_scope"))
    pat = str(rule.get("match_pattern") or "")
    if not pat:
        return False
    if scope == "key":
        return key == pat
    if scope == "label_exact":
        alts = [a.strip() for a in pat.split("|") if a.strip()]
        return label in alts if alts else label == pat
    if scope == "label_contains":
        return pat in label
    if scope == "label_regex":
        try:
            return bool(re.search(pat, label))
        except re.error:
            return False
    return False


def match_widget_hint(
    *,
    field_type: str,
    key: str,
    label: str,
    rows: list[dict[str, Any]] | None = None,
    only_widgets: frozenset[str] | None = None,
) -> str | None:
    for rule in export_hints(rows=rows):
        widget = rule["widget"]
        if only_widgets is not None and widget not in only_widgets:
            continue
        if rule_matches(rule, field_type=field_type, key=key, label=label):
            return widget
    return None


def render_field_widget_rules_js(
    *,
    rows: list[dict[str, Any]] | None = None,
) -> str:
    """学生腔 JS 模块正文。"""
    payload = json.dumps(project_student_rules(rows=rows), ensure_ascii=False, indent=2)
    return (
        "/**\n"
        " * 按字段中文标签选择表单控件，避免档案项一律用文本框。\n"
        " * 从上往下匹配，先命中的生效。\n"
        " */\n"
        f"export const FIELD_WIDGET_RULES = {payload}\n"
    )


def write_field_widget_rules(
    dest: Path,
    *,
    rows: list[dict[str, Any]] | None = None,
) -> Path | None:
    """写出学生包 fieldWidgetRules.js；并删掉旧厂形 widgetHints.json。"""
    fe = dest / "frontend" / "src" / "utils"
    fe.mkdir(parents=True, exist_ok=True)
    path = fe / "fieldWidgetRules.js"
    path.write_text(render_field_widget_rules_js(rows=rows), encoding="utf-8")
    legacy = fe / "widgetHints.json"
    if legacy.is_file():
        try:
            legacy.unlink()
        except OSError:
            pass
    return path


def write_widget_hints_json(
    dest: Path,
    *,
    rows: list[dict[str, Any]] | None = None,
) -> Path | None:
    """兼容旧调用名 → 学生投影 fieldWidgetRules.js。"""
    return write_field_widget_rules(dest, rows=rows)


def apply_widget_hints_to_schema(
    schema: dict[str, Any] | None,
    *,
    rows: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    if not isinstance(schema, dict):
        return schema or {}
    # 学生 schema 只留投影；禁止 match_scope 厂形进 ZIP
    schema["fieldWidgetRules"] = project_student_rules(rows=rows)
    schema.pop("widgetHints", None)
    return schema


def expected_rule_keys_from_seed() -> tuple[str, ...]:
    return tuple(
        sorted({_norm(r.get("rule_key")) for r in _seed_payload() if _norm(r.get("rule_key"))})
    )


def gap_report(*, rows: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    data = _rows_or_seed(rows)
    have = {
        _norm(r.get("rule_key")): r
        for r in data
        if _norm(r.get("source")) in BAKE_SOURCES and _norm(r.get("rule_key"))
    }
    gaps = []
    for rk in expected_rule_keys_from_seed():
        if rk not in have:
            gaps.append({"rule_key": rk, "reason": "缺少控件语义规则"})
            continue
        row = have[rk]
        if not str(row.get("match_pattern") or "").strip():
            gaps.append({"rule_key": rk, "reason": "匹配模式为空"})
        elif _norm(row.get("widget")) not in WIDGET_KINDS:
            gaps.append({"rule_key": rk, "reason": "控件类型非法"})
    return {"gap_count": len(gaps), "gaps": gaps}


async def upsert_entry(
    db: AsyncSession,
    *,
    rule_key: str,
    match_scope: str,
    match_pattern: str,
    widget: str,
    when_type: str = "",
    note_zh: str = "",
    sort: int = 0,
    enabled: bool = True,
    source: str = "manual",
) -> dict[str, Any]:
    from app.models import FactoryWidgetHint

    rule_key = _norm(rule_key)
    match_scope = _norm(match_scope) or "label_contains"
    match_pattern = str(match_pattern or "").strip()
    widget = _norm(widget)
    source = _norm(source) or "manual"
    if not rule_key or not match_pattern or not widget:
        raise ValueError("rule_key、match_pattern、widget 必填")
    if match_scope not in MATCH_SCOPES:
        raise ValueError(f"match_scope 须为 {', '.join(sorted(MATCH_SCOPES))}")
    if widget not in WIDGET_KINDS:
        raise ValueError(f"widget 须为已知控件类型")
    when_type = _norm(when_type)
    if when_type not in WHEN_TYPES:
        raise ValueError("when_type 须为空、string 或 number")
    if source not in SOURCES:
        source = "manual"
    result = await db.execute(
        select(FactoryWidgetHint).where(FactoryWidgetHint.rule_key == rule_key)
    )
    row = result.scalar_one_or_none()
    if row:
        row.match_scope = match_scope
        row.match_pattern = match_pattern
        row.when_type = when_type
        row.widget = widget
        row.note_zh = _norm(note_zh)
        row.sort = int(sort or 0)
        row.enabled = bool(enabled)
        row.source = source
        row.updated_at = datetime.utcnow()
    else:
        row = FactoryWidgetHint(
            rule_key=rule_key,
            match_scope=match_scope,
            match_pattern=match_pattern,
            when_type=when_type,
            widget=widget,
            note_zh=_norm(note_zh),
            sort=int(sort or 0),
            enabled=bool(enabled),
            source=source,
        )
        db.add(row)
    await db.commit()
    await db.refresh(row)
    invalidate_cache()
    await load_all_rows(db)
    return row_to_dict(row)


async def delete_entry(db: AsyncSession, entry_id: int) -> bool:
    from app.models import FactoryWidgetHint

    row = await db.get(FactoryWidgetHint, entry_id)
    if not row:
        return False
    await db.delete(row)
    await db.commit()
    invalidate_cache()
    return True
