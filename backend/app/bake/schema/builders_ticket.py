"""独立工单域 builder（宿舍/物业/IT）。"""

from __future__ import annotations

from typing import Any

from app.bake.schema.shells import standalone_ticket_schema

def _dorm_schema(title: str) -> dict[str, Any]:
    return standalone_ticket_schema(
        title,
        domain="DOM-DORM",
        user_role_id="student",
        user_label="学生",
        admin_label="宿管（总管）",
        subadmin_label="楼管",
        ticket_key="repair",
        ticket_label="报修单",
        ticket_plural="报修",
        verbs={
            "apply": "提交报修",
            "approve": "受理",
            "reject": "驳回",
            "return": "完成",
        },
        states={
            "pending": "待受理",
            "approved": "处理中",
            "rejected": "已驳回",
            "returned": "已完成",
        },
        site_menu="楼栋房间",
        type_menu="报修类型",
        users_menu="学生管理",
        auth_eyebrow="宿舍服务",
        auth_lead="验证码登录；学生可提交报修，宿管受理跟进。",
        auth_points=["验证码登录", "报修申请", "受理进度"],
        register_hint="注册后以学生身份提交报修",
        notice_title="报修须知",
        notice_body="请如实填写宿舍与故障描述并上传现场照片，宿管将尽快受理。",
        notice_page_title="宿舍公告",
        notice_page_lead="报修须知、宿舍安排与临时通知，点击条目阅读全文。",
        two_level_approve=True,
        require_attach=True,
        allow_rating=True,
    )

