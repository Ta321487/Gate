"""跨域 SQL 共享片段：bake 时幂等补列，避免各 DOM-*.sql 手改漏列。

预约/订单/单据扩展列均按域（及能力开关）注入并剔除跨域超集；
运行时禁止再 ALTER 补全套。
"""

from __future__ import annotations

import re

from app.bake.sql.ddl_edit import (
    CREATE_TABLE_RE as _CREATE_TABLE_RE,
    inject_missing_columns as _inject_missing_columns,
    prune_columns as _prune_columns,
    strip_trailing_comma_before_close as _strip_trailing_comma,
)

# 预约扩展列全集（仅作剔除名单；注入按域拆分，禁止跨域超集）
RESERVATION_EXTRA_COLUMNS: list[tuple[str, str]] = [
    ("plate_no", "VARCHAR(16) DEFAULT ''"),
    ("patient_name", "VARCHAR(32) DEFAULT ''"),
    ("visit_type", "VARCHAR(16) DEFAULT ''"),
    ("symptom_note", "VARCHAR(255) DEFAULT ''"),
    ("subject", "VARCHAR(128) DEFAULT ''"),
    ("party_size", "INT DEFAULT 0"),
    ("guest_name", "VARCHAR(32) DEFAULT ''"),
    ("guest_count", "INT DEFAULT 0"),
    ("preferred_stylist", "VARCHAR(32) DEFAULT ''"),
    ("queue_no", "INT DEFAULT 0"),
    ("entry_at", "DATETIME NULL"),
]

_RESERVATION_EXTRA_NAMES = {n.lower() for n, _ in RESERVATION_EXTRA_COLUMNS}

# 具名预约域各自只保留本域字段；GENERIC / 未登记域不加扩展列
RESERVATION_COLUMNS_BY_DOMAIN: dict[str, list[tuple[str, str]]] = {
    "DOM-PARKING": [
        ("plate_no", "VARCHAR(16) DEFAULT ''"),
        ("entry_at", "DATETIME NULL"),
    ],
    "DOM-HOSPITAL": [
        ("patient_name", "VARCHAR(32) DEFAULT ''"),
        ("visit_type", "VARCHAR(16) DEFAULT ''"),
        ("symptom_note", "VARCHAR(255) DEFAULT ''"),
        ("queue_no", "INT DEFAULT 0"),
    ],
    "DOM-MEETING": [
        ("subject", "VARCHAR(128) DEFAULT ''"),
        ("party_size", "INT DEFAULT 0"),
    ],
    "DOM-HOTEL": [
        ("guest_name", "VARCHAR(32) DEFAULT ''"),
        ("guest_count", "INT DEFAULT 0"),
    ],
    "DOM-CARRENT": [
        ("guest_name", "VARCHAR(32) DEFAULT ''"),
        ("guest_count", "INT DEFAULT 0"),
    ],
    "DOM-SALON": [
        ("preferred_stylist", "VARCHAR(32) DEFAULT ''"),
        ("queue_no", "INT DEFAULT 0"),
    ],
}

# 订单履约扩展列全集（剔除名单）；注入按域拆分，禁止餐饮/商城/酒店串味
ORDER_ADDRESS_COLUMNS: list[tuple[str, str]] = [
    ("receiver_name", "VARCHAR(64) DEFAULT ''"),
    ("receiver_phone", "VARCHAR(32) DEFAULT ''"),
    ("address_line", "VARCHAR(255) DEFAULT ''"),
    ("delivery_type", "VARCHAR(32) DEFAULT ''"),
]

ORDER_FOOD_COLUMNS: list[tuple[str, str]] = [
    ("taste_note", "VARCHAR(255) DEFAULT ''"),
    ("pickup_code", "VARCHAR(32) DEFAULT ''"),
    ("shipped_at", "DATETIME NULL"),
]

ORDER_SHOP_FULFILL_COLUMNS: list[tuple[str, str]] = [
    ("tracking_no", "VARCHAR(64) DEFAULT ''"),
    ("pickup_code", "VARCHAR(32) DEFAULT ''"),
    ("shipped_at", "DATETIME NULL"),
]

ORDER_RESERVATION_LINK_COLUMNS: list[tuple[str, str]] = [
    ("reservation_id", "BIGINT NULL"),
]

# 兼容旧名：曾作「全交易域超集」；现仅作已知列目录
ORDER_SHIP_COLUMNS: list[tuple[str, str]] = [
    *ORDER_ADDRESS_COLUMNS,
    ("taste_note", "VARCHAR(255) DEFAULT ''"),
    ("tracking_no", "VARCHAR(64) DEFAULT ''"),
    ("pickup_code", "VARCHAR(32) DEFAULT ''"),
    ("shipped_at", "DATETIME NULL"),
    ("reservation_id", "BIGINT NULL"),
]

_ORDER_FULFILL_NAMES = {n.lower() for n, _ in ORDER_SHIP_COLUMNS}

# 子管/业务员工岗位（任命与登录分流）
SYS_USER_STAFF_COLUMNS: list[tuple[str, str]] = [
    ("staff_post", "VARCHAR(64) DEFAULT ''"),
    ("staff_kind", "VARCHAR(16) DEFAULT ''"),
]

# 忠诚度：余额 / 积分 / 会员（运行时按能力使用）
SYS_USER_LOYALTY_COLUMNS: list[tuple[str, str]] = [
    ("balance_yuan", "DECIMAL(10,2) NOT NULL DEFAULT 0"),
    ("points", "INT NOT NULL DEFAULT 0"),
    ("member_tier", "VARCHAR(32) DEFAULT ''"),
    ("spend_total_yuan", "DECIMAL(10,2) NOT NULL DEFAULT 0"),
]

ORDER_LOYALTY_COLUMNS: list[tuple[str, str]] = [
    ("discount_yuan", "DECIMAL(10,2) NOT NULL DEFAULT 0"),
    ("pay_balance_yuan", "DECIMAL(10,2) NOT NULL DEFAULT 0"),
    ("points_earned", "INT NOT NULL DEFAULT 0"),
    ("coupon_code", "VARCHAR(32) DEFAULT ''"),
]

ORDER_REFUND_COLUMNS: list[tuple[str, str]] = [
    ("refund_status", "VARCHAR(16) DEFAULT ''"),
    ("refund_reason", "VARCHAR(255) DEFAULT ''"),
    ("refund_at", "DATETIME NULL"),
]

_USER_LEDGER_DDL = """
CREATE TABLE IF NOT EXISTS user_ledger (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  username VARCHAR(64) NOT NULL,
  kind VARCHAR(16) NOT NULL,
  delta DECIMAL(12,2) NOT NULL,
  balance_after DECIMAL(12,2) NOT NULL DEFAULT 0,
  reason VARCHAR(64) DEFAULT '',
  ref_type VARCHAR(32) DEFAULT '',
  ref_id BIGINT NULL,
  operator VARCHAR(64) DEFAULT '',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  KEY idx_ledger_user (username, id)
);
"""


_SYS_USER_LOYALTY_NAMES = {n.lower() for n, _ in SYS_USER_LOYALTY_COLUMNS}
_ORDER_LOYALTY_NAMES = {n.lower() for n, _ in ORDER_LOYALTY_COLUMNS}


def order_fulfill_columns_for(
    domain: str,
    archetypes: list[str] | None = None,
) -> list[tuple[str, str]]:
    """按域返回订单履约列（不含退款/忠诚度）。"""
    d = (domain or "").strip()
    arches = {a for a in (archetypes or []) if a}

    if d == "DOM-FOOD":
        return list(ORDER_ADDRESS_COLUMNS) + list(ORDER_FOOD_COLUMNS)
    if d == "DOM-SHOP":
        return list(ORDER_ADDRESS_COLUMNS) + list(ORDER_SHOP_FULFILL_COLUMNS)
    if d == "DOM-HOTEL":
        return list(ORDER_RESERVATION_LINK_COLUMNS)
    if d == "DOM-CARRENT":
        return list(ORDER_RESERVATION_LINK_COLUMNS)
    if d == "DOM-GENERIC":
        cols = list(ORDER_ADDRESS_COLUMNS) + list(ORDER_SHOP_FULFILL_COLUMNS)
        if "ARCH-RESERVE" in arches:
            cols = cols + list(ORDER_RESERVATION_LINK_COLUMNS)
        return cols
    # 其他带订单的域：按商城履约，不含餐饮口味/预约外键
    return list(ORDER_ADDRESS_COLUMNS) + list(ORDER_SHOP_FULFILL_COLUMNS)


# 预约办结评价列（由 schema.entities.reservation.allowRating 注入，不进域固有超集）
RESERVATION_RATING_COLUMNS: list[tuple[str, str]] = [
    ("rating", "INT NULL"),
    ("rating_remark", "VARCHAR(255) NOT NULL DEFAULT ''"),
    ("rated_at", "DATETIME NULL"),
]
_RESERVATION_RATING_NAMES = {n.lower() for n, _ in RESERVATION_RATING_COLUMNS}


def ensure_shared_sql_columns(
    sql: str,
    *,
    domain: str = "",
    archetypes: list[str] | None = None,
    staff: bool = True,
    loyalty: bool = False,
    reservation_flags: dict | None = None,
) -> str:
    """对 reservation / 订单表 / sys_user 补齐共享列。

    预约/订单履约列均按 domain（及 GENERIC 的 archetype）注入并剔除跨域字段。
    """
    resv_cols = list(RESERVATION_COLUMNS_BY_DOMAIN.get(domain or "", []))
    resv_allow = {n.lower() for n, _ in resv_cols}
    # 评价列：开则注入并加入 allow，关则从 known 剔除（避免脏列残留）
    rf = reservation_flags if isinstance(reservation_flags, dict) else {}
    if rf.get("allowRating"):
        resv_cols = list(resv_cols) + list(RESERVATION_RATING_COLUMNS)
        resv_allow |= _RESERVATION_RATING_NAMES
    known_resv = _RESERVATION_EXTRA_NAMES | _RESERVATION_RATING_NAMES
    order_fulfill = order_fulfill_columns_for(domain, archetypes)
    order_allow = {n.lower() for n, _ in order_fulfill} | {
        n.lower() for n, _ in ORDER_REFUND_COLUMNS
    }
    if loyalty:
        order_allow |= _ORDER_LOYALTY_NAMES

    def repl(m: re.Match[str]) -> str:
        head, table, body, tail = m.group(1), m.group(2), m.group(3), m.group(4)
        t = table.lower()
        if t == "reservation":
            body = _prune_columns(
                body, allow=resv_allow, known=known_resv
            )
            if resv_cols:
                body = _inject_missing_columns(body, resv_cols)
        elif t in ("biz_order", "shop_order", "food_order", "hotel_order", "orders"):
            body = _prune_columns(
                body,
                allow=order_allow,
                known=_ORDER_FULFILL_NAMES | _ORDER_LOYALTY_NAMES,
            )
            cols = list(order_fulfill) + list(ORDER_REFUND_COLUMNS)
            if loyalty:
                cols = list(order_fulfill) + list(ORDER_LOYALTY_COLUMNS) + list(
                    ORDER_REFUND_COLUMNS
                )
            body = _inject_missing_columns(body, cols)
        elif t == "sys_user":
            if not loyalty:
                body = _prune_columns(
                    body, allow=set(), known=_SYS_USER_LOYALTY_NAMES
                )
            cols: list[tuple[str, str]] = []
            if staff:
                cols.extend(SYS_USER_STAFF_COLUMNS)
            if loyalty:
                cols.extend(SYS_USER_LOYALTY_COLUMNS)
            if cols:
                body = _inject_missing_columns(body, cols)
        return f"{head}{body}{tail}"

    out = _CREATE_TABLE_RE.sub(repl, sql)
    if not loyalty:
        out = re.sub(
            r"CREATE TABLE IF NOT EXISTS\s+`?user_ledger`?\s*\((?:.|\n)*?\);\s*",
            "",
            out,
            flags=re.IGNORECASE,
        )
    elif "user_ledger" not in out.lower():
        out = out.rstrip() + "\n" + _USER_LEDGER_DDL
    return out


_TICKET_PROGRESS_DDL = """
CREATE TABLE IF NOT EXISTS `{table}` (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  ticket_id BIGINT NOT NULL,
  status VARCHAR(32) NOT NULL,
  operator VARCHAR(64),
  remark VARCHAR(255) DEFAULT '',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  KEY idx_progress_ticket (ticket_id, id)
);
"""


_GUESTBOOK_DDL = """
CREATE TABLE IF NOT EXISTS sys_guestbook (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  username VARCHAR(64) NOT NULL,
  nickname VARCHAR(64) DEFAULT '',
  body VARCHAR(500) NOT NULL,
  reply VARCHAR(500) DEFAULT '',
  reply_username VARCHAR(64) DEFAULT '',
  replied_at DATETIME NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  KEY idx_gb_created (id),
  KEY idx_gb_user (username)
);
"""

_DM_DDL = """
CREATE TABLE IF NOT EXISTS sys_dm_message (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  from_username VARCHAR(64) NOT NULL,
  to_username VARCHAR(64) NOT NULL,
  body VARCHAR(500) NOT NULL,
  read_at DATETIME NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  KEY idx_dm_from (from_username, id),
  KEY idx_dm_to (to_username, id),
  KEY idx_dm_pair (from_username, to_username, id),
  KEY idx_dm_unread (to_username, read_at, id)
);
"""

# 私信演示：补第二用户 + 几条互发（幂等；依赖已有 user 账号）
_DM_SEED = """
INSERT INTO sys_user (username, password, role, nickname, phone, profile_json, super_admin, profile_editable, enabled)
SELECT 'user2', 'user123', 'user', '用户乙', '13800000003', '{}', 0, 1, 1
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_user WHERE username='user2');
INSERT INTO sys_dm_message (from_username, to_username, body, created_at)
SELECT 'user', 'user2', '你好，方便私信问下帖子细节吗？', DATE_SUB(NOW(), INTERVAL 10 MINUTE)
FROM DUAL
WHERE EXISTS (SELECT 1 FROM sys_user WHERE username='user')
  AND EXISTS (SELECT 1 FROM sys_user WHERE username='user2')
  AND NOT EXISTS (SELECT 1 FROM sys_dm_message LIMIT 1);
INSERT INTO sys_dm_message (from_username, to_username, body, created_at)
SELECT 'user2', 'user', '可以，你说。', DATE_SUB(NOW(), INTERVAL 8 MINUTE)
FROM DUAL
WHERE EXISTS (SELECT 1 FROM sys_user WHERE username='user')
  AND EXISTS (SELECT 1 FROM sys_user WHERE username='user2')
  AND (SELECT COUNT(*) FROM sys_dm_message) < 2;
INSERT INTO sys_dm_message (from_username, to_username, body, created_at)
SELECT 'user', 'user2', '谢谢，本期用两个浏览器窗口就能互发。', DATE_SUB(NOW(), INTERVAL 5 MINUTE)
FROM DUAL
WHERE EXISTS (SELECT 1 FROM sys_user WHERE username='user')
  AND EXISTS (SELECT 1 FROM sys_user WHERE username='user2')
  AND (SELECT COUNT(*) FROM sys_dm_message) < 3;
"""


GUESTBOOK_CHANNEL_COLUMNS: list[tuple[str, str]] = [
    ("channel", "VARCHAR(16) DEFAULT 'user'"),
]


def ensure_guestbook_sql(
    sql: str,
    *,
    enabled: bool,
    with_channel: bool = False,
) -> str:
    """能力开启时幂等补留言表；多店再补 channel 列（走 inject，勿平行 regex）。"""
    if not enabled:
        return sql
    out = sql
    if not re.search(r"(?i)CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+`?sys_guestbook`?\b", out):
        out = out.rstrip() + "\n" + _GUESTBOOK_DDL
    if not with_channel:
        return out

    def repl(m: re.Match[str]) -> str:
        head, table, body, tail = m.group(1), m.group(2), m.group(3), m.group(4)
        if table.lower() != "sys_guestbook":
            return m.group(0)
        body = _inject_missing_columns(body, GUESTBOOK_CHANNEL_COLUMNS)
        return f"{head}{body}{tail}"

    return _CREATE_TABLE_RE.sub(repl, out)


