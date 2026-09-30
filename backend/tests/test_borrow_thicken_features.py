"""借用组 borrow_thicken：域默认用途字典/代取/床位约束/热门榜文案；扫词 ISBN/押金/代收协议。"""

from __future__ import annotations

import unittest

from app.bake.domain_schema import attach_accept
from app.bake.domains import DOMAIN_CAPABILITIES
from app.bake.engine_bake import _patch_thesis_yml
from app.bake.runtime_policy import policy_preview as app_policy_preview
from app.bake.ticket_policy import policy_preview
from app.bake.engine_sql import domain_sql
from app.bake.features.borrow_thicken import (
    scan_abandon_dual,
    scan_bed_luggage,
    scan_blind_count,
    scan_calib_due,
    scan_count_lock,
    scan_diff_reason,
    scan_dual_review,
    scan_equip_accessory,
    scan_equip_deposit,
    scan_equip_insurance,
    scan_fine_waive,
    scan_isbn_validate,
    scan_month_quota,
    scan_parcel_notice_ack,
    scan_peer_confirm,
    scan_project_no,
    scan_renew_no_hold,
    scan_ship_fee,
)
from app.bake.sql.fragments import ensure_borrow_archive_columns


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


class BorrowThickenFeatureTests(unittest.TestCase):
    def test_library_hot_loan_and_holding(self) -> None:
        out = _spec("DOM-LIBRARY", "图书借阅管理系统", "")
        schema = out.get("schema") or {}
        labels = schema.get("labels") or {}
        thicken = schema.get("borrowThicken") or {}
        self.assertEqual(labels.get("recommendSectionTitle"), "热门借阅")
        self.assertTrue(thicken.get("hotLoanBoard"))
        self.assertTrue(thicken.get("closedLoanHint"))
        keys = {
            f.get("key")
            for f in ((schema.get("entities") or {}).get("archive") or {}).get("fields") or []
            if isinstance(f, dict)
        }
        self.assertIn("holdingLoc", keys)
        self.assertIn("campusZone", keys)
        self.assertIn("clcCode", keys)
        self.assertTrue(thicken.get("damageCompTable"))
        self.assertTrue(thicken.get("creditRuleHint"))

    def test_equip_purpose_dict_and_training(self) -> None:
        out = _spec("DOM-EQUIP", "实验室设备借用管理系统", "")
        ticket = ((out.get("schema") or {}).get("entities") or {}).get("ticket") or {}
        self.assertTrue(ticket.get("requireRemark"))
        self.assertEqual(ticket.get("remarkLabel"), "用途说明")
        opts = ticket.get("remarkOptions") or []
        self.assertIn("课程实验", opts)
        self.assertTrue(ticket.get("requireTrainingAck"))
        yml = _patch_thesis_yml("thesis:\n  title: x\n", "DOM-EQUIP", out) + policy_preview("DOM-EQUIP", out)
        self.assertIn("ticket-require-remark: true", yml)
        self.assertIn("ticket-require-training-ack: true", yml)

    def test_asset_purpose_and_stock_warn_below(self) -> None:
        out = _spec("DOM-ASSET", "物资领用管理系统", "")
        schema = out.get("schema") or {}
        ticket = (schema.get("entities") or {}).get("ticket") or {}
        self.assertIn("教学科研", ticket.get("remarkOptions") or [])
        self.assertGreaterEqual(int(schema.get("stockWarnBelow") or 0), 1)
        keys = {
            f.get("key")
            for f in ((schema.get("entities") or {}).get("archive") or {}).get("fields") or []
            if isinstance(f, dict)
        }
        self.assertIn("batchNo", keys)
        self.assertIn("shelfNo", keys)
        self.assertIn("supplierContact", keys)
        self.assertTrue(ticket.get("allowProcureRef"))
        yml = _patch_thesis_yml("thesis:\n  title: x\n", "DOM-ASSET", out) + policy_preview("DOM-ASSET", out)
        self.assertIn("ticket-allow-procure-ref: true", yml)

    def test_procure_to_stock_in_default(self) -> None:
        out = _spec("DOM-PROCURE", "物资申购管理系统", "")
        schema = out.get("schema") or {}
        ticket = (schema.get("entities") or {}).get("ticket") or {}
        caps = set(out.get("capabilities") or [])
        self.assertTrue(ticket.get("procureToStockIn"))
        self.assertIn("stock_io", caps)
        yml = _patch_thesis_yml("thesis:\n  title: x\n", "DOM-PROCURE", out) + policy_preview("DOM-PROCURE", out) + app_policy_preview("DOM-PROCURE", out)
        self.assertIn("ticket-procure-to-stock-in: true", yml)
        self.assertIn("stock-io-enabled: true", yml)
        sql = domain_sql(
            "DOM-PROCURE",
            "db_test",
            capabilities=list(out.get("capabilities") or []),
            title="物资申购",
            ticket_flags=ticket,
        )
        self.assertIn("stock_move", sql)

    def test_scrap_approve_flow_on_stock_scrap(self) -> None:
        out = _spec("DOM-ASSET", "物资领用与报废", "物资报废审批。")
        schema = out.get("schema") or {}
        caps = set(out.get("capabilities") or [])
        self.assertIn("stock_scrap", caps)
        opts = schema.get("stockScrapOpts") or {}
        self.assertTrue(opts.get("approveFlow"))
        yml = _patch_thesis_yml("thesis:\n  title: x\n", "DOM-ASSET", out) + policy_preview("DOM-ASSET", out)
        self.assertIn("stock-scrap-approve-flow: true", yml)
        sql = domain_sql(
            "DOM-ASSET",
            "db_test",
            capabilities=list(out.get("capabilities") or []),
            title="物资领用与报废",
            ticket_flags=(schema.get("entities") or {}).get("ticket") or {},
        )
        self.assertIn("scrap_request", sql)

    def test_parcel_proxy_arrival_exception(self) -> None:
        out = _spec("DOM-PARCEL", "校园快递驿站", "")
        ticket = ((out.get("schema") or {}).get("entities") or {}).get("ticket") or {}
        self.assertTrue(ticket.get("allowProxyPickup"))
        self.assertTrue(ticket.get("arrivalNotify"))
        self.assertTrue(ticket.get("allowExceptionClose"))
        yml = _patch_thesis_yml("thesis:\n  title: x\n", "DOM-PARCEL", out) + policy_preview("DOM-PARCEL", out)
        self.assertIn("ticket-allow-proxy-pickup: true", yml)
        self.assertIn("ticket-arrival-notify: true", yml)
        self.assertIn("ticket-allow-exception-close: true", yml)
        sql = domain_sql(
            "DOM-PARCEL",
            "db_test",
            capabilities=list(DOMAIN_CAPABILITIES["DOM-PARCEL"]),
            title="校园快递驿站",
            ticket_flags=ticket,
        )
        self.assertIn("proxy_name", sql)
        self.assertIn("exception_reason", sql)

    def test_bed_constraint_and_notice(self) -> None:
        out = _spec("DOM-BED", "学生床位调配管理系统", "")
        ticket = ((out.get("schema") or {}).get("entities") or {}).get("ticket") or {}
        self.assertTrue(ticket.get("bedConstraint"))
        self.assertTrue(ticket.get("requireNoticeAck"))
        yml = _patch_thesis_yml("thesis:\n  title: x\n", "DOM-BED", out) + policy_preview("DOM-BED", out)
        self.assertIn("ticket-bed-constraint: true", yml)
        self.assertIn("ticket-require-notice-ack: true", yml)
        keys = {
            f.get("key")
            for f in ((out.get("schema") or {}).get("entities") or {})
            .get("archive", {})
            .get("fields")
            or []
            if isinstance(f, dict)
        }
        self.assertIn("allowedGender", keys)
        self.assertIn("allowedGrades", keys)
        self.assertIn("buildingZone", keys)

    def test_isbn_deposit_parcel_ack_scan(self) -> None:
        self.assertTrue(scan_isbn_validate("图书录入支持 ISBN 校验与查重提示。"))
        self.assertFalse(scan_isbn_validate("图书借阅归还催还。"))
        self.assertTrue(scan_equip_deposit("设备借用押金登记与归还退押。"))
        self.assertTrue(scan_parcel_notice_ack("取件前须勾选驿站代收协议。"))

        lib = _spec("DOM-LIBRARY", "图书借阅", "ISBN校验与索书号查重提示。")
        self.assertTrue((lib.get("schema") or {}).get("borrowThicken", {}).get("isbnValidate"))

        eq = _spec("DOM-EQUIP", "设备借用", "设备押金登记与归还退押。")
        t = ((eq.get("schema") or {}).get("entities") or {}).get("ticket") or {}
        self.assertTrue(t.get("allowDeposit"))
        yml = _patch_thesis_yml("thesis:\n  title: x\n", "DOM-EQUIP", eq) + policy_preview("DOM-EQUIP", eq)
        self.assertIn("ticket-allow-deposit: true", yml)

        parcel = _spec("DOM-PARCEL", "驿站", "驿站代收协议勾选后方可取件。")
        t2 = ((parcel.get("schema") or {}).get("entities") or {}).get("ticket") or {}
        self.assertTrue(t2.get("requireNoticeAck"))

    def test_batch2_scans_and_fields(self) -> None:
        self.assertTrue(scan_calib_due("设备校准证书到期停借。"))
        self.assertTrue(scan_equip_insurance("借用前须勾选设备保险声明。"))
        self.assertTrue(scan_equip_accessory("随借配件勾选清单。"))
        self.assertTrue(scan_bed_luggage("退宿行李清点。"))
        self.assertTrue(scan_dual_review("领用双人复核签字。"))
        self.assertTrue(scan_project_no("填写课题号。"))
        self.assertTrue(scan_ship_fee("寄件运费登记。"))

        eq = _spec("DOM-EQUIP", "设备", "校准证书到期停借；设备保险声明勾选；随借配件清单。")
        te = ((eq.get("schema") or {}).get("entities") or {}).get("ticket") or {}
        self.assertTrue(te.get("blockIfCalibExpired"))
        self.assertTrue(te.get("requireInsuranceAck"))
        self.assertIn("material_check", eq.get("capabilities") or [])
        yml = _patch_thesis_yml("thesis:\n  title: x\n", "DOM-EQUIP", eq) + policy_preview("DOM-EQUIP", eq)
        self.assertIn("ticket-block-if-calib-expired: true", yml)
        self.assertIn("ticket-require-insurance-ack: true", yml)

        asset = _spec("DOM-ASSET", "物资", "领用须填课题号；双人复核签字栏。")
        ta = ((asset.get("schema") or {}).get("entities") or {}).get("ticket") or {}
        self.assertTrue(ta.get("allowProjectNo"))
        self.assertTrue(ta.get("allowDualReview"))

        bed = _spec("DOM-BED", "床位", "退宿行李清点；住宿费预定金；退宿水电清算备注。")
        self.assertIn("material_check", bed.get("capabilities") or [])
        tb = ((bed.get("schema") or {}).get("entities") or {}).get("ticket") or {}
        self.assertTrue(tb.get("allowDeposit"))
        self.assertTrue(tb.get("allowUtilityNote"))

        parcel = _spec("DOM-PARCEL", "驿站", "寄件运费登记与滞留弃件。")
        tp = ((parcel.get("schema") or {}).get("entities") or {}).get("ticket") or {}
        self.assertTrue(tp.get("allowShipFee"))
        self.assertTrue((parcel.get("schema") or {}).get("borrowThicken", {}).get("parcelAbandon"))
        keys = {
            f.get("key")
            for f in ((parcel.get("schema") or {}).get("entities") or {})
            .get("archive", {})
            .get("fields")
            or []
            if isinstance(f, dict)
        }
        self.assertIn("slotStatus", keys)

    def test_batch3_peer_fine_count_opts(self) -> None:
        self.assertTrue(scan_peer_confirm("调宿双方确认后再审。"))
        self.assertTrue(scan_fine_waive("支持逾期罚款减免申请。"))
        self.assertTrue(scan_renew_no_hold("续借须无预约他人抢约。"))
        self.assertTrue(scan_month_quota("物资领用额度按月限额。"))
        self.assertTrue(scan_count_lock("盘点锁定期间禁出入库。"))
        self.assertTrue(scan_blind_count("支持盲盘先数后看账。"))
        self.assertTrue(scan_diff_reason("盘点差异原因登记。"))
        self.assertTrue(scan_abandon_dual("弃件双人确认。"))

        lib = _spec(
            "DOM-LIBRARY",
            "图书",
            "逾期罚款减免；续借须无预约他人抢约。",
        )
        tl = ((lib.get("schema") or {}).get("entities") or {}).get("ticket") or {}
        self.assertTrue(tl.get("allowQty"))
        self.assertEqual(tl.get("qtyLabel"), "册数")
        self.assertTrue(tl.get("allowFineWaive"))
        self.assertTrue(tl.get("renewBlockIfHeld"))
        yml = _patch_thesis_yml("thesis:\n  title: x\n", "DOM-LIBRARY", lib) + policy_preview("DOM-LIBRARY", lib)
        self.assertIn("ticket-allow-fine-waive: true", yml)
        self.assertIn("ticket-renew-block-if-held: true", yml)

        bed = _spec("DOM-BED", "床位", "调宿双方确认与对向同意后再审。")
        tb = ((bed.get("schema") or {}).get("entities") or {}).get("ticket") or {}
        self.assertTrue(tb.get("requirePeerConfirm"))
        menus = ((bed.get("schema") or {}).get("menus") or {}).get("user") or []
        keys = {m.get("key") for m in menus if isinstance(m, dict)}
        self.assertIn("peer_tickets", keys)

        asset = _spec(
            "DOM-ASSET",
            "物资",
            "领用额度按月；盘点锁定禁出入库；盲盘；盘点差异原因登记。",
        )
        opts = (asset.get("schema") or {}).get("stockCountOpts") or {}
        self.assertTrue(opts.get("countLock"))
        self.assertTrue(opts.get("blindCount"))
        self.assertTrue(opts.get("requireDiffReason"))
        ta = ((asset.get("schema") or {}).get("entities") or {}).get("ticket") or {}
        self.assertGreaterEqual(int(ta.get("categoryLimit") or 0), 1)
        yml2 = _patch_thesis_yml("thesis:\n  title: x\n", "DOM-ASSET", asset) + policy_preview("DOM-ASSET", asset)
        self.assertIn("stock-count-lock: true", yml2)

        parcel = _spec("DOM-PARCEL", "驿站", "滞留弃件双人确认。")
        tp = ((parcel.get("schema") or {}).get("entities") or {}).get("ticket") or {}
        self.assertTrue(tp.get("requireAbandonDual"))

    def test_borrow_archive_columns_inject(self) -> None:
        raw = """
CREATE TABLE IF NOT EXISTS book (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  title VARCHAR(128) NOT NULL,
  stock INT NOT NULL DEFAULT 0
);
"""
        out = ensure_borrow_archive_columns(raw, domain="DOM-LIBRARY", item_table="book")
        self.assertIn("holding_loc", out)
        self.assertIn("campus_zone", out)
        self.assertIn("clc_code", out)
        skip = ensure_borrow_archive_columns(raw, domain="DOM-DORM", item_table="book")
        self.assertNotIn("holding_loc", skip)


if __name__ == "__main__":
    unittest.main()
