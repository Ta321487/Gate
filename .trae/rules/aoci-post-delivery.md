---
description: 业务收尾后 AOCI 流水线：有新文件先 scope acknowledge 再 maintain
alwaysApply: true
---

# AOCI 收尾流水线

业务需求做完、受管理对象已达最终稳定态后，按序收尾认知。不要只跑 `aoci_maintain` 就结束。

## DO

1. 先判：本次是否新增了受 AOCI 管理的路径（新 `.py` / Store / Controller / Vue 等）。
2. **有新文件** → 先 `scope acknowledge`（或当前 Guide/`aoci` 等价命令）把新路径纳入 Managed Scope，再调用一次 `aoci_maintain`。
3. Maintain 若返回 candidates → 按合同完整创作并 `aoci_update_entry`；`remaining` 非零则继续 Maintain。
4. 无新文件、仅改已管对象 → 可直接 `aoci_maintain`（仍等业务稳定后再调）。

## DON'T

- 业务刚写完、Maintain 因 `code_missing` / scope 未承认被 `blocked` 时停住不处理。
- 未 acknowledge 就反复 Maintain 或跳过认知收尾。
- 把测试夹具、缓存、用户未要求进管的杂文件强行 acknowledge。

