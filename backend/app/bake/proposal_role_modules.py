"""测试开题「按角色模块树」正文素材。

对齐 docs/opening-feature-delivery-map.md：已实现 / 扫词开写入拟实现；
不支持 / OUT_OF_MVP 不进树（由 pack digressions 表达本期不做）。

pack 可设 role_modules 覆盖；否则按 anchor_domain 取默认树，并用
user_role / admin_role / merchant_role / worker_role / goods_label 等换皮。
"""

from __future__ import annotations

from typing import Any

# ---------------------------------------------------------------------------
# 小工具
# ---------------------------------------------------------------------------

Module = tuple[str, str]  # (模块名, 括号内细节)
RoleTree = dict[str, Any]  # {title, modules: list[Module]}


def _m(name: str, detail: str) -> Module:
    return (name, detail)


def _role(title: str, modules: list[Module]) -> RoleTree:
    return {"title": title, "modules": modules}


def _fmt(text: str, ctx: dict[str, str]) -> str:
    try:
        return text.format(**ctx)
    except (KeyError, ValueError):
        return text


def _fmt_modules(modules: list[Module], ctx: dict[str, str]) -> list[Module]:
    return [(_fmt(n, ctx), _fmt(d, ctx)) for n, d in modules]


def _auth_profile(extra: str = "") -> Module:
    base = "注册登录、个人信息（头像、昵称、联系方式、修改密码）"
    if extra:
        base = f"{base}、{extra}"
    return _m("登录注册与个人中心模块", base)


def _notice_guestbook_stats_admin() -> list[Module]:
    return [
        _m("公告管理模块", "发布、编辑、下架系统公告与办事须知"),
        _m("留言反馈模块", "查看并回复用户留言"),
        _m("用户管理模块", "用户查询、启用停用与基础资料维护"),
        _m("数据统计模块", "业务量、办理进度与工作台概览图表"),
    ]


def _ticket_user(
    *,
    apply_label: str,
    apply_detail: str,
    mine_detail: str,
    extras: list[Module] | None = None,
) -> list[Module]:
    mods = [
        _auth_profile(),
        _m(apply_label, apply_detail),
        _m("我的办理记录模块", mine_detail),
        _m("公告查阅模块", "查看系统公告与办事须知"),
        _m("留言反馈模块", "向管理员留言并查看回复"),
    ]
    if extras:
        mods[2:2] = extras
    return mods


def _ticket_admin(
    *,
    audit_label: str,
    audit_detail: str,
    master_label: str,
    master_detail: str,
    extras: list[Module] | None = None,
) -> list[Module]:
    mods = [
        _m("登录与个人中心模块", "登录、修改密码与个人资料"),
        _m(audit_label, audit_detail),
        _m(master_label, master_detail),
        *_notice_guestbook_stats_admin(),
    ]
    if extras:
        mods[2:2] = extras
    return mods


def _dual(
    user_title: str,
    user_mods: list[Module],
    admin_title: str,
    admin_mods: list[Module],
) -> list[RoleTree]:
    return [_role(user_title, user_mods), _role(admin_title, admin_mods)]


# ---------------------------------------------------------------------------
# 各域默认树（信息密度对齐对照表；不含不支持项）
# ---------------------------------------------------------------------------

def _shop_tree(ctx: dict[str, str]) -> list[RoleTree]:
    goods = ctx.get("goods", "商品")
    user = ctx["user"]
    merchant = ctx.get("merchant", "商家")
    admin = ctx["admin"]
    return [
        _role(
            f"{user}功能模块划分",
            [
                _m(
                    "登录注册模块",
                    "注册、登录、修改密码",
                ),
                _m(
                    "个人中心模块",
                    "个人信息（头像、昵称、联系方式、修改密码）、收藏、收货地址",
                ),
                _m(
                    f"{goods}模块",
                    f"浏览搜索{goods}、查看详情（分类、规格说明、价格、简介、图片）、收藏、加入购物车、查看评价",
                ),
                _m("活动模块", "查看促销信息、新品或节日优惠等公告"),
                _m("留言反馈模块", "与管理员沟通"),
                _m("客服模块", f"与{merchant}在线沟通（站内私信）"),
                _m(
                    "评价模块",
                    f"查看其他用户对{goods}的评价；确认收货后可发表评价",
                ),
                _m(
                    "购物车模块",
                    "商品数量增减、删除、价格合计、提交订单",
                ),
                _m(
                    "支付模块",
                    "系统内在线支付：选择支付宝/微信渠道并输入支付密码（模拟支付，不对接商户清算）",
                ),
                _m(
                    "订单模块",
                    "查看订单状态（待付款、待发货、已发货、已完成、已取消等）",
                ),
                _m("申请售后模块", "退货/售后申请与进度查询"),
            ],
        ),
        _role(
            f"{merchant}功能模块划分",
            [
                _m("登录注册模块", "注册、登录、修改密码"),
                _m(
                    "个人中心模块",
                    "店铺信息编辑（店铺名称、简介、联系方式、修改密码）",
                ),
                _m(
                    f"{goods}管理模块",
                    f"{goods}新增、上下架、信息编辑、查看库存与库存预警；可填规格说明",
                ),
                _m("评价管理模块", "查看或回复用户评价"),
                _m(
                    "订单管理模块",
                    "查看/推进订单状态（待付款、待发货、已发货、运输中、已签收、已完成、已取消）、发货操作",
                ),
                _m("售后管理模块", "退货审核"),
                _m("客服模块", f"与{user}在线沟通"),
                _m("留言反馈模块", "与管理员沟通"),
                _m("活动管理模块", "添加促销信息、新品公告"),
                _m(
                    "数据分析模块",
                    "店铺销售总额、日/月销量、商品销量排行、库存与订单统计、热销分析",
                ),
            ],
        ),
        _role(
            f"{admin}功能模块划分",
            [
                _m("登录模块", "登录与修改密码"),
                _m("用户管理模块", "全平台用户查询与启用停用"),
                _m(f"{merchant}管理模块", f"{merchant}入驻审核、店铺信息与启用停用"),
                _m("评价管理模块", "查看全部评价，必要时删除"),
                _m("售后管理模块", "查看全平台售后工单，最高权限处理"),
                _m("订单管理模块", "查看全平台订单状态，最高权限处理"),
                _m(
                    f"{goods}管理模块",
                    f"全局{goods}增删改查、审核内容与图片，违规强制下架",
                ),
                _m("留言反馈模块", f"分别与{user}和{merchant}沟通"),
                _m(f"{goods}分类模块", "分类维护"),
                _m("活动管理模块", f"审核{merchant}提交的促销、新品公告；可配置限时购"),
                _m("数据统计模块", "全平台交易与活跃概览"),
            ],
        ),
    ]


def _food_tree(ctx: dict[str, str]) -> list[RoleTree]:
    user, admin = ctx["user"], ctx["admin"]
    merchant = ctx.get("merchant", "档口商家")
    rider = ctx.get("worker", "配送员")
    return [
        _role(
            f"{user}功能模块划分",
            [
                _auth_profile("收货/取餐地址"),
                _m("菜品模块", "分类浏览搜索、查看详情与库存、加入购物车、查看评价"),
                _m("购物车与下单模块", "数量增减、堂食/自取/外卖方式、提交订单"),
                _m(
                    "支付模块",
                    "系统内支付（渠道+支付密码模拟，不对接商户清算）",
                ),
                _m("订单模块", "查看订单状态、催单、确认收货"),
                _m("评价模块", "完成后评价；查看他人评价"),
                _m("退单模块", "申请退单与进度查询"),
                _m("公告与留言模块", "查阅公告；向管理员留言"),
                _m("客服模块", f"与{merchant}站内沟通"),
            ],
        ),
        _role(
            f"{merchant}功能模块划分",
            [
                _m("登录与店铺模块", "登录、档口/店铺信息编辑"),
                _m("菜品管理模块", "菜品新增编辑、上下架、库存维护"),
                _m("订单接单模块", "接单、拒单、出餐、推进配送状态"),
                _m("评价管理模块", "查看回复评价"),
                _m("退单处理模块", "审核退单"),
                _m("公告统计模块", "本档口销量与订单概览"),
                _m("客服模块", f"与{user}站内沟通"),
            ],
        ),
        _role(
            f"{rider}功能模块划分",
            [
                _m("登录模块", "登录与个人资料"),
                _m("配送任务模块", "领取/查看配送单、确认取餐与送达"),
            ],
        ),
        _role(
            f"{admin}功能模块划分",
            [
                _m("登录模块", "登录与修改密码"),
                _m("用户与档口管理模块", f"用户管理；{merchant}审核与启用"),
                _m("菜品与分类管理模块", "全局菜品审核、违规下架、分类维护"),
                _m("订单与退单管理模块", "全平台订单/退单最高权限"),
                _m("评价管理模块", "查看删除评价"),
                _m("公告与留言模块", "公告发布；回复留言"),
                _m("数据统计模块", "全平台点餐与配送概览"),
            ],
        ),
    ]


