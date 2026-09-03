"""薄领域门禁契约：文件清单 + gate_* 工厂（非 gates/ 评测包）。"""

from __future__ import annotations


# 薄报修壳门禁：文件均在 baseline，多领域共用（文案用 features 对齐）
_GATE_STANDALONE_TICKET_FILES = [
    "backend/src/main/java/com/thesis/capability/TicketStore.java",
    "backend/src/main/java/com/thesis/capability/TicketLookupStore.java",
    "backend/src/main/java/com/thesis/common/AdminAuth.java",
    "backend/src/main/java/com/thesis/controller/TicketController.java",
    "backend/src/main/java/com/thesis/controller/TicketDashboardController.java",
    "backend/src/main/java/com/thesis/controller/LookupController.java",
    "backend/src/main/java/com/thesis/controller/LookupAdminController.java",
    "backend/src/main/java/com/thesis/controller/UsersAdminController.java",
    "backend/src/main/java/com/thesis/controller/GateController.java",
    "backend/src/main/java/com/thesis/controller/NoticeController.java",
    "backend/src/main/java/com/thesis/controller/MessageController.java",
    "backend/src/main/java/com/thesis/service/MessageStore.java",
    "backend/src/main/java/com/thesis/controller/AuthController.java",
    "backend/src/main/java/com/thesis/controller/ProfileController.java",
    "backend/src/main/java/com/thesis/config/DomainRuntimeBinder.java",
    "frontend/src/views/user/MyTickets.vue",
    "frontend/src/views/admin/TicketsAdmin.vue",
    "frontend/src/views/admin/TicketRecordsAdmin.vue",
    "frontend/src/views/admin/TicketDashboard.vue",
    "frontend/src/views/admin/LookupSitesAdmin.vue",
    "frontend/src/views/admin/LookupTypesAdmin.vue",
    "frontend/src/views/admin/UsersAdmin.vue",
    "frontend/src/views/Notices.vue",
    "frontend/src/views/NoticeDetail.vue",
    "frontend/src/views/admin/NoticesAdmin.vue",
    "frontend/src/components/MessageBell.vue",
    "frontend/src/views/Profile.vue",
    "frontend/src/views/Login.vue",
    "frontend/src/views/Register.vue",
    "frontend/src/layouts/PortalLayout.vue",
    "frontend/src/layouts/AdminLayout.vue",
    "frontend/src/utils/domainSchema.js",
    "frontend/src/appDelivered.js",
    "frontend/src/router/index.js",
    "sql/schema.sql",
]


def gate_standalone_ticket(
    *,
    flow_feature: str,
    records_feature: str,
    users_feature: str,
    site_feature: str,
    type_feature: str,
    dashboard_feature: str = "管理端工作台",
    notice_feature: str = "公告管理",
) -> dict:
    """报修类薄领域共用 ZIP/路由/主路径门禁。"""
    return {
        "routes": [
            {"seg": "tickets", "from_feature": flow_feature},
            {"seg": "admin/dashboard", "from_feature": dashboard_feature},
            {"seg": "admin/tickets", "from_feature": flow_feature},
            {"seg": "admin/ticket-records", "from_feature": records_feature},
            {"seg": "admin/sites", "from_feature": site_feature},
            {"seg": "admin/types", "from_feature": type_feature},
            {"seg": "admin/users", "from_feature": users_feature},
            {"seg": "admin/notices", "from_feature": notice_feature},
            {"seg": "notices", "from_feature": notice_feature},
            {"seg": "notices/:id", "from_feature": notice_feature},
            {"seg": "profile", "from_baseline": "profile"},
            {"seg": "register", "from_baseline": "register"},
        ],
        "files": list(_GATE_STANDALONE_TICKET_FILES),
        "flow_api": {
            "apply": {"file": "TicketController.java", "need": ["/apply", "applyStandalone"]},
            "approve": {"file": "TicketController.java", "need": ["approve"]},
            "complete": {"file": "TicketController.java", "need": ["/complete", "complete"]},
        },
        "admin_invariants": {
            "require_super_auth": True,
            "master_kind": "lookup",
            "master_menus": ["lookup_site", "lookup_type"],
            "super_menus": ["users", "content", "lookup_site", "lookup_type"],
        },
    }


# 薄借用壳：档案检索 + 单据流（设备/组 A；文件均在 baseline）
_GATE_ARCHIVE_TICKET_FILES = [
    "backend/src/main/java/com/thesis/capability/ArchiveStore.java",
    "backend/src/main/java/com/thesis/capability/TicketStore.java",
    "backend/src/main/java/com/thesis/capability/RecommendStore.java",
    "backend/src/main/java/com/thesis/common/AdminAuth.java",
    "backend/src/main/java/com/thesis/controller/ArchiveController.java",
    "backend/src/main/java/com/thesis/controller/CategoryController.java",
    "backend/src/main/java/com/thesis/controller/TicketController.java",
    "backend/src/main/java/com/thesis/controller/TicketDashboardController.java",
    "backend/src/main/java/com/thesis/controller/RecommendController.java",
    "backend/src/main/java/com/thesis/controller/UsersAdminController.java",
    "backend/src/main/java/com/thesis/controller/GateController.java",
    "backend/src/main/java/com/thesis/controller/NoticeController.java",
    "backend/src/main/java/com/thesis/controller/MessageController.java",
    "backend/src/main/java/com/thesis/service/MessageStore.java",
    "backend/src/main/java/com/thesis/controller/AuthController.java",
    "backend/src/main/java/com/thesis/controller/ProfileController.java",
    "backend/src/main/java/com/thesis/config/DomainRuntimeBinder.java",
    "frontend/src/views/user/ArchiveBrowse.vue",
    "frontend/src/components/RecommendStrip.vue",
    "frontend/src/components/MessageBell.vue",
    "frontend/src/views/user/MyTickets.vue",
    "frontend/src/views/admin/ArchiveAdmin.vue",
    "frontend/src/views/admin/CategoriesAdmin.vue",
    "frontend/src/views/admin/TicketsAdmin.vue",
    "frontend/src/views/admin/TicketRecordsAdmin.vue",
    "frontend/src/views/admin/TicketDashboard.vue",
    "frontend/src/views/admin/UsersAdmin.vue",
    "frontend/src/views/Notices.vue",
    "frontend/src/views/NoticeDetail.vue",
    "frontend/src/views/admin/NoticesAdmin.vue",
    "frontend/src/views/Profile.vue",
    "frontend/src/views/Login.vue",
    "frontend/src/views/Register.vue",
    "frontend/src/layouts/PortalLayout.vue",
    "frontend/src/layouts/AdminLayout.vue",
    "frontend/src/utils/domainSchema.js",
    "frontend/src/appDelivered.js",
    "frontend/src/router/index.js",
    "sql/schema.sql",
]

