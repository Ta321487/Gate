# UI 观感加厚批次（活表）

> **本文只负责**：工厂出包「一眼精美 / 不像模板后台」的**观感加厚**进度、全域台账、验收口径与真源落点。
> **不负责**：能力四件套（各组 `*_thicken` / 地图待补）；选型键目录与 ASCII（[`domain-group-ui-styles.md`](./domain-group-ui-styles.md) §2）；沉浸边角（[`immersion-corners.md`](./immersion-corners.md)）。
> **状态**：**收口** · 公共壳 + 九组观感 **首刀已齐**（含审批）；用户列表卡底口径已跨页统一；兜底吃公共壳。
> **硬闸**：键接满、测绿了，观感仍像模板站 —— **仍算未完成**（同选型册 §0.0）。
> **索引**：[README.md](./README.md) · 选型册 [`domain-group-ui-styles.md`](./domain-group-ui-styles.md) · 搁置 [`parked-work.md`](./parked-work.md) · 领域 [`domains.md`](./domains.md)。

---

## 0. 硬口径

| 规则 | 含义 |
|------|------|
| **修工厂** | 只改 `skeletons/baseline` + bake 注入；禁止只擦某一学生 ZIP |
| **对标商业站** | 摆法学公开页，改成毕设可演示版；不抄真支付 / IM / 无限滑 |
| **一轮一组** | 观感加厚按域组推进；公共壳单独一轮（全厂受益） |
| **接线 ≠ 好看** | `{组}_surface_style` / `shellColors` / `cardVoice` 已接线只算管道；本组须过 §0.0 截图闸 |
| **覆盖全域** | `DOMAIN_CAPABILITIES` 68 域均须进台账；组观感齐 = 组内全部 `DOM-*` 默认识别脸达标 |
| **菜单保全** | 换脸不删开题菜单；详情用 `/archive/item/:id`，禁止写死 `/goods/:id` |

### 0.1 两层交付

| 层 | 范围 | 验收 |
|----|------|------|
| **A 公共壳** | 顶栏 / 登录注册 / 管理端品牌条 / Element 主色盖死 | 任意域打开都不像默认 Admin |
| **B 组主表面** | 该组 `*_surface_style` + 首页（若有）+ 详情主路径 | 对标摆法可辨；同组多域靠软皮/短签/色分脸 |

### 0.2 真源落点

| 件 | 路径 |
|----|------|
| 门户壳 | `skeletons/baseline/frontend/src/layouts/PortalLayout.vue` |
| 管理端壳 | `AdminLayout.vue` + `styles/chrome.css`（`.workbench`） |
| 登录壳 | `components/AuthShell.vue` |
| 主色注入 | `main.js`（`shellColors` → `--portal-*` / `--el-color-primary*`） |
| 68 域脸表 | `backend/app/bake/shell_face.py` |
| 列表构图 CSS | `views/user/ArchiveBrowse.css`（`surface-*`；脚本 `ArchiveBrowse.setup.js`） |
| 商城首页 | `views/user/PortalHome.vue`（`portal_home_style=mall`） |
| 独立详情 | `views/user/ArchiveItemDetail.vue`（`/archive/item/:id`） |
| 路由挂载 | `router/index.js` → `withPortalHub` |
| 选型 / 对标 | [`domain-group-ui-styles.md`](./domain-group-ui-styles.md) §2 / §3 |

---

## 1. 组进度总表

| 组 id | 组名 | 选型接线 | 公共壳 A | 组观感 B | 主表面 | 下一刀 |
|-------|------|----------|----------|----------|--------|--------|
| （全厂） | 公共壳 | — | **首刀已齐** | — | PortalLayout / AuthShell / AdminLayout / main.js | 抽检回归 |
| borrow | 借用/占用 | 已接线 | 吃 A | **首刀已齐** | ArchiveBrowse bookshelf/stockrow/bedblocks/parcelshelf | 详情借阅文案再磨 |
| trade | 交易 | 已接线 | 吃 A | **首刀已齐** | PortalHome mall + shelfgrid + ArchiveItemDetail | menuboard/showtime **再磨已齐**；软皮短签继续 |
| reserve | 预约 | 已接线 | 吃 A | **首刀已齐** | SlotBook + slotstrip/roomstate/vehiclecard + 详情选时段 | 软皮短签再磨 |
| content | 内容 | 已接线 | 吃 A | **首刀已齐** | folio/coverwall/ledger/splitdesk + 阅读详情 | 软皮短签再磨 |
| apply | 报名/申请 | 已接线 | 吃 A | **首刀已齐** | eventposter/coursetable/noticeboard/tourcard + 详情报名 | 软皮短签再磨 |
| follow | 跟进 | 已接线 | 吃 A | **首刀已齐** | pipeline/dossier/listing（+LISTING price 价签） | 软皮短签再磨 |
| interact | 互动 | 已接线 | 吃 A | **首刀已齐** | profilegrid/mutualpick/triprow + 详情意向；EXAM/SURVEY/VOTE 专用页不动 | 软皮短签再磨 |
| ticket | 报修/工单 | 已接线 | 吃 A | **首刀已齐** | MyTickets ticketfeed/faultboard | 软皮短签再磨 |
| approve | 审批/填报 | 已接线 | 吃 A | **首刀已齐** | MyTickets/TicketsAdmin typelist/inboxsteps | 软皮短签再磨 |
| fallback | 兜底 | 无选型键 | 吃 A | **吃公共壳** | 导引 + 中性壳 | 随壳即可 |

