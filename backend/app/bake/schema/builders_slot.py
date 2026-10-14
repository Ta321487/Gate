"""交易 / 预约类域 builder。"""

from __future__ import annotations

from typing import Any

from app.bake.schema.shells import (
    order_shell_schema,
    slot_shell_schema,
)

def _shop_schema(title: str, proposal_text: str = "") -> dict[str, Any]:
    """校园二手 / 行业货皮 / 社会零售：成色仅 campus；货名跟 scene seed。"""
    from app.bake.scene_scan import scan_shop_marketplace, shop_product_kind

    pk = shop_product_kind(title, proposal_text)
    marketplace = scan_shop_marketplace(title, proposal_text)
    campus = pk == "campus"
    niche = None
    pack = None
    if campus:
        brow, lead = (
            "校园商城",
            "验证码登录；浏览校园闲置、加入购物车并提交订单。",
        )
        notice_title = "商城须知"
        notice_body = "下单后由管理员确认发货或自提。"
        fields = [
            {"key": "title", "label": "商品名", "type": "string"},
            {"key": "author", "label": "单价(元)", "type": "number", "format": "money"},
            {"key": "isbn", "label": "货号", "type": "string"},
            {"key": "conditionGrade", "label": "成色", "type": "string"},
            {"key": "sellerNote", "label": "卖家备注", "type": "string"},
            {"key": "category", "label": "分类", "type": "select"},
            {"key": "stock", "label": "库存", "type": "number"},
        ]
    else:
        brow_map = {
            "farm": ("助农商城", "验证码登录；浏览水果蔬菜粮油，加入购物车并提交订单。"),
            "print": ("文印下单", "验证码登录；选打印装订服务下单。"),
            "flowers": ("花店商城", "验证码登录；浏览鲜花特产并下单配送。"),
            "errand": ("跑腿代买", "验证码登录；下单代买代取，由跑腿员接单送达。"),
            "points": ("积分兑换", "验证码登录；用积分兑换商品并提交订单。"),
        }
        from app.bake.scene_scan import shop_retail_niche
        from app.bake.shop_retail_niches import get_retail_niche

        niche = shop_retail_niche(title, proposal_text) if pk == "retail" else None
        pack = get_retail_niche(niche)
        if pack is not None:
            brow, lead = pack.eyebrow, pack.lead
            notice_title, notice_body = pack.notice_title, pack.notice_body
        else:
            brow, lead = brow_map.get(pk) or (
                "在线商城",
                "验证码登录；浏览商品、加入购物车并提交订单。",
            )
            notice_body = {
                "farm": "水果蔬菜粮油分类上架，下单后由管理员确认发货或自提。",
                "print": "下单后到店取件或约定配送。",
                "flowers": "下单后由店员确认配送。",
                "errand": "代买代取由跑腿员接单送达；请填写送达地点与联系方式。",
                "points": "兑换下单后由管理员确认发放。",
            }.get(pk, "下单后由管理员确认发货或自提。")
            notice_title = {
                "farm": "农产选购须知",
                "print": "文印须知",
                "flowers": "花店须知",
                "errand": "跑腿须知",
                "points": "积分兑换须知",
            }.get(pk, "商城须知")
        if pk == "farm":
            # 农产开题常见：产地/采摘时间/规格/价格/简介/图片（封面）；
            # 物理列仍走 author→price_yuan、isbn→sku；region/harvest_on 仅 farm 注入。
            fields = [
                {"key": "title", "label": "农产品名称", "type": "string"},
                {"key": "author", "label": "价格", "type": "number", "format": "money"},
                {"key": "isbn", "label": "规格", "type": "string"},
                {"key": "region", "label": "产地", "type": "string"},
                # 产品属性日：默认 date；开题强调时分时由 temporal_field 升 datetime
                {"key": "harvestOn", "label": "采摘时间", "type": "date"},
                {"key": "sellerNote", "label": "简介", "type": "textarea"},
                {"key": "category", "label": "分类", "type": "select"},
                {"key": "stock", "label": "库存", "type": "number"},
            ]
        elif pk == "print":
            fields = [
                {"key": "title", "label": "服务项目", "type": "string"},
                {"key": "author", "label": "单价(元)", "type": "number", "format": "money"},
                {"key": "isbn", "label": "装订规格", "type": "string"},
                {"key": "sellerNote", "label": "工艺说明", "type": "textarea"},
                {"key": "category", "label": "分类", "type": "select"},
                {"key": "stock", "label": "可接单量", "type": "number"},
            ]
        elif pk == "flowers":
            fields = [
                {"key": "title", "label": "花材名称", "type": "string"},
                {"key": "author", "label": "单价(元)", "type": "number", "format": "money"},
                {"key": "isbn", "label": "花束规格", "type": "string"},
                {"key": "sellerNote", "label": "配送说明", "type": "textarea"},
                {"key": "category", "label": "分类", "type": "select"},
                {"key": "stock", "label": "库存", "type": "number"},
            ]
        elif pk == "errand":
            fields = [
                {"key": "title", "label": "代买项目", "type": "string"},
                {"key": "author", "label": "服务费(元)", "type": "number", "format": "money"},
                {"key": "isbn", "label": "服务范围", "type": "string"},
                {"key": "sellerNote", "label": "代买说明", "type": "textarea"},
                {"key": "category", "label": "分类", "type": "select"},
                {"key": "stock", "label": "可接单", "type": "number"},
            ]
        elif pk == "points":
            fields = [
                {"key": "title", "label": "兑换商品", "type": "string"},
                {"key": "author", "label": "积分价", "type": "number"},
                {"key": "isbn", "label": "兑换货号", "type": "string"},
                {"key": "sellerNote", "label": "兑换说明", "type": "textarea"},
                {"key": "category", "label": "分类", "type": "select"},
                {"key": "stock", "label": "库存", "type": "number"},
            ]
        else:
            # retail / 默认：标签来自登记表 pack
            if pack is not None:
                title_lab, sku_lab, note_lab = pack.title_lab, pack.sku_lab, pack.note_lab
            else:
                title_lab, sku_lab, note_lab = "商品名", "货号", "商品说明"
            fields = [
                {"key": "title", "label": title_lab, "type": "string"},
                {"key": "author", "label": "单价(元)", "type": "number", "format": "money"},
                {"key": "isbn", "label": sku_lab, "type": "string"},
                {"key": "sellerNote", "label": note_lab, "type": "string"},
                {"key": "category", "label": "分类", "type": "select"},
                {"key": "stock", "label": "库存", "type": "number"},
            ]
    sub_lab = "商家" if marketplace else ("店员" if pk == "farm" else "订单管理员")
    admin_lab = (
        "平台管理员（总管）"
        if marketplace
        else ("农产主管（总管）" if pk == "farm" else "商城主管（总管）")
    )
    arch_menu = "农产品管理" if pk == "farm" else "商品管理"
    arch_browse = "农产品浏览" if pk == "farm" else "商品浏览"
    arch_lab = "农产品" if pk == "farm" else "商品"
    if pack is not None:
        arch_menu, arch_browse, arch_lab = pack.arch_menu, pack.arch_browse, pack.arch_lab
        if not marketplace:
            admin_lab = pack.admin_lab
            sub_lab = pack.sub_name
    if marketplace:
        if pk == "farm":
            brow = "多商家助农商城"
            lead = (
                "买家选购下单，商家入驻开店，平台统一监管；"
                "平台管理员为系统预制账号，不开放自助注册。"
            )
        elif pack is not None:
            brow, lead = pack.mp_eyebrow, pack.mp_lead
        else:
            brow = "多商家商城"
            lead = (
                "买家选购下单，商家入驻开店，平台统一监管；"
                "平台管理员为系统预制账号，不开放自助注册。"
            )
    schema = order_shell_schema(
        title,
        domain="DOM-SHOP",
        user_role_id="user",
        user_label="买家",
        admin_label=admin_lab,
        subadmin_label=sub_lab,
        archive_key="product",
        archive_label=arch_lab,
        archive_plural=arch_lab,
        archive_fields=fields,
        archive_menu_admin=arch_menu,
        archive_menu_user=arch_browse,
        users_menu="用户管理",
        cart_label="购物车",
        my_orders_label="我的订单",
        orders_admin_label="订单管理",
        auth_eyebrow=brow,
        auth_lead=lead,
        auth_points=["验证码登录", "商品浏览", "购物车与订单"],
        register_hint="注册后可购物下单",
        notice_title=notice_title,
        notice_body=notice_body,
        notice_page_title="商城公告" if pk != "farm" else "农产公告",
        # 域默认：商品上下架（软删可恢复）；开题未写也做，勿当扫词才挂
        soft_delete=True,
    )
    if marketplace:
        schema["shopMarketplace"] = True
        hint = (
            "仅开放买家与商家注册；平台管理员不开放自助注册。"
            "商家须平台审核通过后方可登录店铺后台。"
        )
        schema["registerHint"] = hint
        labels = schema.setdefault("labels", {})
        labels["registerHint"] = hint
        labels["registerRoleHint"] = hint
        labels["authLead"] = lead
        labels["authPoints"] = [
            "用户 / 商家 / 管理三端",
            "买家购物 · 商家入驻",
            "管理端仅登录（无注册）",
        ]
        # 对照老师模块名：活动≈公告、数据分析≈工作台、分类/商品皮；售后挂订单管理
        if pk == "farm":
            cat_lab = "农产品分类"
        elif pack is not None:
            cat_lab = pack.cat_menu_lab
        else:
            cat_lab = "商品分类"
        for m in (schema.get("menus") or {}).get("admin") or []:
            if not isinstance(m, dict):
                continue
            k = m.get("key")
            if k == "dashboard":
                m["label"] = "数据分析"
            elif k == "content":
                m["label"] = "活动管理"
            elif k == "guestbook":
                m["label"] = "留言反馈"
            elif k == "category":
                m["label"] = cat_lab
            elif k == "archive" and pack is not None:
                m["label"] = pack.arch_menu
            elif k == "users":
                m["label"] = "用户管理"
            elif k == "orders":
                m["label"] = "订单管理"
            # 商家可管自家商品、留言、订单、评价、活动送审；用户/分类仍超管
            if k in ("archive", "guestbook", "orders", "order_reviews", "content"):
                m["superOnly"] = False
        for m in (schema.get("menus") or {}).get("user") or []:
            if isinstance(m, dict) and m.get("key") == "archive" and pack is not None:
                m["label"] = pack.arch_browse
        for m in (schema.get("menus") or {}).get("user") or []:
            if not isinstance(m, dict):
                continue
            k = m.get("key")
            if k == "content":
                m["label"] = "活动"
            elif k == "guestbook":
                m["label"] = "留言反馈"
            elif k == "profile":
                m["label"] = "个人中心"
            elif k == "my_orders":
                m["label"] = "我的订单"
        labels["noticePageTitle"] = "活动公告" if pk != "farm" else "农产活动"
        labels["guestbookPageTitle"] = "留言反馈"
        labels["guestbookPageLead"] = "有问题可向平台留言，我们会尽快回复。"
        labels["guestbookGuestCta"] = "登录后发表留言"
        labels["noticeGuestCta"] = "登录后查看更多活动"
        labels["messagesPageLead"] = "新订单、售后与系统通知。"
        labels["orderReviewPageTitle"] = "我的评价"
        labels["orderReviewPageLead"] = "对已完成订单进行星级与文字评价。"
        labels["usersAdminLead"] = "管理买家账号，审核商家入驻申请。"
        labels["ordersAdminLead"] = "处理发货、物流与售后申请。"
        labels["demoPayHint"] = "选择支付宝或微信，确认后从账户余额扣款。"
        labels["stockWarnHint"] = "库存低于预警值时高亮提示商家补货。"
        schema["demoPay"] = True
        schema["stockWarnBelow"] = 10
        # 对照老师订单态：在现有状态机上扩展运输中/已签收
        ent = (schema.get("entities") or {}).get("order")
        if isinstance(ent, dict):
            ent["states"] = {
                "pending": "待付款",
                "confirmed": "待发货",
                "shipped": "已发货",
                "in_transit": "运输中",
                "signed": "已签收",
                "completed": "已完成",
                "cancelled": "已取消",
            }
        # 多店默认会再扫入 dm/favorites/order_review；此处先占位文案，菜单由 attach_accept 收束
    return schema


