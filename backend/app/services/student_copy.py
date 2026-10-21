"""出包后清洗学生可见工厂腔：emit schema scrub + Vue + 工厂注记注释。"""

from __future__ import annotations

import copy
import json
from typing import Any

from app.bake.domain_schema import (
    refresh_polluted_js_from_baseline,
    refresh_polluted_vue_from_baseline,
)
from app.bake.engine_islands import emit_schema_to_workspace
from app.bake.gates.evaluate import evaluate_domain_gates
from app.bake.pack_prune import (
    prune_shell_chrome_in_workspace,
    scrub_factory_notes_in_workspace,
)
from app.models import Project
from app.services import projects as project_svc


def scrub_project_student_copy(project: Project) -> dict[str, Any]:
    """emit（schema scrub）+ Vue 清洗 + 抹工厂注记 + 补裁壳件；重算门禁。

    点按钮后须能过 p3copy / p3lean（注记与 PortalSideRail 壳件），不必为此重 bake。
    """
    ws, reason = project_svc.workspace_or_reason(project)
    if reason or ws is None:
        raise ValueError(reason or "无工作区")

    spec = dict(project.spec or {})
    # 壳件裁剪认 shell_nav_style；工作区 spec.json 常比 ORM 更全
    disk_spec = ws / "spec.json"
    if disk_spec.is_file():
        try:
            loaded_spec = json.loads(disk_spec.read_text(encoding="utf-8"))
            if isinstance(loaded_spec, dict) and loaded_spec:
                for key in ("shell_nav_style", "domain", "title", "card_voice", "domain_group"):
                    if not spec.get(key) and loaded_spec.get(key):
                        spec[key] = loaded_spec[key]
        except Exception:  # noqa: BLE001
            pass
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
    # utils/*.js 展示字面量（旁路/不对接…）——只 scrub Vue 会漏 p3copy
    written.extend(refresh_polluted_js_from_baseline(ws))
    # 全树再抹注记：覆盖 js/css，以及回拷 baseline Vue 残留
    notes = scrub_factory_notes_in_workspace(ws)
    written.extend(notes)
    # 非市集补裁右侧栏（旧包漏裁 / 清洗不重跑 prune 时 p3lean 会红）
    chrome = prune_shell_chrome_in_workspace(ws, spec)
    written.extend(chrome)
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
    lean_gate = (project.gates or {}).get("p3lean") or {}
    return {
        "written": written[:40],
        "copy_ok": bool(copy_gate.get("ok")),
        "copy_desc": str(copy_gate.get("desc") or ""),
        "hits": list((copy_gate.get("detail") or {}).get("hits") or [])[:12],
        "semantic_ok": bool(sem_gate.get("ok", True)),
        "semantic_desc": str(sem_gate.get("desc") or ""),
        "demo_hits": list((sem_gate.get("detail") or {}).get("demo_hits") or [])[:8],
        "lean_ok": bool(lean_gate.get("ok", True)),
        "lean_desc": str(lean_gate.get("desc") or ""),
        "notes_scrubbed": notes[:20],
        "chrome_pruned": chrome[:10],
        "zip_ready": bool(project.zip_ready and downloadable),
        "download_blocked_reason": project_svc.delivery_block_reason(project),
    }
