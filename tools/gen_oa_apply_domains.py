"""生成泳道 C · P-01～P-08 具名申请域（archive+ticket 跟进壳）。

用法（仓库根）：python tools/gen_oa_apply_domains.py
写：catalog/oa.py、SQL 模板、样例、corpus 片段、builders 片段（stdout 提示）。
"""

from __future__ import annotations

import json
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend" / "app" / "bake"

# (清单ID, DOM, label, flavor, archive表, ticket表, 档案名, 单据名, apply动词, keywords, cats, seeds, admin, clerk, user)
OA_SPECS: list[dict] = [
    {
        "pid": "P-01",
        "domain": "DOM-SEAL",
        "label": "用章申请",
        "flavor": "seal",
        "archive": "seal_item",
        "ticket": "seal_apply",
        "archive_label": "印章事项",
        "ticket_label": "用章申请",
        "apply": "提交用章",
        "keywords": [
            "用章", "印章申请", "公章使用", "用印申请", "行政用章", "用章审批",
            "行政印章", "印章使用", "印章审批", "用印审批",
        ],
        "hint": "适用：行政印章/合同章用章申请与审批。勿与资助申请、请假或开具证明混淆。",
        "cats": ["行政章", "合同章", "财务章"],
        "seeds": [
            ("公章外出使用", "党政办", "校外盖章 / 需审批"),
            ("合同章用印", "法务办", "合同签订"),
            ("财务章用印", "财务处", "报销附件"),
            ("法人章用印", "院长办公室", "对外文书"),
            ("业务专用章", "教务处", "成绩证明盖章"),
        ],
        "admin": "行政主管",
        "clerk": "用章管理员",
        "user": "申请人",
        "auth_q": "office stamp seal approval desk",
        "title": "学校行政印章使用申请审批系统",
        "phrase": "行政印章使用申请审批",
    },
    {
        "pid": "P-02",
        "domain": "DOM-FLEET",
        "label": "用车申请",
        "flavor": "fleet",
        "archive": "fleet_vehicle",
        "ticket": "fleet_apply",
        "archive_label": "车辆",
        "ticket_label": "用车申请",
        "apply": "提交用车",
        "keywords": ["用车申请", "公务用车", "派车申请", "车辆申请", "公车预约", "用车审批"],
        "hint": "适用：公务用车申请与审批（可选时段冲突）。勿与车位预约、请假出差混淆。",
        "cats": ["轿车", "商务车", "中巴"],
        "seeds": [
            ("粤A·行政01", "司机王师傅", "5座轿车 / 本市"),
            ("粤A·行政02", "司机李师傅", "7座商务"),
            ("粤A·接待03", "司机赵师傅", "中巴 / 接待"),
            ("粤A·后勤04", "司机陈师傅", "皮卡 / 物资"),
            ("粤A·备用05", "车队", "5座轿车"),
        ],
        "admin": "车队主管",
        "clerk": "调度员",
        "user": "用车人",
        "auth_q": "company car fleet dispatch office",
        "title": "公务用车申请审批管理系统",
        "phrase": "公务用车选车申请审批",
    },
    {
        "pid": "P-03",
        "domain": "DOM-CERT",
        "label": "开具证明",
        "flavor": "cert",
        "archive": "cert_type",
        "ticket": "cert_apply",
        "archive_label": "证明类型",
        "ticket_label": "开具申请",
        "apply": "申请开具",
        "keywords": ["开具证明", "在读证明", "在职证明", "成绩单证明", "证明申请", "开证明"],
        "hint": "适用：在读/在职/成绩单等证明开具申请审核。勿与成绩更正、资助申请或用章混淆。",
        "cats": ["在读证明", "在职证明", "成绩证明"],
        "seeds": [
            ("在读证明", "教务处", "中英文可选"),
            ("成绩单证明", "教务处", "加盖成绩专用章"),
            ("在职证明", "人事处", "在编员工"),
            ("实习证明", "就业办", "顶岗实习"),
            ("学历证明", "档案馆", "毕业档案核对"),
        ],
        "admin": "综合主管",
        "clerk": "证明专员",
        "user": "申请人",
        "auth_q": "certificate letter stamp office desk",
        "title": "在读成绩单在职证明开具申请系统",
        "phrase": "在读成绩单在职证明开具申请审批",
    },
    {
        "pid": "P-04",
        "domain": "DOM-PROMO",
        "label": "宣传审批",
        "flavor": "promo",
        "archive": "promo_matter",
        "ticket": "promo_apply",
        "archive_label": "宣传事项",
        "ticket_label": "宣传审批",
        "apply": "提交方案",
        "keywords": ["横幅审批", "海报审批", "户外宣传", "宣传审批", "条幅申请", "宣传品审批"],
        "hint": "适用：横幅/海报/户外宣传方案审批。勿与活动报名或物业报修混淆。",
        "cats": ["横幅", "海报", "户外展板"],
        "seeds": [
            ("迎新横幅", "学工处", "校门口东侧"),
            ("讲座海报", "团委", "教学楼大厅"),
            ("招聘展板", "就业办", "广场临时展位"),
            ("运动会条幅", "体育部", "田径场看台"),
            ("社团招新海报", "学生会", "食堂门口"),
        ],
        "admin": "宣传主管",
        "clerk": "宣传员",
        "user": "申报人",
        "auth_q": "campus banner poster approval desk",
        "title": "横幅海报户外宣传审批管理系统",
        "phrase": "横幅海报户外宣传方案审批",
    },
    {
        "pid": "P-05",
        "domain": "DOM-FITOUT",
        "label": "装修备案",
        "flavor": "fitout",
        "archive": "fitout_site",
        "ticket": "fitout_apply",
        "archive_label": "施工区域",
        "ticket_label": "装修备案",
        "apply": "提交备案",
        "keywords": ["装修备案", "进场施工", "施工备案", "装修申请", "进场申请", "装修审批"],
        "hint": "适用：装修/进场施工备案申请与审核。勿与物业报修工单或事件上报混淆。",
        "cats": ["室内装修", "外立面", "机电改造"],
        "seeds": [
            ("A栋101装修", "物业工程", "工期 7 日"),
            ("食堂二层改造", "后勤处", "夜间施工"),
            ("实验室水电改造", "实验中心", "需断电备案"),
            ("办公区隔断", "行政办", "周末施工"),
            ("地下车库划线", "物业", "临时围挡"),
        ],
        "admin": "工程主管",
        "clerk": "备案员",
        "user": "申报人",
        "auth_q": "renovation construction permit office desk",
        "title": "装修进场施工备案审批系统",
        "phrase": "装修进场施工备案申请审批",
    },
    {
        "pid": "P-06",
        "domain": "DOM-ACAD",
        "label": "学籍异动",
        "flavor": "acad",
        "archive": "acad_matter",
        "ticket": "acad_apply",
        "archive_label": "异动事项",
        "ticket_label": "异动申请",
        "apply": "提交申请",
        "keywords": ["学籍异动", "转专业申请", "缓考申请", "休学申请", "复学申请", "学籍变更"],
        "hint": "适用：转专业/缓考/休学复学等学籍异动申请审核。勿与成绩更正、选课占名额或请假混淆。",
        "cats": ["转专业", "缓考", "休学复学"],
        "seeds": [
            ("转专业申请", "教务处", "跨院需会签"),
            ("缓考申请", "教务处", "病假证明"),
            ("休学申请", "学工处", "一学期起"),
            ("复学申请", "学工处", "休学期满"),
            ("退学申请", "学工处", "需家长确认"),
        ],
        "admin": "教务主管",
        "clerk": "教务员",
        "user": "学生",
        "auth_q": "university academic status change office",
        "title": "学籍异动转专业缓考申请系统",
        "phrase": "学籍异动转专业缓考申请审批",
    },
    {
        "pid": "P-07",
        "domain": "DOM-TRIP",
        "label": "出差加班",
        "flavor": "trip",
        "archive": "trip_matter",
        "ticket": "trip_apply",
        "archive_label": "事项类型",
        "ticket_label": "出差加班单",
        "apply": "提交申请",
        "keywords": ["出差申请", "加班审批", "出差审批", "加班申请", "公出申请", "加班单"],
        "hint": "适用：出差/加班申请与审批销结。勿与请销假（考勤请假）或用车申请混淆。",
        "cats": ["市内公出", "出差", "加班"],
        "seeds": [
            ("市内公出", "人事处", "当日往返"),
            ("省内出差", "人事处", "需行程说明"),
            ("加班申请", "部门", "工作日延时"),
            ("周末加班", "部门", "调休或补贴"),
            ("驻场出差", "项目组", "一周以上"),
        ],
        "admin": "人事主管",
        "clerk": "考勤员",
        "user": "员工",
        "auth_q": "business trip overtime approval desk",
        "title": "出差加班申请审批管理系统",
        "phrase": "出差加班申请审批与销结",
    },
    {
        "pid": "P-08",
        "domain": "DOM-EXPENSE",
        "label": "经费报销",
        "flavor": "expense",
        "archive": "expense_project",
        "ticket": "expense_apply",
        "archive_label": "经费项目",
        "ticket_label": "报销单",
        "apply": "提交报销",
        "keywords": ["经费报销", "报销申请", "费用报销", "差旅报销", "报销审批", "报销单"],
        "hint": "适用：演示级经费/差旅报销单审核（无银行直连）。勿与学生资助、用章或开具证明混淆。",
        "cats": ["差旅费", "办公费", "业务费"],
        "seeds": [
            ("教研差旅", "教务处", "预算内"),
            ("办公耗材报销", "行政办", "票据齐全"),
            ("会议业务费", "科研处", "需附件清单"),
            ("培训差旅", "人事处", "提前申请"),
            ("接待费报销", "党政办", "标准内"),
        ],
        "admin": "财务主管",
        "clerk": "报销审核员",
        "user": "报销人",
        "auth_q": "expense reimbursement finance desk",
        "title": "经费报销申请审批管理系统",
        "phrase": "经费差旅报销单填写与审批",
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
 '{{"realName":"样例用户","email":"demo@demo.edu","gender":"男","identityType":"教职工","employeeNo":"T20260001","dept":"综合办"}}',
 0, 1, 1)
ON DUPLICATE KEY UPDATE nickname=VALUES(nickname), phone=VALUES(phone), profile_json=VALUES(profile_json);

INSERT IGNORE INTO category (id, name) VALUES {cats};
INSERT IGNORE INTO {arch} (id, title, author, isbn, category_id, stock, status) VALUES
{seeds};
INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '{notice}', '请如实填写事由与附件说明；审批通过后方可办理。演示环境无银行/硬件对接。', 'admin', '{spec["admin"]}'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='{notice}');
"""


def _catalog_py() -> str:
    blocks = []
    for s in OA_SPECS:
        kws = ", ".join(f'"{k}"' for k in s["keywords"])
        blocks.append(
            f'''    "{s["domain"]}": {{
        "label": "{s["label"]}",
        "keywords": [{kws}],
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
            {{"name": "{s["ticket_label"]}记录", "status": "module"}},
            {{"name": "公告管理", "status": "module"}},
        ],
        "out_of_mvp": [],
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
        '"""领域目录 — OA 申请预设（P-01～P-08）。"""\n\n'
        "from __future__ import annotations\n\n"
        "from app.bake.gate_contracts import gate_archive_ticket\n\n"
        "DOMAINS: dict = {\n" + "\n".join(blocks) + "\n}\n"
    )


def _preset_snippet(s: dict) -> str:
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
        "notice_body": "请如实填写事由；演示环境无银行/硬件对接。",
        "notice_page_title": "办理公告",
        "notice_page_lead": "办理须知与临时通知，点击条目阅读全文。",
        "my_tickets_label": "我的申请",
        "pending_label": "待审申请",
        "records_label": "申请记录",
        "remark_label": "申请事由",
        "auto_approve": False,
        "contact_channel_label": "办理方式",
        "contact_channel_options": ["线上申请", "窗口补录", "其他"],
        "contact_channel_placeholder": "线上/窗口等",
        "next_follow_label": "期望办结日",
        "banners": [
            {{"title": "{s["archive_label"]}目录", "lead": "浏览可申请事项与说明。"}},
            {{"title": "{s["apply"]}", "lead": "选择事项提交申请，等待审批。"}},
            {{"title": "办理公告", "lead": "须知与节点见公告栏。"}},
            {{"title": "我的申请", "lead": "跟踪审批进度。"}},
            {{"title": "分类检索", "lead": "按类型筛选事项。"}},
        ],
    }},
'''


def main() -> None:
    cat_path = BACKEND / "domains_catalog" / "oa.py"
    cat_path.write_text(_catalog_py(), encoding="utf-8")
    print("wrote", cat_path)

    sql_dir = BACKEND / "sql" / "templates"
    for s in OA_SPECS:
        p = sql_dir / f"{s['domain']}.sql"
        p.write_text(_sql(s), encoding="utf-8")
        print("wrote", p.name)

    samples = ROOT / "data" / "samples" / "申请预设开题"
    samples.mkdir(parents=True, exist_ok=True)
    readme = ["申请预设开题（泳道 C · P-01～P-08）", "=" * 28, ""]
    for s in OA_SPECS:
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
            多级会签引擎、银行直连、电子签章 CA、硬件门禁不在本期。
            """
        )
        name = f"{s['pid']}-{s['domain']}-{s['title']}.txt"
        (samples / name).write_text(body, encoding="utf-8")
        readme.append(f"{name} -> {s['domain']}")
    (samples / "00-说明.txt").write_text("\n".join(readme) + "\n", encoding="utf-8")
    print("wrote samples", samples)

    # corpus append file for manual merge
    corpus_extra = []
    for s in OA_SPECS:
        text = (samples / f"{s['pid']}-{s['domain']}-{s['title']}.txt").read_text(encoding="utf-8")
        corpus_extra.append(
            {
                "domain": s["domain"],
                "title": s["title"],
                "year": 2025,
                "text": text,
            }
        )
    (ROOT / "backend" / "tests" / "fixtures" / "oa_opening_corpus_extra.json").write_text(
        json.dumps(corpus_extra, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print("wrote oa_opening_corpus_extra.json")

    presets = "".join(_preset_snippet(s) for s in OA_SPECS)
    (BACKEND / "schema" / "_oa_presets_generated.py").write_text(
        "# AUTO — paste into FOLLOWUP_PRESETS\nOA_PRESET_BLOCKS = {\n" + presets + "}\n",
        encoding="utf-8",
    )
    print("wrote schema/_oa_presets_generated.py")

    meta = [{k: s[k] for k in ("pid", "domain", "label", "flavor", "archive", "ticket", "auth_q", "title", "phrase")} for s in OA_SPECS]
    (BACKEND / "oa_apply_meta.py").write_text(
        '"""OA 申请域元数据（P-01～P-08）。"""\n\nOA_APPLY_META = '
        + repr(meta)
        + "\n",
        encoding="utf-8",
    )
    print("wrote oa_apply_meta.py")


if __name__ == "__main__":
    main()
