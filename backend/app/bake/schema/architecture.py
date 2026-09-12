"""论文「系统逻辑架构图」：B/S 分层，画法对齐常见开题图 4.x。

真源：domain.schema.json 的交付角色（与用例图 actors 同口径）。
框内固定：界面 → Vue → SpringBoot → MySQL；界面↔Vue 旁标 HTTPS / 发起请求。
样式：白底黑框直角矩形、浅蓝双箭（上下各一支），不加圆角/阴影/色块。
箭数：角色→界面、界面→Vue 按角色列多路；Vue→SpringBoot、SpringBoot→MySQL 仅居中一对。
"""

from __future__ import annotations

import html
import json
import re
from pathlib import Path
from typing import Any

from app.bake.schema.usecases import list_usecase_actors

# —— 画布几何（论文插图比例）——
_PAD_X = 48.0
_PAD_Y = 36.0
_ROLE_H = 40.0
_ROLE_GAP = 48.0
_ROLE_W_MIN = 100.0
_ROLE_W_MAX = 160.0
_LAYER_H = 42.0
_ARROW_GAP = 58.0  # 层间留给双箭 + 文案的高度
_ARROW_PAIR_DX = 10.0  # 下箭 / 上箭水平错开
_STROKE = 1.2
_ARROW_COLOR = "#5B9BD5"
_FONT = "Microsoft YaHei, SimSun, serif"
_FONT_TECH = "Times New Roman, SimSun, serif"


def _esc(s: str) -> str:
    return html.escape(str(s or ""), quote=True)


def _f(v: float) -> str:
    return f"{v:.1f}"


def _role_box_w(label: str) -> float:
    """按中文长度估宽，避免长岗位名挤框。"""
    n = max(1, len(str(label or "")))
    # 约 14px 字宽 + 左右内边距
    w = 28.0 + n * 14.0
    return max(_ROLE_W_MIN, min(_ROLE_W_MAX, w))


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return data if isinstance(data, dict) else None


def architecture_roles(schema: dict[str, Any]) -> list[dict[str, str]]:
    """顶层角色框：与用例图 actors 同口径；顺序对齐论文习惯（用户 → 中间角色 → 管理员）。"""
    actors = list_usecase_actors(schema)
    raw: list[dict[str, str]] = []
    for a in actors:
        if not isinstance(a, dict):
            continue
        aid = str(a.get("id") or "").strip()
        lab = str(a.get("label") or "").strip() or aid
        if not aid:
            continue
        raw.append({"id": aid, "label": lab})
    if not raw:
        roles = schema.get("roles") if isinstance(schema.get("roles"), dict) else {}
        for key, fallback in (("user", "用户"), ("subadmin", "经办员"), ("admin", "管理员")):
            slot = roles.get(key)
            if not isinstance(slot, dict):
                continue
            lab = str(slot.get("label") or "").strip() or fallback
            # 与用例图短名一致：去括号说明
            lab = re.sub(r"[（(][^）)]*[）)]", "", lab).strip() or fallback
            raw.append({"id": key, "label": lab})
        if not raw:
            return [{"id": "user", "label": "用户"}, {"id": "admin", "label": "管理员"}]
    users = [a for a in raw if a["id"] == "user"]
    admins = [a for a in raw if a["id"] == "admin"]
    mids = [a for a in raw if a["id"] not in ("user", "admin")]
    return users + mids + admins


