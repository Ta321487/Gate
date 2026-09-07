# 开题密功能 → 工厂交付对照表

> **用途**：接单 / 匹配 / bake 时查「开题写了啥、工厂落哪、别踢错壳」。  
> **搭配**：主链路 [`delivery-audit-rules.md`](./delivery-audit-rules.md)；缺口立项 [`domain-skin-gap-analysis.md`](./domain-skin-gap-analysis.md)；AI 专项 [`ai-opening-delivery-map.md`](./ai-opening-delivery-map.md)；域表 [`HANDOFF.md`](../HANDOFF.md)。  
> **覆盖**：工厂现网 **68 个域**全索引（按 `DOMAIN_GROUPS`）；详表补高频组。  
> **素材**：近约十年国内本科毕设常见模块 + 工厂能力。表是活的，撞到新高频点就加行。

**状态**：`有` / `扫词开` / `演示` / `不做` / `缺口` / `部分有`

**匹配**：附属审核/库存等勿无故降 `DOM-GENERIC`（`catalog.reconcile_match` soft）。真交叉（如借阅+座位）仍可降通用。

---

## 0. 横切（各域开题都爱写）

| 开题常写 | 工厂落点 | 状态 | 匹配注意 |
|----------|----------|------|----------|
| 登录/注册/改密/头像资料 | 基线 auth + profile | 有 | — |
| 验证码 | captcha | 有 | — |
| 用户/管理分端；子管岗 | role + staff_post | 有 | 勿新开 DOM |
| 公告/资讯/轮播 | content / notice | 有 | 勿当资讯站主业 |
| 留言/意见反馈 | guestbook | 有/扫词 | 勿当 IM |
| 私信/在线客服 | dm | 扫词开 | 非 WebSocket |
| 收藏 | favorites | 扫词开 | — |
| 评价/回复/删评 | order_review 等 | 扫词开 | — |
| 上传图片 | upload | 有 | — |
| 统计图/数据分析 | 工作台 ECharts | 演示 | 勿吹大数据平台 |
| 审核/审批/通过驳回 | 各域状态机 | 有/演示 | 附属审核勿乱抬 ARCH-FLOW 改通用 |
| 库存/库存预警 | stock；进销存另壳 | 有/演示 | 商城/点餐 soft 掉 ARCH-STOCK |
| 支付/支付宝/微信 | demoPay / 余额演示 | 演示 | 真支付=不做；文献噪声须裁 |
| 小程序/uni-app/Django/Android | — | 不做 | 裁参考文献后仍点名才报警 |
| 协同过滤/人脸/真地图/物联网 | — | 不做 | OUT_OF_SCOPE |
| AI 客服/大模型问答 | ai_assistant | 扫词开 | 见 AI 对照表 |

---

## 1. 全域索引（68）

每域一行：主业积木 + 开题常塞密功能 + 匹配注意。高频细节见 §2。

### 1.1 借用/占用（`borrow`）

