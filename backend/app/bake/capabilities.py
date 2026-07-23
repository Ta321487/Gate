"""运行时能力积木：与题目类型无关；决定可接题边界。"""

from __future__ import annotations

from typing import Any

from app.bake.proposal_lexicon import keyword_mentioned

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
        "desc": "资源时段库存占坑、取消与履约办结（入场/就诊/到店/入住离店等）",
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
    "guestbook": {
        "label": "访客留言",
        "status": "implemented",
        "desc": "门户留言；用户发表，管理端列表/删除/简短回复（非论坛、非公告、非站内信）",
    },
    "favorites": {
        "label": "收藏夹",
        "status": "implemented",
        "desc": "即时收藏/取消；交易域可再加购，内容流用于片单/曲库/文章",
    },
    "coupon": {
        "label": "优惠券",
        "status": "implemented",
        "desc": "券模板领取/我的券/下单核销/过期扫标（非真支付）",
    },
    "order_review": {
        "label": "订单评价",
        "status": "implemented",
        "desc": "已完成订单星级+文字评价；管理端回复；仅开题写到才挂",
    },
    "search_assist": {
        "label": "搜索联想与热搜",
        "status": "implemented",
        "desc": "标题前缀联想 + 配置热搜词；仅开题写到才挂",
    },
    "browse_history": {
        "label": "浏览历史",
        "status": "implemented",
        "desc": "最近浏览足迹；仅开题写到才挂",
    },
    "gallery": {
        "label": "商品多图",
        "status": "implemented",
        "desc": "档案图集（非 SKU 多规格）；仅开题写到才挂",
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

# 技术 L3：全文扫描（研究现状里写到也降级，避免当已交付）
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
    # 接题边界：专科/本科毕设·课设；硕博 / 真实全流程不接（扫全文）
    ("硕士学位论文", "硕博课题（不接）"),
    ("博士学位论文", "硕博课题（不接）"),
    ("研究生学位论文", "硕博课题（不接）"),
    ("硕士研究生开题", "硕博课题（不接）"),
    ("博士研究生开题", "硕博课题（不接）"),
    ("真实业务全流程", "真实业务全流程（不接）"),
    ("生产级全流程", "真实业务全流程（不接）"),
    ("端到端真实业务", "真实业务全流程（不接）"),
    ("企业级全链路", "真实业务全流程（不接）"),
]

# 业务写太大：优先扫「拟实现/主要功能」段，减少国内外现状误伤
# 短语尽量具体，避免单字「检查」等误报
BUSINESS_OVERREACH_SIGNALS: list[tuple[str, str]] = [
    # 医疗 / 门诊发散
    ("电子病历", "电子病历"),
    ("病历管理", "电子病历"),
    ("处方开药", "处方开药"),
    ("开具处方", "处方开药"),
    ("处方管理", "处方开药"),
    ("检验检查", "检验检查"),
    ("检验申请", "检验检查"),
    ("叫号大屏", "排队叫号大屏"),
    ("排队叫号", "排队叫号大屏"),
    ("候诊大屏", "排队叫号大屏"),
    ("医保结算", "医保对接/结算"),
    ("医保对接", "医保对接/结算"),
    ("医保接口", "医保对接/结算"),
    # 企业 / 流程过重
    ("bpmn", "可配置工作流/BPMN"),
    ("工作流引擎", "可配置工作流/BPMN"),
    ("activiti", "可配置工作流/BPMN"),
    ("camunda", "可配置工作流/BPMN"),
    ("erp系统", "ERP/多仓进销存"),
    ("多仓", "ERP/多仓进销存"),
    ("进销存", "ERP/多仓进销存"),
    ("多仓批次", "ERP/多仓进销存"),
    # 裸「批次管理」歧义大（食安/物资台账也写）；须与 ERP 同伴共现才算过重
    ("批次管理", "ERP/多仓进销存"),
    # 各域常见吹大
    ("智能排课", "智能排课"),
    ("自动排课", "智能排课"),
    ("公海池", "外呼/公海池"),
    ("外呼中心", "外呼/公海池"),
    ("实时私信", "实时私信"),
    ("富文本协同", "富文本协同编辑"),
    ("协同编辑", "富文本协同编辑"),
    ("转码cdn", "转码/CDN"),
    ("转码 CDN", "转码/CDN"),
    ("歌词同步", "歌词同步"),
    ("rfid", "RFID全链路"),
    ("RFID", "RFID全链路"),
]