_ITEM_COMMENT_DDL = """
CREATE TABLE IF NOT EXISTS item_comment (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  item_id BIGINT NOT NULL,
  username VARCHAR(64) NOT NULL,
  nickname VARCHAR(64) DEFAULT '',
  body VARCHAR(500) NOT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  KEY idx_ic_item (item_id, id),
  KEY idx_ic_user (username)
);
"""


def ensure_item_comment_sql(sql: str, *, enabled: bool) -> str:
    """能力开启时幂等补档案条下评论表（≠ sys_guestbook）。"""
    if not enabled:
        return sql
    if re.search(r"(?i)CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+`?item_comment`?\b", sql):
        return sql
    return sql.rstrip() + "\n" + _ITEM_COMMENT_DDL


_AI_KNOWLEDGE_DDL = """
CREATE TABLE IF NOT EXISTS sys_ai_knowledge (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  category VARCHAR(64) NOT NULL DEFAULT '通用',
  title VARCHAR(128) NOT NULL,
  content VARCHAR(2000) NOT NULL,
  keywords VARCHAR(255) DEFAULT '',
  hit_count INT NOT NULL DEFAULT 0,
  enabled TINYINT NOT NULL DEFAULT 1,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  KEY idx_ai_kb_cat (category, enabled),
  KEY idx_ai_kb_hit (hit_count, id)
);
CREATE TABLE IF NOT EXISTS sys_ai_message (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  username VARCHAR(64) NOT NULL,
  role VARCHAR(16) NOT NULL,
  content VARCHAR(4000) NOT NULL,
  source VARCHAR(32) DEFAULT 'faq',
  category VARCHAR(64) DEFAULT '',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  KEY idx_ai_msg_user (username, id)
);
CREATE TABLE IF NOT EXISTS sys_ai_feedback (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  username VARCHAR(64) NOT NULL,
  message_id BIGINT NULL,
  satisfied TINYINT NOT NULL,
  comment VARCHAR(255) DEFAULT '',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  KEY idx_ai_fb_user (username, id)
);
"""


def ensure_ai_assistant_sql(
    sql: str,
    *,
    enabled: bool,
    domain: str = "",
    title: str = "",
    proposal_text: str = "",
    capabilities: list | None = None,
) -> str:
    """能力开启时幂等补 AI 表，并按域/开题灌 FAQ 种子。"""
    if not enabled:
        return sql
    from app.bake.features.ai_assistant import build_ai_knowledge_seed_sql

    out = sql
    if not re.search(r"(?i)CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+`?sys_ai_knowledge`?\b", out):
        out = out.rstrip() + "\n" + _AI_KNOWLEDGE_DDL
    if "INSERT INTO sys_ai_knowledge" not in out:
        out = out.rstrip() + "\n" + build_ai_knowledge_seed_sql(
            domain=domain,
            title=title,
            proposal_text=proposal_text,
            capabilities=capabilities,
        )
    return out


_EXAM_WRONGBOOK_DDL = """
CREATE TABLE IF NOT EXISTS exam_wrongbook (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  username VARCHAR(64) NOT NULL,
  question_id BIGINT NOT NULL,
  last_answer VARCHAR(2000) DEFAULT '',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uk_wb_user_q (username, question_id),
  KEY idx_wb_user (username, id)
);
"""

_EXAM_CORE_DDL = """
CREATE TABLE IF NOT EXISTS exam_question (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  subject_id BIGINT NULL,
  type VARCHAR(16) NOT NULL,
  stem VARCHAR(2000) NOT NULL,
  options_json VARCHAR(2000) DEFAULT '',
  answer_key VARCHAR(500) NOT NULL,
  score INT NOT NULL DEFAULT 5,
  explain_text VARCHAR(2000) NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS exam_paper (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  title VARCHAR(200) NOT NULL,
  duration_min INT NOT NULL DEFAULT 0,
  status VARCHAR(16) NOT NULL DEFAULT 'draft',
  subject_id BIGINT NULL,
  max_attempts INT NOT NULL DEFAULT 0,
  gate_ticket TINYINT NOT NULL DEFAULT 0,
  pass_score INT NOT NULL DEFAULT 60,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS exam_paper_question (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  paper_id BIGINT NOT NULL,
  question_id BIGINT NOT NULL,
  sort_no INT NOT NULL DEFAULT 0,
  UNIQUE KEY uk_paper_q (paper_id, question_id)
);

CREATE TABLE IF NOT EXISTS exam_attempt (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  paper_id BIGINT NOT NULL,
  username VARCHAR(64) NOT NULL,
  mode VARCHAR(16) NOT NULL DEFAULT 'exam',
  status VARCHAR(16) NOT NULL DEFAULT 'in_progress',
  score INT NOT NULL DEFAULT 0,
  total_score INT NOT NULL DEFAULT 0,
  started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  submitted_at DATETIME NULL,
  timed_out TINYINT NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS exam_answer (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  attempt_id BIGINT NOT NULL,
  question_id BIGINT NOT NULL,
  answer_text VARCHAR(2000) DEFAULT '',
  is_correct TINYINT NOT NULL DEFAULT 0,
  score INT NOT NULL DEFAULT 0,
  UNIQUE KEY uk_attempt_q (attempt_id, question_id)
);
"""

_EXAM_LABSAFE_GATE_SEED = """
INSERT IGNORE INTO exam_question (id, subject_id, type, stem, options_json, answer_key, score, explain_text) VALUES
(9001, NULL, 'single', '进入实验室前应首先确认什么？',
 '["实验目的","安全须知与防护用品","午餐菜单","课程成绩"]', 'B', 20, '须先完成安全培训与防护准备。'),
(9002, NULL, 'judge', '未通过安全准入考试也可直接申请入室。',
 '["正确","错误"]', '错误', 20, '须先考试通过再申请准入。'),
(9003, NULL, 'multi', '实验室常见防护措施包括哪些？',
 '["穿实验服","戴护目镜","禁止饮食","随意倾倒废液"]', 'A,B,C', 30, '废液须按规定回收。'),
(9004, NULL, 'subjective', '简述发现火情时的正确做法。',
 '', '参考：报警、撤离、使用灭火器，勿用水扑灭电器火。', 30, '参考答案供教师阅卷，不自动匹配。');

INSERT IGNORE INTO exam_paper (id, title, duration_min, status, subject_id, max_attempts, gate_ticket, pass_score) VALUES
(9001, '实验室安全准入考试卷', 30, 'published', NULL, 0, 1, 60);

INSERT IGNORE INTO exam_paper_question (id, paper_id, question_id, sort_no) VALUES
(9001, 9001, 9001, 1), (9002, 9001, 9002, 2), (9003, 9001, 9003, 3), (9004, 9001, 9004, 4);
"""


def ensure_exam_wrongbook_sql(sql: str, *, enabled: bool) -> str:
    """开题写到错题本时幂等补表；未开启不注入。"""
    if not enabled:
        return sql
    if re.search(r"(?i)CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+`?exam_wrongbook`?\b", sql):
        return sql
    return sql.rstrip() + "\n" + _EXAM_WRONGBOOK_DDL


_VOTE_CORE_DDL = """
CREATE TABLE IF NOT EXISTS vote_campaign (
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

CREATE TABLE IF NOT EXISTS vote_candidate (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  campaign_id BIGINT NOT NULL,
  name VARCHAR(128) NOT NULL,
  intro VARCHAR(1000) DEFAULT '',
  sort_no INT NOT NULL DEFAULT 0,
  status VARCHAR(32) DEFAULT 'available',
  avatar_url VARCHAR(255) DEFAULT '',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  KEY idx_vote_cand_camp (campaign_id)
);

CREATE TABLE IF NOT EXISTS vote_ballot (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  campaign_id BIGINT NOT NULL,
  username VARCHAR(64) NOT NULL,
  candidate_id BIGINT NOT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uk_vote_user_cand (campaign_id, username, candidate_id),
  KEY idx_vote_ball_user (campaign_id, username)
);
"""

_VOTE_ACTIVITY_SEED = """
INSERT IGNORE INTO vote_campaign (id, title, author, isbn, category_id, stock, status) VALUES
(1, '活动优秀个人评选', '主办方', '每人限投 1 票；与活动报名并行', 1, 1, 'available');
INSERT IGNORE INTO vote_candidate (id, campaign_id, name, intro, sort_no, status) VALUES
(1, 1, '候选人甲', '活动积极分子', 1, 'available'),
(2, 1, '候选人乙', '志愿服务突出', 2, 'available'),
(3, 1, '候选人丙', '组织协调得力', 3, 'available');
"""


VOTE_CANDIDATE_COLUMNS: list[tuple[str, str]] = [
    ("avatar_url", "VARCHAR(255) DEFAULT ''"),
]


def ensure_vote_sql(sql: str, *, enabled: bool, seed_activity: bool = False) -> str:
    """vote 能力开启时幂等补评选表；表已存在时仍补 avatar_url（DOM-VOTE 模板曾漏列）。"""
    if not enabled:
        return sql
    out = sql
    if not re.search(r"(?i)CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+`?vote_ballot`?\b", out):
        out = out.rstrip() + "\n" + _VOTE_CORE_DDL

    def repl(m: re.Match[str]) -> str:
        head, table, body, tail = m.group(1), m.group(2), m.group(3), m.group(4)
        if table.lower() != "vote_candidate":
            return m.group(0)
        body = _inject_missing_columns(body, VOTE_CANDIDATE_COLUMNS)
        return f"{head}{body}{tail}"

    out = _CREATE_TABLE_RE.sub(repl, out)
    if seed_activity and "活动优秀个人评选" not in out:
        out = out.rstrip() + "\n" + _VOTE_ACTIVITY_SEED
    return out


def ensure_exam_core_sql(sql: str, *, enabled: bool, gate_ticket: bool = False) -> str:
    """exam 能力开启时幂等补考试核心表；LABSAFE 闸门再补准入卷种子。"""
    if not enabled:
        return sql
    out = sql
    if not re.search(r"(?i)CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+`?exam_question`?\b", out):
        out = out.rstrip() + "\n" + _EXAM_CORE_DDL
    elif "gate_ticket" not in out:
        out = out.replace(
            "max_attempts INT NOT NULL DEFAULT 0,\n  created_at DATETIME DEFAULT CURRENT_TIMESTAMP\n);\n\nCREATE TABLE IF NOT EXISTS exam_paper_question",
            "max_attempts INT NOT NULL DEFAULT 0,\n"
            "  gate_ticket TINYINT NOT NULL DEFAULT 0,\n"
            "  pass_score INT NOT NULL DEFAULT 60,\n"
            "  created_at DATETIME DEFAULT CURRENT_TIMESTAMP\n);\n\nCREATE TABLE IF NOT EXISTS exam_paper_question",
        )
    if gate_ticket and "实验室安全准入考试卷" not in out:
        out = out.rstrip() + "\n" + _EXAM_LABSAFE_GATE_SEED
    return out


def ensure_dm_sql(sql: str, *, enabled: bool) -> str:
    """能力开启时幂等补私信表与演示种子；未开启不注入。"""
    if not enabled:
        return sql
    out = sql
    if not re.search(r"(?i)CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+`?sys_dm_message`?\b", out):
        out = out.rstrip() + "\n" + _DM_DDL
    if "sys_dm_message" in out and "用户乙" not in out:
        out = out.rstrip() + "\n" + _DM_SEED
    return out


_FAVORITE_DDL = """
CREATE TABLE IF NOT EXISTS user_favorite (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  username VARCHAR(64) NOT NULL,
  item_id BIGINT NOT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uk_fav_user_item (username, item_id),
  KEY idx_fav_user (username, id)
);
"""

_POST_LIKE_DDL = """
CREATE TABLE IF NOT EXISTS user_post_like (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  username VARCHAR(64) NOT NULL,
  item_id BIGINT NOT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uk_like_user_item (username, item_id),
  KEY idx_like_item (item_id)
);
"""

_CONTENT_REPORT_DDL = """
CREATE TABLE IF NOT EXISTS content_report (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  username VARCHAR(64) NOT NULL,
  target_type VARCHAR(32) NOT NULL DEFAULT 'archive',
  target_id BIGINT NOT NULL,
  reason VARCHAR(512) NOT NULL,
  status VARCHAR(32) NOT NULL DEFAULT 'pending',
  handler VARCHAR(64) DEFAULT '',
  handle_note VARCHAR(512) DEFAULT '',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  handled_at DATETIME NULL,
  KEY idx_creport_status (status, id),
  KEY idx_creport_target (target_type, target_id)
);
"""


def ensure_favorites_sql(sql: str, *, enabled: bool) -> str:
    """交易收藏表；未开启不注入。"""
    if not enabled:
        return sql
    if re.search(r"(?i)CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+`?user_favorite`?\b", sql):
        return sql
    return sql.rstrip() + "\n" + _FAVORITE_DDL


def ensure_post_like_sql(sql: str, *, enabled: bool, item_table: str | None = None) -> str:
    """点赞表；开题挂 post_like 才注入。like_count 列由 FavoriteStore 运行时 ensure。"""
    del item_table  # 列由运行时补，避免各 MySQL 版本 ALTER 方言差异
    if not enabled:
        return sql
    if re.search(r"(?i)CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+`?user_post_like`?\b", sql):
        return sql
    return sql.rstrip() + "\n" + _POST_LIKE_DDL


def ensure_content_report_sql(sql: str, *, enabled: bool) -> str:
    """内容举报表；开题挂 content_report 才注入。"""
    if not enabled:
        return sql
    if re.search(r"(?i)CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+`?content_report`?\b", sql):
        return sql
    return sql.rstrip() + "\n" + _CONTENT_REPORT_DDL




_STAFF_ROSTER_DDL = """
CREATE TABLE IF NOT EXISTS staff_roster (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  username VARCHAR(64) NOT NULL,
  work_date DATE NOT NULL,
  shift_label VARCHAR(64) NOT NULL DEFAULT '全天',
  note VARCHAR(256) DEFAULT '',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uk_roster_user_day (username, work_date),
  KEY idx_roster_date (work_date)
);
"""

_STAFF_ROSTER_SEED = """
INSERT INTO staff_roster (username, work_date, shift_label, note)
SELECT 'subadmin', CURDATE(), '全天', '当日值班'
FROM DUAL WHERE NOT EXISTS (
  SELECT 1 FROM staff_roster WHERE username='subadmin' AND work_date=CURDATE()
);
INSERT INTO staff_roster (username, work_date, shift_label, note)
SELECT 'subadmin', DATE_ADD(CURDATE(), INTERVAL 1 DAY), '全天', '次日值班'
FROM DUAL WHERE NOT EXISTS (
  SELECT 1 FROM staff_roster WHERE username='subadmin' AND work_date=DATE_ADD(CURDATE(), INTERVAL 1 DAY)
);
"""


def ensure_staff_roster_sql(sql: str, *, enabled: bool) -> str:
    """周排班表+种子；开题挂 staff_roster 才注入。"""
    if not enabled:
        return sql
    if re.search(r"(?i)CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+`?staff_roster`?\b", sql):
        return sql
    return sql.rstrip() + "\n" + _STAFF_ROSTER_DDL + "\n" + _STAFF_ROSTER_SEED


_MESSAGE_TEMPLATE_DDL = """
CREATE TABLE IF NOT EXISTS sys_message_template (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  code VARCHAR(64) NOT NULL,
  title VARCHAR(128) NOT NULL,
  body VARCHAR(512) NOT NULL,
  enabled TINYINT NOT NULL DEFAULT 1,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uk_msg_tpl_code (code)
);
"""

