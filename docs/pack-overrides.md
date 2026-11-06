# 出包微调（Overrides）· 计划册

> **本文只负责**：论文材料 / 展示文案的 Human-in-the-loop 覆盖层——目标、红线、数据、按图手调范围、分期与验收。  
> **不写**：能力岛新功能、改开题迁就模板、扫盘替换 `.vue` 中文。  
> **站队**：修工厂共享钩子；单题补丁可进 DB + `islands`，重 bake **必须可重放**。  
> **状态（2026-11-04）**：UI §6 已定 · 对账已订 · **P0～P3 代码/文档已落地**（含 hide、序列/活动/用例描述、架构/用例图/测例/菜单/类图短签、invariants/审计一句）；双写收口口径：分文件仍由现网 PUT 写坐标/E-R，Overrides 统一镜像+apply；**工作区未 commit**。

相关：[`invariants.md`](./invariants.md)（八张材料真源）· [`delivery-audit-rules.md`](./delivery-audit-rules.md) · 已有零件 `modules.py` label patch · `er_labels.json` · `class_layout.json`。

---

## 0. 一句话

机器出图 / 出表之后，运营可在控制台做**最后细微手调**；**文字是一等公民**（短签、表内字段、菜单显示名、消息文案），位置/勾选是辅。**结构级大改仍建议重 bake**。重 bake 后 Overrides **原样叠回**，不得丢。

**P0 一票否决（已补）**：`bake_project` 整树删除前经 `islands_preserve` stash/restore 白名单（§4.4）；测见 `test_islands_preserve`。

---

## 1. 目标与非目标

### 目标

1. 控制台可调齐 **论文材料八张**（见 §3）上的**展示文字**（主）与显隐/勾选/坐标（辅）。
2. 微调只碰**展示层**，不碰 API / 表结构 / 路由 path。
3. 持久化：`project_overrides`（元库）+ 工作区 `islands/` 镜像；bake / 打开材料 / 出 ZIP 前均能 `apply`。
4. 重 bake 后：以**稳定业务键**匹配旧**文字**补丁；键仍在则生效，键消失进「失效补丁」，**不静默改契约**。

### 非目标（明确不做）

| 不做 | 原因 |
|------|------|
| 打包前全文替换 `.vue` / 任意文件中文 | 易改废、难幂等、撞学生可见文案门禁 |
| Overrides 里「强制关能力岛」代替匹配 | 须改匹配开关后 **重 bake**；pack 前撕菜单易空壳 |
| 在图上**新增**菜单外模块 / 用例 / 表 | 假论文；与「材料跟交付」冲突 |
| 改 API path、表名、Java 标识符 | 安全红线 |
| 用 Overrides 修工厂系统性短签 bug | 重复瑕疵回 `modules.py` / 词表；Overrides 是 1% 逃生舱 |

---

## 1.5 现网对账（已订 · 实现须遵守）

> 2026-11-04 对照仓库实码；与计划冲突时以本表为准，改本册再动刀。

| 项 | 现网事实 | Overrides 订法 |
|----|----------|----------------|
| **重 bake** | ~~无保留~~ → **已接** `stash_islands_whitelist` / `restore_islands_whitelist` | 维护白名单表与 `test_islands_preserve`；禁 stash `diagram_cache` |
| **模块短签钩子** | `islands/module_labels.json` + `apply_module_label_patch`；`build_module_model` 已叠补丁后再 `attach_module_label_gate` | **扩展此链**，禁止第二套 apply；LLM Agent 亦写同文件 → 落盘形状须兼容 |
| **补丁 JSON 形状** | 盘上为 `{"nodes":{"<id>":"短签"}}`（`sanitize_module_label_patch`） | DB payload 可用扁平 `module_labels`；**落盘/调用 apply 前适配成 `nodes`**（§4.2） |
| **模块 node id** | 菜单叶 `{side}:{menuKey}`（较稳）；身份叶 `identity:{i}:m{j}`（**索引，重 bake 易失效**） | 键消失 → 失效补丁，**禁止**按原文模糊贴到别的节点；UI 可提示身份叶不稳定 |
| **人工写接口** | E-R / 类图布局有 PUT；**模块短签无**控制台 PUT（现靠 LLM 写盘） | P0 新增薄 API → `save_module_label_patch`（或统一 overrides save 内调） |
| **图缓存** | `diagram_cache` 对 modules 指纹只有 `domain.schema.json`+`spec.json`，**不含** `module_labels.json` | 保存文字后必须 `invalidate(modules)` 或 `force`；指纹可后续把补丁文件列入（P9） |
| **闸 findings** | `kind` / `branch` / `label` / `detail`；材料卡「文案红」已接 | **仅增量** `source`、`override_key`；不另起红灯产品 |
| **序列勾选** | 仅请求参数 `ids=`，**无持久化** | 归 **P1**（本册原口径，对账确认） |
| **测例文字** | 已有 `testcase_labels.json` 同类补丁 | 归 **P2**，模式对齐模块图 |
| **`module_hide`** | 现网无图面隐藏 | **不进 P0 必交**；作 P0.5 / 与 P1 同批，免拖垮「改字+重放」 |

