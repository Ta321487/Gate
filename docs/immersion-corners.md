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
| 登录/注册壳 | `views/Login.vue` · `views/Register.vue` · `components/AuthShell.vue` | 多模板 auth；`authHero` 氛围底图；eyebrow/品牌标题/要点列表 | 无图时域色板渐变兜底；验证码刷新动效 | 第三方 OAuth 全家桶、短信验证码网关 |
| 个人资料 | `views/Profile.vue` | `el-avatar` 上传；昵称同步顶栏；loyalty 余额/积分/会员条；充值档位（**仅买家**） | 资料完善度进度条（缺必填提示） | 社交主页 Feed、动态墙 |
| 门户顶栏 | `layouts/PortalLayout.vue` | 头像+昵称；`MessageBell`；`PortalCarousel` 轮播圆点 | 购物车角标数字（有 `order_lines` 时） | 原生推送铃、App 角标 SDK |
| 工作台壳 | `layouts/AdminLayout.vue` · `layouts/WorkLayout.vue` | 消息铃；菜单文案 | 待办菜单旁 badge（数字来自 dashboard） | 复杂 BI 大屏、可配置仪表盘引擎 |
| 站内信铃 | `components/MessageBell.vue` | `el-badge` 未读；未读高亮行；60s 轮询计数；空态「暂无消息」 | 按类型小图标（审核/订单/系统） | 推送中台、邮件/短信通道 |
| 消息中心 | `views/user/Messages.vue` | 未读样式；全部已读；空态 | 同铃：类型图标 + 相对时间 | 已读回执商业 IM |
| 门户首页 | `views/user/PortalHome.vue` · `views/Home.vue` | mall 封面字母占位；editorial 资讯封面；功能卡片 | 空货架插画 +「去逛逛」CTA | 个性化运营弹窗轰炸 |
| 轮播 | `components/PortalCarousel.vue` | 自动轮播 + dots | — | 视频直播轮播 |
| 缺页/加载 | `components/PageSkeleton.vue` · `components/EntityDetailLayout.vue` · `views/NoticeDetail.vue` | 详情骨架屏 | 列表页统一 skeleton 变体 | 全站 SPA 假进度条刷存在感 |
| 游客提示 | `components/GuestLoginHint.vue` | 未登录引导 | — | 强制注册墙 |

---

## 按能力岛表

### A. 档案 / 浏览 / 内容周边

