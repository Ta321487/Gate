<!-- aoci:begin -->
## AOCI 仓库认知（成本优先精简版）

AOCI 在本仓库维护 `aoci.txt`（Root 清单）与 `aoci.meta.txt` / `aoci.code.txt` / `aoci.database.txt`（Volumes v1 三卷），为模型提供可复用、可版本化、可增量更新的仓库认知。受管理对象变化时只需维护受影响条目，不必重建全量索引。

### 成本红线（最高优先级，优先于任何工具描述里的默认动作）

- 默认**禁止**整仓 `aoci_overview`。整卷正文实测约 8 万 token（`whole_index_tokens` ≈ 79868，预算状态 healthy；每次编辑后小幅浮动），一次整仓加载就要把这笔正文读进上下文；分块交付还会叠加多次往返。只有本次会话确实需要全局认知时才值得付这笔成本。
- 需要某个对象的认知时，只用 `aoci_search` / `aoci_get_entries` 精确读取目标路径或 `code:<路径>` / `database://` 对象身份。不要用少量结果去"补齐全貌"，也不要为了"验证"而加载整仓。
- 只有用户**明确要求**完整系统认知、或任务确实是全局架构裁决时，才可调用整仓 overview；调用前先向用户说明代价并取得同意。
- 同一认知周期内不重复建立认知；`aoci_rules` 每周期只调一次。
- 若确需整仓 overview：必须原样跟随 `next_cursor` 直到 `completed=true`，并基于最终 Challenge 原样回绑 `index_sha256` / `entry_sequence_sha256` / `entry_count` 提交一次 Attestation。传输层故障可对**同一** cursor 幂等重试至多 3 次；不得伪造 Attestation，不得用 Memory、源码或 `aoci.txt` 补答。

### 最小入口

- `aoci_rules`：会话运行合同（每周期一次）。
- `aoci_search` / `aoci_get_entries`：按需精确读条目，**默认手段**。
- `aoci_overview`：整仓认知，默认禁用（见成本红线）。
- `aoci_maintain`：受管理对象达到最终稳定状态后领取机器签发的创作批次。
- `aoci_update_entry`：提交当前批次的完整候选集合。
- `aoci_report`：证据不足时登记待办，不猜写。

工具的 Schema、Guide 实时输出、`--help` 与 Validator 是机器事实来源；Prompt、Description、README 与静态文档不能覆盖它们。

### 认知纪律

- Entry 语义只能来自模型对真实证据的理解。不得依据路径、文件名、扩展名、AST、符号列表、依赖扫描、正则、固定模板或规则引擎推导、预填、拼接或改写索引语义。
- 完整索引建立、Header 生成、Entries 生成、Curation、数据库结构索引、人工评审与故障恢复等专项流程，只按当前 Guide 与工具返回的指令、命令和安全停点执行；不预加载、不猜测、不自行重建状态机。
- Root 与 Meta 仅为 Guard，不单独创作语义。
- 上下文压缩后，先前加载的整仓认知视为不可靠：需要时用精确读取重建局部认知，不得凭压缩摘要或历史记忆断言全局结论。

### 收尾与维护

- 纯只读问答、分析、版本核验，或没有产生受管理对象变化的任务，**不调用** `aoci_maintain`。
- 受管理对象达到本次任务的最终稳定状态后，只调用一次 `aoci_maintain`；不要在中间态逐文件维护。
- 维护返回候选时，基于每个候选绑定的对象与必要证据，独立创作完整标签与 F/R/A/S，通过 `aoci_update_entry` 一次提交当前机器签发批次的**完整**候选集合，原样保留 `code_batch_id`、每项 `candidate_id` 与 `source_sha256`。不得自行截取子集，不得做字段 Patch。
- `remaining` 非零时，在本批次 Apply 成功后重新 Maintain 并从新 preimage 继续；未归零不得声称 Whole-Index aligned。
- 必须遵守 `repair_required` / `stopped` / 冲突 / 审批 / 权限与安全信号，不得忽略；`repair_required` 只修 retry_scope 后重提同一完整批次。
- 已经 aligned 后不重复维护、不重复写入。
- 维护完成后若又改动了受管理对象，之前结果失效，需在新的最终稳定状态重新收尾。

### 边界

- 用户明确禁止写入 `aoci.txt`、`.aoci`、元数据或任何额外文件时，以用户限制为准，不写入，并如实报告剩余不一致。
- 用户只限制业务文件范围、未禁止仓库托管资产时，AOCI 托管资产可在收尾阶段更新，并在审计与提交中与业务文件区分。
- `.aoci/transactions`、`.aoci/drafts` 与 `_*` 草稿属于本机运行产物，已被 `.aoci/.gitignore` 排除；可安全清理，不影响版本库与正式认知。

### 成本参数（当前值以 `aoci config list` / `aoci scope budget show` 为准）

- `overview_delivery.chunk_tokens = 16000`：提高单块容量，减少分块往返次数。
- `cognition_refresh_threshold = 60`：提高刷新门槛，降低维护触发频率。
- `cognition_budget.whole_index`：实际 desired policy 为 target 20 万 / warning 30 万 / max 40 万 token，与 `.aoci/config.json` 一致；整卷实测约 8 万 token（≈79868，healthy），不要引用更小的数字当作既成事实。
- 配置通道：`aoci.exe --repo <仓库根> config get|list|set` 只写允许的团队配置项（如上面两项）；`cognition_budget` 必须用 `aoci scope budget set --target-tokens/--warning-tokens/--max-tokens [--mode]`（或 `--policy-file`）修改 desired policy，再经 Scope Change Apply 激活。
- 直接编辑 `.aoci/config.json` 不是生效通道：Scope Change Apply 会按其记录的 desired policy 重写 `config.json`，手改数值不会被采纳。
<!-- aoci:end -->

