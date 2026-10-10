# 域组 UI 表面选型册

> **本文只负责**：地图 §1.1～§1.10 **域组**上，共用列表/主路径「过通用、不像该业务」的问题判定，以及可选手选构图目录（含 ASCII）。  
> **不负责**：密功能四件套（各组 `*_thicken` / 地图待补）；换皮配色（theme）；沉浸边角（[`immersion-corners.md`](./immersion-corners.md)）；门户首页轴（已有 `portal_home_style`）。  
> **状态**：**选型册 · 未实现**（只定目录与 ASCII；bake/骨架未接线）。  
> **索引**：[README.md](./README.md) · 地图 [`opening-feature-delivery-map.md`](./opening-feature-delivery-map.md) · 领域 [`domains.md`](./domains.md)。

---

## 0. 硬口径

### 0.1 与加厚的分工

| 层 | 文档 / 模块 | 何时做 |
|----|-------------|--------|
| 能力四件套 | 地图 §1.x + `*_thicken` | 先做；本组待补清零或 batch 收口 |
| **本册：页内构图** | `{组}_surface_style` | **加厚后**再开该组独立实现 plan |
| 配色 / 质感 / 壳 / 字体 | `themes.py` 既有轴 | 正交，不绑本册 |
| 门户首页 | `portal_home_style`（cards / editorial / mall） | 正交；交易 mall 已有，不重做 |

### 0.2 菜单保全（毕设 + 论文）

换构图只改**页内排列与信息密度**，不删、不藏、不合并交付菜单与路由入口。

- 匹配挂上的用户端 / 管理端 / 员工端菜单须仍可从壳导航点进。
- 首页构图（editorial / mall 等）不得取消侧栏或顶栏里已有业务入口。
- 禁止为了「像内容站 / 商城」做成单页沉浸、管理功能只留深链。
- 能力未挂而不出的菜单仍按 cap / 扫词，不在此列。
- 答辩截图与论文插图依赖「菜单还在、点得到」。

### 0.3 选型键命名（统一，禁止混用 browse）

| 层 | 规则 | 例 |
|----|------|----|
| Spec / bake | `{组}_surface_style` | `content_surface_style` |
| 学生包交付 | `{组}SurfaceStyle` | `contentSurfaceStyle` |
| 组前缀 | 与 thicken 对齐 | borrow / follow / repair / apply / approve / trade / reserve / content / interact |
| 正交 | 门户只用 `portal_home_style`；配色 theme id 不进本轴 | 交易列表用 `trade_surface_style` |
| 兜底 §1.10 | **不设**选型键 | 仅交叉导引块 |

十组键：`borrow_surface_style` · `follow_surface_style` · `repair_surface_style` · `apply_surface_style` · `approve_surface_style` · `trade_surface_style` · `reserve_surface_style` · `content_surface_style` · `interact_surface_style`。  
不用单键 `group_surface_style`，不用 `*_browse_style`。

### 0.4 一组一实现 plan（禁止跨组一轮做完）

| 字段 | 内容 |
|------|------|
| 触发 | 该组 thicken 已收口，或地图本组待补已清 |
| 范围 | 仅该节样式目录 + 主表面分支 |
| 交付 | `themes.py` 目录/resolve → catalog / match → `APP_DELIVERED` → 工厂手选 → 学生包 `data-*` 分支；仿 `test_portal_home_style` 单测 |
| 菜单 | 同 spec 下切换任意 style，交付菜单 path 集合不变 |
| 禁止 | 顺手改邻组；借 UI 改能力语义；沉浸首页吃掉菜单 |

**建议开工顺序**：内容 §1.8（加厚收口后优先）→ 交易 §1.6 → 预约 §1.7 → 借用 §1.1 → 报名 §1.4 → 互动 §1.9 → 跟进 §1.2 → 报修 §1.3 / 审批 §1.5 → 兜底 §1.10（导引文案）。

### 0.5 不做

学贴吧等商业站交互；新 `DOM-*`；用 UI 冒充 WebSocket / 真支付 / 道闸 / 人脸；为样式砍菜单。

---

## 1. 总表

