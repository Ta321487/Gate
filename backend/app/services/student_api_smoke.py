"""学生端 API 全量冒烟：只探测已启动预览，不启停进程。"""

from __future__ import annotations

import re
import threading
import time
from datetime import date, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import httpx

from app.bake.api_inventory import load_api_inventory

_PATH_PARAM_RE = re.compile(r"\{([^}/]+)\}")
_SMOKE_LOCKS: dict[str, threading.Lock] = {}
_SMOKE_BUSY: set[str] = set()
_BUSY_GUARD = threading.Lock()

REQUEST_TIMEOUT = 12.0


class FactorySmokeError(Exception):
    """工厂侧错误（未启动等），由 API 层转 409。"""

    def __init__(self, detail: str, *, payload: dict[str, Any] | None = None):
        super().__init__(detail)
        self.detail = detail
        self.payload = payload or {}


def _lock_for(project_id: str) -> threading.Lock:
    with _BUSY_GUARD:
        if project_id not in _SMOKE_LOCKS:
            _SMOKE_LOCKS[project_id] = threading.Lock()
        return _SMOKE_LOCKS[project_id]


def _acquire_busy(project_id: str) -> None:
    with _BUSY_GUARD:
        if project_id in _SMOKE_BUSY:
            raise FactorySmokeError(
                "该项目正在冒烟，请稍后再试",
                payload={"error_source": "factory", "busy": True},
            )
        _SMOKE_BUSY.add(project_id)


def _release_busy(project_id: str) -> None:
    with _BUSY_GUARD:
        _SMOKE_BUSY.discard(project_id)


def _student_ok(body: Any) -> bool:
    if not isinstance(body, dict):
        return False
    return body.get("code") in (0, "0")


def _r_data(body: Any) -> Any:
    if isinstance(body, dict) and "data" in body:
        return body.get("data")
    return body


def _portal_user(spec: dict[str, Any] | None) -> tuple[str, str]:
    domain = str((spec or {}).get("domain") or "")
    schema = (spec or {}).get("schema") if isinstance((spec or {}).get("schema"), dict) else {}
    roles = schema.get("roles") if isinstance(schema, dict) else {}
    user = roles.get("user") if isinstance(roles, dict) else {}
    role_id = str((user or {}).get("id") or "").strip().lower()
    if domain == "DOM-COURSE" or role_id == "student":
        return "student", "student123"
    return "user", "user123"


def _allow_checkin(spec: dict[str, Any] | None) -> bool:
    return bool(_ticket_flags(spec).get("allowCheckin"))


def _ticket_flags(spec: dict[str, Any] | None) -> dict[str, Any]:
    schema = (spec or {}).get("schema") if isinstance((spec or {}).get("schema"), dict) else {}
    ents = schema.get("entities") if isinstance(schema, dict) else {}
    ticket = ents.get("ticket") if isinstance(ents, dict) else {}
    return ticket if isinstance(ticket, dict) else {}


def _flow_api(spec: dict[str, Any] | None) -> dict[str, Any]:
    gate = (spec or {}).get("gate") if isinstance((spec or {}).get("gate"), dict) else {}
    fa = gate.get("flow_api") if isinstance(gate, dict) else {}
    return fa if isinstance(fa, dict) else {}


def _ticket_mode(spec: dict[str, Any] | None, gate_mode: str | None = None) -> str:
    if gate_mode:
        return str(gate_mode).lower()
    runtime = (spec or {}).get("runtime") if isinstance((spec or {}).get("runtime"), dict) else {}
    mode = str((runtime or {}).get("ticket_mode") or "").strip().lower()
    if mode:
        return mode
    return "archive"


def _apply_json(
    ctx: dict[str, Any],
    spec: dict[str, Any] | None,
    *,
    ticket_mode: str = "archive",
) -> dict[str, Any] | None:
    if ticket_mode == "standalone":
        body: dict[str, Any] = {
            "title": "冒烟报修",
            "location": "测试地点",
            "remark": "冒烟申请",
        }
        if ctx.get("typeId") is not None:
            body["typeId"] = ctx["typeId"]
        if ctx.get("roomId") is not None:
            body["roomId"] = ctx["roomId"]
        return body
    item_id = ctx.get("itemId") or ctx.get("id")
    if item_id is None:
        return None
    body = {
        "itemId": item_id,
        "bookId": item_id,
        "remark": "冒烟申请",
    }
    start = date.today() + timedelta(days=1)
    end = start + timedelta(days=2)
    body["periodStart"] = start.isoformat()
    body["periodEnd"] = end.isoformat()
    body["startAt"] = body["periodStart"]
    body["endAt"] = body["periodEnd"]
    due = date.today() + timedelta(days=7)
    body["dueAt"] = due.isoformat()
    body["borrowUntil"] = body["dueAt"]
    if _ticket_flags(spec).get("allowQty"):
        body["qty"] = 1
    if _ticket_flags(spec).get("requireClaimCode"):
        code = str(ctx.get("claimCode") or ctx.get("pickupCode") or "")
        if code:
            body["pickupCode"] = code
            body["claimCode"] = code
            body["remark"] = code
    return body


