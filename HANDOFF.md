# 毕设港 · 交接

工作区：`d:\graduate_factory_v3`  
**禁止**参考 / 迁移 `d:\graduate_factory`、`d:\graduate_factory_v2`。

> **本文只负责**：新对话交接（主线、硬边界摘要、开场白）。  
> **产品总览 / 启动**：[README.md](./README.md) · **专题索引**：[docs/README.md](./docs/README.md)

---

## 当前主线

> **进行中 · 新人入职上手（波次 10）**（真源 [`docs/product-form-maturity.md`](./docs/product-form-maturity.md) §5.1.1）。  
> 对标：**最多两人用的正经产品**——拉仓起服、第一单、自然文案；不作坊腔、不装大厂工单腔。  
> 学生包大线与产品化 0～9 **已收口**；**D1 论文图**仍并行开（parked **m**），不与本波混关。

### 产品化执行波次（摘要）

| 波次 | 状态 |
|------|------|
| **0～4、6～9** | **已关**（见册 §5.1） |
| **5** 材料闭环 | **E 齐；D1 仍开**（parked m） |
| **7** 多操作者 | **默认不做** |
| **10** 上手 | **本会话实现关**（CX/ON0/S0～S3）；验收 [`docs/acceptance/newhire-onboarding-2026-11-09.md`](./docs/acceptance/newhire-onboarding-2026-11-09.md) |

**下一棒（单结续维护 · 按优先级）**：

| 优先 | 项 | 口令 / 入口 | 现状 |
|------|----|-------------|------|
| 1 | **词表待补消缺** | `做词表建议稿`：列名片段+同表已有词 → 确定性「建议中文」一键填；可选批草稿。**禁止** LLM 悬停猜名 | 侧栏/抽屉已齐；待补量仍靠人逐条 |
| 2 | **资产台落地** | `做资产台` / `做资产台 #n`（真源 [`docs/factory-asset-catalogs.md`](./docs/factory-asset-catalogs.md)；parked **q**） | **只立册**，工厂未改 |
| 3 | **D1 论文图几何** | parked **m**；模块/序列/活动厂内排版仍债 | 导出/rubric 已齐 ≠ 初开可读 |
| 4 | **旧题 canary** | `test_audit_group_canaries`：`DOM-ACTIVITY`→`DOM-CLUB` | 厂级红，非单题 |
| 5 | **AOCI 收尾** | 本批新路径（`zh_lexicon` / `system_zh_lexicon` / `schema_thesis_export` / `ZhLexicon.vue` / `LongOpWait` / `longOpSession` / `mdRender` 等）→ scope acknowledge → `aoci_maintain` | 推送后做；MCP 挂则停手重启 |

**本批提交主题**（2026-11-16 拆推）：文案口径 → 资产台册 → 词表+Stripe+主题色 → 论文图材料 → 等待态 I2 → 手调/对账 UX → 本交接。轨迹以 `git log` 为准。  
**勿提交**：根目录学生 `.docx`、`er-*.drawio` 草稿、`backend/` 下短随机名临时文件。

### 本会话（2026-11-16）· 学生可见文案口径（本域角色 · 修复全域）

- **站队**：**修工厂**（规则口径；非擦包）。
- **修**：`student-copy` 本域本端口吻 + **范围明示全域**（禁只修 SHOP/当面包）；资产台 §1.2 / parked **q** 同钉「口吻按域 ≠ 机制按域」；已 sync Trae。
- **提交**：本批主题 1。

### 本会话（2026-11-16）· 工厂可维护资产台（方向册 + parked q）

- **站队**：**修工厂**（只立册，不改 bake/UI）。
- **写**：[`docs/factory-asset-catalogs.md`](./docs/factory-asset-catalogs.md)——词表同构十二选项；#1～#3 细案；与 m/j/p/e 划界。
- **park**：碎另案 **q**；`docs/README.md` 已挂索引。
- **口令**：`做资产台` / `做资产台 #n`。
- **未改代码** · **提交**：本批主题 2 · **续**：工厂落地见上表优先 2。

### 本会话（2026-11-16）· 工厂词表维护（COMMENT）+ Stripe 结构 + 主题色

- **站队**：**修工厂**（列名英文；中文进 `factory_zh_lexicon` → bake `COMMENT`；全域全皮可维护）。
- **已有**：表/API/迁入 er_zh 一种子；bake `annotate_sql_comments`；图一保存回写 schema.sql COMMENT；侧栏「词表维护」。
- **2026-11-16**：去掉 `zh_lexicon._SHELL_COLUMN_SEED`，履约/售后壳列并入 `er_zh._COMMON_COL_ZH`；迁入补缺走全量种子。
- **本轮**：§3.5 Stripe；`ZhLexicon` R1～R7；顶栏**主题色**色板（港湾/潮汐/晴空/竹青/朱砂/岩灰，`localStorage` + Naive 主色联动）。
- **你这边**：硬刷新 → 顶栏色点切换；「词表维护」看抽屉锁定/中性占位；旧包需重 bake 才带 COMMENT。
- **提交**：本批主题 3 · **未做完**：待补消缺（上表优先 1）；不做 ❓+LLM 悬停。

### 本会话（2026-11-15）· 类图中文与多分类中间表

- **站队**：**修工厂**（共有：`StockNotify` 无中文；`product_category` 拆段撞成「健身用品分类」与 Category 双框）。
- **修**：`er_zh` 补 `stock_notify`/`product_category`；sample 藏 `product_category`（全量仍画「多分类关联」）。
- **测**：`test_schema_classes` **27 绿**。方木类图 cache 已清。
- **提交**：随本批「论文图材料」主题。硬刷新 → 类图 force/重开。

### 本会话（2026-11-15）· 方木交付审计（只报告）

- **对象**：`gf-20261026-233153` · `DOM-SHOP` · 方木健身用品电商。
- **结论**：**部分有**（主交易链齐；支付文案像真支付宝/微信；表 23 张超舒适区；类图项已跟修；`menus.subadmin` 空靠 `staffPackMenus`）。
- **旧题回归**：`test_audit_group_canaries` **1 红**（`DOM-ACTIVITY` 被匹配成 `DOM-CLUB`）——厂级，非本单独有。
- **未做浏览器扫**。

### 本会话（2026-11-15）· 类图模板画法（边不挂列名）

- **站队**：**修工厂**（论文模板只定画法：线上不写 FK 列名；类框 `Pascal (中文)`；结构仍跟 `schema.sql` + Store，不抄模板里的 Coupon/Seller 清单）。
- **修**：`class_box_title` + `_scrub_class_edge_labels`；SVG / Draw.io / Mermaid 同源；`via` 仅留结构对账。
- **测**：`test_schema_classes` **26 绿**（含边 label 全空 + 标题中文括号）。
- **提交**：`203b268d`。农产 `gf-20261102-235812` sample 类图 cache 已清。
- **你这边**：硬刷新 → 系统类图 force/重开再导出；旧 drawio（带 `publisher_username` 的）作废。

### 本会话（2026-11-15）· 失败码漏挂入库

- **站队**：**修工厂**（`BAKE_LAYOUT` / `BAKE_FORM_CONTROLS` 分类已接线、对照表未入库）。
- **修**：补进 `CODES`/`LABELS`/`FIX_LOCUS` + `docs/bake-fail-analysis.md`（顺带补文档缺的 `BAKE_FILE_LOCK`）；测钉「stem/gate 映射 ⊆ CODES」。
- **测**：`test_bake_fail_classify`。
- **未 commit**。

### 本会话（2026-11-15）· 等待态产品化满分（I2）

- **站队**：**修工厂**（验收/启停/论文对账长任务中间态；短加载统一 `ContentLoading`）。
- **修**：`LongOpWait` + `longOpSession`；`DeliveryReviewPane` 阶段提示与刷新可恢复；Runtime / 论文对账挂同件；Help/Projects/Jobs 短加载。
- **测**：`test_console_wait_state_contract`；成熟度册 I2 ✅。
- **提交**：本批主题「等待态 I2」。

### 本会话（2026-11-15）· 对账「去处理」定位到手调行

- **站队**：**修工厂**（跳转不只到图分组，还带 focus_query / focus_index）。
- **根因（查空）**：①「缺槽位「db」」把结构词当检索，表里无此行；②`opts[index]` 用的是标题排序后的下拉，不是 `sequences[N]`；③图题带「序列图」对手调短标题对不上。
- **修**：跳过槽位/结构检索词；图筛按出图顺序；短标题；筛空则回退并提示。
- **测**：`test_parse_finding_focus_and_enrich_nav_locate_field` 绿。
- **提交**：本批主题「手调/对账 UX」。硬刷新后再点「去处理」。

### 本会话（2026-11-15）· 类图禁 User↔Product 塌缩「关联/收藏」

- **站队**：**修工厂**（不盯死「关联」「收藏」字面：E-R M:N 塌缩 + 菱形动词进了类图）。
- **修**：`infer_relations(collapse_links=False)` 专供类图；边 `via` 只留结构、**线上文案空**（模板画法，见上节）；E-R 总图仍塌中间表。
- **测**：`test_class_keeps_favorite_link_table_no_user_product_collapse` + ER collapse；后并入 `203b268d`。
- **你这边**：重开类图 / force 出图即可。

### 本会话（2026-11-15）· 换主题色 theme_missing 误报异域肤

- **现象**：`p3lean`「异域行业肤 1：theme_missing:shop-lime」——改生鲜青绿/壳色后，盘上仍是上一档瘦身 CSS。
- **修工厂**：`scrub_pack_themes` 找不到本题块时从骨架 `themes/*` 回补再裁；闸文案拆成「本题行业肤缺失」vs「异域行业肤」。
- **测**：`test_pack_themes_rehydrate_when_switching_after_scrub`（整组 `pack_themes`）。
- **未 commit**。重 bake / 再跑门禁即可。

### 本会话（2026-11-15）· 手调区检索扩到各材料表

- **站队**：**修工厂**（搜索/筛选不应只挂功能模块图）。
- **修**：`OverridesTab` 各长表统一「搜索位置 / 原词 / 手调」；序列/活动按图、用例按类型、测例按用例、菜单按类型；切换分组清筛选。
- **提交**：本批主题「手调/对账 UX」。硬刷新 → 出包微调各左侧分组可见工具条。

### 本会话（2026-11-15）· 序列图 → 工作流程文案（进组件）

- **站队**：**修工厂**（任意选题：本张序列消息逐步改写为编号流程；不套示例范文、不发明图外步骤）。
- **修**：`sequence_workflow.py`；`sequence_model`/`load_sequence_model` 挂 `diagram.workflow`；控制台 `SequenceDiagramViewer` 当前图下展示 +「复制工作流程」。
- **测**：`test_workflow_*` + `test_exactly_three` **3 绿**（整文件未全跑）。
- **未 commit**。
- **你这边**：硬刷新 → 打开系统序列图，切图看工作流程区；可贴论文。

### 本会话（2026-11-15）· 序列图主链路默认选题 + 确认收货

