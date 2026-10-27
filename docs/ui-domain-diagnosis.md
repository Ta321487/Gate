# 全域 UI 诊断表（活表）

> **本文只负责一件事**：**诊断结果台账**——对 `DOMAIN_CAPABILITIES` **68 域**（+ 共享基线行）勾选 `L`/`C` 过没过、红灯记在哪。  
> **不负责**：一眼病规则/草图/门禁分期（[`ui-layout-prebake-gate.md`](./ui-layout-prebake-gate.md)）；控件选型与下拉纪律正文（[`form-controls.md`](./form-controls.md)）；观感精美进度；能力/地图待补。  
> **一句话**：本册只记 **诊没诊、过没过**；怎么才算过 → 打开对应细则册，**禁止在本册展开细则正文**。  
> **状态**：首诊已开 · **§2 共享双 OK** · **§3 68 域双 OK**。  
> **域名单真源**：`backend/app/bake/domains.py` → `DOMAIN_CAPABILITIES` / `DOMAIN_GROUPS`（须 68 行）。  
> **索引**：[README.md](./README.md) · [`../HANDOFF.md`](../HANDOFF.md)。

---

## 0. 怎么用（只谈记账，不谈细则）

### 0.1 两层行

| 层 | 记什么 | 记分 |
|----|--------|------|
| **S 共享基线** | 各域共用的壳/列表/单据/组件等 | §2；共享一红 → 相关域备注「共享红：…」，不得假装单域已过 |
| **D 域行** | 该域默认识别面 / 专用页 | §3；**68 行必须齐**，漏域 = 本表未尽责 |

### 0.2 两列（细则外链，本表不复述）

| 列 | 含义 | 过的标准写在 |
|----|------|----------------|
| `L` | 布局一眼病 | [`ui-layout-prebake-gate.md`](./ui-layout-prebake-gate.md) §0.0a / §0.0b |
| `C` | 可交互控件 | [`form-controls.md`](./form-controls.md) 全文 |

勾选前打开上表链接执行检查；**不要**把缺陷分类或控件表抄进本册。

### 0.3 格值

| 记号 | 含义 |
|------|------|
| `—` | 未诊 |
| `OK` | 已诊且过（须有日期 + 证据：截图路径或预览备注） |
| `RED` | 已诊有红；「红灯」列写短码（见下） |
| `N/A` | 本域无该面（须写原因；禁止偷懒） |

`L` 与 `C` 皆 `OK` 才算该行诊断过；任一 `RED` / `—` → 未过。

### 0.4 红灯短码（只记账格式）

逗号分隔，前缀标轴，例如：

`L:crushed,overflow` · `C:select_handfill,date_as_input` · `S:TicketsAdmin.toolbar`

`L:` 后码名以布局闸 `defect_class` 为准；`C:` 后码名以控件册违例为准（本表不维护码表正文）。

修好共享面 → 清 §2 并扫域行「共享红」；修好单域面 → 只改该域行。

### 0.5 证据口径

| 轴 | 证据 | 结论口径 |
|----|------|----------|
| `L` | `layout_gate_snapshot`：对账/结构 **unexpected=0**；`BASELINE_KNOWN_*` 空 | 无 finding → `OK`；有 → `RED` |
| `C` | `form_controls_gate_snapshot`：**finding=0**、`BASELINE_KNOWN_CONTROLS` 空 | 基线共用面 `C=OK` |
| 视觉全表 | D4 已齐；全表 Playwright 不挡勾选 | 结构债优先 |

---

## 1. 总览（随勾选更新）

| 项 | 值 |
|----|-----|
| 域行数 | **68**（须 = `len(DOMAIN_CAPABILITIES)`） |
| 共享诊断行 | §2（基线共用面 **13**；全部双 OK） |
| `L`/`C` 双 OK 域数 | **68** |
| `RED` 域数 | **0** |
| `—` 未诊域数 | **0** |
| 机器闸 | 布局 D1–D5 / 控件 C0–C5 已开；`BASELINE_KNOWN_ISSUES` / `BASELINE_KNOWN_CONTRACTS` / `BASELINE_KNOWN_CONTROLS` 均空 |

**消红摘要（2026-10-25）**：管理端操作区加 `flex-wrap`；多段 toolbar 合并/改 `desk-panel`；dialog/drawer 表外包 `table-scroll`；删未挂回孤儿 `EntityDetailLayout`。组附债页（Orders/Overdue/Reservations/GradeScores）同批清。

---

## 2. 共享基线诊断（先诊 · 影响全域）

> 这些面不按域重复 68 次；**先诊共享**。末次 **2026-10-25**（首诊 + 同日消红复验）。