def _step_result(
    name: str,
    *,
    ok: bool,
    error_source: str | None = None,
    http_status: int | None = None,
    student_body: Any = None,
    detail: str | None = None,
    skip: bool = False,
    ms: int = 0,
) -> dict[str, Any]:
    return {
        "name": name,
        "ok": ok,
        "skip": skip,
        "error_source": error_source,
        "http_status": http_status,
        "student_body": student_body,
        "detail": detail,
        "ms": ms,
    }


def _http_step(
    client: httpx.Client,
    base: str,
    name: str,
    method: str,
    path: str,
    *,
    json_body: Any = None,
) -> dict[str, Any]:
    t0 = time.perf_counter()
    st, body, ferr = _request(
        client, method, urljoin(base, path), json_body=json_body
    )
    ms = int((time.perf_counter() - t0) * 1000)
    if ferr:
        return _step_result(name, ok=False, error_source="factory", detail=ferr, ms=ms)
    ok = st is not None and 200 <= st < 300 and _student_ok(body)
    row = _step_result(
        name,
        ok=ok,
        error_source="student" if not ok else None,
        http_status=st,
        student_body=body if not ok else None,
        ms=ms,
    )
    if ok:
        row["data"] = _r_data(body)
    else:
        row["student_body"] = body
    return row


def _warm_lookups(portal: httpx.Client, base: str, ctx: dict[str, Any]) -> None:
    for path, key in (
        ("/api/lookups/types", "typeId"),
        ("/api/lookups/units", "roomId"),
    ):
        st, body, ferr = _request(portal, "GET", urljoin(base, path))
        if ferr or not body:
            continue
        data = _r_data(body)
        lst = data if isinstance(data, list) else (
            (data or {}).get("list") if isinstance(data, dict) else None
        )
        if isinstance(lst, list) and lst and isinstance(lst[0], dict) and lst[0].get("id") is not None:
            ctx.setdefault(key, lst[0].get("id"))


