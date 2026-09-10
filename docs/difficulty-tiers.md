# 开题难度分层（L0–L3）

> **本文只负责**：可写 / 可加价 / 仍不接的分层，以及开题怎么写建议。
> **交接**：[HANDOFF.md](../HANDOFF.md) · **总览**：[README.md](../README.md) · **索引**：[README.md](./README.md)

---

**原则**：开题写进「拟实现」的，答辩要能演示。基线不是纯 CRUD——标配含单据流 + **时间冲突等轻规则**；再往上是可加价亮点；硬件/真支付/深度模型仍不接。

交叉白名单与域表见 [`domains.md`](./domains.md)；能力 id 见 [`capabilities.md`](./capabilities.md)。

### L0 · 基线标配（换名词即可交付，含轻规则）

| 说法 | 运行时 |
|------|--------|
| 注册登录、验证码、资料头像 | baseline + org_users |
| 分类浏览 / 检索 / 详情 | archive |
| 申请→审核通过/驳回→完结 | ticket_flow |
| 库存或名额占用与归还/取消回补 | quota |
| 应还日期、逾期提醒、罚款登记 | deadline（借阅/设备等） |
| **自选应还日 + 申请数量** | `pickLoanPeriod` / `allowQty`：申请弹窗选到期日与数量；审批扣/还库存按 qty；LIBRARY/EQUIP 默认开，ASSET 仅数量 |
| **必填说明 / 起止日期** | `requireRemark` + `pickDateRange`：用途/跟进/认领说明；请假起止写入 `period_start/end`；PARKING 车牌、HOSPITAL 就诊人、MEETING 会议主题（`reservation.requireRemark`）；DORM/PROPERTY/IT 默认强制附件 |
| **时间冲突检测** | `time_conflict`：主数据 `start_at`/`end_at`；申请时与本人已占用时段做区间相交 |
| **报名/选课截止** | 主数据 `apply_deadline_at`；截止后不可再申请 |
| **我的日程/课表列表** | 我的单据展示 `startAt`/`endAt`（非拖拽排期） |
| **站内消息（审核结果）** | `sys_message` + 顶栏铃铛；审核通过/驳回写入申请人收件箱 |
| **访客留言** | `guestbook` + `sys_guestbook`；门户列表/发表，总管回复与删除（≠ 公告 ≠ 论坛） |
| **管理端 CSV 导出** | 记录/档案/订单/预约按当前筛选下载（**UTF-8 BOM + CRLF**，Excel 中文不乱码） |
| **工作台 ECharts** | 状态饼图 + 近 7 日趋势 + 分类库存柱图（基线内置，无大屏） |
| **档案 CSV 导入** | 模板下载 + 校验导入（分类按名匹配/自动新建） |
| **工作台简易统计** | `/api/admin/dashboard`：待审/处理中/已完成/用户数（档案域附加库存等） |
| 公告 | content |
| 总管主数据+用户+公告；子管审单 | 全厂不变式 |
| 猜你喜欢（偏好/热度/上新） | recommend，非协同过滤 |
| 富文本正文/回复；论坛用户发帖即时可见 + 多楼 @一层；回复仍审核 | 基线编辑器 + archive.userPublish + 多单据 |

选课 / 活动等带时段的域默认打开冲突检测；图书借阅等无时段列则自动跳过（不报错）。

### L1 · 可加价亮点（纯软件 · 再抬一点难度）