_MESSAGE_TEMPLATE_SEED = """
INSERT INTO sys_message_template (code, title, body, enabled)
SELECT 'ticket_approved', '审核已通过', '「{{subject}}」已通过{{note_suffix}}', 1
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_message_template WHERE code='ticket_approved');
INSERT INTO sys_message_template (code, title, body, enabled)
SELECT 'ticket_rejected', '审核未通过', '「{{subject}}」已驳回{{note_suffix}}', 1
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_message_template WHERE code='ticket_rejected');
"""


def ensure_message_template_sql(sql: str, *, enabled: bool) -> str:
    """消息模板表+种子；开题挂 message_template 才注入。"""
    if not enabled:
        return sql
    if re.search(r"(?i)CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+`?sys_message_template`?\b", sql):
        return sql
    return sql.rstrip() + "\n" + _MESSAGE_TEMPLATE_DDL + "\n" + _MESSAGE_TEMPLATE_SEED


_BOOK_SUGGEST_DDL = """
CREATE TABLE IF NOT EXISTS book_suggest (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  username VARCHAR(64) NOT NULL,
  title VARCHAR(200) NOT NULL,
  isbn VARCHAR(32) DEFAULT '',
  author VARCHAR(100) DEFAULT '',
  reason VARCHAR(512) DEFAULT '',
  status VARCHAR(16) NOT NULL DEFAULT 'pending',
  handler VARCHAR(64) DEFAULT '',
  handle_note VARCHAR(512) DEFAULT '',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  handled_at DATETIME NULL,
  KEY idx_bs_user (username, id),
  KEY idx_bs_status (status, id)
);
"""

_BOOK_SUGGEST_SEED = """
INSERT INTO book_suggest (username, title, isbn, author, reason, status)
SELECT 'user', '数据结构与算法分析', '9787111213826', 'Weiss', '课程参考书', 'pending'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM book_suggest WHERE username='user' AND title='数据结构与算法分析');
"""


def ensure_book_suggest_sql(sql: str, *, enabled: bool) -> str:
    """图书荐购表+种子；开题挂 book_suggest 才注入。"""
    if not enabled:
        return sql
    if re.search(r"(?i)CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+`?book_suggest`?\b", sql):
        return sql
    return sql.rstrip() + "\n" + _BOOK_SUGGEST_DDL + "\n" + _BOOK_SUGGEST_SEED


_AUDIT_LOG_DDL = """
CREATE TABLE IF NOT EXISTS sys_audit_log (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  username VARCHAR(64) NOT NULL,
  action VARCHAR(64) NOT NULL,
  target_type VARCHAR(32) DEFAULT '',
  target_id VARCHAR(64) DEFAULT '',
  detail VARCHAR(512) DEFAULT '',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  KEY idx_audit_created (created_at, id),
  KEY idx_audit_user (username)
);
"""


def ensure_audit_log_sql(sql: str, *, enabled: bool) -> str:
    """操作审计表；开题挂 audit_log 才注入。"""
    if not enabled:
        return sql
    if re.search(r"(?i)CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+`?sys_audit_log`?\b", sql):
        return sql
    return sql.rstrip() + "\n" + _AUDIT_LOG_DDL

_BROWSE_HISTORY_DDL = """
CREATE TABLE IF NOT EXISTS user_browse_history (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  username VARCHAR(64) NOT NULL,
  item_id BIGINT NOT NULL,
  viewed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uk_browse_user_item (username, item_id),
  KEY idx_browse_user_time (username, viewed_at)
);
"""


def ensure_browse_history_sql(sql: str, *, enabled: bool) -> str:
    """浏览足迹表；仅开题挂 browse_history 时注入。"""
    if not enabled:
        return sql
    if re.search(r"(?i)CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+`?user_browse_history`?\b", sql):
        return sql
    return sql.rstrip() + "\n" + _BROWSE_HISTORY_DDL


_ARCHIVE_LOG_DDL = """
CREATE TABLE IF NOT EXISTS archive_log (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  item_id BIGINT NOT NULL,
  username VARCHAR(64) NOT NULL,
  log_date DATE NOT NULL,
  log_type VARCHAR(32) NOT NULL DEFAULT 'checkin',
  payload_json TEXT,
  abnormal TINYINT DEFAULT 0,
  remark VARCHAR(512) DEFAULT '',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  KEY idx_alog_item_date (item_id, log_date),
  KEY idx_alog_date_type (log_date, log_type),
  KEY idx_alog_user (username, id)
);
"""


def ensure_archive_log_sql(sql: str, *, enabled: bool) -> str:
    """档案打卡/随访表；archive_log 能力开启时注入。"""
    if not enabled:
        return sql
    if re.search(r"(?i)CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+`?archive_log`?\b", sql):
        return sql
    return sql.rstrip() + "\n" + _ARCHIVE_LOG_DDL


SOFT_DELETE_COLUMNS: list[tuple[str, str]] = [
    ("deleted_at", "DATETIME NULL"),
]


def ensure_soft_delete_columns(
    sql: str,
    *,
    enabled: bool,
    item_table: str | None,
) -> str:
    """archive.softDelete 开时档案主表须有 deleted_at（与 yml archive-soft-delete 对齐）。"""
    if not enabled:
        return sql
    t = (item_table or "").strip()
    if not t or not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", t):
        return sql

    def repl(m: re.Match[str]) -> str:
        head, table, body, tail = m.group(1), m.group(2), m.group(3), m.group(4)
        if table.lower() != t.lower():
            return m.group(0)
        body = _inject_missing_columns(body, SOFT_DELETE_COLUMNS)
        return f"{head}{body}{tail}"

    return _CREATE_TABLE_RE.sub(repl, sql)


NOTICE_PINNED_COLUMNS: list[tuple[str, str]] = [
    ("pinned", "TINYINT NOT NULL DEFAULT 0"),
]


def ensure_notice_pinned_column(sql: str, *, enabled: bool = True) -> str:
    """公告表幂等补 pinned，避免依赖学生包运行时 ALTER。"""
    if not enabled:
        return sql
    if not re.search(r"(?i)CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+`?sys_notice`?\b", sql):
        return sql

    def repl(m: re.Match[str]) -> str:
        head, table, body, tail = m.group(1), m.group(2), m.group(3), m.group(4)
        if table.lower() != "sys_notice":
            return m.group(0)
        body = _inject_missing_columns(body, NOTICE_PINNED_COLUMNS)
        return f"{head}{body}{tail}"

    return _CREATE_TABLE_RE.sub(repl, sql)


GALLERY_COLUMNS: list[tuple[str, str]] = [
    ("gallery_json", "TEXT NULL"),
]

DETAIL_ATTR_COLUMNS: list[tuple[str, str]] = [
    ("detail_json", "TEXT NULL"),
]


def ensure_detail_attrs_sql(sql: str, *, enabled: bool, item_table: str | None) -> str:
    """商品详情属性 JSON。开题详情括号里列出的品牌、材质等写入此列。"""
    if not enabled:
        return sql
    t = (item_table or "").strip()
    if not t or not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", t):
        return sql

    def repl(m: re.Match[str]) -> str:
        head, table, body, tail = m.group(1), m.group(2), m.group(3), m.group(4)
        if table.lower() != t.lower():
            return m.group(0)
        body = _inject_missing_columns(body, DETAIL_ATTR_COLUMNS)
        return f"{head}{body}{tail}"

    return _CREATE_TABLE_RE.sub(repl, sql)


def ensure_gallery_sql(sql: str, *, enabled: bool, item_table: str | None) -> str:
    """档案主表补 gallery_json；仅 gallery 能力开启时注入。"""
    if not enabled:
        return sql
    t = (item_table or "").strip()
    if not t or not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", t):
        return sql

    def repl(m: re.Match[str]) -> str:
        head, table, body, tail = m.group(1), m.group(2), m.group(3), m.group(4)
        if table.lower() != t.lower():
            return m.group(0)
        body = _inject_missing_columns(body, GALLERY_COLUMNS)
        return f"{head}{body}{tail}"

    return _CREATE_TABLE_RE.sub(repl, sql)


ROOM_EQUIPMENT_COLUMNS: list[tuple[str, str]] = [
    ("equipment_json", "TEXT NULL"),
]

_EQUIPMENT_DICT_DDL = """
CREATE TABLE IF NOT EXISTS sys_equipment_dict (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  name VARCHAR(64) NOT NULL,
  sort_order INT NOT NULL DEFAULT 0,
  enabled TINYINT NOT NULL DEFAULT 1,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uk_equip_name (name)
);
"""

_EQUIPMENT_DICT_SEED = """
INSERT INTO sys_equipment_dict (name, sort_order, enabled)
SELECT '投影仪', 10, 1 FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_equipment_dict WHERE name='投影仪');
INSERT INTO sys_equipment_dict (name, sort_order, enabled)
SELECT '音响', 20, 1 FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_equipment_dict WHERE name='音响');
INSERT INTO sys_equipment_dict (name, sort_order, enabled)
SELECT '白板', 30, 1 FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_equipment_dict WHERE name='白板');
INSERT INTO sys_equipment_dict (name, sort_order, enabled)
SELECT '视频会议终端', 40, 1 FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_equipment_dict WHERE name='视频会议终端');
INSERT INTO sys_equipment_dict (name, sort_order, enabled)
SELECT '投屏线', 50, 1 FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_equipment_dict WHERE name='投屏线');
"""


def ensure_room_equipment_sql(sql: str, *, enabled: bool, item_table: str | None) -> str:
    """档案主表补 equipment_json + 设备字典；仅 room_equipment 开启时注入。"""
    if not enabled:
        return sql
    t = (item_table or "").strip()
    out = sql
    if t and re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", t):

        def repl(m: re.Match[str]) -> str:
            head, table, body, tail = m.group(1), m.group(2), m.group(3), m.group(4)
            if table.lower() != t.lower():
                return m.group(0)
            body = _inject_missing_columns(body, ROOM_EQUIPMENT_COLUMNS)
            return f"{head}{body}{tail}"

        out = _CREATE_TABLE_RE.sub(repl, out)
    if not re.search(r"(?i)CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+`?sys_equipment_dict`?\b", out):
        out = out.rstrip() + "\n" + _EQUIPMENT_DICT_DDL + "\n" + _EQUIPMENT_DICT_SEED
    if t and re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", t):
        seed_upd = (
            f"\nUPDATE `{t}` SET equipment_json="
            f"""'["投影仪","音响","白板"]' """
            f"WHERE id=1 AND (equipment_json IS NULL OR equipment_json='' OR equipment_json='[]');\n"
        )
        if f"UPDATE `{t}` SET equipment_json=" not in out:
            out = out.rstrip() + seed_upd
    return out


CHECKIN_CODE_COLUMNS: list[tuple[str, str]] = [
    ("checkin_code", "VARCHAR(16) NOT NULL DEFAULT ''"),
]

OWNER_USERNAME_COLUMNS: list[tuple[str, str]] = [
    ("owner_username", "VARCHAR(64) NOT NULL DEFAULT ''"),
]

MUTEX_CODE_COLUMNS: list[tuple[str, str]] = [
    ("mutex_code", "VARCHAR(32) NOT NULL DEFAULT ''"),
]


APPLY_DEADLINE_COLUMNS: list[tuple[str, str]] = [
    ("apply_deadline_at", "DATETIME NULL"),
]

SCHEDULE_COLUMNS: list[tuple[str, str]] = [
    ("start_at", "DATETIME NULL"),
    ("end_at", "DATETIME NULL"),
]



FLASH_PRICE_COLUMNS: list[tuple[str, str]] = [
    ("promo_price", "DECIMAL(10,2) NULL"),
    ("promo_start", "DATETIME NULL"),
    ("promo_end", "DATETIME NULL"),
]


def ensure_flash_price_columns(sql: str, *, enabled: bool, item_table: str | None) -> str:
    """限时购列；开题挂 flash_price 才注入档案表。"""
    if not enabled:
        return sql
    t = (item_table or "").strip()
    if not t or not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", t):
        return sql

    def repl(m: re.Match[str]) -> str:
        head, table, body, tail = m.group(1), m.group(2), m.group(3), m.group(4)
        if table.lower() != t.lower():
            return m.group(0)
        body = _inject_missing_columns(body, FLASH_PRICE_COLUMNS)
        return f"{head}{body}{tail}"

    return _CREATE_TABLE_RE.sub(repl, sql)


PRODUCT_SPEC_COLUMNS: list[tuple[str, str]] = [
    ("spec_note", "VARCHAR(128) DEFAULT ''"),
]


def ensure_product_spec_columns(sql: str, *, enabled: bool, item_table: str | None) -> str:
    """商品规格说明列；挂 product_spec 时注入（FOOD 语义列已是 spec_note 则跳过）。"""
    if not enabled:
        return sql
    t = (item_table or "").strip()
    if not t or not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", t):
        return sql

    def repl(m: re.Match[str]) -> str:
        head, table, body, tail = m.group(1), m.group(2), m.group(3), m.group(4)
        if table.lower() != t.lower():
            return m.group(0)
        body = _inject_missing_columns(body, PRODUCT_SPEC_COLUMNS)
        return f"{head}{body}{tail}"

    return _CREATE_TABLE_RE.sub(repl, sql)


CATEGORY_DIMENSION_COLUMNS: list[tuple[str, str]] = [
    ("dimension", "VARCHAR(64) NOT NULL DEFAULT ''"),
]


def ensure_multi_category_sql(
    sql: str,
    *,
    enabled: bool,
    item_table: str | None = "product",
    junction_table: str = "product_category",
    axis_seed_sql: str = "",
) -> str:
    """多维分类：category.dimension + 条目-分类关联表。未开不加。"""
    if not enabled:
        return sql
    t = (item_table or "product").strip()
    junc = (junction_table or "product_category").strip()
    if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", junc):
        junc = "product_category"

    def cat_repl(m: re.Match[str]) -> str:
        head, table, body, tail = m.group(1), m.group(2), m.group(3), m.group(4)
        if table.lower() != "category":
            return m.group(0)
        body = _inject_missing_columns(body, CATEGORY_DIMENSION_COLUMNS)
        return f"{head}{body}{tail}"

    out = _CREATE_TABLE_RE.sub(cat_repl, sql)
    if not re.search(
        rf"(?i)CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+`?{re.escape(junc)}`?\b", out
    ):
        ddl = f"""
CREATE TABLE IF NOT EXISTS {junc} (
  item_id BIGINT NOT NULL,
  category_id BIGINT NOT NULL,
  PRIMARY KEY (item_id, category_id),
  KEY idx_{junc}_cat (category_id)
);
"""
        out = out.rstrip() + "\n" + ddl
    # 种子：开题解析出维度取值时换掉默认分类名；否则补通用维度演示行
    if (axis_seed_sql or "").strip():
        seed = axis_seed_sql if axis_seed_sql.endswith("\n") else axis_seed_sql + "\n"
    else:
        seed = """
UPDATE category SET dimension='品类' WHERE (dimension IS NULL OR dimension='') AND id IN (1,2,3);
INSERT IGNORE INTO category (id, name, dimension) VALUES
(10, '自用', '用途'), (11, '练手', '用途'),
(12, '入门', '目标'), (13, '进阶', '目标');
"""
        if t and re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", t):
            seed += f"""
INSERT IGNORE INTO {junc} (item_id, category_id)
SELECT id, category_id FROM {t} WHERE category_id IS NOT NULL AND category_id > 0;
INSERT IGNORE INTO {junc} (item_id, category_id) VALUES (1, 10), (1, 12), (2, 11), (2, 13);
"""
    out = out.rstrip() + "\n" + seed
    return out


