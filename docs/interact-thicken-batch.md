# §1.9 互动/匹配组加厚批次

> **本文只负责**：地图 [`opening-feature-delivery-map.md`](./opening-feature-delivery-map.md) §1.9「本组待补」的**分批实现顺序、挂载口径、验收勾选**。  
> **不负责**：cap 定义（[`capabilities.md`](./capabilities.md)）；怎么审交付（[`delivery-audit-rules.md`](./delivery-audit-rules.md)）；清待补工序纪律（`.cursor/rules/opening-group-delivery.mdc`）。  
> **状态**：**进行中**（批次立项；I-00 起尚未迁行）。地图 §1.9 待补约 **100** 条实现债（表内 2 条不支持已剔出，只留边界）。  
> **索引**：[README.md](./README.md) · 地图 §1.9 · 范本 `content_thicken` / `reserve_thicken` / `trade_thicken`。  
> **不负责 UI 表面构图**：列表选型见 [`domain-group-ui-styles.md`](./domain-group-ui-styles.md)（本组加厚收口后再开实现 plan）。

---

## 0. 硬口径（写代码前先背）

### 0.1 一组一包

| 规则 | 含义 |
|------|------|
| **组模块** | `backend/app/bake/features/interact_thicken.py` + `apply_interact_thicken_to_spec` |
| **注册** | 必须挂进 `backend/app/bake/domain_schema.py`（紧接 `content_thicken` 之后） |
| **白名单** | `HUB_BYPASS_MODULES` + [`capabilities.md`](./capabilities.md) Hub 例外表同步登记 |
| **域集合** | `INTERACT_DOMAINS` = DATING / MUTUAL-TUTOR / MUTUAL-TOPIC / MUTUAL-TEAM / CARPOOL / TIMEBANK / EXAM / SURVEY / VOTE |
| **不抢邻组** | 不碰 §1.6 交易、§1.7 预约、§1.8 内容；DATING∩ACTIVITY、MUTUAL∩MEETING 只做**文案交叉**，不另起邻组状态机 |
| **Store 主战场** | 分域：`ExamStore` / `SurveyStore` / `VoteStore` / `TimebankStore`；双选/拼车/婚恋意向辅 `TicketStore` + `ArchiveStore`；私信辅 `DmStore`；收藏辅 Favorites |
| **一轮只清本组** | 禁止同轮动 §1.8/§1.10；禁止只改地图不改骨架 |

### 0.2 一条待补 = 四件套 + 三骨架

硬口径：**管理端能管 + 用户端可产生数据（真写库）**。纯 Hint / 只读 / 打印 / 前端零读取字面量 → 不得标已齐。

| 件 | 真源 |
|----|------|
| ① 表 / 列 | `ensure_interact_thicken_sql` + 既有 exam/survey/vote/timebank/ticket/archive 列 |
| ② Store 写方法 | 上表各 Store（三套骨架同改） |
| ③ API | 对应 Controller |
| ④ 前端控件 | 用户端作答/志愿/行程/资料 + 管理端审核/导出/配置 |

三骨架：`baseline` · `persistence-mybatis` · `persistence-jpa`。

### 0.3 挂载：域默认 vs 扫词加深

| 类型 | 何时开 | 地图「挂载」列 |
|------|--------|----------------|
| **九域壳内底** | INTERACT_DOMAINS 主路径刚需（按域裁剪；双选三壳共享 mutual_select 加深） | **域默认** |
| **能力岛加深** | 仅当已挂对应 cap（`favorites` / `allowRating` / `dm` / `content_report` / `deadline` 等） | 扫词挂 cap 时（I-11） |
| **禁止** | 因「互动常见」把协同过滤推荐、真地图、人脸监考、实时 IM SDK 做成永远开 | — |

组口径（地图原话）：双选/考试/问卷/投票/拼车/时间银行/婚恋等；多数无商城订单主路径。

### 0.4 不支持（不进待补实现）

