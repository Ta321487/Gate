# 搁置工作台账

> **本文只负责**：统计「先扔一边、回头再开」的工作。  
> **不负责**：实现规格、验收勾选、地图待补行（仍以各专题册为准）。  
> **状态**：活表 · 仅记账。  
> **索引**：[README.md](./README.md)

---

## 大线（4）

| # | 项 | 一句话 | 真源 / 下次从哪开 | 现状 |
|---|----|--------|-------------------|------|
| 1 | **UI 包** | 观感加厚；Vue 大文件拆分；起包前布局闸；可交互控件；全域 UI 诊断表 | 观感 [`ui-look-thicken-batch.md`](./ui-look-thicken-batch.md)；拆分 [`vue-split-batch.md`](./vue-split-batch.md)；布局 [`ui-layout-prebake-gate.md`](./ui-layout-prebake-gate.md)；控件 [`form-controls.md`](./form-controls.md)；诊断 [`ui-domain-diagnosis.md`](./ui-domain-diagnosis.md) | 观感已齐；**拆分已收口**；布局/控件口径已立·代码未开；诊断表未诊 |
| 2 | **X 系列** | §0 通识横切剩余簇（一轮一簇） | [`crosscut-delivery-batch.md`](./crosscut-delivery-batch.md) | X-AUTH～X-UX 已齐；打印/灯箱/Toast/页脚版本/离开提示/复制单号为**基线体验**；档案 Excel 导入导出已是 xlsx |
| 3 | **挂载收口 → 全族** | 把 **A 壳底 / B 扫词开 / C 能力加深** 三档从交易族**迁到其它域组**（地图挂载列 + bake） | 范本：[`trade-thicken-batch.md`](./trade-thicken-batch.md) §0.3；地图各 §1.x | **交易族 + 借用组已收口**；跟进/报修/报名/审批/预约/内容/互动 **未推** |
| 4 | **开题对齐门禁 → 全族** | 登记开关双向对上（B↔扫词、C↔cap）；禁止全文自由匹配；**随 #3 扩到各域组** | [`opening-align-gate.md`](./opening-align-gate.md)；`TRADE_*` / `BORROW_*_ALIGN_RULES` + `test_opening_align_gate.py` | **交易族 + 借用组 A 白名单 + B + C 门禁已齐**；其余域组登记表/测 **未开** |

### #3 / #4 与 ABC（要扩展到全族）

| 档 | 含义 | #3 迁档 | #4 门禁 |
|----|------|---------|---------|
| **A 壳底** | 域该有的；开题不用逐条写 | 各组定白名单 | 不审扫词；灰区人工进白名单 |
| **B 扫词开** | 开题命中登记词才挂 | 各组从「假域默认」迁出 | 开关 ↔ 同套 `scan_*` |
| **C 能力加深** | 已挂 cap 才叠配套 | 禁止域默认硬塞 cap | 开关 ↔ 依赖 cap |

**是的：ABC 目标都是全族（各域组）**——交易只是范本与首版落地；#3 负责改挂载，#4 负责改完能反向验上。

---

## 碎另案

