"""运营控制台写后 UI 契约（产品化 A1～A4）。

静态钉：合卷/验圈/清洗/匹配解锁/启停不得「成功 = await 全量 load」；
busy 不得拖住权威 getDeliveryReview；重写操作超时 ≥120s。
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FE = ROOT / "frontend" / "src"
PANE = FE / "components" / "DeliveryReviewPane.vue"
DETAIL = FE / "views" / "projectDetail" / "useProjectDetail.js"
RUNTIME = FE / "views" / "projectDetail" / "usePdRuntime.js"
API = FE / "api.js"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _fn_body(src: str, name: str) -> str:
    """取 async function name(...) { ... } 顶层函数体（花括号配对）。"""
    m = re.search(rf"async function {re.escape(name)}\s*\(", src)
    if not m:
        raise AssertionError(f"missing async function {name}")
    i = src.find("{", m.end())
    if i < 0:
        raise AssertionError(f"no body for {name}")
    depth = 0
    for j in range(i, len(src)):
        if src[j] == "{":
            depth += 1
        elif src[j] == "}":
            depth -= 1
            if depth == 0:
                return src[i : j + 1]
    raise AssertionError(f"unbalanced body for {name}")


class ConsoleWriteAfterContractTest(unittest.TestCase):
    def test_repack_patches_zip_stale_false_before_refresh(self):
        body = _fn_body(_read(PANE), "onRepack")
        self.assertIn("zip_stale: false", body)
        # 写成功后 busy 已消，再后台 refreshAfter（禁止 await 拖住 finally）
        self.assertRegex(body, r"finally\s*\{[^}]*busy\.value\s*=\s*['\"]['\"]")
        self.assertIn("if (wroteOk) void refreshAfter()", body)
        self.assertNotIn("await refreshAfter()", body)

    def test_verify_apply_then_background_refresh(self):
        body = _fn_body(_read(PANE), "onVerify")
        self.assertIn("applyFromWrite(", body)
        self.assertIn("if (wroteOk) void refreshAfter()", body)
        self.assertNotIn("await refreshAfter()", body)

    def test_scrub_busy_cleared_before_authority_refresh(self):
        body = _fn_body(_read(DETAIL), "scrubStudentCopy")
        self.assertIn("applyDeliveryReviewPanel(", body)
        self.assertIn("zip_stale: true", body)
        self.assertIn("void refreshDeliveryReviewPanel()", body)
        # 权威拉不得在 finally 清 busy 之前 await
        self.assertNotRegex(
            body,
            r"await refreshDeliveryReviewPanel\(\)[\s\S]*?finally",
        )

    def test_match_unlock_uses_patch_response_not_full_load(self):
        body = _fn_body(_read(DETAIL), "toggleUnlock")
        self.assertIn("api.patchMatch(", body)
        self.assertIn("p.value = await api.patchMatch", body)
        self.assertNotIn("await load(", body)
        self.assertNotIn("await reload(", body)

    def test_runtime_busy_not_bound_to_settle_loop(self):
        src = _read(RUNTIME)
        body = _fn_body(src, "rtAction")
        self.assertIn("api.runtimeAction(", body)
        self.assertIn("refreshRuntime(", body)
        # 禁止写请求后 while+deadline 长轮询拖住 busy
        self.assertNotIn("while (Date.now() < deadline", body)
        self.assertIn("rtSettling", src)

    def test_heavy_write_timeouts_at_least_120s(self):
        src = _read(API)
        need = {
            "getDeliveryReview": 120000,
            "verifyDeliveryReview": 120000,
            "repackDeliveryReview": 120000,
            "scrubStudentCopy": 120000,
            "runtimeAction": 120000,
            "putOverrides": 120000,
            "getProposalDiff": 120000,
            "failAnalysisClassifyAssist": 120000,
        }
        for key, min_ms in need.items():
            # 取该键所在对象方法片段至下一顶层键或结尾
            m = re.search(
                rf"{re.escape(key)}\s*:\s*\([^)]*\)\s*=>\s*([\s\S]*?)(?=\n\s{2}\w+\s*:|\n\}})",
                src,
            )
            self.assertIsNotNone(m, f"api.{key} missing")
            chunk = m.group(1)
            tm = re.search(r"timeout:\s*(\d+)", chunk)
            self.assertIsNotNone(tm, f"api.{key} missing timeout")
            self.assertGreaterEqual(
                int(tm.group(1)),
                min_ms,
                f"api.{key} timeout {tm.group(1)} < {min_ms}",
            )

    def test_timeout_copy_mentions_server_may_have_succeeded(self):
        pane = _read(PANE)
        self.assertIn("服务端可能已成功", pane)
        detail = _read(DETAIL)
        self.assertIn("服务端可能已成功", detail)
        runtime = _read(RUNTIME)
        self.assertIn("服务端可能已受理", runtime)


if __name__ == "__main__":
    unittest.main()
