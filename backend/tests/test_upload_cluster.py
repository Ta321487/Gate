"""上传分堆抽测：规则聚类 + 真实样例开题正文（不调 LLM）。

覆盖建议场景：
- 一次拖 5 个不同域开题 → 约 5 个项目
- 同课题开题 + 功能清单 → 并成 1 个
- 混合分堆（2+2+1）→ 3 个
- 同域不同实现 → 拆开
- 无关材料 → 剔除
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.bake.sample_proposal import build_sample_proposal
from app.services.upload_cluster import (
    DocProfile,
    apply_overrides,
    assemble_plan,
    build_profiles,
    normalize_title_key,
    rule_cluster,
    validate_cluster_payload,
)

# 抽测用的五个不同域（固定 seed，结果可复现）
_FIVE_DOMAINS = (
    ("DOM-LIBRARY", 101),
    ("DOM-FOOD", 102),
    ("DOM-DORM", 103),
    ("DOM-PARKING", 104),
    ("DOM-CRM", 105),
)


def _p(i, name, title, role, signal, fp, chars=500):
    return DocProfile(
        index=i,
        name=name,
        path="",
        size=0,
        signal=signal,
        role=role,
        title=title,
        title_key=normalize_title_key(title),
        fingerprint=fp,
        excerpt="",
        chars=chars,
    )


def _write_bundle(
    root: Path, items: list[tuple[str, str]]
) -> list[tuple[Path, str, int]]:
    """items: (filename, text) → create_from_uploads 同形的文件列表。"""
    out: list[tuple[Path, str, int]] = []
    for name, text in items:
        path = root / name
        path.write_text(text, encoding="utf-8")
        out.append((path, name, path.stat().st_size))
    return out


def _cluster_files(files: list[tuple[Path, str, int]]):
    profiles = build_profiles(files)
    clusters, discard, notes = rule_cluster(profiles)
    return profiles, clusters, discard, notes


def _checklist_for(title: str, rows: list[tuple[str, str]]) -> str:
    lines = [
        f"题目：{title}",
        "",
        "功能清单",
        "| 编号 | 功能 | 说明 |",
        "| --- | --- | --- |",
    ]
    for i, (feat, desc) in enumerate(rows, 1):
        lines.append(f"| F{i} | {feat} | {desc} |")
    lines.extend(
        [
            "",
            "一、模块划分",
            f"1. {rows[0][0]}模块",
            f"2. {rows[1][0]}模块" if len(rows) > 1 else "2. 审核模块",
            "3. 用户角色与权限模块",
            "",
            "数据库实体：用户、业务单、审核记录。",
        ]
    )
    return "\n".join(lines)


def _trade_book_proposal(title: str) -> str:
    """图书皮 + 交易实现（与借阅壳刻意不同）；写长一点避免被判成清单挂靠。"""
    return f"""本科毕业设计（论文）开题报告

题目：{title}

一、选题背景
校园闲置教材流转需求旺盛，拟实现在线下单与购物车，走交易履约而非馆藏流通。

二、研究意义
为师生提供闲置教材流转渠道，强调订单履约。

三、国内外研究现状
同类课题多做馆藏流通；本课题聚焦二手交易下单。

四、主要功能
1. 商品上架与浏览
2. 购物车与下单
3. 订单配送与退款
4. 闲置教材检索与收藏

五、拟解决的关键问题
订单状态机、库存扣减、退款审核。

六、技术路线
Spring Boot + Vue + MySQL。

七、本期范围
实现订单、购物车、下单、配送、二手交易、退款模块。

八、进度安排
第1–2周需求分析，第3–10周开发，第11–12周测试。

数据库实体：商品、订单、购物车、用户、退款单。
"""


def _noise_resume() -> str:
    return """个人简历

