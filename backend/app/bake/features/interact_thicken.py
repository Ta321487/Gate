"""互动/匹配组加厚（§1.9）：双选/考试/问卷/投票/拼车/时银/婚恋等通识与域皮。

I-00：脚手架（INTERACT_DOMAINS + 注册点）。
I-01：半截钉齐——favorites 心动 / allowRating 评价 / mutual 截止倒计时 /
      客观题判分口径 / 时银星级叠。
I-02：DATING 域皮——完整度 / 互关 / 见面意向 / 举报时限 / 审驳 /
      条件筛选 / 黑名单 / 相册审 / 活动入口叠。
I-03：MUTUAL 通识——调剂留痕 / 截止前改志愿 / 附件包 / 盲选 / 志愿互斥 /
      公示页 / 调剂上限 / 确认超时婉拒 / 锁定倒计时 / 结果导出信 / 面试叠。
I-04：MUTUAL 域皮——名额进度条；组队技能/邀请/满员/附言/退出/匹配度；导师互评。
I-05：CARPOOL——满员关行程 / 出发提醒 / 分摊备注 / 座位余量 / 偏好 /
      途经点 / 取消惩罚 / 锁座 / 校区字典 / AA / 行李 / 电话脱敏 / 重复发布。
I-06：TIMEBANK——时长榜 / 兑换导出 / 技能认证 / 兑换目录 / 信用分 /
      发布须审 / 时长冻结 / 证明附件 / 申诉 / 转让 / 清零说明。
I-07：EXAM 作答与规则——练习模式 / 防切屏 / 解析 / 乱序 / 进度条 /
      及格线 / 多选部分分 / 交卷不可改 / 迟到禁入 / 监考口令。
I-08：EXAM 题库与成绩——及格证书 / 错题本导出 / 题目导入 / 多卷抽题 /
      主观评分细则 / 成绩导入 / 难度标签。
I-09：SURVEY——开放截止上下架 / 匿名 / 跳题 / 进度条 / 限填一次 / 必答 /
      矩阵题 / 结果图表 / 截止提醒 / 草稿 / 显隐 / 投放组织 / 感谢页 / 回收率。
I-10：VOTE——结果导出 / IP 提示 / 十佳海报 / 图文简介 / 票数轮询 /
      每日限票 / 匿名 / 延迟公布 / 拉票文案 / 实名可投 / 弃权 / 实时榜前三。
I-11：能力岛加深——仅当已挂 favorites / allowRating / dm / content_report；
      未挂无旗/无按钮（读 thicken 前已合并的 capabilities）。
I-12：扫尾对照地图「本组待补」清零。

硬约束
------
- 只挂 INTERACT_DOMAINS = DATING / MUTUAL-* / CARPOOL / TIMEBANK / EXAM /
  SURVEY / VOTE。
- 不碰 §1.6 交易、§1.7 预约、§1.8 内容；DATING∩ACTIVITY、MUTUAL∩MEETING
  只做文案交叉，不另起邻组状态机。
- Store 分域：ExamStore / SurveyStore / VoteStore / TimebankStore；
  双选/拼车/婚恋意向辅 TicketStore + ArchiveStore；私信辅 DmStore；
  收藏辅 Favorites。禁止第二套互选/问卷/投票/判分引擎。
- 心动列表复用 favorites；评价仅 allowRating 已挂时加深；客观题判分钉口径。
- 协同过滤推荐 / 真地图 / 人脸监考 / 实时 IM SDK / 刷票中台 → 不支持，不进待补。
- I-11 仅 cap 已挂时加深；禁止因「互动常见」域默认硬开邻组岛。
"""

from __future__ import annotations

import re
from typing import Any

INTERACT_DOMAINS = frozenset(
    {
        "DOM-DATING",
        "DOM-MUTUAL-TUTOR",
        "DOM-MUTUAL-TOPIC",
        "DOM-MUTUAL-TEAM",
        "DOM-CARPOOL",
        "DOM-TIMEBANK",
        "DOM-EXAM",
        "DOM-SURVEY",
        "DOM-VOTE",
    }
)

_MUTUAL_DOMAINS = frozenset(
    {"DOM-MUTUAL-TUTOR", "DOM-MUTUAL-TOPIC", "DOM-MUTUAL-TEAM"}
)
_RATING_SKIN_DOMAINS = frozenset({"DOM-CARPOOL", "DOM-TIMEBANK"})

_APPLY_DEADLINE_COLS: list[tuple[str, str]] = [
    ("apply_deadline_at", "DATETIME NULL"),
]

# I-03：导师/选题附件简介包（档案侧 URL；≠单据 requireAttach）
_MUTUAL_ITEM_COLS: list[tuple[str, str]] = [
    ("intro_pack_url", "VARCHAR(255) NOT NULL DEFAULT ''"),
]

# I-04 TUTOR：名额上限（余量仍用 stock；进度条 = (cap-stock)/cap）
_TUTOR_ITEM_COLS: list[tuple[str, str]] = [
    ("quota_cap", "INT NULL"),
]

# I-04 TEAM：技能标签 CSV + 招募阶段
_TEAM_ITEM_COLS: list[tuple[str, str]] = [
    ("skill_tags", "VARCHAR(255) NOT NULL DEFAULT ''"),
    ("stage", "VARCHAR(32) NOT NULL DEFAULT '招募中'"),
]

# I-04 TEAM：退出申请标记（approved 单上请求退出）
_TEAM_TICKET_COLS: list[tuple[str, str]] = [
    ("exit_request", "TINYINT NOT NULL DEFAULT 0"),
]

# I-05 CARPOOL：行程档案列（途经点文本顶地图；总费用落库供 AA；≠支付）
_CARPOOL_ITEM_COLS: list[tuple[str, str]] = [
    ("stage", "VARCHAR(32) NOT NULL DEFAULT '开放'"),
    ("start_campus", "VARCHAR(64) NOT NULL DEFAULT ''"),
    ("end_campus", "VARCHAR(64) NOT NULL DEFAULT ''"),
    ("via_points", "VARCHAR(512) NOT NULL DEFAULT ''"),
    ("share_note", "VARCHAR(255) NOT NULL DEFAULT ''"),
    ("pref_note", "VARCHAR(255) NOT NULL DEFAULT ''"),
    ("luggage_count", "INT NOT NULL DEFAULT 0"),
    ("fare_total_yuan", "DECIMAL(10,2) NULL"),
    ("remind_before_minutes", "INT NOT NULL DEFAULT 0"),
    ("depart_reminded_at", "DATETIME NULL"),
]

_CARPOOL_CAMPUS_OPTIONS = "东校区,西校区,南校区,北校区,主校区"

# I-06 TIMEBANK：账户加厚列（技能认证 / 信用分 / 冻结）
_TIMEBANK_ACCOUNT_COLS: list[tuple[str, str]] = [
    ("skill_tags", "VARCHAR(255) NOT NULL DEFAULT ''"),
    ("skill_certified", "TINYINT NOT NULL DEFAULT 0"),
    ("credit_score", "INT NOT NULL DEFAULT 100"),
    ("frozen_hours", "DECIMAL(10,2) NOT NULL DEFAULT 0"),
]

# I-07 EXAM：试卷规则列（及格线 pass_score 已在模板；此处补乱序/解析/部分分/锁卷/开考/迟到/口令）
# I-08：难度标签叠在试卷上
_EXAM_PAPER_COLS: list[tuple[str, str]] = [
    ("pass_score", "INT NOT NULL DEFAULT 60"),
    ("shuffle_questions", "TINYINT NOT NULL DEFAULT 0"),
    ("shuffle_options", "TINYINT NOT NULL DEFAULT 0"),
    ("explain_after_score", "TINYINT NOT NULL DEFAULT 1"),
    ("partial_multi", "TINYINT NOT NULL DEFAULT 0"),
    ("lock_after_submit", "TINYINT NOT NULL DEFAULT 0"),
    ("open_at", "DATETIME NULL"),
    ("late_enter_min", "INT NOT NULL DEFAULT 0"),
    ("entry_code", "VARCHAR(64) NOT NULL DEFAULT ''"),
    ("difficulty", "VARCHAR(32) NOT NULL DEFAULT ''"),
]

_EXAM_ATTEMPT_COLS: list[tuple[str, str]] = [
    ("blur_count", "INT NOT NULL DEFAULT 0"),
]

# I-08：主观题评分细则
_EXAM_QUESTION_COLS: list[tuple[str, str]] = [
    ("mark_rubric", "VARCHAR(1000) NOT NULL DEFAULT ''"),
]

# I-09 SURVEY：问卷表加厚列
_SURVEY_FORM_COLS: list[tuple[str, str]] = [
    ("open_at", "DATETIME NULL"),
    ("close_at", "DATETIME NULL"),
    ("anonymous", "TINYINT NOT NULL DEFAULT 0"),
    ("once_only", "TINYINT NOT NULL DEFAULT 1"),
    ("target_org", "VARCHAR(128) NOT NULL DEFAULT ''"),
    ("remind_before_hours", "INT NOT NULL DEFAULT 0"),
    ("close_reminded_at", "DATETIME NULL"),
    ("target_count", "INT NOT NULL DEFAULT 0"),
]

_SURVEY_QUESTION_COLS: list[tuple[str, str]] = [
    ("skip_when_label", "VARCHAR(8) NOT NULL DEFAULT ''"),
    ("skip_to_sort", "INT NULL"),
    ("show_when_qid", "BIGINT NULL"),
    ("show_when_label", "VARCHAR(8) NOT NULL DEFAULT ''"),
    ("matrix_rows", "VARCHAR(1000) NOT NULL DEFAULT ''"),
]

_SURVEY_EXTRA_DDL = """
CREATE TABLE IF NOT EXISTS survey_draft (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  form_id BIGINT NOT NULL,
  username VARCHAR(64) NOT NULL,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uk_survey_draft (form_id, username)
);
CREATE TABLE IF NOT EXISTS survey_draft_answer (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  form_id BIGINT NOT NULL,
  username VARCHAR(64) NOT NULL,
  question_id BIGINT NOT NULL,
  answer_text VARCHAR(2000) DEFAULT '',
  UNIQUE KEY uk_survey_draft_ans (form_id, username, question_id),
  KEY idx_survey_draft_ans (form_id, username)
);
CREATE TABLE IF NOT EXISTS survey_audience (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  form_id BIGINT NOT NULL,
  username VARCHAR(64) NOT NULL,
  UNIQUE KEY uk_survey_audience (form_id, username)
);
"""

# I-10 VOTE：评选规则列 + 候选人拉票文案 + 选票 IP/弃权
_VOTE_CAMPAIGN_COLS: list[tuple[str, str]] = [
    ("anonymous", "TINYINT NOT NULL DEFAULT 0"),
    ("daily_vote_limit", "INT NOT NULL DEFAULT 0"),
    ("results_publish_at", "DATETIME NULL"),
    ("allow_abstain", "TINYINT NOT NULL DEFAULT 0"),
    ("require_real_name", "TINYINT NOT NULL DEFAULT 0"),
    ("poll_seconds", "INT NOT NULL DEFAULT 0"),
    ("ip_hint_enabled", "TINYINT NOT NULL DEFAULT 1"),
]

