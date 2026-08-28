"""Agent D：交付 QA（LLM 主审；无模型时结构回退）。"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.llm.agents_common import *  # noqa: F403
from app.llm.client import (
    append_deepseek_log,
    budget_ok,
    chat,
    format_usage_detail,
)

_SYS = (
    "你是毕设交付 QA Agent（Drift/Consistency）。根据「结构化上下文 + 文件摘录」审查"
    "文案/菜单/种子是否一致，找出跨领域错词、写死文案、空壳、占位符、菜单与实体不符等问题。"
    "禁止改代码；只输出 JSON：\n"
    '{"ok":boolean,"summary":string,'
    '"findings":[{"level":"error|warn|info","msg":string,"where":string}],'
    '"priorities":string[]}\n'
    "level=error 仅用于会误导答辩/明显错域的问题；其余用 warn/info。"
    "where 填文件路径或 schema 字段名。\n"
    "必须以结构化字段为准：entityKeys / menuKeys / staffPackMenus / traits / capabilities；"
    "文件摘录可能被截断，禁止凭摘录臆造未出现在结构化字段里的实体或菜单。\n"
    "工厂口径（勿误报）：\n"
    "1) entities 槽位常见为 archive/ticket/reservation/order/category；"
    "menus.admin 含 category 且 entityKeys 含 category → 不算缺口；"
    "staffPackMenus 只含本域岗位已挂 pack，勿把未列出的 pack/菜单名当成实体。\n"
    "2) traits.followUp（或旧包 traits.crm）表示跟进表单能力（渠道/下次复核），"
    "是跨域 UI 特征，不是「必须等于 CRM 行业域」；勿因 flavor/题名不含 CRM 而报错。\n"
    "3) NoticeDetail 正文小标题允许 labels.noticeBodyHeading 或中性「正文」。\n"
    "诚实口径（Q-04，必须遵守）：\n"
    "4) 禁止用错域实体名：INTERN≠投递/入职多家；RECRUIT≠周报岗；EVAL≠成绩更正；"
    "MORAL≠评教；BED≠宿舍报修；PARCEL≠跑腿商城；HOTEL≠会议室+小卖部交叉壳；"
    "INSTRUMENT≠纯场地预约；EXAM≠问卷/评教；LOST≠宠物挂号。\n"
    "5) capabilities 未列出的能力不得宣称「已支持/已集成」："
    "人脸/指纹/GPS、真微信支付/支付宝、法大大/CA、RFID/多仓ERP、小程序原生等硬边界"
    "若出现在交付文案且当作本期功能 → level=error；若仅「非本期/不做」说明 → 不算问题。\n"
    "6) accept=reject 或 out_of_mvp 已标缺口时，禁止在 summary 写「可全文答辩/已支持该能力」。"
)

# 交付文案若把硬边界写成「本期已支持」→ 本地确定性报错（不依赖 LLM）
_HARD_BOUNDARY_AS_SUPPORTED = (
    (re.compile(r"(人脸识别|指纹闸机|GPS\s*轨迹|真门禁开锁)"), "生物识别/硬件定位"),
    (re.compile(r"(微信支付|支付宝(支付|对接)|真实支付)"), "真支付对接"),
    (re.compile(r"(法大大|上上签|第三方电子签|CA\s*证书)"), "第三方电子签/CA"),
    (re.compile(r"(RFID\s*盘点|多仓\s*WMS|ERP\s*财务)"), "RFID/多仓ERP"),
)

# 「非本期 / 不做 / 不接」等诚实划界，不算宣称支持
_HONEST_SCOPE = re.compile(
    r"(非本期|本期不|不做|不接|不在本期|不作为本期|不纳入|超出|硬边界|演示级替代|"
    r"仅作为背景|背景对比|调研阶段|扩展能力|必实现项|不实现)"
)

# 域 → 错域实体词（出现在 labels/菜单且像主叙事时 warn）
_WRONG_DOMAIN_ENTITY: dict[str, tuple[str, ...]] = {
    "DOM-INTERN": ("简历投递", "多单位入职", "同时入职多家"),
    "DOM-RECRUIT": ("提交周报", "实习鉴定", "在岗填报"),
    "DOM-EVAL": ("成绩更正", "成绩复核"),
    "DOM-GRADE": ("网上评教", "多维评分"),
    "DOM-BED": ("宿舍报修", "水电维修"),
    "DOM-DORM": ("床位分配", "调宿申请", "选房"),
    "DOM-PARCEL": ("跑腿代买", "外卖配送"),
    "DOM-HOTEL": ("会议室预约", "小卖部下单"),
    "DOM-LOST": ("门诊挂号", "宠物医院"),
    "DOM-HOSPITAL": ("流浪动物领养", "认领申请"),
}


def _read_clip(path: Path, limit: int = 1800) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")[:limit]


def _menu_keys(menus: Any) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    if not isinstance(menus, dict):
        return out
    for side, items in menus.items():
        if not isinstance(items, list):
            continue
        keys = [str(m.get("key")) for m in items if isinstance(m, dict) and m.get("key")]
        out[str(side)] = keys
    return out


def _delivered_skin(workspace: Path) -> dict[str, Any]:
    """从 appDelivered 抽 traits/flavor（截断摘录读不到文件尾部）。"""
    path = workspace / "frontend" / "src" / "appDelivered.js"
    if not path.exists():
        return {}
    text = path.read_text(encoding="utf-8", errors="ignore")
    out: dict[str, Any] = {}
    fm = re.search(r'"flavor"\s*:\s*"([^"]*)"', text)
    if fm:
        out["flavor"] = fm.group(1)
    dm = re.search(r'"domainLabel"\s*:\s*"([^"]*)"', text)
    if dm:
        out["domainLabel"] = dm.group(1)
    tm = re.search(r'"traits"\s*:\s*(\{[^{}]*\})', text)
    if tm:
        blob = re.sub(r",\s*}", "}", tm.group(1))
        try:
            traits = json.loads(blob)
            if isinstance(traits, dict):
                out["traits"] = traits
        except json.JSONDecodeError:
            pass
    return out


def _collect_qa_context(workspace: Path, spec: dict[str, Any]) -> dict[str, Any]:
    """只采集上下文，不做领域词硬编码判定。"""
    schema = spec.get("schema") if isinstance(spec.get("schema"), dict) else {}
    files: dict[str, Any] = {}
    missing: list[str] = []
    for rel in _QA_FILES:
        path = workspace / rel
        if not path.exists():
            missing.append(rel)
            continue
        files[rel] = _read_clip(path)

    entities_raw = schema.get("entities") if isinstance(schema.get("entities"), dict) else {}
    entities = {
        k: {
            "label": (v or {}).get("label"),
            "labelPlural": (v or {}).get("labelPlural"),
            "verbs": (v or {}).get("verbs"),
            "states": (v or {}).get("states"),
        }
        for k, v in entities_raw.items()
        if isinstance(v, dict)
    }
    menus = schema.get("menus") or {}
    skin = _delivered_skin(workspace)
    traits = skin.get("traits") if isinstance(skin.get("traits"), dict) else {}
    if not traits and isinstance(spec.get("traits"), dict):
        traits = dict(spec["traits"])

    return {
        "domain": spec.get("domain"),
        "title": spec.get("title"),
        "accept": spec.get("accept"),
        "proposal": _proposal_text(spec)[:1500],
        "labels": schema.get("labels") or {},
        "seeds": schema.get("seeds") or {},
        "menus": menus,
        "menuKeys": _menu_keys(menus),
        "entities": entities,
        "entityKeys": sorted(entities.keys()),
        "capabilities": list(schema.get("capabilities") or []),
        "staffPackMenus": schema.get("staffPackMenus") or {},
        "staffPackPages": schema.get("staffPackPages") or {},
        "traits": traits,
        "flavor": skin.get("flavor") or "",
        "domainLabel": skin.get("domainLabel") or "",
        "missing_files": missing,
        "files": files,
    }


def _flatten_label_text(ctx: dict[str, Any]) -> str:
    parts: list[str] = []
    labels = ctx.get("labels") or {}
    if isinstance(labels, dict):
        for v in labels.values():
            if isinstance(v, str):
                parts.append(v)
            elif isinstance(v, list):
                parts.extend(str(x) for x in v)
    menus = ctx.get("menus") or {}
    if isinstance(menus, dict):
        for items in menus.values():
            if not isinstance(items, list):
                continue
            for m in items:
                if isinstance(m, dict):
                    parts.append(str(m.get("label") or ""))
    parts.append(str(ctx.get("domainLabel") or ""))
    parts.append(str(ctx.get("proposal") or "")[:800])
    return "\n".join(parts)


def _honesty_findings(ctx: dict[str, Any]) -> list[dict[str, str]]:
    """Q-04：硬边界不得写成已支持；错域实体名本地可拦。"""
    findings: list[dict[str, str]] = []
    blob = _flatten_label_text(ctx)
    for rx, name in _HARD_BOUNDARY_AS_SUPPORTED:
        for m in rx.finditer(blob):
            # 开题研究现状 / out_scope 列表邻近词常在 ±24 外，放宽到 ±100
            start = max(0, m.start() - 100)
            end = min(len(blob), m.end() + 100)
            window = blob[start:end]
            if _HONEST_SCOPE.search(window):
                continue
            findings.append(
                {
                    "level": "error",
                    "msg": f"交付文案将硬边界「{name}」写成本期可用（附近：{window.strip()[:60]}）",
                    "where": "schema.labels|proposal",
                }
            )
            break

    domain = str(ctx.get("domain") or "")
    forbidden = _WRONG_DOMAIN_ENTITY.get(domain) or ()
    for term in forbidden:
        if term and term in blob:
            # 仅当像主叙事：出现在 labels/菜单短文，且无「≠/不是/非」划界
            idx = blob.find(term)
            window = blob[max(0, idx - 12) : idx + len(term) + 12]
            if re.search(r"(≠|不是|非|勿|禁止|易混)", window):
                continue
            findings.append(
                {
                    "level": "warn",
                    "msg": f"疑似错域实体词「{term}」出现在 {domain} 交付文案",
                    "where": "schema.labels|menus",
                }
            )

    accept = str(ctx.get("accept") or "")
    if accept in ("reject", "partial") or ctx.get("out_of_mvp"):
        # summary 由 LLM 写；本地只在 proposal 宣称「已支持全文」时拦
        if re.search(r"(已支持|可全文答辩|已完整实现).{0,8}(人脸|微信支付|法大大|RFID)", blob):
            findings.append(
                {
                    "level": "error",
                    "msg": "accept/缺口未就绪却宣称硬边界能力已支持",
                    "where": "spec.accept",
                }
            )
    return findings


def _structural_findings(ctx: dict[str, Any]) -> list[dict[str, str]]:
    """本地确定性检查（不依赖 LLM）。"""
    findings: list[dict[str, str]] = []
    for rel in ctx.get("missing_files") or []:
        findings.append({"level": "warn", "msg": f"缺失文件 {rel}", "where": rel})
    labels = ctx.get("labels") or {}
    if not labels.get("noticePageTitle"):
        findings.append({"level": "warn", "msg": "labels.noticePageTitle 缺失", "where": "schema.labels"})
    if not labels.get("appName"):
        findings.append({"level": "warn", "msg": "labels.appName 缺失", "where": "schema.labels"})

    menu_keys = ctx.get("menuKeys") or {}
    admin_keys = set(menu_keys.get("admin") or [])
    entity_keys = set(ctx.get("entityKeys") or [])
    if "category" in admin_keys and "category" not in entity_keys:
        findings.append(
            {
                "level": "warn",
                "msg": "admin 菜单有 category，但 entities 缺少 category 字典实体",
                "where": "schema.entities",
            }
        )

    notice = (ctx.get("files") or {}).get("frontend/src/views/NoticeDetail.vue") or ""
    if ">公告正文<" in notice or "公告正文</h2>" in notice:
        findings.append(
            {
                "level": "warn",
                "msg": "公告详情页写死文案「公告正文」",
                "where": "frontend/src/views/NoticeDetail.vue",
            }
        )
    findings.extend(_honesty_findings(ctx))
    return findings


def _fallback_qa(ctx: dict[str, Any]) -> dict[str, Any]:
    """无 Key / 关 QA 时的结构回退（不写死领域错词表）。"""
    findings = _structural_findings(ctx)
    return {
        "summary": "未启用 LLM QA，仅做结构回退检查",
        "findings": findings,
        "ok": not any(f.get("level") == "error" for f in findings),
        "mode": "fallback",
    }


def _normalize_findings(raw: Any) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    if not isinstance(raw, list):
        return out
    for item in raw[:24]:
        if isinstance(item, str):
            out.append({"level": "warn", "msg": item[:200], "where": ""})
            continue
        if not isinstance(item, dict):
            continue
        level = str(item.get("level") or "warn").lower()
        if level not in ("error", "warn", "info"):
            level = "warn"
        out.append(
            {
                "level": level,
                "msg": str(item.get("msg") or item.get("message") or "")[:200],
                "where": str(item.get("where") or item.get("file") or "")[:120],
            }
        )
    return [f for f in out if f["msg"]]


def _is_noise_finding(msg: str, ctx: dict[str, Any]) -> bool:
    """滤掉与结构化真相矛盾的 LLM 臆造（全厂规则，不绑单一域）。"""
    text = msg or ""
    entity_keys = set(ctx.get("entityKeys") or [])
    menu_flat = {k for keys in (ctx.get("menuKeys") or {}).values() for k in keys}
    pack_menus = ctx.get("staffPackMenus") or {}
    pack_flat = {k for keys in pack_menus.values() for k in (keys or [])}
    traits = ctx.get("traits") or {}

    # 结构化里根本没有 reservation，却报「未使用的 reservation 实体」
    if re.search(r"\breservations?\b", text, re.I):
        if (
            "reservation" not in entity_keys
            and "reservations" not in menu_flat
            and "reservations" not in pack_flat
            and "my_reservations" not in menu_flat
        ):
            if re.search(r"未使用|多余|无关|残留|不该|未定义", text):
                return True

    # 已有 category 实体仍报未定义（只认英文 key，避免误伤正文「分类」文案问题）
    if "category" in entity_keys and re.search(r"\bcategory\b", text, re.I):
        if re.search(r"未定义|缺少|缺失|没有", text):
            return True

    # followUp/crm 是 UI 特征，不是行业名；结构化已开则勿报「与领域无关」
    if traits.get("followUp") or traits.get("crm"):
        if re.search(r"traits\.(crm|followUp)|crm\s*:\s*true|followUp\s*:\s*true", text, re.I):
            if re.search(r"无关|不符|错域|不该|不应", text):
                return True
        if re.search(r"特征标记.*crm|系统特征.*crm", text, re.I) and re.search(
            r"无关|不符|错域", text
        ):
            return True

    # 详情页已用动态正文小标题
    notice = (ctx.get("files") or {}).get("frontend/src/views/NoticeDetail.vue") or ""
    if "公告正文" in text and ("bodyHeading" in notice or ">公告正文<" not in notice):
        return True

    return False


def _filter_findings(findings: list[dict[str, str]], ctx: dict[str, Any]) -> list[dict[str, str]]:
    kept: list[dict[str, str]] = []
    for f in findings:
        if f.get("level") == "info":
            kept.append(f)
            continue
        if _is_noise_finding(str(f.get("msg") or ""), ctx):
            continue
        kept.append(f)
    return kept


def _merge_findings(*groups: list[dict[str, str]]) -> list[dict[str, str]]:
    seen: set[str] = set()
    out: list[dict[str, str]] = []
    for group in groups:
        for f in group:
            key = f"{f.get('level')}|{f.get('where')}|{f.get('msg')}"
            if key in seen:
                continue
            seen.add(key)
            out.append(f)
    return out


async def run_qa_agent(
    db: AsyncSession,
    rt: LlmRuntime,
    *,
    project_id: str,
    workspace: Path,
    spec: dict[str, Any],
) -> dict[str, Any]:
    ctx = _collect_qa_context(workspace, spec)
    use_llm = rt.stage_on("qa_report") and rt.configured and await budget_ok(db, project_id, rt)

    if not use_llm:
        report = _fallback_qa(ctx)
        await record_call(
            db,
            project_id=project_id,
            stage="qa_report",
            tokens=0,
            ok=True,
            detail="回退：仅结构扫描（未调用大模型）",
        )
        write_qa_report(
            workspace, {**report, "domain": ctx.get("domain"), "title": ctx.get("title")}
        )
        return report

    payload = {
        "domain": ctx["domain"],
        "title": ctx["title"],
        "flavor": ctx.get("flavor"),
        "domainLabel": ctx.get("domainLabel"),
        "traits": ctx.get("traits") or {},
        "capabilities": ctx.get("capabilities") or [],
        "accept": ctx["accept"],
        "proposal": ctx["proposal"],
        "labels": ctx["labels"],
        "seeds": ctx["seeds"],
        "menuKeys": ctx.get("menuKeys") or {},
        "entityKeys": ctx.get("entityKeys") or [],
        "entities": ctx["entities"],
        "staffPackMenus": ctx.get("staffPackMenus") or {},
        "staffPackPages": ctx.get("staffPackPages") or {},
        "missing_files": ctx["missing_files"],
        "file_excerpts": ctx["files"],
    }
    messages = [
        {"role": "system", "content": _SYS},
        {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
    ]
    res = await chat(rt, messages, json_mode=True, temperature=0.25, timeout=120.0)
    append_deepseek_log(project_id, f"qa ok={res.ok} {format_usage_detail(res)}")

    if not res.ok or not res.data:
        report = _fallback_qa(ctx)
        report["summary"] = f"LLM QA 失败，回退结构检查 · {res.error or 'no json'}"
        report["mode"] = "fallback_after_llm_error"
        await record_call(
            db,
            project_id=project_id,
            stage="qa_report",
            tokens=res.tokens,
            ok=False,
            detail=format_usage_detail(res, "质量摘要：大模型失败"),
        )
        write_qa_report(
            workspace, {**report, "domain": ctx.get("domain"), "title": ctx.get("title")}
        )
        return report

    data = res.data
    llm_findings = _normalize_findings(data.get("findings"))
    for p in data.get("priorities") or []:
        llm_findings.append({"level": "info", "msg": str(p)[:200], "where": "priority"})
    llm_findings = _filter_findings(llm_findings, ctx)
    findings = _merge_findings(_structural_findings(ctx), llm_findings)

    # ok 以过滤后的 error 为准，避免模型对 warn 也打 ok=False
    ok = not any(f.get("level") == "error" for f in findings)
    summary = str(data.get("summary") or "").strip()
    warn_n = len([f for f in findings if f.get("level") in ("error", "warn")])
    if not summary:
        summary = (
            f"LLM QA 完成 · {warn_n} 条发现" if warn_n else "LLM QA 未发现明显问题"
        )
    elif ok and warn_n == 0:
        # 模型摘要可能仍写着旧误报；过滤后无问题则改写
        if re.search(r"不一致|写死|无关|未使用|未定义", summary):
            summary = "LLM QA 未发现明显问题"
    report = {
        "domain": ctx.get("domain"),
        "title": ctx.get("title"),
        "summary": summary[:800],
        "findings": findings,
        "ok": ok,
        "mode": "llm",
    }
    await record_call(
        db,
        project_id=project_id,
        stage="qa_report",
        tokens=res.tokens,
        ok=True,
        detail=format_usage_detail(res, summary[:400]),
    )
    write_qa_report(workspace, report)
    return report
