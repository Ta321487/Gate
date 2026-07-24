"""archive_log：挂档案的打卡/随访记录。DOM-EVENT 域默认；其它域开题写到才挂。"""

from __future__ import annotations

from typing import Any

from app.bake.proposal_lexicon import keyword_mentioned

ARCHIVE_LOG_CAP = "archive_log"

# 与 catalog / capabilities 同一套 keyword_mentioned（否定/对比不计）
_LOG_SIGNAL_TERMS = (
    "健康打卡",
    "晨午检",
    "晨检",
    "午检",
    "随访记录",
    "每日监测",
    "巡访",
    "巡访打卡",
    "隔离观察",
    "复工监测",
    "因病缺课",
    "服药督导",
    "日护打卡",
    "体征登记",
    "健康监测",
    "每日打卡",
    "打卡记录",
    "观察记录",
    "健康筛查",
    "筛查打卡",
    "定位打卡",
)

_DEFAULT_FIELDS = [
    {"key": "temperature", "label": "体温℃", "type": "string"},
    {"key": "bloodPressure", "label": "血压", "type": "string"},
    {"key": "bloodSugar", "label": "血糖", "type": "string"},
    {"key": "note", "label": "备注", "type": "textarea"},
]


def scan_archive_log(text: str) -> bool:
    raw = text or ""
    return any(keyword_mentioned(raw, kw, ignore_contrast=True) for kw in _LOG_SIGNAL_TERMS)


def merge_archive_log_capabilities(
    caps: list[str],
    proposal_text: str = "",
    *,
    domain: str | None = None,
) -> list[str]:
    out = list(caps or [])
    if "archive" not in out:
        return [c for c in out if c != ARCHIVE_LOG_CAP]
    # 域默认已带则保留；否则仅材料命中才挂
    if ARCHIVE_LOG_CAP in out:
        return out
    if domain == "DOM-EVENT" or scan_archive_log(proposal_text or ""):
        out.append(ARCHIVE_LOG_CAP)
    return out


def attach_archive_log_schema(schema: dict[str, Any], caps: list[str]) -> None:
    from app.bake.schema.menu_utils import ensure_menu

    if ARCHIVE_LOG_CAP not in (caps or []):
        return
    labels = schema.setdefault("labels", {})
    menus = schema.setdefault("menus", {})
    admin = menus.setdefault("admin", [])
    ents = schema.setdefault("entities", {})
    log_ent = ents.setdefault("archiveLog", {})
    log_ent.setdefault("key", "archive_log")
    log_ent.setdefault("label", "监测记录")
    log_ent.setdefault("labelPlural", "监测记录")
    log_ent.setdefault("defaultType", "checkin")
    log_ent.setdefault(
        "typeOptions",
        [
            {"value": "checkin", "label": "健康打卡"},
            {"value": "followup", "label": "随访记录"},
            {"value": "assess", "label": "评估记录"},
        ],
    )
    log_ent.setdefault("fields", list(_DEFAULT_FIELDS))
    log_ent.setdefault("requireItem", True)

    labels.setdefault("archiveLogPageTitle", "监测记录")
    labels.setdefault("archiveLogPageLead", "按对象查看打卡与随访；可筛选今日未打卡。")
    labels.setdefault("archiveLogSubmitLabel", "提交打卡")
    labels.setdefault("archiveLogMissingTitle", "今日未打卡")
    labels.setdefault("archiveLogSectionTitle", "打卡与随访")

    ensure_menu(
        admin,
        "archive_logs",
        {"key": "archive_logs", "label": labels.get("archiveLogPageTitle") or "监测记录"},
        before_key="tickets",
    )
    if not any(m.get("key") == "archive_logs" for m in admin):
        ensure_menu(
            admin,
            "archive_logs",
            {"key": "archive_logs", "label": "监测记录"},
            before_key="records",
        )


def apply_archive_log_to_spec(spec: dict[str, Any], proposal_text: str = "") -> dict[str, Any]:
    domain = str(spec.get("domain") or "")
    caps = merge_archive_log_capabilities(
        list(spec.get("capabilities") or []),
        proposal_text,
        domain=domain,
    )
    spec = {**spec, "capabilities": caps}
    schema = dict(spec.get("schema") or {})
    schema["capabilities"] = caps
    if ARCHIVE_LOG_CAP in caps:
        attach_archive_log_schema(schema, caps)
        from app.bake.gate_contracts import merge_archive_log_gate

        gate = dict(spec.get("gate") or {})
        spec["gate"] = merge_archive_log_gate(gate, caps)
        features = list(spec.get("features") or [])
        names = {f.get("name") for f in features if isinstance(f, dict)}
        if "健康打卡/监测记录" not in names:
            features.append({"name": "健康打卡/监测记录", "status": "domain"})
        spec["features"] = features
    spec["schema"] = schema
    return spec
