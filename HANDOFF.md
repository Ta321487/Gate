# 毕设港 · 交接

工作区：`d:\graduate_factory_v3`  
**禁止**参考 / 迁移 `d:\graduate_factory`、`d:\graduate_factory_v2`。

> **本文只负责**：新对话交接（主线、硬边界摘要、开场白）。  
> **产品总览 / 启动**：[README.md](./README.md) · **专题索引**：[docs/README.md](./docs/README.md)

---

## 当前主线

1. **能力运行时 + 薄域 A～G + GENERIC** 已可 bake；差的是按需冒烟与文案微调。  
2. **Path B** 三条真交叉可 `full`（借用+下单 / 借用+预约 / 下单+预约）；三合一与智慧校园仍 `reject`。  
3. LLM **只填 schema JSON**（不生成业务 Java/Vue）；接 LLM 后「代码无误」靠运行时固定。  
4. **Path B 口径**：开题写进「拟实现」的必须能答辩演示；做不到就拒收 / 改开题 / 先扩能力，禁止 `degraded` 交半成品装全文。

领域与交叉长表 → [`docs/domains.md`](./docs/domains.md)。  
能力 cap 矩阵 → [`docs/capabilities.md`](./docs/capabilities.md)。

---

## 接题边界（硬原则）

本产品定位：**专科 / 本科毕设、课设级别的 Web 管理系统生成**（演示级主路径），不是研究生平台，也不是真实业务交付。

| 接 | 不接 |
|----|------|
| **专科 / 本科** 毕设、**课设**（Web 管理、演示级） | **硕士研究生 / 博士研究生** 课题与开题 |
| 薄域单路径；白名单内且 `defense_ready` 的交叉 | **真实业务全流程** / 生产级全链路 / 企业级端到端 |
| L0～L2 积木内可演示的功能 | L3、HIS/ERP 级发散、未就绪交叉 |

信号：`OUT_OF_SCOPE_SIGNALS`（硕博学位论文、真实业务全流程等）→ `reject`。  
分层细则 → [`docs/difficulty-tiers.md`](./docs/difficulty-tiers.md)。

---

## 开题场景 / 身份文案（硬原则）

**开题与材料为准，工厂跟场景走；禁止改开题迁就模板。**

| 约定 | 含义 |
|------|------|
| **单一真源** | `app/bake/scene_scan.py` → `scene_for(domain, title, proposal)` |
| **同场景同口径** | 壳 eyebrow/roles 与 `profileFields`（注册/资料页）必须读同一 scene |
| **扫词选分支** | 不是逐字复述开题；场景定了不得再写死冲突身份（如企业 CRM ≠ 学号/教职工） |
| **业务角色优先** | 背景里的「学院/校园」不压过正文里的「销售/客户跟进」等企业档 |
| **未写清用域默认** | 默认档在 builder / `PROFILE_FIELDS_BY_DOMAIN`，不是臆造开题 |

须分支域清单见 `SCENE_BRANCH_DOMAINS`。改 hint 只动 `scene_scan`，并补场景测试。

---

## 读什么（专题）

| 要查 | 文档 |
|------|------|
| 能力 cap / 挂载口径 | [`docs/capabilities.md`](./docs/capabilities.md) |
| 领域组 A–H / Path B 交叉 | [`docs/domains.md`](./docs/domains.md) |
| L0–L3 / 加价边界 | [`docs/difficulty-tiers.md`](./docs/difficulty-tiers.md) |
| 库表预算 / 角色不变式 | [`docs/invariants.md`](./docs/invariants.md) |
| 怎么审交付 | [`docs/delivery-audit-rules.md`](./docs/delivery-audit-rules.md) |
| 换皮 ID 册 | [`docs/domain-skin-gap-analysis.md`](./docs/domain-skin-gap-analysis.md) |
| 开题功能对照 | [`docs/opening-feature-delivery-map.md`](./docs/opening-feature-delivery-map.md) |
| AI 开题对照 | [`docs/ai-opening-delivery-map.md`](./docs/ai-opening-delivery-map.md) |
| 全索引 | [`docs/README.md`](./docs/README.md) |

宿舍样板账号见 [README.md](./README.md)「样例开题」节。

---

## 新对话开场（当前主线）

```
继续 graduate_factory_v3。先读 HANDOFF.md；能力/领域长表见 docs/。
主线：Path B 三条交叉已可 full；薄域冒烟或 LLM 填 schema。
超壳 / 三合一 / 智慧校园必须 reject；硕博与真实业务全流程不接。
不要新开厚 DOM 包。领域清单以 docs/domains.md 为准。
```