_GATE_OVERDUE_FILE = "frontend/src/views/admin/OverdueAdmin.vue"


def gate_archive_ticket(
    *,
    archive_feature: str,
    flow_feature: str,
    records_feature: str,
    users_feature: str,
    category_feature: str = "分类管理",
    overdue_feature: str = "归还 / 逾期",
    dashboard_feature: str = "管理端工作台",
    notice_feature: str = "公告管理",
    with_deadline: bool = True,
    user_publish: bool = False,
    publish_feature: str = "用户发帖",
) -> dict:
    """借用/收藏类薄领域：archive + ticket_flow（±quota ±deadline）共用门禁。"""
    routes = [
        {"seg": "archive", "from_feature": archive_feature},
        {"seg": "tickets", "from_feature": flow_feature},
        {"seg": "admin/dashboard", "from_feature": dashboard_feature},
        {"seg": "admin/archive", "from_feature": archive_feature},
        {"seg": "admin/categories", "from_feature": category_feature},
        {"seg": "admin/tickets", "from_feature": flow_feature},
        {"seg": "admin/ticket-records", "from_feature": records_feature},
        {"seg": "admin/users", "from_feature": users_feature},
        {"seg": "admin/notices", "from_feature": notice_feature},
        {"seg": "notices", "from_feature": notice_feature},
        {"seg": "notices/:id", "from_feature": notice_feature},
        {"seg": "profile", "from_baseline": "profile"},
        {"seg": "register", "from_baseline": "register"},
    ]
    files = list(_GATE_ARCHIVE_TICKET_FILES)
    if user_publish:
        routes.insert(1, {"seg": "my-archive", "from_feature": publish_feature})
        files.append("frontend/src/views/user/MyArchive.vue")
    if with_deadline:
        routes.insert(
            7 + (1 if user_publish else 0),
            {"seg": "admin/overdue", "from_feature": overdue_feature},
        )
        files.append(_GATE_OVERDUE_FILE)
    flow_api = {
        "apply": {"file": "TicketController.java", "need": ["/apply", "TicketStore.apply"]},
        "approve": {"file": "TicketController.java", "need": ["approve"]},
        "return": {"file": "TicketController.java", "need": ["/return", "complete"]},
    }
    if user_publish:
        flow_api["publish"] = {
            "file": "ArchiveController.java",
            "need": ["/publish", "ArchiveStore.addUserPost"],
        }
    if with_deadline:
        flow_api["overdue"] = {"file": "TicketController.java", "need": ["/overdue", "markOverdue"]}
        flow_api["remind"] = {"file": "TicketController.java", "need": ["/remind", "remind"]}
    return {
        "routes": routes,
        "files": files,
        "flow_api": flow_api,
        "admin_invariants": {
            "require_super_auth": True,
            "master_kind": "archive",
            "master_menus": ["archive", "category"],
            "super_menus": ["users", "content", "archive", "category"],
        },
    }


_GATE_ORDER_FILES = [
    "backend/src/main/java/com/thesis/capability/ArchiveStore.java",
    "backend/src/main/java/com/thesis/capability/OrderStore.java",
    "backend/src/main/java/com/thesis/controller/ArchiveController.java",
    "backend/src/main/java/com/thesis/controller/OrderController.java",
    "backend/src/main/java/com/thesis/controller/TicketDashboardController.java",
    "backend/src/main/java/com/thesis/controller/MessageController.java",
    "backend/src/main/java/com/thesis/service/MessageStore.java",
    "frontend/src/views/user/ArchiveBrowse.vue",
    "frontend/src/views/user/Cart.vue",
    "frontend/src/views/user/MyOrders.vue",
    "frontend/src/views/admin/ArchiveAdmin.vue",
    "frontend/src/views/admin/OrdersAdmin.vue",
    "frontend/src/views/admin/TicketDashboard.vue",
    "frontend/src/components/MessageBell.vue",
    "frontend/src/layouts/PortalLayout.vue",
    "frontend/src/layouts/AdminLayout.vue",
    "frontend/src/utils/apiCalls.js",
    "frontend/src/router/index.js",
    "sql/schema.sql",
]

_GATE_SLOT_FILES = [
    "backend/src/main/java/com/thesis/capability/ArchiveStore.java",
    "backend/src/main/java/com/thesis/capability/SlotStore.java",
    "backend/src/main/java/com/thesis/controller/ArchiveController.java",
    "backend/src/main/java/com/thesis/controller/SlotController.java",
    "backend/src/main/java/com/thesis/controller/TicketDashboardController.java",
    "backend/src/main/java/com/thesis/controller/MessageController.java",
    "backend/src/main/java/com/thesis/service/MessageStore.java",
    "frontend/src/views/user/ArchiveBrowse.vue",
    "frontend/src/views/user/SlotBook.vue",
    "frontend/src/views/user/MyReservations.vue",
    "frontend/src/views/admin/ArchiveAdmin.vue",
    "frontend/src/views/admin/ReservationsAdmin.vue",
    "frontend/src/views/admin/TicketDashboard.vue",
    "frontend/src/components/MessageBell.vue",
    "frontend/src/layouts/PortalLayout.vue",
    "frontend/src/layouts/AdminLayout.vue",
    "frontend/src/router/index.js",
    "sql/schema.sql",
]

_GATE_LOYALTY_FILES = [
    "backend/src/main/java/com/thesis/capability/LoyaltyStore.java",
    "backend/src/main/java/com/thesis/controller/LoyaltyController.java",
    "frontend/src/views/user/Cart.vue",
    "frontend/src/views/admin/UsersAdmin.vue",
    "frontend/src/utils/domainSchema.js",
]