---

## 2. 原则

| # | 原则 |
|---|------|
| P1 | **大调整 → 重 bake**；细调 → Overrides。UI 文案写清。 |
| P2 | **重 bake 不变**：补丁按稳定键重放，不绑某次 SVG 字节。 |
| P3 | **白名单 schema**：未知键拒绝保存。 |
| P4 | **钩子应用，禁止扫盘**：只进 labels / menus 显示名 / 图 model / 布局 JSON。 |
| P5 | **闸统一、不放水**：手调后仍走**现有**出错通路（如模块图 `label_gate` → 材料卡「文案红」→ 禁导出）。**禁止**另起手调专用闸/专用红灯产品。findings 仅增 `source` 区分机器/手调，见 §6.6。 |
| P6 | **程序归工厂**：同款瑕疵多题出现 → 修生成，不堆单题补丁当主路径。 |
| P7 | **不抢现有拖位**：类图 / E-R 等已有「松手存坐标」入口继续当**唯一排版编辑器**；Overrides 只保证重 bake **不删**对应 `islands/*`，并可在微调 Tab **链过去**，禁止第二套坐标编辑器并行写同一文件。 |
| P8 | **文字优先于位置**：微调 Tab 默认首屏是「可改文案清单」；拖位只做入口链接。同一节点「改名」与「挪框」分开存、互不覆盖。 |
| P9 | **保存后出图必变**：文字保存并应用后，材料卡打开 / 预览 / 导出 PNG·SVG 共用叠补丁后的 model，禁止「表已改、图仍旧」。**实现=写盘后 invalidate 对应 kind**（照抄 `put_er_labels`），不得只改 JSON 指望缓存自失效。 |
| P10 | **挂现有钩子**：模块图走 `apply_module_label_patch`；E-R/类图走现有 save；测例走 `apply_testcase_label_patch`。Overrides 是编排+持久化+UI，不是平行渲染器。 |

---

## 2.0 文字层（核心 · 你要的重点）

Overrides **主战场是字**，不是框在哪。位置（§2.1）只保证不丢、不抢；**不能替代文字手调**。

### 三层文字，分清

| 层 | 改什么 | 进不进 Overrides | 怎么改 |
|----|--------|------------------|--------|
| **A. 论文材料字** | 模块图叶子、架构槽位名、类中文名、序列/活动消息与条件、用例名、用例描述表单元格、测例步骤/预期、E-R 实体/列中文 | **要 · 主路径** | 按稳定 id 覆盖 → 重渲 SVG / 重出表；重 bake 重放 |
| **B. 包内界面显示名** | 侧栏菜单 title、`schema.labels` 里学生看得见的短句 | **要 · 白名单键**（`menu_labels` / `schema_labels`） | bake 钩子合并进 menus / labels；**只改显示字符串**，不改 menu key / path |
| **C. 包内任意页面正文** | 随手改某个 `.vue` 里一行中文 | **不进** | 禁止扫盘替换；系统性问题改工厂词表 / `ticket_copy_text`；单题急救另议，不进本册 v1 |

你说的「很重要的地方就是文字」→ 默认指 **A + 必要的 B**。C 不做，以免改废包。

### 文字补丁长什么样

- 一律 `稳定键 → 新中文`（或表单元格 `rowId.field → 文案`）。  
- **不**存「把全局字符串 X 换成 Y」（易误伤）。  
- 保存后：对应图/表重算；模块图再跑 `label_gate`（过长/散文仍可「文案红」）。  
- 重 bake：键还在 → 新树上叠回你改的字；键没了 → 失效列表，字不会写到别的节点上。