def _run_flow_api_business(
    *,
    portal: httpx.Client,
    admin: httpx.Client,
    base: str,
    spec: dict[str, Any] | None,
    ctx: dict[str, Any],
    ticket_mode: str,
    main_flow: list[dict[str, Any]],
) -> None:
    """按 spec.gate.flow_api 跑主流程（可多链并存，如仪器借+约）；目标能代替页面点主路径。"""
    fa = _flow_api(spec)
    if not fa:
        main_flow.append(
            _step_result(
                "flow_api",
                ok=True,
                skip=True,
                error_source="skip",
                detail="本域无 flow_api 主链（多为检索/CRUD），已跳过业务步骤",
            )
        )
        return

    keys = list(fa.keys())
    main_flow.append(
        _step_result(
            "flow_plan",
            ok=True,
            detail="主链: " + " → ".join(keys),
        )
    )
    done: set[str] = set()

    # —— 单据壳（可与预约/收藏并存）——
    if "apply" in fa or "approve" in fa or "return" in fa or "complete" in fa:
        if ticket_mode == "standalone":
            _warm_lookups(portal, base, ctx)

        step_list = _http_step(
            portal, base, "my_tickets", "GET", "/api/tickets?page=1&size=10"
        )
        main_flow.append(step_list)
        pending_id = ctx.get("pendingTicketId")
        if step_list.get("ok"):
            st_m, body_m, _ = _request(
                portal, "GET", urljoin(base, "/api/tickets?page=1&size=10")
            )
            data_m = _r_data(body_m) if body_m else {}
            lst = (data_m.get("list") or []) if isinstance(data_m, dict) else []
            if isinstance(lst, list):
                for row in lst:
                    if (
                        isinstance(row, dict)
                        and row.get("status") == "pending"
                        and row.get("id") is not None
                    ):
                        pending_id = row.get("id")
                        break

        ticket_id = pending_id
        if "apply" in fa:
            done.add("apply")
            # 冒烟要代替页面点「申请」：有待审也不跳过，再提一单
            apply_body = _apply_json(ctx, spec, ticket_mode=ticket_mode)
            if apply_body is None:
                main_flow.append(
                    _step_result(
                        "apply",
                        ok=False,
                        skip=True,
                        error_source="skip",
                        detail="缺少档案 itemId / 报修字段，未申请",
                    )
                )
            else:
                step_ap = _http_step(
                    portal,
                    base,
                    "apply",
                    "POST",
                    "/api/tickets/apply",
                    json_body=apply_body,
                )
                main_flow.append(step_ap)
                created = step_ap.get("data")
                if isinstance(created, dict) and created.get("id") is not None:
                    ticket_id = created.get("id")
                elif step_ap.get("ok"):
                    st_c, body_c, _ = _request(
                        portal, "GET", urljoin(base, "/api/tickets?page=1&size=5")
                    )
                    data_c = _r_data(body_c) if body_c else {}
                    lst_c = (data_c.get("list") or []) if isinstance(data_c, dict) else []
                    if isinstance(lst_c, list):
                        for row in lst_c:
                            if isinstance(row, dict) and row.get("status") == "pending":
                                ticket_id = row.get("id")
                                break
        # 无 apply 键时沿用已有 pending
        elif ticket_id is None:
            pass

        if "approve" in fa:
            done.add("approve")
            if ticket_id is None:
                main_flow.append(
                    _step_result(
                        "approve",
                        ok=False,
                        skip=True,
                        error_source="skip",
                        detail="无待审单据，跳过审核",
                    )
                )
            else:
                main_flow.append(
                    _http_step(
                        admin,
                        base,
                        "approve",
                        "POST",
                        f"/api/tickets/{ticket_id}/approve",
                        json_body={"pass": True, "remark": "冒烟通过"},
                    )
                )

        # 口令签到：域 flag（活动报名等页面必点）
        if _allow_checkin(spec) and ticket_id is not None:
            code = str(ctx.get("checkinCode") or "")
            if not code:
                st_d, body_d, _ = _request(
                    portal, "GET", urljoin(base, f"/api/tickets/{ticket_id}")
                )
                data_d = _r_data(body_d) if body_d else {}
                if isinstance(data_d, dict):
                    code = str(
                        data_d.get("checkinCode") or data_d.get("checkin_code") or ""
                    )
                if not code and ctx.get("itemId") is not None:
                    st_a, body_a, _ = _request(
                        portal, "GET", urljoin(base, f"/api/archive/{ctx['itemId']}")
                    )
                    data_a = _r_data(body_a) if body_a else {}
                    if isinstance(data_a, dict):
                        code = str(
                            data_a.get("checkinCode")
                            or data_a.get("checkin_code")
                            or data_a.get("passCode")
                            or ""
                        )
            if not code:
                main_flow.append(
                    _step_result(
                        "checkin",
                        ok=False,
                        skip=True,
                        error_source="skip",
                        detail="缺少签到码，未请求",
                    )
                )
            else:
                main_flow.append(
                    _http_step(
                        portal,
                        base,
                        "checkin",
                        "POST",
                        f"/api/tickets/{ticket_id}/checkin",
                        json_body={"code": code},
                    )
                )

        # 逾期/催还：页面上通常在到期后由管理端点；冒烟不改系统时间，明确跳过
        for admin_key in ("overdue", "remind"):
            if admin_key in fa:
                done.add(admin_key)
                main_flow.append(
                    _step_result(
                        admin_key,
                        ok=True,
                        skip=True,
                        error_source="skip",
                        detail="逾期/催还依赖演示日期间隔，冒烟跳过（页面亦多在逾期后操作）",
                    )
                )

        end_key = "return" if "return" in fa else ("complete" if "complete" in fa else None)
        if end_key:
            done.add(end_key)
            if ticket_id is not None:
                main_flow.append(
                    _http_step(
                        portal,
                        base,
                        end_key,
                        "POST",
                        f"/api/tickets/{ticket_id}/{end_key}",
                    )
                )
            else:
                main_flow.append(
                    _step_result(
                        end_key,
                        ok=False,
                        skip=True,
                        error_source="skip",
                        detail="无单据，跳过完结",
                    )
                )

    # —— 发帖（论坛等，与单据可并存）——
    if "publish" in fa:
        done.add("publish")
        main_flow.append(
            _http_step(
                portal,
                base,
                "publish",
                "POST",
                "/api/archive/publish",
                json_body={
                    "title": "冒烟发帖",
                    "body": "冒烟正文",
                    "isbn": "冒烟正文",
                    "categoryId": 1,
                },
            )
        )

    # —— 下单壳 ——
    if "cart" in fa or "place" in fa:
        if "cart" in fa:
            done.add("cart")
            if ctx.get("itemId") is not None:
                main_flow.append(
                    _http_step(
                        portal,
                        base,
                        "cart",
                        "POST",
                        "/api/cart",
                        json_body={"itemId": ctx["itemId"], "qty": 1},
                    )
                )
            else:
                main_flow.append(
                    _step_result(
                        "cart",
                        ok=False,
                        skip=True,
                        error_source="skip",
                        detail="缺少商品 itemId，未加购",
                    )
                )
        if "place" in fa:
            done.add("place")
            main_flow.append(
                _http_step(
                    portal,
                    base,
                    "place",
                    "POST",
                    "/api/orders",
                    json_body={"remark": "冒烟下单", "deliveryType": "pickup"},
                )
            )

    # —— 预约壳（仪器借+约：单据跑完后继续跑）——
    if "reserve" in fa:
        done.add("reserve")
        slot_id = ctx.get("slotId")
        if slot_id is None:
            st_s, body_s, _ = _request(portal, "GET", urljoin(base, "/api/slots"))
            data_s = _r_data(body_s) if body_s else {}
            lst_s: list[Any] = []
            if isinstance(data_s, dict):
                lst_s = data_s.get("list") or data_s.get("slots") or []
            elif isinstance(data_s, list):
                lst_s = data_s
            if isinstance(lst_s, list):
                for row in lst_s:
                    if isinstance(row, dict) and row.get("id") is not None:
                        slot_id = row.get("id")
                        break
        if slot_id is None:
            main_flow.append(
                _step_result(
                    "reserve",
                    ok=False,
                    skip=True,
                    error_source="skip",
                    detail="无可用时段，未预约",
                )
            )
        else:
            step_r = _http_step(
                portal,
                base,
                "reserve",
                "POST",
                "/api/slots/reserve",
                json_body={"slotId": slot_id, "remark": "冒烟预约"},
            )
            main_flow.append(step_r)
            if "cancel" in fa:
                done.add("cancel")
                rid = None
                created_r = step_r.get("data")
                if isinstance(created_r, dict) and created_r.get("id") is not None:
                    rid = created_r.get("id")
                if rid is None and step_r.get("ok"):
                    st_rv, body_rv, _ = _request(
                        portal,
                        "GET",
                        urljoin(base, "/api/slots/reservations?page=1&size=5"),
                    )
                    data_rv = _r_data(body_rv) if body_rv else {}
                    lst_rv = (data_rv.get("list") or []) if isinstance(data_rv, dict) else []
                    if isinstance(lst_rv, list) and lst_rv and isinstance(lst_rv[0], dict):
                        rid = lst_rv[0].get("id")
                if rid is not None:
                    main_flow.append(
                        _http_step(
                            portal,
                            base,
                            "cancel",
                            "POST",
                            f"/api/slots/reservations/{rid}/cancel",
                        )
                    )
                else:
                    main_flow.append(
                        _step_result(
                            "cancel",
                            ok=False,
                            skip=True,
                            error_source="skip",
                            detail="无预约 id，跳过取消",
                        )
                    )
    elif "cancel" in fa:
        done.add("cancel")
        main_flow.append(
            _step_result(
                "cancel",
                ok=False,
                skip=True,
                error_source="skip",
                detail="无 reserve 步骤，跳过取消",
            )
        )

    # —— 收藏（媒体/音乐等页面：浏览后点收藏）——
    if "favorites" in fa:
        done.add("favorites")
        item_id = ctx.get("itemId")
        if item_id is None:
            main_flow.append(
                _step_result(
                    "favorites",
                    ok=False,
                    skip=True,
                    error_source="skip",
                    detail="缺少档案 itemId，未收藏",
                )
            )
        else:
            main_flow.append(
                _http_step(
                    portal,
                    base,
                    "favorites",
                    "POST",
                    f"/api/favorites/{item_id}/toggle",
                )
            )
            # 再打开「我的收藏」列表，对齐页面验收
            main_flow.append(
                _http_step(
                    portal,
                    base,
                    "favorites_list",
                    "GET",
                    "/api/favorites?page=1&size=10",
                )
            )

    missing = [k for k in keys if k not in done]
    if missing:
        main_flow.append(
            _step_result(
                "flow_api_gap",
                ok=False,
                error_source="factory",
                detail=f"flow_api 未编排业务步: {', '.join(missing)}",
            )
        )



