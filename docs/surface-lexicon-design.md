# 话术层（Surface Lexicon）设计方案

> **状态：设计稿，待评审**（本次未改任何代码）
> 触发事件：`gate_e2e` 交付质量摘要连续两轮 fail
> 关联：`docs/delivery-audit-rules.md`、`docs/domain-skin-gap-analysis.md`、`docs/domains.md`
> 实现位置（现网）：`backend/app/services/delivery_review.py`

---

## 0. 硬性要求（追加，覆盖本方案全部批次）

> 需求方明确：**所有域都得吃到此次变更；修复后不可以再次出现同样问题。**
> 这两条是验收前提，任何"只修可见文案"或"逐域打补丁"的做法都不满足。

### 0.1 全域覆盖（禁止逐域补丁）

变更必须落在**全域共用 choke point**，只让个别域受益的写法一律不接受：

1. `backend/app/bake/schema/followup_presets.py::followup_domain_schema()` —— **所有具名域的 schema 总装点**（改这里即全域生效）；
2. `backend/app/bake/schema/builders_archive.py` 的域/场景 override 汇聚点（本次两案发源处）；
3. schema 发射与产物写入链路（`app/bake/engine_islands.py::emit_schema_to_workspace`）；
4. `backend/app/bake/sql/domain_scene_seed.py` 的**种子公告**生成（口径分叉的第三方）。

**验收**：对 `proposal_packs_data/*.json` **全部 74 个域包**批量 bake，断言
① 产物可见文案对"域专属名词表"**零命中**；② 同一 slot（如 `category_axis`）**零口径分叉**。**必须脚本化全量跑，不接受抽样**。

### 0.2 不可复发（门禁必须能自动拦）

- 批 C 的跨域词门禁与 A/B **同批次上线**，等级为 **`error`（阻断交付）**，不接受 `warn`；
- 门禁必须**数据驱动、覆盖全部域**（"专属名词 → 归属域"表 + 反向 forbidden 下发），禁止逐个 case 硬编码；
- **验收（反例必红）**：
  1. 向 EVENT 产物注入「打卡」→ gate 必须 `error`；
  2. 向 CRM 产物注入「分类标签」（与实体「客户分级」分叉）→ gate 必须 `error`；
  3. 现有全部域包产物 → gate 保持绿（零回归）。

### 0.3 对 §11 待拍板问题的结论（由本节覆盖）

- 问题 4（门禁等级）→ **`error`**；
- 问题 5（顺序）→ **A/B/C 必须同批交付**，不允许"先修文案、门禁以后补"。


## 1. 触发事件与证据

| # | gate 报错 | 证据位置（实测） |
|---|---|---|
| 1 | CRM：种子公告与提案称「**分类标签**」，实体 `label/labelPlural` 为「**客户分级**」，门户 banner 又写「**按分级浏览客户**」，三处口径不统一 | ① 开题正文 `backend/app/bake/proposal_packs_data/crm.json:11`；② 实体分类轴名 `backend/app/bake/schema/builders_archive.py:449`；③ banner 同文件 `:457` |
| 2 | EVENT：用户端「上报」列表空状态写「还没有**打卡**记录，点击右上角提交。」，「打卡」属考勤域用语 | `backend/app/bake/schema/builders_archive.py:483`（`_event_self_report_overrides()`，同函数 `:470-490` 的 doc / `archive_menu_user` / `my_tickets_label` / banners 亦全为「打卡」） |

**共同点**：同一语义（分类轴 / 单据名词）在**多处各自硬编码话术**，且触发场景与话术归属域不一致。

> 用户提出的关键问题：**"将来的开题材料是这个意思、但话术不是这个，该如何解决？"**
> 本文档的核心回答：把「语义」和「话术」彻底分层，话术只从**开题材料 + 域词表**解析，不再手写。

---

## 2. 问题本质

系统现在把「意思」和「说法」混在一起：

- **语义**（已有雏形）：category 轴、ticket 单据、archive 档案 —— `_std_archive_fields(第 6 参数)`、`my_tickets_label`、`banners` 本身都是槽位；
- **话术**（到处手写，无单一来源）：客户分级 / 分类标签 / 评级；上报 / 打卡 / 填报。

