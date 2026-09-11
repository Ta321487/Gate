# 沉浸感边角（毕设非强制清单）

> 口径：**加分项 / 演示沉浸**，不是门禁红灯，也不进老板小卡强制项。  
> 组织轴：**能力岛 × 共用 UI 表面**（`skeletons/baseline/frontend/src/`），**禁止**按 68 个 `DOM-*` 复制皮肤。  
> 对照：`backend/app/bake/capabilities.py`（55 个 `implemented`）、`docs/opening-feature-delivery-map.md`、`docs/difficulty-tiers.md`、`docs/ai-opening-delivery-map.md`。  
> 原则：能挂在跨域同一表面就改一处；禁止用边角冒充 WebSocket IM、真支付、真地图、人脸、闸机等超出范围能力。

---

## 口径

| 项 | 说明 |
|----|------|
| 是什么 | 头像、角标、空态、表情条、倒计时、进度色点、图集、星级气泡等**观感/演示**增强 |
| 不是什么 | 业务主路径、门禁断言、新 `DOM-*`、新能力开关冒充 |
| 常驻 vs 扫词 | 头像/空态/状态色点可常驻；表情条、限时倒计时、二维码等优先挂**已有能力**（开题写到才挂的 E/C 项） |
| 路径写法 | 下文路径相对 `skeletons/baseline/frontend/src/` |

**能力全集（55，来自 `capabilities.py`）**  
`archive` · `ticket_flow` · `quota` · `deadline` · `loan_renew` · `waitlist` · `post_like` · `content_report` · `slot_reserve` · `order_lines` · `wallet` · `points` · `spend_discount` · `member_tier` · `content` · `message_template` · `audit_log` · `guestbook` · `ai_assistant` · `dm` · `favorites` · `coupon` · `flash_price` · `product_spec` · `order_review` · `checkin` · `mutual_select` · `pass_code` · `code_qr` · `staff_roster` · `room_equipment` · `book_hold` · `book_suggest` · `post_mute` · `bed_occupy` · `instrument_slot` · `exam` · `survey` · `vote` · `doclib` · `timebank` · `seat_select` · `multi_approve` · `stock_io` · `stock_scrap` · `stock_count` · `e_sign` · `rating_dims` · `search_assist` · `browse_history` · `archive_log` · `gallery` · `org_users` · `recommend` · `time_conflict`

---

## 共用壳（auth / profile / layout / bell）

| 表面 | 主路径 | 已做（证据） | 建议下一档 | 明确不做 |
|------|--------|--------------|------------|----------|
| 登录/注册壳 | `views/Login.vue` · `views/Register.vue` · `components/AuthShell.vue` | 多模板 auth；`authHero`；无图时域色渐变（`data-hero=0`）；**验证码刷新动效**（Login/Register） | — | 第三方 OAuth、短信网关 |
| 个人资料 | `views/Profile.vue` | `el-avatar`；完善度进度条；loyalty；**会员等级色条**；**积分流水迷你列表**；充值（仅买家） | — | 社交主页 Feed |
| 门户顶栏 | `layouts/PortalLayout.vue` | 头像+昵称；`MessageBell`；轮播圆点；**`CartBadge`** | — | 原生推送铃 |
| 工作台壳 | `layouts/AdminLayout.vue` | 消息铃；**待办 badge**；**缺卡 badge**（`archive_logs`） | — | 可配置仪表盘引擎 |
| 站内信铃 | `components/MessageBell.vue` | 未读 badge；类型小标；相对时间 | — | 推送中台 |
| 消息中心 | `views/user/Messages.vue` | 类型小标；相对时间；EmptyHint | — | 已读回执 IM |
| 门户首页 | `views/user/PortalHome.vue` | mall/editorial；**空货架 EmptyHint CTA** | — | 运营弹窗轰炸 |
| 轮播 | `components/PortalCarousel.vue` | 自动轮播 + dots | — | 视频直播轮播 |
| 缺页/加载 | `PageSkeleton` · `EntityDetailLayout` · `NoticeDetail` | 详情骨架；**列表 `variant=list`**（消息/公告/订单） | — | SPA 假进度条 |
| 游客提示 | `GuestLoginHint.vue` | 未登录引导 | — | 强制注册墙 |

