# 学生包 Redis 接入落点（规划册）

> **状态**：规划 · **未落地** · **未开工**。  
> **范围**：技术栈开关接到学生 ZIP；子面注入只走**基线横切登记表**，不按域临场改业务。  
> **对标**：`addons.spring_security`（扫词 → 匹配确认 → overlay → README/论文同字）。  
> **姊妹册**：[`tech-stack-delivery.md`](./tech-stack-delivery.md)

本册是**毕设可交齐**的 Redis 栈交付。架构评审意见已吸收处见 **§4**；未采纳处写明原因。

---

## 0. 交什么

| 项 | 口径 |
|----|------|
| 开关名 | `addons.redis`（与 `persistence` / `spring_security` 正交） |
| 受益面 | **全域**（全部 `DOM-*` / GENERIC）：一套叠层，不绑域、不按域复制 |
| **底线交齐** | 开则必有：依赖 + 连得上的 Redis + **Spring Session（JSON 序列化）** + 可跟做的本机启动说明 + README/论文同字；关则整包无 Redis |
| 默认 | 关 → 容器 `HttpSession`（现网） |
| 开题点名 | 推荐开；人工可关 → **双显**；任意域写了都能开 |
| 关则 | ZIP / README / 论文不得写「已集成 Redis」 |
| 永不交 | 集群/哨兵、消息队列、向量库、工厂进程 Redis/ARQ；**未实现却宣称**「Redis 挂了自动回退本地 Session」 |

开题只写「用了 Redis」→ Session 落 Redis 即技术栈表述交齐。  
开题**还写**缓存 / 分布式锁 / 验证码冷却等 → **同一 `addons.redis`、同一 Redis 实例**上加横切面（见 §0.1），挂了必须有**可演示调用**（§0.2）。

### 0.1 同开关上的横切面（要则交齐）

原则：**Redis 连接只建一次**；Session 是默认面；其它面用扫词决定挂不挂，挂了就必须有代码 + 门禁 + 材料同字。

| 面 | 何时挂 | 栈上交什么 | 怎么定「用不用」 |
|----|--------|------------|------------------|
| **Session** | `redis=on` **必挂** | Spring Session Data Redis + **强制 JSON 序列化**（§1.3 #14） | 开开关即用 |
| **客户端 Bean** | `redis=on` **必挂** | `StringRedisTemplate`（或等价）；禁止各功能私拉连接 | 开开关即有 |
| **Cache** | 开题点名「缓存」等（只判挂不挂） | `CacheManager` + §0.2 登记注入 | `REDIS_CACHE_HINTS` |
| **Lock / TTL 键** | 开题点名分布式锁 / 冷却等（只判挂不挂） | 共用工具类（setNX+TTL **或** Redisson，工厂择一写死）+ §0.2 登记注入 | `REDIS_LOCK_HINTS` |
| **限流** | 开题点名接口限流（只判挂不挂） | 全局一处计数器 + TTL + §0.2 登记注入 | `REDIS_RATE_HINTS` |

**键名从哪来**

- 开题**扫不到**具体业务键，也不从开题抠键名。
- 扫词只回答：Session / Cache / Lock / Rate **挂哪些面**。
- 前缀 → bake 用学生包应用名 / 交付名（与 `spring.application.name` 同源），形如 `{app}:cache:`、`{app}:lock:`、`{app}:rate:`；**禁止** `thesis:` / `factory:` / `gf-`。
- 规范形状工厂统一，字面每包不同；常量 bake 写入，README 同字。
- Session 键交给 Spring Session（可用同一 app 名作 namespace）。
- 禁止按域第二套前缀；禁止 LLM 编键。

### 0.2 子面必须有可演示调用（防空壳）

**采纳「不能只生成空工具类」**；**不采纳**「全域强行给订单提交 / 库存扣减加锁」——借阅、报修、内容等包没有订单，会逼出假落点或只给交易域装有。

硬口径：

1. 子面点亮 → 必须命中 **基线横切注入登记表** 至少一行；bake 改的是表内路径，不是临场「找个业务塞一下」。  
2. 登记表只收**几乎每包都有**或**已由 cap 挂上才存在**的基线点；无落点则 **不许推荐/点亮该子面**（或开题要了但包无落点 → 双显「材料写了、本包无对应横切」）。  
3. 门禁：子面 on → 对应注入点源码可检出（注解 / 工具类调用）；否则挡 ZIP。  
4. 答辩能指到具体接口：「缓存的是公告列表」「锁的是登录冷却」——不是「我有个 RedisUtil」。

