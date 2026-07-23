"""Bake：门户轮播图（与登录 auth-hero 分套资产）。"""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path
from typing import Any

from app.bake.auth_hero import (
    _FALLBACK_PHOTOS,
    _download,
    _search_photo_urls,
    build_query,
)
from app.core.config import get_settings

log = logging.getLogger("gf.portal_banners")

# 默认抽几帧：过少轮播显得空；过多拖 bake / 占磁盘
PORTAL_BANNER_COUNT = 5

# 门户专用兜底图（与 auth_hero 列表错开；每域尽量多图，不足时再拼 GENERIC）
_PORTAL_FALLBACK: dict[str, list[str]] = {
    "DOM-LIBRARY": [
        "1524995997941-a1c2fe3ad0e4",
        "1497633762265-9d179a990aa6",
        "1519682337058-a94d519337bc",
        "1481627834876-b7833e8f5570",
        "1507842217343-583bb7270b66",
        "1521587760476-6c12a4b040da",
    ],
    "DOM-EQUIP": [
        "1581092918056-0c4c3acd3789",
        "1581092160562-40aa08e78837",
        "1576086213369-97a306d36557",
        "1581091226825-a6a2a5aee158",
        "1532094349884-543bc11b234d",
        "1497366216548-37526070297c",
    ],
    "DOM-ASSET": [
        "1553413077-190dd305871c",
        "1586528116311-ad8dd3c8310d",
        "1566576912321-884a322b5463",
        "1587295505552-e48d4365a2f8",
        "1497215728101-856f4ea42174",
        "1486406146926-c627a92ad1ab",
    ],
    "DOM-CRM": [
        "1556761179-b4dda1f7e3e8",
        "1521791138484-c2a0e5d94c05",
        "1600880292203-757bb62b4baf",
        "1551836022-d5d88e9218df",
        "1552664730-d307ca884978",
        "1522202176988-66273c2fd55f",
    ],
    "DOM-EVENT": [
        "1551836022-d5d88e9218df",
        "1522202176988-66273c2fd55f",
        "1552664730-d307ca884978",
        "1556761179-b4dda1f7e3e8",
        "1521791138484-c2a0e5d94c05",
        "1600880292203-757bb62b4baf",
    ],
    "DOM-ACTIVITY": [
        "1523580494863-6f3031224c94",
        "1505373877841-8d25f7d46678",
        "1540575467063-178a50c2df87",
        "1529156069898-49953e39b1ac",
        "1517245386807-bb43f82c33c4",
        "1522071820081-009f0129c71c",
    ],
    "DOM-COURSE": [
        "1523240795612-9a054b0db644",
        "1509062522246-3755977927d7",
        "1524178232363-1fb2b075b655",
        "1486312338219-ce68d2c6f44d",
        "1455390582262-044cdead135a",
        "1499750310102-2b4b9a5b1d8a",
    ],
    "DOM-LOST": [
        "1497366811353-6870744d04b2",
        "1497366754035-f200968a6e72",
        "1529156069898-49953e39b1ac",
        "1486406146926-c627a92ad1ab",
        "1497366216548-37526070297c",
        "1497215728101-856f4ea42174",
    ],
    "DOM-SHOP": [
        "1441986300917-64674bd600d8",
        "1472851294608-062f824d29cc",
        "1556742049-0cfed4f6a45d",
        "1483985988106-5bed74ebaa38",
        "1497215728101-856f4ea42174",
        "1441984904996-e0b6ba687e04",
    ],
    "DOM-FOOD": [
        "1414235077428-338989a2e8c0",
        "1555939594-58d7cb561ad1",
        "1504674900247-0877df9cc836",
        "1517248135467-4c7edcad34c4",
        "1565299624946-b28f40a0ae38",
        "1559339352-11d035aa65de",
    ],
    "DOM-MEDIA": [
        "1489597841871-5aae429cfe5e",
        "1478720568477-1520c75063ef",
        "1536440136628-849c17754e3d",
        "1489590313635-f39d5193a4ea",
        "1517604931442-48118040a824",
        "1470229722913-7c0e2dfb8b1c",
    ],
    "DOM-MUSIC": [
        "1511379938546-c1fef3a1a8f0",
        "1514320291860-5e1ff1ff9c9a",
        "1493225457124-a3eb161ffa5f",
        "1511379938547-c1f69419868d",
        "1514525253161-7a46d19cd819",
        "1470225620780-dbe8f1019dba",
    ],
    "DOM-FORUM": [
        "1522071820081-009f0129c71c",
        "1552664730-d307ca884978",
        "1517245386807-bb43f82c33c4",
        "1516321318423-f06f85e504b3",
        "1522202176988-66273c2fd55f",
        "1529156069898-49953e39b1ac",
    ],
    "DOM-BLOG": [
        "1432821596592-e2c18b78144f",
        "1456327102063-fb1691c3f9a1",
        "1499750310102-2b4b9a5b1d8a",
        "1486312338219-ce68d2c6f44d",
        "1455390582262-044cdead135a",
        "1497215728101-856f4ea42174",
    ],
}

