"""交易 / 预约类域 builder。"""

from __future__ import annotations

from typing import Any

from app.bake.schema.shells import (
    _CAMPUS_HINTS,
    _copy_scan_text,
    _scan_has,
    order_shell_schema,
    slot_shell_schema,
)

def _shop_schema(title: str, proposal_text: str = "") -> dict[str, Any]:
    t = _copy_scan_text(title, proposal_text)
    campus = any(k in t for k in ("校园", "校内", "二手", "学校"))
    brow = "校园商城" if campus else "在线商城"
    lead = (
        "验证码登录；浏览商品、加入购物车并提交订单（演示无真支付）。"
        if not campus
        else "验证码登录；浏览校园商品、加入购物车并提交订单（演示无真支付）。"
    )
    return order_shell_schema(
        title,
        domain="DOM-SHOP",
        user_role_id="user",
        user_label="买家",
        admin_label="商城主管（总管）",
        subadmin_label="订单管理员",
        archive_key="product",
        archive_label="商品",
        archive_plural="商品",
            archive_fields=[
            {"key": "title", "label": "商品名", "type": "string"},
            {"key": "author", "label": "单价(元)", "type": "number", "format": "money"},
            {"key": "isbn", "label": "货号", "type": "string"},
            {"key": "conditionGrade", "label": "成色", "type": "string"},
            {"key": "sellerNote", "label": "卖家备注", "type": "string"},
            {"key": "category", "label": "分类", "type": "select"},
            {"key": "stock", "label": "库存", "type": "number"},
        ],
        archive_menu_admin="商品管理",
        archive_menu_user="商品浏览",
        users_menu="用户管理",
        cart_label="购物车",
        my_orders_label="我的订单",
        orders_admin_label="订单管理",
        auth_eyebrow=brow,
        auth_lead=lead,
        auth_points=["验证码登录", "商品浏览", "购物车与订单"],
        register_hint="注册后可购物下单",
        notice_title="商城须知",
        notice_body="演示环境无真支付；下单后由管理员确认发货/自提。",
        notice_page_title="商城公告",
    )

def _food_schema(title: str, proposal_text: str = "") -> dict[str, Any]:
    t = _copy_scan_text(title, proposal_text)
    canteen = any(k in t for k in ("食堂", "校园", "档口", "学子"))
    if canteen:
        admin, sub, brow, win, notice = "食堂主管（总管）", "档口管理员", "食堂点餐", "窗口", "食堂公告"
        body = "下单后到对应窗口取餐或按约定配送；演示无真支付。"
    else:
        admin, sub, brow, win, notice = "门店主管（总管）", "店员", "点餐外卖", "档口/门店", "门店公告"
        body = "支持堂食、自取或外卖配送演示；无真支付。"
    return order_shell_schema(
        title,
        domain="DOM-FOOD",
        user_role_id="user",
        user_label="用餐者",
        admin_label=admin,
        subadmin_label=sub,
        archive_key="dish",
        archive_label="菜品",
        archive_plural="菜品",
        archive_fields=[
            {"key": "title", "label": "菜品名", "type": "string"},
            {"key": "author", "label": "单价(元)", "type": "number", "format": "money"},
            {"key": "isbn", "label": win, "type": "string"},
            {"key": "spicyLevel", "label": "辣度", "type": "string"},
            {"key": "isVegetarian", "label": "素食(1是0否)", "type": "number"},
            {"key": "category", "label": "分类", "type": "select"},
            {"key": "stock", "label": "可售份数", "type": "number"},
        ],
        archive_menu_admin="菜品管理",
        archive_menu_user="点餐",
        users_menu="用户管理",
        cart_label="已选菜品",
        my_orders_label="我的订单",
        orders_admin_label="订单管理",
        auth_eyebrow=brow,
        auth_lead="验证码登录；选菜加入清单并下单（演示无真支付）。",
        auth_points=["验证码登录", "菜品浏览", "下单"],
        register_hint="注册后可点餐",
        notice_title="点餐须知",
        notice_body=body,
        notice_page_title=notice,
        order_states={
            "pending": "待出餐",
            "confirmed": "制作中",
            "shipped": "配送中/待取",
            "completed": "已完成",
            "cancelled": "已取消",
        },
    )