_GATE_GUESTBOOK_FILES = [
    "backend/src/main/java/com/thesis/service/GuestbookStore.java",
    "backend/src/main/java/com/thesis/controller/GuestbookController.java",
    "frontend/src/views/Guestbook.vue",
    "frontend/src/views/admin/GuestbookAdmin.vue",
    "frontend/src/layouts/PortalLayout.vue",
    "frontend/src/layouts/AdminLayout.vue",
    "frontend/src/router/index.js",
]


def merge_guestbook_gate(gate: dict, caps: list[str] | None) -> dict:
    """叠加留言板文件、路由与 flow_api。"""
    caps = set(caps or [])
    if "guestbook" not in caps:
        return gate
    out = dict(gate or {})
    files = list(out.get("files") or [])
    for f in _GATE_GUESTBOOK_FILES:
        if f not in files:
            files.append(f)
    out["files"] = files
    routes = list(out.get("routes") or [])
    have = {r.get("seg") for r in routes if isinstance(r, dict)}
    if "guestbook" not in have:
        routes.append({"seg": "guestbook", "from_feature": "访客留言"})
    if "admin/guestbook" not in have:
        routes.append({"seg": "admin/guestbook", "from_feature": "访客留言"})
    out["routes"] = routes
    flow = dict(out.get("flow_api") or {})
    flow["guestbook"] = {"file": "GuestbookController.java", "need": ["/api/guestbook"]}
    out["flow_api"] = flow
    inv = dict(out.get("admin_invariants") or {})
    super_menus = list(inv.get("super_menus") or [])
    if "guestbook" not in super_menus:
        # 插在 content 前
        if "content" in super_menus:
            super_menus.insert(super_menus.index("content"), "guestbook")
        else:
            super_menus.append("guestbook")
        inv["super_menus"] = super_menus
        out["admin_invariants"] = inv
    return out


_GATE_AI_ASSISTANT_FILES = [
    "backend/src/main/java/com/thesis/service/AiAssistantStore.java",
    "backend/src/main/java/com/thesis/service/AiBizContext.java",
    "backend/src/main/java/com/thesis/service/DeepSeekClient.java",
    "backend/src/main/java/com/thesis/controller/AiAssistantController.java",
    "frontend/src/views/AiAssistant.vue",
    "frontend/src/views/admin/AiKnowledgeAdmin.vue",
    "frontend/src/components/AiAssistantFloat.vue",
    "frontend/src/layouts/PortalLayout.vue",
    "frontend/src/layouts/AdminLayout.vue",
    "frontend/src/router/index.js",
]


def merge_ai_assistant_gate(gate: dict, caps: list[str] | None) -> dict:
    """叠加 AI 助手文件、路由与 flow_api。"""
    caps = set(caps or [])
    if "ai_assistant" not in caps:
        return gate
    out = dict(gate or {})
    files = list(out.get("files") or [])
    for f in _GATE_AI_ASSISTANT_FILES:
        if f not in files:
            files.append(f)
    out["files"] = files
    routes = list(out.get("routes") or [])
    have = {r.get("seg") for r in routes if isinstance(r, dict)}
    if "ai-assistant" not in have:
        routes.append({"seg": "ai-assistant", "from_feature": "AI智能助手"})
    if "admin/ai-knowledge" not in have:
        routes.append({"seg": "admin/ai-knowledge", "from_feature": "AI智能助手"})
    out["routes"] = routes
    flow = dict(out.get("flow_api") or {})
    flow["ai_assistant"] = {
        "file": "AiAssistantController.java",
        "need": ["/api/ai-assistant"],
    }
    out["flow_api"] = flow
    inv = dict(out.get("admin_invariants") or {})
    super_menus = list(inv.get("super_menus") or [])
    if "ai_knowledge" not in super_menus:
        if "content" in super_menus:
            super_menus.insert(super_menus.index("content"), "ai_knowledge")
        else:
            super_menus.append("ai_knowledge")
        inv["super_menus"] = super_menus
        out["admin_invariants"] = inv
    return out


_GATE_EXAM_FILES = [
    "backend/src/main/java/com/thesis/service/ExamStore.java",
    "backend/src/main/java/com/thesis/controller/ExamController.java",
    "frontend/src/views/ExamPapers.vue",
    "frontend/src/views/ExamTake.vue",
    "frontend/src/views/ExamAttempts.vue",
    "frontend/src/views/ExamPractice.vue",
    "frontend/src/views/ExamRank.vue",
    "frontend/src/views/ExamWrongbook.vue",
    "frontend/src/views/admin/ExamQuestionsAdmin.vue",
    "frontend/src/views/admin/ExamPapersAdmin.vue",
    "frontend/src/layouts/PortalLayout.vue",
    "frontend/src/layouts/AdminLayout.vue",
    "frontend/src/router/index.js",
    "frontend/src/utils/menuRoutes.js",
]


_GATE_SURVEY_FILES = [
    "backend/src/main/java/com/thesis/service/SurveyStore.java",
    "backend/src/main/java/com/thesis/controller/SurveyController.java",
    "frontend/src/views/SurveyForms.vue",
    "frontend/src/views/SurveyFill.vue",
    "frontend/src/views/SurveyMine.vue",
    "frontend/src/views/admin/SurveyFormsAdmin.vue",
    "frontend/src/views/admin/SurveyStatsAdmin.vue",
    "frontend/src/layouts/PortalLayout.vue",
    "frontend/src/layouts/AdminLayout.vue",
    "frontend/src/router/index.js",
    "frontend/src/utils/menuRoutes.js",
]


_GATE_DOCLIB_FILES = [
    "backend/src/main/java/com/thesis/service/DoclibStore.java",
    "backend/src/main/java/com/thesis/controller/DoclibController.java",
    "frontend/src/views/DocBrowse.vue",
    "frontend/src/views/DocMine.vue",
    "frontend/src/views/admin/DocFilesAdmin.vue",
    "frontend/src/views/admin/DocLogsAdmin.vue",
    "frontend/src/layouts/PortalLayout.vue",
    "frontend/src/layouts/AdminLayout.vue",
    "frontend/src/router/index.js",
    "frontend/src/utils/menuRoutes.js",
]


