"""系统活动图：3 张、三泳道、四符号、条件在菱形外、与序列同源。"""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

from app.bake.schema.activity import (
    ACTIVITY_COUNT,
    activity_model,
    audit_activity_edges,
    audit_activity_labels,
    audit_activity_nodes,
    render_activity_svg,
)
from app.bake.schema.sequence import (
    default_sequence_selection,
    list_sequence_candidates,
    sequence_model,
)


class ActivityDiagramTests(unittest.TestCase):
    def _schema(self, stem: str) -> dict:
        path = Path(__file__).resolve().parents[0] / "golden" / "schema" / f"{stem}.json"
        return json.loads(path.read_text(encoding="utf-8"))

    def test_exactly_three_diagrams(self) -> None:
        model = activity_model(self._schema("DOM-SHOP"))
        self.assertEqual(len(model["diagrams"]), ACTIVITY_COUNT)
        self.assertEqual(len(model["selected"]), ACTIVITY_COUNT)

    def test_same_default_ids_as_sequence(self) -> None:
        schema = self._schema("DOM-SHOP")
        cands = list_sequence_candidates(schema)
        seq_ids = default_sequence_selection(cands)
        act = activity_model(schema)
        self.assertEqual(act["selected"], seq_ids)
        seq = sequence_model(schema)
        self.assertEqual(act["selected"], seq["selected"])

    def test_three_swimlanes_user_controller_db(self) -> None:
        model = activity_model(self._schema("DOM-SHOP"))
        d0 = model["diagrams"][0]
        lanes = [s["id"] for s in d0["swimlanes"]]
        self.assertEqual(lanes, ["user", "system", "db"])
        labs = [s["label"] for s in d0["swimlanes"]]
        # 与序列图四槽位同名：角色 / 页面 / 控制器 / 数据库
        self.assertEqual(labs, ["用户", "控制器", "数据库"])
        svg = render_activity_svg(d0)
        self.assertIn(">用户<", svg)
        self.assertIn(">控制器<", svg)
        self.assertIn(">数据库<", svg)
        self.assertNotIn(">页面<", svg)
        self.assertNotIn(">系统<", svg)

    def test_symbols_start_action_decision_end(self) -> None:
        model = activity_model(self._schema("DOM-SHOP"))
        d = next(
            (x for x in model["diagrams"] if any(n.get("kind") == "decision" for n in x["nodes"])),
            model["diagrams"][0],
        )
        kinds = {n["kind"] for n in d["nodes"]}
        self.assertIn("start", kinds)
        self.assertIn("end", kinds)
        self.assertIn("action", kinds)
        starts = [n for n in d["nodes"] if n["kind"] == "start"]
        ends = [n for n in d["nodes"] if n["kind"] == "end"]
        self.assertEqual(len(starts), 1)
        self.assertEqual(len(ends), 1)
        self.assertEqual(starts[0]["lane"], "user")
        self.assertEqual(ends[0]["lane"], "user")

    def test_decision_text_on_incoming_edge_not_inside(self) -> None:
        model = activity_model(self._schema("DOM-SHOP"))
        found = False
        for d in model["diagrams"]:
            decisions = [n for n in d["nodes"] if n["kind"] == "decision"]
            for dec in decisions:
                self.assertEqual(dec.get("text") or "", "")
                self.assertTrue(dec.get("decision_of"), msg=str(dec))
                found = True
            guards = [e.get("guard") for e in d["edges"] if e.get("guard")]
            if decisions:
                self.assertTrue(any(g in ("是", "否") for g in guards), msg=str(guards))
        self.assertTrue(found, "至少一张图应含判断菱形")
        d0 = next(x for x in model["diagrams"] if any(n.get("kind") == "decision" for n in x["nodes"]))
        svg = render_activity_svg(d0)
        self.assertIn("L ", svg)  # diamond path
        # 判断语义标在入边旁（框外）；是/否在出边
        self.assertTrue(
            "用户是否存在" in svg or "信息是否存在" in svg,
            msg=svg[:800],
        )
        self.assertIn(">是<", svg)
        self.assertIn(">否<", svg)
        self.assertNotIn(" C ", svg)
        self.assertIn("<polyline", svg)

    def test_favorites_not_leak_archive_entity(self) -> None:
        """收藏图不得串成影片/点播/文章等 archive 词。"""
        from app.bake.schema.sequence import candidate_id, list_sequence_candidates

        for stem in ("DOM-MEDIA", "DOM-MUSIC", "DOM-BLOG"):
            schema = self._schema(stem)
            archive = str(((schema.get("entities") or {}).get("archive") or {}).get("label") or "")
            cands = list_sequence_candidates(schema)
            fav = next((c for c in cands if c.get("kind") == "favorites"), None)
            if not fav:
                continue
            # 凑满 3 个：favorites + 另外两个
            others = [c["id"] for c in cands if c["id"] != fav["id"]][:2]
            if len(others) < 2:
                continue
            model = activity_model(schema, selection=[fav["id"], *others])
            d = next(x for x in model["diagrams"] if x["kind"] == "favorites")
            texts = [n.get("text") or "" for n in d["nodes"] if n["kind"] == "action"]
            blob = " ".join(texts)
            self.assertIn("收藏", blob, msg=f"{stem}: {texts}")
            if archive:
                self.assertNotIn(archive, blob, msg=f"{stem} leaked {archive}: {texts}")
            self.assertNotIn("点播", blob, msg=texts)
            decisions = [n.get("decision_of") for n in d["nodes"] if n["kind"] == "decision"]
            self.assertNotIn("信息是否存在", decisions, msg=f"{stem} browse should not loop")

    def test_ticket_uses_ticket_entity_not_archive(self) -> None:
        schema = self._schema("DOM-ACTIVITY")
        ticket = str(((schema.get("entities") or {}).get("ticket") or {}).get("label") or "")
        archive = str(((schema.get("entities") or {}).get("archive") or {}).get("label") or "")
        self.assertTrue(ticket)
        self.assertTrue(archive)
        from app.bake.schema.sequence import list_sequence_candidates

        cands = list_sequence_candidates(schema)
        mt = next(c for c in cands if c.get("kind") == "my_tickets")
        others = [c["id"] for c in cands if c["id"] != mt["id"]][:2]
        model = activity_model(schema, selection=[mt["id"], *others])
        d = next(x for x in model["diagrams"] if x["kind"] == "my_tickets")
        db_texts = [n.get("text") or "" for n in d["nodes"] if n["kind"] == "action" and n["lane"] == "db"]
        # 业务库操作应贴近单据实体，不应「保存活动信息」冒充报名单
        biz_db = [t for t in db_texts if "登录" not in t and "报名者" not in t and "用户" not in t]
        self.assertTrue(any(ticket in t for t in biz_db), msg=db_texts)
        self.assertFalse(any(t == f"保存{archive}信息" for t in biz_db), msg=db_texts)

    def test_browse_kinds_skip_info_exists(self) -> None:
        schema = self._schema("DOM-SHOP")
        from app.bake.schema.sequence import list_sequence_candidates

        cands = list_sequence_candidates(schema)
        # SHOP 默认有 cart；强制带上 archive_user 测浏览
        au = next((c for c in cands if c.get("kind") == "archive_user"), None)
        if not au:
            return
        others = [c["id"] for c in cands if c["id"] != au["id"]][:2]
        model = activity_model(schema, selection=[au["id"], *others])
        d = next(x for x in model["diagrams"] if x["kind"] == "archive_user")
        decisions = [n.get("decision_of") for n in d["nodes"] if n["kind"] == "decision"]
        self.assertNotIn("信息是否存在", decisions)
        self.assertIn("用户是否存在", decisions)

    def test_golden_smoke_no_favorites_archive_leak(self) -> None:
        """全量 golden：凡 favorites 图，action 不得含该域 archive.label。"""
        root = Path(__file__).resolve().parents[0] / "golden" / "schema"
        from app.bake.schema.sequence import list_sequence_candidates

        for path in sorted(root.glob("DOM-*.json")):
            schema = json.loads(path.read_text(encoding="utf-8"))
            archive = str(((schema.get("entities") or {}).get("archive") or {}).get("label") or "")
            if not archive:
                continue
            cands = list_sequence_candidates(schema)
            fav = next((c for c in cands if c.get("kind") == "favorites"), None)
            if not fav:
                continue
            others = [c["id"] for c in cands if c["id"] != fav["id"]][:2]
            if len(others) < 2:
                continue
            model = activity_model(schema, selection=[fav["id"], *others])
            d = next(x for x in model["diagrams"] if x["kind"] == "favorites")
            for n in d["nodes"]:
                if n["kind"] != "action":
                    continue
                t = n.get("text") or ""
                self.assertNotIn(archive, t, msg=f"{path.stem}: {t}")

    def test_no_sequence_artifacts(self) -> None:
        model = activity_model(self._schema("DOM-SHOP"))
        d0 = model["diagrams"][0]
        svg = render_activity_svg(d0)
        self.assertNotIn("stroke-dasharray", svg)  # 无生命线
        self.assertNotIn("seq-solid", svg)
        blob = json.dumps(d0, ensure_ascii=False)
        self.assertNotIn('"participants"', blob)

    def test_no_example_study_room(self) -> None:
        model = activity_model(self._schema("DOM-SHOP"))
        blob = json.dumps(model, ensure_ascii=False)
        self.assertNotIn("自习室", blob)
        for d in model["diagrams"]:
            self.assertNotIn("自习室", render_activity_svg(d))

    def test_action_texts_are_chinese_verbs(self) -> None:
        model = activity_model(self._schema("DOM-SHOP"))
        for d in model["diagrams"]:
            for n in d["nodes"]:
                if n["kind"] != "action":
                    continue
                t = n.get("text") or ""
                self.assertTrue(t, msg=str(n))
                self.assertFalse(re.search(r"[A-Za-z]{2,}", t), msg=t)

    def test_lanes_only_allowed(self) -> None:
        model = activity_model(self._schema("DOM-SHOP"))
        allowed = {"user", "system", "db"}
        for d in model["diagrams"]:
            for n in d["nodes"]:
                self.assertIn(n["lane"], allowed)

    def test_selection_must_be_three(self) -> None:
        schema = self._schema("DOM-SHOP")
        cands = list_sequence_candidates(schema)
        with self.assertRaises(ValueError):
            activity_model(schema, selection=[cands[0]["id"]])


