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


def test_apply_delivery_mark_delivered_requires_ready(tmp_path):
    zip_file = tmp_path / "demo.zip"
    zip_file.write_bytes(b"PK")
    p = SimpleNamespace(
        status="generated",
        delivery_mark="none",
        zip_ready=True,
        gates={"overall": True, "zip_allowed": True},
        zip_path=str(zip_file),
    )
    with pytest.raises(ValueError, match="请先标记"):
        project_svc.apply_delivery_mark(p, "delivered")
