# 角色边界文案批次（按域族收）

> **本文只负责**：① 把「换开题还会不会年年磨」说清楚（难度诚实账）；② 按 `DOMAIN_GROUPS` **一组一轮**收「提案角色树 ↔ 页面/菜单/`labels.*`」这一族，并收成**结构闸**。  
> **不负责**：密功能四件套（地图 §1.x / thicken 已收口档案）；跨域招牌词词表正文（[`surface-lexicon-design.md`](./surface-lexicon-design.md) / `domain_vocab.py`）；布局/控件闸细则；交付审计小卡写法（[`delivery-audit-rules.md`](./delivery-audit-rules.md)）。  
> **状态**：**L4 十组已齐** · 难度账常读；`trade`～`fallback` **已齐**；未知口语/L5 仍长尾。  
> **索引**：[README.md](./README.md) · 组真源 `backend/app/bake/domains.py` → `DOMAIN_GROUPS` / `AUDIT_GROUP_CANARIES` · 结构闸家 `backend/app/llm/agents_qa.py`。

---

## 0. 换开题抗性（诚实账）

> 读本册其余章节前先读本节。  
> **禁止**把「某一族已钉结构闸」说成「明年换开题可以撒手」。那是低估。

### 0.1 你真正怕的是什么

怕的不是「管理员 lead 那一句」 alone，而是：

**明年题库换皮换说法之后，还要不要像今年一样——红一单、擦一包、再踩一个从没见过的缝。**

若答案变成「要，而且按域按单」，工厂主链路就失败了。目标仍是：**程序归工厂**；新开题是探针，洞进共享机制。  
但「目标」≠「已经到达」。下面按层记账，不灌鸡汤。

### 0.2 难度为什么重（不是矫情）

| 因子 | 为什么啃人 |
|------|------------|
| **开题是自然语言** | 同业务无数说法；扫词/角色树/模块图都是有限表，**盖不住明年新口语** |
| **组合爆炸** | ~68 域 × 场景皮 × 能力岛 × 单店/多店/三端 × 技术栈；洞往往出在**交点**，不是单域正文 |
| **可见面很长** | labels、菜单、种子 SQL、公告、模块图、用例、README、空态——一处对、另一处串，门禁与答辩都能打脸 |
| **出包冻得住** | bake 进 ZIP 的文案不会自动跟仓库热修；修工厂后**旧包仍要重 bake**，体感像「又磨一单」 |
| **`p3q` 仍有 LLM 主审** | 结构闸只覆盖**已写成规则**的洞；其余靠模型，**同包重跑措辞可能变**，体感像随机 |
| **「组已齐」≠「语义已齐」** | thicken / 布局 / 控件收口的是**功能与几何**；角色口吻、错域词、假宣称是另一条战线上的活 |

所以：按域族收，是把复杂度从「题 × 域」压成「组 × 失败家族」——**仍然是多轮硬活**，只是拒绝题海人肉。

### 0.3 换开题抗性分层（全厂，不限本册）

| 层 | 内容 | 换开题后大概怎样 | 抗性 | 还要不要磨 |
|----|------|------------------|------|------------|
| **L0 几何/控件** | 布局一眼病、可交互控件 | 基线+出包闸已钉；新题少踩同款几何 | **高** | 基本不用按题磨；新一眼病先补册再消 |
| **L1 密功能骨架** | 地图 §1.x 四件套 / thicken | 新题多半挂已有 cap；真缺能力才扩岛 | **中高** | 扩岛是立项活，不是每题打磨 |
| **L2 匹配/对齐** | 域判定、扫词、开题对齐门禁 | 新说法可能打偏邻域或漏挂 | **中** | 撞偏 → 补规则/测；仍有误匹配风险 |
| **L3 话术口径** | 跨域招牌词、同槽分叉、`allow*` | 词表外新词会漏；皮一多易分叉 | **中** | 补 `domain_vocab` / lexicon，不是重做 68 域 |
| **L4 角色边界** | 多端职责、Admin/Staff lead、模块角色树 | **本册主战场**；多店/档口等交点最脏 | **偏低→往中抬** | **按组收 + 结构闸**；未收完前还会红 |
| **L5 材料↔实包** | 模块图/用例/论文实现叙述 vs ZIP | 文案一改八张材料易漂；LLM/模板都可能漂 | **偏低** | 长期债；不能假装 thicken 已顺便清掉 |
| **L6 假宣称/硬边界** | 真支付、人脸、CA、小程序原生等 | 开题爱写、工厂不能交则须双显/拒收 | **中（有诚实闸）** | 新吹法要补种子；漏了就答辩事故 |
| **L7 真交叉/拒收题** | Path B、三合一、智慧校园等 | 边界题年年可能换皮撞枪口 | **题型相关** | 该拒就拒；禁止空壳冒充 |

