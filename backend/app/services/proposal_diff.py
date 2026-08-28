"""开题功能行与 Spec checklist 对照（生成前上游验收，不调 LLM）。"""



from __future__ import annotations



from typing import Any



from app.services.proposal_match import classify_line_match





def _proposal_lines(spec: dict[str, Any], proposal_text: str = "") -> list[str]:

    prop = spec.get("proposal") if isinstance(spec.get("proposal"), dict) else {}

    lines = list(prop.get("feature_lines") or [])

    if lines:

        return [str(x).strip() for x in lines if str(x).strip()]

    if proposal_text.strip():

        from app.services.proposal import summarize_proposal



        hits = spec.get("hits") if isinstance(spec.get("hits"), list) else None

        summary = summarize_proposal(proposal_text, hits)

        return [str(x).strip() for x in (summary.get("feature_lines") or []) if str(x).strip()]

    return []





def _active_features(spec: dict[str, Any]) -> list[dict[str, Any]]:

    return [

        f

        for f in (spec.get("features") or [])

        if isinstance(f, dict) and f.get("status") != "out_of_mvp"

    ]





def _compose_status(

    *,

    total: int,

    matched_n: int,

    review_n: int,

    unmatched_n: int,

) -> dict[str, Any]:

    covered = matched_n + review_n

    if total <= 0:

        return {

            "summary": "将按已选领域默认清单生成",

            "operator_hint": "无开题功能行时跳过措辞对照，直接确认即可。",

            "coverage_label": "按领域默认清单",

            "ok": True,

            "ready": True,

            "needs_review": False,

        }



    coverage_label = f"{covered}/{total} 已覆盖"

    if unmatched_n == 0:

        if review_n == 0:

            summary = f"开题 {total} 项均已对照，可确认生成"

        else:

            summary = (

                f"开题 {total} 项已覆盖（{matched_n} 项直接对照 · "

                f"{review_n} 项措辞弱匹配），可确认生成"

            )

        return {

            "summary": summary,

            "operator_hint": "主流程已对齐，确认后将按清单出包。",

            "coverage_label": f"{total}/{total} 已覆盖",

            "ok": True,

            "ready": True,

            "needs_review": review_n > 0,

        }



    ratio = covered / total

    if ratio >= 0.6 and unmatched_n <= 2:

        return {

            "summary": f"开题 {covered}/{total} 项已覆盖，{unmatched_n} 项措辞待核",

            "operator_hint": "多为开题表述与模块名不一致；若领域选对，通常不影响出包与演示。",

            "coverage_label": coverage_label,

            "ok": False,

            "ready": True,

            "needs_review": True,

        }



    return {

        "summary": f"开题 {unmatched_n} 项可能与清单不一致，请确认领域是否正确",

        "operator_hint": "若领域选错，生成后演示可能与开题不符；请在匹配确认页核对领域。",

        "coverage_label": coverage_label,

        "ok": False,

        "ready": False,

        "needs_review": True,

    }





def build_proposal_diff(

    spec: dict[str, Any],

    proposal_text: str = "",

) -> dict[str, Any]:

    """返回开题功能行与工厂 checklist 的差异摘要。"""

    lines = _proposal_lines(spec, proposal_text)

    features = _active_features(spec)

    checklist = [

        str(f.get("name") or "").strip()

        for f in features

        if str(f.get("name") or "").strip()

    ]



    matched: list[str] = []

    review: list[str] = []

    unmatched: list[str] = []

    match_links: list[dict[str, Any]] = []



    for line in lines:

        kind, links = classify_line_match(line, features)

        if links:

            match_links.append({"line": line, "hits": links})

        if kind == "matched":

            matched.append(line)

        elif kind == "review":

            review.append(line)

        else:

            unmatched.append(line)



    covered_features: set[str] = set()

    for row in match_links:

        for hit in row.get("hits") or []:

            name = str(hit.get("feature") or "")

            if name:

                covered_features.add(name)



    extra_in_spec = [n for n in checklist if n not in covered_features]



    matched_n = len(matched)

    review_n = len(review)

    unmatched_n = len(unmatched)

    status = _compose_status(

        total=len(lines),

        matched_n=matched_n,

        review_n=review_n,

        unmatched_n=unmatched_n,

    )



    return {

        "proposal_lines": lines,

        "checklist_names": checklist,

        "matched": matched,

        "review_proposal": review,

        "unmatched_proposal": unmatched,

        "match_links": match_links,

        "extra_checklist": extra_in_spec,

        "ok": status["ok"],

        "ready": status["ready"],

        "needs_review": status["needs_review"],

        "summary": status["summary"],

        "coverage_label": status["coverage_label"],

        "operator_hint": status["operator_hint"],

    }

