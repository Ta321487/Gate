# 开题密功能 → 工厂交付对照表

> **本文只负责**：开题常见功能 → 工厂落点与状态（已实现 / 扫词开 / 待补 / 不支持）。非 AI。  
> **不负责**：cap 定义与挂载细则（[`capabilities.md`](./capabilities.md)）；DOM 分组与域默认能力组合（[`domains.md`](./domains.md)）；换皮 ID 册（[`domain-skin-gap-analysis.md`](./domain-skin-gap-analysis.md)）；怎么审交付（[`delivery-audit-rules.md`](./delivery-audit-rules.md)）。  
> **索引**：[README.md](./README.md) · **AI 轴**：[`ai-opening-delivery-map.md`](./ai-opening-delivery-map.md) · **扩岛档案**（已收口）：[`capability-expansion-batch.md`](./capability-expansion-batch.md)。  
> **覆盖**：全 **68** 域。活表。  
> **口径**：全国专本科 **Web 管理类毕设**通识可交付（能注册、走主流程、能答辩）。**不**依赖工厂样例库，**不**绑某一所学校课表；按开题常写模块建库存。禁止用「演示级」打发已实现能力。  
> **库存原则**：工厂先列全「毕设常见且不超纲」功能；域壳仍可薄配置。开题命中才挂扫词项。挂载细节以 [`capabilities.md`](./capabilities.md) 为准；与本表冲突时只改一处并同步，禁止两套口径。  
> **齐度**：有「待补」=实现未齐，≠库存未列。超纲进「不支持」，不进待补装齐。压力测见下节。

## 压力测门（整模块级 · 真缺口）

按横切 + 10 组扫（**非** 68 域逐个过）。

**计入「真缺口新增」**（须同时满足）：

1. 开题目录里常见的**整块功能**（新菜单 / 新主状态机 / 新 cap，或能单写成「系统功能」一节）；**且**  
2. 本表**没有任何对应落点**（含换皮、壳附带、已有 cap/schema、已写明的不支持等价顶）。

**不计入**（可改修订备注，但数字记 0）：

- 边角加深（字段、文案、打印、计数榜、Toast…）— 有必要，往后稍稍  
- 给已有落点**补别名 / 换皮说明**（如心理咨询→预约皮）  
- 在已有「不支持」边上再写一条同类边界  

冻结：连续 **2** 轮真缺口新增 **= 0** → **已达成（第7～8轮）**。松口径第 1～10 轮、以及「整 1～5」里的别名/漏登记补行，**不作冻结依据**。

**停滴水**：物联网 / 闸机人脸 / 单体架构 / 真短信邮件 / 商户支付 等**已有不支持簇**时，不再把 POS、梯控、MQ、国密、开放平台细分条当成新真缺口计入（可写修订备注，数字仍为 0）。

**冻结后**：只改行状态或纠错；禁止用换皮别名 / 拆不支持簇刷「新增」。边角加深仍往后稍稍。

## 状态（只许这四类）

| 状态 | 含义 | bake？ |
|------|------|--------|
| **已实现** | 有表/接口/菜单/状态，出包可跑 | 能 |
| **扫词开** | 开题命中才挂进本包 | 命中则能 |
| **待补** | 缺实现（缺 Store/SQL/菜单/状态机之一），程序员应改代码 | 现不能，补后能 |
| **不支持** | 超工厂技术边界；**必须写清原因** | 不能，且不装能 |

## 不能 bake 怎么判（发现就改或标死）

1. **匹配错壳**（通用壳/邻域）→ 先修匹配 soft，再 bake。  
2. **壳对但缺能力**（开题写了催办，域默认无 `deadline`）→ **待补**，往 `DOMAIN_CAPABILITIES` / 扫词 / Store 补。  
3. **壳对且能力有** → 应能出包；出不了就查 bake 日志（缺门禁文件、SQL 失败等）当 bug 修。  
4. **要原生小程序 / 银行通道 / 人脸 / 真地图调度** → **不支持**，写原因；论文写本包已实现的等价流程（如系统内支付密码、站内私信）。

---

## 0. 横切

