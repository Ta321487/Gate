"""出包微调 Overrides：payload 白名单校验与 islands 镜像（docs/pack-overrides.md）。

P0 模块短签 · P0.5 hide · P1 序列/活动/用例描述 · P2 架构/用例图/测例/菜单显示名。
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

OVERRIDES_REL = Path("islands") / "overrides.json"

_SCHEMA_VERSION = 1

# 顶层允许键（未知键拒绝）
_ALLOWED_TOP: frozenset[str] = frozenset(
    {
        "schema_version",
        "module_labels",
        "module_hide",
        "architecture_labels",
        "class_labels",
        "class_layout_ref",
        "sequence",
        "activity",
        "usecase",
        "usecase_desc",
        "testcases",
        "menu_labels",
        "schema_labels",
        "er_labels",
        "er_view_ref",
        "_stale",  # 机器写入；人保存时可带入，sanitize 会规范化
    }
)

_FORBIDDEN_EXACT: frozenset[str] = frozenset(
    {
        "caps_force_off",
        "file_replaces",
    }
)

_FORBIDDEN_PREFIX: tuple[str, ...] = ("sql_", "api_")

# 允许 diagramId::m:3 / user::orders::browse::p:actor 等稳定键
_LABEL_KEY_RE = re.compile(r"^[\w.:\-/]+$", re.UNICODE)


class OverridesValidationError(ValueError):
    """payload 不合法；API 映成 400。"""


def empty_payload() -> dict[str, Any]:
    return {
        "schema_version": _SCHEMA_VERSION,
        "module_labels": {},
        "module_hide": [],
        "architecture_labels": {},
        "class_labels": {},
        "class_layout_ref": True,
        "sequence": {"selected_ids": [], "labels": {}},
        "activity": {"selected_ids": [], "labels": {}},
        "usecase": {"labels": {}, "hide": []},
        "usecase_desc": {"selected_ids": [], "cell_overrides": {}},
        "testcases": {"hide": [], "cell_overrides": {}},
        "menu_labels": {},
        "schema_labels": {},
        "er_labels": {},
        "er_view_ref": True,
    }


def _reject_forbidden_key(key: str) -> None:
    k = str(key or "").strip()
    if not k:
        raise OverridesValidationError("空键名")
    if k in _FORBIDDEN_EXACT or any(k.startswith(p) for p in _FORBIDDEN_PREFIX):
        raise OverridesValidationError(f"禁止键: {k}")


def _clean_str_map(raw: Any, *, field: str) -> dict[str, str]:
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise OverridesValidationError(f"{field} 须为对象")
    out: dict[str, str] = {}
    for k, v in raw.items():
        _reject_forbidden_key(str(k))
        key = str(k).strip()
        if not key or not _LABEL_KEY_RE.match(key):
            raise OverridesValidationError(f"{field} 键非法: {k!r}")
        lab = str(v or "").strip().replace("\n", "")
        lab = re.sub(r"\s+", "", lab) if field.startswith("module") else lab
        if not lab:
            continue
        out[key] = lab[:64]
    return out


def _clean_id_list(raw: Any, *, field: str) -> list[str]:
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise OverridesValidationError(f"{field} 须为数组")
    out: list[str] = []
    seen: set[str] = set()
    for item in raw:
        s = str(item or "").strip()
        if not s or s in seen:
            continue
        if not _LABEL_KEY_RE.match(s):
            raise OverridesValidationError(f"{field} 含非法 id: {item!r}")
        seen.add(s)
        out.append(s)
    return out


def _clean_nested_block(raw: Any, *, field: str, shape: str) -> dict[str, Any]:
    if raw is None:
        return empty_payload()[field]  # type: ignore[return-value]
    if not isinstance(raw, dict):
        raise OverridesValidationError(f"{field} 须为对象")
    for k in raw:
        if str(k) not in (
            "selected_ids",
            "labels",
            "hide",
            "cell_overrides",
        ):
            raise OverridesValidationError(f"{field} 未知键: {k}")
        _reject_forbidden_key(str(k))
    if shape == "seq":
        return {
            "selected_ids": _clean_id_list(raw.get("selected_ids"), field=f"{field}.selected_ids"),
            "labels": _clean_str_map(raw.get("labels"), field=f"{field}.labels"),
        }
    if shape == "usecase":
        return {
            "labels": _clean_str_map(raw.get("labels"), field=f"{field}.labels"),
            "hide": _clean_id_list(raw.get("hide"), field=f"{field}.hide"),
        }
    if shape == "cells":
        return {
            "selected_ids": _clean_id_list(
                raw.get("selected_ids"), field=f"{field}.selected_ids"
            )
            if "selected_ids" in raw or field == "usecase_desc"
            else [],
            "hide": _clean_id_list(raw.get("hide"), field=f"{field}.hide")
            if field == "testcases"
            else [],
            "cell_overrides": _clean_str_map(
                raw.get("cell_overrides"), field=f"{field}.cell_overrides"
            ),
        }
    raise OverridesValidationError(f"内部 shape 未知: {shape}")


def sanitize_overrides_payload(data: dict | None) -> dict[str, Any]:
    """校验并规范化 payload；非法抛 OverridesValidationError。"""
    if data is None:
        return empty_payload()
    if not isinstance(data, dict):
        raise OverridesValidationError("payload 须为对象")

    for k in data:
        key = str(k)
        _reject_forbidden_key(key)
        if key not in _ALLOWED_TOP:
            raise OverridesValidationError(f"未知键: {key}")

    ver = data.get("schema_version", _SCHEMA_VERSION)
    try:
        ver_i = int(ver)
    except (TypeError, ValueError) as e:
        raise OverridesValidationError("schema_version 须为整数") from e
    if ver_i != _SCHEMA_VERSION:
        raise OverridesValidationError(f"不支持的 schema_version: {ver_i}")

    base = empty_payload()
    base["module_labels"] = _clean_str_map(
        data.get("module_labels"), field="module_labels"
    )
    base["module_hide"] = _clean_id_list(data.get("module_hide"), field="module_hide")
    base["architecture_labels"] = _clean_str_map(
        data.get("architecture_labels"), field="architecture_labels"
    )
    base["class_labels"] = _clean_str_map(data.get("class_labels"), field="class_labels")
    base["class_layout_ref"] = bool(data.get("class_layout_ref", True))
    base["er_view_ref"] = bool(data.get("er_view_ref", True))
    base["sequence"] = _clean_nested_block(
        data.get("sequence"), field="sequence", shape="seq"
    )
    base["activity"] = _clean_nested_block(
        data.get("activity"), field="activity", shape="seq"
    )
    base["usecase"] = _clean_nested_block(
        data.get("usecase"), field="usecase", shape="usecase"
    )
    ud = _clean_nested_block(
        data.get("usecase_desc"), field="usecase_desc", shape="cells"
    )
    base["usecase_desc"] = {
        "selected_ids": ud.get("selected_ids") or [],
        "cell_overrides": ud.get("cell_overrides") or {},
    }
    tc = _clean_nested_block(data.get("testcases"), field="testcases", shape="cells")
    base["testcases"] = {
        "hide": tc.get("hide") or [],
        "cell_overrides": tc.get("cell_overrides") or {},
    }
    base["menu_labels"] = _clean_str_map(data.get("menu_labels"), field="menu_labels")
    base["schema_labels"] = _clean_str_map(
        data.get("schema_labels"), field="schema_labels"
    )
    er = data.get("er_labels")
    if er is None:
        base["er_labels"] = {}
    elif isinstance(er, dict):
        # 与现网 er_labels 宽松兼容：只拒禁止键，结构留给现有 put
        for k in er:
            _reject_forbidden_key(str(k))
        base["er_labels"] = er
    else:
        raise OverridesValidationError("er_labels 须为对象")

    stale = data.get("_stale")
    if stale is not None:
        if not isinstance(stale, list):
            raise OverridesValidationError("_stale 须为数组")
        base["_stale"] = list(stale)
    return base


def write_overrides_mirror(workspace: Path, payload: dict[str, Any]) -> Path:
    """写入 islands/overrides.json（已 sanitize 的 payload）。"""
    clean = sanitize_overrides_payload(payload)
    path = Path(workspace) / OVERRIDES_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(clean, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return path


def load_overrides_mirror(workspace: Path) -> dict[str, Any] | None:
    path = Path(workspace) / OVERRIDES_REL
    if not path.is_file():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(raw, dict):
        return None
    try:
        return sanitize_overrides_payload(raw)
    except OverridesValidationError:
        return None


def module_labels_flat_to_nodes(flat: dict[str, str] | None) -> dict[str, Any]:
    """DB 扁平 module_labels → 盘上 ``{"nodes": {...}}``。"""
    nodes = {
        str(k).strip(): str(v).strip()
        for k, v in (flat or {}).items()
        if str(k).strip() and str(v).strip()
    }
    return {"nodes": nodes}


def merge_module_label_nodes(
    existing: dict[str, Any] | None, flat_overrides: dict[str, str] | None
) -> dict[str, Any]:
    """与 LLM/已有 nodes merge：同 id 手调覆盖，其它 id 保留。"""
    base_nodes: dict[str, str] = {}
    if isinstance(existing, dict):
        raw = existing.get("nodes") if isinstance(existing.get("nodes"), dict) else existing
        if isinstance(raw, dict):
            for k, v in raw.items():
                if str(k) in ("mode", "nodes"):
                    continue
                ks, vs = str(k).strip(), str(v or "").strip()
                if ks and vs:
                    base_nodes[ks] = vs
    for k, v in (flat_overrides or {}).items():
        ks, vs = str(k).strip(), str(v or "").strip()
        if ks and vs:
            base_nodes[ks] = vs
    return {"nodes": base_nodes}


def collect_module_node_ids(
    workspace: Path,
    *,
    proposal_text: str = "",
) -> set[str]:
    """当前模块树稳定 id（用于失效补丁）。无 schema 则空集。

    与微调表 / 材料图同口径：带开题正文 + ``expand_details=True``。
    """
    from app.bake.schema.modules import build_module_model, iter_nodes

    model = build_module_model(
        Path(workspace),
        with_label_patch=False,
        apply_hide=False,
        expand_details=True,
        proposal_text=proposal_text or "",
    )
    if not model:
        return set()
    return {str(n.get("id") or "").strip() for n in iter_nodes(model) if n.get("id")}


def list_module_nodes_for_overrides_ui(
    workspace: Path,
    *,
    proposal_text: str = "",
) -> list[dict[str, str]]:
    """微调表节点清单：与材料图同树（开题+展开细节）；label/path 用机器原词。"""
    from app.bake.schema.modules import build_module_model

    model = build_module_model(
        Path(workspace),
        with_label_patch=False,
        apply_hide=False,
        expand_details=True,
        proposal_text=proposal_text or "",
    )
    if not model:
        return []
    rows: list[dict[str, str]] = []

    def walk(n: dict, path: str) -> None:
        lab = str(n.get("label") or "").strip()
        nid = str(n.get("id") or "").strip()
        kids = [c for c in (n.get("children") or []) if isinstance(c, dict)]
        here = f"{path}/{lab}" if path else lab
        if nid and nid != "root":
            rows.append(
                {
                    "id": nid,
                    "label": lab,
                    "path": here,
                    "source": str(n.get("source") or ""),
                    "is_leaf": "0" if kids else "1",
                }
            )
        for c in kids:
            walk(c, here)

    root = model.get("root") if isinstance(model.get("root"), dict) else None
    if root:
        # 已在本项目微调页：路径从身份枝起，不重复系统标题
        for c in root.get("children") or []:
            if isinstance(c, dict):
                walk(c, "")
    return rows


def refresh_stale_module_labels(payload: dict[str, Any], live_ids: set[str]) -> dict[str, Any]:
    """module_labels / module_hide 键不在树上 → 挪进 ``_stale``，不糊到其它节点。"""
    clean = sanitize_overrides_payload(payload)
    labels = dict(clean.get("module_labels") or {})
    stale_rows: list[dict[str, Any]] = []
    kept: dict[str, str] = {}
    for kid, lab in labels.items():
        if kid in live_ids:
            kept[kid] = lab
        else:
            stale_rows.append(
                {
                    "key": f"module_labels.{kid}",
                    "node_id": kid,
                    "label": lab,
                    "kind": "module_labels",
                }
            )
    clean["module_labels"] = kept

    hide_kept: list[str] = []
    for hid in clean.get("module_hide") or []:
        hs = str(hid).strip()
        if not hs:
            continue
        if hs in live_ids:
            hide_kept.append(hs)
        else:
            stale_rows.append(
                {
                    "key": f"module_hide.{hs}",
                    "node_id": hs,
                    "label": "",
                    "kind": "module_hide",
                }
            )
    clean["module_hide"] = hide_kept

    prev = clean.get("_stale") if isinstance(clean.get("_stale"), list) else []
    prev_f = [
        x
        for x in prev
        if not (
            isinstance(x, dict)
            and (
                str(x.get("key") or "").startswith("module_labels.")
                or str(x.get("key") or "").startswith("module_hide.")
            )
        )
    ]
    clean["_stale"] = prev_f + stale_rows
    return clean


def apply_overrides_to_workspace(
    workspace: Path,
    payload: dict[str, Any] | None,
    *,
    invalidate_modules: bool = True,
    refresh_stale: bool = True,
    proposal_text: str = "",
) -> dict[str, Any]:
    """写 overrides 镜像 + 合并模块短签到 ``module_labels.json``；可选标失效键。

    返回规范化后的 payload（含 ``_stale``）。
    ``proposal_text`` 须与材料图同源，否则身份叶 id 对不齐、会误标失效。
    """
    from app.bake.schema.modules import (
        load_module_label_patch,
        save_module_label_patch,
    )

    ws = Path(workspace)
    clean = sanitize_overrides_payload(payload)
    if refresh_stale:
        live = collect_module_node_ids(ws, proposal_text=proposal_text)
        if live:
            clean = refresh_stale_module_labels(clean, live)

    # 写镜像前记下旧手调键：空=跟机器时须从 module_labels.json 删掉，不能只靠 merge 加法
    prev_mirror = load_overrides_mirror(ws)
    prev_hand = {
        str(k).strip()
        for k in ((prev_mirror or {}).get("module_labels") or {})
        if str(k).strip()
    }

    write_overrides_mirror(ws, clean)

    flat = clean.get("module_labels") if isinstance(clean.get("module_labels"), dict) else {}
    flat = {str(k).strip(): str(v).strip() for k, v in flat.items() if str(k).strip() and str(v).strip()}
    # 即使 flat 空也要跑：清掉上一版手调键，保留 LLM 等其它 nodes
    if flat or prev_hand:
        existing = load_module_label_patch(ws)
        merged = merge_module_label_nodes(existing, flat)
        nodes: dict[str, str] = {}
        for k, v in (merged.get("nodes") or {}).items():
            ks = str(k).strip()
            lab = str(v or "").strip().replace("\n", "")
            lab = re.sub(r"\s+", "", lab)
            if not ks or not lab:
                continue
            # 曾手调、本次 payload 已去掉 → 跟机器（删键）
            if ks in prev_hand and ks not in flat:
                continue
            # 手调允许「AI客服」等拉丁混中文；勿走 sanitize 的 looks_latin 静默丢弃。
            # 过长/散文仍由 label_gate 红（与现网统一）。
            nodes[ks] = lab[:16]
        save_module_label_patch(ws, {"nodes": nodes})

    # P2：菜单 / schema.labels 只改显示字符串
    apply_menu_schema_label_overrides(ws, clean)

    if invalidate_modules:
        from app.bake.schema.diagram_cache import invalidate as invalidate_diagram_cache

        # 按相对上一份镜像的变更失效；勿每次保存都刷 classes（旧钉坐标 + 新框高会糊）
        kinds = {"modules"}
        prev = prev_mirror or {}

        def _changed(key: str) -> bool:
            return prev.get(key) != clean.get(key)

        if _changed("sequence"):
            kinds.add("sequences")
        if _changed("activity"):
            kinds.add("activities")
        if _changed("architecture_labels"):
            kinds.add("architecture")
        if _changed("usecase"):
            kinds.add("usecases")
        if (
            _changed("class_labels")
            or _changed("menu_labels")
            or _changed("schema_labels")
        ):
            kinds.add("classes")
        for kind in kinds:
            invalidate_diagram_cache(ws, kind)

    return clean


def apply_class_label_overrides(
    model: dict[str, Any], labels: dict[str, str] | None
) -> dict[str, Any]:
    """``class_labels``：按类稳定名（Java 名 / 表名）盖中文显示名，不改坐标。"""
    if not labels or not isinstance(model, dict):
        return model
    classes = model.get("classes")
    if not isinstance(classes, list):
        return model
    out: list[dict[str, Any]] = []
    for c in classes:
        if not isinstance(c, dict):
            out.append(c)
            continue
        row = dict(c)
        name = str(row.get("name") or "").strip()
        table = str(row.get("table") or "").strip()
        for key in (name, table):
            if key and key in labels and str(labels[key]).strip():
                row["label"] = str(labels[key]).strip()[:32]
                break
        out.append(row)
    model = dict(model)
    model["classes"] = out
    return model


def resolve_override_selection(
    workspace: Path, section: str
) -> list[str] | None:
    """读镜像里 sequence/activity/usecase_desc 的 selected_ids；无则 None。"""
    mirror = load_overrides_mirror(workspace)
    if not mirror:
        return None
    block = mirror.get(section)
    if not isinstance(block, dict):
        return None
    ids = block.get("selected_ids")
    if not isinstance(ids, list):
        return None
    out = [str(x).strip() for x in ids if str(x).strip()]
    return out or None


def override_labels_map(workspace: Path, section: str) -> dict[str, str]:
    mirror = load_overrides_mirror(workspace)
    if not mirror:
        return {}
    block = mirror.get(section)
    if not isinstance(block, dict):
        return {}
    labels = block.get("labels")
    return dict(labels) if isinstance(labels, dict) else {}


def apply_sequence_label_overrides(
    model: dict[str, Any], labels: dict[str, str] | None
) -> dict[str, Any]:
    """叠短签：``{diagramId}::p:{participantId}`` / ``{diagramId}::m:{seq}``。"""
    if not labels or not isinstance(model, dict):
        return model
    for d in model.get("diagrams") or []:
        if not isinstance(d, dict):
            continue
        did = str(d.get("id") or "").strip()
        if not did:
            continue
        for p in d.get("participants") or []:
            if not isinstance(p, dict):
                continue
            pid = str(p.get("id") or "").strip()
            key = f"{did}::p:{pid}"
            if key in labels and str(labels[key]).strip():
                p["label"] = str(labels[key]).strip()[:32]
                if pid == "actor":
                    d["actor_label"] = p["label"]
        for m in d.get("messages") or []:
            if not isinstance(m, dict):
                continue
            seq = m.get("seq")
            key = f"{did}::m:{seq}"
            if key in labels and str(labels[key]).strip():
                m["text"] = str(labels[key]).strip()[:48]
    return model


def apply_activity_label_overrides(
    model: dict[str, Any], labels: dict[str, str] | None
) -> dict[str, Any]:
    """叠短签：``{diagramId}::n:{nodeId}`` / ``{diagramId}::g:{from}_{to}``（菱形旁条件）。"""
    if not labels or not isinstance(model, dict):
        return model
    for d in model.get("diagrams") or []:
        if not isinstance(d, dict):
            continue
        did = str(d.get("id") or "").strip()
        if not did:
            continue
        for n in d.get("nodes") or []:
            if not isinstance(n, dict):
                continue
            nid = str(n.get("id") or "").strip()
            key = f"{did}::n:{nid}"
            if key in labels and str(labels[key]).strip():
                n["text"] = str(labels[key]).strip()[:32]
        for e in d.get("edges") or []:
            if not isinstance(e, dict):
                continue
            frm = str(e.get("from") or "").strip()
            to = str(e.get("to") or "").strip()
            key = f"{did}::g:{frm}_{to}"
            if key in labels and str(labels[key]).strip():
                e["guard"] = str(labels[key]).strip()[:16]
    return model


def apply_usecase_desc_cell_overrides(
    model: dict[str, Any], cell_overrides: dict[str, str] | None
) -> dict[str, Any]:
    """单元格：``{stableId}.name|actor|summary`` / ``{stableId}.flow.{i}``。"""
    if not cell_overrides or not isinstance(model, dict):
        return model
    for case in model.get("cases") or []:
        if not isinstance(case, dict):
            continue
        sid = str(case.get("stable_id") or case.get("id") or "").strip()
        if not sid:
            continue
        for field in ("name", "actor", "summary"):
            key = f"{sid}.{field}"
            if key in cell_overrides and str(cell_overrides[key]).strip():
                case[field] = str(cell_overrides[key]).strip()
        flow = case.get("flow")
        if isinstance(flow, list):
            new_flow = list(flow)
            changed = False
            for i in range(len(new_flow)):
                key = f"{sid}.flow.{i}"
                if key in cell_overrides and str(cell_overrides[key]).strip():
                    new_flow[i] = str(cell_overrides[key]).strip()
                    changed = True
            if changed:
                case["flow"] = new_flow
    # 重算 markdown
    if model.get("cases"):
        from app.bake.schema.usecase_descriptions import (
            render_usecase_description_markdown,
        )

        model["markdown"] = render_usecase_description_markdown(
            title=str(model.get("title") or ""),
            cases=list(model.get("cases") or []),
            table_start=str(model.get("table_start") or "3.1"),
        )
        names = [str(c.get("name") or "") for c in (model.get("cases") or []) if isinstance(c, dict)]
        if names:
            model["intro"] = (
                f"由于内容篇幅限制，本次仅针对{'、'.join(names)}这{len(names)}个用例进行阐述。"
            )
    return model


def apply_architecture_label_overrides(
    model: dict[str, Any], labels: dict[str, str] | None
) -> dict[str, Any]:
    """``architecture_labels``：角色 id / 层 id → 显示名。"""
    if not labels or not isinstance(model, dict):
        return model
    for r in model.get("roles") or []:
        if not isinstance(r, dict):
            continue
        rid = str(r.get("id") or "").strip()
        if rid in labels and str(labels[rid]).strip():
            r["label"] = str(labels[rid]).strip()[:32]
    for layer in model.get("layers") or []:
        if not isinstance(layer, dict):
            continue
        lid = str(layer.get("id") or "").strip()
        if lid in labels and str(labels[lid]).strip():
            layer["label"] = str(labels[lid]).strip()[:32]
    for key in ("protocol_label", "action_label"):
        if key in labels and str(labels[key]).strip():
            model[key] = str(labels[key]).strip()[:32]
    return model


def apply_usecase_diagram_overrides(
    model: dict[str, Any],
    *,
    labels: dict[str, str] | None = None,
    hide: list[str] | None = None,
) -> dict[str, Any]:
    """用例图：改 actor/用例短签；hide 去掉图面节点（不改菜单）。"""
    if not isinstance(model, dict):
        return model
    labels = labels or {}
    hide_set = {str(x).strip() for x in (hide or []) if str(x).strip()}

    actor = model.get("actor")
    if isinstance(actor, dict):
        aid = str(actor.get("id") or "").strip()
        if aid and f"actor:{aid}" in labels and str(labels[f"actor:{aid}"]).strip():
            actor["label"] = str(labels[f"actor:{aid}"]).strip()[:32]
        elif aid and aid in labels and str(labels[aid]).strip():
            actor["label"] = str(labels[aid]).strip()[:32]

    def map_node(n: dict[str, Any]) -> dict[str, Any] | None:
        nid = str(n.get("id") or "").strip()
        if nid and nid in hide_set:
            return None
        out = dict(n)
        if nid and nid in labels and str(labels[nid]).strip():
            out["label"] = str(labels[nid]).strip()[:32]
        # 现网字段名为 includes（二级用例）
        kids = out.get("includes")
        if isinstance(kids, list) and kids:
            kept = []
            for c in kids:
                if isinstance(c, dict):
                    pruned = map_node(c)
                    if pruned is not None:
                        kept.append(pruned)
            if kept:
                out["includes"] = kept
            else:
                out.pop("includes", None)
        return out

    level1 = model.get("level1")
    if isinstance(level1, list):
        new_l1: list[dict[str, Any]] = []
        for n in level1:
            if not isinstance(n, dict):
                continue
            pruned = map_node(n)
            if pruned is not None:
                new_l1.append(pruned)
        model = dict(model)
        model["level1"] = new_l1
    return model


def apply_testcase_overrides(
    model: dict[str, Any],
    *,
    hide: list[str] | None = None,
    cell_overrides: dict[str, str] | None = None,
) -> dict[str, Any]:
    """测例：藏行 + ``{caseId}.{field}`` 单元格覆盖。"""
    if not isinstance(model, dict):
        return model
    hide_set = {str(x).strip() for x in (hide or []) if str(x).strip()}
    cells = cell_overrides or {}
    rows = model.get("rows")
    if not isinstance(rows, list):
        return model
    out_rows: list[dict[str, Any]] = []
    for r in rows:
        if not isinstance(r, dict):
            continue
        cid = str(r.get("id") or "").strip()
        if cid and cid in hide_set:
            continue
        row = dict(r)
        if cid:
            for k, v in list(row.items()):
                key = f"{cid}.{k}"
                if key in cells and str(cells[key]).strip():
                    row[k] = str(cells[key]).strip()
        out_rows.append(row)
    model = dict(model)
    model["rows"] = out_rows
    return model


def apply_menu_schema_label_overrides(
    workspace: Path, payload: dict[str, Any] | None
) -> None:
    """只改 ``domain.schema.json``（及 public 镜像）里的菜单 title / labels 显示串。"""
    clean = sanitize_overrides_payload(payload)
    menu_labels = clean.get("menu_labels") if isinstance(clean.get("menu_labels"), dict) else {}
    schema_labels = (
        clean.get("schema_labels") if isinstance(clean.get("schema_labels"), dict) else {}
    )
    if not menu_labels and not schema_labels:
        return

    ws = Path(workspace)
    schema_path = ws / "domain.schema.json"
    if not schema_path.is_file():
        return
    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return
    if not isinstance(schema, dict):
        return

    changed = False
    if schema_labels:
        labels = schema.get("labels") if isinstance(schema.get("labels"), dict) else {}
        labels = dict(labels)
        for k, v in schema_labels.items():
            ks, vs = str(k).strip(), str(v or "").strip()
            if ks and vs:
                labels[ks] = vs[:64]
                changed = True
        schema["labels"] = labels

    if menu_labels:
        menus = schema.get("menus") if isinstance(schema.get("menus"), dict) else {}
        menus = dict(menus)
        for side, items in list(menus.items()):
            if not isinstance(items, list):
                continue
            new_items = []
            for it in items:
                if not isinstance(it, dict):
                    new_items.append(it)
                    continue
                row = dict(it)
                key = str(row.get("key") or "").strip()
                if key and key in menu_labels and str(menu_labels[key]).strip():
                    lab = str(menu_labels[key]).strip()[:32]
                    row["label"] = lab
                    if "title" in row:
                        row["title"] = lab
                    changed = True
                new_items.append(row)
            menus[side] = new_items
        schema["menus"] = menus

    if not changed:
        return

    text = json.dumps(schema, ensure_ascii=False, indent=2)
    schema_path.write_text(text, encoding="utf-8")
    public = ws / "frontend" / "public" / "domain.schema.json"
    if public.parent.is_dir():
        public.write_text(text, encoding="utf-8")
