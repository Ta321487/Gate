# ${APP_NAME} · 使用说明（给学生）

> 解压后请先读本文。按下面步骤即可在本机跑起来，并理解代码该怎么讲、该改哪里。

---

## 1. 你拿到的是什么

这是一套**可运行的毕业设计系统源码**（前端 + 后端 + 数据库脚本），已按你的课题配置好业务文案与演示数据。

技术栈（写进论文「系统实现」即可）：

| 层次 | 技术 |
|------|------|
| 前端 | Vue 3 + Vue Router + Element Plus + Vite + Axios |
| 后端 | Spring Boot 3 + Spring JDBC（`JdbcTemplate`） |
| 数据库 | MySQL 8（脚本见 `sql/schema.sql`） |

**说明：** 本项目**没有使用 MyBatis / Mapper 接口**。持久化统一写在 `*Store` 类里，用 `JdbcTemplate` 执行 SQL。答辩时不要说「MyBatis 自动生成 Mapper」——目录里也没有空的 `mapper`/`entity` 包。

---

## 2. 环境准备

请先安装并确认版本大致匹配：

1. **JDK 17**（`java -version`）
2. **Maven 3.8+**（`mvn -v`）
3. **Node.js 18+**（建议 20 LTS，`node -v` / `npm -v`）
4. **MySQL 8**，本机可登录（默认脚本按 `root` / `root123` 写的，可改）

---

## 3. 五分钟启动

### 3.1 建库

用 MySQL 客户端或命令行执行项目根目录下的脚本：

```text
sql/schema.sql
```

脚本会创建数据库 **`${DB_NAME}`** 并写入表结构与演示数据。  
若你本机 MySQL 密码不是 `root123`，先改后端配置再启动（见下一小节）。

### 3.2 后端

```bash
cd backend
```

检查并按需修改：

`backend/src/main/resources/application.yml`

- `spring.datasource.username` / `password`
- `spring.datasource.url` 中的库名（应与脚本一致）

启动：

```bash
mvn spring-boot:run
```

成功后接口在：**http://127.0.0.1:8080**

### 3.3 前端

新开一个终端：

```bash
cd frontend
npm install
npm run dev
```

浏览器打开终端里提示的地址（一般是 **http://127.0.0.1:5173**）。  
前端开发服务器已把 `/api` 代理到后端 `8080`。

---

## 4. 演示账号（脚本预置）

多数课题种子数据相同（昵称随领域略有不同）：

| 用户名 | 密码 | 角色说明 |
|--------|------|----------|
| `admin` | `admin123` | **总管理员**（超级管理员）：可管账号、公告、业务配置等 |
| `subadmin` | `sub123` | **业务管理员**（子管）：处理业务单据，不管总控配置 |
| `user` | `user123` | **普通用户**：注册角色侧业务（借阅/报名/下单/预约等） |

也可在登录页走「注册」自建普通用户（管理员一般不开放自助注册）。

---

## 5. 目录怎么读（答辩常用）

```text
├── README.md                 ← 本说明
├── sql/schema.sql            ← 建库 + 演示数据（先执行）
├── backend/                  ← Spring Boot 后端
│   └── src/main/java/com/thesis/
│       ├── controller/       ← 接口层（给前端调用）
│       ├── service/          ← 用户、公告、消息等通用业务
│       ├── capability/       ← 核心业务能力（档案/单据/订单/预约等）
│       ├── config/           ← 数据源、跨域、领域开关绑定
│       └── common/           ← 统一返回、异常、鉴权工具
└── frontend/                 ← Vue 前端
    └── src/
        ├── views/            ← 页面（user 用户端 / admin 管理端）
        ├── layouts/          ← 布局
        ├── components/       ← 公共组件
        ├── router/           ← 路由
        ├── api/              ← Axios 封装
        └── utils/            ← 领域文案、校验等工具
```

### 后端怎么分层（重点讲清）

- **Controller**：接收 HTTP，做登录校验，调用 Store。
- **\*Store（JdbcTemplate）**：真正访问数据库。  
  例如 `ArchiveStore`（业务档案）、`TicketStore`（申请/借阅/报修等单据）、`OrderStore`、`SlotStore`、`UserStore`。
- **application.yml 里的 `thesis.*`**：本课题打开了哪些能力（是否有库存、逾期、预约表名等），启动时由配置绑定到运行时。

没有 `mapper` 包是**刻意设计**：毕设体量用 JDBC 模板更直观，SQL 和 Java 在同一处，方便你对照改和讲解。

### 前端怎么找页面

- 用户端：`frontend/src/views/user/`、门户布局 `layouts/PortalLayout.vue`
- 管理端：`frontend/src/views/admin/`、`layouts/AdminLayout.vue`
- 登录/注册：`views/Login.vue`、`views/Register.vue`

菜单与文案多数来自课题配置（如 `factoryDelivered.js`、领域 schema），**改显示名称优先改配置/文案工具，而不是到处硬编码中文。**

---

## 6. 常见改法（二次开发建议）

| 你想改什么 | 优先看哪里 |
|------------|------------|
| 登录后标题、主题色 | `frontend/.env`、`factoryDelivered.js`、主题样式 |
| 注册要填哪些资料 | 后端 `domain-profile-fields.json` + 前端资料组件 |
| 某张表字段 / 演示数据 | `sql/schema.sql`（改完需重新导入或手工 ALTER） |
| 接口逻辑（审核、库存） | `capability/*Store.java` 对应方法 |
| 管理端某个列表页 | `views/admin/` 下对应 Vue |
| 数据库账号密码 | `application.yml` |