_GATE_TIMEBANK_FILES = [
    "backend/src/main/java/com/thesis/service/TimebankStore.java",
    "backend/src/main/java/com/thesis/controller/TimebankController.java",
    "frontend/src/views/TimebankAccount.vue",
    "frontend/src/views/TimebankLedger.vue",
    "frontend/src/views/admin/TimebankAccountsAdmin.vue",
    "frontend/src/views/admin/TimebankLedgerAdmin.vue",
    "frontend/src/layouts/PortalLayout.vue",
    "frontend/src/layouts/AdminLayout.vue",
    "frontend/src/router/index.js",
    "frontend/src/utils/menuRoutes.js",
]


_GATE_SEAT_SELECT_FILES = [
    "backend/src/main/java/com/thesis/service/SeatStore.java",
    "backend/src/main/java/com/thesis/controller/SeatController.java",
    "frontend/src/views/SeatShows.vue",
    "frontend/src/views/SeatMap.vue",
    "frontend/src/layouts/PortalLayout.vue",
    "frontend/src/layouts/AdminLayout.vue",
    "frontend/src/router/index.js",
    "frontend/src/utils/menuRoutes.js",
]


_GATE_STOCK_IO_FILES = [
    "backend/src/main/java/com/thesis/service/StockIoStore.java",
    "backend/src/main/java/com/thesis/controller/StockIoController.java",
    "frontend/src/views/admin/StockMovesAdmin.vue",
    "frontend/src/views/admin/StockLedgerAdmin.vue",
    "frontend/src/layouts/AdminLayout.vue",
    "frontend/src/router/index.js",
    "frontend/src/utils/menuRoutes.js",
]


_GATE_E_SIGN_FILES = [
    "backend/src/main/java/com/thesis/service/ESignStore.java",
    "backend/src/main/java/com/thesis/controller/ESignController.java",
    "frontend/src/views/ESignMine.vue",
    "frontend/src/views/admin/ESignAdmin.vue",
    "frontend/src/layouts/PortalLayout.vue",
    "frontend/src/layouts/AdminLayout.vue",
    "frontend/src/router/index.js",
    "frontend/src/utils/menuRoutes.js",
]


def merge_seat_select_gate(gate: dict, caps: list[str] | None) -> dict:
    """叠加选座购票文件、路由与 flow_api。"""
    caps = set(caps or [])
    if "seat_select" not in caps:
        return gate
    out = dict(gate or {})
    files = list(out.get("files") or [])
    for f in _GATE_SEAT_SELECT_FILES:
        if f not in files:
            files.append(f)
    out["files"] = files
    routes = list(out.get("routes") or [])
    have = {r.get("seg") for r in routes if isinstance(r, dict)}
    for seg, feat in (
        ("seats/shows", "选座购票"),
        ("seats/map/:id", "选座购票"),
    ):
        if seg not in have:
            routes.append({"seg": seg, "from_feature": feat})
    out["routes"] = routes
    flow = dict(out.get("flow_api") or {})
    flow["seat_select"] = {"file": "SeatController.java", "need": ["/api/seats"]}
    out["flow_api"] = flow
    return out


def merge_stock_io_gate(gate: dict, caps: list[str] | None) -> dict:
    """叠加浅进销存文件、路由与 flow_api。"""
    caps = set(caps or [])
    if "stock_io" not in caps:
        return gate
    out = dict(gate or {})
    files = list(out.get("files") or [])
    for f in _GATE_STOCK_IO_FILES:
        if f not in files:
            files.append(f)
    out["files"] = files
    routes = list(out.get("routes") or [])
    have = {r.get("seg") for r in routes if isinstance(r, dict)}
    for seg, feat in (
        ("admin/stock/moves", "入出库与库存流水"),
        ("admin/stock/ledger", "入出库与库存流水"),
    ):
        if seg not in have:
            routes.append({"seg": seg, "from_feature": feat})
    out["routes"] = routes
    flow = dict(out.get("flow_api") or {})
    flow["stock_io"] = {"file": "StockIoController.java", "need": ["/api/stock-io"]}
    out["flow_api"] = flow
    inv = dict(out.get("admin_invariants") or {})
    super_menus = list(inv.get("super_menus") or [])
    for key in ("stock_moves", "stock_ledger"):
        if key not in super_menus:
            if "content" in super_menus:
                super_menus.insert(super_menus.index("content"), key)
            else:
                super_menus.append(key)
    inv["super_menus"] = super_menus
    out["admin_invariants"] = inv
    return out


def merge_timebank_gate(gate: dict, caps: list[str] | None) -> dict:
    """叠加时间银行文件、路由与 flow_api。"""
    caps = set(caps or [])
    if "timebank" not in caps:
        return gate
    out = dict(gate or {})
    files = list(out.get("files") or [])
    for f in _GATE_TIMEBANK_FILES:
        if f not in files:
            files.append(f)
    out["files"] = files
    routes = list(out.get("routes") or [])
    have = {r.get("seg") for r in routes if isinstance(r, dict)}
    for seg, feat in (
        ("tb/account", "时长账户与流水"),
        ("tb/ledger", "时长账户与流水"),
        ("admin/tb/accounts", "时长账户与流水"),
        ("admin/tb/ledger", "时长账户与流水"),
    ):
        if seg not in have:
            routes.append({"seg": seg, "from_feature": feat})
    out["routes"] = routes
    flow = dict(out.get("flow_api") or {})
    flow["timebank"] = {"file": "TimebankController.java", "need": ["/api/timebank"]}
    out["flow_api"] = flow
    inv = dict(out.get("admin_invariants") or {})
    super_menus = list(inv.get("super_menus") or [])
    for key in ("tb_accounts", "tb_ledger_admin"):
        if key not in super_menus:
            if "content" in super_menus:
                super_menus.insert(super_menus.index("content"), key)
            else:
                super_menus.append(key)
    inv["super_menus"] = super_menus
    out["admin_invariants"] = inv
    return out


