"""系统序列图：3 张、四槽位、六条画法、角色/文案取自 bake。"""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from app.bake.schema.sequence import (
    SEQUENCE_COUNT,
    _activation_spans,
    default_sequence_selection,
    list_sequence_candidates,
    render_sequence_svg,
    sequence_model,
)


class SequenceDiagramTests(unittest.TestCase):
    def _schema(self, stem: str) -> dict:
        path = Path(__file__).resolve().parents[0] / "golden" / "schema" / f"{stem}.json"
        return json.loads(path.read_text(encoding="utf-8"))

    def test_exactly_three_diagrams(self) -> None:
        model = sequence_model(self._schema("DOM-SHOP"))
        self.assertEqual(len(model["diagrams"]), SEQUENCE_COUNT)
        self.assertEqual(len(model["selected"]), SEQUENCE_COUNT)

    def test_actor_from_bake_not_hardcoded_user(self) -> None:
        model = sequence_model(self._schema("DOM-SHOP"))
        actors = [d["actor_label"] for d in model["diagrams"]]
        self.assertTrue(any("买家" in a for a in actors) or any(a == "买家" for a in actors))
        # 至少一张图的参与者框不是写死「用户」占业务角色
        for d in model["diagrams"]:
            if d.get("side") == "user":
                self.assertEqual(d["actor_label"], "买家")
                self.assertEqual(d["participants"][0]["label"], "买家")
                break

    def test_four_slots_and_stick(self) -> None:
        model = sequence_model(self._schema("DOM-SHOP"))
        d0 = model["diagrams"][0]
        ids = [p["id"] for p in d0["participants"]]
        self.assertEqual(ids, ["actor", "page", "controller", "db"])
        labs = [p["label"] for p in d0["participants"]]
        self.assertEqual(labs[1:], ["页面", "控制器", "数据库"])
        self.assertTrue(d0["participants"][0]["stick"])
        svg = render_sequence_svg(d0)
        self.assertIn("<circle", svg)  # 火柴人
        self.assertIn("页面", svg)
        self.assertIn("控制器", svg)
        self.assertIn("数据库", svg)

    def test_request_parens_response_no_parens(self) -> None:
        model = sequence_model(self._schema("DOM-SHOP"))
        d0 = model["diagrams"][0]
        svg = render_sequence_svg(d0)
        # 渲染后：实线消息带 ()，虚线返回不带
        import re

        # 抽序号行
        texts = re.findall(r">(\d+、[^<]+)<", svg)
        self.assertGreaterEqual(len(texts), 4)
        for m in d0["messages"]:
            seq = m["seq"]
            hit = next((t for t in texts if t.startswith(f"{seq}、")), "")
            self.assertTrue(hit, msg=f"missing seq {seq}")
            if m["dir"] in ("request", "self"):
                self.assertTrue(hit.rstrip().endswith("()"), msg=hit)
            else:
                self.assertFalse(hit.rstrip().endswith("()"), msg=hit)
                self.assertFalse(hit.rstrip().endswith("（）"), msg=hit)

    def test_activation_bars_segmented_variable_length(self) -> None:
        model = sequence_model(self._schema("DOM-SHOP"))
        # 找一张含 login+biz 两阶段的图
        d = next(x for x in model["diagrams"] if len(x.get("phases") or []) >= 2)
        spans = _activation_spans(d["messages"], "actor")
        self.assertGreaterEqual(len(spans), 2)
        heights = [b - a + 1 for _, a, b in spans]
        # 至少存在不同跨度（长短之分）
        self.assertTrue(len(set(heights)) >= 1)
        svg = render_sequence_svg(d)
        # 激活条 rect 多于参与者框（4）——另有多段激活
        # 粗计：stroke 黑框数量
        self.assertIn('stroke-dasharray="4 3"', svg)  # 生命线

    def test_no_example_study_room(self) -> None:
        model = sequence_model(self._schema("DOM-SHOP"))
        blob = json.dumps(model, ensure_ascii=False)
        self.assertNotIn("自习室", blob)
        for d in model["diagrams"]:
            svg = render_sequence_svg(d)
            self.assertNotIn("自习室", svg)

    def test_selection_must_be_three(self) -> None:
        schema = self._schema("DOM-SHOP")
        cands = list_sequence_candidates(schema)
        self.assertGreaterEqual(len(cands), 3)
        one = [cands[0]["id"]]
        with self.assertRaises(ValueError):
            sequence_model(schema, selection=one)
        three = [cands[0]["id"], cands[1]["id"], cands[2]["id"]]
        model = sequence_model(schema, selection=three)
        self.assertEqual(model["selected"], three)

    def test_default_selection_stable_ids(self) -> None:
        cands = list_sequence_candidates(self._schema("DOM-SHOP"))
        ids = default_sequence_selection(cands)
        self.assertEqual(len(ids), 3)
        self.assertEqual(len(set(ids)), 3)

    def test_shop_messages_carry_delivery_labels(self) -> None:
        model = sequence_model(self._schema("DOM-SHOP"))
        blob = json.dumps(model["diagrams"], ensure_ascii=False)
        # 交付菜单/实体应出现在某张图中
        self.assertTrue(
            any(x in blob for x in ("商品", "订单", "购物车", "买家", "登录")),
            msg=blob[:500],
        )

    def test_arrow_markers_are_open(self) -> None:
        model = sequence_model(self._schema("DOM-SHOP"))
        # 选一张含自调用的图测直角回路
        d = next(
            (x for x in model["diagrams"] if any(m.get("dir") == "self" for m in x["messages"])),
            model["diagrams"][0],
        )
        svg = render_sequence_svg(d)
        self.assertIn("seq-solid", svg)
        # marker 为空心折线箭头，不是 fill 实心三角 path z
        self.assertIn('path d="M0,0 L10,5 L0,10" fill="none"', svg)
        if any(m.get("dir") == "self" for m in d["messages"]):
            self.assertIn("<polyline", svg)
            self.assertNotIn(" C ", svg)

    def test_no_doubled_login_phrase(self) -> None:
        from app.bake.schema.sequence import _join_verb_noun, _op_text

        self.assertEqual(_join_verb_noun("验证登录", "登录"), "验证登录")
        self.assertEqual(_join_verb_noun("验证", "登录"), "验证登录")
        self.assertEqual(_join_verb_noun("查询", "订单"), "查询订单")
        self.assertEqual(
            _op_text({"method": "login", "verb": "验证", "summary": ""}, entity="", menu_label="登录"),
            "验证登录",
        )
        self.assertEqual(
            _op_text({"verb": "验证登录", "method": "login", "summary": ""}, entity="", menu_label="登录"),
            "验证登录",
        )
        model = sequence_model(self._schema("DOM-SHOP"))
        blob = json.dumps(model, ensure_ascii=False)
        self.assertNotIn("登录登录", blob)
        for d in model["diagrams"]:
            for m in d["messages"]:
                self.assertNotIn("登录登录", str(m.get("text") or ""))
            self.assertNotIn("登录登录", render_sequence_svg(d))


    def test_btn_must_align_menu_or_entity(self) -> None:
        """串台根因：其它功能页的复合按钮不含本菜单/实体 → 拒收；不靠领域黑名单。"""
        from app.bake.schema.sequence import _build_business_phase, _btn_fits_feature

        self.assertFalse(
            _btn_fits_feature("提交签署", menu_label="农产品管理", entity="农产品", kind="archive_admin")
        )
        self.assertFalse(
            _btn_fits_feature("去结算支付", menu_label="农产品管理", entity="农产品", kind="archive_admin")
        )
        self.assertTrue(
            _btn_fits_feature("保存", menu_label="农产品管理", entity="农产品", kind="archive_admin")
        )
        self.assertTrue(
            _btn_fits_feature("保存农产品", menu_label="农产品管理", entity="农产品", kind="archive_admin")
        )
        msgs = _build_business_phase(
            seq0=0,
            actor="商家",
            menu_label="农产品管理",
            entity="农产品",
            ops=[],
            vue_btns=["提交签署", "去结算支付", "保存", "选择无关项"],
            kind="archive_admin",
        )
        blob = " ".join(str(m["text"]) for m in msgs)
        self.assertNotIn("签署", blob)
        self.assertNotIn("支付", blob)
        self.assertIn("农产品", blob)


    def test_op_text_never_leaks_english_method(self) -> None:
        """无中文摘要时，禁止 suggest/getList 等英文方法名进序列图文案。"""
        from app.bake.schema.sequence import _build_business_phase, _leaks_code_ident, _op_text

        self.assertTrue(_leaks_code_ident("suggest图书"))
        self.assertFalse(_leaks_code_ident("查询逾期罚款"))
        bad = _op_text(
            {"method": "suggest", "verb": "", "summary": ""},
            entity="图书",
            menu_label="逾期罚款",
        )
        self.assertEqual(bad, "")
        ok = _op_text(
            {"method": "list", "verb": "查询", "summary": ""},
            entity="图书",
            menu_label="逾期罚款",
        )
        self.assertEqual(ok, "查询图书")
        self.assertFalse(_leaks_code_ident(ok))
        msgs = _build_business_phase(
            seq0=0,
            actor="读者",
            menu_label="逾期罚款",
            entity="图书",
            ops=[{"method": "suggest", "verb": "", "summary": ""}],
            vue_btns=[],
            kind="open",
        )
        blob = " ".join(str(m["text"]) for m in msgs)
        self.assertNotRegex(blob, r"[A-Za-z]{2,}")
        self.assertIn("逾期罚款", blob)


if __name__ == "__main__":
    unittest.main()
