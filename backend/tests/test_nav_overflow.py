"""管理侧栏项多略密 + navItemActive；门户顶栏改由 portalShellNav（见 test_portal_shell_nav）。"""

from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path

_FRONT = (
    Path(__file__).resolve().parents[2] / "skeletons" / "baseline" / "frontend" / "src"
)
_UTIL = _FRONT / "utils" / "navOverflow.js"


def _eval_nav(payload: dict) -> dict:
    script = (
        "import { splitPortalNav, adminAsideDense, navItemActive } "
        f"from {json.dumps(_UTIL.as_uri())};\n"
        f"const input = {json.dumps(payload, ensure_ascii=False)};\n"
        "const items = input.items;\n"
        "const split = splitPortalNav(items);\n"
        "console.log(JSON.stringify({\n"
        "  primary: split.primary.map((x) => x.to),\n"
        "  more: split.more.map((x) => x.to),\n"
        "  dense: input.counts.map((n) => adminAsideDense(n)),\n"
        "  active: input.paths.map(([p, t]) => navItemActive(p, t)),\n"
        "}));\n"
    )
    proc = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    if proc.returncode != 0:
        raise AssertionError(proc.stderr or proc.stdout)
    return json.loads(proc.stdout)


class NavOverflowTests(unittest.TestCase):
    def test_aside_dense_and_active(self) -> None:
        six = [{"to": f"/m{i}", "label": f"项{i}"} for i in range(6)]
        fit = _eval_nav(
            {
                "items": six,
                "counts": [0, 8, 9, 12],
                "paths": [
                    ["/orders/1", "/orders"],
                    ["/home", "/"],
                    ["/cart", "/cart"],
                ],
            }
        )
        self.assertEqual(fit["dense"], [False, False, True, True])
        self.assertEqual(fit["active"], [True, False, True])

    def test_split_helper_still_caps(self) -> None:
        """legacy helper 仍可供非门户调用；阈值保持 ≤6 / 前 5。"""
        ten = [{"to": f"/m{i}", "label": f"项{i}"} for i in range(10)]
        got = _eval_nav(
            {
                "items": ten,
                "counts": [9],
                "paths": [["/a", "/a"]],
            }
        )
        self.assertEqual(got["primary"], [f"/m{i}" for i in range(5)])
        self.assertEqual(got["more"], [f"/m{i}" for i in range(5, 10)])

    def test_admin_wires_dense(self) -> None:
        admin = (_FRONT / "layouts" / "AdminLayout.vue").read_text(encoding="utf-8")
        chrome = (_FRONT / "styles" / "chrome.css").read_text(encoding="utf-8")
        thesis = (_FRONT / "styles" / "thesis-display.css").read_text(encoding="utf-8")
        layout = (_FRONT / "styles" / "layout.css").read_text(encoding="utf-8")
        self.assertIn("wb-aside--dense", admin)
        self.assertIn("wb-menu-scroll", admin)
        self.assertIn("adminAsideDense", admin)
        self.assertIn(".wb-menu-scroll", chrome)
        self.assertIn(".wb-aside--dense", chrome)
        self.assertIn(".wb-menu-scroll", thesis)
        self.assertIn("flex-wrap: nowrap", layout)
        self.assertIn("PORTAL_NAV_INLINE_MAX = 6", _UTIL.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