def _property_schema(title: str, proposal_text: str = "") -> dict[str, Any]:
    """物业报修默认；投诉 / 市政深皮；校园公寓走 campus。"""
    from app.bake.scene_scan import property_product_kind, scene_for

    kind = property_product_kind(title, proposal_text)
    campus = scene_for("DOM-PROPERTY", title, proposal_text) == "campus"

    if kind == "municipal":
        return standalone_ticket_schema(
            title,
            domain="DOM-PROPERTY",
            user_role_id="user",
            user_label="市民",
            admin_label="市政主管",
            subadmin_label="巡查员",
            ticket_key="repair",
            ticket_label="报修单",
            ticket_plural="市政报修",
            verbs={
                "apply": "提交报修",
                "approve": "受理",
                "reject": "驳回",
                "return": "完成",
            },
            states={
                "pending": "待受理",
                "approved": "处理中",
                "rejected": "已驳回",
                "returned": "已完成",
            },
            site_menu="片区路段",
            type_menu="设施类型",
            users_menu="用户管理",
            auth_eyebrow="市政报修",
            auth_lead="验证码登录；市民上报路灯/井盖等市政设施问题，巡查员受理办结。",
            auth_points=["验证码登录", "市政报修", "受理进度"],
            register_hint="注册后可上报市政设施问题",
            notice_title="报修须知",
            notice_body="请写明片区路段与设施位置并上传现场照片，市政将尽快受理。",
            notice_page_title="市政公告",
            notice_page_lead="市政报修须知与临时通知，点击条目阅读全文。",
            my_tickets_label="我的报修",
            pending_label="报修受理",
            records_label="报修记录",
            two_level_approve=True,
            require_attach=True,
            allow_rating=True,
        )

    complaint = kind == "complaint"
    verb_apply = "提交投诉" if complaint else "提交报修"
    ticket_lab = "投诉单" if complaint else "报修单"
    ticket_pl = "投诉" if complaint else "报修"
    type_menu = "工单类型" if complaint else "报修类型"
    notice_t = "投诉须知" if complaint else "报修须知"
    notice_b = (
        "请如实填写地址与诉求描述；投诉与报修共用受理完结流程。"
        if complaint
        else "请如实填写地址与故障描述并上传现场照片，物业将尽快受理。"
    )
    site_menu = "楼栋单元" if complaint else "楼栋房间"

    if campus:
        return standalone_ticket_schema(
            title,
            domain="DOM-PROPERTY",
            user_role_id="user",
            user_label="师生",
            admin_label="物业主管",
            subadmin_label="物业调度",
            ticket_key="repair",
            ticket_label=ticket_lab,
            ticket_plural=ticket_pl,
            verbs={
                "apply": verb_apply,
                "approve": "受理",
                "reject": "驳回",
                "return": "完成",
            },
            states={
                "pending": "待受理",
                "approved": "处理中",
                "rejected": "已驳回",
                "returned": "已完成",
            },
            site_menu=site_menu,
            type_menu=type_menu,
            users_menu="用户管理",
            auth_eyebrow="校园投诉" if complaint else "校园物业",
            auth_lead=(
                "验证码登录；师生提交投诉建议，物业受理办结。"
                if complaint
                else "验证码登录；师生提交公寓/公共设施报修，物业受理跟进。"
            ),
            auth_points=["验证码登录", verb_apply, "受理进度"],
            register_hint="注册后可提交投诉建议" if complaint else "注册后可提交校园报修",
            notice_title=notice_t,
            notice_body=(
                notice_b
                if complaint
                else "请如实填写楼栋房号与故障描述并上传现场照片，物业将尽快受理。"
            ),
            notice_page_title="物业公告",
            notice_page_lead="报修/投诉须知、公寓安排与临时通知，点击条目阅读全文。",
            my_tickets_label="我的投诉" if complaint else "我的报修",
            pending_label="投诉受理" if complaint else "报修受理",
            records_label="投诉记录" if complaint else "报修记录",
            two_level_approve=True,
            require_attach=True,
            allow_rating=True,
        )
    return standalone_ticket_schema(
        title,
        domain="DOM-PROPERTY",
        user_role_id="user",
        user_label="业主" if complaint else "住户",
        admin_label="物业主管",
        subadmin_label="物业调度",
        ticket_key="repair",
        ticket_label=ticket_lab,
        ticket_plural=ticket_pl,
        verbs={
            "apply": verb_apply,
            "approve": "受理",
            "reject": "驳回",
            "return": "完成",
        },
        states={
            "pending": "待受理",
            "approved": "处理中",
            "rejected": "已驳回",
            "returned": "已完成",
        },
        site_menu=site_menu,
        type_menu=type_menu,
        users_menu="用户管理",
        auth_eyebrow="投诉建议" if complaint else "物业报修",
        auth_lead=(
            "验证码登录；住户提交投诉建议，物业受理办结。"
            if complaint
            else "验证码登录；住户提交报修，物业受理跟进。"
        ),
        auth_points=["验证码登录", verb_apply, "受理进度"],
        register_hint="注册后可提交投诉建议" if complaint else "注册后以住户身份提交报修",
        notice_title=notice_t,
        notice_body=notice_b,
        notice_page_title="物业公告",
        notice_page_lead="报修/投诉须知、社区安排与临时通知，点击条目阅读全文。",
        my_tickets_label="我的投诉" if complaint else "我的报修",
        pending_label="投诉受理" if complaint else "报修受理",
        records_label="投诉记录" if complaint else "报修记录",
        two_level_approve=True,
        require_attach=True,
        allow_rating=True,
    )

