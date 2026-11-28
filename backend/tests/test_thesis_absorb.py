"""终稿吸收：分桶抽取、对比句、同材同果、弱抽告警。"""

from __future__ import annotations

import unittest
from pathlib import Path

from app.services.thesis_absorb_extract import (
    EXTRACTOR_VERSION,
    apply_table_module_cross_check,
    build_feed_markdown,
    build_opening_draft,
    build_thesis_excerpt,
    content_sha256,
    excerpt_looks_junk,
    extract_tech_stack_lines,
    extract_thesis_proposal,
    gather_cjk_abstract,
    looks_half_cut,
    table_module_cross_warnings,
)


SAMPLE = """
第一章 绪论
本文主要工作包括图书借阅模块、读者管理模块、逾期罚款模块。
现有系统支持协同过滤推荐，本系统不做推荐。
传统系统具有人脸打卡功能。

第三章 需求分析
系统角色包括管理员与读者。
本系统需要实现图书借阅、读者管理等业务。

第四章 系统设计
系统分为管理端与读者端。
管理端包含图书借阅管理、读者管理、逾期罚款管理、图书检索管理。
图书借阅模块负责借还流程。

第五章 系统实现
借阅流程：读者检索图书后提交借阅申请，管理员审核。
逾期罚款模块按天数计算费用。

第六章 系统测试
测试了借阅申请与逾期罚款主路径。
"""

THIN = """
第一章 绪论
随着信息技术发展，管理系统越来越重要。

第三章 相关技术
介绍了 Spring 与 Vue。
"""

CONTRAST = """
第一章 绪论
本文主要工作是实验室预约模块。
现有系统支持推荐算法与人脸识别。
本文不包含支付功能。

第三章 需求分析
系统角色包括管理员与预约用户。

第四章 系统设计
管理端包含实验室预约管理、时段管理。
"""