## 新对话开场（某个薄领域）

```
继续 graduate_factory_v3。先读 HANDOFF.md。
目标：薄领域 DOM-___（关键词：___）冒烟或文案/SQL 微调。
能力组合：___（对照 docs/capabilities.md + docs/domains.md）；仅 catalog + schema + SQL 种子 + 皮肤。
禁止内存 Store、禁止排除 DataSource、LLM 只填 schema。
```

---

## 专项交接：话术层（Surface Lexicon）修复 · 2026-09-26/27

> **设计稿（先读这份）**：[`docs/surface-lexicon-design.md`](./docs/surface-lexicon-design.md)
> 状态：**批 A ✅ / B1 ✅ / B2 ✅ / C ✅ 已落地**；重生成 goldens 与全量脚本已跑通。
> 未完成（运维步）：**库内 7 条 `gate_e2e` 需重新 bake 对应项目**（改素材/改门禁都不会回溯修旧工作区）。

### 触发与硬性要求

`gate_e2e`「交付质量摘要」连续 fail，两条均为**可见的错域/不一致文案**：

| # | 症状 | 证据 |
|---|---|---|
| 1 | CRM 分类轴：「分类标签」（开题正文）vs「客户分级」（实体 label/labelPlural）vs「按分级浏览客户」（banner）→ 三处口径不一 | `schema/builders_archive.py:449`（分类轴名）、`:457`（banner）、`proposal_packs_data/crm.json:11`（正文） |
| 2 | 事件上报域用户端空状态写「还没有**打卡**记录…」 | `schema/builders_archive.py:483`（`_event_self_report_overrides()`，同函数 `:470-490` 全为「打卡」） |

**需求方硬性要求（设计稿 §0）**：
1. **所有域都得吃到此次变更** → 只准改全域 choke point，禁止逐域补丁；
2. **修复后不可再出现同样问题** → 门禁等级 `error`、数据驱动、全域覆盖；A/B/B2/C **同批交付**；
3. 验收必须**脚本化全量**（74 个域包），不接受抽样。

### 根因一句话

既有零件齐全（`bake/ticket_copy_text.py` 单据文案生成器、`schema/er_zh.py` 表列词表、`proposal_lexicon.py` 扫词、`student_copy.py` 事后清洗、`delivery_review.py` 事后 gate），**缺的是把"页面级话术"（`banners`/`doc`/`auth_lead`/`my_tickets_*`/种子公告）统一串起来的解析层**，且 `proposal_lexicon` 只用于"判能力开不开"、从未用于"决定怎么说"。

### 已完成：批 A（素材口径对齐）

| 文件 | 改动 | 状态 |
|---|---|---|
| `proposal_packs_data/crm.json:11` | 「分类标签」→「**客户分级**」 | ✅ 与实体 golden 同词（`DOM-CRM.json` 命中） |
| `proposal_packs_data/event_report.json:11` | 「分类标签」→「**分类**」 | ⚠️ 依据是 `DOM-EVENT.json` L60/L61 的 `label/labelPlural`（域默认）；**精确串回校未命中，未经机器证实**，批 B 全量断言时一并确认 |

**验证已过**：两 JSON 解析通过；全仓 `分类标签` 零残留（仅设计稿引用原文）；pack 消费方测试 `test_proposal_diff / test_identity_align / test_cap4_delivery / test_form_first_residual / test_attend_scene` → **49 passed / 229 subtests** 与 **32 passed / 229 subtests** 两轮均绿。

**踩坑记录（重要）**：EVENT 的「**事件分类**」只存在于**部分场景皮**（`builders_archive.py:743/769/813/860`），域默认是「分类」。第一版曾误写「事件分类」，已改回。

### 批 B1 / B2 / C 计划表（**已全部执行**，落地与验证见下文「已完成」节）

| 序 | 内容 | 关键落点 |
|---|---|---|
| **B1** 话术层 | 扩展 `bake/ticket_copy_text.py` 为主干（`slot` + `DOMAIN_LEXICON` + `SLOT_PATTERNS` + `lex()/lex_all()`）；`followup_domain_schema()` 写 `schema["lex"]`；②来源 13+ 文件改读 `schema["lex"]`；`_event_self_report_overrides()` **槽位化**（治「打卡」：`还没有{ticket_noun}记录，点击右上角提交。`） | `schema/followup_presets.py`、`schema/builders_archive.py`、`schema/builders_ticket.py`、`schema/form_first_entry.py`、`oa/tail/stuwork/deep_skin/mutual/checkin/bed/carpool/instrument/timebank_*` |
| **B2** 渲染分支 | 通用前端组件补 `allow*` 保护（治 1014 / 12 / 6）：`row.dueAt/dueLabel/row.qty`（借阅/商城字段）、`hold_ready/holdCountdown/取书截止` | `skeletons/baseline/frontend/src/views/user/MyTickets.vue` 等，三栈同步 |
| **C** 门禁 | `bake/domain_vocab.py`（专属名词→归属域，数据驱动、全域）+ `services/delivery_review.py` 新增 **error 级**检查（跨域词 + 口径分叉 + 缺 `allow*`，现 `:340` 已挂「交付质量摘要」项）；补 `tests/test_delivery_review.py` 正反例 | 复核 `docs/delivery-audit-rules.md` 红灯表 |

