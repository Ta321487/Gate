# -*- coding: utf-8 -*-
"""Generate docs/ui-look-thicken-batch.md (68-domain look-thicken ledger)."""
from __future__ import annotations

from pathlib import Path

from app.bake import themes as T
from app.bake.domains import DOMAIN_CAPABILITIES, DOMAIN_GROUPS
from app.bake.shell_face import resolve_card_voice, resolve_shell_colors, top_search_placeholder

LOOK = {
    "trade": "首刀已齐",
    "borrow": "首刀已齐",
    "ticket": "未开",
    "follow": "未开",
    "apply": "首刀已齐",
    "approve": "未开",
    "reserve": "首刀已齐",
    "content": "首刀已齐",
    "interact": "首刀已齐",
    "fallback": "未开",
}
SHELL = "全厂已齐"

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "ui-look-thicken-batch.md"


def surface_of(d: str) -> str:
    for attr in (
        "TRADE_SURFACE_DOMAIN_DEFAULTS",
        "BORROW_SURFACE_DOMAIN_DEFAULTS",
        "RESERVE_SURFACE_DOMAIN_DEFAULTS",
        "CONTENT_SURFACE_DOMAIN_DEFAULTS",
        "APPLY_SURFACE_DOMAIN_DEFAULTS",
        "INTERACT_SURFACE_DOMAIN_DEFAULTS",
        "FOLLOW_SURFACE_DOMAIN_DEFAULTS",
        "REPAIR_SURFACE_DOMAIN_DEFAULTS",
        "APPROVE_SURFACE_DOMAIN_DEFAULTS",
    ):
        m = getattr(T, attr, None)
        if m and d in m:
            return str(m[d])
    return "—"


