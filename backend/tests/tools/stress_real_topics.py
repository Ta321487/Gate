"""近五年公开渠道真实选题压测（本批与上一批不重复）。

来源：
- YY25: 杨洋「2025 SpringBoot 选题」https://damodev.csdn.net/68639cf8b93e2f4179625159.html (2024-08)
- GH: OliverAAAAA/Code-Project 仓库列举的 SpringBoot 题名 (GitHub)
- CR: 666bears/Conference-Room 高校会议室预订 (2024-01)
- BSZK: 毕设智库「学生公寓管理系统」等公开案 https://www.itbszk.com/7765.html
"""
from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.bake.capabilities import resolve_accept
from app.bake.catalog import build_spec, domain_covers_archetype, match_text
from app.bake.domain_schema import baseline_runtime_covers, required_capabilities

# 全新一批：刻意避开上一轮 AMO/OWL/CSDN 已测题名
REAL_TOPICS: list[tuple[str, str]] = [
    # --- YY25 预约 / 占坑 ---
    ("YY25", "图书馆功能性包厢预约管理系统的设计与实现"),
    ("YY25", "基于SpringBoot的小区智能泊车系统的设计与实现"),
    ("YY25", "基于微信小程序的体育场馆预约管理系统的设计与实现"),
    ("YY25", "高校会议室预约管理系统的设计与实现"),
    ("YY25", "HPV疫苗预约系统的设计与实现"),
    ("YY25", "“纯萃”咖啡点单预约系统的设计与实现"),
    ("YY25", "万达广场停车管理系统的设计与实现"),
    ("YY25", "Android共享停车位系统的设计与实现"),
    ("CR", "基于SpringBoot Vue的高校会议室预订管理系统的设计与实现"),
    ("GH", "基于JAVA的图书馆预约占座系统的设计与实现"),
    ("GH", "基于SpringBoot的小型诊疗预约平台的设计与实现"),
    ("GH", "基于MVC框架自习室管理和预约系统的设计与实现"),
    # --- YY25 / GH 交易点餐二手 ---
    ("YY25", "高校饭堂点餐系统的设计与实现"),
    ("YY25", "Springboot二手商品交易平台的设计与实现"),
    ("YY25", "Java校园二手书城平台的设计与实现"),
    ("YY25", "Java校园二手书籍交易平台的设计与实现"),
    ("YY25", "基于Java的在线图书销售系统的设计与实现"),
    ("YY25", "基于web的办公用品网上销售管理系统的设计与实现"),
    ("YY25", "特色农产品销售系统的设计与实现"),
    ("YY25", "东莞市二手相机交易管理系统的设计与实现"),
    ("YY25", "“起拍拍”在线拍卖系统的设计与实现"),
    ("YY25", "Free商城系统的设计与实现"),
    ("YY25", "java螺蛳粉点餐管理系统的设计与实现"),
    ("YY25", "“每日鲜”水果直销网络系统的设计与实现"),
    ("GH", "SpringBoot网上点餐系统的设计与实现"),
    ("GH", "基于spring boot的餐厅点餐管理系统的设计与实现"),
    ("GH", "SpringBoot+VUE技术的智慧生活商城的设计与实现"),
    ("GH", "SpringBoot电商平台的设计与实现"),
    ("GH", "springboot欢迪迈手机商城的设计与开发"),
    # --- 报修 / 物业 / 请假 / 工单 ---
    ("YY25", "Java小区物业管理系统的设计与实现"),
    ("YY25", "Java学生请假管理分析系统的设计与实现"),
    ("YY25", "4S店汽车维修保养管理系统的设计与实现"),
    ("GH", "Spring boot的名城小区物业管理系统的设计与实现"),
    ("GH", "springboot大学城水电管理系统的设计与实现"),
    ("BSZK", "基于SpringBoot的学生公寓管理系统的设计与实现"),
    ("GH", "springboot宿舍管理系统的设计与实现"),
    # --- 图书借阅 ---
    ("YY25", "图书借阅管理系统的设计与实现"),
    ("YY25", "Java图书管理系统的设计与实现"),
    ("YY25", "三人行旧书网的设计与实现"),
    ("GH", "springboot阿博图书馆管理系统的设计与实现"),
    ("GH", "springboot的图书进销存管理系统的设计与实现"),
    # --- 内容社区 ---
    ("YY25", "MOBA类游戏论坛交流系统的设计与实现"),
    ("YY25", "“请君一笑”休闲论坛的设计与实现"),
    ("YY25", "IT学习交流平台的设计与实现"),
    ("YY25", "“城市书吧”线上阅读网站设计与实现"),
    ("GH", "SpringBoot的论坛系统的设计与实现"),
    ("GH", "springboot个人博客系统的设计与实现"),
    ("GH", "springboot电影评论网站系统的设计与实现"),
    ("GH", "springboot光影视频平台的设计与实现"),
    # --- 教务 / 竞赛 / 志愿 ---
    ("YY25", "SSM基于B/S的毕业设计题目管理系统的设计与实现"),
    ("YY25", "Springboot+Vue实习实训管理系统的设计与实现"),
    ("YY25", "Java校园志愿者服务平台的设计与实现"),
    ("YY25", "a市驾考管理系统的设计与实现"),
    ("GH", "springboot大学生竞赛管理系统的设计与实现"),
    ("GH", "springboot高校学科竞赛平台的设计与实现"),
    ("GH", "springboot的大创管理系统的设计与实现"),
    ("GH", "springboot-vue的毕业管理系统的设计与实现"),
    # --- 酒店民宿停车美容 ---
    ("YY25", "Java酒店管理系统的设计与实现"),
    ("GH", "springboot酒店管理系统的设计与实现"),
    ("GH", "springboot房屋租赁管理系统的设计与实现"),
    ("GH", "SpringBoot房屋租赁系统的设计与实现"),
    ("GH", "springboot健身房管理系统的设计与实现"),
    ("YY25", "360家政服务中心的家政服务管理系统的设计与实现"),
    # --- 设备 / 库存 / 资产 ---
    ("YY25", "java建筑材料仓库管理系统的设计与实现"),
    ("YY25", "Vue的应急救援物资管理系统的设计与实现"),
    ("GH", "SpringBoot+Vue的常规应急物资管理的设计与实现"),
    ("GH", "基于Spring Boot的库存管理系统的设计与实现"),
    ("GH", "SpringBoot技术的实验室管理系统的设计与实现"),
    # --- 纯 CRUD / 人事档案 ---
    ("YY25", "Springboot党支部信息管理系统的设计与实现"),
    ("YY25", "网吧管理系统的设计与实现"),
    ("YY25", "NBA球星管理系统的设计与实现"),
    ("GH", "springboot教师工作量管理系统的设计与实现"),
    ("GH", "springboot高校教师科研管理系统的设计与实现"),
    ("GH", "springboot公司日常考勤系统的设计与实现"),
    ("GH", "springboot精准扶贫管理系统的设计与实现"),
    # --- L3 擦边真实题 ---
    ("YY25", "Springcloud的聚合支付系统的设计与实现"),
    ("YY25", "python电影推荐协同过滤算法的设计与实现"),
    ("YY25", "基于微信小程序的体育场馆预约管理系统"),  # 小程序信号
    ("GH", "SpringBoot的秒杀系统的设计与实现"),
    ("YY25", "一种就业推荐系统的设计与实现"),
    # --- 跨域综合真实案 ---
    ("BSZK", "基于SpringBoot的学生公寓含二手商品与入住退宿审核系统的设计与实现"),
    ("YY25", "springboot校园顺风车平台的设计与实现"),
    ("YY25", "Java智慧社区养老服务系统的设计与实现"),
    ("YY25", "Java医院就医平台系统的设计与实现"),
    ("YY25", "Java医院诊疗系统的设计与实现"),
    ("GH", "SpringBoot的中山社区医疗综合服务的设计与实现"),
    ("GH", "springboot宠物领养系统的设计与实现"),
    ("YY25", "“爱宠”宠物用品商店的设计与实现"),
    ("GH", "springboot宠物咖啡馆平台的设计与实现"),
    ("YY25", "东湖学院教材征订的设计与实现"),
    ("YY25", "七八登山用品公司销售平台的设计与实现"),
]


