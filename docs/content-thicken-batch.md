# §1.8 内容组加厚批次（已收口档案）

> **本文只负责**：地图 [`opening-feature-delivery-map.md`](./opening-feature-delivery-map.md) §1.8「本组待补」的**分批实现顺序、挂载口径、验收勾选**。  
> **不负责**：cap 定义（[`capabilities.md`](./capabilities.md)）；怎么审交付（[`delivery-audit-rules.md`](./delivery-audit-rules.md)）；清待补工序纪律（`.cursor/rules/opening-group-delivery.mdc`）。  
> **状态**：**已收口档案**（C-00～C-09 均已齐）。地图 §1.8 待补已清；不支持只留边界。  
> **索引**：[README.md](./README.md) · 地图 §1.8 · 范本 `reserve_thicken` / `trade_thicken`。  
> **不负责 UI 表面构图**：列表选型见 [`domain-group-ui-styles.md`](./domain-group-ui-styles.md)（本组加厚收口后再开实现 plan）。

---

## 0. 硬口径（写代码前先背）

### 0.1 一组一包

| 规则 | 含义 |
|------|------|
| **组模块** | `backend/app/bake/features/content_thicken.py` + `apply_content_thicken_to_spec` |
| **注册** | 必须挂进 `backend/app/bake/domain_schema.py`（紧接 `reserve_thicken` 之后） |
| **白名单** | `HUB_BYPASS_MODULES` + [`capabilities.md`](./capabilities.md) Hub 例外表同步登记 |
| **域集合** | `CONTENT_DOMAINS` = MEDIA / MUSIC / FORUM / BLOG / DOCLIB |
| **不抢邻组** | 不碰 §1.6 交易、§1.7 预约、§1.9 互动；婚恋举报等归邻组 |
| **Store 主战场** | `ArchiveStore`；论坛跟帖辅 `TicketStore`；辅 Message / Favorites / ItemComment / DemoScheduleJobs |
| **一轮只清本组** | 禁止同轮动 §1.9+；禁止只改地图不改骨架 |

### 0.2 一条待补 = 四件套 + 三骨架

硬口径：**管理端能管 + 用户端可产生数据（真写库）**。纯 Hint / 只读 / 打印 / 前端零读取字面量 → 不得标已齐。

| 件 | 真源 |
|----|------|
| ① 表 / 列 | `ensure_content_thicken_sql` + 既有 archive / ticket 列 |
| ② Store 写方法 | `ArchiveStore` 等（三套骨架同改） |
| ③ API | `ArchiveController` / 对应 Controller |
| ④ 前端控件 | ArchiveBrowse / 发帖发文页 / 管理端列表与审核 |

三骨架：`baseline` · `persistence-mybatis` · `persistence-jpa`。

### 0.3 挂载：域默认 vs 扫词加深

| 类型 | 何时开 | 地图「挂载」列 |
|------|--------|----------------|
| **五域通识底** | CONTENT_DOMAINS 主路径刚需（阅读数/热门等；域皮按域裁） | **域默认** |
| **能力岛加深** | 仅当已挂对应 cap（post_like / content_report / post_mute / browse_history / favorites / item_comment / points / wallet / userPublish） | 扫词挂 cap 时（C-08） |
| **禁止** | 因「论坛常见」把点赞/举报/禁言/积分做成永远开 | — |

组口径（地图原话）：archive 浏览为主；论坛跟帖走 ticket；留言默认（论坛除外）。条下评论/投稿/点赞等扫词见 §0。

### 0.4 不支持（不进待补实现）

| 边界 | 原因 |
|------|------|
| 转码 / CDN / 弹幕 | 组末已钉；无流媒体主线 |
| 影音会员真支付 / 曲库版权结算 | 系统内会员/点券顶；≠商户清算 |
| 影音片单多人协作编辑 | 个人片单顶 |
| 协同过滤推荐 / RAG 冒充文库 | OUT_OF_SCOPE；recommend 浅榜可顶 |
| 实时聊天室 SDK | 站内私信顶 |

