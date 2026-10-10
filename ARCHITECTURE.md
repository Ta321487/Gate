# 毕设港 · 系统架构图

> **本文只负责**：用图讲清系统怎么分层、一次「上传 → 交付」在哪些进程之间跑。
> 产品是什么 / 怎么跑 → [README.md](./README.md) · 专题索引 → [docs/README.md](./docs/README.md) · 新对话交接 → [HANDOFF.md](./HANDOFF.md)

一句话概括：**一个运营中台（FastAPI + Vue 3）驱动一条确定性流水线，把开题材料烘成可答辩的学生工程（Spring Boot 3.2 + Vue 3 + MySQL），门禁不过就不放行 ZIP。**

- 可靠性来自**固定骨架 + 模板 + 门禁**；LLM 只填白名单「业务岛」，不写业务 Java / Vue。
- 两个数据库完全分离：**工厂元库**（项目/任务/用量，默认 SQLite）与**学生库**（每题一个 MySQL schema）。
- 三种不同性质的东西都叫「图」，别混：本文件是**工厂自身**的架构；学生对内交付物里另有**论文用** E-R / 类图 / 用例图（由 `app/bake/schema/` 生成）；`prototype/` 是运营端静态原型。

---

## 1. 总体架构（运行边界）

```mermaid
flowchart TB
    subgraph L1["① 使用者"]
        OP["运营 / 交付团队浏览器"]
        STU["学生（拿到 ZIP 后自己跑）"]
    end

    subgraph L2["② 运营前端 frontend/ · :5173 · Vue 3 + Naive UI + Vite"]
        FE_VIEW["views/ 项目 · 详情 · 任务 · 大模型 · Unsplash · 运行环境 · 帮助"]
        FE_DETAIL["views/projectDetail/ · 匹配 / 生成 / 产物 / 运行 / 日志"]
        FE_API["api.js（axios baseURL=/api）+ SSE 进度订阅"]
    end

    subgraph L3["③ 运营后端 backend/ · :8000 · FastAPI"]
        API_PROJ["api/projects/ · 上传分堆 · 匹配 · 生成 · 下载 · 运行"]
        API_JOBS["api/jobs · 任务队列 · 取消 / 重试"]
        API_SYS["api/system* · 大模型 / 用量 / 环境 / 端口"]
        API_PPT["api/defense_ppt · 答辩 PPT"]
        SVC["services/ · 编排层<br/>projects · jobs · runtime · delivery_review · proposal"]
    end

    subgraph L4["④ 生成核心 backend/app/bake · 确定性 bake"]
        BAKE_ENG["engine_bake.py<br/>复制 baseline → 叠加域 / 持久层 / 能力"]
        BAKE_SQL["sql/ · DOM-*.sql 模板 + compose 拼 GENERIC"]
        BAKE_SCH["schema/ · 壳 / ER / 模块 / 用例 / 测试用例"]
        BAKE_GATE["gates/ · 门禁 p0a…p3q + overall"]
        SCENE["scene_scan.py · 场景身份唯一真源"]
    end

    subgraph L5["⑤ LLM 层 backend/app/llm · 只填白名单岛"]
        LLM_FLOW["unit_flow/ · Plan → Unit 并发 → Merge"]
        LLM_AG["agents_* · match / island / usecase / fix / qa / sample"]
        LLM_RT["client · runtime · model_catalog（DeepSeek / Gemini）"]
    end

    subgraph L6["⑥ 工厂元库"]
        META["默认 SQLite data/factory.db<br/>或 MySQL（docker-compose）"]
    end

    subgraph L7["⑦ 运行预览沙箱 backend/app/services/runtime.py"]
        RT_BE["学生后端进程 · 端口池 9100–9120"]
        RT_FE["学生前端 Vite · 端口池 9200–9220"]
    end

    subgraph L8["⑧ 学生交付物 data/workspace/&lt;project_id&gt;/"]
        DEL_BE["backend/ · Spring Boot 3.2 + JDK 17"]
        DEL_FE["frontend/ · Vue 3 + Element Plus"]
        DEL_SQL["sql/ · 库表与种子数据"]
        DEL_ZIP["ZIP（门禁通过才可下载）"]
    end

    subgraph L9["⑨ 外部依赖"]
        DS["DeepSeek API"]
        GEM["Gemini API（可选，双开互备）"]
        UNS["Unsplash（可选，失败用本地色板）"]
    end

    DB_STU[("学生 MySQL<br/>每题一个 schema")]

    OP --> FE_VIEW --> FE_DETAIL --> FE_API
    FE_API -->|HTTP /api| API_PROJ
    FE_API -->|轮询 + SSE| API_JOBS
    FE_API --> API_SYS
    FE_API --> API_PPT
    API_PROJ --> SVC
    API_JOBS --> SVC
    API_SYS --> SVC
    API_PPT --> SVC
    SVC --> META
    SVC --> BAKE_ENG
    BAKE_ENG --> BAKE_SQL
    BAKE_ENG --> BAKE_SCH
    BAKE_ENG --> SCENE
    SVC --> LLM_FLOW --> LLM_AG --> LLM_RT
    LLM_RT --> DS
    LLM_RT --> GEM
    BAKE_SCH -.->|本地色板兜底| UNS
    SVC --> BAKE_GATE
    BAKE_ENG --> DEL_BE
    BAKE_ENG --> DEL_FE
    BAKE_ENG --> DEL_SQL
    SVC -->|门禁通过后打包| DEL_ZIP
    DEL_ZIP -->|交给学生| STU
    SVC --> RT_BE --> DEL_BE
    SVC --> RT_FE --> DEL_FE
    RT_BE --> DB_STU
    DEL_SQL --> DB_STU
    STU --> DB_STU
```

