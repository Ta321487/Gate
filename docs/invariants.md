# 全厂硬约束与不变式

> **本文只负责**：库表预算（舒适区 6–15 / 硬顶 18）、学生端持久化、总管/子管/员工管理页槽位。
> **交接**：[HANDOFF.md](../HANDOFF.md) · **总览**：[README.md](../README.md) · **索引**：[README.md](./README.md)

---

## 硬约束：库表数量（舒适区 6~15，硬顶 18）

- 常量：`backend/app/bake/engine.py`（再导出；定义在 `engine_sql.py`）→ `TABLE_COUNT_MIN` / `TABLE_COUNT_MAX`（舒适区上沿）/ `TABLE_COUNT_HARD`（硬顶）。含 L0 平台表 `sys_message`。**借用/占用族**另有 `BORROW_TABLE_MIN = 10`（`table_budget_floor`），其他族仍 6。
- **判定**：低于下限打回；**超过 15 警告**（仍可出包）；**计费张数超过 18 打回**。计费 = 总表数 − 开题扫入（非域默认）选题必需业务表（`ESSENTIAL_CAP_TABLES`）− 通识横切平台表（`PLATFORM_HARD_EXEMPT_TABLES`：会话/登录日志/邀请码/注销/公告确认/轮播/站点统计）。业务岛表仍随开题保留，不与平台壳抢硬顶。
- **现状样板**：GENERIC CRUD 6 / FLOW·RESERVE 7 / TRADE（含 guestbook）约 8～9 · SHOP/FOOD（guestbook+favorites）约 **12** · 借用/占用族出包后 **10～15** · 图书/报修壳 9 · 论坛约 13 · 能力叠加可到 16～18（警告）
- DDL/种子：具名域 `backend/app/bake/sql/templates/DOM-*.sql`（`domain_templates.py` 加载）；GENERIC 壳仍为 `sql/DOM-GENERIC*.sql`（`domain_sql` / `compose`）
- bake 写 `schema.sql` 前 `assert_schema_nf` + `assert_table_budget`；门禁 `p3n`/`p3t` 硬失败则禁 ZIP（表预算 `warn` 不拦）

## 硬约束：3NF 口径（禁止 JSON 当业务规则）

