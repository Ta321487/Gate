"""帖子禁言 post_mute：论坛行业默认；博客仍开题扫词。

管理端设禁言截止时间；期内不可发帖/回复（≠ enabled=0 整号停用）。
举报处置可一键禁言。禁言截止写入 sys_user.post_mute_until。
"""

from __future__ import annotations

from typing import Any

from app.bake.proposal_lexicon import keyword_mentioned

POST_MUTE_CAP = "post_mute"

_TERMS = ("禁言", "禁止发帖", "禁言处罚", "禁言功能")
_MUTE_DOMAINS = frozenset({"DOM-FORUM", "DOM-BLOG"})
_MUTE_DEFAULT_DOMAINS = frozenset({"DOM-FORUM"})


def scan_post_mute(text: str) -> bool:
    raw = text or ""
    return any(keyword_mentioned(raw, kw, ignore_contrast=True) for kw in _TERMS)


def merge_post_mute_capabilities(
    caps: list[str] | None,
    proposal_text: str = "",
    *,
    domain: str | None = None,
) -> list[str]:
    out = list(caps or [])
    if POST_MUTE_CAP in out:
        return out
    if (domain or "") not in _MUTE_DOMAINS:
        return out
    want = (domain or "") in _MUTE_DEFAULT_DOMAINS or scan_post_mute(
        proposal_text or ""
    )
    if not want:
        return out
    out.append(POST_MUTE_CAP)
    return out


def apply_post_mute_to_spec(spec: dict[str, Any], proposal_text: str = "") -> dict[str, Any]:
    text = proposal_text or ""
    caps = merge_post_mute_capabilities(
        list(spec.get("capabilities") or []),
        text,
        domain=spec.get("domain"),
    )
    spec = {**spec, "capabilities": caps}
    schema = dict(spec.get("schema") or {})
    schema["capabilities"] = caps
    if POST_MUTE_CAP in caps:
        labels = schema.setdefault("labels", {})
        labels.setdefault("postMuteVerb", "禁言")
        labels.setdefault("postMuteClearVerb", "解除禁言")
        labels.setdefault(
            "postMuteHint",
            "禁言期内不可发帖或回复；不等于停用账号。",
        )
        from app.bake.gate_contracts import merge_post_mute_gate

        gate = dict(spec.get("gate") or {})
        spec["gate"] = merge_post_mute_gate(gate, caps)
        features = list(spec.get("features") or [])
        names = {f.get("name") for f in features if isinstance(f, dict)}
        if "禁言" not in names:
            features.append({"name": "禁言", "status": "module"})
        spec["features"] = features
    spec["schema"] = schema
    return spec


POST_MUTE_COLUMNS: list[tuple[str, str]] = [
    ("post_mute_until", "DATETIME NULL"),
]


def ensure_post_mute_sql(sql: str, *, enabled: bool) -> str:
    """禁言截止落 sys_user.post_mute_until，不写 profile_json。"""
    if not enabled:
        return sql
    import re

    from app.bake.sql.ddl_edit import CREATE_TABLE_RE, inject_missing_columns, strip_trailing_comma_before_close

    def repl(m: re.Match[str]) -> str:
        head, table, body, tail = m.group(1), m.group(2), m.group(3), m.group(4)
        if table.lower() != "sys_user":
            return m.group(0)
        body = inject_missing_columns(body, POST_MUTE_COLUMNS)
        body = strip_trailing_comma_before_close(body)
        return f"{head}{body}{tail}"

    return CREATE_TABLE_RE.sub(repl, sql)