**登记表初稿（开工前钉死进代码常量；可增行，禁止按域旁路）**

| 子面 | 优先注入点（基线横切） | 演示怎么说 |
|------|------------------------|------------|
| Cache | 门户/管理端 **公告列表只读**（`NoticeStore` / 对应 Controller 读路径 `@Cacheable`，写路径显式 evict） | 热点公告走 Redis，减轻库压 |
| Cache 备选 | 已挂 lookup 的只读选项列表（有表才挂） | 字典/下拉缓存 |
| Lock | **登录失败 / 验证码或短时冷却**（认证横切；全域有登录） | 防刷、短时锁 |
| Lock 加分（非唯一） | 包已挂 `order_lines` 时，下单写路径可再挂一行；**无订单域不挂、不因此拒收 Lock 子面** | 防重复提交（仅交易壳） |
| Rate | 登录或公开写接口全局限流 Filter 一处 | 接口限流 |

落点增量（相对 §1 Session 底座）：

| # | 落点 | 做什么 |
|---|------|--------|
| E1 | `stack_scan.py` | Hints → 子面推荐；**不**抽键名 |
| E2 | Match 确认 | 子面勾选；双显 |
| E3 | `addon-redis` + 注入登记表 | Session+Template 底座；子面配置裁进包；**按表改基线横切调用点** |
| E4 | 键约定真源 | bake 写入的 `{app}:…` 常量 + README；门禁对账 |
| E5 | 门禁 | 无 CacheManager / 无工具类 / **无登记注入痕迹** → 挡；关则不得宣称 |
| E6 | 测试 | 子面开/关；注入点存在；底座 × persistence × Security |

---

## 1. 落点清单（技术栈轴 · Session 底座）

### 1.1 扫词

| # | 落点 | 做什么 |
|---|------|--------|
| 1 | `backend/app/bake/stack_scan.py` | `REDIS_HINTS`；点名 → `recommended_redis` / `addons.redis`；未落地前「规划内未落地」强提示，禁止静默忽略 |
| 2 | `docs/tech-stack-delivery.md` | 按需开关表登记 Redis |
| 3 | `.cursor/rules/tech-stack-delivery.mdc` + `scripts/sync-ide-rules.ps1` | 摘要：开则真有 Session→Redis |

### 1.2 匹配确认

| # | 落点 | 做什么 |
|---|------|--------|
| 4 | `backend/app/models` Project | `recommended_redis` / `redis` 布尔列（对标 Security） |
| 5 | 工厂库迁移 | 加列 |
| 6 | `project_match.py` | 上传/确认读写开关 |
| 7 | API schemas | 请求响应带字段 |
| 8 | `MatchTab.vue` | 开关 + 开题 vs 拟选双显 |
| 9 | `useProjectDetail.js` | form / dirty / confirm |
| 10 | `Help.vue` | 词条：开=Spring Session→Redis；关=容器 Session |

### 1.3 Bake 叠层

| # | 落点 | 做什么 |
|---|------|--------|
| 11 | `skeletons/overlays/addon-redis/` | 新建（对标 `addon-spring-security`） |
| 12 | pom | `spring-boot-starter-data-redis` + `spring-session-data-redis`（跟 Boot BOM） |
| 13 | `application.yml` 片段 | `spring.data.redis.*`、`spring.session.store-type=redis`；超时对齐现网 |
| 14 | Java 配置（**必做**） | **禁止默认 JDK 序列化**。Session 强制 `GenericJackson2JsonRedisSerializer`（或等价 JSON）；防实体未 `Serializable` 导致登录 `NotSerializableException`；Redis 桌面能看明文，便于答辩 |
| 15 | `backend/app/bake/addons.py` | `resolve_redis` / `apply_redis_overlay`；并入 `apply_addons_overlays` |
| 16 | `engine_bake.py` | 沿用 addons 入口；与 Security 同开可编译可登录 |
| 17 | `pack_prune` / bake 断言 | 开必有依赖+JSON 序列化配置；关必无残留 |
| 18 | 学生包 README（**本机第一**） | ① **Windows 免安装**：解压即用的 Redis 获取说明 + 「双击 `redis-server.exe`」；链接用可维护真源（GitHub Release / 学校网盘口径），**禁止把 exe 打进 ZIP**；② 环境变量；③ Docker 为可选附录。缺 Windows 路径 = 未交齐 |
| 19 | compose 片段 | `redis=on` 可带 `redis` 服务；**不能替代** #18 的免安装说明 |

### 1.4 兼容（仍属栈）