def architecture_model(
    schema: dict[str, Any],
    *,
    title_fallback: str = "管理系统",
) -> dict[str, Any]:
    title = str(schema.get("title") or "").strip() or title_fallback
    roles = architecture_roles(schema)
    return {
        "title": title,
        "figure_title": "系统逻辑架构图",
        "roles": roles,
        "layers": [
            {"id": "ui", "label": "界面", "bold": False},
            {"id": "vue", "label": "Vue", "bold": True},
            {"id": "boot", "label": "SpringBoot", "bold": True},
            {"id": "db", "label": "MySQL", "bold": True},
        ],
        "protocol_label": "HTTPS",
        "action_label": "发起请求",
        "description": (
            f"本系统采用 B/S 架构，面向{ '、'.join(r['label'] for r in roles) }等角色；"
            "角色经界面发起 HTTPS 请求，前端 Vue 与后端 SpringBoot 交互，数据持久化于 MySQL。"
        ),
        "source_note": "角色取自交付门户/岗位；技术栈为工厂默认 B/S（Vue + Spring Boot + MySQL）。",
        "style": {
            "box_fill": "#ffffff",
            "box_stroke": "#000000",
            "arrow": _ARROW_COLOR,
            "rules_zh": [
                "白底黑框直角矩形，无圆角无阴影",
                "角色→界面、界面→Vue：按角色列多路双箭",
                "Vue→SpringBoot、SpringBoot→MySQL：居中一对双箭",
                "仅界面↔Vue 旁标 HTTPS（下行侧）/ 发起请求（上行侧）",
            ],
        },
    }


def load_architecture_model(workspace: Path, *, title_fallback: str = "管理系统") -> dict[str, Any] | None:
    schema = _read_json(workspace / "domain.schema.json")
    if not schema:
        return None
    return architecture_model(schema, title_fallback=title_fallback)


def _marker_defs() -> str:
    return (
        '<defs>'
        f'<marker id="arch-arrow" viewBox="0 0 10 10" refX="9" refY="5" '
        f'markerWidth="7" markerHeight="7" orient="auto">'
        f'<path d="M0,0 L10,5 L0,10 z" fill="{_ARROW_COLOR}"/>'
        f"</marker>"
        "</defs>"
    )


def _box(x: float, y: float, w: float, h: float, label: str, *, bold: bool = False) -> str:
    weight = ' font-weight="700"' if bold else ""
    # 技术名略偏衬线，中文层用雅黑
    family = _FONT_TECH if bold else _FONT
    size = 15 if bold else 14
    return (
        f'<rect x="{_f(x)}" y="{_f(y)}" width="{_f(w)}" height="{_f(h)}" '
        f'fill="#fff" stroke="#000" stroke-width="{_STROKE}"/>'
        f'<text x="{_f(x + w / 2)}" y="{_f(y + h / 2 + 5)}" text-anchor="middle" '
        f'font-size="{size}" font-family="{family}"{weight} fill="#000">'
        f"{_esc(label)}</text>"
    )


def _bi_arrows(cx: float, y0: float, y1: float) -> str:
    """一对上下箭：左下行、右上行。"""
    dx = _ARROW_PAIR_DX
    return (
        f'<line x1="{_f(cx - dx)}" y1="{_f(y0)}" x2="{_f(cx - dx)}" y2="{_f(y1)}" '
        f'stroke="{_ARROW_COLOR}" stroke-width="1.2" marker-end="url(#arch-arrow)"/>'
        f'<line x1="{_f(cx + dx)}" y1="{_f(y1)}" x2="{_f(cx + dx)}" y2="{_f(y0)}" '
        f'stroke="{_ARROW_COLOR}" stroke-width="1.2" marker-end="url(#arch-arrow)"/>'
    )


def _protocol_labels(cx: float, mid_y: float, protocol: str, action: str) -> str:
    """HTTPS 在箭对左侧，发起请求在右侧（对齐示例图）。"""
    lx = cx - _ARROW_PAIR_DX - 8
    rx = cx + _ARROW_PAIR_DX + 8
    return (
        f'<text x="{_f(lx)}" y="{_f(mid_y + 4)}" text-anchor="end" '
        f'font-size="11" font-family="{_FONT}" font-weight="700" fill="#000">'
        f"{_esc(protocol)}</text>"
        f'<text x="{_f(rx)}" y="{_f(mid_y + 4)}" text-anchor="start" '
        f'font-size="11" font-family="{_FONT}" fill="#000">'
        f"{_esc(action)}</text>"
    )


