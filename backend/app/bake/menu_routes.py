"""菜单 key ↔ 路径 ↔ 有效路由：拦导航 404（结构性），不拦空列表。

与骨架 ``frontend/src/utils/menuRoutes.js`` 必须同表；改一侧必改另一侧。
"""

from __future__ import annotations

from typing import Any

# 门户：menu key → path（与 PortalLayout / PortalHome / menuRoutes.js 一致）
USER_MENU_PATHS: dict[str, str] = {
    "home": "/home",
    "archive": "/archive",
    "my_archive": "/my-archive",
    "my_tickets": "/tickets",
    "peer_tickets": "/peer-tickets",
    "content": "/notices",
    "guestbook": "/guestbook",
    "book_suggest": "/book-suggest",
    "parcel_ship": "/parcel-ship",
    "ai_assistant": "/ai-assistant",
    "exam_papers": "/exam/papers",
    "exam_attempts": "/exam/attempts",
    "exam_practice": "/exam/practice",
    "exam_rank": "/exam/rank",
    "exam_wrongbook": "/exam/wrongbook",
    "grade_scores_mine": "/grade/scores",
    "fund_publicity_mine": "/fund/publicity",
    "survey_forms": "/survey/forms",
    "survey_mine": "/survey/mine",
    "vote_campaigns": "/vote/campaigns",
    "vote_mine": "/vote/mine",
    "doc_browse": "/doc/browse",
    "doc_mine": "/doc/mine",
    "tb_account": "/tb/account",
    "tb_ledger": "/tb/ledger",
    "seat_shows": "/seats/shows",
    "e_sign_mine": "/e-sign",
    "dm": "/dm",
    "profile": "/profile",
    "favorites": "/favorites",
    "browse_history": "/browse-history",
    "coupons": "/coupons",
    "cart": "/cart",
    "my_orders": "/orders",
    "my_consigns": "/consigns",
    "my_loss": "/loss",
    "my_shots": "/shots",
    "my_stay": "/stay",
    "my_buybacks": "/buybacks",
    "my_lessons": "/lessons",
    "my_digital": "/digital",
    "my_permits": "/permits",
    "order_reviews": "/order-reviews",
    "addresses": "/addresses",
    "my_reservations": "/reservations",
    "slots": "/slots",
    "week_calendar": "/week",
    "balance_mine": "/balance/mine",
    "balance_ledger_mine": "/balance/ledger",
    "occupy_mine": "/occupy/mine",
    "messages": "/messages",
}

