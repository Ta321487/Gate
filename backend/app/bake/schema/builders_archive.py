"""档案 / followup / 报名申请类域 builder。"""

from __future__ import annotations

from typing import Any

from app.bake.domains import DOMAIN_CAPABILITIES
from app.bake.schema.shells import (
    _copy_scan_text,
    _with_portal_banners,
    archive_ticket_schema,
    product_name_from_title,
)

def _library_schema(title: str) -> dict[str, Any]:
    return {
        "version": 1,
        "title": title,
        "capabilities": list(DOMAIN_CAPABILITIES["DOM-LIBRARY"]),
        "roles": {
            "user": {"id": "reader", "label": "读者"},
            "admin": {"id": "admin", "label": "馆长（总管）"},
            "subadmin": {"id": "subadmin", "label": "馆员"},
        },
        "entities": {
            "archive": {
                "key": "book",
                "label": "图书",
                "labelPlural": "图书",
                "fields": [
                    {"key": "title", "label": "书名", "type": "string"},
                    {"key": "author", "label": "作者", "type": "string"},
                    {"key": "isbn", "label": "ISBN", "type": "string"},
                    {"key": "publisher", "label": "出版社", "type": "string"},
                    {"key": "callNo", "label": "索书号", "type": "string"},
                    {"key": "category", "label": "分类", "type": "select"},
                    {"key": "stock", "label": "库存", "type": "number"},
                ],
                "softDelete": True,
            },
            "ticket": {
                "key": "borrow",
                "label": "借阅单",
                "labelPlural": "借阅",
                "verbs": {
                    "apply": "申请借阅",
                    "approve": "通过",
                    "reject": "驳回",
                    "return": "归还",
                    "remind": "催还",
                },
                "states": {
                    "pending": "待审核",
                    "approved": "借阅中",
                    "rejected": "已驳回",
                    "returned": "已归还",
                    "overdue": "已逾期",
                },
                "pickLoanPeriod": True,
                "allowQty": True,
                "dueLabel": "应还日",
                "fineLabel": "罚款",
                "finePaidLabel": "罚款已缴",
            },
        },
        "menus": {
            "admin": [
                {"key": "dashboard", "label": "工作台"},
                {"key": "archive", "label": "图书管理", "superOnly": True},
                {"key": "category", "label": "分类管理", "superOnly": True},
                {"key": "users", "label": "读者管理", "superOnly": True},
                {"key": "ticket_pending", "label": "借阅审核"},
                {"key": "ticket_records", "label": "借阅记录"},
                {"key": "deadline", "label": "逾期罚款"},
                {"key": "content", "label": "公告管理", "superOnly": True},
            ],
            "user": [
                {"key": "archive", "label": "图书检索"},
                {"key": "my_tickets", "label": "我的借阅"},
                {"key": "content", "label": "公告"},
                {"key": "profile", "label": "个人资料"},
            ],
        },
        "labels": {
            "appName": product_name_from_title(title),
            "authEyebrow": "欢迎使用",
            "authLead": "验证码登录，开放注册；读者可检索图书并申请借阅。",
            "authPoints": ["验证码登录", "开放注册", "借阅申请与归还"],
            "registerRoleHint": "注册后以读者身份使用系统",
            "noticePageTitle": "馆内公告",
            "noticePageLead": "开放时间、借阅须知与临时通知，点击条目阅读全文。",
            "messagesPageLead": "审核结果、还书提醒与系统通知。",
            "recommendSectionTitle": "猜你喜欢",
            "recommendLatestHint": "最新上架",
        },
        "seeds": {
            "noticeTitle": "开放借阅通知",
            "noticeBody": "系统已就绪，欢迎检索图书并提交借阅申请。",
        },
        "portalBanners": [
            {"title": "开架阅览", "lead": "按书名、作者或 ISBN 检索，在线提交借阅。"},
            {"title": "借阅须知", "lead": "每人同时最多借阅 5 本，请按时归还。"},
            {"title": "开放时间", "lead": "工作日开放；临时调整见馆内公告。"},
            {"title": "我的书架", "lead": "登录后查看借阅进度与到期提醒。"},
            {"title": "新书上架", "lead": "分类浏览最新到馆图书。"},
        ],
    }

