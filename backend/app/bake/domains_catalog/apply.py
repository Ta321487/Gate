"""领域目录 — ACTIVITY/LOST/COURSE。"""

from __future__ import annotations

from app.bake.gate_contracts import (
    gate_archive_ticket,
)

DOMAINS: dict = {
    "DOM-ACTIVITY": {
        "label": "活动报名",
        # 词表预算 ≤20；景区领票/评选近义等长尾见 match_hint
        "keywords": [
            "社团活动", "志愿活动", "志愿者", "活动报名", "讲座报名",
            "社团报名", "志愿报名", "三下乡",
            "培训班报名", "证书报考", "四六级报名",
            "研学报名", "夏令营报名", "赛事报名", "大赛报名", "军训",
            "演出票务", "献血报名", "开放日报名", "投票报名",
        ],
        "match_hint": (
            "适用：社团/志愿/讲座/三下乡/研学/夏令营/赛事/大赛/军训等活动报名审核（占名额，非学分）；"
            "证书报考/四六级/培训班名额报名、景区演出领票、献血/开放日报名亦挂本域。"
            "开题同时写报名占名额 + 投票计票 → 本域并挂 vote（C-11）；纯十佳选票无报名走投票评选。"
            "勿与第二课堂学分认定、劳动/志愿时长认定、宿舍查寝归寝签到（查寝签到）或公选课选课混淆。"
            "勿与学生社团注册/年审材料审批（非报名占名额）混淆。"
            "勿与纯投票评选（无报名）混淆——报名占名额≠仅选票计票。"
            "勿与拼车/结伴出行意向对接（拼车结伴）混淆——活动报名≠行程同行。"
            "勿与时间银行志愿时长账户存取核销（时间银行）混淆——报名占名额≠时长账户。"
            "勿与影院选座购票座位图下单（影院选座）混淆——报名领票≠座位图购票。"
            "勿与旅行社线路/跟团游产品报名（DOM-TOUR）混淆——校园活动报名≠旅行社线路产品。"
            "献血若主写健康筛查/随访建档选事件上报，勿因献血一词互抢。"
        ),
        "entities": ["Activity", "Category", "Signup", "Notice"],
        "roles": ["user", "admin", "subadmin"],
        "flows": ["浏览活动 → 报名 → 审核占名额 → 口令签到（结束未签到记爽约）"],
        "features": [
            {"name": "登录", "status": "baseline"},
            {"name": "个人资料与头像", "status": "baseline"},
            {"name": "管理端工作台", "status": "module"},
            {"name": "活动检索", "status": "domain"},
            {"name": "分类管理", "status": "module"},
            {"name": "用户管理", "status": "module"},
            {"name": "报名申请 → 审核", "status": "flow"},
            {"name": "口令签到", "status": "module"},
            {"name": "结束未签到记爽约（可选登记费用，无余额体系）", "status": "module"},
            {"name": "报名记录", "status": "module"},
            {"name": "时间冲突检测", "status": "module"},
            {"name": "公告管理", "status": "module"},
            {"name": "人脸签到", "status": "out_of_mvp"},
        ],
        "out_of_mvp": ["人脸签到"],
        "themes": [
            {"id": "act-coral", "label": "活动珊瑚"},
            {"id": "act-sky", "label": "报名天蓝"},
            {"id": "act-lime", "label": "志愿青绿"},
            {"id": "act-night", "label": "晚会夜色"},
        ],
        "gate": gate_archive_ticket(
            archive_feature="活动检索",
            flow_feature="报名申请 → 审核",
            records_feature="报名记录",
            users_feature="用户管理",
            category_feature="分类管理",
            with_deadline=False,
        ),
        "portal_banners": True,
        "runtime": {
            "ticket_mode": "archive",
            "ticket_table": "signup",
            "register_role": "user",
            "archive_category_table": "category",
            "archive_item_table": "activity",
            "check_time_conflict": True,
        },
    },
    "DOM-LOST": {
        "label": "失物招领",
        "keywords": [
            "失物招领", "失物", "招领", "寻物", "失物管理",
            "宠物领养", "领养申请", "领养系统", "动物领养", "流浪动物领养",
            "捐赠认领", "物资认领", "捐赠物资",
        ],
        "match_hint": (
            "适用：失物招领、认领审核；题名含宠物领养时走领养申请皮（同认领壳）；"
            "捐赠物资认领亦挂本域。"
            "勿与商城二手交易、宠物医院挂号或事件上报混淆。"
        ),
        "entities": ["LostItem", "Category", "Claim", "Notice"],
        "roles": ["user", "admin", "subadmin"],
        "flows": ["浏览启事 → 认领申请 → 审核"],
        "features": [
            {"name": "登录", "status": "baseline"},
            {"name": "个人资料与头像", "status": "baseline"},
            {"name": "管理端工作台", "status": "module"},
            {"name": "失物检索", "status": "domain"},
            {"name": "分类管理", "status": "module"},
            {"name": "用户管理", "status": "module"},
            {"name": "认领申请 → 审核", "status": "flow"},
            {"name": "认领记录", "status": "module"},
            {"name": "公告管理", "status": "module"},
            {"name": "图像识别匹配", "status": "out_of_mvp"},
        ],
        "out_of_mvp": ["图像识别匹配"],
        "themes": [
            {"id": "lost-amber", "label": "招领暖黄"},
            {"id": "lost-blue", "label": "寻物蓝"},
            {"id": "lost-gray", "label": "登记灰"},
            {"id": "lost-night", "label": "夜间公示"},
        ],
        "gate": gate_archive_ticket(
            archive_feature="失物检索",
            flow_feature="认领申请 → 审核",
            records_feature="认领记录",
            users_feature="用户管理",
            category_feature="分类管理",
            with_deadline=False,
        ),
        "runtime": {
            "ticket_mode": "archive",
            "ticket_table": "claim",
            "register_role": "user",
            "archive_category_table": "category",
            "archive_item_table": "lost_item",
        },
    },
    "DOM-COURSE": {
        "label": "选课",
        "keywords": ["选课", "公选课", "课程报名", "选课系统", "课程管理", "学分名额"],
        "match_hint": (
            "适用：公选课、课程选课占名额与学分名额。"
            "勿与社团/志愿/讲座活动报名（活动报名，无学分主线）混淆。"
            "勿与第二课堂/素拓学分认定、创新学分成果登记混淆——选课占名额≠学分认定台账。"
            "开题写智能/自动排课 → 本期不做排课引擎；实包为选课+冲突检测，接题须双显。"
        ),
        "entities": ["Course", "Category", "Enrollment", "Notice"],
        "roles": ["student", "admin", "subadmin"],
        "flows": ["浏览课程 → 选课申请 → 审核占名额"],
        "features": [
            {"name": "登录", "status": "baseline"},
            {"name": "个人资料与头像", "status": "baseline"},
            {"name": "管理端工作台", "status": "module"},
            {"name": "课程检索", "status": "domain"},
            {"name": "分类管理", "status": "module"},
            {"name": "学生管理", "status": "module"},
            {"name": "选课申请 → 审核", "status": "flow"},
            {"name": "选课记录", "status": "module"},
            {"name": "时间冲突检测", "status": "module"},
            {"name": "公告管理", "status": "module"},
            {"name": "智能排课", "status": "out_of_mvp"},
        ],
        "out_of_mvp": ["智能排课"],
        "themes": [
            {"id": "course-ink", "label": "课表墨蓝"},
            {"id": "course-grove", "label": "学期青绿"},
            {"id": "course-clay", "label": "教室暖陶"},
            {"id": "course-night", "label": "夜修模式"},
        ],
        "gate": gate_archive_ticket(
            archive_feature="课程检索",
            flow_feature="选课申请 → 审核",
            records_feature="选课记录",
            users_feature="学生管理",
            category_feature="分类管理",
            with_deadline=False,
        ),
        "portal_banners": True,
        "runtime": {
            "ticket_mode": "archive",
            "ticket_table": "enrollment",
            "register_role": "student",
            "archive_category_table": "category",
            "archive_item_table": "course",
            "check_time_conflict": True,
        },
    }
}
