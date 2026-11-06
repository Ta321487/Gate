"""Overrides payload 校验 / nodes merge / 失效键（pack-overrides P0②③）。"""

from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from app.bake.overrides import (
    OverridesValidationError,
    apply_class_label_overrides,
    apply_overrides_to_workspace,
    empty_payload,
    merge_module_label_nodes,
    module_labels_flat_to_nodes,
    refresh_stale_module_labels,
    sanitize_overrides_payload,
    write_overrides_mirror,
)
from app.bake.schema.modules import apply_module_hide


class TestOverridesSanitize(unittest.TestCase):
    def test_empty_ok(self) -> None:
        p = sanitize_overrides_payload({})
        self.assertEqual(p["schema_version"], 1)
        self.assertEqual(p["module_labels"], {})

    def test_forbidden_caps_force_off(self) -> None:
        with self.assertRaises(OverridesValidationError) as ctx:
            sanitize_overrides_payload({"caps_force_off": ["x"]})
        self.assertIn("禁止", str(ctx.exception))

    def test_forbidden_sql_prefix(self) -> None:
        with self.assertRaises(OverridesValidationError):
            sanitize_overrides_payload({"sql_drop": True})

    def test_unknown_top_key(self) -> None:
        with self.assertRaises(OverridesValidationError) as ctx:
            sanitize_overrides_payload({"file_replaces": {}})
        self.assertTrue("禁止" in str(ctx.exception) or "未知" in str(ctx.exception))

    def test_module_labels_flat(self) -> None:
        p = sanitize_overrides_payload(
            {"module_labels": {"user:orders": "我的订单", "bad": ""}}
        )
        self.assertEqual(p["module_labels"], {"user:orders": "我的订单"})


class TestModuleLabelMerge(unittest.TestCase):
    def test_flat_to_nodes(self) -> None:
        self.assertEqual(
            module_labels_flat_to_nodes({"a:b": "短"}),
            {"nodes": {"a:b": "短"}},
        )

    def test_merge_keeps_other_ids(self) -> None:
        existing = {"nodes": {"user:a": "机A", "user:b": "机B"}}
        out = merge_module_label_nodes(existing, {"user:a": "手A"})
        self.assertEqual(out["nodes"]["user:a"], "手A")
        self.assertEqual(out["nodes"]["user:b"], "机B")

    def test_stale_moves_missing_keys(self) -> None:
        payload = empty_payload()
        payload["module_labels"] = {"live:1": "在", "gone:2": "没了"}
        payload["module_hide"] = ["live:1", "gone:hide"]
        out = refresh_stale_module_labels(payload, {"live:1"})
        self.assertEqual(out["module_labels"], {"live:1": "在"})
        self.assertEqual(out["module_hide"], ["live:1"])
        keys = {x.get("key") for x in out.get("_stale") or []}
        self.assertIn("module_labels.gone:2", keys)
        self.assertIn("module_hide.gone:hide", keys)


class TestClassLabelOverrides(unittest.TestCase):
    def test_covers_by_class_name(self) -> None:
        model = {
            "classes": [
                {"name": "OrderStore", "table": "biz_order", "label": "订单"},
                {"name": "UserStore", "table": "sys_user", "label": "用户"},
            ]
        }
        out = apply_class_label_overrides(model, {"OrderStore": "订单仓"})
        self.assertEqual(out["classes"][0]["label"], "订单仓")
        self.assertEqual(out["classes"][1]["label"], "用户")


