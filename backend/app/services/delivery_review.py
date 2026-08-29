"""交付复审：缩圈验收入口、单调性、合卷与运营交接（不进学生 ZIP）。"""

from __future__ import annotations

import hashlib
import io
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.bake.gates import evaluate_domain_gates
from app.bake.gates.keys import GATE_MONOTONE_KEYS
from app.models import Project
from app.services.proposal import load_merged_proposal_text

_HASH_ROOTS = (
    "backend/src",
    "frontend/src",
    "sql",
    "README.md",
    "frontend/package.json",
    "backend/pom.xml",
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def empty_review_state() -> dict[str, Any]:
    """公开：交付复审初始态（jobs 重置时共用）。"""
    return _empty_state()


def _empty_state() -> dict[str, Any]:
    return {
        "status": "idle",
        "round": 0,
        "frozen_checklist": [],
        "frozen_gates": {},
        "fix_notes": [],
        "rounds": [],
        "workspace_hash_at_pack": "",
        "last_qa": None,
        "last_verify": None,
        "pre_generate_ack_at": None,
        "first_pack_at": None,
        "first_pack_direct": None,
        "review_entered_at": None,
        "repack_count": 0,
    }


def get_review_state(project: Project) -> dict[str, Any]:
    raw = getattr(project, "delivery_review", None)
    if not isinstance(raw, dict) or not raw:
        return _empty_state()
    st = _empty_state()
    st.update(raw)
    return st


def save_review_state(project: Project, state: dict[str, Any]) -> None:
    project.delivery_review = state
    try:
        from sqlalchemy.orm.attributes import flag_modified

        flag_modified(project, "delivery_review")
    except Exception:  # noqa: BLE001
        pass


def review_status_of(project: Project) -> str:
    """列表履约细分：idle | active | closed。"""
    status = str(get_review_state(project).get("status") or "idle")
    return status if status in ("idle", "active", "closed") else "idle"


def workspace_delivery_hash(workspace: Path) -> str:
    """交付树内容指纹（不含 node_modules / target）。"""
    h = hashlib.sha256()
    if not workspace.is_dir():
        return ""
    files: list[Path] = []
    for rel in _HASH_ROOTS:
        p = workspace / rel
        if p.is_file():
            files.append(p)
        elif p.is_dir():
            for f in sorted(p.rglob("*")):
                if not f.is_file():
                    continue
                if set(f.parts) & {"node_modules", "target", ".git", "islands"}:
                    continue
                files.append(f)
    for path in sorted(files, key=lambda x: x.relative_to(workspace).as_posix()):
        rel = path.relative_to(workspace).as_posix()
        h.update(rel.encode("utf-8"))
        try:
            h.update(path.read_bytes())
        except OSError:
            h.update(b"<read_error>")
    return h.hexdigest()[:24]


def is_zip_stale(project: Project, workspace: Path | None = None) -> bool:
    st = get_review_state(project)
    packed = str(st.get("workspace_hash_at_pack") or "")
    if not packed:
        return False
    ws = workspace
    if ws is None:
        if not project.workspace_path:
            return False
        ws = Path(project.workspace_path)
    if not ws.is_dir():
        return False
    return workspace_delivery_hash(ws) != packed


def checklist_done_names(checklist: list[Any]) -> list[str]:
    out: list[str] = []
    for item in checklist or []:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        if not name:
            continue
        if item.get("result") == "done":
            out.append(name)
    return out


def gates_ok_keys(gates: dict[str, Any]) -> dict[str, bool]:
    out: dict[str, bool] = {}
    for k in GATE_MONOTONE_KEYS:
        item = gates.get(k)
        if isinstance(item, dict):
            out[k] = bool(item.get("ok"))
    return out


def compare_monotonic(
    *,
    prev_checklist: list[Any],
    new_checklist: list[Any],
    prev_gates: dict[str, Any],
    new_gates: dict[str, Any],
    frozen_checklist: list[str] | None = None,
    frozen_gates: dict[str, bool] | None = None,
) -> tuple[bool, list[dict[str, str]]]:
    """检测安全区是否回退（done→pending、gate ok→fail）。"""
    regressions: list[dict[str, str]] = []
    prev_done = set(checklist_done_names(prev_checklist))
    prev_done.update(frozen_checklist or [])
    new_map = {
        str(x.get("name") or ""): x
        for x in (new_checklist or [])
        if isinstance(x, dict)
    }
    for name in sorted(prev_done):
        cur = new_map.get(name) or {}
        if cur.get("result") != "done":
            regressions.append(
                {
                    "kind": "checklist",
                    "key": name,
                    "message": f"清单实装项「{name}」由已通过回退为未通过",
                }
            )

    prev_ok = gates_ok_keys(prev_gates)
    prev_ok.update({k: v for k, v in (frozen_gates or {}).items() if v})
    new_ok = gates_ok_keys(new_gates)
    for key, was_ok in prev_ok.items():
        if was_ok and not new_ok.get(key):
            label = (prev_gates.get(key) or {}).get("label") or key
            regressions.append(
                {
                    "kind": "gate",
                    "key": key,
                    "message": f"质量检查项「{label}」由已通过回退为未通过",
                }
            )
    return (len(regressions) == 0, regressions)


def partition_zones(
    checklist: list[Any],
    fix_notes: list[Any],
    frozen_checklist: list[str],
) -> dict[str, Any]:
    frozen = set(frozen_checklist or [])
    safe: list[dict[str, Any]] = []
    poison: list[dict[str, Any]] = []
    for item in checklist or []:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "")
        row = dict(item)
        if item.get("result") == "done" or name in frozen:
            safe.append(row)
        elif item.get("result") != "out_of_mvp":
            poison.append(row)
    open_notes = [
        n for n in (fix_notes or [])
        if isinstance(n, dict) and str(n.get("status") or "open") == "open"
    ]
    return {"safe_zone": safe, "poison_zone": poison, "open_notes": open_notes}


