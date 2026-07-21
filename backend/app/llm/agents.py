"""四个窄 Agent：只碰白名单 JSON / 诊断，不生成业务 Java/Vue。"""

from __future__ import annotations

import asyncio
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.bake.domain_schema import (
    deterministic_llm_patch,
    merge_schema,
    validate_schema,
)
from app.bake.engine import emit_schema_to_workspace, llm_fill_islands
from app.llm.client import (
    append_deepseek_log,
    budget_ok,
    chat,
    format_usage_detail,
    record_call,
    write_qa_report,
)
from app.llm.runtime import LlmRuntime
from app.services.runtime import _resolve_cmd

# 填岛允许 LLM 改写的 labels 键（页面文案）
_LABEL_KEYS = (
    "appName",
    "authEyebrow",
    "authLead",
    "authPoints",
    "registerRoleHint",
    "noticePageTitle",
    "noticePageLead",
)
_SEED_KEYS = ("noticeTitle", "noticeBody")


def _proposal_text(spec: dict[str, Any]) -> str:
    prop = spec.get("proposal")
    if isinstance(prop, dict):
        parts = [
            prop.get("title"),
            prop.get("background"),
            "\n".join(prop.get("feature_lines") or []),
            "\n".join(prop.get("out_scope_lines") or []),
            prop.get("excerpt"),
        ]
        return "\n".join(str(x) for x in parts if x)
    return str(prop or "")


# ---------- Agent A：Spec ----------
async def run_spec_agent(
    db: AsyncSession,
    rt: LlmRuntime,
    *,
    project_id: str,
    raw_text: str,
    spec: dict[str, Any],
) -> dict[str, Any]:
    """润色 proposal / 功能点摘要；不改 archetype/domain。"""
    if not (rt.stage_on("parse_spec") and rt.configured):
        return spec
    if not await budget_ok(db, project_id, rt):
        append_deepseek_log(project_id, "spec skip · budget exceeded")
        return spec

    domain = spec.get("domain") or ""
    title = spec.get("title") or ""
    excerpt = (raw_text or "")[:6000]
    messages = [
        {
            "role": "system",
            "content": (
                "你是毕设开题 Spec Agent。只输出 JSON，不要 markdown。"
                "禁止改技术栈/造新表/改领域 ID。"
                "字段：title(string), background(string), feature_lines(string[]), "
                "out_scope_lines(string[]), summary(string)。"
                "feature_lines≤8，out_scope_lines≤5，中文短句。"
            ),
        },
        {
            "role": "user",
            "content": (
                f"已匹配领域={domain}，当前标题={title}\n"
                f"开题摘录：\n{excerpt}"
            ),
        },
    ]
    res = await chat(rt, messages, json_mode=True, temperature=0.2)
    await record_call(
        db,
        project_id=project_id,
        stage="parse_spec",
        tokens=res.tokens,
        ok=res.ok and bool(res.data),
        detail=format_usage_detail(res, "spec enrich"),
    )
    append_deepseek_log(
        project_id,
        f"spec ok={res.ok} {format_usage_detail(res)}",
    )
    if not res.ok or not res.data:
        return spec

    data = res.data
    prop = dict(spec.get("proposal") or {})
    if data.get("title"):
        prop["title"] = str(data["title"])[:120]
        # 仅当标题明显更好时同步 spec.title（上传后未确认前可改）
        if not spec.get("title") or len(str(data["title"])) > 4:
            spec["title"] = str(data["title"])[:120]
    if data.get("background"):
        prop["background"] = str(data["background"])[:400]
    if data.get("summary"):
        prop["summary"] = str(data["summary"])[:400]
    if isinstance(data.get("feature_lines"), list):
        prop["feature_lines"] = [str(x)[:80] for x in data["feature_lines"][:8]]
    if isinstance(data.get("out_scope_lines"), list):
        prop["out_scope_lines"] = [str(x)[:80] for x in data["out_scope_lines"][:5]]
    prop["llm_enriched"] = True
    spec["proposal"] = prop
    return spec