def _equip_schema(title: str) -> dict[str, Any]:
    return _with_portal_banners(
        archive_ticket_schema(
            title,
            domain="DOM-EQUIP",
            user_role_id="user",
            user_label="借用人",
            admin_label="实验室主管（总管）",
            subadmin_label="器材管理员",
            archive_key="equip",
            archive_label="设备",
            archive_plural="设备",
            archive_fields=[
                {"key": "title", "label": "设备名称", "type": "string"},
                {"key": "author", "label": "品牌/型号", "type": "string"},
                {"key": "isbn", "label": "资产编号", "type": "string"},
                {"key": "category", "label": "分类", "type": "select"},
                {"key": "stock", "label": "可借数量", "type": "number"},
                {"key": "requiresTraining", "label": "需培训", "type": "boolean"},
                {"key": "ownerName", "label": "责任人", "type": "string"},
            ],
            ticket_key="loan",
            ticket_label="借用单",
            ticket_plural="借用",
            verbs={
                "apply": "申请借用",
                "approve": "通过",
                "reject": "驳回",
                "return": "归还",
                "remind": "催还",
            },
            states={
                "pending": "待审核",
                "approved": "借用中",
                "rejected": "已驳回",
                "returned": "已归还",
                "overdue": "已逾期",
            },
            archive_menu_admin="设备管理",
            archive_menu_user="设备检索",
            users_menu="用户管理",
            auth_eyebrow="实验室设备",
            auth_lead="验证码登录；检索设备并申请借用，管理员审核后领用。",
            auth_points=["验证码登录", "设备检索", "借用申请与归还"],
            register_hint="注册后可申请借用实验室设备",
            notice_title="设备借用须知",
            notice_body="请按需申请、按时归还；逾期将登记催还。",
            notice_page_title="实验室公告",
            notice_page_lead="借用须知、开放时段与临时通知，点击条目阅读全文。",
            my_tickets_label="我的借用",
            pending_label="借用审核",
            records_label="借用记录",
            deadline_label="逾期催还",
            soft_delete=True,
        ),
        [
            {"title": "实验室器材", "lead": "检索设备、查看库存，在线提交借用申请。"},
            {"title": "借用须知", "lead": "按需申请、按时归还；逾期将登记催还。"},
            {"title": "领用时段", "lead": "工作日办理领用与归还，详见实验室公告。"},
            {"title": "我的借用", "lead": "登录后查看审核进度与归还期限。"},
            {"title": "器材公告", "lead": "检修停用与临时安排见公告栏。"},
        ],
    )

