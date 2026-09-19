"""时间银行（timebank）：时长账户、流水加减、核销扣减（C-14）。"""

from __future__ import annotations

import re
from typing import Any

from app.bake.proposal_lexicon import pattern_mentioned

TIMEBANK_CAP = "timebank"

_TIMEBANK_SIGNALS = re.compile(
    r"时间银行|志愿时长账户|时长账户|存入时长|时长核销|时间币|互助时长|时长存取|志愿时数账户|社区时间银行"
)


def scan_timebank(text: str) -> bool:
    return pattern_mentioned(text or "", _TIMEBANK_SIGNALS, ignore_contrast=True)


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


# —— 额度台账（借用族 OA）：同文件维护，与 timebank 同为账户+流水形态 ——

BALANCE_LEDGER_CAP = "balance_ledger"

LEDGER_DOMAINS: frozenset[str] = frozenset({
    "DOM-FUND",
    "DOM-EXPENSE",
    "DOM-SEAL",
    "DOM-RECRUIT",
    "DOM-CREDIT",
    "DOM-LABOR",
    "DOM-MORAL",
    "DOM-AWARD",
})

# 科目名 + 单位。未列入的域（扫词挂上）回落「次」。金额仍是整数元。
LEDGER_SUBJECT: dict[str, tuple[str, str]] = {
    "DOM-FUND": ("资助额度", "元"),
    "DOM-EXPENSE": ("经费额度", "元"),
    "DOM-SEAL": ("用章额度", "次"),
    "DOM-RECRUIT": ("投递额度", "次"),
    "DOM-CREDIT": ("学分额度", "学分"),
    "DOM-LABOR": ("时长额度", "小时"),
    "DOM-MORAL": ("综测额度", "分"),
    "DOM-AWARD": ("学分额度", "学分"),
}


def ledger_subject(domain: str | None) -> tuple[str, str]:
    return LEDGER_SUBJECT.get(domain or "", ("默认额度", "次"))

_LEDGER_SIGNALS = re.compile(
    r"额度账户|额度台账|余额台账|额度流水|额度不足|次数额度|经费额度|"
    r"额度校验|额度扣减|个人额度|申请额度"
)


def scan_balance_ledger(text: str) -> bool:
    return pattern_mentioned(text or "", _LEDGER_SIGNALS, ignore_contrast=True)


def balance_ledger_wanted(
    *,
    domain: str | None,
    capabilities: list[str] | None = None,
    proposal_text: str = "",
) -> bool:
    caps = list(capabilities or [])
    if BALANCE_LEDGER_CAP in caps:
        return True
    if (domain or "") in LEDGER_DOMAINS:
        return True
    return scan_balance_ledger(proposal_text)


def merge_balance_ledger_capabilities(
    caps: list[str],
    proposal_text: str = "",
    *,
    domain: str | None = None,
    force: bool = False,
) -> list[str]:
    out = list(caps or [])
    want = force or balance_ledger_wanted(
        domain=domain,
        capabilities=out,
        proposal_text=proposal_text,
    )
    if want and BALANCE_LEDGER_CAP not in out:
        out.append(BALANCE_LEDGER_CAP)
    return out


def attach_balance_ledger_menus(schema: dict[str, Any], domain: str | None = None) -> None:
    from app.bake.schema.menu_utils import ensure_menu

    menus = schema.setdefault("menus", {})
    admin = menus.setdefault("admin", [])
    user = menus.setdefault("user", [])
    ensure_menu(
        admin,
        "balance_accounts",
        {"key": "balance_accounts", "label": "额度账户", "superOnly": False},
        before_key="content",
    )
    ensure_menu(
        admin,
        "balance_ledger_admin",
        {"key": "balance_ledger_admin", "label": "额度流水", "superOnly": False},
        before_key="content",
    )
    ensure_menu(
        user,
        "balance_mine",
        {"key": "balance_mine", "label": "我的额度"},
        before_key="content",
    )
    ensure_menu(
        user,
        "balance_ledger_mine",
        {"key": "balance_ledger_mine", "label": "额度流水"},
        before_key="content",
    )
    labels = schema.setdefault("labels", {})
    subject, unit = ledger_subject(domain)
    labels["balanceUnit"] = unit
    labels["balanceSubjectTitle"] = subject
    labels.setdefault("balanceMineTitle", "我的额度")
    labels.setdefault(
        "balanceMineLead",
        "查看本人可用额度；提交申请并审批通过时按需扣减，余额不足将无法通过。",
    )
    labels.setdefault("balanceLedgerTitle", "额度流水")
    labels.setdefault("balanceAccountsTitle", "额度账户")
    labels.setdefault("balanceLedgerAdminTitle", "额度流水")
    ents = schema.setdefault("entities", {})
    if "balance_ledger" not in ents:
        ents["balance_ledger"] = {
            "key": "balance_ledger",
            "label": "额度",
            "labelPlural": "额度账户",
        }


def apply_balance_ledger_to_spec(spec: dict[str, Any], proposal_text: str = "") -> dict[str, Any]:
    domain = spec.get("domain")
    caps = merge_balance_ledger_capabilities(
        list(spec.get("capabilities") or []),
        proposal_text,
        domain=domain,
    )
    spec = {**spec, "capabilities": caps}
    schema = dict(spec.get("schema") or {})
    schema["capabilities"] = caps

    if BALANCE_LEDGER_CAP in caps:
        attach_balance_ledger_menus(schema, domain)
        from app.bake.gate_contracts import merge_balance_ledger_gate

        gate = dict(spec.get("gate") or {})
        spec["gate"] = merge_balance_ledger_gate(gate, caps)

        features = list(spec.get("features") or [])
        names = {f.get("name") for f in features if isinstance(f, dict)}
        if "额度台账与扣减" not in names:
            features.append({"name": "额度台账与扣减", "status": "flow"})
        spec["features"] = features

        ents = list(spec.get("entities") or [])
        if "BalanceLedger" not in ents:
            if "Notice" in ents:
                ents.insert(ents.index("Notice"), "BalanceLedger")
            else:
                ents.append("BalanceLedger")
            spec["entities"] = ents

        ticket = schema.setdefault("entities", {}).setdefault("ticket", {})
        if isinstance(ticket, dict):
            ticket["debitBalanceOnApprove"] = True

    spec["schema"] = schema
    return spec
