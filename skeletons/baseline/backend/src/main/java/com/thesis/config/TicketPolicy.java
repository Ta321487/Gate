package com.thesis.config;

/**
 * 单据（申请 / 审核 / 跟进）业务规则与功能开关。
 * <p>按本系统开题口径生成，集中保存单据流程用到的天数、上限、文案与开关；
 * 需要调整业务口径时改这里的常量即可。</p>
 */
public final class TicketPolicy {

    private TicketPolicy() {}

    // ---------- 单据主流程 ----------
    /** 是否启用单据主流程 */
    public static final boolean ENABLED = true;
    /** 单据模式：archive（关联档案、占库存）/ standalone（自由填写） */
    public static final String MODE = "archive";
    /** 单据主表名 */
    public static final String TABLE = "borrow";
    /** 是否按截止日管理（应还 / 处理时限） */
    public static final boolean USE_DEADLINE = true;
    /** 是否允许同一人同时开多张单 */
    public static final boolean ALLOW_MULTI = false;
    /** 申请时检测本人已占用时段是否冲突 */
    public static final boolean CHECK_TIME_CONFLICT = false;

    // ---------- 借阅 / 罚金 / 爽约 ----------
    /** 默认借期 / 处理时限天数；0 表示不按天 */
    public static final int LOAN_DAYS = 0;
    /** 每人同时在手的单据上限；0 表示不限 */
    public static final int MAX_ACTIVE = 0;
    /** 逾期每天罚金（元）；-1 沿用代码默认，0 表示不收罚金 */
    public static final double FINE_PER_DAY = -1;
    /** 取件 / 送达地点文案 */
    public static final String PICKUP_PLACE = "";
    /** 活动结束仍未签到记爽约 */
    public static final boolean NO_SHOW_AFTER_END = false;
    /** 爽约固定费用（元）；0 只改状态 */
    public static final double NO_SHOW_PENALTY_YUAN = 0;
    /** 预约到货后保留的小时数 */
    public static final int HOLD_HOURS = 48;
    /** 允许取消占用的次数上限；0 表示不限 */
    public static final int MAX_CANCEL_HOLDS = 0;

    // ---------- 跟进与时限（SLA） ----------
    /** 跟进提醒间隔天数 */
    public static final int FOLLOW_REMIND_DAYS = 0;
    /** 超过 N 天无跟进视为停滞 */
    public static final int STALE_FOLLOW_DAYS = 0;
    /** 高优先级单据的处理时限（天） */
    public static final int LEVEL_SLA_HIGH_DAYS = 0;
    /** 中优先级单据的处理时限（天） */
    public static final int LEVEL_SLA_MID_DAYS = 0;
    /** 低优先级单据的处理时限（天） */
    public static final int LEVEL_SLA_LOW_DAYS = 0;
    /** 到期前 N 天提醒 */
    public static final int DUE_SOON_DAYS = 0;
    /** 历史逾期达 N 次限制再借 */
    public static final int MAX_OVERDUE_TIMES = 0;
    /** 结果公示后的异议登记窗口天数 */
    public static final int OBJECTION_DAYS = 0;
    /** 每周汇报的提交截止日（周内第几天） */
    public static final int WEEK_REPORT_DEADLINE_DAY = 0;
    /** 用户催办的冷却分钟数 */
    public static final int URGE_COOLDOWN_MINUTES = 0;
    /** 活动开始前可取消报名的最少提前小时数；0 表示不限制 */
    public static final int CANCEL_BEFORE_HOURS = 0;
    /** 失物启事发布后可认领的冷却小时数；0 表示不限制 */
    public static final int CLAIM_COOLDOWN_HOURS = 0;

    // ---------- 续借 / 修改 / 信用 ----------
    /** 单次借出最多续借次数 */
    public static final int MAX_RENEW = 1;
    /** 每次续借延长的天数；0 表示跟默认天数 */
    public static final int RENEW_DAYS = 0;
    /** 同一分类下进行中单据上限；0 表示不限 */
    public static final int CATEGORY_LIMIT = 0;
    /** 申请说明的最少字数 */
    public static final int MIN_REMARK_WORDS = 0;
    /** 被驳回后可修改重提的次数 */
    public static final int MAX_REVISE_TIMES = 0;
    /** 本学期退选次数上限；0 表示不限制 */
    public static final int MAX_DROP_TIMES = 0;
    /** 学期已选学分上限；0 表示不限制 */
    public static final int SEMESTER_CREDIT_CAP = 0;
    /** 剩余学分低于该值时提示接近上限；0 表示不提示 */
    public static final int CREDIT_WARN_REMAINING = 0;
    /** 初始信用分 */
    public static final int CREDIT_INITIAL = 100;
    /** 每次逾期扣减的信用分 */
    public static final int CREDIT_OVERDUE_DELTA = 5;
    /** 信用分低于该值限制再借 */
    public static final int CREDIT_BLOCK_BELOW = 60;