def _asset_schema(title: str, proposal_text: str = "") -> dict[str, Any]:
    """固定资产 / 耗材申领：高校物资 vs 企业仓储（同 _food_schema 分支）。"""
    from app.bake.scene_scan import scene_asset

    t = _copy_scan_text(title, proposal_text)
    campus = scene_asset(t) == "campus"
    if campus:
        brow, lead, notice, hint = (
            "高校物资",
            "验证码登录；浏览校内物资台账并提交申领，库管审核后出库。",
            "物资公告",
            "注册后可按院系申领办公物资与耗材",
        )
        banners = [
            {"title": "物资台账", "lead": "校内固定资产与耗材分类浏览，查看可领库存。"},
            {"title": "在线申领", "lead": "提交申领单，库管审核通过后办理出库。"},
            {"title": "物资公告", "lead": "盘点安排与领用须知见公告栏。"},
            {"title": "我的申领", "lead": "登录后跟踪审核与出库进度。"},
            {"title": "分类检索", "lead": "按品类快速定位可领物资。"},
        ]
    else:
        brow, lead, notice, hint = (
            "物资领用",
            "验证码登录；浏览物资台账并提交申领，库管审核后出库。",
            "仓储公告",
            "注册后可按部门申领办公物资与耗材",
        )
        banners = [
            {"title": "物资台账", "lead": "固定资产与耗材分类浏览，查看可领库存。"},
            {"title": "在线申领", "lead": "提交申领单，库管审核通过后办理出库。"},
            {"title": "仓储公告", "lead": "盘点安排与领用须知见公告栏。"},
            {"title": "我的申领", "lead": "登录后跟踪审核与出库进度。"},
            {"title": "分类检索", "lead": "按品类快速定位可领物资。"},
        ]
    return _with_portal_banners(
        archive_ticket_schema(
            title,
            domain="DOM-ASSET",
            user_role_id="user",
            user_label="申领人",
            admin_label="仓管主管（总管）",
            subadmin_label="库管员",
            archive_key="asset",
            archive_label="物资",
            archive_plural="物资",
            archive_fields=[
                {"key": "title", "label": "物资名称", "type": "string"},
                {"key": "author", "label": "规格/型号", "type": "string"},
                {"key": "isbn", "label": "资产编号", "type": "string"},
                {"key": "category", "label": "分类", "type": "select"},
                {"key": "stock", "label": "可领数量", "type": "number"},
            ],
            ticket_key="requisition",
            ticket_label="申领单",
            ticket_plural="申领",
            verbs={
                "apply": "提交申领",
                "approve": "通过出库",
                "reject": "驳回",
                "return": "退库",
                "remind": "催办",
            },
            states={
                "pending": "待审核",
                "approved": "已出库",
                "rejected": "已驳回",
                "returned": "已退库",
                "overdue": "已失效",
            },
            archive_menu_admin="物资台账",
            archive_menu_user="物资目录",
            users_menu="用户管理",
            auth_eyebrow=brow,
            auth_lead=lead,
            auth_points=["验证码登录", "物资目录", "申领审核与出库"],
            register_hint=hint,
            notice_title="领用须知",
            notice_body="请按需申领、如实填写用途；固定资产领用后请妥善保管，耗材出库不退。",
            notice_page_title=notice,
            notice_page_lead="领用须知、盘点安排与临时通知，点击条目阅读全文。",
            my_tickets_label="我的申领",
            pending_label="申领审核",
            records_label="申领记录",
            with_deadline=False,
            soft_delete=True,
            allow_qty=True,
            require_remark=True,
            remark_label="用途说明",
        ),
        banners,
    )

def _crm_schema(title: str) -> dict[str, Any]:
    """轻量 CRM：客户档案 + 跟进单据（非公海/外呼引擎）。"""
    from app.bake.schema.followup_presets import followup_domain_schema

    return followup_domain_schema(title, "DOM-CRM")

def _event_schema(title: str, proposal_text: str = "") -> dict[str, Any]:
    """事件/公卫：校园晨午检 vs 社区网格（同 _food_schema 分支）。"""
    from app.bake.schema.followup_presets import followup_domain_schema
    from app.bake.scene_scan import scene_event

    t = _copy_scan_text(title, proposal_text)
    scene = scene_event(t)
    if scene == "campus":
        return followup_domain_schema(
            title,
            "DOM-EVENT",
            overrides={
                "user_label": "师生",
                "admin_label": "学工主管（总管）",
                "subadmin_label": "班主任",
                "auth_eyebrow": "校园晨午检",
                "auth_lead": "验证码登录；维护学生档案并打卡/上报，异常由学工处置。",
                "auth_points": ["验证码登录", "学生档案", "晨午检打卡", "异常上报"],
                "notice_page_title": "学工公告",
                "banners": [
                    {"title": "学生档案", "lead": "按班级浏览对象档案，维护摘要与状态。"},
                    {"title": "晨午检打卡", "lead": "每日打卡或随访，查看今日未打卡。"},
                    {"title": "异常上报", "lead": "因病缺课等线索提交上报，办结可追溯。"},
                    {"title": "学工公告", "lead": "晨午检规范与通知见公告栏。"},
                    {"title": "我的上报", "lead": "登录后查看上报进度与记录。"},
                    {"title": "分类管理", "lead": "按分类筛选重点对象。"},
                ],
            },
        )
    if scene == "community":
        return followup_domain_schema(
            title,
            "DOM-EVENT",
            overrides={
                "user_label": "居民",
                "admin_label": "主管（总管）",
                "subadmin_label": "网格员",
                "auth_eyebrow": "社区公卫",
                "auth_lead": "验证码登录；维护对象档案并打卡/上报，异常由网格处置。",
                "auth_points": ["验证码登录", "对象档案", "健康打卡", "上报记录"],
                "notice_page_title": "社区公告",
                "banners": [
                    {"title": "对象档案", "lead": "按分类浏览重点对象，维护摘要与状态。"},
                    {"title": "健康打卡", "lead": "每日打卡或随访，查看今日未打卡。"},
                    {"title": "事件上报", "lead": "异常线索提交上报，办结后可追溯。"},
                    {"title": "社区公告", "lead": "排查规范与通知见公告栏。"},
                    {"title": "我的上报", "lead": "登录后查看上报进度与记录。"},
                    {"title": "分类管理", "lead": "按分类筛选重点对象。"},
                ],
            },
        )
    return followup_domain_schema(title, "DOM-EVENT")