`backend/app/bake/proposal_lexicon.py` 已有 `keyword_mentioned` / `pattern_mentioned`，被 40+ 个 `features/*.py` 引用 —— 但它**只用于判断"能力是否开启"，从未用于决定"文案怎么写"**。缺的就是这一层。

### 2.1 现有话术来源盘点（实测统计）

| 编号 | 来源 | 实测规模 | 例子 |
|---|---|---|---|
| ① | 域/场景 schema override | `"banners":` 出现在 **12** 个文件：`schema/builders_archive.py`(22 处)、`followup_presets.py`(10)、`oa_followup_presets.py`(8)、`tail_followup_presets.py`(8)、`stuwork_followup_presets.py`(5)、`deep_skin_overrides.py`(3)、`mutual_followup_presets.py`(3)、`bed/checkin/carpool/instrument/timebank_followup_presets.py`(各 1) | 「按分级浏览客户」 |
| ② | 单据页文案槽位 | `my_tickets_label/empty/page_lead` 出现在 **13+** 文件：`followup_presets.py`(18 处)、`builders_archive.py`(14)、`oa_followup_presets.py`(8)、`builders_ticket.py`(7)、`form_first_entry.py`(5)、`checkin_followup_presets.py`(3)、`deep_skin_overrides.py`(3)、`mutual_followup_presets.py`(3)、`bed/carpool/instrument_followup_presets.py`(各 1)、`builders_content.py`(1) | 「还没有打卡记录…」 |
| ③ | 开题样例正文 | `backend/app/bake/proposal_packs_data/*.json` 共 **74** 个域包（`value` 字段即开题正文） | 「客户档案、**分类标签**、跟进提交…」 |
| ④ | 场景种子 / 覆盖 | `sql/domain_scene_seed.py`(**145 KB**)、`sql/event_scene_seed.py`、`sql/content_scene_overlays.py`、`sql/reserve_scene_overlays.py` | 种子公告正文 |
| ⑤ | 前端硬编码空状态 | `skeletons/baseline/frontend/src` 中「还没有」类文案 **12+** 页（`views/admin/*.vue` 等） | 「还没有…」 |

### 2.2 已有机制盘点（先纠正定位：本方案是**补缺口**，不是新建一套）

| 已有模块 | 职责 | 与本方案的关系 |
|---|---|---|
| `backend/app/bake/ticket_copy_text.py` | 单据/档案提示文案：**bake 期参数化生成 → 写 `domain-ticket-copy.json` + schema → 运行时只读**；已按词分派（`sibling_reject_tip(archive_label, apply_verb)` → 「已借完/名额已满/已无法再申请」） | **就是"话术层"的既有雏形，应扩展它**（批 B 落点从"新建 surface_lexicon.py"改为"以本模块为主干 + 新增 slot 解析"） |
| `backend/app/bake/schema/er_zh.py` + `er_labels.py` | 表/列 → 中文标签词表（`_COMMON_COL_ZH` / `_TABLE_PART_ZH` / `_COL_SUFFIX_RULES` / `_STEM_ZH`） | 已提供**实体/字段级**单一来源；本方案补的是**页面级**（`banners`/`doc`/`auth_lead`/`my_tickets_*`/种子公告） |
| `backend/app/bake/proposal_lexicon.py` | 扫词表（`keyword_mentioned` / `pattern_mentioned`） | 已有语义→词底座；本方案**并列新增"说话术"用途**，不替换 |
| `backend/app/services/student_copy.py` | 出包后清洗学生可见"工厂腔" + `refresh_polluted_vue_from_baseline` | 上位防线；本方案让"生成期就不脏"，减少事后清洗 |
| `backend/app/services/delivery_review.py` | 交付质量摘要 gate（本次两条 fail 即它报出） | 现为**事后**比对；批 C 在它内部增设**事前可约束**的跨域词检查 |
| `docs/delivery-audit-rules.md` v5.3 | 规则文档：**开题优先**、「状态机…按钮文案一致」、红灯表 | 规则已存在；本方案把它从"功能取舍层"落到**文案层** |

