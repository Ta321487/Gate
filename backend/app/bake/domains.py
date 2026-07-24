"""领域目录：ARCHETYPES / DOMAIN_CAPABILITIES / DOMAINS。门禁见 gate_contracts。"""

from __future__ import annotations

# 行为词桶（有上限）：对齐运行时积木，不堆行业名词。新增词先问「是不是新能力」。
# 同分/并集排序：预约 > 交易 > 审核流（catalog 与 archetype_shells 共用）
ARCH_PATH_ORDER: tuple[str, ...] = (
    "ARCH-RESERVE",
    "ARCH-TRADE",
    "ARCH-FLOW",
    "ARCH-STOCK",
    "ARCH-CONTENT",
    "ARCH-CRUD",
)

ARCHETYPES = {
    # 不用光杆「管理」：开题几乎都带「管理系统」，会压过预约/订单等更具体原型
    "ARCH-CRUD": {"label": "纯管理", "keywords": ["信息维护", "增删改查", "档案管理", "台账管理"]},
    "ARCH-FLOW": {
        "label": "审核流",
        "keywords": [
            # 审核 / 单据
            "审核", "审批", "会签", "申请", "申报", "递交", "认定",
            "借阅", "借还", "报修", "保修", "维修", "工单", "派发", "派单", "回访", "投诉", "挂失",
            "申领", "领用", "巡检", "巡查", "报名", "请假",
            "跟进", "线索",
            # 流转类 = ticket_flow 同义，不新开 ARCH
            "流转", "上报", "分拨", "转办",
            # 事件/公卫（与 DOM-EVENT 对齐；勿用光杆「打卡/照护」抬分）
            "随访", "排查", "晨检", "晨午检", "监测", "处置", "密接", "接触者", "病例",
            "健康监测", "健康打卡", "复工监测", "隔离观察", "健康筛查",
            # 英文行为（极少）
            "repair", "approval", "workflow",
        ],
    },
    "ARCH-TRADE": {
        "label": "交易流",
        "keywords": [
            "交易", "二手", "订单", "下单", "支付", "购物", "购物车", "交换",
            "配送", "助餐", "拼单", "预售", "点单", "订餐", "代购", "接单",
            "结算", "团购", "转卖", "提货", "成交", "拍卖", "跑腿", "售票", "点餐",
            "销售", "电商", "直销",
            "order", "checkout", "cart",
        ],
    },
    "ARCH-RESERVE": {
        "label": "预约流",
        "keywords": [
            "预约", "预订", "挂号", "车位", "订座", "排班", "场次", "占座", "座位确认",
            "座位管理", "座位预约", "包厢预约", "改约", "订场", "占坑", "泊车",
            "booking", "reservation",
        ],
    },
    "ARCH-CONTENT": {
        "label": "内容流",
        "keywords": [
            # 不用光杆「发布」：公告发布几乎每题都有，会误抬内容流
            "资讯", "新闻", "文章", "影视", "视频", "点播", "音乐", "歌曲",
            "论坛", "博客", "帖子", "BBS", "贴吧", "CMS", "展播", "收藏",
        ],
    },
    "ARCH-STOCK": {
        "label": "进销存",
        "keywords": [
            "进销存", "库存", "采购", "出库", "入库", "盘点", "inventory",
            "仓储", "调拨", "库存预警", "出入库", "物资调度",
        ],
    },
}


# 领域分组（级联选择一级；与 DOMAIN_CAPABILITIES 注释分组一致）
DOMAIN_GROUPS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    (
        "borrow",
        "借用/占用",
        (
            "DOM-LIBRARY",
            "DOM-EQUIP",
            "DOM-ASSET",
            "DOM-CRM",
            "DOM-EVENT",
            "DOM-ATTEND",
            "DOM-FUND",
            "DOM-LABSAFE",
            "DOM-RECRUIT",
            "DOM-GRADE",
            "DOM-INTERN",
            "DOM-PARCEL",
        ),
    ),
    ("ticket", "报修/工单", ("DOM-DORM", "DOM-PROPERTY", "DOM-IT")),
    ("apply", "报名/申请", ("DOM-ACTIVITY", "DOM-LOST", "DOM-COURSE")),
    ("trade", "交易", ("DOM-SHOP", "DOM-FOOD")),
    (
        "reserve",
        "预约",
        ("DOM-HOSPITAL", "DOM-PARKING", "DOM-MEETING", "DOM-SALON", "DOM-HOTEL"),
    ),
    ("content", "内容/媒资/社区", ("DOM-MEDIA", "DOM-MUSIC", "DOM-FORUM", "DOM-BLOG")),
    ("fallback", "兜底", ("DOM-GENERIC",)),
)

