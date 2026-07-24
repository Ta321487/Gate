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

def _property_schema(title: str) -> dict[str, Any]:
    return standalone_ticket_schema(
        title,
        domain="DOM-PROPERTY",
        user_role_id="user",
        user_label="住户",
        admin_label="物业主管",
        subadmin_label="维修员",
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
        users_menu="用户管理",
        auth_eyebrow="物业报修",
        auth_lead="验证码登录；住户提交报修，物业受理跟进。",
        auth_points=["验证码登录", "报修申请", "受理进度"],
        register_hint="注册后以住户身份提交报修",
        notice_title="报修须知",
        notice_body="请如实填写地址与故障描述并上传现场照片，物业将尽快受理。",
        notice_page_title="物业公告",
        notice_page_lead="报修须知、社区安排与临时通知，点击条目阅读全文。",
        two_level_approve=True,
        require_attach=True,
        allow_rating=True,
    )

def _it_schema(title: str) -> dict[str, Any]:
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

