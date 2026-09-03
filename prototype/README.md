# 运营端原型（在线预览版）

静态 HTML 原型，方便手机/浏览器直接打开对照 UI，**不是**学生交付 ZIP，也不替代 `frontend/` 正式运营台。

| 文件 | 说明 |
|------|------|
| `index.html` | 页面结构（含终期答辩 PPT 开跑 / 产物 / 对照） |
| `styles.css` | 样式 |
| `app.js` | 交互示意 |

## 匹配确认 · 技术栈与按需开关

与现网 `MatchTab` 对齐（控件在匹配确认，**不**进一键生成视觉区）：

- **持久层**：`jdbc` / `mybatis` / `jpa`
- **Spring Security**：关（默认）/ 开 · 过滤器链
- **AI 助手**：关（默认）/ 开 · Spring AI + DeepSeek + FAQ  
  解锁后可手改；与推荐不一致时左侧「推荐 · 当前出包」双显。  
  演示状态下拉可选 **「AI 助手双显」** 看推荐开≠拟选关。

正式口径见 `.cursor/rules/ai-assistant-delivery.mdc`、`docs/ai-opening-delivery-map.md`。

## 答辩 PPT（设计见 `docs/defense-ppt-module.md`）

演示状态下拉可切换：

- **可生成答辩 PPT** — bake 通过后，「一键生成」下半截解锁；封面字段 + 校徽（Word 粘贴为主，默认原样，去掉白底可选）全部必填才可开跑
- **答辩 PPT 生成中** — 独立短任务流水线（非程序同次步骤）
- **答辩 PPT 已生成** — 产物行 + 对照子 Tab「答辩 PPT」；可检查 / 导出 PPTX（不进 ZIP）
- **答辩 PPT 业务脏** — 脏标横幅；禁止导出，须「按工程更新业务页」

在线预览（若已发布）：见仓库根 [`README.md`](../README.md) 里的 GitHub Pages 链接。本地可直接双击 `index.html` 打开。