**本册只加厚 L4**（并捎带扫到的 L3/L6 槽位漏网）。  
**L5、L2 的剩余长尾，足够再开独立批次**——不要写进「角色族已齐」里报喜。

### 0.4 「明年还要挨个磨吗」——可验收的说法

| 说法 | 是否诚实 |
|------|----------|
| 「角色那句修了，明年随便出题都绿」 | **否** · 吹牛 |
| 「布局/控件/密功能不用按 68 域年年重做」 | **大致是** · 已有闸与收口档案 |
| 「语义长尾（L2～L5）还会红，但应变成：红 → 一组收 → 结构闸 → 同族不再静默过」 | **是** · 本册纪律 |
| 「零人工、零重 bake、零新闸」 | **否** · 做不到 |
| 「成功 = 常规题不必开修复会话跟单改包；新洞小时级进工厂，而不是天级擦 ZIP」 | **是** · 产品最终形态（见 boss-intent） |

旧包：仓库热修**不会**写进已生成 ZIP → 当面消红仍要重 bake。这很烦，但是冻包语义；烦的是「洞没进闸所以明年又撞」，不是「重 bake」本身。

### 0.5 助手/进度汇报禁令（防轻飘）

写 HANDOFF / 对老板说话时：

- **禁止**用「基本不用怕」「撒手」「差不多齐了」形容 L2～L5 未收完状态。  
- **禁止**把「金丝雀绿」「单测绿」说成「该组换开题抗性已高」。  
- **可以**说：某条结构闸已钉、某组台账迁已齐、**已知**剩余风险在哪一层。  
- 每收一组，必须补一句：**本组还没挡住的家族**（若无，写「已知洞已闸；未知口语仍依赖 p3q/LLM」）。

### 0.6 和本册后文的关系

- §1 起才是 **L4 角色边界** 的开工纪律与组台账。  
- 若老板要「换开题抗性」总攻：优先顺序建议 **L4（本册）→ L3 补表巩固 → L5 材料一致性**；L0/L1 勿当还没做的主线。  
- 年库方向题与成品域对照见 [`cohort-opening-title-map.md`](./cohort-opening-title-map.md)（不代替本账）。

---

## 1. 本册硬口径（L4 · 角色边界这一刀）

### 1.1 为什么有本册正文

交付质量摘要（`p3q`）里，LLM 常抓「管理员页写成商家活 / 提案监督却写发货」这类**角色边界**。  
同款会换句子、换槽位再冒——**禁止** 68 域逐单踩；按**域族**收，踩一次 → 共享机制 + 本组测 + 结构闸。  
这是 L4 的降维打法，**不是**给全表 L0～L7 开脱。

### 1.2 一轮 = 一组（禁止跨组清）

| 规则 | 含义 |
|------|------|
| **组** | `DOMAIN_GROUPS` 的 gid（`trade` / `reserve` / …），不是单个 `DOM-*` |
| **探针** | 默认用 `AUDIT_GROUP_CANARIES` 该组代表题；本组若有「多角色/多端」变体再加 1 邻域（如交易加多店、FOOD） |
| **修工厂** | 改 bake schema / `proposal_role_modules` 对齐 / `agents_qa` 结构闸 / 对口测；**禁止**只擦当面 ZIP |
| **收成闸** | 本组发现的可机器判规则 → `_structural_findings`（或 `domain_vocab`）；关 LLM 也必须能挡 |
| **迁行** | 本册 §3 勾选改已齐；HANDOFF 记「做到哪组」+ §0.5 剩余风险句 |

### 1.3 本册范围（失败家族）

| 家族 | 症状 | 典型落点 |
|------|------|----------|
| **R1 角色串台** | 管理员 lead/菜单写成商家·档口·馆员一线操作（或反过来） | `labels.*AdminLead` / `*StaffLead`、订单/售后页头、模块图角色树 |
| **R2 壳叙事串邻组** | 预约/影院写「发货物流」；报修写商城购物车口吻 | `orderFulfillHint`、notice、种子公告、entities.verbs |
| **R3 宣称 vs 菜单/实体** | 文案宣称某端能力，menuKeys/entityKeys 未挂 | labels / README 学生面 / modules |
| **R4 支付/硬边界吹过头** | 支付宝微信当真接；人脸等硬边界写成已支持 | 已有支付/诚实结构闸；本组只扫是否新槽位漏网 |