### 和「拖位置」的关系（防误会）

| | 文字 | 位置 |
|--|------|------|
| 存哪 | `module_labels` / `*.labels` / `cell_overrides` / `er_labels`… | `class_layout.json` / `er_view`（`*_ref`） |
| 谁编辑 | **微调 Tab 主表** + 各图旁「改名」 | 现有类图/E-R 画布 |
| 会不会互相覆盖 | 改字 **不**改坐标 | 拖框 **不**改短签 |
| 分期 | **P0 起就做文字**（先模块图短签） | P0 只做「bake 保留文件」；UI 链现有入口 |

### 控制台怎么呈现（文字优先）

1. 微调 Tab 顶部：**按材料分组的文案表**（原词 → 输入框 → 保存）。  
2. 每组下方次要操作：打开类图拖位置、勾选序列张数；**隐藏叶子自 P0.5**。  
3. 「应用到材料 / 预览」先刷新**带新字的图/表**，再谈导出。

---

## 2.1 与现有「调位置」能力的关系（必读）

| 现有能力 | 真源文件 / API | Overrides 怎么处理 | 会不会抢 |
|----------|----------------|-------------------|----------|
| **系统类图拖拽** | `islands/class_layout.json`；松手存框、只重算折线 | payload 里 `class_layout_ref: true` =「承认并保留该文件」；**坐标仍只由现有类图弹窗写入** | **不抢**。微调 Tab 最多放「打开类图调整位置」按钮，不另做拖拽板 |
| **E-R 人工视图** | `er_view` / 相关 islands；指纹一致盖过自动排版 | `er_view_ref: true` 同上 | **不抢** |
| **E-R 中文名** | `islands/er_labels.json` | 可并入 payload `er_labels` 或双写同一文件；**保存 API 仍走现有 put er-labels**（或薄封装同一 `save`） | **不抢写路径**：一个文件一个写入函数 |
| **模块图** | 几乎无「拖框」；短签走 `module_labels.json`（LLM 已写；**无人工 PUT**） | Overrides **P0 补人工改短签**（挂现有 apply）；**图面隐藏延后**（§1.5）；不发明坐标拖拽 | 无冲突；与 Agent 补丁同文件，保存须 merge 非盲盖 |
| **序列/活动勾选** | 仅 query `ids=`，**未落盘** | P1 把 `selected_ids` **持久化进 payload**，重 bake / 重开仍在 | 是**补持久化**，不是换 UI；勾选控件可留在原 Viewer，保存时写入 overrides |

**硬约束（实现时钉测）**

1. bake / 清工作区 **白名单保留**（`islands_preserve`，见 §4.4）：`class_layout.json`、`er_view*`、`er_labels.json`、`module_labels.json`、`testcase_labels.json`、`overrides.json`。  
2. 禁止 Overrides apply 阶段 **重写** layout 坐标（除非人点了「复位布局」——复位仍调现有 `clear_class_layout_patch` 一类 API）。  
3. 微调 Tab **不得**再实现一套类图/E-R 画布；链接/深链到现有 modal 即可。  
4. 若将来把 layout 字节也塞进 DB：只能是 **与 islands 文件同步的镜像**，编辑仍只走现有保存接口，避免双写打架。  
5. 改字保存后：`invalidate` 对应 `diagram_cache` kind（modules 至少），保证 P9。

---

## 3. 八张材料 · 允许的手调面

> 「核心大调整」= 换域、加减能力、菜单结构、表结构 → 重 bake。  
> 「细微手调」= 下面各行。类图拖拽、序列/活动勾选等**已有**能力纳入同一 Overrides 叙事（统一入口 + 统一持久化），避免两套补丁。

