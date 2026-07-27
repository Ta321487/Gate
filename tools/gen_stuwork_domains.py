"""生成泳道 D · P-12～P-16 学工预设域（archive+ticket）。

用法（仓库根）：python tools/gen_stuwork_domains.py
再跑：python tools/wire_stuwork_domains.py
"""

from __future__ import annotations

import json
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend" / "app" / "bake"

STU_SPECS: list[dict] = [
    {
        "pid": "P-12",
        "domain": "DOM-CREDIT",
        "label": "第二课堂认定",
        "flavor": "credit",
        "archive": "credit_item",
        "ticket": "credit_apply",
        "archive_label": "认定项目",
        "ticket_label": "学分认定",
        "apply": "提交认定",
        "keywords": [
            "第二课堂", "学分认定", "第二课堂学分", "素拓学分", "素质拓展认定",
            "第二课堂认定", "课外学分认定",
        ],
        "hint": "适用：第二课堂/素拓学分项目建档与认定申请审核。勿与活动报名占名额、成绩更正或综测德育分混淆。",
        "cats": ["文体艺术", "社会实践", "学术科技"],
        "seeds": [
            ("讲座听课认定", "团委", "单次 0.5 学分"),
            ("志愿时长认定", "学工处", "累计折算"),
            ("竞赛参与认定", "教务处", "校级及以上"),
            ("社团骨干认定", "团委", "任期满一年"),
            ("社会实践认定", "学工处", "暑期实践"),
        ],
        "admin": "学工主管",
        "clerk": "认定专员",
        "user": "学生",
        "auth_q": "campus second classroom credit recognition desk",
        "title": "高校第二课堂学分认定管理系统",
        "phrase": "第二课堂学分项目认定申请审批",
        "allow_rating": False,
        "status_done": "已齐",
    },
    {
        "pid": "P-13",
        "domain": "DOM-LABOR",
        "label": "劳动时长认定",
        "flavor": "labor",
        "archive": "labor_item",
        "ticket": "labor_apply",
        "archive_label": "劳动项目",
        "ticket_label": "时长认定",
        "apply": "提交时长",
        "keywords": [
            "劳动教育", "志愿时长", "劳动时长", "劳动时长认定", "志愿时长认定",
            "劳动教育认定", "实践时长认定", "劳动实践认定",
        ],
        "hint": "适用：劳动教育/志愿实践时长登记与认定审核。勿与活动报名、请假考勤或第二课堂学分认定混淆。",
        "cats": ["劳动教育", "志愿服务", "公益实践"],
        "seeds": [
            ("校园清洁劳动", "后勤处", "每次 2 小时"),
            ("社区志愿服务", "团委", "累计登记"),
            ("图书馆整理劳动", "图书馆", "排班登记"),
            ("迎新接待志愿", "学工处", "暑期集中"),
            ("宿舍楼层劳动", "宿管中心", "每周一次"),
        ],
        "admin": "学工主管",
        "clerk": "劳动专员",
        "user": "学生",
        "auth_q": "campus labor education volunteer hours desk",
        "title": "高校劳动教育与志愿时长认定系统",
        "phrase": "劳动教育志愿时长登记认定审批",
        "allow_rating": False,
        "status_done": "已齐",
    },
    {
        "pid": "P-14",
        "domain": "DOM-EVAL",
        "label": "网上评教",
        "flavor": "eval",
        "archive": "eval_course",
        "ticket": "eval_sheet",
        "archive_label": "评教课程",
        "ticket_label": "评教卷",
        "apply": "提交评教",
        "keywords": [
            "网上评教", "教学评价", "评教系统", "课程评价", "学生评教",
            "学期评教", "教师评价",
        ],
        "hint": "适用：学期末对课程/教师提交评分与评语（演示级单分+备注）。勿与成绩更正、论坛发帖或综测申报混淆。多维度量表见能力册 C-06。",
        "cats": ["公共课", "专业课", "实验课"],
        "seeds": [
            ("高等数学A", "张老师", "2025 秋 / 公共课"),
            ("程序设计基础", "李老师", "2025 秋 / 专业课"),
            ("大学英语", "王老师", "2025 秋 / 公共课"),
            ("电路实验", "赵老师", "2025 秋 / 实验课"),
            ("形势与政策", "陈老师", "2025 秋 / 公共课"),
        ],
        "admin": "教务主管",
        "clerk": "评教员",
        "user": "学生",
        "auth_q": "university course teaching evaluation survey desk",
        "title": "高校学生网上评教管理系统",
        "phrase": "学期末学生网上评教评分与评语",
        "allow_rating": True,
        "status_done": "部分有",  # 待 C-06 多维评分
    },
    {
        "pid": "P-15",
        "domain": "DOM-MORAL",
        "label": "综测申报",
        "flavor": "moral",
        "archive": "moral_item",
        "ticket": "moral_apply",
        "archive_label": "测评指标",
        "ticket_label": "加减分申请",
        "apply": "提交申报",
        "keywords": [
            "综测", "综合测评", "德育分", "综测申报", "加减分申报",
            "综合测评系统", "德育分申报", "素质测评",
        ],
        "hint": "适用：综合测评/德育分指标项与加减分申报审核台账。勿与成绩更正、资助申请或第二课堂学分认定混淆。",
        "cats": ["德育加分", "文体加分", "扣分项"],
        "seeds": [
            ("社会工作加分", "学工处", "学生干部任期"),
            ("文体比赛加分", "团委", "校级及以上"),
            ("违规违纪扣分", "学工处", "通报处分"),
            ("志愿服务加分", "团委", "时长折算"),
            ("学术论文加分", "教务处", "公开见刊"),
        ],
        "admin": "学工主管",
        "clerk": "综测专员",
        "user": "学生",
        "auth_q": "campus comprehensive moral evaluation score desk",
        "title": "高校综合测评与德育分申报系统",
        "phrase": "综合测评德育分加减分申报审批",
        "allow_rating": False,
        "status_done": "已齐",
    },
    {
        "pid": "P-16",
        "domain": "DOM-AWARD",
        "label": "成果登记",
        "flavor": "award",
        "archive": "award_item",
        "ticket": "award_apply",
        "archive_label": "成果类型",
        "ticket_label": "成果登记",
        "apply": "提交登记",
        "keywords": [
            "创新学分", "竞赛获奖登记", "获奖登记", "学科竞赛登记",
            "创新学分登记", "竞赛成果登记", "科研成果登记",
        ],
        "hint": "适用：创新学分/竞赛获奖/成果登记与审核台账。勿与学生资助、成绩更正或活动报名混淆。",
        "cats": ["学科竞赛", "创新创业", "学术论文"],
        "seeds": [
            ("省级编程竞赛", "教务处", "一等奖可认定"),
            ("大创结题登记", "科研处", "结题证明"),
            ("公开发表论文", "科研处", "需检索证明"),
            ("专利授权登记", "科研处", "证书扫描"),
            ("校级挑战杯", "团委", "获奖证书"),
        ],
        "admin": "教务主管",
        "clerk": "成果专员",
        "user": "学生",
        "auth_q": "campus competition award innovation credit desk",
        "title": "高校创新学分与竞赛获奖登记系统",
        "phrase": "创新学分竞赛获奖成果登记审批",
        "allow_rating": False,
        "status_done": "已齐",
    },
]


