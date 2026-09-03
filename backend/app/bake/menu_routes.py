"""菜单 key ↔ 路径 ↔ 有效路由：拦导航 404（结构性），不拦空列表。

与骨架 ``frontend/src/utils/menuRoutes.js`` 必须同表；改一侧必改另一侧。
"""

from __future__ import annotations

from typing import Any

# 门户：menu key → path（与 PortalLayout / PortalHome 一致）
USER_MENU_PATHS: dict[str, str] = {
    "home": "/home",
    "archive": "/archive",
    "my_archive": "/my-archive",
    "my_tickets": "/tickets",
    "peer_tickets": "/peer-tickets",
    "content": "/notices",
    "guestbook": "/guestbook",
    "ai_assistant": "/ai-assistant",
    "exam_papers": "/exam/papers",
    "exam_attempts": "/exam/attempts",
    "exam_practice": "/exam/practice",
    "exam_rank": "/exam/rank",
    "exam_wrongbook": "/exam/wrongbook",
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
    "order_reviews": "/order-reviews",
    "addresses": "/addresses",
    "my_reservations": "/reservations",
    "slots": "/slots",
    "week_calendar": "/week",
    "messages": "/messages",
}

# 管理端：menu key → path（与 AdminLayout 一致）
ADMIN_MENU_PATHS: dict[str, str] = {
    "dashboard": "/admin/dashboard",
    "messages": "/admin/messages",
    "ticket_pending": "/admin/tickets",
    "ticket_records": "/admin/ticket-records",
    "users": "/admin/users",
    "content": "/admin/notices",
    "guestbook": "/admin/guestbook",
    "ai_knowledge": "/admin/ai-knowledge",
    "exam_questions": "/admin/exam/questions",
    "exam_papers": "/admin/exam/papers",
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
    "e_sign_admin": "/admin/e-sign",
    "archive_logs": "/admin/archive-logs",
    "lookup_site": "/admin/sites",
    "lookup_type": "/admin/types",
    "archive": "/admin/archive",
    "category": "/admin/categories",
    "deadline": "/admin/overdue",
    "coupons": "/admin/coupons",
    "orders": "/admin/orders",
    "order_reviews": "/admin/order-reviews",
    "reservations": "/admin/reservations",
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
            }
        )
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
    if "e_sign" in cap_set:
        paths.update({"/e-sign", "/admin/e-sign"})
    if "favorites" in cap_set:
        paths.add("/favorites")
    if "dm" in cap_set:
        paths.add("/dm")
    if "browse_history" in cap_set:
        paths.add("/browse-history")
    if "coupon" in cap_set:
        paths.update({"/coupons", "/admin/coupons"})
    if "order_review" in cap_set:
        paths.update({"/order-reviews", "/admin/order-reviews"})
    if "archive_log" in cap_set:
        paths.add("/admin/archive-logs")

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