| 材料卡 | 已有零件 | v1 细调 | v1.5+ | 重 bake 后保留方式 |
|--------|----------|---------|-------|-------------------|
| **功能模块图** | `apply_module_label_patch` / `islands/module_labels.json` | **P0**：按 node id **改短签**（必交）。**P0.5**：图面隐藏叶子（菜单仍在包内） | 图面同级排序 | 扁平键 ↔ 盘上 `nodes`；菜单叶 id 跟 `{side}:{key}`；身份叶索引 id 失效进 stale |
| **系统逻辑架构图** | `architecture.py` | 层/角色**显示名**覆盖 | 藏某一装饰箱 | 按 role key / 层 id |
| **系统类图** | `class_layout.json` 拖拽 | **坐标/折线**（已有）；类**中文显示名**覆盖（若有） | 隐藏某辅助类（仅图） | layout 按 class 稳定名；缺类则失效条目 |
| **系统序列图** | 候选勾选 + bake 文案 | **保留勾选 ids**；消息/角色**短签**覆盖 | 单条消息改写 | `sequence.selected_ids` + `sequence.labels` |
| **系统活动图** | 与序列可同勾选 | 同序列：勾选 + 菱形旁条件短签 | — | `activity.*` 同构 |
| **用例图** | 角色×菜单 | 用例/角色**显示名**；图面藏未讲用例 | StarUML 导出仍跟 model | `usecase.labels` / `usecase.hide` |
| **用例描述表** | 默认 4 主路径 | 改表内**字段文案**；换哪 4 条（在候选内勾选） | — | `usecase_desc.selected` + 单元格覆盖 |
| **软件测试用例** | 菜单推导 | 改步骤/预期**展示文案**；藏某行 | — | `testcases` 按 case id |

E-R 概念图（若仍挂在库表/材料区）：继续走现有 `er_labels` / `er_view`，**并入**同一 `payload` 的 `er_*` 段，避免第三套存储。

---

## 4. 数据设计

### 4.1 元库表

```text
project_overrides
  project_id    VARCHAR  PK  → projects.id
  version       INT          乐观锁，保存时 +1
  payload       JSON         见 §4.2
  updated_at    DATETIME
  updated_by    VARCHAR NULL  可选
```

### 4.2 payload（schema_version = 1）

```json
{
  "schema_version": 1,
  "module_labels": { "<nodeId>": "短签" },
  "module_hide": ["<nodeId>"],
  "architecture_labels": { "<slotId>": "显示名" },
  "class_labels": { "<className>": "显示名" },
  "class_layout_ref": true,
  "sequence": {
    "selected_ids": ["..."],
    "labels": { "<msgOrActorId>": "短签" }
  },
  "activity": {
    "selected_ids": ["..."],
    "labels": { "<nodeId>": "短签" }
  },
  "usecase": {
    "labels": { "<useCaseId>": "名" },
    "hide": ["<useCaseId>"]
  },
  "usecase_desc": {
    "selected_ids": ["..."],
    "cell_overrides": { "<rowId.field>": "文案" }
  },
  "testcases": {
    "hide": ["<caseId>"],
    "cell_overrides": { "<caseId.field>": "文案" }
  },
  "menu_labels": { "<menuKey>": "显示名" },
  "schema_labels": { "<labels.key>": "文案" },
  "er_labels": {},
  "er_view_ref": true
}
```

说明：

- `*_ref: true` 表示「布局/视图以工作区已有 `islands/class_layout.json` / `er_view` 为准」，重 bake **不得清空**这些文件（bake 契约：§4.4 白名单）。
- `module_labels`（DB 扁平）↔ 落盘 `module_labels.json` 的 `{"nodes":{...}}`：**apply / save 必须适配**；与 LLM 已写节点 **按 id merge**（手调覆盖同 id，不删其它 id）。
- `module_hide`：schema 可留空数组；**P0 校验器可收、UI 可不暴露**，直到 P0.5。
- `menu_labels` / `schema_labels`：只改**显示**；key / path / 列名不变（P2）。
- **禁止键**：`caps_force_off`、`file_replaces`、`sql_*`、`api_*`（校验器直接拒）。

### 4.3 工作区镜像

| 路径 | 用途 |
|------|------|
| `islands/overrides.json` | payload 全量镜像（bake 可读、可进备份） |
| `islands/module_labels.json` | 与现网 LLM/apply **同文件**；由 overrides 的 `module_labels` 适配写入 |
| 现有 `er_labels.json` / `class_layout.json` / `er_view*` / `testcase_labels.json` | **迁移期**双写或 `*_ref`；收口见 P3 |

### 4.4 重 bake 白名单（P0 第一刀 · 现网缺口）

