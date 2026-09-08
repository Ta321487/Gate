"""能力扩岛 E-07：码二维码出示 code_qr（开题扫词才挂，无域默认）。"""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from app.bake.capabilities import CAPABILITIES
from app.bake.domain_schema import attach_accept
from app.bake.domains import DOMAIN_CAPABILITIES
from app.bake.features.code_qr import (
    CODE_QR_CAP,
    merge_code_qr_capabilities,
    scan_code_qr,
)

ROOT = Path(__file__).resolve().parents[2]
BASELINE = ROOT / "skeletons" / "baseline"


class CodeQrE07Tests(unittest.TestCase):
    def test_capability_registered_no_domain_default(self) -> None:
        self.assertEqual(CAPABILITIES[CODE_QR_CAP]["status"], "implemented")
        for dom in ("DOM-VISITOR", "DOM-CARPASS", "DOM-PARCEL"):
            self.assertNotIn(CODE_QR_CAP, DOMAIN_CAPABILITIES.get(dom) or [], dom)

    def test_scan_terms(self) -> None:
        self.assertTrue(scan_code_qr("通过后支持通行码二维码出示。"))
        self.assertTrue(scan_code_qr("取件码二维码扫码出示。"))
        self.assertFalse(scan_code_qr("访客登记与通行码字符串。"))

    def test_merge_and_attach(self) -> None:
        base = list(DOMAIN_CAPABILITIES["DOM-VISITOR"])
        no = merge_code_qr_capabilities(base, "访客登记通行码。", domain="DOM-VISITOR")
        self.assertNotIn(CODE_QR_CAP, no)
        yes = merge_code_qr_capabilities(
            base, "访客登记；支持二维码出示。", domain="DOM-VISITOR"
        )
        self.assertIn(CODE_QR_CAP, yes)

        plain = attach_accept(
            {
                "domain": "DOM-VISITOR",
                "title": "访客登记",
                "capabilities": list(DOMAIN_CAPABILITIES["DOM-VISITOR"]),
                "archetype": "ARCH-FLOW",
            },
            "访客预约与通行码。",
        )
        self.assertNotIn(CODE_QR_CAP, plain.get("capabilities") or [])

        rich = attach_accept(
            {
                "domain": "DOM-VISITOR",
                "title": "访客登记",
                "capabilities": list(DOMAIN_CAPABILITIES["DOM-VISITOR"]),
                "archetype": "ARCH-FLOW",
            },
            "访客预约；通行码二维码出示。",
        )
        self.assertIn(CODE_QR_CAP, rich.get("capabilities") or [])
        labels = (rich.get("schema") or {}).get("labels") or {}
        self.assertIn("出示", str(labels.get("codeQrShowVerb") or "出示"))
        self.assertNotIn("演示", str(labels.get("codeQrHint") or ""))
        self.assertNotIn("闸机硬件联动", str(labels.get("codeQrHint") or ""))

    def test_baseline_fe_and_dep(self) -> None:
        pkg = json.loads(
            (BASELINE / "frontend/package.json").read_text(encoding="utf-8")
        )
        self.assertIn("qrcode", pkg.get("dependencies") or {})
        util = BASELINE / "frontend/src/utils/codeQr.js"
        comp = BASELINE / "frontend/src/components/CodeQrBlock.vue"
        my = BASELINE / "frontend/src/views/user/MyTickets.vue"
        self.assertTrue(util.is_file())
        self.assertTrue(comp.is_file())
        text = my.read_text(encoding="utf-8")
        self.assertIn("CodeQrBlock", text)
        self.assertIn("code_qr", text)
        self.assertIn("不对接闸机", text)


if __name__ == "__main__":
    unittest.main()
