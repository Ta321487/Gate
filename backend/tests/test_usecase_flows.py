"""工厂用例描述流程台：种子、face 覆盖、68 域菜单零缺口。"""

from __future__ import annotations

import unittest
from pathlib import Path

from app.bake.catalog import DOMAINS
from app.services import usecase_flows as uf
from app.services.asset_seeds import load_seed_json


class UsecaseFlowsUnit(unittest.TestCase):
    def setUp(self) -> None:
        load_seed_json.cache_clear()
        uf.invalidate_cache()
        uf.bootstrap_from_seed()

    def test_seed_has_star_and_cinema_faces(self) -> None:
        rows = uf._seed_payload()
        kinds = {r["flow_kind"] for r in rows if r.get("face") == "*"}
        self.assertIn("seat_shows", kinds)
        self.assertIn("orders", kinds)
        self.assertIn("my_archive", kinds)
        self.assertIn("peer_tickets", kinds)
        faces = {(r["flow_kind"], r["face"]) for r in rows}
        self.assertIn(("orders", "performance"), faces)
        self.assertIn(("orders", "cinema"), faces)

    def test_resolve_face_override(self) -> None:
        star = uf.resolve_flow_spec("orders", face="*")
        perf = uf.resolve_flow_spec("orders", face="performance")
        self.assertIn("发货", star["summary"] + "".join(star["flow"]))
        self.assertIn("核销", perf["summary"] + "".join(perf["flow"]))
        self.assertNotIn("确认、发货", "".join(perf["flow"]))

    def test_unknown_kind_falls_to_open(self) -> None:
        hit = uf.resolve_flow_spec("no_such_kind_xyz")
        open_spec = uf.resolve_flow_spec("open")
        self.assertEqual(hit["name"], open_spec["name"])

    def test_gap_empty_on_full_seed(self) -> None:
        report = uf.gap_report()
        self.assertEqual(report["gap_count"], 0)

    def test_all_domains_zero_menu_flow_gaps(self) -> None:
        """68 域菜单推导出的 kind 相对种子零缺口。"""
        report = uf.catalog_domain_gaps()
        self.assertEqual(report["domain_count"], len(DOMAINS))
        self.assertEqual(
            report["gap_count"],
            0,
            msg="; ".join(
                f"{g['domain_id']}:{g['flow_kind']}" for g in report["gaps"][:30]
            ),
        )

    def test_renderer_has_no_builtin_flow_blob(self) -> None:
        src = Path("app/bake/schema/usecase_descriptions.py").read_text(encoding="utf-8")
        self.assertIn("usecase_flows", src)
        self.assertNotIn("确认、发货等办理操作", src)
        self.assertNotIn('"{actor}选座购票"', src)
        self.assertNotIn("def _apply_cinema_face_flow", src)

    def test_placeholders_documented(self) -> None:
        tokens = {p["token"] for p in uf.PLACEHOLDERS}
        self.assertIn("{actor}", tokens)
        self.assertIn("{ticket_stem}", tokens)
        self.assertTrue(all(p.get("zh") for p in uf.PLACEHOLDERS))

    def test_no_hardcoded_put_in_service(self) -> None:
        src = Path(uf.__file__).read_text(encoding="utf-8")
        self.assertNotIn('put("DOM-', src)
        self.assertIn("load_seed_json", src)


if __name__ == "__main__":
    unittest.main()
