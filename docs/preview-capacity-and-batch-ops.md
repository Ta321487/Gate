# 预览进程容量与批量启停（实测 + 分期方案）

> **轮次**：2026-09-29（**只测不改**：本文不含任何代码改动；结论来自本机实测进程/DB 取证 + 行号级代码核对）  
> **口径**：一个「预览」= 项目列表/详情点开的运行态（Spring 后端 + Vite 前端）。容量按**提交内存 PrivateMemorySize（下称 Priv）**计，不按工作集（WS）：本机已在换页，WS 被系统裁剪到 5–60 MB，会严重低估真实占用。  
> **范围**：`backend/app/api/projects.py`、`backend/app/services/runtime.py`、`backend/app/services/projects.py`、`backend/app/api/system_info.py`、`backend/app/core/config.py`、`frontend/src/views/Projects.vue`、`frontend/src/api.js`、`skeletons/baseline/frontend/vite.config.js`、`skeletons/overlays/persistence-mybatis/backend/pom.xml`。  
> **不算**：生成/烘焙任务并发（那是 `gf_fill_unit_concurrency`）、LLM 限流、端口池本身（仅在 §3.4 说明它不构成资源闸门）。

---

## 0. 结论（TL;DR）

| 问题 | 实测结论 |
|------|----------|
| 为什么「按顺序起 7 个」就卡死 | 单预览 **≈1.1 GB / 6 个进程**，7 个 ≈ **7.4 GB** 常驻；本机 15.7 GB 总内存、实测仅剩 3.4 GB 空闲，编辑器/浏览器/Defender/本地工具链已占约 6 GB → 必然重度换页 |
| 是机器太弱吗 | 不是主因。根因是 **没有并发闸门** + **每个预览白起一个 378 MB 的 Maven JVM** |
| 端口池 21 能防住吗 | 不能。端口池只限端口，**没有任何内存 / CPU / 进程数闸门**；实测当时跑着 7 个、池里还剩 14 个空位 |
| 顺序点击能规避吗 | 不能。进程是常驻累积的；且启动动作直接跑在事件循环里（§3.5），逐个点会让整个工厂 API 一起卡 |
| 建议先做什么 | **P0 一键关闭 + 修前端端口漂移**（零风险，且卡死时就是降温阀）→ **P1 并发闸门 + 多选启停** → **P2 JVM 参数收敛**（7 个预览拿回 2.5–3.5 GB） |

---

## 1. 实测现场

### 1.1 机器水位

| 指标 | 实测值 |
|------|--------|
| 物理内存 / 空闲 | **15.7 GB / 3.4 GB** |
| 逻辑核 | 12 |
| 提交上限 / 可用提交 | 31.5 GB / 5.8 GB |
| 换页证据 | `Memory Compression` 275 MB；各 JVM 工作集被裁到 5–60 MB 而 Priv 仍 230–380 MB |
| 工厂库（`projects` 表） | 13 行：**7 行 running**（backend 9101–9107）+ 6 行 idle（端口 0/0） |
| 实际监听 | 后端 **9101–9107** 全部 LISTENING；前端 **9201、9203–9207**（9202 的前端未在跑） |

### 1.2 进程角色盘点（按命令行归类）

| 角色 | 进程数 | 单个 Priv | 小计 | 命令行特征 |
|------|--------|-----------|------|------------|
| 应用 JVM（fork 出的 Spring Boot） | 7 | 232–283 MB | **≈1.86 GB** | `java -XX:TieredStopAtLevel=1 -cp @…\spring-boot-*.argfile com.campus.*Application --server.port=91xx` |
| **Maven 启动器 JVM** | 7 | **377–379 MB** | **≈2.65 GB** | `java -classpath "D:\apac…"`（只等子进程，纯白占） |
| Vite dev server | 6 | 296–308 MB | ≈1.79 GB | `node …\vite.js --host 127.0.0.1 --port 9200` |
| npm 壳（`cmd → npm → vite` 中间层） | 6 | 153–154 MB | ≈0.92 GB | `node …\npm\bin\npm-cli.js run dev` |
| esbuild 服务 | 6 | 34–38 MB | ≈0.22 GB | `data\cache\baseline-frontend\node_modules\@esbuild\win32-x64\esbuild.exe` |
| **合计（7 后端 + 6 前端）** | **32** | | **≈7.4 GB** | |

同机非预览占用（约 6 GB）：编辑器 7 进程 ≈3.6 GB、Defender 0.48 GB、Chrome ≈0.5 GB、Memory Compression 0.27 GB、MySQL 0.11 GB、本地 MCP/工具链 ≈1.6 GB。**两者相加已 ≈14 GB / 15.7 GB。**

