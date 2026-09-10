# 领域清单（组 A–H）

> **本文只负责**：薄域 DOM 分组、GENERIC/ARCH 绑壳、Path B 真交叉白名单与答辩口径。  
> **交接**：[HANDOFF.md](../HANDOFF.md) · **总览**：[README.md](../README.md) · **索引**：[README.md](./README.md)

---

薄配置，不是厚代码包。按**能力组合**分组；同组共享同一套运行时，差别主要在 schema 文案/种子/菜单。组 **H** 为真交叉（两套玩法）。

| 相关专题 | 链接 |
|----------|------|
| 能力组合含义 | [`capabilities.md`](./capabilities.md) |
| 换皮 ID 册 / 组审进度 | [`domain-skin-gap-analysis.md`](./domain-skin-gap-analysis.md) |
| 怎么审交付 | [`delivery-audit-rules.md`](./delivery-audit-rules.md) |

### A. 借用 / 占用流（能力齐，可先薄落地）

| 领域 ID | 覆盖题目关键词 | 能力组合 |
|---------|----------------|----------|
| **DOM-LIBRARY** | 图书、图书馆、借阅、读者 | archive + ticket_flow + quota + deadline + content + org_users |
| **DOM-EQUIP** | 设备借用、器材、实验室物资 | 同上 |
| **DOM-ASSET** | 固定资产领用、耗材申领、物资台账、浅进销存 | archive + ticket_flow + quota + content + org_users + **stock_io**（无 deadline；与 EQUIP 设备借用区分；≠ 采购申购） |
| **DOM-CRM** | 客户关系、客户跟进、销售线索 | archive + ticket_flow + content + org_users（轻量跟进单；不接公海/外呼） |
| **DOM-EVENT** | 事件上报、公卫/院感、晨检随访、健康监测、隐患上报 | archive + ticket_flow + **archive_log** + content + org_users（档案 `event_case`、单据 `event_report`、记录 `archive_log`） |
| **DOM-ATTEND** | 考勤请假、请销假、假勤台账 | archive + ticket_flow + content + org_users（人员 `staff_person`、请假 `leave_req`） |
| **DOM-FUND** | 资助、奖学金、助学金、困难补助申请 | archive + ticket_flow + content + org_users（项目 `fund_program`、申请 `fund_apply`） |
| **DOM-LABSAFE** | 实验室安全准入、入室许可、安全培训证明 | archive + ticket_flow + content + org_users（实验室 `lab_room`、准入 `access_apply`）；开题写准入考试 → 另挂 **exam**（先考后申） |
| **DOM-RECRUIT** | 校园招聘、岗位发布、简历投递 | archive + ticket_flow + content + org_users（岗位 `job_post`、投递 `job_apply`） |
| **DOM-GRADE** | 教务成绩、补考/成绩更正申请 | archive + ticket_flow + content + org_users（课程 `course_item`、申请 `grade_apply`）；我的成绩申请填单优先；演示库按学号软筛本人课（无匹配回退开放课） |
| **DOM-INTERN** | 实习岗位、实习周报审阅、鉴定本地签章 | archive + ticket_flow + content + org_users + **e_sign**（实习岗 `intern_post`、周报 `week_report`；≠ CA）；默认我的周报填单选岗；开题绑岗→资料 `internOrg`/`internPost` + matchProfileRoom |
| **DOM-PARCEL** | 校园快递驿站、取件核销 | archive + ticket_flow + quota + content + org_users（包裹 `parcel`、取件 `parcel_claim`）；我的取件 + 手机号本人件硬筛 + 凭码 |
| **DOM-SEAL** | 用章、印章申请、公章使用 | archive + ticket_flow + content + org_users（事项 `seal_item`、申请 `seal_apply`） |
| **DOM-FLEET** | 用车申请、公务用车、派车 | archive + ticket_flow + content + org_users（车辆 `fleet_vehicle`、申请 `fleet_apply`） |
| **DOM-CERT** | 开具证明、在读/在职/成绩单证明 | archive + ticket_flow + content + org_users（类型 `cert_type`、申请 `cert_apply`） |
| **DOM-PROMO** | 横幅/海报/户外宣传审批 | archive + ticket_flow + content + org_users（事项 `promo_matter`、审批 `promo_apply`） |
| **DOM-FITOUT** | 装修备案、进场施工 | archive + ticket_flow + content + org_users（区域 `fitout_site`、备案 `fitout_apply`） |
| **DOM-ACAD** | 学籍异动、转专业、缓考/休复学 | archive + ticket_flow + content + org_users（事项 `acad_matter`、申请 `acad_apply`） |
| **DOM-TRIP** | 出差、加班审批 | archive + ticket_flow + content + org_users（事项 `trip_matter`、单 `trip_apply`） |
| **DOM-EXPENSE** | 经费报销、差旅报销（演示级） | archive + ticket_flow + content + org_users（项目 `expense_project`、报销 `expense_apply`） |
| **DOM-CREDIT** | 第二课堂、素拓学分认定 | archive + ticket_flow + content + org_users（项目 `credit_item`、认定 `credit_apply`） |
| **DOM-LABOR** | 劳动教育、志愿时长认定 | archive + ticket_flow + content + org_users（项目 `labor_item`、认定 `labor_apply`） |
| **DOM-EVAL** | 网上评教、教学评价（多维+评语+可选匿名） | archive + ticket_flow + content + org_users + **rating_dims**（课程 `eval_course`、评教卷 `eval_sheet`） |
| **DOM-MORAL** | 综测、德育分加减分申报 | archive + ticket_flow + content + org_users（指标 `moral_item`、申请 `moral_apply`） |
| **DOM-AWARD** | 创新学分、竞赛获奖登记 | archive + ticket_flow + content + org_users（类型 `award_item`、登记 `award_apply`） |
| **DOM-BED** | 床位分配、选房、调宿/退宿 | archive + ticket_flow + **quota** + content + org_users + **bed_occupy**（床位 `bed`、申请 `bed_apply`） |
| **DOM-CHECKIN** | 查寝、本人寝室归寝登记审核、口令签到、缺勤 | archive + ticket_flow + **quota** + content + org_users + **checkin**（资料绑楼栋/房间 + `matchProfileRoom`；寝室 `dorm_room`、登记 `checkin_apply`；主路径「我的归寝」；非直签） |
| **DOM-MUTUAL-TUTOR** | 导师双选 | archive + ticket_flow + **quota** + content + org_users + **mutual_select** |
| **DOM-MUTUAL-TOPIC** | 毕设选题双选 | 同上（选题档案） |
| **DOM-MUTUAL-TEAM** | 竞赛组队/学习搭子 | 同上（组队资料） |
| **DOM-VISITOR** | 访客登记、临时门禁申请 | archive + ticket_flow + **quota** + content + org_users + **pass_code** |
| **DOM-CARPASS** | 车辆通行证、临时车牌备案 | archive + ticket_flow + **quota** + content + org_users + **pass_code** |
| **DOM-LISTING** | 房源挂牌、带看意向跟进 | archive + ticket_flow + content + org_users |
| **DOM-PROCURE** | 采购申购、物资申购单 | archive + ticket_flow + **quota** + content + org_users |
| **DOM-CLUB** | 社团注册、年审材料 | archive + ticket_flow + content + org_users |
| **DOM-PROJ** | 大创/项目申报、中期检查 | archive + ticket_flow + content + org_users |
| **DOM-ETHIC** | 伦理审查、开题答辩材料 | archive + ticket_flow + content + org_users |
| **DOM-PARTY** | 党员发展、入党阶段材料 | archive + ticket_flow + content + org_users |
| **DOM-CONTRACT** | 合同登记、单级审批 | archive + ticket_flow + content + org_users |
| **DOM-INSTRUMENT** | 大型仪器借用 + 机时预约 | archive + ticket_flow + **slot_reserve** + quota + deadline + content + org_users + **instrument_slot** |
| **DOM-EXAM** | 在线考试、题库、组卷、结业考、党建/驾校/安全答题皮 | archive + **exam** + content + org_users（无单据；刷题/解析/限时/次数/排行/错题本开题按需） |
| **DOM-SURVEY** | 问卷调查、满意度调研、简易量表（非评教/非考试） | archive + **survey** + content + org_users（无单据；配置/填写/回收统计） |
| **DOM-VOTE** | 投票评选、十佳选票、结果公示（非报名） | archive + **vote** + content + org_users（无单据；候选人/限票/计票） |
| **DOM-DOCLIB** | 知识库/文库资料下载台账（非借阅/非博客） | archive + **doclib** + content + org_users（无单据；附件权限/下载台账） |
| **DOM-CARPOOL** | 拼车/结伴行程与同行意向（非地图） | archive + ticket_flow + **quota** + content + org_users（行程 `trip_route`、意向 `carpool_intent`） |
| **DOM-TIMEBANK** | 时间银行志愿时长账户存取核销 | archive + ticket_flow + content + org_users + **timebank**（服务事项、账户/流水、核销扣减；无 quota） |