class ThesisAbsorbExtractTests(unittest.TestCase):
    def test_extractor_version_set(self) -> None:
        self.assertTrue(EXTRACTOR_VERSION)

    def test_excerpt_prefers_chinese_not_raw_dump(self) -> None:
        """短摘录可读中文；禁止整篇 raw 硬截与英文粘连墙。"""
        r = extract_thesis_proposal(SAMPLE)
        ex = r["proposal"].get("excerpt") or ""
        self.assertTrue(ex, "应有中文短摘")
        self.assertLessEqual(len(ex), 480)
        self.assertFalse(excerpt_looks_junk(ex), ex)
        self.assertIn("借阅", ex)
        # 不得把整篇粘连原文塞进 excerpt
        self.assertNotIn("第六章 系统测试", ex)

    def test_english_glued_abstract_not_excerpt(self) -> None:
        """英文 Abstract 粘词（roomcollection）不得进短摘录；有设计中文则用中文。"""
        text = """
Abstract
The hotel system mainly provides users with the function of booking hotels.
User identities include registration, login, room viewing, room reservation,
order viewing, check-out, room renewal, roomcollection, commentPosting,
newsviewing, andinformationmodification. The administrator identity includes
room information management, check-in management, renewal management.

摘要
酒店预订系统面向住客与管理员，提供客房浏览与预订等业务。

第一章 绪论
本文主要工作包括客房预订模块、续住管理模块、评价管理模块。

第四章 系统设计
管理端包含客房信息管理、入住管理、续住管理、评价管理、用户管理。
用户端包含客房浏览、客房预订、订单查看、续住申请。

第五章 系统实现
客房预订模块负责下单与支付。
"""
        r = extract_thesis_proposal(text)
        ex = r["proposal"].get("excerpt") or ""
        self.assertTrue(ex)
        self.assertFalse(excerpt_looks_junk(ex), ex)
        self.assertNotIn("roomcollection", ex)
        self.assertNotIn("commentPosting", ex)
        self.assertNotIn("andinformationmodification", ex)
        self.assertRegex(ex, r"[\u4e00-\u9fff]")

    def test_finalize_drops_shell_entities_and_rbac_features(self) -> None:
        """换题同形：壳实体/RBAC 功能不得进三栏主路径，减少人手删噪。"""
        from app.services.thesis_absorb_extract import (
            finalize_draft_entities,
            finalize_draft_features,
            finalize_feature_lines,
            normalize_llm_drafts,
            clean_thesis_title,
        )

        ents = finalize_draft_entities(
            ["订单", "菜单", "配置文件", "系统日志", "信息", "权限", "角色", "用户"]
        )
        self.assertIn("订单", ents)
        self.assertIn("用户", ents)
        for bad in ("菜单", "配置文件", "系统日志", "信息", "权限", "角色"):
            self.assertNotIn(bad, ents, ents)

        # 设计采矿可留个人中心（后置）；三栏草稿丢掉 RBAC/端壳
        mined = finalize_feature_lines(
            [
                "个人中心管理",
                "借阅管理",
                "读者管理",
                "轮播图管理",
            ]
        )
        self.assertIn("借阅管理", mined)
        self.assertIn("个人中心管理", mined)
        self.assertGreater(mined.index("个人中心管理"), mined.index("借阅管理"))

        feats = finalize_draft_features(
            [
                "个人中心管理",
                "角色管理",
                "权限管理",
                "日志管理",
                "借阅管理",
                "读者管理",
                "轮播图管理",
            ]
        )
        self.assertIn("借阅管理", feats)
        self.assertIn("读者管理", feats)
        for bad in ("个人中心管理", "角色管理", "权限管理", "日志管理"):
            self.assertNotIn(bad, feats, feats)
        if "轮播图管理" in feats:
            self.assertGreater(feats.index("轮播图管理"), feats.index("借阅管理"))

        norm = normalize_llm_drafts(
            ["管理员", "读者"],
            ["菜单", "系统日志", "图书"],
            ["个人中心管理", "借阅管理", "图书管理"],
            entity_hints=["图书表", "读者表"],
            table_captions=["表4.1 图书表"],
        )
        self.assertIn("图书", norm["draft_entities"])
        self.assertNotIn("菜单", norm["draft_entities"])
        self.assertIn("借阅管理", norm["draft_features"])
        self.assertNotIn("个人中心管理", norm["draft_features"])
        self.assertEqual(clean_thesis_title("论文题目：某某系统的设计与实现"), "某某系统的设计与实现")

    def test_excerpt_rejects_design_blueprint_dump(self) -> None:
        from app.services.thesis_absorb_extract import (
            build_thesis_excerpt,
            excerpt_looks_junk,
        )

        dump = (
            "主要对系统架构、模块划分、数据库逻辑设计、安全性、可扩展性等进行说明，"
            "为系统的实现提供蓝图。更新和分类管理，在业务支撑上可以实现积分奖品和兑换。"
        )
        self.assertTrue(excerpt_looks_junk(dump))
        ex = build_thesis_excerpt(
            background=dump,
            abstract_lines=[dump],
            design_lines=[],
            feature_lines=["预约管理", "积分管理"],
        )
        self.assertFalse(excerpt_looks_junk(ex), ex)
        self.assertNotIn("提供蓝图", ex)

    def test_build_thesis_excerpt_empty_when_only_english_junk(self) -> None:
        junk = (
            "The hotel system mainly provides users with the function of booking hotels. "
            "roomcollection commentPosting newsviewing andinformationmodification"
        )
        self.assertTrue(excerpt_looks_junk(junk))
        self.assertEqual(
            build_thesis_excerpt(
                background=junk,
                abstract_lines=[junk],
                design_lines=[],
                feature_lines=[],
            ),
            "",
        )

    def test_excerpt_joins_half_cut_abstract_lines(self) -> None:
        """摘要折行半截（……的服 / 务。……）必须拼成完整句，禁止首行半截出栏。"""
        half = "青竹小轩酒店管理系统旨在为外出游玩的旅行人员提供高效便捷的酒店预定的服"
        self.assertTrue(looks_half_cut(half))
        joined = gather_cjk_abstract(
            [
                half,
                "务。用户可以注册登录、浏览客房并完成预订。",
            ]
        )
        self.assertFalse(looks_half_cut(joined), joined)
        self.assertIn("服务", joined)
        self.assertTrue(joined.endswith("。"), joined)

        text = f"""
摘要
{half}
务。用户可以注册登录、浏览客房并完成预订。

第一章 绪论
本文主要工作包括客房预订模块、续住管理模块。

第四章 系统设计
管理端包含客房信息管理、入住管理、续住管理。
"""
        r = extract_thesis_proposal(text)
        ex = r["proposal"].get("excerpt") or ""
        self.assertTrue(ex, "应有完整短摘")
        self.assertFalse(looks_half_cut(ex), ex)
        self.assertNotEqual(ex, half)
        self.assertIn("服务", ex)
        bg = r["proposal"].get("background") or ""
        if bg:
            self.assertFalse(looks_half_cut(bg), bg)

    def test_buckets_pull_features(self) -> None:
        r = extract_thesis_proposal(SAMPLE)
        feats = r["proposal"]["feature_lines"]
        self.assertGreaterEqual(len(feats), 3)
        blob = " ".join(feats)
        self.assertIn("借阅", blob)
        self.assertEqual(r["proposal"]["hits"], [])
        self.assertFalse(r["thin_features"])
        self.assertTrue(r["ok_to_feed"])

    def test_contrast_not_in_features(self) -> None:
        r = extract_thesis_proposal(CONTRAST)
        blob = " ".join(r["proposal"]["feature_lines"])
        self.assertNotIn("推荐", blob)
        self.assertNotIn("人脸", blob)
        # 不做支付 → out_scope 或至少不在 feature
        self.assertNotIn("支付", blob)
        outs = " ".join(r["proposal"].get("out_scope_lines") or [])
        self.assertTrue("支付" in outs or "支付" not in blob)

    def test_test_case_steps_not_out_scope(self) -> None:
        """测试是实现验货：用例步骤不得撕成「不做」碎片。"""
        sample = """
第一章 绪论
本文主要工作包括材料入库模块、订单管理模块。

第三章 需求分析
系统角色包括管理员与用户。

第四章 系统设计
管理端包含材料入库管理、订单管理、材料类型管理。

第五章 系统实现
材料入库模块完成入库登记。

第六章 系统测试
测试用例 TC-01 材料入库
在材料入库界面，选择一种材料，填写合法的入库数量，点击“提交”
材料：“环保材料再生铁”，入库数量为 10
预期结果：与预期相同，系统阻止非法数量
实际结果：通过
"""
        r = extract_thesis_proposal(sample)
        outs = r["proposal"].get("out_scope_lines") or []
        outs_blob = " ".join(outs)
        for junk in (
            "阻止",
            "与预期",
            "入库数量，点击",
            "环保材料再生",
            "选择一种材",
            "填写合法的",
        ):
            self.assertNotIn(junk, outs_blob, outs)
        feats_blob = " ".join(r["proposal"].get("feature_lines") or [])
        self.assertIn("材料入库", feats_blob)
        # 步骤正文也不得垫进功能主清单
        self.assertNotIn("点击", feats_blob)
        self.assertNotIn("与预期", feats_blob)

    def test_same_material_same_result(self) -> None:
        a = extract_thesis_proposal(SAMPLE)
        b = extract_thesis_proposal(SAMPLE)
        self.assertEqual(a["proposal"]["feature_lines"], b["proposal"]["feature_lines"])
        self.assertEqual(a["proposal"]["sections"], b["proposal"]["sections"])
        self.assertEqual(a["extractor_version"], b["extractor_version"])
        self.assertEqual(content_sha256(SAMPLE), content_sha256(SAMPLE))

    def test_byte_change_allows_diff(self) -> None:
        a = extract_thesis_proposal(SAMPLE)
        b = extract_thesis_proposal(SAMPLE + "\n额外图书续借模块\n")
        # 哈希不同
        self.assertNotEqual(content_sha256(SAMPLE), content_sha256(SAMPLE + "x"))
        # 结构至少可运行
        self.assertIsInstance(a["proposal"]["feature_lines"], list)
        self.assertIsInstance(b["proposal"]["feature_lines"], list)

    def test_thin_warning(self) -> None:
        r = extract_thesis_proposal(THIN)
        self.assertTrue(r["thin_features"])
        self.assertFalse(r["ok_to_feed"])
        self.assertEqual(r["extract_warning"], "thin_features")
        # thin 只走旗标，不进 warnings（UI 单条提示，避免双黄条）
        self.assertFalse(any("偏少" in w for w in r["warnings"]))

    def test_tech_stack_from_related_section(self) -> None:
        """相关技术章点名 → tech_stack_lines；未点名不得脑补默认栈。"""
        thin = extract_thesis_proposal(THIN)
        stack = thin["proposal"]["tech_stack_lines"]
        self.assertIn("Spring", stack)
        self.assertIn("Vue", stack)

        bare = extract_thesis_proposal(SAMPLE)
        self.assertEqual(bare["proposal"]["tech_stack_lines"], [])

    def test_tech_stack_prefers_specific_labels(self) -> None:
        doc = """
摘要
本系统采用 Spring Boot、MyBatis 与 Vue 3、Element Plus，数据库 MySQL。

第一章 绪论
研究意义略。

第二章 相关技术
后端 Spring Boot + MyBatis，前端 Vue 3 与 Element Plus，持久化不用 JdbcTemplate。

第三章 需求分析
系统角色包括管理员与用户。

第四章 系统设计
管理端包含用户管理、订单管理。
"""
        r = extract_thesis_proposal(doc)
        stack = r["proposal"]["tech_stack_lines"]
        self.assertIn("Spring Boot", stack)
        self.assertNotIn("Spring", stack)
        self.assertIn("Vue 3", stack)
        self.assertNotIn("Vue", stack)
        self.assertIn("MyBatis", stack)
        self.assertIn("Element Plus", stack)
        self.assertIn("MySQL", stack)
        self.assertNotIn("JdbcTemplate", stack)  # 「不用」否定点名

    def test_extract_tech_stack_lines_unit(self) -> None:
        self.assertEqual(extract_tech_stack_lines(""), [])
        self.assertEqual(extract_tech_stack_lines("无技术描述"), [])
        self.assertEqual(
            extract_tech_stack_lines("采用 JavaScript 与 TypeScript"),
            ["TypeScript"],
        )
        # PDF 软折行：Vue\n3 → Vue 3
        self.assertIn(
            "Vue 3",
            extract_tech_stack_lines("前端采用 Vue\n3 与 Element Plus"),
        )

    def test_glued_pdf_text_recovers_modules(self) -> None:
        """PDF 粘连无换行时，仍应从设计章扫出「××管理/模块」。"""
        glued = (
            "第一章绪论本文主要工作包括订单管理模块、客户管理模块与库存管理模块。"
            "第三章需求分析系统角色包括管理员与客户。"
            "第四章系统设计管理端包含订单管理、客户管理、库存管理、销售统计管理。"
            "第五章系统实现订单管理模块负责下单与发货。"
        )
        r = extract_thesis_proposal(glued)
        feats = r["proposal"]["feature_lines"]
        blob = " ".join(feats)
        self.assertGreaterEqual(len(feats), 3, feats)
        self.assertIn("订单管理", blob)
        self.assertIn("客户管理", blob)
        self.assertFalse(r["thin_features"])
        self.assertEqual(r["extractor_version"], EXTRACTOR_VERSION)

    def test_glued_pdf_multi_domain_not_title_bound(self) -> None:
        """粘连正文按形态抽，功能主矿在设计章；不绑某一题名/钢材域。"""
        cases = {
            "借阅": (
                "第一章绪论本文完成图书借阅模块读者管理模块逾期罚款模块。"
                "第三章需求分析角色包括管理员与读者。"
                "第四章系统设计包含图书借阅管理、读者管理、图书检索管理。"
                "第五章系统实现图书借阅模块负责借还。",
                ("借阅", "读者"),
            ),
            "报修": (
                "第一章绪论本系统实现报修申请模块派单管理模块评价反馈模块。"
                "第三章需求分析角色包括报修人与受理人。"
                "第四章系统设计包含报修申请管理、派单管理、工单跟踪管理。"
                "第五章系统实现报修申请模块支持拍照上传。",
                ("报修", "派单"),
            ),
            "交易": (
                "第 1 章 绪论主要工作含商品管理模块购物车模块订单管理模块。"
                "第 3 章 需求分析角色包括买家与店员。"
                "第 4 章 系统设计包含商品管理、订单管理、支付对接管理。"
                "第 5 章 系统实现订单管理模块覆盖下单发货。",
                ("商品", "订单"),
            ),
            "预约": (
                "第一章绪论完成场馆预约模块时段管理模块器材借用模块。"
                "第三章需求分析角色包括预约人与接待。"
                "第四章系统设计包含场馆预约管理、时段管理、消息通知管理。"
                "第五章系统实现场馆预约模块支持改期。",
                ("预约", "时段"),
            ),
        }
        for label, (text, needles) in cases.items():
            with self.subTest(label=label):
                r = extract_thesis_proposal(text)
                feats = r["proposal"]["feature_lines"]
                blob = " ".join(feats)
                self.assertGreaterEqual(len(feats), 3, feats)
                self.assertFalse(r["thin_features"], feats)
                for n in needles:
                    self.assertIn(n, blob, feats)

    def test_opening_style_without_design_is_thin(self) -> None:
        """无设计章 P1 → 弱抽；禁止用开题清单腔顶替终稿主矿。"""
        raw = """题目：基于 Spring Boot 的图书借阅管理系统
一、研究背景
高校图书馆借阅业务需要信息化管理。
二、主要功能
1. 读者注册与登录（含验证码）
2. 图书检索与详情
3. 借阅申请与管理员审核
4. 归还与逾期处理
5. 公告管理
三、非本期范围
人脸识别进馆、协同过滤推荐算法不在本期实现。
"""
        glued = " ".join(raw.split())
        r = extract_thesis_proposal(glued)
        self.assertTrue(r["thin_features"])
        self.assertFalse(r["ok_to_feed"])

    def test_pdf_spaced_glyphs_still_bucket(self) -> None:
        """pypdf 常把「绪论」抽成「绪 论」——应捏合后仍能分桶采矿。"""
        spaced = """
第 1 章 绪 论
本 文 主 要 工 作 包 括 座 位 预 约 模 块 、 签 到 管 理 模 块 、 违 规 处 理 模 块 。
第 3 章 需 求 分 析
角 色 包 括 管 理 员 与 读 者 。
第 4 章 系 统 设 计
管 理 端 包 含 座 位 预 约 管 理 、 签 到 管 理 、 违 规 处 理 管 理 、 消 息 通 知 管 理 。
第 5 章 系 统 实 现
座 位 预 约 模 块 负 责 占 座 与 释 放 。
"""
        r = extract_thesis_proposal(spaced)
        feats = r["proposal"]["feature_lines"]
        blob = " ".join(feats)
        self.assertGreaterEqual(len(feats), 3, feats)
        self.assertIn("预约", blob)
        self.assertFalse(r["thin_features"], feats)
        for f in feats:
            self.assertNotIn("、", f, f)

    def test_multi_layout_variants_not_school_bound(self) -> None:
        """常见版式变体都应能抽到要点（不绑某一校模板）；功能落在设计章。"""
        cases = {
            "tight_chapter": (
                "第一章 绪论\n本文完成借阅模块、读者模块、罚款模块。\n"
                "第三章 需求分析\n角色包括管理员与读者。\n"
                "第四章 系统设计\n包含借阅管理、读者管理、罚款管理、检索管理。\n"
                "第五章 系统实现\n借阅模块负责借还。",
                "借阅",
            ),
            "toc_dots": (
                "第1章 绪论..........1\n第3章 需求分析..........9\n"
                "第1章 绪论\n含预约模块、签到模块、审核模块。\n"
                "第3章 需求分析\n角色包括预约人。\n"
                "第4章 系统设计\n包含预约管理、签到管理、审核管理、通知管理。\n"
                "第5章 系统实现\n预约模块已完成。",
                "预约",
            ),
            "glued": (
                "第一章绪论本文完成报修申请模块派单管理模块评价反馈模块。"
                "第三章需求分析角色包括报修人。"
                "第四章系统设计包含报修申请管理、派单管理、工单跟踪管理。"
                "第五章系统实现报修申请模块支持上传。",
                "报修",
            ),
            "design_include": (
                "第四章 系统设计\n"
                "管理端包含图书借阅管理、读者管理、逾期罚款管理。\n"
                "第五章 系统实现\n借阅模块负责借还。",
                "借阅",
            ),
        }
        for label, (text, needle) in cases.items():
            with self.subTest(label=label):
                r = extract_thesis_proposal(text)
                feats = r["proposal"]["feature_lines"]
                self.assertGreaterEqual(len(feats), 3, feats)
                self.assertFalse(r["thin_features"], feats)
                self.assertIn(needle, " ".join(feats), feats)

    def test_feed_markdown_branches(self) -> None:
        prop = {"feature_lines": ["订单管理"], "out_scope_lines": [], "sections": []}
        for cov in ("unknown", "covered", "skin_gap", "domain_gap"):
            md = build_feed_markdown(record_id=1, coverage=cov, proposal=prop)
            self.assertIn("【给助手】", md)
            self.assertIn("【补齐建议】", md)
            self.assertIn("【禁令】", md)
            self.assertIn("订单管理", md)
            self.assertNotIn("匹配成功", md)
            self.assertIn("不是出包订单", md)

    def test_coalesce_broken_enum_lines(self) -> None:
        from app.services.thesis_absorb_extract import coalesce_broken_lines

        merged = coalesce_broken_lines(
            ["1.1", "研究背景", "1.2 课题研究的目的及意义", "1.3", "研究现状"]
        )
        self.assertEqual(
            merged,
            ["1.1 研究背景", "1.2 课题研究的目的及意义", "1.3 研究现状"],
        )

    def test_clean_feature_strips_toc_numbers(self) -> None:
        from app.services.thesis_absorb_extract import (
            clean_feature_label,
            finalize_feature_lines,
        )

        self.assertEqual(clean_feature_label("1.4厂商管理"), "厂商管理")
        self.assertEqual(clean_feature_label("1 管理员模块"), "管理员模块")
        self.assertIsNone(clean_feature_label("1.3操作可行性"))
        self.assertIsNone(clean_feature_label("2.5用例说明"))
        self.assertIsNone(clean_feature_label("4.3管理员删除厂商序列图"))
        self.assertIsNone(clean_feature_label("系统功能模块"))
        self.assertIsNone(clean_feature_label("2.4仓库管理员端功能设计"))
        cleaned = finalize_feature_lines(
            [
                "系统功能模块",
                "管理员模块",
                "1 管理员模块",
                "1.4厂商管理",
                "1.3操作可行性",
                "2.5用例说明",
                "厂商模块",
                "测试背景",
                "测试意义",
                "厂商登录",
            ]
        )
        self.assertEqual(cleaned, ["管理员模块", "厂商管理"])
        self.assertNotIn("测试背景", cleaned)
        self.assertNotIn("厂商模块", cleaned)  # 与厂商管理同词干，留管理

    def test_ver_int_and_outdated_clean(self) -> None:
        from app.services.thesis_absorb import _ver_int

        self.assertEqual(_ver_int("9"), 9)
        self.assertEqual(_ver_int("8"), 8)
        self.assertTrue(_ver_int("8") < _ver_int("9"))

    def test_resolved_drafts_drops_feature_stem_entities(self) -> None:
        """库内假实体草稿（功能掐词干）不得继续展示；重启后打开也要洗掉。"""
        from types import SimpleNamespace

        from app.services.thesis_absorb import _resolved_drafts

        row = SimpleNamespace(
            draft_roles=["用户", "厂商"],
            draft_entities=[
                "材料商城",
                "材料类型",
                "地址",
                "收藏",
                "购物车",
                "材料入库",
                "材料出库",
                "订单",
            ],
            draft_features=[
                "材料商城管理",
                "材料类型管理",
                "地址管理",
                "收藏管理",
                "购物车管理",
                "材料入库管理",
                "材料出库管理",
                "订单管理",
            ],
        )
        out = _resolved_drafts(
            row,
            {
                "feature_lines": list(row.draft_features),
                "entity_hints": ["用户信息", "订单信息"],
            },
        )
        self.assertEqual(out["draft_entities"], ["用户信息", "订单信息"])
        self.assertNotIn("材料商城", out["draft_entities"])
        self.assertNotIn("材料入库", out["draft_entities"])

    def test_extract_bundle_fast_path_keeps_prior_figures(self) -> None:
        """打开详情升版：文字重抽、图侧沿用，不依赖 PDF OCR。"""
        from app.services.thesis_absorb import _extract_bundle

        # 图侧沿用只断言「原样带回」；占位用形态尾巴，不从 SAMPLE 功能清单抄、不写死域业务名
        prior_label = "甲管理"
        prior = {
            "figure_labels": [prior_label],
            "structure_captions": ["图4.2 功能结构图"],
            "sections": [
                {
                    "heading": "图注与结构标签",
                    "lines": ["图4.2 功能结构图", prior_label],
                }
            ],
        }
        data = _extract_bundle(
            SAMPLE,
            with_figures=False,
            prior_proposal=prior,
            prior_has_figure=True,
        )
        prop = data["proposal_json"]
        self.assertIn(prior_label, prop.get("figure_labels") or [])
        self.assertTrue(data["has_figure_text"])
        heads = [
            s.get("heading")
            for s in (prop.get("sections") or [])
            if isinstance(s, dict)
        ]
        self.assertIn("图注与结构标签", heads)

    def test_suggest_drafts_from_features(self) -> None:
        from app.services.thesis_absorb_extract import suggest_drafts_from_proposal

        sug = suggest_drafts_from_proposal(
            {
                "feature_lines": [
                    "管理员模块",
                    "厂商模块",
                    "厂商管理",
                    "仓库管理员模块",
                    "仓库管理员管理",
                    "材料类型管理",
                    "材料入库管理",
                    "个人中心管理",
                    "测试背景",
                ],
                # 角色靠材料结构线索（module / role_hints），不靠行业私榜
                "module_hints": [
                    "管理员模块",
                    "厂商模块",
                    "仓库管理员模块",
                    "用户模块",
                ],
            }
        )
        self.assertEqual(
            sug["draft_roles"], ["管理员", "厂商", "仓库管理员", "用户"]
        )
        # 设计清单里的「××管理」保留；仅「××模块」端分区不进功能
        self.assertIn("材料类型管理", sug["draft_features"])
        self.assertIn("材料入库管理", sug["draft_features"])
        self.assertIn("厂商管理", sug["draft_features"])
        self.assertNotIn("管理员模块", sug["draft_features"])
        self.assertNotIn("用户模块", sug["draft_features"])
        self.assertNotIn("测试背景", sug["draft_features"])
        # 无库表题注 → 实体空；禁止掐「××管理」充数
        self.assertEqual(sug["draft_entities"], [])

        # 仅剩「××管理」、无模块线索 → 不得靠白名单猜角色；实体仍须表证据
        sug2 = suggest_drafts_from_proposal(
            {"feature_lines": ["厂商管理", "仓库管理员管理", "材料类型管理"]}
        )
        self.assertEqual(sug2["draft_roles"], [])
        self.assertEqual(sug2["draft_entities"], [])
        self.assertEqual(
            sug2["draft_features"],
            ["厂商管理", "仓库管理员管理", "材料类型管理"],
        )

        # 库表题注 → 实体；功能清单不得灌进实体
        sug2b = suggest_drafts_from_proposal(
            {
                "feature_lines": ["材料类型管理", "材料入库管理", "系统首页管理"],
                "entity_hints": ["材料类型", "订单信息"],
            }
        )
        self.assertEqual(sug2b["draft_entities"], ["材料类型", "订单信息"])
        self.assertNotIn("材料入库", sug2b["draft_entities"])
        self.assertNotIn("系统首页", sug2b["draft_entities"])

        # 角色名与库表名可并存：用户表既是角色也是实体
        sug2c = suggest_drafts_from_proposal(
            {
                "feature_lines": ["用户管理", "订单管理"],
                "role_hints": ["用户", "厂商", "管理员"],
                "entity_hints": ["用户", "厂商", "管理员", "订单"],
            }
        )
        self.assertEqual(sug2c["draft_roles"], ["用户", "厂商", "管理员"])
        for ent in ("用户", "厂商", "管理员", "订单"):
            self.assertIn(ent, sug2c["draft_entities"])

        # 换题：馆员/读者只靠模块词干；功能不抄端分区壳
        sug3 = suggest_drafts_from_proposal(
            {
                "feature_lines": ["馆员模块", "读者模块", "图书借阅管理"],
                "module_hints": ["馆员模块", "读者模块"],
            }
        )
        self.assertEqual(sug3["draft_roles"], ["馆员", "读者"])
        self.assertEqual(sug3["draft_entities"], [])
        self.assertEqual(sug3["draft_features"], ["图书借阅管理"])
        self.assertNotIn("馆员模块", sug3["draft_features"])

        # 列举句与开题同函数
        from app.services.proposal import extract_role_labels

        roles = extract_role_labels(
            "系统角色包括辅导员、班主任和学生三种角色。辅导员登录后可审核。"
        )
        self.assertIn("辅导员", roles)
        self.assertIn("班主任", roles)
        self.assertIn("学生", roles)

    def test_entities_from_db_tables_not_list_or_sequence(self) -> None:
        """实体只认库表名；叙述句/列表/所示/图侧词不得进。"""
        from app.services.thesis_absorb_extract import (
            extract_entity_labels_from_text,
            suggest_drafts_from_proposal,
        )

        junk = (
            "第4章 系统设计\n"
            "4.2 序列图\n"
            "页面向后端控制器发送查询厂商列表。\n"
            "厂商服务层访问数据库查询厂商列表。\n"
            "页面渲染厂商列表。\n"
            "表4.1所示\n"
            "4.3 数据库设计\n"
            "表 4.1 用户表yonghu\n"
            "表 4.2 厂商表changshang\n"
            "仓库管理员的信息存储在该表中。\n"
            "材料商城的信息存储在该表中。\n"
            "材料类型的信息存储在该表中。\n"
            "的多个数据表不做。\n"
            "的特定数据表不做。\n"
            "具体内容如表所示。\n"
            "订单信息表包含订单编号字段。\n"
        )
        ents = extract_entity_labels_from_text(junk)
        self.assertIn("用户", ents)
        self.assertIn("厂商", ents)
        self.assertIn("订单信息", ents)
        for bad in (
            "所示",
            "厂商列",
            "材料商城",
            "收藏",
            "购物车",
            "多个数据",
            "特定数据",
            "的多个数据",
            "的特定数据",
            "表中",
            "仓库管理员的信息存储在该",
            "材料类型的信息存储在该",
            "具体内容如",
            "yonghu",
        ):
            self.assertNotIn(bad, ents, ents)

        # 图侧 table_labels 不得灌实体
        sug = suggest_drafts_from_proposal(
            {
                "feature_lines": ["材料商城管理", "收藏管理"],
                "table_labels": ["材料商城", "收藏", "购物车", "地址"],
                "entity_hints": ["订单信息"],
            }
        )
        self.assertEqual(sug["draft_entities"], ["订单信息"])
        self.assertNotIn("材料商城", sug["draft_entities"])
        self.assertNotIn("收藏", sug["draft_entities"])

    def test_entities_mine_full_db_chapter(self) -> None:
        """数据库章应把表题注/小节标题尽量采全，不是掐几个功能名。"""
        from app.services.thesis_absorb_extract import extract_entity_labels_from_text

        text = (
            "第4章 系统设计\n"
            "4.2 功能模块\n"
            "管理端包含材料入库管理、材料商城管理、订单管理。\n"
            "4.3 数据库设计\n"
            "本系统主要数据表如下。\n"
            "表 4.1 用户信息表\n"
            "表 4.2 厂商信息表\n"
            "表4-3 仓库管理员表\n"
            "表 4.4 材料类型表\n"
            "表 4.5 订单信息表\n"
            "表 4.6 收货地址表\n"
            "表 4.7 购物车表\n"
            "表 4.8 收藏表\n"
            "表 4.9 充值记录表\n"
            "表 4.10 公告信息表\n"
            "4.3.1 材料入库表\n"
            "表名：材料出库表\n"
            "（1）评价表\n"
        )
        ents = extract_entity_labels_from_text(text)
        for need in (
            "用户信息",
            "厂商信息",
            "仓库管理员",
            "材料类型",
            "订单信息",
            "收货地址",
            "购物车",
            "收藏",
            "充值记录",
            "公告信息",
            "材料入库",
            "材料出库",
            "评价",
        ):
            self.assertIn(need, ents, ents)
        # 功能清单里的商城、元叙述不得进实体
        self.assertNotIn("材料商城", ents)
        self.assertNotIn("本系统主要数据", ents)
        self.assertNotIn("材料出库表", ents)
        self.assertGreaterEqual(len(ents), 12, ents)

    def test_finalize_sections_drops_toc_noise(self) -> None:
        from app.services.thesis_absorb_extract import (
            clean_background,
            finalize_sections,
        )

        secs = finalize_sections(
            [
                {
                    "heading": "第1章绪论",
                    "lines": ["1.1", "研究背景", "1.2 课题研究的目的及意义"],
                },
                {
                    "heading": "第5章系统实现",
                    "lines": [
                        "5.1 管理员模块",
                        "5.1.4厂商管理",
                        "Ⅳ",
                        "3.1.1 经济可行性",
                        "3.2.1管理员用例图",
                    ],
                },
            ]
        )
        self.assertEqual(len(secs), 1)
        self.assertIn("系统实现", secs[0]["heading"])
        blob = " ".join(secs[0]["lines"])
        self.assertIn("管理员模块", blob)
        self.assertIn("厂商管理", blob)
        self.assertNotIn("可行性", blob)
        self.assertNotIn("用例图", blob)
        self.assertNotIn("Ⅳ", blob)
        self.assertEqual(clean_background("1.2 课题研究的目的及意义"), "")
        self.assertTrue(len(clean_background("材料销售数字化需求日益增长，需要一套业务系统。")) > 10)

    def test_section_lines_drop_toc_and_test_steps(self) -> None:
        """按章节摘句：目录点线/页眉目录/测试步骤叙述必须清掉。"""
        from app.services.thesis_absorb_extract import (
            clean_section_line,
            finalize_sections,
        )

        for bad in (
            "第3章 需求分析 ................. 5",
            "第5章 网站实现 ............. 27",
            "大连科技学院 2026届本科毕业设计（论文） 目录",
            "测试输入查询信息。输入「这个蛋糕很好吃」。",
            "显示「评价提交成功」，与预期结果相同。",
            "请填写此字段，与预期结果相同。",
            "在不同浏览器环境下进行了兼容性测试。",
            "[J].电脑与信息技术,2024,32(01):95-97",
            "第4章为系统设计，第5章为系统实现。",
            "分析",
            # 可行性散文 / 半截起句 / 图题 / 实现走读 / 题名残片
            "程中，开发最大的财务开支就是人力成本，所以经济上是可行的。",
            "所以在技术上可行。",
            "青竹小轩酒店管理系统的研究为消费者提供了更加便捷的酒店预定途径，也为酒店",
            "则使用 Vue 技术，实现了页面的动态交互和流畅的用户体验。",
            "图 4.1 系统架构图",
            "图 4.2 用户功能模块图",
            "系统结构设计",
            "管理员端功能设计",
            "用户进入系统首先要进行的操作就是注册，登录的页面是在用户完成上一步注册之",
            "图 5.1 登录页面图",
            "图 5.2 登录成功页面图",
            "系统前端",
            "房间页面",
            "在进行酒店客房管理",
            "青竹小轩酒店管理",
        ):
            self.assertIsNone(clean_section_line(bad), bad)

        for good in (
            "预定管理",
            "续订管理",
            "评论管理",
            "用户管理",
            "房型管理",
            "管理端包含客房信息管理与入住管理",
        ):
            self.assertIsNotNone(clean_section_line(good), good)

        self.assertIsNotNone(clean_section_line("管理端包含订单管理与用户管理"))
        secs = finalize_sections(
            [
                {
                    "heading": "系统设计",  # 裸短标题不得进按章节
                    "lines": ["[J].电脑与信息技术,2024,32(01):95-97"],
                },
                {
                    "heading": "第6章系统测试",
                    "lines": [
                        "测试输入查询信息。",
                        "显示「评价提交成功」，与预期结果相同。",
                        "第3章 需求分析 ................. 5",
                        "大连科技学院 2026届本科毕业设计（论文） 目录",
                        "购物车管理模块负责加购与结算。",
                    ],
                },
            ]
        )
        self.assertEqual(len(secs), 1)
        self.assertIn("第6章", secs[0]["heading"])
        blob = " ".join(secs[0]["lines"])
        self.assertIn("购物车管理", blob)
        self.assertNotIn("评价提交", blob)
        self.assertNotIn("目录", blob)
        self.assertNotIn("..........", blob)
        self.assertNotIn("电脑与信息技术", blob)

    def test_chapter_sections_reject_prose_and_captions(self) -> None:
        """按章节：只认真章题；叙述句/图注/测试结果图名不得冒充章。"""
        from app.services.thesis_absorb_extract import (
            extract_thesis_proposal,
            split_buckets,
        )

        sample = (
            "第3章需求分析\n"
            "汽车销售行业发展迅速，汽车销售平台具有广阔的市场前景。\n"
            "行为模式。用户用例图，如图3.2所示。\n"
            "功能需求，但系统仍需完善。\n"
            "管理端包含用户管理与订单管理。\n"
            "第4章网站总体设计\n"
            "本网站采用B/S架构，使用MySQL数据库。\n"
            "数据库设计\n"
            "表4.1 用户表 含用户管理与订单管理。\n"
            "购物车管理模块负责加购。\n"
            "第6章系统测试\n"
            "用户功能评价测试用例1结果图\n"
            "如图6.1所示。\n"
            "购物车测试用例2结果图\n"
            "如图6.4所示。\n"
        )
        heads = []
        for _bucket, items in split_buckets(sample).items():
            for h, _lines in items:
                if h:
                    heads.append(h)
        self.assertIn("第3章需求分析", heads)
        self.assertIn("第4章网站总体设计", heads)
        self.assertIn("第6章系统测试", heads)
        self.assertIn("数据库设计", heads)
        for bad in (
            "行为模式。用户用例图，如图3.2所示。",
            "功能需求，但系统仍需完善。",
            "用户功能评价测试用例1结果图",
            "购物车测试用例2结果图",
        ):
            self.assertNotIn(bad, heads)

        secs = extract_thesis_proposal(sample)["proposal"].get("sections") or []
        sec_heads = [str(s.get("heading") or "") for s in secs]
        self.assertTrue(any("第3章" in h for h in sec_heads), sec_heads)
        self.assertTrue(any("第4章" in h for h in sec_heads), sec_heads)
        # 展示只留第x章；「数据库设计」可分桶但不得进按章节
        self.assertFalse(any(h == "数据库设计" for h in sec_heads), sec_heads)
        # 第6章桶仍切开；摘句若只剩测试图注则不进「按章节」展示
        blob = " ".join(
            " ".join(s.get("lines") or []) for s in secs if isinstance(s, dict)
        )
        self.assertNotIn("结果图", blob)
        self.assertNotIn("如图6", blob)
        for h in sec_heads:
            self.assertTrue(h.startswith("第") or h == "图注与结构标签", h)
            self.assertNotIn("。", h)
            self.assertNotIn("结果图", h)
            self.assertNotIn("如图", h)

    def test_title_not_stolen_from_toc_heading(self) -> None:
        text = (
            "冠清绿能环保材料销售系统的设计与实现\n"
            "张三\n"
            "摘要 本文设计了一套材料销售系统。\n"
            "第1章 绪论\n"
            "1.1 研究背景\n"
            "材料销售数字化需求日益增长。\n"
            "1.2 课题研究的目的及意义\n"
            "第2章 系统分析\n"
            "2.1 管理员模块负责用户与订单管理。\n"
            "2.2 厂商模块负责供货与入库。\n"
            "2.3 仓库管理员模块负责出入库。\n"
        )
        r = extract_thesis_proposal(text)
        title = r["proposal"].get("title") or ""
        self.assertNotIn("1.2", title)
        self.assertNotIn("目的及意义", title)
        self.assertTrue(
            "销售系统" in title or "冠清" in title,
            title,
        )

    def test_opening_draft_no_original_title_forced(self) -> None:
        prop = {
            "title": "2024级秘密题名",
            "background": "背景一句",
            "feature_lines": ["借阅模块"],
            "out_scope_lines": [],
        }
        draft = build_opening_draft(prop)
        self.assertIn("某业务系统", draft)
        self.assertNotIn("2024级秘密题名", draft)
        self.assertIn("借阅模块", draft)

    def test_no_llm_in_extract_module(self) -> None:
        import app.services.thesis_absorb_extract as mod
        import inspect

        src = inspect.getsource(mod)
        self.assertNotIn("run_", src)  # 禁代理 LLM agent 调用名混入
        self.assertNotIn("temperature_for", src)
        self.assertNotIn("chat.completions", src)


