"""可交互控件闸 C1/C2/C3：禁 creatable + 禁手填 + 档案循环须走 ArchiveFieldControl。"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

from app.bake.form_controls_contract import (
    BASELINE_KNOWN_CONTROLS,
    PATTERN_IDS,
    assert_form_controls_ok,
    scan_file_controls,
    scan_form_controls,
)
from app.bake.layout_inventory import frontend_src

_REPO = Path(__file__).resolve().parents[2]


class FormControlsContractTests(unittest.TestCase):
    def test_pattern_catalog(self) -> None:
        self.assertEqual(
            set(PATTERN_IDS),
            {
                "no_select_allow_create",
                "no_input_handfill_temporal",
                "no_input_handfill_numeric",
                "archive_field_loop_uses_control",
            },
        )

    def test_allow_create_reds(self) -> None:
        snippet = """
<template>
  <el-select v-model="form.category" filterable allow-create>
    <el-option label="A" value="A" />
  </el-select>
</template>
"""
        hits = [
            f
            for f in scan_file_controls("probe/bad.vue", snippet)
            if f.pattern_id == "no_select_allow_create"
        ]
        self.assertTrue(hits)
        self.assertEqual(hits[0].detail, "form.category")

    def test_multiline_allow_create_reds(self) -> None:
        snippet = """
<template>
  <el-select
    v-model="collegeFilter"
    filterable
    allow-create
    default-first-option
  >
    <el-option label="计科" value="计科" />
  </el-select>
</template>
"""
        hits = [
            f
            for f in scan_file_controls("probe/multi.vue", snippet)
            if f.pattern_id == "no_select_allow_create"
        ]
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0].detail, "collegeFilter")

    def test_select_without_allow_create_clean(self) -> None:
        """filterable 筛选输入允许；仅 allow-create 造库外值才红。"""
        snippet = """
<template>
  <el-select v-model="form.category" filterable clearable>
    <el-option label="A" value="A" />
  </el-select>
</template>
"""
        hits = [
            f
            for f in scan_file_controls("probe/good.vue", snippet)
            if f.pattern_id == "no_select_allow_create"
        ]
        self.assertEqual(hits, [])

    def test_date_input_handfill_reds(self) -> None:
        snippet = """
<template>
  <el-input v-model="form.expireAt" placeholder="yyyy-MM-dd HH:mm:ss" />
</template>
"""
        hits = [
            f
            for f in scan_file_controls("probe/date.vue", snippet)
            if f.pattern_id == "no_input_handfill_temporal"
        ]
        self.assertTrue(hits)
        self.assertEqual(hits[0].detail, "form.expireAt")

    def test_native_date_type_reds(self) -> None:
        snippet = """
<template>
  <el-input v-model="form.day" type="date" />
</template>
"""
        hits = [
            f
            for f in scan_file_controls("probe/native_date.vue", snippet)
            if f.pattern_id == "no_input_handfill_temporal"
        ]
        self.assertTrue(hits)

    def test_number_input_handfill_reds(self) -> None:
        snippet = """
<template>
  <el-input v-model="form.priceYuan" />
</template>
"""
        hits = [
            f
            for f in scan_file_controls("probe/num.vue", snippet)
            if f.pattern_id == "no_input_handfill_numeric"
        ]
        self.assertTrue(hits)
        self.assertEqual(hits[0].detail, "form.priceYuan")

    def test_input_number_widget_clean(self) -> None:
        """el-input-number 是正解，不得误杀。"""
        snippet = """
<template>
  <el-input-number v-model="form.priceYuan" :min="0" />
  <el-date-picker v-model="form.expireAt" type="datetime" />
</template>
"""
        hits = [
            f
            for f in scan_file_controls("probe/ok_widgets.vue", snippet)
            if f.pattern_id
            in {"no_input_handfill_temporal", "no_input_handfill_numeric"}
        ]
        self.assertEqual(hits, [])

    def test_reason_text_not_date_false_positive(self) -> None:
        """reason/location 以 on 结尾，不得当日期。"""
        snippet = """
<template>
  <el-input v-model="form.reason" />
  <el-input v-model="form.location" />
  <el-input v-model="form.securityQuestion" />