### B. 报修 / 工单流（能力齐）

| 领域 ID | 覆盖题目关键词 | 能力组合 |
|---------|----------------|----------|
| **DOM-DORM** | 宿舍报修、水电、寝室 | ticket_flow + content + org_users（±archive）；报修表单按资料楼栋/房间预填 lookup |
| **DOM-PROPERTY** | 物业报修、社区维修 | 同上（house* / 校园皮 dorm*） |
| **DOM-IT** | 校园网报修、IT 运维工单 | 同上 |

### C. 报名 / 申请流（能力齐）

| 领域 ID | 覆盖题目关键词 | 能力组合 |
|---------|----------------|----------|
| **DOM-ACTIVITY** | 社团活动、志愿活动报名 | archive + ticket_flow + quota + content + org_users + **time_conflict** + **checkin**；开题写报名+投票 → 另挂 **vote**（C-11） |
| **DOM-LOST** | 失物招领；宠物领养（认领壳换皮） | archive + ticket_flow + **quota** + content + org_users |
| **DOM-COURSE** | 选课、公选课（名额） | archive + ticket_flow + quota + content + org_users + **time_conflict**（+ L1 互斥/分类限额） |
| **DOM-TOUR** | 旅行社线路、跟团游报名、出团确认 | archive + ticket_flow + **quota** + content + org_users（线路 `tour_line`、报名 `tour_signup`；≠酒店≠校园活动≠拼车≠出差） |

