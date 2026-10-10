# §1.7 预约组加厚批次（已收口档案）

> **本文只负责**：地图 [`opening-feature-delivery-map.md`](./opening-feature-delivery-map.md) §1.7「本组待补」的**分批实现顺序、挂载口径、验收勾选**。  
> **不负责**：cap 定义（[`capabilities.md`](./capabilities.md)）；怎么审交付（[`delivery-audit-rules.md`](./delivery-audit-rules.md)）；清待补工序纪律（`.cursor/rules/opening-group-delivery.mdc`）。  
> **状态**：**已收口档案**（R-00～R-10 全部 **已齐**）。  
> **索引**：[README.md](./README.md) · 地图 §1.7 · 范本 `trade_thicken` / `apply_thicken`。  
> **不负责 UI 表面构图**：号源/房态列表选型见 [`domain-group-ui-styles.md`](./domain-group-ui-styles.md)（加厚已收口，实现另开 plan）。

---

## 0. 硬口径（写代码前先背）

### 0.1 一组一包

| 规则 | 含义 |
|------|------|
| **组模块** | `backend/app/bake/features/reserve_thicken.py` + `apply_reserve_thicken_to_spec` |
| **注册** | 必须挂进 `backend/app/bake/domain_schema.py`（紧接 `trade_thicken` 之后） |
| **域集合** | `RESERVE_DOMAINS` = HOSPITAL / PARKING / MEETING / SALON / HOTEL / CARRENT / INSTRUMENT |
| **不抢邻组** | 不碰 §1.6 交易三域；不碰 §1.8+ |
| **Store 主战场** | `SlotStore`；辅 `ArchiveStore` / `MessageStore` / `DemoScheduleJobs`；酒店租车可轻碰 `OrderStore`，**禁止**第二套预约状态机 |
| **一轮只清本组** | 禁止同轮动 §1.6/§1.8；禁止只改地图不改骨架 |

### 0.2 一条待补 = 四件套 + 三骨架

硬口径：**管理端能管 + 用户端可产生数据（真写库）**。纯 Hint / 只读 / 打印 / 前端零读取字面量 → 不得标已齐。

| 件 | 真源 |
|----|------|
| ① 表 / 列 | `ensure_reserve_thicken_sql` + 既有 `RESERVATION_COLUMNS_BY_DOMAIN` |
| ② Store 写方法 | `SlotStore` 等（三套骨架同改） |
| ③ API | `SlotController` 等 |
| ④ 前端控件 | `SlotBook` / `MyReservations` / `ReservationsAdmin` / 黑名单申诉 |

三骨架：`baseline` · `persistence-mybatis` · `persistence-jpa`。

### 0.3 挂载：域默认 vs 扫词加深

| 类型 | 何时开 | 地图「挂载」列 |
|------|--------|----------------|
| **七域通识底** | RESERVE_DOMAINS 主路径刚需 | **域默认** |
| **能力岛加深** | 仅当已挂对应 cap（staff_roster / room_equipment / venue_clean / lesson_pack / rental_bond / material_check / code_qr / gallery） | 扫词挂 cap 时（R-09） |
| **禁止** | 因「预约常见」把排班/保洁/押金做成永远开 | — |

### 0.4 不支持（不进待补实现）

| 边界 | 原因 |
|------|------|
| 会议室开门密码短信 | 真短信；站内信顶 |
| 酒店入住登记公安上传 | 无公安网 |
| 医保 / 道闸 / OTA / 门锁 / HIS / 高并发锁座引擎 | 超纲 |

### 0.5 每批工序（固定）

```
1. reserve_thicken：开关 / labels / 域默认或扫词条件
2. ensure 列 / 子表（禁止 JSON 冒充三范式）
3. SlotStore 写方法 — 三套同改
4. Controller API — 三套 DomainRuntimeBinder 同绑
5. 用户端写控件 + 管理端管控件（文案无工厂腔）
6. 三绿才迁行：
   - pytest backend/tests/test_opening_map_skeleton_gate.py -q
   - pytest backend/tests/test_reserve_thicken_features.py -q
7. 地图：待补 →「本组本轮已齐」；本册状态改已齐；changelog 一行
8. 业务稳定后 AOCI maintain（新 .py 先 scope acknowledge；本轮可暂缓）
```

