# 技术栈交付契约（细则档案）

> 操作手册（短规则）见 `.cursor/rules/tech-stack-delivery.mdc`。本文保留完整口径，改栈/开开关时查阅。

## 与现网关系

- **现行唯一学生 ZIP**：Spring Boot + Vue 3 + Element Plus + MySQL + `JdbcTemplate`（`skeletons/baseline`）。
- 未单独开任务落地前，**禁止**为「组合轴 / 第二物理骨架」改 bake、门禁、匹配或现有骨架行为。
- 场景、身份、领域走 `scene_scan`；技术栈是另一轴。
- **已落地**：`persistence=mybatis`（PageHelper）、`persistence=jpa`、`addons.spring_security`。开题写明且能 bake → 跟开题。

## 硬原则

1. 开题技术方案为准（在可交付范围内）；能 bake 则实包 = README = 论文系统实现。禁止改开题迁就工厂。
2. 默认分离 ZIP（`frontend/` + `backend/` + `sql/`）；一次 bake 一条主线。
3. 同一 `spine=spa` 内 `jdbc` | `mybatis` | `jpa` 只换实现，不换业务能力与域语义。
4. 开题未写清 → 工厂默认：分离 + JdbcTemplate + 手写分页 + Element Plus。
5. SSR / 无 Vue（规划中）：另出物理骨架，不得与 Vue 包混搭；与 `ARCH-*`「骨架」不是同一概念。
6. 同题不同技术组合：领域能力、场景、主流程、演示数据、论文结构同质。

## 命名防撞

| 词 | 现网含义 | 技术栈 |
|----|----------|--------|
| 骨架 / archetype | `ARCH-*` 能力路径 | **禁止**用来表达 `spine` |
| 技术主线 / spine | （界面用语） | `spa` \| `ssr` |
| 基线 / baseline | `skeletons/baseline` | `spine=spa` 默认物理骨架 |

## Web 控件（匹配确认，非一键生成视觉区）

| 字段 | 选项 | 默认 |
|------|------|------|
| `spine` | `spa` \| `ssr` | `spa`（`ssr` 未落地前不出现） |
| `persistence` | `jdbc` \| `mybatis` \| `jpa` | `jdbc`（仅 spa） |

禁止「V/T 线」。拟选 ≠ 出包 → **双显**。

## 按需开关

- **ECharts**：基线常驻，无需开关。
- **Spring Security**：`addons.spring_security`；开题点名推荐开；开=真有 starter + SecurityConfig；关=不写 Security 技术名。
- 无生成路径不许开开关。

## 开题写了别的技术

| 情况 | 做法 |
|------|------|
| 已可 bake | 跟开题 |
| 规划内未落地 | 强提示；实包跟工厂默认；论文写实包 |
| 超出范围 | 标不支持；禁止静默 Boot+Vue 冒充 |

## 禁止

- `spine` 塞进 `ARCH-*`；未落地先挖 Store/门禁坑。
- 技术栈驱动 `scene_scan`；开题与实包不一致无双显。
- 按需开关打开后 ZIP/论文假装已集成。
