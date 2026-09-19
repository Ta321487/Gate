"""系统活动图：3 张、三泳道、四符号、条件在菱形外、与序列同源。"""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

from app.bake.schema.activity import (
    ACTIVITY_COUNT,
    activity_model,
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

    def test_three_swimlanes_user_system_db(self) -> None:
        model = activity_model(self._schema("DOM-SHOP"))
        d0 = model["diagrams"][0]
        lanes = [s["id"] for s in d0["swimlanes"]]
        self.assertEqual(lanes, ["user", "system", "db"])
        labs = [s["label"] for s in d0["swimlanes"]]
        self.assertEqual(labs, ["用户", "系统", "数据库"])
        svg = render_activity_svg(d0)
        self.assertIn(">用户<", svg)
        self.assertIn(">系统<", svg)
        self.assertIn(">数据库<", svg)
        self.assertNotIn(">页面<", svg)
        self.assertNotIn(">控制器<", svg)

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


if __name__ == "__main__":
    unittest.main()
