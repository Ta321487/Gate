"""WinError 32：任务失败文案须带文件与重试指引，不能只甩系统原文。"""

from __future__ import annotations

import unittest
from pathlib import Path

from app.services.jobs import _short_error
from app.services.project_disk import (
    format_file_busy_error,
    humanize_job_exception,
    path_from_os_error,
)


class FileBusyHumanizeTests(unittest.TestCase):
    def test_path_from_winerror_text(self) -> None:
        raw = (
            "[WinError 32] 另一个程序正在使用此文件，进程无法访问。: "
            r"'D:\graduate_factory_v3\data\workspace\gf-x\backend\RentalBondStore.java'"
        )
        p = path_from_os_error(OSError(raw))
        self.assertIsNotNone(p)
        assert p is not None
        self.assertEqual(p.name, "RentalBondStore.java")

    def test_humanize_permission_error(self) -> None:
        path = Path(r"D:\graduate_factory_v3\data\workspace\gf-x\RentalBondStore.java")
        err = PermissionError(32, "另一个程序正在使用此文件，进程无法访问。", str(path))
        # winerror on Windows; synthesize for cross-platform
        if getattr(err, "winerror", None) is None:
            err.winerror = 32  # type: ignore[attr-defined]
        text = humanize_job_exception(err)
        self.assertIn("工作区文件被占用", text)
        self.assertIn("RentalBondStore.java", text)
        self.assertIn("从失败步骤重试", text)
        self.assertIn("系统原文", text)

    def test_short_error_enriches_raw_winerror(self) -> None:
        raw = (
            "[WinError 32] 另一个程序正在使用此文件，进程无法访问。: "
            r"'D:\graduate_factory_v3\data\workspace\gf-x\capability\RentalBondStore.java'"
        )
        out = _short_error(raw)
        self.assertIn("工作区文件被占用", out)
        self.assertIn("RentalBondStore.java", out)
        self.assertNotEqual(out, raw)

    def test_already_formatted_passthrough(self) -> None:
        msg = format_file_busy_error(
            Path("RentalBondStore.java"),
            OSError("x"),
            action="删除",
        )
        self.assertEqual(humanize_job_exception(RuntimeError(msg)), msg)


if __name__ == "__main__":
    unittest.main()
