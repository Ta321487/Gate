"""无网本地氛围图：从学生 themes.css 抽 brand/accent/bg，按域族 + theme 稳定生成 JPEG。

与 AuthShell 的 color-mix 叠色同源，避免外网挂掉后只剩纯渐变水印。
Unsplash 仍优先；本模块仅作最终兜底。
"""

from __future__ import annotations

import hashlib
import logging
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from app.core.config import ROOT, get_settings

log = logging.getLogger("gf.local_atmosphere")

# 生成器版本：改构图时 bump，自动换缓存文件名
_GEN_VER = "v2"

_HEX_RE = re.compile(r"^#?[0-9a-fA-F]{3}([0-9a-fA-F]{3})?$")
_THEME_BLOCK_RE = re.compile(
    r"((?:\[data-theme=[\"'][^\"']+[\"']\]\s*,?\s*)+)\s*\{([^}]*)\}",
    re.MULTILINE,
)
_THEME_ID_RE = re.compile(r'\[data-theme=["\']([^"\']+)["\']\]')
_VAR_RE = re.compile(
    r"--portal-(brand|accent|bg|surface|accent-soft)\s*:\s*(#[0-9a-fA-F]{3,8})\s*;"
)

# 域 → 视觉族（构图差异；配色仍跟 theme CSS）
_DOMAIN_FAMILY: dict[str, str] = {
    "DOM-LIBRARY": "campus",
    "DOM-DORM": "campus",
    "DOM-COURSE": "campus",
    "DOM-ACTIVITY": "campus",
    "DOM-LOST": "campus",
    "DOM-BED": "campus",
    "DOM-CHECKIN": "campus",
    "DOM-FUND": "campus",
    "DOM-CREDIT": "campus",
    "DOM-LABOR": "campus",
    "DOM-EVAL": "campus",
    "DOM-MORAL": "campus",
    "DOM-AWARD": "campus",
    "DOM-GRADE": "campus",
    "DOM-CLUB": "campus",
    "DOM-PROJ": "campus",
    "DOM-RECRUIT": "campus",
    "DOM-PARCEL": "campus",
    "DOM-VISITOR": "campus",
    "DOM-CARPASS": "campus",
    "DOM-CARPOOL": "campus",
    "DOM-PROMO": "campus",
    "DOM-ACAD": "campus",
    "DOM-PARTY": "campus",
    "DOM-ETHIC": "campus",
    "DOM-MUTUAL-TUTOR": "campus",
    "DOM-MUTUAL-TOPIC": "campus",
    "DOM-MUTUAL-TEAM": "campus",
    "DOM-CRM": "office",
    "DOM-ATTEND": "office",
    "DOM-EVENT": "office",
    "DOM-PROPERTY": "office",
    "DOM-SEAL": "office",
    "DOM-CONTRACT": "office",
    "DOM-EXPENSE": "office",
    "DOM-TRIP": "office",
    "DOM-LISTING": "office",
    "DOM-PROCURE": "office",
    "DOM-FITOUT": "office",
    "DOM-CERT": "office",
    "DOM-FLEET": "office",
    "DOM-GENERIC": "office",
    "DOM-SHOP": "trade",
    "DOM-FOOD": "trade",
    "DOM-CINEMA": "trade",
    "DOM-TOUR": "trade",
    "DOM-TIMEBANK": "trade",
    "DOM-HOSPITAL": "care",
    "DOM-SALON": "care",
    "DOM-HOTEL": "hospitality",
    "DOM-CARRENT": "transit",
    "DOM-MEETING": "hospitality",
    "DOM-PARKING": "transit",
    "DOM-IT": "tech",
    "DOM-EQUIP": "tech",
    "DOM-ASSET": "tech",
    "DOM-LABSAFE": "tech",
    "DOM-INSTRUMENT": "tech",
    "DOM-MEDIA": "media",
    "DOM-MUSIC": "media",
    "DOM-FORUM": "media",
    "DOM-BLOG": "media",
    "DOM-EXAM": "media",
    "DOM-SURVEY": "media",
    "DOM-VOTE": "media",
    "DOM-DOCLIB": "media",
    "DOM-INTERN": "office",
    "DOM-DATING": "campus",
}


@dataclass(frozen=True)
class ThemePalette:
    brand: tuple[int, int, int]
    accent: tuple[int, int, int]
    bg: tuple[int, int, int]
    surface: tuple[int, int, int]
    accent_soft: tuple[int, int, int]
    dark: bool = False


