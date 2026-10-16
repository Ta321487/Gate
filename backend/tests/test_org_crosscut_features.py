"""§0 X-ORG：用户标签常开；字典/外观/组织/岗位菜单扫词开。"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

from app.bake.domain_schema import attach_accept
from app.bake.domains import DOMAIN_CAPABILITIES
from app.bake.engine_sql import domain_sql
from app.bake.features.org_crosscut import (
    ORG_CROSSCUT_COLUMNS_CORE,
    apply_org_crosscut_to_spec,
    resolve_org_crosscut_flags,
    scan_org_dict,
    scan_org_role_menus,
    scan_org_site_settings,
    scan_org_tree,
)
from app.bake.features.proposal_caps import HUB_BYPASS_MODULES

REPO = Path(__file__).resolve().parents[2]

_CORE_LABEL_KEYS = (
    "userTagsLabel",
    "batchEnableLabel",
)


def _spec(domain: str = "DOM-LIBRARY", title: str = "图书借阅管理系统", body: str = "") -> dict:
    return attach_accept(
        {
            "domain": domain,
            "title": title,
            "capabilities": list(DOMAIN_CAPABILITIES[domain]),
            "features": [],
            "archetype": "ARCH-FLOW",
        },
        body,
    )


class OrgCrosscutFeatureTests(unittest.TestCase):
    def test_hub_bypass_lists_org_crosscut(self) -> None:
        self.assertIn("org_crosscut", HUB_BYPASS_MODULES)

    def test_empty_opening_skips_optional_modules(self) -> None:
        flags = resolve_org_crosscut_flags("实现图书借阅与归还流程。", "图书借阅管理系统")
        self.assertFalse(flags["dict"])
        self.assertFalse(flags["siteSettings"])
        self.assertFalse(flags["org"])
        self.assertFalse(flags["roleMenus"])

    def test_boilerplate_role_perm_does_not_open_role_menus(self) -> None:
        text = "Spring Security 实现登录鉴权与角色权限；持久层使用 MyBatis。"
        self.assertFalse(scan_org_role_menus(text, "图书借阅管理系统"))

    def test_scan_terms_open_flags(self) -> None:
        self.assertTrue(scan_org_dict("维护数据字典与状态文案。", ""))
        self.assertTrue(scan_org_site_settings("提供系统设置与 Logo 配置。", ""))
        self.assertTrue(scan_org_site_settings("登录页可更换 Logo。", ""))
        self.assertTrue(scan_org_tree("支持组织树与资料挂组织。", ""))
        self.assertTrue(scan_org_role_menus("实现权限管理与菜单权限勾选。", ""))

    def test_sql_without_opening_has_tags_only(self) -> None:
        sql = domain_sql("DOM-LIBRARY", "thesis_org_x", title="图书借阅管理系统")
        m = re.search(
            r"CREATE TABLE IF NOT EXISTS\s+`?sys_user`?\s*\((.*?)\)\s*;",
            sql,
            flags=re.IGNORECASE | re.DOTALL,
        )
        self.assertIsNotNone(m)
        body = m.group(1).lower()
        for col, _ in ORG_CROSSCUT_COLUMNS_CORE:
            self.assertIn(col.lower(), body)
        self.assertNotIn("org_id", body)
        low = sql.lower()
        self.assertNotIn("create table if not exists sys_dict", low)
        self.assertNotIn("create table if not exists sys_org", low)
        self.assertNotIn("create table if not exists sys_site_setting", low)
        self.assertNotIn("create table if not exists sys_post_menu", low)

    def test_sql_with_org_terms_injects_org(self) -> None:
        sql = domain_sql(
            "DOM-LIBRARY",
            "thesis_org_y",
            title="图书借阅管理系统",
            proposal_text="维护组织树，资料挂所属组织，并按组织过滤用户列表。",
        )
        low = sql.lower()
        self.assertIn("create table if not exists sys_org", low)
        self.assertIn("org_id", low)

    def test_apply_spec_empty_opening_no_optional_menus(self) -> None:
        out = apply_org_crosscut_to_spec(_spec(), "")
        labels = (out.get("schema") or {}).get("labels") or {}
        for key in _CORE_LABEL_KEYS:
            self.assertTrue(str(labels.get(key) or "").strip(), key)
        self.assertNotIn("dictMenu", labels)
        admin = ((out.get("schema") or {}).get("menus") or {}).get("admin") or []
        keys = {m.get("key") for m in admin if isinstance(m, dict)}
        self.assertNotIn("dict", keys)
        self.assertNotIn("site_settings", keys)
        self.assertNotIn("org", keys)
        self.assertNotIn("role_menus", keys)
        oc = (out.get("schema") or {}).get("orgCrosscut") or {}
        self.assertFalse(oc.get("dict"))

    def test_apply_spec_with_terms_hangs_menus(self) -> None:
        body = "数据字典、系统设置与 Logo、组织树、权限管理与菜单权限。"
        out = apply_org_crosscut_to_spec(_spec(body=body), body)
        admin = ((out.get("schema") or {}).get("menus") or {}).get("admin") or []
        keys = {m.get("key") for m in admin if isinstance(m, dict)}
        self.assertIn("dict", keys)
        self.assertIn("site_settings", keys)
        self.assertIn("org", keys)
        self.assertIn("role_menus", keys)

    def test_attach_accept_empty_opening_core_only(self) -> None:
        labels = ((_spec().get("schema") or {}).get("labels") or {})
        for key in _CORE_LABEL_KEYS:
            self.assertTrue(str(labels.get(key) or "").strip(), key)
        self.assertFalse(str(labels.get("dictMenu") or "").strip())

    def test_skeleton_files_exist(self) -> None:
        base = REPO / "skeletons/baseline/backend/src/main/java/com/thesis"
        for rel in (
            "service/DictStore.java",
            "service/SiteSettingStore.java",
            "service/OrgStore.java",
            "service/RoleMenuStore.java",
            "controller/DictController.java",
            "controller/SiteSettingController.java",
            "controller/OrgController.java",
            "controller/RoleMenuController.java",
        ):
            self.assertTrue((base / rel).is_file(), rel)

    def test_menu_routes_registry(self) -> None:
        from app.bake.menu_routes import ADMIN_MENU_PATHS, _BASE_ALWAYS, effective_paths

        self.assertEqual(ADMIN_MENU_PATHS.get("dict"), "/admin/dict")
        self.assertEqual(ADMIN_MENU_PATHS.get("org"), "/admin/org")
        self.assertNotIn("/admin/dict", _BASE_ALWAYS)
        self.assertNotIn("/admin/org", _BASE_ALWAYS)
        empty = effective_paths(["archive", "ticket_flow"], schema={"orgCrosscut": {}})
        self.assertNotIn("/admin/dict", empty)
        self.assertNotIn("/admin/role-menus", empty)
        hit = effective_paths(
            ["archive", "ticket_flow"],
            schema={"orgCrosscut": {"dict": True, "roleMenus": True, "org": True, "siteSettings": True}},
        )
        self.assertIn("/admin/dict", hit)
        self.assertIn("/admin/site-settings", hit)
        self.assertIn("/admin/org", hit)
        self.assertIn("/admin/role-menus", hit)

    def test_role_menu_scrub_keeps_login_payload(self) -> None:
        from app.bake.pack_prune import _strip_type_usages

        src = "m.putAll(com.thesis.service.RoleMenuStore.loginMenuPayload(profile.staffPost));"
        out = _strip_type_usages(src, "RoleMenuStore")
        self.assertNotIn("RoleMenuStore", out)
        self.assertIn("menuUsePacks", out)
        self.assertNotIn("putAll(null)", out.replace(" ", ""))

    def test_no_factory_cavity_in_student_labels(self) -> None:
        body = "数据字典与系统设置。"
        out = apply_org_crosscut_to_spec(_spec(body=body), body)
        labels = (out.get("schema") or {}).get("labels") or {}
        blob = " ".join(str(v) for v in labels.values()).lower()
        for bad in ("bake", "dom-", "开题", "能力岛", "工厂", "thicken"):
            self.assertNotIn(bad, blob, bad)


if __name__ == "__main__":
    unittest.main()
