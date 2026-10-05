"""开题密功能地图 · 骨架静态门禁（不靠起包）。

已齐硬口径（文档）：管理端能管 + 用户端可产生数据（写库）。
本门禁只钉保险丝：已齐表里的 labels.* 必须被 Vue 真读；§1.3 报修硬点控件存在。
纯 Hint / 只读提示不得标已齐——应由地图待补表约束，本测试防止字面量空挂回流已齐。
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
MAP = REPO / "docs" / "opening-feature-delivery-map.md"
FE_SRC = REPO / "skeletons" / "baseline" / "frontend" / "src"
BE_BASE = (
    REPO
    / "skeletons"
    / "baseline"
    / "backend"
    / "src"
    / "main"
    / "java"
    / "com"
    / "thesis"
)
OV_MYBATIS = (
    REPO
    / "skeletons"
    / "overlays"
    / "persistence-mybatis"
    / "backend"
    / "src"
    / "main"
    / "java"
    / "com"
    / "thesis"
    / "capability"
    / "TicketStore.java"
)
OV_JPA = (
    REPO
    / "skeletons"
    / "overlays"
    / "persistence-jpa"
    / "backend"
    / "src"
    / "main"
    / "java"
    / "com"
    / "thesis"
    / "capability"
    / "TicketStore.java"
)


def _read(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def _fe_blob() -> str:
    parts: list[str] = []
    for p in FE_SRC.rglob("*"):
        if p.suffix in {".vue", ".js"} and p.is_file():
            parts.append(_read(p))
    return "\n".join(parts)


def _be_ticket_blob() -> str:
    files = [
        BE_BASE / "capability" / "TicketStore.java",
        BE_BASE / "capability" / "TicketDashOps.java",
        BE_BASE / "capability" / "TicketPatchOps.java",
        BE_BASE / "capability" / "TicketRowMaps.java",
        BE_BASE / "controller" / "TicketController.java",
        OV_MYBATIS,
        OV_JPA,
    ]
    return "\n".join(_read(p) for p in files if p.is_file())


def _map_done_sections(md: str) -> list[str]:
    """截取每个「本组本轮已齐」到下一節标题之间的正文。"""
    parts = re.split(r"(?=#### 本组本轮已齐)", md)
    return [p for p in parts if p.startswith("#### 本组本轮已齐")]


def _labels_claimed_done(md: str) -> list[str]:
    keys: list[str] = []
    for sec in _map_done_sections(md):
        for m in re.finditer(r"labels\.([A-Za-z][A-Za-z0-9_]*)", sec):
            keys.append(m.group(1))
    return sorted(set(keys))


class OpeningMapSkeletonGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.map_text = _read(MAP)
        cls.fe = _fe_blob()
        cls.be_ticket = _be_ticket_blob()

    def test_done_labels_must_be_read_in_frontend(self) -> None:
        """已齐表里的 labels.xxx 必须在 baseline Vue/JS 出现字面量。"""
        missing = [
            k for k in _labels_claimed_done(self.map_text) if k not in self.fe
        ]
        self.assertEqual(
            missing,
            [],
            "地图「已齐」含纯 Hint（前端零读取），退回待补或挂控件："
            + ", ".join(missing),
        )

    def test_repair_thicken_ui_markers(self) -> None:
        """§1.3 答辩硬点：色标 / 故障频次图 / 楼栋筛 / 对比图 / 维修员今日看板。"""
        fe_need = [
            ("categoryColorOn", "报修分类色标"),
            ("faultReasonSeries", "故障现象高频统计"),
            ("locationFilterOn", "派单按地点/楼栋筛"),
            ("cmp-lab", "报修/完工图对比"),
            ("今日处理中", "维修员今日看板"),
            ("default-today", "StaffTickets 切今日"),
        ]
        for needle, label in fe_need:
            self.assertIn(needle, self.fe, f"FE 缺 {label}: {needle}")

        be_need = [
            ("faultReasonSeries", "故障原因 series"),
            ("todayAssigned", "今日处理中筛选"),
            ("rankScope", "成绩排名范围写库"),
            ("rank_scope", "成绩排名范围列"),
        ]
        for needle, label in be_need:
            self.assertIn(needle, self.be_ticket, f"BE 缺 {label}: {needle}")

        self.assertIn("rankScope", self.fe, "FE 缺 rankScope 写库")
        self.assertIn("rank_scope", _read(REPO / "backend/app/bake/sql/fragments.py"), "SQL 缺 rank_scope")

        # §1.2 双端硬点：补考报名入口 + 按假种附件（曾 FE 空挂）
        fe_follow = [
            ("allowMakeupApply", "补考报名开关"),
            ("openApply({ makeup", "补考报名入口调用"),
            ("attachByLeaveType", "按假种附件开关"),
            ("sickAttachHint", "病假附件提示"),
            ("makeupApplyHint", "补考报名提示"),
            ("allowConfidential", "保密标记开关"),
            ("allowDisburseBatch", "发放批次开关"),
            ("allowExcellentMark", "优秀周报开关"),
            ("allowExceptionClose", "异常件办结开关"),
            ("resumeFieldSet", "简历字段套"),
            ("allowAssignDept", "分拨科室开关"),
        ]
        for needle, label in fe_follow:
            self.assertIn(needle, self.fe, f"FE 缺 {label}: {needle}")

        for path, name in ((OV_MYBATIS, "mybatis"), (OV_JPA, "jpa")):
            text = _read(path)
            if "faultReasonSeries" not in text and "TicketDashOps.chartStats" not in text:
                self.fail(f"{name} 缺 faultReasonSeries（或 TicketDashOps.chartStats 委托）")
            self.assertIn("todayAssigned", text, f"{name} 缺 todayAssigned")
        dash = _read(BE_BASE / "capability" / "TicketDashOps.java")
        self.assertIn("faultReasonSeries", dash, "baseline TicketDashOps 缺 faultReasonSeries")

    def test_close_attach_slot_falls_back_to_schema_labels(self) -> None:
        """共用办结附件槽：域皮开关只覆盖，默认必须回落 schema labels.closeAttach*。

        不改 bake 匹配；禁止后一批把默认枝写成某一域文案。
        """
        files = [
            FE_SRC / "views" / "user" / "MyTickets.vue",
            FE_SRC / "components" / "RepairFinishDialog.vue",
        ]
        for path in files:
            text = _read(path)
            hint_m = re.search(
                r"const closeAttachHint = computed\(\(\) =>\s*(.*?)\n\)",
                text,
                re.S,
            )
            self.assertIsNotNone(hint_m, f"{path.name} 缺 closeAttachHint computed")
            body = hint_m.group(1)
            self.assertIn("allowSealClosePhoto", body, f"{path.name} 办结提示须先用印开关")
            self.assertIn("allowPromoFeedback", body, f"{path.name} 办结提示须次宣传开关")
            self.assertIn(
                "labels.value.closeAttachHint",
                body,
                f"{path.name} 办结提示默认须回落 labels.closeAttachHint",
            )
            seal_at = body.find("allowSealClosePhoto")
            promo_at = body.find("allowPromoFeedback")
            fallback_at = body.find("labels.value.closeAttachHint")
            self.assertLess(seal_at, promo_at, f"{path.name} 用印覆盖须在宣传之前")
            self.assertLess(promo_at, fallback_at, f"{path.name} 宣传覆盖须在 schema 默认之前")
            self.assertNotRegex(
                body,
                r"allowSealClosePhoto[^\n]*\?[^:]+:\s*promoFeedbackHint",
                f"{path.name} 禁止宣传句当作全组默认",
            )
            label_m = re.search(
                r"const closeAttach(?:Field)?Label = computed\(\(\) =>\s*(.*?)\n\)",
                text,
                re.S,
            )
            self.assertIsNotNone(label_m, f"{path.name} 缺 closeAttach 标签 computed")
            lbody = label_m.group(1)
            self.assertIn(
                "labels.value.closeAttachLabel",
                lbody,
                f"{path.name} 办结标签默认须回落 labels.closeAttachLabel",
            )

        from app.bake.domain_schema import attach_accept
        from app.bake.domains import DOMAIN_CAPABILITIES
        from app.bake.ticket_policy import policy_preview

        def spec(domain: str, title: str) -> dict:
            return attach_accept(
                {
                    "domain": domain,
                    "title": title,
                    "capabilities": list(DOMAIN_CAPABILITIES[domain]),
                    "features": [],
                    "archetype": "ARCH-FLOW",
                },
                "",
            )

        event = spec("DOM-EVENT", "事件上报")
        ev_t = ((event.get("schema") or {}).get("entities") or {}).get("ticket") or {}
        ev_l = (event.get("schema") or {}).get("labels") or {}
        self.assertTrue(ev_t.get("requireCloseAttach"))
        self.assertFalse(bool(ev_t.get("allowPromoFeedback")))
        self.assertFalse(bool(ev_t.get("allowSealClosePhoto")))
        self.assertTrue(str(ev_l.get("closeAttachHint") or "").strip())

        promo = spec("DOM-PROMO", "宣传品审批")
        pr_t = ((promo.get("schema") or {}).get("entities") or {}).get("ticket") or {}
        pr_l = (promo.get("schema") or {}).get("labels") or {}
        self.assertTrue(pr_t.get("requireCloseAttach"))
        self.assertTrue(pr_t.get("allowPromoFeedback"))
        self.assertFalse(bool(pr_t.get("allowSealClosePhoto")))
        self.assertTrue(str(pr_l.get("promoFeedbackHint") or "").strip())
        yml = policy_preview("DOM-PROMO", promo)
        self.assertIn("ticket-allow-promo-feedback: true", yml)
        self.assertIn("ticket-allow-seal-close-photo: false", yml)

        seal = spec("DOM-SEAL", "用印申请")
        se_t = ((seal.get("schema") or {}).get("entities") or {}).get("ticket") or {}
        se_l = (seal.get("schema") or {}).get("labels") or {}
        self.assertTrue(se_t.get("requireCloseAttach"))
        self.assertTrue(se_t.get("allowSealClosePhoto"))
        self.assertFalse(bool(se_t.get("allowPromoFeedback")))
        self.assertTrue(str(se_l.get("sealPhotoHint") or "").strip())

        fleet = spec("DOM-FLEET", "公务用车")
        ft = ((fleet.get("schema") or {}).get("entities") or {}).get("ticket") or {}
        self.assertFalse(bool(ft.get("requireCloseAttach")))
        self.assertFalse(bool(ft.get("allowPromoFeedback")))
        self.assertFalse(bool(ft.get("allowSealClosePhoto")))

    def test_shared_apply_and_finish_slots_fall_back_to_schema(self) -> None:
        """提交附件 / 办结弹窗 / 档案占位 / 报修对比图：域皮只覆盖，禁止某域中文当全页默认。"""
        my = _read(FE_SRC / "views" / "user" / "MyTickets.vue")
        repair = _read(FE_SRC / "components" / "RepairFinishDialog.vue")

        self.assertNotIn("劳动时长证明", my)
        self.assertNotIn("查寝照片", my)

        att_m = re.search(
            r"const attachFieldLabel = computed\(\(\) =>\s*(.*?)\n\)",
            my,
            re.S,
        )
        self.assertIsNotNone(att_m, "缺 attachFieldLabel computed")
        att = att_m.group(1)
        self.assertIn("laborAttachLabel", att)
        self.assertIn("checkinPhotoLabel", att)
        self.assertIn("fleetTollAttachLabel", att)
        self.assertIn("labels.value.attachLabel", att)
        self.assertIn("'附件'", att)
        self.assertLess(att.find("laborAttachLabel"), att.find("'附件'"))
        self.assertNotRegex(
            att,
            r"fleetTollAttachLabel\.value\s*\|\|\s*'附件'",
            "禁止过路费标签独占提交附件槽",
        )

        hint_m = re.search(
            r"const attachFieldHint = computed\(\(\) =>\s*(.*?)\n\)",
            my,
            re.S,
        )
        self.assertIsNotNone(hint_m, "缺 attachFieldHint computed")
        ah = hint_m.group(1)
        self.assertIn("homePhotoAttachHint", ah)
        self.assertIn("labels.value.attachHint", ah)

        fin_m = re.search(
            r"const finishAttachFieldLabel = computed\(\(\) =>\s*(.*?)\n\}",
            my,
            re.S,
        )
        self.assertIsNotNone(fin_m, "缺 finishAttachFieldLabel computed")
        fin = fin_m.group(1)
        self.assertIn("requireCloseAttach", fin)
        self.assertIn("requireReturnAttach", fin)
        self.assertIn("returnAttachLabel", fin)
        self.assertLess(fin.find("requireCloseAttach"), fin.find("requireReturnAttach"))

        ph_m = re.search(
            r"const archiveSelectPlaceholder = computed\(\(\) =>\s*(.*?)\n\}",
            my,
            re.S,
        )
        self.assertIsNotNone(ph_m, "缺 archiveSelectPlaceholder computed")
        ph = ph_m.group(1)
        self.assertIn("archiveLabel", ph)
        self.assertRegex(ph, r"return `请选择\$\{archiveLabel")

        self.assertIn("showRepairPhotoCompare", repair)
        self.assertRegex(
            repair,
            r"showRepairPhotoCompare && row && \(row\.attachUrl \|\| form\.closeAttachUrl\)",
        )
        self.assertIn("ticket.value.repairThicken", repair)

        from app.bake.domain_schema import attach_accept
        from app.bake.domains import DOMAIN_CAPABILITIES

        def spec(domain: str, title: str) -> dict:
            return attach_accept(
                {
                    "domain": domain,
                    "title": title,
                    "capabilities": list(DOMAIN_CAPABILITIES[domain]),
                    "features": [],
                    "archetype": "ARCH-FLOW",
                },
                "",
            )

        def ticket_labels(out: dict) -> tuple[dict, dict]:
            schema = out.get("schema") or {}
            t = (schema.get("entities") or {}).get("ticket") or {}
            return t, schema.get("labels") or {}

        labor_t, labor_l = ticket_labels(spec("DOM-LABOR", "劳动时长登记"))
        self.assertTrue(labor_t.get("requireAttach"))
        self.assertTrue(str(labor_l.get("laborAttachLabel") or "").strip())
        self.assertFalse(str(labor_l.get("fleetTollAttachLabel") or "").strip())
        self.assertFalse(str(labor_l.get("checkinPhotoLabel") or "").strip())

        chk_t, chk_l = ticket_labels(spec("DOM-CHECKIN", "查寝登记"))
        self.assertTrue(chk_t.get("requireAttach"))
        self.assertTrue(str(chk_l.get("checkinPhotoLabel") or "").strip())
        self.assertFalse(str(chk_l.get("laborAttachLabel") or "").strip())
        self.assertFalse(str(chk_l.get("fleetTollAttachLabel") or "").strip())

        fleet_t, fleet_l = ticket_labels(spec("DOM-FLEET", "公务用车"))
        self.assertTrue(fleet_t.get("requireAttach"))
        self.assertTrue(str(fleet_l.get("fleetTollAttachLabel") or "").strip())
        self.assertFalse(str(fleet_l.get("laborAttachLabel") or "").strip())
        self.assertFalse(str(fleet_l.get("checkinPhotoLabel") or "").strip())

        exp_t, exp_l = ticket_labels(spec("DOM-EXPENSE", "报销申请"))
        self.assertTrue(exp_t.get("requireAttach"))
        self.assertFalse(str(exp_l.get("fleetTollAttachLabel") or "").strip())
        self.assertFalse(str(exp_l.get("laborAttachLabel") or "").strip())
        self.assertFalse(str(exp_l.get("checkinPhotoLabel") or "").strip())

        ev_t, _ = ticket_labels(spec("DOM-EVENT", "事件上报"))
        self.assertFalse(bool(ev_t.get("requireAttach")))

        dorm = spec("DOM-DORM", "宿舍报修")
        d_t = ((dorm.get("schema") or {}).get("entities") or {}).get("ticket") or {}
        self.assertTrue(d_t.get("repairThicken"))
        self.assertTrue(d_t.get("requireCloseAttach"))


if __name__ == "__main__":
    unittest.main()
