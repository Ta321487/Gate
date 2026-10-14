# 搁置工作台账

> **本文只负责**：统计「先扔一边、回头再开」的工作。  
> **不负责**：实现规格、验收勾选、地图待补行（仍以各专题册为准）。  
> **状态**：活表 · 仅记账。  
> **索引**：[README.md](./README.md)

---

## 大线（4）

| # | 项 | 一句话 | 真源 / 下次从哪开 | 现状 |
|---|----|--------|-------------------|------|
| 1 | **UI 包** | 域组页内构图选型 → bake/骨架接线；一组一 plan | [`domain-group-ui-styles.md`](./domain-group-ui-styles.md) | 选型册已齐 · **未实现**；优先 `content_surface_style` |
| 2 | **X 系列** | §0 通识横切剩余簇（一轮一簇） | [`crosscut-delivery-batch.md`](./crosscut-delivery-batch.md) | X-AUTH / X-MSG / X-DASH **已齐**；待开 **X-ORG → X-LIST → X-UX** |
| 3 | **挂载收口 → 全族** | 把 **A 壳底 / B 扫词开 / C 能力加深** 三档从交易族**迁到其它域组**（地图挂载列 + bake） | 范本：[`trade-thicken-batch.md`](./trade-thicken-batch.md) §0.3；地图各 §1.x | **仅交易族迁档已齐**；借用/跟进/报修/报名/审批/预约/内容/互动等 **未推** |
| 4 | **开题对齐门禁 → 全族** | 登记开关双向对上（B↔扫词、C↔cap）；禁止全文自由匹配；**随 #3 扩到各域组** | [`opening-align-gate.md`](./opening-align-gate.md)；`TRADE_*_ALIGN_RULES` + `test_opening_align_gate.py` | **交易族 A 白名单 + B + C 门禁已齐**；其它域组登记表/测 **未开** |

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
| h | **门户「更多」过早收纳** | 用户菜单 >6 就进「更多」 | `PORTAL_NAV_INLINE_MAX=12`（≤12 全直出） | **已修**（2026-10-14） |
| i | **工作台空图空表** | 超管/商家仪表盘空（种子少；商家缺 `owner_username`） | `_SHOP_FARM` 补成交单+商品归属店员 | **已修种子**（2026-10-14）；**已有库要重导/补种子**才看得见图 |

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
