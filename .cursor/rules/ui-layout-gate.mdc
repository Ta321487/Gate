---
description: 起包前布局闸（改基线 UI 必对台账行；工厂须露红绿）
alwaysApply: true
---

# 起包前布局闸（主链路·基线 UI）

细则真源：[`docs/ui-layout-prebake-gate.md`](../../docs/ui-layout-prebake-gate.md)。  
管 **一眼病**（错位/挤破/叠穿/溢出等几何），不管控件选型（见 `form-controls`）、不管 68 域诊断勾选。

## DO

1. 改 `skeletons/baseline/frontend` 的 `views` / `layouts` / `components`（模板、CSS、工具条/按钮区）→ 收工前对照**台账绑定该文件的全部行**；改组件须含其 `hosts` 页。  
2. 至少跑受影响面：结构 `test_layout_contract`；视觉冒烟跑对应行或全表 `test_layout_smoke`（全表挂慢测）。  
3. 工厂反应：基线看运行环境「起包前布局闸」或 `GET /api/system/layout-gate`；**出包**看门禁 **`p3layout`**（对本包 frontend 对账+结构，红则禁 ZIP）。  
4. 新一眼病 → 先补册 §0.0a + 模式/断言，再消红；真阳性可记账，**禁止**只擦当前学生 ZIP。

## DON'T

- 闭眼改 UI、只靠字符串 pytest 绿就宣称布局已齐。  
- 只改 `components/`、不看宿主页画面。  
- 为消红改当面学生包 / 跳过 D1–D4 机器闸或出包 `p3layout`。  
- 以为「基线摘要绿」就等于「每题 ZIP 已过布局」——出包另有 `p3layout`。