---

## 1. 批次总表

> **状态列**：`待写` → `实现中` → `已齐`（须过 §0.5 三绿 + 地图迁行）。

| 序 | ID | 主题 | 条数约 | 主要落域 | 状态 |
|----|-----|------|--------|----------|------|
| 0 | **R-00** | 脚手架：`reserve_thicken` + `domain_schema` + `test_reserve_thicken_features` + 本册 | — | 工厂 | **已齐** |
| 1 | **R-01** | 通识钉齐：取消时限 / 改约上限 / 提前提醒 / 爽约限制 / 成功信 / 签到迟到 / 维护禁约 / 候补转正信 / 日历着色 / 管理员备注 / 黑名单申诉 | 11 | 七域 | **已齐** |
| 2 | **R-02** | HOSPITAL：报到口令 / 分时段余量 / 就诊人多档案 / 队列号 / 候补 / 退号 / 初复诊 / 科室介绍 / 停诊通知与日历 / 排队预估 / 黄牛限号 / 复诊优先说明 / 检验分槽 | 13 | HOSPITAL | **已齐** |
| 3 | **R-03** | PARKING：超时加收 / 套餐次卡 / 通行证提示 / 时长计费 / 取消罚则文案 / 拼单说明 / overlapping 说明（ETC 归 R-07） | 7 | PARKING | **已齐** |
| 4 | **R-04** | MEETING：纪要附件 / 签到导出 / 冲突文案 / 录屏链接 / 周重复 / 需审批 / 茶水设备勾选 / 黑名单 / 门禁密码手发 / 视频链接 / 签到二维码 / 最低时长 / 召开中状态 | 13 | MEETING | **已齐** |
| 5 | **R-05** | SALON：报到口令叠 / 时长占坑 / 队列号 / 改约手续费 / 迟到宽限 / 禁忌备注 / 到店扫码 / 到店次数（储值/作品集扫词，不域默认） | 8 | SALON | **已齐** |
| 6 | **R-06** | HOTEL：续住延期 / 延迟退房加收 / 身份证脱敏 / 定金尾款 / 连住说明 / 早餐券 / 入住须知 / 加床 / 钟点房 / 同住人数 / 查房清单 | 12 | HOTEL | **已齐** |
| 7 | **R-07** | CARRENT：违章预留押说明 / 验车单 / 里程超支 / 导航外链 / 保险套餐 / 驾照有效期 / 违章附件 / ETC 通行费登记 | 8 | CARRENT | **已齐** |
| 8 | **R-08** | INSTRUMENT：超时计费 / 培训合格才可约 / 冲突可视化 / 实验目的 / 耗材领用 / 导师同意 / 机时费导出 | 7 | INSTRUMENT | **已齐** |
| 9 | **R-09** | 能力岛加深（仅 cap 已挂） | ~6 | 扫词 | **已齐** |
| 10 | **R-10** | 扫尾：对照地图「本组待补」清零；不支持段只留边界；批次改已收口档案 | 余量 | 全组 | **已齐** |

**推荐编码顺序**：R-00 → R-01 → R-02…R-08 → R-09 → R-10。

---

## 2. 分批明细

### R-00 脚手架

| 勾选 | 项 |
|------|-----|
| ☑ | 新建 `backend/app/bake/features/reserve_thicken.py` |
| ☑ | `domain_schema.py` 注册（紧接 `trade_thicken` 之后） |
| ☑ | `backend/tests/test_reserve_thicken_features.py` |
| ☑ | 本册 + README / 地图 §1.7 批次入口 |

### R-01 通识（本组通用 · 域默认）

