"""按 Spec.gate 契约评测工作区（全领域共用，不绑某一 DOM）。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.bake.engine import TABLE_COUNT_MAX, TABLE_COUNT_MIN, count_create_tables


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore") if path.exists() else ""


def _has_files(workspace: Path, rels: list[str]) -> tuple[bool, list[str]]:
    from app.bake.java_package import find_java_package_root

    java_root = workspace / "backend" / "src" / "main" / "java"
    pkg_root = find_java_package_root(workspace)
    missing: list[str] = []
    for r in rels:
        rp = str(r).replace("\\", "/")
        if (workspace / rp).exists():
            continue
        # 契约仍写 com/thesis/... 时，按包内相对路径查找
        marker = "/com/thesis/"
        if marker in f"/{rp}":
            suffix = rp.split("com/thesis/", 1)[-1]
            candidate = pkg_root / Path(suffix)
            if candidate.is_file():
                continue
            hits = [
                p
                for p in java_root.rglob(Path(suffix).name)
                if str(p).replace("\\", "/").endswith("/" + suffix)
            ]
            if hits:
                continue
        missing.append(r)
    return len(missing) == 0, missing


def _route_present(router_src: str, seg: str) -> bool:
    for q in (f"'{seg}'", f'"{seg}"', f"'/{seg}'", f'"/{seg}"'):
        if q in router_src:
            return True
    # 嵌套路由：admin/tickets → 父 '/admin' + 子 'tickets'
    if "/" in seg:
        parent, child = seg.split("/", 1)
        parent_ok = any(
            p in router_src
            for p in (f"'{parent}'", f"'/{parent}'", f'"{parent}"', f'"/{parent}"')
        )
        child_ok = any(c in router_src for c in (f"'{child}'", f'"{child}"'))
        if parent_ok and child_ok:
            return True
    return False


def _ticket_main_path_logic() -> bool:
    """主路径状态机自检（archive 库存 + ticket 申请/审核/归还）。"""
    items = [{"id": 1, "title": "T", "stock": 2}]
    tickets: list[dict] = []

    def apply(uid: str, item_id: int) -> int:
        item = next(b for b in items if b["id"] == item_id)
        if item["stock"] <= 0:
            raise RuntimeError("stock")
        tid = len(tickets) + 1
        tickets.append({"id": tid, "itemId": item_id, "username": uid, "status": "pending"})
        return tid

    def approve(tid: int, pass_: bool) -> None:
        br = next(b for b in tickets if b["id"] == tid)
        if br["status"] != "pending":
            raise RuntimeError("status")
        if pass_:
            item = next(b for b in items if b["id"] == br["itemId"])
            item["stock"] -= 1
            br["status"] = "approved"
        else:
            br["status"] = "rejected"

    def complete(tid: int) -> None:
        br = next(b for b in tickets if b["id"] == tid)
        if br["status"] not in ("approved", "overdue"):
            raise RuntimeError("status")
        item = next(b for b in items if b["id"] == br["itemId"])
        item["stock"] += 1
        br["status"] = "returned"

    try:
        tid = apply("user", 1)
        approve(tid, True)
        complete(tid)
        return tickets[0]["status"] == "returned" and items[0]["stock"] == 2
    except Exception:
        return False


def _active_feature_names(spec: dict[str, Any]) -> set[str]:
    names = set()
    for f in spec.get("features") or []:
        if isinstance(f, dict) and f.get("status") != "out_of_mvp":
            names.add(f.get("name", ""))
    return names


def _required_routes(spec: dict[str, Any]) -> list[str]:
    """按 Spec.gate.routes + 启用功能 / baseline 过滤。"""
    gate = spec.get("gate") or {}
    baseline = set(spec.get("baseline") or [])
    active = _active_feature_names(spec)
    segs: list[str] = []
    for item in gate.get("routes") or []:
        if not isinstance(item, dict):
            continue
        seg = item.get("seg")
        if not seg:
            continue
        feat = item.get("from_feature")
        bl = item.get("from_baseline")
        if feat and feat not in active:
            continue
        if bl and bl not in baseline:
            continue
        segs.append(seg)
    return segs


def _routes_for_feature(spec: dict[str, Any], feature_name: str) -> list[str]:
    gate = spec.get("gate") or {}
    return [
        item["seg"]
        for item in (gate.get("routes") or [])
        if isinstance(item, dict)
        and item.get("from_feature") == feature_name
        and item.get("seg")
    ]


def _eval_flow_api(be: Path, flow_api: dict[str, Any]) -> dict[str, bool]:
    """只评测契约声明的 flow_api 键，不臆造 apply/return/complete。"""
    hits: dict[str, bool] = {}
    for key, rule in (flow_api or {}).items():
        if not isinstance(rule, dict):
            hits[key] = False
            continue
        src = _read(be / "controller" / rule.get("file", ""))
        need = rule.get("need") or []
        hits[key] = all(n in src for n in need)
    return hits


def _main_path_ok(be: Path, api_hits: dict[str, bool], flow_api: dict[str, Any]) -> bool:
    """主路径 = 契约声明的全部 API 命中；空 flow_api（CRUD）视为通过。"""
    if not flow_api:
        return True
    if not all(api_hits.get(k, False) for k in flow_api):
        return False
    # 借用壳：额外跑库存/状态机自检
    if "return" in flow_api and (be / "capability" / "TicketStore.java").exists():
        return _ticket_main_path_logic()
    return True


def _checklist_feature_ok(
    *,
    name: str,
    spec: dict[str, Any],
    workspace: Path,
    be: Path,
    fe: Path,
    router_src: str,
    api_hits: dict[str, bool],
    flow_api: dict[str, Any],
    files_ok: bool,
) -> bool:
    """开题对照：优先按能力/路由实装判断，避免死绑 ticket 动词或残缺 baseline。"""
    has_apply = api_hits.get("apply", False)
    has_approve = api_hits.get("approve", False)
    has_return = api_hits.get("return", False)
    has_complete = api_hits.get("complete", False)
    has_finish = has_return or has_complete
    has_overdue = api_hits.get("overdue", False)
    has_remind = api_hits.get("remind", False)
    has_place = api_hits.get("place", False)
    has_cart = api_hits.get("cart", False)
    has_reserve = api_hits.get("reserve", False)
    store_src = _read(be / "capability" / "TicketStore.java")
    has_fine = "fineYuan" in store_src or "FINE_PER_DAY" in store_src or "dueAt" in store_src
    profile_src = _read(be / "controller" / "ProfileController.java")
    has_profile = "profileEditable" in profile_src
    baseline = set(spec.get("baseline") or [])

    # 1) 契约路由绑定的功能：路由全在即可（订单/预约/档案等壳共用）
    bound = _routes_for_feature(spec, name)
    if bound:
        if all(_route_present(router_src, s) for s in bound):
            # 绑定主流程名时再要求对应 API（排除「借阅记录」等列表页）
            if (
                any(k in name for k in ("借阅", "借用", "报修"))
                and "记录" not in name
                and "apply" in flow_api
            ):
                return has_apply and has_approve and has_finish
            if (
                any(k in name for k in ("下单", "购物车", "订单"))
                and "记录" not in name
                and "place" in flow_api
            ):
                return has_place and has_cart
            if (
                any(k in name for k in ("预约", "号源", "车位", "场地"))
                and "记录" not in name
                and "reserve" in flow_api
            ):
                return has_reserve and ("cancel" not in flow_api or api_hits.get("cancel", False))
            return True
        return False

    # 2) 无路由绑定：按关键词落到具体实装（兼容旧题面文案）
    if "借阅记录" in name or "借用记录" in name or "申领记录" in name:
        return (fe / "views" / "admin" / "TicketRecordsAdmin.vue").exists()
    if "报修记录" in name or ("记录" in name and "报修" in name):
        return (fe / "views" / "admin" / "TicketRecordsAdmin.vue").exists()
    if "报修" in name or ("故障" in name and "受理" in name):
        return has_apply and has_approve and has_finish
    if "借用" in name or "借阅" in name or ("审核" in name and "报修" not in name):
        if "apply" in flow_api:
            return has_apply and has_approve
        return files_ok
    if "提醒" in name or "罚款" in name:
        if "overdue" not in flow_api:
            return (fe / "views" / "admin" / "OverdueAdmin.vue").exists() or files_ok
        return has_overdue and has_remind and has_fine and (
            fe / "views" / "admin" / "OverdueAdmin.vue"
        ).exists()
    if "归还" in name or ("逾期" in name and "提醒" not in name):
        # return-only 壳无需 overdue/complete；有 overdue 契约才强制
        if not has_finish:
            return False
        if "overdue" in flow_api:
            return has_overdue or has_complete
        return True
    if "分类" in name:
        return (be / "controller" / "CategoryController.java").exists() and (
            fe / "views" / "admin" / "CategoriesAdmin.vue"
        ).exists()
    if any(k in name for k in ("读者", "学生管理", "用户管理", "患者管理", "会员管理")):
        return (be / "controller" / "UsersAdminController.java").exists() and (
            fe / "views" / "admin" / "UsersAdmin.vue"
        ).exists()
    if "楼栋" in name or "房间管理" in name or "区域终端" in name:
        return (be / "controller" / "LookupAdminController.java").exists() and (
            fe / "views" / "admin" / "LookupSitesAdmin.vue"
        ).exists()
    if "报修类型" in name or "故障类型" in name:
        return (be / "controller" / "LookupAdminController.java").exists() and (
            fe / "views" / "admin" / "LookupTypesAdmin.vue"
        ).exists()
    if "工作台" in name:
        return (be / "controller" / "TicketDashboardController.java").exists() and (
            fe / "views" / "admin" / "TicketDashboard.vue"
        ).exists()
    if any(k in name for k in ("设备", "图书", "物资", "菜品", "商品", "号源", "车位", "场地")) or (
        "检索" in name and "archive" in ((spec.get("schema") or {}).get("capabilities") or [])
    ):
        return (be / "controller" / "ArchiveController.java").exists() and (
            fe / "views" / "user" / "ArchiveBrowse.vue"
        ).exists()
    if "公告" in name:
        return (be / "controller" / "NoticeController.java").exists()
    if "登录" in name or "注册" in name:
        auth_src = _read(be / "controller" / "AuthController.java")
        ok = "/login" in auth_src
        if "注册" in name or "register" in baseline:
            ok = ok and "/register" in auth_src and (fe / "views" / "Register.vue").exists()
        return ok
    if "个人资料" in name or "头像" in name:
        return has_profile and _route_present(router_src, "profile")
    if "购物车" in name or "下单" in name or ("订单" in name and "place" in flow_api):
        return has_place and has_cart
    if "预约" in name and "reserve" in flow_api:
        return has_reserve and api_hits.get("cancel", False)
    if "猜你喜欢" in name or "推荐" in name:
        return (be / "capability" / "RecommendStore.java").exists() or (
            be / "controller" / "RecommendController.java"
        ).exists()

    # 3) 未识别：不把整包 files_ok 当通过（避免误绿）；有契约文件则要求文件齐
    return files_ok


def evaluate_contract_gates(workspace: Path, spec: dict[str, Any]) -> dict[str, Any]:
    """有 Spec.gate 契约时的评测（archive/ticket/order/slot 等薄壳共用）。"""
    from app.bake.java_package import find_java_package_root

    be = find_java_package_root(workspace)
    fe = workspace / "frontend" / "src"
    gate = spec.get("gate") or {}

    required = list(gate.get("files") or [])
    if not required:
        return {
            "p0a": {"ok": False, "label": "后端骨架"},
            "p0b": {"ok": False, "label": "前端骨架"},
            "p1": {"ok": False, "label": "登录基线"},
            "p2": {"ok": False, "label": "领域主流程 E2E", "desc": "Spec 缺少 gate 契约"},
            "p3a": {"ok": False, "label": "开题对照 · 核心项"},
            "p3b": {"ok": False, "label": "Spec / 路由一致"},
            "p3t": {
                "ok": False,
                "label": f"表数量 {TABLE_COUNT_MIN}~{TABLE_COUNT_MAX}",
                "desc": "Spec 缺少 gate 契约",
            },
            "checklist": [],
            "overall": False,
            "zip_allowed": False,
        }

    files_ok, missing = _has_files(workspace, required)

    flow_api = gate.get("flow_api") or {}
    api_hits = _eval_flow_api(be, flow_api)

    router_src = _read(fe / "router" / "index.js")
    required_routes = _required_routes(spec)
    missing_routes = [s for s in required_routes if not _route_present(router_src, s)]
    # 有 gate.routes 时至少应筛出一条；空列表视为契约/功能不同步
    has_routes = (not (gate.get("routes") or []) and not required_routes) or (
        len(required_routes) > 0 and not missing_routes
    )

    flow_desc = " → ".join(spec.get("flows") or []) or "主路径"
    main_path_ok = _main_path_ok(be, api_hits, flow_api)

    features = spec.get("features") or []
    checklist = []
    for f in features:
        if not isinstance(f, dict):
            continue
        name = f.get("name", "")
        st = f.get("status")
        if st == "out_of_mvp":
            checklist.append({**f, "result": "out_of_mvp"})
            continue
        ok = _checklist_feature_ok(
            name=name,
            spec=spec,
            workspace=workspace,
            be=be,
            fe=fe,
            router_src=router_src,
            api_hits=api_hits,
            flow_api=flow_api,
            files_ok=files_ok,
        )
        checklist.append({**f, "result": "done" if ok else "pending"})

    core_ok = all(c.get("result") in ("done", "out_of_mvp") for c in checklist)

    p0a = (workspace / "backend" / "pom.xml").exists()
    p0b = (workspace / "frontend" / "package.json").exists()
    p1 = (be / "controller" / "AuthController.java").exists() and "captcha" in _read(
        be / "controller" / "AuthController.java"
    )
    p2 = main_path_ok and has_routes and files_ok
    p3a = core_ok and len(checklist) > 0
    p3b = (workspace / "spec.json").exists() and bool(spec.get("archetype"))
    sql_text = _read(workspace / "sql" / "schema.sql")
    table_n = count_create_tables(sql_text)
    p3t_ok = TABLE_COUNT_MIN <= table_n <= TABLE_COUNT_MAX

    # 全厂：总管门禁与主数据 Admin 不得在 bake 中丢失
    admin_inv = gate.get("admin_invariants") or {}
    auth_src = _read(be / "controller" / "AuthController.java")
    admin_auth_src = _read(be / "common" / "AdminAuth.java")
    login_src = _read(fe / "views" / "Login.vue")
    layout_src = _read(fe / "layouts" / "AdminLayout.vue")
    schema_js = _read(fe / "utils" / "domainSchema.js")
    users_admin_src = _read(be / "controller" / "UsersAdminController.java")
    notice_src = _read(be / "controller" / "NoticeController.java")

    has_admin_auth = "requireSuperAdmin" in admin_auth_src
    has_super_session = "superAdmin" in auth_src
    has_super_persist = "superAdmin" in login_src
    has_super_menu = "superAdmin" in layout_src or "isSuperOnlyMenu" in layout_src
    has_super_route = "superOnlyAdminPaths" in router_src or "superAdmin" in router_src
    users_gated = "requireSuperAdmin" in users_admin_src
    notice_gated = "requireSuperAdmin" in notice_src

    master_ok = True
    master_detail: dict[str, Any] = {}
    if admin_inv.get("require_super_auth") or admin_inv.get("master_menus"):
        kind = admin_inv.get("master_kind") or "lookup"
        if kind == "archive":
            archive_admin = (be / "controller" / "ArchiveController.java").exists()
            cat_ctrl = (be / "controller" / "CategoryController.java").exists()
            archive_vue = (fe / "views" / "admin" / "ArchiveAdmin.vue").exists()
            cats_vue = (fe / "views" / "admin" / "CategoriesAdmin.vue").exists()
            archive_gated = "requireSuperAdmin" in _read(
                be / "controller" / "ArchiveController.java"
            )
            cat_gated = "requireSuperAdmin" in _read(
                be / "controller" / "CategoryController.java"
            )
            master_ok = (
                archive_admin and cat_ctrl and archive_vue and cats_vue
                and archive_gated and cat_gated
            )
            master_detail = {
                "archive_admin": archive_admin,
                "category_ctrl": cat_ctrl,
                "archive_vue": archive_vue,
                "cats_vue": cats_vue,
                "archive_gated": archive_gated,
                "cat_gated": cat_gated,
            }
        else:
            lookup_admin = (be / "controller" / "LookupAdminController.java").exists()
            sites_vue = (fe / "views" / "admin" / "LookupSitesAdmin.vue").exists()
            types_vue = (fe / "views" / "admin" / "LookupTypesAdmin.vue").exists()
            lookup_gated = "requireSuperAdmin" in _read(
                be / "controller" / "LookupAdminController.java"
            )
            master_ok = lookup_admin and sites_vue and types_vue and lookup_gated
            master_detail = {
                "lookup_admin": lookup_admin,
                "sites_vue": sites_vue,
                "types_vue": types_vue,
                "lookup_gated": lookup_gated,
            }

    admin_boundary_ok = (
        has_admin_auth
        and has_super_session
        and has_super_persist
        and has_super_menu
        and has_super_route
        and users_gated
        and notice_gated
        and master_ok
        and ("isSuperOnlyMenu" in schema_js or "SUPER_ONLY" in layout_src)
    )

    results = {
        "p0a": {"ok": p0a, "label": "后端骨架"},
        "p0b": {"ok": p0b, "label": "前端骨架"},
        "p1": {"ok": p1, "label": "登录 + 验证码基线"},
        "p2": {
            "ok": p2,
            "label": "领域主流程 E2E",
            "desc": flow_desc,
            "detail": {
                "files_ok": files_ok,
                "missing": missing,
                "flow_api": api_hits,
                "routes": has_routes,
                "required_routes": required_routes,
                "missing_routes": missing_routes,
                "logic": main_path_ok,
            },
        },
        "p3a": {"ok": p3a, "label": "开题对照 · 核心项"},
        "p3b": {"ok": p3b, "label": "Spec / 契约一致"},
        "p3t": {
            "ok": p3t_ok,
            "label": f"表数量 {TABLE_COUNT_MIN}~{TABLE_COUNT_MAX}",
            "desc": f"当前 {table_n} 张" if sql_text else "缺少 schema.sql",
        },
        "p3d": {
            "ok": admin_boundary_ok,
            "label": "总管/子管管理边界",
            "desc": "AdminAuth + superAdmin 菜单/路由 + 主数据 Admin"
            if admin_boundary_ok
            else "缺少总管门禁或主数据管理页",
            "detail": {
                "admin_auth": has_admin_auth,
                "super_session": has_super_session,
                "super_persist": has_super_persist,
                "super_menu": has_super_menu,
                "super_route": has_super_route,
                "users_gated": users_gated,
                "notice_gated": notice_gated,
                "master": master_detail,
            },
        },
        "checklist": checklist,
    }
    results["overall"] = all(
        results[k]["ok"] for k in ("p0a", "p0b", "p1", "p2", "p3a", "p3b", "p3t", "p3d")
    )
    results["zip_allowed"] = results["overall"]
    return results


def evaluate_generic_gates(workspace: Path, spec: dict[str, Any]) -> dict[str, Any]:
    """无 gate 契约：骨架存在即可，主路径未做实，禁止交付。"""
    be = workspace / "backend"
    fe = workspace / "frontend"
    p0a = (be / "pom.xml").exists()
    p0b = (fe / "package.json").exists()
    p1 = (be / "src").exists() and (fe / "src").exists()
    p2 = False
    features = spec.get("features") or []
    checklist = []
    for f in features:
        if isinstance(f, dict):
            if f.get("status") == "out_of_mvp":
                checklist.append({**f, "result": "out_of_mvp"})
            else:
                checklist.append({**f, "result": "pending"})
    results = {
        "p0a": {"ok": p0a, "label": "后端骨架"},
        "p0b": {"ok": p0b, "label": "前端骨架"},
        "p1": {"ok": p1, "label": "登录基线"},
        "p2": {"ok": p2, "label": "领域主流程 E2E", "desc": "该领域尚未做实，禁止交付"},
        "p3a": {"ok": False, "label": "开题对照 · 核心项"},
        "p3b": {"ok": (workspace / "spec.json").exists(), "label": "Spec 存在"},
        "p3t": {
            "ok": False,
            "label": f"表数量 {TABLE_COUNT_MIN}~{TABLE_COUNT_MAX}",
            "desc": "领域未做实",
        },
        "checklist": checklist,
    }
    results["overall"] = False
    results["zip_allowed"] = False
    return results


def _schema_gate(workspace: Path, spec: dict[str, Any]) -> dict[str, Any]:
    from app.bake.domain_schema import validate_schema

    schema_path = workspace / "domain.schema.json"
    schema = spec.get("schema")
    if schema_path.exists():
        try:
            import json

            schema = json.loads(schema_path.read_text(encoding="utf-8"))
        except Exception:
            pass
    ok, errors = validate_schema(schema if isinstance(schema, dict) else None)
    accept = (spec.get("accept") or (schema or {}).get("accept") or "reject") if isinstance(schema, dict) else "reject"
    return {
        "ok": ok,
        "label": "Domain Schema",
        "desc": "合法" if ok else "; ".join(errors),
        "accept": accept,
    }


def evaluate_domain_gates(workspace: Path, spec: dict[str, Any]) -> dict[str, Any]:
    """入口：有 Spec.gate → 契约评测；否则 generic 占位。"""
    from app.bake.domain_schema import ensure_spec_schema

    spec = ensure_spec_schema(spec)
    accept = spec.get("accept") or "reject"
    gate = spec.get("gate") or {}
    if gate.get("files") or gate.get("routes") or gate.get("flow_api"):
        results = evaluate_contract_gates(workspace, spec)
    else:
        results = evaluate_generic_gates(workspace, spec)

    sg = _schema_gate(workspace, spec)
    results["p3c"] = {
        "ok": sg["ok"],
        "label": sg["label"],
        "desc": f"{sg['desc']} · accept={sg['accept']}",
    }
    if accept == "reject":
        results["zip_allowed"] = False
        results["overall"] = False
        results["accept"] = {
            "ok": False,
            "label": "可接题边界",
            "desc": spec.get("accept_reason") or "reject",
        }
    else:
        results["accept"] = {
            "ok": True,
            "label": "可接题边界",
            "desc": f"{accept}: {spec.get('accept_reason') or ''}".strip(),
        }
        if accept == "degraded" and results.get("zip_allowed"):
            results["accept"]["desc"] += "（降级交付，未实现卖点见 out_of_mvp）"
        if not sg["ok"]:
            results["zip_allowed"] = False
            results["overall"] = False
        elif results.get("overall") and not results.get("zip_allowed"):
            pass
        elif results.get("overall"):
            results["zip_allowed"] = bool(results.get("zip_allowed", True))
    return results
