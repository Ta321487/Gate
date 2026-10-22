# 开题对齐门禁（登记开关双向对上）

> **本文只负责**：壳底白名单 + B 扫词对照 + C cap 对照；门禁口径。  
> **不负责**：开题全文 vs 页面全文匹配；既有模块缺口闸（[`opening_align.py`](../backend/app/bake/features/opening_align.py)）。  
> **状态**：交易族 + **借用** + **跟进** + **报修** + **报名** + **审批** + **预约** + **内容** + **互动** A 白名单 · **B+C 门禁已齐**（#3+#4 全族收口）。  
> **索引**：[parked-work.md](./parked-work.md) · [`trade-thicken-batch.md`](./trade-thicken-batch.md) §0.3 · 各组 `*_thicken.py`

---

## 0. 一句话

门禁只问：**登记过的功能开关，能否和 bake 同一套条件反向对上**（多挂 / 漏挂）。  
B 对扫词，C 对 cap。不审开题每个动词，不扫页面裸文案。

---

## 1. 三档

| 档 | 门禁 | 真源 |
|----|------|------|
| **A 壳底** | 跟域走；不要求开题写出 | 各组 `*_A_SHELL_WHITELIST`（含 `APPLY_*`） |
| **B 扫词开** | thicken 键 ↔ 同一 `scan_*` / RE | 各组 `*_B_ALIGN_RULES` |
| **C 能力加深** | thicken 键 ↔ 依赖 cap 在不在 | 各组 `*_C_ALIGN_RULES` |

**禁止第二套词典**：改词只改该组 thicken 的 RE / `scan_*`；改 cap 条件只改 apply + 本表。

---

## 2. A 壳底白名单（交易 · 摘录）

人工定；灰区（如「改地址」）进白名单，不靠模型猜。

| 开关（例） | 域 | 说明 |
|------------|-----|------|
| cartSelectAll / cartClearInvalid / cartAutoUncheck | SHOP·FOOD | 购物车壳 |
| changeAddress | SHOP | 灰区：订单壳延伸 |
| cartFreeShip / confirmReceiveTimeout | SHOP（±FOOD） | 主路径 |
| refundType / refundTracking / afterSaleDays / refundTrace | SHOP | 仅退/退货壳；**换货**走 B |
| packagingFee | **FOOD** | 点餐壳底；SHOP 走 B |
| orderReceiptPrint | **FOOD·CINEMA** | 壳底；SHOP 走 B |
| tableNo / utensilPack / cinemaSnack / … | 各域壳 | 见常量全文 |

---

## 3. B 扫词开关对照（交易）

真源：`TRADE_B_ALIGN_RULES` → `diff_trade_b_align`。

| thicken 键 | 域 | 扫词（与 bake 同） |
|------------|-----|-------------------|
| cartChangeSpec / specStock | SHOP | `_scan_cart_spec_ux` |
| cartFreeShip | SHOP | 包邮 / 满额包邮 / 免运费 / 凑单包邮（自提配送题不空挂） |
| refundExchange | SHOP | 换货 / 以换代修 / 仅换货 |
| shipNodes | SHOP | 物流进度·节点…（≠「物流损坏」） |
| warranty | SHOP | 延保 / 质保… |
| orderShare | SHOP·FOOD | 分享口令 / 凭口令… |
| receiveCode | SHOP·FOOD | 收货码 / 当面核销… |
| orderReceiptPrint | **SHOP** | 打印小票 / 订单小票… |
| invoiceTitle / invoiceStatus / invoicePdf | SHOP | 发票 / 开票… |
| giftPromo | SHOP | 满赠 / 赠品… |
| packagingFee | **SHOP** | 包装费 / 打包费… |
| presaleNote | SHOP | 预售 / 定金 / 尾款 |
| stockNotify | SHOP | 到货通知 / 缺货提醒… |
| itemQa | SHOP | 商品问答… |
| shelfSchedule | SHOP·FOOD | 定时上架 / 定时下架… |

---

## 4. C 能力加深对照（交易）

真源：`TRADE_C_ALIGN_RULES` → `diff_trade_c_align`。  
条件：适用域内 **cap 在 → 开关真；cap 不在 → 开关假**。

| thicken 键 | 域 | 依赖 cap |
|------------|-----|----------|
| stockLock | SHOP·FOOD | `quota` |
| inviteReview | 三域 | `order_review` |
| reviewImage / reviewFollow | SHOP·FOOD | `order_review` |
| browseHistory | SHOP | `browse_history` |
| spendDiscountHelp | SHOP | `spend_discount` |
| couponMutex / couponRedeemCode / couponClaimCenter / couponExpireNotify | SHOP | `coupon` |
| memberDay | SHOP | `member_tier` |
| groupBuyProgress / groupBuyFailRefund | SHOP | `group_buy` |
| flashCountdown | SHOP | `flash_price` |
| blindDraws | SHOP | `blind_box` |
| pointsLedger / pointsFreight | SHOP | `points` |
| cinemaPointsTicket | CINEMA | `points` |
| cinemaMemberPrice | CINEMA | `member_tier` |

