# 全域 UI 诊断表（活表）

> **本文只负责一件事**：**诊断结果台账**——对 `DOMAIN_CAPABILITIES` **68 域**（+ 共享基线行）勾选 `L`/`C` 过没过、红灯记在哪。  
> **不负责**：一眼病规则/草图/门禁分期（[`ui-layout-prebake-gate.md`](./ui-layout-prebake-gate.md)）；控件选型与下拉纪律正文（[`form-controls.md`](./form-controls.md)）；观感精美进度；能力/地图待补。  
> **一句话**：本册只记 **诊没诊、过没过**；怎么才算过 → 打开对应细则册，**禁止在本册展开细则正文**。  
> **状态**：台账已立 · 全域未诊。  
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

---

## 1. 总览（随勾选更新）

| 项 | 值 |
|----|-----|
| 域行数 | **68**（须 = `len(DOMAIN_CAPABILITIES)`） |
| 共享诊断行 | §2（基线共用面） |
| `L`/`C` 双 OK 域数 | **0**（开表） |
| `RED` 域数 | **0**（开表；有则改本行） |
| `—` 未诊域数 | **68** |
| 机器闸 | 未开（见布局闸 D1–D4、控件册 §5）；未批准勿改代码 |

---

## 2. 共享基线诊断（先诊 · 影响全域）

> 这些面不按域重复 68 次；**先诊共享**。状态默认 `—`。

| `row_id` | 面 | 典型路径 | `L` | `C` | 红灯 | 末次 |
|----------|-----|----------|----|----|------|------|
| `S:portal_chrome` | 门户顶栏/壳 | `layouts/PortalLayout.vue` | — | — | | |
| `S:admin_chrome` | 管理端壳 | `layouts/AdminLayout.vue` | — | — | | |
| `S:work_chrome` | 员工壳 | `layouts/WorkLayout.vue` | — | — | | |
| `S:auth` | 登录/注册 | `AuthShell` / Login / Register | — | — | | |
| `S:archive_browse` | 档案列表（多 surface 共用） | `views/user/ArchiveBrowse*` | — | — | | |
| `S:archive_detail` | 档案详情 | `views/user/ArchiveItemDetail.vue` | — | — | | |
| `S:tickets_admin` | 管理端单据 | `views/admin/TicketsAdmin.vue` | — | — | | |
| `S:my_tickets` | 用户端单据 | `views/user/MyTickets.vue` | — | — | | |
| `S:archive_admin` | 管理端档案 | `views/admin/ArchiveAdmin.vue` | — | — | | |
| `S:components` | 共享组件包 | `components/**`（按布局闸台账） | — | — | | |
| `S:field_control` | 档案字段控件 | `ArchiveFieldControl` + widget 映射 | — | — | | |

共享行未双 `OK` 前，§3 域行不得标「全包已诊过」（可诊域专属面，但合计仍受共享拖累，备注写明）。

---

## 3. 全域诊断表（68）

组名与 surface 与观感批次对齐，便于对照；**本表不验收精美**。

