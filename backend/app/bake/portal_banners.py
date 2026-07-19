"""Bake：门户轮播图（与登录 auth-hero 分套资产）。"""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path
from typing import Any

from app.bake.auth_hero import _FALLBACK_PHOTOS, _download, _fetch_via_api, build_query
from app.core.config import get_settings

log = logging.getLogger("gf.portal_banners")

# 门户专用兜底图（与 auth_hero 列表错开）
_PORTAL_FALLBACK: dict[str, list[str]] = {
    "DOM-LIBRARY": [
        "1524995997941-a1c2fe3ad0e4",
        "1497633762265-9d179a990aa6",
        "1519682337058-a94d519337bc",
        "1481627834876-b7833e8f5570",
    ],
    "DOM-EQUIP": [
        "1581092918056-0c4c3acd3789",
        "1581092160562-40aa08e78837",
        "1576086213369-97a306d36557",
        "1581091226825-a6a2a5aee158",
    ],
    "DOM-ACTIVITY": [
        "1523580494863-6f3031224c94",
        "1505373877841-8d25f7d46678",
        "1540575467063-178a50c2df87",
    ],
    "DOM-COURSE": [
        "1523240795612-9a054b0db644",
        "1509062522246-3755977927d7",
        "1524178232363-1fb2b075b655",
    ],
    "DOM-LOST": [
        "1497366811353-6870744d04b2",
        "1497366754035-f200968a6e72",
        "1529156069898-49953e39b1ac",
    ],
    "DOM-SHOP": [
        "1441986300917-64674bd600d8",
        "1472851294608-062f824d29cc",
        "1556742049-0cfed4f6a45d",
    ],
    "DOM-FOOD": [
        "1414235077428-338989a2e8c0",
        "1555939594-58d7cb561ad1",
        "1504674900247-0877df9cc836",
    ],
    "DOM-MEDIA": [
        "1489597841871-5aae429cfe5e",
        "1478720568477-1520c75063ef",
        "1536440136628-849c17754e3d",
    ],
    "DOM-MUSIC": [
        "1511379938546-c1fef3a1a8f0",
        "1514320291860-5e1ff1ff9c9a",
        "1493225457124-a3eb161ffa5f",
    ],
    "DOM-FORUM": [
        "1522071820081-009f0129c71c",
        "1552664730-d307ca884978",
        "1517245386807-bb43f82c33c4",
    ],
    "DOM-BLOG": [
        "1432821596592-e2c18b78144f",
        "1456327102063-fb1691c3f9a1",
        "1499750310102-2b4b9a5b1d8a",
    ],
}

_DEFAULT_CAPTIONS = [
    {"title": "欢迎使用", "lead": "检索业务对象并提交申请。"},
    {"title": "使用须知", "lead": "请按流程申请，按时完结单据。"},
    {"title": "服务时间", "lead": "工作日开放办理，详见公告。"},
]


def domain_wants_portal_banners(domain: str) -> bool:
    from app.bake.catalog import DOMAINS

    dom = DOMAINS.get(domain) or {}
    if dom.get("portal_banners"):
        return True
    runtime = dom.get("runtime") or {}
    return bool(runtime.get("portal_banners"))


def _caption_seeds(schema: dict[str, Any] | None) -> list[dict[str, str]]:
    schema = schema or {}
    banners = schema.get("portalBanners")
    if isinstance(banners, list) and banners:
        out = []
        for b in banners:
            if not isinstance(b, dict):
                continue
            title = str(b.get("title") or "").strip()
            lead = str(b.get("lead") or "").strip()
            if title or lead:
                out.append({"title": title or "通知", "lead": lead})
        if out:
            return out
    labels = schema.get("labels") or {}
    seeds = schema.get("seeds") or {}
    return [
        {
            "title": str(
                labels.get("portalBannerTitle")
                or seeds.get("noticeTitle")
                or _DEFAULT_CAPTIONS[0]["title"]
            ),
            "lead": str(
                labels.get("portalBannerLead")
                or seeds.get("noticeBody")
                or _DEFAULT_CAPTIONS[0]["lead"]
            ),
        },
        dict(_DEFAULT_CAPTIONS[1]),
        dict(_DEFAULT_CAPTIONS[2]),
    ]