**因此本方案真正的新增只有 4 项（其余皆为对齐既有机制）：**

1. **页面级话术**（`banners` / `doc` / `auth_lead` / `my_tickets_*` / 种子公告）目前**无集中来源**，散落在 `schema/*.py` 的字面量里（§2.1 ①②）；
2. **各机制之间不共享同一域词表**：`er_zh` 的词、域 override 的分类轴名、开题正文的用词，三者各写各的 → 直接产出本案例 #1；
3. **"开题优先"只落在功能取舍，未落到话术**：文案始终用域默认，忽略开题实际用词（如开题写"上报"仍出"打卡"）→ 本案例 #2；
4. **门禁只能事后字符串比对**，无事前词表约束。

> 修正后的落点：批 B **以 `ticket_copy_text.py` 为主干扩展**（新增 slot 解析并统一供值），仅当其承载不下时才新建 `surface_lexicon.py`；§5/§8 的"新增文件"应据此重读。


---

## 3. 目标与非目标

**目标**

1. 同一语义实体在**所有**可见位置只有一个话术来源（物理同一个值）。
2. 开题材料用不同话术表达同一语义时，系统**跟随开题用词**（既不回退域默认，也不串到别的域）。
3. 跨域串词可被**自动拦截**（把这次的 error 从"事后发现"变成"事前预防"）。

**非目标**

- 不改状态机、不改能力开关语义、不引入 LLM 依赖（纯词表 + 规则）。
- 不改 `TABLE_COUNT_MIN/MAX/HARD` 配额、不改 ticket 四层结构与 `fragments.py` 片段机制。
- 不追求"自动理解任意自然语言"，只处理**同义簇内**的用词差异。

---

## 4. L1：语义槽位字典（slot 清单）

| slot | 含义 | 现值示例 | 现有承载位 |
|---|---|---|---|
| `entity_label` / `entity_plural` | 主实体名 | 客户 | schema `label` / `labelPlural` |
| `category_axis` | 分类轴名 | 客户分级 | `_std_archive_fields` 第 6 参 / `archive_fields[5]` |
| `category_values` | 分类取值 | 线索/意向/成交/搁置 | `_std_archive_fields` 第 5 参 |
| `ticket_noun` | 单据名词 | 上报 / 打卡 / 跟进 / 申请 | `my_tickets_label`、`doc`、`auth_lead` |
| `empty_state` | 列表空状态 | 还没有上报记录，点击右上角提交。 | `my_tickets_empty` |
| `list_lead` | 列表页导语 | — | `my_tickets_page_lead` |
| `banner_*` | 门户 banner | 按分级浏览客户 | `banners[]` |
| `seed_notice` | 种子公告正文 | — | ④ 场景种子 |
| `menu_*` | 菜单名 | 我的跟进 / 打卡说明 | `archive_menu_user` 等 |
| `button_*` | 按钮文案 | 提交上报 | 前端 |

---

## 5. L2：话术解析层 `surface_lexicon.py`

新增 `backend/app/bake/surface_lexicon.py`。

### 5.1 接口

```python
def lex(slot: str, *, domain: str, proposal_text: str = "", fallback: str = "") -> str
def lex_all(slots: list[str], *, domain: str, proposal_text: str) -> dict[str, str]  # 一次求值 → schema["lex"]
```

### 5.2 解析优先级（四条，逐级回退）

1. **开题抽取**：按 `SLOT_PATTERNS[slot]` 从 `proposal_text` 取词，且该词须落在本域 `DOMAIN_LEXICON[domain][slot]` 允许集内；
2. **域词表**：`DOMAIN_LEXICON[domain][slot]` 首选值；
3. **域默认**：schema override 显式给的值（即老逻辑，保证向后兼容）；
4. **通用兜底**：`fallback`（如「分类」/「记录」）。

判定规则：**开题命中即用开题词**；抽不到或不合法 → 逐级回退。这样"开题换词"无需改代码，词表外的新词只补一次词表。

