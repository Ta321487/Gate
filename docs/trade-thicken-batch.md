# §1.6 交易组加厚批次（已收口档案）

> **本文只负责**：地图 [`opening-feature-delivery-map.md`](./opening-feature-delivery-map.md) §1.6「本组待补」的**分批实现顺序、挂载口径、验收勾选**。  
> **不负责**：cap 定义（[`capabilities.md`](./capabilities.md)）；怎么审交付（[`delivery-audit-rules.md`](./delivery-audit-rules.md)）；清待补工序纪律（`.cursor/rules/opening-group-delivery.mdc`）。  
> **状态**：**已收口档案**（T-00～T-11 均已齐）。地图 §1.6 待补仅留「小票打印≠已齐」与不支持项。  
> **索引**：[README.md](./README.md) · 地图 §1.6 · 范本 `approve_thicken` / `apply_thicken`。

---

## 0. 硬口径（写代码前先背）

### 0.1 一组一包

| 规则 | 含义 |
|------|------|
| **组模块** | `backend/app/bake/features/trade_thicken.py` + `apply_trade_thicken_to_spec` |
| **注册** | 必须挂进 `backend/app/bake/domain_schema.py`（漏注册 = 死代码 = 未交付） |
| **域集合** | `TRADE_DOMAINS = {DOM-SHOP, DOM-FOOD, DOM-CINEMA}` |
| **不抢邻组** | HOTEL / CARRENT 虽有 `order_lines`，加厚归 §1.7 预约；本组不写其域皮 |
| **Store 主战场** | `OrderStore` / `AddressStore` / Cart 相关页面；**不是** `TicketStore` |
| **一轮只清本组** | 禁止同轮动 §1.7+；禁止只改地图不改骨架 |

### 0.2 一条待补 = 四件套 + 三骨架

硬口径：**管理端能管 + 用户端可产生数据（真写库）**。纯 Hint / 只读 / 打印 / 前端零读取字面量 → 不得标已齐。

| 件 | 真源 |
|----|------|
| ① 表 / 列 | `skeletons/baseline/sql/schema.sql`（+ 既有 `ensure_*` / inject） |
| ② Store 写方法 | `OrderStore` 等（三套骨架同改） |
| ③ API | `OrderController` 等 |
| ④ 前端控件 | `user/` + `admin/`（及 staff 若需要） |

三骨架：`baseline` · `persistence-mybatis` · `persistence-jpa` 的 Store / Binder / 必要时 Mapper 同绑。

### 0.3 挂载：域默认 vs 扫词加深

| 类型 | 何时开 | 地图「挂载」列 |
|------|--------|----------------|
| **三域通识底** | SHOP/FOOD/CINEMA（或 SHOP+FOOD）主路径刚需 | **域默认** |
| **能力岛加深** | 仅当已挂对应 cap（coupon / group_buy / flash_price / blind_box / points / member_tier / spend_discount / order_review / line_custom 等） | 扫词挂 cap 时 |
| **禁止** | 因「商城常见」把券/拼团/盲盒做成 SHOP 永远开 | — |

复用优先：`order_extras`（超时/评价/限时购）、`line_custom`、`code_qr`、`browse_history`、售后壳附带路径——**加深原文件，禁止平行第二套订单状态机**。

### 0.4 不支持（不进待补实现）

| 边界 | 原因 |
|------|------|
| 完整 SKU 多规格库存矩阵 | 独立库存引擎；浅二维规格分记可做，完整矩阵不支持 |
| 微信/支付宝商户清算 | 系统内支付 + 余额/支付密码顶 |
| 原生小程序包 | 无对应物理骨架 |
| 实时运单调度 / 独立骑手 App | 骑手岗扫词开；≠美团调度 |
| 堂食叫号大屏 | 地图已标不支持；桌号/取餐号顶 |
| 直播带货 / 电子发票税控 / 快递 100 | 超纲 |

### 0.5 每批工序（固定）