def merge_e_sign_gate(gate: dict, caps: list[str] | None) -> dict:
    """叠加本地签章文件、路由与 flow_api。"""
    caps = set(caps or [])
    if "e_sign" not in caps:
        return gate
    out = dict(gate or {})
    files = list(out.get("files") or [])
    for f in _GATE_E_SIGN_FILES:
        if f not in files:
            files.append(f)
    out["files"] = files
    routes = list(out.get("routes") or [])
    have = {r.get("seg") for r in routes if isinstance(r, dict)}
    for seg, feat in (
        ("e-sign", "本地签章"),
        ("admin/e-sign", "本地签章"),
    ):
        if seg not in have:
            routes.append({"seg": seg, "from_feature": feat})
    out["routes"] = routes
    flow = dict(out.get("flow_api") or {})
    flow["e_sign"] = {"file": "ESignController.java", "need": ["/api/e-sign"]}
    out["flow_api"] = flow
    inv = dict(out.get("admin_invariants") or {})
    super_menus = list(inv.get("super_menus") or [])
    if "e_sign_admin" not in super_menus:
        if "content" in super_menus:
            super_menus.insert(super_menus.index("content"), "e_sign_admin")
        else:
            super_menus.append("e_sign_admin")
    inv["super_menus"] = super_menus
    out["admin_invariants"] = inv
    return out


def merge_doclib_gate(gate: dict, caps: list[str] | None) -> dict:
    """叠加文库下载文件、路由与 flow_api。"""
    caps = set(caps or [])
    if "doclib" not in caps:
        return gate
    out = dict(gate or {})
    files = list(out.get("files") or [])
    for f in _GATE_DOCLIB_FILES:
        if f not in files:
            files.append(f)
    out["files"] = files
    routes = list(out.get("routes") or [])
    have = {r.get("seg") for r in routes if isinstance(r, dict)}
    for seg, feat in (
        ("doc/browse", "资料下载与台账"),
        ("doc/mine", "资料下载与台账"),
        ("admin/doc/files", "资料下载与台账"),
        ("admin/doc/logs", "资料下载与台账"),
    ):
        if seg not in have:
            routes.append({"seg": seg, "from_feature": feat})
    out["routes"] = routes
    flow = dict(out.get("flow_api") or {})
    flow["doclib"] = {"file": "DoclibController.java", "need": ["/api/doclib"]}
    out["flow_api"] = flow
    inv = dict(out.get("admin_invariants") or {})
    super_menus = list(inv.get("super_menus") or [])
    for key in ("doc_files", "doc_logs"):
        if key not in super_menus:
            if "content" in super_menus:
                super_menus.insert(super_menus.index("content"), key)
            else:
                super_menus.append(key)
    inv["super_menus"] = super_menus
    out["admin_invariants"] = inv
    return out


_GATE_VOTE_FILES = [
    "backend/src/main/java/com/thesis/service/VoteStore.java",
    "backend/src/main/java/com/thesis/controller/VoteController.java",
    "frontend/src/views/VoteCampaigns.vue",
    "frontend/src/views/VoteCast.vue",
    "frontend/src/views/VoteMine.vue",
    "frontend/src/views/admin/VoteCandidatesAdmin.vue",
    "frontend/src/views/admin/VoteResultsAdmin.vue",
    "frontend/src/layouts/PortalLayout.vue",
    "frontend/src/layouts/AdminLayout.vue",
    "frontend/src/router/index.js",
    "frontend/src/utils/menuRoutes.js",
]


def merge_vote_gate(gate: dict, caps: list[str] | None) -> dict:
    """叠加投票评选文件、路由与 flow_api。"""
    caps = set(caps or [])
    if "vote" not in caps:
        return gate
    out = dict(gate or {})
    files = list(out.get("files") or [])
    for f in _GATE_VOTE_FILES:
        if f not in files:
            files.append(f)
    out["files"] = files
    routes = list(out.get("routes") or [])
    have = {r.get("seg") for r in routes if isinstance(r, dict)}
    for seg, feat in (
        ("vote/campaigns", "投票与计票"),
        ("vote/cast/:id", "投票与计票"),
        ("vote/mine", "投票与计票"),
        ("admin/vote/candidates", "投票与计票"),
        ("admin/vote/results", "投票与计票"),
    ):
        if seg not in have:
            routes.append({"seg": seg, "from_feature": feat})
    out["routes"] = routes
    flow = dict(out.get("flow_api") or {})
    flow["vote"] = {"file": "VoteController.java", "need": ["/api/vote"]}
    out["flow_api"] = flow
    inv = dict(out.get("admin_invariants") or {})
    super_menus = list(inv.get("super_menus") or [])
    for key in ("vote_candidates", "vote_results"):
        if key not in super_menus:
            if "content" in super_menus:
                super_menus.insert(super_menus.index("content"), key)
            else:
                super_menus.append(key)
    inv["super_menus"] = super_menus
    out["admin_invariants"] = inv
    return out


def merge_survey_gate(gate: dict, caps: list[str] | None) -> dict:
    """叠加问卷文件、路由与 flow_api。"""
    caps = set(caps or [])
    if "survey" not in caps:
        return gate
    out = dict(gate or {})
    files = list(out.get("files") or [])
    for f in _GATE_SURVEY_FILES:
        if f not in files:
            files.append(f)
    out["files"] = files
    routes = list(out.get("routes") or [])
    have = {r.get("seg") for r in routes if isinstance(r, dict)}
    for seg, feat in (
        ("survey/forms", "问卷填写与回收"),
        ("survey/fill/:id", "问卷填写与回收"),
        ("survey/mine", "问卷填写与回收"),
        ("admin/survey/forms", "问卷填写与回收"),
        ("admin/survey/stats", "问卷填写与回收"),
    ):
        if seg not in have:
            routes.append({"seg": seg, "from_feature": feat})
    out["routes"] = routes
    flow = dict(out.get("flow_api") or {})
    flow["survey"] = {"file": "SurveyController.java", "need": ["/api/survey"]}
    out["flow_api"] = flow
    inv = dict(out.get("admin_invariants") or {})
    super_menus = list(inv.get("super_menus") or [])
    for key in ("survey_forms", "survey_stats"):
        if key not in super_menus:
            if "content" in super_menus:
                super_menus.insert(super_menus.index("content"), key)
            else:
                super_menus.append(key)
    inv["super_menus"] = super_menus
    out["admin_invariants"] = inv
    return out