实现：`app/bake/islands_preserve.py`；`bake_project` 在 `remove_tree` **之前** stash、copytree **之后** restore 下列相对路径（缺则跳过；目录 `er_view/` 整树）：

| 相对路径 | 备注 |
|----------|------|
| `islands/overrides.json` | Overrides 镜像 |
| `islands/module_labels.json` | 模块短签（手调 + Agent） |
| `islands/class_layout.json` | 类图坐标 |
| `islands/er_labels.json` | E-R 中文 |
| `islands/er_view/**` | E-R 人工视图 |
| `islands/testcase_labels.json` | 测例展示补丁（若已有） |

钉测最低线：

1. 写入假 `module_labels.json` + `class_layout.json` → bake 同 project → 两文件仍在且内容可识别。  
2. 读 DB overrides（若有）→ 写入 / 合并 `islands/overrides.json` → 再 `apply` 模块短签。  
3. 键不在新树 → 进 `_stale` / API 字段，控制台可清理；**不** 500、不改 SQL。  
4. **禁止** stash `diagram_cache/`（应随新 schema 作废；打开材料再预热）。

---

## 5. 应用层（流水线）

```text
bake 主路径
  → 【P0 第一刀】stash 白名单 islands（若 dest 已存在）
  → remove_tree + copytree 骨架 …
  → restore 白名单 islands
  → 生成 schema / menus / 工作区其余
  → sync_overrides_from_db → islands/overrides.json
  → apply: module_labels → module_labels.json（nodes 形）+ 现有 apply 链
  → （P2）apply: schema_labels, menu_labels
  → （预热图缓存时）model 已含补丁；勿用未 invalidate 的旧 cache
  → pre_zip_validate(overrides)   # 只校验，不扫盘改文件
  → pack ZIP
```

打开材料卡 / 「重新加载」：

- 保存手调后：**先 invalidate 该 kind**，再 `force` 或普通打开；与 `put_er_labels` 同口径。  
- 叠补丁发生在 `build_module_model`（已有），Overrides 只保证盘上 patch 正确。

**禁止**：`apply_overrides` 对工作区做「搜中文 → 替换」。

---

## 6. 控制台 UI（评审已定稿）

> 2026-11-04 评审通过后写入。文字一等公民；出错机制与现网统一。

### 6.1 入口

| 入口 | 行为 |
|------|------|
| ProjectDetail → **【微调】** Tab | 主战场：按材料分组的文案表 |
| 论文材料卡次要链「手调文字」 | 跳进微调 Tab 并锚到对应分组；**打开××图**等现有主按钮保留 |

页头常驻：

> 此处只改展示文字与材料勾选。结构大改请回匹配并重 bake；重 bake 后本页补丁会自动叠回。

### 6.2 总布局

```text
┌─ 微调 ──────────────────────────────────────────────┐
│ [页头说明]                                           │
│ 状态：已保存 vN · 上次应用 … · 失效补丁 K              │
│ [应用到材料并预览]  [仅保存]  [清理失效]                │
├─ 左侧锚点 ──┬─ 右侧内容 ─────────────────────────────┤
│ 功能模块图   │  ★ 文案表（主）                         │
│ 逻辑架构图   │  次：打开出图预览（hide→P0.5）            │
│ 系统类图     │                                         │
│ 序列图       │                                         │
│ 活动图       │                                         │
│ 用例图       │                                         │
│ 用例描述表   │                                         │
│ 测试用例     │                                         │
│ 菜单显示名   │  （P2）                                  │
│ 失效补丁     │                                         │
└─────────────┴─────────────────────────────────────────┘
```

- 左：材料锚点；右：**先文字表，后次要操作**。  
- **不做**整页大画布；出图仍进现有 Viewer modal。

### 6.3 单组右侧标准件（模块图样板）

| 列 | 含义 |
|----|------|
| 位置 / 原词 | 机器算出的路径与原文（只读）；旁注 node id（身份叶可标「索引键·易失效」） |
| 手调文案 | 输入框；空 = 跟机器 |
| 图上隐藏 | **P0.5 再露**；P0 表可不含此列 |

行操作：各材料表统一「还原」= 清空本行手调、跟机器原文（输入框亦 clearable）。  
次要：`打开模块图预览` → 现有 `ModuleDiagramViewer`（须已是新字）。  
v1 不提供第二套拖拽排序。

