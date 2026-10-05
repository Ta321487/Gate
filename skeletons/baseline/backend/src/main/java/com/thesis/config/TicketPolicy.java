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
    /** 审核意见的最少字数（通过/驳回） */
    public static final int MIN_APPROVE_REMARK_WORDS = 0;
    /** 待审超过 N 小时自动通过；0 表示关闭 */
    public static final int APPROVE_AUTO_PASS_HOURS = 0;
    /** 被驳回后可修改重提的次数 */
    public static final int MAX_REVISE_TIMES = 0;
    /** 本学期退选次数上限；0 表示不限制 */
    public static final int MAX_DROP_TIMES = 0;
    /** 学期已选学分上限；0 表示不限制 */
    public static final int SEMESTER_CREDIT_CAP = 0;
    /** 剩余学分低于该值时提示接近上限；0 表示不提示 */
    public static final int CREDIT_WARN_REMAINING = 0;
    /** 采购比价最少供应商家数；0 不校验 */
    public static final int MIN_VENDOR_QUOTES = 0;
    /** 合同/许可/年检到期前 N 天站内信提醒；0 关闭 */
    public static final int NOTIFY_ARCHIVE_EXPIRE_DAYS = 0;
    /** 通行码自审过之日起有效天数；0 关闭 */
    public static final int PASS_EXPIRE_DAYS = 0;
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
    /** 一人一档重复提交拒绝文案 */
    public static final String ONE_PER_ARCHIVE_DENY_MESSAGE = "";
    /** 黑名单拒绝文案 */
    public static final String APPLY_BLACKLIST_DENY_MESSAGE = "";
    /** 评教开放窗口外拒绝文案 */
    public static final String EVAL_OPEN_WINDOW_DENY_MESSAGE = "";

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
    /** 选课志愿序（第一/第二） */
    public static final boolean ALLOW_WISH_ORDER = false;
    /** 活动志愿者岗位意向 */
    public static final boolean ALLOW_VOLUNTEER_ROLE = false;
    /** 管理端可为报名补签 */
    public static final boolean ALLOW_ADMIN_CHECKIN = false;
    /** 出团天气须知须勾选 */
    public static final boolean REQUIRE_TOUR_NOTICE_ACK = false;
    /** 集体报名可填同行人姓名 */
    public static final boolean ALLOW_COMPANIONS = false;
    /** 名额紧张时随机抽签录取 */
    public static final boolean ALLOW_LOTTERY = false;
    /** 活动座位分区报名 */
    public static final boolean ALLOW_SEAT_ZONE = false;
    /** 已通过报名可站内转让 */
    public static final boolean ALLOW_TICKET_TRANSFER = false;
    /** 电子票夹出示通行码 */
    public static final boolean ALLOW_TICKET_WALLET = false;
    /** 黑名单用户禁止报名 */
    public static final boolean ALLOW_APPLY_BLACKLIST = false;
    /** 调课变更站内信通知已选学生 */
    public static final boolean SCHEDULE_CHANGE_NOTIFY = false;
    /** 活动办结后用户可上传相册 */
    public static final boolean ALLOW_POST_GALLERY = false;
    /** 活动学分认定非自动回写须勾选确认 */
    public static final boolean REQUIRE_CREDIT_WRITEBACK_ACK = false;
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
    /** 审批/填报组加厚（意见短语/抄送/审意见字数等） */
    public static final boolean APPROVE_THICKEN = false;
    /** 审核时可抄送知会（站内信） */
    public static final boolean ALLOW_APPROVE_CC = false;
    /** 审批转审（一跳改处理人） */
    public static final boolean ALLOW_APPROVE_TRANSFER = false;
    /** 请假期间代审 */
    public static final boolean ALLOW_APPROVE_DELEGATE = false;
    /** 审核时可上传意见附件 */
    public static final boolean ALLOW_APPROVE_REMARK_ATTACH = false;
    /** 抄送人可追加知会评论 */
    public static final boolean ALLOW_APPROVE_CC_COMMENT = false;
    /** 限时自动通过（危险开关） */
    public static final boolean ALLOW_APPROVE_AUTO_PASS = false;
    /** 证明领取方式（自取/邮寄） */
    public static final boolean ALLOW_CERT_PICKUP = false;
    /** 证明加急件标记 */
    public static final boolean ALLOW_CERT_URGENT = false;
    /** 用印份数与装订说明 */
    public static final boolean ALLOW_SEAL_COPIES = false;
    /** 用车里程与油耗回填 */
    public static final boolean ALLOW_FLEET_MILEAGE = false;
    /** 报销发票张数与金额校验 */
    public static final boolean ALLOW_EXPENSE_INVOICE = false;
    /** 访客随行人数 */
    public static final boolean ALLOW_VISITOR_COUNT = false;
    /** 获奖证书编号查重 */
    public static final boolean ALLOW_AWARD_CERT_NO = false;
    /** 采购比价供应商列表 */
    public static final boolean ALLOW_VENDOR_QUOTES = false;
    /** 同一档案仅一张进行中单据（评教一人一课） */
    public static final boolean FORCE_ONE_PER_ARCHIVE = false;
    /** 评教开放窗口起止日校验 */
    public static final boolean ALLOW_EVAL_OPEN_WINDOW = false;
    /** 加班调休核定小时（办结必填） */
    public static final boolean ALLOW_COMP_HOURS = false;
    /** 用车驾驶员与随车人 */
    public static final boolean ALLOW_FLEET_CREW = false;
    /** 伦理批件编号与有效期（档案） */
    public static final boolean ALLOW_ETHIC_BATCH = false;
    /** 通行码到期自动失效 */
    public static final boolean ALLOW_PASS_EXPIRE = false;
    /** 用车回场油量（办结必填） */
    public static final boolean ALLOW_RETURN_FUEL = false;
    /** 劳动地点（申请必填） */
    public static final boolean ALLOW_LABOR_PLACE = false;
    /** 宣传品尺寸与悬挂位置（档案） */
    public static final boolean ALLOW_PROMO_PLACE = false;
    /** 伦理会议日期与决议摘要（档案） */
    public static final boolean ALLOW_ETHIC_MEETING = false;
    /** 学籍异动生效日期 */
    public static final boolean ALLOW_EFFECTIVE_ON = false;
    /** 证明开具流水号（审过签发） */
    public static final boolean ALLOW_CERT_ISSUE_NO = false;
    /** 宣传品投放反馈照片（办结必附） */
    public static final boolean ALLOW_PROMO_FEEDBACK = false;
    /** 合同正文版本号（申请必填） */
    public static final boolean ALLOW_DOC_REV = false;
    /** 装修施工时段对照禁噪窗 */
    public static final boolean ALLOW_FITOUT_QUIET = false;
    /** 用印现场照片（办结必附） */
    public static final boolean ALLOW_SEAL_CLOSE_PHOTO = false;
    /** 证明开具份数上限 */
    public static final boolean ALLOW_ISSUE_COPIES = false;
    /** 合同签署方多方勾选 */
    public static final boolean ALLOW_SIGN_PARTIES = false;
    /** 准入培训学时累计 */
    public static final boolean ALLOW_TRAIN_HOURS = false;
    /** 车辆通行证年检到期提醒 */
    public static final boolean ALLOW_INSPECT_EXPIRE = false;
    /** 大创项目成员变更说明 */
    public static final boolean ALLOW_MEMBER_CHANGE = false;
    /** 采购申购金额对照预算余额 */
    public static final boolean ALLOW_PROCURE_BUDGET = false;
    /** 查寝异常类型 */
    public static final boolean ALLOW_CHECKIN_EXCEPTION = false;
    /** 访客来访目的 */
    public static final boolean ALLOW_VISIT_PURPOSE = false;
    /** 用车违章责任人（办结必填） */
    public static final boolean ALLOW_FLEET_VIOLATION = false;
    /** 装修验收整改说明 */
    public static final boolean ALLOW_FITOUT_RECTIFY = false;
    /** 大创中期/结题材料节点提醒 */
    public static final boolean ALLOW_PROJ_NODE_REMIND = false;
    /** 社团年审材料复制上年 */
    public static final boolean ALLOW_CLUB_COPY_LAST = false;
    /** 采购验收不合格退货说明 */
    public static final boolean ALLOW_PROCURE_RETURN = false;
    /** 综测公示期异议登记 */
    public static final boolean ALLOW_MORAL_OBJECTION = false;
    /** 大创经费使用登记 */
    public static final boolean ALLOW_PROJ_FUND_USE = false;
    /** 评教课程维度权重 */
    public static final boolean ALLOW_EVAL_DIM_WEIGHT = false;
    /** 访客预约时段余量 */
    public static final boolean ALLOW_VISIT_SLOT_REMAIN = false;
    /** 大创结题查重报告外链 */
    public static final boolean ALLOW_PLAGIARISM_URL = false;
    /** 查寝连续未归预警 */
    public static final boolean ALLOW_ABSENT_STREAK = false;
    /** 党员发展阶段登记 */
    public static final boolean ALLOW_PARTY_STAGE = false;
    /** 评教督导听课记录 */
    public static final boolean ALLOW_EVAL_OBSERVE = false;
    /** 学籍异动对课表影响说明 */
    public static final boolean ALLOW_SCHEDULE_IMPACT = false;
    /** 合同金额及大写展示 */
    public static final boolean ALLOW_CONTRACT_AMOUNT = false;
    /** 报销单明细多行 */
    public static final boolean ALLOW_EXPENSE_LINES = false;
    /** 出差行程多段 */
    public static final boolean ALLOW_TRIP_LEGS = false;
    /** 评教结果对学生不可见 */
    public static final boolean ALLOW_HIDE_EVAL_RESULT = false;
    /** 合同审批意见对签署方可见 */
    public static final boolean ALLOW_SIGN_REMARK_VISIBLE = false;
    /** 大创项目变更日志 */
    public static final boolean ALLOW_PROJ_CHANGE_LOG = false;
    /** 证明真伪查询码 */
    public static final boolean ALLOW_CERT_VERIFY = false;
    /** 访客现场补录 */
    public static final boolean ALLOW_VISIT_WALK_IN = false;
    /** 查寝楼栋长代登记 */
    public static final boolean ALLOW_CHECKIN_PROXY = false;
    /** 社团成员名册 */
    public static final boolean ALLOW_CLUB_ROSTER = false;
    /** 车辆通行证车位同日互斥 */
    public static final boolean ALLOW_CARPASS_PARKING_MUTEX = false;
    /** 评教未评催评 */
    public static final boolean ALLOW_EVAL_URGE = false;
    /** 合同续签日期与说明 */
    public static final boolean ALLOW_CONTRACT_RENEW = false;
    /** 合同到期续签提醒 */
    public static final boolean ALLOW_CONTRACT_EXPIRE_REMIND = false;
    /** 证明领取核销码 */
    public static final boolean ALLOW_CERT_PICKUP_REDEEM = false;
    /** 实验室准入考试成绩门槛 */
    public static final boolean ALLOW_EXAM_PASS_MIN = false;
    /** 查寝抽查任务 */
    public static final boolean ALLOW_CHECKIN_SPOT = false;
    /** 评教先评后查分 */
    public static final boolean ALLOW_EVAL_BEFORE_GRADE = false;
    /** 审批人均办理耗时 */
    public static final boolean ALLOW_APPROVE_DURATION_STATS = false;
    /** 申请附件覆盖留旧 */
    public static final boolean ALLOW_ATTACH_KEEP_OLD = false;
    /** 证明领取核销码二维码 */
    public static final boolean ALLOW_CERT_PICKUP_QR = false;
    /** 证明真伪查询页加深 */
    public static final boolean ALLOW_CERT_VERIFY_PAGE = false;
    /** 访客通行证打印 */
    public static final boolean ALLOW_VISITOR_PASS_PRINT = false;
    /** 查寝楼长日报 */
    public static final boolean ALLOW_CHECKIN_DAILY_REPORT = false;
    /** 评教院系汇总导出 */
    public static final boolean ALLOW_EVAL_COLLEGE_EXPORT = false;
    /** 用印台账导出 */
    public static final boolean ALLOW_SEAL_LEDGER_EXPORT = false;
    /** 综测加减分证据材料清单 */
    public static final boolean ALLOW_MORAL_MATERIAL_CHECK = false;
    /** 党员发展阶段材料清单模板 */
    public static final boolean ALLOW_PARTY_MATERIAL_TEMPLATE = false;
    /** 思想汇报/心得附件节点 */
    public static final boolean ALLOW_PARTY_THOUGHT_ATTACH = false;
    /** 证明开具套打页 */
    public static final boolean ALLOW_CERT_FORM_PRINT = false;
    /** 用印审批单套打 */
    public static final boolean ALLOW_SEAL_FORM_PRINT = false;
    /** 大创中期检查表套打 */
    public static final boolean ALLOW_PROJ_MID_FORM_PRINT = false;
    /** 伦理审查意见书套打 */
    public static final boolean ALLOW_ETHIC_OPINION_PRINT = false;
    /** 报销票据影像张数提示 */
    public static final boolean ALLOW_EXPENSE_ATTACH_COUNT = false;
    /** 用车驾驶员资质材料清单 */
    public static final boolean ALLOW_FLEET_DRIVER_CERT = false;
    public static final boolean NOTIFY_ON_APPLY_SUCCESS = false;
    public static final boolean ALLOW_MEETING_PLACE = false;
    public static final boolean ALLOW_EMERGENCY_CONTACT = false;
}