def _fill_path(path: str, ctx: dict[str, Any]) -> tuple[str | None, str | None]:
    """返回 (filled_path, skip_reason)。"""
    missing: list[str] = []

    def repl(m: re.Match[str]) -> str:
        key = m.group(1)
        for cand in (key, key.lower(), "id", "ticketId", "itemId", "bookId"):
            if cand in ctx and ctx[cand] is not None:
                return str(ctx[cand])
        missing.append(key)
        return m.group(0)

    filled = _PATH_PARAM_RE.sub(repl, path)
    if missing or "{" in filled:
        return None, f"缺少 {','.join(missing) or 'path 变量'}，未请求"
    return filled, None


def _parse_json(resp: httpx.Response) -> Any:
    try:
        return resp.json()
    except Exception:  # noqa: BLE001
        text = (resp.text or "")[:500]
        return {"raw": text} if text else None


def _request(
    client: httpx.Client,
    method: str,
    url: str,
    *,
    json_body: Any = None,
) -> tuple[int | None, Any, str | None]:
    """返回 http_status, body, factory_error_detail。"""
    try:
        kw: dict[str, Any] = {"timeout": REQUEST_TIMEOUT}
        if json_body is not None and method.upper() not in ("GET", "HEAD"):
            kw["json"] = json_body
        elif method.upper() not in ("GET", "HEAD", "DELETE"):
            kw["json"] = {}
        resp = client.request(method.upper(), url, **kw)
        return resp.status_code, _parse_json(resp), None
    except httpx.TimeoutException:
        return None, None, "连接学生后端超时"
    except httpx.HTTPError as e:
        return None, None, f"无法连接学生后端: {e.__class__.__name__}"