def merge_exam_gate(gate: dict, caps: list[str] | None) -> dict:
    """叠加在线考试文件、路由与 flow_api。"""
    caps = set(caps or [])
    if "exam" not in caps:
        return gate
    out = dict(gate or {})
    files = list(out.get("files") or [])
    for f in _GATE_EXAM_FILES:
        if f not in files:
            files.append(f)
    out["files"] = files
    routes = list(out.get("routes") or [])
    have = {r.get("seg") for r in routes if isinstance(r, dict)}
    for seg, feat in (
        ("exam/papers", "在线作答与判分"),
        ("exam/attempts", "在线作答与判分"),
        ("exam/take/:id", "在线作答与判分"),
        ("exam/practice", "在线作答与判分"),
        ("exam/rank", "在线作答与判分"),
        ("exam/wrongbook", "在线作答与判分"),
        ("admin/exam/questions", "题库与组卷"),
        ("admin/exam/papers", "题库与组卷"),
    ):
        if seg not in have:
            routes.append({"seg": seg, "from_feature": feat})
    out["routes"] = routes
    flow = dict(out.get("flow_api") or {})
    flow["exam"] = {"file": "ExamController.java", "need": ["/api/exam"]}
    out["flow_api"] = flow
    inv = dict(out.get("admin_invariants") or {})
    super_menus = list(inv.get("super_menus") or [])
    for key in ("exam_questions", "exam_papers"):
        if key not in super_menus:
            if "content" in super_menus:
                super_menus.insert(super_menus.index("content"), key)
            else:
                super_menus.append(key)
    inv["super_menus"] = super_menus
    out["admin_invariants"] = inv
    return out


_GATE_DM_FILES = [
    "backend/src/main/java/com/thesis/service/DmStore.java",
    "backend/src/main/java/com/thesis/controller/DmController.java",
    "frontend/src/views/user/Dm.vue",
    "frontend/src/layouts/PortalLayout.vue",
    "frontend/src/router/index.js",
]


def merge_dm_gate(gate: dict, caps: list[str] | None) -> dict:
    """叠一对一私信文件、路由与 flow_api（仅门户，无管理端）。"""
    caps = set(caps or [])
    if "dm" not in caps:
        return gate
    out = dict(gate or {})
    files = list(out.get("files") or [])
    for f in _GATE_DM_FILES:
        if f not in files:
            files.append(f)
    out["files"] = files
    routes = list(out.get("routes") or [])
    have = {r.get("seg") for r in routes if isinstance(r, dict)}
    if "dm" not in have:
        routes.append({"seg": "dm", "from_feature": "一对一私信"})
    out["routes"] = routes
    flow = dict(out.get("flow_api") or {})
    flow["dm"] = {"file": "DmController.java", "need": ["/api/dm"]}
    out["flow_api"] = flow
    return out


_GATE_FAVORITES_FILES = [
    "backend/src/main/java/com/thesis/capability/FavoriteStore.java",
    "backend/src/main/java/com/thesis/controller/FavoriteController.java",
    "frontend/src/views/user/MyFavorites.vue",
    "frontend/src/views/user/ArchiveBrowse.vue",
    "frontend/src/utils/apiCalls.js",
    "frontend/src/router/index.js",
]


def merge_favorites_gate(
    gate: dict,
    caps: list[str] | None,
    *,
    feature: str = "商品收藏",
) -> dict:
    caps = set(caps or [])
    if "favorites" not in caps:
        return gate
    out = dict(gate or {})
    files = list(out.get("files") or [])
    for f in _GATE_FAVORITES_FILES:
        if f not in files:
            files.append(f)
    out["files"] = files
    routes = list(out.get("routes") or [])
    have = {r.get("seg") for r in routes if isinstance(r, dict)}
    if "favorites" not in have:
        routes.append({"seg": "favorites", "from_feature": feature})
    out["routes"] = routes
    flow = dict(out.get("flow_api") or {})
    flow["favorites"] = {"file": "FavoriteController.java", "need": ["/api/favorites"]}
    out["flow_api"] = flow
    return out


_GATE_ARCHIVE_FAVORITES_FILES = [
    "backend/src/main/java/com/thesis/capability/ArchiveStore.java",
    "backend/src/main/java/com/thesis/capability/FavoriteStore.java",
    "backend/src/main/java/com/thesis/capability/RecommendStore.java",
    "backend/src/main/java/com/thesis/common/AdminAuth.java",
    "backend/src/main/java/com/thesis/controller/ArchiveController.java",
    "backend/src/main/java/com/thesis/controller/CategoryController.java",
    "backend/src/main/java/com/thesis/controller/FavoriteController.java",
    "backend/src/main/java/com/thesis/controller/RecommendController.java",
    "backend/src/main/java/com/thesis/controller/UsersAdminController.java",
    "backend/src/main/java/com/thesis/controller/GateController.java",
    "backend/src/main/java/com/thesis/controller/NoticeController.java",
    "backend/src/main/java/com/thesis/controller/MessageController.java",
    "backend/src/main/java/com/thesis/service/MessageStore.java",
    "backend/src/main/java/com/thesis/controller/AuthController.java",
    "backend/src/main/java/com/thesis/controller/ProfileController.java",
    "backend/src/main/java/com/thesis/controller/TicketDashboardController.java",
    "backend/src/main/java/com/thesis/config/DomainRuntimeBinder.java",
    "frontend/src/views/user/ArchiveBrowse.vue",
    "frontend/src/views/user/MyFavorites.vue",
    "frontend/src/components/RecommendStrip.vue",
    "frontend/src/components/MessageBell.vue",
    "frontend/src/views/admin/ArchiveAdmin.vue",
    "frontend/src/views/admin/CategoriesAdmin.vue",
    "frontend/src/views/admin/TicketDashboard.vue",
    "frontend/src/views/admin/UsersAdmin.vue",
    "frontend/src/views/Notices.vue",
    "frontend/src/views/NoticeDetail.vue",
    "frontend/src/views/admin/NoticesAdmin.vue",
    "frontend/src/views/Profile.vue",
    "frontend/src/views/Login.vue",
    "frontend/src/views/Register.vue",
    "frontend/src/layouts/PortalLayout.vue",
    "frontend/src/layouts/AdminLayout.vue",
    "frontend/src/utils/domainSchema.js",
    "frontend/src/utils/apiCalls.js",
    "frontend/src/appDelivered.js",
    "frontend/src/router/index.js",
    "sql/schema.sql",
]


