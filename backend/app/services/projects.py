from __future__ import annotations

from datetime import datetime
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.bake.catalog import (
    THEME_ALIASES,
    build_spec,
    default_theme,
    match_text,
    normalize_password_hash,
    normalize_theme,
    themes_for_domain,
)
from app.bake.gates import evaluate_domain_gates
from app.core.config import get_settings
from app.models import Project, ProjectStatus
from app.services.proposal import load_merged_proposal_text, summarize_proposal
from app.services import runtime as rt


def _next_id() -> str:
    return f"gf-{datetime.now().strftime('%Y%m%d-%H%M%S')}"


def _db_name(domain: str, project_id: str) -> str:
    short = domain.replace("DOM-", "").lower()
    suffix = project_id.split("-")[-1]
    return f"gf_thesis_{short}_{suffix}"[:64]


async def reclaim_idle_ports(db: AsyncSession, *, keep_id: str | None = None) -> int:
    """未在跑的项目释放端口占用，让库存可大于并发预览数。"""
    listening = rt.listening_tcp_ports()
    result = await db.execute(select(Project))
    n = 0
    for proj in result.scalars().all():
        if keep_id and proj.id == keep_id:
            continue
        if not proj.backend_port and not proj.frontend_port:
            continue
        be_on = rt.side_active(proj.id, proj.backend_port, "backend", listening)
        fe_on = rt.side_active(proj.id, proj.frontend_port, "frontend", listening)
        if be_on or fe_on:
            continue
        proj.backend_port = 0
        proj.frontend_port = 0
        n += 1
        if proj.status == ProjectStatus.running.value:
            proj.status = ProjectStatus.generated.value
    return n


async def ensure_project_ports(db: AsyncSession, project: Project) -> tuple[int, int]:
    """启动预览前租用一对端口；已占用则复用。"""
    await reclaim_idle_ports(db, keep_id=project.id)
    if project.backend_port and project.frontend_port:
        return project.backend_port, project.frontend_port

    q = await db.execute(select(Project.backend_port, Project.frontend_port))
    used_be = {r[0] for r in q.all() if r[0]}
    used_fe = {r[1] for r in q.all() if r[1]}
    s = get_settings()
    listening = rt.listening_tcp_ports()
    used_be |= {p for p in listening if s.backend_port_start <= p <= s.backend_port_end}
    used_fe |= {p for p in listening if s.frontend_port_start <= p <= s.frontend_port_end}
    be, fe = await rt.allocate_ports(used_be, used_fe)
    project.backend_port = be
    project.frontend_port = fe
    await db.flush()
    return be, fe


def sync_project_runtime(project: Project) -> tuple[str, str, bool]:
    """按真实可服务态纠正 running 标记与项目 status；两侧皆停时还端口。

    返回 (backend_status, frontend_status, dirty)。
    """
    be_st = rt.backend_status(project.id, project.backend_port)
    fe_st = rt.frontend_status(project.id, project.frontend_port)
    be = be_st in ("starting", "healthy")
    fe = fe_st in ("starting", "healthy")
    dirty = False
    if project.backend_running != be or project.frontend_running != fe:
        project.backend_running = be
        project.frontend_running = fe
        dirty = True
    if be or fe:
        if project.status not in (
            ProjectStatus.running.value,
            ProjectStatus.generating.value,
        ):
            project.status = ProjectStatus.running.value
            dirty = True
    elif project.status == ProjectStatus.running.value:
        project.status = ProjectStatus.generated.value
        dirty = True
    if not be and not fe and (project.backend_port or project.frontend_port):
        listening = rt.listening_tcp_ports()
        be_listen = bool(project.backend_port and project.backend_port in listening)
        fe_listen = bool(project.frontend_port and project.frontend_port in listening)
        if not be_listen and not fe_listen:
            project.backend_port = 0
            project.frontend_port = 0
            dirty = True
    return be_st, fe_st, dirty


def _feature_names(features: list | None) -> list[str]:
    return [f.get("name", "") for f in (features or []) if isinstance(f, dict)]


def sync_checklist_from_workspace(project: Project) -> bool:
    """工作区存在则按当前门禁逻辑重算 checklist / gates（打开详情即可刷新）。"""
    if not project.workspace_path:
        return False
    ws = Path(project.workspace_path)
    if not ws.exists():
        return False
    gates = evaluate_domain_gates(ws, project.spec or {})
    new_checklist = gates.get("checklist") or []
    new_gates = {k: v for k, v in gates.items() if k != "checklist"}
    deliverable = bool(new_gates.get("zip_allowed") and new_gates.get("overall"))
    generating = project.status == ProjectStatus.generating.value
    zip_exists = bool(project.zip_path and Path(str(project.zip_path)).exists())
    # 门禁回退时关掉 zip_ready；生成中禁止因门禁重算把旧包重新解锁
    zip_changed = False
    if generating:
        if project.zip_ready:
            project.zip_ready = False
            zip_changed = True
    elif deliverable and zip_exists and not project.zip_ready:
        project.zip_ready = True
        zip_changed = True
    elif (not deliverable or not zip_exists) and project.zip_ready:
        project.zip_ready = False
        zip_changed = True
    if project.checklist == new_checklist and project.gates == new_gates and not zip_changed:
        return False
    project.checklist = new_checklist
    project.gates = new_gates
    return True


