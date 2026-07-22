"""第三批真实选题压测（jkcode 2025 清单 + 公开 GitHub 题名，尽量不与前两批重复）。

来源：
- JK: https://jkcode.blog.csdn.net/article/details/140872543
- GD: gdutxujun94/GraduationProject README 列举题
- ES: 666bears/E-Shop 网上商城案
"""
from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.bake.capabilities import resolve_accept
from app.bake.catalog import build_spec, match_text
from app.bake.domain_schema import baseline_runtime_covers, required_capabilities

TOPICS: list[tuple[str, str]] = [
    ("JK", "基于SpringBoot的在线拍卖系统的设计与实现"),
    ("JK", "基于SpringBoot的医护人员排班系统的设计与实现"),
    ("JK", "SpringBoot网页时装购物系统的设计与实现"),
    ("JK", "基于SpringBoot的网上订餐系统的设计与实现"),
    ("JK", "大学生租房平台的设计与实现"),
    ("JK", "SpringBoot房屋租赁系统的设计与实现"),
    ("JK", "大学生入学审核系统的设计与实现"),
    ("JK", "基于SpringBoot的课程作业管理系统的设计与实现"),
    ("JK", "基于SpringBoot的社区团购系统的设计与实现"),
    ("JK", "在线视频教育平台的设计与实现"),
    ("JK", "SpringBoot房产销售系统的设计与实现"),
    ("JK", "SpringBoot母婴商城的设计与实现"),
    ("JK", "基于Java的免税商品优选购物商城的设计与实现"),
    ("JK", "学生宿舍管理系统的设计与开发"),
    ("JK", "SpringBoot网上超市的设计与实现"),
    ("JK", "SpringBoot网上点餐系统的设计与实现"),
    ("JK", "基于springboot的网上购物商城系统的设计与实现"),
    ("JK", "springboot阿博图书馆管理系统的设计与实现"),
    ("JK", "在线商城系统设计与开发"),
    ("JK", "海滨体育馆管理系统的设计与实现"),
    ("JK", "SpringBoot的墙绘产品展示交易平台的设计与实现"),
    ("JK", "SpringBoot的网上租赁系统的设计与实现"),
    ("JK", "SpringBoot社区医院信息平台的设计与实现"),
    ("JK", "基于springboot的衣依服装销售平台的设计与实现"),
    ("JK", "SpringBoot美容院管理系统的设计与实现"),
    ("JK", "springboot新闻推荐系统的设计与实现"),
    ("JK", "springboot古典舞在线交流平台的设计与实现"),
    ("JK", "springboot校园资料分享平台的设计与实现"),
    ("JK", "景区民宿预约系统的设计与实现"),
    ("JK", "基于java的公寓报修管理系统的设计与实现"),
    ("JK", "springboot学生选课系统的设计与实现"),
    ("JK", "基于SpringBoot的医护人员排班与号源预约系统的设计与实现"),
    ("GD", "springboot私人健身与教练预约管理系统的设计与实现"),
    ("GD", "springboot乒乓球预约管理系统的设计与实现"),
    ("GD", "沁园健身房预约管理系统的设计与实现"),
    ("GD", "springboot校园在线拍卖系统的设计与实现"),
    ("GD", "家具商城系统的设计与实现"),
    ("GD", "学生选课系统的设计与实现"),
    ("GD", "福聚苑社区团购系统的设计与实现"),
    ("GD", "医患档案管理系统的设计与实现"),
    ("ES", "基于SpringBoot Vue的网上商城系统的设计与实现"),
    ("JK", "基于微信的设备故障报修管理系统的设计与实现"),
    ("JK", "基于微信小程序的在线选课系统的设计与实现"),
    ("JK", "校园二手平台的设计与实现"),
    ("JK", "ssm医院门诊挂号系统的设计与实现"),
    ("JK", "会议室管理与预约系统的设计与实现"),
    ("JK", "少儿编程网上报名系统的设计与实现"),
    ("JK", "新能源汽车在线租赁管理系统的设计与实现"),
    ("JK", "健身房管理系统的设计与实现"),
    ("JK", "校园驿站管理系统的设计与实现"),
    ("JK", "实验室耗材管理系统的设计与实现"),
    ("JK", "学生请假系统的设计与实现"),
    ("JK", "家居商城系统的设计与实现"),
    ("JK", "基于Java的图书管理系统的设计与实现"),
    ("JK", "ssm博客系统的设计与实现"),
    # 综合多路径题（开题常写两条以上）
    ("MIX", "高校体育馆预约与器材借用审核系统的设计与实现"),
    ("MIX", "社区团购下单与自提点时段预约系统的设计与实现"),
    ("MIX", "公寓报修派单与楼栋会议室预约系统的设计与实现"),
    ("MIX", "图书馆座位预约与图书借阅审核系统的设计与实现"),
    ("MIX", "校园二手交易与失物招领审核系统的设计与实现"),
]


def synth_body(title: str) -> str:
    """按题名粗生成「主要功能」，模拟真实开题会写清干什么。"""
    lines = ["题目：" + title, "", "二、主要功能"]
    n = 1
    if any(k in title for k in ("预约", "预订", "挂号", "排班", "占座", "座位", "泊车", "停车")):
        lines.append(f"{n}. 用户选择资源与时段进行预约/改约")
        n += 1
    if any(k in title for k in ("报修", "保修", "借阅", "审核", "请假", "报名", "申请", "招领", "派单")):
        lines.append(f"{n}. 用户提交申请单据，管理员审核处理")
        n += 1
    if any(
        k in title
        for k in ("商城", "购物", "点餐", "订餐", "团购", "拍卖", "二手", "销售", "交易", "超市", "租赁")
    ):
        lines.append(f"{n}. 商品/服务浏览、购物车下单与订单管理")
        n += 1
    if any(k in title for k in ("选课",)):
        lines.append(f"{n}. 课程检索与选课申请，管理员审核")
        n += 1
    if any(k in title for k in ("博客", "论坛", "交流", "分享", "资讯", "新闻", "视频")):
        lines.append(f"{n}. 内容发布与浏览收藏")
        n += 1
    if n == 1:
        lines.append("1. 业务信息维护、查询与用户权限管理")
        lines.append("2. 公告发布")
    lines += ["", "三、技术路线", "Spring Boot + Vue + MySQL"]
    return "\n".join(lines)


def run(label: str, with_body: bool) -> None:
    print(f"\n######## {label} n={len(TOPICS)} ########")
    c_dom: Counter[str] = Counter()
    c_arch: Counter[str] = Counter()
    c_acc: Counter[str] = Counter()
    multi = 0
    for src, title in TOPICS:
        text = synth_body(title) if with_body else title
        m = match_text(text)
        arches = list(m.archetypes or [m.archetype])
        if len(arches) > 1:
            multi += 1
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
        c_dom[spec["domain"]] += 1
        for a in arches:
            c_arch[a] += 1
        c_acc[acc["accept"]] += 1
        print(
            f"{src:3} {spec['domain']:14} {','.join(arches):28} {acc['accept']:8} | {title[:42]}"
        )

    print(f"multi_arch_topics={multi}/{len(TOPICS)}")
    print("domain:", dict(c_dom.most_common(12)))
    print("arch hits:", dict(c_arch.most_common()))
    print("accept:", dict(c_acc))


def main() -> None:
    run("TITLE_ONLY", with_body=False)
    run("TITLE+SYNTH_BODY", with_body=True)


if __name__ == "__main__":
    main()