def _food_schema(title: str, proposal_text: str = "") -> dict[str, Any]:
    """食堂 vs 社会餐饮：只分两档，不按菜系开皮。"""
    from app.bake.scene_scan import food_product_kind

    canteen = food_product_kind(title, proposal_text) == "canteen"
    if canteen:
        admin, sub, brow, win, notice = "食堂主管（总管）", "档口管理员", "食堂点餐", "窗口", "食堂公告"
        body = "下单后到对应窗口取餐或按约定配送。"
    else:
        admin, sub, brow, win, notice = "门店主管（总管）", "店员", "点餐外卖", "门店", "门店公告"
        body = "支持堂食、自取或外卖配送。"
    schema = order_shell_schema(
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
        auth_lead="验证码登录；选菜加入清单并下单。",
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
        soft_delete=True,
    )
    schema["entities"]["order"]["verbs"] = {
        "confirm": "接单",
        "ship": "出餐",
        "complete": "完成",
        "cancel": "取消",
    }
    labels = dict(schema.get("labels") or {})
    labels["orderFulfillColumnLabel"] = "配送"
    labels["orderShipFieldLabel"] = "取餐码"
    schema["labels"] = labels
    return schema


def _cinema_schema(title: str, proposal_text: str = "") -> dict[str, Any]:
    """影院选座购票：场次档案 + 订单壳；座位图由 seat_select 能力叠菜单。"""
    from app.bake.schema.shells import _with_portal_banners

    schema = _with_portal_banners(
        order_shell_schema(
            title,
            domain="DOM-CINEMA",
            user_role_id="user",
            user_label="观影者",
            admin_label="影院主管（总管）",
            subadmin_label="售票员",
            archive_key="cinema_show",
            archive_label="场次",
            archive_plural="场次",
            archive_fields=[
                {"key": "title", "label": "影片/场次名", "type": "string"},
                {"key": "author", "label": "价格", "type": "number", "format": "money"},
                {"key": "isbn", "label": "影厅名称", "type": "string"},
                {"key": "category", "label": "影厅类型", "type": "select"},
                {"key": "startAt", "label": "开场时间", "type": "datetime"},
                {"key": "seatRows", "label": "座位排数", "type": "number"},
                {"key": "seatCols", "label": "每排座位数", "type": "number"},
                {"key": "stock", "label": "余座", "type": "number"},
            ],
            archive_menu_admin="场次管理",
            archive_menu_user="场次目录",
            users_menu="用户管理",
            cart_label="购物车",
            my_orders_label="我的影票订单",
            orders_admin_label="订单管理",
            auth_eyebrow="影院选座",
            auth_lead="验证码登录；选择场次进入座位图，确认后生成订单并占座。",
            auth_points=["验证码登录", "场次选座", "影票订单"],
            register_hint="注册后可选座购票",
            notice_title="选座购票须知",
            notice_body="场次含影厅类型、开场时间与座位排×列；选座确认后即时占座并生成订单；过开场时间自动下架不可售。",
            notice_page_title="影院公告",
            order_states={
                "pending": "待取票",
                "confirmed": "已确认",
                "shipped": "已出票",
                "completed": "已观影",
                "cancelled": "已取消",
            },
        ),
        [
            {"title": "热映场次", "lead": "浏览今日场次与余座。"},
            {"title": "座位图选座", "lead": "点选空闲座位后确认下单。"},
            {"title": "我的订单", "lead": "查看影票订单与座位备注。"},
            {"title": "影院公告", "lead": "排片与维护通知见公告栏。"},
            {"title": "使用说明", "lead": "选座确认后生成订单；柜台取票观影。"},
        ],
    )
    # 选座订单禁止商城「物流/发货」叙事（对齐 HOTEL stay）
    order = dict((schema.get("entities") or {}).get("order") or {})
    order.update(
        {
            "key": "order",
            "label": "订单",
            "labelPlural": "我的影票订单",
            "fulfillMode": "cinema",
            "states": {
                "pending": "待取票",
                "confirmed": "已确认",
                "shipped": "已出票",
                "completed": "已观影",
                "cancelled": "已取消",
            },
            "verbs": {
                "ship": "出票",
                "complete": "确认观影",
            },
        }
    )
    ents = dict(schema.get("entities") or {})
    ents["order"] = order
    schema["entities"] = ents
    labels = dict(schema.get("labels") or {})
    labels["orderFulfillHint"] = "选座确认后生成订单并占座；柜台出票/确认观影，无物流发货。"
    labels["orderShipFieldLabel"] = "影票凭证"
    labels["orderFulfillColumnLabel"] = "选座备注"
    schema["labels"] = labels
    return schema