| 开题常写 | 工厂落点 | 状态 | 不能 bake 时原因 / 匹配注意 |
|----------|----------|------|------------------------------|
| 登录注册改密头像资料 | auth + profile | 已实现 | — |
| 验证码 | captcha | 已实现 | — |
| 用户端/管理端/子管商家岗 | role + staff_post | 已实现 | 勿新 DOM |
| 公告资讯轮播 | content / notice | 已实现 | — |
| 留言反馈 | guestbook | 域默认交易/内容壳；否则扫词开 | — |
| 条下评论（影音/曲库/博客详情） | item_comment | 扫词开 | ≠留言；论坛用回帖 |
| 私信在线客服 | dm | 扫词开（交易写「客服」即挂） | 不支持：第三方 IM / WebSocket 云信 |
| 收藏 | favorites | **域默认** SHOP/FOOD 与 MEDIA/MUSIC/BLOG；**开题写到才挂**：ACTIVITY/COURSE/TOUR/LOST/DATING 及其它 `order_lines` 壳 | 细则见 capabilities |
| 订单评价回复删评 | order_review | **域默认** SHOP/FOOD/HOTEL/CARRENT；否则扫词开 | ≠ 单据星级评价（报名组 `allowRating`） |
| 上传 | upload | 已实现 | — |
| 数据统计图表工作台 | ECharts 工作台 | 已实现 | 不支持：独立大数据平台 |
| 审核审批通过驳回 | 各域状态机 | 已实现 | 附属审勿抬 FLOW 改通用 |
| 库存库存预警 | stock；进销存 ASSET | 已实现 | 商城 soft STOCK |
| 支付宝微信+支付密码 | demoPay / 余额 | 已实现 | 不支持：对接微信/支付宝商户与银行清算 |
| 小程序 uni-app Django Android | — | 不支持 | 无对应物理骨架/技术主线 |
| 协同过滤人脸真地图物联网 | — | 不支持 | OUT_OF_SCOPE |
| 智能客服大模型问答 | ai_assistant | 扫词开 | 见 AI 表；不支持自训模型/RAG 工程冒充 |
| 操作/审计日志 | audit_log | **扫词开**（E-04 已齐） | 未写不挂；仅写登录日志则只记登录 |
| 站内消息模板 | message_template | **扫词开**（E-06 已齐） | 不支持：真短信/邮件通道 |
| 通行码/取件码二维码出示 | code_qr | **扫词开**（E-07 已齐） | 不支持：闸机硬件 |
| 技师/维修排班 | staff_roster | **扫词开**（E-09 已齐） | 不支持：智能排课 |
| 会议室设备清单 | room_equipment | **扫词开**（E-10 已齐） | ≠ 设备借用主路径 |
| 订单明细定制快照（刻字/规格图/待制作） | line_custom | **扫词开** | 不回写商品；≠ 独立礼品域 |
| 配送时段 / 当日达·预订 / 节日加价 | delivery_window | **扫词开** | ≠ 场地预约；≠ flash_price 冒充节日日历 |
| 购买审核 / 按人按月限购 | purchase_gate | **扫词开** | ≠ 医院处方开药 |
| 拼团成团 / 截止退款 | group_buy | **扫词开** | ≠ 活动报名 ≠ 拼车 |
| 盲盒概率池 / 保底 | blind_box | **扫词开** | 抽中才扣奖品库存；≠ 活动抽奖 |
| 寄卖质检上架 / 抽成提现 | consign | **扫词开** | ≠ 多商家入驻 |
| 按重量计价 / 次日达 / 损耗赔付 | weigh_sale | **扫词开** | 次日达复用配送时段 |
| 旧书回收估价上门再上架 | buyback | **扫词开** | ≠ 图书借阅 |
| 租赁押金 / 验损退押 / 三笔钱 | rental_bond | **扫词开** | CARRENT；≠ 设备借用 |
| 数字商品 / 激活码交付 / 不退 | digital_goods | **扫词开** | fulfillMode=digital；≠ 实体发货 |
| 积分赠分 / 兑换 / 抵扣；登录涨分；过期 | points（loyalty） | **窄扫** | 兑换≠抵扣≠仅写「积分」；签到/过期写到才挂 |
| 约拍套餐 / 交片 | shoot | **扫词开** | ≠ 选座 ≠ 点播 ≠ 场地座位 |
| 寄养按天 / 每日反馈 | boarding | **扫词开** | ≠ 挂号 ≠ 领养 ≠ 宠物咖啡 |
| 房态板 / 房态图 | room_board | **扫词开**（伞扫「酒店管理」三开） | HOTEL；民宿/寄养不挂；≠ OTA |
| 前台登记 / 退房结算 / 挂账 | front_desk | **扫词开**（依赖 room_board） | ≠ 活动口令签到 `checkin` |
| 客房保洁 / 清洁任务 | housekeeping | **扫词开**（依赖 room_board） | 裸「清洁工」不够；≠ 健身房保洁 |
| 场馆保洁 / 保洁任务 / 清洁管理 | venue_clean | **窄扫** | SALON/MEETING/PROPERTY；裸「清洁工」不够；≠ 酒店房态 `housekeeping` |
| 课时包消课退节 | lesson_pack | **扫词开** | ≠ 时间银行 ≠ 选课 |
| 优惠券领取核销过期 | coupon | **扫词开** | 交易壳；≠支付商户券平台 |
| 满减算价 | spend_discount | **扫词开** | 与券取更优；≠复杂促销引擎 |
| 会员等级折扣 | member_tier | **扫词开** | 成长档折扣；≠付费会员真清算 |
| 账户余额充值扣退 | wallet | **扫词开** | 系统内余额；≠微信商户 |
| 收货地址簿 | order_lines 壳附带 | 已实现 | 无独立 cap |
| 售后申请 / 物流轨迹 | order_lines 壳附带 | 已实现 | 无独立 cap |
| 预约改约 / 办结 | slot_reserve 壳附带 | 已实现 | 无独立 cap |
| 订单支付超时自动取消 | 扫词写配置 | 已实现 | 无独立 cap；`order-timeout-minutes` |
| 限时购 / 活动价窗口 | flash_price | **扫词开**（E-05） | ≠秒杀引擎；≠节日配送加价冒充 |
| 商品规格说明（非色码矩阵） | product_spec | **扫词开**（E-14） | ≠完整 SKU 库存矩阵 |
| 多维分类筛选 | multi_category | **扫词开** | SHOP/FOOD/CINEMA；两组维度才挂 |
| 商品标签多选 | product_tags | **扫词开** | ≠论坛帖标 |
| 详情独立属性列（品牌/材质等） | detail_attrs | **扫词开** | 开题点名详情字段才挂 |
| 猜你喜欢（非协同过滤） | recommend | **域默认** 多内容/借用壳；FORUM 开题才挂 | ≠协同过滤 |
| 点赞 | post_like | **扫词开**（E-03） | FORUM/BLOG/MEDIA/MUSIC |
| 举报处理 | content_report | **扫词开**（E-03） | FORUM/DATING/BLOG |
| 禁言 | post_mute | **扫词开**（E-12） | FORUM/BLOG |
| 搜索联想 + 热搜配置 | search_assist | **扫词开** | 标题前缀；≠ ES |
| 浏览足迹 | browse_history | **扫词开** | 最近约 20 条 |
| 档案多图相册 | gallery | **扫词开** | gallery_json；≠ SKU |
| 续借 | loan_renew | **域默认** LIBRARY/EQUIP/INSTRUMENT；其它开题才挂 | — |
| 图书预约 / 到书通知 | book_hold | **扫词开**（E-11） | ≠报名候补 |
| 图书丢失赔偿 | book_lost | **域默认** LIBRARY | ≠逾期罚款 |
| 图书荐购 | book_suggest | **扫词开**（E-13） | ≠采购壳 |
| 驿站寄件 | parcel_ship | **扫词开** | ≠电子面单 |
| 报废登记 | stock_scrap | **扫词开**（E-08） | 须 stock_io |
| 盘点调库 | stock_count | **扫词开**（E-08） | 须 stock_io |
| 三级审批 | multi_approve | **扫词开**（C-16） | ≠任意 BPM 设计器 |
| 本地签章留痕 | e_sign | **域默认** INTERN；其它开题才挂 | ≠法定 CA |
| 分类档案 CRUD / 检索详情 | archive | 已实现（基线脊柱） | 全业务对象壳 |
| 单据流（提交→审→完结） | ticket_flow | 已实现（基线脊柱） | — |
| 名额 / 库存占用与归还 | quota | 已实现（基线脊柱） | — |
| 购物车 + 多明细订单 | order_lines | 已实现（交易壳） | 系统内支付；影院选座无购物车主路径 |
| 资源时段占坑预约 | slot_reserve | 已实现（预约壳） | ≠本人已选时段相交 `time_conflict` |
| 自选借期 / 申请数量 | pickLoanPeriod + allowQty | 已实现（L0 schema） | LIBRARY/EQUIP 默认 |
| 强制附件 | requireAttach | 已实现（L1 schema） | LOST 等默认；开题写证明必传 |
| 必填说明 / 起止日期 | requireRemark + pickDateRange | 已实现（L0 schema） | 请假/用途等 |
| 点餐骑手岗（接单配送） | staff_post 扫词 | **扫词开** | FOOD；≠独立骑手 App / 实时调度 |
| 名额候补 / FIFO 递补 | waitlist | **域默认** ACTIVITY/COURSE；TOUR/LOST 扫词开 | ≠图书预约 |
| 口令签到 / 爽约缺勤 | checkin | **域默认** ACTIVITY/CHECKIN | ≠人脸；≠前台登记 |
| 单据星级评价（非订单评） | allowRating（schema） | **域默认** ACTIVITY/LOST/TOUR 等 | ≠ `order_review` |
| 用户投稿 / 发帖上架 | userPublish（schema） | **扫词开** | 内容壳；细则见 difficulty L0 |
| 时段冲突检测 | time_conflict | 已实现（壳规则） | 选课/活动等；无时段列则跳过 |
| 到期 / 处理时限催办 | deadline | **域默认** 借用与报修三域、**PARCEL 催领**；借还壳另含应还日前 N 天站内提前催还 | 站内催办；≠短信 |
| 超期达 N 次限制再借 | ticket.maxOverdueTimes | **开题扫** | ≠征信 |
| 低库存站内信提醒 | stockWarnNotify | **开题扫**（须 stock_io）；工作台图表默认有 | ≠短信 |
| 出入库流水 | stock_io | **域默认** ASSET | ≠多仓 WMS |
| 额度台账扣减 | balance_ledger | **域默认** 报销/用印/综测等 | ≠银企 |
| 申请材料清单必传 | material_check | **域默认** 证明/社团/大创等 | — |
| 占用时段台账 | occupy_span | **域默认** 请假/用车/出差等 | 含冲突 |
| 通行码字符串签发 | pass_code | **域默认** VISITOR/CARPASS | 叠 code_qr 才出二维码 |
| 影院选座占座 | seat_select | **域默认** CINEMA | ≠场地预约；≠高并发锁 |
| 档案监测打卡 | archive_log | **域默认** EVENT；其它开题才挂 | 晨午检等 |
| 驿站货架柜格 | parcel_shelf | **域默认** PARCEL | ≠柜机硬件 |
| 失物认领凭证核验 | claim_proof | **域默认** LOST | — |
| 失物路人线索 | lost_clue | **域默认** LOST | 可游客 |
| 志愿双选接受/婉拒/调剂 | mutual_select | **域默认** MUTUAL-* | — |
| 评教多维评分 | rating_dims | **域默认** EVAL | ≠问卷 SURVEY |
| 二级审批（schema） | difficulty L1 | 已实现（扫词/配置） | ≠三级 `multi_approve`；≠任意 BPM |
| 选课互斥 / 分类限额（schema） | difficulty L1 | 已实现（COURSE 等） | — |
| 我的周历 / 课表列表 | difficulty L0 | 已实现 | 非拖拽排期引擎 |
| 忘记密码 / 邮箱或手机找回 | — | **待补** | 通识高频；现网多为验证码登录改密，缺自助找回闭环 |
| 注册手机号/学号唯一校验提示 | auth | **待补** | 多数域已有唯一约束，缺统一友好提示文案契约 |
| 敏感操作二次确认（删档/驳回/退款） | — | **待补** | 前端确认框+后端再校验；通识开题常写 |
| 数据备份/恢复说明（非功能） | README | 已实现（交付说明） | 开题写「备份」→ 论文写运维说明，不另起备份引擎 |
| Excel/CSV 导出当前列表 | 基线导出 | 已实现 | 见 difficulty L0 |
| 个人中心改手机号/邮箱（需验证码） | auth + profile | **待补** | 通识；现网改密多、改绑定少 |
| 登录失败次数锁定 / 冷却 | auth | **待补** | 防爆破浅规则；≠验证码平台 |
| 用户启用停用 + 强制下线提示 | org_users | 已实现（启停） | 「强制踢下线」会话侧 **待补** |
| 站内信已读/未读/全部已读 | sys_message | **待补** | 铃铛已有；缺已读态闭环 |
| 公告置顶 / 过期自动下架 | content | **待补** | 字段+列表过滤 |
| 工作台待办数字角标与跳转 | 基线工作台 | **待补** | 通识开题常写「待办提醒」 |
| 列表高级筛选（多条件组合） | 基线列表 | **待补** | 状态+日期+关键词；≠报表引擎 |
| 操作成功/失败统一 Toast 文案契约 | FE | **待补** | 学生可见文案一致性 |
| 附件大小/类型限制与提示 | upload | **待补** | 配置+前端提示；通识 |
| 打印当前页（浏览器打印样式） | FE | **待补** | @media print；≠报表套打引擎 |
| 帮助中心 / 操作手册页（静态） | content 或静态页 | **待补** | 开题常写「系统帮助」 |
| 用户协议 / 隐私政策勾选注册 | auth | **待补** | 勾选+链接；≠法务审 |
| 黑暗主题 / 换肤 | — | **不支持**（视觉在一键生成另轴） | 勿当业务密功能 |
| 多语言 i18n | — | **不支持** | 毕设极少刚需；中文包 |
| 组织/院系树（资料挂组织） | org | **待补** | 校园/企业题高频；浅树；≠完整 HR |
| 角色菜单权限勾选矩阵 | RBAC | **待补** | 开题常写权限管理；浅勾选；≠动态权限引擎 |
| 数据字典（枚举文案可配） | dict | **待补** | 状态/类型下拉统一维护 |
| 系统参数页（开关/文案键） | sys_config | **待补** | 开题常写系统设置；浅 KV |
| Excel 批量导入（模板+行校验） | 基线导入 | **待补** | 与导出成对；通识高频 |
| 列表批量通过/驳回/删除 | 基线列表 | **待补** | 管理端多选；各壳复用 |
| 软删除回收站（管理恢复） | 基线 | **待补** | 内容/档案类开题常写 |
| 注册密码强度规则提示 | auth | **待补** | 长度/复杂度提示；≠风控中台 |
| 首次登录强制改初始密码 | auth | **待补** | 种子账号答辩常写 |
| 图片灯箱预览（附件/封面） | FE | **待补** | 通识 UX；≠专业预览云 |
| 全局关键词搜索入口 | 基线 | **待补** | 顶栏搜档案标题；浅 |
| 系统维护中提示条（只读开关） | sys_config | **待补** | 文案条；≠运维平台 |
| 管理员重置用户密码 | org_users | **待补** | 通识高频；重置后强制改密可叠 |
| 会话超时自动退出提示 | auth | **待补** | 前端闲置计时；通识 |
| 邮箱验证激活（注册后点链/填码） | auth | **待补** | 站内信/演示码即可；≠真 SMTP 必达 |
| 账号注销/停用自助申请 | auth | **待补** | 轻申请+审；通识偶见 |
| 数据权限按组织过滤列表 | org | **待补** | 依赖组织树；浅过滤；≠完整数据权限引擎 |
| 公告/详情富文本编辑 | content | **待补** | 通识高频；浅编辑器 |
| 防重复提交（按钮锁定/幂等键） | FE + API | **待补** | 开题常写；浅 |
| 工作台常用功能快捷入口可配 | 基线工作台 | **待补** | 入口集合；≠低代码 |
| 页脚系统版本号展示 | FE | **待补** | 答辩常问；只读 |
| 「记住登录」延长会话 | auth | **待补** | Cookie/Token 时长；浅 |
| 登录设备/最近登录记录 | auth | **待补** | 列表只读；≠风控中台 |
| 省市区三级联动（地址簿） | profile / 地址 | **待补** | 通识高频；本地码表；≠真地图 |
| 身份证号校验（位权算法提示） | profile | **待补** | 格式校验；≠公安网 |
| 手机号格式统一校验契约 | auth + profile | **待补** | 文案+正则；通识 |
| 强制公告弹窗（未读不可关） | content | **待补** | 开题常写；浅 |
| 分类/字典拖拽排序 | dict / 分类 | **待补** | 管理端排序权重；浅 |
| 个人中心「我的单据」聚合入口 | 基线 | **待补** | 各壳单据列表汇总链；浅 |
| 消息按类型筛选（系统/业务） | sys_message | **待补** | Tab；已读闭环可叠 |
| 简易访问量统计（PV，工作台） | 基线工作台 | **待补** | 计数；≠大数据 UV 中台 |
| 第三方/微信登录 | — | **不支持** | 无 OAuth 主线；论文写账号密码 |
| 统一身份认证 CAS/LDAP | — | **不支持** | 无校园 IdP 对接主线 |
| 多租户 SaaS 隔离 | — | **不支持** | 单校单库毕设口径 |
| 系统名称 / Logo 可配 | sys_config | **待补** | 开题常写系统设置；浅 |
| 登录页背景/轮播可配 | sys_config | **待补** | 管理端上传；浅 |
| 密保问题找回密码 | auth | **待补** | 与邮箱找回二选一即可；浅 |
| 用户管理打标签筛选 | org_users | **待补** | 管理标签；浅 |
| 批量启用/停用账号 | org_users | **待补** | 多选操作；通识 |
| 离开页未保存提示 | FE | **待补** | beforeunload；通识 UX |
| 单号一键复制 | FE | **待补** | 通识 UX；浅 |
| 演示账号一键填登录 | FE | **待补** | 答辩演示常用；种子账号 |
| 上传图片前端压缩 | upload | **待补** | 通识；≠专业图床 |
| 接口说明 / Swagger 入口说明 | README | 已实现（交付说明） | 开题写「接口文档」→ README；不另起门户 |
| 注册邀请码（限本校） | auth | **待补** | 开题偶见；浅码表 |
| 密码定期强制更换提示 | auth | **待补** | 日期规则；通识等保题常写 |
| 操作日志导出 CSV | audit_log | **待补** | 扫词挂审计时加深 |
| 工作台待办按角色过滤 | 基线工作台 | **待补** | 与角标可叠；浅 |
| 附件病毒扫描 | — | **不支持** | 无杀毒引擎主线 |
| 电子签章平台对接（法大大等） | — | **不支持** | 法定 CA；本地签章另见 e_sign |
| 真短信/邮件网关必达 | — | **不支持** | 站内信/消息模板顶；已散见口径收口于此 |
| 首页自定义门户区块编排 | — | **不支持** | 低代码门户；固定工作台+公告顶 |
| 工作流可视化拖拽设计器 | — | **不支持** | 完整 BPM；三级审+转审顶 |
| 报表拖拽自制 BI | — | **不支持** | ECharts 工作台顶 |
| 移动端自适应专项包 | — | **不支持** | 无独立 H5/小程序主线；浏览器缩放顶 |
| 同账号多端会话列表互踢细控 | auth | **待补** | 强制下线加深；浅 |
| 敏感字段脱敏策略可配 | sys_config | **待补** | 手机号/证件；浅 |
| 列表导出字段勾选 | 基线导出 | **待补** | 列选择；通识偶见 |
| 登录页验证码一键刷新无障碍文案 | captcha | **待补** | 文案契约；浅 |
| 个人中心实名认证勾选（非公安） | profile | **待补** | 勾选+姓名证件字段；浅 |
| 站内信删除（软删） | sys_message | **待补** | 已读闭环加深 |
| 字典项启用停用 | dict | **待补** | 浅；通识 |
| 区块链存证 / 上链 | — | **不支持** | 无链主线 |
| 视频通话 / WebRTC 面试 | — | **不支持** | 无音视频 SDK 主线 |
| 物联网设备遥测接入 | — | **不支持** | OUT_OF_SCOPE 收口 |
| 国产化数据库强制（达梦等） | — | **不支持** | 主线 MySQL；拟选双显另轴 |
| 微服务拆分交付 | — | **不支持** | 单体毕设口径 |
| 容器编排 K8s 交付 | — | **不支持** | 交付说明顶 |
| 全局全站检索（ES） | — | **不支持** | 基线关键词顶 |
| 验证码行为式（滑块/点选） | captcha | **待补** | 可先图形；行为式浅可选 |
| 账号异地登录提醒 | auth | **待补** | 对照登录记录；浅 |
| 注册图形验证码失败次数提示 | captcha | **待补** | 文案契约；浅 |
| 个人资料完整度进度条 | profile | **待补** | 对齐婚恋完整度；横切化 |
| 菜单按角色动态隐藏已齐说明 | RBAC | 已实现（交付说明） | 开题写动态菜单→角色勾选顶；缺则待补矩阵 |
| 大数据实时数仓 | — | **不支持** | ECharts 工作台顶 |
| 中台业务中台交付 | — | **不支持** | 单体域壳顶 |
| 灰度发布 / 功能开关中台 | — | **不支持** | sys_config 浅 KV 顶 |
| 全链路调用追踪 APM | — | **不支持** | 审计日志顶 |
| 账号绑定学工号唯一强校验提示齐 | auth | **待补** | 与手机号唯一提示同契约 |
| 导出任务中心（异步大导出） | — | **不支持** | 同步 CSV 顶；毕设极少刚需 |
| 自定义表单设计器 | — | **不支持** | schema 字段顶；≠低代码 |
| 素材/文件库中心（统一管附件） | upload 加深菜单 | **待补** | 开题常写「文件管理」；≠网盘产品 |
| 推广邀请 + 一级佣金台账 | — | **待补** | 商城题目录级「分销」浅做；≠多级裂变 |
| 多级分销树 / 裂变佣金 | — | **不支持** | 无分销引擎主线；一级台账顶 |
| 校园跑腿 / 代买独立 App | — | **不支持** | 无跑腿骨架；驿站寄取 / 点餐骑手顶等价流程 |
| 企业微信 / 钉钉对接 | — | **不支持** | 无 IM/OA 中台主线；站内信顶 |
| 税控电子发票平台对接 | — | **不支持** | 发票抬头/演示 PDF 顶 |
| 多商家入驻平台 | — | **不支持** | 寄卖/子管岗顶；≠多店商城中台 |
| 校园一卡通 / 门禁闸机硬件 | — | **不支持** | 证件号字段 / 通行码顶 |
| 二手交易专域 | consign / SHOP 皮 | 扫词开或商城深皮 | 勿新 DOM；寄卖/旧书回收顶 |
| 在线用户列表与强制下线 | auth 会话 | **待补** | 开题常写「在线用户」；与启停行「强制踢下线」同缺口 |
| 每日签到涨积分 | points 窄扫 | **扫词开** | 材料写签到才挂；≠活动口令 `checkin` |
| 定时任务只读台（关单/过期券等） | 基线调度 | **待补** | 展示调度项说明；≠ XXL-JOB 中台 |
| 广告位 Banner 多槽 | content | **待补** | 开题写广告位/运营位时；单轮播可先顶 |
| 自习室 / 图书馆座位预约 | MEETING 皮或 X-BORROW-RESERVE | 已实现 | 见 domains 组 H；勿新 DOM |
| 心理咨询预约 | slot_reserve 深皮 | 已实现（换皮） | 勿新 DOM；挂号/美业/会议皮顶 |
| 校友录 / 通讯录 | CRM 或 archive 深皮 | 已实现（换皮） | 勿新 DOM |
| 体质健康测试登记 | GRADE / SURVEY / EVENT 深皮 | 已实现（换皮） | 勿新 DOM |
| 代码生成器进学生包 | — | **不支持** | 工厂侧能力，不进 ZIP |
| 对象存储 OSS / 云盘对接 | — | **不支持** | 本地 upload 顶 |
| 系统 CPU/内存监控台 | — | **不支持** | 工作台顶；≠ APM |
| 人事工资套件 | — | **不支持** | 组织树+考勤顶；≠ HR 中台 |
| 车牌识别道闸 | — | **不支持** | 硬件；通行码/车证顶 |
| 砍价 / 助力砍价 | — | **待补** | 商城目录级常见；浅：底价+邀请人数；≠拼团 `group_buy`；≠多级裂变 |
| 活动抽奖 / 大转盘 | — | **待补** | 开题常写；浅概率池；≠盲盒 `blind_box`（付费抽盒） |
| OCR / 证件自动识别 | — | **不支持** | 无视觉主线；手填+上传顶 |
| App 推送 / 厂商推送通道 | — | **不支持** | 站内信 / 消息模板顶 |
| 成就勋章 / 徽章 | — | **待补** | 社区/学习题偶见目录级；浅：条件达成发徽章；≠游戏引擎 |
| 众筹发起与兑付 | — | **不支持** | 无众筹清算主线；拼团/预售顶 |
| 拍卖竞价引擎 | — | **不支持** | 无限时加价拍卖状态机；限时购顶 |
| 电子病历 / 诊疗闭环 | — | **不支持** | 业务过重；挂号预约皮顶；对齐 difficulty 拒收口径 |
| 现金红包 / 微信红包发放通道 | — | **不支持** | 无资金红包主线；积分赠分 / 优惠券顶 |
| 学信网等学历认证对接 | — | **不支持** | 无外部学历核验主线；成绩/证明本包顶 |
| 安防视频监控 / NVR 对接 | — | **不支持** | 无视频平台主线；报修/事件附件顶 |
| 生产报工 / MES 车间执行 | — | **不支持** | 无车间工序报工主线；物资出入库 `stock_io` 顶 |
| 跨境电商 / 保税仓清关 | — | **不支持** | 无跨境清关主线；普通商城订单顶 |
| CMDB 配置管理库 | — | **不支持** | IT 终端 lookup 顶；≠资产配置库产品 |
| 收银外设硬件（POS / 小票机 / 强制扫码枪 / 读卡 / 高拍仪） | — | **不支持** | 浏览器打印与手输码顶；≠驱动级外设 |
| 开放平台 OpenAPI / 对外 Webhook | — | **不支持** | 无开发者平台主线；本包 API 仅自用 |

