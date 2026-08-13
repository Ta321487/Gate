"""人工交付标记：与机器质检 zip_ready 分离。"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.services import projects as project_svc


def test_normalize_delivery_mark():
    assert project_svc.normalize_delivery_mark(None) == "none"
    assert project_svc.normalize_delivery_mark("READY") == "ready"
    assert project_svc.normalize_delivery_mark("bogus") == "none"


def test_reset_delivery_mark():
    p = SimpleNamespace(delivery_mark="ready")
    assert project_svc.reset_delivery_mark(p) is True
    assert p.delivery_mark == "none"
    assert project_svc.reset_delivery_mark(p) is False


def test_apply_delivery_mark_requires_downloadable():
    p = SimpleNamespace(
        status="generated",
        delivery_mark="none",
        zip_ready=False,
        gates={"overall": False, "zip_allowed": False},
        zip_path=None,
    )
    with pytest.raises(ValueError, match="质量检查未通过"):
        project_svc.apply_delivery_mark(p, "ready")


def test_apply_delivery_mark_ready_then_delivered(tmp_path):
    zip_file = tmp_path / "demo.zip"
    zip_file.write_bytes(b"PK")
    p = SimpleNamespace(
        status="generated",
        delivery_mark="none",
        zip_ready=True,
        gates={"overall": True, "zip_allowed": True},
        zip_path=str(zip_file),
    )
    assert project_svc.apply_delivery_mark(p, "ready") == "ready"
    assert project_svc.apply_delivery_mark(p, "delivered") == "delivered"


def test_apply_delivery_mark_none_to_delivered_when_downloadable(tmp_path):
    """质检可下时允许一步标已发出（跳过已审待发暂存）。"""
    zip_file = tmp_path / "demo.zip"
    zip_file.write_bytes(b"PK")
    p = SimpleNamespace(
        status="generated",
        delivery_mark="none",
        zip_ready=True,
        gates={"overall": True, "zip_allowed": True},
        zip_path=str(zip_file),
    )
    assert project_svc.apply_delivery_mark(p, "delivered") == "delivered"


def test_apply_delivery_mark_delivered_blocked_without_zip(tmp_path):
    p = SimpleNamespace(
        status="generated",
        delivery_mark="none",
        zip_ready=False,
        gates={"overall": False, "zip_allowed": False},
        zip_path=None,
    )
    with pytest.raises(ValueError, match="质量检查未通过"):
        project_svc.apply_delivery_mark(p, "delivered")


def test_is_zip_downloadable_requires_zip_and_gates(tmp_path):
    zip_file = tmp_path / "demo.zip"
    zip_file.write_bytes(b"PK")
    ok = SimpleNamespace(
        status="generated",
        zip_ready=True,
        gates={"overall": True, "zip_allowed": True},
        zip_path=str(zip_file),
    )
    assert project_svc.is_zip_downloadable(ok) is True
    assert project_svc.delivery_block_reason(ok) is None

    missing = SimpleNamespace(
        status="generated",
        zip_ready=True,
        gates={"overall": True, "zip_allowed": True},
        zip_path=str(tmp_path / "gone.zip"),
        delivery_mark="ready",
    )
    assert project_svc.is_zip_downloadable(missing) is False
    assert project_svc.delivery_block_reason(missing) == project_svc.MSG_DOWNLOAD_ZIP_MISSING


def test_sync_clears_stale_zip_ready_without_workspace(tmp_path):
    """工作区缺失时仍清掉 zip_ready=true 但 ZIP/门禁已失效的陈旧标志。"""
    p = SimpleNamespace(
        status="generated",
        workspace_path=None,
        zip_ready=True,
        gates={"overall": True, "zip_allowed": True},
        zip_path=str(tmp_path / "missing.zip"),
        delivery_mark="delivered",
        checklist=[],
        spec={},
    )
    assert project_svc.sync_checklist_from_workspace(p) is True
    assert p.zip_ready is False
    assert p.delivery_mark == "none"


def test_sync_clears_stale_zip_ready_when_gates_fail(tmp_path):
    zip_file = tmp_path / "demo.zip"
    zip_file.write_bytes(b"PK")
    p = SimpleNamespace(
        status="generated",
        workspace_path=str(tmp_path / "no-ws"),
        zip_ready=True,
        gates={"overall": False, "zip_allowed": False},
        zip_path=str(zip_file),
        delivery_mark="ready",
        checklist=[],
        spec={},
    )
    assert project_svc.sync_checklist_from_workspace(p) is True
    assert p.zip_ready is False
    assert p.delivery_mark == "none"
