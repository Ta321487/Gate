"""项目服务门面：兼容 ``from app.services import projects`` / ``projects.xxx``。

正文已按职责搬到 project_delivery / project_disk / project_projection / project_match。
新逻辑请直接进对应家，不要再往本文件堆正文。
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.bake.gates import evaluate_domain_gates  # noqa: F401  # 测试 patch 兼容
from app.core.config import get_settings  # noqa: F401
from app.core.key_mask import mask_key
from app.models import Project, ProjectStatus
from app.services import runtime as rt  # noqa: F401  # 测试 patch 兼容
from app.services.project_delivery import (  # noqa: F401
    DELIVERY_MARKS,
    MSG_DOWNLOAD_GATES,
    MSG_DOWNLOAD_GENERATING,
    MSG_DOWNLOAD_NO_ZIP,
    MSG_DOWNLOAD_OPEN_FIX_NOTES,
    MSG_DOWNLOAD_REVIEW_REGRESSION,
    MSG_DOWNLOAD_ZIP_MISSING,
    MSG_DOWNLOAD_ZIP_STALE,
    MSG_PREVIEW_GENERATING,
    MSG_WS_GONE,
    MSG_WS_MISSING,
    apply_delivery_mark,
    delivery_block_reason,
    gates_allow_delivery,
    is_zip_downloadable,
    normalize_delivery_mark,
    preview_start_block_reason,
    reset_delivery_mark,
    set_delivery_mark,
    touch_json_fields,
    workspace_or_reason,
)
from app.services.project_disk import (  # noqa: F401
    purge_orphan_project_disk,
    purge_project_disk,
    remove_project_logs,
    remove_project_source_if_owned,
    remove_project_zips,
    remove_tree_reliable,
    resolve_workspace_dir,
)
from app.services.project_match import (  # noqa: F401
    create_from_upload,
    create_from_uploads,
    ensure_proposal_in_spec,
    load_proposal_summary,
    update_match,
)
from app.services.project_projection import (  # noqa: F401
    _CHECKLIST_LIST_TTL_SEC,
    ensure_project_ports,
    reclaim_idle_ports,
    reconcile_list_items,
    reconcile_lock,
    release_read_transaction,
    reset_checklist_list_cache,
    sync_checklist_for_list,
    sync_checklist_from_workspace,
    sync_project_runtime,
    workspace_signature,
)

__all__ = [
    "DELIVERY_MARKS",
    "MSG_DOWNLOAD_GATES",
    "MSG_DOWNLOAD_GENERATING",
    "MSG_DOWNLOAD_NO_ZIP",
    "MSG_DOWNLOAD_OPEN_FIX_NOTES",
    "MSG_DOWNLOAD_REVIEW_REGRESSION",
    "MSG_DOWNLOAD_ZIP_MISSING",
    "MSG_DOWNLOAD_ZIP_STALE",
    "MSG_PREVIEW_GENERATING",
    "MSG_WS_GONE",
    "MSG_WS_MISSING",
    "apply_delivery_mark",
    "create_from_upload",
    "create_from_uploads",
    "delivery_block_reason",
    "ensure_project_ports",
    "ensure_proposal_in_spec",
    "gates_allow_delivery",
    "is_zip_downloadable",
    "load_proposal_summary",
    "mask_key",
    "normalize_delivery_mark",
    "preview_start_block_reason",
    "purge_orphan_project_disk",
    "purge_project_disk",
    "reclaim_idle_ports",
    "reconcile_list_items",
    "reconcile_lock",
    "release_read_transaction",
    "remove_project_logs",
    "remove_project_source_if_owned",
    "remove_project_zips",
    "remove_tree_reliable",
    "reset_checklist_list_cache",
    "reset_delivery_mark",
    "resolve_workspace_dir",
    "set_delivery_mark",
    "stats",
    "sync_checklist_for_list",
    "sync_checklist_from_workspace",
    "sync_project_runtime",
    "touch_json_fields",
    "update_match",
    "workspace_or_reason",
    "workspace_signature",
]


async def stats(db: AsyncSession) -> dict:
    # 只读库计数 + 只读投影缓存，不扫工作区。zip_ready / delivery_mark 由 /projects 列表收敛；
    # 同页并行时两边都扫盘会堵事件循环（每个项目要遍历约 1.4 万文件），
    # 且曾占着 SQLite 读锁互相 busy 数秒。过期判定由后台对账线程投影。
    result = await db.execute(select(Project))
    items = list(result.scalars().all())

    total = len(items)
    generating = sum(
        1 for p in items if p.status == ProjectStatus.generating.value
    )
    previewable = sum(
        1
        for p in items
        if p.status
        in (ProjectStatus.generated.value, ProjectStatus.running.value)
    )
    pending_review = sum(
        1
        for p in items
        if p.status
        in (ProjectStatus.generated.value, ProjectStatus.running.value)
        and is_zip_downloadable(p, verify_stale=False)
        and normalize_delivery_mark(getattr(p, "delivery_mark", None)) == "none"
    )
    delivery_ready = sum(
        1
        for p in items
        if normalize_delivery_mark(getattr(p, "delivery_mark", None)) == "ready"
    )
    delivery_delivered = sum(
        1
        for p in items
        if normalize_delivery_mark(getattr(p, "delivery_mark", None)) == "delivered"
    )
    from app.llm.client import monthly_tokens_breakdown

    tokens_bd = await monthly_tokens_breakdown(db)
    s = get_settings()
    return {
        "total": total,
        "generating": generating,
        "previewable": previewable,
        "pending_review": int(pending_review),
        "delivery_ready": int(delivery_ready),
        "delivery_delivered": int(delivery_delivered),
        "monthly_tokens": int(tokens_bd["total"]),
        "monthly_tokens_pipeline": int(tokens_bd["pipeline"]),
        "monthly_tokens_support": int(tokens_bd["support"]),
        "monthly_budget": s.monthly_token_budget,
    }

