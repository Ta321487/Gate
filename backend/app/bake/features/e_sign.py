"""本地签章（e_sign）：上传签章图 + 勾选同意（C-18；非 CA）。"""

from __future__ import annotations

import re
from typing import Any

E_SIGN_CAP = "e_sign"

_E_SIGN_SIGNALS = re.compile(
    r"电子签|签章图|本地签章|上传签章|勾选同意签|鉴定签署|签字确认|签署留痕|"
    r"签章演示|电子签名演示|实习鉴定签"
)


def scan_e_sign(text: str) -> bool:
    return bool(_E_SIGN_SIGNALS.search(text or ""))


def e_sign_wanted(
    *,
    domain: str | None,
    capabilities: list[str] | None = None,
    proposal_text: str = "",
) -> bool:
    caps = list(capabilities or [])
    if E_SIGN_CAP in caps:
        return True
    if (domain or "") == "DOM-INTERN":
        return True
    return scan_e_sign(proposal_text)


def merge_e_sign_capabilities(
    caps: list[str],
    proposal_text: str = "",
    *,
    domain: str | None = None,
    force: bool = False,
) -> list[str]:
    out = list(caps or [])
    want = force or e_sign_wanted(
        domain=domain,
        capabilities=out,
        proposal_text=proposal_text,
    )
    if want and E_SIGN_CAP not in out:
        out.append(E_SIGN_CAP)
    return out


def attach_e_sign_menus(schema: dict[str, Any]) -> None:
    from app.bake.schema.menu_utils import ensure_menu

    menus = schema.setdefault("menus", {})
    admin = menus.setdefault("admin", [])
    user = menus.setdefault("user", [])
    ensure_menu(
        admin,
        "e_sign_admin",
        {"key": "e_sign_admin", "label": "签署记录", "superOnly": True},
        before_key="content",
    )
    ensure_menu(
        user,
        "e_sign_mine",
        {"key": "e_sign_mine", "label": "鉴定签署"},
        before_key="content",
    )
    labels = schema.setdefault("labels", {})
    labels.setdefault("eSignTitle", "鉴定签署")
    labels.setdefault(
        "eSignLead",
        "上传签章图并勾选同意完成签署；非 CA、非法大大等第三方电子签平台。",
    )
    labels.setdefault("eSignAdminTitle", "签署记录")
    ents = schema.setdefault("entities", {})
    if "e_sign" not in ents:
        ents["e_sign"] = {
            "key": "e_sign",
            "label": "签章",
            "labelPlural": "签署记录",
        }


def apply_e_sign_to_spec(spec: dict[str, Any], proposal_text: str = "") -> dict[str, Any]:
    domain = spec.get("domain")
    caps = merge_e_sign_capabilities(
        list(spec.get("capabilities") or []),
        proposal_text,
        domain=domain,
    )
    spec = {**spec, "capabilities": caps}
    schema = dict(spec.get("schema") or {})
    schema["capabilities"] = caps

    if E_SIGN_CAP in caps:
        attach_e_sign_menus(schema)
        from app.bake.gate_contracts import merge_e_sign_gate

        gate = dict(spec.get("gate") or {})
        spec["gate"] = merge_e_sign_gate(gate, caps)

        features = list(spec.get("features") or [])
        names = {f.get("name") for f in features if isinstance(f, dict)}
        if "本地签章" not in names:
            features.append({"name": "本地签章", "status": "flow"})
        spec["features"] = features

        ents = list(spec.get("entities") or [])
        if "ESign" not in ents:
            if "Notice" in ents:
                ents.insert(ents.index("Notice"), "ESign")
            else:
                ents.append("ESign")
            spec["entities"] = ents

    spec["schema"] = schema
    return spec
