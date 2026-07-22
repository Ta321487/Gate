"""抽检：匹配是否合理 + 交付主线是否够「毕设厚度」。

厚度定义（答辩能讲的）：
- thick：有 ticket_flow / order_lines / slot_reserve 之一（单据/订单/预约）
- medium：仅 archive+content（纯台账），但题名本身就是档案/展示类
- thin_risk：题名暗示审批/交易/预约/进销存/CRM，实际却落成纯 CRUD
"""
from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.bake.capabilities import resolve_accept, scan_out_of_scope
from app.bake.catalog import build_spec, match_text
from app.bake.domain_schema import baseline_runtime_covers, required_capabilities

# 并集：真实题 + 常见「怕太薄」类（CRM/ERP/人事/教务）
TOPICS: list[tuple[str, str]] = [
    # --- 预约 ---
    ("R", "高校会议室预约管理系统的设计与实现"),
    ("R", "HPV疫苗预约系统的设计与实现"),
    ("R", "基于SpringBoot的小区智能泊车系统的设计与实现"),
    ("R", "Java酒店管理系统的设计与实现"),
    ("R", "SpringBoot美容院管理系统的设计与实现"),
    # --- 交易 ---
    ("R", "高校饭堂点餐系统的设计与实现"),
    ("R", "Springboot二手商品交易平台的设计与实现"),
    ("R", "Free商城系统的设计与实现"),
    ("R", "基于web的办公用品网上销售管理系统的设计与实现"),
    ("R", "社区团购系统的设计与实现"),
    # --- 借阅/报修/报名 ---
    ("R", "图书借阅管理系统的设计与实现"),
    ("R", "基于java的公寓报修管理系统的设计与实现"),
    ("R", "springboot学生选课系统的设计与实现"),
    ("R", "Java校园志愿者服务平台的设计与实现"),
    ("R", "失物招领管理系统的设计与实现"),
    # --- 设备/物资/进销存 ---
    ("R", "SpringBoot技术的实验室管理系统的设计与实现"),
    ("R", "实验室耗材管理系统的设计与实现"),
    ("R", "java建筑材料仓库管理系统的设计与实现"),
    ("R", "基于Spring Boot的库存管理系统的设计与实现"),
    ("R", "springboot的图书进销存管理系统的设计与实现"),
    ("R", "固定资产领用与耗材申领管理系统的设计与实现"),
    ("R", "Vue的应急救援物资管理系统的设计与实现"),
    # --- 内容社区 ---
    ("R", "SpringBoot的论坛系统的设计与实现"),
    ("R", "springboot个人博客系统的设计与实现"),
    ("R", "springboot电影评论网站系统的设计与实现"),
    ("R", "springboot光影视频平台的设计与实现"),
    # --- 综合多路径 ---
    ("M", "高校体育馆预约与器材借用审核系统的设计与实现"),
    ("M", "公寓报修派单与楼栋会议室预约系统的设计与实现"),
    ("M", "校园二手交易与失物招领审核系统的设计与实现"),
    ("M", "图书馆座位预约与图书借阅审核系统的设计与实现"),
    # --- CRM / ERP / 人事 / 教务（用户担心太薄的类）---
    ("X", "基于SpringBoot的客户关系管理系统的设计与实现"),
    ("X", "中小企业CRM客户跟进管理系统的设计与实现"),
    ("X", "销售线索与客户跟进管理系统的设计与实现"),
    ("X", "企业进销存管理系统的设计与实现"),
    ("X", "中小企业ERP进销存模块的设计与实现"),
    ("X", "人力资源管理系统的设计与实现"),
    ("X", "企业员工考勤与请假管理系统的设计与实现"),
    ("X", "springboot公司日常考勤系统的设计与实现"),
    ("X", "Springboot党支部信息管理系统的设计与实现"),
    ("X", "springboot高校教师科研管理系统的设计与实现"),
    ("X", "医患档案管理系统的设计与实现"),
    ("X", "学生学籍档案管理系统的设计与实现"),
    ("X", "网吧管理系统的设计与实现"),
    ("X", "NBA球星管理系统的设计与实现"),
    # --- L3 擦边 ---
    ("L3", "基于微信小程序的体育场馆预约管理系统的设计与实现"),
    ("L3", "python电影推荐协同过滤算法的设计与实现"),
    ("L3", "Springcloud的聚合支付系统的设计与实现"),
]

FLOW_HINT = (
    "预约", "预订", "挂号", "占座", "泊车", "停车",
    "报修", "借阅", "审核", "请假", "报名", "申请", "招领", "派单", "跟进", "受理",
    "申领", "领用", "出库", "入库", "进销存", "采购", "盘点",
)
TRADE_HINT = ("商城", "购物", "点餐", "订餐", "团购", "拍卖", "二手", "销售", "交易", "超市", "租赁", "下单")
RESERVE_HINT = ("预约", "预订", "挂号", "占座", "泊车", "停车", "排班")
CRM_HINT = ("CRM", "客户关系", "客户跟进", "销售线索", "客户管理")
ERP_HINT = ("ERP", "进销存", "多仓")
ARCHIVE_OK = ("档案", "信息管理", "球星", "党支部", "科研", "学籍", "网吧")  # 题名本身偏台账也可接受


def title_expects(title: str) -> set[str]:
    exp: set[str] = set()
    if any(k in title for k in FLOW_HINT) or any(k in title for k in CRM_HINT):
        exp.add("flow")
    if any(k in title for k in TRADE_HINT):
        exp.add("trade")
    if any(k in title for k in RESERVE_HINT):
        exp.add("reserve")
    if any(k in title for k in ERP_HINT) or "库存" in title or "仓库" in title or "物资" in title:
        exp.add("stockish")
    return exp


