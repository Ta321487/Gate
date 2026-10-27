"""出包前布局 companion 回拷：旧 Profile / 过期 accountFace 不得再红 abs_in_stretch_slot。"""

from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

from app.bake.layout_contract import scan_layout_contracts
from app.bake.layout_heal import heal_layout_companions_from_baseline
from app.core.config import get_settings

BASE_FE = get_settings().skeletons_dir / "baseline" / "frontend" / "src"
# 旧工作区样本：内联 Profile + 无 align-self 的 accountFace
_OLD_WS = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "workspace"
    / "gf-ut-sec-jdbc"
    / "frontend"
    / "src"
)


class LayoutHealTests(unittest.TestCase):
    def test_heal_creates_profile_css_and_refreshes_account_face(self) -> None:
        if not BASE_FE.is_dir():
            self.skipTest("baseline missing")
        if not (_OLD_WS / "views" / "Profile.vue").is_file():
            self.skipTest("old workspace sample missing")

        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp) / "ws"
            fe = ws / "frontend" / "src"
            (fe / "views").mkdir(parents=True)
            (fe / "styles").mkdir(parents=True)
            shutil.copy2(_OLD_WS / "views" / "Profile.vue", fe / "views" / "Profile.vue")
            shutil.copy2(
                _OLD_WS / "styles" / "accountFace.css",
                fe / "styles" / "accountFace.css",
            )
            self.assertFalse((fe / "views" / "Profile.css").is_file())
            before = [
                f
                for f in scan_layout_contracts(src=fe)
                if f.pattern_id == "abs_in_stretch_slot"
            ]
            self.assertTrue(before, "旧包样本应先红，否则测不到 heal")

            written = heal_layout_companions_from_baseline(ws)
            self.assertTrue(
                any(p.endswith("Profile.css") for p in written)
                or (fe / "views" / "Profile.css").is_file(),
                f"应补齐 Profile.css，written={written}",
            )
            self.assertTrue((fe / "views" / "Profile.css").is_file())
            af = (fe / "styles" / "accountFace.css").read_text(encoding="utf-8")
            self.assertIn("align-self", af)
            vue = (fe / "views" / "Profile.vue").read_text(encoding="utf-8")
            # 内联槽或 companion 至少一处自限高
            self.assertTrue(
                "align-self" in vue
                or "align-self" in (fe / "views" / "Profile.css").read_text(encoding="utf-8"),
                "heal 后槽须自限高",
            )
            after = [
                f
                for f in scan_layout_contracts(src=fe)
                if f.pattern_id == "abs_in_stretch_slot"
            ]
            self.assertEqual(after, [], f"heal 后仍红: {after}")

    def test_heal_patches_inline_avatar_slot_without_companion(self) -> None:
        """仅有内联 style、无 styles 目录时，仍给 .avatar-slot 打 align-self。"""
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp) / "ws"
            fe = ws / "frontend" / "src" / "views"
            fe.mkdir(parents=True)
            (fe / "Profile.vue").write_text(
                """
<template>
  <section class="card identity af-identity">
    <div class="avatar-slot">
      <el-upload class="avatar-up"><button type="button" class="avatar-btn">换头像</button></el-upload>
    </div>
  </section>
</template>
<style scoped>
.identity { display: flex; align-items: stretch; gap: 12px; }
.avatar-slot { position: relative; flex-shrink: 0; }
.avatar-up { position: absolute; left: 50%; bottom: 0; }
</style>
""",
                encoding="utf-8",
            )
            written = heal_layout_companions_from_baseline(ws)
            self.assertTrue(
                any("Profile" in p for p in written),
                f"应改 Profile 页或 companion，written={written}",
            )
            text = (fe / "Profile.vue").read_text(encoding="utf-8")
            css = ""
            side = fe / "Profile.css"
            if side.is_file():
                css = side.read_text(encoding="utf-8")
            blob = text + "\n" + css
            self.assertRegex(
                blob,
                r"\.avatar-slot\s*\{[^}]*align-self\s*:\s*(?:flex-start|start|center)",
            )
            after = [
                f
                for f in scan_layout_contracts(src=ws / "frontend" / "src")
                if f.pattern_id == "abs_in_stretch_slot"
            ]
            self.assertEqual(after, [], f"heal 后仍红: {after}")

    def test_heal_refreshes_dirty_card_voice_notes(self) -> None:
        """旧 cardVoice 头注释含 § → 回拷基线后不得再被注记扫描命中。"""
        if not BASE_FE.is_dir():
            self.skipTest("baseline missing")
        from app.bake.pack_prune import scan_factory_notes_leaks

        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp) / "ws"
            fe = ws / "frontend" / "src"
            (fe / "styles").mkdir(parents=True)
            (fe / "styles" / "cardVoice.css").write_text(
                "/** §2.5 card_voice 工厂注记 */\n.card { }\n",
                encoding="utf-8",
            )
            self.assertIn(
                "fe:styles/cardVoice.css",
                scan_factory_notes_leaks(ws),
            )
            heal_layout_companions_from_baseline(ws)
            from app.bake.pack_prune import scrub_factory_notes_in_workspace

            scrub_factory_notes_in_workspace(ws)
            self.assertNotIn(
                "fe:styles/cardVoice.css",
                scan_factory_notes_leaks(ws),
                "回拷+抹注记后 cardVoice 不得再漏",
            )


if __name__ == "__main__":
    unittest.main()
