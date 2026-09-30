package com.thesis.config;

/**
 * 非单据业务规则与功能开关（档案表位、下拉主数据、订单/预约表、能力岛）。
 * <p>按本系统开题口径生成；单据相关常量见 {@link TicketPolicy}，两处不要互相搬键。</p>
 * <p>需要调整业务口径时改这里的常量即可。</p>
 */
public final class AppPolicy {

    private AppPolicy() {}

    // ---------- 档案 / 订单 / 预约表位 ----------
    /** 档案分类表名 */
    public static final String ARCHIVE_CATEGORY_TABLE = "category";
    /** 档案条目表名 */
    public static final String ARCHIVE_ITEM_TABLE = "book";
    /** 档案标签表名；空串表示未启用标签 */
    public static final String ARCHIVE_TAG_TABLE = "";
    /** 档案条目-标签关联表；空串表示未启用 */
    public static final String ARCHIVE_ITEM_TAG_TABLE = "";
    /** 购物车表名；空串表示未启用订单 */
    public static final String ORDER_CART_TABLE = "";
    /** 订单主表名 */
    public static final String ORDER_TABLE = "";
    /** 订单明细表名 */
    public static final String ORDER_LINE_TABLE = "";
    /** 可预约时段表名 */
    public static final String SLOT_TABLE = "";
    /** 预约记录表名 */
    public static final String RESERVATION_TABLE = "";
    /** 下拉主数据：楼栋 / 站点表 */
    public static final String LOOKUP_SITE_TABLE = "";
    /** 下拉主数据：房间 / 单元表 */
    public static final String LOOKUP_UNIT_TABLE = "";
    /** 下拉主数据：类型表 */
    public static final String LOOKUP_TYPE_TABLE = "";

    // ---------- 下拉展示标签 ----------
    /** 楼栋 / 站点列展示名 */
    public static final String LOOKUP_SITE_LABEL = "楼栋";
    /** 房间 / 单元列展示名 */
    public static final String LOOKUP_UNIT_LABEL = "房间";
    /** 单元容量列展示名；空串表示隐藏该列 */
    public static final String LOOKUP_UNIT_CAPACITY_LABEL = "容量";
    /** 类型列展示名 */
    public static final String LOOKUP_TYPE_LABEL = "类型";

    // ---------- 数值阈值 ----------
    /** 库存预警阈值（件） */
    public static final int STOCK_WARN_BELOW = 10;
    /** 每消费一元赠送的积分 */
    public static final int POINTS_EARN_PER_YUAN = 1;

    // ---------- 能力开关（按开题启用） ----------
    /** 档案软删除（标记删除，不物理抹掉） */
    public static final boolean ARCHIVE_SOFT_DELETE = false;
    /** 允许用户自行发布档案内容 */
    public static final boolean ARCHIVE_USER_PUBLISH = false;
    /** 用户发布需审核后上架 */
    public static final boolean ARCHIVE_PUBLISH_REVIEW = false;
    /** 档案变更日志 */
    public static final boolean ARCHIVE_LOG_ENABLED = false;
    /** 店铺入驻 / 多商家市集 */
    public static final boolean SHOP_MARKETPLACE = false;
    /** 库存低于阈值时提醒 */
    public static final boolean STOCK_WARN_NOTIFY = false;
    /** 进销存流水 */
    public static final boolean STOCK_IO_ENABLED = false;
    /** 钱包余额 */
    public static final boolean WALLET_ENABLED = false;
    /** 积分账户 */
    public static final boolean POINTS_ENABLED = false;
    /** 积分直接抵付 */
    public static final boolean POINTS_PAY_ENABLED = false;
    /** 订单评价 */
    public static final boolean ORDER_REVIEW_ENABLED = false;
    /** 收藏 */
    public static final boolean FAVORITES_ENABLED = false;
    /** 物资核对 */
    public static final boolean MATERIAL_CHECK_ENABLED = false;
    /** 占用时段登记 */
    public static final boolean OCCUPY_SPAN_ENABLED = false;
    /** 在线选座 */
    public static final boolean SEAT_SELECT_ENABLED = false;
    /** 包裹上架 */
    public static final boolean PARCEL_SHELF_ENABLED = false;
    /** 领取凭证 */
    public static final boolean CLAIM_PROOF_ENABLED = false;
    /** 失物线索 */
    public static final boolean LOST_CLUE_ENABLED = false;
    /** 帖子禁言 */
    public static final boolean POST_MUTE_ENABLED = false;
    /** 内容举报 */
    public static final boolean CONTENT_REPORT_ENABLED = false;
    /** 私信走店铺客服（买家只能选商家） */
    public static final boolean DM_SHOP_CS = false;
    /** 本地签章 */
    public static final boolean E_SIGN_ENABLED = false;
    /** 在线考试 */
    public static final boolean EXAM_ENABLED = false;
    /** 文档库 */
    public static final boolean DOCLIB_ENABLED = false;
    /** 问卷 */
    public static final boolean SURVEY_ENABLED = false;
    /** 投票 */
    public static final boolean VOTE_ENABLED = false;
    /** 时间银行 */
    public static final boolean TIMEBANK_ENABLED = false;
    /** 审核通过时兑入时间币 */
    public static final boolean TIMEBANK_REDEEM_ON_APPROVE = false;
    /** 成绩分数 */
    public static final boolean GRADE_SCORES_ENABLED = false;
    /** 余额流水账 */
    public static final boolean BALANCE_LEDGER_ENABLED = false;
    /** 审核通过时扣减余额 */
    public static final boolean BALANCE_LEDGER_DEBIT_ON_APPROVE = false;
}
