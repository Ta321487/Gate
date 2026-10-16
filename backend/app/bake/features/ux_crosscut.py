"""§0 X-UX：使用说明、文件库、省市区、二次确认、一级佣金。开题写到才挂。

硬约束：禁止 *_thicken；学生包禁止工厂腔。
打印、灯箱、Toast 属于只读或前端提示，不在本波标已齐。
附件 10MB 上限是上传接口原有限制，本波只把超限说清楚。
一级佣金只记邀请人一笔，不做多级。
"""

from __future__ import annotations

from typing import Any

from app.bake.proposal_lexicon import keyword_mentioned

_HELP_TERMS = (
    "系统帮助",
    "操作手册",
    "使用帮助",
    "使用说明",
)
_FILE_TERMS = (
    "文件管理",
    "素材库",
    "附件管理",
)
_REGION_TERMS = (
    "省市区",
    "三级联动",
)
_CONFIRM_TERMS = (
    "二次确认",
    "再次确认",
    "敏感操作",
)
_COMMISSION_TERMS = (
    "分销",
    "一级佣金",
    "推广佣金",
)

_HELP_SQL = """
-- 使用说明（单页，管理员可改）
CREATE TABLE IF NOT EXISTS sys_help_doc (
  id TINYINT PRIMARY KEY,
  title VARCHAR(64) NOT NULL,
  body VARCHAR(4000) NOT NULL,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
INSERT INTO sys_help_doc (id, title, body)
SELECT 1, '使用说明', '这里说明本系统的常用操作。管理员可在后台修改本文。' FROM DUAL
WHERE NOT EXISTS (SELECT 1 FROM sys_help_doc WHERE id=1);
"""

_COMMISSION_SQL = """
-- 一级佣金台账（支付成功后按邀请人记一笔）
CREATE TABLE IF NOT EXISTS sys_commission (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  order_id BIGINT NOT NULL,
  buyer VARCHAR(64) NOT NULL,
  inviter VARCHAR(64) NOT NULL,
  amount_yuan DECIMAL(10,2) NOT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uk_commission_order (order_id, inviter)
);
"""

_LABELS = {
    "helpMenu": "使用说明",
    "helpAdminMenu": "使用说明",
    "helpLead": "阅读本系统的操作说明。",
    "helpTitleLabel": "标题",
    "helpBodyLabel": "正文",
    "filesMenu": "文件",
    "commissionMenu": "佣金台账",
    "inviterLabel": "邀请人账号",
}

_HELP_KEYS = ("helpMenu", "helpAdminMenu", "helpLead", "helpTitleLabel", "helpBodyLabel")
_FILE_KEYS = ("filesMenu",)
_COMMISSION_KEYS = ("commissionMenu", "inviterLabel")


def _any(text: str, title: str, terms: tuple[str, ...]) -> bool:
    blob = f"{title or ''}\n{text or ''}"
    return any(keyword_mentioned(blob, kw, ignore_contrast=True) for kw in terms)


def resolve_ux_crosscut_flags(text: str, title: str = "") -> dict[str, bool]:
    return {
        "help": _any(text, title, _HELP_TERMS),
        "files": _any(text, title, _FILE_TERMS),
        "region": _any(text, title, _REGION_TERMS),
        "confirm": _any(text, title, _CONFIRM_TERMS),
        "commission": _any(text, title, _COMMISSION_TERMS),
    }


def ensure_ux_help_sql(sql: str, *, enabled: bool) -> str:
    out = sql or ""
    if not enabled:
        return out
    if "CREATE TABLE IF NOT EXISTS sys_help_doc" not in out:
        out = out.rstrip() + "\n" + _HELP_SQL
    return out


def ensure_ux_commission_sql(sql: str, *, enabled: bool) -> str:
    out = sql or ""
    if not enabled:
        return out
    if "CREATE TABLE IF NOT EXISTS sys_commission" not in out:
        out = out.rstrip() + "\n" + _COMMISSION_SQL
    return out


def apply_ux_crosscut_to_spec(spec: dict[str, Any], proposal_text: str = "") -> dict[str, Any]:
    from app.bake.schema.menu_utils import ensure_menu

    title = str(spec.get("title") or "")
    flags = resolve_ux_crosscut_flags(proposal_text or "", title)
    schema = dict(spec.get("schema") or {})
    labels = dict(schema.get("labels") or {})
    menus = schema.setdefault("menus", {})
    user = list(menus.setdefault("user", []))
    admin = list(menus.setdefault("admin", []))

    if flags["help"]:
        for key in _HELP_KEYS:
            labels.setdefault(key, _LABELS[key])
        ensure_menu(user, "help", {"key": "help", "label": labels["helpMenu"]})
        ensure_menu(
            admin,
            "help_admin",
            {"key": "help_admin", "label": labels["helpAdminMenu"], "superOnly": True},
        )
    else:
        for key in _HELP_KEYS:
            labels.pop(key, None)
        user = _kept(user, {"help", "help_admin"})
        admin = _kept(admin, {"help", "help_admin"})

    if flags["files"]:
        for key in _FILE_KEYS:
            labels.setdefault(key, _LABELS[key])
        ensure_menu(
            admin,
            "files",
            {"key": "files", "label": labels["filesMenu"], "superOnly": True},
        )
    else:
        for key in _FILE_KEYS:
            labels.pop(key, None)
        admin = _kept(admin, {"files"})

    if flags["commission"]:
        for key in _COMMISSION_KEYS:
            labels.setdefault(key, _LABELS[key])
        ensure_menu(
            admin,
            "commissions",
            {"key": "commissions", "label": labels["commissionMenu"], "superOnly": True},
        )
    else:
        for key in _COMMISSION_KEYS:
            labels.pop(key, None)
        admin = _kept(admin, {"commissions"})

    menus["user"] = user
    menus["admin"] = admin
    schema["labels"] = labels
    schema["uxCrosscut"] = dict(flags)
    schema["menus"] = menus
    return {**spec, "schema": schema}


def _kept(rows: list, keys: set[str]) -> list:
    return [m for m in rows if not (isinstance(m, dict) and m.get("key") in keys)]
