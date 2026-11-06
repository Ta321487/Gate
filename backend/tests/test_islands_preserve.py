"""重 bake islands 白名单保留（pack-overrides §4.4 P0①）。"""

from __future__ import annotations

import json
import shutil
import unittest
from pathlib import Path

from app.bake.catalog import build_spec
from app.bake.engine import bake_project
from app.bake.islands_preserve import (
    ISLANDS_PRESERVE_FORBIDDEN_PREFIXES,
    clear_islands_stash,
    restore_islands_whitelist,
    stash_islands_whitelist,
)
from app.core.config import get_settings


class TestIslandsPreserveUnit(unittest.TestCase):
    def test_roundtrip_keeps_whitelist_skips_diagram_cache(self) -> None:
        import tempfile

        root = Path(tempfile.mkdtemp(prefix="gf_islands_ut_"))
        try:
            islands = root / "islands"
            islands.mkdir()
            (islands / "module_labels.json").write_text(
                json.dumps({"nodes": {"user:home": "手调首页"}}, ensure_ascii=False),
                encoding="utf-8",
            )
            (islands / "class_layout.json").write_text(
                json.dumps({"layout": {"Foo": {"x": 1, "y": 2}}}, ensure_ascii=False),
                encoding="utf-8",
            )
            er_view = islands / "er_view"
            er_view.mkdir()
            (er_view / "user.svg").write_text("<svg>MARKER</svg>", encoding="utf-8")
            cache = islands / "diagram_cache"
            cache.mkdir()
            (cache / "modules__default.json").write_text(
                '{"marker":"SHOULD_NOT_STASH"}', encoding="utf-8"
            )

            stash = stash_islands_whitelist(root)
            self.assertIsNotNone(stash)
            assert stash is not None
            self.assertTrue((stash / "islands" / "module_labels.json").is_file())
            self.assertTrue((stash / "islands" / "class_layout.json").is_file())
            self.assertTrue((stash / "islands" / "er_view" / "user.svg").is_file())
            self.assertFalse((stash / "islands" / "diagram_cache").exists())

            shutil.rmtree(root)
            root.mkdir()
            restored = restore_islands_whitelist(root, stash)
            self.assertIn("islands/module_labels.json", restored)
            self.assertIn("islands/class_layout.json", restored)
            self.assertIn("islands/er_view", restored)

            labels = json.loads(
                (root / "islands" / "module_labels.json").read_text(encoding="utf-8")
            )
            self.assertEqual(labels["nodes"]["user:home"], "手调首页")
            layout = json.loads(
                (root / "islands" / "class_layout.json").read_text(encoding="utf-8")
            )
            self.assertEqual(layout["layout"]["Foo"]["x"], 1)
            self.assertIn(
                "MARKER",
                (root / "islands" / "er_view" / "user.svg").read_text(encoding="utf-8"),
            )
            self.assertFalse((root / "islands" / "diagram_cache").exists())
            clear_islands_stash(stash)
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_empty_workspace_returns_none(self) -> None:
        import tempfile

        root = Path(tempfile.mkdtemp(prefix="gf_islands_empty_"))
        try:
            self.assertIsNone(stash_islands_whitelist(root))
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_forbidden_prefix_documented(self) -> None:
        self.assertIn("islands/diagram_cache", ISLANDS_PRESERVE_FORBIDDEN_PREFIXES)


