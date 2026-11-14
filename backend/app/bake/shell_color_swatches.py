# -*- coding: utf-8 -*-
"""壳色色点池（确定性静态资产）。

真源口径：docs/shell-color-swatch-pool.md
- 行业配色 themes/*.css 的 --portal-brand / --portal-accent 必须入池
- 人可有限自配 brand + accent；禁止运行时 LLM 现吐 hex
- 出包仍写 APP_DELIVERED.shellColors（cover/glow 随两色派生）
"""

from __future__ import annotations

import colorsys
import re
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Literal

Role = Literal["brand", "accent", "both"]
Tone = Literal["warm", "cool", "neutral"]

_HEX_RE = re.compile(r"^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")

# 浅底对照（按钮字白 / 底色对比）
_LIGHT_BG = ("#F4F6F8", "#FFFFFF", "#FFFDF8", "#EEF3F5")

# 通用稳色（主题灌池后若缺则补；id 稳定，勿随意改）
_CURATED: tuple[tuple[str, str, Role, Tone, str], ...] = (
    ("g-ink-teal", "#0b6e75", "both", "cool", "稳青绿"),
    ("g-ink-slate", "#475569", "both", "cool", "稳灰蓝"),
    ("g-ink-forest", "#15803d", "both", "cool", "稳叶绿"),
    ("g-ink-navy", "#1e3a5f", "both", "cool", "稳藏青"),
    ("g-ink-wine", "#9f1239", "both", "warm", "稳酒红"),
    ("g-ink-clay", "#9a3412", "both", "warm", "稳陶土"),
    ("g-accent-sky", "#0ea5e9", "accent", "cool", "点缀天蓝"),
    ("g-accent-coral", "#e1453d", "accent", "warm", "点缀珊瑚"),
    ("g-accent-amber", "#ca8a04", "accent", "warm", "点缀琥珀（慎作大面积壳底）"),
    ("g-accent-lime", "#65a30d", "accent", "cool", "点缀叶绿"),
)


@dataclass(frozen=True)
class ShellSwatch:
    id: str
    hex: str
    roles: frozenset[str]
    tone: Tone
    note: str = ""

    def as_dict(self) -> dict[str, Any]:
        roles = sorted(self.roles)
        role_label: Role = "both" if set(roles) >= {"brand", "accent"} else roles[0]  # type: ignore[assignment]
        return {
            "id": self.id,
            "hex": self.hex,
            "roles": roles,
            "role": role_label,
            "tone": self.tone,
            "note": self.note,
            "brand_ok": "brand" in self.roles,
            "accent_ok": "accent" in self.roles,
        }


def normalize_hex(raw: str | None) -> str | None:
    """#RGB / #RRGGBB → 小写 #rrggbb；非法则 None。"""
    s = (raw or "").strip()
    if not s:
        return None
    if not s.startswith("#"):
        s = f"#{s}"
    if not _HEX_RE.match(s):
        return None
    body = s[1:]
    if len(body) == 3:
        body = "".join(ch * 2 for ch in body)
    return f"#{body.lower()}"


def _parse_rgb(hex_color: str) -> tuple[float, float, float]:
    h = normalize_hex(hex_color)
    if not h:
        raise ValueError(f"invalid hex: {hex_color!r}")
    return int(h[1:3], 16) / 255.0, int(h[3:5], 16) / 255.0, int(h[5:7], 16) / 255.0


def relative_luminance(hex_color: str) -> float:
    def chan(c: float) -> float:
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = _parse_rgb(hex_color)
    return 0.2126 * chan(r) + 0.7152 * chan(g) + 0.0722 * chan(b)


def contrast_ratio(a: str, b: str) -> float:
    la, lb = relative_luminance(a), relative_luminance(b)
    lighter, darker = max(la, lb), min(la, lb)
    return (lighter + 0.05) / (darker + 0.05)


def _hsl(hex_color: str) -> tuple[float, float, float]:
    r, g, b = _parse_rgb(hex_color)
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    return h * 360.0, s, l


def tone_of(hex_color: str) -> Tone:
    h, s, _l = _hsl(hex_color)
    if s < 0.18:
        return "neutral"
    # 暖：红–黄–橙；冷：绿–青–蓝–紫
    if h < 70 or h >= 330:
        return "warm"
    if 70 <= h < 100 and s > 0.45:
        return "warm"
    return "cool"


def is_dirty_warm_for_brand(hex_color: str) -> bool:
    """高饱和脏黄 / 荧光：不宜作大面积壳主色（可作点缀）。"""
    h, s, l = _hsl(hex_color)
    if s < 0.42:
        return False
    # 黄–金–荧光绿黄
    if 40 <= h <= 95 and l > 0.38:
        return True
    # 过高明度高饱和（荧光感）
    if s > 0.72 and l > 0.52:
        return True
    return False


