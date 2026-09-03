# 开题 AI 表述 → 工厂产出对照表

> **用途**：接单 / 匹配 / bake / 写 README·论文「系统实现」时查表。保证**开题怎么写、实包能交什么**一一对应。  
> **真源**：代码行为以本表「工厂产出」列为准；扫词以 `features/ai_assistant.py`、`stack_scan.py` 为准；硬拒以 `capabilities.py` → `OUT_OF_SCOPE_SIGNALS` 为准。

---

## 1. 三秒判型（先判再 bake）

| 判型 | 怎么认（题名 + 主路径） | 工厂动作 |
|------|------------------------|----------|
| **A. 业务 + AI 挂件** | 主路径是商城/借阅/预约/报修等 CRUD+交易；AI 在「特色/创新点」一节 | **接**；`DOM-*` 按场景 + **`ai_assistant` 推荐开** |
| **B. AI 主产品** | 题眼是「RAG 平台 / 向量库工程 / 模型训练 / 病虫害 CNN / 多 Agent 平台 / 小程序多模态主路径」 | **标不支持或拒**；禁止用 FAQ 聊天壳冒充整题 |
| **C. 纯业务** | 全文无 AI/大模型/智能客服类词 | **不接 AI**；`ai_assistant` 保持关 |

**混写默认拆句处理**（同一段里出现多个 AI 词）：

- 大模型问答 / 导购 / 客服 → `ai_assistant`
- 协同过滤 / 矩阵分解 → **不当已交付**（可挂规则 `recommend`，论文写「规则推荐」）
- Milvus / Chroma / 向量库集群 → **不当已交付**（FAQ 表代替；论文写「结构化知识表」）
- Redis 会话 / 向量 → 演示包 **标不支持**（除非另开任务）

---

## 2. 匹配确认操作清单（保证产出）

1. **领域 `DOM-*`**：按开题场景（农产品/商城 → `DOM-SHOP`；图书 → 借阅/商城壳；宿舍报修 → 对应域）。
2. **AI 助手开关**（匹配确认，与 Security 同级）  
   - 开题命中 §3 任一词 → **推荐开** → 确认 **开 · DeepSeek 助手岛**  
   - 拟选 ≠ 出包 → **双显**（生成前弹窗 + MatchTab）
3. **一键生成** → 业务逻辑与其余 cap **不变**。
4. **验收**（`ai_assistant=true` 时）：  
   - `spec.json` 含 `ai_assistant` cap  
   - `sql/schema.sql` 含 `sys_ai_knowledge` / `sys_ai_message` / `sys_ai_feedback`  
   - 门户菜单 **AI助手**；管理端 **AI知识库**  
   - 用户侧：**右下角悬浮图标 + 对话弹窗**（`AiAssistantFloat`）；顶栏不重复挂 AI  
   - 管理端：知识 CRUD + 咨询统计（**不是**用户同款聊天窗）  
   - README 含 DeepSeek / `DEEPSEEK_API_KEY` FAQ  
   - 无 Key 时问答仍可用（FAQ 回落）

---

## 3. 开题表述 → 工厂产出（主对照表）

