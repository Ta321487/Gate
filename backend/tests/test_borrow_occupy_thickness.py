"""借用/占用组加厚：提前催还域默认、超期限借扫词、PARCEL催领默认、EQUIP用途必填、低库存站内信扫词。"""

from __future__ import annotations

import unittest

from app.bake.domain_schema import attach_accept
from app.bake.domains import DOMAIN_CAPABILITIES
from app.bake.engine_bake import _patch_thesis_yml
from app.bake.runtime_policy import policy_preview as app_policy_preview
from app.bake.ticket_policy import policy_preview
from app.bake.features.core_cap_scan import scan_overdue_freeze
from app.bake.features.stock_io import scan_stock_warn_notify
from app.bake.schema.templates import SCHEMA_BUILDERS


def _spec(domain: str, title: str, body: str = "") -> dict:
    return attach_accept(
        {
            "domain": domain,
            "title": title,
            "capabilities": list(DOMAIN_CAPABILITIES[domain]),
            "features": [],
            "archetype": "ARCH-FLOW",
        },
        body,
    )


class BorrowOccupyThicknessTests(unittest.TestCase):
    def test_parcel_default_deadline(self) -> None:
        caps = DOMAIN_CAPABILITIES["DOM-PARCEL"]
        self.assertIn("deadline", caps)
        out = _spec("DOM-PARCEL", "校园快递驿站", "")
        self.assertIn("deadline", out.get("capabilities") or [])
        ticket = ((out.get("schema") or {}).get("entities") or {}).get("ticket") or {}
        self.assertTrue(ticket.get("slaDeadline"))
        labels = (out.get("schema") or {}).get("labels") or {}
        self.assertEqual(labels.get("deadlineMenuLabel"), "催领")

    def test_library_due_soon_default(self) -> None:
        out = _spec("DOM-LIBRARY", "图书借阅管理系统", "")
        ticket = ((out.get("schema") or {}).get("entities") or {}).get("ticket") or {}
        self.assertTrue(ticket.get("pickLoanPeriod"))
        self.assertEqual(int(ticket.get("dueSoonDays") or 0), 3)
        yml = _patch_thesis_yml("thesis:\n  title: x\n", "DOM-LIBRARY", out) + policy_preview("DOM-LIBRARY", out)
        self.assertIn("ticket-due-soon-days: 3", yml)
        feats = {f.get("name") for f in (out.get("features") or []) if isinstance(f, dict)}
        self.assertIn("即将到期提醒", feats)

    def test_equip_require_remark_default(self) -> None:
        schema = SCHEMA_BUILDERS["DOM-EQUIP"]("实验室设备借用管理系统")
        ticket = (schema.get("entities") or {}).get("ticket") or {}
        self.assertTrue(ticket.get("requireRemark"))
        self.assertEqual(ticket.get("remarkLabel"), "用途说明")
        out = _spec("DOM-EQUIP", "实验室设备借用管理系统", "")
        yml = _patch_thesis_yml("thesis:\n  title: x\n", "DOM-EQUIP", out) + policy_preview("DOM-EQUIP", out)
        self.assertIn("ticket-require-remark: true", yml)

    def test_overdue_freeze_domain_default_library(self) -> None:
        """超期限借：LIBRARY 域默认 maxOverdueTimes=3（信用分双端：用户借还写库 + 管理限制再借）。"""
        self.assertTrue(scan_overdue_freeze("超期达3次限制再借，资格冻结。"))
        bare = _spec("DOM-LIBRARY", "图书借阅", "借阅归还催还。")
        t0 = ((bare.get("schema") or {}).get("entities") or {}).get("ticket") or {}
        self.assertEqual(int(t0.get("maxOverdueTimes") or 0), 3)
        yml = _patch_thesis_yml("thesis:\n  title: x\n", "DOM-LIBRARY", bare) + policy_preview("DOM-LIBRARY", bare)
        self.assertIn("ticket-max-overdue-times: 3", yml)

    def test_stock_warn_notify_scan(self) -> None:
        self.assertTrue(scan_stock_warn_notify("低库存提醒与库存预警通知。"))
        self.assertFalse(scan_stock_warn_notify("物资申领与出入库登记。"))
        bare = _spec("DOM-ASSET", "物资领用", "出入库与库存台账。")
        self.assertFalse(bool((bare.get("schema") or {}).get("stockWarnNotify")))
        hit = _spec("DOM-ASSET", "物资领用", "出入库；低库存提醒站内通知总管。")
        self.assertTrue(bool((hit.get("schema") or {}).get("stockWarnNotify")))
        yml = _patch_thesis_yml("thesis:\n  title: x\n", "DOM-ASSET", hit) + policy_preview("DOM-ASSET", hit) + app_policy_preview("DOM-ASSET", hit)
        self.assertIn("stock-warn-notify: true", yml)

    def test_renew_max_already_with_loan_renew(self) -> None:
        """续借次数上限随 loan_renew 域默认，非待补。"""
        out = _spec("DOM-LIBRARY", "图书借阅", "")
        ticket = ((out.get("schema") or {}).get("entities") or {}).get("ticket") or {}
        self.assertTrue(ticket.get("allowRenew"))
        self.assertGreaterEqual(int(ticket.get("maxRenew") or 0), 1)


if __name__ == "__main__":
    unittest.main()
