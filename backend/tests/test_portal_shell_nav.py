"""§3 门户壳：开题菜单；顶栏业务 / 头像账户 / 市集右侧栏；无「更多」垃圾桶。"""

from __future__ import annotations

from tests._vue_src import vue_src

import json
import subprocess
import unittest
from pathlib import Path

_FRONT = (
    Path(__file__).resolve().parents[2] / "skeletons" / "baseline" / "frontend" / "src"
)
_UTIL = _FRONT / "utils" / "portalShellNav.js"


def _eval(payload: dict) -> dict:
    uri = json.dumps(_UTIL.as_uri())
    body = json.dumps(payload, ensure_ascii=False)
    script = (
        "import {\n"
        "  classifyPortalMenus,\n"
        "  shellModeFromDelivered,\n"
        "  shellNavStyleFromDelivered,\n"
        "  domainGroupFromDelivered,\n"
        "  cartUsesChromeBadge,\n"
        f"}} from {uri};\n"
        f"const input = {body};\n"
        "const delivered = input.delivered || {};\n"
        "const mode = shellModeFromDelivered(delivered);\n"
        "const navStyle = shellNavStyleFromDelivered(delivered);\n"
        "const group = domainGroupFromDelivered(delivered);\n"
        "const split = classifyPortalMenus(input.items || [], mode, navStyle, delivered);\n"
        "console.log(JSON.stringify({\n"
        "  mode, navStyle, group,\n"
        "  primary: split.primary.map((x) => x.key),\n"
        "  account: split.account.map((x) => x.key),\n"
        "  sideRail: split.sideRail.map((x) => x.key),\n"
        "  cartBadge: cartUsesChromeBadge(mode, navStyle, delivered),\n"
        "}));\n"
    )
    proc = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    if proc.returncode != 0:
        raise AssertionError(proc.stderr or proc.stdout)
    return json.loads(proc.stdout)


def _item(key: str) -> dict:
    return {"key": key, "to": f"/{key}", "label": key}


_SHOP_MENUS = [
    "archive",
    "favorites",
    "cart",
    "order_reviews",
    "my_orders",
    "addresses",
    "guestbook",
    "content",
    "dm",
    "messages",
]