def _repair_tree(ctx: dict[str, str]) -> list[RoleTree]:
    user, admin = ctx["user"], ctx["admin"]
    worker = ctx.get("worker", "维修人员")
    return [
        _role(
            f"{user}功能模块划分",
            [
                _auth_profile(),
                _m(
                    "报修申请模块",
                    "选择分类/位置提交报修，上传图片说明，查看进度与催办提醒",
                ),
                _m("我的工单模块", "查询待受理/处理中/已完成记录；完成后可评价"),
                _m("公告查阅模块", "查看报修须知与公告"),
                _m("留言反馈模块", "与管理员沟通"),
            ],
        ),
        _role(
            f"{worker}功能模块划分",
            [
                _m("登录模块", "登录与修改密码"),
                _m("工单接单模块", "查看派单、接单跟进、填写处理结果直至完结"),
                _m("排班查看模块", "查看维修排班（材料写到则启用）"),
            ],
        ),
        _role(
            f"{admin}功能模块划分",
            [
                _m("登录模块", "登录与修改密码"),
                _m(
                    "报修管理模块",
                    "派单、跟进、催办、完结或驳回；查看评价",
                ),
                _m("基础数据模块", "楼栋/位置/报修类型等主数据维护"),
                _m("排班管理模块", f"维护{worker}排班（材料写到则启用）"),
                _m("用户管理模块", "用户查询与启用停用"),
                _m("公告与留言模块", "发布公告；回复留言"),
                _m("数据统计模块", "工单量、时效与分类统计"),
            ],
        ),
    ]


def _library_tree(ctx: dict[str, str]) -> list[RoleTree]:
    user, admin = ctx["user"], ctx["admin"]
    return _dual(
        f"{user}功能模块划分",
        [
            _auth_profile(),
            _m("馆藏检索模块", "按书名/作者/分类检索，查看馆藏与可借状态"),
            _m("借阅模块", "借出申请/办理、续借（材料写到则启用）"),
            _m("我的借阅模块", "在借、历史、超期与罚款查询；催还提醒查阅"),
            _m("荐购模块", "提交图书荐购并查看处理结果（材料写到则启用）"),
            _m("公告与留言模块", "查阅公告；向管理员留言"),
        ],
        f"{admin}功能模块划分",
        [
            _m("登录模块", "登录与修改密码"),
            _m("图书档案模块", "图书增删改查、分类、库存册数"),
            _m(
                "借还管理模块",
                "借出、归还、续借审批、超期罚款与催还",
            ),
            _m("荐购管理模块", "审核图书荐购"),
            _m("读者管理模块", "用户与借阅额度维护"),
            _m("公告留言与统计模块", "公告、留言回复、借阅统计工作台"),
        ],
    )


def _borrow_like(
    ctx: dict[str, str],
    *,
    item: str,
    user_extras: list[Module] | None = None,
    admin_extras: list[Module] | None = None,
) -> list[RoleTree]:
    user, admin = ctx["user"], ctx["admin"]
    u = [
        _auth_profile(),
        _m(f"{item}浏览模块", f"检索{item}档案、查看可借状态与说明"),
        _m(
            "借用申请模块",
            f"提交借用申请、领取/归还记录查询；可续借（材料写到则启用）",
        ),
        _m("我的借用模块", "在借、超期、损坏赔付与排队进度"),
        _m("公告与留言模块", "查阅公告；留言反馈"),
    ]
    if user_extras:
        u.extend(user_extras)
    a = [
        _m("登录模块", "登录与修改密码"),
        _m(f"{item}档案模块", f"{item}建档、分类、状态维护"),
        _m(
            "借用审批模块",
            "审批、发放、归还确认、超期处理、损坏赔付、排队调度",
        ),
        _m("用户管理模块", "用户与额度维护"),
        *_notice_guestbook_stats_admin(),
    ]
    if admin_extras:
        a[3:3] = admin_extras
    return _dual(f"{user}功能模块划分", u, f"{admin}功能模块划分", a)


def _asset_tree(ctx: dict[str, str]) -> list[RoleTree]:
    user, admin = ctx["user"], ctx["admin"]
    return _dual(
        f"{user}功能模块划分",
        _ticket_user(
            apply_label="物资领用申请模块",
            apply_detail="选择物资与数量提交领用申请，查看审批与出库进度",
            mine_detail="我的领用单、驳回原因与历史记录",
        ),
        f"{admin}功能模块划分",
        _ticket_admin(
            audit_label="领用审批与出入库模块",
            audit_detail="审批领用、出库入库、库存预警；盘点/报废（材料写到则启用）",
            master_label="物资档案模块",
            master_detail="物资分类、库存数量与预警阈值维护",
        ),
    )


def _crm_tree(ctx: dict[str, str]) -> list[RoleTree]:
    user, admin = ctx["user"], ctx["admin"]
    return _dual(
        f"{user}功能模块划分",
        [
            _auth_profile(),
            _m("客户档案模块", "建档、编辑客户资料与标签"),
            _m("线索跟进模块", "记录线索、跟进、回访与商机阶段"),
            _m("我的客户模块", "按跟进状态筛选本人负责客户"),
            _m("公告与留言模块", "查阅公告；留言反馈"),
        ],
        f"{admin}功能模块划分",
        [
            _m("登录模块", "登录与修改密码"),
            _m("客户与线索管理模块", "全量客户/线索查询、分配与审核关键变更"),
            _m("商机统计模块", "跟进转化与业务概览"),
            *_notice_guestbook_stats_admin(),
        ],
    )


def _event_tree(ctx: dict[str, str]) -> list[RoleTree]:
    user, admin = ctx["user"], ctx["admin"]
    return _dual(
        f"{user}功能模块划分",
        _ticket_user(
            apply_label="事件上报模块",
            apply_detail="填写事件类型与说明上报，可附图片；查看排查与处置进度",
            mine_detail="本人上报记录与闭环状态",
        ),
        f"{admin}功能模块划分",
        _ticket_admin(
            audit_label="事件处置模块",
            audit_detail="审核、排查、晨午检类台账、处置闭环",
            master_label="事件类型与对象档案模块",
            master_detail="类型、重点对象或点位档案维护",
        ),
    )


def _attend_tree(ctx: dict[str, str]) -> list[RoleTree]:
    user, admin = ctx["user"], ctx["admin"]
    return _dual(
        f"{user}功能模块划分",
        _ticket_user(
            apply_label="请假销假模块",
            apply_detail="提交请假/销假申请，查看审批结果；可补卡申请",
            mine_detail="请假记录、班次与汇总查阅",
        ),
        f"{admin}功能模块划分",
        _ticket_admin(
            audit_label="假勤审批模块",
            audit_detail="请假销假审批、补卡处理、班次与汇总",
            master_label="班次与规则模块",
            master_detail="班次、请假类型等基础配置",
        ),
    )