- **站队**：**修工厂**（跨域：默认三席不再单占纯登录；交易/单据优先；`my_orders` 默认确认收货；去「数据保存成功」套话）。
- **修**：`sequence.default_sequence_selection`；`_KIND_WRITE_PHASES`/`BROWSE`；通用「保存」让位业务相位。农产 `overrides.sequence.selected_ids` 清空以吃默认。
- **测**：`test_schema_sequence` **17 绿**。农产默认：购物车 / 我的订单(确认收货) / 订单管理(发货)。
- **未 commit**。
- **你这边**：硬刷新 → 序列图 force/重开；若仍旧勾选可清空微调里的序列勾选。

### 本会话（2026-11-15）· 类图论文示例再精简

- **站队**：**修工厂**（仍在「论文示例（精简方法）」签：藏壳表、属性截断、方法去 Spring 噪音/按表语义筛）。
- **修**：`class_model.apply_class_display_mode(sample)` 藏 auth/login/banner 等；属性业务优先最多 8；方法最多 4；`order_line` 不挂整单 Store。
- **测**：`test_schema_classes` **25 绿**。农产 sample ≈14 类。
- **未 commit**。核对稿：`gf-20261102-235812-类图-论文示例精简.drawio`。
- **你这边**：类图保持「论文示例」签 → force/重开再导出。

### 本会话（2026-11-15）· 类图跟实包、禁上帝 Store 串台

- **站队**：**修工厂**（论文类图乱：属性被 Loyalty/Archive 行映射盖掉，方法蹭错表；不以参考图加券/店铺）。
- **修**：`class_code` 按 Store 主表归属收口索引 + 亲和度绑方法；**属性以 schema.sql 为准**；跳过跨域噪音方法；sample 方法前缀优先（`addItem`/`placeOrder`）。
- **测**：`test_schema_classes` **24 绿**（含 `test_java_bind_keeps_sql_attrs_and_blocks_god_store`）。农产包抽查：User/Category/Order 属性干净，Category→Controller CRUD，订单/购物车→OrderStore。
- **未 commit**。
- **你这边**：硬刷新后打开系统类图（已清 `gf-20261102-235812` 类图 cache）；若仍旧图可对账 force。

### 本会话（2026-11-15）· 近义匹配、架构文档与控制台原型收尾

- **匹配**：目录支持 `synonyms` 近义簇，同簇命中计 1 锚分；LLM 目录摘要展示锚与近义写法。补「办公用品劳保用品申领」真题写法，避免 S-05 落入 `DOM-GENERIC`。
- **架构文档**：`ARCHITECTURE.md` 与 `architecture.html` 同步论文图 SVG / Mermaid / Draw.io 导出与 `rubric`、壳色色点池、`p3layout` / `p3controls`，并修正放大提示文案。
- **原型**：`prototype/` 对齐现行开工台、项目列表、失败分析与详情阶段轨；失败样本四类筛选组合生效，仍为静态 mock。
- **测**：`test_sample_proposal_match.py`、`test_deep_skin_s.py`、`test_oa_apply_p.py` **48 通过，541 子用例通过**；pytest cache 有 Windows `WinError 5` 权限警告，不影响结果。原型 `node --check`、浏览器筛选 / 阶段门槛验收、`git diff --check` 通过。

### 本会话（2026-11-15）· 真红四处（评审子集）

- **修工厂**：基线抹 `OrdersAdmin`/`ReservationsAdmin` 工厂注记（禁 `bake` 词）；`PortalHome` mall-hero 自限高消 `abs_in_stretch_slot`；博客加厚不再硬塞 `userPublish`（投稿仍扫词）；足迹/收藏/留言 SQL 预算改走 `evaluate_table_budget` + 足迹增量 1 表。  
- **测**：`test_pack_prune` 基线注记、`test_layout_contract`、`test_ux_scan` 足迹预算、`test_user_publish_content`、`test_c08_capability_islands_gated` / `test_c04_blog_skin`、favorites/guestbook SQL **绿**。  
- **未 commit**。

### 本会话（2026-11-15）· 行业肤出包必须剪

- **现象**：李锐莹包 `themes.css` 仍全厂 `@import` + `themes/*` 六十多套（工厂配色库穿帮）。  
- **修工厂**：`pack_themes.scrub_pack_themes` 按 `spec.theme` 只留本题（如 `shop-lime`→`themes/shop.css` 单块）；`p3lean.foreign_themes` 红则禁 ZIP；`engine_bake` 在 layout_heal 后再裁一次。  
- **测**：`test_pack_prune -k pack_themes` 绿。  
- **未 commit**（`pack_themes.py` 仍 `??`）。  
- **你这边**：重启后端后**重 bake** 才吃到；手边旧目录不会自动变瘦。骨架 `skeletons/.../themes.css` 全库是真源，故意不砍。

### 本会话（2026-11-15）· Overrides P0 验收红（手调类图去簇回写）

- **站队**：**修工厂**（代码已推 `47369246`/`b1dc4cbc`，但 P0 验收未绿 → 完工不成立）。  
- **根因**：bake 预热 `load_class_model` 对手调重叠框内存去簇后**回写** `islands/class_layout.json`，盖掉白名单 restore；非重叠坐标本可保留。  
- **已做**：去簇只留内存、仅「首次自动排版」落盘；钉 `test_unclump_does_not_rewrite_hand_layout_on_disk`；台账 [`pack-overrides.md`](./docs/pack-overrides.md) / 本节与下节「未 commit / 测绿」对齐。  
- **测**：`test_unclump_*` 2 绿；`test_rebake_keeps_module_labels_and_class_layout` **1 绿**（约 3min；先前 FileNotFound 为并发脏盘假红）。  
- **未 commit**（等人令）。

### 本会话（2026-11-15）· 壳色色点池 P0～P3

- **修工厂**：按 [`docs/shell-color-swatch-pool.md`](./docs/shell-color-swatch-pool.md) 接线——`shell_color_swatches.py` 静态池（themes 灌入+稳色）；catalog 暴露；微调色块选 theme + 可折叠自配主色/点缀 + 小预览；`shell_face`/`shell_colors_for_pack` 叠自配；换皮/reset **钉死清空自配**；脏主色/对比硬拦，互撞软提示。  
- **示意跟色**：catalog `theme_shell_previews` 与 themes CSS 同源；微调区**只留一处生效线框**（去掉问号线框、自配条第二预览、行业色下拉）。  
- **口径**：行业=底皮；自配=可选盖主色/点缀（不是第三套色）；已自配时色块标「底皮」、示意文案写清覆盖关系。  
- **测**：`test_shell_color_swatches` + `test_shell_face` **19 绿**。  
- **未 commit**。  
- **你这边**：硬刷新控制台；自配紫+米时示意跟自配，海蓝只作底皮锚点。

### 上一段（2026-11-15）· 农产改生鲜青绿 + 侧栏乱码

- **探针**：李锐莹包 **`shop-lime`**；侧栏 UTF-8 已修；marketplace 侧栏已接。  
- **未 commit**。

### 本会话（2026-11-14）· 序列/活动去模板腔

- **修工厂**：`_KIND_WRITE_PHASES` 覆盖主链路常见 kind（cart/review/orders/tickets/archive/content/profile/users/category/lookup/coupons/browse_history/week_calendar/deadline/archive_logs/blind_pools/group_campaigns/delivery_slots/price_spans/permits/line_specs/lost_clues/consigns/open…）；缺表走 `_phases_from_flow_spec`；禁「选择{菜单}」容器套话；活动图同源。  
- **测**：`test_schema_sequence` 15 绿；`test_diagram_rubric` + `test_agents_thesis_diagrams` 17 绿。  
- **未 commit**。  
- **你这边**：重启后端 + 打开序列/活动（或对账 force）吃新文案。  
- **余（非本片）**：私信 usecase 勿与资料页合并（超新 dm+profile）。

### 上一段（2026-11-14）· 论文材料生成纠偏 + 对账不吃旧缓存

- **修工厂**：有 `staff_posts` 时按岗 pack 校验（空 subadmin 不误杀）；评价序列勿吃 OrderController；购物车↔订单拆桶；`product←order_line` 改关联；对账 `pack_*` **force**；评价订单文案规则闸不依赖 menus。  
- **探针**：健身电商 force 后确定性须改 **0**。  
- **测**：`test_agents_thesis_diagrams` + `test_diagram_rubric` 17 绿。  
- **未 commit**。  
- **你这边**：**重启工厂后端**再点对账；材料卡旧图可重开/重 bake。

### 上一段（2026-11-14）· 学生端 API 清单对准实包

- **修工厂**：`api_inventory` 不再按 `api_style` 藏变体；清单 = 工作区 Controller 实有 Mapping；`flow_api` 路径 need 改精确匹配；产物页/帮助文案标明「源码清单，非 Swagger」。  
- **测**：`test_api_inventory` + `test_api_style` 绿（含基线条数对账）。  
- **未 commit**（与论文图等同批未推）。  
- **余**：不改运行时 OpenAPI；真要 Swagger 联调仍走「运行」页后端。

### 上一段（2026-11-14）· 论文图同源导出 + M3 rubric 闸

- **修工厂**：三档导出（Draw.io / Mermaid / SVG）同源；`diagram_rubric.py` 挂 `rubric_gate`，下载红则 400；几何债仍延期（parked **m**）。  
- **测**：`test_diagram_rubric` + `test_diagram_export_*` 22 绿。  
- **未 commit**。  
- **余**：M4 LLM 对账（可选）；厂内几何刀另开。

### 上一段（2026-11-14）· 手调归论文材料

- **修工厂**：出包「手调文字」从轨旁工具迁回论文材料；八张材料卡齐挂并锚 Overrides 分组；工具只留日志。  
- **测**：`test_console_product_form_contract` + `test_delivery_stages_contract` 绿。  
- **未 commit**。

### 上一段（2026-11-14）· 出包门禁按 Job 落库

- **修工厂**：`jobs.gate_report` 存当次质量门禁表（rows/checklist，瘦身无 detail 巨文）；列表只带 `has_gate_report`；`GET /jobs/{id}/gate-report` + 任务队列「门禁」弹层查历史。  
- **测**：`test_gate_report` 5 绿。  
- **未 commit**（与阶段轨等同批未推）。

### 上一段（2026-11-14）· 阶段轨按毕设顺序

- **修工厂**：主轨六步；质检交付压短（删产物墙；失败场景合并阻断卡，门禁全文进弹层不抹错）。  
- **测**：`test_delivery_stages_contract` + product-form / workbench 契约。  
- **未 commit**。

### 上一段（2026-11-12）· 出包身份/死依赖/README 假表（探针 gf-20261102-235812）

- **修工厂**：`pack_deps` 瘦身（关 AI 裁 spring-ai / lombok / validation / tinycolor）+ `p3lean` 扩库名一致、单启动类、README 假表；骨架 README 改为按本包 schema 填 SQL 示例。  
- **取证**：工厂工作区库名/包名一致；学生目录 `agri-mall-app` 双包 `agri_mall`+`agri_produce_mall` 为下载后改名残留，非 bake 产物。  
- **测**：`test_pack_deps` + `test_pack_prune` lean/commission 对口。  
- **未 commit**；旧 ZIP 须 **重 bake** 才干净。

### 上一段（2026-11-09）· 新人入职上手 CX～S3

