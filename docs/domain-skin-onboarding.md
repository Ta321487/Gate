# 域与皮接入清单（同步改哪里）

> **本文只负责**：新增 / 修改 **具名域（`DOM-*`）** 与 **同壳皮（kind / niche / deep skin）** 时，必须同步改到的落点与验收；同一套工序，域是域、皮是皮。  
> **不负责**：域默认能力表正文（[`domains.md`](./domains.md)）；换皮 ID 进度册（[`domain-skin-gap-analysis.md`](./domain-skin-gap-analysis.md)）；怎么审交付（[`delivery-audit-rules.md`](./delivery-audit-rules.md)）；cap 挂载细则（[`capabilities.md`](./capabilities.md)）。  
> **纪律**：改工厂登记表与 bake，**禁止**只擦当面学生 ZIP。  
> **索引**：[README.md](./README.md) · [`domains.md`](./domains.md) 换皮纪律 A/B/C · [`delivery-audit-rules.md`](./delivery-audit-rules.md) §5。

---

## 0. 先判：域还是皮？

| 问 | 答「是」→ | 答「否」→ |
|----|-----------|-----------|
| 现有某个 `DOM-*` 的主流程（借还 / 报修 / 下单 / 约时段 / 跟进单…）能否盖住本题？ | **皮**（挂靠该域，换文案/种子/kind） | 继续 |
| 是否需要**另一套**默认能力组合、表位、状态机或菜单主路径？ | **新域**（新 `DOM-*`，薄壳；禁止新开厚 overlay 包） | 优先深皮或扫词挂既有 cap |
| 是否只是商城换分类/SKU、预约换眉标、考试换题库说法？ | **皮 A/B**（见 §1） | 见 §1 C 或 §2 |

**默认**：能皮就皮。新域只在「同组共运行时也盖不住主流程」时开。  
**禁止**：为单题另起平行逻辑 / 第二套开关 / 在 `builders_*` 里散落 `if niche/kind ==`。

```
开题题型
  ├─ 挂靠已有 DOM + 同壳换说法/种子     → §1 皮
  ├─ 新 DOM-*（新默认能力组合 / 主路径） → §2 域
  └─ 新玩法积木（新 cap / Store）       → capabilities.md（本文不展开）
```

---

## 1. 皮（Skin）

皮 = **不换 `DOM-*`**，在挂靠域上换可见面 / kind / 种子。  
分层真源与 [`domains.md`](./domains.md) **换皮纪律 A/B/C**、[`delivery-audit-rules.md`](./delivery-audit-rules.md) §5.1 对齐。

### 1.1 皮怎么选层

| 层 | 何时用 | 主落点 | 禁止 |
|----|--------|--------|------|
| **A 软货架** | 商城等同壳换分类 / 文案 / SKU / 多店名 | `backend/app/bake/shop_retail_niches.py` | 在 `builders_slot` 写 `niche ==` |
| **B 同壳标签** | 预约 / 内容 / 医院等换眉标·角色名·名词 | `schema/kind_label_packs.py`；CRM 深皮 → `schema/deep_skin_overrides.py` | builder 内 `if kind == 新皮` |
| **C 换表/种子** | 同域种子 SQL 形态随场景变（EQUIP 分类物、EVENT 场景等） | `sql/domain_scene_seed.py`、`event_scene_seed.py`、`content_scene_overlays` / `reserve_scene_overlays`；各域 seed blob | 只改 rules 不改 seed（或反过来） |
| **结构皮（跟进族等）** | 档案字段 / 菜单 / banner 覆盖包随挂靠叙事变深 | `schema/*_followup_presets.py`、`deep_skin_overrides.py`；辅 `ticket_copy_text.py` | 只改一个 builder、其它可见面仍旧题腔 |
| **考试 / 内容专项** | 题库党建/安全等；论坛影视等 `_apply_*_skin` | `features/exam.py`（`exam_skin`）；`features/content_thicken.py` | 新开 DOM 冒充换皮 |

### 1.2 新增皮（清单）

同一条皮按下表勾；**rules / pack / seed 同到**。

