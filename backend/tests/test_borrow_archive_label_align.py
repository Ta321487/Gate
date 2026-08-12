"""借用/占用组：档案 author/isbn 的 UI 标签须与物理列 ER 中文一致。"""

from __future__ import annotations

import unittest

from app.bake.archive_columns import archive_column_spec_for
from app.bake.domain_schema import build_domain_schema
from app.bake.schema.er_labels import _col_zh
from app.bake.schema.er_zh import _COMMON_COL_ZH

# HANDOFF 组 A + 收口簇占用域 CINEMA（共 47）
BORROW_OCCUPY_DOMAINS = (
    "DOM-LIBRARY",
    "DOM-EQUIP",
    "DOM-ASSET",
    "DOM-CRM",
    "DOM-EVENT",
    "DOM-ATTEND",
    "DOM-FUND",
    "DOM-LABSAFE",
    "DOM-RECRUIT",
    "DOM-GRADE",
    "DOM-INTERN",
    "DOM-PARCEL",
    "DOM-SEAL",
    "DOM-FLEET",
    "DOM-CERT",
    "DOM-PROMO",
    "DOM-FITOUT",
    "DOM-ACAD",
    "DOM-TRIP",
    "DOM-EXPENSE",
    "DOM-CREDIT",
    "DOM-LABOR",
    "DOM-EVAL",
    "DOM-MORAL",
    "DOM-AWARD",
    "DOM-BED",
    "DOM-CHECKIN",
    "DOM-MUTUAL-TUTOR",
    "DOM-MUTUAL-TOPIC",
    "DOM-MUTUAL-TEAM",
    "DOM-VISITOR",
    "DOM-CARPASS",
    "DOM-LISTING",
    "DOM-PROCURE",
    "DOM-CLUB",
    "DOM-PROJ",
    "DOM-ETHIC",
    "DOM-PARTY",
    "DOM-CONTRACT",
    "DOM-INSTRUMENT",
    "DOM-EXAM",
    "DOM-SURVEY",
    "DOM-VOTE",
    "DOM-DOCLIB",
    "DOM-CARPOOL",
    "DOM-TIMEBANK",
    "DOM-CINEMA",
)


class BorrowArchiveLabelAlignTests(unittest.TestCase):
    def test_group_size(self) -> None:
        self.assertEqual(len(BORROW_OCCUPY_DOMAINS), 47)

    def test_preset_labels_match_er_physical_cols(self) -> None:
        """默认 thesis_test schema；开题深皮换词可不与 ER 同字。"""
        for domain in BORROW_OCCUPY_DOMAINS:
            with self.subTest(domain=domain):
                (author_col, _), (isbn_col, _) = archive_column_spec_for(domain)
                schema = build_domain_schema("thesis_test", domain)
                fields = {
                    f.get("key"): f.get("label")
                    for f in ((schema.get("entities") or {}).get("archive") or {}).get("fields")
                    or []
                }
                ui_author, ui_isbn = fields.get("author"), fields.get("isbn")
                self.assertIsNotNone(ui_author, f"{domain} missing author field")
                self.assertIsNotNone(ui_isbn, f"{domain} missing isbn field")
                er_author = _col_zh(author_col, "archive", dict(_COMMON_COL_ZH), {}, {})
                er_isbn = _col_zh(isbn_col, "archive", dict(_COMMON_COL_ZH), {}, {})
                self.assertEqual(
                    ui_author,
                    er_author,
                    f"{domain} author: UI={ui_author!r} ER={er_author!r} col={author_col}",
                )
                self.assertEqual(
                    ui_isbn,
                    er_isbn,
                    f"{domain} isbn: UI={ui_isbn!r} ER={er_isbn!r} col={isbn_col}",
                )

    def test_bed_and_checkin_do_not_share_isbn_physical_col(self) -> None:
        """床位「布局说明」与查寝「房型说明」不得共用同一物理列名。"""
        (_, _), (bed_isbn, _) = archive_column_spec_for("DOM-BED")
        (_, _), (checkin_isbn, _) = archive_column_spec_for("DOM-CHECKIN")
        self.assertEqual(bed_isbn, "layout_note")
        self.assertEqual(checkin_isbn, "room_note")
        self.assertNotEqual(bed_isbn, checkin_isbn)

    def test_visitor_carpass_not_generic_subtitle(self) -> None:
        for domain, want in (
            ("DOM-VISITOR", ("zone_place", "receive_note")),
            ("DOM-CARPASS", ("dept_name", "note_hint")),
        ):
            with self.subTest(domain=domain):
                (a, _), (i, _) = archive_column_spec_for(domain)
                self.assertEqual((a, i), want)


if __name__ == "__main__":
    unittest.main()
