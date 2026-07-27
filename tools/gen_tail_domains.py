"""生成长尾预设 P-18、P-23～P-29（archive+ticket）。

用法（仓库根）：python tools/gen_tail_domains.py
再跑：python tools/wire_tail_domains.py
"""

from __future__ import annotations

import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
B = ROOT / "backend" / "app" / "bake"

SPECS: list[dict] = [
    {
        "pid": "P-18",
        "domain": "DOM-CARPASS",
        "label": "车辆通行证",
        "flavor": "carpass",
        "archive": "pass_zone",
        "ticket": "carpass_apply",
        "archive_label": "通行区域",
        "ticket_label": "通行证申请",
        "apply": "提交备案",
        "keywords": [
            "车辆通行证", "临时车牌", "车牌备案", "车辆通行证申请",
            "临时通行证", "进校车辆备案", "校门通行证",
        ],
        "hint": (
            "适用：临时车辆通行证/车牌备案申请与审核，通过后可签发演示通行码。"
            "勿与车位预约（停车预约）或访客行人登记混淆。"
        ),
        "caps": ["archive", "ticket_flow", "quota", "content", "org_users", "pass_code"],
        "issue_pass_code": True,
        "clerk": "车证管理员",
        "pkg": ("com.campus.carpass", "CarpassApplication", "carpass-app"),
        "title": "高校临时车辆通行证备案管理系统",
        "phrase": "临时车辆通行证与车牌备案申请审批",
        "cats": ["校门通行", "施工车辆", "访客车辆"],
        "seeds": [
            ("东门通行区", "保卫处", "工作日 7:00-22:00"),
            ("西门通行区", "保卫处", "含夜间"),
            ("施工临时区", "后勤处", "限工程车"),
        ],
        "channel": ["临时车牌", "长期备案", "施工车辆", "其他"],
        "auth_q": "campus vehicle temporary pass registration",
    },
    {
        "pid": "P-23",
        "domain": "DOM-LISTING",
        "label": "房源带看",
        "flavor": "listing",
        "archive": "listing",
        "ticket": "listing_follow",
        "archive_label": "房源",
        "ticket_label": "带看跟进",
        "apply": "登记意向",
        "keywords": [
            "房源中介", "带看跟进", "房源挂牌", "租房带看",
            "二手房带看", "房源意向", "中介带看",
        ],
        "hint": (
            "适用：房源挂牌与带看/意向跟进单据（非酒店客房预约、非二手商城成交）。"
            "勿与酒店预约或二手交易混淆。"
        ),
        "caps": ["archive", "ticket_flow", "content", "org_users"],
        "issue_pass_code": False,
        "clerk": "置业顾问",
        "pkg": ("com.campus.listing", "ListingApplication", "listing-app"),
        "title": "房源挂牌与带看跟进管理系统",
        "phrase": "房源中介挂牌与带看意向跟进",
        "cats": ["整租", "合租", "二手出售"],
        "seeds": [
            ("阳光花园 2 室", "张顾问", "地铁旁 / 可看房"),
            ("学府路单间", "李顾问", "近学校"),
            ("城南两房", "王顾问", "精装"),
        ],
        "channel": ["电话约看", "到店带看", "线上沟通", "其他"],
        "auth_q": "real estate listing showing follow up desk",
    },
    {
        "pid": "P-24",
        "domain": "DOM-PROCURE",
        "label": "采购申购",
        "flavor": "procure",
        "archive": "procure_item",
        "ticket": "procure_apply",
        "archive_label": "采购品目",
        "ticket_label": "申购单",
        "apply": "提交申购",
        "keywords": [
            "采购申请", "申购单", "物资申购", "采购审批",
            "办公用品申购", "设备申购", "采购申请单",
        ],
        "hint": (
            "适用：采购/申购单填报与审批台账（演示级，无真电商下单）。"
            "勿与资产领用或经费报销混淆。"
        ),
        "caps": ["archive", "ticket_flow", "quota", "content", "org_users"],
        "issue_pass_code": False,
        "clerk": "采购专员",
        "pkg": ("com.campus.procure", "ProcureApplication", "procure-app"),
        "title": "单位物资采购申购审批管理系统",
        "phrase": "物资采购申请与申购单审批",
        "cats": ["办公用品", "实验耗材", "设备配件"],
        "seeds": [
            ("A4 复印纸", "后勤处", "箱装 / 可申购"),
            ("试剂耗材包", "实验中心", "按清单"),
            ("键鼠套装", "信息中心", "常用"),
        ],
        "channel": ["常规采购", "紧急采购", "集中采购", "其他"],
        "auth_q": "purchase requisition procurement approval desk",
    },
    {
        "pid": "P-25",
        "domain": "DOM-CLUB",
        "label": "社团年审",
        "flavor": "club",
        "archive": "club_item",
        "ticket": "club_apply",
        "archive_label": "社团事项",
        "ticket_label": "注册年审",
        "apply": "提交材料",
        "keywords": [
            "社团注册", "社团年审", "学生社团成立", "社团备案",
            "社团注册年审", "社团审批",
        ],
        "hint": (
            "适用：学生社团成立注册/年审材料提交与审批（非活动报名占名额）。"
            "勿与社团活动报名或经费资助混淆。"
        ),
        "caps": ["archive", "ticket_flow", "content", "org_users"],
        "issue_pass_code": False,
        "clerk": "社团专员",
        "pkg": ("com.campus.club", "ClubApplication", "club-app"),
        "title": "学生社团注册与年审管理系统",
        "phrase": "学生社团注册成立与年审材料审批",
        "cats": ["成立注册", "年度审核", "变更备案"],
        "seeds": [
            ("新社团成立注册", "团委", "章程+名单"),
            ("社团年度审核", "团委", "年度总结"),
            ("负责人变更备案", "团委", "交接材料"),
        ],
        "channel": ["成立注册", "年审", "变更", "其他"],
        "auth_q": "student club registration annual review desk",
    },
    {
        "pid": "P-26",
        "domain": "DOM-PROJ",
        "label": "项目申报",
        "flavor": "proj",
        "archive": "proj_item",
        "ticket": "proj_apply",
        "archive_label": "申报项目",
        "ticket_label": "申报/检查",
        "apply": "提交申报",
        "keywords": [
            "项目申报", "大创中期", "大创检查", "创新创业项目申报",
            "科研项目申报", "项目中期检查", "大创申报",
        ],
        "hint": (
            "适用：大创/科研等项目申报与中期检查单据审核。"
            "勿与经费报销或单纯资助申请混淆。"
        ),
        "caps": ["archive", "ticket_flow", "content", "org_users"],
        "issue_pass_code": False,
        "clerk": "项目专员",
        "pkg": ("com.campus.proj", "ProjApplication", "proj-app"),
        "title": "大学生创新创业项目申报与中期检查系统",
        "phrase": "大创项目申报与中期检查材料审批",
        "cats": ["立项申报", "中期检查", "结题材料"],
        "seeds": [
            ("大创立项申报", "教务处", "本科生创新"),
            ("中期检查填报", "教务处", "进度材料"),
            ("结题验收材料", "教务处", "成果清单"),
        ],
        "channel": ["立项", "中期", "结题", "其他"],
        "auth_q": "student innovation project midterm review desk",
    },
    {
        "pid": "P-27",
        "domain": "DOM-ETHIC",
        "label": "材料审核",
        "flavor": "ethic",
        "archive": "ethic_item",
        "ticket": "ethic_apply",
        "archive_label": "审核事项",
        "ticket_label": "材料审核",
        "apply": "提交材料",
        "keywords": [
            "伦理审查", "开题答辩材料", "开题材料审核", "伦理材料",
            "答辩材料审核", "人因伦理", "开题审核",
        ],
        "hint": (
            "适用：伦理审查/开题答辩等材料提交与单级审核。"
            "勿与成绩更正或实验室准入考试混淆。"
        ),
        "caps": ["archive", "ticket_flow", "content", "org_users"],
        "issue_pass_code": False,
        "clerk": "审核秘书",
        "pkg": ("com.campus.ethic", "EthicApplication", "ethic-app"),
        "title": "开题答辩与伦理审查材料审核系统",
        "phrase": "伦理审查与开题答辩材料提交审核",
        "cats": ["伦理审查", "开题材料", "答辩材料"],
        "seeds": [
            ("人因伦理审查", "科研处", "知情同意等"),
            ("开题报告审核", "研究生院", "开题材料"),
            ("答辩材料预审", "学院", "PPT/论文稿"),
        ],
        "channel": ["伦理", "开题", "答辩", "其他"],
        "auth_q": "ethics review thesis proposal materials desk",
    },
    {
        "pid": "P-28",
        "domain": "DOM-PARTY",
        "label": "党员发展",
        "flavor": "party",
        "archive": "party_stage",
        "ticket": "party_apply",
        "archive_label": "发展阶段",
        "ticket_label": "阶段材料",
        "apply": "提交材料",
        "keywords": [
            "党员发展", "入党申请", "积极分子", "发展对象",
            "入党积极分子", "党员发展台账", "入党材料",
        ],
        "hint": (
            "适用：入党申请/积极分子等发展阶段材料提交与审批台账。"
            "勿与党建答题考试或活动报名混淆。"
        ),
        "caps": ["archive", "ticket_flow", "content", "org_users"],
        "issue_pass_code": False,
        "clerk": "组织员",
        "pkg": ("com.campus.party", "PartyApplication", "party-app"),
        "title": "党员发展对象阶段材料管理系统",
        "phrase": "入党申请与党员发展阶段材料审批",
        "cats": ["递交申请", "积极分子", "发展对象"],
        "seeds": [
            ("入党申请书审核", "党组织", "申请阶段"),
            ("积极分子考察", "党组织", "思想汇报"),
            ("发展对象公示材料", "党组织", "公示附件"),
        ],
        "channel": ["申请", "积极分子", "发展对象", "其他"],
        "auth_q": "party membership development materials desk",
    },
    {
        "pid": "P-29",
        "domain": "DOM-CONTRACT",
        "label": "合同审批",
        "flavor": "contract",
        "archive": "contract_type",
        "ticket": "contract_apply",
        "archive_label": "合同类型",
        "ticket_label": "合同审批",
        "apply": "提交合同",
        "keywords": [
            "合同审批", "合同登记", "合同审核", "单级合同审批",
            "采购合同审批", "合作协议审批",
        ],
        "hint": (
            "适用：合同/协议登记与单级审批演示（非多级会签引擎）。"
            "勿与用章申请或客户跟进（CRM）混淆。"
        ),
        "caps": ["archive", "ticket_flow", "content", "org_users"],
        "issue_pass_code": False,
        "clerk": "合同专员",
        "pkg": ("com.campus.contract", "ContractApplication", "contract-app"),
        "title": "单位合同登记与单级审批管理系统",
        "phrase": "合同登记与单级审批管理",
        "cats": ["采购合同", "合作协议", "服务合同"],
        "seeds": [
            ("采购合同审核", "法务办", "单级审批"),
            ("合作协议审核", "法务办", "对外合作"),
            ("服务合同审核", "法务办", "外包服务"),
        ],
        "channel": ["新签", "续签", "变更", "其他"],
        "auth_q": "contract registration single level approval desk",
    },
]


