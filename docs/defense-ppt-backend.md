# 答辩 PPT：后端实现指导

> **状态**：前端运营端已落地（`frontend/src/ppt/*` + 挂载点）；本文件是后端对接与实现口径。  
> **产品设计**：见 [`defense-ppt-module.md`](./defense-ppt-module.md)（勿与本文重复拍板；冲突以产品设计为准，契约字段以本文 + 现网前端为准）。  
> **前端契约真源**：[`frontend/src/api.js`](../frontend/src/api.js)（`defense-ppt*`）、[`frontend/src/ppt/types.js`](../frontend/src/ppt/types.js)、[`frontend/src/ppt/pptClient.js`](../frontend/src/ppt/pptClient.js)。  
> **联调**：后端未齐前可用 `VITE_PPT_MOCK=1` / 404 降级演示；**后端全部完成后必须移除 mock**（见 §1.4）。

---

## 0. 一句话

**独立短任务**：在 bake 可下载（与 ZIP 同口径）之后，生成 `deck.json` → 对照收口 → 检查 → **单独导出 PPTX（永不进学生 ZIP）**。

LLM **只整形**开题∪实包∪产物图，禁止编造模块/中间件/技术名。手段对齐现有 `unit_flow`（裁剪、校验、`source_refs`、门禁）。

---

## 1. 一套实现（强制；禁止第二套）

答辩 PPT **挂在现网链路上**，是 `delivery_review` / 填岛同级的旁路模块，**不是**第二套任务系统、第二套 SSE、第二套材料扫描。

| 维度 | 强制做法 | 禁止 |
|------|----------|------|
| **任务进度** | `jobs` 表 + `kind=defense_ppt`；`start_ppt_job()` / `run_ppt_job()`；`GET …/defense-ppt/job` **只读 Job 行** | 以 workspace `job.json` 作主真源；另写一套进度状态机；**直接调用** bake 的 `start_job()`（会把 `project.status` 打成 `generating`、清 `zip_ready`） |
| **SSE** | 复用 `fill_events.FillEventHub` 同款模式：扩展 channel（`project_id`+类型）或薄封装 `ppt_event_hub`（同一文件/同一类） | 另起 Redis/ARQ、另写一套订阅总线 |
| **证据 evidence** | **只组装**现有读取：`load_merged_proposal_text`、schema/modules/er/testcases 既有服务与产物路径、`delivery_block_reason` / `gates` | 再写「PPT 专用扫描器」扫一遍开题/菜单/E-R |
| **就绪口径** | 与 ZIP 同：`delivery_block_reason` 空 / `gates.overall` | 另立运行探活作开跑条件 |
| **路由** | `/api/projects/{id}/defense-ppt/*`，挂在 projects 路由族 | 独立账号体系、新开主 Tab 后端 |

### 1.1 任务：`Job.kind` + 独立 runner（必读）

现网 bake：`services/jobs.py` 的 `start_job` → `run_job`，会：

- 写 `jobs` 表  
- 设 `project.status = generating`  
- `zip_ready = False`  

PPT **不得**走这条入口。正确拆法：

1. `Job` 增加字段 `kind`（默认 `bake`；PPT 为 `defense_ppt`）。列表/清理逻辑按 `kind` 过滤，避免运营「任务」页把 PPT 误当成程序生成。  
2. 新增 `start_ppt_job(db, project)` / `run_ppt_job(job_id)`（可放在 `services/defense_ppt/job_runner.py`，或 `jobs.py` 内明确分支，**禁止**复用 `start_job` 函数体）。  
3. PPT 进行中：**不改** `project.status` 为 `generating`，**不清** `zip_ready`（程序交付态与 PPT 解耦）。  
4. `steps` 仍用 Job.steps（与 bake 同形）；页级 Unit 进度可放在 `steps` 某步的 `meta`、或 Job JSON 扩展字段（如 `units`），**真源仍是 Job 行**。  
5. 前端继续调 `/defense-ppt/job` 与 `/defense-ppt/cancel`：后端 **代理读写** `kind=defense_ppt` 的 Job，不必改前端去调 `/api/jobs`（`/api/jobs` 列表可顺带展示，但不是第二套进度源）。