class ThesisAbsorbUiContract(unittest.TestCase):
    """控制台文案禁词 + 路由/侧栏挂载。"""

    def test_vue_forbidden_copy(self) -> None:
        from pathlib import Path

        root = Path(__file__).resolve().parents[2]
        vue = (root / "frontend/src/views/ThesisAbsorb.vue").read_text(encoding="utf-8")
        for bad in ("智能匹配论文", "上传论文出包", "确认创建", "开始生成", "预览学生端"):
            self.assertNotIn(bad, vue)
        self.assertIn("终稿吸收", vue)
        self.assertIn("复制给助手", vue)
        self.assertIn("非正式建项", vue)
        # 六区同屏（禁止仅用三 Tab 代替）
        for label in ("记录概要", "抽出的要点", "覆盖情况", "补齐建议", "给助手", "试一下"):
            self.assertIn(label, vue)
        self.assertIn("短摘录", vue)
        self.assertIn("ta-feat-pill", vue)
        self.assertIn("function coverageClass", vue)
        self.assertIn("现厂速查", vue)
        self.assertIn("ta-coverage-hints", vue)
        self.assertIn("coverage_hints", vue)
        self.assertIn("不算出包匹配", vue)
        # 搜无 ≠ 库空：禁止搜不到也催「拖入上方上传区」
        self.assertIn("listEmptyCopy", vue)
        self.assertIn("没有搜到终稿", vue)
        self.assertIn("换关键词或清空搜索", vue)
        self.assertIn("还没有终稿", vue)
        self.assertIn("拖入上方上传区", vue)
        self.assertIn("doBatchReextract", vue)
        self.assertIn("batchReextractLabel", vue)
        self.assertIn("checkedRowKeys", vue)
        self.assertIn("重抽已选", vue)
        self.assertIn("重抽规则落后", vue)
        self.assertIn("type: 'selection'", vue)
        self.assertIn("maybeFinishAbsorbBatch", vue)
        self.assertIn("applyPollItemToList", vue)
        self.assertIn("absorbBatchSession", vue)
        self.assertIn("absorbBatchTotal", vue)
        self.assertIn("批量抽取完成", vue)
        panel = (root / "frontend/src/components/UploadJobPanel.vue").read_text(encoding="utf-8")
        self.assertIn("batchTotal", panel)
        self.assertIn("settledCount", panel)
        # 数量只在 overview 出现一次，头 pill 不写「进度 N/M」
        self.assertNotIn("进度 ${settledCount", panel)
        self.assertNotIn("进度 ·", panel)
        api_js = (root / "frontend/src/api.js").read_text(encoding="utf-8")
        self.assertIn("thesisAbsorbReextractBatch", api_js)
        self.assertIn("/system/thesis-absorb/reextract-batch", api_js)
        self.assertIn("n-data-table", vue)
        self.assertIn("surface-detail", vue)
        self.assertIn("proj-head", vue)
        self.assertIn("detail-stage-body", vue)
        self.assertIn("返回终稿列表", vue)
        self.assertIn("ta-feed-grid", vue)
        self.assertIn("ta-draft-grid", vue)
        self.assertIn("按抽取重填", vue)
        self.assertIn("解锁调整", vue)
        self.assertIn("machineUnlocked", vue)
        self.assertIn(':disabled="!machineUnlocked"', vue)
        self.assertIn("needs_reextract", vue)
        self.assertIn("reextractAlertTitle", vue)
        self.assertIn("抽取规则已更新", vue)
        self.assertIn("反推成开题", vue)
        self.assertIn("spec-preview", vue)
        self.assertIn("含图注", vue)
        self.assertIn("文字/图注", vue)
        self.assertIn("图与文字交叉", vue)
        self.assertIn("figureStatusLabel", vue)
        self.assertNotIn("暂未开通", vue)
        self.assertNotIn('n-tab-pane name="structure"', vue)
        # 禁说明书腔反复刷屏
        for bad in ("不建项、不出包", "进厂库补能力", "喂助手稿", "身份条", "第 1 刀"):
            self.assertNotIn(bad, vue)

    def test_nav_and_router(self) -> None:
        from pathlib import Path

        root = Path(__file__).resolve().parents[2]
        app = (root / "frontend/src/App.vue").read_text(encoding="utf-8")
        router = (root / "frontend/src/router.js").read_text(encoding="utf-8")
        self.assertIn("/thesis-absorb", app)
        self.assertIn("终稿吸收", app)
        self.assertIn("从终稿抽出要点", app)
        # 工作台：紧挨「项目」之后（不埋在资产台末尾）
        proj = app.index("label: '项目'")
        absorb = app.index("label: '终稿吸收'")
        assets = app.index("label: '资产台'")
        self.assertLess(proj, absorb)
        self.assertLess(absorb, assets)
        self.assertIn("thesis-absorb", router)
        self.assertIn("ThesisAbsorb.vue", router)

    def test_help_card_present(self) -> None:
        from pathlib import Path

        root = Path(__file__).resolve().parents[2]
        help_src = (root / "frontend/src/views/Help.vue").read_text(encoding="utf-8")
        self.assertIn("anchor: '终稿吸收'", help_src)
        self.assertIn("同材同果", help_src)
        self.assertIn("现厂速查", help_src)
        self.assertIn("/thesis-absorb", help_src)

    def test_api_registered(self) -> None:
        from pathlib import Path

        root = Path(__file__).resolve().parents[2]
        sys_py = (root / "backend/app/api/system.py").read_text(encoding="utf-8")
        self.assertIn("system_thesis_absorb", sys_py)
        api_js = (root / "frontend/src/api.js").read_text(encoding="utf-8")
        self.assertIn("thesisAbsorbUpload", api_js)

    def test_async_extract_and_product_copy(self) -> None:
        from pathlib import Path

        root = Path(__file__).resolve().parents[2]
        svc = (root / "backend/app/services/thesis_absorb.py").read_text(encoding="utf-8")
        self.assertIn("schedule_absorb_extract", svc)
        self.assertIn("reextract_batch", svc)
        self.assertIn("_EXTRACT_CONCURRENCY", svc)
        self.assertIn("kick_stale_extracts", svc)
        self.assertIn("_KICK_STALE_MIN_INTERVAL_S", svc)
        self.assertIn("_apply_llm_drafts_to_row", svc)
        self.assertIn("ensure_extract_alive", svc)
        self.assertIn("EXTRACT_STALE_S", svc)
        self.assertIn("EXTRACT_SYNC_TIMEOUT_S", svc)
        self.assertIn("_job_text_only", svc)
        api = (root / "backend/app/api/system_thesis_absorb.py").read_text(encoding="utf-8")
        self.assertIn("已接收，抽取中", api)
        self.assertIn("/system/thesis-absorb/reextract-batch", api)
        self.assertIn("ThesisAbsorbBatchReextract", api)
        self.assertNotIn("可离开本页", api)
        # 详情轮询禁止 kick；light/poll 减负
        self.assertIn("poll: bool", api)
        get_block = api.split("async def get_thesis_absorb", 1)[1].split(
            "async def upload_thesis_absorb", 1
        )[0]
        self.assertNotIn("kick_stale_extracts", get_block)
        self.assertIn("ensure_extract_alive", get_block)
        vue = (root / "frontend/src/views/ThesisAbsorb.vue").read_text(encoding="utf-8")
        self.assertIn("pollAbsorbExtract", vue)
        self.assertIn("hydrateExtractingJobs", vue)
        self.assertNotIn("可离开本页", vue)
        self.assertIn("poll: true", vue)
        # 抽取未完：上传条「打开」仅 done；列表操作列不给进详情
        self.assertIn("job.status === 'done' && job.recordId", vue)
        self.assertIn("if (row.status === 'extracting')", vue)
        self.assertIn("job.status !== 'done'", vue)
        # 续传计时锚服务端时刻，禁止回来清零
        self.assertIn("absorbExtractStartedAtMs", vue)
        self.assertIn("keepStartedAt", vue)
        api_js = (root / "frontend/src/api.js").read_text(encoding="utf-8")
        self.assertIn("opts.poll", api_js)


