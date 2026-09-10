# 毕设港 · 交接

工作区：`d:\graduate_factory_v3`  
**禁止**参考 / 迁移 `d:\graduate_factory`、`d:\graduate_factory_v2`。

> **本文只负责**：新对话交接（主线、硬边界摘要、开场白）。  
> **产品总览 / 启动**：[README.md](./README.md) · **专题索引**：[docs/README.md](./docs/README.md)

---

## 当前主线

1. **能力运行时 + 薄域 A～G + GENERIC** 已可 bake；差的是按需冒烟与文案微调。  
2. **Path B** 三条真交叉可 `full`（借用+下单 / 借用+预约 / 下单+预约）；三合一与智慧校园仍 `reject`。  
3. LLM **只填 schema JSON**（不生成业务 Java/Vue）；接 LLM 后「代码无误」靠运行时固定。  
4. **Path B 口径**：开题写进「拟实现」的必须能答辩演示；做不到就拒收 / 改开题 / 先扩能力，禁止 `degraded` 交半成品装全文。

领域与交叉长表 → [`docs/domains.md`](./docs/domains.md)。  
能力 cap 矩阵 → [`docs/capabilities.md`](./docs/capabilities.md)。

---

## 接题边界（硬原则）

本产品定位：**专科 / 本科毕设、课设级别的 Web 管理系统生成**（演示级主路径），不是研究生平台，也不是真实业务交付。

| 接 | 不接 |
|----|------|
| **专科 / 本科** 毕设、**课设**（Web 管理、演示级） | **硕士研究生 / 博士研究生** 课题与开题 |
| 薄域单路径；白名单内且 `defense_ready` 的交叉 | **真实业务全流程** / 生产级全链路 / 企业级端到端 |
| L0～L2 积木内可演示的功能 | L3、HIS/ERP 级发散、未就绪交叉 |

信号：`OUT_OF_SCOPE_SIGNALS`（硕博学位论文、真实业务全流程等）→ `reject`。  
分层细则 → [`docs/difficulty-tiers.md`](./docs/difficulty-tiers.md)。

---

## 开题场景 / 身份文案（硬原则）

**开题与材料为准，工厂跟场景走；禁止改开题迁就模板。**

| 约定 | 含义 |
|------|------|
| **单一真源** | `app/bake/scene_scan.py` → `scene_for(domain, title, proposal)` |
| **同场景同口径** | 壳 eyebrow/roles 与 `profileFields`（注册/资料页）必须读同一 scene |
| **扫词选分支** | 不是逐字复述开题；场景定了不得再写死冲突身份（如企业 CRM ≠ 学号/教职工） |
| **业务角色优先** | 背景里的「学院/校园」不压过正文里的「销售/客户跟进」等企业档 |
| **未写清用域默认** | 默认档在 builder / `PROFILE_FIELDS_BY_DOMAIN`，不是臆造开题 |

须分支域清单见 `SCENE_BRANCH_DOMAINS`。改 hint 只动 `scene_scan`，并补场景测试。

---

## 读什么（专题）

| 要查 | 文档 |
|------|------|
| 能力 cap / 挂载口径 | [`docs/capabilities.md`](./docs/capabilities.md) |
| 领域组 A–H / Path B 交叉 | [`docs/domains.md`](./docs/domains.md) |
| L0–L3 / 加价边界 | [`docs/difficulty-tiers.md`](./docs/difficulty-tiers.md) |
| 库表预算 / 角色不变式 | [`docs/invariants.md`](./docs/invariants.md) |
| 怎么审交付 | [`docs/delivery-audit-rules.md`](./docs/delivery-audit-rules.md) |
| 换皮 ID 册 | [`docs/domain-skin-gap-analysis.md`](./docs/domain-skin-gap-analysis.md) |
| 开题功能对照 | [`docs/opening-feature-delivery-map.md`](./docs/opening-feature-delivery-map.md) |
| AI 开题对照 | [`docs/ai-opening-delivery-map.md`](./docs/ai-opening-delivery-map.md) |
| 全索引 | [`docs/README.md`](./docs/README.md) |

宿舍样板账号见 [README.md](./README.md)「样例开题」节。

---

## 新对话开场（当前主线）

```
继续 graduate_factory_v3。先读 HANDOFF.md；能力/领域长表见 docs/。
主线：Path B 三条交叉已可 full；薄域冒烟或 LLM 填 schema。
超壳 / 三合一 / 智慧校园必须 reject；硕博与真实业务全流程不接。
不要新开厚 DOM 包。领域清单以 docs/domains.md 为准。
```

## 新对话开场（某个薄领域）

```
继续 graduate_factory_v3。先读 HANDOFF.md。
目标：薄领域 DOM-___（关键词：___）冒烟或文案/SQL 微调。
能力组合：___（对照 docs/capabilities.md + docs/domains.md）；仅 catalog + schema + SQL 种子 + 皮肤。
禁止内存 Store、禁止排除 DataSource、LLM 只填 schema。
```