| 边界 | 原因 |
|------|------|
| 婚恋匹配推荐算法 / 恋爱社交推荐 | 协同过滤；筛选 + 私信顶 |
| 投票刷票检测中台 | 浅 IP/实名提示顶 |
| 真地图导航拼车 | 途经点文本 / 校区字典顶 |
| 人脸监考 | 监考口令 + 防切屏提示顶 |
| 实时 IM SDK | 站内 `dm` 短轮询顶 |

### 0.5 每批工序（固定）

```
1. interact_thicken：开关 / labels / 域默认或扫词条件
2. ensure 列 / 子表（禁止 JSON 冒充三范式）
3. 对应 Store 写方法 — 三套同改
4. Controller API — 三套 DomainRuntimeBinder 同绑
5. 用户端写控件 + 管理端管控件（文案无工厂腔）
6. 三绿才迁行：
   - pytest backend/tests/test_opening_map_skeleton_gate.py -q
   - pytest backend/tests/test_interact_thicken_features.py -q
   - 受影响的 backend/tests/test_schema_*.py
7. 地图：待补 →「本组本轮已齐」；本册状态改已齐；changelog 一行
8. 业务稳定后 AOCI maintain（新 .py 先 scope acknowledge）
```

单批体量：**约 8～14 条**；含子表/状态机/组卷引擎时砍到 6～8。

### 0.6 已有半截优先钉齐（忌重写）

| 待补表述 | 现网线索 | 策略 |
|----------|----------|------|
| 心动列表 | `favorites` | DATING 挂上时钉双端；禁止第二套收藏表 |
| 拼车/时银/双选评价 | `allowRating` / 既有评价开关 | 仅 cap 或域皮已开时加深；禁止平行评价引擎 |
| 双选接受/婉拒/志愿序 | `mutual_select` + `TicketDeriveOps` / PeerTickets | 加深调剂留痕、改志愿、盲选等；禁止第二套互选状态机 |
| 客观题自动判分 | `ExamStore` 已有匹配 | 口径钉死 + 多选部分分；不重写判分引擎 |
| 问卷/投票/时银主路径 | `SurveyStore` / `VoteStore` / `TimebankStore` | 在既有表上加深；禁止平行问卷/投票产品 |
| 婚恋私信 | `dm` 域默认 | 不另起 IM；举报时限对齐 deadline |
| 名额/座位余量 | `quota` | 可视化进度条/余量；不另起库存域 |

---

## 1. 批次总表

> **状态列**：`待写` → `实现中` → `已齐`（须过 §0.5 三绿 + 地图迁行）。