</template>
"""
        hits = [
            f
            for f in scan_file_controls("probe/reason.vue", snippet)
            if f.pattern_id == "no_input_handfill_temporal"
        ]
        self.assertEqual(hits, [])

    def test_label_date_with_plain_input_reds(self) -> None:
        snippet = """
<template>
  <el-form-item label="过期时间">
    <el-input v-model="form.x" />
  </el-form-item>
</template>
"""
        hits = [
            f
            for f in scan_file_controls("probe/label_date.vue", snippet)
            if f.pattern_id == "no_input_handfill_temporal" and f.detail.startswith("label:")
        ]
        self.assertTrue(hits)

    def test_disabled_date_display_clean(self) -> None:
        snippet = """
<template>
  <el-form-item label="日期">
    <el-input :model-value="form.workDate" disabled />
  </el-form-item>
</template>
"""
        hits = [
            f
            for f in scan_file_controls("probe/disabled_date.vue", snippet)
            if f.pattern_id == "no_input_handfill_temporal"
        ]
        self.assertEqual(hits, [])

    def test_archive_field_control_no_allow_create(self) -> None:
        path = frontend_src() / "components" / "ArchiveFieldControl.vue"
        text = path.read_text(encoding="utf-8")
        # 注释可写「禁 creatable」；断言只盯标签属性，避免注释误杀
        stripped = re.sub(r"<!--.*?-->", "", text, flags=re.S)
        self.assertNotRegex(
            stripped,
            r"\ballow-create\b|\ballowCreate\b",
            "ArchiveFieldControl 不得带 allow-create",
        )
        hits = [
            f
            for f in scan_file_controls("components/ArchiveFieldControl.vue", text)
            if f.pattern_id == "no_select_allow_create"
        ]
        self.assertEqual(hits, [])
        self.assertIn("filterable", text)

    def test_archive_loop_without_control_reds(self) -> None:
        snippet = """
<template>
  <el-form-item v-for="f in logFields" :key="f.key" :label="f.label">
    <el-input v-if="f.type === 'textarea'" type="textarea" v-model="payload[f.key]" />
    <el-input v-else v-model="payload[f.key]" />
  </el-form-item>
</template>
"""
        hits = [
            f
            for f in scan_file_controls("probe/log_loop.vue", snippet)
            if f.pattern_id == "archive_field_loop_uses_control"
        ]
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0].detail, "logFields")

    def test_archive_loop_with_control_clean(self) -> None:
        snippet = """
<template>
  <el-form-item v-for="f in extraFields" :key="f.key" :label="f.label">
    <ArchiveFieldControl :field="f" v-model="form[f.key]" />
  </el-form-item>
</template>
"""
        hits = [
            f
            for f in scan_file_controls("probe/extra_ok.vue", snippet)
            if f.pattern_id == "archive_field_loop_uses_control"
        ]
        self.assertEqual(hits, [])

    def test_profile_field_loop_not_in_scope(self) -> None:
        """资料页 visibleFields 不走 ArchiveFieldControl，本模式不扫。"""
        snippet = """
<template>
  <el-form-item v-for="f in visibleFields" :key="f.key">
    <el-input v-model="extras[f.key]" />
  </el-form-item>
</template>
"""
        hits = [
            f
            for f in scan_file_controls("probe/profile.vue", snippet)
            if f.pattern_id == "archive_field_loop_uses_control"
        ]
        self.assertEqual(hits, [])

    def test_baseline_only_known_debt(self) -> None:
        findings = scan_form_controls()
        unexpected = [f for f in findings if f.key() not in BASELINE_KNOWN_CONTROLS]
        self.assertEqual(
            unexpected,
            [],
            "控件契约红灯（真阳性先记 BASELINE_KNOWN_CONTROLS 再消红）:\n"
            + "\n".join(str(f) for f in unexpected[:30]),
        )
        hit = {f.key() for f in findings}
        missing = BASELINE_KNOWN_CONTROLS - hit
        self.assertFalse(
            missing,
            f"已知债未再报（若已修基线请清空对应记账）: {missing}",
        )
        if not BASELINE_KNOWN_CONTROLS:
            self.assertEqual(findings, [], "已知债已空则基线扫描应无红灯")

    def test_assert_ok_with_known(self) -> None:
        assert_form_controls_ok()


if __name__ == "__main__":
    unittest.main()
