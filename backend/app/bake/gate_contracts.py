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

