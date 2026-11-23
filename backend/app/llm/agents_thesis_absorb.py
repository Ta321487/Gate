"""终稿吸收：LLM 主抽角色/实体/功能 + 覆盖预选（章节温度证据包）。"""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.bake.catalog import catalog_brief_for_match
from app.llm.client import (
    append_deepseek_log,
    chat,
    format_usage_detail,
    monthly_tokens_used,
    record_call,
)
from app.llm.runtime import LlmRuntime
from app.llm.temperature import temperature_for
from app.services.thesis_absorb_extract import (
    _impl_confirm_labels,
    build_absorb_evidence,
    contract_roles_from_proposal,
    fallback_drafts_no_llm,
    finalize_feature_lines,
    normalize_llm_drafts,
)

STAGE = "thesis_absorb_drafts"
PROMPT_ID = "ta-drafts-v6"
_PID = "gf-thesis-absorb"

_SYSTEM = (
    "你是毕设港「终稿吸收」抽取器。只输出一个 JSON 对象，不要 Markdown，不要解释。\n"
    "\n"
    "字段（必须齐全）：\n"
    '{"roles":[],"entities":[],"features":[],'
    '"coverage":"unknown|covered|skin_gap|domain_gap",'
    '"coverage_note":"","notes":""}\n'
    "\n"
    "产品口径（最高优先级）：\n"
    "论文遣词会变（查重改写、口语、UML 类名腔都常见）——你负责读懂写法差异；"
    "只输出**合同形态**短名，不要照抄口语尾巴或类图「××类」。\n"
    "忠于原文：须材料里提到、且有实义（角色岗 / 菜单级功能 / 可建表实体）；"
    "【P3】实现菜单或【P4】结构图能交叉的优先；"
    "禁止把「系统管理员/仓库管理员……」岗名剥成功能「系统管理/仓库管理」；"
    "禁止把「系统首页/首页展示」编成「首页管理」（材料写「系统首页管理」才可收）。\n"
    "\n"
    "三分法（严格）：\n"
    "- roles：业务角色/端岗名（用户、管理员、厂商、经销商…）。读【P2】；【P1】「××端」可补。"
    "「系统管理员/后台管理员」→「管理员」。\n"
    "- entities：库表业务短名（去「表」字）。主矿【P1-库表】与表题注；"
    "题注有的必须进（含关于我们/投诉纠纷/系统简介等真表）；无题注不发明过程词。\n"
    "- features：菜单/模块短名，**稳形态「××管理」**（或材料里等价的模块入口名）。"
    "读【P1】设计 + 用【P3】/【P4】确认实义；有实现菜单时用具体入口名。"
    "禁止空壳：系统管理、首页管理、基础管理、功能管理、模块管理、业务管理、信息管理、数据管理；"
    "禁止步骤句、测试项、目录/可行性；禁止 UML「用户类/管理员类」当功能。\n"
    "\n"
    "覆盖预选（对照「现厂能力简报」，不是出包匹配）：\n"
    "- covered：现厂主流程壳已能盖住论文主路径。\n"
    "- skin_gap：壳大致有，差行业词/种子/眉标/分类轴。\n"
    "- domain_gap：主流程盖不住或缺必备能力。\n"
    "- unknown：证据不足或吃不准——宁可 unknown，禁止硬标 covered。\n"
    "- coverage_note：≤40 字。\n"
    "\n"
    "章节温度：【P1-模块】【P3】【P4】一起定 features；【P1-库表】定 entities；【P2】定 roles；"
    "未提供的等级不得脑补。\n"
    "\n"
    "禁止写入三栏：前端、后端、协议、传输、回传、控制器、框架名；"
    "以「与」「及」开头的半截；「这些功能」「可以进行操作」等口语；"
    "可进入、点击、填写、登录后、如图、所示。\n"
    "\n"
    "形态：每项 2～12 个汉字短名；roles≤8；entities≤24；features≤32；"
    "角色名与实体名允许相同；notes 证据不足时写「弱抽：缺P1/缺P2/缺库表」或空串。\n"
)

