# 全厂硬约束与不变式

> **本文只负责**：库表预算（舒适区 6–15 / 硬顶 18）、学生端持久化、总管/子管/员工管理页槽位。
> **交接**：[HANDOFF.md](../HANDOFF.md) · **总览**：[README.md](../README.md) · **索引**：[README.md](./README.md)

---

## 硬约束：库表数量（舒适区 6~15，硬顶 18）

- 常量：`backend/app/bake/engine.py`（再导出；定义在 `engine_sql.py`）→ `TABLE_COUNT_MIN` / `TABLE_COUNT_MAX`（舒适区上沿）/ `TABLE_COUNT_HARD`（硬顶）。含 L0 平台表 `sys_message`。**借用/占用族**另有 `BORROW_TABLE_MIN = 10`（`table_budget_floor`），其他族仍 6。
- **判定**：低于下限打回；**超过 15 警告**（仍可出包）；**计费张数超过 18 打回**。计费 = 总表数 − 开题扫入（非域默认）的选题必需业务表（`ESSENTIAL_CAP_TABLES`）。
- **现状样板**：GENERIC CRUD 6 / FLOW·RESERVE 7 / TRADE（含 guestbook）约 8～9 · SHOP/FOOD（guestbook+favorites）约 **12** · 借用/占用族出包后 **10～15** · 图书/报修壳 9 · 论坛约 13 · 能力叠加可到 16～18（警告）
- DDL/种子：具名域 `backend/app/bake/sql/templates/DOM-*.sql`（`domain_templates.py` 加载）；GENERIC 壳仍为 `sql/DOM-GENERIC*.sql`（`domain_sql` / `compose`）
- bake 写 `schema.sql` 前 `assert_table_budget`；门禁 `p3t` 硬失败则禁 ZIP（`warn` 不拦）
- 论坛含：`sys_message` + 原业务/平台表
- 报修薄壳：楼栋/房间/类型/单据/进度/附件 + 用户/公告/消息
- 论文 **E-R** 按交付 SQL 如实画（优先全环 / 内点直线零交叉，必要时环外折线；实现拆为 `schema/er_model.py` / `er_labels.py`+`er_zh.py` / `er_svg.py`）；**功能模块图** 按交付 menus 如实画（开题只辅助中文命名；**按身份**亦过滤未交付模块，禁止图上有、包里无）；默认 **按身份拆**，工厂可切换 **按业务拆**；**系统类图** 按交付 `sql/schema.sql` 表/外键 + bake 包 Java（*Store 行映射与方法签名，可见性 +/#/-）如实画三栏 UML；外键推关联·聚合·组合，extends/implements 推继承·实现，类型引用推依赖；默认 `sample` 精简真实方法且禁止无代码填空，可切 `full`（含 private-）；**自动排版零交叉必须**（竞赛 + 挪框开槽；少画边可拖开后重算补回）；**人工拖拽**：松手存坐标并回拉重选折线、不挪其它框；实现 `schema/class_model.py` + `class_layout.py` + `class_svg.py` + `class_code.py`（`classes.py` 门面））；**论文图打开**：GET model 一次带 `svg`（禁止前端连打 model+svg）；bake 后预热默认视图落 `islands/diagram_cache`（按参缓存，变参才重算；日志含 model/layout/svg/total 四段耗时）；**系统序列图** 固定 3 张核心功能（可从交付 menus 勾选），四槽位（交付角色 / 页面 / 控制器 / 数据库）、生命线与分段变长激活条、往库实线带 () / 往角色虚线无 ()、阶梯序号；角色与消息文案取自 bake，禁止模板套话（实现 `schema/sequence.py`）；**系统活动图** 固定 3 张（候选/勾选 id 与序列图同源），三泳道（用户 / 系统 / 数据库），开始实心点 · 圆角动词任务 · 菱形判断（框内无字，是/否写在出边旁）· 结束实心点外套圆；流程与同 ids 序列图一致，文案取自 bake（实现 `schema/activity.py`）；**用例描述表** 按交付 menus + 开题正文选用默认 4 个主路径（事件流对照实包菜单操作，禁止发明未交付功能；实现 `schema/usecase_descriptions.py`）；**软件测试用例表** 按交付 menus/roles 推导（5～9 列可选，默认 6），可选 LLM 只润色已有行文案，不增删用例、不发明功能

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