### 1.3 结论式推导

单预览（前后端都起）≈ **1.1 GB / 6 个进程**；7 个 ≈ **8 GB**。在本机剩余 3.4 GB 的条件下，第 8 个预览开始必然重度换页 —— 与「起 7 个就卡死」的现象一致。

---

## 2. 单预览的 6 个进程从哪来

| 层 | 进程链 | 代码依据 |
|----|--------|----------|
| 后端 | `_popen(shell=True)` → `cmd.exe` → `mvn`（JVM#1，378 MB）→ **fork** 出应用 JVM（JVM#2，≈260 MB） | `runtime.py:197-213`（`shell=True`）、`runtime.py:475-485`（`mvn -q spring-boot:run`）、`pom.xml:76-79` 的插件**无 `<configuration>`** → `fork` 取默认 `true` |
| 前端 | `cmd.exe /c _start_fe.cmd` → `call npm run dev`（npm 壳 153 MB）→ `node vite.js`（298 MB）→ `esbuild.exe`（36 MB） | `runtime.py:555-574`（Windows 走 `_start_fe.cmd` + `call npm run dev`） |

---

## 3. 五条结构性根因

1. **每个预览起 2 个 JVM**：`skeletons/overlays/persistence-mybatis/backend/pom.xml:76-79` 的 `spring-boot-maven-plugin` **没有 `<configuration>`**，`fork` 取默认 `true` → Maven 自己那个 JVM（**378 MB × 7 = 2.65 GB**）只负责等子进程，纯浪费。
2. **没有堆上限**：`runtime.py:470-485` 只传 `-Dspring-boot.run.arguments`，**没有任何 `-Xmx`** → 每个 JVM 默认最大堆 = 物理内存/4 ≈ **3.9 GB**，多开时互相膨胀且无保护线。
3. **前端一条链 4 个进程**：`cmd → npm 壳（153 MB）→ vite（298 MB）→ esbuild（36 MB）`，其中 npm 壳完全可以省掉。
4. **端口池不是资源闸门**：`core/config.py:50-53` 只限端口（各 21 个）。全局**没有任何预览并发上限**（对照：LLM 有 `gf_fill_unit_concurrency=3`）。实测当时跑 7 个、池里还剩 14 个空位 → 界面不会阻止继续点。
5. **启动阻塞事件循环**：`projects.py:1554-1628` 的 `runtime_action` 是 `async def` 里**直接跑阻塞同步代码**（未 `to_thread`）；`start_frontend` 内部的 `prepare_frontend_deps` + `_clear_vite_cache`（`runtime.py:553-554`）是分钟级 CPU/磁盘阻塞，`mvn spring-boot:run` 首次要编译。⇒ 点第 2 个时第 1 个还占着事件循环，**整个工厂 API（列表/日志/轮询）一起卡**；`time.sleep(0.6)`（`projects.py:1617-1618`）也在循环里。

**关键判断**：顺序点击 ≠ 不并发。进程一旦起来就常驻，最后仍同时有 7 套在跑，内存恒定 ≈8 GB。

---

## 4. 既有缺陷 A：前端端口记录漂移（会影响「关闭」的正确性）

### 4.1 实证

| 项目 id | `backend_port` | `frontend_port` | 实际监听端口 |
|---------|----------------|-----------------|--------------|
| gf-…224459 | 9101 | **9200** | 9201 |
| gf-…224507 | 9102 | **9200** | （前端未跑） |
| gf-…224515 | 9103 | **9200** | 9203 |
| gf-…224523 | 9104 | **9200** | 9204 |
| gf-…224531 | 9105 | **9200** | 9205 |
| gf-…224540 | 9106 | **9200** | 9206 |
| gf-…224549 | 9107 | **9200** | 9207 |

**7 行的 `frontend_port` 全是 9200**，而真实 Vite 在 9201–9207；后端端口则是正常递增的 9101–9107。

### 4.2 机制

- 学生模板 `skeletons/baseline/frontend/vite.config.js:13-15` 只写 `port: 5173`，**没有 `strictPort: true`** → Vite 发现端口被占会**静默 +1**，于是「DB 记 9200、进程实际在 9201」。
- 工厂进程表 `STORE`（`runtime.py:40`）是**内存态**，uvicorn reload / 重启即丢。此时：
  - `side_active(id, 9200, "frontend")`（`runtime.py:749-764`）= `9200 ∉ listening` → 判「未运行」；
  - `reclaim_idle_ports`（`services/projects.py:379-398`）随之把该行端口清零；
  - 而 9201 上的 Vite **仍在跑**，`_kill_port(9200)`（`runtime.py:165-177`）打空 → 再也没人按记录端口杀得掉它。

