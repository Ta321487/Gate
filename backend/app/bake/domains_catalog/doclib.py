"""领域目录 — 简易知识库 / 文库下载台账（C-12）。"""

from __future__ import annotations

from app.bake.gate_contracts import gate_archive_only

DOMAINS: dict = {
    "DOM-DOCLIB": {
        "label": "文库资料",
        "keywords": [
            "知识库",
            "文库",
            "资料库",
            "文档库",
            "下载台账",
            "资料下载",
            "附件下载",
            "共享文档",
            "课件下载",
            "制度文件库",
            "文件库",
            "资料共享",
        ],
        "match_hint": (
            "适用：资料条目、附件权限、下载记录台账。"
            "勿与图书借阅归还、院刊/资讯博文收藏混淆。"
        ),
        "entities": ["Archive", "Category", "Doclib", "Notice"],
        "roles": ["user", "admin", "subadmin"],
        "flows": ["浏览资料 → 按权限下载 → 台账记录"],
        "features": [
            {"name": "登录", "status": "baseline"},
            {"name": "个人资料与头像", "status": "baseline"},
            {"name": "管理端工作台", "status": "module"},
            {"name": "资料条目", "status": "domain"},
            {"name": "分类管理", "status": "module"},
            {"name": "用户管理", "status": "module"},
            {"name": "资料下载与台账", "status": "flow"},
            {"name": "公告管理", "status": "module"},
            {"name": "对象存储签名URL/全文检索", "status": "out_of_mvp"},
        ],
        "out_of_mvp": ["对象存储签名URL", "全文检索引擎", "版本diff"],
        "themes": [
            {"id": "doclib-ink", "label": "文库墨蓝"},
            {"id": "doclib-sand", "label": "资料暖沙"},
            {"id": "doclib-slate", "label": "制度灰青"},
            {"id": "doclib-night", "label": "夜读深色"},
        ],
        "gate": gate_archive_only(
            archive_feature="资料条目",
            users_feature="用户管理",
            category_feature="分类管理",
        ),
        "portal_banners": True,
        "runtime": {
            "enable_ticket": False,
            "register_role": "user",
            "archive_category_table": "category",
            "archive_item_table": "doc_item",
        },
    },
}