# ---------- Agent B：填岛 ----------
def _sanitize_island_patch(data: dict[str, Any], base_labels: dict, base_seeds: dict) -> dict[str, Any]:
    labels: dict[str, Any] = {}
    src_l = data.get("labels") if isinstance(data.get("labels"), dict) else data
    for k in _LABEL_KEYS:
        if k in src_l and src_l[k] is not None:
            v = src_l[k]
            if k == "authPoints" and isinstance(v, list):
                labels[k] = [str(x)[:40] for x in v[:6]]
            else:
                labels[k] = str(v)[:200]
    # 领域专名标题：若基线已有 noticePageTitle，LLM 可润色但保留非空
    if not labels.get("noticePageTitle") and base_labels.get("noticePageTitle"):
        labels["noticePageTitle"] = base_labels["noticePageTitle"]
    seeds: dict[str, Any] = {}
    src_s = data.get("seeds") if isinstance(data.get("seeds"), dict) else {}
    for k in _SEED_KEYS:
        if k in src_s and src_s[k] is not None:
            seeds[k] = str(src_s[k])[:500]
        elif k in data and isinstance(data.get(k), str):
            seeds[k] = str(data[k])[:500]
    if not seeds.get("noticeTitle") and base_seeds.get("noticeTitle"):
        seeds["noticeTitle"] = base_seeds["noticeTitle"]
    # 实体文案：仅 verbs/states/label
    entities_out: dict[str, Any] = {}
    ents = data.get("entities") if isinstance(data.get("entities"), dict) else {}
    for ek, ev in ents.items():
        if not isinstance(ev, dict):
            continue
        piece: dict[str, Any] = {}
        if ev.get("label"):
            lab = str(ev["label"])[:40].strip()
            # 动作名词勿带「记录」（与 merge_schema 一致）
            if ek in ("reservation", "ticket") and lab.endswith("记录") and len(lab) > 2:
                lab = lab.removesuffix("记录").strip() or lab
            piece["label"] = lab
        if ev.get("labelPlural"):
            piece["labelPlural"] = str(ev["labelPlural"])[:40]
        if isinstance(ev.get("verbs"), dict):
            piece["verbs"] = {str(k): str(v)[:40] for k, v in list(ev["verbs"].items())[:12]}
        if isinstance(ev.get("states"), dict):
            piece["states"] = {str(k): str(v)[:40] for k, v in list(ev["states"].items())[:12]}
        if piece:
            entities_out[ek] = piece
    patch: dict[str, Any] = {"mode": "llm", "labels": labels, "seeds": seeds}
    if entities_out:
        patch["entities"] = entities_out
    if data.get("title"):
        patch["title"] = str(data["title"])[:120]
    return patch