# 管理端：menu key → path（与 AdminLayout / menuRoutes.js 一致）
ADMIN_MENU_PATHS: dict[str, str] = {
    "dashboard": "/admin/dashboard",
    "messages": "/admin/messages",
    "ticket_pending": "/admin/tickets",
    "ticket_records": "/admin/ticket-records",
    "users": "/admin/users",
    "content": "/admin/notices",
    "guestbook": "/admin/guestbook",
    "item_comments": "/admin/item-comments",
    "content_reports": "/admin/content-reports",
    "audit_logs": "/admin/audit-logs",
    "message_templates": "/admin/message-templates",
    "staff_roster": "/admin/staff-roster",
    "book_suggest": "/admin/book-suggest",
    "parcel_shelf": "/admin/parcel-shelf",
    "parcel_ship": "/admin/parcel-ship",
    "equipment_dict": "/admin/equipment-dict",
    "ai_knowledge": "/admin/ai-knowledge",
    "exam_questions": "/admin/exam/questions",
    "exam_papers": "/admin/exam/papers",
    "exam_mark": "/admin/exam/mark",
    "survey_forms": "/admin/survey/forms",
    "survey_stats": "/admin/survey/stats",
    "vote_candidates": "/admin/vote/candidates",
    "vote_results": "/admin/vote/results",
    "doc_files": "/admin/doc/files",
    "doc_logs": "/admin/doc/logs",
    "tb_accounts": "/admin/tb/accounts",
    "tb_ledger_admin": "/admin/tb/ledger",
    "stock_moves": "/admin/stock/moves",
    "stock_ledger": "/admin/stock/ledger",
    "balance_accounts": "/admin/balance/accounts",
    "balance_ledger_admin": "/admin/balance/ledger",
    "occupy_admin": "/admin/occupy",
    "material_checklist": "/admin/material/checklist",
    "apply_blacklist": "/admin/apply/blacklist",
    "lost_clues": "/admin/lost/clues",
    "e_sign_admin": "/admin/e-sign",
    "grade_scores_admin": "/admin/grade/scores",
    "fund_publicity_admin": "/admin/fund/publicity",
    "fund_disburse_admin": "/admin/fund/disburse",
    "listing_deal_admin": "/admin/listing/deal",
    "archive_logs": "/admin/archive-logs",
    "lookup_site": "/admin/sites",
    "lookup_type": "/admin/types",
    "archive": "/admin/archive",
    "category": "/admin/categories",
    "deadline": "/admin/overdue",
    "coupons": "/admin/coupons",
    "delivery_slots": "/admin/delivery/slots",
    "price_spans": "/admin/delivery/spans",
    "purchase_permits": "/admin/purchase-permits",
    "group_campaigns": "/admin/group-buys",
    "blind_pools": "/admin/blind-boxes",
    "consigns": "/admin/consigns",
    "loss_claims": "/admin/loss",
    "shoot_bundles": "/admin/shoot-bundles",
    "shoot_files": "/admin/shoot-files",
    "care_options": "/admin/care-options",
    "stay_logs": "/admin/stay-logs",
    "buybacks": "/admin/buybacks",
    "buyback_slots": "/admin/buyback-slots",
    "lesson_packs": "/admin/lesson-packs",
    "lesson_uses": "/admin/lesson-uses",
    "rental_inspect": "/admin/rental-inspect",
    "room_board": "/admin/room-board",
    "front_checkin": "/admin/front-checkin",
    "front_checkout": "/admin/front-checkout",
    "clean_tasks": "/admin/clean-tasks",
    "digital_codes": "/admin/digital-codes",
    "line_specs": "/admin/line-specs",
    "orders": "/admin/orders",
    "order_reviews": "/admin/order-reviews",
    "reservations": "/admin/reservations",
    "dm": "/admin/dm",
}

# 壳基线路由（镜像 router/index.js pickRoutes 主干；不含登录等）
_BASE_ALWAYS = frozenset(
    {
        "/login",
        "/register",
        "/profile",
        "/notices",
        "/admin/dashboard",
        "/admin/users",
        "/admin/notices",
        "/admin/profile",
        "/admin/messages",
        "/messages",
        "/home",
        "/staff",
        "/staff/tickets",
        "/staff/orders",
        "/staff/slots",
    }
)

_TICKET_SHELL = frozenset(
    {
        "/tickets",
        "/admin/tickets",
        "/admin/ticket-records",
        "/admin/sites",
        "/admin/types",
    }
)

_ARCHIVE_TICKET_SHELL = frozenset(
    {
        "/archive",
        "/tickets",
        "/peer-tickets",
        "/week",
        "/admin/archive",
        "/admin/categories",
        "/admin/tickets",
        "/admin/ticket-records",
        "/admin/overdue",
    }
)

_ORDER_SHELL = frozenset(
    {
        "/archive",
        "/cart",
        "/orders",
        "/admin/archive",
        "/admin/categories",
        "/admin/orders",
    }
)

_SLOT_SHELL = frozenset(
    {
        "/archive",
        "/slots",
        "/reservations",
        "/orders",
        "/admin/archive",
        "/admin/categories",
        "/admin/reservations",
        "/admin/orders",
    }
)

_ARCHIVE_ONLY_SHELL = frozenset(
    {
        "/archive",
        "/admin/archive",
        "/admin/categories",
    }
)


