"""操作审计日志 audit_log：开题扫词才挂；无域默认。

管理端关键写操作（审单/改档案/改用户）与登录写入 sys_audit_log；
总管可查。仅扫「登录日志」时 loginOnly=true，只记登录。
"""

from __future__ import annotations

from typing import Any

from app.bake.proposal_lexicon import keyword_mentioned

AUDIT_LOG_CAP = "audit_log"

_FULL_TERMS = ("操作日志", "审计日志", "操作记录")
_LOGIN_TERMS = ("登录日志",)


def scan_audit_full(text: str) -> bool:
    raw = text or ""
    return any(keyword_mentioned(raw, kw, ignore_contrast=True) for kw in _FULL_TERMS)


def scan_audit_login(text: str) -> bool:
    raw = text or ""
    return any(keyword_mentioned(raw, kw, ignore_contrast=True) for kw in _LOGIN_TERMS)


def scan_audit_log(text: str) -> bool:
    return scan_audit_full(text) or scan_audit_login(text)


def audit_login_only(proposal_text: str = "") -> bool:
    """仅写登录日志、未写操作/审计日志 → 只记登录。"""
    return scan_audit_login(proposal_text) and not scan_audit_full(proposal_text)


def merge_audit_log_capabilities(
    caps: list[str] | None,
    proposal_text: str = "",
    *,
    domain: str | None = None,
) -> list[str]:
    del domain  # 横切能力，不限域
    out = list(caps or [])
    if AUDIT_LOG_CAP in out:
        return out
    if not scan_audit_log(proposal_text or ""):
        return out
    out.append(AUDIT_LOG_CAP)
    return out


def attach_audit_log_menus(schema: dict[str, Any]) -> None:
    from app.bake.schema.menu_utils import ensure_menu

    menus = schema.setdefault("menus", {})
    admin = menus.setdefault("admin", [])
    ensure_menu(
        admin,
        "audit_logs",
        {"key": "audit_logs", "label": "操作日志", "superOnly": True},
        before_key="guestbook",
    )
    labels = schema.setdefault("labels", {})
    labels.setdefault("auditLogsPageTitle", "操作日志")
    labels.setdefault(
        "auditLogsPageLead",
        "查看管理端关键写操作与登录记录（时间、操作者、动作、对象）。",
    )
    ents = schema.setdefault("entities", {})
    ents.setdefault(
        "auditLog",
        {"key": "audit_log", "label": "操作日志", "labelPlural": "操作日志"},
    )


def apply_audit_log_to_spec(spec: dict[str, Any], proposal_text: str = "") -> dict[str, Any]:
    text = proposal_text or ""
    caps = merge_audit_log_capabilities(
        list(spec.get("capabilities") or []),
        text,
        domain=spec.get("domain"),
    )
    spec = {**spec, "capabilities": caps}
    schema = dict(spec.get("schema") or {})
    schema["capabilities"] = caps

    if AUDIT_LOG_CAP in caps:
        attach_audit_log_menus(schema)
        login_only = audit_login_only(text)
        schema["auditLoginOnly"] = login_only
        from app.bake.gate_contracts import merge_audit_log_gate

        gate = dict(spec.get("gate") or {})
        spec["gate"] = merge_audit_log_gate(gate, caps)

        features = list(spec.get("features") or [])
        names = {f.get("name") for f in features if isinstance(f, dict)}
        feat_name = "登录日志" if login_only else "操作日志"
        if feat_name not in names and "操作日志" not in names and "登录日志" not in names:
            features.append({"name": feat_name, "status": "module"})
        spec["features"] = features

    spec["schema"] = schema
    return spec