| 序 | ID | 主题 | 条数约 | 主要落域 | 状态 |
|----|-----|------|--------|----------|------|
| 0 | **I-00** | 脚手架：`interact_thicken` + `domain_schema` + `HUB_BYPASS` + `test_interact_thicken_features` + 本册 | — | 工厂 | **待写** |
| 1 | **I-01** | 半截钉齐：favorites 心动 / allowRating 评价入口 / mutual 截止倒计时 / 客观题判分口径 | ~6 | 跨域 | **待写** |
| 2 | **I-02** | DATING：完整度 / 互关 / 见面意向 / 举报时限 / 审驳理由 / 条件筛选 / 黑名单 / 相册审 / 活动入口叠 | ~10 | DATING | **待写** |
| 3 | **I-03** | MUTUAL 通识：调剂留痕 / 截止前改志愿 / 附件包 / 盲选 / 志愿互斥 / 公示页 / 调剂上限 / 确认超时婉拒 / 锁定倒计时 / 结果导出信 / 面试叠文案 | ~11 | MUTUAL-* | **待写** |
| 4 | **I-04** | MUTUAL 域皮：名额进度条；组队技能标签/邀请信/满员关招募/附言必填/退出须同意/匹配度计数；导师学生互评 | ~8 | TUTOR·TEAM | **待写** |
| 5 | **I-05** | CARPOOL：满员关行程 / 出发提醒 / 分摊备注 / 评价 / 座位余量 / 性别人数偏好 / 途经点 / 取消惩罚 / 锁座 / 校区字典 / AA 算 / 行李 / 电话脱敏 / 重复发布检测 | ~14 | CARPOOL | **待写** |
| 6 | **I-06** | TIMEBANK：时长榜 / 评价 / 兑换导出 / 技能认证勾选 / 兑换目录 / 信用分 / 发布须审 / 时长冻结 / 证明附件 / 申诉单 / 转让 / 清零说明 / 星级叠 | ~13 | TIMEBANK | **待写** |
| 7 | **I-07** | EXAM 作答与规则：练习模式 / 防切屏 / 解析开关 / 乱序 / 进度条 / 及格线 / 多选部分分 / 交卷不可改 / 迟到禁入 / 监考口令 | ~10 | EXAM | **待写** |
| 8 | **I-08** | EXAM 题库与成绩：及格证书页 / 错题本导出 / 题目导入 / 多卷抽题 / 主观评分细则 / 成绩导入 / 难度标签 | ~7 | EXAM | **待写** |
| 9 | **I-09** | SURVEY：开放截止上下架 / 匿名 / 跳题 / 进度条叠 / 限填一次 / 必答 / 矩阵题 / 结果图表 / 截止提醒 / 草稿 / 显隐 / 投放组织 / 感谢页 / 回收率卡片 | ~13 | SURVEY | **待写** |
| 10 | **I-10** | VOTE：结果导出 / IP 提示 / 十佳海报 / 图文简介 / 票数轮询 / 每日限票 / 匿名 / 延迟公布 / 拉票文案 / 实名可投 / 弃权 / 实时榜前三 | ~12 | VOTE | **待写** |
| 11 | **I-11** | 能力岛加深（仅 cap 已挂）：favorites / allowRating / dm / content_report / deadline 等表内未尽项 | 余量 | 扫词 | **待写** |
| 12 | **I-12** | 扫尾：对照地图「本组待补」清零；不支持段只留边界；批次改已收口档案 | 余量 | 全组 | **待写** |

**推荐编码顺序**：I-00 → I-01 → I-02 → I-03 → I-04 → I-05 → I-06 → I-07 → I-08 → I-09 → I-10 → I-11 → I-12。

可并行（不同 Store 触点、互不改同一状态机时）：I-07∥I-09；I-05∥I-06；I-02∥I-10。

---

## 2. 分批明细

### I-00 脚手架

| 勾选 | 项 |
|------|-----|
| ☐ | 新建 `backend/app/bake/features/interact_thicken.py`（`INTERACT_DOMAINS`、硬约束注释、`apply_interact_thicken_to_spec`） |
| ☐ | `domain_schema.py` 注册（紧接 `content_thicken` 之后） |
| ☐ | `engine_sql.py` 挂 `ensure_interact_thicken_sql`（若本批尚无列可空实现） |
| ☐ | `HUB_BYPASS_MODULES` + `docs/capabilities.md` Hub 例外表登记 |
| ☐ | `backend/tests/test_interact_thicken_features.py`：只动九互动域、不碰内容/交易/预约语义 |
| ☐ | 地图 §1.9 增加「本组本轮已齐」空表头；changelog 记 I-00 立项 |
| ☐ | `.cursor/rules/opening-group-delivery.mdc`「已有」列表补 `interact_thicken`（实现落地后） |

**验收**：pytest 绿；尚不迁待补行。

---

### I-01 半截钉齐（跨域）

| 地图待补 | 落点建议 | 挂载 |
|----------|----------|------|
| 心动列表（收藏对方资料） | favorites + DATING 入口；labels | 扫词挂 favorites 或域默认钉读 |
| 拼车评价 | allowRating + CARPOOL | 扫词或域皮开评价时 |
| 时间银行服务评价 | allowRating + TIMEBANK | 同上 |
| 互选截止倒计时展示 | labels + PeerTickets / MyTickets UI | **域默认** MUTUAL-* |
| 客观题自动判分口径钉死 | ExamStore 判分契约 + 特征测 | **域默认** EXAM |
| 时间银行星级信誉 | allowRating 叠星级展示 | 扫词挂评价时 |

