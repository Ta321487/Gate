---
name: form-controls-gate
description: >-
  Runs or interprets the student-pack interactive controls gate (ban allow-create
  / inventing options; filterable search OK; date/number handfill;
  ArchiveFieldControl loops; p3controls) when changing baseline Vue
  forms/filters/dialogs, or when the user asks about 控件闸 / form-controls /
  allow-create. Use before claiming controls OK.
---

# 可交互控件闸

真源：`docs/form-controls.md`。站队：**修工厂**；不为消红改学生页。

## 改了哪些文件 → 跑什么

| 改动 | 必跑 |
|------|------|
| `skeletons/baseline/frontend` 表单/筛选/对话框/`ArchiveFieldControl` / `archiveFieldWidget` | `cd backend; .\.venv\Scripts\python.exe -m pytest -q tests\test_form_controls_contract.py tests\test_form_controls_widget.py` |
| 出包闸 / 门禁键 | 再加 `tests\test_form_controls_workspace_gate.py` |
| 只改工厂控制台摘要 | `form_controls_gate_status` / `GET /api/system/form-controls-gate` |

## 工厂反应

- 基线：运行环境 →「可交互控件检查」；开工台「控件检查」一行；`GET /api/system/form-controls-gate`。  
- **出包**：门禁键 **`p3controls`**（对本包 `frontend/src` 跑 C1～C3；红禁 ZIP）。

## 红灯

- 非预期 → 修共享映射/契约或记账到 `BASELINE_KNOWN_CONTROLS`（须真阳性）。  
- 禁止只擦 `.runtime-tmp` 学生包过关。  
- 有限名单 `allow-create` → 去掉 creatable，**保留 filterable**；自由叙述 → 改文本框，禁止假下拉。  
- 「手填」= 造库外值，不是禁止在下拉里敲字筛选。