| 地图待补 | 落点建议 | 挂载 |
|----------|----------|------|
| 取消预约规则（开始前 N 小时可免费取消） | `cancelFreeHours` + SlotStore.cancel 校验 | **域默认** |
| 改约次数上限 | `rescheduleMaxTimes` + `reschedule_count` | **域默认** |
| 预约开始前站内信提醒 | `remindAheadMinutes` + DemoScheduleJobs + `remind_sent` | **域默认** |
| 预约爽约次数限制再约 | `noShowLimit` + `no_show` 标记计数 | **域默认** |
| 预约成功短信式站内信 | 钉 MessageStore 成功信 + labels | **域默认** |
| 预约签到迟到标记 | `checked_in_at` / `late_flag` + 签到 API | **域默认** |
| 预约资源维护时段禁约 | archive.`maintain_from`/`maintain_to` | **域默认** |
| 预约候补转正站内信 | waitlisted→confirmed 发信 | **域默认**（有候补时生效） |
| 预约资源容量日历着色 | SlotBook 日格 + `slotFillTone` / dayFill | **域默认** |
| 预约资源管理员备注（对用户不可见） | archive.`admin_note`；用户端剥离 | **域默认** |
| 预约黑名单申诉入口 | `reserve_blacklist` + `reserve_blacklist_appeal` | **域默认** |

### R-02 HOSPITAL 域皮（域默认 · 仅 DOM-HOSPITAL）

| 勾选 | 地图待补 | 落点 |
|------|----------|------|
| ☑ | 报到签到口令 | checkin_code + checkIn 核对；labels.checkinCode* |
| ☑ | 分时段余量 | SlotBook 上午/下午分组；labels.slotPeriod* |
| ☑ | 就诊人多档案 | patient_profile + PatientProfiles |
| ☑ | 候诊队列序号 | queue_no；labels.queueNo* |
| ☑ | 号源候补 | allowWaitlist + 转正；labels.hospitalWaitlistHint |
| ☑ | 退号（开诊前 N 分钟） | hospitalCancelCutoffMinutes |
| ☑ | 初诊/复诊 | visit_type；labels.visitType* |
| ☑ | 科室介绍 | dept_intro；labels.deptIntro* |
| ☑ | 停诊通知与日历 | notifyStopAndCancel + maintain_* |
| ☑ | 排队预估 | queue_estimate_hint；labels.queueEstimate* |
| ☑ | 同证件限号 | hospitalIdLimitPerDay |
| ☑ | 复诊优先说明 | labels.revisitPriorityHint |
| ☑ | 检验分槽 | slot_kind；labels.slotKind* |

三绿：`test_opening_map_skeleton_gate` + `test_reserve_thicken_features`（含 `test_hospital_r02_domain_skin`）。

### R-03 PARKING 域皮（域默认 · 仅 DOM-PARKING）

| 勾选 | 地图待补 | 落点 |
|------|----------|------|
| ☑ | 超时占用加收 | overtime_fee_yuan + registerOvertimeFee |
| ☑ | 套餐次卡 | parking_pass + ParkingPassStore |
| ☑ | 通行证提示 | pass_hint + labels.parkingCarpassHint |
| ☑ | 时长计费进离场 | exit_at / duration_fee_yuan + markExit |
| ☑ | 取消罚则说明 | labels.parkingCancelPenaltyHint |
| ☑ | 拼单说明 | labels.parkingShareSlotHint |
| ☑ | overlapping 检测说明 | assertParkingOverlap + labels.parkingOverlapHint |

三绿：`test_opening_map_skeleton_gate` + `test_reserve_thicken_features`（含 `test_parking_r03_domain_skin`）。ETC 租车条归 R-07。

### R-04 MEETING 域皮（域默认 · 仅 DOM-MEETING）

| 勾选 | 地图待补 | 落点 |
|------|----------|------|
| ☑ | 会议结束后必填纪要附件 | minutes_attach + meetingMinutesRequired；办结核验 |
| ☑ | 会议签到表导出 | ReservationsAdmin CSV |
| ☑ | 会议冲突检测说明文案 | labels.meetingConflictHint + listSlotOccupants |
| ☑ | 会议录屏链接字段 | recording_url |
| ☑ | 会议室按周重复预约 | generateWeeklySlots |
| ☑ | 会议室预约需审批开关 | requireConfirm |
| ☑ | 会议茶水/设备服务勾选 | service_tea / service_device |
| ☑ | 场地预约黑名单 | 复用 R-01 reserve_blacklist |
| ☑ | 会议室门禁密码字段（手发） | door_code + patchMeeting |
| ☑ | 会议室视频会议链接字段 | video_url |
| ☑ | 会议签到二维码 | checkin_token（确认后签发） |
| ☑ | 会议室最低预约时长 | archive.min_duration_minutes |
| ☑ | 会议召开中状态 | meeting_stage |