改 Java 后重启后端；改 Vue 一般热更新即可，不行就停掉 `npm run dev` 再开。

---

## 6.1 老师要 SQL 时怎么做

老师说「交一份 SQL / 把某某查出来 / 再加一张表」时，**不必另起一套库**，在本项目上改即可。按要求类型选做法：

### A. 只要「建库脚本 / 表结构」（论文附录、开题材料）

直接交根目录的：

```text
sql/schema.sql
```

这就是完整建库 + 演示数据脚本。论文「数据库设计」章节按里面的 `CREATE TABLE` 画表、写字段说明即可。

### B. 要「查询类 SQL」（统计、多表关联、条件筛选）

1. 先在 MySQL 客户端里把语句写对、跑通。  
2. 把语句保存成单独文件，方便上交，例如：

```text
sql/queries-答辩演示.sql
```

可按业务写几条有代表性的，例如（表名以你课题 `schema.sql` 为准）：

```sql
-- 示例：按状态统计单据数量（把表名换成你库里的实际表）
SELECT status, COUNT(*) AS cnt
FROM signup
GROUP BY status;

-- 示例：用户与业务主表关联（按实际外键列调整）
SELECT u.username, u.nickname, a.title
FROM sys_user u
JOIN signup s ON s.username = u.username
JOIN activity a ON a.id = s.book_id
WHERE s.status = 'approved';
```

3. 若老师要求「系统里也能查」，再到对应 `*Store.java` 里用 `JdbcTemplate` 接上同一条 SQL（改接口 + 前端展示）。**先有可运行的 `.sql` 文件，再决定要不要进代码。**

### C. 要「加字段 / 加一张表」

1. **改** `sql/schema.sql`（正式交付以这份为准）。  
2. 本机已建过库时，可再写一份增量脚本，避免每次都删库重来，例如：

```text
sql/alter-老师要求.sql
```

```sql
USE `${DB_NAME}`;
-- 示例：业务主表加备注
ALTER TABLE activity ADD COLUMN remark VARCHAR(255) NULL COMMENT '备注' AFTER title;

-- 示例：新建辅助表（名称、字段按老师要求改）
CREATE TABLE IF NOT EXISTS activity_attach (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  activity_id BIGINT NOT NULL,
  file_name VARCHAR(200) NOT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

3. 若页面/接口要用新字段：同步改对应 `*Store.java` 的增删改查，以及前端表单/表格列。  
   **只交结构、不改功能**：改完 `schema.sql` + 演示插入即可。

### D. 要「学生自己会写 SQL」的证明

建议准备一个小文件夹上交或放进论文附录：

```text
sql/
  schema.sql              ← 系统建库（已有）
  queries-答辩演示.sql     ← 你手写的查询/统计
  alter-老师要求.sql       ← 若有加表加字段
```

答辩时打开 MySQL，现场执行 `queries-答辩演示.sql` 里的 2～3 条，比空讲「用了 JDBC」更有说服力。

### 注意

- 表名、字段名以**你这份** `schema.sql` 为准（不同课题表名不同，不要照抄别人库的表名）。  
- 改结构后若程序报错，多半是 Store 里 SQL 还没带上新列——对照报错改 Java。  
- 不要删掉系统运行必需的核心表（如 `sys_user`）和关键列；老师要的扩展用**加列/加表**，尽量别推翻重来。

---

## 7. 答辩可以怎么说（简洁版）

1. **前后端分离**：Vue 负责界面，Spring Boot 提供 REST API，Session 维持登录态。  
2. **业务按「能力」组织**：档案维护、流程单据、订单、时段预约等落在不同 Store，课题通过配置开关组合，而不是每个题目重写一整套后端。  
3. **数据访问**：采用 Spring JDBC，在 Store 中编写 SQL，结构清晰，便于演示与维护。  
4. **角色**：普通用户办理业务；子管处理业务；总管维护基础数据与账号。

把「你实际点过的功能路径」准备 2～3 条（例如：注册 → 浏览 → 提交单据 → 管理员审核），比背名词更重要。

---

## 8. 常见问题

**Q：前端能开，接口全失败？**  
先确认后端已启动；再看浏览器控制台 / Network 里 `/api` 是否 404 或连错端口。

**Q：登录提示密码错误？**  
确认已执行本包里的 `schema.sql`，并用上表账号；若改过 `thesis.password-hash`，需与库中密码存储方式一致。

**Q：为什么没有 Mapper 文件夹？**  
本系统使用 `JdbcTemplate`，不生成 MyBatis Mapper。以 `*Store` 为准即可。

**Q：论文里数据库设计写什么？**  
以 `sql/schema.sql` 中的表为准，画 ER 图、说明主键与主要业务流程表即可。

**Q：老师临时要几条 SQL / 加表怎么办？**  
见上文 **§6.1**：建库交 `schema.sql`；查询单独写 `sql/queries-答辩演示.sql`；加字段写 `ALTER` 或改 `schema.sql`，需要进系统再改对应 Store。

---

## 9. 交付物自检清单

- [ ] 执行 `sql/schema.sql` 成功  
- [ ] 后端 `8080` 可访问  
- [ ] 前端能打开，三种角色都能登录  
- [ ] 走通一条完整业务（提交 → 管理端处理）  
- [ ] 能指着 `Controller` → `Store` → 某张表讲清一次请求  

祝答辩顺利。