def _login(
    client: httpx.Client,
    base: str,
    username: str,
    password: str,
) -> dict[str, Any]:
    """登录；失败时结果带 student_body。成功返回 ok 步。"""
    t0 = time.perf_counter()
    st, body, ferr = _request(client, "GET", urljoin(base, "/api/auth/captcha"))
    ms = int((time.perf_counter() - t0) * 1000)
    if ferr:
        return {
            "name": f"login:{username}",
            "ok": False,
            "error_source": "factory",
            "detail": ferr,
            "ms": ms,
        }
    data = _r_data(body) if isinstance(body, dict) else {}
    code = ""
    if isinstance(data, dict):
        code = str(data.get("code") or "")
    if not code:
        return {
            "name": f"login:{username}",
            "ok": False,
            "error_source": "factory",
            "http_status": st,
            "student_body": body,
            "detail": "验证码未回显明文；请在运行页停止并重新启动后端预览后重试",
            "ms": ms,
        }
    t1 = time.perf_counter()
    st2, body2, ferr2 = _request(
        client,
        "POST",
        urljoin(base, "/api/auth/login"),
        json_body={"username": username, "password": password, "captcha": code},
    )
    ms2 = int((time.perf_counter() - t1) * 1000)
    if ferr2:
        return {
            "name": f"login:{username}",
            "ok": False,
            "error_source": "factory",
            "detail": ferr2,
            "ms": ms + ms2,
        }
    ok = st2 is not None and 200 <= st2 < 300 and _student_ok(body2)
    return {
        "name": f"login:{username}",
        "ok": ok,
        "error_source": "student" if not ok else None,
        "http_status": st2,
        "student_body": body2 if not ok else None,
        "ms": ms + ms2,
    }


def _probe_endpoint(
    client: httpx.Client,
    base: str,
    ep: dict[str, Any],
    ctx: dict[str, Any],
    sessions: dict[str, httpx.Client],
    *,
    spec: dict[str, Any] | None = None,
) -> dict[str, Any]:
    method = str(ep.get("method") or "GET").upper()
    path = str(ep.get("path") or "")
    surface = str(ep.get("surface") or "baseline")
    filled, skip_reason = _fill_path(path, ctx)
    row: dict[str, Any] = {
        "method": method,
        "path": path,
        "filled_path": filled,
        "surface": surface,
        "flow_keys": list(ep.get("flow_keys") or []),
        "handler": ep.get("handler"),
        "layer": "reachability",
    }
    if skip_reason:
        row.update(
            {
                "ok": False,
                "skip": True,
                "error_source": "skip",
                "detail": skip_reason,
                "ms": 0,
            }
        )
        return row

    use = client
    if (
        surface == "admin"
        or path.startswith("/api/admin")
        or "/approve" in path
        or path.endswith("/dispatch-targets")
    ) and "admin" in sessions:
        use = sessions["admin"]
    elif surface in ("portal", "baseline") and "portal" in sessions:
        use = sessions["portal"]

    assert filled is not None
    url = urljoin(base, filled)
    body_json: Any = None
    if method == "POST" and filled.endswith("/api/tickets/apply"):
        mode = _ticket_mode(spec)
        body_json = _apply_json(ctx, spec, ticket_mode=mode) or {}
    elif method == "POST" and "/approve" in filled:
        body_json = {"pass": True, "remark": "冒烟通过"}
    elif method == "POST" and "/checkin" in filled:
        body_json = {"code": str(ctx.get("checkinCode") or ctx.get("checkin_code") or "")}

    t0 = time.perf_counter()
    st, body, ferr = _request(use, method, url, json_body=body_json)
    # 学生常 HTTP 200 +「需要管理员权限」：换 admin 再试一次
    if (
        use is not sessions.get("admin")
        and "admin" in sessions
        and isinstance(body, dict)
        and "管理员" in str(body.get("message") or "")
    ):
        st, body, ferr = _request(sessions["admin"], method, url, json_body=body_json)
    ms = int((time.perf_counter() - t0) * 1000)
    row["ms"] = ms
    if ferr:
        row.update({"ok": False, "skip": False, "error_source": "factory", "detail": ferr})
        return row
    row["http_status"] = st
    if st is None:
        row.update({"ok": False, "error_source": "factory", "detail": "无响应"})
        return row
    if st >= 500:
        row.update(
            {
                "ok": False,
                "skip": False,
                "error_source": "student",
                "student_body": body,
            }
        )
        return row

    # 可达：有 HTTP；业务文案仅在 R.code≠0 时附带（避免「通过 + ok」噪音）
    biz_ok = _student_ok(body) if isinstance(body, dict) else True
    row.update(
        {
            "ok": True,
            "skip": False,
            "error_source": None,
            "reachable": True,
            "business_ok": biz_ok,
        }
    )
    if isinstance(body, dict) and not biz_ok:
        row["student_body"] = body
        row["error_source"] = "student"  # 展示原样，汇总仍按可达计绿
    elif 400 <= st < 500:
        row["student_body"] = body
        row["business_ok"] = False
        row["error_source"] = "student"
    return row