### 0.5 每批工序（固定）

```
1. content_thicken：开关 / labels / 域默认或扫词条件
2. ensure 列 / 子表（禁止 JSON 冒充三范式）
3. ArchiveStore（及 Ticket/Message/Favorites）写方法 — 三套同改
4. Controller API — 三套 DomainRuntimeBinder 同绑
5. 用户端写控件 + 管理端管控件（文案无工厂腔）
6. 三绿才迁行：
   - pytest backend/tests/test_opening_map_skeleton_gate.py -q
   - pytest backend/tests/test_content_thicken_features.py -q
   - 受影响的 backend/tests/test_schema_*.py
7. 地图：待补 →「本组本轮已齐」；本册状态改已齐；changelog 一行
8. 业务稳定后 AOCI maintain（新 .py 先 scope acknowledge）
```

单批体量：**约 5～8 条**；含子表/状态机时砍到 4～5。

### 0.6 已有半截优先钉齐（忌重写）

| 待补表述 | 现网线索 | 策略 |
|----------|----------|------|
| 个人浏览历史 | `browse_history` cap | 内容域挂上时钉双端；禁止第二套足迹表 |
| 收藏 / 专栏订阅 | `favorites` | 分类/专栏变体加深；禁止平行收藏引擎 |
| 点赞 / 举报 / 禁言 | `post_like` / `content_report` / `post_mute` | 仅 cap 已挂时加深（C-08） |
| 条下评论 / 楼中楼 | `item_comment`；论坛回帖 ticket | 父评论 id 浅一层；≠无限嵌套 |
| 投稿上架通知 | `userPublish` schema | 审过发信；未开投稿不挂 |
| 文库下载台账 | `doclib` | 次数/记录/预览加深，不另起下载域 |

---

## 1. 批次总表

> **状态列**：`待写` → `实现中` → `已齐`（须过 §0.5 三绿 + 地图迁行）。

| 序 | ID | 主题 | 条数约 | 主要落域 | 状态 |
|----|-----|------|--------|----------|------|
| 0 | **C-00** | 脚手架：`content_thicken` + `domain_schema` + `HUB_BYPASS` + `test_content_thicken_features` + 本册 | — | 工厂 | **已齐** |
| 1 | **C-01** | 通识：阅读数 / 热门排行 / 个人足迹 / 标题搜索 | 4 | 五域裁剪 | **已齐** |
| 2 | **C-02** | FORUM 运营：精华置顶 / 锁定 / 草稿 / 移版 / 发帖上限 / 审后可见 / 版块公告 | 7 | FORUM | **已齐** |
| 3 | **C-03** | FORUM 互动治理：楼中楼 / @提醒 / 禁言到期 / 举报通知 / 评论点赞 / 敏感词 / 版主 / 评论折叠 / 操作日志 / 举报时效 | 10 | FORUM（BLOG 叠楼中楼等） | **已齐** |
| 4 | **C-04** | BLOG：订阅与订阅信 / 定时发撤 / 归档 / 系列文 / 原创声明 / 作者主页 / 评论通知 / 密码访问 / 友情链接 / 订阅数 | 12 | BLOG | **已齐** |
| 5 | **C-05** | MEDIA：进度 / 选集完播 / 海报墙 / 播放榜 / 下架原因 / 分集通知 / 定时发布叠 / 分享码 / 订阅叠 | 10 | MEDIA | **已齐** |
| 6 | **C-06** | MUSIC：歌手专辑筛 / 歌单公开私密 / 歌词 / 翻唱 / 收藏夹分组 / 分享码 / 音质文案 / 下架原因叠 | 8 | MUSIC | **已齐** |
| 7 | **C-07** | DOCLIB：下载记录 / 预览 / 权限角色 / 章节目录 / 版本 / 限额 / 审核 / 水印 / 标签云 / 试读说明 / 纠错 / 侵权投诉 | 12 | DOCLIB | **已齐** |
| 8 | **C-08** | 能力岛加深（仅 cap 已挂）：积分下载/付费点券、精华奖分、签到涨分、等级规则页、举报字典、评论举报、粉丝可见评论、投稿上架通知 | ~8 | 扫词 | **已齐** |
| 9 | **C-09** | 扫尾：对照地图「本组待补」清零；不支持段只留边界；批次改已收口档案 | 余量 | 全组 | **已齐** |

