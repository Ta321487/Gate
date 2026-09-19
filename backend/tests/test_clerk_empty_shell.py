"""跨域：子管不得空转；工作台不得裸跳总管页。"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

from app.bake.domain_schema import attach_accept
from app.bake.domains import DOMAIN_CAPABILITIES, DOMAINS
from app.bake.staff_posts import PACK_ADMIN_MENUS, _clerk_reachable_menu_keys

_REPO = Path(__file__).resolve().parents[2]
_FE = _REPO / "skeletons" / "baseline" / "frontend" / "src"

# 永属总管、除多店外不得写进岗包底表的 key
_FOREVER_SUPER = frozenset({"users", "content", "category", "lookup_site", "lookup_type"})


class ClerkCrossDomainRegressionTests(unittest.TestCase):
    def test_pack_menus_do_not_claim_forever_super_keys(self) -> None:
        """岗包底表勿空头宣称总管菜单（merchant 可含 archive/content）。"""
        for pk, keys in PACK_ADMIN_MENUS.items():
            if pk == "merchant_ops":
                continue
            bad = set(keys) & _FOREVER_SUPER
            self.assertFalse(bad, f"{pk} 不应含总管空头 key: {bad}")

    def test_attach_accept_no_empty_shell_clerks(self) -> None:
        """完整挂载后：存活 clerk 必须有可进业务菜单，否则应被 prune。"""
        for domain in sorted(DOMAINS):
            with self.subTest(domain=domain):
                out = attach_accept(
                    {
                        "domain": domain,
                        "title": f"{domain}课题",
                        "capabilities": list(DOMAIN_CAPABILITIES.get(domain) or []),
                    },
                    "",
                )
                schema = out.get("schema") or {}
                posts = (schema.get("roles") or {}).get("staff_posts") or []
                for p in posts:
                    if not isinstance(p, dict) or p.get("kind") != "clerk":
                        continue
                    reach = _clerk_reachable_menu_keys(schema, p.get("packs") or [])
                    self.assertTrue(
                        reach,
                        f"{domain} clerk {p.get('id')} 空转 packs={p.get('packs')} "
                        f"menus={schema.get('staffPackMenus')}",
                    )

    def test_ticket_dashboard_admin_pushes_go_through_nav(self) -> None:
        """工作台禁止裸 $router.push('/admin/…')，一律 go(nav(...)) / withNav。"""
        path = _FE / "views" / "admin" / "TicketDashboard.vue"
        text = path.read_text(encoding="utf-8")
        naked = re.findall(r"\$router\.push\((['\"`])/admin/", text)
        self.assertEqual(naked, [], f"TicketDashboard 仍有裸 admin push: {naked}")
        self.assertIn("adminNavPath", text)
        self.assertIn("function go(", text)

    def test_special_page_uses_home_path_after_login(self) -> None:
        path = _FE / "views" / "special" / "SpecialPage.vue"
        text = path.read_text(encoding="utf-8")
        self.assertIn("homePathAfterLogin", text)
        self.assertNotIn("router.push('/admin/dashboard')", text)


if __name__ == "__main__":
    unittest.main()