class ThesisAbsorbOverlapHelper(unittest.TestCase):
    def test_overlap_noise_from_shell_menus_keys(self) -> None:
        """相近剔噪挂 shell_menus key，禁止 absorb 再抄平行中文表。"""
        from pathlib import Path

        from app.bake.schema.shell_menus import (
            SHELL_OPEN_MENU_KEYS,
            near_dup_shell_feature_labels,
        )
        from app.services import thesis_absorb as ta

        labels = near_dup_shell_feature_labels()
        self.assertIn("用户管理", labels)
        self.assertIn("公告管理", labels)
        self.assertIn("轮播图管理", labels)
        self.assertIn("留言管理", labels)
        self.assertIn("users", SHELL_OPEN_MENU_KEYS)
        src = Path(ta.__file__).read_text(encoding="utf-8")
        self.assertNotIn("_OVERLAP_NOISE", src)
        self.assertIn("near_dup_shell_feature_labels", src)

    def test_overlap_score_strips_shell_from_count(self) -> None:
        from app.services.thesis_absorb import _overlap_score

        n, inter = _overlap_score(["借阅模块", "读者模块"], ["借阅模块", "罚款模块"])
        self.assertEqual(n, 1)
        self.assertEqual(inter, ["借阅模块"])
        # 壳进展示交集，但不计入剔壳后的 n
        n2, inter2 = _overlap_score(
            ["用户管理", "公告管理", "社团活动管理"],
            ["用户管理", "公告管理", "轮播图管理"],
        )
        self.assertEqual(n2, 0)
        self.assertEqual(inter2, ["公告管理", "用户管理"])

    def test_near_duplicate_shell_only_not_flagged(self) -> None:
        from app.services.thesis_absorb import _near_duplicate_features

        ok, n, _ = _near_duplicate_features(
            ["用户管理", "公告管理", "轮播图管理", "个人信息管理"],
            ["用户管理", "公告管理", "轮播图管理", "个人中心"],
        )
        self.assertFalse(ok)
        self.assertEqual(n, 0)

    def test_near_duplicate_few_shared_business_not_flagged(self) -> None:
        from app.services.thesis_absorb import _near_duplicate_features

        a = [
            "社团活动管理",
            "成员管理",
            "经费管理",
            "场地预约管理",
            "活动报名管理",
            "社团公告管理",
            "考核管理",
            "请假管理",
            "用户管理",
        ]
        b = [
            "社团活动管理",
            "成员管理",
            "物资借用管理",
            "招新管理",
            "积分管理",
            "印章管理",
            "会议室管理",
            "值班管理",
            "公告管理",
        ]
        ok, n, _ = _near_duplicate_features(a, b)
        self.assertFalse(ok)
        self.assertEqual(n, 2)

    def test_near_duplicate_almost_full_coverage_flagged(self) -> None:
        from app.services.thesis_absorb import _near_duplicate_features

        short = [
            "社团活动管理",
            "成员管理",
            "经费管理",
            "场地预约管理",
            "用户管理",
        ]
        long = [
            "社团活动管理",
            "成员管理",
            "经费管理",
            "场地预约管理",
            "活动报名管理",
            "考核管理",
            "公告管理",
        ]
        ok, n, inter = _near_duplicate_features(short, long)
        self.assertTrue(ok)
        self.assertEqual(n, 4)  # 剔壳后短侧 4 条全中
        self.assertIn("社团活动管理", inter)
        self.assertIn("经费管理", inter)
        # 壳只在一侧：不进交集行，也不挡出条
        self.assertNotIn("用户管理", inter)

    def test_vue_overlaps_hint_not_blocking(self) -> None:
        """相近只提示：disabled 不读 overlaps / detailOverlaps。"""
        from pathlib import Path

        vue = (Path(__file__).resolve().parents[2] / "frontend/src/views/ThesisAbsorb.vue").read_text(
            encoding="utf-8"
        )
        self.assertIn("ta-alert info", vue)
        self.assertIn(".ta-alert.info", vue)
        for line in vue.splitlines():
            if ":disabled" not in line and "disabled=" not in line:
                continue
            self.assertNotIn("overlap", line.lower())

    def test_extract_wall_age_naive_local(self) -> None:
        """naive 库时不得当 UTC，否则东八区年龄会被算成 0。"""
        from datetime import datetime, timedelta
        from types import SimpleNamespace

        from app.services.thesis_absorb import _extract_wall_age_s

        past = datetime.now() - timedelta(minutes=47)
        age = _extract_wall_age_s(SimpleNamespace(updated_at=past, created_at=None))
        self.assertGreater(age, 40 * 60)
        self.assertLess(age, 55 * 60)


