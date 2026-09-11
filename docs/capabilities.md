# 能力积木（cap 矩阵）

> **本文只负责**：接题可认的 cap id、挂载口径与壳/附加能力表；对齐 `capabilities.py`。
> **交接**：[HANDOFF.md](../HANDOFF.md) · **总览**：[README.md](../README.md) · **索引**：[README.md](./README.md)

---

对齐 `capabilities.py` / `BASELINE_RUNTIME_CAPS`。接题只认下表 **cap id**；`status=implemented` 均可进 `accept=full`。

**挂载口径（原有约定，不是新分类）**：

| 口径 | 含义 |
|------|------|
| **域默认** | 该域 bake 时直接带上（如 SHOP 带 `favorites`） |
| **开题写到才挂** | 材料里找到对应描述才写入 caps；**没有就保持原样**（如联想 / 足迹 / 多图 / 订单评价） |
| **壳附带** | 有订单壳或预约壳即有，不单独占 cap（售后、物流轨迹、改约、办结） |
| **扫词写配置** | 开题写到 → 写 yml/开关，仍无独立 cap（如超时关单分钟数） |
| **schema 开关** | 二级审批 / 互斥 / 签到 / 软删 / 周历等 → 见 [difficulty-tiers.md](./difficulty-tiers.md) L1，不另开 cap |

### 壳与主路径

| 能力 | 状态 | 含义 | 解锁的典型题 |
|------|------|------|----------------|
| `org_users` | ✅ | 角色用户、资料、重置密码、工作台 | 全部 |
| `content` | ✅ | 公告 / 资讯 | 全部 |
| `archive` | ✅ | 分类 + 业务对象 CRUD / 检索 / 详情 | 图书、设备、商品、菜品、片单… |
| `ticket_flow` | ✅ | 提交→审/受理→完结；我的与待办 | 借阅、报修、报名… |
| `quota` | ✅ | 库存 / 名额占用与归还 | 借阅、选课、设备… |
| `deadline` | ✅ | 到期、逾期、催办、可选费用 | 借阅、租赁… |
| `loan_renew` | ✅ | 借出中/逾期单据延长应还日；次数上限 | **开题写「续借」才挂**（E-01）；LIBRARY/EQUIP/INSTRUMENT；无域默认 |
| `waitlist` | ✅ | 名额满可候补；完结/回补后 FIFO 晋升待审 | **开题写「候补」才挂**（E-02）；ACTIVITY/COURSE/TOUR/LOST（须 ticket+quota）；无域默认 |
| `time_conflict` | ✅ | 起止时段相交 + 报名截止 | 选课、活动报名… |
| `slot_reserve` | ✅ | 资源时段占坑、取消与履约办结 | 挂号、车位、会议室、美发、客房 |
| `order_lines` | ✅ | 购物车 + 多明细订单（系统内余额/渠道密码；不对接商户 SDK） | 商城、点餐、客房 |
| `recommend` | ✅ | 猜你喜欢（分类偏好 + 热度 + 上新；非协同过滤） | 内容壳 / 档案浏览常见 |

### 交易附加（须已有 `order_lines`）