_WARN = {
    "llm_no_key": "未配置可用大模型 Key（运行环境 → LLM）",
    "llm_stage_off": "阶段「终稿吸收三栏」已关闭",
    "llm_budget": "本月 Token 预算已用尽",
    "llm_call_fail": "大模型调用失败或返回无法校验",
    "llm_thin_evidence": "证据包偏薄（缺 P1 或 P2 重点章）",
}


def _trim(s: str, n: int) -> str:
    t = (s or "").strip()
    return t if len(t) <= n else t[: n - 1] + "…"


def _user_payload(evidence: dict[str, Any], catalog: str) -> str:
    packs = {p["grade"]: p for p in evidence.get("packs") or [] if isinstance(p, dict)}
    caps = "、".join(evidence.get("table_captions") or []) or "（无）"
    p2 = packs.get("P2", {})
    p1m = packs.get("P1-modules", {})
    p1t = packs.get("P1-tables", {})
    p3 = packs.get("P3", {})
    p4 = packs.get("P4", {})
    return (
        f"题名：{evidence.get('title') or '（无）'}\n\n"
        f"【P2·需求用例·角色主矿】\n{_trim(str(p2.get('text') or '（无）'), 3500)}\n\n"
        f"【P1·模块设计·功能主矿】\n{_trim(str(p1m.get('text') or '（无）'), 4000)}\n\n"
        f"【P1·库表·实体主矿】\n表题注：{caps}\n"
        f"{_trim(str(p1t.get('text') or '（无）'), 3000)}\n\n"
        f"【P3·实现测试·仅佐证】\n{_trim(str(p3.get('text') or '（无）'), 1500)}\n\n"
        f"【P4·图标签·可选】\n{_trim(str(p4.get('text') or '（无）'), 800)}\n\n"
        f"【现厂能力简报·仅供覆盖预选】\n{_trim(catalog, 2500)}\n\n"
        "请按 System 规则输出 JSON。"
    )


def _validate_raw(data: dict[str, Any] | None) -> list[str]:
    errs: list[str] = []
    if not isinstance(data, dict):
        return ["非 JSON 对象"]
    for k in ("roles", "entities", "features"):
        if not isinstance(data.get(k), list):
            errs.append(f"{k} 须为数组")
    cov = str(data.get("coverage") or "").strip()
    if cov not in {"unknown", "covered", "skin_gap", "domain_gap"}:
        errs.append("coverage 非法")
    return errs