class PortalShellNavTests(unittest.TestCase):
    def test_storefront_account_under_avatar(self) -> None:
        got = _eval(
            {
                "delivered": {
                    "domain": "DOM-SHOP",
                    "domainGroup": "trade",
                    "tradeSurfaceStyle": "shelfgrid",
                    "shellNavStyle": "storefront",
                },
                "items": [_item(k) for k in _SHOP_MENUS],
            }
        )
        self.assertEqual(got["primary"], ["archive", "my_orders", "content"])
        self.assertEqual(
            got["account"],
            ["favorites", "order_reviews", "addresses", "guestbook", "dm"],
        )
        self.assertEqual(got["sideRail"], [])
        self.assertTrue(got["cartBadge"])
        self.assertNotIn("my_orders", got["account"])

    def test_marketplace_secondary_to_rail(self) -> None:
        got = _eval(
            {
                "delivered": {
                    "domain": "DOM-SHOP",
                    "domainGroup": "trade",
                    "tradeSurfaceStyle": "shelfgrid",
                    "shellNavStyle": "marketplace",
                },
                "items": [_item(k) for k in _SHOP_MENUS],
            }
        )
        self.assertEqual(got["primary"], ["archive", "cart", "my_orders", "content"])
        self.assertEqual(got["account"], [])
        self.assertIn("favorites", got["sideRail"])
        self.assertIn("addresses", got["sideRail"])
        self.assertFalse(got["cartBadge"])

    def test_borrow_business_all_on_primary(self) -> None:
        got = _eval(
            {
                "delivered": {"domain": "DOM-LIBRARY", "domainGroup": "borrow"},
                "items": [
                    _item("archive"),
                    _item("my_tickets"),
                    _item("book_suggest"),
                    _item("favorites"),
                    _item("guestbook"),
                    _item("content"),
                    _item("messages"),
                ],
            }
        )
        self.assertEqual(
            got["primary"],
            ["archive", "my_tickets", "book_suggest", "content"],
        )
        self.assertEqual(got["account"], ["favorites", "guestbook"])
        self.assertNotIn("my_tickets", got["account"])
        self.assertEqual(got["sideRail"], [])

    def test_many_business_stay_on_primary_no_more_dump(self) -> None:
        keys = [
            "archive",
            "my_tickets",
            "peer_tickets",
            "slots",
            "week_calendar",
            "content",
            "favorites",
        ]
        got = _eval(
            {
                "delivered": {"domain": "DOM-DORM", "domainGroup": "ticket"},
                "items": [_item(k) for k in keys],
            }
        )
        # 非市集：业务全留顶栏，不造「更多」、不塞头像
        self.assertEqual(
            got["primary"],
            ["archive", "my_tickets", "peer_tickets", "slots", "week_calendar", "content"],
        )
        self.assertEqual(got["account"], ["favorites"])
        self.assertEqual(got["sideRail"], [])

    def test_does_not_invent_keys(self) -> None:
        got = _eval(
            {
                "delivered": {"domain": "DOM-BLOG", "domainGroup": "content"},
                "items": [
                    _item("content"),
                    _item("favorites"),
                    _item("guestbook"),
                ],
            }
        )
        all_keys = got["primary"] + got["account"] + got["sideRail"]
        self.assertEqual(sorted(all_keys), sorted(["content", "favorites", "guestbook"]))
        self.assertEqual(got["primary"], ["content"])
        self.assertEqual(got["account"], ["favorites", "guestbook"])

    def test_account_face_by_group(self) -> None:
        uri = json.dumps(_UTIL.as_uri())
        cases = [
            ({"domainGroup": "borrow"}, "reader"),
            ({"domainGroup": "trade", "shellNavStyle": "marketplace"}, "stall"),
            ({"domainGroup": "trade", "shellNavStyle": "storefront"}, "member"),
            (
                {
                    "domainGroup": "trade",
                    "shellNavStyle": "storefront",
                    "tradeSurfaceStyle": "showtime",
                },
                "showcard",
            ),
            ({"domainGroup": "content"}, "desk"),
            ({"domainGroup": "approve"}, "inbox"),
            ({"domainGroup": "ticket"}, "service"),
        ]
        for delivered, want in cases:
            body = json.dumps({"delivered": delivered}, ensure_ascii=False)
            script = (
                "import { accountFaceFromDelivered } from "
                f"{uri};\n"
                f"const input = {body};\n"
                "console.log(accountFaceFromDelivered(input.delivered));\n"
            )
            proc = subprocess.run(
                ["node", "--input-type=module", "-e", script],
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=False,
            )
            if proc.returncode != 0:
                raise AssertionError(proc.stderr or proc.stdout)
            self.assertEqual(proc.stdout.strip(), want, delivered)

    def test_account_face_copy_no_factory_jargon(self) -> None:
        """账户中心导语须学生可见口语，禁旁路/分栏等工厂腔。"""
        util = _UTIL.read_text(encoding="utf-8")
        start = util.find("export function accountFaceCopy")
        end = util.find("export function accountChromeLabel", start)
        if end < 0:
            end = util.find("export function shellModeFromDelivered", start)
        self.assertGreater(start, 0)
        self.assertGreater(end, start)
        copy_fn = util[start:end]
        for bad in ("旁路", "分栏", "顶栏业务", "bake", "DOM-"):
            self.assertNotIn(bad, copy_fn)
        center = (_FRONT / "views" / "user" / "AccountCenter.vue").read_text(
            encoding="utf-8"
        )
        # 与资料页同脸：身份卡 + 墨色标题，禁止登录前后各一套封面
        self.assertIn("af-identity", center)
        self.assertIn("profileEntryLabel", center)
        self.assertIn("PROFILE_ENTRY_LABEL", util)
        self.assertIn("个人资料", util)
        self.assertIn("requireLogin", center)
        self.assertNotIn("portal-cover,", center.split("<style")[0])
        # 下方入口按钮：左色条 + 深色抬升
        self.assertIn("border-left: 3px solid", center)
        self.assertIn("data-scheme='dark'", center)

    def test_p3copy_catches_jargon_in_portal_shell_js(self) -> None:
        """p3copy 须扫 utils JS 字面量；注释里的旁路/顶栏业务不算。"""
        import tempfile
        from pathlib import Path

        from app.bake.domain_schema import FACTORY_UI_FORBIDDEN
        from app.bake.gates.evaluate import _student_copy_hits

        self.assertIn("旁路", FACTORY_UI_FORBIDDEN)
        self.assertIn("顶栏业务", FACTORY_UI_FORBIDDEN)
        # Windows 下后端 reload 监视会占住临时目录句柄，cleanup 失败不阻塞断言
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as td:
            ws = Path(td)
            util_dst = ws / "frontend" / "src" / "utils" / "portalShellNav.js"
            util_dst.parent.mkdir(parents=True)
            util_dst.write_text(
                "export function accountFaceCopy() {\n"
                "  return { title: '账户', lead: '服务台旁路入口在此。' }\n"
                "}\n",
                encoding="utf-8",
            )
            hits = _student_copy_hits(ws, {"schema": {}})
            self.assertTrue(
                any(h.get("bad") == "旁路" for h in hits),
                msg=str(hits),
            )
            util_dst.write_text(
                "/** 资助公示旁路岛 */\nexport const x = 1\n",
                encoding="utf-8",
            )
            hits2 = _student_copy_hits(ws, {"schema": {}})
            self.assertEqual(hits2, [], msg=str(hits2))

    def test_arrange_side_rail_respects_saved_outside(self) -> None:
        """编辑勾选/顺序须落地：不得保存后又自动补满外侧。"""
        uri = json.dumps(_UTIL.as_uri())
        script = (
            "import { arrangeSideRail } from "
            f"{uri};\n"
            "const items = ['a','b','c','d','e','f'].map((k) => "
            "({ key: k, to: '/' + k, label: k }));\n"
            "const saved = arrangeSideRail(items, { order: ['c','a','b','d','e','f'], "
            "outside: ['c','a'] });\n"
            "const fresh = arrangeSideRail(items, null);\n"
            "console.log(JSON.stringify({\n"
            "  savedOutside: saved.outside.map((x) => x.key),\n"
            "  savedMore: saved.more.map((x) => x.key),\n"
            "  freshOutside: fresh.outside.map((x) => x.key),\n"
            "}));\n"
        )
        proc = subprocess.run(
            ["node", "--input-type=module", "-e", script],
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )
        if proc.returncode != 0:
            raise AssertionError(proc.stderr or proc.stdout)
        got = json.loads(proc.stdout)
        self.assertEqual(got["savedOutside"], ["c", "a"])
        self.assertEqual(got["savedMore"][:4], ["b", "d", "e", "f"])
        self.assertEqual(len(got["freshOutside"]), 5)

    def test_account_hub_groups_not_flat_dump(self) -> None:
        uri = json.dumps(_UTIL.as_uri())
        script = (
            "import { groupAccountHubItems, collectAccountHubItems } from "
            f"{uri};\n"
            "const items = ['favorites','coupons','dm','doc_mine'].map((k) => "
            "({ key: k, to: '/' + k, label: k }));\n"
            "const hub = collectAccountHubItems(items);\n"
            "const groups = groupAccountHubItems(hub);\n"
            "console.log(JSON.stringify({\n"
            "  keys: hub.map((x) => x.key),\n"
            "  titles: groups.map((g) => g.title),\n"
            "  flat: groups.flatMap((g) => g.items.map((x) => x.key)),\n"
            "}));\n"
        )
        proc = subprocess.run(
            ["node", "--input-type=module", "-e", script],
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )
        if proc.returncode != 0:
            raise AssertionError(proc.stderr or proc.stdout)
        got = json.loads(proc.stdout)
        self.assertEqual(got["keys"], ["favorites", "coupons", "dm", "doc_mine"])
        self.assertIn("常用", got["titles"])
        self.assertIn("资产与优惠", got["titles"])
        self.assertEqual(got["flat"], ["favorites", "dm", "coupons", "doc_mine"])

    def test_skeleton_no_more_dump(self) -> None:
        portal = (_FRONT / "layouts" / "PortalLayout.vue").read_text(encoding="utf-8")
        util = _UTIL.read_text(encoding="utf-8")
        account = (_FRONT / "views" / "user" / "AccountCenter.vue").read_text(encoding="utf-8")
        router = (_FRONT / "router" / "index.js").read_text(encoding="utf-8")
        self.assertNotIn("navMore", portal)
        self.assertNotIn(">更多<", portal)
        self.assertIn("router.push('/account')", portal)
        self.assertIn("navClassifiedFull", portal)
        self.assertIn("accountEntryLabel", portal)
        self.assertIn("accountChromeLabel", portal)
        self.assertIn("profileEntryLabel", portal)
        self.assertIn("PROFILE_ENTRY_LABEL", portal)
        self.assertIn("ACCOUNT_KEYS.has", portal)
        self.assertNotIn(">我的</el-button>", portal)
        self.assertNotIn(">资料</el-dropdown-item>", portal)
        self.assertNotIn("v-for=\"item in navAccount\"", portal)
        self.assertIn("ACCOUNT_KEYS", util)
        self.assertIn("accountChromeLabel", util)
        self.assertIn("PROFILE_ENTRY_LABEL", util)
        self.assertIn("头像下拉只留", util)
        self.assertIn("profileEntryLabel", account)
        self.assertIn("PROFILE_ENTRY_LABEL", account)
        self.assertNotIn("GROUP_PRIMARY", util)
        self.assertIn("groupAccountHubItems", account)
        self.assertIn("withAccountCenterRoutes", router)
        rail = (_FRONT / "components" / "PortalSideRail.vue").read_text(encoding="utf-8")
        self.assertTrue(rail)
        # 弹层必须挂 body；侧栏禁止 transform，否则遮罩盖全屏、对话框被箍成窄条，整页点不了
        self.assertIn("append-to-body", rail)
        self.assertIn("teleported", rail)
        self.assertNotIn("translateY(-50%)", rail)
        self.assertIn("portal-side-rail-edit", rail)
        profile = vue_src((_FRONT / "views" / "Profile.vue"))
        self.assertIn("profilePageCopy", profile)
        self.assertIn("profileCopy.title", profile)
        self.assertNotIn("faceCopy.title", profile)
        # 身份卡与顶栏同用昵称，禁止 realName 顶成两套
        self.assertIn("chromeDisplayName", profile)
        self.assertNotIn("extras?.realName", profile)
        self.assertIn('name="profile"', profile)
        self.assertIn('name="security"', profile)
        self.assertIn('name="devices"', profile)
        self.assertIn('name="other"', profile)
        self.assertIn("settings-tabs", profile)
        self.assertIn("data-account-face", profile)
        self.assertIn("accountFaceFromDelivered", profile)
        self.assertNotIn("points-mini", profile)
        main_js = (_FRONT / "main.js").read_text(encoding="utf-8")
        self.assertIn("accountFace.css", main_js)
        self.assertIn("--portal-skel-base", main_js)
        chrome = (_FRONT / "styles" / "chrome.css").read_text(encoding="utf-8")
        self.assertIn("--portal-skel-gradient", chrome)
        self.assertIn(".el-loading-spinner", chrome)
        self.assertIn("stroke: var(--portal-accent", chrome)
        skel = (_FRONT / "components" / "PageSkeleton.vue").read_text(encoding="utf-8")
        self.assertIn("--portal-skel-gradient", skel)
        self.assertNotIn("portal-accent-soft, #d7eef0) 0%", skel)
        self.assertIn("cardVoice.css", main_js)
        voice = (_FRONT / "styles" / "cardVoice.css").read_text(encoding="utf-8")
        for needle in ("catalog", "story", "board"):
            self.assertIn(f"[data-card-voice='{needle}']", voice)
        # catalog：价大字 + 短签芯片 + 促销条；禁止灰墙 detail-line
        self.assertIn(".short-tag", voice)
        self.assertIn(".promo-bar", voice)
        self.assertIn(".main-signal.price", voice)
        browse = (_FRONT / "views" / "user" / "ArchiveBrowse.vue").read_text(encoding="utf-8")
        self.assertIn("storyLeadOf", browse)
        self.assertIn("boardToneOf", browse)
        self.assertIn("cardShortTags", browse)
        self.assertIn('class="short-tags"', browse)
        self.assertIn('class="promo-bar"', browse)
        self.assertIn('class="more-hint"', browse)
        # catalog 不再把 cardPreviewFields 整表打成灰墙行
        self.assertIn("cardVoice === 'story' ? cardPreviewFields : []", browse)
        # 卡底：状态条与操作条拆开，禁止 tag/按钮同一 flex-wrap
        self.assertIn('class="card-foot"', browse)
        self.assertIn('class="card-meta"', browse)
        self.assertIn('class="card-acts"', browse)
        self.assertIn("act-primary", browse)
        self.assertIn(
            "surface-shelfgrid .card-acts",
            browse.replace("\n", " "),
        )
        # 卡底口径铺开到五个用户页：状态条（card-meta）与操作条（card-acts）拆开，
        # 禁止各自再造一套 .row / .acts 混装状态标签与按钮
        self.assertIn(".card-foot", voice)
        self.assertIn(".card-meta", voice)
        self.assertIn(".card-acts", voice)
        for name in (
            "MyOrders.vue",
            "MyReservations.vue",
            "MyTickets.vue",
            "PeerTickets.vue",
            "MyFavorites.vue",
        ):
            page = (_FRONT / "views" / "user" / name).read_text(encoding="utf-8")
            self.assertIn('class="card-foot"', page, name)
            self.assertIn('class="card-acts"', page, name)
            self.assertNotIn('class="row"', page, name)
            self.assertNotIn('class="acts"', page, name)
        for name in ("MyTickets.vue", "PeerTickets.vue"):
            page = (_FRONT / "views" / "user" / name).read_text(encoding="utf-8")
            self.assertIn('class="card-meta"', page, name)
        tone = (_FRONT / "utils" / "statusTone.js").read_text(encoding="utf-8")
        self.assertIn("reserveTone", tone)
        chip = (_FRONT / "components" / "StatusChip.vue").read_text(encoding="utf-8")
        self.assertIn("var(--portal-accent", chip)
        self.assertNotIn("#0284c7", chip)
        faces = (_FRONT / "styles" / "accountFace.css").read_text(encoding="utf-8")
        for needle in ("stall", "member", "reader", "desk", "inbox", "service"):
            self.assertIn(f"[data-account-face='{needle}']", faces)
        # 会员/票夹深底须压过 scoped `.card` 白底，否则完善度近白字落白卡
        self.assertIn("[data-account-face='member'] .card.af-identity", faces)
        self.assertIn("[data-account-face='showcard'] .card.af-identity", faces)
        profile_css = vue_src((_FRONT / "views" / "Profile.vue"))
        self.assertIn("complete-row strong", profile_css)


if __name__ == "__main__":
    unittest.main()