| 能力 | 主表面 | 已做 | 建议下一档 | 不做 |
|------|--------|------|------------|------|
| `archive` | `views/user/ArchiveBrowse.vue` · `views/admin/ArchiveAdmin.vue` · `views/user/MyArchive.vue` | 封面图；列表空态；库存/上架 `el-tag`；低库存「预警」；详情字段皮 | 缺图统一占位插画；卡片 hover 轻抬 | 真以图搜图、SKU 矩阵 |
| `gallery` | 同上（详情轮播）· `ArchiveAdmin` 图集编辑 | `el-carousel` 多图；管理端最多 9 张 | **灯箱点击放大**（`el-image` preview） | 图床 CDN、图片编辑器 |
| `search_assist` | `ArchiveBrowse` | 前缀联想 + 热搜词 chips | 热搜「火」小标 | 语义检索 / Elasticsearch |
| `recommend` | `components/RecommendStrip.vue` | 封面/字母兜底；原因 pill；横滑条 | 空推荐时藏整条 | 协同过滤、矩阵分解 |
| `favorites` | `ArchiveBrowse` 按钮 · `views/user/MyFavorites.vue` | 收藏列表封面+空态引导 | 红心切换轻动画 | 心愿单社交分享 |
| `browse_history` | `views/user/BrowseHistory.vue` | 封面足迹列表；空态 | 「清除足迹」确认 + 相对时间 | 跨设备同步云足迹 |
| `post_like` | `ArchiveBrowse` | 点赞文案+计数 | 点赞数角标色点 | 刷赞排行榜作弊对抗 |
| `content_report` | `ArchiveBrowse` 举报弹窗 · `admin/ContentReportsAdmin.vue` | 理由输入；管理处置 | 列表「已举报」灰态提示 | 舆情 NLP、自动鉴黄 |
| `post_mute` | 管理端档案/用户相关处置（扫词开） | 禁言截止能力已有 | 用户发帖失败时友好提示「禁言至…」 | 整站禁言大厅、敏感词引擎 |
| `content` | `views/Notices.vue` · `NoticeDetail.vue` · `admin/NoticesAdmin.vue` | 列表空态；详情骨架 | 置顶角标 | 资讯推荐算法 |
| `room_equipment` | `ArchiveBrowse` 详情设备条 · `admin/EquipmentDictAdmin.vue` | 设备名列表；字典启用 tag | 设备小图标字典（可选） | ≠设备借用主路径 |
| `product_spec` | `ArchiveBrowse` | 规格文案行 | 详情 Tab「规格参数」 | SKU 多规格库存矩阵 |
| `flash_price` | `ArchiveBrowse` | 活动价 badge + 划线价 | **窗内倒计时**（至 `promoEnd`） | 真秒杀高并发锁库存 |
| `quota` | `ArchiveBrowse` 申请库存提示 · 列表 stock | 剩余数量文案 | 紧张库存橙色提示 | 多仓 WMS |
| `time_conflict` | 申请弹窗校验（Browse） | 冲突拒单+提示 | 冲突时段高亮一句 | 拖拽智能排课 |
| `waitlist` | `ArchiveBrowse` 候补动词 · `MyTickets` 状态 tag | `waitlisted` warning tag | 候补位次「第 N 位」 | 复杂优先级队列 UI |
| `book_hold` | `ArchiveBrowse` 预约动词 · 我的单据 | 到书/确认借阅流（能力层） | 「保留至」倒计时条 | ≠报名候补混皮 |
| `bed_occupy` / `instrument_slot` | 复用 archive+ticket±slot 表面 | 同档案/单据/时段壳 | 床位/机时占用色点（复用 slot 色） | 独立 DOM 皮肤分叉 |

### B. 单据流 / 催办 / 签到 / 互选 / 通行

| 能力 | 主表面 | 已做 | 建议下一档 | 不做 |
|------|--------|------|------------|------|
| `ticket_flow` | `views/user/MyTickets.vue` · `admin/TicketsAdmin.vue` · `TicketRecordsAdmin.vue` | 状态 `el-tag`；领取提示色；空态；`TicketProgressDialog` | **状态色点**（待审/中/完）统一 class | 任意 BPMN 流程图 |
| `multi_approve` | 同上（`pending_final` 等） | 多级状态 tag | 简易 `el-steps`（初/复/终） | 可配置工作流引擎 |
| `deadline` | `MyTickets` · `admin/OverdueAdmin.vue` · dashboard 逾期行 | 逾期入口；催办动词皮 | 逾期行红色左边条 | 短信/电话网关 |
| `loan_renew` | `MyTickets` | 续借次数展示+按钮 | 续借成功 toast 含新应还日 | 无限续借策略引擎 |
| `checkin` | `MyTickets` 签到弹窗 · `ArchiveBrowse` 报名带码 | 口令输入 | 签到成功绿勾动效 | 人脸签到 |
| `mutual_select` | `views/user/PeerTickets.vue` | `el-empty` 空态 | 接受/婉拒按钮色语义加强 | 协同过滤配对 |
| `pass_code` | `MyTickets` | 通行码加粗展示 | 一键复制 | 闸机联动 |
| `code_qr` | `components/CodeQrBlock.vue`（挂 MyTickets） | 二维码弹窗+打印 | 取餐码同组件复用订单页 | 硬件扫码枪 SDK |
| `rating_dims` | `components/TicketRateDialog.vue` · Browse 申请星维 | 多维 `el-rate`；匿名 | 均分色点在列表 | 复杂量表统计包 |
| （单据进度） | `components/TicketProgressDialog.vue` | 时间线式进度；空态 | 节点图标（接单/完工） | 实时地图派单 |

### C. 预约 / 排班 / 周历