def shell_kind(capabilities: list[str] | None) -> str:
    """与前端 pickRoutes 同一判定（含 GENERIC 多主路径）。"""
    caps = set(capabilities or [])
    has = caps.__contains__
    ticket = has("ticket_flow") and has("archive")
    order = has("order_lines") and has("archive")
    slot = has("slot_reserve") and has("archive")
    # 多主路径：单据壳 + 预约/订单（archiveTicketRoutes + withExtraBizRoutes）
    if ticket and (order or slot):
        return "archive_ticket_multi"
    if has("ticket_flow") and not has("archive"):
        return "ticket"
    if (
        has("ticket_flow")
        and has("archive")
        and not has("order_lines")
        and not has("slot_reserve")
    ):
        return "archive_ticket"
    if has("order_lines") and has("archive") and not has("ticket_flow") and not has("slot_reserve"):
        return "order"
    if has("slot_reserve") and has("archive") and not has("ticket_flow"):
        return "slot"
    if has("archive") and not has("ticket_flow") and not has("order_lines") and not has("slot_reserve"):
        return "archive_only"
    return "baseline"


def effective_paths(
    capabilities: list[str] | None,
    *,
    traits: dict[str, Any] | None = None,
    schema: dict[str, Any] | None = None,
) -> set[str]:
    """本包实际会挂上的路径集合（结构性；不含动态 :id）。"""
    caps = list(capabilities or [])
    if schema and isinstance(schema.get("capabilities"), list) and not caps:
        caps = [str(c) for c in schema["capabilities"]]
    cap_set = set(caps)
    traits = traits or {}
    kind = shell_kind(caps)
    paths: set[str] = set(_BASE_ALWAYS)

    if kind == "ticket":
        paths |= _TICKET_SHELL
    elif kind in ("archive_ticket", "archive_ticket_multi"):
        paths |= _ARCHIVE_TICKET_SHELL
        if kind == "archive_ticket_multi":
            if "order_lines" in cap_set:
                paths.update({"/cart", "/orders", "/admin/orders"})
                if traits.get("addressBook"):
                    paths.add("/addresses")
            if "slot_reserve" in cap_set:
                paths.update({"/slots", "/reservations", "/admin/reservations"})
    elif kind == "order":
        paths |= _ORDER_SHELL
        # 订单壳（FOOD/SHOP/交易 GENERIC）菜单必有地址簿；勿依赖 traits 是否已写入 spec
        paths.add("/addresses")
    elif kind == "slot":
        paths |= _SLOT_SHELL
        # 预约壳可叠订单（TRADE+RESERVE）；地址仅 addressBook
        if "order_lines" in cap_set and traits.get("addressBook"):
            paths.add("/addresses")
            paths.add("/cart")
    elif kind == "archive_only":
        paths |= _ARCHIVE_ONLY_SHELL
    else:
        # baseline：几乎无业务路由；菜单若仍挂业务键必炸
        pass

    # 能力叠加（与 with*Routes 对齐）
    if "guestbook" in cap_set:
        paths.update({"/guestbook", "/admin/guestbook"})
    if "item_comment" in cap_set:
        paths.add("/admin/item-comments")
    if "content_report" in cap_set:
        paths.add("/admin/content-reports")
    if "audit_log" in cap_set:
        paths.add("/admin/audit-logs")
    if "message_template" in cap_set:
        paths.add("/admin/message-templates")
    if "staff_roster" in cap_set:
        paths.add("/admin/staff-roster")
    if "book_suggest" in cap_set:
        paths.update({"/book-suggest", "/admin/book-suggest"})
    if "parcel_shelf" in cap_set:
        paths.add("/admin/parcel-shelf")
    if "parcel_ship" in cap_set:
        paths.update({"/parcel-ship", "/admin/parcel-ship"})
    if "room_equipment" in cap_set:
        paths.add("/admin/equipment-dict")
    if "ai_assistant" in cap_set:
        paths.update({"/ai-assistant", "/admin/ai-knowledge"})
    if "exam" in cap_set:
        paths.update(
            {
                "/exam/papers",
                "/exam/attempts",
                "/exam/practice",
                "/exam/rank",
                "/exam/wrongbook",
                "/admin/exam/questions",
                "/admin/exam/papers",
                "/admin/exam/mark",
            }
        )
    if (schema or {}).get("gradeScores"):
        paths.update({"/grade/scores", "/admin/grade/scores"})
    # 资助公示/发放旁路岛（DOM-FUND 域默认），与 withFundIslandRoutes 对齐
    if (schema or {}).get("fundIsland"):
        paths.update(
            {"/fund/publicity", "/admin/fund/publicity", "/admin/fund/disburse"}
        )
    # 房源成交台账（DOM-LISTING 域默认），与 withListingDealRoutes 对齐
    if (schema or {}).get("listingDeal"):
        paths.add("/admin/listing/deal")
    if "survey" in cap_set:
        paths.update(
            {
                "/survey/forms",
                "/survey/mine",
                "/admin/survey/forms",
                "/admin/survey/stats",
            }
        )
    if "vote" in cap_set:
        paths.update(
            {
                "/vote/campaigns",
                "/vote/mine",
                "/admin/vote/candidates",
                "/admin/vote/results",
            }
        )
    if "doclib" in cap_set:
        paths.update(
            {
                "/doc/browse",
                "/doc/mine",
                "/admin/doc/files",
                "/admin/doc/logs",
            }
        )
    if "timebank" in cap_set:
        paths.update(
            {
                "/tb/account",
                "/tb/ledger",
                "/admin/tb/accounts",
                "/admin/tb/ledger",
            }
        )
    if "seat_select" in cap_set:
        paths.update({"/seats/shows", "/seats/map"})
    if "stock_io" in cap_set:
        paths.update({"/admin/stock/moves", "/admin/stock/ledger"})
    if "balance_ledger" in cap_set:
        paths.update(
            {
                "/balance/mine",
                "/balance/ledger",
                "/admin/balance/accounts",
                "/admin/balance/ledger",
            }
        )
    if "occupy_span" in cap_set:
        paths.update({"/occupy/mine", "/admin/occupy"})
    if "material_check" in cap_set:
        paths.add("/admin/material/checklist")
    if isinstance(schema, dict) and schema.get("applyBlacklist"):
        paths.add("/admin/apply/blacklist")
    if "lost_clue" in cap_set:
        paths.add("/admin/lost/clues")
    if "e_sign" in cap_set:
        paths.update({"/e-sign", "/admin/e-sign"})
    if "favorites" in cap_set:
        paths.add("/favorites")
    if "dm" in cap_set:
        paths.update({"/dm", "/admin/dm"})
    if "browse_history" in cap_set:
        paths.add("/browse-history")
    if "coupon" in cap_set:
        paths.update({"/coupons", "/admin/coupons"})
    if "order_review" in cap_set:
        paths.update({"/order-reviews", "/admin/order-reviews"})
    if "archive_log" in cap_set:
        paths.add("/admin/archive-logs")
    # 能力岛菜单（与 frontend with*Routes 对齐）
    if "lesson_pack" in cap_set:
        paths.update({"/lessons", "/admin/lesson-packs", "/admin/lesson-uses"})
    if "buyback" in cap_set:
        paths.update({"/buybacks", "/admin/buybacks", "/admin/buyback-slots"})
    if "rental_bond" in cap_set:
        paths.add("/admin/rental-inspect")
    if "room_board" in cap_set:
        paths.add("/admin/room-board")
    if "front_desk" in cap_set:
        paths.update({"/admin/front-checkin", "/admin/front-checkout"})
    if "housekeeping" in cap_set or "venue_clean" in cap_set:
        paths.add("/admin/clean-tasks")
    if "digital_goods" in cap_set:
        paths.update({"/digital", "/admin/digital-codes"})
    if "boarding" in cap_set:
        paths.update({"/stay", "/admin/care-options", "/admin/stay-logs"})
    if "shoot" in cap_set:
        paths.update({"/shots", "/admin/shoot-bundles", "/admin/shoot-files"})
    if "weigh_sale" in cap_set:
        paths.update({"/loss", "/admin/loss"})
    if "consign" in cap_set:
        paths.update({"/consigns", "/admin/consigns"})
    if "line_custom" in cap_set:
        paths.add("/admin/line-specs")
    if "blind_box" in cap_set:
        paths.add("/admin/blind-boxes")
    if "group_buy" in cap_set:
        paths.add("/admin/group-buys")
    if "purchase_gate" in cap_set:
        paths.update({"/permits", "/admin/purchase-permits"})
    if "delivery_window" in cap_set:
        paths.update({"/admin/delivery/slots", "/admin/delivery/spans"})

    arch = ((schema or {}).get("entities") or {}).get("archive") or {}
    if isinstance(arch, dict) and arch.get("userPublish"):
        paths.add("/my-archive")

    return paths