class ThesisAbsorbRoleNoise(unittest.TestCase):
    def test_role_labels_reject_narrative_fragments(self) -> None:
        from app.services.proposal import extract_role_labels

        blob = (
            "系统共划分为四类核心角色：用户、厂商、仓库管理员、管理员。"
            "用户在材料商城登录后下单，并提交评论，着重展示前后对比。"
            "辅导员登录后可审核。"
        )
        roles = extract_role_labels(blob)
        self.assertIn("厂商", roles)
        self.assertIn("仓库管理员", roles)
        self.assertIn("辅导员", roles)
        for bad in ("在材料商城", "用户在", "并提交", "着重展示前后"):
            self.assertNotIn(bad, roles)


class ThesisAbsorbDesignChapterMining(unittest.TestCase):
    """功能模块从需求/设计章采，目录参考文献点线不得裁掉正文。"""

    def test_strip_skips_toc_references_dots(self) -> None:
        from app.services.proposal import strip_non_dev_sections

        raw = (
            "目录\n"
            "第4章系统总体设计........15\n"
            "参考文献..................40\n"
            "致谢......................42\n"
            "第4章系统总体设计\n"
            "4.2 系统功能模块\n"
            "管理员端分为十二大定制模块，其中包含用户管理、厂商管理、材料类型管理、订单管理。\n"
            "第5章系统实现\n"
            "5.1 管理员登录\n"
            "参考文献\n"
            "[1] 某文献\n"
        )
        body = strip_non_dev_sections(raw)
        self.assertIn("材料类型管理", body)
        self.assertIn("系统实现", body)
        self.assertNotIn("[1] 某文献", body)

    def test_features_prefer_design_include_list(self) -> None:
        text = (
            "某销售系统的设计与实现\n"
            "第3章 需求分析\n"
            "3.2 用例图\n"
            "第4章 系统总体设计\n"
            "4.2 系统功能模块\n"
            "4.2.1 管理员端功能设计\n"
            "管理员端分为十二大定制模块，其中包含用户管理、厂商管理、仓库管理员管理、"
            "材料类型管理、材料商城管理、材料入库管理、材料出库管理、充值记录管理、订单管理。\n"
            "系统共划分为四类核心角色：用户、厂商、仓库管理员、管理员。\n"
            "4.3 数据库设计\n"
            "表 4.1 材料类型表\n"
            "表 4.2 订单信息表\n"
            "第5章 系统实现\n"
            "5.1 管理员模块\n"
            "5.1.1 管理员登录\n"
            "5.1.2 管理员系统首页界面\n"
        )
        r = extract_thesis_proposal(text)
        prop = r["proposal"]
        sug = __import__(
            "app.services.thesis_absorb_extract", fromlist=["suggest_drafts_from_proposal"]
        ).suggest_drafts_from_proposal(prop)
        self.assertIn("材料类型管理", sug["draft_features"])
        self.assertIn("订单管理", sug["draft_features"])
        self.assertNotIn("管理员登录", sug["draft_features"])
        self.assertNotIn("管理员系统首页界面", sug["draft_features"])
        self.assertIn("厂商", sug["draft_roles"])
        # 实体来自库表题注，不是掐功能词干
        self.assertIn("材料类型", sug["draft_entities"])
        self.assertIn("订单信息", sug["draft_entities"])
        self.assertNotIn("材料商城", sug["draft_entities"])
        self.assertNotIn("系统首页", sug["draft_entities"])
        self.assertNotIn("材料入库", sug["draft_entities"])


class ThesisAbsorbPersistReextract(unittest.TestCase):
    """持久化：升版/缺结构线索必须重读源文件，不能只洗库存 JSON。"""

    def test_stale_json_suggest_misplaces_roles_without_source(self) -> None:
        from app.services.thesis_absorb_extract import suggest_drafts_from_proposal

        # 旧库存：模块已被收成「××管理」，又无 role_hints → 角色进不了
        stale = {
            "feature_lines": [
                "管理员模块",
                "用户模块",
                "厂商管理",
                "仓库管理员管理",
                "材料类型管理",
            ]
        }
        sug = suggest_drafts_from_proposal(stale)
        self.assertEqual(sug["draft_roles"], ["管理员", "用户"])
        # 无库表证据不得把「厂商管理」掐成实体（有表时角色名可并存进实体）
        self.assertNotIn("厂商", sug["draft_entities"])
        self.assertNotIn("仓库管理员", sug["draft_entities"])
        self.assertEqual(sug["draft_entities"], [])

    def test_reextract_from_source_recovers_roles(self) -> None:
        import tempfile
        from types import SimpleNamespace

        from app.services.thesis_absorb import (
            _proposal_missing_structure_hints,
            _try_reextract_from_source,
        )

        body = (
            "某材料销售系统的设计与实现\n"
            "摘要 本文设计材料销售系统。\n"
            "第2章 系统分析\n"
            "系统共划分为四类核心角色：用户、厂商、仓库管理员、管理员。\n"
            "2.1 管理员模块负责用户与订单。\n"
            "2.2 厂商模块负责供货。\n"
            "2.3 仓库管理员模块负责出入库。\n"
            "2.4 用户模块可浏览商城下单。\n"
            "第3章 系统设计\n"
            "管理端包含材料类型管理、材料入库管理、订单管理、材料商城管理。\n"
        )
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "multi.txt"
            path.write_text(body, encoding="utf-8")
            row = SimpleNamespace(
                source_path=str(path),
                proposal_json={
                    "feature_lines": ["管理员模块", "厂商管理", "材料类型管理"],
                    # 故意缺 role_hints 键 = 假升版库存
                },
                warnings_json=[],
                content_sha256="",
                extractor_version="9",
                char_count=0,
                feature_line_count=0,
                has_figure_text=False,
                draft_roles=["管理员", "用户"],
                draft_entities=["厂商", "仓库管理员", "材料类型"],
                draft_features=[],
                status="stored",
            )
            self.assertTrue(_proposal_missing_structure_hints(row.proposal_json))
            self.assertTrue(_try_reextract_from_source(row))
            self.assertIn("role_hints", row.proposal_json)
            # 同步弱抽：功能空；实体仅表题注（本夹具无表 → 实体空）；角色回填合同端名
            self.assertIn("用户", row.draft_roles)
            self.assertIn("管理员", row.draft_roles)
            self.assertEqual(row.draft_features, [])
            self.assertEqual(row.draft_entities, [])

    def test_role_labels_cross_domain_not_hardcoded(self) -> None:
        from app.services.proposal import extract_role_labels

        cases = [
            (
                "系统角色包括馆员和读者。馆员模块负责借还，读者模块可检索。",
                {"馆员", "读者"},
            ),
            (
                "系统面向店员与就餐用户。店员模块接单，就餐用户模块下单。",
                {"店员", "就餐用户"},
            ),
            (
                "分为辅导员、班主任和学生三种角色。辅导员登录后审核。",
                {"辅导员", "班主任", "学生"},
            ),
        ]
        for blob, expect in cases:
            roles = set(extract_role_labels(blob))
            self.assertTrue(
                expect.issubset(roles),
                f"expect {expect} in {roles} for {blob[:24]}",
            )


class ThesisAbsorbFigureSide(unittest.TestCase):
    def test_figure_libs_ready_tuple(self) -> None:
        from app.services.thesis_absorb_figures import figure_libs_ready

        ready, hint = figure_libs_ready()
        self.assertIsInstance(ready, bool)
        self.assertTrue(hint)

    def test_ready_check_does_not_import_rapidocr(self) -> None:
        """meta/列表就绪检查不得冷加载 OCR（约 1～2s）。"""
        import importlib
        import sys

        # 清掉可能已被其它用例 import 的模块，再只跑就绪检查
        victims = [
            k
            for k in list(sys.modules)
            if k == "rapidocr_onnxruntime" or k.startswith("rapidocr_onnxruntime.")
        ]
        saved = {k: sys.modules.pop(k) for k in victims}
        try:
            import app.services.thesis_absorb_figures as fig

            importlib.reload(fig)
            ready, hint = fig.figure_libs_ready()
            self.assertIsInstance(ready, bool)
            self.assertTrue(hint)
            self.assertNotIn(
                "rapidocr_onnxruntime",
                sys.modules,
                "figure_libs_ready 不应真 import rapidocr",
            )
            self.assertTrue(fig.ocr_libs_ready() or not fig.ocr_libs_ready())
            self.assertNotIn("rapidocr_onnxruntime", sys.modules)
        finally:
            # 恢复其它用例可能依赖的已加载状态
            sys.modules.update(saved)
            importlib.reload(
                importlib.import_module("app.services.thesis_absorb_figures")
            )

    def test_captions_from_text(self) -> None:
        from app.services.thesis_absorb_figures import extract_captions_from_text

        caps = extract_captions_from_text(
            "如图 4.2 管理员端功能结构图所示。\n表 4.1 订单表结构\n"
        )
        self.assertTrue(any("图" in c for c in caps), caps)
        self.assertTrue(any("表" in c for c in caps), caps)

    def test_structure_ends_from_captions(self) -> None:
        from app.services.thesis_absorb_figures import ends_from_structure_captions

        ends = ends_from_structure_captions(
            [
                "图4.2 管理员端网站功能结构设计图",
                "图4.3 用户端功能结构设计图",
                "图4.4 厂商端功能结构设计图",
            ]
        )
        self.assertIn("管理员", ends)
        self.assertIn("用户", ends)
        self.assertIn("厂商", ends)

    def test_figure_cross_check_partial_overlap(self) -> None:
        from app.services.thesis_absorb_extract import apply_figure_cross_check

        result = {
            "proposal": {
                "feature_lines": ["订单管理", "材料类型管理", "购物车管理"],
                "role_hints": ["管理员", "用户"],
            },
            "warnings": ["角色与端不一致"],  # 正文误抽端留下的假红，图题对齐后应清掉
        }
        out = apply_figure_cross_check(
            result,
            ["订单管理", "材料类型管理", "充值记录管理"],
            structure_ends=["管理员", "用户"],
        )
        blob = " ".join(out["warnings"])
        self.assertTrue(
            "部分重合" in blob or "结构图" in blob or "文字清单" in blob,
            out["warnings"],
        )
        self.assertNotIn("角色与端不一致", out["warnings"])
        # 不脑补进主清单
        self.assertEqual(
            out["proposal"]["feature_lines"],
            ["订单管理", "材料类型管理", "购物车管理"],
        )

    def test_table_module_cross_hang_and_warn(self) -> None:
        """§3.0b：表能挂模块名；挂不上只告警不删对方。"""
        # 轮播图↔轮播图管理；内容分类↔分类管理（包含挂）
        ok = table_module_cross_warnings(
            entities=["轮播图", "内容分类", "订单"],
            features=["轮播图管理", "分类管理", "订单管理"],
        )
        self.assertEqual(ok, [])

        only_table = table_module_cross_warnings(
            entities=["轮播图", "订单"],
            features=["订单管理"],
            table_labels=["轮播图表"],
        )
        blob = " ".join(only_table)
        self.assertIn("表有模块无", blob)
        self.assertIn("轮播图", blob)
        self.assertNotIn("订单", blob)  # 订单已挂上

        only_mod = table_module_cross_warnings(
            entities=["订单"],
            features=["订单管理", "材料类型管理", "购物车管理"],
        )
        blob2 = " ".join(only_mod)
        self.assertIn("模块有表无", blob2)
        self.assertTrue("材料类型" in blob2 or "购物车" in blob2, only_mod)

        # 一侧空 → 不对账（不瞎黄）
        self.assertEqual(
            table_module_cross_warnings(entities=["订单"], features=[]),
            [],
        )
        # 壳模块不要求有表
        self.assertEqual(
            table_module_cross_warnings(
                entities=["订单"],
                features=["订单管理", "个人中心管理", "系统首页管理"],
            ),
            [],
        )
        # apply 替换旧告警，不改传入清单引用外的业务栏
        feats = ["订单管理", "材料类型管理", "购物车管理"]
        ents = ["订单"]
        out = apply_table_module_cross_check(
            ["表有模块无：旧告警", "其它告警"],
            entities=ents,
            features=feats,
        )
        self.assertIn("其它告警", out)
        self.assertTrue(any(w.startswith("模块有表无") for w in out), out)
        self.assertFalse(any(w == "表有模块无：旧告警" for w in out))
        self.assertEqual(feats, ["订单管理", "材料类型管理", "购物车管理"])
        self.assertEqual(ents, ["订单"])

    def test_extract_table_module_cross_in_warnings(self) -> None:
        """抽取路径：实体题注与功能清单能对上时，告警里应出现表↔模块黄条。"""
        text = """
第四章 系统设计
管理端包含订单管理、轮播图管理。
第五章 数据库设计
表 4.1 订单表 orders
表 4.2 轮播图表 rotation
表 4.3 内容分类表 sort
"""
        # 弱抽功能可能空；用 entity_hints + 手工拼对账形状已由上测覆盖。
        # 这里钉：有实体线索进 proposal，EXTRACTOR 升版。
        r = extract_thesis_proposal(text)
        self.assertEqual(r["extractor_version"], EXTRACTOR_VERSION)
        hints = r["proposal"].get("entity_hints") or []
        self.assertTrue(
            any("订单" in str(h) or "轮播" in str(h) or "分类" in str(h) for h in hints),
            hints,
        )

    def test_merge_figure_into_proposal(self) -> None:
        from app.services.thesis_absorb_figures import merge_figure_into_proposal

        prop = merge_figure_into_proposal(
            {"feature_lines": ["订单管理"], "sections": []},
            {
                "section_lines": ["图 4.2 功能结构图", "订单管理"],
                "structure_labels": ["订单管理"],
                "ocr_labels": ["订单管理"],
                "table_labels": ["订单"],
                "structure_ends": ["管理员"],
            },
        )
        self.assertEqual(prop["feature_lines"], ["订单管理"])  # 不改写主清单
        self.assertTrue(
            any(s.get("heading") == "图注与结构标签" for s in prop["sections"])
        )
        self.assertIn("订单管理", prop.get("figure_labels") or [])

    def test_ocr_label_pliers_drop_narrative(self) -> None:
        """整页 OCR 旁白不得冒充结构图模块标签。"""
        from app.services.thesis_absorb_figures import _labels_from_blob

        blob = (
            "图4.2管理员端系统功能结构图 "
            "投诉反馈管理 座位管理 订单管理 "
            "Flask微框架在路由管理 绘制了系统的功能模块 "
            "本章详细描述了系统各功能模块 时间成本与管理 当前自习室管理"
        )
        labs = _labels_from_blob(blob)
        self.assertIn("投诉反馈管理", labs)
        self.assertIn("座位管理", labs)
        self.assertIn("订单管理", labs)
        for junk in (
            "Flask微框架在路由管理",
            "绘制了系统的功能模块",
            "各功能模块",
            "时间成本与管理",
            "当前自习室管理",
        ):
            self.assertNotIn(junk, labs, labs)