def _meeting_schema(title: str, proposal_text: str = "") -> dict[str, Any]:
    """会议室 / 琴房 / 体育场 / 自习室 / 座位等共用时段预约壳，文案跟题名/开题走。"""
    t = _copy_scan_text(title, proposal_text)
    if any(k in t for k in ("琴房", "排练", "舞蹈")):
        noun, remark, admin, sub = "琴房", "排练说明", "琴房管理员（总管）", "琴房值班"
    elif any(k in t for k in ("体育场", "体育馆", "球馆", "羽毛球场", "篮球场", "足球场", "游泳")):
        noun, remark, admin, sub = "场地", "预约说明", "场馆主管（总管）", "场馆管理员"
    elif any(k in t for k in ("座位", "占座", "选座")):
        noun, remark, admin, sub = "座位", "用途说明", "座位管理员（总管）", "座位管理员"
    elif any(k in t for k in ("自习室", "研习室", "研讨室")):
        noun, remark, admin, sub = "自习室", "用途说明", "教务主管（总管）", "自习室管理员"
    elif any(k in t for k in ("工位", "实验室", "实训室")):
        noun, remark, admin, sub = "实验室", "使用说明", "实验室主管（总管）", "实验室管理员"
    elif "会议" in t:
        noun, remark, admin, sub = "会议室", "会议主题", "会务主管（总管）", "会务管理员"
    else:
        noun, remark, admin, sub = "场地", "预约说明", "场地主管（总管）", "场地管理员"
    return slot_shell_schema(
        title,
        domain="DOM-MEETING",
        user_role_id="user",
        user_label="预约人",
        admin_label=admin,
        subadmin_label=sub,
        archive_key="room",
        archive_label=noun,
        archive_plural=noun,
        archive_fields=[
            {"key": "title", "label": noun, "type": "string"},
            {"key": "author", "label": "费用", "type": "number", "format": "money"},
            {"key": "isbn", "label": "位置", "type": "string"},
            {"key": "seatCapacity", "label": "容纳人数", "type": "number"},
            {"key": "category", "label": "类型", "type": "select"},
        ],
        archive_menu_admin=f"{noun}管理",
        archive_menu_user=noun,
        users_menu="用户管理",
        my_resv_label="我的预约",
        resv_admin_label="预约记录",
        auth_eyebrow=f"{noun}预约",
        auth_lead=f"验证码登录；选择{noun}与时段，占坑预约；管理端可办结履约。",
        auth_points=["验证码登录", f"{noun}检索", "时段占坑预约与办结"],
        register_hint=f"注册后可预约{noun}",
        notice_title="预约须知",
        notice_body=f"请填写{remark}；按时使用；管理端可登记完成；不用请及时取消以释放时段。",
        notice_page_title="预约公告",
        reserve_require_remark=True,
        reserve_remark_label=remark,
        complete_verb="完成使用",
        completed_label="已完成",
    )

