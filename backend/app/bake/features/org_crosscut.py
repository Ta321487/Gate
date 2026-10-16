"""§0 X-ORG 通识横切：用户标签/批量启停常开；字典/外观/组织/岗位菜单扫词开。

硬约束：
- 禁止 *_thicken / 具名 DOM 专线；
- 浅字典 + 浅 KV，≠ HR / RBAC 引擎 / 运维中台；
- 学生包禁止工厂腔（bake/开题/DOM/能力岛）与工厂运营 Key；
- 开题未写：不挂菜单、不灌表、出包 prune 掉对应源码（对齐邀请码口径）。
"""

from __future__ import annotations

import re
from typing import Any

from app.bake.proposal_lexicon import keyword_mentioned

ORG_CROSSCUT_COLUMNS_CORE: list[tuple[str, str]] = [
    ("admin_tags", "VARCHAR(255) NOT NULL DEFAULT ''"),
]

ORG_CROSSCUT_COLUMNS_ORG: list[tuple[str, str]] = [
    ("org_id", "BIGINT NULL"),
]

# 兼容旧测：两套列并集
ORG_CROSSCUT_COLUMNS: list[tuple[str, str]] = (
    ORG_CROSSCUT_COLUMNS_CORE + ORG_CROSSCUT_COLUMNS_ORG
)

ORG_CROSSCUT_TABLES: tuple[str, ...] = (
    "sys_dict",
    "sys_site_setting",
    "sys_org",
    "sys_post_menu",
)

_LABELS_CORE: dict[str, str] = {
    "userTagsLabel": "管理标签",
    "userTagsHint": "多个标签用逗号分隔，便于筛选",
    "userTagsFilterPlaceholder": "按标签筛选",
    "batchEnableLabel": "批量启用",
    "batchDisableLabel": "批量停用",
    "batchSelectedHint": "已选 {n} 人",
}

_LABELS_DICT: dict[str, str] = {
    "dictMenu": "数据字典",
    "dictPageLead": "维护状态、类型等下拉文案；停用后新单据不再出现该选项。",
    "dictTypeLabel": "字典类型",
    "dictCodeLabel": "编码",
    "dictLabelLabel": "显示名",
    "dictSortLabel": "排序",
    "dictEnabledLabel": "启用",
    "dictEmptyHint": "暂无字典项",
}

_LABELS_SITE: dict[str, str] = {
    "siteSettingsMenu": "系统外观",
    "siteSettingsLead": "可调整系统名称、标志与登录页背景；敏感字段脱敏仅影响管理端列表展示。",
    "siteNameLabel": "系统名称",
    "siteLogoLabel": "标志图片地址",
    "loginBgLabel": "登录页背景图地址",
    "maskPhoneLabel": "管理端列表手机号脱敏",
    "maskPhoneHint": "开启后用户管理列表中的手机号中间四位显示为 *",
    "maintenanceOnLabel": "维护提示条",
    "maintenanceTextLabel": "维护提示文案",
    "maintenanceDefaultText": "系统维护中，部分功能暂不可用",
}

_LABELS_ORG: dict[str, str] = {
    "orgMenu": "组织",
    "orgPageLead": "维护院系或部门树；用户可在资料里选择所属组织。",
    "orgNameLabel": "名称",
    "orgParentLabel": "上级",
    "orgRootLabel": "（顶级）",
    "orgEmptyHint": "暂无组织",
    "orgPickLabel": "所属组织",
    "orgPickPlaceholder": "请选择组织",
    "orgFilterPlaceholder": "按组织筛选",
}

_LABELS_ROLE_MENUS: dict[str, str] = {
    "roleMenusMenu": "岗位菜单",
    "roleMenusLead": "在岗位已有菜单上勾选增减；未保存过的岗位仍按原岗位菜单。",
    "roleMenusPostLabel": "岗位",
    "roleMenusEmptyHint": "当前没有可配置的办理岗",
}

_ORG_LABELS: dict[str, str] = {
    **_LABELS_CORE,
    **_LABELS_DICT,
    **_LABELS_SITE,
    **_LABELS_ORG,
    **_LABELS_ROLE_MENUS,
}

