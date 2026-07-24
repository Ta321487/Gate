"""领域目录 — GENERIC。"""

from __future__ import annotations

DOMAINS: dict = {
    "DOM-GENERIC": {
        "label": "通用",
        "keywords": [],
        "match_hint": "适用：无明确行业场景的纯档案 CRUD 兜底。有更贴切领域时勿选本域。",
        "entities": ["Item", "Category", "Notice"],
        "roles": ["user", "admin", "subadmin"],
        "flows": ["新增 → 编辑 → 查询"],
        "features": [
            {"name": "登录", "status": "baseline"},
            {"name": "个人资料与头像", "status": "baseline"},
            {"name": "基础 CRUD", "status": "domain"},
        ],
        "out_of_mvp": [],
        "themes": [
            {"id": "gen-ink", "label": "通用墨蓝"},
            {"id": "gen-grove", "label": "通用青绿"},
            {"id": "gen-clay", "label": "通用暖陶"},
            {"id": "gen-night", "label": "通用深色"},
        ],
    }
}