| `DOM-*` | 组 | surface（默认识别） | `L` | `C` | 红灯 | 末次 |
|---------|-----|---------------------|----|----|------|------|
| `DOM-LIBRARY` | borrow | bookshelf | — | — | | |
| `DOM-EQUIP` | borrow | stockrow | — | — | | |
| `DOM-ASSET` | borrow | stockrow | — | — | | |
| `DOM-PARCEL` | borrow | parcelshelf | — | — | | |
| `DOM-BED` | borrow | bedblocks | — | — | | |
| `DOM-SHOP` | trade | shelfgrid | — | — | | |
| `DOM-FOOD` | trade | menuboard | — | — | | |
| `DOM-CINEMA` | trade | showtime | — | — | | |
| `DOM-HOSPITAL` | reserve | slotstrip | — | — | | |
| `DOM-MEETING` | reserve | slotstrip | — | — | | |
| `DOM-SALON` | reserve | slotstrip | — | — | | |
| `DOM-INSTRUMENT` | reserve | slotstrip | — | — | | |
| `DOM-HOTEL` | reserve | roomstate | — | — | | |
| `DOM-CARRENT` | reserve | vehiclecard | — | — | | |
| `DOM-PARKING` | reserve | vehiclecard | — | — | | |
| `DOM-BLOG` | content | folio | — | — | | |
| `DOM-FORUM` | content | folio | — | — | | |
| `DOM-MEDIA` | content | coverwall | — | — | | |
| `DOM-MUSIC` | content | coverwall | — | — | | |
| `DOM-DOCLIB` | content | ledger | — | — | | |
| `DOM-ACTIVITY` | apply | eventposter | — | — | | |
| `DOM-COURSE` | apply | coursetable | — | — | | |
| `DOM-LOST` | apply | noticeboard | — | — | | |
| `DOM-TOUR` | apply | tourcard | — | — | | |
| `DOM-CRM` | follow | pipeline | — | — | | |
| `DOM-LISTING` | follow | listing | — | — | | |
| `DOM-ATTEND` | follow | dossier | — | — | | |
| `DOM-EVENT` | follow | dossier | — | — | | |
| `DOM-FUND` | follow | dossier | — | — | | |
| `DOM-GRADE` | follow | dossier | — | — | | |
| `DOM-INTERN` | follow | dossier | — | — | | |
| `DOM-RECRUIT` | follow | dossier | — | — | | |
| `DOM-DATING` | interact | profilegrid | — | — | | |
| `DOM-MUTUAL-TEAM` | interact | mutualpick | — | — | | |
| `DOM-MUTUAL-TOPIC` | interact | mutualpick | — | — | | |
| `DOM-MUTUAL-TUTOR` | interact | mutualpick | — | — | | |
| `DOM-CARPOOL` | interact | triprow | — | — | | |
| `DOM-TIMEBANK` | interact | triprow | — | — | | |
| `DOM-EXAM` | interact | —（专用页） | — | — | | |
| `DOM-SURVEY` | interact | —（专用页） | — | — | | |
| `DOM-VOTE` | interact | —（专用页） | — | — | | |
| `DOM-DORM` | ticket | ticketfeed | — | — | | |
| `DOM-IT` | ticket | ticketfeed | — | — | | |
| `DOM-PROPERTY` | ticket | ticketfeed | — | — | | |
| `DOM-ACAD` | approve | typelist | — | — | | |
| `DOM-AWARD` | approve | typelist | — | — | | |
| `DOM-CARPASS` | approve | typelist | — | — | | |
| `DOM-CERT` | approve | typelist | — | — | | |
| `DOM-CHECKIN` | approve | typelist | — | — | | |
| `DOM-CLUB` | approve | typelist | — | — | | |
| `DOM-CONTRACT` | approve | typelist | — | — | | |
| `DOM-CREDIT` | approve | typelist | — | — | | |
| `DOM-ETHIC` | approve | typelist | — | — | | |
| `DOM-EVAL` | approve | typelist | — | — | | |
| `DOM-EXPENSE` | approve | typelist | — | — | | |
| `DOM-FITOUT` | approve | typelist | — | — | | |
| `DOM-FLEET` | approve | typelist | — | — | | |
| `DOM-LABOR` | approve | typelist | — | — | | |
| `DOM-LABSAFE` | approve | typelist | — | — | | |
| `DOM-MORAL` | approve | typelist | — | — | | |
| `DOM-PARTY` | approve | typelist | — | — | | |
| `DOM-PROCURE` | approve | stockrow | — | — | | |
| `DOM-PROJ` | approve | typelist | — | — | | |
| `DOM-PROMO` | approve | typelist | — | — | | |
| `DOM-SEAL` | approve | typelist | — | — | | |
| `DOM-TRIP` | approve | typelist | — | — | | |
| `DOM-VISITOR` | approve | typelist | — | — | | |
| `DOM-GENERIC` | fallback | —（吃公共壳） | — | — | | |

**行数核对**：上表 **68**。`DOMAIN_CAPABILITIES` 增删域时 **同批改本表**，否则本诊断表红。

---

## 4. 回写约定（未批准勿动代码）

| 来源 | 回写本表 |
|------|----------|
| 人工按细则册诊完一面 | 改对应行 `L`/`C` + 末次 + 红灯 |
| 布局闸机器测（D1–D4，若已开） | 回写 `L` |
| 控件册门禁（若已开） | 回写 `C` |

建议诊序：先 §2 共享 → 再 §3 按组；**检查步骤只读细则册，结果只写本表**。

---

## 5. 修订

| 日期 | 说明 |
|------|------|
| 2026-10-22 | 立册：S/D 两层；68 域全 `—`；代码未开 |
| 2026-10-22 | **一文一事**：删复述检查单；只保留记账口径；细则外链布局闸/控件册 |
