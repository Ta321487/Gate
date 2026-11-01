"""Unsplash 拉图共用：检索 / 下载重试 / 本机缓存读写。

auth_hero 与 portal_banners 只编排用途与落盘路径，禁止各自再写一套下载。
出包侧优先读本机缓存；外网只在缓存未命中时短窗重试。
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from app.core.config import get_settings

log = logging.getLogger("gf.unsplash_fetch")

MIN_IMAGE_BYTES = 2000
USER_AGENT = "thesis-harbor/1 unsplash"

# 运营台固定提示（单一真源；API / 页面勿另写一套口径）
OPERATOR_HINTS: tuple[str, ...] = (
    "出包读本机缓存；Unsplash 只在缓存未命中时拉一次并写入缓存。",
    "确认匹配时会短窗灌库（失败不挡确认）；通了一次后同域主题再出包少抖。",
    "大陆无代理时 api.unsplash.com / images.unsplash.com 可能超时——先点「测试连接」，通了再生成。",
    "可选环境变量 UNSPLASH_HTTP_PROXY（http://host:port），只给工厂拉图，不进学生 ZIP。",
    "未配置 Key 或外网失败时，登录图/轮播会按 themes.css 色板本地生成（非实拍）。",
)


def operator_hint_text() -> str:
    return " ".join(OPERATOR_HINTS)


def access_key() -> str:
    return (getattr(get_settings(), "unsplash_access_key", None) or "").strip()


def http_proxy() -> str:
    return (getattr(get_settings(), "unsplash_http_proxy", None) or "").strip()


def _opener() -> urllib.request.OpenerDirector:
    proxy = http_proxy()
    if proxy:
        return urllib.request.build_opener(
            urllib.request.ProxyHandler({"http": proxy, "https": proxy})
        )
    return urllib.request.build_opener()


def is_image_bytes(data: bytes, content_type: str = "") -> bool:
    if len(data) < MIN_IMAGE_BYTES:
        return False
    ctype = (content_type or "").lower()
    is_jpeg = data[:3] == b"\xff\xd8\xff"
    is_png = data[:8] == b"\x89PNG\r\n\x1a\n"
    if "image" in ctype:
        return True
    return is_jpeg or is_png


def download_image(
    url: str,
    dest: Path,
    *,
    timeout: float = 8.0,
    retries: int = 3,
) -> bool:
    """下载到 dest；失败重试（短退避）。成功 True。"""
    retries = max(1, min(int(retries or 1), 5))
    opener = _opener()
    last_err: Exception | None = None
    for attempt in range(retries):
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with opener.open(req, timeout=timeout) as resp:
                data = resp.read()
                ctype = (resp.headers.get("Content-Type") or "").lower()
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            last_err = e
            log.warning(
                "unsplash download fail attempt %s/%s: %s (%s)",
                attempt + 1,
                retries,
                url[:80],
                e,
            )
            if attempt + 1 < retries:
                time.sleep(0.4 * (attempt + 1))
            continue
        if not is_image_bytes(data, ctype):
            last_err = ValueError("not an image payload")
            if attempt + 1 < retries:
                time.sleep(0.4 * (attempt + 1))
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        return True
    if last_err is not None:
        log.warning("unsplash download gave up: %s (%s)", url[:80], last_err)
    return False


def search_photo_urls(
    query: str,
    access_key: str,
    *,
    limit: int = 5,
    page: int = 1,
    orientation: str = "landscape",
    timeout: float = 8.0,
    retries: int = 2,
) -> list[str]:
    """Unsplash Search API：去重后的图片 URL（不下载）。"""
    key = (access_key or "").strip()
    if not key:
        return []
    limit = max(1, min(int(limit or 1), 30))
    qs = urllib.parse.urlencode(
        {
            "query": query,
            "per_page": limit,
            "page": max(1, int(page or 1)),
            "orientation": orientation,
        }
    )
    api = f"https://api.unsplash.com/search/photos?{qs}"
    opener = _opener()
    retries = max(1, min(int(retries or 1), 4))
    payload: dict | None = None
    for attempt in range(retries):
        req = urllib.request.Request(
            api,
            headers={
                "Authorization": f"Client-ID {key}",
                "Accept-Version": "v1",
                "User-Agent": USER_AGENT,
            },
        )
        try:
            with opener.open(req, timeout=timeout) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
            break
        except Exception as e:  # noqa: BLE001
            log.warning(
                "unsplash api search fail attempt %s/%s: %s",
                attempt + 1,
                retries,
                e,
            )
            if attempt + 1 < retries:
                time.sleep(0.4 * (attempt + 1))
    if not isinstance(payload, dict):
        return []
    out: list[str] = []
    seen: set[str] = set()
    for item in payload.get("results") or []:
        urls = item.get("urls") or {}
        img = urls.get("regular") or urls.get("full") or urls.get("small")
        if not img or img in seen:
            continue
        seen.add(img)
        out.append(img)
        if len(out) >= limit:
            break
    return out


def direct_photo_url(
    photo_id: str,
    *,
    width: int = 1600,
    height: int = 900,
    quality: int = 80,
) -> str:
    pid = (photo_id or "").strip().removeprefix("photo-")
    return (
        f"https://images.unsplash.com/photo-{pid}"
        f"?auto=format&fit=crop&w={int(width)}&h={int(height)}&q={int(quality)}"
    )


def cache_file(kind: str, name: str, *, cache_dir: Path | None = None) -> Path:
    """kind: auth-heroes | portal-banners；name 已是安全文件名。"""
    root = cache_dir if cache_dir is not None else get_settings().cache_dir
    folder = Path(root) / kind
    folder.mkdir(parents=True, exist_ok=True)
    safe = name.replace("/", "_").replace("\\", "_")
    return folder / safe


def cache_key_hash(*parts: str, n: int = 16) -> str:
    raw = "|".join(str(p) for p in parts)
    return hashlib.md5(raw.encode()).hexdigest()[:n]


def cache_read(path: Path, dest: Path) -> bool:
    if not path.is_file() or path.stat().st_size < MIN_IMAGE_BYTES:
        return False
    try:
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(path.read_bytes())
        return True
    except OSError as e:
        log.warning("unsplash cache read failed: %s", e)
        return False


def cache_write(path: Path, src: Path) -> None:
    if not src.is_file() or src.stat().st_size < MIN_IMAGE_BYTES:
        return
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(src.read_bytes())
    except OSError as e:
        log.warning("unsplash cache write failed: %s", e)


def vault_counts() -> dict[str, int]:
    """本机 Unsplash 实图缓存张数（供运营台提示）。"""
    settings = get_settings()
    out = {"auth_heroes": 0, "portal_banners": 0}

    def _count(subdir: str) -> int:
        d = settings.cache_dir / subdir
        if not d.is_dir():
            return 0
        n = 0
        for p in d.glob("*.jpg"):
            try:
                if p.is_file() and p.stat().st_size >= MIN_IMAGE_BYTES:
                    n += 1
            except OSError:
                continue
        return n

    out["auth_heroes"] = _count("auth-heroes")
    out["portal_banners"] = _count("portal-banners")
    return out


def status_payload() -> dict:
    key = access_key()
    proxy = http_proxy()
    counts = vault_counts()
    return {
        "key_configured": bool(key),
        "proxy_configured": bool(proxy),
        "vault_auth_heroes": counts["auth_heroes"],
        "vault_portal_banners": counts["portal_banners"],
        "hints": list(OPERATOR_HINTS),
        "hint": operator_hint_text(),
    }
