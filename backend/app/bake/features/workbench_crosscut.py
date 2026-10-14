"""§0 X-DASH 通识横切：工作台角标/快捷入口 + XD-02 PV/我的单据/定时任务只读台。

硬约束：
- 禁止 *_thicken / 具名 DOM 专线；
- PV 只计次，≠ UV/中台；定时任务台只读说明，≠ XXL-JOB；
- 快捷入口 / 我的单据浅链 schema 菜单，≠ 低代码。
"""

from __future__ import annotations

from typing import Any

_DASH_LABELS: dict[str, str] = {
    "dashShortcutsTitle": "常用入口",
    "dashTodoTitle": "待办",
    "dashScopedHint": "当前账号仅统计本人相关处理中单据",
    "dashPvTitle": "今日访问",
    "dashPvTotalLabel": "累计访问",
    "myDocsTitle": "我的单据",
    "myDocsEmptyHint": "暂无关联业务入口",
    "scheduleJobsMenu": "定时任务",
    "scheduleJobsHint": "以下为本系统已启用的定时任务；本页只读说明，不能改调度。",
}

_DEFAULT_SHORTCUT_KEYS: tuple[str, ...] = (
    "ticket_pending",
    "orders",
    "reservations",
    "content",
    "users",
    "archive",
)

_MY_DOC_KEYS: tuple[str, ...] = (
    "my_tickets",
    "my_orders",
    "my_reservations",
    "peer_tickets",
    "exam_attempts",
    "survey_mine",
    "vote_mine",
    "messages",
)

_SITE_STAT_SQL = """
-- X-DASH XD-02: 简易站点 PV（按日）
CREATE TABLE IF NOT EXISTS sys_site_stat (
  day_key VARCHAR(10) NOT NULL,
  pv INT NOT NULL DEFAULT 0,
  PRIMARY KEY (day_key)
);
"""


def ensure_workbench_crosscut_sql(sql: str) -> str:
    """追加 sys_site_stat（幂等）。"""
    out = sql or ""
    if "CREATE TABLE IF NOT EXISTS sys_site_stat" not in out:
        out = out.rstrip() + "\n" + _SITE_STAT_SQL
    return out


def apply_workbench_crosscut_to_spec(spec: dict[str, Any], proposal_text: str = "") -> dict[str, Any]:
    """基线常开：工作台 labels / 快捷入口 / 我的单据链 / 定时任务菜单。"""
    del proposal_text
    from app.bake.schema.menu_utils import ensure_menu

    schema = dict(spec.get("schema") or {})
    labels = dict(schema.get("labels") or {})
    for key, val in _DASH_LABELS.items():
        labels.setdefault(key, val)
    schema["labels"] = labels

    menus = schema.setdefault("menus", {})
    admin = menus.setdefault("admin", [])
    user = menus.get("user") or []
    by_admin = {str(m.get("key") or ""): m for m in admin if isinstance(m, dict)}
    by_user = {str(m.get("key") or ""): m for m in user if isinstance(m, dict)}

    shortcuts: list[dict[str, str]] = []
    for key in _DEFAULT_SHORTCUT_KEYS:
        m = by_admin.get(key)
        if not m:
            continue
        shortcuts.append({"key": key, "label": str(m.get("label") or key)})
        if len(shortcuts) >= 6:
            break

    my_docs: list[dict[str, str]] = []
    for key in _MY_DOC_KEYS:
        m = by_user.get(key)
        if not m:
            continue
        my_docs.append({"key": key, "label": str(m.get("label") or key)})

    wb = dict(schema.get("workbench") or {})
    if "shortcuts" not in wb:
        wb["shortcuts"] = shortcuts
    if "myDocs" not in wb:
        wb["myDocs"] = my_docs
    schema["workbench"] = wb

    ensure_menu(
        admin,
        "schedule_jobs",
        {
            "key": "schedule_jobs",
            "label": labels.get("scheduleJobsMenu") or "定时任务",
            "superOnly": True,
        },
        before_key="users",
    )
    return {**spec, "schema": schema}
