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
    /** 预约开始前可免费取消的时限（小时）；0 表示不限制 */
    public static final int CANCEL_FREE_HOURS = 0;
    /** 预约改约次数上限；0 表示不限制 */
    public static final int RESCHEDULE_MAX_TIMES = 0;
    /** 预约开始前站内信提醒（分钟）；0 表示关闭 */
    public static final int REMIND_AHEAD_MINUTES = 0;
    /** 爽约次数上限；0 表示不限制 */
    public static final int NO_SHOW_LIMIT = 0;
    /** 签到迟到宽限（分钟） */
    public static final int LATE_GRACE_MINUTES = 15;
    /** 挂号退号截止（开诊前分钟）；0 表示不额外限制 */
    public static final int HOSPITAL_CANCEL_CUTOFF_MINUTES = 0;
    /** 同就诊人每日限号；0 表示不限制 */
    public static final int HOSPITAL_ID_LIMIT_PER_DAY = 0;
    /** 论坛每日发帖上限；0 表示不限制 */
    public static final int FORUM_DAILY_POST_LIMIT = 0;
    /** 内容举报处理时限（天）；0 表示不设时限 */
    public static final int REPORT_HANDLE_DAYS = 0;
    /** 车位小时费率（元）；0 表示未启用时长计费 */
    public static final int PARKING_HOURLY_YUAN = 0;
    /** 车位超时加收默认金额（元）；0 表示未启用 */
    public static final int PARKING_OVERTIME_YUAN = 0;
    /** 会议室最低预约时长（分钟）；0 表示不限制 */
    public static final int MEETING_MIN_DURATION_MINUTES = 0;
    /** 美业改约手续费默认金额（元）；0 表示未启用 */
    public static final int SALON_RESCHEDULE_FEE_YUAN = 0;
    /** 客房延迟退房加收默认金额（元）；0 表示未启用 */
    public static final int HOTEL_LATE_CHECKOUT_FEE_YUAN = 0;
    /** 租车里程超支加收默认金额（元）；0 表示未启用 */
    public static final int CARRENT_MILEAGE_OVER_FEE_YUAN = 0;
    /** 仪器机时超时加收默认金额（元）；0 表示未启用 */
    public static final int INSTRUMENT_OVERTIME_YUAN = 0;

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
    /** 发帖/跟帖本地敏感词拦截 */
    public static final boolean CONTENT_SENSITIVE_FILTER = false;
    /** 跟帖 @登录名 站内信提醒 */
    public static final boolean CONTENT_MENTION_NOTIFY = false;
    /** 专栏/分类订阅与更新站内信 */
    public static final boolean CONTENT_CATEGORY_FOLLOW = false;
    /** 博客新评论通知作者 */
    public static final boolean CONTENT_COMMENT_AUTHOR_NOTIFY = false;
    /** 博客友情链接栏 */
    public static final boolean CONTENT_FRIEND_LINKS = false;
    /** 影音播放进度与完播标记 */
    public static final boolean CONTENT_PLAY_PROGRESS = false;
    /** 影音选集分集列表 */
    public static final boolean CONTENT_MEDIA_EPISODE = false;
    /** 片单只读分享码 */
    public static final boolean CONTENT_SHARE_CODE = false;
    public static final boolean CONTENT_FAVORITE_GROUP = false;
    /** 文库章节目录与版本记录 */
    public static final boolean CONTENT_DOCLIB_CHAPTER = false;
    /** 文库纠错与侵权投诉 */
    public static final boolean CONTENT_DOCLIB_FEEDBACK = false;
    /** 文库热门标签云 */
    public static final boolean CONTENT_DOCLIB_TAG_CLOUD = false;
    /** 文库预览/权限/限额/审核/水印 */
    public static final boolean CONTENT_DOCLIB_DOWNLOAD_GATE = false;
    /** 文库下载扣积分/点券 */
    public static final boolean CONTENT_DOCLIB_POINTS_DOWNLOAD = false;
    /** 精华帖奖励积分 */
    public static final boolean CONTENT_ESSENCE_POINTS_REWARD = false;
    /** 标精华时奖励作者的积分；0 表示不奖 */
    public static final int ESSENCE_POINTS_REWARD = 0;
    /** 每日登录奖励积分 */
    public static final boolean POINTS_CHECK_IN_ENABLED = false;
    /** 每日登录奖励积分数 */
    public static final int POINTS_CHECK_IN_AMOUNT = 10;
    /** 内容举报原因字典 */
    public static final boolean CONTENT_REPORT_REASON_DICT = false;
    /** 评论举报 */
    public static final boolean CONTENT_COMMENT_REPORT = false;
    /** 评论仅粉丝可见 */
    public static final boolean CONTENT_FOLLOWERS_ONLY_COMMENT = false;
    /** 投稿审过站内信通知 */
    public static final boolean CONTENT_PUBLISH_APPROVE_NOTIFY = false;
    /** 文库每日下载上限；0 表示不限制 */
    public static final int DOCLIB_DAILY_DOWNLOAD_LIMIT = 0;
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
    /** 预约须填写备注 */
    public static final boolean SLOT_REQUIRE_REMARK = false;
    /** 预约须管理端确认 */
    public static final boolean SLOT_REQUIRE_CONFIRM = false;
    /** 办结后允许用户评价 */
    public static final boolean SLOT_ALLOW_RATING = false;
    /** 预约黑名单与申诉 */
    public static final boolean RESERVE_BLACKLIST_ENABLED = false;
    /** 号源满时可候补 */
    public static final boolean HOSPITAL_WAITLIST_ENABLED = false;
    /** 就诊人多档案 */
    public static final boolean PATIENT_PROFILE_ENABLED = false;
    /** 停车次卡 */
    public static final boolean PARKING_PASS_ENABLED = false;
    /** 会议结束后须上传纪要附件 */
    public static final boolean MEETING_MINUTES_REQUIRED = false;
    /** 客房预约须勾选入住须知 */
    public static final boolean HOTEL_NOTICE_REQUIRED = false;
    /** 仪器机时预约须勾选培训合格 */
    public static final boolean INSTRUMENT_TRAINING_REQUIRED = false;
}
