# 学生包 AI 助手交付契约（细则档案）

> 操作手册（短规则）见 `.cursor/rules/ai-assistant-delivery.mdc`。对照表见 [`ai-opening-delivery-map.md`](./ai-opening-delivery-map.md)。

## 与现网关系

- 工厂 LLM（`backend/app/llm/*`）与 Key **禁止**进学生 ZIP。
- 学生包：`addons.ai_assistant`；运行时 Spring AI + DeepSeek（env `DEEPSEEK_API_KEY`）；禁止第二套手写 HTTP 客户端。
- AI **不是** `DOM-*` / `spine` / `persistence` / `ARCH-*`；对标按需开关。

## 接单

| 类型 | 口径 |
|------|------|
| A 业务+AI 挂件 | 接；开 `ai_assistant` |
| B AI 主产品（RAG/CNN/多 Agent 平台等） | 不支持；禁止聊天壳冒充 |

## 开则必交

对话问答（FAQ 回落）、只读接业务 Store、知识种子按域灌（`resolve_ai_knowledge_skin`）、会话/满意度/热门问答。

演示级：浏览器 TTS、文件名/类目映射识图。不交：真视觉/协同过滤/人脸/Agent 下单等。

## 防撞

`recommend`≠大模型推荐；`search_assist`≠语义检索；`doclib`≠RAG；`guestbook`/`dm`≠AI 客服。

## 禁止

工厂 Key 进 ZIP；按行业复制多套助手；FAQ 写死农产；关开关仍写已集成 DeepSeek。

## 核对

`tests/test_ai_assistant_bake.py` + 至少一域 bake 冒烟。
