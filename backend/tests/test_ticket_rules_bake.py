# -*- coding: utf-8 -*-
"""工厂写参：生侧无 sys_config，规则进 thesis.ticket-*。"""

from __future__ import annotations

from app.bake.engine_bake import _patch_thesis_yml
from app.bake.features.guestbook import GUESTBOOK_CAP, guestbook_wanted
from app.bake.ticket_rules import rules_for


def test_library_rules_baked_into_yml():
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
    out = _patch_thesis_yml(base, "DOM-LIBRARY", spec)
    assert "ticket-loan-days: 30" in out
    assert "ticket-max-active: 5" in out
    assert "ticket-fine-per-day: 0.5" in out
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