**推荐编码顺序**：C-00 → C-01 → C-02 → C-03 → C-04 → C-05 → C-06 → C-07 → C-08 → C-09。

可并行（不同 Store 触点、互不改同一状态机时）：C-05 ∥ C-06；C-04 文案项 ∥ C-07 前半（下载记录/预览）。

---

## 2. 分批明细

### C-00 脚手架

| 勾选 | 项 |
|------|-----|
| ☑ | 新建 `backend/app/bake/features/content_thicken.py`（`CONTENT_DOMAINS`、硬约束注释、`apply_content_thicken_to_spec`） |
| ☑ | `domain_schema.py` 注册（紧接 `reserve_thicken` 之后） |
| ☑ | `HUB_BYPASS_MODULES` + `docs/capabilities.md` Hub 例外表登记 |
| ☑ | `backend/tests/test_content_thicken_features.py`：只动五内容域、不碰交易/预约/互动语义 |
| ☑ | 本册 + README / 地图 §1.8 批次入口（立项行） |

**验收**：pytest 绿；可进 C-01。

---

### C-01 通识（本组通用 · 域默认裁剪）

| 地图待补 | 落点建议 | 挂载 |
|----------|----------|------|
| 帖子/文章阅读数展示 | archive.`view_count` + 详情递增；列表展示 | **域默认** 五域 |
| 热门排行（按浏览/下载计数） | 排序 API + 管理/用户榜页；DOCLIB 可按下载 | **域默认** 五域 |
| 个人浏览历史 | 复用 `browse_history`；未挂则内容域可域默认钉 | **域默认** MEDIA/MUSIC/BLOG（FORUM/DOCLIB 可选） |
| 帖子搜索（标题关键词） | 基线检索加深；标题前缀 | **域默认** FORUM/BLOG（MEDIA/MUSIC/DOCLIB 可叠标题搜） |

**硬约束**：热门=计数排序，≠协同过滤；足迹禁止第二套表。媒资播放次数排行归 C-05/C-06 域皮加深同一计数。

---

### C-02 FORUM 运营（域默认 · 仅 DOM-FORUM）

| 地图待补 | 落点建议 | 挂载 |
|----------|----------|------|
| 精华帖 / 置顶（管理标记+列表优先） | `essence` / `pinned` + 列表排序 | **域默认** FORUM |
| 帖子锁定（禁止再回） | `locked`；回帖闸 | **域默认** FORUM |
| 草稿箱（发帖/发文先存后发） | status `draft`；用户草稿列表 | **域默认** FORUM（BLOG 叠 C-04） |
| 帖子移动版块 | 管理改分类 | **域默认** FORUM |
| 论坛每日发帖上限 | AppPolicy 阈值 + 当日计数闸 | **域默认** FORUM |
| 发帖需审后可见开关 | schema 开关；未审仅作者/管理可见 | **域默认** FORUM |
| 版块公告（分类级须知） | 分类扩展字段 `section_notice` | **域默认** FORUM |

**硬约束**：精华/置顶≠推荐引擎；草稿自动保存加深归 C-03 或本批尾巴（浅 local/定时写 draft）。

同批可顺带：帖子草稿自动保存（浅，FORUM/BLOG）。

---

### C-03 FORUM 互动治理（域默认裁剪 · FORUM 为主）