workspace 内 **禁止** `job.json` 作为进度主源。若调试需要落盘快照，仅允许写在 `.factory/defense-ppt/debug/`，且实现与测试不得依赖它。

### 1.2 SSE：与填岛同一 hub 模式

现网：`services/fill_events.py` 的 `FillEventHub` + `GET /projects/{id}/fill-events`。

PPT：

- **首选**：给 hub 增加 `channel`（如 `fill` | `defense_ppt`），`subscribe(project_id, channel=…)`；`GET /defense-ppt/events` 订阅 PPT channel。  
- **可接受**：同文件内 `ppt_event_hub = FillEventHub()` 第二实例（类复用，不是第二套协议）。  

前端已 poll `GET /job`；SSE 为加速，**缺 SSE 不阻塞 MVP**，但一旦做 SSE 必须走上述模式。

### 1.3 证据：只组装，不重扫

`evidence` 与 collect 上下文 **禁止**另起扫描器。映射：

| evidence 字段 | 复用 |
|---------------|------|
| `proposal` | `load_merged_proposal_text` / 项目 `source_path` 是否有材料（与 proposal-diff 同源） |
| `modules` | 既有 modules 产物 / `getModules` 同源逻辑（工作区模块图是否可出） |
| `er` | 既有 schema / ER SVG 同源逻辑 |
| `testcases` | 既有 testcases 同源逻辑 |
| `gates_overall` | `delivery_block_reason(project)` 为空（与 ZIP 可下载同口径） |

`services/defense_ppt/evidence.py` 的职责是 **布尔组装 + 给 LLM 裁剪上下文**，内部 `import` 现有 services，不得复制一份 parse 开题/抽表结构。

### 1.4 后端全部完成后：移除前端 mock（强制）

mock 仅作后端未就绪时的运营端演示 / 联调垫片，**不是**长期双轨。

当 §12 验收清单全部通过、真实 `/api/projects/:id/defense-ppt/*` 可支撑全流程后，**必须**做掉 mock，禁止继续靠降级「假装后端已齐」：

| 动作 | 说明 |
|------|------|
| 删 | `frontend/src/ppt/mockPptApi.js`、`smokeMockPpt.mjs`（若仅服务 mock） |
| 改 | `pptClient.js`：去掉 `VITE_PPT_MOCK`、404/501 自动降级；失败走正常错误提示 |
| 删 | `frontend/.env.development` 中的 `VITE_PPT_MOCK`（及相关说明） |
| 收 | UI「填演示封面」「演示标脏」等 **仅 mock** 入口一并去掉 |
| 验 | 关 mock 后运营端 locked→生成→对照→检查→导出 全走真接口 |

未完成移除不得宣称「答辩 PPT 后端已交付」。

---

## 2. 与现网边界（禁止踩线）

| 做 | 不做 |
|----|------|
| `kind=defense_ppt` 的独立 Job | 塞进 bake 同次流水线；调用 `start_job()` |
| 工作区旁路 `.factory/defense-ppt/` | PPTX 打进学生 ZIP；进度靠 `job.json` |
| 就绪 = bake 可下载同口径 | 另立「运行探活」作开跑条件 |
| 业务指纹脏 → 禁导出 | 换主题/版式标脏 |
| 页级 Unit + Semaphore，挂 `unit_flow` 手段 | 整仓搬 LangChain / ARQ-Redis |
| FillEventHub 同款 SSE（可选） | 新订阅总线 |
| 半自动主路径截图 + 对照换图 | 无人值守乱爬全站 |
| 后端齐后 **移除** 前端 mock | 真接口已齐仍保留 `VITE_PPT_MOCK` / 404 降级双轨 |

场景轴 / 技术栈轴仍走既有规则；PPT **不得**驱动 `scene_scan`，不得改 `ARCH-*` / 领域。

---

## 3. 目录与落盘