def _sql(spec: dict) -> str:
    arch, ticket = spec["archive"], spec["ticket"]
    cats = ", ".join(f"({i}, '{c}')" for i, c in enumerate(spec["cats"], 1))
    seeds = ",\n".join(
        f"({i}, '{t}', '{a}', '{n}', {(i - 1) % len(spec['cats']) + 1}, 1, 'available')"
        for i, (t, a, n) in enumerate(spec["seeds"], 1)
    )
    notice = f"{spec['ticket_label']}须知"
    rating_cols = ""
    if spec.get("allow_rating"):
        rating_cols = """
  rating INT NULL,
  rating_remark VARCHAR(255) DEFAULT '',
  rated_at DATETIME NULL,"""
    return f"""-- bake domain={spec['domain']} · tables in [${{TABLE_COUNT_MIN}},${{TABLE_COUNT_MAX}}]
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

CREATE TABLE IF NOT EXISTS {arch} (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  title VARCHAR(200) NOT NULL,
  author VARCHAR(100),
  isbn VARCHAR(256),
  category_id BIGINT,
  stock INT DEFAULT 1,
  status VARCHAR(32) DEFAULT 'available',
  cover_url VARCHAR(255),
  stage VARCHAR(32) DEFAULT '开放',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS {ticket} (
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
  next_follow_at DATETIME NULL,{rating_cols}
);

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

CREATE TABLE IF NOT EXISTS {ticket}_log (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  {ticket}_id BIGINT NOT NULL,
  action VARCHAR(32) NOT NULL,
  operator VARCHAR(64),
  remark VARCHAR(255) DEFAULT '',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO sys_user (username, password, role, nickname, phone, profile_json, super_admin, profile_editable, enabled) VALUES
('admin', 'admin123', 'admin', '{spec["admin"]}', '13800000000', '{{}}', 1, 0, 1),
('subadmin', 'sub123', 'admin', '{spec["clerk"]}', '13800000001', '{{}}', 0, 1, 1),
('user', 'user123', 'user', '{spec["user"]}甲', '13800000002',
 '{{"realName":"样例学生","email":"stu@demo.edu","gender":"男","studentNo":"20230001","dept":"计算机学院"}}',
 0, 1, 1)
ON DUPLICATE KEY UPDATE nickname=VALUES(nickname), phone=VALUES(phone), profile_json=VALUES(profile_json);

INSERT IGNORE INTO category (id, name) VALUES {cats};
INSERT IGNORE INTO {arch} (id, title, author, isbn, category_id, stock, status) VALUES
{seeds};
INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '{notice}', '请如实填写说明与佐证；审批通过后计入台账。演示环境无学信网/银行对接。', 'admin', '{spec["admin"]}'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='{notice}');
"""