### 5.3 同义簇草案（`SLOT_PATTERNS`）

| slot | 同义簇（正则） | 效果 |
|---|---|---|
| `category_axis` | `分级\|等级\|评级\|星级\|档位\|标签\|类目\|分类\|类别` | 开题写「评级」→ 全程「评级」；写「客户分级」→ 全程「客户分级」 |
| `ticket_noun` | `上报\|填报\|打卡\|申报\|申请\|报修\|登记\|诉求\|预约` | 开题写「上报」→ 产物中不出现「打卡」 |
| `entity_label` | 由域包标题/实体词抽取 | 受 §6 合法性校验约束 |
| `empty_state` | **不抽词**，由 `ticket_noun` 模板化：`还没有{ticket_noun}记录，点击右上角提交。` | **直接修掉本案例 #2**，且无需为每个场景写 override |

> 说明：`empty_state` / `list_lead` / `menu_*` / `button_*` 这类**句式槽位**走模板化（参数化 `ticket_noun`），只有名词槽位才走抽词。

### 5.4 域词表草案（`DOMAIN_LEXICON`，节选）

| domain | `entity_label` | `category_axis` | `ticket_noun` | 备注 |
|---|---|---|---|---|
| DOM-CRM | 客户 | 客户分级 | 跟进 | 本案例 #1：三处统一为「客户分级」 |
| DOM-EVENT | 事件/事项 | 事件分类 | 上报 | self_report 皮由开题决定是否用「打卡」 |
| DOM-ATTEND | 考勤记录 | 出勤状态 | 打卡 | 「打卡」仅在**本域**合法 |
| DOM-FUND | 困难生 | 资助等级 | 申请 | 公示/发放台账沿用 |
| DOM-LISTING | 房源 | 房源类型 | 发布 | 成交台账 |
| DOM-RECRUIT | 岗位 | 岗位类别 | 投递 | 两级审 |
| DOM-GRADE | 成绩 | 课程类别 | 登记 | 改分留痕 |
| DOM-INTERN | 实习周报 | 实习类别 | 填报 | 周次 |

> 74 个域包的**全量表**在实施批 B 时由 `proposal_packs_data/*.json` + 域包 label 脚本生成初稿，再人工复核一次。

---

## 6. L3：一致性渲染（消除"三处分叉"）

1. `followup_domain_schema()` 中**一次性**求值 `lex_all(...)` 并写入 `schema["lex"]`；
2. 所有消费点只读 `schema["lex"]`，**禁止再写字面量**：`doc`、种子公告、`banners`、`label`/`labelPlural`、`archive_fields`（尤其分类轴名与取值）、`my_tickets_label/page_lead/empty`、`archive_menu_user`、前端空状态；
3. 前端 ⑤ 类硬编码空状态改为读 schema（`MyTickets.vue` 已有"标签读 schema.labels"的先例，按同法推广到其它页）；
4. `_std_archive_fields(..., 分类轴名, ...)` 的调用点改为传 `schema["lex"]["category_axis"]`。

**验收断言**：任意域产物中，`category_axis` 的字符串在 **doc / banner / 实体分类字段** 三处**逐字相同**。

---

## 7. C：跨域词门禁（`domain_vocab.py`）

新增 `backend/app/bake/domain_vocab.py`：

```python
DOMAIN_VOCAB = {
    # forbidden = 其它域的"招牌词"，本域产物不得出现
    "DOM-ATTEND": {"forbidden": ["借阅", "挂号", "房源", "下单", "选课"]},
    "DOM-EVENT":  {"forbidden": ["借阅", "挂号", "下单", "选课", "排课"]},
    "DOM-CRM":    {"forbidden": ["打卡", "借阅", "挂号"]},
    # ... 按域互斥下发
}
```