def _pick_portal_ids(domain: str, theme: str, count: int = 3) -> list[str]:
    photos = list(_PORTAL_FALLBACK.get(domain) or [])
    auth_list = _FALLBACK_PHOTOS.get(domain) or _FALLBACK_PHOTOS["DOM-GENERIC"]
    for pid in auth_list:
        if pid not in photos:
            photos.append(pid)
    if not photos:
        photos = list(_FALLBACK_PHOTOS["DOM-GENERIC"])
    h = int(hashlib.md5(f"portal|{domain}|{theme}".encode()).hexdigest()[:8], 16)
    start = h % len(photos)
    ids = [photos[(start + i) % len(photos)] for i in range(count)]
    auth_h = int(hashlib.md5(f"{domain}|{theme}".encode()).hexdigest()[:8], 16)
    auth_first = auth_list[auth_h % len(auth_list)] if auth_list else ""
    if ids and ids[0] == auth_first and len(photos) > 1:
        ids[0] = photos[(start + count) % len(photos)]
    return ids


def _download_portal_photo(pid: str, dest: Path, *, timeout: float = 4.0) -> bool:
    url = (
        f"https://images.unsplash.com/photo-{pid}"
        f"?auto=format&fit=crop&w=1800&h=720&q=80"
    )
    return _download(url, dest, timeout=timeout)


def fetch_portal_banners(
    workspace: Path,
    domain: str,
    theme: str,
    schema: dict[str, Any] | None = None,
    count: int = 3,
) -> list[dict[str, str]]:
    """写入 public/portal-banners/{n}.jpg；失败不抛。网络慢时尽快跳过。"""
    if not domain_wants_portal_banners(domain):
        return []

    settings = get_settings()
    public = workspace / "frontend" / "public" / "portal-banners"
    public.mkdir(parents=True, exist_ok=True)
    cache_dir = settings.cache_dir / "portal-banners"
    cache_dir.mkdir(parents=True, exist_ok=True)

    captions = _caption_seeds(schema)
    while len(captions) < count:
        captions.append(dict(_DEFAULT_CAPTIONS[len(captions) % len(_DEFAULT_CAPTIONS)]))

    ids = _pick_portal_ids(domain, theme, count)
    query = build_query(domain, theme) + " wide interior"
    key = (getattr(settings, "unsplash_access_key", None) or "").strip()

    slides: list[dict[str, str]] = []
    net_fail = 0
    for i, pid in enumerate(ids):
        dest = public / f"{i + 1}.jpg"
        cache_key = hashlib.md5(f"portal|{domain}|{theme}|{i}|{pid}".encode()).hexdigest()[:16]
        cache_file = cache_dir / f"{domain}-{i}-{cache_key}.jpg".replace("/", "_")
        ok = False
        if cache_file.is_file() and cache_file.stat().st_size > 2000:
            dest.write_bytes(cache_file.read_bytes())
            ok = True
        elif net_fail >= 2:
            # 连续失败则不再拖 bake
            log.warning("portal banner network aborted after failures (%s)", domain)
            break
        else:
            if key and i == 0:
                tmp = public / f"_api_{i + 1}.jpg"
                if _fetch_via_api(query, key, tmp):
                    dest.write_bytes(tmp.read_bytes())
                    tmp.unlink(missing_ok=True)
                    ok = True
            if not ok:
                ok = _download_portal_photo(pid, dest, timeout=4.0)
            if ok and dest.is_file():
                try:
                    cache_file.write_bytes(dest.read_bytes())
                except OSError:
                    pass
            else:
                net_fail += 1
        if ok and dest.is_file():
            cap = captions[i]
            slides.append({
                "src": f"/portal-banners/{i + 1}.jpg",
                "title": cap["title"],
                "lead": cap["lead"],
            })
        else:
            log.warning("portal banner %s skipped for %s", i + 1, domain)

    log.info("portal banners: %s × %s", domain, len(slides))
    return slides


def portal_banners_from_workspace(
    workspace: Path, schema: dict[str, Any] | None = None
) -> list[dict[str, str]]:
    public = workspace / "frontend" / "public" / "portal-banners"
    if not public.is_dir():
        return []
    captions = _caption_seeds(schema)
    slides: list[dict[str, str]] = []
    for i in range(1, 6):
        path = public / f"{i}.jpg"
        if not path.is_file() or path.stat().st_size < 2000:
            continue
        cap = captions[len(slides) % len(captions)]
        slides.append({
            "src": f"/portal-banners/{i}.jpg",
            "title": cap["title"],
            "lead": cap["lead"],
        })
    return slides