async def run_island_agent(
    db: AsyncSession,
    rt: LlmRuntime,
    *,
    project_id: str,
    workspace: Path,
    spec: dict[str, Any],
    llm_enabled: bool,
) -> tuple[list[str], str]:
    """
    返回 (written_paths, mode_meta)。
    无 Key / 关开关 / 超预算 → 确定性填岛。
    """
    use_llm = bool(llm_enabled and rt.stage_on("island_fill") and rt.configured)
    if use_llm and not await budget_ok(db, project_id, rt):
        use_llm = False
        append_deepseek_log(project_id, "island skip llm · budget exceeded")

    base = spec.get("schema") or {}
    if not use_llm:
        written = llm_fill_islands(workspace, spec, llm_enabled)
        await record_call(
            db,
            project_id=project_id,
            stage="emit",
            tokens=0,
            ok=True,
            detail="deterministic," + ",".join(written),
        )
        return written, "deterministic"

    labels = dict(base.get("labels") or {})
    seeds = dict(base.get("seeds") or {})
    domain = spec.get("domain") or ""
    title = spec.get("title") or labels.get("appName") or "毕设系统"
    messages = [
        {
            "role": "system",
            "content": (
                "你是毕设港 Island Agent。只输出 JSON："
                '{"title","labels":{...},"seeds":{noticeTitle,noticeBody},"entities":{ticket?:{label,labelPlural,verbs,states},reservation?:{label,labelPlural,states}}}。'
                "labels 可含: " + ",".join(_LABEL_KEYS) + "。"
                "禁止改 menus/capabilities/路由/表结构；禁止输出代码。"
                "文案必须贴合领域，禁止出现其它领域错词（如宿舍系统勿写馆内/借阅）。"
                "entities.reservation/ticket 的 label 须为短动作名词（如挂号/预约/借阅），禁止带「记录」；「XX记录」仅用于管理端菜单。"
            ),
        },
        {
            "role": "user",
            "content": json.dumps(
                {
                    "domain": domain,
                    "title": title,
                    "current_labels": labels,
                    "current_seeds": seeds,
                    "proposal": _proposal_text(spec)[:2500],
                    "entities_keys": list((base.get("entities") or {}).keys()),
                },
                ensure_ascii=False,
            ),
        },
    ]
    res = await chat(rt, messages, json_mode=True, temperature=0.35)
    append_deepseek_log(
        project_id,
        f"island ok={res.ok} {format_usage_detail(res)}",
    )

    patch = deterministic_llm_patch(spec, True)
    mode = "llm_fallback_deterministic"
    if res.ok and res.data:
        try:
            llm_patch = _sanitize_island_patch(res.data, labels, seeds)
            merged_try = merge_schema(base, llm_patch)
            for k in ("accept", "missing_capabilities", "out_of_mvp_signals", "capabilities"):
                if k in base:
                    merged_try[k] = base[k]
            ok, errors = validate_schema(merged_try)
            if ok:
                patch = llm_patch
                mode = "llm"
            else:
                append_deepseek_log(project_id, "island validate fail · " + "; ".join(errors[:3]))
        except Exception as e:  # noqa: BLE001
            append_deepseek_log(project_id, f"island merge fail · {e}")

    merged = merge_schema(base, patch)
    for k in ("accept", "missing_capabilities", "out_of_mvp_signals", "capabilities"):
        if k in base:
            merged[k] = base[k]
    ok, errors = validate_schema(merged)
    if not ok:
        # 最后兜底确定性
        patch = deterministic_llm_patch(spec, False)
        merged = merge_schema(base, patch)
        for k in ("accept", "missing_capabilities", "out_of_mvp_signals", "capabilities"):
            if k in base:
                merged[k] = base[k]
        mode = "deterministic_recover"
        ok, errors = validate_schema(merged)
        if not ok:
            await record_call(
                db,
                project_id=project_id,
                stage="island_fill",
                tokens=res.tokens,
                ok=False,
                detail=format_usage_detail(res, "; ".join(errors)),
            )
            raise RuntimeError("schema 校验失败: " + "; ".join(errors))

    spec["schema"] = merged
    if patch.get("title"):
        spec["title"] = patch["title"]
    written = emit_schema_to_workspace(workspace, spec)
    await record_call(
        db,
        project_id=project_id,
        stage="island_fill",
        tokens=res.tokens,
        ok=True,
        detail=format_usage_detail(res, f"{mode}," + ",".join(written)),
    )
    return written, mode


# ---------- Agent C：构建修复（诊断 + 重放填岛，不改 Java/Vue） ----------
def _mvn_compile(workspace: Path) -> tuple[bool, str]:
    be = workspace / "backend"
    if not be.exists():
        return False, "无 backend 目录"
    mvn = _resolve_cmd("mvn")
    if not mvn:
        return True, "skip · 未检测到 mvn"
    try:
        if sys.platform == "win32":
            from subprocess import list2cmdline

            args: str | list[str] = list2cmdline([mvn, "-q", "-DskipTests", "compile"])
            use_shell = True
        else:
            args = [mvn, "-q", "-DskipTests", "compile"]
            use_shell = False
        p = subprocess.run(
            args,
            cwd=str(be),
            capture_output=True,
            text=True,
            timeout=180,
            shell=use_shell,
        )
        out = ((p.stdout or "") + "\n" + (p.stderr or "")).strip()
        if p.returncode == 0:
            return True, (out[-800:] if out else "compile ok")
        return False, out[-2500:] or f"exit {p.returncode}"
    except subprocess.TimeoutExpired:
        return False, "mvn compile timeout 180s"
    except Exception as e:  # noqa: BLE001
        return False, str(e)


