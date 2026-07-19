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
| `time_conflict` | ✅ | 起止时段相交检测 + 报名截止 | 选课、活动报名… |
| `slot_reserve` | ✅ | 资源时段库存占坑与取消 | 挂号、车位、会议室、美发、客房 |
| `order_lines` | ✅ | 购物车 + 多明细订单（无真支付） | 商城、点餐、客房 |

依赖未实现能力 → `accept=reject`；上述两项已落地，D/E 可 full。

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

### D. 交易 / 点餐（`order_lines` 已开）

| 领域 ID | 覆盖题目关键词 | 能力组合 |
|---------|----------------|----------|
| **DOM-SHOP** | 商城、二手、购物车、订单 | archive + order_lines + quota + content + org_users |
| **DOM-FOOD** | 食堂、点餐、外卖档口 | 同上 |

### E. 预约流（`slot_reserve` 已开）

| 领域 ID | 覆盖题目关键词 | 能力组合 |
|---------|----------------|----------|
| **DOM-HOSPITAL** | 挂号、门诊预约 | archive + slot_reserve + content + org_users |
| **DOM-PARKING** | 车位预约 | archive + slot_reserve + content + org_users |
| **DOM-MEETING** | 会议室预约 | archive + slot_reserve + content + org_users |
| **DOM-SALON** | 美发/美容/场地预约 | archive + slot_reserve + content + org_users |
| **DOM-HOTEL** | 宾馆客房 | archive + slot_reserve + order_lines + content + org_users |

### F. 兜底

| 领域 ID | 覆盖 | 能力 |
|---------|------|------|
| **DOM-GENERIC** | 对不上具体行业关键词时的兜底域 | 按 **ARCH-*** 绑壳：CRUD / FLOW / TRADE / RESERVE（见下） |

未命中具体 `DOM-*` 时 **禁止**误落 LIBRARY：`score_catalog(..., fallback="DOM-GENERIC")`。  
GENERIC 再按原型选 SQL/runtime/gate（`archetype_shells.py`）：

| ARCH | 能力 | bake SQL |
|------|------|----------|
| ARCH-CRUD | archive + content + org_users | `DOM-GENERIC.sql` |
| ARCH-FLOW / STOCK / CONTENT | + ticket_flow（±quota） | `DOM-GENERIC-FLOW.sql` |
| ARCH-TRADE | + order_lines | `DOM-GENERIC-TRADE.sql` |
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

**覆盖率怎么理解**：A+B+C+D+E+F+G ≈ 常见 Web 管理类毕设主体；不是 100% 开题都能 full（L3 仍 reject/degraded）。

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
| **时间冲突检测** | `time_conflict`：主数据 `start_at`/`end_at`；申请时与本人已占用时段做区间相交 |
| **报名/选课截止** | 主数据 `apply_deadline_at`；截止后不可再申请 |
| **我的日程/课表列表** | 我的单据展示 `startAt`/`endAt`（非拖拽排期） |
| **站内消息（审核结果）** | `sys_message` + 顶栏铃铛；审核通过/驳回写入申请人收件箱 |
| **管理端 CSV 导出** | 记录页按当前筛选下载（UTF-8 BOM） |
| **工作台简易统计** | `/api/admin/dashboard`：待审/处理中/已完成/用户数（档案域附加库存等） |
| 公告 | content |
| 总管主数据+用户+公告；子管审单 | 全厂不变式 |
| 猜你喜欢（偏好/热度/上新） | recommend，非协同过滤 |
| 富文本正文/回复；论坛多楼 + @一层 | 基线编辑器 + 多单据 |

选课 / 活动等带时段的域默认打开冲突检测；图书借阅等无时段列则自动跳过（不报错）。

### L1 · 可加价亮点（纯软件 · 再抬一点难度）