_DICT_TERMS = ("数据字典", "字典管理", "字典项", "字典维护")
_SITE_TERMS = (
    "系统设置",
    "系统参数",
    "系统外观",
    "系统名称",
    "Logo",
    "登录页背景",
    "维护提示",
    "系统维护中",
    "脱敏策略",
    "手机号脱敏",
)
_ORG_TERMS = (
    "组织树",
    "组织架构",
    "院系树",
    "部门树",
    "所属组织",
    "挂组织",
    "按组织过滤",
    "数据权限按组织",
)
# 忌单独「权限」「角色权限」（技术节套话假阳性）
_ROLE_MENU_TERMS = (
    "权限管理",
    "菜单权限",
    "角色菜单",
    "权限矩阵",
    "权限勾选",
    "菜单勾选",
    "动态菜单",
)

_SQL_DICT = """
-- 通识数据字典（类型 + 项）
CREATE TABLE IF NOT EXISTS sys_dict (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  dict_type VARCHAR(64) NOT NULL,
  item_code VARCHAR(64) NOT NULL,
  item_label VARCHAR(128) NOT NULL,
  sort_order INT NOT NULL DEFAULT 0,
  enabled TINYINT NOT NULL DEFAULT 1,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uk_dict_type_code (dict_type, item_code),
  KEY idx_dict_type_sort (dict_type, enabled, sort_order)
);

INSERT INTO sys_dict (dict_type, item_code, item_label, sort_order, enabled)
SELECT 'common_status', 'enabled', '启用', 10, 1 FROM DUAL
WHERE NOT EXISTS (SELECT 1 FROM sys_dict WHERE dict_type='common_status' AND item_code='enabled');
INSERT INTO sys_dict (dict_type, item_code, item_label, sort_order, enabled)
SELECT 'common_status', 'disabled', '停用', 20, 1 FROM DUAL
WHERE NOT EXISTS (SELECT 1 FROM sys_dict WHERE dict_type='common_status' AND item_code='disabled');
"""

_SQL_SITE = """
-- 站点浅设置；≠ 工厂 AppPolicy 摊页
CREATE TABLE IF NOT EXISTS sys_site_setting (
  setting_key VARCHAR(64) NOT NULL,
  setting_value VARCHAR(1024) NOT NULL DEFAULT '',
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (setting_key)
);
"""

_SQL_ORG = """
-- 浅组织树（≠ 人事中台）
CREATE TABLE IF NOT EXISTS sys_org (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  parent_id BIGINT NULL,
  name VARCHAR(64) NOT NULL,
  sort_order INT NOT NULL DEFAULT 0,
  enabled TINYINT NOT NULL DEFAULT 1,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  KEY idx_org_parent (parent_id, sort_order)
);

INSERT INTO sys_org (parent_id, name, sort_order, enabled)
SELECT NULL, '本部', 0, 1 FROM DUAL
WHERE NOT EXISTS (SELECT 1 FROM sys_org WHERE name='本部' AND parent_id IS NULL);
"""

_SQL_ROLE_MENUS = """
-- 岗位菜单勾选；某岗位尚无行时仍用原岗位菜单包
CREATE TABLE IF NOT EXISTS sys_post_menu (
  staff_post VARCHAR(64) NOT NULL,
  menu_key VARCHAR(64) NOT NULL,
  PRIMARY KEY (staff_post, menu_key)
);
"""


def _blob(text: str, title: str = "") -> str:
    return f"{title or ''}\n{text or ''}"


def _hit(blob: str, terms: tuple[str, ...]) -> bool:
    return any(keyword_mentioned(blob, kw, ignore_contrast=True) for kw in terms)


def scan_org_dict(text: str, title: str = "") -> bool:
    return _hit(_blob(text, title), _DICT_TERMS)


def scan_org_site_settings(text: str, title: str = "") -> bool:
    return _hit(_blob(text, title), _SITE_TERMS)


def scan_org_tree(text: str, title: str = "") -> bool:
    return _hit(_blob(text, title), _ORG_TERMS)


def scan_org_role_menus(text: str, title: str = "") -> bool:
    return _hit(_blob(text, title), _ROLE_MENU_TERMS)