---

## 1. 全域密功能枚举（68）

分组对齐工厂级联（`DOMAIN_GROUPS`）。每域顿号 = 开题常见模块。状态默认跟壳走：**壳内主路径已实现**；表内点名「扫词开/待补/不支持」优先。  
§0 已列横切扫词项各组可碰，**分域行不必再抄**。挂载细则见 [`capabilities.md`](./capabilities.md)；域默认能力组合见 [`domains.md`](./domains.md)。

### 1.1 借用 / 占用

组口径：档案 + 单据 + 名额/库存；图书/设备带到期催办与续借。借阅+座位真交叉可降 GENERIC（见 domains 组 H）。

| 域 | 开题密功能枚举 | 状态要点 |
|----|----------------|----------|
| `DOM-LIBRARY` 图书 | 检索借还、额度、超期罚款催还、统计、**续借**、**丢失→赔偿**；**图书预约 / 荐购**（材料命中）；分类/关键词检索 | 续借/丢失域默认；预约 E-11、荐购 E-13 **扫词开** |
| `DOM-EQUIP` 设备借用 | 申请审批领取、**归还验图**、归还超期损坏、排队、**续借**；档案「维修中」；**用途说明必填** | 续借/用途域默认；验图/维修中为域皮 |
| `DOM-ASSET` 物资领用 | 领用审批、出入库、库存预警、入出库统计；**盘点 / 报废**（材料命中）；分类台账 | stock_io 域默认；盘点/报废 E-08 扫词开；≠多仓 WMS、≠采购壳 |
| `DOM-PARCEL` 快递驿站 | 到件、取件码核销、滞留催领、**货架**；异常件；**寄件 / 取件码二维码**（材料命中）；手机号本人件 | parcel_shelf 域默认；**催领 deadline 域默认**；寄件/code_qr 扫词开；≠跑腿商城 |
| `DOM-BED` 床位 | 选房/调宿/退宿审批、床位占用、浏览**状态色块**；同宿舍约束文案 | bed_occupy 域默认 |

#### 本组待补

| 功能 | 建议落域 | 说明 |
|------|----------|------|
| （本组 §1.1 待补已清） | — | — |

#### 本组本轮已齐（从待补迁出）

| 功能 | 落点 | 挂载 |
|------|------|------|
| 报废审批流深化（独立报废状态机） | scrap_request + stockScrapOpts.approveFlow | **扫词开** stock_scrap 时；pending→approved/rejected 后才扣库存；gate 验 scrap-requests |
| 物资申购转领用一键动作 | ticket.allowProcureRef / procureToStockIn | **域默认** ASSET 申购单号确认；PROCURE 一键入库（补 stock_io gate） |
| 续借次数上限 | loan_renew → `maxRenew` | **域默认** 随续借 |
| 即将到期提前提醒（站内信，应还日前 N 天） | deadline → `dueSoonDays`（默认 3） | **域默认** 借还壳 |
| 超期达 N 次限制再借（资格冻结） | ticket → `maxOverdueTimes` | **开题扫** |
| 领用用途必填 | ticket.requireRemark | **域默认** ASSET/EQUIP |
| 滞留超 N 日催领（站内） | deadline（PARCEL SLA） | **域默认** PARCEL |
| 低库存自动站内信提醒总管 | schema `stockWarnNotify` | **开题扫** |
| 热门借阅榜文案（复用 recommend 计数热度） | labels.recommendSectionTitle | **域默认** LIBRARY/EQUIP |
| 领用常用用途字典（下拉可手填） | ticket.remarkOptions | **域默认** ASSET/EQUIP |
| 物资安全库存下限可配 | schema.stockWarnBelow | **域默认** ASSET |
| 代取件登记（代取人姓名手机） | ticket.allowProxyPickup | **域默认** PARCEL |
| 到件站内信通知本人 | ticket.arrivalNotify | **域默认** PARCEL |
| 包裹异常件原因 + 破损理赔说明 | ticket.allowExceptionClose | **域默认** PARCEL |
| 驿站营业时间外取件提示 | labels.offHoursPickupHint | **域默认** PARCEL |
| 驿站代收协议勾选 | ticket.requireNoticeAck | **开题扫** |
| 床位性别/年级约束校验 | ticket.bedConstraint | **域默认** BED |
| 床位入住须知勾选 | ticket.requireNoticeAck | **域默认** BED |
| 调宿原床位释放时机说明 | labels.bedReleaseHint | **域默认** BED |
| 图书馆藏地点 / 分馆校区 | archive holdingLoc/campusZone | **域默认** LIBRARY |
| 图书漂流/赠阅标记 | archive.stage 选项 | **域默认** LIBRARY |
| 寒暑假闭馆停借规则提示 | labels.closedLoanHint | **域默认** LIBRARY |
| 图书索书号 / ISBN 规范校验 | borrowThicken.isbnValidate | **开题扫** |
| 设备保养到期日字段 | archive.maintainDue | **开题扫** |
| 设备押金登记 | ticket.allowDeposit | **开题扫** |
| 设备借用须培训合格勾选 | ticket.requireTrainingAck | **域默认** EQUIP |
| 设备外借单位（校外）字段 | archive.loanOrg | **域默认** EQUIP |
| 物资批次号 / 有效期 / 库位货架 / 供应商联系人 | archive 浅列 | **域默认** ASSET |
| 库位/货架号（驿站格口） | archive.shelfNo | **域默认** ASSET/PARCEL/EQUIP |
| 分馆/校区字段（浅） | archive.campusZone | **域默认** LIBRARY/EQUIP/ASSET |
| 图书分类树 / 中图法简码字段 | archive.clcCode | **域默认** LIBRARY |
| 损坏赔偿标准表（按类型定额） | schema.damageCompStandards | **域默认** LIBRARY/EQUIP |
| 设备校检合格证附件槽 | archive.calibCertUrl | **域默认** EQUIP |
| 退宿行李清点勾选清单 | material_check 变体 | **开题扫**（行李清点/退宿清点） |
| 预约到书站内信通知 | book_hold → hold_ready MessageStore | **扫词开** book_hold（原已闭环） |
| 设备随借配件勾选清单 | material_check 变体 | **开题扫**（随借配件） |
| 排队到号站内信 | waitlist 晋升 MessageStore | **扫词开** waitlist（原已闭环） |
| 新书/新物资上架通报提示 | labels.shelfAnnounceHint | **域默认** LIBRARY/ASSET |
| 驿站货架格口占用状态 | archive.slotStatus | **域默认** PARCEL |
| 读者证号/一卡通号字段 | profile.cardNo 文案 | **域默认** LIBRARY |
| 随书附件（光盘）勾选借出 | material_check 变体 | **开题扫**（随书光盘/附件） |
| 设备标签二维码打印说明 | labels.equipQrPrintHint | **域默认** EQUIP |
| 领用双人复核签字栏 | ticket.allowDualReview | **开题扫**（双人复核） |
| 床位住宿费/预定金演示登记 | ticket.allowDeposit | **开题扫**（住宿费/预定金） |
| 设备故障转报修单号 | archive.repairTicketNo | **域默认** EQUIP |
| 超期催还计入信誉分（提示+开关） | ticket.creditOnOverdue + labels | **开题扫**（信誉分） |
| 图书预约取消次数限制 | ticket.maxCancelHolds | **开题扫** |
| 设备归还逾期转赔付提示开关 | ticket.overdueAutoCompensate | **开题扫** |
| 退宿水电清算备注 | ticket.allowUtilityNote | **开题扫** |
| 图书荐购预算余额提示 | labels.suggestBudgetHint | **域默认** LIBRARY |
| 设备校准证书到期停借 | archive.calibDue + blockIfCalibExpired | **开题扫**（校准证书） |
| 包裹逾期弃件标记 | archive.stage 弃件 + 文案 | **开题扫**（弃件） |
| 物资领用课题号 | ticket.allowProjectNo | **开题扫**（课题号） |
| 驿站寄件运费登记 | ticket.allowShipFee | **开题扫** |
| 设备借用保险声明勾选 | ticket.requireInsuranceAck | **开题扫** |
| 图书读者信用分规则提示 | labels.creditRuleHint | **域默认** LIBRARY |
| 设备借用合同模板说明 | labels.contractTemplateHint | **域默认** EQUIP |
| 床位入住登记表打印提示 | labels.bedPrintHint | **域默认** BED |
| 图书闭架索书单打印提示 | labels.closedStackPrintHint | **域默认** LIBRARY |
| 设备保养工单联动说明 | labels.maintainWorkOrderHint + repairTicketNo | **域默认** EQUIP |
| 楼栋床位分区色块字段 | archive.buildingZone + bedPlanHint | **域默认** BED |
| 床位互换意向文案指引 | labels.bedSwapHint | **域默认** BED |
| 报废叠二级审 | ticket.twoLevelApprove（挂 stock_scrap 时） | **扫词开** stock_scrap 时叠 |
| 多册合借一单（册数） | ticket.allowQty + qtyLabel=册数 | **域默认** LIBRARY（检索页填数量） |
| 逾期罚款减免 | ticket.allowFineWaive → fine_status=waived | **开题扫**（罚款减免） |
| 续借须无他人预约 | ticket.renewBlockIfHeld | **开题扫** |
| 调宿双方确认 | ticket.requirePeerConfirm + peer_ack → `peer_tickets` 菜单 + Mapper 收件箱 | **开题扫**（双方确认/对向同意） |
| 床位互换双方确认链路 | 同上 + peer_tickets 菜单 | **开题扫**（与双方确认同开） |
| 图书征订目录导入提示 | labels.catalogImportHint（复用档案 CSV） | **域默认** LIBRARY |
| 荐购进度查询（审核说明） | BookSuggest 用户列表 handleNote | **扫词开** book_suggest（原已闭环） |
| 物资领用额度（分类上限） | ticket.categoryLimit | **开题扫**（领用额度/按月限额） |
| 盘点锁定禁出入库 | stockCountOpts.countLock → StockIoStore | **开题扫** |
| 盘点差异原因必填 | stockCountOpts.requireDiffReason | **开题扫** |
| 物资盘点盲盘 | stockCountOpts.blindCount | **开题扫** |
| 驿站弃件双人确认 | ticket.requireAbandonDual | **开题扫**（弃件双人） |

不支持：RFID/物联网盘点、跨馆互借、柜机硬件对接、多仓调拨、图书联合编目 Z39.50。

### 1.2 跟进

组口径：档案 + 跟进/申请单；多为自建档自跟或学工台账。横切留言/审计/消息模板可扫。

| 域 | 开题密功能枚举 | 状态要点 |
|----|----------------|----------|
| `DOM-CRM` 客户跟进 | 客户档案、线索阶段、跟进记录、办结、统计；联系人电话备注 | 轻量跟进单；**不支持**公海池/外呼中心 |
| `DOM-EVENT` 事件上报 | 上报审核、排查处置、晨午检、**档案监测打卡**、事件等级、附件 | archive_log 域默认；食安≠点餐 |
| `DOM-ATTEND` 考勤请假 | 请假销假、起止算天数、占用冲突、汇总；假种文案 | occupy_span+冲突；**不支持**人脸/GPS 打卡硬件 |
| `DOM-FUND` 资助奖学金 | 申请材料审、名额、**公示登记**、**发放台账**；困难等级字段 | 公示/发放随域表；不扩申请状态机 |
| `DOM-RECRUIT` 招聘投递 | 岗位、投递、初筛、面试时间地点、必传附件、简历附件 | 接单≠购物车 |
| `DOM-GRADE` 成绩 | 成绩登记、课内名次、CSV、改分留痕、分布及格率、成绩更正申请 | grade_score 域默认 |
| `DOM-INTERN` 实习周报 | 岗绑定、周报填、导师审、**本地签章**；周次 | e_sign 域默认；≠ CA |
| `DOM-LISTING` 房源带看 | 挂牌上下架、带看跟进、**成交登记台账**；价格面积字段 | 成交只记事实；不做交易支付 |

#### 本组待补

| 功能 | 建议落域 | 说明 |
|------|----------|------|
| （本组 §1.2 待补已清） | — | — |

#### 本组本轮已齐（从待补迁出）