### 4.3 影响面

| 场景 | 后果 |
|------|------|
| 工厂未重启（STORE 有句柄） | `stop_frontend` 靠 `_kill(handle)`（`taskkill /PID /T /F`，`runtime.py:65-84`）侥幸能杀掉真进程 |
| 工厂重启过 | 列表把在跑的预览显示成「未运行」，Vite 与 npm 壳泄漏累积，占内存/CPU |
| 一键关闭若只信 DB 端口 | 漏杀（漂移）+ **误杀风险**（`_kill_port` 是按端口 `taskkill /T /F`，9200 若被别的进程占用就会被连根杀掉） |

> 标注：§4.1、§4.2 前半（模板无 `strictPort`、DB 与监听不一致）为**实测**；「工厂重启 → 泄漏」为基于代码路径的**推断**，未做实验复现（见 §9）。

---

## 5. 既有缺陷 B：孤儿进程残留（npm 壳 / 无法按端口回收的 Vite）

- 前端启动链是 `cmd.exe /c _start_fe.cmd` → `call npm run dev`（`runtime.py:555-574`）。正常停止走 `_kill(handle)` 的 `taskkill /PID /T /F`，能连树带走；**但只要有一次没走句柄路径**（工厂重启后 `STORE` 丢空），`153–154 MB` 的 npm 壳与漂移端口上的 Vite 就会永久留下。
- 实测存在 **6 个 153–154 MB 的 `npm-cli.js` 壳**，数量与在跑的 6 个 Vite 一一对应；另可见若干 `_npx`/临时脚本残留（非预览，属本地工具链，不在此文档责任范围）。
- `_kill_port` 每次调用 `_pids_on_port(port)` → `_listening_ports_win()` = **再跑一次完整 netstat**（`runtime.py:87-114`、`144-177`）；批量停止时若逐侧按端口杀，会产生大量 netstat 调用（可复用一次探测结果避免）。

**要点**：真正可靠的「关」需要**双证据**——`STORE` 句柄（有则 `taskkill /T`）+ **现探真实监听端口**（`listening_tcp_ports()` 一次净探复用），而不是只信 DB 里的 `frontend_port`。

---

## 6. 并发闸门与内存预算

### 6.1 内存账：改造前 / 后（按 7 个预览估算）

| 方案 | 估算常驻 | 说明 |
|------|----------|------|
| 现状（2 JVM + npm 壳 + Vite + esbuild） | **≈7.4–8.0 GB** | 实测 |
| `MAVEN_OPTS=-Xmx192m`（Maven 启动器 378→≈130 MB × 7） | ≈5.7 GB | 一行环境变量，收益 2.6 GB |
| 再加 `-Dspring-boot.run.jvmArguments="-Xmx320m -XX:MaxMetaspaceSize=192m -XX:TieredStopAtLevel=1"`（应用 ≈260→≈200 MB × 7） | ≈5.2 GB | **必须保留 `-XX:TieredStopAtLevel=1`**，否则启动变慢（该参数当前由插件默认注入） |
| 前端去掉 npm 壳那一层 + **并发闸门限 3–4** | **≈3.5–4.5 GB** | 15.7 GB 机器上的安全水位 |

### 6.2 四道闸门（缺一就会出现「一键启动 = 一键卡死」）

| 闸门 | 内容 | 落点 |
|------|------|------|
| 并发上限 | `GF_PREVIEW_MAX_RUNNING`（建议默认 3）；批量启动只启动到额度，其余返回 `deferred: 并发额度已满`，**不硬起** | `core/config.py`（对照 `gf_fill_unit_concurrency`） |
| 启动前预检 | 读可用内存 + 当前真实运行数 → 提示「空闲 3.4 GB，建议最多再起 2 个」 | 新批量端点 / 前端确认框 |
| 串行错峰 | 相邻启动间隔 3–5 s（`mvn spring-boot:run` 首次编译；7 个同时编译会在 12 核上打满 CPU + 磁盘） | 批量端点执行循环内 |
| 阻塞隔离 | 整批 `asyncio.to_thread`；`listening_tcp_ports()` 一次净探供整批复用 | `services/runtime.py` / `services/projects.py` |

> 顺带修（P0 一并做掉）：学生模板 `vite.config.js` 加 `strictPort: true`，或在启动前按真实空闲端口重分配，否则「多选启动」会立刻踩 §4 的同一个坑。