def ensure_product_tags_sql(sql: str, *, enabled: bool) -> str:
    """商城标签表 + 商品-标签关联。未开不加。论坛自有 tag/post_tag，勿对本岛调用。"""
    if not enabled:
        return sql
    out = sql
    if not re.search(r"(?i)CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+`?tag`?\b", out):
        out = out.rstrip() + """
CREATE TABLE IF NOT EXISTS tag (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  name VARCHAR(64) NOT NULL UNIQUE
);
"""
    if not re.search(
        r"(?i)CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+`?product_tag`?\b", out
    ):
        out = out.rstrip() + """
CREATE TABLE IF NOT EXISTS product_tag (
  item_id BIGINT NOT NULL,
  tag_id BIGINT NOT NULL,
  PRIMARY KEY (item_id, tag_id)
);
"""
    seed = """
INSERT IGNORE INTO tag (id, name) VALUES
(1, '热门'), (2, '新品'), (3, '包邮'), (4, '自营');
INSERT IGNORE INTO product_tag (item_id, tag_id) VALUES
(1, 1), (1, 3), (2, 2), (2, 4), (3, 1);
"""
    out = out.rstrip() + "\n" + seed
    return out


ORDER_LINE_CUSTOM_COLUMNS: list[tuple[str, str]] = [
    ("custom_text", "VARCHAR(200) DEFAULT ''"),
    ("spec_choice", "VARCHAR(120) DEFAULT ''"),
    ("attach_url", "VARCHAR(255) DEFAULT ''"),
]


def ensure_order_line_custom_columns(sql: str, *, enabled: bool, with_spec: bool = False) -> str:
    """订单明细快照列。未开则不加。有规格时再加选项表，刻字仍是手填。"""
    if not enabled:
        return sql

    def repl(m: re.Match[str]) -> str:
        head, table, body, tail = m.group(1), m.group(2), m.group(3), m.group(4)
        if table.lower() != "order_line":
            return m.group(0)
        body = _inject_missing_columns(body, ORDER_LINE_CUSTOM_COLUMNS)
        return f"{head}{body}{tail}"

    out = _CREATE_TABLE_RE.sub(repl, sql)
    if not with_spec:
        return out
    if re.search(r"(?i)CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+`?line_spec_option`?\b", out):
        return out
    ddl = """\
CREATE TABLE IF NOT EXISTS line_spec_option (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  label VARCHAR(64) NOT NULL,
  enabled TINYINT NOT NULL DEFAULT 1,
  sort_no INT NOT NULL DEFAULT 0
);
INSERT INTO line_spec_option (id, label, enabled, sort_no)
SELECT 1, '宋体', 1, 10 FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM line_spec_option WHERE id=1);
INSERT INTO line_spec_option (id, label, enabled, sort_no)
SELECT 2, '红色', 1, 20 FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM line_spec_option WHERE id=2);
INSERT INTO line_spec_option (id, label, enabled, sort_no)
SELECT 3, '大号', 1, 30 FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM line_spec_option WHERE id=3);
"""
    return out.rstrip() + "\n" + ddl


ORDER_WINDOW_COLUMNS: list[tuple[str, str]] = [
    ("fulfill_mode", "VARCHAR(16) DEFAULT ''"),
    ("delivery_on", "DATE NULL"),
    ("slot_id", "BIGINT NULL"),
    ("slot_label", "VARCHAR(64) DEFAULT ''"),
    ("price_rate", "DECIMAL(6,2) NOT NULL DEFAULT 1.00"),
]

_DELIVERY_WINDOW_DDL = """
CREATE TABLE IF NOT EXISTS delivery_slot (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  label VARCHAR(64) NOT NULL,
  start_hm VARCHAR(8) NOT NULL DEFAULT '',
  end_hm VARCHAR(8) NOT NULL DEFAULT '',
  capacity INT NOT NULL DEFAULT 1,
  fulfill_mode VARCHAR(16) NOT NULL DEFAULT 'preorder',
  cutoff_hm VARCHAR(8) NOT NULL DEFAULT '',
  enabled TINYINT NOT NULL DEFAULT 1,
  sort_no INT NOT NULL DEFAULT 0,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS price_span (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  name VARCHAR(64) NOT NULL,
  date_from DATE NOT NULL,
  date_to DATE NOT NULL,
  rate DECIMAL(6,2) NOT NULL DEFAULT 1.00,
  enabled TINYINT NOT NULL DEFAULT 1,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
"""

_DELIVERY_WINDOW_SEED = """
INSERT INTO delivery_slot (id, label, start_hm, end_hm, capacity, fulfill_mode, cutoff_hm, enabled, sort_no)
SELECT 1, '上午档', '09:00', '12:00', 8, 'same_day', '11:00', 1, 10 FROM DUAL
WHERE NOT EXISTS (SELECT 1 FROM delivery_slot WHERE id=1);
INSERT INTO delivery_slot (id, label, start_hm, end_hm, capacity, fulfill_mode, cutoff_hm, enabled, sort_no)
SELECT 2, '下午档', '14:00', '18:00', 8, 'preorder', '', 1, 20 FROM DUAL
WHERE NOT EXISTS (SELECT 1 FROM delivery_slot WHERE id=2);
INSERT INTO price_span (id, name, date_from, date_to, rate, enabled)
SELECT 1, '情人节', '2026-02-10', '2026-02-14', 1.50, 1 FROM DUAL
WHERE NOT EXISTS (SELECT 1 FROM price_span WHERE id=1);
UPDATE biz_order
SET fulfill_mode='preorder', delivery_on='2026-09-26', slot_id=2, slot_label='下午档', price_rate=1.00
WHERE id=1 AND (slot_id IS NULL OR slot_id=0);
"""


def ensure_delivery_window_sql(sql: str, *, enabled: bool) -> str:
    """配送时段表、节日加价表、订单头快照列。未开不加。"""
    if not enabled:
        return sql

    def repl(m: re.Match[str]) -> str:
        head, table, body, tail = m.group(1), m.group(2), m.group(3), m.group(4)
        if table.lower() != "biz_order":
            return m.group(0)
        body = _inject_missing_columns(body, ORDER_WINDOW_COLUMNS)
        return f"{head}{body}{tail}"

    out = _CREATE_TABLE_RE.sub(repl, sql)
    if not re.search(r"(?i)CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+`?delivery_slot`?\b", out):
        out = out.rstrip() + "\n" + _DELIVERY_WINDOW_DDL + "\n" + _DELIVERY_WINDOW_SEED
    return out


PRODUCT_GATE_COLUMNS: list[tuple[str, str]] = [
    ("need_permit", "TINYINT NOT NULL DEFAULT 0"),
    ("month_limit", "INT NOT NULL DEFAULT 0"),
]

_PURCHASE_GATE_DDL = """\
CREATE TABLE IF NOT EXISTS purchase_permit (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  username VARCHAR(64) NOT NULL,
  item_id BIGINT NULL,
  category_id BIGINT NULL,
  image_url VARCHAR(255) NOT NULL DEFAULT '',
  status VARCHAR(16) NOT NULL DEFAULT 'pending',
  reviewer VARCHAR(64) DEFAULT '',
  reject_reason VARCHAR(255) DEFAULT '',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  reviewed_at DATETIME NULL,
  KEY idx_permit_user_item (username, item_id),
  KEY idx_permit_user_cat (username, category_id)
);
"""


def ensure_purchase_gate_sql(sql: str, *, enabled: bool, item_table: str | None) -> str:
    """购买审核表与商品上的开关、月限。未开不加列。"""
    if not enabled:
        return sql
    t = (item_table or "").strip()
    if not t or not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", t):
        return sql

    def repl(m: re.Match[str]) -> str:
        head, table, body, tail = m.group(1), m.group(2), m.group(3), m.group(4)
        if table.lower() != t.lower():
            return m.group(0)
        body = _inject_missing_columns(body, PRODUCT_GATE_COLUMNS)
        return f"{head}{body}{tail}"

    out = _CREATE_TABLE_RE.sub(repl, sql)
    if re.search(r"(?i)CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+`?purchase_permit`?\b", out):
        return out
    seed = (
        f"UPDATE {t} SET need_permit=1, month_limit=2 WHERE id=1;\n"
        f"UPDATE {t} SET need_permit=0, month_limit=0 WHERE id=2;\n"
        "INSERT INTO purchase_permit (username, item_id, image_url, status)\n"
        "SELECT 'user', 1, '/uploads/seed-permit.png', 'pending' FROM DUAL\n"
        "WHERE NOT EXISTS (SELECT 1 FROM purchase_permit WHERE username='user' AND item_id=1 AND status='pending');\n"
    )
    return out.rstrip() + "\n" + _PURCHASE_GATE_DDL + "\n" + seed


_GROUP_BUY_DDL = """\
CREATE TABLE IF NOT EXISTS group_campaign (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  item_id BIGINT NOT NULL,
  target_size INT NOT NULL,
  deadline DATETIME NOT NULL,
  status VARCHAR(16) NOT NULL DEFAULT 'open',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  KEY idx_group_item (item_id, status)
);
CREATE TABLE IF NOT EXISTS group_member (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  campaign_id BIGINT NOT NULL,
  order_id BIGINT NOT NULL,
  username VARCHAR(64) NOT NULL,
  UNIQUE KEY uk_group_user (campaign_id, username),
  KEY idx_group_order (order_id)
);
"""

_GROUP_BUY_SEED = """\
INSERT INTO group_campaign (item_id, target_size, deadline, status)
SELECT 1, 3, DATE_ADD(NOW(), INTERVAL 2 DAY), 'open' FROM DUAL
WHERE NOT EXISTS (SELECT 1 FROM group_campaign WHERE item_id=1 AND status='open');
INSERT INTO group_member (campaign_id, order_id, username)
SELECT c.id, 1, 'demo_joiner' FROM group_campaign c
WHERE c.item_id=1 AND c.status='open'
AND NOT EXISTS (SELECT 1 FROM group_member m WHERE m.campaign_id=c.id AND m.username='demo_joiner')
LIMIT 1;
INSERT INTO group_campaign (item_id, target_size, deadline, status)
SELECT 2, 3, DATE_SUB(NOW(), INTERVAL 1 DAY), 'failed' FROM DUAL
WHERE NOT EXISTS (SELECT 1 FROM group_campaign WHERE status='failed');
"""


def ensure_group_buy_sql(sql: str, *, enabled: bool) -> str:
    """拼团两张表。未开不加，活动报名和拼车也不会走到这里。"""
    if not enabled:
        return sql
    if re.search(r"(?i)CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+`?group_campaign`?\b", sql):
        return sql
    return sql.rstrip() + "\n" + _GROUP_BUY_DDL + "\n" + _GROUP_BUY_SEED


PRODUCT_PITY_COLUMNS: list[tuple[str, str]] = [
    ("pity_n", "INT NOT NULL DEFAULT 0"),
]

ORDER_LINE_DRAW_COLUMNS: list[tuple[str, str]] = [
    ("draw_title", "VARCHAR(500) NOT NULL DEFAULT ''"),
    ("draw_hidden", "TINYINT NOT NULL DEFAULT 0"),
]

_BLIND_BOX_DDL = """\
CREATE TABLE IF NOT EXISTS blind_pool (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  box_id BIGINT NOT NULL,
  prize_id BIGINT NOT NULL,
  weight INT NOT NULL,
  hidden TINYINT NOT NULL DEFAULT 0,
  enabled TINYINT NOT NULL DEFAULT 1,
  UNIQUE KEY uk_box_prize (box_id, prize_id)
);
CREATE TABLE IF NOT EXISTS blind_pity (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  username VARCHAR(64) NOT NULL,
  box_id BIGINT NOT NULL,
  draws INT NOT NULL DEFAULT 0,
  hidden_got TINYINT NOT NULL DEFAULT 0,
  UNIQUE KEY uk_user_box (username, box_id)
);
"""


def ensure_blind_box_sql(sql: str, *, enabled: bool, item_table: str | None) -> str:
    """盲盒奖池、保底计数、盒子上的保底次数。未开不加。"""
    if not enabled:
        return sql
    t = (item_table or "").strip()
    if not t or not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", t):
        return sql

    def repl(m: re.Match[str]) -> str:
        head, table, body, tail = m.group(1), m.group(2), m.group(3), m.group(4)
        low = table.lower()
        if low == t.lower():
            body = _inject_missing_columns(body, PRODUCT_PITY_COLUMNS)
        elif low == "order_line":
            body = _inject_missing_columns(body, ORDER_LINE_DRAW_COLUMNS)
        else:
            return m.group(0)
        return f"{head}{body}{tail}"

    out = _CREATE_TABLE_RE.sub(repl, sql)
    if re.search(r"(?i)CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+`?blind_pool`?\b", out):
        return out
    seed = (
        f"UPDATE {t} SET pity_n=3 WHERE id=1;\n"
        "INSERT INTO blind_pool (box_id, prize_id, weight, hidden, enabled)\n"
        "SELECT 1, 2, 70, 0, 1 FROM DUAL\n"
        "WHERE NOT EXISTS (SELECT 1 FROM blind_pool WHERE box_id=1 AND prize_id=2);\n"
        "INSERT INTO blind_pool (box_id, prize_id, weight, hidden, enabled)\n"
        "SELECT 1, 3, 25, 0, 1 FROM DUAL\n"
        "WHERE NOT EXISTS (SELECT 1 FROM blind_pool WHERE box_id=1 AND prize_id=3);\n"
        "INSERT INTO blind_pool (box_id, prize_id, weight, hidden, enabled)\n"
        "SELECT 1, 4, 5, 1, 1 FROM DUAL\n"
        "WHERE NOT EXISTS (SELECT 1 FROM blind_pool WHERE box_id=1 AND prize_id=4);\n"
    )
    return out.rstrip() + "\n" + _BLIND_BOX_DDL + "\n" + seed


_CONSIGN_DDL = """
CREATE TABLE IF NOT EXISTS consign_item (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  username VARCHAR(64) NOT NULL,
  title VARCHAR(200) NOT NULL DEFAULT '',
  expect_yuan DECIMAL(10,2) NOT NULL DEFAULT 0,
  condition_note VARCHAR(64) NOT NULL DEFAULT '',
  status VARCHAR(16) NOT NULL DEFAULT 'pending',
  reject_reason VARCHAR(255) NOT NULL DEFAULT '',
  product_id BIGINT NULL,
  fee_rate DECIMAL(6,4) NOT NULL DEFAULT 0.1000,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS consign_ledger (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  consign_id BIGINT NOT NULL,
  order_id BIGINT NOT NULL,
  username VARCHAR(64) NOT NULL,
  gross_yuan DECIMAL(10,2) NOT NULL DEFAULT 0,
  fee_rate DECIMAL(6,4) NOT NULL DEFAULT 0,
  payout_yuan DECIMAL(10,2) NOT NULL DEFAULT 0,
  withdraw_status VARCHAR(16) NOT NULL DEFAULT 'ready',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uk_consign_order (consign_id, order_id)
);
"""


