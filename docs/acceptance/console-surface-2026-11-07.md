# 收卡片墙验收 · 2026-11-07

对照 [`console-product-surface.md`](../console-product-surface.md) §2（S1～S7）。  
证据截图（1280×800）：`surface-ops-home.png` · `surface-projects.png` · `surface-detail.png`  
机器钉：`test_console_surface_contract` 绿。

| # | 标准 | 结论 | 证据摘要 |
|---|------|------|----------|
| S1 | 一页一主区 | **过** | 开工台主区=`今日要处理`；项目主区=`项目列表`托盘；详情=`阶段内容`一块 |
| S2 | 能去框则去框 | **过** | 开工台无厚 panel；详情 Tab 用 `panel-quiet`；工作台无嵌套 panel 框 |
| S3 | 统计不抢主任务 | **过** | 开工台=`surface-strip`；项目=`stats` 条带筛选，不与列表同权拼盘 |
| S4 | 环境/配置沉底 | **过** | 开工台=`surface-env-line`；System 路径在「高级」折叠 |
| S5 | 列表像表 | **过** | Projects/Jobs 表在托盘；行内无抢色 primary |
| S6 | 详情壳干净 | **过** | 无同级「质检交付」h3；阶段轨 + 工作台；折叠「更多」保持 |
| S7 | 不打架多个 primary | **过** | 详情可见 primary 仅「下载 ZIP」一处 |

**总评**：**通过**（台面可宣称含观感产品完工）。

**已知余债（不挡验收）**

- 「更多」内答辩 PPT 仍用非 quiet `.panel`（折叠态不可见）。  
- §3.1 未改；未宣称无人值守发版（见 `release-checklist` 其余项）。