- **修工厂**：主路径文案（清洗文案 / 你可以先 / 需要改程序）；launcher `N` 环境检查；README 拉仓开工；开工台/项目空态；MatchTab 核对清单；就绪条 `recoveryHint`。  
- **测**：`test_console_newhire_copy_contract` + readiness/workbench 契约。  
- **§3.1**：下载/门禁判定未改；仅呈现与引导。  
- **未 commit**。

### 上一段（2026-11-07）· 同阶段双 primary 收口

- **修工厂**：就绪条在匹配/生成/质检（非下载）同阶段改为「请在下方…」文案，不放同义主钮；下载仍只在质检强调；生成页「去质检」改 secondary。  
- **测**：readiness + product-form。  
- **未 commit**。

### 上一段 · 整厂产品形态验收通过

- W1～W15 + §2.4.1 过；侧栏「连接与用量」。

### 上一段（同日）· 波次 9 全局收（禅道品类）

- 全局扁平面板、密侧栏、条带 stats；Projects/Jobs 工具条+托盘。

### 上一段（同日）· 波次 9 开工（V1+V3）

- 开工台主区 + 详情壳 + Artifacts 去同级 panel 头；`.surface-*` 铺底。

### 上一段（同日）· 波次 9 手册

- 表面册 + 成熟度 §2.5 / 波次 9 落档；UI 待令后已开工。

### 上一段（同日）· 波次 8 整厂产品形态

- **修工厂**：W1～W15 按 §2.4.1 收呈现；详情垫刀保留。  
- **§3.1**：未改下载/门禁/复审判定。  
- **测**：`test_console_product_form_contract` + stages/workbench/readiness。  
- **关闭**：清单已勾；走查仍建议 `整厂产品形态验收`。

**接棒三步**

1. 读本表「当前待做」波次 + 册对应 §4 完成定义（勿通读全仓）；必读册 **§3.1**。  
2. **修工厂** `frontend/src`（波次 2+）或 git 合入（波次 0）；禁止只擦学生 ZIP。  
3. 波次勾选关闭后改本表状态，再等人令 commit；收工按 §3.1 写三条自检。

**实现铁律（极重要 · 全书波次适用）**

1. **只改已有实现**：先搜现成家（`applyDeliveryReviewPanel` / `canDownload` / 复审 API / OpsHome 队列等），能改原路径就改原路径。  
2. **禁止第二套逻辑**：同一职责一条因果链；UI 重组 = 搬接与显隐，不双写状态、不平行判定。  
3. **改前改后业务逻辑不变**：下载/阻断/验收/重打包条件与 API 语义保持原样；只改编排与呈现。  
4. **要改逻辑 → 先问作者再动手**：判定/条件/API 语义/状态机不得不改时，停手提问，取得同意后再写代码；禁止先改再汇报。  

违反任一条 = 本波未完成。细则：[`docs/product-form-maturity.md`](./docs/product-form-maturity.md) **§3.1**。

**禁止插队**：未关 0～2c 前不做视觉换肤 / 多租户 / 新域 thicken。  
**波次 0 代码堆（2026-11-06 已推 main）**

1. `47369246` 出包微调：bake islands + Overrides 元库重放  
2. `979b7a5e` 控制台写后乐观更新与超时  
3. `b1dc4cbc` 控制台 Overrides Tab  
4. `853f50a2` 产品化成熟度 / 执行波次 / §3.1  

校验闭环批 1～4、FAQ 专皮等更早已在主线。余下：作者勾 §7 定位 → 关波次 0 → `做产品化 A`。

### 本会话（2026-11-06）· 全做收尾（O2～O4 / E2 / L1 / M1；D1 未关）

- **A O2**：后端下载/复审 API 文案「验收/重打包」；前端匹配兼容旧词。  
- **B O3/O4**：boss-intent / 00-factory-core 标准名 + `sync-ide-rules`；delivery-audit / maturity 活表文首。  
- **C E2**：地图 §0「版本或放弃」表。  
- **D**：D2/D5 按现有门禁与对齐机制勾部分齐；**D1（parked m）不假关**。  
- **E**：FailAnalysis→Help 码表；发版检查 M1/D1 抽检项。  
- **F C1**：台账格仍在，须人填数字。  
- **测**：readiness / schema_modules / write_after 48 绿。未 commit。

### 本会话（2026-11-06）· 波次 2d / P9 陌生人走查（助手伪装新手）

- **环境**：`http://127.0.0.1:5300/` + API `:8000`。
- **开场 blocker（已热修）**：控制台白屏，`useProjectDetail.js` 误写 `queue Promise` → 改为 `void Promise`；否则无法进任何页。
- **成功路径**：开工台「可下未发」→ `超新农产品` → 顶栏就绪「可下载 / 下载 ZIP」→ 收到 `agri-produce-mall-app.zip`（主路径约 2 次有效点击）。
- **阻断路径**：图书借阅单 → 「暂不可下载 ZIP」+ 门禁未过列表 + 主按钮「去质检交付重打包」→ 落到质检交付工作台（同屏）。
- **残留（不挡 P9 关）**：后端 `download_blocked_reason` 仍含「验圈/合卷」旧词；UI 主按钮已是「重打包」。O2 可再洗 MSG。
- **结论**：**P9 通过**；波次 2d 关。未宣称材料债/O3 已齐。

### 本会话（2026-11-06）· 波次 3～6 关闭（作者口令：3、4、5、6按顺序）

- **波次 3**：MatchTab 高级折叠；OpsHome「门禁失败/可下未发」；Projects 行内收敛 + undelivered；`glossary.md`；DeliveryReviewPane/Help/opsShared 标准名（验收/重打包/未通过清单/审计检查表）。O3/O4 顺延。  
- **波次 4**：C1 人工介入率台账（见下）；C2 [`docs/release-checklist.md`](./docs/release-checklist.md)。  
- **波次 5（诚实）**：README 对外三态；匹配无 SSR；题名映射「文档≠产品」；答辩 PPT 无前端 mock。**未宣称** D1/D2/D5/E2 已齐。  
- **波次 6**：`SystemInfo.preview_*` + 开工台 N/M；README「最多 3 路」；P8 就绪条唯一 primary。  
- **2d(P9)**：按作者点名跳过，待 `产品化走查`。  
- **§3.1**：只改已有路径；无第二套下载/复审判定；逻辑未改。  
- **测**：跑控制台契约 + canary 门禁（本会话收工）。  
- **未 commit**（等人令）。

### 人工介入率台账（C1 · 30 天滚动）

> 填法：每开一次「修工厂」修复会话记 1；同期「可下载出包」数作分母。分类只勾主因。

| 窗口起 | 窗口止 | 修复会话 | 出包数 | 介入率 | 匹配 | bake | 门禁 | 控制台 | 材料 |
|--------|--------|----------|--------|--------|------|------|------|--------|------|
| 2026-10-10 | 2026-11-09 | （待填） | （待填） | — | | | | | |
| （说明） | | 本窗口已开；入职走查后按「修工厂会话 / 可下载出包」实填，勿用体感关 C1 | | | | | | | |

### 本会话（2026-11-06）· 波次 2c 关闭（做产品化 P3）

- **修工厂**：质检交付单页 `DeliveryWorkbench`——清洗/门禁/验收/重打包/下载同屏；对照材料下沉。  
- **改的已有路径**：复用 `DeliveryReviewPane` + `gateRows`/`scrubStudentCopy`/`downloadZip`；`goArtifacts(gates|review)`→滚到工作台。  
- **无第二套**判定；下载/复审条件未改。  
- **逻辑变更**：无。  
- **测**：`test_delivery_workbench_contract` 绿。  
- **当前波**：下一棒曾为 **`产品化走查`**；作者改令先做 3～6（已关）。

### 本会话（2026-11-06）· 波次 2b 关闭（做产品化 P2 · P2/B1/B2）

- **修工厂**：阶段轨 + 一级 Tab 降维（匹配/生成/质检交付/预览 + 工具）；生成成功默认落地质检交付。  
- **改的已有路径**：`defaultTabForStatus`（`opsShared`→`deliveryStages`）、`canEnterDetailTab`、`DeliveryStageRail`、`openTools`；日志/微调并入工具。  
- **无第二套**状态机；下载/门禁条件未改。  
- **逻辑变更**：无判定语义变更；仅导航呈现与默认落地 Tab（generated/running→artifacts）。  
- **测**：`test_delivery_stages_contract` 绿。

### 本会话（2026-11-06）· 波次 2a 关闭（做产品化 P · P1/P7/A5/A6）

- **修工厂**：详情顶栏交付就绪指示 + 主路径错误三件套（呈现层）。  
- **改的已有路径**：`projectIsDownloadable` 同口径 → `deliveryReadiness.js`；`goArtifacts` / `downloadZip` / `scrubStudentCopy` / `retryCurrent`；`ProjectDetail` 页头主下载并入就绪条；`GenerateTab` 失败横幅。  
- **无第二套**下载判定（仍读 `download_blocked_reason` / `blocking_gates`）；阻断 ≤3。  
- **逻辑变更**：无（未动 `canDownload` / 门禁键 / 复审通过条件）；仅主操作视觉唯一与导航搬接。  
- **测**：`test_delivery_readiness_contract` + `test_console_write_after_contract` 绿。

### 本会话（2026-11-06）· 波次 1 关闭（做产品化 A）

- **修工厂**：写后 busy 与权威拉解耦；启停不绑 Maven 长轮询；超时文案；契约测。  
- **改的已有路径**：`DeliveryReviewPane`（`applyFromWrite` / `refreshAfter`）、`scrubStudentCopy` / `applyDeliveryReviewPanel`、`usePdRuntime.rtAction`、`api.js` 超时。  
- **无第二套**就绪/下载判定；下载/合卷/验圈条件未改语义。  
- **逻辑变更**：无（未动 `canDownload` / 门禁键 / 复审通过条件）；启停仅 `rtSettling` 门闩防 busy 提前消后的重复 start（starting 仍可 stop，与改前一致）。  
- **测**：`pytest tests/test_console_write_after_contract.py` → 7 passed。

### 本会话（2026-11-06）· 波次 0 关闭 · 开波次 1

- §7 勾选 **Single-operator**；README 定位句已写；册 §5.1 波次 0 → 已关。  
- 波次 1 已同会话收口（见上）。

### 本会话（2026-11-06）· 拆主题提交并推送

- 上表四笔已 `origin/main`；工作区干净。  
- **当时波**：0 仅余 §7；现已关。

### 本会话（2026-11-06）· §3.1 实现铁律入册

- **写文档**：册 §3.1 + 本文件「实现铁律」——已有路径 / 禁第二套 / 逻辑不变 / **改逻辑先问作者**。  
- 改代码时自检（含是否触及逻辑、是否已问）写回本文件。

### 本会话（2026-11-06）· 产品化执行波次写入交接

- **写文档**：册 §5.1 + 本文件波次表。  
- **当前**：波次 0 代码已推；余 §7 勾选。下一代码口令 **`做产品化 A`** → **`做产品化 P`**。

### 本会话（2026-11-06）· 运营控制台产品级交互入册

- **已做**：册 §2.4 + §4·P；parked **p**。UI 未改。  
- **并入**：上表波次 2a～2d。

### 本会话（2026-11-05）· 产品化成熟度入册

- **已做**：册 A～N；§O 用语（parked **o**）。  
- **并入**：波次 0 / 1 / 3（O）。

### 本会话（2026-11-05）· 合卷/写后 UI 不同步

