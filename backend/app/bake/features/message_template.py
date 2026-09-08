"""站内消息模板 message_template：开题扫词才挂；无域默认。

总管维护模板（标题/正文占位符）；审单通过/驳回优先套模板发 sys_message；
无模板或未挂 cap 时保持现网硬编码文案。学生包写「站内消息」，不写演示短信。
"""

from __future__ import annotations

from typing import Any

from app.bake.proposal_lexicon import keyword_mentioned

MESSAGE_TEMPLATE_CAP = "message_template"

_TERMS = ("消息模板", "通知模板", "站内信模板", "站内消息模板")


def scan_message_template(text: str) -> bool:
    raw = text or ""
    return any(keyword_mentioned(raw, kw, ignore_contrast=True) for kw in _TERMS)


def merge_message_template_capabilities(
    caps: list[str] | None,
    proposal_text: str = "",
    *,
    domain: str | None = None,
) -> list[str]:
    del domain
    out = list(caps or [])
    if MESSAGE_TEMPLATE_CAP in out:
        return out
    if not scan_message_template(proposal_text or ""):
        return out
    out.append(MESSAGE_TEMPLATE_CAP)
    return out


def attach_message_template_menus(schema: dict[str, Any]) -> None:
    from app.bake.schema.menu_utils import ensure_menu

    menus = schema.setdefault("menus", {})
    admin = menus.setdefault("admin", [])
    ensure_menu(
        admin,
        "message_templates",
        {"key": "message_templates", "label": "消息模板", "superOnly": True},
        before_key="audit_logs",
    )
    labels = schema.setdefault("labels", {})
    labels.setdefault("messageTemplatesPageTitle", "消息模板")
    labels.setdefault(
        "messageTemplatesPageLead",
        "维护站内消息标题与正文模板；支持占位符 {{subject}} {{note}} {{passCode}}。"
        "审核通过/驳回时优先使用模板；未配置则用系统默认文案。",
    )
    ents = schema.setdefault("entities", {})
    ents.setdefault(
        "messageTemplate",
        {"key": "message_template", "label": "消息模板", "labelPlural": "消息模板"},
    )


def apply_message_template_to_spec(
    spec: dict[str, Any], proposal_text: str = ""
) -> dict[str, Any]:
    text = proposal_text or ""
    caps = merge_message_template_capabilities(
        list(spec.get("capabilities") or []),
        text,
        domain=spec.get("domain"),
    )
    spec = {**spec, "capabilities": caps}
    schema = dict(spec.get("schema") or {})
    schema["capabilities"] = caps
    if MESSAGE_TEMPLATE_CAP in caps:
        attach_message_template_menus(schema)
        from app.bake.gate_contracts import merge_message_template_gate

        gate = dict(spec.get("gate") or {})
        spec["gate"] = merge_message_template_gate(gate, caps)
        features = list(spec.get("features") or [])
        names = {f.get("name") for f in features if isinstance(f, dict)}
        if "消息模板" not in names:
            features.append({"name": "消息模板", "status": "module"})
        spec["features"] = features
    spec["schema"] = schema
    return spec