def apply_qa_to_gates(
    gates: dict[str, Any],
    qa: dict[str, Any] | None,
    *,
    warn_blocks: bool | None = None,
) -> None:
    if not isinstance(qa, dict):
        return
    from app.core.config import get_settings

    if warn_blocks is None:
        warn_blocks = bool(get_settings().gf_qa_warn_blocks_pack)
    findings = [f for f in (qa.get("findings") or []) if isinstance(f, dict)]
    err_n = len([f for f in findings if f.get("level") == "error"])
    warn_n = len([f for f in findings if f.get("level") == "warn"])
    ok = bool(qa.get("ok")) and err_n == 0 and (not warn_blocks or warn_n == 0)
    desc = str(qa.get("summary") or "")[:240]
    if not desc:
        if ok:
            desc = "无 error 级问题" + ("" if not warn_n else f" · {warn_n} 项 warn（未挡包）")
        else:
            parts = []
            if err_n:
                parts.append(f"{err_n} 项 error")
            if warn_blocks and warn_n:
                parts.append(f"{warn_n} 项 warn")
            desc = " · ".join(parts) or "质量摘要未通过"
    gates["p3q"] = {
        "ok": ok,
        "label": "交付质量摘要",
        "desc": desc,
        "detail": {
            "mode": qa.get("mode"),
            "error_count": err_n,
            "warn_count": warn_n,
            "warn_blocks": warn_blocks,
            "findings": findings[:12],
        },
    }
    if not ok:
        gates["zip_allowed"] = False
        gates["overall"] = False


def evaluate_workspace_gates(workspace: Path, spec: dict[str, Any]) -> dict[str, Any]:
    """与 evaluate_domain_gates 同口径（p3s 已在 gate 入口合并）。"""
    return evaluate_domain_gates(workspace, spec)


def open_fix_notes(st: dict[str, Any] | None) -> list[dict[str, Any]]:
    return [
        n
        for n in (st or {}).get("fix_notes") or []
        if isinstance(n, dict) and str(n.get("status") or "open") == "open"
    ]


def can_repack_after_verify(verify_result: dict[str, Any], review_state: dict[str, Any]) -> tuple[bool, str]:
    if not verify_result.get("monotonic_ok"):
        return False, "检测到安全区回退 · 请先修复后再合卷"
    if open_fix_notes(review_state):
        return False, "仍有未结案的复审偏差登记 · 请先处理或结案"
    if not verify_result.get("round_pass"):
        return False, "仍有待收敛项或未通过质量检查 · 请先验圈通过"
    return True, ""


def record_first_pack(project: Project) -> None:
    st = get_review_state(project)
    if st.get("first_pack_at"):
        return
    st["first_pack_at"] = _utc_now()
    st["first_pack_direct"] = st.get("status") != "active" and not st.get("review_entered_at")
    save_review_state(project, st)


def record_repack(project: Project) -> None:
    st = get_review_state(project)
    st["repack_count"] = int(st.get("repack_count") or 0) + 1
    if st.get("first_pack_direct") is not False:
        st["first_pack_direct"] = False
    save_review_state(project, st)


def ack_pre_generate(project: Project) -> dict[str, Any]:
    st = get_review_state(project)
    st["pre_generate_ack_at"] = _utc_now()
    save_review_state(project, st)
    return st


def pre_generate_acked(project: Project) -> bool:
    st = get_review_state(project)
    return bool(st.get("pre_generate_ack_at"))


def has_proposal_material(project: Project) -> bool:
    return bool(project.source_path or getattr(project, "source_filename", None))