_VOTE_CANDIDATE_COLS: list[tuple[str, str]] = [
    ("avatar_url", "VARCHAR(255) DEFAULT ''"),
    ("slogan", "VARCHAR(255) NOT NULL DEFAULT ''"),
]

_VOTE_BALLOT_COLS: list[tuple[str, str]] = [
    ("client_ip", "VARCHAR(64) NOT NULL DEFAULT ''"),
    ("abstain", "TINYINT NOT NULL DEFAULT 0"),
]

_TIMEBANK_EXTRA_DDL = """
CREATE TABLE IF NOT EXISTS tb_catalog (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  title VARCHAR(120) NOT NULL,
  cost_hours DECIMAL(10,2) NOT NULL DEFAULT 1,
  stock INT NOT NULL DEFAULT 0,
  enabled TINYINT NOT NULL DEFAULT 1,
  remark VARCHAR(255) NOT NULL DEFAULT '',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS tb_appeal (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  username VARCHAR(64) NOT NULL,
  reason VARCHAR(255) NOT NULL DEFAULT '',
  status VARCHAR(16) NOT NULL DEFAULT 'pending',
  admin_remark VARCHAR(255) NOT NULL DEFAULT '',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  KEY idx_tb_appeal_user (username)
);
CREATE TABLE IF NOT EXISTS tb_clear_rule (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  body VARCHAR(512) NOT NULL DEFAULT '',
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
"""

_MUTUAL_PEER_TIMEOUT_HOURS = 72
_MUTUAL_MAX_ADJUST_WISHES = 1

# 图集列 gallery_json 不在此注入：I-02 走 _force_gallery → ensure_gallery_sql
# owner_username：审驳/投稿归属需要；domain_sql 的 ensure_archive_flag 只读 builder 原皮，
# 读不到 interact 加厚的 userPublish，故在此与审驳列一并注入。
_DATING_ITEM_COLS: list[tuple[str, str]] = [
    ("owner_username", "VARCHAR(64) NOT NULL DEFAULT ''"),
    ("reject_reason", "VARCHAR(255) NOT NULL DEFAULT ''"),
    ("age_years", "INT NULL"),
    ("ideal_city", "VARCHAR(64) NOT NULL DEFAULT ''"),
    ("ideal_age_min", "INT NULL"),
    ("ideal_age_max", "INT NULL"),
    ("album_audit_status", "VARCHAR(16) NOT NULL DEFAULT 'none'"),
]

_USER_FOLLOW_DDL = """
CREATE TABLE IF NOT EXISTS user_follow (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  follower VARCHAR(64) NOT NULL,
  followee VARCHAR(64) NOT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uk_uf_pair (follower, followee),
  KEY idx_uf_followee (followee)
);
"""

_DATING_REPORT_HANDLE_DAYS = 3

_MEET_INTENT_OPTIONS = ["线上沟通", "线下见面", "参加联谊", "暂不确定"]


def _live_schema(spec: dict[str, Any]) -> dict[str, Any]:
    schema = spec.get("schema")
    if not isinstance(schema, dict):
        schema = {}
        spec["schema"] = schema
    return schema


def _add_feature(spec: dict[str, Any], name: str) -> None:
    feats = spec.get("features")
    if not isinstance(feats, list):
        feats = []
        spec["features"] = feats
    if name not in feats:
        feats.append(name)


def _ensure_archive_field(archive: dict[str, Any], field: dict[str, Any]) -> None:
    fields = archive.get("fields")
    if not isinstance(fields, list):
        fields = []
        archive["fields"] = fields
    key = str(field.get("key") or "")
    if not key:
        return
    for f in fields:
        if isinstance(f, dict) and f.get("key") == key:
            return
    fields.append(field)


