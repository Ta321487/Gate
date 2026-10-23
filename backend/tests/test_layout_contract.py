"""起包前布局闸 D2：结构契约（一眼病模式再犯必红；不改学生页消红）。"""

from __future__ import annotations

import unittest

from app.bake.layout_contract import (
    BASELINE_KNOWN_CONTRACTS,
    PATTERN_IDS,
    scan_file_contracts,
    scan_layout_contracts,
)


_BAD_SNIPPETS: dict[str, str] = {
    "no_status_acts_same_wrap": """
<template>
  <div class="row flex-wrap">
    <StatusChip tone="ok" />
    <el-button type="primary">通过</el-button>
    <el-button>驳回</el-button>
  </div>
</template>
""",
    "toolbar_layers": """
<template>
  <div class="toolbar"><el-button>查</el-button></div>
  <div class="toolbar"><el-button>导出</el-button></div>
</template>
""",
    "primary_cta_in_slot": """
<template>
  <el-button type="primary" style="position:absolute;top:0;right:0">提交</el-button>
</template>
""",
    "row_actions_column": """
<template>
  <el-table>
    <el-table-column label="混合">
      <template #default="{ row }">
        <StatusChip :tone="row.status" />
        <el-button link>通过</el-button>
      </template>
    </el-table-column>
  </el-table>
</template>
""",
    "actions_may_wrap_or_menu": """
<template>
  <div class="table-ops">
    <el-button link>1</el-button>
    <el-button link>2</el-button>
    <el-button link>3</el-button>
    <el-button link>4</el-button>
    <el-button link>5</el-button>
  </div>
</template>
""",
    "no_orphan_absolute_btn": """
<template>
  <el-button style="position:absolute;left:0">漂</el-button>
</template>
""",
    "dialog_body_scroll": """
<template>
  <el-dialog v-model="vis" title="表">
    <el-table :data="list" />
  </el-dialog>
</template>
""",
}


_GOOD_SNIPPETS: dict[str, str] = {
    "no_status_acts_same_wrap": """
<template>
  <div class="row">
    <div class="status-line"><StatusChip tone="ok" /></div>
    <div class="table-ops flex-wrap">
      <el-button type="primary">通过</el-button>
    </div>
  </div>
</template>
""",
    "actions_may_wrap_or_menu": """
<template>
  <div class="table-ops" style="flex-wrap:wrap">
    <el-button link>1</el-button>
    <el-button link>2</el-button>
    <el-button link>3</el-button>
    <el-button link>4</el-button>
    <el-button link>5</el-button>
  </div>
</template>
""",
    "dialog_body_scroll": """
<template>
  <el-dialog v-model="vis" title="表">
    <div class="table-scroll"><el-table :data="list" /></div>
  </el-dialog>
</template>
""",
    "row_actions_column": """
<template>
  <el-table>
    <el-table-column label="状态"><template #default><StatusChip /></template></el-table-column>
    <el-table-column label="操作">
      <template #default>
        <div class="table-ops"><el-button link>通过</el-button></div>
      </template>
    </el-table-column>
  </el-table>
</template>
""",
}


class LayoutContractD2Tests(unittest.TestCase):
    def test_pattern_catalog_complete(self) -> None:
        self.assertEqual(
            set(PATTERN_IDS),
            set(_BAD_SNIPPETS),
            "§3.2 七模式须人人有反例片段",
        )

    def test_each_pattern_reds_on_bad_snippet(self) -> None:
        for pid, snippet in _BAD_SNIPPETS.items():
            with self.subTest(pid=pid):
                hits = [
                    f
                    for f in scan_file_contracts(f"probe/{pid}.vue", snippet)
                    if f.pattern_id == pid
                ]
                self.assertTrue(hits, f"{pid} 反例未红")

    def test_good_snippets_clean(self) -> None:
        for pid, snippet in _GOOD_SNIPPETS.items():
            with self.subTest(pid=pid):
                hits = [
                    f
                    for f in scan_file_contracts(f"probe/good_{pid}.vue", snippet)
                    if f.pattern_id == pid
                ]
                self.assertEqual(hits, [], f"{pid} 误杀好例: {hits}")

    def test_css_class_absolute_primary_reds(self) -> None:
        """机器爱写 class + CSS absolute，不能只挡 inline。"""
        snippet = """
<template>
  <el-button type="primary" class="float-cta">提交</el-button>
</template>
<style>
.float-cta { position: absolute; top: 0; right: 0; }
</style>
"""
        hits = [
            f
            for f in scan_file_contracts("probe/css_abs_primary.vue", snippet)
            if f.pattern_id == "primary_cta_in_slot"
        ]
        self.assertTrue(hits, "CSS class absolute 主 CTA 未红")

    def test_css_class_absolute_orphan_reds(self) -> None:
        snippet = """
<template>
  <el-button class="drift-btn">漂</el-button>
</template>
<style>
.card .drift-btn { position: absolute; left: 0; }
</style>
"""
        hits = [
            f
            for f in scan_file_contracts("probe/css_abs_orphan.vue", snippet)
            if f.pattern_id == "no_orphan_absolute_btn"
        ]
        self.assertTrue(hits, "CSS class absolute 业务钮未红")

    def test_css_absolute_on_non_button_clean(self) -> None:
        """装饰点/轨道 absolute 不挂 el-button → 不误杀。"""
        snippet = """
<template>
  <div class="fab-dot"></div>
  <el-button type="primary">提交</el-button>
</template>
<style>
.fab-dot { position: absolute; top: 0; }
.hero-track { position: fixed; inset: 0; }
</style>
"""
        hits = [
            f
            for f in scan_file_contracts("probe/css_abs_deco.vue", snippet)
            if f.pattern_id in {"primary_cta_in_slot", "no_orphan_absolute_btn"}
        ]
        self.assertEqual(hits, [], f"装饰 absolute 误杀按钮: {hits}")

    def test_companion_css_absolute_reds(self) -> None:
        """同页 .css companion 也要扫到。"""
        vue = """
<template>
  <el-button type="primary" class="side-float">去结算</el-button>
</template>
"""
        hits = [
            f
            for f in scan_file_contracts(
                "probe/side_float.vue",
                vue,
                extra_css=".side-float { position: absolute; right: 8px; }",
            )
            if f.pattern_id == "primary_cta_in_slot"
        ]
        self.assertTrue(hits, "companion .css absolute 未红")

    def test_baseline_only_known_debt(self) -> None:
        findings = scan_layout_contracts()
        unexpected = [f for f in findings if f.key() not in BASELINE_KNOWN_CONTRACTS]
        self.assertEqual(
            unexpected,
            [],
            "非预期结构红灯（本刀不改页；真阳性请记入 BASELINE_KNOWN_CONTRACTS）:\n"
            + "\n".join(str(f) for f in unexpected[:30]),
        )
        # 已知债必须仍被扫到，避免静默放过
        hit = {f.key() for f in findings}
        missing = BASELINE_KNOWN_CONTRACTS - hit
        self.assertFalse(
            missing,
            f"已知债未再报（若已修基线请清空 BASELINE_KNOWN_CONTRACTS）: {missing}",
        )


if __name__ == "__main__":
    unittest.main()