# domain → 默认所需能力（题目无关的积木组合）
# 分组见 DOMAIN_GROUPS / HANDOFF「90% 毕设覆盖」
DOMAIN_CAPABILITIES: dict[str, list[str]] = {
    # A 借用/占用
    "DOM-LIBRARY": ["archive", "ticket_flow", "quota", "deadline", "content", "org_users", "recommend"],
    "DOM-EQUIP": ["archive", "ticket_flow", "quota", "deadline", "content", "org_users", "recommend"],
    "DOM-ASSET": ["archive", "ticket_flow", "quota", "content", "org_users"],
    "DOM-CRM": ["archive", "ticket_flow", "content", "org_users"],
    "DOM-EVENT": ["archive", "ticket_flow", "archive_log", "content", "org_users"],
    "DOM-ATTEND": ["archive", "ticket_flow", "content", "org_users"],
    "DOM-FUND": ["archive", "ticket_flow", "content", "org_users"],
    "DOM-LABSAFE": ["archive", "ticket_flow", "content", "org_users"],
    "DOM-RECRUIT": ["archive", "ticket_flow", "content", "org_users"],
    "DOM-GRADE": ["archive", "ticket_flow", "content", "org_users"],
    "DOM-INTERN": ["archive", "ticket_flow", "content", "org_users"],
    "DOM-PARCEL": ["archive", "ticket_flow", "quota", "content", "org_users"],
    # B 报修/工单
    "DOM-DORM": ["ticket_flow", "content", "org_users"],
    "DOM-PROPERTY": ["ticket_flow", "content", "org_users"],
    "DOM-IT": ["ticket_flow", "content", "org_users"],
    # C 报名/申请
    "DOM-ACTIVITY": ["archive", "ticket_flow", "quota", "content", "org_users", "time_conflict"],
    "DOM-LOST": ["archive", "ticket_flow", "quota", "content", "org_users"],
    "DOM-COURSE": ["archive", "ticket_flow", "quota", "content", "org_users", "time_conflict"],
    # D 交易（order_lines）
    "DOM-SHOP": ["archive", "order_lines", "quota", "content", "org_users", "guestbook"],
    "DOM-FOOD": ["archive", "order_lines", "quota", "content", "org_users", "guestbook"],
    # E 预约（slot_reserve；资源走 archive）
    "DOM-HOSPITAL": ["archive", "slot_reserve", "content", "org_users"],
    "DOM-PARKING": ["archive", "slot_reserve", "content", "org_users"],
    "DOM-MEETING": ["archive", "slot_reserve", "content", "org_users"],
    "DOM-SALON": ["archive", "slot_reserve", "content", "org_users"],
    "DOM-HOTEL": ["archive", "slot_reserve", "order_lines", "content", "org_users"],
    # F 兜底
    "DOM-GENERIC": ["archive", "content", "org_users"],
    # G 内容/媒资/社区（MEDIA/MUSIC/BLOG 即时收藏；FORUM 回帖仍走审核单）
    "DOM-MEDIA": ["archive", "favorites", "content", "org_users", "recommend"],
    "DOM-MUSIC": ["archive", "favorites", "content", "org_users", "recommend"],
    "DOM-FORUM": ["archive", "ticket_flow", "content", "org_users", "recommend"],
    "DOM-BLOG": ["archive", "favorites", "content", "org_users", "recommend"],
}


# out_of_mvp：行业壳「常见边界」示例外壳，可随时改本表；交付清单由
# attach_accept → compose_out_of_mvp（目录相关项 ∪ 开题扫词）合成，非写死契约。

from app.bake.domains_catalog import CATALOG_DOMAINS

DOMAINS = dict(CATALOG_DOMAINS)

# 档案表 / 单据表 / ticket_mode 以 domain_entities 为准（覆盖上方 runtime 同名字段）
from app.bake.domain_entities import bind_runtime_tables  # noqa: E402

bind_runtime_tables(DOMAINS)