def _meeting_schema(title: str, proposal_text: str = "") -> dict[str, Any]:
    """会议室 / 琴房 / 体育场 / 自习室 / 座位等共用时段预约壳，文案跟题名/开题走。"""
    from app.bake.scene_scan import meeting_product_kind
    from app.bake.schema.kind_label_packs import meeting_label_pack

    p = meeting_label_pack(meeting_product_kind(title, proposal_text))
    noun, remark, admin, sub = p["noun"], p["remark"], p["admin"], p["sub"]
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
    """门诊 / 疫苗接种 / 宠物医院：同号源预约壳；宠物走 scene_hospital=adopt。"""
    from app.bake.scene_scan import hospital_product_kind
    from app.bake.schema.kind_label_packs import hospital_label_pack

    kind = hospital_product_kind(title, proposal_text)
    p = hospital_label_pack(kind)
    noun, remark, admin, sub = p["noun"], p["remark"], p["admin"], p["sub"]
    user, brow, resv = p["user"], p["eyebrow"], p["resv"]
    fee, isbn, cat, title_lab = p["fee"], p["isbn"], p["cat"], p["title_lab"]
    lead, notice = p["lead"], p["notice"]
    notice_t, notice_page, reg, done = (
        p["notice_t"],
        p["notice_page"],
        p["reg"],
        p["done"],
    )
    menu_u, points_mid = p["menu_u"], p["points_mid"]
    if kind == "window":
        visit_lab, symptom_lab = "业务类型", "办事说明"
        visit_opts = [
            {"label": "初办", "value": "初办"},
            {"label": "续办", "value": "续办"},
            {"label": "咨询", "value": "咨询"},
        ]
        default_visit = "初办"
    elif kind == "visit":
        visit_lab, symptom_lab = "探视类型", "探视说明"
        visit_opts = [
            {"label": "普通探视", "value": "普通探视"},
            {"label": "陪护", "value": "陪护"},
            {"label": "日间探访", "value": "日间探访"},
        ]
        default_visit = "普通探视"
    elif kind == "vaccine":
        visit_lab, symptom_lab = "针次", "接种备注"
        visit_opts = [
            {"label": "首针", "value": "首针"},
            {"label": "第二针", "value": "第二针"},
            {"label": "第三针", "value": "第三针"},
            {"label": "加强针", "value": "加强针"},
        ]
        default_visit = "首针"
    elif kind == "pet":
        visit_lab, symptom_lab = "初诊/复诊", "病情简述"
        visit_opts = [
            {"label": "初诊", "value": "初诊"},
            {"label": "复诊", "value": "复诊"},
        ]
        default_visit = "初诊"
    else:
        visit_lab, symptom_lab = "初诊/复诊", "症状简述"
        visit_opts = [
            {"label": "初诊", "value": "初诊"},
            {"label": "复诊", "value": "复诊"},
        ]
        default_visit = "初诊"
    schema = slot_shell_schema(
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
        allow_rating=True,
    )
    resv_ent = schema["entities"]["reservation"]
    resv_ent["patientNameLabel"] = remark
    resv_ent["visitTypeLabel"] = visit_lab
    resv_ent["visitTypeOptions"] = visit_opts
    resv_ent["visitTypeDefault"] = default_visit
    resv_ent["symptomNoteLabel"] = symptom_lab
    return schema