**按钮语义**

| 按钮 | 行为 |
|------|------|
| 仅保存 | 写 DB + islands（`nodes` 形 merge）；`invalidate(modules)`；不强制打开预览 |
| 应用到材料并预览 | 保存 + invalidate + `force` 重算 + 可选打开 Viewer |
| 清理失效 | 去掉重 bake 后键已不存在的补丁 |

脏离开 Tab 须确认。version 冲突 → 409，提示刷新。

### 6.4 各材料 UI 骨相

| 分组 | 主 UI（文字） | 次要 |
|------|---------------|------|
| 功能模块图 | 树路径 + 短签（隐藏→P0.5） | 打开模块图 |
| 逻辑架构图 | 槽位显示名 | 打开架构图 |
| 系统类图 | 类 → 中文显示名 | **打开类图调位置**（现有拖拽，不重做） |
| 序列 / 活动 | 消息/角色/条件短签 | 勾选哪几张 + 打开图 |
| 用例图 | 用例/角色显示名 + 隐藏 | 打开用例图 |
| 用例描述表 | 候选勾选 + 单元格文案 | 打开描述表 |
| 测试用例 | 步骤/预期单元格 + 藏行 | 打开测例 |
| 菜单显示名 | menuKey 只读 + title | 说明：不改 path |
| 失效补丁 | 键 / 原词 / 所属图 / 清除 | 重 bake 后自动出现 |

**不放进本 Tab**：关能力岛、改匹配域、全文替换、第二套类图/E-R 画布。

### 6.5 与出图的数据关系（保存后图必变）

```text
微调改字 ──保存/应用──► overrides
                      │
                      ▼ apply
               各图 model（带新字）
                      │
          ┌───────────┼───────────┐
          ▼           ▼           ▼
     微调「预览」  材料卡「打开」  导出 PNG/SVG
              （同一叠补丁结果）
```

### 6.6 出错机制（与现网统一 · 已定）

1. **同一套闸**：手调叠上后仍跑现有检查（模块图 = `label_gate` → 材料卡「文案红」→ 禁复制/下载 PNG·SVG）。**不放水，不另起手调专用红灯/专用闸框架。**  
2. **允许保存、禁止当可贴图导出**：补丁可留下；导出规则与现网文案红一致。  
3. **仅 findings 标来源**（机器 vs 手调），便于改输入框或「恢复机器名」，**不是**第二套产品状态机：

```json
{
  "kind": "too_long",
  "source": "override",
  "override_key": "module_labels.<nodeId>",
  "branch": "买家",
  "label": "……",
  "detail": "超过 8 字"
}
```

| `source` | 含义 | 列表展示（仍挂在现有 findings / 工厂提示下） |
|----------|------|-----------------------------------------------|
| `machine` | 生效字来自机器生成并撞闸 | 可标「机器」 |
| `override` | 生效字来自手调并撞闸 | 可标「手调」；行旁可「恢复机器名」 |

4. 工厂提示分句（同一 banner 结构）：机器红 → 修工厂清洗；手调红 → 改短签或恢复机器名；**禁止为消一手调红而放宽闸阈值**。  
5. 微调表与材料卡、Viewer **共用** `label_gate` / findings，禁止 Tab 内另算一套对错。

### 6.7 UI 分期可见范围

| 期 | 微调 Tab 可见 |
|----|----------------|
| **P0** | 模块图**文案表**（无 hide 列）+ 保存/应用/预览 + 失效骨架 + 类图「去调位置」链接；闸 findings 带 `source` |
| **P0.5** | 模块图「图上隐藏」列（可选，可与 P1 合并排期） |
| **P1** | 序列/活动/用例描述文字 + 勾选持久化；统一「失效补丁」体验收口 |
| **P2** | 架构/用例图/测例/菜单显示名 |

---

## 7. 分期（工时粗估 · 1 人）