- **招牌词来源**：各域 `proposal_lexicon` 抽取词 + `proposal_packs_data/*.json` 域关键词，按域汇总后互斥下发（脚本生成初稿 + 人工复核）；
- **检查点**：`backend/app/services/delivery_review.py` 现有检查函数旁新增 `_check_cross_domain_wording()`，扫描产物可见文案（`doc` / `banners` / 空状态 / 页面标题 / 菜单 / 种子公告），命中即报；
- **自测**：`backend/tests/test_delivery_review.py` 增加正例 + 反例各一（反例即本案例 #2 的「上报域出现打卡」）。

**效果**：把这次的 error 从"人肉发现"变成"门禁自动拦"，未来新开题、新场景皮只要串词就红。

---

## 8. 影响面清单

### 8.1 新增文件

| 文件 | 作用 | 规模估计 |
|---|---|---|
| `backend/app/bake/ticket_copy_text.py`（**优先扩展既有模块**；仅当承载不下才新建 `surface_lexicon.py`，见 §2.2） | L2 解析层（slot + 词表 + `lex`/`lex_all`） | 扩展 +~150 行 |
| `backend/app/bake/domain_vocab.py` | C 跨域词表 | ~150 行（脚本生成初稿） |
| `backend/tests/test_surface_lexicon.py` | 单测：优先级、同义簇、必不串词 | ~120 行 |
| `docs/surface-lexicon-design.md` | 本文档 | — |

### 8.2 改造文件（按 5 类来源）

| 来源 | 文件 | 改动 | 风险 |
|---|---|---|---|
| ① | `schema/builders_archive.py`（22 banner + 14 `my_tickets_*`） | banner 与实体字段改由 `lex()` 取值 | 中：场景皮多，需逐皮核对 |
| ① | `followup_presets.py`(18+10)、`oa_followup_presets.py`(8+8)、`tail_followup_presets.py`(8)、`stuwork_followup_presets.py`(5)、`deep_skin_overrides.py`(3)、`mutual_followup_presets.py`(3) | 同上 | 中 |
| ① | `bed` / `checkin` / `carpool` / `instrument` / `timebank_followup_presets.py`（各 1） | 同上 | 低 |
| ② | `builders_ticket.py`(7)、`form_first_entry.py`(5)、`builders_content.py`(1) | `my_tickets_*` 改模板化 | 中：单据页文案多 |
| ③ | `proposal_packs_data/*.json`（74 个，`value` 正文） | **不删词**，仅把与域词表冲突的词对齐（如 `crm.json:11`「分类标签」→「客户分级」；`event_report.json:11` 同款需核对） | 低但量大：需脚本比对清单 |
| ④ | `sql/domain_scene_seed.py`(**145 KB**)、`sql/event_scene_seed.py`、`content_scene_overlays.py`、`reserve_scene_overlays.py` | 种子公告正文改走 `lex()` | **高**：文件大、正文多处 |
| ⑤ | `skeletons/baseline/frontend/src/views/**`（12+ 处空状态）、`MyTickets.vue`；若有前端叠层则同步 | 空状态读 schema | 中：三栈/多包同步 |
| gate | `backend/app/services/delivery_review.py` + `backend/tests/test_delivery_review.py` | 新增跨域词检查 + 测试 | 低 |
| 认知 | goldens（`tests/golden/schema\|sql/DOM-*.json\|.sql`）、三栈编译抽测包 | 必然全量重生成 + 复编译 | 中 |

### 8.3 **不动**的部分（划清边界）

- `fragments.py` 片段机制、`ticket_columns.py`、表配额、状态机、能力开关语义；
- `proposal_lexicon.keyword_mentioned/pattern_mentioned`：保留"判能力"用途，**并列新增**"说话术"用途，不替换。

---

## 9. 落地步骤（三批，每批可独立验收）

### 批 A：修可见错文案（先转绿，最小改动）

1. **CRM 三处统一**：`crm.json:11` 正文对齐 → `builders_archive.py:449`（分类轴名）与 `:457`（banner）改从同一常量取值；
2. **EVENT 空状态**：`builders_archive.py:483` 改为 `还没有{ticket_noun}记录，点击右上角提交。`，由 `ticket_noun` 决定「上报 / 打卡」。

