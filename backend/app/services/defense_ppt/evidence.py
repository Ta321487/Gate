"""evidence：只组装现有 proposal / modules / er / testcases / gates，禁止重扫。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.models import Project
from app.services.projects import delivery_block_reason, workspace_or_reason
from app.services.proposal import load_merged_proposal_text

from .themes import workspace_path


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except Exception:  # noqa: BLE001
        return None


def has_proposal(project: Project) -> bool:
    if project.source_path and Path(str(project.source_path)).exists():
        return True
    text = ""
    try:
        if project.source_path:
            text = load_merged_proposal_text(project.source_path) or ""
    except Exception:  # noqa: BLE001
        text = ""
    return bool(str(text).strip())


def has_modules(project: Project) -> bool:
    ws = workspace_path(project)
    if not ws:
        return False
    # 与 getModules / modules.svg 同源
    from app.bake.schema.modules import load_module_model

    try:
        model = load_module_model(ws)
    except Exception:  # noqa: BLE001
        return False
    if not model:
        return False
    groups = model.get("groups") or model.get("nodes") or model.get("tree")
    return bool(groups)


def has_er(project: Project) -> bool:
    ws = workspace_path(project)
    if not ws:
        return False
    # 与 ER API 同源：能 load_schema_model 即可
    from app.bake.schema.er import load_schema_model

    try:
        model = load_schema_model(ws)
    except Exception:  # noqa: BLE001
        return False
    return bool(model and (model.get("tables") or model.get("entities")))


def has_testcases(project: Project) -> bool:
    ws = workspace_path(project)
    if not ws:
        return False
    from app.bake.schema.testcases import load_testcase_model

    try:
        model = load_testcase_model(ws)
    except Exception:  # noqa: BLE001
        return False
    return bool(model and (model.get("rows") or model.get("cases") or model.get("items")))


def gates_overall_ok(project: Project) -> bool:
    return delivery_block_reason(project) is None


def assemble_evidence(project: Project) -> dict[str, bool]:
    return {
        "proposal": has_proposal(project),
        "modules": has_modules(project),
        "er": has_er(project),
        "testcases": has_testcases(project),
        "gates_overall": gates_overall_ok(project),
    }


def evidence_ready(evidence: dict[str, bool] | None) -> bool:
    e = evidence or {}
    return all(bool(e.get(k)) for k in ("proposal", "modules", "er", "testcases", "gates_overall"))


def collect_context(project: Project) -> dict[str, Any]:
    """给 fill Unit 裁剪用的上下文（只读现有服务/产物）。"""
    ws, _ = workspace_or_reason(project)
    proposal = ""
    try:
        if project.source_path:
            proposal = load_merged_proposal_text(project.source_path) or ""
    except Exception:  # noqa: BLE001
        proposal = ""

    schema: dict[str, Any] = {}
    modules: dict[str, Any] | None = None
    er: dict[str, Any] | None = None
    testcases: dict[str, Any] | None = None
    if ws:
        schema = _read_json(ws / "domain.schema.json") or {}
        try:
            from app.bake.schema.modules import load_module_model

            modules = load_module_model(ws, proposal_text=proposal) or None
        except Exception:  # noqa: BLE001
            modules = None
        try:
            from app.bake.schema.er import load_schema_model

            er = load_schema_model(ws)
        except Exception:  # noqa: BLE001
            er = None
        try:
            from app.bake.schema.testcases import load_testcase_model

            testcases = load_testcase_model(ws)
        except Exception:  # noqa: BLE001
            testcases = None

    menus = schema.get("menus") if isinstance(schema, dict) else None
    features = schema.get("features") if isinstance(schema, dict) else None
    entities = schema.get("entities") if isinstance(schema, dict) else None
    persistence = getattr(project, "persistence", None) or (project.spec or {}).get("persistence") or "jdbc"
    spring_security = bool(getattr(project, "spring_security", False))

    return {
        "title": project.title or "",
        "proposal": proposal[:12000],
        "menus": menus,
        "features": features,
        "entities": entities,
        "modules": modules,
        "er": er,
        "testcases": testcases,
        "persistence": persistence,
        "spring_security": spring_security,
        "domain": project.domain,
        "archetype": project.archetype,
        "spec": project.spec if isinstance(project.spec, dict) else {},
    }
