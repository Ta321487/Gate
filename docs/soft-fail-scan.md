# 静默失败 / 「不对接＝免做」扫描清单

> **轮次**：2026-09-11 R2（R-17～R-27 **已改代码**；R-01～R-16 已齐）  
> **口径**：不对接第三方 SDK/硬件 ≠ 系统内闭环可免。能力开了，关键结果写库失败或缺列时，禁止「假成功 / 静默跳过」。  
> **范围**：`skeletons/baseline`（Store/Service/Controller + 学生可见前端）+ overlays 对照。  
> **不算**：MessageStore 通知吞异常、DDL ensure、ResultSet 缺列映射、失败补偿尽力回滚、批处理单条 continue、纯 UI/沉浸。

---

## 0. 易挂热区（按思想归纳）

不是「功能没做」，而是 **能力/UI 已露出，写路径对缺列·坏数据·序列化失败选择了兼容跳过**。答辩里最容易被追成「假成功」的，多落在这些模式：

| 模式 | 典型表现 | 为何易挂 |
|------|----------|----------|
| **A. 有则写 / 无列跳过** | `hasXxxColumn` 为 false 仍 200；前端已填结构化字段 | 场景页必填看起来生效，详情无列 |
| **B. 解析失败当 0 / 空 / 未过期** | `parseMoney` / `Double.parse` catch → 0 | 脏价变免单；上限/过期虚设（过期类 R-07 已收） |
| **C. 序列化失败写 `"{}"`** | extras / payload Jackson 失败仍落库 | 资料/日志空壳，调用方当成功 |
| **D. 能力开了、列契约残** | soft-delete / 置顶 / profile_json / channel | 开关语义与表结构不一致时静默降级 |
| **E. overlays 弱于 baseline** | 管理端有字段，jpa/mybatis 不读不写 | 一切 persistence 后「保存成功」更假 |
| **F. 部分列有、部分列无** | 收货三列 / 物流单号只写存在的列 | 一半进库一半丢，且不回流 remark |

**主路径相对安全（勿与上表混谈）**：钱货扣减、券核销、工单主状态机、预约占坑回滚、考试准入等——见 §3。

---

## 1. 已收口（勿再当缺口）

支付扣余额（含 demoPay / placeSimple / 补缴）、物流 `in_transit`/`signed`、选座失败回滚、券须领取与核销/回退硬失败、通行码/附件缺列硬失败、审核进度写失败抛错、错题本表未就绪抛错、预约联动订单、档案 `patchOpt`、申请截止/冲突/门数坏数据拦截、准入考试缺列硬失败、`reservation_id` 缺列硬失败、券过期 `parseTs`、发帖分类/数量解析拒请求、线路 stage/应还日/跟进日/数量/时间解析、选座布局同步等。

**已收口批次**：
- R-01～R-08：数量/应还日/区间/领取缺列；支付密码文案；形态校验；脏时间当不可用；点赞热度
- R-09～R-16：续借次数；领取实发/地点；多维评分；到书过期；CRM extras；图集/设施/秒杀；日志 payload
- R-17～R-20、R-25：资料 extras 序列化；预约结构化列；单价/票价硬解析；独立工单 priority/电话；选票头像三套对齐
- R-21～R-24、R-26～R-27：收货/物流含键缺列；软删缺列；公告置顶；profile_json；留言 channel

