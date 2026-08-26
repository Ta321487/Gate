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





def _checklist_features(spec: dict[str, Any]) -> list[dict[str, Any]]:

    return [f for f in (spec.get("features") or []) if isinstance(f, dict)]





def build_proposal_diff(

    spec: dict[str, Any],

    proposal_text: str = "",

) -> dict[str, Any]:

    """返回开题功能行与工厂 checklist 的差异摘要。"""

    lines = _proposal_lines(spec, proposal_text)

    features = _checklist_features(spec)

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



    review_n = len(review)

    unmatched_n = len(unmatched)

    if unmatched_n:

        summary = f"开题 {unmatched_n} 项未落入 checklist，生成前请确认"

    elif review_n:

        summary = f"开题 {review_n} 项措辞与 checklist 仅弱匹配，建议扫一眼再生成"

    else:

        summary = "开题功能行已纳入对照清单"



    return {

        "proposal_lines": lines,

        "checklist_names": checklist,

        "matched": matched,

        "review_proposal": review,

        "unmatched_proposal": unmatched,

        "match_links": match_links,

        "extra_checklist": extra_in_spec,

        "ok": unmatched_n == 0,

        "needs_review": review_n > 0,

        "summary": summary,

    }