| 开题常见写法 | 推荐开关 / cap | 实包交付（已实现） | 论文/README 建议写法 | 禁止写成 |
|-------------|----------------|-------------------|---------------------|----------|
| 智能客服 / 智能导购 / 智能助手 / 智能问答 / 智能答疑 | `ai_assistant` **开** | 悬浮对话 + Spring AI + DeepSeek；无 Key → FAQ | **Spring AI** 对接 DeepSeek；知识表 + 大模型补充 | 自研大模型 |
| AI智能农产品导购 / 对话式商品推荐 | 同上 + 农产文案种子 | 同上；标题可变为「AI智能农产品导购」 | 同上 + 领域 FAQ 种子 | CNN 识图 |
| 大模型 / ChatGPT / DeepSeek / 通义 / 百炼（作客服） | `ai_assistant` **开** | `DeepSeekClient`（Spring AI `DeepSeekChatModel`） | 写 **Spring AI + DeepSeek** | 本地训练 |
| Spring AI / LangChain4j（技术路线） | `ai_assistant` **开** | pom 含 `spring-ai-bom` + `spring-ai-deepseek`；`DeepSeekClient` 调 `DeepSeekChatModel` | **采用 Spring AI 对接 DeepSeek API**（与实包一致） | 写了 Spring AI 但 pom 无依赖；另写第二套 HTTP 客户端 |
| 知识库匹配 / 知识库问答 / 智能匹配知识库 / RAG 问答 | `ai_assistant` **开** | `sys_ai_knowledge` + 关键词匹配 + LLM 上下文 | **结构化知识表 + 检索匹配**；非 Milvus 集群 | 企业级 RAG 平台 |
| 知识库 / 文库 / 资料下载 / 附件下载 | `doclib`（≠ AI） | 文库下载台账 | 资料下载管理 | RAG 向量库 |
| 两者都写 | `ai_assistant` + `doclib` | 两套菜单分写 | FAQ 问答 vs 文件下载 **分开描述** | 一个词两用 |
| 文字问答 / 多轮对话 / 会话记录 | `ai_assistant` **开** | 消息表分页；单轮为主，历史可查 | 会话持久化 + 多轮上下文（按实包：消息历史） | Redis 分布式会话 |
| 满意度反馈 / 热门问答 / 咨询热度 | `ai_assistant` **开** | 反馈表 + 热门 API；管理端 stats | 用户反馈与热门知识统计 | — |
| 语音播报 / TTS | `ai_assistant` **开** | 浏览器 `speechSynthesis` | **浏览器语音播报** | 自研语音模型 |
| 图片上传匹配 / 识图 / 识别品类 | `ai_assistant` **开** | `/ask-image` 文件名→品类映射演示 | **演示级品类映射** / 接口识别 | CNN / 以图搜图 |
| 猜你喜欢 / 个性化推荐 / 相关推荐 | `recommend`（规则） | `RecommendStore` 规则引擎 | **规则推荐**（分类+热度+上新） | 协同过滤 |
| 协同过滤 / 矩阵分解 / UserCF / ItemCF | **不挂为已交付** | 最多规则 `recommend` | 规则推荐或写「规划」 | 已实现协同过滤 |
| 意图识别 / Agent / Tool 调用 / 自动下单 | **未交付** | 仅 FAQ 问答 | 规划或「问答为主」 | Agent 已落地 |
| SSE 流式 / 打字机 | **未交付** | 同步 JSON 回复 | 同步请求-响应 | 流式已上线 |
| ECharts / 数据可视化 / 销量统计 | 基线常驻 | 管理端图表 | 直接写 ECharts | — |
| 深度学习 / CNN / 卷积神经网络 | **硬拒** | — | 不写已实现 | — |
| 以图搜图 / 视觉检索引擎 | **硬拒** | 仅演示映射 | 演示口径 | 自研视觉 |
| 小程序 / 安卓原生 | **硬拒**（主交付） | Web 分离包 | 非本仓库主形态 | — |

---

## 4. 按业务域：开题模块 → 工厂组合（可复制）

| 场景 | 领域 | 业务 cap（默认/常见） | AI 相关 |
|------|------|----------------------|---------|
| 农产品/商城/特产 | `DOM-SHOP` | 订单、购物车、评价、地址、ECharts | `ai_assistant` |
| 图书借阅 + AI 馆员 | 借阅域 + 内容 | 借阅、公告、收藏 | `ai_assistant` + 可选 `recommend` |
| 宿舍/报修/预约 + 办事问答 | 对应 `DOM-*` | 工单/预约主路径 | `ai_assistant`（FAQ 换种子） |
| 文库/制度下载 | `DOM-DOCLIB` 或 doclib | `doclib` | 仅下载台账；问答另开 `ai_assistant` |
| 纯 RAG 知识库平台（B 类） | — | — | **不接**或整包拒 |

**跨域原则**：只有一个 `ai_assistant` 岛；换域只换 **FAQ 种子 + 页面标题**，不复制 Java/Vue 工程。  
**分类同字**：商城 FAQ 分类名 = `shop_product_kind` 货架分类（`SHOP_KIND_CATEGORIES`，如农产→水果/蔬菜/粮油）；请假→事假类/病假类；点餐→套餐/面食/饮品；报修→水电/公共设施/门禁。

---

## 5. `ai_assistant` 开时实包清单（与 gate 一致）

| 层级 | 路径 / 对象 |
|------|-------------|
| 开关 | `spec.ai_assistant` / `addons.ai_assistant` / cap `ai_assistant` |
| SQL | `sys_ai_knowledge` / `sys_ai_message` / `sys_ai_feedback` + **按域/开题自动灌 FAQ 种子**（农产/商城/图书/宿舍报修/请假/点餐/文库/通用） |
| 后端 | `AiAssistantController`, `AiAssistantStore`, `AiBizContext`（只读复用 Archive/Order/Ticket/Doclib）, `DeepSeekClient`（**Spring AI** `DeepSeekChatModel`） |
| 前端 | `AiAssistantFloat.vue`（门户悬浮弹窗）、`AiAssistant.vue`（说明页）、`admin/AiKnowledgeAdmin.vue` |
| 路由 | `/ai-assistant`（说明+打开弹窗）、`/admin/ai-knowledge`（`hasCap('ai_assistant')`） |
| API | `/api/ai-assistant/ask`, `hot`, `feedback`, `knowledge`, `ask-image` |
| README | `${AI_ASSISTANT_FAQ}` → DeepSeek + 无 Key 回落说明 |
| Key | 环境变量 `DEEPSEEK_API_KEY`（可选 `DEEPSEEK_BASE_URL`, `DEEPSEEK_MODEL`） |

