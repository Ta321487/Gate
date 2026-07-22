# 毕设港 · 交接（能力运行时 + 新领域）

工作区：`d:\graduate_factory_v3`  
**禁止**参考 / 迁移 `d:\graduate_factory`、`d:\graduate_factory_v2`。

---

## 先做什么（顺序）

1. **能力运行时（基线）** ✅ 已齐：`ArchiveStore` / `TicketStore` / `OrderStore` / `SlotStore` + 通用 API  
2. **薄领域** ✅ 组 A～G + GENERIC 兜底已可 bake；差的是按需冒烟与文案微调  
3. **当前主线**：薄域冒烟 → **LLM 只填 schema JSON**（不生成业务 Java/Vue）；L1 亮点已齐  
4. **Path B · 开题全文答辩** ✅ 三条真交叉可 full（借用+下单 / 借用+预约 / 下单+预约）；三合一与智慧校园仍 reject；超壳 reject

接 LLM 后「代码无误」靠的是运行时固定，不是 LLM 写码。  
**Path B 口径**：开题写进「拟实现」的必须能答辩演示；做不到就 **拒收 / 改开题 / 先扩能力**，禁止再用 `degraded` 交半成品装全文。

### 接题边界（硬原则，Path B 也遵守）

本产品定位：**专科 / 本科毕设、课设级别的 Web 管理系统生成**（演示级主路径），不是研究生平台，也不是真实业务交付。

| 接 | 不接 |
|----|------|
| **专科 / 本科** 毕设、**课设**（Web 管理、演示级） | **硕士研究生 / 博士研究生** 课题与开题 |
| 薄域单路径；白名单内且 `defense_ready` 的交叉 | **真实业务全流程** / 生产级全链路 / 企业级端到端 |
| L0～L2 积木内可演示的功能 | L3、HIS/ERP 级发散、未就绪交叉 |

Path B 的「全文答辩」= **专科/本科（含课设）开题里拟实现、且落在白名单/单域能力内的全文**，不是把硕博题或真实生产流程接进来。  
信号：`OUT_OF_SCOPE_SIGNALS`（硕博学位论文、真实业务全流程等）→ `reject`。

---

## 能力积木（`capabilities.py` · 与 `BASELINE_RUNTIME_CAPS` 对齐）

接题只认下表 **cap id**；`status=implemented` 均可进 `accept=full`。

**挂载口径（原有约定，不是新分类）**：

| 口径 | 含义 |
|------|------|
| **域默认** | 该域 bake 时直接带上（如 SHOP 带 `favorites`） |
| **开题写到才挂** | 材料里找到对应描述才写入 caps；**没有就保持原样**（如联想 / 足迹 / 多图 / 订单评价） |
| **壳附带** | 有订单壳或预约壳即有，不单独占 cap（售后、物流轨迹、改约、办结） |
| **扫词写配置** | 开题写到 → 写 yml/开关，仍无独立 cap（如超时关单分钟数） |
| **schema 开关** | 二级审批 / 互斥 / 签到 / 软删 / 周历等 → 见 L1，不另开 cap |

### 壳与主路径

| 能力 | 状态 | 含义 | 解锁的典型题 |
|------|------|------|----------------|
| `org_users` | ✅ | 角色用户、资料、重置密码、工作台 | 全部 |
| `content` | ✅ | 公告 / 资讯 | 全部 |
| `archive` | ✅ | 分类 + 业务对象 CRUD / 检索 / 详情 | 图书、设备、商品、菜品、片单… |
| `ticket_flow` | ✅ | 提交→审/受理→完结；我的与待办 | 借阅、报修、报名… |
| `quota` | ✅ | 库存 / 名额占用与归还 | 借阅、选课、设备… |
| `deadline` | ✅ | 到期、逾期、催办、可选费用 | 借阅、租赁… |
| `time_conflict` | ✅ | 起止时段相交 + 报名截止 | 选课、活动报名… |
| `slot_reserve` | ✅ | 资源时段占坑、取消与履约办结 | 挂号、车位、会议室、美发、客房 |
| `order_lines` | ✅ | 购物车 + 多明细订单（无真支付） | 商城、点餐、客房 |
| `recommend` | ✅ | 猜你喜欢（分类偏好 + 热度 + 上新；非协同过滤） | 内容壳 / 档案浏览常见 |