**读图要点**

| 边界 | 说明 |
|---|---|
| 进程隔离 | 运营后端（Python）与学生工程（JVM + Node）是**两类进程**；工厂只负责启停与探活，不把学生代码跑在自身事件循环里 |
| 端口池 | 学生后端 `9100–9120`、前端 `9200–9220`；`GF_PREVIEW_MAX_RUNNING` 限制**同时运行**数，不限制选题库存 |
| 数据分离 | 工厂元库管运营状态；学生库由 `services/student_db.py` 建库建表灌种子，删项目时按规则回收 |
| LLM 边界 | LLM 只产出白名单 island / 标签 / 用例等 **schema JSON**；业务 Java / Vue 由骨架与模板决定 |

---

## 2. 一次生成 Job 的六步流水线

`services/jobs.py` 的 `STEP_DEFS` 是唯一真源；`run_job()` 在单进程 asyncio 里串行推进，每步把状态写回 `jobs.steps` 供前端渲染步骤条。

```mermaid
flowchart LR
    U["上传材料<br/>PDF / Word / TXT"] --> PLAN["分堆方案<br/>upload/plan"]
    PLAN --> CONF["确认分堆<br/>upload/confirm"]
    CONF --> MATCH["匹配推荐<br/>骨架 × 领域"]
    MATCH --> GEN["POST /{id}/generate<br/>建 Job"]

    subgraph JOB["生成 Job · STEP_DEFS（六步）"]
        direction TB
        S0["1 parse_merge<br/>解析开题 · 合并 Spec"]
        S1["2 copy_bake<br/>复制骨架 · 领域 SQL"]
        S2["3 island_fill<br/>业务配置填充"]
        S3["4 build_verify<br/>构建验证"]
        S4["5 gate_e2e<br/>门禁：登录 + 主流程"]
        S5["6 pack<br/>清单验收 · 打包 ZIP"]
        S0 --> S1 --> S2 --> S3 --> S4 --> S5
    end

    GEN --> S0
    S5 --> DONE["zip_ready = true<br/>status = generated"]
    S4 -->|overall = false| FAIL["status = failed<br/>禁止下载 ZIP"]
    FAIL -->|从失败步续跑| S2

    DONE --> REVIEW["交付复审<br/>验圈 / 合卷 / 登记偏差"]
    DONE --> PPT["答辩 PPT Job（旁路 kind=defense_ppt）"]
    REVIEW --> DELIVER["delivery_mark<br/>人工履约标记"]
```

**每步实际在做什么**

