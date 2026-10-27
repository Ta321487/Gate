---
description: 可交互控件闸（改基线表单/筛选必跑契约；工厂须露红绿）
alwaysApply: true
---

# 可交互控件（主链路·学生包）

细则真源：[`docs/form-controls.md`](../../docs/form-controls.md)（**全包可交互控件**，不限 el-form）。改口径先改该册；本规则只作摘要。

档案字段映射：`archiveFieldWidget.js` + `ArchiveFieldControl.vue`。  
**视图 / 组件 / 布局 / 对话框 / 筛选条 / 表格行内** 凡采集或改变业务状态、查询条件的控件，同一套语义纪律；无免检区。

## DO

1. 先看语义再选控件；能走 `archiveFieldWidget` 的走映射，手写区对齐同一语义表。
2. 日期 → 日期选择器；日期时间 → 日期时间选择器；时刻（`HH:mm`）→ 时间选择器。
3. 数量、金额、倍率 → 数字框；是否启用 → 开关；有限选项 → 下拉或单选。
4. 管理端维护的名单，各端从接口选，不在页面写死选项。
5. **下拉：可 filterable 筛选，禁 `allow-create` 造库外值**（表单/筛选/对话框/行内同一条）；选项来自学生可配数据（分类、lookup 等）。
6. 同一语义全包一致（如分类：编辑与筛选都不得一处下拉一处纯文本框）。
7. 改基线交互收工前跑 `test_form_controls_contract`（+ 动映射则 `test_form_controls_widget`）。
8. 工厂反应：基线看运行环境「可交互控件检查」或 `GET /api/system/form-controls-gate`；**出包**看门禁 **`p3controls`**（红则禁 ZIP）。

## DON'T

- 任意位置用 `el-input` 手填日期、时刻、数字、枚举。
- 任意位置的分类/类型下拉 `allow-create` / creatable，或写死业务选项表。
- 为「禁手填」误删 `filterable`（筛选输入 ≠ 创库外值）。
- 「档案合规、别处例外」。
- 刻字、备注、原因等自由文本改成无数据源选择器。
- 手写页面绕开已有控件映射。
- 为消红只擦当面学生包 / 跳过 `p3controls`。
- 以为「基线摘要绿」就等于「每题 ZIP 已过控件」——出包另有 `p3controls`。