| 域 | 主业积木 | 开题密功能（常写） | 匹配注意 |
|----|----------|--------------------|----------|
| `DOM-LIBRARY` 图书 | archive、ticket_flow、quota、deadline、content、org_users、recommend | 借还续借超期罚款荐购 | 座位预约=真交叉可降通用；论坛扩展点名再挂 |
| `DOM-EQUIP` 设备借用 | archive、ticket_flow、quota、deadline、content、org_users、recommend | 借用归还超期损坏赔付预约排队 | 附属审核保本域 |
| `DOM-ASSET` 物资领用 | archive、ticket_flow、quota、content、org_users、stock_io | 领用审批库存出入库盘点 | stock_io 真进销存；勿与商城库存预警混 |
| `DOM-CRM` 客户跟进 | archive、ticket_flow、content、org_users | 线索跟进回访成交公海 | 家访/学院背景不压销售档 |
| `DOM-EVENT` 事件上报 | archive、ticket_flow、archive_log、content、org_users | 上报审核排查晨午检处置闭环 | 食安排查≠点餐 |
| `DOM-ATTEND` 考勤请假 | archive、ticket_flow、content、org_users | 请假销假审批班次补卡 | 人脸/GPS 打卡=不做 |
| `DOM-FUND` 资助奖学金 | archive、ticket_flow、content、org_users | 资助申请材料审核公示发放 | 附属审保本域 |
| `DOM-LABSAFE` 实验室安全准入 | archive、ticket_flow、content、org_users | 准入培训考试许可到期 | 可叠考试能力 |
| `DOM-RECRUIT` 招聘投递 | archive、ticket_flow、content、org_users | 岗位投递初筛面试录用 | 接单≠购物车交易 |
| `DOM-DATING` 婚恋交友 | archive、ticket_flow、content、org_users、dm | 资料匹配私信举报审核 | dm 常挂；真婚恋推荐算法=不做 |
| `DOM-GRADE` 教务成绩 | archive、ticket_flow、content、org_users | 成绩录入复核申诉发布 | 附属审保本域 |
| `DOM-INTERN` 实习周报 | archive、ticket_flow、content、org_users、e_sign | 实习岗位周报签核电子签 | e_sign 扫词 |
| `DOM-PARCEL` 快递驿站 | archive、ticket_flow、quota、content、org_users | 到件取件核销滞留催领 | 勿与跑腿代买商城混 |
| `DOM-SEAL` 用章申请 | archive、ticket_flow、content、org_users | 用印申请审批用后登记 | 附属审=主路径正常 |
| `DOM-FLEET` 用车申请 | archive、ticket_flow、content、org_users | 用车申请派车里程归还 | 附属审保本域 |
| `DOM-CERT` 开具证明 | archive、ticket_flow、content、org_users | 证明开具审批打印领取 | 附属审保本域 |
| `DOM-PROMO` 宣传审批 | archive、ticket_flow、content、org_users | 宣传品申请审核制作发放 | 附属审保本域 |
| `DOM-FITOUT` 装修备案 | archive、ticket_flow、content、org_users | 装修申报审批验收巡查 | 社区/企业场景 |
| `DOM-ACAD` 学籍异动 | archive、ticket_flow、content、org_users | 学术活动申报审核场地 | 可叠活动/预约词，保本域优先 |
| `DOM-TRIP` 出差加班 | archive、ticket_flow、content、org_users | 出差申请审批报销关联 | 可叠报销域交叉 |
| `DOM-EXPENSE` 经费报销 | archive、ticket_flow、content、org_users | 报销单发票审核付款 | 真财务对接=不做 |
| `DOM-CREDIT` 第二课堂认定 | archive、ticket_flow、content、org_users | 第二课堂学分申报认定审核 | 附属审保本域 |
| `DOM-LABOR` 劳动时长认定 | archive、ticket_flow、content、org_users | 劳动时长申报认定审核 | 附属审保本域 |
| `DOM-EVAL` 网上评教 | archive、ticket_flow、content、org_users、rating_dims | 测评问卷评分汇总审核 | 可叠问卷能力 |
| `DOM-MORAL` 综测申报 | archive、ticket_flow、content、org_users | 德育申报材料审核公示 | 附属审保本域 |
| `DOM-AWARD` 成果登记 | archive、ticket_flow、content、org_users | 成果登记审核认定展示 | 附属审保本域 |
| `DOM-BED` 床位分配 | archive、ticket_flow、quota、content、org_users、bed_occupy | 床位申请调宿审批分配 | 附属审保本域 |
| `DOM-CHECKIN` 查寝签到 | archive、ticket_flow、quota、content、org_users、checkin | 登记审核签到缺勤 | checkin 能力；非人脸 |
| `DOM-MUTUAL-TUTOR` 导师双选 | archive、ticket_flow、quota、content、org_users、mutual_select | 志愿双选匹配确认审核 | 匹配≠协同过滤 |
| `DOM-MUTUAL-TOPIC` 选题双选 | archive、ticket_flow、quota、content、org_users、mutual_select | 选题双选志愿确认审核 | 同上 |
| `DOM-MUTUAL-TEAM` 组队匹配 | archive、ticket_flow、quota、content、org_users、mutual_select | 组队匹配邀请确认 | 同上 |
| `DOM-VISITOR` 访客登记 | archive、ticket_flow、quota、content、org_users、pass_code | 访客预约审批签到通行证 | 预约词 soft 部分覆盖 |
| `DOM-CARPASS` 车辆通行证 | archive、ticket_flow、quota、content、org_users、pass_code | 车辆通行证申请审批进出 | 附属审保本域 |
| `DOM-LISTING` 房源带看 | archive、ticket_flow、content、org_users | 房源发布审核上下架带看 | 勿与商城交易壳混除非点名下单 |
| `DOM-PROCURE` 采购申购 | archive、ticket_flow、quota、content、org_users | 采购申请比价审批入库 | 可叠库存；勿误挂纯商城 |
| `DOM-CLUB` 社团年审 | archive、ticket_flow、content、org_users | 社团注册活动审批成员 | 可叠活动报名 |
| `DOM-PROJ` 项目申报 | archive、ticket_flow、content、org_users | 项目申报评审立项中期结题 | 附属审=主业 |
| `DOM-ETHIC` 材料审核 | archive、ticket_flow、content、org_users | 伦理审查申报会议批件 | 附属审=主业 |
| `DOM-PARTY` 党员发展 | archive、ticket_flow、content、org_users | 党员发展材料审核转正 | 附属审=主业 |
| `DOM-CONTRACT` 合同审批 | archive、ticket_flow、content、org_users | 合同起草审批签署归档 | e_sign 扫词；真 CA=不做 |
| `DOM-INSTRUMENT` 仪器机时 | archive、ticket_flow、slot_reserve、quota、deadline、content、org_users、instrument_slot | 仪器预约使用超时计费 | 可叠预约冲突 |
| `DOM-EXAM` 在线考试 | archive、exam、content、org_users | 组卷考试阅卷错题本 | 考试能力；监考人脸=不做 |
| `DOM-SURVEY` 问卷调研 | archive、survey、content、org_users | 问卷发布填写统计导出 | survey 能力 |
| `DOM-VOTE` 投票评选 | archive、vote、content、org_users | 投票候选项计票公示 | vote 能力 |
| `DOM-DOCLIB` 文库资料 | archive、doclib、content、org_users | 资料上传分类下载台账 | 勿冒充 AI 知识库/RAG |
| `DOM-CARPOOL` 拼车结伴 | archive、ticket_flow、quota、content、org_users | 拼车发布预约成行取消 | 真地图=不做 |
| `DOM-TIMEBANK` 时间银行 | archive、ticket_flow、content、org_users、timebank | 服务发布兑换时长结算 | 时长演示 |
| `DOM-CINEMA` 影院选座 | archive、order_lines、quota、content、org_users、seat_select | 排片选座下单出票退票 | 交易壳；占座≠场地预约壳 |

