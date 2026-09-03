"""半自动截图：采图失败标 missing；上传替换。与 Job 流水线共用 in-memory 接口。"""

from __future__ import annotations

import base64
import re
import uuid
from pathlib import Path
from typing import Any

from app.models import Project

from .deck_io import load_deck, save_deck
from .themes import ensure_ppt_dirs, ppt_root


def _shots_dir(project: Project) -> Path:
    root = ensure_ppt_dirs(project)
    d = root / "figures" / "shots"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _decode_data_url(data_url: str) -> tuple[bytes, str]:
    m = re.match(r"^data:([^;,]+)?(;base64)?,(.*)$", data_url or "", re.DOTALL)
    if not m:
        raise ValueError("无效的图片 data URL")
    mime = (m.group(1) or "image/png").lower()
    payload = m.group(3) or ""
    raw = base64.b64decode(payload)
    ext = ".png"
    if "jpeg" in mime or "jpg" in mime:
        ext = ".jpg"
    elif "webp" in mime:
        ext = ".webp"
    return raw, ext


def _set_demo_figure(deck: dict[str, Any], page_id: str | None, figure: dict[str, Any]) -> str:
    pages = [p for p in (deck.get("pages") or []) if isinstance(p, dict)]
    page = None
    if page_id:
        page = next((p for p in pages if p.get("id") == page_id), None)
    if not page:
        page = next((p for p in pages if p.get("role") == "demo"), None)
    if not page:
        raise FileNotFoundError("演示页不存在")
    page["figure"] = figure
    return str(page.get("id") or "demo")


async def try_capture_bytes(project: Project) -> tuple[bytes | None, str]:
    """探测学生预览；返回 (png_bytes|None, hint)。无 headless 时仅当响应是图片才算采到。"""
    hint = "自动采图未成功 · 请上传主流程截图"
    if not (project.frontend_running and project.frontend_port):
        return None, "预览未运行 · 请先启动前端或手动上传截图"
    try:
        import httpx

        port = int(project.frontend_port)
        candidates = [
            f"http://127.0.0.1:{port}/login",
            f"http://127.0.0.1:{port}/",
        ]
        async with httpx.AsyncClient(timeout=5.0, follow_redirects=True) as client:
            for url in candidates:
                try:
                    resp = await client.get(url)
                except Exception:  # noqa: BLE001
                    continue
                ctype = (resp.headers.get("content-type") or "").lower()
                if ctype.startswith("image/") and resp.content:
                    return resp.content, "已采"
                if resp.status_code < 500:
                    hint = f"预览已可达（{url}）· 请登录演示账号后截主流程并上传"
                    break
    except Exception:  # noqa: BLE001
        pass
    return None, hint


async def capture_into_deck(
    project: Project,
    deck: dict[str, Any],
    *,
    page_id: str | None = None,
) -> dict[str, Any]:
    """半自动采图写入传入的 deck（不强制落盘）。Job 流水线与 API 共用。"""
    raw, hint = await try_capture_bytes(project)
    if raw:
        shots = _shots_dir(project)
        name = f"demo-capture-{uuid.uuid4().hex[:8]}.png"
        path = shots / name
        path.write_bytes(raw)
        figure = {
            "kind": "screenshot",
            "label": "主流程界面截图（已采）",
            "available": True,
            "missing": False,
            "path": f"figures/shots/{name}",
        }
        shot_ok = True
    else:
        figure = {
            "kind": "screenshot",
            "label": "主流程界面截图",
            "available": False,
            "missing": True,
            "hint": hint,
        }
        shot_ok = False
    pid = _set_demo_figure(deck, page_id, figure)
    return {"ok": shot_ok, "page_id": pid, "figure": figure}


async def capture_current(project: Project, *, page_id: str | None = None) -> dict[str, Any]:
    """API：读盘 → 采图 → 写回 deck.json。"""
    deck = load_deck(project)
    if not deck:
        raise FileNotFoundError("尚无答辩 PPT")
    # 已有可用截图则不覆盖（半自动不冲掉人工上传）
    demo = next(
        (p for p in (deck.get("pages") or []) if isinstance(p, dict) and p.get("role") == "demo"),
        None,
    )
    fig = (demo or {}).get("figure") if isinstance(demo, dict) else None
    if isinstance(fig, dict) and fig.get("available") and not fig.get("missing"):
        return {"ok": True, "page_id": demo.get("id"), "figure": fig, "skipped": True}

    result = await capture_into_deck(project, deck, page_id=page_id)
    save_deck(project, deck)
    return result


def upload_screenshot(
    project: Project, *, page_id: str | None, data_url: str
) -> dict[str, Any]:
    deck = load_deck(project)
    if not deck:
        raise FileNotFoundError("尚无答辩 PPT")
    raw, ext = _decode_data_url(data_url)
    shots = _shots_dir(project)
    name = f"demo-upload-{uuid.uuid4().hex[:8]}{ext}"
    path = shots / name
    path.write_bytes(raw)
    figure = {
        "kind": "screenshot",
        "label": "主流程界面截图（已上传）",
        "available": True,
        "missing": False,
        "path": f"figures/shots/{name}",
        "url": data_url if len(data_url) < 2_000_000 else None,
    }
    pid = _set_demo_figure(deck, page_id, figure)
    save_deck(project, deck)
    return {"ok": True, "page_id": pid, "figure": figure}


def resolve_shot_file(project: Project, figure: dict[str, Any] | None) -> Path | None:
    if not isinstance(figure, dict):
        return None
    root = ppt_root(project)
    if not root:
        return None
    rel = figure.get("path")
    if rel:
        p = root / str(rel)
        if p.is_file():
            return p
    return None
