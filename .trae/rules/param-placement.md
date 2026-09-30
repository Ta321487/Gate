---
description: 参数落点：单据/业务参数进生成的 Java 策略类，yml 只留身份与共享尺
globs: backend/app/bake/**, skeletons/**
alwaysApply: false
---

# 参数落点（主链路·bake/骨架）

新增或改动业务参数**前先定落点**。学生包里**不得**出现成排的工厂腔 yml 键。

## 三分法（唯一口径）

| 参数性质 | 落点 | 例 |
|----------|------|----|
| **单据参数与单据开关** | bake 生成交付包 `config/TicketPolicy.java`；真源 `backend/app/bake/ticket_policy.py` | `ticket-loan-days` → `TicketPolicy.LOAN_DAYS` |
| **非单据业务参数与能力开关**（档案/订单/预约/lookup 表位、下拉标签、库存与积分阈值、`*-enabled`） | bake 生成 `config/AppPolicy.java`；真源 `backend/app/bake/runtime_policy.py`（`FIELDS` / `FLAG_KEYS`） | `archive-item-table` → `AppPolicy.ARCHIVE_ITEM_TABLE` |
| **身份 / 会话 / 门禁 / 共享尺**（`runtime_policy.KEEP_YML_KEYS`，禁止下沉） | 留 `application.yml` 的 `thesis:` 段 | `title`、`register-role`、`password-hash`、`portal-guest-browse`、`guest-teaser-limit`、`allow-appoint-from-users`（门禁校验 yml↔schema）、`use-quota`（与 `OrderStore` 共用） |
| **时序类（仍无独立 cap）** | yml | `order-timeout-minutes` |

口径沿革：2026-07-25 前各 `DOM-*.sql` 内置 `sys_config` 表 → 之后 yml `thesis.ticket-*` → 现在 Java 策略类（学生可读可改）。

> **子开关口径**：`AppPolicy.FLAG_KEYS` 目前只收**主开关**；子开关与阈值（如 `points-checkin-enabled`、`coupon-enabled`、`slot-require-remark`、`stock-count-lock`、`member-tier-basis`）仍在 yml，binder 仍以 `@Value` 读取（baseline binder 现存 66 个 `thesis.` 键，其中仅 `register-role` / `password-hash` / `use-quota` 属保留集）。要下沉子开关就一并扩 `FLAG_KEYS` + 三份 binder 常量 + 差分，**不许只改一半**。

## DO

1. 新参数先加**对应真源**（单据 → `ticket_policy.py`；非单据 → `runtime_policy.py`）的 `FIELDS` / `FLAG_KEYS`（+ `COMMENTS`），再 `render()` 出 Java；`skeletons/baseline`、`overlays/persistence-mybatis`、`overlays/persistence-jpa` 三份 `config/TicketPolicy.java` / `config/AppPolicy.java` 与 bake 产物**逐字一致**（`backend/tests/test_ticket_rules_bake.py` 对账；骨架缺就补骨架，别只让 bake 生成）。
2. `write_policy(...)` 必须在 **java 包名 remap 之前**调用；**两条写盘路径**都要接：`engine_bake.py` 与 `engine_islands.sync_workspace_thesis_yml`。
3. binder 侧用常量：`DomainRuntimeBinder` 里 `@Value("${thesis.ticket-*}")` → `TicketPolicy.XXX`、非单据键 → `AppPolicy.XXX`；**按各文件实际引用数替换**（jpa 引用数少于 baseline，别按 baseline 全量套）。
4. 改完跑下表验收三件套。

## DON'T

- 把单据/业务参数写回 `application.yml`（含 `ticket-*` 与 `enable-ticket` / `use-deadline` / `allow-multi-ticket` / `check-time-conflict`；非单据键同理由 `runtime_policy.py` 收口）。
- 下沉 `runtime_policy.KEEP_YML_KEYS` 里的键，或把两个策略类揉成一个（TicketPolicy = 单据主流程；AppPolicy = 表位 / 标签 / 阈值 / 非单据开关）。
- 动共键发射守卫：`use-quota` 由 `if enable_ticket:` 与下方 `order_lines` 块分别发射，**放宽即重复发键**。
- 下沉「写进 yml 但全链路无人读」的死键（先做读取侧鉴权）。
- 漏掉实体驱动的开关收集（如 `LEVEL_AFFECTS_DEADLINE`），或把新键塞进别人的策略类。

## 验收三件套

1. 真 bake 三线（jdbc / mybatis / jpa）+ `mvn -q -DskipTests compile` → 必须 `rc=0`。
2. **全域名差分**：取 `git show HEAD:backend/app/bake/engine_bake.py` 与新版，对 68 个域各跑一遍 `_patch_thesis_yml`，剔除目标键后**键多重集必须相等**（重复键就是靠它抓出来的）。
3. 定向 pytest + `test_ticket_rules_bake.py` 三条护栏（骨架↔渲染器一致 / binder 无 yml 占位 / `use-quota` 唯一）。

长表：`docs/capabilities.md`（扫词写配置 / 扫词写代码常量）· `docs/invariants.md`
