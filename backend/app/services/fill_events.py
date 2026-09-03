"""填岛进度事件（进程内 SSE，无 Redis）。答辩 PPT 复用同类 hub。"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator
from typing import Any

_HEARTBEAT_SEC = 15
_TERMINAL = frozenset({"fill_complete", "fill_failed", "ppt_complete", "ppt_failed"})


def _empty_snapshot() -> dict[str, Any]:
    return {
        "phase": "idle",
        "units": {},
        "total": 0,
        "done": 0,
        "failed": 0,
        "running": 0,
    }


def _merge_event(snap: dict[str, Any], event: dict[str, Any]) -> None:
    t = str(event.get("type") or "")
    if t in ("fill_plan", "ppt_plan"):
        units: dict[str, dict[str, Any]] = {}
        for raw in event.get("units") or []:
            if not isinstance(raw, dict):
                continue
            uid = str(raw.get("id") or raw.get("key") or "")
            if not uid:
                continue
            units[uid] = {
                "id": uid,
                "kind": str(raw.get("kind") or raw.get("key") or ""),
                "title": str(raw.get("title") or ""),
                "budget_chars": int(raw.get("budget_chars") or 0),
                "source_refs": list(raw.get("source_refs") or []),
                "status": "pending",
                "error": "",
            }
        snap.clear()
        snap.update(_empty_snapshot())
        snap["units"] = units
        snap["total"] = int(event.get("total") or len(units))
        snap["phase"] = "running"
        return

    if t in ("fill_reset", "ppt_reset"):
        snap.clear()
        snap.update(_empty_snapshot())
        return

    if t == "unit_started":
        uid = str(event.get("unit_id") or event.get("key") or "")
        if not uid:
            return
        u = snap["units"].setdefault(uid, {"id": uid, "status": "pending", "error": ""})
        prev = str(u.get("status") or "pending")
        if prev != "running":
            snap["running"] = int(snap.get("running") or 0) + 1
        u["status"] = "running"
        if event.get("kind"):
            u["kind"] = str(event.get("kind"))
        if event.get("title"):
            u["title"] = str(event.get("title"))
        return

    if t in ("unit_done", "unit_failed", "unit_skipped"):
        uid = str(event.get("unit_id") or event.get("key") or "")
        if not uid:
            return
        u = snap["units"].setdefault(uid, {"id": uid, "error": ""})
        prev = str(u.get("status") or "pending")
        if prev == "running":
            snap["running"] = max(0, int(snap.get("running") or 0) - 1)
        if t == "unit_done":
            u["status"] = "done"
            if prev not in ("done", "failed", "skipped"):
                snap["done"] = int(snap.get("done") or 0) + 1
        elif t == "unit_skipped":
            u["status"] = "skipped"
        else:
            u["status"] = "failed"
            u["error"] = str(event.get("error") or "")
            if prev not in ("done", "failed", "skipped"):
                snap["failed"] = int(snap.get("failed") or 0) + 1
        return

    if t in ("fill_complete", "ppt_complete"):
        snap["phase"] = "done"
        snap["running"] = 0
        return

    if t in ("fill_failed", "ppt_failed"):
        snap["phase"] = "failed"
        snap["running"] = 0
        if event.get("error"):
            snap["error"] = str(event.get("error"))


class FillEventHub:
    """单进程进度：快照 + 订阅队列，供 SSE 首帧与断线恢复。

    channel 默认 fill；答辩 PPT 用 defense_ppt，键为 ``{channel}:{project_id}``。
    """

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._snapshots: dict[str, dict[str, Any]] = {}
        self._queues: dict[str, list[asyncio.Queue[dict[str, Any] | None]]] = {}

    @staticmethod
    def _key(project_id: str, channel: str = "fill") -> str:
        ch = (channel or "fill").strip() or "fill"
        return f"{ch}:{project_id}"

    def snapshot(self, project_id: str, *, channel: str = "fill") -> dict[str, Any]:
        base = _empty_snapshot()
        raw = self._snapshots.get(self._key(project_id, channel)) or {}
        base.update({k: raw[k] for k in base if k in raw})
        units = raw.get("units")
        base["units"] = dict(units) if isinstance(units, dict) else {}
        if raw.get("error"):
            base["error"] = raw["error"]
        return base

    async def reset(self, project_id: str, *, channel: str = "fill") -> None:
        key = self._key(project_id, channel)
        async with self._lock:
            self._snapshots[key] = _empty_snapshot()
        await self._publish_snapshot(project_id, channel=channel)

    async def handle(
        self, project_id: str, event: dict[str, Any], *, channel: str = "fill"
    ) -> None:
        key = self._key(project_id, channel)
        async with self._lock:
            snap = self._snapshots.setdefault(key, _empty_snapshot())
            _merge_event(snap, event)
        await self._publish_snapshot(project_id, channel=channel)

    async def _publish_snapshot(self, project_id: str, *, channel: str = "fill") -> None:
        payload = {"type": "snapshot", **self.snapshot(project_id, channel=channel)}
        for q in list(self._queues.get(self._key(project_id, channel), [])):
            try:
                q.put_nowait(payload)
            except asyncio.QueueFull:
                pass

    async def subscribe(
        self, project_id: str, *, channel: str = "fill"
    ) -> AsyncGenerator[dict[str, Any], None]:
        key = self._key(project_id, channel)
        q: asyncio.Queue[dict[str, Any] | None] = asyncio.Queue(maxsize=64)
        async with self._lock:
            self._queues.setdefault(key, []).append(q)
        try:
            yield {"type": "snapshot", **self.snapshot(project_id, channel=channel)}
            while True:
                try:
                    event = await asyncio.wait_for(q.get(), timeout=_HEARTBEAT_SEC)
                except TimeoutError:
                    yield {"type": "heartbeat"}
                    continue
                if event is None:
                    break
                yield event
                if str(event.get("type") or "") in _TERMINAL:
                    return
                if event.get("type") == "snapshot" and event.get("phase") in ("done", "failed"):
                    return
        finally:
            async with self._lock:
                qs = self._queues.get(key, [])
                if q in qs:
                    qs.remove(q)


fill_event_hub = FillEventHub()
# 可接受：同文件第二实例；首选是 channel=defense_ppt 共用 fill_event_hub
ppt_event_hub = fill_event_hub
