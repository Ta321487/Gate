"""领域目录 — 长尾预设 P-18、P-23～P-29。"""

from __future__ import annotations

from app.bake.gate_contracts import gate_archive_ticket

DOMAINS: dict = {
    "DOM-CARPASS": {
        "label": "车辆通行证",
        "keywords": ["车辆通行证", "临时车牌", "车牌备案", "车辆通行证申请", "临时通行证", "进校车辆备案", "校门通行证"],
        "match_hint": ("适用：临时车辆通行证/车牌备案申请与审核，通过后可签发通行码。勿与车位预约（停车预约）或访客行人登记混淆。"),
        "entities": ["Archive", "Category", "Ticket", "Notice"],
        "roles": ["user", "admin", "subadmin"],
        "flows": ["本人备案填单（选区域） → 审"],
        "features": [
            {"name": "登录", "status": "baseline"},
            {"name": "个人资料与头像", "status": "baseline"},
            {"name": "管理端工作台", "status": "module"},
            {"name": "通行区域档案", "status": "domain"},
            {"name": "分类管理", "status": "module"},
            {"name": "用户管理", "status": "module"},
            {"name": "通行证申请审核", "status": "flow"},
            {"name": "通行证申请记录", "status": "module"},
            {"name": "公告管理", "status": "module"},
            {"name": "通行码", "status": "module"},
            {"name": "真车牌识别闸机", "status": "out_of_mvp"},
        ],
        "out_of_mvp": ["真车牌识别闸机", "电子签章 CA"],
        "themes": [
            {"id": "carpass-teal", "label": "车辆通行证青绿"},
{"id": "carpass-sand", "label": "车辆通行证暖沙"},
{"id": "carpass-slate", "label": "车辆通行证灰青"},
{"id": "carpass-night", "label": "车辆通行证深色"}
        ],
        "gate": gate_archive_ticket(
            archive_feature="通行区域档案",
            flow_feature="通行证申请审核",
            records_feature="通行证申请记录",
            users_feature="用户管理",
            category_feature="分类管理",
            with_deadline=False,
        ),
        "portal_banners": True,
        "runtime": {
            "ticket_mode": "archive",
            "ticket_table": "carpass_apply",
            "register_role": "user",
            "archive_category_table": "category",
            "archive_item_table": "pass_zone",
        },
    },

    "DOM-LISTING": {
        "label": "房源带看",
        "keywords": [
            "房源中介",
            "带看跟进",
            "房源挂牌",
            "租房带看",
            "二手房带看",
            "房源意向",
            "中介带看",
            "中介看房",
            "带看安排",
            "房产经纪",
        ],
        "match_hint": (
            "适用：房源挂牌与带看/意向跟进单据（非酒店客房预约、非二手商城成交）。"
            "勿与酒店预约、二手交易或客户销售跟进（CRM）混淆。"
        ),
        "entities": ["Archive", "Category", "Ticket", "Notice"],
        "roles": ["user", "admin", "subadmin"],
        "flows": ["浏览房源 → 登记意向 → 审"],
        "features": [
            {"name": "登录", "status": "baseline"},
            {"name": "个人资料与头像", "status": "baseline"},
            {"name": "管理端工作台", "status": "module"},
            {"name": "房源档案", "status": "domain"},
            {"name": "分类管理", "status": "module"},
            {"name": "用户管理", "status": "module"},
            {"name": "带看跟进审核", "status": "flow"},
            {"name": "带看跟进记录", "status": "module"},
            {"name": "公告管理", "status": "module"},
        ],
        "out_of_mvp": ["外部系统对接", "电子签章 CA"],
        "themes": [
            {"id": "listing-teal", "label": "房源带看青绿"},
{"id": "listing-sand", "label": "房源带看暖沙"},
{"id": "listing-slate", "label": "房源带看灰青"},
{"id": "listing-night", "label": "房源带看深色"}
        ],
        "gate": gate_archive_ticket(
            archive_feature="房源档案",
            flow_feature="带看跟进审核",
            records_feature="带看跟进记录",
            users_feature="用户管理",
            category_feature="分类管理",
            with_deadline=False,
        ),
        "portal_banners": True,
        "runtime": {
            "ticket_mode": "archive",
            "ticket_table": "listing_follow",
            "register_role": "user",
            "archive_category_table": "category",
            "archive_item_table": "listing",
        },
    },

    "DOM-PROCURE": {
        "label": "采购申购",
        "keywords": [
            "采购申请",
            "申购单",
            "物资申购",
            "采购审批",
            "办公用品申购",
            "设备申购",
            "采购申请单",
            "请购单",
            "请购审批",
            "物资请购",
        ],
        "match_hint": (
            "适用：采购/申购单填报与审批台账（无真电商下单）。"
            "勿与资产领用、经费报销或商城下单混淆。"
        ),
        "entities": ["Archive", "Category", "Ticket", "Notice"],
        "roles": ["user", "admin", "subadmin"],
        "flows": ["本人申购填单（选品目） → 审"],
        "features": [
            {"name": "登录", "status": "baseline"},
            {"name": "个人资料与头像", "status": "baseline"},
            {"name": "管理端工作台", "status": "module"},
            {"name": "采购品目档案", "status": "domain"},
            {"name": "分类管理", "status": "module"},
            {"name": "用户管理", "status": "module"},
            {"name": "申购单审核", "status": "flow"},
            {"name": "申购单记录", "status": "module"},
            {"name": "公告管理", "status": "module"},
        ],
        "out_of_mvp": ["外部系统对接", "电子签章 CA"],
        "themes": [
            {"id": "procure-teal", "label": "采购申购青绿"},
{"id": "procure-sand", "label": "采购申购暖沙"},
{"id": "procure-slate", "label": "采购申购灰青"},
{"id": "procure-night", "label": "采购申购深色"}
        ],
        "gate": gate_archive_ticket(
            archive_feature="采购品目档案",
            flow_feature="申购单审核",
            records_feature="申购单记录",
            users_feature="用户管理",
            category_feature="分类管理",
            with_deadline=False,
        ),
        "portal_banners": True,
        "runtime": {
            "ticket_mode": "archive",
            "ticket_table": "procure_apply",
            "register_role": "user",
            "archive_category_table": "category",
            "archive_item_table": "procure_item",
        },
    },

    "DOM-CLUB": {
        "label": "社团年审",
        "keywords": [
            "社团注册",
            "社团年审",
            "学生社团成立",
            "社团备案",
            "社团注册年审",
            "社团审批",
            "学生组织备案",
            "成立备案",
            "年度复核",
        ],
        "match_hint": (
            "适用：学生社团成立注册/年审材料提交与审批（非活动报名占名额）。"
            "勿与社团活动报名或经费资助混淆——注册年审≠活动占名额。"
        ),
        "entities": ["Archive", "Category", "Ticket", "Notice"],
        "roles": ["user", "admin", "subadmin"],
        "flows": ["本人申请填单（选事项） → 审"],
        "features": [
            {"name": "登录", "status": "baseline"},
            {"name": "个人资料与头像", "status": "baseline"},
            {"name": "管理端工作台", "status": "module"},
            {"name": "社团事项档案", "status": "domain"},
            {"name": "分类管理", "status": "module"},
            {"name": "用户管理", "status": "module"},
            {"name": "注册年审审核", "status": "flow"},
            {"name": "注册年审记录", "status": "module"},
            {"name": "公告管理", "status": "module"},
        ],
        "out_of_mvp": ["外部系统对接", "电子签章 CA"],
        "themes": [
            {"id": "club-teal", "label": "社团年审青绿"},
{"id": "club-sand", "label": "社团年审暖沙"},
{"id": "club-slate", "label": "社团年审灰青"},
{"id": "club-night", "label": "社团年审深色"}
        ],
        "gate": gate_archive_ticket(
            archive_feature="社团事项档案",
            flow_feature="注册年审审核",
            records_feature="注册年审记录",
            users_feature="用户管理",
            category_feature="分类管理",
            with_deadline=False,
        ),
        "portal_banners": True,
        "runtime": {
            "ticket_mode": "archive",
            "ticket_table": "club_apply",
            "register_role": "user",
            "archive_category_table": "category",
            "archive_item_table": "club_item",
        },
    },

    "DOM-PROJ": {
        "label": "项目申报",
        "keywords": [
            "项目申报",
            "大创中期",
            "大创检查",
            "创新创业项目申报",
            "科研项目申报",
            "项目中期检查",
            "大创申报",
            "大创立项",
            "中期检查材料",
            "结题验收",
        ],
        "match_hint": (
            "适用：大创/科研等项目申报与中期检查单据审核。"
            "勿与经费报销、单纯资助申请或合同审批混淆。"
        ),
        "entities": ["Archive", "Category", "Ticket", "Notice"],
        "roles": ["user", "admin", "subadmin"],
        "flows": ["本人申报填单（选项目） → 审"],
        "features": [
            {"name": "登录", "status": "baseline"},
            {"name": "个人资料与头像", "status": "baseline"},
            {"name": "管理端工作台", "status": "module"},
            {"name": "申报项目档案", "status": "domain"},
            {"name": "分类管理", "status": "module"},
            {"name": "用户管理", "status": "module"},
            {"name": "申报/检查审核", "status": "flow"},
            {"name": "申报/检查记录", "status": "module"},
            {"name": "公告管理", "status": "module"},
        ],
        "out_of_mvp": ["外部系统对接", "电子签章 CA"],
        "themes": [
            {"id": "proj-teal", "label": "项目申报青绿"},
{"id": "proj-sand", "label": "项目申报暖沙"},
{"id": "proj-slate", "label": "项目申报灰青"},
{"id": "proj-night", "label": "项目申报深色"}
        ],
        "gate": gate_archive_ticket(
            archive_feature="申报项目档案",
            flow_feature="申报/检查审核",
            records_feature="申报/检查记录",
            users_feature="用户管理",
            category_feature="分类管理",
            with_deadline=False,
        ),
        "portal_banners": True,
        "runtime": {
            "ticket_mode": "archive",
            "ticket_table": "proj_apply",
            "register_role": "user",
            "archive_category_table": "category",
            "archive_item_table": "proj_item",
        },
    },

    "DOM-ETHIC": {
        "label": "材料审核",
        "keywords": [
            "伦理审查",
            "开题答辩材料",
            "开题材料审核",
            "伦理材料",
            "答辩材料审核",
            "人因伦理",
            "开题审核",
            "伦理预审",
            "开题报告审核",
            "答辩材料预审",
        ],
        "match_hint": (
            "适用：伦理审查/开题答辩等材料提交与单级审核。"
            "勿与成绩更正、实验室准入考试或党员发展材料混淆。"
        ),
        "entities": ["Archive", "Category", "Ticket", "Notice"],
        "roles": ["user", "admin", "subadmin"],
        "flows": ["本人送审填单（选事项） → 审"],
        "features": [
            {"name": "登录", "status": "baseline"},
            {"name": "个人资料与头像", "status": "baseline"},
            {"name": "管理端工作台", "status": "module"},
            {"name": "审核事项档案", "status": "domain"},
            {"name": "分类管理", "status": "module"},
            {"name": "用户管理", "status": "module"},
            {"name": "材料审核", "status": "flow"},
            {"name": "材料审核记录", "status": "module"},
            {"name": "公告管理", "status": "module"},
        ],
        "out_of_mvp": ["外部系统对接", "电子签章 CA"],
        "themes": [
            {"id": "ethic-teal", "label": "材料审核青绿"},
{"id": "ethic-sand", "label": "材料审核暖沙"},
{"id": "ethic-slate", "label": "材料审核灰青"},
{"id": "ethic-night", "label": "材料审核深色"}
        ],
        "gate": gate_archive_ticket(
            archive_feature="审核事项档案",
            flow_feature="材料审核",
            records_feature="材料审核记录",
            users_feature="用户管理",
            category_feature="分类管理",
            with_deadline=False,
        ),
        "portal_banners": True,
        "runtime": {
            "ticket_mode": "archive",
            "ticket_table": "ethic_apply",
            "register_role": "user",
            "archive_category_table": "category",
            "archive_item_table": "ethic_item",
        },
    },

    "DOM-PARTY": {
        "label": "党员发展",
        "keywords": [
            "党员发展",
            "入党申请",
            "积极分子",
            "发展对象",
            "入党积极分子",
            "党员发展台账",
            "入党材料",
            "入党申请书",
            "发展阶段台账",
            "思想汇报",
        ],
        "match_hint": (
            "适用：入党申请/积极分子等发展阶段材料提交与审批台账。"
            "勿与党建答题考试、活动报名或伦理开题材料混淆。"
        ),
        "entities": ["Archive", "Category", "Ticket", "Notice"],
        "roles": ["user", "admin", "subadmin"],
        "flows": ["本人阶段填单 → 审"],
        "features": [
            {"name": "登录", "status": "baseline"},
            {"name": "个人资料与头像", "status": "baseline"},
            {"name": "管理端工作台", "status": "module"},
            {"name": "发展阶段档案", "status": "domain"},
            {"name": "分类管理", "status": "module"},
            {"name": "用户管理", "status": "module"},
            {"name": "阶段材料审核", "status": "flow"},
            {"name": "阶段材料记录", "status": "module"},
            {"name": "公告管理", "status": "module"},
        ],
        "out_of_mvp": ["外部系统对接", "电子签章 CA"],
        "themes": [
            {"id": "party-teal", "label": "党员发展青绿"},
{"id": "party-sand", "label": "党员发展暖沙"},
{"id": "party-slate", "label": "党员发展灰青"},
{"id": "party-night", "label": "党员发展深色"}
        ],
        "gate": gate_archive_ticket(
            archive_feature="发展阶段档案",
            flow_feature="阶段材料审核",
            records_feature="阶段材料记录",
            users_feature="用户管理",
            category_feature="分类管理",
            with_deadline=False,
        ),
        "portal_banners": True,
        "runtime": {
            "ticket_mode": "archive",
            "ticket_table": "party_apply",
            "register_role": "user",
            "archive_category_table": "category",
            "archive_item_table": "party_stage",
        },
    },

    "DOM-CONTRACT": {
        "label": "合同审批",
        "keywords": [
            "合同审批",
            "合同登记",
            "合同审核",
            "单级合同审批",
            "采购合同审批",
            "合作协议审批",
            "协议审批",
            "合同台账",
            "采购合同",
            "合作协议登记",
            "协议登记审核",
            "合同单级审批",
        ],
        "match_hint": (
            "适用：合同/协议登记与单级审批（非多级会签引擎）。"
            "勿与用章申请、客户跟进（CRM）或物资申购（PROCURE）混淆——合同审批≠申购单。"
        ),
        "entities": ["Archive", "Category", "Ticket", "Notice"],
        "roles": ["user", "admin", "subadmin"],
        "flows": ["本人合同填单（选类型） → 审"],
        "features": [
            {"name": "登录", "status": "baseline"},
            {"name": "个人资料与头像", "status": "baseline"},
            {"name": "管理端工作台", "status": "module"},
            {"name": "合同类型档案", "status": "domain"},
            {"name": "分类管理", "status": "module"},
            {"name": "用户管理", "status": "module"},
            {"name": "合同审批", "status": "flow"},
            {"name": "合同审批记录", "status": "module"},
            {"name": "公告管理", "status": "module"},
        ],
        "out_of_mvp": ["外部系统对接", "电子签章 CA", "多级会签引擎"],
        "themes": [
            {"id": "contract-teal", "label": "合同审批青绿"},
{"id": "contract-sand", "label": "合同审批暖沙"},
{"id": "contract-slate", "label": "合同审批灰青"},
{"id": "contract-night", "label": "合同审批深色"}
        ],
        "gate": gate_archive_ticket(
            archive_feature="合同类型档案",
            flow_feature="合同审批",
            records_feature="合同审批记录",
            users_feature="用户管理",
            category_feature="分类管理",
            with_deadline=False,
        ),
        "portal_banners": True,
        "runtime": {
            "ticket_mode": "archive",
            "ticket_table": "contract_apply",
            "register_role": "user",
            "archive_category_table": "category",
            "archive_item_table": "contract_type",
        },
    },
}
