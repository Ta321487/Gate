"""CRM / 考勤等「档案+跟进单」族：参数化预设，避免 templates 七份近同构复制。"""

from __future__ import annotations

import copy
from typing import Any, Callable


def _stage_field(label: str, options: list[str]) -> dict[str, Any]:
    return {"key": "stage", "label": label, "type": "select", "options": options}


def _std_archive_fields(
    title_label: str,
    author_label: str,
    isbn_label: str,
    stage_label: str,
    stage_options: list[str],
    category_label: str,
    stock_label: str,
) -> list[dict[str, Any]]:
    return [
        {"key": "title", "label": title_label, "type": "string"},
        {"key": "author", "label": author_label, "type": "string"},
        {"key": "isbn", "label": isbn_label, "type": "textarea"},
        _stage_field(stage_label, stage_options),
        {"key": "category", "label": category_label, "type": "select"},
        {"key": "stock", "label": stock_label, "type": "number"},
    ]


# domain -> kwargs for archive_ticket_schema (+ banners, optional postprocess)
FOLLOWUP_PRESETS: dict[str, dict[str, Any]] = {
    "DOM-CRM": {
        "doc": "轻量 CRM：客户档案 + 跟进单据（非公海/外呼引擎）。",
        "user_label": "业务员",
        "admin_label": "销售主管（总管）",
        "subadmin_label": "客户经理",
        "archive_key": "customer",
        "archive_label": "客户",
        "archive_plural": "客户",
        "archive_fields": _std_archive_fields(
            "客户名称",
            "联系人",
            "电话/备注",
            "销售阶段",
            ["线索", "意向", "谈判", "成交", "搁置"],
            "客户分级",
            "可跟进",
        ),
        "ticket_key": "follow_up",
        "ticket_label": "跟进单",
        "ticket_plural": "跟进",
        "verbs": {
            "apply": "提交跟进",
            "approve": "确认",
            "reject": "驳回",
            "return": "完结",
            "remind": "催办",
        },
        "states": {
            "pending": "待确认",
            "approved": "跟进中",
            "rejected": "已驳回",
            "returned": "已完结",
            "overdue": "已失效",
        },
        "archive_menu_admin": "客户档案",
        "archive_menu_user": "客户列表",
        "auth_eyebrow": "客户跟进",
        "auth_lead": "验证码登录；登记名下客户并提交跟进记录，跟进即时生效，可在完成后结案。",
        "auth_points": ["验证码登录", "客户档案", "跟进记录"],
        "register_hint": "注册后可登记名下客户并提交跟进",
        "notice_title": "跟进须知",
        "notice_body": "请如实登记联系结果；跟进提交后即时入档，办结后可在记录中查阅。",
        "notice_page_title": "销售公告",
        "notice_page_lead": "跟进规范与临时通知，点击条目阅读全文。",
        "my_tickets_label": "我的跟进",
        "pending_label": "跟进审核",
        "records_label": "跟进记录",
        "remark_label": "跟进内容",
        "auto_approve": True,
        "user_publish": True,
        "contact_channel_label": "联系渠道",
        "contact_channel_options": ["电话", "微信", "邮件", "到访", "其他"],
        "contact_channel_placeholder": "电话/微信/到访等",
        "next_follow_label": "下次跟进",
        "banners": [
            {"title": "客户档案", "lead": "按分级浏览客户，维护联系人与备注。"},
            {"title": "登记客户", "lead": "登录后可登记名下客户，即时可见。"},
            {"title": "客户跟进", "lead": "提交跟进记录即时生效，办结后可追溯。"},
            {"title": "销售公告", "lead": "跟进规范与活动通知见公告栏。"},
            {"title": "我的跟进", "lead": "登录后查看跟进进度与记录。"},
        ],
    },
    "DOM-EVENT": {  # auto_approve=False：值班员确认（与场景文案一致）
        "doc": "事件/公卫上报：档案 + 上报单 + 监测打卡。",
        "user_label": "上报人",
        "admin_label": "主管（总管）",
        "subadmin_label": "值班员",
        "archive_key": "event_case",
        "archive_label": "事件",
        "archive_plural": "事件",
        "archive_fields": _std_archive_fields(
            "事件标题",
            "上报人",
            "地点/摘要",
            "处置阶段",
            ["待核查", "排查中", "处置中", "已闭环"],
            "事件分类",
            "可上报",
        ),
        "ticket_key": "event_report",
        "ticket_label": "上报单",
        "ticket_plural": "上报",
        "verbs": {
            "apply": "提交上报",
            "approve": "确认",
            "reject": "驳回",
            "return": "完结",
            "remind": "催办",
        },
        "states": {
            "pending": "待确认",
            "approved": "处置中",
            "rejected": "已驳回",
            "returned": "已完结",
            "overdue": "已失效",
        },
        "archive_menu_admin": "事件档案",
        "archive_menu_user": "事件列表",
        "auth_eyebrow": "事件上报",
        "auth_lead": "验证码登录；维护对象档案并打卡/上报，异常可转处置。",
        "auth_points": ["验证码登录", "对象档案", "健康打卡", "上报记录"],
        "register_hint": "内部账号登录后可维护档案、打卡并提交上报",
        "notice_title": "上报须知",
        "notice_body": "请如实登记要素；重大异常请及时上报，办结后可在记录中查阅。",
        "notice_page_title": "应急公告",
        "notice_page_lead": "上报规范与临时通知，点击条目阅读全文。",
        "my_tickets_label": "我的上报",
        "pending_label": "上报确认",
        "records_label": "上报记录",
        "remark_label": "上报说明",
        "auto_approve": False,
        "contact_channel_label": "上报渠道",
        "contact_channel_options": ["电话", "现场", "系统填报", "其他"],
        "contact_channel_placeholder": "电话/现场/系统填报等",
        "next_follow_label": "下次复核",
        "banners": [
            {"title": "事件档案", "lead": "按分类浏览对象档案，维护摘要与状态。"},
            {"title": "健康打卡", "lead": "对档案提交每日打卡或随访，查看今日未打卡。"},
            {"title": "事件上报", "lead": "异常线索提交上报，办结后可追溯。"},
            {"title": "应急公告", "lead": "上报规范与排查通知见公告栏。"},
            {"title": "我的上报", "lead": "登录后查看上报进度与记录。"},
            {"title": "分类管理", "lead": "按分类筛选重点对象。"},
        ],
        "postprocess": "event_archive_log",
    },
    "DOM-ATTEND": {
        "doc": "考勤请假：假种档案 + 本人请假单（我的请假填单选假种，非逛目录下单）。",
        "user_label": "员工/学生",
        "admin_label": "人事主管（总管）",
        "subadmin_label": "考勤员",
        "archive_key": "leave_type",
        "archive_label": "假种",
        "archive_plural": "假种",
        "archive_fields": _std_archive_fields(
            "假种名称",
            "归口说明",
            "申请须知备注",
            "开放状态",
            ["开放申请", "暂停", "已关闭"],
            "假种分类",
            "可申请",
        ),
        "ticket_key": "leave_req",
        "ticket_label": "请假单",
        "ticket_plural": "请假",
        "verbs": {
            "apply": "提交请假",
            "approve": "批准",
            "reject": "驳回",
            "return": "销假",
            "remind": "催办",
        },
        "states": {
            "pending": "待审批",
            "approved": "已批准",
            "rejected": "已驳回",
            "returned": "已销假",
            "overdue": "已失效",
        },
        "archive_menu_admin": "假种档案",
        "archive_menu_user": "假种说明",
        "auth_eyebrow": "考勤请假",
        "auth_lead": "验证码登录；在「我的请假」选择假种提交本人请假，审批通过后按时销假（不能代他人请假）。",
        "auth_points": ["验证码登录", "本人请假填单", "审批与销假"],
        "register_hint": "注册后可提交本人请假申请",
        "notice_title": "请假须知",
        "notice_body": "事假须提前申请；病假可补交证明；返回当日请销假。请假单归属登录账号本人。",
        "notice_page_title": "人事公告",
        "notice_page_lead": "考勤与请假通知，点击条目阅读全文。",
        "my_tickets_label": "我的请假",
        "pending_label": "请假审批",
        "records_label": "请假记录",
        "remark_label": "请假事由",
        "auto_approve": False,
        "apply_from_list": True,
        "user_tickets_first": True,
        "pick_date_range": True,
        "my_tickets_page_lead": "在此选择假种提交本人请假，并跟踪审批与销假。",
        "my_tickets_empty": "还没有请假记录，点击右上角提交请假。",
        "contact_channel_label": "请假方式",
        "contact_channel_options": ["线上申请", "纸质补录", "电话报备", "其他"],
        "contact_channel_placeholder": "线上/纸质/电话等",
        "next_follow_label": "预计销假日",
        "banners": [
            {"title": "本人请假", "lead": "登录后在「我的请假」选假种、填事由并提交。"},
            {"title": "假种说明", "lead": "查阅事假、病假、年假等开放规则与须知。"},
            {"title": "人事公告", "lead": "考勤节点与请假须知见公告栏。"},
            {"title": "审批销假", "lead": "跟踪本人审批进度，返回后按时销假。"},
            {"title": "分类查阅", "lead": "假种说明可按分类筛选查阅。"},
        ],
    },
    "DOM-FUND": {
        "doc": "资助奖学金：项目档案 + 申请单。",
        "user_label": "学生",
        "admin_label": "资助主管（总管）",
        "subadmin_label": "资助专员",
        "archive_key": "fund_program",
        "archive_label": "资助项目",
        "archive_plural": "资助项目",
        "archive_fields": _std_archive_fields(
            "项目名称",
            "归口单位",
            "名额/条件备注",
            "开放状态",
            ["开放申请", "审核中", "已截止", "已关闭"],
            "资助类型",
            "可申请",
        ),
        "ticket_key": "fund_apply",
        "ticket_label": "申请单",
        "ticket_plural": "申请",
        "verbs": {
            "apply": "提交申请",
            "approve": "通过",
            "reject": "驳回",
            "return": "办结",
            "remind": "催办",
        },
        "states": {
            "pending": "待审核",
            "approved": "已通过",
            "rejected": "已驳回",
            "returned": "已办结",
            "overdue": "已失效",
        },
        "archive_menu_admin": "资助项目",
        "archive_menu_user": "项目列表",
        "auth_eyebrow": "学生资助",
        "auth_lead": "验证码登录；浏览资助项目并提交申请，资助办审核后反馈结果。",
        "auth_points": ["验证码登录", "资助项目", "申请与审核"],
        "register_hint": "注册后可提交资助申请",
        "notice_title": "资助须知",
        "notice_body": "请按通知提交申请材料；审批通过后留意发放进度。",
        "notice_page_title": "资助公告",
        "notice_page_lead": "资助节点与材料要求，点击条目阅读全文。",
        "my_tickets_label": "我的申请",
        "pending_label": "资助审批",
        "records_label": "申请记录",
        "remark_label": "申请理由",
        "auto_approve": False,
        "contact_channel_label": "申请方式",
        "contact_channel_options": ["线上申请", "纸质补录", "其他"],
        "contact_channel_placeholder": "线上/纸质等",
        "next_follow_label": "预计办结日",
        "banners": [
            {"title": "项目浏览", "lead": "按资助类型查看开放项目与申请条件。"},
            {"title": "在线申请", "lead": "选择项目提交申请单，等待资助办审核。"},
            {"title": "资助公告", "lead": "材料节点与发放说明见公告栏。"},
            {"title": "我的申请", "lead": "登录后跟踪审批进度。"},
            {"title": "分类检索", "lead": "国家助学/校内奖学金/困难补助快速筛选。"},
        ],
    },
    "DOM-LABSAFE": {
        "doc": "实验室安全准入：实验室档案 + 准入申请单。",
        "user_label": "学生/教师",
        "admin_label": "实验室主管（总管）",
        "subadmin_label": "安全员",
        "archive_key": "lab_room",
        "archive_label": "实验室",
        "archive_plural": "实验室",
        "archive_fields": _std_archive_fields(
            "实验室名称",
            "楼宇/负责人",
            "安全等级备注",
            "开放状态",
            ["可申请", "审核中", "暂停准入", "已关闭"],
            "实验室类型",
            "可申请准入",
        ),
        "ticket_key": "access_apply",
        "ticket_label": "准入单",
        "ticket_plural": "准入",
        "verbs": {
            "apply": "申请准入",
            "approve": "批准",
            "reject": "驳回",
            "return": "办结",
            "remind": "催办",
        },
        "states": {
            "pending": "待审核",
            "approved": "已准入",
            "rejected": "已驳回",
            "returned": "已办结",
            "overdue": "已失效",
        },
        "archive_menu_admin": "实验室档案",
        "archive_menu_user": "实验室列表",
        "auth_eyebrow": "安全准入",
        "auth_lead": "验证码登录；选择实验室提交准入申请，完成安全培训审核后方可进室。",
        "auth_points": ["验证码登录", "实验室档案", "准入申请与审核"],
        "register_hint": "注册后可提交准入申请",
        "notice_title": "准入须知",
        "notice_body": "请完成安全培训并上传证明；审核通过后方可进室。",
        "notice_page_title": "实验室公告",
        "notice_page_lead": "准入规范与安全通知，点击条目阅读全文。",
        "my_tickets_label": "我的准入",
        "pending_label": "准入审批",
        "records_label": "准入记录",
        "remark_label": "实验内容摘要",
        "auto_approve": False,
        "contact_channel_label": "申请方式",
        "contact_channel_options": ["线上申请", "纸质补录", "其他"],
        "contact_channel_placeholder": "线上/纸质等",
        "next_follow_label": "拟进室日",
        "banners": [
            {"title": "实验室目录", "lead": "按类型浏览实验室与安全等级。"},
            {"title": "准入申请", "lead": "提交准入单并附培训证明，等待安全员审核。"},
            {"title": "实验室公告", "lead": "准入节点与安全须知见公告栏。"},
            {"title": "我的准入", "lead": "登录后跟踪审批结果。"},
            {"title": "分类检索", "lead": "化学/机房/金工等快速定位。"},
        ],
    },
    "DOM-RECRUIT": {
        "doc": "招聘投递：岗位 + 投递单。",
        "user_label": "求职者",
        "admin_label": "招聘主管（总管）",
        "subadmin_label": "HR专员",
        "archive_key": "job_post",
        "archive_label": "岗位",
        "archive_plural": "岗位",
        "archive_fields": _std_archive_fields(
            "岗位名称",
            "用人部门",
            "薪资/任职要求",
            "招聘状态",
            ["招聘中", "初筛中", "已满员", "已关闭"],
            "岗位类型",
            "可投递",
        ),
        "ticket_key": "job_apply",
        "ticket_label": "投递单",
        "ticket_plural": "投递",
        "verbs": {
            "apply": "投递简历",
            "approve": "初筛通过",
            "reject": "不合适",
            "return": "结束流程",
            "remind": "催办",
        },
        "states": {
            "pending": "待初筛",
            "approved": "初筛通过",
            "rejected": "未通过",
            "returned": "已结束",
            "overdue": "已失效",
        },
        "archive_menu_admin": "岗位管理",
        "archive_menu_user": "职位浏览",
        "auth_eyebrow": "校园招聘",
        "auth_lead": "验证码登录；浏览岗位并投递简历，HR 初筛后反馈结果。",
        "auth_points": ["验证码登录", "职位浏览", "投递与初筛"],
        "register_hint": "注册后可投递岗位",
        "notice_title": "投递须知",
        "notice_body": "请如实填写经历；本期不含视频面试。",
        "notice_page_title": "招聘公告",
        "notice_page_lead": "岗位更新与投递规范，点击条目阅读全文。",
        "my_tickets_label": "我的投递",
        "pending_label": "投递初筛",
        "records_label": "投递记录",
        "remark_label": "简历摘要/说明",
        "auto_approve": False,
        "contact_channel_label": "投递渠道",
        "contact_channel_options": ["网申", "现场", "内推", "其他"],
        "contact_channel_placeholder": "网申/现场/内推等",
        "next_follow_label": "期望到岗",
        "banners": [
            {"title": "职位浏览", "lead": "按类型查看在招岗位与任职要求。"},
            {"title": "投递简历", "lead": "选择岗位提交投递单，等待 HR 初筛。"},
            {"title": "招聘公告", "lead": "校招节点与材料要求见公告。"},
            {"title": "我的投递", "lead": "跟踪初筛进度与结果。"},
            {"title": "分类检索", "lead": "技术/职能/实习快速筛选。"},
        ],
    },
    "DOM-DATING": {
        "doc": "婚恋交友：交友资料 + 牵线单。",
        "user_label": "会员",
        "admin_label": "红娘主管（总管）",
        "subadmin_label": "红娘专员",
        "archive_key": "dating_profile",
        "archive_label": "交友资料",
        "archive_plural": "资料",
        "archive_fields": _std_archive_fields(
            "昵称/称呼",
            "所在城市",
            "择偶意向摘要",
            "资料状态",
            ["征婚中", "沟通中", "已牵线", "已下架"],
            "资料类型",
            "可牵线",
        ),
        "ticket_key": "match_apply",
        "ticket_label": "牵线单",
        "ticket_plural": "牵线",
        "verbs": {
            "apply": "发起牵线",
            "approve": "同意牵线",
            "reject": "不合适",
            "return": "结束流程",
            "remind": "催办",
        },
        "states": {
            "pending": "待审核",
            "approved": "已牵线",
            "rejected": "未通过",
            "returned": "已结束",
            "overdue": "已失效",
        },
        "archive_menu_admin": "资料管理",
        "archive_menu_user": "资料浏览",
        "auth_eyebrow": "婚恋交友",
        "auth_lead": "验证码登录；浏览交友资料并发起牵线，红娘审核后反馈结果。",
        "auth_points": ["验证码登录", "资料浏览", "牵线与审核"],
        "register_hint": "注册后可浏览资料并发起牵线",
        "notice_title": "牵线须知",
        "notice_body": "请如实填写资料；可通过一对一私信沟通；本期不含视频相亲。",
        "notice_page_title": "交友公告",
        "notice_page_lead": "活动节点与牵线规范，点击条目阅读全文。",
        "my_tickets_label": "我的牵线",
        "pending_label": "牵线审核",
        "records_label": "牵线记录",
        "remark_label": "意向说明",
        "auto_approve": False,
        "contact_channel_label": "意向渠道",
        "contact_channel_options": ["线上", "活动现场", "红娘推荐", "其他"],
        "contact_channel_placeholder": "线上/活动/红娘等",
        "next_follow_label": "期望见面日",
        "banners": [
            {"title": "资料浏览", "lead": "按类型查看会员资料与择偶意向。"},
            {"title": "发起牵线", "lead": "选择资料提交牵线单，等待红娘审核。"},
            {"title": "交友公告", "lead": "联谊节点与材料要求见公告。"},
            {"title": "我的牵线", "lead": "跟踪审核进度与结果。"},
            {"title": "分类检索", "lead": "按年龄段/城市等快速筛选。"},
        ],
    },
    "DOM-GRADE": {
        "doc": "教务成绩：课程档案 + 补考/更正申请。",
        "user_label": "学生",
        "admin_label": "教务主管（总管）",
        "subadmin_label": "教务员",
        "archive_key": "course_item",
        "archive_label": "课程",
        "archive_plural": "课程",
        "archive_fields": _std_archive_fields(
            "课程名称",
            "授课教师",
            "课号/学分",
            "开课状态",
            ["开课中", "已结课", "补考中", "已归档"],
            "课程类别",
            "可申请",
        ),
        "ticket_key": "grade_apply",
        "ticket_label": "成绩申请单",
        "ticket_plural": "成绩申请",
        "verbs": {
            "apply": "提交申请",
            "approve": "教务确认",
            "reject": "驳回",
            "return": "办结",
            "remind": "催办",
        },
        "states": {
            "pending": "待教务审核",
            "approved": "已确认",
            "rejected": "已驳回",
            "returned": "已办结",
            "overdue": "已失效",
        },
        "archive_menu_admin": "课程档案",
        "archive_menu_user": "课程列表",
        "auth_eyebrow": "教务成绩",
        "auth_lead": "验证码登录；查看课程并提交补考或成绩更正申请，由教务审核。",
        "auth_points": ["验证码登录", "课程列表", "成绩申请"],
        "register_hint": "注册后可提交成绩相关申请",
        "notice_title": "成绩须知",
        "notice_body": "补考与更正须说明理由；不对接学信网。",
        "notice_page_title": "教务公告",
        "notice_page_lead": "补考安排与成绩说明，点击条目阅读全文。",
        "my_tickets_label": "我的成绩申请",
        "pending_label": "成绩审核",
        "records_label": "成绩申请记录",
        "remark_label": "申请说明",
        "auto_approve": False,
        "contact_channel_label": "申请类型",
        "contact_channel_options": ["成绩更正", "补考申请", "缓考备案", "其他"],
        "contact_channel_placeholder": "更正/补考/缓考等",
        "next_follow_label": "期望处理日",
        "banners": [
            {"title": "课程列表", "lead": "按类别浏览课程与授课教师。"},
            {"title": "成绩申请", "lead": "提交补考或成绩更正，等待教务确认。"},
            {"title": "教务公告", "lead": "补考与成绩节点见公告栏。"},
            {"title": "我的申请", "lead": "跟踪审核进度。"},
            {"title": "分类检索", "lead": "必修/选修快速定位。"},
        ],
    },
    "DOM-INTERN": {
        "doc": "实习周报：实习岗 + 周报单。",
        "user_label": "实习生",
        "admin_label": "就业办主管（总管）",
        "subadmin_label": "实习辅导员",
        "archive_key": "intern_post",
        "archive_label": "实习岗位",
        "archive_plural": "实习岗位",
        "archive_fields": _std_archive_fields(
            "岗位名称",
            "企业导师",
            "单位/岗位说明",
            "实习状态",
            ["待上岗", "实习中", "已结束", "已鉴定"],
            "实习类型",
            "可交周报",
        ),
        "ticket_key": "week_report",
        "ticket_label": "周报",
        "ticket_plural": "周报",
        "verbs": {
            "apply": "提交周报",
            "approve": "导师通过",
            "reject": "退回修改",
            "return": "审阅完结",
            "remind": "催交",
        },
        "states": {
            "pending": "待审阅",
            "approved": "已通过",
            "rejected": "退回修改",
            "returned": "已完结",
            "overdue": "已逾期",
        },
        "archive_menu_admin": "实习岗位",
        # 全库示范岗目录，非「我的」过滤；与 §18 / M-01 对齐
        "archive_menu_user": "岗位目录",
        "auth_eyebrow": "实习周报",
        "auth_lead": "验证码登录；从示范岗位目录选岗提交周报，辅导员/导师审阅（≠多单位入职）。",
        "auth_points": ["验证码登录", "示范岗位目录", "周报提交与审阅"],
        "register_hint": "注册后可提交实习周报",
        "notice_title": "周报须知",
        "notice_body": (
            "请按周填写工作与问题；列表为示范岗位目录，"
            "「实习中」仅标在关联岗；CA/第三方电子签平台不在本期，本地签章见 e_sign。"
        ),
        "notice_page_title": "就业办公告",
        "notice_page_lead": "实习节点与周报要求，点击条目阅读全文。",
        "my_tickets_label": "我的周报",
        "pending_label": "周报审阅",
        "records_label": "周报记录",
        "remark_label": "本周工作内容",
        "auto_approve": False,
        "contact_channel_label": "周报形式",
        "contact_channel_options": ["在线填写", "附件补交", "其他"],
        "contact_channel_placeholder": "在线/附件等",
        "next_follow_label": "下周期望反馈",
        "banners": [
            {"title": "岗位目录", "lead": "浏览示范实习岗位与导师（全库目录，非多单位入职）。"},
            {"title": "提交周报", "lead": "选一岗按周提交工作内容，等待审阅。"},
            {"title": "就业办公告", "lead": "实习与鉴定安排见公告。"},
            {"title": "我的周报", "lead": "跟踪审阅结果。"},
            {"title": "分类检索", "lead": "按实习类型筛选示范岗位。"},
        ],
    },
    "DOM-PARCEL": {
        "doc": "快递驿站：包裹 + 取件单（接线近 LOST）。",
        "user_label": "取件人",
        "admin_label": "驿站主管（总管）",
        "subadmin_label": "驿站店员",
        "archive_key": "parcel",
        "archive_label": "包裹",
        "archive_plural": "包裹",
        "archive_fields": _std_archive_fields(
            "运单号",
            "站点",
            "取件码/柜号",
            "包裹状态",
            ["待取", "已预约", "已取出", "逾期"],
            "件型",
            "可取件",
        ),
        "ticket_key": "parcel_claim",
        "ticket_label": "取件单",
        "ticket_plural": "取件",
        "verbs": {
            "apply": "凭码取件",
            "approve": "核销出库",
            "reject": "驳回",
            "return": "取消取件",
            "remind": "催取",
        },
        "states": {
            "pending": "待核销",
            "approved": "已取出",
            "rejected": "已驳回",
            "returned": "已取消",
            "overdue": "已逾期",
        },
        "archive_menu_admin": "包裹台账",
        # 全库检索，非按用户过滤；与 §18 对齐
        "archive_menu_user": "包裹检索",
        "auth_eyebrow": "校园驿站",
        "auth_lead": "验证码登录；检索待取包裹，填写取件码提交后到站由店员核销出库（≠跑腿代买）。",
        "auth_points": ["验证码登录", "包裹检索", "取件码核销"],
        "register_hint": "注册后可凭取件码办理取件",
        "notice_title": "取件须知",
        "notice_body": "请凭取件码与手机号取件；提交后请到站出示，由店员核销。智能柜硬件不在本期。",
        "notice_page_title": "驿站公告",
        "notice_page_lead": "营业时间与催取通知，点击条目阅读全文。",
        "my_tickets_label": "我的取件",
        "pending_label": "取件核销",
        "records_label": "取件记录",
        "remark_label": "取件码",
        "stock_display": "available",
        "approve_ends_flow": True,
        "allow_rating": True,
        "require_claim_code": True,
        # 无 contact_channel / auto_approve（与 CRM 族其它域不同）
        "banners": [
            {"title": "包裹查询", "lead": "按运单与取件码查看待取包裹。"},
            {"title": "凭码取件", "lead": "填写正确取件码提交，到站由店员核销出库。"},
            {"title": "驿站公告", "lead": "营业时间与逾期催取见公告。"},
            {"title": "我的取件", "lead": "跟踪核销进度。"},
            {"title": "件型筛选", "lead": "普通/生鲜/大件快速定位。"},
        ],
    },
}

