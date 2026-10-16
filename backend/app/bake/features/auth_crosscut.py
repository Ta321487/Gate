"""§0 X-AUTH 通识横切：锁定/改密/密保 + XA-02 会话踢下线/改绑/激活等。

硬约束：
- 禁止 *_thicken / 具名 DOM 专线；
- 阈值进 AppPolicy，禁止成排 thesis.auth-*；
- 密保顶邮箱找回；改绑/激活用图形验证码与站内码；≠ 真 SMTP / 短信。

口径拆分（别再「全挂再关一半」）：
- 会话 / 登录日志 / 注销申请：基线常开（平台账号卫生）。
- 邀请码：开题写到才挂菜单、才强制注册、才建码表/灌种子；未写则菜单、表、源码都不留。
"""

from __future__ import annotations

import re
from typing import Any

from app.bake.proposal_lexicon import keyword_mentioned

AUTH_CROSSCUT_COLUMNS: list[tuple[str, str]] = [
    ("failed_login_count", "INT NOT NULL DEFAULT 0"),
    ("lock_until", "DATETIME NULL"),
    ("must_change_password", "TINYINT NOT NULL DEFAULT 0"),
    ("password_changed_at", "DATETIME NULL"),
    ("security_question", "VARCHAR(128) NULL"),
    ("security_answer_hash", "VARCHAR(128) NULL"),
    ("email_activated", "TINYINT NOT NULL DEFAULT 0"),
    ("activation_code", "VARCHAR(16) NULL"),
    ("real_name_acked", "TINYINT NOT NULL DEFAULT 0"),
]

AUTH_CROSSCUT_TABLES_CORE: tuple[str, ...] = (
    "sys_auth_session",
    "sys_login_log",
    "sys_account_cancel",
)
AUTH_CROSSCUT_INVITE_TABLE = "sys_invite_code"
# 兼容旧引用：常开 + 邀请表名（邀请表是否落库看 invite_enabled）
AUTH_CROSSCUT_TABLES: tuple[str, ...] = AUTH_CROSSCUT_TABLES_CORE + (
    AUTH_CROSSCUT_INVITE_TABLE,
)

_INVITE_TERMS = (
    "邀请码",
    "邀请注册",
    "注册邀请",
    "限本校",
    "本校注册",
    "凭邀请",
    "邀请制",
)

_AUTH_LABELS_CORE: dict[str, str] = {
    "passwordStrengthHint": "密码至少 6 位，建议包含字母和数字",
    "accountLockedHint": "尝试次数过多，请稍后再登录",
    "mustChangePasswordHint": "请先修改密码后再使用系统",
    "forgotPasswordLink": "忘记密码",
    "rememberLoginLabel": "记住登录",
    "trialLoginFillLabel": "填入试用账号",
    "sessionIdleHint": "登录已超时，请重新登录",
    "securityQuestionLabel": "密保问题",
    "securityAnswerLabel": "密保答案",
    "phoneDupHint": "该手机号已被使用，请更换",
    "studentNoDupHint": "该学号或工号已被绑定，请核对",
    "phoneFormatHint": "手机号格式不正确（11 位）",
    "emailFormatHint": "邮箱格式不正确",
    "captchaRefreshHint": "点击刷新验证码",
    "captchaFailHint": "验证码多次错误，请看清后重试",
    "agreeTermsLabel": "我已阅读并同意用户协议与隐私政策",
    "mustActivateEmailHint": "请先用站内激活码完成账号激活",
    "activationCodeLabel": "激活码",
    "changeContactHint": "修改手机号或邮箱需填写验证码",
    "realNameAckLabel": "我确认以上姓名信息属实",
    "remoteLoginHint": "检测到与上次不同的登录来源，请确认是否本人操作",
    "cancelAccountLabel": "申请注销账号",
    "onlineSessionsMenu": "在线用户",
}