_DEFAULT_CAPTIONS = [
    {"title": "欢迎使用", "lead": "检索业务对象并提交申请。"},
    {"title": "使用须知", "lead": "请按流程申请，按时完结单据。"},
    {"title": "服务时间", "lead": "工作日开放办理，详见公告。"},
    {"title": "便捷办理", "lead": "在线提交、进度可查，少跑腿。"},
    {"title": "公告提醒", "lead": "重要变更与临时通知见公告栏。"},
]

_WELCOME_TITLE = "欢迎使用"


def _is_welcome_title(title: str) -> bool:
    t = (title or "").strip()
    return t == _WELCOME_TITLE or t.startswith("欢迎")


def _welcome_lead(schema: dict[str, Any]) -> str:
    labels = schema.get("labels") or {}
    for key in ("portalBannerWelcomeLead", "portalBannerLead", "authLead"):
        raw = labels.get(key)
        if not raw:
            continue
        text = str(raw).strip()
        for sep in ("。", "；", ";", "\n"):
            if sep in text:
                head = text.split(sep, 1)[0].strip()
                if head:
                    return head + ("。" if sep == "。" else "。")
        return text if text.endswith("。") else text + "。"
    return _DEFAULT_CAPTIONS[0]["lead"]


def _ensure_welcome_first(
    captions: list[dict[str, str]], schema: dict[str, Any] | None
) -> list[dict[str, str]]:
    """各域轮播第一帧固定「欢迎使用」，领域句从第二帧起。"""
    schema = schema or {}
    welcome = {"title": _WELCOME_TITLE, "lead": _welcome_lead(schema)}
    rest: list[dict[str, str]] = []
    for cap in captions:
        title = str(cap.get("title") or "").strip()
        if _is_welcome_title(title):
            if not welcome.get("lead") or welcome["lead"] == _DEFAULT_CAPTIONS[0]["lead"]:
                lead = str(cap.get("lead") or "").strip()
                if lead:
                    welcome["lead"] = lead
            continue
        rest.append({"title": title or "通知", "lead": str(cap.get("lead") or "").strip()})
    return [welcome, *rest]


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
            return _ensure_welcome_first(out, schema)
    labels = schema.get("labels") or {}
    base = [
        {
            "title": str(labels.get("portalBannerTitle") or _DEFAULT_CAPTIONS[0]["title"]),
            "lead": str(
                labels.get("portalBannerLead")
                or _DEFAULT_CAPTIONS[0]["lead"]
            ),
        },
        *[dict(c) for c in _DEFAULT_CAPTIONS[1:]],
    ]
    return _ensure_welcome_first(base, schema)