def _it_schema(title: str, proposal_text: str = "") -> dict[str, Any]:
    """故障报修默认；售后 / 维保深皮；企业运维走 enterprise。"""
    from app.bake.scene_scan import it_product_kind, scene_for

    kind = it_product_kind(title, proposal_text)
    enterprise = scene_for("DOM-IT", title, proposal_text) == "enterprise"

    if kind == "aftersales":
        return standalone_ticket_schema(
            title,
            domain="DOM-IT",
            user_role_id="user",
            user_label="客户",
            admin_label="客服主管",
            subadmin_label="客服专员",
            ticket_key="ticket",
            ticket_label="售后单",
            ticket_plural="售后",
            verbs={
                "apply": "提交售后",
                "approve": "受理",
                "reject": "驳回",
                "return": "完成",
            },
            states={
                "pending": "待受理",
                "approved": "处理中",
                "rejected": "已驳回",
                "returned": "已完成",
            },
            site_menu="服务网点",
            type_menu="售后类型",
            users_menu="用户管理",
            auth_eyebrow="客服售后",
            auth_lead="验证码登录；客户提交售后诉求，客服受理办结。",
            auth_points=["验证码登录", "售后申请", "受理进度"],
            register_hint="注册后可提交售后工单",
            notice_title="售后须知",
            notice_body="请写明网点、商品/服务与问题描述并上传凭证，客服将尽快受理。",
            notice_page_title="客服公告",
            notice_page_lead="售后须知与临时通知，点击条目阅读全文。",
            my_tickets_label="我的售后",
            pending_label="售后受理",
            records_label="售后记录",
            two_level_approve=True,
            require_attach=True,
            allow_rating=True,
        )

    if kind == "maintenance":
        return standalone_ticket_schema(
            title,
            domain="DOM-IT",
            user_role_id="user",
            user_label="报修人",
            admin_label="维保主管",
            subadmin_label="维保员",
            ticket_key="ticket",
            ticket_label="维保单",
            ticket_plural="维保",
            verbs={
                "apply": "提交维保",
                "approve": "受理",
                "reject": "驳回",
                "return": "完成",
            },
            states={
                "pending": "待受理",
                "approved": "处理中",
                "rejected": "已驳回",
                "returned": "已完成",
            },
            site_menu="设备区域",
            type_menu="维保类型",
            users_menu="用户管理",
            auth_eyebrow="设备维保",
            auth_lead="验证码登录；提交设备维保申请，维保员受理办结。",
            auth_points=["验证码登录", "维保申请", "受理进度"],
            register_hint="注册后可提交维保工单",
            notice_title="维保须知",
            notice_body="请写明设备区域、资产编号与故障现象并上传照片，维保将尽快受理。",
            notice_page_title="维保公告",
            notice_page_lead="维保须知与临时通知，点击条目阅读全文。",
            my_tickets_label="我的维保",
            pending_label="维保受理",
            records_label="维保记录",
            two_level_approve=True,
            require_attach=True,
            allow_rating=True,
        )

    if enterprise:
        return standalone_ticket_schema(
            title,
            domain="DOM-IT",
            user_role_id="user",
            user_label="员工",
            admin_label="运维主管",
            subadmin_label="运维员",
            ticket_key="ticket",
            ticket_label="故障单",
            ticket_plural="故障报修",
            verbs={
                "apply": "提交故障",
                "approve": "受理",
                "reject": "驳回",
                "return": "完成",
            },
            states={
                "pending": "待受理",
                "approved": "处理中",
                "rejected": "已驳回",
                "returned": "已完成",
            },
            site_menu="区域终端",
            type_menu="故障类型",
            users_menu="用户管理",
            auth_eyebrow="企业运维",
            auth_lead="验证码登录；员工提交故障，运维受理跟进。",
            auth_points=["验证码登录", "故障报修", "受理进度"],
            register_hint="注册后可提交故障报修",
            notice_title="报修须知",
            notice_body="请写明区域、终端与故障现象并上传截图/照片，运维将尽快受理。",
            notice_page_title="运维公告",
            notice_page_lead="故障处理须知与临时通知，点击条目阅读全文。",
            my_tickets_label="我的故障",
            pending_label="故障受理",
            records_label="报修记录",
            two_level_approve=True,
            require_attach=True,
            allow_rating=True,
        )
    return standalone_ticket_schema(
        title,
        domain="DOM-IT",
        user_role_id="user",
        user_label="师生",
        admin_label="运维主管",
        subadmin_label="运维员",
        ticket_key="ticket",
        ticket_label="故障单",
        ticket_plural="故障报修",
        verbs={
            "apply": "提交故障",
            "approve": "受理",
            "reject": "驳回",
            "return": "完成",
        },
        states={
            "pending": "待受理",
            "approved": "处理中",
            "rejected": "已驳回",
            "returned": "已完成",
        },
        site_menu="区域终端",
        type_menu="故障类型",
        users_menu="用户管理",
        auth_eyebrow="校园网运维",
        auth_lead="验证码登录；师生提交故障，运维受理跟进。",
        auth_points=["验证码登录", "故障报修", "受理进度"],
        register_hint="注册后可提交故障报修",
        notice_title="报修须知",
        notice_body="请写明区域、终端与故障现象并上传截图/照片，运维将尽快受理。",
        notice_page_title="运维公告",
        notice_page_lead="故障处理须知与临时通知，点击条目阅读全文。",
        my_tickets_label="我的故障",
        pending_label="故障受理",
        records_label="报修记录",
        two_level_approve=True,
        require_attach=True,
        allow_rating=True,
    )
