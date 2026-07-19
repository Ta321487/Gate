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
    "frontend/src/factoryDelivered.js",
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
    "frontend/src/views/admin/OverdueAdmin.vue",
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
    "frontend/src/factoryDelivered.js",
    "frontend/src/router/index.js",
    "sql/schema.sql",
]


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
    if with_deadline:
        routes.insert(
            7,
            {"seg": "admin/overdue", "from_feature": overdue_feature},
        )
    flow_api = {
        "apply": {"file": "TicketController.java", "need": ["/apply", "TicketStore.apply"]},
        "approve": {"file": "TicketController.java", "need": ["approve"]},
        "return": {"file": "TicketController.java", "need": ["/return", "complete"]},
    }
    if with_deadline:
        flow_api["overdue"] = {"file": "TicketController.java", "need": ["/overdue", "markOverdue"]}
        flow_api["remind"] = {"file": "TicketController.java", "need": ["/remind", "remind"]}
    return {
        "routes": routes,
        "files": list(_GATE_ARCHIVE_TICKET_FILES),
        "flow_api": flow_api,
        "admin_invariants": {
            "require_super_auth": True,
            "master_kind": "archive",
            "master_menus": ["archive", "category"],
            "super_menus": ["users", "content", "archive", "category"],
        },
    }


# 图书厚包（过渡）：专用 Store / 路由，非 baseline 薄壳
_GATE_LIBRARY_FILES = [
    "backend/src/main/java/com/thesis/service/LibraryStore.java",
    "backend/src/main/java/com/thesis/capability/RecommendStore.java",
    "backend/src/main/java/com/thesis/controller/BookController.java",
    "backend/src/main/java/com/thesis/controller/CategoryController.java",
    "backend/src/main/java/com/thesis/controller/LibraryDashboardController.java",
    "backend/src/main/java/com/thesis/controller/ReaderAdminController.java",
    "backend/src/main/java/com/thesis/controller/BorrowController.java",
    "backend/src/main/java/com/thesis/controller/RecommendController.java",
    "backend/src/main/java/com/thesis/controller/NoticeController.java",
    "backend/src/main/java/com/thesis/service/NoticeStore.java",
    "backend/src/main/java/com/thesis/controller/MessageController.java",
    "backend/src/main/java/com/thesis/service/MessageStore.java",
    "backend/src/main/java/com/thesis/controller/AuthController.java",
    "backend/src/main/java/com/thesis/controller/ProfileController.java",
    "frontend/src/views/reader/Books.vue",
    "frontend/src/views/reader/BookDetail.vue",
    "frontend/src/views/reader/MyBorrows.vue",
    "frontend/src/views/Notices.vue",
    "frontend/src/views/NoticeDetail.vue",
    "frontend/src/views/admin/NoticesAdmin.vue",
    "frontend/src/components/EntityDetailLayout.vue",
    "frontend/src/components/RecommendStrip.vue",
    "frontend/src/components/MessageBell.vue",
    "frontend/src/views/admin/BooksAdmin.vue",
    "frontend/src/views/admin/CategoriesAdmin.vue",
    "frontend/src/views/admin/Dashboard.vue",
    "frontend/src/views/admin/ReadersAdmin.vue",
    "frontend/src/views/admin/BorrowsAdmin.vue",
    "frontend/src/views/admin/BorrowRecordsAdmin.vue",
    "frontend/src/views/admin/OverdueAdmin.vue",
    "frontend/src/views/Profile.vue",
    "frontend/src/views/Login.vue",
    "frontend/src/views/Register.vue",
    "frontend/src/components/AuthShell.vue",
    "frontend/src/utils/authTemplates.js",
    "frontend/src/factoryDelivered.js",
    "frontend/src/router/index.js",
    "sql/schema.sql",
]


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


def gate_library() -> dict:
    """图书领域门禁（bake / gate 共用，禁止在 gate 代码里再写死路径）。"""
    return {
        "routes": [
            {"seg": "books", "from_feature": "图书检索与详情"},
            {"seg": "admin/categories", "from_feature": "分类管理"},
            {"seg": "admin/dashboard", "from_feature": "管理端工作台"},
            {"seg": "admin/readers", "from_feature": "读者管理"},
            {"seg": "my-borrows", "from_feature": "借阅申请 → 审核"},
            {"seg": "admin/borrows", "from_feature": "借阅申请 → 审核"},
            {"seg": "admin/borrow-records", "from_feature": "借阅记录"},
            {"seg": "admin/overdue", "from_feature": "逾期提醒与罚款"},
            {"seg": "notices", "from_feature": "公告管理"},
            {"seg": "notices/:id", "from_feature": "公告管理"},
            {"seg": "profile", "from_baseline": "profile"},
            {"seg": "register", "from_baseline": "register"},
        ],
        "files": list(_GATE_LIBRARY_FILES),
        "flow_api": {
            "apply": {"file": "BorrowController.java", "need": ["/apply", "applyBorrow"]},
            "approve": {"file": "BorrowController.java", "need": ["approve"]},
            "return": {"file": "BorrowController.java", "need": ["/return"]},
            "overdue": {"file": "BorrowController.java", "need": ["/overdue", "markOverdue"]},
            "remind": {"file": "BorrowController.java", "need": ["/remind", "remind"]},
        },
    }