class ThesisAbsorbDesignPriority(unittest.TestCase):
    """§3：实现章不得反写设计主清单。"""

    def test_pdf_word_break_include_list(self) -> None:
        """PDF 词中换行仍应抽出「包含 A管理、B管理」。"""
        from app.services.thesis_absorb_extract import extract_included_mgmt_items

        raw = (
            "管理员端分为十二大定制模块，其中包含用户管理、厂商管理、仓库管理员管理、"
            "材料类型管理、材\n料商城管理、材料入库管理、材料出库管理、订单管理。"
        )
        items = extract_included_mgmt_items(raw)
        self.assertIn("材料类型管理", items)
        self.assertIn("材料商城管理", items)
        self.assertIn("订单管理", items)

    def test_divide_ie_and_ji_list_morphology(self) -> None:
        """形态：划分为…模块即…；包含…及…；涵盖…等核心功能。"""
        from app.services.thesis_absorb_extract import extract_included_mgmt_items

        divide = (
            "管理员端功能划分为九个模块，即系统用户管理、跑腿工单管理、订单评价管理、"
            "生活服务管理、活动管理、轮播图管理、论坛管理，以及留言管理和通知公告管理"
            "共九个模块。"
        )
        items = extract_included_mgmt_items(divide)
        for need in (
            "系统用户管理",
            "跑腿工单管理",
            "活动管理",
            "留言管理",
            "通知公告管理",
        ):
            self.assertIn(need, items, items)
        self.assertFalse(any("共九个" in x for x in items), items)

        ji = "其中用户端包含了用户管理、商家管理及菜品信息管理等核心模块。"
        items2 = extract_included_mgmt_items(ji)
        self.assertIn("用户管理", items2)
        self.assertIn("商家管理", items2)
        self.assertIn("菜品信息管理", items2)

        cover = (
            "管理员端涵盖个人中心、用户管理、公告管理、商品及入库管理、订单管理等核心功能。"
        )
        items3 = extract_included_mgmt_items(cover)
        self.assertIn("用户管理", items3)
        self.assertIn("公告管理", items3)
        self.assertIn("商品及入库管理", items3)
        self.assertIn("订单管理", items3)

    def test_design_divide_ie_enters_feature_lines(self) -> None:
        """总体设计「划分为…即」清单应进 feature_lines（弱抽亦收）。"""
        text = (
            "跑腿服务平台的设计与实现\n"
            "第4章 系统总体设计\n"
            "4.2 功能结构设计\n"
            "管理员端功能划分为九个模块，即系统用户管理、跑腿工单管理、订单评价管理、"
            "生活服务管理、活动管理、轮播图管理、论坛管理，以及留言管理和通知公告管理"
            "共九个模块。管理员端功能结构设计参见图4.2。\n"
            "用户端功能划分为八个模块，即首页、跑腿工单、活动管理、生活服务点、"
            "金额管理、订单评价、留言及论坛。\n"
            "第5章 系统实现\n"
            "5.1 管理员系统用户管理\n"
            "5.2 管理员跑腿工单管理\n"
            "5.3 管理员活动管理\n"
        )
        r = extract_thesis_proposal(text)
        feats = r["proposal"]["feature_lines"]
        blob = " ".join(feats)
        # 忠于原文：设计清单 ∩ 实现交叉；下列三项两端皆有
        for need in ("系统用户管理", "跑腿工单管理", "活动管理"):
            self.assertIn(need, blob, feats)
        self.assertGreaterEqual(len(feats), 3, feats)
        # 设计侧「划分为…即」须采到金额管理（可进 module_hints / 弱抽池）
        from app.services.thesis_absorb_extract import extract_included_mgmt_items

        mined = extract_included_mgmt_items(text)
        self.assertIn("金额管理", mined, mined)

    def test_multi_end_include_lists_full(self) -> None:
        """四端清单无「等」——要全收；含「系统首页、××管理」起头。"""
        text = (
            "某销售系统的设计与实现\n"
            "第4章 系统总体设计\n"
            "管理员端分为十二大定制模块，其中包含用户管理、厂商管理、仓库管理员管理、"
            "材料类型管理、材料商城管理、材料入库管理、材料出库管理、我的收藏管理、"
            "充值记录管理、系统管理、订单管理、个人中心管理。\n"
            "用户端分为九大定制模块，其中包含系统首页、材料商城管理、公告咨询管理、"
            "购物车管理、在线客服管理、个人中心管理、我的收藏管理、订单管理、地址管理。\n"
            "厂商端分为四大定制模块，其中包含系统首页、材料商城管理、订单管理、个人中心管理。\n"
            "仓库管理员端分为五大定制模块，其中包含系统首页管理、材料商城管理、"
            "材料入库管理、材料出库管理、个人中心管理。\n"
        )
        r = extract_thesis_proposal(text)
        feats = r["proposal"]["feature_lines"]
        blob = " ".join(feats)
        for need in (
            "用户管理",
            "订单管理",
            "个人中心管理",
            "购物车管理",
            "地址管理",
            "公告咨询管理",
            "在线客服管理",
            "系统首页",
        ):
            self.assertIn(need, blob, feats)
        # 「系统管理」是空壳分组，不是菜单——设计总述点名也掐
        self.assertNotIn("系统管理", blob, feats)
        self.assertGreaterEqual(len(feats), 15, feats)

    def test_impl_shell_not_in_features(self) -> None:
        text = (
            "某系统的设计与实现\n"
            "第4章 系统总体设计\n"
            "管理端包含材料类型管理、订单管理、材料入库管理。\n"
            "第5章 系统实现\n"
            "5.1 管理员登录\n"
            "5.2 管理员系统首页界面\n"
            "5.3 密码修改\n"
            "5.4 管理员材料类型管理\n"
            "5.5 管理员订单管理\n"
            "5.6 管理员材料入库管理\n"
        )
        r = extract_thesis_proposal(text)
        feats = r["proposal"]["feature_lines"]
        blob = " ".join(feats)
        self.assertIn("材料类型管理", blob)
        self.assertIn("订单管理", blob)
        self.assertNotIn("管理员登录", blob)
        self.assertNotIn("首页", blob)

    def test_faithful_no_peel_sysadmin_to_sysmgmt(self) -> None:
        """忠于原文：系统管理员≠系统管理；须设计提到+实现交叉才进。"""
        from app.services.thesis_absorb_extract import (
            admit_features_faithful,
            clean_feature_label,
        )

        self.assertIsNone(clean_feature_label("系统管理员"))
        self.assertIsNone(clean_feature_label("系统管理"))
        self.assertIsNone(clean_feature_label("进入钢材管理"))
        self.assertIsNone(clean_feature_label("点击采购订单管理"))
        self.assertIsNone(clean_feature_label("通过留言反馈模块"))
        self.assertIsNone(clean_feature_label("为厂商钢材管理"))
        self.assertIsNone(clean_feature_label("在用户管理"))
        self.assertIsNone(clean_feature_label("管理"))

        text = (
            "钢材销售系统的设计与实现\n"
            "第4章 系统总体设计\n"
            "管理员端包含用户订单管理、系统管理、交流论坛管理、订单处理管理。\n"
            "第5章 系统实现\n"
            "5.4 系统管理员端设计\n"
            "5.4.1 系统管理员登录\n"
            "系统管理员进入个人中心页面。\n"
            "5.4.5 管理员用户管理\n"
            "5.4.9 管理员订单处理管理\n"
            "5.4.12 管理员交流论坛管理\n"
        )
        r = extract_thesis_proposal(text)
        feats = r["proposal"]["feature_lines"]
        blob = " ".join(feats)
        self.assertNotIn("系统管理", blob)
        self.assertNotIn("系统管理员", blob)
        self.assertIn("订单处理管理", blob)
        self.assertIn("交流论坛管理", blob)
        # 用户管理在实现有、设计是「用户订单管理」——交叉可收
        self.assertTrue(
            any("用户" in x for x in feats),
            feats,
        )

        # 纯钳子：无交叉锚时弱抽仍掐空壳
        weak = admit_features_faithful(
            ["系统管理", "订单管理"],
            [],
        )
        self.assertNotIn("系统管理", weak)
        self.assertIn("订单管理", weak)
        # 有交叉：设计点名空壳仍不得因实现里的「系统管理员」而放行
        tight = admit_features_faithful(
            ["系统管理", "订单处理管理", "交流论坛管理"],
            [
                "订单处理管理",
                "管理员订单处理管理",
                "交流论坛管理",
                "管理员交流论坛管理",
                "用户管理",
            ],
            require_substantial=True,
        )
        self.assertNotIn("系统管理", tight)
        self.assertIn("订单处理管理", tight)
        self.assertIn("交流论坛管理", tight)

    def test_no_peel_warehouse_admin_or_fake_home_mgmt(self) -> None:
        """v39：仓库管理员≠仓库管理；系统首页≠首页管理。"""
        from app.services.thesis_absorb_extract import (
            _feat_confirmed_strict,
            _impl_confirm_labels,
            clean_feature_label,
            normalize_llm_drafts,
        )

        self.assertIsNone(clean_feature_label("首页管理"))
        self.assertEqual(clean_feature_label("系统首页管理"), "系统首页管理")
        self.assertEqual(clean_feature_label("仓库管理员管理"), "仓库管理员管理")

        # 实现章「仓库管理员」不得截出「仓库管理」
        confirms = _impl_confirm_labels(
            [
                "5.3 仓库管理员端",
                "5.3.1 仓库管理员登录",
                "仓库管理员进入材料入库管理界面。",
                "5.3.2 系统首页管理",
                "5.3.3 材料入库管理",
                "5.3.4 材料出库管理",
            ],
            limit=40,
        )
        self.assertNotIn("仓库管理", confirms)
        self.assertIn("材料入库管理", confirms)
        self.assertIn("系统首页管理", confirms)

        # 交叉：假「仓库管理」不得靠「仓库管理员管理」过关
        self.assertFalse(
            _feat_confirmed_strict(
                "仓库管理",
                ["仓库管理员管理", "材料入库管理", "材料出库管理"],
            )
        )
        self.assertTrue(
            _feat_confirmed_strict(
                "仓库管理员管理",
                ["仓库管理员管理", "材料入库管理"],
            )
        )
        # 「首页管理」不得靠「系统首页」弱干过关
        self.assertFalse(
            _feat_confirmed_strict("首页管理", ["系统首页", "系统首页管理"])
        )

        norm = normalize_llm_drafts(
            ["用户", "厂商", "仓库管理员", "管理员"],
            ["用户", "订单"],
            [
                "用户管理",
                "仓库管理",
                "仓库管理员管理",
                "首页管理",
                "系统首页管理",
                "材料入库管理",
            ],
            table_captions=["用户", "订单"],
            entity_hints=["用户", "订单"],
            confirm_features=[
                "仓库管理员管理",
                "系统首页管理",
                "材料入库管理",
                "材料出库管理",
                "用户管理",
            ],
        )
        feats = norm["draft_features"]
        self.assertNotIn("仓库管理", feats)
        self.assertNotIn("首页管理", feats)
        self.assertIn("仓库管理员管理", feats)
        self.assertIn("系统首页管理", feats)

        text = (
            "冠清绿能环保材料销售系统的设计与实现\n"
            "第3章 需求分析\n"
            "系统共划分为四类核心角色：用户、厂商、仓库管理员、管理员。\n"
            "第4章 系统总体设计\n"
            "管理员端包含用户管理、厂商管理、仓库管理员管理、材料类型管理、订单管理。\n"
            "仓库管理员端分为五大定制模块，其中包含系统首页管理、材料商城管理、"
            "材料入库管理、材料出库管理、个人中心管理。\n"
            "第5章 系统实现\n"
            "5.3 仓库管理员端\n"
            "5.3.1 仓库管理员登录\n"
            "5.3.2 系统首页管理\n"
            "5.3.3 材料入库管理\n"
            "5.3.4 材料出库管理\n"
        )
        r = extract_thesis_proposal(text)
        feats = r["proposal"]["feature_lines"]
        # 交叉后主清单可能只留实现对上的项；禁止假剥/假首页
        self.assertNotIn("仓库管理", feats)
        self.assertNotIn("首页管理", feats)
        self.assertTrue(
            any(x == "系统首页管理" or x.endswith("入库管理") for x in feats),
            feats,
        )
        # 设计采矿仍应收真「仓库管理员管理」（交叉薄时在 module_hints）
        hints = r["proposal"].get("module_hints") or []
        self.assertIn("仓库管理员管理", hints)

    def test_writing_variants_prefer_mgmt_form(self) -> None:
        """写法多变：口语/UML类名不进功能；××管理才是稳形态；角色不吃叙述渣。"""
        from app.services.thesis_absorb_extract import (
            clean_feature_label,
            extract_included_mgmt_items,
        )
        from app.services.proposal import extract_role_labels

        self.assertIsNone(clean_feature_label("个人中心这些功能"))
        self.assertIsNone(clean_feature_label("可以进行操作和管理"))
        self.assertIsNone(clean_feature_label("管理员类"))
        self.assertIsNone(clean_feature_label("用户类"))
        self.assertEqual(clean_feature_label("订单管理"), "订单管理")

        # 类图句不得当功能清单
        uml = extract_included_mgmt_items(
            "本网站主要包含用户类、管理员类、自习室类、座位类、订单类。"
        )
        self.assertEqual(uml, [])
        # 顿号××管理仍收
        mgmt = extract_included_mgmt_items(
            "管理端包含订单管理、材料类型管理、个人中心管理、系统管理。"
        )
        self.assertIn("订单管理", mgmt)
        self.assertIn("材料类型管理", mgmt)
        self.assertNotIn("系统管理", mgmt)

        roles = extract_role_labels(
            "模块涵盖管理员登录、服务审核。无需复杂学习即可轻松使用。"
            "系统角色包括管理员与用户。"
        )
        self.assertIn("管理员", roles)
        self.assertIn("用户", roles)
        self.assertNotIn("涵盖管理员", roles)
        self.assertNotIn("即可", roles)

        # 实现口语清单 + 设计××管理
        text = (
            "材料销售系统\n"
            "第3章 需求分析\n"
            "系统角色包括管理员与用户。\n"
            "第4章 系统总体设计\n"
            "管理员端包含用户管理、订单管理、材料类型管理、个人中心管理。\n"
            "第5章 系统实现\n"
            "首页上包含材料商城，订单管理，个人中心这些功能，厂商可以进行操作和管理。\n"
            "5.1 管理员用户管理\n"
            "5.2 管理员订单管理\n"
            "5.3 管理员材料类型管理\n"
        )
        r = extract_thesis_proposal(text)
        feats = r["proposal"]["feature_lines"]
        blob = " ".join(feats)
        self.assertIn("订单管理", blob)
        self.assertIn("用户管理", blob)
        self.assertNotIn("这些功能", blob)
        self.assertNotIn("可以进行操作", blob)
        self.assertNotIn("管理员类", blob)
        roles2 = r["proposal"]["role_hints"]
        self.assertIn("管理员", roles2)
        self.assertIn("用户", roles2)
        self.assertNotIn("即可", roles2)

    def test_no_design_means_thin_even_with_impl(self) -> None:
        text = (
            "第5章 系统实现\n"
            "订单管理模块负责下单。\n"
            "客户管理模块负责档案。\n"
            "库存管理模块负责出入库。\n"
        )
        r = extract_thesis_proposal(text)
        self.assertTrue(r["thin_features"])
        self.assertEqual(r["proposal"]["feature_lines"], [])

    def test_fallback_and_normalize_llm_drafts(self) -> None:
        from app.services.thesis_absorb_extract import (
            fallback_drafts_no_llm,
            normalize_llm_drafts,
            build_absorb_evidence,
        )

        fb = fallback_drafts_no_llm(
            {"entity_hints": ["用户表", "订单表", "协议与前"]}
        )
        # 无模型也回填合同角色（实体里已有用户表 → 用户）
        self.assertIn("用户", fb["draft_roles"])
        self.assertEqual(fb["draft_features"], [])
        self.assertIn("用户", fb["draft_entities"])
        self.assertIn("订单", fb["draft_entities"])
        self.assertNotIn("协议与前", fb["draft_entities"])

        fb2 = fallback_drafts_no_llm(
            {
                "role_hints": ["管理员", "用户", "即可"],
                "entity_hints": ["订单表"],
            }
        )
        self.assertIn("管理员", fb2["draft_roles"])
        self.assertIn("用户", fb2["draft_roles"])
        self.assertNotIn("即可", fb2["draft_roles"])

        norm = normalize_llm_drafts(
            ["用户", "协议与前", "作为前"],
            ["订单", "与基础管理", "订单处理", "投诉纠纷"],
            [
                "订单管理",
                "与基础管理模块",
                "管理员类",
                "用户可进入自习室预约模块",
                "系统管理",
            ],
            table_captions=["订单", "用户"],
        )
        self.assertEqual(norm["draft_roles"], ["用户"])
        self.assertIn("订单", norm["draft_entities"])
        self.assertNotIn("与基础管理", norm["draft_entities"])
        # 无题注时过程词仍掐
        self.assertNotIn("订单处理", norm["draft_entities"])
        self.assertNotIn("投诉纠纷", norm["draft_entities"])
        self.assertIn("订单管理", norm["draft_features"])
        self.assertNotIn("与基础管理模块", norm["draft_features"])
        self.assertNotIn("管理员类", norm["draft_features"])
        self.assertNotIn("系统管理", norm["draft_features"])

        # 题注有的表必须进实体（含过程尾巴真表）；LLM 漏抽也要补上
        seeded = normalize_llm_drafts(
            ["用户"],
            ["用户"],  # LLM 漏了钢材分类/投诉纠纷
            ["订单管理", "系统管理"],
            table_captions=["用户表", "钢材分类表", "投诉纠纷表", "关于我们表"],
            entity_hints=["用户", "钢材分类"],
            design_features=["系统管理", "订单管理"],
        )
        self.assertIn("钢材分类", seeded["draft_entities"])
        self.assertIn("投诉纠纷", seeded["draft_entities"])
        self.assertIn("关于我们", seeded["draft_entities"])
        # 空壳形态闸仍掐（不靠正则遣词清单）
        self.assertNotIn("系统管理", seeded["draft_features"])

        # 产品跟合同：无正则 design 清单时，LLM××管理仍保留；口语/类名仍掐
        free = normalize_llm_drafts(
            ["管理员", "用户"],
            ["用户"],
            ["订单管理", "自习室预约管理", "管理员类", "个人中心这些功能"],
            table_captions=["用户表"],
            entity_hints=["用户"],
            design_features=None,
            confirm_features=None,
        )
        self.assertIn("订单管理", free["draft_features"])
        self.assertIn("自习室预约管理", free["draft_features"])
        self.assertNotIn("管理员类", free["draft_features"])
        self.assertNotIn("个人中心这些功能", free["draft_features"])

        from app.services.thesis_absorb_extract import finalize_feature_lines

        cleaned = finalize_feature_lines(
            [
                "订单管理",
                "系统管理",
                "进入采购订单管理模块",
                "图 4.2 管理员端系统功能结构设计图",
                "订单处理管理等",
                "关于我们",
            ]
        )
        self.assertIn("订单管理", cleaned)
        self.assertNotIn("系统管理", cleaned)
        self.assertFalse(any("进入" in x for x in cleaned))
        self.assertFalse(any(x.startswith("图") for x in cleaned))
        self.assertFalse(any(x.endswith("等") for x in cleaned))

        from app.services.thesis_absorb_extract import (
            _normalize_table_title_to_entity,
            coalesce_broken_lines,
            extract_entity_labels_from_text,
        )

        self.assertIsNone(_normalize_table_title_to_entity("关于我们"))
        self.assertIsNone(_normalize_table_title_to_entity("订单处理"))
        self.assertIsNone(_normalize_table_title_to_entity("据库表"))
        self.assertEqual(_normalize_table_title_to_entity("订单表"), "订单")
        self.assertEqual(_normalize_table_title_to_entity("关于我们表"), "关于我们")
        self.assertEqual(_normalize_table_title_to_entity("投诉纠纷表"), "投诉纠纷")
        self.assertEqual(_normalize_table_title_to_entity("系统简介表"), "系统简介")
        glued = coalesce_broken_lines(
            ["都变成实际的数", "据库表以及表和表之间的关联规则。"]
        )
        self.assertEqual(len(glued), 1)
        self.assertIn("数据库表", glued[0])
        broken = (
            "4.6 数据库设计\n"
            "都变成实际的数\n"
            "据库表以及表和表之间的关联规则。\n"
            "表 4.1 菜品信息表\n"
        )
        self.assertNotIn("据库", extract_entity_labels_from_text(broken))

        ev = build_absorb_evidence(
            "第3章 需求分析\n角色包括用户与管理员。\n"
            "第4章 系统设计\n管理端包含订单管理、用户管理。\n"
            "4.6 数据库设计\n表 4.1 用户表 people\n表 4.2 订单表 porder\n",
            proposal={"title": "小羽自习室", "entity_hints": ["用户", "订单"]},
        )
        grades = {p["grade"] for p in ev["packs"]}
        self.assertIn("P2", grades)
        self.assertIn("P1-modules", grades)
        self.assertIn("P1-tables", grades)
        self.assertFalse(ev["thin_p1"])
        self.assertFalse(ev["thin_p2"])

    def test_llm_drafts_agent_no_key_fallback(self) -> None:
        import asyncio
        from types import SimpleNamespace
        from unittest.mock import AsyncMock

        from app.llm.agents_thesis_absorb import run_thesis_absorb_drafts_agent

        rt = SimpleNamespace(
            stage_on=lambda _s: True,
            configured=False,
            monthly_token_budget=1_000_000,
        )
        db = AsyncMock()
        out = asyncio.run(
            run_thesis_absorb_drafts_agent(
                db,
                rt,
                text="第4章 数据库设计\n表 4.1 用户表\n",
                proposal={"title": "测", "entity_hints": ["用户"]},
                record_id=1,
            )
        )
        self.assertFalse(out["used_llm"])
        self.assertEqual(out["skip_reason"], "llm_no_key")
        self.assertEqual(out["coverage"], "unknown")
        self.assertIn("用户", out["draft_roles"])
        self.assertIn("用户", out["draft_entities"])
        self.assertTrue(any("Key" in w or "大模型" in w for w in out["warnings"]))


