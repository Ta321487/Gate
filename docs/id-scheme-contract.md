# 编号合同（落库 · 运营/答辩可见）

> **本文只负责**：能落库、给人看或给人点名的 id / 编号——分层、产品脸、对账键、学生包签发家。  
> **不负责**：迁已有 `projects.id`；论文图节点 id；改当面 ZIP；批量重写已交付包旧单号。  
> **状态**：口径册 · **D1～D3 已开工收口**（2026-11-24）。  
> **口令**：`做编号合同`（维护 / 回归）。  
> **搁置**：[`parked-work.md`](./parked-work.md) 碎另案 **v**。  
> **索引**：[README.md](./README.md) · 产品对标 [`product-form-maturity.md`](./product-form-maturity.md) §5.1.1

---

## 0. 产品目标（一眼像产品）

| 场景 | 及格长相 |
|------|----------|
| 协作时点名一条记录 | 可复述、可搜、可复制；不像调试后台甩裸 `3` |
| 项目与吸收同屏 | 项目跟 `gf-…`；吸收列表像任务 `#12`；复制出去能对账 |
| 学生答辩用单号 | 有语义前缀（流水/核销/取票各不同）；同能力换开题不换第三种随机写法 |
| 上手认号 | 不用猜「这串是库主键还是业务号」 |

**硬原则**

1. **分层，不一种格式打天下。**  
2. **展示前缀 ≠ 库格式**：`#1099` 的 `#` 只进 UI。  
3. **禁止**为大整齐迁历史项目 id / 已 bake 包旧单号 / 把 `#` 写进主键。  
4. **禁止**夹在论文吸收抽取刀、出图几何刀里顺手拧编号。

---

## 1. 收口总表（相对产品）

| # | 面 | 现状 | 状态 |
|---|-----|------|------|
| 1 | **项目** | `gf-YYYYMMDD-HHMMSS` | **已齐** |
| 2 | **出包任务 Job** | UI `#{{job.id}}` | **已齐** |
| 3 | **终稿吸收** | 主脸 `#N`；对账键 `gf-ta-…`；路由兼吃 int / `gf-ta-…` | **D2 已齐** |
| 4 | **临时方案 `gf-plan-…`** | 保持 | **已齐** |
| 5 | **资产台行** | 自增 + UK；主展示跟中文/UK | **可接受** |
| 6 | **目录码** | `DOM-*` / cap / addon | **已齐** |
| 7 | **学生包可见业务号** | `BizCodeIssuer` 一处签发；三栈接线 | **D1 已齐** |
| 8 | **外单号（快递等）** | 手填 | **已齐** |
| 9 | **编号门禁** | `test_biz_code_issuer_contract` 钉签发家与接线 | **D3 已齐**（骨架闸；非出包 p3 键） |

---

## 2. 三层合同

| 层 | 名称 | 口径 |
|----|------|------|
| **A** | 机器行键 | 自增；可被 `#N` 借用数字；禁止无井号裸数字当主文案 |
| **B** | 工厂业务键 · 目录码 | `gf-*` 族 + `DOM-*` 等；运营点名、复制 |
| **C** | 学生包业务号 | `{前缀}{定长正文}`；**只走** `BizCodeIssuer` |

**两种「看起来像 Id」**

| 长相 | 是什么 | 进库？ |
|------|--------|--------|
| `#1099` | 展示脸 | `#` 不落库 |
| `gf-…` / `gf-ta-…` | B 层对账键 | 进库 |

**不进本册**：论文图节点 id、布局 pattern id、主题 swatch id。

---

## 3. B 层 · 工厂侧

| 种类 | 形状 | 状态 |
|------|------|------|
| 项目 | `gf-YYYYMMDD-HHMMSS` | 已落地 |
| 临时方案 | `gf-plan-{uuid12}` | 已落地 |
| Job | 自增 + UI `#N` | 已落地 |
| **终稿吸收** | `public_id=gf-ta-YYYYMMDD-HHMMSS`；`display_no=#id`；API `/system/thesis-absorb/{id\|gf-ta-…}` | **已落地** |
| 资产台 / 目录码 | 双键 / `DOM-*` | 保持 |

**`gf-*` 族（勿再发明第四种）**

| 前缀 | 用途 |
|------|------|
| `gf-YYYYMMDD-HHMMSS` | 项目 |
| `gf-plan-…` | 临时方案 |
| `gf-ta-YYYYMMDD-HHMMSS` | 终稿吸收对账键 |

---

## 4. C 层 · 学生包签发家

**家**：`skeletons/baseline/.../common/BizCodeIssuer.java`（jdbc 包必有；overlay Store 同调）。

| 方法 | 前缀/形状 | 调用方 |
|------|-----------|--------|
| `certIssueNo` | `CERT`+8 | TicketApproveOps |
| `pickupRedeemCode` | `PK`+10 | TicketApproveOps |
| `verifyCode` | `VF`+10 | TicketApproveOps |
| `passCode` | `VIS`+8 | TicketApproveOps |
| `pickupFromOrderId` | 4 位（订单派生） | OrderStore |
| `orderShareToken` | 8 位 hex | OrderStore |
| `memberCheckinToken` | `M`+5 | SlotStore |
| `permitCode` / `activationCode` | `PERMIT-…` / `ACT-…` | DigitalGoodsStore |

正文策略：单调毫秒序（`nextBody`）；取票码由订单 id 稳定派生。  
**不做**：批量重写已交付包旧号；外单号进签发器；OTP 验证码进本家。

---

## 5. 测与回归

| 测 | 钉什么 |
|----|--------|
| `tests/test_id_scheme_ta_public_id.py` | `gf-ta` 形状、`display_no`、路由解析、喂助手稿指针 |
| `tests/test_biz_code_issuer_contract.py` | 签发家存在、签发点无 nanoTime/Random、必调方法齐全 |
| `tests/test_thesis_absorb*.py` | 吸收主路径回归 |

用法：重启工厂后端走 `create_all` + `public_id` ALTER；旧吸收行列表/详情时自动补发 `gf-ta-…`。

---

## 6. 邻册边界

| 邻册 | 边界 |
|------|------|
| [`product-form-maturity.md`](./product-form-maturity.md) | 产品形态对标 |
| [`factory-asset-catalogs.md`](./factory-asset-catalogs.md) | 管内容；本册管键与可见号 |
| [`thesis-absorb.md`](./thesis-absorb.md) | 吸收产品；本册钉记录 id |
| `backend/app/bake/naming.py` | slug / ZIP / 库名；≠ 业务流水号 |
| [`opening-feature-delivery-map.md`](./opening-feature-delivery-map.md) | 有没有流水号能力 |
| [`student-copy`](../.cursor/rules/student-copy.mdc) | 界面称呼；不规定生成算法 |

---

## 修订

| 日期 | 说明 |
|------|------|
| 2026-11-24 | **开工收口 D1～D3**：`BizCodeIssuer` + 吸收 `gf-ta`/`#N` + 合同测 |
| 2026-11-24 | 去「同事」口吻；重排差口表；吸收裁定 `#N`+`gf-ta` |
| 2026-11-23 | 立册 |
