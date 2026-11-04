"""AI 助手按需开关 bake 冒烟（guestbook 式能力岛 + DeepSeek）。"""

from __future__ import annotations

import json
import shutil
import unittest
from pathlib import Path

from app.bake.catalog import build_spec
from app.bake.domain_schema import attach_accept
from app.bake.engine import bake_project
from app.bake.features.ai_assistant import (
    resolve_ai_knowledge_skin,
    scan_ai_assistant,
)
from app.bake.stack_scan import scan_stack
from app.core.config import get_settings

_FARM_TITLE = "基于 SpringBoot+Vue 的农产品选购答疑销售平台设计与实现"
_FARM_BODY = """
核心特色功能：AI智能农产品导购
- 对话式商品推荐、农产品文字问答
- 支持农产品图片上传匹配，识别农产品品类后定向检索对应知识
- 系统智能匹配知识库，自动回复农产品种植常识、保存方法、食用建议、挑选技巧
- 答疑结果支持文字展示与语音播报播放
- 用户可对答疑内容进行满意度反馈
- 平台展示热门农产品问答
"""


def _bake(
    *,
    ai_assistant: bool,
    pid: str,
    title: str = "校园二手交易平台",
    domain: str = "DOM-SHOP",
    proposal_excerpt: str | None = None,
) -> Path:
    settings = get_settings()
    dest = settings.workspace_dir / pid
    if dest.exists():
        shutil.rmtree(dest)
    excerpt = proposal_excerpt if proposal_excerpt is not None else title
    spec = build_spec(
        title=title,
        archetype="ARCH-CRUD",
        domain=domain,
        theme="gen-ink",
        llm_enabled=False,
        match_mode="recommended",
        confidence=0.9,
        ai_assistant=ai_assistant,
        proposal={"excerpt": excerpt},
    )
    return bake_project(pid, spec, f"smoke_ai_{pid}")