class ThesisAbsorbCoverageHints(unittest.TestCase):
    """现厂速查：同材同果 + 弱证禁假绿。"""

    def test_library_features_hint_library(self) -> None:
        from app.services.thesis_absorb import coverage_domain_hints

        prop = {
            "feature_lines": [
                "图书管理",
                "借阅管理",
                "归还管理",
                "续借管理",
                "读者管理",
            ],
            "role_hints": ["读者", "馆员"],
        }
        a = coverage_domain_hints(prop)
        b = coverage_domain_hints(prop)
        self.assertEqual(a, b)
        self.assertTrue(a)
        self.assertEqual(a[0]["domain_id"], "DOM-LIBRARY")
        self.assertGreaterEqual(int(a[0]["score"]), 2)
        self.assertTrue(a[0].get("primary"))
        self.assertTrue(a[0].get("caps"))
        self.assertTrue(a[0].get("flows") or a[0].get("hits"))
        # 主候选领先：弱尾不得与主候选同分并列刷屏
        if len(a) > 1:
            self.assertGreaterEqual(int(a[0]["score"]), int(a[1]["score"]))

    def test_weak_equal_hints_keep_best_hit_only(self) -> None:
        """弱证 score=1：只留命中最厚的，少人工从一堆同分里挑。"""
        from app.services.thesis_absorb import coverage_domain_hints

        prop = {
            "feature_lines": ["商品管理", "库存管理", "论坛管理", "物流管理"],
            "role_hints": ["用户", "管理员"],
        }
        hints = coverage_domain_hints(prop, top_n=6)
        self.assertTrue(hints)
        self.assertTrue(hints[0].get("primary"))
        # 不得把一长串 score=1 全摊开（收窄后应明显少于全目录）
        self.assertLessEqual(len(hints), 4)

    def test_shop_with_forum_addon_not_primary_forum(self) -> None:
        """订单/购物车主路径时，「论坛管理」挂件不得拐成 DOM-FORUM 主候选。"""
        from app.services.thesis_absorb import coverage_domain_hints

        # 功能行有订单+论坛、实体有购物车（真实吸收常见）
        prop = {
            "feature_lines": [
                "订单管理",
                "地址管理",
                "车辆管理",
                "分类管理",
                "论坛管理",
                "退换货管理",
            ],
            "entity_hints": ["购物车", "订单", "汽车商品", "车辆规格", "地址"],
            "role_hints": ["管理员", "用户"],
        }
        hints = coverage_domain_hints(prop, top_n=6)
        self.assertTrue(hints)
        self.assertEqual(hints[0]["domain_id"], "DOM-SHOP")
        self.assertTrue(hints[0].get("primary"))
        self.assertNotEqual(hints[0]["domain_id"], "DOM-FORUM")
        # 仅功能行：订单硬词在、商城词表未点名商品时，也不得把论坛推成唯一主候选
        bare = coverage_domain_hints(
            {
                "feature_lines": ["订单管理", "论坛管理", "用户管理"],
                "role_hints": ["用户"],
            },
            top_n=6,
        )
        if bare:
            self.assertNotEqual(bare[0]["domain_id"], "DOM-FORUM")

    def test_ambient_addon_not_steal_primary_across_groups(self) -> None:
        """彻查：主路径+论坛/收藏挂件时，不得被内容环境音字典序抢走。"""
        from app.services.thesis_absorb import coverage_domain_hints

        content = frozenset(
            {"DOM-FORUM", "DOM-BLOG", "DOM-MEDIA", "DOM-MUSIC", "DOM-DOCLIB"}
        )
        cases = [
            (
                "DOM-SHOP",
                {
                    "feature_lines": ["商品管理", "库存管理", "论坛管理", "收藏管理"],
                    "entity_hints": ["商品", "购物车"],
                },
            ),
            (
                "DOM-LIBRARY",
                {
                    "feature_lines": ["图书管理", "借阅管理", "论坛管理", "公告管理"],
                    "entity_hints": ["图书", "读者"],
                },
            ),
            (
                "DOM-DORM",
                {
                    "feature_lines": ["宿舍管理", "报修管理", "论坛管理"],
                    "entity_hints": ["宿舍", "报修单"],
                },
            ),
            (
                "DOM-HOSPITAL",
                {
                    "feature_lines": ["挂号管理", "科室管理", "论坛管理"],
                    "entity_hints": ["号源"],
                },
            ),
            (
                "DOM-SEAL",
                {
                    "feature_lines": ["用章申请管理", "审批管理", "论坛管理"],
                    "entity_hints": ["用章申请"],
                },
            ),
            (
                "DOM-SURVEY",
                {
                    "feature_lines": ["问卷管理", "题目管理", "论坛管理"],
                    "entity_hints": ["问卷"],
                },
            ),
            (
                "DOM-VOTE",
                {
                    "feature_lines": ["投票管理", "选项管理", "论坛管理"],
                    "entity_hints": ["投票"],
                },
            ),
            (
                "DOM-CINEMA",
                {
                    "feature_lines": ["场次管理", "选座管理", "论坛管理"],
                    "entity_hints": ["场次"],
                },
            ),
            (
                "DOM-MEDIA",
                {
                    "feature_lines": ["视频管理", "点播管理", "论坛管理", "收藏管理"],
                    "entity_hints": ["视频"],
                },
            ),
            (
                "DOM-FORUM",
                {
                    "feature_lines": ["论坛管理", "回帖管理", "板块管理", "收藏管理"],
                    "entity_hints": ["帖子", "板块"],
                },
            ),
        ]
        for expect, prop in cases:
            prop = {**prop, "role_hints": ["用户", "管理员"]}
            hints = coverage_domain_hints(prop, top_n=4)
            self.assertTrue(hints, msg=expect)
            self.assertEqual(
                hints[0]["domain_id"],
                expect,
                msg=f"{expect} got {hints[0]['domain_id']} hits={hints[0].get('hits')}",
            )
            if expect not in content:
                self.assertNotIn(hints[0]["domain_id"], content)

        # 弱主路径只有硬词+挂件：宁空，不假主推论坛/新闻
        for feats in (
            ["订单管理", "论坛管理"],
            ["订单管理", "新闻管理"],
            ["预约管理", "论坛管理"],
            ["报修管理", "论坛管理"],
        ):
            hints = coverage_domain_hints(
                {"feature_lines": feats, "role_hints": ["用户"]},
                top_n=4,
            )
            if hints:
                self.assertNotIn(hints[0]["domain_id"], content, msg=str(feats))

    def test_stem_overlap_on_current_version_not_batch_target(self) -> None:
        """现行规则下实体≈功能词干属常态，不得假亮需重抽 / 批量死循环。"""
        from types import SimpleNamespace

        from app.services.thesis_absorb import (
            EXTRACTOR_VERSION,
            _entities_look_like_feature_stems,
            _row_needs_rule_reextract,
        )

        ents = ["用户", "购物车", "订单", "地址", "材料类型"]
        feats = [
            "用户管理",
            "购物车管理",
            "订单管理",
            "地址管理",
            "材料类型管理",
        ]
        self.assertTrue(_entities_look_like_feature_stems(ents, feats))
        cur = SimpleNamespace(
            extractor_version=EXTRACTOR_VERSION,
            proposal_json={
                "feature_lines": feats,
                "tech_stack_lines": ["Spring Boot"],
                "role_hints": ["用户"],
            },
            draft_roles=["用户"],
            draft_entities=ents,
            draft_features=feats,
        )
        self.assertFalse(_row_needs_rule_reextract(cur))
        old = SimpleNamespace(
            extractor_version="40",
            proposal_json=cur.proposal_json,
            draft_roles=cur.draft_roles,
            draft_entities=ents,
            draft_features=feats,
        )
        self.assertTrue(_row_needs_rule_reextract(old))

    def test_llm_drafts_upgrade_review_and_keep_feats_on_skip(self) -> None:
        """同步薄→review 后 LLM 抽厚应升 stored；模型失败不得清空清单。"""
        from types import SimpleNamespace

        from app.services.thesis_absorb import _apply_llm_drafts_to_row

        thick = [
            "订单管理",
            "购物车管理",
            "商品管理",
            "用户管理",
            "地址管理",
        ]
        row = SimpleNamespace(
            proposal_json={"feature_lines": ["订单管理"], "title": "x"},
            warnings_json=["缺实现/结构图交叉，功能仅按设计清单弱抽"],
            draft_roles=[],
            draft_entities=[],
            draft_features=[],
            feature_line_count=1,
            status="review",
            coverage="unknown",
            coverage_machine="",
            coverage_note="",
            coverage_review_json=[],
            schema_extract_meta={},
        )
        _apply_llm_drafts_to_row(
            row,
            {
                "draft_roles": ["用户", "管理员"],
                "draft_entities": ["订单", "购物车"],
                "draft_features": thick,
                "coverage": "skin_gap",
                "coverage_note": "差皮",
                "warnings": [],
                "used_llm": True,
                "skip_reason": "",
            },
        )
        self.assertEqual(row.status, "stored")
        self.assertEqual(row.feature_line_count, len(thick))
        self.assertEqual(row.proposal_json.get("feature_lines"), thick)
        self.assertEqual(row.coverage, "skin_gap")

        # 模型失败：保留同步清单，勿清空制造假待核对
        row2 = SimpleNamespace(
            proposal_json={"feature_lines": thick},
            warnings_json=[],
            draft_roles=["用户"],
            draft_entities=["订单"],
            draft_features=thick,
            feature_line_count=len(thick),
            status="stored",
            coverage="unknown",
            coverage_machine="",
            coverage_note="",
            coverage_review_json=[],
            schema_extract_meta={},
        )
        _apply_llm_drafts_to_row(
            row2,
            {
                "draft_roles": [],
                "draft_entities": [],
                "draft_features": [],
                "coverage": "unknown",
                "coverage_note": "",
                "warnings": ["未配置可用大模型 Key（运行环境 → LLM）"],
                "used_llm": False,
                "skip_reason": "llm_no_key",
            },
        )
        self.assertEqual(row2.proposal_json.get("feature_lines"), thick)
        self.assertEqual(row2.feature_line_count, len(thick))
        self.assertEqual(row2.status, "stored")
        self.assertTrue(row2.proposal_json.get("absorb_llm_skip"))

    def test_gate_weak_covered_to_unknown(self) -> None:
        from app.services.thesis_absorb import gate_coverage_by_hints

        self.assertEqual(gate_coverage_by_hints("covered", []), "unknown")
        self.assertEqual(
            gate_coverage_by_hints(
                "covered",
                [{"domain_id": "DOM-GENERIC", "score": 1}],
            ),
            "unknown",
        )
        self.assertEqual(
            gate_coverage_by_hints(
                "covered",
                [{"domain_id": "DOM-LIBRARY", "score": 3}],
            ),
            "covered",
        )
        self.assertEqual(
            gate_coverage_by_hints(
                "skin_gap",
                [],
            ),
            "skin_gap",
        )

    def test_hints_brief_empty_forbids_covered_wording(self) -> None:
        from app.services.thesis_absorb import coverage_hints_brief

        brief = coverage_hints_brief([])
        self.assertIn("unknown", brief)
        self.assertIn("禁止 covered", brief)

    def test_coverage_copy_skin_gap_is_not_covered(self) -> None:
        """行业皮盖不住 / 栈形态交不了 ≠ 已齐：提示词/简报/控制台同口径。"""
        from pathlib import Path

        from app.llm import agents_thesis_absorb as agent
        from app.services.thesis_absorb import (
            absorb_stack_coverage_blockers,
            coverage_domain_hints,
            coverage_hints_brief,
            gate_coverage_by_stack,
        )

        self.assertIn("皮盖不住", agent._SYSTEM)
        self.assertIn("形态交不了", agent._SYSTEM)
        self.assertIn("不是 covered", agent._SYSTEM)
        self.assertEqual(agent.PROMPT_ID, "ta-drafts-v11")

        brief = coverage_hints_brief(
            coverage_domain_hints(
                {"feature_lines": ["图书管理", "借阅管理"], "role_hints": ["读者"]},
                top_n=3,
            )
            or [{"domain_id": "DOM-X", "label": "x", "score": 2, "hits": [], "flows": [], "caps": [], "primary": True}]
        )
        self.assertIn("skin_gap", brief)
        self.assertIn("不是 covered", brief)
        self.assertIn("技术栈", brief)

        self.assertTrue(absorb_stack_coverage_blockers(["Spring Boot", "微信小程序"]))
        self.assertEqual(
            gate_coverage_by_stack("covered", ["Django", "MySQL"]),
            "domain_gap",
        )
        self.assertEqual(
            gate_coverage_by_stack("covered", ["Spring Boot", "Vue 3", "MySQL"]),
            "covered",
        )
        self.assertEqual(
            gate_coverage_by_stack("covered", ["Vue 3", "Redis"]),
            "domain_gap",
        )

        vue = (Path(__file__).resolve().parents[2] / "frontend/src/views/ThesisAbsorb.vue").read_text(
            encoding="utf-8"
        )
        self.assertIn("差皮", vue)
        self.assertNotIn("差说法", vue)
        self.assertIn("栈交不了都不是已齐", vue)
        self.assertIn("coverage_stack_blockers", vue)
        self.assertIn("coverage_machine", vue)
        self.assertIn("filterMode = ref('unknown')", vue)

    def test_resolve_machine_coverage_hard_cases(self) -> None:
        from app.services.thesis_absorb import resolve_machine_coverage

        # 栈冲突：任意预选 → 差能力
        for prop in ("unknown", "covered", "skin_gap"):
            cov, reason = resolve_machine_coverage(
                prop,
                [{"domain_id": "DOM-LIBRARY", "score": 5}],
                ["Django", "MySQL"],
            )
            self.assertEqual(cov, "domain_gap", prop)
            self.assertTrue(reason.startswith("栈冲突"), reason)

        # 弱证 covered → unknown
        cov, _ = resolve_machine_coverage(
            "covered",
            [{"domain_id": "DOM-GENERIC", "score": 1}],
            ["Spring Boot", "Vue 3", "MySQL"],
        )
        self.assertEqual(cov, "unknown")

        # 并列弱证 covered → unknown
        cov, reason = resolve_machine_coverage(
            "covered",
            [
                {"domain_id": "DOM-A", "score": 3},
                {"domain_id": "DOM-B", "score": 3},
            ],
            ["Spring Boot", "Vue 3"],
        )
        self.assertEqual(cov, "unknown")
        self.assertIn("并列", reason)

        # 强主候选 covered → covered
        cov, reason = resolve_machine_coverage(
            "covered",
            [
                {"domain_id": "DOM-LIBRARY", "score": 4},
                {"domain_id": "DOM-OTHER", "score": 1},
            ],
            ["Spring Boot", "Vue 3", "MySQL"],
        )
        self.assertEqual(cov, "covered")
        self.assertEqual(reason, "")

    def test_llm_agent_gates_weak_covered(self) -> None:
        import asyncio
        from types import SimpleNamespace
        from unittest.mock import AsyncMock, patch

        from app.llm.agents_thesis_absorb import run_thesis_absorb_drafts_agent

        rt = SimpleNamespace(
            stage_on=lambda _s: True,
            configured=True,
            monthly_token_budget=1_000_000,
        )
        db = AsyncMock()
        fake = SimpleNamespace(
            ok=True,
            data={
                "roles": ["用户"],
                "entities": ["用户"],
                "features": ["某某管理"],
                "coverage": "covered",
                "coverage_note": "瞎标",
                "notes": "",
            },
            tokens=10,
            prompt_tokens=5,
            completion_tokens=5,
            reasoning_tokens=0,
            model="",
            provider="",
            error="",
        )

        async def _run():
            with (
                patch(
                    "app.llm.agents_thesis_absorb.monthly_tokens_used",
                    AsyncMock(return_value=0),
                ),
                patch(
                    "app.llm.agents_thesis_absorb.chat",
                    AsyncMock(return_value=fake),
                ),
                patch(
                    "app.llm.agents_thesis_absorb.record_call",
                    AsyncMock(),
                ),
                patch(
                    "app.llm.agents_thesis_absorb.append_deepseek_log",
                    lambda *_a, **_k: None,
                ),
            ):
                return await run_thesis_absorb_drafts_agent(
                    db,
                    rt,
                    text="第3章 需求分析\n角色包括用户。\n第4章 系统设计\n管理端包含某某管理。\n",
                    proposal={"title": "无关题名", "feature_lines": [], "entity_hints": ["用户"]},
                    record_id=99,
                )

        out = asyncio.run(_run())
        self.assertTrue(out["used_llm"])
        self.assertEqual(out["coverage"], "unknown")


if __name__ == "__main__":
    unittest.main()