def _apply_flow_tree(
    ctx: dict[str, str],
    *,
    biz: str,
    apply_detail: str,
    mine_detail: str,
    audit_detail: str,
    master_label: str,
    master_detail: str,
    catalog_label: str | None = None,
    catalog_detail: str | None = None,
    result_label: str | None = None,
    result_detail: str | None = None,
    admin_extra: list[Module] | None = None,
    user_extra: list[Module] | None = None,
) -> list[RoleTree]:
    """票单学工深树：申请材料 + 状态查询 + 审核办结 + 主数据（可再叠目录/结果/横切扫词模块）。"""
    user, admin = ctx["user"], ctx["admin"]
    u: list[Module] = [
        _auth_profile(),
    ]
    if catalog_label and catalog_detail:
        u.append(_m(catalog_label, catalog_detail))
    u.append(_m(f"{biz}申请填报模块", apply_detail))
    u.append(
        _m(
            "材料附件模块",
            "开题要求上传附件/证明材料时须附档提交（材料写到则启用）",
        )
    )
    u.append(_m(f"我的{biz}办理模块", mine_detail))
    u.append(
        _m(
            "驳回重提模块",
            "审核驳回后按意见修改材料并再次提交；查看历史办理意见",
        )
    )
    if result_label and result_detail:
        u.append(_m(result_label, result_detail))
    if user_extra:
        u.extend(user_extra)
    u.extend(
        [
            _m(
                "办理催办模块",
                "待办超时催办与提醒（材料写催办则启用）",
            ),
            _m(
                "消息通知模块",
                "审核通过/驳回站内消息通知（材料写消息模板/通知模板则启用）",
            ),
            _m("公告查阅模块", "查看办事须知与公示类公告"),
            _m("留言反馈模块", "向管理员留言并查看回复"),
        ]
    )
    a: list[Module] = [
        _m("登录模块", "登录与修改密码"),
        _m(
            f"{biz}审核办理模块",
            audit_detail
            if "待审" in audit_detail or "通过" in audit_detail
            else f"待审队列；{audit_detail}；填写审核意见",
        ),
        _m(
            "多级审批模块",
            "初审与终审或三级签批（材料写两级/三级审批则启用）",
        ),
        _m(master_label, master_detail),
    ]
    if admin_extra:
        # 插在主数据之后、横切模块之前
        a[3:3] = admin_extra
    a.extend(
        [
            _m(
                "操作审计模块",
                "关键写操作与登录记入审计日志（材料写操作日志/审计日志则启用）",
            ),
        ]
    )
    a.extend(_notice_guestbook_stats_admin())
    return _dual(f"{user}功能模块划分", u, f"{admin}功能模块划分", a)


def _fund_tree(ctx: dict[str, str]) -> list[RoleTree]:
    return _apply_flow_tree(
        ctx,
        biz="资助",
        catalog_label="资助项目浏览模块",
        catalog_detail="浏览奖学金/助学金/困难补助项目、申请条件与名额",
        apply_detail="选择项目、填写家庭经济与申请理由、上传证明材料后提交",
        mine_detail="查看待审/通过/驳回/已公示/已发放等状态与审核意见",
        result_label="公示与发放查阅模块",
        result_detail="查阅公示名单与发放登记结果（无银行直发对接）",
        audit_detail="材料审核、通过驳回、公示名单、发放登记与名额占用统计",
        master_label="资助项目与名额模块",
        master_detail="项目类型、申请窗口、名额与材料要求配置",
    )


def _seal_tree(ctx: dict[str, str]) -> list[RoleTree]:
    return _apply_flow_tree(
        ctx,
        biz="用印",
        catalog_label="用印事项说明模块",
        catalog_detail="查阅可申请印章类型、用印须知与份数规则",
        apply_detail="填写用印事由、文件名称、份数，上传附件后提交",
        mine_detail="查看待审/已通过/已驳回/已用印登记等进度",
        audit_detail="审批通过驳回、用印办理登记、台账核对",
        master_label="印章类型与规则模块",
        master_detail="印章档案、可用状态与申请规则",
        admin_extra=[
            _m("用印台账模块", "按日期/印章类型查询用印记录"),
        ],
    )


def _fleet_tree(ctx: dict[str, str]) -> list[RoleTree]:
    return _apply_flow_tree(
        ctx,
        biz="用车",
        catalog_label="车辆与时段查阅模块",
        catalog_detail="查看可用车辆、载客与大致档期说明",
        apply_detail="填写用车时间、行程、人数与事由后提交",
        mine_detail="查看待审/已派车/行驶中/已归还/已驳回等状态",
        audit_detail="审批、派车、登记出车里程、确认归还",
        master_label="车辆档案模块",
        master_detail="车辆信息、可用状态与驾驶员备注",
        admin_extra=[
            _m("派车归还台账模块", "出车与归还记录查询"),
        ],
    )


def _cert_tree(ctx: dict[str, str]) -> list[RoleTree]:
    return _apply_flow_tree(
        ctx,
        biz="证明",
        catalog_label="证明类型浏览模块",
        catalog_detail="浏览在读/在职/成绩等证明类型与办理说明",
        apply_detail="选择证明类型、填写用途与领取方式后提交",
        mine_detail="查看待审/已开具/待领取/已领取/已驳回等状态",
        result_label="领取结果模块",
        result_detail="查看开具结果与领取登记信息",
        audit_detail="审批、开具、打印登记、领取确认",
        master_label="证明模板模块",
        master_detail="证明类型、模板字段与办理时限配置",
    )


def _promo_tree(ctx: dict[str, str]) -> list[RoleTree]:
    return _apply_flow_tree(
        ctx,
        biz="宣传品",
        catalog_label="宣传品目录模块",
        catalog_detail="浏览可领用/可制作宣传品品类与库存说明",
        apply_detail="选择品类、数量与用途说明后提交",
        mine_detail="查看待审/制作中/待发放/已发放/已驳回等进度",
        audit_detail="审核、安排制作或出库、发放确认与库存扣减",
        master_label="宣传品库存模块",
        master_detail="品类、库存数量与预警",
    )


def _fitout_tree(ctx: dict[str, str]) -> list[RoleTree]:
    return _apply_flow_tree(
        ctx,
        biz="装修报备",
        apply_detail="填写装修区域、工期，上传图纸/方案说明后提交",
        mine_detail="查看待审/施工中/待验收/已验收/已驳回等状态",
        audit_detail="审批、巡查记录、验收办结或整改退回",
        master_label="报备类型与区域模块",
        master_detail="装修类型、可报备区域与注意事项",
        admin_extra=[
            _m("巡查验收台账模块", "巡查与验收意见查询"),
        ],
    )


def _acad_tree(ctx: dict[str, str]) -> list[RoleTree]:
    return _apply_flow_tree(
        ctx,
        biz="学术活动",
        apply_detail="填写活动主题、时间场地需求，上传材料后申报",
        mine_detail="查看待审/已批准/已驳回/成果已登记等状态",
        audit_detail="审核申报、场地与材料把关、成果登记确认",
        master_label="学术活动类型模块",
        master_detail="活动类别、申报窗口与材料要求",
        result_label="成果查阅模块",
        result_detail="查看已登记的活动成果摘要",
    )


def _trip_tree(ctx: dict[str, str]) -> list[RoleTree]:
    return _apply_flow_tree(
        ctx,
        biz="出差",
        apply_detail="填写行程、时间、人员与借款说明后提交",
        mine_detail="查看待审/已批准/已驳回/已关联报销等状态",
        audit_detail="审批出差、登记借款意向、关联后续报销单号",
        master_label="差旅规则模块",
        master_detail="出差类型、补贴说明与审批规则",
        admin_extra=[
            _m("出差台账模块", "按部门/日期查询出差单"),
        ],
    )


def _expense_tree(ctx: dict[str, str]) -> list[RoleTree]:
    return _apply_flow_tree(
        ctx,
        biz="报销",
        apply_detail="填写费用明细、发票信息与附件说明后提交（系统内流程）",
        mine_detail="查看待审/已通过/已驳回/已付款登记等状态",
        audit_detail="审核票据与金额、通过驳回、系统内付款登记（无银企直连）",
        master_label="费用科目模块",
        master_detail="费用类型、科目与限额说明",
        admin_extra=[
            _m("报销台账模块", "按申请人/科目查询报销单"),
        ],
    )