- **修工厂**：乐观更新 + `refreshDeliveryReviewPanel` 等（见当日 diff）。  
- **未提交**：归波次 0 拆 commit；收口扫漏归波次 1 `做产品化 A`。

### 本会话（2026-11-04）· FAQ 分类同字 + 具名域专皮

- **站队**：**修工厂**（种子跟开题/SQL lookup 同口径；具名域不偏科）。
- **已做**：① 36 具名域 FAQ 专皮；② bake 时 FAQ 分类名对齐 `category`/`ticket_type`；③ 表外分类 → lexicon error 挡 ZIP；`fragments.ensure_ai_assistant_sql` 委托 features。
- **测**：s75 同字 / align / 分叉闸 / 具名域不落 generic 绿。
- **未提交**：与校验闭环批 1～4 一并等人令 commit。

### 本会话（2026-11-04）· 校验闭环 · 批 1～4 收口

- **站队**：**修工厂**（碎另案 **n** · [`docs/validation-loop-hardening.md`](./docs/validation-loop-hardening.md)）。
- **已做**：①假宣称硬闸；②FAQ 种子跨域词；③`thesis.ai-reply-polish` 默认关；④低置信/GENERIC「已人工核域」。
- **未提交**：等人令 commit。
- **续**：上节 FAQ 专皮全补。

### 本会话（2026-11-04）· 模块图「文案红」可诊断

- **站队**：**修工厂**（L0 闸体验；不做可编辑页）。
- **原因**：闸红时卡禁打开；未列 findings；图缓存不跟 `modules.py`，重载像没修。
- **已做**：文案红仍可打开；卡/弹窗工厂提示 + findings；`force` 绕过缓存；红时禁导出。
- **假绿收口**：未拉图不得「可导出」→「待核验」；进论文材料页 `ensureModulesMeta` 预检闸；真红才「文案红」、真绿才「可导出」。
- **Overrides P0～P3**：[`docs/pack-overrides.md`](./docs/pack-overrides.md)——白名单 bake、元库+API、模块短签/hide、序列·活动·用例描述勾选与短签、架构/用例图/测例/菜单/类图、`invariants`+交付审计一句。**已推送** `47369246` / `b1dc4cbc`。P0 验收曾红（预热去簇回写手调坐标）→ 见上节 2026-11-15 修；`test_overrides_payload`（含 hide/class）绿。
- **你这边**：说 **`提交并推送`**（本轮去簇不回写 + 台账）；真机点微调 Tab 验收。

### 本会话（2026-11-03）· 农产下单 NPE · Map.get→doubleValue

- **站队**：**修工厂**（探针：超新农产品商城 `gf-20261102-235812`）。
- **根因**：未挂 `weigh_sale` 时 prune 把 `WeighSaleStore.priceLine(...)` 抹成 `priced = item`；档案行无 `lineYuan`，结算 `((Number) priced.get("lineYuan")).doubleValue()` NPE。
- **已做（已 commit）**：三骨架 `OrderStore.priceLineOf`（称重开则委托，否则件数×单价）；`pack_prune` 去掉「抹成 item」；钉测 `test_order_store_price_line_of_survives_weigh_prune` + strip 用例；当面工作区已补同一计价并重编。
- **测**：pack_prune strip / weigh_sale 相关绿。
- **你这边**：新包重 bake；当面农产预览若后端已起，可再走一遍「确认支付并下单」。

### 本会话（2026-11-02）· 热修 · QA 只报影响程序的问题

- **站队**：**修工厂**。
- **口径**：LLM warn/error 必须命中「影响程序/演示」信号（缺 labels、串台、假宣称、空壳等）；口味/建议类丢掉。
- **已做（已 commit）**：`_SYS` + `_PROGRAM_IMPACT_RE` 过滤；评价双口径误报仍滤；temperature 0.1。
- **测**：program-impact / 润色 / 评价误报 绿。
- **你这边**：工厂吃新代码后重跑交付质量摘要。

### 本会话（2026-11-02）· 角色边界 · fallback 收齐 · **L4 十组完**

- **站队**：**修工厂**（L4 · `fallback`）。
- **已做（已 commit）**：R-FALLBACK-01～02；L4 十组全齐。
- **续**：见上节热修；本片已随主题拆提交推送。

### 本会话（2026-11-02）· 角色边界 · interact / content / apply 等已齐

- 见册 `docs/role-boundary-copy-batch.md` §3～§4；本轮末组见上节。

### 本会话（2026-11-02）· 角色边界 · borrow 组收齐

- **站队**：**修工厂**（L4 · `borrow`）。
- **已做（已 commit）**：R-BORROW-01～02；`borrow` **已齐**。
- **续**：见上节 `ticket`。

### 本会话（2026-11-02）· 角色边界 · reserve 组收齐

- **站队**：**修工厂**（L4 · `reserve`）。
- **已做（已 commit）**：R-RESERVE-01～02；`reserve` **已齐**。
- **已知未挡**：INSTRUMENT 未拆 lead；未知口语；L5。
- **续**：见上节 `borrow`。

### 本会话（2026-11-01）· 角色边界 · trade 组收齐（R-TRADE-02～05）

- **站队**：**修工厂**（L4 按域族收）。
- **已做（已 commit）**：02～05（订单页 lead / FOOD / 多店 notice / CINEMA 回归）；`trade` **已齐**。
- **已知未挡**：未知口语仍依赖 p3q/LLM；L5。
- **续**：见上节 `reserve`。

### 本会话（2026-11-01）· 角色边界文案按域族收（批次册）· R-TRADE-01

> **老板离场口径**：同题再 bake，**不许**再因同一句 `ordersAdminLead`（发货/物流塞进管理员）红掉。其它洞另说，禁止轻飘保证「整包永远绿」。

- **主题**：`p3q`「管理员 lead 写成商家发货」→ **修工厂**；批次册 + 换开题抗性诚实账。
- **已做（已核对并 commit）**：`builders_slot` lead 拆句；`_marketplace_role_copy_findings`；册 §0 + R-TRADE-01。
- **同题再 bake**：本条 error **不应复发**。若仍红必是别条 finding。
- **续**：见上节 trade 02～05 已收；本片已随主题拆提交推送。

### 本会话（2026-11-01）· Unsplash 题槽灌库（消抖）

- **主题**：大陆无魔法时 Unsplash 抖动 → **修工厂**（出包读盘，外网只灌库）。
- **口径**：共用 `unsplash_fetch`（重试 + 可选 `UNSPLASH_HTTP_PROXY` + 本机 auth/portal 缓存）；确认匹配时 `atmosphere_prefetch` 短窗灌库，**失败不挡确认**；结果进 `spec.atmosphere`。
- **运营台**：Unsplash 页显示代理/缓存张数与提示。
- **测试**：`test_unsplash_fetch` + `test_atmosphere_prefetch` **9 passed**。
- **下一步（未做）**：开题关键词合题检索；确认失败硬闸（无代理会卡死，暂不做）；国内图源另案。

### 本会话（2026-10-31）· E-R 几何外页（碎另案 m）

- **主题**：直线咋拖都交叉 → **修工厂**（禁实体全环）。
- **口径**：ELK layered 摆框不变；直线真交叉的联系进**外页弯线**（绕布局包围弧）；内页直线零交叉。
- **已做**：`_partition_geometric_outer`；`render_er_svg` 接回外弧；`test_schema_er_layout` 钉 K5/hub。
- **测试**：`test_schema_er_layout` + `test_schema_er_labels` **17 passed**。
- **用法**：控制台重新生成 E-R 总图（或重 bake 材料）才看见；旧 SVG 不会自动变。

### 本会话（2026-10-28）· 论文图 ELK 初局（碎另案 m · E-R/类图）

- **主题**：E-R/类图换引擎 → **修工厂**（少去 draw.io；控制台拖=正式路径）。
- **口径**：初局 `pyelk` layered（禁全环）；拖拽钉框、**不重跑 ELK**；失败不回退环排。
- **已做**：`layout_elk.py`；E-R / 类图走 ELK；invariants + parked **m**。
- **余债**：模块/序列/活动等图种仍属 **m**；`class_layout` 旧竞赛残留。
- **续**：2026-10-31 已接几何外页（见上节）。

### 本会话（2026-10-28）· 碎另案 i 补漏

- **主题**：工作台空图空表补漏 → **修工厂**。
- **已做**：`DOM-CARRENT` 预约/订单三态+日期；`DOM-SHOP` 基线模板四态；跨域测扩 CARRENT/SHOP 基线。
- **说明**：单据域主体此前已修；内容/档案向域 KPI 靠目录种子，不造假订单。农产封面去 twemoji，走 `/uploads/demo/cover-NN.jpg`。

### 本会话（2026-10-28）· 碎另案 l

- **主题**：开题未扫中勿硬落 SQL 列（全局）→ **修工厂**。
- **已做**：`ensure_shared_sql_columns` 按 `loyalty_caps` 拆列；交易三域售后宽列 / 其它有单域只 `completed_at`；`engine_sql` 传 cap 集合；golden SQL 重生；`test_shared_sql_loyalty_split` + golden + trade thicken **48 passed**。
- **余债**：FOOD/预约 thicken A 壳整包另刀；parked **l** 标已修。

### 本会话（2026-10-27）· 任务日志按次切段

- **主题**：控制台 job.log 按 RUN 切段（多次出包不糊一条河）→ **修工厂**。
- **已做**：`jobLogRuns.js` 分隔符与 `jobs.format_run_*` 同 U+00B7；pytest↔Node parity 用 `encoding=utf-8`（Windows 不再把 `·` 读成 `?` 导致 outcome=RUNNING）。`test_job_log_runs.py` **4 passed**。未提交。

- **主题**：功能模块图短签 + 机器闸（全选题，不靠人盯）→ **修工厂**。
- **原因**：切开粘句后仍啰嗦；「…系统后台登录」因含「登录」进框；人不能每题盯 SVG。
- **已做**：
  - 认证白名单；散文/泄漏双丢；短签去前缀/模块尾；超长·并列换菜单短名；每行≤8 折行。
  - **`label_gate`**：每张图出 `ok/findings`；红则材料卡「文案红」、弹窗警告；SHOP/HOTEL/BLOG/CARRENT + 方木 canary 钉绿；人工补丁后重跑闸。
- **测试**：`test_schema_modules.py` **30 passed**。未提交。
- **下一步**：热重载后重开模块图；闸红改 `modules.py` 清洗，勿只擦单包 SVG。

### 本会话（2026-10-26）· 任务日志按次切段

- **主题**：行业配色与壳强调色打架（健身橙盖海蓝）→ **修工厂**。
- **已做**：壳色优先从 themes CSS 按当前 theme 派生；出包 `shell_colors_for_pack` 重算；货架橙仅无 theme 兜底。`test_shell_face` 绿。须重 bake / 改配色后再生成。未提交。

- **主题**：商城 GATE 红「学号或工号已被绑定」错域残留 → **修工厂**。
- **原因**：`studentNoDupHint` + `UserStore` 写死校园句，无学号档案的商城仍进包。
- **已做**：hint 跟 `profileFields` 有无校园身份键；三骨架异常改中性句；Register 映射；auth 钉测。须重 bake。未提交。