**不进本册**：纯几何一眼病、控件选型、`allow*` 字段渲染漏分支（归 lexicon / B2）、表配额、论文八图系统性对账（L5 另册）。

### 1.4 一条命中 = 三件套（缺一不算已齐）

| 件 | 要求 |
|----|------|
| ① **文案真源** | bake 写出正确角色句（admin ≠ staff；提案树与 lead 同口径） |
| ② **结构闸** | 可正则/旗标判定的再发 → `agents_qa`（或 vocab）error；正反例测 |
| ③ **组探针绿** | 至少 canary schema（+ 本组邻域若本轮动了）断言 lead/关键 labels |

纯改一句文案、不闸、不测 → **不得**标已齐。  
只靠 LLM 又撞到同一句、没有结构闸 → **不得**宣称「这族明年不会再踩」。

### 1.5 不做

- 同轮跨两组大扫；为消红改学生包 / 跳过 `p3q`
- 新开 `*_thicken`；把场景轴/技术栈轴扯进本册
- 「基线摘要绿 = 每题 ZIP 已过」——出包仍走门禁；旧包需重 bake 才吃到新文案
- 用本册进度暗示 L2/L5「也差不多了」

---

## 2. 每轮工序（复制用）

```
组：________（gid）
探针：canary = ________；邻域（可选）= ________

1. 读提案角色树
   - proposal_role_modules 该组树（若有）
   - 开题/金丝雀材料里的「管理员 / 子管·商家·馆员 / 用户」分工

2. 扫可见面（schema 为主，必要时基线页）
   - labels：*AdminLead / *StaffLead / *PageLead / *Hint / notice*
   - menus.admin|user 文案；shopMarketplace / 多端旗标
   - entities.order|ticket verbs/states 是否串邻组叙事

3. 判
   - 串台 / 串邻组 / 吹过头 → 记「洞」一行（槽位 + 错句 + 应收成的闸规则）
   - 真阳性噪声 → 记账，不擦包

4. 改
   - 共享路径优先（builders_* / features / agents_qa）
   - 独有才写域皮，原因写进本册该组「备注」

5. 验
   - 对口 pytest（本组 + test_qa_factory_drift 新闸）
   - 可选：该组 canary bake 看 p3q 是否还靠 LLM 撞同一句

6. 迁
   - §3 本行 → 已齐；HANDOFF：下一组 + 「已知未挡：…」
```

**推荐收口顺序**（L4 内风险高 → 低；可按当面单改序，但勿跳步不闸）：

1. `trade`（多店/档口角色最多）  
2. `reserve`（易串物流发货）  
3. `borrow` / `ticket`（单据态与 hold/额度串页）  
4. `follow` / `approve` / `apply`（申请·审批角色与槽位名）  
5. `content` / `interact`  
6. `fallback`（空皮/错绑，轻扫——**轻扫 ≠ 简单**，错绑开题仍能整题报废）

---

## 3. 组台账

真源组员见 `DOMAIN_GROUPS`；金丝雀见 `AUDIT_GROUP_CANARIES`。  
**状态**：`待收` / `进行中` / `已齐`。  
**已齐**只表示本册 L4 条目与闸；**不**上调 §0.3 整层抗性口头评级。