def _credit_tree(ctx: dict[str, str]) -> list[RoleTree]:
    return _apply_flow_tree(
        ctx,
        biz="第二课堂学分",
        catalog_label="学分项目浏览模块",
        catalog_detail="浏览可申报学分类型与认定标准",
        apply_detail="选择学分类型、填写参与说明并上传证明材料",
        mine_detail="查看待认定/已认定/已驳回及学分汇总",
        audit_detail="材料认定审核、学分入账与汇总统计",
        master_label="学分规则模块",
        master_detail="学分类型、分值规则与申报窗口",
    )


def _labor_tree(ctx: dict[str, str]) -> list[RoleTree]:
    return _apply_flow_tree(
        ctx,
        biz="劳动时长",
        apply_detail="申报劳动日期、时长与岗位说明，可附证明",
        mine_detail="查看待审/已认定/已驳回及累计时长",
        audit_detail="审核认定、驳回说明与时长汇总",
        master_label="劳动类型模块",
        master_detail="劳动岗位类型与认定规则",
    )


def _eval_tree(ctx: dict[str, str]) -> list[RoleTree]:
    return _apply_flow_tree(
        ctx,
        biz="综合测评",
        catalog_label="测评指标查阅模块",
        catalog_detail="查阅测评学年、指标与填报说明",
        apply_detail="按指标填报加减分项并上传佐证材料",
        mine_detail="查看填报进度、审核结果与公示成绩",
        result_label="测评结果查阅模块",
        result_detail="查看个人测评汇总与公示信息",
        audit_detail="评分复核、汇总审核与结果公示",
        master_label="测评指标体系模块",
        master_detail="学年、指标权重与填报窗口配置",
    )


def _moral_tree(ctx: dict[str, str]) -> list[RoleTree]:
    return _apply_flow_tree(
        ctx,
        biz="德育",
        catalog_label="德育项目浏览模块",
        catalog_detail="浏览可申报德育项目与材料要求",
        apply_detail="选择项目、填写事迹说明并上传材料",
        mine_detail="查看待审/已通过/已驳回/已公示等状态",
        result_label="公示查阅模块",
        result_detail="查阅德育结果公示",
        audit_detail="材料审核、结果认定与公示",
        master_label="德育项目类型模块",
        master_detail="项目类别与评分/认定规则",
    )


def _award_tree(ctx: dict[str, str]) -> list[RoleTree]:
    return _apply_flow_tree(
        ctx,
        biz="成果登记",
        apply_detail="登记成果名称、级别、时间并上传证明材料",
        mine_detail="查看待审/已认定/已驳回/已展示等状态",
        result_label="成果展示查阅模块",
        result_detail="查看已认定成果展示信息",
        audit_detail="审核认定、驳回说明与展示上架",
        master_label="成果类型模块",
        master_detail="成果类别与认定标准",
    )


def _bed_tree(ctx: dict[str, str]) -> list[RoleTree]:
    return _apply_flow_tree(
        ctx,
        biz="床位调整",
        apply_detail="提交调宿或退宿申请，填写原因与意向楼栋",
        mine_detail="查看待审/已分配/已驳回/已办结等状态",
        audit_detail="审批、床位分配或退宿确认、结果通知",
        master_label="楼栋床位档案模块",
        master_detail="楼栋、房间与床位占用状态",
        admin_extra=[
            _m("床位分配台账模块", "调宿退宿办理记录查询"),
        ],
    )


def _checkin_tree(ctx: dict[str, str]) -> list[RoleTree]:
    return _apply_flow_tree(
        ctx,
        biz="登记签到",
        apply_detail="按登记点完成登记、签到或签退（无人脸核验）",
        mine_detail="查看本人登记与签到记录、缺勤标记",
        audit_detail="审核登记信息、处理缺勤、导出汇总",
        master_label="登记点规则模块",
        master_detail="登记点、开放时段与签到规则",
    )


def _visitor_tree(ctx: dict[str, str]) -> list[RoleTree]:
    return _apply_flow_tree(
        ctx,
        biz="访客",
        apply_detail="填写来访人、被访人、来访事由与时间后提交预约",
        mine_detail="查看待审/已批准/已签到/已驳回等状态；可出示通行码（材料写到则启用）",
        audit_detail="审批来访、签到核验、通行证办理",
        master_label="来访类型与区域模块",
        master_detail="来访类型、可进入区域与有效期规则",
    )


def _carpass_tree(ctx: dict[str, str]) -> list[RoleTree]:
    return _apply_flow_tree(
        ctx,
        biz="车辆通行证",
        apply_detail="填写车牌、车主信息与申请期限后提交",
        mine_detail="查看待审/已生效/已过期/已驳回等状态；可出示通行码（材料写到则启用）",
        audit_detail="审批通行证、维护有效期与进出登记",
        master_label="通行证类型模块",
        master_detail="通行证类别、有效期规则与区域范围",
    )


def _procure_tree(ctx: dict[str, str]) -> list[RoleTree]:
    return _apply_flow_tree(
        ctx,
        biz="采购申购",
        apply_detail="填写申购品目、数量、预估金额与比价说明后提交",
        mine_detail="查看待审/已批准/采购中/已入库/已驳回等状态",
        audit_detail="审批申购、登记采购进度、确认入库",
        master_label="品类与供应商模块",
        master_detail="采购品类、常用供应商与预算科目说明",
        admin_extra=[
            _m("入库台账模块", "申购入库记录查询"),
        ],
    )


def _proj_tree(ctx: dict[str, str]) -> list[RoleTree]:
    return _apply_flow_tree(
        ctx,
        biz="项目申报",
        apply_detail="填写项目名称、成员与摘要，上传申报书后提交",
        mine_detail="查看申报/评审中/已立项/中期/结题/已驳回等阶段状态",
        audit_detail="组织评审、立项确认、中期检查与结题验收",
        master_label="项目类别模块",
        master_detail="项目类别、申报批次与材料模板",
        admin_extra=[
            _m("项目过程台账模块", "立项中期结题进度总览"),
        ],
    )


def _ethic_tree(ctx: dict[str, str]) -> list[RoleTree]:
    return _apply_flow_tree(
        ctx,
        biz="伦理审查",
        apply_detail="填写研究摘要与风险说明，上传伦理材料后申报",
        mine_detail="查看待审/会议审查中/已批件/需补正/已驳回等状态",
        audit_detail="形式审查、上会安排、批件发放与补正跟踪",
        master_label="审查类型模块",
        master_detail="审查类别、会议批次与材料清单",
        admin_extra=[
            _m("批件跟踪模块", "批件编号与有效期登记"),
        ],
    )


def _party_tree(ctx: dict[str, str]) -> list[RoleTree]:
    return _apply_flow_tree(
        ctx,
        biz="党员发展",
        apply_detail="按发展阶段递交思想汇报、培养考察等材料",
        mine_detail="查看积极分子/发展对象/预备党员/转正等阶段进度",
        audit_detail="材料审核、阶段确认与转正办理",
        master_label="发展阶段配置模块",
        master_detail="发展阶段、材料清单与时限要求",
    )


def _contract_tree(ctx: dict[str, str]) -> list[RoleTree]:
    return _apply_flow_tree(
        ctx,
        biz="合同",
        apply_detail="起草合同要素、上传附件后提交审批",
        mine_detail="查看起草/审批中/已签署/已归档/已驳回等状态；电子签（材料写到则启用，非法定 CA）",
        audit_detail="合同审批、签署确认、归档编号",
        master_label="合同类型模板模块",
        master_detail="合同类别、必备条款提示与归档规则",
        admin_extra=[
            _m("合同台账模块", "按对方单位/类型查询合同"),
        ],
    )


def _activity_tree(ctx: dict[str, str]) -> list[RoleTree]:
    user, admin = ctx["user"], ctx["admin"]
    return _dual(
        f"{user}功能模块划分",
        [
            _auth_profile(),
            _m("活动浏览报名模块", "浏览活动、报名/取消、候补（材料写到则启用）"),
            _m("我的报名模块", "报名状态、签到、电子票/证书查阅"),
            _m("评价与支付模块", "活动评价；系统内缴费（模拟支付）"),
            _m("公告与留言模块", "查阅公告；留言反馈"),
        ],
        f"{admin}功能模块划分",
        [
            _m("登录模块", "登录与修改密码"),
            _m(
                "活动发布管理模块",
                "发布活动、名额、审核报名、签到核销、证书/票务、候补处理",
            ),
            _m("评价与缴费管理模块", "查看评价；核对缴费记录"),
            *_notice_guestbook_stats_admin(),
        ],
    )