def _list_rows(data: Any) -> list[dict[str, Any]]:
    lst: list[Any] | None = None
    if isinstance(data, dict):
        lst = data.get("list") or data.get("records") or data.get("items")
    elif isinstance(data, list):
        lst = data
    if not isinstance(lst, list):
        return []
    return [r for r in lst if isinstance(r, dict)]


def _claim_code_from_item(data: dict[str, Any]) -> str:
    isbn = str(data.get("isbn") or "")
    if not isbn:
        return ""
    code = isbn.strip()
    if code.startswith("取件码"):
        code = code.replace("取件码", "", 1).strip()
    for sep in ("/", "·"):
        if sep in code:
            code = code.split(sep, 1)[0].strip()
    return code


def _archive_detail_ok(
    portal: httpx.Client, base: str, item_id: Any
) -> dict[str, Any] | None:
    st, body, ferr = _request(portal, "GET", urljoin(base, f"/api/archive/{item_id}"))
    if ferr or not _student_ok(body):
        return None
    data = _r_data(body)
    return data if isinstance(data, dict) else None


def _candidate_item_ids(row: dict[str, Any]) -> list[Any]:
    out: list[Any] = []
    seen: set[Any] = set()
    for k in ("id", "bookId", "itemId"):
        v = row.get(k)
        if v is None or v in seen:
            continue
        seen.add(v)
        out.append(v)
    return out


def _stash_apply_item(
    ctx: dict[str, Any], item_id: Any, detail: dict[str, Any] | None
) -> None:
    ctx["itemId"] = item_id
    ctx["bookId"] = item_id
    ctx["id"] = item_id
    if not detail:
        return
    for k in ("checkinCode", "checkin_code"):
        if detail.get(k):
            ctx["checkinCode"] = detail.get(k)
    code = _claim_code_from_item(detail)
    if code:
        ctx["claimCode"] = code


def _warm_context(portal: httpx.Client, base: str, ctx: dict[str, Any]) -> None:
    st, body, ferr = _request(portal, "GET", urljoin(base, "/api/archive?page=1&size=20"))
    if not ferr and body:
        for row in _list_rows(_r_data(body)):
            for cand in _candidate_item_ids(row):
                detail = _archive_detail_ok(portal, base, cand)
                if detail is not None:
                    _stash_apply_item(ctx, cand, detail)
                    break
            if ctx.get("itemId") is not None:
                break

    st_t, body_t, ferr_t = _request(portal, "GET", urljoin(base, "/api/tickets?page=1&size=10"))
    ticket_rows: list[dict[str, Any]] = []
    if not ferr_t and body_t:
        ticket_rows = _list_rows(_r_data(body_t))
        for row in ticket_rows:
            if row.get("status") == "pending" and row.get("id") is not None:
                ctx.setdefault("ticketId", row.get("id"))
                ctx.setdefault("pendingTicketId", row.get("id"))
                break

    if ctx.get("itemId") is None:
        for row in ticket_rows:
            bid = row.get("bookId")
            if bid is None:
                continue
            detail = _archive_detail_ok(portal, base, bid)
            if detail is not None:
                _stash_apply_item(ctx, bid, detail)
                break