### D. 交易 / 点餐（`order_lines` 已开）

| 领域 ID | 覆盖题目关键词 | 能力组合 |
|---------|----------------|----------|
| **DOM-SHOP** | 商城、二手、购物车、订单 | archive + order_lines + quota + content + org_users + **guestbook** + **favorites**（开题可再扫 coupon / loyalty / order_review / 联想·足迹·多图） |
| **DOM-FOOD** | 食堂、点餐、外卖档口 | 同上 |
| **DOM-CINEMA** | 影院选座购票、座位图占座 | archive + order_lines + quota + content + org_users + **seat_select**（场次 `cinema_show`、座位 `cinema_seat`；无购物车主路径） |

交易答辩口径：下单 → 管理确认/发货 → 用户看物流轨迹 → 完成；可选领券核销、售后、收藏再加购、评价。影院为选座确认后即时占座生成订单。

### E. 预约流（`slot_reserve` 已开）

| 领域 ID | 覆盖题目关键词 | 能力组合 |
|---------|----------------|----------|
| **DOM-HOSPITAL** | 挂号、门诊预约、宠物医院挂号、疫苗/HPV 接种预约 | archive + slot_reserve + content + org_users |
| **DOM-PARKING** | 车位预约 | archive + slot_reserve + content + org_users |
| **DOM-MEETING** | 会议室 / 球馆 / 自习室 / 座位占坑预约 | archive + slot_reserve + content + org_users |
| **DOM-SALON** | 美发美容 / 健身私教服务预约 | archive + slot_reserve + content + org_users |
| **DOM-HOTEL** | 宾馆客房 | archive + slot_reserve + order_lines + content + org_users |

预约答辩口径：选时段占坑 →（可选确认）→ 管理端履约办结 / 用户取消或改约。状态含 `completed`（入场/就诊/到店/入住离店等文案随 schema）。

### F. 兜底

| 领域 ID | 覆盖 | 能力 |
|---------|------|------|
| **DOM-GENERIC** | 对不上具体行业关键词时的兜底域 | 按 **ARCH-*** 绑壳：CRUD / FLOW / TRADE / RESERVE（见下） |