| 步 | 关键实现 | 产物 / 副作用 |
|---|---|---|
| 1 `parse_merge` | `services/proposal.py`、`proposal_diff.py` | 合并后的开题文本、`spec` 契约 |
| 2 `copy_bake` | `bake/engine_bake.py` → 复制 `skeletons/baseline`，叠加 `skeletons/overlays/*`（mybatis / jpa / spring-security）与域 SQL | `data/workspace/<id>/` 完整工程骨架；`student_db.ensure_student_schema` 建库建表 |
| 3 `island_fill` | `llm/unit_flow/`：`build_delivery_plan` → 并发跑 Unit → `merge` 写回 workspace | 白名单岛文案、角色、E-R / 模块 / 用例标签；`fill_event_hub` 推 SSE |
| 4 `build_verify` | `llm/agents_fix.py` 的 `run_fix_agent` | 构建与修复轮次（`fix_rounds_max`） |
| 5 `gate_e2e` | `bake/gates/evaluate.py` 的 `evaluate_domain_gates` + `delivery_review.evaluate_workspace_gates` + QA Agent | `projects.gates`、`projects.checklist`；`overall` 决定能否打包 |
| 6 `pack` | `delivery_review.finalize_pack` → `jobs.pack_zip` | 临时文件写完再原子替换的 ZIP；排除 `node_modules` / `target` / `.git` / `islands` / `.factory` |

**门禁键（交付闸）**：`p0a` 后端骨架、`p0b` 前端骨架、`p1` 登录基线、`p2` 领域主流程 E2E、`p3a` 清单实装、`p3b` Spec/契约一致、`p3t` 技术栈、`p3d` 文档、`p3s` 语义、`p3n` 库表、`p3q` 质量摘要；外加可接题边界 `accept`。单调性键见 `bake/gates/keys.py`，复审期间由 `forbid_full_rebake` 拦截整段重跑。

---

## 3. 任务状态机

```mermaid
stateDiagram-v2
    [*] --> queued: 建 Job
    queued --> running: run_job 取到
    running --> success: 六步全过
    running --> failed: 任一步异常 / 门禁不过
    running --> cancelled: POST /cancel
    failed --> running: POST /retry（带 from_step 续跑）
    success --> [*]
    cancelled --> [*]
    failed --> [*]: 服务重启 → fail_orphaned_jobs 兜底
```

- 进度：`progress = (已完成步 + 当前步 0.5) / 6 × 100`，每步 `set_step` 即 `commit`，前端短轮询 + SSE 双通道读。
- 重启兜底：`fail_orphaned_jobs()` 把库里仍 `running/queued` 但内存无 Task 的任务标失败，避免进度条永远卡住（如停在 `pack=91%`）。
- 旁路：`kind=defense_ppt` 的 Job 走 `services/defense_ppt/job_runner.py` 自己的 5 步（证据 → 填页 Unit → 采图 → 瞎写/结构检查 → 写 `deck.json`），**不得**改动 `project.status` / `zip_ready`。

---

## 4. 运营前端结构（`frontend/src/`）

```mermaid
flowchart TB
    MAIN["main.js<br/>createApp + naive 全量安装 + initTheme + 全局 errorHandler → /error/500"] --> APP["App.vue · 唯一布局壳<br/>侧栏（工作区 / 系统两组）+ 面包屑 + 暗色切换 + router-view"]
    APP --> RT["router.js（createWebHistory）"]

    RT --> V1["/ 项目 Projects.vue"]
    RT --> V2["/projects/:id 详情 ProjectDetail.vue"]
    RT --> V3["/jobs 任务队列 Jobs.vue"]
    RT --> V4["/llm 大模型 Llm.vue（/deepseek /gemini 重定向到此）"]
    RT --> V5["/unsplash · /system · /help"]
    RT --> V6["/error/500 · 404 兜底 ErrorPage.vue"]

    V2 --> PD["views/projectDetail/<br/>useProjectDetail() 统一下发上下文（provide PD_KEY）"]
    PD --> T1["MatchTab 骨架 × 领域 × 身份场景"]
    PD --> T2["GenerateTab 生成 / soft-bake 选项 / 步骤轨"]
    PD --> T3["RuntimeTab 预览启停 + 日志"]
    PD --> T4["LogsTab 日志过滤"]
    PD --> T5["ArtifactsTab 库表 / 论文材料 / API / 复审 / 质量 / PPT"]
    T5 --> AV["图查看器组件<br/>ER · 模块 · 架构 · 序列 · 活动 · 类 · 用例 · 测试用例"]
    T2 --> PPM["components/defensePpt/ + ppt/<br/>答辩 PPT 面板与页预览"]

    V1 --> API["api.js · axios baseURL='/api'<br/>timeout 60s（重操作 600s / 轮询 8s 静默）"]
    V2 --> API
    V3 --> API
    V4 --> API
```