def catalog_py() -> str:
    blocks = []
    for s in SPECS:
        kws = ", ".join(f'"{k}"' for k in s["keywords"])
        themes = ",\n            ".join(
            f'{{"id": "{s["flavor"]}-{x}", "label": "{s["label"]}{lab}"}}'
            for x, lab in [("teal", "青绿"), ("sand", "暖沙"), ("slate", "灰青"), ("night", "深色")]
        )
        extra_feat = ""
        oom = '["外部系统对接", "电子签章 CA"]'
        if s.get("issue_pass_code"):
            extra_feat = (
                '                        {"name": "演示通行码", "status": "module"},\n'
                '                        {"name": "真车牌识别闸机", "status": "out_of_mvp"},\n'
            )
            oom = '["真车牌识别闸机", "电子签章 CA"]'
        blocks.append(
            textwrap.dedent(
                f"""\
                "{s['domain']}": {{
                    "label": "{s['label']}",
                    "keywords": [{kws}],
                    "match_hint": ("{s['hint']}"),
                    "entities": ["Archive", "Category", "Ticket", "Notice"],
                    "roles": ["user", "admin", "subadmin"],
                    "flows": ["浏览{s['archive_label']} → {s['apply']} → 审"],
                    "features": [
                        {{"name": "登录", "status": "baseline"}},
                        {{"name": "个人资料与头像", "status": "baseline"}},
                        {{"name": "管理端工作台", "status": "module"}},
                        {{"name": "{s['archive_label']}档案", "status": "domain"}},
                        {{"name": "分类管理", "status": "module"}},
                        {{"name": "用户管理", "status": "module"}},
                        {{"name": "{s['ticket_label']}审核", "status": "flow"}},
                        {{"name": "{s['ticket_label']}记录", "status": "module"}},
                        {{"name": "公告管理", "status": "module"}},
{extra_feat}                    ],
                    "out_of_mvp": {oom},
                    "themes": [
                        {themes}
                    ],
                    "gate": gate_archive_ticket(
                        archive_feature="{s['archive_label']}档案",
                        flow_feature="{s['ticket_label']}审核",
                        records_feature="{s['ticket_label']}记录",
                        users_feature="用户管理",
                        category_feature="分类管理",
                        with_deadline=False,
                    ),
                    "portal_banners": True,
                    "runtime": {{
                        "ticket_mode": "archive",
                        "ticket_table": "{s['ticket']}",
                        "register_role": "user",
                        "archive_category_table": "category",
                        "archive_item_table": "{s['archive']}",
                    }},
                }},
                """
            )
        )
    body = "\n".join(blocks)
    return (
        '"""领域目录 — 长尾预设 P-18、P-23～P-29。"""\n\n'
        "from __future__ import annotations\n\n"
        "from app.bake.gate_contracts import gate_archive_ticket\n\n"
        "DOMAINS: dict = {\n"
        f"{body}"
        "}\n"
    )


