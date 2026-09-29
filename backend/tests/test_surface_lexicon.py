"""话术层（Surface Lexicon）：槽位解析优先级、同义簇跟随、跨域串词门禁。

对应设计稿 `docs/surface-lexicon-design.md` 批 B1（话术层）/ B2（渲染分支）/ C（error 门禁）。
"""

from __future__ import annotations

import unittest
from pathlib import Path

from app.bake.domain_vocab import (
    cross_domain_findings,
    lexicon_findings,
    render_guard_findings,
    slot_divergence_findings,
)
from app.bake.schema.builders_archive import _event_schema
from app.bake.schema.followup_presets import followup_domain_schema
from app.bake.ticket_copy_text import fill_slots, normalize_slot_words, resolve_slots

REPO = Path(__file__).resolve().parents[2]
MY_TICKETS = REPO / "skeletons" / "baseline" / "frontend" / "src" / "views" / "user" / "MyTickets.vue"

PROPOSAL_CRM = "中小企业客户评级系统：客户档案、客户评级、跟进提交与办结。"
PROPOSAL_EVENT = "社区公共卫生事件应急上报系统：学生填报本人上报，异常可转处置。"
PROPOSAL_EVENT_SELF = "校园晨午检：学生打卡填报与异常上报，班主任台账作说明。"


def _axis(schema: dict) -> str:
    fields = schema["entities"]["archive"]["fields"]
    return next(f["label"] for f in fields if f["key"] == "category")


def _menu(schema: dict, key: str) -> str:
    return next(m["label"] for m in schema["menus"]["admin"] if m["key"] == key)


class SlotResolutionTests(unittest.TestCase):
    def test_schema_carries_lex_slots(self):
        schema = followup_domain_schema("测试课题", "DOM-CRM")
        self.assertEqual(schema["lex"]["category_axis"], "客户分级")
        self.assertEqual(schema["lex"]["ticket_noun"], "跟进")

    def test_proposal_cluster_word_wins_and_prefix_kept(self):
        schema = followup_domain_schema("测试课题", "DOM-CRM", proposal_text=PROPOSAL_CRM)
        self.assertEqual(schema["lex"]["category_axis"], "客户评级")
        self.assertEqual(_axis(schema), "客户评级")
        self.assertEqual(_menu(schema, "category"), "客户评级管理")

    def test_proposal_outside_cluster_falls_back_to_domain_default(self):
        schema = followup_domain_schema("测试课题", "DOM-CRM", proposal_text="人脸识别门禁系统")
        self.assertEqual(schema["lex"]["category_axis"], "客户分级")

    def test_unknown_slot_value_is_not_invented(self):
        preset = {"archive_label": "案件", "archive_fields": [], "ticket_label": "跟进单"}
        lex = resolve_slots(preset, proposal_text="案件台账管理")  # 材料无簇词 → 通用兜底
        self.assertEqual(lex["category_axis"], "分类")

    def test_fill_slots_replaces_only_declared_tokens(self):
        obj = {"lead": "按{category_axis}浏览{archive_plural}。", "keep": "原样"}
        fill_slots(obj, {"category_axis": "客户分级", "archive_plural": "客户"})
        self.assertEqual(obj["lead"], "按客户分级浏览客户。")
        self.assertEqual(obj["keep"], "原样")

    def test_normalize_slot_words_keeps_adjacent_terms(self):
        self.assertEqual(normalize_slot_words("还没有申请记录", "ticket_noun", "登记"), "还没有登记记录")
        # 邻近还有簇词时不动，避免造出「借阅借阅」
        self.assertEqual(normalize_slot_words("申请借阅", "ticket_noun", "借阅"), "申请借阅")
        self.assertEqual(normalize_slot_words("提交申请", "ticket_noun", "借阅"), "提交借阅")


class EventSelfReportTests(unittest.TestCase):
    """① 事件域本人填单皮：单据名词随槽位走，禁止写死「打卡」。"""

    def test_report_proposal_uses_report_noun(self):
        schema = _event_schema("社区公共卫生事件应急上报系统", PROPOSAL_EVENT)
        self.assertEqual(schema["lex"]["ticket_noun"], "上报")
        self.assertEqual(schema["labels"]["myTicketsEmpty"], "还没有上报记录，点击右上角提交。")

    def test_checkin_proposal_keeps_checkin_noun(self):
        schema = _event_schema("校园晨午检打卡系统", PROPOSAL_EVENT_SELF)
        self.assertEqual(schema["lex"]["ticket_noun"], "打卡")
        self.assertEqual(schema["labels"]["myTicketsEmpty"], "还没有打卡记录，点击右上角提交。")
        menus = schema["menus"]["user"]
        self.assertIn("打卡", next(m["label"] for m in menus if m["key"] == "my_tickets"))