def resolve_org_crosscut_flags(text: str, title: str = "") -> dict[str, bool]:
    return {
        "dict": scan_org_dict(text, title),
        "siteSettings": scan_org_site_settings(text, title),
        "org": scan_org_tree(text, title),
        "roleMenus": scan_org_role_menus(text, title),
    }


def ensure_org_crosscut_sql(
    sql: str,
    *,
    flags: dict[str, bool] | None = None,
) -> str:
    """常开注入 admin_tags；字典/站点/组织/岗位菜单表仅扫词命中时灌。"""
    from app.bake.sql.ddl_edit import (
        CREATE_TABLE_RE,
        inject_missing_columns,
        strip_trailing_comma_before_close,
    )

    f = flags or {}
    want_org = bool(f.get("org"))
    cols = list(ORG_CROSSCUT_COLUMNS_CORE)
    if want_org:
        cols.extend(ORG_CROSSCUT_COLUMNS_ORG)

    def repl(m: re.Match[str]) -> str:
        head, table, body, tail = m.group(1), m.group(2), m.group(3), m.group(4)
        if table.lower() != "sys_user":
            return m.group(0)
        body = inject_missing_columns(body, cols)
        body = strip_trailing_comma_before_close(body)
        return f"{head}{body}{tail}"

    out = CREATE_TABLE_RE.sub(repl, sql or "")

    def drop_table(name: str, blob: str) -> str:
        blob = CREATE_TABLE_RE.sub(
            lambda m: "" if m.group(2).lower() == name else m.group(0),
            blob,
        )
        blob = re.sub(
            rf"(?is)INSERT\s+INTO\s+`?{name}`?\b.*?;\s*",
            "",
            blob,
        )
        return blob

    for name, want, fragment in (
        ("sys_dict", bool(f.get("dict")), _SQL_DICT),
        ("sys_site_setting", bool(f.get("siteSettings")), _SQL_SITE),
        ("sys_org", want_org, _SQL_ORG),
        ("sys_post_menu", bool(f.get("roleMenus")), _SQL_ROLE_MENUS),
    ):
        if want:
            if f"CREATE TABLE IF NOT EXISTS {name}" not in out:
                out = out.rstrip() + "\n" + fragment
        else:
            out = drop_table(name, out)
    return out


def apply_org_crosscut_to_spec(spec: dict[str, Any], proposal_text: str = "") -> dict[str, Any]:
    """用户标签/批量启停 labels 常开；四块管理菜单仅开题命中才挂。"""
    from app.bake.schema.menu_utils import ensure_menu

    title = str(spec.get("title") or "")
    flags = resolve_org_crosscut_flags(proposal_text or "", title)

    schema = dict(spec.get("schema") or {})
    labels = dict(schema.get("labels") or {})
    for key, val in _LABELS_CORE.items():
        labels.setdefault(key, val)

    def apply_block(want: bool, block: dict[str, str]) -> None:
        if want:
            for key, val in block.items():
                labels.setdefault(key, val)
        else:
            for key in block:
                labels.pop(key, None)

    apply_block(flags["dict"], _LABELS_DICT)
    apply_block(flags["siteSettings"], _LABELS_SITE)
    apply_block(flags["org"], _LABELS_ORG)
    apply_block(flags["roleMenus"], _LABELS_ROLE_MENUS)
    schema["labels"] = labels
    schema["orgCrosscut"] = dict(flags)

    menus = schema.setdefault("menus", {})
    admin = list(menus.setdefault("admin", []))

    def upsert(key: str, want: bool, label: str) -> None:
        nonlocal admin
        if want:
            ensure_menu(
                admin,
                key,
                {"key": key, "label": label, "superOnly": True},
                before_key="users",
            )
        else:
            admin = [m for m in admin if not (isinstance(m, dict) and m.get("key") == key)]

    upsert("dict", flags["dict"], labels.get("dictMenu") or "数据字典")
    upsert(
        "site_settings",
        flags["siteSettings"],
        labels.get("siteSettingsMenu") or "系统外观",
    )
    upsert("org", flags["org"], labels.get("orgMenu") or "组织")
    upsert(
        "role_menus",
        flags["roleMenus"],
        labels.get("roleMenusMenu") or "岗位菜单",
    )
    menus["admin"] = admin
    return {**spec, "schema": schema}