| 地图待补 | 落点建议 | 挂载 |
|----------|----------|------|
| 二级回复（楼中楼，一层） | `parent_id`；浅一层 | **域默认** FORUM；BLOG 有评论时叠 |
| @提醒站内信（跟帖提到某人） | 解析 @ + MessageStore | **域默认** FORUM |
| 禁言到期自动解除 | `mute_until` + 定时/登录扫 | 有 `post_mute` 时生效；FORUM 域默认可钉字段 |
| 举报处理结果通知举报人 | 处理写库 + 站内信 | 有 `content_report` 时；FORUM 域默认入口 |
| 评论点赞计数 | 浅计数表/列 | **域默认** FORUM/BLOG（有评论时） |
| 敏感词拦截提示（本地词表） | 本地词表 + 提交闸 | **域默认** FORUM/BLOG |
| 论坛版主任命 | staff_post / 角色勾选浅 | **域默认** FORUM |
| 评论折叠（楼中楼过长） | UI 折叠阈值 | **域默认** FORUM/BLOG |
| 帖子精华/置顶操作日志 | 审计叠或操作日志表浅行 | **域默认** FORUM |
| 论坛举报表处理时效 | deadline 思路；超时提示 | **域默认** FORUM |

**硬约束**：楼中楼仅一层；敏感词≠云审核；禁言到期复用 `post_mute`，禁止第二套禁言。举报字典/评论举报归 C-08。

---

### C-04 BLOG 域皮（域默认 · 仅 DOM-BLOG）

| 地图待补 | 落点建议 | 挂载 |
|----------|----------|------|
| 专栏/分类订阅（收藏分类） | favorites 变体或 `category_follow` | **域默认** BLOG（MEDIA 叠 C-05） |
| 专栏订阅更新站内信 | 新文触发 MessageStore | **域默认** BLOG |
| 博客专栏订阅数展示 | 计数展示 | **域默认** BLOG |
| 文章定时发布 | `publish_at` + DemoScheduleJobs | **域默认** BLOG（MEDIA 叠 C-05） |
| 博客定时撤回（到点下架） | `unpublish_at` + 定时 | **域默认** BLOG |
| 博客归档按年月 | 列表年月筛 | **域默认** BLOG |
| 博客系列文（上一篇下一篇） | `series_id` / prev-next | **域默认** BLOG |
| 转载/原创声明勾选 | 发布字段 | **域默认** BLOG |
| 作者主页（TA 的文章/帖子） | 用户维度列表 | **域默认** BLOG；FORUM 可叠 |
| 博客评论邮件式站内信通知 | 新评论→作者信 | **域默认** BLOG |
| 博客文章密码访问 | 口令字段 + 校验 | **域默认** BLOG |
| 博客友情链接栏 | 多行浅表或字段列表 | **域默认** BLOG |

**硬约束**：订阅≠推荐引擎；定时走同一 DemoScheduleJobs；密码访问≠付费墙。体量偏大时可拆 C-04a（订阅/定时/归档/系列）与 C-04b（声明/主页/评论信/密码/友链）。

草稿箱与 C-02 共用 draft 状态；BLOG 本批须双端可见。

---

### C-05 MEDIA 域皮（域默认 · 仅 DOM-MEDIA）

| 地图待补 | 落点建议 | 挂载 |
|----------|----------|------|
| 播放进度记住（本地/按用户一条） | 进度表/列；按用户一条 | **域默认** MEDIA（MUSIC 叠 C-06） |
| 影音选集/分集列表 | 子项列表浅表 | **域默认** MEDIA |
| 影音选集完播标记 | 进度加深 `completed` | **域默认** MEDIA |
| 影音海报墙分类浏览 | 列表皮 + 分类 | **域默认** MEDIA |
| 媒资播放次数排行 | 复用 C-01 计数榜皮 | **域默认** MEDIA |
| 媒资下架原因登记 | `off_shelf_reason` | **域默认** MEDIA（MUSIC 叠） |
| 影音分集更新站内信 | 新分集→订阅/关注者信 | **域默认** MEDIA |
| 片单/歌单分享码（只读链接口令） | 字符串码 | **域默认** MEDIA（MUSIC 叠 C-06） |
| 文章定时发布（媒资侧） | `publish_at` 叠 C-04 机制 | **域默认** MEDIA |
| 专栏/分类订阅（媒资） | 同 C-04 订阅机制 | **域默认** MEDIA |