async def run_thesis_absorb_drafts_agent(
    db: AsyncSession,
    rt: LlmRuntime,
    *,
    text: str,
    proposal: dict[str, Any] | None,
    record_id: int | None = None,
) -> dict[str, Any]:
    """返回 draft_* / coverage / coverage_note / warnings / used_llm / prompt_id。"""
    evidence = build_absorb_evidence(text, proposal=proposal)
    fb = fallback_drafts_no_llm(proposal)
    thin = bool(evidence.get("thin_p1") or evidence.get("thin_p2"))
    base_warns: list[str] = []
    if thin:
        base_warns.append(_WARN["llm_thin_evidence"])

    pid = f"{_PID}-{record_id}" if record_id else _PID

    def _fail(code: str, detail: str = "") -> dict[str, Any]:
        msg = _WARN.get(code, code)
        if detail:
            msg = f"{msg}：{detail}"[:160]
        warns = list(base_warns)
        if msg not in warns:
            warns.append(msg)
        return {
            **fb,
            "coverage": "unknown",
            "coverage_note": "",
            "warnings": warns,
            "used_llm": False,
            "skip_reason": code,
            "prompt_id": PROMPT_ID,
            "evidence_grades": [p.get("grade") for p in evidence.get("packs") or []],
        }

    if not rt.stage_on(STAGE):
        return _fail("llm_stage_off")
    if not rt.configured:
        return _fail("llm_no_key")
    monthly = await monthly_tokens_used(db)
    if monthly >= rt.monthly_token_budget:
        append_deepseek_log(pid, f"{STAGE} skip · monthly budget")
        return _fail("llm_budget")

    catalog = catalog_brief_for_match()
    user1 = _user_payload(evidence, catalog)
    messages = [
        {"role": "system", "content": _SYSTEM},
        {"role": "user", "content": user1},
    ]
    res = await chat(
        rt,
        messages,
        json_mode=True,
        temperature=temperature_for(STAGE),
        timeout=120.0,
    )
    await record_call(
        db,
        project_id=pid,
        stage=STAGE,
        tokens=res.tokens,
        ok=res.ok and bool(res.data),
        detail=format_usage_detail(res, "终稿吸收三栏"),
    )
    append_deepseek_log(pid, f"{STAGE} ok={res.ok} {format_usage_detail(res)}")

    data = res.data if isinstance(res.data, dict) else None
    errs = _validate_raw(data)
    if errs and res.ok:
        messages.append(
            {
                "role": "user",
                "content": (
                    "上次输出未通过校验："
                    + "；".join(errs)
                    + "。请只修正后重新输出完整 JSON；不要解释。"
                ),
            }
        )
        res2 = await chat(
            rt,
            messages,
            json_mode=True,
            temperature=temperature_for(STAGE),
            timeout=120.0,
        )
        await record_call(
            db,
            project_id=pid,
            stage=STAGE,
            tokens=res2.tokens,
            ok=res2.ok and bool(res2.data),
            detail=format_usage_detail(res2, "终稿吸收三栏重试"),
        )
        data = res2.data if isinstance(res2.data, dict) else None
        errs = _validate_raw(data)
        res = res2

    if not res.ok or errs or not data:
        return _fail("llm_call_fail", "；".join(errs) if errs else (res.error or ""))

    caps = list(evidence.get("table_captions") or [])
    prop = proposal if isinstance(proposal, dict) else {}
    hints = [
        str(x).strip()
        for x in list(prop.get("entity_hints") or [])
        if isinstance(x, str) and str(x).strip()
    ]
    # 实现/图只作交叉锚；不把正则采矿的 feature_lines/module_hints 当硬门闩
    p3_pack = next(
        (
            p
            for p in (evidence.get("packs") or [])
            if isinstance(p, dict) and p.get("grade") == "P3"
        ),
        None,
    )
    p3_text = str((p3_pack or {}).get("text") or "")
    confirm_feats = _impl_confirm_labels(p3_text.splitlines(), limit=40)
    fig_labs = [
        str(x).strip()
        for x in list(prop.get("figure_labels") or [])
        + list(prop.get("structure_captions") or [])
        if isinstance(x, str) and str(x).strip()
    ]
    p4_pack = next(
        (
            p
            for p in (evidence.get("packs") or [])
            if isinstance(p, dict) and p.get("grade") == "P4"
        ),
        None,
    )
    if p4_pack and p4_pack.get("text"):
        fig_labs.extend(
            x.strip()
            for x in str(p4_pack["text"]).replace("、", ",").split(",")
            if x.strip()
        )
    confirm_feats = finalize_feature_lines(confirm_feats + fig_labs, limit=48)
    norm = normalize_llm_drafts(
        data.get("roles"),
        data.get("entities"),
        data.get("features"),
        table_captions=caps,
        entity_hints=hints,
        design_features=None,
        confirm_features=confirm_feats,
    )
    cov = str(data.get("coverage") or "unknown").strip()
    if cov not in {"unknown", "covered", "skin_gap", "domain_gap"}:
        cov = "unknown"
    note = str(data.get("coverage_note") or "").strip()[:80]
    warns = list(base_warns)
    extra = str(data.get("notes") or "").strip()
    if extra and extra not in warns:
        warns.append(extra[:120])
    # 实体：题注底 + LLM；题注非空时不得被 LLM 空列表冲掉
    ents = list(norm["draft_entities"] or []) or list(fb["draft_entities"] or [])
    # 角色：LLM 空时回填合同端名（禁止「实体有管理员、角色可空」）
    roles = list(norm["draft_roles"] or []) or contract_roles_from_proposal(prop)
    return {
        "draft_roles": roles,
        "draft_entities": ents,
        "draft_features": norm["draft_features"],
        "coverage": cov,
        "coverage_note": note,
        "warnings": warns,
        "used_llm": True,
        "skip_reason": "",
        "prompt_id": PROMPT_ID,
        "evidence_grades": [p.get("grade") for p in evidence.get("packs") or []],
    }