def _catalog_py() -> str:
    blocks = []
    for s in STU_SPECS:
        kws = ",\n            ".join(f'"{k}"' for k in s["keywords"])
        rating_feat = ""
        if s.get("allow_rating"):
            rating_feat = (
                '\n            {"name": "评分与评语", "status": "module"},'
            )
        out_mvp = '["多维度评教量表"]' if s["domain"] == "DOM-EVAL" else "[]"
        blocks.append(
            f'''    "{s["domain"]}": {{
        "label": "{s["label"]}",
        "keywords": [
            {kws},
        ],
        "match_hint": "{s["hint"]}",
        "entities": ["Archive", "Category", "Ticket", "Notice"],
        "roles": ["user", "admin", "subadmin"],
        "flows": ["选档案事项 → {s["apply"]} → 审批完结"],
        "features": [
            {{"name": "登录", "status": "baseline"}},
            {{"name": "个人资料与头像", "status": "baseline"}},
            {{"name": "管理端工作台", "status": "module"}},
            {{"name": "{s["archive_label"]}", "status": "domain"}},
            {{"name": "分类管理", "status": "module"}},
            {{"name": "用户管理", "status": "module"}},
            {{"name": "{s["ticket_label"]}审核", "status": "flow"}},
            {{"name": "{s["ticket_label"]}记录", "status": "module"}},{rating_feat}
            {{"name": "公告管理", "status": "module"}},
        ],
        "out_of_mvp": {out_mvp},
        "themes": [
            {{"id": "{s["flavor"]}-teal", "label": "{s["label"]}青绿"}},
            {{"id": "{s["flavor"]}-sand", "label": "{s["label"]}暖沙"}},
            {{"id": "{s["flavor"]}-slate", "label": "{s["label"]}灰青"}},
            {{"id": "{s["flavor"]}-night", "label": "{s["label"]}深色"}},
        ],
        "gate": gate_archive_ticket(
            archive_feature="{s["archive_label"]}",
            flow_feature="{s["ticket_label"]}审核",
            records_feature="{s["ticket_label"]}记录",
            users_feature="用户管理",
            category_feature="分类管理",
            with_deadline=False,
        ),
        "portal_banners": True,
        "runtime": {{
            "ticket_mode": "archive",
            "ticket_table": "{s["ticket"]}",
            "register_role": "user",
            "archive_category_table": "category",
            "archive_item_table": "{s["archive"]}",
        }},
    }},'''
        )
    return (
        '"""领域目录 — 学工预设（P-12～P-16）。"""\n\n'
        "from __future__ import annotations\n\n"
        "from app.bake.gate_contracts import gate_archive_ticket\n\n"
        "DOMAINS: dict = {\n" + "\n".join(blocks) + "\n}\n"
    )


