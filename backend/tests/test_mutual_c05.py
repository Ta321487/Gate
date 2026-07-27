"""泳道 E · C-05：互选确认；P-09～P-11 挂 DOM-MUTUAL-*。"""

from __future__ import annotations

import unittest
from pathlib import Path

from app.bake.capabilities import CAPABILITIES
from app.bake.catalog import match_text
from app.bake.domain_schema import build_domain_schema, validate_schema
from app.bake.domains import DOMAIN_CAPABILITIES, DOMAINS
from app.bake.engine_sql import domain_sql
from app.bake.menu_routes import USER_MENU_PATHS, check_menu_routes_aligned
from app.bake.oa_apply_p import MUTUAL_CASES

SAMPLES = Path(__file__).resolve().parents[2] / "data" / "samples" / "申请预设开题"


class MutualC05Tests(unittest.TestCase):
    def test_capability_registered(self) -> None:
        self.assertIn("mutual_select", CAPABILITIES)
        self.assertEqual(CAPABILITIES["mutual_select"]["status"], "implemented")
        for _pid, _p, domain, _t in MUTUAL_CASES:
            self.assertIn("mutual_select", DOMAIN_CAPABILITIES[domain])

    def test_p09_p11_hit_and_schema(self) -> None:
        self.assertEqual(len(MUTUAL_CASES), 3)
        for sid, phrase, want, title in MUTUAL_CASES:
            with self.subTest(id=sid):
                got = match_text(f"基于 Spring Boot 的{title}的设计与实现。主要功能：{phrase}。")
                self.assertEqual(got.domain, want, f"hits={got.hits[:10]}")
                schema = build_domain_schema(title, want)
                ok, errs = validate_schema(schema)
                self.assertTrue(ok, errs[:5])
                ticket = (schema.get("entities") or {}).get("ticket") or {}
                self.assertTrue(ticket.get("peerAccept"))
                self.assertTrue(ticket.get("approveEndsFlow"))
                menus = [m.get("key") for m in (schema.get("menus") or {}).get("user") or []]
                self.assertIn("peer_tickets", menus)
                issues = check_menu_routes_aligned(schema, domain=want)
                self.assertEqual(issues, [], issues)

    def test_neighbors(self) -> None:
        cases = [
            ("研究生导师双向选择志愿与确认", "DOM-MUTUAL-TUTOR", "DOM-DATING"),
            ("研究生导师双向选择志愿与确认", "DOM-MUTUAL-TUTOR", "DOM-RECRUIT"),
            ("毕业论文选题双选志愿与确认", "DOM-MUTUAL-TOPIC", "DOM-COURSE"),
            ("竞赛组队学习搭子意向匹配", "DOM-MUTUAL-TEAM", "DOM-DATING"),
            ("竞赛组队学习搭子意向匹配", "DOM-MUTUAL-TEAM", "DOM-ACTIVITY"),
            ("校园相亲牵线交友审核", "DOM-DATING", "DOM-MUTUAL-TUTOR"),
        ]
        for phrase, want, avoid in cases:
            with self.subTest(phrase=f"{phrase}->{want}!={avoid}"):
                got = match_text(f"基于 Spring Boot 的{phrase}系统的设计与实现")
                self.assertEqual(got.domain, want, f"hits={got.hits[:10]}")
                self.assertNotEqual(got.domain, avoid)

    def test_sql_has_owner_username(self) -> None:
        sql = domain_sql(
            "DOM-MUTUAL-TUTOR",
            "t_tutor",
            title="研究生导师双向选择志愿与确认系统",
            proposal_text="研究生导师双向选择志愿与确认",
        )
        self.assertIn("owner_username", sql)
        self.assertIn("tutor_wish", sql)
        self.assertIn("'peer'", sql)

    def test_samples_and_menu_path(self) -> None:
        self.assertEqual(USER_MENU_PATHS.get("peer_tickets"), "/peer-tickets")
        for sid, _p, domain, title in MUTUAL_CASES:
            path = SAMPLES / f"{sid}-{domain}-{title}.txt"
            self.assertTrue(path.is_file(), path)
            self.assertIn(domain, DOMAINS)


if __name__ == "__main__":
    unittest.main()