| 功能 | 落点 | 挂载 |
|------|------|------|
| 下次跟进日到期站内信提醒 | followThicken.followRemindDays → next_follow_at | **域默认** CRM/LISTING |
| 客户/房源标签多选筛选 | archive.tags | **域默认** CRM/LISTING |
| 跟进记录时间轴 | labels.followTimelineHint | **域默认** CRM |
| 年假/调休余额扣减 | balance_ledger（ATTEND 域默认）+ leave_days 扣减 | **域默认** ATTEND |
| 请假销假后余额回补 | balanceLedger.creditOnReturn | **域默认** ATTEND |
| 面试结果登记 | ticket.allowInterviewResult | **域默认** RECRUIT |
| 录用/淘汰批量操作 | ticket.allowBatchHire → POST `/api/tickets/batch-hire` + 管理端勾选 | **域默认** RECRUIT |
| 周报截止未交提醒 | ticket.weekReportRemind → `maybeNotifyWeekReports` + MessageStore.existsRef（每周一封） | **域默认** INTERN |
| 实习鉴定表字段套 | ticket.requireAppraisal | **域默认** INTERN |
| 成绩单打印预览页 | labels.gradePrintHint | **域默认** GRADE |
| 带看评价（星级） | ticket.allowRating | **域默认** LISTING |
| 事件结案报告附件必传 | ticket.requireCloseAttach | **域默认** EVENT |
| 长期未跟进标「搁置」 | archive.stage 含搁置 | **域默认** CRM |
| 跟进方式统计饼图 | contact_channel → 工作台 channelSeries 饼图 | **域默认** CRM |
| 家访/谈话记录模板字段套 | ticket.homeVisitTemplate | **开题扫** |
| 请假附件按假种必传 | ticket.attachByLeaveType | **域默认** ATTEND |
| 销假确认（返岗日期） | ticket.requireReturnDate | **域默认** ATTEND |
| 资助答辩/评议结果登记 | ticket.allowDefenseResult | **域默认** FUND |
| 岗位收藏 / 投递进度时间轴 | favorites 扫词 + progressTimelineHint | **开题扫** 收藏；时间轴域默认 |
| 成绩排名班级/专业切换 | labels.rankSwitchHint | **域默认** GRADE |
| 补考报名入口 | ticket.allowMakeupApply | **域默认** GRADE |
| 实习周报优秀标记 + 汇总导出 | ticket.allowExcellentMark | **开题扫** |
| 房源收藏与对比 | favorites + 导出/复制清单（listingCompareHint） | **开题扫** |
| 成交漏斗简图 | rent_stage/stage → 工作台 listingFunnelSeries | **域默认** LISTING |
| 客户/线索查重提示 | ticket.phoneDupCheck | **域默认** CRM |
| 考勤月汇总表导出 | labels.monthExportHint | **域默认** ATTEND |
| 招聘岗位有效期自动下架 | archive.expireOn → 列表入口 expirePastExpireOn | **域默认** RECRUIT |
| 成绩导入行级错误回显 | labels.importRowErrorHint | **域默认** GRADE |
| 事件等级影响处理时限 | ticket.levelAffectsDeadline + deadline | **开题扫** |
| 资助名额余量实时展示 | labels.quotaRemainHint | **域默认** FUND |
| 周报退回修改次数限制 | ticket.maxReviseTimes | **域默认** INTERN |
| 房源价格变更留痕 | archive.priceHistory | **域默认** LISTING |
| 线索来源统计饼图 | lead_source → 工作台 leadSourceSeries | **开题扫** |
| 客户阶段漏斗简图 | archive.stage → 工作台 stageSeries | **域默认** CRM |
| 面试评价表（维度打分） | rating_dims 叠 | **开题扫** |
| 奖学金公示异议登记窗口 | ticket.allowObjectionWindow | **开题扫** |
| 实习单位对实习生评价 | ticket.allowCompanyEval | **域默认** INTERN |
| 晨午检未打卡名单导出 | labels.checkExportHint | **域默认** EVENT |
| 请假审批时限超时提醒 | deadline 扫词叠 | **开题扫** |
| 带看预约时段冲突提示 | time_conflict 扫词 | **开题扫** |
| 招聘笔试/机试成绩登记 | ticket.allowWrittenScore | **开题扫** |
| 绩点换算说明页 | labels.gpaPageHint | **域默认** GRADE |
| 事件上报手填位置描述 | archive.locationDesc | **域默认** EVENT |
| 资助银行卡号脱敏展示 | ticket.maskBankAccount | **域默认** FUND |
| 客户跟进下次行动待办勾选 | ticket.allowNextAction | **开题扫** |
| 家访照片附件槽 | requireAttach 扫词 | **开题扫** |
| 请假跨天拆段展示 | labels.leaveSplitHint | **域默认** ATTEND |
| 房源VR外链字段 | archive.vrUrl | **域默认** LISTING |
| 招聘用人部门筛选 | archive.hireDept | **开题扫** |
| 成绩异议申请时限 | ticket.objectionDays | **开题扫** |
| 实习周报字数下限 | ticket.minRemarkWords | **域默认** INTERN |
| 分配负责人 | archive.ownerUsername | **开题扫** |
| 事件上报保密标记 | ticket.allowConfidential | **开题扫** |
| 请假代理人登记 | ticket.allowLeaveProxy | **开题扫** |
| 带看反馈必填项套 | ticket.requireFeedbackSet | **域默认** LISTING |
| 招聘简历解析字段手填套 | ticket.resumeFieldSet | **开题扫** |
| 成绩加权平均说明 | labels.weightedAvgHint | **域默认** GRADE |
| 实习考勤与周报联动提示 | labels.attendLinkHint | **域默认** INTERN |
| 客户成交金额登记 | ticket.allowDealAmount | **域默认** CRM |
| 事件上报分拨科室 | ticket.allowAssignDept | **开题扫** |
| 请假 overlapping 冲突提示 | labels.leaveOverlapHint | **域默认** ATTEND |
| 招聘录用通知站内信模板 | message_template 扫词叠 | **开题扫** |
| 成绩正态分布简易图 | labels.distChartHint | **域默认** GRADE |
| 未跟进 N 天列表 | ticket.staleFollowDays | **开题扫** |
| 资助发放批次号 | ticket.allowDisburseBatch | **域默认** FUND |
| 房源意向客户计数 | labels.intentCountHint | **域默认** LISTING |
| 招聘岗位收藏夹分享 | favorites + 导出清单/复制清单（favShareHint） | **开题扫** |
| 成绩导出含学号脱敏选项 | labels.stuNoMaskExportHint | **域默认** GRADE |
| 事件上报一键通知值班表 | ticket.notifyDutyOnReport | **开题扫** |
| 请假假期余额导入 | labels.leaveBalanceImportHint | **开题扫** |
| 带看录音外链字段 | ticket.allowRecordUrl | **开题扫** |
| 招聘面试间预约叠会议室 | labels.interviewRoomHint | **开题扫** |
| 成绩排名隐私开关 | schema.rankPrivacy | **开题扫** |
| 客户标签颜色 | labels.tagColorHint | **开题扫** |
| 资助形式枚举 | archive.fundForm | **域默认** FUND |
| 实习单位评价匿名开关 | schema.companyEvalAnonymous | **开题扫** |
| 招聘入职材料清单 | material_check 扫词 | **开题扫** |
| 成绩补考后覆盖规则说明 | labels.makeupOverlayHint | **域默认** GRADE |
| 事件值班排班叠 staff_roster | staff_roster 扫词 | **开题扫** |
| 请假销假二维码确认 | code_qr 扫词 | **开题扫** |
| 招聘背调备注字段 | ticket.allowBgCheckNote | **开题扫** |
| 客户合同回款计划 | archive.paymentPlan | **开题扫** |
| 房源意向跟进下次提醒 | followRemindDays（LISTING） | **域默认** LISTING |

不支持：公海抢客、外呼中心、真视频面试 SDK、银企发奖、教务正方对接；客户跟进语音转写（无 ASR）；成绩 analytics 看板独立产品。

### 1.3 报修 / 工单

组口径：**处理时限/催办（deadline）域默认**。催办=站内时限提醒，非短信。三域同壳换皮。

| 域 | 开题密功能枚举 | 状态要点 |
|----|----------------|----------|
| `DOM-DORM` 宿舍报修 | 分类图片、派单接单跟进、**催办**、完结、评价；楼栋房间预填；**排班 / 留言**（材料命中） | deadline 域默认；排班/留言扫词开 |
| `DOM-PROPERTY` 物业报修 | 同上；小区/房屋皮；**场馆保洁任务**（材料命中） | venue_clean 窄扫；缴费/车位分域；保洁≠酒店 PMS |
| `DOM-IT` IT 报修 | 同上 + 区域/终端 lookup；故障描述 | 终端 lookup≠ CMDB |

#### 本组待补

| 功能 | 建议落域 | 说明 |
|------|----------|------|
| 用户端「催办」按钮（未超时也可点，记一笔） | 三域 | ≠短信外呼 |
| 报修单满意度（单据星级，对齐 `allowRating`） | 三域 | 开题常写评价时 |
| 常用故障原因字典 + 结单必选 | 三域 | 主数据字典；≠智能诊断 |
| 紧急程度（一般/紧急）影响列表排序 | 三域 | 字段+排序；≠智能派单 |
| 维修前后图片对比区（结单可传） | 三域 | 附件槽；通识开题常写 |
| 转派记录留痕（谁转给谁） | 三域 | 流水；≠工单引擎 |
| 备件/耗材出库记一笔（关联工单） | PROPERTY / IT | 浅台账；≠完整进销存 ASSET |
| 重复报修提示（同房间未结同类） | DORM / PROPERTY | 提交校验提示 |
| 报修进度时间轴（用户可见） | 三域 | 状态变更流水展示 |
| 预约上门时段（用户期望时间） | 三域 | 字段；≠排班强约束可先弱 |
| 维修超时自动升紧急 | 三域 | 规则；依赖 deadline |
| 知识库式「常见问题」只读页 | IT / PROPERTY | content 深皮或静态；≠ RAG |
| 报修满意度差评必填原因 | 三域 | 评价扩展 |
| 同楼栋未结工单热力简表 | DORM | 管理端统计；≠大屏 |
| 资产编号扫码录入（手输码） | IT | 文本码；≠硬件扫码枪强制 |
| 维修员工作量统计（接单/完结数） | 三域 | 工作台；通识高频 |
| 用户催办后冷却（防刷催） | 三域 | 规则；浅 |
| 派单按区域/楼栋过滤维修员 | DORM / PROPERTY | 名单过滤；≠智能派单 |
| SLA：响应时限与完结时限分列 | 三域 | 两字段；deadline 加深 |
| 结单必填处理过程摘要 | 三域 | 办结字段 |
| 用户撤单（未派单前可撤） | 三域 | 状态规则；通识高频 |
| 维修员拒单原因登记 | 三域 | 回池+原因；浅 |
| 工单编号规则说明（只读） | 三域 | 文案；流水号已有可钉 |
| 夜间/节假日报修加急标记 | 三域 | 字段；浅规则 |
| 评价后锁定单据不可再催 | 三域 | 规则 |
| 同类知识条目关联推荐（手工挂） | IT | lookup 链接；≠ RAG |
| 维修报价用户确认 | 三域 | 金额+确认态；通识偶见 |
| 重复工单合并（主从关联） | 三域 | 浅关联；≠工单中台 |
| 服务态度/效率分项评价 | 三域 | allowRating 多维浅 |
| 备件不足时结单警告 | PROPERTY / IT | 对照耗材台账；浅 |
| 报修语音备注（上传音频文件） | 三域 | 附件类型放宽；浅 |
| 用户端进度订阅开关 | 三域 | 站内信偏好；浅 |
| 报修单打印工单页 | 三域 | 浏览器打印；通识 |
| 维修员当日路线备注（手填） | 三域 | 字段；≠地图调度 |
| 用户端历史报修复用上次地址 | 三域 | UX；浅 |
| 结单回访任务（站内待办） | 三域 | 浅待办；通识偶见 |
| 故障现象词云式高频标签（计数） | 三域 | 字典计数；≠ NLP |
| 报修单评价邀请延迟（办结后 N 小时） | 三域 | 规则；浅 |
| 维修员技能标签过滤派单 | 三域 | 标签；≠智能派单 |
| 用户端撤销催办 | 三域 | 状态；浅 |
| 物业公共区域报修（无房号） | PROPERTY | 地址类型；浅 |
| IT 远程协助备注（会议号外链） | IT | URL 字段；浅 |
| 报修分类图标/色标 | 三域 | 字典扩展；浅 |
| 结单知识沉淀勾选（写入常见问题） | IT / PROPERTY | 手工沉淀；≠自动知识库 |
| 多人协作工单（主责+协助） | 三域 | 字段；浅 |
| 用户端满意度追评（一次） | 三域 | 评价扩展；浅 |
| 报修材料费用户确认支付（系统内） | 三域 | 金额+demoPay 思路；浅 |
| 值班表冲突与报修派单提示 | 三域 | 排班叠；浅 |
| 用户端常见故障自助排查页 | IT / PROPERTY | 静态步骤；≠智能诊断 |
| 工单挂起/恢复 | 三域 | 状态；通识偶见 |
| 宿舍公共卫生间报修（公区） | DORM | 对齐物业公区；浅 |
| 报修单导出含图片链接列 | 三域 | CSV；浅 |
| 维修超时升级主管站内信 | 三域 | 规则；浅 |
| 用户端草稿报修 | 三域 | draft；通识偶见 |
| 备件序列号登记 | PROPERTY / IT | 字段；浅 |
| 报修服务水平协议说明页 | 三域 | 只读 SLA 文案；浅 |
| 维修员端今日工单看板 | 三域 | 列表过滤；通识 |
| 用户端取消已派单（须理由） | 三域 | 规则；通识偶见 |
| 物业费催缴 | — | **不支持**：缴费另域；勿塞报修壳 |
| 报修评价标签（态度好/准时） | 三域 | 字典多选；浅 |
| 维修员拒单次数统计 | 三域 | 计数；浅 |
| 用户端历史地址簿 | 三域 | 地址复用；浅 |

不支持：智能派单算法引擎、短信/电话外呼网关、物联网报修采集、物业费收费系统（缴费另域）。

### 1.4 报名 / 申请

组口径：**候补** ACTIVITY/COURSE 域默认、TOUR/LOST 扫词开；**单据星级评价**（`allowRating`，≠ `order_review`）ACTIVITY/LOST/TOUR 域默认；COURSE 无单据评价（评教走 DOM-EVAL）。报名+投票 → ACTIVITY 扫词挂 `vote`（C-11）。组内**不接**真支付商户 / 闸机 / 地图 / OTA / 短信。

| 域 | 开题密功能枚举 | 状态要点 |
|----|----------------|----------|
| `DOM-ACTIVITY` 活动报名 | 发布名额截止、报名审取消、**时段冲突**、**候补**、**口令签到**与爽约、**单据评价**、周历日程；票务/证书/献血/研学深皮；名单导出 | 主路径+候补+签到+评价已实现 |
| `DOM-LOST` 失物招领 | 启事、认领审、**凭证核验**、**路人线索**、领养/捐赠/行李深皮、单据评价；地点/时间字段 | claim_proof+lost_clue 域默认；候补扫词开 |
| `DOM-COURSE` 选课 | 选退改、名额截止、**冲突**、**互斥**、**分类限额**、**候补**、课表、学分字段；教师教室 | ≠ DOM-EVAL |
| `DOM-TOUR` 旅行社线路 | 线路档案（出团/下架）、余位报名审、截止、取消回补、期望出行日、**单据评价**；行程亮点 | 候补扫词；**无**商城订单支付主路径；≠酒店/活动/拼车 |

#### 本组待补