def _preset_snippet(s: dict) -> str:
    rating_line = '        "allow_rating": True,\n' if s.get("allow_rating") else ""
    remark = "评教评语" if s["domain"] == "DOM-EVAL" else "申请说明"
    apply_lead = (
        "选择课程提交评分与评语。"
        if s["domain"] == "DOM-EVAL"
        else "选择事项提交申请，等待审批。"
    )
    return f'''    "{s["domain"]}": {{
        "doc": "{s["label"]}：{s["archive_label"]} + {s["ticket_label"]}。",
        "user_label": "{s["user"]}",
        "admin_label": "{s["admin"]}（总管）",
        "subadmin_label": "{s["clerk"]}",
        "archive_key": "{s["archive"]}",
        "archive_label": "{s["archive_label"]}",
        "archive_plural": "{s["archive_label"]}",
        "archive_fields": _std_archive_fields(
            "名称",
            "责任部门",
            "说明",
            "状态",
            ["开放", "暂停", "关闭"],
            "分类",
            "可申请",
        ),
        "ticket_key": "{s["ticket"]}",
        "ticket_label": "{s["ticket_label"]}",
        "ticket_plural": "{s["ticket_label"]}",
        "verbs": {{
            "apply": "{s["apply"]}",
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
        "archive_menu_admin": "{s["archive_label"]}",
        "archive_menu_user": "{s["archive_label"]}目录",
        "auth_eyebrow": "{s["label"]}",
        "auth_lead": "验证码登录；选择{s["archive_label"]}并{s["apply"]}，管理员审批后完结。",
        "auth_points": ["验证码登录", "{s["archive_label"]}", "{s["apply"]}与审批"],
        "register_hint": "注册后可{s["apply"]}",
        "notice_title": "{s["ticket_label"]}须知",
        "notice_body": "请如实填写说明与佐证；演示环境无学信网/银行对接。",
        "notice_page_title": "办理公告",
        "notice_page_lead": "办理须知与临时通知，点击条目阅读全文。",
        "my_tickets_label": "我的申请",
        "pending_label": "待审申请",
        "records_label": "申请记录",
        "remark_label": "{remark}",
        "auto_approve": False,
{rating_line}        "contact_channel_label": "办理方式",
        "contact_channel_options": ["线上申请", "窗口补录", "其他"],
        "contact_channel_placeholder": "线上/窗口等",
        "next_follow_label": "期望办结日",
        "banners": [
            {{"title": "{s["archive_label"]}目录", "lead": "浏览可申请事项与说明。"}},
            {{"title": "{s["apply"]}", "lead": "{apply_lead}"}},
            {{"title": "办理公告", "lead": "须知与节点见公告栏。"}},
            {{"title": "我的申请", "lead": "跟踪审批进度。"}},
            {{"title": "分类检索", "lead": "按类型筛选事项。"}},
        ],
    }},
'''