---

## 7. 分期方案

> **共同事实（本次复核过的实测锚点，各期都依赖它）**
>
> - **单项目启停已存在**：`projectDetail/RuntimeTab.vue:6-33`（全部启动 / 全部关闭 / 全部重启 / 打开预览）→ `useProjectDetail.js:2460 rtAction(side, action)` → `api.js:158 runtimeAction(id, side, action)` → 后端 `projects.py:1554 runtime_action(side, action)`。该端点**已支持 `side=all`**（`projects.py:1575-1590`），但**只作用于单个项目**，且每次请求自成一个事务（`sync_project_runtime` + `commit`，`projects.py:1619-1620`）。
> - **列表页 `Projects.vue` 当前没有任何启停控件**：271 行是「刷新」按钮，274-286 行是筛选行。因此下文 P0/P1 提到的列表页按钮属于**新增**，不是改造现有控件；「关闭全部运行中」在列表页目前**没有等价入口**。
> - **最近的批量先例**：「释放僵尸端口」`system_info.py:180-235` —— `asyncio.to_thread(_run)` + **单次** `listening_tcp_ports()` 快照 + `ApiOk(message, data={"cleaned","still_active"})` 聚合 + 单次 `commit`。注意它**明确声明「本按钮不会停运行中的预览」**（`system_info.py:231`），所以本次要做到「一键关闭」正是在补这个缺口，而不是重复它。
> - **阻塞点（批量版必须处理）**：`runtime_action` 内部有 `time.sleep(0.6)`（`projects.py:1618`），`start_backend`/`start_frontend` 全程同步阻塞；批量端点必须在 `asyncio.to_thread` 里跑，否则事件循环冻结（§3 根因 5）。
> - **启动前两道闸门不可绕过**：`preview_start_block_reason`（`services/projects.py:185`，`projects.py:1566` 调用）与 `ensure_project_ports`（`services/projects.py:401`，`projects.py:1573` 调用）。

### 7.1 P0 —— 一键关闭 + 端口漂移修复（零风险，当天可验）

| 项 | 落点 |
|----|------|
| 批量关闭端点 | 新增 `POST /api/projects/runtime/batch`（`backend/app/api/projects.py`，紧邻 `runtime_action`）；返回体沿用 `ApiOk` 聚合先例（`system_info.py:216-235`） |
| 作用域 | `filter=active` 口径（`projects.py:135-141`）+ **真实占用探测**（`side_active`），不信库内标记 |
| 清理（双证据） | `STORE` 句柄 `taskkill /T` + 现探 `listening_tcp_ports()`；单次净探供整批复用 |
| 收敛 | 逐项 `sync_project_runtime(p, listening=…, probe_http=False)` + 单次 `commit`（`services/projects.py:421-470`） |
| 前端入口 | `Projects.vue:271`（panel-hd）或 `274-286`（筛选行）**新增**「关闭全部运行中」+ `confirm()`（列表页当前无启停控件，见 §7 共同事实）；完成后 `load({ listOnly: true })`（`Projects.vue:914`），随后由 5 s 后台对账收敛（`services/runtime_reconcile.py:46-73`），**不新增轮询** |
| 模板修复 | `skeletons/baseline/frontend/vite.config.js:13-15` 增加 `strictPort: true` |

**验收**：7 个预览全部关干净（`netstat` 无 91xx/92xx LISTENING；java/node 残留不高于基线）；空闲内存回升 ≥6 GB；关闭过程中 `GET /api/projects` 不超时。

### 7.2 P1 —— 并发闸门 + 多选启停（闸门先于按钮）

- `core/config.py` 新增 `GF_PREVIEW_MAX_RUNNING`（默认 3）；启动前预检可用内存；相邻启动错峰 3–5 s；整批 `asyncio.to_thread`。
- `Projects.vue`：`columns`（`771`）首项加 `{ type: 'selection' }`，配 `:checked-row-keys` / `@update:checked-row-keys`（naive-ui `^2.44.1`）。**注意**：行跳转只绑在「项目」列的 render（`Projects.vue:779-781`），表格没有 `:row-props`，因此复选框列**不会**误触跳转，**不需要** `stopPropagation`。
- `api.js`：新增批量方法，显式 `timeout: 600000`（先例 `api.js:60` uploadConfirm）。
- 跳过/失败明细用 `ApiOk.data.items` 渲染成一条可关闭的结果条，不引入新组件。
- 语义提醒：`start_backend`（`runtime.py:413`）与 `start_frontend`（`runtime.py:530`）都**先 stop 再起** → 对运行中的项目，「启动」= 重启，文案与确认框必须写清。批量启动同样要先过 `preview_start_block_reason`（`services/projects.py:185`）与 `ensure_project_ports`（`services/projects.py:401`）两道闸，并沿用 `rtAction` 的 `viewEpoch` 守卫 + 700 ms 轮询收敛（`useProjectDetail.js:2470-2495`），不要另造状态机。

