# -*- coding: utf-8 -*-
"""近五年域开题缩样 → 匹配 + 生成业务交付物（schema/SQL/模块/用例）。

不新开匹配旁路；只证明「壳内开题」能对路 bake，不是只过 match_text。
"""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

from app.bake.catalog import build_spec, match_text
from app.bake.domain_schema import validate_schema
from app.bake.domains import DOMAIN_CAPABILITIES, DOMAINS
from app.bake.engine import assert_table_budget, domain_sql
from app.bake.schema.modules import iter_nodes, module_model
from app.bake.schema.testcases import build_testcase_rows
from app.bake.themes import default_theme

CORPUS = Path(__file__).resolve().parent / "fixtures" / "domain_opening_corpus.json"
NAMED = [k for k in DOMAINS if k != "DOM-GENERIC"]


def _slug_db(domain: str) -> str:
    return "gf_" + re.sub(r"[^a-z0-9]+", "_", domain.lower())[:40]


def _bake(text: str, filename: str = "") -> tuple[object, dict]:
    m = match_text(text, filename)
    title = (m.title or "").strip() or filename.replace(".txt", "") or "管理系统"
    theme = default_theme(m.domain) or ""
    spec = build_spec(
        title,
        m.archetype,
        m.domain,
        theme,
        False,
        "auto",
        float(m.confidence or 0.8),
        list(m.hits or []),
        proposal={"excerpt": text, "text": text},
        archetypes=list(m.archetypes or [m.archetype]),
    )
    return m, spec


class DomainOpeningCorpusTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.data = json.loads(CORPUS.read_text(encoding="utf-8"))
        cls.samples = cls.data["samples"]
        cls.by_domain = {s["domain"]: s for s in cls.samples}

    def test_era_meta(self) -> None:
        self.assertEqual(self.data["_meta"]["era"], "2021-2026")
        for s in self.samples:
            self.assertGreaterEqual(s["year"], 2021, s["domain"])
            self.assertLessEqual(s["year"], 2026, s["domain"])

    def test_covers_every_named_domain(self) -> None:
        missing = [d for d in NAMED if d not in self.by_domain]
        self.assertEqual(missing, [], f"缺开题缩样: {missing}")
        extra = [d for d in self.by_domain if d not in NAMED]
        self.assertEqual(extra, [], f"未知域: {extra}")

    def test_each_sample_bakes_business_deliverables(self) -> None:
        """匹配对域 + accept full + schema/SQL/模块图/测试表可生成且能力对齐。"""
        for s in self.samples:
            with self.subTest(domain=s["domain"], title=s["title"]):
                self._assert_named_deliverables(s)

    def test_generic_fallback_bakes_crud_shell(self) -> None:
        g = self.data["generic"]
        m, spec = _bake(g["text"], f"{g['title']}.txt")
        self.assertEqual(m.domain, "DOM-GENERIC", f"hits={m.hits[:12]}")
        self.assertEqual(spec.get("accept"), "full", spec.get("accept_reason"))
        good, errs = validate_schema(spec.get("schema"))
        self.assertTrue(good, errs[:5])
        caps = set(spec.get("capabilities") or [])
        self.assertTrue({"archive", "content", "org_users"} <= caps, caps)
        sql = domain_sql(
            "DOM-GENERIC",
            _slug_db("DOM-GENERIC"),
            m.archetype,
            list(m.archetypes or [m.archetype]),
            capabilities=list(caps),
            proposal_text=g["text"],
        )
        assert_table_budget(sql, "generic-opening")
        self.assertIn("CREATE TABLE", sql.upper())
        schema = spec["schema"]
        mod = module_model(schema, proposal_text=g["text"], title_fallback=g["title"])
        self.assertTrue(mod and iter_nodes(mod), mod)
        rows = build_testcase_rows(schema)
        self.assertGreaterEqual(len(rows), 3, rows[:2])

    def _assert_named_deliverables(self, s: dict) -> None:
        want = s["domain"]
        text = s["text"]
        m, spec = _bake(text, f"{s['title']}.txt")
        self.assertEqual(m.domain, want, f"arch={m.archetype} hits={m.hits[:12]}")
        self.assertEqual(
            spec.get("domain"),
            want,
            f"spec.domain drift accept={spec.get('accept')}",
        )
        self.assertEqual(
            spec.get("accept"),
            "full",
            f"reason={spec.get('accept_reason')} oos={spec.get('out_of_mvp_signals')}",
        )

        schema = spec.get("schema") or {}
        good, errs = validate_schema(schema)
        self.assertTrue(good, errs[:6])

        need = set(DOMAIN_CAPABILITIES.get(want) or [])
        caps = set(spec.get("capabilities") or [])
        self.assertTrue(
            need <= caps,
            f"{want} missing caps {need - caps}; have={sorted(caps)}",
        )

        # 业务 runtime 表应进 SQL（档案/单据/订单/预约）
        rt = dict((DOMAINS.get(want) or {}).get("runtime") or {})
        sql = domain_sql(
            want,
            _slug_db(want),
            m.archetype,
            list(m.archetypes or [m.archetype]),
            capabilities=list(caps),
            proposal_text=text,
            ticket_table=rt.get("ticket_table"),
        )
        assert_table_budget(sql, want)
        sql_l = sql.lower()
        for key in (
            "archive_item_table",
            "ticket_table",
            "order_table",
            "reservation_table",
            "slot_table",
        ):
            table = rt.get(key)
            if not table:
                continue
            self.assertIn(
                str(table).lower(),
                sql_l,
                f"{want} SQL 缺 runtime.{key}={table}",
            )
        if "archive_log" in need:
            self.assertIn("archive_log", sql_l, f"{want} 应含 archive_log 表")
        if "favorites" in need:
            self.assertTrue(
                "favorite" in sql_l or "user_favorite" in sql_l,
                f"{want} 应含收藏表",
            )

        # 模块图 / 测试用例表（论文交付物骨架）
        mod = module_model(schema, proposal_text=text, title_fallback=s["title"])
        self.assertIsNotNone(mod)
        nodes = iter_nodes(mod)
        self.assertGreaterEqual(len(nodes), 4, f"{want} 模块图过瘦: {len(nodes)}")
        schema_blob = json.dumps(schema, ensure_ascii=False)
        mod_blob = json.dumps(mod, ensure_ascii=False)
        # 行业词应进菜单/文案（证明换皮交付，不是空壳英文）
        kws = list((DOMAINS[want].get("keywords") or [])[:10])
        self.assertTrue(
            any(k in schema_blob or k in mod_blob for k in kws),
            f"{want} schema/模块未见行业词 {kws[:5]}",
        )
        menus = schema.get("menus") if isinstance(schema.get("menus"), dict) else {}
        admin_keys = {
            str(m.get("key") or "")
            for m in (menus.get("admin") or [])
            if isinstance(m, dict)
        }
        if "archive" in need:
            self.assertTrue(
                any("archive" in k or k in {"category", "books"} for k in admin_keys)
                or "archive" in schema_blob,
                f"{want} 缺档案类菜单 keys={sorted(admin_keys)[:12]}",
            )
        if "ticket_flow" in need:
            self.assertTrue(
                any(
                    x in schema_blob
                    for x in ("ticket", "tickets", "borrow", "repair", "apply")
                ),
                f"{want} schema 未见单据痕迹",
            )
        if "order_lines" in need:
            self.assertTrue(
                any(x in schema_blob for x in ("order", "cart", "订单", "购物车", "点餐")),
                f"{want} schema 未见订单痕迹",
            )
        if "slot_reserve" in need:
            self.assertTrue(
                any(x in schema_blob for x in ("reserve", "slot", "预约", "挂号")),
                f"{want} schema 未见预约痕迹",
            )

        rows = build_testcase_rows(schema)
        self.assertGreaterEqual(len(rows), 5, f"{want} 测试表过少: {len(rows)}")
        if need & {"ticket_flow", "order_lines", "slot_reserve"}:
            row_blob = json.dumps(rows, ensure_ascii=False)
            self.assertTrue(
                any(
                    k in row_blob
                    for k in (
                        "审核",
                        "申请",
                        "工单",
                        "订单",
                        "预约",
                        "报名",
                        "借阅",
                        "下单",
                        "投递",
                        "请假",
                        "报修",
                        "取件",
                    )
                )
                or len(rows) >= 8,
                f"{want} 测试表缺少流转类用例痕迹",
            )


if __name__ == "__main__":
    unittest.main()
