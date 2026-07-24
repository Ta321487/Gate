# -*- coding: utf-8 -*-
"""开题样例 → match → build_spec 业务皮校验；可选 Island LLM 润色角色。"""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from app.bake.catalog import build_spec, match_text  # noqa: E402
from app.bake.domain_schema import merge_schema, validate_schema  # noqa: E402
from app.bake.themes import pick_theme  # noqa: E402
from app.core.config import get_settings  # noqa: E402
from app.llm.agents import _LABEL_KEYS, _sanitize_island_patch, _proposal_text  # noqa: E402
from app.llm.client import chat  # noqa: E402
from app.llm.runtime import LlmRuntime, ProviderEndpoint  # noqa: E402
from app.services.proposal import summarize_proposal  # noqa: E402

SAMPLES = ROOT / "data" / "samples" / "开题报告"
EXPECT_DOM = {
    "01": "DOM-EVENT",
    "02": "DOM-EVENT",
    "03": "DOM-EVENT",
    "04": "DOM-ASSET",
    "05": "DOM-EVENT",
    "06": "DOM-EVENT",
    "07": "DOM-EVENT",
    "08": "DOM-EVENT",
    "09": "DOM-EVENT",
    "10": "DOM-EVENT",
    "11": "DOM-EVENT",
    "12": "DOM-EVENT",
}
# Island 抽检：题面角色差异大的几份
ISLAND_PICK = {"01", "03", "05", "08", "11", "04"}


def _runtime() -> LlmRuntime:
    s = get_settings()
    return LlmRuntime(
        deepseek=ProviderEndpoint(
            name="deepseek",
            api_key=s.deepseek_api_key or "",
            base_url=s.deepseek_base_url,
            model=s.deepseek_model,
            thinking=False,
        ),
        gemini=ProviderEndpoint(
            name="gemini", api_key="", base_url="", model="", thinking=False
        ),
        deepseek_enabled=True,
        gemini_enabled=False,
        preferred="deepseek",
        match_recommend=True,
        parse_spec=True,
        island_fill=True,
        er_labels=False,
        module_labels=False,
        testcase_labels=False,
        auto_fix=False,
        qa_report=False,
        fix_rounds_max=1,
        project_token_budget=200_000,
        monthly_token_budget=2_000_000,
    )


def check_biz(num: str, spec: dict) -> list[str]:
    errs: list[str] = []
    domain = spec.get("domain")
    want = EXPECT_DOM[num]
    if domain != want:
        errs.append(f"domain {domain}!={want}")
    if spec.get("accept") != "full":
        errs.append(f"accept={spec.get('accept')} reason={spec.get('accept_reason')}")
    schema = spec.get("schema") or {}
    ok, verrs = validate_schema(schema)
    if not ok:
        errs.append("schema:" + ";".join(verrs[:3]))
    ents = schema.get("entities") or {}
    archive = ents.get("archive") or {}
    ticket = ents.get("ticket") or {}
    caps = set(spec.get("capabilities") or schema.get("capabilities") or [])
    if want == "DOM-EVENT":
        if archive.get("key") != "event_case":
            errs.append(f"archive.key={archive.get('key')}")
        if ticket.get("key") != "event_report":
            errs.append(f"ticket.key={ticket.get('key')}")
        if not ticket.get("autoApprove"):
            errs.append("ticket.autoApprove missing")
        if (ticket.get("verbs") or {}).get("apply") != "提交上报":
            errs.append(f"verbs.apply={(ticket.get('verbs') or {}).get('apply')}")
        if "archive" not in caps or "ticket_flow" not in caps:
            errs.append(f"caps={sorted(caps)}")
        if "archive_log" not in caps:
            errs.append(f"missing archive_log caps={sorted(caps)}")
        log_ent = ents.get("archiveLog") or {}
        if not log_ent.get("fields"):
            errs.append("archiveLog.fields missing")
        flows = spec.get("flows") or []
        if not any(("上报" in str(f) or "打卡" in str(f) or "随访" in str(f)) for f in flows):
            errs.append(f"flows={flows}")
        # 07 等监测题主路径应为 FLOW，勿被物资词抬成 STOCK
        if num in {"03", "06", "07", "09", "11"}:
            arch = spec.get("archetype") or ""
            if arch == "ARCH-STOCK":
                errs.append(f"archetype={arch} (want FLOW for monitor samples)")
    if want == "DOM-ASSET":
        if archive.get("key") not in ("asset", "item") and "asset" not in str(
            archive.get("key") or ""
        ):
            # ASSET 模板 key
            if archive.get("key") != "asset":
                errs.append(f"archive.key={archive.get('key')}")
        if "ticket_flow" not in caps:
            errs.append(f"caps={sorted(caps)}")
        if not ticket.get("key"):
            errs.append("no ticket")
    return errs


def role_brief(schema: dict) -> str:
    roles = schema.get("roles") or {}
    bits = []
    for rid in ("user", "admin"):
        lab = (roles.get(rid) or {}).get("label")
        if lab:
            bits.append(f"{rid}={lab}")
    for p in roles.get("staff_posts") or []:
        if isinstance(p, dict) and p.get("id"):
            bits.append(f"{p['id']}={p.get('label')}")
    return " · ".join(bits)


