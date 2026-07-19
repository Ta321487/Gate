"""Bake：按领域 + 主题拉取登录氛围图 → frontend/public/auth-hero.jpg。"""

from __future__ import annotations

import hashlib
import json
import logging
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from app.core.config import get_settings

log = logging.getLogger("gf.auth_hero")

# 领域英文检索锚点
_DOMAIN_QUERY: dict[str, str] = {
    "DOM-LIBRARY": "university library books reading",
    "DOM-DORM": "university dormitory campus building",
    "DOM-PROPERTY": "residential apartment community property",
    "DOM-IT": "server room network operations campus it",
    "DOM-EQUIP": "laboratory equipment workshop",
    "DOM-ASSET": "warehouse inventory shelves",
    "DOM-CRM": "business meeting handshake office crm",
    "DOM-ACTIVITY": "campus event students gathering",
    "DOM-LOST": "campus corridor lost and found desk",
    "DOM-COURSE": "university classroom lecture hall",
    "DOM-SHOP": "modern retail store aisle",
    "DOM-FOOD": "campus cafeteria food counter",
    "DOM-HOSPITAL": "hospital clinic corridor",
    "DOM-PARKING": "parking garage cars",
    "DOM-MEETING": "conference meeting room",
    "DOM-SALON": "salon service studio interior",
    "DOM-HOTEL": "hotel lobby interior",
    "DOM-MEDIA": "cinema movie theater screen audience",
    "DOM-MUSIC": "headphones music vinyl record studio",
    "DOM-FORUM": "online forum discussion community bulletin board",
    "DOM-BLOG": "writing desk laptop coffee blog journal",
    "DOM-GENERIC": "modern office workspace",
}

# 主题气质（取 id 后缀 / 关键词）
_THEME_MOOD: dict[str, str] = {
    "night": "night dark moody",
    "ink": "blue ink calm",
    "grove": "green nature soft",
    "amber": "warm amber light",
    "orange": "warm orange daylight",
    "sky": "bright sky blue",
    "teal": "teal cyan",
    "cyan": "cyan tech",
    "violet": "violet purple",
    "coral": "coral warm",
    "sand": "warm sand beige",
    "leaf": "green leaf fresh",
    "mint": "mint green",
    "steel": "steel blue industrial",
    "olive": "olive green",
    "clay": "warm clay terracotta",
    "slate": "slate gray",
    "plum": "plum magenta",
    "gold": "gold warm luxury",
    "navy": "navy blue",
    "chili": "red warm",
    "bamboo": "bamboo green",
    "rose": "soft rose",
    "cream": "cream warm light",
    "asphalt": "gray asphalt urban",
    "signal": "green signal",
    "sesame": "warm brown",
    "berry": "berry purple",
    "lime": "lime green",
    "ocean": "ocean blue",
    "vinyl": "vinyl record warm",
    "cinema": "cinema theater",
    "forum": "community discussion",
    "blog": "writing reading",
}

# 无 API Key 时的兜底：Unsplash 公开 photo id（可商用，按领域轮换）
_FALLBACK_PHOTOS: dict[str, list[str]] = {
    "DOM-LIBRARY": [
        "1507842217343-583bb7270b66",
        "1521587760476-6c12a4b040da",
        "1481627834876-b7833e8f5570",
    ],
    "DOM-DORM": [
        "1562774053-701939374585",
        "1541339907198-e08756dedf3f",
        "1498243691581-b145c3f54a5a",
    ],
    "DOM-PROPERTY": [
        "1545324418-cc1a3fa10c00",
        "1460317443168-6bc7e1a8e3b0",
        "1486406146926-c627a92ad1ab",
    ],
    "DOM-IT": [
        "1558494949-ef010cbdcc31",
        "1518770660439-4636190af475",
        "1451188502541-13943edb6acb",
    ],
    "DOM-EQUIP": [
        "1581091226825-a6a2a5aee158",
        "1532094349884-543bc11b234d",
    ],
    "DOM-ASSET": [
        "1553413077-190dd305871c",
        "1586528116311-ad8dd3c8310d",
    ],
    "DOM-CRM": [
        "1556761179-b4dda1f7e3e8",
        "1521791138484-c2a0e5d94c05",
    ],
    "DOM-ACTIVITY": [
        "1529156069898-49953e39b1ac",
        "1540575467063-178a50c2df87",
    ],
    "DOM-LOST": [
        "1497366811353-6870744d04b2",
        "1497366754035-f200968a6e72",
    ],
    "DOM-COURSE": [
        "1509062522246-3755977927d7",
        "1524178232363-1fb2b075b655",
    ],
    "DOM-SHOP": [
        "1441986300917-64674bd600d8",
        "1472851294608-062f824d29cc",
    ],
    "DOM-FOOD": [
        "1414235077428-338989a2e8c0",
        "1555939594-58d7cb561ad1",
    ],
    "DOM-HOSPITAL": [
        "1519494026892-80bbd2d6fd0d",
        "1579684385127-1ef15d508118",
    ],
    "DOM-PARKING": [
        "1506521780686-c9a7f9e1c3f7",
        "1590674899484-d5640e854abe",
    ],
    "DOM-MEETING": [
        "1497366216548-37526070297c",
        "1431540015161-0bf868a2d407",
    ],
    "DOM-SALON": [
        "1560066984-138dadb4c035",
        "1522337660859-02fbefca4702",
    ],
    "DOM-HOTEL": [
        "1566073771259-6a8506099945",
        "1551882547-ff40c63fe5fa",
    ],
    "DOM-MEDIA": [
        "1489590313635-f39d5193a4ea",
        "1517604931442-48118040a824",
        "1478720568477-1520c12bfcad",
    ],
    "DOM-MUSIC": [
        "1511379938547-c1f69419868d",
        "1514525253161-7a46d19cd819",
        "1470225620780-dbe8f1019dba",
    ],
    "DOM-FORUM": [
        "1529156069898-49953e39b1ac",
        "1516321318423-f06f85e504b3",
        "1517245386807-bb43f82c33c4",
    ],
    "DOM-BLOG": [
        "1486312338219-ce68d2c6f44d",
        "1455390582262-044cdead135a",
        "1499750310102-2b4b9a5b1d8a",
    ],
    "DOM-GENERIC": [
        "1497366216548-37526070297c",
        "1497215728101-856f4ea42174",
        "1486312338219-ce68d2c6f44d",
    ],
}