| 序 | gid | 组名 | 金丝雀 | 状态 | 本轮邻域建议 | 已收条目 | 备注 |
|----|-----|------|--------|------|--------------|----------|------|
| 1 | `trade` | 交易 | DOM-SHOP 校园二手商城 | **已齐** | 多店商城；DOM-FOOD 档口 | R-TRADE-01～05 | 本组 L4 条目已闸；未知口语仍依赖 p3q/LLM；L5 材料另册 |
| 2 | `reserve` | 预约 | DOM-MEETING | **已齐** | HOTEL / CARRENT | R-RESERVE-01～02 | 本组 L4 已闸；INSTRUMENT 跟进皮未拆 lead；未知口语仍依赖 p3q/LLM |
| 3 | `borrow` | 借用/占用 | DOM-LIBRARY | **已齐** | EQUIP / PARCEL | R-BORROW-01～02 | 本组 L4 已闸；未知口语仍依赖 p3q/LLM |
| 4 | `ticket` | 报修/工单 | DOM-DORM | **已齐** | PROPERTY / IT | R-TICKET-01～02 | 本组 L4 已闸；未知口语仍依赖 p3q/LLM |
| 5 | `follow` | 跟进 | DOM-INTERN | **已齐** | CRM / EVENT | R-FOLLOW-01～02 | 本组 L4 已闸；分级/分类归 lexicon；未知口语仍依赖 p3q/LLM |
| 6 | `approve` | 审批/填报 | DOM-SEAL | **已齐** | EXPENSE（多级审） | R-APPROVE-01～02 | 本组 L4 已闸；未知口语仍依赖 p3q/LLM |
| 7 | `apply` | 报名/申请 | DOM-ACTIVITY | **已齐** | COURSE / LOST / TOUR | R-APPLY-01～02 | 本组 L4 已闸；未知口语仍依赖 p3q/LLM |
| 8 | `content` | 内容 | DOM-FORUM | **已齐** | MEDIA / MUSIC / BLOG / DOCLIB | R-CONTENT-01～02 | 本组 L4 已闸；未知口语仍依赖 p3q/LLM |
| 9 | `interact` | 互动/匹配 | DOM-SURVEY | **已齐** | DATING / EXAM / MUTUAL / CARPOOL / TIMEBANK | R-INTERACT-01～02 | 本组 L4 已闸；未挂能力假宣称仍靠诚实闸/p3q；L5 |
| 10 | `fallback` | 兜底 | DOM-GENERIC | **已齐** | FLOW/TRADE/RESERVE 壳 | R-FALLBACK-01～02 | 本组 L4 已闸；错绑开题另案；未知口语仍依赖 p3q/LLM |

---

## 4. 条目明细（按组追加）

### 4.1 trade（交易）

| id | 洞 | 收法 | 闸 / 测 | 状态 |
|----|----|------|---------|------|
| **R-TRADE-01** | 多店 `ordersAdminLead` 写「处理发货、物流与售后」= 商家活塞进管理员 | `builders_slot`：admin=全平台监督；`ordersStaffLead`=本店发货物流售后 | `_marketplace_role_copy_findings`；`test_shop_marketplace` + `test_qa_factory_drift` | **已齐** · 同题重 bake **不得**再因本句红；若仍红必是别条 finding |
| **R-TRADE-02** | 订单页是否按角色露出 Admin/Staff lead | 基线 `OrdersAdmin`：`marketplace` 下超管→`ordersAdminLead`、商家→`ordersStaffLead`（`page-lead`） | `test_orders_admin_role_leads_by_super` | **已齐** |
| **R-TRADE-03** | FOOD 档口：主管 lead 是否写成档口接单发餐 | `_food_schema` 拆 Admin/Staff lead；`OrdersAdmin` 按超管露出；`_food_role_copy_findings` | `test_food_canteen_vs_restaurant` + `test_food_admin_order_lead_blocks_stall_ops` | **已齐** |
| **R-TRADE-04** | 单店 notice「管理员确认发货」在扫成多店时与角色树冲突 | `_shop_schema` 多店改用 `mp_notice_*` / 默认多店句；闸挡残留 | `test_marketplace_schema_flag` + `test_marketplace_notice_blocks_admin_ship_copy` | **已齐** |
| **R-TRADE-05** | CINEMA/非物流壳：模块文案是否仍写发货 | 已有 `skin_invariants` + cinema fulfillMode；本轮钉回归断言 | `test_cinema_not_logistics_ship_copy` + skin leak 矩阵 | **已齐** |

**trade 组已知未挡**：本组 L4 条目已闸；未知口语仍依赖 p3q/LLM；材料图 L5 不在本条范围。**禁止**说「换开题都没事了」。

### 4.2 reserve（预约）

| id | 洞 | 收法 | 闸 / 测 | 状态 |
|----|----|------|---------|------|
| **R-RESERVE-01** | HOTEL/CARRENT/CINEMA 履约句串「发货/物流」 | `orderFulfillHint` 保留「无物流发货」；寄养皮补否定句；`skin_invariants` + `_reserve_fulfill_copy_findings` | `test_reserve_fulfill_blocks_ship_copy` + skin leak | **已齐** |
| **R-RESERVE-02** | 前台/店员 vs 总管预约页 lead 串台 | `_stamp_reserve_role_leads`（MEETING/HOSPITAL/PARKING/SALON/HOTEL/CARRENT）；`ReservationsAdmin` 按超管挂 lead；HOTEL/CARRENT 兼 orders*Lead | `test_reserve_role_leads_meeting_hotel_carrent` + `test_reservations_admin_role_leads_by_super` | **已齐** |