def _course_tree(ctx: dict[str, str]) -> list[RoleTree]:
    user, admin = ctx["user"], ctx["admin"]
    return _dual(
        f"{user}功能模块划分",
        [
            _auth_profile(),
            _m("选课模块", "选课、退改、冲突提示、候补（材料写到则启用）"),
            _m("我的课表模块", "已选课程与课表查阅"),
            _m("公告与留言模块", "查阅选课须知；留言反馈"),
        ],
        f"{admin}功能模块划分",
        [
            _m("登录模块", "登录与修改密码"),
            _m("课程与名额模块", "开课、名额、审核退改、候补处理"),
            _m("学生选课管理模块", "查询调整学生选课记录"),
            *_notice_guestbook_stats_admin(),
        ],
    )


def _lost_tree(ctx: dict[str, str]) -> list[RoleTree]:
    user, admin = ctx["user"], ctx["admin"]
    return _dual(
        f"{user}功能模块划分",
        [
            _auth_profile(),
            _m("失物登记模块", "登记失物/招领信息，上传图片说明"),
            _m("认领申请模块", "申请认领并跟踪审核归还"),
            _m("我的登记模块", "本人发布与认领进度"),
            _m("公告与留言模块", "查阅公告；留言反馈"),
        ],
        f"{admin}功能模块划分",
        [
            _m("登录模块", "登录与修改密码"),
            _m("招领审核模块", "审核登记、认领、归还办结；领养/捐赠细档"),
            _m("分类与用户管理模块", "分类维护与用户管理"),
            *_notice_guestbook_stats_admin(),
        ],
    )


def _tour_tree(ctx: dict[str, str]) -> list[RoleTree]:
    user, admin = ctx["user"], ctx["admin"]
    return _dual(
        f"{user}功能模块划分",
        [
            _auth_profile(),
            _m("线路浏览报名模块", "浏览线路、报名、取消"),
            _m("缴费模块", "系统内缴费（模拟支付）"),
            _m("我的行程模块", "报名状态、出团信息、评价"),
            _m("公告与留言模块", "查阅公告；留言反馈"),
        ],
        f"{admin}功能模块划分",
        [
            _m("登录模块", "登录与修改密码"),
            _m("线路与报名管理模块", "发布线路、审核报名、出团、取消处理"),
            _m("缴费与评价管理模块", "核对缴费；查看评价"),
            *_notice_guestbook_stats_admin(),
        ],
    )


def _reserve_tree(
    ctx: dict[str, str],
    *,
    item: str,
    user_detail: str,
    admin_detail: str,
    extras_user: list[Module] | None = None,
    extras_admin: list[Module] | None = None,
) -> list[RoleTree]:
    user, admin = ctx["user"], ctx["admin"]
    u = [
        _auth_profile(),
        _m(f"{item}预约模块", user_detail),
        _m("我的预约模块", "预约状态、取消改约、签到履约记录"),
        _m("公告与留言模块", "查阅公告；留言反馈"),
    ]
    if extras_user:
        u[2:2] = extras_user
    a = [
        _m("登录模块", "登录与修改密码"),
        _m(f"{item}资源管理模块", admin_detail),
        _m("预约审批模块", "审批、取消处理、签到核销、超时与催办"),
        *_notice_guestbook_stats_admin(),
    ]
    if extras_admin:
        a[2:2] = extras_admin
    return _dual(f"{user}功能模块划分", u, f"{admin}功能模块划分", a)


def _hotel_tree(ctx: dict[str, str]) -> list[RoleTree]:
    return _reserve_tree(
        ctx,
        item="客房",
        user_detail="房型浏览、日历选日、预订、定金支付（模拟）、取消",
        admin_detail="房型、房价、可售日历维护",
        extras_user=[
            _m("评价模块", "入住完成后评价"),
            _m("支付模块", "系统内定金/房费模拟支付"),
        ],
        extras_admin=[_m("入住与评价管理模块", "签到办理、查看评价")],
    )


def _hospital_tree(ctx: dict[str, str]) -> list[RoleTree]:
    return _reserve_tree(
        ctx,
        item="号源",
        user_detail="科室/医生号源预约、取消、候诊顺序查阅",
        admin_detail="科室、号源时段与限额维护",
        extras_user=[_m("签到候诊模块", "到院签到与候诊状态")],
    )


def _parking_tree(ctx: dict[str, str]) -> list[RoleTree]:
    return _reserve_tree(
        ctx,
        item="车位",
        user_detail="车位预约、缴费（模拟支付）、取消",
        admin_detail="车位资源与开放时段维护",
        extras_user=[_m("进出记录模块", "预约进出与缴费记录查询")],
        extras_admin=[_m("缴费与审核模块", "预约审核、缴费核对")],
    )


def _meeting_tree(ctx: dict[str, str]) -> list[RoleTree]:
    return _reserve_tree(
        ctx,
        item="会议室",
        user_detail="按时段预约、冲突提示、取消、签到；可查看设备清单（材料写到则启用）",
        admin_detail="会议室、开放时段、设备清单维护",
        extras_admin=[_m("超时催办模块", "超时占用提醒与统计")],
    )


def _salon_tree(ctx: dict[str, str]) -> list[RoleTree]:
    user, admin = ctx["user"], ctx["admin"]
    worker = ctx.get("worker", "技师")
    return [
        _role(
            f"{user}功能模块划分",
            [
                _auth_profile(),
                _m("项目预约模块", "选择项目/技师/时段预约、取消、支付（模拟）"),
                _m("我的预约模块", "预约状态与履约记录"),
                _m("评价模块", "服务完成后评价"),
                _m("公告与留言模块", "查阅公告；留言反馈"),
            ],
        ),
        _role(
            f"{worker}功能模块划分",
            [
                _m("登录模块", "登录与资料"),
                _m("我的排班与预约模块", "查看排班与当日预约单"),
            ],
        ),
        _role(
            f"{admin}功能模块划分",
            [
                _m("登录模块", "登录与修改密码"),
                _m("项目与技师管理模块", "项目、技师档案与排班（材料写到则启用）"),
                _m("预约与支付管理模块", "审批/核销预约、核对模拟支付、查看评价"),
                *_notice_guestbook_stats_admin(),
            ],
        ),
    ]


def _carrent_tree(ctx: dict[str, str]) -> list[RoleTree]:
    return _reserve_tree(
        ctx,
        item="租车",
        user_detail="车型浏览、租期预订、定金支付（模拟）、取消",
        admin_detail="车型档案、库存与租价维护",
        extras_user=[_m("取还车模块", "取车/还车状态查询")],
        extras_admin=[_m("取还车办理模块", "审核、取还车确认、定金处理")],
    )


def _forum_tree(ctx: dict[str, str]) -> list[RoleTree]:
    user, admin = ctx["user"], ctx["admin"]
    return _dual(
        f"{user}功能模块划分",
        [
            _auth_profile(),
            _m("发帖回帖模块", "发帖、回帖、编辑删除本人内容"),
            _m("互动模块", "收藏、点赞、热搜浏览；私信（材料写到则启用）"),
            _m("举报模块", "举报不当内容（材料写到则启用）"),
            _m("公告查阅模块", "查看公告"),
        ],
        f"{admin}功能模块划分",
        [
            _m("登录模块", "登录与修改密码"),
            _m("内容审核模块", "审帖、删帖、下架；禁言（材料写到则启用）"),
            _m("举报处理模块", "处理举报工单"),
            _m("用户与板块管理模块", "用户管理、板块分类"),
            _m("公告与统计模块", "公告发布与活跃概览"),
        ],
    )