### 交易附加（须已有 `order_lines`）

| 能力 | 状态 | 含义 | 挂载口径 |
|------|------|------|----------|
| `guestbook` | ✅ | 门户留言；总管删与简短回复（≠ 公告 ≠ 论坛） | 域默认 SHOP/FOOD/GENERIC·TRADE；否则开题写「留言」才挂 |
| `favorites` | ✅ | 收藏夹：收藏/取消，再加购 | 域默认 SHOP/FOOD；否则开题写「收藏」才挂 |
| `coupon` | ✅ | 券模板领取 → 我的券 → 下单核销 → 过期扫标 | 开题写到才挂 |
| `wallet` | ✅ | 演示余额扣/退（非真支付）；管理端可充值 | 开题写到才挂 |
| `points` | ✅ | 消费积分入账（不可充值） | 开题写到才挂 |
| `spend_discount` | ✅ | 满减算价（与券取更优） | 开题写到才挂 |
| `member_tier` | ✅ | 会员成长等级折扣 | 开题写到才挂 |
| `order_review` | ✅ | 完成单星级+文字；管理端回复 | 开题写到才挂（无域默认） |
| `search_assist` | ✅ | 标题前缀联想 + 配置热搜 | 开题写到才挂（无域默认） |
| `browse_history` | ✅ | 最近浏览足迹（约 20 条） | 开题写到才挂（无域默认） |
| `gallery` | ✅ | 档案 `gallery_json` 多图（非 SKU） | 开题写到才挂（无域默认） |

依赖未实现能力 → `accept=reject`；上表均已落地。

**壳附带（无独立 cap）**：有 `order_lines` → 地址簿、售后、物流轨迹；有 `slot_reserve` → 办结 `complete`、改约 `reschedule`。  
**扫词写配置（无独立 cap）**：开题写「超时取消/支付超时」→ `thesis.order-timeout-minutes=30` + `@Scheduled`。

源码对照：`backend/app/bake/capabilities.py` 的 `CAPABILITIES` 键集 = 上表全部 id；增删能力须同步改本表与 `BASELINE_RUNTIME_CAPS`。

---

## 90% 毕设覆盖：领域清单（薄配置，不是厚代码包）

按**能力组合**分组；同组共享同一套运行时，差别主要在 schema 文案/种子/菜单。组 **H** 为真交叉（两套玩法），见 G 节之后。

### A. 借用 / 占用流（能力齐，可先薄落地）

| 领域 ID | 覆盖题目关键词 | 能力组合 |
|---------|----------------|----------|
| **DOM-LIBRARY** | 图书、图书馆、借阅、读者 | archive + ticket_flow + quota + deadline + content + org_users |
| **DOM-EQUIP** | 设备借用、器材、实验室物资 | 同上 |
| **DOM-ASSET** | 固定资产领用、耗材申领、物资台账 | archive + ticket_flow + quota + content + org_users（无 deadline；与 EQUIP 设备借用区分） |
| **DOM-CRM** | 客户关系、客户跟进、销售线索 | archive + ticket_flow + content + org_users（轻量跟进单；不接公海/外呼） |

### B. 报修 / 工单流（能力齐）

| 领域 ID | 覆盖题目关键词 | 能力组合 |
|---------|----------------|----------|
| **DOM-DORM** | 宿舍报修、水电、寝室 | ticket_flow + content + org_users（±archive） |
| **DOM-PROPERTY** | 物业报修、社区维修 | 同上 |
| **DOM-IT** | 校园网报修、IT 运维工单 | 同上 |

### C. 报名 / 申请流（能力齐）

| 领域 ID | 覆盖题目关键词 | 能力组合 |
|---------|----------------|----------|
| **DOM-ACTIVITY** | 社团活动、志愿活动报名 | archive + ticket_flow + quota + content + org_users + **time_conflict** |
| **DOM-LOST** | 失物招领 | archive + ticket_flow + **quota** + content + org_users |
| **DOM-COURSE** | 选课、公选课（名额） | archive + ticket_flow + quota + content + org_users + **time_conflict**（+ L1 互斥/分类限额） |

### D. 交易 / 点餐（`order_lines` 已开）