def presets_py() -> str:
    chunks = []
    for s in SPECS:
        pass_lines = ""
        if s.get("issue_pass_code"):
            pass_lines = (
                '                    "issue_pass_code": True,\n'
                '                    "pass_code_label": "通行码",\n'
            )
        ch = ", ".join(f'"{c}"' for c in s["channel"])
        chunks.append(
            textwrap.dedent(
                f"""\
                "{s['domain']}": {{
                    "doc": "{s['label']}：{s['archive_label']} + {s['ticket_label']}。",
                    "user_label": "申请人",
                    "admin_label": "业务主管（总管）",
                    "subadmin_label": "{s['clerk']}",
                    "archive_key": "{s['archive']}",
                    "archive_label": "{s['archive_label']}",
                    "archive_plural": "{s['archive_label']}",
                    "archive_fields": _std_archive_fields(
                        "名称",
                        "责任部门",
                        "说明",
                        "状态",
                        ["开放", "暂停", "关闭"],
                        "分类",
                        "可申请",
                    ),
                    "stock_display": "toggle",
                    "ticket_key": "{s['ticket']}",
                    "ticket_label": "{s['ticket_label']}",
                    "ticket_plural": "{s['ticket_label']}",
                    "verbs": {{
                        "apply": "{s['apply']}",
                        "approve": "通过",
                        "reject": "驳回",
                        "return": "完结",
                        "remind": "催办",
                    }},
                    "states": {{
                        "pending": "待审",
                        "approved": "已通过",
                        "rejected": "已驳回",
                        "returned": "已完结",
                        "overdue": "已逾期",
                    }},
                    "archive_menu_admin": "{s['archive_label']}",
                    "archive_menu_user": "{s['archive_label']}目录",
                    "auth_eyebrow": "{s['label']}",
                    "auth_lead": "验证码登录；选择{s['archive_label']}并{s['apply']}，管理员审批后完结。",
                    "auth_points": ["验证码登录", "{s['archive_label']}", "{s['apply']}与审批"],
                    "register_hint": "注册后可办理",
                    "notice_title": "{s['label']}须知",
                    "notice_body": "请如实填写说明与附件；演示环境无外部系统对接。",
                    "notice_page_title": "办理公告",
                    "notice_page_lead": "办理须知与临时通知，点击条目阅读全文。",
                    "my_tickets_label": "我的申请",
                    "pending_label": "待审申请",
                    "records_label": "申请记录",
                    "remark_label": "申请说明",
                    "auto_approve": False,
                    "approve_ends_flow": True,
{pass_lines}                    "contact_channel_label": "办理类型",
                    "contact_channel_options": [{ch}],
                    "contact_channel_placeholder": "选择类型",
                    "next_follow_label": "期望办结日",
                    "banners": [
                        {{"title": "{s['archive_label']}目录", "lead": "浏览可办理事项。"}},
                        {{"title": "{s['apply']}", "lead": "填写说明提交申请。"}},
                        {{"title": "办理公告", "lead": "须知见公告栏。"}},
                        {{"title": "我的申请", "lead": "跟踪审批进度。"}},
                        {{"title": "分类检索", "lead": "按类型筛选。"}},
                    ],
                }},
                """
            )
        )
    return (
        '"""长尾预设 FOLLOWUP_PRESETS（P-18、P-23～P-29）。"""\n\n'
        "from __future__ import annotations\n\n"
        "from typing import Any, Callable\n\n\n"
        "def build_tail_followup_presets(\n"
        "    _std_archive_fields: Callable[..., list[dict[str, Any]]],\n"
        ") -> dict[str, dict[str, Any]]:\n"
        "    return {\n"
        + "\n".join(chunks)
        + "    }\n"
    )