def brand_contrast_ok(hex_color: str, min_ratio: float = 3.0) -> bool:
    """主色作按钮底、白字时，对常见浅底/白字有基本对比。"""
    hx = normalize_hex(hex_color)
    if not hx:
        return False
    # 白字在 brand 上
    if contrast_ratio(hx, "#FFFFFF") >= min_ratio:
        return True
    # 深字在 brand 上（浅色品牌条）
    if contrast_ratio(hx, "#1A1E24") >= min_ratio:
        # 且与浅底能分得开
        return any(contrast_ratio(hx, bg) >= 1.2 for bg in _LIGHT_BG)
    return False


def _swatch_id_for_hex(hex_color: str) -> str:
    hx = normalize_hex(hex_color) or "#000000"
    return f"c-{hx[1:]}"


def _merge_roles(existing: frozenset[str] | None, role: str) -> frozenset[str]:
    base = set(existing or ())
    if role == "both":
        base.update({"brand", "accent"})
    else:
        base.add(role)
    return frozenset(base)


@lru_cache(maxsize=1)
def shell_swatch_pool() -> tuple[ShellSwatch, ...]:
    """静态池：主题灌入 + 通用稳色；按 id 稳定排序。"""
    from app.bake.shell_face import _theme_token_map

    by_hex: dict[str, dict[str, Any]] = {}

    def add(hex_raw: str, role: str, note: str = "", forced_id: str | None = None) -> None:
        hx = normalize_hex(hex_raw)
        if not hx:
            return
        row = by_hex.get(hx)
        if row is None:
            row = {
                "id": forced_id or _swatch_id_for_hex(hx),
                "hex": hx,
                "roles": frozenset(),
                "note": note,
            }
            by_hex[hx] = row
        elif forced_id and not str(row["id"]).startswith("g-"):
            # 保留 curated 优先 id
            pass
        row["roles"] = _merge_roles(row["roles"], role)
        if note and not row.get("note"):
            row["note"] = note

    tokens = _theme_token_map()
    for tid, toks in tokens.items():
        brand = toks.get("brand")
        accent = toks.get("accent")
        if brand:
            add(brand, "brand", note=f"theme:{tid}:brand")
        if accent:
            add(accent, "accent", note=f"theme:{tid}:accent")

    for cid, hx, role, _tone, note in _CURATED:
        add(hx, role, note=note, forced_id=cid)
        # curated 强制 id
        nh = normalize_hex(hx)
        if nh and nh in by_hex:
            by_hex[nh]["id"] = cid
            if note:
                by_hex[nh]["note"] = note

    out: list[ShellSwatch] = []
    for hx, row in by_hex.items():
        roles = set(row["roles"])
        # 脏暖色：降权，不许当 brand
        if is_dirty_warm_for_brand(hx):
            roles.discard("brand")
            roles.add("accent")
            note = row.get("note") or ""
            if "慎" not in note:
                note = (note + " · 慎作壳主色").strip(" ·")
            row["note"] = note
        # 对比度不够的也不进 brand
        if "brand" in roles and not brand_contrast_ok(hx):
            roles.discard("brand")
            roles.add("accent")
            note = row.get("note") or ""
            if "对比" not in note:
                note = (note + " · 浅底对比弱，仅点缀").strip(" ·")
            row["note"] = note
        if not roles:
            continue
        out.append(
            ShellSwatch(
                id=str(row["id"]),
                hex=hx,
                roles=frozenset(roles),
                tone=tone_of(hx),
                note=str(row.get("note") or ""),
            )
        )

    out.sort(key=lambda s: (0 if s.id.startswith("g-") else 1, s.id))
    return tuple(out)


@lru_cache(maxsize=1)
def _pool_by_id() -> dict[str, ShellSwatch]:
    return {s.id: s for s in shell_swatch_pool()}


@lru_cache(maxsize=1)
def _pool_by_hex() -> dict[str, ShellSwatch]:
    return {s.hex: s for s in shell_swatch_pool()}


def list_shell_swatches(*, role: str | None = None) -> list[dict[str, Any]]:
    """控制台 / catalog 用。role=brand|accent 时过滤。"""
    rows = [s.as_dict() for s in shell_swatch_pool()]
    if role in ("brand", "accent"):
        rows = [r for r in rows if role in r["roles"]]
    return rows


def get_swatch(swatch_id: str | None) -> ShellSwatch | None:
    sid = (swatch_id or "").strip()
    if not sid:
        return None
    return _pool_by_id().get(sid)


def resolve_swatch_hex(swatch_id: str | None, *, role: str) -> str | None:
    """取池内 hex；角色不匹配则 None。"""
    sw = get_swatch(swatch_id)
    if not sw:
        return None
    if role not in sw.roles:
        return None
    return sw.hex


def validate_swatch_choice(
    swatch_id: str | None,
    *,
    role: Literal["brand", "accent"],
) -> str | None:
    """合法返回 None；非法返回中文原因。空 id 表示跟行业配色，合法。"""
    sid = (swatch_id or "").strip()
    if not sid:
        return None
    sw = get_swatch(sid)
    if not sw:
        return f"色点不在池内：{sid}"
    if role not in sw.roles:
        if role == "brand":
            return f"「{sw.note or sid}」不宜作壳主色，请换一档或只作点缀"
        return f"色点不可作{role}：{sid}"
    if role == "brand" and not brand_contrast_ok(sw.hex):
        return "主色与浅底对比不足，请另选"
    return None