三绿：`test_opening_map_skeleton_gate` + `test_reserve_thicken_features`（含 `test_meeting_r04_domain_skin`）。录制设备借用归 R-09；开门密码短信不支持。

### R-05 SALON 域皮（域默认 · 仅 DOM-SALON）

| 勾选 | 地图待补 | 落点 |
|------|----------|------|
| ☑ | 到店报到口令 | checkin_code + checkIn 核对 |
| ☑ | 服务项目时长占坑 | service_minutes + generate/assert |
| ☑ | 到店队列序号 | queue_no + labels |
| ☑ | 改约手续费登记 | reschedule_fee_yuan；默认金额 AppPolicy |
| ☐ | 储值卡余额 | **不域默认**：wallet 扫词可顶 |
| ☑ | 到店迟到宽限 | AppPolicy.LATE_GRACE_MINUTES + salonLateGraceHint；实例 late_flag |
| ☑ | 项目禁忌备注 | taboo_note |
| ☑ | 到店扫码签到 | checkin_token + CodeQrBlock |
| ☑ | 会员到店次数 | visitCount API |
| ☐ | 作品集 | **不域默认**：gallery 扫词可顶；禁止硬挂 gallery_json |

三绿：`test_opening_map_skeleton_gate` + `test_reserve_thicken_features`（含 `test_salon_r05_domain_skin`）。会员卡余次仍走 lesson_pack 扫词。

### R-06 HOTEL 域皮

| 勾选 | 项 |
|------|-----|
| ☑ | 续住延期 | stay_to + extendStay |
| ☑ | 延迟退房加收 | late_checkout_fee_yuan；AppPolicy 默认 |
| ☑ | 身份证脱敏 | id_no + idNoMasked |
| ☑ | 定金尾款 | deposit_yuan / balance_yuan |
| ☑ | 连住说明 | hotelStayMultiNightHint |
| ☑ | 早餐券 | breakfast_vouchers |
| ☑ | 入住须知勾选 | notice_ack + hotelNoticeRequired |
| ☑ | 加床 | extra_bed |
| ☑ | 钟点房类型 | archive.room_kind |
| ☑ | 超时转全日说明 | hotelHourlyToFullHint |
| ☑ | 同住人数 | guest_count 文案钉齐 |
| ☑ | 查房清单 | checkout_checklist 浅字段；**禁止**硬挂 material_check |

三绿：`test_opening_map_skeleton_gate` + `test_reserve_thicken_features`（含 `test_hotel_r06_domain_skin`）。

### R-07 CARRENT 域皮

| 勾选 | 项 |
|------|-----|
| ☑ | 违章预留押说明 | violation_hold_yuan / note |
| ☑ | 验车单勾选 | inspect_ack 浅字段；**禁止**硬挂 material_check |
| ☑ | 里程超支加收 | mileage_over_fee_yuan；AppPolicy 默认 |
| ☑ | 取还点导航外链 | archive.pickup_nav_url / return_nav_url |
| ☑ | 保险套餐勾选 | insurance_pkg；文案价 |
| ☑ | 驾照有效期 | license_expire_on |
| ☑ | 违章附件 | violation_attach |
| ☑ | ETC 通行费登记 | etc_fee_yuan |

三绿：`test_opening_map_skeleton_gate` + `test_reserve_thicken_features`（含 `test_carrent_r07_domain_skin`）。禁止域默认 `rental_bond`。

### R-08 INSTRUMENT 域皮

| 勾选 | 项 |
|------|-----|
| ☑ | 超时机时费登记 | overtime_fee_yuan；AppPolicy.INSTRUMENT_OVERTIME_YUAN |
| ☑ | 培训合格勾选 | training_ack 浅字段；**禁止**硬挂 material_check |
| ☑ | 冲突可视化说明 | instrumentConflictHint（对齐会议） |
| ☑ | 实验目的必填 | requireRemark + remarkLabel |
| ☑ | 耗材领用浅登记 | consumable_note + patchInstrument |
| ☑ | 导师同意 | requireConfirm 轻审 |
| ☑ | 机时费结算导出 | CSV；ReservationsAdmin |