| 能力 | 状态 | 含义 | 挂载口径 |
|------|------|------|----------|
| `guestbook` | ✅ | 门户留言；总管删与简短回复（≠ 公告 ≠ 论坛） | 域默认 SHOP/FOOD/GENERIC·TRADE；否则开题写「留言」才挂 |
| `favorites` | ✅ | 收藏夹：收藏/取消，再加购 | 域默认 SHOP/FOOD；否则开题写「收藏」才挂 |
| `post_like` | ✅ | 档案/帖一人一赞开关与计数 | **开题写「点赞」才挂**（E-03）；FORUM/BLOG/MEDIA/MUSIC；无域默认 |
| `content_report` | ✅ | 用户举报→管理忽略/下架 | **开题写「举报」才挂**（E-03）；FORUM/DATING/BLOG；无域默认 |
| `audit_log` | ✅ | 管理端关键写/登录记入 sys_audit_log；总管可查 | **开题写「操作/审计/登录日志」才挂**（E-04）；无域默认；仅登录日志则 loginOnly |
| `message_template` | ✅ | 审单通过/驳回套模板发站内消息 | **开题写「消息/通知/站内信模板」才挂**（E-06）；无域默认；非短信邮件 |
| `coupon` | ✅ | 券模板领取 → 我的券 → 下单核销 → 过期扫标 | 开题写到才挂 |
| `flash_price` | ✅ | 档案活动价窗口；窗内下单快照活动价 | **开题写「限时购/活动价/秒杀」才挂**（E-05）；无域默认；非秒杀引擎 |
| `product_spec` | ✅ | 档案规格说明；详情展示；下单明细标题可带规格快照 | **开题写「规格/规格参数」才挂**（E-14）；SHOP/FOOD+订单壳；非色码矩阵 SKU |
| `wallet` | ✅ | 账户余额扣/退（不对接微信支付宝商户）；管理端可充值 | 开题写到才挂 |
| `points` | ✅ | 消费积分入账（不可充值） | 开题写到才挂 |
| `spend_discount` | ✅ | 满减算价（与券取更优） | 开题写到才挂 |
| `member_tier` | ✅ | 会员成长等级折扣 | 开题写到才挂 |
| `order_review` | ✅ | 完成单星级+文字；管理端回复 | 开题写到才挂（无域默认） |
| `rating_dims` | ✅ | 单据多维评分+评语+可选匿名（综合分=均值） | 域默认 DOM-EVAL（C-06） |
| `bed_occupy` | ✅ | 床位档案库存占用 + 选房/调宿申请 | 域默认 DOM-BED（C-08；复用 quota） |
| `checkin` | ✅ | 口令签到；结束未签可记爽约/缺勤 | 域默认 DOM-ACTIVITY、DOM-CHECKIN（C-10） |
| `mutual_select` | ✅ | 志愿提交后档案确认人接受/婉拒，管理可调剂 | 域默认 DOM-MUTUAL-*（C-05） |
| `pass_code` | ✅ | 审核通过签发通行码字符串（不对接闸机） | 域默认 DOM-VISITOR、DOM-CARPASS（C-09） |
| `code_qr` | ✅ | 通行码/取件码前端二维码出示与打印 | **开题写「二维码/扫码出示」才挂**（E-07）；无域默认；不对接闸机 |
| `staff_roster` | ✅ | 员工按日班次维护；预约看当班；派单标当日当班 | **开题写「排班/值班表」才挂**（E-09）；无域默认；非智能排课 |
| `room_equipment` | ✅ | 会议室档案配套设备清单；设备字典维护；详情/预约展示 | **开题写「设备清单/配套设备」才挂**（E-10）；无域默认；≠ 设备借用主路径 |
| `book_hold` | ✅ | 无库存可预约；还书后到书通知；限时确认借阅/顺延 | **开题写「图书预约/到书通知」才挂**（E-11）；LIBRARY；≠ 报名候补 |
| `book_suggest` | ✅ | 读者荐购→审通过/驳回台账 | **开题写「荐购」才挂**（E-13）；LIBRARY；≠PROCURE期刊遴选；不自动建档 |
| `post_mute` | ✅ | 设禁言截止；期内不可发帖/回复；举报可下架并禁言 | **开题写「禁言/禁止发帖」才挂**（E-12）；FORUM/BLOG；≠ enabled=0 停用 |
| `instrument_slot` | ✅ | 单域借+约（ticket+slot）；主路径约机时 | 域默认 DOM-INSTRUMENT（C-07） |
| `exam` | ✅ | 题库/组卷/作答/自动判分；刷题·解析·限时·次数·排行·错题本按需 | 域默认 DOM-EXAM（C-01）；`exam_skin` 换皮；LABSAFE 写「准入考试/先考试」→ 挂载 + 先考后申（C-02） |
| `survey` | ✅ | 问卷配置、在线填写、回收列表、选项计数统计 | 域默认 DOM-SURVEY（C-03）；≠ 评教 ≠ 考试 |
| `vote` | ✅ | 候选档案、一票/限票、结果公示 | 域默认 DOM-VOTE（C-04）；ACTIVITY 开题写报名+投票 → 并挂（C-11） |
| `doclib` | ✅ | 资料附件、权限、下载台账 | 域默认 DOM-DOCLIB（C-12）；≠ 借阅 ≠ 博客 |
| `timebank` | ✅ | 时长账户余额、流水加减、核销审核扣减 | 域默认 DOM-TIMEBANK（C-14）；≠ 劳动认定 ≠ 活动报名 |
| `seat_select` | ✅ | 场次座位图占座 + 订单 | 域默认 DOM-CINEMA（C-15）；毕设级占座，无高并发锁座；≠ 点播 ≠ 场地预约 |
| `multi_approve` | ✅ | 固定三级单据状态机：初审→复审→终审 | 开题写「三级审批/会签」才挂（C-16）；终审仍需总管；≠ 任意流程图 |
| `stock_io` | ✅ | 管理端入库/出库登记 + 库存流水 | 域默认 DOM-ASSET（C-17）；复用档案 stock；单仓演示；≠ 多仓 ERP ≠ RFID ≠ 采购申购 |
| `stock_scrap` | ✅ | 报废登记扣库存 + scrap 流水 | **开题写「报废」才挂**（E-08）；无域默认；须配 stock_io；≠ 多仓调拨 |
| `stock_count` | ✅ | 实盘录入调库存 + 差额流水 | **开题写「盘点」才挂**（E-08）；无域默认；须配 stock_io；≠ RFID |
| `e_sign` | ✅ | 上传签章图 + 勾选同意留痕 | 域默认 DOM-INTERN（C-18）；非 CA/法大大等第三方签平台 |
| `search_assist` | ✅ | 标题前缀联想 + 配置热搜 | 开题写到才挂（无域默认） |
| `browse_history` | ✅ | 最近浏览足迹（约 20 条） | 开题写到才挂（无域默认） |
| `archive_log` | ✅ | 挂档案的打卡/随访/评估记录；今日未打卡 | 域默认 DOM-EVENT；其它域开题写到才挂 |
| `gallery` | ✅ | 档案 `gallery_json` 多图（非 SKU） | 开题写到才挂（无域默认） |

依赖未实现能力 → `accept=reject`；上表均已落地。

**壳附带（无独立 cap）**：有 `order_lines` → 地址簿、售后、物流轨迹；有 `slot_reserve` → 办结 `complete`、改约 `reschedule`。  
**扫词写配置（无独立 cap）**：开题写「超时取消/支付超时」→ `thesis.order-timeout-minutes=30` + `@Scheduled`。

源码对照：`backend/app/bake/capabilities.py` 的 `CAPABILITIES` 键集 = 上表全部 id；增删能力须同步改本表与 `BASELINE_RUNTIME_CAPS`。

---
