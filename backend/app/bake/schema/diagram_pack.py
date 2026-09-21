"""论文图打包：一次算出 model+svg，走 diagram_cache；bake 后预热默认视图。"""

from __future__ import annotations

import hashlib
import logging
import time
from pathlib import Path
from typing import Any

from app.bake.schema import diagram_cache as dcache

logger = logging.getLogger("app.bake.diagram_pack")


def _prop_tag(proposal_text: str) -> str:
    raw = (proposal_text or "").strip()
    if not raw:
        return "0"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12]


def pack_er(
    workspace: Path,
    *,
    mode: str = "total",
    entity: str | None = None,
    force: bool = False,
) -> dict[str, Any] | None:
    """E-R 总图/分图：一次返回 model + svg；按 mode/entity 缓存。"""
    from app.bake.schema.er import (
        collect_english_gaps,
        count_er_gaps,
        load_schema_model,
        render_er_svg,
    )

    mode_n = (mode or "total").strip().lower()
    if mode_n not in ("total", "part"):
        mode_n = "total"
    ent = (entity or "").strip() or None
    params: dict[str, Any] = {"mode": mode_n}
    if mode_n == "part":
        params["entity"] = ent or ""

    def build() -> tuple[dict[str, Any], dict[str, float]]:
        t0 = time.perf_counter()
        model = load_schema_model(workspace)
        if not model:
            raise FileNotFoundError("er: no schema.sql")
        model_ms = (time.perf_counter() - t0) * 1000.0
        conceptual = [
            str(x)
            for x in (model.get("conceptual_entities") or [])
            if str(x).strip()
        ]
        use_ent = ent
        if mode_n == "part" and not use_ent:
            use_ent = conceptual[0] if conceptual else None
            if not use_ent:
                tables = [
                    t
                    for t in (model.get("tables") or [])
                    if isinstance(t, dict)
                    and t.get("name")
                    and not t.get("assoc_link")
                    and not t.get("role_of")
                ]
                use_ent = str((tables[0] or {}).get("name") or "") if tables else None
        t1 = time.perf_counter()
        # E-R 排版在 render 内完成，记入 layout_ms
        svg = render_er_svg(model, mode=mode_n, entity=use_ent)
        layout_svg_ms = (time.perf_counter() - t1) * 1000.0
        packed = dict(model)
        packed["svg"] = svg
        packed["er_mode"] = mode_n
        packed["er_entity"] = use_ent
        packed["conceptual_entities"] = conceptual
        packed["er_gap_count"] = count_er_gaps(collect_english_gaps(model))
        return packed, {
            "model_ms": model_ms,
            "layout_ms": layout_svg_ms * 0.85,
            "svg_ms": layout_svg_ms * 0.15,
        }

    try:
        model = dcache.get_or_build(workspace, "er", params, build, force=force)
    except FileNotFoundError:
        return None
    if not model:
        return None
    from app.bake.schema.er_view import load_user_svg

    use_ent = ent if mode_n == "part" else None
    if mode_n == "part" and not use_ent:
        use_ent = str(model.get("er_entity") or "") or None
    saved = load_user_svg(workspace, mode_n, use_ent)
    if saved:
        model = dict(model)
        model["svg"] = saved
        model["er_view"] = "user"
    return model


def _strip_internal(model: dict[str, Any]) -> dict[str, Any]:
    """缓存/响应前去掉仅排版内部字段（体积大且前端不用）。"""
    out = dict(model)
    out.pop("_assoc_paths", None)
    out.pop("associations_all", None)
    for cls in out.get("classes") or []:
        if isinstance(cls, dict):
            cls.pop("_attrs_full", None)
            cls.pop("_methods_full", None)
    return out


def pack_classes(
    workspace: Path,
    *,
    display: str = "sample",
    title_fallback: str = "管理系统",
    force: bool = False,
) -> dict[str, Any] | None:
    from app.bake.schema.classes import load_class_model, render_class_svg
    from app.bake.schema.class_model import normalize_class_display_mode

    mode = normalize_class_display_mode(display)
    params = {"display": mode}

    def build() -> tuple[dict[str, Any], dict[str, float]]:
        t_model = time.perf_counter()
        model = load_class_model(
            workspace,
            title_fallback=title_fallback,
            display_mode=mode,
        )
        if not model:
            raise FileNotFoundError("classes: no schema.sql")
        # load_class_model 已含 layout；单独记一段便于日志对齐口径
        layout_ms = float((model.get("evidence") or {}).get("layout_ms") or 0)
        model_ms = (time.perf_counter() - t_model) * 1000.0
        t_svg = time.perf_counter()
        svg = render_class_svg(model)
        svg_ms = (time.perf_counter() - t_svg) * 1000.0
        packed = _strip_internal(model)
        packed["svg"] = svg
        return packed, {
            "model_ms": model_ms - layout_ms if layout_ms else model_ms,
            "layout_ms": layout_ms,
            "svg_ms": svg_ms,
        }

    try:
        return dcache.get_or_build(
            workspace, "classes", params, build, force=force
        )
    except FileNotFoundError:
        return None


