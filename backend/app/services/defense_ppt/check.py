"""检查项 → can_export。Job 流水线与导出 API 共用同一套门闩。"""

from __future__ import annotations

from typing import Any

from app.models import Project
from app.services.projects import delivery_block_reason

from .deck_io import load_deck
from .fingerprint import is_biz_dirty


_REQUIRED_ROLES = ("cover", "toc", "modules", "er", "demo", "summary")
_BULLET_SOFT_MAX = 80
_BULLET_HARD_MAX = 120


def run_check(project: Project) -> dict[str, Any]:
    deck = load_deck(project)
    return run_check_on_deck(project, deck)


def run_check_on_deck(project: Project, deck: dict[str, Any] | None) -> dict[str, Any]:
    """对内存中的 deck 跑检查（写盘前 Job 步与导出门闩同源）。"""
    items: list[dict[str, str]] = []
    if not deck:
        items.append({"level": "error", "code": "no_deck", "message": "尚未生成答辩 PPT"})
        return {"items": items, "can_export": False}

    items.append({"level": "ok", "code": "deck_ok", "message": "deck.json 结构完整"})

    if delivery_block_reason(project):
        items.append(
            {
                "level": "error",
                "code": "gates",
                "message": "bake 门禁 overall 未通过，禁止导出",
            }
        )

    dirty = bool(deck.get("biz_dirty")) or is_biz_dirty(project)
    if dirty:
        items.append(
            {
                "level": "error",
                "code": "biz_dirty",
                "message": "业务指纹脏 · 须先按工程更新业务页",
            }
        )

    pages = [p for p in (deck.get("pages") or []) if isinstance(p, dict)]
    roles = {p.get("role") for p in pages}
    missing_roles = [r for r in _REQUIRED_ROLES if r not in roles]
    if missing_roles:
        items.append(
            {
                "level": "error",
                "code": "structure",
                "message": f"大纲缺页：{', '.join(missing_roles)}",
            }
        )

    demo = next((p for p in pages if p.get("role") == "demo"), None)
    fig = (demo or {}).get("figure") if isinstance(demo, dict) else None
    if not isinstance(fig, dict) or fig.get("missing") or not fig.get("available"):
        items.append(
            {
                "level": "error",
                "code": "demo_shot",
                "message": "演示页缺主流程界面截图（禁导出）",
            }
        )

    from .evidence import collect_context
    from .planner import build_allowlist

    try:
        allow = build_allowlist(collect_context(project))
    except Exception:  # noqa: BLE001
        allow = {"tech": []}
    hallu = _hallucination_hits(deck, allowlist_tech=allow.get("tech") or [])
    if hallu:
        items.append(
            {
                "level": "error",
                "code": "hallucination",
                "message": f"技术/模块不在实包：{', '.join(hallu[:4])}",
            }
        )

    locked_conflict = any(
        isinstance(b, dict)
        and b.get("locked")
        and "冲突" in str(b.get("text") or "")
        for p in pages
        for b in (p.get("bullets") or [])
    )
    if locked_conflict:
        items.append(
            {
                "level": "warning",
                "code": "locked_conflict",
                "message": "存在已锁定要点与实包可能冲突（未自动覆盖）",
            }
        )

    soft_long = False
    hard_long = False
    for p in pages:
        for b in p.get("bullets") or []:
            if not isinstance(b, dict):
                continue
            n = len(str(b.get("text") or ""))
            if n > _BULLET_HARD_MAX:
                hard_long = True
            elif n > _BULLET_SOFT_MAX:
                soft_long = True
    if hard_long:
        items.append(
            {
                "level": "warning",
                "code": "overflow",
                "message": f"部分要点超过 {_BULLET_HARD_MAX} 字，导出时可能溢出版心",
            }
        )
    elif soft_long:
        items.append({"level": "warning", "code": "verbose", "message": "部分要点字数偏多"})

    has_error = any(i["level"] == "error" for i in items)
    if not has_error:
        items.append({"level": "ok", "code": "export_ok", "message": "可通过导出门闩"})

    can_export = (
        not has_error
        and delivery_block_reason(project) is None
        and not dirty
        and bool(deck)
    )
    return {"items": items, "can_export": can_export}


_FORBIDDEN_STACK = (
    "redis",
    "kafka",
    "rabbitmq",
    "mongodb",
    "elasticsearch",
    "docker",
    "kubernetes",
    "django",
    "flask",
    ".net",
    "android",
)


def _hallucination_hits(
    deck: dict[str, Any], *, allowlist_tech: list[str] | None = None
) -> list[str]:
    text_bits: list[str] = []
    for p in deck.get("pages") or []:
        if not isinstance(p, dict):
            continue
        for b in p.get("bullets") or []:
            if isinstance(b, dict):
                text_bits.append(str(b.get("text") or ""))
        table = p.get("table")
        if isinstance(table, dict):
            for row in table.get("rows") or []:
                if isinstance(row, (list, tuple)):
                    text_bits.extend(str(x) for x in row)
    blob = "\n".join(text_bits).lower()
    allowed = {str(x).lower() for x in (allowlist_tech or [])}
    allowed.update({"spring", "vue", "element", "mysql", "jdbc", "mybatis", "jpa", "security"})
    hits = []
    for word in _FORBIDDEN_STACK:
        if word in blob and word not in allowed:
            hits.append(word)
    return hits


# Job 流水线：这些 error 仍落盘，但 Job 标 failed（demo_shot 留给人手补图，不阻生成成功）
_JOB_HARD_CODES = frozenset({"structure", "hallucination", "no_deck", "gates"})


def job_hard_failures(check_result: dict[str, Any]) -> list[str]:
    return [
        i["message"]
        for i in (check_result.get("items") or [])
        if i.get("level") == "error" and i.get("code") in _JOB_HARD_CODES
    ]
