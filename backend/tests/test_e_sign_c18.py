"""泳道 E · C-18：本地签章演示 e_sign + DOM-INTERN。"""

from __future__ import annotations

import unittest
from pathlib import Path

from app.bake.capabilities import CAPABILITIES, resolve_accept, scan_out_of_scope
from app.bake.catalog import match_text
from app.bake.domain_schema import attach_accept, build_domain_schema, validate_schema
from app.bake.domains import DOMAIN_CAPABILITIES, DOMAINS
from app.bake.engine_bake import _patch_thesis_yml
from app.bake.engine_sql import domain_sql
from app.bake.features.e_sign import E_SIGN_CAP, scan_e_sign
from app.bake.menu_routes import shell_kind

ROOT = Path(__file__).resolve().parents[2]
SAMPLES = ROOT / "data" / "samples" / "能力预设开题"
BASELINE = ROOT / "skeletons" / "baseline"
MYBATIS = ROOT / "skeletons" / "overlays" / "persistence-mybatis"
JPA = ROOT / "skeletons" / "overlays" / "persistence-jpa"


class ESignC18Tests(unittest.TestCase):
    def test_capability_and_domain(self) -> None:
        self.assertIn(E_SIGN_CAP, CAPABILITIES)
        self.assertEqual(CAPABILITIES[E_SIGN_CAP]["status"], "implemented")
        self.assertIn("DOM-INTERN", DOMAINS)
        caps = DOMAIN_CAPABILITIES["DOM-INTERN"]
        self.assertIn(E_SIGN_CAP, caps)
        self.assertIn("ticket_flow", caps)

    def test_scan_and_oos(self) -> None:
        self.assertTrue(scan_e_sign("实习鉴定签署：上传签章图并勾选同意。"))
        self.assertTrue(scan_e_sign("支持本地签章演示留痕。"))
        shallow = "主要功能\n1. 周报审阅\n2. 鉴定签署上传签章图勾选同意\n3. 公告"
        self.assertNotIn("电子签章CA/第三方签平台", scan_out_of_scope(shallow))
        ca = "主要功能\n对接法大大第三方电子签完成三方协议。"
        self.assertIn("电子签章CA/第三方签平台", scan_out_of_scope(ca))

    def test_match(self) -> None:
        got = match_text(
            "基于 Spring Boot 的高校实习周报与鉴定签署管理系统的设计与实现。"
            "主要功能：实习岗位、周报提交审阅、鉴定签署上传签章图勾选同意。"
        )
        self.assertEqual(got.domain, "DOM-INTERN", f"hits={got.hits[:12]}")

    def test_schema_menus_yml(self) -> None:
        schema = build_domain_schema("实习周报与鉴定签署系统", "DOM-INTERN")
        ok, errs = validate_schema(schema)
        self.assertTrue(ok, errs[:5])
        self.assertEqual(shell_kind(DOMAIN_CAPABILITIES["DOM-INTERN"]), "archive_ticket")
        spec = attach_accept(
            {
                "domain": "DOM-INTERN",
                "title": "高校实习周报与鉴定签署管理系统",
                "capabilities": list(DOMAIN_CAPABILITIES["DOM-INTERN"]),
                "archetype": "ARCH-FLOW",
            },
            "周报审阅；鉴定签署上传签章图勾选同意。本期不对接法大大与 CA。",
        )
        sch = spec.get("schema") or {}
        user_keys = {m.get("key") for m in (sch.get("menus") or {}).get("user") or []}
        admin_keys = {m.get("key") for m in (sch.get("menus") or {}).get("admin") or []}
        self.assertIn("e_sign_mine", user_keys)
        self.assertIn("e_sign_admin", admin_keys)
        self.assertIn(E_SIGN_CAP, spec.get("capabilities") or [])
        self.assertEqual(spec.get("accept"), "full", spec.get("accept_reason"))

        yml = _patch_thesis_yml("thesis:\n  title: x\n", "DOM-INTERN", spec)
        self.assertIn("e-sign-enabled: true", yml)

        sql = domain_sql(
            "DOM-INTERN",
            "t_intern",
            title="实习鉴定签署系统",
            proposal_text="鉴定签署签章图",
        )
        self.assertIn("e_sign_record", sql)

        d = resolve_accept(
            list(DOMAIN_CAPABILITIES["DOM-INTERN"]),
            "周报；鉴定签署上传签章图。",
            has_domain_overlay=True,
            has_baseline_runtime=True,
            archetypes=["ARCH-FLOW"],
            domain="DOM-INTERN",
            primary_archetype="ARCH-FLOW",
        )
        self.assertEqual(d["accept"], "full", d)

    def test_runtime_paths(self) -> None:
        for rel in (
            "backend/src/main/java/com/thesis/service/ESignStore.java",
            "backend/src/main/java/com/thesis/controller/ESignController.java",
            "frontend/src/views/ESignMine.vue",
            "frontend/src/views/admin/ESignAdmin.vue",
        ):
            self.assertTrue((BASELINE / rel).is_file(), rel)
        for root in (BASELINE, MYBATIS, JPA):
            binder = root / "backend/src/main/java/com/thesis/config/DomainRuntimeBinder.java"
            bt = binder.read_text(encoding="utf-8")
            self.assertIn("e-sign-enabled", bt, msg=str(binder))
            self.assertIn("ESignStore.configure", bt, msg=str(binder))
            store = root / "backend/src/main/java/com/thesis/service/ESignStore.java"
            self.assertTrue(store.is_file(), msg=str(store))
        self.assertTrue(
            (MYBATIS / "backend/src/main/java/com/thesis/mapper/ESignMapper.java").is_file()
        )
        router = (BASELINE / "frontend/src/router/index.js").read_text(encoding="utf-8")
        self.assertIn("withESignRoutes", router)

    def test_sample_file(self) -> None:
        samples = list(SAMPLES.glob("C-18*.txt"))
        self.assertTrue(samples, "missing C-18 sample under 能力预设开题")
        body = samples[0].read_text(encoding="utf-8")
        self.assertTrue(scan_e_sign(body))
        self.assertIn("DOM-INTERN", body)
        self.assertNotIn("电子签章CA/第三方签平台", scan_out_of_scope(body))


if __name__ == "__main__":
    unittest.main()