未进表：骑手回池（岗/扫词混合，非纯 cap）等——有再登记。

---

## 5. 验收

```
pytest backend/tests/test_opening_align_gate.py -q
```

- B：空开题不多挂；扫词命中不漏挂  
- C：无 cap 不多挂；有 cap 不漏挂  
- `diff_*_align` = 各域组 B+C 合并（含 `diff_*_align` 全族）  

---

## 6. 借用组（§1.1）

真源：`BORROW_*` → `diff_borrow_b_align` / `diff_borrow_c_align` / `diff_borrow_align`。  
改词只改 `borrow_thicken.py` 的 `_*_TERMS` / `scan_*`。

| 档 | 要点 |
|----|------|
| **A** | 热门榜、用途字典、代取、床位性别年级、入库衔接等；灰区：信誉规则文案壳、闭架/征订/漂流文案、驿站异常件、保养工单说明 |
| **B** | ISBN、随书光盘、信誉分值、罚款减免、续借无预约、保养到期日、押金、校准停借、双方确认、弃件、盘点锁定等（见 `BORROW_B_ALIGN_RULES`） |
| **C** | `suggestBudget` ↔ `book_suggest` |

未进 C 表：报废叠二级审（`stock_scrap` 且无 `approveFlow` 才叠；有独立报废流则关，不是「有 cap 必开」）。

---

## 7. 跟进组（§1.2）

真源：`FOLLOW_*` → `diff_follow_b_align` / `diff_follow_c_align` / `diff_follow_align`。  
改词只改 `follow_thicken.py` 的 `_*_TERMS` / `scan_*`。

| 档 | 要点 |
|----|------|
| **A** | 跟进提醒/时间轴/渠道饼图/成交金额、结案附件、假期额度、面试结果批量录用、补考入口、带看评价反馈、周报催交等 |
| **B** | 查重、家访、未跟进池、回款计划、事件等级时限/值班、异议窗口、岗位收藏、入职材料、周报优秀、房源对比/冲突等（见 `FOLLOW_B_ALIGN_RULES`） |
| **C** | 本组暂无纯 C 键（favorites/deadline/material_check 等由 B 扫词连同 cap 挂上） |

迁档要点：客户查重原假域默认 → **扫词开**（空开题关）。

---

## 8. 报修组（§1.3）

真源：`REPAIR_*` → `diff_repair_b_align` / `diff_repair_c_align` / `diff_repair_align`。  
改词只改 `repair_thicken.py` 的 `_*_TERMS` / `scan_*`。

| 档 | 要点 |
|----|------|
| **A** | 催办链/结单摘要/SLA 分列/评价/挂起草稿等 `core`；查重公区；技能标签；IT 资产号/远程；PROPERTY·IT 备件序列号与 FAQ |
| **B** | 报价、知识沉淀、工单合并、值班冲突提示；DORM 备件/序列号/FAQ；DORM·PROPERTY 资产号/远程（见 `REPAIR_B_ALIGN_RULES`） |
| **C** | 本组暂无纯 C 键（deadline 域默认） |

分域双档同交易 packagingFee：同一 thicken 键可 A/B 分域，禁止第二套词典。

---

## 9. 报名组（§1.4）

真源：`APPLY_*` → `diff_apply_b_align` / `diff_apply_c_align` / `diff_apply_align`。  
改词只改 `apply_thicken.py` / `ticket_flow_opts.scan_waitlist`。

| 档 | 要点 |
|----|------|
| **A** | 须知勾选/驳回必填/站内信/批量审/名额紧张；四域域皮字段与抽签/黑名单/票务等壳底 |
| **B** | `surveyLink` ↔ 活动问卷扫词（ACTIVITY） |
| **C** | `tourWaitlist` ↔ `waitlist`（TOUR；空开题关） |

迁档：TOUR 从候补行业默认摘掉；线路候补仅随 waitlist cap。

---

## 10. 审批组（§1.5）

真源：`APPROVE_*` → `diff_approve_b_align` / `diff_approve_c_align` / `diff_approve_align`。  
改词只改 `approve_thicken.py` 的 `_AUTO_PASS_TERMS` / `scan_approve_auto_pass`。

