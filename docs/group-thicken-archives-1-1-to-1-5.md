# §1.1～§1.5 组加厚已收口档案（复盘）

> **本文只负责**：借用 / 跟进 / 报修 / 报名 / 审批五组加厚的**复盘索引**（模块、域集、收口时间线、真源指针）。  
> **不负责**：逐条功能明细（真源是地图各节「本组本轮已齐」）；cap 定义（[`capabilities.md`](./capabilities.md)）；UI 表面（[`domain-group-ui-styles.md`](./domain-group-ui-styles.md)）。  
> **状态**：**已收口档案**。这五组在 §1.6 起「独立 batch 册」制度之前清完；当时勾选与迁行写在地图 changelog，**无** `T-00` 式分册。本文补齐复盘入口，不改写历史批次号。  
> **索引**：[README.md](./README.md) · 地图 [`opening-feature-delivery-map.md`](./opening-feature-delivery-map.md) · 范本（分册制）[`trade-thicken-batch.md`](./trade-thicken-batch.md)。

---

## 0. 怎么复盘

| 步骤 | 去哪 |
|------|------|
| 1 | 下表点进对应地图 §1.x「本组本轮已齐」核对功能行 |
| 2 | 打开组模块 `backend/app/bake/features/<组>_thicken.py` 看域默认 / 扫词 |
| 3 | 对照 changelog 日期段（见各节）理解齐度纠偏（Hint 退回 → 双端写库） |
| 4 | UI 构图另册，加厚后做：[`domain-group-ui-styles.md`](./domain-group-ui-styles.md) |

**共同硬口径**（与 §1.6+ batch 册相同）：管理能管 + 用户可产生数据；三骨架同绑；纯 Hint / 只读 / 打印 ≠ 已齐。

| 地图节 | 组 | 模块 | 独立 batch 册 |
|--------|----|------|----------------|
| §1.1 | 借用/占用 | `borrow_thicken.py` | 无 → 本文 §1 |
| §1.2 | 跟进 | `follow_thicken.py` | 无 → 本文 §2 |
| §1.3 | 报修/工单 | `repair_thicken.py` | 无 → 本文 §3 |
| §1.4 | 报名/申请 | `apply_thicken.py` | 无 → 本文 §4 |
| §1.5 | 审批/填报 | `approve_thicken.py` | 无 → 本文 §5 |
| §1.6+ | 交易起 | 各组 `*_thicken` | 有独立 `*-thicken-batch.md` |

---

## 1. §1.1 借用 / 占用 — `borrow_thicken`

| 项 | 内容 |
|----|------|
| 地图 | [`opening-feature-delivery-map.md`](./opening-feature-delivery-map.md) §1.1 |
| 模块 | `backend/app/bake/features/borrow_thicken.py` → `apply_borrow_thicken_to_spec` |
| 主域 | LIBRARY / EQUIP / ASSET / PARCEL / BED（INSTRUMENT 级联归 §1.7） |
| Store 主战场 | `ArchiveStore` / `TicketStore`；辅 Message / Favorites / stock |
| 待补 | 已清（地图本组待补无行） |
| 收口时间线（changelog） | 2026-09-30：续借/催还/信誉分/报废单/PROCURE 一键入库；齐度纠偏（Hint≠已齐）后双端闭环 |

**复盘要点**：信誉分（`credit_score` + 台账）曾误判 Store 不读，后已跨 Store / 逾期扣分 / 再借拦截；报废走独立审批单 `scrap_request`。

**不支持边界（摘）**：多仓 WMS、采购壳冒充领用、跑腿商城、道闸等——见地图 §1.1 不支持段。

---

## 2. §1.2 跟进 — `follow_thicken`

| 项 | 内容 |
|----|------|
| 地图 | 地图 §1.2 |
| 模块 | `backend/app/bake/features/follow_thicken.py` |
| 域集 | `FOLLOW_DOMAINS`：CRM / EVENT / ATTEND / FUND / RECRUIT / GRADE / INTERN / LISTING |
| Store 主战场 | `TicketStore` / `ArchiveStore`；时间轴与渠道统计 |
| 待补 | 已清 |
| 收口时间线 | 2026-09-30：跟进组加厚收尾；批量录用 / 周报催交 / 漏斗与渠道饼图；ATTEND 假期额度域默认 |

**复盘要点**：不接公海池 / 外呼中心；成交登记只记事实（LISTING）；成绩 / 实习与 CRM 同壳不同皮。

**与 domains 组 A**：CRM 等写在 domains **A** 大表里，加厚归地图 **§1.2**，勿按 A 族一次清完。

---

## 3. §1.3 报修 / 工单 — `repair_thicken`

| 项 | 内容 |
|----|------|
| 地图 | 地图 §1.3 |
| 模块 | `backend/app/bake/features/repair_thicken.py` |
| 域集 | `REPAIR_DOMAINS`：DORM / PROPERTY / IT |
| Store 主战场 | `TicketStore`（催办 / 评价 / 结单） |
| 待补 | 主链已清；边缘 Hint 另案（地图待补说明） |
| 收口时间线 | 2026-09-30 前后：用户催办链、冷却、评价锁定、SLA 分列等双端闭环；门禁钉控件 |

**复盘要点**：催办 = 站内时限提醒，≠短信；三域同壳换皮。

---

## 4. §1.4 报名 / 申请 — `apply_thicken`

| 项 | 内容 |
|----|------|
| 地图 | 地图 §1.4 |
| 模块 | `backend/app/bake/features/apply_thicken.py` |
| 域集 | `APPLY_DOMAINS`：ACTIVITY / LOST / COURSE / TOUR |
| Store 主战场 | `TicketStore` / `ArchiveStore`；候补 / 签到 / 课表冲突 |
| 待补 | 已清 |
| 收口时间线 | 2026-10-01～10-02：第二～八批（批量审、候补、口令/费用、冲突高亮、办结相册等） |

**复盘要点**：COURSE 单据评价不挂（评教走 DOM-EVAL）；不接真支付 / 闸机 / 地图 / OTA。

---

## 5. §1.5 审批 / 填报 — `approve_thicken`

| 项 | 内容 |
|----|------|
| 地图 | 地图 §1.5 |
| 模块 | `backend/app/bake/features/approve_thicken.py` |
| 域集 | `APPROVE_DOMAINS`（约 23 域：LABSAFE…CHECKIN；见模块 frozenset） |
| Store 主战场 | `TicketStore`；材料清单 / 多级审 / 抄送 / 转审一跳 |
| 待补 | 已清（2026-10-05 第十七批） |
| 收口时间线 | 2026-10-02～10-05：第一～十七批（撤回/退回、转审、域皮字段、子表三范式、套打壳等） |

**复盘要点**：批次最多；第十二批起报销/行程强制子表（禁 JSON 明细）；VISITOR 不进 `APPLY_DOMAINS`；通行码软闸 ≠ 道闸；PROCURE 入库复用 `borrow_thicken`。

**与 domains 组 A**：大量审批域仍列在 A 表，加厚只走 §1.5。

---

## 6. 修订

| 日期 | 说明 |
|------|------|
| 2026-10-10 | 初版复盘档案：汇总 §1.1～§1.5 已收口事实；明细仍以地图为准 |
