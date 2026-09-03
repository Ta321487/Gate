"""运行时能力积木：与题目类型无关；决定可接题边界。"""

from __future__ import annotations

import re
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
    "ai_assistant": {
        "label": "AI智能助手",
        "status": "implemented",
        "desc": "Spring AI + DeepSeek；FAQ + 只读接业务（商品/订单/借阅报修等现有 Store）；热门/满意度；演示级图片品类与浏览器播报",
    },
    "dm": {
        "label": "一对一私信",
        "status": "implemented",
        "desc": "用户↔用户私信；短轮询刷新（非 WebSocket / 非环信等 IM SDK）",
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
    "checkin": {
        "label": "口令签到",
        "status": "implemented",
        "desc": "单据口令/列表签到；结束未签到可记爽约或缺勤（C-10；挂 ACTIVITY/CHECKIN）",
    },
    "mutual_select": {
        "label": "互选确认",
        "status": "implemented",
        "desc": "志愿提交后由档案确认人接受/婉拒，管理端可调剂（C-05；挂导师/选题/组队互选域）",
    },
    "pass_code": {
        "label": "演示通行码",
        "status": "implemented",
        "desc": "审核通过签发演示通行码字符串（非真门禁/二维码硬件；C-09，挂 DOM-VISITOR / DOM-CARPASS）",
    },
    "bed_occupy": {
        "label": "床位占用",
        "status": "implemented",
        "desc": "床位档案库存占用 + 选房/调宿申请（C-08；挂 DOM-BED，复用 quota）",
    },
    "instrument_slot": {
        "label": "仪器机时（借+约）",
        "status": "implemented",
        "desc": "单域 archive+ticket_flow+slot_reserve；机时预约为主、借用单可选（C-07；挂 DOM-INSTRUMENT）",
    },
    "exam": {
        "label": "在线考试",
        "status": "implemented",
        "desc": "题库/组卷/作答/自动判分；刷题·解析·限时·次数·排行·错题本按需（C-01；挂 DOM-EXAM）",
    },
    "survey": {
        "label": "简易问卷",
        "status": "implemented",
        "desc": "问卷配置/填写/回收/选项计数（非跳题/SPSS；C-03；挂 DOM-SURVEY）",
    },
    "vote": {
        "label": "投票评选",
        "status": "implemented",
        "desc": "候选档案、一票/限票、结果公示（C-04；挂 DOM-VOTE；≠活动报名）",
    },
    "doclib": {
        "label": "文库下载台账",
        "status": "implemented",
        "desc": "资料附件、演示权限、下载台账（C-12；挂 DOM-DOCLIB；≠借阅≠博客）",
    },
    "timebank": {
        "label": "时间银行时长账户",
        "status": "implemented",
        "desc": "志愿时长账户余额、流水加减、核销审核扣减（C-14；挂 DOM-TIMEBANK；≠劳动认定≠活动报名）",
    },
    "seat_select": {
        "label": "影院选座购票",
        "status": "implemented",
        "desc": "场次座位图占座+订单（C-15；挂 DOM-CINEMA；演示级，无真锁座高并发；≠点播≠场地预约）",
    },
    "multi_approve": {
        "label": "多级会签（≤3级）",
        "status": "implemented",
        "desc": "固定三级单据状态机：初审→复审→终审（C-16；开题写三级才挂；非任意流程图）",
    },
    "stock_io": {
        "label": "浅进销存（入出库）",
        "status": "implemented",
        "desc": "管理端入库/出库登记+库存流水；复用档案 stock（C-17；挂 DOM-ASSET；单仓演示；≠多仓ERP≠RFID）",
    },
    "e_sign": {
        "label": "本地签章演示",
        "status": "implemented",
        "desc": "上传签章图+勾选同意留痕（C-18；挂 DOM-INTERN 等；非 CA/第三方签平台）",
    },
    "rating_dims": {
        "label": "多维评分",
        "status": "implemented",
        "desc": "单据完结后按维度打分+评语，可选匿名演示；综合分为维度均值（C-06，挂 DOM-EVAL 等）",
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
    "archive_log": {
        "label": "档案打卡记录",
        "status": "implemented",
        "desc": "挂档案的每日打卡/随访/评估记录；今日未打卡；异常可转上报",
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
    # 大模型问答 / ChatGPT 作客服·导购 → 已可 bake（ai_assistant）；勿再整包拒
    ("以图搜图", "视觉检索"),
    ("协同过滤", "协同过滤推荐"),
    ("矩阵分解", "协同过滤推荐"),
    ("物联网", "物联网采集"),
    ("传感器", "物联网采集"),
    ("单片机", "硬件交付"),
    # 道闸/抬杆/车牌识别：硬件联控，非软件通行证备案（CARPASS/VISITOR 只发通行码字符串）
    ("抬杆", "道闸/抬杆硬件"),
    ("自动抬杆", "道闸/抬杆硬件"),
    ("道闸", "道闸/抬杆硬件"),
    ("道闸联动", "道闸/抬杆硬件"),
    ("车牌识别", "车牌识别硬件"),
    ("识别抬杆", "道闸/抬杆硬件"),
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
    # 裸「进销存」可由 C-17 stock_io 浅演示承接；须与 ERP/多仓同伴共现才过重
    ("进销存", "ERP/多仓进销存"),
    ("多仓批次", "ERP/多仓进销存"),
    # 裸「批次管理」歧义大（食安/物资台账也写）；须与 ERP 同伴共现才算过重
    ("批次管理", "ERP/多仓进销存"),
    # 各域常见吹大（智能排课见 SOFT_OVERREACH：接题双显不 reject）
    ("公海池", "外呼/公海池"),
    ("外呼中心", "外呼/公海池"),
    # 毕设级一对一私信已落地为 cap=dm（短轮询）；真 IM SDK / WebSocket 推送仍过重
    ("websocket私信", "WebSocket实时推送"),
    ("WebSocket私信", "WebSocket实时推送"),
    ("环信", "IM云服务/SDK"),
    ("融云", "IM云服务/SDK"),
    ("即时通讯sdk", "IM云服务/SDK"),
    ("IM SDK", "IM云服务/SDK"),
    ("富文本协同", "富文本协同编辑"),
    ("协同编辑", "富文本协同编辑"),
    ("转码cdn", "转码/CDN"),
    ("转码 CDN", "转码/CDN"),
    ("歌词同步", "歌词同步"),
    ("rfid", "RFID全链路"),
    ("RFID", "RFID全链路"),
    # 真 CA / 第三方签平台；裸「电子签/签章」由 C-18 e_sign 浅演示承接
    ("电子签章ca", "电子签章CA/第三方签平台"),
    ("电子签章 CA", "电子签章CA/第三方签平台"),
    ("法大大", "电子签章CA/第三方签平台"),
    ("上上签", "电子签章CA/第三方签平台"),
    ("e签宝", "电子签章CA/第三方签平台"),
    ("第三方电子签", "电子签章CA/第三方签平台"),
]

# 歧义词：命中后还须同段出现任一同伴，才记入过重（仍走 keyword_mentioned，不另开扫描）
_OVERREACH_NEED_COMPANION: dict[str, tuple[str, ...]] = {
    "批次管理": ("多仓", "进销存", "erp系统", "ERP", "WMS", "多组织库存", "采购入库"),
    "进销存": ("多仓", "erp系统", "ERP", "WMS", "财务一体化", "多组织库存", "多仓批次", "批次追溯"),
}

# 软超壳：写入本期不做 / 接题双显，但不触发 accept=reject（排课引擎等）
SOFT_OVERREACH_SIGNALS: list[tuple[str, str]] = [
    ("智能排课", "智能排课"),
    ("自动排课", "智能排课"),
    ("排课引擎", "智能排课"),
    ("排课系统", "智能排课"),
    ("教务排课", "智能排课"),
]


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
    """扫描开题里「拟交付」的超范围卖点。

    真实开题常在研究现状 / 非本期写到人脸、真支付、ERP 等——那是划界，不是承诺。
    因此只扫「拟实现/主要功能」等实现段（无章节时退回全文），并忽略否定与对比语境。
    """
    from app.services.proposal import strip_non_dev_sections

    raw = strip_non_dev_sections(text or "")
    focus = raw
    try:
        from app.bake.catalog import proposal_impl_sections_for_scope

        focused = proposal_impl_sections_for_scope(text or "")
        if focused and focused.strip():
            focus = focused
    except Exception:  # noqa: BLE001
        pass
    hits = _scan_signals(focus, OUT_OF_SCOPE_SIGNALS, ignore_contrast=True)
    for label in _scan_signals(focus, BUSINESS_OVERREACH_SIGNALS, ignore_contrast=True):
        if label not in hits:
            hits.append(label)
    # P-30：用章+用车+证明三联不得一题三引擎冒充
    for label in _scan_oa_triple(focus):
        if label not in hits:
            hits.append(label)
    return hits


def scan_soft_out_of_mvp(text: str) -> list[str]:
    """软超壳：进本期不做与接题双显，不 reject。"""
    from app.services.proposal import strip_non_dev_sections

    raw = strip_non_dev_sections(text or "")
    focus = raw
    try:
        from app.bake.catalog import proposal_impl_sections_for_scope

        focused = proposal_impl_sections_for_scope(text or "")
        if focused and focused.strip():
            focus = focused
    except Exception:  # noqa: BLE001
        pass
    return _scan_signals(focus, SOFT_OVERREACH_SIGNALS, ignore_contrast=True)


def _scan_oa_triple(text: str) -> list[str]:
    """开题同时承诺用章、用车、开具证明三条申请主路径 → reject。"""
    t = text or ""
    seal = any(k in t for k in ("用章", "印章申请", "用印申请", "行政印章"))
    fleet = any(k in t for k in ("用车申请", "公务用车", "派车申请", "车辆调度申请"))
    cert = any(k in t for k in ("开具证明", "在读证明", "在职证明", "成绩单证明", "证明开具"))
    if seal and fleet and cert:
        return ["OA三联（用章+用车+证明）须裁成单一申请主路径"]
    return []


def compose_out_of_mvp(
    domain: str,
    proposal_text: str = "",
    *,
    scanned_signals: list[str] | None = None,
) -> list[str]:
    """合成「本期不做」：域目录默认 ∪ 开题扫到的超范围；非写死交付清单。

    - `DOMAINS[*].out_of_mvp`：行业壳常见边界，维护者随时改 domains.py
    - 开题有实质正文时：仅保留与题面相关的默认项（题面出现该词/片段即相关，含「不做X」）
    - 再并入 `scan_out_of_scope` 命中项（开题提及的超壳卖点）
    - 再并入软超壳（排课等：双显不 reject）
    """
    from app.bake.domains import DOMAINS

    defaults = list((DOMAINS.get(domain) or {}).get("out_of_mvp") or [])
    text = (proposal_text or "").strip()
    substantial = len(text) >= 80
    out: list[str] = []

    def _add(item: str) -> None:
        item = (item or "").strip()
        if item and item not in out:
            out.append(item)

    for item in defaults:
        if not substantial:
            _add(item)
            continue
        parts = [item] + [
            p.strip() for p in re.split(r"[/、与和]", item) if len(p.strip()) >= 2
        ]
        if any(p in text for p in parts):
            _add(item)

    for sig in scanned_signals or []:
        _add(str(sig))

    for sig in scan_soft_out_of_mvp(proposal_text):
        _add(str(sig))

    return out


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
            "reason": "拟实现/主要功能段承诺了未落地能力（"
            + "、".join(oos[:6])
            + ("…" if len(oos) > 6 else "")
            + "）；请改开题承诺或先扩能力后再 full",
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