def _hospital_schema(title: str, proposal_text: str = "") -> dict[str, Any]:
    """门诊 / 疫苗接种 / 宠物医院：同号源预约壳，文案跟题名/开题走（同 _meeting_schema）。"""
    t = _copy_scan_text(title, proposal_text)
    if any(k in t for k in ("疫苗", "HPV", "接种预约", "接种点")):
        noun, remark, admin, sub = "接种门诊", "接种人", "接种点主管（总管）", "预约管理员"
        user, brow, resv = "接种人", "疫苗预约", "预约"
        fee, isbn, cat, title_lab = "费用(元)", "针次/说明", "疫苗类型", "门诊/疫苗名称"
        lead = "验证码登录；选择疫苗门诊与时段预约接种；到点后由管理端登记完成。"
        notice = "号源有限；请填写接种人姓名，按预约时段到点；完成后由前台办结；取消请提前操作。"
        notice_t, notice_page, reg, done = "接种须知", "接种公告", "注册后可预约疫苗接种", "接种"
        menu_u, points_mid = "选门诊", "门诊检索"
    elif any(k in t for k in ("宠物", "宠医", "爱宠", "猫狗", "犬猫")):
        noun, remark, admin, sub = "医生", "宠物/就诊人", "宠物医院主管（总管）", "挂号员"
        user, brow, resv = "宠主", "宠物挂号", "挂号"
        fee, isbn, cat, title_lab = "挂号费(元)", "职称/说明", "科室", "医生"
        lead = "验证码登录；选择科室医生与号源时段为宠物挂号；到诊后由前台登记就诊完成。"
        notice = "号源有限；请填写宠物昵称与就诊人；按时到诊；就诊完成后由前台办结；取消请提前操作。"
        notice_t, notice_page, reg, done = "挂号须知", "宠物医院公告", "注册后可以宠主身份挂号", "就诊"
        menu_u, points_mid = "选医生", "医生检索"
    else:
        noun, remark, admin, sub = "医生", "就诊人", "医务主管（总管）", "挂号员"
        user, brow, resv = "患者", "门诊挂号", "挂号"
        fee, isbn, cat, title_lab = "挂号费(元)", "职称/说明", "科室", "医生"
        lead = "验证码登录；选择科室医生与号源时段挂号；到诊后由管理端登记就诊完成。"
        notice = "号源有限；请填写就诊人姓名，按时就诊；就诊完成后由挂号台办结；取消请提前操作。"
        notice_t, notice_page, reg, done = "挂号须知", "医院公告", "注册后可以患者身份挂号", "就诊"
        menu_u, points_mid = "选医生", "医生检索"
    return slot_shell_schema(
        title,
        domain="DOM-HOSPITAL",
        user_role_id="patient",
        user_label=user,
        admin_label=admin,
        subadmin_label=sub,
        archive_key="doctor",
        archive_label=noun,
        archive_plural=noun,
        archive_fields=[
            {"key": "title", "label": title_lab, "type": "string"},
            {"key": "author", "label": fee, "type": "number", "format": "money"},
            {"key": "isbn", "label": isbn, "type": "string"},
            {"key": "category", "label": cat, "type": "select"},
        ],
        archive_menu_admin=f"{noun}管理",
        archive_menu_user=menu_u,
        users_menu=f"{user}管理",
        my_resv_label=f"我的{resv}",
        resv_admin_label=f"{resv}记录",
        resv_label=resv,
        auth_eyebrow=brow,
        auth_lead=lead,
        auth_points=["验证码登录", points_mid, f"分时{resv}与{done}办结"],
        register_hint=reg,
        notice_title=notice_t,
        notice_body=notice,
        notice_page_title=notice_page,
        reserve_require_remark=True,
        reserve_remark_label=remark,
        complete_verb=f"{done}完成",
        completed_label=f"已{done}",
    )

def _parking_schema(title: str, proposal_text: str = "") -> dict[str, Any]:
    """车位：校园 vs 商场/小区车场（同 _food_schema 分支）。"""
    t = _copy_scan_text(title, proposal_text)
    campus = _scan_has(t, _CAMPUS_HINTS)
    if campus:
        brow, lead, admin = (
            "校园车位",
            "验证码登录；选择校内车位与时段占坑预约；入场由管理端登记。",
            "后勤主管（总管）",
        )
    else:
        brow, lead, admin = (
            "车位预约",
            "验证码登录；选择车位与时段占坑预约；入场由管理端登记。",
            "车场主管（总管）",
        )
    return slot_shell_schema(
        title,
        domain="DOM-PARKING",
        user_role_id="user",
        user_label="车主",
        admin_label=admin,
        subadmin_label="车场管理员",
        archive_key="space",
        archive_label="车位",
        archive_plural="车位",
        archive_fields=[
            {"key": "title", "label": "车位号", "type": "string"},
            {"key": "author", "label": "费用(元)", "type": "number", "format": "money"},
            {"key": "isbn", "label": "位置", "type": "string"},
            {"key": "feeRule", "label": "计费规则", "type": "string"},
            {"key": "category", "label": "分区", "type": "select"},
        ],
        archive_menu_admin="车位管理",
        archive_menu_user="选车位",
        users_menu="用户管理",
        my_resv_label="我的预约",
        resv_admin_label="预约记录",
        auth_eyebrow=brow,
        auth_lead=lead,
        auth_points=["验证码登录", "车位检索", "时段预约与入场登记"],
        register_hint="注册后可预约车位",
        notice_title="停车须知",
        notice_body="请按时入场；入场后由车场登记办结；取消预约将释放时段。请填写车牌号便于核对。",
        notice_page_title="车场公告",
        reserve_require_remark=True,
        reserve_remark_label="车牌号",
        complete_verb="登记入场",
        completed_label="已入场",
    )