- **主题**：分堆题名「了面向…」+ 任务书标成开题 → **修工厂**（通用，不一种一修）。
- **原因**：文献句「设计并实现了…[6]」串题；研究现状段别人系统名；长文压过文件名「任务书」。
- **已做**：明示/整行/引号优先；弱线索裁掉研究现状；跳过助词与 `[n]` 尾；文件名角色优先；图书/宿舍/方木等多例钉测。未提交。

- **主题**：`upload/plan` WinError 32（move 开题 docx）→ **修工厂**。
- **原因**：python-docx 按路径打开会占锁；随后 `shutil.move` 删源失败。
- **已做**：`_read_docx` 改 BytesIO；迁 plan 目录改 copy2 + 重试 unlink。未提交。

- **主题**：任务书被分堆剔除（看起来像 LLM 误伤）→ **修工厂**。
- **原因**：`_read_docx` 只读段落，方木任务书正文在表格里 → 仅 11 字 → signal=0 → 规则/LLM 都当空材料剔。
- **已做**：docx 抽表（按 `tc` 去重）；`test_read_docx_tables`。不关上传 LLM（多课题分堆仍有用）。未提交。

- **主题**：`GET /api/projects/stats` MissingGreenlet → **修工厂**。
- **原因**：`stats` 误 `defer(delivery_review)`，但 `pending_review`→`is_zip_downloadable`→`get_review_state` 仍要读该列 → async 懒加载炸。
- **已做**：去掉该 defer；`test_stats_must_not_defer_delivery_review` 钉住。未提交。

- **主题**：确认分堆缺「追加材料」→ **修工厂**（复用 `build_upload_plan`，不改分堆/建项语义）。
- **已做**：`POST /upload/plans/{id}/append` + `append_and_rebuild_plan`（同 plan_id）；`Projects.vue` 弹窗按钮；Help / ARCHITECTURE；`test_upload_cluster` 追加 2 例。
- **测试**：`test_upload_cluster.py` **14 passed**。未提交。
- **下一步**：浏览器确认弹窗点「追加材料」验活；后端热重载后即可。

### 本会话（2026-10-25）· 任务日志按次切段

- **主题**：控件闸口径——下拉可筛选、禁造库外值 → **修工厂**。
- **已做**：册/规则/skill/`ArchiveFieldControl` 注释对齐；C1 仍只红 `allow-create`，`filterable` 绿。方木 `p3controls` 扫 0 命中（无 creatable；列表分类 ID / 佣金误挂不归本闸）。未提交。

- **主题**：佣金台账误挂（方木研究现状「分销」）→ **修工厂**。
- **已做**：`ux_crosscut` 禁光杆「分销」，改扫一级/推广/分销佣金等；`CONTRAST` 补研究现状段；钉测。旧包须重 bake 才掉菜单。未提交。

- **主题**：管理端列表双「分类」出 `1,5` + 回收站同列 → **修工厂**。
- **已做**：`listExtraFields` 禁 `multi-select`/分类键；`vue-script-setup-src` 补 `addWatchFile`（改 `.setup.js` 须重编 `.vue`，否则 HMR 假绿）。
- **验活**：方木预览列表/回收站均只 1 列「分类」（名称）；`test_archive_admin_core_fields` + `test_vue_script_setup_src` 绿。未提交。
- **坑**：只改 setup 不碰 `.vue` 时旧 Vite 会吃内联缓存；垫片已钉 watch。

- **主题**：档案字段「不适用」L1～L3 → **修工厂**（方木探针）。
- **L1**：管理端主通道吞 `categoryIds` 等，禁二次手填「9,7」。
- **L2**：承重/阻力等出 `number`；控件兜底。
- **L3**：适用表**不进学生 schema**。软皮 `detail_attr_when` + 基线 `detailAttrWhen.js`（按 `shopCatalogKind`）；出包只带皮 id（如 `retail_fitness`）。`scrub` 会剥 `detailAttrWhen`。
- **测试**：`test_detail_attr_when` 等绿。未提交。
- **坑**：开题含糊且没命中皮 → 整池选填+空不露；正式题重 bake。
- **下一步**：硬刷新：选瑜伽垫无阻力；选弹力带才有。

- **主题（早段）**：货架卡 + 独立详情不像真货架 → **修工厂**。
- **已做**：短签只出值；关货架「另有 N 项」；详情 buybox 钉底、去「单价(元)」。
- **测试**：trade/detail shop 绿。未提交。

- **主题（早段）**：货架卡底（库存/详情/加购）歪 → **修工厂**（`ArchiveBrowse` 卡底拆分 + shelfgrid CSS）。
- **已做**：卡底拆分；`:only-of-type`→`nth-child(2):last-child`；预览曾只同步 CSS。
- **测试**：layout + portal nav 绿。未提交。

- **主题（早段）**：方木「换头像」掉条底 → **修工厂**；闸改**通用规则**（禁一事一断言）。
- **已做**：
  - 基线头像槽自限高。
  - D2 通用 `abs_in_stretch_slot`（stretch + 贴底 absolute → 槽须自限高；全局 `styles/**`；原生 button）；轮播满高台豁免。
  - 视觉通用：每 visit 量「绝对可点 ↔ 同槽文档流」间距；`/profile`×accountFace 仅作回归探针。
- **测试**：contract+smoke 单元绿；`test_pilot_browser_pipe` **1 passed**。未提交。
- **坑**：出包 `p3layout` 仍只 D1+D2。

- **主题（早段）**：布局闸对齐覆盖不全（一包装露 → 全基线同构）→ **修工厂闸**。
- **已做**：`list_card_partition` / `side_rail_align`；CSS `flex-wrap` 别名；消红若干页；册九→十模式续见上段。
- **坑**：曾标 D1～D5 已齐但断言窄；绿 ≠ 盖住。

- **主题（早段）**：市集侧栏 UX + 门户首页 mall 被空 domain 打回 cards → **修工厂**。
- **已做**：
  - `portalShellNav.js`：`RAIL_OUTSIDE_DEFAULT=3`；`RAIL_SHORT_LABEL` + `railShortLabel`（禁双「我的」）。
  - `PortalSideRail.vue`：短签 + 居中对齐。
  - `themes.resolve_portal_home_style`：domain 空串时手选 mall 不再降级；`pdLabels.defaultPortalHomeStyle` + `useProjectDetail` 货架域缺省 mall。
  - 探针 `gf-20260929-235748` 已同步侧栏文件并把 `appDelivered.portalHomeStyle`→`mall`。
- **测试**：`test_portal_shell_nav.py` + `test_portal_home_style.py` **17 passed**。
- **下一步**：浏览器清 `localStorage.gf_shop_side_rail` 后硬刷新 Vite；正式题请重 bake。未提交。
- **坑**：旧本机偏好会把 5 个全钉外侧，看起来「编辑=外侧」；清 key 即可。

- **主题（早段）**：项目详情「日志」Tab 多次出包糊成一条河 → 修工厂控制台。
- **已做**：`jobs.py` 写 `RUN start/end` 锚点；`LogsTab` 默认只看最近一次，可下拉历史/全部；旧日志用 `preview stopped` 兼容切段；`job_log` tail 200→800。
- **测试**：`tests/test_job_log_runs.py` **3 passed**。
- **坑**：未提交；勿只擦学生包日志。切段真源 `frontend/.../jobLogRuns.js`；parity 测 `tests/fixtures/run_job_log_parse.mjs`。

领域与交叉长表 → [`docs/domains.md`](./docs/domains.md)。  
能力 cap 矩阵 → [`docs/capabilities.md`](./docs/capabilities.md)。  
开题密功能 / 待补 → [`docs/opening-feature-delivery-map.md`](./docs/opening-feature-delivery-map.md)。  
挂载/对齐门禁 → [`docs/opening-align-gate.md`](./docs/opening-align-gate.md) · 搁置 [`docs/parked-work.md`](./docs/parked-work.md)。  
UI 观感加厚 → [`docs/ui-look-thicken-batch.md`](./docs/ui-look-thicken-batch.md)。  
Vue 大文件拆分 → [`docs/vue-split-batch.md`](./docs/vue-split-batch.md)。  
起包前布局闸 → [`docs/ui-layout-prebake-gate.md`](./docs/ui-layout-prebake-gate.md)。  
可交互控件 → [`docs/form-controls.md`](./docs/form-controls.md)。  
全域 UI 诊断 → [`docs/ui-domain-diagnosis.md`](./docs/ui-domain-diagnosis.md)。  
域组 UI 选型 → [`docs/domain-group-ui-styles.md`](./docs/domain-group-ui-styles.md)。

---

## 接题边界（硬原则）

本产品定位：**专科 / 本科毕设、课设级别的 Web 管理系统生成**（演示级主路径），不是研究生平台，也不是真实业务交付。

| 接 | 不接 |
|----|------|
| **专科 / 本科** 毕设、**课设**（Web 管理、演示级） | **硕士研究生 / 博士研究生** 课题与开题 |
| 具名域薄壳单路径（密功能见地图 / 各组 thicken）；白名单内且 `defense_ready` 的交叉 | **真实业务全流程** / 生产级全链路 / 企业级端到端 |
| L0～L2 积木内可演示的功能 | L3、HIS/ERP 级发散、未就绪交叉 |

信号：`OUT_OF_SCOPE_SIGNALS`（硕博学位论文、真实业务全流程等）→ `reject`。  
分层细则 → [`docs/difficulty-tiers.md`](./docs/difficulty-tiers.md)。

---

## 开题场景 / 身份文案（硬原则）

**开题与材料为准，工厂跟场景走；禁止改开题迁就模板。**

| 约定 | 含义 |
|------|------|
| **单一真源** | `app/bake/scene_scan.py` → `scene_for(domain, title, proposal)` |
| **同场景同口径** | 壳 eyebrow/roles 与 `profileFields`（注册/资料页）必须读同一 scene |
| **扫词选分支** | 不是逐字复述开题；场景定了不得再写死冲突身份（如企业 CRM ≠ 学号/教职工） |
| **业务角色优先** | 背景里的「学院/校园」不压过正文里的「销售/客户跟进」等企业档 |
| **未写清用域默认** | 默认档在 builder / `PROFILE_FIELDS_BY_DOMAIN`，不是臆造开题 |

须分支域清单见 `SCENE_BRANCH_DOMAINS`。改 hint 只动 `scene_scan`，并补场景测试。

---

## 读什么（专题）

