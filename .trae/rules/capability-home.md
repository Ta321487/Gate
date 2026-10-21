---
description: 工厂进程重构重点：backend/ 与 frontend/；一条逻辑一个家；不改现有执行，不动学生包
alwaysApply: true
---

# 工厂进程重构

重构重点是工厂自己的进程，不是学生包。

- 在范围内：仓库根 `backend/`（Python，含 bake）和 `frontend/`（工厂控制台）。这两个在工厂进程里跑。
- 不在范围内：`skeletons/` 的 Java / Vue。那是学生包，这次不搬，也不借重构改它的执行。

一条逻辑一个家，不按新旧分。只搬家。工厂接口、bake 出包、页面行为必须与搬家前一致。

## 家在哪

- bake 能力正文：`backend/app/bake/features/<cap>.py`（扫描、菜单、`ensure_*` SQL）。`sql/fragments.py` 只按开关调用，不再长正文。
- 工厂 API / 服务：归已有模块（`app/api`、`app/services`、`app/llm`）。禁止新函数外调、正文仍堆在 `projects.py` 这类宿主里。
- 工厂页面：正文跟页面走（`frontend/src/views/`）。禁止只抽新交互、旧交互留在 `useProjectDetail.js`。

## DO

1. 碰哪块，同一次把该块旧正文搬走。半截不算做完。
2. 先用现有测试钉住行为，再搬。同一输入仍是同一输出。
3. 新逻辑直接进自己的家。禁止在宿主里再写一份正文。

## DON'T

- 把学生包 Store / 页面当成这次重构对象。
- 新逻辑走调用、老正文留在宿主。
- 借搬家改匹配、出包内容、接口字段、文案。
- 为行数拆文件。`usecases.py`、`scene_scan.py` 这种互调用管道不拆。
- 未钉行为就搬。本规则生效不等于动手搬。