---

## 按能力岛表

### A. 档案 / 浏览 / 内容周边

| 能力 | 主表面 | 已做 | 建议下一档 | 不做 |
|------|--------|------|------------|------|
| `archive` | `ArchiveBrowse` 等 | 封面/字母占位；EmptyHint；库存 tag；**hover 轻抬**；紧张库存橙字 | — | 真以图搜图 |
| `gallery` | 详情轮播 | carousel；**灯箱 preview** | — | 图床 CDN |
| `search_assist` | ArchiveBrowse | 联想；热搜 chips；**前 3「火」标** | — | 语义检索 |
| `recommend` | `RecommendStrip` | 空推荐藏整条 | — | 协同过滤 |
| `favorites` | Browse / MyFavorites | EmptyHint CTA；**收藏按钮 like-pulse** | — | 心愿单社交 |
| `browse_history` | BrowseHistory | 清除确认；相对时间；EmptyHint | — | 跨设备云足迹 |
| `post_like` | ArchiveBrowse | 计数；**StatusChip 色点**；pulse | — | 刷赞排行 |
| `content_report` | Browse | 举报；**已举报灰态** | — | 舆情 NLP |
| `post_mute` | 发帖失败 | 后端「禁言至…」经 http 全局 toast | — | 禁言大厅 |
| `content` | Notices | 空态；骨架；**置顶列 pinned**（运行时补列 + 管理开关）；48h「新」 | — | 资讯推荐算法 |
| `room_equipment` | Browse | 设备名 tag；**关键词图标字典**（`equipmentMark`） | — | ≠借用主路径 |
| `product_spec` | Browse | 规格行；**详情 Tab** | — | SKU 矩阵 |
| `flash_price` | Browse | badge；**窗内倒计时** | — | 真秒杀锁 |
| `quota` | Browse | 余量；**紧张橙提示** | — | 多仓 WMS |
| `time_conflict` | 申请校验 | 冲突拒单提示 | 冲突高亮一句（可选） | 拖拽排课 |
| `waitlist` | Browse / MyTickets | warning tag；**候补第 N 位** | — | 复杂队列 UI |
| `book_hold` | MyTickets | 保留流；**保留倒计时** | — | ≠候补混皮 |
| `bed_occupy` / `instrument_slot` | 复用 archive+ticket±slot | **时段色块复用** | — | DOM 分叉 |

### B. 单据流 / 催办 / 签到 / 互选 / 通行

| 能力 | 主表面 | 已做 | 建议下一档 | 不做 |
|------|--------|------|------------|------|
| `ticket_flow` | MyTickets 等 | StatusChip；tag；进度弹窗 | — | BPMN |
| `multi_approve` | MyTickets | **ImmSteps 初/复/终** | — | 工作流引擎 |
| `deadline` | MyTickets | **逾期左边条** | — | 短信网关 |
| `loan_renew` | MyTickets | 续借；**toast 含新应还日** | — | 无限续借引擎 |
| `checkin` | MyTickets | 口令；**成功 ✓** | — | 人脸 |
| `mutual_select` | PeerTickets | 空态；**确认绿 / 婉拒红** | — | 协同过滤配对 |
| `pass_code` | MyTickets | 加粗；**一键复制** | — | 闸机 |
| `code_qr` | CodeQrBlock | 弹窗打印；**订单取餐码复用** | — | 扫码枪 SDK |
| `rating_dims` | TicketRateDialog | 多维 rate | 列表均分色点（可选） | 量表统计包 |
| （单据进度） | TicketProgressDialog | 时间线；**节点字标** | — | 实时地图派单 |

### C. 预约 / 排班 / 周历

