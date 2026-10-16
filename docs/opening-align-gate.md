# 开题对齐门禁（登记开关双向对上）

> **本文只负责**：壳底白名单 + B 扫词对照 + C cap 对照；门禁口径。  
> **不负责**：开题全文 vs 页面全文匹配；既有模块缺口闸（[`opening_align.py`](../backend/app/bake/features/opening_align.py)）。  
> **状态**：交易族 + **借用组** A 白名单 · **B+C 门禁已齐**；其余域组见 [parked-work.md](./parked-work.md) #3/#4。  
> **索引**：[parked-work.md](./parked-work.md) · [`trade-thicken-batch.md`](./trade-thicken-batch.md) §0.3 · 借用 `borrow_thicken.py`

---

## 0. 一句话

门禁只问：**登记过的功能开关，能否和 bake 同一套条件反向对上**（多挂 / 漏挂）。  
B 对扫词，C 对 cap。不审开题每个动词，不扫页面裸文案。

---

## 1. 三档

| 档 | 门禁 | 真源 |
|----|------|------|
| **A 壳底** | 跟域走；不要求开题写出 | `TRADE_A_SHELL_WHITELIST` / `BORROW_A_SHELL_WHITELIST` |
| **B 扫词开** | thicken 键 ↔ 同一 `scan_*` / RE | `TRADE_B_ALIGN_RULES` / `BORROW_B_ALIGN_RULES` |
| **C 能力加深** | thicken 键 ↔ 依赖 cap 在不在 | `TRADE_C_ALIGN_RULES` / `BORROW_C_ALIGN_RULES` |

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
- `diff_trade_align` / `diff_borrow_align` = 各域组 B+C 合并  

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

## 7. 修订

| 日期 | 说明 |
|------|------|
| 2026-10-14 | 首版：交易 B 对照 + A 白名单摘录 |
| 2026-10-14 | 补 C：`TRADE_C_ALIGN_RULES` + gate 测 |
| 2026-10-17 | 借用组 A/B/C：`BORROW_*_ALIGN_RULES` + gate 测 |