**前端约定（读代码可确认）**

| 维度 | 事实 |
|---|---|
| 技术栈 | Vue `^3.5.39` + vue-router `^4.6.4` + Naive UI `^2.44.1` + axios `^1.18.1` + jszip；Vite `^5.4.11` |
| **没有**的东西 | 无 Pinia / Vuex、无 TypeScript、无 ESLint 配置、无 `playwright.config.*`（装了没接线） |
| 状态管理 | 不用 store：`ProjectDetail.vue` 是薄壳，全部逻辑在 `views/projectDetail/useProjectDetail.js`，用 `provide(PD_KEY, …)` + `bindPd()` 下发给各标签页；各 Tab 不直接调 `api.*` |
| 壳的职责 | `App.vue` 同时是布局与导航（无单独 layout 组件）：侧栏「项目 / 任务队列 / 帮助文档」+「大模型 / Unsplash / 运行环境」，面包屑由 `route.meta.crumb` 推导 |
| 错误处理 | axios 响应拦截器统一 `message.error`；`silent: true` 用于轮询不刷屏；未捕获异常经 `app.config.errorHandler` 跳 `/error/500` |

**实时性机制（两条通道，都不是 WebSocket）**

| 场景 | 机制 | 参数 |
|---|---|---|
| 任务队列页 | 定时轮询 `GET /jobs` | `setInterval` 3000 ms |
| 生成中的项目详情 | 轮询（`lite` 模式）+ SSE | 轮询 1500 ms（`pollInFlight` 防重入，连续 2 次失败提示「状态同步暂时中断」）；SSE `GET /api/projects/{id}/fill-events`，由进程内 `fill_event_hub` 推送 unit_started / unit_done / fill_complete / fill_failed，收到 `done|failed` 自动关闭 |
| 答辩 PPT 进度 | SSE + 轮询双保险 | SSE `GET /api/projects/{id}/defense-ppt/events`（独立 channel），同时 `setInterval(pollPptJob, 800)` |
| 预览启停 | 有限次轮询收敛 | 动作后 700 ms 轮询一次；`stop` 上限 8 s、`start/restart` 上限 90 s |
| 孤儿盘清理 | 轮询状态接口 | `GET /projects/purge-orphan-disk`，1200 ms 一轮、15 分钟上限 |

> 全程无 WebSocket、无 `fetch()`：进度靠轮询 + SSE，文件类（ZIP / 交接包 / PPTX / SVG / Markdown）走浏览器直达 URL，不走 axios。

**上传链路（前端）**：`uploadMaterials.js` 负责递归收集（拖拽用 `webkitGetAsEntry()`、`.zip` 用 jszip 动态展开、跳过 `__MACOSX` / `.DS_Store` / `~$`、大小写无关去重），**超过 8 份直接报错而不是截断**；`Projects.vue` 用客户端队列逐个上传 → `upload/plan` 出分堆方案 → 人工确认 → `upload/confirm` 建项目，未确认方案刷新后可从 `upload/plans` 恢复。

**开发期代理**：`frontend/vite.config.js` 把 `/api`、`/docs`、`/redoc`、`/openapi.json` 代理到 `VITE_API_PROXY || http://127.0.0.1:8000`；host 取 `VITE_HOST || GF_HOST || 127.0.0.1`。

---

## 5. 后端分层与模块职责

