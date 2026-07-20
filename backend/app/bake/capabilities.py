"""运行时能力积木：与题目类型无关；决定可接题边界。"""

from __future__ import annotations

import re
from typing import Any

# status: implemented = 当前骨架/运行时已能交付；planned = 规格已定未落地
CAPABILITIES: dict[str, dict[str, Any]] = {
    "archive": {
        "label": "档案维护",
        "status": "implemented",
        "desc": "业务对象增删改查、分类、详情",
    },
    "ticket_flow": {
        "label": "单据流转",
        "status": "implemented",
        "desc": "提交/待审/通过驳回/完结；我的与待办",
    },
    "quota": {
        "label": "数量占用",
        "status": "implemented",
        "desc": "占用与归还（库存、名额等）",
    },
    "deadline": {
        "label": "到期催办",
        "status": "implemented",
        "desc": "到期、逾期、提醒、可选费用",
    },
    "slot_reserve": {
        "label": "时段预约",
        "status": "implemented",
        "desc": "资源时段库存占坑与取消（有别于本人已选时段相交）",
    },
    "order_lines": {
        "label": "多明细履约",
        "status": "implemented",
        "desc": "购物车 + 多明细订单（无真支付）",
    },
    "wallet": {
        "label": "演示余额",
        "status": "implemented",
        "desc": "用户余额字段+流水；管理端可充值；下单扣减（非真支付）",
    },
    "points": {
        "label": "积分",
        "status": "implemented",
        "desc": "积分字段+流水；下单完成赠送；不可充值",
    },
    "spend_discount": {
        "label": "满减",
        "status": "implemented",
        "desc": "满 xx 元减 yy（演示优惠，写入订单快照）",
    },
    "member_tier": {
        "label": "会员成长",
        "status": "implemented",
        "desc": "累计消费升级；等级折扣叠在下单算价",
    },
    "content": {
        "label": "内容发布",
        "status": "implemented",
        "desc": "公告/资讯",
    },
    "org_users": {
        "label": "组织与用户",
        "status": "implemented",
        "desc": "角色用户、启用停用、重置密码、工作台",
    },
    "recommend": {
        "label": "轻量推荐",
        "status": "implemented",
        "desc": "猜你喜欢：分类偏好 + 热度 + 上新兜底（非协同过滤）",
    },
    "time_conflict": {
        "label": "时间冲突检测",
        "status": "implemented",
        "desc": "主数据起止时间；申请时与本人已占用时段区间相交检测；报名截止校验",
    },
}

# 开题命中这些信号 → 不得进入 complete（最多 degraded）
# 注：轻量「猜你喜欢」已落地；协同过滤/深度推荐仍视为超范围卖点
OUT_OF_SCOPE_SIGNALS: list[tuple[str, str]] = [
    ("人脸", "生物识别/人脸"),
    ("指纹", "生物识别"),
    ("深度学习", "模型训练/推理"),
    ("卷积神经网络", "模型训练/推理"),
    ("大模型", "大模型问答"),
    ("chatgpt", "大模型问答"),
    ("以图搜图", "视觉检索"),
    ("协同过滤", "协同过滤推荐"),
    ("矩阵分解", "协同过滤推荐"),
    ("物联网", "物联网采集"),
    ("传感器", "物联网采集"),
    ("单片机", "硬件交付"),
    ("区块链", "区块链存证"),
    ("直播", "实时直播"),
    ("webrtc", "实时音视频"),
    ("hadoop", "大数据作业"),
    ("spark", "大数据作业"),
    ("微信支付", "真实第三方支付"),
    ("支付宝", "真实第三方支付"),
    ("小程序", "非本仓库主交付形态"),
    ("安卓", "非本仓库主交付形态"),
    ("android", "非本仓库主交付形态"),
]


def implemented_capability_ids() -> set[str]:
    return {k for k, v in CAPABILITIES.items() if v.get("status") == "implemented"}


def scan_out_of_scope(text: str) -> list[str]:
    """扫描超范围卖点；「不做/不要求/不作为必交」等否定语境不计。"""
    raw = text or ""
    neg = re.compile(
        r"(?:不要求|不实现|不做|不作为|不纳入|不属于|仅作展望|仅参考|非本课题|"
        r"本期不|范围外|不强制|非必交|非必演示|不作为必)"
    )
    hits: list[str] = []
    for kw, label in OUT_OF_SCOPE_SIGNALS:
        for m in re.finditer(re.escape(kw), raw, flags=re.IGNORECASE):
            window = raw[max(0, m.start() - 24) : m.end() + 24]
            if neg.search(window):
                continue
            if label not in hits:
                hits.append(label)
            break
    return hits


def resolve_accept(
    required: list[str],
    proposal_text: str = "",
    *,
    has_domain_overlay: bool = False,
    has_baseline_runtime: bool = False,
) -> dict[str, Any]:
    """
    full: 所需能力均已实现，且有可跑骨架（领域 overlay 或基线通用壳）
    degraded: 主路径可交付，但开题含未实现卖点
    reject: 主路径依赖未实现能力，或无任何可运行骨架
    """
    req = [c for c in required if c]
    impl = implemented_capability_ids()
    missing = [c for c in req if c not in impl]
    oos = scan_out_of_scope(proposal_text)

    if missing:
        return {
            "accept": "reject",
            "required_capabilities": req,
            "missing_capabilities": missing,
            "out_of_mvp_signals": oos,
            "reason": "主路径依赖尚未落地的运行时能力",
        }

    # 基线通用壳已覆盖 ticket_flow/archive/content/org_users 等 → 不再强制 DOM overlay
    if not has_domain_overlay and not has_baseline_runtime and req:
        return {
            "accept": "reject",
            "required_capabilities": req,
            "missing_capabilities": ["domain_runtime"],
            "out_of_mvp_signals": oos,
            "reason": "能力已规划但当前无对应可运行骨架",
        }

    if oos:
        return {
            "accept": "degraded",
            "required_capabilities": req,
            "missing_capabilities": [],
            "out_of_mvp_signals": oos,
            "reason": "主路径可交付；开题中的未实现卖点已标出",
        }

    return {
        "accept": "full",
        "required_capabilities": req,
        "missing_capabilities": [],
        "out_of_mvp_signals": [],
        "reason": "主路径能力齐备",
    }