def ensure_consign_sql(sql: str, *, enabled: bool, item_table: str | None) -> str:
    """寄卖单、成交账。未开不加。成色列不在这里注入。"""
    if not enabled:
        return sql
    t = (item_table or "").strip()
    if not t or not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", t):
        return sql
    if re.search(r"(?i)CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+`?consign_item`?\b", sql):
        return sql
    seed = f"""INSERT INTO consign_item (id, username, title, expect_yuan, condition_note, status, fee_rate)
SELECT 9, '', '', 0, '', 'rate', 0.1000 FROM DUAL
WHERE NOT EXISTS (SELECT 1 FROM consign_item WHERE status='rate');
INSERT INTO consign_item (id, username, title, expect_yuan, condition_note, status, fee_rate)
SELECT 1, 'user', '耳机', 80.00, '九成新', 'pending', 0.1000 FROM DUAL
WHERE NOT EXISTS (SELECT 1 FROM consign_item WHERE id=1);
INSERT IGNORE INTO {t} (id, title, author, isbn, category_id, stock, status) VALUES
(5, '台灯', '45.00', 'CS-05', 2, 1, 'available');
INSERT INTO consign_item (id, username, title, expect_yuan, condition_note, status, product_id, fee_rate)
SELECT 2, 'user', '台灯', 45.00, '八成新', 'on_sale', 5, 0.1000 FROM DUAL
WHERE NOT EXISTS (SELECT 1 FROM consign_item WHERE id=2);
INSERT IGNORE INTO {t} (id, title, author, isbn, category_id, stock, status) VALUES
(6, '键盘', '100.00', 'CS-06', 2, 0, 'unavailable');
INSERT INTO consign_item (id, username, title, expect_yuan, condition_note, status, product_id, fee_rate)
SELECT 3, 'user', '键盘', 100.00, '九成新', 'sold', 6, 0.1000 FROM DUAL
WHERE NOT EXISTS (SELECT 1 FROM consign_item WHERE id=3);
INSERT IGNORE INTO biz_order (id, username, status, total_yuan, remark, receiver_name, receiver_phone, address_line, delivery_type) VALUES
(2, 'user', 'completed', 100.00, '', '王先生', '13800000002', '示例小区 3 栋 1201', '配送到家');
INSERT IGNORE INTO order_line (id, order_id, item_id, title, price_yuan, qty) VALUES
(2, 2, 6, '键盘', 100.00, 1);
INSERT INTO consign_ledger (id, consign_id, order_id, username, gross_yuan, fee_rate, payout_yuan, withdraw_status)
SELECT 1, 3, 2, 'user', 100.00, 0.1000, 90.00, 'ready' FROM DUAL
WHERE NOT EXISTS (SELECT 1 FROM consign_ledger WHERE id=1);
"""
    return sql.rstrip() + "\n" + _CONSIGN_DDL + "\n" + seed


PRODUCT_WEIGH_COLUMNS: list[tuple[str, str]] = [
    ("sell_by_weight", "TINYINT NOT NULL DEFAULT 0"),
    ("weight_unit", "VARCHAR(8) NOT NULL DEFAULT ''"),
]

ORDER_LINE_WEIGHT_COLUMNS: list[tuple[str, str]] = [
    ("weight_qty", "DECIMAL(10,3) NULL"),
]

_WEIGH_SALE_DDL = """
CREATE TABLE IF NOT EXISTS loss_policy (
  id BIGINT PRIMARY KEY,
  enabled TINYINT NOT NULL DEFAULT 0,
  cap_yuan DECIMAL(10,2) NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS loss_claim (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  username VARCHAR(64) NOT NULL,
  order_id BIGINT NOT NULL,
  amount_yuan DECIMAL(10,2) NOT NULL DEFAULT 0,
  reason VARCHAR(255) NOT NULL DEFAULT '',
  status VARCHAR(16) NOT NULL DEFAULT 'pending',
  paid_yuan DECIMAL(10,2) NOT NULL DEFAULT 0,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
"""


def ensure_weigh_sale_sql(sql: str, *, enabled: bool, item_table: str | None) -> str:
    """重量列、次日达时段、损耗赔付。未开不加。"""
    if not enabled:
        return sql
    t = (item_table or "").strip()
    if not t or not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", t):
        return sql

    def repl(m: re.Match[str]) -> str:
        head, table, body, tail = m.group(1), m.group(2), m.group(3), m.group(4)
        low = table.lower()
        if low == t.lower():
            body = _inject_missing_columns(body, PRODUCT_WEIGH_COLUMNS)
        elif low == "order_line":
            body = _inject_missing_columns(body, ORDER_LINE_WEIGHT_COLUMNS)
        elif low == "sys_user":
            body = _inject_missing_columns(body, [("balance_yuan", "DECIMAL(10,2) NOT NULL DEFAULT 0")])
        else:
            return m.group(0)
        return f"{head}{body}{tail}"

    out = _CREATE_TABLE_RE.sub(repl, sql)
    if re.search(r"(?i)CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+`?loss_policy`?\b", out):
        return out
    seed = f"""UPDATE {t} SET sell_by_weight=1, weight_unit='斤' WHERE id=1;
INSERT INTO delivery_slot (id, label, start_hm, end_hm, capacity, fulfill_mode, cutoff_hm, enabled, sort_no)
SELECT 3, '次日达', '09:00', '18:00', 20, 'next_day', '', 1, 30 FROM DUAL
WHERE NOT EXISTS (SELECT 1 FROM delivery_slot WHERE id=3);
INSERT INTO loss_policy (id, enabled, cap_yuan)
SELECT 1, 1, 20.00 FROM DUAL
WHERE NOT EXISTS (SELECT 1 FROM loss_policy WHERE id=1);
"""
    return out.rstrip() + "\n" + _WEIGH_SALE_DDL + "\n" + seed


_SHOOT_DDL = """
CREATE TABLE IF NOT EXISTS service_bundle (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  name VARCHAR(64) NOT NULL,
  price_yuan DECIMAL(10,2) NOT NULL DEFAULT 0,
  detail VARCHAR(255) NOT NULL DEFAULT '',
  enabled TINYINT NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS deliverable (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  reservation_id BIGINT NOT NULL,
  file_url VARCHAR(255) NOT NULL DEFAULT '',
  delivered TINYINT NOT NULL DEFAULT 0,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
"""


def ensure_shoot_sql(sql: str, *, enabled: bool) -> str:
    """套餐与交片。未开不加。摄影师占用仍用 resource_slot。"""
    if not enabled:
        return sql

    def repl(m: re.Match[str]) -> str:
        head, table, body, tail = m.group(1), m.group(2), m.group(3), m.group(4)
        if table.lower() != "reservation":
            return m.group(0)
        body = _inject_missing_columns(
            body,
            [
                ("bundle_id", "BIGINT NULL"),
                ("bundle_yuan", "DECIMAL(10,2) NULL"),
            ],
        )
        return f"{head}{body}{tail}"

    out = _CREATE_TABLE_RE.sub(repl, sql)
    if re.search(r"(?i)CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+`?service_bundle`?\b", out):
        return out
    seed = """INSERT INTO service_bundle (id, name, price_yuan, detail, enabled)
SELECT 1, '证件照', 199.00, '含精修 2 张', 1 FROM DUAL
WHERE NOT EXISTS (SELECT 1 FROM service_bundle WHERE id=1);
INSERT INTO service_bundle (id, name, price_yuan, detail, enabled)
SELECT 2, '写真', 599.00, '含精修 8 张', 1 FROM DUAL
WHERE NOT EXISTS (SELECT 1 FROM service_bundle WHERE id=2);
INSERT INTO deliverable (id, reservation_id, file_url, delivered)
SELECT 1, 1, '/files/photo-1.jpg', 1 FROM DUAL
WHERE NOT EXISTS (SELECT 1 FROM deliverable WHERE id=1);
INSERT INTO deliverable (id, reservation_id, file_url, delivered)
SELECT 2, 2, '/files/photo-2.jpg', 0 FROM DUAL
WHERE NOT EXISTS (SELECT 1 FROM deliverable WHERE id=2);
"""
    return out.rstrip() + "\n" + _SHOOT_DDL + "\n" + seed


_BOARDING_DDL = """
CREATE TABLE IF NOT EXISTS stay_log (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  reservation_id BIGINT NULL,
  option_name VARCHAR(64) DEFAULT '',
  enabled TINYINT DEFAULT 1,
  day_key DATE NULL,
  note VARCHAR(255) DEFAULT '',
  photo_url VARCHAR(255) DEFAULT '',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
"""


def ensure_boarding_sql(sql: str, *, enabled: bool) -> str:
    """寄养日期与日志。未开不加。特殊要求与每日记录共用 stay_log。"""
    if not enabled:
        return sql

    def repl(m: re.Match[str]) -> str:
        head, table, body, tail = m.group(1), m.group(2), m.group(3), m.group(4)
        if table.lower() != "reservation":
            return m.group(0)
        body = _inject_missing_columns(
            body,
            [
                ("stay_from", "DATE NULL"),
                ("stay_to", "DATE NULL"),
                ("care_ids", "VARCHAR(128) NULL"),
            ],
        )
        return f"{head}{body}{tail}"

    out = _CREATE_TABLE_RE.sub(repl, sql)
    if re.search(r"(?i)CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+`?stay_log`?\b", out):
        return out
    seed = """INSERT INTO stay_log (id, option_name, enabled)
SELECT 1, '喂药', 1 FROM DUAL
WHERE NOT EXISTS (SELECT 1 FROM stay_log WHERE id=1);
INSERT INTO stay_log (id, option_name, enabled)
SELECT 2, '遛弯', 1 FROM DUAL
WHERE NOT EXISTS (SELECT 1 FROM stay_log WHERE id=2);
INSERT INTO stay_log (id, reservation_id, day_key, note, photo_url)
SELECT 3, 1, '2026-09-21', '已喂食，精神好', '/files/pet-1.jpg' FROM DUAL
WHERE NOT EXISTS (SELECT 1 FROM stay_log WHERE id=3);
"""
    return out.rstrip() + "\n" + _BOARDING_DDL + "\n" + seed


_ROOM_BOARD_DDL = """
CREATE TABLE IF NOT EXISTS room_instance (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  room_type_id BIGINT NOT NULL,
  room_no VARCHAR(32) NOT NULL DEFAULT '',
  status VARCHAR(16) NOT NULL DEFAULT '空房',
  order_id BIGINT NULL,
  checkin_id BIGINT NULL,
  note VARCHAR(255) DEFAULT '',
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS room_status_log (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  room_id BIGINT NOT NULL,
  old_status VARCHAR(16) DEFAULT '',
  new_status VARCHAR(16) NOT NULL DEFAULT '',
  operator_username VARCHAR(64) DEFAULT '',
  note VARCHAR(255) DEFAULT '',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
"""

_FRONT_DESK_DDL = """
CREATE TABLE IF NOT EXISTS checkin (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  order_id BIGINT NULL,
  reservation_id BIGINT NULL,
  room_id BIGINT NULL,
  guest_name VARCHAR(64) DEFAULT '',
  id_no VARCHAR(64) DEFAULT '',
  deposit_yuan DECIMAL(10,2) NOT NULL DEFAULT 0,
  status VARCHAR(16) NOT NULL DEFAULT 'checked_in',
  checked_in_at DATETIME NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS checkout (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  checkin_id BIGINT NOT NULL,
  order_id BIGINT NULL,
  room_id BIGINT NULL,
  settle_yuan DECIMAL(10,2) NOT NULL DEFAULT 0,
  deposit_back_yuan DECIMAL(10,2) NOT NULL DEFAULT 0,
  note VARCHAR(255) DEFAULT '',
  checked_out_at DATETIME NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS consumption (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  checkin_id BIGINT NOT NULL,
  order_id BIGINT NULL,
  title VARCHAR(128) NOT NULL DEFAULT '',
  amount_yuan DECIMAL(10,2) NOT NULL DEFAULT 0,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
"""


_VENUE_CLEAN_COLUMNS = (
    ("clean_status", "VARCHAR(16) NOT NULL DEFAULT ''"),
)


def ensure_venue_clean_sql(sql: str, *, enabled: bool, item_table: str | None) -> str:
    """档案/场地表补 clean_status。未开不加列；不新建表。"""
    if not enabled:
        return sql
    t = (item_table or "").strip()
    if not t or not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", t):
        return sql

    def repl(m: re.Match[str]) -> str:
        head, table, body, tail = m.group(1), m.group(2), m.group(3), m.group(4)
        if table.lower() != t.lower():
            return m.group(0)
        body = _inject_missing_columns(body, _VENUE_CLEAN_COLUMNS)
        return f"{head}{body}{tail}"

    return _CREATE_TABLE_RE.sub(repl, sql)


def ensure_room_board_sql(sql: str, *, enabled: bool) -> str:
    """房间实例 + 房态日志。未开不加。"""
    if not enabled:
        return sql
    if re.search(r"(?i)CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+`?room_instance`?\b", sql):
        return sql
    seed = """INSERT INTO room_instance (id, room_type_id, room_no, status)
SELECT 1, 1, '101', '空房' FROM DUAL
WHERE NOT EXISTS (SELECT 1 FROM room_instance WHERE id=1);
INSERT INTO room_instance (id, room_type_id, room_no, status)
SELECT 2, 1, '102', '空房' FROM DUAL
WHERE NOT EXISTS (SELECT 1 FROM room_instance WHERE id=2);
INSERT INTO room_instance (id, room_type_id, room_no, status)
SELECT 3, 2, '201', '待打扫' FROM DUAL
WHERE NOT EXISTS (SELECT 1 FROM room_instance WHERE id=3);
INSERT INTO room_status_log (id, room_id, old_status, new_status, operator_username, note)
SELECT 1, 3, '入住中', '待打扫', 'admin', '退房后待打扫' FROM DUAL
WHERE NOT EXISTS (SELECT 1 FROM room_status_log WHERE id=1);
"""
    return sql.rstrip() + "\n" + _ROOM_BOARD_DDL + "\n" + seed


def ensure_front_desk_sql(sql: str, *, enabled: bool) -> str:
    """入住登记 / 退房结算 / 消费挂账。未开不加。"""
    if not enabled:
        return sql
    if re.search(r"(?i)CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+`?checkin`?\b", sql):
        return sql
    seed = """INSERT INTO checkin (id, order_id, room_id, guest_name, id_no, deposit_yuan, status, checked_in_at)
SELECT 1, 1, 1, '张三', '110101199001011234', 200.00, 'checked_in', '2026-09-20 14:00:00' FROM DUAL
WHERE NOT EXISTS (SELECT 1 FROM checkin WHERE id=1);
INSERT INTO consumption (id, checkin_id, order_id, title, amount_yuan)
SELECT 1, 1, 1, '迷你吧', 36.00 FROM DUAL
WHERE NOT EXISTS (SELECT 1 FROM consumption WHERE id=1);
"""
    return sql.rstrip() + "\n" + _FRONT_DESK_DDL + "\n" + seed


ORDER_RENTAL_BOND_COLUMNS: list[tuple[str, str]] = [
    ("deposit_yuan", "DECIMAL(10,2) NOT NULL DEFAULT 0"),
    ("rent_yuan", "DECIMAL(10,2) NOT NULL DEFAULT 0"),
    ("late_fee_yuan", "DECIMAL(10,2) NOT NULL DEFAULT 0"),
    ("deposit_status", "VARCHAR(16) NOT NULL DEFAULT ''"),
    ("damage_note", "VARCHAR(255) DEFAULT ''"),
    ("damage_deduct_yuan", "DECIMAL(10,2) NOT NULL DEFAULT 0"),
]

VEHICLE_RENTAL_BOND_COLUMNS: list[tuple[str, str]] = [
    ("deposit_yuan", "DECIMAL(10,2) NOT NULL DEFAULT 0"),
    ("rent_stage", "VARCHAR(16) NOT NULL DEFAULT 'available'"),
]


def ensure_rental_bond_sql(sql: str, *, enabled: bool, item_table: str | None = "vehicle") -> str:
    """订单三笔钱 + 验损列；档案押金与可租/已租/维修。未开不加。"""
    if not enabled:
        return sql

    def order_repl(m: re.Match[str]) -> str:
        head, table, body, tail = m.group(1), m.group(2), m.group(3), m.group(4)
        if table.lower() != "biz_order":
            return m.group(0)
        body = _inject_missing_columns(body, ORDER_RENTAL_BOND_COLUMNS)
        return f"{head}{body}{tail}"

    out = _CREATE_TABLE_RE.sub(order_repl, sql)
    t = (item_table or "vehicle").strip()
    if t and re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", t):

        def item_repl(m: re.Match[str]) -> str:
            head, table, body, tail = m.group(1), m.group(2), m.group(3), m.group(4)
            if table.lower() != t.lower():
                return m.group(0)
            body = _inject_missing_columns(body, VEHICLE_RENTAL_BOND_COLUMNS)
            return f"{head}{body}{tail}"

        out = _CREATE_TABLE_RE.sub(item_repl, out)
        seed = (
            f"UPDATE {t} SET deposit_yuan=500.00, rent_stage='available' WHERE id=1 AND (deposit_yuan IS NULL OR deposit_yuan=0);\n"
            f"UPDATE {t} SET deposit_yuan=800.00, rent_stage='available' WHERE id=2 AND (deposit_yuan IS NULL OR deposit_yuan=0);\n"
            "UPDATE biz_order SET deposit_yuan=500.00, rent_yuan=total_yuan, deposit_status='held' "
            "WHERE id=1 AND (deposit_status IS NULL OR deposit_status='');\n"
        )
        out = out.rstrip() + "\n" + seed
    return out


