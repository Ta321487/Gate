"""学生端 API 全量冒烟编排单测（mock，不启真预览）。"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.services.student_api_smoke import FactorySmokeError, run_student_api_smoke


def test_smoke_requires_healthy_runtime():
    with pytest.raises(FactorySmokeError) as ei:
        run_student_api_smoke(
            project_id="p1",
            workspace=Path("."),
            spec={},
            backend_url="http://127.0.0.1:18080",
            frontend_url="http://127.0.0.1:15173",
            backend_status="stopped",
            frontend_status="healthy",
        )
    assert ei.value.payload.get("need_runtime") is True
    assert ei.value.payload.get("error_source") == "factory"
    assert "运行页" in ei.value.detail


def test_student_message_verbatim_on_apply_fail(tmp_path: Path):
    """mock 学生返回 message=名额不足 → 结果字符串全等。"""
    inv = {
        "count": 1,
        "controller_count": 1,
        "endpoints": [
            {
                "method": "GET",
                "path": "/api/tickets",
                "surface": "portal",
                "handler": "list",
                "flow_keys": [],
            }
        ],
        "surfaces": [],
    }

    class FakeResp:
        def __init__(self, status_code: int, payload):
            self.status_code = status_code
            self._payload = payload
            self.text = ""

        def json(self):
            return self._payload

    call_n = {"n": 0}

    def fake_request(method, url, **kwargs):
        call_n["n"] += 1
        u = str(url)
        if "captcha" in u:
            return FakeResp(200, {"code": 0, "data": {"key": "k", "code": "ABCD"}})
        if "login" in u:
            return FakeResp(200, {"code": 0, "data": {"username": "user"}})
        if "/api/meta" in u or u.rstrip("/").endswith(":18080"):
            return FakeResp(200, {"ok": True})
        if "ticket-main-path" in u:
            return FakeResp(200, {"code": 0, "data": {"ok": True}})
        if "/api/archive" in u:
            return FakeResp(
                200,
                {"code": 0, "data": {"list": [{"id": 1, "title": "活动A"}]}},
            )
        if "/api/tickets?" in u or u.endswith("/api/tickets"):
            return FakeResp(200, {"code": 0, "data": {"list": []}})
        if u.endswith("/api/tickets/apply"):
            return FakeResp(200, {"code": 4001, "message": "名额不足", "data": None})
        if method.upper() == "GET":
            return FakeResp(200, {"code": 0, "data": {}})
        return FakeResp(200, {"code": 0, "data": {}})

    fe_resp = FakeResp(200, {"ok": True})

    with (
        patch("app.services.student_api_smoke.load_api_inventory", return_value=inv),
        patch("httpx.Client") as Client,
    ):
        inst = MagicMock()
        inst.request.side_effect = fake_request
        inst.get.return_value = fe_resp
        inst.__enter__ = MagicMock(return_value=inst)
        inst.__exit__ = MagicMock(return_value=False)
        Client.return_value = inst

        out = run_student_api_smoke(
            project_id="p-msg",
            workspace=tmp_path,
            spec={
                "domain": "DOM-ACTIVITY",
                "runtime": {"ticket_mode": "archive"},
                "gate": {
                    "flow_api": {
                        "apply": {"need": ["/apply"]},
                        "approve": {"need": ["approve"]},
                        "return": {"need": ["/return"]},
                    }
                },
            },
            backend_url="http://127.0.0.1:18080",
            frontend_url="http://127.0.0.1:15173",
            backend_status="healthy",
            frontend_status="healthy",
        )

    apply_steps = [s for s in out["main_flow"] if s.get("name") == "apply"]
    assert apply_steps, "应有 apply 步骤"
    body = apply_steps[0].get("student_body")
    assert body is not None
    assert body.get("message") == "名额不足"
    assert apply_steps[0].get("error_source") == "student"
    assert apply_steps[0].get("ok") is False


def test_apply_json_includes_period_when_pick_date_range():
    from app.services.student_api_smoke import _apply_json

    body = _apply_json({"itemId": 9}, {})
    assert body is not None
    assert body["itemId"] == 9
    assert body.get("periodStart")
    assert body.get("periodEnd")
    assert body.get("dueAt")


def test_gate_fail_detail_uses_data_message(tmp_path: Path):
    inv = {
        "count": 0,
        "controller_count": 0,
        "endpoints": [],
        "surfaces": [],
    }

    class FakeResp:
        def __init__(self, status_code: int, payload):
            self.status_code = status_code
            self._payload = payload
            self.text = ""

        def json(self):
            return self._payload

    def fake_request(method, url, **kwargs):
        u = str(url)
        if "captcha" in u:
            return FakeResp(200, {"code": 0, "data": {"code": "ABCD"}})
        if "login" in u:
            return FakeResp(200, {"code": 0, "data": {}})
        if "ticket-main-path" in u:
            return FakeResp(
                200,
                {
                    "code": 0,
                    "message": "ok",
                    "data": {"ok": False, "message": "主路径未通过"},
                },
            )
        if "/api/meta" in u:
            return FakeResp(200, {"ok": True})
        if "/api/archive" in u or "/api/tickets" in u:
            return FakeResp(200, {"code": 0, "data": {"list": []}})
        return FakeResp(200, {"code": 0, "data": {}})

    with (
        patch("app.services.student_api_smoke.load_api_inventory", return_value=inv),
        patch("httpx.Client") as Client,
    ):
        inst = MagicMock()
        inst.request.side_effect = fake_request
        inst.get.return_value = FakeResp(200, {"ok": True})
        inst.__enter__ = MagicMock(return_value=inst)
        inst.__exit__ = MagicMock(return_value=False)
        Client.return_value = inst

        out = run_student_api_smoke(
            project_id="p-gate",
            workspace=tmp_path,
            spec={"domain": "DOM-ATTEND"},
            backend_url="http://127.0.0.1:18080",
            frontend_url="http://127.0.0.1:15173",
            backend_status="healthy",
            frontend_status="healthy",
        )

    gate = next(s for s in out["main_flow"] if s["name"] == "gate_self_check")
    assert gate["ok"] is False
    assert gate["detail"] == "主路径未通过"


def test_attend_flow_plan_is_apply_approve_return():
    from app.services.student_api_smoke import _flow_api

    spec = {
        "domain": "DOM-ATTEND",
        "gate": {
            "flow_api": {
                "apply": {},
                "approve": {},
                "return": {},
            }
        },
    }
    assert list(_flow_api(spec).keys()) == ["apply", "approve", "return"]


def test_fill_path_skip_missing_id():
    from app.services.student_api_smoke import _fill_path

    filled, reason = _fill_path("/api/tickets/{id}/approve", {})
    assert filled is None
    assert reason and "缺少" in reason


def _fake_client(fake_request, fe_ok=True):
    class FakeResp:
        def __init__(self, status_code: int, payload):
            self.status_code = status_code
            self._payload = payload
            self.text = ""

        def json(self):
            return self._payload

    inst = MagicMock()
    inst.request.side_effect = fake_request
    inst.get.return_value = FakeResp(200, {"ok": True}) if fe_ok else FakeResp(500, {})
    inst.__enter__ = MagicMock(return_value=inst)
    inst.__exit__ = MagicMock(return_value=False)
    return inst, FakeResp


def test_instrument_dual_chain_runs_ticket_and_reserve(tmp_path: Path):
    """借+约双链：单据跑完后必须继续 reserve/cancel，不能提前 return。"""
    inv = {"count": 0, "controller_count": 0, "endpoints": [], "surfaces": []}
    ticket_seq = {"n": 0}

    class FakeResp:
        def __init__(self, status_code: int, payload):
            self.status_code = status_code
            self._payload = payload
            self.text = ""

        def json(self):
            return self._payload

    def fake_request(method, url, **kwargs):
        u = str(url)
        if "captcha" in u:
            return FakeResp(200, {"code": 0, "data": {"code": "ABCD"}})
        if "login" in u:
            return FakeResp(200, {"code": 0, "data": {}})
        if "ticket-main-path" in u:
            return FakeResp(200, {"code": 0, "data": {"ok": True, "mode": "archive"}})
        if "/api/meta" in u:
            return FakeResp(200, {"ok": True})
        if "/api/archive" in u and method.upper() == "GET":
            return FakeResp(200, {"code": 0, "data": {"list": [{"id": 7, "title": "仪器A"}]}})
        if "/api/tickets/apply" in u:
            return FakeResp(200, {"code": 0, "data": {"id": 100, "status": "pending"}})
        if "/approve" in u:
            return FakeResp(200, {"code": 0, "data": {"id": 100, "status": "approved"}})
        if "/return" in u:
            return FakeResp(200, {"code": 0, "data": {"id": 100, "status": "returned"}})
        if "/api/tickets" in u:
            ticket_seq["n"] += 1
            if ticket_seq["n"] <= 2:
                return FakeResp(200, {"code": 0, "data": {"list": []}})
            return FakeResp(
                200, {"code": 0, "data": {"list": [{"id": 100, "status": "pending"}]}}
            )
        if "/api/slots/reserve" in u:
            return FakeResp(200, {"code": 0, "data": {"id": 55}})
        if "/cancel" in u:
            return FakeResp(200, {"code": 0, "data": {"id": 55, "status": "cancelled"}})
        if "/api/slots" in u and "reservations" not in u:
            return FakeResp(200, {"code": 0, "data": {"list": [{"id": 9}]}})
        if "/api/slots/reservations" in u:
            return FakeResp(200, {"code": 0, "data": {"list": [{"id": 55}]}})
        return FakeResp(200, {"code": 0, "data": {}})

    with (
        patch("app.services.student_api_smoke.load_api_inventory", return_value=inv),
        patch("httpx.Client") as Client,
    ):
        inst = MagicMock()
        inst.request.side_effect = fake_request

        class FR:
            status_code = 200
            text = ""

            def json(self):
                return {"ok": True}

        inst.get.return_value = FR()
        inst.__enter__ = MagicMock(return_value=inst)
        inst.__exit__ = MagicMock(return_value=False)
        Client.return_value = inst

        out = run_student_api_smoke(
            project_id="p-inst",
            workspace=tmp_path,
            spec={
                "domain": "DOM-INSTRUMENT",
                "runtime": {"ticket_mode": "archive"},
                "gate": {
                    "flow_api": {
                        "apply": {},
                        "approve": {},
                        "return": {},
                        "overdue": {},
                        "remind": {},
                        "reserve": {},
                        "cancel": {},
                    }
                },
            },
            backend_url="http://127.0.0.1:18080",
            frontend_url="http://127.0.0.1:15173",
            backend_status="healthy",
            frontend_status="healthy",
        )

    names = [s["name"] for s in out["main_flow"]]
    assert "apply" in names
    assert "approve" in names
    assert "return" in names
    assert "reserve" in names
    assert "cancel" in names
    assert "flow_api_gap" not in names
    assert next(s for s in out["main_flow"] if s["name"] == "reserve")["ok"] is True


def test_favorites_chain_toggles_item(tmp_path: Path):
    inv = {"count": 0, "controller_count": 0, "endpoints": [], "surfaces": []}

    class FakeResp:
        def __init__(self, status_code: int, payload):
            self.status_code = status_code
            self._payload = payload
            self.text = ""

        def json(self):
            return self._payload

    def fake_request(method, url, **kwargs):
        u = str(url)
        if "captcha" in u:
            return FakeResp(200, {"code": 0, "data": {"code": "ABCD"}})
        if "login" in u:
            return FakeResp(200, {"code": 0, "data": {}})
        if "ticket-main-path" in u:
            return FakeResp(200, {"code": 0, "data": {"ok": True, "mode": "archive"}})
        if "/api/meta" in u:
            return FakeResp(200, {"ok": True})
        if "/api/archive" in u:
            return FakeResp(200, {"code": 0, "data": {"list": [{"id": 3}]}})
        if "/api/favorites/3/toggle" in u:
            return FakeResp(200, {"code": 0, "data": {"favorited": True}})
        if "/api/favorites" in u:
            return FakeResp(200, {"code": 0, "data": {"list": [{"id": 3}]}})
        return FakeResp(200, {"code": 0, "data": {}})

    with (
        patch("app.services.student_api_smoke.load_api_inventory", return_value=inv),
        patch("httpx.Client") as Client,
    ):
        inst = MagicMock()
        inst.request.side_effect = fake_request

        class FR:
            status_code = 200
            text = ""

            def json(self):
                return {"ok": True}

        inst.get.return_value = FR()
        inst.__enter__ = MagicMock(return_value=inst)
        inst.__exit__ = MagicMock(return_value=False)
        Client.return_value = inst

        out = run_student_api_smoke(
            project_id="p-fav",
            workspace=tmp_path,
            spec={
                "domain": "DOM-MEDIA",
                "gate": {"flow_api": {"favorites": {}}},
            },
            backend_url="http://127.0.0.1:18080",
            frontend_url="http://127.0.0.1:15173",
            backend_status="healthy",
            frontend_status="healthy",
        )

    names = [s["name"] for s in out["main_flow"]]
    assert "favorites" in names
    assert "favorites_list" in names
    assert next(s for s in out["main_flow"] if s["name"] == "favorites")["ok"] is True
    assert "flow_api_gap" not in names