| `row_id` | 面 | 典型路径 | `L` | `C` | 红灯 | 末次 |
|----------|-----|----------|----|----|------|------|
| `S:portal_chrome` | 门户顶栏/壳 | `layouts/PortalLayout.vue` | OK | OK | | 2026-10-25 |
| `S:admin_chrome` | 管理端壳 | `layouts/AdminLayout.vue` | OK | OK | | 2026-10-25 |
| `S:work_chrome` | 员工壳 | `layouts/WorkLayout.vue` | OK | OK | | 2026-10-25 |
| `S:auth` | 登录/注册 | `AuthShell` / Login / Register | OK | OK | | 2026-10-25 |
| `S:archive_browse` | 档案列表（多 surface 共用） | `views/user/ArchiveBrowse*` | OK | OK | | 2026-10-25 |
| `S:archive_detail` | 档案详情 | `views/user/ArchiveItemDetail.vue` | OK | OK | | 2026-10-25 |
| `S:tickets_admin` | 管理端单据 | `views/admin/TicketsAdmin.vue` | OK | OK | | 2026-10-25 |
| `S:my_tickets` | 用户端单据 | `views/user/MyTickets.vue` | OK | OK | | 2026-10-25 |
| `S:archive_admin` | 管理端档案 | `views/admin/ArchiveAdmin.vue` | OK | OK | | 2026-10-25 |
| `S:components` | 共享组件包 | `components/**`（按布局闸台账） | OK | OK | | 2026-10-25 |
| `S:field_control` | 档案字段控件 | `ArchiveFieldControl` + widget 映射 | OK | OK | | 2026-10-25 |
| `S:users_admin` | 用户管理（全域挂） | `views/admin/UsersAdmin.vue` | OK | OK | | 2026-10-25 |
| `S:ticket_records` | 单据记录（多域挂） | `views/admin/TicketRecordsAdmin.vue` | OK | OK | | 2026-10-25 |

共享行均双 `OK`；§3 域行可计双 OK（无共享拖累）。

---

## 3. 全域诊断表（68）

组名与 surface 与观感批次对齐，便于对照；**本表不验收精美**。  
末次均为 **2026-10-25**。`L`/`C` 均 OK（布局/控件机器闸 unexpected=0；共享与组附债已消）。