| 要查 | 文档 |
|------|------|
| 能力 cap / 挂载口径 | [`docs/capabilities.md`](./docs/capabilities.md) |
| 领域组 A–H（A～F 具名 → G 真交叉 → H 兜底） | [`docs/domains.md`](./docs/domains.md) |
| L0–L3 / 加价边界 | [`docs/difficulty-tiers.md`](./docs/difficulty-tiers.md) |
| 库表预算 / 角色不变式 | [`docs/invariants.md`](./docs/invariants.md) |
| **参数该落哪（yml ≠ 唯一去处）** | 规则 `.cursor/rules/param-placement.mdc` · `.trae/rules/param-placement.md`（口径同 [`docs/capabilities.md`](./docs/capabilities.md)） |
| 怎么审交付 | [`docs/delivery-audit-rules.md`](./docs/delivery-audit-rules.md) |
| 换皮 ID 册 | [`docs/domain-skin-gap-analysis.md`](./docs/domain-skin-gap-analysis.md) |
| 开题功能对照 | [`docs/opening-feature-delivery-map.md`](./docs/opening-feature-delivery-map.md) |
| §1.1～§1.5 加厚复盘（已收口） | [`docs/group-thicken-archives-1-1-to-1-5.md`](./docs/group-thicken-archives-1-1-to-1-5.md)（明细仍以地图为准；§1.6 起另有独立 batch 册） |
| §1.6 交易加厚批次（已收口） | [`docs/trade-thicken-batch.md`](./docs/trade-thicken-batch.md) |
| §1.7 预约加厚批次（已收口） | [`docs/reserve-thicken-batch.md`](./docs/reserve-thicken-batch.md) |
| §1.8 内容加厚批次（进行中） | [`docs/content-thicken-batch.md`](./docs/content-thicken-batch.md) |
| 域组 UI 表面选型 | [`docs/domain-group-ui-styles.md`](./docs/domain-group-ui-styles.md) |
| 起包前 UI 布局闸（全表） | [`docs/ui-layout-prebake-gate.md`](./docs/ui-layout-prebake-gate.md) |
| 学生包可交互控件（全包·可筛选、禁造库外值） | [`docs/form-controls.md`](./docs/form-controls.md) |
| 全域 UI 诊断表（68 域 L×C） | [`docs/ui-domain-diagnosis.md`](./docs/ui-domain-diagnosis.md) |
| AI 开题对照 | [`docs/ai-opening-delivery-map.md`](./docs/ai-opening-delivery-map.md) |
| 全索引 | [`docs/README.md`](./docs/README.md) |

宿舍样板账号见 [README.md](./README.md)「样例开题」节。

---

## 新对话开场（当前主线）

```
继续 graduate_factory_v3。先读 HANDOFF.md。
大线 #1 UI 诊断已收口（68 双 OK；布局/控件 BASELINE_KNOWN 空）。
下一主题另开；勿回抢已齐闸。#3+#4 全族已齐。
```

## 新对话开场（某个具名域）

```
继续 graduate_factory_v3。先读 HANDOFF.md。
目标：具名域 DOM-___（关键词：___）冒烟、文案/SQL 微调，或对照地图该组待补。
能力组合：___（对照 docs/capabilities.md + docs/domains.md）；密功能以 opening-feature-delivery-map 为准。
禁止内存 Store、禁止排除 DataSource、LLM 只填 schema；禁止新开厚 DOM 包。
```

---

## 专项交接：话术层（Surface Lexicon）修复 · 2026-09-26/27

> **设计稿（先读这份）**：[`docs/surface-lexicon-design.md`](./docs/surface-lexicon-design.md)
> 状态：**批 A ✅ / B1 ✅ / B2 ✅ / C ✅ 已落地**；重生成 goldens 与全量脚本已跑通。
> 未完成（运维步）：**库内 7 条 `gate_e2e` 需重新 bake 对应项目**（改素材/改门禁都不会回溯修旧工作区）。

### 触发与硬性要求

`gate_e2e`「交付质量摘要」连续 fail，两条均为**可见的错域/不一致文案**：

| # | 症状 | 证据 |
|---|---|---|
| 1 | CRM 分类轴：「分类标签」（开题正文）vs「客户分级」（实体 label/labelPlural）vs「按分级浏览客户」（banner）→ 三处口径不一 | `schema/builders_archive.py:449`（分类轴名）、`:457`（banner）、`proposal_packs_data/crm.json:11`（正文） |
| 2 | 事件上报域用户端空状态写「还没有**打卡**记录…」 | `schema/builders_archive.py:483`（`_event_self_report_overrides()`，同函数 `:470-490` 全为「打卡」） |

**需求方硬性要求（设计稿 §0）**：
1. **所有域都得吃到此次变更** → 只准改全域 choke point，禁止逐域补丁；
2. **修复后不可再出现同样问题** → 门禁等级 `error`、数据驱动、全域覆盖；A/B/B2/C **同批交付**；
3. 验收必须**脚本化全量**（74 个域包），不接受抽样。

### 根因一句话

既有零件齐全（`bake/ticket_copy_text.py` 单据文案生成器、`schema/er_zh.py` 表列词表、`proposal_lexicon.py` 扫词、`student_copy.py` 事后清洗、`delivery_review.py` 事后 gate），**缺的是把"页面级话术"（`banners`/`doc`/`auth_lead`/`my_tickets_*`/种子公告）统一串起来的解析层**，且 `proposal_lexicon` 只用于"判能力开不开"、从未用于"决定怎么说"。

### 已完成：批 A（素材口径对齐）

| 文件 | 改动 | 状态 |
|---|---|---|
| `proposal_packs_data/crm.json:11` | 「分类标签」→「**客户分级**」 | ✅ 与实体 golden 同词（`DOM-CRM.json` 命中） |
| `proposal_packs_data/event_report.json:11` | 「分类标签」→「**分类**」 | ⚠️ 依据是 `DOM-EVENT.json` L60/L61 的 `label/labelPlural`（域默认）；**精确串回校未命中，未经机器证实**，批 B 全量断言时一并确认 |

**验证已过**：两 JSON 解析通过；全仓 `分类标签` 零残留（仅设计稿引用原文）；pack 消费方测试 `test_proposal_diff / test_identity_align / test_cap4_delivery / test_form_first_residual / test_attend_scene` → **49 passed / 229 subtests** 与 **32 passed / 229 subtests** 两轮均绿。

**踩坑记录（重要）**：EVENT 的「**事件分类**」只存在于**部分场景皮**（`builders_archive.py:743/769/813/860`），域默认是「分类」。第一版曾误写「事件分类」，已改回。

### 批 B1 / B2 / C 计划表（**已全部执行**，落地与验证见下文「已完成」节）

| 序 | 内容 | 关键落点 |
|---|---|---|
| **B1** 话术层 | 扩展 `bake/ticket_copy_text.py` 为主干（`slot` + `DOMAIN_LEXICON` + `SLOT_PATTERNS` + `lex()/lex_all()`）；`followup_domain_schema()` 写 `schema["lex"]`；②来源 13+ 文件改读 `schema["lex"]`；`_event_self_report_overrides()` **槽位化**（治「打卡」：`还没有{ticket_noun}记录，点击右上角提交。`） | `schema/followup_presets.py`、`schema/builders_archive.py`、`schema/builders_ticket.py`、`schema/form_first_entry.py`、`oa/tail/stuwork/deep_skin/mutual/checkin/bed/carpool/instrument/timebank_*` |
| **B2** 渲染分支 | 通用前端组件补 `allow*` 保护（治 1014 / 12 / 6）：`row.dueAt/dueLabel/row.qty`（借阅/商城字段）、`hold_ready/holdCountdown/取书截止` | `skeletons/baseline/frontend/src/views/user/MyTickets.vue` 等，三栈同步 |
| **C** 门禁 | `bake/domain_vocab.py`（专属名词→归属域，数据驱动、全域）+ `services/delivery_review.py` 新增 **error 级**检查（跨域词 + 口径分叉 + 缺 `allow*`，现 `:340` 已挂「交付质量摘要」项）；补 `tests/test_delivery_review.py` 正反例 | 复核 `docs/delivery-audit-rules.md` 红灯表 |

**B1 解析优先级**：开题抽取（须落在本域允许集内）→ 域词表 → 域默认 override → 通用兜底。
**同义簇**：`category_axis = 分级|等级|评级|星级|档位|标签|类目|分类|类别`；`ticket_noun = 上报|填报|打卡|申报|申请|报修|登记|诉求|预约`。

**验收（缺一不可）**
1. **74 个域包**批量 bake → 断言：对专属名词表零命中、同一 slot 零口径分叉；
2. **反例必红**：EVENT 注入「打卡」→ error；CRM 注入「分类标签」→ error；`dueAt` 未加 `allow*` → error；
3. 现有全部域包产物 → gate 保持**绿**（零回归）；
4. goldens 重生成：`python tests/tools/regen_sql_goldens.py` + `tests/tools/regen_schema_goldens.py`；
5. 三栈 `mvn -o compile`（jdbc / mybatis / jpa）+ 现有 105 项门禁全绿；
6. `gate_e2e` 那 **7 条文案/可见面类**转绿（需**重新 bake** 对应项目，改素材不会回溯修旧工作区）。

**次批**：收紧 `scene_scan.EVENT_SELF_REPORT_HINTS`（配 74 域包"皮命中矩阵 before/after"）；`sql/domain_scene_seed.py`（145 KB）**公共模板同批、域特有分支分批**迁移。

**另立清单（不同源，勿并入本批）**：`shopMarketplace` 缺 `guestbookGuestCta / noticeGuestCta`；上传素材 `'utf-8' codec can't decode … invalid continuation byte`。

### 库内 bake 失败普查（实测，`jobs` 表）

`jobs.bake`：failed **12** / success 15；`projects`：failed 5 / generated 7 / ready 1。原文导出：`C:\Users\17386\AppData\Local\Temp\gf_bake_fail_reasons.txt`。

| 步骤 | 条数 | 判定 |
|---|---|---|
| `gate_e2e` | **7** | **同源家族**＝可见文案/可见面 vs 实体不一致（1010 打卡、1009 口径、1014/12/6 缺 `allow*`、1011/10 宣称 vs 实体）→ 本专项对症 |
| `copy_bake` | **5** | **不同源**：`DOM-SHOP` 16 表配额、`shopMarketplace` 缺 `guestbookCta`、上传素材 UTF-8 |

**「存量 vs 活跃」判据**：`[1001]/[1000]/[2]/[1]` 全属历史项目 `gf-20260911-033005`（9/11，存量）；**9/26–9/27 的 4 条新失败 100% 是 `gate_e2e` 文案类**＝当前活跃阻塞源。

**表配额真相（勿再误判）**：`engine_sql.py:33-39` → `MIN 6` / `TABLE_COUNT_MAX 15`＝**仅警告（注释原话"超过只警告，不拦出包"）** / `TABLE_COUNT_HARD 18`＝打回；开题扫入的必需表（`ESSENTIAL_CAP_TABLES`）**不计入 18**。实测 16/17/18 表均 `ok=True`（仅 warn），≥19 才打回。
→ 库里 `DOM-SHOP 16 表` 那条是**放开之前的旧记录**，那条消息在当前代码里已搜不到，**无需处理**。
→ 配额契约由 `backend/tests/test_table_budget.py:70-71` 钉死（`(15, 18)`），将来再动配额必须同步它。

### 已完成：批 B1 / B2 / C（2026-09-27）

