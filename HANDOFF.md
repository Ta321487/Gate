# 毕设港 · 交接（能力运行时 + 新领域）

工作区：`d:\graduate_factory_v3`  
**禁止**参考 / 迁移 `d:\graduate_factory`、`d:\graduate_factory_v2`。

---

## 先做什么（顺序）

1. **能力运行时（基线）** ← 当前主线：共用 JDBC + 通用 API，从 LIBRARY 抽取  
2. **薄领域**：catalog + schema + SQL 种子 + 皮肤；尽量不写专用 Store  
3. **LLM**：只填 schema JSON，不生成业务 Java/Vue  

接 LLM 后「代码无误」靠的是运行时固定，不是 LLM 写码。

---

## 能力积木（`capabilities.py`）

| 能力 | 状态 | 含义 | 解锁的典型题 |
|------|------|------|----------------|
| `org_users` | ✅ | 角色用户、资料、重置密码 | 全部 |
| `content` | ✅ | 公告 | 全部 |
| `archive` | ✅ | 分类 + 业务对象 CRUD / 检索 | 图书、设备、商品、菜品、片单… |
| `ticket_flow` | ✅ | 提交→审/受理→完结 | 借阅、报修、报名… |
| `quota` | ✅ | 库存/名额占用与归还 | 借阅、选课、设备… |
| `deadline` | ✅ | 到期、逾期、催办、可选费用 | 借阅、租赁… |
| `slot_reserve` | ❌ planned | 时段/资源预约 | 挂号、车位、会议室、美发 |
| `order_lines` | ❌ planned | 多明细行订单（可不含真支付） | 商城、点餐、客房 |

未实现的能力 → 依赖它的领域 `accept=reject`，这是预期。

---

## 90% 毕设覆盖：领域清单（薄配置，不是厚代码包）

按**能力组合**分组；同组共享同一套运行时，差别主要在 schema 文案/种子/菜单。

### A. 借用 / 占用流（能力齐，可先薄落地）

| 领域 ID | 覆盖题目关键词 | 能力组合 |
|---------|----------------|----------|
| **DOM-LIBRARY** | 图书、图书馆、借阅、读者 | archive + ticket_flow + quota + deadline + content + org_users |
| **DOM-EQUIP** | 设备借用、器材、实验室物资 | 同上 |
| **DOM-ASSET** | 固定资产领用、耗材申领 | archive + ticket_flow + quota + content + org_users（可无 deadline） |

### B. 报修 / 工单流（能力齐）

| 领域 ID | 覆盖题目关键词 | 能力组合 |
|---------|----------------|----------|
| **DOM-DORM** | 宿舍报修、水电、寝室 | ticket_flow + content + org_users（±archive） |
| **DOM-PROPERTY** | 物业报修、社区维修 | 同上 |
| **DOM-IT** | 校园网报修、IT 运维工单 | 同上 |

### C. 报名 / 申请流（能力齐）

| 领域 ID | 覆盖题目关键词 | 能力组合 |
|---------|----------------|----------|
| **DOM-ACTIVITY** | 社团活动、志愿活动报名 | archive + ticket_flow + quota + content + org_users |
| **DOM-LOST** | 失物招领 | archive + ticket_flow + content + org_users |
| **DOM-COURSE** | 选课、公选课（名额） | archive + ticket_flow + quota + content + org_users |

### D. 交易 / 点餐（缺 `order_lines` → 先 reject，能力补齐后再开）

| 领域 ID | 覆盖题目关键词 | 能力组合 |
|---------|----------------|----------|
| **DOM-SHOP** | 商城、二手、购物车、订单 | archive + order_lines + quota + content + org_users |
| **DOM-FOOD** | 食堂、点餐、外卖档口 | 同上 |

### E. 预约流（缺 `slot_reserve` → 先 reject）

| 领域 ID | 覆盖题目关键词 | 能力组合 |
|---------|----------------|----------|
| **DOM-HOSPITAL** | 挂号、门诊预约 | archive + slot_reserve + content + org_users |
| **DOM-PARKING** | 车位预约 | slot_reserve + ticket_flow + deadline + org_users |
| **DOM-MEETING** | 会议室预约 | slot_reserve + ticket_flow + org_users |
| **DOM-SALON** | 美发/美容/场地预约 | slot_reserve + archive + org_users |
| **DOM-HOTEL** | 宾馆客房（可加 order_lines） | slot_reserve + order_lines + archive + org_users |