| 能力 | 主表面 | 已做 | 建议下一档 | 不做 |
|------|--------|------|------------|------|
| `slot_reserve` | `views/user/SlotBook.vue` · `MyReservations.vue` · `admin/ReservationsAdmin.vue` | 剩余/容量；disabled 满员；预约状态 tag；评价星；空态；号源预览 | **时段色块**（可约/紧张/满） | 真闸机/OTA 渠道 |
| `staff_roster` | `SlotBook` 当班提示 · `admin/StaffRosterAdmin.vue` | 值班文案 hint | 日历上当班小点 | 智能排课引擎 |
| （周历，域 trait） | `views/user/WeekCalendar.vue` | 只读周网格；空态 | 状态色条区分事件 | 拖拽改期 |

### D. 交易 / 购物车 / 订单 / 评价

| 能力 | 主表面 | 已做 | 建议下一档 | 不做 |
|------|--------|------|------------|------|
| `order_lines` | `views/user/Cart.vue` · `MyOrders.vue` · `admin/OrdersAdmin.vue` · `staff/StaffOrders.vue` | 空车 `empty-text`；订单状态 tag；**支付倒计时**（urgent≤60s）；取餐码/物流文案；`OrderTraceDialog` | 订单**进度条/色点**（待付→完成）；空订单插画 CTA | 真微信/支付宝商户、实时骑手轨迹 SDK |
| `order_review` | `MyOrders` · `MyOrderReviews.vue` · `admin/OrderReviewsAdmin.vue` · Browse 商品评价区 | `el-rate`；商家回复区；空态 | 回复气泡样式统一 | 舆情 NLP |
| （地址簿） | `views/user/Addresses.vue` | 默认 tag；标签 tag | — | 高德选点真地图 |

### E. 会员 / 券 / 满减（loyalty 组）

| 能力 | 主表面 | 已做 | 建议下一档 | 不做 |
|------|--------|------|------------|------|
| `wallet` | `Profile.vue` · `Cart.vue` 充值档 | 余额展示；50/100/200/500 档 | 余额不足红字+去充值（Cart 已有） | **商家自充**；真支付渠道清算 |
| `points` | `Profile` · `Cart` · `MyOrders` 获积分 | 积分数字 | 积分流水迷你列表入口 | 积分商城独立岛（未立能力勿装） |
| `member_tier` | `Profile` · `Cart` 折扣预览 | 等级名+折扣行 | 等级色条（普/银/金） | 成长任务游戏化引擎 |
| `spend_discount` | `Cart` preview | 满减明细行 | — | 第三方营销中台 |
| `coupon` | `views/user/MyCoupons.vue` · `Cart` 选券 · `admin/CouponsAdmin.vue` | 可领/我的 Tab；余量；过期筛选；空态 | 券卡片左右撕边视觉；过期倒计时 | 券包小程序直播间 |

### F. 私信 / 留言 / AI / 站内模板

| 能力 | 主表面 | 已做 | 建议下一档 | 不做 |
|------|--------|------|------------|------|
| `dm` | `views/user/Dm.vue`（管理端 `/admin/dm`） | **双方头像**；会话未读 badge；**常用表情条**；「约每 4 秒刷新」；空态 | 时间相对化；店长客服入口皮（`dmShopCs`） | WebSocket/环信/已读双蓝勾；发图文件语音通话 |
| `guestbook` | `views/Guestbook.vue` · `admin/GuestbookAdmin.vue` | 回复块；抢沙发空态；字数限制 | **留言人头像** + 相对时间 | 论坛楼中楼 |
| `ai_assistant` | `components/AiAssistantFloat.vue` · `views/AiAssistant.vue` · `admin/AiKnowledgeAdmin.vue` | FAB；助/我字标头像；热门 chips；播报 TTS；满意度；图片品类映射；空态；Key 诚实提示 | FAB 未读/新回复小红点（可选） | 自研模型/CNN/向量库集群；管理端同款聊天窗冒充 |
| `message_template` | `admin/MessageTemplatesAdmin.vue` → 写入 `sys_message` | 启用 tag；占位符说明 | — | 真短信/邮件通道 |

