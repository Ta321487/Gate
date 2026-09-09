"""出包后清洗学生可见工厂腔：只编排已有 bake scrub / 门禁，不另写清洗规则。"""

from __future__ import annotations

import json
from typing import Any

from app.bake.domain_schema import refresh_polluted_vue_from_baseline
from app.bake.engine_islands import emit_schema_to_workspace
from app.models import Project
from app.services import projects as project_svc


def scrub_project_student_copy(project: Project) -> dict[str, Any]:
    """emit（schema scrub）+ 用现网 baseline 覆写仍脏的 Vue；不必整题重 bake。"""
    ws, reason = project_svc.workspace_or_reason(project)
    if reason or ws is None:
        raise ValueError(reason or "无工作区")

    spec = dict(project.spec or {})
    disk = ws / "domain.schema.json"
    if disk.is_file():
        try:
            loaded = json.loads(disk.read_text(encoding="utf-8"))
            if isinstance(loaded, dict) and loaded:
                spec = {**spec, "schema": loaded}
        except Exception:  # noqa: BLE001
            pass

    written = emit_schema_to_workspace(ws, spec)
    written.extend(refresh_polluted_vue_from_baseline(ws))
    cleaned = json.loads(disk.read_text(encoding="utf-8")) if disk.is_file() else dict(
        spec.get("schema") or {}
    )
    project.spec = {**spec, "schema": cleaned}

    project_svc.sync_checklist_from_workspace(project)
    if project.zip_path:
        project.zip_ready = False

    downloadable = project_svc.gates_allow_delivery(project.gates)
    copy_gate = (project.gates or {}).get("p3copy") or {}
    return {
        "written": written[:40],
        "copy_ok": bool(copy_gate.get("ok")),
        "copy_desc": str(copy_gate.get("desc") or ""),
        "hits": list((copy_gate.get("detail") or {}).get("hits") or [])[:12],
        "zip_ready": bool(project.zip_ready and downloadable),
        "download_blocked_reason": project_svc.delivery_block_reason(project),
    }