_AUTH_LABELS_INVITE: dict[str, str] = {
    "inviteCodeLabel": "邀请码",
    "inviteCodeHint": "请填写注册邀请码",
    "inviteCodesMenu": "邀请码",
}

_INVITE_LABEL_KEYS = frozenset(_AUTH_LABELS_INVITE.keys())


_SEED_MUST_CHANGE = (
    "\n-- 业务试用账号首次登录须改密\n"
    "UPDATE sys_user SET must_change_password=1 "
    "WHERE username='user' AND IFNULL(super_admin,0)=0;\n"
)

_SEED_EMAIL_ACTIVATED = (
    "\n-- 种子账号一律免激活闸（新注册仍走默认未激活）\n"
    "UPDATE sys_user SET email_activated=1;\n"
)

_XA02_CORE_TABLES_SQL = """
-- 会话登记、登录记录、注销申请
CREATE TABLE IF NOT EXISTS sys_auth_session (
  session_id VARCHAR(128) NOT NULL,
  username VARCHAR(64) NOT NULL,
  ip VARCHAR(64) NOT NULL DEFAULT '',
  user_agent VARCHAR(255) NOT NULL DEFAULT '',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  last_seen_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  kicked TINYINT NOT NULL DEFAULT 0,
  PRIMARY KEY (session_id),
  KEY idx_auth_sess_user (username, kicked)
);

CREATE TABLE IF NOT EXISTS sys_login_log (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  username VARCHAR(64) NOT NULL,
  ip VARCHAR(64) NOT NULL DEFAULT '',
  user_agent VARCHAR(255) NOT NULL DEFAULT '',
  geo_hint VARCHAR(64) NOT NULL DEFAULT '',
  success TINYINT NOT NULL DEFAULT 1,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  KEY idx_login_log_user (username, created_at)
);

CREATE TABLE IF NOT EXISTS sys_account_cancel (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  username VARCHAR(64) NOT NULL,
  reason VARCHAR(255) NOT NULL DEFAULT '',
  status VARCHAR(16) NOT NULL DEFAULT 'pending',
  admin_note VARCHAR(255) NOT NULL DEFAULT '',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  reviewed_at DATETIME NULL,
  KEY idx_cancel_user (username, status)
);
"""