| 功能 | 建议落域 | 说明 |
|------|----------|------|
| 学分上限（已选合计 ≤ 学期上限） | COURSE | 纯校验；≠评教 |
| 先修课提示（同码/同系列提示，非强制引擎） | COURSE | 文案+弱校验即可 |
| 集体报名 / 代填同行人（一单多人占额） | ACTIVITY / TOUR | ≠拼团商城 |
| 报名须知「已阅读」勾选后才可提交 | 四域 | schema 开关 |
| 年级/身份资格限制 | ACTIVITY / COURSE | 对照资料字段 |
| 黑名单禁止报名（管理维护名单） | ACTIVITY / TOUR | 轻名单表；≠风控引擎 |
| 认领成功自动下架启事 | LOST | stock→0+状态 |
| 失物招领到期自动下架提醒 | LOST | 日期字段+任务或提交时校验 |
| 活动办结「报名证明」PDF（固定模板） | ACTIVITY | ≠ CA 证书平台 |
| 出团名单打印/导出（含联系方式列） | TOUR | CSV 已有可加深列配置 |
| 活动取消规则（开始前 N 小时可退） | ACTIVITY | schema+校验 |
| 活动海报/封面多图 | ACTIVITY | gallery 扫词即可先顶；表内钉口径 |
| 签到成功率 / 缺勤名单导出 | ACTIVITY / CHECKIN | 统计+CSV |
| 活动问卷联动（结束后填满意度卷） | ACTIVITY | 扫词挂 survey；表内钉联动口径 |
| 选课结果公示页（已满/开放） | COURSE | 档案 stage 展示加深 |
| 退选次数上限 | COURSE | 规则；通识教务题常写 |
| 培养方案学分结构提示（选修/必修标签） | COURSE | 分类标签；≠完整培养方案引擎 |
| 失物「悬赏」备注字段（非支付） | LOST | 文案字段；≠真打赏 |
| 认领双方评价 | LOST | allowRating 双向或单次 |
| 线路行程日明细（D1/D2 文本） | TOUR | 富文本或多行；≠地图轨迹 |
| 出团前资料清单勾选（护照复印等） | TOUR | material_check 变体 |
| 保险声明勾选（非保单系统） | TOUR | 须知勾选变体 |
| 报名审核批量通过/驳回 | 四域 | 管理端多选；通识高频 |
| 候补自动递补占额 | ACTIVITY / COURSE | 取消后队列顶上；规则 |
| 签到二维码页（口令可视化） | ACTIVITY / CHECKIN | code_qr 可叠；表内钉 |
| 课表冲突可视化高亮 | COURSE | UI；规则已有可加深 |
| 认领冷却期（发布后 N 小时可认） | LOST | 防秒认；浅规则 |
| 活动名额紧张提示（余量阈值） | ACTIVITY | 文案；浅 |
| 线路成团最低人数提示 | TOUR | 字段+列表提示；≠强制关团引擎 |
| 活动分场次/分组报名 | ACTIVITY | 子档案或场次字段；通识 |
| 抽签录取（随机抽满额） | ACTIVITY | 浅随机；≠公平抽签平台 |
| 选课志愿序（第一/第二志愿） | COURSE | 字段+录取规则浅；≠完整志愿引擎 |
| 报名费演示登记（非商户支付） | ACTIVITY / TOUR | 金额备注；系统内或线下勾选 |
| 失物面交地点/时间约定字段 | LOST | 认领单扩展 |
| 活动志愿者岗位报名分流 | ACTIVITY | 分类名额；浅 |
| 出团天气/须知附件包 | TOUR | 附件；浅 |
| 报名邀请码/口令报名 | ACTIVITY | 字符串码；通识 |
| 安全责任书勾选（研学/献血皮） | ACTIVITY / TOUR | 须知变体 |
| 失物分类（卡证/数码/衣物）字典 | LOST | 分类加深 |
| 选课抽签录取（名额紧张时） | COURSE | 浅随机；对齐活动抽签 |
| 活动座位分区（区域名额） | ACTIVITY | 浅分区；≠影院选座主路径 |
| 团员保险名单导出列 | TOUR | CSV 列配置 |
| 认领面交双方确认勾选 | LOST | 轻双确认；浅 |
| 活动签到补签（管理端） | ACTIVITY / CHECKIN | 管理补录；通识 |
| 报名成功站内信 | 四域 | 消息模板；通识高频 |
| 选课学分预警（接近上限） | COURSE | 提示；浅 |
| 失物启事加急置顶（付积分演示） | LOST | 字段+积分可选；浅 |
| 线路余位紧张候补开关 | TOUR | waitlist 钉口径 |
| 活动相册（办结后上传） | ACTIVITY | gallery；浅 |
| 活动候补转正站内信 | ACTIVITY / COURSE | 递补齐后加深 |
| 选课教材信息字段 | COURSE | 档案扩展；浅 |
| 失物认领所需证件类型勾选 | LOST | material_check 变体 |
| 线路报名年龄限制 | TOUR | 对照资料；浅 |
| 活动学分认定回写提示（非自动） | ACTIVITY / CREDIT | 文案交叉；浅 |
| 团体票价说明（文案） | ACTIVITY / TOUR | 只读；浅 |
| 活动签到地点字段 | ACTIVITY | 字段；≠ GPS 打卡 |
| 选课开课学院筛选 | COURSE | 组织筛选；浅 |
| 失物启事浏览计数 | LOST | 计数；浅 |
| 出团领队联系方式字段 | TOUR | 档案；通识 |
| 报名审核驳回理由必填 | 四域 | 通识高频 |
| 活动签到迟到分钟数登记 | ACTIVITY | 字段；浅 |
| 选课教师调课通知站内信 | COURSE | 消息；浅 |
| 失物启事评论区开关 | LOST | item_comment 叠；浅 |
| 线路报名紧急联系人 | TOUR | 字段；通识 |
| 活动容量超售保护（乐观锁说明） | ACTIVITY | 文案+校验；浅 |
| 活动赞助商展示位 | ACTIVITY | 档案字段；浅 |
| 选课先修课硬拦截开关 | COURSE | 弱提示升级可选；浅 |
| 失物认领需要押金演示 | LOST | 金额；浅 |
| 线路单房差说明 | TOUR | 文案；浅 |
| 活动电子票夹（我的票） | ACTIVITY | 列表+码；通识 |
| 选课培养方案外链 | COURSE | URL；≠方案引擎 |
| 失物招领诚信分 | LOST | 浅分；通识偶见 |
| 出团集合点字段 | TOUR | 字段；通识 |
| 活动门票转让（站内改签人） | ACTIVITY | 浅改名额占用；偶见 |
| 选课抽签结果公示 | COURSE | 公示页；浅 |
| 失物启事过期自动关闭 | LOST | 规则；对齐到期下架 |
| 线路签证材料清单 | TOUR | material_check；出国皮 |

不支持：真支付售票、闸机、地图导航、OTA 渠道、短信验证码通道（登录验证码除外）。

### 1.5 审批 / 填报

组口径：事项/类型档案 + 申请单；常见挂材料清单 / 额度台账 / 占用时段 / 多级审（见 capabilities）。证明/合同类勿冒充法定 CA。

| 域 | 开题密功能枚举 | 状态要点 |
|----|----------------|----------|
| `DOM-LABSAFE` 实验室准入 | 准入培训、许可到期、材料；开题写考试可叠 **exam** | material_check；先考后申按扫词 |
| `DOM-SEAL` 用印 | 事项、申请、审批、用印登记 | balance_ledger |
| `DOM-FLEET` 用车 | 派车、里程、归还、时段冲突 | occupy_span |
| `DOM-CERT` 证明 | 类型、申请、审、开具领取 | material_check |
| `DOM-PROMO` 宣传品 | 方案审、时段占用 | occupy_span |
| `DOM-FITOUT` 装修报备 | 申报图纸、验收巡查、占位 | occupy_span |
| `DOM-ACAD` 学籍异动 | 转专业/缓考等申请审 | occupy_span |
| `DOM-TRIP` 出差加班 | 申请审、可与报销交叉 | occupy_span |
| `DOM-EXPENSE` 经费报销 | 报销单发票、审、付款台账 | balance+多级审；**不支持**银企直连 |
| `DOM-CREDIT` 第二课堂 | 学分认定申报审汇总 | balance_ledger |
| `DOM-LABOR` 劳动时长 | 时长认定申报审 | balance_ledger |
| `DOM-EVAL` 评教 | 多维评分+评语+可选匿名 | rating_dims；≠问卷壳 SURVEY |
| `DOM-MORAL` 德育综测 | 加减分申报审公示 | balance_ledger |
| `DOM-AWARD` 成果登记 | 获奖登记认定展示 | balance_ledger |
| `DOM-PROCURE` 采购申购 | 申购比价审、入库供应商 | ≠纯商城；浅申购 |
| `DOM-CLUB` 社团注册年审 | 材料审；可叠活动报名 | material_check |
| `DOM-PROJ` 大创项目 | 申报立项中期结题、多级审 | material+multi_approve |
| `DOM-ETHIC` 伦理审查 | 申报会议批件跟踪 | material+multi_approve |
| `DOM-PARTY` 党员发展 | 阶段材料审转正 | material_check |
| `DOM-CONTRACT` 合同 | 起草审批签署归档；e_sign 扫词 | **不支持**法大大/法定 CA |
| `DOM-VISITOR` 访客 | 预约审、通行码 | pass_code；code_qr 扫词 |
| `DOM-CARPASS` 车辆通行证 | 临牌备案、有效期、通行码 | pass_code；**不支持**道闸抬杆 |
| `DOM-CHECKIN` 查寝归寝 | 登记审、口令签到、缺勤 | checkin；**不支持**人脸签到 |

#### 本组待补

| 功能 | 建议落域 | 说明 |
|------|----------|------|
| 证明/用印「套打 PDF」下载（固定模板） | CERT / SEAL | 本地模板；≠电子签章平台 |
| 合同/许可到期站内信提醒 | CONTRACT / LABSAFE | 按日期扫；≠短信 |
| 报销发票张数/金额校验规则 | EXPENSE | 提交校验；≠税控 |
| 报销单明细多行（差旅交通住宿分行） | EXPENSE | 子表或 JSON 行；通识高频 |
| 访客通行码到期自动失效展示 | VISITOR / CARPASS | 码字符串上加有效期展示 |
| 用车里程回填与油耗备注 | FLEET | 办结字段 |
| 评教未评名单导出催评 | EVAL | CSV；≠强制弹窗阻断登录（可另议） |
| 党员发展阶段时间轴展示 | PARTY | 只读时间线；≠智慧党建平台 |
| 大创中期/结题材料节点提醒 | PROJ | 站内信；按日期 |
| 采购比价至少 N 家供应商校验 | PROCURE | 提交规则；浅 |
| 查寝缺勤连续 N 次预警名单 | CHECKIN | 列表筛选；≠人脸 |
| 用印份数/份号回填 | SEAL | 办结字段 |
| 证明领取方式（自取/邮寄地址） | CERT | 申请字段 |
| 宣传品尺寸/悬挂位置字段 | PROMO | 档案字段加深 |
| 装修噪音时段约束提示 | FITOUT | 文案+弱校验 |
| 学籍异动影响课表提示（只读说明） | ACAD | 公告式提示；≠自动改课表 |
| 出差行程多段（出发/途经/返回） | TRIP | 多行明细 |
| 加班调休核定小时数 | TRIP | 办结字段 |
| 第二课堂学分上限校验 | CREDIT | 对齐选课学分上限思路 |
| 劳动时长证明附件 | LABOR | requireAttach |
| 评教开放窗口（起止日期） | EVAL | 与问卷截止同思路 |
| 综测加减分证据材料清单 | MORAL | material_check |
| 获奖证书编号查重 | AWARD | 录入校验 |
| 伦理批件编号与有效期 | ETHIC | 档案字段 |
| 合同正文附件版本号 | CONTRACT | 附件+版本备注 |
| 访客黑名单（禁止预约） | VISITOR | 轻名单；对齐活动黑名单 |
| 车辆通行证与车位预约互斥提示 | CARPASS | 文案；≠道闸 |
| 准入培训学时累计 | LABSAFE | 字段累计；考试另挂 exam |
| 申请人撤回未审单据 | 本组通用 | 状态规则；通识高频 |
| 审批常用意见短语 | 本组通用 | 下拉短语；浅 |
| 审批抄送知会（只读通知） | 本组通用 | 站内信；≠会签引擎 |
| 用车驾驶员/随车人登记 | FLEET | 办结或申请字段 |
| 查寝楼栋长代登记 | CHECKIN | 岗权限；通识宿舍题 |
| 报销票据影像必传张数 | EXPENSE | requireAttach 条件 |
| 合同签署方多方勾选 | CONTRACT | 字段；≠法大大 |
| 社团年审材料一键复制上年 | CLUB | 浅复制；通识 |
| 审批时限超时催办站内信 | 本组通用 | 对齐 deadline；通识 |
| 证明开具流水号规则 | CERT | 编号生成；浅 |
| 用印监印人确认勾选 | SEAL | 办结字段 |
| 大创项目成员变更申请 | PROJ | 轻单；通识 |
| 评教一人一课防重复提交 | EVAL | 规则；高频 |
| 访客邀约码（被访人生成） | VISITOR | 字符串码；浅 |
| 采购到货入库一键转台账 | PROCURE | 浅联动 ASSET 思路；表内钉 |
| 伦理会议日期与决议摘要 | ETHIC | 字段；浅 |
| 加签/转审（仅一跳，非任意 BPM） | 本组通用 | 浅转审；完整流程图引擎仍不支持 |
| 审批意见最少字数 | 本组通用 | 提交校验；通识 |
| 证明真伪查询码（公开页） | CERT | 字符串码查询；浅 |
| 用车加油票/过路费附件 | FLEET | requireAttach |
| 查寝照片必传 | CHECKIN | requireAttach；通识宿舍题 |
| 合同续签提醒（到期前） | CONTRACT | 对齐到期提醒加深 |
| 思想汇报/心得附件节点 | PARTY | material_check 节点 |
| 评教结果对学生不可见开关 | EVAL | schema；通识 |
| 访客到访登记（现场补录） | VISITOR | 管理端补单；浅 |
| 劳动时长地点字段 | LABOR | 申请字段 |
| 审批委托（请假期间代审） | 本组通用 | 浅委托；≠完整授权中心 |
| 用印文件份数与装订说明 | SEAL | 申请字段加深 |
| 证明开具领取二维码 | CERT | code_qr 叠 |
| 大创中期检查表套打 | PROJ | PDF 模板；浅 |
| 访客预约时段余量 | VISITOR | slot 思路；浅 |
| 车辆通行证年检到期提醒 | CARPASS | 日期提醒；浅 |
| 采购预算余额校验 | PROCURE | 额度台账；浅 |
| 综测公示期异议入口 | MORAL | 轻单；对齐资助异议 |
| 审批退回修改后再提 | 本组通用 | 状态回退；通识高频 |
| 用车回场油量登记 | FLEET | 办结字段 |
| 证明邮寄快递单号回填 | CERT | 字段；浅 |
| 大创经费使用登记浅表 | PROJ | 台账；≠银企 |
| 评教课程维度权重可配 | EVAL | schema；浅 |
| 访客随行人数字段 | VISITOR | 申请字段 |
| 查寝异常类型字典 | CHECKIN | 字典；通识 |
| 合同审批意见对签署方可见开关 | CONTRACT | schema；浅 |
| 审批限时自动通过（可选危险开关） | 本组通用 | schema；通识偶见；默认关 |
| 实验室准入考试成绩门槛 | LABSAFE | 叠 exam；规则 |
| 宣传品投放反馈照片 | PROMO | 办结附件 |
| 装修验收不合格整改单 | FITOUT | 轻单；浅 |
| 学籍异动生效日期 | ACAD | 字段；通识 |
| 党员发展阶段材料清單模板 | PARTY | material_check 模板 |
| 审批附件版本覆盖留旧 | 本组通用 | 附件历史；浅 |
| 用印登记拍摄回传 | SEAL | 办结附件 |
| 证明开具份数上限 | CERT | 规则；浅 |
| 大创结题查重说明（外链） | PROJ | URL；≠查重引擎 |
| 评教督导听课记录 | EVAL | 管理端浅表；偶见 |
| 访客通行证打印 | VISITOR | 浏览器打印；浅 |
| 伦理审查意见书模板下载 | ETHIC | PDF；浅 |
| 社团成员名册导入 | CLUB | 导入；通识 |
| 审批抄送人可追加评论 | 本组通用 | 浅；知会加深 |
| 用车违章责任人登记 | FLEET | 字段；浅 |
| 证明加急件标记 | CERT | 字段；浅 |
| 采购验收不合格退货登记 | PROCURE | 浅单；浅 |
| 查寝抽查任务生成 | CHECKIN | 名单抽样浅；≠算法 |
| 合同金额大写展示 | CONTRACT | UI；通识 |
| 审批统计（人均耗时）简表 | 本组通用 | 工作台；浅 |
| 用印台账导出 | SEAL | CSV；通识 |
| 证明真伪公开查询页已齐钉口径 | CERT | 查伪码齐后加深公开页 |
| 大创项目变更日志 | PROJ | 流水；浅 |
| 评教结果院系汇总导出 | EVAL | CSV；通识 |
| 访客来访目的字典 | VISITOR | 字典；浅 |
| 审批意见附件（审时上传） | 本组通用 | 附件；浅 |
| 用车驾驶员资质附件 | FLEET | requireAttach |
| 证明领取核销码 | CERT | code_qr；浅 |
| 评教强制顺序（先评后查分） | EVAL / GRADE | 文案交叉；偶见 |
| 查寝楼长日报汇总 | CHECKIN | 导出；通识 |