**硬约束**：进度≠多端云同步；片单协作编辑不支持（个人片单顶）；弹幕/真支付不进本批。

---

### C-06 MUSIC 域皮（域默认 · 仅 DOM-MUSIC）

| 地图待补 | 落点建议 | 挂载 |
|----------|----------|------|
| 曲库按歌手/专辑筛选 | 筛字段 | **域默认** MUSIC |
| 歌单公开/私密开关 | 收藏夹可见性 | **域默认** MUSIC |
| 曲库歌词文本字段 | 多行字段 | **域默认** MUSIC |
| 曲库翻唱标记 | 字段勾选 | **域默认** MUSIC |
| 收藏夹分组命名 | favorites 加深 | **域默认** MUSIC（MEDIA 可叠） |
| 片单/歌单分享码 | 同 C-05 码机制 | **域默认** MUSIC |
| 曲库音质切换（文案假切换） | UI 文案；不真转码 | **域默认** MUSIC |
| 媒资下架原因 / 播放进度 / 播放榜 | 叠 C-01/C-05 机制 | **域默认** MUSIC |

**硬约束**：音质切换禁止宣称真转码；版权结算不支持。

---

### C-07 DOCLIB 域皮（域默认 · 仅 DOM-DOCLIB）

| 地图待补 | 落点建议 | 挂载 |
|----------|----------|------|
| 下载次数展示与个人下载记录 | 台账加深 + 个人列表 | **域默认** DOCLIB |
| 资料预览（图片/PDF 新窗口） | 浏览器打开；≠预览云 | **域默认** DOCLIB |
| 文库下载权限按角色 | 角色勾选浅闸 | **域默认** DOCLIB |
| 文库章节目录（锚点列表） | 多行目录子表 | **域默认** DOCLIB |
| 文库资料版本历史（备注级） | 版本号+说明子表 | **域默认** DOCLIB |
| 文库下载次数个人限额 | 规则+阈值 | **域默认** DOCLIB |
| 下载审核（文库敏感类） | 浅审状态机 | **域默认** DOCLIB |
| 文库预览页水印（姓名） | 浅水印层 | **域默认** DOCLIB |
| 文库热门标签云（计数） | 标签计数；≠推荐 | **域默认** DOCLIB |
| 文库章节试读前 N 页说明 | 文案字段；≠DRM | **域默认** DOCLIB |
| 文库纠错反馈单 | 轻单/留言变体 | **域默认** DOCLIB |
| 文库侵权投诉单 | 轻单 | **域默认** DOCLIB |

**硬约束**：预览≠永中/转码云；积分下载/付费点券归 C-08（须 points/wallet）；≠借阅 ≠ RAG。体量大可拆 C-07a（记录/预览/权限/目录/版本）与 C-07b（限额/审核/水印/标签/试读/纠错/侵权）。

---

### C-08 能力岛加深（仅 cap 已挂）

| 依赖 cap / 开关 | 地图待补 | 落点 |
|-----------------|----------|------|
| points / wallet | 文库积分下载（扣点后下） | 下载前扣点；双端流水 |
| points / wallet | 文库付费下载（系统内点券） | 点券价+扣减；≠商户支付 |
| points | 精华帖奖励积分登记 | 管理点精华时记分 |
| points | 论坛每日签到涨积分 | 窄扫叠；有签到开关时 |
| points | 论坛用户等级积分规则页 | 文案页+规则说明；浅 |
| content_report | 内容举报原因字典 | 字典维护+提交必选 |
| content_report | 评论举报 | 举报目标扩到评论 |
| —（浅规则） | 评论仅粉丝可见（互关） | 关系浅表+可见闸；通识偶见 |
| userPublish | 投稿审过自动上架通知 | 审过→投稿人站内信 |