**B1 解析优先级**：开题抽取（须落在本域允许集内）→ 域词表 → 域默认 override → 通用兜底。
**同义簇**：`category_axis = 分级|等级|评级|星级|档位|标签|类目|分类|类别`；`ticket_noun = 上报|填报|打卡|申报|申请|报修|登记|诉求|预约`。

**验收（缺一不可）**
1. **74 个域包**批量 bake → 断言：对专属名词表零命中、同一 slot 零口径分叉；
2. **反例必红**：EVENT 注入「打卡」→ error；CRM 注入「分类标签」→ error；`dueAt` 未加 `allow*` → error；
3. 现有全部域包产物 → gate 保持**绿**（零回归）；
4. goldens 重生成：`python tests/tools/regen_sql_goldens.py` + `tests/tools/regen_schema_goldens.py`；
5. 三栈 `mvn -o compile`（jdbc / mybatis / jpa）+ 现有 105 项门禁全绿；
6. `gate_e2e` 那 **7 条文案/可见面类**转绿（需**重新 bake** 对应项目，改素材不会回溯修旧工作区）。

**次批**：收紧 `scene_scan.EVENT_SELF_REPORT_HINTS`（配 74 域包"皮命中矩阵 before/after"）；`sql/domain_scene_seed.py`（145 KB）**公共模板同批、域特有分支分批**迁移。

**另立清单（不同源，勿并入本批）**：`shopMarketplace` 缺 `guestbookGuestCta / noticeGuestCta`；上传素材 `'utf-8' codec can't decode … invalid continuation byte`。

### 库内 bake 失败普查（实测，`jobs` 表）

`jobs.bake`：failed **12** / success 15；`projects`：failed 5 / generated 7 / ready 1。原文导出：`C:\Users\17386\AppData\Local\Temp\gf_bake_fail_reasons.txt`。

| 步骤 | 条数 | 判定 |
|---|---|---|
| `gate_e2e` | **7** | **同源家族**＝可见文案/可见面 vs 实体不一致（1010 打卡、1009 口径、1014/12/6 缺 `allow*`、1011/10 宣称 vs 实体）→ 本专项对症 |
| `copy_bake` | **5** | **不同源**：`DOM-SHOP` 16 表配额、`shopMarketplace` 缺 `guestbookCta`、上传素材 UTF-8 |

**「存量 vs 活跃」判据**：`[1001]/[1000]/[2]/[1]` 全属历史项目 `gf-20260911-033005`（9/11，存量）；**9/26–9/27 的 4 条新失败 100% 是 `gate_e2e` 文案类**＝当前活跃阻塞源。

**表配额真相（勿再误判）**：`engine_sql.py:33-39` → `MIN 6` / `TABLE_COUNT_MAX 15`＝**仅警告（注释原话"超过只警告，不拦出包"）** / `TABLE_COUNT_HARD 18`＝打回；开题扫入的必需表（`ESSENTIAL_CAP_TABLES`）**不计入 18**。实测 16/17/18 表均 `ok=True`（仅 warn），≥19 才打回。
→ 库里 `DOM-SHOP 16 表` 那条是**放开之前的旧记录**，那条消息在当前代码里已搜不到，**无需处理**。
→ 配额契约由 `backend/tests/test_table_budget.py:70-71` 钉死（`(15, 18)`），将来再动配额必须同步它。

### 已完成：批 B1 / B2 / C（2026-09-27）

