"""影院/演艺多主办方（复用 shopMarketplace）：扫词 / schema / SQL；单场馆反测。"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

from app.bake.domain_schema import validate_schema
from app.bake.engine_sql import domain_sql
from app.bake.scene_scan import cinema_product_kind, scan_shop_marketplace
from app.bake.schema.builders_slot import _cinema_schema
from app.bake.shell_face import resolve_shell_nav_style

_SEAT_SHOWS = (
    Path(__file__).resolve().parents[2]
    / "skeletons"
    / "baseline"
    / "frontend"
    / "src"
    / "views"
    / "SeatShows.vue"
)
_SEAT_MAP = (
    Path(__file__).resolve().parents[2]
    / "skeletons"
    / "baseline"
    / "frontend"
    / "src"
    / "views"
    / "SeatMap.vue"
)


def _show_create_body(sql: str) -> str:
    m = re.search(
        r"CREATE TABLE IF NOT EXISTS\s+cinema_show\s*\((.*?)\n\s*created_at\b",
        sql,
        re.I | re.S,
    )
    assert m is not None, "cinema_show CREATE missing"
    return m.group(1)


class CinemaMarketplaceScanTests(unittest.TestCase):
    def test_scan_on_organizer_taskbook(self) -> None:
        body = (
            "主办方商家后台：演出场次、场馆座位、订单核销；"
            "平台管理员：主办方商家管理、演出审核、全局订单。"
        )
        self.assertTrue(scan_shop_marketplace("潮汐演艺票务销售网站", body))

    def test_scan_off_single_venue_opening(self) -> None:
        body = (
            "用户选座购票；管理员：用户管理、演艺类别、剧目信息、场次座位、"
            "订单、评价、留言、轮播图、公告。"
        )
        self.assertFalse(scan_shop_marketplace("潮汐演艺票务销售网站", body))


class CinemaCartNamedTests(unittest.TestCase):
    """任务书点名购物车：与 seat_select 并存，禁止静默摘车。"""

    def test_taskbook_keeps_cart_menu(self) -> None:
        from app.bake.domain_schema import attach_accept, ensure_spec_schema
        from app.bake.features.opening_align import scan_opening_delivery_gaps
        from app.bake.features.seat_select import scan_cart_named

        text = (
            "用户功能模块划分为：登录注册模块、首页展示模块、用户模块、演出项目模块、"
            "购物车模块、支付与电子票模块、订单与售后退票模块、可视化选座购票模块、"
            "互动评价模块；主办方商家后台；平台管理员演出审核。"
        )
        self.assertTrue(scan_cart_named(text))
        schema = _cinema_schema("潮汐演艺票务销售网站", text)
        spec = ensure_spec_schema(
            {
                "title": "潮汐演艺票务销售网站的设计与实现",
                "domain": "DOM-CINEMA",
                "proposal_text": text,
                "capabilities": list(schema.get("capabilities") or []),
                "schema": schema,
            }
        )
        spec = attach_accept(spec, text)
        fsch = spec.get("schema") or {}
        self.assertTrue(fsch.get("seatSelectKeepCart"))
        user = (fsch.get("menus") or {}).get("user") or []
        keys = {m.get("key") for m in user if isinstance(m, dict)}
        self.assertIn("cart", keys)
        self.assertIn("seat_shows", keys)
        self.assertNotIn("addresses", keys)
        self.assertNotIn("archive", keys)
        gaps = scan_opening_delivery_gaps(spec, text)
        self.assertFalse(
            any("购物车" in g for g in gaps),
            f"点名购物车仍报缺口: {gaps}",
        )

    def test_no_cart_word_still_drops_cart(self) -> None:
        from app.bake.domain_schema import attach_accept, ensure_spec_schema

        text = "用户选座购票；管理员场次座位订单公告。"
        schema = _cinema_schema("潮汐演艺票务销售网站", text)
        spec = attach_accept(
            ensure_spec_schema(
                {
                    "title": "潮汐演艺票务销售网站",
                    "domain": "DOM-CINEMA",
                    "proposal_text": text,
                    "capabilities": list(schema.get("capabilities") or []),
                    "schema": schema,
                }
            ),
            text,
        )
        fsch = spec.get("schema") or {}
        self.assertFalse(bool(fsch.get("seatSelectKeepCart")))
        keys = {
            m.get("key")
            for m in ((fsch.get("menus") or {}).get("user") or [])
            if isinstance(m, dict)
        }
        self.assertNotIn("cart", keys)


class CinemaMarketplaceSchemaTests(unittest.TestCase):
    def test_marketplace_schema(self) -> None:
        text = "主办方商家后台与平台管理员演出审核、商家管理"
        schema = _cinema_schema("潮汐演艺票务销售网站", text)
        self.assertTrue(schema.get("shopMarketplace"))
        roles = schema.get("roles") or {}
        self.assertEqual((roles.get("subadmin") or {}).get("label"), "主办方")
        self.assertIn("平台", (roles.get("admin") or {}).get("label") or "")
        labels = schema.get("labels") or {}
        self.assertIn("主办方", str(labels.get("registerHint") or ""))
        fulfill = str(labels.get("orderFulfillHint") or "")
        self.assertRegex(fulfill, r"无物流|无.*发货|出票")
        self.assertNotRegex(fulfill, r"(?<!无)物流发货|(?<!无)确认发货")
        staff = str(labels.get("ordersStaffLead") or "")
        self.assertRegex(staff, r"出票|核销|退票")
        admin_lead = str(labels.get("ordersAdminLead") or "")
        self.assertIn("全平台", admin_lead)
        ok, errs = validate_schema(schema)
        self.assertTrue(ok, errs)
        self.assertEqual(
            resolve_shell_nav_style("DOM-CINEMA", "潮汐", text),
            "storefront",
        )
        from app.bake.staff_posts import attach_staff_posts, staff_posts_for_domain
        from app.bake.schema.usecases import list_usecase_actors

        posts = staff_posts_for_domain(
            "DOM-CINEMA", title="潮汐", proposal_text=text
        )
        # 材料点名「主办方商家」→ 岗名跟材料（不再停在皮默认「主办方」）
        self.assertTrue(
            any(
                p.get("id") == "shop_merchant" and p.get("label") == "主办方商家"
                for p in posts
            ),
            posts,
        )
        # 完整身份段：用户 / 主办方商家 / 平台管理员
        full = (
            "用户功能模块划分为：登录注册模块、选座购票模块、订单模块。"
            "主办方商家后台功能模块划分为：演出场次管理模块、订单核销模块。"
            "平台管理员后台功能模块划分为：用户管理模块、主办方商家管理模块、演出审核管理模块。"
        )
        attached = attach_staff_posts(
            _cinema_schema("潮汐演艺票务销售网站", full),
            "DOM-CINEMA",
            proposal_text=full,
            title="潮汐演艺票务销售网站",
        )
        actors = {a["label"] for a in list_usecase_actors(attached)}
        self.assertIn("用户", actors)
        self.assertIn("主办方商家", actors)
        self.assertTrue(any("平台管理员" in lab for lab in actors), actors)
        from app.bake.profile_fields import profile_fields_for

        fields = profile_fields_for("DOM-CINEMA", title="潮汐", proposal_text=text)
        shop_name = next(
            (f for f in fields if isinstance(f, dict) and f.get("key") == "shopName"),
            None,
        )
        self.assertIsNotNone(shop_name)
        self.assertEqual(shop_name.get("label"), "主办方名称")
        self.assertEqual(shop_name.get("forRoles"), ["staff"])
        arch = (schema.get("entities") or {}).get("archive") or {}
        self.assertTrue(arch.get("softDelete"), "多主办方场次须可上下架")
        self.assertEqual(labels.get("archiveReviewTitle"), "演出审核")
        admin_lead = str(labels.get("archiveAdminLead") or "")
        staff_lead = str(labels.get("archiveStaffLead") or "")
        self.assertIn("审核主办方", admin_lead)
        self.assertNotIn("本方场次", admin_lead)
        self.assertIn("本方场次", staff_lead)
        self.assertIn("演出审核", staff_lead)
        self.assertEqual(labels.get("topSearchPlaceholder"), "剧目 / 场次")
        self.assertEqual(labels.get("domainLabel"), "演艺选座")
        self.assertNotEqual(labels.get("effectHallImax"), "IMAX")

    def test_taskbook_eticket_and_show_review_align(self) -> None:
        """任务书：支付与电子票 + 演出审核 → 取票码文案 + 多店审核对齐，禁止报缺口。"""
        from app.bake.domain_schema import attach_accept, ensure_spec_schema
        from app.bake.features.opening_align import scan_opening_delivery_gaps

        text = (
            "用户功能模块划分为：登录注册模块、首页展示模块、用户模块、演出项目模块、"
            "购物车模块、支付与电子票模块、订单与售后退票模块、可视化选座购票模块、"
            "互动评价模块；主办方商家后台；平台管理员演出审核、主办方商家管理。"
        )
        schema = _cinema_schema("潮汐演艺票务销售网站", text)
        self.assertEqual(schema.get("labels", {}).get("pickupCodeLabel"), "电子票码")
        self.assertEqual(schema.get("labels", {}).get("archiveReviewTitle"), "演出审核")
        spec = attach_accept(
            ensure_spec_schema(
                {
                    "title": "潮汐演艺票务销售网站的设计与实现",
                    "domain": "DOM-CINEMA",
                    "proposal_text": text,
                    "capabilities": list(schema.get("capabilities") or []),
                    "schema": schema,
                }
            ),
            text,
        )
        gaps = scan_opening_delivery_gaps(spec, text)
        self.assertFalse(
            any("电子票" in g or "演出" in g or "商品审核" in g for g in gaps),
            f"电子票/演出审核仍报缺口: {gaps}",
        )
        self.assertIn(
            "archiveReviewTitle",
            (
                Path(__file__).resolve().parents[2]
                / "skeletons"
                / "baseline"
                / "frontend"
                / "src"
                / "views"
                / "admin"
                / "ArchiveAdmin.setup.js"
            ).read_text(encoding="utf-8"),
        )

    def test_single_venue_schema_unchanged(self) -> None:
        text = "场馆管理者高效管理剧目、订单；用户在线选座购票。"
        schema = _cinema_schema("潮汐演艺票务销售网站", text)
        self.assertFalse(bool(schema.get("shopMarketplace")))
        self.assertEqual(schema.get("cinemaFace"), "performance")
        roles = schema.get("roles") or {}
        self.assertEqual((roles.get("subadmin") or {}).get("label"), "售票员")
        self.assertIn("场馆主管", (roles.get("admin") or {}).get("label") or "")
        labels = schema.get("labels") or {}
        self.assertNotIn("主办方入驻", str(labels.get("authPoints") or ""))
        self.assertEqual(labels.get("seatStageLabel"), "舞台")
        arch = (schema.get("entities") or {}).get("archive") or {}
        self.assertFalse(bool(arch.get("softDelete")))
        ok, errs = validate_schema(schema)
        self.assertTrue(ok, errs)


class CinemaMarketplaceSqlTests(unittest.TestCase):
    def test_single_no_marketplace_residue(self) -> None:
        sql = domain_sql(
            "DOM-CINEMA",
            "t_cinema_single",
            title="潮汐演艺票务销售网站",
            proposal_text="用户选座购票；管理员场次座位订单公告轮播",
        )
        show = _show_create_body(sql)
        self.assertNotIn("owner_username", show)
        self.assertNotIn("星海脱口秀", sql)
        self.assertNotIn("merchant_b", sql)
        self.assertNotIn("shop_merchant", sql)

    def test_marketplace_sql_owner_and_dual_organizers(self) -> None:
        sql = domain_sql(
            "DOM-CINEMA",
            "t_cinema_mp",
            title="潮汐演艺票务销售网站",
            proposal_text="主办方商家后台；平台管理员主办方商家管理、演出审核",
        )
        show = _show_create_body(sql)
        self.assertIn("owner_username", show)
        self.assertIn("deleted_at", show)
        self.assertIn("潮汐剧场", sql)
        self.assertIn("星海演艺", sql)
        self.assertIn("春江话剧夜", sql)
        self.assertIn("merchant_b", sql)
        self.assertIn("shop_merchant", sql)
        self.assertIn("owner_username", sql)

    def test_single_sql_no_deleted_at_forced(self) -> None:
        sql = domain_sql(
            "DOM-CINEMA",
            "t_cinema_single2",
            title="潮汐演艺票务销售网站",
            proposal_text="用户选座购票；管理员场次座位订单公告",
        )
        show = _show_create_body(sql)
        self.assertNotIn("deleted_at", show)


class CinemaMarketplaceUiTests(unittest.TestCase):
    def test_login_register_use_role_labels_not_shop_buyer(self) -> None:
        """多店登录/注册跟域角色名；禁止基线写死「买家或商家」（影院会穿帮成应付商城腔）。"""
        root = Path(__file__).resolve().parents[2] / "skeletons" / "baseline" / "frontend" / "src" / "views"
        login = (root / "Login.vue").read_text(encoding="utf-8")
        register = (root / "Register.vue").read_text(encoding="utf-8")
        self.assertNotIn("买家或商家账号登录", login)
        self.assertNotIn("买家与商家可注册", login)
        self.assertIn("userLabel.value}或${subLabel.value}", login)
        self.assertNotIn('label="买家"', register)
        self.assertNotIn('label="商家"', register)
        self.assertIn(":label=\"userLabel\"", register)
        self.assertIn(":label=\"subLabel\"", register)

    def test_my_orders_cinema_skips_marketplace_ship_labels(self) -> None:
        """影院多店订单态跟 schema；禁止套商城「待发货/确认收货/退货物流」。"""
        setup = (
            Path(__file__).resolve().parents[2]
            / "skeletons"
            / "baseline"
            / "frontend"
            / "src"
            / "views"
            / "user"
            / "MyOrders.setup.js"
        ).read_text(encoding="utf-8")
        self.assertIn("!marketplace.value || isCinema.value", setup)
        self.assertIn("isCinema.value || !marketplace.value", setup)
        self.assertIn("isCinema.value || !changeAddressOn.value", setup)
        self.assertIn("影院退票无退货物流", setup)
        self.assertIn("座位、场次、观演体验", setup)
        self.assertIn("canPrintReceipt", setup)
        self.assertNotIn("canSetRefundFee", setup)

    def test_archive_admin_role_leads_by_super(self) -> None:
        """多主办方场次页：超管→archiveAdminLead，主办方→archiveStaffLead。"""
        root = (
            Path(__file__).resolve().parents[2]
            / "skeletons"
            / "baseline"
            / "frontend"
            / "src"
            / "views"
            / "admin"
        )
        vue = (root / "ArchiveAdmin.vue").read_text(encoding="utf-8")
        setup = (root / "ArchiveAdmin.setup.js").read_text(encoding="utf-8")
        self.assertIn("pageLead", setup)
        self.assertIn("archiveAdminLead", setup)
        self.assertIn("archiveStaffLead", setup)
        self.assertIn("pageLead", vue)
        self.assertIn('v-if="pageLead"', vue)

    def test_seat_attr_brush_and_snack_delete(self) -> None:
        """座位属性：刷子选类型再点座；卖品管理端可删除。"""
        root = (
            Path(__file__).resolve().parents[2]
            / "skeletons"
            / "baseline"
            / "frontend"
            / "src"
            / "views"
            / "admin"
        )
        vue = (root / "ArchiveAdmin.vue").read_text(encoding="utf-8")
        setup = (root / "ArchiveAdmin.setup.js").read_text(encoding="utf-8")
        self.assertIn("seatAttrBrush", setup)
        self.assertIn("paintSeatAttr", setup)
        self.assertNotIn("cycleSeatAttr", setup)
        self.assertIn("先选座位类型，再点座位刷上", vue)
        self.assertIn("deleteSnackRow", setup)
        self.assertIn("删除卖品", setup)
        self.assertIn("@click=\"deleteSnackRow(row)\"", vue)
        ctrl = (
            Path(__file__).resolve().parents[2]
            / "skeletons"
            / "baseline"
            / "backend"
            / "src"
            / "main"
            / "java"
            / "com"
            / "thesis"
            / "controller"
            / "SeatController.java"
        ).read_text(encoding="utf-8")
        store = (
            Path(__file__).resolve().parents[2]
            / "skeletons"
            / "baseline"
            / "backend"
            / "src"
            / "main"
            / "java"
            / "com"
            / "thesis"
            / "service"
            / "SeatStore.java"
        ).read_text(encoding="utf-8")
        self.assertIn('@DeleteMapping("/snacks/{id}")', ctrl)
        self.assertIn("deleteSnack", store)

    def test_orders_admin_cinema_skips_marketplace_logistics(self) -> None:
        """影院/演艺管理端：多主办方也不出「运输中/已签收」与物流节点。"""
        root = (
            Path(__file__).resolve().parents[2]
            / "skeletons"
            / "baseline"
            / "frontend"
            / "src"
            / "views"
            / "admin"
            / "OrdersAdmin.vue"
        )
        text = root.read_text(encoding="utf-8")
        self.assertIn("marketplace && !isCinema && row.status === 'shipped'", text)
        self.assertIn("marketplace && !isCinema && (row.status === 'shipped'", text)
        self.assertIn("isCinema.value || !changeAddressOn.value", text)
        self.assertIn("isCinema.value || !shipNodesOn.value", text)
        store = (
            Path(__file__).resolve().parents[2]
            / "skeletons"
            / "baseline"
            / "backend"
            / "src"
            / "main"
            / "java"
            / "com"
            / "thesis"
            / "capability"
            / "OrderStore.java"
        ).read_text(encoding="utf-8")
        self.assertIn("shopMarketplaceEnabled() && !SeatStore.enabled()", store)
        self.assertIn("影院/演艺订单无物流进度", store)

    def test_marketplace_pending_is_pay_not_pickup(self) -> None:
        """多主办方开演示支付：pending=待付款，confirmed=待取票；勿把未付款叫待取票。"""
        mp = _cinema_schema(
            "潮汐演艺票务销售网站",
            "主办方商家后台；平台管理员主办方商家管理、演出审核",
        )
        states = ((mp.get("entities") or {}).get("order") or {}).get("states") or {}
        self.assertEqual(states.get("pending"), "待付款")
        self.assertEqual(states.get("confirmed"), "待取票")
        self.assertTrue(mp.get("demoPay"))
        self.assertTrue(mp.get("shopMarketplace"))
        single = _cinema_schema(
            "潮汐演艺票务销售网站",
            "用户选座购票；管理员场次座位订单公告",
        )
        s2 = ((single.get("entities") or {}).get("order") or {}).get("states") or {}
        self.assertEqual(s2.get("pending"), "待取票")
        self.assertEqual(s2.get("confirmed"), "已确认")
        self.assertFalse(single.get("demoPay"))

    def test_seat_shows_reads_shop_name(self) -> None:
        src = _SEAT_SHOWS.read_text(encoding="utf-8")
        self.assertIn("shopName", src)
        self.assertIn("cinemaFace", src)
        self.assertIn("show-card", src)
        self.assertIn("show-poster", src)
        self.assertIn("box-sizing: border-box", src)
        self.assertIn("minmax(0, 1fr)", src)
        self.assertIn("assertCanManageShow", Path(
            Path(__file__).resolve().parents[2]
            / "skeletons"
            / "baseline"
            / "backend"
            / "src"
            / "main"
            / "java"
            / "com"
            / "thesis"
            / "controller"
            / "SeatController.java"
        ).read_text(encoding="utf-8"))

    def test_mybatis_seat_mapper_uses_cinema_columns(self) -> None:
        mapper = (
            Path(__file__).resolve().parents[2]
            / "skeletons"
            / "overlays"
            / "persistence-mybatis"
            / "backend"
            / "src"
            / "main"
            / "java"
            / "com"
            / "thesis"
            / "mapper"
            / "SeatMapper.java"
        ).read_text(encoding="utf-8")
        self.assertIn("title, author, isbn", mapper)
        self.assertNotIn("price_yuan AS author", mapper)
        self.assertNotIn("hall_note AS isbn", mapper)


class CinemaFaceTests(unittest.TestCase):
    """DOM-CINEMA 同域双皮：演艺扫词开，默认影院。"""

    def test_scan_performance_from_title(self) -> None:
        self.assertEqual(
            cinema_product_kind("潮汐演艺票务销售网站", "用户选座购票"),
            "performance",
        )
        self.assertEqual(
            cinema_product_kind("校园影院选座购票系统", "排片与银幕选座"),
            "cinema",
        )

    def test_performance_schema_labels(self) -> None:
        schema = _cinema_schema("潮汐演艺票务销售网站", "剧目场次选座购票")
        self.assertEqual(schema.get("cinemaFace"), "performance")
        labels = schema.get("labels") or {}
        self.assertEqual(labels.get("seatStageLabel"), "舞台")
        self.assertEqual(labels.get("seatShowsTitle"), "演出选座")
        self.assertEqual(labels.get("cinemaNoticeLabel"), "观演须知")
        self.assertEqual(labels.get("cinemaSnackLabel"), "观演加购")
        self.assertNotIn("爆米花", str(labels.get("cinemaSnackHint") or ""))
        self.assertEqual(labels.get("seatAttrCoupleLabel"), "双人座")
        roles = schema.get("roles") or {}
        self.assertEqual((roles.get("user") or {}).get("label"), "观众")
        fields = ((schema.get("entities") or {}).get("archive") or {}).get("fields") or []
        title_f = next((f for f in fields if isinstance(f, dict) and f.get("key") == "title"), {})
        isbn_f = next((f for f in fields if isinstance(f, dict) and f.get("key") == "isbn"), {})
        self.assertIn("剧目", str(title_f.get("label") or ""))
        self.assertIn("场馆", str(isbn_f.get("label") or ""))

    def test_cinema_schema_default_face(self) -> None:
        schema = _cinema_schema("校园影院选座购票系统", "排片选座与特效厅")
        self.assertEqual(schema.get("cinemaFace"), "cinema")
        labels = schema.get("labels") or {}
        self.assertEqual(labels.get("seatStageLabel"), "银幕")
        self.assertNotEqual(labels.get("seatShowsTitle"), "演出选座")
        roles = schema.get("roles") or {}
        self.assertEqual((roles.get("user") or {}).get("label"), "观影者")
        self.assertIn("影院主管", (roles.get("admin") or {}).get("label") or "")

    def test_performance_seed_categories(self) -> None:
        from app.bake.sql.domain_scene_seed import apply_domain_scene_seed

        base = (
            Path(__file__).resolve().parents[2]
            / "backend"
            / "app"
            / "bake"
            / "sql"
            / "templates"
            / "DOM-CINEMA.sql"
        ).read_text(encoding="utf-8")
        out = apply_domain_scene_seed(
            "DOM-CINEMA",
            base,
            title="潮汐演艺票务销售网站",
            proposal_text="主办方商家后台与平台管理员演出审核",
        )
        self.assertIn("话剧", out)
        self.assertIn("春江话剧夜", out)
        self.assertIn("潮汐剧场", out)
        self.assertNotIn("IMAX", out)

    def test_baseline_seat_pages_wire_face(self) -> None:
        shows = _SEAT_SHOWS.read_text(encoding="utf-8")
        seat_map = _SEAT_MAP.read_text(encoding="utf-8")
        seat_store = (
            Path(__file__).resolve().parents[2]
            / "skeletons/baseline/backend/src/main/java/com/thesis/service/SeatStore.java"
        ).read_text(encoding="utf-8")
        self.assertIn("data-cinema-face", shows)
        self.assertIn("face-performance", shows)
        self.assertIn("/api/categories", shows)
        self.assertIn("perf-shelf", shows)
        self.assertIn("space-evenly", shows)
        self.assertIn("演出分类", shows)
        self.assertNotIn("catIconSvg", shows)
        self.assertIn("rankShows", shows)
        self.assertIn("catsNeedScroll", shows)
        self.assertIn("soldCount", shows)
        self.assertNotIn("perf-hot", shows)
        self.assertNotIn("热卖推荐", shows)
        self.assertNotIn("精选推荐", shows)
        self.assertIn("PortalCarousel", shows)  # 注释：头图归布局广告位
        self.assertIn("enrichSoldCounts", seat_store)
        self.assertIn("seatStageLabel", seat_map)
        self.assertIn("face-performance", seat_map)
        self.assertIn("stage", seat_map)

    def test_performance_account_chrome_not_guanying(self) -> None:
        """演艺皮账户入口禁「我的观影」（影院腔）。"""
        util = (
            Path(__file__).resolve().parents[2]
            / "skeletons/baseline/frontend/src/utils/portalShellNav.js"
        ).read_text(encoding="utf-8")
        self.assertIn("我的观演", util)
        self.assertIn("cinemaFaceFromDelivered", util)
        self.assertIn("performance", util)

    def test_seat_map_hold_sync_and_expire(self) -> None:
        """取消选座勿被旧占座回包写回；倒计时到点须强制空占座释放。"""
        seat_map = _SEAT_MAP.read_text(encoding="utf-8")
        self.assertIn("holdSeq", seat_map)
        self.assertIn("expireHoldLocal", seat_map)
        self.assertIn("forceClear", seat_map)
        self.assertIn("applyingMap", seat_map)
        store = (
            Path(__file__).resolve().parents[2]
            / "skeletons/baseline/backend/src/main/java/com/thesis/service/SeatStore.java"
        ).read_text(encoding="utf-8")
        self.assertIn("过期占座不当", store)
        self.assertIn("picked.value = mine", seat_map)
        self.assertIn("seats: []", seat_map)

    def test_seat_home_guest_back_from_login(self) -> None:
        """登录「返回首页」须能进场次列表：白名单 + 品牌路径跟 userHomePath + 列表 API 免登录。"""
        root = Path(__file__).resolve().parents[2]
        session = (root / "skeletons/baseline/frontend/src/utils/session.js").read_text(
            encoding="utf-8"
        )
        menus = (root / "skeletons/baseline/frontend/src/utils/menuRoutes.js").read_text(
            encoding="utf-8"
        )
        seat = (
            root / "skeletons/baseline/backend/src/main/java/com/thesis/controller/SeatController.java"
        ).read_text(encoding="utf-8")
        self.assertIn("/seats/shows", session)
        self.assertIn("userHomePath", menus)
        # listOpenShows 调用前不得再 requireLogin（游客可逛场次）
        block = seat.split('@GetMapping("/shows")', 1)[1].split("@GetMapping", 1)[0]
        self.assertIn("listOpenShows", block)
        self.assertNotIn("requireLogin", block)

    def test_performance_detail_tabs_and_nav(self) -> None:
        detail = (
            Path(__file__).resolve().parents[2]
            / "skeletons/baseline/frontend/src/views/user/ArchiveItemDetail.vue"
        ).read_text(encoding="utf-8")
        browse = (
            Path(__file__).resolve().parents[2]
            / "skeletons/baseline/frontend/src/views/user/ArchiveBrowse.setup.js"
        ).read_text(encoding="utf-8")
        portal = (
            Path(__file__).resolve().parents[2]
            / "skeletons/baseline/frontend/src/views/user/PortalHome.setup.js"
        ).read_text(encoding="utf-8")
        self.assertIn("项目详情", detail)
        self.assertIn("购票须知", detail)
        self.assertIn("isPerformance", detail)
        self.assertIn("isPerformanceFace", browse)
        self.assertIn("isPerformanceFace", portal)


if __name__ == "__main__":
    unittest.main()