| 增强项 | 开题常见说法 | 难度感 | 控范围 |
|--------|--------------|--------|--------|
| **二级审批** | 初审→终审 | ★★ | 已落地：`pending→pending_final→approved`；终审需总管；DORM/PROPERTY/IT 默认开 |
| **互斥规则** | 两门课不能同选 | ★★ | 已落地：档案 `mutex_code`；同码进行中不可并存；COURSE 默认开 |
| **分类限额** | 每类最多选 N 门 | ★★ | 已落地：`ticket.categoryLimit`；COURSE 默认每类 1 门 |
| **评分评价** | 满意度 1～5 分 | ★★ | 已落地：`TicketRateDialog` + `POST /rate`；工作台均分；ACTIVITY/LOST 默认开 |
| **强制附件** | 认领须上传证明 | ★ | 已落地：`requireAttach` + 上传；LOST 默认开 |
| **周历视图** | 周视图看课表 | ★★ | 已落地：只读 `WeekCalendar`；COURSE/ACTIVITY 默认开 |
| **软件签到码** | 活动口令签到 | ★★ | 已落地：`checkin_code` + `POST /checkin`；ACTIVITY 默认开 |
| **标签组合筛选** | 多标签过滤 | ★ | 已落地：复用 FORUM `tag`/`post_tag`；AND 筛选 |
| **软删除** | 下架可恢复 | ★ | 已落地：`deleted_at`；LIBRARY/EQUIP/MEDIA/MUSIC/BLOG/FORUM/ASSET/**SHOP/FOOD** 默认开 |
| **ECharts 统计** | 工作台图表 | ★ | ✅ 已在 L0；勿扩成自定义报表 |
| **CSV 导入** | 批量录入主数据 | ★ | ✅ 已在 L0（仅档案；模板+校验） |
| **商品收藏** | 收藏夹 / wishlist | ★ | 已落地：`favorites` + `FavoriteStore` + `/favorites`；默认 SHOP/FOOD；开题扫「收藏」可挂其它 `order_lines` 域 |
| **优惠券** | 领取 / 我的券 / 核销 | ★★ | 已落地：`coupon`；`promo_coupon`+`user_coupon`；领券中心→Cart 选码→核销→定时过期；未领亦可填模板码；与满减取更优 |
| **订单评价** | 星级+文字 / 商家回复 | ★★ | 已落地：`order_review`；**材料命中才挂**；完成单可评；管理端回复 |
| **超时关单** | 待确认自动取消 | ★ | 已落地：**无独立 cap**；扫「超时取消」→ yml 30 分钟 + `DemoScheduleJobs` |
| **演示余额 / 积分 / 满减 / 会员** | 校园卡、积分、会员价 | ★★ | 已落地：`wallet`/`points`/`spend_discount`/`member_tier`；均开题扫描，须已有订单 |
| **售后/退款申请** | 申请退货退款 | ★★ | 已落地：**无独立 cap**；`refund_*` 列 + 用户申请 / 管理通过·驳回（回补库存+退演示余额） |
| **预约改约** | 改时段 | ★★ | 已落地：**无独立 cap**；`SlotStore.reschedule`（先释放原坑再占新坑；新坑失败则原约已取消） |
| **演示物流轨迹** | 快递跟踪 / 配送进度 | ★ | 已落地：**无独立 cap**；`OrderStore.logisticsTrace` + `OrderTraceDialog`（`el-timeline`，与审核进度同款）；发货后含运输中/派送中，自取为出餐→待取；收尾可为完成或售后 |
| **搜索联想 / 热搜** | 下拉联想、热搜榜 | ★ | 已落地：`search_assist`；**材料命中才挂**；标题前缀联想 + `schema.search.hotKeywords` |
| **浏览历史** | 足迹 / 最近浏览 | ★ | 已落地：`browse_history`；**材料命中才挂**；最近约 20 条 |
| **商品多图** | 详情图集 / 多图轮播 | ★ | 已落地：`gallery`；**材料命中才挂**；bake 向档案主表注入 `gallery_json`（运行时 ALTER 兜底）；最多 9 张；**非 SKU 多规格** |

**开题挂载 vs 壳附带**：收藏/券/忠诚度等靠开题词或交易域默认进 caps；联想/足迹/多图/订单评价按「开题写到才挂，没有保持原样」；超时关单靠开题词写 yml（无 cap）；售后/轨迹/改约随壳自带。

**报价建议**：L0 已含冲突检测与导出等，报价高于「纯 CRUD」；L1 每加 1～2 项作为亮点再上浮。

### 加价边界（真 SDK / 真通道 · 不进基线）

开题或客户点名下列能力时，**按加价项报价**，不写入本期演示承诺；基线只提供文案/占位或「非本期」说明：

| 加价项 | 基线替代（可演示） | 加价交付 |
|--------|-------------------|----------|
| 真短信 / 邮件通道 | 站内信 + 验证码（本地/演示） | 运营商/SMTP |
| 地图 SDK（选点/导航） | 地址簿纯文本 | 高德/腾讯等 |
| 实时客服 IM / WebSocket 推送 | 一对一私信（短轮询，`dm`） / 留言板 / 站内信 | 环信/融云/WebSocket 推送引擎 |
| 电子发票 / 税控 | 不接 | 开票服务对接 |
| 数据大屏 / 自定义报表 | 工作台 ECharts | 大屏工程 |
| 完整 SKU 多规格矩阵 | 单仓库存 + 规格说明字段（扫词） | 独立 SKU 库存引擎 |
| 高并发/跨活动候补引擎 | 开题扫词挂 `waitlist`（FIFO 晋升待审） | 独立候补产品/插队算法 |
| 真快递轨迹 API | 状态拼节点（含运输中/派送中） | 快递公司回调/查询 |

### L2 · 交易 / 占坑积木（已落地，D/E 组可接）

| 项 | 运行时 | 参考域 |
|----|--------|--------|
| 购物车 / 多明细行订单 | `order_lines`：`OrderStore` + `/api/cart` + `/api/orders`（无真支付） | SHOP / FOOD |
| 地址簿 / 履约字段 | `AddressStore` + 订单收货/配送/取餐码 | SHOP / FOOD |
| 售后 + 演示物流 | 订单 `refund_*`；`GET /api/orders/{id}/trace` + `OrderTraceDialog` | 凡 `order_lines` |
| 挂号分时、车位/会议室整点预约占坑 | `slot_reserve`：`SlotStore` 时段容量（≠ L0 本人已选时段相交） | MEETING / HOSPITAL / PARKING / SALON；HOTEL = 预约 + 订单 |
| 履约办结 / 改约 | `POST .../complete`；`POST .../reschedule` | 凡 `slot_reserve` |

### L3 · 仍不接（超毕设纯 Web 舒适区 / OOS）

人脸/指纹门禁、物联网传感器、真微信支付支付宝、小程序/安卓为交付物、协同过滤与深度学习训练、直播弹幕与转码 CDN、区块链、Hadoop/Spark、BPMN 可配置工作流、多仓批次 ERP、WebSocket/IM SDK 实时推送与无限楼中楼树、富文本多人协同编辑。

（毕设级一对一私信已落地为可选能力 `dm`：短轮询，非 WebSocket。）

**学历 / 真实生产（硬不接）**：硕士研究生、博士研究生课题；真实业务全流程 / 生产级全链路。本产品只做 **专科/本科毕设与课设** 演示级 Web 管理。

命中 `OUT_OF_SCOPE_SIGNALS` / `BUSINESS_OVERREACH_SIGNALS` → **`accept=reject`（Path B）**；改开题划入「非本期」或先扩能力，禁止当作本期演示承诺。  
业务过重（电子病历、处方、叫号大屏、BPMN、智能排课等）优先扫功能/拟实现段。  
多 ARCH 交叉另见 [`domains.md`](./domains.md) 组 H；`defense_ready=false` 的组合同样 reject。

### 开题怎么写（推荐）

1. **主要功能** = L0（含时间冲突等）+ 可选 1～2 个 L1 亮点；商城/点餐写购物车订单，预约类写时段占坑。  
2. 商城若写「收藏 / 优惠券 / 物流跟踪 / 售后」——前两项靠扫词进 caps，后两项订单壳自带，均可答辩演示。  
3. 预约若写「改约 / 到店完成 / 入场」——改约与办结随预约壳自带。  
4. **非本期** = L3 + 加价边界表（真支付、真短信、地图 SDK、真快递 API 等）。  
5. 换名词保留域关键词；冲突检测 vs 占坑一句分清：选课=本人已选相交；挂号=号源容量占坑。

---