未命中具体 `DOM-*` 时 **禁止**误落 LIBRARY：`score_catalog(..., fallback="DOM-GENERIC")`。  
匹配原则：**行为词桶（ARCH）有上限**，不堆行业百科；具体 DOM 若盖不住原型能力 → 降 `DOM-GENERIC`（`reconcile_match`）。  
上传开题时对**全文**匹配，并优先加权「主要功能 / 研究内容」段（`proposal_focus_for_match`）：开题写到的行为应对齐可交付壳。  
小程序/人脸/真支付等 L3 与业务过重信号 → **`accept=reject`（Path B）**，不可 degraded 出 ZIP。  
**多主路径**：功能段命中多条 ARCH 时写入 `archetypes` 并集；须命中交叉白名单且 `defense_ready`（见下节），否则 reject。  
GENERIC SQL 由 `sql/compose` 拼装；前端 `withExtraBizRoutes` 追加预约/订单路由。
GENERIC 再按原型选 SQL/runtime/gate（`archetype_shells.py`）：

| ARCH | 能力 | bake SQL |
|------|------|----------|
| ARCH-CRUD | archive + content + org_users | `DOM-GENERIC.sql` |
| ARCH-FLOW / STOCK / CONTENT | + ticket_flow（±quota） | `DOM-GENERIC-FLOW.sql` |
| ARCH-TRADE | + order_lines + **guestbook**（+ 默认 **favorites**） | `DOM-GENERIC-TRADE.sql` |
| ARCH-RESERVE | + slot_reserve | `DOM-GENERIC-RESERVE.sql` |

### G. 内容 / 媒资 / 社区（能力齐，可薄落地）

| 领域 ID | 覆盖题目关键词 | 能力组合 |
|---------|----------------|----------|
| **DOM-MEDIA** | 影视、电影、电视剧、综艺、视频点播、在线视频、片库 | archive + **favorites** + content + org_users + recommend |
| **DOM-MUSIC** | 音乐、歌曲、歌单、在线音乐、音乐播放器、听歌 | 同上 |
| **DOM-FORUM** | 论坛、BBS、贴吧、社区帖子、板块 | archive + ticket_flow + content + org_users + recommend |
| **DOM-BLOG** | 博客、个人博客、文章系统、资讯发布、CMS | archive + favorites + content + org_users + recommend |

**媒资（MEDIA/MUSIC）**：播放为外链 / HTML5（`isbn` 映射播放链接）；收藏走即时 `favorites`（`user_favorite`），**无审核单据**。影院选座购票走 **DOM-CINEMA**；不接直播、转码 CDN。

**论坛 / 博客（FORUM/BLOG）** — 薄配置语义（复用 archive；FORUM 另挂 reply 审核，BLOG 收藏同媒资即时收藏）：

| 概念 | 运行时映射 | 说明 |
|------|------------|------|
| 板块 / 分类 | `category` | 总管主数据 |
| 版主任职（FORUM） | `board_moderator` | 子管挂板块；种子/ER 用，非厚 Store |
| 主帖 / 文章 | archive 主表（`post` / `article`） | FORUM：用户可发帖即时可见，站长软删下架；BLOG：总管 CRUD；`isbn`=`TEXT` 富文本 HTML（`type: richtext`） |
| 标签 / 附件（FORUM） | `tag` + `post_tag` + `post_attach` / `reply_attach` | 补齐库表与 ER；运行时仍以 archive+reply 为主路径 |
| **回复 / 楼层（FORUM）** | `ticket_flow`（`reply`） | 挂主帖；`remark`=富文本；`allow_multi_ticket` 可多次跟帖 |
| 收藏 / 订阅（BLOG） | `favorites`（`user_favorite`） | 读者一键收藏，无编辑确认 |
| 站内公告 | `content` | 与帖文分离，勿混用 |
| 猜你喜欢 | `recommend` | 分类偏好 + 热度 + 上新 |

**富文本（在范围内）**：基线 `RichTextEditor` / `RichTextView`（粗斜体、列表、链接；前端消毒）。主帖/文章与论坛回复走富文本；**不是**多人协同编辑。

**楼中楼（FORUM，在范围内）**：同一主帖下多条回复即楼层；「回复某人」用正文 `@昵称` 一层引用。不接无限深度树形引擎。