| 批 | 落地 | 文件 |
|---|---|---|
| **B1 话术层** | 槽位解析层（`category_axis`/`ticket_noun` + 同义簇 + `{slot}` 占位符 + 单据壳归一化）；`followup_domain_schema()` 写 `schema["lex"]`，并把解析值写回 `archive_fields` 分类轴与门户轮播（分类菜单随字段自动跟随） | `bake/ticket_copy_text.py`、`schema/followup_presets.py`（全域 choke point） |
| **B1 事件皮** | `_event_self_report_overrides()` 全部改 `{ticket_noun}` 占位符：开题写「打卡/晨午检」才出「打卡」，否则跟本域单据名词（默认「上报」）；`_crm_schema` 三处 + `_event_schema` 已回传 `proposal_text` | `schema/builders_archive.py` |
| **B2 渲染分支** | 通用前端组件域外字段补 `allow*` 分支：`allowQty` / `showDueCols` / `showFineCols`（数量、到期、实发、罚金、领取行） | `skeletons/baseline/frontend/src/views/user/MyTickets.vue`（全仓唯一副本） |
| **C 门禁** | `domain_vocab.py`（专属名词→归属域逆向 forbidden + 三条 error 规则）；接入 `_structural_findings()` → `p3q`「交付质量摘要」挡包（无 LLM 也生效） | `bake/domain_vocab.py`（新）、`llm/agents_qa.py`、`docs/delivery-audit-rules.md`（H24） |

C 的三条规则（全数据驱动、全域覆盖，非逐 case）：

1. **跨域专属名词**：`_NOUN_OWNERS`（借阅/挂号/客房/查寝/寄养…）反向下发 forbidden；豁免本域实体词/槽位值/项目题名/划界否定语境。
2. **同 slot 口径分叉**：`ticket_noun` 只审单据壳（`myTicketsEmpty/PageLead/EmptyArchive` + `my_tickets` 菜单）；`category_axis` 只审分类菜单 + 门户轮播 + `category*` label；已覆盖的簇词（「分级」⊂「客户分级」）与本域自有词（「事件等级」）不算分叉。
3. **域外字段缺 `allow*`**：`dueAt/dueLabel/renewCount/qty/actualQty/holdExpireAt/hold_ready/fineYuan` 出现在 `.vue/.js` 且 ±6 行无 `allow*`/`hasCap` 分支 → error。

### 验证结果（本批实测）

```powershell
cd d:\graduate_factory_v3\backend
python tests/tools/check_surface_lexicon.py         # 74 域包全量：checked 69 packs, failed 0（4 个 DOM-GENERIC 交叉包无 builder，SKIP）
python -m pytest -q tests/test_surface_lexicon.py    # 14 passed（优先级/同义簇/3 条反例必红/baseline 渲染守卫）
python tests/tools/regen_schema_goldens.py           # 98 个 golden 重生成（含 SQL：另有此前存量漂移一并归位）
python tests/tools/regen_sql_goldens.py
mvn -o -q compile                                    # skeletons/baseline/backend → EXIT=0（本批未改一行 Java）
```

- 反例必红（已入单测）：EVENT 自报皮注入「打卡」（槽位为「上报」）→ error；CRM 注入「分类标签」→ error；`dueAt` 无 `allow*` → error；改为 baseline 真实文件后 → 零 finding。
- 相关黄金/文案测试批量复跑：`test_schema_builders_golden / test_domain_sql_golden / test_shells_archive_lead / test_attend_scene / test_checkin_c10 / test_cap4_delivery / test_identity_align / test_form_first_residual / test_proposal_diff / test_copy_h22 / test_student_facing_copy / test_qa_factory_drift / test_semantic_gates / test_oa_apply_p / test_tail_p / test_stuwork_p / test_mutual_c05 / test_domain_skin_leak / test_delivery_review / test_domain_column_forbid / test_table_budget` → **186 passed / 872 subtests**；另 33 个域/场景/皮测试文件 → **247 passed**。
- **存量红收口中（按载体口径，2026-09-27）**：`test_code_qr_e07::test_baseline_fe_and_dep` 原是**自相矛盾的过期断言**（要求 baseline `MyTickets.vue` 含「不对接闸机」，而该句已被 `domain_schema.py:758` 的 `FACTORY_UI_FORBIDDEN` 明令禁止上学生页面）。已按新载体口径修：页面断言改为 `assertNotIn`，新增 `tests/test_copy_carrier_contract.py`（学生可见面禁硬件纠葛词 / 工厂侧必须留划界语 / 同一句多载体逐字一致），并把 `CodeQrBlock.vue` 兜底与 `features/code_qr.py::CODE_QR_HINT_DEFAULT`、`domain_schema._LABEL_FALLBACKS["codeQrHint"]` 对齐为同句。**该族 9 条测试已全绿**（全量 suite 存量红由 16 → 15）。
- **全量 `pytest -q tests` 现状（本批前后一致，均非本批引入）**：`15 failed, 1260 passed, …`。其余失败集中在**已存在的存量漂移**：`test_chrome_theme`(2 主题 token/暗色对比)、`test_delivery_mark`(5：`projects.py:167` 直接读 `project.workspace_path`，测试用 `SimpleNamespace` 无该属性)、`test_upload_cluster`(3 聚类分组)、`test_schema_testcases`(mojibake 断言)、`test_core_cap_scan::test_asset_mounts_loan_deadline`、`test_compose_out_of_mvp`、`test_student_api_smoke::test_gate_fail_detail_uses_data_message`、`test_appoint_from_users::test_scene_blocks_property_media_event_lost`、`test_ai_assistant_bake`。**判据**：失败点都不在本批改动的调用链上（traceback 指向 `projects.py`/themes/testcases/cluster 等未改文件），且本批改的是「更严」的 error 门禁，不会把红转绿。
- **gate_e2e 7 条**：门禁与素材都已换用新口径，但旧工作区是历史产物 → 必须**重新 bake** 那几个项目（`jobs` 步骤 4+）才会转绿；未在本轮执行（会覆盖用户工程）。

