"""单路径 / 具体 DOM 回归：多主路径改动后不应误伤。"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.bake.capabilities import resolve_accept
from app.bake.catalog import build_spec, match_text
from app.bake.domain_schema import baseline_runtime_covers, required_capabilities
from app.bake.engine import assert_table_budget, domain_sql

CASES = [
    ("基于SpringBoot的学院图书借阅管理系统的设计与实现", "DOM-LIBRARY", {"ARCH-FLOW"}),
    ("基于SpringBoot的学生选课系统的设计与实现", "DOM-COURSE", {"ARCH-FLOW"}),
    ("基于SpringBoot的网上商城系统的设计与实现", "DOM-SHOP", {"ARCH-TRADE"}),
    ("基于SpringBoot的小型餐厅点餐系统的设计与实现", "DOM-FOOD", {"ARCH-TRADE"}),
    ("基于SpringBoot的会议室预约管理系统的设计与实现", "DOM-MEETING", {"ARCH-RESERVE"}),
    ("基于SpringBoot的宿舍报修管理系统的设计与实现", "DOM-DORM", {"ARCH-FLOW"}),
    ("基于SpringBoot的失物招领系统的设计与实现", "DOM-LOST", {"ARCH-FLOW"}),
    ("基于SpringBoot的个人博客系统的设计与实现", "DOM-BLOG", {"ARCH-CONTENT"}),
    ("基于SpringBoot的临沂大学实验室预约管理系统的设计与实现", "DOM-GENERIC", {"ARCH-RESERVE"}),
    ("基于SpringBoot的后勤报修管理系统的设计与实现", "DOM-GENERIC", {"ARCH-FLOW"}),
    ("基于SpringBoot的跳蚤市场交易平台的设计与实现", "DOM-GENERIC", {"ARCH-TRADE"}),
    ("基于SpringBoot的学生管理系统的设计与实现", "DOM-GENERIC", {"ARCH-CRUD"}),
    ("基于SSM的图书馆座位预约管理系统的设计与实现", "DOM-GENERIC", {"ARCH-RESERVE"}),
]


def main() -> None:
    ok = 0
    for title, exp_dom, exp_arch in CASES:
        m = match_text(title)
        arches = set(m.archetypes or [m.archetype])
        arch_ok = exp_arch <= arches
        unexpected = set()
        if "ARCH-TRADE" not in exp_arch and "ARCH-TRADE" in arches:
            if not any(k in title for k in ("交易", "二手", "商城", "点餐", "订餐", "购物", "销售")):
                unexpected.add("TRADE")
        if "ARCH-RESERVE" not in exp_arch and "ARCH-RESERVE" in arches:
            if not any(k in title for k in ("预约", "预订", "挂号", "停车", "座位", "包厢")):
                unexpected.add("RESERVE")
        spec = build_spec(
            m.title,
            m.archetype,
            m.domain,
            "",
            False,
            "auto",
            m.confidence,
            m.hits,
            archetypes=list(m.archetypes or [m.archetype]),
        )
        req = list(
            spec.get("capabilities")
            or required_capabilities(
                spec["domain"], spec.get("archetype"), list(m.archetypes or [])
            )
        )
        base = baseline_runtime_covers(
            spec["domain"], spec.get("archetype"), list(m.archetypes or [])
        )
        acc = resolve_accept(
            req,
            title,
            has_domain_overlay=spec["domain"] == "DOM-LIBRARY",
            has_baseline_runtime=base,
        )
        sql_ok = True
        if m.domain == "DOM-GENERIC":
            try:
                assert_table_budget(
                    domain_sql(
                        "DOM-GENERIC", "t", m.archetype, list(m.archetypes or [])
                    ),
                    "g",
                )
            except Exception:
                sql_ok = False
        good = (
            m.domain == exp_dom
            and arch_ok
            and acc["accept"] == "full"
            and sql_ok
            and not unexpected
        )
        ok += int(good)
        mark = "OK" if good else "FAIL"
        print(
            f"{mark} dom={m.domain} exp={exp_dom} arch={sorted(arches)} "
            f"acc={acc['accept']} unexpected={sorted(unexpected)}"
        )
        if not good:
            print(" ", title[:52], "hits=", m.hits[:6])
    print(f"\nregression {ok}/{len(CASES)}")


if __name__ == "__main__":
    main()
