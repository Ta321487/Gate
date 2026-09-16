"""类图：SQL/领域印证 + Java 方法/属性 + 折线 SVG。"""

from __future__ import annotations

import json
import re
import shutil
import tempfile
import unittest
from pathlib import Path

from app.bake.schema.class_code import parse_java_type_members
from app.bake.schema.classes import (
    build_class_model,
    class_model_from_er_tables,
    ortho_path,
    render_class_svg,
    sql_type_to_java,
    table_to_class_name,
)

_REPO = Path(__file__).resolve().parents[2]

_MINI_SQL = """
CREATE TABLE `sys_user` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `username` varchar(64) NOT NULL,
  `password` varchar(128) NOT NULL,
  PRIMARY KEY (`id`)
);
CREATE TABLE `sys_notice` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `title` varchar(120) NOT NULL,
  `content` text,
  `publisher_username` varchar(64) DEFAULT NULL,
  PRIMARY KEY (`id`)
);
CREATE TABLE `book` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `title` varchar(120) NOT NULL,
  `stock` int NOT NULL DEFAULT 0,
  PRIMARY KEY (`id`)
);
CREATE TABLE `borrow` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `username` varchar(64) NOT NULL,
  `book_id` bigint NOT NULL,
  `status` varchar(32) NOT NULL,
  PRIMARY KEY (`id`),
  FOREIGN KEY (`book_id`) REFERENCES `book` (`id`)
);
"""

_DOMAIN = {
    "title": "图书馆管理系统",
    "labels": {"appName": "图书馆"},
    "entities": {
        "archive": {"key": "book", "label": "图书"},
        "ticket": {"key": "borrow", "label": "借阅单"},
    },
}

_NOTICE_JAVA = """
package com.thesis.service;
public class NoticeStore {
    private static Map<String, Object> row(java.sql.ResultSet rs) throws Exception {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("id", rs.getLong("id"));
        m.put("title", rs.getString("title"));
        m.put("content", rs.getString("content"));
        return m;
    }
    public static Map<String, Object> page(int page, int size) { return null; }
    public static Map<String, Object> add(String title, String content) { return null; }
    public static void delete(long id) {}
    private static void ensurePinnedColumn() {}
    private static void wipeCache() {}
}
"""