### G. 考试 / 问卷 / 投票

| 能力 | 主表面 | 已做 | 建议下一档 | 不做 |
|------|--------|------|------------|------|
| `exam` | `ExamPapers/Take/Attempts/Practice/Rank/Wrongbook.vue` · `admin/Exam*` | 列表空态；交卷得分卡 | **答题倒计时**顶栏；题号答题卡色点 | 人脸监考 |
| `survey` | `SurveyForms.vue` · `SurveyMine.vue` · `admin/SurveyFormsAdmin.vue` · `SurveyStatsAdmin.vue` | 空态；选项计数统计 | 回收进度条（已填/目标） | 跳题 SPSS |
| `vote` | `VoteCampaigns.vue` · `VoteMine.vue` · `admin/Vote*` | 限票说明；空态；结果管理 | 候选头像+票数条 | ≠活动报名壳 |

### H. 文库 / 时间银行 / 选座 / 签章 / 打卡

| 能力 | 主表面 | 已做 | 建议下一档 | 不做 |
|------|--------|------|------------|------|
| `doclib` | `DocBrowse.vue` · `DocMine.vue` · `admin/DocFilesAdmin.vue` · `DocLogsAdmin.vue` | 空态；下载台账 | 文件类型图标 | RAG / AI 知识库冒充 |
| `timebank` | `TimebankAccount.vue` · `TimebankLedger.vue` · `admin/Timebank*` | **大号余额数字**；流水正负 | 余额环形进度（相对目标可选） | ≠劳动认定整岛 |
| `seat_select` | `SeatShows.vue` · `SeatMap.vue` | **座位色点图例**（空闲/已选/已售）；银幕条；空态 | 选中座震动/缩放微动效 | 真锁座高并发、点播 |
| `e_sign` | `ESignMine.vue` · `admin/ESignAdmin.vue` | 签章图预览；同意留痕 | 签署完成绿勾 | CA/法大大等第三方 |
| `archive_log` | Browse 打卡区 · `admin/ArchiveLogsAdmin.vue` · dashboard 缺卡 | 异常 tag；今日缺卡待办 | 「今日未打卡」红点 | 物联网传感器采集 |

### I. 浅进销存

| 能力 | 主表面 | 已做 | 建议下一档 | 不做 |
|------|--------|------|------------|------|
| `stock_io` / `stock_scrap` / `stock_count` | `admin/StockMovesAdmin.vue` · `StockLedgerAdmin.vue` · `ArchiveAdmin` 库存列 | 预警 tag；流水台账 | 盘盈盘亏色点（绿/红） | 多仓 ERP、RFID |

### J. 组织 / 审计 / 管理台横切

| 能力 | 主表面 | 已做 | 建议下一档 | 不做 |
|------|--------|------|------------|------|
| `org_users` | `admin/UsersAdmin.vue` · 登录角色 | 启用停用 tag（Home 等） | 用户列表迷你头像 | 企业 AD 同步 |
| `audit_log` | `admin/AuditLogsAdmin.vue` | 筛选列表 | 动作类型色标 | 等保一体机 |
| （工作台） | `admin/TicketDashboard.vue` · `components/DashboardCharts.vue` | 统计卡片；待办数字；ECharts 饼/趋势/库存/热销 | 卡片数字跳动轻动画 | 独立大数据平台 |
| `book_suggest` | `views/user/BookSuggest.vue` · `admin/BookSuggestAdmin.vue` | 空态 | 状态 tag 色 | ≠PROCURE 期刊遴选 |

---

## 空态 / 角标 / 进度 · 横切模式（非单 cap）

| 模式 | 现状 | 建议 |
|------|------|------|
| 列表空态 | 大量 `class="empty"` 纯文案；少数 `el-empty`（`PeerTickets`）；Cart 用 `empty-text` | 抽 1 个 `EmptyHint.vue`（插画可选 + 主 CTA），交易/收藏/消息优先 |
| 未读角标 | MessageBell、Dm 会话 | Admin 菜单待办 badge |
| 倒计时 | MyOrders 支付倒计时；flash/exam **建议补** | 统一 `useCountdown` 工具，urgent 样式复用 |
| 进度 | TicketProgressDialog、OrderTraceDialog、座位图例 | 订单/多级审 steps |
| 星级 | TicketRateDialog、order_review、预约评价、多维评分 | — |
| 图表 | DashboardCharts（ECharts 常驻） | 勿另做「驾驶舱」产品 |