**reserve 组已知未挡**：`DOM-INSTRUMENT` 跟进皮未拆 lead；材料图 L5；未知口语仍依赖 p3q/LLM。**禁止**说「换开题都没事了」。

### 4.3 borrow（借用/占用）

| id | 洞 | 收法 | 闸 / 测 | 状态 |
|----|----|------|---------|------|
| **R-BORROW-01** | hold/取书/借阅额度串到设备·驿站等邻域 | `_borrow_role_copy_findings`：非 LIBRARY 禁 `allowBookHold`/`hold_ready`/`bookHold*`/`待取书`/`借阅额度` | `test_borrow_hold_leak_and_role_leads` | **已齐** |
| **R-BORROW-02** | 总管 vs 馆员/店员单据页 lead 未挂 | `ensure_borrow_role_leads`；`TicketsAdmin` / `TicketRecordsAdmin` 按超管露出 | `test_borrow_role_leads_library_equip_parcel` + `test_tickets_admin_role_leads_by_super` | **已齐** |

**borrow 组已知未挡**：未知口语仍依赖 p3q/LLM；材料图 L5。**禁止**说「换开题都没事了」。

### 4.4 ticket（报修/工单）

| id | 洞 | 收法 | 闸 / 测 | 状态 |
|----|----|------|---------|------|
| **R-TICKET-01** | 工单文案串商城「发货/物流/购物车」 | `_ticket_role_copy_findings` 挡 labels/verbs | `test_ticket_repair_blocks_shop_copy_and_needs_leads` | **已齐** |
| **R-TICKET-02** | 总管 vs 楼管/调度/运维 lead | `ensure_repair_role_leads`；待审/记录页已按超管挂（借用组同页） | `test_ticket_repair_role_leads_dorm_property_it` | **已齐** |

**ticket 组已知未挡**：未知口语仍依赖 p3q/LLM；材料图 L5。**禁止**说「换开题都没事了」。

### 4.5 follow（跟进）

| id | 洞 | 收法 | 闸 / 测 | 状态 |
|----|----|------|---------|------|
| **R-FOLLOW-01** | 跟进页串商城/借阅口吻 | `_follow_role_copy_findings` | `test_follow_blocks_foreign_copy_and_needs_leads` | **已齐** |
| **R-FOLLOW-02** | 总管 vs 辅导员/专员 lead | `ensure_follow_role_leads`（INTERN/CRM/EVENT/ATTEND/FUND/RECRUIT/GRADE/LISTING）；待审页已挂 | `test_follow_role_leads_intern_crm_event` | **已齐** |

**follow 组已知未挡**：分级/分类口径归 lexicon（L3）；未知口语仍依赖 p3q/LLM；L5。**禁止**说「换开题都没事了」。

### 4.6 approve（审批/填报）

| id | 洞 | 收法 | 闸 / 测 | 状态 |
|----|----|------|---------|------|
| **R-APPROVE-01** | 审批页串商城/借阅口吻 | `_approve_role_copy_findings` | `test_approve_blocks_foreign_copy_and_needs_leads` | **已齐** |
| **R-APPROVE-02** | 总管 vs 承办岗 lead | `ensure_approve_role_leads`（SEAL/EXPENSE 等 23 域）；待审页已挂 | `test_approve_role_leads_seal_expense` | **已齐** |

**approve 组已知未挡**：未知口语仍依赖 p3q/LLM；L5。**禁止**说「换开题都没事了」。

### 4.7 apply（报名/申请）

| id | 洞 | 收法 | 闸 / 测 | 状态 |
|----|----|------|---------|------|
| **R-APPLY-01** | 报名页串商城/借阅口吻 | `_apply_role_copy_findings` | `test_apply_blocks_foreign_copy_and_needs_leads` | **已齐** |
| **R-APPLY-02** | 总管 vs 助理 lead | `ensure_apply_role_leads`（ACTIVITY/LOST/COURSE/TOUR）；待审页已挂 | `test_apply_role_leads_activity_course` | **已齐** |

**apply 组已知未挡**：未知口语仍依赖 p3q/LLM；L5。**禁止**说「换开题都没事了」。

### 4.8 content（内容/媒资/社区）

