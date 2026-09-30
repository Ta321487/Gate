# -*- coding: utf-8 -*-
"""工厂写参：生侧无 sys_config；单据策略进生成的 config/TicketPolicy.java。"""

from __future__ import annotations

from app.bake.engine_bake import _patch_thesis_yml
from app.bake.features.guestbook import GUESTBOOK_CAP, guestbook_wanted
from app.bake.ticket_policy import collect, render
from app.bake.ticket_rules import rules_for


def test_library_rules_baked_into_policy_class():
    base = "thesis:\n  title: demo\n  register-role: reader\n"
    spec = {
        "capabilities": ["archive", "ticket_flow", "quota", "content", "org_users"],
        "schema": {
            "capabilities": ["archive", "ticket_flow", "quota", "content", "org_users"],
            "entities": {
                "ticket": {"table": "borrow", "useQuota": True, "useDeadline": True},
                "archive": {},
            },
            "roles": {"user": {"id": "reader"}},
        },
    }
    policy = collect("DOM-LIBRARY", spec)
    assert policy["LOAN_DAYS"] == 30
    assert policy["MAX_ACTIVE"] == 5
    assert policy["FINE_PER_DAY"] == 0.5
    java = render(policy)
    assert "public static final int LOAN_DAYS = 30;" in java
    assert "public static final int MAX_ACTIVE = 5;" in java
    assert "public static final double FINE_PER_DAY = 0.5;" in java
    assert "class TicketPolicy" in java
    # 单据整段不再进 yml
    out = _patch_thesis_yml(base, "DOM-LIBRARY", spec)
    assert "ticket-loan-days" not in out
    assert "ticket-" not in out
    assert "sys_config" not in out


def test_blog_has_no_ticket_rules_but_guestbook_default():
    assert rules_for("DOM-BLOG") == {}
    assert guestbook_wanted(domain="DOM-BLOG", capabilities=["archive", "favorites"])
    assert GUESTBOOK_CAP


def test_sql_templates_have_no_sys_config():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1] / "app" / "bake" / "sql"
    hits = []
    for f in list((root / "templates").glob("DOM-*.sql")) + list(root.glob("DOM-*.sql")):
        if "sys_config" in f.read_text(encoding="utf-8"):
            hits.append(f.name)
    assert hits == []


def test_skeleton_policy_matches_renderer():
    """三棵树骨架的 TicketPolicy 必须与渲染器默认版逐字一致（防止手改漂移）。"""
    from pathlib import Path

    from app.bake.ticket_policy import POLICY_REL, render

    repo = Path(__file__).resolve().parents[2]
    expected = render({})
    for tag, tree in (
        ("baseline", "skeletons/baseline"),
        ("mybatis", "skeletons/overlays/persistence-mybatis"),
        ("jpa", "skeletons/overlays/persistence-jpa"),
    ):
        text = (repo / tree / POLICY_REL).read_text(encoding="utf-8")
        assert text == expected, f"{tag} 骨架 TicketPolicy 与渲染器不一致"


def test_binder_reads_ticket_policy_not_yml():
    """binder 不再持有 thesis.ticket-* 占位，改读 TicketPolicy 常量。"""
    from pathlib import Path

    repo = Path(__file__).resolve().parents[2]
    rel = "backend/src/main/java/com/thesis/config/DomainRuntimeBinder.java"
    for tag, tree in (
        ("baseline", "skeletons/baseline"),
        ("mybatis", "skeletons/overlays/persistence-mybatis"),
        ("jpa", "skeletons/overlays/persistence-jpa"),
    ):
        text = (repo / tree / rel).read_text(encoding="utf-8")
        assert "thesis.ticket-" not in text, tag
        assert "thesis.enable-ticket" not in text, tag
        assert "TicketPolicy." in text, tag


def test_thesis_yml_keeps_single_shared_quota_key():
    """单据域/交易域 yml 里 use-quota 只能出现一次（防与 order_lines 块重复发键），且无票据键。"""
    from app.bake.catalog import DOMAINS
    from app.bake.domains import DOMAIN_CAPABILITIES

    text = "thesis:\n  title: 校园二手交易平台\n"
    for dom in ("DOM-SHOP", "DOM-LIBRARY"):
        out = _patch_thesis_yml(
            text,
            dom,
            {
                "title": "校园二手交易平台",
                "capabilities": list(DOMAIN_CAPABILITIES.get(dom) or []),
                "runtime": dict((DOMAINS.get(dom) or {}).get("runtime") or {}),
                "schema": {},
            },
        )
        assert out.count("use-quota") == 1, dom
        assert "ticket" not in out, dom