async def run_fix_agent(
    db: AsyncSession,
    rt: LlmRuntime,
    *,
    project_id: str,
    workspace: Path,
    spec: dict[str, Any],
) -> tuple[bool, str]:
    """
    结构校验后尝试 mvn compile；失败则 LLM 诊断 + 重放确定性/LLM 填岛（不改业务源码）。
    返回 (ok, meta)。
    """
    ok_be = (workspace / "backend").exists()
    ok_fe = (workspace / "frontend").exists()
    if not (ok_be and ok_fe):
        return False, "骨架不完整"

    if not (rt.stage_on("auto_fix") and rt.configured):
        return True, "结构校验通过 · 未开自动修复"

    # mvn compile 可长达数分钟，必须进线程，否则工厂 API 整体假死
    compile_ok, log = await asyncio.to_thread(_mvn_compile, workspace)
    if compile_ok:
        await record_call(
            db,
            project_id=project_id,
            stage="auto_fix",
            tokens=0,
            ok=True,
            detail="compile ok / skip",
        )
        return True, "结构+编译通过" if "skip" not in log else "结构校验通过 · " + log

    rounds = max(0, int(rt.fix_rounds_max))
    last = log
    total_tokens = 0
    for i in range(rounds):
        if not await budget_ok(db, project_id, rt):
            break
        messages = [
            {
                "role": "system",
                "content": (
                    "你是 Build Fix Agent。工厂禁止改业务 Java/Vue。"
                    "只输出 JSON：{\"diagnosis\":string,\"suggest_schema_tweak\":boolean,\"note\":string}。"
                    "说明失败原因；若像环境/依赖问题，suggest_schema_tweak=false。"
                ),
            },
            {
                "role": "user",
                "content": f"第{i+1}轮编译失败日志：\n{last[:3500]}",
            },
        ]
        res = await chat(rt, messages, json_mode=True, temperature=0.1)
        total_tokens += res.tokens
        append_deepseek_log(
            project_id,
            f"fix#{i+1} ok={res.ok} {format_usage_detail(res)}",
        )
        # 仅重放交付配置，不写业务源码
        try:
            await asyncio.to_thread(emit_schema_to_workspace, workspace, spec)
        except Exception:  # noqa: BLE001
            await asyncio.to_thread(llm_fill_islands, workspace, spec, True)
        compile_ok, last = await asyncio.to_thread(_mvn_compile, workspace)
        if compile_ok:
            await record_call(
                db,
                project_id=project_id,
                stage="auto_fix",
                tokens=total_tokens,
                ok=True,
                detail=f"fixed after {i+1} round(s)",
            )
            return True, f"编译修复成功 · {i+1} 轮"

    await record_call(
        db,
        project_id=project_id,
        stage="auto_fix",
        tokens=total_tokens,
        ok=False,
        detail=(last or "compile failed")[:500],
    )
    # 编译失败不阻断交付（本机缺 JDK/依赖常见）；记警告继续门禁
    return True, f"编译未过已记录 · 继续门禁 · {(last or '')[:120]}"


# ---------- Agent D：QA（LLM 主审；仅无模型时做结构回退） ----------
_QA_FILES = (
    "frontend/src/appDelivered.js",
    "frontend/src/views/Notices.vue",
    "frontend/src/views/NoticeDetail.vue",
    "frontend/src/views/user/MyTickets.vue",
    "frontend/src/layouts/PortalLayout.vue",
    "islands/island_ui_hints.json",
    "islands/island_notice_seed.json",
)


def _read_clip(path: Path, limit: int = 1800) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")[:limit]