from app.bake.schema.oa_followup_presets import build_oa_followup_presets

FOLLOWUP_PRESETS.update(build_oa_followup_presets(_std_archive_fields))

from app.bake.schema.stuwork_followup_presets import build_stuwork_followup_presets

FOLLOWUP_PRESETS.update(build_stuwork_followup_presets(_std_archive_fields))

from app.bake.schema.bed_followup_presets import build_bed_followup_presets

FOLLOWUP_PRESETS.update(build_bed_followup_presets(_std_archive_fields))

from app.bake.schema.checkin_followup_presets import build_checkin_followup_presets

FOLLOWUP_PRESETS.update(build_checkin_followup_presets(_std_archive_fields))

from app.bake.schema.mutual_followup_presets import build_mutual_followup_presets

FOLLOWUP_PRESETS.update(build_mutual_followup_presets(_std_archive_fields))

from app.bake.schema.visitor_followup_presets import build_visitor_followup_presets

FOLLOWUP_PRESETS.update(build_visitor_followup_presets(_std_archive_fields))

from app.bake.schema.tail_followup_presets import build_tail_followup_presets

FOLLOWUP_PRESETS.update(build_tail_followup_presets(_std_archive_fields))

from app.bake.schema.carpool_followup_presets import build_carpool_followup_presets
from app.bake.schema.tour_followup_presets import build_tour_followup_presets