**验收**：三绿；迁行对应条；禁止新建平行收藏/评价/判分引擎。

---

### I-02 DATING

| 地图待补 | 落点建议 | 挂载 |
|----------|----------|------|
| 婚恋资料完整度提示 | profile 完整度条 + labels | **域默认** DATING |
| 婚恋互相关注/取消 | 关注浅表 + API 双端 | **域默认** DATING |
| 婚恋见面意向登记（非支付） | 轻单 ticket/archive 字段 | **域默认** DATING |
| 婚恋举报处理时限提醒 | deadline + 管理端提醒 | 扫词挂 content_report/deadline |
| 婚恋资料审核驳回理由 | 审驳字段 + 管理写/用户读 | **域默认** DATING |
| 婚恋理想对象条件筛选加深 | 筛选字段 + 列表 | **域默认** DATING |
| 婚恋黑名单 | 轻名单 Store | **域默认** DATING |
| 婚恋资料相册审核 | 附件审状态 | **域默认** DATING |
| 婚恋活动报名入口（叠活动） | 文案链到 ACTIVITY；不抢报名状态机 | 文案交叉 |

（心动列表若 I-01 已迁则本批跳过。）

---

### I-03 MUTUAL 通识

| 地图待补 | 落点建议 | 挂载 |
|----------|----------|------|
| 双选志愿调剂记录留痕列表 | 调剂日志表/列 + 管理列表 | **域默认** MUTUAL-* |
| 志愿提交后允许在截止前修改 | 规则开关 + apply 改写 | **域默认** MUTUAL-* |
| 双选导师/选题附件简介包 | 附件槽 | **域默认** MUTUAL-* |
| 双选盲选阶段（截止前互不可见） | 规则开关 + 列表脱敏 | **域默认** MUTUAL-* |
| 双选志愿互斥（同志愿不可双报） | apply 校验 | **域默认** MUTUAL-* |
| 双选结果公示页 | 只读名单页 | **域默认** MUTUAL-* |
| 双选调剂志愿上限 | 规则 + 校验 | **域默认** MUTUAL-* |
| 双选确认超时自动婉拒 | DemoScheduleJobs / 规则 | **域默认** MUTUAL-* |
| 双选学生端志愿锁定倒计时 | UI + 截止字段 | **域默认** MUTUAL-* |
| 双选结果导出通知信 | CSV + 站内信 | **域默认** MUTUAL-* |
| 双选面试时段预约叠 | 文案交叉 MEETING；不另起预约机 | 文案交叉 |

---

### I-04 MUTUAL 域皮（TUTOR / TEAM）

| 地图待补 | 落点建议 | 挂载 |
|----------|----------|------|
| 导师学生名额占用进度条 | quota 可视化 | **域默认** MUTUAL-TUTOR |
| 组队技能标签筛选 | 标签字段 + 筛 | **域默认** MUTUAL-TEAM |
| 组队邀请站内信 | MessageStore | **域默认** MUTUAL-TEAM |
| 组队满员自动关招募 | 状态规则 | **域默认** MUTUAL-TEAM |
| 组队申请附言必填 | 字段校验 | **域默认** MUTUAL-TEAM |
| 组队退出须队长同意 | 规则 | **域默认** MUTUAL-TEAM |
| 组队技能匹配度提示（计数重合） | 浅计数；≠协同过滤 | **域默认** MUTUAL-TEAM |
| 双选导师学生互评 | allowRating | 扫词或域皮 |

---

### I-05 CARPOOL