class TestAiAssistantScan(unittest.TestCase):
    def test_farm_opening_recommends_ai(self) -> None:
        self.assertTrue(scan_ai_assistant(_FARM_TITLE + "\n" + _FARM_BODY))
        stack = scan_stack(_FARM_TITLE, _FARM_BODY)
        self.assertTrue(stack.get("ai_assistant"))
        self.assertTrue(stack.get("recommended_ai_assistant"))
        addon = (stack.get("addons") or {}).get("ai_assistant") or {}
        self.assertTrue(addon.get("recommended"))

    def test_plain_shop_no_ai(self) -> None:
        self.assertFalse(scan_ai_assistant("二手交易平台 商品订单购物车"))
        stack = scan_stack("二手交易平台", "用户下单与评价")
        self.assertFalse(stack.get("ai_assistant"))

    def test_spring_ai_and_rag_phrases(self) -> None:
        for phrase in (
            "技术路线 Spring AI + Vue3",
            "基于 LangChain4j 实现智能客服",
            "RAG 检索增强问答",
            "智能匹配知识库",
            "AI 阅读助手",
        ):
            self.assertTrue(scan_ai_assistant(phrase), phrase)
            stack = scan_stack("管理系统", phrase)
            self.assertTrue(stack.get("ai_assistant"), phrase)

    def test_knowledge_skin_by_opening_and_domain(self) -> None:
        self.assertEqual(
            resolve_ai_knowledge_skin("DOM-SHOP", _FARM_TITLE, _FARM_BODY),
            "shop_farm",
        )
        self.assertEqual(
            resolve_ai_knowledge_skin("DOM-LIBRARY", "图书管理系统", "借阅与馆员问答"),
            "library_book",
        )
        self.assertEqual(
            resolve_ai_knowledge_skin("DOM-SHOP", "二手商城", "购物车与订单"),
            "shop_retail",
        )
        self.assertEqual(
            resolve_ai_knowledge_skin("DOM-ATTEND", "请假系统", "请假销假"),
            "attend",
        )
        self.assertEqual(
            resolve_ai_knowledge_skin("DOM-GENERIC", "综合系统", "公告与资料"),
            "generic",
        )
        # 客房/租车/线路等须自有 FAQ 皮，禁止再挂商城购物车口吻
        self.assertEqual(
            resolve_ai_knowledge_skin("DOM-HOTEL", "宾馆客房预订", "入住离店"),
            "hotel",
        )
        self.assertEqual(
            resolve_ai_knowledge_skin("DOM-TOUR", "旅行社线路报名", "出团确认"),
            "tour",
        )
        self.assertEqual(
            resolve_ai_knowledge_skin("DOM-CARRENT", "汽车租赁管理", "取还车"),
            "carrent",
        )
        self.assertEqual(
            resolve_ai_knowledge_skin("DOM-LISTING", "房源中介带看", "整租合租"),
            "listing",
        )
        self.assertEqual(
            resolve_ai_knowledge_skin("DOM-CINEMA", "影院选座购票", "场次座位"),
            "cinema",
        )
        for dom, title in (
            ("DOM-HOTEL", "宾馆客房预订"),
            ("DOM-TOUR", "旅行社线路报名"),
            ("DOM-CARRENT", "汽车租赁管理"),
        ):
            skin = resolve_ai_knowledge_skin(dom, title, "")
            self.assertFalse(skin.startswith("shop_"), f"{dom} -> {skin}")
        # 报修簇与业务域各自成皮，勿再共用 dorm
        self.assertEqual(
            resolve_ai_knowledge_skin("DOM-PROPERTY", "物业报修", "楼栋水电"),
            "property",
        )
        self.assertEqual(
            resolve_ai_knowledge_skin("DOM-IT", "校园网故障报修", "终端机房"),
            "it",
        )
        self.assertEqual(
            resolve_ai_knowledge_skin("DOM-DORM", "宿舍报修", "水电门窗"),
            "dorm",
        )
        self.assertEqual(
            resolve_ai_knowledge_skin("DOM-HOSPITAL", "医院挂号预约", "内科外科"),
            "hospital",
        )
        self.assertEqual(
            resolve_ai_knowledge_skin("DOM-FOOD", "高校食堂点餐", "档口堂食"),
            "food_canteen",
        )
        self.assertEqual(
            resolve_ai_knowledge_skin("DOM-FOOD", "奶茶点餐外卖", "门店自取"),
            "food",
        )
        # S-75～S-81：深皮 FAQ 不得落 generic / 错邻域口吻
        self.assertEqual(
            resolve_ai_knowledge_skin(
                "DOM-EVENT", "防返贫数字化辅助系统", "帮扶户建档走访上报"
            ),
            "event_household",
        )
        self.assertEqual(
            resolve_ai_knowledge_skin(
                "DOM-ACTIVITY", "安顺学院献血管理系统", "献血场次报名"
            ),
            "activity_blood",
        )
        self.assertEqual(
            resolve_ai_knowledge_skin(
                "DOM-ACTIVITY", "校园防暴恐培训管理系统", "防暴恐培训报名"
            ),
            "activity_security",
        )
        self.assertEqual(
            resolve_ai_knowledge_skin(
                "DOM-ACTIVITY", "歌剧院票务报名管理系统", "歌剧院领票"
            ),
            "activity_ticket",
        )
        self.assertEqual(
            resolve_ai_knowledge_skin(
                "DOM-PROCURE", "外文学术期刊遴选服务平台", "期刊遴选荐购"
            ),
            "procure_journal",
        )
        self.assertEqual(
            resolve_ai_knowledge_skin(
                "DOM-LOST", "航班行李挂失认领管理系统", "行李挂失认领"
            ),
            "lost_baggage",
        )
        self.assertEqual(
            resolve_ai_knowledge_skin(
                "DOM-RECRUIT", "威客任务接单管理系统", "威客任务投递初筛"
            ),
            "recruit_witkey",
        )

    def test_s75_s81_faq_categories_match_sql_seed(self) -> None:
        """FAQ 分类名须与深皮 SQL category.name 同字。"""
        from app.bake.engine_sql import domain_sql
        from app.bake.features.ai_assistant import build_ai_knowledge_seed_sql

        cases = [
            (
                "DOM-EVENT",
                "防返贫数字化辅助系统",
                "帮扶户建档走访上报",
                ("监测户", "边缘易致贫", "突发严重困难"),
            ),
            (
                "DOM-ACTIVITY",
                "安顺学院献血管理系统",
                "献血场次报名",
                ("献血场次", "校园开放日", "其它公益"),
            ),
            (
                "DOM-ACTIVITY",
                "校园防暴恐培训管理系统",
                "防暴恐培训报名",
                ("防暴恐培训", "应急疏散", "安全常识"),
            ),
            (
                "DOM-ACTIVITY",
                "歌剧院票务报名管理系统",
                "歌剧院领票",
                ("歌剧院场次", "演出场次", "景区场次"),
            ),
            (
                "DOM-PROCURE",
                "外文学术期刊遴选服务平台",
                "期刊遴选荐购",
                ("理工外刊", "社科外刊", "综合索引"),
            ),
            (
                "DOM-LOST",
                "航班行李挂失认领管理系统",
                "行李挂失认领",
                ("托运行李", "登机箱", "随身物品"),
            ),
            (
                "DOM-RECRUIT",
                "威客任务接单管理系统",
                "威客任务投递初筛",
                ("设计类", "开发类", "文案类"),
            ),
        ]
        for domain, title, body, cats in cases:
            with self.subTest(title=title):
                sql_seed = domain_sql(domain, "t_ai", title=title, proposal_text=body)
                faq = build_ai_knowledge_seed_sql(
                    domain, title, body, sql_context=sql_seed
                )
                for cat in cats:
                    self.assertIn(cat, sql_seed, f"sql missing {cat}")
                    self.assertIn(cat, faq, f"faq missing {cat}")
                self.assertNotIn("水果", faq)
                self.assertNotIn("社团活动怎么报名", faq)

    def test_faq_aligns_pack_cats_to_sql_lookup_names(self) -> None:
        """皮模板分类名若与 SQL lookup 不一致 → bake 时改写成同字。"""
        from app.bake.features.ai_assistant import (
            align_faq_rows_to_lookup_names,
            build_ai_knowledge_seed_sql,
            extract_lookup_names_from_sql,
        )

        sql = (
            "INSERT IGNORE INTO category (id, name) VALUES "
            "(1, '甲类'), (2, '乙类'), (3, '丙类');\n"
        )
        self.assertEqual(extract_lookup_names_from_sql(sql), ["甲类", "乙类", "丙类"])
        # 报修族 lookup 表也要抽到
        repair_sql = (
            "INSERT IGNORE INTO repair_type (id, name, sort_no) VALUES "
            "(1, '水电', 1), (2, '门窗', 2), (3, '家具', 3);"
        )
        self.assertEqual(
            extract_lookup_names_from_sql(repair_sql), ["水电", "门窗", "家具"]
        )
        # VALUES 换行（IT fault_type / 物业 ticket_type 真种子形态）不得漏抽
        multiline = (
            "INSERT IGNORE INTO fault_type (id, name, sort_no) VALUES\n"
            "(1, '内网', 1), (2, '终端', 2), (3, '打印机', 3);\n"
        )
        self.assertEqual(
            extract_lookup_names_from_sql(multiline), ["内网", "终端", "打印机"]
        )
        rows = [
            ("旧一", "旧一怎么办", "请选「旧一」提交", "旧一,办理", 12),
            ("旧二", "旧二须知", "「旧二」请看说明", "旧二,须知", 10),
            ("旧三", "旧三说明", "了解「旧三」", "旧三", 8),
            ("旧一", "如何查看进度", "看进度", "进度", 6),
        ]
        aligned = align_faq_rows_to_lookup_names(rows, ["甲类", "乙类", "丙类"])
        self.assertEqual([r[0] for r in aligned], ["甲类", "乙类", "丙类", "甲类"])
        self.assertIn("甲类怎么办", aligned[0][1])
        self.assertIn("「乙类」", aligned[1][2])

        faq = build_ai_knowledge_seed_sql(
            "DOM-ATTEND",
            "请假系统",
            "事假病假",
            sql_context=sql,
        )
        self.assertIn("'甲类'", faq)
        self.assertIn("'乙类'", faq)
        self.assertNotIn("'事假类'", faq)

        dorm_faq = build_ai_knowledge_seed_sql(
            "DOM-DORM",
            "宿舍报修",
            "水电门窗",
            sql_context=repair_sql,
        )
        self.assertIn("'水电'", dorm_faq)
        self.assertIn("'门窗'", dorm_faq)

    def test_farm_faq_pack_titles(self) -> None:
        from app.bake.features.ai_assistant import build_ai_knowledge_seed_sql

        sql = build_ai_knowledge_seed_sql("DOM-SHOP", _FARM_TITLE, _FARM_BODY)
        self.assertIn("如何挑选新鲜农产品", sql)
        self.assertIn("水果保存与食用建议", sql)
        self.assertNotIn("热销", sql)

    def test_all_ai_skins_have_conversational_hot_titles(self) -> None:
        """各皮热门应为口语问句，禁止千篇一律「选购说明」。"""
        from app.bake.features.ai_assistant import _AI_SEED_PACKS, _shop_pack

        expected_snippets = {
            "shop_farm": "如何挑选新鲜农产品",
            "shop_retail": "热销商品怎么选",
            "shop_campus": "教材教辅怎么买",
            "shop_print": "黑白打印怎么下单",
            "shop_flowers": "花束怎么选购",
            "shop_errand": "代买餐饮怎么下单",
            "shop_points": "积分怎么兑换文创",
            "library_book": "逾期与催还怎么办",
            "library_archive": "学籍档案如何查阅",
            "library_drift": "漂流文学书怎么取阅",
            "dorm": "水电报修怎么提交",
            "property": "物业水电报修怎么提",
            "it": "上不了网怎么报",
            "fitout": "室内装修怎么备案",
            "attend": "如何提交事假",
            "food": "如何点套餐",
            "food_canteen": "食堂套餐怎么点",
            "doclib": "如何下载制度文件",
            "hotel": "标准间怎么预订",
            "tour": "周边游怎么报名",
            "carrent": "经济型怎么租",
            "listing": "整租房源怎么看",
            "cinema": "普通厅怎么选座",
            "hospital": "内科号怎么约",
            "salon": "剪发怎么预约",
            "meeting": "小型会议室怎么约",
            "parking": "地上车位怎么约",
            "activity": "社团活动怎么报名",
            "activity_blood": "献血场次怎么报名",
            "activity_ticket": "歌剧院怎么领票",
            "activity_cert": "证书报考怎么报名",
            "activity_security": "防暴恐培训怎么报名",
            "activity_camp": "研学怎么报名",
            "equip": "仪器怎么借",
            "crm": "重点客户怎么跟进",
            "recruit": "技术岗怎么投递",
            "recruit_witkey": "设计类任务怎么接",
            "parcel": "普通件怎么取",
            "media": "电影怎么点播",
            "music": "流行歌怎么试听",
            "blog": "技术文章怎么发",
            "forum": "学习帖怎么发",
            "bed": "四人间怎么申请",
            "event": "传染病线索怎么上报",
            "event_household": "监测户怎么走访上报",
            "lost": "证件遗失怎么登记",
            "lost_baggage": "托运行李挂失怎么认领",
            "lost_adopt": "怎么申请领养猫",
            "lost_donate": "捐赠物资怎么认领",
            "procure": "办公用品怎么申购",
            "procure_journal": "理工外刊怎么荐购",
            # 原落 generic 的具名域（抽检若干 + 全量另测）
            "intern": "岗位周报怎么写",
            "exam": "期末考试怎么参加",
            "survey": "学风问卷怎么填",
            "checkin": "正常归寝怎么签到",
            "vote": "评优选先怎么投票",
            "generic": "AI 助手能做什么",
        }
        for skin, snippet in expected_snippets.items():
            rows = _AI_SEED_PACKS[skin]
            self.assertEqual(len(rows), 4, skin)
            titles = " ".join(r[1] for r in rows)
            self.assertIn(snippet, titles, skin)
            self.assertNotIn("选购说明", titles, skin)
        # 动态皮与静态表一致
        for kind in ("farm", "retail", "campus", "print", "flowers", "errand", "points"):
            self.assertEqual(_shop_pack(kind), _AI_SEED_PACKS[f"shop_{kind}"])

    def test_all_named_domains_have_dedicated_faq_skin(self) -> None:
        """具名域禁止偏科落 generic；仅 DOM-GENERIC 用通用四条。"""
        from app.bake.domains import DOMAIN_CAPABILITIES
        from app.bake.features.ai_assistant import (
            _AI_SEED_PACKS,
            resolve_ai_knowledge_skin,
        )

        for domain in sorted(DOMAIN_CAPABILITIES):
            with self.subTest(domain=domain):
                skin = resolve_ai_knowledge_skin(domain, "测试系统", "业务办理与信息管理")
                self.assertIn(skin, _AI_SEED_PACKS, domain)
                self.assertEqual(len(_AI_SEED_PACKS[skin]), 4, skin)
                if domain == "DOM-GENERIC":
                    self.assertEqual(skin, "generic")
                else:
                    self.assertNotEqual(
                        skin,
                        "generic",
                        f"{domain} 不应再落 generic（工厂孩子一视同仁）",
                    )

    def test_attach_accept_force_on(self) -> None:
        spec = build_spec(
            title=_FARM_TITLE,
            archetype="ARCH-CRUD",
            domain="DOM-SHOP",
            theme="gen-ink",
            llm_enabled=False,
            match_mode="recommended",
            confidence=0.9,
            ai_assistant=True,
            proposal={"excerpt": _FARM_BODY},
        )
        out = attach_accept(spec, _FARM_BODY)
        self.assertIn("ai_assistant", out.get("capabilities") or [])
        labels = (out.get("schema") or {}).get("labels") or {}
        self.assertIn("导购", labels.get("aiAssistantPageTitle", ""))
        gate = out.get("gate") or {}
        files = " ".join(gate.get("files") or [])
        self.assertIn("DeepSeekClient.java", files)
        self.assertIn("AiAssistantController.java", files)


