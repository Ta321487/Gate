# §0 通识横切清待补批次

> **本文只负责**：地图 [`opening-feature-delivery-map.md`](./opening-feature-delivery-map.md) **§0 横切**待补的分簇顺序、**分波实现要点**、挂载口径、验收勾选。  
> **不负责**：域组 `*_thicken`（§1.1～§1.9 已收口）；§1.10 GENERIC 导引（已浅清）；域组 UI 表面（[`domain-group-ui-styles.md`](./domain-group-ui-styles.md)）；AI 轴；cap 定义（[`capabilities.md`](./capabilities.md)）。  
> **状态**：**X-AUTH 已齐**；**X-MSG XM-00～XM-02 已齐**；**X-DASH XD-01～02 已齐**；下波 **X-ORG**。  
> **索引**：[README.md](./README.md) · 地图 §0 · 范本工序见 `.cursor/rules/opening-group-delivery.mdc`（四件套 / 三骨架 / 门禁），**但不**新建 `*_thicken.py`。

---

## 0. 硬口径

### 0.1 与域组加厚的分工

| 层 | 文档 / 模块 | 何时做 |
|----|-------------|--------|
| 域组四件套 | 地图 §1.x + `*_thicken` | **已收口**；禁止再开新 thicken |
| **本册：§0 横切** | 基线 auth / org / message / dict / 工作台… | 一轮一簇；落点共享骨架，非域皮 |
| UI 表面 | `{组}_surface_style` | 外链选型册；一组一独立 plan |

### 0.2 一轮 = 一簇（禁止跨簇、禁止套 thicken）

| 规则 | 含义 |
|------|------|
| **簇** | 下表 X-AUTH / X-MSG / …（按落点，不按 DOM） |
| **波** | 簇内再切 XA-01 / XA-02…（共享列与管线的一批）；**禁止**同轮跨波硬塞邻簇项 |
| **模块** | 改基线 Store / Controller / Vue；**禁止** `generic_thicken` / 新 `*_thicken` |
| **一轮只清本簇本波** | 禁止同轮动邻簇或域组已齐行 |
| **迁行** | 地图 §0 行状态：待补 → 已实现；本册勾选表改已齐 |

### 0.3 一条待补 = 四件套 + 三骨架

硬口径仍是：**管理端能管 + 用户端可产生数据（真写库）**。  
纯 Hint / 只读 / 打印 / 前端零读取字面量 → 不得标已齐（与地图文首一致）。

三骨架：`baseline` · `persistence-mybatis` · `persistence-jpa`。

### 0.4 验收（每波）

```
1. 本波四件套齐（表/列 · Store · API · 前端控件）
2. pytest backend/tests/test_opening_map_skeleton_gate.py -q（若本波写入 labels 契约）
3. 本簇特征测 backend/tests/test_auth_crosscut_features.py -q（或扩测）
4. 新菜单则 pytest backend/tests/test_menu_routes.py -q
5. 地图 §0 对应行迁状态；本册本波勾选改已齐
6. 动了 Java 骨架且有 mvn：test_skeleton_mvn_compile / bake probe（slow）
```

### 0.5 不做

- 新开任何域组 `*_thicken.py`
- 把横切做成具名 DOM 专线
- UI `*_surface_style`（另 plan）
- 真短信 / 真 SMTP / OAuth / CAS / 多租户（地图已标不支持）
- 学生可见文案出现工厂腔（「演示」「开题」「bake」「DOM」等）；试用账号按钮文案用「试用账号」

---

## 1. 分簇总表

| 簇 | 状态 | 代表落点 | 建议顺序 |
|----|------|----------|----------|
| **X-AUTH** | **XA-02 已齐** | 找回密码、锁定冷却、踢下线、改绑、邀请码… | **1（首簇·已齐）** |
| **X-MSG** | **XM-00～02 已齐** | 站内信/公告加深/广告位 | 2 |
| **X-DASH** | **XD-01～02 已齐** | 待办角标/快捷入口；PV/我的单据/定时任务只读台 | 3 |
| **X-ORG** | 待开 | 组织树、RBAC 勾选、**字典**、sys_config、数据权限… | 4 |
| **X-LIST** | 待开 | 高级筛选、批量操作、导入导出、回收站… | 5 |
| **X-UX** | 待开 | Toast、打印、灯箱、帮助页… | 6 |