| 期 | 交付 | 人天 |
|----|------|------|
| **P0** | ① **bake 白名单 stash/restore**（§4.4）钉测；② 表 + API + payload 校验；③ **模块图改字**（扁平↔`nodes` merge + 现有 apply）；④ invalidate modules；⑤ 微调主表 + 失效骨架；⑥ findings.`source`；⑦ 重 bake 重放测 | **6–8**（含①；砍 hide） |
| **P0.5** | `module_hide` 图面过滤 + UI 列 | 1–2 |
| **P1** | **序列/活动/用例描述文字** + 勾选持久化 | 3–4 |
| **P2** | 架构/用例图/测例/**菜单与 schema.labels** 文字钩子；各图 hide（若需要） | 3–5 |
| **P3** | 收口双写、文档对齐 invariants、控制台文案与交付审计一句 | 1–2 |

类图拖拽、E-R 标签：**P0 起靠 §4.4 保留 islands**，UI 可仍用现入口；E-R 改名继续走现 PUT，P2 再链进微调 Tab。

**P0 建议刀序（不可颠倒①② 与 UI）**

1. bake 白名单保留 + 测  
2. `project_overrides` + schema 校验（禁键）+ `overrides.json` 镜像  
3. apply：扁平 → `nodes` merge → `apply_module_label_patch`；保存后 invalidate  
4. 微调 Tab 模块图文案表 + findings `source`  
5. 端到端：改字 → 见图 → 重 bake → 字仍在  

---

## 8. 验收标准

1. 改模块图短签 → 保存 → 打开模块图见新名 → 导出 PNG 为新名（**未** `force` 手动清盘时也应因 invalidate 见新字）。  
2. **重 bake 同一项目** → 短签仍在；类图拖过的坐标仍在（§4.4 白名单未吞）；`diagram_cache` **不**被 stash 复活成旧图。  
3. 重 bake 后某 menu 删除（或身份叶索引漂移）→ 对应 override 进「失效」，不报 500、不改 SQL、**不**糊到其它节点。  
4. 保存含禁止键的 payload → 400。  
5. 模块图补丁导致闸红 → 与现网一致：材料卡「文案红」、不可导出；findings 含 `source=override`（或 machine），**无**第二套红灯。  
6. 保存并应用后：材料卡打开与导出均为新字（P9）。  
7. 回归：`test_schema_modules` 等材料测不因 hooks 假绿；新增 override 重放测 + **bake islands 保留测**。  
8. 与 LLM 已写的 `module_labels.json` 并存：手调同 id 覆盖，其它 id 保留。

---

## 9. 文档与规则同步（落地时）

| 动作 | 说明 |
|------|------|
| 本册状态 | **对账已订**（§1.5）；实现中改「活表」；[`docs/README.md`](./README.md) 已挂链接 |
| `invariants.md` | P0 合入后补一句：材料图手调走 Overrides，重 bake 白名单重放 |
| `HANDOFF.md` | 手册修订 / 开工 / 收口各刷一行 |
| Cursor rule（可选） | 短 rule：禁 vue 扫盘替换；禁 overrides 关岛；bake 须保留 islands 白名单 |

---

## 10. 决策记录

| 决策 | 结论 |
|------|------|
| 要不要扫 `.vue` 替换 | **否** |
| 关能力是否进 Overrides | **否**（匹配 + 重 bake） |
| 八张是否都要可手调 | **要**（分期；P0 先模块图文字） |
| 重 bake 后补丁 | **必须保留并重放**；今日缺口用 §4.4 补 |
| 存储 | **DB + islands 镜像**；模块短签落盘兼容现有 `nodes` 形 |
| 文字 vs 位置 | **文字一等公民**；拖位不抢、分存（§2.0 / §2.1 / P7–P8） |
| 保存后出图 | **必须变**（P9：invalidate，非指望指纹） |
| 手调撞闸 | **不放水**；走**现有**文案红/禁导出；findings 仅加 `source`（§6.6） |
| UI 定稿 | **2026-11-04 评审通过**写入 §6 |
| 现网对账 | **2026-11-04** 写入 §1.5；挂现有 apply，不平行渲染 |
| P0 是否含 hide | **否**（P0.5）；P0 必交 = 白名单 + 改字 + 重放 + source |
| 身份叶 id | 索引键，允许进失效；**禁止**按中文模糊重绑 |

---

## 11. 下一步（等人令）

- 说 **`提交并推送`**：建议按主题拆 commit（bake 白名单 / overrides 核心 / 控制台 Tab / 文档）。  
- 说 **`改范围`**：增减某张图的手调面后再改本册 §3 / §1.5。  
- 真机验收：控制台微调 Tab 改字 → 打开材料见新字 → 重 bake → 字仍在。
