"""通行码/取件码二维码出示 code_qr：开题扫词才挂；无域默认。

对已有码字符串生成前端 QR；出示/打印页。文案：通行码/取件码，不对接闸机。
不做硬件扫码枪、闸机联动。未挂时仍只显示字符串。
"""

from __future__ import annotations

from typing import Any

from app.bake.proposal_lexicon import keyword_mentioned

CODE_QR_CAP = "code_qr"

_TERMS = (
    "二维码",
    "扫码出示",
    "通行码二维码",
    "取件码二维码",
    "出示二维码",
    "二维码出示",
)


def scan_code_qr(text: str) -> bool:
    raw = text or ""
    return any(keyword_mentioned(raw, kw, ignore_contrast=True) for kw in _TERMS)


def merge_code_qr_capabilities(
    caps: list[str] | None,
    proposal_text: str = "",
    *,
    domain: str | None = None,
) -> list[str]:
    del domain
    out = list(caps or [])
    if CODE_QR_CAP in out:
        return out
    if not scan_code_qr(proposal_text or ""):
        return out
    out.append(CODE_QR_CAP)
    return out


def apply_code_qr_to_spec(spec: dict[str, Any], proposal_text: str = "") -> dict[str, Any]:
    text = proposal_text or ""
    caps = merge_code_qr_capabilities(
        list(spec.get("capabilities") or []),
        text,
        domain=spec.get("domain"),
    )
    spec = {**spec, "capabilities": caps}
    schema = dict(spec.get("schema") or {})
    schema["capabilities"] = caps
    if CODE_QR_CAP in caps:
        labels = schema.setdefault("labels", {})
        labels.setdefault("codeQrShowVerb", "出示二维码")
        labels.setdefault("codeQrPrintVerb", "打印")
        labels.setdefault(
            "codeQrHint",
            "扫码可识别下方码文，用于现场出示核对。",
        )
        from app.bake.gate_contracts import merge_code_qr_gate

        gate = dict(spec.get("gate") or {})
        spec["gate"] = merge_code_qr_gate(gate, caps)
        features = list(spec.get("features") or [])
        names = {f.get("name") for f in features if isinstance(f, dict)}
        if "二维码出示" not in names:
            features.append({"name": "二维码出示", "status": "module"})
        spec["features"] = features
    spec["schema"] = schema
    return spec