def check_menu_routes_aligned(
    schema: dict[str, Any] | None,
    *,
    domain: str = "",
    capabilities: list[str] | None = None,
    traits: dict[str, Any] | None = None,
    proposal_text: str = "",
) -> list[str]:
    """返回问题列表；空 = 通过。"""
    issues: list[str] = []
    if not isinstance(schema, dict):
        return ["schema 缺失，无法校验菜单路由"]
    menus = schema.get("menus") if isinstance(schema.get("menus"), dict) else {}
    dom = (domain or str(schema.get("domain") or "")).strip()

    caps = capabilities
    if caps is None:
        raw = schema.get("capabilities")
        caps = [str(c) for c in raw] if isinstance(raw, list) else []
    if not caps and dom:
        from app.bake.domains import DOMAIN_CAPABILITIES
        from app.bake.features.proposal_caps import merge_proposal_capabilities

        caps = merge_proposal_capabilities(
            list(DOMAIN_CAPABILITIES.get(dom) or []),
            proposal_text or "",
            domain=dom,
        )

    trait_map = traits if isinstance(traits, dict) else None
    # bake 早期 spec.traits 常为空 dict，不能当成「无特征」
    if (not trait_map) and dom:
        from app.bake.domain_skin import traits_for_domain

        trait_map = traits_for_domain(dom)
    trait_map = trait_map or {}

    paths = effective_paths(caps, traits=trait_map, schema=schema)
    kind = shell_kind(caps)
    if kind == "baseline" and any(
        (menus.get("user") or []) or (menus.get("admin") or [])
    ):
        # 有业务菜单却落到 baseline 壳 → 几乎必 404
        issues.append(
            f"capabilities={caps} 落到 baseline 路由壳，业务菜单将 404；请检查能力组合"
        )

    for side, registry in (("user", USER_MENU_PATHS), ("admin", ADMIN_MENU_PATHS)):
        for item in menus.get(side) or []:
            if not isinstance(item, dict):
                continue
            key = str(item.get("key") or "").strip()
            if not key:
                continue
            path = registry.get(key)
            if not path:
                issues.append(f"菜单 key「{key}」({side}) 无路径注册表项（会静默丢导航或 404）")
                continue
            if path not in paths:
                issues.append(
                    f"菜单「{key}」→ {path} 不在本包有效路由内（壳={kind}），点击将进 404"
                )
    return issues


def assert_menu_routes_aligned(
    schema: dict[str, Any] | None,
    *,
    domain: str = "",
    capabilities: list[str] | None = None,
    traits: dict[str, Any] | None = None,
    proposal_text: str = "",
) -> None:
    issues = check_menu_routes_aligned(
        schema,
        domain=domain,
        capabilities=capabilities,
        traits=traits,
        proposal_text=proposal_text,
    )
    if issues:
        raise AssertionError("菜单/路由未对齐：\n- " + "\n- ".join(issues))