def _expand_captions(captions: list[dict[str, str]], count: int) -> list[dict[str, str]]:
    """不足 count 时用通用句补齐（不重复同一条领域文案）。"""
    if not captions:
        captions = [dict(c) for c in _DEFAULT_CAPTIONS]
    out = [dict(c) for c in captions]
    seen = {(c["title"], c["lead"]) for c in out}
    for pad in _DEFAULT_CAPTIONS:
        if len(out) >= count:
            break
        key = (pad["title"], pad["lead"])
        if key in seen:
            continue
        seen.add(key)
        out.append(dict(pad))
    # 仍不足则停止在已有条数（宁可少帧，也不复用同文案硬凑）
    return out[:count]


def _photo_pool(domain: str) -> list[str]:
    """合并领域 / 登录兜底 / 其它域图源，去重后供轮播抽不重复图。"""
    seen: set[str] = set()
    out: list[str] = []

    def add_all(ids: list[str] | None) -> None:
        for pid in ids or []:
            p = (pid or "").strip()
            if not p or p in seen:
                continue
            seen.add(p)
            out.append(p)

    add_all(_PORTAL_FALLBACK.get(domain))
    add_all(_FALLBACK_PHOTOS.get(domain))
    for d, ids in _PORTAL_FALLBACK.items():
        if d != domain:
            add_all(ids)
    for d, ids in _FALLBACK_PHOTOS.items():
        if d != domain:
            add_all(ids)
    add_all(_FALLBACK_PHOTOS.get("DOM-GENERIC"))
    return out


def _pick_portal_ids(domain: str, theme: str, count: int = PORTAL_BANNER_COUNT) -> list[str]:
    photos = _photo_pool(domain)
    if not photos:
        return []
    h = int(hashlib.md5(f"portal|{domain}|{theme}".encode()).hexdigest()[:8], 16)
    start = h % len(photos)
    rotated = photos[start:] + photos[:start]
    # 只取不重复的前 count 张（池多大就多少，绝不 modulo 复用同一 id）
    return rotated[: min(count, len(rotated))]


def _download_portal_photo(pid: str, dest: Path, *, timeout: float = 4.0) -> bool:
    url = (
        f"https://images.unsplash.com/photo-{pid}"
        f"?auto=format&fit=crop&w=1800&h=720&q=80"
    )
    return _download(url, dest, timeout=timeout)


def _content_md5(path: Path) -> str:
    try:
        return hashlib.md5(path.read_bytes()).hexdigest()
    except OSError:
        return ""