```
backend/app/
  api/defense_ppt.py              # 路由；include 到 projects 前缀下
  models/                         # Job.kind 字段（bake | defense_ppt）
  services/jobs.py                # bake 仍走 start_job；PPT 禁止调用
  services/fill_events.py         # hub 扩展 channel 或 ppt 实例
  services/defense_ppt/
    __init__.py
    status.py                     # phase / evidence 组装 / 摘要
    cover.py                      # 封面校验与校徽存储
    job_runner.py                 # start_ppt_job / run_ppt_job（读 Job 表）
    deck_io.py                    # 读写 deck.json
    fingerprint.py                # 业务指纹计算与标脏
    sync_biz.py                   # 按工程更新（跳过 locked）
    check.py                      # error/warning → can_export
    export_pptx.py                # python-pptx 渲染
    screenshots.py                # 半自动采图 / 上传替换
    themes.py                     # 主题包 / 版式族 / 母版壳
    evidence.py                   # 组装现有 proposal/schema/modules/…（禁止重扫）
```

**工作区旁路**（勿写入学生交付根导致误打进 ZIP）：

```
{workspace}/.factory/defense-ppt/
  deck.json
  cover.json                  # 或并入 deck.cover
  fingerprint.json            # 上次生成时业务指纹
  badge/
    original.png
    current.png
  figures/
    modules.svg               # 引用或拷贝既有产物，勿另生成语义
    er.svg
    shots/
      demo-login.png
      ...
  export/
    defense.pptx              # 导出缓存（可选）
  debug/                      # 可选；禁止当作进度真源
```

ZIP 打包须 **排除** `.factory/`（若尚未排除，实现时一并改）。

---

## 4. 状态机 `phase`

与前端一致：`locked | ready | generating | done | dirty`

| phase | 条件（后端判定） |
|-------|------------------|
| `locked` | 不可下载（`delivery_block_reason` 非空）或 evidence 不全 |
| `ready` | 可下载 + 无进行中 `kind=defense_ppt` Job +（尚无 deck 或允许再生成） |
| `generating` | 存在 `kind=defense_ppt` 且 `queued|running` 的 Job |
| `done` | 有 deck 且 `biz_dirty=false` |
| `dirty` | 有 deck 且业务指纹与当前工程不一致 |

前端会用项目的 `canDownload` 再盖一层展示；后端 `evidence.gates_overall` 必须与「可下 ZIP」同源。

缺任一项开跑 → `409`；UI 用红/绿 pill。

---

## 5. HTTP 契约（必须对齐前端）

前缀：`/api/projects/{project_id}/defense-ppt`  
鉴权 / 项目归属：与现网 projects 路由一致。

### 5.1 `GET /`

状态摘要。进行中或最近一次 PPT Job 写入 `job` 字段（从 `jobs` 表读）。

```json
{
  "phase": "ready",
  "evidence": {
    "proposal": true,
    "modules": true,
    "er": true,
    "testcases": true,
    "gates_overall": true
  },
  "cover": {
    "school": "",
    "college": "",
    "class_name": "",
    "student_name": "",
    "student_id": "",
    "advisor": "",
    "badge_data_url": null
  },
  "theme": "scholar",
  "layout_family": "band",
  "master": "none",
  "biz_dirty": false,
  "has_deck": false,
  "page_count": 0,
  "job": null,
  "title": "某某管理系统的设计与实现",
  "deck_summary": ""
}
```

`deck_summary`：`"{n}页 · {theme} · {layout_family}"`。  
主题种子：`project_id` hash → `scholar|ink|grove` × `band|center|footer`（与前端 mock 一致）。

### 5.2 `PUT /cover`

Body = cover（JSON；校徽 data URL，MVP 可接受）。六字段 + 校徽齐，否则 `400`。落盘；有 deck 则同步 cover 页。返回 status。

### 5.3 `POST /generate`

Body：`cover?` + `theme` / `layout_family` / `master`。

门闩：可下载 ✓ · evidence 齐 ✓ · cover 齐 ✓ · 无进行中 PPT Job（或先 cancel）。

成功：`start_ppt_job` → 返回 `job_id` + `phase=generating` + job 快照。  
失败：`400` 封面；`409` 未就绪。

MVP：覆盖写 `deck.json`；不做多版本。

### 5.4 `GET /job`

**只读**该项目最新 `kind=defense_ppt` 的 Job，映射为前端形状：

