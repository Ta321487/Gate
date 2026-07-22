"""伪开题压测：单路径 + 多主路径并集；L3 → degraded。"""
from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.bake.capabilities import resolve_accept, scan_out_of_scope
from app.bake.catalog import build_spec, match_text
from app.bake.domain_schema import baseline_runtime_covers, required_capabilities
from app.bake.engine import assert_table_budget, domain_sql

# title, 主要功能, 期望 archetypes 超集（实际可多不可少关键族）
CASES: list[tuple[str, str, set[str]]] = [
    (
        "基于SpringBoot的学生公寓管理系统的设计与实现",
        "1. 学生提交宿舍报修工单\n2. 宿管审核派单与维修回访\n3. 公告与用户管理",
        {"ARCH-FLOW"},
    ),
    (
        "房屋租赁信息管理系统的设计与实现",
        "1. 房源档案维护\n2. 租客在线预约看房时段与改约\n3. 租赁意向申请与管理员审核",
        {"ARCH-RESERVE", "ARCH-FLOW"},
    ),
    (
        "社区助餐与场次预约综合平台的设计与实现",
        "1. 菜品浏览购物车下单与订单配送\n2. 助餐窗口时段预约\n3. 公告管理",
        {"ARCH-TRADE", "ARCH-RESERVE"},
    ),
    (
        "实验室耗材领用与采购下单系统的设计与实现",
        "1. 耗材档案与库存\n2. 领用申请审核\n3. 采购购物车下单",
        {"ARCH-FLOW", "ARCH-TRADE"},
    ),
    (
        "体育馆综合服务平台的设计与实现",
        "1. 场馆时段预约\n2. 器材借用申请审核\n3. 饮品购物车下单",
        {"ARCH-RESERVE", "ARCH-FLOW", "ARCH-TRADE"},
    ),
    (
        "特色农产品销售平台的设计与实现",
        "1. 商品浏览与分类\n2. 购物车下单与订单管理\n3. 后台商品与库存维护",
        {"ARCH-TRADE"},
    ),
    (
        "基于微信小程序的食堂点餐系统的设计与实现",
        "1. 菜品浏览与购物车下单\n2. 订单状态跟踪\n技术路线：微信小程序 + SpringBoot",
        {"ARCH-TRADE"},
    ),
]


def wrap(title: str, features: str) -> str:
    return (
        f"题目：{title}\n\n"
        f"一、研究背景\n传统方式效率低。\n\n"
        f"二、主要功能\n{features}\n\n"
        f"三、技术路线\nSpring Boot + Vue + MySQL。\n"
    )


def main() -> None:
    print(f"cases={len(CASES)}")
    ok = 0
    c_acc: Counter[str] = Counter()
    for title, feats, expect in CASES:
        text = wrap(title, feats)
        m = match_text(text)
        arches = list(m.archetypes or [m.archetype])
        spec = build_spec(
            m.title,
            m.archetype,
            m.domain,
            "",
            False,
            "auto",
            m.confidence,
            m.hits,
            proposal={"excerpt": text},
            archetypes=arches,
        )
        req = list(
            spec.get("capabilities")
            or required_capabilities(spec["domain"], spec.get("archetype"), arches)
        )
        base = baseline_runtime_covers(spec["domain"], spec.get("archetype"), arches)
        acc = resolve_accept(
            req,
            text,
            has_domain_overlay=spec["domain"] == "DOM-LIBRARY",
            has_baseline_runtime=base,
        )
        c_acc[acc["accept"]] += 1
        oos = scan_out_of_scope(text)
        got = set(spec.get("archetypes") or arches)
        arch_ok = expect <= got
        if oos:
            principle_ok = acc["accept"] == "degraded" and arch_ok
        else:
            principle_ok = acc["accept"] == "full" and arch_ok
        if spec["domain"] == "DOM-GENERIC":
            sql = domain_sql(
                "DOM-GENERIC", "gf_stress", spec.get("archetype"), spec.get("archetypes")
            )
            try:
                assert_table_budget(sql, "GENERIC")
            except AssertionError as e:
                principle_ok = False
                print(f"SQL {e}")
        ok += int(principle_ok)
        mark = "OK" if principle_ok else "FAIL"
        print(
            f"{mark:4} {m.domain:14} arches={sorted(got)} {acc['accept']:8} "
            f"expect>={sorted(expect)} oos={oos}"
        )
        print(f"     caps={spec.get('capabilities')}")
        if not principle_ok:
            print(f"     !! got={got} hits={m.hits[:8]}")

    print(f"\nprinciple_ok={ok}/{len(CASES)} accept={dict(c_acc)}")


if __name__ == "__main__":
    main()
