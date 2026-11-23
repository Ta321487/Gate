"""编号合同 D1/D3：学生包可见号走 BizCodeIssuer；禁散落 nanoTime/Random。"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "skeletons" / "baseline" / "backend" / "src" / "main" / "java" / "com" / "thesis"
MYBATIS = (
    ROOT
    / "skeletons"
    / "overlays"
    / "persistence-mybatis"
    / "backend"
    / "src"
    / "main"
    / "java"
    / "com"
    / "thesis"
)
JPA = (
    ROOT
    / "skeletons"
    / "overlays"
    / "persistence-jpa"
    / "backend"
    / "src"
    / "main"
    / "java"
    / "com"
    / "thesis"
)

ISSUER = BASE / "common" / "BizCodeIssuer.java"

# 签发点文件：必须引用 BizCodeIssuer，且正文不得再散落 nanoTime / Math.random*100000
ISSUE_FILES = [
    BASE / "capability" / "TicketApproveOps.java",
    MYBATIS / "capability" / "TicketApproveOps.java",
    BASE / "capability" / "OrderStore.java",
    MYBATIS / "capability" / "OrderStore.java",
    JPA / "capability" / "OrderStore.java",
    BASE / "capability" / "SlotStore.java",
    MYBATIS / "capability" / "SlotStore.java",
    JPA / "capability" / "SlotStore.java",
    BASE / "capability" / "DigitalGoodsStore.java",
    MYBATIS / "capability" / "DigitalGoodsStore.java",
    JPA / "capability" / "DigitalGoodsStore.java",
]

FORBIDDEN = re.compile(
    r"System\.nanoTime\s*\(|Math\.random\s*\(\s*\)\s*\*\s*100000"
)
REQUIRED_CALLS = (
    "BizCodeIssuer.certIssueNo",
    "BizCodeIssuer.pickupRedeemCode",
    "BizCodeIssuer.verifyCode",
    "BizCodeIssuer.passCode",
    "BizCodeIssuer.pickupFromOrderId",
    "BizCodeIssuer.memberCheckinToken",
    "BizCodeIssuer.orderShareToken",
    "BizCodeIssuer.permitCode",
    "BizCodeIssuer.activationCode",
)


class BizCodeIssuerContractTests(unittest.TestCase):
    def test_issuer_home_exists(self) -> None:
        self.assertTrue(ISSUER.is_file(), "缺 BizCodeIssuer.java（编号合同 C 层家）")
        text = ISSUER.read_text(encoding="utf-8")
        self.assertIn("certIssueNo", text)
        self.assertIn("pickupRedeemCode", text)
        self.assertIn("nextBody", text)

    def test_issue_sites_use_issuer_no_scatter(self) -> None:
        missing = [str(p) for p in ISSUE_FILES if not p.is_file()]
        self.assertFalse(missing, f"缺签发点文件: {missing}")
        for path in ISSUE_FILES:
            text = path.read_text(encoding="utf-8")
            self.assertIn(
                "BizCodeIssuer",
                text,
                f"{path.name} 未引用 BizCodeIssuer",
            )
            bad = FORBIDDEN.search(text)
            self.assertIsNone(
                bad,
                f"{path} 仍散落 nanoTime/Random: {bad.group(0) if bad else ''}",
            )

    def test_required_call_sites_present(self) -> None:
        blob = "\n".join(p.read_text(encoding="utf-8") for p in ISSUE_FILES if p.is_file())
        for call in REQUIRED_CALLS:
            self.assertIn(call, blob, f"签发家方法未被调用: {call}")

    def test_d3_cert_feature_claims_have_column_and_issuer(self) -> None:
        """宣称开具流水号 → 列 + TicketApprove 走签发家（假宣称闸底线）。"""
        schema = (ROOT / "skeletons" / "baseline" / "sql" / "schema.sql").read_text(
            encoding="utf-8"
        )
        # 列由 thicken/ensure 挂；此处钉签发家与 ApproveOps 接线
        approve = (BASE / "capability" / "TicketApproveOps.java").read_text(
            encoding="utf-8"
        )
        self.assertIn("issueCertIssueNoIfNeeded", approve)
        self.assertIn("BizCodeIssuer.certIssueNo()", approve)
        self.assertIn("cert_issue_no", approve)
        # 策略开关名存在（开则 bake 出列）
        policy = (BASE / "config" / "TicketPolicy.java").read_text(encoding="utf-8")
        self.assertIn("ALLOW_CERT_ISSUE_NO", policy)
        _ = schema  # 列随域挂，不在裸 schema 强求


if __name__ == "__main__":
    unittest.main()
