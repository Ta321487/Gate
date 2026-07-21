"""Path B：交叉白名单与 accept 变严。"""

from app.bake.capabilities import resolve_accept, scan_out_of_scope
from app.bake.cross_paths import evaluate_cross_path, path_key_from_archetypes


def test_path_key_singles_and_pairs():
    assert path_key_from_archetypes(["ARCH-FLOW"]) == "F"
    assert path_key_from_archetypes(["ARCH-TRADE"]) == "T"
    assert path_key_from_archetypes(["ARCH-RESERVE"]) == "R"
    assert path_key_from_archetypes(["ARCH-FLOW", "ARCH-TRADE"]) == "FT"
    assert path_key_from_archetypes(["ARCH-FLOW", "ARCH-TRADE", "ARCH-RESERVE"]) == "FTR"


def test_single_path_named_domain_ok():
    key, entry, reason = evaluate_cross_path(
        ["ARCH-FLOW"], domain="DOM-LIBRARY", primary="ARCH-FLOW"
    )
    assert key == "F"
    assert entry and entry.defense_ready
    assert reason is None


def test_pair_cross_defense_ready():
    need = {
        "ARCH-FLOW": ["archive", "ticket_flow", "quota", "content", "org_users"],
        "ARCH-TRADE": ["archive", "order_lines", "quota", "content", "org_users"],
        "ARCH-RESERVE": ["archive", "slot_reserve", "content", "org_users"],
    }
    for arches, label in [
        (["ARCH-FLOW", "ARCH-TRADE"], "借用/申请+下单"),
        (["ARCH-FLOW", "ARCH-RESERVE"], "借用/申请+预约"),
        (["ARCH-TRADE", "ARCH-RESERVE"], "下单+预约"),
    ]:
        _key, entry, reason = evaluate_cross_path(arches, domain="DOM-GENERIC")
        assert entry and entry.defense_ready, label
        assert reason is None, (label, reason)
        caps: list[str] = []
        for a in arches:
            for c in need[a]:
                if c not in caps:
                    caps.append(c)
        d = resolve_accept(
            caps,
            "主要功能：演示交叉主路径。",
            has_domain_overlay=True,
            has_baseline_runtime=True,
            archetypes=arches,
            domain="DOM-GENERIC",
            primary_archetype=arches[0],
        )
        assert d["accept"] == "full", (label, d)


def test_triple_cross_not_defense_ready():
    key, entry, reason = evaluate_cross_path(
        ["ARCH-RESERVE", "ARCH-TRADE", "ARCH-FLOW"],
        domain="DOM-GENERIC",
    )
    assert key == "FTR"
    assert entry and not entry.defense_ready
    assert reason and ("三合一" in reason or "全文" in reason or "裁成" in reason)

def test_oos_rejects_not_degraded():
    text = "二手商城。主要功能：购物车下单；微信支付与支付宝对接。"
    assert "真实第三方支付" in scan_out_of_scope(text)
    d = resolve_accept(
        ["archive", "order_lines", "quota", "content", "org_users"],
        text,
        has_domain_overlay=True,
        has_baseline_runtime=True,
        archetypes=["ARCH-TRADE"],
        domain="DOM-SHOP",
        primary_archetype="ARCH-TRADE",
    )
    assert d["accept"] == "reject"
    assert d["out_of_mvp_signals"]


def test_library_roles_no_reader_user_dup():
    """单域图书：Spec 角色不得同时出现 reader 与 user（读者）。"""
    from app.bake.catalog import build_spec
    from app.bake.themes import default_theme

    s = build_spec(
        "图书借阅系统",
        "ARCH-FLOW",
        "DOM-LIBRARY",
        default_theme("DOM-LIBRARY"),
        False,
        "keyword",
        0.8,
        hits=[],
        proposal={"excerpt": "主要功能：借阅"},
        archetypes=["ARCH-FLOW"],
    )
    roles = s.get("roles") or []
    assert "user" in roles
    assert "reader" not in roles
    assert "admin" in roles


def test_merge_llm_cannot_drop_trade_for_library_skin():
    """图示问题：LLM 荐 LIBRARY 时不得丢掉关键词的二手下单路径。"""
    from app.bake.catalog import MatchResult, merge_llm_match

    kw = MatchResult(
        title="校园图书借阅与二手交易系统",
        archetype="ARCH-TRADE",
        domain="DOM-GENERIC",
        confidence=0.9,
        hits=["借阅", "购物车"],
        text_excerpt="",
        archetypes=["ARCH-TRADE", "ARCH-FLOW"],
        keyword_arch="ARCH-TRADE",
        keyword_domain="DOM-GENERIC",
    )
    merged = merge_llm_match(
        kw,
        {
            "archetype": "ARCH-FLOW",
            "domain": "DOM-LIBRARY",
            "confidence": 0.77,
            "rationale": "主路径借阅审核",
            "slug": "library_trade",
        },
    )
    assert merged is not None
    assert merged.domain == "DOM-GENERIC"
    assert "ARCH-FLOW" in (merged.archetypes or [])
    assert "ARCH-TRADE" in (merged.archetypes or [])


def test_match_keeps_borrow_and_shop_union():
    """借阅+二手不得落成纯商城（曾丢掉审核流）。"""
    from app.bake.catalog import match_text

    m = match_text(
        "校园综合小平台。主要功能：图书借阅申请与归还；二手商品浏览、加入购物车并提交订单；公告。"
    )
    assert m.domain == "DOM-GENERIC"
    assert "ARCH-FLOW" in (m.archetypes or [])
    assert "ARCH-TRADE" in (m.archetypes or [])


def test_match_keeps_borrow_and_reserve_union():
    from app.bake.catalog import match_text

    m = match_text(
        "图书馆服务系统。主要功能：图书借阅；图书馆座位分时预约占坑；约满不可再约；公告。"
    )
    assert m.domain == "DOM-GENERIC"
    assert "ARCH-FLOW" in (m.archetypes or [])
    assert "ARCH-RESERVE" in (m.archetypes or [])


def test_match_keeps_trade_and_reserve_union():
    from app.bake.catalog import match_text

    m = match_text(
        "校园服务。主要功能：会议室分时预约；另设小卖部购物车下单；无真支付。"
    )
    assert "ARCH-TRADE" in (m.archetypes or [])
    assert "ARCH-RESERVE" in (m.archetypes or [])
    # 无「宾馆/酒店」词时走通用交叉壳
    assert m.domain == "DOM-GENERIC"