def fetch_portal_banners(
    workspace: Path,
    domain: str,
    theme: str,
    schema: dict[str, Any] | None = None,
    count: int = PORTAL_BANNER_COUNT,
) -> list[dict[str, str]]:
    """写入 public/portal-banners/{n}.jpg；失败不抛。网络慢时尽快跳过。"""
    if not domain_wants_portal_banners(domain):
        return []

    count = max(3, min(int(count or PORTAL_BANNER_COUNT), 8))
    settings = get_settings()
    public = workspace / "frontend" / "public" / "portal-banners"
    public.mkdir(parents=True, exist_ok=True)
    cache_dir = settings.cache_dir / "portal-banners"
    cache_dir.mkdir(parents=True, exist_ok=True)

    # 清掉旧轮播，避免残留 1.jpg/3.jpg 缺号或旧重复图
    for old in public.glob("*.jpg"):
        try:
            old.unlink()
        except OSError:
            pass

    captions = _expand_captions(_caption_seeds(schema), count)
    candidates = _pick_portal_ids(domain, theme, max(count * 2, 12))  # 多备几张，失败可换
    query = build_query(domain, theme) + " wide interior"
    key = (getattr(settings, "unsplash_access_key", None) or "").strip()

    slides: list[dict[str, str]] = []
    used_hashes: set[str] = set()
    net_fail = 0

    # 有 Key：先批量检索，按结果逐张下载（每帧不同图）
    api_urls: list[str] = []
    if key:
        api_urls = _search_photo_urls(query, key, limit=max(count + 3, 8), timeout=8.0)
        if not api_urls:
            log.warning("portal banners unsplash search empty for %s", domain)

    for img_url in api_urls:
        if len(slides) >= count or len(slides) >= len(captions):
            break
        slot = len(slides) + 1
        dest = public / f"{slot}.jpg"
        cache_key = hashlib.md5(f"portal-api|{domain}|{theme}|{img_url}".encode()).hexdigest()[:16]
        cache_file = cache_dir / f"{domain}-{cache_key}.jpg".replace("/", "_")
        ok = False
        if cache_file.is_file() and cache_file.stat().st_size > 2000:
            try:
                dest.write_bytes(cache_file.read_bytes())
                ok = True
            except OSError:
                ok = False
        elif net_fail >= 4:
            log.warning("portal banner network aborted after failures (%s)", domain)
            break
        else:
            ok = _download(img_url, dest, timeout=4.0)
            if ok and dest.is_file():
                try:
                    cache_file.write_bytes(dest.read_bytes())
                except OSError:
                    pass
            else:
                net_fail += 1
                dest.unlink(missing_ok=True)
                continue

        if not ok or not dest.is_file() or dest.stat().st_size < 2000:
            dest.unlink(missing_ok=True)
            continue
        digest = _content_md5(dest)
        if not digest or digest in used_hashes:
            dest.unlink(missing_ok=True)
            log.warning("portal banner skip duplicate api image for %s", domain)
            continue
        used_hashes.add(digest)
        cap = captions[len(slides)]
        slides.append({
            "src": f"/portal-banners/{slot}.jpg",
            "title": cap["title"],
            "lead": cap["lead"],
        })

    # 不足再用固定 photo id 补齐（仍去重）
    for pid in candidates:
        if len(slides) >= count or len(slides) >= len(captions):
            break
        slot = len(slides) + 1
        dest = public / f"{slot}.jpg"
        cache_key = hashlib.md5(f"portal|{domain}|{theme}|{pid}".encode()).hexdigest()[:16]
        cache_file = cache_dir / f"{domain}-{cache_key}.jpg".replace("/", "_")
        ok = False
        if cache_file.is_file() and cache_file.stat().st_size > 2000:
            try:
                dest.write_bytes(cache_file.read_bytes())
                ok = True
            except OSError:
                ok = False
        elif net_fail >= 4:
            log.warning("portal banner network aborted after failures (%s)", domain)
            break
        else:
            ok = _download_portal_photo(pid, dest, timeout=4.0)
            if ok and dest.is_file():
                try:
                    cache_file.write_bytes(dest.read_bytes())
                except OSError:
                    pass
            else:
                net_fail += 1
                dest.unlink(missing_ok=True)
                continue

        if not ok or not dest.is_file() or dest.stat().st_size < 2000:
            dest.unlink(missing_ok=True)
            continue

        digest = _content_md5(dest)
        if not digest or digest in used_hashes:
            dest.unlink(missing_ok=True)
            log.warning("portal banner skip duplicate image for %s (%s)", domain, pid)
            continue
        used_hashes.add(digest)
        cap = captions[len(slides)]
        slides.append({
            "src": f"/portal-banners/{slot}.jpg",
            "title": cap["title"],
            "lead": cap["lead"],
        })

    log.info("portal banners: %s × %s (unique)%s", domain, len(slides), " · api" if api_urls else "")
    return slides


def portal_banners_from_workspace(
    workspace: Path, schema: dict[str, Any] | None = None
) -> list[dict[str, str]]:
    public = workspace / "frontend" / "public" / "portal-banners"
    if not public.is_dir():
        return []
    captions = _expand_captions(_caption_seeds(schema), PORTAL_BANNER_COUNT)
    slides: list[dict[str, str]] = []
    used_hashes: set[str] = set()
    for i in range(1, 9):
        if len(slides) >= len(captions):
            break
        path = public / f"{i}.jpg"
        if not path.is_file() or path.stat().st_size < 2000:
            continue
        digest = _content_md5(path)
        if not digest or digest in used_hashes:
            continue
        used_hashes.add(digest)
        cap = captions[len(slides)]
        slides.append({
            "src": f"/portal-banners/{i}.jpg",
            "title": cap["title"],
            "lead": cap["lead"],
        })
    return slides