### F. 兜底

| 领域 ID | 覆盖 | 能力 |
|---------|------|------|
| **DOM-GENERIC** | 对不上上面的「信息管理 / CRUD」题 | archive + content + org_users |

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

**覆盖率怎么理解**：A+B+C+F+G +（补齐 order_lines / slot_reserve 后的 D+E）≈ 常见 Web 管理类毕设主体；不是 100% 开题都能 full。

---

## 开题禁写清单（写了就要实现 · 当前壳做不到）

**原则**：开题一旦写进「拟实现功能」，答辩要演示。工厂只交付固定能力运行时；换名词可以，**不要写壳外规则**。  
改开题时：能演示的才写进「主要功能」；做不到的放「非本期 / 展望」，且避免触发 `OUT_OF_SCOPE_SIGNALS` 关键词（否则 accept 最多 degraded）。

### 可以写（壳内，能演示）

| 说法 | 实际对应 |
|------|----------|
| 注册登录、验证码、个人资料、头像 | baseline + org_users |
| 分类浏览 / 条件检索 / 详情 | archive |
| 申请 / 报名 / 认领 / 选课 / 借阅 / 报修 → 审核通过或驳回 | ticket_flow |
| 库存或名额占用与归还/取消回补 | quota（有该能力的域） |
| 应还日期、逾期提醒、罚款登记 | deadline（图书/设备等） |
| 公告发布与查阅 | content |
| 总管主数据 + 用户 + 公告；子管只审业务单 | 全厂不变式 |
| 猜你喜欢（按分类偏好/热度/上新） | recommend（非协同过滤） |
| 富文本正文 / 回复排版（论坛博客） | RichTextEditor，非协同编辑 |
| 楼中楼（主帖下多楼 + @一层引用） | 多回复单据，非无限树 |

### 隐性规则 · 听起来像「加一点业务」· 当前没有（开题勿写进本期）

| 隐性需求 | 常见开题措辞 | 为何踩坑 |
|----------|--------------|----------|
| **时间冲突检测** | 选课冲突、活动时段冲突、会议室撞档、借阅与课程冲突 | 无日历/时段引擎；`slot_reserve` 未实现 |
| **课表/日历视图** | 个人课表、周历、拖拽排期 | 仅列表+单据，无日历组件与冲突算法 |
| **多级审批** | 辅导员→院系→教务；班长初审再终审 | 仅一层 pending→approve/reject |
| **会签 / 或签 / 转交** | 多人会签、任意一人通过、工单转派链 | 无审批流引擎；最多 assignee 字段 |
| **同一人多规则限额** | 每学期最多选 N 门且跨类限制、借阅类型配额矩阵 | 仅全局 `MAX_ACTIVE` / 简单 stock，无规则引擎 |
| **业务互斥组合** | 两门课不能同选、互斥活动、套装只能借其一 | 无互斥表与校验 |
| **自动过期 / 定时任务业务** | 报名截止自动关、超时未审自动驳回、定时发布 | 无调度器驱动业务状态（逾期催还除外有限） |
| **消息通知闭环** | 站内信、邮件、短信、微信模板消息推审核结果 | 仅公告；无站内信/短信通道 |
| **评价 / 评分 / 问卷** | 活动评价、课程评分、报修满意度 | 无评价实体与统计 |
| **收藏夹 + 另一套单据** | 选课系统还要「收藏课程」另表 | 一域通常一套 ticket；论坛是回复不是收藏 |
| **用户自由发主数据** | 学生自由发活动/发帖/登记失物免审 | archive 写权限在总管；用户侧是开单 |
| **附件强业务** | 认领必须上传证明、报修强制照片才能提交 | 表可有 attach 种子；基线申请表单未强制附件流 |
| **标签筛选主路径** | 按多标签组合检索为硬需求 | 论坛标签偏 ER/种子；检索仍以分类+关键词为主 |
| **统计报表 / 导出** | 报名统计图、Excel 导出、打印条码 | 工作台概览有限；无报表引擎 |
| **软删除 / 回收站 / 操作审计全文** | 误删恢复、全量操作日志审计 | 无统一回收站；日志表不完整覆盖 UI |
| **全文检索 / 分词** | Elasticsearch、拼音搜、同义词 | 仅 SQL LIKE 级检索 |
| **工作流可视化** | BPMN、可配置节点 | 状态机写死在 TicketStore |
| **库存多仓 / 批次 / 序列号** | 多仓库调拨、批次保质期 | 单 stock 计数 |
| **购物车 / 多明细行订单** | 加购多商品一行订单 | 缺 `order_lines` → 域 reject |
| **时段预约占坑** | 挂号分时、车位时段、会议室整点 | 缺 `slot_reserve` → 域 reject |
| **真支付** | 微信支付、支付宝、退款对账 | OOS 信号 + 无支付能力 |
| **原生 / 小程序交付** | 安卓 App、微信小程序为交付物 | OOS；主交付是 Web ZIP |
| **生物识别 / 硬件** | 人脸签到、门禁、物联网传感器 | OOS |
| **深度推荐 / 训练** | 协同过滤、深度学习推荐、大模型问答 | OOS；仅有轻量猜你喜欢 |
| **媒体重能力** | 直播弹幕、转码 CDN、歌词同步滚动 | OOS / 域 out_of_mvp |
| **UGC 社交** | 实时私信、无限楼中楼树、@通知系统 | 论坛仅薄回复 |