def render_architecture_svg(model: dict[str, Any] | None) -> str:
    if not model or not isinstance(model.get("roles"), list) or not model["roles"]:
        body = '<text x="24" y="64" fill="#000" font-family="Microsoft YaHei, SimSun, serif">暂无架构数据</text>'
        return (
            '<?xml version="1.0" encoding="UTF-8"?>'
            f'<svg xmlns="http://www.w3.org/2000/svg" width="320" height="100" viewBox="0 0 320 100">'
            f"{body}</svg>"
        )

    roles = [r for r in model["roles"] if isinstance(r, dict) and str(r.get("label") or "").strip()]
    if not roles:
        roles = [{"id": "user", "label": "用户"}]
    n = len(roles)
    layers = model.get("layers") if isinstance(model.get("layers"), list) else []
    layer_labels: list[tuple[str, bool]] = []
    for layer in layers:
        if isinstance(layer, dict):
            lab = str(layer.get("label") or "").strip()
            if lab:
                layer_labels.append((lab, bool(layer.get("bold"))))
    if len(layer_labels) < 4:
        layer_labels = [
            ("界面", False),
            ("Vue", True),
            ("SpringBoot", True),
            ("MySQL", True),
        ]

    protocol = str(model.get("protocol_label") or "HTTPS").strip() or "HTTPS"
    action = str(model.get("action_label") or "发起请求").strip() or "发起请求"

    role_ws = [_role_box_w(str(r.get("label") or "")) for r in roles]
    # 等宽列：取最大角色框宽，视觉更整齐（贴近示例三等宽）
    col_w = max(role_ws)
    content_w = n * col_w + (n - 1) * _ROLE_GAP
    layer_w = content_w
    # 左右留白：HTTPS / 发起请求 标在箭对两侧
    left_extra = 64.0
    right_extra = 64.0
    total_w = content_w + 2 * _PAD_X + left_extra + right_extra
    origin_x = _PAD_X + left_extra

    # 角色列中心（等宽列）
    role_cx = [origin_x + i * (col_w + _ROLE_GAP) + col_w / 2 for i in range(n)]
    layer_x = origin_x

    y = _PAD_Y
    parts: list[str] = [_marker_defs()]

    # 角色层
    role_y = y
    for i, r in enumerate(roles):
        rx = origin_x + i * (col_w + _ROLE_GAP)
        parts.append(_box(rx, role_y, col_w, _ROLE_H, str(r["label"]), bold=False))
    y = role_y + _ROLE_H

    # 角色 → 界面
    arrow_top = y + 4
    arrow_bot = y + _ARROW_GAP - 4
    for cx in role_cx:
        parts.append(_bi_arrows(cx, arrow_top, arrow_bot))
    y += _ARROW_GAP

    # 逐层：界面 / Vue / SpringBoot / MySQL
    # 画法对齐示例图：界面↔Vue 按角色列多路双箭+HTTPS/发起请求；
    # Vue↔SpringBoot、SpringBoot↔MySQL 仅居中一对双箭。
    layer_cx = layer_x + layer_w / 2
    for li, (lab, bold) in enumerate(layer_labels):
        parts.append(_box(layer_x, y, layer_w, _LAYER_H, lab, bold=bold))
        layer_bottom = y + _LAYER_H
        if li >= len(layer_labels) - 1:
            y = layer_bottom
            break
        a0 = layer_bottom + 4
        a1 = layer_bottom + _ARROW_GAP - 4
        mid = (a0 + a1) / 2
        if li == 0:
            for cx in role_cx:
                parts.append(_bi_arrows(cx, a0, a1))
                parts.append(_protocol_labels(cx, mid, protocol, action))
        else:
            parts.append(_bi_arrows(layer_cx, a0, a1))
        y = layer_bottom + _ARROW_GAP

    total_h = y + _PAD_Y
    inner = "".join(parts)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{int(total_w)}" height="{int(total_h)}" '
        f'viewBox="0 0 {_f(total_w)} {_f(total_h)}" data-figure="architecture">'
        f"{inner}</svg>"
    )