| 增强项 | 开题常见说法 | 难度感 | 控范围 |
|--------|--------------|--------|--------|
| **二级审批** | 初审→终审 | ★★ | 多一档状态；不会签/BPMN |
| **互斥规则** | 两门课不能同选 | ★★ | 小表或互斥码 |
| **分类限额** | 每类最多选 N 门 | ★★ | 配置 + 计数 |
| **评分评价** | 满意度 1～5 分 | ★★ | 完结后短评 + 均分 |
| **强制附件** | 认领须上传证明 | ★ | 表单非空校验 |
| **周历视图** | 周视图看课表 | ★★ | 只读周格；不拖拽 |
| **软件签到码** | 活动口令签到 | ★★ | token/口令；不接人脸闸机 |
| **标签组合筛选** | 多标签过滤 | ★ | 接到列表 API |
| **软删除** | 下架可恢复 | ★ | `deleted_at` |

**报价建议**：L0 已含冲突检测与导出等，报价高于「纯 CRUD」；L1 每加 1～2 项作为亮点再上浮。

### L2 · 交易 / 占坑积木（已落地，D/E 组可接）

| 项 | 运行时 | 参考域 |
|----|--------|--------|
| 购物车 / 多明细行订单 | `order_lines`：`OrderStore` + `/api/cart` + `/api/orders`（无真支付） | SHOP / FOOD |
| 挂号分时、车位/会议室整点预约占坑 | `slot_reserve`：`SlotStore` 时段容量 `--`（≠ L0 本人已选时段相交） | MEETING / HOSPITAL / PARKING / SALON；HOTEL = 预约 + 订单 |

### L3 · 仍不接（超毕设纯 Web 舒适区 / OOS）

人脸/指纹门禁、物联网传感器、真微信支付支付宝、小程序/安卓为交付物、协同过滤与深度学习训练、直播弹幕与转码 CDN、区块链、Hadoop/Spark、BPMN 可配置工作流、多仓批次 ERP、实时私信与无限楼中楼树、富文本多人协同编辑。

命中 `OUT_OF_SCOPE_SIGNALS` → accept 最多 degraded；不要当作本期演示承诺。

### 开题怎么写（推荐）

1. **主要功能** = L0（含时间冲突等）+ 可选 1～2 个 L1 亮点；商城/点餐写购物车订单，预约类写时段占坑。  
2. **非本期** = L3（真支付、人脸等）。  
3. 换名词保留域关键词；冲突检测 vs 占坑一句分清：选课=本人已选相交；挂号=号源容量占坑。

---

## 硬约束：库表数量 6~13

- 常量：`backend/app/bake/engine.py` → `TABLE_COUNT_MIN/MAX`（含 L0 平台表 `sys_message`）
- DDL/种子模板：`backend/app/bake/sql/<DOMAIN>.sql`（`domain_sql` 加载；GENERIC 按 ARCH 选 `DOM-GENERIC*.sql`）
- bake 写 `schema.sql` 前 `assert_table_budget`；门禁 `p3t` 不过则禁 ZIP
- **现状样板**：GENERIC CRUD 6 / FLOW·RESERVE 7 / TRADE 8 · 多数薄域 8~9 · 图书/报修壳 9 · **论坛 13（顶格参考）**
- 论坛含：`sys_message` + 原 12 业务/平台表
- 报修薄壳：楼栋/房间/类型/单据/进度/附件 + 用户/公告/消息

## 学生端持久化（已完成）

- `UserStore` / `NoticeStore` / `MessageStore` / `LibraryStore` → MySQL + JdbcTemplate  
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
- [x] L0 **站内消息**（`MessageStore` / `sys_message` / 顶栏铃铛；审核结果通知）+ **薄域工作台**（`TicketDashboardController` 对非 LIBRARY 全开）
- [x] L2 **`order_lines` / `slot_reserve`**：组 D SHOP/FOOD + 组 E MEETING/HOSPITAL/PARKING/SALON/HOTEL（SQL + schema + 订单/预约壳）
- [x] **匹配兜底**：域零命中 → `DOM-GENERIC`（不再误落 LIBRARY）；GENERIC 按 ARCH-* 绑 FLOW/TRADE/RESERVE 壳（`archetype_shells.py`）

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