不支持：银企直连、法定 CA、道闸/人脸门禁硬件、完整 BPM 任意流程图引擎（三级审已有 cap）、党建学习强国对接。

### 1.6 交易

组口径：`order_lines` 购物车/订单（影院为选座下单）。系统内支付=渠道+密码/余额；**不接**微信支付宝商户清算。横切券/积分/拼团等见 §0。

| 域 | 开题密功能枚举 | 状态要点 |
|----|----------------|----------|
| `DOM-SHOP` 商城 | 浏览分类、收藏、购物车、下单地址、系统内支付、订单全态、售后、评价、库存预警、留言；多店/规格/限时购/定制/配送时段/审方限购/拼团/盲盒/寄卖/称重/旧书回收/数字商品/积分（材料命中） | 收藏/评价/留言域默认；其余扫词或窄扫；**不支持**完整 SKU 矩阵、原生小程序 |
| `DOM-FOOD` 点餐 | 堂食自取外卖、档口接单、评价退单、支付；**骑手岗**、配送时段/明细定制（材料命中） | 骑手扫词开；**不支持**美团式实时调度/独立骑手 App |
| `DOM-CINEMA` 影院选座 | 排片、座位图占座、下单出票退票、系统内支付 | seat_select 域默认；占座≠场地预约；无购物车主路径 |

#### 本组待补

| 功能 | 建议落域 | 说明 |
|------|----------|------|
| 售后原因分类 + 简单占比图 | SHOP / FOOD | 工作台级；≠大数据 |
| 收货地址「默认地址」一键 | SHOP / FOOD | 资料/地址簿字段 |
| 购物车全选 / 失效商品清理 | SHOP / FOOD | 通识 UX |
| 订单备注（用户下单留言给商家） | SHOP / FOOD | 已有字段则钉文案；缺则待补列 |
| 影院退票截止规则（开场前 N 分钟） | CINEMA | schema+校验 |
| 连座推荐（相邻空位提示，非算法锁座） | CINEMA | UI 提示；≠高并发锁 |
| 订单完成自动邀评站内信 | 三域 | 挂 order_review 时 |
| 销售日报简表（按日订单数/金额） | SHOP / FOOD | 工作台或导出；≠BI |
| 缺货登记 / 到货通知（站内信） | SHOP | 轻表；≠采购 ERP |
| 商品上下架定时（到点改状态） | SHOP / FOOD | 日期字段+任务或登录扫；浅 |
| 满减叠加说明页（只读规则文案） | SHOP | 已有 spend_discount 可钉帮助 |
| 发票抬头登记（订单备注级，非税控） | SHOP | 字段；≠电子发票平台 |
| 堂食桌号 / 取餐号展示 | FOOD | 下单字段+小票文案 |
| 口味备注（少辣/多冰）快捷选项 | FOOD | line_custom 扫词可顶；表内钉 |
| 骑手接单超时自动回池 | FOOD | 状态规则；扫词挂骑手时 |
| 场次售罄自动关售 | CINEMA | stage 同步 stock |
| 取票码展示（订单号派生） | CINEMA | 字符串码；code_qr 可叠 |
| 观影须知勾选 | CINEMA | 须知勾选变体 |
| 退货物流单号回填 | SHOP | 售后字段 |
| 会员日折扣说明（文案+member_tier） | SHOP | 扫词挂会员时 |
| 订单超时未付自动取消 | SHOP / FOOD / CINEMA | 规则；通识高频 |
| 下单锁库存 / 取消回补 | SHOP / FOOD | 与 stock 对齐钉口径 |
| 售后仅退款 / 退货退款分流 | SHOP | 类型字段；浅 |
| 优惠券核销码（订单展示） | SHOP | 字符串码；扫词挂券时 |
| 档口营业时段外禁下单 | FOOD | 对照营业时间字段 |
| 影院卖品加购（简易加价项） | CINEMA | 订单附加行；浅；≠独立卖品域 |
| 评价晒图（图文评价） | SHOP / FOOD | order_review 附件槽 |
| 确认收货超时自动完成 | SHOP | 规则；通识高频 |
| 退款/售后原因必填 | SHOP / FOOD | 提交校验 |
| 优惠券领取中心页 | SHOP | 扫词挂券时；列表领 |
| 拼团进度条（已参团/待成团） | SHOP | group_buy 齐后加深 |
| 物流轨迹演示节点（手填） | SHOP | 多行状态；≠快递100 |
| 商品好评率展示 | SHOP / FOOD | 聚合计数；浅 |
| 购物车改规格（有则换无则提示） | SHOP | UX；浅 |
| 影院选座倒计时释放 | CINEMA | 占座超时；通识 |
| 优惠券过期站内信提醒 | SHOP | 扫词挂券时 |
| 订单分享口令（只读查单） | SHOP / FOOD | 字符串码；浅 |
| 餐具/打包选项 | FOOD | 下单字段；通识 |
| 满赠说明（买赠文案） | SHOP | 只读规则；浅 |
| 发票申请状态（申请中/已开） | SHOP | 字段机；≠税控 |
| 影院情侣座/残疾人座标记 | CINEMA | 座位属性；浅 |
| 售后进度时间轴 | SHOP | 对齐报修时间轴；浅 |
| 积分明细流水页 | SHOP | points 齐后加深 |
| 收货后仅 N 天可申请售后 | SHOP | 规则；通识高频 |
| 购物车凑单提示（差 N 元包邮） | SHOP | 文案；浅 |
| 档口评分排序 | FOOD | 聚合；浅 |
| 订单发票下载占位（PDF 演示） | SHOP | 固定模板；≠税控 |
| 影院排片日历周视图 | CINEMA | UI；通识 |
| 退款原路退回说明（系统内余额） | SHOP / FOOD | 文案口径；浅 |
| 商品浏览足迹 | SHOP | 对齐内容浏览历史；浅 |
| 商品规格库存分记（浅二维） | SHOP | 有限规格；≠完整 SKU 矩阵（完整仍不支持） |
| 外卖配送费阶梯说明 | FOOD | 文案+规则；浅 |
| 订单部分发货登记 | SHOP | 状态加深；通识偶见 |
| 影院会员价说明 | CINEMA | member_tier 叠；浅 |
| 购物车失效自动勾掉 | SHOP / FOOD | UX；浅 |
| 售后换货流程（浅状态） | SHOP | 类型扩展；浅 |
| 限时购倒计时展示 | SHOP | flash_price 齐后加深 |
| 拼团失败自动退款说明 | SHOP | group_buy 齐后加深 |
| 点餐必选品类校验（如必选主食） | FOOD | 规则；通识偶见 |
| 影院退票手续费登记 | CINEMA | 金额；浅 |
| 订单收货码核销 | SHOP / FOOD | code_qr 思路；浅 |
| 商品评论追评 | SHOP / FOOD | order_review 加深 |
| 包装费选项 | FOOD / SHOP | 下单字段；浅 |
| 影院卖品库存扣减 | CINEMA | 加购齐后加深 |
| 订单改地址（未发货） | SHOP | 规则；通识 |
| 优惠券互斥说明页 | SHOP | 文案；浅 |
| 盲盒中赏记录页 | SHOP | blind_box 齐后加深 |
| 商品详情页问答（留言式） | SHOP | guestbook 深皮；浅 |
| 外卖预计送达时间文案 | FOOD | 字段；≠调度 |
| 影院特效厅标记（IMAX 文案） | CINEMA | 场次属性；浅 |
| 订单小票浏览器打印 | SHOP / FOOD / CINEMA | print；通识 |
| 积分商城兑换运费说明 | SHOP | points 叠；浅 |
| 商品预售定金尾款说明 | SHOP | 文案+状态；浅 |
| 点餐拼单（同桌合并） | FOOD | 浅合并；≠美团拼单 |
| 影院积分兑票说明 | CINEMA | points 叠；浅 |
| 售后仅换货不退款选项 | SHOP | 类型；浅 |
| 商品到货订阅（再次） | SHOP | 缺货登记加深 |
| 堂食排队取餐号叫号大屏 | — | **不支持**：桌号/取餐号顶；无硬件大屏 |
| 影院连场套票说明 | CINEMA | 文案；浅 |
| 订单延保登记 | SHOP | 字段；浅 |

不支持：完整 SKU 多规格库存矩阵、微信/支付宝商户清算、原生小程序包、实时运单调度、直播带货。

### 1.7 预约

组口径：`slot_reserve` 时段占坑；酒店/租车可叠订单。改约/办结随壳。INSTRUMENT 为借+约单域（级联归本组）。

| 域 | 开题密功能枚举 | 状态要点 |
|----|----------------|----------|
| `DOM-HOSPITAL` 挂号 | 号源预约取消、签到候诊文案 | **不支持**医保结算 |
| `DOM-PARKING` 车位 | 预约、取消审；缴费演示 | **不支持**道闸硬件 |
| `DOM-MEETING` 会议/场地 | 冲突预约、取消、超时；**设备清单**、**保洁任务**（材料命中） | room_equipment / venue_clean 扫词或窄扫 |
| `DOM-SALON` 美业 | 技师时段、取消支付评价；**排班 / 约拍 / 课时包**、保洁（材料命中） | 扫词开；裸「清洁工」不挂保洁 |
| `DOM-HOTEL` 客房 | 房型日历预订、定金支付、评价；**寄养**、**房态/前台/客房清洁**（材料命中） | PMS 伞扫；民宿/寄养不挂房态三件套；**不支持**OTA/门锁 |
| `DOM-CARRENT` 租车 | 车型预订取还；**押金/验损分账**（材料命中） | rental_bond 扫词开 |
| `DOM-INSTRUMENT` 仪器机时 | 借用+机时预约、超时、续借 | instrument_slot 域默认 |

#### 本组待补

| 功能 | 建议落域 | 说明 |
|------|----------|------|
| 就诊/到店「报到签到」口令（复用 checkin 思路） | HOSPITAL / SALON | ≠人脸 |
| 号源分时段余量展示（上午/下午） | HOSPITAL | 文案或 slot 分组；≠叫号大屏 |
| 车位超时占用加收演示费 | PARKING | 规则+登记；≠地感线圈 |
| 会议结束后必填纪要附件 | MEETING | requireAttach 变体 |
| 会议签到表导出 | MEETING | CSV |
| 预约开始前站内信提醒 | 本组通用 | 可先靠消息模板扫词；专用调度待补 |
| 取消预约规则（开始前 N 小时可免费取消） | 本组通用 | schema+校验 |
| 技师服务项目时长自动占坑 | SALON | 档案时长字段；已有则可钉 |
| 客房续住延期（改离店日） | HOTEL | 改约变体 |
| 机时超时自动计费登记 | INSTRUMENT | 规则+台账；≠实验室门禁 |
| 医生/诊室排班展示（只读） | HOSPITAL | staff_roster 扫词可顶 |
| 就诊人多档案（家属代约） | HOSPITAL | 资料扩展；通识高频 |
| 车位套餐（包月次卡计数） | PARKING | 浅计数；≠道闸计费硬件 |
| 会议冲突检测说明文案（已约人可见） | MEETING | 提示增强 |
| 会议录屏链接字段（外链） | MEETING | URL 字段；≠会议云录制 |
| 美业会员卡余次（对齐课时包） | SALON | lesson_pack 扫词可顶 |
| 作品集展示（技师档案多图） | SALON | gallery |
| 客房延迟退房加收说明+登记 | HOTEL | 费用备注；≠门锁 |
| 入住人身份证号字段（脱敏展示） | HOTEL / 前台 | 字段+脱敏；≠公安网核验 |
| 租车违章预留押（备注+金额） | CARRENT | rental_bond 扩展说明 |
| 仪器培训合格才可约（材料勾选） | INSTRUMENT | material_check 或 LABSAFE 叠 |
| 预约爽约次数限制再约 | 本组通用 | 对齐活动爽约；通识 |
| 候诊/到店队列序号展示 | HOSPITAL / SALON | 序号字段；≠叫号硬件 |
| 会议室按周重复预约（简单） | MEETING | 生成多条；浅；≠日历引擎 |
| 酒店定金与尾款分列登记 | HOTEL | 金额字段；系统内支付 |
| 租车取还车验车单勾选 | CARRENT | material_check；通识 |
| 车位预约与访客车通行证提示 | PARKING / CARPASS | 文案交叉；浅 |
| 机时预约冲突可视化 | INSTRUMENT | 对齐会议冲突提示 |
| 改约次数上限 | 本组通用 | 规则；通识 |
| 号源候补队列 | HOSPITAL | 对齐活动候补；浅 |
| 会议室预约需审批开关 | MEETING | 状态机浅挂审 |
| 酒店连住优惠说明（文案） | HOTEL | 只读规则；浅 |
| 美业改约手续费登记 | SALON | 金额备注；浅 |
| 租车里程套餐超支加收登记 | CARRENT | 规则+登记 |
| 仪器预约须填实验目的 | INSTRUMENT | 必填字段；通识 |
| 挂号科室介绍只读页 | HOSPITAL | content/档案扩展 |
| 停车时长计费演示（进离场时间） | PARKING | 规则+金额；≠地感 |
| 会议茶水/设备服务勾选 | MEETING | 附加服务字段；浅 |
| 酒店早餐券张数登记 | HOTEL | 字段；浅 |
| 美业储值卡余额 | SALON | 浅余额；对齐钱包思路 |
| 租车取还点外链导航 | CARRENT | URL；≠自研地图 |
| 号源停诊通知站内信 | HOSPITAL | 消息；浅 |
| 场地预约黑名单 | MEETING | 对齐活动黑名单 |
| 预约成功短信式站内信 | 本组通用 | 消息模板；通识 |
| 挂号退号规则（开诊前 N 分钟） | HOSPITAL | schema；通识 |
| 会议室门禁密码字段（手发） | MEETING | 字符串；≠门禁硬件 |
| 酒店入住须知勾选 | HOTEL | 须知变体 |
| 美业到店迟到宽限分钟 | SALON | 规则；浅 |
| 租车保险套餐勾选（文案价） | CARRENT | 选项；≠保司对接 |
| 仪器耗材领用关联登记 | INSTRUMENT | 浅台账；浅 |
| 预约签到迟到标记 | 本组通用 | 字段；通识 |
| 挂号初诊/复诊选项 | HOSPITAL | 字段；通识 |
| 车位预约取消罚则说明 | PARKING | 文案；浅 |
| 会议录制设备借用勾选 | MEETING | room_equipment 叠 |
| 酒店加床登记 | HOTEL | 费用备注；浅 |
| 美业项目禁忌备注 | SALON | 档案字段；浅 |
| 租车驾驶员驾照有效期 | CARRENT | 字段；浅 |
| 预约资源维护时段禁约 | 本组通用 | 日期窗口；通识 |
| 挂号科室排队预估文案 | HOSPITAL | 只读文案；≠叫号 |
| 会议室视频会议链接字段 | MEETING | URL；浅 |
| 酒店钟点房时段类型 | HOTEL | 档案类型；浅 |
| 美业卡项过期提醒 | SALON | 站内信；浅 |
| 仪器预约须导师同意 | INSTRUMENT | 轻审；通识实验室题 |
| 预约候补转正站内信 | 本组通用 | 对齐活动候补；浅 |
| 挂号禁止黄牛：同证件限号 | HOSPITAL | 规则；浅 |
| 车位共享时段拼单说明 | PARKING | 文案；浅 |
| 会议签到二维码 | MEETING | code_qr；通识 |
| 酒店钟点房超时转全日说明 | HOTEL | 规则文案；浅 |
| 美业技师请假挡班 | SALON | roster 叠；浅 |
| 租车违章回传附件 | CARRENT | 附件；浅 |
| 预约资源容量日历着色 | 本组通用 | UI；通识 |
| 挂号复诊优先号说明 | HOSPITAL | 文案；浅 |
| 会议室最低预约时长 | MEETING | 规则；浅 |
| 酒店入住人同住人数 | HOTEL | 字段；通识 |
| 美业到店扫码签到 | SALON | checkin 叠；浅 |
| 仪器机时费结算导出 | INSTRUMENT | CSV；浅 |
| 预约资源管理员备注（对用户不可见） | 本组通用 | 字段；浅 |
| 挂号科室停诊日历 | HOSPITAL | 日期；浅 |
| 车位预约 overlapping 检测说明 | PARKING | 文案；浅 |
| 会议召开中状态 | MEETING | stage；浅 |
| 酒店退房查房清单 | HOTEL | material_check；通识 |
| 美业会员到店次数统计 | SALON | 计数；浅 |
| 预约黑名单申诉入口 | 本组通用 | 轻单；浅 |
| 挂号检验检查预约分槽 | HOSPITAL | 类型字段；浅；≠HIS |
| 会议室开门密码短信 | — | **不支持**：真短信；站内信顶 |
| 酒店入住登记公安上传 | — | **不支持**：无公安网 |
| 租车 ETC 通行费回传 | CARRENT | 金额登记；浅 |