| ID | 优先级 | 路径 | 证据 | 答辩风险 | 建议修法 | 状态 |
|----|--------|------|------|----------|----------|------|
| **R-01** | **P0** | `TicketStore.apply`（三套） | `allowQty` 缺 `qty` 仍成功 | 数量按 1 扣库存 | 缺列硬失败 | **已齐** |
| **R-02** | P1 | `TicketStore.apply` | 应还日/区间解析后缺列静默不写 | 详情无日期 | 缺列硬失败 | **已齐** |
| **R-03** | P1 | `TicketStore.approve` | `useDeadline` 缺 `due_at` 仍通过 | 逾期断链 | 通过前硬失败 | **已齐** |
| **R-04** | P1 | `TicketStore.markPickup` | 无 `pickup_at` 仍成功 | 无领取时间 | 缺列硬失败 | **已齐** |
| **R-05** | P1 | `Cart.vue` / `MyOrders.vue` | 「任意不少于 4 位」 | 看成免校验 | 去掉「任意」 | **已齐** |
| **R-06** | P2 | `OrderStore` / README | 只验长度 | 老师追问怎么验 | 写清形态校验 | **已齐** |
| **R-07** | P2 | Slot/Seat/Archive 过期判断 | 解析失败当未过期 | 脏时间仍可约 | 失败视为已过 | **已齐** |
| **R-08** | P2 | `FavoriteStore.bumpLikeCount` | 热度 UPDATE 被吞 | 点赞无热度 | 写失败抛错 | **已齐** |
| **R-09** | **P0** | `TicketStore.renew`（baseline；overlay 无续借入口） | 缺 `renew_count` 不写次数；坏数据当 0 | 续借上限虚设 | 缺列/坏数据硬失败 | **已齐** |
| **R-10** | P1 | `TicketStore.markPickup`（三套） | `allowQty` 缺 `actual_qty` 仍成功 | 实发不落库 | 缺列硬失败 | **已齐** |
| **R-11** | P1 | `TicketStore.markPickup`（三套） | 缺 `pickup_place` 只写时间 | 地点丢失 | 缺列硬失败 | **已齐** |
| **R-12** | P1 | `TicketStore.rate`（三套） | 多维 dims 缺列只写总分 | 维度分丢弃 | 缺列硬失败 | **已齐** |
| **R-13** | P1 | `TicketStore` 到书（baseline） | 缺 `hold_expire_at` 仍晋升且永不超时 | 预约永不过期 | 申请/晋升硬拦；晋升必写过期 | **已齐** |
| **R-14** | P1 | `TicketStore.patchTicketExtras`（三套） | CRM 键有值缺列静默不写 | 跟进/渠道/金额丢 | 含键缺列硬失败 | **已齐** |
| **R-15** | P1 | `ArchiveStore.updateItem`（三套） | 图集/设施/秒杀能力开缺列跳过 | 管理端保存假成功 | 含键缺列硬失败 | **已齐** |
| **R-16** | P2 | `ArchiveLogStore.submit`（三套） | payload 序列化失败写 `{}` | 日志内容空壳 | 序列化失败抛错 | **已齐** |
| **R-17** | P1 | `UserStore.writeExtras`（三套） | JSON 序列化失败写 `"{}"` | 扩展资料空壳覆盖 | 序列化失败抛错 | **已齐** |
| **R-18** | P1 | `SlotStore.reserve`（三套） | 结构化 extras 缺列仍约成功 | 详情无车牌/就诊人等 | 含键缺列硬失败 | **已齐** |
| **R-19** | P1 | `ArchiveStore` / `SeatStore` 单价（三套） | 解析失败当 0 仍成交 | 脏价免单 | 成交路径硬解析；列表软解析 | **已齐** |
| **R-20** | P1 | `TicketStore.applyStandalone`（三套） | priority/电话缺列静默不写 | 优先级/回访丢失 | 含键缺列硬失败 | **已齐** |
| **R-25** | P1 | `VoteStore.createCandidate`（三套） | overlays 不写 avatar；有值缺列假成功 | 头像保存假成功 | overlays 对齐；有值缺列硬失败 | **已齐** |
| **R-21** | P2 | `OrderStore.placeOrder`（三套） | 收货部分列有、部分丢且不回流 remark | 配送信息丢失 | 含键缺列硬失败 | **已齐** |
| **R-22** | P2 | `OrderStore.advance` 发货（三套） | 填了单号缺列仍改 status | 单号假保存 | 含键缺列硬失败 | **已齐** |
| **R-23** | P2 | `ArchiveStore.deleteItem`（三套） | soft-delete 开缺列走物理删 | 「下架」变真删 | 缺列硬失败 | **已齐** |
| **R-24** | P2 | `NoticeStore.update(..., pinned)`（三套） | 缺 pinned 仍改正文忽略置顶；overlays 曾无置顶 API | 置顶假保存 / 切 persistence 编译断 | 含 pinned 意图缺列硬失败；overlays 对齐 | **已齐** |
| **R-26** | P2 | `UserStore` register/saveProfile/adminUpdate（三套） | 非空 extras 缺 `profile_json` 仍成功 | 身份扩展校验过不落库 | 含非空 extras 缺列硬失败 | **已齐** |
| **R-27** | P2 | `GuestbookStore.add`（三套） | 非默认 channel 缺列仍插入 | 多店通道不可分 | merchant 缺列硬失败 | **已齐** |