def ticket_brief(schema: dict) -> str:
    t = (schema.get("entities") or {}).get("ticket") or {}
    a = (schema.get("entities") or {}).get("archive") or {}
    verbs = t.get("verbs") or {}
    return (
        f"archive={a.get('key')}/{a.get('label')} "
        f"ticket={t.get('key')}/{t.get('label')} "
        f"apply={verbs.get('apply')} auto={bool(t.get('autoApprove'))} "
        f"channel={t.get('contactChannelLabel') or '-'}"
    )


async def island_once(spec: dict, rt: LlmRuntime) -> tuple[dict, str]:
    """直接调 chat + sanitize，不走 DB 预算。"""
    base = spec.get("schema") or {}
    labels = dict(base.get("labels") or {})
    seeds = dict(base.get("seeds") or {})
    roles = dict(base.get("roles") or {})
    messages = [
        {
            "role": "system",
            "content": (
                "你是毕设港 Island Agent。只输出 JSON："
                '{"title","labels":{...},"seeds":{noticeTitle,noticeBody},'
                '"entities":{ticket?:{label,labelPlural,verbs,states}},'
                '"roles":{user?:{label},admin?:{label},staff_posts?:[{id,label}]}}。'
                "labels 可含: " + ",".join(_LABEL_KEYS) + "。"
                "roles：开题写了什么岗位称呼就原样填 label，禁止改写；未写则不要输出 roles。"
                "禁止增删 id。禁止改 menus/capabilities/路由/表结构。"
                "entities.ticket label 须为短动作名词，禁止带「记录」。"
            ),
        },
        {
            "role": "user",
            "content": json.dumps(
                {
                    "domain": spec.get("domain"),
                    "title": spec.get("title"),
                    "current_labels": {k: labels.get(k) for k in _LABEL_KEYS if k in labels},
                    "current_roles": {
                        "user": (roles.get("user") or {}).get("label"),
                        "admin": (roles.get("admin") or {}).get("label"),
                        "staff_posts": [
                            {"id": p.get("id"), "label": p.get("label")}
                            for p in (roles.get("staff_posts") or [])
                            if isinstance(p, dict)
                        ],
                    },
                    "proposal": _proposal_text(spec)[:2500],
                    "entities_keys": list((base.get("entities") or {}).keys()),
                },
                ensure_ascii=False,
            ),
        },
    ]
    res = await chat(rt, messages, json_mode=True, temperature=0.35)
    if not res.ok or not res.data:
        return base, f"llm_fail:{res.error or 'empty'}"
    patch = _sanitize_island_patch(res.data, labels, seeds, roles)
    merged = merge_schema(base, patch)
    for k in ("accept", "missing_capabilities", "out_of_mvp_signals", "capabilities"):
        if k in base:
            merged[k] = base[k]
    ok, errors = validate_schema(merged)
    if not ok:
        return base, "validate_fail:" + ";".join(errors[:2])
    return merged, "llm_ok"


async def main() -> None:
    files = sorted(p for p in SAMPLES.glob("[0-9][0-9]-*.txt") if not p.name.startswith("00-"))
    print(f"=== 业务皮（build_spec）files={len(files)} ===\n")
    fail = 0
    specs: dict[str, dict] = {}
    for path in files:
        num = path.name[:2]
        text = path.read_text(encoding="utf-8")
        m = match_text(text, path.name)
        prop = summarize_proposal(text, m.hits)
        prop["excerpt"] = text[:3000]
        prop["text"] = text
        theme = pick_theme(m.domain, f"{m.title}|{m.domain}|theme")
        spec = build_spec(
            m.title,
            m.archetype,
            m.domain,
            theme=theme,
            llm_enabled=True,
            match_mode="keyword",
            confidence=m.confidence,
            hits=m.hits,
            proposal=prop,
            archetypes=m.archetypes,
        )
        errs = check_biz(num, spec)
        mark = "OK" if not errs else "FAIL"
        if errs:
            fail += 1
        schema = spec.get("schema") or {}
        print(
            f"[{mark}] {path.name[:40]}\n"
            f"  accept={spec.get('accept')} domain={spec.get('domain')} "
            f"arch={spec.get('archetype')} arches={spec.get('archetypes')}\n"
            f"  {ticket_brief(schema)}\n"
            f"  roles={role_brief(schema)}\n"
            f"  flows={spec.get('flows')}\n"
            f"  oos={spec.get('out_of_mvp_signals') or spec.get('out_of_mvp')}\n"
            + (f"  ERR {errs}\n" if errs else "")
        )
        specs[num] = spec

    print(f"biz summary fail={fail}/{len(files)}\n")

    rt = _runtime()
    if not rt.configured:
        print("=== Island 跳过：无 API Key ===")
        return

    print(f"=== Island LLM 抽检 {sorted(ISLAND_PICK)} ===\n")
    for num in sorted(ISLAND_PICK):
        spec = specs[num]
        before = role_brief(spec.get("schema") or {})
        labels_before = (spec.get("schema") or {}).get("labels") or {}
        app_before = labels_before.get("appName")
        merged, mode = await island_once(spec, rt)
        after = role_brief(merged)
        app_after = (merged.get("labels") or {}).get("appName")
        t_after = ((merged.get("entities") or {}).get("ticket") or {}).get("label")
        print(
            f"[{num}] {mode}\n"
            f"  roles: {before}\n"
            f"      → {after}\n"
            f"  appName: {app_before} → {app_after}\n"
            f"  ticket.label: {((spec.get('schema') or {}).get('entities') or {}).get('ticket', {}).get('label')} → {t_after}\n"
        )


if __name__ == "__main__":
    asyncio.run(main())