> **分工提醒**：开题口头常说的「登录 / 字典 / 角标」分属 X-AUTH / X-ORG / X-DASH，**禁止**同轮混做。

活表行以地图 §0 为准；本册钉波次与实现要点，不复制地图全文。

---

## 2. X-AUTH 波次总表

> **状态列**：`待写` → `实现中` → `已齐`（须过 §0.4 + 地图迁行）。

| 序 | ID | 主题 | 条数约 | 状态 |
|----|-----|------|--------|------|
| 0 | **XA-00** | 脚手架：`auth_crosscut` feature + SQL 注入钩子 + 特征测空架 + 本册波次 | — | **已齐** |
| 1 | **XA-01** | 会话安全闭环：锁冷却 / 强制改密 / 定期换密 / 超时 / 记住登录 / 强度 / 密保找回 / 试用账号一键填 | 8 | **已齐** |
| 2 | **XA-02** | 会话与资料加深：在线踢下线 / 改绑 / 登录记录异地 / 邀请码注销激活 / 协议闸 / 验证码文案 / 唯一校验契约 / 实名勾选 / 手机号格式 | ~15 | **已齐** |

**推荐编码顺序**：XA-00 → XA-01 →（收口迁行）→ XA-02。

---

## 3. 基线现状（写前对照 · 禁止平行第二套）

### 3.1 已有（叠加深）

| 能力 | 真源 |
|------|------|
| 验证码 + 登录 + 注册 + `/me` | `skeletons/baseline/.../AuthController.java` |
| 认证 / 启停 / `adminResetPassword` | `UserStore.java` × baseline + mybatis + jpa |
| 自助改密（旧+新；改后清 session） | `ProfileController` + `Profile.vue` |
| 管理端重置密码 UI | `UsersAdminController` + `UsersAdmin.vue` |
| 永久停用 `enabled=0` | 登录拒 + `40102`（**≠**失败锁定冷却） |
| 登录审计（有 `audit_log` 时） | `AuditLogStore.record(..., "login", ...)` |
| 壳文案 | labels：`authEyebrow` / `authLead` / `authPoints`；delivered：`authTemplate` 等 |

### 3.2 缺口（本簇要补）

- `sys_user` 无：`failed_login_count`、`lock_until`、`must_change_password`、`password_changed_at`、密保列
- 无忘记密码页 / 密保校验 API
- 无闲置超时、记住登录、服务端 `/logout`
- 管理重置**不**置强制改密闸
- 无 `test_auth_crosscut_features.py`

---

## 4. XA-00 脚手架（实现要点）

| 勾选 | 项 |
|------|-----|
| ☑ | 新建 `backend/app/bake/features/auth_crosscut.py`：列常量、`ensure_auth_crosscut_sql`、labels 种子键、模块头注释钉硬约束 |
| ☑ | `engine_sql.py` **常开**调用注入——通识不扫词 |
| ☑ | Hub：`HUB_BYPASS_MODULES` + `docs/capabilities.md` 例外表一行（**非** thicken） |
| ☑ | `backend/tests/test_auth_crosscut_features.py`：列注入 / AppPolicy / labels 门禁 |
| ☑ | 本册波次表 + README 状态句更新 |

**硬约束**：禁止 `*_thicken` / `generic_thicken`；禁止按 DOM 分叉 auth。

**验收**：pytest 空架绿；可进 XA-01。

---

## 5. XA-01 会话安全闭环（已齐 · 实现要点）

### 5.1 纳入本波的地图行

| 地图功能（原文） | 落点 | 挂载 |
|------------------|------|------|
| 登录失败次数锁定 / 冷却 | auth | **基线常开** |
| 首次登录强制改初始密码 | auth | **基线常开**（种子可 `must_change_password=1`） |
| 管理员重置用户密码 | org_users | **基线常开**（已有 API；本波叠强制改密） |
| 密码定期强制更换提示 | auth | **基线常开**（yml 天数；0=关） |
| 会话超时自动退出提示 | auth | **基线常开** |
| 「记住登录」延长会话 | auth | **基线常开** |
| 注册密码强度规则提示 | auth | **基线常开** |
| 密保问题找回密码 | auth | **基线常开**（优先于邮箱找回） |
| 忘记密码 / 邮箱或手机找回 | auth | **本波用密保闭环顶**；地图行迁已实现时备注「密保顶；≠真 SMTP」 |
| 演示账号一键填登录 | FE | **基线常开**（文案「试用账号」） |