def main() -> None:
    cat_path = BACKEND / "domains_catalog" / "stuwork.py"
    cat_path.write_text(_catalog_py(), encoding="utf-8")
    print("wrote", cat_path)

    sql_dir = BACKEND / "sql" / "templates"
    for s in STU_SPECS:
        p = sql_dir / f"{s['domain']}.sql"
        p.write_text(_sql(s), encoding="utf-8")
        print("wrote", p.name)

    samples = ROOT / "data" / "samples" / "学工预设开题"
    samples.mkdir(parents=True, exist_ok=True)
    readme = ["学工预设开题（泳道 D · P-12～P-16）", "=" * 28, ""]
    for s in STU_SPECS:
        body = textwrap.dedent(
            f"""\
            本科毕业设计（论文）开题报告

            题目：基于 Spring Boot 与 Vue 的{s['title']}的设计与实现

            开题年份：2025
            清单编号：{s['pid']}
            挂靠领域：{s['domain']}

            一、选题背景与意义

            1.1 选题背景
            围绕「{s['phrase']}」建设轻量 Web 管理系统，支撑事项建档、在线申请与审批完结。

            1.2 选题意义
            （1）规范{s['label']}主流程；（2）审批留痕；（3）完成前后端分离工程实践。

            二、研究目标与主要内容

            3.1 研究目标
            实现{s['archive_label']}档案、{s['ticket_label']}提交与审核、记录查询及公告。

            3.2 主要功能
            1. 用户登录与资料；2. {s['archive_label']}分类检索；3. {s['apply']}；
            4. 管理端审批；5. 申请记录；6. 公告。

            四、技术方案
            Spring Boot + Vue 3 + Element Plus + MySQL；持久层按开题可选 JdbcTemplate/MyBatis/JPA。

            五、非本期范围
            多级会签、学信网对接、银行直连、硬件打卡不在本期。
            """
        )
        name = f"{s['pid']}-{s['domain']}-{s['title']}.txt"
        (samples / name).write_text(body, encoding="utf-8")
        readme.append(f"{name} -> {s['domain']} ({s['status_done']})")
    readme += [
        "",
        "P-20～P-22 床位/查寝：见 00-床位查寝骨架-P20-P22.txt（待 C-08/C-10）。",
    ]
    (samples / "00-说明.txt").write_text("\n".join(readme) + "\n", encoding="utf-8")
    print("wrote samples", samples)

    corpus_extra = []
    for s in STU_SPECS:
        text = (samples / f"{s['pid']}-{s['domain']}-{s['title']}.txt").read_text(encoding="utf-8")
        corpus_extra.append(
            {"domain": s["domain"], "title": s["title"], "year": 2025, "text": text}
        )
    (ROOT / "backend" / "tests" / "fixtures" / "stuwork_opening_corpus_extra.json").write_text(
        json.dumps(corpus_extra, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    presets = "".join(_preset_snippet(s) for s in STU_SPECS)
    (BACKEND / "schema" / "_stuwork_presets_generated.py").write_text(
        "# AUTO\nSTU_PRESET_BLOCKS = {\n" + presets + "}\n",
        encoding="utf-8",
    )

    meta = [
        {
            k: s[k]
            for k in (
                "pid", "domain", "label", "flavor", "archive", "ticket",
                "auth_q", "title", "phrase", "allow_rating", "status_done",
            )
        }
        for s in STU_SPECS
    ]
    (BACKEND / "stuwork_meta.py").write_text(
        '"""学工预设域元数据（P-12～P-16）。"""\n\nSTUWORK_META = ' + repr(meta) + "\n",
        encoding="utf-8",
    )
    print("wrote meta + presets + corpus extra")


if __name__ == "__main__":
    main()
