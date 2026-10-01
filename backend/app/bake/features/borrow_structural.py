"""借用族结构表 DDL：按域/能力幂等补 ER 缺表。"""

from __future__ import annotations

import re

from app.bake.features.e_sign import ensure_e_sign_sql

# --- SQL ensure (moved from fragments.py) ---

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
CREATE TABLE IF NOT EXISTS grade_score_history (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  score_id BIGINT NOT NULL,
  username VARCHAR(64) NOT NULL DEFAULT '',
  course_id BIGINT NULL,
  term_id BIGINT NULL,
  old_score DECIMAL(5,2) NULL,
  new_score DECIMAL(5,2) NULL,
  action VARCHAR(16) NOT NULL DEFAULT 'update',
  operator VARCHAR(64) NOT NULL DEFAULT '',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  KEY idx_grade_history_score (score_id)
);
INSERT IGNORE INTO grade_term (id, name) VALUES (1, '2025-2026-1');
INSERT IGNORE INTO grade_score (id, username, course_id, term_id, score) VALUES
(1, 'user', 1, 1, 86.00),
(2, 'user', 3, 1, 91.50),
(3, 'peer', 1, 1, 92.00);
""",
    # 资助域旁路岛：审核通过后「公示」→「发放」；挂在申请之后，不扩 ticket 状态机
    "fund_extra": """
CREATE TABLE IF NOT EXISTS fund_publicity (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  ticket_id BIGINT NOT NULL,
  title VARCHAR(128) NOT NULL DEFAULT '',
  start_at DATE NULL,
  end_at DATE NULL,
  status VARCHAR(16) NOT NULL DEFAULT 'publicizing',
  operator VARCHAR(64) NOT NULL DEFAULT '',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  KEY idx_fund_publicity_ticket (ticket_id)
);
CREATE TABLE IF NOT EXISTS fund_disburse (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  ticket_id BIGINT NOT NULL,
  amount DECIMAL(10,2) NOT NULL DEFAULT 0,
  paid_at DATE NULL,
  operator VARCHAR(64) NOT NULL DEFAULT '',
  remark VARCHAR(255) DEFAULT '',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  KEY idx_fund_disburse_ticket (ticket_id)
);
""",
    # 房源成交台账：带看跟进办结后登记成交，不把房源做成交易系统
    "listing_deal": """
CREATE TABLE IF NOT EXISTS listing_deal (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  ticket_id BIGINT NOT NULL,
  deal_price DECIMAL(12,2) NOT NULL DEFAULT 0,
  deal_at DATE NULL,
  operator VARCHAR(64) NOT NULL DEFAULT '',
  remark VARCHAR(255) DEFAULT '',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  KEY idx_listing_deal_ticket (ticket_id)
);
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

    # 借用/占用族下限 BORROW_TABLE_MIN=10 是无条件的：续借/罚金是「常见好做默认实现」，
    # 材料没写也补表（否则窄材料只剩 8 张，与本函数 docstring 和门禁下限自相矛盾）。
    if d in ("DOM-LIBRARY", "DOM-EQUIP", "DOM-INSTRUMENT"):
        out = _append_ddl_if_missing(out, "renew_log", _STRUCTURAL_DDL["loan_renew_log"])
    if d in ("DOM-LIBRARY", "DOM-EQUIP"):
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
    if d == "DOM-FUND":
        out = _append_ddl_if_missing(out, "fund_publicity", _STRUCTURAL_DDL["fund_extra"])
    if d == "DOM-LISTING":
        out = _append_ddl_if_missing(out, "listing_deal", _STRUCTURAL_DDL["listing_deal"])
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