# 歧义词：命中后还须同段出现任一同伴，才记入过重（仍走 keyword_mentioned，不另开扫描）
_OVERREACH_NEED_COMPANION: dict[str, tuple[str, ...]] = {
    "批次管理": ("多仓", "进销存", "erp系统", "ERP", "WMS", "多组织库存", "采购入库"),
}


def implemented_capability_ids() -> set[str]:
    return {k for k, v in CAPABILITIES.items() if v.get("status") == "implemented"}


def _scan_signals(
    raw: str,
    signals: list[tuple[str, str]],
    *,
    window: int = 48,
    ignore_contrast: bool = False,
) -> list[str]:
    hits: list[str] = []
    if not raw:
        return hits
    for kw, label in signals:
        if not keyword_mentioned(
            raw, kw, window=window, ignore_contrast=ignore_contrast
        ):
            continue
        need = _OVERREACH_NEED_COMPANION.get(kw)
        if need and not any(
            keyword_mentioned(raw, c, window=window, ignore_contrast=ignore_contrast)
            for c in need
        ):
            continue
        if label not in hits:
            hits.append(label)
    return hits


def scan_out_of_scope(text: str) -> list[str]:
    """扫描超范围卖点；「不做/不纳入」等否定语境不计。

    - 技术 L3：扫全文（去掉参考文献等噪声后）
    - 业务过重：优先扫功能/拟实现焦点段，避免现状综述里的 HIS 对比误伤；
      对比/展望/「先实现…再扩展」语境走 keyword_mentioned(ignore_contrast=True)
    """
    from app.services.proposal import strip_non_dev_sections

    raw = strip_non_dev_sections(text or "")
    hits = _scan_signals(raw, OUT_OF_SCOPE_SIGNALS)

    focus = raw
    try:
        from app.bake.catalog import proposal_impl_sections_for_scope

        focused = proposal_impl_sections_for_scope(text or "")
        # 有明确功能段才收窄；否则退回全文（无章节标题的清单仍能打标）
        if focused and focused.strip():
            focus = focused
    except Exception:  # noqa: BLE001
        pass
    for label in _scan_signals(focus, BUSINESS_OVERREACH_SIGNALS, ignore_contrast=True):
        if label not in hits:
            hits.append(label)
    return hits


def resolve_accept(
    required: list[str],
    proposal_text: str = "",
    *,
    has_domain_overlay: bool = False,
    has_baseline_runtime: bool = False,
    archetypes: list[str] | None = None,
    domain: str | None = None,
    primary_archetype: str | None = None,
) -> dict[str, Any]:
    """
    full: 所需能力均已实现，有可跑骨架，且开题无超壳/未就绪交叉（Path B）
    reject: 缺能力、无骨架、开题命中 OOS/过重，或交叉未 defense_ready
    degraded: 保留枚举兼容旧项目；Path B 新匹配不再给出（超壳改 reject）
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

    # Path B：开题超壳 / L3 → reject（不可再 degraded 装作能全文答辩）
    if oos:
        return {
            "accept": "reject",
            "required_capabilities": req,
            "missing_capabilities": [],
            "out_of_mvp_signals": oos,
            "reason": "开题含未实现卖点（"
            + "、".join(oos[:6])
            + ("…" if len(oos) > 6 else "")
            + "）；Path B 要求改开题或扩能力后再 full",
        }

    from app.bake.cross_paths import evaluate_cross_path

    _key, _entry, cross_reject = evaluate_cross_path(
        archetypes,
        primary=primary_archetype,
        domain=domain,
    )
    if cross_reject:
        return {
            "accept": "reject",
            "required_capabilities": req,
            "missing_capabilities": [],
            "out_of_mvp_signals": [],
            "reason": cross_reject,
            "cross_path": _key,
        }

    return {
        "accept": "full",
        "required_capabilities": req,
        "missing_capabilities": [],
        "out_of_mvp_signals": [],
        "reason": "主路径能力齐备；开题未超壳",
        "cross_path": _key,
    }