关开关时：无 cap、无 SQL 种子、无菜单、README 无 DeepSeek 段；Java 文件仍在 baseline 但不挂载。

---

## 6. 论文 / README「系统实现」模板（可直接粘贴改名词）

**AI 助手（与实包一致）：**

> 系统采用前后端分离架构。用户侧通过门户**右下角悬浮助手**进行对话问答；管理端维护 **MySQL 结构化知识表**并查看咨询统计。智能助手模块基于 **Spring AI**（`DeepSeekChatModel`）对接 **DeepSeek**（`DEEPSEEK_API_KEY`）。回答依据两类只读材料：**知识库条目**，以及按已开通能力从本系统查询的**业务摘要**（分类与在架条目、本人购物车/订单、本人借阅或报修等办理单——复用现有 Store，不另写查询、不自动下单改状态）。未命中或明显无关问题返回固定提示。无 Key 时直接返回知识原文或业务摘要。支持热门知识展示、用户满意度反馈；图片上传采用 **品类映射**（非卷积神经网络）；答案播报采用 **浏览器 Web Speech API**。本系统未实现本地模型训练、向量数据库集群与协同过滤推荐。

**若开题写了协同过滤但实包只有规则推荐：**

> 商品推荐采用 **规则策略**（分类偏好、热度与上新兜底），非协同过滤矩阵分解。

---

## 7. 扫描词真源（维护时改代码，本文同步）

### 7.1 推荐开 `ai_assistant`（`stack_scan.AI_ASSISTANT_HINTS` + `features/ai_assistant._AI_ASSISTANT_SIGNALS`）

智能客服、智能导购、智能助手、智能问答、智能答疑、AI智能导购、AI智能客服、AI助手、大模型、ChatGPT、DeepSeek、对话式商品推荐、知识库匹配、知识库问答、智能匹配知识库、语音播报、农产品文字问答、图片上传匹配、Spring AI、LangChain4j、RAG、检索增强、阅读助手、馆员问答、智能体、满意度反馈、热门问答、多轮对话（与 AI 同框时）等。

### 7.2 硬拒 / 降级（`OUT_OF_SCOPE_SIGNALS`）

深度学习、卷积神经网络、以图搜图、协同过滤、矩阵分解、人脸、指纹、物联网、小程序原生、真支付、硕博课题等 → 见 `capabilities.py`。

### 7.3 易混

| 词 | 走 |
|----|-----|
| 裸「知识库」且无问答语境 | 可能命中 `doclib`；有「匹配/问答/导购」→ `ai_assistant` |
| 「推荐算法」 | `recommend` 规则，非 AI 岛 |
| 「ECharts」 | 基线，非 AI |

---

## 8. 代码索引（改行为先改此处）

| 环节 | 文件 |
|------|------|
| 开题扫词（cap） | `backend/app/bake/features/ai_assistant.py` |
| 开题扫词（匹配推荐） | `backend/app/bake/stack_scan.py` |
| 挂 cap / 菜单 / gate | `apply_ai_assistant_to_spec` → `domain_schema.attach_accept` |
| SQL 种子 | `backend/app/bake/sql/fragments.py` → `ensure_ai_assistant_sql` |
| 开关解析 | `backend/app/bake/addons.py` → `resolve_ai_assistant` |
| README | `addons.ai_assistant_readme_bits` + `engine_sql._patch_student_readme` |
| 学生运行时 | `skeletons/baseline/.../AiAssistant*.java`, `DeepSeekClient.java`, `AiAssistant.vue` |
| 匹配 UI | `frontend/.../MatchTab.vue`, `useProjectDetail.js` |
| 门禁 | `backend/app/bake/gate_contracts.py` → `merge_ai_assistant_gate` |
| 冒烟测试 | `backend/tests/test_ai_assistant_bake.py`, `test_stack_scan.py` |
| 规则 | `.cursor/rules/ai-assistant-delivery.mdc` |

---

## 9. 典型开题段落示例（农产品 · 全量可交）

**开题原文要点** → **工厂配置**：

- 注册登录 / 地址 / 分类商品 / 购物车订单 / 评价 / 后台 / ECharts → `DOM-SHOP` 默认能力  
- 核心特色 AI 导购 / 知识库 / 语音 / 满意度 / 热门问答 → **`ai_assistant` = 开**  
- 技术路线 SpringBoot + Vue + DeepSeek → 跟开题；持久层未写则 jdbc 默认  

**不要**：为农产品单独建 `DOM-FARM` 或第二套 AI 工程。

---

*文档版本与 `ai_assistant` 岛同步；变更扫词或交付边界时请同时更新 §7 与本文件。*
