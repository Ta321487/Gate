"""匹配确认时灌本机氛围图缓存：外网只在此刻短窗碰 Unsplash，bake 优先读盘。

不阻断确认（大陆无代理时常连不上）；结果写入 project.spec['atmosphere'] 供运营可见。
"""

from __future__ import annotations

import logging
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.bake import unsplash_fetch as uf
from app.core.config import get_settings

log = logging.getLogger("gf.atmosphere_prefetch")


def auth_cache_path(domain: str, theme: str, *, cache_dir: Path | None = None) -> Path:
    settings = get_settings()
    root = cache_dir if cache_dir is not None else settings.cache_dir
    cache_key = uf.cache_key_hash(domain, theme)
    return uf.cache_file(
        "auth-heroes",
        f"{domain}-{theme}-{cache_key}.jpg",
        cache_dir=root,
    )


def prefetch_match_atmosphere(domain: str, theme: str) -> dict[str, Any]:
    """
    向工厂 cache 灌登录氛围（及门户轮播若该域需要）。
    返回可写入 spec 的摘要；失败不抛。
    """
    domain = (domain or "DOM-GENERIC").strip() or "DOM-GENERIC"
    theme = (theme or "gen-ink").strip() or "gen-ink"
    settings = get_settings()
    auth_path = auth_cache_path(domain, theme, cache_dir=settings.cache_dir)
    had_auth = (
        auth_path.is_file() and auth_path.stat().st_size >= uf.MIN_IMAGE_BYTES
    )

    auth_ok = False
    portal_n = 0
    try:
        from app.bake.auth_hero import fetch_auth_hero
        from app.bake.portal_banners import (
            domain_wants_portal_banners,
            fetch_portal_banners,
        )

        with tempfile.TemporaryDirectory(prefix="gf-atm-") as td:
            ws = Path(td)
            auth_ok = bool(fetch_auth_hero(ws, domain, theme))
            if domain_wants_portal_banners(domain):
                slides = fetch_portal_banners(ws, domain, theme, None) or []
                portal_n = len(slides)
    except Exception as e:  # noqa: BLE001
        log.warning("atmosphere prefetch failed %s/%s: %s", domain, theme, e)

    auth_real = (
        auth_path.is_file() and auth_path.stat().st_size >= uf.MIN_IMAGE_BYTES
    )
    return {
        "domain": domain,
        "theme": theme,
        "auth_ok": auth_ok,
        "auth_real": auth_real,
        "auth_was_cached": had_auth,
        "portal_slides": portal_n,
        "proxy": bool(uf.http_proxy()),
        "at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


def apply_atmosphere_to_spec(spec: dict | None, result: dict[str, Any]) -> dict:
    out = dict(spec or {})
    out["atmosphere"] = result
    return out
