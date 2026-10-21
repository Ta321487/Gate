"""bake 失败码分类：与 docs/bake-fail-analysis.md / FIX_LOCUS 同源。"""

from __future__ import annotations

import unittest
from pathlib import Path

from app.services.bake_fail_classify import (
    CODES,
    FIX_LOCUS,
    LABELS,
    catalog_payload,
    classify_bake_error,
    code_from_gates,
)


class BakeFailClassifyTests(unittest.TestCase):
    def test_codes_labels_locus_aligned(self):
        self.assertEqual(set(CODES), set(LABELS))
        self.assertEqual(set(CODES), set(FIX_LOCUS))
        self.assertEqual(FIX_LOCUS["UNKNOWN"], "待补码表")

    def test_catalog_covers_all_codes(self):
        cats = {c["code"] for c in catalog_payload()}
        self.assertEqual(cats, set(CODES))

    def test_doc_mentions_each_code(self):
        root = Path(__file__).resolve().parents[2]
        doc = (root / "docs" / "bake-fail-analysis.md").read_text(encoding="utf-8")
        for code in CODES:
            self.assertIn(code, doc, msg=f"文档缺少码 {code}")

    def test_ops_and_bake_stems(self):
        cases = [
            ("服务重启，任务中断 · 请从失败步骤重试", "OPS_RESTART"),
            ("已取消", "OPS_CANCELLED"),
            ("项目不存在", "OPS_PROJECT_MISSING"),
            ("交付复审进行中 · 不可重跑生成", "OPS_REVIEW_LOCK"),
            ("工作区不存在，无法续跑，请重新一键生成", "RESUME_NO_WORKSPACE"),
            ("库表须满足 3NF 口径（禁止 JSON 当业务规则）：x", "BAKE_SCHEMA_NF"),
            ("DOM-SHOP schema 表数量=19，超过硬顶 18", "BAKE_TABLE_BUDGET"),
            ("档案语义列未对齐（逻辑 author/isbn 与物理列不一致）", "BAKE_ARCHIVE_COLUMNS"),
            ("schema.sql 缺少 books 的 INSERT IGNORE 演示种子", "BAKE_ARCHIVE_SEED"),
            ("身份/壳未对齐 [DOM-SHOP] title=x: y", "BAKE_IDENTITY"),
            ("菜单/路由未对齐：\n- a", "BAKE_MENU_ROUTES"),
            ("硬拦与收集 UI 未对齐[DOM-X]: z", "BAKE_HARD_ASSERT_UI"),
            ("错皮/怪交互硬闸失败 [DOM-SHOP] title=t: miss", "BAKE_SKIN"),
            ("DOM-SHOP schema 缺少 entities.order.refundReasonOptions", "BAKE_TRADE_SURFACE"),
            ("usecase: L1 无二级用例", "BAKE_USECASE"),
            ("persistence=mybatis 包仍含 JdbcSupport", "BAKE_PERSISTENCE"),
            ("Spring Security 叠层缺少: foo", "BAKE_ADDON_SECURITY"),
            ("pack_prune 后仍残留未挂岛文件", "BAKE_PACK_LEAN"),
            ("填岛合并失败", "FILL_MERGE"),
            ("骨架不完整", "BUILD_SKELETON"),
            ("编译失败 · [ERROR] ...", "BUILD_COMPILE"),
            ("未知身份场景：campus", "MATCH_PATH"),
            ("无法连接学生 MySQL · refused", "STUDENT_DB"),
        ]
        for err, want in cases:
            got = classify_bake_error(err)
            self.assertEqual(got.code, want, msg=err)
            self.assertEqual(got.fix_locus, FIX_LOCUS[want])

    def test_gate_overall_message(self):
        err = "质量检查未通过 · 暂不可下载交付包 · 交付质量摘要 · 2 项 error · 跨域词"
        got = classify_bake_error(err)
        self.assertEqual(got.code, "GATE_QA")

    def test_gates_dict_priority(self):
        gates = {
            "overall": False,
            "p3q": {"ok": False, "label": "交付质量摘要", "desc": "1 项 error"},
            "p2": {"ok": False, "label": "领域主流程 E2E"},
        }
        self.assertEqual(code_from_gates(gates), "GATE_QA")
        got = classify_bake_error(
            "质量检查未通过 · 暂不可下载交付包 · x",
            gates=gates,
        )
        self.assertEqual(got.code, "GATE_QA")

    def test_accept_gate(self):
        gates = {"accept": {"ok": False, "desc": "reject"}, "overall": False}
        self.assertEqual(code_from_gates(gates), "GATE_ACCEPT")

    def test_unknown_no_fake_locus(self):
        got = classify_bake_error("completely novel failure xyzzy")
        self.assertEqual(got.code, "UNKNOWN")
        self.assertEqual(got.fix_locus, "待补码表")
        self.assertEqual(got.confidence, "low")

    def test_generic_unrealized(self):
        got = classify_bake_error(
            "质量检查未通过 · 暂不可下载交付包 · 该领域尚未做实，禁止交付"
        )
        self.assertEqual(got.code, "GATE_GENERIC_UNREALIZED")


if __name__ == "__main__":
    unittest.main()
