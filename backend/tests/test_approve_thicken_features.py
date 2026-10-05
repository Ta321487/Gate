"""审批/填报组 approve_thicken：十批（… + 复制上年/退货/综测异议/经费使用/评教权重/访客余量）。"""

from __future__ import annotations

import unittest

from app.bake.domain_schema import attach_accept
from app.bake.domains import DOMAIN_CAPABILITIES
from app.bake.engine_bake import _patch_thesis_yml
from app.bake.engine_sql import domain_sql
from app.bake.features.approve_thicken import APPROVE_DOMAINS
from app.bake.schema.er_model import schema_model
from app.bake.ticket_policy import policy_preview


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


class ApproveThickenFeatureTests(unittest.TestCase):
    def test_cert_core_defaults(self) -> None:
        out = _spec("DOM-CERT", "校园证明开具管理系统", "")
        schema = out.get("schema") or {}
        ticket = (schema.get("entities") or {}).get("ticket") or {}
        thicken = schema.get("approveThicken") or {}
        labels = schema.get("labels") or {}
        self.assertTrue(ticket.get("approveThicken"))
        self.assertTrue(thicken.get("core"))
        self.assertEqual(int(ticket.get("maxReviseTimes") or 0), 3)
        self.assertEqual(int(ticket.get("minApproveRemarkWords") or 0), 4)
        self.assertEqual(int(ticket.get("dueSoonDays") or 0), 3)
        self.assertTrue(ticket.get("allowApproveCc"))
        self.assertTrue(ticket.get("slaDeadline"))
        phrases = ticket.get("approvePhrases") or []
        self.assertGreaterEqual(len(phrases), 3)
        self.assertIn("withdrawHint", labels)
        self.assertIn("maxReviseHint", labels)
        self.assertIn("approvePhraseLabel", labels)
        self.assertIn("minApproveRemarkHint", labels)
        self.assertIn("approveDueSoonHint", labels)
        self.assertIn("approveCcLabel", labels)
        self.assertTrue(ticket.get("allowApproveTransfer"))
        self.assertTrue(ticket.get("allowApproveDelegate"))
        self.assertTrue(ticket.get("allowApproveRemarkAttach"))
        self.assertTrue(ticket.get("allowApproveCcComment"))
        self.assertFalse(bool(ticket.get("allowApproveAutoPass")))
        self.assertEqual(int(ticket.get("approveAutoPassHours") or 0), 0)
        self.assertIn("approveTransferLabel", labels)
        self.assertIn("approveDelegateLabel", labels)
        self.assertIn("approveRemarkAttachLabel", labels)
        self.assertIn("approveCcCommentLabel", labels)
        self.assertIn("approveAutoPassHint", labels)
        self.assertIn("deadline", out.get("capabilities") or [])
        yml = _patch_thesis_yml("thesis:\n  title: x\n", "DOM-CERT", out) + policy_preview(
            "DOM-CERT", out
        )
        self.assertIn("ticket-approve-thicken: true", yml)
        self.assertIn("ticket-allow-approve-cc: true", yml)
        self.assertIn("ticket-allow-approve-transfer: true", yml)
        self.assertIn("ticket-allow-approve-delegate: true", yml)
        self.assertIn("ticket-allow-approve-remark-attach: true", yml)
        self.assertIn("ticket-allow-approve-cc-comment: true", yml)
        self.assertIn("ticket-min-approve-remark-words: 4", yml)
        self.assertIn("ticket-max-revise-times: 3", yml)
        self.assertIn("ticket-due-soon-days: 3", yml)

    def test_auto_pass_scan_opens(self) -> None:
        out = _spec("DOM-SEAL", "用印审批", "支持限时自动通过")
        ticket = ((out.get("schema") or {}).get("entities") or {}).get("ticket") or {}
        self.assertTrue(ticket.get("allowApproveAutoPass"))
        self.assertEqual(int(ticket.get("approveAutoPassHours") or 0), 72)
        yml = policy_preview("DOM-SEAL", out)
        self.assertIn("ticket-allow-approve-auto-pass: true", yml)
        self.assertIn("ticket-approve-auto-pass-hours: 72", yml)

    def test_non_approve_domain_untouched(self) -> None:
        out = _spec("DOM-ACTIVITY", "校园活动报名系统", "")
        schema = out.get("schema") or {}
        ticket = (schema.get("entities") or {}).get("ticket") or {}
        self.assertFalse(bool(ticket.get("approveThicken")))
        self.assertFalse(bool(schema.get("approveThicken")))
        self.assertFalse(bool(ticket.get("allowApproveTransfer")))
        self.assertFalse(bool(ticket.get("allowApproveDelegate")))
        self.assertNotEqual(int(ticket.get("minApproveRemarkWords") or 0), 4)
        self.assertFalse(bool(ticket.get("allowCertPickup")))
        self.assertFalse(bool(ticket.get("allowSealCopies")))
        self.assertFalse(bool(ticket.get("allowFleetMileage")))

    def test_all_approve_domains_get_core(self) -> None:
        for domain in sorted(APPROVE_DOMAINS):
            out = _spec(domain, f"{domain} 审批填报", "")
            ticket = ((out.get("schema") or {}).get("entities") or {}).get("ticket") or {}
            self.assertTrue(ticket.get("approveThicken"), domain)
            self.assertTrue(ticket.get("allowApproveCc"), domain)
            self.assertTrue(ticket.get("allowApproveTransfer"), domain)
            self.assertTrue(ticket.get("allowApproveDelegate"), domain)
            self.assertTrue(ticket.get("allowApproveRemarkAttach"), domain)
            self.assertTrue(ticket.get("allowApproveCcComment"), domain)

    def test_sql_has_cc_attach_delegate(self) -> None:
        out = _spec("DOM-SEAL", "用印审批系统", "")
        ticket = ((out.get("schema") or {}).get("entities") or {}).get("ticket") or {}
        text = domain_sql(
            "DOM-SEAL",
            "db_test",
            capabilities=list(out.get("capabilities") or []),
            title="用印审批",
            ticket_flags=ticket,
        )
        self.assertIn("cc_usernames", text)
        self.assertIn("approve_attach_url", text)
        self.assertIn("revise_count", text)
        self.assertIn("due_soon_notified_at", text)
        self.assertIn("approve_delegate", text)

    def test_intern_max_revise_not_overwritten_by_approve(self) -> None:
        """非审批域不受 approve_thicken 影响；INTERN 仍走 follow 的 maxRevise。"""
        out = _spec("DOM-INTERN", "实习周报管理系统", "退回修改次数")
        ticket = ((out.get("schema") or {}).get("entities") or {}).get("ticket") or {}
        self.assertFalse(bool(ticket.get("approveThicken")))
        self.assertFalse(bool(ticket.get("allowApproveCc")))
        self.assertFalse(bool(ticket.get("allowApproveTransfer")))

    def test_domain_skins_cert_seal_fleet_expense_visitor(self) -> None:
        """第三批域皮（已补厚）：开关 + SQL + policy + 办结/附件规则；互不串味。"""
        cases = [
            (
                "DOM-CERT",
                "证明开具",
                {
                    "allowCertPickup": True,
                    "allowCertUrgent": True,
                },
                ["pickup_method", "mail_address", "express_no", "cert_urgent"],
                [
                    "ticket-allow-cert-pickup: true",
                    "ticket-allow-cert-urgent: true",
                    "ticket-allow-seal-copies: false",
                ],
                [
                    "certPickupLabel",
                    "certUrgentLabel",
                    "mailAddressLabel",
                    "expressNoLabel",
                ],
            ),
            (
                "DOM-SEAL",
                "用印审批",
                {"allowSealCopies": True},
                ["seal_copies", "bind_note", "seal_copy_nos", "seal_witness_ack"],
                [
                    "ticket-allow-seal-copies: true",
                    "ticket-allow-cert-pickup: false",
                ],
                ["sealCopiesLabel", "bindNoteLabel", "sealCopyNosLabel", "sealWitnessAckLabel"],
            ),
            (
                "DOM-FLEET",
                "公务用车",
                {"allowFleetMileage": True},
                ["mileage_km", "fuel_note"],
                [
                    "ticket-allow-fleet-mileage: true",
                    "ticket-allow-expense-invoice: false",
                ],
                ["mileageLabel", "fuelNoteLabel"],
            ),
            (
                "DOM-EXPENSE",
                "经费报销",
                {"allowExpenseInvoice": True, "requireAttach": True},
                ["invoice_count"],
                [
                    "ticket-allow-expense-invoice: true",
                    "ticket-allow-visitor-count: false",
                ],
                ["invoiceCountLabel", "expenseAmountLabel"],
            ),
            (
                "DOM-VISITOR",
                "访客预约",
                {"allowVisitorCount": True},
                ["visitor_count", "ticket_companion"],
                [
                    "ticket-allow-visitor-count: true",
                    "ticket-allow-fleet-mileage: false",
                ],
                ["visitorCountLabel", "companionNamesLabel"],
            ),
        ]
        skin_keys = (
            "allowCertPickup",
            "allowCertUrgent",
            "allowSealCopies",
            "allowFleetMileage",
            "allowExpenseInvoice",
            "allowVisitorCount",
        )
        for domain, title, expect_flags, cols, yml_needles, label_keys in cases:
            out = _spec(domain, title, "")
            schema = out.get("schema") or {}
            ticket = (schema.get("entities") or {}).get("ticket") or {}
            labels = schema.get("labels") or {}
            for k, v in expect_flags.items():
                self.assertEqual(bool(ticket.get(k)), v, f"{domain}.{k}")
            for k in skin_keys:
                if k not in expect_flags:
                    self.assertFalse(bool(ticket.get(k)), f"{domain} 不应开 {k}")
            for lk in label_keys:
                self.assertIn(lk, labels, f"{domain} labels.{lk}")
            yml = policy_preview(domain, out)
            for needle in yml_needles:
                self.assertIn(needle, yml, f"{domain} {needle}")
            text = domain_sql(
                domain,
                "db_skin",
                capabilities=list(out.get("capabilities") or []),
                title=title,
                ticket_flags=ticket,
            )
            for col in cols:
                self.assertIn(col, text, f"{domain} sql {col}")

    def test_batch4_rules_skins(self) -> None:
        """第四批：黑名单/学分上限/一人一课/证书查重/比价N家/到期提醒。"""
        cases = [
            (
                "DOM-VISITOR",
                "访客预约",
                {
                    "allowVisitorCount": True,
                    "allowApplyBlacklist": True,
                },
                ["visitor_count", "ticket_companion"],
                [
                    "ticket-allow-apply-blacklist: true",
                    "ticket-allow-visitor-count: true",
                ],
                [
                    "applyBlacklistTitle",
                    "applyBlacklistDenyMessage",
                    "visitorCountLabel",
                ],
                {"visitorBlacklist": True},
                None,
            ),
            (
                "DOM-CREDIT",
                "第二课堂学分认定",
                {"semesterCreditCap": 30, "creditWarnRemaining": 4},
                ["credit"],
                [
                    "ticket-semester-credit-cap: 30",
                    "ticket-credit-warn-remaining: 4",
                ],
                ["creditCapHint"],
                {"creditCap": True},
                "credit",
            ),
            (
                "DOM-EVAL",
                "评教系统",
                {"forceOnePerArchive": True, "allowMultiTicket": False},
                [],
                [
                    "ticket-force-one-per-archive: true",
                    "allow-multi-ticket: false",
                ],
                ["evalOnePerCourseHint", "onePerArchiveDenyMessage"],
                {"evalOnePerCourse": True},
                None,
            ),
            (
                "DOM-AWARD",
                "获奖成果登记",
                {"allowAwardCertNo": True},
                ["award_cert_no"],
                ["ticket-allow-award-cert-no: true"],
                ["awardCertNoLabel", "awardCertNoHint"],
                {"awardCertNo": True},
                None,
            ),
            (
                "DOM-PROCURE",
                "采购申购",
                {"allowVendorQuotes": True, "minVendorQuotes": 3},
                ["vendor_quotes"],
                [
                    "ticket-allow-vendor-quotes: true",
                    "ticket-min-vendor-quotes: 3",
                ],
                ["vendorQuotesLabel", "minVendorQuotesHint"],
                {"minVendorQuotes": True},
                None,
            ),
            (
                "DOM-CONTRACT",
                "合同审批",
                {"notifyArchiveExpireDays": 7},
                ["expire_on", "expire_soon_notified_at"],
                ["ticket-notify-archive-expire-days: 7"],
                ["archiveExpireNotifyHint", "expireOnLabel"],
                {"archiveExpireNotify": True},
                "expire_on",
            ),
            (
                "DOM-LABSAFE",
                "实验室准入",
                {"notifyArchiveExpireDays": 7},
                ["expire_on", "expire_soon_notified_at"],
                ["ticket-notify-archive-expire-days: 7"],
                ["archiveExpireNotifyHint"],
                {"archiveExpireNotify": True},
                "expire_on",
            ),
        ]
        for (
            domain,
            title,
            expect_flags,
            cols,
            yml_needles,
            label_keys,
            thicken_flags,
            archive_col,
        ) in cases:
            out = _spec(domain, title, "")
            schema = out.get("schema") or {}
            ticket = (schema.get("entities") or {}).get("ticket") or {}
            labels = schema.get("labels") or {}
            thicken = schema.get("approveThicken") or {}
            for k, v in expect_flags.items():
                if isinstance(v, bool):
                    self.assertEqual(bool(ticket.get(k)), v, f"{domain}.{k}")
                else:
                    self.assertEqual(int(ticket.get(k) or 0), int(v), f"{domain}.{k}")
            for lk in label_keys:
                self.assertIn(lk, labels, f"{domain} labels.{lk}")
            for tk, tv in thicken_flags.items():
                self.assertEqual(bool(thicken.get(tk)), tv, f"{domain} thicken.{tk}")
            if domain == "DOM-VISITOR":
                self.assertTrue(schema.get("applyBlacklist"), domain)
            yml = policy_preview(domain, out)
            for needle in yml_needles:
                self.assertIn(needle, yml, f"{domain} {needle}")
            text = domain_sql(
                domain,
                "db_b4",
                capabilities=list(out.get("capabilities") or []),
                title=title,
                ticket_flags=ticket,
            )
            for col in cols:
                self.assertIn(col, text, f"{domain} sql {col}")
            if archive_col:
                self.assertIn(archive_col, text, f"{domain} archive {archive_col}")

        # 互不串味：AWARD 不开比价；PROCURE 不开证书编号
        award = _spec("DOM-AWARD", "获奖", "")
        at = ((award.get("schema") or {}).get("entities") or {}).get("ticket") or {}
        self.assertFalse(bool(at.get("allowVendorQuotes")))
        self.assertEqual(int(at.get("minVendorQuotes") or 0), 0)
        procure = _spec("DOM-PROCURE", "采购", "")
        pt = ((procure.get("schema") or {}).get("entities") or {}).get("ticket") or {}
        self.assertFalse(bool(pt.get("allowAwardCertNo")))
        self.assertFalse(bool(pt.get("forceOnePerArchive")))

    def test_batch5_rules_skins(self) -> None:
        """第五批：评教窗口/核定小时/驾乘人/劳动查寝必附/伦理批件。"""
        cases = [
            (
                "DOM-EVAL",
                "评教系统",
                {"allowEvalOpenWindow": True, "forceOnePerArchive": True},
                [],
                [
                    "ticket-allow-eval-open-window: true",
                    "ticket-eval-open-window-deny-message:",
                ],
                [
                    "evalOpenWindowHint",
                    "evalOpenWindowDenyMessage",
                    "evalOpenOnLabel",
                    "evalCloseOnLabel",
                ],
                {"evalOpenWindow": True},
                "eval_open_on",
            ),
            (
                "DOM-TRIP",
                "加班出差审批",
                {"allowCompHours": True},
                ["comp_hours"],
                ["ticket-allow-comp-hours: true"],
                ["compHoursLabel", "compHoursHint"],
                {"compHours": True},
                None,
            ),
            (
                "DOM-FLEET",
                "公务用车",
                {"allowFleetCrew": True},
                ["driver_name", "passenger_names"],
                ["ticket-allow-fleet-crew: true"],
                ["driverNameLabel", "passengerNamesLabel", "fleetCrewHint"],
                {"fleetCrew": True},
                None,
            ),
            (
                "DOM-LABOR",
                "劳动时长认定",
                {"requireAttach": True},
                ["attach_url"],
                ["ticket-require-attach: true"],
                ["laborAttachLabel", "laborAttachHint"],
                {"laborAttach": True},
                None,
            ),
            (
                "DOM-ETHIC",
                "伦理审查",
                {"allowEthicBatch": True},
                [],
                ["ticket-allow-ethic-batch: true"],
                ["batchNoLabel", "expireOnLabel", "ethicBatchHint"],
                {"ethicBatch": True},
                "batch_no",
            ),
            (
                "DOM-CHECKIN",
                "查寝归寝",
                {"requireAttach": True},
                ["attach_url"],
                ["ticket-require-attach: true"],
                ["checkinPhotoLabel", "checkinPhotoHint"],
                {"checkinPhoto": True},
                None,
            ),
        ]
        for (
            domain,
            title,
            expect_flags,
            cols,
            yml_needles,
            label_keys,
            thicken_flags,
            archive_col,
        ) in cases:
            out = _spec(domain, title, "")
            schema = out.get("schema") or {}
            ticket = (schema.get("entities") or {}).get("ticket") or {}
            labels = schema.get("labels") or {}
            thicken = schema.get("approveThicken") or {}
            for k, v in expect_flags.items():
                if isinstance(v, bool):
                    self.assertEqual(bool(ticket.get(k)), v, f"{domain}.{k}")
                else:
                    self.assertEqual(int(ticket.get(k) or 0), int(v), f"{domain}.{k}")
            for lk in label_keys:
                self.assertIn(lk, labels, f"{domain} labels.{lk}")
            for tk, tv in thicken_flags.items():
                self.assertEqual(bool(thicken.get(tk)), tv, f"{domain} thicken.{tk}")
            yml = policy_preview(domain, out)
            for needle in yml_needles:
                self.assertIn(needle, yml, f"{domain} {needle}")
            text = domain_sql(
                domain,
                "db_b5",
                capabilities=list(out.get("capabilities") or []),
                title=title,
                ticket_flags=ticket,
            )
            for col in cols:
                self.assertIn(col, text, f"{domain} sql {col}")
            if archive_col:
                self.assertIn(archive_col, text, f"{domain} archive {archive_col}")

        # 互不串味：TRIP 不开驾乘人；FLEET 不开核定小时；LABOR 不挂评教窗口
        trip = _spec("DOM-TRIP", "加班", "")
        tt = ((trip.get("schema") or {}).get("entities") or {}).get("ticket") or {}
        self.assertFalse(bool(tt.get("allowFleetCrew")))
        self.assertFalse(bool(tt.get("allowEvalOpenWindow")))
        fleet = _spec("DOM-FLEET", "用车", "")
        ft = ((fleet.get("schema") or {}).get("entities") or {}).get("ticket") or {}
        self.assertFalse(bool(ft.get("allowCompHours")))
        labor = _spec("DOM-LABOR", "劳动", "")
        lt = ((labor.get("schema") or {}).get("entities") or {}).get("ticket") or {}
        self.assertFalse(bool(lt.get("allowEvalOpenWindow")))
        self.assertFalse(bool(lt.get("allowEthicBatch")))

    def test_batch6_rules_skins(self) -> None:
        """第六批：通行码失效/回场油量/劳动地点/宣传悬挂/伦理会议/学籍生效日。"""
        cases = [
            (
                "DOM-VISITOR",
                "访客预约",
                {"allowPassExpire": True, "passExpireDays": 1},
                ["pass_expire_at", "pass_code"],
                [
                    "ticket-allow-pass-expire: true",
                    "ticket-pass-expire-days: 1",
                ],
                ["passExpireAtLabel", "passExpiredLabel", "passExpireHint"],
                {"passExpire": True},
                None,
            ),
            (
                "DOM-CARPASS",
                "车辆通行证",
                {"allowPassExpire": True, "passExpireDays": 1},
                ["pass_expire_at"],
                ["ticket-allow-pass-expire: true"],
                ["passExpireHint"],
                {"passExpire": True},
                None,
            ),
            (
                "DOM-FLEET",
                "公务用车",
                {"allowReturnFuel": True},
                ["return_fuel"],
                ["ticket-allow-return-fuel: true"],
                ["returnFuelLabel", "returnFuelHint"],
                {"returnFuel": True},
                None,
            ),
            (
                "DOM-LABOR",
                "劳动时长认定",
                {"allowLaborPlace": True},
                ["labor_place"],
                ["ticket-allow-labor-place: true"],
                ["laborPlaceLabel", "laborPlaceHint"],
                {"laborPlace": True},
                None,
            ),
            (
                "DOM-PROMO",
                "宣传品审批",
                {"allowPromoPlace": True},
                [],
                ["ticket-allow-promo-place: true"],
                ["promoSizeLabel", "hangPlaceLabel", "promoPlaceHint"],
                {"promoPlace": True},
                "promo_size",
            ),
            (
                "DOM-ETHIC",
                "伦理审查",
                {"allowEthicMeeting": True},
                [],
                ["ticket-allow-ethic-meeting: true"],
                ["meetingOnLabel", "resolutionNoteLabel", "ethicMeetingHint"],
                {"ethicMeeting": True},
                "meeting_on",
            ),
            (
                "DOM-ACAD",
                "学籍异动",
                {"allowEffectiveOn": True},
                ["effective_on"],
                ["ticket-allow-effective-on: true"],
                ["effectiveOnLabel", "effectiveOnHint"],
                {"effectiveOn": True},
                None,
            ),
        ]
        for (
            domain,
            title,
            expect_flags,
            cols,
            yml_needles,
            label_keys,
            thicken_flags,
            archive_col,
        ) in cases:
            out = _spec(domain, title, "")
            schema = out.get("schema") or {}
            ticket = (schema.get("entities") or {}).get("ticket") or {}
            labels = schema.get("labels") or {}
            thicken = schema.get("approveThicken") or {}
            for k, v in expect_flags.items():
                if isinstance(v, bool):
                    self.assertEqual(bool(ticket.get(k)), v, f"{domain}.{k}")
                else:
                    self.assertEqual(int(ticket.get(k) or 0), int(v), f"{domain}.{k}")
            for lk in label_keys:
                self.assertIn(lk, labels, f"{domain} labels.{lk}")
            for tk, tv in thicken_flags.items():
                self.assertEqual(bool(thicken.get(tk)), tv, f"{domain} thicken.{tk}")
            yml = policy_preview(domain, out)
            for needle in yml_needles:
                self.assertIn(needle, yml, f"{domain} {needle}")
            text = domain_sql(
                domain,
                "db_b6",
                capabilities=list(out.get("capabilities") or []),
                title=title,
                ticket_flags=ticket,
            )
            for col in cols:
                self.assertIn(col, text, f"{domain} sql {col}")
            if archive_col:
                self.assertIn(archive_col, text, f"{domain} archive {archive_col}")

        labor = _spec("DOM-LABOR", "劳动", "")
        lt = ((labor.get("schema") or {}).get("entities") or {}).get("ticket") or {}
        self.assertFalse(bool(lt.get("allowPassExpire")))
        self.assertFalse(bool(lt.get("allowReturnFuel")))
        self.assertFalse(bool(lt.get("allowEffectiveOn")))
        fleet = _spec("DOM-FLEET", "用车", "")
        ft = ((fleet.get("schema") or {}).get("entities") or {}).get("ticket") or {}
        self.assertFalse(bool(ft.get("allowLaborPlace")))
        acad = _spec("DOM-ACAD", "学籍", "")
        at = ((acad.get("schema") or {}).get("entities") or {}).get("ticket") or {}
        self.assertFalse(bool(at.get("allowPromoPlace")))


    def test_batch7_rules_skins(self) -> None:
        """第七批：证明流水/过路附件/反馈照/版本号/禁噪窗/邀约码。"""
        cases = [
            (
                "DOM-CERT",
                "证明开具",
                {"allowCertIssueNo": True},
                ["cert_issue_no"],
                ["ticket-allow-cert-issue-no: true"],
                ["certIssueNoLabel", "certIssueNoHint"],
                {"certIssueNo": True},
                None,
            ),
            (
                "DOM-FLEET",
                "公务用车",
                {"requireAttach": True},
                [],
                ["ticket-require-attach: true"],
                ["fleetTollAttachLabel", "fleetTollAttachHint"],
                {"fleetTollAttach": True},
                None,
            ),
            (
                "DOM-PROMO",
                "宣传品审批",
                {"requireCloseAttach": True, "allowPromoFeedback": True},
                [],
                ["ticket-require-close-attach: true", "ticket-allow-promo-feedback: true"],
                ["promoFeedbackLabel", "promoFeedbackHint"],
                {"promoFeedback": True},
                None,
            ),
            (
                "DOM-CONTRACT",
                "合同审批",
                {"allowDocRev": True},
                ["doc_rev"],
                ["ticket-allow-doc-rev: true"],
                ["docRevLabel", "docRevHint"],
                {"docRev": True},
                None,
            ),
            (
                "DOM-FITOUT",
                "装修报备",
                {"allowFitoutQuiet": True},
                ["work_start", "work_end"],
                ["ticket-allow-fitout-quiet: true"],
                ["fitoutWindowLabel", "fitoutQuietHint"],
                {"fitoutQuiet": True},
                "quiet_start",
            ),
            (
                "DOM-VISITOR",
                "访客预约",
                {"requireApplyInvite": True},
                [],
                ["ticket-require-apply-invite: true"],
                ["visitorInviteLabel", "visitorInviteHint"],
                {"visitorInvite": True},
                "apply_invite_code",
            ),
        ]
        for (
            domain,
            title,
            expect_flags,
            cols,
            yml_needles,
            label_keys,
            thicken_flags,
            archive_col,
        ) in cases:
            out = _spec(domain, title, "")
            schema = out.get("schema") or {}
            ticket = (schema.get("entities") or {}).get("ticket") or {}
            labels = schema.get("labels") or {}
            thicken = schema.get("approveThicken") or {}
            for k, v in expect_flags.items():
                if isinstance(v, bool):
                    self.assertEqual(bool(ticket.get(k)), v, f"{domain}.{k}")
                else:
                    self.assertEqual(int(ticket.get(k) or 0), int(v), f"{domain}.{k}")
            for lk in label_keys:
                self.assertIn(lk, labels, f"{domain} labels.{lk}")
            for tk, tv in thicken_flags.items():
                self.assertEqual(bool(thicken.get(tk)), tv, f"{domain} thicken.{tk}")
            yml = policy_preview(domain, out)
            for needle in yml_needles:
                self.assertIn(needle, yml, f"{domain} {needle}")
            text = domain_sql(
                domain,
                "db_b7",
                capabilities=list(out.get("capabilities") or []),
                title=title,
                ticket_flags=ticket,
            )
            for col in cols:
                self.assertIn(col, text, f"{domain} sql {col}")
            if archive_col:
                self.assertIn(archive_col, text, f"{domain} archive {archive_col}")

        cert = _spec("DOM-CERT", "证明", "")
        ct = ((cert.get("schema") or {}).get("entities") or {}).get("ticket") or {}
        self.assertFalse(bool(ct.get("allowDocRev")))
        self.assertFalse(bool(ct.get("allowFitoutQuiet")))
        fleet = _spec("DOM-FLEET", "用车", "")
        ft = ((fleet.get("schema") or {}).get("entities") or {}).get("ticket") or {}
        self.assertFalse(bool(ft.get("allowCertIssueNo")))
        self.assertFalse(bool(ft.get("allowPromoFeedback")))
        labor = _spec("DOM-LABOR", "劳动", "")
        lt = ((labor.get("schema") or {}).get("entities") or {}).get("ticket") or {}
        self.assertFalse(bool(lt.get("allowFitoutQuiet")))
        self.assertFalse(bool(lt.get("requireApplyInvite")))

    def test_batch8_rules_skins(self) -> None:
        """第八批：用印现场照/份数上限/签署方/学时累计/年检到期/成员变更。"""
        cases = [
            (
                "DOM-SEAL",
                "用印申请",
                {"requireCloseAttach": True, "allowSealClosePhoto": True},
                [],
                ["ticket-require-close-attach: true", "ticket-allow-seal-close-photo: true"],
                ["sealPhotoLabel", "sealPhotoHint"],
                {"sealClosePhoto": True},
                None,
            ),
            (
                "DOM-CERT",
                "证明开具",
                {"allowIssueCopies": True},
                ["issue_copies"],
                ["ticket-allow-issue-copies: true"],
                ["issueCopiesLabel", "issueCopiesHint"],
                {"issueCopies": True},
                "max_issue_copies",
            ),
            (
                "DOM-CONTRACT",
                "合同审批",
                {"allowSignParties": True},
                ["sign_parties"],
                ["ticket-allow-sign-parties: true"],
                ["signPartiesLabel", "signPartiesHint"],
                {"signParties": True},
                None,
            ),
            (
                "DOM-LABSAFE",
                "实验室准入",
                {"allowTrainHours": True},
                ["train_hours"],
                ["ticket-allow-train-hours: true"],
                ["trainHoursLabel", "trainHoursHint"],
                {"trainHours": True},
                "train_hours_total",
            ),
            (
                "DOM-CARPASS",
                "车辆通行证",
                {"allowInspectExpire": True, "notifyArchiveExpireDays": 7},
                [],
                ["ticket-allow-inspect-expire: true", "ticket-notify-archive-expire-days: 7"],
                ["inspectExpireOnLabel", "inspectExpireHint"],
                {"inspectExpire": True},
                "inspect_expire_on",
            ),
            (
                "DOM-PROJ",
                "大创项目",
                {"allowMemberChange": True},
                ["member_change_note"],
                ["ticket-allow-member-change: true"],
                ["memberChangeNoteLabel", "memberChangeNoteHint"],
                {"memberChange": True},
                None,
            ),
        ]
        for (
            domain,
            title,
            expect_flags,
            cols,
            yml_needles,
            label_keys,
            thicken_flags,
            archive_col,
        ) in cases:
            out = _spec(domain, title, "")
            schema = out.get("schema") or {}
            ticket = (schema.get("entities") or {}).get("ticket") or {}
            labels = schema.get("labels") or {}
            thicken = schema.get("approveThicken") or {}
            for k, v in expect_flags.items():
                if isinstance(v, bool):
                    self.assertEqual(bool(ticket.get(k)), v, f"{domain}.{k}")
                else:
                    self.assertEqual(int(ticket.get(k) or 0), int(v), f"{domain}.{k}")
            for lk in label_keys:
                self.assertIn(lk, labels, f"{domain} labels.{lk}")
            for tk, tv in thicken_flags.items():
                self.assertEqual(bool(thicken.get(tk)), tv, f"{domain} thicken.{tk}")
            yml = policy_preview(domain, out)
            for needle in yml_needles:
                self.assertIn(needle, yml, f"{domain} {needle}")
            text = domain_sql(
                domain,
                "db_b8",
                capabilities=list(out.get("capabilities") or []),
                title=title,
                ticket_flags=ticket,
            )
            for col in cols:
                self.assertIn(col, text, f"{domain} sql {col}")
            if archive_col:
                self.assertIn(archive_col, text, f"{domain} archive {archive_col}")

        fleet = _spec("DOM-FLEET", "用车", "")
        ft = ((fleet.get("schema") or {}).get("entities") or {}).get("ticket") or {}
        self.assertFalse(bool(ft.get("allowSealClosePhoto")))
        self.assertFalse(bool(ft.get("allowIssueCopies")))
        self.assertFalse(bool(ft.get("allowSignParties")))
        labor = _spec("DOM-LABOR", "劳动", "")
        lt = ((labor.get("schema") or {}).get("entities") or {}).get("ticket") or {}
        self.assertFalse(bool(lt.get("allowTrainHours")))
        self.assertFalse(bool(lt.get("allowInspectExpire")))
        self.assertFalse(bool(lt.get("allowMemberChange")))
        visitor = _spec("DOM-VISITOR", "访客", "")
        vt = ((visitor.get("schema") or {}).get("entities") or {}).get("ticket") or {}
        self.assertFalse(bool(vt.get("allowInspectExpire")))

    def test_batch9_rules_skins(self) -> None:
        cases = [
            (
                "DOM-PROCURE",
                "采购申购",
                {"allowProcureBudget": True},
                ["procure_amount"],
                ["ticket-allow-procure-budget: true"],
                ["procureAmountLabel", "procureBudgetHint"],
                {"procureBudget": True},
                "budget_total",
            ),
            (
                "DOM-CHECKIN",
                "查寝登记",
                {"allowCheckinException": True},
                ["exception_type"],
                ["ticket-allow-checkin-exception: true"],
                ["exceptionTypeLabel", "exceptionTypeHint"],
                {"checkinException": True},
                None,
            ),
            (
                "DOM-VISITOR",
                "访客预约",
                {"allowVisitPurpose": True},
                ["visit_purpose"],
                ["ticket-allow-visit-purpose: true"],
                ["visitPurposeLabel", "visitPurposeHint"],
                {"visitPurpose": True},
                None,
            ),
            (
                "DOM-FLEET",
                "公务用车",
                {"allowFleetViolation": True},
                ["violation_person"],
                ["ticket-allow-fleet-violation: true"],
                ["violationPersonLabel", "violationPersonHint"],
                {"fleetViolation": True},
                None,
            ),
            (
                "DOM-FITOUT",
                "装修报备",
                {"allowFitoutRectify": True},
                ["rectify_note"],
                ["ticket-allow-fitout-rectify: true"],
                ["rectifyNoteLabel", "rectifyNoteHint"],
                {"fitoutRectify": True},
                None,
            ),
            (
                "DOM-PROJ",
                "大创项目",
                {"allowProjNodeRemind": True, "notifyArchiveExpireDays": 7},
                [],
                ["ticket-allow-proj-node-remind: true"],
                ["midDueOnLabel", "finalDueOnLabel", "projNodeRemindHint"],
                {"projNodeRemind": True},
                "mid_due_on",
            ),
        ]
        for (
            domain,
            title,
            expect_flags,
            cols,
            yml_needles,
            label_keys,
            thicken_flags,
            archive_col,
        ) in cases:
            out = _spec(domain, title, "")
            schema = out.get("schema") or {}
            ticket = (schema.get("entities") or {}).get("ticket") or {}
            labels = schema.get("labels") or {}
            thicken = schema.get("approveThicken") or {}
            for k, v in expect_flags.items():
                if isinstance(v, bool):
                    self.assertEqual(bool(ticket.get(k)), v, f"{domain}.{k}")
                else:
                    self.assertEqual(int(ticket.get(k) or 0), int(v), f"{domain}.{k}")
            for lk in label_keys:
                self.assertIn(lk, labels, f"{domain} labels.{lk}")
            for tk, tv in thicken_flags.items():
                self.assertEqual(bool(thicken.get(tk)), tv, f"{domain} thicken.{tk}")
            yml = policy_preview(domain, out)
            for needle in yml_needles:
                self.assertIn(needle, yml, f"{domain} {needle}")
            text = domain_sql(
                domain,
                "db_b9",
                capabilities=list(out.get("capabilities") or []),
                title=title,
                ticket_flags=ticket,
            )
            for col in cols:
                self.assertIn(col, text, f"{domain} sql {col}")
            if archive_col:
                self.assertIn(archive_col, text, f"{domain} archive {archive_col}")

        chk = _spec("DOM-CHECKIN", "查寝", "")
        ct = ((chk.get("schema") or {}).get("entities") or {}).get("ticket") or {}
        self.assertTrue(list(ct.get("exceptionTypeOptions") or []))
        vis = _spec("DOM-VISITOR", "访客", "")
        vt = ((vis.get("schema") or {}).get("entities") or {}).get("ticket") or {}
        self.assertTrue(list(vt.get("visitPurposeOptions") or []))
        self.assertFalse(bool(vt.get("allowCheckinException")))
        fleet = _spec("DOM-FLEET", "用车", "")
        ft = ((fleet.get("schema") or {}).get("entities") or {}).get("ticket") or {}
        self.assertFalse(bool(ft.get("allowProcureBudget")))
        self.assertFalse(bool(ft.get("requireCloseAttach")))
        labor = _spec("DOM-LABOR", "劳动", "")
        lt = ((labor.get("schema") or {}).get("entities") or {}).get("ticket") or {}
        self.assertFalse(bool(lt.get("allowFitoutRectify")))
        self.assertFalse(bool(lt.get("allowFleetViolation")))

    def test_batch10_rules_skins(self) -> None:
        cases = [
            (
                "DOM-CLUB",
                "社团年审",
                {"allowClubCopyLast": True},
                [],
                ["ticket-allow-club-copy-last: true"],
                ["clubCopyLastLabel", "clubCopyLastHint"],
                {"clubCopyLast": True},
                None,
            ),
            (
                "DOM-PROCURE",
                "采购申购",
                {"allowProcureReturn": True},
                ["return_note", "return_fail"],
                ["ticket-allow-procure-return: true"],
                ["returnNoteLabel", "procureReturnHint"],
                {"procureReturn": True},
                None,
            ),
            (
                "DOM-MORAL",
                "综合测评",
                {"allowMoralObjection": True},
                ["objection_note", "objection_due_at"],
                ["ticket-allow-moral-objection: true"],
                ["moralObjectionLabel", "moralObjectionHint"],
                {"moralObjection": True},
                None,
            ),
            (
                "DOM-PROJ",
                "大创项目",
                {"allowProjFundUse": True},
                ["fund_use_yuan", "fund_use_note"],
                ["ticket-allow-proj-fund-use: true"],
                ["fundUseYuanLabel", "fundUseNoteLabel", "fundUseHint"],
                {"projFundUse": True},
                None,
            ),
            (
                "DOM-EVAL",
                "教学评价",
                {"allowEvalDimWeight": True},
                [],
                ["ticket-allow-eval-dim-weight: true"],
                ["evalDimWeightHint", "teachingWeightLabel"],
                {"evalDimWeight": True},
                "teaching_weight",
            ),
            (
                "DOM-VISITOR",
                "访客预约",
                {"allowVisitSlotRemain": True},
                ["visit_on"],
                ["ticket-allow-visit-slot-remain: true"],
                ["visitOnLabel", "visitSlotRemainHint", "visitSlotCapLabel"],
                {"visitSlotRemain": True},
                "visit_slot_cap",
            ),
        ]
        for (
            domain,
            title,
            expect_flags,
            cols,
            yml_needles,
            label_keys,
            thicken_flags,
            archive_col,
        ) in cases:
            out = _spec(domain, title, "")
            schema = out.get("schema") or {}
            ticket = (schema.get("entities") or {}).get("ticket") or {}
            labels = schema.get("labels") or {}
            thicken = schema.get("approveThicken") or {}
            for k, v in expect_flags.items():
                self.assertEqual(bool(ticket.get(k)), v, f"{domain}.{k}")
            for lk in label_keys:
                self.assertIn(lk, labels, f"{domain} labels.{lk}")
            for tk, tv in thicken_flags.items():
                self.assertEqual(bool(thicken.get(tk)), tv, f"{domain} thicken.{tk}")
            yml = policy_preview(domain, out)
            for needle in yml_needles:
                self.assertIn(needle, yml, f"{domain} {needle}")
            self.assertNotIn("ticket-allow-objection-window: true", yml)
            text = domain_sql(
                domain,
                "db_b10",
                capabilities=list(out.get("capabilities") or []),
                title=title,
                ticket_flags=ticket,
            )
            for col in cols:
                self.assertIn(col, text, f"{domain} sql {col}")
            if archive_col:
                self.assertIn(archive_col, text, f"{domain} archive {archive_col}")

        eval_spec = _spec("DOM-EVAL", "评教", "")
        et = ((eval_spec.get("schema") or {}).get("entities") or {}).get("ticket") or {}
        dims = et.get("ratingDims") or []
        self.assertTrue(any(isinstance(d, dict) and d.get("weight") is not None for d in dims))
        moral = _spec("DOM-MORAL", "综测", "")
        mt = ((moral.get("schema") or {}).get("entities") or {}).get("ticket") or {}
        self.assertFalse(bool(mt.get("allowObjectionWindow")))
        fleet = _spec("DOM-FLEET", "用车", "")
        ft = ((fleet.get("schema") or {}).get("entities") or {}).get("ticket") or {}
        self.assertFalse(bool(ft.get("allowClubCopyLast")))
        self.assertFalse(bool(ft.get("allowProcureReturn")))
        self.assertFalse(bool(ft.get("allowMoralObjection")))
        self.assertFalse(bool(ft.get("allowProjFundUse")))
        self.assertFalse(bool(ft.get("allowEvalDimWeight")))
        self.assertFalse(bool(ft.get("allowVisitSlotRemain")))
        labor = _spec("DOM-LABOR", "劳动", "")
        lt = ((labor.get("schema") or {}).get("entities") or {}).get("ticket") or {}
        self.assertFalse(bool(lt.get("allowVisitSlotRemain")))
        vis = _spec("DOM-VISITOR", "访客", "")
        vt = ((vis.get("schema") or {}).get("entities") or {}).get("ticket") or {}
        self.assertTrue(bool(vt.get("allowVisitPurpose")))
        self.assertTrue(bool(vt.get("allowVisitSlotRemain")))

    def test_batch11_rules_skins(self) -> None:
        cases = [
            (
                "DOM-PROJ",
                "大创项目",
                {"allowPlagiarismUrl": True},
                ["plagiarism_url"],
                ["ticket-allow-plagiarism-url: true"],
                ["plagiarismUrlLabel", "plagiarismUrlHint"],
                {"plagiarismUrl": True},
                None,
            ),
            (
                "DOM-CHECKIN",
                "查寝归寝",
                {"allowAbsentStreak": True},
                [],
                ["ticket-allow-absent-streak: true"],
                ["absentWarnNLabel", "absentStreakHint"],
                {"absentStreak": True},
                "absent_warn_n",
            ),
            (
                "DOM-PARTY",
                "党员发展",
                {"allowPartyStage": True},
                ["party_stage", "stage_on"],
                ["ticket-allow-party-stage: true"],
                ["partyStageLabel", "stageOnLabel", "partyStageHint"],
                {"partyStage": True},
                None,
            ),
            (
                "DOM-EVAL",
                "教学评价",
                {"allowEvalObserve": True},
                ["observe_on", "observe_note"],
                ["ticket-allow-eval-observe: true"],
                ["observeOnLabel", "observeNoteLabel", "evalObserveHint"],
                {"evalObserve": True},
                None,
            ),
            (
                "DOM-ACAD",
                "学籍异动",
                {"allowScheduleImpact": True},
                ["schedule_impact_note"],
                ["ticket-allow-schedule-impact: true"],
                ["scheduleImpactNoteLabel", "scheduleImpactHint"],
                {"scheduleImpact": True},
                None,
            ),
            (
                "DOM-CONTRACT",
                "合同审批",
                {"allowContractAmount": True},
                ["contract_amount"],
                ["ticket-allow-contract-amount: true"],
                ["contractAmountLabel", "contractAmountCnLabel", "contractAmountHint"],
                {"contractAmount": True},
                None,
            ),
        ]
        for (
            domain,
            title,
            expect_flags,
            cols,
            yml_needles,
            label_keys,
            thicken_flags,
            archive_col,
        ) in cases:
            out = _spec(domain, title, "")
            schema = out.get("schema") or {}
            ticket = (schema.get("entities") or {}).get("ticket") or {}
            labels = schema.get("labels") or {}
            thicken = schema.get("approveThicken") or {}
            for k, v in expect_flags.items():
                self.assertEqual(bool(ticket.get(k)), v, f"{domain}.{k}")
            for lk in label_keys:
                self.assertIn(lk, labels, f"{domain} labels.{lk}")
            for tk, tv in thicken_flags.items():
                self.assertEqual(bool(thicken.get(tk)), tv, f"{domain} thicken.{tk}")
            yml = policy_preview(domain, out)
            for needle in yml_needles:
                self.assertIn(needle, yml, f"{domain} {needle}")
            text = domain_sql(
                domain,
                "db_b11",
                capabilities=list(out.get("capabilities") or []),
                title=title,
                ticket_flags=ticket,
            )
            for col in cols:
                self.assertIn(col, text, f"{domain} sql {col}")
            if archive_col:
                self.assertIn(archive_col, text, f"{domain} archive {archive_col}")

        party = _spec("DOM-PARTY", "党员发展", "")
        pt = ((party.get("schema") or {}).get("entities") or {}).get("ticket") or {}
        self.assertTrue(list(pt.get("partyStageOptions") or []))
        fleet = _spec("DOM-FLEET", "用车", "")
        ft = ((fleet.get("schema") or {}).get("entities") or {}).get("ticket") or {}
        self.assertFalse(bool(ft.get("allowPlagiarismUrl")))
        self.assertFalse(bool(ft.get("allowAbsentStreak")))
        self.assertFalse(bool(ft.get("allowPartyStage")))
        self.assertFalse(bool(ft.get("allowEvalObserve")))
        self.assertFalse(bool(ft.get("allowScheduleImpact")))
        self.assertFalse(bool(ft.get("allowContractAmount")))
        proj = _spec("DOM-PROJ", "大创", "")
        jt = ((proj.get("schema") or {}).get("entities") or {}).get("ticket") or {}
        self.assertTrue(bool(jt.get("allowProjFundUse")))
        self.assertTrue(bool(jt.get("allowPlagiarismUrl")))
        self.assertFalse(bool(jt.get("requireCloseAttach")))
        eval_spec = _spec("DOM-EVAL", "评教", "")
        et = ((eval_spec.get("schema") or {}).get("entities") or {}).get("ticket") or {}
        self.assertTrue(bool(et.get("allowEvalDimWeight")))
        self.assertTrue(bool(et.get("allowEvalObserve")))
        acad = _spec("DOM-ACAD", "学籍", "")
        at = ((acad.get("schema") or {}).get("entities") or {}).get("ticket") or {}
        self.assertTrue(bool(at.get("allowEffectiveOn")))
        self.assertTrue(bool(at.get("allowScheduleImpact")))

    def test_batch12_rules_skins(self) -> None:
        cases = [
            (
                "DOM-EXPENSE",
                "报销申请",
                {"allowExpenseLines": True},
                ["ticket_expense_line", "fk_ticket_expense_line_ticket"],
                ["ticket-allow-expense-lines: true"],
                ["expenseLinesLabel", "expenseLinesHint", "expenseLineCategoryLabel"],
                {"expenseLines": True},
                None,
            ),
            (
                "DOM-TRIP",
                "出差审批",
                {"allowTripLegs": True},
                ["ticket_trip_leg", "fk_ticket_trip_leg_ticket"],
                ["ticket-allow-trip-legs: true"],
                ["tripLegsLabel", "tripLegsHint", "tripLegFromLabel"],
                {"tripLegs": True},
                None,
            ),
            (
                "DOM-EVAL",
                "教学评价",
                {"allowHideEvalResult": True},
                [],
                ["ticket-allow-hide-eval-result: true"],
                ["hideEvalResultLabel", "hideEvalResultHint"],
                {"hideEvalResult": True},
                "hide_eval_result",
            ),
            (
                "DOM-CONTRACT",
                "合同审批",
                {"allowSignRemarkVisible": True},
                [],
                ["ticket-allow-sign-remark-visible: true"],
                ["signRemarkVisibleLabel", "signApproveRemarkLabel", "signRemarkVisibleHint"],
                {"signRemarkVisible": True},
                "sign_remark_visible",
            ),
            (
                "DOM-PROJ",
                "大创项目",
                {"allowProjChangeLog": True},
                ["change_log_note"],
                ["ticket-allow-proj-change-log: true"],
                ["changeLogNoteLabel", "projChangeLogHint"],
                {"projChangeLog": True},
                None,
            ),
            (
                "DOM-CERT",
                "证明开具",
                {"allowCertVerify": True},
                ["verify_code"],
                ["ticket-allow-cert-verify: true"],
                ["certVerifyCodeLabel", "certVerifyHint", "certVerifyPageTitle"],
                {"certVerify": True},
                None,
            ),
        ]
        for (
            domain,
            title,
            expect_flags,
            cols,
            yml_needles,
            label_keys,
            thicken_flags,
            archive_col,
        ) in cases:
            out = _spec(domain, title, "")
            schema = out.get("schema") or {}
            ticket = (schema.get("entities") or {}).get("ticket") or {}
            labels = schema.get("labels") or {}
            thicken = schema.get("approveThicken") or {}
            for k, v in expect_flags.items():
                self.assertEqual(bool(ticket.get(k)), v, f"{domain}.{k}")
            for lk in label_keys:
                self.assertIn(lk, labels, f"{domain} labels.{lk}")
            for tk, tv in thicken_flags.items():
                self.assertEqual(bool(thicken.get(tk)), tv, f"{domain} thicken.{tk}")
            yml = policy_preview(domain, out)
            for needle in yml_needles:
                self.assertIn(needle, yml, f"{domain} {needle}")
            text = domain_sql(
                domain,
                "db_b12",
                capabilities=list(out.get("capabilities") or []),
                title=title,
                ticket_flags=ticket,
            )
            for col in cols:
                self.assertIn(col, text, f"{domain} sql {col}")
            if archive_col:
                self.assertIn(archive_col, text, f"{domain} archive {archive_col}")

        expense = _spec("DOM-EXPENSE", "报销", "")
        et = ((expense.get("schema") or {}).get("entities") or {}).get("ticket") or {}
        self.assertTrue(bool(et.get("allowExpenseInvoice")))
        self.assertTrue(bool(et.get("allowExpenseLines")))
        self.assertTrue(list(et.get("expenseLineCategoryOptions") or []))
        fleet = _spec("DOM-FLEET", "用车", "")
        ft = ((fleet.get("schema") or {}).get("entities") or {}).get("ticket") or {}
        self.assertFalse(bool(ft.get("allowExpenseLines")))
        self.assertFalse(bool(ft.get("allowTripLegs")))
        self.assertFalse(bool(ft.get("allowHideEvalResult")))
        self.assertFalse(bool(ft.get("allowSignRemarkVisible")))
        self.assertFalse(bool(ft.get("allowProjChangeLog")))
        self.assertFalse(bool(ft.get("allowCertVerify")))
        proj = _spec("DOM-PROJ", "大创", "")
        jt = ((proj.get("schema") or {}).get("entities") or {}).get("ticket") or {}
        self.assertTrue(bool(jt.get("allowPlagiarismUrl")))
        self.assertTrue(bool(jt.get("allowProjChangeLog")))
        cert = _spec("DOM-CERT", "证明", "")
        ct = ((cert.get("schema") or {}).get("entities") or {}).get("ticket") or {}
        self.assertTrue(bool(ct.get("allowCertIssueNo")))
        self.assertTrue(bool(ct.get("allowCertVerify")))
        fleet_sql = domain_sql(
            "DOM-FLEET",
            "db_b12_fleet",
            capabilities=list(fleet.get("capabilities") or []),
            title="用车",
            ticket_flags=ft,
        )
        self.assertNotIn("ticket_expense_line", fleet_sql)
        self.assertNotIn("ticket_trip_leg", fleet_sql)
        self.assertNotIn("expense_lines_json", fleet_sql)
        self.assertNotIn("trip_legs_json", fleet_sql)
        expense_sql = domain_sql(
            "DOM-EXPENSE",
            "db_b12_exp_nf",
            capabilities=list(expense.get("capabilities") or []),
            title="报销",
            ticket_flags=et,
        )
        self.assertNotIn("expense_lines_json", expense_sql)
        self.assertIn("REFERENCES `expense_apply` (id)", expense_sql)
        er = schema_model(expense_sql)
        self.assertIn("ticket_expense_line", {t["name"] for t in er["tables"]})
        self.assertNotIn("ticket_expense_line", set(er.get("link_tables") or []))
        hit = False
        for r in er.get("relations") or []:
            if r.get("right") == "ticket_expense_line" and r.get("via") == "ticket_id":
                self.assertEqual(r.get("left"), "expense_apply")
                self.assertEqual(r.get("card_left"), "1")
                self.assertEqual(r.get("card_right"), "n")
                hit = True
        self.assertTrue(hit)
        by = {t["name"]: t for t in er["tables"]}
        self.assertEqual(by["ticket_expense_line"]["label"], "报销明细")
        rel_lab = next(
            r.get("label")
            for r in (er.get("relations") or [])
            if r.get("right") == "ticket_expense_line" and r.get("via") == "ticket_id"
        )
        self.assertEqual(rel_lab, "明细")
        trip = _spec("DOM-TRIP", "出差", "")
        tt = ((trip.get("schema") or {}).get("entities") or {}).get("ticket") or {}
        trip_sql = domain_sql(
            "DOM-TRIP",
            "db_b12_trip_er",
            capabilities=list(trip.get("capabilities") or []),
            title="出差",
            ticket_flags=tt,
        )
        ter = schema_model(trip_sql)
        tby = {t["name"]: t for t in ter["tables"]}
        self.assertEqual(tby["ticket_trip_leg"]["label"], "出差行程")
        trip_hit = False
        for r in ter.get("relations") or []:
            if r.get("right") == "ticket_trip_leg" and r.get("via") == "ticket_id":
                self.assertEqual(r.get("card_right"), "n")
                self.assertEqual(r.get("label"), "分段")
                trip_hit = True
        self.assertTrue(trip_hit)

    def test_batch13_rules_skins(self) -> None:
        cases = [
            (
                "DOM-VISITOR",
                "访客预约",
                {"allowVisitWalkIn": True},
                ["walk_in"],
                ["ticket-allow-visit-walk-in: true"],
                ["visitWalkInLabel", "visitWalkInForLabel", "visitWalkInHint"],
                {"visitWalkIn": True},
                None,
            ),
            (
                "DOM-CHECKIN",
                "查寝登记",
                {"allowCheckinProxy": True},
                ["checkin_proxy_by"],
                ["ticket-allow-checkin-proxy: true"],
                ["checkinProxyLabel", "checkinProxyForLabel", "checkinProxyByLabel", "checkinProxyHint"],
                {"checkinProxy": True},
                None,
            ),
            (
                "DOM-CLUB",
                "社团年审",
                {"allowClubRoster": True},
                ["ticket_club_member", "fk_ticket_club_member_ticket"],
                ["ticket-allow-club-roster: true"],
                ["clubRosterLabel", "clubMemberNameLabel", "clubMemberNoLabel", "clubRosterHint"],
                {"clubRoster": True},
                None,
            ),
            (
                "DOM-CARPASS",
                "车辆通行证",
                {"allowCarpassParkingMutex": True},
                ["parking_on"],
                ["ticket-allow-carpass-parking-mutex: true"],
                ["parkingOnLabel", "parkingMutexLabel", "carpassParkingMutexHint"],
                {"carpassParkingMutex": True},
                "parking_mutex",
            ),
            (
                "DOM-EVAL",
                "教学评价",
                {"allowEvalUrge": True},
                [],
                ["ticket-allow-eval-urge: true"],
                ["evalUrgeLabel", "evalUrgeHint"],
                {"evalUrge": True},
                None,
            ),
            (
                "DOM-CONTRACT",
                "合同审批",
                {"allowContractRenew": True},
                ["renew_on", "renew_note"],
                ["ticket-allow-contract-renew: true"],
                ["renewOnLabel", "renewNoteLabel", "contractRenewHint"],
                {"contractRenew": True},
                None,
            ),
        ]
        for (
            domain,
            title,
            expect_flags,
            cols,
            yml_needles,
            label_keys,
            thicken_flags,
            archive_col,
        ) in cases:
            out = _spec(domain, title, "")
            schema = out.get("schema") or {}
            ticket = (schema.get("entities") or {}).get("ticket") or {}
            labels = schema.get("labels") or {}
            thicken = schema.get("approveThicken") or {}
            for k, v in expect_flags.items():
                self.assertEqual(bool(ticket.get(k)), v, f"{domain}.{k}")
            for lk in label_keys:
                self.assertIn(lk, labels, f"{domain} labels.{lk}")
            for tk, tv in thicken_flags.items():
                self.assertEqual(bool(thicken.get(tk)), tv, f"{domain} thicken.{tk}")
            yml = policy_preview(domain, out)
            for needle in yml_needles:
                self.assertIn(needle, yml, f"{domain} {needle}")
            text = domain_sql(
                domain,
                "db_b13",
                capabilities=list(out.get("capabilities") or []),
                title=title,
                ticket_flags=ticket,
            )
            for col in cols:
                self.assertIn(col, text, f"{domain} sql {col}")
            if archive_col:
                self.assertIn(archive_col, text, f"{domain} archive {archive_col}")

        visitor = _spec("DOM-VISITOR", "访客", "")
        vt = ((visitor.get("schema") or {}).get("entities") or {}).get("ticket") or {}
        self.assertTrue(bool(vt.get("allowVisitSlotRemain")))
        self.assertTrue(bool(vt.get("allowVisitWalkIn")))
        checkin = _spec("DOM-CHECKIN", "查寝", "")
        ct = ((checkin.get("schema") or {}).get("entities") or {}).get("ticket") or {}
        self.assertTrue(bool(ct.get("allowAbsentStreak")))
        self.assertTrue(bool(ct.get("allowCheckinProxy")))
        club = _spec("DOM-CLUB", "社团", "")
        lt = ((club.get("schema") or {}).get("entities") or {}).get("ticket") or {}
        self.assertTrue(bool(lt.get("allowClubCopyLast")))
        self.assertTrue(bool(lt.get("allowClubRoster")))
        eval_spec = _spec("DOM-EVAL", "评教", "")
        et = ((eval_spec.get("schema") or {}).get("entities") or {}).get("ticket") or {}
        self.assertTrue(bool(et.get("allowHideEvalResult")))
        self.assertTrue(bool(et.get("allowEvalUrge")))
        contract = _spec("DOM-CONTRACT", "合同", "")
        kt = ((contract.get("schema") or {}).get("entities") or {}).get("ticket") or {}
        self.assertTrue(bool(kt.get("allowContractAmount")))
        self.assertTrue(bool(kt.get("allowContractRenew")))
        fleet = _spec("DOM-FLEET", "用车", "")
        ft = ((fleet.get("schema") or {}).get("entities") or {}).get("ticket") or {}
        self.assertFalse(bool(ft.get("allowVisitWalkIn")))
        self.assertFalse(bool(ft.get("allowCheckinProxy")))
        self.assertFalse(bool(ft.get("allowClubRoster")))
        self.assertFalse(bool(ft.get("allowCarpassParkingMutex")))
        self.assertFalse(bool(ft.get("allowEvalUrge")))
        self.assertFalse(bool(ft.get("allowContractRenew")))
        fleet_sql = domain_sql(
            "DOM-FLEET",
            "db_b13_fleet",
            capabilities=list(fleet.get("capabilities") or []),
            title="用车",
            ticket_flags=ft,
        )
        self.assertNotIn("ticket_club_member", fleet_sql)
        self.assertNotIn("walk_in", fleet_sql)
        self.assertNotIn("checkin_proxy_by", fleet_sql)
        club_sql = domain_sql(
            "DOM-CLUB",
            "db_b13_club_nf",
            capabilities=list(club.get("capabilities") or []),
            title="社团",
            ticket_flags=lt,
        )
        self.assertIn("REFERENCES `club_apply` (id)", club_sql)
        self.assertNotIn("club_members_json", club_sql)
        er = schema_model(club_sql)
        self.assertIn("ticket_club_member", {t["name"] for t in er["tables"]})
        self.assertNotIn("ticket_club_member", set(er.get("link_tables") or []))
        hit = False
        for r in er.get("relations") or []:
            if r.get("right") == "ticket_club_member" and r.get("via") == "ticket_id":
                self.assertEqual(r.get("card_right"), "n")
                self.assertEqual(r.get("label"), "名册")
                hit = True
        self.assertTrue(hit)


    def test_batch14_rules_skins(self) -> None:
        cases = [
            (
                "DOM-CONTRACT",
                "合同审批",
                {"allowContractExpireRemind": True},
                [],
                [
                    "ticket-allow-contract-expire-remind: true",
                    "ticket-notify-archive-expire-days: 7",
                ],
                [
                    "contractExpireRemindHint",
                    "contractExpireRemindTitle",
                ],
                {"contractExpireRemind": True},
                None,
            ),
            (
                "DOM-CERT",
                "证明开具",
                {"allowCertPickupRedeem": True},
                ["pickup_redeem_code", "pickup_redeemed"],
                ["ticket-allow-cert-pickup-redeem: true"],
                [
                    "pickupRedeemCodeLabel",
                    "pickupRedeemedLabel",
                    "pickupRedeemHint",
                ],
                {"certPickupRedeem": True},
                None,
            ),
            (
                "DOM-LABSAFE",
                "实验室准入",
                {"allowExamPassMin": True},
                [],
                ["ticket-allow-exam-pass-min: true"],
                ["examPassMinLabel", "examPassMinHint"],
                {"examPassMin": True},
                "exam_pass_min",
            ),
            (
                "DOM-CHECKIN",
                "查寝登记",
                {"allowCheckinSpot": True},
                ["checkin_spot_task", "checkin_spot_member", "fk_checkin_spot_member_task"],
                ["ticket-allow-checkin-spot: true"],
                [
                    "checkinSpotLabel",
                    "checkinSpotSampleLabel",
                    "checkinSpotOnLabel",
                    "checkinSpotHint",
                ],
                {"checkinSpot": True},
                None,
            ),
            (
                "DOM-EVAL",
                "教学评价",
                {"allowEvalBeforeGrade": True},
                [],
                ["ticket-allow-eval-before-grade: true"],
                ["evalBeforeGradeHint"],
                {"evalBeforeGrade": True},
                None,
            ),
            (
                "DOM-FLEET",
                "用车申请",
                {"allowApproveDurationStats": True},
                [],
                ["ticket-allow-approve-duration-stats: true"],
                ["approveDurationStatsLabel", "approveDurationStatsHint"],
                {"approveDurationStats": True},
                None,
            ),
        ]
        for (
            domain,
            title,
            expect_flags,
            cols,
            yml_needles,
            label_keys,
            thicken_flags,
            archive_col,
        ) in cases:
            out = _spec(domain, title, "")
            schema = out.get("schema") or {}
            ticket = (schema.get("entities") or {}).get("ticket") or {}
            labels = schema.get("labels") or {}
            thicken = schema.get("approveThicken") or {}
            for k, v in expect_flags.items():
                self.assertEqual(bool(ticket.get(k)), v, f"{domain}.{k}")
            for lk in label_keys:
                self.assertIn(lk, labels, f"{domain} labels.{lk}")
            for tk, tv in thicken_flags.items():
                self.assertEqual(bool(thicken.get(tk)), tv, f"{domain} thicken.{tk}")
            yml = policy_preview(domain, out)
            for needle in yml_needles:
                self.assertIn(needle, yml, f"{domain} {needle}")
            text = domain_sql(
                domain,
                "db_b14",
                capabilities=list(out.get("capabilities") or []),
                title=title,
                ticket_flags=ticket,
            )
            for col in cols:
                self.assertIn(col, text, f"{domain} sql {col}")
            if archive_col:
                self.assertIn(archive_col, text, f"{domain} archive {archive_col}")

        contract = _spec("DOM-CONTRACT", "合同", "")
        kt = ((contract.get("schema") or {}).get("entities") or {}).get("ticket") or {}
        self.assertTrue(bool(kt.get("allowContractRenew")))
        self.assertTrue(bool(kt.get("allowContractExpireRemind")))
        eval_spec = _spec("DOM-EVAL", "评教", "")
        et = ((eval_spec.get("schema") or {}).get("entities") or {}).get("ticket") or {}
        self.assertTrue(bool(et.get("allowEvalUrge")))
        self.assertTrue(bool(et.get("allowEvalBeforeGrade")))
        checkin = _spec("DOM-CHECKIN", "查寝", "")
        ct = ((checkin.get("schema") or {}).get("entities") or {}).get("ticket") or {}
        self.assertTrue(bool(ct.get("allowCheckinProxy")))
        self.assertTrue(bool(ct.get("allowCheckinSpot")))
        fleet = _spec("DOM-FLEET", "用车", "")
        ft = ((fleet.get("schema") or {}).get("entities") or {}).get("ticket") or {}
        self.assertTrue(bool(ft.get("allowApproveDurationStats")))
        self.assertFalse(bool(ft.get("allowCertPickupRedeem")))
        self.assertFalse(bool(ft.get("allowExamPassMin")))
        self.assertFalse(bool(ft.get("allowCheckinSpot")))
        self.assertFalse(bool(ft.get("allowEvalBeforeGrade")))
        self.assertFalse(bool(ft.get("allowContractExpireRemind")))
        fleet_sql = domain_sql(
            "DOM-FLEET",
            "db_b14_fleet",
            capabilities=list(fleet.get("capabilities") or []),
            title="用车",
            ticket_flags=ft,
        )
        self.assertNotIn("checkin_spot_task", fleet_sql)
        self.assertNotIn("pickup_redeem_code", fleet_sql)
        self.assertNotIn("exam_pass_min", fleet_sql)
        cert_sql = domain_sql(
            "DOM-CERT",
            "db_b14_cert",
            capabilities=list(_spec("DOM-CERT", "证明", "").get("capabilities") or []),
            title="证明",
            ticket_flags=(( _spec("DOM-CERT", "证明", "").get("schema") or {}).get("entities") or {}).get("ticket") or {},
        )
        self.assertIn("pickup_redeem_code", cert_sql)
        self.assertNotIn("checkin_spot_task", cert_sql)
        checkin_sql = domain_sql(
            "DOM-CHECKIN",
            "db_b14_checkin_nf",
            capabilities=list(checkin.get("capabilities") or []),
            title="查寝",
            ticket_flags=ct,
        )
        self.assertIn("REFERENCES checkin_spot_task (id)", checkin_sql)
        er = schema_model(checkin_sql)
        self.assertIn("checkin_spot_task", {t["name"] for t in er["tables"]})
        self.assertIn("checkin_spot_member", {t["name"] for t in er["tables"]})
        self.assertNotIn("checkin_spot_member", set(er.get("link_tables") or []))
        hit = False
        for r in er.get("relations") or []:
            if r.get("right") == "checkin_spot_member" and r.get("via") == "task_id":
                self.assertEqual(r.get("card_right"), "n")
                self.assertEqual(r.get("label"), "名册")
                hit = True
        self.assertTrue(hit)

    def test_batch15_rules_skins(self) -> None:
        cases = [
            (
                "DOM-FLEET",
                "用车申请",
                {"allowAttachKeepOld": True},
                ["ticket_attach_rev", "fk_ticket_attach_rev_ticket"],
                ["ticket-allow-attach-keep-old: true"],
                ["attachKeepOldLabel", "attachKeepOldHint"],
                {"attachKeepOld": True},
                None,
            ),
            (
                "DOM-CERT",
                "证明开具",
                {"allowCertPickupQr": True, "allowCertVerifyPage": True},
                [],
                [
                    "ticket-allow-cert-pickup-qr: true",
                    "ticket-allow-cert-verify-page: true",
                ],
                [
                    "pickupQrLabel",
                    "pickupQrHint",
                    "certVerifyStatusLabel",
                    "certVerifyAtLabel",
                    "certVerifyIssueNoLabel",
                    "certVerifyPageDeepenHint",
                ],
                {"certPickupQr": True, "certVerifyPage": True},
                None,
            ),
            (
                "DOM-VISITOR",
                "访客预约",
                {"allowVisitorPassPrint": True},
                [],
                ["ticket-allow-visitor-pass-print: true"],
                ["visitorPassPrintLabel", "visitorPassPrintHint"],
                {"visitorPassPrint": True},
                None,
            ),
            (
                "DOM-CHECKIN",
                "查寝登记",
                {"allowCheckinDailyReport": True},
                [],
                ["ticket-allow-checkin-daily-report: true"],
                ["checkinDailyLabel", "checkinDailyOnLabel", "checkinDailyHint"],
                {"checkinDailyReport": True},
                None,
            ),
            (
                "DOM-EVAL",
                "教学评价",
                {"allowEvalCollegeExport": True},
                [],
                ["ticket-allow-eval-college-export: true"],
                [
                    "evalCollegeExportLabel",
                    "evalCollegeLabel",
                    "evalCollegeExportHint",
                ],
                {"evalCollegeExport": True},
                "college",
            ),
        ]
        for (
            domain,
            title,
            expect_flags,
            cols,
            yml_needles,
            label_keys,
            thicken_flags,
            archive_col,
        ) in cases:
            out = _spec(domain, title, "")
            schema = out.get("schema") or {}
            ticket = (schema.get("entities") or {}).get("ticket") or {}
            labels = schema.get("labels") or {}
            thicken = schema.get("approveThicken") or {}
            for k, v in expect_flags.items():
                self.assertEqual(bool(ticket.get(k)), v, f"{domain}.{k}")
            for lk in label_keys:
                self.assertIn(lk, labels, f"{domain} labels.{lk}")
            for tk, tv in thicken_flags.items():
                self.assertEqual(bool(thicken.get(tk)), tv, f"{domain} thicken.{tk}")
            yml = policy_preview(domain, out)
            for needle in yml_needles:
                self.assertIn(needle, yml, f"{domain} {needle}")
            text = domain_sql(
                domain,
                "db_b15",
                capabilities=list(out.get("capabilities") or []),
                title=title,
                ticket_flags=ticket,
            )
            for col in cols:
                self.assertIn(col, text, f"{domain} sql {col}")
            if archive_col:
                self.assertIn(archive_col, text, f"{domain} archive {archive_col}")

        fleet = _spec("DOM-FLEET", "用车", "")
        ft = ((fleet.get("schema") or {}).get("entities") or {}).get("ticket") or {}
        self.assertTrue(bool(ft.get("allowAttachKeepOld")))
        self.assertFalse(bool(ft.get("allowCertPickupQr")))
        self.assertFalse(bool(ft.get("allowVisitorPassPrint")))
        self.assertFalse(bool(ft.get("allowCheckinDailyReport")))
        self.assertFalse(bool(ft.get("allowEvalCollegeExport")))
        cert = _spec("DOM-CERT", "证明", "")
        ct = ((cert.get("schema") or {}).get("entities") or {}).get("ticket") or {}
        self.assertTrue(bool(ct.get("allowCertPickupRedeem")))
        self.assertTrue(bool(ct.get("allowCertPickupQr")))
        self.assertTrue(bool(ct.get("allowCertVerifyPage")))
        fleet_sql = domain_sql(
            "DOM-FLEET",
            "db_b15_fleet",
            capabilities=list(fleet.get("capabilities") or []),
            title="用车",
            ticket_flags=ft,
        )
        self.assertIn("ticket_attach_rev", fleet_sql)
        self.assertIn("REFERENCES `fleet_apply` (id)", fleet_sql)
        er = schema_model(fleet_sql)
        self.assertIn("ticket_attach_rev", {t["name"] for t in er["tables"]})
        hit = False
        for r in er.get("relations") or []:
            if r.get("right") == "ticket_attach_rev" and r.get("via") == "ticket_id":
                self.assertEqual(r.get("card_right"), "n")
                self.assertEqual(r.get("label"), "历史")
                hit = True
        self.assertTrue(hit)

    def test_batch16_rules_skins(self) -> None:
        seal = _spec("DOM-SEAL", "用印审批", "")
        st = ((seal.get("schema") or {}).get("entities") or {}).get("ticket") or {}
        sl = (seal.get("schema") or {}).get("labels") or {}
        sth = (seal.get("schema") or {}).get("approveThicken") or {}
        self.assertTrue(bool(st.get("allowSealLedgerExport")))
        self.assertTrue(bool(sth.get("sealLedgerExport")))
        self.assertIn("sealLedgerExportLabel", sl)
        self.assertIn("sealLedgerExportHint", sl)
        yml = policy_preview("DOM-SEAL", seal)
        self.assertIn("ticket-allow-seal-ledger-export: true", yml)

        moral = _spec("DOM-MORAL", "综测加减分", "")
        mt = ((moral.get("schema") or {}).get("entities") or {}).get("ticket") or {}
        ml = (moral.get("schema") or {}).get("labels") or {}
        mth = (moral.get("schema") or {}).get("approveThicken") or {}
        self.assertTrue(bool(mt.get("allowMoralMaterialCheck")))
        self.assertTrue(bool(mt.get("requireMaterialChecklist")))
        self.assertTrue(bool(mth.get("moralMaterialCheck")))
        self.assertIn("material_check", moral.get("capabilities") or [])
        self.assertIn("moralMaterialHint", ml)
        self.assertEqual(ml.get("materialChecklistTitle"), "综测加减分证据材料")
        my = policy_preview("DOM-MORAL", moral)
        self.assertIn("ticket-allow-moral-material-check: true", my)
        moral_sql = domain_sql(
            "DOM-MORAL",
            "db_b16_moral",
            capabilities=list(moral.get("capabilities") or []),
            title="综测",
            ticket_flags=mt,
        )
        self.assertIn("material_checklist", moral_sql)
        self.assertIn("加分证明材料", moral_sql)

        party = _spec("DOM-PARTY", "党员发展", "")
        pt = ((party.get("schema") or {}).get("entities") or {}).get("ticket") or {}
        pl = (party.get("schema") or {}).get("labels") or {}
        pth = (party.get("schema") or {}).get("approveThicken") or {}
        self.assertTrue(bool(pt.get("allowPartyMaterialTemplate")))
        self.assertTrue(bool(pt.get("allowPartyThoughtAttach")))
        self.assertTrue(bool(pt.get("requireMaterialChecklist")))
        self.assertTrue(bool(pth.get("partyMaterialTemplate")))
        self.assertTrue(bool(pth.get("partyThoughtAttach")))
        self.assertIn("partyMaterialHint", pl)
        self.assertIn("partyThoughtHint", pl)
        self.assertEqual(pl.get("materialChecklistTitle"), "党员发展材料清单")
        py = policy_preview("DOM-PARTY", party)
        self.assertIn("ticket-allow-party-material-template: true", py)
        self.assertIn("ticket-allow-party-thought-attach: true", py)
        party_sql = domain_sql(
            "DOM-PARTY",
            "db_b16_party",
            capabilities=list(party.get("capabilities") or []),
            title="党员发展",
            ticket_flags=pt,
        )
        self.assertIn("入党积极分子阶段材料", party_sql)
        self.assertIn("思想汇报", party_sql)
        self.assertIn("心得体会", party_sql)
        self.assertIn("material_template", party_sql)

        fleet = _spec("DOM-FLEET", "用车", "")
        ft = ((fleet.get("schema") or {}).get("entities") or {}).get("ticket") or {}
        self.assertFalse(bool(ft.get("allowSealLedgerExport")))
        self.assertFalse(bool(ft.get("allowMoralMaterialCheck")))
        self.assertFalse(bool(ft.get("allowPartyMaterialTemplate")))
        self.assertFalse(bool(ft.get("allowPartyThoughtAttach")))

    def test_batch17_form_print_and_skins(self) -> None:
        cases = [
            (
                "DOM-CERT",
                "证明开具",
                "allowCertFormPrint",
                "certFormPrint",
                ["printTicketLabel", "certFormPrintHint"],
                "ticket-allow-cert-form-print: true",
            ),
            (
                "DOM-SEAL",
                "用印审批",
                "allowSealFormPrint",
                "sealFormPrint",
                ["printTicketLabel", "sealFormPrintHint"],
                "ticket-allow-seal-form-print: true",
            ),
            (
                "DOM-PROJ",
                "大创项目",
                "allowProjMidFormPrint",
                "projMidFormPrint",
                ["printTicketLabel", "projMidFormPrintHint"],
                "ticket-allow-proj-mid-form-print: true",
            ),
            (
                "DOM-ETHIC",
                "伦理审查",
                "allowEthicOpinionPrint",
                "ethicOpinionPrint",
                ["printTicketLabel", "ethicOpinionPrintHint"],
                "ticket-allow-ethic-opinion-print: true",
            ),
        ]
        for domain, title, flag, thick, label_keys, yml_needle in cases:
            out = _spec(domain, title, "")
            schema = out.get("schema") or {}
            ticket = (schema.get("entities") or {}).get("ticket") or {}
            labels = schema.get("labels") or {}
            thicken = schema.get("approveThicken") or {}
            self.assertTrue(bool(ticket.get(flag)), f"{domain}.{flag}")
            self.assertTrue(bool(ticket.get("printTicket")), f"{domain}.printTicket")
            self.assertTrue(bool(thicken.get(thick)), f"{domain}.{thick}")
            for lk in label_keys:
                self.assertIn(lk, labels, f"{domain} labels.{lk}")
            self.assertIn(yml_needle, policy_preview(domain, out), f"{domain} {yml_needle}")

        exp = _spec("DOM-EXPENSE", "报销", "")
        et = ((exp.get("schema") or {}).get("entities") or {}).get("ticket") or {}
        el = (exp.get("schema") or {}).get("labels") or {}
        self.assertTrue(bool(et.get("allowExpenseAttachCount")))
        self.assertTrue(bool(et.get("requireAttach")))
        self.assertIn("expenseAttachCountHint", el)
        self.assertIn(
            "ticket-allow-expense-attach-count: true",
            policy_preview("DOM-EXPENSE", exp),
        )

        fleet = _spec("DOM-FLEET", "用车", "")
        ft = ((fleet.get("schema") or {}).get("entities") or {}).get("ticket") or {}
        fl = (fleet.get("schema") or {}).get("labels") or {}
        self.assertTrue(bool(ft.get("allowFleetDriverCert")))
        self.assertTrue(bool(ft.get("requireMaterialChecklist")))
        self.assertIn("material_check", fleet.get("capabilities") or [])
        self.assertIn("fleetDriverCertHint", fl)
        self.assertEqual(fl.get("materialChecklistTitle"), "驾驶员资质材料")
        fleet_sql = domain_sql(
            "DOM-FLEET",
            "db_b17_fleet",
            capabilities=list(fleet.get("capabilities") or []),
            title="用车",
            ticket_flags=ft,
        )
        self.assertIn("驾驶证", fleet_sql)
        self.assertIn("从业资格证", fleet_sql)

        # PROCURE 一键入库属 borrow_thicken，本组不重复造轮
        procure = _spec("DOM-PROCURE", "采购申购", "")
        pt = ((procure.get("schema") or {}).get("entities") or {}).get("ticket") or {}
        self.assertTrue(bool(pt.get("procureToStockIn")))
        self.assertIn("stock_io", procure.get("capabilities") or [])

        visitor = _spec("DOM-VISITOR", "访客", "")
        vt = ((visitor.get("schema") or {}).get("entities") or {}).get("ticket") or {}
        self.assertFalse(bool(vt.get("allowCertFormPrint")))
        self.assertFalse(bool(vt.get("allowExpenseAttachCount")))
        self.assertFalse(bool(vt.get("allowFleetDriverCert")))


if __name__ == "__main__":
    unittest.main()
