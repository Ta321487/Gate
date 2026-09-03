"""嵌既有模块图 / E-R SVG 到 .factory/defense-ppt/figures（不另生成语义）。"""

from __future__ import annotations

import base64
from typing import Any
from urllib.parse import quote

from app.models import Project

from .themes import ensure_ppt_dirs, ppt_root, workspace_path


def _svg_data_url(svg: str) -> str:
    raw = svg.encode("utf-8")
    return "data:image/svg+xml;base64," + base64.b64encode(raw).decode("ascii")


def materialize_artifact_figures(
    project: Project,
    deck: dict[str, Any],
    ctx: dict[str, Any],
) -> dict[str, Any]:
    """写 modules.svg / er.svg，并回填 deck 页 figure。"""
    root = ensure_ppt_dirs(project)
    fig_dir = root / "figures"
    fig_dir.mkdir(parents=True, exist_ok=True)
    ws = workspace_path(project)
    proposal = str(ctx.get("proposal") or "")

    modules_ok = False
    er_ok = False
    modules_url = None
    er_url = None

    if ws:
        try:
            from app.bake.schema.modules import load_module_model, render_module_svg

            model = load_module_model(ws, proposal_text=proposal)
            if model:
                svg = render_module_svg(model)
                path = fig_dir / "modules.svg"
                path.write_text(svg, encoding="utf-8")
                modules_ok = True
                modules_url = _svg_data_url(svg)
        except Exception:  # noqa: BLE001
            modules_ok = False
        try:
            from app.bake.schema.er import load_schema_model, render_er_svg

            model = load_schema_model(ws)
            if model and (model.get("tables") or model.get("entities")):
                svg = render_er_svg(model, mode="total")
                path = fig_dir / "er.svg"
                path.write_text(svg, encoding="utf-8")
                er_ok = True
                er_url = _svg_data_url(svg)
        except Exception:  # noqa: BLE001
            er_ok = False

    for page in deck.get("pages") or []:
        if not isinstance(page, dict):
            continue
        role = page.get("role")
        if role == "modules":
            page["figure"] = {
                "kind": "modules",
                "label": "模块图（嵌自产物 SVG）",
                "available": modules_ok,
                "missing": not modules_ok,
                "path": "figures/modules.svg" if modules_ok else None,
                "url": modules_url,
                "project_svg": "modules",
            }
        elif role == "er":
            page["figure"] = {
                "kind": "er",
                "label": "E-R 图（嵌自产物 SVG）",
                "available": er_ok,
                "missing": not er_ok,
                "path": "figures/er.svg" if er_ok else None,
                "url": er_url,
                "project_svg": "er",
            }
        elif role == "demo":
            fig = page.get("figure") if isinstance(page.get("figure"), dict) else {}
            if not fig.get("available"):
                page["figure"] = {
                    "kind": "screenshot",
                    "label": "主流程界面截图",
                    "available": False,
                    "missing": True,
                    "hint": "缺主流程截图 · 请采图或上传",
                }
    return deck


def figure_file(project: Project, rel: str):
    root = ppt_root(project)
    if not root:
        return None
    # 防路径穿越
    rel_n = str(rel or "").replace("\\", "/").lstrip("/")
    if ".." in rel_n.split("/"):
        return None
    path = root / rel_n
    return path if path.is_file() else None


def project_figure_api_hint(project_id: str, kind: str) -> str:
    if kind == "modules":
        return f"/api/projects/{quote(project_id)}/schema/modules.svg?layout=biz"
    if kind == "er":
        return f"/api/projects/{quote(project_id)}/schema/er.svg?mode=total"
    return ""
