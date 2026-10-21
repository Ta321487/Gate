---
description: AI IDE 接力开发：接手三步走（读 HANDOFF/跑测试/看 git log），交活三步走（测试绿/更新 HANDOFF/小步提交推送）；同一时间只开一个 AI IDE
alwaysApply: true
---

# AI IDE 接力开发

工厂要在多个 AI IDE / agent（Cursor、Trae、Doubao 等）之间接力。接力的目标：**下一个 AI 不读全量代码，也能立刻知道干到哪、接着干**。

## 接手三步走（开场必做，按序）

1. **读交接**：先读 `HANDOFF.md`（当前主线 / 中断点 / 下一步 / 坑）；核心规则读 `AGENTS.md`；需要仓库认知时用 AOCI 精确查，禁止默认整仓 overview。
2. **跑测试**：`cd backend; .\.venv\Scripts\python.exe -m pytest -q tests\xxx.py`；**红的测试就是上一个 AI 的中断点**。
3. **顺脉络**：`git log --oneline -20`、`git status` 看提交与未提交改动，确认当前在做哪个主题。

## 交活三步走（收工 / 切换必做）

1. **测试绿**：把本主题测试跑到绿；环境噪声类的红如实标注，不许假绿、不许把没做完的说成做完。
2. **更新交接**：刷新 `HANDOFF.md`——当前主题、干到哪、下一步、坑、测试结果（通过数 / 红数及原因）。
3. **小步提交推送**：一个主题一条，按 `commit-messages` 规则；推送后下一个 AI 才能从 git 接手。

## 接力是轮流，不是同时

- 同一时间只开**一个 AI IDE + 必要后端**；切换时关掉旧的，崩溃残留进程要清（`scripts/kill-dup-backend.ps1`）。
- 规则两处同步：改了 `.cursor/rules` 必须跑 `scripts/sync-ide-rules.ps1` 同步到 `.trae/rules`，禁止两套规则漂移。

## 交接物（接力棒）

| 文件 | 作用 |
|---|---|
| `HANDOFF.md` | 新对话第一入口：主线 / 中断点 / 下一步 / 坑 |
| `AGENTS.md` | 通用 agent 规则与 AOCI 用法 |
| AOCI（`.aoci` / `aoci*.txt`） | 仓库认知，精确查、按需读 |
| `docs/parked-work.md` | 搁置台账 |
| `git log` | 提交即轨迹 |

## 冲突

与 `00-factory-core`、`boss-intent` 一致时强化；冲突时以工厂主链路与“交接 / 规则保持最新”为准。
