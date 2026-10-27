"""任务日志 RUN 锚点与切段（控制台按次查看）。"""

from __future__ import annotations

import json
import shutil
import subprocess
import unittest
from pathlib import Path

from app.services.jobs import RUN_END_MARK, RUN_START_MARK, format_run_end, format_run_start

ROOT = Path(__file__).resolve().parents[2]
PARSE_MJS = Path(__file__).resolve().parent / "fixtures" / "run_job_log_parse.mjs"


def _parse_job_runs(raw: str) -> list[dict]:
    """与 frontend jobLogRuns.js 同口径的最小切段（测锚点契约）。"""
    lines = (raw or "").split("\n")
    cuts: list[int] = []
    for i, line in enumerate(lines):
        if RUN_START_MARK in line or "preview stopped · 生成前已停旧进程" in line:
            if "preview stopped · 生成前已停旧进程" in line and cuts:
                chunk = "\n".join(lines[cuts[-1] : i])
                if RUN_START_MARK in chunk and RUN_END_MARK not in chunk:
                    continue
            cuts.append(i)
    if not cuts:
        return [{"body": raw.strip(), "outcome": "UNKNOWN"}] if raw.strip() else []
    if cuts[0] > 0 and "\n".join(lines[: cuts[0]]).strip():
        cuts[0] = 0
    out = []
    for idx, start in enumerate(cuts):
        end = cuts[idx + 1] if idx + 1 < len(cuts) else len(lines)
        body = "\n".join(lines[start:end]).rstrip()
        outcome = "RUNNING"
        if f"{RUN_END_MARK} · SUCCESS" in body or "SUCCESS · zip unlocked" in body:
            outcome = "SUCCESS"
        elif f"{RUN_END_MARK} · GATE_FAIL" in body or "GATE FAIL ·" in body:
            outcome = "GATE_FAIL"
        elif f"{RUN_END_MARK} · FAIL" in body or "] ERROR " in body or body.endswith("ERROR"):
            outcome = "FAIL"
        elif f"{RUN_END_MARK} · CANCELLED" in body:
            outcome = "CANCELLED"
        out.append({"body": body, "outcome": outcome})
    return out


class JobLogRunMarkersTest(unittest.TestCase):
    def test_format_markers(self):
        self.assertIn("job=42", format_run_start(42))
        self.assertTrue(format_run_start(42).startswith(RUN_START_MARK))
        self.assertEqual(format_run_end("SUCCESS"), f"{RUN_END_MARK} · SUCCESS ========")
        self.assertIn("FAIL · boom", format_run_end("FAIL", "boom\nmore"))

    def test_split_anchored_runs(self):
        raw = "\n".join(
            [
                "[10-13 15:36:03] ======== RUN start · job=1 ========",
                "[10-13 15:36:03] preview stopped · 生成前已停旧进程",
                "[10-13 15:36:24] SUCCESS · zip unlocked",
                "[10-13 15:36:24] ======== RUN end · SUCCESS ========",
                "[10-14 23:18:32] ======== RUN start · job=2 ========",
                "[10-14 23:18:32] preview stopped · 生成前已停旧进程",
                "[10-14 23:21:20] ERROR 编译失败",
                "[10-14 23:21:20] ======== RUN end · FAIL · 编译失败 ========",
            ]
        )
        runs = _parse_job_runs(raw)
        self.assertEqual(len(runs), 2)
        self.assertEqual(runs[0]["outcome"], "SUCCESS")
        self.assertEqual(runs[1]["outcome"], "FAIL")
        self.assertIn("job=1", runs[0]["body"])
        self.assertIn("job=2", runs[1]["body"])

    def test_legacy_preview_stopped_split(self):
        raw = "\n".join(
            [
                "[10-13 15:36:03] preview stopped · 生成前已停旧进程",
                "[10-13 15:36:24] SUCCESS · zip unlocked",
                "[10-14 23:18:32] preview stopped · 生成前已停旧进程",
                "[10-14 23:21:20] SUCCESS · zip unlocked",
            ]
        )
        runs = _parse_job_runs(raw)
        self.assertEqual(len(runs), 2)
        self.assertEqual(runs[0]["outcome"], "SUCCESS")
        self.assertEqual(runs[1]["outcome"], "SUCCESS")

    @unittest.skipUnless(shutil.which("node"), "需要 node")
    def test_frontend_parse_job_runs_parity(self):
        """切段真源是 frontend jobLogRuns.js，pytest 内联解析仅作契约备份。"""
        raw = "\n".join(
            [
                "[10-13 15:36:03] ======== RUN start · job=1 ========",
                "[10-13 15:36:24] SUCCESS · zip unlocked",
                "[10-13 15:36:24] ======== RUN end · SUCCESS ========",
                "[10-14 23:18:32] ======== RUN start · job=2 ========",
                "[10-14 23:21:20] ERROR 编译失败",
                "[10-14 23:21:20] ======== RUN end · FAIL · 编译失败 ========",
            ]
        )
        proc = subprocess.run(
            ["node", str(PARSE_MJS)],
            input=raw,
            capture_output=True,
            text=True,
            encoding="utf-8",
            cwd=str(ROOT),
            timeout=15,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr or proc.stdout)
        runs = json.loads(proc.stdout)
        self.assertEqual(len(runs), 2)
        self.assertEqual(runs[0]["outcome"], "SUCCESS")
        self.assertEqual(runs[1]["outcome"], "FAIL")
        py = _parse_job_runs(raw)
        self.assertEqual([r["outcome"] for r in py], [r["outcome"] for r in runs])


if __name__ == "__main__":
    unittest.main()
