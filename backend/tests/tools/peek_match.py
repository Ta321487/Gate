"""quick peek matches"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from app.bake.catalog import match_text
from app.bake.domain_schema import required_capabilities

CASES = [
    "基于SpringBoot的客户关系管理系统的设计与实现",
    "中小企业CRM客户跟进管理系统的设计与实现",
    "销售线索与客户跟进管理系统的设计与实现",
    "企业进销存管理系统的设计与实现",
    "中小企业ERP进销存模块的设计与实现",
    "企业员工考勤与请假管理系统的设计与实现",
    "Java校园志愿者服务平台的设计与实现",
    "SpringBoot技术的实验室管理系统的设计与实现",
    "实验室耗材管理系统的设计与实现",
    "高校会议室预约管理系统的设计与实现",
    "高校饭堂点餐系统的设计与实现",
    "HPV疫苗预约系统的设计与实现",
    "基于SpringBoot的小区智能泊车系统的设计与实现",
    "失物招领管理系统的设计与实现",
    "固定资产领用与耗材申领管理系统的设计与实现",
]


def body_for(t: str) -> str:
    lines = ["题目：" + t, "", "二、主要功能"]
    if any(k in t for k in ("跟进", "CRM", "客户")):
        lines.append("1. 客户建档与跟进单据审核")
    if "请假" in t:
        lines.append("1. 员工提交请假，管理员审批")
    if any(k in t for k in ("进销存", "ERP")):
        lines.append("1. 入库出库申请与库存台账")
    if "志愿" in t:
        lines.append("1. 志愿活动报名与审核")
    if "实验室" in t and "耗材" not in t:
        lines.append("1. 设备借用申请与归还")
    if any(k in t for k in ("预约", "泊车", "疫苗")):
        lines.append("1. 用户选择资源与时段进行预约")
    if "点餐" in t or "饭堂" in t:
        lines.append("1. 点餐下单与订单管理")
    if "招领" in t:
        lines.append("1. 认领申请审核")
    if "耗材" in t or "申领" in t:
        lines.append("1. 耗材申领审核")
    return "\n".join(lines)


def main() -> None:
    for t in CASES:
        m = match_text(body_for(t))
        caps = required_capabilities(m.domain, m.archetype, archetypes=m.archetypes)
        arches = ",".join(m.archetypes or [m.archetype])
        thick = any(c in caps for c in ("ticket_flow", "order_lines", "slot_reserve"))
        flag = "THICK" if thick else "CRUD!"
        print(f"{flag:6} | {m.domain:14} | {arches:32} | {t[:40]}")
        print(f"       caps={caps}")
        print(f"       hits={m.hits}")


if __name__ == "__main__":
    main()