def _parking_schema(title: str, proposal_text: str = "") -> dict[str, Any]:
    """车位：校园 vs 商场/小区车场（同 _food_schema 分支）。"""
    from app.bake.scene_scan import parking_product_kind, scene_parking_parts

    charge = parking_product_kind(title, proposal_text) == "charge"
    campus = scene_parking_parts(title, proposal_text) == "campus"
    if charge:
        brow, lead, admin = (
            "充电预约",
            "验证码登录；选择充电桩与时段占坑预约；入位由管理端登记。",
            "充电站主管（总管）",
        )
        archive_lab, title_lab, fee_lab, loc_lab = "充电桩", "桩位号", "电费参考(元)", "功率/位置"
        menu_u, points_mid, reg = "选充电桩", "桩位检索", "注册后可预约充电"
        notice = "预约成功后请按时入位充电；取消后释放桩位时段。"
        notice_t = "充电预约"
    elif campus:
        brow, lead, admin = (
            "校园车位",
            "验证码登录；选择校内车位与时段占坑预约；入场由管理端登记。",
            "后勤主管（总管）",
        )
        archive_lab, title_lab, fee_lab, loc_lab = "车位", "车位号", "费用(元)", "位置"
        menu_u, points_mid, reg = "选车位", "车位检索", "注册后可预约车位"
        notice = "预约成功后请按时入场；取消后释放车位时段。"
        notice_t = "校园车位预约"
    else:
        brow, lead, admin = (
            "车位预约",
            "验证码登录；选择车位与时段占坑预约；入场由管理端登记。",
            "车场主管（总管）",
        )
        archive_lab, title_lab, fee_lab, loc_lab = "车位", "车位号", "费用(元)", "位置"
        menu_u, points_mid, reg = "选车位", "车位检索", "注册后可预约车位"
        notice = "预约成功后请按时入场；取消后释放车位时段。"
        notice_t = "车位预约"
    return slot_shell_schema(
        title,
        domain="DOM-PARKING",
        user_role_id="user",
        user_label="车主",
        admin_label=admin,
        subadmin_label="预约管理员",
        archive_key="space",
        archive_label=archive_lab,
        archive_plural=archive_lab,
        archive_fields=[
            {"key": "title", "label": title_lab, "type": "string"},
            {"key": "author", "label": fee_lab, "type": "number", "format": "money"},
            {"key": "isbn", "label": loc_lab, "type": "string"},
            {"key": "feeRule", "label": "计费规则", "type": "string"},
            {"key": "category", "label": "分区", "type": "select"},
        ],
        archive_menu_admin=f"{archive_lab}管理",
        archive_menu_user=menu_u,
        users_menu="用户管理",
        my_resv_label="我的预约",
        resv_admin_label="预约记录",
        auth_eyebrow=brow,
        auth_lead=lead,
        auth_points=["验证码登录", points_mid, "时段预约与入场登记"],
        register_hint=reg,
        notice_title=notice_t,
        notice_body=notice + "请填写车牌号便于核对。",
        notice_page_title="车场公告",
        reserve_require_remark=True,
        reserve_remark_label="车牌号",
        complete_verb="登记入场",
        completed_label="已入场",
    )