| 地图待补 | 落点建议 | 挂载 |
|----------|----------|------|
| 意向人数满自动关闭行程 | 状态规则 | **域默认** CARPOOL |
| 拼车出发前提醒站内信 | 消息模板 + 调度 | **域默认** CARPOOL |
| 拼车费用分摊备注（非支付） | 文案字段 | **域默认** CARPOOL |
| 拼车座位余量展示 | quota 可视化 | **域默认** CARPOOL |
| 拼车性别/人数偏好备注 | 文案字段 | **域默认** CARPOOL |
| 拼车途经点文本 | 多行；≠地图 | **域默认** CARPOOL |
| 拼车取消惩罚提示（爽约计数） | 规则 + 提示 | **域默认** CARPOOL |
| 拼车乘客确认后锁座 | 状态 | **域默认** CARPOOL |
| 拼车起点终点校区字典 | 字典 | **域默认** CARPOOL |
| 拼车费用 AA 计算器 | 前端算；≠支付 | **域默认** CARPOOL |
| 拼车行李件数备注 | 字段 | **域默认** CARPOOL |
| 拼车评价后不可见对方电话 | 脱敏规则 | **域默认** CARPOOL |
| 拼车行程重复发布检测 | 校验 | **域默认** CARPOOL |

（拼车评价若 I-01 已迁则跳过。）

---

### I-06 TIMEBANK

| 地图待补 | 落点建议 | 挂载 |
|----------|----------|------|
| 时间银行时长排行榜 | 只读榜 API + 页 | **域默认** TIMEBANK |
| 兑换记录对账导出 | CSV | **域默认** TIMEBANK |
| 时间银行技能标签认证勾选 | 资料字段 | **域默认** TIMEBANK |
| 时间银行兑换商品目录 | 浅兑换表；≠商城 | **域默认** TIMEBANK |
| 时间银行信用分（爽约扣分） | 浅分；≠征信 | **域默认** TIMEBANK |
| 时间银行发布须审 | 状态机 | **域默认** TIMEBANK |
| 时间银行时长冻结（纠纷） | 状态 | **域默认** TIMEBANK |
| 时间银行技能证明附件 | requireAttach | **域默认** TIMEBANK |
| 时间银行申诉单 | 轻单 | **域默认** TIMEBANK |
| 时间银行时长转让 | 流水；≠货币 | **域默认** TIMEBANK |
| 时间银行时长清零规则说明 | 文案 | **域默认** TIMEBANK |

（服务评价 / 星级若 I-01 已迁则跳过。）

---

### I-07 EXAM 作答与规则

| 地图待补 | 落点建议 | 挂载 |
|----------|----------|------|
| 练习模式不计分 / 不计次数 | schema 开关 | **域默认** EXAM |
| 考试防切屏提示（文案+失焦计数） | FE 计数 + 可选落库；≠锁屏 SDK | **域默认** EXAM |
| 成绩公布后可看解析开关 | schema | **域默认** EXAM |
| 试卷题目/选项乱序 | 组卷/作答侧浅乱序 | **域默认** EXAM |
| 交卷前答题进度条 | UI（SURVEY 叠见 I-09） | **域默认** EXAM |
| 考试及格线可配 | schema | **域默认** EXAM |
| 多选题部分得分规则 | schema | **域默认** EXAM |
| 考试交卷后不可修改开关 | schema | **域默认** EXAM |
| 考试迟到禁止进入（开考后 N 分） | 规则 | **域默认** EXAM |
| 考试监考口令（入场码） | 字符串；≠人脸 | **域默认** EXAM |

---

### I-08 EXAM 题库与成绩

| 地图待补 | 落点建议 | 挂载 |
|----------|----------|------|
| 考试及格证书页（固定模板 PDF） | 打印/PDF 壳；≠ CA | **域默认** EXAM |
| 错题本导出 | CSV | **域默认** EXAM |
| 考试题目导入 Word/Excel | 导入加深 | **域默认** EXAM |
| 考试多卷随机抽题 | 组卷加深 | **域默认** EXAM |
| 考试主观题评分细则字段 | 阅卷备注 | **域默认** EXAM |
| 考试成绩导入模板 | 导入 | **域默认** EXAM |
| 考试试卷难度标签 | 字段 | **域默认** EXAM |

（客观题判分若 I-01 已迁则跳过。）

---

### I-09 SURVEY