```
1. trade_thicken：开关 / labels / 域默认或扫词条件
2. schema.sql + ensure 列（多行用子表，禁止 JSON 冒充三范式）
3. OrderStore（及 Address/Cart）写方法 — 三套同改
4. Controller API — 三套 DomainRuntimeBinder 同绑
5. 用户端写控件 + 管理端管控件（文案无工厂腔）
6. 八张材料：受影响的 schema 测试一起看；菜单外功能不进图
7. 三绿才迁行：
   - pytest backend/tests/test_opening_map_skeleton_gate.py -q
   - pytest backend/tests/test_trade_thicken_features.py -q
   - 受影响的 backend/tests/test_schema_*.py
8. 地图：待补 →「本组本轮已齐」；本册状态改已齐；changelog 一行
9. 业务稳定后 AOCI maintain（新 .py 先 scope acknowledge）
```

单批体量：**约 5～8 条**；含子表/状态机时砍到 4～5。

### 0.6 已有半截优先钉齐（忌重写）

| 待补表述 | 现网线索 | 策略 |
|----------|----------|------|
| 订单备注 | `orders.remark` + 下单入参 | 钉 labels + 双端可见；缺则补列 |
| 默认地址一键 | `AddressStore.isDefault` + `Addresses.vue` | 确认闭环 + 门禁真读 |
| 口味备注 | `taste_note` | FOOD 快捷选项 + labels |
| 订单超时未付取消 | `order_extras` + `DemoScheduleJobs` | **钉口径/门禁**，禁止第二套超时 |
| 取票码 | `pickup_code` | CINEMA 展示；可叠 `code_qr` |
| 售后原因 | `refund_reason` | 必填/分类加深，不另起平行列 |

---

## 1. 批次总表

> **状态列**：`待写` → `实现中` → `已齐`（须过 §0.5 三绿 + 地图迁行）。中断后续写只改状态与勾选，不删行。

| 序 | ID | 主题 | 条数约 | 主要落域 | 状态 |
|----|-----|------|--------|----------|------|
| 0 | **T-00** | 脚手架：`trade_thicken` + `domain_schema` 注册 + `test_trade_thicken_features` | — | 工厂 | **已齐** |
| 1 | **T-01** | 钉已有：备注 / 默认地址 / 口味快捷 / 超时关单 / 取票码 | 5 | 三域 | **已齐** |
| 2 | **T-02** | 购物车 UX：全选清理 / 失效勾掉 / 改规格 / 凑单提示 | 4 | SHOP·FOOD | **已齐** |
| 3 | **T-03** | 订单主规则：锁库存回补 / 确认收货超时 / 邀评信 / 销售日报 / 改地址 / 小票打印 | 6 | 三域 | **已齐**（小票打印壳已挂，地图不迁） |
| 4 | **T-04** | 售后闭环：原因分类占比 / 原因必填 / 仅退款·退货分流 / 物流单号 / N 天可售后 / 进度时间轴 | 6 | SHOP·FOOD | **已齐** |
| 5 | **T-05** | 售后扩展+物流：换货 / 仅换货 / 轨迹手填 / 部分发货 / 分享口令 / 收货码核销 / 延保 | 7 | SHOP | **已齐** |
| 6 | **T-06** | 影院：退票截止 / 选座倒计时 / 连座提示 / 售罄关售 / 观影须知 / 座属性 / 特效厅 / 手续费 / 周视图 / 连场说明 | 10 | CINEMA | **已齐**（T-06a + T-06b） |
| 7 | **T-07** | 点餐：桌号取餐号 / 餐具打包包装费 / 营业时段禁单 / 骑手回池 / 配送费与送达 / 必选品类 / 拼单 / 档口分排序 | 9 | FOOD | **已齐** |
| 8 | **T-08** | 发票+规则文案：抬头/状态/PDF 占位；满减满赠互斥；原路退回；会员日说明 | 8 | SHOP | **已齐** |
| 9 | **T-09** | 商品侧：缺货到货 / 上下架定时 / 好评率晒图追评 / 足迹 / 浅规格库存 / 详情问答 / 预售说明 | 9 | SHOP·FOOD | **已齐** |
| 10 | **T-10** | 能力岛加深：券/拼团/限时购/盲盒/积分/会员价（**仅 cap 已挂时**） | ~12 | SHOP·CINEMA | **已齐** |
| 11 | **T-11** | 影院卖品加购+库存扣减；SHOP 包装费；扫尾清零 | 余量 | CINEMA+SHOP | **已齐** |