### 5.2 SQL 列（`sys_user` · 常开注入）

| 列 | 类型 | 用途 |
|----|------|------|
| `failed_login_count` | INT NOT NULL DEFAULT 0 | 连续失败次数 |
| `lock_until` | DATETIME NULL | 冷却截止；未过期则拒登 |
| `must_change_password` | TINYINT NOT NULL DEFAULT 0 | 1=登录后只许改密 |
| `password_changed_at` | DATETIME NULL | 上次成功改密时间；定期换密基准 |
| `security_question` | VARCHAR(128) NULL | 密保问题明文（题目可展示） |
| `security_answer_hash` | VARCHAR(128) NULL | 密保答案哈希（与登录密码同套 `PasswordHashes`） |

注入真源：`auth_crosscut.ensure_*` → `fragments` / `shared_columns` 的 `sys_user` 分支。  
三套 Store 读列须容缺（旧库无列时不炸；bake 新包必有列）。

### 5.3 参数落点（禁止成排 `thesis.auth-*` yml）

对齐 [`param-placement`](../.cursor/rules/param-placement.mdc)：**阈值 / 非单据规则 → `AppPolicy`**；**不得**为 XA-01 往 `KEEP_YML_KEYS` 堆一串工厂腔 `auth-*`。

| AppPolicy 常量 | 默认 | 含义 |
|----------------|------|------|
| `AUTH_LOCK_MAX_ATTEMPTS` | `5` | 连续失败达此次数写入冷却 |
| `AUTH_LOCK_MINUTES` | `15` | 冷却分钟数 |
| `AUTH_PASSWORD_MAX_DAYS` | `0` | 密码最长天数；`0`=不启定期换密 |
| `AUTH_REMEMBER_DAYS` | `7` | 勾选「记住登录」时 session 延长天数 |
| `AUTH_PASSWORD_MIN_LENGTH` | `6` | 强度：最短长度 |
| `AUTH_SESSION_IDLE_MINUTES` | `30` | 前端闲置提示参考 |

真源：`runtime_policy.FIELDS`（numeric 组）+ 三骨架 `AppPolicy.java` 与 bake `write_policy` 对账；binder 用常量，**禁止** `@Value("${thesis.auth-…}")`。

仅会话容器尺（非业务阈值）留 Spring 原生，不进 `thesis:`：

| 键 | 落点 |
|----|------|
| `server.servlet.session.timeout` | 骨架/bake `application.yml`；与 `AUTH_SESSION_IDLE_MINUTES` **同量级**（如 `30m`） |

既有 KEEP（`password-hash` / `register-role` 等）**不动**；本波不新增 KEEP 键。

### 5.4 Store 行为（`UserStore` ×3）

| 方法 / 点 | 行为 |
|-----------|------|
| `Profile` 扩展字段 | 暴露 `mustChangePassword`、`passwordChangedAt`、`hasSecurityQuestion`（布尔，不回答案） |
| 登录前 | 若 `lock_until` > now → 抛锁定错（专用码，见下） |
| `authenticate` 失败 | `failed_login_count++`；达阈值设 `lock_until`、计数可清或保留按实现二选一并写测钉死 |
| `authenticate` 成功 | 清 `failed_login_count`、`lock_until`；返回 profile 含强制改密态 |
| 定期换密 | 若 `AppPolicy.AUTH_PASSWORD_MAX_DAYS>0` 且 `password_changed_at` 超期 → 视同 `must_change_password=1`（或登录响应单独旗，前端同闸） |
| `adminResetPassword` | 写新密后 **`must_change_password=1`**，`password_changed_at` 可置空或保留（测钉：重置后必进强制改密） |
| 自助/强制改密成功 | `must_change_password=0`，`password_changed_at=now`，失败计数清零 |
| 密保 | `setSecurityQuestion`（登录态）；`verifySecurityAnswer` + `resetPasswordBySecurity`（匿名，需用户名+答案+新密+验证码） |
| 注册 | 可选一并写密保；密码走强度校验 |
| 种子 | 至少一个业务种子账号可 `must_change_password=1`（答辩「首次改密」）；密保种子题可空，由注册/资料补 |