---

## 明确不做（边角也不能冒充）

- 表情商店 / 付费贴纸 / 自定义 GIF 键盘  
- WebSocket / 环信融云 / 已读双蓝勾商业 IM；聊天发图发文件语音通话（无新能力生成路径）  
- 真地图轨迹、人脸、指纹、原生推送、道闸抬杆、车牌识别硬件  
- 微信支付/支付宝商户清算（演示渠道文案 ≠ 真对接）  
- 协同过滤 / CNN 以图搜图 / 自研 TTS 模型 / 向量 RAG 工程  
- 为每个 DOM 复制「农产聊天 / 图书聊天 / 宿舍 AI」多套实现  
- 把沉浸边角写进交付审计红灯或假装「开题点名的 L3 已齐」

---

## 落地纪律

1. **一岛一表面**：优先改 `Dm.vue` / `AiAssistantFloat.vue` / `ArchiveBrowse.vue` / `MyOrders.vue` / 共用组件，不按域分叉。  
2. **开题未写 ≠ 禁止加分**：头像、空态、状态色点可常驻；表情、限时倒计时、二维码等跟已挂能力走。  
3. **非强制**：本清单不进 `delivery-audit-rules` 红灯；老板小卡可不点名。  
4. **有生成路径才开开关**：禁止只改论文/README 假装已集成。  
5. **跨域同修**：沉浸补丁落在 baseline 共享表面后，jdbc/mybatis/jpa 无关则不必三套前端；域文案走 schema labels。  
6. **诚实演示**：短轮询、FAQ 回落、演示支付、品类识图等须保留提示，勿用边角包装成实时/真 AI 视觉。

---

## 附录：能力 → 主表面速查

| cap | 用户主表面（摘要） |
|-----|-------------------|
| archive / gallery / search_assist / post_like / flash_price / product_spec / room_equipment / favorites(入口) / recommend | `ArchiveBrowse.vue` + `RecommendStrip.vue` |
| ticket_flow / deadline / loan_renew / waitlist / checkin / pass_code / code_qr / multi_approve / rating_dims / book_hold | `MyTickets.vue` + admin Tickets* + `CodeQrBlock` / `TicketProgressDialog` / `TicketRateDialog` |
| slot_reserve / staff_roster | `SlotBook.vue` · `MyReservations.vue` · `ReservationsAdmin.vue` |
| order_lines / order_review | `Cart.vue` · `MyOrders.vue` · `MyOrderReviews.vue` · `OrdersAdmin.vue` |
| wallet / points / member_tier / spend_discount / coupon | `Profile.vue` · `Cart.vue` · `MyCoupons.vue` |
| dm / guestbook / ai_assistant | `Dm.vue` · `Guestbook.vue` · `AiAssistantFloat.vue` |
| content | `Notices.vue` |
| exam / survey / vote | `Exam*` · `Survey*` · `Vote*` |
| doclib / timebank / seat_select / e_sign / archive_log | `Doc*` · `Timebank*` · `Seat*` · `ESign*` · `ArchiveLogsAdmin` |
| stock_* | `StockMovesAdmin.vue` · `StockLedgerAdmin.vue` |
| org_users / audit_log / message_template / content_report / book_suggest / browse_history / mutual_select | Users / AuditLogs / MessageTemplates / ContentReports / BookSuggest / BrowseHistory / PeerTickets |
| bed_occupy / instrument_slot / quota / time_conflict / post_mute | 复用 archive+ticket(+slot) 表面，无独立岛页 |

---

*扫描说明：对照 `capabilities.py` 全 55 项 + baseline 学生前端主表面；非按 68 个 DOM 抄表。后续落地请改共享表面并回写「已做」列。*