def gate_archive_only(
    *,
    archive_feature: str,
    users_feature: str,
    category_feature: str = "分类管理",
    dashboard_feature: str = "管理端工作台",
    notice_feature: str = "公告管理",
) -> dict:
    """档案浏览壳（无单据、无收藏）；考试等岛能力再 merge 路由。"""
    routes = [
        {"seg": "archive", "from_feature": archive_feature},
        {"seg": "admin/dashboard", "from_feature": dashboard_feature},
        {"seg": "admin/archive", "from_feature": archive_feature},
        {"seg": "admin/categories", "from_feature": category_feature},
        {"seg": "admin/users", "from_feature": users_feature},
        {"seg": "admin/notices", "from_feature": notice_feature},
        {"seg": "notices", "from_feature": notice_feature},
        {"seg": "notices/:id", "from_feature": notice_feature},
        {"seg": "profile", "from_baseline": "profile"},
        {"seg": "register", "from_baseline": "register"},
    ]
    # 复用收藏壳文件集但去掉收藏页（门禁只认存在的基线文件）
    files = [
        f
        for f in _GATE_ARCHIVE_FAVORITES_FILES
        if "Favorite" not in f and "favorites" not in f.lower()
    ]
    return {
        "routes": routes,
        "files": files,
        "flow_api": {},
        "admin_invariants": {
            "require_super_auth": True,
            "master_kind": "archive",
            "master_menus": ["archive", "category"],
            "super_menus": ["users", "content", "archive", "category"],
        },
    }


def gate_archive_favorites(
    *,
    archive_feature: str,
    favorites_feature: str,
    users_feature: str,
    category_feature: str = "分类管理",
    dashboard_feature: str = "管理端工作台",
    notice_feature: str = "公告管理",
) -> dict:
    """内容流：档案浏览 + 即时收藏（无单据审核）。"""
    routes = [
        {"seg": "archive", "from_feature": archive_feature},
        {"seg": "favorites", "from_feature": favorites_feature},
        {"seg": "admin/dashboard", "from_feature": dashboard_feature},
        {"seg": "admin/archive", "from_feature": archive_feature},
        {"seg": "admin/categories", "from_feature": category_feature},
        {"seg": "admin/users", "from_feature": users_feature},
        {"seg": "admin/notices", "from_feature": notice_feature},
        {"seg": "notices", "from_feature": notice_feature},
        {"seg": "notices/:id", "from_feature": notice_feature},
        {"seg": "profile", "from_baseline": "profile"},
        {"seg": "register", "from_baseline": "register"},
    ]
    return {
        "routes": routes,
        "files": list(_GATE_ARCHIVE_FAVORITES_FILES),
        "flow_api": {
            "favorites": {"file": "FavoriteController.java", "need": ["/api/favorites"]},
        },
        "admin_invariants": {
            "require_super_auth": True,
            "master_kind": "archive",
            "master_menus": ["archive", "category"],
            "super_menus": ["users", "content", "archive", "category"],
        },
    }


_GATE_UX_FILES = [
    "backend/src/main/java/com/thesis/capability/BrowseHistoryStore.java",
    "backend/src/main/java/com/thesis/controller/BrowseHistoryController.java",
    "frontend/src/views/user/BrowseHistory.vue",
    "frontend/src/utils/apiCalls.js",
    "frontend/src/router/index.js",
]


def merge_ux_gate(gate: dict, caps: list[str] | None) -> dict:
    caps = set(caps or [])
    if not caps.intersection({"search_assist", "browse_history", "gallery"}):
        return gate
    out = dict(gate or {})
    files = list(out.get("files") or [])
    if "browse_history" in caps:
        for f in _GATE_UX_FILES:
            if f not in files:
                files.append(f)
    out["files"] = files
    routes = list(out.get("routes") or [])
    have = {r.get("seg") for r in routes if isinstance(r, dict)}
    if "browse_history" in caps and "browse_history" not in have:
        routes.append({"seg": "browse_history", "from_feature": "浏览历史"})
    out["routes"] = routes
    flow = dict(out.get("flow_api") or {})
    if "browse_history" in caps:
        flow["browse_history"] = {
            "file": "BrowseHistoryController.java",
            "need": ["/api/browse-history"],
        }
    if "search_assist" in caps:
        flow["search_assist"] = {
            "file": "ArchiveController.java",
            "need": ["/api/archive/suggest"],
        }
    out["flow_api"] = flow
    return out


_GATE_ARCHIVE_LOG_FILES = [
    "backend/src/main/java/com/thesis/capability/ArchiveLogStore.java",
    "backend/src/main/java/com/thesis/controller/ArchiveLogController.java",
    "backend/src/main/java/com/thesis/controller/AdminArchiveLogController.java",
    "frontend/src/views/admin/ArchiveLogsAdmin.vue",
    "frontend/src/views/user/ArchiveBrowse.vue",
    "frontend/src/router/index.js",
]


def merge_archive_log_gate(gate: dict, caps: list[str] | None) -> dict:
    caps = set(caps or [])
    if "archive_log" not in caps:
        return gate
    out = dict(gate or {})
    files = list(out.get("files") or [])
    for f in _GATE_ARCHIVE_LOG_FILES:
        if f not in files:
            files.append(f)
    out["files"] = files
    routes = list(out.get("routes") or [])
    have = {r.get("seg") for r in routes if isinstance(r, dict)}
    if "admin/archive-logs" not in have:
        routes.append({"seg": "admin/archive-logs", "from_feature": "健康打卡/监测记录"})
    out["routes"] = routes
    flow = dict(out.get("flow_api") or {})
    flow["archive_log"] = {
        "file": "ArchiveLogController.java",
        "need": ["/api/archive-logs", "/api/admin/archive-logs"],
    }
    out["flow_api"] = flow
    return out


_GATE_COUPON_FILES = [
    "backend/src/main/java/com/thesis/capability/CouponStore.java",
    "backend/src/main/java/com/thesis/controller/CouponController.java",
    "frontend/src/views/user/MyCoupons.vue",
    "frontend/src/views/admin/CouponsAdmin.vue",
    "frontend/src/router/index.js",
]

