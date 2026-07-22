"""Path B：交叉白名单与 accept 变严。"""

import re

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


def test_match_ignores_negated_pay_keyword():
    """「不扩展真实支付」不得单独抬升交易流。"""
    from app.bake.catalog import match_text

    m = match_text(
        "仓储物资申领系统。主要功能：物资目录；提交申领；库管审核出库；"
        "范围控制：不扩展真实支付与重型盘点设备对接。"
    )
    assert "ARCH-TRADE" not in (m.archetypes or [])
    assert "ARCH-FLOW" in (m.archetypes or [])


def test_match_media_ignores_oos_pay_and_keeps_skin():
    """关键问题里顺口提支付，不得抬 TRADE 并顶掉影视综皮。"""
    from pathlib import Path

    from app.bake.catalog import match_text

    path = Path(__file__).resolve().parents[2] / "data/samples/校园影视资源点播系统开题.txt"
    if not path.is_file():
        path = Path("d:/graduate_factory_v3/data/samples/校园影视资源点播系统开题.txt")
    text = path.read_text(encoding="utf-8")
    m = match_text(text, path.name)
    assert m.domain == "DOM-MEDIA"
    assert "ARCH-TRADE" not in (m.archetypes or [])
    assert m.archetype in ("ARCH-CONTENT", "ARCH-FLOW")
    assert m.confidence < 0.9


def test_match_material_claim_opening_to_asset():
    """仓储物资申领开题 → 物资域；角色为库管而非商城骑手。"""
    from pathlib import Path

    from app.bake.catalog import build_spec, match_text

    text = Path("d:/graduate_factory_v3/data/samples/仓储物资申领开题.txt").read_text(
        encoding="utf-8"
    )
    m = match_text(text, "仓储物资申领开题.txt")
    assert m.domain == "DOM-ASSET"
    assert "ARCH-TRADE" not in (m.archetypes or [])
    assert "ARCH-FLOW" in (m.archetypes or []) or "ARCH-STOCK" in (m.archetypes or [])

    spec = build_spec(
        m.title,
        m.archetype,
        m.domain,
        "asset-olive",
        False,
        "keyword",
        m.confidence,
        hits=m.hits,
        archetypes=m.archetypes,
    )
    roles = spec.get("roles") or []
    assert "order_clerk" not in roles
    assert "rider" not in roles
    assert "storekeeper" in roles
    ents = spec.get("entities") or []
    assert all(re.fullmatch(r"[A-Za-z][A-Za-z0-9]*", e) for e in ents)
    assert "Asset" in ents
    assert not any("申领" in e or "仓储" in e for e in ents)


def test_generic_shell_entities_are_english():
    from app.bake.archetype_shells import apply_generic_shell

    spec = apply_generic_shell(
        {
            "title": "基于 Spring Boot 的高校仓储物资申领管理系统的设计与实现",
            "domain": "DOM-GENERIC",
            "archetype": "ARCH-FLOW",
            "archetypes": ["ARCH-FLOW"],
        }
    )
    assert "Item" in (spec.get("entities") or [])
    assert not any("\u4e00" <= c <= "\u9fff" for e in (spec["entities"] or []) for c in e)


def test_generic_cross_staff_posts_union_no_rider():
    """交叉壳按能力并集挂 clerk，不默认塞配送员。"""
    from app.bake.staff_posts import staff_posts_for_domain

    posts = staff_posts_for_domain(
        "DOM-GENERIC", archetypes=["ARCH-FLOW", "ARCH-TRADE"]
    )
    ids = [p["id"] for p in posts]
    assert ids == ["clerk", "order_clerk"]
    assert all(p.get("kind") == "clerk" for p in posts)

    trade_only = staff_posts_for_domain("DOM-GENERIC", archetype="ARCH-TRADE")
    assert [p["id"] for p in trade_only] == ["order_clerk"]
    assert "rider" not in [p["id"] for p in trade_only]


def test_build_spec_generic_cross_keeps_staff_posts():
    """apply_generic_shell 不得冲掉交叉岗位表。"""
    from app.bake.catalog import build_spec, match_text

    m = match_text(
        "校园综合小平台。主要功能：图书借阅申请与归还；"
        "二手商品浏览、加入购物车并提交订单；公告。"
    )
    assert m.domain == "DOM-GENERIC"
    spec = build_spec(
        m.title,
        m.archetype,
        m.domain,
        "ink-blue",
        False,
        "keyword",
        m.confidence,
        hits=m.hits,
        archetypes=m.archetypes,
    )
    posts = ((spec.get("schema") or {}).get("roles") or {}).get("staff_posts") or []
    assert [p.get("id") for p in posts] == ["clerk", "order_clerk"]
    assert "rider" not in (spec.get("roles") or [])


def test_cross_sql_seeds_all_clerks():
    """交叉多 clerk：首岗绑 subadmin，其余各一演示账号。"""
    from app.bake.engine import domain_sql

    sql = domain_sql(
        "DOM-GENERIC", "t", archetypes=["ARCH-FLOW", "ARCH-TRADE"]
    )
    assert "staff_post='clerk'" in sql
    assert "VALUES ('order_clerk'" in sql
    assert "rider" not in sql


def test_announce_publish_does_not_force_content_arch():
    """公告发布不得单独抬升内容流。"""
    from app.bake.catalog import match_text

    m = match_text(
        "仓储物资申领。主要功能：提交申领；库管审核出库；仓储公告的发布与查阅。"
    )
    assert "ARCH-CONTENT" not in (m.archetypes or [])
    assert "ARCH-FLOW" in (m.archetypes or [])