```mermaid
flowchart TB
    subgraph API["app/api · HTTP 边界（只做校验 / 编排调用）"]
        A1["projects/：common · crud · schema · runtime · delivery_review"]
        A2["jobs · system_router → deepseek / gemini / usage / info / tools / unsplash"]
        A3["defense_ppt"]
    end

    subgraph SERVICES["app/services · 业务编排（无 HTTP 依赖）"]
        SV1["projects 门面 → project_match / project_delivery / project_disk / project_projection"]
        SV2["jobs 任务执行器"]
        SV3["runtime + runtime_reconcile（进程与投影）"]
        SV4["delivery_review（复审 / 验圈 / 合卷）"]
        SV5["proposal · proposal_match · proposal_diff · upload_cluster"]
        SV6["student_db · student_copy · student_api_smoke"]
        SV7["defense_ppt/（planner · job_runner · export_pptx · figures · screenshots）"]
    end

    subgraph CORE["app/core"]
        C1["config.py · Settings（GF_* / LLM_* / 端口池 / 预算）"]
        C2["database.py · async engine + SessionLocal + create_all + 幂等 ALTER"]
        C3["key_mask.py"]
    end

    subgraph BAKE["app/bake · 纯函数为主，便于单测"]
        B1["engine*.py 入口（sql / bake / resources / islands 分册）"]
        B2["domains_catalog/ + domain_registry + domain_entities"]
        B3["schema/ · shells · builders_* · er_* · modules · usecases · testcases"]
        B4["sql/templates + compose + ddl_edit"]
        B5["gates/ · evaluate · semantic · schema_nf · feature_keywords"]
        B6["features/ · 能力加厚运行时"]
    end

    MODELS["app/models · Project / Job / LlmCall / SettingRow"]
    SCHEMAS["app/schemas · Pydantic 出入参"]

    API --> SERVICES
    SERVICES --> BAKE
    SERVICES --> MODELS
    API --> SCHEMAS
    SERVICES --> CORE
    BAKE --> CORE
    MODELS --> C2
```

**分层纪律（从代码注释可读出的约定）**

- `api/` 只做 HTTP；业务写进 `services/`；`services/projects.py` 是**门面**，正文按职责拆到 `project_match` / `project_delivery` / `project_disk` / `project_projection`，新逻辑不再往门面堆。
- `bake/` 尽量保持确定性、可单测；LLM 相关一律在 `llm/`。
- 启动生命周期（`main.py lifespan`）：`init_db()` → 回灌 DeepSeek 预算/模型设置 → `fail_orphaned_jobs()` → 启动后台对账 `start_runtime_reconcile()`，关闭时 `stop_runtime_reconcile()`。

---

## 6. 数据模型与磁盘布局

```mermaid
erDiagram
    PROJECT ||--o{ JOB : "project_id"
    PROJECT ||--o{ LLM_CALL : "project_id"

    PROJECT {
        string id PK
        string title
        string status "needs_confirm/ready/generating/generated/failed/running/archived"
        string domain "DOM-*"
        string archetype "ARCH-CRUD…"
        string persistence "jdbc/mybatis/jpa"
        bool spring_security
        bool ai_assistant
        bool match_locked
        json spec
        json gates
        json checklist
        string workspace_path
        string zip_path
        bool zip_ready
        string delivery_mark "none/ready/delivered"
        json delivery_review
        int backend_port
        int frontend_port
        bool backend_running
        bool frontend_running
    }
    JOB {
        int id PK
        string project_id FK
        string kind "bake/defense_ppt"
        string status "queued/running/success/failed/cancelled"
        string step
        int progress
        json steps
        json units
        text error
    }
    LLM_CALL {
        int id PK
        string project_id FK
        string stage
        int tokens
        bool ok
    }
    SETTING_ROW {
        string key PK
        json value
    }
```

```
data/
  factory.db           工厂元库（默认 SQLite；也可指本机 MySQL）
  uploads/             上传材料落盘
  workspace/<id>/      每题学生工程工作区（backend / frontend / sql / spec.json）
  workspace/<id>.zip   门禁通过后的交付包
  logs/<id>/           job.log · backend.log · frontend.log · deepseek.log
  cache/baseline-frontend/  共享 node_modules（目录联结复用到每题，避免每题重装）

data/workspace/<id>/.factory/   工厂内部产物：bake_in_progress 锁、defense-ppt 旁路树（不进 ZIP）
skeletons/
  baseline/            学生工程骨架（jdbc 默认）
  overlays/            mybatis / jpa / spring-security 叠加层
```

---

## 7. 运行时预览子系统

