"""后台对账成本：投影输入签名跳过未变项目 + 每轮重算额度（不饿死、可轮转）。

背景：`evaluate_domain_gates` 单项目 110~180ms，此前每 20s TTL 到期后无条件重扫；
工作区没动也照扫，项目一多后台线程就长期占着磁盘。签名只走查 size+mtime（不读文件内容）
实测 ≈18~20ms/项目，未变即跳过重算；额度再把长突发摊到多轮。
"""

from __future__ import annotations

from contextlib import ExitStack
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from app.services import projects as project_svc

FAKE_GATES = {
    "overall": True,
    "zip_allowed": True,
    "p0a": {"ok": True, "label": "结构"},
    "checklist": [],
}


def _project(tmp_path: Path, pid: str = "p1", **over) -> SimpleNamespace:
    ws = tmp_path / pid
    ws.mkdir(exist_ok=True)
    (ws / "README.md").write_text(f"# {pid}", encoding="utf-8")
    data: dict = {
        "id": pid,
        "status": "generated",
        "workspace_path": str(ws),
        "zip_ready": False,
        "gates": {},
        "zip_path": "",
        "delivery_mark": "none",
        "checklist": [],
        "spec": {},
        "delivery_review": {},
    }
    data.update(over)
    return SimpleNamespace(**data)


def _reconcile(items, *, max_scans=None, settings=None):
    """跑一轮对账，返回 (dirty, 本轮真正重算过的项目名)。"""
    scanned: list[str] = []

    def _gates(workspace, spec):  # noqa: ANN001
        scanned.append(Path(workspace).name)
        return dict(FAKE_GATES)

    with ExitStack() as stack:
        stack.enter_context(
            patch("app.services.project_projection.evaluate_domain_gates", side_effect=_gates)
        )
        stack.enter_context(
            patch(
                "app.services.project_projection.sync_project_runtime",
                return_value=("stopped", "stopped", False),
            )
        )
        if settings is not None:
            stack.enter_context(
                patch("app.services.project_projection.get_settings", return_value=settings)
            )
        dirty = project_svc.reconcile_list_items(items, max_scans=max_scans)
    return dirty, scanned


def test_signature_skips_rescan_when_nothing_changed(tmp_path):
    """TTL 到期但投影输入没变：不再重扫工作区（首页变慢的那部分真省下来）。"""
    p = _project(tmp_path)
    project_svc.reset_checklist_list_cache()
    with patch("app.services.project_projection._CHECKLIST_LIST_TTL_SEC", 0.0):
        _, first = _reconcile([p])
        _, second = _reconcile([p])
        _, third = _reconcile([p])
    assert first == ["p1"]  # 首轮（冷签名）照常重算
    assert second == []  # 签名未变 → 跳过
    assert third == []


def test_signature_recomputes_when_workspace_changed(tmp_path):
    """工程文件变了（新增/改动源码）→ 签名变 → 恢复重算。"""
    p = _project(tmp_path)
    ws = Path(p.workspace_path)
    project_svc.reset_checklist_list_cache()
    with patch("app.services.project_projection._CHECKLIST_LIST_TTL_SEC", 0.0):
        _, first = _reconcile([p])
        (ws / "src").mkdir()
        (ws / "src" / "App.java").write_text("class App {}", encoding="utf-8")
        _, second = _reconcile([p])
        (ws / "src" / "App.java").write_text("class App { int x; }", encoding="utf-8")
        _, third = _reconcile([p])
    assert first == ["p1"]
    assert second == ["p1"]
    assert third == ["p1"]


def test_signature_recomputes_when_review_state_changed(tmp_path):
    """只改复审态（工作区没动）也必须重算：投影要把 last_qa 重挂到 gates。"""
    p = _project(tmp_path)
    project_svc.reset_checklist_list_cache()
    with patch("app.services.project_projection._CHECKLIST_LIST_TTL_SEC", 0.0):
        _, first = _reconcile([p])
        p.delivery_review = {"status": "active", "last_qa": {"p3q": {"ok": True}}}
        _, second = _reconcile([p])
    assert first == ["p1"]
    assert second == ["p1"]


def test_scan_budget_rotates_without_starving(tmp_path):
    """额度=1、三个项目都要重算：逐轮轮到「最久未扫」的那个，三轮全覆盖。"""
    items = [_project(tmp_path, pid=f"p{i}") for i in (1, 2, 3)]
    project_svc.reset_checklist_list_cache()
    with patch("app.services.project_projection._CHECKLIST_LIST_TTL_SEC", 0.0):
        _, first = _reconcile(items, max_scans=1)
        _, second = _reconcile(items, max_scans=1)
        _, third = _reconcile(items, max_scans=1)
    assert first == ["p1"]
    assert second == ["p2"]
    assert third == ["p3"]


def test_scan_budget_zero_means_unlimited(tmp_path):
    items = [_project(tmp_path, pid=f"p{i}") for i in (1, 2)]
    project_svc.reset_checklist_list_cache()
    _, scanned = _reconcile(items, max_scans=0)
    assert sorted(scanned) == ["p1", "p2"]


def test_scan_budget_defaults_to_settings(tmp_path):
    """不传 max_scans 时读 GF_RECONCILE_SCAN_PER_PASS。"""
    items = [_project(tmp_path, pid=f"p{i}") for i in (1, 2, 3)]
    project_svc.reset_checklist_list_cache()
    _, scanned = _reconcile(
        items, settings=SimpleNamespace(gf_reconcile_scan_per_pass=1)
    )
    assert scanned == ["p1"]


def test_generating_project_does_not_consume_budget(tmp_path):
    """生成中只走廉价收敛（只降 zip_ready），不占额度、也不让别的项目被拖住。"""
    generating = _project(tmp_path, pid="gen", status="generating")
    ready = _project(tmp_path, pid="ready")
    project_svc.reset_checklist_list_cache()
    _, scanned = _reconcile([generating, ready], max_scans=1)
    assert scanned == ["ready"]


def test_project_without_workspace_does_not_consume_budget(tmp_path):
    """磁盘上没有工作区的项目只走 O(1) 收敛，不占额度（否则会饿死真有工作区的项目）。"""
    hollow = _project(
        tmp_path, pid="hollow", workspace_path=str(tmp_path / "missing")
    )
    ready = _project(tmp_path, pid="ready")
    project_svc.reset_checklist_list_cache()
    _, scanned = _reconcile([hollow, ready], max_scans=1)
    assert scanned == ["ready"]


def test_workspace_signature_tracks_files_and_prunes_build_output(tmp_path):
    ws = tmp_path / "ws"
    (ws / "src").mkdir(parents=True)
    (ws / "src" / "A.java").write_text("a", encoding="utf-8")
    first = project_svc.workspace_signature(ws)
    assert first == project_svc.workspace_signature(ws)
    (ws / "node_modules").mkdir()
    (ws / "node_modules" / "junk.js").write_text("x", encoding="utf-8")
    (ws / "target" / "classes").mkdir(parents=True)
    (ws / "target" / "classes" / "App.class").write_bytes(b"\x00\x01")
    assert project_svc.workspace_signature(ws) == first
    (ws / "src" / "A.java").write_text("class A {}", encoding="utf-8")
    assert project_svc.workspace_signature(ws) != first