| `DOM-*` | 组 | surface（默认识别） | `L` | `C` | 红灯 | 末次 |
|---------|-----|---------------------|----|----|------|------|
| `DOM-LIBRARY` | borrow | bookshelf | OK | OK | | 2026-10-25 |
| `DOM-EQUIP` | borrow | stockrow | OK | OK | | 2026-10-25 |
| `DOM-ASSET` | borrow | stockrow | OK | OK | | 2026-10-25 |
| `DOM-PARCEL` | borrow | parcelshelf | OK | OK | | 2026-10-25 |
| `DOM-BED` | borrow | bedblocks | OK | OK | | 2026-10-25 |
| `DOM-SHOP` | trade | shelfgrid | OK | OK | | 2026-10-25 |
| `DOM-FOOD` | trade | menuboard | OK | OK | | 2026-10-25 |
| `DOM-CINEMA` | trade | showtime | OK | OK | | 2026-10-25 |
| `DOM-HOSPITAL` | reserve | slotstrip | OK | OK | | 2026-10-25 |
| `DOM-MEETING` | reserve | slotstrip | OK | OK | | 2026-10-25 |
| `DOM-SALON` | reserve | slotstrip | OK | OK | | 2026-10-25 |
| `DOM-INSTRUMENT` | reserve | slotstrip | OK | OK | | 2026-10-25 |
| `DOM-HOTEL` | reserve | roomstate | OK | OK | | 2026-10-25 |
| `DOM-CARRENT` | reserve | vehiclecard | OK | OK | | 2026-10-25 |
| `DOM-PARKING` | reserve | vehiclecard | OK | OK | | 2026-10-25 |
| `DOM-BLOG` | content | folio | OK | OK | | 2026-10-25 |
| `DOM-FORUM` | content | folio | OK | OK | | 2026-10-25 |
| `DOM-MEDIA` | content | coverwall | OK | OK | | 2026-10-25 |
| `DOM-MUSIC` | content | coverwall | OK | OK | | 2026-10-25 |
| `DOM-DOCLIB` | content | ledger | OK | OK | | 2026-10-25 |
| `DOM-ACTIVITY` | apply | eventposter | OK | OK | | 2026-10-25 |
| `DOM-COURSE` | apply | coursetable | OK | OK | | 2026-10-25 |
| `DOM-LOST` | apply | noticeboard | OK | OK | | 2026-10-25 |
| `DOM-TOUR` | apply | tourcard | OK | OK | | 2026-10-25 |
| `DOM-CRM` | follow | pipeline | OK | OK | | 2026-10-25 |
| `DOM-LISTING` | follow | listing | OK | OK | | 2026-10-25 |
| `DOM-ATTEND` | follow | dossier | OK | OK | | 2026-10-25 |
| `DOM-EVENT` | follow | dossier | OK | OK | | 2026-10-25 |
| `DOM-FUND` | follow | dossier | OK | OK | | 2026-10-25 |
| `DOM-GRADE` | follow | dossier | OK | OK | | 2026-10-25 |
| `DOM-INTERN` | follow | dossier | OK | OK | | 2026-10-25 |
| `DOM-RECRUIT` | follow | dossier | OK | OK | | 2026-10-25 |
| `DOM-DATING` | interact | profilegrid | OK | OK | | 2026-10-25 |
| `DOM-MUTUAL-TEAM` | interact | mutualpick | OK | OK | | 2026-10-25 |
| `DOM-MUTUAL-TOPIC` | interact | mutualpick | OK | OK | | 2026-10-25 |
| `DOM-MUTUAL-TUTOR` | interact | mutualpick | OK | OK | | 2026-10-25 |
| `DOM-CARPOOL` | interact | triprow | OK | OK | | 2026-10-25 |
| `DOM-TIMEBANK` | interact | triprow | OK | OK | | 2026-10-25 |
| `DOM-EXAM` | interact | —（专用页） | OK | OK | | 2026-10-25 |
| `DOM-SURVEY` | interact | —（专用页） | OK | OK | | 2026-10-25 |
| `DOM-VOTE` | interact | —（专用页） | OK | OK | | 2026-10-25 |
| `DOM-DORM` | ticket | ticketfeed | OK | OK | | 2026-10-25 |
| `DOM-IT` | ticket | ticketfeed | OK | OK | | 2026-10-25 |
| `DOM-PROPERTY` | ticket | ticketfeed | OK | OK | | 2026-10-25 |
| `DOM-ACAD` | approve | typelist | OK | OK | | 2026-10-25 |
| `DOM-AWARD` | approve | typelist | OK | OK | | 2026-10-25 |
| `DOM-CARPASS` | approve | typelist | OK | OK | | 2026-10-25 |
| `DOM-CERT` | approve | typelist | OK | OK | | 2026-10-25 |
| `DOM-CHECKIN` | approve | typelist | OK | OK | | 2026-10-25 |
| `DOM-CLUB` | approve | typelist | OK | OK | | 2026-10-25 |
| `DOM-CONTRACT` | approve | typelist | OK | OK | | 2026-10-25 |
| `DOM-CREDIT` | approve | typelist | OK | OK | | 2026-10-25 |
| `DOM-ETHIC` | approve | typelist | OK | OK | | 2026-10-25 |
| `DOM-EVAL` | approve | typelist | OK | OK | | 2026-10-25 |
| `DOM-EXPENSE` | approve | typelist | OK | OK | | 2026-10-25 |
| `DOM-FITOUT` | approve | typelist | OK | OK | | 2026-10-25 |
| `DOM-FLEET` | approve | typelist | OK | OK | | 2026-10-25 |
| `DOM-LABOR` | approve | typelist | OK | OK | | 2026-10-25 |
| `DOM-LABSAFE` | approve | typelist | OK | OK | | 2026-10-25 |
| `DOM-MORAL` | approve | typelist | OK | OK | | 2026-10-25 |
| `DOM-PARTY` | approve | typelist | OK | OK | | 2026-10-25 |
| `DOM-PROCURE` | approve | stockrow | OK | OK | | 2026-10-25 |
| `DOM-PROJ` | approve | typelist | OK | OK | | 2026-10-25 |
| `DOM-PROMO` | approve | typelist | OK | OK | | 2026-10-25 |
| `DOM-SEAL` | approve | typelist | OK | OK | | 2026-10-25 |
| `DOM-TRIP` | approve | typelist | OK | OK | | 2026-10-25 |
| `DOM-VISITOR` | approve | typelist | OK | OK | | 2026-10-25 |
| `DOM-GENERIC` | fallback | —（吃公共壳） | OK | OK | | 2026-10-25 |

**行数核对**：上表 **68**。`DOMAIN_CAPABILITIES` 增删域时 **同批改本表**，否则本诊断表红。

---

## 4. 回写约定（未批准勿动代码）

| 来源 | 回写本表 |
|------|----------|
| 人工按细则册诊完一面 | 改对应行 `L`/`C` + 末次 + 红灯 |
| 布局闸机器测（D1–D4，若已开） | 回写 `L` |
| 控件册门禁（若已开） | 回写 `C` |

建议诊序：先 §2 共享 → 再 §3 按组；**检查步骤只读细则册，结果只写本表**。

**本轮收口**：共享 `L` 红 + 组附债已消；台账 68 双 OK。新红再开诊，禁止只擦单包。

---

## 5. 修订

| 日期 | 说明 |
|------|------|
| 2026-10-22 | 立册：S/D 两层；68 域全 `—`；代码未开 |
| 2026-10-22 | **一文一事**：删复述检查单；只保留记账口径；细则外链布局闸/控件册 |
| 2026-10-25 | **首诊开账**：§2 先诊（13 行；5 行 `L` RED）；§3 68 域 `C=OK`、`L=RED`（共享红）；双 OK 域数 0 |
| 2026-10-25 | **共享 L 消红**：基线管理页结构债清零 + 删 `EntityDetailLayout` 孤儿；`BASELINE_KNOWN_*` 空；§2/§3 全部双 OK（68） |
