---
description: 学生包 TicketStore 薄门面 + package-private *Ops；三栈对齐；禁止把脂肪正文塞回 Store
globs: skeletons/**/TicketStore.java, skeletons/**/Ticket*Ops.java
alwaysApply: false
---

# TicketStore 工作流拆分（学生包·骨架）

`TicketStore` 随域扩展会涨；**人可读无所谓，Agent 上下文太贵**。胖工作流已抽到同包 `Ticket*Ops`，Store 只留 **public 薄门面**（字段、bind/configure、一行委托）。

## 家在哪

| 类 | 职责 |
|---|---|
| `TicketStore` | public API + 静态配置字段；方法体只 `return XxxOps.…` / 短转发重载 |
| `Ticket*Ops` | package-private；含 SQL 的脂肪实现（apply / approve / page / patch / complete / dashboard…） |

已有 Ops 对照（baseline 齐全；mybatis 常自备；jpa 仅在正文与 baseline **不同** 时放 overlay）：

- 申请 `TicketApplyOps` · 审核 `TicketApproveOps` · 分页 `TicketQueryOps`
- 扩展补丁 `TicketPatchOps` · 完结 `TicketCompleteOps` · 看板 `TicketDashOps`
- 另有 Cfg / Guard / Notify / Derive / Queue / Revise / Status / Progress 等

## DO

1. **新能力 / 修工作流**：先找对应 `*Ops`；没有才新建 `TicketFooOps`，Store 只加薄委托。
2. **三栈同源**：`baseline`（jdbc）+ `persistence-jpa` + `persistence-mybatis`。行为一致；禁止只改一套。
3. **jpa 复用**：与 baseline 方法体相同 → 不写 overlay Ops，Store 直接调 baseline 类名；有差异（如 patch / complete）→ 才在 jpa overlay 放同名 Ops。
4. **搬家保行为**：只搬不改语义；Ops 内访问 Store 字段/助手写 `TicketStore.xxx` / `TicketStore.hasColumn(`；已迁助手走既有 Ops（如 `TicketDeriveOps` / `TicketQueueOps`）。
5. **私有助手**跟主流程走（如 `patchFollowExtraStr` 进 `TicketPatchOps`），不要留在 Store 喂上下文。

## DON'T

- 把 apply / approve / page / patchTicketExtras / complete / dashboard / chartStats 的脂肪正文写回 `TicketStore`。
- 为「好看」再拆 `usecases.py` / `scene_scan.py`（工厂管道；见 `capability-home`）。
- 只改当前选题 ZIP 或只改单套 Store 冒充主链路已修好。
- 借拆分改状态机、SQL、对外 API 或学生可见文案。

## 薄门面示例

```java
public static Map<String, Object> approve(
        long ticketId, boolean pass, String remark,
        String operator, boolean superAdmin, String assigneeUsername) {
    return TicketApproveOps.approve(
            ticketId, pass, remark, operator, superAdmin, assigneeUsername);
}
```