def delivered_paths(caps: list[str]) -> set[str]:
    d: set[str] = set()
    if "ticket_flow" in caps:
        d.add("flow")
    if "order_lines" in caps:
        d.add("trade")
    if "slot_reserve" in caps:
        d.add("reserve")
    if "quota" in caps and "ticket_flow" in caps:
        d.add("stockish")
    return d


def synth_body(title: str) -> str:
    lines = ["题目：" + title, "", "二、主要功能"]
    n = 1
    exp = title_expects(title)
    if "reserve" in exp:
        lines.append(f"{n}. 用户选择资源与时段进行预约")
        n += 1
    if "flow" in exp:
        lines.append(f"{n}. 用户提交申请/跟进单据，管理员审核处理")
        n += 1
    if "trade" in exp:
        lines.append(f"{n}. 商品浏览、购物车下单与订单管理")
        n += 1
    if "stockish" in exp:
        lines.append(f"{n}. 库存台账与出入库/申领审核")
        n += 1
    if n == 1:
        lines.append("1. 业务对象检索与后台维护")
        lines.append("2. 用户注册登录与公告")
    lines.append("")
    lines.append("三、研究内容")
    lines.append("实现上述主流程的 Web 管理端与用户端。")
    return "\n".join(lines)


def verdict(title: str, caps: list[str], domain: str, arch: str) -> str:
    exp = title_expects(title)
    got = delivered_paths(caps)
    has_biz = bool(got & {"flow", "trade", "reserve"})

    if any(k in title for k in ("小程序", "协同过滤", "聚合支付", "微信支付", "人脸")):
        return "oos_ok"  # L3 擦边，degraded 预期内

    if not exp:
        # 题名偏档案：CRUD 可接受，但标 soft
        if has_biz:
            return "ok_thick"
        if any(k in title for k in ARCHIVE_OK) or domain == "DOM-GENERIC" and arch == "ARCH-CRUD":
            return "ok_archive"
        return "soft_crud"  # 「XX管理系统」无行为词 → 易偏薄

    missing = exp - got
    # stockish 可用 flow+quota 满足
    if "stockish" in missing and ("flow" in got or "stockish" in got):
        missing.discard("stockish")
    # CRM 期望 flow
    if missing:
        return "thin_risk"
    if has_biz:
        return "ok_thick"
    return "thin_risk"


def main() -> None:
    counts: Counter[str] = Counter()
    by_verdict: dict[str, list[str]] = {k: [] for k in (
        "ok_thick", "ok_archive", "soft_crud", "thin_risk", "oos_ok", "reject", "degraded"
    )}
    labels_weak: list[str] = []

    for src, title in TOPICS:
        text = synth_body(title)
        m = match_text(text)
        req = required_capabilities(m.domain, m.archetype, archetypes=m.archetypes)
        acc = resolve_accept(
            req,
            text,
            has_baseline_runtime=baseline_runtime_covers(
                m.domain, m.archetype, archetypes=m.archetypes
            ),
        )
        spec = build_spec(
            title=m.title or title,
            archetype=m.archetype,
            domain=m.domain,
            theme="default",
            llm_enabled=False,
            match_mode="audit",
            confidence=m.confidence,
            hits=m.hits,
            proposal={"excerpt": text},
            archetypes=m.archetypes,
        )
        schema = spec.get("schema") or {}
        caps = list(schema.get("capabilities") or req)
        labels = schema.get("labels") or {}
        arch_ent = (schema.get("entities") or {}).get("archive") or {}
        ticket = (schema.get("entities") or {}).get("ticket") or {}

        v = verdict(title, caps, m.domain, m.archetype)
        if acc["accept"] == "reject":
            v = "reject"
        elif acc["accept"] == "degraded" and v not in ("thin_risk",):
            v = "degraded" if v != "oos_ok" else "oos_ok"

        counts[v] += 1
        arches = ",".join(m.archetypes or [m.archetype])
        line = (
            f"[{src}] {title[:42]}\n"
            f"     → {m.domain}/{arches} accept={acc['accept']} caps={caps}\n"
            f"     → archive={arch_ent.get('label')} ticket={ticket.get('label') or '-'} "
            f"app={labels.get('appName')}"
        )
        by_verdict.setdefault(v, []).append(line)

        # 文案假：仍叫业务对象
        if arch_ent.get("label") in ("业务对象", "对象", None) and m.domain == "DOM-GENERIC":
            labels_weak.append(line)

    print("=== 厚度抽检汇总 ===")
    for k in ("ok_thick", "ok_archive", "soft_crud", "thin_risk", "oos_ok", "degraded", "reject"):
        print(f"  {k:12} {counts[k]}")
    print(f"  total        {sum(counts.values())}")

    for key, title in (
        ("thin_risk", "主线偏薄（题名要流程，交付像 CRUD）"),
        ("soft_crud", "题名含糊、易落成纯台账"),
        ("ok_archive", "档案类可接受"),
        ("labels_weak", "GENERIC 文案仍偏假"),
    ):
        rows = labels_weak if key == "labels_weak" else by_verdict.get(key, [])
        if not rows:
            continue
        print(f"\n-- {title} ({len(rows)}) --")
        for r in rows[:20]:
            print(r)

    print("\n-- ok_thick 样例（前 8）--")
    for r in by_verdict.get("ok_thick", [])[:8]:
        print(r)


if __name__ == "__main__":
    main()