```json
{
  "id": 87,
  "progress": 60,
  "status": "running",
  "error": null,
  "steps": [
    { "key": "collect", "title": "收集证据…", "status": "done", "meta": "" },
    { "key": "fill", "title": "填页 Unit…", "status": "running", "meta": "" },
    { "key": "screenshots", "title": "采集界面截图…", "status": "pending", "meta": "" },
    { "key": "check", "title": "瞎写/结构检查", "status": "pending", "meta": "" },
    { "key": "write", "title": "写 deck.json", "status": "pending", "meta": "" }
  ],
  "units": [
    { "key": "ppt.cover", "title": "封面", "status": "done" },
    { "key": "ppt.modules", "title": "功能模块", "status": "generating", "meta": "嵌模块图" },
    { "key": "ppt.demo", "title": "实现与演示", "status": "queued" }
  ]
}
```

Job.status 用现网枚举：`queued|running|success|failed|cancelled`（对外可把 `success` 映射为前端习惯的 `succeeded`，二选一写死并与前端 mock 对齐）。  
无 PPT Job → `404` 或 `null`（与前端约定一致即可，建议 `200` + `null` 或空对象时在 status 里 `job: null`）。

**不要**再维护一份与 Job 并行的进度文件。

### 5.5 `GET /events`（SSE）

同 §1.2。事件形态可对标 fill：`unit_started` / `unit_done` / … + PPT 完成帧。无 SSE 时前端靠 poll。

### 5.6 `POST /cancel`

`cancel_ppt_job`：只取消 `kind=defense_ppt`；**不得**误伤 bake Job；**不得**把 `project.status` 从 `generating` 乱改（除非当前本来就不是因 bake 在生成）。

### 5.7 `GET /deck`

完整 `deck.json`。无 → `404`。

### 5.8 `PATCH /deck/pages/{page_id}`

局部更新 bullets / locked / cover / figure。返回单页。人手改过的 bullet 带 `locked`；sync 跳过。

### 5.9 `PATCH /skin`

`{ "theme", "layout_family", "master" }`。只改皮，**不标** `biz_dirty`。

### 5.10 `POST /sync-biz`

未锁定块按开题∪实包重填；保留皮。响应含 `updated` / `kept` / `message`。锁定冲突 → check `warning`（`locked_conflict`）。

### 5.11 `POST /check`

```json
{
  "items": [
    { "level": "error", "code": "demo_shot", "message": "演示页缺主流程界面截图（禁导出）" },
    { "level": "warning", "code": "verbose", "message": "部分要点字数偏多" },
    { "level": "ok", "code": "deck_ok", "message": "deck.json 结构完整" }
  ],
  "can_export": false
}
```

`can_export` ⇔ 无 error ∧ 可下载 ∧ 未脏 ∧ 有 deck。

| code | 含义 |
|------|------|
| `no_deck` | 无 deck |
| `gates` | bake 门禁不过 |
| `biz_dirty` | 业务指纹脏 |
| `demo_shot` | 缺主流程截图（默认 **error**） |
| `hallucination` | 技术/模块不在实包 |
| `structure` | 大纲不合模板 |

### 5.12 `GET /export`

附件 `.pptx`；服务端再跑 check 等价门闩，不过 → `409`。**禁止**写入学生 ZIP。

### 5.13 截图

`POST /screenshots/capture-current`：`{ "page_id"? }`；半自动主路径；失败 → `figure.missing=true`。  
`POST /screenshots/upload`：`{ "page_id", "data_url" }`。

---

## 6. `deck.json` 口径

Web 预览与 PPTX **同一份**。字段对齐前端 JSDoc（`version` / `theme` / `layout_family` / `master` / `cover` / `pages[]` / `biz_dirty`）。

**页角色** `role`：`cover|toc|section|bullets|two-column|table|modules|er|demo|summary`

默认大纲：

```
封面 → 目录 → 背景与需求 → 技术选型 → 系统架构
  → 功能模块 → E-R → 实现与演示 → 测试 → 总结与致谢
```

Unit key：`ppt.cover` … `ppt.summary`（与前端 mock 对齐）。  
部分 Unit 失败：保存已成功页；Job 可 `failed` 但保留部分 deck。