- 实现：`backend/app/bake/gates/schema_nf.py`；ZIP 评测键 `p3n`。
- **一对多**走子表外键（报销/行程/随行/评分维度/试题选项/设备关联）；禁止 `*_json` 列或逗号串装名单、规则、明细。
- **白名单**（不当闸口）：`sys_user.profile_json`（仅资料扩展）、`archive_log.payload_json`（快照）、`gallery_json` / `post_gallery_json`（媒体 URL 袋）。
- 禁言截止用 `sys_user.post_mute_until`，禁止写入 `profile_json`。
- 新 bake 禁止 `detail_json`；骨架不得 `ADD COLUMN` 非白名单 JSON。
- 3NF 拆出的子表计入 `ESSENTIAL_CAP_TABLES` / 计费豁免，不与硬顶 18 对打。
- 论坛含：`sys_message` + 原业务/平台表
- 报修最小表集（架构薄壳，≠密功能未加厚）：楼栋/房间/类型/单据/进度/附件 + 用户/公告/消息；§1.3 加厚见地图
- 论文 **E-R** 按交付 SQL 如实画（初局 **pyelk layered 分层**，**禁止全环默认**；实现拆为 schema/er_model.py / er_labels.py+er_zh.py / er_svg.py + layout_elk.py）；打开走 GET /schema/er 一次带 svg（按 mode/entity 缓存；bake 预热总图+各概念实体属性图）；总图为概念实体+联系（纯 M:N 中间表塌成 N:M 菱形，不进属性图清单）；分图=实体属性图（仅自身列、无外键）；人工拖过的图存整张 SVG（er_view），指纹一致则盖过自动排版、不重跑布局；**功能模块图** 按交付 menus 如实画（开题只辅助中文命名；**按身份**亦过滤未交付模块，禁止图上有、包里无；丢掉项进 ``delivery_gap`` **弱提醒施工清单**，不红 label_gate、不挡导出）；默认 **按身份拆**，工厂可切换 **按业务拆**；**系统类图** 按交付 sql/schema.sql 表/外键 + bake 包 Java（*Store 行映射与方法签名，可见性 +/#/-）如实画三栏 UML；外键推关联·聚合·组合，extends/implements 推继承·实现，类型引用推依赖；默认 sample 精简真实方法且禁止无代码填空，可切 ull（含 private-）；**初局排版**用 pyelk layered（不保证零交叉；尽量画全边）；**人工拖拽**：松手存坐标，只重算折线、**不挪其它框、不重跑 ELK**；实现 schema/class_model.py + class_layout.py + class_svg.py + class_code.py + layout_elk.py（classes.py 门面））；**论文图打开**：GET model 一次带 svg（禁止前端连打 model+svg）；bake 后预热默认视图落 islands/diagram_cache（按参缓存，变参才重算；日志含 model/layout/svg/total 四段耗时）；**系统序列图** 固定 3 张核心功能（可从交付 menus 勾选），四槽位（交付角色 / 页面 / 控制器 / 数据库）、生命线与分段变长激活条、往库实线带 () / 往角色虚线无 ()、阶梯序号；角色与消息文案取自 bake，禁止模板套话（实现 `schema/sequence.py`）；**系统活动图** 固定 3 张（候选/勾选 id 与序列图同源），三泳道（用户 / 控制器 / 数据库，键仍 user/system/db，与序列图四槽位同名），开始实心点 · 圆角动词任务 · 菱形判断（框内无字，是/否写在出边旁）· 结束实心点外套圆；**标签几何**（`audit_activity_labels` / `audit_activity_edges` 门禁，rubric warn + golden 全量 0 findings）：是/否 贴菱形**出边起点**（竖边写右侧、横边写上方，放不下自动换侧），**不得挂整条边中点**；判断条件贴菱形**入射处**（优先上角外侧，被折线占位退右侧）；标签一律夹在所属泳道内、不压任何连线；否回边折点按**目标**泳道算（禁止用源泳道左边距，否则横段穿目标节点框）；任务框（含长文案自适应加宽后）不得跨泳道分隔线（`audit_activity_nodes`）；流程与同 ids 序列图一致，文案取自 bake（实现 `schema/activity.py`）；**用例描述表** 按交付 menus + 开题正文选用默认 4 个主路径（事件流对照实包菜单操作，禁止发明未交付功能；实现 `schema/usecase_descriptions.py`）；**软件测试用例表** 按交付 menus/roles 推导（5～9 列可选，默认 6），可选 LLM 只润色已有行文案，不增删用例、不发明功能
- **材料手调（Overrides）**：展示层短签/勾选/图面隐藏走元库 `project_overrides` + `islands/overrides.json`；重 bake 经 islands 白名单 stash/restore 后按稳定键重放（见 [`pack-overrides.md`](./pack-overrides.md)）；禁止扫盘改 `.vue`、禁止用 Overrides 关能力岛；撞闸仍走现网文案红，不另起手调闸。
- **论文图业务动词单一真源**：图内业务动词只许来自材料 `entities.<实体>.verbs`（优先）或工厂表 `factory_diagram_verb`（具名域 → `*` 兜底），渲染器不得自带业务句。句式形状在 `asset_seeds/diagram_flow.json`（kind → 实体/动作/前后状态），拼句在 `services/diagram_verbs.material_phases`：`选择{状态}{实体} → {动词} → 发起{动词} → 更新{实体}为{状态} → {动词}成功`。材料缺词时只出**中性骨架**（`查看{实体}` / `提交变更` / `更新{实体}状态`）并由 `material_gaps` → `rubric_gate` warn 报“材料缺词”，出口指资产台「实体动作词」（`/diagram-verbs`），**不得借别域业务句**。启动时 `main.py` 与 titles 一样 `migrate_seed_if_empty`；内存缓存空亦回退种子（对齐 `diagram_titles`）。序列图 `_KIND_WRITE_PHASES` 业务句库已删除，`_flow_spec` 仍为用例描述表遗留（待改占位）。
- **论文图三档导出**：PNG/SVG · Mermaid · Draw.io 必须同源自叠 Overrides 后的同一 `pack_*` model（见 [`thesis-diagram-export.md`](./thesis-diagram-export.md)）；结构 ⊆ 实包可测；**老师 rubric** 挂 `rubric_gate`（`diagram_rubric.py`），error 禁可交导出；导出可交 ≠ 厂内几何已齐（parked **m** / D1 几何债另账，不关单）。
- **论文图字体与图注（全图统一，禁止各图各字体）**：font-family 一律取自 `schema/diagram_style.py` —— `FONT_CN`（`SimSun, Songti SC, Times New Roman, serif`，中文宋体打头，对齐往届样例）用于所有中文图内文字；`FONT_TECH` 给纯西文/基数标注；类图属性/方法行保留 `FONT_MONO` 等宽。**图内不画标题**（序列图/活动图原先在画布上写 figure_title，已去掉）：标题只做图注，写 Word（形如「图 4.9 用户订餐活动图」），前端标题栏仍显示 `figure_title`。活动图任务框按文案自适应宽度、三条泳道随之统一加宽（不再靠 12/10 号缩字硬塞）。改字体/标题/几何后必须 bump `diagram_cache._CACHE_VER`，否则页面读旧 SVG。