| 批 | 落地 | 文件 |
|---|---|---|
| **B1 话术层** | 槽位解析层（`category_axis`/`ticket_noun` + 同义簇 + `{slot}` 占位符 + 单据壳归一化）；`followup_domain_schema()` 写 `schema["lex"]`，并把解析值写回 `archive_fields` 分类轴与门户轮播（分类菜单随字段自动跟随） | `bake/ticket_copy_text.py`、`schema/followup_presets.py`（全域 choke point） |
| **B1 事件皮** | `_event_self_report_overrides()` 全部改 `{ticket_noun}` 占位符：开题写「打卡/晨午检」才出「打卡」，否则跟本域单据名词（默认「上报」）；`_crm_schema` 三处 + `_event_schema` 已回传 `proposal_text` | `schema/builders_archive.py` |
| **B2 渲染分支** | 通用前端组件域外字段补 `allow*` 分支：`allowQty` / `showDueCols` / `showFineCols`（数量、到期、实发、罚金、领取行） | `skeletons/baseline/frontend/src/views/user/MyTickets.vue`（全仓唯一副本） |
| **C 门禁** | `domain_vocab.py`（专属名词→归属域逆向 forbidden + 三条 error 规则）；接入 `_structural_findings()` → `p3q`「交付质量摘要」挡包（无 LLM 也生效） | `bake/domain_vocab.py`（新）、`llm/agents_qa.py`、`docs/delivery-audit-rules.md`（H24） |

C 的三条规则（全数据驱动、全域覆盖，非逐 case）：

1. **跨域专属名词**：`_NOUN_OWNERS`（借阅/挂号/客房/查寝/寄养…）反向下发 forbidden；豁免本域实体词/槽位值/项目题名/划界否定语境。
2. **同 slot 口径分叉**：`ticket_noun` 只审单据壳（`myTicketsEmpty/PageLead/EmptyArchive` + `my_tickets` 菜单）；`category_axis` 只审分类菜单 + 门户轮播 + `category*` label；已覆盖的簇词（「分级」⊂「客户分级」）与本域自有词（「事件等级」）不算分叉。
3. **域外字段缺 `allow*`**：`dueAt/dueLabel/renewCount/qty/actualQty/holdExpireAt/hold_ready/fineYuan` 出现在 `.vue/.js` 且 ±6 行无 `allow*`/`hasCap` 分支 → error。

### 验证结果（本批实测）

```powershell
cd d:\graduate_factory_v3\backend
python tests/tools/check_surface_lexicon.py         # 74 域包全量：checked 69 packs, failed 0（4 个 DOM-GENERIC 交叉包无 builder，SKIP）
python -m pytest -q tests/test_surface_lexicon.py    # 14 passed（优先级/同义簇/3 条反例必红/baseline 渲染守卫）
python tests/tools/regen_schema_goldens.py           # 98 个 golden 重生成（含 SQL：另有此前存量漂移一并归位）
python tests/tools/regen_sql_goldens.py
mvn -o -q compile                                    # skeletons/baseline/backend → EXIT=0（本批未改一行 Java）
```

- 反例必红（已入单测）：EVENT 自报皮注入「打卡」（槽位为「上报」）→ error；CRM 注入「分类标签」→ error；`dueAt` 无 `allow*` → error；改为 baseline 真实文件后 → 零 finding。
- 相关黄金/文案测试批量复跑：`test_schema_builders_golden / test_domain_sql_golden / test_shells_archive_lead / test_attend_scene / test_checkin_c10 / test_cap4_delivery / test_identity_align / test_form_first_residual / test_proposal_diff / test_copy_h22 / test_student_facing_copy / test_qa_factory_drift / test_semantic_gates / test_oa_apply_p / test_tail_p / test_stuwork_p / test_mutual_c05 / test_domain_skin_leak / test_delivery_review / test_domain_column_forbid / test_table_budget` → **186 passed / 872 subtests**；另 33 个域/场景/皮测试文件 → **247 passed**。
- **存量红收口中（按载体口径，2026-09-27）**：`test_code_qr_e07::test_baseline_fe_and_dep` 原是**自相矛盾的过期断言**（要求 baseline `MyTickets.vue` 含「不对接闸机」，而该句已被 `domain_schema.py:758` 的 `FACTORY_UI_FORBIDDEN` 明令禁止上学生页面）。已按新载体口径修：页面断言改为 `assertNotIn`，新增 `tests/test_copy_carrier_contract.py`（学生可见面禁硬件纠葛词 / 工厂侧必须留划界语 / 同一句多载体逐字一致），并把 `CodeQrBlock.vue` 兜底与 `features/code_qr.py::CODE_QR_HINT_DEFAULT`、`domain_schema._LABEL_FALLBACKS["codeQrHint"]` 对齐为同句。**该族 9 条测试已全绿**（全量 suite 存量红由 16 → 15）。
- **全量 `pytest -q tests` 现状（本批前后一致，均非本批引入）**：`15 failed, 1260 passed, …`。其余失败集中在**已存在的存量漂移**：`test_chrome_theme`(2 主题 token/暗色对比)、`test_delivery_mark`(5：`projects.py:167` 直接读 `project.workspace_path`，测试用 `SimpleNamespace` 无该属性)、`test_upload_cluster`(3 聚类分组)、`test_schema_testcases`(mojibake 断言)、`test_core_cap_scan::test_asset_mounts_loan_deadline`、`test_compose_out_of_mvp`、`test_student_api_smoke::test_gate_fail_detail_uses_data_message`、`test_appoint_from_users::test_scene_blocks_property_media_event_lost`、`test_ai_assistant_bake`。**判据**：失败点都不在本批改动的调用链上（traceback 指向 `projects.py`/themes/testcases/cluster 等未改文件），且本批改的是「更严」的 error 门禁，不会把红转绿。
- **gate_e2e 7 条**：门禁与素材都已换用新口径，但旧工作区是历史产物 → 必须**重新 bake** 那几个项目（`jobs` 步骤 4+）才会转绿；未在本轮执行（会覆盖用户工程）。

### 与设计稿的偏差（如实记录）

1. `category_axis` 采用「**保留域限定前缀、只跟随开题簇词**」（客户分级 + 开题「评级」→ 客户评级），而非整词替换：避免把「费用类别」写成「分类」丢限定词。开题词不在簇内 → 回落域默认。
2. 只有 `_crm_schema` / `_event_schema` 把 `proposal_text` 传进 `followup_domain_schema`；其余 builders 仍走域默认（全域一致性由 C 门禁保证）。要全域跟随开题，需按 builders_archive 的 20+ 调用点逐个补 `proposal_text=`。
3. ④ 种子公告（`sql/domain_scene_seed.py` 145 KB）**未迁移**，按设计稿 §11.3 分批；本轮由 C 门禁兜底。
4. 次批原计划：收紧 `scene_scan.EVENT_SELF_REPORT_HINTS`（现 `_event_self_report_overrides()` 已槽位化，「打卡」不会再串到单据壳，词表收紧改为纯收窄皮判定，优先级下降）。

### 批 C 进展（2026-09-27）

| 子项 | 状态 | 说明 |
|---|---|---|
| **C1 全域跟随开题** | ✅ 完成 | `builders_archive.py` 的 **22 个** `followup_domain_schema()` 调用点补 `proposal_text=proposal_text`（此前只有 `followup_builder` 路径回传）。效果：这批域（ATTEND/FUND/LABSAFE/RECRUIT/PROCURE/DATING/GRADE/BED/INTERN/PARCEL 等）现在也按「开题簇词 → 域默认 → 兜底」解析话术，域默认仍兜底 |
| C2 ④ 种子公告迁移 | ⏳ 待办 | `sql/domain_scene_seed.py`（145 KB）：设计稿 §11.3 已定「公共模板同批、域特有分支分批」；本轮仍由 C 门禁兜底 |
| C3 ⑤ 前端空状态迁移 | ⏳ 待办 | 实测 baseline 前端 `还没有|暂无` 共 **90 行、40+ 个 .vue**（Top: ArchiveBrowse 10、MyTickets 4、SlotBook 4、PortalHome 3…）；需逐个映射到 schema label，属设计稿 §10「体量大、一次改不完」项 |

**C1 验证**：`check_surface_lexicon.py` → `checked 73 packs, failed 0`；goldens 重生成后与 C1 前**逐字节相同**（无新增 churn）；A 批 + C1 相关 **34 个测试文件 316 passed / 1227 subtests**。

**过程记录（踩坑）**：用脚本批量插 kwarg 时，自写的括号扫描没跳过注释里的 `)`，插错位置并一度破坏语法；改用 `tokenize` 精确定位跨度后修复，并补排版还原。**结论：这类批量改写必须用 `tokenize`/AST 定位，不要手写括号计数**（脚手架脚本已删）。


`bake/domain_vocab.py`、`bake/ticket_copy_text.py`、`bake/schema/followup_presets.py`、`llm/agents_qa.py`、`skeletons/baseline/frontend/src/views/user/MyTickets.vue`、`docs/delivery-audit-rules.md`。

### 环境与命令速查

```powershell
cd d:\graduate_factory_v3\backend
python -m pytest -q tests/<某个>.py                  # 单测（.pytest_cache 有权限告警，忽略）
python tests/tools/regen_sql_goldens.py              # SQL golden 重生成
python tests/tools/regen_schema_goldens.py           # schema golden 重生成
python -m app.bake.sample_proposal --list            # 测试开题 74 个域包
AOCI: "C:\Users\17386\tools\aoci\aoci.exe" verify|check --json ; index agent guide --agent cline --json
DB:  mysql+pymysql://root:****@127.0.0.1:3306/graduate_factory（见 backend 配置）
```