| 领域 ID | 覆盖题目关键词 | 能力组合 |
|---------|----------------|----------|
| **DOM-SHOP** | 商城、二手、购物车、订单 | archive + order_lines + quota + content + org_users + **guestbook** + **favorites**（开题可再扫 coupon / loyalty / order_review / 联想·足迹·多图） |
| **DOM-FOOD** | 食堂、点餐、外卖档口 | 同上 |

交易答辩口径：下单 → 管理确认/发货 → 用户看物流轨迹 → 完成；可选领券核销、售后、收藏再加购、评价。

### E. 预约流（`slot_reserve` 已开）

| 领域 ID | 覆盖题目关键词 | 能力组合 |
|---------|----------------|----------|
| **DOM-HOSPITAL** | 挂号、门诊预约 | archive + slot_reserve + content + org_users |
| **DOM-PARKING** | 车位预约 | archive + slot_reserve + content + org_users |
| **DOM-MEETING** | 会议室预约 | archive + slot_reserve + content + org_users |
| **DOM-SALON** | 美发/美容/场地预约 | archive + slot_reserve + content + org_users |
| **DOM-HOTEL** | 宾馆客房 | archive + slot_reserve + order_lines + content + org_users |

预约答辩口径：选时段占坑 →（可选确认）→ 管理端履约办结 / 用户取消或改约。状态含 `completed`（入场/就诊/到店/入住离店等文案随 schema）。

### F. 兜底

| 领域 ID | 覆盖 | 能力 |
|---------|------|------|
| **DOM-GENERIC** | 对不上具体行业关键词时的兜底域 | 按 **ARCH-*** 绑壳：CRUD / FLOW / TRADE / RESERVE（见下） |

未命中具体 `DOM-*` 时 **禁止**误落 LIBRARY：`score_catalog(..., fallback="DOM-GENERIC")`。  
匹配原则：**行为词桶（ARCH）有上限**，不堆行业百科；具体 DOM 若盖不住原型能力 → 降 `DOM-GENERIC`（`reconcile_match`）。  
上传开题时对**全文**匹配，并优先加权「主要功能 / 研究内容」段（`proposal_focus_for_match`）：开题写到的行为应对齐可交付壳。  
小程序/人脸/真支付等 L3 与业务过重信号 → **`accept=reject`（Path B）**，不可 degraded 出 ZIP。  
**多主路径**：功能段命中多条 ARCH 时写入 `archetypes` 并集；须命中交叉白名单且 `defense_ready`（见下节），否则 reject。  
GENERIC SQL 由 `sql_compose` 拼装；前端 `withExtraBizRoutes` 追加预约/订单路由。  
GENERIC 再按原型选 SQL/runtime/gate（`archetype_shells.py`）：

| ARCH | 能力 | bake SQL |
|------|------|----------|
| ARCH-CRUD | archive + content + org_users | `DOM-GENERIC.sql` |
| ARCH-FLOW / STOCK / CONTENT | + ticket_flow（±quota） | `DOM-GENERIC-FLOW.sql` |
| ARCH-TRADE | + order_lines + **guestbook**（+ 默认 **favorites**） | `DOM-GENERIC-TRADE.sql` |
| ARCH-RESERVE | + slot_reserve | `DOM-GENERIC-RESERVE.sql` |

### G. 内容 / 媒资 / 社区（能力齐，可薄落地）

| 领域 ID | 覆盖题目关键词 | 能力组合 |
|---------|----------------|----------|
| **DOM-MEDIA** | 影视、电影、电视剧、综艺、视频点播、在线视频、片库 | archive + ticket_flow + content + org_users |
| **DOM-MUSIC** | 音乐、歌曲、歌单、在线音乐、音乐播放器、听歌 | 同上 |
| **DOM-FORUM** | 论坛、BBS、贴吧、社区帖子、板块 | 同上 |
| **DOM-BLOG** | 博客、个人博客、文章系统、资讯发布、CMS | 同上 |

**媒资（MEDIA/MUSIC）**：播放为外链 / HTML5（`isbn` 映射播放链接）；收藏走单据流。不接影院选座购票、直播、转码 CDN。

**论坛 / 博客（FORUM/BLOG）** — 薄配置语义（复用 archive+ticket，**不是**厚 UGC 引擎）：