def _attend_schema(title: str, proposal_text: str = "") -> dict[str, Any]:
    """考勤请假：题名/开题含学生/校园走学工口径（同 _food_schema 食堂分支）。"""
    from app.bake.schema.followup_presets import _std_archive_fields, followup_domain_schema
    from app.bake.scene_scan import scene_attend

    t = _copy_scan_text(title, proposal_text)
    campus = scene_attend(t) == "campus"
    if not campus:
        return followup_domain_schema(title, "DOM-ATTEND")
    return followup_domain_schema(
        title,
        "DOM-ATTEND",
        overrides={
            "user_label": "学生",
            "admin_label": "学工主管（总管）",
            "subadmin_label": "辅导员",
            "archive_label": "学生",
            "archive_plural": "学生",
            "archive_fields": _std_archive_fields(
                "姓名",
                "院系/班级",
                "学号备注",
                "在校状态",
                ["在校", "请假中", "休学", "离校"],
                "学生类型",
                "可请假",
            ),
            "archive_menu_admin": "学生档案",
            "archive_menu_user": "学生名册",
            "auth_eyebrow": "学生请假",
            "auth_lead": "验证码登录；维护学生档案并提交请假，审批通过后按时销假。",
            "auth_points": ["验证码登录", "学生档案", "请假与销假"],
            "notice_page_title": "学工公告",
            "notice_page_lead": "请假须知与学工通知，点击条目阅读全文。",
            "banners": [
                {"title": "学生名册", "lead": "按学生类型浏览，维护院系与学号。"},
                {"title": "在线请假", "lead": "提交请假单，学工审批后生效。"},
                {"title": "学工公告", "lead": "请假节点与销假须知见公告栏。"},
                {"title": "我的请假", "lead": "登录后跟踪审批与销假。"},
                {"title": "分类检索", "lead": "按学生类型快速定位。"},
            ],
        },
    )

def _fund_schema(title: str) -> dict[str, Any]:
    from app.bake.schema.followup_presets import followup_domain_schema

    return followup_domain_schema(title, "DOM-FUND")

def _labsafe_schema(title: str) -> dict[str, Any]:
    from app.bake.schema.followup_presets import followup_domain_schema

    return followup_domain_schema(title, "DOM-LABSAFE")

def _recruit_schema(title: str, proposal_text: str = "") -> dict[str, Any]:
    """招聘：校园校招 vs 企业 HR（同 _food_schema 分支）。"""
    from app.bake.schema.followup_presets import followup_domain_schema
    from app.bake.scene_scan import scene_recruit

    t = _copy_scan_text(title, proposal_text)
    scene = scene_recruit(t)
    if scene == "campus":
        return followup_domain_schema(
            title,
            "DOM-RECRUIT",
            overrides={
                "admin_label": "就业办主管（总管）",
                "subadmin_label": "就业专员",
                "auth_eyebrow": "校园招聘",
                "auth_lead": "验证码登录；浏览校招岗位并投递简历，就业办初筛后反馈结果。",
                "auth_points": ["验证码登录", "职位浏览", "投递与初筛"],
                "notice_page_title": "就业公告",
                "banners": [
                    {"title": "职位浏览", "lead": "按类型查看校招岗位与任职要求。"},
                    {"title": "投递简历", "lead": "选择岗位提交投递单，等待就业办初筛。"},
                    {"title": "就业公告", "lead": "校招节点与材料要求见公告。"},
                    {"title": "我的投递", "lead": "跟踪初筛进度与结果。"},
                    {"title": "分类检索", "lead": "技术/职能/实习快速筛选。"},
                ],
            },
        )
    if scene == "enterprise":
        return followup_domain_schema(
            title,
            "DOM-RECRUIT",
            overrides={
                "admin_label": "招聘主管（总管）",
                "subadmin_label": "HR专员",
                "auth_eyebrow": "企业招聘",
                "auth_lead": "验证码登录；浏览岗位并投递简历，HR 初筛后反馈结果。",
                "notice_page_title": "招聘公告",
                "banners": [
                    {"title": "职位浏览", "lead": "按类型查看在招岗位与任职要求。"},
                    {"title": "投递简历", "lead": "选择岗位提交投递单，等待 HR 初筛。"},
                    {"title": "招聘公告", "lead": "招聘节点与材料要求见公告。"},
                    {"title": "我的投递", "lead": "跟踪初筛进度与结果。"},
                    {"title": "分类检索", "lead": "技术/职能/实习快速筛选。"},
                ],
            },
        )
    return followup_domain_schema(title, "DOM-RECRUIT")