```mermaid
flowchart LR
    UI["前端「运行」标签页"] -->|"GET /{id}/runtime"| ST["RuntimeState"]
    UI -->|"POST /{id}/runtime/{side}/{action}"| ACT["start / stop"]
    UI -->|POST /runtime/batch| BATCH["批量启停（错峰 + 额度）"]
    ACT --> POOL["allocate_ports<br/>从空闲端口池取一对"]
    BATCH --> POOL
    POOL --> PREP["prepare_frontend_deps<br/>共享缓存 node_modules 软链"]
    POOL --> BE["start_backend<br/>mvn spring-boot:run · 注入 GF_STUDENT_MYSQL_*"]
    POOL --> FE["start_frontend<br/>vite --port"]
    BE --> PROBE["探活：TCP / HTTP / 日志致命串"]
    FE --> PROBE
    PROBE --> PROJ["回写 projects.<side>_running / _port"]
    REC["runtime_reconcile 后台循环<br/>GF_RUNTIME_RECONCILE_SEC=5s"] --> PROBE
    REC --> PURGE["孤儿目录小额清盘<br/>GF_ORPHAN_PURGE_PER_PASS"]
```

**为什么这样设计**（见 `docs/preview-capacity-and-batch-ops.md`、`docs/background-reconcile-cost.md`）：学生预览一个实例就是一组 JVM + Node 进程，内存是硬约束，所以上了三重闸门：

1. **只读库**：列表 GET 与 `/stats` 不扫盘、不探活；真实运行态由后台 `runtime_reconcile` 每 `GF_RUNTIME_RECONCILE_SEC` 对账回写（投影输入签名 + 20s TTL + 每轮扫描额度，避免对账本身变贵）。
2. **内存闸门**：批量启动的额度 = `GF_PREVIEW_MAX_RUNNING − 实际在跑`，再被 `可用内存 ÷ 约 1.1 GB` 夹一次；超出额度的项返回 `deferred` 而不是硬起。
3. **错峰**：按 `GF_PREVIEW_START_STAGGER_SEC` 间隔依次启动，避开首次 Maven 编译吃满 CPU / 磁盘。

启动的学生后端带资源上限（`-Xmx320m -XX:MaxMetaspaceSize=192m -XX:TieredStopAtLevel=1`，`MAVEN_OPTS=-Xmx192m`），`mvn` / `pom.xml` 缺失时退化为内置 Python 桩，保证预览链路可演示。进程句柄只存在内存，所以停止时按「句柄 + 端口占用者」双重证据杀进程。

---

## 8. 交付闸与人工履约

```mermaid
flowchart TB
    G["门禁 overall 通过"] --> ZR["zip_ready = true（机器质检）"]
    ZR --> DM{"delivery_mark（人工履约）"}
    DM -->|none| N1["不可下载"]
    DM -->|ready 已审待发| N2["可下载，未视为已交学生"]
    DM -->|delivered 已发出| N3["已交学生"]
    ZR --> RV["交付复审 delivery_review"]
    RV --> V1["验圈 verify：重跑门禁 + 单调性比对"]
    RV --> V2["合卷 repack：重打学生 ZIP"]
    RV --> V3["登记偏差 fix_notes"]
    RV --> V4["清洗学生可见工厂腔 scrub-student-copy"]
    RV --> V5["导出运营交接包 handoff"]
```

**两套「通过」刻意分开**：`zip_ready` 是机器质检结论，`delivery_mark` 是人工履约动作。复审期间 `forbid_full_rebake` 禁止整段重跑生成，只能验圈 / 合卷，防止「基线修洞后 ZIP 仍是旧工程」。

---

## 9. 学生交付物内部结构

```mermaid
flowchart TB
    subgraph STU["data/workspace/&lt;id&gt;（= 交付 ZIP 内容）"]
        subgraph SE["backend/ · Spring Boot 3.2 · JDK 17"]
            SC["controller/ · REST 入口（Auth / 各业务）"]
            SS["service/ + capability/ · 业务与能力运行时"]
            SP["config/ · JdbcSupport / WebConfig / 上传 / 种子对齐"]
            SY["resources/application.yml + domain-*.json"]
        end
        subgraph SF["frontend/ · Vue 3 + Element Plus（zh-cn）"]
            FV["views/ + views/admin/"]
            FC["components/ · 通用组件"]
            FT["styles/themes/*.css · 按域配色"]
            FH["api/http.js + utils/"]
        end
        SQ["sql/ · 建库建表 + 种子数据"]
        SR["README.md · 运行说明"]
        SX["spec.json / domain.schema.json（工厂产物，不进 ZIP）"]
    end
    SQ --> MYSQL[("MySQL · 每题一个库")]
    SE --> MYSQL
    SF -->|/api| SE
```

