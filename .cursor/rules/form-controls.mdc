---
description: 
alwaysApply: true
---

# 表单控件（主链路·学生包）

档案字段已有映射：`skeletons/baseline/frontend/src/utils/archiveFieldWidget.js`（「禁止一律文本框」）和 `ArchiveFieldControl.vue`。手写的管理页、结算页、对话框必须同一套，不得另起文本框。

## DO

1. 先看字段语义再选控件，和 `archiveFieldWidget` 对齐。
2. 日期 → 日期选择器；日期时间 → 日期时间选择器；时刻（`HH:mm`）→ 时间选择器。
3. 数量、金额、倍率 → 数字框；是否启用 → 开关；有限选项 → 下拉或单选。
4. 管理端维护的名单，用户从接口选，不在页面写死选项。

## DON'T

- 日期、时刻、数字、枚举用 `el-input` 手填。
- 刻字、备注、原因这类自由文本改成选择器。
- 手写页面绕开已有控件映射。