class CrossDomainGateTests(unittest.TestCase):
    """C 批三条规则：error 级反例必红，现有产物保持绿。"""

    def test_report_domain_injected_checkin_word_is_error(self):
        schema = _event_schema("社区公共卫生事件应急上报系统", PROPOSAL_EVENT)
        self.assertEqual(slot_divergence_findings(schema), [])
        schema["labels"]["myTicketsEmpty"] = "还没有打卡记录，点击右上角提交。"
        findings = slot_divergence_findings(schema)
        self.assertTrue(findings)
        self.assertTrue(all(f["level"] == "error" for f in findings))
        self.assertIn("ticket_noun", findings[0]["msg"])

    def test_crm_injected_category_axis_word_is_error(self):
        schema = followup_domain_schema("测试课题", "DOM-CRM")
        self.assertEqual(slot_divergence_findings(schema), [])
        schema["portalBanners"][0]["lead"] = "按分类标签浏览客户，维护联系人与备注。"
        findings = slot_divergence_findings(schema)
        self.assertTrue(findings)
        self.assertIn("category_axis", findings[0]["msg"])

    def test_cross_domain_exclusive_noun_is_error(self):
        schema = followup_domain_schema("测试课题", "DOM-CRM")
        schema["labels"]["myTicketsPageLead"] = "在此提交挂号并跟踪进度。"
        findings = cross_domain_findings(schema, "DOM-CRM")
        self.assertTrue(any("挂号" in f["msg"] for f in findings))

    def test_unguarded_domain_field_render_is_error(self):
        raw = "        <template v-if=\"row.dueAt\"> · {{ dueLabel }} {{ row.dueAt }}</template>\n"
        findings = render_guard_findings({"frontend/src/views/user/MyTickets.vue": raw})
        self.assertTrue(any(f["level"] == "error" for f in findings))

    def test_script_data_mapping_is_not_a_render(self):
        """❌ 回归：脚本里取值/工具函数不是渲染，任何域都要能取值。"""
        raw = "\n".join(
            [
                "<template><div></div></template>",
                "<script setup>",
                "const due = res.data?.dueAt || res.data?.data?.dueAt",
                "const used = Number(row.renewCount) || 0",
                "function holdCountdownText(row) {",
                "  if (!row?.holdExpireAt) return null",
                "  return secondsUntil(row.holdExpireAt, nowMs.value)",
                "}",
                "</script>",
            ]
        )
        self.assertEqual(render_guard_findings({"frontend/src/views/user/MyTickets.vue": raw}), [])

    def test_baseline_my_tickets_has_no_unguarded_field(self):
        body = MY_TICKETS.read_text(encoding="utf-8")  # 整份文件（含 <script> 取值）
        self.assertEqual(render_guard_findings({"frontend/src/views/user/MyTickets.vue": body}), [])

    def test_form_input_and_value_guard_are_not_a_render(self):
        """❌ 回归：`v-model` 表单输入 / `!= null` 值守卫都不是「无条件渲染域外字段」。"""
        raw = "\n".join(
            [
                "<template>",
                '  <el-input-number v-model="form.qty" :min="1" :max="999" />',
                '  <template v-if="row.actualQty != null"> · 实发{{ row.actualQty }}</template>',
                "</template>",
            ]
        )
        self.assertEqual(render_guard_findings({"frontend/src/views/x/Generic.vue": raw}), [])

    def test_capability_owned_pages_are_exempt_but_gate_still_arms(self):
        """能力专属页豁免不得把通用页一起豁免（门禁不能被静默阉掉）。"""
        from app.bake.domain_vocab import _CAPABILITY_OWNED_PAGES

        self.assertTrue(all(path.endswith(".vue") for path, _ in _CAPABILITY_OWNED_PAGES))
        self.assertTrue(all(reason.strip() for _, reason in _CAPABILITY_OWNED_PAGES))
        self.assertNotIn("views/user/MyTickets.vue", {p for p, _ in _CAPABILITY_OWNED_PAGES})
        raw = '<template>\n  <el-table-column prop="qty" label="数量" width="80" />\n</template>\n'
        self.assertEqual(render_guard_findings({"frontend/src/views/user/MyOrders.vue": raw}), [])
        self.assertTrue(render_guard_findings({"frontend/src/views/user/SomeGeneric.vue": raw}))

    def test_no_unfilled_slot_tokens_in_domain_defaults(self):
        """占位符必须全部落值：皮里写错槽位名（如 {archive_plural}）会漏出去。"""
        from app.bake.schema.templates import SCHEMA_BUILDERS
        from app.bake.ticket_copy_text import page_copy_texts

        for domain, builder in SCHEMA_BUILDERS.items():
            schema = builder("测试课题")
            for text in page_copy_texts(
                [
                    schema.get("labels") or {},
                    schema.get("portalBanners") or [],
                    schema.get("menus") or {},
                ]
            ):
                self.assertNotIn("{", text, f"{domain} 有未替换的槽位占位符：{text}")

    def test_lexicon_findings_clean_on_domain_defaults(self):
        from app.bake.schema.templates import SCHEMA_BUILDERS

        for domain in ("DOM-CRM", "DOM-EVENT", "DOM-LIBRARY", "DOM-PARCEL", "DOM-SHOP"):
            schema = SCHEMA_BUILDERS[domain]("测试课题")
            self.assertEqual(
                lexicon_findings(schema, domain=domain, title="测试课题"), [], domain
            )


if __name__ == "__main__":
    unittest.main()