FOLLOWUP_PRESETS.update(build_carpool_followup_presets(_std_archive_fields))
FOLLOWUP_PRESETS.update(build_tour_followup_presets(_std_archive_fields))

from app.bake.schema.timebank_followup_presets import build_timebank_followup_presets

FOLLOWUP_PRESETS.update(build_timebank_followup_presets(_std_archive_fields))

from app.bake.schema.instrument_followup_presets import build_instrument_followup_presets

FOLLOWUP_PRESETS.update(build_instrument_followup_presets(_std_archive_fields))


def _attach_event_archive_log(schema: dict[str, Any]) -> dict[str, Any]:
    from app.bake.features.archive_log import ARCHIVE_LOG_CAP, attach_archive_log_schema

    caps = list(schema.get("capabilities") or [])
    if ARCHIVE_LOG_CAP not in caps:
        caps.append(ARCHIVE_LOG_CAP)
        schema["capabilities"] = caps
    attach_archive_log_schema(schema, caps)
    return schema


def _attach_instrument_slot(schema: dict[str, Any]) -> dict[str, Any]:
    """C-07：在 archive+ticket 壳上挂预约实体与菜单（机时为主路径）。"""
    from app.bake.schema.menu_utils import ensure_menu

    ents = schema.setdefault("entities", {})
    if "reservation" not in ents:
        ents["reservation"] = {
            "key": "reservation",
            "label": "机时预约",
            "labelPlural": "我的预约",
            "states": {
                "pending": "待确认",
                "confirmed": "已预约",
                "completed": "已上机",
                "cancelled": "已取消",
            },
            "completeVerb": "办结",
            "requireRemark": False,
            "remarkLabel": "备注",
            "requireConfirm": False,
            "verbs": {"apply": "预约机时"},
        }
    admin = schema.setdefault("menus", {}).setdefault("admin", [])
    user = schema.setdefault("menus", {}).setdefault("user", [])
    ensure_menu(
        user, "my_reservations", {"key": "my_reservations", "label": "我的预约"}, before_key="content"
    )
    ensure_menu(
        admin, "reservations", {"key": "reservations", "label": "预约记录"}, before_key="users"
    )
    return schema