async def create_from_upload(
    db: AsyncSession,
    file_path: Path,
    filename: str,
    size: int,
) -> Project:
    """兼容旧单文件入口。"""
    return await create_from_uploads(db, [(file_path, filename, size)])


async def create_from_uploads(
    db: AsyncSession,
    files: list[tuple[Path, str, int]],
) -> Project:
    """多材料建项：至少一份；按业务信号加权匹配。"""
    from app.services.proposal import merge_proposal_documents, read_proposal

    if not files:
        raise ValueError("请至少上传一份材料")

    docs: list[tuple[str, str]] = []
    total_size = 0
    for path, name, size in files:
        docs.append((name, read_proposal(path)))
        total_size += int(size or 0)

    match_body, summary_text, file_info, weak_tips = merge_proposal_documents(docs)
    primary_name = files[0][1]
    matched = match_text(match_body, primary_name)
    # 弱材料提示并入 hits（详情页可展示）
    hits = list(matched.hits or [])
    for tip in weak_tips:
        if tip not in hits:
            hits.append(tip)

    pid = _next_id()
    while await db.get(Project, pid):
        pid = _next_id() + f"-{total_size % 97}"

    db_name = _db_name(matched.domain, pid)
    theme = default_theme(matched.domain)
    proposal = summarize_proposal(summary_text, hits)
    proposal["source_files"] = file_info
    spec = build_spec(
        title=matched.title,
        archetype=matched.archetype,
        domain=matched.domain,
        theme=theme,
        llm_enabled=True,
        password_hash="none",
        match_mode="recommended",
        confidence=matched.confidence,
        hits=hits,
        proposal=proposal,
        archetypes=matched.archetypes,
    )
    try:
        from app.llm.agents import run_spec_agent
        from app.llm.runtime import load_llm_runtime

        llm_rt = await load_llm_runtime(db)
        if llm_rt.stage_on("parse_spec") and llm_rt.configured:
            spec = await run_spec_agent(
                db, llm_rt, project_id=pid, raw_text=summary_text, spec=spec
            )
    except Exception:  # noqa: BLE001
        pass

    project_title = str(spec.get("title") or matched.title)
    names = [n for _, n, _ in files]
    joined = "；".join(names)
    if len(joined) > 240:
        joined = joined[:237] + "…"

    # 多文件：目录 + manifest；单文件：仍指向原文件（兼容旧逻辑）
    if len(files) == 1:
        source_path = str(files[0][0])
    else:
        import json

        bundle = files[0][0].parent
        manifest = {
            "files": [
                {"name": name, "path": path.name, "size": size, "score": next(
                    (i["score"] for i in file_info if i["name"] == name), 0
                )}
                for path, name, size in files
            ]
        }
        man_path = bundle / "manifest.json"
        man_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        source_path = str(man_path)

    project = Project(
        id=pid,
        title=project_title,
        status=ProjectStatus.needs_confirm.value,
        source_filename=joined or primary_name,
        source_path=source_path,
        source_size=total_size,
        recommended_arch=matched.archetype,
        recommended_domain=matched.domain,
        confidence=matched.confidence,
        archetype=matched.archetype,
        domain=matched.domain,
        theme=theme,
        llm_enabled=True,
        password_hash="none",
        match_locked=True,
        match_confirmed=False,
        match_mode="recommended",
        db_name=db_name,
        backend_port=0,
        frontend_port=0,
        spec=spec,
        gates={},
        checklist=spec.get("features", []),
    )
    db.add(project)
    await db.commit()
    await db.refresh(project)
    return project


