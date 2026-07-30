"""简易问卷（survey）：字段配置、填写、回收、选项计数（C-03）。"""

from __future__ import annotations

import re
from typing import Any

from app.bake.proposal_lexicon import pattern_mentioned

SURVEY_CAP = "survey"

# 禁止裸「调研」：开题进度几乎都有「文献调研」。
# 禁止裸「问卷」：「邮箱、问卷或现场投递」是投递渠道，不是 C-03 问卷系统。
_SURVEY_SIGNALS = re.compile(
    r"问卷调查|问卷配置|问卷填写|问卷回收|问卷统计|问卷系统|问卷调研|问卷管理|问卷表"
    r"|在线问卷|调查表|简易量表|满意度调查"
    r"|用户调研|客户调研|满意度调研|在线调研"
)


def scan_survey(text: str) -> bool:
    return pattern_mentioned(text or "", _SURVEY_SIGNALS, ignore_contrast=True)


def survey_wanted(
    *,
    domain: str | None,
    capabilities: list[str] | None = None,
    proposal_text: str = "",
) -> bool:
    caps = list(capabilities or [])
    if SURVEY_CAP in caps:
        return True
    if (domain or "") == "DOM-SURVEY":
        return True
    return scan_survey(proposal_text)


def merge_survey_capabilities(
    caps: list[str],
    proposal_text: str = "",
    *,
    domain: str | None = None,
    force: bool = False,
) -> list[str]:
    out = list(caps or [])
    want = force or survey_wanted(
        domain=domain,
        capabilities=out,
        proposal_text=proposal_text,
    )
    if want and SURVEY_CAP not in out:
        out.append(SURVEY_CAP)
    return out


def attach_survey_menus(schema: dict[str, Any]) -> None:
    from app.bake.schema.menu_utils import ensure_menu

    menus = schema.setdefault("menus", {})
    admin = menus.setdefault("admin", [])
    user = menus.setdefault("user", [])
    ensure_menu(
        admin,
        "survey_forms",
        {"key": "survey_forms", "label": "问卷管理", "superOnly": True},
        before_key="content",
    )
    ensure_menu(
        admin,
        "survey_stats",
        {"key": "survey_stats", "label": "回收统计", "superOnly": True},
        before_key="content",
    )
    ensure_menu(
        user,
        "survey_forms",
        {"key": "survey_forms", "label": "填写问卷"},
        before_key="content",
    )
    ensure_menu(
        user,
        "survey_mine",
        {"key": "survey_mine", "label": "我的答卷"},
        before_key="content",
    )
    labels = schema.setdefault("labels", {})
    labels.setdefault("surveyFormsTitle", "填写问卷")
    labels.setdefault("surveyFormsLead", "选择已发布问卷填写提交；每人每卷限填一次。")
    labels.setdefault("surveyMineTitle", "我的答卷")
    ents = schema.setdefault("entities", {})
    if "survey" not in ents:
        ents["survey"] = {"key": "survey", "label": "问卷", "labelPlural": "问卷"}


def apply_survey_to_spec(spec: dict[str, Any], proposal_text: str = "") -> dict[str, Any]:
    domain = spec.get("domain")
    caps = merge_survey_capabilities(
        list(spec.get("capabilities") or []),
        proposal_text,
        domain=domain,
    )
    spec = {**spec, "capabilities": caps}
    schema = dict(spec.get("schema") or {})
    schema["capabilities"] = caps

    if SURVEY_CAP in caps:
        attach_survey_menus(schema)
        from app.bake.gate_contracts import merge_survey_gate

        gate = dict(spec.get("gate") or {})
        spec["gate"] = merge_survey_gate(gate, caps)

        features = list(spec.get("features") or [])
        names = {f.get("name") for f in features if isinstance(f, dict)}
        if "问卷填写与回收" not in names:
            features.append({"name": "问卷填写与回收", "status": "flow"})
        spec["features"] = features

        ents = list(spec.get("entities") or [])
        if "Survey" not in ents:
            if "Notice" in ents:
                ents.insert(ents.index("Notice"), "Survey")
            else:
                ents.append("Survey")
            spec["entities"] = ents

    spec["schema"] = schema
    return spec
