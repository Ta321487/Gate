"""出包后清洗学生可见工厂腔：emit schema scrub + Vue（骨架可脏则就地洗）。"""

from __future__ import annotations

import copy
import json
from typing import Any

from app.bake.domain_schema import refresh_polluted_vue_from_baseline
from app.bake.engine_islands import emit_schema_to_workspace
from app.bake.gates.evaluate import evaluate_domain_gates
from app.models import Project
from app.services import projects as project_svc


def scrub_project_student_copy(project: Project) -> dict[str, Any]:
    """emit（schema scrub）+ Vue 清洗；重算门禁并强制落库 JSON。

    骨架允许保留工厂注记；点按钮后工作区 + project.gates 必须与实盘一致。
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
    project.spec = {**spec, "schema": copy.deepcopy(cleaned)}
    project_svc.touch_json_fields(project, "spec")

    # 以洗后实盘为准重算；不要沿用旧 gates 详情
    fresh = evaluate_domain_gates(ws, project.spec if isinstance(project.spec, dict) else {})
    project.checklist = list(fresh.get("checklist") or [])
    project.gates = {k: copy.deepcopy(v) for k, v in fresh.items() if k != "checklist"}
    project_svc.touch_json_fields(project, "checklist", "gates")

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
