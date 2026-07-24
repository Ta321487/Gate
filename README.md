# 毕设港

面向专科/本科毕设与课设交付团队的 B 端运营中台：把开题、任务书等材料稳定加工成可答辩的 Web 管理系统（演示级；不接硕博课题与真实业务全流程）。

**运营端原型（在线预览版，手机可直接打开）：** [https://ta321487.github.io/Gate/](https://ta321487.github.io/Gate/)

**上传材料 → 匹配确认 → bake 生成 → 门禁质检 → ZIP 交付**

生成以确定性骨架 + 领域配置为主；LLM（DeepSeek）只填白名单「业务岛」，不写业务 Java/Vue。门禁未通过禁止下载 ZIP。

## 技术栈

| 端 | 技术 |
|---|---|
| 运营后端 | FastAPI + SQLAlchemy + SQLite（开发默认）/ MySQL |
| 运营前端 | Vue 3 + Naive UI + Vite |
| 学生产出 | Spring Boot 3.2（Java 17）+ Vue 3 + Element Plus（`zh-cn`）+ MySQL |

## 环境要求

- Python 3.11+
- Node.js 18+
- JDK 17、Maven（学生项目构建 / 运营端预览）
- MySQL 8（学生库必用；工厂元库可选 SQLite）

## 快速启动

### 1. 可选：启动 MySQL

```bash
docker compose up -d
```

提供：

- 工厂库用户 `gf` / `gf123456`，库名 `graduate_factory`
- root `root123`（默认给学生项目用）

### 2. 运营后端（`:8000`）

```bash
cd backend
copy .env.example .env
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

也可用 `scripts\start-backend.bat`（需已建好 `.venv`）。

说明：

- 不配 `GF_DATABASE_URL` 时，代码默认使用 `data/factory.db`（SQLite）
- 复制 `.env.example` 后默认指向 MySQL；若暂不用 Docker，请改回 SQLite 或先 `docker compose up -d`
- DeepSeek Key 仅环境变量：`DEEPSEEK_API_KEY`（可写 `.env`，界面只读掩码；无 Key 也可 bake，业务岛走确定性填充）
- 可选 Gemini：`GEMINI_API_KEY`；与 DeepSeek 可分别启用或双开（优先一家，失败自动换另一家）
- 默认仅开 DeepSeek（`LLM_PROVIDER` / 运营台开关）
- 上传匹配：阶段「匹配推荐」用系统已配大模型推荐骨架×领域（失败回落关键词）；仍可解锁手改
- 健康检查：`GET http://127.0.0.1:8000/api/health`
- 工厂 API 文档（调试用，非学生端）：http://127.0.0.1:8000/docs · http://127.0.0.1:8000/redoc

### 3. 运营前端（`:5173`）

```bash
cd frontend
npm install
npm run dev
```

浏览器打开 http://127.0.0.1:5173（`/api` 代理到后端 `:8000`）。

也可用 `scripts\start-frontend.bat`。

## 产品流程

1. **上传材料**（开题 / 任务书 / 功能清单等，PDF / Word / TXT，可多选）→ 自动建项并推荐骨架 × 领域  
2. **匹配确认**（默认可锁定推荐；解锁后可改选）  
3. **生成 Job**（六步）  
   - `parse_merge`：解析 / 合并 Spec  
   - `copy_bake`：复制 `skeletons/baseline` + 领域 SQL / schema  
   - `island_fill`：白名单业务岛（有 Key 可走 LLM，否则确定性）  
   - `build_verify`：构建校验，可选 Fix Agent  
   - `gate_e2e`：门禁；不过则不打包  
   - `pack`：打 ZIP（排除 `node_modules` / `target` 等）  
4. **运营端预览**：在端口池内起停学生前后端（后端 `9100–9120`，前端 `9200–9220`）  
5. **下载 ZIP**：仅 `zip_ready` 且门禁整体通过时开放  

运营端页面：项目、任务队列、帮助文档、大模型、Unsplash、运行环境。运营端本身无登录鉴权。

## 能力与领域

薄领域 = catalog + schema + SQL + 皮肤；共用能力运行时（档案 / 单据流 / 占用 / 到期 / 公告 / 组织用户 / 轻量推荐）。组 A～G + GENERIC 兜底均可 bake；Path B 三条真交叉可 full（详见 [`HANDOFF.md`](./HANDOFF.md)）。

| 组 | 已可 bake（示例） |
|---|---|
| A 借用/跟进 | 图书、设备、物资领用、CRM、事件上报、请假、资助奖学金、实验室准入、招聘、成绩、实习、快递驿站 |
| B 报修 | 宿舍 / 物业 / IT 工单 |
| C 报名 | 活动报名、失物招领（含宠物领养换皮）、选课 |
| D 交易 | 商城/二手、食堂点餐 |
| E 预约 | 挂号（含宠物医院、HPV/疫苗）、车位、会议室/座位占座、美发/健身私教、客房 |
| F 兜底 | `DOM-GENERIC`（按 ARCH 绑壳；盖不住则降通用，不误落 LIBRARY） |
| G 内容 | 影视、音乐、论坛、博客 |
| H 交叉 | 借用+下单 / 借用+预约 / 下单+预约（白名单内 `accept=full`） |

接题边界：专科/本科·课设演示级；硕博 / 真实全流程 / 未就绪交叉 → reject。

硬约束：库表数量 **6–15**；任意领域须具备总管主数据 CRUD、用户管理、公告；子管仅业务流。

刻意不接：人脸、协同过滤、物联网、真支付、小程序/原生 App、大数据作业等。

## 样例开题

`data/samples/`：

| 路径 | 用途 |
|---|---|
| `*.txt`（根下） | 单题快速试传（借阅、报修、交叉等） |
| `域开题样例近五年/` | 按 `DOM-*` 编号的近五年风格开题（含 FUND / LABSAFE / 座位 / 健身 / HPV / 领养等） |
| `开题报告/` | 偏长文开题报告样例（含跨场景文案，匹配以全文为准） |
| `upload_cluster_demo/` | 多材料分堆演示 |

宿舍类 bake 后样板账号（其它领域同类约定）：

| 角色 | 账号 | 密码 |
|---|---|---|
| 总管 | `admin` | `admin123` |
| 子管 | `subadmin` | `sub123` |
| 学生 | `student` | `student123` |

## 主要配置

| 变量 | 说明 |
|---|---|
| `GF_DATABASE_URL` | 工厂元库；默认 SQLite，示例见 `.env.example` |
| `GF_DATA_DIR` / `GF_SKELETONS_DIR` | 数据目录 / 骨架目录 |
| `DEEPSEEK_API_KEY` / `DEEPSEEK_BASE_URL` / `DEEPSEEK_MODEL` | DeepSeek LLM；Key 不入库 |
| `GEMINI_API_KEY` / `GEMINI_BASE_URL` / `GEMINI_MODEL` | 可选 Gemini（OpenAI 兼容）；与 DeepSeek 并存 |
| `LLM_PROVIDER` | 初始偏好（迁移用）；日常在运营台用双开关控制 |
| `GF_*_PORT_START/END` | 学生预览端口池（限制**同时运行**数，不限制选题库存；停预览后还池） |
| `GF_HOST` / `GF_PORT` | 工厂 API 监听（服务器用 `0.0.0.0`） |
| `GF_PUBLIC_HOST` | 预览/复制地址用的对外 IP 或域名；非本机时学生进程自动绑 `0.0.0.0` |
| `GF_BIND_HOST` | 可选；强制学生前后端监听地址 |
| `GF_STUDENT_MYSQL_*` | 学生库连接（默认 `root` / `root123` @ `3306`） |
| `UNSPLASH_ACCESS_KEY` | 可选；登录氛围图与门户轮播检索（Key 不入库，工作台可测连通） |

完整示例：`backend/.env.example`。

## 目录结构

```
backend/                 运营 API（bake / gates / llm / jobs）
  app/bake/              工厂核心
    domains.py           原型词桶 / 能力表；具名域目录见 domains_catalog/
    domains_catalog/     薄域条目（borrow / ticket / apply / trade / reserve / content / fallback）
    proposal_packs.py    选题包加载器；正文 proposal_packs_data/*.json
    engine*.py           bake 入口 + sql / bake / resources / islands 分册
    schema/              shells / builders_* / followup_presets / er_* …
    sql/templates/       具名域 DOM-*.sql；compose 拼 GENERIC
  app/llm/agents*.py     窄 Agent（match / island / labels / fix / qa / sample）
  app/api/system*.py     DeepSeek / Gemini / 用量 / 运行环境 / 样例开题
  tests/                 单测；helpers/；tools/
frontend/                运营端 UI
skeletons/baseline/      学生骨架（styles/themes/*.css 按域配色）
data/
  samples/               样例开题（见上）
  uploads/ · workspace/  上传落盘 · 每题工作区与 ZIP
scripts/                 Windows 启动 / 校验 bat
prototype/               运营端原型（见 prototype/README.md）
docker-compose.yml       仅 MySQL
HANDOFF.md               能力矩阵与领域覆盖（开发交接）
```

## 设计原则

- **工厂交付，不是通用 AI 写码**：可靠性来自固定运行时 + 模板，LLM 只填缺口  
- **开题材料为准**：壳文案与资料页身份跟场景走（`scene_scan`），禁止改开题迁就模板  
- **门禁即发货闸**：功能点清单 + 主路径未通过，ZIP 不放行  
- **薄领域优先**：新题优先加 schema / SQL / 皮肤，不新开厚代码包  

更细的能力矩阵与待办见 [`HANDOFF.md`](./HANDOFF.md)。