| # | 落点 | 做什么 |
|---|------|--------|
| 20 | 现有 `HttpSession` 调用面 | 保持不变（属性尽量基础类型 / 已能 JSON 化） |
| 21 | `addon-spring-security` 同开 | 登录/登出必须可用 |
| 22 | 基线「枚举容器 Session」的在线用户（若有） | Redis 下改 SessionRepository **并交齐** |
| 23 | jdbc / mybatis / jpa | 三线各 bake + `mvn compile` |

### 1.5 诚实闸与文案

| # | 落点 | 做什么 |
|---|------|--------|
| 24 | bake gate / QA | 点名却关 → 双显或挡；开却无依赖 / 无 JSON 序列化 / 子面无注入 → **挡 ZIP** |
| 25 | 工厂侧 `redis` 敏感词 | 工厂进程禁 Redis ≠ 学生包开关已开可写 |
| 26 | README / 论文系统实现 | 开写 Session+Redis；关只写 HttpSession。答辩对齐口径见 §1.5a |
| 26a | 假降级 | 材料**禁止**写「Redis 挂了自动回退本地 Session」，除非真实现并有测；默认口径：启动前先开 Redis，连不上则登录不可用（诚实） |

### 1.5a 答辩 / README 可对齐话术（须与实包一致）

| 问 | 可写答案（须已实现） |
|----|----------------------|
| 为何 Session 用 Redis？ | 会话不绑单机内存；后端重启后登录态仍可在（配合冒烟测） |
| 为何还做缓存/锁？（仅子面已挂时） | 指向 §0.2 真实注入点：公告缓存 / 登录冷却等，禁止空讲「降低压力」无代码 |
| Redis 挂了怎么办？ | **默认**：先保证本机 Redis 已启动；应用依赖 Redis 可达。若将来做降级，须单独立项 + 门禁，本册不宣称 |

### 1.6 测试（交齐必绿）

| # | 落点 | 做什么 |
|---|------|--------|
| 27 | `tests/test_stack_scan.py` | 点名推荐开；未写默认关 |
| 28 | `tests/test_redis_bake.py` | 对标 Security bake；三 persistence；开有 JSON 序列化配置；关无残留 |
| 29 | 冒烟 | 起 Redis：登录 → 重启后端 → 会话仍在 |
| 30 | 组合 | Security × Redis；子面 on → 注入点断言 |

### 1.7 收口文档

| # | 落点 | 做什么 |
|---|------|--------|
| 31 | 本册状态 | 落地后改「现行」 |
| 32 | `docs/README.md` | 已挂索引 |
| 33 | `HANDOFF.md` | **开工当日记**；本册不等于开工令 |

---

## 2. 施工顺序（开工后再做）

1. 扫词 + Project 字段 + Match 双显  
2. `addon-redis`（含 **JSON Session 序列化**）+ `addons.py` + README（**Windows 免安装优先**）+ 可选 compose  
3. §0.2 注入登记表 + 门禁（禁空壳）  
4. 测：三线 compile + Session 冒烟 + 子面注入断言  
5. `tech-stack-delivery`：未落地 → **已可 bake**  

---

## 3. 不做

- 未下令就改骨架 / 开开关出包  
- 按域临场改订单/库存当 Lock 唯一落点（无订单域硬塞）  
- 只给某域接 Redis、其它域装没有  
- 工厂控制台改用 Redis  
- ZIP 内塞 Redis 安装包二进制  
- 默认 JDK Session 序列化  
- 无生成路径却开 `addons.redis`  
- 子面空挂；材料假吹 Redis 降级回退  

---

## 4. 评审意见采纳表（质检单 · 不开工）

| 意见 | 判 | 计划怎么落 |
|------|----|------------|
| 开关正交、子面扫词、`{app}:` 前缀、双显诚实闸 | **照做** | 已在 §0 / §1 |
| 强制 JSON Session 序列化 | **采纳** | #14、#17、#28 |
| README Windows 免安装 + 双击 exe；勿只靠 Docker | **采纳** | #18 为主，#19 为辅；不进 ZIP 二进制 |
| 子面必须有真实业务注入，禁空工具类 | **采纳精神** | §0.2 登记表 + 门禁 |
| 强制给「下单 / 扣库存」加锁 | **不整条采纳** | 仅作 order_lines 包加分行；Lock 主落点用登录冷却等全域横切 |
| README 答辩话术 Session/缓存 | **采纳（须与实包一致）** | §1.5a |
| 「Redis 挂了自动回退本地 Session」 | **不采纳为默认宣称** | 未实现即假成功；要做另立项 |