不支持：医保、道闸、OTA 渠道、智能门锁、高并发锁座引擎、HIS 对接。

### 1.8 内容 / 媒资 / 社区

组口径：archive 浏览为主；论坛跟帖走 ticket。留言默认（论坛除外）。条下评论/投稿/点赞等扫词见 §0。

| 域 | 开题密功能枚举 | 状态要点 |
|----|----------------|----------|
| `DOM-MEDIA` 影音 | 分类播放、收藏、上下架、留言；条下评论/投稿/点赞/私信（材料命中） | **不支持** CDN/转码/弹幕/会员真支付 |
| `DOM-MUSIC` 曲库 | 点播、收藏夹（歌单=收藏）、留言；评论/上传/点赞/私信（材料命中） | 上传须点名；**不支持**版权结算/直播 |
| `DOM-FORUM` 论坛 | 发帖回帖审删；点赞/举报/禁言/私信/猜你喜欢/收藏（材料命中） | 跟帖≠guestbook；**不支持**实时聊天室 SDK |
| `DOM-BLOG` 博客 | 专栏、收藏、留言；评论/投稿/点赞/举报/禁言/私信（材料命中） | **不支持** SEO/CDN/多作者工作流引擎 |
| `DOM-DOCLIB` 文库 | 资料上传分类、权限、下载台账 | ≠借阅；勿冒充 RAG |

#### 本组待补

| 功能 | 建议落域 | 说明 |
|------|----------|------|
| 精华帖 / 置顶（管理标记+列表优先） | FORUM | 字段+排序；≠推荐引擎 |
| 帖子搜索（标题关键词） | FORUM / BLOG | 基线检索加深 |
| 下载次数展示与个人下载记录 | DOCLIB | 台账已有可加深展示 |
| 资料预览（图片/PDF 新窗口，非转码） | DOCLIB | 浏览器打开；≠永中预览云 |
| 播放进度记住（本地/按用户一条） | MEDIA / MUSIC | 毕设级；≠多端云同步 |
| 专栏/分类订阅（收藏分类） | BLOG / MEDIA | 可复用 favorites 变体 |
| 热门排行（按浏览/下载计数） | 内容组通用 | 计数+排序；≠协同过滤 |
| 草稿箱（发帖/发文先存后发） | FORUM / BLOG | 状态 draft；通识高频 |
| @提醒站内信（跟帖提到某人） | FORUM | 解析 @ + 消息；浅 |
| 版块公告（分类级须知） | FORUM | 分类扩展字段 |
| 专栏订阅更新站内信 | BLOG | 新文通知；浅 |
| 文章定时发布 | BLOG / MEDIA | 日期字段 |
| 片单/歌单分享码（只读链接口令） | MEDIA / MUSIC | 字符串码 |
| 文库积分下载（扣点后下） | DOCLIB | 须 points/wallet；扫词叠 |
| 敏感词拦截提示（本地词表） | FORUM / BLOG | 浅词表；≠云审核 |
| 举报处理结果通知举报人 | FORUM | 消息模板 |
| 二级回复（楼中楼，一层） | FORUM / BLOG | 父评论 id；浅；≠无限嵌套 |
| 个人浏览历史 | MEDIA / MUSIC / BLOG | 最近 N 条；通识 |
| 帖子/文章阅读数展示 | 内容组通用 | 计数；已有可钉 |
| 禁言到期自动解除 | FORUM | 日期字段；扫词挂禁言时 |
| 文库下载权限按角色 | DOCLIB | 角色勾选；浅 |
| 投稿审过自动上架通知 | MEDIA / BLOG | 站内信；userPublish 时 |
| 评论点赞计数 | FORUM / BLOG | 浅计数；通识 |
| 内容举报原因字典 | FORUM / BLOG | 字典；扫词挂举报时 |
| 转载/原创声明勾选 | BLOG | 发布字段；浅 |
| 文库章节目录（锚点列表） | DOCLIB | 多行目录；≠全文检索引擎 |
| 影音选集/分集列表 | MEDIA | 子项列表；浅 |
| 歌单公开/私密开关 | MUSIC | 收藏夹可见性；浅 |
| 帖子移动版块 | FORUM | 管理操作；浅 |
| 作者主页（TA 的文章/帖子） | BLOG / FORUM | 用户维度列表；通识 |
| 文库资料版本历史（备注级） | DOCLIB | 版本号+说明；浅 |
| 精华帖奖励积分登记 | FORUM | 须 points；扫词叠 |
| 评论举报 | FORUM / BLOG | 举报扫词齐后加深到评论 |
| 影音海报墙分类浏览 | MEDIA | 列表皮；浅 |
| 曲库按歌手/专辑筛选 | MUSIC | 筛选字段；通识 |
| 下载审核（文库敏感类） | DOCLIB | 浅审；通识偶见 |
| 帖子锁定（禁止再回） | FORUM | 管理标记；通识 |
| 博客归档按年月 | BLOG | 筛选；通识 |
| 媒资下架原因登记 | MEDIA / MUSIC | 字段；浅 |
| 文库热门标签云（计数） | DOCLIB | 标签计数；≠推荐 |
| 评论折叠（楼中楼过长） | FORUM / BLOG | UI；浅 |
| 收藏夹分组命名 | MEDIA / MUSIC | favorites 加深 |
| 帖子精华/置顶操作日志 | FORUM | 审计叠；浅 |
| 博客系列文（上一篇下一篇） | BLOG | 链表字段；浅 |
| 文库预览页水印（姓名） | DOCLIB | 浅水印；通识偶见 |
| 媒资播放次数排行 | MEDIA / MUSIC | 计数榜；浅 |
| 论坛每日发帖上限 | FORUM | 规则；防刷 |
| 评论仅粉丝可见（互关） | BLOG / FORUM | 浅规则；婚恋/社区偶见 |
| 发帖需审后可见开关 | FORUM | schema；通识 |
| 博客评论邮件式站内信通知 | BLOG | 消息；浅 |
| 文库下载次数个人限额 | DOCLIB | 规则；浅 |
| 影音选集完播标记 | MEDIA | 进度加深；浅 |
| 曲库歌词文本字段 | MUSIC | 字段；浅 |
| 论坛用户等级积分规则页 | FORUM | 文案+points 叠；浅 |
| 博客定时撤回（到点下架） | BLOG | 日期；浅 |
| 文库章节试读前 N 页说明 | DOCLIB | 文案；≠DRM |
| 影音片单协作（多人编辑） | MEDIA | **不支持**：协作编辑；个人片单顶 |
| 曲库音质切换（文案假切换） | MUSIC | UI；浅 |
| 帖子草稿自动保存 | FORUM / BLOG | 草稿加深；浅 |
| 论坛版主任命 | FORUM | 岗/角色；通识 |
| 博客文章密码访问 | BLOG | 口令；浅 |
| 文库纠错反馈单 | DOCLIB | 轻单；浅 |
| 影音分集更新站内信 | MEDIA | 消息；浅 |
| 曲库翻唱标记 | MUSIC | 字段；浅 |
| 论坛举报表处理时效 | FORUM | deadline 思路；浅 |
| 博客专栏订阅数展示 | BLOG | 计数；浅 |
| 文库付费下载（系统内点券） | DOCLIB | points/wallet；浅 |
| 影音会员真支付 | — | **不支持**：组末已有；系统内会员顶 |
| 曲库版权结算 | — | **不支持**：组末已有；表内钉 |
| 论坛每日签到涨积分 | FORUM | points 窄扫叠；浅 |
| 博客友情链接栏 | BLOG | 字段列表；浅 |
| 文库侵权投诉单 | DOCLIB | 轻单；浅 |
| 影音弹幕 | — | **不支持**：组末已有；表内钉 |

不支持：转码 CDN、弹幕、协同过滤推荐、RAG 知识库问答冒充文库、短视频算法推荐。

### 1.9 互动 / 匹配

组口径：双选/考试/问卷/投票/拼车/时间银行/婚恋等；多数无商城订单主路径。

| 域 | 开题密功能枚举 | 状态要点 |
|----|----------------|----------|
| `DOM-DATING` 婚恋 | 资料筛选、配对、私信、审；**举报**（材料命中） | dm 默认；**不支持**协同过滤 |
| `DOM-MUTUAL-TUTOR` 导师双选 | 志愿、确认人接受/婉拒、调剂、名额 | mutual_select |
| `DOM-MUTUAL-TOPIC` 选题双选 | 同上（选题档案） | 同上 |
| `DOM-MUTUAL-TEAM` 组队 | 同上（组队资料） | 同上 |
| `DOM-CARPOOL` 拼车 | 发行程、同行意向、确认、取消 | **不支持**真地图；「预约」词 soft |
| `DOM-TIMEBANK` 时间银行 | 服务事项、时长账户流水、核销扣减 | ≠劳动认定≠活动报名 |
| `DOM-EXAM` 在线考试 | 题库组卷交卷阅卷；刷题/解析/限时/次数/排行/错题本按需 | **不支持**人脸监考 |
| `DOM-SURVEY` 问卷 | 配置填写回收统计 | ≠评教≠考试 |
| `DOM-VOTE` 投票 | 候选、限票、计票公示 | 纯投票；报名+投票见 ACTIVITY |

#### 本组待补

| 功能 | 建议落域 | 说明 |
|------|----------|------|
| 意向人数满自动关闭行程 | CARPOOL | 状态规则 |
| 拼车出发前提醒站内信 | CARPOOL | 消息模板 |
| 双选志愿调剂记录留痕列表 | MUTUAL-* | 管理端可查 |
| 志愿提交后允许在截止前修改 | MUTUAL-* | 规则开关 |
| 问卷开放/截止自动上下架 | SURVEY | 按日期 |
| 问卷匿名填写开关 | SURVEY | schema；通识高频 |
| 投票结果导出 | VOTE | CSV |
| 考试及格证书页（固定模板 PDF） | EXAM | ≠ CA；可与活动证明同思路 |
| 练习模式不计分 / 不计次数 | EXAM | 开题常写刷题 |
| 时间银行时长排行榜 | TIMEBANK | 只读榜；≠复杂经济系统 |
| 婚恋资料完整度提示 | DATING | 资料页提示条 |
| 心动列表（收藏对方资料） | DATING | favorites 已可挂；表内钉 |
| 互选截止倒计时展示 | MUTUAL-* | UI；规则已有可加深 |
| 导师学生名额占用进度条 | MUTUAL-TUTOR | 配额可视化 |
| 组队技能标签筛选 | MUTUAL-TEAM | 标签字段 |
| 拼车费用分摊备注（非支付） | CARPOOL | 文案字段 |
| 拼车评价 | CARPOOL | allowRating |
| 时间银行服务评价 | TIMEBANK | allowRating |
| 兑换记录对账导出 | TIMEBANK | CSV |
| 考试防切屏提示（文案+失焦计数） | EXAM | 浅；≠锁屏监考 SDK |
| 成绩公布后可看解析开关 | EXAM | schema |
| 问卷逻辑跳题（简单若选A则跳） | SURVEY | 浅规则；≠全功能问卷引擎 |
| 投票防刷：同 IP 提示（仅提示） | VOTE | 浅；≠风控中台 |
| 十佳结果海报页（静态生成） | VOTE | 结果页美化；≠设计工具 |
| 试卷题目/选项乱序 | EXAM | 开题常写防抄；浅 |
| 交卷前答题进度条 | EXAM / SURVEY | UI；通识 |
| 问卷每人限填一次 | SURVEY | 规则；高频 |
| 投票候选人图文简介 | VOTE | 档案字段加深 |
| 双选导师/选题附件简介包 | MUTUAL-* | 附件槽；通识 |
| 组队邀请站内信 | MUTUAL-TEAM | 消息；浅 |
| 拼车座位余量展示 | CARPOOL | 名额字段可视化 |
| 时间银行技能标签认证勾选 | TIMEBANK | 资料字段；浅 |
| 婚恋互相关注/取消 | DATING | 关系浅表；≠推荐 |
| 考试及格线可配 | EXAM | schema；通识高频 |
| 客观题自动判分口径钉死 | EXAM | 已有可钉；表内待补缺口项 |
| 问卷必答题标记与校验 | SURVEY | 通识高频 |
| 投票票数定时刷新（轮询） | VOTE | 前端轮询；≠ WebSocket |
| 双选盲选阶段（截止前互不可见） | MUTUAL-* | 规则开关；通识偶见 |
| 拼车性别/人数偏好备注 | CARPOOL | 文案字段；浅 |
| 时间银行兑换商品目录 | TIMEBANK | 浅兑换表；≠商城 |
| 婚恋见面意向登记（非支付） | DATING | 轻单；浅 |
| 错题本导出 | EXAM | CSV；刷题齐后加深 |
| 多选题部分得分规则 | EXAM | schema；通识 |
| 问卷矩阵题（简单表格题） | SURVEY | 题型加深；浅 |
| 投票每人每天限票 | VOTE | 规则；防刷加深 |
| 双选志愿互斥（同志愿不可双报） | MUTUAL-* | 校验；浅 |
| 时间银行信用分（爽约扣分） | TIMEBANK | 浅分；≠征信 |
| 拼车途经点文本 | CARPOOL | 多行；≠地图轨迹 |
| 婚恋举报处理时限提醒 | DATING | 对齐 deadline；浅 |
| 组队满员自动关招募 | MUTUAL-TEAM | 状态规则 |
| 考试交卷后不可修改开关 | EXAM | schema；通识 |
| 考试迟到禁止进入（开考后 N 分） | EXAM | 规则；通识 |
| 问卷结果图表（柱/饼） | SURVEY | ECharts；通识高频 |
| 投票匿名开关 | VOTE | schema；浅 |
| 双选结果公示页 | MUTUAL-* | 只读名单；通识 |
| 拼车取消惩罚提示（爽约计数） | CARPOOL | 规则；浅 |
| 时间银行发布须审 | TIMEBANK | 状态机；浅 |
| 婚恋资料审核驳回理由 | DATING | 审驳字段；通识 |
| 组队申请附言必填 | MUTUAL-TEAM | 字段；浅 |
| 考试题目导入 Word/Excel | EXAM | 导入加深；通识 |
| 问卷截止前提醒站内信 | SURVEY | 消息；浅 |
| 投票结果对学生延迟公布 | VOTE | 日期开关；浅 |
| 双选调剂志愿上限 | MUTUAL-* | 规则；浅 |
| 拼车乘客确认后锁座 | CARPOOL | 状态；浅 |
| 时间银行时长冻结（纠纷） | TIMEBANK | 状态；浅 |
| 婚恋理想对象条件筛选加深 | DATING | 筛选字段；浅 |
| 组队退出须队长同意 | MUTUAL-TEAM | 规则；通识 |
| 考试多卷随机抽题 | EXAM | 组卷加深；通识 |
| 问卷填写进度保存草稿 | SURVEY | 草稿；通识 |
| 投票候选人拉票文案字段 | VOTE | 字段；浅 |
| 双选导师学生互评 | MUTUAL-TUTOR | allowRating；浅 |
| 拼车行李件数备注 | CARPOOL | 字段；浅 |
| 时间银行技能证明附件 | TIMEBANK | requireAttach |
| 婚恋活动报名入口（叠活动） | DATING / ACTIVITY | 文案交叉；浅 |
| 考试监考口令（入场码） | EXAM | 字符串；≠人脸 |
| 问卷逻辑显示（显隐，非跳题） | SURVEY | 浅规则；跳题已有可区分 |
| 投票禁刷：实名后可投 | VOTE | 对照实名勾选；浅 |
| 双选面试时段预约叠 | MUTUAL-* / MEETING | 文案交叉；浅 |
| 拼车起点终点校区字典 | CARPOOL | 字典；浅 |
| 时间银行申诉单 | TIMEBANK | 轻单；浅 |
| 婚恋黑名单 | DATING | 轻名单；通识 |
| 组队技能匹配度提示（计数重合） | MUTUAL-TEAM | 浅计数；≠协同过滤 |
| 考试主观题评分细则字段 | EXAM | 阅卷备注；浅 |
| 问卷投放对象按组织 | SURVEY | 组织过滤；浅 |
| 投票弃权选项 | VOTE | 选项；浅 |
| 双选结果导出通知信 | MUTUAL-* | CSV+消息；浅 |
| 拼车评价后不可见对方电话 | CARPOOL | 脱敏规则；浅 |
| 时间银行时长转让 | TIMEBANK | 流水；浅；≠货币 |
| 婚恋资料相册审核 | DATING | 附件审；浅 |
| 考试成绩导入模板 | EXAM | 导入；通识 |
| 问卷填写后感谢页 | SURVEY | 静态页；浅 |
| 投票实时榜置顶前三 | VOTE | UI；浅 |
| 双选确认超时自动婉拒 | MUTUAL-* | 规则；通识偶见 |
| 拼车行程重复发布检测 | CARPOOL | 校验；浅 |
| 时间银行时长清零规则说明 | TIMEBANK | 文案；浅 |
| 婚恋匹配推荐算法 | — | **不支持**：协同过滤；筛选+私信顶 |
| 考试试卷难度标签 | EXAM | 字段；浅 |
| 问卷回收率工作台卡片 | SURVEY | 计数；通识 |
| 投票刷票检测中台 | — | **不支持**：浅 IP/实名提示顶 |
| 双选学生端志愿锁定倒计时 | MUTUAL-* | UI；浅 |
| 拼车费用AA计算器 | CARPOOL | 前端算；浅；≠支付 |
| 时间银行星级信誉 | TIMEBANK | allowRating 叠；浅 |