| 节 | 组 | 问题 | 主表面 | 选型键 | 档数 | 实现前置 |
|----|----|------|--------|--------|------|----------|
| G-1.1 | 借用/占用 | 重 | ArchiveBrowse、床位色块 | `borrow_surface_style` | 4 | borrow 已收口 |
| G-1.2 | 跟进 | 中 | ArchiveBrowse、跟进时间轴 | `follow_surface_style` | 3 | follow 已收口 |
| G-1.3 | 报修 | 轻 | MyTickets、报修看板 | `repair_surface_style` | 2 | repair 已收口 |
| G-1.4 | 报名/申请 | 重 | ArchiveBrowse、课表 | `apply_surface_style` | 4 | apply 已收口 |
| G-1.5 | 审批/填报 | 轻 | 申请入口、TicketsAdmin | `approve_surface_style` | 2 | approve 已收口 |
| G-1.6 | 交易 | 中 | PortalHome、Cart、ArchiveBrowse | `trade_surface_style` | 3 | trade 已收口 |
| G-1.7 | 预约 | 中 | Slot 页、ArchiveBrowse | `reserve_surface_style` | 3 | reserve 已收口 |
| G-1.8 | 内容 | 重 | ArchiveBrowse | `content_surface_style` | 4 | content 收口后 |
| G-1.9 | 互动 | 中重 | ArchiveBrowse、PeerTickets；Exam/Survey 专用页不动 | `interact_surface_style` | 3 | 互动 thicken 后 |
| G-1.10 | 兜底 | 异质 | 门户说明、README | （无） | 导引块 | 文档向 |

---

## 2. 各组

每节固定：问题 · 主表面 · 菜单保全提示 · 样式目录 · ASCII · 域默认。

### G-1.1 借用 / 占用 — `borrow_surface_style`

**问题（重）**：浏览仍像通用卡片，不像书架 / 货架 / 床位。  
**主表面**：`ArchiveBrowse`；BED 色块；PARCEL 货架。  
**菜单保全**：检索/借阅、我的单据、管理端档案与库存台账等既有入口不因 style 消失。

| id | 名 | 最贴 |
|----|----|------|
| `bookshelf` | 书架脊列 | LIBRARY |
| `stockrow` | 库存台账行 | ASSET / EQUIP |
| `bedblocks` | 床位色块墙 | BED |
| `parcelshelf` | 驿站货架格 | PARCEL |

```text
bookshelf:
| [检索][分类][搜索]  可借图书                    |
| |脊| |脊| |脊| |脊| |脊| |脊|   ← 竖条封面+书名 |
| |脊| |脊| |脊| ...                              |
| 点选 → 余量/借阅/续借说明                       |

stockrow:
| 名称           分类    库存  状态    操作        |
| 示波器×2       仪器    2     可借   [申请]      |
| 投影仪         设备    0     维修中 [查看]      |

bedblocks:
| 楼栋 v  楼层 v                                     |
| [空][占][空][留][空][占]  ← 色块=床位状态         |
| 图例：空=可申请 占=已住 留=保留                   |

parcelshelf:
| 货架 A-1        A-2        A-3                    |
| [件][件][  ]   [件][  ]   [件][件][件]           |
| 取件码核销入口（有码再显）                        |
```

域默认：LIBRARY→`bookshelf`；ASSET/EQUIP→`stockrow`；BED→`bedblocks`；PARCEL→`parcelshelf`。手选优先。

### G-1.2 跟进 — `follow_surface_style`

**问题（中）**：客户 / 房源像物资卡，缺阶段或价签感。  
**主表面**：`ArchiveBrowse`、跟进时间轴。  
**菜单保全**：档案浏览、我的跟进/申请、管理端台账入口保留。

| id | 名 | 最贴 |
|----|----|------|
| `pipeline` | 阶段看板 | CRM |
| `dossier` | 档案行+下次跟进 | CRM / INTERN / FUND |
| `listing` | 挂牌价签卡 | LISTING |

```text
pipeline:
| 线索 | 跟进中 | 待成交 | 已办结 |
| [卡] | [卡]  | [卡]   | [卡]  |
|      | [卡]  |        |       |

dossier:
| 名称/学号     阶段    上次跟进   下次约定   操作 |
| 张三-企微线索 跟进中  03-01     03-08    [跟进] |

listing:
| +--------+  学府路两室  ¥3200/月  90㎡          |
| | 封面   |  标签色点 · 带看 3 次                 |
| +--------+  [约带看]                            |
```

域默认：CRM→`pipeline`；LISTING→`listing`；其余跟进域→`dossier`。

### G-1.3 报修 — `repair_surface_style`（问题轻）

**问题（轻）**：主路径已是工单；分类浏览偶发通用。不强凑四套。  
**主表面**：`MyTickets`、报修看板。  
**菜单保全**：报修申请、我的工单、管理受理/结单入口保留。

| id | 名 | 说明 |
|----|----|------|
| `ticketfeed` | 我的工单进度流 | 默认 |
| `faultboard` | 分类故障看板 | 管理/今日看板加深 |

```text
ticketfeed:
| 我的报修                                       |
| ● 水管漏水  处理中  催办冷却 12:00  [催办][评价]|
| ○ 门锁失灵  已办结  ★★★★☆                     |

faultboard:
| 今日 待派 3  处理中 5  超时 1                   |
| 水电 | 门窗 | 网络 |                           |
| [条] | [条] | [条] |                           |
```