**刻意不接（reject / out_of_mvp）**：WebSocket/IM SDK 实时推送、富文本协同编辑、人脸、协同过滤/深度推荐、物联网、真支付、小程序/安卓原生、大数据作业等（见 `OUT_OF_SCOPE_SIGNALS`）。毕设级一对一私信已落地为 `dm`（短轮询）。域目录 `out_of_mvp` 只是壳默认示意，可改 `domains_catalog/` 各条目；项目交付清单由 `compose_out_of_mvp`（相关默认项 ∪ 开题扫词）合成。

轻量「猜你喜欢」（`recommend` 能力）：档案域按分类偏好 + 热度 + 上新兜底，挂 LIBRARY / EQUIP / MEDIA / MUSIC / FORUM / BLOG；**不是**协同过滤。

### H. 真交叉（专科/本科·课设常见；Path B 已可 full）

与组 A～G **单域换皮**并列；开题写清**两套玩法**时匹配降 `DOM-GENERIC` 并保留行为并集（不再挤掉借用/审核）。  
样例开题（可上传匹配）：
- X-BORROW-SHOP：`data/samples/快速试传/图书借阅与二手交叉开题.txt`；`交叉预设开题/X-01-*.txt`（点餐+报修）
- X-BORROW-RESERVE：`data/samples/交叉预设开题/X-02-*.txt`（图书+座位；仪器借+机时 → DOM-INSTRUMENT）
- X-SHOP-RESERVE：`data/samples/交叉预设开题/X-03-*.txt`
三合一 / 智慧校园大杂烩 → reject。宾馆客房预约+附加消费 → 具名 DOM-HOTEL（非本交叉壳）。

| 交叉 ID | 覆盖题目关键词（开题常见说法） | 两套玩法 | 生成落点 | 状态 |
|---------|-------------------------------|----------|----------|------|
| **X-BORROW-SHOP** | 二手/跳蚤 + 借阅；点餐 + 报修；闲置交易 + 物品借用 | 申请/借用审核 + 购物车下单 | GENERIC 单据壳 + 订单路由 | ✅ |
| **X-BORROW-RESERVE** | 图书借阅 + 座位预约；场地预约 + 设备借用；报修 + 活动室预约 | 申请/借用审核 + 时段占坑 | GENERIC 单据壳 + 预约路由 | ✅ |
| **X-SHOP-RESERVE** | 小卖部 + 会议室预约；到店预约 + 卖套餐（非宾馆） | 下单 + 时段占坑 | GENERIC 订单壳 + 预约路由 | ✅ |
| （具名优先） | 宾馆 / 民宿 / 酒店客房 + 附加消费 | 预约 + 订单 | **DOM-HOTEL** 单域 | ✅ 走组 E |
| — | 借阅+二手+预约三套；智慧校园 N 合一 | — | reject / 裁成上表一条 | ❌ |

**答辩演示（三条共用口径，种子账号 bake 后见交付 README）**  
1. 借用+下单：门户提交借阅 → 管理端审核；再加购下单 → 订单办理。  
2. 借用+预约：借阅审核一路 + 选资源约时段（约满不可再约）一路。  
3. 下单+预约：约时段一路 + 购物车订单一路（宾馆题优先 DOM-HOTEL）。

匹配原则（`reconcile_match`）：行业皮盖不住开题里任一主路径 → **改用通用壳，保留全部路径**（禁止「留商城、丢借阅」）。

**Path B 白名单**（`cross_paths.py`）：上表三条可 full；实现键内部为 FT/FR/TR。  
SQL golden：`DOM-GENERIC__ARCH-FLOW_ARCH-TRADE` / `…FLOW_ARCH-RESERVE` / `…TRADE_ARCH-RESERVE`。  
**禁止**：DOM×DOM 厚融合；L3；硕博；真实业务全流程；三合一装全文。  
代码：`evaluate_cross_path` + `reconcile_match` + `resolve_accept`。

**覆盖率怎么理解**：A+B+C+D+E+F+G+**H（真交叉三条）** ≈ 常见 Web 管理类毕设主体；不是 100% 开题都能 full。L3 / 三合一 → **reject**（Path B）。

---
