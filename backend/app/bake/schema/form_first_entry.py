"""填单优先入口（与 ATTEND / CHECKIN 同开关）。

档案页仅作说明/查阅；学生主路径在「我的*」选类型或对象填单。
禁止另写一套菜单排序或 Store 分支。
"""

from __future__ import annotations

from typing import Any


def apply_form_first_entry(
    preset: dict[str, Any],
    *,
    page_lead: str | None = None,
    empty: str | None = None,
) -> dict[str, Any]:
    """原地打开 apply_from_list + user_tickets_first，并把「*目录/*检索」收成说明/查阅。"""
    preset["apply_from_list"] = True
    preset["user_tickets_first"] = True
    menu = str(preset.get("archive_menu_user") or "")
    if menu.endswith("目录"):
        preset["archive_menu_user"] = f"{menu[:-2]}说明"
    elif menu.endswith("检索"):
        preset["archive_menu_user"] = f"{menu[:-2]}查阅"
    for b in preset.get("banners") or []:
        if not isinstance(b, dict):
            continue
        title = str(b.get("title") or "")
        lead = str(b.get("lead") or "")
        if title.endswith("目录"):
            b["title"] = f"{title[:-2]}说明"
            if lead.startswith("浏览"):
                b["lead"] = f"查阅{lead[2:]}"
        elif title.endswith("检索"):
            b["title"] = f"{title[:-2]}查阅"
    points = preset.get("auth_points")
    if isinstance(points, list):
        preset["auth_points"] = [
            (x.replace("目录", "说明") if isinstance(x, str) else x) for x in points
        ]
    lead = str(preset.get("auth_lead") or "")
    my = str(preset.get("my_tickets_label") or "我的申请").strip() or "我的申请"
    if lead and f"「{my}」" not in lead:
        for needle in ("登录；选择", "登录；浏览"):
            if needle in lead:
                preset["auth_lead"] = lead.replace(
                    needle, f"登录；在「{my}」选择", 1
                )
                break
    if page_lead:
        preset["my_tickets_page_lead"] = page_lead
    elif not str(preset.get("my_tickets_page_lead") or "").strip():
        preset["my_tickets_page_lead"] = (
            f"在「{my}」选择事项提交并跟踪进度；说明页仅作查阅。"
        )
    if empty:
        preset["my_tickets_empty"] = empty
    return preset