**临时脚本**（`C:\Users\17386\AppData\Local\Temp\`）：`gf_bake_fail.py`（探库）、`gf_bake_fail_dump.py`（导出+分桶）、`gf_table_budget.py`（配额实测）、`gf_testproposal.py`（测试开题→匹配→出包核对）。

### 陷阱（本会话踩过）

1. `Get-Content` 在 PS 5.1 对 UTF-8 文件会**误读成 ANSI**，行数/内容会失真（曾误判"文件被截断"）→ 用 `read_files` 或 `[IO.File]::ReadAllText(path,[Text.Encoding]::UTF8)` 复核；
2. `.NET` 相对路径按**进程 CWD**（VS Code 目录）解析，`cd` 无效 → 一律用绝对路径；
3. 递归扫 `backend` 会撞 `.pytest_cache` 权限拒绝 → 限定 `backend\app` / `backend\tests` 并加 `-ErrorAction SilentlyContinue`；
4. `search_codebase` 会被 `.aoci` 基线/草稿刷屏 → 改用 `Select-String` 限定目录；
5. MCP `desktop-commander` 单次调用上限 300s → 7 个包连编/全量 check（约 220s）要拆开跑。

### AOCI 收尾状态（2026-09-30，已收尾 ✅）

- **现状（机器事实，三绿）**：`verify --json` → `governance_aligned=true, result=aligned, next_required_action=none, findings=[]`；`check --json` → `ok=true, exit_code=0, next_action=none`；`index agent guide --agent cline --json` → `mode=complete, stage=aligned, complete=true, next_action=none, executable_targets=0, findings=[]`。code 卷 **1449** entry / database 卷 **4** entry、`managed_scope.index_count=1453`、drift 只剩 `.cursor/rules/aoci-post-delivery.mdc` 的 `line_ending_only`（无 stale / missing / orphan / unbaselined）。
- **本轮怎么收的**：09-29/09-30 的新改动（bake features、`sql/fragments.py`、skeletons、docs、AGENTS.md/HANDOFF.md）曾让基线落后 → `guide` 报 `stage=authoring_required, executable_targets=53`（49 条 `code_stale` + 2 条 `code_missing` 兼 `code_unbaselined`：`backend/app/bake/features/borrow_thicken.py`、`skeletons/baseline/frontend/src/utils/isbn.js`）；先 `aoci.exe scope acknowledge --reviewed-by cline --json` 清零 `observed_pending_review`，再分 3 轮 `maintain → update_entry` 把候选全部 applied，`remaining=0`。
- **为什么曾反复**：09-27 那轮 24 条已 applied 并曾回 `aligned`，但此后每批新改动都会让相关条目重新 stale——这是 AOCI 的正常机理，不是故障。
- **再编辑即失效（仍然成立）**：任何受管文件（含本文件）被改动都会让该条回到 stale，必须重走 `scope acknowledge`（领批前）→ `maintain` → `update_entry` → `verify/check/guide`；`remaining` 归零前不得声称 Whole-Index aligned。**这次收尾后再改本文件，就会重新落回 `authoring_required`**。
- **领批纪律（仍然成立）**：无参 `aoci_maintain` 领批，单批上限 `code_cognition_batch_entries=20`；提交要带 `code_batch_id` + 每项 `candidate_id` / `source_sha256`，且必须是该批次**完整**候选集合（不许截子集、不许字段 patch）；`repair_required` 只修 `retry_scope` 后重提同一批次。
- **一个退出码陷阱**：`scope acknowledge --reviewed-by <agent> --json` 可能以非 0 退出码返回，判定只看输出里的 `status` / `observed_pending_review`，不要看 exit code。
- **成本实测**：`whole_index_tokens`≈79,868 / target 200,000（healthy，每次编辑后小幅浮动），`overview_delivery.chunk_tokens=16000`；`cognition_budget` 只能经 `aoci scope budget set` + Scope Change Apply 修改，手改 `.aoci/config.json` 不会被采纳（AGENTS.md 已同步更正）。
- **本机体积**：`.aoci` 实测 **272.9 MB**，几乎全在 `transactions` / `governance` / `drafts` 等本机运行产物；`.aoci/.gitignore` 用 `*` + 白名单（`baseline.json`、`config.json`、`curation.json`、`database-baseline.json`）把它们挡在 Git 外，可安全清理。

- **两条实测经验**：
  1. **S 字段机器 token 上限比 Meta 表格更严**：C6/C7 对象实测上限 **80 tokens**（≈240 UTF-8 字节，中文≈80 字），超了会 `entry_field_budget_exceeded` → 按 finding 压缩重写整个字段（不许机械截断），然后**重提同一完整批次**。
  2. **每次改动文件后 guide 会回到 `observed_pending`**：作者化前若又编辑了任何文件（含 `tests/tools/*`），需再跑一次 `scope acknowledge --reviewed-by cline` 才能领到候选批次。

- 认知效力（09-27 那轮）：Overview 交付被 Host 中段截断 → `model_attestation=partial`（Challenge 3/10）；按合同不做无保留的「完整系统认知」声明，但 source-bound 工程不受限。想恢复完整认知：`overview_delivery.chunk_tokens` 降到 4000 重跑。

### C2 第一步：种子公告纳入门禁（2026-09-27）

种子公告（`sys_notice`）由 `sql/domain_scene_seed.py` 等**手写**、随 DDL 插进学生包，是可见文案的第四个来源；此前没有任何门禁。

- **判据**：`domain_vocab.notice_slot_findings(sql, schema, domain=)` —— 只在**名词位置**判分叉（`提交X / 我的X / X单 / X记录 / 办理X / X已开放 / X通过后 / 还没有X`，分类轴另用 `按X浏览 / X管理`），避免把「如实登记联系结果」「预约面试」这类**动词用法**误杀；同时查跨域专属名词。
- **上线**：`lexicon_findings(..., seed_sql=)` → `agents_qa._collect_qa_context` 读 `workspace/sql/*.sql` → 进 `p3q`「交付质量摘要」（error 级挡包）。
- **全量实测**：87 条公告，初筛 10 处 → 收敛到 **3 处真分叉**（其余 7 处是动词用法）；已修字面量 2 处（EQUIP 种子「办理领用与归还」→「办理**借用**与归还」，`domain_scene_seed.py:921/1105`）。
- **显式登记（不是静默放过）**：`SEED_NOTICE_KNOWN_PENDING` 记 3 条待 C2 迁移项，迁移时删掉就会被门禁要求一致：
  1. `DOM-FUND`「申报」← 公告「奖助学金申报已开放」由 f-string 拼出；
  2. `DOM-VISITOR`「预约」← 公告「预约通过后出示通行码」同上；
  3. `DOM-EQUIP`「领用」←「开放时间」公告由 `builders_archive.py:256` banner 合成。
- **新测试**：`tests/test_seed_notice_lexicon.py`（74 域零命中 + 2 条反例必红）；新脚本 `tests/tools/check_seed_notice_lexicon.py`、`list_notices.py`、`dump_lex.py`。

**同时自查出并修掉 B1 两个真缺陷**（由这次普查暴露）：

1. 单据壳归一化会造叠词（「点击右上角**归寝归寝签到**」）→ `normalize_slot_words` 增加「前后缀已含解析值首尾」保护；
2. 槽位取错概念：DOM-CHECKIN 的票据标签是「归寝签到」（口令签到），而域自己的话术是「归寝登记」（提交动作）→ `preset_slots` 改为**优先采信域自己单据壳话术里的复合名词**，且材料里的通用簇词不得覆盖它（`copy_authoritative_noun`）。

### C3 结论修正：前端空状态**不需要迁移**（2026-09-27）

原判断（设计稿 §2.1 ⑤「12+ 页写死空状态」）实测**不成立**，两点证据：

1. 学生可见页面（`views/user/**`、门户壳）的空状态**早就走 `labels.*` + schema**，那 90 处「还没有/暂无」绝大多数是**取不到标签时的兜底句**，不是另一套说法；
2. 剩余的写死文案全部落在**能力岛专属页**（`BuybacksAdmin`/`LessonPacksAdmin`/`LossAdmin`/`FrontCare…`/`FundDisburse…`/`CareOptions` 等）：岛不开不挂载，其用语（回收单/课时包/赔付/登记入住/预约队列）是**该岛的功能词**，不构成跨域错词；实测「共享页面里写死域词」命中 **0**。

→ 因此 C3 从「迁移 90 处」降级为「**可选**的进一步收敛」（若要更严，把岛页文案也改走 `schema.labels`）。
→ 真正需要保留的门禁是**兜底句与 schema 默认句同源**（codeQrHint 就是这个坑，已修）；这条由 `test_code_qr_e07::test_code_qr_hint_same_text_on_every_carrier` + 载体口径三测覆盖。

## 专项：存量测试红清零（批 A，2026-09-27）

> 目标：让全量 `pytest` 回到 **0 红**，否则「零回归」无法证明、真红会被噪声淹没。逐条先定性「谁的契约过期」，再改最小一侧。

| # | 症状 | 定性（实测判据） | 修法 | 文件 |
|---|---|---|---|---|
| 1 | `test_delivery_mark` 5 红（`AttributeError: SimpleNamespace has no workspace_path`） | 实现侧过硬：`delivery_block_reason` 直接读 `project.workspace_path`，测试桩用 `SimpleNamespace` | 改防御式读：`getattr(project, "workspace_path", "")` | `app/services/projects.py:167` |
| 2 | `test_schema_testcases::testcase_model` setup ERROR（mojibake 断言） | **pytest 收集事故**：`testcase_model` 被 `from ... import` 进来，名字匹配 `test*` → 当测试函数收集（缺参→fixture 解析失败） | 别名导入 `as build_testcase_model`（顺带放出 5 条被遮蔽用例） | `tests/test_schema_testcases.py` |
| 3 | `test_chrome_theme` 2 红（缺 token / 深色 accent 过浅） | 真缺陷：`doclib.css`/`vote.css` 还在用**旧 token**（`--bg/--accent/…`，全前端已无人消费）→ 这 8 套主题**实际不生效** | 迁到 portal token 套装（`--portal-scheme/mix/bg/ink/…`）；`cinema-night` accent `#d49448`(lum .61) → `#a87b3c`(lum .50) | `skeletons/baseline/frontend/src/styles/themes/{doclib,vote,cinema}.css` |
| 4 | `test_upload_cluster` 3 红（同课题未合并） | 规则过硬：卫星（功能清单）挂靠时被**能力指纹冲突**否决；清单的功能词天然与开题正文不同 | 指纹冲突只用于「题名不像」：`if _fps_conflict(...) and not title_ok: continue` | `app/services/upload_cluster.py` |
| 5 | `test_core_cap_scan::test_asset_mounts_loan_deadline` | 规则过硬：非 LIBRARY/EQUIP 一律「只补 due_at」→ 领用逾期罚款无 `fine_yuan` 落点 | 新增 `_LOAN_SHELL_DOMAINS=(LIBRARY, EQUIP, ASSET)`：领用/借用族开借阅期即完整壳；SLA 型仍只补 due_at | `app/bake/ticket_columns.py` |
| 6 | `test_compose_out_of_mvp::test_attach_accept_writes_composed_out_of_mvp` | 实现退化：docstring 写「该词/**片段**即相关」，代码只剩整词/斜杠片段；题面「人脸**识别**」匹配不到默认项「人脸**考勤**」 | 补 `_default_item_related()`：整项/斜杠片段/词干片段（片段须含 CJK 或 ≥3 位 ASCII，如 GPS/ATS） | `app/bake/capabilities.py` |
| 7 | `test_appoint_from_users::test_scene_blocks_…` | **测试快照过期**：`staff_posts.py:206` 明写「MEDIA 默认双角色，开题写编辑/权限划分才挂 content_ops」 | 断言改为：校园无角色材料 → False；校园+「运营编辑/权限划分」→ True；商业仍 False | `tests/test_appoint_from_users.py` |
| 8 | `test_ai_assistant_bake::test_all_ai_skins_…`（1/50 皮） | **测试快照过期**：书皮问句已由「续借与逾期怎么办」改为「**逾期与催还怎么办**」（与产品 `deadline_label=逾期催还` 同词） | 更新该快照（其余 50 皮逐条比对无差异） | `tests/test_ai_assistant_bake.py` |
| 9 | `test_student_api_smoke::test_gate_fail_detail_uses_data_message` | **测试桩缺契约**：gate 自检只在「单据主链域」跑（`_ticket_flow_keys`），桩只给 `{"domain": …}` → 整步 skip，测不到 detail | 桩补 `gate.flow_api{apply,approve,return}` | `tests/test_student_api_smoke.py` |

**遗留说明**：`PermissionError: Temp\pytest-of-*` / `WinError 145 目录不是空的` 是**并发 pytest 抢临时目录**的环境噪声（单跑即绿）；复跑请用独立 `--basetemp`，别并行开两个 pytest。

### 新对话开场（话术层专项）

```
继续 graduate_factory_v3。先读 HANDOFF.md「专项交接：话术层修复」与 docs/surface-lexicon-design.md（含 §0 硬性要求、§12 库内普查）。
已完成批 A（两条素材口径）；现在按顺序做 B1 话术层 → B2 allow* 渲染分支 → C error 级门禁，同批交付。
硬约束：所有域都吃到（只改 choke point）、修复后不可复发；验收＝74 域包全量脚本 + 反例注入必红 + goldens 重生成 + 三栈编译 + 105 门禁 + gate_e2e 7 条转绿。
```
