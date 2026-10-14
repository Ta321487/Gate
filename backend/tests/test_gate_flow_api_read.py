"""门禁读源码：空 file / 目录路径不得 PermissionError。"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.bake.gates.evaluate import _eval_flow_api, _read


class GateFlowApiReadTests(unittest.TestCase):
    def test_read_directory_returns_empty(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp) / "controller"
            d.mkdir()
            self.assertEqual(_read(d), "")
            self.assertEqual(_read(d / ""), "")

    def test_eval_flow_api_empty_file_no_crash(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            be = Path(tmp)
            ctrl = be / "controller"
            ctrl.mkdir()
            (ctrl / "TicketController.java").write_text(
                "public void apply() {}", encoding="utf-8"
            )
            hits = _eval_flow_api(
                be,
                {
                    "broken": {"file": "", "need": ["apply"]},
                    "ok": {"file": "TicketController.java", "need": ["apply"]},
                    "missing": {"file": "NoSuch.java", "need": ["apply"]},
                },
            )
            self.assertFalse(hits["broken"])
            self.assertTrue(hits["ok"])
            self.assertFalse(hits["missing"])


if __name__ == "__main__":
    unittest.main()