### 1.2 报修/工单（`ticket`）

| 域 | 主业积木 | 开题密功能（常写） | 匹配注意 |
|----|----------|--------------------|----------|
| `DOM-DORM` 宿舍 | ticket_flow、content、org_users | 宿舍报修派单跟进评价 | 工单主路径；催办演示 |
| `DOM-PROPERTY` 物业报修 | ticket_flow、content、org_users | 物业报修派单巡查评价 | 同上；缴费另说 |
| `DOM-IT` IT 报修 | ticket_flow、content、org_users | IT 报修派单资产关联 | 同上 |

### 1.3 报名/申请（`apply`）

| 域 | 主业积木 | 开题密功能（常写） | 匹配注意 |
|----|----------|--------------------|----------|
| `DOM-ACTIVITY` 活动报名 | archive、ticket_flow、quota、content、org_users、time_conflict、checkin | 报名名额审核签到证书票务 | 签到扫词；证书部分有 |
| `DOM-LOST` 失物招领 | archive、ticket_flow、quota、content、org_users | 失物登记认领审核招领 | 领养/捐赠细档见深皮 |
| `DOM-COURSE` 选课 | archive、ticket_flow、quota、content、org_users、time_conflict | 选课名额退改审核冲突 | 证书报考对比勿抬错 |
| `DOM-TOUR` 旅行社线路 | archive、ticket_flow、quota、content、org_users | 线路报名审核缴费出团 | 演示支付 |

### 1.4 交易（`trade`）

| 域 | 主业积木 | 开题密功能（常写） | 匹配注意 |
|----|----------|--------------------|----------|
| `DOM-SHOP` 商城 | archive、order_lines、quota、content、org_users、guestbook | 多店入驻审库存预警双通道留言假支付评价售后 | soft FLOW/STOCK；保 SHOP |
| `DOM-FOOD` 点餐 | archive、order_lines、quota、content、org_users、guestbook | 档口库存配送评价支付 | soft FLOW/STOCK；食安≠点餐 |

### 1.5 预约（`reserve`）

| 域 | 主业积木 | 开题密功能（常写） | 匹配注意 |
|----|----------|--------------------|----------|
| `DOM-HOSPITAL` 医院 | archive、slot_reserve、content、org_users | 号源预约取消签到候诊 | soft FLOW；真支付=演示/不做 |
| `DOM-PARKING` 车位 | archive、slot_reserve、content、org_users | 车位预约缴费进出取消 | soft FLOW；道闸=不做 |
| `DOM-MEETING` 场地预约 | archive、slot_reserve、content、org_users | 会议室预约审批冲突签到 | soft FLOW |
| `DOM-SALON` 服务预约 | archive、slot_reserve、content、org_users | 项目预约技师取消支付 | soft FLOW |
| `DOM-HOTEL` 客房 | archive、slot_reserve、order_lines、content、org_users | 房型预订审核取消定金签到 | soft FLOW |
| `DOM-CARRENT` 汽车租赁 | archive、slot_reserve、order_lines、content、org_users | 租车预订审核取还车定金 | soft FLOW |

