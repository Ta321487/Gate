"""终稿吸收：分桶抽取、对比句、同材同果、弱抽告警。"""

from __future__ import annotations

import unittest
from pathlib import Path

from app.services.thesis_absorb_extract import (
    EXTRACTOR_VERSION,
    build_feed_markdown,
    build_opening_draft,
    content_sha256,
    extract_thesis_proposal,
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
        self.assertIn("不会当成正式订单", vue)
        # 六区同屏（禁止仅用三 Tab 代替）
        for label in ("基本信息", "抽出的要点", "覆盖情况", "补齐建议", "给助手", "试一下"):
            self.assertIn(label, vue)
        self.assertIn("短摘录", vue)
        self.assertIn("ta-feat-pill", vue)
        self.assertIn("function coverageClass", vue)
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
        self.assertIn("建议按现行规则重新抽取", vue)
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
        self.assertIn("/thesis-absorb", help_src)

    def test_api_registered(self) -> None:
        from pathlib import Path

        root = Path(__file__).resolve().parents[2]
        sys_py = (root / "backend/app/api/system.py").read_text(encoding="utf-8")
        self.assertIn("system_thesis_absorb", sys_py)
        api_js = (root / "frontend/src/api.js").read_text(encoding="utf-8")
        self.assertIn("thesisAbsorbUpload", api_js)


class ThesisAbsorbOverlapHelper(unittest.TestCase):
    def test_overlap_score(self) -> None:
        from app.services.thesis_absorb import _overlap_score

        n, inter = _overlap_score(["借阅模块", "读者模块"], ["借阅模块", "罚款模块"])
        self.assertEqual(n, 1)
        self.assertEqual(inter, ["借阅模块"])


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

        from app.services.thesis_absorb_extract import _normalize_table_title_to_entity

        self.assertIsNone(_normalize_table_title_to_entity("关于我们"))
        self.assertIsNone(_normalize_table_title_to_entity("订单处理"))
        self.assertEqual(_normalize_table_title_to_entity("订单表"), "订单")
        self.assertEqual(_normalize_table_title_to_entity("关于我们表"), "关于我们")
        self.assertEqual(_normalize_table_title_to_entity("投诉纠纷表"), "投诉纠纷")
        self.assertEqual(_normalize_table_title_to_entity("系统简介表"), "系统简介")

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


if __name__ == "__main__":
    unittest.main()