姓名：张三
教育经历：某某大学 软件工程
实习经历：前端开发三个月
技能：HTML CSS JavaScript
求职意向：实习
"""


class UploadClusterUnitTests(unittest.TestCase):
    """轻量 DocProfile 断言（无 I/O）。"""

    def test_same_thesis_merges(self):
        ps = [
            _p(0, "开题.txt", "宿舍报修管理系统", "proposal", 8, ["报修", "派工", "审核"]),
            _p(1, "清单.txt", "宿舍报修", "checklist", 7, ["报修", "派工"]),
        ]
        cl, disc, _ = rule_cluster(ps)
        self.assertEqual(disc, [])
        self.assertEqual(cl, [[0, 1]])

    def test_different_topics_split(self):
        ps = [
            _p(0, "a.txt", "图书借阅系统", "proposal", 8, ["借阅", "逾期", "罚金"]),
            _p(1, "b.txt", "食堂点餐系统", "proposal", 8, ["点餐", "订单", "配送"]),
        ]
        cl, disc, _ = rule_cluster(ps)
        self.assertEqual(disc, [])
        self.assertEqual(sorted(cl), [[0], [1]])

    def test_same_domain_different_impl(self):
        ps = [
            _p(
                0,
                "a.txt",
                "图书借阅管理系统",
                "proposal",
                9,
                ["借阅", "归还", "逾期", "罚金", "续借"],
            ),
            _p(
                1,
                "b.txt",
                "校园二手图书交易",
                "proposal",
                9,
                ["二手", "订单", "购物车", "下单", "图书"],
            ),
        ]
        cl, disc, _ = rule_cluster(ps)
        self.assertEqual(disc, [])
        self.assertEqual(len(cl), 2)

    def test_discard_noise(self):
        ps = [
            _p(0, "resume.txt", "个人简历", "unknown", 0, [], chars=50),
            _p(1, "开题.txt", "物业报修系统", "proposal", 8, ["报修", "审核"]),
        ]
        cl, disc, _ = rule_cluster(ps)
        self.assertEqual(disc, [0])
        self.assertEqual(cl, [[1]])

    def test_llm_payload_reject_two_main_proposals(self):
        ps = [
            _p(0, "a.txt", "图书借阅系统", "proposal", 8, ["借阅", "逾期"], chars=800),
            _p(1, "b.txt", "食堂点餐系统", "proposal", 8, ["点餐", "订单"], chars=800),
        ]
        bad = {"discard": [], "clusters": [{"files": [0, 1], "reason": "都是系统"}]}
        self.assertIsNone(validate_cluster_payload(ps, bad))
        good = {
            "discard": [],
            "clusters": [
                {"files": [0], "reason": "借阅"},
                {"files": [1], "reason": "点餐"},
            ],
        }
        self.assertIsNotNone(validate_cluster_payload(ps, good))


class UploadClusterFixtureTests(unittest.TestCase):
    """用样例开题 / 手写清单落盘后走 build_profiles + rule_cluster。"""

    def test_five_different_domains_split(self):
        """一次拖 5 个不同域开题 → 约 5 个项目。"""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            items: list[tuple[str, str]] = []
            for dom, seed in _FIVE_DOMAINS:
                sample = build_sample_proposal(domain=dom, seed=seed)
                items.append((sample.filename + ".txt", sample.text))
            files = _write_bundle(root, items)
            profiles, clusters, discard, _ = _cluster_files(files)

            self.assertEqual(len(profiles), 5)
            self.assertEqual(discard, [], msg="样例开题不应被剔除")
            self.assertEqual(
                len(clusters),
                5,
                msg=f"期望 5 簇，实际 {clusters}；titles={[p.title for p in profiles]}",
            )
            # 每簇恰好一份
            self.assertEqual(sorted(len(c) for c in clusters), [1, 1, 1, 1, 1])

    def test_same_thesis_proposal_plus_checklist_merge(self):
        """同课题开题 + 功能清单 → 并成 1 个。"""
        sample = build_sample_proposal(domain="DOM-DORM", seed=201)
        checklist = _checklist_for(
            sample.title,
            [
                ("报修申请", "学生提交报修"),
                ("派工审核", "管理员派工"),
                ("进度查询", "查看报修进度"),
                ("评价反馈", "完成后评价"),
            ],
        )
        with tempfile.TemporaryDirectory() as td:
            files = _write_bundle(
                Path(td),
                [
                    (f"{sample.filename}.txt", sample.text),
                    ("宿舍报修功能清单.txt", checklist),
                ],
            )
            _profiles, clusters, discard, _ = _cluster_files(files)
            self.assertEqual(discard, [])
            self.assertEqual(len(clusters), 1, msg=f"应合并为一簇: {clusters}")
            self.assertEqual(sorted(clusters[0]), [0, 1])

    def test_mixed_two_two_one_yields_three_projects(self):
        """混合：两份同课题 + 另两份同课题 + 一份独立 → 3 个项目。"""
        dorm = build_sample_proposal(domain="DOM-DORM", seed=301)
        food = build_sample_proposal(domain="DOM-FOOD", seed=302)
        park = build_sample_proposal(domain="DOM-PARKING", seed=303)
        dorm_list = _checklist_for(
            dorm.title,
            [("报修", "提交"), ("派工", "处理"), ("审核", "通过"), ("进度", "查询")],
        )
        food_list = _checklist_for(
            food.title,
            [("点餐", "下单"), ("订单", "状态"), ("配送", "取餐"), ("口味", "备注")],
        )
        with tempfile.TemporaryDirectory() as td:
            files = _write_bundle(
                Path(td),
                [
                    ("dorm_proposal.txt", dorm.text),
                    ("dorm_checklist.txt", dorm_list),
                    ("food_proposal.txt", food.text),
                    ("food_checklist.txt", food_list),
                    ("parking_proposal.txt", park.text),
                ],
            )
            profiles, clusters, discard, _ = _cluster_files(files)
            self.assertEqual(discard, [])
            self.assertEqual(
                len(clusters),
                3,
                msg=(
                    f"期望 3 簇，实际 {clusters}；"
                    f"roles={[(p.name, p.role, p.title_key[:20], p.fingerprint[:6]) for p in profiles]}"
                ),
            )
            sizes = sorted(len(c) for c in clusters)
            self.assertEqual(sizes, [1, 2, 2])

    def test_same_domain_skin_different_impl_split(self):
        """都沾「图书」，一套借阅、一套二手交易 → 两个项目。"""
        lib = build_sample_proposal(domain="DOM-LIBRARY", seed=401)
        trade_title = "基于 Spring Boot 与 Vue 的校园二手图书交易系统的设计与实现"
        with tempfile.TemporaryDirectory() as td:
            files = _write_bundle(
                Path(td),
                [
                    ("library_loan.txt", lib.text),
                    ("library_trade.txt", _trade_book_proposal(trade_title)),
                ],
            )
            profiles, clusters, discard, _ = _cluster_files(files)
            self.assertEqual(discard, [])
            self.assertEqual(
                len(clusters),
                2,
                msg=(
                    f"同域不同实现应拆开: {clusters}；"
                    f"fp={[p.fingerprint for p in profiles]}"
                ),
            )

    def test_noise_discarded_others_kept(self):
        """无关简历剔除；有效开题保留。"""
        prop = build_sample_proposal(domain="DOM-PROPERTY", seed=501)
        with tempfile.TemporaryDirectory() as td:
            files = _write_bundle(
                Path(td),
                [
                    ("resume.txt", _noise_resume()),
                    (f"{prop.filename}.txt", prop.text),
                    ("notes.txt", "今天天气不错\n开会纪要\n"),
                ],
            )
            profiles, clusters, discard, _ = _cluster_files(files)
            self.assertIn(0, discard)
            self.assertIn(2, discard)
            self.assertEqual(len(clusters), 1)
            self.assertEqual(clusters[0], [1])
            self.assertTrue(all(p.signal >= 3 for p in profiles if p.index == 1))

    def test_assemble_plan_reasons_readable(self):
        """组装方案带可解释 reason，供确认弹窗展示。"""
        sample = build_sample_proposal(domain="DOM-IT", seed=601)
        with tempfile.TemporaryDirectory() as td:
            files = _write_bundle(Path(td), [("it.txt", sample.text)])
            profiles, clusters, discard, notes = _cluster_files(files)
            plan = assemble_plan(
                "testplan01",
                profiles,
                clusters,
                discard,
                source="rules",
                notes=notes,
                llm_ok=False,
            )
            d = plan.to_dict()
            self.assertEqual(d["plan_id"], "testplan01")
            self.assertEqual(len(d["clusters"]), 1)
            self.assertTrue(d["clusters"][0]["reason"])
            self.assertTrue(d["clusters"][0]["label"])

    def test_apply_overrides_split_all(self):
        """确认弹窗「全部拆开」覆盖分堆。"""
        sample = build_sample_proposal(domain="DOM-DORM", seed=701)
        checklist = _checklist_for(
            sample.title,
            [("报修", "提交"), ("派工", "处理"), ("审核", "通过")],
        )
        with tempfile.TemporaryDirectory() as td:
            files = _write_bundle(
                Path(td),
                [("a.txt", sample.text), ("b.txt", checklist)],
            )
            profiles, clusters, discard, notes = _cluster_files(files)
            plan = assemble_plan(
                "ov1",
                profiles,
                clusters,
                discard,
                source="rules",
                notes=notes,
                llm_ok=False,
            ).to_dict()
            # 先应是合并
            self.assertEqual(len(plan["clusters"]), 1)
            overridden = apply_overrides(
                plan, clusters=[[0], [1]], discard=[]
            )
            self.assertEqual(len(overridden["clusters"]), 2)
            self.assertEqual(overridden["source"], "confirmed")


if __name__ == "__main__":
    unittest.main()