---

## 7. 生成流水线（挂 unit_flow，不整包搬）

Job.steps 建议：

1. **collect**：调用 §1.3 组装函数取开题/菜单/栈/模块图/E-R/用例；写指纹快照  
2. **fill**：页级 TaskUnit；LLM 只出结构化要点；校验 ⊆ 证据；`source_refs`；Semaphore 对标填岛；**共用**项目 LLM 预算与 `llm_calls`  
3. **screenshots**：半自动截图（可与 fill 并行或紧后）  
4. **check**：反瞎写 + 结构 + 必要截图  
5. **write**：原子写 `deck.json`；清脏；Job `success`；progress=100  

导出：`python-pptx`；字体优先微软雅黑/宋体。

---

## 8. 业务指纹与标脏

**计入**：重 bake / 合卷；persistence / Security；菜单、features、模块树、用例、E-R 结构或实体中文名；开题正文变更。  
**不计入**：学生站视觉软选项；仅 PPT 换皮；日志/运行启停/运营备注。

钩子：bake / 合卷成功 → 有 deck 则比指纹，变则 `biz_dirty=true`（**保留 deck**）。`PATCH /skin` 不碰指纹。脏则 check error + export `409`。

---

## 9. 封面与校徽

cover 页固定；字段全齐才 generate。校徽前端粘贴为主；后端存 original/current。题名取自项目/开题。

---

## 10. 落地顺序

1. `Job.kind` 迁移 + `start_ppt_job` / `cancel_ppt_job`（确认 **不**动 `project.status` / `zip_ready`）  
2. `GET/PUT cover`、`GET status`、deck 落盘；evidence **只组装**现有服务  
3. `POST generate` + `GET job` + poll 联调（关 mock）  
4. fill Unit + 反瞎写；嵌既有模块图/E-R  
5. check / export（python-pptx）  
6. 截图 capture/upload；缺图 error  
7. 指纹钩子 + sync-biz  
8. SSE（FillEventHub channel）；学院母版、溢出检测  

每步：API 测试 + 关 `VITE_PPT_MOCK` 主路径冒烟。

---

## 11. 错误与前端

| HTTP | 前端 |
|------|------|
| `404` / `501` / `405`（模块未挂） | **仅后端未齐过渡期** pptClient 可降级 mock；后端齐后已无降级，按正常错误处理 |
| `400` | toast detail |
| `409` | 未就绪 / 禁导出 |
| Job `failed` | 面板展示 error |

API 多为 `silent: true`，`detail` 用清晰字符串。

---

## 12. 验收清单

- [ ] PPT Job 带 `kind=defense_ppt`；bake `start_job` 与 PPT 互不抢 `project.status` / `zip_ready`  
- [ ] 无 workspace `job.json` 进度依赖；`GET …/job` 只读 Job 表  
- [ ] evidence 仅组装现有 proposal/schema/modules/er/testcases/gates，无第二套扫描  
- [ ] SSE（若做）走 FillEventHub 同款，无第二套总线  
- [ ] 不可下载 → `locked` / generate `409`  
- [ ] 可下载 + 封面齐 → job → deck → 预览与导出同源  
- [ ] 换 skin 不标脏；bake 后脏 → 禁导；sync-biz 尊重 locked  
- [ ] 缺主流程截图 → check error；采/传后可导  
- [ ] PPTX 不进 ZIP；关 mock 运营端全流程可走  
- [ ] **后端全部完成后**：已按 §1.4 **移除** mock（`mockPptApi` / `VITE_PPT_MOCK` / 404 降级 / 仅 mock 的演示按钮）；未移除不得标交付完成  

---

## 13. 修订记录

| 日期 | 说明 |
|------|------|
| 2026-09-02 | 初稿：按已落地前端契约梳理后端指导 |
| 2026-09-02 | **收口一套实现**：强制 `Job.kind` + `start_ppt_job`；FillEventHub 同款 SSE；evidence 只组装现有服务；删除 job.json / 双进度源歧义 |
| 2026-09-02 | 强制：后端全部完成后须移除前端 mock（§1.4 + 验收项） |