class TestIslandsPreserveBake(unittest.TestCase):
    """真 bake 两轮：白名单文件应在，diagram_cache 旧标记不得靠 stash 复活。"""

    PID = "gf-ut-islands-preserve"

    def test_rebake_keeps_module_labels_and_class_layout(self) -> None:
        settings = get_settings()
        dest = settings.workspace_dir / self.PID
        if dest.exists():
            shutil.rmtree(dest)

        spec = build_spec(
            title="学生请假销假管理系统",
            archetype="ARCH-FLOW",
            domain="DOM-ATTEND",
            theme="gen-ink",
            llm_enabled=False,
            match_mode="recommended",
            confidence=0.9,
            persistence="jdbc",
        )
        bake_project(self.PID, spec, "smoke_islands_preserve")

        islands = dest / "islands"
        islands.mkdir(exist_ok=True)
        marker_labels = {"nodes": {"admin:users": "P0白名单短签"}, "mode": "manual-test"}
        (islands / "module_labels.json").write_text(
            json.dumps(marker_labels, ensure_ascii=False), encoding="utf-8"
        )

        # 改「真有的类」坐标；假类名会被预热写回清掉，不能当探针
        layout_path = islands / "class_layout.json"
        self.assertTrue(layout_path.is_file(), "首轮 bake 预热应写出 class_layout.json")
        layout_doc = json.loads(layout_path.read_text(encoding="utf-8"))
        boxes = layout_doc.get("layout") if isinstance(layout_doc, dict) else None
        self.assertIsInstance(boxes, dict)
        self.assertTrue(boxes, "class_layout.layout 应非空")
        probe_cls = next(iter(boxes.keys()))
        boxes[probe_cls]["x"] = 42.0
        boxes[probe_cls]["y"] = 99.0
        layout_path.write_text(
            json.dumps(layout_doc, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        cache_dir = islands / "diagram_cache"
        cache_dir.mkdir(exist_ok=True)
        (cache_dir / "modules__default.json").write_text(
            json.dumps({"marker": "OLD_CACHE_MUST_DIE"}), encoding="utf-8"
        )

        bake_project(self.PID, spec, "smoke_islands_preserve")

        labels = json.loads(
            (dest / "islands" / "module_labels.json").read_text(encoding="utf-8")
        )
        self.assertEqual(labels["nodes"]["admin:users"], "P0白名单短签")
        layout_after = json.loads(
            (dest / "islands" / "class_layout.json").read_text(encoding="utf-8")
        )
        box = (layout_after.get("layout") or {}).get(probe_cls) or {}
        self.assertEqual(
            float(box.get("x")),
            42.0,
            msg=f"重 bake 后类 {probe_cls} 坐标应保留",
        )
        self.assertEqual(float(box.get("y")), 99.0)

        # 旧 cache 不得被 stash 原样复活；预热可能新建 cache，但不得含 OLD 标记
        cache_after = dest / "islands" / "diagram_cache"
        if cache_after.is_dir():
            for p in cache_after.rglob("*.json"):
                text = p.read_text(encoding="utf-8")
                self.assertNotIn(
                    "OLD_CACHE_MUST_DIE",
                    text,
                    msg=f"diagram_cache 被错误保留: {p}",
                )

    def test_rebake_keeps_applied_module_override_label(self) -> None:
        """P0⑤：apply_overrides 写短签 → 重 bake → 字仍在且进 model（stash + 盘上 nodes）。

        裸 ``bake_project`` 不落 ``domain.schema.json``（填岛/emit 才写）；测里补 emit，贴近 job 后半段。
        """
        from app.bake.engine_islands import emit_schema_to_workspace
        from app.bake.overrides import apply_overrides_to_workspace, empty_payload
        from app.bake.schema.modules import build_module_model, iter_nodes

        settings = get_settings()
        dest = settings.workspace_dir / self.PID
        if dest.exists():
            shutil.rmtree(dest)

        spec = build_spec(
            title="学生请假销假管理系统",
            archetype="ARCH-FLOW",
            domain="DOM-ATTEND",
            theme="gen-ink",
            llm_enabled=False,
            match_mode="recommended",
            confidence=0.9,
            persistence="jdbc",
        )
        bake_project(self.PID, spec, "smoke_islands_preserve")
        # bake 写回了盘上 spec；emit 需要带 schema 的那份
        disk_spec = json.loads((dest / "spec.json").read_text(encoding="utf-8"))
        emit_schema_to_workspace(dest, disk_spec)

        model = build_module_model(dest, with_label_patch=False)
        self.assertIsNotNone(model)
        leaf = next(
            (
                n
                for n in iter_nodes(model)
                if n.get("id")
                and ":" in str(n.get("id"))
                and str(n.get("id")) not in ("root",)
                and not (n.get("children") or [])
            ),
            None,
        )
        self.assertIsNotNone(leaf, "应有菜单叶子可手调")
        nid = str(leaf["id"])
        hand = "手调短签甲"

        payload = empty_payload()
        payload["module_labels"] = {nid: hand}
        apply_overrides_to_workspace(dest, payload, refresh_stale=True)

        bake_project(self.PID, spec, "smoke_islands_preserve")
        disk_spec2 = json.loads((dest / "spec.json").read_text(encoding="utf-8"))
        emit_schema_to_workspace(dest, disk_spec2)

        labels = json.loads(
            (dest / "islands" / "module_labels.json").read_text(encoding="utf-8")
        )
        self.assertEqual(labels.get("nodes", {}).get(nid), hand)
        after = build_module_model(dest, with_label_patch=True)
        self.assertIsNotNone(after)
        hit = next((n for n in iter_nodes(after) if str(n.get("id")) == nid), None)
        self.assertIsNotNone(hit)
        self.assertEqual(str(hit.get("label")), hand)

if __name__ == "__main__":
    unittest.main()