- **论文图几何口径（对齐往届样例，2026-11 起）**：改这些常量必须同步 bump `diagram_cache._CACHE_VER`。
  - **活动图**（`schema/activity.py`）：箭头实心三角 `M0,0 L10,4.5 L0,9 Z`；判定菱形扁化 `_DEC_W=52/_DEC_H=26`；相邻同文案同泳道动作合并。
  - **序列图**（`schema/sequence.py`）：序号 `1.正文`；不画自消息（页面确认改 actor→page）；火柴人在角色框**正上方**。
  - **架构图**（`schema/architecture.py`）：箭头黑色实心；层名「页面 / Spring Boot / 发送请求」；业务角色加粗、技术层名常规；四层不等宽（`_LAYER_W_SCALE`）。
  - **E-R**（`schema/er_svg.py`）：`_grid_layout` 蛇形栅格（列宽 `2*实体宽+210`、行高 `2*ENTITY_HH+140`）+ `_route_ortho` 七型正交路由（A 直连 / B 竖空档 / C 横空档 / D 五段绕行 / E 竖出竖入 / F·F2 外侧横母线 / G 外侧竖母线）；菱形沿空档落位并与实体框留 10px 净距（`_diamond_free(..., boxes)`，撞已放菱形按软惩罚处理）；候选打分 `hits*20 + cross*60 + 段长*0.02 + 菱形贴挤*70`；布完线做两级收敛（逐条重选折线 → 交叉两端实体互换坐标，均只接受交叉数下降）+ 6 档留白缩放择优；`1/n` 基数标签走 `_place_card` 不与框/菱形/标签相压；`er_check` 要求 `diamond_overlap=0`，`er_xcheck` 统计真线线交叉（潮汐 0 条）。
  - **类图**（`schema/class_layout.py`）：等宽栅格 + 通道正交路由 + 端点 fan 错位 + 同 from/to/kind 关系只画一根；人工拖拽走 B 方案——`snap_layout_to_slots` 让拖出的坐标只决定行/列顺序，坐标由生成器按槽位重算、间距大于聚类阈值保证吸附幂等，48 次模拟拖动合计 0 交叉；`islands/class_layout.json` 记 `source: manual|auto`，`manual` 永不因 `_CLASS_LAYOUT_VER` 变更作废、`auto` 版本不符才重排；`>=20` 边且栅格有交叉才退回 ELK。
  - **模块图**（`schema/modules.py`）：二/三级恒竖排窄框（`_presentation_tree` 强制 `orient="v"`），子节点多行均分（每行 ≤8）。
  - **用例图**（`schema/usecases.py`）：同名一级用例合并 include（`_dedupe_level1`）；一级 ≥4 且行数 >9 时双列（Actor 居中在底、二级朝外侧），`assert_usecase_invariants` 的竖线对齐按列数放宽为 1/2 条。
- **待定口径**：E-R 菱形兜底词「关联」尚未改成具体动词（样例为具体动词）；`er_labels.py` 的 `_rel_zh_from_via` 兜底仍返回「关联」，若要改须走材料 `verbs` / 新映射并同步 golden。

## 学生端持久化（已完成）

- `UserStore` / `NoticeStore` / `MessageStore` / `ArchiveStore`+`TicketStore` → MySQL + JdbcTemplate  
- 工厂 `student_db.ensure_student_schema` + `GF_STUDENT_MYSQL_*`  
- 种子在 `schema.sql` 幂等；重启不 Cle 业务数据  

---

## 全厂不变式：管理页 + 总管 / 子管理 / 业务员工

**任意领域**（含未来商城 / ERP / 预约）必须满足；缺一不可标 `full` / 出 ZIP。

| 槽位 | 谁可见 | 要求 | 示例 |
|------|--------|------|------|
| **领域主数据** | 仅总管 | ≥1 个 admin 菜单 + 真实主表 + CRUD Admin | 宿舍：楼栋/房间/类型；图书：图书/分类；商城：商品/分类 |
| **用户管理 / 任命** | 仅总管 | `users` + `requireSuperAdmin`；任命写入 `staff_post`+`staff_kind` | 学生 + 岗位（clerk/worker） |
| **公告管理** | 仅总管 | `content` + NoticesAdmin + `requireSuperAdmin` | 全域壳，文案随 schema |
| **留言管理** | 仅总管 | `guestbook` + GuestbookAdmin + `requireSuperAdmin` | 默认交易壳；开题写留言可扫入其它域 |
| **业务流（办理）** | 总管+子管理(clerk) | AdminLayout，菜单按 clerk packs 裁剪 | 报修受理、订单办理、预约办理 |
| **现场作业** | 业务员工(worker) | WorkLayout `/staff/*`，页面按 worker packs | 维修员/骑手/拣货/技师/客房服务等 **均开题写到才挂**（默认不空挂） |

岗位表：`backend/app/bake/staff_posts.py`（clerk / worker 均按域可选；无岗位 = 仅门户+总管；无 worker 则隐藏员工端入口）。
**显示名**：开题扫到的岗位/门户称呼原样进 `label`（`keyword_mentioned`，非新匹配旁路）；Island LLM 亦可原样填；`attach_staff_posts` 重绑保留已定文案。

**禁止**：用「用户+公告」顶替领域主数据；挂无表无路由的假菜单；bake 丢掉 `superAdmin` 门禁；子管理/员工互相任命。

| 角色 | 能做 | 不能做 |
|------|------|--------|
| 总管 `super_admin=1` | 主数据、用户、公告；也可看业务流 | — |
| 子管 `role=admin` 且非总管 | 该域业务流（工作台/受理/记录等） | 主数据写、用户管理、公告写 |

菜单 key 约定：主数据可用 `archive` / `category` / `lookup_site` / `lookup_type`；均标 `superOnly: true`。

---