| id | 洞 | 收法 | 闸 / 测 | 状态 |
|----|----|------|---------|------|
| **R-CONTENT-01** | 内容页串商城/借阅/报名口吻 | `_content_role_copy_findings` | `test_content_blocks_foreign_copy_and_needs_leads` | **已齐** |
| **R-CONTENT-02** | 站长审核下架 vs 版主/运营 lead | `ensure_content_role_leads`（FORUM/MEDIA/MUSIC/BLOG/DOCLIB）；待审页已挂 | `test_content_role_leads_forum_media` | **已齐** |

**content 组已知未挡**：MEDIA 等无岗位域 lead 已预置但闸仅在有 `staff_posts` 时强检；作者编辑 vs 站长下架口语长尾仍依赖 p3q/LLM；L5。**禁止**说「换开题都没事了」。

### 4.9 interact（互动/匹配）

| id | 洞 | 收法 | 闸 / 测 | 状态 |
|----|----|------|---------|------|
| **R-INTERACT-01** | 互动页串商城/借阅/报名口吻 | `_interact_role_copy_findings` | `test_interact_blocks_foreign_copy_and_needs_leads` | **已齐** |
| **R-INTERACT-02** | 总管 vs 一线（联谊/秘书/对接/核销）lead | `ensure_interact_role_leads`（9 域）；待审页已挂 | `test_interact_role_leads_dating_survey` | **已齐** |

**interact 组已知未挡**：EXAM/SURVEY/VOTE 无岗位域 lead 已预置但闸仅在有 `staff_posts` 时强检；「未挂能力勿宣称」仍靠既有诚实闸 + p3q；L5。**禁止**说「换开题都没事了」。

### 4.10 fallback（兜底）

| id | 洞 | 收法 | 闸 / 测 | 状态 |
|----|----|------|---------|------|
| **R-FALLBACK-01** | 交易壳公告「管理员确认发货」= 总管串一线；lead 串借阅/报修等行业口吻 | `notice_body` 改办理员履约；`_fallback_role_copy_findings` 挡总管发货与行业专名 | `test_fallback_blocks_admin_ship_and_needs_leads` | **已齐** |
| **R-FALLBACK-02** | FLOW/TRADE/RESERVE 有岗位却缺 Admin/Staff lead | `ensure_fallback_role_leads`（按实体路径拆 tickets*/orders*/reservations*）；`finalize_generic_schema` 出口挂 | `test_fallback_role_leads_generic_paths` | **已齐** |

**fallback 组已知未挡**：错绑开题另案；CRUD 空岗不强制 lead；未知口语仍依赖 p3q/LLM；L5。**禁止**说「换开题都没事了」。

---

## 5. 共享落点（改之前先搜）

| 事 | 家 |
|----|----|
| 多店/商城壳 labels | `backend/app/bake/schema/builders_slot.py` |
| 提案角色模块树 | `backend/app/bake/proposal_role_modules.py` |
| 交付质量结构闸 | `backend/app/llm/agents_qa.py` → `_structural_findings` |
| 跨域词 / 口径分叉 | `backend/app/bake/domain_vocab.py`（L3；与本册 L4 互补） |
| 组与金丝雀 | `backend/app/bake/domains.py` |
| 门禁键 | 出包 `p3q`「交付质量摘要」 |

---

## 6. 与邻册边界

| 册 | 分工 |
|----|------|
| 本册 §0 | **换开题抗性总账**（L0～L7）；防低估 |
| [`surface-lexicon-design.md`](./surface-lexicon-design.md) | L3 槽位用词、跨域招牌词 |
| [`delivery-audit-rules.md`](./delivery-audit-rules.md) | 怎么审、小卡、旧题回归；不替代本册加固 |
| [`staff-posts-cross-domain.md`](./staff-posts-cross-domain.md) | 岗位↔界面；本册偏可见文案角色边界 |
| 各组 `*-thicken-batch.md` | L1 功能四件套；**已收口 ≠ L4/L5 已收口** |
| [`cohort-opening-title-map.md`](./cohort-opening-title-map.md) | 年题方向；不保证抗性 |

---

## 7. 汇报模板（一组收完）

- 组：gid；探针 canary + 邻域  
- 清了哪些 id；结构闸函数/正则一句话  
- 测：命令与通过数  
- 是否需要旧包重 bake（吃过错误文案的题）  
- **已知未挡**：（必填；可写「未知口语仍依赖 p3q/LLM」）  
- 下一组：gid  
- **禁止**写「这组以后换开题都没事了」  