def _salon_schema(title: str, proposal_text: str = "") -> dict[str, Any]:
    """美发 / 健身私教：同服务预约壳，文案跟题名/开题走（同 _meeting_schema）。"""
    t = _copy_scan_text(title, proposal_text)
    if any(k in t for k in ("健身", "私教", "瑜伽", "游泳私教", "器械课")):
        noun, staff, admin, user = "课程", "默认教练", "场馆主管（总管）", "会员"
        title_lab, brow, place, notice_page = "课程/私教项目", "健身预约", "到馆", "场馆公告"
        lead = "验证码登录；选择私教/团课与时段预约到馆；到馆后由前台登记完成。"
        points = ["验证码登录", "课程浏览", "时段预约与到馆办结"]
    else:
        noun, staff, admin, user = "服务", "默认技师", "门店主管（总管）", "顾客"
        title_lab, brow, place, notice_page = "服务项目", "服务预约", "到店", "门店公告"
        lead = "验证码登录；选择服务项目与时段预约到店；到店后由门店登记完成。"
        points = ["验证码登录", "服务浏览", "时段预约与到店办结"]
    return slot_shell_schema(
        title,
        domain="DOM-SALON",
        user_role_id="user",
        user_label=user,
        admin_label=admin,
        subadmin_label="预约管理员",
        archive_key="service",
        archive_label=noun,
        archive_plural=noun,
        archive_fields=[
            {"key": "title", "label": title_lab, "type": "string"},
            {"key": "author", "label": "价格(元)", "type": "number", "format": "money"},
            {"key": "isbn", "label": "时长说明", "type": "string"},
            {"key": "stylistName", "label": staff, "type": "string"},
            {"key": "category", "label": "分类", "type": "select"},
        ],
        archive_menu_admin=f"{noun}管理",
        archive_menu_user=f"选{noun}",
        users_menu=f"{user}管理",
        my_resv_label="我的预约",
        resv_admin_label="预约记录",
        auth_eyebrow=brow,
        auth_lead=lead,
        auth_points=points,
        register_hint=f"注册后可预约{noun}",
        notice_title="预约须知",
        notice_body=f"请准时{place}；{place}完成后由前台办结；改约请先取消原时段。",
        notice_page_title=notice_page,
        complete_verb=f"{place}完成",
        completed_label="已完成",
    )

def _hotel_schema(title: str) -> dict[str, Any]:
    return slot_shell_schema(
        title,
        domain="DOM-HOTEL",
        user_role_id="user",
        user_label="住客",
        admin_label="酒店主管（总管）",
        subadmin_label="前台",
        archive_key="room_type",
        archive_label="房型",
        archive_plural="房型",
        archive_fields=[
            {"key": "title", "label": "房型", "type": "string"},
            {"key": "author", "label": "房价(元)", "type": "number", "format": "money"},
            {"key": "isbn", "label": "说明", "type": "string"},
            {"key": "category", "label": "分类", "type": "select"},
            {"key": "stock", "label": "可售间数", "type": "number"},
        ],
        archive_menu_admin="房型管理",
        archive_menu_user="选房型",
        users_menu="住客管理",
        my_resv_label="我的预订",
        resv_admin_label="预订记录",
        resv_label="预订",
        auth_eyebrow="客房预订",
        auth_lead="验证码登录；选择房型与入住时段预订，同步生成订单；前台可办理入住/离店办结。",
        auth_points=["验证码登录", "房型浏览", "分时预订与入住离店"],
        register_hint="注册后可预订客房",
        notice_title="入住须知",
        notice_body="演示环境无真支付；预约成功即占坑并生成订单；入住/离店由前台办结。",
        notice_page_title="酒店公告",
        with_orders=True,
        complete_verb="入住/离店",
        completed_label="已离店",
    )