不支持：协同过滤匹配、真地图导航拼车、人脸监考、实时 IM SDK、恋爱社交推荐算法。

### 1.10 兜底

| 域 | 开题密功能枚举 | 状态要点 |
|----|----------------|----------|
| `DOM-GENERIC` | 仅真交叉或无贴切行业皮时的 ARCH 绑壳（CRUD/FLOW/TRADE/RESERVE） | 能具名 DOM 勿落这；交叉白名单见 domains 组 H |

#### 本组待补

| 功能 | 建议落域 | 说明 |
|------|----------|------|
| 交叉壳双主路径答辩导引页（只读） | GENERIC 真交叉 | README/门户一段；帮学生讲清两套路 |
| 通用壳行业词浅替换开关说明 | GENERIC | 文档口径；勿 silently 冒充具名 DOM |
| 真交叉时双菜单分区标签 | GENERIC | 导航文案；答辩导引配套 |
| 交叉白名单题答辩话术模板段 | GENERIC | README 固定段；浅 |
| 通用壳禁止静默改 Dom 标签的门禁说明 | GENERIC | 文档+匹配页口径；浅 |
| ARCH 绑壳与 DOM 具名优先级说明 | GENERIC | 文档口径；浅 |

---

## 2. 怎么用（程序员）

1. 开题模块 ↔ §1：已实现/扫词开 → 必须能 bake；bake 失败当 bug。  
2. **待补** → 改 `DOMAIN_CAPABILITIES` / Store / SQL / 菜单，补测，改本表。  
3. **不支持** → 匹配页提示原因；禁止静默通用壳冒充。  
4. 发现「表写已实现但出包没有」→ 先复现匹配域与 caps，再查 bake 门禁。  
5. 域默认能力组合以 [`domains.md`](./domains.md) 为准；本表不重复抄能力组合列。  
6. 扩库存按**通识毕设常写**加行，勿等样例库、勿按单校课表裁剪；超纲只进「不支持」。  
7. **压力测只计真缺口**（见文首）；别名/换皮钉口径/边角加深不计入新增。

## 3. 修订

| 日期 | 说明 |
|------|------|
| 2026-09-08 | 初版枚举；误用「演示级」 |
| 2026-09-08 | 改口径：已实现/扫词开/待补/不支持；写清不能 bake 原因；报修默认 deadline |
| 2026-09-08 | DOC-FIX：续借/预约/荐购/候补等改扫词开；OOS 标不支持；见 `capability-expansion-batch.md` |
| 2026-09-09 | E-10～E-14 + COPY/MAP 收口 |
| 2026-09-17 | 内容壳：留言≠条下评论；歌单=收藏夹 |
| 2026-09-18 | item_comment / userPublish 扫词开；续借/候补/订单评价升域默认口径 |
| 2026-09-20 | 换皮压力题能力岛回写 line_custom～lesson_pack |
| 2026-09-21 | venue_clean 与 housekeeping 分轨 |
| 2026-09-22 | 正文域+语境判定；系统内支付 vs 商户对接 |
| 2026-09-30 | 报名组一文一事；单据评价≠订单评价 |
| 2026-09-30 | **§1 按工厂级联重排**（借用/跟进/报修/报名/审批/交易/预约/内容/互动/兜底）；各组补口径+待补；CINEMA/DOCLIB/INSTRUMENT 归位 |
| 2026-09-30 | **通识加厚**：文首标明不依赖样例库/不绑单校；§0 补找回密码等横切待补；各组待补按全国 Web 管管类毕设常写项扩一圈 |
| 2026-09-30 | **通识再扩**：§0 补站内信已读/公告置顶/待办角标/帮助页等；各组待补再扩（借还榜、报修时间轴、选课退选上限、报销/用印/访客、堂食桌号、代约就诊、草稿箱、跳题问卷等） |
| 2026-09-30 | **压力测门·第1轮**：横切+10组扫缺口；本轮新增 **77** 行（组织树/RBAC/字典/批量导入、续借上限、候补递补、撤回申请、超时取消订单、楼中楼、试卷乱序等）；未出现整块新模块组 |
| 2026-09-30 | **压力测门·第2轮**：再扫横切+10组；本轮新增 **81** 行（重置密码/会话超时/富文本、荐购进度、用户撤单、分场次报名、确认收货超时、改约上限、及格线可配等）；仍无整块新模块组；距冻结阈值（&lt;5）仍远 |
| 2026-09-30 | **压力测门·第3轮**：本轮新增 **82** 行（省市区联动/强制公告、读者证号、维修报价确认、邀请码报名、证明查伪码、优惠券过期提醒、作者主页、矩阵题等）；并补第三方登录/CAS/多租户为不支持；仍无整块新模块组 |
| 2026-09-30 | **压力测门·第4轮**：收紧标准后再扫；本轮新增 **70** 行（系统 Logo 可配/密保找回、补签、审批委托、售后时限、问卷图表、开考迟到禁入等）；仍无整块新模块组 |
| 2026-09-30 | **压力测门·第5轮**：本轮新增 **64** 行（注册邀请码/密码定期更换、领用额度、审批退回再提、浅二维规格、开诊复诊等）；并收口杀毒/法大大/真短信为不支持 |
| 2026-09-30 | **压力测门·第6轮**：再收紧；本轮新增 **55** 行（拒低代码门户/拖拽 BPM/自制 BI；补脱敏可配、盘点锁库、驳回理由必填、多卷抽题、问卷草稿等） |
| 2026-09-30 | **压力测门·第7轮**：本轮新增 **63** 行（实名勾选/区块链不支持、工单挂起、订单改地址、监考口令等）；协作片单标不支持 |
| 2026-09-30 | **压力测门·第8轮**：本轮新增 **52** 行（拒微服务/K8s/ES；补异地登录提醒、版主任命、问卷按组织投放等） |
| 2026-09-30 | **压力测门·第9轮**：严筛；本轮新增 **51** 行（资料完整度横切、电子票夹、维修看板、预售说明等）；钉大数据/中台/直播/推荐算法不支持 |
| 2026-09-30 | **压力测门·第10轮**：继续严筛；本轮新增 **44** 行（拒灰度中台/APM/表单设计器/叫号大屏/公安上传；补盲盘、门票转让、签到涨积分等） |
| 2026-09-30 | **压力测口径改定**：只计整模块级（新菜单/主状态机、新 cap 或表漏写整岛、开题目录级章节）；边角加深往后稍稍不计入。第1～10轮松口径作废为冻结依据 |
| 2026-09-30 | **压力测门·整模块级第1轮**：新增 **8**（§0 补齐 coupon/spend_discount/member_tier/wallet/地址簿壳附带；待补素材库+一级佣金；不支持多级分销） |
| 2026-09-30 | **压力测门·整模块级第2轮**：新增 **25**（对照 capabilities 补 §0 漏写整岛：flash_price/规格/多维分类/推荐/点赞举报禁言/足迹联想/续借预约荐购/寄件报废盘点/三级审/签章及壳附带售后物流改约超时；不支持校园跑腿 App） |
| 2026-09-30 | **压力测门·整模块级第3轮**：新增 **23**（补候补/签到/单据评价/投稿/冲突催办/出入库/额度/材料/占用/通行码/选座/监测打卡/货架/认领线索/双选/评教维/二级审/互斥限额/周历；不支持企微钉钉与税控发票） |
| 2026-09-30 | **压力测门·整模块级第4轮**：新增 **12**（补基线脊柱 archive/ticket_flow/quota/order_lines/slot_reserve；L0/L1 schema 借期数量/强制附件/必填说明；骑手岗；不支持多商家入驻与一卡通门禁；二手走寄卖/商城皮） |
| 2026-09-30 | **压力测门·整模块级第5轮**：新增 **13**（在线用户/每日签到/定时任务台/广告位；钉自习室座位·心理咨询·校友·体测为换皮已实现；不支持代码生成/OSS/系统监控/人事工资/车牌识别） |
| 2026-09-30 | **压力测改真缺口口径**：无对应落点才计新增；别名/换皮说明/叠不支持不计。冻结改为连续 2 轮真缺口=0 |
| 2026-09-30 | **压力测门·真缺口第1轮**：新增 **4**（待补：砍价、活动抽奖/转盘；不支持：OCR、App 推送） |
| 2026-09-30 | **压力测门·真缺口第2轮**：新增 **4**（待补：成就勋章；不支持：众筹、拍卖、电子病历） |
| 2026-09-30 | **压力测门·真缺口第3轮**：新增 **3**（不支持：现金红包通道、学信网学历认证、安防视频监控对接；分享有礼/班车/家长端等有积分·预约·角色等价落点记 0） |
| 2026-09-30 | **压力测门·真缺口第4轮**：新增 **1**（不支持：生产报工/MES；驾校/宠物医/月子/培训/问诊/政务信访/会展等均有预约·活动·审批·挂号等价落点记 0） |
| 2026-09-30 | **压力测门·真缺口第5轮**：新增 **2**（不支持：跨境/保税、CMDB；健康码/共享出行/充电桩/SCRM/网关注册中心等有通行码·物联网·企微·微服务等价落点记 0） |
| 2026-09-30 | **压力测门·真缺口第6轮**：新增 **2**（不支持：收银外设硬件套件、开放平台 OpenAPI/Webhook；楼宇自控/GIS/国密等保/分库MQ 等有物联网·单体口径·安全说明等价落点记 0） |
| 2026-09-30 | **停滴水**：已有不支持簇上不再拆 POS/梯控/MQ/国密等单列计新增 |
| 2026-09-30 | **压力测门·真缺口第7轮**：新增 **0**（剩余探针均为换皮、过时防疫词、或物联网/闸机/单体/支付簇细分；无新菜单/新状态机/新 cap 缺口） |
| 2026-09-30 | **压力测门·真缺口第8轮**：新增 **0**（通识整模块探针均有落点或落入已有不支持簇；连续两轮 0 → **库存真缺口门冻结**） |
| 2026-09-30 | **冻结声明**：真缺口压力测门冻结。之后只改状态（待补→已实现等）或纠错；不靠拆不支持簇/换皮别名刷新增。边角加深仍往后稍稍 |
| 2026-09-30 | **借用/占用组加厚**：续借次数上限标已齐；应还日前 N 天站内提前催还域默认；超期限借/低库存站内信开题扫；PARCEL 催领与 EQUIP 用途必填域默认 |
| 2026-09-30 | **§1.1 收尾**：报废独立审批单 `scrap_request`；ASSET 申购单号确认 + PROCURE 一键入库；本组待补清零 |
| 2026-09-30 | **§1.2 收尾**：`follow_thicken` 跟进组加厚（CRM/EVENT/ATTEND/FUND/RECRUIT/GRADE/INTERN/LISTING）；ATTEND 假期额度域默认；本组待补清零 |
| 2026-09-30 | **§1.1/§1.2 硬闭环**：批量录用 API+管理端多选；收藏夹导出/复制清单；渠道饼图/阶段漏斗/成交漏斗进工作台；周报截止扫表催信；岗位 `expire_on` 自动下架；借用续借/预约/罚款与跟进非主链（peer/procure/patch）收进 mybatis Mapper/XML；三线 binder/`thesis.yml` 对齐 |
| 2026-09-30 | **论文图跟实包**：E-R 补跟进/借用加厚列中文；序列/泳道从 Vue `{{ batchHireLabel }}` 等按 `schema.labels`/`verbs` 解析演示按钮，禁止写死域词进骨架 |