_DEFAULT_PALETTE = ThemePalette(
    brand=(8, 84, 90),
    accent=(11, 110, 117),
    bg=(238, 243, 245),
    surface=(255, 255, 255),
    accent_soft=(215, 238, 240),
    dark=False,
)


def _hex_to_rgb(raw: str) -> tuple[int, int, int] | None:
    s = (raw or "").strip()
    if not _HEX_RE.match(s):
        return None
    h = s.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    if len(h) == 8:
        h = h[:6]
    try:
        return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    except ValueError:
        return None


def _mix(
    a: tuple[int, int, int], b: tuple[int, int, int], t: float
) -> tuple[int, int, int]:
    t = max(0.0, min(1.0, t))
    return (
        int(a[0] + (b[0] - a[0]) * t),
        int(a[1] + (b[1] - a[1]) * t),
        int(a[2] + (b[2] - a[2]) * t),
    )


def _luma(c: tuple[int, int, int]) -> float:
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]


def _themes_css_roots() -> list[Path]:
    settings = get_settings()
    styles = settings.skeletons_dir / "baseline" / "frontend" / "src" / "styles"
    roots = [styles / "themes.css", styles / "themes"]
    # 测试 / 异常路径：相对仓库根再试一次
    alt = ROOT / "skeletons" / "baseline" / "frontend" / "src" / "styles"
    if alt != styles:
        roots.extend([alt / "themes.css", alt / "themes"])
    return roots


def _iter_theme_css_text() -> str:
    chunks: list[str] = []
    seen: set[Path] = set()
    for root in _themes_css_roots():
        if root in seen:
            continue
        seen.add(root)
        if root.is_file():
            try:
                chunks.append(root.read_text(encoding="utf-8"))
            except OSError:
                continue
        elif root.is_dir():
            for path in sorted(root.glob("*.css")):
                try:
                    chunks.append(path.read_text(encoding="utf-8"))
                except OSError:
                    continue
    return "\n".join(chunks)


@lru_cache(maxsize=1)
def _all_theme_palettes() -> dict[str, ThemePalette]:
    text = _iter_theme_css_text()
    out: dict[str, ThemePalette] = {}
    for m in _THEME_BLOCK_RE.finditer(text):
        ids = _THEME_ID_RE.findall(m.group(1))
        body = m.group(2)
        vals: dict[str, tuple[int, int, int]] = {}
        for vm in _VAR_RE.finditer(body):
            rgb = _hex_to_rgb(vm.group(2))
            if rgb:
                vals[vm.group(1)] = rgb
        if "brand" not in vals or "accent" not in vals or not ids:
            continue
        brand = vals["brand"]
        accent = vals["accent"]
        bg = vals.get("bg") or _mix(brand, (255, 255, 255), 0.92)
        surface = vals.get("surface") or (255, 255, 255)
        soft = vals.get("accent-soft") or _mix(accent, (255, 255, 255), 0.85)
        dark = _luma(bg) < 80 or any(
            tid.endswith("-night") or tid in ("media-cinema", "music-vinyl")
            for tid in ids
        )
        pal = ThemePalette(
            brand=brand,
            accent=accent,
            bg=bg,
            surface=surface,
            accent_soft=soft,
            dark=dark,
        )
        for tid in ids:
            out[tid.strip()] = pal
    return out


def palette_for_theme(theme: str) -> ThemePalette:
    tid = (theme or "").strip()
    pals = _all_theme_palettes()
    if tid in pals:
        return pals[tid]
    # 旧别名 / 截断匹配
    for key, pal in pals.items():
        if tid and (tid in key or key.endswith(tid)):
            return pal
    return _DEFAULT_PALETTE


def family_for_domain(domain: str) -> str:
    d = (domain or "").strip()
    if d in _DOMAIN_FAMILY:
        return _DOMAIN_FAMILY[d]
    if d.startswith("DOM-MUTUAL"):
        return "campus"
    return "office"


def _seed_int(*parts: str) -> int:
    raw = "|".join(parts)
    return int(hashlib.md5(raw.encode("utf-8")).hexdigest()[:8], 16)