def _salon_schema(title: str, proposal_text: str = "") -> dict[str, Any]:
    """美发 / 健身私教：同服务预约壳，文案跟题名/开题走（同 _meeting_schema）。"""
    from app.bake.scene_scan import salon_product_kind
    from app.bake.schema.kind_label_packs import salon_label_pack

    kind = salon_product_kind(title, proposal_text)
    p = salon_label_pack(kind)
    noun, staff, admin, user = p["noun"], p["staff"], p["admin"], p["user"]
    title_lab, brow, place, notice_page = (
        p["title_lab"],
        p["eyebrow"],
        p["place"],
        p["notice_page"],
    )
    lead, points = p["lead"], list(p["points"])
    schema = slot_shell_schema(
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
        allow_rating=True,
    )
    schema["entities"]["reservation"]["stylistLabel"] = p["stylist_label"]
    return schema

def _carrent_schema(title: str, proposal_text: str = "") -> dict[str, Any]:
    schema = slot_shell_schema(
        title,
        domain="DOM-CARRENT",
        user_role_id="user",
        user_label="租车人",
        admin_label="门店主管（总管）",
        subadmin_label="门店店员",
        archive_key="vehicle",
        archive_label="车型",
        archive_plural="车型",
        archive_fields=[
            {"key": "title", "label": "车型", "type": "string"},
            {"key": "author", "label": "日租金(元)", "type": "number", "format": "money"},
            {"key": "isbn", "label": "说明", "type": "string"},
            {"key": "category", "label": "分类", "type": "select"},
            {"key": "stock", "label": "可租辆数", "type": "number"},
        ],
        archive_menu_admin="车型管理",
        archive_menu_user="选车型",
        users_menu="租车人管理",
        my_resv_label="我的租约",
        resv_admin_label="租约记录",
        resv_label="租约",
        auth_eyebrow="汽车租赁",
        auth_lead="验证码登录；选择车型与租期下单，同步生成订单；门店办理取车/还车办结。",
        auth_points=["验证码登录", "车型浏览", "按日租期与取还车"],
        register_hint="注册后可在线租车",
        notice_title="租车须知",
        notice_body="下单成功即占车并生成订单；取车与还车由门店办结。",
        notice_page_title="租车公告",
        with_orders=True,
        complete_verb="取车/还车",
        completed_label="已还车",
        allow_rating=True,
    )
    order = dict((schema.get("entities") or {}).get("order") or {})
    order.update(
        {
            "key": "order",
            "label": "订单",
            "labelPlural": "我的订单",
            "fulfillMode": "rental",
            "states": {
                "pending": "待确认",
                "confirmed": "待取车",
                "shipped": "租赁中",
                "completed": "已还车",
                "cancelled": "已取消",
            },
            "verbs": {
                "ship": "办理取车",
                "complete": "办理还车",
            },
        }
    )
    ents = dict(schema.get("entities") or {})
    ents["order"] = order
    schema["entities"] = ents
    labels = dict(schema.get("labels") or {})
    labels["orderFulfillHint"] = "租车订单随租约生成；门店办理取车/还车，无物流发货。"
    schema["labels"] = labels
    resv_ent = schema["entities"]["reservation"]
    resv_ent["guestNameLabel"] = "驾驶人"
    resv_ent["guestCountLabel"] = "用车人数"
    return schema


