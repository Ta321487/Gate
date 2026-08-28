"""DOM-INTERN：开题写岗位与学生绑定 → 资料绑岗（matchProfileRoom）。"""

from __future__ import annotations

import unittest

from app.bake.domain_schema import build_domain_schema
from app.bake.engine_sql import domain_sql
from app.bake.profile_fields import profile_fields_for
from app.bake.scene_scan import intern_post_bound


BIND_OPENING = (
    "本系统实现顶岗实习周报管理。要求岗位与学生绑定，"
    "学生仅可对资料确认的实习单位与岗位提交周报，导师审阅。"
)


class InternBindTests(unittest.TestCase):
    def test_intern_post_bound_true_false(self) -> None:
        self.assertTrue(intern_post_bound("顶岗实习", BIND_OPENING))
        self.assertTrue(intern_post_bound("", "岗位与学生绑定后交周报"))
        self.assertFalse(intern_post_bound("顶岗实习周报", "学生提交周报，导师审阅"))
        self.assertFalse(intern_post_bound("实习周报管理系统", ""))

    def test_schema_without_bind_no_match_profile_room(self) -> None:
        schema = build_domain_schema(
            "顶岗实习周报",
            "DOM-INTERN",
            proposal_text="学生提交周报，导师审阅",
        )
        ticket = (schema.get("entities") or {}).get("ticket") or {}
        self.assertFalse(bool(ticket.get("matchProfileRoom")))

    def test_schema_with_bind_match_profile_keys(self) -> None:
        schema = build_domain_schema(
            "顶岗实习周报管理系统",
            "DOM-INTERN",
            proposal_text=BIND_OPENING,
        )
        ticket = (schema.get("entities") or {}).get("ticket") or {}
        self.assertTrue(ticket.get("matchProfileRoom"))
        self.assertEqual(ticket.get("matchProfileBuildingKey"), "internOrg")
        self.assertEqual(ticket.get("matchProfileRoomKey"), "internPost")
        self.assertEqual(ticket.get("matchProfileBuildingField"), "isbn")
        self.assertEqual(ticket.get("matchProfileRoomField"), "title")
        self.assertTrue(ticket.get("matchProfileLooseBuilding"))

    def test_profile_fields_required_when_bind(self) -> None:
        unbound = profile_fields_for(
            "DOM-INTERN",
            title="顶岗实习周报",
            proposal_text="学生提交周报",
        )
        by_key = {f.get("key"): f for f in unbound if isinstance(f, dict)}
        self.assertIn("internOrg", by_key)
        self.assertFalse(bool(by_key["internOrg"].get("required")))

        bound = profile_fields_for(
            "DOM-INTERN",
            title="顶岗实习周报",
            proposal_text=BIND_OPENING,
        )
        by_key_b = {f.get("key"): f for f in bound if isinstance(f, dict)}
        self.assertTrue(by_key_b["internOrg"].get("required"))
        self.assertTrue(by_key_b["internPost"].get("required"))

    def test_sample_opening_bind_phrase(self) -> None:
        """近五年样例开题「岗位与学生绑定关系清晰」须走绑岗。"""
        phrase = "岗位与学生绑定关系清晰"
        self.assertTrue(intern_post_bound("顶岗实习岗位与周报审阅系统", phrase))
        schema = build_domain_schema(
            "顶岗实习岗位与周报审阅系统",
            "DOM-INTERN",
            proposal_text=f"拟解决关键问题：（3）{phrase}。",
        )
        ticket = (schema.get("entities") or {}).get("ticket") or {}
        self.assertTrue(ticket.get("matchProfileRoom"))
        self.assertEqual(ticket.get("matchProfileBuildingKey"), "internOrg")

    def test_sql_user_profile_has_intern_org_with_bind(self) -> None:
        sql = domain_sql(
            "DOM-INTERN",
            "t",
            title="顶岗实习周报",
            proposal_text=BIND_OPENING,
        )
        self.assertIn("internOrg", sql)
        self.assertIn("星河科技", sql)
        self.assertIn("资料绑岗", sql)


if __name__ == "__main__":
    unittest.main()
