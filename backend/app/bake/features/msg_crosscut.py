"""§0 X-MSG 通识横切：站内信软删/类型筛选 + XM-02 公告过期/强制弹窗/浅富文本/广告位。

硬约束：
- 禁止 *_thicken / 具名 DOM 专线；
- 富文本仅浅 HTML（textarea + 详情 v-html），≠专业编辑器；
- Banner 多槽浅表；图片 URL 手填/本地路径，≠ CDN/OSS。
"""

from __future__ import annotations

import re
from typing import Any

MSG_CROSSCUT_COLUMNS: list[tuple[str, str]] = [
    ("deleted_at", "DATETIME NULL"),
]

NOTICE_CROSSCUT_COLUMNS: list[tuple[str, str]] = [
    ("expire_at", "DATETIME NULL"),
    ("force_ack", "TINYINT NOT NULL DEFAULT 0"),
    ("content_fmt", "VARCHAR(16) NOT NULL DEFAULT 'text'"),
]

_MSG_LABELS: dict[str, str] = {
    "messageKindAll": "全部",
    "messageKindSystem": "系统",
    "messageKindBiz": "业务",
    "messageDeleteLabel": "删除",
    "messageDeletedHint": "已删除",
    "noticeExpireLabel": "过期时间",
    "noticeForceAckLabel": "强制阅读弹窗",
    "noticeForceAckHint": "登录后须确认阅读才能关闭",
    "noticeForceAckConfirm": "我已阅读",
    "noticeRichHtmlHint": "可选基础 HTML（加粗/换行/链接）；勿贴脚本",
    "noticeContentFmtLabel": "正文格式",
    "bannersMenu": "广告位",
    "bannerSlotLabel": "槽位",
    "bannerEmptyHint": "暂无广告位",
}

_XM02_TABLES_SQL = """
-- X-MSG XM-02: 强制公告确认 / 广告位多槽
CREATE TABLE IF NOT EXISTS sys_notice_ack (
  notice_id BIGINT NOT NULL,
  username VARCHAR(64) NOT NULL,
  acked_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (notice_id, username),
  KEY idx_notice_ack_user (username)
);

CREATE TABLE IF NOT EXISTS sys_banner (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  slot VARCHAR(32) NOT NULL DEFAULT 'home',
  title VARCHAR(128) NOT NULL DEFAULT '',
  lead_text VARCHAR(255) NOT NULL DEFAULT '',
  image_url VARCHAR(512) NOT NULL DEFAULT '',
  link_url VARCHAR(512) NOT NULL DEFAULT '',
  sort_order INT NOT NULL DEFAULT 0,
  enabled TINYINT NOT NULL DEFAULT 1,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  KEY idx_banner_slot (slot, enabled, sort_order)
);

INSERT INTO sys_banner (slot, title, lead_text, image_url, link_url, sort_order, enabled)
SELECT 'home', '欢迎使用', '系统已就绪，可开始浏览业务入口。', '', '/notices', 0, 1 FROM DUAL
WHERE NOT EXISTS (SELECT 1 FROM sys_banner WHERE slot='home' AND title='欢迎使用');
"""


def ensure_msg_crosscut_sql(sql: str) -> str:
    """注入 sys_message.deleted_at、sys_notice XM-02 列，并补 ack/banner 表。"""
    from app.bake.sql.ddl_edit import (
        CREATE_TABLE_RE,
        inject_missing_columns,
        strip_trailing_comma_before_close,
    )

    def repl(m: re.Match[str]) -> str:
        head, table, body, tail = m.group(1), m.group(2), m.group(3), m.group(4)
        t = table.lower()
        if t == "sys_message":
            body = inject_missing_columns(body, MSG_CROSSCUT_COLUMNS)
        elif t == "sys_notice":
            body = inject_missing_columns(body, NOTICE_CROSSCUT_COLUMNS)
        else:
            return m.group(0)
        body = strip_trailing_comma_before_close(body)
        return f"{head}{body}{tail}"

    out = CREATE_TABLE_RE.sub(repl, sql or "")
    if "CREATE TABLE IF NOT EXISTS sys_notice_ack" not in out:
        out = out.rstrip() + "\n" + _XM02_TABLES_SQL
    return out


def apply_msg_crosscut_to_spec(spec: dict[str, Any], proposal_text: str = "") -> dict[str, Any]:
    """基线常开：站内信/公告/广告位文案与管理端菜单。"""
    del proposal_text
    from app.bake.schema.menu_utils import ensure_menu

    schema = dict(spec.get("schema") or {})
    labels = dict(schema.get("labels") or {})
    for key, val in _MSG_LABELS.items():
        labels.setdefault(key, val)
    schema["labels"] = labels
    menus = schema.setdefault("menus", {})
    admin = menus.setdefault("admin", [])
    ensure_menu(
        admin,
        "banners",
        {
            "key": "banners",
            "label": labels.get("bannersMenu") or "广告位",
            "superOnly": True,
        },
        before_key="content",
    )
    return {**spec, "schema": schema}