建议下一轮：借用 **详情借阅文案再磨**；其余组软皮短签继续分批。

---

## 2. 已齐首刀（实现纪要）

### 2.1 公共壳 A（全 68 域吃到）

- 顶栏：实底品牌条、短链下划线选中、登录/注册实心按钮；去掉双光晕 SaaS 底
- 登录：与门户同主色面板；少模板光晕
- 管理端：侧栏品牌条用系统名 + 主色浅字；禁「管理后台」套话
- `shellColors`：盖 `--el-color-primary` 及 light/dark 阶，避免残留默认蓝

### 2.2 交易组 B

- `PortalHome` mall：轮播点、新品 + **热销**、累计销量、卡片观感；点进 `/archive/item/:id`
- `ArchiveBrowse` `shelfgrid`：货架卡加厚
- `ArchiveItemDetail`：独立详情（加购/收藏/评价）；不写死 `/goods`
- 覆盖域：`DOM-SHOP` / `DOM-FOOD` / `DOM-CINEMA`
- **再磨（2026-10-22）**：`menuboard` 菜单板行价 + 短签；`showtime` 排片左边条 + 余座主信号；列表 `short-tags` 芯片接线（catalog / 档口 / 排片）
- 护栏：`backend/tests/test_trade_look_polish.py`

### 2.3 借用组 B

- `bookshelf` 脊列 / `stockrow` 台账行 / `bedblocks` 空占色块 / `parcelshelf` 驿站格
- 有 `borrowSurfaceStyle` 时列表进独立详情；单据域详情「申请办理」→ `?openApply=1`
- 覆盖域：`DOM-LIBRARY` / `EQUIP` / `ASSET` / `PARCEL` / `BED`（`PROCURE` 默认可走 stockrow 隐喻，组属审批）

### 2.4 预约组 B（三档异脸，禁止套借用/货架模板）

- `slotstrip`：号源横条 + 圆头像 +「有号」徽标；`SlotBook` 时段芯片（时间主信号、余号 pill）
- `roomstate`：房态色块墙（可订绿/紧张琥珀/已满深灰）+ 顶条封面；`SlotBook` PMS 填色格
- `vehiclecard`：左大图右日价宽卡；`SlotBook` 左边强调条档期卡
- 有 `reserveSurfaceStyle` 时列表进 `/archive/item/:id`；详情主按钮「选择时段…」→ `/slots?itemId=`
- 覆盖域：`DOM-HOSPITAL` / `MEETING` / `SALON` / `INSTRUMENT` / `HOTEL` / `CARRENT` / `PARKING`

### 2.5 内容组 B（四档异脸，禁止套货架/库存/号源模板）

- `folio`：刊头流——头条大封 + 摘要，下文横条阅读卡
- `coverwall`：海报墙——2:3 封面格、题名极简（片库/曲库）
- `ledger`：资料清单——虚线台账行、右栏作者·阅读数
- `splitdesk`：双栏台——左目录高亮条、右 sticky 预览；宽屏不整卡跳详情
- 有 `contentSurfaceStyle`（非 splitdesk）时进 `/archive/item/:id`；详情「正文」阅读脸
- 覆盖域：`DOM-BLOG` / `FORUM` / `MEDIA` / `MUSIC` / `DOCLIB`

### 2.6 报名组 B（四档异脸，禁止套内容海报/房态/资料清单）