### 1.6 内容/媒资/社区（`content`）

| 域 | 主业积木 | 开题密功能（常写） | 匹配注意 |
|----|----------|--------------------|----------|
| `DOM-MEDIA` 影视综 | archive、favorites、content、org_users、recommend、guestbook | 影音上传分类审核播放 | 内容主业；勿用交易词改壳 |
| `DOM-MUSIC` 音乐 | archive、favorites、content、org_users、recommend、guestbook | 曲库点播收藏审核 | 同上 |
| `DOM-FORUM` 论坛 | archive、ticket_flow、content、org_users | 发帖回帖审帖举报私信 | dm 扫词；实时聊天室=不做 |
| `DOM-BLOG` 博客 | archive、favorites、content、org_users、recommend、guestbook | 文章发布审核专栏评论 | 内容主业 |

### 1.7 兜底（`fallback`）

| 域 | 主业积木 | 开题密功能（常写） | 匹配注意 |
|----|----------|--------------------|----------|
| `DOM-GENERIC` 通用 | archive、content、org_users | 仅真交叉兜底 | 能具名域勿落这里 |

> 本索引实列 **68** 行；`DOMAINS` 共 **68**。

---

## 2. 高频详表

### 2.1 商城 `DOM-SHOP`

| 开题常写 | 工厂落点 | 状态 | 匹配注意 |
|----------|----------|------|----------|
| 商品浏览/搜索/分类 | archive + category | 有 | — |
| 规格/产地/采摘/简介/图 | 农产皮 + gallery | 有/扫词 | 非农产勿灌农产列 |
| 购物车/下单/订单态 | order_lines | 有 | ARCH-TRADE |
| 收货地址 | addressBook | 有 | — |
| 收藏/评价/删评 | favorites / order_review | 扫词开 | 多店常开 |
| 假支付输密码 | demoPay | 演示 | 多店开 |
| 真微信支付/分账 | — | 不做 | — |
| 物流单号 | tracking | 演示 | — |
| 售后退货 | refund 态 | 有 | 勿改报修域 |
| 库存预警 | stockWarnBelow | 有/演示 | soft STOCK |
| 多商家/入驻/店铺资料 | shopMarketplace | 扫词开 | 保 SHOP |
| 商品审/强制下架/活动审 | audit + notice pending | 扫词开 | soft FLOW |
| 留言双通道/客服 dm | guestbook.channel / dm | 扫词开 | — |
| 数据分析 | DashboardCharts | 演示 | — |

### 2.2 点餐 `DOM-FOOD`

| 开题常写 | 工厂落点 | 状态 | 匹配注意 |
|----------|----------|------|----------|
| 菜品/分类/购物车/下单 | order 壳 | 有 | — |
| 堂食自取/配送骑手 | delivery 演示；真调度缺口 | 演示/缺口 | soft FLOW |
| 库存售罄/评价退单/支付 | stock / review / demoPay | 有/扫词/演示 | soft STOCK |
| 食安排查 | 勿挂 FOOD | — | 走 EVENT |

### 2.3 预约组 / 报修组 / 借阅·活动·论坛

| 范围 | 开题密功能 | 匹配注意 |
|------|------------|----------|
| 预约组（酒店车位会议医美租车医院） | 时段冲突审核取消签到定金 | 组内 soft FLOW；道闸=不做 |
| 报修组（宿舍物业 IT） | 派单跟进催办完结评价 | ARCH-FLOW；缴费分域 |
| LIBRARY | 续借超期；座位预约 | 座位=真交叉可降通用 |
| ACTIVITY | 名额审核签到证书票务 | 签到扫词 |
| FORUM | 审帖举报私信 | 实时聊天室=不做 |

---

## 3. 怎么用

1. 匹配：查 §1 落对 `DOM-*`；看「匹配注意」。  
2. 挂载：横切 + 本域密功能能挂则挂；`不做` 要提示。  
3. 缺口：进 gap 册立项。  
4. 扩表：改 §1 该行或 §2，并补测试。

## 4. 修订

| 日期 | 说明 |
|------|------|
| 2026-09-08 | 初版高频详表 |
| 2026-09-08 | 全 68 域索引按 DOMAIN_GROUPS 铺齐 |