### 与设计稿的偏差（如实记录）

1. `category_axis` 采用「**保留域限定前缀、只跟随开题簇词**」（客户分级 + 开题「评级」→ 客户评级），而非整词替换：避免把「费用类别」写成「分类」丢限定词。开题词不在簇内 → 回落域默认。
2. 只有 `_crm_schema` / `_event_schema` 把 `proposal_text` 传进 `followup_domain_schema`；其余 builders 仍走域默认（全域一致性由 C 门禁保证）。要全域跟随开题，需按 builders_archive 的 20+ 调用点逐个补 `proposal_text=`。
3. ④ 种子公告（`sql/domain_scene_seed.py` 145 KB）**未迁移**，按设计稿 §11.3 分批；本轮由 C 门禁兜底。
4. 次批原计划：收紧 `scene_scan.EVENT_SELF_REPORT_HINTS`（现 `_event_self_report_overrides()` 已槽位化，「打卡」不会再串到单据壳，词表收紧改为纯收窄皮判定，优先级下降）。

### 批 C 进展（2026-09-27）

| 子项 | 状态 | 说明 |
|---|---|---|
| **C1 全域跟随开题** | ✅ 完成 | `builders_archive.py` 的 **22 个** `followup_domain_schema()` 调用点补 `proposal_text=proposal_text`（此前只有 `followup_builder` 路径回传）。效果：这批域（ATTEND/FUND/LABSAFE/RECRUIT/PROCURE/DATING/GRADE/BED/INTERN/PARCEL 等）现在也按「开题簇词 → 域默认 → 兜底」解析话术，域默认仍兜底 |
| C2 ④ 种子公告迁移 | ⏳ 待办 | `sql/domain_scene_seed.py`（145 KB）：设计稿 §11.3 已定「公共模板同批、域特有分支分批」；本轮仍由 C 门禁兜底 |
| C3 ⑤ 前端空状态迁移 | ⏳ 待办 | 实测 baseline 前端 `还没有|暂无` 共 **90 行、40+ 个 .vue**（Top: ArchiveBrowse 10、MyTickets 4、SlotBook 4、PortalHome 3…）；需逐个映射到 schema label，属设计稿 §10「体量大、一次改不完」项 |

**C1 验证**：`check_surface_lexicon.py` → `checked 73 packs, failed 0`；goldens 重生成后与 C1 前**逐字节相同**（无新增 churn）；A 批 + C1 相关 **34 个测试文件 316 passed / 1227 subtests**。

**过程记录（踩坑）**：用脚本批量插 kwarg 时，自写的括号扫描没跳过注释里的 `)`，插错位置并一度破坏语法；改用 `tokenize` 精确定位跨度后修复，并补排版还原。**结论：这类批量改写必须用 `tokenize`/AST 定位，不要手写括号计数**（脚手架脚本已删）。


`bake/domain_vocab.py`、`bake/ticket_copy_text.py`、`bake/schema/followup_presets.py`、`llm/agents_qa.py`、`skeletons/baseline/frontend/src/views/user/MyTickets.vue`、`docs/delivery-audit-rules.md`。

### 环境与命令速查

```powershell
cd d:\graduate_factory_v3\backend
python -m pytest -q tests/<某个>.py                  # 单测（.pytest_cache 有权限告警，忽略）
python tests/tools/regen_sql_goldens.py              # SQL golden 重生成
python tests/tools/regen_schema_goldens.py           # schema golden 重生成
python -m app.bake.sample_proposal --list            # 测试开题 74 个域包
AOCI: "C:\Users\17386\tools\aoci\aoci.exe" verify|check --json ; index agent guide --agent cline --json
DB:  mysql+pymysql://root:****@127.0.0.1:3306/graduate_factory（见 backend 配置）
```