| # | 必改 | 路径 / 动作 |
|---|------|-------------|
| P1 | **扫词 rules** | `scene_scan.py` 对应 `*_KIND_RULES`（或 `shop_retail_niches` 的 `hints`）——命中才出 kind/niche |
| P2 | **标签 / pack** | A：`RetailNichePack` 一条；B：`kind_label_packs` 一条；CRM：`deep_skin_overrides`；考试：`exam_skin` 文案+种子 |
| P3 | **种子 / overlay**（若本层会换演示数据） | `domain_scene_seed` / `event_scene_seed` / content·reserve overlays；C 层必做 |
| P4 | **话术占位**（跟进/单据壳） | `ticket_copy_text` + preset 只用 `{category_axis}` / `{ticket_noun}` 等占位，勿写死邻域词 |
| P5 | **样例开题**（建议） | `proposal_packs_data/<挂靠域或 niche>.json`；新文件须进 `_order.json` |
| P6 | **易混对**（与邻域互抢时） | `domain-skin-gap-analysis.md` 补 M/S 行；双侧 `match_hint`；`test_confusion_pairs` 或专测 |
| P7 | **清单状态** | `domain-skin-gap-analysis.md` 对应 S/P 行：`待补`→收口后 `已齐` |
| P8 | **专属词门禁**（新行业专名词） | `domain_vocab.py` 必要时登记归属域，防串台 |
| P9 | **AI 助手岛**（开题开了助手） | `resolve_ai_knowledge_skin` 角色/FAQ 种子跟皮；见 [`ai-assistant-delivery.md`](./ai-assistant-delivery.md) |
| P10 | **测试** | 至少：命中 kind/niche 的单测；A 层 niche pack 测；易混对测。跑绿再标已齐 |

**收工自检（皮）**

- [ ] 开题正句 → 仍落**同一** `DOM-*`，kind/niche 正确  
- [ ] 邻域旧题不被新 hints 抢走  
- [ ] 界面眉标 / 角色名 / 种子 / 空态无邻域穿帮  
- [ ] 未改当面 ZIP；未在 builder 加 `if niche/kind ==`

### 1.3 修改已有皮（清单）

| 改什么 | 同步改 |
|--------|--------|
| 扫词 hints / KIND_RULES | 对应 pack 是否仍匹配；易混对与 `match_hint`；相关 pytest |
| pack 文案（眉标/角色/SKU） | 种子公告是否仍同腔；`proposal_packs` 样例；学生可见文案禁工厂腔 |
| 种子 SQL / overlay | rules 是否仍指向该种；演示主路径能走通 |
| 深皮字段覆盖 | `FOLLOWUP_PRESETS` / `deep_skin_overrides` 与 `builders_*` 读取点；`ticket_copy_text` |
| 删皮 / 改 id | 全仓搜旧 id（rules、pack、seed、测、清单册）；禁止留死 kind |

修改皮**不必**动 `DOMAIN_CAPABILITIES` / `DOMAIN_GROUPS`（那是域轴）。若发现「改皮不够、必须改默认能力」→ 升级为 §2 改域或挂 cap，不要把 cap 偷塞进皮 pack。

---

## 2. 域（Domain）

域 = 新的或改动的 **`DOM-*`**：匹配目录、默认能力、schema 组装、分组与文档台账。  
**薄壳**：不另起 `skeletons/domains` 厚包（`DOMAINS_WITH_OVERLAY` 须保持空策略）。

### 2.1 新增域（清单）

按顺序做；漏一项 = 匹配有、出包穿帮或控制台找不到。

#### A. 匹配与目录（材料 → 命中）

| # | 必改 | 路径 / 动作 |
|---|------|-------------|
| D1 | **catalog 条目** | `backend/app/bake/domains_catalog/<组文件>.py`：`label` / `keywords`（词表预算紧）/ `match_hint` / `entities` / `roles` / `flows` / `features` / `out_of_mvp` / `themes` / `gate` / `runtime` |
| D2 | **catalog 合并** | `domains_catalog/__init__.py` 已 import 并入 `CATALOG_DOMAINS`（新文件才加 import） |
| D3 | **默认能力** | `domains.py` → `DOMAIN_CAPABILITIES["DOM-…"]`；能力 id 必须已在 [`capabilities.md`](./capabilities.md) / `capabilities.py` 可交付 |
| D4 | **控制台分组** | `domains.py` → `DOMAIN_GROUPS` 某一组的成员元组；未知域会掉进 `fallback` |
| D5 | **借用族表预算**（若属借用/占用薄壳加厚口径） | `BORROW_FAMILY_DOMAINS` 是否纳入 |
| D6 | **文档域表** | [`domains.md`](./domains.md) 对应组表加一行（能力组合与代码一致） |

