"""菜单 ↔ 有效路由硬闸；与骨架 menuRoutes.js 同表。"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

from app.bake.catalog import DOMAINS
from app.bake.domain_schema import build_domain_schema
from app.bake.menu_routes import (
    ADMIN_MENU_PATHS,
    USER_MENU_PATHS,
    assert_menu_routes_aligned,
    check_menu_routes_aligned,
    shell_kind,
)

_FE_MENU = (
    Path(__file__).resolve().parents[2]
    / "skeletons"
    / "baseline"
    / "frontend"
    / "src"
    / "utils"
    / "menuRoutes.js"
)


def _parse_js_map(name: str, src: str) -> dict[str, str]:
    m = re.search(
        rf"export const {name} = \{{(.*?)\n\}}",
        src,
        re.S,
    )
    assert m, f"missing {name} in menuRoutes.js"
    out: dict[str, str] = {}
    for km in re.finditer(r"(\w+)\s*:\s*'([^']+)'", m.group(1)):
        out[km.group(1)] = km.group(2)
    return out


class MenuRoutesTests(unittest.TestCase):
    def test_py_js_registry_sync(self) -> None:
        src = _FE_MENU.read_text(encoding="utf-8")
        self.assertEqual(_parse_js_map("USER_MENU_PATHS", src), USER_MENU_PATHS)
        self.assertEqual(_parse_js_map("ADMIN_MENU_PATHS", src), ADMIN_MENU_PATHS)

    def test_shell_kind_mirrors_frontend(self) -> None:
        self.assertEqual(shell_kind(["ticket_flow"]), "ticket")
        self.assertEqual(
            shell_kind(["ticket_flow", "archive"]), "archive_ticket"
        )
        self.assertEqual(shell_kind(["order_lines", "archive"]), "order")
        self.assertEqual(shell_kind(["slot_reserve", "archive"]), "slot")
        self.assertEqual(shell_kind(["archive"]), "archive_only")
        # GENERIC 多主路径：单据 + 订单/预约
        self.assertEqual(
            shell_kind(["ticket_flow", "archive", "order_lines"]),
            "archive_ticket_multi",
        )
        self.assertEqual(
            shell_kind(["ticket_flow", "archive", "slot_reserve"]),
            "archive_ticket_multi",
        )

    def test_generic_multi_path_menus_ok(self) -> None:
        for arches in (
            ["ARCH-FLOW", "ARCH-TRADE"],
            ["ARCH-FLOW", "ARCH-RESERVE"],
            ["ARCH-TRADE", "ARCH-RESERVE"],
            ["ARCH-FLOW", "ARCH-TRADE", "ARCH-RESERVE"],
        ):
            with self.subTest(arches="+".join(arches)):
                schema = build_domain_schema(
                    "通用业务系统",
                    "DOM-GENERIC",
                    archetype=arches[0],
                    archetypes=arches,
                    proposal_text="",
                )
                assert_menu_routes_aligned(
                    schema, domain="DOM-GENERIC", traits={}, proposal_text=""
                )
    def test_unknown_menu_key_fails(self) -> None:
        issues = check_menu_routes_aligned(
            {
                "menus": {"user": [{"key": "wallet", "label": "钱包"}], "admin": []},
                "capabilities": ["archive", "order_lines"],
            },
            domain="DOM-SHOP",
        )
        self.assertTrue(any("wallet" in i for i in issues))

    def test_every_catalog_domain_default_ok(self) -> None:
        for domain in DOMAINS:
            if domain == "DOM-GENERIC":
                continue
            label = str((DOMAINS[domain] or {}).get("label") or domain)
            title = f"{label}管理系统"
            with self.subTest(domain=domain):
                schema = build_domain_schema(title, domain, proposal_text="")
                assert_menu_routes_aligned(schema, domain=domain, proposal_text="")


if __name__ == "__main__":
    unittest.main()