_DIGITAL_GOODS_DDL = """
CREATE TABLE IF NOT EXISTS digital_code (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  item_id BIGINT NULL,
  code_value VARCHAR(128) NOT NULL DEFAULT '',
  link_url VARCHAR(255) NOT NULL DEFAULT '',
  kind VARCHAR(16) NOT NULL DEFAULT 'code',
  used_order_id BIGINT NULL,
  enabled TINYINT NOT NULL DEFAULT 1,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS digital_delivery (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  order_id BIGINT NOT NULL,
  item_id BIGINT NULL,
  kind VARCHAR(16) NOT NULL DEFAULT 'code',
  code_value VARCHAR(128) NOT NULL DEFAULT '',
  link_url VARCHAR(255) NOT NULL DEFAULT '',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  KEY idx_digital_order (order_id)
);
"""

PRODUCT_DIGITAL_COLUMNS: list[tuple[str, str]] = [
    ("digital_kind", "VARCHAR(16) NOT NULL DEFAULT 'code'"),
]


def ensure_digital_goods_sql(sql: str, *, enabled: bool, item_table: str | None = "product") -> str:
    """数字码池与订单交付快照。未开不加。"""
    if not enabled:
        return sql
    t = (item_table or "product").strip()
    out = sql
    if t and re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", t):

        def repl(m: re.Match[str]) -> str:
            head, table, body, tail = m.group(1), m.group(2), m.group(3), m.group(4)
            if table.lower() != t.lower():
                return m.group(0)
            body = _inject_missing_columns(body, PRODUCT_DIGITAL_COLUMNS)
            return f"{head}{body}{tail}"

        out = _CREATE_TABLE_RE.sub(repl, out)
    if re.search(r"(?i)CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+`?digital_delivery`?\b", out):
        return out
    seed = f"""UPDATE {t} SET digital_kind='code' WHERE id=1;
UPDATE {t} SET digital_kind='link' WHERE id=2;
INSERT INTO digital_code (id, item_id, code_value, kind, enabled)
SELECT 1, 1, 'DEMO-ACTIVATE-1001', 'code', 1 FROM DUAL
WHERE NOT EXISTS (SELECT 1 FROM digital_code WHERE id=1);
INSERT INTO digital_code (id, item_id, code_value, link_url, kind, enabled)
SELECT 2, 2, '', '/files/ebook-demo.pdf', 'link', 1 FROM DUAL
WHERE NOT EXISTS (SELECT 1 FROM digital_code WHERE id=2);
"""
    return out.rstrip() + "\n" + _DIGITAL_GOODS_DDL + "\n" + seed


_BUYBACK_DDL = """
CREATE TABLE IF NOT EXISTS buyback_slot (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  name VARCHAR(64) NOT NULL,
  enabled TINYINT DEFAULT 1
);
CREATE TABLE IF NOT EXISTS buyback_order (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  username VARCHAR(64) NOT NULL,
  book_title VARCHAR(200) NOT NULL,
  condition_note VARCHAR(255) DEFAULT '',
  slot_id BIGINT NULL,
  quote_yuan DECIMAL(10,2) NULL,
  status VARCHAR(32) NOT NULL DEFAULT 'pending',
  product_id BIGINT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
"""


def ensure_buyback_sql(sql: str, *, enabled: bool) -> str:
    """回收单与上门时段。未开不加。上架仍用商品表。"""
    if not enabled:
        return sql
    if re.search(r"(?i)CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+`?buyback_order`?\b", sql):
        return sql
    grade_col = ", condition_grade" if re.search(r"\bcondition_grade\b", sql, re.I) else ""
    grade_val = ", '八成新'" if grade_col else ""
    seed = f"""INSERT INTO buyback_slot (id, name, enabled)
SELECT 1, '上午上门', 1 FROM DUAL
WHERE NOT EXISTS (SELECT 1 FROM buyback_slot WHERE id=1);
INSERT INTO buyback_slot (id, name, enabled)
SELECT 2, '下午上门', 1 FROM DUAL
WHERE NOT EXISTS (SELECT 1 FROM buyback_slot WHERE id=2);
INSERT INTO product (id, title, author, isbn, category_id, stock, status{grade_col})
SELECT 9, '操作系统', '28.00', 'BOOK-OS', 1, 1, 'available'{grade_val} FROM DUAL
WHERE NOT EXISTS (SELECT 1 FROM product WHERE id=9);
INSERT INTO buyback_order (id, username, book_title, condition_note, slot_id, status)
SELECT 1, 'user', '线性代数', '有笔记', 1, 'pending' FROM DUAL
WHERE NOT EXISTS (SELECT 1 FROM buyback_order WHERE id=1);
INSERT INTO buyback_order (id, username, book_title, condition_note, slot_id, quote_yuan, status, product_id)
SELECT 2, 'user', '操作系统', '书页干净', 2, 28.00, 'listed', 9 FROM DUAL
WHERE NOT EXISTS (SELECT 1 FROM buyback_order WHERE id=2);
"""
    return sql.rstrip() + "\n" + _BUYBACK_DDL + "\n" + seed


_LESSON_PACK_DDL = """
CREATE TABLE IF NOT EXISTS lesson_pack (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  name VARCHAR(64) NOT NULL,
  sessions INT NOT NULL,
  price_yuan DECIMAL(10,2) NOT NULL,
  valid_days INT NOT NULL,
  enabled TINYINT DEFAULT 1
);
CREATE TABLE IF NOT EXISTS lesson_wallet (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  username VARCHAR(64) NOT NULL,
  total_sessions INT DEFAULT 0,
  remain_sessions INT DEFAULT 0,
  expire_at DATE NULL,
  reservation_id BIGINT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
"""


def ensure_lesson_pack_sql(sql: str, *, enabled: bool) -> str:
    """课时包与剩余节数。未开不加。约课仍用 reservation。"""
    if not enabled:
        return sql
    if re.search(r"(?i)CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+`?lesson_pack`?\b", sql):
        return sql
    seed = """INSERT INTO lesson_pack (id, name, sessions, price_yuan, valid_days, enabled)
SELECT 1, '体验包', 4, 199.00, 30, 1 FROM DUAL
WHERE NOT EXISTS (SELECT 1 FROM lesson_pack WHERE id=1);
INSERT INTO lesson_pack (id, name, sessions, price_yuan, valid_days, enabled)
SELECT 2, '季度包', 12, 499.00, 90, 1 FROM DUAL
WHERE NOT EXISTS (SELECT 1 FROM lesson_pack WHERE id=2);
INSERT INTO lesson_wallet (id, username, total_sessions, remain_sessions, expire_at)
SELECT 1, 'user', 4, 3, '2026-12-31' FROM DUAL
WHERE NOT EXISTS (SELECT 1 FROM lesson_wallet WHERE id=1);
INSERT INTO lesson_wallet (id, username, reservation_id, total_sessions, remain_sessions)
SELECT 2, 'user', 1, 0, 0 FROM DUAL
WHERE NOT EXISTS (SELECT 1 FROM lesson_wallet WHERE id=2);
"""
    return sql.rstrip() + "\n" + _LESSON_PACK_DDL + "\n" + seed


def ensure_archive_flag_columns(
    sql: str,
    *,
    item_table: str | None,
    allow_checkin: bool = False,
    peer_accept: bool = False,
    user_publish: bool = False,
    shop_marketplace: bool = False,
    check_mutex: bool = False,
    apply_deadline: bool = False,
    schedule: bool = False,
) -> str:
    """档案表按单据能力补签到码 / 确认人 / 互斥码 / 申报截止 / 起止时间列（禁止运行时再 ALTER）。"""
    t = (item_table or "").strip()
    if not t or not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", t):
        return sql
    cols: list[tuple[str, str]] = []
    if allow_checkin:
        cols.extend(CHECKIN_CODE_COLUMNS)
    # 互选确认人、门户发布归属均用 owner_username；商城多店商品归属亦复用
    if peer_accept or user_publish or shop_marketplace:
        cols.extend(OWNER_USERNAME_COLUMNS)
    if check_mutex:
        cols.extend(MUTEX_CODE_COLUMNS)
    if apply_deadline:
        cols.extend(APPLY_DEADLINE_COLUMNS)
    if schedule:
        cols.extend(SCHEDULE_COLUMNS)
    if not cols:
        return sql

    def repl(m: re.Match[str]) -> str:
        head, table, body, tail = m.group(1), m.group(2), m.group(3), m.group(4)
        if table.lower() != t.lower():
            return m.group(0)
        body = _inject_missing_columns(body, cols)
        return f"{head}{body}{tail}"

    return _CREATE_TABLE_RE.sub(repl, sql)


_PROMO_COUPON_DDL = """
CREATE TABLE IF NOT EXISTS promo_coupon (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  code VARCHAR(32) NOT NULL,
  label VARCHAR(64) DEFAULT '',
  min_yuan DECIMAL(10,2) NOT NULL DEFAULT 0,
  off_yuan DECIMAL(10,2) NOT NULL DEFAULT 0,
  total_quota INT NOT NULL DEFAULT 0,
  claimed INT NOT NULL DEFAULT 0,
  expire_at DATETIME NULL,
  status VARCHAR(16) NOT NULL DEFAULT 'active',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uk_promo_code (code)
);
"""

_USER_COUPON_DDL = """
CREATE TABLE IF NOT EXISTS user_coupon (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  username VARCHAR(64) NOT NULL,
  coupon_id BIGINT NOT NULL,
  status VARCHAR(16) NOT NULL DEFAULT 'unused',
  claimed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  used_at DATETIME NULL,
  order_id BIGINT NULL,
  UNIQUE KEY uk_user_coupon (username, coupon_id),
  KEY idx_user_coupon_user (username, status, id)
);
"""

_ORDER_REVIEW_DDL = """
CREATE TABLE IF NOT EXISTS order_review (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  order_id BIGINT NOT NULL,
  username VARCHAR(64) NOT NULL,
  rating INT NOT NULL,
  body VARCHAR(500) DEFAULT '',
  reply VARCHAR(500) DEFAULT '',
  replied_at DATETIME NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uk_order_review (order_id),
  KEY idx_review_user (username, id)
);
"""


def ensure_coupon_lifecycle_sql(sql: str, *, enabled: bool) -> str:
    if not enabled:
        return sql
    out = sql
    if not re.search(r"(?i)CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+`?promo_coupon`?\b", out):
        out = out.rstrip() + "\n" + _PROMO_COUPON_DDL
    if not re.search(r"(?i)CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+`?user_coupon`?\b", out):
        out = out.rstrip() + "\n" + _USER_COUPON_DDL
    return out


def _ensure_create_table_ddl(sql: str, *, table: str, ddl: str) -> str:
    """幂等补 CREATE TABLE；种子若已 INSERT/UPDATE 该表，则插到首条引用之前。"""
    if re.search(
        rf"(?i)CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?`?{re.escape(table)}`?\b",
        sql,
    ):
        return sql
    block = ddl if ddl.endswith("\n") else ddl + "\n"
    m = re.search(
        rf"(?i)(?:INSERT\s+(?:IGNORE\s+)?INTO|UPDATE|ALTER\s+TABLE|DELETE\s+FROM)\s+`?{re.escape(table)}`?\b",
        sql,
    )
    if m:
        return sql[: m.start()] + block + sql[m.start() :]
    return sql.rstrip() + "\n" + block


def ensure_order_review_sql(sql: str, *, enabled: bool) -> str:
    if not enabled:
        return sql
    return _ensure_create_table_ddl(sql, table="order_review", ddl=_ORDER_REVIEW_DDL)


_STOCK_IO_DDL = """
CREATE TABLE IF NOT EXISTS stock_move (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  move_type VARCHAR(16) NOT NULL,
  item_id BIGINT NOT NULL,
  item_title VARCHAR(200) DEFAULT '',
  qty INT NOT NULL,
  remark VARCHAR(255) DEFAULT '',
  operator VARCHAR(64) NOT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  KEY idx_stock_move_item (item_id, id),
  KEY idx_stock_move_type (move_type, id)
);
"""


def ensure_stock_io_sql(sql: str, *, enabled: bool) -> str:
    """能力开启时幂等补入出库流水表。"""
    if not enabled:
        return sql
    if re.search(r"(?i)CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+`?stock_move`?\b", sql):
        return sql
    return sql.rstrip() + "\n" + _STOCK_IO_DDL


_E_SIGN_DDL = """
CREATE TABLE IF NOT EXISTS e_sign_record (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  username VARCHAR(64) NOT NULL,
  title VARCHAR(200) NOT NULL,
  ticket_id BIGINT NULL,
  sign_image_url VARCHAR(255) NOT NULL DEFAULT '',
  agreed TINYINT NOT NULL DEFAULT 0,
  remark VARCHAR(255) DEFAULT '',
  signed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  KEY idx_e_sign_user (username, id)
);
"""


def ensure_e_sign_sql(sql: str, *, enabled: bool) -> str:
    """能力开启时幂等补签署留痕表。"""
    if not enabled:
        return sql
    if re.search(r"(?i)CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+`?e_sign_record`?\b", sql):
        return sql
    return sql.rstrip() + "\n" + _E_SIGN_DDL


_BALANCE_LEDGER_DDL = """
CREATE TABLE IF NOT EXISTS balance_subject (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  title VARCHAR(100) NOT NULL,
  unit_label VARCHAR(32) DEFAULT '次',
  status VARCHAR(32) DEFAULT 'available',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS balance_account (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  username VARCHAR(64) NOT NULL,
  subject_id BIGINT NOT NULL DEFAULT 1,
  balance INT NOT NULL DEFAULT 0,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uk_balance_user_subject (username, subject_id),
  KEY idx_balance_account_user (username)
);

CREATE TABLE IF NOT EXISTS balance_ledger (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  username VARCHAR(64) NOT NULL,
  subject_id BIGINT NOT NULL DEFAULT 1,
  delta_qty INT NOT NULL,
  reason VARCHAR(255) DEFAULT '',
  ref_type VARCHAR(32) DEFAULT '',
  ref_id BIGINT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  KEY idx_balance_ledger_user (username, id)
);

INSERT IGNORE INTO balance_subject (id, title, unit_label, status) VALUES
(1, '默认额度', '次', 'available');
INSERT IGNORE INTO balance_account (username, subject_id, balance) VALUES
('student', 1, 2),
('admin', 1, 100);
"""


def ensure_balance_ledger_sql(sql: str, *, enabled: bool, domain: str = "") -> str:
    if not enabled:
        return sql
    if re.search(r"(?i)CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+`?balance_account`?\b", sql):
        return sql
    from app.bake.features.timebank import ledger_subject

    title, unit = ledger_subject(domain)
    title = title.replace("'", "")
    unit = unit.replace("'", "")
    ddl = _BALANCE_LEDGER_DDL.replace(
        "(1, '默认额度', '次', 'available')",
        f"(1, '{title}', '{unit}', 'available')",
    )
    return sql.rstrip() + "\n" + ddl


_OCCUPY_SPAN_DDL = """
CREATE TABLE IF NOT EXISTS resource_occupy (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  username VARCHAR(64) NOT NULL,
  item_id BIGINT NULL,
  ticket_id BIGINT NULL,
  title VARCHAR(200) DEFAULT '',
  period_start DATETIME NOT NULL,
  period_end DATETIME NOT NULL,
  status VARCHAR(32) DEFAULT 'active',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  KEY idx_occupy_user (username, period_start),
  KEY idx_occupy_ticket (ticket_id)
);

CREATE TABLE IF NOT EXISTS occupy_block (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  title VARCHAR(200) NOT NULL,
  period_start DATETIME NOT NULL,
  period_end DATETIME NOT NULL,
  remark VARCHAR(255) DEFAULT '',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS occupy_day_stat (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  day_key VARCHAR(16) NOT NULL,
  occupy_count INT NOT NULL DEFAULT 0,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uk_occupy_day (day_key)
);
"""