def _collect_qa_context(workspace: Path, spec: dict[str, Any]) -> dict[str, Any]:
    """只采集上下文，不做领域词硬编码判定。"""
    schema = spec.get("schema") or {}
    files: dict[str, Any] = {}
    missing: list[str] = []
    for rel in _QA_FILES:
        path = workspace / rel
        if not path.exists():
            missing.append(rel)
            continue
        files[rel] = _read_clip(path)
    return {
        "domain": spec.get("domain"),
        "title": spec.get("title"),
        "accept": spec.get("accept"),
        "proposal": _proposal_text(spec)[:1500],
        "labels": schema.get("labels") or {},
        "seeds": schema.get("seeds") or {},
        "menus": schema.get("menus") or {},
        "entities": {
            k: {
                "label": (v or {}).get("label"),
                "labelPlural": (v or {}).get("labelPlural"),
                "verbs": (v or {}).get("verbs"),
                "states": (v or {}).get("states"),
            }
            for k, v in (schema.get("entities") or {}).items()
            if isinstance(v, dict)
        },
        "missing_files": missing,
        "files": files,
    }


def _fallback_qa(ctx: dict[str, Any]) -> dict[str, Any]:
    """无 Key / 关 QA 时的极简结构回退（不写死领域错词表）。"""
    findings: list[dict[str, str]] = []
    for rel in ctx.get("missing_files") or []:
        findings.append({"level": "warn", "msg": f"缺失文件 {rel}", "where": rel})
    labels = ctx.get("labels") or {}
    if not labels.get("noticePageTitle"):
        findings.append({"level": "warn", "msg": "labels.noticePageTitle 缺失", "where": "schema.labels"})
    if not labels.get("appName"):
        findings.append({"level": "warn", "msg": "labels.appName 缺失", "where": "schema.labels"})
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
            detail="fallback structural only",
        )
        write_qa_report(
            workspace, {**report, "domain": ctx.get("domain"), "title": ctx.get("title")}
        )
        return report

    payload = {
        "domain": ctx["domain"],
        "title": ctx["title"],
        "accept": ctx["accept"],
        "proposal": ctx["proposal"],
        "labels": ctx["labels"],
        "seeds": ctx["seeds"],
        "menus": ctx["menus"],
        "entities": ctx["entities"],
        "missing_files": ctx["missing_files"],
        "file_excerpts": ctx["files"],
    }
    messages = [
        {
            "role": "system",
            "content": (
                "你是毕设交付 QA Agent（Drift/Consistency）。根据领域与摘录审查文案/菜单/种子是否一致，"
                "找出跨领域错词、写死文案、空壳、占位符、菜单与实体不符等问题。"
                "禁止改代码；只输出 JSON：\n"
                '{"ok":boolean,"summary":string,'
                '"findings":[{"level":"error|warn|info","msg":string,"where":string}],'
                '"priorities":string[]}\n'
                "level=error 仅用于会误导答辩/明显错域的问题；其余用 warn/info。"
                "where 填文件路径或 schema 字段名。"
            ),
        },
        {
            "role": "user",
            "content": json.dumps(payload, ensure_ascii=False),
        },
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
            detail=format_usage_detail(res, "qa llm failed"),
        )
        write_qa_report(
            workspace, {**report, "domain": ctx.get("domain"), "title": ctx.get("title")}
        )
        return report

    data = res.data
    findings = _normalize_findings(data.get("findings"))
    for p in data.get("priorities") or []:
        findings.append({"level": "info", "msg": str(p)[:200], "where": "priority"})
    for rel in ctx.get("missing_files") or []:
        if not any(rel in (f.get("where") or "") or rel in f.get("msg", "") for f in findings):
            findings.append({"level": "warn", "msg": f"缺失文件 {rel}", "where": rel})

    ok = data.get("ok")
    if not isinstance(ok, bool):
        ok = not any(f.get("level") == "error" for f in findings)
    summary = str(data.get("summary") or "").strip() or (
        f"LLM QA 完成 · {len(findings)} 条发现" if findings else "LLM QA 未发现明显问题"
    )
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