class ActivityLabelGeometryTests(unittest.TestCase):
    """是/否 与判断条件必须贴菱形、不压线、不出泳道；折线不得穿节点。"""

    def _schema(self, stem: str) -> dict:
        path = Path(__file__).resolve().parents[0] / "golden" / "schema" / f"{stem}.json"
        return json.loads(path.read_text(encoding="utf-8"))

    def _all_diagrams(self) -> list[tuple[str, dict]]:
        root = Path(__file__).resolve().parents[0] / "golden" / "schema"
        out: list[tuple[str, dict]] = []
        for path in sorted(root.glob("DOM-*.json")):
            schema = json.loads(path.read_text(encoding="utf-8"))
            for idx, d in enumerate(activity_model(schema)["diagrams"]):
                out.append((f"{path.stem}[{idx}]", d))
        return out

    def test_all_golden_diagrams_have_clean_labels(self) -> None:
        diagrams = self._all_diagrams()
        self.assertGreater(len(diagrams), 3)
        for tag, d in diagrams:
            svg = render_activity_svg(d)
            findings = audit_activity_labels(svg)
            self.assertEqual(findings, [], msg=f"{tag}: {findings[:4]}")

    def test_all_golden_diagrams_have_clean_edges(self) -> None:
        for tag, d in self._all_diagrams():
            findings = audit_activity_edges(render_activity_svg(d))
            self.assertEqual(findings, [], msg=f"{tag}: {findings[:4]}")

    def test_all_golden_diagrams_have_nodes_inside_lanes(self) -> None:
        for tag, d in self._all_diagrams():
            findings = audit_activity_nodes(render_activity_svg(d))
            self.assertEqual(findings, [], msg=f"{tag}: {findings[:4]}")

    def test_guard_label_hugs_its_decision(self) -> None:
        """老毛病：是/否 写在整条边长中点，离菱形几十上百像素。"""
        d = activity_model(self._schema("DOM-SHOP"))["diagrams"][0]
        svg = render_activity_svg(d)
        centres = [(float(mx), float(my) + 14.0) for mx, my in re.findall(
            r'<path d="M ([-\d.]+) ([-\d.]+) L', svg
        )]
        self.assertTrue(centres)
        labels = [
            (float(mx), float(my), raw)
            for mx, my, raw in re.findall(
                r'<text x="([-\d.]+)" y="([-\d.]+)"(?: text-anchor="[a-z]+")?'
                r' font-family="[^"]*" font-size="[\d.]+" fill="#000">(是|否)</text>',
                svg,
            )
        ]
        self.assertEqual(len(labels), 4, msg=labels)
        for lx, ly, text in labels:
            near = min(((lx - cx) ** 2 + (ly - cy) ** 2) ** 0.5 for cx, cy in centres)
            self.assertLessEqual(near, 48.0, msg=f"{text} 离最近菱形 {near:.0f}px")

    def test_audit_catches_label_on_line(self) -> None:
        """门禁自身要有牙齿：文字压线必须报出来。"""
        svg = (
            '<svg xmlns="http://www.w3.org/2000/svg">'
            '<polyline points="300,300 100,300" fill="none" stroke="#000"/>'
            '<text x="200" y="297" font-family="x" font-size="11" fill="#000">用户是否存在</text>'
            "</svg>"
        )
        self.assertTrue(audit_activity_labels(svg))

    def test_audit_catches_line_through_node(self) -> None:
        svg = (
            '<svg xmlns="http://www.w3.org/2000/svg">'
            '<polyline points="300,134 62,134" fill="none" stroke="#000"/>'
            '<rect x="62" y="116" width="132" height="36" rx="10" fill="#fff" stroke="#000"/>'
            "</svg>"
        )
        self.assertTrue(audit_activity_edges(svg))

    def test_long_action_widens_box_and_lane(self) -> None:
        """P4：长文案把任务框和三条泳道一起撑开，不缩字、不压分隔线。"""
        from app.bake.schema.activity import _SWIMLANES, _lane_boxes, _node_boxes

        diag = {
            "figure_title": "长文案活动图",
            "swimlanes": [dict(s) for s in _SWIMLANES],
            "nodes": [
                {"id": "s", "kind": "start", "lane": "user", "text": ""},
                {
                    "id": "a",
                    "kind": "action",
                    "lane": "user",
                    "text": "核对预约时段与可选服务项目清单",
                },
                {
                    "id": "d",
                    "kind": "decision",
                    "lane": "system",
                    "text": "",
                    "decision_of": "时段是否冲突",
                },
                {"id": "e", "kind": "end", "lane": "user", "text": ""},
            ],
            "edges": [
                {"from": "s", "to": "a"},
                {"from": "a", "to": "d"},
                {"from": "d", "to": "e", "guard": "是"},
            ],
        }
        svg = render_activity_svg(diag)
        self.assertEqual(audit_activity_labels(svg), [])
        self.assertEqual(audit_activity_edges(svg), [])
        lanes = _lane_boxes(svg)
        self.assertEqual(len(lanes), 3)
        lane_w = lanes[0][2]
        self.assertGreater(lane_w, 200.0)
        for x0, _y0, x1, _y1 in _node_boxes(svg):
            self.assertGreaterEqual(x0, lanes[0][0])
            self.assertLessEqual(x1, lanes[0][0] + lane_w)
        # 框宽已撑开 → 任务框字号统一 11，不再靠 12/10 缩字
        self.assertNotIn('font-size="12.0"', svg)
        self.assertNotIn('font-size="10.0"', svg)

    def test_rubric_surfaces_geometry_findings(self) -> None:
        """门禁要接得出：rubric 里能看到「标签压线」而不是静默出图。"""
        from app.bake.schema.diagram_rubric import audit_activity_rubric

        model = activity_model(self._schema("DOM-SHOP"))
        bad = (
            '<svg xmlns="http://www.w3.org/2000/svg">'
            '<polyline points="300,300 100,300" fill="none" stroke="#000"/>'
            '<text x="200" y="297" font-family="x" font-size="11" fill="#000">用户是否存在</text>'
            "</svg>"
        )
        model["diagrams"] = [dict(model["diagrams"][0], svg=bad)]
        findings = audit_activity_rubric(model)
        self.assertTrue(
            any("标签压线" in f.get("msg", "") for f in findings), msg=findings
        )

        good = render_activity_svg(activity_model(self._schema("DOM-SHOP"))["diagrams"][0])
        model["diagrams"] = [dict(model["diagrams"][0], svg=good)]
        findings = audit_activity_rubric(model)
        self.assertFalse(
            [f for f in findings if "压线" in f.get("msg", "") or "穿框" in f.get("msg", "")],
            msg=findings,
        )


if __name__ == "__main__":
    unittest.main()
