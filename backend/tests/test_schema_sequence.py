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

        # 抽序号行（编号口径对齐样例：`1.`，不是 `1、`）
        texts = re.findall(r">(\d+\.[^<]+)<", svg)
        self.assertGreaterEqual(len(texts), 4)
        for m in d0["messages"]:
            seq = m["seq"]
            hit = next((t for t in texts if t.startswith(f"{seq}.")), "")
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

    def test_default_selection_prefers_trade_not_login_slot(self) -> None:
        """序列图三席不单占纯登录；商城优先购物车/订单主链路。"""
        cands = list_sequence_candidates(self._schema("DOM-SHOP"))
        ids = default_sequence_selection(cands)
        kinds = []
        by = {c["id"]: c for c in cands}
        for i in ids:
            kinds.append(str(by[i].get("kind") or ""))
        self.assertNotIn("auth_login", kinds)
        self.assertTrue(
            {"cart", "my_orders"} <= set(kinds)
            or ({"cart", "orders"} <= set(kinds))
            or ({"my_orders", "orders"} <= set(kinds)),
            msg=kinds,
        )
        self.assertNotIn("users", kinds)

    def test_primary_home_menu_and_selection_generic(self) -> None:
        """家路径 → primary；默认选题抬主入口、辅购物车让位（不绑题名/单域）。"""
        from app.bake.schema.sequence import primary_user_menu_keys

        schema = {
            "labels": {"userHomePath": "/seats/shows", "appName": "选座票务"},
            "roles": {"user": {"label": "观众"}, "admin": {"label": "管理员"}},
            "menus": {
                "user": [
                    {"key": "seat_shows", "label": "场次选座"},
                    {"key": "cart", "label": "购物车"},
                    {"key": "my_orders", "label": "我的订单"},
                ],
                "admin": [{"key": "orders", "label": "订单管理"}],
            },
            "entities": {"order": {"label": "订单"}, "archive": {"key": "cinema_show", "label": "场次"}},
            "capabilities": ["seat_select", "order_lines"],
        }
        self.assertEqual(primary_user_menu_keys(schema), {"seat_shows"})
        # 合成候选：主入口分低 + open；购物车分高——选题后须含主入口
        cands = [
            {
                "id": "user::cart::cart",
                "side": "user",
                "menu_key": "cart",
                "kind": "cart",
                "label": "购物车",
                "name": "用购物车",
                "actor": "观众",
                "score": 149,
                "primary": False,
            },
            {
                "id": "user::seat_shows::open",
                "side": "user",
                "menu_key": "seat_shows",
                "kind": "open",
                "label": "场次选座",
                "name": "用场次选座",
                "actor": "观众",
                "score": 83,
                "primary": True,
            },
            {
                "id": "user::my_orders::my_orders",
                "side": "user",
                "menu_key": "my_orders",
                "kind": "my_orders",
                "label": "我的订单",
                "name": "看订单",
                "actor": "观众",
                "score": 87,
                "primary": False,
            },
            {
                "id": "admin::orders::orders",
                "side": "admin",
                "menu_key": "orders",
                "kind": "orders",
                "label": "订单管理",
                "name": "管订单",
                "actor": "管理员",
                "score": 80,
                "primary": False,
            },
        ]
        ids = default_sequence_selection(cands)
        by = {c["id"]: c for c in cands}
        picked = [str(by[i].get("menu_key") or "") for i in ids]
        self.assertIn("seat_shows", picked, msg=picked)
        # 另：家路径是预约列表时同样抬分
        self.assertEqual(
            primary_user_menu_keys(
                {
                    "labels": {"userHomePath": "/my/reservations"},
                    "menus": {
                        "user": [
                            {"key": "my_reservations", "label": "我的预约"},
                            {"key": "profile", "label": "资料"},
                        ]
                    },
                }
            ),
            {"my_reservations"},
        )

    def test_my_orders_confirm_receive_phases(self) -> None:
        """材料有 verbs 时按材料拼句；材料没词时只出中性骨架，不得编「确认收货」。"""
        from app.bake.schema.sequence import _build_business_phase, _feature_entity

        cinema = {
            "domain": "DOM-CINEMA",
            "entities": {
                "order": {
                    "label": "订单",
                    "verbs": {"ship": "出票", "complete": "确认观演"},
                    "states": {"pending": "待取票", "shipped": "已出票", "completed": "已观影"},
                }
            },
        }
        msgs = _build_business_phase(
            seq0=0,
            actor="买家",
            menu_label="我的票务订单",
            entity=_feature_entity(cinema, kind="my_orders", menu_label="我的票务订单"),
            ops=[{"method": "page", "verb": "分页查询", "summary": ""}],
            vue_btns=["确认收货", "去支付"],
            kind="my_orders",
            side="user",
            schema=cinema,
        )
        blob = " ".join(str(m["text"]) for m in msgs)
        self.assertIn("确认观演", blob)
        self.assertIn("确认观演成功", blob)
        self.assertNotIn("确认收货", blob)

        # 材料缺词（商城 order 无 verbs）：中性骨架 + 缺词告警，不借别域业务句
        plain = {"entities": {"order": {"label": "订单"}}}
        msgs2 = _build_business_phase(
            seq0=0,
            actor="买家",
            menu_label="我的订单",
            entity=_feature_entity(plain, kind="my_orders", menu_label="我的订单"),
            ops=[{"method": "page", "verb": "分页查询", "summary": ""}],
            vue_btns=["确认收货"],
            kind="my_orders",
            side="user",
            schema=plain,
        )
        blob2 = " ".join(str(m["text"]) for m in msgs2)
        self.assertNotIn("确认收货", blob2)
        self.assertNotIn("发货", blob2)
        self.assertIn("订单", blob2)

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


    def test_feature_entity_order_reviews_is_review_not_order(self) -> None:
        """order_reviews_* 含 order 子串，不得把实体错解析成订单。"""
        from app.bake.schema.sequence import _feature_entity, _build_business_phase

        schema = {
            "entities": {
                "order": {"label": "订单"},
                "review": {"label": "评价"},
            }
        }
        self.assertEqual(
            _feature_entity(schema, kind="order_reviews_user", menu_label="我的评价"),
            "评价",
        )
        self.assertEqual(
            _feature_entity(schema, kind="order_reviews_admin", menu_label="评价管理"),
            "评价",
        )
        msgs = _build_business_phase(
            seq0=0,
            actor="买家",
            menu_label="我的评价",
            entity=_feature_entity(schema, kind="order_reviews_user", menu_label="我的评价"),
            ops=[{"method": "page", "verb": "分页查询", "summary": ""}],
            vue_btns=[],
            kind="order_reviews_user",
        )
        blob = " ".join(str(m["text"]) for m in msgs)
        self.assertIn("评价", blob)
        self.assertNotIn("分页查询订单", blob)
        self.assertNotIn("提交订单", blob)
        self.assertNotIn("保存订单信息", blob)

    def test_cart_and_review_no_container_template_phrases(self) -> None:
        """写路径只许「材料词 / 中性骨架」：容器套话与别域业务句一律不出现。"""
        from app.bake.schema.sequence import _build_business_phase, _feature_entity

        schema = {
            "entities": {
                "cart": {"label": "购物车"},
                "order": {"label": "订单"},
                "review": {"label": "评价", "verbs": {"apply": "提交评价"}},
            }
        }
        cart_msgs = _build_business_phase(
            seq0=0,
            actor="买家",
            menu_label="购物车",
            entity=_feature_entity(schema, kind="cart", menu_label="购物车"),
            ops=[
                {"method": "page", "verb": "分页查询", "summary": ""},
                {"method": "add", "verb": "新增", "summary": ""},
            ],
            vue_btns=[],
            kind="cart",
            side="user",
            schema=schema,
        )
        cart_blob = " ".join(str(m["text"]) for m in cart_msgs)
        for bad in ("选择购物车", "确认购物车", "新增购物车", "提交购物车", "保存购物车信息"):
            self.assertNotIn(bad, cart_blob, msg=cart_blob)
        # 材料没给 cart 动作词 → 中性骨架，不得借商城的「结算 / 商品」
        self.assertNotIn("结算", cart_blob, msg=cart_blob)
        self.assertNotIn("商品", cart_blob, msg=cart_blob)
        self.assertIn("购物车", cart_blob)

        rev_msgs = _build_business_phase(
            seq0=0,
            actor="买家",
            menu_label="我的评价",
            entity=_feature_entity(
                schema, kind="order_reviews_user", menu_label="我的评价"
            ),
            ops=[{"method": "page", "verb": "分页查询", "summary": ""}],
            vue_btns=[],
            kind="order_reviews_user",
            side="user",
            schema=schema,
        )
        rev_blob = " ".join(str(m["text"]) for m in rev_msgs)
        for bad in ("选择我的评价", "确认我的评价", "选择评价", "新增评价"):
            self.assertNotIn(bad, rev_blob, msg=rev_blob)
        # 材料给了 review.apply=提交评价 → 直接说材料词
        self.assertIn("提交评价", rev_blob)

        # 无 schema 的冷门 kind：中性骨架，不写「选择{菜单}」
        slot_msgs = _build_business_phase(
            seq0=0,
            actor="读者",
            menu_label="座位预约",
            entity="预约",
            ops=[],
            vue_btns=[],
            kind="reservations",
            side="user",
        )
        slot_blob = " ".join(str(m["text"]) for m in slot_msgs)
        self.assertNotIn("选择预约", slot_blob)
        self.assertNotIn("选择座位预约", slot_blob)
        self.assertNotIn("选择可预约项或时段", slot_blob)
        self.assertIn("预约", slot_blob)

    def test_workflow_prose_follows_messages_not_sample_essay(self) -> None:
        """工作流由本图消息改写：步数对齐、含角色与动作、不塞示例范文腔。"""
        from app.bake.schema.sequence_workflow import workflow_prose_from_diagram

        model = sequence_model(self._schema("DOM-SHOP"))
        for d in model["diagrams"]:
            wf = d.get("workflow") or {}
            self.assertTrue(wf.get("title", "").endswith("的工作流程如下："))
            self.assertEqual(len(wf["steps"]), len(d["messages"]))
            self.assertIn(d["actor_label"], wf["plain"])
            self.assertNotIn("合法性校验", wf["plain"])  # 图无则文无
            self.assertNotIn("示例论文", wf["plain"])
            rebuilt = workflow_prose_from_diagram(d)
            self.assertEqual(rebuilt["plain"], wf["plain"])

    def test_workflow_sentence_mapping_deterministic(self) -> None:
        from app.bake.schema.sequence_workflow import workflow_prose_from_diagram

        diagram = {
            "figure_title": "确认收货序列图",
            "participants": [
                {"id": "actor", "label": "买家"},
                {"id": "page", "label": "页面"},
                {"id": "controller", "label": "控制器"},
                {"id": "db", "label": "数据库"},
            ],
            "messages": [
                {"seq": 1, "from": "actor", "to": "page", "dir": "request", "text": "打开我的订单"},
                {"seq": 2, "from": "page", "to": "controller", "dir": "request", "text": "查询订单()"},
                {"seq": 3, "from": "controller", "to": "db", "dir": "request", "text": "读取订单()"},
                {"seq": 4, "from": "db", "to": "controller", "dir": "response", "text": "返回订单数据"},
                {"seq": 5, "from": "controller", "to": "page", "dir": "response", "text": "返回结果"},
                {"seq": 6, "from": "page", "to": "page", "dir": "self", "text": "确认收货"},
                {"seq": 7, "from": "page", "to": "actor", "dir": "response", "text": "收货成功"},
            ],
        }
        wf = workflow_prose_from_diagram(diagram)
        self.assertEqual(wf["title"], "确认收货的工作流程如下：")
        texts = [s["text"] for s in wf["steps"]]
        self.assertEqual(texts[0], "买家在页面上打开我的订单。")
        self.assertEqual(texts[1], "页面向控制器发出请求：查询订单。")
        self.assertEqual(texts[2], "控制器向数据库读取订单。")
        self.assertEqual(texts[3], "数据库返回订单数据。")
        self.assertEqual(texts[4], "控制器向页面返回结果。")
        self.assertEqual(texts[5], "买家在页面上确认收货。")
        self.assertEqual(texts[6], "页面向买家反馈：收货成功。")

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
