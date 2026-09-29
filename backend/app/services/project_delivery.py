"""项目交付门禁与人工标记原语。"""

from __future__ import annotations

from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.models import Project, ProjectStatus

def gates_allow_delivery(gates: dict | None) -> bool:
    g = gates if isinstance(gates, dict) else {}
    return bool(g.get("zip_allowed") and g.get("overall"))

MSG_DOWNLOAD_GENERATING = "生成中 · 请等待打包完成后再下载"

MSG_DOWNLOAD_GATES = "质量检查未通过 · 暂不可下载交付包"

MSG_DOWNLOAD_NO_ZIP = "交付包尚未生成或不存在"

MSG_DOWNLOAD_ZIP_MISSING = "ZIP 文件不存在 · 请重新生成"

MSG_DOWNLOAD_ZIP_STALE = "工程已变更 · 请完成验圈并重新合卷后再下载"

MSG_DOWNLOAD_REVIEW_REGRESSION = "复审检测到回退 · 请修复后再验圈"

MSG_DOWNLOAD_OPEN_FIX_NOTES = "仍有未结案复审偏差 · 请先处理后再下载"

MSG_PREVIEW_GENERATING = "生成中 · 请等待完成后再启动预览"

MSG_WS_MISSING = "尚未生成工作区 · 请先完成一键生成"

MSG_WS_GONE = "工作区目录不存在 · 请重新生成"

DELIVERY_MARKS = frozenset({"none", "ready", "delivered"})

def normalize_delivery_mark(raw: str | None) -> str:
    m = str(raw or "none").strip().lower()
    return m if m in DELIVERY_MARKS else "none"

def touch_json_fields(project: Project, *fields: str) -> None:
    """JSON 列整对象替换后必须 flag，否则 commit 可能写不进库（洗文案后 gates 仍脏就是这类）。"""
    for name in fields:
        if hasattr(project, name):
            try:
                flag_modified(project, name)
            except Exception:  # noqa: BLE001
                pass

def reset_delivery_mark(project: Project) -> bool:
    """机器门禁回退或重新生成时清掉人工标记。"""
    cur = str(getattr(project, "delivery_mark", None) or "none")
    if cur == "none":
        return False
    project.delivery_mark = "none"
    return True

def apply_delivery_mark(project: Project, mark: str) -> str:
    """校验并写入 delivery_mark，返回新标记；不写库。"""
    raw = str(mark or "").strip().lower()
    target = normalize_delivery_mark(raw)
    if target != raw:
        raise ValueError("标记须为 none / ready / delivered")
    current = normalize_delivery_mark(getattr(project, "delivery_mark", None))
    if target == current:
        project.delivery_mark = current
        return current
    if target == "ready":
        if delivery_block_reason(project):
            raise ValueError("质量检查未通过 · 请先通过机器质检后再标记已审待发")
        if project.status not in (
            ProjectStatus.generated.value,
            ProjectStatus.running.value,
        ):
            raise ValueError("仅已生成的项目可标记已审待发")
    elif target == "delivered":
        # none→delivered：质检已过时允许一步到位（仍要求可下载；跳过「已审待发」暂存）
        if current == "none":
            if delivery_block_reason(project):
                raise ValueError("质量检查未通过 · 请先通过机器质检后再标记已发出")
            if project.status not in (
                ProjectStatus.generated.value,
                ProjectStatus.running.value,
            ):
                raise ValueError("仅已生成的项目可标记已发出")
        elif current != "ready":
            raise ValueError("请先标记「已审待发」，再标记「已发出」")
    project.delivery_mark = target
    return target

async def set_delivery_mark(db: AsyncSession, project: Project, mark: str) -> Project:
    """人工标记：none / ready（已审待发）/ delivered（已发出）。"""
    apply_delivery_mark(project, mark)
    await db.commit()
    await db.refresh(project)
    return project

def workspace_or_reason(project: Project) -> tuple[Path | None, str | None]:
    """返回 (工作区路径, 错误文案)；成功时错误为 None。"""
    if not project.workspace_path:
        return None, MSG_WS_MISSING
    ws = Path(project.workspace_path)
    if not ws.exists():
        return None, MSG_WS_GONE
    return ws, None

def delivery_block_reason(project: Project, *, verify_stale: bool = True) -> str | None:
    """None = 可下载 ZIP。唯一文案来源（列表/详情 API 下发，前端勿再抄一份）。

    verify_stale=False 供列表 / /stats 等高频只读投影：过期判定只读后台投影缓存，
    不现场遍历工作区（单项目约 1.4 万文件）；下载/详情等写路径保持现场核验。
    """
    if project.status == ProjectStatus.generating.value:
        return MSG_DOWNLOAD_GENERATING
    from app.services.delivery_review import (
        get_review_state,
        is_zip_stale,
        is_zip_stale_cached,
        open_fix_notes,
    )

    st = get_review_state(project)
    last_verify = st.get("last_verify") if isinstance(st.get("last_verify"), dict) else {}
    if st.get("status") == "active" and last_verify.get("monotonic_ok") is False:
        return MSG_DOWNLOAD_REVIEW_REGRESSION
    if st.get("status") == "active" and open_fix_notes(st):
        return MSG_DOWNLOAD_OPEN_FIX_NOTES
    if getattr(project, "workspace_path", ""):
        stale = (
            is_zip_stale(project)
            if verify_stale
            else is_zip_stale_cached(project, compute=False)
        )
        if stale:
            return MSG_DOWNLOAD_ZIP_STALE
    zip_ok = bool(project.zip_ready and gates_allow_delivery(project.gates))
    zip_exists = bool(project.zip_path and Path(str(project.zip_path)).exists())
    if zip_ok and zip_exists:
        return None
    if zip_ok and not zip_exists:
        return MSG_DOWNLOAD_ZIP_MISSING
    if not zip_exists:
        return MSG_DOWNLOAD_NO_ZIP
    return MSG_DOWNLOAD_GATES

def is_zip_downloadable(project: Project, *, verify_stale: bool = True) -> bool:
    """与 delivery_block_reason 同源：True = 机器质检可下。"""
    return delivery_block_reason(project, verify_stale=verify_stale) is None

def preview_start_block_reason(project: Project) -> str | None:
    """None = 可启动预览。预览不要求门禁通过（便于排查失败包）。"""
    if project.status == ProjectStatus.generating.value:
        return MSG_PREVIEW_GENERATING
    _, reason = workspace_or_reason(project)
    return reason

