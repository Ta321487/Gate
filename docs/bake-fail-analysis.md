# bake 失败分析（码表）

> **本文只负责**：失败码目录、归桶规则、A 档权威修工厂落点。  
> **不负责**：能力地图、交付审计红灯全文、学生包实现细节。  
> **机器真源**：与 `backend/app/services/bake_fail_classify.py` 常量同源；改码必改测。  
> **索引**：[README.md](./README.md)

---

## 产品

运营台侧栏 **失败分析**（Issues / Error Tracking）：周看分布、对照 A 档落点排修。

## 两档修法

| 档 | 字段 | 可否当排修依据 |
|----|------|----------------|
| **A 权威落点** | `fix_locus`（本表 + 常量） | **可以** |
| **B 修法建议** | DeepSeek `fix_draft`，标「未核对」 | **不可以**，直到人确认后由 Cursor 对照实现升格进本表 |

错建议 → 丢弃；不写库、不进本表、不进周优先。升格无产品 API。工作流：`DeepSeek 建议 → Cursor 核对 → 确认再改工厂`。

---

## 码表

| 码 | 典型步骤 | stem / 判据 | A 档落点 | gate key | 门禁/测 |
|----|----------|-------------|---------|----------|---------|
| `OPS_RESTART` | 任意 | `服务重启，任务中断` | `backend/app/services/jobs.py` 孤儿收口 | — | 运维 |
| `OPS_CANCELLED` | 任意 | `已取消` | `jobs.cancel_job` | — | 运维 |
| `OPS_PROJECT_MISSING` | start | `项目不存在` | `jobs.run_job` | — | 运维 |
| `OPS_REVIEW_LOCK` | start | `交付复审进行中`（仅同步 ZIP→验圈合卷；须重出包→先结束复审） | `delivery_review.forbid_full_rebake` | — | 有 |
| `RESUME_NO_WORKSPACE` | copy_bake+ | `工作区不存在，无法续跑` | `jobs.run_job` 续跑 | — | 有 |
| `BAKE_SCHEMA_NF` | copy_bake / gate | `库表须满足 3NF` / p3n | `bake/gates/schema_nf.py` | `p3n` | 有 |
| `BAKE_TABLE_BUDGET` | copy_bake / gate | `表数量=` / 低于下限 / 超过硬顶 / p3t | `bake/engine_sql.py` | `p3t` | `test_table_budget` |
| `BAKE_ARCHIVE_COLUMNS` | copy_bake / gate | `档案语义列未对齐` / p3ac | `bake/archive_columns.py` | `p3ac` | 有 |
| `BAKE_ARCHIVE_SEED` | copy_bake | `INSERT IGNORE 演示种子` / `缺少 archive_item_table` | `bake/archive_seed_guard.py` | — | 有 |
| `BAKE_IDENTITY` | copy_bake | `身份/壳未对齐` | `bake/identity_align.py` | — | 有 |
| `BAKE_MENU_ROUTES` | copy_bake / p2 | `菜单/路由未对齐` | `bake/menu_routes.py` | `p2` | 有 |
| `BAKE_HARD_ASSERT_UI` | copy_bake | `硬拦与收集 UI 未对齐` | `bake/schema/hard_assert_ui.py` | — | 有 |
| `BAKE_SKIN` | copy_bake | `错皮/怪交互硬闸失败` | `bake/skin_invariants.py` | — | 有 |
| `BAKE_TRADE_SURFACE` | copy_bake | `refundReasonOptions` | `bake/features/trade_thicken.py` | — | 有 |
| `BAKE_USECASE` | copy_bake / fill | `usecase:` | `bake/schema/usecases.py` | — | 有 |
| `BAKE_PERSISTENCE` | copy_bake | `persistence=mybatis/jpa 包仍含` | `bake/persistence.py` | — | 有 |
| `BAKE_ADDON_SECURITY` | copy_bake | `spring-boot-starter-security` / `Security 叠层缺少` | `bake/addons.py` | — | 有 |
| `BAKE_PACK_LEAN` | copy_bake / gate | `pack_prune` / 未挂岛 / 工厂注记 / 壳件不符 / p3lean | `bake/pack_prune.py` | `p3lean` | 有 |
| `FILL_MERGE` | island_fill | `island merge` / `填岛合并失败` | `llm/unit_flow/merge.py` | — | 有 |
| `BUILD_SKELETON` | build_verify | `骨架不完整` | `llm/agents_fix.py` | — | 有 |
| `BUILD_COMPILE` | build_verify | `编译失败` / `mvn compile timeout` | `llm/agents_fix.py` | — | 有 |
| `GATE_ACCEPT` | gate_e2e | 可接题边界 / accept | `bake/gates/evaluate.py` accept | `accept` | 有 |
| `GATE_SCHEMA` | gate_e2e | Domain Schema / p3c / p3b | `bake/gates/evaluate.py` | `p3c`/`p3b` | 有 |
| `GATE_E2E_PATH` | gate_e2e | 领域主流程 E2E / 缺文件·路由·逻辑 / p2·p1·p0 | `bake/gates/evaluate.py` | `p2` 等 | 有 |
| `GATE_ADMIN_BOUNDARY` | gate_e2e | 总管/子管 / p3d | `bake/gates/evaluate.py` | `p3d` | 有 |
| `GATE_STUDENT_COPY` | gate_e2e | 说明书口吻 / p3copy | `bake/gates` + FACTORY_UI | `p3copy` | 有 |
| `GATE_SEMANTIC` | gate_e2e | 「演示」字样 / 场景资料穿帮 / p3s | `bake/gates/semantic.py` | `p3s` | 有 |
| `GATE_CHECKLIST` | gate_e2e | 清单实装 / p3a | `bake/gates/evaluate.py` | `p3a` | 有 |
| `GATE_QA` | gate_e2e | 交付质量摘要 / N 项 error / p3q | `services/delivery_review` + domain_vocab | `p3q` | 有 |
| `GATE_GENERIC_UNREALIZED` | gate_e2e | `该领域尚未做实，禁止交付` | 域实现 / evaluate | — | 有 |
| `GATE_OVERALL` | gate_e2e | `质量检查未通过` 且细项不明 | `jobs._gate_fail_summary` | `overall` | 有 |
| `MATCH_PATH` | 预 bake / parse | `未知身份场景` / `未知主路径入口` | `bake/match_path_axes.py` | — | 有 |
| `STUDENT_DB` | copy_bake meta | `无法连接学生 MySQL` / `执行 schema.sql 失败` | `services/student_db.py` | — | **当前不写 job.failed**，仅元数据/文档 |
| `UNKNOWN` | 任意 | 未命中上表 | **待补码表**（无假 A 档） | — | 补 stem 后入库 |

---

## 归桶规则（实现序）

1. 运维固定句（重启 / 取消 / 项目不存在 / 复审锁）  
2. 若传入 `project.gates`：按与 `_gate_fail_summary` 同序找首个 `ok=false` → 映射码  
3. `质量检查未通过` 前缀 + 文案细项  
4. copy_bake / fill / build stem 前缀表  
5. `UNKNOWN`；可并族提示 `looks_like_code`（只读已有码）

---

## B 档工作流

1. 页内点「修法建议」→ DeepSeek 出 `fix_draft`（注入该码 A 档落点，禁止改学生包）  
2. 标「未核对·勿直接当依据」  
3. 胡说 → **丢弃**；值得一试 → 扔 Cursor 核对现网  
4. 确认可行 → 人下令改本表 + `FIX_LOCUS` + 测（无自动升格 API）

---

## 修订

| 日期 | 说明 |
|------|------|
| 2026-10-21 | 立册：与失败分析看板同批 |