| 概念 | 运行时映射 | 说明 |
|------|------------|------|
| 板块 / 分类 | `category` | 总管主数据 |
| 版主任职（FORUM） | `board_moderator` | 子管挂板块；种子/ER 用，非厚 Store |
| 主帖 / 文章 | archive 主表（`post` / `article`） | 总管 CRUD；`isbn`=`TEXT` 富文本 HTML（`type: richtext`） |
| 标签 / 附件（FORUM） | `tag` + `post_tag` + `post_attach` / `reply_attach` | 补齐库表与 ER；运行时仍以 archive+reply 为主路径 |
| **回复 / 楼层（FORUM）** | `ticket_flow`（`reply`） | 挂主帖；`remark`=富文本；`allow_multi_ticket` 可多次跟帖 |
| 收藏 / 订阅（BLOG） | `ticket_flow`（`favorite`） | 读者收藏博文 → 编辑确认 |
| 站内公告 | `content` | 与帖文分离，勿混用 |
| 猜你喜欢 | `recommend` | 分类偏好 + 热度 + 上新 |

**富文本（在范围内）**：基线 `RichTextEditor` / `RichTextView`（粗斜体、列表、链接；前端消毒）。主帖/文章与论坛回复走富文本；**不是**多人协同编辑。

**楼中楼（FORUM，在范围内）**：同一主帖下多条回复即楼层；「回复某人」用正文 `@昵称` 一层引用。不接无限深度树形引擎。

**刻意不接（reject / out_of_mvp）**：实时私信、富文本协同编辑、用户自由开新主帖无审核（主帖仍总管维护）、人脸、协同过滤/深度推荐、物联网、真支付、小程序/安卓原生、大数据作业等（见 `OUT_OF_SCOPE_SIGNALS`）。

轻量「猜你喜欢」（`recommend` 能力）：档案域按分类偏好 + 热度 + 上新兜底，挂 LIBRARY / EQUIP / MEDIA / MUSIC / FORUM / BLOG；**不是**协同过滤。

### H. 真交叉（专科/本科·课设常见；Path B 已可 full）

与组 A～G **单域换皮**并列；开题写清**两套玩法**时匹配降 `DOM-GENERIC` 并保留行为并集（不再挤掉借用/审核）。  
样例开题（可上传匹配）：`data/samples/图书借阅与二手交叉开题.txt`。三合一 / 智慧校园大杂烩 → reject。

| 交叉 ID | 覆盖题目关键词（开题常见说法） | 两套玩法 | 生成落点 | 状态 |
|---------|-------------------------------|----------|----------|------|
| **X-BORROW-SHOP** | 二手/跳蚤 + 借阅；点餐 + 报修；闲置交易 + 物品借用 | 申请/借用审核 + 购物车下单 | GENERIC 单据壳 + 订单路由 | ✅ |
| **X-BORROW-RESERVE** | 图书借阅 + 座位预约；场地预约 + 设备借用；报修 + 活动室预约 | 申请/借用审核 + 时段占坑 | GENERIC 单据壳 + 预约路由 | ✅ |
| **X-SHOP-RESERVE** | 小卖部 + 会议室预约；到店预约 + 卖套餐（非宾馆） | 下单 + 时段占坑 | GENERIC 订单壳 + 预约路由 | ✅ |
| （具名优先） | 宾馆 / 民宿 / 酒店客房 + 附加消费 | 预约 + 订单 | **DOM-HOTEL** 单域 | ✅ 走组 E |
| — | 借阅+二手+预约三套；智慧校园 N 合一 | — | reject / 裁成上表一条 | ❌ |

**答辩演示（三条共用口径，种子账号 bake 后见交付 README）**  
1. 借用+下单：门户提交借阅 → 管理端审核；再加购下单 → 订单办理。  
2. 借用+预约：借阅审核一路 + 选资源约时段（约满不可再约）一路。  
3. 下单+预约：约时段一路 + 购物车订单一路（宾馆题优先 DOM-HOTEL）。

匹配原则（`reconcile_match`）：行业皮盖不住开题里任一主路径 → **改用通用壳，保留全部路径**（禁止「留商城、丢借阅」）。