def ensure_occupy_span_sql(sql: str, *, enabled: bool) -> str:
    if not enabled:
        return sql
    if re.search(r"(?i)CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+`?resource_occupy`?\b", sql):
        return sql
    return sql.rstrip() + "\n" + _OCCUPY_SPAN_DDL


_MATERIAL_CHECK_DDL = """
CREATE TABLE IF NOT EXISTS material_checklist (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  title VARCHAR(120) NOT NULL,
  required TINYINT NOT NULL DEFAULT 1,
  sort_order INT NOT NULL DEFAULT 0,
  status VARCHAR(32) DEFAULT 'available',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS ticket_material (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  ticket_id BIGINT NOT NULL,
  checklist_id BIGINT NOT NULL,
  file_url VARCHAR(255) NOT NULL DEFAULT '',
  uploaded_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  KEY idx_ticket_material_ticket (ticket_id)
);

CREATE TABLE IF NOT EXISTS material_template (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  title VARCHAR(120) NOT NULL,
  sample_url VARCHAR(255) DEFAULT '',
  remark VARCHAR(255) DEFAULT '',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

INSERT IGNORE INTO material_checklist (id, title, required, sort_order, status) VALUES
(1, '身份证明', 1, 1, 'available'),
(2, '申请说明附件', 1, 2, 'available');
INSERT IGNORE INTO material_template (id, title, remark) VALUES
(1, '材料模板说明', '按清单上传清晰扫描件');
"""


def ensure_material_check_sql(sql: str, *, enabled: bool) -> str:
    if not enabled:
        return sql
    if re.search(r"(?i)CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+`?material_checklist`?\b", sql):
        return sql
    return sql.rstrip() + "\n" + _MATERIAL_CHECK_DDL


# 亮点域结构补表：只补 ER 缺实体，规则仍走已有 cap
_STRUCTURAL_DDL: dict[str, str] = {
    "loan_renew_log": """
CREATE TABLE IF NOT EXISTS renew_log (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  ticket_id BIGINT NOT NULL,
  username VARCHAR(64) NOT NULL,
  old_due_at DATETIME NULL,
  new_due_at DATETIME NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  KEY idx_renew_ticket (ticket_id)
);
""",
    "fine_record": """
CREATE TABLE IF NOT EXISTS fine_record (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  ticket_id BIGINT NOT NULL,
  username VARCHAR(64) NOT NULL,
  amount DECIMAL(10,2) NOT NULL DEFAULT 0,
  status VARCHAR(32) DEFAULT 'open',
  remark VARCHAR(255) DEFAULT '',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  KEY idx_fine_ticket (ticket_id)
);
""",
    "doclib_extra": """
CREATE TABLE IF NOT EXISTS doc_folder (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  name VARCHAR(100) NOT NULL,
  parent_id BIGINT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS doc_version (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  doc_id BIGINT NOT NULL,
  version_no INT NOT NULL DEFAULT 1,
  file_url VARCHAR(255) DEFAULT '',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  KEY idx_doc_version_doc (doc_id)
);
CREATE TABLE IF NOT EXISTS download_grant (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  doc_id BIGINT NOT NULL,
  username VARCHAR(64) NOT NULL,
  status VARCHAR(32) DEFAULT 'allowed',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uk_download_grant (doc_id, username)
);
CREATE TABLE IF NOT EXISTS doc_tag (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  name VARCHAR(64) NOT NULL UNIQUE
);
""",
    "stock_location": """
CREATE TABLE IF NOT EXISTS stock_location (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  name VARCHAR(100) NOT NULL,
  remark VARCHAR(255) DEFAULT '',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
INSERT IGNORE INTO stock_location (id, name, remark) VALUES (1, '主仓', '单仓演示');
""",
    "stock_bin": """
CREATE TABLE IF NOT EXISTS stock_bin (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  location_id BIGINT NOT NULL DEFAULT 1,
  name VARCHAR(64) NOT NULL,
  remark VARCHAR(255) DEFAULT '',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  KEY idx_stock_bin_loc (location_id)
);
INSERT IGNORE INTO stock_bin (id, location_id, name, remark) VALUES (1, 1, '默认货位', '单仓演示');
""",
    "bed_building": """
CREATE TABLE IF NOT EXISTS dorm_building (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  name VARCHAR(64) NOT NULL UNIQUE,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS dorm_room_ref (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  building_id BIGINT NOT NULL,
  room_no VARCHAR(32) NOT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uk_dorm_room_ref (building_id, room_no)
);
CREATE TABLE IF NOT EXISTS bed_occupy_log (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  bed_id BIGINT NOT NULL,
  username VARCHAR(64) NOT NULL,
  action VARCHAR(32) NOT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
""",
    "checkin_extra": """
CREATE TABLE IF NOT EXISTS dorm_building (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  name VARCHAR(64) NOT NULL UNIQUE,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS checkin_absence (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  username VARCHAR(64) NOT NULL,
  room_id BIGINT NULL,
  day_key VARCHAR(16) NOT NULL,
  reason VARCHAR(255) DEFAULT '',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  KEY idx_absence_user (username, day_key)
);
CREATE TABLE IF NOT EXISTS checkin_code_log (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  apply_id BIGINT NOT NULL,
  username VARCHAR(64) NOT NULL,
  code_used VARCHAR(32) DEFAULT '',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
""",
    "pass_code_log": """
CREATE TABLE IF NOT EXISTS pass_code_issue (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  ticket_id BIGINT NOT NULL,
  username VARCHAR(64) NOT NULL,
  pass_code VARCHAR(64) NOT NULL,
  issued_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  KEY idx_pass_issue_ticket (ticket_id)
);
CREATE TABLE IF NOT EXISTS pass_code_show_log (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  ticket_id BIGINT NOT NULL,
  username VARCHAR(64) NOT NULL,
  shown_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS pass_site (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  name VARCHAR(100) NOT NULL,
  remark VARCHAR(255) DEFAULT ''
);
""",
    "mutual_wish": """
CREATE TABLE IF NOT EXISTS wish_rank (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  ticket_id BIGINT NOT NULL,
  archive_id BIGINT NOT NULL,
  rank_no INT NOT NULL DEFAULT 1,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  KEY idx_wish_ticket (ticket_id)
);
CREATE TABLE IF NOT EXISTS match_adjust_log (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  ticket_id BIGINT NOT NULL,
  operator VARCHAR(64) NOT NULL,
  remark VARCHAR(255) DEFAULT '',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS match_quota_day (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  day_key VARCHAR(16) NOT NULL,
  matched_count INT NOT NULL DEFAULT 0,
  UNIQUE KEY uk_match_quota_day (day_key)
);
""",
    "intern_extra": """
CREATE TABLE IF NOT EXISTS intern_org (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  name VARCHAR(120) NOT NULL,
  contact VARCHAR(64) DEFAULT '',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS intern_week_attach (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  ticket_id BIGINT NOT NULL,
  file_url VARCHAR(255) DEFAULT '',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
""",
    "parcel_extra": """
CREATE TABLE IF NOT EXISTS parcel_shelf (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  code VARCHAR(32) NOT NULL UNIQUE,
  remark VARCHAR(255) DEFAULT ''
);
CREATE TABLE IF NOT EXISTS parcel_pickup_log (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  ticket_id BIGINT NOT NULL,
  username VARCHAR(64) NOT NULL,
  code_used VARCHAR(32) DEFAULT '',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS parcel_station (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  name VARCHAR(100) NOT NULL,
  address VARCHAR(255) DEFAULT ''
);
""",
    "grade_extra": """
CREATE TABLE IF NOT EXISTS grade_term (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  name VARCHAR(64) NOT NULL UNIQUE
);
CREATE TABLE IF NOT EXISTS grade_score (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  username VARCHAR(64) NOT NULL,
  course_id BIGINT NOT NULL,
  term_id BIGINT NOT NULL,
  score DECIMAL(5,2) NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  KEY idx_grade_user (username)
);
CREATE TABLE IF NOT EXISTS grade_apply_attach (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  ticket_id BIGINT NOT NULL,
  file_url VARCHAR(255) DEFAULT ''
);
INSERT IGNORE INTO grade_term (id, name) VALUES (1, '2025-2026-1');
INSERT IGNORE INTO grade_score (id, username, course_id, term_id, score) VALUES
(1, 'user', 1, 1, 86.00),
(2, 'user', 3, 1, 91.50),
(3, 'peer', 1, 1, 92.00);
""",
    "procure_extra": """
CREATE TABLE IF NOT EXISTS procure_vendor (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  name VARCHAR(120) NOT NULL,
  contact VARCHAR(64) DEFAULT ''
);
CREATE TABLE IF NOT EXISTS procure_line (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  ticket_id BIGINT NOT NULL,
  item_title VARCHAR(200) NOT NULL,
  qty INT NOT NULL DEFAULT 1,
  unit_price DECIMAL(10,2) DEFAULT 0
);
CREATE TABLE IF NOT EXISTS procure_budget (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  title VARCHAR(120) NOT NULL,
  amount DECIMAL(12,2) NOT NULL DEFAULT 0
);
""",
    "carpool_extra": """
CREATE TABLE IF NOT EXISTS trip_stop (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  route_id BIGINT NOT NULL,
  stop_name VARCHAR(120) NOT NULL,
  sort_order INT NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS carpool_member (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  ticket_id BIGINT NOT NULL,
  username VARCHAR(64) NOT NULL,
  seat_no INT DEFAULT 0
);
CREATE TABLE IF NOT EXISTS carpool_chat_note (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  ticket_id BIGINT NOT NULL,
  body VARCHAR(255) DEFAULT '',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
""",
    "crm_listing": """
CREATE TABLE IF NOT EXISTS follow_contact (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  archive_id BIGINT NOT NULL,
  name VARCHAR(64) NOT NULL,
  phone VARCHAR(32) DEFAULT ''
);
CREATE TABLE IF NOT EXISTS follow_org (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  name VARCHAR(120) NOT NULL,
  remark VARCHAR(255) DEFAULT ''
);
CREATE TABLE IF NOT EXISTS follow_stage (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  name VARCHAR(64) NOT NULL UNIQUE
);
""",
    "eval_dims": """
CREATE TABLE IF NOT EXISTS eval_dimension (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  name VARCHAR(64) NOT NULL,
  weight INT NOT NULL DEFAULT 1,
  sort_order INT NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS eval_score_line (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  ticket_id BIGINT NOT NULL,
  dimension_id BIGINT NOT NULL,
  score INT NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS eval_term (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  name VARCHAR(64) NOT NULL UNIQUE
);
""",
    "survey_extra": """
CREATE TABLE IF NOT EXISTS survey_option (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  question_id BIGINT NOT NULL,
  label VARCHAR(200) NOT NULL,
  sort_order INT NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS survey_audience (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  form_id BIGINT NOT NULL,
  username VARCHAR(64) NOT NULL,
  UNIQUE KEY uk_survey_audience (form_id, username)
);
""",
    "vote_limit": """
CREATE TABLE IF NOT EXISTS vote_limit (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  vote_id BIGINT NOT NULL,
  max_ballots INT NOT NULL DEFAULT 1
);
""",
    "vote_round": """
CREATE TABLE IF NOT EXISTS vote_round (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  title VARCHAR(120) NOT NULL,
  status VARCHAR(32) DEFAULT 'open'
);
""",
    "vote_stat": """
CREATE TABLE IF NOT EXISTS vote_stat (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  vote_id BIGINT NOT NULL,
  candidate_id BIGINT NOT NULL,
  ballot_count INT NOT NULL DEFAULT 0,
  UNIQUE KEY uk_vote_stat (vote_id, candidate_id)
);
""",
    "timebank_org": """
CREATE TABLE IF NOT EXISTS tb_org (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  name VARCHAR(120) NOT NULL,
  contact VARCHAR(64) DEFAULT '',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
""",
    "instrument_renew": """
CREATE TABLE IF NOT EXISTS renew_log (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  ticket_id BIGINT NOT NULL,
  username VARCHAR(64) NOT NULL,
  old_due_at DATETIME NULL,
  new_due_at DATETIME NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  KEY idx_renew_ticket (ticket_id)
);
""",
    "event_extra": """
CREATE TABLE IF NOT EXISTS event_org_unit (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  name VARCHAR(120) NOT NULL,
  remark VARCHAR(255) DEFAULT ''
);
CREATE TABLE IF NOT EXISTS event_contact (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  case_id BIGINT NOT NULL,
  name VARCHAR(64) NOT NULL,
  phone VARCHAR(32) DEFAULT ''
);
""",
    "dating_extra": """
CREATE TABLE IF NOT EXISTS dating_tag (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  name VARCHAR(64) NOT NULL UNIQUE
);
CREATE TABLE IF NOT EXISTS dating_pref (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  username VARCHAR(64) NOT NULL,
  tag_id BIGINT NOT NULL,
  UNIQUE KEY uk_dating_pref (username, tag_id)
);
CREATE TABLE IF NOT EXISTS dating_match_log (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  username VARCHAR(64) NOT NULL,
  peer VARCHAR(64) NOT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
""",
    "oa_org": """
CREATE TABLE IF NOT EXISTS biz_org_unit (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  name VARCHAR(120) NOT NULL,
  remark VARCHAR(255) DEFAULT ''
);
CREATE TABLE IF NOT EXISTS biz_staff_ref (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  username VARCHAR(64) NOT NULL,
  org_id BIGINT NULL,
  title VARCHAR(64) DEFAULT ''
);
CREATE TABLE IF NOT EXISTS biz_apply_attach (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  ticket_id BIGINT NOT NULL,
  file_url VARCHAR(255) DEFAULT '',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
""",
}


def _append_ddl_if_missing(sql: str, table: str, ddl: str) -> str:
    if re.search(
        rf"(?i)CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+`?{re.escape(table)}`?\b",
        sql,
    ):
        return sql
    return sql.rstrip() + "\n" + ddl