域默认：三域→`ticketfeed`；管理端可选手选 `faultboard`（实现时再钉是否仅管理端）。

### G-1.4 报名 / 申请 — `apply_surface_style`

**问题（重）**：活动 / 选课 / 失物共用物资卡。  
**主表面**：`ArchiveBrowse`、课表。  
**菜单保全**：浏览报名、我的报名、课表、管理审核入口保留。

| id | 名 | 最贴 |
|----|----|------|
| `eventposter` | 活动海报墙 | ACTIVITY |
| `coursetable` | 课表网 | COURSE |
| `noticeboard` | 启事板 | LOST |
| `tourcard` | 线路行程卡 | TOUR |

```text
eventposter:
| [大海报·名额紧张] 春季杯报名中  余 12  [报名]  |
| +------+ +------+ +------+                     |
| |海报  | |海报  | |海报  |  截止·候补提示      |

coursetable:
|    一  二  三  四  五                          |
| 1 [高数][   ][英语][   ][实验]  冲突高亮       |
| 2 [   ][程C ][   ][程C ][   ]                  |

noticeboard:
| + 寻物 --+ + 招领 --+ + 线索 --+               |
| | 钥匙…  | | 校园卡 | | 目击…  |  地点·时间   |
| +--------+ +--------+ +--------+               |

tourcard:
| 云南大理5日  余位 8  出团 04-01  [报名]        |
| 行程亮点一行……                                 |
```

域默认：ACTIVITY→`eventposter`；COURSE→`coursetable`；LOST→`noticeboard`；TOUR→`tourcard`。

### G-1.5 审批 / 填报 — `approve_surface_style`（问题轻）

**问题（轻）**：事项类型列表像后台表。  
**主表面**：申请入口、审批收件箱。  
**菜单保全**：各事项申请、我的申请、待我审、管理台账入口保留。

| id | 名 | 说明 |
|----|----|------|
| `typelist` | 事项类型清单+申请 | 默认 |
| `inboxsteps` | 待审收件箱+步骤条 | 审批岗 |

```text
typelist:
| 证明开具     需材料 2 项    [申请]              |
| 用车申请     须填时段       [申请]              |
| 经费报销     多级审         [申请]              |

inboxsteps:
| 待我审 (3)                                     |
| 报销-张三  初审→复审→终审  ●○○  [审]         |
```

域默认：用户端 `typelist`；审批岗视图 `inboxsteps`（可与角色绑定，实现 plan 钉）。

### G-1.6 交易 — `trade_surface_style`

**问题（中）**：门户已有 mall；列表仍偏通用商品卡。  
**主表面**：`PortalHome`、`Cart`、`ArchiveBrowse`、选座页。  
**菜单保全**：浏览/购物车/订单/售后/管理端订单与商品入口保留；不因货架皮取消菜单。

| id | 名 | 最贴 |
|----|----|------|
| `shelfgrid` | 货架密铺 | SHOP |
| `menuboard` | 档口菜单板 | FOOD |
| `showtime` | 排片+选座入口 | CINEMA |

```text
shelfgrid:
| 分类chips: 全部 数码 日用 …                    |
| [图¥][图¥][图¥][图¥]  价签角标·限时倒计时     |

menuboard:
| 一食堂窗口A          窗口B                     |
| 黄焖鸡  ¥12 [加购]   米线 ¥10 [加购]          |
| 套餐…                饮品…                     |

showtime:
| 今日排片                                       |
| 14:20 厅3  余座 40  [选座]                     |
| 19:30 厅1  余座 12  [选座]                     |
```

域默认：SHOP→`shelfgrid`；FOOD→`menuboard`；CINEMA→`showtime`。门户 `portal_home_style=mall` 已存在，本组实现只补列表轴。

### G-1.7 预约 — `reserve_surface_style`

**问题（中）**：时段组件有，房型/号源列表仍通用。  
**主表面**：Slot 页、`ArchiveBrowse`。  
**菜单保全**：预约浏览、我的预约、管理时段/黑名单入口保留。

| id | 名 | 最贴 |
|----|----|------|
| `slotstrip` | 时段条/号源行 | HOSPITAL / MEETING / SALON |
| `roomstate` | 房态格 | HOTEL |
| `vehiclecard` | 车型档期卡 | CARRENT / PARKING |

```text
slotstrip:
| 科室/场地 v  日期 v                            |
| 09:00 有号  09:30 满  10:00 有号  [预约]       |

roomstate:
| 日期 →                                         |
| 标间 [空][住][脏][空]  图例=房态               |
| 大床 [住][住][空][预]                          |

vehiclecard:
| +----+  朗逸 · 自动  ¥180/天  押金说明         |
| |车图|  可取 03-12 起  [预订]                  |
| +----+                                         |
```