| 地图待补 | 落点建议 | 挂载 |
|----------|----------|------|
| 问卷开放/截止自动上下架 | 日期 + 调度 | **域默认** SURVEY |
| 问卷匿名填写开关 | schema | **域默认** SURVEY |
| 问卷逻辑跳题（简单若选 A 则跳） | 浅规则；≠全功能引擎 | **域默认** SURVEY |
| 交卷前答题进度条 | UI 叠 | **域默认** SURVEY |
| 问卷每人限填一次 | 规则 | **域默认** SURVEY |
| 问卷必答题标记与校验 | 通识 | **域默认** SURVEY |
| 问卷矩阵题（简单表格题） | 题型加深 | **域默认** SURVEY |
| 问卷结果图表（柱/饼） | ECharts | **域默认** SURVEY |
| 问卷截止前提醒站内信 | 消息 | **域默认** SURVEY |
| 问卷填写进度保存草稿 | 草稿写库 | **域默认** SURVEY |
| 问卷逻辑显示（显隐，非跳题） | 浅规则 | **域默认** SURVEY |
| 问卷投放对象按组织 | 组织过滤 | **域默认** SURVEY |
| 问卷填写后感谢页 | 静态页 | **域默认** SURVEY |
| 问卷回收率工作台卡片 | 计数 | **域默认** SURVEY |

---

### I-10 VOTE

| 地图待补 | 落点建议 | 挂载 |
|----------|----------|------|
| 投票结果导出 | CSV | **域默认** VOTE |
| 投票防刷：同 IP 提示（仅提示） | 浅提示；≠风控中台 | **域默认** VOTE |
| 十佳结果海报页（静态生成） | 结果页美化 | **域默认** VOTE |
| 投票候选人图文简介 | 档案字段 | **域默认** VOTE |
| 投票票数定时刷新（轮询） | FE 轮询；≠ WebSocket | **域默认** VOTE |
| 投票每人每天限票 | 规则 | **域默认** VOTE |
| 投票匿名开关 | schema | **域默认** VOTE |
| 投票结果对学生延迟公布 | 日期开关 | **域默认** VOTE |
| 投票候选人拉票文案字段 | 字段 | **域默认** VOTE |
| 投票禁刷：实名后可投 | 对照实名勾选 | **域默认** VOTE |
| 投票弃权选项 | 选项 | **域默认** VOTE |
| 投票实时榜置顶前三 | UI | **域默认** VOTE |

---

### I-11 能力岛加深（仅 cap 已挂）

| 依赖 cap / 开关 | 地图待补 | 落点 |
|-----------------|----------|------|
| `favorites` | 心动列表未尽 / 收藏变体 | FavoriteStore 双端 |
| `allowRating` | 各域评价未尽 | 评价写库 + 管理可见 |
| `dm` | 私信相关加深（若表内仍有） | DmStore；禁止 SDK |
| `content_report` + `deadline` | 婚恋举报时限等 | 管理提醒 |
| 其它扫词 cap | 表内余量 | 禁止域默认硬挂 |

**禁止**：未扫词挂 cap 时域默认硬开积分/钱包类邻组岛。

---

### I-12 扫尾（收口）

| 勾选 | 项 |
|------|-----|
| ☐ | §1.9「本组待补」实现债清零（不支持项不进待补） |
| ☐ | 不支持段只留边界（协同过滤 / 真地图 / 人脸监考 / 实时 IM / 刷票中台） |
| ☐ | 地图 changelog 有 I-00～I-12 收口行 |
| ☐ | 本册总表全部 **已齐**；文首改为「已收口档案」 |
| ☐ | `delivery-audit-rules.md` 互动行改为已收口 |
| ☐ | AOCI maintain（新文件先 acknowledge） |

---

## 3. 修订

| 日期 | 说明 |
|------|------|
| 2026-10-10 | 批次立项：I-00～I-12；对齐 §1.6/§1.7/§1.8 工序；待补约 100 条（剔 2 条不支持）；尚未迁行 |
