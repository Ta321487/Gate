---
description: 清待补交付：一轮一组 · 一条四件套 · 三骨架同绑 · 八张材料可见 · 门禁三绿才迁行
globs: docs/opening-feature-delivery-map.md, backend/app/bake/**, backend/tests/**, skeletons/**
alwaysApply: false
---

# 清待补交付（开题密功能地图）

地图：`docs/opening-feature-delivery-map.md`。

> **适用范围（后加厚）**：本文纪律原服务于域组 `*_thicken`（§1.1～§1.9）。**九组加厚已收口**，禁止再开新 `*_thicken` / `generic_thicken`。  
> - **§0 通识横切** → [`docs/crosscut-delivery-batch.md`](../../docs/crosscut-delivery-batch.md)（一轮一簇；四件套 / 三骨架 / 门禁仍适用，模块落点是基线而非 thicken）。  
> - **§1.10 导引** → 已浅清（`cross_path_guide`）；勿再套本组工序开 thicken。  
> - **域组 UI 表面** → [`docs/domain-group-ui-styles.md`](../../docs/domain-group-ui-styles.md)，一组一独立 plan。  
> 下文「一轮一组 / thicken 注册」保留作**已收口档案的维护与回归**口径，不是下一主线开工令。

## 一轮 = 一组（历史域组加厚）

- 组 = 地图 `### 1.x`（§1.1~§1.9）；一组一个 `backend/app/bake/features/<组>_thicken.py`。
  已有（均已收口）：`borrow_thicken` · `follow_thicken` · `repair_thicken` · `apply_thicken` · `approve_thicken` · `trade_thicken` · `reserve_thicken` · `content_thicken` · `interact_thicken`（均须在 `HUB_BYPASS_MODULES` + `docs/capabilities.md` 例外表登记）。
- **禁止**再新建 thicken 模块。若维护既有模块：须在 `backend/app/bake/domain_schema.py` 保持注册：`from app.bake.features.<组>_thicken import apply_<组>_thicken_to_spec` + `out = apply_<组>_thicken_to_spec(out, body)`。**漏注册 = 死代码。**
- 一组清完：同节「#### 本组待补」清空，行迁到「#### 本组本轮已齐（从待补迁出 · 双端闭环 · 骨架门禁）」，列保持 `功能 / 落点 / 挂载`。

## 一条待补 = 四件套（缺一不算已齐）

| 件 | 真源 |
|----|------|
| ① 表 / 列 | `skeletons/baseline/sql/schema.sql` |
| ② Store 写方法 | `skeletons/baseline/backend/src/main/java/com/thesis/capability/TicketStore.java`（或同目录 `*Store.java`、`service/*Store.java`） |
| ③ API | `skeletons/baseline/backend/src/main/java/com/thesis/controller/TicketController.java`（或对应 `*Controller.java`） |
| ④ 前端控件 | `skeletons/baseline/frontend/src/views/`（`user/`、`admin/`、`staff/`、`special/`）或 `frontend/src/components/` |

硬口径：**管理端能管 + 用户端能产生数据（真写库）**。
纯 Hint / 只读展示 / 打印页 / 前端零读取的字面量 → 只能留在「待补」。

## 菜单一上必须跟有效路由（禁止只挂 key）

新菜单 / 新页面入口算交付的一部分，**同一提交**对齐三处，缺一不算已齐：

| 处 | 真源 |
|----|------|
| 菜单 key → path | `skeletons/baseline/frontend/src/utils/menuRoutes.js` + `backend/app/bake/menu_routes.py`（`USER_MENU_PATHS` / `ADMIN_MENU_PATHS`） |
| 前端真挂路由 | `skeletons/baseline/frontend/src/router/index.js`（壳内写死或 `with*Routes`） |
| bake 有效路径 | `backend/app/bake/menu_routes.py` 的 `effective_paths()`（壳集合或能力/schema 分支，与上一行同一条件） |

只写菜单 + Vue、不改 `effective_paths` → 真 bake 会「菜单/路由未对齐」红灯；单元测读骨架源码绿、探针/出包红。迁地图前必跑：`python -m pytest backend/tests/test_menu_routes.py -q`。

## 三骨架同一批（禁止只改一套）

| 骨架 | 绑定处 |
|------|--------|
| baseline | `skeletons/baseline/backend/src/main/java/com/thesis/config/DomainRuntimeBinder.java` |
| persistence-mybatis | `skeletons/overlays/persistence-mybatis/backend/src/main/java/com/thesis/config/DomainRuntimeBinder.java` |
| persistence-jpa | `skeletons/overlays/persistence-jpa/backend/src/main/java/com/thesis/config/DomainRuntimeBinder.java` |

新列 / 新写方法 / 新开关：三份骨架同改、三处 `DomainRuntimeBinder` 同绑，overlay 的 `capability/TicketStore.java` 也各有自己一份。
**少一套 = 该栈静默关功能**；三套齐才进「已齐」。

## 八张材料可见性（一组同看）

| 材料 | bake 真源（`backend/app/bake/schema/`） | 卡片 id（`frontend/src/views/projectDetail/ArtifactsTab.vue`） | 测试（`backend/tests/`） |
|------|------|------|------|
| 功能模块图 | `modules.py` | `modules` | `test_schema_modules.py` |
| 系统逻辑架构图 | `architecture.py` | `architecture` | `test_schema_architecture.py` |
| 系统类图 | `classes.py` | `classes` | `test_schema_classes.py` |
| 系统序列图 | `sequence.py` | `sequences` | `test_schema_sequence.py` |
| 系统活动图 | `activity.py` | `activities` | `test_schema_activity.py` |
| 用例图 | `usecases.py` | `usecases` | `test_schema_usecases.py` |
| 用例描述表 | `usecase_descriptions.py` | `usecase-desc` | `test_schema_usecase_descriptions.py` |
| 软件测试用例 | `testcases.py` | `testcases` | `test_schema_testcases.py` |

材料只能从**交付菜单 / 角色 / 实体**推导（`testcases.py` 原话）；菜单外功能不许进图。
本轮动的功能，八张里受影响的要一起看，不受影响在汇报里写「无」。

## 两组归并（别一组一个文件）

- **域默认必开**：该组所有域都该有的底（如 CRM 跟进时间轴）→ 挂 `DOMAIN_CAPABILITIES`（`backend/app/bake/domains.py`），地图「挂载」列写 `**域默认**`。
- **开题扫词才开**：命中开题正文才挂（评价 / 售后 / 多商家入驻等）→ 落 `backend/app/bake/features/opening_align.py` 规则表；地图「挂载」列写「扫词开」。
- 超纲项不进待补：进「不支持」并写原因（如 CRM 公海池 / 外呼中心、ATTEND 人脸 GPS 打卡）。

## 收尾：四绿才准迁行

1. `python -m pytest backend/tests/test_opening_map_skeleton_gate.py -q`（地图 ↔ 骨架：已齐 `labels.*` 必须被 baseline 前端真读、§1.3 报修硬点控件存在）
2. 本组特征：`backend/tests/test_<组>_thicken_features.py`（现有 `test_borrow_thicken_features.py` · `test_follow_thicken_features.py` · `test_repair_thicken_features.py`）
3. 受影响材料的 `backend/tests/test_schema_*.py`
4. `python -m pytest backend/tests/test_menu_routes.py -q`（菜单 key ↔ `effective_paths` ↔ 前端 `with*Routes`；本轮新菜单必过）

任一红 → 行留在「本组待补」，**不许先迁行**，不许靠改地图文字变绿。

### 动了 Java 骨架再加跑（真编，本机要有 mvn）

工厂出包页**不用开关**——`build_verify` 已自动 `mvn compile`。下面是给加厚/改骨架的开发验收，避免靠随机起包才撞 javac 红：

```text
python -m pytest backend/tests/test_skeleton_java_compile_smells.py backend/tests/test_runtime_policy_bake.py backend/tests/test_skeleton_unreachable_catch.py -q
python -m pytest backend/tests/test_skeleton_mvn_compile.py backend/tests/test_bake_mvn_compile_probe.py -q -m slow
```

默认全量 pytest 会跳过 `slow`；`-m slow` / `--run-slow` 才真编。无 mvn 时 slow 用例 skip 不红；有 mvn 则 **baseline 骨架真编** + **一条 DOM-ATTEND jdbc bake 探针**必须编过。mybatis/jpa overlay 不是完整工程、叠层洁净另案，不绑进本 slow 门禁。

## DON'T

- 一轮清多组 / 一次起多个包；只改地图不改骨架。
- 只改 baseline 或只改一套 Store（另两套漏绑 = 静默关功能）。
- 把只读页 / Hint / 打印当已齐（门禁会红）。
- 菜单 / `with*Routes` 加了、`menu_routes.effective_paths` 不跟（骨架测绿、真 bake 红）。
- 起包发给学生 —— **起包由人执行**，本规则只管交付齐度。

## 汇报（一组一段）

- 组：§1.x 名称；本轮清了 N 条，迁行 N。
- 四件套：①表/列 ②Store ③API ④前端控件 各自的真实文件路径。
- 菜单路由：新 key 是否已进 `menuRoutes.js` + `USER/ADMIN_MENU_PATHS` + `effective_paths`（与 `with*Routes` 同条件）。
- 三骨架：baseline / mybatis / jpa 各改了哪些文件（含 `DomainRuntimeBinder.java` 与 `TicketStore.java`）。
- 材料：八张里哪几张受影响，未受影响写「无」。
- 门禁：上面四条命令与结果。

