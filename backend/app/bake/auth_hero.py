"""Bake：按领域 + 主题拉取登录氛围图 → frontend/public/auth-hero.jpg。"""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path

from app.bake.domain_skin import auth_hero_query_for
from app.bake import unsplash_fetch as uf
from app.core.config import get_settings

log = logging.getLogger("gf.auth_hero")

# 兼容旧测：仍可 monkeypatch 本模块名；实现落在 unsplash_fetch
_download = uf.download_image
_search_photo_urls = uf.search_photo_urls

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
    "DOM-EVENT": [
        "1551836022-d5d88e9218df",
        "1522202176988-66273c2fd55f",
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
    "DOM-CARRENT": [
        "1492144534705-7e91d30b5d07",
        "1449968766-5ae1de75f3e0",
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
    base = auth_hero_query_for(domain)
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


def _fetch_via_api(query: str, access_key: str, dest: Path) -> bool:
    for img in _search_photo_urls(query, access_key, limit=5):
        if _download(img, dest):
            return True
    return False


def _fetch_fallback_photo(domain: str, theme: str, dest: Path) -> bool:
    pid = _pick_fallback_id(domain, theme)
    return _download(uf.direct_photo_url(pid, width=1600, height=900), dest)


def _fetch_local_atmosphere(domain: str, theme: str, dest: Path) -> bool:
    """外网不可用时：按 themes.css 色板 + 域族构图生成本地氛围图。"""
    from app.bake.local_atmosphere import write_local_atmosphere_cached

    return write_local_atmosphere_cached(
        dest, domain=domain, theme=theme, kind="auth", slot=0
    )


def fetch_auth_hero(workspace: Path, domain: str, theme: str) -> bool:
    """
    写入 workspace/frontend/public/auth-hero.jpg。
    成功 True；失败不抛，bake 继续。
    顺序：本机缓存 → Unsplash API → Unsplash 直链 → 主题色本地生成。
    """
    settings = get_settings()
    public = workspace / "frontend" / "public"
    dest = public / "auth-hero.jpg"
    cache_key = uf.cache_key_hash(domain, theme)
    cache_file = uf.cache_file(
        "auth-heroes",
        f"{domain}-{theme}-{cache_key}.jpg",
        cache_dir=settings.cache_dir,
    )

    if uf.cache_read(cache_file, dest):
        log.info("auth hero cache hit → %s", dest)
        return True

    query = build_query(domain, theme)
    key = (getattr(settings, "unsplash_access_key", None) or "").strip()
    ok = False
    source = ""
    if key:
        ok = _fetch_via_api(query, key, dest)
        if ok:
            source = "unsplash-api"
    if not ok:
        ok = _fetch_fallback_photo(domain, theme, dest)
        if ok:
            source = "unsplash-direct"
    if not ok:
        ok = _fetch_local_atmosphere(domain, theme, dest)
        if ok:
            source = "local-theme"
    if ok and dest.is_file():
        # 仅缓存外网图；本地生成另有 local-atmosphere 缓存
        if source.startswith("unsplash"):
            uf.cache_write(cache_file, dest)
        log.info("auth hero saved (%s / %s): %s", source or "?", query, dest)
        return True
    log.warning("auth hero skipped for %s / %s", domain, theme)
    return False


def auth_hero_public_path(workspace: Path) -> str:
    """若文件存在返回前端路径，否则空串。"""
    if (workspace / "frontend" / "public" / "auth-hero.jpg").is_file():
        return "/auth-hero.jpg"
    return ""
