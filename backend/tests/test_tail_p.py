"""泳道 E 长尾：P-18、P-23～P-29 具名 DOM。"""

from __future__ import annotations

import unittest
from pathlib import Path

from app.bake.catalog import match_text
from app.bake.domain_schema import build_domain_schema, validate_schema
from app.bake.domains import DOMAIN_CAPABILITIES, DOMAINS
from app.bake.engine_sql import domain_sql
from app.bake.schema.followup_presets import FOLLOWUP_PRESETS
from app.bake.schema.templates import SCHEMA_BUILDERS
from app.bake.tail_p import TAIL_CASES

SAMPLES = Path(__file__).resolve().parents[2] / "data" / "samples" / "长尾预设开题"


class TailPTests(unittest.TestCase):
    def test_domains_registered(self) -> None:
        self.assertEqual(len(TAIL_CASES), 8)
        for sid, _phrase, domain, _title in TAIL_CASES:
            with self.subTest(id=sid):
                self.assertIn(domain, DOMAINS)
                self.assertIn(domain, DOMAIN_CAPABILITIES)
                self.assertIn(domain, FOLLOWUP_PRESETS)
                self.assertIn(domain, SCHEMA_BUILDERS)

    def test_all_hit_named_domain(self) -> None:
        for sid, phrase, want, title in TAIL_CASES:
            with self.subTest(id=sid, title=title):
                text = f"基于 Spring Boot 的{title}的设计与实现。主要功能：{phrase}。"
                got = match_text(text)
                self.assertEqual(got.domain, want, f"hits={got.hits[:12]}")

    def test_neighbors_do_not_steal(self) -> None:
        cases = [
            ("临时车辆通行证与车牌备案申请审批", "DOM-CARPASS", "DOM-PARKING"),
            ("临时车辆通行证与车牌备案申请审批", "DOM-CARPASS", "DOM-VISITOR"),
            ("房源中介挂牌与带看意向跟进", "DOM-LISTING", "DOM-HOTEL"),
            ("房源中介挂牌与带看意向跟进", "DOM-LISTING", "DOM-CRM"),
            ("中介看房带看安排管理", "DOM-LISTING", "DOM-HOTEL"),
            ("房产经纪带看安排跟进", "DOM-LISTING", "DOM-CRM"),
            ("物资采购申请与申购单审批", "DOM-PROCURE", "DOM-ASSET"),
            ("请购单审批台账", "DOM-PROCURE", "DOM-ASSET"),
            ("物资请购审批管理", "DOM-PROCURE", "DOM-SHOP"),
            ("学生社团注册成立与年审材料审批", "DOM-CLUB", "DOM-ACTIVITY"),
            ("学生组织备案材料审批", "DOM-CLUB", "DOM-ACTIVITY"),
            ("学生组织成立备案与年度复核", "DOM-CLUB", "DOM-ACTIVITY"),
            ("大创项目申报与中期检查材料审批", "DOM-PROJ", "DOM-FUND"),
            ("大创立项与结题验收材料", "DOM-PROJ", "DOM-FUND"),
            ("中期检查材料填报审批", "DOM-PROJ", "DOM-EXPENSE"),
            ("伦理审查与开题答辩材料提交审核", "DOM-ETHIC", "DOM-GRADE"),
            ("伦理预审材料提交", "DOM-ETHIC", "DOM-GRADE"),
            ("开题报告审核台账", "DOM-ETHIC", "DOM-PARTY"),
            ("入党申请与党员发展阶段材料审批", "DOM-PARTY", "DOM-EVENT"),
            ("入党申请书审核", "DOM-PARTY", "DOM-EXAM"),
            ("发展阶段台账材料", "DOM-PARTY", "DOM-ACTIVITY"),
            ("合同登记与单级审批管理", "DOM-CONTRACT", "DOM-SEAL"),
            ("采购合同单级审批", "DOM-CONTRACT", "DOM-PROCURE"),
            ("合作协议登记审核", "DOM-CONTRACT", "DOM-CRM"),
            ("停车场车位时段预约管理", "DOM-PARKING", "DOM-CARPASS"),
        ]
        for phrase, want, avoid in cases:
            with self.subTest(phrase=phrase, avoid=avoid):
                got = match_text(f"基于 Spring Boot 的{phrase}系统的设计与实现")
                self.assertEqual(got.domain, want, f"hits={got.hits[:12]}")
                self.assertNotEqual(got.domain, avoid)

    def test_listing_procure_club_archive_columns(self) -> None:
        from app.bake.archive_columns import archive_column_spec_for
        from app.bake.schema.er import collect_english_gaps, schema_model

        cases = {
            "DOM-LISTING": ("listing", "estate_area", "house_type_note"),
            "DOM-PROCURE": ("procure_item", "own_dept", "item_spec"),
            "DOM-CLUB": ("club_item", "guide_unit", "matter_note"),
            "DOM-PROJ": ("proj_item", "own_unit", "declare_note"),
            "DOM-ETHIC": ("ethic_item", "own_unit", "material_brief"),
            "DOM-PARTY": ("party_stage", "party_org", "material_brief"),
            "DOM-CONTRACT": ("contract_type", "own_dept", "approve_note"),
        }
        for domain, (table, want_a, want_i) in cases.items():
            with self.subTest(domain=domain):
                (a, _), (i, _) = archive_column_spec_for(domain)
                self.assertEqual((a, i), (want_a, want_i))
                sql = domain_sql(domain, "thesis_test")
                self.assertIn(f"CREATE TABLE IF NOT EXISTS {table}", sql)
                self.assertIn(a, sql)
                self.assertIn(i, sql)
                self.assertNotIn("isbn VARCHAR", sql)
                model = schema_model(sql)
                gaps = collect_english_gaps(model)
                archive_cols = [
                    c
                    for c in gaps.get("columns") or []
                    if c.get("table") == table
                    and c.get("name") in ("dept_name", "note_hint", "subtitle", "detail", a, i)
                ]
                self.assertEqual(archive_cols, [], archive_cols)

    def test_listing_procure_club_skin(self) -> None:
        from app.bake.profile_fields import profile_fields_for

        expect = {
            "DOM-LISTING": {
                "title": "房源带看",
                "user": "看房客户",
                "labels": ["房源名称", "小区/区域", "户型说明", "可带看"],
                "seed": ["城东高新区", "两室一厅"],
                "forbid_seed": ["张顾问"],
                "profile": ["客户类型", "意向区域"],
                "forbid_profile": ["学号"],
            },
            "DOM-PROCURE": {
                "title": "采购申购",
                "user": "申购人",
                "labels": ["品目名称", "归口部门", "规格说明", "可申购"],
                "seed": ["后勤处", "箱装"],
                "forbid_seed": [],
                "profile": ["工号", "部门"],
                "forbid_profile": ["学号"],
            },
            "DOM-CLUB": {
                "title": "社团年审",
                "user": "社团负责人",
                "labels": ["事项名称", "指导单位", "事项说明", "可办理"],
                "seed": ["团委", "章程"],
                "forbid_seed": [],
                "profile": ["学号", "所属社团"],
                "forbid_profile": [],
            },
            "DOM-PROJ": {
                "title": "项目申报",
                "user": "申报人",
                "labels": ["项目名称", "归口单位", "申报说明", "可申报"],
                "seed": ["教务处", "本科生创新"],
                "forbid_seed": [],
                "profile": ["学号", "项目角色"],
                "forbid_profile": [],
            },
            "DOM-ETHIC": {
                "title": "材料审核",
                "user": "送审人",
                "labels": ["事项名称", "归口单位", "材料说明", "可送审"],
                "seed": ["科研处", "知情同意"],
                "forbid_seed": [],
                "profile": ["学号", "指导教师"],
                "forbid_profile": [],
            },
            "DOM-PARTY": {
                "title": "党员发展",
                "user": "入党申请人",
                "labels": ["阶段名称", "党组织", "材料说明", "可办理"],
                "seed": ["党组织", "思想汇报"],
                "forbid_seed": [],
                "profile": ["学号", "所在党支部"],
                "forbid_profile": [],
            },
            "DOM-CONTRACT": {
                "title": "合同审批",
                "user": "经办人",
                "labels": ["类型名称", "归口部门", "审批说明", "可登记"],
                "seed": ["法务办", "单级审批"],
                "forbid_seed": [],
                "profile": ["工号", "部门"],
                "forbid_profile": ["学号"],
            },
        }
        for domain, spec in expect.items():
            with self.subTest(domain=domain):
                schema = build_domain_schema(spec["title"], domain)
                archive = (schema.get("entities") or {}).get("archive") or {}
                labels = [str(f.get("label") or "") for f in (archive.get("fields") or [])]
                for lab in spec["labels"]:
                    self.assertIn(lab, labels)
                user_role = ((schema.get("roles") or {}).get("user") or {})
                self.assertEqual(user_role.get("label"), spec["user"])
                sql = domain_sql(domain, "thesis_test")
                for frag in spec["seed"]:
                    self.assertIn(frag, sql)
                for frag in spec["forbid_seed"]:
                    self.assertNotIn(frag, sql)
                pfs = profile_fields_for(domain, title=spec["title"])
                plabels = [str(f.get("label") or "") for f in pfs]
                for lab in spec["profile"]:
                    self.assertIn(lab, plabels)
                for lab in spec["forbid_profile"]:
                    self.assertNotIn(lab, plabels)

    def test_carpass_issue_pass_code(self) -> None:
        schema = build_domain_schema("高校临时车辆通行证备案管理系统", "DOM-CARPASS")
        ok, errs = validate_schema(schema)
        self.assertTrue(ok, errs[:5])
        ticket = (schema.get("entities") or {}).get("ticket") or {}
        self.assertTrue(ticket.get("issuePassCode"))
        self.assertIn("pass_code", DOMAIN_CAPABILITIES["DOM-CARPASS"])
        sql = domain_sql(
            "DOM-CARPASS",
            "t_carpass",
            title="高校临时车辆通行证备案管理系统",
            proposal_text="临时车辆通行证与车牌备案",
        )
        self.assertIn("pass_code", sql)
        self.assertIn("pass_zone", sql)

    def test_schema_builds(self) -> None:
        for sid, _phrase, domain, title in TAIL_CASES:
            with self.subTest(id=sid):
                schema = build_domain_schema(title, domain)
                ok, errs = validate_schema(schema)
                self.assertTrue(ok, errs[:5])

    def test_sample_files_exist(self) -> None:
        self.assertTrue(SAMPLES.is_dir(), SAMPLES)
        for sid, _phrase, domain, title in TAIL_CASES:
            with self.subTest(id=sid):
                path = SAMPLES / f"{sid}-{domain}-{title}.txt"
                self.assertTrue(path.is_file(), path)


if __name__ == "__main__":
    unittest.main()