| # | 项 | 一句话 | 真源 | 现状 |
|---|----|--------|------|------|
| a | **收藏备注** | favorites 备注字段加深 | 地图 / [`interact-thicken-batch.md`](./interact-thicken-batch.md) I-11 | I-11 明文另案；不进互动收口 |
| b | **报修边缘 Hint** | §1.3 主链已清后的边角文案 Hint | 地图 §1.3；[`group-thicken-archives-1-1-to-1-5.md`](./group-thicken-archives-1-1-to-1-5.md) | 另案；非报修主链债 |
| c | **订单小票打印** | 浏览器打印壳已挂；打印≠已齐 | 地图 §1.6 待补；[`trade-thicken-batch.md`](./trade-thicken-batch.md) T-11 | 仍待补（发票下载占位已齐） |
| d | **行为式验证码** | 真行为式后置；图形文案先顶 | [`crosscut-delivery-batch.md`](./crosscut-delivery-batch.md) XA-02 | XA 已齐口径下留待补 |
| e | **Surface Lexicon 尾债** | C2 种子公告迁移 · C3 前端空状态映射 · 库内旧 `gate_e2e` 重 bake | [`surface-lexicon-design.md`](./surface-lexicon-design.md)；[`../HANDOFF.md`](../HANDOFF.md) 话术专项 | 批 A/B/C 已落地；运维/迁移步未清 |
| f | **工厂 API MySQL 池抖** | 控制台刷 `projects` 时 `slow_sql` 飙到数秒～数十秒，偶发 500：`Packet sequence number wrong - got 1 expected 2`（aiomysql） | `GET /api/projects/{id}` → `crud.get_project`；池 / `projects` 宽列 SELECT；可对照 [`preview-capacity-and-batch-ops.md`](./preview-capacity-and-batch-ops.md) | **未修**。先像连接池耗尽/坏连回收或同连并发乱序，不是业务 SQL 写错 |
| g | **资料页角色分栏** | 买家/商家/超管资料像同一模板；`profileFields` 缺 `forRoles` | bake 钉 shop*=staff、收货=user；农产包重写 profileFields | **已修**（2026-10-14） |
| h | **门户顶栏换行一团** | 曾抬到 12 全直出，商城 8～11 项长标签换行挤成两排 | §3：软皮分岔 marketplace 右侧栏 / storefront 头像菜单；禁表情与叠两份 | **已修**（2026-10-20） |
| k | **学生包工厂注记** | 骨架可写开题/§3 注释；bake 须抹掉且裁未挂壳件 | `pack_prune.scrub_factory_notes` + 非 marketplace 裁 SideRail | **已接**（2026-10-20） |
| i | **工作台空图空表** | 超管/商家仪表盘空（种子少；商家缺 `owner_username`） | `_SHOP_FARM` 补成交单+商品归属店员 | **已修种子**（2026-10-14）；**已有库要重导/补种子**才看得见图 |
| j | **今年题名库** | 只代表今年的选题，不预测明年。工厂按册一点点长，不等全文开题 | [`cohort-opening-title-map.md`](./cohort-opening-title-map.md) | **方向已写** · 工厂未改（2026-10-17） |

---

## 不进本表

- 已收口档案（§1.1～§1.9 thicken、扩岛 E 批等）——不往回开。
- 单包学生样例修补（如农产扫词关开关）——随手活。
- AI 轴、换皮 ID、沉浸边角、答辩 PPT、预览容量——各有专册；未点名进上表则不抄。

---

## 修订

