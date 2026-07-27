# ${APP_NAME}

> 解压后请先读本文。按下面步骤即可在本机跑起来。

---

## 1. 你拿到的是什么

本仓库是一套可运行的毕业设计系统（前端 + 后端 + 数据库脚本），含样例数据，便于本地启动与答辩。

技术栈（可写进论文「系统实现」）：

| 层次 | 技术 |
|------|------|
| 前端 | Vue 3 + Vue Router + Element Plus + Vite + Axios |
| 后端 | ${PERSISTENCE_BACKEND} |
| 数据库 | MySQL 8（脚本见 `sql/schema.sql`） |

**说明：** ${PERSISTENCE_NOTE}

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

脚本会创建数据库 **`${DB_NAME}`** 并写入表结构与样例数据。  
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

## 4. 样例账号

导入 `sql/schema.sql` 后可用下列账号登录（以脚本中的插入为准）：

| 用户名 | 密码 | 说明 |
|--------|------|------|
| `admin` | `admin123` | 总管理员：账号、公告、业务配置等 |
| `subadmin` | `sub123` | 业务管理员：处理业务单据，不管总控配置 |
| `${DEMO_PORTAL_USER}` | `${DEMO_PORTAL_PASS}` | ${DEMO_PORTAL_DESC} |

若脚本里还有其它账号（如现场作业人员、`user2` 私信样例号），密码一般为「用户名 + `123`」。  
也可在登录页「注册」自建普通用户（管理员账号一般不开放自助注册）。

开通一对一私信时：用普通窗口登录 `user`、无痕窗口登录 `user2`（密码均为 `user123`），即可互发消息。

---

## 5. 目录怎么读（答辩常用）

```text
├── README.md                 ← 本说明
├── sql/schema.sql            ← 建库 + 样例数据（先执行）
├── backend/                  ← Spring Boot 后端
│   └── src/main/java/${JAVA_PACKAGE_PATH}/
│       ├── controller/       ← 接口层（给前端调用）
│       ├── service/          ← 用户、公告、消息等通用业务
│       ├── capability/       ← 核心业务能力（档案/单据/订单/预约等）
│       ├── config/           ← 数据源、跨域、业务开关绑定
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
- ${PERSISTENCE_STORE_LINE}
- **application.yml 里的 `thesis.*`**：本系统打开了哪些业务能力（库存、逾期、预约表名等），启动时绑定到运行时。
- **接口传参**：收藏 / 足迹 / 购物车等少数接口写法略有差异，**本包前后端已对齐**。改的时候跟着现有 `Controller` 和 `frontend/src/utils/apiCalls.js` 即可。

${PERSISTENCE_NOTE}

### 前端怎么找页面

- 用户端：`frontend/src/views/user/`、门户布局 `layouts/PortalLayout.vue`
- 管理端：`frontend/src/views/admin/`、`layouts/AdminLayout.vue`
- 登录/注册：`views/Login.vue`、`views/Register.vue`

菜单与页面文案多在 `frontend/src/appDelivered.js` 与相关配置里，**改显示名称优先改这些配置，避免在页面里到处硬编码中文。**

---

## 6. 常见改法（二次开发建议）

| 你想改什么 | 优先看哪里 |
|------------|------------|
| 登录后标题、主题色 | `frontend/.env`、`appDelivered.js`、主题样式 |
| 注册要填哪些资料 | 后端 `domain-profile-fields.json` + 前端资料组件 |
| 某张表字段 / 样例数据 | `sql/schema.sql`（改完需重新导入或手工 ALTER） |
| 收货地址 / 口味备注（商城点餐） | 表 `user_address`；下单写入订单的收货与 `taste_note` |
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

这就是完整建库 + 样例数据脚本。论文「数据库设计」章节按里面的 `CREATE TABLE` 画表、写字段说明即可。

### B. 要「查询类 SQL」（统计、多表关联、条件筛选）

1. 先在 MySQL 客户端里把语句写对、跑通。  
2. 把语句保存成单独文件，方便上交，例如：

```text
sql/queries-答辩.sql
```

可按业务写几条有代表性的，例如（表名以本包 `schema.sql` 为准）：

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
   **只交结构、不改功能**：改完 `schema.sql` + 样例插入即可。

### D. 要「学生自己会写 SQL」的证明

建议准备一个小文件夹上交或放进论文附录：

```text
sql/
  schema.sql              ← 系统建库（已有）
  queries-答辩.sql     ← 你手写的查询/统计
  alter-老师要求.sql       ← 若有加表加字段
```

答辩时打开 MySQL，现场执行 `queries-答辩.sql` 里的 2～3 条，比空讲「用了 JDBC」更有说服力。

### 注意

- 表名、字段名以本包 `schema.sql` 为准。  
- 改结构后若程序报错，多半是 Store 里 SQL 还没带上新列——对照报错改 Java。  
- 不要删掉系统运行必需的核心表（如 `sys_user`）和关键列；扩展需求用**加列/加表**，尽量别推翻重来。

---

## 7. 答辩可以怎么说（简洁版）

1. **${SECURITY_AUTH_LINE}**  
2. **业务分层**：档案维护、流程单据、订单、时段预约等落在不同 Store，由配置组合启用。  
3. **数据访问**：见上文「技术栈」与持久层说明（JdbcTemplate 或 MyBatis）。  
4. **角色**：普通用户办理业务；业务管理员处理单据；总管理员维护基础数据与账号。

把「你实际点过的功能路径」准备 2～3 条（例如：注册 → 浏览 → 提交单据 → 管理员审核），比背名词更重要。

---

## 8. 常见问题

**Q：前端能开，接口全失败？**  
先确认后端已启动；再看浏览器控制台 / Network 里 `/api` 是否 404 或连错端口。

**Q：登录提示密码错误？**  
确认已执行本包里的 `schema.sql`，并用上表账号；若改过 `thesis.password-hash`，需与库中密码存储方式一致。

${PERSISTENCE_FAQ}

${SECURITY_FAQ}

**Q：论文里数据库设计写什么？**  
以 `sql/schema.sql` 中的表为准，画 ER 图、说明主键与主要业务流程表即可。

**Q：老师临时要几条 SQL / 加表怎么办？**  
见上文 **§6.1**：建库交 `schema.sql`；查询单独写 `sql/queries-答辩.sql`；加字段写 `ALTER` 或改 `schema.sql`，需要进系统再改对应 Store / Mapper。

---

## 9. 交付物自检清单

- [ ] 执行 `sql/schema.sql` 成功  
- [ ] 后端 `8080` 可访问  
- [ ] 前端能打开，三种角色都能登录  
- [ ] 走通一条完整业务（提交 → 管理端处理）  
- [ ] 能指着 `Controller` → `Store` → 某张表讲清一次请求  

祝答辩顺利。