def _hotel_schema(title: str, proposal_text: str = "") -> dict[str, Any]:
    from app.bake.scene_scan import hotel_product_kind

    homestay = hotel_product_kind(title, proposal_text) == "homestay"
    if homestay:
        brow, admin, notice_t, notice_page = (
            "民宿预订",
            "民宿老板（总管）",
            "入住须知",
            "民宿公告",
        )
        lead = "验证码登录；选择民宿房型与入住时段预订，同步生成订单；前台可办理入住/离店办结。"
        reg = "注册后可预订民宿客房"
    else:
        brow, admin, notice_t, notice_page = (
            "客房预约",
            "酒店主管（总管）",
            "入住须知",
            "酒店公告",
        )
        lead = "验证码登录；选择房型与入住时段预订，同步生成订单；前台可办理入住/离店办结。"
        reg = "注册后可预订客房"
    schema = slot_shell_schema(
        title,
        domain="DOM-HOTEL",
        user_role_id="user",
        user_label="住客",
        admin_label=admin,
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
        auth_eyebrow=brow,
        auth_lead=lead,
        auth_points=["验证码登录", "房型浏览", "分时预订与入住离店"],
        register_hint=reg,
        notice_title=notice_t,
        notice_body="预约成功即占坑并生成订单；入住/离店由前台办结。",
        notice_page_title=notice_page,
        with_orders=True,
        complete_verb="入住/离店",
        completed_label="已离店",
        allow_rating=True,
    )
    # 订单跟入住离店，禁止复用商城「物流/发货」叙事
    order = dict((schema.get("entities") or {}).get("order") or {})
    order.update(
        {
            "key": "order",
            "label": "订单",
            "labelPlural": "我的订单",
            "fulfillMode": "stay",
            "states": {
                "pending": "待确认",
                "confirmed": "已确认",
                "shipped": "已入住",
                "completed": "已离店",
                "cancelled": "已取消",
            },
            "verbs": {
                "ship": "办理入住",
                "complete": "办理离店",
            },
        }
    )
    ents = dict(schema.get("entities") or {})
    ents["order"] = order
    schema["entities"] = ents
    labels = dict(schema.get("labels") or {})
    labels["orderFulfillHint"] = "客房订单随预订生成；前台办理入住/离店，无物流发货。"
    schema["labels"] = labels
    resv_ent = schema["entities"]["reservation"]
    resv_ent["guestNameLabel"] = "入住人"
    resv_ent["guestCountLabel"] = "入住人数"
    if hotel_product_kind(title, proposal_text) == "boarding":
        for field in (schema["entities"].get("archive") or {}).get("fields") or []:
            if field.get("key") == "title":
                field["label"] = "寄养位"
            elif field.get("key") == "author":
                field["label"] = "日价(元)"
            elif field.get("key") == "stock":
                field["label"] = "可寄养数"
        resv_ent["guestNameLabel"] = "宠物名"
        labels["orderFulfillHint"] = "金额按日价乘以天数。前台办理入住和离店。"
        schema["labels"] = labels
    return schema