| 日期 | 说明 |
|------|------|
| 2026-10-14 | 立册：大线 UI 包 · X 系列 · 挂载收口到全族 |
| 2026-10-14 | 加「碎另案」表：收藏备注 / 报修 Hint / 小票打印 / 行为验证码 / Lexicon 尾债 |
| 2026-10-14 | 大线补 **#4 开题对齐门禁**（对照表 + 多挂/漏挂 gate；≠ 既有 opening_align） |
| 2026-10-14 | #4 交易 B 首版落地：`opening-align-gate.md` + `TRADE_B_ALIGN_RULES` + gate 测 |
| 2026-10-14 | #4 补交易 C；钉清 **ABC 目标扩全族**（#3 迁档 + #4 门禁） |
| 2026-10-14 | 碎另案 **f**：工厂 API `projects` slow_sql + aiomysql packet sequence 500 |
| 2026-10-14 | 农产探针：协议链已修进骨架 `publicPaths`；另记 g/h/i（资料分栏/更多/空仪表盘） |
| 2026-10-14 | 落地 g/h/i：forRoles 加固、门户更多阈值 12、农产种子加成交/店归属；包邮改扫词开 |
| 2026-10-16 | X-ORG XO-00/01：字典+站点浅设置+标签/批量启停收口；组织树/RBAC 仍挂 XO-02 |
| 2026-10-16 | X-ORG XO-02：浅组织树、资料挂组织、用户列表按组织过滤、岗位菜单勾选；无勾选记录仍用原岗位包 |
| 2026-10-16 | X-ORG 挂载纠偏：字典/外观/组织/岗位菜单改扫词开；标签批量启停仍常开；技术节「角色权限」不误开 |
| 2026-10-16 | X-LIST XL-01：档案组合筛选、导出列勾选、顶栏搜索扫词才挂；XL-02 仍含导入/批量/回收站/素材/佣金 |
| 2026-10-16 | X-LIST XL-02：回收站、档案批量删除、单据批量通过/驳回扫词才挂；Excel 二进制、素材库、一级佣金仍待补 |
| 2026-10-16 | X-UX XU-01：使用说明页扫词才挂；上传超过 10MB 返回明确提示 |
| 2026-10-16 | X-UX XU-02：文件列表、省市区、删档驳回售后二次确认、一级佣金扫词才挂；Excel 二进制与打印/灯箱仍待补 |
| 2026-10-16 | 基线体验常开：打印本页/灯箱/Toast/页脚版本/离开未保存/单号复制；地图改「基线体验」 |
| 2026-10-16 | 档案导入模板、导入、导出改为 xlsx（Apache POI），按行回错；其它名单导出仍为 CSV |
| 2026-10-17 | #3/#4 **借用组**收口：双方确认/保养到期日/超期次数改扫词；荐购预算随 book_suggest；`BORROW_*_ALIGN_RULES` + gate 测 |
| 2026-10-17 | 碎另案 **j**：本届题名库 → 域/皮/功能判断入 [`cohort-opening-title-map.md`](./cohort-opening-title-map.md)；补皮与新域候选未开工 |
| 2026-10-17 | **j** 口径：只有超新有开题正文；其余题名是工作猜测，不再等正文 |
| 2026-10-17 | **j** 再改：多实现题不猜一条。将来一讲法一份开题再喂工厂；现在不出开题 |
| 2026-10-17 | **j** 口径：文档写清「若有这种开题，成品长什么样」；当下不改工厂 |
| 2026-10-17 | **j** 再改：选题表即近年来开题范例；按册一点点长，不等全文开题 |
| 2026-10-17 | **j** 纠偏：这是今年的选题，不写成近年来，也不预测明年 |
| 2026-10-17 | 大线 #1：`content_surface_style` 首刀接线（仿 `portal_home_style`）；下一 `trade_surface_style` |
| 2026-10-17 | 大线 #1：`trade_surface_style` 接线；下一 `reserve_surface_style` |
| 2026-10-17 | 大线 #1：`reserve_surface_style` 接线；下一 `borrow_surface_style` |
| 2026-10-18 | 大线 #1：`borrow_surface_style` 接线（含工厂示意预览）；下一 `apply_surface_style` |
| 2026-10-19 | 大线 #1：`apply_surface_style` 接线（含示意预览与隐喻绑域）；下一 `interact_surface_style` |
| 2026-10-19 | 大线 #1：`interact_surface_style` 接线（婚恋/双选/拼车；考试问卷投票不进轴）；下一 `follow_surface_style` |
| 2026-10-19 | 大线 #1：`follow_surface_style` 接线（阶段看板只 CRM、挂牌价签只 LISTING）；下一 `repair_surface_style` |
| 2026-10-19 | 大线 #1：`repair_surface_style` 接线（进度流/故障看板只给宿舍物业 IT）；下一 `approve_surface_style` |
| 2026-10-19 | 大线 #1：`approve_surface_style` 接线（事项清单/待审步骤条只给审批域）；下一 §1.10 导引文案 |
| 2026-10-21 | 大线 #1：跟进 follow 观感首刀已齐（pipeline/dossier/listing，LISTING 补 price 价签）；下一报修 |
| 2026-10-22 | 大线 #1：跟进观感收口——priceYuan/priceUnit 多档、followStageTone、三档 CSS；下一报修 |
| 2026-10-22 | 大线 #1：报修观感首刀已齐（ticketfeed/faultboard）；下一审批 |
| 2026-10-22 | 大线 #1：审批观感首刀已齐（typelist/inboxsteps）；九组观感首刀齐，下一软皮短签再磨 |
| 2026-10-22 | 大线 #1：交易再磨——menuboard/showtime + 列表短签芯片接线；下一借用详情文案 |
| 2026-10-22 | 大线 #1：借用再磨——详情借阅/床位/取件文案按 surface 分脸；下一软皮短签分批 |
| 2026-10-22 | 大线 #1：软皮短签再磨收口（预约→内容→报名→跟进/互动→报修/审批轻磨）；下一抽检回归 |
| 2026-10-22 | 大线 #1：开 Vue 大文件拆分批次（vue-split-batch）；范式 ArchiveBrowse；排队 MyTickets 起 |
| 2026-10-22 | 大线 #1：Vue 大文件拆分收口（MyTickets→MyOrders 九页 + ArchiveBrowse 范式）；合读 `vue_src` |