def build_query(domain: str, theme: str) -> str:
    base = _DOMAIN_QUERY.get(domain) or _DOMAIN_QUERY["DOM-GENERIC"]
    mood = ""
    tid = (theme or "").lower()
    for key, words in _THEME_MOOD.items():
        if key in tid:
            mood = words
            break
    if not mood and "night" in tid:
        mood = _THEME_MOOD["night"]
    return f"{base} {mood}".strip()


def _pick_fallback_id(domain: str, theme: str) -> str:
    photos = _FALLBACK_PHOTOS.get(domain) or _FALLBACK_PHOTOS["DOM-GENERIC"]
    h = int(hashlib.md5(f"{domain}|{theme}".encode()).hexdigest()[:8], 16)
    return photos[h % len(photos)]


def _download(url: str, dest: Path, timeout: float = 8.0) -> bool:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "thesis-harbor/1 auth-hero"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = resp.read()
            ctype = (resp.headers.get("Content-Type") or "").lower()
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        log.warning("auth hero download failed: %s (%s)", url[:80], e)
        return False
    if len(data) < 2000:
        return False
    is_jpeg = data[:3] == b"\xff\xd8\xff"
    is_png = data[:8] == b"\x89PNG\r\n\x1a\n"
    if "image" not in ctype and not (is_jpeg or is_png):
        return False
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)
    return True


def _fetch_via_api(query: str, access_key: str, dest: Path) -> bool:
    qs = urllib.parse.urlencode(
        {"query": query, "per_page": 5, "orientation": "landscape"}
    )
    api = f"https://api.unsplash.com/search/photos?{qs}"
    req = urllib.request.Request(
        api,
        headers={
            "Authorization": f"Client-ID {access_key}",
            "User-Agent": "thesis-harbor/1 auth-hero",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except Exception as e:  # noqa: BLE001
        log.warning("unsplash api search failed: %s", e)
        return False
    results = payload.get("results") or []
    for item in results:
        urls = item.get("urls") or {}
        img = urls.get("regular") or urls.get("full") or urls.get("small")
        if img and _download(img, dest):
            return True
    return False


def _fetch_fallback_photo(domain: str, theme: str, dest: Path) -> bool:
    pid = _pick_fallback_id(domain, theme)
    url = (
        f"https://images.unsplash.com/photo-{pid}"
        f"?auto=format&fit=crop&w=1600&h=900&q=80"
    )
    return _download(url, dest)


def fetch_auth_hero(workspace: Path, domain: str, theme: str) -> bool:
    """
    写入 workspace/frontend/public/auth-hero.jpg。
    成功 True；失败不抛，bake 继续。
    """
    settings = get_settings()
    public = workspace / "frontend" / "public"
    dest = public / "auth-hero.jpg"
    cache_dir = settings.cache_dir / "auth-heroes"
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_key = hashlib.md5(f"{domain}|{theme}".encode()).hexdigest()[:16]
    cache_file = cache_dir / f"{domain}-{theme}-{cache_key}.jpg".replace("/", "_")

    if cache_file.is_file() and cache_file.stat().st_size > 2000:
        public.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(cache_file.read_bytes())
        log.info("auth hero cache hit → %s", dest)
        return True

    query = build_query(domain, theme)
    key = (getattr(settings, "unsplash_access_key", None) or "").strip()
    ok = False
    if key:
        ok = _fetch_via_api(query, key, dest)
    if not ok:
        ok = _fetch_fallback_photo(domain, theme, dest)
    if ok and dest.is_file():
        try:
            cache_file.write_bytes(dest.read_bytes())
        except OSError:
            pass
        log.info("auth hero saved (%s): %s", query, dest)
        return True
    log.warning("auth hero skipped for %s / %s", domain, theme)
    return False


def auth_hero_public_path(workspace: Path) -> str:
    """若文件存在返回前端路径，否则空串。"""
    if (workspace / "frontend" / "public" / "auth-hero.jpg").is_file():
        return "/auth-hero.jpg"
    return ""
