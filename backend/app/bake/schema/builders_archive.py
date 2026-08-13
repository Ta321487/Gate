"""档案 / followup / 报名申请类域 builder。"""

from __future__ import annotations

from typing import Any

from app.bake.domains import DOMAIN_CAPABILITIES
from app.bake.schema.shells import (
    _with_portal_banners,
    archive_ticket_schema,
    product_name_from_title,
)

def _library_schema(title: str, proposal_text: str = "") -> dict[str, Any]:
    """图书借阅默认；档案馆卷宗 / 漂流换字段与菜单皮。"""
    from app.bake.scene_scan import library_product_kind

    kind = library_product_kind(title, proposal_text)
    if kind == "archive":
        arch_lab, title_lab, author_lab, isbn_lab = "卷宗", "卷宗题名", "责任者", "档号"
        pub_lab, call_lab, stock_lab = "形成单位", "保管号", "可借份数"
        user_lab, admin_lab, sub_lab = "查阅人", "档案馆长（总管）", "档案员"
        ticket_lab, apply = "借阅单", "申请借阅"
        brow, lead = "档案借阅", "验证码登录；检索卷宗档案并申请借阅，馆员审核后领取归还。"
        points = ["验证码登录", "开放注册", "卷宗借阅与归还"]
        menus_arch_a, menus_arch_u = "卷宗管理", "卷宗检索"
        users_menu, notice = "查阅人管理", "馆内公告"
        banners = [
            {"title": "卷宗检索", "lead": "按题名、责任者或档号检索，在线提交借阅。"},
            {"title": "借阅须知", "lead": "按馆规办理；逾期请及时归还。"},
            {"title": "开放时间", "lead": "工作日开放；临时调整见馆内公告。"},
            {"title": "我的借阅", "lead": "登录后查看借阅进度与到期提醒。"},
            {"title": "分类浏览", "lead": "按档案分类定位卷宗。"},
        ]
        seeds = {
            "noticeTitle": "开放查阅通知",
            "noticeBody": "系统已就绪，欢迎检索卷宗并提交借阅申请。",
        }
    elif kind == "drift":
        arch_lab, title_lab, author_lab, isbn_lab = "图书", "书名", "作者", "漂流编号"
        pub_lab, call_lab, stock_lab = "投放点", "索书号", "可借"
        user_lab, admin_lab, sub_lab = "读者", "漂流站长（总管）", "站务员"
        ticket_lab, apply = "漂流借阅单", "申请借阅"
        brow, lead = "图书漂流", "验证码登录；检索漂流图书并申请借阅，站务审核后领取归还。"
        points = ["验证码登录", "开放注册", "漂流借阅与归还"]
        menus_arch_a, menus_arch_u = "漂流图书", "漂流检索"
        users_menu, notice = "读者管理", "漂流公告"
        banners = [
            {"title": "漂流书架", "lead": "按书名或漂流编号检索，在线申请借阅。"},
            {"title": "漂流须知", "lead": "读完请按时归还，方便下一位同学。"},
            {"title": "投放点", "lead": "各楼栋漂流架位置见公告。"},
            {"title": "我的借阅", "lead": "登录后查看借阅进度。"},
            {"title": "新书投放", "lead": "最新漂流图书上架。"},
        ]
        seeds = {
            "noticeTitle": "漂流开放通知",
            "noticeBody": "欢迎取阅漂流图书并提交借阅登记。",
        }
    else:
        arch_lab, title_lab, author_lab, isbn_lab = "图书", "书名", "作者", "ISBN"
        pub_lab, call_lab, stock_lab = "出版社", "索书号", "库存"
        user_lab, admin_lab, sub_lab = "读者", "馆长（总管）", "馆员"
        ticket_lab, apply = "借阅单", "申请借阅"
        brow, lead = "欢迎使用", "验证码登录，开放注册；读者可检索图书并申请借阅。"
        points = ["验证码登录", "开放注册", "借阅申请与归还"]
        menus_arch_a, menus_arch_u = "图书管理", "图书检索"
        users_menu, notice = "读者管理", "馆内公告"
        banners = [
            {"title": "开架阅览", "lead": "按书名、作者或 ISBN 检索，在线提交借阅。"},
            {"title": "借阅须知", "lead": "每人同时最多借阅 5 本，请按时归还。"},
            {"title": "开放时间", "lead": "工作日开放；临时调整见馆内公告。"},
            {"title": "我的书架", "lead": "登录后查看借阅进度与到期提醒。"},
            {"title": "新书上架", "lead": "分类浏览最新到馆图书。"},
        ]
        seeds = {
            "noticeTitle": "开放借阅通知",
            "noticeBody": "系统已就绪，欢迎检索图书并提交借阅申请。",
        }
    return {
        "version": 1,
        "title": title,
        "capabilities": list(DOMAIN_CAPABILITIES["DOM-LIBRARY"]),
        "roles": {
            "user": {"id": "reader", "label": user_lab},
            "admin": {"id": "admin", "label": admin_lab},
            "subadmin": {"id": "subadmin", "label": sub_lab},
        },
        "entities": {
            "archive": {
                "key": "book",
                "label": arch_lab,
                "labelPlural": arch_lab,
                "fields": [
                    {"key": "title", "label": title_lab, "type": "string"},
                    {"key": "author", "label": author_lab, "type": "string"},
                    {"key": "isbn", "label": isbn_lab, "type": "string"},
                    {"key": "publisher", "label": pub_lab, "type": "string"},
                    {"key": "callNo", "label": call_lab, "type": "string"},
                    {"key": "category", "label": "分类", "type": "select"},
                    {"key": "stock", "label": stock_lab, "type": "number"},
                ],
                "softDelete": True,
            },
            "ticket": {
                "key": "borrow",
                "label": ticket_lab,
                "labelPlural": "借阅",
                "verbs": {
                    "apply": apply,
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
                {"key": "archive", "label": menus_arch_a, "superOnly": True},
                {"key": "category", "label": "分类管理", "superOnly": True},
                {"key": "users", "label": users_menu, "superOnly": True},
                {"key": "ticket_pending", "label": "借阅审核"},
                {"key": "ticket_records", "label": "借阅记录"},
                {"key": "deadline", "label": "逾期罚款"},
                {"key": "content", "label": "公告管理", "superOnly": True},
            ],
            "user": [
                {"key": "archive", "label": menus_arch_u},
                {"key": "my_tickets", "label": "我的借阅"},
                {"key": "content", "label": "公告"},
                {"key": "profile", "label": "个人资料"},
            ],
        },
        "labels": {
            "appName": product_name_from_title(title),
            "authEyebrow": brow,
            "authLead": lead,
            "authPoints": points,
            "registerRoleHint": f"注册后以{user_lab}身份使用系统",
            "noticePageTitle": notice,
            "noticePageLead": "开放时间、借阅须知与临时通知，点击条目阅读全文。",
            "messagesPageLead": "审核结果、还书提醒与系统通知。",
            "recommendSectionTitle": "猜你喜欢",
            "recommendLatestHint": "最新上架",
        },
        "seeds": seeds,
        "portalBanners": banners,
    }

def _equip_schema(title: str, proposal_text: str = "") -> dict[str, Any]:
    """实验室默认；轻资产/演出/体育/影像/乐器/教具/户外/中性器材换皮（同壳）。

    具名档用 packs；枚举盖不住的开题走 gear，眉题由 ``equip_gear_noun`` 从题名抠。
    """
    from app.bake.scene_scan import equip_gear_noun, equip_product_kind

    # arch, title, author, isbn, train, owner, admin, sub, brow, lead_noun, menu, notice_page, banner_title, banner_lead
    packs: dict[str, tuple[str, str, str, str, str, str, str, str, str, str, str, str, str, str]] = {
        "light": (
            "物品", "物品名称", "提供方", "物品编号", "需押金", "保管人",
            "后勤主管（总管）", "物资管理员", "校园轻资产", "共享物品",
            "物品", "后勤公告", "共享物品", "雨伞、充电宝、门禁卡等分类检索，在线提交租借。",
        ),
        "costume": (
            "物品", "物品名称", "所属单位", "道具编号", "需试装", "保管人",
            "艺术团主管（总管）", "道具管理员", "演出道具", "服装道具",
            "道具", "艺术团公告", "服装道具", "按剧目或品类检索服装、道具与舞台器材。",
        ),
        "sports": (
            "器材", "器材名称", "品牌/规格", "器材编号", "需培训", "保管人",
            "体育部主管（总管）", "器材管理员", "体育器材", "体育器材",
            "器材", "体育部公告", "体育器材", "球类与运动器材分类检索，在线提交借用。",
        ),
        "media": (
            "设备", "设备名称", "品牌/型号", "设备编号", "需培训", "保管人",
            "传媒中心主管（总管）", "器材管理员", "影像设备", "摄影摄像设备",
            "设备", "传媒公告", "影像设备", "相机、摄像机与多媒体设备分类检索借用。",
        ),
        "music": (
            "乐器", "乐器名称", "品牌/规格", "乐器编号", "需培训", "保管人",
            "音乐系主管（总管）", "乐器管理员", "乐器租借", "乐器",
            "乐器", "音乐系公告", "乐器库", "弦乐、管乐与打击乐分类检索，在线申请借用。",
        ),
        "teach": (
            "教具", "教具名称", "规格说明", "教具编号", "需培训", "保管人",
            "教务主管（总管）", "教具管理员", "教学教具", "教学教具",
            "教具", "教务公告", "教具库", "模型、挂图与演示教具分类检索借用。",
        ),
        "outdoor": (
            "装备", "装备名称", "规格说明", "装备编号", "需培训", "保管人",
            "团委主管（总管）", "装备管理员", "户外拓展", "户外拓展装备",
            "装备", "团委公告", "拓展装备", "帐篷、登山与拓展器材分类检索借用。",
        ),
        "gear": (
            "器材", "器材名称", "品牌/型号", "器材编号", "需培训", "保管人",
            "设备主管（总管）", "器材管理员", "器材借用", "器材",
            "器材", "设备公告", "器材库", "检索可借器材、查看库存，在线提交借用申请。",
        ),
        "lab": (
            "设备", "设备名称", "品牌/型号", "资产编号", "需培训", "责任人",
            "实验室主管（总管）", "器材管理员", "实验室设备", "实验室设备",
            "设备", "实验室公告", "实验室器材", "检索设备、查看库存，在线提交借用申请。",
        ),
    }
    kind = equip_product_kind(title, proposal_text)
    (
        arch_lab, title_lab, author_lab, isbn_lab, train_lab, owner_lab,
        admin_lab, sub_lab, brow, lead_noun, menu, notice_page, ban_t, ban_lead,
    ) = packs.get(kind) or packs["lab"]
    if kind == "gear":
        noun = equip_gear_noun(title, proposal_text)
        brow = noun
        lead_noun = noun
        ban_t = noun
        ban_lead = f"检索可借{noun}、查看库存，在线提交借用申请。"
        if noun.endswith(("器材", "器械", "用具")):
            arch_lab, title_lab, isbn_lab, menu = "器材", "器材名称", "器材编号", "器材"
        elif noun.endswith("装备"):
            arch_lab, title_lab, isbn_lab, menu = "装备", "装备名称", "装备编号", "装备"
        elif noun.endswith("设备"):
            arch_lab, title_lab, isbn_lab, menu = "设备", "设备名称", "设备编号", "设备"
    loan_word = "租借" if kind in ("light", "costume", "music") else "借用"
    lead = f"验证码登录；检索{lead_noun}并申请{loan_word}，管理员审核后领用。"
    points = ["验证码登录", f"{menu}检索", f"{loan_word}申请与归还"]
    if kind == "lab":
        notice_title, notice_body = "设备借用须知", "请按需申请、按时归还；逾期将登记催还。"
        notice_lead = "借用须知、开放时段与临时通知，点击条目阅读全文。"
    elif kind == "costume":
        notice_title = "租借须知"
        notice_body = "请爱护服装道具、按时归还；损坏须登记说明。"
        notice_lead = "租借须知、排练档期与临时通知，点击条目阅读全文。"
    elif loan_word == "租借":
        notice_title, notice_body = "租借须知", "请按需申请、按时归还；逾期将登记催还。"
        notice_lead = "租借须知、开放时段与临时通知，点击条目阅读全文。"
    else:
        notice_title, notice_body = "借用须知", "请按需申请、按时归还；逾期将登记催还。"
        notice_lead = "借用须知、开放时段与临时通知，点击条目阅读全文。"
    register_hint = f"注册后可申请{loan_word}{lead_noun}"
    ban_notice = "借用须知" if kind == "lab" else notice_title
    banners = [
        {"title": ban_t, "lead": ban_lead},
        {"title": ban_notice, "lead": notice_body},
        {"title": "领用时段", "lead": f"工作日办理领用与归还，详见{notice_page}。"},
        {"title": f"我的{loan_word}", "lead": "登录后查看审核进度与归还期限。"},
        {"title": f"{menu}公告", "lead": "停用检修与临时安排见公告栏。"},
    ]
    return _with_portal_banners(
        archive_ticket_schema(
            title,
            domain="DOM-EQUIP",
            user_role_id="user",
            user_label="借用人",
            admin_label=admin_lab,
            subadmin_label=sub_lab,
            archive_key="equip",
            archive_label=arch_lab,
            archive_plural=arch_lab,
            archive_fields=[
                {"key": "title", "label": title_lab, "type": "string"},
                {"key": "author", "label": author_lab, "type": "string"},
                {"key": "isbn", "label": isbn_lab, "type": "string"},
                {"key": "category", "label": "分类", "type": "select"},
                {"key": "stock", "label": "可借数量", "type": "number"},
                {"key": "requiresTraining", "label": train_lab, "type": "boolean"},
                {"key": "ownerName", "label": owner_lab, "type": "string"},
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
            archive_menu_admin=f"{menu}管理",
            archive_menu_user=f"{menu}检索",
            users_menu="用户管理",
            auth_eyebrow=brow,
            auth_lead=lead,
            auth_points=points,
            register_hint=register_hint,
            notice_title=notice_title,
            notice_body=notice_body,
            notice_page_title=notice_page,
            notice_page_lead=notice_lead,
            my_tickets_label="我的借用",
            pending_label="借用审核",
            records_label="借用记录",
            deadline_label="逾期催还",
            soft_delete=True,
        ),
        banners,
    )

def _asset_schema(title: str, proposal_text: str = "") -> dict[str, Any]:
    """固定资产 / 耗材申领：高校物资 vs 企业仓储（同 _food_schema 分支）。"""
    from app.bake.scene_scan import scene_for

    campus = scene_for("DOM-ASSET", title, proposal_text) == "campus"
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

def _crm_schema(title: str, proposal_text: str = "") -> dict[str, Any]:
    """轻量 CRM：销售默认；律所/家访/校企深皮；校园创业团队走 campus。"""
    from app.bake.schema.deep_skin_overrides import crm_kind_overrides
    from app.bake.schema.followup_presets import (
        _std_archive_fields,
        followup_domain_schema,
    )
    from app.bake.scene_scan import crm_product_kind, scene_crm_parts

    kind = crm_product_kind(title, proposal_text)
    pack = crm_kind_overrides(kind, _std_archive_fields)
    if pack:
        return followup_domain_schema(title, "DOM-CRM", overrides=pack)
    if scene_crm_parts(title, proposal_text) == "campus":
        return followup_domain_schema(
            title,
            "DOM-CRM",
            overrides={
                "user_label": "成员",
                "admin_label": "指导教师（总管）",
                "archive_label": "客户",
                "archive_plural": "客户",
                "archive_fields": _std_archive_fields(
                    "客户名称",
                    "联系人",
                    "电话/备注",
                    "跟进阶段",
                    ["线索", "意向", "成交", "搁置"],
                    "客户分级",
                    "可跟进",
                ),
                "auth_eyebrow": "校园创业",
                "auth_lead": "验证码登录；登记名下客户并提交跟进，跟进即时生效，可在完成后结案。",
                "auth_points": ["验证码登录", "客户档案", "跟进记录"],
                "notice_page_title": "团队公告",
                "banners": [
                    {"title": "客户档案", "lead": "按分级浏览客户，维护联系人与备注。"},
                    {"title": "登记客户", "lead": "登录后可登记名下客户，即时可见。"},
                    {"title": "客户跟进", "lead": "提交跟进记录即时生效，办结后可追溯。"},
                    {"title": "团队公告", "lead": "跟进规范与通知见公告栏。"},
                    {"title": "我的跟进", "lead": "登录后查看跟进进度。"},
                    {"title": "分级管理", "lead": "按客户分级筛选。"},
                ],
            },
        )
    return followup_domain_schema(title, "DOM-CRM")

def _event_schema(title: str, proposal_text: str = "") -> dict[str, Any]:
    """事件/公卫：校园 / 社区网格 / 养老机构 / 企业复工 / 默认随访（同 _food_schema 分支）。

    scene 管身份档；``event_product_kind`` 管监测皮 vs 应急上报皮（默认 monitor，不改能力壳）。
    """
    from app.bake.schema.followup_presets import (
        _std_archive_fields,
        followup_domain_schema,
    )
    from app.bake.scene_scan import event_product_kind, scene_event_parts

    scene = scene_event_parts(title, proposal_text)
    kind = event_product_kind(title, proposal_text)
    if scene == "campus":
        schema = followup_domain_schema(
            title,
            "DOM-EVENT",
            overrides={
                "user_label": "师生",
                "admin_label": "学工主管（总管）",
                "subadmin_label": "班主任",
                "archive_label": "学生",
                "archive_plural": "学生",
                "archive_fields": _std_archive_fields(
                    "学生姓名",
                    "责任教师",
                    "班级/健康摘要",
                    "处置阶段",
                    ["待核查", "排查中", "处置中", "已闭环"],
                    "关注分类",
                    "可上报",
                ),
                "archive_menu_admin": "学生档案",
                "archive_menu_user": "学生列表",
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
        return _event_apply_incident_skin(schema, scene) if kind == "incident" else schema
    if scene == "institution":
        schema = followup_domain_schema(
            title,
            "DOM-EVENT",
            overrides={
                "user_label": "家属",
                "admin_label": "机构主管（总管）",
                "subadmin_label": "照护员",
                "archive_label": "老人",
                "archive_plural": "老人",
                "archive_fields": _std_archive_fields(
                    "老人姓名",
                    "责任照护",
                    "房号/健康摘要",
                    "照护阶段",
                    ["待核查", "监测中", "处置中", "已闭环"],
                    "照护分类",
                    "可上报",
                ),
                "archive_menu_admin": "老人档案",
                "archive_menu_user": "老人列表",
                "auth_eyebrow": "机构照护",
                "auth_lead": "验证码登录；维护入住老人档案并打卡/上报，异常由照护员处置。",
                "auth_points": ["验证码登录", "老人档案", "健康打卡", "异常上报"],
                "notice_page_title": "机构公告",
                "notice_title": "照护须知",
                "notice_body": "请如实登记老人健康与照护要素；异常请及时上报并由主管确认处置。",
                "banners": [
                    {"title": "老人档案", "lead": "按分类浏览入住老人，维护房号与健康摘要。"},
                    {"title": "健康打卡", "lead": "每日体征打卡或随访，查看今日未打卡。"},
                    {"title": "异常上报", "lead": "跌倒、发热等线索提交上报，办结可追溯。"},
                    {"title": "机构公告", "lead": "照护规范与通知见公告栏。"},
                    {"title": "我的上报", "lead": "登录后查看上报进度与记录。"},
                    {"title": "分类管理", "lead": "按分类筛选重点老人。"},
                ],
            },
        )
        return _event_apply_incident_skin(schema, scene) if kind == "incident" else schema
    if scene == "enterprise":
        schema = followup_domain_schema(
            title,
            "DOM-EVENT",
            overrides={
                "user_label": "员工",
                "admin_label": "企管主管（总管）",
                "subadmin_label": "监测员",
                "archive_label": "员工",
                "archive_plural": "员工",
                "archive_fields": _std_archive_fields(
                    "员工姓名",
                    "责任监测",
                    "部门/健康摘要",
                    "监测阶段",
                    ["待核查", "监测中", "处置中", "已闭环"],
                    "风险分类",
                    "可上报",
                ),
                "archive_menu_admin": "员工档案",
                "archive_menu_user": "员工列表",
                "auth_eyebrow": "企业复工",
                "auth_lead": "验证码登录；维护员工档案并健康打卡/上报，异常由监测员处置。",
                "auth_points": ["验证码登录", "员工档案", "健康打卡", "异常上报"],
                "notice_page_title": "企管公告",
                "notice_title": "监测须知",
                "notice_body": "请如实登记体温与健康状况；异常请及时上报并由主管确认复工评估。",
                "banners": [
                    {"title": "员工档案", "lead": "按部门浏览员工，维护岗位与健康摘要。"},
                    {"title": "健康打卡", "lead": "每日打卡或随访，查看今日未打卡。"},
                    {"title": "异常上报", "lead": "发热、暴露等线索提交上报，办结可追溯。"},
                    {"title": "企管公告", "lead": "复工规范与通知见公告栏。"},
                    {"title": "我的上报", "lead": "登录后查看上报进度与记录。"},
                    {"title": "分类管理", "lead": "按风险分类筛选重点员工。"},
                ],
            },
        )
        return _event_apply_incident_skin(schema, scene) if kind == "incident" else schema
    if scene == "community":
        # 开题一线填报=网格员（门户 user）；值班员=子管确认；对象档案≠登录身份
        schema = followup_domain_schema(
            title,
            "DOM-EVENT",
            overrides={
                "user_label": "网格员",
                "admin_label": "主管（总管）",
                "subadmin_label": "值班员",
                "archive_label": "对象",
                "archive_plural": "对象",
                "archive_fields": _std_archive_fields(
                    "对象姓名",
                    "责任网格",
                    "住址/健康摘要",
                    "处置阶段",
                    ["待核查", "排查中", "处置中", "已闭环"],
                    "关注分类",
                    "可上报",
                ),
                "archive_menu_admin": "对象档案",
                "archive_menu_user": "对象列表",
                "auth_eyebrow": "社区公卫",
                "auth_lead": "验证码登录；维护对象档案并打卡/上报，异常由值班员确认处置。",
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
        return _event_apply_incident_skin(schema, scene) if kind == "incident" else schema
    # default：慢病随访/院感/献血等公卫随访档（禁止校园学号壳与食堂种子）
    schema = followup_domain_schema(
        title,
        "DOM-EVENT",
        overrides={
            "user_label": "随访对象",
            "admin_label": "公卫主管（总管）",
            "subadmin_label": "随访员",
            "archive_label": "对象",
            "archive_plural": "对象",
            "archive_fields": _std_archive_fields(
                "对象姓名",
                "责任随访",
                "病种/健康摘要",
                "随访阶段",
                ["待核查", "随访中", "处置中", "已闭环"],
                "随访分类",
                "可上报",
            ),
            "archive_menu_admin": "对象档案",
            "archive_menu_user": "对象列表",
            "auth_eyebrow": "健康随访",
            "auth_lead": "验证码登录；维护随访对象档案并打卡/上报，异常由随访员处置。",
            "auth_points": ["验证码登录", "对象档案", "随访打卡", "异常上报"],
            "notice_page_title": "公卫公告",
            "notice_title": "随访须知",
            "notice_body": "请如实登记随访要素与指标；异常请及时上报并由主管确认处置。",
            "banners": [
                {"title": "对象档案", "lead": "按分类浏览随访对象，维护病种与摘要。"},
                {"title": "随访打卡", "lead": "按计划打卡或随访，查看今日未随访。"},
                {"title": "异常上报", "lead": "指标异常等线索提交上报，办结可追溯。"},
                {"title": "公卫公告", "lead": "随访规范与通知见公告栏。"},
                {"title": "我的上报", "lead": "登录后查看上报进度与记录。"},
                {"title": "分类管理", "lead": "按随访分类筛选重点对象。"},
            ],
        },
    )
    return _event_apply_incident_skin(schema, scene) if kind == "incident" else schema


def _event_apply_incident_skin(schema: dict[str, Any], scene: str) -> dict[str, Any]:
    """应急上报皮：保留角色/能力，改档案与门户叙事（弱化每日打卡）。"""
    from app.bake.schema.followup_presets import _std_archive_fields

    ents = dict(schema.get("entities") or {})
    arch = dict(ents.get("archive") or {})
    labels = dict(schema.get("labels") or {})
    menus = dict(schema.get("menus") or {})

    if scene == "community":
        arch["label"] = "事件"
        arch["labelPlural"] = "事件"
        arch["fields"] = _std_archive_fields(
            "事件标题",
            "责任网格",
            "地点/摘要",
            "处置阶段",
            ["待核查", "排查中", "处置中", "已闭环"],
            "事件分类",
            "可上报",
        )
        labels["authEyebrow"] = "应急上报"
        labels["authLead"] = "验证码登录；维护事件线索并提交上报，由值班员确认处置。"
        labels["authPoints"] = ["验证码登录", "事件台账", "线索上报", "处置记录"]
        labels["registerHint"] = "网格账号登录后可维护事件线索并提交上报"
        labels["noticePageTitle"] = "应急公告"
        admin_arch, user_arch = "事件台账", "事件列表"
        banners = [
            {"title": "事件台账", "lead": "按分类浏览事件线索，维护地点与处置阶段。"},
            {"title": "线索上报", "lead": "提交聚集性发热、隐患等线索，办结可追溯。"},
            {"title": "处置确认", "lead": "值班员确认处置进度，闭环后可查阅记录。"},
            {"title": "应急公告", "lead": "排查规范与临时通知见公告栏。"},
            {"title": "我的上报", "lead": "登录后查看上报进度与记录。"},
            {"title": "分类管理", "lead": "按事件分类筛选重点线索。"},
        ]
    elif scene == "campus":
        arch["label"] = "事件"
        arch["labelPlural"] = "事件"
        arch["fields"] = _std_archive_fields(
            "事件标题",
            "责任教师",
            "班级/地点摘要",
            "处置阶段",
            ["待核查", "排查中", "处置中", "已闭环"],
            "事件分类",
            "可上报",
        )
        labels["authEyebrow"] = "校园应急"
        labels["authLead"] = "验证码登录；维护校园事件线索并提交上报，由学工确认处置。"
        labels["authPoints"] = ["验证码登录", "事件台账", "线索上报", "处置记录"]
        labels["registerHint"] = "内部账号登录后可维护事件线索并提交上报"
        labels["noticePageTitle"] = "学工公告"
        admin_arch, user_arch = "事件台账", "事件列表"
        banners = [
            {"title": "事件台账", "lead": "按班级/分类浏览事件线索。"},
            {"title": "线索上报", "lead": "因病缺课聚集、校园隐患等提交上报。"},
            {"title": "处置确认", "lead": "学工确认处置并办结。"},
            {"title": "学工公告", "lead": "应急规范与通知见公告栏。"},
            {"title": "我的上报", "lead": "登录后查看上报进度与记录。"},
            {"title": "分类管理", "lead": "按事件分类筛选。"},
        ]
    else:
        # institution / enterprise / default：只改叙事，档案主体名保留
        labels["authEyebrow"] = {
            "institution": "机构应急",
            "enterprise": "企管应急",
        }.get(scene, "应急上报")
        labels["authLead"] = "验证码登录；维护事件线索并提交上报，异常由值班岗确认处置。"
        labels["authPoints"] = ["验证码登录", "事件线索", "上报处置", "办结记录"]
        labels["registerHint"] = "内部账号登录后可维护事件线索并提交上报"
        admin_arch = user_arch = None
        banners = [
            {"title": "事件线索", "lead": "浏览待处置线索，维护摘要与阶段。"},
            {"title": "线索上报", "lead": "提交异常线索，办结后可追溯。"},
            {"title": "处置确认", "lead": "值班岗确认处置进度。"},
            {"title": "应急公告", "lead": "排查规范与通知见公告栏。"},
            {"title": "我的上报", "lead": "登录后查看上报进度与记录。"},
            {"title": "分类管理", "lead": "按分类筛选重点线索。"},
        ]
        if arch.get("label") in ("对象", "事件"):
            arch["label"] = "事件"
            arch["labelPlural"] = "事件"
            arch["fields"] = _std_archive_fields(
                "事件标题",
                "责任人",
                "地点/摘要",
                "处置阶段",
                ["待核查", "排查中", "处置中", "已闭环"],
                "事件分类",
                "可上报",
            )
            admin_arch, user_arch = "事件台账", "事件列表"

    # 监测记录能力保留；应急皮换字段与文案（勿再露出体温/血压/血糖）
    labels["archiveLogPageTitle"] = "排查记录"
    labels["archiveLogPageLead"] = "按事件查看巡查登记；重大线索请走上报单。"
    labels["archiveLogSubmitLabel"] = "登记巡查"
    labels["archiveLogMissingTitle"] = "待巡查"
    labels["archiveLogSectionTitle"] = "巡查登记"

    log_ent = dict(ents.get("archiveLog") or {})
    log_ent["key"] = log_ent.get("key") or "archive_log"
    log_ent["label"] = "排查记录"
    log_ent["labelPlural"] = "排查记录"
    log_ent["defaultType"] = "patrol"
    log_ent["typeOptions"] = [
        {"value": "patrol", "label": "现场巡查"},
        {"value": "verify", "label": "线索复核"},
        {"value": "dispose", "label": "处置登记"},
    ]
    log_ent["fields"] = [
        {"key": "sceneStatus", "label": "现场情况", "type": "string"},
        {"key": "peopleCount", "label": "涉及人数", "type": "string"},
        {"key": "measure", "label": "已采取措施", "type": "string"},
        {"key": "note", "label": "备注", "type": "textarea"},
    ]
    log_ent["requireItem"] = True
    ents["archiveLog"] = log_ent

    ents["archive"] = arch
    schema["entities"] = ents
    schema["labels"] = labels
    if banners:
        schema["portalBanners"] = banners
        # 部分壳把 banners 挂在别处时仍刷新 labels 侧入口文案
    admin = list(menus.get("admin") or [])
    user = list(menus.get("user") or [])
    for m in admin:
        if not isinstance(m, dict):
            continue
        if m.get("key") == "archive" and admin_arch:
            m["label"] = admin_arch
        if m.get("key") == "archive_logs":
            m["label"] = labels["archiveLogPageTitle"]
        if m.get("key") == "category" and scene in ("community", "campus", "default"):
            m["label"] = "事件分类管理"
    for m in user:
        if isinstance(m, dict) and m.get("key") == "archive" and user_arch:
            m["label"] = user_arch
    menus["admin"] = admin
    menus["user"] = user
    schema["menus"] = menus
    return schema


def _attend_schema(title: str, proposal_text: str = "") -> dict[str, Any]:
    """考勤请假：假种档案 + 本人请假填单；题名/开题含学生/校园走学工口径。"""
    from app.bake.schema.followup_presets import _std_archive_fields, followup_domain_schema
    from app.bake.scene_scan import scene_for

    campus = scene_for("DOM-ATTEND", title, proposal_text) == "campus"
    leave_fields = _std_archive_fields(
        "假种名称",
        "适用说明",
        "申请须知备注",
        "开放状态",
        ["开放申请", "暂停", "已关闭"],
        "假种分类",
        "可申请",
    )
    if not campus:
        return followup_domain_schema(
            title,
            "DOM-ATTEND",
            overrides={
                "user_label": "员工",
                "admin_label": "人事主管（总管）",
                "subadmin_label": "考勤员",
                "archive_label": "假种",
                "archive_plural": "假种",
                "archive_fields": leave_fields,
                "archive_menu_admin": "假种档案",
                "archive_menu_user": "假种说明",
                "auth_eyebrow": "员工考勤",
                "auth_lead": "验证码登录；在「我的请假」选择假种提交本人请假，审批通过后按时销假（不能代同事请假）。",
                "auth_points": ["验证码登录", "本人请假填单", "审批与销假"],
                "notice_page_title": "人事公告",
                "notice_page_lead": "考勤与请假通知，点击条目阅读全文。",
                "banners": [
                    {"title": "本人请假", "lead": "登录后在「我的请假」选假种、填事由并提交。"},
                    {"title": "假种说明", "lead": "查阅事假、病假、年假等开放规则与须知。"},
                    {"title": "人事公告", "lead": "请假节点与销假须知见公告栏。"},
                    {"title": "审批销假", "lead": "跟踪本人审批进度，返回后按时销假。"},
                    {"title": "分类查阅", "lead": "假种说明可按分类筛选查阅。"},
                ],
            },
        )
    return followup_domain_schema(
        title,
        "DOM-ATTEND",
        overrides={
            "user_label": "学生",
            "admin_label": "学工主管（总管）",
            "subadmin_label": "辅导员",
            "archive_label": "假种",
            "archive_plural": "假种",
            "archive_fields": leave_fields,
            "archive_menu_admin": "假种档案",
            "archive_menu_user": "假种说明",
            "auth_eyebrow": "学生请假",
            "auth_lead": "验证码登录；在「我的请假」选择假种提交本人请假，辅导员审批后按时销假（不能代同学请假）。",
            "auth_points": ["验证码登录", "本人请假填单", "审批与销假"],
            "notice_page_title": "学工公告",
            "notice_page_lead": "请销假通知，点击条目阅读全文。",
            "banners": [
                {"title": "本人请假", "lead": "登录后在「我的请假」选假种、填事由并提交。"},
                {"title": "假种说明", "lead": "查阅事假、病假等开放规则与须知。"},
                {"title": "学工公告", "lead": "请销假节点与须知见公告栏。"},
                {"title": "审批销假", "lead": "跟踪本人审批进度，返校后按时销假。"},
                {"title": "分类查阅", "lead": "假种说明可按分类筛选查阅。"},
            ],
        },
    )

def _fund_schema(title: str, proposal_text: str = "") -> dict[str, Any]:
    """资助：校园奖助学金默认；员工福利/企业补助走 enterprise。"""
    from app.bake.schema.followup_presets import (
        _std_archive_fields,
        followup_domain_schema,
    )
    from app.bake.scene_scan import scene_for

    if scene_for("DOM-FUND", title, proposal_text) == "enterprise":
        return followup_domain_schema(
            title,
            "DOM-FUND",
            overrides={
                "user_label": "员工",
                "admin_label": "福利主管（总管）",
                "subadmin_label": "人事专员",
                "archive_label": "福利项目",
                "archive_plural": "福利项目",
                "archive_fields": _std_archive_fields(
                    "项目名称",
                    "归口部门",
                    "名额/条件备注",
                    "开放状态",
                    ["开放申请", "审核中", "已截止", "已关闭"],
                    "福利类型",
                    "可申请",
                ),
                "archive_menu_admin": "福利项目",
                "archive_menu_user": "项目列表",
                "auth_eyebrow": "员工福利",
                "auth_lead": "验证码登录；浏览福利项目并提交申请，人事审核后反馈结果。",
                "auth_points": ["验证码登录", "福利项目", "申请与审核"],
                "register_hint": "注册后可提交福利申请",
                "notice_title": "福利须知",
                "notice_body": "请按通知提交申请材料；审批通过后留意发放进度。",
                "notice_page_title": "人事公告",
                "notice_page_lead": "福利节点与材料要求，点击条目阅读全文。",
                "pending_label": "福利审批",
                "contact_channel_options": ["线上申请", "人事窗口", "其他"],
                "banners": [
                    {"title": "项目浏览", "lead": "按福利类型查看开放项目与申请条件。"},
                    {"title": "在线申请", "lead": "选择项目提交申请单，等待人事审核。"},
                    {"title": "人事公告", "lead": "材料节点与发放说明见公告栏。"},
                    {"title": "我的申请", "lead": "登录后跟踪审批进度。"},
                    {"title": "分类检索", "lead": "节日慰问/困难补助/培训补贴快速筛选。"},
                ],
            },
        )
    return followup_domain_schema(title, "DOM-FUND")

def _labsafe_schema(title: str, proposal_text: str = "") -> dict[str, Any]:
    """实验室准入：校园默认；厂区/安环走 enterprise。"""
    from app.bake.schema.followup_presets import (
        _std_archive_fields,
        followup_domain_schema,
    )
    from app.bake.scene_scan import scene_for

    if scene_for("DOM-LABSAFE", title, proposal_text) == "enterprise":
        return followup_domain_schema(
            title,
            "DOM-LABSAFE",
            overrides={
                "user_label": "员工",
                "admin_label": "安环主管（总管）",
                "subadmin_label": "安全员",
                "archive_label": "实验室",
                "archive_plural": "实验室",
                "archive_fields": _std_archive_fields(
                    "实验室名称",
                    "厂区/负责人",
                    "安全等级备注",
                    "开放状态",
                    ["可申请", "审核中", "暂停准入", "已关闭"],
                    "实验室类型",
                    "可申请准入",
                ),
                "auth_eyebrow": "安环准入",
                "auth_lead": "验证码登录；选择实验室提交准入申请，完成安全培训审核后方可进室。",
                "auth_points": ["验证码登录", "实验室档案", "准入申请与审核"],
                "register_hint": "注册后可提交准入申请",
                "notice_page_title": "安环公告",
                "banners": [
                    {"title": "实验室目录", "lead": "按类型浏览厂区实验室与安全等级。"},
                    {"title": "准入申请", "lead": "提交准入单并附培训证明，等待安全员审核。"},
                    {"title": "安环公告", "lead": "准入节点与安全须知见公告栏。"},
                    {"title": "我的准入", "lead": "登录后跟踪审批结果。"},
                    {"title": "分类检索", "lead": "化学/机房/金工等快速定位。"},
                ],
            },
        )
    return followup_domain_schema(title, "DOM-LABSAFE")

def _recruit_schema(title: str, proposal_text: str = "") -> dict[str, Any]:
    """招聘：校园校招 vs 企业 HR（同 _food_schema 分支）。"""
    from app.bake.schema.followup_presets import followup_domain_schema
    from app.bake.scene_scan import scene_for

    scene = scene_for("DOM-RECRUIT", title, proposal_text)
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

def _dating_schema(title: str, proposal_text: str = "") -> dict[str, Any]:
    """婚恋交友：校园联谊 vs 社区相亲（默认社区）。"""
    from app.bake.schema.followup_presets import followup_domain_schema
    from app.bake.scene_scan import scene_for

    scene = scene_for("DOM-DATING", title, proposal_text)
    if scene == "campus":
        return followup_domain_schema(
            title,
            "DOM-DATING",
            overrides={
                "user_label": "同学",
                "admin_label": "学工主管（总管）",
                "subadmin_label": "联谊辅导员",
                "auth_eyebrow": "校园交友",
                "auth_lead": "验证码登录；浏览同学资料并发起牵线，学工审核后反馈结果。",
                "auth_points": ["验证码登录", "资料浏览", "牵线与审核"],
                "notice_page_title": "联谊公告",
                "banners": [
                    {"title": "资料浏览", "lead": "按类型查看同学资料与择偶意向。"},
                    {"title": "发起牵线", "lead": "选择资料提交牵线单，等待学工审核。"},
                    {"title": "联谊公告", "lead": "校园联谊节点与规范见公告。"},
                    {"title": "我的牵线", "lead": "跟踪审核进度与结果。"},
                    {"title": "分类检索", "lead": "按院系/年级等快速筛选。"},
                ],
            },
        )
    return followup_domain_schema(title, "DOM-DATING")

def _grade_schema(title: str, proposal_text: str = "") -> dict[str, Any]:
    """教务成绩默认；内训/培训考核走 enterprise。"""
    from app.bake.schema.followup_presets import (
        _std_archive_fields,
        followup_domain_schema,
    )
    from app.bake.scene_scan import scene_for

    if scene_for("DOM-GRADE", title, proposal_text) == "enterprise":
        return followup_domain_schema(
            title,
            "DOM-GRADE",
            overrides={
                "user_label": "学员",
                "admin_label": "培训主管（总管）",
                "subadmin_label": "培训专员",
                "archive_label": "培训课",
                "archive_plural": "培训课",
                "archive_fields": _std_archive_fields(
                    "课程名称",
                    "讲师",
                    "课号/学时",
                    "开课状态",
                    ["开课中", "已结课", "补考中", "已归档"],
                    "课程类别",
                    "可申请",
                ),
                "archive_menu_admin": "培训课档案",
                "archive_menu_user": "培训课列表",
                "ticket_label": "成绩申请单",
                "auth_eyebrow": "内训成绩",
                "auth_lead": "验证码登录；查看培训课并提交补考或成绩更正申请，由培训专员审核。",
                "auth_points": ["验证码登录", "培训课列表", "成绩申请"],
                "register_hint": "注册后可提交成绩相关申请",
                "notice_title": "成绩须知",
                "notice_body": "补考与更正须说明理由；不对接外部证书库。",
                "notice_page_title": "培训公告",
                "pending_label": "成绩审核",
                "contact_channel_options": ["成绩更正", "补考申请", "缓考备案", "其他"],
                "banners": [
                    {"title": "培训课列表", "lead": "按类别浏览内训课与讲师。"},
                    {"title": "成绩申请", "lead": "提交补考或成绩更正，等待培训确认。"},
                    {"title": "培训公告", "lead": "补考与成绩节点见公告栏。"},
                    {"title": "我的申请", "lead": "跟踪审核进度。"},
                    {"title": "分类检索", "lead": "必修/选修快速定位。"},
                ],
            },
        )
    return followup_domain_schema(title, "DOM-GRADE")

def _intern_schema(title: str, proposal_text: str = "") -> dict[str, Any]:
    """实习周报：校就业办默认；企业带教走 enterprise。"""
    from app.bake.schema.followup_presets import (
        _std_archive_fields,
        followup_domain_schema,
    )
    from app.bake.scene_scan import scene_for

    if scene_for("DOM-INTERN", title, proposal_text) == "enterprise":
        return followup_domain_schema(
            title,
            "DOM-INTERN",
            overrides={
                "user_label": "实习生",
                "admin_label": "实习主管（总管）",
                "subadmin_label": "企业导师",
                "archive_fields": _std_archive_fields(
                    "岗位名称",
                    "企业导师",
                    "部门/岗位说明",
                    "实习状态",
                    ["待上岗", "实习中", "已结束", "已鉴定"],
                    "实习类型",
                    "可交周报",
                ),
                "archive_menu_user": "岗位目录",
                "auth_eyebrow": "企业实习周报",
                "auth_lead": "验证码登录；从示范岗位目录选岗提交周报，企业导师审阅（≠多部门入职）。",
                "auth_points": ["验证码登录", "示范岗位目录", "周报提交与审阅"],
                "notice_page_title": "实习公告",
                "pending_label": "周报审阅",
                "banners": [
                    {"title": "岗位目录", "lead": "浏览示范实习岗位与企业导师（全库目录）。"},
                    {"title": "提交周报", "lead": "选一岗按周提交工作内容，等待审阅。"},
                    {"title": "实习公告", "lead": "实习与鉴定安排见公告。"},
                    {"title": "我的周报", "lead": "跟踪审阅结果。"},
                    {"title": "分类检索", "lead": "按实习类型筛选示范岗位。"},
                ],
            },
        )
    return followup_domain_schema(title, "DOM-INTERN")

def _parcel_schema(title: str, proposal_text: str = "") -> dict[str, Any]:
    """驿站：校园 vs 社区代收点（同 _food_schema 分支）。"""
    from app.bake.schema.followup_presets import followup_domain_schema
    from app.bake.scene_scan import scene_for

    if scene_for("DOM-PARCEL", title, proposal_text) == "community":
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

def _activity_schema(title: str, proposal_text: str = "") -> dict[str, Any]:
    from app.bake.scene_scan import activity_product_kind

    kind = activity_product_kind(title, proposal_text)
    # default：社团/志愿/讲座
    arch_title, arch_author, arch_isbn = "活动名称", "主办方", "地点"
    arch_noun, stock_lab = "活动", "剩余名额"
    brow = "活动报名"
    user, admin, sub = "报名者", "活动主管（总管）", "活动助理"
    apply_v, ticket_lab = "报名", "报名单"
    lead = "验证码登录；浏览活动并报名；系统检测时段冲突与报名截止；到场口令签到；结束未签到记爽约。"
    points = ["验证码登录", "活动检索", "报名、冲突检测、口令签到与爽约"]
    reg = "注册后可报名校园活动"
    notice_t = "报名须知"
    notice = "请如实填写资料；名额有限；时段冲突或已截止将无法提交；到场请向主办方索取签到码；活动结束后未签到将记为爽约。"
    notice_page = "活动公告"
    menu_a, menu_u = "活动管理", "活动检索"
    banners = [
        {"title": "热门活动", "lead": "社团、志愿、讲座分类浏览，在线报名。"},
        {"title": "到场签到", "lead": "到场向主办方索取签到码完成核验；时段重叠将无法重复报名。"},
        {"title": "活动公告", "lead": "变更与须知见公告栏。"},
        {"title": "我的日程", "lead": "登录后查看已报名活动与时段安排。"},
        {"title": "志愿时长", "lead": "志愿类活动可登记服务时长。"},
    ]
    if kind == "cert":
        arch_title, arch_author, arch_isbn = "报考/培训项目", "主办方/考点", "考点/说明"
        arch_noun, stock_lab = "报考项目", "剩余名额"
        brow = "证书报考"
        user, admin, sub = "报考人", "培训主管（总管）", "报名助理"
        apply_v, ticket_lab = "报名", "报名单"
        lead = "验证码登录；浏览证书报考与培训班项目并报名；系统检测时段冲突与报名截止。"
        points = ["验证码登录", "项目检索", "名额报名与审核"]
        reg = "注册后可报名培训班与证书报考"
        notice_t = "报考须知"
        notice = "请如实填写报考信息；名额有限；时段冲突或已截止将无法提交；本期不对接外部证书库。"
        notice_page = "培训公告"
        menu_a, menu_u = "项目管理", "项目检索"
        banners = [
            {"title": "报考项目", "lead": "证书报考、培训班与四六级名额分类浏览。"},
            {"title": "在线报名", "lead": "提交报名申请，审核通过后占名额。"},
            {"title": "培训公告", "lead": "考点变更与须知见公告栏。"},
            {"title": "我的报名", "lead": "登录后查看报考进度。"},
            {"title": "名额说明", "lead": "名额有限，请在截止前完成报名。"},
        ]
    elif kind == "ticket":
        arch_title, arch_author, arch_isbn = "场次/演出名称", "主办方", "场馆/须知"
        arch_noun, stock_lab = "场次", "剩余票额"
        brow = "票务报名"
        user, admin, sub = "观众", "票务主管（总管）", "票务助理"
        apply_v, ticket_lab = "领票报名", "领票单"
        lead = "验证码登录；浏览景区/演出场次并领票报名；系统检测时段冲突与报名截止（非选座购票）。"
        points = ["验证码登录", "场次检索", "领票报名与审核"]
        reg = "注册后可领票报名"
        notice_t = "领票须知"
        notice = "请如实填写联系方式；票额有限；时段冲突或已截止将无法提交；本期无选座与真支付。"
        notice_page = "票务公告"
        menu_a, menu_u = "场次管理", "场次检索"
        banners = [
            {"title": "场次目录", "lead": "景区与演出场次分类浏览，在线领票。"},
            {"title": "领票报名", "lead": "提交领票申请，审核通过后占票额。"},
            {"title": "票务公告", "lead": "场次变更与须知见公告栏。"},
            {"title": "我的领票", "lead": "登录后查看领票进度。"},
            {"title": "到场核验", "lead": "到场可向主办方索取签到码完成核验。"},
        ]
    elif kind == "blood":
        arch_title, arch_author, arch_isbn = "场次名称", "主办单位", "地点/注意事项"
        arch_noun, stock_lab = "场次", "剩余名额"
        brow = "献血开放日"
        user, admin, sub = "报名者", "场次主管（总管）", "场次助理"
        apply_v, ticket_lab = "报名", "报名单"
        lead = "验证码登录；浏览献血与开放日场次并报名；系统检测时段冲突与报名截止。"
        points = ["验证码登录", "场次检索", "报名与审核"]
        reg = "注册后可报名献血与开放日场次"
        notice_t = "报名须知"
        notice = "请如实填写资料与身体状况说明；名额有限；时段冲突或已截止将无法提交；本期无健康筛查建档引擎。"
        notice_page = "场次公告"
        menu_a, menu_u = "场次管理", "场次检索"
        banners = [
            {"title": "开放场次", "lead": "献血与开放日场次分类浏览。"},
            {"title": "在线报名", "lead": "提交报名申请，审核通过后占名额。"},
            {"title": "场次公告", "lead": "时间地点变更见公告栏。"},
            {"title": "我的报名", "lead": "登录后查看报名进度。"},
            {"title": "到场核验", "lead": "到场可向主办方索取签到码。"},
        ]
    elif kind == "camp":
        arch_title, arch_author, arch_isbn = "项目名称", "主办方", "集合地点/行程"
        arch_noun, stock_lab = "项目", "剩余名额"
        brow = "研学赛事"
        user, admin, sub = "报名者", "项目主管（总管）", "项目助理"
        apply_v, ticket_lab = "报名", "报名单"
        lead = "验证码登录；浏览研学、夏令营与赛事项目并报名；系统检测时段冲突与报名截止。"
        points = ["验证码登录", "项目检索", "报名与审核"]
        reg = "注册后可报名研学与赛事项目"
        notice_t = "报名须知"
        notice = "请如实填写资料；名额有限；时段冲突或已截止将无法提交；到场请向主办方索取签到码。"
        notice_page = "项目公告"
        menu_a, menu_u = "项目管理", "项目检索"
        banners = [
            {"title": "研学赛事", "lead": "研学、夏令营与赛事项目分类浏览。"},
            {"title": "在线报名", "lead": "提交报名申请，审核通过后占名额。"},
            {"title": "项目公告", "lead": "行程变更与须知见公告栏。"},
            {"title": "我的日程", "lead": "登录后查看已报名项目与时段。"},
            {"title": "到场签到", "lead": "到场向主办方索取签到码完成核验。"},
        ]
    return _with_portal_banners(
        archive_ticket_schema(
            title,
            domain="DOM-ACTIVITY",
            user_role_id="user",
            user_label=user,
            admin_label=admin,
            subadmin_label=sub,
            archive_key="activity",
            archive_label=arch_noun,
            archive_plural=arch_noun,
            archive_fields=[
                {"key": "title", "label": arch_title, "type": "string"},
                {"key": "author", "label": arch_author, "type": "string"},
                {"key": "isbn", "label": arch_isbn, "type": "string"},
                {"key": "category", "label": "分类", "type": "select"},
                {"key": "stock", "label": stock_lab, "type": "number"},
                {"key": "checkinCode", "label": "签到码", "type": "string"},
                {"key": "startAt", "label": "开始时间", "type": "datetime", "timeStepMinutes": 30},
                {"key": "endAt", "label": "结束时间", "type": "datetime", "timeStepMinutes": 30},
                {"key": "applyDeadlineAt", "label": "报名截止", "type": "datetime", "timeStepMinutes": 30},
                {"key": "serviceHours", "label": "志愿时长(小时)", "type": "number"},
            ],
            ticket_key="signup",
            ticket_label=ticket_lab,
            ticket_plural="报名" if kind != "ticket" else "领票",
            verbs={
                "apply": apply_v,
                "approve": "通过",
                "reject": "驳回",
                "return": "取消报名" if kind != "ticket" else "取消领票",
                "remind": "提醒",
            },
            states={
                "pending": "待审核",
                "approved": "已报名" if kind != "ticket" else "已领票",
                "rejected": "已驳回",
                "returned": "已取消",
                "overdue": "爽约",
            },
            archive_menu_admin=menu_a,
            archive_menu_user=menu_u,
            users_menu="用户管理",
            auth_eyebrow=brow,
            auth_lead=lead,
            auth_points=points,
            register_hint=reg,
            notice_title=notice_t,
            notice_body=notice,
            notice_page_title=notice_page,
            notice_page_lead=f"{notice_t}、变更与临时通知，点击条目阅读全文。",
            my_tickets_label="我的报名" if kind != "ticket" else "我的领票",
            pending_label="报名审核" if kind != "ticket" else "领票审核",
            records_label="报名记录" if kind != "ticket" else "领票记录",
            with_deadline=False,
            allow_rating=True,
            week_calendar=True,
            week_calendar_label="我的日程",
            allow_checkin=True,
            no_show_after_end=True,
            no_show_penalty_yuan=0,
            approve_ends_flow=True,
        ),
        banners,
    )

def _lost_schema(title: str, proposal_text: str = "") -> dict[str, Any]:
    """失物招领 / 宠物领养 / 捐赠认领：同认领壳，文案跟题名/开题走（同 _meeting_schema）。"""
    from app.bake.scene_scan import scene_lost_parts

    sc = scene_lost_parts(title, proposal_text)
    if sc == "adopt":
        noun, remark, admin, sub = "待领养", "领养说明", "领养站主管（总管）", "领养专员"
        user, verb = "申请人", "领养"
        title_lab, author_lab, isbn_lab = "昵称/编号", "登记人", "品种/健康说明"
        kind_opts, found_lab = ["待领养", "已预约看宠"], "登记时间"
        brow, menu_u = "宠物领养", "待领养检索"
        lead = "验证码登录；浏览待领养档案，提交领养申请，管理员审核后办理。"
        notice = "请如实填写养宠条件与联系方式；审核通过后按通知办理交接。"
        notice_t, notice_page, return_v = "领养须知", "领养公告", "撤销申请"
        reg = "注册后可浏览并申请领养"
    elif sc == "donate":
        noun, remark, admin, sub = "捐赠物资", "认领说明", "捐赠站主管（总管）", "认领专员"
        user, verb = "申请人", "认领"
        title_lab, author_lab, isbn_lab = "物资名称", "登记人", "规格/数量说明"
        kind_opts, found_lab = ["可认领", "已预约领取"], "登记时间"
        brow, menu_u = "捐赠认领", "物资名录"
        lead = "验证码登录；浏览捐赠物资名录，提交认领申请，管理员审核后领取。"
        notice = "请如实填写用途与联系方式；审核通过后按通知到站领取，本期无物流寄送。"
        notice_t, notice_page, return_v = "认领须知", "捐赠公告", "撤销认领"
        reg = "注册后可浏览物资并申请认领"
    elif sc == "community":
        noun, remark, admin, sub = "启事", "认领说明", "社区招领主管（总管）", "招领管理员"
        user, verb = "居民", "认领"
        title_lab, author_lab, isbn_lab = "物品名称", "拾获/登记人", "小区地点/特征"
        kind_opts, found_lab = ["招领", "寻物"], "拾获时间"
        brow, menu_u = "社区招领", "失物检索"
        lead = "验证码登录；浏览社区失物启事，提交认领申请，管理员审核后领取。"
        notice = "认领时请提供有效身份与物品特征；审核通过后到物业/驿站领取。"
        notice_t, notice_page, return_v = "招领须知", "社区公告", "撤销认领"
        reg = "注册后可浏览启事并申请认领"
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