### 按组额外小心

| 组 | 开题易多写 | 建议改成 |
|----|------------|----------|
| A 借用 | 预约时段领用、RFID 盘点、损坏赔付流程引擎 | 申请→审核→归还→逾期催还 |
| B 报修 | 派工到人到班组、备件库存、服务级别 SLA 计时 | 提交→受理→完结 + 楼栋房间类型 |
| C 活动/失物/选课 | **时间冲突**、签到二维码、图像识物、智能排课 | 浏览→报名/认领/选课→审核→占名额 |
| G 论坛/博客 | 用户自由发帖、私信、协同编辑、SEO | 总管维护主帖/文章；用户回复或收藏 |
| D/E | 整题商城/挂号 | 能力未齐前不要开题承诺本期交付 |

### 开题措辞模板（安全）

- 「主要功能」只写上表「可以写」行。  
- 「非本期」写：时间冲突检测、多级审批、消息推送、统计导出、人脸/支付/小程序等，**尽量换说法避免命中 OOS 词**（例如写「现场核验设备对接」而非「人脸」；写「个性化深度推荐」仍可能踩「推荐」类预期——直接写「不纳入智能推荐算法」并接受说明书说明即可）。  
- 题目换名词保留域关键词：活动报名 / 失物招领 / 选课 / 借阅 / 报修……

---

## 硬约束：库表数量 6~12

- 常量：`backend/app/bake/engine.py` → `TABLE_COUNT_MIN/MAX`
- DDL/种子模板：`backend/app/bake/sql/<DOMAIN>.sql`（`domain_sql` 加载；缺省 `DOM-GENERIC.sql`）
- bake 写 `schema.sql` 前 `assert_table_budget`；门禁 `p3t` 不过则禁 ZIP
- **现状样板**：GENERIC 6 · 媒资/设备/博客/组 C 7 · 图书/报修壳 8 · **论坛 12（顶格参考）**
- 论坛 12 表：`sys_user` / `category` / `board_moderator` / `post` / `post_attach` / `tag` / `post_tag` / `reply` / `reply_log` / `reply_attach` / `sys_notice` / `sys_config`
- 报修薄壳 8 张：楼栋/房间/类型/单据/进度/附件 + 用户/公告

## 学生端持久化（已完成）

- `UserStore` / `NoticeStore` / `LibraryStore` → MySQL + JdbcTemplate  
- 工厂 `student_db.ensure_student_schema` + `GF_STUDENT_MYSQL_*`  
- 种子在 `schema.sql` 幂等；重启不 Cle 业务数据  

---

## 能力运行时抽取进度

