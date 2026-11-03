# 校验闭环加固（语义幻觉 · FAQ · 匹配复核）

> **本文只负责**：机器防崩已封版后，**人防错域 + 机拦假宣称/错词 + 客服不瞎承诺**的落地裁定与开工清单。  
> **不负责**：温度分级细则（见 `backend/app/llm/temperature.py`）；布局/控件闸；交付审计小卡写法。  
> **状态**：**待开工**（人下令「开工」后再改代码）。  
> **索引**：[README.md](./README.md) · 搁置：[parked-work.md](./parked-work.md) 碎另案 **n**

---

## 0. 闭环目标（最终形态）

| 层 | 内容 | 状态 |
|----|------|------|
| 机器防崩 | LLM 温度分级 + unit_flow 校验/重试 + 确定性/静态 fallback | **已封版**（勿在本单重开温度/重试大改） |
| 机拦假宣称 / 错域词 | 扩 `_honesty_findings` + `domain_vocab`；**error 拦 ZIP** | 本单 ① |
| 客服不瞎承诺 | 未命中不调 LLM；**交付默认关润色**，只吐种子 | 本单 ② |
| 人防错域 | 低置信 / `DOM-GENERIC` **强制勾选**「已人工核域」（照抄 `path_ack`） | 本单 ③ |

**明确作废**：全包 `.vue`/种子「提取所有动词名词 ↔ Capabilities/状态机」的通用 NLP 穷举——误伤与维护成本不可接受。

---

## 1. 裁定摘要（老板已拍）

1. **穿帮检测** = 显式黑名单 / 假宣称搭配窗，**不是**开放式动词抽取。  
2. **FAQ** = 分层：未命中固定拒答；交付默认只吐种子；演示可另开润色。  
3. **匹配** = 不禁确认按钮；低置信或 GENERIC 必须多勾一项才能 `match_confirmed`。  
4. 三刀做完即本闭环收口；回归用**定向闸**，不默认整仓+浏览器全扫。

---

## 2. 开工钉死项（A～D · 动代码前必守）

### A. 假宣称必须本地可复现

- ZIP 红灯不能只靠 LLM QA 主审（漏报 = 假绿）。  
- 扩展后的 **`_honesty_findings` 本地规则**须能单独把 `p3q`（及约定并入的 `p3s` 语义项）打成 **`ok=False` → 禁 ZIP**。  
- LLM QA 只做加强，不当唯一保险丝。

### B. 「宣称」保留搭配窗 + 否定/划界

- 沿用 `_honesty_hard_boundary_hit`：**硬边界种子 ∩ 宣称搭配**，且无「非本期 / 不做 / 不支持」等划界。  
- 禁止改成「出现能力词即红」。

### C. 润色与 API Key 解耦

- 现状：有 `DEEPSEEK_API_KEY` 且命中 FAQ/业务摘录 → LLM 润色。  
- 目标：交付包 **默认不润色**（只吐种子原文）；演示/自测可开。  
- 须有**独立开关**（建议 `thesis.ai-reply-polish` 或等价 env），**禁止**靠拔 Key 关润色。  
- bake 进学生包默认 `false`；baseline + mybatis/jpa 三份 `AiAssistantStore` **同改**。

### D. 勾选卡在匹配确认，后端也验

- UI：置信度 `< 0.75` 或域为 `DOM-GENERIC` → 标红 + 必勾「已人工核域」（机制对齐 `needs_path_ack` / 「主路径已核对」）。  
- **不**禁用确认按钮；勾完仍可确认。  
- API：无该 ack 时拒绝写入 `match_confirmed`（只卡前端 = 未闭环）。  
- 阈值沿用现成 **0.75**，不另发明。

---

## 3. 落地清单（按序）

### ① 穿帮检测（约 3～7 人日）

| 子项 | 落点 | 验收 |
|------|------|------|
| 错域词 | `domain_vocab` / surface-lexicon **批 C** 口径；扫学生可见面 + 种子 | 跨域专属词 → **error**；反例必红、旧 canary 不误伤 |
| 假宣称 | `agents_qa._honesty_findings` 扩种子/扫描面（含 FAQ/公告等可见种子） | 未挂能力却「可退款/已对接…」类强宣称 → **error 拦 ZIP** |
| 门禁合并 | `p3q` / 约定的 `p3s` 子项；`zip_allowed` 同源 | 红则禁下载 ZIP；勿只 warning |

相关已有资产（先搜再改，禁止平行第二套）：

- `backend/app/llm/agents_qa.py` · `_honesty_findings`  
- `backend/app/bake/domain_vocab.py` · `lexicon_findings`  
- `backend/app/bake/gates/semantic.py` · `p3s`（当前偏演示口吻/场景资料）  
- `docs/surface-lexicon-design.md` · `docs/role-boundary-copy-batch.md`

### ② FAQ 强约束（约 0.5～2 人日）

| 子项 | 落点 | 验收 |
|------|------|------|
| 未命中 | 保持：无 FAQ 且无业务摘录 → `REPLY_NO_FAQ`，**不调** DeepSeek | 契约测钉死 |
| 交付默认 | 润色开关默认关 → 命中只返回种子 `content` | 有 Key 也不改写 |
| 演示可开 | 开关 true 时允许现有「依据摘录口语化」路径 | 与交付默认分测 |

真源：`skeletons/baseline/.../AiAssistantStore.java`（+ overlays 两份）。

### ③ 匹配人工复核（约 0.5～1.5 人日）

| 子项 | 落点 | 验收 |
|------|------|------|
| UI | `MatchTab.vue`：低置信 / GENERIC 风险标红 + 新勾选 | 不勾不能点「确认并继续」 |
| API | 匹配确认接口校验 ack | 裸 POST 无法 `match_confirmed` |
| 生成链 | 仍依赖已有 `match_confirmed` 才能生成 | 不新开第二道「禁生成」旁路 |

参考现成：`needs_path_ack` / `ackMainPath` / `preBakeRisks`（`< 0.75` 已提示但未强制勾选）。

---

## 4. 收工回归（定向 · 默认）

口令「开工」后做完，**默认只跑**（够证明闭环）：

1. `test_qa_factory_drift`（及本单新增 honesty 反例）  
2. `test_surface_lexicon` / `domain_vocab` 相关  
3. 匹配确认 ack 前后端测  
4. AI 助手契约：未命中不调 LLM；默认不润色  
5. 少量 canary：含 `DOM-GENERIC`、低置信确认路径；至少一单假宣称/错域词反例 bake 或夹具红

**不默认**：整仓 pytest、布局全表 smoke、Playwright 扫学生包。需要时另下一句。

---

## 5. 非目标（本单禁止）

- 全包动词/名词自由抽取对 Capabilities。  
- 「状态机节点」全文对齐动词（无统一机读总表前不做）。  
- 低置信直接禁用确认/生成。  
- 只擦当前学生包消红。  
- 为关润色拔掉学生包 API Key。  
- 重开温度档或 unit_flow 重试次数大改（防崩已封版）。

---

## 6. 口令

| 口令 | 含义 |
|------|------|
| `开工` | 按本册 §2 A～D + §3 ①→②→③ 改工厂；跑 §4 定向回归 |
| `全做` | 同上；仍不自动开整仓/浏览器，除非本条同时点名 |
| `别拆只答` | 只解释本册，不动代码 |

---

## 7. 修订

| 日期 | 说明 |
|------|------|
| 2026-11-04 | 初稿：老板接受「加固不新开战场」；作废 NLP 动词穷举；钉 A～D；待「开工」 |