### 7.3 P2 —— JVM 参数收敛（收益最大，可独立做）

- `runtime.py:475-485`：mvn cmd 增加 `-Dspring-boot.run.jvmArguments="-Xmx320m -XX:MaxMetaspaceSize=192m -XX:TieredStopAtLevel=1"`；`env` 增加 `MAVEN_OPTS=-Xmx192m`（启动器 JVM 无需大堆）。
- 可选：前端由 `npm run dev` 改为直接 `node …/vite.js`，去掉 153 MB 的 npm 壳（`runtime.py:555-574`）。
- 7 个预览预计从 ≈8 GB 降到 ≈5 GB（叠加闸门后可到 3.5–4.5 GB）。

---

## 8. 复测方法（只读，可原样执行）

```powershell
# 1) 内存水位
Get-CimInstance Win32_OperatingSystem | Select-Object @{n='TotalGB';e={[math]::Round($_.TotalVisibleMemorySize/1MB,1)}},@{n='FreeGB';e={[math]::Round($_.FreePhysicalMemory/1MB,1)}}

# 2) 预览端口是否还在监听
netstat -ano | Select-String ':91[0-2][0-9]|:92[0-2][0-9]'

# 3) 角色盘点（Priv = 真实提交内存）
Get-CimInstance Win32_Process | Where-Object { $_.Name -in @('java.exe','node.exe','esbuild.exe') } |
  ForEach-Object { $c = ($_.CommandLine -replace '\s+',' '); $pr = Get-Process -Id $_.ProcessId -ErrorAction SilentlyContinue
    '{0,6}MB :: {1}' -f [int]($pr.PrivateMemorySize64/1MB), $c.Substring(0,[Math]::Min(70,$c.Length)) } | Sort-Object

# 4) DB 端口记录 vs 实际监听（对账漂移）
& 'd:\graduate_factory_v3\backend\.venv\Scripts\python.exe' -c "import pymysql;c=pymysql.connect(host='127.0.0.1',user='root',password='1719406',database='graduate_factory');cur=c.cursor();cur.execute('select id,backend_port,frontend_port,backend_running,frontend_running,status from projects order by backend_port');print(chr(10).join(str(r) for r in cur.fetchall()))"
```

---

## 9. 未验证 / 待确认

1. **端口为何全部记成 9200**：`ensure_project_ports`（`services/projects.py:401-418`）与 `allocate_ports`（`runtime.py:731-746`）代码路径上看不出明显缺陷 → 需要一次可复现实验（工厂重启后逐个启动并记录分配结果）才能定位。
2. **「工厂重启 → Vite 泄漏」** 属代码路径推断，未实验复现（可 kill 工厂进程后观察 92xx 是否仍在监听）。
3. **npm 壳归因**：6 个 vs 6 个在跑前端数量吻合，但未逐 PID 追父进程树。
4. **并发编译尖峰**：7 个首次 `mvn spring-boot:run` 同时编译的 CPU/磁盘曲线未实测，仅由代码路径判定为阻塞。
5. 同机非预览 ≈6 GB 占用中，本地工具链（MCP/`_npx`）部分不在工厂责任范围，未细究。

---

## 10. 变更记录

| 日期 | 说明 |
|------|------|
| 2026-09-29 | 初版：**只测不改**。实测 7 预览 ≈7.4 GB / 32 进程（含每预览 2 个 JVM）；记录缺陷 A（前端端口记录漂移，7 行全 9200 vs 实际 9201–9207）与缺陷 B（npm 壳/孤儿残留）；给出 P0/P1/P2 分期与内存预算 |
| 2026-09-29 | v1.1：**复核并修正落点**——`start_backend`/`start_frontend` 行号 414/531 → 413/530；§7 新增「共同事实」块：单项目启停链路（`RuntimeTab.vue:6-33` → `rtAction`：`useProjectDetail.js:2460` → `api.js:158` → `projects.py:1554`，已支持 `side=all`）、**列表页当前无任何启停控件**、`free-ports`（`system_info.py:180-235`）声明不自停运行中预览、`time.sleep(0.6)`（`projects.py:1618`）阻塞点、启动两道闸门。结论与分期不变 |