def _draw_orb(
    overlay,
    xy: tuple[int, int],
    r: int,
    color: tuple[int, int, int],
    alpha: int,
) -> None:
    from PIL import Image, ImageDraw

    layer = Image.new("RGBA", overlay.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    x, y = xy
    d.ellipse((x - r, y - r, x + r, y + r), fill=(*color, alpha))
    overlay.alpha_composite(layer)


def _draw_band(
    overlay,
    *,
    y0: int,
    y1: int,
    color: tuple[int, int, int],
    alpha: int,
    slant: int = 0,
) -> None:
    from PIL import Image, ImageDraw

    w, h = overlay.size
    layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    pts = [
        (0, y0),
        (w, y0 + slant),
        (w, y1 + slant),
        (0, y1),
    ]
    d.polygon(pts, fill=(*color, alpha))
    overlay.alpha_composite(layer)


def _motif_shapes(
    overlay,
    family: str,
    pal: ThemePalette,
    rng: int,
    *,
    kind: str,
) -> None:
    """按域族画轻量几何，避免各域同一张糊渐变。"""
    w, h = overlay.size
    a = pal.accent
    b = pal.brand
    soft = pal.accent_soft
    ink = (240, 248, 250) if pal.dark else b

    # 公共光斑
    _draw_orb(
        overlay,
        (int(w * (0.15 + (rng % 40) / 100)), int(h * 0.2)),
        int(min(w, h) * (0.28 + (rng % 17) / 100)),
        soft if not pal.dark else a,
        55 if pal.dark else 90,
    )
    _draw_orb(
        overlay,
        (int(w * (0.72 + (rng % 20) / 100)), int(h * 0.65)),
        int(min(w, h) * 0.35),
        a,
        40 if pal.dark else 70,
    )

    if family == "campus":
        # 横线书架感
        step = max(28, h // 9)
        y = h // 5 + (rng % 17)
        for i in range(5):
            yy = y + i * step
            _draw_band(
                overlay,
                y0=yy,
                y1=yy + 6,
                color=_mix(b, ink, 0.35),
                alpha=35 + (i * 4),
                slant=(rng % 9) - 4,
            )
    elif family == "office":
        # 斜色带 + 卡片块
        _draw_band(
            overlay,
            y0=int(h * 0.35),
            y1=int(h * 0.55),
            color=b,
            alpha=50,
            slant=int(h * 0.08) * (1 if rng % 2 == 0 else -1),
        )
        from PIL import Image, ImageDraw

        layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        d = ImageDraw.Draw(layer)
        cw, ch = int(w * 0.28), int(h * 0.22)
        x0 = int(w * (0.55 + (rng % 10) / 100))
        y0 = int(h * (0.28 + (rng % 12) / 100))
        d.rounded_rectangle(
            (x0, y0, x0 + cw, y0 + ch),
            radius=18,
            fill=(*soft, 100 if not pal.dark else 55),
        )
        overlay.alpha_composite(layer)
    elif family == "trade":
        # 竖向货架/货道
        from PIL import Image, ImageDraw

        layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        d = ImageDraw.Draw(layer)
        gap = w // 7
        x = gap // 2 + (rng % 20)
        for i in range(5):
            d.rectangle(
                (x + i * gap, int(h * 0.18), x + i * gap + 10, int(h * 0.88)),
                fill=(*_mix(a, b, 0.4), 45 + i * 5),
            )
        overlay.alpha_composite(layer)
    elif family == "care":
        _draw_orb(overlay, (w // 2, h // 2), int(min(w, h) * 0.22), soft, 80)
        _draw_orb(overlay, (w // 2, h // 2), int(min(w, h) * 0.12), a, 55)
    elif family == "tech":
        from PIL import Image, ImageDraw

        layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        d = ImageDraw.Draw(layer)
        cell = max(36, min(w, h) // 12)
        ox, oy = rng % cell, (rng // 3) % cell
        for ix in range(-1, w // cell + 2):
            for iy in range(-1, h // cell + 2):
                if (ix + iy + rng) % 3 != 0:
                    continue
                x = ox + ix * cell
                y = oy + iy * cell
                d.rectangle(
                    (x, y, x + cell // 3, y + cell // 3),
                    fill=(*a, 35),
                )
        overlay.alpha_composite(layer)
    elif family == "media":
        _draw_band(
            overlay,
            y0=int(h * 0.15),
            y1=int(h * 0.78),
            color=b,
            alpha=42,
            slant=int(h * 0.12) * (1 if kind == "auth" else -1),
        )
        _draw_orb(
            overlay,
            (int(w * 0.78), int(h * 0.3)),
            int(min(w, h) * 0.18),
            soft,
            70,
        )
    elif family == "transit":
        _draw_band(
            overlay,
            y0=int(h * 0.48),
            y1=int(h * 0.62),
            color=a,
            alpha=60,
            slant=0,
        )
        _draw_band(
            overlay,
            y0=int(h * 0.66),
            y1=int(h * 0.72),
            color=soft,
            alpha=80,
            slant=0,
        )
    elif family == "hospitality":
        _draw_orb(
            overlay,
            (int(w * 0.3), int(h * 0.55)),
            int(min(w, h) * 0.4),
            soft,
            70,
        )
        _draw_band(
            overlay,
            y0=int(h * 0.7),
            y1=h,
            color=b,
            alpha=55,
            slant=-int(h * 0.05),
        )
    else:
        _draw_band(
            overlay,
            y0=int(h * 0.4),
            y1=int(h * 0.7),
            color=a,
            alpha=45,
            slant=int(h * 0.06),
        )


def render_local_atmosphere(
    dest: Path,
    *,
    domain: str,
    theme: str,
    kind: str = "auth",
    slot: int = 0,
    width: int | None = None,
    height: int | None = None,
) -> bool:
    """写入 JPEG；失败返回 False（不抛）。"""
    try:
        from PIL import Image
    except ImportError:
        log.warning("Pillow not installed; skip local atmosphere")
        return False

    kind = "portal" if kind == "portal" else "auth"
    if width is None:
        width = 1800 if kind == "portal" else 1600
    if height is None:
        height = 720 if kind == "portal" else 900

    pal = palette_for_theme(theme)
    family = family_for_domain(domain)
    rng = _seed_int(domain, theme, kind, str(slot), _GEN_VER)

    # 底：小图对角渐变再放大（与 --portal-cover 气质接近，且足够快）
    c0 = _mix(pal.bg, pal.brand, 0.55 if not pal.dark else 0.75)
    c1 = _mix(pal.accent, pal.brand, 0.35 if not pal.dark else 0.55)
    c2 = pal.brand if pal.dark else _mix(pal.accent, (255, 255, 255), 0.15)
    twist = (rng % 40) / 100.0
    c0 = _mix(c0, c1, twist * 0.35)
    c1 = _mix(c1, c2, (1 - twist) * 0.25)
    sw, sh = 48, 27
    small = Image.new("RGB", (sw, sh))
    spx = small.load()
    for y in range(sh):
        ty = y / max(sh - 1, 1)
        row_a = _mix(c0, c1, ty)
        row_b = _mix(c1, c2, ty)
        for x in range(sw):
            tx = x / max(sw - 1, 1)
            t = max(0.0, min(1.0, tx * 0.65 + ty * 0.35))
            spx[x, y] = _mix(row_a, row_b, t)
    img = small.resize((width, height), Image.Resampling.LANCZOS)

    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    _motif_shapes(overlay, family, pal, rng, kind=kind)
    if kind == "auth":
        _draw_orb(
            overlay,
            (int(width * 0.1), int(height * 0.85)),
            int(min(width, height) * 0.45),
            pal.surface if not pal.dark else pal.accent,
            35,
        )
    else:
        _draw_orb(
            overlay,
            (int(width * 0.9), int(height * 0.15)),
            int(min(width, height) * 0.5),
            pal.accent_soft,
            50 if not pal.dark else 30,
        )

    base = img.convert("RGBA")
    base.alpha_composite(overlay)
    out = base.convert("RGB")

    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        out.save(dest, format="JPEG", quality=88, optimize=True)
    except OSError as e:
        log.warning("local atmosphere save failed: %s", e)
        return False
    if not dest.is_file() or dest.stat().st_size < 2000:
        dest.unlink(missing_ok=True)
        return False
    log.info(
        "local atmosphere %s/%s family=%s theme=%s → %s",
        kind,
        slot,
        family,
        theme,
        dest.name,
    )
    return True


def write_local_atmosphere_cached(
    dest: Path,
    *,
    domain: str,
    theme: str,
    kind: str = "auth",
    slot: int = 0,
    cache_dir: Path | None = None,
) -> bool:
    """带磁盘缓存的本地生成（同 domain|theme|kind|slot 可复用）。"""
    settings = get_settings()
    cdir = cache_dir or (settings.cache_dir / "local-atmosphere")
    cdir.mkdir(parents=True, exist_ok=True)
    key = hashlib.md5(
        f"{_GEN_VER}|{domain}|{theme}|{kind}|{slot}".encode()
    ).hexdigest()[:16]
    cache_file = cdir / f"{kind}-{domain}-{theme}-{slot}-{key}.jpg".replace("/", "_")
    if cache_file.is_file() and cache_file.stat().st_size > 2000:
        try:
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(cache_file.read_bytes())
            return True
        except OSError:
            pass
    if not render_local_atmosphere(
        dest, domain=domain, theme=theme, kind=kind, slot=slot
    ):
        return False
    try:
        cache_file.write_bytes(dest.read_bytes())
    except OSError:
        pass
    return True