def _valid_ident(name: str | None) -> bool:
    t = (name or "").strip()
    return bool(t and re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", t))


def ensure_interact_thicken_sql(
    sql: str,
    *,
    domain: str | None,
    item_table: str | None = None,
    ticket_table: str | None = None,
) -> str:
    """九互动域加厚列/子表；I-01～I-06 MUTUAL/DATING/CARPOOL/TIMEBANK。"""
    dom = domain or ""
    if dom not in INTERACT_DOMAINS:
        return sql
    from app.bake.sql.ddl_edit import (
        CREATE_TABLE_RE as _CREATE_TABLE_RE,
        inject_missing_columns as _inject_missing_columns,
    )

    out = sql
    item = (item_table or "").strip()
    ticket = (ticket_table or "").strip()
    if dom in _MUTUAL_DOMAINS and _valid_ident(item):

        def repl_mutual(m: re.Match[str]) -> str:
            head, table, body, tail = m.group(1), m.group(2), m.group(3), m.group(4)
            if table.lower() != item.lower():
                return m.group(0)
            cols = list(_APPLY_DEADLINE_COLS) + list(_MUTUAL_ITEM_COLS)
            if dom == "DOM-MUTUAL-TUTOR":
                cols.extend(_TUTOR_ITEM_COLS)
            if dom == "DOM-MUTUAL-TEAM":
                cols.extend(_TEAM_ITEM_COLS)
            body = _inject_missing_columns(body, cols)
            return f"{head}{body}{tail}"

        out = _CREATE_TABLE_RE.sub(repl_mutual, out)

    if dom == "DOM-MUTUAL-TEAM" and _valid_ident(ticket):

        def repl_team_ticket(m: re.Match[str]) -> str:
            head, table, body, tail = m.group(1), m.group(2), m.group(3), m.group(4)
            if table.lower() != ticket.lower():
                return m.group(0)
            body = _inject_missing_columns(body, list(_TEAM_TICKET_COLS))
            return f"{head}{body}{tail}"

        out = _CREATE_TABLE_RE.sub(repl_team_ticket, out)

    if dom == "DOM-CARPOOL" and _valid_ident(item):

        def repl_carpool(m: re.Match[str]) -> str:
            head, table, body, tail = m.group(1), m.group(2), m.group(3), m.group(4)
            if table.lower() != item.lower():
                return m.group(0)
            body = _inject_missing_columns(body, list(_CARPOOL_ITEM_COLS))
            return f"{head}{body}{tail}"

        out = _CREATE_TABLE_RE.sub(repl_carpool, out)

    if dom == "DOM-TIMEBANK":

        def repl_tb_account(m: re.Match[str]) -> str:
            head, table, body, tail = m.group(1), m.group(2), m.group(3), m.group(4)
            if table.lower() != "tb_account":
                return m.group(0)
            body = _inject_missing_columns(body, list(_TIMEBANK_ACCOUNT_COLS))
            return f"{head}{body}{tail}"

        out = _CREATE_TABLE_RE.sub(repl_tb_account, out)
        if "CREATE TABLE IF NOT EXISTS tb_catalog" not in out:
            out = out.rstrip() + "\n\n" + _TIMEBANK_EXTRA_DDL.strip() + "\n"

    if dom == "DOM-DATING" and _valid_ident(item):

        def repl_dating(m: re.Match[str]) -> str:
            head, table, body, tail = m.group(1), m.group(2), m.group(3), m.group(4)
            if table.lower() != item.lower():
                return m.group(0)
            cols = list(_DATING_ITEM_COLS)
            # gallery 由 gallery cap ensure；此处只补相册审状态与资料列
            body = _inject_missing_columns(body, cols)
            return f"{head}{body}{tail}"

        out = _CREATE_TABLE_RE.sub(repl_dating, out)
        if "CREATE TABLE IF NOT EXISTS user_follow" not in out:
            out = out.rstrip() + "\n\n" + _USER_FOLLOW_DDL.strip() + "\n"

    if dom == "DOM-EXAM":

        def repl_exam_paper(m: re.Match[str]) -> str:
            head, table, body, tail = m.group(1), m.group(2), m.group(3), m.group(4)
            if table.lower() != "exam_paper":
                return m.group(0)
            body = _inject_missing_columns(body, list(_EXAM_PAPER_COLS))
            return f"{head}{body}{tail}"

        def repl_exam_attempt(m: re.Match[str]) -> str:
            head, table, body, tail = m.group(1), m.group(2), m.group(3), m.group(4)
            if table.lower() != "exam_attempt":
                return m.group(0)
            body = _inject_missing_columns(body, list(_EXAM_ATTEMPT_COLS))
            return f"{head}{body}{tail}"

        def repl_exam_question(m: re.Match[str]) -> str:
            head, table, body, tail = m.group(1), m.group(2), m.group(3), m.group(4)
            if table.lower() != "exam_question":
                return m.group(0)
            body = _inject_missing_columns(body, list(_EXAM_QUESTION_COLS))
            return f"{head}{body}{tail}"

        out = _CREATE_TABLE_RE.sub(repl_exam_paper, out)
        out = _CREATE_TABLE_RE.sub(repl_exam_attempt, out)
        out = _CREATE_TABLE_RE.sub(repl_exam_question, out)

    if dom == "DOM-SURVEY":

        def repl_survey_form(m: re.Match[str]) -> str:
            head, table, body, tail = m.group(1), m.group(2), m.group(3), m.group(4)
            if table.lower() != "survey_form":
                return m.group(0)
            body = _inject_missing_columns(body, list(_SURVEY_FORM_COLS))
            return f"{head}{body}{tail}"

        def repl_survey_question(m: re.Match[str]) -> str:
            head, table, body, tail = m.group(1), m.group(2), m.group(3), m.group(4)
            if table.lower() != "survey_question":
                return m.group(0)
            body = _inject_missing_columns(body, list(_SURVEY_QUESTION_COLS))
            return f"{head}{body}{tail}"

        out = _CREATE_TABLE_RE.sub(repl_survey_form, out)
        out = _CREATE_TABLE_RE.sub(repl_survey_question, out)
        if "CREATE TABLE IF NOT EXISTS survey_draft" not in out:
            out = out.rstrip() + "\n\n" + _SURVEY_EXTRA_DDL.strip() + "\n"

    if dom == "DOM-VOTE":

        def repl_vote_campaign(m: re.Match[str]) -> str:
            head, table, body, tail = m.group(1), m.group(2), m.group(3), m.group(4)
            if table.lower() != "vote_campaign":
                return m.group(0)
            body = _inject_missing_columns(body, list(_VOTE_CAMPAIGN_COLS))
            return f"{head}{body}{tail}"

        def repl_vote_candidate(m: re.Match[str]) -> str:
            head, table, body, tail = m.group(1), m.group(2), m.group(3), m.group(4)
            if table.lower() != "vote_candidate":
                return m.group(0)
            body = _inject_missing_columns(body, list(_VOTE_CANDIDATE_COLS))
            return f"{head}{body}{tail}"

        def repl_vote_ballot(m: re.Match[str]) -> str:
            head, table, body, tail = m.group(1), m.group(2), m.group(3), m.group(4)
            if table.lower() != "vote_ballot":
                return m.group(0)
            body = _inject_missing_columns(body, list(_VOTE_BALLOT_COLS))
            return f"{head}{body}{tail}"

        out = _CREATE_TABLE_RE.sub(repl_vote_campaign, out)
        out = _CREATE_TABLE_RE.sub(repl_vote_candidate, out)
        out = _CREATE_TABLE_RE.sub(repl_vote_ballot, out)
    return out


def _nail_dating_favorites(spec: dict[str, Any], schema: dict[str, Any], thicken: dict[str, Any]) -> None:
    """I-01：DATING 域默认挂 favorites，文案钉为心动列表（禁止第二套收藏表）。"""
    from app.bake.features.favorites import FAVORITES_CAP, attach_favorites_menus
    from app.bake.gate_contracts import merge_favorites_gate

    caps = list(spec.get("capabilities") or [])
    if FAVORITES_CAP not in caps:
        caps.append(FAVORITES_CAP)
        spec["capabilities"] = caps
        schema["capabilities"] = caps
    attach_favorites_menus(
        schema,
        page_lead="收藏心仪的交友资料，方便再次查看与牵线。",
    )
    labels = schema.setdefault("labels", {})
    labels["favoritesPageTitle"] = "心动列表"
    labels["favoritesPageLead"] = "收藏心仪的交友资料，方便再次查看与牵线。"
    labels.setdefault("favoritesVerb", "心动")
    labels.setdefault("favoritedVerb", "已心动")
    labels.setdefault("favoritesEmptyTitle", "暂无心动")
    labels.setdefault("favoritesEmptyDesc", "去资料浏览里点心动，感兴趣的人会出现在这里。")
    labels.setdefault("favoritesCancelLabel", "取消心动")
    try:
        spec["gate"] = merge_favorites_gate(dict(spec.get("gate") or {}), caps)
    except Exception:
        pass
    thicken["datingFavorites"] = True
    _add_feature(spec, "心动列表")


def _nail_rating_skin(
    spec: dict[str, Any],
    schema: dict[str, Any],
    thicken: dict[str, Any],
    *,
    domain: str,
) -> None:
    """I-01：CARPOOL/TIMEBANK 域皮开 allowRating（复用 TicketStore.rate，禁止平行评价引擎）。"""
    ents = schema.setdefault("entities", {})
    ticket = ents.get("ticket") if isinstance(ents.get("ticket"), dict) else {}
    if not isinstance(ticket, dict):
        ticket = {}
        ents["ticket"] = ticket
    ticket["allowRating"] = True
    labels = schema.setdefault("labels", {})
    if domain == "DOM-CARPOOL":
        labels.setdefault("ratingLabel", "拼车评价")
        labels.setdefault("rateInviteHint", "行程结束后可对本次拼车评分。")
        labels.setdefault("avgRatingLabel", "拼车均分")
        thicken["carpoolRating"] = True
        _add_feature(spec, "拼车评价")
    elif domain == "DOM-MUTUAL-TUTOR":
        labels.setdefault("ratingLabel", "师生互评")
        labels.setdefault("rateInviteHint", "互选确认后可对本次双选评分。")
        labels.setdefault("avgRatingLabel", "互评均分")
        thicken["tutorMutualRating"] = True
        _add_feature(spec, "双选导师学生互评")
    else:
        labels.setdefault("ratingLabel", "服务评价")
        labels.setdefault("rateInviteHint", "服务办结后可对本次互助评分。")
        labels.setdefault("avgRatingLabel", "星级信誉")
        labels.setdefault("timebankStarReputationLabel", "星级信誉")
        labels.setdefault(
            "timebankStarReputationHint",
            "根据已完成服务的评分汇总，分数越高表示口碑越好。",
        )
        thicken["timebankRating"] = True
        thicken["timebankStarReputation"] = True
        _add_feature(spec, "时间银行服务评价")
        _add_feature(spec, "时间银行星级信誉")


def _nail_mutual_deadline(
    spec: dict[str, Any],
    schema: dict[str, Any],
    thicken: dict[str, Any],
) -> None:
    """I-01：MUTUAL-* 域默认志愿截止 + 倒计时文案（复用 applyDeadlineAt）。"""
    ents = schema.setdefault("entities", {})
    archive = ents.get("archive") if isinstance(ents.get("archive"), dict) else {}
    if not isinstance(archive, dict):
        archive = {}
        ents["archive"] = archive
    _ensure_archive_field(
        archive,
        {"key": "applyDeadlineAt", "label": "志愿截止", "type": "datetime"},
    )
    labels = schema.setdefault("labels", {})
    labels.setdefault("applyDeadlineLabel", "志愿截止")
    labels.setdefault("mutualDeadlineCountdownLabel", "距志愿截止")
    labels.setdefault("mutualDeadlinePassedLabel", "志愿已截止")
    labels.setdefault(
        "mutualDeadlineHint",
        "请在截止前提交或调整志愿；截止后不可再报。",
    )
    thicken["mutualDeadlineCountdown"] = True
    _add_feature(spec, "互选截止倒计时")


def _nail_exam_grade_contract(
    spec: dict[str, Any],
    schema: dict[str, Any],
    thicken: dict[str, Any],
) -> None:
    """I-01：客观题自动判分口径钉死（多选部分分归 I-07）。"""
    labels = schema.setdefault("labels", {})
    labels.setdefault(
        "examObjectiveGradeHint",
        "客观题交卷后按标准答案自动判分：单选与判断须完全一致；多选须选项集合完全一致才得分（部分对不得分）；主观题由教务主管阅卷。",
    )
    labels.setdefault("examObjectiveGradedLead", "客观题已自动判分。总分在全部主观题阅完后公布。")
    thicken["examObjectiveGradeContract"] = True
    _add_feature(spec, "客观题自动判分口径")


def _nail_exam_i07(
    spec: dict[str, Any],
    schema: dict[str, Any],
    thicken: dict[str, Any],
) -> None:
    """I-07 EXAM：练习不计分次数 / 防切屏 / 解析开关 / 乱序 / 进度条 / 及格线 / 部分分 / 交卷锁 / 迟到 / 口令。"""
    from app.bake.features.exam import attach_exam_menus

    labels = schema.setdefault("labels", {})
    opts = schema.get("examOpts") if isinstance(schema.get("examOpts"), dict) else {}
    opts = dict(opts)
    opts["practice"] = True
    opts["explain"] = True
    opts.setdefault("timer", True)
    opts.setdefault("attempt_limit", True)
    schema["examOpts"] = opts
    ents = schema.setdefault("entities", {})
    exam_ent = ents.get("exam") if isinstance(ents.get("exam"), dict) else {}
    if not isinstance(exam_ent, dict):
        exam_ent = {"key": "exam", "label": "考试", "labelPlural": "考试"}
        ents["exam"] = exam_ent
    exam_ent["opts"] = {
        **(exam_ent.get("opts") if isinstance(exam_ent.get("opts"), dict) else {}),
        "practice": True,
        "explain": True,
        "timer": bool(opts.get("timer")),
        "attemptLimit": bool(opts.get("attempt_limit")),
        "rank": bool(opts.get("rank")),
        "wrongbook": bool(opts.get("wrongbook")),
    }
    attach_exam_menus(schema, opts=opts)

    # —— 练习模式不计分 / 不计次数 ——
    labels.setdefault("examPracticeTitle", "刷题练习")
    labels.setdefault(
        "examPracticeLead",
        "练习模式不计正式得分、不计考试次数，可反复作答；成绩不进排行。",
    )
    labels.setdefault("examPracticeNoScoreHint", "练习交卷仅供自测，不记正式得分。")
    thicken["examPracticeNoScore"] = True
    _add_feature(spec, "练习模式不计分 / 不计次数")

    # —— 防切屏（文案 + 失焦计数；≠锁屏 SDK）——
    labels.setdefault(
        "examBlurWarnLead",
        "答题期间请勿切换窗口。离开页面会累计切屏次数，供考后核对。",
    )
    labels.setdefault("examBlurCountLabel", "切屏次数")
    thicken["examBlurWarn"] = True
    _add_feature(spec, "考试防切屏提示（文案+失焦计数）")

    # —— 成绩公布后可看解析 ——
    labels.setdefault("examExplainAfterScoreLabel", "成绩公布后显示解析")
    labels.setdefault(
        "examExplainAfterScoreHint",
        "开启后，答卷成绩公布（客观题交卷或主观题阅完）才可查看题目解析。",
    )
    thicken["examExplainAfterScore"] = True
    _add_feature(spec, "成绩公布后可看解析开关")

    # —— 题目/选项乱序 ——
    labels.setdefault("examShuffleQuestionsLabel", "题目乱序")
    labels.setdefault("examShuffleOptionsLabel", "选项乱序")
    labels.setdefault("examShuffleHint", "开考后按答卷固定乱序，刷新页面顺序不变。")
    thicken["examShuffle"] = True
    _add_feature(spec, "试卷题目/选项乱序")

    # —— 交卷前答题进度条 ——
    labels.setdefault("examProgressLabel", "答题进度")
    labels.setdefault("examProgressHint", "已作答题数 / 总题数")
    thicken["examAnswerProgress"] = True
    _add_feature(spec, "交卷前答题进度条")

    # —— 及格线可配 ——
    labels.setdefault("examPassScoreLabel", "及格线(%)")
    labels.setdefault("examPassScoreHint", "百分制及格线，用于成绩展示与准入校验。")
    thicken["examPassScore"] = True
    _add_feature(spec, "考试及格线可配")

    # —— 多选题部分得分 ——
    labels.setdefault("examPartialMultiLabel", "多选部分得分")
    labels.setdefault(
        "examPartialMultiHint",
        "开启后：选对部分且无错选时按比例给分；有错选不得分。关闭则须全对才得分。",
    )
    labels.setdefault(
        "examObjectiveGradeHint",
        "客观题交卷后按标准答案自动判分：单选与判断须完全一致；多选在开启部分得分时按比例计分（有错选为 0），否则须选项集合完全一致；主观题由教务主管阅卷。",
    )
    thicken["examPartialMulti"] = True
    _add_feature(spec, "多选题部分得分规则")

    # —— 交卷后不可修改 ——
    labels.setdefault("examLockAfterSubmitLabel", "交卷后不可再考")
    labels.setdefault(
        "examLockAfterSubmitHint",
        "开启后，正式考试一旦交卷不可再次开考修改。",
    )
    labels.setdefault("examLockAfterSubmitDeny", "本卷已交卷，不可再次开考。")
    thicken["examLockAfterSubmit"] = True
    _add_feature(spec, "考试交卷后不可修改开关")

    # —— 迟到禁止进入 ——
    labels.setdefault("examOpenAtLabel", "开考时间")
    labels.setdefault("examLateEnterMinLabel", "迟到限时(分)")
    labels.setdefault(
        "examLateEnterHint",
        "填写开考时间与迟到限时后，超过开考时刻加限时分钟不可进入。0 表示不限制迟到。",
    )
    labels.setdefault("examLateEnterDeny", "已超过允许迟到时间，无法进入考试。")
    labels.setdefault("examNotOpenYetDeny", "未到开考时间，请稍后再试。")
    thicken["examLateEnter"] = True
    _add_feature(spec, "考试迟到禁止进入（开考后 N 分）")

    # —— 监考口令 ——
    labels.setdefault("examEntryCodeLabel", "入场口令")
    labels.setdefault("examEntryCodePlaceholder", "请输入监考老师提供的口令")
    labels.setdefault("examEntryCodeHint", "填写后开考须输入正确口令；≠人脸核验。")
    labels.setdefault("examEntryCodeRequired", "请输入入场口令")
    labels.setdefault("examEntryCodeDeny", "入场口令不正确")
    thicken["examEntryCode"] = True
    _add_feature(spec, "考试监考口令（入场码）")


def _nail_exam_i08(
    spec: dict[str, Any],
    schema: dict[str, Any],
    thicken: dict[str, Any],
) -> None:
    """I-08 EXAM：及格证书 / 错题导出 / 题目导入 / 随机抽题 / 评分细则 / 成绩导入 / 难度标签。"""
    from app.bake.features.exam import attach_exam_menus

    labels = schema.setdefault("labels", {})
    opts = schema.get("examOpts") if isinstance(schema.get("examOpts"), dict) else {}
    opts = dict(opts)
    opts["wrongbook"] = True
    opts.setdefault("practice", True)
    opts.setdefault("explain", True)
    schema["examOpts"] = opts
    ents = schema.setdefault("entities", {})
    exam_ent = ents.get("exam") if isinstance(ents.get("exam"), dict) else {}
    if not isinstance(exam_ent, dict):
        exam_ent = {"key": "exam", "label": "考试", "labelPlural": "考试"}
        ents["exam"] = exam_ent
    exam_opts = exam_ent.get("opts") if isinstance(exam_ent.get("opts"), dict) else {}
    exam_ent["opts"] = {**exam_opts, "wrongbook": True}
    attach_exam_menus(schema, opts=opts)

    # —— 及格证书页（打印壳；≠ CA）——
    labels.setdefault("examCertificateTitle", "考试及格证书")
    labels.setdefault(
        "examCertificateLead",
        "成绩达到及格线后可查看并打印本页证书，仅供本系统内证明，非权威认证。",
    )
    labels.setdefault("examCertificatePrintLabel", "打印证书")
    labels.setdefault("examCertificateOpenLabel", "查看证书")
    labels.setdefault("examCertificateDeny", "未达到及格线，暂无证书。")
    labels.setdefault("examCertificateNameLabel", "考生")
    labels.setdefault("examCertificatePaperLabel", "试卷")
    labels.setdefault("examCertificateScoreLabel", "成绩")
    labels.setdefault("examCertificatePassLabel", "及格线")
    labels.setdefault("examCertificateDateLabel", "发证日期")
    thicken["examCertificate"] = True
    _add_feature(spec, "考试及格证书页（固定模板 PDF）")

    # —— 错题本导出 ——
    labels.setdefault("examWrongbookExportLabel", "导出错题")
    labels.setdefault("examWrongbookExportHint", "导出当前错题本为 CSV，便于复习。")
    thicken["examWrongbookExport"] = True
    _add_feature(spec, "错题本导出")

    # —— 题目导入（CSV 文本；Word/Excel 可另存为 CSV 后粘贴）——
    labels.setdefault("examQuestionImportLabel", "导入题目")
    labels.setdefault(
        "examQuestionImportHint",
        "每行：题型,题干,选项(用|分隔),答案,分值,解析,评分细则。题型为 single/multi/judge/subjective。",
    )
    labels.setdefault("examQuestionImportTemplateLabel", "下载导入模板")
    labels.setdefault("examQuestionImportDone", "题目已导入")
    thicken["examQuestionImport"] = True
    _add_feature(spec, "考试题目导入 Word/Excel")

    # —— 多卷随机抽题 ——
    labels.setdefault("examRandomDrawLabel", "随机抽题")
    labels.setdefault(
        "examRandomDrawHint",
        "从题库随机抽取若干题加入本卷（已在卷中的题目会跳过）。",
    )
    labels.setdefault("examRandomDrawCountLabel", "抽取数量")
    labels.setdefault("examRandomDrawDone", "已抽入试卷")
    thicken["examRandomDraw"] = True
    _add_feature(spec, "考试多卷随机抽题")

    # —— 主观题评分细则 ——
    labels.setdefault("examMarkRubricLabel", "评分细则")
    labels.setdefault("examMarkRubricHint", "供阅卷教务主管参考的给分说明，不对学生展示。")
    labels.setdefault("examMarkRubricPlaceholder", "如：要点齐全得满分，缺一项扣 2 分…")
    thicken["examMarkRubric"] = True
    _add_feature(spec, "考试主观题评分细则字段")

    # —— 成绩导入模板 ——
    labels.setdefault("examScoreImportLabel", "导入成绩")
    labels.setdefault(
        "examScoreImportHint",
        "每行：账号,试卷ID,得分,总分。用于补录已批改成绩。",
    )
    labels.setdefault("examScoreImportTemplateLabel", "下载成绩模板")
    labels.setdefault("examScoreImportDone", "成绩已导入")
    thicken["examScoreImport"] = True
    _add_feature(spec, "考试成绩导入模板")

    # —— 试卷难度标签 ——
    labels.setdefault("examDifficultyLabel", "难度")
    labels.setdefault("examDifficultyPlaceholder", "如：简单 / 中等 / 较难")
    labels.setdefault("examDifficultyHint", "试卷难度标签，便于筛选与组卷说明。")
    thicken["examDifficulty"] = True
    _add_feature(spec, "考试试卷难度标签")


def _nail_survey_i09(
    spec: dict[str, Any],
    schema: dict[str, Any],
    thicken: dict[str, Any],
) -> None:
    """I-09 SURVEY：上下架/匿名/跳题/进度/限填/必答/矩阵/图表/提醒/草稿/显隐/组织/感谢/回收率。"""
    labels = schema.setdefault("labels", {})

    # —— 开放/截止自动上下架 ——
    labels.setdefault("surveyOpenAtLabel", "开放时间")
    labels.setdefault("surveyCloseAtLabel", "截止时间")
    labels.setdefault(
        "surveyScheduleHint",
        "填写开放/截止时间后，系统会按时间自动上架或下架；留空则仅看状态字段。",
    )
    thicken["surveySchedule"] = True
    _add_feature(spec, "问卷开放/截止自动上下架")

    # —— 匿名 ——
    labels.setdefault("surveyAnonymousLabel", "匿名填写")
    labels.setdefault("surveyAnonymousHint", "开启后回收明细不展示填写人账号。")
    thicken["surveyAnonymous"] = True
    _add_feature(spec, "问卷匿名填写开关")

    # —— 跳题 ——
    labels.setdefault("surveySkipWhenLabel", "选中则跳题")
    labels.setdefault("surveySkipToSortLabel", "跳至题号")
    labels.setdefault(
        "surveySkipHint",
        "单选题：选中指定选项后跳到目标排序题（-1 表示结束）。浅规则，非全功能引擎。",
    )
    thicken["surveySkip"] = True
    _add_feature(spec, "问卷逻辑跳题（简单若选A则跳）")

    # —— 进度条 ——
    labels.setdefault("surveyProgressLabel", "填写进度")
    labels.setdefault("surveyProgressHint", "已答可见必答题 / 可见必答题总数。")
    thicken["surveyAnswerProgress"] = True
    _add_feature(spec, "交卷前答题进度条")

    # —— 限填一次 ——
    labels.setdefault("surveyOnceOnlyLabel", "每人限填一次")
    labels.setdefault("surveyOnceOnlyHint", "开启后同一账号不可重复提交。")
    labels.setdefault("surveyOnceOnlyDeny", "您已填写过该问卷")
    thicken["surveyOnceOnly"] = True
    _add_feature(spec, "问卷每人限填一次")

    # —— 必答 ——
    labels.setdefault("surveyRequiredLabel", "必答")
    labels.setdefault("surveyRequiredHint", "勾选后交卷前须作答。")
    thicken["surveyRequired"] = True
    _add_feature(spec, "问卷必答题标记与校验")

    # —— 矩阵题 ——
    labels.setdefault("surveyMatrixLabel", "矩阵题")
    labels.setdefault("surveyMatrixRowsLabel", "行标签 JSON")
    labels.setdefault(
        "surveyMatrixHint",
        '矩阵题：行标签填 JSON 如 ["服务态度","环境卫生"]，列选项用选项 JSON。',
    )
    thicken["surveyMatrix"] = True
    _add_feature(spec, "问卷矩阵题（简单表格题）")

    # —— 结果图表 ——
    labels.setdefault("surveyChartTitle", "结果图表")
    labels.setdefault("surveyChartBarLabel", "柱状图")
    labels.setdefault("surveyChartPieLabel", "饼图")
    thicken["surveyResultCharts"] = True
    _add_feature(spec, "问卷结果图表（柱/饼）")

    # —— 截止提醒 ——
    labels.setdefault("surveyRemindHoursLabel", "截止前提醒(小时)")
    labels.setdefault(
        "surveyRemindHint",
        "大于 0 时，在截止前向未填用户发站内信（浅提醒）。",
    )
    thicken["surveyCloseRemind"] = True
    _add_feature(spec, "问卷截止前提醒站内信")

    # —— 草稿 ——
    labels.setdefault("surveyDraftSaveLabel", "保存草稿")
    labels.setdefault("surveyDraftSaved", "草稿已保存")
    labels.setdefault("surveyDraftHint", "可中途保存，提交后草稿清除。")
    thicken["surveyDraft"] = True
    _add_feature(spec, "问卷填写进度保存草稿")

    # —— 显隐 ——
    labels.setdefault("surveyShowWhenQidLabel", "依赖题目ID")
    labels.setdefault("surveyShowWhenLabel", "依赖选项")
    labels.setdefault(
        "surveyShowHint",
        "填写依赖题目 ID 与选项字母后，仅当选中该选项时显示本题（显隐，非跳题）。",
    )
    thicken["surveyShowIf"] = True
    _add_feature(spec, "问卷逻辑显示（显隐，非跳题）")

    # —— 投放组织 ——
    labels.setdefault("surveyTargetOrgLabel", "投放组织")
    labels.setdefault(
        "surveyTargetOrgHint",
        "填写后仅资料中院系/组织匹配的用户可见；也可在受众表按账号白名单投放。",
    )
    thicken["surveyTargetOrg"] = True
    _add_feature(spec, "问卷投放对象按组织")

    # —— 感谢页 ——
    labels.setdefault("surveyThanksTitle", "感谢填写")
    labels.setdefault(
        "surveyThanksLead",
        "您的答卷已提交，感谢参与本次调查。",
    )
    labels.setdefault("surveyThanksBackLabel", "查看我的答卷")
    thicken["surveyThanks"] = True
    _add_feature(spec, "问卷填写后感谢页")

    # —— 回收率卡片 ——
    labels.setdefault("surveyRecycleCardLabel", "回收率")
    labels.setdefault("surveyTargetCountLabel", "回收目标份数")
    thicken["surveyRecycleCard"] = True
    _add_feature(spec, "问卷回收率工作台卡片")


def _nail_vote_i10(
    spec: dict[str, Any],
    schema: dict[str, Any],
    thicken: dict[str, Any],
) -> None:
    """I-10 VOTE：导出 / IP 提示 / 海报 / 图文 / 轮询 / 每日限票 / 匿名 / 延迟 / 拉票 / 实名 / 弃权 / 前三。"""
    labels = schema.setdefault("labels", {})

    labels.setdefault("voteExportLabel", "导出结果")
    labels.setdefault("voteExportHint", "导出计票排名与选票明细（CSV）。")
    thicken["voteResultExport"] = True
    _add_feature(spec, "投票结果导出")

    labels.setdefault(
        "voteIpHintLead",
        "同一网络地址已有其他人投票时会提示，不拦截提交。",
    )
    thicken["voteIpHint"] = True
    _add_feature(spec, "投票防刷：同 IP 提示（仅提示）")

    labels.setdefault("votePosterTitle", "十佳结果海报")
    labels.setdefault("votePosterLead", "按得票展示前十名，可打印存档。")
    labels.setdefault("votePosterLinkLabel", "十佳海报")
    thicken["votePoster"] = True
    _add_feature(spec, "十佳结果海报页（静态生成）")

    labels.setdefault("voteIntroLabel", "图文简介")
    labels.setdefault("voteIntroHint", "候选人简介与头像一并展示。")
    labels.setdefault("voteAvatarLabel", "头像")
    thicken["voteCandidateIntro"] = True
    _add_feature(spec, "投票候选人图文简介")

    labels.setdefault("votePollSecondsLabel", "结果刷新间隔(秒)")
    labels.setdefault(
        "votePollHint",
        "大于 0 时结果公示区按间隔自动刷新；0 表示不轮询。",
    )
    thicken["votePollRefresh"] = True
    _add_feature(spec, "投票票数定时刷新（轮询）")

    labels.setdefault("voteDailyLimitLabel", "每人每天限票")
    labels.setdefault(
        "voteDailyLimitHint",
        "大于 0 时限制每天可投票数；0 表示不按天限额（仍受每人总限票约束）。",
    )
    thicken["voteDailyLimit"] = True
    _add_feature(spec, "投票每人每天限票")

    labels.setdefault("voteAnonymousLabel", "匿名计票明细")
    labels.setdefault(
        "voteAnonymousHint",
        "开启后管理端明细与导出中的投票人显示为匿名。",
    )
    thicken["voteAnonymous"] = True
    _add_feature(spec, "投票匿名开关")

    labels.setdefault("voteResultPublishAtLabel", "结果公布时间")
    labels.setdefault(
        "voteResultDelayHint",
        "填写后，到达该时间前学生端不可看计票结果；管理端始终可看。",
    )
    labels.setdefault("voteResultDelayMsg", "结果尚未到公布时间")
    thicken["voteResultDelay"] = True
    _add_feature(spec, "投票结果对学生延迟公布")

    labels.setdefault("voteSloganLabel", "拉票文案")
    labels.setdefault("voteSloganPlaceholder", "一句话拉票（选填）")
    thicken["voteSlogan"] = True
    _add_feature(spec, "投票候选人拉票文案字段")

    labels.setdefault("voteRequireRealNameLabel", "实名后可投")
    labels.setdefault(
        "voteRealNameWarn",
        "本评选需实名后投票，请先在资料中填写真实姓名。",
    )
    thicken["voteRequireRealName"] = True
    _add_feature(spec, "投票禁刷：实名后可投")

    labels.setdefault("voteAbstainLabel", "弃权")
    labels.setdefault("voteAllowAbstainLabel", "允许弃权")
    labels.setdefault("voteAbstainHint", "开启后投票页显示弃权按钮。")
    thicken["voteAbstain"] = True
    _add_feature(spec, "投票弃权选项")

    labels.setdefault("voteTop3Hint", "实时榜前三名高亮展示。")
    labels.setdefault("voteCastLead", "按限票数选择候选人后提交。")
    thicken["voteTop3"] = True
    _add_feature(spec, "投票实时榜置顶前三")

    labels.setdefault("voteSettingsTitle", "评选规则")
    labels.setdefault("voteSettingsSaveLabel", "保存规则")


def _attach_mutual_result_menu(schema: dict[str, Any]) -> None:
    """互选结果公示：用户菜单只读入口。"""
    menus = schema.setdefault("menus", {})
    user = menus.get("user")
    if not isinstance(user, list):
        user = []
        menus["user"] = user
    if any(isinstance(m, dict) and m.get("key") == "mutual_results" for m in user):
        return
    user.append({"key": "mutual_results", "label": "互选结果公示"})


def _nail_mutual_i03(
    spec: dict[str, Any],
    schema: dict[str, Any],
    thicken: dict[str, Any],
) -> None:
    """I-03：MUTUAL 通识——调剂留痕/改志愿/附件包/盲选/互斥/公示/上限/超时婉拒/锁定/导出信/面试叠。"""
    ents = schema.setdefault("entities", {})
    archive = ents.get("archive") if isinstance(ents.get("archive"), dict) else {}
    if not isinstance(archive, dict):
        archive = {}
        ents["archive"] = archive
    ticket = ents.get("ticket") if isinstance(ents.get("ticket"), dict) else {}
    if not isinstance(ticket, dict):
        ticket = {}
        ents["ticket"] = ticket
    labels = schema.setdefault("labels", {})

    # —— 调剂记录留痕（progress.admin_adjust + 管理列表）——
    labels.setdefault("mutualAdjustLogTitle", "调剂记录")
    labels.setdefault("mutualAdjustLogLead", "查看管理端对志愿的调剂确认与驳回留痕。")
    labels.setdefault("mutualAdjustLogEmpty", "暂无调剂记录")
    thicken["mutualAdjustLog"] = True
    _add_feature(spec, "双选志愿调剂记录留痕")

    # —— 截止前改志愿 ——
    ticket["allowWishEditBeforeDeadline"] = True
    labels.setdefault("mutualEditWishLabel", "修改志愿")
    labels.setdefault("mutualEditWishHint", "志愿截止前可修改说明与志愿类型。")
    labels.setdefault("mutualEditWishDone", "志愿已更新")
    thicken["mutualEditBeforeDeadline"] = True
    _add_feature(spec, "志愿截止前修改")

    # —— 附件简介包 ——
    _ensure_archive_field(
        archive,
        {"key": "introPackUrl", "label": "附件简介包", "type": "text"},
    )
    labels.setdefault("introPackLabel", "附件简介包")
    labels.setdefault("introPackHint", "可填写简介材料链接，便于学生了解后再报志愿。")
    labels.setdefault("introPackOpenLabel", "查看简介包")
    thicken["mutualIntroPack"] = True
    _add_feature(spec, "双选附件简介包")

    # —— 盲选阶段 ——
    ticket["blindPhaseUntilDeadline"] = True
    labels.setdefault("mutualBlindPhaseLabel", "盲选中")
    labels.setdefault(
        "mutualBlindPhaseHint",
        "志愿截止前为盲选阶段，确认人暂不可见申请人详情；截止后自动揭晓。",
    )
    labels.setdefault("mutualBlindMaskedName", "盲选申请人")
    thicken["mutualBlindPhase"] = True
    _add_feature(spec, "双选盲选阶段")

    # —— 志愿互斥（同对象不可双报；复用 forceOnePerArchive）——
    ticket["forceOnePerArchive"] = True
    labels["onePerArchiveDenyMessage"] = "该对象已有进行中的志愿，不可重复申报。"
    labels.setdefault("mutualWishMutexHint", "同一对象仅可保留一条进行中的志愿。")
    thicken["mutualWishMutex"] = True
    _add_feature(spec, "双选志愿互斥")

    # —— 结果公示页 ——
    labels.setdefault("mutualResultTitle", "互选结果公示")
    labels.setdefault("mutualResultLead", "已确认互选的名单（脱敏展示）。")
    labels.setdefault("mutualResultEmpty", "暂无已公示的互选结果")
    labels.setdefault("mutualResultHint", "名单以确认结果为准，仅供查阅。")
    _attach_mutual_result_menu(schema)
    thicken["mutualResultPublicity"] = True
    _add_feature(spec, "双选结果公示")

    # —— 调剂志愿上限 ——
    if not int(ticket.get("maxAdjustWishes") or 0):
        ticket["maxAdjustWishes"] = _MUTUAL_MAX_ADJUST_WISHES
    labels.setdefault(
        "mutualAdjustCapHint",
        f"调剂志愿最多 {_MUTUAL_MAX_ADJUST_WISHES} 条进行中的申报。",
    )
    labels.setdefault("mutualAdjustCapDeny", "调剂志愿数量已达上限，请先撤销后再报。")
    thicken["mutualAdjustCap"] = True
    _add_feature(spec, "双选调剂志愿上限")

    # —— 确认超时自动婉拒（运行时 peerAccept 开启时生效）——
    ticket["allowPeerTimeoutReject"] = True
    if not int(ticket.get("peerTimeoutRejectHours") or 0):
        ticket["peerTimeoutRejectHours"] = _MUTUAL_PEER_TIMEOUT_HOURS
    labels.setdefault(
        "mutualPeerTimeoutHint",
        f"待确认超过 {int(ticket['peerTimeoutRejectHours'])} 小时将自动婉拒。",
    )
    thicken["mutualPeerTimeoutReject"] = True
    _add_feature(spec, "双选确认超时自动婉拒")

    # —— 学生端志愿锁定倒计时（加深 I-01 截止展示）——
    labels.setdefault("mutualWishLockLabel", "志愿锁定倒计时")
    labels.setdefault("mutualWishLockedLabel", "志愿已锁定")
    labels.setdefault(
        "mutualWishLockHint",
        "截止前可修改；截止后志愿锁定，不可再改。",
    )
    thicken["mutualWishLock"] = True
    _add_feature(spec, "双选志愿锁定倒计时")

    # —— 结果导出 + 通知信 ——
    labels.setdefault("mutualResultExportLabel", "导出互选结果")
    labels.setdefault("mutualResultNotifyLabel", "通知已互选学生")
    labels.setdefault("mutualResultNotifyDone", "已发送互选结果通知")
    labels.setdefault(
        "mutualResultNotifyBody",
        "你的志愿已确认互选，请到「我的志愿」查看详情。",
    )
    thicken["mutualResultExportNotify"] = True
    _add_feature(spec, "双选结果导出通知信")

    # —— 面试时段预约叠（仅文案交叉，不抢 MEETING 状态机）——
    labels.setdefault("mutualInterviewEntryTitle", "面试时段")
    labels.setdefault(
        "mutualInterviewEntryHint",
        "面试时段安排见互选公告；如需预约会议室请按当期公告指引办理。",
    )
    labels.setdefault("mutualInterviewEntryCta", "查看互选公告")
    thicken["mutualInterviewEntry"] = True
    _add_feature(spec, "双选面试时段预约叠")


def _nail_mutual_i04_tutor(
    spec: dict[str, Any],
    schema: dict[str, Any],
    thicken: dict[str, Any],
) -> None:
    """I-04 TUTOR：名额占用进度条 + 师生互评。"""
    ents = schema.setdefault("entities", {})
    archive = ents.get("archive") if isinstance(ents.get("archive"), dict) else {}
    if not isinstance(archive, dict):
        archive = {}
        ents["archive"] = archive
    labels = schema.setdefault("labels", {})

    _ensure_archive_field(
        archive, {"key": "quotaCap", "label": "名额上限", "type": "number"}
    )
    labels.setdefault("tutorQuotaBarLabel", "名额占用")
    labels.setdefault("tutorQuotaBarHint", "已占用相对名额上限的比例；余量随确认互选扣减。")
    labels.setdefault("quotaRemainHint", "名额余量")
    thicken["mutualTutorQuotaBar"] = True
    _add_feature(spec, "导师学生名额占用进度条")

    _nail_rating_skin(spec, schema, thicken, domain="DOM-MUTUAL-TUTOR")


def _nail_mutual_i04_team(
    spec: dict[str, Any],
    schema: dict[str, Any],
    thicken: dict[str, Any],
) -> None:
    """I-04 TEAM：技能标签/邀请/满员关招募/附言/退出须同意/匹配度。"""
    ents = schema.setdefault("entities", {})
    archive = ents.get("archive") if isinstance(ents.get("archive"), dict) else {}
    if not isinstance(archive, dict):
        archive = {}
        ents["archive"] = archive
    ticket = ents.get("ticket") if isinstance(ents.get("ticket"), dict) else {}
    if not isinstance(ticket, dict):
        ticket = {}
        ents["ticket"] = ticket
    labels = schema.setdefault("labels", {})

    # —— 技能标签筛选 ——
    _ensure_archive_field(
        archive, {"key": "skillTags", "label": "技能标签", "type": "text"}
    )
    labels.setdefault("skillTagsLabel", "技能标签")
    labels.setdefault("skillTagsPlaceholder", "多个标签用逗号分隔，如：Java,算法,UI")
    labels.setdefault("skillTagsFilterPlaceholder", "按技能标签筛选")
    thicken["mutualTeamSkillTags"] = True
    _add_feature(spec, "组队技能标签筛选")

    # —— 邀请站内信 ——
    labels.setdefault("teamInviteLabel", "邀请组队")
    labels.setdefault("teamInviteHint", "向同学发送组队邀请站内信。")
    labels.setdefault("teamInviteDone", "邀请已发送")
    labels.setdefault("teamInviteTitle", "组队邀请")
    labels.setdefault(
        "teamInviteBody",
        "邀请你加入组队，请到组队资料目录查看并提交志愿。",
    )
    thicken["mutualTeamInvite"] = True
    _add_feature(spec, "组队邀请站内信")

    # —— 满员自动关招募 ——
    _ensure_archive_field(
        archive,
        {
            "key": "stage",
            "label": "招募状态",
            "type": "select",
            "options": ["招募中", "已满员"],
        },
    )
    labels.setdefault("teamFullStageHint", "名额用尽后自动变为已满员，暂不可再报。")
    thicken["mutualTeamFullClose"] = True
    _add_feature(spec, "组队满员自动关招募")

    # —— 附言必填 ——
    ticket["requireRemark"] = True
    labels.setdefault("remarkLabel", "申请附言")
    labels.setdefault("teamRemarkRequired", "请填写申请附言后再提交")
    thicken["mutualTeamRemarkRequired"] = True
    _add_feature(spec, "组队申请附言必填")

    # —— 退出须队长同意 ——
    labels.setdefault("teamExitRequestLabel", "申请退出")
    labels.setdefault("teamExitRequestHint", "退出须队长同意后生效。")
    labels.setdefault("teamExitRequestDone", "已提交退出申请，等待队长处理")
    labels.setdefault("teamExitApproveLabel", "同意退出")
    labels.setdefault("teamExitRejectLabel", "挽留/拒绝退出")
    labels.setdefault("teamExitPendingLabel", "退出待确认")
    thicken["mutualTeamExitNeedOwner"] = True
    _add_feature(spec, "组队退出须队长同意")

    # —— 技能匹配度（浅计数）——
    labels.setdefault("teamSkillMatchLabel", "技能匹配")
    labels.setdefault(
        "teamSkillMatchHint",
        "按标签重合数量提示匹配度，仅供参考。",
    )
    labels.setdefault("teamSkillMatchEmpty", "填写技能标签后可看重合数")
    thicken["mutualTeamSkillMatch"] = True
    _add_feature(spec, "组队技能匹配度提示")


def _nail_carpool_i05(
    spec: dict[str, Any],
    schema: dict[str, Any],
    thicken: dict[str, Any],
) -> None:
    """I-05 CARPOOL：满员关行程 / 提醒 / 分摊·偏好·途经·行李·校区 / 余座 / 锁座 / 爽约 / AA / 脱敏 / 重复检测。"""
    ents = schema.setdefault("entities", {})
    archive = ents.get("archive") if isinstance(ents.get("archive"), dict) else {}
    if not isinstance(archive, dict):
        archive = {}
        ents["archive"] = archive
    labels = schema.setdefault("labels", {})

    # —— 满员自动关闭行程（复用 stock + stage 开放↔已满）——
    _ensure_archive_field(
        archive,
        {
            "key": "stage",
            "label": "行程状态",
            "type": "select",
            "options": ["开放", "已满"],
        },
    )
    labels.setdefault("carpoolFullStageHint", "座位满后行程自动关闭，暂不可再报。")
    thicken["carpoolFullClose"] = True
    _add_feature(spec, "意向人数满自动关闭行程")

    # —— 座位余量展示（quota 可视化）——
    labels.setdefault("carpoolSeatRemainLabel", "剩余座位")
    labels.setdefault("carpoolSeatRemainHint", "确认同行后扣减余座。")
    thicken["carpoolSeatRemain"] = True
    _add_feature(spec, "拼车座位余量展示")

    # —— 校区字典（种子名单 + 下拉；管理/用户同读）——
    _ensure_archive_field(
        archive, {"key": "startCampus", "label": "出发校区", "type": "select"}
    )
    _ensure_archive_field(
        archive, {"key": "endCampus", "label": "到达校区", "type": "select"}
    )
    labels.setdefault("carpoolCampusStartLabel", "出发校区")
    labels.setdefault("carpoolCampusEndLabel", "到达校区")
    labels.setdefault("carpoolCampusPlaceholder", "选择校区")
    labels.setdefault(
        "carpoolCampusDictHint",
        "请从校区名单中选择出发与到达校区。",
    )
    labels.setdefault("carpoolCampusOptions", _CARPOOL_CAMPUS_OPTIONS)
    thicken["carpoolCampusDict"] = True
    _add_feature(spec, "拼车起点终点校区字典")

    # —— 途经点文本（≠地图）——
    _ensure_archive_field(
        archive, {"key": "viaPoints", "label": "途经点", "type": "textarea"}
    )
    labels.setdefault("viaPointsLabel", "途经点")
    labels.setdefault("viaPointsPlaceholder", "多个途经点用逗号或换行分隔")
    labels.setdefault("viaPointsHint", "填写途经地点文字说明，不提供地图导航。")
    thicken["carpoolViaPoints"] = True
    _add_feature(spec, "拼车途经点文本")

    # —— 费用分摊备注（真列；≠支付）——
    _ensure_archive_field(
        archive, {"key": "shareNote", "label": "费用分摊说明", "type": "textarea"}
    )
    labels.setdefault("shareNoteLabel", "费用分摊说明")
    labels.setdefault("shareNotePlaceholder", "如：油费 AA、过路费各付一半")
    labels.setdefault("shareNoteHint", "仅作同行协商备注，不涉及在线支付。")
    thicken["carpoolShareNote"] = True
    _add_feature(spec, "拼车费用分摊备注（非支付）")

    # —— 性别/人数偏好备注 ——
    _ensure_archive_field(
        archive, {"key": "prefNote", "label": "同行偏好", "type": "text"}
    )
    labels.setdefault("prefNoteLabel", "同行偏好")
    labels.setdefault("prefNotePlaceholder", "如：限女生、最多两人")
    labels.setdefault("prefNoteHint", "写明人数或性别等同行偏好，供对方参考。")
    thicken["carpoolPrefNote"] = True
    _add_feature(spec, "拼车性别/人数偏好备注")

    # —— 行李件数 ——
    _ensure_archive_field(
        archive, {"key": "luggageCount", "label": "行李件数", "type": "number"}
    )
    labels.setdefault("luggageCountLabel", "行李件数")
    labels.setdefault("luggageCountHint", "大件行李请如实填写，方便安排座位。")
    thicken["carpoolLuggage"] = True
    _add_feature(spec, "拼车行李件数备注")

    # —— 总费用 + AA 计算器（总费用落库；FE 除法展示）——
    _ensure_archive_field(
        archive, {"key": "fareTotalYuan", "label": "预计总费用", "type": "number"}
    )
    labels.setdefault("fareTotalLabel", "预计总费用")
    labels.setdefault("fareTotalHint", "填写预计总费用，系统按人数估算人均（非支付）。")
    labels.setdefault("carpoolAaLabel", "人均分摊")
    labels.setdefault("carpoolAaHint", "按余座与已占座估算，仅供参考。")
    thicken["carpoolAaCalc"] = True
    _add_feature(spec, "拼车费用AA计算器")

    # —— 出发前提醒站内信 ——
    _ensure_archive_field(
        archive,
        {"key": "remindBeforeMinutes", "label": "出发前提醒（分钟）", "type": "number"},
    )
    labels.setdefault("carpoolDepartRemindLeadLabel", "出发前提醒")
    labels.setdefault(
        "carpoolDepartRemindHint",
        "出发前按设置分钟数向车主与已确认乘客发送站内信。",
    )
    labels.setdefault("carpoolDepartRemindTitle", "出发提醒")
    labels.setdefault(
        "carpoolDepartRemindBody",
        "行程即将出发，请按时到达约定地点。",
    )
    labels.setdefault("carpoolDepartRemindNoneLabel", "未设置出发提醒")
    thicken["carpoolDepartRemind"] = True
    _add_feature(spec, "拼车出发前提醒站内信")

    # —— 乘客确认后锁座 ——
    labels.setdefault("carpoolSeatLockedLabel", "已锁座")
    labels.setdefault("carpoolSeatLockedHint", "车主确认后锁定座位，取消将计入爽约。")
    thicken["carpoolSeatLock"] = True
    _add_feature(spec, "拼车乘客确认后锁座")

    # —— 取消惩罚 / 爽约计数 ——
    labels.setdefault("carpoolCancelPenaltyLabel", "取消同行")
    labels.setdefault(
        "carpoolCancelPenaltyHint",
        "确认后取消将记一次爽约，请尽量守约。",
    )
    labels.setdefault("carpoolNoShowCountLabel", "爽约次数")
    labels.setdefault("carpoolNoShowCountHint", "确认后取消会累计爽约次数。")
    thicken["carpoolCancelPenalty"] = True
    _add_feature(spec, "拼车取消惩罚提示（爽约计数）")

    # —— 评价后电话脱敏 ——
    labels.setdefault(
        "carpoolPhoneMaskedHint",
        "评价完成后对方联系方式已隐藏。",
    )
    thicken["carpoolPhoneMaskAfterRate"] = True
    _add_feature(spec, "拼车评价后不可见对方电话")

    # —— 行程重复发布检测 ——
    labels.setdefault(
        "carpoolDupTripDeny",
        "你已发布相近出发时间的同行行程，请勿重复发布。",
    )
    thicken["carpoolDupTripCheck"] = True
    _add_feature(spec, "拼车行程重复发布检测")


def _nail_dating_i02(
    spec: dict[str, Any],
    schema: dict[str, Any],
    thicken: dict[str, Any],
) -> None:
    """I-02：DATING 域皮——完整度 / 互关 / 见面意向 / 举报时限 / 审驳 / 筛选 / 黑名单 / 相册审 / 活动叠。"""
    from app.bake.features.apply_thicken import (
        _attach_apply_blacklist_menus,
        _force_gallery,
    )

    ents = schema.setdefault("entities", {})
    archive = ents.get("archive") if isinstance(ents.get("archive"), dict) else {}
    if not isinstance(archive, dict):
        archive = {}
        ents["archive"] = archive
    ticket = ents.get("ticket") if isinstance(ents.get("ticket"), dict) else {}
    if not isinstance(ticket, dict):
        ticket = {}
        ents["ticket"] = ticket
    labels = schema.setdefault("labels", {})
    caps = list(spec.get("capabilities") or [])

    # —— 资料完整度（复用 Profile 进度条 + 婚恋提示文案）——
    labels.setdefault("profileCompletenessLabel", "资料完善度")
    labels.setdefault(
        "datingCompletenessHint",
        "完善城市、学历与年龄段，更容易被看到并牵线。",
    )
    labels.setdefault("datingCompletenessMissingLead", "待完善：")
    thicken["datingProfileCompleteness"] = True
    _add_feature(spec, "婚恋资料完整度提示")

    # —— 互相关注（复用 UserFollowStore；运行时映射 CONTENT_FOLLOWERS_ONLY_COMMENT）——
    labels.setdefault("followUserLabel", "关注")
    labels.setdefault("unfollowUserLabel", "取消关注")
    labels.setdefault("datingFollowDone", "已关注")
    labels.setdefault("datingUnfollowDone", "已取消关注")
    thicken["datingUserFollow"] = True
    _add_feature(spec, "婚恋互相关注")

    # —— 见面意向（轻单字段 meetIntent；非支付）——
    ticket["meetIntentOptions"] = list(
        ticket.get("meetIntentOptions") or _MEET_INTENT_OPTIONS
    )
    labels.setdefault("meetIntentLabel", "见面意向")
    labels.setdefault("meetIntentPlaceholder", "请选择见面意向")
    labels.setdefault("meetIntentRequired", "请选择见面意向")
    thicken["datingMeetIntent"] = True
    _add_feature(spec, "婚恋见面意向登记")

    # —— 举报处理时限：I-11 统一按 content_report 加深（此处不再重复）——

    # —— 资料审核驳回理由（复用 publishReview 管道）——
    archive["userPublish"] = True
    archive["publishReview"] = True
    _ensure_archive_field(
        archive, {"key": "rejectReason", "label": "驳回理由", "type": "text"}
    )
    labels.setdefault("rejectReasonLabel", "驳回理由")
    labels.setdefault("rejectReasonPlaceholder", "请填写驳回理由，便于对方修改后再提交")
    labels.setdefault("rejectReasonRequired", "请填写驳回理由")
    labels.setdefault("datingRejectReasonLead", "资料未通过：")
    thicken["datingRejectReason"] = True
    _add_feature(spec, "婚恋资料审核驳回理由")

    # —— 理想对象条件筛选 ——
    _ensure_archive_field(
        archive, {"key": "ageYears", "label": "年龄", "type": "number"}
    )
    _ensure_archive_field(
        archive, {"key": "idealCity", "label": "理想城市", "type": "text"}
    )
    _ensure_archive_field(
        archive, {"key": "idealAgeMin", "label": "理想年龄下限", "type": "number"}
    )
    _ensure_archive_field(
        archive, {"key": "idealAgeMax", "label": "理想年龄上限", "type": "number"}
    )
    labels.setdefault("datingFilterCityLabel", "所在城市")
    labels.setdefault("datingFilterCityPlaceholder", "按城市筛选")
    labels.setdefault("datingFilterAgeLabel", "年龄")
    labels.setdefault("datingFilterAgeMinPlaceholder", "最小")
    labels.setdefault("datingFilterAgeMaxPlaceholder", "最大")
    labels.setdefault("idealCityLabel", "理想城市")
    labels.setdefault("idealAgeLabel", "理想年龄段")
    thicken["datingIdealFilter"] = True
    _add_feature(spec, "婚恋理想对象条件筛选")

    # —— 黑名单（复用 ApplyBlacklistStore）——
    schema["applyBlacklist"] = True
    ticket["allowApplyBlacklist"] = True
    labels["applyBlacklistMenuLabel"] = "牵线黑名单"
    labels["applyBlacklistTitle"] = "牵线黑名单"
    labels["applyBlacklistLead"] = "维护暂不可发起牵线的账号；名单内用户提交牵线时将被拒绝。"
    labels["applyBlacklistDenyMessage"] = "当前账号暂不可发起牵线，请联系红娘专员。"
    _attach_apply_blacklist_menus(schema)
    thicken["datingBlacklist"] = True
    _add_feature(spec, "婚恋黑名单")

    # —— 资料相册审核（复用 gallery + album_audit_status）——
    _force_gallery(spec, schema)
    _ensure_archive_field(
        archive,
        {
            "key": "albumAuditStatus",
            "label": "相册审核",
            "type": "select",
            "options": ["none", "pending", "approved", "rejected"],
        },
    )
    labels.setdefault("albumAuditLabel", "相册审核")
    labels.setdefault("albumAuditPending", "相册待审")
    labels.setdefault("albumAuditApproved", "相册已通过")
    labels.setdefault("albumAuditRejected", "相册未通过")
    labels.setdefault("albumAuditApproveAction", "通过相册")
    labels.setdefault("albumAuditRejectAction", "驳回相册")
    labels.setdefault("albumAuditHiddenHint", "相册审核通过后才会公开展示。")
    thicken["datingAlbumAudit"] = True
    _add_feature(spec, "婚恋资料相册审核")

    # —— 活动报名入口叠（仅文案交叉，不抢 ACTIVITY 状态机）——
    labels.setdefault("datingActivityEntryTitle", "线下联谊")
    labels.setdefault(
        "datingActivityEntryHint",
        "线下联谊安排见交友公告；报名入口以当期公告为准。",
    )
    labels.setdefault("datingActivityEntryCta", "查看交友公告")
    thicken["datingActivityEntry"] = True
    _add_feature(spec, "婚恋活动报名入口叠")


def _nail_timebank_i06(
    spec: dict[str, Any],
    schema: dict[str, Any],
    thicken: dict[str, Any],
) -> None:
    """I-06 TIMEBANK：时长榜/兑换导出/技能认证/目录/信用分/发布须审/冻结/证明附件/申诉/转让/清零说明。"""
    from app.bake.schema.menu_utils import ensure_menu

    ents = schema.setdefault("entities", {})
    archive = ents.get("archive") if isinstance(ents.get("archive"), dict) else {}
    if not isinstance(archive, dict):
        archive = {}
        ents["archive"] = archive
    ticket = ents.get("ticket") if isinstance(ents.get("ticket"), dict) else {}
    if not isinstance(ticket, dict):
        ticket = {}
        ents["ticket"] = ticket
    labels = schema.setdefault("labels", {})
    menus = schema.setdefault("menus", {})
    user_menus = menus.setdefault("user", [])
    admin_menus = menus.setdefault("admin", [])

    # —— 时长排行榜 ——
    labels.setdefault("tbRankTitle", "时长排行榜")
    labels.setdefault("tbRankLead", "按账户余额小时数排序，仅供参考。")
    labels.setdefault("tbRankHoursLabel", "时长（小时）")
    ensure_menu(
        user_menus,
        "tb_rank",
        {"key": "tb_rank", "label": "时长排行"},
        before_key="content",
    )
    thicken["timebankRank"] = True
    _add_feature(spec, "时间银行时长排行榜")

    # —— 兑换记录对账导出 ——
    labels.setdefault("tbLedgerExportLabel", "导出流水")
    labels.setdefault("tbLedgerExportHint", "导出当前筛选下的时长流水，便于对账。")
    thicken["timebankLedgerExport"] = True
    _add_feature(spec, "兑换记录对账导出")

    # —— 技能标签认证勾选 ——
    labels.setdefault("tbSkillTagsLabel", "技能标签")
    labels.setdefault("tbSkillTagsPlaceholder", "多个标签用逗号分隔")
    labels.setdefault("tbSkillCertifiedLabel", "技能已认证")
    labels.setdefault("tbSkillCertifiedHint", "管理端勾选认证后，资料页显示已认证。")
    thicken["timebankSkillCert"] = True
    _add_feature(spec, "时间银行技能标签认证勾选")

    # —— 兑换商品目录（浅表；≠商城）——
    labels.setdefault("tbCatalogTitle", "兑换目录")
    labels.setdefault("tbCatalogLead", "用时长兑换互助权益，不涉及在线支付。")
    labels.setdefault("tbCatalogCostLabel", "所需时长")
    labels.setdefault("tbCatalogRedeemLabel", "兑换")
    labels.setdefault("tbCatalogRedeemDone", "已兑换")
    labels.setdefault("tbCatalogEmpty", "暂无可兑换项目")
    labels.setdefault("tbCatalogAdminTitle", "兑换目录维护")
    ensure_menu(
        user_menus,
        "tb_catalog",
        {"key": "tb_catalog", "label": "兑换目录"},
        before_key="content",
    )
    ensure_menu(
        admin_menus,
        "tb_catalog_admin",
        {"key": "tb_catalog_admin", "label": "兑换目录", "superOnly": True},
        before_key="content",
    )
    thicken["timebankCatalog"] = True
    _add_feature(spec, "时间银行兑换商品目录")

    # —— 信用分（爽约扣分）——
    labels.setdefault("tbCreditScoreLabel", "信用分")
    labels.setdefault(
        "tbCreditScoreHint",
        "确认后取消或爽约会扣减信用分，分数过低时部分兑换可能受限。",
    )
    thicken["timebankCreditScore"] = True
    _add_feature(spec, "时间银行信用分（爽约扣分）")

    # —— 发布须审 ——
    archive["userPublish"] = True
    archive["publishReview"] = True
    labels.setdefault("tbPublishReviewHint", "服务事项发布后需审核通过才会公开展示。")
    thicken["timebankPublishReview"] = True
    _add_feature(spec, "时间银行发布须审")

    # —— 时长冻结 ——
    labels.setdefault("tbFrozenHoursLabel", "冻结时长")
    labels.setdefault(
        "tbFrozenHoursHint",
        "纠纷处理期间可冻结部分时长，冻结部分不可核销或转让。",
    )
    labels.setdefault("tbFreezeAction", "冻结时长")
    labels.setdefault("tbUnfreezeAction", "解冻")
    thicken["timebankFreeze"] = True
    _add_feature(spec, "时间银行时长冻结（纠纷）")

    # —— 技能证明附件 ——
    ticket["requireAttach"] = True
    labels.setdefault("attachLabel", "技能证明附件")
    labels.setdefault("tbSkillAttachHint", "提交核销时请上传技能证明附件。")
    thicken["timebankSkillAttach"] = True
    _add_feature(spec, "时间银行技能证明附件")

    # —— 申诉单 ——
    labels.setdefault("tbAppealTitle", "时长申诉")
    labels.setdefault("tbAppealLead", "对核销或流水有异议时可提交申诉。")
    labels.setdefault("tbAppealReasonLabel", "申诉说明")
    labels.setdefault("tbAppealSubmitLabel", "提交申诉")
    labels.setdefault("tbAppealDone", "申诉已提交")
    labels.setdefault("tbAppealAdminTitle", "申诉处理")
    labels.setdefault("tbAppealApproveLabel", "通过")
    labels.setdefault("tbAppealRejectLabel", "驳回")
    ensure_menu(
        user_menus,
        "tb_appeal",
        {"key": "tb_appeal", "label": "时长申诉"},
        before_key="content",
    )
    ensure_menu(
        admin_menus,
        "tb_appeal_admin",
        {"key": "tb_appeal_admin", "label": "时长申诉", "superOnly": True},
        before_key="content",
    )
    thicken["timebankAppeal"] = True
    _add_feature(spec, "时间银行申诉单")

    # —— 时长转让 ——
    labels.setdefault("tbTransferLabel", "转让时长")
    labels.setdefault("tbTransferHint", "将自己的可用时长转让给同学，不涉及货币。")
    labels.setdefault("tbTransferToLabel", "对方账号")
    labels.setdefault("tbTransferHoursLabel", "转让小时")
    labels.setdefault("tbTransferDone", "已转让")
    thicken["timebankTransfer"] = True
    _add_feature(spec, "时间银行时长转让")

    # —— 清零规则说明（管理端可改正文，用户端展示）——
    labels.setdefault("tbClearRuleTitle", "时长清零规则")
    labels.setdefault(
        "tbClearRuleLead",
        "闲置过久的时长可能按当期规则清零，详见下方说明。",
    )
    labels.setdefault("tbClearRuleSaveLabel", "保存清零说明")
    thicken["timebankClearRule"] = True
    _add_feature(spec, "时间银行时长清零规则说明")


def _nail_report_deadline_when_cap(
    spec: dict[str, Any],
    schema: dict[str, Any],
    thicken: dict[str, Any],
    *,
    domain: str,
) -> None:
    """content_report 已挂时：处理时限提醒（婚恋文案 / 通识文案）。"""
    caps = set(spec.get("capabilities") or [])
    if "content_report" not in caps:
        return
    labels = schema.setdefault("labels", {})
    if not int(schema.get("reportHandleDays") or 0):
        schema["reportHandleDays"] = _DATING_REPORT_HANDLE_DAYS
    days = int(schema["reportHandleDays"])
    labels.setdefault("reportDeadlineLabel", "处理时限")
    labels.setdefault("reportOverdueLabel", "已超时")
    if domain == "DOM-DATING":
        labels.setdefault(
            "datingReportDeadlineHint",
            f"举报须在 {days} 日内处理完毕。",
        )
        thicken["datingReportDeadline"] = True
        _add_feature(spec, "婚恋举报处理时限提醒")
    else:
        labels.setdefault(
            "reportDeadlineHint",
            f"举报须在 {days} 日内处理完毕。",
        )
    thicken["reportDeadlineIsland"] = True
    _add_feature(spec, "举报处理时限提醒（已挂 content_report）")


def _nail_i11_cap_islands(
    spec: dict[str, Any],
    schema: dict[str, Any],
    thicken: dict[str, Any],
    *,
    domain: str,
) -> None:
    """I-11：仅当能力已挂时加深；禁止未挂 cap 硬开邻组岛。"""
    from app.bake.features.favorites import FAVORITES_CAP, attach_favorites_menus

    caps = set(spec.get("capabilities") or [])
    labels = schema.setdefault("labels", {})
    ents = schema.setdefault("entities", {})
    ticket = ents.get("ticket") if isinstance(ents.get("ticket"), dict) else {}
    if not isinstance(ticket, dict):
        ticket = {}
        ents["ticket"] = ticket

    # —— favorites：菜单保全 + 清单导出提示（心动皮由 I-01 钉）——
    if FAVORITES_CAP in caps:
        attach_favorites_menus(
            schema,
            page_lead=str(
                labels.get("favoritesPageLead")
                or "收藏感兴趣的内容，便于再次查看。"
            ),
        )
        if domain == "DOM-DATING":
            labels.setdefault(
                "favShareHint",
                "可导出心动清单，便于整理意向对象。",
            )
        else:
            labels.setdefault("favoritesPageTitle", "我的收藏")
            labels.setdefault(
                "favoritesPageLead",
                "收藏感兴趣的内容，便于再次查看。",
            )
            labels.setdefault("favoritesEmptyTitle", "暂无收藏")
            labels.setdefault("favoritesEmptyDesc", "去浏览加一加吧。")
            labels.setdefault("favoritesCancelLabel", "取消收藏")
            labels.setdefault(
                "favShareHint",
                "可导出收藏清单，便于对照查看。",
            )
        thicken["favoritesIsland"] = True
        _add_feature(spec, "收藏岛加深（已挂 favorites）")

    # —— dm：私信页文案加深（禁止 SDK）——
    if "dm" in caps:
        if domain == "DOM-DATING":
            labels.setdefault("dmPageTitle", "私信")
            labels.setdefault(
                "dmPageLead",
                "与心仪对象礼貌沟通；本系统仅站内短轮询，不支持第三方即时通讯。",
            )
            labels.setdefault(
                "dmEmptyPeers",
                "暂无会话，可从资料页发起私信。",
            )
            labels.setdefault("dmEmptyChat", "选择左侧会话开始聊天。")
        else:
            labels.setdefault(
                "dmPageLead",
                "站内私信一对一沟通；打开会话后自动刷新，不支持第三方 IM。",
            )
        thicken["dmIsland"] = True
        _add_feature(spec, "私信岛加深（已挂 dm）")

    # —— allowRating：管理端评价可见加深 ——
    if ticket.get("allowRating"):
        labels.setdefault(
            "ratingAdminLead",
            "查看用户提交的星级与短评；可筛「仅已评分」。",
        )
        labels.setdefault("ratingFilterRatedLabel", "仅已评分")
        thicken["ratingIsland"] = True
        _add_feature(spec, "单据评价岛加深（已开 allowRating）")

    # —— content_report：处理时限 ——
    _nail_report_deadline_when_cap(spec, schema, thicken, domain=domain)


def apply_interact_thicken_to_spec(
    spec: dict[str, Any], proposal_text: str = ""
) -> dict[str, Any]:
    """按域默认加厚互动组 schema（只增不减；非本组原样返回）。"""
    del proposal_text  # 通识/域皮不扫词；I-11 读已合并的 capabilities
    domain = str(spec.get("domain") or "")
    if domain not in INTERACT_DOMAINS:
        return spec

    schema = _live_schema(spec)
    labels = schema.setdefault("labels", {})
    thicken = (
        schema.get("interactThicken")
        if isinstance(schema.get("interactThicken"), dict)
        else {}
    )
    schema["interactThicken"] = thicken
    thicken["core"] = True
    _add_feature(spec, "互动组加厚")

    # —— I-01：半截钉齐 ——
    if domain == "DOM-DATING":
        _nail_dating_favorites(spec, schema, thicken)
        _nail_dating_i02(spec, schema, thicken)
    if domain in _RATING_SKIN_DOMAINS:
        _nail_rating_skin(spec, schema, thicken, domain=domain)
    if domain in _MUTUAL_DOMAINS:
        _nail_mutual_deadline(spec, schema, thicken)
        _nail_mutual_i03(spec, schema, thicken)
    if domain == "DOM-MUTUAL-TUTOR":
        _nail_mutual_i04_tutor(spec, schema, thicken)
    if domain == "DOM-MUTUAL-TEAM":
        _nail_mutual_i04_team(spec, schema, thicken)
    if domain == "DOM-CARPOOL":
        _nail_carpool_i05(spec, schema, thicken)
    if domain == "DOM-TIMEBANK":
        _nail_timebank_i06(spec, schema, thicken)
    if domain == "DOM-EXAM":
        _nail_exam_grade_contract(spec, schema, thicken)
        _nail_exam_i07(spec, schema, thicken)
        _nail_exam_i08(spec, schema, thicken)
    if domain == "DOM-SURVEY":
        _nail_survey_i09(spec, schema, thicken)
    if domain == "DOM-VOTE":
        _nail_vote_i10(spec, schema, thicken)

    # —— I-11：能力岛加深（读当前已挂 caps / allowRating；未挂不硬开）——
    _nail_i11_cap_islands(spec, schema, thicken, domain=domain)

    del labels  # labels 已通过 setdefault 写入 schema
    return spec
