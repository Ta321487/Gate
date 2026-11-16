# 论文图同源导出（Mermaid / Draw.io）

> **本文只负责**：论文阶段三档导出合同、正确性红线、分期与几何债延期口径。  
> **不负责**：厂内排版刀实现细节（见 parked **m** / 产品化 D1）；Overrides 手调 UI（见 [`pack-overrides.md`](./pack-overrides.md)）。  
> **索引**：[README.md](./README.md) · 搁置 [`parked-work.md`](./parked-work.md) **m** · 不变量 [`invariants.md`](./invariants.md)

---

## 0. 产品一句

工厂代替「理解项目 → 画参考图」。**结构正确性由工厂保证**（跟 ZIP / 叠 Overrides 后 model 一致，可机器复验）。论文阶段用 **Draw.io / Mermaid 导出**保手调交付；厂内错位/叠穿/交叉是**必须修的债，本期延期**，禁止用导出绿冒充 D1 已齐。

---

## 1. 三档导出（同一 model）

```text
交付包 (SQL / menus / Java)
  → diagram_pack.pack_*
  → Overrides 叠补丁
  → 统一 model
       ├─ render_*_svg     （A 快照）
       ├─ to_mermaid       （B 结构参考）
       └─ to_drawio        （C 手调主档）
```

| 档 | 格式 | 用途 |
|----|------|------|
| A | PNG / SVG | 几何可交时贴论文 |
| B | Mermaid `.mmd` | 老师路径：粘 [diagrams.net](https://app.diagrams.net/) 出参考 |
| C | Draw.io `.drawio` | **框可拖、线可改**；论文阶段几何翻车时的主兜底 |

表类材料（用例描述表、测例、物理设计表）不进本册图格式，继续 Markdown / Word。

用例图现有 StarUML `.mdj` 可与 `.drawio` 并存；全图手调主档统一 `.drawio`。

---

## 2. 正确性红线（硬保证）

| 保证 | 钉法 | 失败 |
|------|------|------|
| 结构 ⊆ 实包 | model 只从 menus / SQL / Java 推；禁止包外 id | 材料红，禁可交导出 |
| 三档 ≡ 同一 model | SVG / Mermaid / Draw.io 同快照；测试比对标签/hide/边 | 单测红 |
| rubric 可复现 | FK 剥离、张数、槽位、描述对菜单 = 确定性断言 | error → 禁导出 |
| LLM 只审不改 | 可选对账 findings；禁止写回 model / 导出正文 | 丢弃坏 LLM 条 |
| 几何另账 | 错位 ≠ 结构错；导出可交 ≠ 初开可读齐 | parked **m** 不关 |

实现入口：`backend/app/bake/schema/diagram_export.py`（合同/同源断言）、`diagram_drawio.py`（mxGraph）、`diagram_mermaid.py`。

**进度（2026-11-14）**：M0～M4 **已齐**（导出 + rubric 闸 + 手动 LLM/确定性对账）；序列/活动暂仅 Mermaid；几何债仍延期。

---

## 3. 覆盖与分期

| 材料 | Draw.io | Mermaid | 状态 |
|------|---------|---------|------|
| E-R 总图 / 实体属性图（无 FK） | 要（含多页 bundle `er-parts.drawio`） | 要 | **已齐** |
| 功能模块图 | 要 | 要 | **已齐** |
| 系统类图 | 要 | 要 | **已齐** |
| 用例图 | 要 | 要 | **已齐**（+ .mdj） |
| 序列 / 活动 | 可后 | 要（老师主路径） | Mermaid **已齐**；Draw.io 可后 |
| 逻辑架构图 | 要 | 要 | **已齐** |

| 刀 | 内容 | 状态 |
|----|------|------|
| **M0** | 合同文档 + 同源模块 + 夹具 | **已齐** |
| **M1** | Draw.io（E-R / 类 / 模块 / 用例）+ UI + 测试 | **已齐** |
| **M2** | Mermaid（序列/活动/类等）+ UI | **已齐** |
| **M3** | 其余图齐 + rubric 确定性闸 | **已齐**（架构导出 + rubric 闸） |
| **M4**（可选） | `agents_thesis_diagrams`：证据包对账，只审不改 | **已齐**（手动「论文图对账」；无 Key 仅确定性） |
| **延期** | D1 / parked **m** 厂内几何 | 仍开、不关单 |

---

## 4. 老师 rubric（确定性优先）

实现：[`backend/app/bake/schema/diagram_rubric.py`](../backend/app/bake/schema/diagram_rubric.py)；`pack_*` 出参挂 `rubric_gate`；导出走 `_ensure_diagram_export_ok`。

| 材料 | 钉什么（error 禁导出） |
|------|------------------------|
| 实体属性图 | `own_columns` 不得含 FK；中间表不出属性图；Draw.io **陈氏**（矩形实体 + 椭圆属性 + 连线），禁止单框换行列表 |
| E-R 总图 | 概念实体 ∈ tables；纯 M:N 中间表不得进清单 |
| 序列图 | 四槽位 actor/page/controller/db；消息端点 ∈ 参与者 |
| 活动图 | 泳道 user/system/db；有 start/end |
| 用例描述表 | 候选够时张数达标；Markdown 含「用例描述表」；事件流非空；有 menu_key（auth 等内置除外） |
| 类图 | 关系端点 ∈ classes |
| 用例图 / 架构 / 模块 | 有角色与一级用例 / 有角色 / 有 root（模块文案仍走 `label_gate`） |

规矩变更 → 改本册 + `diagram_rubric` 断言，禁止每单翻学习通。

---

## 5. 不做

- 每单开放式 LLM 聊天画图当真源。
- 与 `pack_*` / Overrides 脱钩的第二套图。
- 工厂 Key 进学生 ZIP。
- 宣称「有导出 = 厂内几何已齐」。

---

## 6. 验收

- 下载 `.drawio` 可在 diagrams.net 打开并拖框；节点/边与 model 对齐（有测）。
- Overrides 改短签/隐藏 → 三档同字同隐。
- 属性图导出不含 FK 列名；包外结构 → 红且禁导出（API 400 + 弹层禁用导出 + 材料卡「规则红」）。
- 收工不得关闭 parked **m**，不得宣称 D1 齐。
