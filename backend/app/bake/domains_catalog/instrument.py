"""领域目录 — 大型仪器机时（P-19 · C-07：archive + ticket + slot）。"""

from __future__ import annotations

from typing import Any

from app.bake.gate_contracts import gate_archive_ticket, gate_slot_shell


def _merge_gate(parts: list[dict[str, Any]]) -> dict[str, Any]:
    routes: list[dict] = []
    seen_seg: set[str] = set()
    files: list[str] = []
    seen_f: set[str] = set()
    flow_api: dict[str, Any] = {}
    inv: dict[str, Any] = {
        "require_super_auth": True,
        "master_kind": "archive",
        "master_menus": ["archive", "category"],
        "super_menus": ["users", "content", "archive", "category"],
    }
    for g in parts:
        for r in g.get("routes") or []:
            seg = r.get("seg")
            if seg and seg not in seen_seg:
                seen_seg.add(seg)
                routes.append(r)
        for f in g.get("files") or []:
            if f not in seen_f:
                seen_f.add(f)
                files.append(f)
        flow_api.update(g.get("flow_api") or {})
        ai = g.get("admin_invariants") or {}
        for k in ("master_menus", "super_menus"):
            if ai.get(k):
                inv[k] = list(dict.fromkeys(list(inv.get(k) or []) + list(ai[k])))
    return {
        "routes": routes,
        "files": files,
        "flow_api": flow_api,
        "admin_invariants": inv,
    }


DOMAINS: dict = {
    "DOM-INSTRUMENT": {
        "label": "仪器机时",
        "keywords": [
            "大型仪器",
            "仪器机时",
            "机时预约",
            "机时时段",
            "大型仪器预约",
            "仪器借用与机时",
            "共享仪器",
            "仪器共享平台",
            "机时管理",
            "大型仪器借用",
            "仪器上机预约",
            "分析测试中心预约",
        ],
        "match_hint": (
            "适用：大型仪器/共享仪器「借用申请 + 机时时段预约」一体（单域 FR）。"
            "勿与纯设备借用（无预约）、会议室/场地预约或耗材领用混淆。"
        ),
        "entities": ["Archive", "Category", "Ticket", "Reservation", "Notice"],
        "roles": ["user", "admin", "subadmin"],
        "flows": ["选仪器 → 约机时 →（可选）提交借用 → 审/履约"],
        "features": [
            {"name": "登录", "status": "baseline"},
            {"name": "个人资料与头像", "status": "baseline"},
            {"name": "管理端工作台", "status": "module"},
            {"name": "仪器档案", "status": "domain"},
            {"name": "分类管理", "status": "module"},
            {"name": "用户管理", "status": "module"},
            {"name": "机时时段预约", "status": "flow"},
            {"name": "借用申请审核", "status": "flow"},
            {"name": "借用记录", "status": "module"},
            {"name": "归还 / 逾期", "status": "module"},
            {"name": "预约记录", "status": "module"},
            {"name": "公告管理", "status": "module"},
            {"name": "真物联网联机计费", "status": "out_of_mvp"},
        ],
        "out_of_mvp": ["真物联网联机计费", "仪器远程控制"],
        "themes": [
            {"id": "instrument-teal", "label": "仪器青绿"},
            {"id": "instrument-sand", "label": "仪器暖沙"},
            {"id": "instrument-slate", "label": "仪器灰青"},
            {"id": "instrument-night", "label": "仪器深色"},
        ],
        "gate": _merge_gate(
            [
                gate_archive_ticket(
                    archive_feature="仪器档案",
                    flow_feature="借用申请审核",
                    records_feature="借用记录",
                    users_feature="用户管理",
                    category_feature="分类管理",
                    overdue_feature="归还 / 逾期",
                    with_deadline=True,
                ),
                gate_slot_shell(
                    archive_feature="仪器档案",
                    reserve_feature="机时时段预约",
                ),
            ]
        ),
        "portal_banners": True,
        "runtime": {
            "ticket_mode": "archive",
            "ticket_table": "instrument_loan",
            "register_role": "user",
            "archive_category_table": "category",
            "archive_item_table": "instrument",
            "slot_table": "resource_slot",
            "reservation_table": "reservation",
            "use_quota": True,
            "use_deadline": True,
        },
    },
}
