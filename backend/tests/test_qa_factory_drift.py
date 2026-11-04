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

        # 未挂 my_tickets 时，MyTickets 图书馆残留属噪声（archive 壳）
        archive_ctx = {
            **ctx,
            "entityKeys": ["archive", "category", "favorites"],
            "menuKeys": {
                "admin": ["dashboard", "archive", "category"],
                "user": ["archive", "favorites"],
            },
            "staffPackMenus": {},
            "traits": {},
        }
        self.assertTrue(
            _is_noise_finding(
                "检测到图书馆域残留模板：MyTickets.vue 内写死已续借",
                archive_ctx,
            )
        )
        # where 带路径、msg 不提文件名（真实 LLM 输出）
        self.assertTrue(
            _is_noise_finding(
                "检测到图书馆域残留模板：文件内写死已续借",
                archive_ctx,
                where="frontend/src/views/user/MyTickets.vue",
            )
        )
        ticket_ctx = {
            **archive_ctx,
            "menuKeys": {
                "admin": ["dashboard", "tickets"],
                "user": ["my_tickets"],
            },
        }
        self.assertFalse(
            _is_noise_finding(
                "检测到图书馆域残留模板：文件内写死已续借",
                ticket_ctx,
                where="frontend/src/views/user/MyTickets.vue",
            )
        )
        # 状态不在 schema、摘录里又包在 allow* 开关里 → 任一域都不当错域
        gated = {
            **ticket_ctx,
            "entities": {
                "ticket": {
                    "states": {
                        "pending": "待审",
                        "approved": "通过",
                        "rejected": "已驳回",
                    }
                }
            },
            "files": {
                "frontend/src/views/user/MyTickets.vue": (
                    '<template v-if="allowBookHold && row.status === \'hold_ready\'">'
                    "取书截止"
                ),
            },
        }
        self.assertTrue(
            _is_noise_finding(
                "页面残留未定义状态 hold_ready",
                gated,
                where="frontend/src/views/user/MyTickets.vue",
            )
        )
        listed = {
            **gated,
            "entities": {
                "ticket": {
                    "states": {
                        "pending": "待审",
                        "hold_ready": "待取书",
                    }
                }
            },
        }
        self.assertFalse(
            _is_noise_finding(
                "页面残留未定义状态 hold_ready",
                listed,
                where="frontend/src/views/user/MyTickets.vue",
            )
        )
        ungated = {
            **gated,
            "files": {
                "frontend/src/views/user/MyTickets.vue": "row.status === 'hold_ready'",
            },
        }
        self.assertFalse(
            _is_noise_finding(
                "页面残留未定义状态 hold_ready",
                ungated,
                where="frontend/src/views/user/MyTickets.vue",
            )
        )

        # 预约域本身有 reservation 时，勿滤掉真实问题
        slot_ctx = {
            **ctx,
            "entityKeys": ["archive", "reservation", "category"],
            "menuKeys": {"admin": ["reservations", "category"], "user": ["my_reservations"]},
            "staffPackMenus": {"slot_ops": ["dashboard", "reservations"]},
            "traits": {},
        }
        self.assertFalse(_is_noise_finding("reservation 状态文案与开题不符", slot_ctx))

    def test_qa_skips_my_tickets_excerpt_when_unmounted(self) -> None:
        import tempfile
        from pathlib import Path

        from app.llm.agents_qa import _collect_qa_context

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "frontend" / "src" / "views" / "user").mkdir(parents=True)
            (root / "frontend" / "src" / "views" / "user" / "MyTickets.vue").write_text(
                "已续借", encoding="utf-8"
            )
            (root / "frontend" / "src" / "views" / "NoticeDetail.vue").write_text(
                "<h2>{{ bodyHeading }}</h2>", encoding="utf-8"
            )
            spec = {
                "domain": "DOM-MUSIC",
                "schema": {
                    "menus": {"user": [{"key": "archive"}], "admin": [{"key": "archive"}]},
                    "entities": {"archive": {"label": "歌曲"}},
                    "labels": {"appName": "曲库"},
                },
            }
            ctx = _collect_qa_context(root, spec)
            self.assertNotIn("frontend/src/views/user/MyTickets.vue", ctx["files"])

            spec["schema"]["menus"]["user"].append({"key": "my_tickets"})
            ctx2 = _collect_qa_context(root, spec)
            self.assertIn("frontend/src/views/user/MyTickets.vue", ctx2["files"])

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

    def test_honesty_refund_claim_without_order_surface(self) -> None:
        """未挂订单面却写「可退款」→ error；有订单面或划界 → 不挡。"""
        from app.llm.agents_qa import _honesty_findings

        bad = _honesty_findings(
            {
                "domain": "DOM-LIBRARY",
                "labels": {"faqLead": "支持退款，下单后可一键退款"},
                "menus": {"user": [{"key": "archive", "label": "馆藏"}]},
                "capabilities": [],
                "proposal": "",
            }
        )
        self.assertTrue(any(f.get("level") == "error" for f in bad), bad)

        scoped = _honesty_findings(
            {
                "domain": "DOM-LIBRARY",
                "labels": {"faqLead": "在线退款不在本期，仅登记人工处理"},
                "menus": {"user": [{"key": "archive", "label": "馆藏"}]},
                "capabilities": [],
                "proposal": "",
            }
        )
        self.assertFalse(any(f.get("level") == "error" for f in scoped), scoped)

        with_orders = _honesty_findings(
            {
                "domain": "DOM-SHOP",
                "labels": {"ordersLead": "支持退款申请"},
                "menus": {"user": [{"key": "my_orders", "label": "我的订单"}]},
                "capabilities": ["order_lines"],
                "proposal": "",
            }
        )
        self.assertFalse(
            any("退款" in str(f.get("msg")) and f.get("level") == "error" for f in with_orders),
            with_orders,
        )

    def test_honesty_faq_and_notice_seed_sql_surface(self) -> None:
        """FAQ / 公告 SQL 种子须进诚实扫描面（关 LLM 也能本地打红）。"""
        from app.llm.agents_qa import _fallback_qa, _honesty_findings

        faq_sql = (
            "INSERT INTO sys_ai_knowledge (category, title, content, keywords, hit_count)\n"
            "SELECT '支付', '支付渠道', '本系统已对接微信支付与支付宝支付', '支付', 0\n"
            "FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_ai_knowledge WHERE title='支付渠道');"
        )
        bad_faq = _honesty_findings(
            {
                "domain": "DOM-FOOD",
                "labels": {"appName": "食堂"},
                "menus": {},
                "seed_sql": faq_sql,
                "proposal": "",
            }
        )
        self.assertTrue(any(f.get("level") == "error" for f in bad_faq), bad_faq)

        notice_sql = (
            "INSERT INTO sys_notice (title, content, publisher_username, publisher_name)\n"
            "SELECT '售后说明', '本店支持七天无理由退款', 'admin', '管理员'\n"
            "FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='售后说明');"
        )
        bad_notice = _honesty_findings(
            {
                "domain": "DOM-MUSIC",
                "labels": {"appName": "曲库"},
                "menus": {"user": [{"key": "archive", "label": "曲目"}]},
                "capabilities": [],
                "seed_sql": notice_sql,
                "proposal": "",
            }
        )
        self.assertTrue(any(f.get("level") == "error" for f in bad_notice), bad_notice)

        # portal banner 面
        banner_hit = _honesty_findings(
            {
                "domain": "DOM-FOOD",
                "labels": {},
                "menus": {},
                "schema": {
                    "portalBanners": [
                        {"title": "支付升级", "lead": "已接入短信网关与高德地图"},
                    ]
                },
                "proposal": "",
            }
        )
        self.assertTrue(any(f.get("level") == "error" for f in banner_hit), banner_hit)

        mini = _honesty_findings(
            {
                "domain": "DOM-FOOD",
                "labels": {"techLead": "本期已支持小程序原生交付"},
                "menus": {},
                "proposal": "",
            }
        )
        self.assertTrue(any(f.get("level") == "error" for f in mini), mini)

        report = _fallback_qa(
            {
                "domain": "DOM-FOOD",
                "labels": {"appName": "食堂", "noticePageTitle": "公告"},
                "menus": {},
                "menuKeys": {},
                "entityKeys": [],
                "capabilities": [],
                "files": {},
                "missing_files": [],
                "seed_sql": faq_sql,
                "proposal": "",
            }
        )
        self.assertFalse(report.get("ok"), report)

    def test_honesty_error_blocks_p3q_zip(self) -> None:
        """本地 honesty error → fallback ok=False → apply_qa_to_gates 禁 ZIP。"""
        from app.llm.agents_qa import _fallback_qa
        from app.services.delivery_review import apply_qa_to_gates

        qa = _fallback_qa(
            {
                "domain": "DOM-FOOD",
                "labels": {
                    "appName": "食堂",
                    "noticePageTitle": "公告",
                    "authPoints": ["已支持人脸识别闸机"],
                },
                "menus": {},
                "menuKeys": {},
                "entityKeys": [],
                "capabilities": [],
                "files": {},
                "missing_files": [],
                "proposal": "",
            }
        )
        self.assertFalse(qa.get("ok"), qa)
        self.assertTrue(any(f.get("level") == "error" for f in qa.get("findings") or []))

        gates = {"overall": True, "zip_allowed": True}
        apply_qa_to_gates(gates, qa, warn_blocks=False)
        self.assertFalse(gates["p3q"]["ok"], gates["p3q"])
        self.assertFalse(gates["zip_allowed"])
        self.assertFalse(gates["overall"])

    def test_payment_copy_blocks_fallback_qa_without_llm(self) -> None:
        """关 LLM QA 时，支付宝/微信下单句仍须结构闸 error 挡包（农产续跑装绿回归）。"""
        from app.llm.agents_qa import _fallback_qa, _payment_copy_findings

        dirty = {
            "labels": {
                "demoPayHint": "请选择支付宝或微信支付完成下单。",
                "appName": "农产商城",
                "noticePageTitle": "公告",
            },
            "capabilities": ["wallet", "order"],
            "menus": {},
            "menuKeys": {},
            "entityKeys": [],
            "files": {},
            "missing_files": [],
            "proposal": "",
            "domain": "DOM-SHOP",
        }
        hits = _payment_copy_findings(dirty)
        self.assertTrue(any(f.get("level") == "error" for f in hits), hits)
        report = _fallback_qa(dirty)
        self.assertFalse(report.get("ok"), report)
        self.assertEqual(report.get("mode"), "fallback")

        clean = {
            **dirty,
            "labels": {
                **dirty["labels"],
                "demoPayHint": "请选择支付方式并输入支付密码，费用从账户余额扣除。",
            },
        }
        self.assertFalse(_payment_copy_findings(clean))
        self.assertTrue(_fallback_qa(clean).get("ok"))

        honest = {
            **dirty,
            "labels": {
                **dirty["labels"],
                "demoPayHint": "选择支付宝或微信并输入支付密码，扣减账户余额。",
            },
        }
        self.assertFalse(_payment_copy_findings(honest))

    def test_marketplace_admin_order_lead_blocks_merchant_ops(self) -> None:
        """多店 ordersAdminLead 写发货/物流 → 结构闸 error（不靠 LLM 碰运气）。"""
        from app.llm.agents_qa import _fallback_qa, _marketplace_role_copy_findings

        dirty = {
            "schema": {"shopMarketplace": True},
            "labels": {
                "ordersAdminLead": "处理发货、物流与售后申请。",
                "appName": "多店商城",
                "noticePageTitle": "活动公告",
            },
            "capabilities": ["order"],
            "menus": {},
            "menuKeys": {},
            "entityKeys": [],
            "files": {},
            "missing_files": [],
            "proposal": "管理员仅做全平台订单与售后监督",
            "domain": "DOM-SHOP",
        }
        hits = _marketplace_role_copy_findings(dirty)
        self.assertTrue(any(f.get("level") == "error" for f in hits), hits)
        self.assertTrue(any("ordersAdminLead" in str(f.get("msg")) for f in hits), hits)
        self.assertFalse(_fallback_qa(dirty).get("ok"))

        clean = {
            **dirty,
            "labels": {
                **dirty["labels"],
                "ordersAdminLead": "查看全平台订单与售后，必要时介入处理。",
                "ordersStaffLead": "处理本店发货、物流与售后申请。",
            },
        }
        self.assertFalse(_marketplace_role_copy_findings(clean))
        self.assertTrue(_fallback_qa(clean).get("ok"))

    def test_order_review_blocks_buyer_copy_for_merchant(self) -> None:
        """merchant_ops + order_review：缺商家评价导语或写买家口径 → error。"""
        from app.llm.agents_qa import _fallback_qa, _order_review_role_copy_findings

        dirty = {
            "schema": {
                "shopMarketplace": True,
                "roles": {
                    "staff_posts": [
                        {
                            "id": "merchant",
                            "label": "商家",
                            "kind": "clerk",
                            "packs": ["merchant_ops"],
                        }
                    ]
                },
            },
            "labels": {
                "orderReviewPageTitle": "我的评价",
                "orderReviewPageLead": "对已完成订单进行星级与文字评价。",
                "appName": "农产品商城",
                "noticePageTitle": "活动公告",
            },
            "capabilities": ["order", "order_review"],
            "menus": {},
            "menuKeys": {},
            "entityKeys": [],
            "files": {},
            "missing_files": [],
            "proposal": "商家端评价回复",
            "domain": "DOM-SHOP",
        }
        hits = _order_review_role_copy_findings(dirty)
        self.assertTrue(any(f.get("level") == "error" for f in hits), hits)
        self.assertTrue(
            any("orderReviewStaffPageLead" in str(f.get("where")) for f in hits), hits
        )
        self.assertFalse(_fallback_qa(dirty).get("ok"))

        clean = {
            **dirty,
            "labels": {
                **dirty["labels"],
                "orderReviewAdminPageLead": "查看全平台评价，必要时删除不当内容。",
                "orderReviewStaffPageLead": "查看本店评价并回复买家。",
            },
        }
        self.assertFalse(_order_review_role_copy_findings(clean))
        self.assertTrue(_fallback_qa(clean).get("ok"))

    def test_order_review_llm_warn_filtered_when_staff_leads_present(self) -> None:
        """已有商家/总管评价导语时，LLM 再报买家键不匹配 → 噪声滤掉（warn 挡包场景）。"""
        from app.llm.agents_qa import _filter_findings, _is_noise_finding

        ctx = {
            "labels": {
                "orderReviewPageTitle": "我的评价",
                "orderReviewPageLead": "对已完成订单进行星级与文字评价。",
                "orderReviewAdminPageLead": "查看全平台评价，必要时删除不当内容。",
                "orderReviewStaffPageLead": "查看本店评价并回复买家。",
            },
            "entityKeys": [],
            "menuKeys": {},
            "staffPackMenus": {},
            "traits": {},
            "files": {},
        }
        msg = (
            "merchant_ops 包含 order_reviews，开题也明确商家端评价回复，"
            "但现有 orderReviewPageTitle/orderReviewPageLead 只有买家口径"
            "「我的评价/对已完成订单进行星级与文字评价」，"
            "商家进入该菜单会看到不匹配文案。"
            "建议按角色补充商家「评价管理/回复评价」标题与引导。"
        )
        self.assertTrue(_is_noise_finding(msg, ctx, where="schema.labels"))
        kept = _filter_findings(
            [{"level": "warn", "msg": msg, "where": "schema.labels.orderReviewPageLead"}],
            ctx,
        )
        self.assertEqual(kept, [])

        # 真缺商家导语时不得滤
        missing_ctx = {
            **ctx,
            "labels": {
                "orderReviewPageTitle": "我的评价",
                "orderReviewPageLead": "对已完成订单进行星级与文字评价。",
            },
        }
        self.assertFalse(_is_noise_finding(msg, missing_ctx))

    def test_qa_filters_pure_polish_suggestions(self) -> None:
        """纯润色建议滤掉；带「缺失/不匹配」的真报保留。"""
        from app.llm.agents_qa import _filter_findings, _is_noise_finding

        ctx = {
            "labels": {},
            "entityKeys": ["order"],
            "menuKeys": {},
            "staffPackMenus": {},
            "traits": {},
            "files": {},
        }
        self.assertTrue(
            _is_noise_finding("建议优化订单页措辞，体验上可以更好。", ctx)
        )
        self.assertFalse(
            _is_noise_finding(
                "缺 labels.ordersStaffLead，商家订单页文案不匹配。",
                ctx,
            )
        )
        kept = _filter_findings(
            [
                {"level": "warn", "msg": "不妨润色一下公告标题。", "where": "labels"},
                {
                    "level": "warn",
                    "msg": "菜单有 order_reviews 却缺失商家评价导语。",
                    "where": "labels",
                },
                {
                    "level": "warn",
                    "msg": "公告语气可以更专业一些。",
                    "where": "labels.noticePageLead",
                },
            ],
            ctx,
        )
        self.assertEqual(len(kept), 1)
        self.assertIn("缺失", kept[0]["msg"])

    def test_qa_llm_warn_requires_program_impact(self) -> None:
        """LLM warn 须带影响程序信号；口味类直接丢。"""
        from app.llm.agents_qa import _filter_findings, _llm_finding_affects_program

        self.assertFalse(_llm_finding_affects_program("标题用词不够贴切。"))
        self.assertTrue(
            _llm_finding_affects_program(
                "商家菜单已挂 order_reviews，却缺失 labels.orderReviewStaffPageLead。"
            )
        )
        kept = _filter_findings(
            [
                {"level": "warn", "msg": "标题用词不够贴切。", "where": "labels"},
                {
                    "level": "error",
                    "msg": "capabilities 未挂支付却宣称已对接微信支付。",
                    "where": "README",
                },
            ],
            {
                "labels": {},
                "entityKeys": [],
                "menuKeys": {},
                "staffPackMenus": {},
                "traits": {},
                "files": {},
            },
        )
        self.assertEqual(len(kept), 1)
        self.assertIn("微信支付", kept[0]["msg"])

    def test_marketplace_notice_blocks_admin_ship_copy(self) -> None:
        """多店 seeds.noticeBody 写「管理员确认发货」→ 结构闸 error。"""
        from app.llm.agents_qa import _fallback_qa, _marketplace_role_copy_findings

        dirty = {
            "schema": {
                "shopMarketplace": True,
                "seeds": {"noticeBody": "下单后由管理员确认发货或自提。"},
            },
            "labels": {
                "ordersAdminLead": "查看全平台订单与售后，必要时介入处理。",
                "appName": "多店商城",
                "noticePageTitle": "活动公告",
            },
            "capabilities": ["order"],
            "menus": {},
            "menuKeys": {},
            "entityKeys": [],
            "files": {},
            "missing_files": [],
            "proposal": "商家入驻；平台监督",
            "domain": "DOM-SHOP",
        }
        hits = _marketplace_role_copy_findings(dirty)
        self.assertTrue(any("noticeBody" in str(f.get("where")) for f in hits), hits)
        self.assertFalse(_fallback_qa(dirty).get("ok"))

        clean = {
            **dirty,
            "schema": {
                "shopMarketplace": True,
                "seeds": {"noticeBody": "多店入驻；下单后可在订单页查看进度。"},
            },
        }
        self.assertFalse(_marketplace_role_copy_findings(clean))
        self.assertTrue(_fallback_qa(clean).get("ok"))

    def test_food_admin_order_lead_blocks_stall_ops(self) -> None:
        """DOM-FOOD ordersAdminLead 写接单/出餐 → 结构闸 error（不靠 LLM）。"""
        from app.llm.agents_qa import _fallback_qa, _food_role_copy_findings

        dirty = {
            "schema": {"domain": "DOM-FOOD"},
            "labels": {
                "ordersAdminLead": "处理本档口接单、出餐与配送状态。",
                "appName": "食堂点餐",
                "noticePageTitle": "食堂公告",
            },
            "capabilities": ["order"],
            "menus": {},
            "menuKeys": {},
            "entityKeys": [],
            "files": {},
            "missing_files": [],
            "proposal": "主管监督全食堂订单；档口接单出餐",
            "domain": "DOM-FOOD",
        }
        hits = _food_role_copy_findings(dirty)
        self.assertTrue(any(f.get("level") == "error" for f in hits), hits)
        self.assertTrue(any("ordersAdminLead" in str(f.get("msg")) for f in hits), hits)
        self.assertFalse(_fallback_qa(dirty).get("ok"))

        clean = {
            **dirty,
            "labels": {
                **dirty["labels"],
                "ordersAdminLead": "查看全食堂订单与退单，必要时介入处理。",
                "ordersStaffLead": "处理本档口接单、出餐与配送状态。",
            },
        }
        self.assertFalse(_food_role_copy_findings(clean))
        self.assertTrue(_fallback_qa(clean).get("ok"))

    def test_reserve_fulfill_blocks_ship_copy(self) -> None:
        """stay/rental/cinema：履约 hint / 主管 lead 写发货 → 结构闸 error。"""
        from app.llm.agents_qa import _fallback_qa, _reserve_fulfill_copy_findings

        dirty = {
            "schema": {
                "entities": {
                    "order": {
                        "fulfillMode": "stay",
                        "verbs": {"ship": "发货", "complete": "完成"},
                    }
                }
            },
            "labels": {
                "orderFulfillHint": "下单后发货配送到客房。",
                "ordersAdminLead": "处理发货与物流。",
                "appName": "酒店",
                "noticePageTitle": "入住须知",
            },
            "capabilities": ["order_lines"],
            "menus": {},
            "menuKeys": {},
            "entityKeys": [],
            "files": {},
            "missing_files": [],
            "proposal": "客房预订",
            "domain": "DOM-HOTEL",
        }
        hits = _reserve_fulfill_copy_findings(dirty)
        self.assertTrue(any(f.get("level") == "error" for f in hits), hits)
        self.assertFalse(_fallback_qa(dirty).get("ok"))

        clean = {
            **dirty,
            "schema": {
                "entities": {
                    "order": {
                        "fulfillMode": "stay",
                        "verbs": {"ship": "办理入住", "complete": "办理离店"},
                    }
                }
            },
            "labels": {
                **dirty["labels"],
                "orderFulfillHint": "客房订单随预订生成；前台办理入住/离店，无物流发货。",
                "ordersAdminLead": "查看全店订单与预订，必要时介入处理。",
            },
        }
        self.assertFalse(_reserve_fulfill_copy_findings(clean))
        self.assertTrue(_fallback_qa(clean).get("ok"))

    def test_borrow_hold_leak_and_role_leads(self) -> None:
        """非图书借用域挂待取书 → error；缺 tickets*Lead → error。"""
        from app.llm.agents_qa import _borrow_role_copy_findings, _fallback_qa

        dirty_hold = {
            "schema": {
                "roles": {"staff_posts": [{"id": "keeper", "label": "器材管理员"}]},
                "entities": {
                    "ticket": {
                        "allowBookHold": True,
                        "states": {"pending": "待审", "hold_ready": "待取书"},
                    }
                },
            },
            "labels": {
                "ticketsAdminLead": "查看全室借用与额度，必要时介入处理。",
                "ticketsStaffLead": "审批借用、发放归还验收与催还。",
                "appName": "设备借用",
                "noticePageTitle": "公告",
            },
            "capabilities": ["ticket_flow"],
            "menus": {},
            "menuKeys": {},
            "entityKeys": [],
            "files": {},
            "missing_files": [],
            "proposal": "设备借用",
            "domain": "DOM-EQUIP",
        }
        hits = _borrow_role_copy_findings(dirty_hold)
        self.assertTrue(any("取书" in str(f.get("msg")) for f in hits), hits)
        self.assertFalse(_fallback_qa(dirty_hold).get("ok"))

        missing_leads = {
            **dirty_hold,
            "schema": {
                "roles": {"staff_posts": [{"id": "keeper", "label": "器材管理员"}]},
                "entities": {"ticket": {"states": {"pending": "待审"}}},
            },
            "labels": {
                "appName": "设备借用",
                "noticePageTitle": "公告",
            },
        }
        hits2 = _borrow_role_copy_findings(missing_leads)
        self.assertTrue(any("ticketsAdminLead" in str(f.get("where")) for f in hits2), hits2)

        clean = {
            **missing_leads,
            "labels": {
                "ticketsAdminLead": "查看全室借用与额度，必要时介入处理。",
                "ticketsStaffLead": "审批借用、发放归还验收与催还。",
                "appName": "设备借用",
                "noticePageTitle": "公告",
            },
        }
        self.assertFalse(_borrow_role_copy_findings(clean))
        self.assertTrue(_fallback_qa(clean).get("ok"))

    def test_ticket_repair_blocks_shop_copy_and_needs_leads(self) -> None:
        """报修组：商城发货口吻 → error；缺 tickets*Lead → error。"""
        from app.llm.agents_qa import _fallback_qa, _ticket_role_copy_findings

        dirty = {
            "schema": {
                "roles": {"staff_posts": [{"id": "dorm_mgr", "label": "楼管"}]},
                "entities": {
                    "ticket": {
                        "verbs": {
                            "apply": "提交报修",
                            "approve": "发货",
                            "reject": "驳回",
                            "return": "完成",
                        }
                    }
                },
            },
            "labels": {
                "ticketsAdminLead": "处理发货与物流售后。",
                "ticketsStaffLead": "受理报修、派单跟进与办结。",
                "appName": "宿舍报修",
                "noticePageTitle": "报修须知",
            },
            "capabilities": ["ticket_flow"],
            "menus": {},
            "menuKeys": {},
            "entityKeys": [],
            "files": {},
            "missing_files": [],
            "proposal": "宿舍报修",
            "domain": "DOM-DORM",
        }
        hits = _ticket_role_copy_findings(dirty)
        self.assertTrue(any(f.get("level") == "error" for f in hits), hits)
        self.assertFalse(_fallback_qa(dirty).get("ok"))

        missing = {
            **dirty,
            "schema": {
                "roles": {"staff_posts": [{"id": "dorm_mgr", "label": "楼管"}]},
                "entities": {
                    "ticket": {
                        "verbs": {
                            "apply": "提交报修",
                            "approve": "受理",
                            "reject": "驳回",
                            "return": "完成",
                        }
                    }
                },
            },
            "labels": {"appName": "宿舍报修", "noticePageTitle": "报修须知"},
        }
        hits2 = _ticket_role_copy_findings(missing)
        self.assertTrue(any("ticketsAdminLead" in str(f.get("where")) for f in hits2), hits2)

        clean = {
            **missing,
            "labels": {
                "ticketsAdminLead": "查看全楼报修工单，维护楼栋与类型，必要时介入处理。",
                "ticketsStaffLead": "受理报修、派单跟进与办结。",
                "appName": "宿舍报修",
                "noticePageTitle": "报修须知",
            },
        }
        self.assertFalse(_ticket_role_copy_findings(clean))
        self.assertTrue(_fallback_qa(clean).get("ok"))

    def test_follow_blocks_foreign_copy_and_needs_leads(self) -> None:
        """跟进组：商城/借阅口吻 → error；缺 tickets*Lead → error。"""
        from app.llm.agents_qa import _fallback_qa, _follow_role_copy_findings

        dirty = {
            "schema": {
                "roles": {"staff_posts": [{"id": "intern_tutor", "label": "实习辅导员"}]},
                "entities": {"ticket": {"verbs": {"apply": "提交周报"}}},
            },
            "labels": {
                "ticketsAdminLead": "处理发货与物流。",
                "ticketsStaffLead": "审阅周报、催交与退回修改。",
                "appName": "顶岗实习",
                "noticePageTitle": "实习须知",
            },
            "capabilities": ["ticket_flow"],
            "menus": {},
            "menuKeys": {},
            "entityKeys": [],
            "files": {},
            "missing_files": [],
            "proposal": "实习周报",
            "domain": "DOM-INTERN",
        }
        hits = _follow_role_copy_findings(dirty)
        self.assertTrue(any(f.get("level") == "error" for f in hits), hits)
        self.assertFalse(_fallback_qa(dirty).get("ok"))

        missing = {
            **dirty,
            "labels": {"appName": "顶岗实习", "noticePageTitle": "实习须知"},
        }
        hits2 = _follow_role_copy_findings(missing)
        self.assertTrue(any("ticketsAdminLead" in str(f.get("where")) for f in hits2), hits2)

        clean = {
            **missing,
            "labels": {
                "ticketsAdminLead": "查看全员周报与实习岗位，必要时介入处理。",
                "ticketsStaffLead": "审阅周报、催交与退回修改。",
                "appName": "顶岗实习",
                "noticePageTitle": "实习须知",
            },
        }
        self.assertFalse(_follow_role_copy_findings(clean))
        self.assertTrue(_fallback_qa(clean).get("ok"))

    def test_approve_blocks_foreign_copy_and_needs_leads(self) -> None:
        """审批组：商城口吻 → error；缺 tickets*Lead → error。"""
        from app.llm.agents_qa import _approve_role_copy_findings, _fallback_qa

        dirty = {
            "schema": {
                "roles": {"staff_posts": [{"id": "seal_clerk", "label": "用章管理员"}]},
                "entities": {"ticket": {"verbs": {"apply": "提交用章"}}},
            },
            "labels": {
                "ticketsAdminLead": "处理发货与物流。",
                "ticketsStaffLead": "受理用章、核验材料与办结。",
                "appName": "用章审批",
                "noticePageTitle": "用章须知",
            },
            "capabilities": ["ticket_flow"],
            "menus": {},
            "menuKeys": {},
            "entityKeys": [],
            "files": {},
            "missing_files": [],
            "proposal": "用章审批",
            "domain": "DOM-SEAL",
        }
        hits = _approve_role_copy_findings(dirty)
        self.assertTrue(any(f.get("level") == "error" for f in hits), hits)
        self.assertFalse(_fallback_qa(dirty).get("ok"))

        missing = {
            **dirty,
            "labels": {"appName": "用章审批", "noticePageTitle": "用章须知"},
        }
        hits2 = _approve_role_copy_findings(missing)
        self.assertTrue(any("ticketsAdminLead" in str(f.get("where")) for f in hits2), hits2)

        clean = {
            **missing,
            "labels": {
                "ticketsAdminLead": "查看全盘用章申请，维护规则，必要时介入处理。",
                "ticketsStaffLead": "受理用章、核验材料与办结。",
                "appName": "用章审批",
                "noticePageTitle": "用章须知",
            },
        }
        self.assertFalse(_approve_role_copy_findings(clean))
        self.assertTrue(_fallback_qa(clean).get("ok"))

    def test_apply_blocks_foreign_copy_and_needs_leads(self) -> None:
        """报名组：商城口吻 → error；缺 tickets*Lead → error。"""
        from app.llm.agents_qa import _apply_role_copy_findings, _fallback_qa

        dirty = {
            "schema": {
                "roles": {"staff_posts": [{"id": "assistant", "label": "活动助理"}]},
                "entities": {"ticket": {"verbs": {"apply": "报名"}}},
            },
            "labels": {
                "ticketsAdminLead": "处理发货与物流。",
                "ticketsStaffLead": "审核报名、签到催办与取消处理。",
                "appName": "活动报名",
                "noticePageTitle": "报名须知",
            },
            "capabilities": ["ticket_flow"],
            "menus": {},
            "menuKeys": {},
            "entityKeys": [],
            "files": {},
            "missing_files": [],
            "proposal": "活动报名",
            "domain": "DOM-ACTIVITY",
        }
        hits = _apply_role_copy_findings(dirty)
        self.assertTrue(any(f.get("level") == "error" for f in hits), hits)
        self.assertFalse(_fallback_qa(dirty).get("ok"))

        missing = {
            **dirty,
            "labels": {"appName": "活动报名", "noticePageTitle": "报名须知"},
        }
        hits2 = _apply_role_copy_findings(missing)
        self.assertTrue(any("ticketsAdminLead" in str(f.get("where")) for f in hits2), hits2)

        clean = {
            **missing,
            "labels": {
                "ticketsAdminLead": "查看全盘活动报名，维护名额与规则，必要时介入处理。",
                "ticketsStaffLead": "审核报名、签到催办与取消处理。",
                "appName": "活动报名",
                "noticePageTitle": "报名须知",
            },
        }
        self.assertFalse(_apply_role_copy_findings(clean))
        self.assertTrue(_fallback_qa(clean).get("ok"))

    def test_content_blocks_foreign_copy_and_needs_leads(self) -> None:
        """内容组：商城口吻 → error；缺 tickets*Lead → error。"""
        from app.llm.agents_qa import _content_role_copy_findings, _fallback_qa

        dirty = {
            "schema": {
                "roles": {"staff_posts": [{"id": "moderator", "label": "版主"}]},
                "entities": {"ticket": {"verbs": {"apply": "跟帖"}}},
            },
            "labels": {
                "ticketsAdminLead": "处理发货与物流。",
                "ticketsStaffLead": "审核回复、处理违规与催办。",
                "appName": "校园论坛",
                "noticePageTitle": "站内公告",
            },
            "capabilities": ["ticket_flow", "content"],
            "menus": {},
            "menuKeys": {},
            "entityKeys": [],
            "files": {},
            "missing_files": [],
            "proposal": "校园论坛",
            "domain": "DOM-FORUM",
        }
        hits = _content_role_copy_findings(dirty)
        self.assertTrue(any(f.get("level") == "error" for f in hits), hits)
        self.assertFalse(_fallback_qa(dirty).get("ok"))

        missing = {
            **dirty,
            "labels": {"appName": "校园论坛", "noticePageTitle": "站内公告"},
        }
        hits2 = _content_role_copy_findings(missing)
        self.assertTrue(any("ticketsAdminLead" in str(f.get("where")) for f in hits2), hits2)

        clean = {
            **missing,
            "labels": {
                "ticketsAdminLead": "查看全盘主帖与回复，维护版规，必要时下架与介入处理。",
                "ticketsStaffLead": "审核回复、处理违规与催办。",
                "appName": "校园论坛",
                "noticePageTitle": "站内公告",
            },
        }
        self.assertFalse(_content_role_copy_findings(clean))
        self.assertTrue(_fallback_qa(clean).get("ok"))

    def test_interact_blocks_foreign_copy_and_needs_leads(self) -> None:
        """互动组：商城口吻 → error；缺 tickets*Lead → error。"""
        from app.llm.agents_qa import _interact_role_copy_findings, _fallback_qa

        dirty = {
            "schema": {
                "roles": {"staff_posts": [{"id": "matchmaker", "label": "联谊辅导员"}]},
                "entities": {"ticket": {"verbs": {"apply": "牵线"}}},
            },
            "labels": {
                "ticketsAdminLead": "处理发货与物流。",
                "ticketsStaffLead": "审核牵线、反馈结果与催办。",
                "appName": "校园交友",
                "noticePageTitle": "牵线须知",
            },
            "capabilities": ["ticket_flow", "dm"],
            "menus": {},
            "menuKeys": {},
            "entityKeys": [],
            "files": {},
            "missing_files": [],
            "proposal": "校园交友",
            "domain": "DOM-DATING",
        }
        hits = _interact_role_copy_findings(dirty)
        self.assertTrue(any(f.get("level") == "error" for f in hits), hits)
        self.assertFalse(_fallback_qa(dirty).get("ok"))

        missing = {
            **dirty,
            "labels": {"appName": "校园交友", "noticePageTitle": "牵线须知"},
        }
        hits2 = _interact_role_copy_findings(missing)
        self.assertTrue(any("ticketsAdminLead" in str(f.get("where")) for f in hits2), hits2)

        clean = {
            **missing,
            "labels": {
                "ticketsAdminLead": "查看全盘牵线申请，维护规范，必要时介入处理。",
                "ticketsStaffLead": "审核牵线、反馈结果与催办。",
                "appName": "校园交友",
                "noticePageTitle": "牵线须知",
            },
        }
        self.assertFalse(_interact_role_copy_findings(clean))
        self.assertTrue(_fallback_qa(clean).get("ok"))

    def test_fallback_blocks_admin_ship_and_needs_leads(self) -> None:
        """兜底组：管理员确认发货 → error；缺路径 lead → error。"""
        from app.llm.agents_qa import _fallback_qa, _fallback_role_copy_findings

        dirty = {
            "schema": {
                "roles": {"staff_posts": [{"id": "order_clerk", "label": "订单办理员"}]},
                "entities": {"order": {"states": {"pending": "待确认"}}},
                "seeds": {
                    "noticeTitle": "使用须知",
                    "noticeBody": "下单后由管理员确认发货或自提。",
                },
            },
            "labels": {
                "ordersAdminLead": "管理员确认发货与物流。",
                "ordersStaffLead": "确认履约、发货或自提与售后办理。",
                "appName": "通用交易",
                "noticePageTitle": "公告",
            },
            "capabilities": ["cart_order"],
            "menus": {},
            "menuKeys": {},
            "entityKeys": [],
            "files": {},
            "missing_files": [],
            "proposal": "通用交易",
            "domain": "DOM-GENERIC",
        }
        hits = _fallback_role_copy_findings(dirty)
        self.assertTrue(any(f.get("level") == "error" for f in hits), hits)
        self.assertFalse(_fallback_qa(dirty).get("ok"))

        missing = {
            **dirty,
            "schema": {
                "roles": {"staff_posts": [{"id": "clerk", "label": "审核员"}]},
                "entities": {"ticket": {"verbs": {"apply": "提交申请"}}},
                "seeds": {"noticeTitle": "须知", "noticeBody": "请按时办理。"},
            },
            "labels": {"appName": "业务申请", "noticePageTitle": "公告"},
        }
        hits2 = _fallback_role_copy_findings(missing)
        self.assertTrue(
            any("ticketsAdminLead" in str(f.get("where")) for f in hits2), hits2
        )

        clean = {
            **missing,
            "labels": {
                "ticketsAdminLead": "查看全盘申请，维护规则，必要时介入处理。",
                "ticketsStaffLead": "审核申请、催办与办结。",
                "appName": "业务申请",
                "noticePageTitle": "公告",
            },
        }
        self.assertFalse(_fallback_role_copy_findings(clean))
        self.assertTrue(_fallback_qa(clean).get("ok"))


if __name__ == "__main__":
    unittest.main()