def main() -> None:
    print(f"real_topics={len(REAL_TOPICS)} (fresh batch)")
    print(f"{'src':4} {'domain':14} {'arch':12} {'acc':8} | title")
    print("-" * 110)
    c_dom: Counter[str] = Counter()
    c_arch: Counter[str] = Counter()
    c_acc: Counter[str] = Counter()
    alerts: list[tuple] = []
    crud_only: list[str] = []
    degraded: list[str] = []
    demoted: list[str] = []

    for src, t in REAL_TOPICS:
        m = match_text(t)
        spec = build_spec(
            m.title,
            m.archetype,
            m.domain,
            "",
            False,
            "auto",
            m.confidence,
            m.hits,
            proposal={"excerpt": t},
        )
        req = list(
            spec.get("capabilities")
            or required_capabilities(spec["domain"], spec.get("archetype"))
        )
        base = baseline_runtime_covers(spec["domain"], spec.get("archetype"))
        acc = resolve_accept(
            req,
            t,
            has_domain_overlay=spec["domain"] == "DOM-LIBRARY",
            has_baseline_runtime=base,
        )
        c_dom[spec["domain"]] += 1
        c_arch[m.archetype] += 1
        c_acc[acc["accept"]] += 1
        print(f"{src:4} {spec['domain']:14} {m.archetype:12} {acc['accept']:8} | {t[:56]}")
        print(f"     hits={m.hits[:8]}")

        if m.domain != "DOM-GENERIC" and not domain_covers_archetype(m.domain, m.archetype):
            alerts.append(("DOM_ARCH_MISMATCH", t, m.domain, m.archetype))
        if any(h.startswith("dom↓") for h in m.hits):
            demoted.append(f"{m.archetype} | {t[:44]}")
        if m.archetype == "ARCH-CRUD" and acc["accept"] == "full":
            crud_only.append(t[:52])
        if acc["accept"] == "degraded":
            degraded.append(f"{m.domain}/{m.archetype} | {t[:40]}")
        if acc["accept"] == "reject":
            alerts.append(("REJECT", t))

    print("\n=== domain ===")
    for k, v in c_dom.most_common():
        print(f"  {k}: {v}")
    print("=== arch ===")
    for k, v in c_arch.most_common():
        print(f"  {k}: {v}")
    print("=== accept ===")
    for k, v in c_acc.most_common():
        print(f"  {k}: {v}")
    print(f"\nalerts={len(alerts)} demoted={len(demoted)} crud_only={len(crud_only)} degraded={len(degraded)}")
    for a in alerts:
        print(" !", a)
    if demoted:
        print("\n-- behavior demoted domain --")
        for x in demoted:
            print(" ", x)
    print("\n-- CRUD-only --")
    for x in crud_only:
        print(" ", x)
    print("\n-- degraded --")
    for x in degraded:
        print(" ", x)


if __name__ == "__main__":
    main()