硬约束：未挂对应 cap 时无 thicken 旗 / 无按钮 / 无扣点入口。禁止因「文库常见」域默认硬挂 points/wallet。

三绿：`test_opening_map_skeleton_gate` + `test_content_thicken_features`（含 `test_c08_capability_islands`）。

---

### C-09 扫尾（收口）

| 勾选 | 项 |
|------|-----|
| ☑ | §1.8「本组待补」实现债清零（不支持项不进待补） |
| ☑ | 不支持段只留边界：转码 CDN、弹幕、真支付、版权结算、片单协作、协同过滤、RAG 冒充 |
| ☑ | 地图 changelog 有 C-00～C-09 收口行 |
| ☑ | `test_opening_map_skeleton_gate` + `test_content_thicken_features` 绿 |
| ☑ | 本册总表全部 **已齐**；文首改为「已收口档案」 |
| ☑ | `opening-group-delivery.mdc` 已有列表补上 `content_thicken` |
| ☑ | 作者主页 FORUM 叠 + 草稿自动保存（updateUserDraft / 双端防抖） |

---

## 3. Changelog

| 日期 | 说明 |
|------|------|
| 2026-10-09 | 批次立项：C-00～C-09；对齐 §1.6/§1.7 工序；尚未迁行 |
| 2026-10-09 | **C-00 已齐**：脚手架 `content_thicken` + `domain_schema` / `engine_sql` / `HUB_BYPASS` + 特征测；可进 C-01 |
| 2026-10-09 | **C-01 已齐**：阅读数/热门/足迹/标题搜索；三套 ArchiveStore + 双端；地图四条迁已齐 |
| 2026-10-09 | **C-02 已齐**：FORUM 运营七条；三套 ArchiveStore + TicketApplyOps 锁定闸 + 双端草稿/公告；地图七条迁已齐 |
| 2026-10-09 | **C-03 已齐**：楼中楼/@提醒/禁言到期/举报通知与时效/评论赞/敏感词/版主/折叠/精华置顶审计；地图十条迁已齐 |
| 2026-10-10 | **C-04 已齐**：BLOG 域皮十二条（订阅/定时/归档/系列/声明/作者页/评论信/口令/友链/订阅数/草稿叠）；地图迁已齐；MEDIA 叠项留 C-05 |
| 2026-10-10 | **C-05 已齐**：MEDIA 域皮十条（进度/分集完播/海报墙/播放榜/下架原因/分集信/分享码/定时与订阅叠）；地图迁已齐；MUSIC 叠项留 C-06 |
| 2026-10-10 | **C-06 已齐**：MUSIC 域皮八条（歌手专辑筛/歌词/翻唱/音质文案/歌单公开私密/收藏分组 + 进度/榜/下架/分享叠）；MEDIA 叠收藏分组；地图迁已齐 |
| 2026-10-10 | **C-07 已齐**：DOCLIB 域皮十二条（下载记录/预览/角色/章节/版本/限额/审核/水印/标签云/试读/纠错/侵权）；三套 DoclibStore + 双端；地图迁已齐；积分下载留 C-08 |
| 2026-10-10 | **C-08 已齐**：能力岛八条（积分下载/点券、精华奖分、签到、规则页、举报字典、评论举报、粉丝可见、投稿通知）；无订单壳扫词可挂 points；三套 Store + 双端；地图迁已齐 |
| 2026-10-10 | **C-09 已齐并收口**：FORUM 作者主页叠、草稿自动保存；不支持只留边界；本组待补清零；本册改已收口档案 |