def pack_modules(
    workspace: Path,
    *,
    layout: str = "identity",
    expand_details: bool = False,
    proposal_text: str = "",
    force: bool = False,
) -> dict[str, Any] | None:
    from app.bake.schema.modules import (
        load_module_model,
        normalize_module_layout,
        render_module_svg,
    )

    layout_n = normalize_module_layout(layout)
    params = {
        "layout": layout_n,
        "expand": bool(expand_details),
        "prop": _prop_tag(proposal_text),
    }

    def build() -> tuple[dict[str, Any], dict[str, float]]:
        t0 = time.perf_counter()
        model = load_module_model(
            workspace,
            proposal_text=proposal_text,
            layout=layout_n,
            expand_details=expand_details,
        )
        if not model:
            raise FileNotFoundError("modules: no domain.schema")
        model_ms = (time.perf_counter() - t0) * 1000.0
        t1 = time.perf_counter()
        svg = render_module_svg(model)
        svg_ms = (time.perf_counter() - t1) * 1000.0
        packed = dict(model)
        packed["svg"] = svg
        return packed, {"model_ms": model_ms, "layout_ms": 0.0, "svg_ms": svg_ms}

    try:
        return dcache.get_or_build(
            workspace, "modules", params, build, force=force
        )
    except FileNotFoundError:
        return None


def pack_architecture(
    workspace: Path,
    *,
    title_fallback: str = "管理系统",
    force: bool = False,
) -> dict[str, Any] | None:
    from app.bake.schema.architecture import (
        load_architecture_model,
        render_architecture_svg,
    )

    params: dict[str, Any] = {"v": "default"}

    def build() -> tuple[dict[str, Any], dict[str, float]]:
        t0 = time.perf_counter()
        model = load_architecture_model(workspace, title_fallback=title_fallback)
        if not model:
            raise FileNotFoundError("architecture: no domain.schema")
        model_ms = (time.perf_counter() - t0) * 1000.0
        t1 = time.perf_counter()
        svg = render_architecture_svg(model)
        svg_ms = (time.perf_counter() - t1) * 1000.0
        packed = dict(model)
        packed["svg"] = svg
        return packed, {"model_ms": model_ms, "layout_ms": 0.0, "svg_ms": svg_ms}

    try:
        return dcache.get_or_build(
            workspace, "architecture", params, build, force=force
        )
    except FileNotFoundError:
        return None


def _pack_multi_diagram(
    workspace: Path,
    kind: str,
    *,
    selection: list[str] | None,
    proposal_text: str,
    title_fallback: str,
    load_fn,
    render_fn,
    force: bool,
) -> dict[str, Any] | None:
    ids = list(selection) if selection else []
    params = {
        "ids": ",".join(ids) if ids else "default",
        "prop": _prop_tag(proposal_text),
    }

    def build() -> tuple[dict[str, Any], dict[str, float]]:
        t0 = time.perf_counter()
        model = load_fn(
            workspace,
            proposal_text=proposal_text,
            selection=selection,
            title_fallback=title_fallback,
        )
        if not model:
            raise FileNotFoundError(f"{kind}: no domain.schema")
        model_ms = (time.perf_counter() - t0) * 1000.0
        t1 = time.perf_counter()
        packed = dict(model)
        diagrams = []
        for d in packed.get("diagrams") or []:
            if not isinstance(d, dict):
                continue
            row = dict(d)
            row["svg"] = render_fn(d)
            diagrams.append(row)
        packed["diagrams"] = diagrams
        # 兼容旧前端：首张也挂顶层 svg
        if diagrams:
            packed["svg"] = diagrams[0].get("svg") or ""
        svg_ms = (time.perf_counter() - t1) * 1000.0
        return packed, {"model_ms": model_ms, "layout_ms": 0.0, "svg_ms": svg_ms}

    try:
        return dcache.get_or_build(workspace, kind, params, build, force=force)
    except FileNotFoundError:
        return None


def pack_sequences(
    workspace: Path,
    *,
    selection: list[str] | None = None,
    proposal_text: str = "",
    title_fallback: str = "管理系统",
    force: bool = False,
) -> dict[str, Any] | None:
    from app.bake.schema.sequence import load_sequence_model, render_sequence_svg

    return _pack_multi_diagram(
        workspace,
        "sequences",
        selection=selection,
        proposal_text=proposal_text,
        title_fallback=title_fallback,
        load_fn=load_sequence_model,
        render_fn=render_sequence_svg,
        force=force,
    )


def pack_activities(
    workspace: Path,
    *,
    selection: list[str] | None = None,
    proposal_text: str = "",
    title_fallback: str = "管理系统",
    force: bool = False,
) -> dict[str, Any] | None:
    from app.bake.schema.activity import load_activity_model, render_activity_svg

    return _pack_multi_diagram(
        workspace,
        "activities",
        selection=selection,
        proposal_text=proposal_text,
        title_fallback=title_fallback,
        load_fn=load_activity_model,
        render_fn=render_activity_svg,
        force=force,
    )