| 能力 | 主表面 | 已做 | 建议下一档 | 不做 |
|------|--------|------|------------|------|
| `slot_reserve` | SlotBook 等 | **时段色块**；满员 disabled | — | 真闸机 |
| `staff_roster` | SlotBook | 当班 hint；**日期旁当班绿点** | — | 智能排课 |
| （周历） | WeekCalendar | **状态色条 tone-*** | — | 拖拽改期 |

### D. 交易 / 购物车 / 订单 / 评价

| 能力 | 主表面 | 已做 | 建议下一档 | 不做 |
|------|--------|------|------------|------|
| `order_lines` | Cart / MyOrders | 支付倒计时；ImmSteps；EmptyHint；取餐码 QR | — | 真支付/骑手 SDK |
| `order_review` | MyOrderReviews | rate；**回复气泡**；EmptyHint | — | 舆情 NLP |
| （地址簿） | Addresses | 默认/标签 tag | — | 真地图选点 |

### E. 会员 / 券 / 满减

| 能力 | 主表面 | 已做 | 建议下一档 | 不做 |
|------|--------|------|------------|------|
| `wallet` | Profile / Cart | 余额；充值档；**不足红字+去充值（Cart）** | — | 商家自充；真清算 |
| `points` | Profile | 积分；**流水迷你列表**（`/api/loyalty/ledger`） | — | 积分商城岛 |
| `member_tier` | Profile | 等级名；**等级色条** | — | 成长任务引擎 |
| `spend_discount` | Cart | 满减明细 | — | 营销中台 |
| `coupon` | MyCoupons | 撕边；过期倒计时；EmptyHint | — | 券包直播 |

### F. 私信 / 留言 / AI / 模板

| 能力 | 主表面 | 已做 | 建议下一档 | 不做 |
|------|--------|------|------------|------|
| `dm` | Dm.vue | 头像；表情；相对时间；店长皮 | — | WebSocket IM |
| `guestbook` | Guestbook | 头像；相对时间；EmptyHint | — | 楼中楼 |
| `ai_assistant` | AiAssistantFloat | FAB；助/我头像；**关面板新回复小红点** | — | 自研模型/管理端聊天窗 |
| `message_template` | MessageTemplatesAdmin | 启用 tag | — | 真短信邮件 |

### G. 考试 / 问卷 / 投票

| 能力 | 主表面 | 已做 | 建议下一档 | 不做 |
|------|--------|------|------------|------|
| `exam` | ExamTake 等 | **倒计时 + 答题卡** | — | 人脸监考 |
| `survey` | Survey* / SurveyStatsAdmin | EmptyHint；**回收进度条**（目标读 stock/target） | — | 跳题 SPSS |
| `vote` | VoteCast / VoteCampaigns | **avatarUrl 列**（运行时补列 + 管理端 URL）；票数条；EmptyHint | — | ≠报名壳 |

### H. 文库 / 时间银行 / 选座 / 签章 / 打卡

| 能力 | 主表面 | 已做 | 建议下一档 | 不做 |
|------|--------|------|------------|------|
| `doclib` | DocBrowse / DocMine | **文件类型标**；EmptyHint | — | RAG 冒充 |
| `timebank` | TimebankAccount | 大号余额；**环形进度** | — | ≠劳动认定岛 |
| `seat_select` | SeatMap | 色点图例；**选中缩放微动效** | — | 真锁座高并发 |
| `e_sign` | ESignMine | 预览；**签署完成 ✓** | — | 第三方 CA |
| `archive_log` | dashboard / AdminLayout | 缺卡待办；**菜单红点 badge** | — | 物联网采集 |

### I. 浅进销存

| 能力 | 主表面 | 已做 | 建议下一档 | 不做 |
|------|--------|------|------------|------|
| `stock_*` | StockMovesAdmin | **盘盈盘亏 StatusChip tone** | — | 多仓 ERP |

### J. 组织 / 审计 / 管理台