def _media_tree(ctx: dict[str, str]) -> list[RoleTree]:
    """主路径：浏览 → 播放 → 收藏。留言=guestbook；条下评论扫词开。"""
    user, admin = ctx["user"], ctx["admin"]
    return _dual(
        f"{user}功能模块划分",
        [
            _auth_profile(),
            _m("影音浏览播放模块", "分类浏览、检索、播放片源"),
            _m("收藏模块", "收藏或取消收藏；在「我的收藏」中查看"),
            _m("评论模块", "在片源详情下发表与查看评论（材料写到则启用；≠ 门户留言）"),
            _m("投稿上传模块", "上传片源链接（材料写到则启用；写了投稿审核/先审后发则待审后展示，否则即时上架）"),
            _m("公告查阅模块", "查看系统公告与资源上新须知"),
            _m("留言反馈模块", "向管理员留言并查看回复（≠ 片下评论）"),
        ],
        f"{admin}功能模块划分",
        [
            _m("登录模块", "登录与修改密码"),
            _m("片库与分类维护模块", "片库增删改、分类维护、上下架"),
            _m("评论管理模块", "删除不当条下评论（材料写到则启用）"),
            *_notice_guestbook_stats_admin(),
        ],
    )


def _music_tree(ctx: dict[str, str]) -> list[RoleTree]:
    """主路径：浏览 → 点播 → 收藏夹。留言=guestbook；条下评论扫词开。"""
    user, admin = ctx["user"], ctx["admin"]
    return _dual(
        f"{user}功能模块划分",
        [
            _auth_profile(),
            _m("曲库点播模块", "分类检索、点播试听"),
            _m("收藏模块", "收藏或取消收藏曲目；在「我的收藏」中查看（收藏夹，非独立歌单协作）"),
            _m("评论模块", "在曲目详情下发表与查看评论（材料写到则启用；≠ 门户留言）"),
            _m("曲目上传模块", "上传曲目试听链接（材料写「用户上传」则启用；写了先审后发则待审后展示，否则即时上架）"),
            _m("公告查阅模块", "查看系统公告与上新须知"),
            _m("留言反馈模块", "向管理员留言并查看回复（≠ 曲下评论）"),
        ],
        f"{admin}功能模块划分",
        [
            _m("登录模块", "登录与修改密码"),
            _m("曲库与分类维护模块", "曲目增删改、分类维护、上下架"),
            _m("评论管理模块", "删除不当条下评论（材料写到则启用）"),
            *_notice_guestbook_stats_admin(),
        ],
    )


def _blog_tree(ctx: dict[str, str]) -> list[RoleTree]:
    """主路径：浏览 → 阅读 → 收藏。留言=guestbook；条下评论扫词开。"""
    user, admin = ctx["user"], ctx["admin"]
    return _dual(
        f"{user}功能模块划分",
        [
            _auth_profile(),
            _m("专栏阅读模块", "按专栏分类浏览与检索文章、阅读正文"),
            _m("收藏模块", "收藏或取消收藏；在「我的收藏」中查看"),
            _m("评论模块", "在文章详情下发表与查看评论（材料写到则启用；≠ 门户留言）"),
            _m("投稿发布模块", "在线投稿（材料写到则启用；写了投稿审核/先审后发则待审后展示，否则即时可见）"),
            _m("公告查阅模块", "查看系统公告"),
            _m("留言反馈模块", "向管理员留言并查看回复（≠ 文下评论）"),
        ],
        f"{admin}功能模块划分",
        [
            _m("登录模块", "登录与修改密码"),
            _m("文章与专栏维护模块", "文章增删改、专栏分类、上下架"),
            _m("评论管理模块", "删除不当条下评论（材料写到则启用）"),
            *_notice_guestbook_stats_admin(),
        ],
    )


def _exam_tree(ctx: dict[str, str]) -> list[RoleTree]:
    user, admin = ctx["user"], ctx["admin"]
    return _dual(
        f"{user}功能模块划分",
        [
            _auth_profile(),
            _m("在线考试模块", "参加考试、交卷、查看成绩与错题本"),
            _m("练习模块", "题库练习（若开放）"),
            _m("公告与留言模块", "查阅考试须知；留言反馈"),
        ],
        f"{admin}功能模块划分",
        [
            _m("登录模块", "登录与修改密码"),
            _m("题库组卷模块", "题目维护、组卷、发布考试"),
            _m("阅卷成绩模块", "阅卷、成绩发布、统计分析"),
            *_notice_guestbook_stats_admin(),
        ],
    )


def _survey_tree(ctx: dict[str, str]) -> list[RoleTree]:
    user, admin = ctx["user"], ctx["admin"]
    return _dual(
        f"{user}功能模块划分",
        [
            _auth_profile(),
            _m("问卷填写模块", "填写问卷、提交、查看是否已填"),
            _m("公告查阅模块", "查看通知"),
        ],
        f"{admin}功能模块划分",
        [
            _m("登录模块", "登录与修改密码"),
            _m("问卷发布模块", "设计发布问卷、回收统计、导出"),
            *_notice_guestbook_stats_admin(),
        ],
    )


def _vote_tree(ctx: dict[str, str]) -> list[RoleTree]:
    user, admin = ctx["user"], ctx["admin"]
    return _dual(
        f"{user}功能模块划分",
        [
            _auth_profile(),
            _m("投票模块", "查看候选项、投票、查看公示"),
            _m("公告查阅模块", "查看评选公告"),
        ],
        f"{admin}功能模块划分",
        [
            _m("登录模块", "登录与修改密码"),
            _m("评选管理模块", "配置候选项、计票、公示结果"),
            *_notice_guestbook_stats_admin(),
        ],
    )


def _doclib_tree(ctx: dict[str, str]) -> list[RoleTree]:
    user, admin = ctx["user"], ctx["admin"]
    return _dual(
        f"{user}功能模块划分",
        [
            _auth_profile(),
            _m("资料浏览下载模块", "分类检索、下载、查看下载台账"),
            _m("上传投稿模块", "上传资料并等待审核"),
            _m("公告与留言模块", "查阅公告；留言反馈"),
        ],
        f"{admin}功能模块划分",
        [
            _m("登录模块", "登录与修改密码"),
            _m("文库管理模块", "审核上下架、分类、下载台账"),
            *_notice_guestbook_stats_admin(),
        ],
    )


def _dating_tree(ctx: dict[str, str]) -> list[RoleTree]:
    user, admin = ctx["user"], ctx["admin"]
    return _dual(
        f"{user}功能模块划分",
        [
            _auth_profile("相亲资料完善"),
            _m("资料筛选配对模块", "按条件筛选、发起配对意向"),
            _m("私信模块", "站内私信沟通"),
            _m("举报模块", "举报不当用户或内容（材料写到则启用）"),
            _m("公告查阅模块", "查看公告"),
        ],
        f"{admin}功能模块划分",
        [
            _m("登录模块", "登录与修改密码"),
            _m("资料审核模块", "审核用户资料与配对记录"),
            _m("举报与用户管理模块", "处理举报、启用停用"),
            *_notice_guestbook_stats_admin()[:2],
            _m("数据统计模块", "配对与活跃概览"),
        ],
    )


def _recruit_tree(ctx: dict[str, str]) -> list[RoleTree]:
    user, admin = ctx["user"], ctx["admin"]
    return _dual(
        f"{user}功能模块划分",
        [
            _auth_profile("简历资料"),
            _m("岗位浏览投递模块", "浏览岗位、投递简历、查看进度"),
            _m("我的投递模块", "初筛/面试/录用状态查询"),
            _m("公告与留言模块", "查阅招聘公告；留言反馈"),
        ],
        f"{admin}功能模块划分",
        [
            _m("登录模块", "登录与修改密码"),
            _m("岗位管理模块", "发布岗位、上下架"),
            _m("简历筛选模块", "初筛、面试、录用状态推进"),
            *_notice_guestbook_stats_admin(),
        ],
    )


def _intern_tree(ctx: dict[str, str]) -> list[RoleTree]:
    user, admin = ctx["user"], ctx["admin"]
    return _dual(
        f"{user}功能模块划分",
        [
            _auth_profile(),
            _m("岗位绑定模块", "选择/绑定实习岗位"),
            _m("周报模块", "提交周报、查看签核意见；电子签（材料写到则启用）"),
            _m("公告与留言模块", "查阅公告；留言反馈"),
        ],
        f"{admin}功能模块划分",
        [
            _m("登录模块", "登录与修改密码"),
            _m("岗位与学生管理模块", "岗位维护、学生绑定"),
            _m("周报签核模块", "审阅周报、签核"),
            *_notice_guestbook_stats_admin(),
        ],
    )


