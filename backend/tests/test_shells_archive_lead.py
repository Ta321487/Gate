"""myArchivePageLead 按域措辞，避免论坛文案套进 CRM 等。"""

from __future__ import annotations

import unittest

from app.bake.schema.shells import _my_archive_page_lead


class MyArchivePageLeadTests(unittest.TestCase):
    def test_crm_uses_followup_wording(self) -> None:
        lead = _my_archive_page_lead("DOM-CRM", "客户")
        self.assertIn("登记", lead)
        self.assertIn("结案", lead)
        self.assertNotIn("站长", lead)
        self.assertNotIn("下架", lead)

    def test_carpool_uses_departure_takedown(self) -> None:
        lead = _my_archive_page_lead("DOM-CARPOOL", "行程")
        self.assertIn("过出发自动下架", lead)
        self.assertNotIn("站长", lead)

    def test_forum_keeps_moderator_wording(self) -> None:
        lead = _my_archive_page_lead("DOM-FORUM", "主帖")
        self.assertIn("站长下架", lead)


if __name__ == "__main__":
    unittest.main()