**推荐编码顺序**：T-00 → T-01 → T-02 → T-03 → T-04 → T-05，再按开题压力在 T-06 / T-07 间二选一优先，其后 T-08 → T-09 → T-10 → T-11。

可并行（不同 Store 触点、互不改同一状态机时）：T-06 ∥ T-07；T-08 文案项 ∥ T-09 前半（缺货/足迹）。

---

## 2. 分批明细

### T-00 脚手架

| 勾选 | 项 |
|------|-----|
| ☑ | 新建 `backend/app/bake/features/trade_thicken.py`（`TRADE_DOMAINS`、硬约束注释、`apply_trade_thicken_to_spec`） |
| ☑ | `domain_schema.py` 注册调用（紧接 `approve_thicken` 之后） |
| ☑ | `backend/tests/test_trade_thicken_features.py`：只动三交易域、不碰审批/报名/借用语义 |
| ☑ | 地图 §1.6 增加「本组本轮已齐」；changelog 记 T-00/T-01 |

**验收**：pytest 绿；T-01 迁行 5 条。

---

### T-01 钉已有字段

| 地图待补 | 落点建议 | 挂载 |
|----------|----------|------|
| 订单备注（用户下单留言给商家） | `remark` + `labels.orderRemarkLabel` 等 | **域默认** SHOP/FOOD |
| 收货地址「默认地址」一键 | `AddressStore` / Addresses 双端 | **域默认** SHOP/FOOD |
| 口味备注快捷选项 | `taste_note` + 快捷 chips | **域默认** FOOD（SHOP 可选） |
| 订单超时未付自动取消 | 复用 `order_extras.order_timeout_minutes` + 定时任务 | 扫词或 marketplace/demoPay 既有逻辑；三域门禁钉读 |
| 取票码展示 | `pickup_code` 订单展示 | **域默认** CINEMA |

**硬约束**：不新建第二套超时；不改支付商户边界。**已齐**（2026-10-06）。

---

### T-02 购物车 UX

| 地图待补 | 落点建议 | 挂载 |
|----------|----------|------|
| 购物车全选 / 失效商品清理 | Cart.vue + 必要 API | **域默认** SHOP/FOOD |
| 购物车失效自动勾掉 | 同上 | **域默认** SHOP/FOOD |
| 购物车改规格（有则换无则提示） | Cart 行操作 | **域默认** SHOP |
| 购物车凑单提示（差 N 元包邮） | 文案+阈值（档案或 AppPolicy） | **域默认** SHOP；浅 |

**硬约束**：全选必须经 `itemIds` 进入 `placeOrder`；改规格=同名在售兄弟行，禁止宣称 SKU 矩阵。**已齐**（2026-10-06）。

---

### T-03 订单主规则

| 地图待补 | 落点建议 | 挂载 |
|----------|----------|------|
| 下单锁库存 / 取消回补 | OrderStore ↔ stock/quota 对齐 | **域默认** SHOP/FOOD |
| 确认收货超时自动完成 | 定时或登录扫；配置分钟数 | **域默认** SHOP |
| 订单完成自动邀评站内信 | 完成态触发；须 `order_review` | 挂评价时 |
| 销售日报简表 | 管理端 GET 按日聚合/导出 | **域默认** SHOP/FOOD |
| 订单改地址（未发货） | 状态闸 + 写库 | **域默认** SHOP |
| 订单小票浏览器打印 | 共用 print 壳 | **域默认** 三域 |

**硬约束**：锁库存禁止假成功超卖；定时对齐 `DemoScheduleJobs` 风格。**已齐**（2026-10-06；小票打印壳已挂，地图因打印≠已齐不迁）。

---

### T-04 售后闭环

| 地图待补 | 落点建议 | 挂载 |
|----------|----------|------|
| 售后原因分类 + 简单占比图 | 原因字典 + 工作台饼/柱 | **域默认** SHOP/FOOD |
| 退款/售后原因必填 | `refund_reason` 校验 | **域默认** SHOP/FOOD |
| 售后仅退款 / 退货退款分流 | 类型字段 | **域默认** SHOP |
| 退货物流单号回填 | 售后字段；用户或商家写 | **域默认** SHOP |
| 收货后仅 N 天可申请售后 | 规则+阈值 | **域默认** SHOP |
| 售后进度时间轴 | 对齐报修时间轴浅做 | **域默认** SHOP |