def _grade_tree(ctx: dict[str, str]) -> list[RoleTree]:
    user, admin = ctx["user"], ctx["admin"]
    return _dual(
        f"{user}功能模块划分",
        [
            _auth_profile(),
            _m("成绩查询模块", "查询已发布成绩及课内名次"),
            _m("成绩申诉模块", "对成绩提出申诉并跟踪"),
            _m("公告查阅模块", "查看成绩发布公告"),
        ],
        f"{admin}功能模块划分",
        [
            _m("登录模块", "登录与修改密码"),
            _m("成绩录入复核模块", "录入分数、按课程排名、导出 CSV"),
            _m("申诉处理模块", "处理学生申诉"),
            *_notice_guestbook_stats_admin(),
        ],
    )


def _parcel_tree(ctx: dict[str, str]) -> list[RoleTree]:
    user, admin = ctx["user"], ctx["admin"]
    return _dual(
        f"{user}功能模块划分",
        [
            _auth_profile(),
            _m("到件查询取件模块", "查询到件、取件码核销、滞留催领提醒"),
            _m("公告与留言模块", "查阅公告；留言反馈"),
        ],
        f"{admin}功能模块划分",
        [
            _m("登录模块", "登录与修改密码"),
            _m("到件入库模块", "录入到件、生成取件码、核销、滞留处理"),
            *_notice_guestbook_stats_admin(),
        ],
    )


def _cinema_tree(ctx: dict[str, str]) -> list[RoleTree]:
    user, admin = ctx["user"], ctx["admin"]
    return _dual(
        f"{user}功能模块划分",
        [
            _auth_profile(),
            _m("排片选座模块", "选影片场次、选座、下单"),
            _m("支付出票模块", "系统内支付（模拟）、出票、退票申请"),
            _m("我的订单模块", "订单与影票查询"),
            _m("公告与留言模块", "查阅公告；留言反馈"),
        ],
        f"{admin}功能模块划分",
        [
            _m("登录模块", "登录与修改密码"),
            _m("排片影厅管理模块", "影片、场次、座位图维护"),
            _m("订单退票管理模块", "订单查询、退票审核"),
            *_notice_guestbook_stats_admin(),
        ],
    )


def _carpool_tree(ctx: dict[str, str]) -> list[RoleTree]:
    user, admin = ctx["user"], ctx["admin"]
    return _dual(
        f"{user}功能模块划分",
        [
            _auth_profile(),
            _m("行程发布预约模块", "发布行程或预约座位、成行确认、取消"),
            _m("评价模块", "行程结束后互评"),
            _m("公告与留言模块", "查阅公告；留言反馈"),
        ],
        f"{admin}功能模块划分",
        [
            _m("登录模块", "登录与修改密码"),
            _m("行程审核管理模块", "审核行程、处理纠纷取消、查看评价"),
            *_notice_guestbook_stats_admin(),
        ],
    )


def _mutual_tree(ctx: dict[str, str]) -> list[RoleTree]:
    user, admin = ctx["user"], ctx["admin"]
    peer = ctx.get("peer", "对方用户")
    return _dual(
        f"{user}功能模块划分",
        [
            _auth_profile(),
            _m("志愿填报模块", f"填报志愿/意向，与{peer}双边确认"),
            _m("匹配结果模块", "查看匹配/组队结果与名额状态"),
            _m("公告与留言模块", "查阅公告；留言反馈"),
        ],
        f"{admin}功能模块划分",
        [
            _m("登录模块", "登录与修改密码"),
            _m("双选审核模块", "审核确认、名额调控、调剂"),
            _m("基础数据模块", "志愿项/导师或队伍档案维护"),
            *_notice_guestbook_stats_admin(),
        ],
    )


def _timebank_tree(ctx: dict[str, str]) -> list[RoleTree]:
    user, admin = ctx["user"], ctx["admin"]
    return _dual(
        f"{user}功能模块划分",
        [
            _auth_profile(),
            _m("服务发布兑换模块", "发布服务、兑换时长、完成确认"),
            _m("评价模块", "服务评价"),
            _m("我的时长模块", "时长收支明细"),
            _m("公告与留言模块", "查阅公告；留言反馈"),
        ],
        f"{admin}功能模块划分",
        [
            _m("登录模块", "登录与修改密码"),
            _m("服务审核模块", "审核服务与兑换、处理评价"),
            *_notice_guestbook_stats_admin(),
        ],
    )


def _listing_tree(ctx: dict[str, str]) -> list[RoleTree]:
    user, admin = ctx["user"], ctx["admin"]
    return _dual(
        f"{user}功能模块划分",
        [
            _auth_profile(),
            _m("房源浏览模块", "检索浏览房源详情"),
            _m("发布与带看模块", "发布房源、预约带看、留言咨询"),
            _m("公告查阅模块", "查看公告"),
        ],
        f"{admin}功能模块划分",
        [
            _m("登录模块", "登录与修改密码"),
            _m("房源审核模块", "审核上下架、处理带看与留言"),
            *_notice_guestbook_stats_admin(),
        ],
    )


def _club_tree(ctx: dict[str, str]) -> list[RoleTree]:
    user, admin = ctx["user"], ctx["admin"]
    return _dual(
        f"{user}功能模块划分",
        [
            _auth_profile(),
            _m("社团注册加入模块", "申请建社/加入、成员信息"),
            _m("活动与经费模块", "社团活动报名、经费申请进度"),
            _m("公告与留言模块", "查阅公告；留言反馈"),
        ],
        f"{admin}功能模块划分",
        [
            _m("登录模块", "登录与修改密码"),
            _m("社团审批模块", "注册审批、成员与活动审批、经费审核"),
            *_notice_guestbook_stats_admin(),
        ],
    )


def _instrument_tree(ctx: dict[str, str]) -> list[RoleTree]:
    return _reserve_tree(
        ctx,
        item="仪器机时",
        user_detail="预约机时、使用登记、超时查看",
        admin_detail="仪器档案、开放机时与计费规则",
        extras_admin=[_m("维护与计费模块", "维护记录、超时计费核对")],
    )


def _labsafe_tree(ctx: dict[str, str]) -> list[RoleTree]:
    user, admin = ctx["user"], ctx["admin"]
    return _dual(
        f"{user}功能模块划分",
        [
            _auth_profile(),
            _m("准入申请模块", "提交准入材料、参加培训/考试、查看许可有效期"),
            _m("我的许可模块", "许可状态与到期提醒"),
            _m("公告与留言模块", "查阅安全须知；留言反馈"),
        ],
        f"{admin}功能模块划分",
        [
            _m("登录模块", "登录与修改密码"),
            _m("准入审核模块", "材料审核、培训考试结果、许可发放与到期管理"),
            *_notice_guestbook_stats_admin(),
        ],
    )


