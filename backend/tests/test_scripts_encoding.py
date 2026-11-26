r"""scripts/ 编码契约：.bat 纯 ASCII 无 BOM，.ps1 必须 UTF-8 with BOM。

事故来源：2026-11-23 批量重写把 scripts\launcher.ps1 存成 UTF-8 无 BOM，
Windows PowerShell 5.1（launcher.bat 调它）按 GBK 解码，中文标题串把结尾的 `"`
吞成双字节尾字节，字符串不闭合，随后报一串 `缺少 using 指令` / `意外的属性 DllImport`。
运行时的门禁是同目录的 scripts\verify-scripts.ps1（-Fix 可自动补 BOM）。
"""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
BOM = b"\xef\xbb\xbf"


class ScriptsEncodingTest(unittest.TestCase):
    def test_ps1_has_utf8_bom(self):
        missing = []
        for path in sorted(SCRIPTS.glob("*.ps1")):
            data = path.read_bytes()
            if not data.startswith(BOM):
                missing.append(path.name)
            try:
                data.decode("utf-8-sig")
            except UnicodeDecodeError as exc:
                self.fail(f"{path.name} 不是合法 UTF-8：{exc}")
        self.assertEqual(
            missing, [], "这些 .ps1 缺 UTF-8 BOM（5.1 会按 GBK 解码）：" + ", ".join(missing)
        )

    def test_launcher_ps1_keeps_bom(self):
        # 主入口单独钉一次，别被后续批量重写悄悄改回去
        path = SCRIPTS / "launcher.ps1"
        self.assertTrue(path.read_bytes().startswith(BOM), "launcher.ps1 必须带 UTF-8 BOM")

    def test_bat_is_ascii_without_bom(self):
        bad = []
        for path in sorted(SCRIPTS.glob("*.bat")):
            data = path.read_bytes()
            issues = []
            if data.startswith(BOM):
                issues.append("带 BOM")
            if any(b > 0x7F for b in data):
                issues.append("含非 ASCII 字节")
            if issues:
                bad.append(f"{path.name}（{'、'.join(issues)}）")
        self.assertEqual(bad, [], "这些 .bat 不符合约定：" + ", ".join(bad))

    def test_vbs_is_ascii(self):
        bad = []
        for path in sorted(SCRIPTS.glob("*.vbs")):
            if any(b > 0x7F for b in path.read_bytes()):
                bad.append(path.name)
        self.assertEqual(bad, [], "这些 .vbs 含非 ASCII 字节：" + ", ".join(bad))


if __name__ == "__main__":
    unittest.main()
