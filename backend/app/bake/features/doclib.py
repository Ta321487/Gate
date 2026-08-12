"""简易文库（doclib）：资料附件、权限档、下载台账（C-12）。"""

from __future__ import annotations

import re
from typing import Any

from app.bake.proposal_lexicon import pattern_mentioned

DOCLIB_CAP = "doclib"

_DOCLIB_SIGNALS = re.compile(
    r"知识库|文库|资料库|文档库|下载台账|资料下载|附件下载|共享文档|课件下载|制度文件库|文件库|资料共享"
)


def scan_doclib(text: str) -> bool:
    return pattern_mentioned(text or "", _DOCLIB_SIGNALS, ignore_contrast=True)


def doclib_wanted(
    *,
    domain: str | None,
    capabilities: list[str] | None = None,
    proposal_text: str = "",
) -> bool:
    caps = list(capabilities or [])
    if DOCLIB_CAP in caps:
        return True
    if (domain or "") == "DOM-DOCLIB":
        return True
    return scan_doclib(proposal_text)


def merge_doclib_capabilities(
    caps: list[str],
    proposal_text: str = "",
    *,
    domain: str | None = None,
    force: bool = False,
) -> list[str]:
    out = list(caps or [])
    want = force or doclib_wanted(
        domain=domain,
        capabilities=out,
        proposal_text=proposal_text,
    )
    if want and DOCLIB_CAP not in out:
        out.append(DOCLIB_CAP)
    return out


def attach_doclib_menus(schema: dict[str, Any]) -> None:
    from app.bake.schema.menu_utils import ensure_menu

    menus = schema.setdefault("menus", {})
    admin = menus.setdefault("admin", [])
    user = menus.setdefault("user", [])
    ensure_menu(
        admin,
        "doc_files",
        {"key": "doc_files", "label": "附件权限", "superOnly": True},
        before_key="content",
    )
    ensure_menu(
        admin,
        "doc_logs",
        {"key": "doc_logs", "label": "下载台账", "superOnly": True},
        before_key="content",
    )
    ensure_menu(
        user,
        "doc_browse",
        {"key": "doc_browse", "label": "文库浏览"},
        before_key="content",
    )
    ensure_menu(
        user,
        "doc_mine",
        {"key": "doc_mine", "label": "我的下载"},
        before_key="content",
    )
    labels = schema.setdefault("labels", {})
    labels.setdefault("docBrowseTitle", "文库浏览")
    labels.setdefault(
        "docBrowseLead",
        "浏览开放资料，按权限下载；下载将记入台账（非真对象存储签名）。",
    )
    labels.setdefault("docMineTitle", "我的下载")
    ents = schema.setdefault("entities", {})
    if "doclib" not in ents:
        ents["doclib"] = {"key": "doclib", "label": "资料", "labelPlural": "资料"}


def apply_doclib_to_spec(spec: dict[str, Any], proposal_text: str = "") -> dict[str, Any]:
    domain = spec.get("domain")
    caps = merge_doclib_capabilities(
        list(spec.get("capabilities") or []),
        proposal_text,
        domain=domain,
    )
    spec = {**spec, "capabilities": caps}
    schema = dict(spec.get("schema") or {})
    schema["capabilities"] = caps

    if DOCLIB_CAP in caps:
        attach_doclib_menus(schema)
        from app.bake.gate_contracts import merge_doclib_gate

        gate = dict(spec.get("gate") or {})
        spec["gate"] = merge_doclib_gate(gate, caps)

        features = list(spec.get("features") or [])
        names = {f.get("name") for f in features if isinstance(f, dict)}
        if "资料下载与台账" not in names:
            features.append({"name": "资料下载与台账", "status": "flow"})
        spec["features"] = features

        ents = list(spec.get("entities") or [])
        if "Doclib" not in ents:
            if "Notice" in ents:
                ents.insert(ents.index("Notice"), "Doclib")
            else:
                ents.append("Doclib")
            spec["entities"] = ents

    spec["schema"] = schema
    return spec