### 5.5 API（`AuthController` / `ProfileController` / `UsersAdminController`）

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/auth/login` | body 增 `remember`；成功 data 含 `mustChangePassword`；锁定返回专用码 |
| POST | `/api/auth/logout` | `session.invalidate()`；FE 退出必调 |
| POST | `/api/auth/register` | 强度校验；可选 `securityQuestion` / `securityAnswer` |
| GET | `/api/auth/me` | 含 `mustChangePassword`、`hasSecurityQuestion` |
| GET | `/api/auth/security-question?username=` | 匿名：返回题目（无用户/无密保时模糊文案，防枚举可统一「若账号存在将显示密保」或固定空题——**测钉一种**） |
| POST | `/api/auth/reset-by-security` | 验证码 + 用户名 + 答案 + 新密码；成功可要求重新登录 |
| POST | 既有改密 | 强制改密态下也允许；成功清闸 |
| POST | 既有 admin reset | 行为见上（置闸） |

**ErrorCode（建议）**：

| 码 | 场景 |
|----|------|
| 既有 `40100` | 未登录 |
| 既有 `40101` | 验证码错 |
| 既有 `40102` | 账号停用 |
| **新增** `40103` | 登录锁定冷却中（message 含剩余分钟，学生口语） |
| **新增** `40010` 或复用 BAD_REQUEST | 密码强度不足 / 密保错误 |

### 5.6 前端

| 文件 | 改动 |
|------|------|
| `views/Login.vue` | 记住登录勾选；「试用账号」一键填（读种子用户名，密码与 README 种子一致处可填）；锁定/强度错误展示；链到忘记密码 |
| `views/Register.vue` | 密码强度即时提示（与后端同规则）；可选密保题+答案 |
| `views/ForgotPassword.vue`（新） | 用户名 → 拉密保题 → 答案+新密+验证码 → 提交 |
| `views/ForceChangePassword.vue`（新） | 仅新密+确认；成功后进原 redirect 或首页 |
| `router/index.js` | 注册上述路由；全局守卫：`mustChangePassword` 时除改密/登出外一律重定向强制改密页 |
| `utils/session.js` | `mustChangePassword` 本地旗；闲置计时读 `AUTH_SESSION_IDLE_MINUTES`（`appDelivered` 或只读 public-config，**不**读 thesis yml）；超时 `kickToLogin` + 文案「登录已超时，请重新登录」；logout 调 `POST /api/auth/logout` |
| `api/http.js` | 识别 `40103` 不误当停用；改密闸与 401 协同 |
| `views/Profile.vue` | 设置/修改密保；改密成功清闸 |
| `views/admin/UsersAdmin.vue` | 重置密码成功提示「对方下次登录需修改密码」（学生口语） |

**试用账号**：按钮文案禁止「演示」；可用 `labels.trialLoginFill` 或写死「填入试用账号」。

**配置暴露**：前端需要的闲置分钟 / 记住天数 / 强度规则，经现有 `appDelivered` 或轻量 `GET /api/auth/public-config`（只读阈值，无敏感）。优先 delivered/bake 注入，少开端点。

### 5.7 labels / 文案键（学生可见）

须进 schema labels 且被 FE 真读（门禁）：

| 键 | 用途（示例口语） |
|----|------------------|
| `passwordStrengthHint` | 密码至少 N 位，建议包含字母和数字 |
| `accountLockedHint` | 尝试次数过多，请稍后再登录 |
| `mustChangePasswordHint` | 请先修改密码后再使用系统 |
| `forgotPasswordLink` | 忘记密码 |
| `rememberLoginLabel` | 记住登录 |
| `trialLoginFillLabel` | 填入试用账号 |
| `sessionIdleHint` | 登录已超时，请重新登录 |
| `securityQuestionLabel` | 密保问题 |
| `securityAnswerLabel` | 密保答案 |

### 5.8 材料八张

本波增登录/改密/找回能力：用例图 / 用例描述 / 测试用例 / 序列（登录失败锁定）若从菜单·角色·实体推导有增量则同批看；无新菜单则 modules 可能无。汇报写明受影响张与「无」。

### 5.9 特征测清单（`test_auth_crosscut_features.py`）

| 用例 | 断言要点 |
|------|----------|
| 列注入 | 任意 DOM bake SQL 的 `sys_user` 含 5.2 列 |
| 锁定 | 连续失败 ≥ max → 再登 40103；冷却后可登（可 mock 时间或把 minutes 测里调小） |
| 强制改密 | admin reset 后 login data 旗为真；改密后假 |
| 定期换密 | max-days>0 且 `password_changed_at` 过旧 → 同强制闸（可用 SQL 直写测） |
| 密保重置 | 设密保 → reset-by-security 成功改密 → 旧密不可登 |
| 强度 | 过短密码 register/改密拒 |
| AppPolicy | 新常量在 `runtime_policy.FIELDS`；三骨架 `AppPolicy.java` 与 render 对账；binder 无 `thesis.auth-*` |
| 文案 | 关键 labels 被 baseline FE 源码引用（或走 map skeleton gate） |

### 5.10 XA-01 勾选（实现后填）

| 项 | 状态 |
|----|------|
| XA-00 脚手架 | 已齐 |
| 四件套 + 三骨架 | 已齐 |
| 地图 §0 本波行迁状态 | 已齐 |
| 特征测绿 | 已齐 |
| labels 门禁（若写入） | 已齐 |

---

## 6. XA-02 会话与资料加深（实现要点）

### 6.1 纳入本波的地图行

| 地图功能（原文） | 落点 | 挂载 |
|------------------|------|------|
| 在线用户列表与强制下线 | auth 会话 | **基线常开** |
| 同账号多端会话列表互踢细控 | auth | **基线常开** |
| 个人中心改手机号/邮箱（需验证码） | auth + profile | **基线常开**（图形验证码；≠真短信） |
| 登录设备/最近登录记录 | auth | **基线常开** |
| 账号异地登录提醒 | auth | **基线常开**（对照登录记录 + 站内信） |
| 邮箱验证激活 | auth | **基线常开**（站内码；≠真 SMTP） |
| 账号注销/停用自助申请 | auth | **基线常开** |
| 注册邀请码 | auth | **开题扫到才挂**（菜单/强制注册/种子）；未写不挂菜单、不强制 |
| 用户协议 / 隐私政策勾选注册 | auth | **基线常开** |
| 注册手机号/学号唯一校验提示 | auth | **基线常开** |
| 账号绑定学工号唯一强校验提示齐 | auth | **基线常开** |
| 手机号格式统一校验契约 | auth + profile | **基线常开** |
| 个人中心实名认证勾选（非公安） | profile | **基线常开** |
| 登录页验证码一键刷新无障碍文案 | captcha | **基线常开** |
| 注册图形验证码失败次数提示 | captcha | **基线常开** |
| 用户启用停用 + 强制下线提示 | org_users | 启停已有；本波叠会话踢下线 |

**不交本波**：验证码行为式（滑块/点选）— 地图行留待补，图形先顶。

### 6.2 SQL（`sys_user` 列 + 四表 · 常开注入）

| 对象 | 说明 |
|------|------|
| `email_activated` / `activation_code` / `real_name_acked` | `sys_user` 新列 |
| `sys_auth_session` | 会话登记；踢下线 / 多端互踢 |
| `sys_login_log` | 最近登录只读 |
| `sys_invite_code` | 注册邀请码 |
| `sys_account_cancel` | 注销申请轻单 |

真源：`auth_crosscut.ensure_auth_crosscut_sql`。种子：≥2 邀请码；试用账号 `email_activated=1`。

### 6.3 AppPolicy

| 常量 | 默认 | 含义 |
|------|------|------|
| `AUTH_MAX_SESSIONS` | `5` | 同账号有效会话上限 |
| `AUTH_REQUIRE_INVITE` | `0` | 注册默认不强制邀请码（开题写到再开） |
| `AUTH_REQUIRE_EMAIL_ACTIVATE` | `1` | 未激活闸（对齐强制改密 UX） |

### 6.4 落点速查

| 层 | 路径 |
|----|------|
| bake | `features/auth_crosscut.py` · `runtime_policy.py` |
| Store | `AuthSessionStore` / `InviteCodeStore` / `AccountCancelStore` / `LoginLogStore` + `UserStore`×3 |
| API | `AuthController` · `ProfileController` · 管理端会话/邀请码/注销审 |
| FE | `OnlineSessionsAdmin` · `InviteCodesAdmin` · `ActivateAccount` · `Agreement`/`Privacy` · Register/Login/Profile/UsersAdmin |
| 测 | `test_auth_crosscut_features.py` · `test_menu_routes.py` · map skeleton gate |

### 6.5 XA-02 勾选（实现后填）

| 项 | 状态 |
|----|------|
| 四件套 + 三骨架 | 已齐 |
| 地图 §0 本波行迁状态 | 已齐 |
| 特征测绿 | 已齐 |
| labels 门禁 | 已齐 |
| 行为式验证码 | **不交**（留待补；图形先顶） |

---


## 7. X-MSG 波次总表

> **状态列**：`待写` → `实现中` → `已齐`（须过 §0.4 + 地图迁行）。

| 序 | ID | 主题 | 条数约 | 状态 |
|----|-----|------|--------|------|
| 0 | **XM-00** | 脚手架：`msg_crosscut` feature + SQL 注入钩子 + 特征测空架 + 本册波次 | — | **已齐** |
| 1 | **XM-01** | 站内信收件箱加深：已读闭环迁齐 / 软删 / 系统·业务筛选 Tab | 3 | **已齐** |
| 2 | **XM-02** | 公告加深：过期下架 / 强制弹窗 / 浅富文本 / 广告位 Banner | ~4 | **已齐** |

**推荐编码顺序**：XM-00 → XM-01 →（收口迁行）→ XM-02。

### 7.1 基线现状（写前对照）

| 能力 | 真源 | 本簇处置 |
|------|------|----------|
| `read_at` + markRead / markAllRead / unread-count | `MessageStore`×3 · `MessageController` · `Messages.vue` · `MessageBell.vue` | **XM-01 迁已齐**（闭环已齐，地图行补迁） |
| 公告 `pinned` | `NoticeStore` 运行时补列 + `NoticesAdmin` | 已有；**不重做**；过期/强制弹窗属 XM-02 |
| `message_template` 扫词岛 | E-06 / `MessageTemplatesAdmin` | 独立 cap；本簇不改 |
| 站内信软删 / 类型 Tab | — | **XM-01 补** |
| 公告过期 / 强制公告 / 富文本 / Banner | — | **XM-02** |

### 7.2 XM-00 脚手架（实现要点）

| 勾选 | 项 |
|------|-----|
| ☑ | 新建 `backend/app/bake/features/msg_crosscut.py`：`ensure_msg_crosscut_sql`、labels 种子、模块头钉硬约束 |
| ☑ | `engine_sql.py` **常开**调用注入——通识不扫词 |
| ☑ | Hub：`HUB_BYPASS_MODULES` + `docs/capabilities.md` 例外表一行（**非** thicken） |
| ☑ | `domain_schema` 调 `apply_msg_crosscut_to_spec` |
| ☑ | `backend/tests/test_msg_crosscut_features.py`：列注入 / labels 门禁 |

### 7.3 XM-01 站内信收件箱（实现要点）

#### 纳入本波的地图行

| 地图功能（原文） | 落点 | 挂载 |
|------------------|------|------|
| 站内信已读/未读/全部已读 | sys_message | **基线常开**（迁已齐；铃铛+列表+API 已闭环） |
| 站内信删除（软删） | sys_message | **基线常开** |
| 消息按类型筛选（系统/业务） | sys_message | **基线常开** |

**不交本波**：公告过期/强制弹窗/富文本/广告位 → XM-02；内容/档案软删回收站 → X-LIST。

#### SQL

| 对象 | 说明 |
|------|------|
| `sys_message.deleted_at` | 软删；列表/未读计数排除 `deleted_at IS NOT NULL`；旧库运行时 ALTER |

真源：`msg_crosscut.ensure_msg_crosscut_sql`。

#### 类型口径（禁止两套）

| Tab | 条件 |
|-----|------|
| 全部 | `deleted_at IS NULL` |
| 系统 | `IFNULL(ref_type,'')=''` 或 `ref_type IN ('system','auth')` |
| 业务 | 其余非空 `ref_type` |

#### 落点速查

| 层 | 路径 |
|----|------|
| bake | `features/msg_crosscut.py` |
| Store×3 | `MessageStore` baseline + mybatis/jpa；MyBatis `MessageMapper`(+xml) |
| API | `MessageController`：`kind` 查询；`DELETE /{id}` 软删 |
| FE | `Messages.vue` Tab + 删除；`MessageBell` 未读仍排除已删 |
| 测 | `test_msg_crosscut_features.py` |

#### labels

| 键 | 默认文案 |
|----|----------|
| `messageKindAll` | 全部 |
| `messageKindSystem` | 系统 |
| `messageKindBiz` | 业务 |
| `messageDeleteLabel` | 删除 |
| `messageDeletedHint` | 已删除 |

#### XM-01 勾选（实现后填）

| 项 | 状态 |
|----|------|
| XM-00 脚手架 | 已齐 |
| 四件套 + 三骨架 | 已齐 |
| 地图 §0 本波三行迁状态 | 已齐 |
| 特征测绿 | 已齐 |

### 7.4 XM-02 公告加深（实现要点）

#### 纳入本波的地图行

| 地图功能（原文） | 落点 | 挂载 |
|------------------|------|------|
| 公告置顶 / 过期自动下架 | content | **基线常开**（置顶已有；本波叠 `expire_at`） |
| 强制公告弹窗（未读不可关） | content | **基线常开** |
| 公告/详情富文本编辑 | content | **基线常开**（浅 HTML，非专业编辑器） |
| 广告位 Banner 多槽 | content | **基线常开** |

#### SQL

| 对象 | 说明 |
|------|------|
| `sys_notice.expire_at` | 过期后门户列表/详情不可见 |
| `sys_notice.force_ack` | 强制弹窗标记 |
| `sys_notice.content_fmt` | `text`/`html` |
| `sys_notice_ack` | 用户确认强制公告 |
| `sys_banner` | 多槽广告位（slot/title/image_url/link_url/sort/enabled） |

真源：`msg_crosscut.ensure_msg_crosscut_sql`。

#### 落点速查

| 层 | 路径 |
|----|------|
| bake | `features/msg_crosscut.py` |
| Store×3 | `NoticeStore`；新建 `BannerStore`（baseline+jpa；mybatis 走 jdbc 同语义） |
| API | `NoticeController` force-pending/ack；`BannerController` |
| FE | `NoticesAdmin` · `NoticeDetail` · `ForceNoticeGate` · `BannersAdmin` · `PortalCarousel` |
| 测 | `test_msg_crosscut_features.py` 扩 XM-02 |

#### XM-02 勾选

| 项 | 状态 |
|----|------|
| 四件套 + 三骨架 | **已齐** |
| 地图 §0 本波四行迁状态 | **已齐** |
| 特征测绿 | **已齐** |

---

## 8. X-DASH 波次总表

> **状态列**：`待写` → `实现中` → `已齐`（须过 §0.4 + 地图迁行）。

| 序 | ID | 主题 | 条数约 | 状态 |
|----|-----|------|--------|------|
| 0 | **XD-00** | 脚手架：`workbench_crosscut` + labels/shortcuts 种子 + 特征测 | — | **随 XD-01** |
| 1 | **XD-01** | 待办角标与跳转 / 按角色过滤 / 常用快捷入口 | 3 | **已齐** |
| 2 | **XD-02** | 简易 PV / 我的单据聚合 / 定时任务只读台 | 3 | **已齐** |

**不交本簇**：全局关键词搜索 → X-LIST（档案列表已有 keyword；顶栏另案）。

### 8.1 XD-01 实现要点

#### 纳入本波的地图行

| 地图功能（原文） | 落点 | 挂载 |
|------------------|------|------|
| 工作台待办数字角标与跳转 | 基线工作台 | **基线常开** |
| 工作台待办按角色过滤 | 基线工作台 | **基线常开**（订单店主过滤已有；工单处理中按 assignee） |
| 工作台常用功能快捷入口可配 | 基线工作台 | **基线常开**（schema.workbench.shortcuts 浅链） |

#### 落点速查

| 层 | 路径 |
|----|------|
| bake | `features/workbench_crosscut.py` |
| API | `TicketDashboardController`：`/counts`；dashboard 传 scope |
| Ops×3 | `TicketDashOps.dashboard(readerRole, scopeUid, superAdmin)` |
| FE | `AdminLayout` 角标；`TicketDashboard` 卡片跳转 + 快捷入口 |
| 测 | `test_workbench_crosscut_features.py` |

#### XD-01 勾选

| 项 | 状态 |
|----|------|
| 四件套（无新表；counts + FE） | **已齐** |
| 地图 §0 本波三行迁状态 | **已齐** |
| 特征测绿 | **已齐** |

### 8.2 XD-02 实现要点

#### 纳入本波的地图行

| 地图功能（原文） | 落点 | 挂载 |
|------------------|------|------|
| 简易访问量统计（PV，工作台） | 基线工作台 | **基线常开**（`sys_site_stat` 按日） |
| 个人中心「我的单据」聚合入口 | 基线 | **基线常开**（Profile 链 `workbench.myDocs`） |
| 定时任务只读台（关单/过期券等） | 基线调度 | **基线常开**（说明台；≠ XXL-JOB） |

#### 落点速查

| 层 | 路径 |
|----|------|
| bake | `workbench_crosscut`：SQL + labels + myDocs + schedule_jobs 菜单 |
| Store×3 | `SiteStatStore` |
| API | `SiteStatController` · `ScheduleJobsController`；dashboard 叠 PV |
| FE | `PortalLayout` bump · `TicketDashboard` 卡片 · `Profile` · `ScheduleJobsAdmin` |
| 测 | `test_workbench_crosscut_features.py` |

#### XD-02 勾选

| 项 | 状态 |
|----|------|
| 四件套 + 三骨架 | **已齐** |
| 地图 §0 本波三行迁状态 | **已齐** |
| 特征测绿 | **已齐** |

---

## 9. 其余簇（占位 · 开簇时扩明细）

| 簇 | 开簇时从地图 §0 拉取的关键词 |
|----|------------------------------|
| X-ORG | 组织树、RBAC 矩阵、**字典**启停/排序、sys_config、Logo/登录页背景、脱敏、数据权限、用户标签、批量启停 |
| X-LIST | 高级筛选、批量通过驳回删除、Excel 导入、导出字段勾选、软删回收站、素材库、一级佣金台账、**全局关键词顶栏** |
| X-UX | Toast 契约、打印样式、灯箱、帮助页、离开未保存、单号复制、图片压缩、附件限制、防重复提交、页脚版本、资料完整度 |

---

## 10. 编码落点速查（历史）

| 层 | 路径 |
|----|------|
| bake feature | `auth_crosscut` · `msg_crosscut` · `workbench_crosscut` |
| 测 | `test_auth_crosscut_features` · `test_msg_crosscut_features` · `test_workbench_crosscut_features` |
| 本册 | §5～§8 |

---

## 11. 修订

| 日期 | 说明 |
|------|------|
| 2026-10-11 | 初版：后加厚三轨立册；分簇 X-AUTH～X-UX；首簇 X-AUTH 待开；禁止再开域组 thicken |
| 2026-10-11 | **X-AUTH 实现要点落册**：波次 XA-00/01/02；XA-01 列/Store/API/FE/labels/测/迁行全钉；字典/角标分属 X-ORG/X-DASH |
| 2026-10-12 | **参数落点纠偏**：XA-01 阈值改 `AppPolicy`（禁成排 `thesis.auth-*` / 不扩 `KEEP_YML_KEYS`）；仅 `server.servlet.session.timeout` 留原生 yml |
| 2026-10-12 | **XA-00/XA-01 收口**：列注入 + 三套 UserStore + Auth API/FE + 特征测；地图 §0 本波行迁已实现；下轮 XA-02 |
| 2026-10-12 | **XA-02 收口**；开簇 **X-MSG**：波次 XM-00/01/02；本轮 XM-00+XM-01（软删/类型筛选/已读迁齐） |
| 2026-10-12 | **XM-02 收口**；**X-DASH XD-01 已齐**：待办角标/角色过滤/快捷入口（角标归 X-DASH，非 XM-03） |
| 2026-10-12 | **X-DASH XD-02 已齐**：简易 PV / 我的单据 / 定时任务只读台；全局搜索留给 X-LIST |
