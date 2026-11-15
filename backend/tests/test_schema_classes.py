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
        # 商品 ← 订单行(item_id)：引用目录，不是组合
        line_ref = {
            "attributes": [
                {"name": "itemId", "column": "item_id", "fk": True, "not_null": True}
            ]
        }
        self.assertEqual(
            _classify_fk_relation_kind(
                "product", "order_line", "item_id", child_cls=line_ref
            ),
            "association",
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

    def test_sample_mode_hides_shell_and_caps_members(self) -> None:
        """论文示例签：藏壳表；属性截断；方法签名无 Spring 注解。"""
        from app.bake.schema.class_model import (
            _SAMPLE_ATTR_LIMIT,
            apply_class_display_mode,
        )

        model = {
            "classes": [
                {
                    "id": "sys_user",
                    "table": "sys_user",
                    "name": "User",
                    "attributes": [
                        {"name": "id", "type": "Long", "pk": True, "source": "sql"},
                        {"name": "username", "type": "String", "source": "sql"},
                        {"name": "password", "type": "String", "source": "sql"},
                        {"name": "nickname", "type": "String", "source": "sql"},
                        {"name": "phone", "type": "String", "source": "sql"},
                        {"name": "failedLoginCount", "type": "Integer", "source": "sql"},
                        {"name": "lockUntil", "type": "LocalDateTime", "source": "sql"},
                        {"name": "securityQuestion", "type": "String", "source": "sql"},
                        {"name": "activationCode", "type": "String", "source": "sql"},
                        {"name": "adminTags", "type": "String", "source": "sql"},
                        {"name": "extra1", "type": "String", "source": "sql"},
                    ],
                    "methods": [
                        {
                            "name": "create",
                            "visibility": "+",
                            "params": "@RequestBody Map body, HttpSession session",
                            "return": "Map<String, Object>",
                            "source": "java",
                        }
                    ],
                },
                {
                    "id": "sys_banner",
                    "table": "sys_banner",
                    "name": "Banner",
                    "attributes": [{"name": "id", "type": "Long", "pk": True}],
                    "methods": [],
                },
                {
                    "id": "sys_login_log",
                    "table": "sys_login_log",
                    "name": "LoginLog",
                    "attributes": [{"name": "id", "type": "Long", "pk": True}],
                    "methods": [],
                },
                {
                    "id": "product",
                    "table": "product",
                    "name": "Product",
                    "attributes": [
                        {"name": "id", "type": "Long", "pk": True},
                        {"name": "title", "type": "String"},
                    ],
                    "methods": [],
                },
            ],
            "associations": [
                {"from": "sys_banner", "to": "sys_user", "kind": "association"},
                {"from": "product", "to": "sys_user", "kind": "association"},
            ],
        }
        apply_class_display_mode(model, "sample")
        ids = {c["id"] for c in model["classes"]}
        self.assertEqual(ids, {"sys_user", "product"})
        self.assertIn("sys_banner", model.get("classes_omitted_sample") or [])
        self.assertEqual(len(model["associations"]), 1)
        user = next(c for c in model["classes"] if c["id"] == "sys_user")
        self.assertLessEqual(len(user["attributes"]), _SAMPLE_ATTR_LIMIT)
        names = [a["name"] for a in user["attributes"]]
        self.assertIn("id", names)
        self.assertIn("username", names)
        # 门锁类后置，截断后不应挤掉业务字段却把 activation 留下一堆
        self.assertNotIn("activationCode", names)
        meth = user["methods"][0]["display"]
        self.assertNotIn("@RequestBody", meth)
        self.assertNotIn("HttpSession", meth)
        self.assertIn("Map", meth)

        full = {
            "classes": [
                {
                    "id": "sys_banner",
                    "table": "sys_banner",
                    "name": "Banner",
                    "attributes": [{"name": "id", "type": "Long"}],
                    "methods": [],
                }
            ],
            "associations": [],
        }
        apply_class_display_mode(full, "full")
        self.assertEqual([c["id"] for c in full["classes"]], ["sys_banner"])

    def test_java_bind_keeps_sql_attrs_and_blocks_god_store(self) -> None:
        """多表上帝 Store 不得盖掉 SQL 属性；订单/购物车能挂上 Order 方法。"""
        sql = """
CREATE TABLE `sys_user` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `username` varchar(64) NOT NULL,
  `nickname` varchar(64) DEFAULT NULL,
  PRIMARY KEY (`id`)
);
CREATE TABLE `category` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `name` varchar(64) NOT NULL,
  PRIMARY KEY (`id`)
);
CREATE TABLE `product` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `title` varchar(120) NOT NULL,
  `category_id` bigint DEFAULT NULL,
  `stock` int DEFAULT 0,
  PRIMARY KEY (`id`)
);
CREATE TABLE `cart_line` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `username` varchar(64) NOT NULL,
  `item_id` bigint NOT NULL,
  `qty` int NOT NULL DEFAULT 1,
  PRIMARY KEY (`id`)
);
CREATE TABLE `biz_order` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `username` varchar(64) NOT NULL,
  `total_yuan` decimal(10,2) NOT NULL,
  `status` varchar(32) NOT NULL,
  PRIMARY KEY (`id`)
);
CREATE TABLE `order_line` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `order_id` bigint NOT NULL,
  `item_id` bigint NOT NULL,
  `qty` int NOT NULL,
  PRIMARY KEY (`id`)
);
CREATE TABLE `user_ledger` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `username` varchar(64) NOT NULL,
  `delta` decimal(12,2) NOT NULL,
  PRIMARY KEY (`id`)
);
"""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "sql").mkdir()
            (root / "sql" / "schema.sql").write_text(sql, encoding="utf-8")
            java_root = (
                root
                / "backend"
                / "src"
                / "main"
                / "java"
                / "com"
                / "campus"
                / "demo"
            )
            (java_root / "capability").mkdir(parents=True)
            (java_root / "service").mkdir(parents=True)
            (java_root / "controller").mkdir(parents=True)
            (java_root / "capability" / "LoyaltyStore.java").write_text(
                """
package com.campus.demo.capability;
public class LoyaltyStore {
    private static Map<String,Object> row(java.sql.ResultSet rs) throws Exception {
        Map<String,Object> m = new LinkedHashMap<>();
        m.put("balanceYuan", rs.getDouble("balance_yuan"));
        m.put("delta", rs.getDouble("delta"));
        return m;
    }
    public static void adjustWallet(String username, double delta) {}
    public static Map pageLedger(String username) { return null; }
    // 蹭绑：字面量提到 sys_user / biz_order
    private static final String U = "sys_user";
    private static final String O = "biz_order";
    private static final String L = "user_ledger";
}
""",
                encoding="utf-8",
            )
            (java_root / "capability" / "ArchiveStore.java").write_text(
                """
package com.campus.demo.capability;
public class ArchiveStore {
    private static String CAT = "category";
    private static String ITEM = "book";
    private static Map<String,Object> row(java.sql.ResultSet rs) throws Exception {
        Map<String,Object> m = new LinkedHashMap<>();
        m.put("title", rs.getString("title"));
        m.put("isbn", rs.getString("isbn"));
        m.put("stock", rs.getInt("stock"));
        return m;
    }
    public static long addCategory(String name) { return 1; }
    public static Map addItem(String title) { return null; }
    public static void addTrainHours(long id, double hours) {}
    public static void bind(String categoryTable, String itemTable) {}
}
""",
                encoding="utf-8",
            )
            (java_root / "capability" / "OrderStore.java").write_text(
                """
package com.campus.demo.capability;
public class OrderStore {
    private static String CART = "";
    private static String ORDER = "";
    private static String LINE = "";
    public static void bind(String cartTable, String orderTable, String lineTable, boolean q) {}
    public static Map pageOrders(String username) { return null; }
    public static void addToCart(String username, long itemId, int qty) {}
    public static long placeOrder(String username) { return 1; }
}
""",
                encoding="utf-8",
            )
            (java_root / "service" / "UserStore.java").write_text(
                """
package com.campus.demo.service;
public class UserStore {
    private static Map<String,Object> row(java.sql.ResultSet rs) throws Exception {
        Map<String,Object> m = new LinkedHashMap<>();
        m.put("id", rs.getLong("id"));
        m.put("username", rs.getString("username"));
        m.put("nickname", rs.getString("nickname"));
        return m;
    }
    public static Map getUserById(long id) { return null; }
    public static void updateUser(long id, String nickname) {}
}
""",
                encoding="utf-8",
            )
            (java_root / "controller" / "CategoryController.java").write_text(
                """
package com.campus.demo.controller;
public class CategoryController {
    public List list() { return null; }
    public long create(String name) { return 1; }
    public void update(long id, String name) {}
    public void delete(long id) {}
    private boolean bool(Object v) { return false; }
}
""",
                encoding="utf-8",
            )

            model = build_class_model(root, display_mode="sample")
            self.assertIsNotNone(model)
            assert model is not None
            by = {c["table"]: c for c in model["classes"]}

            user = by["sys_user"]
            self.assertEqual(user["attr_source"], "sql")
            self.assertEqual({a["name"] for a in user["attributes"]}, {"id", "username", "nickname"})
            self.assertNotIn("balanceYuan", {a["name"] for a in user["attributes"]})
            self.assertNotIn("delta", {a["name"] for a in user["attributes"]})
            self.assertTrue({m["name"] for m in user["methods"]} & {"getUserById", "updateUser"})
            self.assertNotIn("adjustWallet", {m["name"] for m in user["methods"]})

            cat = by["category"]
            self.assertEqual(cat["attr_source"], "sql")
            self.assertEqual({a["name"] for a in cat["attributes"]}, {"id", "name"})
            self.assertNotIn("isbn", {a["name"] for a in cat["attributes"]})
            self.assertNotIn("addTrainHours", {m["name"] for m in cat["methods"]})
            self.assertTrue({m["name"] for m in cat["methods"]} & {"list", "create", "update", "delete"})

            order = by["biz_order"]
            self.assertEqual(order["attr_source"], "sql")
            self.assertIn("totalYuan", {a["name"] for a in order["attributes"]})
            self.assertNotIn("balanceYuan", {a["name"] for a in order["attributes"]})
            self.assertTrue(
                {m["name"] for m in order["methods"]}
                & {"pageOrders", "placeOrder", "addToCart"}
            )

            cart = by["cart_line"]
            self.assertEqual(cart["attr_source"], "sql")
            self.assertTrue(
                {m["name"] for m in cart["methods"]}
                & {"pageOrders", "placeOrder", "addToCart"}
            )

            product = by["product"]
            self.assertEqual(product["attr_source"], "sql")
            self.assertEqual(
                {a["name"] for a in product["attributes"]},
                {"id", "title", "categoryId", "stock"},
            )
            # Archive 归属 product，应有方法且不是空
            self.assertTrue(product["methods"])

    def test_ortho_path_bends(self) -> None:
        pts = ortho_path(0, 0, 100, 80, 300, 200, 100, 80)
        self.assertGreaterEqual(len(pts), 2)
        # 水平主导时应有折点
        self.assertGreaterEqual(len(pts), 3)

    def test_boxes_do_not_overlap_and_paths_avoid_boxes(self) -> None:
        """ELK 初局：框不叠；尽量画全关联（不要求零交叉）。"""
        from app.bake.schema.classes import attach_layout

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
        self.assertFalse(model.get("zero_crossing"))
        self.assertEqual(model.get("assoc_mode"), "elk")
        self.assertEqual(model.get("evidence", {}).get("layout_algo"), "elk")
        self.assertEqual(len(model["associations"]), 7)
        paths = model.get("_assoc_paths") or []
        self.assertEqual(len(paths), len(model["associations"]))
        svg = render_class_svg(model)
        self.assertNotIn('data-zero-crossing="1"', svg)

    def test_dense_assoc_svg_draws_all(self) -> None:
        """稠密关联：ELK 初局尽量画全边（允许交叉）。"""
        from app.bake.schema.classes import attach_layout

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
        attach_layout(model)
        self.assertEqual(len(model["associations"]), len(assocs))
        self.assertEqual(len(model.get("associations_omitted") or []), 0)
        svg = render_class_svg(model)
        self.assertIn("uml-assoc", svg)

    def test_elk_draws_triangle_all_edges(self) -> None:
        """三角环：ELK 画全 3 条边（不要求零交叉）。"""
        from app.bake.schema.classes import attach_layout

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
        self.assertFalse(model.get("zero_crossing"))
        self.assertEqual(len(model["associations"]), 3)
        svg = render_class_svg(model)
        self.assertIn("uml-assoc", svg)

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

    def test_unclump_manual_layout_separates_overlap(self) -> None:
        """框高变大后旧坐标叠堆 → 推开，避免糊作一团。"""
        from app.bake.schema.class_model import _unclump_manual_layout
        from app.bake.schema.classes import _BOX_GAP

        model = {
            "layout": {
                "a": {"x": 40.0, "y": 40.0, "w": 160.0, "h": 200.0},
                "b": {"x": 50.0, "y": 60.0, "w": 160.0, "h": 200.0},
            }
        }
        _unclump_manual_layout(model)
        self.assertTrue(model.get("layout_unclumped"))
        a, b = model["layout"]["a"], model["layout"]["b"]
        separated = (
            a["x"] + a["w"] + _BOX_GAP <= b["x"]
            or b["x"] + b["w"] + _BOX_GAP <= a["x"]
            or a["y"] + a["h"] + _BOX_GAP <= b["y"]
            or b["y"] + b["h"] + _BOX_GAP <= a["y"]
        )
        self.assertTrue(separated, msg=f"still overlapping: {a} vs {b}")

    def test_unclump_does_not_rewrite_hand_layout_on_disk(self) -> None:
        """重叠手调：预热/打开可内存去簇，但不得改写 islands/class_layout.json。"""
        from app.bake.schema.classes import (
            load_class_layout_patch,
            load_class_model,
            save_class_layout_patch,
        )

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "sql").mkdir()
            (root / "sql" / "schema.sql").write_text(
                "CREATE TABLE a (id INT PRIMARY KEY);\n"
                "CREATE TABLE b (id INT PRIMARY KEY, a_id INT, "
                "FOREIGN KEY (a_id) REFERENCES a(id));\n",
                encoding="utf-8",
            )
            model0 = load_class_model(root, display_mode="sample")
            assert model0 is not None
            ids = list(model0["layout"].keys())
            self.assertGreaterEqual(len(ids), 2)
            hand = {
                ids[0]: {"x": 40.0, "y": 40.0},
                ids[1]: {"x": 50.0, "y": 55.0},
            }
            for tid in ids[2:]:
                box = model0["layout"][tid]
                hand[tid] = {"x": float(box["x"]), "y": float(box["y"])}
            save_class_layout_patch(root, hand, display_mode="sample")
            before = load_class_layout_patch(root)

            again = load_class_model(root, display_mode="sample")
            assert again is not None
            self.assertTrue(
                again.get("layout_unclumped"),
                msg="重叠手调应触发内存去簇",
            )
            after = load_class_layout_patch(root)
            self.assertEqual(
                after,
                before,
                msg="去簇不得回写手调 class_layout.json",
            )
            self.assertAlmostEqual(after[ids[0]]["x"], 40.0)
            self.assertAlmostEqual(after[ids[0]]["y"], 40.0)
            self.assertAlmostEqual(after[ids[1]]["x"], 50.0)
            self.assertAlmostEqual(after[ids[1]]["y"], 55.0)

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

    def test_manual_layout_keeps_box_positions(self) -> None:
        """人工钉框：重算折线不挪其它框，且不重跑 ELK。"""
        from unittest import mock

        from app.bake.schema.classes import _apply_manual_zero_cross, attach_layout

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
        model["layout"] = {
            "a": {"x": 40.0, "y": 40.0, "w": 120.0, "h": 80.0},
            "b": {"x": 280.0, "y": 40.0, "w": 120.0, "h": 80.0},
            "c": {"x": 160.0, "y": 220.0, "w": 120.0, "h": 80.0},
        }
        before = {k: dict(v) for k, v in model["layout"].items()}
        with mock.patch(
            "app.bake.schema.class_layout.layout_graph",
            side_effect=AssertionError("manual path must not call ELK"),
        ):
            _apply_manual_zero_cross(model)
        for k, v in before.items():
            self.assertEqual(model["layout"][k]["x"], v["x"])
            self.assertEqual(model["layout"][k]["y"], v["y"])
        self.assertTrue(model.get("layout_manual"))
        self.assertEqual(model.get("layout_algo"), "manual")
        self.assertEqual(len(model["associations"]), 3)

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
            # 属性跟 SQL 列；方法跟 Store
            self.assertEqual(notice["attr_source"], "sql")
            self.assertEqual(notice["method_source"], "java")
            self.assertTrue(any(a["name"] == "title" for a in notice["attributes"]))
            self.assertTrue(any(a.get("column") == "title" for a in notice["attributes"]))
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

    def test_attach_layout_dense_graph_finishes_under_budget(self) -> None:
        """稠密关系不得拖死打开接口（axios 默认 60s；预算约 12s）。"""
        import time

        from app.bake.schema.classes import _paths_conflict, attach_layout

        n = 12
        classes = [
            {
                "id": f"c{i}",
                "name": f"C{i}",
                "attributes": [{"display": f"+ f{j}: String"} for j in range(3)],
                "methods": [{"display": "+ page() : Map"}],
            }
            for i in range(n)
        ]
        assocs = []
        for i in range(n):
            for j in range(i + 1, n):
                if ((i * 31 + j * 17) % 100) < 45:
                    assocs.append(
                        {
                            "from": f"c{i}",
                            "to": f"c{j}",
                            "kind": "association",
                        }
                    )
        self.assertGreaterEqual(len(assocs), 20)
        model = {
            "title": "perf",
            "classes": classes,
            "associations": list(assocs),
            "evidence": {},
        }
        t0 = time.perf_counter()
        attach_layout(model)
        dt = time.perf_counter() - t0
        self.assertLess(dt, 20.0, f"attach_layout too slow: {dt:.2f}s edges={len(assocs)}")
        paths = model.get("_assoc_paths") or []
        for i in range(len(paths)):
            for j in range(i + 1, len(paths)):
                self.assertFalse(_paths_conflict(paths[i], paths[j]))
        self.assertGreaterEqual(len(model.get("associations") or []), n - 1)

    def test_auto_layout_persisted_for_fast_reopen(self) -> None:
        """首次自动排版写 islands/class_layout.json，二次打开跳过竞赛。"""
        from app.bake.schema.classes import load_class_layout_patch, load_class_model

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "sql").mkdir()
            (root / "sql" / "schema.sql").write_text(_MINI_SQL, encoding="utf-8")
            m1 = load_class_model(root, display_mode="sample")
            assert m1 is not None
            patch = load_class_layout_patch(root)
            self.assertTrue(patch, "auto layout should persist")
            self.assertTrue(m1.get("layout_auto_persisted") or patch)
            m2 = load_class_model(root, display_mode="sample")
            assert m2 is not None
            self.assertTrue(m2.get("layout_manual") or m2.get("layout"))

    def test_class_keeps_favorite_link_table_no_user_product_collapse(self) -> None:
        """类图保留 UserFavorite 外键边；禁止塌成 User↔Product 泛关联/收藏直连。"""
        sql = """
CREATE TABLE `sys_user` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `username` varchar(64) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_username` (`username`)
);
CREATE TABLE `product` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `title` varchar(120) NOT NULL,
  `owner_username` varchar(64) DEFAULT NULL,
  PRIMARY KEY (`id`),
  FOREIGN KEY (`owner_username`) REFERENCES `sys_user` (`username`)
);
CREATE TABLE `user_favorite` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `username` varchar(64) NOT NULL,
  `item_id` bigint NOT NULL,
  `created_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  FOREIGN KEY (`username`) REFERENCES `sys_user` (`username`),
  FOREIGN KEY (`item_id`) REFERENCES `product` (`id`)
);
"""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "sql").mkdir()
            (root / "sql" / "schema.sql").write_text(sql, encoding="utf-8")
            model = build_class_model(root, display_mode="full")
            assert model is not None
            ids = {str(c.get("id")) for c in model["classes"]}
            self.assertIn("user_favorite", ids)
            self.assertIn("product", ids)
            self.assertIn("sys_user", ids)

            def ends(a: dict) -> tuple[str, str]:
                return str(a.get("from") or ""), str(a.get("to") or "")

            assocs = [a for a in (model.get("associations") or []) if isinstance(a, dict)]
            # 允许商品→用户的归属 FK；禁止收藏中间表塌成的账号↔商品直连
            collapsed = [
                a
                for a in assocs
                if set(ends(a)) == {"sys_user", "product"}
                and str(a.get("via") or "")
                in ("user_favorite", "收藏", "关联", "")
            ]
            self.assertEqual(
                collapsed,
                [],
                msg=f"unexpected collapsed User↔Product edges: {collapsed}",
            )
            own = [
                a
                for a in assocs
                if set(ends(a)) == {"sys_user", "product"}
                and str(a.get("via") or "") == "owner_username"
            ]
            self.assertEqual(len(own), 1, msg=own)
            vias = {str(a.get("via") or "") for a in assocs}
            self.assertIn("owner_username", vias)
            self.assertIn("username", vias)
            self.assertIn("item_id", vias)
            # 论文模板画法：边不挂 FK 列名，也不 scrub 成 E-R「关联/收藏」
            labels = {str(a.get("label") or "") for a in assocs}
            self.assertEqual(labels, {""}, msg=f"edge labels should be empty: {labels}")
            self.assertNotIn("关联", labels)
            self.assertNotIn("收藏", labels)
            self.assertNotIn("owner_username", labels)
            # 类框标题：Pascal + 中文括号
            from app.bake.schema.class_model import class_box_title

            by_id = {
                str(c.get("id")): c
                for c in model["classes"]
                if isinstance(c, dict)
            }
            self.assertEqual(class_box_title(by_id["sys_user"]), "User (用户)")
            self.assertEqual(class_box_title(by_id["product"]), "Product (商品)")
            self.assertEqual(
                class_box_title(by_id["user_favorite"]), "UserFavorite (用户收藏)"
            )
            # 收藏走中间表两端
            fav_ends = {
                frozenset(ends(a))
                for a in assocs
                if str(a.get("from") or "") == "user_favorite"
                or str(a.get("to") or "") == "user_favorite"
            }
            self.assertIn(frozenset({"user_favorite", "sys_user"}), fav_ends)
            self.assertIn(frozenset({"user_favorite", "product"}), fav_ends)


if __name__ == "__main__":
    unittest.main()