_POSTPROCESS: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] = {
    "event_archive_log": _attach_event_archive_log,
    "instrument_slot": _attach_instrument_slot,
}


def followup_domain_schema(
    title: str,
    domain: str,
    *,
    overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """按 FOLLOWUP_PRESETS 组装 archive_ticket + 门户轮播。

    overrides：题名分支覆盖（同 templates 里 _food_schema / _shop_schema）。
    """
    # 延迟导入，避免与 templates.SCHEMA_BUILDERS 循环依赖
    from app.bake.schema.shells import _with_portal_banners, archive_ticket_schema

    preset = FOLLOWUP_PRESETS.get(domain)
    if not preset:
        raise KeyError(f"no followup preset for {domain}")
    preset = copy.deepcopy(preset)
    if overrides:
        preset.update(overrides)
    banners = list(preset.get("banners") or [])
    post_key = preset.get("postprocess")
    kw: dict[str, Any] = {
        "domain": domain,
        "user_role_id": "user",
        "users_menu": "用户管理",
        "with_deadline": False,
        "stock_display": preset.get("stock_display", "toggle"),
        "require_remark": True,
    }
    skip = {"doc", "banners", "postprocess"}
    for k, v in preset.items():
        if k in skip:
            continue
        kw[k] = v
    schema = _with_portal_banners(archive_ticket_schema(title, **kw), banners)
    if post_key:
        schema = _POSTPROCESS[post_key](schema)
    # 双角色域（STAFF_POSTS 空）不落子管，与 bake 侧 attach_staff_posts 一致
    from app.bake.staff_posts import staff_posts_for_domain

    if not staff_posts_for_domain(domain, title=title, proposal_text=""):
        roles = dict(schema.get("roles") or {})
        roles.pop("subadmin", None)
        schema["roles"] = roles
    return schema


def followup_builder(domain: str) -> Callable[[str], dict[str, Any]]:
    def _build(title: str) -> dict[str, Any]:
        return followup_domain_schema(title, domain)

    _build.__doc__ = str(FOLLOWUP_PRESETS[domain].get("doc") or "")
    _build.__name__ = f"_{domain.split('-', 1)[-1].lower()}_schema"
    return _build
