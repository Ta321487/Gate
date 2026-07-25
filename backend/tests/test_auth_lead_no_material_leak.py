"""authLead / 轮播 lead 不得粘贴开题【材料：】前缀（复用既有判断，全域）。"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.bake.catalog import build_spec
from app.bake.domain_schema import (
    _ui_safe_excerpt,
    deterministic_llm_patch,
    ui_copy_polluted,
)
from app.bake.engine_resources import _write_factory_delivered
from app.bake.portal_banners import _caption_seeds, _welcome_lead
from app.llm.agents_island import _sanitize_island_patch


_LEAK = (
    "【材料：01-DOM-LIBRARY-高校图书借阅管理系统.txt】"
    "本科毕业设计（论文）开题报告 题目：基于 Spring Boot 与 Vue 的高校图书借。"
)

_RECRUIT_LEAK = (
    "【材料：07-DOM-RECRUIT-高校校园招聘岗位投递管理系统.txt】"
    "本科毕业设计（论文）开题报告 题目：基于 Spring Boot 与 Vue 的高。"
    "验证码登录后即可使用系统主流程。"
)


class TestAuthLeadNoMaterialLeak(unittest.TestCase):
    def test_strip_material_header(self) -> None:
        safe = _ui_safe_excerpt(_LEAK)
        self.assertNotIn("【材料：", safe)
        self.assertNotIn("开题报告", safe)

    def test_ui_copy_polluted_recruit_screenshot(self) -> None:
        self.assertTrue(ui_copy_polluted(_RECRUIT_LEAK))
        self.assertFalse(
            ui_copy_polluted("验证码登录；浏览校招岗位并投递简历，就业办初筛后反馈结果。")
        )

    def test_welcome_lead_skips_leak(self) -> None:
        schema = {
            "labels": {
                "authLead": _LEAK + "验证码登录后即可使用系统主流程。",
                "portalBannerLead": "按书名检索并提交借阅。",
            },
            "portalBanners": [
                {"title": "开架阅览", "lead": "按书名、作者或 ISBN 检索，在线提交借阅。"},
            ],
        }
        lead = _welcome_lead(schema)
        self.assertNotIn("【材料：", lead)
        self.assertNotIn("开题报告", lead)
        for c in _caption_seeds(schema):
            self.assertNotIn("【材料：", c.get("lead") or "")
            self.assertNotIn("开题报告", c.get("lead") or "")

    def test_write_factory_delivered_scrubs_auth_lead(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            dest = Path(td)
            (dest / "frontend" / "src").mkdir(parents=True)
            schema = {
                "labels": {
                    "appName": "校园招聘",
                    "authLead": _RECRUIT_LEAK,
                },
                "roles": {"user": {"id": "user", "label": "求职者"}},
                "menus": {"user": [], "admin": []},
                "entities": {},
                "capabilities": [],
            }
            _write_factory_delivered(
                dest,
                "校园招聘",
                "gen-ink",
                "split",
                schema,
                domain="DOM-RECRUIT",
            )
            text = (dest / "frontend" / "src" / "appDelivered.js").read_text(encoding="utf-8")
            self.assertNotIn("【材料：", text)
            self.assertNotIn("07-DOM-RECRUIT", text)
            self.assertNotIn("开题报告", text)

    def test_island_rejects_leaked_auth_lead(self) -> None:
        base = {"authLead": "验证码登录，开放注册；读者可检索图书并申请借阅。"}
        patch = _sanitize_island_patch(
            {"labels": {"authLead": _LEAK}},
            base_labels=base,
            base_seeds={},
        )
        self.assertNotIn("authLead", patch.get("labels") or {})

    def test_keeps_domain_auth_lead(self) -> None:
        spec = build_spec(
            title="基于 Spring Boot 与 Vue 的高校图书借阅管理系统的设计与实现",
            archetype="ARCH-FLOW",
            domain="DOM-LIBRARY",
            theme="lib-ink",
            llm_enabled=False,
            match_mode="recommended",
            confidence=0.9,
        )
        domain_lead = (spec.get("schema") or {}).get("labels", {}).get("authLead")
        self.assertTrue(domain_lead)
        spec["proposal"] = {"excerpt": _LEAK}
        patch = deterministic_llm_patch(spec, True)
        self.assertEqual(patch["labels"]["authLead"], domain_lead)
        self.assertNotIn("【材料：", patch["labels"]["authLead"])


if __name__ == "__main__":
    unittest.main()