def _generic_from_features(pack: dict[str, Any], ctx: dict[str, str]) -> list[RoleTree]:
    """交叉包兜底：把扁平 features 拆成用户/管理两侧模块列表。"""
    user, admin = ctx["user"], ctx["admin"]
    feats = [str(f).rstrip("。.") for f in (pack.get("features") or []) if f]
    mid = max(1, (len(feats) + 1) // 2)
    u_mods = [_m(f"功能{i}", f) for i, f in enumerate(feats[:mid], 1)] or [
        _auth_profile()
    ]
    a_mods = [_m(f"管理功能{i}", f) for i, f in enumerate(feats[mid:], 1)] or [
        _m("业务管理模块", "审核办理与基础数据维护"),
        *_notice_guestbook_stats_admin()[:2],
    ]
    return _dual(f"{user}功能模块划分", u_mods, f"{admin}功能模块划分", a_mods)


_DOMAIN_BUILDERS: dict[str, Any] = {
    "DOM-SHOP": _shop_tree,
    "DOM-FOOD": _food_tree,
    "DOM-DORM": _repair_tree,
    "DOM-PROPERTY": _repair_tree,
    "DOM-IT": _repair_tree,
    "DOM-LIBRARY": _library_tree,
    "DOM-EQUIP": lambda c: _borrow_like(c, item="设备"),
    "DOM-ASSET": _asset_tree,
    "DOM-CRM": _crm_tree,
    "DOM-EVENT": _event_tree,
    "DOM-ATTEND": _attend_tree,
    "DOM-FUND": _fund_tree,
    "DOM-LABSAFE": _labsafe_tree,
    "DOM-RECRUIT": _recruit_tree,
    "DOM-DATING": _dating_tree,
    "DOM-GRADE": _grade_tree,
    "DOM-INTERN": _intern_tree,
    "DOM-PARCEL": _parcel_tree,
    "DOM-SEAL": _seal_tree,
    "DOM-FLEET": _fleet_tree,
    "DOM-CERT": _cert_tree,
    "DOM-PROMO": _promo_tree,
    "DOM-FITOUT": _fitout_tree,
    "DOM-ACAD": _acad_tree,
    "DOM-TRIP": _trip_tree,
    "DOM-EXPENSE": _expense_tree,
    "DOM-CREDIT": _credit_tree,
    "DOM-LABOR": _labor_tree,
    "DOM-EVAL": _eval_tree,
    "DOM-MORAL": _moral_tree,
    "DOM-AWARD": _award_tree,
    "DOM-BED": _bed_tree,
    "DOM-CHECKIN": _checkin_tree,
    "DOM-VISITOR": _visitor_tree,
    "DOM-CARPASS": _carpass_tree,
    "DOM-LISTING": _listing_tree,
    "DOM-PROCURE": _procure_tree,
    "DOM-CLUB": _club_tree,
    "DOM-PROJ": _proj_tree,
    "DOM-ETHIC": _ethic_tree,
    "DOM-PARTY": _party_tree,
    "DOM-CONTRACT": _contract_tree,
    "DOM-INSTRUMENT": _instrument_tree,
    "DOM-EXAM": _exam_tree,
    "DOM-SURVEY": _survey_tree,
    "DOM-VOTE": _vote_tree,
    "DOM-DOCLIB": _doclib_tree,
    "DOM-CARPOOL": _carpool_tree,
    "DOM-TIMEBANK": _timebank_tree,
    "DOM-CINEMA": _cinema_tree,
    "DOM-ACTIVITY": _activity_tree,
    "DOM-LOST": _lost_tree,
    "DOM-COURSE": _course_tree,
    "DOM-TOUR": _tour_tree,
    "DOM-HOTEL": _hotel_tree,
    "DOM-HOSPITAL": _hospital_tree,
    "DOM-PARKING": _parking_tree,
    "DOM-MEETING": _meeting_tree,
    "DOM-SALON": _salon_tree,
    "DOM-CARRENT": _carrent_tree,
    "DOM-MEDIA": _media_tree,
    "DOM-MUSIC": _music_tree,
    "DOM-FORUM": _forum_tree,
    "DOM-BLOG": _blog_tree,
    "DOM-MUTUAL-TEAM": _mutual_tree,
    "DOM-MUTUAL-TOPIC": _mutual_tree,
    "DOM-MUTUAL-TUTOR": _mutual_tree,
}


def build_ctx(pack: dict[str, Any]) -> dict[str, str]:
    domain = str(pack.get("anchor_domain") or "")
    user = str(pack.get("user_role") or "用户")
    admin = str(pack.get("admin_role") or "管理人员")
    merchant = str(pack.get("merchant_role") or "")
    worker = str(pack.get("worker_role") or "")
    goods = str(pack.get("goods_label") or "")
    peer = str(pack.get("peer_role") or "对方用户")
    if not merchant:
        if domain == "DOM-SHOP":
            merchant = "商家"
        elif domain == "DOM-FOOD":
            merchant = "档口商家"
        else:
            merchant = "业务经办"
    if not worker:
        if domain in {"DOM-DORM", "DOM-PROPERTY", "DOM-IT"}:
            worker = "维修人员"
        elif domain == "DOM-FOOD":
            worker = "配送员"
        elif domain == "DOM-SALON":
            worker = "技师"
        else:
            worker = "现场岗位"
    if not goods:
        goods = "商品"
    return {
        "user": user,
        "admin": admin,
        "merchant": merchant,
        "worker": worker,
        "goods": goods,
        "peer": peer,
    }


def _normalize_pack_tree(raw: list[Any], ctx: dict[str, str]) -> list[RoleTree]:
    out: list[RoleTree] = []
    for block in raw:
        if not isinstance(block, dict):
            continue
        title = _fmt(str(block.get("title") or "功能模块划分"), ctx)
        mods_raw = block.get("modules") or []
        mods: list[Module] = []
        for m in mods_raw:
            if isinstance(m, (list, tuple)) and len(m) >= 2:
                mods.append((_fmt(str(m[0]), ctx), _fmt(str(m[1]), ctx)))
            elif isinstance(m, dict) and m.get("name"):
                mods.append(
                    (
                        _fmt(str(m["name"]), ctx),
                        _fmt(str(m.get("detail") or ""), ctx),
                    )
                )
        if mods:
            out.append(_role(title, _fmt_modules(mods, ctx)))
    return out


def resolve_role_modules(pack: dict[str, Any]) -> list[RoleTree]:
    """返回已换皮的角色模块树。"""
    ctx = build_ctx(pack)
    raw = pack.get("role_modules")
    if isinstance(raw, list) and raw:
        return _normalize_pack_tree(raw, ctx)

    domain = str(pack.get("anchor_domain") or "")
    builder = _DOMAIN_BUILDERS.get(domain)
    if builder is None:
        return _generic_from_features(pack, ctx)

    tree = builder(ctx)
    # 再跑一遍 format，防止 builder 内漏换皮
    return [
        _role(r["title"], _fmt_modules(list(r["modules"]), ctx))
        for r in tree
    ]


def render_role_modules_block(
    roles: list[RoleTree],
    *,
    l1_extras: list[str] | None = None,
    ai_line: str | None = None,
) -> str:
    """渲染「（二）主要功能」下的角色模块树正文。"""
    parts: list[str] = []
    for role in roles:
        title = str(role.get("title") or "功能模块划分")
        lines = [f"{title}："]
        mods = list(role.get("modules") or [])
        chunks = [f"{name}【{detail}】" for name, detail in mods]
        lines.append("、".join(chunks) + "。")
        parts.append("\n".join(lines))

    if ai_line:
        parts.append(f"另设智能助手能力：{ai_line.rstrip('。')}")

    extras = list(l1_extras or [])
    if extras:
        extra_txt = "、".join(extras)
        parts.append(f"若进度允许，可补充{extra_txt}。")

    return "\n\n".join(parts)


def roles_para_from_tree(roles: list[RoleTree], pack: dict[str, Any]) -> str:
    """由角色树生成「用户与权限」概述；pack.roles_para 优先。"""
    if pack.get("roles_para"):
        return str(pack["roles_para"])
    names = []
    for r in roles:
        t = str(r.get("title") or "")
        if t.endswith("功能模块划分"):
            names.append(t[: -len("功能模块划分")])
        elif t:
            names.append(t)
    if not names:
        user = pack.get("user_role") or "用户"
        admin = pack.get("admin_role") or "管理人员"
        return f"系统面向{user}与{admin}，按角色划分功能模块与数据权限。"
    if len(names) == 1:
        who = names[0]
    elif len(names) == 2:
        who = f"{names[0]}与{names[1]}"
    else:
        who = "、".join(names[:-1]) + f"与{names[-1]}"
    return (
        f"系统面向{who}。"
        f"各角色登录后进入对应功能模块；总管与业务岗位职责在菜单与权限中划分，"
        f"防止越权查看或办理他人业务。"
    )


def flatten_role_module_text(roles: list[RoleTree]) -> str:
    """供 AI 启发词检测等使用的纯文本拼接。"""
    bits: list[str] = []
    for r in roles:
        bits.append(str(r.get("title") or ""))
        for name, detail in r.get("modules") or []:
            bits.append(f"{name}{detail}")
    return "".join(bits)
