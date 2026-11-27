"""资产台进程缓存：各台共用一把锁+快照，禁止每台复制 _lock/_rows_cache。

真源仍是各 factory_* 库表；本模块只管「库→进程」快照失效。
"""

from __future__ import annotations

import threading
from typing import Any, Callable, Iterable


def norm_text(s: str | None) -> str:
    return (s or "").strip()


class AssetRowsCache:
    """一行台一份实例；invalidate 后下次 load_all_rows 再灌。"""

    __slots__ = ("_lock", "_rows")

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._rows: list[dict[str, Any]] | None = None

    def invalidate(self) -> None:
        with self._lock:
            self._rows = None

    def get(self) -> list[dict[str, Any]] | None:
        with self._lock:
            if self._rows is None:
                return None
            return list(self._rows)

    def set(self, rows: list[dict[str, Any]]) -> None:
        with self._lock:
            self._rows = list(rows)


def filter_rows(
    rows: Iterable[dict[str, Any]],
    *,
    q: str | None = None,
    equals: dict[str, str] | None = None,
    q_fields: tuple[str, ...] = (),
) -> list[dict[str, Any]]:
    """列表筛：equals 精确；q 在 q_fields 上小写包含。"""
    out = list(rows)
    if equals:
        for key, want in equals.items():
            if want is None or want == "":
                continue
            out = [r for r in out if str(r.get(key) or "") == want]
    qq = (q or "").strip().lower()
    if qq and q_fields:
        out = [
            r
            for r in out
            if any(qq in str(r.get(f) or "").lower() for f in q_fields)
        ]
    return out


def domain_options_star_first(
    domains: dict[str, Any],
    *,
    star_name: str = "跨域壳默认",
) -> list[dict[str, str]]:
    """资产台 meta 域下拉：* + catalog。"""
    return [
        {"id": "*", "name": star_name},
        *[
            {"id": k, "name": (domains.get(k) or {}).get("label") or k}
            for k in domains
        ],
    ]