- `eventposter`：活动大海报 + 余位 pill（紧张琥珀 / 已满灰）
- `coursetable`：课表格网，冲突格红边；无封面
- `noticeboard`：启事便签——寻物琥珀 / 招领绿 / 线索靛
- `tourcard`：左边强调条行程横卡 + 亮点摘要 + 余位/价
- 有 `applySurfaceStyle` 时列表进 `/archive/item/:id`（`openApply=1` 仍走报名弹层）；详情「立即报名」
- 覆盖域：`DOM-ACTIVITY` / `COURSE` / `LOST` / `TOUR`

### 2.7 互动组 B（三档异脸；EXAM/SURVEY/VOTE 不进本轴）

- `profilegrid`：圆头像居中资料卡 + 简介；墨灰，禁止粉色配对壳
- `mutualpick`：双选志愿行 + 名额主信号（可叠配额条）
- `triprow`：行程行——时刻·路线·余座；已满降透明度
- 有 `interactSurfaceStyle` 时列表进 `/archive/item/:id`；详情「提交意向」
- 覆盖域：`DOM-DATING` / `MUTUAL-*` / `CARPOOL` / `TIMEBANK`

### 2.8 跟进组 B（三档异脸；看板/档案/价签）

- `pipeline`：阶段看板卡——4 列网格，左侧 4px 阶段色条（线索/意向/谈判/成交/搁置五色），无封面
- `dossier`：档案行——纵向清单，小封面、虚线分隔、hover 左色条；主信号为当前阶段
- `listing`：挂牌价签——左大图右宽卡，价签大数字；补 `priceYuan`（挂牌价）与 `priceUnit`（计价单位）字段（LISTING 专用，其它跟进域不挂）
- 数据层：`DOM-LISTING.sql` 加 `price DECIMAL(12,2)`、`price_unit VARCHAR(16)` 列 + 种子（整租/合租按「元/月」、二手出售按「元/套」）；三份 `ArchiveStore` 用 `hasItemColumn("price")`/`hasItemColumn("price_unit")` 守卫映射到 `priceYuan`/`priceUnit`，写入走 `patchOptNum`/`patchOptStr`
- 口径：单价单位是**行级**语义，主信号按 `priceUnit` 拼后缀（缺失只报金额），禁止前端按数值大小猜「万/月」；管理端下拉含元/月·套·㎡·间·天·辆·个·万元（选题不唯一）
- 有 `followSurfaceStyle` 时列表进 `/archive/item/:id`；详情主按钮 listing「预约带看」、其它「记录跟进」，附「跟进说明」
- 覆盖域：`DOM-CRM` / `EVENT` / `ATTEND` / `FUND` / `RECRUIT` / `GRADE` / `INTERN` / `LISTING`
- 护栏：`backend/tests/test_follow_look_thicken.py`

### 2.9 报修组 B（两档异脸；进度流 / 故障看板）

- `ticketfeed`：我的工单进度流——左边轨时间轴节点 + 卡左边色条，阶段色走 `ticketTone` → `data-ticket-tone` / `--repair-tone`（禁死色表）
- `faultboard`：分类故障看板——顶栏「待派 / 处理中 / 超时」计数；三列工单砖；分类短签 `fault-cat`；顶边 tone
- 覆盖域：`DOM-DORM` / `DOM-PROPERTY` / `DOM-IT`（非报修域无 surface）
- 护栏：`backend/tests/test_repair_look_thicken.py`

### 2.10 审批组 B（两档异脸；事项清单 / 待审步骤）

- `typelist`：事项类型清单行卡——左色条 + `matter-type` 短签；管理台表头跟 portal 浅底
- `inboxsteps`：待审步骤脸——`--approve-tone` 左边条（禁死色 ●○○）；管理台顶栏「待我审 / 待初审 / 待复审 / 待终审」
- 覆盖域：23 个审批域（见 `APPROVE_SURFACE_DOMAINS`）；非审批域无 surface
- 护栏：`backend/tests/test_approve_look_thicken.py`

### 2.11 跨页卡底口径（用户列表统一）

- 标杆口径：`ArchiveBrowse` 卡底 `card-foot`（纵向列）> `card-meta`（状态条）+ `card-acts`（操作条）
- 铺开五页：`MyOrders` / `MyReservations` / `MyTickets` / `PeerTickets` / `MyFavorites`
- 状态标签与操作按钮禁止挤在同一 `flex-wrap` 行；五页删本地 `.row` / `.acts`
- 通用规则落全局 `styles/cardVoice.css`（`.card-foot` / `.card-meta` / `.card-acts`），各页不再自造
- 状态色点单源 `utils/statusTone.js`：`reserveTone` 补入；`MyReservations` / `PeerTickets` 接上 `StatusChip`
- 护栏：`backend/tests/test_portal_shell_nav.py`（钉 `card-foot/card-acts`、禁 `class="row"/"acts"`）