**Path B 白名单**（`cross_paths.py`）：上表三条可 full；实现键内部为 FT/FR/TR。  
SQL golden：`DOM-GENERIC__ARCH-FLOW_ARCH-TRADE` / `…FLOW_ARCH-RESERVE` / `…TRADE_ARCH-RESERVE`。  
**禁止**：DOM×DOM 厚融合；L3；硕博；真实业务全流程；三合一装全文。  
代码：`evaluate_cross_path` + `reconcile_match` + `resolve_accept`。

**覆盖率怎么理解**：A+B+C+D+E+F+G+**H（真交叉三条）** ≈ 常见 Web 管理类毕设主体；不是 100% 开题都能 full。L3 / 三合一 → **reject**（Path B）。

---

## 开题难度分层（可写 · 可加价做 · 仍不接）

**原则**：开题写进「拟实现」的，答辩要能演示。基线不是纯 CRUD——标配含单据流 + **时间冲突等轻规则**；再往上是可加价亮点；硬件/真支付/深度模型仍不接。

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
| 富文本正文/回复；论坛多楼 + @一层 | 基线编辑器 + 多单据 |

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
| **软删除** | 下架可恢复 | ★ | 已落地：`deleted_at`；LIBRARY/EQUIP/MEDIA/MUSIC/BLOG/FORUM/ASSET 默认开 |
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
| 实时客服 IM | 留言板 / 站内信 | WebSocket 私信 |
| 电子发票 / 税控 | 不接 | 开票服务对接 |
| 数据大屏 / 自定义报表 | 工作台 ECharts | 大屏工程 |
| 完整 SKU / 候补队列引擎 | 演示库存 + 时段占坑 | 独立库存/候补引擎 |
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

人脸/指纹门禁、物联网传感器、真微信支付支付宝、小程序/安卓为交付物、协同过滤与深度学习训练、直播弹幕与转码 CDN、区块链、Hadoop/Spark、BPMN 可配置工作流、多仓批次 ERP、实时私信与无限楼中楼树、富文本多人协同编辑。

**学历 / 真实生产（硬不接）**：硕士研究生、博士研究生课题；真实业务全流程 / 生产级全链路。本产品只做 **专科/本科毕设与课设** 演示级 Web 管理。

命中 `OUT_OF_SCOPE_SIGNALS` / `BUSINESS_OVERREACH_SIGNALS` → **`accept=reject`（Path B）**；改开题划入「非本期」或先扩能力，禁止当作本期演示承诺。  
业务过重（电子病历、处方、叫号大屏、BPMN、智能排课等）优先扫功能/拟实现段。  
多 ARCH 交叉另见「Path B · 交叉白名单」；`defense_ready=false` 的组合同样 reject。

### 开题怎么写（推荐）

1. **主要功能** = L0（含时间冲突等）+ 可选 1～2 个 L1 亮点；商城/点餐写购物车订单，预约类写时段占坑。  
2. 商城若写「收藏 / 优惠券 / 物流跟踪 / 售后」——前两项靠扫词进 caps，后两项订单壳自带，均可答辩演示。  
3. 预约若写「改约 / 到店完成 / 入场」——改约与办结随预约壳自带。  
4. **非本期** = L3 + 加价边界表（真支付、真短信、地图 SDK、真快递 API 等）。  
5. 换名词保留域关键词；冲突检测 vs 占坑一句分清：选课=本人已选相交；挂号=号源容量占坑。

---

## 硬约束：库表数量 6~15

- 常量：`backend/app/bake/engine.py` → `TABLE_COUNT_MIN/MAX`（含 L0 平台表 `sys_message`）
- DDL/种子模板：`backend/app/bake/sql/<DOMAIN>.sql`（`domain_sql` 加载；GENERIC 按 ARCH 选 `DOM-GENERIC*.sql`）
- bake 写 `schema.sql` 前 `assert_table_budget`；门禁 `p3t` 不过则禁 ZIP
- **现状样板**：GENERIC CRUD 6 / FLOW·RESERVE 7 / TRADE（含 guestbook）约 8～9 · SHOP/FOOD（guestbook+favorites）约 **12** · 多数薄域 8~9 · 图书/报修壳 9 · 论坛约 13 · **顶格 15**（券表/评价/足迹等按开题叠加）
- 论坛含：`sys_message` + 原业务/平台表
- 报修薄壳：楼栋/房间/类型/单据/进度/附件 + 用户/公告/消息
- 论文 **E-R** 按交付 SQL 如实画；**功能模块图** 按交付 menus/features 如实画（开题只辅助中文命名，与 E-R 同口径）；默认 **按业务拆**，工厂可切换 **按端拆** 预览/下载