def _grade_schema(title: str) -> dict[str, Any]:
    from app.bake.schema.followup_presets import followup_domain_schema

    return followup_domain_schema(title, "DOM-GRADE")

def _intern_schema(title: str) -> dict[str, Any]:
    from app.bake.schema.followup_presets import followup_domain_schema

    return followup_domain_schema(title, "DOM-INTERN")

def _parcel_schema(title: str, proposal_text: str = "") -> dict[str, Any]:
    """驿站：校园 vs 社区代收点（同 _food_schema 分支）。"""
    from app.bake.schema.followup_presets import followup_domain_schema
    from app.bake.scene_scan import scene_parcel

    t = _copy_scan_text(title, proposal_text)
    if scene_parcel(t) == "community":
        return followup_domain_schema(
            title,
            "DOM-PARCEL",
            overrides={
                "admin_label": "站点主管（总管）",
                "subadmin_label": "店员",
                "auth_eyebrow": "快递代收",
                "auth_lead": "验证码登录；查看待取包裹，提交取件申请并由店员核销。",
                "notice_page_title": "站点公告",
                "banners": [
                    {"title": "包裹查询", "lead": "按运单与取件码查看待取包裹。"},
                    {"title": "申请取件", "lead": "提交取件单，到站核销出库。"},
                    {"title": "站点公告", "lead": "营业时间与逾期催取见公告。"},
                    {"title": "我的取件", "lead": "跟踪核销进度。"},
                    {"title": "件型筛选", "lead": "普通/生鲜/大件快速定位。"},
                ],
            },
        )
    return followup_domain_schema(title, "DOM-PARCEL")