async def update_match(db: AsyncSession, project: Project, body) -> Project:
    # 旧全局主题 id / 跨行业残留 → 规范到当前行业
    project.theme = normalize_theme(project.theme, project.domain)

    if body.reset:
        project.archetype = project.recommended_arch
        project.domain = project.recommended_domain
        project.theme = default_theme(project.domain)
        project.match_locked = True
        project.match_mode = "recommended"
        project.match_confirmed = False

    if body.unlock is True:
        project.match_locked = False
    elif body.unlock is False:
        if project.archetype == project.recommended_arch and project.domain == project.recommended_domain:
            project.match_locked = True

    if body.archetype is not None or body.domain is not None:
        if project.match_locked:
            raise ValueError("骨架/领域已锁定，请先解锁")
        prev_arch, prev_dom = project.archetype, project.domain
        if body.archetype:
            project.archetype = body.archetype
        if body.domain:
            project.domain = body.domain
            project.db_name = _db_name(project.domain, project.id)
            # 换行业模板后，配色必须落在该行业可选集内
            project.theme = normalize_theme(project.theme, project.domain)
        # 改骨架/领域后必须重新确认，避免绕过确认直接生成
        if (project.archetype, project.domain) != (prev_arch, prev_dom) and project.match_confirmed:
            project.match_confirmed = False
            if project.status == ProjectStatus.ready.value:
                project.status = ProjectStatus.needs_confirm.value

    if body.theme is not None:
        allowed = {t["id"] for t in themes_for_domain(project.domain)}
        raw = body.theme
        if raw in THEME_ALIASES:
            raw = THEME_ALIASES[raw]
        if raw not in allowed:
            raise ValueError("该配色不属于当前行业模板")
        project.theme = raw
    if body.llm_enabled is not None:
        project.llm_enabled = body.llm_enabled
    if body.password_hash is not None:
        project.password_hash = normalize_password_hash(body.password_hash)

    deviant = (
        project.archetype != project.recommended_arch
        or project.domain != project.recommended_domain
    )
    project.match_mode = "manual_override" if deviant else "recommended"
    conf = 0.41 if deviant else project.confidence
    if not deviant:
        conf = project.confidence

    old_feature_names = _feature_names((project.spec or {}).get("features"))

    project.spec = build_spec(
        title=project.title,
        archetype=project.archetype,
        domain=project.domain,
        theme=project.theme,
        llm_enabled=project.llm_enabled,
        password_hash=getattr(project, "password_hash", None) or "none",
        match_mode=project.match_mode,
        confidence=conf,
        hits=project.spec.get("hits", []),
        proposal=project.spec.get("proposal"),
        archetypes=[project.archetype]
        if deviant
        else list((project.spec or {}).get("archetypes") or [project.archetype]),
    )
    # 仅功能集变化时重置清单；勿用裸 features 冲掉门禁 result
    new_features = project.spec.get("features") or []
    if _feature_names(new_features) != old_feature_names:
        project.checklist = new_features
    elif project.workspace_path:
        sync_checklist_from_workspace(project)

    if body.confirm:
        if not body.ack:
            raise ValueError("请先勾选确认")
        project.match_confirmed = True
        project.match_locked = True
        project.status = ProjectStatus.ready.value

    await db.commit()
    await db.refresh(project)
    return project


async def stats(db: AsyncSession) -> dict:
    total = await db.scalar(select(func.count()).select_from(Project)) or 0
    generating = await db.scalar(
        select(func.count()).select_from(Project).where(Project.status == ProjectStatus.generating.value)
    ) or 0
    previewable = await db.scalar(
        select(func.count())
        .select_from(Project)
        .where(Project.status.in_([ProjectStatus.generated.value, ProjectStatus.running.value]))
    ) or 0
    from app.llm.client import monthly_tokens_used

    tokens = await monthly_tokens_used(db)
    s = get_settings()
    return {
        "total": total,
        "generating": generating,
        "previewable": previewable,
        "monthly_tokens": int(tokens),
        "monthly_budget": s.monthly_token_budget,
    }


def load_proposal_summary(project: Project) -> dict | None:
    """已有项目若 spec 缺 proposal，从源文件补一份摘要。"""
    if isinstance(project.spec, dict) and project.spec.get("proposal"):
        return project.spec["proposal"]
    if not project.source_path:
        return None
    text = load_merged_proposal_text(project.source_path)
    if not text:
        return None
    hits = (project.spec or {}).get("hits") if isinstance(project.spec, dict) else None
    return summarize_proposal(text, hits)


def ensure_proposal_in_spec(project: Project) -> Project:
    summary = load_proposal_summary(project)
    if not summary:
        return project
    spec = dict(project.spec or {})
    if spec.get("proposal") == summary:
        return project
    spec["proposal"] = summary
    project.spec = spec
    return project


def mask_key(key: str, *, env_name: str = "API_KEY", hint_prefix: str = "") -> str:
    if not key:
        return f"未配置（环境变量 {env_name}）"
    if len(key) < 8:
        return f"{hint_prefix}••••" if hint_prefix else "••••"
    return f"{hint_prefix}••••••••••••{key[-4:]}（来自环境变量）"
