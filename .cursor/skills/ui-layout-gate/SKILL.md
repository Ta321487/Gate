---
name: ui-layout-gate
description: >-
  Runs or interprets the pre-bake UI layout gate (inventory, structure contract,
  visual smoke) when changing baseline Vue layouts/views/components, or when the
  user asks about 布局闸 / 一眼病 / layout-gate. Use before claiming layout OK.
---

# 起包前布局闸

真源：`docs/ui-layout-prebake-gate.md`。站队：**修工厂**；不为消红改学生页。

## 改了哪些文件 → 跑什么

| 改动 | 必跑 |
|------|------|
| `skeletons/baseline/frontend/src/views|layouts|components/**` | `cd backend; .\.venv\Scripts\python.exe -m pytest -q tests\test_layout_inventory.py tests\test_layout_contract.py` |
| 涉及几何/挤破/叠穿 | 再加 `tests\test_layout_smoke.py`（试点快；全表 `::test_full_table_coverage` 慢） |
| 只改工厂控制台摘要 | `layout_gate_status` / `GET /api/system/layout-gate` |

改 **组件** → 台账 `hosts` 上的页面一并视为受影响行。

## 工厂反应

- 基线：运行环境 →「起包前布局闸」；开工台「布局闸」一行；`GET /api/system/layout-gate`。  
- **出包**：门禁键 **`p3layout`**（对本包 `frontend/src` 对账+结构；红禁 ZIP）。全表 Playwright 不挡每次出包。

## 红灯

- 非预期 → 修共享闸/基线断言或记账到 `BASELINE_KNOWN_*`（须真阳性）。  
- 禁止只擦 `.runtime-tmp` 学生包过关。