def derive_cover_glow(brand: str, accent: str) -> dict[str, str]:
    return {
        "cover": f"linear-gradient(160deg, {accent}, {brand})",
        "glow": accent,
    }


def overlay_shell_colors(
    base: dict[str, str] | None,
    *,
    brand_swatch: str | None = None,
    accent_swatch: str | None = None,
) -> dict[str, str]:
    """在主题/域派生色上叠自配；未选则原样。"""
    out = dict(base or {})
    brand_hex = resolve_swatch_hex(brand_swatch, role="brand")
    accent_hex = resolve_swatch_hex(accent_swatch, role="accent")
    if brand_hex:
        out["brand"] = brand_hex
    if accent_hex:
        out["accent"] = accent_hex
    brand = out.get("brand") or brand_hex or "#0b6e75"
    accent = out.get("accent") or accent_hex or brand
    out.setdefault("bg", "#F4F6F8")
    out.setdefault("surface", "#FFFFFF")
    out.setdefault("ink", "#1A1E24")
    out.update(derive_cover_glow(brand, accent))
    return out


def pair_gate_issues(
    brand_hex: str | None,
    accent_hex: str | None,
) -> list[str]:
    """P3：硬拦 + 软提示（确定性）。空列表 = 过。"""
    return pair_gate_blockers(brand_hex, accent_hex) + pair_gate_soft_tips(
        brand_hex, accent_hex
    )


def pair_gate_blockers(
    brand_hex: str | None,
    accent_hex: str | None,
) -> list[str]:
    """硬拦：脏主色 / 对比不足。保存与出包须红。"""
    del accent_hex  # 互撞不硬拦
    issues: list[str] = []
    b = normalize_hex(brand_hex)
    if b and is_dirty_warm_for_brand(b):
        issues.append("主色偏脏暖/荧光，不适合大面积壳底")
    if b and not brand_contrast_ok(b):
        issues.append("主色与浅底/白字对比不足")
    return issues


def pair_gate_soft_tips(
    brand_hex: str | None,
    accent_hex: str | None,
) -> list[str]:
    """软提示：高饱和互撞 / 过近；不禁保存，靠预览自查。"""
    tips: list[str] = []
    b = normalize_hex(brand_hex)
    a = normalize_hex(accent_hex)
    if not (b and a):
        return tips
    hb, sb, _lb = _hsl(b)
    ha, sa, _la = _hsl(a)
    dh = abs(hb - ha)
    dh = min(dh, 360 - dh)
    if sb > 0.55 and sa > 0.55 and dh > 100:
        tips.append("主色与点缀高饱和且色相过冲，预览请核对")
    if contrast_ratio(b, a) < 1.15 and sb > 0.3 and sa > 0.3:
        tips.append("主色与点缀过于接近，强调条可能糊成一片")
    return tips


def theme_tokens_missing_from_pool() -> list[str]:
    """护栏：主题 brand/accent 必须能在池里按 hex 找到。"""
    from app.bake.shell_face import _theme_token_map

    by_hex = _pool_by_hex()
    missing: list[str] = []
    for tid, toks in _theme_token_map().items():
        for role in ("brand", "accent"):
            hx = normalize_hex(toks.get(role))
            if not hx:
                missing.append(f"{tid}:{role}:empty")
            elif hx not in by_hex:
                missing.append(f"{tid}:{role}:{hx}")
            elif role == "brand" and "brand" not in by_hex[hx].roles:
                # 被降权为仅 accent 也算入池（hex 在），不报 missing
                pass
    return missing


def assert_pool_invariants() -> None:
    """测试入口：表完整、禁空 hex、角色合法。"""
    pool = shell_swatch_pool()
    if not pool:
        raise AssertionError("shell swatch pool empty")
    ids: set[str] = set()
    for s in pool:
        if not s.id or s.id in ids:
            raise AssertionError(f"bad/dup id: {s.id!r}")
        ids.add(s.id)
        if not normalize_hex(s.hex):
            raise AssertionError(f"bad hex: {s.id}={s.hex!r}")
        if not s.roles or not s.roles <= {"brand", "accent"}:
            raise AssertionError(f"bad roles: {s.id}={s.roles!r}")
        if s.tone not in {"warm", "cool", "neutral"}:
            raise AssertionError(f"bad tone: {s.id}={s.tone!r}")
    miss = theme_tokens_missing_from_pool()
    if miss:
        raise AssertionError(f"theme tokens not in pool: {miss[:12]}")


def clear_pool_cache() -> None:
    """测试改 CSS mock 时用。"""
    shell_swatch_pool.cache_clear()
    _pool_by_id.cache_clear()
    _pool_by_hex.cache_clear()