def pack_usecases(
    workspace: Path,
    *,
    actor: str = "user",
    proposal_text: str = "",
    polish: bool = False,
    force: bool = False,
) -> dict[str, Any] | None:
    from app.bake.schema.usecases import load_usecase_model, render_usecase_svg

    params = {
        "actor": str(actor or "user"),
        "polish": bool(polish),
        "prop": _prop_tag(proposal_text),
    }

    def build() -> tuple[dict[str, Any], dict[str, float]]:
        t0 = time.perf_counter()
        model = load_usecase_model(
            workspace, actor=actor, proposal_text=proposal_text
        )
        if not model:
            raise FileNotFoundError("usecases: no domain.schema")
        # polish 仅润色文案；此处不调 LLM，与现 API 默认 polish=False 对齐
        model_ms = (time.perf_counter() - t0) * 1000.0
        t1 = time.perf_counter()
        svg = render_usecase_svg(model)
        svg_ms = (time.perf_counter() - t1) * 1000.0
        packed = dict(model)
        packed["svg"] = svg
        return packed, {"model_ms": model_ms, "layout_ms": 0.0, "svg_ms": svg_ms}

    try:
        return dcache.get_or_build(
            workspace, "usecases", params, build, force=force
        )
    except FileNotFoundError:
        return None


def warm_default_diagrams(
    workspace: Path,
    *,
    title_fallback: str = "管理系统",
    proposal_text: str = "",
) -> dict[str, Any]:
    """bake 完成后预热默认视图并落盘。失败不阻断出包。"""
    ws = Path(workspace)
    summary: dict[str, Any] = {"ok": True, "items": {}}

    def _one(name: str, fn) -> None:
        try:
            t0 = time.perf_counter()
            model = fn()
            ms = (time.perf_counter() - t0) * 1000.0
            if model is None:
                summary["items"][name] = {"ok": False, "reason": "missing"}
            else:
                summary["items"][name] = {
                    "ok": True,
                    "cache": model.get("diagram_cache"),
                    "total_ms": round(ms, 1),
                    "timing": model.get("timing"),
                }
        except Exception as e:
            logger.warning("warm %s failed: %s", name, e)
            summary["items"][name] = {"ok": False, "reason": str(e)[:200]}
            summary["ok"] = False

    _one(
        "er",
        lambda: pack_er(ws, mode="total", force=True),
    )
    # 每个概念实体一张实体属性图（无外键），避免答辩前逐个点开
    try:
        from app.bake.schema.er import load_schema_model

        _m = load_schema_model(ws)
        _ents = [
            str(x)
            for x in ((_m or {}).get("conceptual_entities") or [])
            if str(x).strip()
        ]
        for _ent in _ents:
            _one(
                f"er_part:{_ent}",
                lambda e=_ent: pack_er(ws, mode="part", entity=e, force=True),
            )
    except Exception as e:
        logger.warning("warm er parts list failed: %s", e)
        summary["items"]["er_parts"] = {"ok": False, "reason": str(e)[:200]}
        summary["ok"] = False
    _one(
        "modules",
        lambda: pack_modules(
            ws,
            layout="identity",
            expand_details=False,
            proposal_text=proposal_text,
            force=True,
        ),
    )
    _one(
        "architecture",
        lambda: pack_architecture(
            ws, title_fallback=title_fallback, force=True
        ),
    )
    _one(
        "classes",
        lambda: pack_classes(
            ws, display="sample", title_fallback=title_fallback, force=True
        ),
    )
    _one(
        "sequences",
        lambda: pack_sequences(
            ws,
            selection=None,
            proposal_text=proposal_text,
            title_fallback=title_fallback,
            force=True,
        ),
    )
    _one(
        "activities",
        lambda: pack_activities(
            ws,
            selection=None,
            proposal_text=proposal_text,
            title_fallback=title_fallback,
            force=True,
        ),
    )

    # 用例：每个 actor 一张
    try:
        from app.bake.schema.usecases import list_usecase_actors

        schema_path = ws / "domain.schema.json"
        schema = {}
        if schema_path.is_file():
            import json

            schema = json.loads(schema_path.read_text(encoding="utf-8"))
        actors = list_usecase_actors(schema) if isinstance(schema, dict) else []
        for a in actors:
            aid = str(a.get("id") or "")
            if not aid:
                continue
            _one(
                f"usecases:{aid}",
                lambda actor_id=aid: pack_usecases(
                    ws,
                    actor=actor_id,
                    proposal_text=proposal_text,
                    polish=False,
                    force=True,
                ),
            )
    except Exception as e:
        summary["items"]["usecases"] = {"ok": False, "reason": str(e)[:200]}
        summary["ok"] = False

    logger.info("diagram warm done workspace=%s summary=%s", ws.name, summary)
    return summary