_INVITE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS sys_invite_code (
  code VARCHAR(64) NOT NULL,
  label VARCHAR(128) NOT NULL DEFAULT '',
  max_uses INT NOT NULL DEFAULT 0,
  used_count INT NOT NULL DEFAULT 0,
  enabled TINYINT NOT NULL DEFAULT 1,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (code)
);
"""

_INVITE_SEED_SQL = """
INSERT INTO sys_invite_code (code, label, max_uses, used_count, enabled)
SELECT 'INVITE2026', '通用邀请码', 0, 0, 1 FROM DUAL
WHERE NOT EXISTS (SELECT 1 FROM sys_invite_code WHERE code='INVITE2026');
INSERT INTO sys_invite_code (code, label, max_uses, used_count, enabled)
SELECT 'WELCOME01', '新客邀请码', 200, 0, 1 FROM DUAL
WHERE NOT EXISTS (SELECT 1 FROM sys_invite_code WHERE code='WELCOME01');
"""


def scan_invite_codes(text: str, title: str = "") -> bool:
    """开题写到邀请制/邀请码才挂；「电子商务」等无关词不命中。"""
    blob = f"{title or ''}\n{text or ''}"
    return any(keyword_mentioned(blob, kw, ignore_contrast=True) for kw in _INVITE_TERMS)


def ensure_auth_crosscut_sql(
    sql: str,
    *,
    invite_enabled: bool = False,
) -> str:
    """向 sys_user 常开注入 X-AUTH 列；会话/注销常开；邀请码表+种子仅开题命中时灌。"""
    from app.bake.sql.ddl_edit import (
        CREATE_TABLE_RE,
        inject_missing_columns,
        strip_trailing_comma_before_close,
    )

    def repl(m: re.Match[str]) -> str:
        head, table, body, tail = m.group(1), m.group(2), m.group(3), m.group(4)
        if table.lower() != "sys_user":
            return m.group(0)
        body = inject_missing_columns(body, AUTH_CROSSCUT_COLUMNS)
        body = strip_trailing_comma_before_close(body)
        return f"{head}{body}{tail}"

    out = CREATE_TABLE_RE.sub(repl, sql)
    if "CREATE TABLE IF NOT EXISTS sys_auth_session" not in out:
        out = out.rstrip() + "\n" + _XA02_CORE_TABLES_SQL
    if invite_enabled:
        if "CREATE TABLE IF NOT EXISTS sys_invite_code" not in out:
            out = out.rstrip() + "\n" + _INVITE_TABLE_SQL
        if "INVITE2026" not in out and "CAMPUS2026" not in out:
            out = out.rstrip() + "\n" + _INVITE_SEED_SQL
    else:
        # 关邀请：表 + 种子都剔掉，避免 ZIP/库里空壳码池被答辩追问
        out = CREATE_TABLE_RE.sub(
            lambda m: (
                ""
                if m.group(2).lower() == "sys_invite_code"
                else m.group(0)
            ),
            out,
        )
        out = re.sub(
            r"(?is)INSERT\s+INTO\s+`?sys_invite_code`?\b.*?;\s*",
            "",
            out,
        )
    marker = "业务试用账号首次登录须改密"
    if marker not in out:
        out = out.rstrip() + _SEED_MUST_CHANGE
    act_marker = "种子账号一律免激活闸"
    if act_marker not in out:
        out = out.rstrip() + _SEED_EMAIL_ACTIVATED
    return out


def apply_auth_crosscut_to_spec(spec: dict[str, Any], proposal_text: str = "") -> dict[str, Any]:
    """会话菜单常开；邀请码菜单/强制注册仅开题扫到才挂，否则摘掉。"""
    from app.bake.schema.menu_utils import ensure_menu

    title = str(spec.get("title") or "")
    want_invite = scan_invite_codes(proposal_text or "", title)

    schema = dict(spec.get("schema") or {})
    labels = dict(schema.get("labels") or {})
    for key, val in _AUTH_LABELS_CORE.items():
        labels.setdefault(key, val)
    if want_invite:
        for key, val in _AUTH_LABELS_INVITE.items():
            labels.setdefault(key, val)
    else:
        for key in _INVITE_LABEL_KEYS:
            labels.pop(key, None)
    schema["labels"] = labels

    policy = dict(schema.get("authPolicy") or {})
    policy.setdefault("lockMaxAttempts", 5)
    policy.setdefault("lockMinutes", 15)
    policy.setdefault("passwordMaxDays", 0)
    policy.setdefault("rememberDays", 7)
    policy.setdefault("passwordMinLength", 6)
    policy.setdefault("sessionIdleMinutes", 30)
    policy.setdefault("maxSessions", 5)
    policy.setdefault("requireEmailActivate", 1)
    policy["requireInvite"] = 1 if want_invite else 0
    schema["authPolicy"] = policy

    menus = schema.setdefault("menus", {})
    admin = list(menus.get("admin") or [])
    ensure_menu(
        admin,
        "online_sessions",
        {
            "key": "online_sessions",
            "label": labels.get("onlineSessionsMenu") or "在线用户",
            "superOnly": True,
        },
        before_key="content",
    )
    if want_invite:
        ensure_menu(
            admin,
            "invite_codes",
            {
                "key": "invite_codes",
                "label": labels.get("inviteCodesMenu") or "邀请码",
                "superOnly": True,
            },
            before_key="content",
        )
    else:
        admin = [m for m in admin if (m or {}).get("key") != "invite_codes"]
    menus["admin"] = admin
    schema["menus"] = menus
    return {**spec, "schema": schema}