def _activity_schema(title: str) -> dict[str, Any]:
    return _with_portal_banners(
        archive_ticket_schema(
            title,
            domain="DOM-ACTIVITY",
            user_role_id="user",
            user_label="报名者",
            admin_label="活动主管（总管）",
            subadmin_label="活动助理",
            archive_key="activity",
            archive_label="活动",
            archive_plural="活动",
            archive_fields=[
                {"key": "title", "label": "活动名称", "type": "string"},
                {"key": "author", "label": "主办方", "type": "string"},
                {"key": "isbn", "label": "地点", "type": "string"},
                {"key": "category", "label": "分类", "type": "select"},
                {"key": "stock", "label": "剩余名额", "type": "number"},
                {"key": "checkinCode", "label": "签到码", "type": "string"},
                {"key": "startAt", "label": "开始时间", "type": "datetime", "timeStepMinutes": 30},
                {"key": "endAt", "label": "结束时间", "type": "datetime", "timeStepMinutes": 30},
                {"key": "applyDeadlineAt", "label": "报名截止", "type": "datetime", "timeStepMinutes": 30},
                {"key": "serviceHours", "label": "志愿时长(小时)", "type": "number"},
            ],
            ticket_key="signup",
            ticket_label="报名单",
            ticket_plural="报名",
            verbs={
                "apply": "报名",
                "approve": "通过",
                "reject": "驳回",
                "return": "取消报名",
                "remind": "提醒",
            },
            states={
                "pending": "待审核",
                "approved": "已报名",
                "rejected": "已驳回",
                "returned": "已取消",
                "overdue": "爽约",
            },
            archive_menu_admin="活动管理",
            archive_menu_user="活动检索",
            users_menu="用户管理",
            auth_eyebrow="活动报名",
            auth_lead="验证码登录；浏览活动并报名；系统检测时段冲突与报名截止；到场口令签到；结束未签到记爽约。",
            auth_points=["验证码登录", "活动检索", "报名、冲突检测、口令签到与爽约"],
            register_hint="注册后可报名校园活动",
            notice_title="报名须知",
            notice_body="请如实填写资料；名额有限；时段冲突或已截止将无法提交；到场请向主办方索取签到码；活动结束后未签到将记为爽约。",
            notice_page_title="活动公告",
            notice_page_lead="报名须知、活动变更与临时通知，点击条目阅读全文。",
            my_tickets_label="我的报名",
            pending_label="报名审核",
            records_label="报名记录",
            with_deadline=False,
            allow_rating=True,
            week_calendar=True,
            week_calendar_label="我的日程",
            allow_checkin=True,
            no_show_after_end=True,
            no_show_penalty_yuan=0,
            approve_ends_flow=True,
        ),
        [
            {"title": "热门活动", "lead": "社团、志愿、讲座分类浏览，在线报名。"},
            {"title": "到场签到", "lead": "到场向主办方索取签到码完成核验；时段重叠将无法重复报名。"},
            {"title": "活动公告", "lead": "变更与须知见公告栏。"},
            {"title": "我的日程", "lead": "登录后查看已报名活动与时段安排。"},
            {"title": "志愿时长", "lead": "志愿类活动可登记服务时长。"},
        ],
    )

def _lost_schema(title: str, proposal_text: str = "") -> dict[str, Any]:
    """失物招领 / 宠物领养：同认领壳，文案跟题名/开题走（同 _meeting_schema）。"""
    from app.bake.scene_scan import scene_lost

    t = _copy_scan_text(title, proposal_text)
    if scene_lost(t) == "adopt":
        noun, remark, admin, sub = "待领养", "领养说明", "领养站主管（总管）", "领养专员"
        user, verb = "申请人", "领养"
        title_lab, author_lab, isbn_lab = "昵称/编号", "登记人", "品种/健康说明"
        kind_opts, found_lab = ["待领养", "已预约看宠"], "登记时间"
        brow, menu_u = "宠物领养", "待领养检索"
        lead = "验证码登录；浏览待领养档案，提交领养申请，管理员审核后办理。"
        notice = "请如实填写养宠条件与联系方式；审核通过后按通知办理交接。"
        notice_t, notice_page, return_v = "领养须知", "领养公告", "撤销申请"
        reg = "注册后可浏览并申请领养"
    else:
        noun, remark, admin, sub = "启事", "认领说明", "招领主管（总管）", "招领管理员"
        user, verb = "用户", "认领"
        title_lab, author_lab, isbn_lab = "物品名称", "拾获/登记人", "地点/特征"
        kind_opts, found_lab = ["招领", "寻物"], "拾获时间"
        brow, menu_u = "失物招领", "失物检索"
        lead = "验证码登录；浏览失物启事，提交认领申请，管理员审核后领取。"
        notice = "认领时请提供有效身份与物品特征；审核通过后到指定地点领取。"
        notice_t, notice_page, return_v = "招领须知", "招领公告", "撤销认领"
        reg = "注册后可浏览启事并申请认领"
    return archive_ticket_schema(
        title,
        domain="DOM-LOST",
        user_role_id="user",
        user_label=user,
        admin_label=admin,
        subadmin_label=sub,
        archive_key="lost_item",
        archive_label=noun,
        archive_plural=noun,
        archive_fields=[
            {"key": "title", "label": title_lab, "type": "string"},
            {"key": "author", "label": author_lab, "type": "string"},
            {"key": "isbn", "label": isbn_lab, "type": "textarea"},
            {"key": "itemKind", "label": "类型", "type": "select", "options": kind_opts},
            {"key": "foundAt", "label": found_lab, "type": "datetime"},
            {"key": "category", "label": "分类", "type": "select"},
            {"key": "stock", "label": f"可{verb}", "type": "number"},
        ],
        ticket_key="claim",
        ticket_label=f"{verb}单",
        ticket_plural=verb,
        verbs={
            "apply": f"申请{verb}",
            "approve": "通过",
            "reject": "驳回",
            "return": return_v,
            "remind": "提醒",
        },
        states={
            "pending": "待审核",
            "approved": f"已{verb}",
            "rejected": "已驳回",
            "returned": "已撤销",
            "overdue": "已失效",
        },
        archive_menu_admin=f"{noun}管理",
        archive_menu_user=menu_u,
        users_menu="用户管理",
        auth_eyebrow=brow,
        auth_lead=lead,
        auth_points=["验证码登录", menu_u, f"{verb}申请与审核"],
        register_hint=reg,
        notice_title=notice_t,
        notice_body=notice,
        notice_page_title=notice_page,
        notice_page_lead=f"{notice_t}与临时通知，点击条目阅读全文。",
        my_tickets_label=f"我的{verb}",
        pending_label=f"{verb}审核",
        records_label=f"{verb}记录",
        with_deadline=False,
        stock_display="available",
        require_attach=True,
        allow_rating=True,
        require_remark=True,
        remark_label=remark,
        approve_ends_flow=True,
    )