**验收**：`gate_e2e` 两条 fail 转绿；`backend/tests/test_delivery_review.py` 全绿。
**特点**：这是批 B 的特例（老写法打补丁），批 B 上线后会被 `lex()` 吸收。

### 批 B：建话术层（治本，回答"开题话术不同"）

1. 扩展 `backend/app/bake/ticket_copy_text.py` 为主干（slot + `DOMAIN_LEXICON` + `SLOT_PATTERNS` + `lex`/`lex_all`）；仅当其承载不下才新建 `surface_lexicon.py`（见 §2.2）；
2. `followup_domain_schema()` 写入 `schema["lex"]`；
3. ①② 两类来源（13+ 文件）改读 `schema["lex"]`；
4. ④⑤ 迁移（先低风险文件，145 KB 的 `domain_scene_seed.py` 最后单独一批）；
5. 重生成 goldens（`regen_sql_goldens.py` + `regen_schema_goldens.py`）+ 三栈编译抽测。

**验收**：`test_surface_lexicon.py` 全绿；随机 10 个域包产物中 `category_axis` 三处逐字一致；**新造一个"同义异词"开题**（如把「客户分级」写成「客户评级」）仍能全程自洽。

### 批 C：跨域门禁（防复发）

1. `domain_vocab.py` 生成初稿 + 人工复核；
2. `delivery_review` 增加 `_check_cross_domain_wording()`；
3. 用本案例 #2 构造反例测试。

**验收**：把「打卡」注入 EVENT 产物 → gate 必须报 error；现有全部域包产物 gate 保持绿。

---

## 10. 风险与取舍

| 风险 | 说明 | 缓解 |
|---|---|---|
| 开题抽词误判 | 同义词但语义不同（如「等级」实指权限等级） | 只接受本域允许集内的词；抽不到即逐级回退 |
| 词表膨胀 | 74 个域包 × 多个 slot | 表格化 + 生成脚本 + 一次性人工复核 |
| golden 全量重生成 | 话术改动会影响所有域 golden | 分批重生成 + diff 审查（只允许文案行变化） |
| 场景皮语义漂移 | `event_self_report()` 判定过宽是本次 #2 诱因 | 批 A 先修文案；批 B 让皮**只改槽位、不写跨域词** |
| 性能 | 每次 bake 多一次词表查找 | `lex_all` 一次求值 + 缓存进 schema，可忽略 |
| 覆盖不全 | ⑤ 前端与 ④ 种子体量大，一次改不完 | 批 C 门禁兜住（先 warn 后 error） |

---

## 11. 待拍板的问题（评审请逐条给结论）

1. ~~**CRM 统一到哪个词**~~ → **已定（需求方）：「客户分级」**；同批把 `crm.json:11` 正文的「分类标签」改为「客户分级」。
   附带（证据已核，**已修正**）：EVENT 域对应词以**域默认实体名**为准——`backend/tests/golden/schema/DOM-EVENT.json` 的 category 实体 `label/labelPlural` 为「**分类**」（L60/L61），而 `builders_archive.py:743/769/813/860` 的「事件分类」**只存在于部分场景皮**。故 `event_report.json:11` 的「分类标签」改为「**分类**」；「事件分类 vs 分类」的统一留给批 B 的 `lex()`。另：「事件等级」已被 `level`（低/中/高，`followup_presets.py:870-888`）占用，不可挪用。
2. **EVENT 的 self_report 判定**：`scene_scan.event_self_report()` 判据 = `EVENT_SELF_REPORT_HINTS` 词表命中（可用 `_path_override()` 给个别 pack 定死 self_report/caseload）。建议：**批 B 先做文案槽位化**（让串词机制上不可能），**收紧词表另起小批**并用 74 域包"皮命中矩阵 before/after"验证。（待确认）
3. **④ 场景种子（145 KB）**：建议 **公共模板同批迁移、域特有分支分批迁移、C 门禁同批上线**（"不可复发"由门禁保证，145 KB 一次性重构会放大 golden + 三栈回归风险）。（待确认）

---

## 12. 同源普查：库内 12 条 bake 失败（实测）

