"""out_scope 与已挂能力主路径不得打架（通用消毒）。"""

from __future__ import annotations

import unittest

from app.bake.proposal_lexicon import (
    normalize_out_scope_lines,
    sanitize_out_scope_vs_capabilities,
)


class OutScopeSanitizeTests(unittest.TestCase):
    def test_time_path_rewrite_when_occupy_conflict_on(self) -> None:
        out = sanitize_out_scope_vs_capabilities(
            ["用车时段字段等扩展内容仅在进度允许时补充", "人脸闸机不在本期"],
            ["archive", "ticket_flow", "occupy_span", "time_conflict"],
        )
        self.assertEqual(len(out), 2)
        self.assertIn("时段冲突校验为本期", out[0])
        self.assertIn("扩展", out[0])
        self.assertIn("人脸", out[1])

    def test_hard_boundary_kept(self) -> None:
        out = sanitize_out_scope_vs_capabilities(
            ["真微信支付对接", "法大大电子签"],
            ["occupy_span", "time_conflict", "wallet"],
        )
        self.assertEqual(out, ["真微信支付对接", "法大大电子签"])

    def test_drop_whole_cap_exclusion(self) -> None:
        out = sanitize_out_scope_vs_capabilities(
            ["名额占用不在本期"],
            ["quota", "ticket_flow"],
        )
        self.assertEqual(out, [])

    def test_normalize_also_dedupes_features(self) -> None:
        out = normalize_out_scope_lines(
            ["支持时段冲突提示"],
            ["支持时段冲突提示", "用车时段字段扩展视进度"],
            ["occupy_span", "time_conflict"],
        )
        self.assertEqual(len(out), 1)
        self.assertIn("时段冲突校验为本期", out[0])

    def test_no_caps_passthrough(self) -> None:
        out = sanitize_out_scope_vs_capabilities(
            ["后续可加报表大屏"],
            [],
        )
        self.assertEqual(out, ["后续可加报表大屏"])


if __name__ == "__main__":
    unittest.main()