class TestAiAssistantBake(unittest.TestCase):
    def test_ai_off_no_sql_seed_no_readme_faq(self) -> None:
        ws = _bake(ai_assistant=False, pid="gf-ut-ai-off")
        sql_path = ws / "sql" / "schema.sql"
        sql = sql_path.read_text(encoding="utf-8") if sql_path.is_file() else ""
        spec = json.loads((ws / "spec.json").read_text(encoding="utf-8"))
        self.assertNotIn("ai_assistant", spec.get("capabilities") or [])
        self.assertNotIn("sys_ai_knowledge", sql)
        readme = (ws / "README.md").read_text(encoding="utf-8")
        self.assertNotIn("DeepSeek", readme)

    def test_ai_on_sql_and_files_and_readme(self) -> None:
        ws = _bake(
            ai_assistant=True,
            pid="gf-ut-ai-on",
            title=_FARM_TITLE,
            domain="DOM-SHOP",
            proposal_excerpt=_FARM_BODY,
        )
        self.assertTrue(any((ws / "backend").rglob("DeepSeekClient.java")))
        pom = (ws / "backend" / "pom.xml").read_text(encoding="utf-8")
        self.assertIn("spring-ai-deepseek", pom)
        self.assertIn("spring-ai-bom", pom)
        ds_txt = next((ws / "backend").rglob("DeepSeekClient.java")).read_text(encoding="utf-8")
        self.assertIn("DeepSeekChatModel", ds_txt)
        self.assertIn("springframework.ai", ds_txt)
        self.assertTrue(any((ws / "backend").rglob("AiBizContext.java")))
        biz_txt = next((ws / "backend").rglob("AiBizContext.java")).read_text(encoding="utf-8")
        # 商城有订单/货架；无 ticket_flow → prune 裁掉 TicketStore（勿再钉字面量）
        self.assertIn("OrderStore", biz_txt)
        self.assertIn("ArchiveStore", biz_txt)
        self.assertNotIn("TicketStore", biz_txt)
        self.assertTrue(any((ws / "backend").rglob("AiAssistantController.java")))
        self.assertTrue(any((ws / "frontend").rglob("AiAssistant.vue")))
        self.assertTrue(any((ws / "frontend").rglob("AiAssistantFloat.vue")))
        self.assertTrue(
            "AiAssistantFloat"
            in (ws / "frontend" / "src" / "layouts" / "PortalLayout.vue").read_text(
                encoding="utf-8"
            )
        )
        sql_path = ws / "sql" / "schema.sql"
        self.assertTrue(sql_path.is_file(), "缺少 sql/schema.sql")
        sql = sql_path.read_text(encoding="utf-8")
        self.assertIn("sys_ai_knowledge", sql)
        self.assertIn("sys_ai_message", sql)
        self.assertIn("sys_ai_feedback", sql)
        self.assertIn("INSERT INTO sys_ai_knowledge", sql)
        self.assertIn("水果", sql)
        self.assertIn("蔬菜", sql)
        self.assertIn("粮油", sql)
        self.assertIn("INSERT IGNORE INTO category (id, name) VALUES (1, '水果'), (2, '蔬菜'), (3, '粮油')", sql)
        self.assertIn("如何挑选新鲜农产品", sql)
        self.assertIn("水果保存与食用建议", sql)
        self.assertIn("叶菜与根茎保存常识", sql)
        self.assertIn("粮油储存要点", sql)
        self.assertIn("红富士苹果", sql)
        self.assertNotIn("毕设", sql)
        self.assertNotIn("毕业设计", sql)
        self.assertNotIn("演示环境", sql)
        readme = (ws / "README.md").read_text(encoding="utf-8")
        self.assertIn("DeepSeek", readme)
        self.assertIn("Spring AI", readme)
        self.assertIn("DEEPSEEK_API_KEY", readme)
        self.assertIn("悬浮", readme)
        spec = json.loads((ws / "spec.json").read_text(encoding="utf-8"))
        self.assertIn("ai_assistant", spec.get("capabilities") or [])
        menus = ((spec.get("schema") or {}).get("menus") or {}).get("user") or []
        self.assertTrue(any(m.get("key") == "ai_assistant" for m in menus))

    def test_ai_on_library_seed_not_farm(self) -> None:
        ws = _bake(
            ai_assistant=True,
            pid="gf-ut-ai-lib",
            title="智能图书管理系统",
            domain="DOM-LIBRARY",
            proposal_excerpt="AI馆员问答与借阅管理",
        )
        sql = (ws / "sql" / "schema.sql").read_text(encoding="utf-8")
        self.assertIn("借阅", sql)
        self.assertIn("计算机", sql)
        self.assertNotIn("粮油", sql)
        # 图书有 ticket_flow：AiBizContext 须保留 TicketStore（对照商城 prune）
        biz = next((ws / "backend").rglob("AiBizContext.java")).read_text(encoding="utf-8")
        self.assertIn("TicketStore", biz)
        self.assertIn("ArchiveStore", biz)

    def test_ai_reply_polish_default_off_decoupled_from_key(self) -> None:
        """交付默认关润色；有 Key 也不改写；须独立开关（禁靠拔 Key）。"""
        from pathlib import Path as _P

        from app.bake.engine_bake import _patch_thesis_yml

        root = _P(__file__).resolve().parents[2]
        yml = (
            root
            / "skeletons"
            / "baseline"
            / "backend"
            / "src"
            / "main"
            / "resources"
            / "application.yml"
        ).read_text(encoding="utf-8")
        self.assertIn("ai-reply-polish:", yml)
        self.assertRegex(yml, r"ai-reply-polish:\s*\$\{AI_REPLY_POLISH:false\}")

        stores = [
            root
            / "skeletons"
            / "baseline"
            / "backend"
            / "src"
            / "main"
            / "java"
            / "com"
            / "thesis"
            / "service"
            / "AiAssistantStore.java",
            root
            / "skeletons"
            / "overlays"
            / "persistence-mybatis"
            / "backend"
            / "src"
            / "main"
            / "java"
            / "com"
            / "thesis"
            / "service"
            / "AiAssistantStore.java",
            root
            / "skeletons"
            / "overlays"
            / "persistence-jpa"
            / "backend"
            / "src"
            / "main"
            / "java"
            / "com"
            / "thesis"
            / "service"
            / "AiAssistantStore.java",
        ]
        for path in stores:
            txt = path.read_text(encoding="utf-8")
            self.assertIn("REPLY_NO_FAQ", txt, path.name)
            self.assertIn("isReplyPolishEnabled", txt, path.name)
            self.assertIn("DeepSeekClient.configured() && isReplyPolishEnabled()", txt, path.name)
            self.assertIn('faq.get("content")', txt, path.name)

        on_yml = _patch_thesis_yml(
            "thesis:\n  title: x\n",
            "DOM-SHOP",
            {"ai_assistant": True, "capabilities": ["ai_assistant"], "title": "农产"},
        )
        self.assertRegex(on_yml, r"ai-reply-polish:\s*false")
        off_yml = _patch_thesis_yml(
            "thesis:\n  title: x\n",
            "DOM-SHOP",
            {"ai_assistant": False, "capabilities": [], "title": "农产"},
        )
        self.assertNotIn("ai-reply-polish", off_yml)


if __name__ == "__main__":
    unittest.main()