| 档 | 要点 |
|----|------|
| **A** | 撤回/退回再提/意见短语/字数/时限催办/抄送/转审代审/意见附件等壳底；23 域域皮字段（证明领取、用印份数、用车里程等） |
| **B** | `autoPass` ↔ 限时自动通过扫词（审批 23 域；空开题关） |
| **C** | `examPassMin` ↔ `exam`（LABSAFE；空开题关） |

迁档：LABSAFE 准入考试成绩门槛从假域默认摘掉；仅随 exam cap。

---

## 11. 预约组（§1.7）

真源：`RESERVE_*` → `diff_reserve_b_align` / `diff_reserve_c_align` / `diff_reserve_align`。  
本组无 thicken 自扫词；cap 扫词在各 feature，R-09 只加深。

| 档 | 要点 |
|----|------|
| **A** | 取消时限/改约上限/提醒/爽约/成功信/迟到/维护禁约/候补转正/日历/备注/黑名单；七域域皮 |
| **B** | 本组暂无 thicken 自扫词键（`RESERVE_B_ALIGN_RULES` 空） |
| **C** | `hospitalRoster`/`salonLeaveBlock` ↔ `staff_roster`；`salonLessonRemain`/`salonLessonExpire` ↔ `lesson_pack`；`salonWallet` ↔ `wallet`；`salonGallery` ↔ `gallery`；`meetingEquipBorrow` ↔ `room_equipment` |

迁档：地图 R-09 从「扫词挂」统一为「能力加深」；bake 本已按 cap 叠，本轮只钉门禁。

---

## 12. 内容组（§1.8）

真源：`CONTENT_*` → `diff_content_b_align` / `diff_content_c_align` / `diff_content_align`。  
本组无 thicken 自扫词；cap 扫词在各 feature，C-08 / 治理叠只加深。

| 档 | 要点 |
|----|------|
| **A** | 阅读数/热门/足迹（MEDIA·MUSIC·BLOG 壳挂 browse_history）/标题搜；五域域皮与论坛运营壳 |
| **B** | 本组暂无 thicken 自扫词键（`CONTENT_B_ALIGN_RULES` 空） |
| **C** | 禁言到期/举报通知时效 ↔ post_mute·content_report；积分岛 ↔ points（或 wallet）；粉丝可见 ↔ item_comment；投稿通知 ↔ userPublish |

迁档：地图 C-08/治理叠从「扫词挂/有 cap」统一为「能力加深」；bake 本已按 cap 叠，本轮只钉门禁。

---

## 13. 互动组（§1.9）

真源：`INTERACT_*` → `diff_interact_b_align` / `diff_interact_c_align` / `diff_interact_align`。  
本组无 thicken 自扫词；cap 扫词在各 feature，I-11 只加深。

| 档 | 要点 |
|----|------|
| **A** | 心动壳（DATING 挂 favorites）/评价壳（CARPOOL·TIMEBANK·MUTUAL-TUTOR）/双选·拼车·时银·考试·问卷·投票域皮 |
| **B** | 本组暂无 thicken 自扫词键（`INTERACT_B_ALIGN_RULES` 空） |
| **C** | `favoritesIsland` ↔ favorites；`dmIsland` ↔ dm；`ratingIsland` ↔ allowRating；举报时限 ↔ content_report |

迁档：地图 I-11 从「已挂/扫词挂」统一为「能力加深」；bake 本已按 cap 叠，本轮只钉门禁。**#3+#4 全族收口。**

---

## 14. 修订

| 日期 | 说明 |
|------|------|
| 2026-10-14 | 首版：交易 B 对照 + A 白名单摘录 |
| 2026-10-14 | 补 C：`TRADE_C_ALIGN_RULES` + gate 测 |
| 2026-10-17 | 借用组 A/B/C：`BORROW_*_ALIGN_RULES` + gate 测 |
| 2026-10-22 | 跟进组 A/B/C：`FOLLOW_*_ALIGN_RULES` + gate 测；查重改扫词 |
| 2026-10-22 | 报修组 A/B/C：`REPAIR_*_ALIGN_RULES` + gate 测；分域双档钉清 |
| 2026-10-22 | 报名组 A/B/C：`APPLY_*_ALIGN_RULES`；TOUR 候补改能力加深 |
| 2026-10-22 | 审批组 A/B/C：`APPROVE_*_ALIGN_RULES`；LABSAFE 考试门槛改能力加深 exam |
| 2026-10-22 | 预约组 A/B/C：`RESERVE_*_ALIGN_RULES`；R-09 能力加深门禁；B 空 |
| 2026-10-22 | 内容组 A/B/C：`CONTENT_*_ALIGN_RULES`；C-08 能力加深门禁；B 空 |
| 2026-10-22 | 互动组 A/B/C：`INTERACT_*_ALIGN_RULES`；I-11 能力加深门禁；**全族收口** |
