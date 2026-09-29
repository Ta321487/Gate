# 后台对账成本（运行态 / checklist 投影）

> **本文只负责**：后台对账线程每轮花在哪、怎么把没变的项目跳过、额度怎么摊平突发、怎么复测。
> 预览内存/进程容量与批量启停闸门：[preview-capacity-and-batch-ops.md](./preview-capacity-and-batch-ops.md)  
> **实测口径**：2026-09-29 本机（Windows 12 核 + Defender 实时防护，5 个项目、每项目 370~750 文件）；
> 数值随负载浮动（并发跑测试 / Defender 扫描 / 预览编译时明显偏高），看量级不看小数。

---

## 1. 谁在跑、每轮做什么

`backend/app/services/runtime_reconcile.py::_reconcile_loop` 每 `GF_RUNTIME_RECONCILE_SEC`（默认 5 s）跑一轮：

1. 拿 `projects.reconcile_lock`，`select(Project)` 全表；
2. `release_read_transaction(db)` 先放掉读事务（否则随后的扫盘会占着读锁，与 `/projects`、`/stats` 互相 busy）；
3. 一次 `runtime.listening_tcp_ports()`（netstat 快照）；
4. `to_thread(projects.reconcile_list_items)` —— 逐项目三件事：
   | 步骤 | 做什么 | 限流 | 实测 |
   |------|--------|------|------|
   | `sync_checklist_for_list` | 重算 checklist / gates（`evaluate_domain_gates` 扫工作区） | `_CHECKLIST_LIST_TTL_SEC` = 20 s + **投影输入签名** | **111~179 ms / 项目** |
   | `sync_project_runtime(probe_http=False)` | 运行态收敛（进程表 + LISTENING） | 无（廉价） | ~0 ms（无端口时） |
   | `delivery_review.is_zip_stale_cached` | 「合卷后工程是否变更」投影预热 | `_ZIP_STALE_TTL_SEC` = 20 s | 50~80 ms（仅已合卷项目） |

列表 `/projects` 与 `/stats` 只读库 + 只读这些投影；**写路径**（启停、详情、下载、合卷、上传确认）仍当场核验。

---

## 2. 实测：一轮对账的时间去哪了

| 环节 | 实测（5 项目） |
|------|----------------|
| netstat 快照 | ~15 ms |
| gates/checklist 重算 | **111~179 ms / 项目**（原主项） |
| 工作区签名走查（size + mtime，不读文件内容） | **18~20 ms / 项目**（370~750 文件；瓶颈是目录枚举/Defender，不是算法） |
| 运行态收敛 | ~0 ms |
| 整轮（TTL 到期且都需重算） | **~450~615 ms** |
| 整轮（TTL 到期但工作区没动） | **~200 ms**（残留 = 签名走查 + netstat） |

结论：**保留签名后，稳态一轮的 gates 重算几乎归零**，剩下的 200 ms 主要是"确认没变"的走查成本 + 15 ms netstat。
预算按项目数线性：20 个项目全到期时一轮 ≈ 2.5~3 s（会在对账线程里与 bake / 预览抢磁盘与 CPU）。

---

## 3. 两个省法（`backend/app/services/projects.py`）

### 3.1 投影输入签名：没变就不重算

`_projection_input_signature(project, ws)` = 工作区签名 + 非文件输入：

- **工作区签名**（`workspace_signature`）：`os.scandir` 递归整棵树，取 `相对路径 | size | mtime_ns` 做 sha256；
  剪掉 `node_modules / target / .git / dist / .mvn / .venv / logs / coverage / __pycache__` 等产物目录（`_SIG_PRUNE_DIRS`）。
- **非文件输入**：`status`、`zip_path` + 其存在性、`spec`、复审态（`last_qa / last_verify`）。

TTL 到期后先算签名：与上次重算时记下的**相同就跳过** `evaluate_domain_gates`（`scanned=False`），只把 TTL 续上。
签名覆盖的是 gates 的**全部输入**（gates 只从 `backend/src`、`frontend/src` 与根级 spec/schema 读值，全树走查是其超集）。

### 3.2 每轮重算额度：把长突发摊到多轮

`reconcile_list_items(..., max_scans=None)`：不传就取 `GF_RECONCILE_SCAN_PER_PASS`（默认 2；`<=0` 不限）。

- 项目按 **`_checklist_list_at` 升序**（最久未扫优先）排序后再处理 → 额度小时不会总停在同一批项目上；
- 没排到的项目**不刷新 TTL**，下一轮仍是最久未扫 → 不会被额度饿死；
- `generating` 项目只走 O(1) 的 `_clear_stale_zip_ready`，**不吃额度**；
- 磁盘上没有工作区的项目同样只走 O(1) 路径，**也不吃额度**（`scanned` 只在真有工作区时为 True）。

