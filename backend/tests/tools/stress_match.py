"""大量擦边选题压测匹配 / accept / GENERIC 绑壳。"""
from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.bake.capabilities import resolve_accept
from app.bake.catalog import build_spec, match_text
from app.bake.domain_schema import baseline_runtime_covers, required_capabilities

# 批次 A：上次暴露问题的回归题
REGRESSION = [
    "图书馆研讨隔间预约与超时清场提醒系统",
    "高校会议室茶歇服务点单与配送跟踪系统",
    "科研仪器故障报修与配件更换跟踪系统",
    "校园闲置球鞋转卖与线下验货交接系统",
    "食堂窗口套餐拼单与取餐码核销平台",
    "校园歌手大赛报名海选与晋级登记系统",
    "Campus Maker Space Equipment Booking System",
    "档案馆纸质档案借阅预约与归还登记系统",
    "宿舍热水卡异常报修与维修回访系统",
    "基于深度学习的图书协同过滤推荐借阅系统",
]

# 批次 B：新大批量擦边题（与上次不重复）
BATCH_B = [
    # 交易擦边
    "校园跳蚤市场议价成交与线下交付登记系统",
    "研究生实验耗材拼单采购与到货核销平台",
    "学生会纪念品预售认购与现场提货系统",
    "社区生鲜团购接龙与分拣签收管理系统",
    "高校文印店在线下单与取件码核销系统",
    "二手电动车过户交接与定金登记平台",
    "食堂档口原料补货订单与验收对账系统",
    "校园奶茶联名杯预售与门店核销系统",
    # 预约擦边
    "钢琴房分段练习预约与爽约记次系统",
    "校医院慢病复诊号源预约改约系统",
    "心理辅导室一对一面询排班预约系统",
    "游泳馆泳道分时段预约与人数上限系统",
    "创新实验室工位短租预约与续约系统",
    "校友返校参观团预约与接待排班系统",
    "答辩教室占用申请与场次冲突提示系统",
    "冷冻样本库格位预约与超期清退系统",
    "同声传译室时段预订与设备领用系统",
    "夜间自习室座位预约与签到核验系统",
    # 审核/工单擦边
    "实验室临时用电申请与安环审批系统",
    "学生转专业材料递交与学院会签系统",
    "科研伦理审查申报与专家审核系统",
    "校园卡补办申请与制卡进度跟踪系统",
    "教学楼门锁故障报修与配件更换系统",
    "机房软件安装申请与网信审核系统",
    "危化品领用申请与双人复核系统",
    "志愿者时长认定申报与团委验真系统",
    "毕业论文延期答辩审批与备案系统",
    "专利费用报销申请与财务审核系统",
    # 内容擦边
    "院系公开课录像点播与学习笔记系统",
    "校园广播节目单发布与音频回听平台",
    "学生短视频作品展播与点赞收藏系统",
    "党建学习微视频库与打卡登记系统",
    # 库存擦边
    "后勤劳保用品入库出库与盘点系统",
    "医护实训耗材库存预警与申领系统",
    "体育器材室进出库与报废登记系统",
    # 报名/活动擦边
    "新生军训分连报名与调剂管理系统",
    "学术沙龙听众报名与座位分配系统",
    "创业大赛项目报名审核与分组系统",
    "运动会检录冲突提示与项目报名系统",
    # 跨域怪题
    "宿舍阳台种菜备案与邻里投诉处理系统",
    "共享雨伞网点借还与逾期催缴系统",
    "快递驿站滞留件催取与转寄登记系统",
    "养老院探视预约与健康申报系统",
    "乡村助农直播场次预约与订单汇总系统",
    "博物馆文物修复工单派发回传系统",
    "实验室废液转移联单登记与审核系统",
    "心理危机线索上报与分级流转系统",
    "产学研协议审批与到期提醒系统",
    "生物样本冷链箱预约与归还核验系统",
    # 纯 CRUD
    "教师纵向课题台账信息维护系统",
    "实验室气体钢瓶台账管理系统",
    "校友通讯录查询与信息维护平台",
    # L3 擦边
    "食堂刷脸支付点餐与库存联动系统",
    "小程序二手书担保交易与真支付系统",
    "物联网实验室门禁与环境传感平台",
    # 英文
    "Lab Equipment Repair Ticket Approval System",
    "Campus Canteen Cart Checkout Demo",
    "Meeting Room Slot Reservation Portal",
    # 噪声长题
    "基于微服务架构的高校研究生开题答辩场次预约、评委回避与材料递交综合信息平台的设计与实现",
    "（内部测试）社区助餐中央厨房拼单、分拣核销与配送状态跟踪V3",
    # 极糊
    "单位内部综合业务管理软件",
    "课程设计演示系统甲",
]


def archive_noun(spec: dict) -> str:
    try:
        return str(spec["schema"]["entities"]["archive"]["label"])[:24]
    except Exception:
        return "-"


def run_batch(name: str, topics: list[str]) -> dict:
    print(f"\n######## {name} n={len(topics)} ########")
    print(f"{'domain':14} {'arch':12} {'acc':8} | title")
    print("-" * 100)
    c_dom: Counter[str] = Counter()
    c_arch: Counter[str] = Counter()
    c_acc: Counter[str] = Counter()
    alerts: list[tuple] = []

    for t in topics:
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
        print(f"{spec['domain']:14} {m.archetype:12} {acc['accept']:8} | {t[:52]}")
        print(f"  hits={m.hits[:8]} noun={archive_noun(spec)}")

        lib_kw = ("图书", "借阅", "图书馆", "读者", "Book", "book")
        if m.domain == "DOM-LIBRARY" and not any(k in t for k in lib_kw):
            alerts.append(("FALSE_LIBRARY", t))
        if acc["accept"] == "reject":
            alerts.append(("REJECT", t, acc["missing_capabilities"]))
        if spec["domain"] == "DOM-GENERIC" and not spec.get("runtime"):
            alerts.append(("NO_RUNTIME", t))
        # 行为词却 CRUD
        behavior = ("预约", "订单", "报修", "审核", "审批", "拼单", "核销", "报名", "booking")
        if (
            m.archetype == "ARCH-CRUD"
            and any(b.lower() in t.lower() for b in behavior)
        ):
            alerts.append(("CRUD_DESPITE_BEHAVIOR", t, m.hits))
        # 域不盖行为（不应再出现，reconcile 后）
        from app.bake.catalog import domain_covers_archetype

        if m.domain != "DOM-GENERIC" and not domain_covers_archetype(m.domain, m.archetype):
            alerts.append(("DOM_ARCH_MISMATCH", t, m.domain, m.archetype))

    print(f"\n--- {name} summary ---")
    print("domain:", dict(c_dom.most_common()))
    print("arch:", dict(c_arch.most_common()))
    print("accept:", dict(c_acc.most_common()))
    print(f"alerts={len(alerts)}")
    for a in alerts:
        print(" !", a)
    return {"dom": c_dom, "arch": c_arch, "acc": c_acc, "alerts": alerts}


def main() -> None:
    a = run_batch("REGRESSION", REGRESSION)
    b = run_batch("BATCH_B", BATCH_B)
    print("\n======== TOTAL ========")
    print(
        f"topics={len(REGRESSION)+len(BATCH_B)} "
        f"alerts={len(a['alerts'])+len(b['alerts'])} "
        f"degraded={a['acc']['degraded']+b['acc']['degraded']}"
    )


if __name__ == "__main__":
    main()