def run_student_api_smoke(
    *,
    project_id: str,
    workspace: Path,
    spec: dict[str, Any] | None,
    backend_url: str,
    frontend_url: str,
    backend_status: str,
    frontend_status: str,
) -> dict[str, Any]:
    """对已启动预览做全量路径探测 + 主流程业务链。"""
    if backend_status != "healthy" or frontend_status != "healthy":
        raise FactorySmokeError(
            "请先到运行页启动前后端预览",
            payload={
                "error_source": "factory",
                "need_runtime": True,
                "backend_status": backend_status,
                "frontend_status": frontend_status,
            },
        )

    inv = load_api_inventory(workspace, spec)
    if not inv:
        raise FactorySmokeError(
            "未找到 Controller，无法冒烟",
            payload={"error_source": "factory"},
        )

    _acquire_busy(project_id)
    lock = _lock_for(project_id)
    if not lock.acquire(blocking=False):
        _release_busy(project_id)
        raise FactorySmokeError(
            "该项目正在冒烟，请稍后再试",
            payload={"error_source": "factory", "busy": True},
        )

    base = backend_url.rstrip("/") + "/"
    endpoints_out: list[dict[str, Any]] = []
    main_flow: list[dict[str, Any]] = []
    try:
        # 前置：FE / BE 轻检
        with httpx.Client(follow_redirects=True, timeout=REQUEST_TIMEOUT) as anon:
            t0 = time.perf_counter()
            try:
                fe = anon.get(frontend_url.rstrip("/") + "/", timeout=REQUEST_TIMEOUT)
                fe_ok = fe.status_code < 500
                main_flow.append(
                    {
                        "name": "fe_health",
                        "ok": fe_ok,
                        "error_source": None if fe_ok else "factory",
                        "http_status": fe.status_code,
                        "detail": None if fe_ok else "前端预览不可用",
                        "ms": int((time.perf_counter() - t0) * 1000),
                    }
                )
            except httpx.HTTPError as e:
                main_flow.append(
                    {
                        "name": "fe_health",
                        "ok": False,
                        "error_source": "factory",
                        "detail": f"前端不可达: {e.__class__.__name__}",
                        "ms": int((time.perf_counter() - t0) * 1000),
                    }
                )
            t1 = time.perf_counter()
            st, body, ferr = _request(anon, "GET", urljoin(base, "/api/meta"))
            if ferr:
                # meta 可能不存在，试 /
                st2, _, ferr2 = _request(anon, "GET", urljoin(base, "/"))
                be_ok = ferr2 is None and st2 is not None and st2 < 500
                main_flow.append(
                    {
                        "name": "be_health",
                        "ok": be_ok,
                        "error_source": None if be_ok else "factory",
                        "http_status": st2,
                        "detail": None if be_ok else (ferr2 or ferr),
                        "ms": int((time.perf_counter() - t1) * 1000),
                    }
                )
            else:
                be_ok = st is not None and st < 500
                main_flow.append(
                    {
                        "name": "be_health",
                        "ok": be_ok,
                        "error_source": None if be_ok else "student",
                        "http_status": st,
                        "student_body": body if not be_ok else None,
                        "ms": int((time.perf_counter() - t1) * 1000),
                    }
                )

        if not main_flow[0].get("ok") or not main_flow[1].get("ok"):
            return _summarize(
                backend_url=backend_url,
                frontend_url=frontend_url,
                inventory=inv,
                endpoints_out=[],
                main_flow=main_flow,
            )

        user, pwd = _portal_user(spec)
        sessions: dict[str, httpx.Client] = {}
        portal = httpx.Client(follow_redirects=True, timeout=REQUEST_TIMEOUT)
        admin = httpx.Client(follow_redirects=True, timeout=REQUEST_TIMEOUT)
        sessions["portal"] = portal
        sessions["admin"] = admin
        try:
            step = _login(portal, base, user, pwd)
            main_flow.append(step)
            step_a = _login(admin, base, "admin", "admin123")
            main_flow.append(step_a)

            ctx: dict[str, Any] = {}
            if step.get("ok"):
                _warm_context(portal, base, ctx)

            ticket_mode = _ticket_mode(spec, None)
            # gate 自检
            t_g = time.perf_counter()
            st_g, body_g, ferr_g = _request(
                portal, "GET", urljoin(base, "/api/gate/ticket-main-path")
            )
            if ferr_g:
                main_flow.append(
                    {
                        "name": "gate_self_check",
                        "ok": False,
                        "error_source": "factory",
                        "detail": ferr_g,
                        "ms": int((time.perf_counter() - t_g) * 1000),
                    }
                )
            else:
                data_g = _r_data(body_g)
                gate_ok = False
                gate_detail = None
                if isinstance(data_g, dict):
                    gate_ok = bool(data_g.get("ok"))
                    if data_g.get("mode"):
                        ticket_mode = _ticket_mode(spec, str(data_g.get("mode")))
                    if not gate_ok:
                        gate_detail = str(
                            data_g.get("message") or "主路径未通过"
                        )
                main_flow.append(
                    {
                        "name": "gate_self_check",
                        "ok": gate_ok,
                        "error_source": "student" if not gate_ok else None,
                        "http_status": st_g,
                        "detail": gate_detail,
                        "student_body": body_g if not gate_ok else None,
                        "ms": int((time.perf_counter() - t_g) * 1000),
                    }
                )

            # 全量 inventory
            for ep in inv.get("endpoints") or []:
                if not isinstance(ep, dict):
                    continue
                path = str(ep.get("path") or "")
                if path.startswith("/api/auth/login") or path.startswith("/api/auth/captcha"):
                    if "captcha" in path:
                        row = _probe_endpoint(
                            portal, base, ep, ctx, sessions, spec=spec
                        )
                    else:
                        row = {
                            "method": ep.get("method"),
                            "path": path,
                            "ok": True,
                            "skip": True,
                            "error_source": "skip",
                            "detail": "登录已在主流程覆盖，跳过重复 POST 以免踢会话",
                            "ms": 0,
                            "flow_keys": list(ep.get("flow_keys") or []),
                            "surface": ep.get("surface"),
                            "layer": "reachability",
                        }
                else:
                    row = _probe_endpoint(
                        portal, base, ep, ctx, sessions, spec=spec
                    )
                    if (
                        row.get("http_status") == 401
                        and str(ep.get("surface")) == "admin"
                        and step_a.get("ok")
                    ):
                        row = _probe_endpoint(
                            admin, base, ep, ctx, sessions, spec=spec
                        )
                endpoints_out.append(row)

            # 主流程业务：跟 gate.flow_api（考勤=请假→审批→销假；报修=申请→受理→完结；商城/预约另链）
            if step.get("ok"):
                _run_flow_api_business(
                    portal=portal,
                    admin=admin,
                    base=base,
                    spec=spec,
                    ctx=ctx,
                    ticket_mode=ticket_mode,
                    main_flow=main_flow,
                )
        finally:
            portal.close()
            admin.close()

        return _summarize(
            backend_url=backend_url,
            frontend_url=frontend_url,
            inventory=inv,
            endpoints_out=endpoints_out,
            main_flow=main_flow,
        )
    finally:
        lock.release()
        _release_busy(project_id)