def require_pre_generate_ack(project: Project) -> str | None:
    """有开题材料时须先确认 proposal-diff。"""
    if not has_proposal_material(project):
        return None
    if pre_generate_acked(project):
        return None
    return "请先查看并确认「开题措辞核对」后再一键生成"


def start_review(project: Project) -> dict[str, Any]:
    st = get_review_state(project)
    if st.get("status") == "active":
        return st
    checklist = project.checklist if isinstance(project.checklist, list) else []
    gates = project.gates if isinstance(project.gates, dict) else {}
    st["status"] = "active"
    st["round"] = max(int(st.get("round") or 0), 1)
    st["frozen_checklist"] = checklist_done_names(checklist)
    st["frozen_gates"] = gates_ok_keys(gates)
    st["started_at"] = _utc_now()
    if not st.get("review_entered_at"):
        st["review_entered_at"] = st["started_at"]
    if st.get("first_pack_direct") is not False:
        st["first_pack_direct"] = False
    save_review_state(project, st)
    return st


def close_review(project: Project) -> dict[str, Any]:
    st = get_review_state(project)
    st["status"] = "closed"
    st["closed_at"] = _utc_now()
    save_review_state(project, st)
    return st


def add_fix_note(project: Project, text: str) -> dict[str, Any]:
    st = get_review_state(project)
    note = {
        "id": hashlib.sha1(f"{text}{_utc_now()}".encode()).hexdigest()[:10],
        "text": text.strip()[:500],
        "status": "open",
        "created_at": _utc_now(),
    }
    notes = list(st.get("fix_notes") or [])
    notes.append(note)
    st["fix_notes"] = notes[-40:]
    if st.get("status") == "idle":
        start_review(project)
        st = get_review_state(project)
        st["fix_notes"] = notes[-40:]
    save_review_state(project, st)
    return note


def resolve_fix_note(project: Project, note_id: str, *, done: bool = True) -> bool:
    st = get_review_state(project)
    changed = False
    for n in st.get("fix_notes") or []:
        if isinstance(n, dict) and n.get("id") == note_id:
            n["status"] = "done" if done else "open"
            n["resolved_at"] = _utc_now() if done else None
            changed = True
    if changed:
        save_review_state(project, st)
    return changed


