"""时间银行（timebank）：时长账户、流水加减、核销扣减（C-14）。"""

from __future__ import annotations

import re
from typing import Any

TIMEBANK_CAP = "timebank"

_TIMEBANK_SIGNALS = re.compile(
    r"时间银行|志愿时长账户|时长账户|存入时长|时长核销|时间币|互助时长|时长存取|志愿时数账户|社区时间银行"
)


def scan_timebank(text: str) -> bool:
    return bool(_TIMEBANK_SIGNALS.search(text or ""))


def timebank_wanted(
    *,
    domain: str | None,
    capabilities: list[str] | None = None,
    proposal_text: str = "",
) -> bool:
    caps = list(capabilities or [])
    if TIMEBANK_CAP in caps:
        return True
    if (domain or "") == "DOM-TIMEBANK":
        return True
    return scan_timebank(proposal_text)


def merge_timebank_capabilities(
    caps: list[str],
    proposal_text: str = "",
    *,
    domain: str | None = None,
    force: bool = False,
) -> list[str]:
    out = list(caps or [])
    want = force or timebank_wanted(
        domain=domain,
        capabilities=out,
        proposal_text=proposal_text,
    )
    if want and TIMEBANK_CAP not in out:
        out.append(TIMEBANK_CAP)
    return out


def attach_timebank_menus(schema: dict[str, Any]) -> None:
    from app.bake.schema.menu_utils import ensure_menu

    menus = schema.setdefault("menus", {})
    admin = menus.setdefault("admin", [])
    user = menus.setdefault("user", [])
    ensure_menu(
        admin,
        "tb_accounts",
        {"key": "tb_accounts", "label": "时长账户", "superOnly": True},
        before_key="content",
    )
    ensure_menu(
        admin,
        "tb_ledger_admin",
        {"key": "tb_ledger_admin", "label": "时长流水", "superOnly": True},
        before_key="content",
    )
    ensure_menu(
        user,
        "tb_account",
        {"key": "tb_account", "label": "我的时长"},
        before_key="content",
    )
    ensure_menu(
        user,
        "tb_ledger",
        {"key": "tb_ledger", "label": "时长流水"},
        before_key="content",
    )
    labels = schema.setdefault("labels", {})
    labels.setdefault("tbAccountTitle", "我的时长")
    labels.setdefault(
        "tbAccountLead",
        "查看志愿时长余额；可对服务事项登记存入，核销须提交申请经审核扣减。",
    )
    labels.setdefault("tbLedgerTitle", "时长流水")
    ents = schema.setdefault("entities", {})
    if "timebank" not in ents:
        ents["timebank"] = {
            "key": "timebank",
            "label": "时长账户",
            "labelPlural": "时长账户",
            "redeemOnApprove": True,
        }
    ticket = ents.get("ticket")
    if isinstance(ticket, dict):
        ticket["allowQty"] = True
        ticket.setdefault("qtyLabel", "核销小时数")


def apply_timebank_to_spec(spec: dict[str, Any], proposal_text: str = "") -> dict[str, Any]:
    domain = spec.get("domain")
    caps = merge_timebank_capabilities(
        list(spec.get("capabilities") or []),
        proposal_text,
        domain=domain,
    )
    spec = {**spec, "capabilities": caps}
    schema = dict(spec.get("schema") or {})
    schema["capabilities"] = caps

    if TIMEBANK_CAP in caps:
        attach_timebank_menus(schema)
        from app.bake.gate_contracts import merge_timebank_gate

        gate = dict(spec.get("gate") or {})
        spec["gate"] = merge_timebank_gate(gate, caps)

        features = list(spec.get("features") or [])
        names = {f.get("name") for f in features if isinstance(f, dict)}
        if "时长账户与流水" not in names:
            features.append({"name": "时长账户与流水", "status": "flow"})
        spec["features"] = features

        ents = list(spec.get("entities") or [])
        if "Timebank" not in ents:
            if "Notice" in ents:
                ents.insert(ents.index("Notice"), "Timebank")
            else:
                ents.append("Timebank")
            spec["entities"] = ents

    spec["schema"] = schema
    return spec
