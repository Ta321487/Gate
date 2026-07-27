"""生成 C-05 / P-09～P-11 互选域目录、SQL、followup preset。"""

from __future__ import annotations

import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
B = ROOT / "backend" / "app" / "bake"

SPECS = [
    {
        "pid": "P-09",
        "domain": "DOM-MUTUAL-TUTOR",
        "label": "导师双选",
        "flavor": "tutor",
        "archive": "tutor",
        "ticket": "tutor_wish",
        "archive_label": "导师",
        "ticket_label": "导师志愿",
        "clerk": "导师秘书",
        "keywords": [
            "导师双选", "双向选择", "导师志愿", "研究生导师选择",
            "导师互选", "选导", "导师确认",
        ],
        "hint": (
            "适用：研究生导师双向选择：浏览导师 → 提交志愿 → 导师确认/婉拒，管理可调剂。"
            "勿与婚恋交友牵线（婚恋交友）或招聘投递混淆。"
        ),
        "title": "研究生导师双向选择志愿与确认系统",
        "phrase": "研究生导师双向选择志愿与确认",
        "pkg": ("com.campus.tutor", "TutorApplication", "tutor-app"),
        "theme_prefix": "tutor",
    },
    {
        "pid": "P-10",
        "domain": "DOM-MUTUAL-TOPIC",
        "label": "选题双选",
        "flavor": "topic",
        "archive": "thesis_topic",
        "ticket": "topic_wish",
        "archive_label": "选题",
        "ticket_label": "选题志愿",
        "clerk": "选题秘书",
        "keywords": [
            "选题双选", "毕业论文选题", "毕业设计选题", "选题志愿",
            "课题双选", "毕设选题互选", "选题确认",
        ],
        "hint": (
            "适用：毕业论文/设计选题双向选择：浏览选题 → 提交志愿 → 指导教师确认，管理可调剂。"
            "勿与公选课选课占名额或招聘投递混淆。"
        ),
        "title": "毕业论文选题双选志愿与确认系统",
        "phrase": "毕业论文选题双选志愿与确认",
        "pkg": ("com.campus.topic", "TopicApplication", "topic-app"),
        "theme_prefix": "topic",
    },
    {
        "pid": "P-11",
        "domain": "DOM-MUTUAL-TEAM",
        "label": "组队匹配",
        "flavor": "team",
        "archive": "team_profile",
        "ticket": "team_wish",
        "archive_label": "组队资料",
        "ticket_label": "组队意向",
        "clerk": "组队协调员",
        "keywords": [
            "竞赛组队", "学习搭子", "组队匹配", "组队意向",
            "搭子匹配", "队友互选", "学习小组匹配",
        ],
        "hint": (
            "适用：竞赛组队/学习搭子意向匹配：建资料 → 投意向 → 对方确认组队，管理可调剂。"
            "勿与婚恋交友或活动报名混淆。"
        ),
        "title": "竞赛组队学习搭子意向匹配系统",
        "phrase": "竞赛组队学习搭子意向匹配",
        "pkg": ("com.campus.team", "TeamApplication", "team-app"),
        "theme_prefix": "team",
    },
]