---

## 3. 全域台账（68）

域集合真源：`backend/app/bake/domains.py` → `DOMAIN_GROUPS` / `DOMAIN_CAPABILITIES`（与下表行数对账 = 68）。

| 域 | 组 id | 组名 | 默认 surface | card_voice | 壳 brand | 检索占位 | 公共壳 A | 组观感 B |
|----|-------|------|--------------|------------|----------|----------|----------|----------|
| `DOM-ASSET` | borrow | 借用/占用 | `stockrow` | catalog | `#335064` | 物资名称 | 全厂已齐 | 首刀已齐 |
| `DOM-BED` | borrow | 借用/占用 | `bedblocks` | board | `#3D4F5C` | 楼栋 / 床位 | 全厂已齐 | 首刀已齐 |
| `DOM-EQUIP` | borrow | 借用/占用 | `stockrow` | catalog | `#2A3F55` | 器材名称 | 全厂已齐 | 首刀已齐 |
| `DOM-LIBRARY` | borrow | 借用/占用 | `bookshelf` | catalog | `#2C4A6E` | 书名 / 作者 | 全厂已齐 | 首刀已齐 |
| `DOM-PARCEL` | borrow | 借用/占用 | `parcelshelf` | board | `#3A4A58` | 取件码 / 姓名 | 全厂已齐 | 首刀已齐 |
| `DOM-ATTEND` | follow | 跟进 | `dossier` | board | `#2A3848` | 假条 / 事由 | 全厂已齐 | 首刀已齐 |
| `DOM-CRM` | follow | 跟进 | `pipeline` | board | `#1E4A45` | 客户名称 | 全厂已齐 | 首刀已齐 |
| `DOM-EVENT` | follow | 跟进 | `dossier` | board | `#3A4550` | 事件关键词 | 全厂已齐 | 首刀已齐 |
| `DOM-FUND` | follow | 跟进 | `dossier` | catalog | `#2A3040` | 资助项目 | 全厂已齐 | 首刀已齐 |
| `DOM-GRADE` | follow | 跟进 | `dossier` | catalog | `#2A3440` | 课程名称 | 全厂已齐 | 首刀已齐 |
| `DOM-INTERN` | follow | 跟进 | `dossier` | catalog | `#2A4850` | 岗位 / 周报 | 全厂已齐 | 首刀已齐 |
| `DOM-LISTING` | follow | 跟进 | `listing` | catalog | `#3A4A3E` | 房源关键词 | 全厂已齐 | 首刀已齐（含 price） |
| `DOM-RECRUIT` | follow | 跟进 | `dossier` | catalog | `#2A4858` | 岗位 / 公司 | 全厂已齐 | 首刀已齐 |
| `DOM-DORM` | ticket | 报修/工单 | `ticketfeed` | board | `#1A5C62` | 工单 / 地点 | 全厂已齐 | 首刀已齐 |
| `DOM-IT` | ticket | 报修/工单 | `ticketfeed` | board | `#1A4A62` | 工单 / 故障 | 全厂已齐 | 首刀已齐 |
| `DOM-PROPERTY` | ticket | 报修/工单 | `ticketfeed` | board | `#1A5C62` | 工单 / 房屋 | 全厂已齐 | 首刀已齐 |
| `DOM-ACTIVITY` | apply | 报名/申请 | `eventposter` | story | `#2A4A55` | 活动名称 | 全厂已齐 | 首刀已齐 |
| `DOM-COURSE` | apply | 报名/申请 | `coursetable` | catalog | `#2A4558` | 课程名称 | 全厂已齐 | 首刀已齐 |
| `DOM-LOST` | apply | 报名/申请 | `noticeboard` | story | `#4A4A3A` | 启事关键词 | 全厂已齐 | 首刀已齐 |
| `DOM-TOUR` | apply | 报名/申请 | `tourcard` | story | `#3A4A5A` | 线路名称 | 全厂已齐 | 首刀已齐 |
| `DOM-ACAD` | approve | 审批/填报 | `typelist` | catalog | `#243044` | 学籍事项 | 全厂已齐 | 首刀已齐 |
| `DOM-AWARD` | approve | 审批/填报 | `typelist` | catalog | `#243848` | 获奖类型 | 全厂已齐 | 首刀已齐 |
| `DOM-CARPASS` | approve | 审批/填报 | `typelist` | board | `#2A3448` | 车牌号 | 全厂已齐 | 首刀已齐 |
| `DOM-CERT` | approve | 审批/填报 | `typelist` | catalog | `#243044` | 证明类型 | 全厂已齐 | 首刀已齐 |
| `DOM-CHECKIN` | approve | 审批/填报 | `typelist` | board | `#2A3A48` | 寝室 / 归寝 | 全厂已齐 | 首刀已齐 |
| `DOM-CLUB` | approve | 审批/填报 | `typelist` | catalog | `#243044` | 社团名称 | 全厂已齐 | 首刀已齐 |
| `DOM-CONTRACT` | approve | 审批/填报 | `typelist` | catalog | `#2A3040` | 合同名称 | 全厂已齐 | 首刀已齐 |
| `DOM-CREDIT` | approve | 审批/填报 | `typelist` | catalog | `#243848` | 认定项目 | 全厂已齐 | 首刀已齐 |
| `DOM-ETHIC` | approve | 审批/填报 | `typelist` | catalog | `#2A3040` | 审查事项 | 全厂已齐 | 首刀已齐 |
| `DOM-EVAL` | approve | 审批/填报 | `typelist` | story | `#2A3844` | 评教课程 | 全厂已齐 | 首刀已齐 |
| `DOM-EXPENSE` | approve | 审批/填报 | `typelist` | board | `#2A3040` | 报销单号 / 事由 | 全厂已齐 | 首刀已齐 |
| `DOM-FITOUT` | approve | 审批/填报 | `typelist` | board | `#243044` | 装修区域 | 全厂已齐 | 首刀已齐 |
| `DOM-FLEET` | approve | 审批/填报 | `typelist` | board | `#243044` | 用车申请 | 全厂已齐 | 首刀已齐 |
| `DOM-LABOR` | approve | 审批/填报 | `typelist` | catalog | `#243848` | 劳动项目 | 全厂已齐 | 首刀已齐 |
| `DOM-LABSAFE` | approve | 审批/填报 | `typelist` | catalog | `#1E3A48` | 实验室名称 | 全厂已齐 | 首刀已齐 |
| `DOM-MORAL` | approve | 审批/填报 | `typelist` | catalog | `#243848` | 综测指标 | 全厂已齐 | 首刀已齐 |
| `DOM-PARTY` | approve | 审批/填报 | `typelist` | catalog | `#243044` | 发展阶段 | 全厂已齐 | 首刀已齐 |
| `DOM-PROCURE` | approve | 审批/填报 | `stockrow` | catalog | `#2A3840` | 申购物资 | 全厂已齐 | 首刀已齐 |
| `DOM-PROJ` | approve | 审批/填报 | `typelist` | catalog | `#2A3040` | 项目名称 | 全厂已齐 | 首刀已齐 |
| `DOM-PROMO` | approve | 审批/填报 | `typelist` | board | `#243044` | 宣传事项 | 全厂已齐 | 首刀已齐 |
| `DOM-SEAL` | approve | 审批/填报 | `typelist` | catalog | `#243044` | 用章事项 | 全厂已齐 | 首刀已齐 |
| `DOM-TRIP` | approve | 审批/填报 | `typelist` | board | `#243044` | 出差事项 | 全厂已齐 | 首刀已齐 |
| `DOM-VISITOR` | approve | 审批/填报 | `typelist` | board | `#2A3448` | 访客姓名 | 全厂已齐 | 首刀已齐 |
| `DOM-CINEMA` | trade | 交易 | `showtime` | board | `#2C2A33` | 影片 / 场次 | 全厂已齐 | 首刀已齐 |
| `DOM-FOOD` | trade | 交易 | `menuboard` | story | `#8C4A32` | 菜名 / 档口 | 全厂已齐 | 首刀已齐 |
| `DOM-SHOP` | trade | 交易 | `shelfgrid` | catalog | `#2A3038` | 商品名称 | 全厂已齐 | 首刀已齐 |
| `DOM-CARRENT` | reserve | 预约 | `vehiclecard` | catalog | `#2A3540` | 车型 | 全厂已齐 | 首刀已齐 |
| `DOM-HOSPITAL` | reserve | 预约 | `slotstrip` | board | `#1A5A66` | 科室 / 医生 | 全厂已齐 | 首刀已齐 |
| `DOM-HOTEL` | reserve | 预约 | `roomstate` | board | `#3A3A4A` | 房型 | 全厂已齐 | 首刀已齐 |
| `DOM-INSTRUMENT` | reserve | 预约 | `slotstrip` | catalog | `#2C4558` | 仪器名称 | 全厂已齐 | 首刀已齐 |
| `DOM-MEETING` | reserve | 预约 | `slotstrip` | board | `#1A4A5A` | 场地名称 | 全厂已齐 | 首刀已齐 |
| `DOM-PARKING` | reserve | 预约 | `vehiclecard` | board | `#2A3A4A` | 车位 | 全厂已齐 | 首刀已齐 |
| `DOM-SALON` | reserve | 预约 | `slotstrip` | story | `#5A3A4A` | 服务项目 | 全厂已齐 | 首刀已齐 |
| `DOM-BLOG` | content | 内容/媒资/社区 | `folio` | story | `#3D4A3A` | 文章标题 | 全厂已齐 | 首刀已齐 |
| `DOM-DOCLIB` | content | 内容/媒资/社区 | `ledger` | catalog | `#3A4038` | 资料名称 | 全厂已齐 | 首刀已齐 |
| `DOM-FORUM` | content | 内容/媒资/社区 | `folio` | story | `#3A4240` | 帖子标题 | 全厂已齐 | 首刀已齐 |
| `DOM-MEDIA` | content | 内容/媒资/社区 | `coverwall` | story | `#2A2A38` | 片名 | 全厂已齐 | 首刀已齐 |
| `DOM-MUSIC` | content | 内容/媒资/社区 | `coverwall` | story | `#2A3040` | 歌名 / 歌手 | 全厂已齐 | 首刀已齐 |
| `DOM-CARPOOL` | interact | 互动/匹配 | `triprow` | board | `#2A3A48` | 行程 / 地点 | 全厂已齐 | 首刀已齐 |
| `DOM-DATING` | interact | 互动/匹配 | `profilegrid` | story | `#3E4454` | 资料关键词 | 全厂已齐 | 首刀已齐 |
| `DOM-EXAM` | interact | 互动/匹配 | `—` | catalog | `#2A3040` | 试卷 / 题目 | 全厂已齐 | 首刀已齐 |
| `DOM-MUTUAL-TEAM` | interact | 互动/匹配 | `mutualpick` | catalog | `#3A4050` | 组队关键词 | 全厂已齐 | 首刀已齐 |
| `DOM-MUTUAL-TOPIC` | interact | 互动/匹配 | `mutualpick` | catalog | `#3A4050` | 选题关键词 | 全厂已齐 | 首刀已齐 |
| `DOM-MUTUAL-TUTOR` | interact | 互动/匹配 | `mutualpick` | catalog | `#3A4050` | 导师 / 方向 | 全厂已齐 | 首刀已齐 |
| `DOM-SURVEY` | interact | 互动/匹配 | `—` | catalog | `#2A3840` | 问卷标题 | 全厂已齐 | 首刀已齐 |
| `DOM-TIMEBANK` | interact | 互动/匹配 | `triprow` | board | `#2F4A42` | 服务事项 | 全厂已齐 | 首刀已齐 |
| `DOM-VOTE` | interact | 互动/匹配 | `—` | story | `#3A3848` | 候选人 / 选项 | 全厂已齐 | 首刀已齐 |
| `DOM-GENERIC` | fallback | 兜底 | `—` | catalog | `#2A3540` | 关键词 | 全厂已齐 | 吃公共壳 |

**行数**：68（须 = `len(DOMAIN_CAPABILITIES)` = 68）。

---

## 4. 验收（每组收口前）

1. 同组至少两域 bake 预览并排：去掉系统名仍可分清业务脸
2. 无 Element 默认蓝主按钮；顶栏不像后台菜单条
3. 列表主路径：交易/借用已进独立详情；其它组收口时同样禁止「只开抽屉交差」
4. 菜单 path 集合相对接线测不回退（既有 `test_*_surface_style`）
5. 学生可见文案无工厂腔

---

## 5. 修订

| 日期 | 说明 |
|------|------|
| 2026-10-21 | 立册：公共壳 / 交易 / 借用首刀入档；68 域全表；接线与观感分列 |
| 2026-10-21 | 跨页卡底口径：用户列表五页按 ArchiveBrowse `card-foot/card-meta/card-acts` 统一；通用规则入 `cardVoice.css`；护栏入 `test_portal_shell_nav.py` |