**硬约束**：加深 `refund_*` 与 `requestRefund`，禁止第二套售后状态机。**已齐**（2026-10-06）。

---

### T-05 售后扩展 + 物流发货

| 地图待补 | 落点建议 | 挂载 |
|----------|----------|------|
| 售后换货流程（浅状态） | 类型扩展 | **域默认** SHOP |
| 售后仅换货不退款选项 | 类型 | **域默认** SHOP |
| 物流轨迹演示节点（手填） | 多行子表或节点列；≠快递 100 | **域默认** SHOP |
| 订单部分发货登记 | 状态加深 | **域默认** SHOP |
| 订单分享口令（只读查单） | 字符串码 | **域默认** SHOP/FOOD |
| 订单收货码核销 | code_qr 思路 | **域默认** SHOP/FOOD |
| 订单延保登记 | 字段 | **域默认** SHOP |

学生可见面写「物流进度」，禁止「演示物流」。

**已齐**：`refund_type` 扩 exchange/exchange_only（通过后不关单）；`order_ship_node` 子表；`partial_ship`/`share_token`/`warranty_until`/`receive_verified_at`；三套 OrderStore + 双端写库；登录页凭口令查单。

---

### T-06 影院

| 地图待补 | 落点建议 | 挂载 |
|----------|----------|------|
| 影院退票截止规则 | schema N 分钟 + 校验 | **域默认** CINEMA（T-06a 已齐） |
| 影院选座倒计时释放 | 占座超时 | **域默认** CINEMA（T-06a 已齐） |
| 连座推荐（相邻空位提示） | UI 提示；≠高并发锁 | **域默认** CINEMA（T-06a 已齐） |
| 场次售罄自动关售 | stage ↔ stock | **域默认** CINEMA（T-06a 已齐） |
| 观影须知勾选 | 须知变体 | **域默认** CINEMA（T-06a 已齐） |
| 情侣座/残疾人座标记 | 座位属性 | **域默认** CINEMA（T-06b 已齐） |
| 特效厅标记（IMAX 文案） | 场次属性 | **域默认** CINEMA（T-06b 已齐） |
| 退票手续费登记 | 金额字段 | **域默认** CINEMA（T-06b 已齐） |
| 排片日历周视图 | 管理/用户 UI | **域默认** CINEMA（T-06b 已齐） |
| 连场套票说明 | 只读规则文案 + labels 真读 | **域默认** CINEMA（T-06b 已齐） |

**T-06a 已齐**：`ticketRefundCutoffMinutes` / `seatHoldTimeoutMinutes`；`cinema_seat.hold_until`；`orders.notice_agreed`；三套 SeatStore + DemoScheduleJobs 释放占座；SeatMap 勾选须知写库。

**T-06b 已齐**：`cinema_seat.seat_attr`（情侣/无障碍）+ ArchiveAdmin 编辑；场次 `categoryName` 特效厅徽章；`orders.refund_fee_yuan` 双端登记；SeatShows 列表/周视图切换；`cinemaCombo*` labels 真读。

---

### T-07 点餐

| 地图待补 | 落点建议 | 挂载 |
|----------|----------|------|
| 堂食桌号 / 取餐号展示 | 下单字段+小票 | **域默认** FOOD |
| 餐具/打包选项 | 下单字段 | **域默认** FOOD |
| 包装费选项 | 下单字段 | **域默认** FOOD（SHOP 可选，仍待补） |
| 档口营业时段外禁下单 | 对照营业时间 | **域默认** FOOD |
| 骑手接单超时自动回池 | 状态规则 | 扫词挂骑手时 |
| 外卖配送费阶梯说明 | 文案+规则 | **域默认** FOOD |
| 外卖预计送达时间文案 | 字段；≠调度 | **域默认** FOOD |
| 点餐必选品类校验 | 规则 | **域默认** FOOD |
| 点餐拼单（同桌合并） | 浅合并；≠美团拼单 | **域默认** FOOD |
| 档口评分排序 | 聚合 | **域默认** FOOD |

**不实现**：堂食排队取餐号叫号大屏（地图不支持）。