def catalog_py() -> str:
    blocks = []
    for s in SPECS:
        kws = ", ".join(f'"{k}"' for k in s["keywords"])
        blocks.append(
            textwrap.dedent(
                f"""\
                "{s['domain']}": {{
                    "label": "{s['label']}",
                    "keywords": [{kws}],
                    "match_hint": (
                        "{s['hint']}"
                    ),
                    "entities": ["Archive", "Category", "Ticket", "Notice"],
                    "roles": ["user", "admin", "subadmin"],
                    "flows": ["浏览{s['archive_label']} → 提交志愿 → 对方确认/婉拒（管理可调剂）"],
                    "features": [
                        {{"name": "登录", "status": "baseline"}},
                        {{"name": "个人资料与头像", "status": "baseline"}},
                        {{"name": "管理端工作台", "status": "module"}},
                        {{"name": "{s['archive_label']}档案", "status": "domain"}},
                        {{"name": "分类管理", "status": "module"}},
                        {{"name": "用户管理", "status": "module"}},
                        {{"name": "志愿互选确认", "status": "flow"}},
                        {{"name": "管理调剂", "status": "module"}},
                        {{"name": "志愿记录", "status": "module"}},
                        {{"name": "公告管理", "status": "module"}},
                    ],
                    "out_of_mvp": ["智能推荐算法", "多轮志愿排序引擎"],
                    "themes": [
                        {{"id": "{s['theme_prefix']}-teal", "label": "{s['label']}青绿"}},
                        {{"id": "{s['theme_prefix']}-sand", "label": "{s['label']}暖沙"}},
                        {{"id": "{s['theme_prefix']}-slate", "label": "{s['label']}灰青"}},
                        {{"id": "{s['theme_prefix']}-night", "label": "{s['label']}深色"}},
                    ],
                    "gate": gate_archive_ticket(
                        archive_feature="{s['archive_label']}档案",
                        flow_feature="志愿互选确认",
                        records_feature="志愿记录",
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
        '"""领域目录 — 互选双选（P-09～P-11 · C-05）。"""\n\n'
        "from __future__ import annotations\n\n"
        "from app.bake.gate_contracts import gate_archive_ticket\n\n"
        "DOMAINS: dict = {\n"
        f"{body}"
        "}\n"
    )


def preset_py() -> str:
    chunks = []
    for s in SPECS:
        noun = s["archive_label"]
        chunks.append(
            textwrap.dedent(
                f"""\
                "{s['domain']}": {{
                    "doc": "{s['label']}：{noun}档案 + 志愿 + 对方确认（管理可调剂）。",
                    "user_label": "学生",
                    "admin_label": "教务主管（总管）",
                    "subadmin_label": "{s['clerk']}",
                    "archive_key": "{s['archive']}",
                    "archive_label": "{noun}",
                    "archive_plural": "{noun}",
                    "archive_fields": [
                        {{"key": "title", "label": "{noun}名称", "type": "string"}},
                        {{"key": "author", "label": "所属院系", "type": "string"}},
                        {{"key": "isbn", "label": "研究方向/说明", "type": "string"}},
                        {{"key": "category", "label": "类别", "type": "select"}},
                        {{"key": "stock", "label": "可带名额", "type": "number"}},
                        {{"key": "ownerUsername", "label": "确认账号", "type": "string"}},
                    ],
                    "stock_display": "count",
                    "ticket_key": "{s['ticket']}",
                    "ticket_label": "{s['ticket_label']}",
                    "ticket_plural": "{s['ticket_label']}",
                    "verbs": {{
                        "apply": "提交志愿",
                        "approve": "调剂确认",
                        "reject": "调剂驳回",
                        "return": "撤销志愿",
                        "remind": "催确认",
                    }},
                    "states": {{
                        "pending": "待对方确认",
                        "approved": "已互选",
                        "rejected": "已婉拒",
                        "returned": "已撤销",
                        "overdue": "已失效",
                    }},
                    "archive_menu_admin": "{noun}档案",
                    "archive_menu_user": "{noun}目录",
                    "auth_eyebrow": "{s['label']}",
                    "auth_lead": "验证码登录；浏览{noun}提交志愿，由确认人接受或婉拒；管理端可调剂。",
                    "auth_points": ["验证码登录", "{noun}目录", "志愿互选确认"],
                    "register_hint": "注册后可提交志愿",
                    "notice_title": "{s['label']}须知",
                    "notice_body": "请如实填写志愿说明；确认后占用名额。智能推荐与多轮排序不在本期。",
                    "notice_page_title": "互选公告",
                    "notice_page_lead": "双选安排与须知，点击条目阅读全文。",
                    "my_tickets_label": "我的志愿",
                    "pending_label": "调剂确认",
                    "records_label": "志愿记录",
                    "remark_label": "志愿说明",
                    "peer_inbox_label": "待我确认",
                    "auto_approve": False,
                    "approve_ends_flow": True,
                    "peer_accept": True,
                    "contact_channel_label": "志愿类型",
                    "contact_channel_options": ["第一志愿", "第二志愿", "调剂志愿", "其他"],
                    "contact_channel_placeholder": "第一/第二志愿等",
                    "next_follow_label": "期望确认日",
                    "banners": [
                        {{"title": "{noun}目录", "lead": "浏览可申报对象与名额。"}},
                        {{"title": "提交志愿", "lead": "选择对象提交志愿，等待确认。"}},
                        {{"title": "待我确认", "lead": "他人向你发起的志愿在此确认或婉拒。"}},
                        {{"title": "互选公告", "lead": "节点与须知见公告栏。"}},
                        {{"title": "我的志愿", "lead": "跟踪确认与调剂结果。"}},
                    ],
                }},
                """
            )
        )
    return (
        '"""互选 FOLLOWUP_PRESETS（P-09～P-11 · C-05）。"""\n\n'
        "from __future__ import annotations\n\n"
        "from typing import Any, Callable\n\n\n"
        "def build_mutual_followup_presets(\n"
        "    _std_archive_fields: Callable[..., list[dict[str, Any]]],\n"
        ") -> dict[str, dict[str, Any]]:\n"
        "    return {\n"
        + "\n".join(chunks)
        + "    }\n"
    )


def sql_for(s: dict) -> str:
    a, t = s["archive"], s["ticket"]
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
  stock INT DEFAULT 0,
  status VARCHAR(32) DEFAULT 'available',
  cover_url VARCHAR(255),
  owner_username VARCHAR(64) NOT NULL DEFAULT '',
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
  next_follow_at DATETIME NULL
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

CREATE TABLE IF NOT EXISTS {t}_log (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  {t}_id BIGINT NOT NULL,
  action VARCHAR(32) NOT NULL,
  operator VARCHAR(64),
  remark VARCHAR(255) DEFAULT '',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO sys_user (username, password, role, nickname, phone, profile_json, super_admin, profile_editable, enabled) VALUES
('admin', 'admin123', 'admin', '教务主管', '13800000000', '{{}}', 1, 0, 1),
('subadmin', 'sub123', 'admin', '{s['clerk']}', '13800000001', '{{}}', 0, 1, 1),
('peer', 'peer123', 'user', '确认人甲', '13800000003',
 '{{"realName":"确认人甲","email":"peer@demo.edu","gender":"男","identityType":"教师","studentNo":"T20260001","dept":"计算机学院"}}',
 0, 1, 1),
('user', 'user123', 'user', '学生甲', '13800000002',
 '{{"realName":"样例学生","email":"stu@demo.edu","gender":"男","studentNo":"20230001","dept":"计算机学院"}}',
 0, 1, 1)
ON DUPLICATE KEY UPDATE nickname=VALUES(nickname), phone=VALUES(phone), profile_json=VALUES(profile_json);

INSERT IGNORE INTO category (id, name) VALUES (1, '工学'), (2, '理学'), (3, '综合');
INSERT IGNORE INTO {a} (id, title, author, isbn, category_id, stock, status, owner_username) VALUES
(1, '演示{s["archive_label"]}A', '计算机学院', '方向一 · 可带 2 人', 1, 2, 'available', 'peer'),
(2, '演示{s["archive_label"]}B', '软件学院', '方向二 · 可带 1 人', 1, 1, 'available', 'peer'),
(3, '演示{s["archive_label"]}C', '数学学院', '方向三 · 可带 2 人', 2, 2, 'available', 'peer');
INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '{s["label"]}须知', '提交志愿后由确认人接受或婉拒；管理端可调剂。智能推荐不在本期。', 'admin', '教务主管'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='{s["label"]}须知');
"""


def main() -> None:
    cat = B / "domains_catalog" / "mutual.py"
    cat.write_text(catalog_py(), encoding="utf-8")
    print("wrote", cat)
    preset = B / "schema" / "mutual_followup_presets.py"
    preset.write_text(preset_py(), encoding="utf-8")
    print("wrote", preset)
    sql_dir = B / "sql" / "templates"
    for s in SPECS:
        path = sql_dir / f"{s['domain']}.sql"
        path.write_text(sql_for(s), encoding="utf-8")
        print("wrote", path)
    meta = B / "mutual_meta.py"
    meta.write_text(
        '"""互选预设元数据（P-09～P-11）。"""\n\n'
        "MUTUAL_META = "
        + repr(
            [
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
                    "theme_prefix": s["theme_prefix"],
                }
                for s in SPECS
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    print("wrote", meta)
    print("done gen")


if __name__ == "__main__":
    main()