_GATE_ORDER_REVIEW_FILES = [
    "backend/src/main/java/com/thesis/capability/OrderReviewStore.java",
    "backend/src/main/java/com/thesis/controller/OrderReviewController.java",
    "frontend/src/views/user/MyOrderReviews.vue",
    "frontend/src/views/admin/OrderReviewsAdmin.vue",
    "frontend/src/router/index.js",
]

_GATE_SCHEDULE_FILES = [
    "backend/src/main/java/com/thesis/config/DemoScheduleJobs.java",
]


def merge_order_extras_gate(gate: dict, caps: list[str] | None, *, timeout_minutes: int = 0) -> dict:
    caps = set(caps or [])
    if "order_review" not in caps and timeout_minutes <= 0 and "coupon" not in caps:
        return gate
    out = dict(gate or {})
    files = list(out.get("files") or [])
    need_files: list[str] = []
    if "coupon" in caps:
        need_files.extend(_GATE_COUPON_FILES)
        need_files.extend(_GATE_SCHEDULE_FILES)
    if "order_review" in caps:
        need_files.extend(_GATE_ORDER_REVIEW_FILES)
    if timeout_minutes > 0:
        need_files.extend(_GATE_SCHEDULE_FILES)
    for f in need_files:
        if f not in files:
            files.append(f)
    out["files"] = files
    routes = list(out.get("routes") or [])
    have = {r.get("seg") for r in routes if isinstance(r, dict)}
    if "order_review" in caps and "order_reviews" not in have:
        routes.append({"seg": "order_reviews", "from_feature": "订单评价"})
    if "order_review" in caps and "admin/order_reviews" not in have:
        routes.append({"seg": "admin/order_reviews", "from_feature": "订单评价"})
    if "coupon" in caps and "coupons" not in have:
        routes.append({"seg": "coupons", "from_feature": "优惠券"})
    if "coupon" in caps and "admin/coupons" not in have:
        routes.append({"seg": "admin/coupons", "from_feature": "优惠券"})
    out["routes"] = routes
    flow = dict(out.get("flow_api") or {})
    if "order_review" in caps:
        flow["order_review"] = {
            "file": "OrderReviewController.java",
            "need": ["/api/order-reviews"],
        }
    if "coupon" in caps:
        flow["coupon"] = {"file": "CouponController.java", "need": ["/api/coupons"]}
    out["flow_api"] = flow
    return out


def merge_loyalty_gate(gate: dict, caps: list[str] | None) -> dict:
    """订单壳 gate 上叠加忠诚度文件与 flow_api。"""
    caps = set(caps or [])
    if not caps.intersection({"wallet", "points", "spend_discount", "member_tier", "coupon"}):
        return gate
    out = dict(gate or {})
    files = list(out.get("files") or [])
    for f in _GATE_LOYALTY_FILES:
        if f not in files:
            files.append(f)
    out["files"] = files
    flow = dict(out.get("flow_api") or {})
    flow["loyalty"] = {"file": "LoyaltyController.java", "need": ["/api/loyalty"]}
    out["flow_api"] = flow
    return out


def gate_order_shell(
    *,
    archive_feature: str,
    cart_feature: str,
    orders_feature: str,
    users_feature: str = "用户管理",
    dashboard_feature: str = "管理端工作台",
) -> dict:
    return {
        "routes": [
            {"seg": "archive", "from_feature": archive_feature},
            {"seg": "cart", "from_feature": cart_feature},
            {"seg": "orders", "from_feature": orders_feature},
            {"seg": "admin/dashboard", "from_feature": dashboard_feature},
            {"seg": "admin/archive", "from_feature": archive_feature},
            {"seg": "admin/orders", "from_feature": orders_feature},
            {"seg": "admin/users", "from_feature": users_feature},
            {"seg": "profile", "from_baseline": "profile"},
            {"seg": "register", "from_baseline": "register"},
        ],
        "files": list(_GATE_ORDER_FILES),
        "flow_api": {
            "place": {"file": "OrderController.java", "need": ["/api/orders", "placeOrder"]},
            "cart": {"file": "OrderController.java", "need": ["/api/cart"]},
        },
        "admin_invariants": {
            "require_super_auth": True,
            "master_kind": "archive",
            "master_menus": ["archive", "category"],
            "super_menus": ["users", "content", "archive", "category"],
        },
    }


def gate_slot_shell(
    *,
    archive_feature: str,
    reserve_feature: str,
    users_feature: str = "用户管理",
    dashboard_feature: str = "管理端工作台",
    with_orders: bool = False,
) -> dict:
    routes = [
        {"seg": "archive", "from_feature": archive_feature},
        {"seg": "slots", "from_feature": reserve_feature},
        {"seg": "reservations", "from_feature": reserve_feature},
        {"seg": "admin/dashboard", "from_feature": dashboard_feature},
        {"seg": "admin/archive", "from_feature": archive_feature},
        {"seg": "admin/reservations", "from_feature": reserve_feature},
        {"seg": "admin/users", "from_feature": users_feature},
        {"seg": "profile", "from_baseline": "profile"},
        {"seg": "register", "from_baseline": "register"},
    ]
    files = list(_GATE_SLOT_FILES)
    if with_orders:
        routes.insert(3, {"seg": "orders", "from_feature": reserve_feature})
        routes.insert(-2, {"seg": "admin/orders", "from_feature": reserve_feature})
        files.extend([
            "backend/src/main/java/com/thesis/capability/OrderStore.java",
            "backend/src/main/java/com/thesis/controller/OrderController.java",
            "frontend/src/views/user/MyOrders.vue",
            "frontend/src/views/admin/OrdersAdmin.vue",
        ])
    return {
        "routes": routes,
        "files": files,
        "flow_api": {
            "reserve": {"file": "SlotController.java", "need": ["/reserve", "reserve"]},
            "cancel": {"file": "SlotController.java", "need": ["/cancel", "cancel"]},
        },
        "admin_invariants": {
            "require_super_auth": True,
            "master_kind": "archive",
            "master_menus": ["archive", "category"],
            "super_menus": ["users", "content", "archive", "category"],
        },
    }