**临时脚本**（`C:\Users\17386\AppData\Local\Temp\`）：`gf_bake_fail.py`（探库）、`gf_bake_fail_dump.py`（导出+分桶）、`gf_table_budget.py`（配额实测）、`gf_testproposal.py`（测试开题→匹配→出包核对）。

### 陷阱（本会话踩过）

1. `Get-Content` 在 PS 5.1 对 UTF-8 文件会**误读成 ANSI**，行数/内容会失真（曾误判"文件被截断"）→ 用 `read_files` 或 `[IO.File]::ReadAllText(path,[Text.Encoding]::UTF8)` 复核；
2. `.NET` 相对路径按**进程 CWD**（VS Code 目录）解析，`cd` 无效 → 一律用绝对路径；
3. 递归扫 `backend` 会撞 `.pytest_cache` 权限拒绝 → 限定 `backend\app` / `backend\tests` 并加 `-ErrorAction SilentlyContinue`；
4. `search_codebase` 会被 `.aoci` 基线/草稿刷屏 → 改用 `Select-String` 限定目录；
5. MCP `desktop-commander` 单次调用上限 300s → 7 个包连编/全量 check（约 220s）要拆开跑。

### AOCI 收尾状态（2026-09-27，已解阻塞）

- **阻塞已解**：本轮新增/改动文件触发 `observed_pending`（Observe 复核）→ 已执行受治理事务 `aoci.exe scope acknowledge --reviewed-by cline --json`（`status=applied`）。guide 现在为 `stage=authoring_required`、`executable_targets=23`。
- **待作者化 23 个对象**（下一次：**无参** `aoci_maintain` 领批 → 按 `code_batch_id` 提交完整批次；23 > 单批 20，需两轮）：
  - `create` 2 个：`backend/app/bake/domain_vocab.py`、`docs/surface-lexicon-design.md`（文件在盘上但索引无条目）；
  - `update` 21 个：本批改过的 `HANDOFF.md`、`capabilities.py`、`features/code_qr.py`、`crm.json`、`event_report.json`、`schema/builders_archive.py`、`schema/followup_presets.py`、`sql/domain_scene_seed.py`、`ticket_columns.py`、`ticket_copy_text.py`、`llm/agents_qa.py`、`services/projects.py`、`services/upload_cluster.py`、`docs/delivery-audit-rules.md`、`CodeQrBlock.vue`、`themes/{cinema,doclib,vote}.css`、`views/user/MyTickets.vue` 等。
- **作者化：✅ 全部完成（24/24 applied）**。终态证明：`verify` → `governance_aligned=true, aligned=true`、预算 health（whole_index 74086 tokens / target 200000）；`check` → `ok=true, next_action=none`；`index agent guide` → **`stage=aligned, complete=True, next_action=none, targets=0`**。
  - 已写对象（24）：`HANDOFF.md`、`capabilities.py`、`features/code_qr.py`、`domain_vocab.py`(create)、`ticket_columns.py`、`ticket_copy_text.py`、`schema/builders_archive.py`、`schema/followup_presets.py`、`sql/domain_scene_seed.py`、`sql/templates/{DOM-EQUIP,DOM-FUND,DOM-VISITOR}.sql`、`llm/agents_qa.py`、`services/projects.py`、`services/upload_cluster.py`、`proposal_packs_data/{crm,event_report}.json`、`docs/delivery-audit-rules.md`、`docs/surface-lexicon-design.md`(create)、`CodeQrBlock.vue`、`themes/{cinema,doclib,vote}.css`、`views/user/MyTickets.vue`
  - **配置已回收**：`code_cognition_batch_entries` 已由 6 改回 **20**（收尾时若再次领批被截断，可临时改 6）。
  - 本条 HANDOFF.md 编辑会使该条再次 stale → 下一轮 `scope acknowledge` → `aoci_maintain` → 只作者化 `HANDOFF.md` 一条即可回 `aligned`。

- **两条实测经验**：
  1. **S 字段机器 token 上限比 Meta 表格更严**：C6/C7 对象实测上限 **80 tokens**（≈240 UTF-8 字节，中文≈80 字），超了会 `entry_field_budget_exceeded` → 按 finding 压缩重写整个字段（不许机械截断），然后**重提同一完整批次**。
  2. **每次改动文件后 guide 会回到 `observed_pending`**：作者化前若又编辑了任何文件（含 `tests/tools/*`），需再跑一次 `scope acknowledge --reviewed-by cline` 才能领到候选批次。

- 认知效力：本轮 Overview 交付被 Host 中段截断 → `model_attestation=partial`（Challenge 3/10）；按合同不做无保留的「完整系统认知」声明，但 source-bound 工程不受限。想恢复完整认知：`overview_delivery.chunk_tokens` 降到 4000 重跑。



1. `docs/surface-lexicon-design.md`（新建，`check` 报 aligned 但列为 target、exit=1）；
2. `backend/app/bake/proposal_packs_data/crm.json`（本轮改）；
3. `backend/app/bake/proposal_packs_data/event_report.json`（本轮改）。
→ 下一次 `aoci_maintain` 领正式候选后一次性作者化。

### C2 第一步：种子公告纳入门禁（2026-09-27）

种子公告（`sys_notice`）由 `sql/domain_scene_seed.py` 等**手写**、随 DDL 插进学生包，是可见文案的第四个来源；此前没有任何门禁。

- **判据**：`domain_vocab.notice_slot_findings(sql, schema, domain=)` —— 只在**名词位置**判分叉（`提交X / 我的X / X单 / X记录 / 办理X / X已开放 / X通过后 / 还没有X`，分类轴另用 `按X浏览 / X管理`），避免把「如实登记联系结果」「预约面试」这类**动词用法**误杀；同时查跨域专属名词。
- **上线**：`lexicon_findings(..., seed_sql=)` → `agents_qa._collect_qa_context` 读 `workspace/sql/*.sql` → 进 `p3q`「交付质量摘要」（error 级挡包）。
- **全量实测**：87 条公告，初筛 10 处 → 收敛到 **3 处真分叉**（其余 7 处是动词用法）；已修字面量 2 处（EQUIP 种子「办理领用与归还」→「办理**借用**与归还」，`domain_scene_seed.py:921/1105`）。
- **显式登记（不是静默放过）**：`SEED_NOTICE_KNOWN_PENDING` 记 3 条待 C2 迁移项，迁移时删掉就会被门禁要求一致：
  1. `DOM-FUND`「申报」← 公告「奖助学金申报已开放」由 f-string 拼出；
  2. `DOM-VISITOR`「预约」← 公告「预约通过后出示通行码」同上；
  3. `DOM-EQUIP`「领用」←「开放时间」公告由 `builders_archive.py:256` banner 合成。
- **新测试**：`tests/test_seed_notice_lexicon.py`（74 域零命中 + 2 条反例必红）；新脚本 `tests/tools/check_seed_notice_lexicon.py`、`list_notices.py`、`dump_lex.py`。

**同时自查出并修掉 B1 两个真缺陷**（由这次普查暴露）：

1. 单据壳归一化会造叠词（「点击右上角**归寝归寝签到**」）→ `normalize_slot_words` 增加「前后缀已含解析值首尾」保护；
2. 槽位取错概念：DOM-CHECKIN 的票据标签是「归寝签到」（口令签到），而域自己的话术是「归寝登记」（提交动作）→ `preset_slots` 改为**优先采信域自己单据壳话术里的复合名词**，且材料里的通用簇词不得覆盖它（`copy_authoritative_noun`）。

### C3 结论修正：前端空状态**不需要迁移**（2026-09-27）

原判断（设计稿 §2.1 ⑤「12+ 页写死空状态」）实测**不成立**，两点证据：

1. 学生可见页面（`views/user/**`、门户壳）的空状态**早就走 `labels.*` + schema**，那 90 处「还没有/暂无」绝大多数是**取不到标签时的兜底句**，不是另一套说法；
2. 剩余的写死文案全部落在**能力岛专属页**（`BuybacksAdmin`/`LessonPacksAdmin`/`LossAdmin`/`FrontCare…`/`FundDisburse…`/`CareOptions` 等）：岛不开不挂载，其用语（回收单/课时包/赔付/登记入住/预约队列）是**该岛的功能词**，不构成跨域错词；实测「共享页面里写死域词」命中 **0**。

→ 因此 C3 从「迁移 90 处」降级为「**可选**的进一步收敛」（若要更严，把岛页文案也改走 `schema.labels`）。
→ 真正需要保留的门禁是**兜底句与 schema 默认句同源**（codeQrHint 就是这个坑，已修）；这条由 `test_code_qr_e07::test_code_qr_hint_same_text_on_every_carrier` + 载体口径三测覆盖。

## 专项：存量测试红清零（批 A，2026-09-27）

> 目标：让全量 `pytest` 回到 **0 红**，否则「零回归」无法证明、真红会被噪声淹没。逐条先定性「谁的契约过期」，再改最小一侧。

| # | 症状 | 定性（实测判据） | 修法 | 文件 |
|---|---|---|---|---|
| 1 | `test_delivery_mark` 5 红（`AttributeError: SimpleNamespace has no workspace_path`） | 实现侧过硬：`delivery_block_reason` 直接读 `project.workspace_path`，测试桩用 `SimpleNamespace` | 改防御式读：`getattr(project, "workspace_path", "")` | `app/services/projects.py:167` |
| 2 | `test_schema_testcases::testcase_model` setup ERROR（mojibake 断言） | **pytest 收集事故**：`testcase_model` 被 `from ... import` 进来，名字匹配 `test*` → 当测试函数收集（缺参→fixture 解析失败） | 别名导入 `as build_testcase_model`（顺带放出 5 条被遮蔽用例） | `tests/test_schema_testcases.py` |
| 3 | `test_chrome_theme` 2 红（缺 token / 深色 accent 过浅） | 真缺陷：`doclib.css`/`vote.css` 还在用**旧 token**（`--bg/--accent/…`，全前端已无人消费）→ 这 8 套主题**实际不生效** | 迁到 portal token 套装（`--portal-scheme/mix/bg/ink/…`）；`cinema-night` accent `#d49448`(lum .61) → `#a87b3c`(lum .50) | `skeletons/baseline/frontend/src/styles/themes/{doclib,vote,cinema}.css` |
| 4 | `test_upload_cluster` 3 红（同课题未合并） | 规则过硬：卫星（功能清单）挂靠时被**能力指纹冲突**否决；清单的功能词天然与开题正文不同 | 指纹冲突只用于「题名不像」：`if _fps_conflict(...) and not title_ok: continue` | `app/services/upload_cluster.py` |
| 5 | `test_core_cap_scan::test_asset_mounts_loan_deadline` | 规则过硬：非 LIBRARY/EQUIP 一律「只补 due_at」→ 领用逾期罚款无 `fine_yuan` 落点 | 新增 `_LOAN_SHELL_DOMAINS=(LIBRARY, EQUIP, ASSET)`：领用/借用族开借阅期即完整壳；SLA 型仍只补 due_at | `app/bake/ticket_columns.py` |
| 6 | `test_compose_out_of_mvp::test_attach_accept_writes_composed_out_of_mvp` | 实现退化：docstring 写「该词/**片段**即相关」，代码只剩整词/斜杠片段；题面「人脸**识别**」匹配不到默认项「人脸**考勤**」 | 补 `_default_item_related()`：整项/斜杠片段/词干片段（片段须含 CJK 或 ≥3 位 ASCII，如 GPS/ATS） | `app/bake/capabilities.py` |
| 7 | `test_appoint_from_users::test_scene_blocks_…` | **测试快照过期**：`staff_posts.py:206` 明写「MEDIA 默认双角色，开题写编辑/权限划分才挂 content_ops」 | 断言改为：校园无角色材料 → False；校园+「运营编辑/权限划分」→ True；商业仍 False | `tests/test_appoint_from_users.py` |
| 8 | `test_ai_assistant_bake::test_all_ai_skins_…`（1/50 皮） | **测试快照过期**：书皮问句已由「续借与逾期怎么办」改为「**逾期与催还怎么办**」（与产品 `deadline_label=逾期催还` 同词） | 更新该快照（其余 50 皮逐条比对无差异） | `tests/test_ai_assistant_bake.py` |
| 9 | `test_student_api_smoke::test_gate_fail_detail_uses_data_message` | **测试桩缺契约**：gate 自检只在「单据主链域」跑（`_ticket_flow_keys`），桩只给 `{"domain": …}` → 整步 skip，测不到 detail | 桩补 `gate.flow_api{apply,approve,return}` | `tests/test_student_api_smoke.py` |

**遗留说明**：`PermissionError: Temp\pytest-of-*` / `WinError 145 目录不是空的` 是**并发 pytest 抢临时目录**的环境噪声（单跑即绿）；复跑请用独立 `--basetemp`，别并行开两个 pytest。

### 新对话开场（话术层专项）

```
继续 graduate_factory_v3。先读 HANDOFF.md「专项交接：话术层修复」与 docs/surface-lexicon-design.md（含 §0 硬性要求、§12 库内普查）。
已完成批 A（两条素材口径）；现在按顺序做 B1 话术层 → B2 allow* 渲染分支 → C error 级门禁，同批交付。
硬约束：所有域都吃到（只改 choke point）、修复后不可复发；验收＝74 域包全量脚本 + 反例注入必红 + goldens 重生成 + 三栈编译 + 105 门禁 + gate_e2e 7 条转绿。
```