---

## 4. 什么时候一定会重扫

| 触发 | 为什么 |
|------|--------|
| 工作区任何文件的 size 或 mtime_ns 变化（新增/删除/改内容/改时间戳） | 进工作区签名 |
| `spec`、复审态（QA/验圈）、`zip_path` 或其存在性变化 | 进非文件输入签名 |
| 进程重启后的首个 TTL 周期 | 签名缓存在进程内，冷启动要重建（受额度摊到 ⌈N/K⌉ 轮） |
| `status` 变化（含 `generating` ↔ `generated`） | 进签名；`generating` 走廉价分支 |

---

## 5. 旋钮

| 环境变量 | 默认 | 作用 |
|----------|------|------|
| `GF_RUNTIME_RECONCILE_SEC` | 5 | 后台对账间隔（秒）；`<=0` 关闭对账 |
| `GF_RECONCILE_SCAN_PER_PASS` | 2 | 每轮最多重算几个项目投影；`<=0` 不限（本文件 §3.2） |
| `GF_ORPHAN_PURGE_PER_PASS` | 1 | 每轮顺带清理几个孤儿工程目录；`<=0` 关闭；与「清理失效项目残留」全量受理互斥 |

投影 TTL 目前是代码常量：`_CHECKLIST_LIST_TTL_SEC`（`services/projects.py`）与 `_ZIP_STALE_TTL_SEC`（`services/delivery_review.py`），都是 20 s，与对账间隔同量级。

---

## 6. 已知边界（写代码前先读）

1. **签名只看 size + mtime**：若有人"改内容后把 mtime 改回原值且长度不变"，签名不变量 → 投影会漏一次重算。
   下载/详情等写路径仍走现场核验（`is_zip_stale`），不会把过期包放行。
2. **签名缓存是进程内的**：多 worker / 重启后各自重建，首个周期会有一次全量重算（受额度分摊）。
3. **不是"工作区变了就一定立刻反映"**：列表现状依赖 TTL（20 s）+ 额度，最坏延迟 = TTL + ⌈N/K⌉ × 对账间隔。
4. 额度只限**重算**（gates）；zip-stale 预热仍每 TTL 周期做一次，因为列表/统计读它（冷缓存按"未过期"处理）。

---

## 7. 复测方法（只读，可原样执行）

两个关键量都能绕开数据库单独复测：

```powershell
# 1) 签名走查成本（逐工作区；分母是工作区数）
& 'd:\graduate_factory_v3\backend\.venv\Scripts\python.exe' -c "import os,sys,time,pathlib; os.chdir(r'd:\graduate_factory_v3\backend'); sys.path.insert(0, os.getcwd()); from app.services import projects as svc; wss=[d for d in pathlib.Path(r'd:\graduate_factory_v3\data\workspace').iterdir() if d.is_dir()]; t=time.perf_counter(); [svc.workspace_signature(w) for w in wss]; print('signature ms/ws', round((time.perf_counter()-t)*1000/max(1,len(wss)),2))"

# 2) gates 重算成本（同一批工作区，先取第一个）
& 'd:\graduate_factory_v3\backend\.venv\Scripts\python.exe' -c "import os,sys,time,pathlib; os.chdir(r'd:\graduate_factory_v3\backend'); sys.path.insert(0, os.getcwd()); from app.bake.gates import evaluate_domain_gates; ws=sorted(d for d in pathlib.Path(r'd:\graduate_factory_v3\data\workspace').iterdir() if d.is_dir())[-1]; t=time.perf_counter(); evaluate_domain_gates(ws, {}); print('gates ms', round((time.perf_counter()-t)*1000,1))"
```

**整轮**口径要连库（列表/统计同源），只读拆解时对同一批项目分别计时：`workspace_signature`（或 `_projection_input_signature`）、
`_sync_checklist_for_list`、`sync_project_runtime(probe_http=False)`、`is_zip_stale_cached`；netstat 用
`runtime.listening_tcp_ports()` 单独计。注意别在真库上 `commit`（对账会把投影写回库）。


---

## 8. 变更记录

| 日期 | 说明 |
|------|------|
| 2026-09-29 | 初版：记录「投影输入签名 + 每轮额度」两处改动与实测（gates 重算 111~179 ms/项目 → 未变时跳过；签名走查 18~20 ms/项目；整轮 615 ms → 稳态 ~200 ms）。签名实现用 `os.scandir` + `DirEntry.stat`（比逐个 `Path.stat()` 快约 20%），并逐工作区比对过条目集合与旧实现 0 差异 |
