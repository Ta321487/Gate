"""论文用例描述表：menus + 开题选用，禁止发明未交付功能。"""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from app.bake.schema.usecase_descriptions import (
    DEFAULT_DESC_COUNT,
    build_usecase_description_candidates,
    normalize_desc_count,
    select_usecase_descriptions,
    usecase_description_model,
)


class UsecaseDescriptionTests(unittest.TestCase):
    def _schema(self, stem: str) -> dict:
        path = Path(__file__).resolve().parents[0] / "golden" / "schema" / f"{stem}.json"
        return json.loads(path.read_text(encoding="utf-8"))

    def test_normalize_count(self) -> None:
        self.assertEqual(normalize_desc_count(4), 4)
        self.assertEqual(normalize_desc_count("3"), 3)
        self.assertEqual(normalize_desc_count(99), DEFAULT_DESC_COUNT)

    def test_hospital_four_cases_from_menus(self) -> None:
        model = usecase_description_model(self._schema("DOM-HOSPITAL"), count=4)
        self.assertEqual(model["count"], 4)
        self.assertIn("仅针对", model["intro"])
        names = [c["name"] for c in model["cases"]]
        blob = " ".join(names)
        self.assertIn("登录", blob)
        # 必须来自交付菜单语义
        self.assertTrue(any("医生" in n or "挂号" in n for n in names))
        # 禁止发明开题外/未交付能力
        md = model["markdown"]
        self.assertNotIn("电子病历", md)
        self.assertNotIn("医保", md)
        self.assertNotIn("自习室", md)
        for c in model["cases"]:
            self.assertTrue(c["flow"])
            self.assertTrue(c["actor"])
            self.assertTrue(c["summary"])

    def test_proposal_boosts_mentioned_menu(self) -> None:
        schema = self._schema("DOM-HOSPITAL")
        proposal = (
            "患者功能模块划分为：选医生、我的挂号、公告、个人资料。\n"
            "本系统支持患者选医生并完成挂号。"
        )
        model = usecase_description_model(schema, proposal_text=proposal, count=4)
        names = " ".join(c["name"] for c in model["cases"])
        self.assertIn("登录", names)
        self.assertTrue("挂号" in names or "医生" in names)
        self.assertTrue(
            any(c.get("source", "").startswith("proposal") for c in model["cases"])
        )

    def test_no_invented_menus(self) -> None:
        schema = {
            "title": "最小系统",
            "labels": {"appName": "最小系统"},
            "roles": {"user": {"label": "用户"}, "admin": {"label": "管理员"}},
            "entities": {"archive": {"label": "事项"}},
            "menus": {
                "user": [{"key": "profile", "label": "个人资料"}],
                "admin": [{"key": "users", "label": "用户管理"}],
            },
            "capabilities": ["org_users"],
        }
        model = usecase_description_model(schema, count=4)
        blob = model["markdown"]
        self.assertIn("个人资料", blob)
        self.assertIn("用户", blob)
        self.assertNotIn("购物车", blob)
        self.assertNotIn("挂号", blob)
        self.assertNotIn("自习室", blob)
        # 候选不足 4 时不强凑
        self.assertLessEqual(model["count"], 4)
        self.assertGreaterEqual(model["count"], 2)

    def test_register_only_when_proposal_mentions(self) -> None:
        schema = self._schema("DOM-HOSPITAL")
        without = build_usecase_description_candidates(schema, proposal_text="")
        self.assertFalse(any(c["kind"] == "auth_register" for c in without))
        with_reg = build_usecase_description_candidates(
            schema, proposal_text="用户可注册账号后登录挂号"
        )
        self.assertTrue(any(c["kind"] == "auth_register" for c in with_reg))

    def test_select_dedupes(self) -> None:
        cands = [
            {
                "name": "A",
                "score": 10,
                "side": "user",
                "menu_key": "profile",
                "kind": "profile",
                "flow": ["1"],
                "actor": "用户",
                "summary": "s",
            },
            {
                "name": "A",
                "score": 9,
                "side": "user",
                "menu_key": "profile2",
                "kind": "profile",
                "flow": ["1"],
                "actor": "用户",
                "summary": "s",
            },
            {
                "name": "B",
                "score": 8,
                "side": "user",
                "menu_key": "messages",
                "kind": "messages",
                "flow": ["1"],
                "actor": "用户",
                "summary": "s",
            },
        ]
        picked = select_usecase_descriptions(cands, count=4)
        self.assertEqual(len(picked), 2)
        self.assertEqual({p["name"] for p in picked}, {"A", "B"})


if __name__ == "__main__":
    unittest.main()
