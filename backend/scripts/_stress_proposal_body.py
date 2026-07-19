"""用「题名 + 伪开题主要功能」压测：开题提到的行为应落到可交付壳；小程序等 L3 → degraded。"""
from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.bake.capabilities import resolve_accept, scan_out_of_scope
from app.bake.catalog import build_spec, match_text
from app.bake.domain_schema import baseline_runtime_covers, required_capabilities

# 与真实题库不重复的一组「题名干、正文写清干什么」
CASES: list[tuple[str, str, str]] = [
    # title, 主要功能正文, 期望 arch 前缀或 exact
    (
        "基于SpringBoot的学生公寓管理系统的设计与实现",
        "1. 学生提交宿舍报修工单\n2. 宿管审核派单与维修回访\n3. 公告与用户管理",
        "ARCH-FLOW",
    ),
    (
        "springboot大学生竞赛管理系统的设计与实现",
        "1. 发布竞赛项目\n2. 学生在线报名并递交材料\n3. 管理员审核与结果公示",
        "ARCH-FLOW",
    ),
    (
        "基于SpringBoot的高校教师科研管理系统的设计与实现",
        "1. 科研成果信息维护与查询\n2. 分类统计与台账导出\n3. 用户权限与公告",
        "ARCH-CRUD",
    ),
    (
        "特色农产品销售平台的设计与实现",
        "1. 商品浏览与分类\n2. 购物车下单与订单管理\n3. 后台商品与库存维护",
        "ARCH-TRADE",
    ),
    (
        "校园顺风车信息平台的设计与实现",
        "1. 发布出行信息\n2. 乘客报名与车主确认审核\n3. 行程状态流转与评价登记",
        "ARCH-FLOW",
    ),
    (
        "宠物领养登记平台的设计与实现",
        "1. 待领养宠物档案维护\n2. 用户提交领养申请\n3. 管理员审核通过或驳回",
        "ARCH-FLOW",
    ),
    (
        "健身房会员与课程管理系统的设计与实现",
        "1. 课程与教练档案\n2. 会员预约团课时段\n3. 取消预约与签到登记",
        "ARCH-RESERVE",
    ),
    (
        "应急救援物资管理系统的设计与实现",
        "1. 物资入库出库与盘点\n2. 库存预警\n3. 领用申请与审批",
        "ARCH-STOCK",  # 或 FLOW；STOCK 优先若出库入库命中
    ),
    (
        "基于微信小程序的食堂点餐系统的设计与实现",
        "1. 菜品浏览与购物车下单\n2. 订单状态跟踪\n技术路线：微信小程序 + SpringBoot",
        "ARCH-TRADE",  # accept 应为 degraded
    ),
    (
        "基于人脸识别的图书馆座位预约系统的设计与实现",
        "1. 座位时段预约与占座\n2. 刷脸进馆核验\n3. 违约记次",
        "ARCH-RESERVE",
    ),
    (
        "三人行旧书交流网站的设计与实现",
        "1. 旧书信息发布\n2. 二手交换意向与成交登记\n3. 线下交接确认",
        "ARCH-TRADE",
    ),
    (
        "房屋租赁信息管理系统的设计与实现",
        "1. 房源档案维护\n2. 租客在线预约看房时段与改约\n3. 房东确认或取消预约",
        "ARCH-RESERVE",
    ),
]


def wrap(title: str, features: str) -> str:
    return (
        f"题目：{title}\n\n"
        f"一、研究背景\n传统方式效率低，需要信息化系统。\n\n"
        f"二、主要功能\n{features}\n\n"
        f"三、技术路线\nSpring Boot + Vue + MySQL。\n"
    )


def main() -> None:
    print(f"cases={len(CASES)}")
    ok = 0
    c_acc: Counter[str] = Counter()
    for title, feats, expect_arch in CASES:
        text = wrap(title, feats)
        m = match_text(text)
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
        )
        req = list(
            spec.get("capabilities")
            or required_capabilities(spec["domain"], spec.get("archetype"))
        )
        base = baseline_runtime_covers(spec["domain"], spec.get("archetype"))
        acc = resolve_accept(
            req,
            text,
            has_domain_overlay=spec["domain"] == "DOM-LIBRARY",
            has_baseline_runtime=base,
        )
        c_acc[acc["accept"]] += 1
        oos = scan_out_of_scope(text)
        arch_ok = m.archetype == expect_arch or (
            expect_arch == "ARCH-STOCK" and m.archetype in ("ARCH-STOCK", "ARCH-FLOW")
        )
        # 原则：非 L3 → full；L3 → degraded；且行为原型要对
        if oos:
            principle_ok = acc["accept"] == "degraded" and arch_ok
        else:
            principle_ok = acc["accept"] == "full" and arch_ok
        ok += int(principle_ok)
        mark = "OK" if principle_ok else "FAIL"
        print(
            f"{mark:4} {m.domain:14} {m.archetype:12} {acc['accept']:8} "
            f"expect={expect_arch} oos={oos}"
        )
        print(f"     {title[:48]}")
        print(f"     hits={m.hits[:8]}")
        if not principle_ok:
            print(f"     !! miss={acc.get('missing_capabilities')} reason={acc.get('reason')}")

    print(f"\nprinciple_ok={ok}/{len(CASES)} accept={dict(c_acc)}")


if __name__ == "__main__":
    main()