class TestModuleHide(unittest.TestCase):
    def test_prune_leaf_keeps_sibling(self) -> None:
        model = {
            "root": {
                "id": "root",
                "label": "系统",
                "children": [
                    {
                        "id": "identity:0",
                        "label": "用户",
                        "children": [
                            {"id": "identity:0:m0", "label": "订单"},
                            {"id": "identity:0:m1", "label": "收藏"},
                        ],
                    }
                ],
            }
        }
        out = apply_module_hide(model, {"identity:0:m0"})
        kids = out["root"]["children"][0]["children"]
        self.assertEqual([c["id"] for c in kids], ["identity:0:m1"])
        self.assertEqual(out.get("module_hide"), ["identity:0:m0"])

    def test_cannot_hide_root(self) -> None:
        model = {"root": {"id": "root", "label": "系统", "children": []}}
        out = apply_module_hide(model, {"root"})
        self.assertEqual(out["root"]["id"], "root")

    def test_build_model_applies_hide_from_mirror(self) -> None:
        from app.bake.schema.modules import build_module_model, iter_nodes

        root = Path(tempfile.mkdtemp(prefix="gf_ov_hide_"))
        try:
            (root / "domain.schema.json").write_text(
                json.dumps(
                    {
                        "title": "测",
                        "labels": {"appName": "测"},
                        "roles": {
                            "user": {"id": "user", "label": "用户"},
                            "admin": {"id": "admin", "label": "管理员"},
                        },
                        "menus": {
                            "user": [{"key": "orders", "label": "订单"}],
                            "admin": [{"key": "users", "label": "用户管理"}],
                        },
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            (root / "spec.json").write_text(
                json.dumps({"title": "测"}, ensure_ascii=False), encoding="utf-8"
            )
            full = build_module_model(root, apply_hide=False)
            assert full is not None
            leaf = next(
                n
                for n in iter_nodes(full)
                if n.get("id", "").endswith(":m0") or ":m" in str(n.get("id") or "")
            )
            lid = str(leaf["id"])
            payload = empty_payload()
            payload["module_hide"] = [lid]
            write_overrides_mirror(root, payload)
            shown = build_module_model(root, apply_hide=True)
            assert shown is not None
            ids = {str(n.get("id") or "") for n in iter_nodes(shown)}
            self.assertNotIn(lid, ids)
            # 微调表路径：未剪枝仍能看到该 id
            listed = build_module_model(root, apply_hide=False)
            assert listed is not None
            self.assertIn(lid, {str(n.get("id") or "") for n in iter_nodes(listed)})
        finally:
            shutil.rmtree(root, ignore_errors=True)


class TestOverridesApplyWorkspace(unittest.TestCase):
    def test_writes_mirror_and_module_labels(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="gf_ov_apply_"))
        try:
            # 最小 schema 供 collect ids；无则 refresh_stale 跳过
            (root / "domain.schema.json").write_text(
                json.dumps(
                    {
                        "title": "测",
                        "labels": {"appName": "测"},
                        "roles": {
                            "user": {"id": "user", "label": "用户"},
                            "admin": {"id": "admin", "label": "管理员"},
                        },
                        "menus": {
                            "user": [{"key": "orders", "label": "订单"}],
                            "admin": [{"key": "users", "label": "用户管理"}],
                        },
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            (root / "spec.json").write_text(
                json.dumps({"title": "测"}, ensure_ascii=False), encoding="utf-8"
            )
            # 预置 LLM 短签（含树上无的 keep:x，merge 须保留）
            islands = root / "islands"
            islands.mkdir()
            (islands / "module_labels.json").write_text(
                json.dumps(
                    {"nodes": {"identity:0:m0": "机叶", "keep:x": "保留"}},
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            payload = empty_payload()
            # 树上真有的 id；gone 必失效；拉丁混中文走手调写盘不得被 looks_latin 静默丢
            payload["module_labels"] = {
                "identity:0:m0": "手叶",
                "gone:never": "应失效",
                "identity:0:m1": "AI客服台",
            }
            applied = apply_overrides_to_workspace(root, payload, refresh_stale=True)

            mirror = json.loads((islands / "overrides.json").read_text(encoding="utf-8"))
            self.assertEqual(mirror["module_labels"].get("identity:0:m0"), "手叶")
            self.assertEqual(mirror["module_labels"].get("identity:0:m1"), "AI客服台")
            self.assertNotIn("gone:never", mirror["module_labels"])
            stale_keys = {x.get("key") for x in (mirror.get("_stale") or [])}
            self.assertIn("module_labels.gone:never", stale_keys)
            labels = json.loads((islands / "module_labels.json").read_text(encoding="utf-8"))
            self.assertEqual(labels["nodes"]["identity:0:m0"], "手叶")
            self.assertEqual(labels["nodes"]["identity:0:m1"], "AI客服台")
            self.assertEqual(labels["nodes"]["keep:x"], "保留")
            self.assertIn("module_labels", applied)

            # 空=跟机器：去掉手调键后须从盘上删掉，不得继续叠旧字
            cleared = empty_payload()
            cleared["module_labels"] = {}
            apply_overrides_to_workspace(root, cleared, refresh_stale=False)
            labels2 = json.loads(
                (islands / "module_labels.json").read_text(encoding="utf-8")
            )
            self.assertNotIn("identity:0:m0", labels2.get("nodes") or {})
            self.assertNotIn("identity:0:m1", labels2.get("nodes") or {})
            self.assertEqual((labels2.get("nodes") or {}).get("keep:x"), "保留")
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_write_mirror_roundtrip(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="gf_ov_mir_"))
        try:
            p = sanitize_overrides_payload({"module_labels": {"a:b": "字"}})
            write_overrides_mirror(root, p)
            text = (root / "islands" / "overrides.json").read_text(encoding="utf-8")
            self.assertIn("a:b", text)
        finally:
            shutil.rmtree(root, ignore_errors=True)


class TestModuleNodesForOverridesUi(unittest.TestCase):
    def test_lists_detail_leaves_and_machine_not_hand(self) -> None:
        """展开细节叶进表；原词不叠手调（避免改「广告位→广告槽」后原词也变槽）。"""
        from app.bake.overrides import (
            apply_overrides_to_workspace,
            empty_payload,
            list_module_nodes_for_overrides_ui,
        )

        root = Path(tempfile.mkdtemp(prefix="gf_ov_nodes_"))
        try:
            schema = {
                "title": "测店",
                "roles": [{"id": "admin", "label": "管理员"}],
                "menus": {
                    "admin": [
                        {"key": "archive", "label": "农产品管理"},
                        {"key": "banners", "label": "广告位"},
                    ],
                    "user": [],
                },
            }
            (root / "domain.schema.json").write_text(
                json.dumps(schema, ensure_ascii=False), encoding="utf-8"
            )
            (root / "spec.json").write_text(
                json.dumps({"title": "测店"}, ensure_ascii=False), encoding="utf-8"
            )
            # 身份枚举进材料：一级模块带【广告位】细节
            proposal = (
                "管理员端功能模块划分为：登录模块、农产品管理模块【广告位】。"
            )
            (root / "proposal.txt").write_text(proposal, encoding="utf-8")

            # 手调叠在盘上后，清单原词仍应是机器名
            from app.bake.schema.modules import build_module_model, save_module_label_patch

            model = build_module_model(
                root,
                with_label_patch=False,
                apply_hide=False,
                expand_details=True,
                proposal_text=proposal,
            )
            self.assertIsNotNone(model)
            # 须与材料图同传开题，否则只见菜单 pad、看不到【广告位】细节叶
            rows = list_module_nodes_for_overrides_ui(root, proposal_text=proposal)
            ad_rows = [r for r in rows if "广告" in (r.get("label") or "")]
            self.assertEqual(len(ad_rows), 1, ad_rows)
            # 路径应含父级（展开后），不能只剩「管理员/广告位」而无农产品
            self.assertTrue(
                any("农产品" in (r.get("path") or "") for r in ad_rows)
                or any(":d" in (r.get("id") or "") for r in ad_rows),
                ad_rows,
            )

            target = ad_rows[0]
            payload = empty_payload()
            payload["module_labels"] = {target["id"]: "广告槽"}
            apply_overrides_to_workspace(
                root, payload, refresh_stale=True, proposal_text=proposal
            )
            after = list_module_nodes_for_overrides_ui(root, proposal_text=proposal)
            hit = next(r for r in after if r["id"] == target["id"])
            self.assertEqual(hit["label"], target["label"])  # 仍是机器原词
            self.assertNotEqual(hit["label"], "广告槽")
            # 手调后树上仍只有一支广告叶（不得新旧并存）
            ad_after = [r for r in after if "广告" in (r.get("label") or "")]
            self.assertEqual(len(ad_after), 1, ad_after)
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_resolve_selection_and_sequence_labels(self) -> None:
        from app.bake.overrides import (
            apply_sequence_label_overrides,
            resolve_override_selection,
            write_overrides_mirror,
        )

        root = Path(tempfile.mkdtemp(prefix="gf_ov_p1_"))
        try:
            payload = empty_payload()
            payload["sequence"] = {
                "selected_ids": ["a", "b", "c"],
                "labels": {"d1::m:1": "手消息", "d1::p:actor": "买家"},
            }
            write_overrides_mirror(root, payload)
            self.assertEqual(resolve_override_selection(root, "sequence"), ["a", "b", "c"])
            model = {
                "diagrams": [
                    {
                        "id": "d1",
                        "participants": [{"id": "actor", "label": "用户"}],
                        "messages": [{"seq": 1, "text": "机消息"}],
                    }
                ]
            }
            out = apply_sequence_label_overrides(model, payload["sequence"]["labels"])
            self.assertEqual(out["diagrams"][0]["messages"][0]["text"], "手消息")
            self.assertEqual(out["diagrams"][0]["participants"][0]["label"], "买家")
        finally:
            shutil.rmtree(root, ignore_errors=True)


class TestP2Overrides(unittest.TestCase):
    def test_architecture_and_usecase_and_menu(self) -> None:
        from app.bake.overrides import (
            apply_architecture_label_overrides,
            apply_menu_schema_label_overrides,
            apply_usecase_diagram_overrides,
            empty_payload,
            write_overrides_mirror,
        )

        arch = {
            "roles": [{"id": "user", "label": "用户"}],
            "layers": [{"id": "vue", "label": "Vue", "bold": True}],
        }
        arch2 = apply_architecture_label_overrides(arch, {"user": "买家", "vue": "前端"})
        self.assertEqual(arch2["roles"][0]["label"], "买家")
        self.assertEqual(arch2["layers"][0]["label"], "前端")

        uc = {
            "actor": {"id": "user", "label": "用户"},
            "level1": [
                {
                    "id": "u1",
                    "label": "管订单",
                    "includes": [{"id": "u1:a", "label": "下单"}, {"id": "u1:b", "label": "退单"}],
                }
            ],
        }
        uc2 = apply_usecase_diagram_overrides(
            uc, labels={"actor:user": "买家", "u1": "订单管理"}, hide=["u1:b"]
        )
        self.assertEqual(uc2["actor"]["label"], "买家")
        self.assertEqual(uc2["level1"][0]["label"], "订单管理")
        self.assertEqual([x["id"] for x in uc2["level1"][0]["includes"]], ["u1:a"])

        root = Path(tempfile.mkdtemp(prefix="gf_ov_p2_"))
        try:
            schema = {
                "labels": {"appName": "机名"},
                "menus": {"user": [{"key": "orders", "label": "订单"}]},
            }
            (root / "domain.schema.json").write_text(
                json.dumps(schema, ensure_ascii=False), encoding="utf-8"
            )
            payload = empty_payload()
            payload["menu_labels"] = {"orders": "我的订单"}
            payload["schema_labels"] = {"appName": "手调店"}
            write_overrides_mirror(root, payload)
            apply_menu_schema_label_overrides(root, payload)
            saved = json.loads((root / "domain.schema.json").read_text(encoding="utf-8"))
            self.assertEqual(saved["labels"]["appName"], "手调店")
            self.assertEqual(saved["menus"]["user"][0]["label"], "我的订单")
        finally:
            shutil.rmtree(root, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