## 学生端持久化（已完成）

- `UserStore` / `NoticeStore` / `MessageStore` / `ArchiveStore`+`TicketStore` → MySQL + JdbcTemplate  
- 工厂 `student_db.ensure_student_schema` + `GF_STUDENT_MYSQL_*`  
- 种子在 `schema.sql` 幂等；重启不 Cle 业务数据  

---

## 落地进度（能力运行时 + 薄域）

- [x] 基线 `ArchiveStore` / `TicketStore`（archive + standalone 工单模式）
- [x] LIBRARY 薄封装；通用 `/api/tickets` + 报修壳前端
- [x] **accept**：能力齐且落在基线积木内 → `full`（不再强制 DOM overlay）
- [x] 组 B：**DOM-DORM / PROPERTY / IT**（`gate_standalone_ticket` + runtime + SQL；L1 二级审批默认开）
- [x] 组 A：**DOM-LIBRARY / DOM-EQUIP**（均走 baseline 薄壳）+ **DOM-ASSET / DOM-CRM**（薄 SQL/schema；ASSET 无 deadline，CRM 轻量跟进单）
- [x] 组 G：**DOM-MEDIA / DOM-MUSIC**（收藏单据、播放外链）+ **DOM-FORUM / DOM-BLOG**（主帖/文章 + 回复/收藏单据；可选门户轮播）
- [x] 门户轮播：与登录图分套（`portal_banners.py`）；LIBRARY / EQUIP / FORUM / BLOG / ACTIVITY / COURSE 开启
- [x] 组 C：**DOM-ACTIVITY / LOST / COURSE**（报名/认领/选课；ACTIVITY/COURSE 含 `time_conflict` + 门户轮播）
- [x] L0 **站内消息** + **薄域工作台** + **ECharts / CSV 导出导入**
- [x] L2 **`order_lines` / `slot_reserve`**：组 D SHOP/FOOD + 组 E MEETING/HOSPITAL/PARKING/SALON/HOTEL
- [x] **匹配兜底**：零命中 → `DOM-GENERIC`；按 ARCH-* 绑 FLOW/TRADE/RESERVE（`archetype_shells.py`）；多 ARCH 并集可拼 SQL
- [x] **Path B**：三条真交叉可 full；匹配并集不再挤掉借用；HANDOFF 组 H 表；样例 `data/samples/图书借阅与二手交叉开题.txt`；三合一仍 reject
- [ ] Path B 可选：交叉组合端到端冒烟（预览点通）与开题对照表 UI
- [x] L1 **二级审批 / 强制附件 / 完结评分**：`configureL1`；FE 待办 `todo`、上传、`TicketRateDialog`
- [x] L1 **互斥码 / 分类限额**：`mutex_code` + `configureRules`；COURSE 种子 MX-ELECTIVE + 每类 1 门
- [x] L1 **软删除 / 标签 AND / 周历 / 签到码**：按域 schema 开关；FORUM 复用 tag 表；COURSE/ACTIVITY 周历；ACTIVITY 口令签到
- [x] L0 **访客留言 `guestbook`**：`GuestbookStore` + 门户/总管；默认 SHOP/FOOD/GENERIC·TRADE；开题可扫入
- [x] L1 交易 **`favorites` / `coupon` 完整券生命周期 + loyalty 扫词**：领取/我的券/核销/过期；SHOP/FOOD 默认收藏
- [x] L1 **`order_review` + 超时关单**：材料命中评价；超时扫词 → 30 分钟 `@Scheduled`
- [x] **论文图**：E-R（SQL）+ 功能模块图（menus/features；按业务 / 按端可切换）；开题只辅助中文命名，不发明表/模块
- [x] L1/L2 订单附带 **售后 + 演示物流轨迹**：`refund_*`；`OrderTraceDialog`（与审核进度同款 timeline）
- [x] L2 预约附带 **履约办结 `complete` + 用户改约 `reschedule`**
- [x] **登录入口随机**：`authEntryMode` = unified / role_pick / split_entry；身份控件 `authRoleWidget` = radio / select；后端按 `loginAs` 校验（选错身份拒登）
- [x] **四类角色 + 分域岗位**：门户用户 / 总管 / 子管理(clerk) / 业务员工(worker)；`schema.roles.staff_posts` + `staff_post`/`staff_kind`；分端 `/staff/login` + WorkLayout；任命仅总管
- [x] **生成不堵 API**：bake / 灌库 / pack / mvn 等同步重活 `asyncio.to_thread`；前端轮询静默短超时，reload 时不假死在 generating