域默认：HOSPITAL/MEETING/SALON/INSTRUMENT→`slotstrip`；HOTEL→`roomstate`；CARRENT/PARKING→`vehiclecard`。

### G-1.8 内容 — `content_surface_style`（收口后优先实现）

**问题（重）**：列表最不像内容站。  
**主表面**：`ArchiveBrowse`（MEDIA `posterWall` 并入 `coverwall`）。  
**菜单保全**：浏览、发文/投稿、我的收藏/足迹、管理审核与档案入口保留；editorial 首页不得吃掉菜单。

| id | 名 | 最贴 |
|----|----|------|
| `folio` | 刊头阅读流 | BLOG / FORUM |
| `coverwall` | 封面墙 | MEDIA / MUSIC |
| `ledger` | 条目清单 | DOCLIB |
| `splitdesk` | 双栏阅读台 | BLOG / DOCLIB；窄屏降级为先列表后详情 |

```text
folio:
| [检索][分类][发文]                             |
| ########### 头条封面 ###########               |
| 标题 摘要 阅读数 [置顶][精华]                  |
| [封面] 条目二 摘要…… [阅读]                    |

coverwall:
| [封面][封面][封面][封面][封面]  题名极简     |

ledger:
| 标题           作者  分类  阅读  [阅读]        |
| 资料A.pdf      张三  教程  320                 |

splitdesk:
| 列表高亮 | 右侧封面+摘要+收藏/点赞             |
| 窄屏：先列表后详情                             |
```

域默认：BLOG/FORUM→`folio`；MEDIA/MUSIC→`coverwall`；DOCLIB→`ledger`。手选优先；未选手选可按种子在目录内抽。

### G-1.9 互动 — `interact_surface_style`

**问题（中重）**：婚恋 / 双选 / 拼车像档案卡。  
**主表面**：`ArchiveBrowse`、`PeerTickets`；**EXAM / SURVEY / VOTE 专用页已存在则不进本轴**（只允许 immersion 边角，不新建第三套答题壳）。  
**菜单保全**：资料浏览、志愿/同行、私信、考试/问卷/投票既有菜单保留。

| id | 名 | 最贴 |
|----|----|------|
| `profilegrid` | 资料卡片墙 | DATING |
| `mutualpick` | 双选志愿卡 | MUTUAL-* |
| `triprow` | 行程同行行 | CARPOOL / TIMEBANK |

```text
profilegrid:
| +----+ +----+ +----+                           |
| |头像| |头像| |头像|  城市·年龄·完整度条      |
| |简介| |简介| |简介|  [打招呼]                 |

mutualpick:
| 志愿1 导师A  名额 2/5  ████░  [确认][婉拒]   |
| 志愿2 选题B  …                                 |

triprow:
| 03-20 08:00  南门→车站  余位 2  分摊备注  [同行]|
```

域默认：DATING→`profilegrid`；MUTUAL-*→`mutualpick`；CARPOOL/TIMEBANK→`triprow`。实现前置：互动组 thicken / 地图 §1.9 待补清到可开工后再开 plan。

### G-1.10 兜底 — 无选型键

**问题（异质）**：要的是交叉导引，不是浏览皮。  
**主表面**：门户只读说明、README 固定段。  
与地图 §1.10 待补导引对齐；不做手选目录。

```text
| 本系统含两条主路径（交叉壳）                   |
| A 借用检索→申请单    B 场地时段→预约           |
| 答辩时先演示 A 再演示 B；勿冒充单一行业站     |
```

---

## 3. 共享实现备忘（各组 plan 复用）

| 步骤 | 落点 |
|------|------|
| 目录与 resolve | [`backend/app/bake/themes.py`](../backend/app/bake/themes.py)（仿 `PORTAL_HOME_STYLES` / `resolve_portal_home_style`） |
| Spec 组装 | `catalog.py`、`project_match.py` |
| 出包注入 | `engine_resources.py` / `APP_DELIVERED` / 可选 `VITE_*` |
| 工厂手选 | `frontend/.../pdLabels.js`、`useProjectDetail.js` |
| 学生包分支 | 以该组主表面为准（多为 `ArchiveBrowse.vue`）；`data-{group}-surface` |
| 菜单门禁 | 同 spec 切换 style → 菜单 path 集合断言不变 |
| 测试 | 仿 [`backend/tests/test_portal_home_style.py`](../backend/tests/test_portal_home_style.py) |

与 [`immersion-corners.md`](./immersion-corners.md) 边界：本册 = 可选手选主路径构图；沉浸边角 = 非强制观感加分，不替代本轴。

---

## 4. 修订

| 日期 | 说明 |
|------|------|
| 2026-10-10 | 初版：§1.1～§1.10 选型 + ASCII；键名统一 `*_surface_style`；菜单保全；加厚后一组一 plan |