- [x] 基线 `ArchiveStore` / `TicketStore`（archive + standalone 工单模式）
- [x] LIBRARY 薄封装；通用 `/api/tickets` + 报修壳前端
- [x] **accept**：能力齐且落在基线积木内 → `full`（不再强制 DOM overlay）
- [x] 薄领域可跑：**DOM-DORM / PROPERTY / IT**（共用 `gate_standalone_ticket` 门禁 + runtime + SQL）
- [x] 组 A 组合壳：**DOM-EQUIP**（`gate_archive_ticket` + Archive API/FE + `DOM-EQUIP.sql`；与 LIBRARY 同能力，无厚包）
- [x] 组 G：**DOM-MEDIA / DOM-MUSIC**（`gate_archive_ticket(with_deadline=False)` + 片库/曲库 SQL/皮肤；收藏单据、播放外链）
- [x] 组 G：**DOM-FORUM / DOM-BLOG**（同壳；主帖/文章主数据；论坛回复单据 + 博客收藏单据；无播放字段；可选门户轮播）
- [x] 门户轮播：与登录图分套（`portal_banners.py`）；LIBRARY / EQUIP / FORUM / BLOG / ACTIVITY / COURSE 开启；基线 `PortalCarousel` + 门户壳强化
- [x] 组 C：**DOM-ACTIVITY / LOST / COURSE**（`gate_archive_ticket(with_deadline=False)`；活动/失物/选课 SQL；报名/认领/选课单据；ACTIVITY/COURSE 门户轮播）
- [ ] 实现 `order_lines`、`slot_reserve` 后打开 D/E 组

### 宿舍验证账号（bake 后）

- 宿管（总管）`admin` / `admin123`：楼栋房间 + 报修类型 + 学生管理 + 公告 + 报修
- 楼管（子管）`subadmin` / `sub123`：仅报修受理/记录/工作台
- 学生 `student` / `student123`

样板（过渡厚包）：`skeletons/domains/DOM-LIBRARY/`  
Catalog：`catalog.py`（匹配 / build_spec）  
目录：`domains.py`（`ARCHETYPES` / `DOMAIN_CAPABILITIES` / `DOMAINS`）  
门禁契约：`gate_contracts.py`（与 `gates/` 评测包分开）  
主题：`themes.py`；档案字段：`profile_fields.py`  
Schema：`domain_schema.py`（组装/accept）；模板：`schema_templates.py`

---

## 全厂不变式：管理页 + 总管/子管

**任意领域**（含未来商城 / ERP / 预约）必须满足；缺一不可标 `full` / 出 ZIP。

| 槽位 | 谁可见 | 要求 | 示例 |
|------|--------|------|------|
| **领域主数据** | 仅总管 | ≥1 个 admin 菜单 + 真实主表 + CRUD Admin | 宿舍：楼栋/房间/类型；图书：图书/分类；商城：商品/分类；ERP：物料/仓库 |
| **用户管理** | 仅总管 | `users` + UsersAdmin + `requireSuperAdmin` | 学生 / 读者 / 会员 / 员工 |
| **公告管理** | 仅总管 | `content` + NoticesAdmin + `requireSuperAdmin` | 全域壳，文案随 schema |
| **业务流** | 总管+子管 | 仅 `requireAdmin` | 报修受理、借阅审核、订单发货、出入库 |

**禁止**：用「用户+公告」顶替领域主数据；挂无表无路由的假菜单；bake 丢掉 `superAdmin` 门禁。

| 角色 | 能做 | 不能做 |
|------|------|--------|
| 总管 `super_admin=1` | 主数据、用户、公告；也可看业务流 | — |
| 子管 `role=admin` 且非总管 | 该域业务流（工作台/受理/记录等） | 主数据写、用户管理、公告写 |

菜单 key 约定：主数据可用 `archive` / `category` / `lookup_site` / `lookup_type`；均标 `superOnly: true`。

---

## 新对话开场（抽运行时）

```
继续 graduate_factory_v3。先读 HANDOFF.md。
主线：补齐能力运行时（ArchiveStore/TicketStore），LIBRARY 改薄封装。
不要新开厚 DOM 包。领域清单以 HANDOFF「90% 覆盖」为准。
```

## 新对话开场（某个薄领域）

```
继续 graduate_factory_v3。先读 HANDOFF.md。
目标：薄领域 DOM-___（关键词：___）。
能力组合：___；仅 catalog + schema + SQL 种子 + 皮肤。
禁止内存 Store、禁止排除 DataSource、LLM 只填 schema。
```