def _course_schema(title: str) -> dict[str, Any]:
    return _with_portal_banners(
        archive_ticket_schema(
            title,
            domain="DOM-COURSE",
            user_role_id="student",
            user_label="学生",
            admin_label="教务主管（总管）",
            subadmin_label="选课管理员",
            archive_key="course",
            archive_label="课程",
            archive_plural="课程",
            archive_fields=[
                {"key": "title", "label": "课程名称", "type": "string"},
                {"key": "author", "label": "授课教师", "type": "string"},
                {"key": "isbn", "label": "课号/教室", "type": "string"},
                {"key": "category", "label": "分类", "type": "select"},
                {"key": "stock", "label": "剩余名额", "type": "number"},
                {"key": "mutexCode", "label": "互斥码", "type": "string"},
                {"key": "startAt", "label": "上课开始", "type": "datetime"},
                {"key": "endAt", "label": "上课结束", "type": "datetime"},
                {"key": "applyDeadlineAt", "label": "选课截止", "type": "datetime"},
                {"key": "credit", "label": "学分", "type": "number"},
            ],
            ticket_key="enrollment",
            ticket_label="选课单",
            ticket_plural="选课",
            verbs={
                "apply": "申请选课",
                "approve": "通过",
                "reject": "驳回",
                "return": "退选",
                "remind": "提醒",
            },
            states={
                "pending": "待审核",
                "approved": "已选上",
                "rejected": "已驳回",
                "returned": "已退选",
                "overdue": "已失效",
            },
            archive_menu_admin="课程管理",
            archive_menu_user="课程检索",
            users_menu="学生管理",
            auth_eyebrow="公选选课",
            auth_lead="验证码登录；浏览公选课并申请；系统检测上课时段冲突、互斥组与分类限额。",
            auth_points=["验证码登录", "课程检索", "选课、冲突/互斥与分类限额"],
            register_hint="注册后可以学生身份选课",
            notice_title="选课须知",
            notice_body="请在截止前选课；名额有限；时段冲突、互斥组或分类超额将无法提交。",
            notice_page_title="教务公告",
            notice_page_lead="选课须知、开放时段与临时通知，点击条目阅读全文。",
            my_tickets_label="我的选课",
            pending_label="选课审核",
            records_label="选课记录",
            with_deadline=False,
            check_mutex=True,
            category_limit=1,
            week_calendar=True,
            week_calendar_label="我的课表",
            approve_ends_flow=True,
        ),
        [
            {"title": "本学期公选", "lead": "按分类浏览课程、课时与剩余名额。"},
            {"title": "选课须知", "lead": "时段重叠或名额已满时无法提交，请注意截止时间。"},
            {"title": "教务公告", "lead": "开放时段与变更通知见公告栏。"},
            {"title": "我的课表", "lead": "登录后查看已选课程与上课时间。"},
            {"title": "学分一览", "lead": "选课前可查看课程学分与教师信息。"},
        ],
    )

