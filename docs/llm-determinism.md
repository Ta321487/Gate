# 工厂 LLM：不确定 → 确定性（硬原则）

> 操作摘要见 `.cursor/rules/llm-determinism.mdc`。  
> 学生包 AI 挂件另册：[`ai-assistant-delivery.md`](./ai-assistant-delivery.md)（不走本原则的「审→闸」主轴）。

## 一句话

**工厂侧 LLM 最重要的事：把不确定变成确定性。**  
不是「多点几次模型碰运气」，也不是「永远靠 LLM 当场审」。

## 两类用法（同一原则，两套落地）

| 类 | 场景 | 正确形态 | 错误形态 |
|----|------|----------|----------|
| **审 / 门禁** | 质量摘要、论文图对账、假宣称、角色串台 | **确定性闸穷尽已能判定的项**；LLM 只补闸尚未覆盖的缺口；LLM 新发现的可复现坑 → **收进闸** | 只靠当次 LLM；点一下又冒新错；闸过了仍假绿 |
| **生成 / 润色** | 填岛、E-R/模块/测例文案、PPT 整形、用例润色、样例开题 | **强校验 + 失败回退确定性/静态稿**；不得发明未交付能力 | 无校验瞎写；失败仍当成功写出 |

学生包客服对话属于产品能力岛，**禁止**用工厂 Key；也不用本册「审→闸」替代 FAQ/门禁。

## 审类硬纪律

1. **确定性先行**：无 Key / 超预算 / 模型失败时，已收闸项仍须一次列全（可挡 ZIP 的 error 不得消失）。  
2. **一次收齐**：同一次调用把当前证据包内可判定问题列完；禁止「先报两条、修好再冒」。  
3. **发现即收闸**：LLM（或人工）确认可复现的规则 → 写入 `_structural_findings` / `diagram_rubric` / `domain_vocab` 等共享闸，并加正反测；**禁止**只擦当面包。  
4. **LLM 不当唯一保险丝**：ZIP / 可交导出红灯必须本地可复现（见 [`validation-loop-hardening.md`](./validation-loop-hardening.md)）。  
5. **Findings 可行动**：挡交付的条须带 `where`，尽量带操作路径 / `goto`（论文图对账已示范）。

## 生成类硬纪律

1. JSON/Schema 校验不过 → 带错重试 → 仍不过 → **确定性 fallback**（见 `unit_flow`）。  
2. 温度走 `app.llm.temperature`；禁止调用点魔法数。  
3. 开了能力岛 / 开关 → 实包与文案必须真有；假成功禁止。

## 家在哪

| 审 | 家 |
|----|-----|
| 交付质量结构闸 | `backend/app/llm/agents_qa.py` → `_structural_findings` |
| 论文图规则 / 菜单对齐 | `backend/app/bake/schema/diagram_rubric.py` + `agents_thesis_diagrams.py` |
| 错域词 / 假宣称种子 | `domain_vocab` · `_honesty_findings` |
| 生成校验回退 | `backend/app/llm/unit_flow/` |

## 改 LLM 前自检

- [ ] 这是 **审** 还是 **生成**？  
- [ ] 审：新坑有没有收进确定性闸 + 测试？有没有仍「只靠再点一次」？  
- [ ] 生成：失败路径是否回退确定性？会不会假成功？  
- [ ] 有没有为当面题开平行第二套逻辑？