**T-07 已齐**：`orders.table_no` / `pickup_code` / `utensil_opt` / `pack_opt` / `packaging_fee_yuan` / `delivery_fee_yuan` / `eta_text` / `merge_code`；`archive.open_hours` / `stall_score`；`categories.required_pick`；`ensure_food_thicken_sql`；三套 OrderStore/ArchiveStore + claimRider / releaseTimedOutRiderClaims + DemoScheduleJobs；Cart / CategoriesAdmin / MyOrders / OrdersAdmin / StaffOrders / 小票真读。

---

### T-08 发票 + 只读规则文案

| 地图待补 | 落点建议 | 挂载 |
|----------|----------|------|
| 发票抬头登记 | 订单备注级字段 | **域默认** SHOP |
| 发票申请状态 | 申请中/已开 | **域默认** SHOP |
| 订单发票下载占位 | 固定模板 PDF；≠税控 | **域默认** SHOP |
| 满减叠加说明页 | `spend_discount` 帮助 | 挂满减时 |
| 满赠说明 | 只读规则 | **域默认** SHOP 或扫词 |
| 优惠券互斥说明页 | 文案 | 挂券时 |
| 退款原路退回说明 | 系统内余额口径 | **域默认** SHOP/FOOD |
| 会员日折扣说明 | 文案 | 挂 `member_tier` 时 |

文案项须 `labels.*` 被 baseline 前端真读，防 Hint 假齐。

**T-08 已齐**：`orders.invoice_title` / `invoice_status`；`updateInvoice` + PUT `/api/orders/{id}/invoice`；Cart 抬头写库；MyOrders 申请/下载；OrdersAdmin 标记已开；`orderInvoicePrint` 演示壳；满减/满赠/券互斥/原路退回/会员日 labels 真读。≠税控。

---

### T-09 商品侧

| 地图待补 | 落点建议 | 挂载 |
|----------|----------|------|
| 缺货登记 / 到货通知 | 轻表 + 站内信 | **域默认** SHOP |
| 商品到货订阅（再次） | 上条加深 | **域默认** SHOP |
| 商品上下架定时 | 日期字段+任务或登录扫 | **域默认** SHOP/FOOD |
| 商品好评率展示 | 聚合计数 | **域默认** SHOP/FOOD |
| 评价晒图 | `order_review` 附件槽 | 挂评价时 |
| 商品评论追评 | `order_review` 加深 | 挂评价时 |
| 商品浏览足迹 | 对齐 `browse_history` | **域默认** SHOP 或扫词 |
| 商品规格库存分记（浅二维） | 有限规格；≠完整 SKU | 扫词或浅域默认；完整矩阵仍不支持 |
| 商品详情页问答 | guestbook 深皮 | **域默认** SHOP 或扫词 |
| 商品预售定金尾款说明 | 文案+状态 | **域默认** SHOP；浅 |

**T-09 已齐**：`ensure_catalog_thicken_sql`（shelf_on/off、presale_note、stock_notify、order_review 晒图追评、guestbook.item_id）；`StockNotifyStore` 三套；`ArchiveStore.applyShelfSchedule` / `listSiblingSpecStock`；好评率聚合；ArchiveBrowse / MyOrders / MyOrderReviews 真读；SHOP 域默认挂 `browse_history`。≠完整 SKU 矩阵。

---

### T-10 能力岛加深（扫词才开）

| 依赖 cap | 地图待补 |
|----------|----------|
| coupon | 核销码（订单展示）、领取中心页、过期站内信 |
| group_buy | 拼团进度条、失败自动退款说明 |
| flash_price | 限时购倒计时展示 |
| blind_box | 盲盒中赏记录页 |
| points | 积分明细流水页、兑换运费说明、影院积分兑票说明 |
| member_tier | 影院会员价说明（会员日见 T-08） |

**硬约束**：未挂对应 cap 时包内无菜单/无按钮/无 README 段落。

**T-10 已齐**：挂 cap 时钉 labels/`thicken.*`；券核销码+领券中心文案+过期站内信；拼团进度条与失败退款说明；限时购倒计时文案；盲盒中赏记录页；积分明细页与运费说明；影院会员价/积分兑票说明。未挂 cap 无入口。

---

### T-11 卖品 + 扫尾