#### B. Schema 与可见面（命中 → 可 bake）

| # | 必改 | 路径 / 动作 |
|---|------|-------------|
| D7 | **SCHEMA_BUILDERS** | `schema/templates.py` 登记 builder；跟进壳优先 `followup_builder` + preset，勿复制整份 archive builder |
| D8 | **结构预设**（跟进/审批/报名等同构） | 对应 `schema/*_followup_presets.py`，并在 `followup_presets.py` `FOLLOWUP_PRESETS.update(...)` |
| D9 | **专用 builder**（交易/预约/内容/考试等） | `builders_slot` / `builders_archive` / `builders_ticket` / `builders_content` 等**既有**组装函数；禁止为单域在 slot 里堆 niche 分支 |
| D10 | **资料字段** | `profile_fields.py` → `PROFILE_FIELDS_BY_DOMAIN`；与 `scene_scan` 场景一致 |
| D11 | **岗位**（需要办理岗时） | `staff_posts.py` 域默认 packs；跨域岗位纪律见 [`staff-posts-cross-domain.md`](./staff-posts-cross-domain.md) |
| D12 | **场景扫词**（壳身份） | `scene_scan.py`：校园/企业/社区只走此处；勿在 shells 另写一套 hint |
| D13 | **种子** | `sql/domain_scene_seed.py`（及组内 overlay）；演示主路径有数据 |
| D14 | **样例开题包** | `proposal_packs_data/<id>.json` + `_order.json` |
| D15 | **跨域词** | `domain_vocab.py`：本域专属词登记，避免出包串台 error 漏拦 |

#### C. 门禁、台账、回归（可交 → 可审）

| # | 必改 | 路径 / 动作 |
|---|------|-------------|
| D16 | **开题对齐**（该组有 thicken/对齐表时） | 组内 A 白名单 / B 扫词 / C cap 规则与 bake 同条件；见 [`opening-align-gate.md`](./opening-align-gate.md) |
| D17 | **换皮/预设清单** | [`domain-skin-gap-analysis.md`](./domain-skin-gap-analysis.md) 新预设行（落点=新预设） |
| D18 | **密功能地图**（若有域默认可演示点） | [`opening-feature-delivery-map.md`](./opening-feature-delivery-map.md) 挂载列写清域默认 / 扫词开 |
| D19 | **UI 诊断台账** | [`ui-domain-diagnosis.md`](./ui-domain-diagnosis.md) 加域行（L/C；新域先空红再诊） |
| D20 | **组 UI 表面**（新表面才动） | [`domain-group-ui-styles.md`](./domain-group-ui-styles.md) / [`ui-look-thicken-batch.md`](./ui-look-thicken-batch.md)——优先复用组内已有 surface |
| D21 | **旧题回归代表** | 一般**不**改 `AUDIT_GROUP_CANARIES`（每组一条代表已定）；新域用交付审计「本轮触点域」抽检。仅当新开**新组**时才扩 canary |
| D22 | **测试** | catalog/match 命中；schema smoke；易混对；组 thicken/特征测（若动到）；`test_sample_proposal_match` 等相关 |

**收工自检（域）**

- [ ] 正句开题 → 本域；旧题仍旧域（尤其易混对）  
- [ ] `DOMAIN_CAPABILITIES` ⊆ 已实现 cap；bake 主路径可点、可写库  
- [ ] 控制台级联能选到；`domains.md` 与代码一致  
- [ ] 无厚 overlay；无只改 ZIP  

### 2.2 修改已有域（清单）

按「改动轴」勾同步面；**改匹配词 ≠ 只改文档**。