---

## 2. 待办

无。R2 全部条目已收口。

**未升格（残差说明，勿开单）**  
- `TicketStore.approve` 对 `assignee_username`：缺列则不绑定但仍通过——域模板几乎都有该列，风险低于已收口项。  
- 前端支付密码 / README 形态校验、demoPay「不对接 SDK 仍扣余额」——已收口诚实说明。  
- MessageStore / DDL ensure / 读侧缺列映射——按口径不算。

---

## 3. 已核：主路径未见同类回潮

| 域 | 结论 |
|----|------|
| TicketStore 主路径 + standalone extras | R-01～R-04、R-09～R-14、R-20 硬失败仍在 |
| OrderStore / LoyaltyStore | 扣余额硬拦；**收货/发货含键缺列硬失败（R-21/R-22）** |
| CouponStore | 未见「成功无券」 |
| SeatStore / SlotStore | 购票回滚；**extras / 票价（R-18/R-19）** |
| ArchiveStore | 图集等缺列硬失败；**软删缺列硬失败（R-23）**；成交单价硬解析 |
| UserStore / ArchiveLogStore | extras / payload 序列化失败抛错；**非空 extras 须 profile_json（R-26）** |
| VoteStore | 三套 avatar；有值缺列硬失败 |
| NoticeStore / GuestbookStore | **置顶三套对齐 + 含键硬失败（R-24）**；merchant channel（R-27） |
| Recommend / AiAssistant | 只读回落 FAQ |

---

## 4. 统计与结论

| 批次 | 优先级 | 条数 | 状态 |
|------|--------|------|------|
| R-01～R-16 | P0×2 / P1×11 / P2×3 | 16 | **已齐** |
| R2 全量（R-17～R-27） | P1×5 / P2×6 | 11 | **已齐** |
| **合计** | | **27 / 27** | **已齐** |

**结论**：R2 软失败清单已全部收口。能力开了、用户填了关键字段却缺列/坏数据/序列化失败时，写路径硬失败，禁止假成功。

---

## 5. 变更记录

| 日期 | 说明 |
|------|------|
| 2026-09-11 | 初版：只扫不改；P0×1 / P1×4 / P2×3 |
| 2026-09-11 | 收口 R-01～R-08 |
| 2026-09-11 | 继续扫并收口 R-09～R-16 |
| 2026-09-11 | R2 只扫不改：增 §0 易挂热区；开 R-17～R-27 |
| 2026-09-11 | 收口 R2 P1：R-17～R-20、R-25 |
| 2026-09-11 | 收口 R2 P2：R-21～R-24、R-26～R-27（三套同源；R-24 仅 baseline） |
| 2026-09-11 | 工厂侧沿 `fragments.ensure_*` 补列：vote `avatar_url`、softDelete→`deleted_at`、notice `pinned`、guestbook `channel` 收编 inject（不再平行 regex） |
| 2026-09-11 | R-24 overlays：jpa/mybatis `NoticeStore` 对齐置顶 API（update/setPinned/读侧排序） |
