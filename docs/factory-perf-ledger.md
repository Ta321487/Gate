# 工厂控制台性能账本

> **本文只负责**：单机工厂控制台（`backend/` + `frontend/`）卡顿条目的症状 / 落点 / 度量 / 勾销状态。  
> **不负责**：学生包性能、加机器当方案。  
> 交叉：[background-reconcile-cost.md](./background-reconcile-cost.md) · [preview-capacity-and-batch-ops.md](./preview-capacity-and-batch-ops.md)

---

## 定数

- 准：同机请求路径不重活叠轮询；度量可复跑。
- HANDOFF / parked 只指针，不另开平行性能台账。

---

## 账本（2026-11-27 本轮勾销）

| ID | 症状 | 落点 | 度量 | 状态 |
|----|------|------|------|------|
| P1 | 生成中 1.5s 轮询仍全量详情+扫盘 | `GET /api/projects/{id}/poll`；`api.getProjectPoll`；lite merge | poll 无 `spec`/`gates`/`checklist`/`delivery_review` 大载荷；不调 `build_review_payload` | **已修** |
| P2 | 启停冻住列表/轮询 | `runtime_action` → `asyncio.to_thread` | 源码无协程内裸 `time.sleep` / 裸 `rt.start_*` | **已修** |
| P3 | Jobs 3s 轮询 N+1 | `list_jobs` 一次 `Project.id/title` | 源码无逐条 `db.get(Project` | **已修** |
| P4 | 列表拖 `gates` 大 JSON | `list_projects` / `stats` `defer(Project.gates)`；未加载时信 `zip_ready` | 列表 options 含 `defer(Project.gates)` | **已修** |
| P5 | 终稿 overlaps 全表大列 | `find_overlaps` `load_only` + limit 200 | 不 hydrate `draft_schema_sql` | **已修** |
| P6 | 对账扫盘尖刺 | 默认间隔 8s、每轮扫描 1；未扫项目 zip_stale `compute=False` | `test_reconcile_scan_budget`；配置默认值 | **已修** |
| P7 | 图 viewer 无 debounce | `diagramFitDebounce.js` + 各 Viewer；`useDiagramFrameResize` RO debounce | Viewer 引用共享 util | **已修** |

---

## 复测口令

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest -q tests\test_factory_perf_ledger.py tests\test_reconcile_scan_budget.py
```

日志：`timing route=projects … select_ms`；生成中 Network 应打 `/projects/{id}/poll` 而非全量详情。
