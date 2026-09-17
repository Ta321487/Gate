"""五组压力开题冒烟：match → 扫词挂 caps → attach_accept → schema/SQL。

组：报修 / 预约 / 报名 / 借用 / 内容。
"""

from __future__ import annotations

import re
import unittest
from typing import Any

from app.bake.catalog import match_text
from app.bake.domain_schema import attach_accept, required_capabilities
from app.bake.engine_sql import domain_sql
from app.bake.identity_align import assert_identity_aligned
from app.bake.menu_routes import assert_menu_routes_aligned
from app.bake.proposal_pressure import expected_capability_ids
from app.bake.sample_proposal import build_sample_proposal

_TRAILING_COMMA = re.compile(r",\s*\n\s*\)")

_PRESSURE_GROUPS: list[tuple[str, str]] = [
    ("报修", "dorm"),
    ("预约", "meeting"),
    ("预约", "salon"),
    ("报名", "activity"),
    ("借用", "library"),
    ("借用", "asset"),
    ("内容", "forum"),
    ("内容", "media"),
    ("内容", "blog"),
    ("申请", "seal"),
    ("申请", "cert"),
]


class PressureGroupBakeSmokeTests(unittest.TestCase):
    def test_pressure_groups_match_caps_and_bake(self) -> None:
        for group, pack_id in _PRESSURE_GROUPS:
            with self.subTest(group=group, pack=pack_id):
                sp = build_sample_proposal(pack_id=pack_id, seed=1, pressure=True)
                domain = sp.anchor_domain
                title = sp.title
                text = sp.text

                got = match_text(text, sp.filename)
                self.assertEqual(
                    got.domain,
                    domain,
                    f"{group}/{pack_id} match={got.domain} warn={got.match_warnings}",
                )

                archetype = got.archetype
                arches = list(got.archetypes or ([archetype] if archetype else []))
                base = required_capabilities(domain, archetype, archetypes=arches)
                spec = attach_accept(
                    {
                        "domain": domain,
                        "title": title,
                        "archetype": archetype,
                        "archetypes": arches,
                        "capabilities": base,
                        "features": [],
                    },
                    text,
                )
                caps = list(spec.get("capabilities") or [])
                self.assertEqual(
                    spec.get("accept"),
                    "full",
                    f"{group}/{pack_id} accept={spec.get('accept')} reason={spec.get('accept_reason')}",
                )
                for cap in expected_capability_ids(domain):
                    self.assertIn(
                        cap,
                        caps,
                        f"{group}/{pack_id} missing cap {cap}; caps={caps}",
                    )

                schema = spec.get("schema") if isinstance(spec.get("schema"), dict) else {}
                self.assertTrue(schema, f"{group}/{pack_id} empty schema")
                sql = domain_sql(
                    domain, "pressure_smoke", title=title, proposal_text=text
                )
                self.assertFalse(
                    _TRAILING_COMMA.search(sql),
                    f"{group}/{pack_id} schema.sql 末列拖尾逗号",
                )
                assert_identity_aligned(
                    domain,
                    title=title,
                    proposal_text=text,
                    sql=sql,
                    schema=schema,
                    profile_fields=schema.get("profileFields"),
                )
                assert_menu_routes_aligned(
                    schema,
                    domain=domain,
                    proposal_text=text,
                )
                self._assert_pressure_surface(domain, schema, caps)

    def _assert_pressure_surface(
        self, domain: str, schema: dict[str, Any], caps: list[str]
    ) -> None:
        menus = schema.get("menus") or {}
        all_keys = {
            str(m.get("key"))
            for side in ("user", "admin")
            for m in (menus.get(side) or [])
            if isinstance(m, dict) and m.get("key")
        }
        labels = schema.get("labels") or {}
        label_blob = " ".join(str(v) for v in labels.values())

        if "staff_roster" in caps:
            self.assertTrue(
                "staff_roster" in all_keys or "排班" in label_blob,
                f"{domain} staff_roster 挂载后菜单/文案未见排班 keys={sorted(all_keys)[:20]}",
            )
        if "dm" in caps:
            self.assertTrue(
                "dm" in all_keys or "私信" in label_blob or "客服" in label_blob,
                f"{domain} dm 挂载后未见入口 keys={sorted(all_keys)[:20]}",
            )


if __name__ == "__main__":
    unittest.main()