三绿：`test_opening_map_skeleton_gate` + `test_reserve_thicken_features`（含 `test_instrument_r08_domain_skin`）。禁止域默认 `material_check`。

### R-09 能力岛加深（仅 cap 已挂）

| 勾选 | 依赖 cap | 项 |
|------|----------|-----|
| ☑ | staff_roster | HOSPITAL：值班展示文案；SlotBook 日历/当班列表 |
| ☑ | staff_roster | SALON：班次「请假/休息」挡班；StaffRosterStore.assertNotOnLeave |
| ☑ | lesson_pack | SALON：课时余次展示；到期前 3 天站内信 |
| ☑ | wallet | SALON：储值余额提示（/api/loyalty/me） |
| ☑ | gallery | SALON：作品集提示（详情页既有 gallery） |
| ☑ | room_equipment | MEETING：equip_borrow 借用录制设备勾选 |

硬约束：未挂对应 cap 时无 thicken 旗 / 无按钮。CARPASS 通行证交叉行留邻组。

三绿：`test_opening_map_skeleton_gate` + `test_reserve_thicken_features`（含 `test_r09_capability_islands`）。

### R-10 扫尾（收口）

| 勾选 | 项 |
|------|-----|
| ☑ | §1.7「本组待补」仅留 CARPASS 邻组交叉（非本组实现债） |
| ☑ | 不支持段只留边界：开门密码真短信、入住公安网、医保/道闸/OTA/门锁/HIS/高并发锁座 |
| ☑ | 地图 changelog 有 R-00～R-10 收口行 |
| ☑ | `test_opening_map_skeleton_gate` + `test_reserve_thicken_features` 绿 |
| ☑ | 本册总表全部 **已齐**；文首改为「已收口档案」 |

---

## 3. Changelog

| 日期 | 说明 |
|------|------|
| 2026-10-07 | 批次立项：R-00～R-10；对齐 §1.6 工序 |
| 2026-10-07 | R-00/R-01 已齐：通识十一钉；三套 SlotStore + DemoScheduleJobs；地图迁行 |
| 2026-10-07 | R-02 HOSPITAL 已齐；R-03 PARKING 已齐：超时加收/次卡/通行证/时长计费/罚则/拼单/overlapping |
| 2026-10-07 | R-04 MEETING 已齐：纪要/签到导出/冲突/录屏视频/周重复/审批/茶水设备/黑名单/门禁密码/签到码/最低时长/召开中 |
| 2026-10-07 | R-05 SALON 已齐：报到口令/时长占坑/队列号/改约手续费/迟到宽限/禁忌/扫码/到店次数；撤回域默认 wallet/gallery |
| 2026-10-08 | R-06 HOTEL 已齐：续住/延迟退房/证件脱敏/定金尾款/连住/早餐券/须知/加床/钟点房/同住/查房浅字段；未硬挂 material_check |
| 2026-10-08 | 纠偏：salon/hotel 业务阈值与须知开关收回 AppPolicy，不再写 thesis yml（param-placement） |
| 2026-10-08 | 预约侧通识与域皮键一并下沉 AppPolicy（取消/改约/提醒/爽约/迟到/黑名单/医院/车位/会议等），`_patch_thesis_yml` 不再发射 slot_reserve 业务键 |
| 2026-10-08 | R-07 CARRENT 已齐：违章预留押/验车浅字段/里程超支/导航外链/保险/驾照期/违章附件/ETC；未硬挂 material_check/rental_bond |
| 2026-10-08 | R-08 INSTRUMENT 已齐：超时计费/培训浅勾选/冲突说明/实验目的/耗材登记/导师轻审/机时费导出；未硬挂 material_check |
| 2026-10-08 | R-09 能力岛加深已齐：排班值班/请假挡班、课时余次与到期信、储值/作品集文案、会议录制设备借用；仅 cap 已挂 |
| 2026-10-08 | R-10 收口：本组实现债清零；待补仅 CARPASS 邻组；不支持只留边界；本册改已收口档案 |
| 2026-10-08 | loyalty：无 order_lines 时开题写到「储值/余额」仍可挂 wallet（美业）；误带仍剥 |