def ensure_borrow_structural_sql(
    sql: str,
    *,
    domain: str,
    capabilities: list[str] | None = None,
) -> str:
    """按域/已有能力补 ER 缺表，凑齐借用族 ≥10；不发明平行规则。"""
    from app.bake.domains import is_borrow_family_domain

    if not is_borrow_family_domain(domain):
        return sql
    caps = set(capabilities or [])
    out = sql
    d = domain or ""

    if "loan_renew" in caps and d in ("DOM-LIBRARY", "DOM-EQUIP", "DOM-INSTRUMENT"):
        out = _append_ddl_if_missing(out, "renew_log", _STRUCTURAL_DDL["loan_renew_log"])
    if "deadline" in caps and d in ("DOM-LIBRARY", "DOM-EQUIP"):
        out = _append_ddl_if_missing(out, "fine_record", _STRUCTURAL_DDL["fine_record"])
    if d == "DOM-DOCLIB":
        out = _append_ddl_if_missing(out, "doc_folder", _STRUCTURAL_DDL["doclib_extra"])
    if d == "DOM-ASSET" and "stock_io" in caps:
        out = _append_ddl_if_missing(out, "stock_location", _STRUCTURAL_DDL["stock_location"])
        out = _append_ddl_if_missing(out, "stock_bin", _STRUCTURAL_DDL["stock_bin"])
    if d == "DOM-BED":
        out = _append_ddl_if_missing(out, "dorm_building", _STRUCTURAL_DDL["bed_building"])
    if d == "DOM-CHECKIN":
        out = _append_ddl_if_missing(out, "checkin_absence", _STRUCTURAL_DDL["checkin_extra"])
    if d in ("DOM-VISITOR", "DOM-CARPASS"):
        out = _append_ddl_if_missing(out, "pass_code_issue", _STRUCTURAL_DDL["pass_code_log"])
    if d in ("DOM-MUTUAL-TUTOR", "DOM-MUTUAL-TOPIC", "DOM-MUTUAL-TEAM"):
        out = _append_ddl_if_missing(out, "wish_rank", _STRUCTURAL_DDL["mutual_wish"])
    if d == "DOM-INTERN":
        out = _append_ddl_if_missing(out, "intern_org", _STRUCTURAL_DDL["intern_extra"])
        if "e_sign" in caps:
            out = ensure_e_sign_sql(out, enabled=True)
    if d == "DOM-PARCEL":
        out = _append_ddl_if_missing(out, "parcel_shelf", _STRUCTURAL_DDL["parcel_extra"])
    if d == "DOM-GRADE":
        out = _append_ddl_if_missing(out, "grade_term", _STRUCTURAL_DDL["grade_extra"])
    if d == "DOM-PROCURE":
        out = _append_ddl_if_missing(out, "procure_vendor", _STRUCTURAL_DDL["procure_extra"])
    if d == "DOM-CARPOOL":
        out = _append_ddl_if_missing(out, "trip_stop", _STRUCTURAL_DDL["carpool_extra"])
    if d in ("DOM-CRM", "DOM-LISTING"):
        out = _append_ddl_if_missing(out, "follow_contact", _STRUCTURAL_DDL["crm_listing"])
    if d == "DOM-EVAL":
        out = _append_ddl_if_missing(out, "eval_dimension", _STRUCTURAL_DDL["eval_dims"])
    if d == "DOM-SURVEY":
        out = _append_ddl_if_missing(out, "survey_option", _STRUCTURAL_DDL["survey_extra"])
    if d == "DOM-VOTE":
        # 模板已有 vote_ballot：逐表补限票/轮次/统计，避免整块因哨兵表跳过
        out = _append_ddl_if_missing(out, "vote_limit", _STRUCTURAL_DDL["vote_limit"])
        out = _append_ddl_if_missing(out, "vote_round", _STRUCTURAL_DDL["vote_round"])
        out = _append_ddl_if_missing(out, "vote_stat", _STRUCTURAL_DDL["vote_stat"])
    if d == "DOM-TIMEBANK":
        out = _append_ddl_if_missing(out, "tb_org", _STRUCTURAL_DDL["timebank_org"])
    if d == "DOM-INSTRUMENT" and "loan_renew" in caps:
        out = _append_ddl_if_missing(out, "renew_log", _STRUCTURAL_DDL["instrument_renew"])
    if d == "DOM-EVENT":
        out = _append_ddl_if_missing(out, "event_org_unit", _STRUCTURAL_DDL["event_extra"])
    if d == "DOM-DATING":
        out = _append_ddl_if_missing(out, "dating_tag", _STRUCTURAL_DDL["dating_extra"])
    # 其余薄 OA / 无专属结构：补通用组织三表
    if d in (
        "DOM-SEAL",
        "DOM-CERT",
        "DOM-PROMO",
        "DOM-FITOUT",
        "DOM-ACAD",
        "DOM-TRIP",
        "DOM-FUND",
        "DOM-EXPENSE",
        "DOM-CREDIT",
        "DOM-LABOR",
        "DOM-MORAL",
        "DOM-AWARD",
        "DOM-RECRUIT",
        "DOM-ATTEND",
        "DOM-FLEET",
        "DOM-CLUB",
        "DOM-PROJ",
        "DOM-ETHIC",
        "DOM-PARTY",
        "DOM-CONTRACT",
        "DOM-LABSAFE",
    ):
        # 有三套补丁时可能已够 10；仍缺则补组织表
        if len(re.findall(r"(?i)create\s+table\b", out)) < 10:
            out = _append_ddl_if_missing(out, "biz_org_unit", _STRUCTURAL_DDL["oa_org"])
    # 图书/设备再保底
    if d in ("DOM-LIBRARY", "DOM-EQUIP") and len(re.findall(r"(?i)create\s+table\b", out)) < 10:
        out = _append_ddl_if_missing(out, "biz_org_unit", _STRUCTURAL_DDL["oa_org"])
    # 族内最终保底：仍 <10 则逐表补 oa_org（避免整块因哨兵表已存在被跳过）
    _floor_tables = (
        ("biz_org_unit", "CREATE TABLE IF NOT EXISTS biz_org_unit (\n"
         "  id BIGINT PRIMARY KEY AUTO_INCREMENT,\n"
         "  name VARCHAR(120) NOT NULL,\n"
         "  remark VARCHAR(255) DEFAULT ''\n"
         ");\n"),
        ("biz_staff_ref", "CREATE TABLE IF NOT EXISTS biz_staff_ref (\n"
         "  id BIGINT PRIMARY KEY AUTO_INCREMENT,\n"
         "  username VARCHAR(64) NOT NULL,\n"
         "  org_id BIGINT NULL,\n"
         "  title VARCHAR(64) DEFAULT ''\n"
         ");\n"),
        ("biz_apply_attach", "CREATE TABLE IF NOT EXISTS biz_apply_attach (\n"
         "  id BIGINT PRIMARY KEY AUTO_INCREMENT,\n"
         "  ticket_id BIGINT NOT NULL,\n"
         "  file_url VARCHAR(255) DEFAULT '',\n"
         "  created_at DATETIME DEFAULT CURRENT_TIMESTAMP\n"
         ");\n"),
    )
    while len(re.findall(r"(?i)create\s+table\b", out)) < 10:
        progressed = False
        for tname, tddl in _floor_tables:
            before = out
            out = _append_ddl_if_missing(out, tname, tddl)
            if out != before:
                progressed = True
                break
        if not progressed:
            break
    return out


# 单据可选扩展列全集（剔除名单）；注入按域 + schema.ticket 能力
TICKET_OPTIONAL_COLUMNS: list[tuple[str, str]] = [
    ("attach_url", "VARCHAR(255) NOT NULL DEFAULT ''"),
    ("rating", "INT NULL"),
    ("rating_remark", "VARCHAR(255) NOT NULL DEFAULT ''"),
    ("rated_at", "DATETIME NULL"),
    ("rating_dims_json", "VARCHAR(1024) DEFAULT ''"),
    ("rating_anonymous", "TINYINT NOT NULL DEFAULT 0"),
    ("priority", "VARCHAR(16) DEFAULT '普通'"),
    ("contact_phone", "VARCHAR(20) DEFAULT ''"),
    ("fine_status", "VARCHAR(16) DEFAULT 'none'"),
    ("pickup_at", "DATETIME NULL"),
    ("pickup_place", "VARCHAR(128) DEFAULT ''"),
    ("actual_qty", "INT NULL"),
    ("contact_channel", "VARCHAR(32) DEFAULT ''"),
    ("next_follow_at", "DATETIME NULL"),
    ("checked_in_at", "DATETIME NULL"),
    ("pass_code", "VARCHAR(32) DEFAULT ''"),
    ("renew_count", "INT NOT NULL DEFAULT 0"),
    ("hold_expire_at", "DATETIME NULL"),
    ("qty", "INT NOT NULL DEFAULT 1"),
    ("period_start", "DATETIME NULL"),
    ("period_end", "DATETIME NULL"),
]

_TICKET_OPTIONAL_NAMES = {n.lower() for n, _ in TICKET_OPTIONAL_COLUMNS}
_TICKET_COL_DDL = {n.lower(): ddl for n, ddl in TICKET_OPTIONAL_COLUMNS}

# 域固有业务列（不含 attach/rating 等能力开关列）
TICKET_DOMAIN_COLUMNS: dict[str, list[str]] = {
    "DOM-LIBRARY": ["fine_status"],
    "DOM-EQUIP": ["fine_status"],
    "DOM-ASSET": ["pickup_at", "pickup_place", "actual_qty"],
    "DOM-CRM": ["contact_channel", "next_follow_at"],
    "DOM-ATTEND": ["contact_channel", "next_follow_at"],
    "DOM-FUND": ["contact_channel", "next_follow_at"],
    "DOM-LABSAFE": ["contact_channel", "next_follow_at"],
    "DOM-RECRUIT": ["contact_channel", "next_follow_at"],
    "DOM-DATING": ["contact_channel", "next_follow_at"],
    "DOM-GRADE": ["contact_channel", "next_follow_at"],
    "DOM-INTERN": ["contact_channel", "next_follow_at"],
    "DOM-SEAL": ["contact_channel", "next_follow_at"],
    "DOM-FLEET": ["contact_channel", "next_follow_at"],
    "DOM-CERT": ["contact_channel", "next_follow_at"],
    "DOM-PROMO": ["contact_channel", "next_follow_at"],
    "DOM-FITOUT": ["contact_channel", "next_follow_at"],
    "DOM-ACAD": ["contact_channel", "next_follow_at"],
    "DOM-TRIP": ["contact_channel", "next_follow_at"],
    "DOM-EXPENSE": ["contact_channel", "next_follow_at"],
    "DOM-CREDIT": ["contact_channel", "next_follow_at"],
    "DOM-LABOR": ["contact_channel", "next_follow_at"],
    "DOM-EVAL": [
        "contact_channel", "next_follow_at",
        "rating", "rating_remark", "rated_at", "rating_dims_json", "rating_anonymous",
    ],
    "DOM-MORAL": ["contact_channel", "next_follow_at"],
    "DOM-AWARD": ["contact_channel", "next_follow_at"],
    "DOM-BED": ["contact_channel", "next_follow_at"],
    "DOM-CHECKIN": ["contact_channel", "next_follow_at"],
    "DOM-MUTUAL-TUTOR": ["contact_channel", "next_follow_at"],
    "DOM-MUTUAL-TOPIC": ["contact_channel", "next_follow_at"],
    "DOM-MUTUAL-TEAM": ["contact_channel", "next_follow_at"],
    "DOM-VISITOR": ["contact_channel", "next_follow_at"],
    "DOM-CARPASS": ["contact_channel", "next_follow_at"],
    "DOM-LISTING": ["contact_channel", "next_follow_at"],
    "DOM-CARPOOL": ["contact_channel", "next_follow_at"],
    "DOM-TOUR": ["contact_channel", "next_follow_at"],
    "DOM-TIMEBANK": ["contact_channel", "next_follow_at"],
    "DOM-PROCURE": ["contact_channel", "next_follow_at"],
    "DOM-CLUB": ["contact_channel", "next_follow_at"],
    "DOM-PROJ": ["contact_channel", "next_follow_at"],
    "DOM-ETHIC": ["contact_channel", "next_follow_at"],
    "DOM-PARTY": ["contact_channel", "next_follow_at"],
    "DOM-CONTRACT": ["contact_channel", "next_follow_at"],
    "DOM-INSTRUMENT": ["contact_channel", "next_follow_at", "fine_status"],
    "DOM-EVENT": ["contact_channel", "next_follow_at"],
    "DOM-DORM": ["priority", "contact_phone"],
    "DOM-PROPERTY": ["priority", "contact_phone"],
    "DOM-IT": ["priority", "contact_phone"],
    "DOM-LOST": ["fine_status", "pickup_at", "pickup_place"],
    "DOM-PARCEL": ["fine_status", "pickup_at", "pickup_place"],
    "DOM-ACTIVITY": [],
    "DOM-COURSE": [],
    "DOM-FORUM": [],
}


def _ticket_flag_column_names(flags: dict | None) -> list[str]:
    """由 schema.entities.ticket 能力开关推导列名。"""
    f = flags or {}
    names: list[str] = []
    if f.get("requireAttach"):
        names.append("attach_url")
    if f.get("allowRating"):
        names.extend(["rating", "rating_remark", "rated_at"])
        if f.get("ratingDims"):
            names.extend(["rating_dims_json", "rating_anonymous"])
    if f.get("allowQty"):
        names.append("qty")
    if f.get("pickDateRange"):
        names.extend(["period_start", "period_end"])
    if f.get("allowCheckin"):
        names.append("checked_in_at")
    if f.get("issuePassCode"):
        names.append("pass_code")
    if f.get("allowRenew"):
        names.append("renew_count")
    if f.get("allowBookHold"):
        names.append("hold_expire_at")
    if f.get("noShowAfterEnd") or f.get("fineLabel"):
        names.append("fine_status")
    # 去重保序
    seen: set[str] = set()
    out: list[str] = []
    for n in names:
        if n not in seen:
            seen.add(n)
            out.append(n)
    return out


def resolve_ticket_flags(
    domain: str,
    *,
    archetype: str | None = None,
    archetypes: list[str] | None = None,
    ticket_flags: dict | None = None,
) -> dict:
    """优先用 bake 传入的 ticket 实体；否则回落域默认 schema。"""
    if isinstance(ticket_flags, dict) and ticket_flags:
        return ticket_flags
    d = (domain or "").strip()
    try:
        from app.bake.schema.templates import SCHEMA_BUILDERS

        builder = SCHEMA_BUILDERS.get(d)
        if builder:
            schema = builder("thesis")
            ent = ((schema.get("entities") or {}).get("ticket") or {})
            if isinstance(ent, dict):
                return ent
    except Exception:
        pass
    if d == "DOM-GENERIC":
        try:
            from app.bake.archetype_shells import build_generic_shell_schema

            schema = build_generic_shell_schema(
                "thesis",
                archetype=archetype,
                archetypes=archetypes,
            )
            ent = ((schema.get("entities") or {}).get("ticket") or {})
            if isinstance(ent, dict):
                return ent
        except Exception:
            pass
    return {}


def ticket_optional_columns_for(
    domain: str,
    *,
    ticket_flags: dict | None = None,
) -> list[tuple[str, str]]:
    names: list[str] = []
    names.extend(TICKET_DOMAIN_COLUMNS.get(domain or "", []))
    names.extend(_ticket_flag_column_names(ticket_flags))
    seen: set[str] = set()
    cols: list[tuple[str, str]] = []
    for n in names:
        key = n.lower()
        if key in seen:
            continue
        for cat_name, cat_ddl in TICKET_OPTIONAL_COLUMNS:
            if cat_name.lower() == key:
                seen.add(key)
                cols.append((cat_name, cat_ddl))
                break
    return cols


def ensure_ticket_extra_sql(
    sql: str,
    *,
    domain: str,
    ticket_table: str | None,
    ticket_flags: dict | None = None,
) -> str:
    """对单据主表按域/能力补齐扩展列，并剔除跨域 L1 超集。"""
    t = (ticket_table or "").strip()
    if not t or not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", t):
        return sql
    want = ticket_optional_columns_for(domain, ticket_flags=ticket_flags)
    allow = {n.lower() for n, _ in want}

    def repl(m: re.Match[str]) -> str:
        head, table, body, tail = m.group(1), m.group(2), m.group(3), m.group(4)
        if table.lower() != t.lower():
            return m.group(0)
        body = _prune_columns(body, allow=allow, known=_TICKET_OPTIONAL_NAMES)
        if want:
            body = _inject_missing_columns(body, want)
        body = _strip_trailing_comma(body)
        return f"{head}{body}{tail}"

    return _CREATE_TABLE_RE.sub(repl, sql)


def ensure_ticket_progress_sql(sql: str, ticket_table: str | None) -> str:
    """单据进度统一为 {ticket}_progress；去掉同域闲置的 {ticket}_log，避免双表语义。"""
    t = (ticket_table or "").strip()
    if not t or not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", t):
        return sql
    progress = f"{t}_progress"
    log_name = f"{t}_log"
    out = re.sub(
        rf"CREATE TABLE IF NOT EXISTS\s+`?{re.escape(log_name)}`?\s*\((?:.|\n)*?\);\s*",
        "",
        sql,
        count=1,
        flags=re.IGNORECASE,
    )
    if re.search(rf"CREATE TABLE IF NOT EXISTS\s+`?{re.escape(progress)}`?\b", out, re.I):
        return out
    return out.rstrip() + "\n" + _TICKET_PROGRESS_DDL.format(table=progress)