def sql_for(s: dict) -> str:
    a, t = s["archive"], s["ticket"]
    cats = ", ".join(f"({i+1}, '{c}')" for i, c in enumerate(s["cats"]))
    seed_rows = []
    for i, (title, author, isbn) in enumerate(s["seeds"], 1):
        seed_rows.append(
            f"({i}, '{title}', '{author}', '{isbn}', {(i-1) % len(s['cats']) + 1}, 1, 'available')"
        )
    seeds = ",\n".join(seed_rows)
    pass_col = (
        "  pass_code VARCHAR(32) NOT NULL DEFAULT '',\n" if s.get("issue_pass_code") else ""
    )
    return f"""-- bake domain={s['domain']} · tables in [${{TABLE_COUNT_MIN}},${{TABLE_COUNT_MAX}}]
CREATE DATABASE IF NOT EXISTS `${{DB_NAME}}` DEFAULT CHARACTER SET utf8mb4;
USE `${{DB_NAME}}`;

CREATE TABLE IF NOT EXISTS sys_user (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  username VARCHAR(64) NOT NULL UNIQUE,
  password VARCHAR(128) NOT NULL,
  role VARCHAR(32) NOT NULL,
  nickname VARCHAR(64),
  phone VARCHAR(32),
  avatar_url VARCHAR(255),
  profile_json VARCHAR(2048) DEFAULT '{{}}',
  super_admin TINYINT DEFAULT 0,
  profile_editable TINYINT DEFAULT 1,
  enabled TINYINT DEFAULT 1,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS category (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  name VARCHAR(64) NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS {a} (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  title VARCHAR(200) NOT NULL,
  author VARCHAR(100),
  isbn VARCHAR(256),
  category_id BIGINT,
  stock INT DEFAULT 1,
  status VARCHAR(32) DEFAULT 'available',
  cover_url VARCHAR(255),
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS {t} (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  book_id BIGINT NOT NULL,
  username VARCHAR(64) NOT NULL,
  status VARCHAR(32) NOT NULL DEFAULT 'pending',
  assignee_username VARCHAR(64) NULL,
  apply_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  approve_at DATETIME NULL,
  due_at DATETIME NULL,
  return_at DATETIME NULL,
  fine_yuan DECIMAL(10,2) NOT NULL DEFAULT 0,
  reminded_at DATETIME NULL,
  remind_msg VARCHAR(255) DEFAULT '',
  remark VARCHAR(512),
  contact_channel VARCHAR(32) DEFAULT '',
  next_follow_at DATETIME NULL,
{pass_col});

CREATE TABLE IF NOT EXISTS sys_message (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  username VARCHAR(64) NOT NULL,
  title VARCHAR(128) NOT NULL,
  body VARCHAR(512) DEFAULT '',
  ref_type VARCHAR(32) DEFAULT '',
  ref_id BIGINT NULL,
  read_at DATETIME NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  KEY idx_msg_user (username, id)
);

CREATE TABLE IF NOT EXISTS sys_notice (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  title VARCHAR(128) NOT NULL,
  content TEXT,
  publisher_username VARCHAR(64),
  publisher_name VARCHAR(64),
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS {t}_log (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  {t}_id BIGINT NOT NULL,
  action VARCHAR(32) NOT NULL,
  operator VARCHAR(64),
  remark VARCHAR(255) DEFAULT '',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO sys_user (username, password, role, nickname, phone, profile_json, super_admin, profile_editable, enabled) VALUES
('admin', 'admin123', 'admin', '业务主管', '13800000000', '{{}}', 1, 0, 1),
('subadmin', 'sub123', 'admin', '{s['clerk']}', '13800000001', '{{}}', 0, 1, 1),
('user', 'user123', 'user', '申请人甲', '13800000002',
 '{{"realName":"样例用户","email":"user@demo.edu","gender":"男","studentNo":"20230001","dept":"计算机学院"}}',
 0, 1, 1)
ON DUPLICATE KEY UPDATE nickname=VALUES(nickname), phone=VALUES(phone), profile_json=VALUES(profile_json);

INSERT IGNORE INTO category (id, name) VALUES {cats};
INSERT IGNORE INTO {a} (id, title, author, isbn, category_id, stock, status) VALUES
{seeds};
INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '{s['label']}须知', '请如实填写说明；演示环境无外部系统对接。', 'admin', '业务主管'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='{s['label']}须知');
"""