`jobs` 表 `bake`：failed **12** / success 15；`projects`：failed 5 / generated 7 / ready 1。原文导出见 `C:\Users\17386\AppData\Local\Temp\gf_bake_fail_reasons.txt`。

| 步骤 | 条数 | 判定 |
|---|---|---|
| `gate_e2e`（交付质量摘要） | **7** | **同源家族**（可见文案 / 可见面 vs 实体不一致） |
| `copy_bake`（生成期硬闸） | **5** | **不同源**（技术/配置类，话术层治不了） |

### 12.1 gate_e2e 7 条（同源家族）

| job | 症状 | 归属 |
|---|---|---|
| 1010 | 上报域空状态写「还没有打卡记录」 | **完全同源** → 批 B / C |
| 1009 | CRM「分类标签 / 客户分级 / 按分级浏览客户」三处不一致 | **完全同源** → 批 B / C |
| 1014 | `MyTickets.vue` 残留 `row.dueAt/dueLabel/row.qty`（借阅/商城字段）且不在 `allow*` 分支内，与 ticket（成绩申诉）实体不符 | **同族异因** → 需**新批 B2**（补 `allow*` 渲染分支） |
| 12 | 「我的借用」页残留「取书截止 / holdCountdown / `hold_ready`」，而 `ticket.states` 仅 pending/approved/rejected | **同族异因** → 批 B2 |
| 6 | 借阅域自洽，但"通用前端组件可能带入 hold、cart、AI…" | **同族异因** → 批 B2 |
| 1011 | 文案宣称「班次」能力，而 `entityKeys` 无班次实体与菜单 | **同族另一支**（宣称 vs 实体）→ 批 C |
| 10 | 音乐域非本期能力"已明确标注"类 | 同族另一支 → 批 C |

### 12.2 copy_bake 5 条（不同源，另立清单）

| job | 症状 | 定性 |
|---|---|---|
| 1002 | `DOM-SHOP schema 表数量=16，必须在 6~15 之间`（2026-09-20） | **存量且已放开，无需处理**：现 `TABLE_COUNT_MAX=15` 只是**警告线**（注释："超过只警告，不拦出包"），打回线是 `TABLE_COUNT_HARD=18`，且开题扫入的必需表**不计入** 18。实测 16 / 17 / 18 表均 `ok=True`（仅 warn），该消息在当前代码中**已搜不到**（`grep 必须在 backend/app` 零命中）＝正是那次"放开"替换掉的硬拦 |
| 1001 / 1000 | `错皮/怪交互硬闸失败 [DOM-SHOP]：shopMarketplace 缺 guestbookGuestCta / noticeGuestCta` | **皮必备项缺失**（配置类） |
| 2 / 1 | `'utf-8' codec can't decode bytes … invalid continuation byte` | **上传素材编码问题** |

> 存量 vs 新增：`[1001]/[1000]/[2]/[1]` 属**同一历史项目** `gf-20260911-033005`（9/11 反复失败）＝存量；**9/26–9/27 的 4 条新失败全部是 `gate_e2e` 文案/可见面类**＝当前活跃阻塞源。

### 12.3 对方案的影响（据此修订）

1. **新增批 B2**：给通用前端组件的域外字段渲染补 `allow*` 开关分支（治 1014 / 12 / 6）；
2. **批 C 门禁须含两类规则**：① 跨域词 + 口径一致性（已设计）② **字段渲染缺 `allow*` 保护**（复用 gate 既有口径）；
3. **5 条 `copy_bake` 技术类不并入本批**，单独立项（其中 `DOM-SHOP` 16 表那条经实测**已失效**——放开后 15 只是警告线、16~18 表照样出包，故仅余「皮必备项缺失」+「UTF-8 解码」两项真实待办）。另注：`backend/tests/test_table_budget.py:70-71` 把 `(15, 18)` 钉为断言，将来再动配额必须同步该测试。
4. ~~**C 的门禁等级**~~ → **已定：`error`（阻断交付）**，见 §0.2。
5. ~~**优先级**~~ → **已定：A/B/C 同批交付**，见 §0.3；批内编码顺序仍为 A → B → C。