| 能力 | 主表面 | 已做 | 建议下一档 | 不做 |
|------|--------|------|------------|------|
| `org_users` | UsersAdmin | **列表迷你头像** | — | AD 同步 |
| `audit_log` | AuditLogsAdmin | **动作类型色标** | — | 等保一体机 |
| （工作台） | TicketDashboard | 卡片；**数字入场动画** | — | 大数据平台 |
| `book_suggest` | BookSuggest | **状态 tag 色** | — | ≠PROCURE |

---

## 空态 / 角标 / 进度 · 横切模式

| 模式 | 现状 | 建议 |
|------|------|------|
| 列表空态 | **`EmptyHint.vue`** 已挂交易/收藏/消息/足迹/留言/问卷/投票/文库/评价等 | 其余纯文案列表可继续替换 |
| 未读角标 | MessageBell、Dm、CartBadge、Admin 待办/缺卡 | — |
| 倒计时 | 支付 / flash / exam / hold / coupon → **`useCountdown`** | — |
| 进度 | ImmSteps、StatusChip、TicketProgress、座位图例 | — |
| 星级 | TicketRate / order_review / 预约评价 | — |
| 图表 | DashboardCharts | 勿另做驾驶舱产品 |

---

## 明确不做（边角也不能冒充）

- 表情商店 / 付费贴纸 / 自定义 GIF 键盘  
- WebSocket / 环信融云 / 已读双蓝勾；聊天发图发文件语音通话  
- 真地图轨迹、人脸、指纹、原生推送、道闸、车牌识别  
- 微信支付/支付宝商户清算  
- 协同过滤 / CNN / 自研 TTS / 向量 RAG  
- 按 DOM 复制多套「农产聊天 / 图书聊天」  
- 把沉浸边角写进交付审计红灯

---

## 落地纪律

1. **一岛一表面**：改共享 baseline，不按域分叉。  
2. **开题未写 ≠ 禁止加分**：头像/空态/色点可常驻；表情/倒计时/二维码跟已挂能力。  
3. **非强制**：不进 `delivery-audit-rules` 红灯。  
4. **有生成路径才开开关**。  
5. **跨域同修**：jdbc/mybatis/jpa 无关则不必三套前端。  
6. **诚实边界提示**：短轮询、FAQ 回落、在线支付（不对接商户 SDK、仍扣账户余额）须保留说明，禁止用「演示」打发。

---

## 附录：能力 → 主表面速查

| cap | 用户主表面（摘要） |
|-----|-------------------|
| archive / gallery / search_assist / post_like / flash_price / product_spec / room_equipment / favorites / recommend | `ArchiveBrowse` + `RecommendStrip` |
| ticket_flow / deadline / loan_renew / waitlist / checkin / pass_code / code_qr / multi_approve / rating_dims / book_hold | `MyTickets` + admin Tickets* + `CodeQrBlock` / Progress / Rate |
| slot_reserve / staff_roster | `SlotBook` · `MyReservations` |
| order_lines / order_review | `Cart` · `MyOrders` · `MyOrderReviews` |
| wallet / points / member_tier / spend_discount / coupon | `Profile` · `Cart` · `MyCoupons` |
| dm / guestbook / ai_assistant | `Dm` · `Guestbook` · `AiAssistantFloat` |
| exam / survey / vote | `Exam*` · `Survey*` · `Vote*` |
| doclib / timebank / seat_select / e_sign / archive_log | `Doc*` · `Timebank*` · `Seat*` · `ESign*` · ArchiveLogs |
| stock_* | `StockMovesAdmin` · `StockLedgerAdmin` |
| org_users / audit_log / book_suggest / browse_history / mutual_select | Users / AuditLogs / BookSuggest / BrowseHistory / PeerTickets |

---

*扫描说明：对照 `capabilities.py` 全 55 项 + baseline 学生前端主表面；非按 68 个 DOM 抄表。*  
*2026-09-11：共用件与主路径边角已齐；第三轮落地列表 skeleton、公告 pinned、候选人 avatar_url、设备图标字典（均走共享表面 / 运行时补列，不按 DOM 分叉）。*
