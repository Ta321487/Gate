"""Q-06：S/P/C 样例开题库存（每个 ID 至少 1 份 data/samples）。"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

SAMPLES = Path(__file__).resolve().parents[2] / "data" / "samples"

# C-05～C-10 为能力挂载，样例落在对应 P-*（非独立 C-*.txt）
_C_COVERED_BY_P = {
    5: ("P-09", "P-10", "P-11"),
    6: ("P-14",),
    7: ("P-19",),
    8: ("P-20", "P-21"),
    9: ("P-17",),
    10: ("P-22",),
}


def _ids_from_glob(pattern: str, prefix: str) -> set[int]:
    found: set[int] = set()
    rx = re.compile(rf"{re.escape(prefix)}-(\d+)")
    for path in SAMPLES.rglob(pattern):
        m = rx.search(path.name)
        if m:
            found.add(int(m.group(1)))
    return found


class SampleInventoryQ06Tests(unittest.TestCase):
    def test_s_skin_samples_complete(self) -> None:
        """S-01～S-74 深皮样例（编号不连续，以深皮开题目录为准）。"""
        root = SAMPLES / "深皮开题"
        self.assertTrue(root.is_dir(), root)
        files = list(root.glob("S-*.txt"))
        self.assertGreaterEqual(len(files), 51, f"got {len(files)}")
        ids = _ids_from_glob("S-*.txt", "S")
        # 册内已知段：01-06, 10-25, 30-36, 40-50, 60-65, 70-74
        expected = (
            set(range(1, 7))
            | set(range(10, 26))
            | set(range(30, 37))
            | set(range(40, 51))
            | set(range(60, 66))
            | set(range(70, 75))
        )
        self.assertEqual(ids, expected, f"missing={sorted(expected - ids)} extra={sorted(ids - expected)}")

    def test_p_preset_samples_complete(self) -> None:
        """P-01～P-29 各 ≥1（P-30 为三联 reject，无独立样例）。"""
        ids = _ids_from_glob("P-*.txt", "P")
        expected = set(range(1, 30))
        self.assertEqual(ids, expected, f"missing={sorted(expected - ids)}")

    def test_c_capability_samples_or_p_cover(self) -> None:
        """C-01～C-18：独立样例或由挂载 P 样例覆盖。"""
        c_ids = _ids_from_glob("C-*.txt", "C")
        p_ids = _ids_from_glob("P-*.txt", "P")
        for cid in range(1, 19):
            with self.subTest(C=cid):
                if cid in c_ids:
                    continue
                covers = _C_COVERED_BY_P.get(cid)
                self.assertIsNotNone(covers, f"C-{cid:02d} missing sample and no P cover map")
                ok = any(int(p[2:]) in p_ids for p in (covers or ()))
                self.assertTrue(ok, f"C-{cid:02d} needs one of {covers}")


if __name__ == "__main__":
    unittest.main()