def main() -> None:
    lines: list[str] = []
    lines += [
        "# UI 观感加厚批次（活表）",
        "",
        "> **本文只负责**：工厂出包「一眼精美 / 不像模板后台」的**观感加厚**进度、全域台账、验收口径与真源落点。",
        "> **不负责**：能力四件套（各组 `*_thicken` / 地图待补）；选型键目录与 ASCII（[`domain-group-ui-styles.md`](./domain-group-ui-styles.md) §2）；沉浸边角（[`immersion-corners.md`](./immersion-corners.md)）。",
        "> **状态**：**进行中** · 公共壳 + 交易/借用/预约/内容/报名/互动 **首刀已齐**；用户列表卡底口径已跨页统一；其余域组 **未开**。",
        "> **硬闸**：键接满、测绿了，观感仍像模板站 —— **仍算未完成**（同选型册 §0.0）。",
        "> **索引**：[README.md](./README.md) · 选型册 [`domain-group-ui-styles.md`](./domain-group-ui-styles.md) · 搁置 [`parked-work.md`](./parked-work.md) · 领域 [`domains.md`](./domains.md)。",
        "",
        "---",
        "",
        "## 0. 硬口径",
        "",
        "| 规则 | 含义 |",
        "|------|------|",
        "| **修工厂** | 只改 `skeletons/baseline` + bake 注入；禁止只擦某一学生 ZIP |",
        "| **对标商业站** | 摆法学公开页，改成毕设可演示版；不抄真支付 / IM / 无限滑 |",
        "| **一轮一组** | 观感加厚按域组推进；公共壳单独一轮（全厂受益） |",
        "| **接线 ≠ 好看** | `{组}_surface_style` / `shellColors` / `cardVoice` 已接线只算管道；本组须过 §0.0 截图闸 |",
        "| **覆盖全域** | `DOMAIN_CAPABILITIES` 68 域均须进台账；组观感齐 = 组内全部 `DOM-*` 默认识别脸达标 |",
        "| **菜单保全** | 换脸不删开题菜单；详情用 `/archive/item/:id`，禁止写死 `/goods/:id` |",
        "",
        "### 0.1 两层交付",
        "",
        "| 层 | 范围 | 验收 |",
        "|----|------|------|",
        "| **A 公共壳** | 顶栏 / 登录注册 / 管理端品牌条 / Element 主色盖死 | 任意域打开都不像默认 Admin |",
        "| **B 组主表面** | 该组 `*_surface_style` + 首页（若有）+ 详情主路径 | 对标摆法可辨；同组多域靠软皮/短签/色分脸 |",
        "",
        "### 0.2 真源落点",
        "",
        "| 件 | 路径 |",
        "|----|------|",
        "| 门户壳 | `skeletons/baseline/frontend/src/layouts/PortalLayout.vue` |",
        "| 管理端壳 | `AdminLayout.vue` + `styles/chrome.css`（`.workbench`） |",
        "| 登录壳 | `components/AuthShell.vue` |",
        "| 主色注入 | `main.js`（`shellColors` → `--portal-*` / `--el-color-primary*`） |",
        "| 68 域脸表 | `backend/app/bake/shell_face.py` |",
        "| 列表构图 CSS | `views/user/ArchiveBrowse.css`（`surface-*`；脚本 `ArchiveBrowse.setup.js`） |",
        "| 商城首页 | `views/user/PortalHome.vue`（`portal_home_style=mall`） |",
        "| 独立详情 | `views/user/ArchiveItemDetail.vue`（`/archive/item/:id`） |",
        "| 路由挂载 | `router/index.js` → `withPortalHub` |",
        "| 选型 / 对标 | [`domain-group-ui-styles.md`](./domain-group-ui-styles.md) §2 / §3 |",
        "",
        "---",
        "",
        "## 1. 组进度总表",
        "",
        "| 组 id | 组名 | 选型接线 | 公共壳 A | 组观感 B | 主表面 | 下一刀 |",
        "|-------|------|----------|----------|----------|--------|--------|",
        "| （全厂） | 公共壳 | — | **首刀已齐** | — | PortalLayout / AuthShell / AdminLayout / main.js | 抽检回归 |",
        "| borrow | 借用/占用 | 已接线 | 吃 A | **首刀已齐** | ArchiveBrowse bookshelf/stockrow/bedblocks/parcelshelf | 详情借阅文案再磨 |",
        "| trade | 交易 | 已接线 | 吃 A | **首刀已齐** | PortalHome mall + shelfgrid + ArchiveItemDetail | menuboard/showtime 再磨 |",
        "| reserve | 预约 | 已接线 | 吃 A | **首刀已齐** | SlotBook + slotstrip/roomstate/vehiclecard + 详情选时段 | 软皮短签再磨 |",
        "| content | 内容 | 已接线 | 吃 A | **首刀已齐** | folio/coverwall/ledger/splitdesk + 阅读详情 | 软皮短签再磨 |",
        "| apply | 报名/申请 | 已接线 | 吃 A | **首刀已齐** | eventposter/coursetable/noticeboard/tourcard + 详情报名 | 软皮短签再磨 |",
        "| follow | 跟进 | 已接线 | 吃 A | 未开 | pipeline/dossier/listing | 下一优先候选 |",
        "| interact | 互动 | 已接线 | 吃 A | **首刀已齐** | profilegrid/mutualpick/triprow + 详情意向；EXAM/SURVEY/VOTE 专用页不动 | 软皮短签再磨 |",
        "| ticket | 报修/工单 | 已接线 | 吃 A | 未开 | MyTickets repair surface | 待排 |",
        "| approve | 审批/填报 | 已接线 | 吃 A | 未开 | MyTickets/TicketsAdmin approve surface | 待排 |",
        "| fallback | 兜底 | 无选型键 | 吃 A | 未开 | 导引 + 中性壳 | 随壳即可 |",
        "",
        "建议下一轮：**跟进**（阶段看板/档案行）或 **报修**。",
        "",
        "---",
        "",
        "## 2. 已齐首刀（实现纪要）",
        "",
        "### 2.1 公共壳 A（全 68 域吃到）",
        "",
        "- 顶栏：实底品牌条、短链下划线选中、登录/注册实心按钮；去掉双光晕 SaaS 底",
        "- 登录：与门户同主色面板；少模板光晕",
        "- 管理端：侧栏品牌条用系统名 + 主色浅字；禁「管理后台」套话",
        "- `shellColors`：盖 `--el-color-primary` 及 light/dark 阶，避免残留默认蓝",
        "",
        "### 2.2 交易组 B",
        "",
        "- `PortalHome` mall：轮播点、新品 + **热销**、累计销量、卡片观感；点进 `/archive/item/:id`",
        "- `ArchiveBrowse` `shelfgrid`：货架卡加厚",
        "- `ArchiveItemDetail`：独立详情（加购/收藏/评价）；不写死 `/goods`",
        "- 覆盖域：`DOM-SHOP` / `DOM-FOOD` / `DOM-CINEMA`（FOOD/CINEMA 档口与排片 CSS 仍可再磨）",
        "",
        "### 2.3 借用组 B",
        "",
        "- `bookshelf` 脊列 / `stockrow` 台账行 / `bedblocks` 空占色块 / `parcelshelf` 驿站格",
        "- 有 `borrowSurfaceStyle` 时列表进独立详情；单据域详情「申请办理」→ `?openApply=1`",
        "- 覆盖域：`DOM-LIBRARY` / `EQUIP` / `ASSET` / `PARCEL` / `BED`（`PROCURE` 默认可走 stockrow 隐喻，组属审批）",
        "",
        "### 2.4 预约组 B（三档异脸，禁止套借用/货架模板）",
        "",
        "- `slotstrip`：号源横条 + 圆头像 +「有号」徽标；`SlotBook` 时段芯片（时间主信号、余号 pill）",
        "- `roomstate`：房态色块墙（可订绿/紧张琥珀/已满深灰）+ 顶条封面；`SlotBook` PMS 填色格",
        "- `vehiclecard`：左大图右日价宽卡；`SlotBook` 左边强调条档期卡",
        "- 有 `reserveSurfaceStyle` 时列表进 `/archive/item/:id`；详情主按钮「选择时段…」→ `/slots?itemId=`",
        "- 覆盖域：`DOM-HOSPITAL` / `MEETING` / `SALON` / `INSTRUMENT` / `HOTEL` / `CARRENT` / `PARKING`",
        "",
        "### 2.5 内容组 B（四档异脸，禁止套货架/库存/号源模板）",
        "",
        "- `folio`：刊头流——头条大封 + 摘要，下文横条阅读卡",
        "- `coverwall`：海报墙——2:3 封面格、题名极简（片库/曲库）",
        "- `ledger`：资料清单——虚线台账行、右栏作者·阅读数",
        "- `splitdesk`：双栏台——左目录高亮条、右 sticky 预览；宽屏不整卡跳详情",
        "- 有 `contentSurfaceStyle`（非 splitdesk）时进 `/archive/item/:id`；详情「正文」阅读脸",
        "- 覆盖域：`DOM-BLOG` / `FORUM` / `MEDIA` / `MUSIC` / `DOCLIB`",
        "",
        "### 2.6 报名组 B（四档异脸，禁止套内容海报/房态/资料清单）",
        "",
        "- `eventposter`：活动大海报 + 余位 pill（紧张琥珀 / 已满灰）",
        "- `coursetable`：课表格网，冲突格红边；无封面",
        "- `noticeboard`：启事便签——寻物琥珀 / 招领绿 / 线索靛",
        "- `tourcard`：左边强调条行程横卡 + 亮点摘要 + 余位/价",
        "- 有 `applySurfaceStyle` 时列表进 `/archive/item/:id`（`openApply=1` 仍走报名弹层）；详情「立即报名」",
        "- 覆盖域：`DOM-ACTIVITY` / `COURSE` / `LOST` / `TOUR`",
        "",
        "### 2.7 互动组 B（三档异脸；EXAM/SURVEY/VOTE 不进本轴）",
        "",
        "- `profilegrid`：圆头像居中资料卡 + 简介；墨灰，禁止粉色配对壳",
        "- `mutualpick`：双选志愿行 + 名额主信号（可叠配额条）",
        "- `triprow`：行程行——时刻·路线·余座；已满降透明度",
        "- 有 `interactSurfaceStyle` 时列表进 `/archive/item/:id`；详情「提交意向」",
        "- 覆盖域：`DOM-DATING` / `MUTUAL-*` / `CARPOOL` / `TIMEBANK`",
        "",
        "### 2.8 跨页卡底口径（用户列表统一）",
        "",
        "- 标杆口径：`ArchiveBrowse` 卡底 `card-foot`（纵向列）> `card-meta`（状态条）+ `card-acts`（操作条）",
        "- 铺开五页：`MyOrders` / `MyReservations` / `MyTickets` / `PeerTickets` / `MyFavorites`",
        "- 状态标签与操作按钮禁止挤在同一 `flex-wrap` 行；五页删本地 `.row` / `.acts`",
        "- 通用规则落全局 `styles/cardVoice.css`（`.card-foot` / `.card-meta` / `.card-acts`），各页不再自造",
        "- 状态色点单源 `utils/statusTone.js`：`reserveTone` 补入；`MyReservations` / `PeerTickets` 接上 `StatusChip`",
        "- 护栏：`backend/tests/test_portal_shell_nav.py`（钉 `card-foot/card-acts`、禁 `class=\"row\"/\"acts\"`）",
        "",
        "---",
        "",
        "## 3. 全域台账（68）",
        "",
        "域集合真源：`backend/app/bake/domains.py` → `DOMAIN_GROUPS` / `DOMAIN_CAPABILITIES`（与下表行数对账 = 68）。",
        "",
        "| 域 | 组 id | 组名 | 默认 surface | card_voice | 壳 brand | 检索占位 | 公共壳 A | 组观感 B |",
        "|----|-------|------|--------------|------------|----------|----------|----------|----------|",
    ]

    n = 0
    for gid, label, doms in DOMAIN_GROUPS:
        for d in sorted(doms):
            voice = resolve_card_voice(d)
            brand = resolve_shell_colors(d).get("brand", "")
            ph = top_search_placeholder(d)
            surf = surface_of(d)
            lines.append(
                f"| `{d}` | {gid} | {label} | `{surf}` | {voice} | `{brand}` | {ph} | {SHELL} | {LOOK.get(gid, '未开')} |"
            )
            n += 1

    lines += [
        "",
        f"**行数**：{n}（须 = `len(DOMAIN_CAPABILITIES)` = {len(DOMAIN_CAPABILITIES)}）。",
    ]
    miss = sorted(set(DOMAIN_CAPABILITIES) - {d for _, _, ds in DOMAIN_GROUPS for d in ds})
    extra = sorted({d for _, _, ds in DOMAIN_GROUPS for d in ds} - set(DOMAIN_CAPABILITIES))
    if miss:
        lines += ["", f"> **缺口**：在 CAPABILITIES 不在 GROUPS：{', '.join(miss)}"]
    if extra:
        lines += ["", f"> **多余**：在 GROUPS 不在 CAPABILITIES：{', '.join(extra)}"]

    lines += [
        "",
        "---",
        "",
        "## 4. 验收（每组收口前）",
        "",
        "1. 同组至少两域 bake 预览并排：去掉系统名仍可分清业务脸",
        "2. 无 Element 默认蓝主按钮；顶栏不像后台菜单条",
        "3. 列表主路径：交易/借用已进独立详情；其它组收口时同样禁止「只开抽屉交差」",
        "4. 菜单 path 集合相对接线测不回退（既有 `test_*_surface_style`）",
        "5. 学生可见文案无工厂腔",
        "",
        "---",
        "",
        "## 5. 修订",
        "",
        "| 日期 | 说明 |",
        "|------|------|",
        "| 2026-10-21 | 立册：公共壳 / 交易 / 借用首刀入档；68 域全表；接线与观感分列 |",
        "| 2026-10-21 | 跨页卡底口径：用户列表五页按 ArchiveBrowse `card-foot/card-meta/card-acts` 统一；通用规则入 `cardVoice.css`；护栏入 `test_portal_shell_nav.py` |",
        "",
    ]

    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {OUT} rows={n}")


if __name__ == "__main__":
    main()
