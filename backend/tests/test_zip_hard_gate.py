"""出包硬闸：门禁未放行 / QA 失败不得 SUCCESS；续跑不得靠关 QA 装绿。"""

from __future__ import annotations

import unittest

from app.services.delivery_review import apply_qa_to_gates


class ZipHardGateTests(unittest.TestCase):
    def test_fallback_qa_payment_error_blocks_overall(self) -> None:
        from app.llm.agents_qa import _fallback_qa

        gates = {"overall": True, "zip_allowed": True, "p0a": {"ok": True}}
        qa = _fallback_qa(
            {
                "labels": {
                    "demoPayHint": "请选择支付宝或微信支付完成下单。",
                    "appName": "店",
                    "noticePageTitle": "公告",
                },
                "capabilities": ["wallet"],
                "menus": {},
                "menuKeys": {},
                "entityKeys": [],
                "files": {},
                "missing_files": [],
                "proposal": "",
                "domain": "DOM-SHOP",
            }
        )
        apply_qa_to_gates(gates, qa, warn_blocks=False)
        self.assertFalse(gates["p3q"]["ok"])
        self.assertFalse(gates["overall"])
        self.assertFalse(gates["zip_allowed"])

    def test_qa_failed_mode_blocks_like_error(self) -> None:
        gates = {"overall": True, "zip_allowed": True}
        apply_qa_to_gates(
            gates,
            {
                "ok": False,
                "mode": "failed",
                "summary": "QA 执行失败，禁止放行",
                "findings": [{"level": "error", "msg": "boom", "where": "qa"}],
            },
            warn_blocks=False,
        )
        self.assertFalse(gates["p3q"]["ok"])
        self.assertFalse(gates["zip_allowed"])

    def test_gate_fail_summary_prefers_p3q(self) -> None:
        from app.services.jobs import _gate_fail_summary

        detail = _gate_fail_summary(
            {
                "overall": False,
                "zip_allowed": False,
                "p3q": {
                    "ok": False,
                    "label": "交付质量摘要",
                    "desc": "1 项 error · labels.demoPayHint 将支付宝/微信写成本期支付能力",
                },
                "p2": {"ok": True, "label": "主流程", "desc": "ok"},
            }
        )
        self.assertIn("交付质量摘要", detail)
        self.assertIn("demoPayHint", detail)


if __name__ == "__main__":
    unittest.main()