| 改动轴 | 必同步 |
|--------|--------|
| **keywords / match_hint** | catalog 文件；易混对双侧 hint；`domain-skin-gap-analysis` M 行；confusion / 专测；必要时 `domain_vocab` |
| **DOMAIN_CAPABILITIES**（增删默认 cap） | [`domains.md`](./domains.md)；地图挂载列；`ensure_*` / 菜单 / 三套 Store 是否已覆盖该 cap；开题对齐 C 档；表数预算（借用族） |
| **runtime / gate / 表位** | catalog `runtime`/`gate`；`runtime_policy` / SQL fragments 是否假定旧表名；种子 |
| **schema 文案 / 字段 / 菜单** | builder 或 `FOLLOWUP_PRESETS`；`profile_fields`；`ticket_copy_text`；种子；样例开题 |
| **换组（DOMAIN_GROUPS）** | 控制台级联；组 thicken / 对齐规则是否仍适用；UI 组表面；审计时邻域抽样 |
| **改名 / 弃用 DOM id** | **极重**：全仓 `DOM-旧`、proposal packs、清单册、诊断台账、测例；优先不改 id，只改 label/keywords |
| **只改文档** | 禁止与 `DOMAIN_CAPABILITIES` / catalog 长期双口径；冲突时改代码真源再回写文档 |

---

## 3. 文档与台账（域、皮收工都可能碰）

| 文档 | 新域 | 新皮 | 备注 |
|------|:----:|:----:|------|
| [`domains.md`](./domains.md) | ✓ | 罕（仅纪律/说明） | 能力组合真源之一 |
| [`domain-skin-gap-analysis.md`](./domain-skin-gap-analysis.md) | ✓ 新预设行 | ✓ S/P/M | 状态列 |
| [`opening-feature-delivery-map.md`](./opening-feature-delivery-map.md) | 按需 | 按需 | 密功能落点 |
| [`ui-domain-diagnosis.md`](./ui-domain-diagnosis.md) | ✓ | — | 按 `DOMAIN_CAPABILITIES` 域行 |
| [`delivery-audit-rules.md`](./delivery-audit-rules.md) | 审计时用 | 审计时用 | 不代替本清单施工 |
| [`cohort-opening-title-map.md`](./cohort-opening-title-map.md) | 可选 | 可选 | 今年题名映射；≠ 产品能力 |
| 本组 `*_thicken` / 对齐规则 | 维护既有 | 罕 | **禁止**再新开 thicken 模块 |

---

## 4. 建议验收命令（按改动面裁剪）

```text
# 匹配 / 样例开题
cd backend
.\.venv\Scripts\python.exe -m pytest -q tests\test_sample_proposal_match.py

# 易混对（改了 keywords / 皮 hints 时）
.\.venv\Scripts\python.exe -m pytest -q tests\test_confusion_pairs.py

# 开题对齐（动了扫词挂载 / thicken 键）
.\.venv\Scripts\python.exe -m pytest -q tests\test_opening_align_gate.py

# 皮穿帮 / 域串台（按需）
.\.venv\Scripts\python.exe -m pytest -q tests\test_domain_skin_leak.py
```

专域探针（例）：`test_carrent_p32` / `test_tour_p31` / 各组 `test_*_thicken_features.py`——**有专测就跑专测**，勿默认全仓。

交付审计轮：只出报告时走 [`delivery-audit-rules.md`](./delivery-audit-rules.md)；旧题回归用 `AUDIT_GROUP_CANARIES` + 本轮触点域。

---

## 5. 绝对不要

- 新开厚 DOM 包或 `skeletons/domains` overlay「专线」。  
- 只改当前选题 ZIP / 单套 Store。  
- 皮逻辑写进 builder 的 `if niche/kind ==`（应进登记表）。  
- 域与皮两套口径：文档已写「已齐」、代码无 pack/rules/seed。  
- 用 `ARCH-*` 或技术栈轴代替 `DOM-*` 匹配。  
- 把场景轴（校园/企业）写进 shells 旁路，绕开 `scene_scan`。  
- 为消红跳过匹配互抢与串台词门禁。

---

## 6. 与其它文档分工

| 需求 | 去哪 |
|------|------|
| **施工：改哪些文件** | **本文** |
| 查域默认能力 / 分组 | [`domains.md`](./domains.md) |
| 换皮 ID 是否已齐 | [`domain-skin-gap-analysis.md`](./domain-skin-gap-analysis.md) |
| 审交付红灯 / 老板小卡 | [`delivery-audit-rules.md`](./delivery-audit-rules.md) |
| 新能力岛 / cap | [`capabilities.md`](./capabilities.md) |
| 开题开关双向登记 | [`opening-align-gate.md`](./opening-align-gate.md) |

---

## 7. 修订记录

| 日期 | 说明 |
|------|------|
| 2026-11-14 | 首版：域/皮分列新增与修改清单；挂 docs 索引 |