| 地图待补 | 落点建议 | 挂载 |
|----------|----------|------|
| 影院卖品加购 | `cinema_snack` + `order_line.line_kind=snack`；SeatMap / ArchiveAdmin | **域默认** CINEMA |
| 影院卖品库存扣减 | 下单扣减、取消/售后回补 | **域默认** CINEMA |
| SHOP 包装费 | `packaging_fee_yuan` + Cart 勾选（复用 FOOD 列契约） | **域默认** SHOP |
| （余量） | 小票打印仍待补（打印≠已齐）；叫号大屏不支持 | — |

**T-11 已齐**：三套 SeatStore/OrderStore + SeatController；SeatMap 加购、ArchiveAdmin 维护；SHOP Cart 包装费；≠独立卖品域。

收口检查：

| 勾选 | 项 |
|------|-----|
| ☑ | §1.6「本组待补」仅剩小票打印（打印≠已齐）与叫号大屏不支持 |
| ☑ | 不支持段含：SKU 矩阵、商户支付、小程序、实时调度、直播、叫号大屏 |
| ☑ | 地图 changelog 有 T-00～T-11 收口行 |
| ☑ | `test_opening_map_skeleton_gate` + `test_trade_thicken_features` 绿（本轮验收） |
| ☑ | 本册总表状态全部 **已齐**；文首改为「已收口档案」口径 |

---

## 3. 材料可见性（八张）

本轮动订单/售后/选座/购物车时，优先核对：

| 材料 | 测试 |
|------|------|
| 用例图 / 用例描述表 | `test_schema_usecases.py` · `test_schema_usecase_descriptions.py` |
| 序列图 / 活动图 | `test_schema_sequence.py` · `test_schema_activity.py` |
| 软件测试用例 | `test_schema_testcases.py` |
| 功能模块图 / 类图 | 有新菜单或实体时看 |

菜单外功能不许进图。未动的材料在汇报写「无」。

---

## 4. 汇报模板（每批一段）

```
组：§1.6 交易；本批 ID：T-0x；清了 N 条，迁行 N。
四件套：①… ②… ③… ④…
三骨架：baseline / mybatis / jpa 各改文件（含 Binder 与 OrderStore）。
材料：受影响 …；未受影响写「无」。
门禁：三条 pytest 命令与结果。
本册：总表状态已改；地图 changelog 已写。
```

---

## 5. 修订记录

| 日期 | 说明 |
|------|------|
| 2026-10-06 | 立项：按地图 §1.6 待补拆 T-00～T-11；钉已有半截优先；能力岛加深不域默认硬塞 |
| 2026-10-06 | T-00/T-01 已齐：备注/默认地址/口味 chips/超时钉齐/影院取票码 |
| 2026-10-06 | T-02 已齐：购物车全选/清理失效/改规格/凑单包邮 |
| 2026-10-06 | T-03 已齐：锁库存回补、确认收货超时、邀评、销售日报、改地址；小票打印壳已挂、地图不迁 |
| 2026-10-06 | T-04 已齐：售后原因分类占比、原因必填、仅退款/退货分流、退货单号、N 天时限、进度时间轴 |
| 2026-10-06 | T-05 已齐：换货/仅换货、物流进度手填子表、部分发货、分享口令、收货码核销、延保 |
| 2026-10-06 | T-06a/T-06b 已齐：影院截止/占座/连座/售罄/须知 + 座属性/特效厅/手续费/周视图/连场 |
| 2026-10-07 | T-07 已齐：FOOD 桌号取餐号/餐具打包包装费/营业时段禁单/骑手回池/配送费送达/必选/拼单/档口评分；叫号大屏仍不支持 |
| 2026-10-07 | T-08 已齐：SHOP 发票抬头/状态/演示下载；满减满赠互斥文案；原路退回；会员日说明；≠税控 |
| 2026-10-07 | T-09 已齐：缺货到货、上下架定时、好评率晒图追评、足迹、浅规格库存、详情问答、预售说明；≠完整 SKU |
| 2026-10-07 | T-10 已齐：券核销码/领券中心/过期信、拼团进度与失败退款说明、限时购倒计时、中赏记录、积分流水与运费/兑票、影院会员价；仅 cap 已挂时 |
| 2026-10-07 | T-11 已齐并收口：影院卖品加购+库存、SHOP 包装费；小票打印仍待补；批次改已收口档案 |
