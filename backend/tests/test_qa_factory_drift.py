"""QA / 交付结构全厂回归：不绑单一 DOM。"""

from __future__ import annotations

import unittest
from pathlib import Path

from app.bake.domain_skin import traits_for_domain
from app.bake.domains import DOMAIN_CAPABILITIES
from app.bake.schema.templates import SCHEMA_BUILDERS
from app.bake.staff_posts import attach_staff_posts


# 抽样：跟进族 / 纯工单 / 预约 / 交易
_SAMPLE_DOMAINS = (
    "DOM-ATTEND",
    "DOM-INTERN",
    "DOM-CRM",
    "DOM-DORM",
    "DOM-FOOD",
    "DOM-MEETING",
    "DOM-LIBRARY",
)


class FactoryQaDriftRegressionTests(unittest.TestCase):
    def test_follow_up_trait_never_named_crm(self) -> None:
        for domain, traits in (
            (d, traits_for_domain(d)) for d in DOMAIN_CAPABILITIES
        ):
            with self.subTest(domain=domain):
                self.assertNotIn("crm", traits)
                if domain in {
                    "DOM-CRM",
                    "DOM-EVENT",
                    "DOM-ATTEND",
                    "DOM-FUND",
                    "DOM-LABSAFE",
                    "DOM-RECRUIT",
                    "DOM-DATING",
                    "DOM-GRADE",
                    "DOM-INTERN",
                }:
                    self.assertTrue(traits.get("followUp"), domain)

    def test_staff_packs_only_mount_what_posts_use(self) -> None:
        for domain in _SAMPLE_DOMAINS:
            with self.subTest(domain=domain):
                builder = SCHEMA_BUILDERS[domain]
                schema = attach_staff_posts(builder("测试课题"), domain, proposal_text="")
                posts = ((schema.get("roles") or {}).get("staff_posts") or [])
                used = {
                    pk
                    for p in posts
                    if isinstance(p, dict)
                    for pk in (p.get("packs") or [])
                    if isinstance(pk, str)
                }
                menus = schema.get("staffPackMenus") or {}
                pages = schema.get("staffPackPages") or {}
                self.assertTrue(set(menus.keys()) <= used)
                self.assertTrue(set(pages.keys()) <= used)
                caps = set(DOMAIN_CAPABILITIES.get(domain) or [])
                if "slot_reserve" not in caps:
                    self.assertNotIn("slot_ops", menus)
                    flat = {k for keys in menus.values() for k in keys}
                    self.assertNotIn("reservations", flat)

    def test_category_entity_when_admin_menu_has_it(self) -> None:
        for domain in _SAMPLE_DOMAINS:
            with self.subTest(domain=domain):
                schema = attach_staff_posts(
                    SCHEMA_BUILDERS[domain]("测试课题"), domain, proposal_text=""
                )
                admin_keys = {
                    m.get("key")
                    for m in (schema.get("menus") or {}).get("admin") or []
                    if isinstance(m, dict)
                }
                if "category" not in admin_keys:
                    continue
                cat = (schema.get("entities") or {}).get("category") or {}
                self.assertEqual(cat.get("key"), "category")
                self.assertTrue(str(cat.get("label") or "").strip())

    def test_notice_detail_no_hardcoded_body_heading(self) -> None:
        path = (
            Path(__file__).resolve().parents[2]
            / "skeletons"
            / "baseline"
            / "frontend"
            / "src"
            / "views"
            / "NoticeDetail.vue"
        )
        text = path.read_text(encoding="utf-8")
        self.assertNotIn(">公告正文<", text)
        self.assertIn("bodyHeading", text)

    def test_qa_filters_structured_contradictions(self) -> None:
        from app.llm.agents_qa import _filter_findings, _is_noise_finding

        ctx = {
            "entityKeys": ["archive", "ticket", "category"],
            "menuKeys": {"admin": ["dashboard", "archive", "category"], "user": ["archive"]},
            "staffPackMenus": {"ticket_ops": ["dashboard", "ticket_pending"]},
            "traits": {"followUp": True},
            "files": {
                "frontend/src/views/NoticeDetail.vue": "<h2>{{ bodyHeading }}</h2>",
            },
        }
        self.assertTrue(
            _is_noise_finding("未使用的'reservation'实体与未定义的'category'实体", ctx)
        )
        self.assertTrue(_is_noise_finding("系统特征标记'crm:true'与当前领域无关", ctx))
        self.assertTrue(_is_noise_finding("公告详情页存在写死文案'公告正文'", ctx))
        # 真跨域错词应保留
        kept = _filter_findings(
            [
                {"level": "error", "msg": "未使用的'reservation'实体", "where": "schema"},
                {"level": "warn", "msg": "真·跨域借阅须知残留", "where": "Notices.vue"},
            ],
            ctx,
        )
        self.assertEqual(len(kept), 1)
        self.assertIn("借阅须知", kept[0]["msg"])

        # 预约域本身有 reservation 时，勿滤掉真实问题
        slot_ctx = {
            **ctx,
            "entityKeys": ["archive", "reservation", "category"],
            "menuKeys": {"admin": ["reservations", "category"], "user": ["my_reservations"]},
            "staffPackMenus": {"slot_ops": ["dashboard", "reservations"]},
            "traits": {},
        }
        self.assertFalse(_is_noise_finding("reservation 状态文案与开题不符", slot_ctx))

    def test_honesty_hard_boundary_as_supported(self) -> None:
        from app.llm.agents_qa import _honesty_findings

        bad = _honesty_findings(
            {
                "domain": "DOM-FOOD",
                "labels": {"authPoints": ["支持微信支付与人脸识别闸机"]},
                "menus": {},
                "proposal": "",
            }
        )
        self.assertTrue(any(f.get("level") == "error" for f in bad), bad)

        ok = _honesty_findings(
            {
                "domain": "DOM-FOOD",
                "labels": {"authPoints": ["真微信支付与人脸识别不在本期"]},
                "menus": {},
                "proposal": "",
            }
        )
        self.assertFalse(any(f.get("level") == "error" for f in ok), ok)

        # 仅出现硬边界词、无「已支持」类宣称 → 不挡包（非穷举否定词表）
        mention = _honesty_findings(
            {
                "domain": "DOM-FOOD",
                "labels": {"authPoints": ["调研阶段常见人脸识别与闸机方案"]},
                "menus": {},
                "proposal": "",
            }
        )
        self.assertFalse(any(f.get("level") == "error" for f in mention), mention)

        # 划界句含「第三方电子签」字样（DOM-CARPASS eSignLead 回归）
        esign = _honesty_findings(
            {
                "domain": "DOM-CARPASS",
                "labels": {
                    "eSignLead": "上传签章图并勾选同意完成签署；非 CA、非法大大等第三方电子签平台。",
                },
                "menus": {},
                "proposal": "",
            }
        )
        self.assertFalse(any(f.get("level") == "error" for f in esign), esign)

        # 「不支持」不得当成宣称支持
        deny = _honesty_findings(
            {
                "domain": "DOM-FOOD",
                "labels": {"authPoints": ["本系统不支持人脸识别与微信支付"]},
                "menus": {},
                "proposal": "",
            }
        )
        self.assertFalse(any(f.get("level") == "error" for f in deny), deny)

    def test_honesty_out_scope_lines_not_as_supported(self) -> None:
        """开题 out_scope 列人脸/GPS 不得挡包（DOM-CHECKIN 真题回归）。"""
        from app.llm.agents_common import _proposal_text
        from app.llm.agents_qa import _honesty_findings

        spec = {
            "proposal": {
                "title": "高校宿舍归寝签到管理系统",
                "background": "归寝登记与口令签到",
                "feature_lines": [
                    "寝室信息与查寝场次维护",
                    "用户信息管理与公告发布",
                ],
                "out_scope_lines": [
                    "门禁硬件联动",
                    "人脸识别签到",
                    "GPS轨迹打卡",
                    "第三方平台接口集成",
                    "其他扩展能力不作为本期系统必实现项",
                ],
            }
        }
        blob = _proposal_text(spec)
        self.assertIn("非本期：人脸识别签到", blob)
        findings = _honesty_findings(
            {
                "domain": "DOM-CHECKIN",
                "labels": {"authPoints": ["归寝登记与口令签到"]},
                "menus": {},
                "proposal": blob[:800],
            }
        )
        self.assertFalse(
            any(f.get("level") == "error" for f in findings),
            findings,
        )

    def test_honesty_wrong_domain_entity_warn(self) -> None:
        from app.llm.agents_qa import _honesty_findings

        warn = _honesty_findings(
            {
                "domain": "DOM-INTERN",
                "labels": {"heroTitle": "多单位入职投递平台"},
                "menus": {"user": [{"key": "archive", "label": "简历投递"}]},
                "proposal": "",
            }
        )
        self.assertTrue(any("错域实体词" in str(f.get("msg")) for f in warn), warn)


if __name__ == "__main__":
    unittest.main()
