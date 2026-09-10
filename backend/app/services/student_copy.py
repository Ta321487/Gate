"""出包后清洗学生可见工厂腔：只编排已有 bake scrub / 门禁，不另写清洗规则。"""

from __future__ import annotations

import json
from typing import Any

from app.bake.domain_schema import refresh_polluted_vue_from_baseline
from app.bake.engine_islands import emit_schema_to_workspace
from app.models import Project
from app.services import projects as project_svc


def scrub_project_student_copy(project: Project) -> dict[str, Any]:
    """emit（schema scrub）+ 用现网 baseline 覆写仍脏的 Vue；不必整题重 bake。

    覆盖工厂腔（p3copy）与演示口吻（p3s demo_hits）；清洗后重评语义门禁。
    """
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

    # 清洗后重评：否则页头仍挂旧 p3s/p3copy
    try:
        from app.bake.gates.evaluate import evaluate_domain_gates

        gates = evaluate_domain_gates(ws, project.spec if isinstance(project.spec, dict) else {})
        project.gates = gates
        from sqlalchemy.orm.attributes import flag_modified

        try:
            flag_modified(project, "gates")
        except Exception:  # noqa: BLE001
            pass
    except Exception:  # noqa: BLE001
        gates = project.gates if isinstance(project.gates, dict) else {}

    if project.zip_path:
        project.zip_ready = False

    downloadable = project_svc.gates_allow_delivery(project.gates)
    copy_gate = (project.gates or {}).get("p3copy") or {}
    sem_gate = (project.gates or {}).get("p3s") or {}
    return {
        "written": written[:40],
        "copy_ok": bool(copy_gate.get("ok")),
        "copy_desc": str(copy_gate.get("desc") or ""),
        "hits": list((copy_gate.get("detail") or {}).get("hits") or [])[:12],
        "semantic_ok": bool(sem_gate.get("ok", True)),
        "semantic_desc": str(sem_gate.get("desc") or ""),
        "demo_hits": list((sem_gate.get("detail") or {}).get("demo_hits") or [])[:8],
        "zip_ready": bool(project.zip_ready and downloadable),
        "download_blocked_reason": project_svc.delivery_block_reason(project),
    }
