"""项目匹配：上传建项、确认匹配、开题摘要补洞。"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.bake.catalog import (
    THEME_ALIASES,
    CHROME_STYLES,
    LAYOUT_SHELLS,
    PORTAL_HOME_STYLES,
    TYPE_PAIRINGS,
    build_spec,
    pick_theme,
    match_text,
    normalize_password_hash,
    normalize_theme,
    resolve_style_override,
    themes_for_domain,
)
from app.bake.naming import sanitize_delivery_slug, student_db_name, zip_download_name
from app.bake.stack_scan import (
    normalize_ai_assistant,
    normalize_persistence,
    normalize_spring_security,
    scan_stack,
)
from app.core.config import get_settings
from app.models import Project, ProjectStatus
from app.services.project_projection import sync_checklist_from_workspace
from app.services.proposal import load_merged_proposal_text, summarize_proposal

logger = logging.getLogger(__name__)

def _next_id() -> str:
    return f"gf-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

def _db_name(
    domain: str,
    project_id: str,
    slug: str | None = None,
    *,
    reserved: set[str] | None = None,
) -> str:
    s = sanitize_delivery_slug(slug, domain=domain)
    return student_db_name(s, project_id, reserved=reserved)

async def _reserved_db_names(
    db: AsyncSession, *, exclude_id: str | None = None
) -> set[str]:
    """其它项目库名 ∪ 本机已有学生库（防 keep_db / 删库失败残留撞名）。

    exclude_id 对应项目的当前库名不计入本机探测结果，避免改领域时被迫改名。
    """
    result = await db.execute(select(Project.id, Project.db_name))
    out: set[str] = set()
    own_name = ""
    for pid, name in result.all():
        if exclude_id and pid == exclude_id:
            if name:
                own_name = str(name)
            continue
        if name:
            out.add(str(name))
    from app.services.student_db import list_existing_student_db_names

    live = await asyncio.to_thread(list_existing_student_db_names)
    own_l = own_name.lower()
    for n in live:
        if own_l and n.lower() == own_l:
            continue
        out.add(n)
    return out

def _feature_names(features: list | None) -> list[str]:
    return [f.get("name", "") for f in (features or []) if isinstance(f, dict)]

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

    pid = _next_id()
    while await db.get(Project, pid):
        pid = _next_id() + f"-{total_size % 97}"

    llm_rt = None
    try:
        from app.llm.runtime import load_llm_runtime

        llm_rt = await load_llm_runtime(db)
    except Exception:  # noqa: BLE001
        llm_rt = None

    if llm_rt is not None and llm_rt.configured:
        try:
            from app.llm.agents import run_match_agent

            matched = await run_match_agent(
                db, llm_rt, project_id=pid, raw_text=match_body, keyword=matched
            )
        except Exception:  # noqa: BLE001
            pass

    hits = list(matched.hits or [])
    for tip in weak_tips:
        if tip not in hits:
            hits.append(tip)

    match_meta = {
        "source": matched.match_source or "keyword",
        "rationale": matched.rationale or "",
        "alts": list(matched.alts or []),
        "keyword_arch": matched.keyword_arch or matched.archetype,
        "keyword_domain": matched.keyword_domain or matched.domain,
        "delivery_slug": sanitize_delivery_slug(
            matched.delivery_slug, domain=matched.domain
        ),
    }
    match_meta["zip_name"] = zip_download_name(match_meta["delivery_slug"], pid)

    stack = scan_stack(matched.title, match_body)
    persistence = normalize_persistence(stack.get("persistence"))
    spring_security = normalize_spring_security(stack.get("spring_security"))
    ai_assistant = normalize_ai_assistant(stack.get("ai_assistant"))
    match_meta["stack"] = {
        "spine": stack.get("spine") or "spa",
        "recommended_persistence": persistence,
        "recommended_spring_security": spring_security,
        "recommended_ai_assistant": ai_assistant,
        "hits": list(stack.get("hits") or []),
        "warnings": list(stack.get("warnings") or []),
        "addons": dict(stack.get("addons") or {}),
    }
    for tip in stack.get("warnings") or []:
        if tip not in hits:
            hits.append(tip)

    reserved = await _reserved_db_names(db)
    db_name = _db_name(
        matched.domain, pid, match_meta["delivery_slug"], reserved=reserved
    )
    theme = pick_theme(matched.domain, f"{matched.title}|{matched.domain}|theme")
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
        match_meta=match_meta,
        persistence=persistence,
        spring_security=spring_security,
        ai_assistant=ai_assistant,
    )
    spec["delivery_slug"] = match_meta["delivery_slug"]
    spec["zip_name"] = match_meta["zip_name"]

    if llm_rt is not None and llm_rt.configured:
        try:
            from app.llm.agents import run_spec_agent

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
        recommended_persistence=persistence,
        recommended_spring_security=spring_security,
        recommended_ai_assistant=ai_assistant,
        confidence=matched.confidence,
        archetype=matched.archetype,
        domain=matched.domain,
        persistence=persistence,
        spring_security=spring_security,
        ai_assistant=ai_assistant,
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
        project.persistence = normalize_persistence(
            getattr(project, "recommended_persistence", None) or "jdbc"
        )
        project.spring_security = normalize_spring_security(
            getattr(project, "recommended_spring_security", None)
        )
        project.ai_assistant = normalize_ai_assistant(
            getattr(project, "recommended_ai_assistant", None)
        )
        project.theme = pick_theme(
            project.domain, f"{project.title}|{project.domain}|theme"
        )
        project.match_locked = True
        project.match_mode = "recommended"
        project.match_confirmed = False

    if body.unlock is True:
        project.match_locked = False
    elif body.unlock is False:
        if (
            project.archetype == project.recommended_arch
            and project.domain == project.recommended_domain
            and normalize_persistence(getattr(project, "persistence", None))
            == normalize_persistence(getattr(project, "recommended_persistence", None))
            and normalize_spring_security(getattr(project, "spring_security", None))
            == normalize_spring_security(
                getattr(project, "recommended_spring_security", None)
            )
            and normalize_ai_assistant(getattr(project, "ai_assistant", None))
            == normalize_ai_assistant(
                getattr(project, "recommended_ai_assistant", None)
            )
        ):
            project.match_locked = True

    path_fields_touched = (
        getattr(body, "scene", None) is not None
        or getattr(body, "entry", None) is not None
    )
    if (
        body.archetype is not None
        or body.domain is not None
        or getattr(body, "persistence", None) is not None
        or getattr(body, "spring_security", None) is not None
        or getattr(body, "ai_assistant", None) is not None
        or path_fields_touched
    ):
        if project.match_locked:
            raise ValueError("骨架/领域/持久层/鉴权/AI助手/身份入口已锁定，请先解锁")
        prev_arch, prev_dom = project.archetype, project.domain
        prev_pers = normalize_persistence(getattr(project, "persistence", None))
        prev_sec = normalize_spring_security(getattr(project, "spring_security", None))
        prev_ai = normalize_ai_assistant(getattr(project, "ai_assistant", None))
        if body.archetype:
            project.archetype = body.archetype
        if body.domain:
            project.domain = body.domain
            # 换领域后库名跟新领域短码，避免旧 slug 与行业皮错位
            slug = sanitize_delivery_slug(None, domain=project.domain)
            reserved = await _reserved_db_names(db, exclude_id=project.id)
            project.db_name = _db_name(
                project.domain, project.id, slug, reserved=reserved
            )
            # 换行业后：仍合法则保留，否则按种子重选（避免总落第一个）
            allowed = {t["id"] for t in themes_for_domain(project.domain)}
            cur = THEME_ALIASES.get(project.theme, project.theme)
            if cur in allowed:
                project.theme = cur
            else:
                project.theme = pick_theme(
                    project.domain, f"{project.title}|{project.domain}|theme"
                )
        if getattr(body, "persistence", None) is not None:
            project.persistence = normalize_persistence(body.persistence)
        if getattr(body, "spring_security", None) is not None:
            project.spring_security = normalize_spring_security(body.spring_security)
        if getattr(body, "ai_assistant", None) is not None:
            project.ai_assistant = normalize_ai_assistant(body.ai_assistant)
        # 改骨架/领域/持久层/鉴权/AI/路径后必须重新确认，避免绕过确认直接生成
        changed = (
            (project.archetype, project.domain) != (prev_arch, prev_dom)
            or normalize_persistence(getattr(project, "persistence", None)) != prev_pers
            or normalize_spring_security(getattr(project, "spring_security", None))
            != prev_sec
            or normalize_ai_assistant(getattr(project, "ai_assistant", None)) != prev_ai
            or path_fields_touched
        )
        if changed and project.match_confirmed:
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
    prev_spec = project.spec if isinstance(project.spec, dict) else {}
    reset = bool(body.reset)
    chrome_override = resolve_style_override(
        reset=reset,
        body_value=getattr(body, "chrome", None),
        prev_value=prev_spec.get("chrome"),
        catalog=CHROME_STYLES,
        default="soft",
        unknown_message="未知质感样式",
    )
    layout_override = resolve_style_override(
        reset=reset,
        body_value=getattr(body, "layout", None),
        prev_value=prev_spec.get("layout"),
        catalog=LAYOUT_SHELLS,
        default="topbar",
        unknown_message="未知门户布局",
    )
    typeface_override = resolve_style_override(
        reset=reset,
        body_value=getattr(body, "typeface", None),
        prev_value=prev_spec.get("typeface"),
        catalog=TYPE_PAIRINGS,
        default="clean",
        unknown_message="未知字体配对",
    )
    portal_home_override = resolve_style_override(
        reset=reset,
        body_value=getattr(body, "portal_home_style", None),
        prev_value=prev_spec.get("portal_home_style"),
        catalog=PORTAL_HOME_STYLES,
        default="cards",
        unknown_message="未知门户首页构图",
    )
    if body.llm_enabled is not None:
        project.llm_enabled = body.llm_enabled
    if body.password_hash is not None:
        project.password_hash = normalize_password_hash(body.password_hash)

    deviant = (
        project.archetype != project.recommended_arch
        or project.domain != project.recommended_domain
        or normalize_persistence(getattr(project, "persistence", None))
        != normalize_persistence(getattr(project, "recommended_persistence", None))
        or normalize_spring_security(getattr(project, "spring_security", None))
        != normalize_spring_security(
            getattr(project, "recommended_spring_security", None)
        )
        or normalize_ai_assistant(getattr(project, "ai_assistant", None))
        != normalize_ai_assistant(
            getattr(project, "recommended_ai_assistant", None)
        )
    )
    project.match_mode = "manual_override" if deviant else "recommended"
    conf = 0.41 if deviant else project.confidence
    if not deviant:
        conf = project.confidence

    old_feature_names = _feature_names((project.spec or {}).get("features"))
    old_spec = project.spec if isinstance(project.spec, dict) else {}
    match_meta = dict(old_spec.get("match_meta") or {}) if isinstance(old_spec.get("match_meta"), dict) else {}
    # 领域变更：刷新交付短名；否则保留上传时大模型/领域 slug
    if body.domain is not None:
        slug = sanitize_delivery_slug(None, domain=project.domain)
        match_meta["delivery_slug"] = slug
        match_meta["zip_name"] = zip_download_name(slug, project.id)
    elif not match_meta.get("delivery_slug"):
        slug = sanitize_delivery_slug(old_spec.get("delivery_slug"), domain=project.domain)
        match_meta["delivery_slug"] = slug
        match_meta["zip_name"] = zip_download_name(slug, project.id)

    from app.bake.match_path_axes import resolve_match_path

    proposal_blob = old_spec.get("proposal")
    proposal_text = ""
    if isinstance(proposal_blob, dict):
        proposal_text = str(
            proposal_blob.get("excerpt")
            or proposal_blob.get("text")
            or proposal_blob.get("summary")
            or proposal_blob.get("background")
            or ""
        )
    elif isinstance(proposal_blob, str):
        proposal_text = proposal_blob
    prev_path = old_spec.get("match_path") if isinstance(old_spec.get("match_path"), dict) else None
    match_path = resolve_match_path(
        project.domain,
        project.title,
        proposal_text or project.title,
        scene=getattr(body, "scene", None) if not body.reset else None,
        entry=getattr(body, "entry", None) if not body.reset else None,
        prev=None if body.reset else prev_path,
        clear_overrides=bool(body.reset),
    )
    if match_path.get("deviant"):
        deviant = True
        project.match_mode = "manual_override"
        conf = 0.41

    project.spec = build_spec(
        title=project.title,
        archetype=project.archetype,
        domain=project.domain,
        theme=project.theme,
        llm_enabled=project.llm_enabled,
        password_hash=getattr(project, "password_hash", None) or "none",
        match_mode=project.match_mode,
        confidence=conf,
        hits=old_spec.get("hits", []),
        proposal=old_spec.get("proposal"),
        archetypes=[project.archetype]
        if deviant
        else list(old_spec.get("archetypes") or [project.archetype]),
        match_meta=match_meta or None,
        chrome=chrome_override,
        layout=layout_override,
        typeface=typeface_override,
        portal_home_style=portal_home_override,
        persistence=getattr(project, "persistence", None) or "jdbc",
        spring_security=getattr(project, "spring_security", None),
        ai_assistant=getattr(project, "ai_assistant", None),
        match_path=match_path,
    )
    if match_meta.get("delivery_slug"):
        project.spec["delivery_slug"] = match_meta["delivery_slug"]
        project.spec["zip_name"] = match_meta.get("zip_name") or zip_download_name(
            match_meta["delivery_slug"], project.id
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
        path_now = (project.spec or {}).get("match_path") if isinstance(project.spec, dict) else None
        if isinstance(path_now, dict) and path_now.get("needs_path_ack"):
            if not getattr(body, "ack_main_path", None):
                raise ValueError(
                    "开题未写清主路径入口，请解锁选择入口，或勾选「主路径已核对」后再确认"
                )
        project.match_confirmed = True
        project.match_locked = True
        project.status = ProjectStatus.ready.value

    await db.commit()
    await db.refresh(project)
    return project

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