### 宿舍验证账号（bake 后）

- 宿管（总管）`admin` / `admin123`：楼栋房间 + 报修类型 + 学生管理 + 公告 + 报修
- 楼管（子管理 clerk）`subadmin` / `sub123`：`staff_post=dorm_mgr`，仅报修受理/记录/工作台
- 维修员（业务员工 worker）`repairer` / `repairer123`：员工端 `/staff` 工单作业
- 学生 `student` / `student123`

样板：已收进 `skeletons/baseline`（LIBRARY 与 EQUIP 等同走薄壳）  
Catalog：`catalog.py`（匹配 / build_spec）  
目录：`domains.py`（`ARCHETYPES` / `DOMAIN_CAPABILITIES` / `DOMAINS`）  
门禁契约：`gate_contracts.py`；评测：`gates/evaluate.py`  
主题：`themes.py`；档案字段：`profile_fields.py`  
Schema：`domain_schema.py`（组装/accept）；模板：`schema_templates.py`

---

## 全厂不变式：管理页 + 总管 / 子管理 / 业务员工

**任意领域**（含未来商城 / ERP / 预约）必须满足；缺一不可标 `full` / 出 ZIP。

| 槽位 | 谁可见 | 要求 | 示例 |
|------|--------|------|------|
| **领域主数据** | 仅总管 | ≥1 个 admin 菜单 + 真实主表 + CRUD Admin | 宿舍：楼栋/房间/类型；图书：图书/分类；商城：商品/分类 |
| **用户管理 / 任命** | 仅总管 | `users` + `requireSuperAdmin`；任命写入 `staff_post`+`staff_kind` | 学生 + 岗位（clerk/worker） |
| **公告管理** | 仅总管 | `content` + NoticesAdmin + `requireSuperAdmin` | 全域壳，文案随 schema |
| **留言管理** | 仅总管 | `guestbook` + GuestbookAdmin + `requireSuperAdmin` | 默认交易壳；开题写留言可扫入其它域 |
| **业务流（办理）** | 总管+子管理(clerk) | AdminLayout，菜单按 clerk packs 裁剪 | 报修受理、订单办理、预约办理 |
| **现场作业** | 业务员工(worker) | WorkLayout `/staff/*`，页面按 worker packs | 维修、骑手配送、客房服务 |

岗位表：`backend/app/bake/staff_posts.py`（clerk / worker 均按域可选；无岗位 = 仅门户+总管；无 worker 则隐藏员工端入口）。

**禁止**：用「用户+公告」顶替领域主数据；挂无表无路由的假菜单；bake 丢掉 `superAdmin` 门禁；子管理/员工互相任命。

| 角色 | 能做 | 不能做 |
|------|------|--------|
| 总管 `super_admin=1` | 主数据、用户、公告；也可看业务流 | — |
| 子管 `role=admin` 且非总管 | 该域业务流（工作台/受理/记录等） | 主数据写、用户管理、公告写 |

菜单 key 约定：主数据可用 `archive` / `category` / `lookup_site` / `lookup_type`；均标 `superOnly: true`。

---

## 新对话开场（当前主线）

```
继续 graduate_factory_v3。先读 HANDOFF.md。
主线：Path B 三条交叉已可 full；薄域冒烟或 LLM 填 schema。
超壳 / 三合一 / 智慧校园必须 reject；硕博与真实业务全流程不接。
不要新开厚 DOM 包。领域清单以 HANDOFF「90% 覆盖」+「Path B」为准。
```

## 新对话开场（某个薄领域）

```
继续 graduate_factory_v3。先读 HANDOFF.md。
目标：薄领域 DOM-___（关键词：___）冒烟或文案/SQL 微调。
能力组合：___；仅 catalog + schema + SQL 种子 + 皮肤。
禁止内存 Store、禁止排除 DataSource、LLM 只填 schema。
```