def _summarize(
    *,
    backend_url: str,
    frontend_url: str,
    inventory: dict[str, Any],
    endpoints_out: list[dict[str, Any]],
    main_flow: list[dict[str, Any]],
) -> dict[str, Any]:
    skipped = sum(1 for e in endpoints_out if e.get("skip"))
    # 可达失败：factory 连接问题，或 5xx student
    factory_errors = sum(
        1
        for e in endpoints_out
        if e.get("error_source") == "factory" and not e.get("skip")
    )
    student_failures = sum(
        1
        for e in endpoints_out
        if e.get("error_source") == "student" and e.get("http_status", 0) >= 500
    )
    # 4xx 可达但记 student 展示：不进 student_failures 硬失败计数的「崩」；另计
    student_4xx = sum(
        1
        for e in endpoints_out
        if e.get("error_source") == "student"
        and isinstance(e.get("http_status"), int)
        and 400 <= e["http_status"] < 500
    )
    probed = len(endpoints_out)
    passed = sum(1 for e in endpoints_out if e.get("ok") and not e.get("skip"))

    mf_fail = [
        s
        for s in main_flow
        if not s.get("ok") and not s.get("skip")
    ]
    ok = (
        factory_errors == 0
        and student_failures == 0
        and not any(s.get("error_source") == "factory" and not s.get("ok") for s in main_flow)
        and not any(
            s.get("name")
            in (
                "my_tickets",
                "apply",
                "approve",
                "return",
                "complete",
                "checkin",
                "cart",
                "place",
                "reserve",
                "cancel",
                "favorites",
                "favorites_list",
                "publish",
                "flow_api_gap",
            )
            and not s.get("ok")
            and not s.get("skip")
            for s in main_flow
        )
    )
    # 主流程登录失败则整单失败
    for s in main_flow:
        if s.get("name", "").startswith("login:") and not s.get("ok"):
            ok = False
        if s.get("name") in ("fe_health", "be_health") and not s.get("ok"):
            ok = False

    summary_parts = [
        f"清单 {inventory.get('count', 0)}",
        f"探测 {probed}",
        f"可达通过 {passed}",
        f"跳过 {skipped}",
        f"工厂错 {factory_errors}",
        f"学生5xx {student_failures}",
        f"学生4xx {student_4xx}",
        f"主流程失败 {len(mf_fail)}",
    ]
    return {
        "ok": ok,
        "summary": " · ".join(summary_parts),
        "backend_url": backend_url,
        "frontend_url": frontend_url,
        "inventory_count": inventory.get("count", 0),
        "probed": probed,
        "passed": passed,
        "failed": factory_errors + student_failures,
        "skipped": skipped,
        "factory_errors": factory_errors
        + sum(1 for s in main_flow if s.get("error_source") == "factory" and not s.get("ok")),
        "student_failures": student_failures
        + sum(
            1
            for s in main_flow
            if s.get("error_source") == "student" and not s.get("ok") and not s.get("skip")
        ),
        "student_4xx": student_4xx,
        "endpoints": endpoints_out,
        "main_flow": main_flow,
    }