class ClassDiagramTests(unittest.TestCase):
    def test_sql_type_and_class_name(self) -> None:
        self.assertEqual(sql_type_to_java("varchar(64)"), "String")
        self.assertEqual(table_to_class_name("sys_user"), "User")

    def test_rel_kind_and_method_format(self) -> None:
        from app.bake.schema.classes import (
            _classify_fk_relation_kind,
            _edge_marker_attrs,
            _format_method_display,
            _marker_defs,
            _normalize_rel_kind,
            _sample_attributes,
            _sample_methods,
        )
        from app.bake.schema.class_code import infer_dependency_relations

        self.assertEqual(_normalize_rel_kind("extends"), "inheritance")
        child = {
            "attributes": [
                {"name": "bookId", "column": "book_id", "fk": True, "not_null": True}
            ]
        }
        self.assertEqual(
            _classify_fk_relation_kind("book", "borrow", "book_id", child_cls=child),
            "aggregation",
        )
        self.assertEqual(
            _classify_fk_relation_kind("sys_user", "borrow", "username", child_cls=child),
            "association",
        )
        detail = {
            "attributes": [
                {"name": "orderId", "column": "order_id", "fk": True, "not_null": True}
            ]
        }
        self.assertEqual(
            _classify_fk_relation_kind("order", "order_item", "order_id", child_cls=detail),
            "composition",
        )
        m = _format_method_display(
            {"name": "page", "visibility": "+", "params": "int page, int size", "return": "Map"}
        )
        self.assertEqual(m, "+ page(int, int) : Map")
        empty = _sample_methods([])
        self.assertEqual(empty, [])
        fake = _sample_methods(
            [{"name": "page", "visibility": "+", "params": "", "return": "Map", "source": "java"}]
        )
        self.assertEqual(len(fake), 1)
        self.assertIn("()", fake[0]["display"])
        # 可见性保留：Java field 的 # 不被 sample 抹成 -
        samp_a = _sample_attributes(
            [
                {"name": "id", "type": "Long", "visibility": "-", "source": "java_row"},
                {"name": "role", "type": "String", "visibility": "#", "source": "java_field"},
            ]
        )
        self.assertEqual(samp_a[0]["visibility"], "-")
        self.assertEqual(samp_a[1]["visibility"], "#")
        self.assertTrue(samp_a[1]["display"].startswith("# "))
        defs = _marker_defs()
        for mid in ("uml-open", "uml-tri", "uml-agg", "uml-comp"):
            self.assertIn(f'id="{mid}"', defs)
        dash, _s, end = _edge_marker_attrs("dependency")
        self.assertIn("6 4", dash)
        self.assertIn("uml-open", end)
        # 类型引用 → 依赖；已有聚合则不叠依赖
        model = {
            "classes": [
                {
                    "id": "borrow",
                    "name": "Borrow",
                    "attributes": [],
                    "methods": [
                        {
                            "name": "attach",
                            "params": "Book book",
                            "return": "void",
                            "visibility": "+",
                        },
                        {
                            "name": "notify",
                            "params": "User user",
                            "return": "void",
                            "visibility": "+",
                        },
                    ],
                },
                {"id": "book", "name": "Book", "attributes": [], "methods": []},
                {"id": "user", "name": "User", "attributes": [], "methods": []},
            ],
            "associations": [
                {
                    "from": "book",
                    "to": "borrow",
                    "kind": "aggregation",
                    "from_class": "Book",
                    "to_class": "Borrow",
                }
            ],
        }
        n = infer_dependency_relations(model)
        self.assertEqual(n, 1)
        dep = next(a for a in model["associations"] if a["kind"] == "dependency")
        self.assertEqual(dep["from"], "borrow")
        self.assertEqual(dep["to"], "user")
        self.assertFalse(
            any(
                a.get("kind") == "dependency"
                and {"book", "borrow"} <= {a.get("from"), a.get("to")}
                for a in model["associations"]
            )
        )

    def test_oo_inheritance_implementation_svg(self) -> None:
        """extends/implements 扫描并入模型后，SVG 使用空心三角（uml-tri）。"""
        from app.bake.schema.class_code import (
            merge_oo_relations_into_model,
            scan_java_oo_relations,
        )
        from app.bake.schema.classes import attach_layout

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            java_dir = (
                root
                / "backend"
                / "src"
                / "main"
                / "java"
                / "com"
                / "thesis"
                / "domain"
            )
            java_dir.mkdir(parents=True)
            (java_dir / "User.java").write_text(
                "package com.thesis.domain;\npublic class User {}\n",
                encoding="utf-8",
            )
            (java_dir / "Payable.java").write_text(
                "package com.thesis.domain;\npublic interface Payable {}\n",
                encoding="utf-8",
            )
            (java_dir / "VipUser.java").write_text(
                "package com.thesis.domain;\n"
                "public class VipUser extends User implements Payable {}\n",
                encoding="utf-8",
            )
            oo = scan_java_oo_relations(root)
            kinds = {(r["from_class"], r["to_class"], r["kind"]) for r in oo}
            self.assertIn(("VipUser", "User", "inheritance"), kinds)
            self.assertIn(("VipUser", "Payable", "implementation"), kinds)

            model = {
                "classes": [
                    {
                        "id": "vip_user",
                        "name": "VipUser",
                        "code_class": "VipUser",
                        "attributes": [{"display": "- id: Long"}],
                        "methods": [],
                    },
                    {
                        "id": "sys_user",
                        "name": "User",
                        "code_class": "User",
                        "attributes": [{"display": "- id: Long"}],
                        "methods": [],
                    },
                    {
                        "id": "payable",
                        "name": "Payable",
                        "code_class": "Payable",
                        "attributes": [],
                        "methods": [{"display": "+ pay() : void"}],
                    },
                ],
                "associations": [],
            }
            added = merge_oo_relations_into_model(model, oo)
            self.assertEqual(added, 2)
            by_kind = {a["kind"]: a for a in model["associations"]}
            self.assertEqual(by_kind["inheritance"]["from"], "vip_user")
            self.assertEqual(by_kind["inheritance"]["to"], "sys_user")
            self.assertEqual(by_kind["implementation"]["from"], "vip_user")
            self.assertEqual(by_kind["implementation"]["to"], "payable")

            attach_layout(model)
            svg = render_class_svg(model)
            self.assertIn('data-kind="inheritance"', svg)
            self.assertIn('data-kind="implementation"', svg)
            self.assertIn('marker-end="url(#uml-tri)"', svg)
            self.assertIn('stroke-dasharray="6 4"', svg)
            # 实现为虚线 + 三角；继承为实线 + 三角
            self.assertRegex(
                svg,
                r'data-kind="implementation"[^>]*stroke-dasharray="6 4"',
            )

    def test_parse_java_members_no_fake_crud(self) -> None:
        attrs, methods = parse_java_type_members(_NOTICE_JAVA)
        self.assertEqual({a["name"] for a in attrs}, {"id", "title", "content"})
        self.assertEqual(attrs[0]["type"], "Long")
        names = {m["name"] for m in methods}
        self.assertIn("page", names)
        self.assertIn("add", names)
        self.assertIn("delete", names)
        self.assertNotIn("getList", names)
        self.assertNotIn("ensurePinnedColumn", names)
        # ensure* 仍跳过；其它 private 方法在全量里保留 -
        self.assertIn("wipeCache", names)
        wipe = next(m for m in methods if m["name"] == "wipeCache")
        self.assertEqual(wipe["visibility"], "-")

    def test_ortho_path_bends(self) -> None:
        pts = ortho_path(0, 0, 100, 80, 300, 200, 100, 80)
        self.assertGreaterEqual(len(pts), 2)
        # 水平主导时应有折点
        self.assertGreaterEqual(len(pts), 3)

    def test_boxes_do_not_overlap_and_paths_avoid_boxes(self) -> None:
        """零交叉布局：框不叠；已画关联线不穿第三方框。"""
        from app.bake.schema.classes import (
            _path_obstacle_hits,
            _paths_proper_cross,
            attach_layout,
            ortho_path,
        )

        classes = []
        for i, name in enumerate(["a", "b", "c", "d", "e", "f"]):
            classes.append(
                {
                    "id": name,
                    "name": name.upper(),
                    "attributes": [{"display": f"+ f{j}: String"} for j in range(4)],
                    "methods": [{"display": "+ page() : Map"} for _ in range(3)],
                }
            )
        model = {
            "classes": classes,
            "associations": [
                {"from": "a", "to": "b"},
                {"from": "a", "to": "c"},
                {"from": "b", "to": "d"},
                {"from": "c", "to": "e"},
                {"from": "d", "to": "f"},
                {"from": "e", "to": "f"},
                {"from": "a", "to": "f"},
            ],
        }
        attach_layout(model)
        pos = {
            k: (v["x"], v["y"], v["w"], v["h"]) for k, v in model["layout"].items()
        }
        ids = list(pos.keys())
        for i in range(len(ids)):
            for j in range(i + 1, len(ids)):
                ax, ay, aw, ah = pos[ids[i]]
                bx, by, bw, bh = pos[ids[j]]
                overlap = not (
                    ax + aw <= bx or bx + bw <= ax or ay + ah <= by or by + bh <= ay
                )
                self.assertFalse(overlap, f"{ids[i]} overlaps {ids[j]}")
        # 零交叉硬约束：已画路径不得冲突；尽量多画
        self.assertTrue(model.get("zero_crossing"))
        self.assertEqual(model.get("assoc_mode"), "zero")
        self.assertGreaterEqual(len(model["associations"]), 5)
        obstacles = [(tid, *pos[tid]) for tid in ids]
        paths = model.get("_assoc_paths") or []
        self.assertEqual(len(paths), len(model["associations"]))
        for i, pts in enumerate(paths):
            a = model["associations"][i]
            frm, to = a["from"], a["to"]
            hits = _path_obstacle_hits(pts, obstacles, {frm, to})
            self.assertEqual(hits, 0, f"path {frm}->{to} punches boxes: {pts}")
        for i in range(len(paths)):
            for j in range(i + 1, len(paths)):
                self.assertFalse(
                    _paths_proper_cross(paths[i], paths[j]),
                    f"crossing between edge {i} and {j}",
                )
        svg = render_class_svg(model)
        self.assertIn('data-zero-crossing="1"', svg)
        self.assertNotIn(" A ", svg)  # 不过桥

    def test_dense_assoc_svg_has_no_path_conflicts(self) -> None:
        """稠密关联 + 零交叉：出图路径两两不得冲突（可少画边）。"""
        from app.bake.schema.classes import _paths_conflict, attach_layout

        names = [f"n{i}" for i in range(8)]
        classes = [
            {
                "id": n,
                "name": n.upper(),
                "attributes": [{"display": f"+ f{j}: String"} for j in range(3)],
                "methods": [{"display": "+ getList() : return"} for _ in range(4)],
            }
            for n in names
        ]
        assocs = []
        for i, a in enumerate(names):
            for b in names[i + 1 :]:
                if (hash(a + b) % 3) == 0:
                    assocs.append({"from": a, "to": b})
        for b in names[1:]:
            assocs.append({"from": names[0], "to": b})
        model = {"classes": classes, "associations": assocs}
        attach_layout(model, assoc_mode="zero")
        svg = render_class_svg(model)
        import re

        ds = re.findall(r'class="uml-assoc"[^>]*\sd="([^"]+)"', svg)
        paths = []
        for d in ds:
            pts = []
            for m in re.finditer(r"[ML]\s*([-\d.]+)\s+([-\d.]+)", d, re.I):
                pts.append((float(m.group(1)), float(m.group(2))))
            if len(pts) >= 2:
                paths.append(pts)
        for i in range(len(paths)):
            for j in range(i + 1, len(paths)):
                self.assertFalse(
                    _paths_conflict(paths[i], paths[j]),
                    f"svg edges {i} and {j} still conflict",
                )

    def test_zero_cross_maximizes_triangle(self) -> None:
        """零交叉下竞赛布局：三角环至少画出生成树 2 条，且无交叉。"""
        from app.bake.schema.classes import _paths_conflict, attach_layout

        classes = [
            {"id": n, "name": n.upper(), "attributes": [], "methods": []}
            for n in ("a", "b", "c")
        ]
        model = {
            "classes": classes,
            "associations": [
                {"from": "a", "to": "b"},
                {"from": "b", "to": "c"},
                {"from": "c", "to": "a"},
            ],
        }
        attach_layout(model)
        self.assertTrue(model.get("zero_crossing"))
        self.assertGreaterEqual(len(model["associations"]), 2)
        paths = model.get("_assoc_paths") or []
        for i in range(len(paths)):
            for j in range(i + 1, len(paths)):
                self.assertFalse(_paths_conflict(paths[i], paths[j]))
        svg = render_class_svg(model)
        self.assertIn('data-zero-crossing="1"', svg)

    def test_readable_text_full_no_truncate(self) -> None:
        """框随全文加宽：不截断签名、不省略条目，字仍落在框内。"""
        from app.bake.schema.classes import (
            _FONT_BODY,
            _H_PAD,
            _box_size,
            _text_w,
        )

        long = "+ updateSomethingVeryLong(String, Integer, Map) : Map<String, Object>"
        model_cls = {
            "id": "t",
            "name": "OrderService",
            "attributes": [
                {"name": f"f{i}", "type": "String", "display": f"+ field{i}NameExtra: String"}
                for i in range(20)
            ],
            "methods": [
                {"name": "updateSomethingVeryLong", "display": long},
                *[{"name": f"m{i}", "display": f"+ m{i}() : void"} for i in range(14)],
            ],
        }
        self.assertEqual(len(model_cls["attributes"]), 20)
        self.assertEqual(len(model_cls["methods"]), 15)
        self.assertNotIn("…", long)
        w, _h = _box_size(model_cls)
        self.assertGreaterEqual(w, _text_w(long, _FONT_BODY, mono=True) + 2 * _H_PAD - 0.5)
        for a in model_cls["attributes"]:
            self.assertLessEqual(
                _text_w(a["display"], _FONT_BODY, mono=True) + 2 * _H_PAD,
                w + 1.0,
            )

    def test_class_layout_patch_roundtrip(self) -> None:
        """拖拽布局落盘后重载仍覆盖自动坐标；并按当前框高收紧间距。"""
        from app.bake.schema.classes import (
            _BOX_GAP,
            apply_class_layout_patch,
            attach_layout,
            clear_class_layout_patch,
            load_class_layout_patch,
            save_class_layout_patch,
        )

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            classes = [
                {"id": "a", "name": "A", "attributes": [], "methods": []},
                {"id": "b", "name": "B", "attributes": [], "methods": []},
            ]
            model = {
                "classes": classes,
                "associations": [{"from": "a", "to": "b"}],
            }
            attach_layout(model)
            # 模拟全量撑开后的大间距（同列上下）
            save_class_layout_patch(
                root,
                {
                    "a": {"x": 100.0, "y": 50.0, "w": 120, "h": 80},
                    "b": {"x": 105.0, "y": 900.0, "w": 120, "h": 80},
                },
            )
            patch = load_class_layout_patch(root)
            self.assertEqual(patch["a"]["x"], 100.0)
            apply_class_layout_patch(model, patch, compact=True)
            self.assertTrue(model.get("layout_manual"))
            self.assertLess(model["layout"]["a"]["y"], model["layout"]["b"]["y"])
            gap = model["layout"]["b"]["y"] - (
                model["layout"]["a"]["y"] + model["layout"]["a"]["h"]
            )
            self.assertAlmostEqual(gap, _BOX_GAP, delta=1.5)
            # 同规则不 compact：保留拖拽绝对坐标
            model2 = {
                "classes": classes,
                "associations": [{"from": "a", "to": "b"}],
            }
            attach_layout(model2)
            apply_class_layout_patch(model2, patch, compact=False)
            self.assertAlmostEqual(model2["layout"]["a"]["x"], 100.0, delta=0.1)
            self.assertAlmostEqual(model2["layout"]["a"]["y"], 50.0, delta=0.1)
            self.assertAlmostEqual(model2["layout"]["b"]["y"], 900.0, delta=0.1)
            clear_class_layout_patch(root)
            self.assertEqual(load_class_layout_patch(root), {})

    def test_parallel_lanes_not_coincident(self) -> None:
        """多条树边中槽应错开，不能叠成同一条水平线。"""
        from app.bake.schema.classes import _LANE_GAP, _route_tree_edge

        # 父框在上，两子框在下
        p1 = _route_tree_edge(100, 40, 120, 80, 40, 200, 100, 80, lane=0, n_lanes=2)
        p2 = _route_tree_edge(100, 40, 120, 80, 200, 200, 100, 80, lane=1, n_lanes=2)
        # 取水平段的 y
        def horiz_ys(pts):
            ys = []
            for i in range(len(pts) - 1):
                if abs(pts[i][1] - pts[i + 1][1]) < 0.5 and abs(pts[i][0] - pts[i + 1][0]) > 1:
                    ys.append(pts[i][1])
            return ys

        y1, y2 = horiz_ys(p1), horiz_ys(p2)
        self.assertTrue(y1 and y2)
        self.assertGreaterEqual(abs(y1[0] - y2[0]), _LANE_GAP - 0.5)

    def test_zero_crossing_spanning_tree(self) -> None:
        """环上优先生成树；能无交叉补回的边可保留，最终路径仍无交叉。"""
        from app.bake.schema.classes import (
            _assoc_route,
            _paths_proper_cross,
            attach_layout,
        )

        classes = [
            {"id": n, "name": n.upper(), "attributes": [], "methods": []}
            for n in ("a", "b", "c")
        ]
        model = {
            "classes": classes,
            "associations": [
                {"from": "a", "to": "b"},
                {"from": "b", "to": "c"},
                {"from": "c", "to": "a"},
            ],
        }
        attach_layout(model, assoc_mode="zero")
        self.assertGreaterEqual(len(model["associations"]), 2)
        self.assertLessEqual(len(model["associations"]), 3)
        self.assertTrue(model.get("zero_crossing"))
        pos = {
            k: (v["x"], v["y"], v["w"], v["h"]) for k, v in model["layout"].items()
        }
        parents = model.get("tree_parents") or {}
        obstacles = [(tid, *pos[tid]) for tid in pos]
        paths = model.get("_assoc_paths") or [
            _assoc_route(a["from"], a["to"], pos, parents, obstacles)
            for a in model["associations"]
        ]
        for i in range(len(paths)):
            for j in range(i + 1, len(paths)):
                self.assertFalse(_paths_proper_cross(paths[i], paths[j]))

    def test_build_with_skeleton_java(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "sql").mkdir()
            (root / "sql" / "schema.sql").write_text(_MINI_SQL, encoding="utf-8")
            (root / "domain.schema.json").write_text(
                json.dumps(_DOMAIN, ensure_ascii=False), encoding="utf-8"
            )
            # 挂入基线 NoticeStore，使 sys_notice 能命中 Java
            src = (
                _REPO
                / "skeletons"
                / "baseline"
                / "backend"
                / "src"
                / "main"
                / "java"
                / "com"
                / "thesis"
                / "service"
                / "NoticeStore.java"
            )
            dest = (
                root
                / "backend"
                / "src"
                / "main"
                / "java"
                / "com"
                / "thesis"
                / "service"
                / "NoticeStore.java"
            )
            dest.parent.mkdir(parents=True, exist_ok=True)
            if src.is_file():
                shutil.copy2(src, dest)
            else:
                dest.write_text(_NOTICE_JAVA, encoding="utf-8")

            # 默认 sample：方法取自实包（带 ()：返回类型），禁止无代码填空四格
            model = build_class_model(root, display_mode="sample")
            self.assertIsNotNone(model)
            assert model is not None
            self.assertEqual(model.get("display_mode"), "sample")
            notice = next(c for c in model["classes"] if c["table"] == "sys_notice")
            self.assertEqual(notice["attr_source"], "java")
            self.assertEqual(notice["method_source"], "java")
            self.assertTrue(any(a["name"] == "title" for a in notice["attributes"]))
            self.assertTrue(str(notice["attributes"][0]["display"]).startswith("- "))
            meth_names = [m["name"] for m in notice["methods"]]
            # 真实方法名；至少命中 page/add 之一
            self.assertTrue(set(meth_names) & {"page", "add", "delete", "list"})
            self.assertNotIn("getList", meth_names)
            for m in notice["methods"]:
                disp = str(m.get("display") or "")
                self.assertIn("(", disp)
                self.assertIn(")", disp)
                self.assertIn(":", disp)

            # full：保留代码真实方法名
            full = build_class_model(root, display_mode="full")
            assert full is not None
            notice_f = next(c for c in full["classes"] if c["table"] == "sys_notice")
            self.assertTrue(
                any(m["name"] in ("page", "add", "delete", "update") for m in notice_f["methods"])
            )
            self.assertFalse(any(m["name"] == "getList" for m in notice_f["methods"]))

            # borrow → book：非空 FK → 聚合（菱形在整体 book）
            all_a = model.get("associations_all") or model["associations"]
            borrow_edges = [
                a
                for a in all_a
                if isinstance(a, dict)
                and {"book", "borrow"} <= {str(a.get("from")), str(a.get("to"))}
            ]
            self.assertTrue(borrow_edges)
            self.assertEqual(borrow_edges[0].get("kind"), "aggregation")
            self.assertEqual(borrow_edges[0].get("from"), "book")
            self.assertEqual(borrow_edges[0].get("to"), "borrow")

            svg = render_class_svg(model)
            self.assertIn("uml-assoc", svg)
            self.assertIn('<path class="uml-assoc"', svg)
            self.assertIn("data-kind=", svg)
            self.assertIn("uml-open", svg)
            self.assertIn('data-from=', svg)
            self.assertIn('class="uml-node"', svg)
            self.assertIn("data-cx=", svg)
            self.assertIn("Notice", svg)
            self.assertNotIn(" A ", svg)  # 不过桥
            # 方法栏应有括号形式
            self.assertRegex(svg, r"\+ (page|add|delete)\(")

    def test_nudge_layout_improves_cramped_boxes(self) -> None:
        """挤在一起的框：挪框开槽后画线数不降，且路径零交叉。"""
        from app.bake.schema.classes import (
            _nudge_layout_for_zero_cross,
            _paths_conflict,
            _trial_zero_crossing,
        )

        names = ("a", "b", "c", "d")
        # 故意挤在一团，逼出漏边
        pos = {
            "a": (48.0, 48.0, 140.0, 90.0),
            "b": (100.0, 70.0, 140.0, 90.0),
            "c": (80.0, 120.0, 140.0, 90.0),
            "d": (130.0, 100.0, 140.0, 90.0),
        }
        all_a = [
            {"from": "a", "to": "b"},
            {"from": "b", "to": "c"},
            {"from": "c", "to": "d"},
            {"from": "d", "to": "a"},
            {"from": "a", "to": "c"},
        ]
        n0, _, t0 = _trial_zero_crossing(all_a, pos, {})
        pos1, t1 = _nudge_layout_for_zero_cross(pos, all_a, {}, max_rounds=24)
        n1 = len(t1.get("associations") or [])
        self.assertGreaterEqual(n1, n0)
        self.assertGreaterEqual(n1, 3)
        paths = t1.get("_assoc_paths") or []
        for i in range(len(paths)):
            for j in range(i + 1, len(paths)):
                self.assertFalse(
                    _paths_conflict(paths[i], paths[j]),
                    f"nudged paths {i},{j} still conflict",
                )
        self.assertEqual(len(pos1), 4)

    def test_refine_persists_nudged_layout(self) -> None:
        """落盘后精炼会写回坐标，且路径保持零交叉。"""
        from app.bake.schema.classes import (
            _paths_conflict,
            load_class_model,
            refine_and_persist_class_layout,
            save_class_layout_patch,
        )

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "sql").mkdir()
            (root / "sql" / "schema.sql").write_text(
                "CREATE TABLE a (id INT PRIMARY KEY);\n"
                "CREATE TABLE b (id INT PRIMARY KEY, a_id INT, "
                "FOREIGN KEY (a_id) REFERENCES a(id));\n"
                "CREATE TABLE c (id INT PRIMARY KEY, b_id INT, "
                "FOREIGN KEY (b_id) REFERENCES b(id));\n",
                encoding="utf-8",
            )
            model = load_class_model(root, display_mode="sample")
            assert model is not None
            # 故意挤在一起
            cramped = {
                tid: {"x": 50.0 + i * 20, "y": 50.0 + i * 15}
                for i, tid in enumerate(model["layout"])
            }
            save_class_layout_patch(root, cramped, display_mode="sample")
            out = refine_and_persist_class_layout(root, display_mode="sample")
            self.assertTrue(out.get("ok"))
            again = load_class_model(root, display_mode="sample")
            assert again is not None
            paths = again.get("_assoc_paths") or []
            for i in range(len(paths)):
                for j in range(i + 1, len(paths)):
                    self.assertFalse(_paths_conflict(paths[i], paths[j]))

    def test_missing_entity_key_reported(self) -> None:
        tables = [{"name": "sys_user", "label": "用户", "columns": []}]
        model = class_model_from_er_tables(
            tables,
            [],
            title="X",
            domain_ents=[{"slot": "archive", "key": "book", "label": "图书"}],
        )
        self.assertEqual(model["evidence"]["entity_keys_missing_in_sql"], ["book"])

    def test_biz_order_matches_entity_key_order(self) -> None:
        """商城 SQL 表名是 biz_order，开题实体 key 是 order，应对上。"""
        tables = [
            {"name": "biz_order", "label": "订单", "columns": []},
            {"name": "order_line", "label": "明细", "columns": []},
        ]
        model = class_model_from_er_tables(
            tables,
            [],
            title="Shop",
            domain_ents=[{"slot": "order", "key": "order", "label": "订单"}],
        )
        ev = model["evidence"]
        self.assertIn("order", ev["entity_keys_matched"])
        self.assertEqual(ev["entity_keys_missing_in_sql"], [])

    def test_svg_paths_inset_from_viewbox_edge(self) -> None:
        """外绕折线不得贴 viewBox 边，默认视口才裁不掉线头。"""
        import re

        from app.bake.schema.classes import (
            _EDGE_MARGIN,
            attach_layout,
            render_class_svg,
        )

        names = [f"n{i}" for i in range(8)]
        classes = [
            {
                "id": nm,
                "name": nm.upper(),
                "attributes": [{"display": f"- f{j}: String"} for j in range(3)],
                "methods": [{"display": "+ page() : Map"}],
            }
            for nm in names
        ]
        assocs = []
        for i in range(len(names)):
            for j in range(i + 1, len(names)):
                if (i + j) % 2 == 0:
                    assocs.append({"from": names[i], "to": names[j], "kind": "association"})
        model = attach_layout(
            {"classes": classes, "associations": assocs, "evidence": {}, "title": "T"}
        )
        svg = render_class_svg(model)
        m = re.search(r'viewBox="0 0 ([\d.]+) ([\d.]+)"', svg)
        self.assertIsNotNone(m)
        vb_w, vb_h = float(m.group(1)), float(m.group(2))
        pts: list[tuple[float, float]] = []
        for d in re.findall(r'class="uml-assoc"[^>]*\sd="([^"]+)"', svg):
            for pm in re.finditer(r"[ML]\s*([-\d.]+)\s+([-\d.]+)", d, re.I):
                pts.append((float(pm.group(1)), float(pm.group(2))))
        self.assertGreater(len(pts), 0)
        min_x = min(p[0] for p in pts)
        min_y = min(p[1] for p in pts)
        max_x = max(p[0] for p in pts)
        max_y = max(p[1] for p in pts)
        # 允许 1px 浮点误差；边距按出图常量
        slack = 1.0
        self.assertGreaterEqual(min_x, _EDGE_MARGIN - slack)
        self.assertGreaterEqual(min_y, _EDGE_MARGIN - slack)
        self.assertLessEqual(max_x, vb_w - _EDGE_MARGIN + slack)
        self.assertLessEqual(max_y, vb_h - _EDGE_MARGIN + slack)

    def test_path_does_not_cut_through_endpoint_box(self) -> None:
        """右侧端口出发禁止再往左穿回自身框（否则白底盖住只剩框外断头）。"""
        from app.bake.schema.classes import (
            _path_respects_endpoint_ports,
            attach_layout,
            render_class_svg,
        )

        box = (100.0, 100.0, 100.0, 80.0)
        # 右端口出发却往左 → 非法
        bad = [(200.0, 140.0), (50.0, 140.0), (50.0, 200.0), (250.0, 200.0)]
        self.assertFalse(_path_respects_endpoint_ports(bad, box, (250.0, 180.0, 80.0, 60.0)))
        # 右端口出发往右 → 合法
        good = [(200.0, 140.0), (230.0, 140.0), (230.0, 210.0), (250.0, 210.0)]
        self.assertTrue(
            _path_respects_endpoint_ports(good, box, (250.0, 180.0, 80.0, 60.0))
        )

        names = [f"n{i}" for i in range(5)]
        classes = [
            {
                "id": nm,
                "name": nm.upper(),
                "attributes": [{"display": "- a: String"}] * 3,
                "methods": [{"display": "+ page() : Map"}],
            }
            for nm in names
        ]
        assocs = [
            {"from": "n0", "to": "n1", "kind": "association"},
            {"from": "n0", "to": "n2", "kind": "aggregation"},
            {"from": "n1", "to": "n3", "kind": "composition"},
            {"from": "n2", "to": "n3", "kind": "association"},
            {"from": "n3", "to": "n4", "kind": "dependency"},
            {"from": "n0", "to": "n4", "kind": "association"},
        ]
        model = attach_layout(
            {"title": "t", "classes": classes, "associations": assocs, "evidence": {}}
        )
        svg = render_class_svg(model)
        boxes: dict[str, tuple[float, float, float, float]] = {}
        for g in re.finditer(r'<g class="uml-node"([^>]*)>', svg):
            attrs = g.group(1)
            bid = re.search(r'data-id="([^"]+)"', attrs).group(1)
            cx = float(re.search(r'data-cx="([^"]+)"', attrs).group(1))
            cy = float(re.search(r'data-cy="([^"]+)"', attrs).group(1))
            hw = float(re.search(r'data-hw="([^"]+)"', attrs).group(1))
            hh = float(re.search(r'data-hh="([^"]+)"', attrs).group(1))
            boxes[bid] = (cx - hw, cy - hh, hw * 2, hh * 2)
        for mm in re.finditer(r'<path class="uml-assoc"[^/]*/>', svg):
            tag = mm.group(0)
            frm_m = re.search(r'data-from="([^"]+)"', tag)
            to_m = re.search(r'data-to="([^"]+)"', tag)
            d_m = re.search(r'\sd="([^"]+)"', tag)
            self.assertTrue(frm_m and to_m and d_m, tag[:120])
            frm, to, d = frm_m.group(1), to_m.group(1), d_m.group(1)
            pts = [
                (float(a), float(b))
                for a, b in re.findall(r"[ML]\s*([-\d.]+)\s+([-\d.]+)", d, re.I)
            ]
            self.assertGreaterEqual(len(pts), 2, f"{frm}->{to} d={d!r}")
            self.assertTrue(
                _path_respects_endpoint_ports(pts, boxes[frm], boxes[to]),
                f"path cuts endpoint box: {frm}->{to} {pts}",
            )


if __name__ == "__main__":
    unittest.main()