- 骨架**不含** `node_modules` / `target` / `dist`：`bake_project` 的 `copytree(ignore=…)` 明确跳过，前端依赖由预览子系统按共享缓存挂载，Maven `target` 由编译再生。
- 持久层由 `bake/persistence.py` 决定：默认 `jdbc`（JdbcTemplate），开题点名时切 `mybatis` / `jpa`，并按需叠 `addon-spring-security`。
- 场景身份（校园 / 企业 / 社区）由 `bake/scene_scan.py` 的 `scene_for(domain, title, proposal)` 统一决定，壳文案与注册资料页必须读同一 scene——**禁止改开题迁就模板**。

---

## 10. 外部依赖与降级

| 依赖 | 用途 | 缺失 / 失败时 |
|---|---|---|
| DeepSeek API | 匹配推荐、填岛、标签、QA、Fix、样例题 | 无 Key 仍可 bake：业务岛走确定性填充 |
| Gemini API（可选） | 与 DeepSeek 并存，可双开，优先一家失败自动换 | 单开时按 `LLM_PROVIDER` / 运营台开关 |
| Unsplash | 登录氛围图、门户轮播 | 按 `themes.css` 色板本地生成 |
| MySQL | 学生库必用；工厂元库可选 | 工厂元库退化为 SQLite `data/factory.db` |

---

## 11. 部署与启动链路

```mermaid
flowchart LR
    L["scripts/launcher.bat<br/>（有 Windows Terminal 则同窗标签页）"] --> B["start-backend → uvicorn :8000"]
    L --> F["start-frontend → vite :5173"]
    B --> H["GET /api/health"]
    F --> P["vite proxy /api → 127.0.0.1:8000"]
    D["docker compose up -d<br/>MySQL 8（可选）"] --> B
```

- 生产 / 局域网：`GF_HOST=0.0.0.0`，`GF_PUBLIC_HOST` 填对外 IP 或域名，学生进程会自动绑 `0.0.0.0`；`GF_BIND_HOST` 可强制覆盖。
- 运营端**本身无登录鉴权**，默认按内网运营工具用；`/docs`、`/redoc` 仅供调试，勿与学生 ZIP 内的 Spring 接口混淆。

---

## 附：关键配置速查

| 变量 | 作用 | 默认 |
|---|---|---|
| `GF_DATABASE_URL` | 工厂元库 | `sqlite+aiosqlite:///data/factory.db` |
| `GF_DATA_DIR` / `GF_SKELETONS_DIR` | 数据目录 / 骨架目录 | `data` / `skeletons` |
| `GF_HOST` / `GF_PORT` | 工厂 API 监听 | `127.0.0.1` / `8000` |
| `GF_BACKEND_PORT_START/END` | 学生后端端口池 | `9100` / `9120` |
| `GF_FRONTEND_PORT_START/END` | 学生前端端口池 | `9200` / `9220` |
| `GF_STUDENT_MYSQL_*` | 学生库连接 | `root` / `root123` @ `3306` |
| `GF_PREVIEW_MAX_RUNNING` | 同时运行预览上限 | `3` |
| `GF_PREVIEW_START_STAGGER_SEC` | 批量启动错峰 | `4.0` |
| `GF_FILL_UNIT_CONCURRENCY` | 填岛 Unit 并发 | `3`（代码内夹在 1–8） |
| `GF_RUNTIME_RECONCILE_SEC` | 后台对账间隔 | `5.0`（`<=0` 关闭） |
| `GF_ORPHAN_PURGE_PER_PASS` | 每轮清孤儿目录数 | `1` |
| `GF_QA_WARN_BLOCKS_PACK` | QA 告警是否拦打包 | `true` |
| `LLM_PROVIDER` / `DEEPSEEK_*` / `GEMINI_*` | 大模型配置 | DeepSeek 开、Gemini 可选 |