def verify_round(
    project: Project,
    workspace: Path,
    *,
    prev_checklist: list[Any] | None = None,
    prev_gates: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """重跑门禁 + 单调性；更新 project gates/checklist。"""
    spec = dict(project.spec or {})
    st = get_review_state(project)
    gates = evaluate_workspace_gates(workspace, spec)
    last_qa = st.get("last_qa")
    if isinstance(last_qa, dict) and last_qa:
        apply_qa_to_gates(gates, last_qa)
    checklist = gates.pop("checklist", []) or []

    if st.get("status") != "active":
        start_review(project)
        st = get_review_state(project)

    prev_cl = prev_checklist if prev_checklist is not None else (st.get("last_verify") or {}).get(
        "checklist"
    ) or project.checklist
    prev_g = prev_gates if prev_gates is not None else (st.get("last_verify") or {}).get("gates") or (
        project.gates or {}
    )

    mono_ok, regressions = compare_monotonic(
        prev_checklist=prev_cl or [],
        new_checklist=checklist,
        prev_gates=prev_g or {},
        new_gates=gates,
        frozen_checklist=list(st.get("frozen_checklist") or []),
        frozen_gates=dict(st.get("frozen_gates") or {}),
    )

    ws_hash = workspace_delivery_hash(workspace)
    poison_pending = [
        x for x in checklist
        if isinstance(x, dict) and x.get("result") not in ("done", "out_of_mvp")
    ]
    open_notes = open_fix_notes(st)
    round_pass = (
        mono_ok
        and gates.get("zip_allowed")
        and not poison_pending
        and not open_notes
    )

    if mono_ok and gates.get("zip_allowed"):
        done_names = set(st.get("frozen_checklist") or [])
        done_names.update(checklist_done_names(checklist))
        st["frozen_checklist"] = sorted(done_names)
        ok_g = dict(st.get("frozen_gates") or {})
        ok_g.update({k: v for k, v in gates_ok_keys(gates).items() if v})
        st["frozen_gates"] = ok_g

    st["round"] = int(st.get("round") or 0) + 1
    round_rec = {
        "round": st["round"],
        "at": _utc_now(),
        "monotonic_ok": mono_ok,
        "regressions": regressions,
        "gates_ok": bool(gates.get("overall")),
        "zip_allowed": bool(gates.get("zip_allowed")),
        "pending_count": len(poison_pending),
        "open_notes_count": len(open_notes),
        "workspace_hash": ws_hash,
        "round_pass": round_pass,
    }
    rounds = list(st.get("rounds") or [])
    rounds.append(round_rec)
    st["rounds"] = rounds[-30:]
    st["last_verify"] = {
        "at": round_rec["at"],
        "checklist": checklist,
        "gates": {k: v for k, v in gates.items() if k != "checklist"},
        "monotonic_ok": mono_ok,
        "regressions": regressions,
        "workspace_hash": ws_hash,
    }
    save_review_state(project, st)

    project.gates = {k: v for k, v in gates.items() if k != "checklist"}
    project.checklist = checklist

    zones = partition_zones(checklist, st.get("fix_notes") or [], st.get("frozen_checklist") or [])

    return {
        "round": round_rec,
        "gates": project.gates,
        "checklist": checklist,
        "monotonic_ok": mono_ok,
        "regressions": regressions,
        "round_pass": round_pass,
        "open_notes_count": len(open_notes),
        "zones": zones,
        "zip_stale": is_zip_stale(project, workspace),
        "review": st,
    }


def finalize_pack(
    project: Project,
    workspace: Path,
    zip_path: Path,
    *,
    is_repack: bool = False,
) -> dict[str, Any]:
    """打 ZIP 并记 workspace 指纹；首包与合卷共用。"""
    from app.services.jobs import pack_zip

    pack_zip(workspace, zip_path)
    ws_hash = workspace_delivery_hash(workspace)
    if is_repack:
        record_repack(project)
    else:
        record_first_pack(project)
    st = get_review_state(project)
    st["workspace_hash_at_pack"] = ws_hash
    st["last_pack_at"] = _utc_now()
    save_review_state(project, st)
    return {"workspace_hash": ws_hash, "zip_path": str(zip_path)}


def repack_project(project: Project, workspace: Path, zip_path: Path) -> dict[str, Any]:
    """合卷：复审场景下的重打包。"""
    return finalize_pack(project, workspace, zip_path, is_repack=True)


def forbid_full_rebake(project: Project, from_step: int) -> int | None:
    """复审进行中禁止 bake/填岛重跑；仅允许 gate/pack 步（4+）。返回 None = 应拒绝启动。"""
    st = get_review_state(project)
    if st.get("status") != "active":
        return from_step
    if from_step <= 3:
        return None
    return from_step


def build_review_payload(project: Project, workspace: Path | None = None) -> dict[str, Any]:
    st = get_review_state(project)
    checklist = project.checklist if isinstance(project.checklist, list) else []
    zones = partition_zones(checklist, st.get("fix_notes") or [], st.get("frozen_checklist") or [])
    ws = workspace
    stale = False
    cur_hash = ""
    if ws and ws.is_dir():
        cur_hash = workspace_delivery_hash(ws)
        stale = is_zip_stale(project, ws)
    return {
        "review": st,
        "zones": zones,
        "workspace_hash": cur_hash,
        "zip_stale": stale,
        "checklist": checklist,
        "gates": project.gates or {},
        "metrics": {
            "first_pack_at": st.get("first_pack_at"),
            "first_pack_direct": st.get("first_pack_direct"),
            "review_entered_at": st.get("review_entered_at"),
            "repack_count": int(st.get("repack_count") or 0),
            "pre_generate_ack_at": st.get("pre_generate_ack_at"),
        },
    }


def build_operator_handoff_zip(project: Project, workspace: Path | None) -> bytes:
    """运营交接包：材料 + 对照 + 复审记录（不进学生交付 ZIP）。"""
    spec = dict(project.spec or {})
    proposal = ""
    if project.source_path:
        try:
            proposal = load_merged_proposal_text(project.source_path)
        except Exception:  # noqa: BLE001
            proposal = ""
    payload = {
        "project_id": project.id,
        "title": project.title,
        "exported_at": _utc_now(),
        "checklist": project.checklist,
        "gates": project.gates,
        "delivery_review": get_review_state(project),
        "spec": spec,
    }
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("handoff/checklist.json", json.dumps(project.checklist, ensure_ascii=False, indent=2))
        zf.writestr("handoff/gates.json", json.dumps(project.gates, ensure_ascii=False, indent=2))
        zf.writestr("handoff/spec.json", json.dumps(spec, ensure_ascii=False, indent=2))
        zf.writestr(
            "handoff/delivery_review.json",
            json.dumps(get_review_state(project), ensure_ascii=False, indent=2),
        )
        if proposal:
            zf.writestr("handoff/merged_proposal.txt", proposal)
        zf.writestr("handoff/manifest.json", json.dumps(payload, ensure_ascii=False, indent=2))
        qa_path = workspace / "islands" / "qa_report.json" if workspace else None
        if qa_path and qa_path.is_file():
            zf.write(qa_path, "handoff/qa_report.json")
    return buf.getvalue()