    // ---------- 匹配与床位口径文案 ----------
    /** 匹配用的楼栋字段键 */
    public static final String MATCH_PROFILE_BUILDING_KEY = "";
    /** 匹配用的房间字段键 */
    public static final String MATCH_PROFILE_ROOM_KEY = "";
    /** 用户资料里的楼栋字段名 */
    public static final String MATCH_PROFILE_BUILDING_FIELD = "";
    /** 用户资料里的房间字段名 */
    public static final String MATCH_PROFILE_ROOM_FIELD = "";
    /** 资料不全时的提示文案 */
    public static final String MATCH_PROFILE_NEED_MESSAGE = "";
    /** 匹配不通过的提示文案 */
    public static final String MATCH_PROFILE_DENY_MESSAGE = "";
    /** 床位约束提示文案 */
    public static final String BED_CONSTRAINT_NEED_MESSAGE = "";
    /** 床位冲突拒绝文案 */
    public static final String BED_CONSTRAINT_DENY_MESSAGE = "";
    /** 年龄限制缺资料提示 */
    public static final String AGE_CONSTRAINT_NEED_MESSAGE = "";
    /** 年龄不符合拒绝文案 */
    public static final String AGE_CONSTRAINT_DENY_MESSAGE = "";

    // ---------- 扩展能力开关（按开题启用） ----------
    public static final boolean TWO_LEVEL = false;
    public static final boolean THREE_LEVEL = false;
    public static final boolean REQUIRE_ATTACH = false;
    public static final boolean ALLOW_RATING = false;
    public static final boolean ALLOW_RATING_TAGS = false;
    public static final boolean CHECK_MUTEX = false;
    public static final boolean WEEK_CALENDAR = false;
    public static final boolean ALLOW_CHECKIN = false;
    public static final boolean PEER_ACCEPT = false;
    public static final boolean ISSUE_PASS_CODE = false;
    public static final boolean ALLOW_RENEW = false;
    public static final boolean ALLOW_WAITLIST = false;
    public static final boolean ALLOW_BOOK_HOLD = false;
    public static final boolean ALLOW_BOOK_LOST = false;
    public static final boolean REQUIRE_RETURN_ATTACH = false;
    public static final boolean PICK_LOAN_PERIOD = false;
    public static final boolean ALLOW_QTY = false;
    public static final boolean REQUIRE_REMARK = false;
    public static final boolean PICK_DATE_RANGE = false;
    public static final boolean APPROVE_ENDS_FLOW = false;
    public static final boolean AUTO_APPROVE = false;
    public static final boolean REQUIRE_CLAIM_CODE = false;
    /** 按楼栋 / 房间匹配（同楼栋才能接单） */
    public static final boolean MATCH_PROFILE_ROOM = false;
    /** 只按楼栋匹配、不校验房间 */
    public static final boolean MATCH_PROFILE_LOOSE_BUILDING = false;
    public static final boolean APPLICANT_COMPLETE_ONLY = false;
    public static final boolean ALLOW_PROXY_PICKUP = false;
    /** 床位占用约束（一人一床） */
    public static final boolean BED_CONSTRAINT = false;
    public static final boolean ARRIVAL_NOTIFY = false;
    public static final boolean REQUIRE_NOTICE_ACK = false;
    public static final boolean ALLOW_DEPOSIT = false;
    public static final boolean ALLOW_EXCEPTION_CLOSE = false;
    public static final boolean REQUIRE_TRAINING_ACK = false;
    public static final boolean REQUIRE_INSURANCE_ACK = false;
    public static final boolean REQUIRE_MEETING_ACK = false;
    public static final boolean REQUIRE_APPLY_INVITE = false;
    public static final boolean REQUIRE_PRICE_NOTE_ACK = false;
    public static final boolean REQUIRE_SPONSOR_ACK = false;
    public static final boolean REQUIRE_PLAN_ACK = false;
    /** 有先修提示码时须勾选确认 */
    public static final boolean REQUIRE_PREREQ_ACK = false;
    /** 线路年龄上下限对照资料 */
    public static final boolean AGE_CONSTRAINT = false;
    /** 签到可登记迟到分钟数 */
    public static final boolean ALLOW_LATE_MINUTES = false;
    public static final boolean BLOCK_IF_CALIB_EXPIRED = false;
    public static final boolean ALLOW_PROJECT_NO = false;
    public static final boolean ALLOW_PROCURE_REF = false;
    public static final boolean PROCURE_TO_STOCK_IN = false;
    public static final boolean ALLOW_DUAL_REVIEW = false;
    public static final boolean ALLOW_SHIP_FEE = false;
    public static final boolean ALLOW_UTILITY_NOTE = false;
    public static final boolean OVERDUE_AUTO_COMPENSATE = false;
    public static final boolean ALLOW_FINE_WAIVE = false;
    public static final boolean RENEW_BLOCK_IF_HELD = false;
    public static final boolean REQUIRE_PEER_CONFIRM = false;
    public static final boolean REQUIRE_ABANDON_DUAL = false;
    public static final boolean PHONE_DUP_CHECK = false;
    /** 按优先级套用不同处理时限 */
    public static final boolean LEVEL_AFFECTS_DEADLINE = false;
    public static final boolean NOTIFY_DUTY_ON_REPORT = false;
    public static final boolean ALLOW_OBJECTION_WINDOW = false;
    public static final boolean ALLOW_DEAL_AMOUNT = false;
    public static final boolean ALLOW_NEXT_ACTION = false;
    public static final boolean REQUIRE_CLOSE_ATTACH = false;
    public static final boolean REQUIRE_RETURN_DATE = false;
    public static final boolean ATTACH_BY_LEAVE_TYPE = false;
    public static final boolean ALLOW_LEAVE_PROXY = false;
    public static final boolean ALLOW_INTERVIEW_RESULT = false;
    public static final boolean ALLOW_BATCH_HIRE = false;
    public static final boolean ALLOW_WRITTEN_SCORE = false;
    public static final boolean ALLOW_BG_CHECK_NOTE = false;
    public static final boolean ALLOW_DEFENSE_RESULT = false;
    public static final boolean MASK_BANK_ACCOUNT = false;
    public static final boolean ALLOW_DISBURSE_BATCH = false;
    public static final boolean WEEK_REPORT_REMIND = false;
    public static final boolean REQUIRE_APPRAISAL = false;
    public static final boolean ALLOW_COMPANY_EVAL = false;
    public static final boolean ALLOW_EXCELLENT_MARK = false;
    public static final boolean REQUIRE_FEEDBACK_SET = false;
    public static final boolean ALLOW_RECORD_URL = false;
    public static final boolean ALLOW_MAKEUP_APPLY = false;
    public static final boolean HOME_VISIT_TEMPLATE = false;
    public static final boolean ALLOW_CONFIDENTIAL = false;
    public static final boolean ALLOW_ASSIGN_DEPT = false;
    public static final boolean CREDIT_ON_OVERDUE = false;
    public static final boolean ALLOW_USER_URGE = false;
    public static final boolean LOCK_URGE_AFTER_RATE = false;
    public static final boolean ALLOW_CANCEL_URGE = false;
    public static final boolean REQUIRE_FAULT_REASON = false;
    public static final boolean REQUIRE_CLOSE_SUMMARY = false;
    public static final boolean REQUIRE_LOW_RATING_REMARK = false;
    public static final boolean SLA_SPLIT = false;
    public static final boolean ESCALATE_ON_OVERDUE = false;
    public static final boolean NOTIFY_SUPERVISOR_ON_OVERDUE = false;
    public static final boolean ALLOW_HOLD_RESUME = false;
    public static final boolean ALLOW_CANCEL_DISPATCHED = false;
    public static final boolean ALLOW_TICKET_DRAFT = false;
    public static final boolean ALLOW_FOLLOW_RATE = false;
    public static final boolean PREFERRED_SLOT = false;
    public static final boolean PROGRESS_SUBSCRIBE = false;
    public static final boolean NIGHT_URGENT = false;
    public static final boolean ALLOW_PARTS_NOTE = false;
    public static final boolean ALLOW_QUOTE = false;
    public static final boolean ALLOW_PUBLIC_AREA = false;
    public static final boolean DUP_ROOM_CHECK = false;
    public static final boolean ALLOW_ASSET_CODE = false;
    public static final boolean ALLOW_REMOTE_URL = false;
    public static final boolean ALLOW_SERIAL_NO = false;
    public static final boolean ALLOW_HELPER = false;
    public static final boolean TODAY_BOARD = false;
    public static final boolean PRINT_TICKET = false;
    public static final boolean REPAIR_THICKEN = false;
    public static final boolean APPLY_THICKEN = false;
    public static final boolean NOTIFY_ON_APPLY_SUCCESS = false;
    public static final boolean ALLOW_MEETING_PLACE = false;
    public static final boolean ALLOW_EMERGENCY_CONTACT = false;
}
