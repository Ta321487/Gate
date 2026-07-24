"""Characterization: domain SQL must not carry cross-domain fulfillment columns."""

from __future__ import annotations

import re
import unittest

from app.bake.engine import domain_sql

_CREATE_RE = re.compile(
    r"CREATE TABLE IF NOT EXISTS\s+(\w+)\s*\((.*?)\)\s*;",
    re.IGNORECASE | re.DOTALL,
)


def _table_cols(sql: str, table: str) -> set[str]:
    for m in _CREATE_RE.finditer(sql):
        if m.group(1).lower() != table.lower():
            continue
        body = m.group(2)
        cols: set[str] = set()
        for line in body.splitlines():
            mm = re.match(r"\s*(\w+)\s+", line.strip())
            if mm:
                cols.add(mm.group(1).lower())
        return cols
    return set()


class DomainColumnForbidTests(unittest.TestCase):
    """毕设交付：禁止跨域业务列出现在不相关域的 schema 中。"""

    def test_reservation_no_cross_domain(self) -> None:
        cases = {
            "DOM-PARKING": {"plate_no", "entry_at"},
            "DOM-HOSPITAL": {"patient_name", "visit_type", "symptom_note", "queue_no"},
            "DOM-MEETING": {"subject", "party_size"},
            "DOM-HOTEL": {"guest_name", "guest_count"},
            "DOM-SALON": {"preferred_stylist", "queue_no"},
        }
        all_extras = {
            "plate_no",
            "patient_name",
            "visit_type",
            "symptom_note",
            "subject",
            "party_size",
            "guest_name",
            "guest_count",
            "preferred_stylist",
            "queue_no",
            "entry_at",
        }
        for domain, allow in cases.items():
            with self.subTest(domain=domain):
                sql = domain_sql(domain, "thesis_test")
                cols = _table_cols(sql, "reservation")
                self.assertTrue(cols, f"{domain} missing reservation")
                forbidden = all_extras - allow
                hit = cols & forbidden
                self.assertFalse(hit, f"{domain} reservation has cross-domain cols: {hit}")
                missing = allow - cols
                self.assertFalse(missing, f"{domain} reservation missing: {missing}")

    def test_generic_reserve_has_no_extras(self) -> None:
        sql = domain_sql("DOM-GENERIC", "thesis_test", archetype="ARCH-RESERVE")
        cols = _table_cols(sql, "reservation")
        extras = {
            "plate_no",
            "patient_name",
            "preferred_stylist",
            "guest_name",
            "subject",
        }
        self.assertFalse(cols & extras, f"GENERIC reserve extras: {cols & extras}")

    def test_order_no_cross_domain(self) -> None:
        cases = {
            "DOM-SHOP": {
                "allow": {
                    "receiver_name",
                    "receiver_phone",
                    "address_line",
                    "delivery_type",
                    "tracking_no",
                    "pickup_code",
                    "shipped_at",
                    "refund_status",
                },
                "forbid": {"taste_note", "reservation_id"},
            },
            "DOM-FOOD": {
                "allow": {
                    "receiver_name",
                    "taste_note",
                    "pickup_code",
                    "shipped_at",
                    "delivery_type",
                    "refund_status",
                },
                "forbid": {"tracking_no", "reservation_id"},
            },
            "DOM-HOTEL": {
                "allow": {"reservation_id", "refund_status"},
                "forbid": {
                    "taste_note",
                    "pickup_code",
                    "tracking_no",
                    "receiver_name",
                    "delivery_type",
                    "address_line",
                },
            },
        }
        for domain, spec in cases.items():
            with self.subTest(domain=domain):
                sql = domain_sql(domain, "thesis_test")
                cols = _table_cols(sql, "biz_order")
                self.assertTrue(cols, f"{domain} missing biz_order")
                hit = cols & spec["forbid"]
                self.assertFalse(hit, f"{domain} order has forbidden cols: {hit}")
                missing = spec["allow"] - cols
                self.assertFalse(missing, f"{domain} order missing: {missing}")

    def test_blog_no_loyalty_schema(self) -> None:
        sql = domain_sql("DOM-BLOG", "thesis_test")
        self.assertNotIn("balance_yuan", sql.lower())
        self.assertNotIn("user_ledger", sql.lower())
        self.assertNotIn("taste_note", sql.lower())

    def test_ticket_no_cross_domain_l1(self) -> None:
        cases = {
            "DOM-LIBRARY": {
                "table": "borrow",
                "allow": {"fine_status", "qty"},
                "forbid": {
                    "pickup_at",
                    "contact_channel",
                    "priority",
                    "preferred_stylist",
                },
            },
            "DOM-CRM": {
                "table": "follow_up",
                "allow": {"contact_channel", "next_follow_at"},
                "forbid": {"fine_status", "pickup_at", "priority", "taste_note"},
            },
            "DOM-ATTEND": {
                "table": "leave_req",
                "allow": {"contact_channel", "next_follow_at"},
                "forbid": {"fine_status", "pickup_at", "priority", "taste_note"},
            },
            "DOM-RECRUIT": {
                "table": "job_apply",
                "allow": {"contact_channel", "next_follow_at"},
                "forbid": {"fine_status", "pickup_at", "priority", "taste_note"},
            },
            "DOM-GRADE": {
                "table": "grade_apply",
                "allow": {"contact_channel", "next_follow_at"},
                "forbid": {"fine_status", "pickup_at", "priority", "taste_note"},
            },
            "DOM-INTERN": {
                "table": "week_report",
                "allow": {"contact_channel", "next_follow_at"},
                "forbid": {"fine_status", "pickup_at", "priority", "taste_note"},
            },
            "DOM-PARCEL": {
                "table": "parcel_claim",
                "allow": {"fine_status", "pickup_at", "pickup_place"},
                "forbid": {"contact_channel", "priority", "taste_note"},
            },
            "DOM-EVENT": {
                "table": "event_report",
                "allow": {"contact_channel", "next_follow_at"},
                "forbid": {"fine_status", "pickup_at", "priority", "taste_note"},
            },
            "DOM-DORM": {
                "table": "repair",
                "allow": {"priority", "contact_phone", "attach_url", "rating"},
                "forbid": {"fine_status", "pickup_at", "contact_channel"},
            },
            "DOM-ASSET": {
                "table": "requisition",
                "allow": {"pickup_at", "pickup_place", "actual_qty", "qty"},
                "forbid": {"fine_status", "contact_channel", "priority"},
            },
            "DOM-ACTIVITY": {
                "table": "signup",
                "allow": {"checked_in_at", "rating", "fine_status"},
                "forbid": {"pickup_place", "contact_channel", "priority"},
            },
        }
        for domain, spec in cases.items():
            with self.subTest(domain=domain):
                sql = domain_sql(domain, "thesis_test")
                cols = _table_cols(sql, spec["table"])
                self.assertTrue(cols, f"{domain} missing {spec['table']}")
                hit = cols & spec["forbid"]
                self.assertFalse(hit, f"{domain} ticket has forbidden cols: {hit}")
                missing = spec["allow"] - cols
                self.assertFalse(missing, f"{domain} ticket missing: {missing}")

    def test_archive_semantic_columns(self) -> None:
        """档案主表物理列按域语义化，禁止无关域残留 isbn/author 壳（图书馆除外）。"""
        from app.bake.archive_columns import archive_column_spec_for

        cases = {
            "DOM-PARKING": "space",
            "DOM-SHOP": "product",
            "DOM-FOOD": "dish",
            "DOM-BLOG": "article",
            "DOM-HOTEL": "room_type",
            "DOM-CRM": "customer",
            "DOM-EVENT": "event_case",
            "DOM-ATTEND": "staff_person",
            "DOM-RECRUIT": "job_post",
            "DOM-GRADE": "course_item",
            "DOM-INTERN": "intern_post",
            "DOM-PARCEL": "parcel",
            "DOM-LIBRARY": "book",
        }
        for domain, table in cases.items():
            with self.subTest(domain=domain):
                sql = domain_sql(domain, "thesis_test")
                cols = _table_cols(sql, table)
                (a, _), (i, _) = archive_column_spec_for(domain)
                self.assertIn(a.lower(), cols, f"{domain}.{table} missing {a}")
                self.assertIn(i.lower(), cols, f"{domain}.{table} missing {i}")
                if domain != "DOM-LIBRARY":
                    if i.lower() != "isbn":
                        self.assertNotIn("isbn", cols, f"{domain} still has isbn shell")
                    if a.lower() != "author":
                        self.assertNotIn("author", cols, f"{domain} still has author shell")

    def test_ticket_loan_shell_and_item_fk(self) -> None:
        from app.bake.ticket_columns import ticket_item_fk_for

        loan_forbid = {"due_at", "fine_yuan", "reminded_at", "remind_msg"}
        cases = {
            "DOM-LIBRARY": ("borrow", "book_id", True),
            "DOM-EQUIP": ("loan", "equip_id", True),
            "DOM-CRM": ("follow_up", "customer_id", False),
            "DOM-EVENT": ("event_report", "event_id", False),
            "DOM-ATTEND": ("leave_req", "staff_person_id", False),
            "DOM-RECRUIT": ("job_apply", "job_post_id", False),
            "DOM-GRADE": ("grade_apply", "course_item_id", False),
            "DOM-INTERN": ("week_report", "intern_post_id", False),
            "DOM-PARCEL": ("parcel_claim", "parcel_id", False),
            "DOM-ACTIVITY": ("signup", "activity_id", False),
            "DOM-FORUM": ("reply", "post_id", False),
            "DOM-COURSE": ("enrollment", "course_id", False),
            "DOM-ASSET": ("requisition", "asset_id", False),
        }
        for domain, (table, fk, loan) in cases.items():
            with self.subTest(domain=domain):
                sql = domain_sql(domain, "thesis_test")
                cols = _table_cols(sql, table)
                self.assertEqual(ticket_item_fk_for(domain), fk)
                self.assertIn(fk, cols, f"{domain} missing fk {fk}")
                if fk != "book_id":
                    self.assertNotIn("book_id", cols, f"{domain} still has book_id")
                hit = cols & loan_forbid
                if loan:
                    self.assertTrue(loan_forbid <= cols, f"{domain} missing loan shell")
                else:
                    self.assertFalse(hit, f"{domain} still has loan shell: {hit}")

        for domain, table in (
            ("DOM-DORM", "repair"),
            ("DOM-IT", "ticket"),
            ("DOM-PROPERTY", "ticket"),
        ):
            with self.subTest(standalone=domain):
                self.assertIsNone(ticket_item_fk_for(domain))
                sql = domain_sql(domain, "thesis_test")
                cols = _table_cols(sql, table)
                self.assertNotIn("book_id", cols)
                self.assertNotIn("item_id", cols)
                self.assertFalse(cols & loan_forbid, f"{domain} loan shell")


if __name__ == "__main__":
    unittest.main()