def main() -> None:
    (B / "domains_catalog" / "tail.py").write_text(catalog_py(), encoding="utf-8")
    print("wrote domains_catalog/tail.py")
    (B / "schema" / "tail_followup_presets.py").write_text(presets_py(), encoding="utf-8")
    print("wrote schema/tail_followup_presets.py")
    for s in SPECS:
        path = B / "sql" / "templates" / f"{s['domain']}.sql"
        path.write_text(sql_for(s), encoding="utf-8")
        print("wrote", path.name)
    meta = [
        {
            "pid": s["pid"],
            "domain": s["domain"],
            "flavor": s["flavor"],
            "archive": s["archive"],
            "ticket": s["ticket"],
            "title": s["title"],
            "phrase": s["phrase"],
            "pkg": s["pkg"],
            "clerk": s["clerk"],
            "caps": s["caps"],
            "auth_q": s["auth_q"],
            "issue_pass_code": bool(s.get("issue_pass_code")),
        }
        for s in SPECS
    ]
    (B / "tail_meta.py").write_text(
        '"""长尾预设元数据 P-18、P-23～P-29。"""\n\nTAIL_META = ' + repr(meta) + "\n",
        encoding="utf-8",
    )
    print("wrote tail_meta.py")
    print("done gen")


if __name__ == "__main__":
    main()
