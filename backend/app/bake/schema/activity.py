"""论文「系统活动图」：固定 3 张，三泳道（用户 / 系统 / 数据库）。

真源与候选与序列图同源：domain.schema.json + bake 包 Controller/Vue。
流程操作与同 ids 序列图一致（复用 build_diagram_messages），仅改画法。
禁止：kind 中文句库、示例「自习室」题材、菱形框内写判断条件、序列图生命线/激活条。
"""

from __future__ import annotations

import html
from pathlib import Path
from typing import Any

from app.bake.schema.sequence import (
    BROWSE_SEQUENCE_KINDS,
    SEQUENCE_COUNT,
    _collapse_dup_zh,
    _leaks_code_ident,
    _read_json,
    _short_role,
    _validate_selection,
    build_diagram_messages,
    candidate_id,
    default_sequence_selection,
    list_sequence_candidates,
    parse_selection_ids,
)

ACTIVITY_COUNT = SEQUENCE_COUNT

_SWIMLANES = (
    {"id": "user", "label": "用户"},
    {"id": "system", "label": "系统"},
    {"id": "db", "label": "数据库"},
)

_FONT = "Microsoft YaHei, SimSun, serif"
_STROKE = 1.2


def _esc(s: str) -> str:
    return html.escape(str(s or ""), quote=True)


def _f(v: float) -> str:
    return f"{v:.1f}"


def _clean_text(text: str) -> str:
    t = _collapse_dup_zh(str(text or "").strip().rstrip("()（）"))
    if _leaks_code_ident(t):
        return ""
    return t


def _node(
    *,
    nid: str,
    kind: str,
    lane: str,
    text: str = "",
    phase: str = "",
) -> dict[str, Any]:
    return {
        "id": nid,
        "kind": kind,  # start | end | action | decision
        "lane": lane,  # user | system | db
        "text": text,
        "phase": phase,
    }


def _edge(
    *,
    frm: str,
    to: str,
    guard: str = "",
) -> dict[str, Any]:
    return {"from": frm, "to": to, "guard": guard}


def _messages_to_activity(
    messages: list[dict[str, Any]],
    *,
    phases: list[str],
    kind: str = "",
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """序列消息 → 活动节点/边；插入判断菱形，条件只挂在边上。"""
    del phases  # 相位从各 message.phase 读取
    kind = str(kind or "")
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    nseq = 0

    def next_id(prefix: str) -> str:
        nonlocal nseq
        nseq += 1
        return f"{prefix}{nseq}"

    def link(frm: str, to: str, guard: str = "") -> None:
        edges.append(_edge(frm=frm, to=to, guard=guard))

    start_id = next_id("n")
    nodes.append(_node(nid=start_id, kind="start", lane="user", phase=""))
    prev = start_id
    login_user_id: str | None = None
    biz_entry_id: str | None = None
    login_db_seen = False
    biz_db_read_seen = False
    saw_write_db = False
    pending_yes_from: str | None = None

    def emit_action(lane: str, text: str, phase: str) -> str | None:
        nonlocal prev, pending_yes_from, login_user_id, biz_entry_id
        t = _clean_text(text)
        if not t:
            return None
        nid = next_id("n")
        nodes.append(_node(nid=nid, kind="action", lane=lane, text=t, phase=phase))
        if pending_yes_from:
            link(pending_yes_from, nid, guard="是")
            pending_yes_from = None
        else:
            link(prev, nid)
        prev = nid
        if phase == "login" and lane == "user" and login_user_id is None:
            login_user_id = nid
        if phase == "biz" and lane == "user" and biz_entry_id is None:
            biz_entry_id = nid
        return nid

    def emit_decision(question: str, *, no_to: str | None, phase: str) -> None:
        nonlocal prev, pending_yes_from
        nid = next_id("n")
        nodes.append(
            {
                "id": nid,
                "kind": "decision",
                "lane": "system",
                "text": "",
                "phase": phase,
                "decision_of": question,
            }
        )
        link(prev, nid)
        if no_to:
            link(nid, no_to, guard="否")
        pending_yes_from = nid
        prev = nid

    for m in messages:
        if not isinstance(m, dict):
            continue
        frm = str(m.get("from") or "")
        to = str(m.get("to") or "")
        direction = str(m.get("dir") or "")
        phase = str(m.get("phase") or "")
        text = str(m.get("text") or "")

        lane: str | None = None
        out_text = text

        if direction == "self" and frm == "page":
            lane = "user"
        elif frm == "actor" and to == "page" and direction == "request":
            lane = "user"
        elif frm == "page" and to == "controller" and direction == "request":
            lane = "system"
        elif frm == "controller" and to == "db" and direction == "request":
            lane = "db"
        elif frm == "controller" and to == "page" and direction == "response":
            if "成功" in text:
                lane = "system"
                if not text.startswith("返回"):
                    out_text = f"返回{text}" if text else "返回成功"
            else:
                continue
        elif frm == "page" and to == "actor" and direction == "response":
            if phase == "login" and ("成功" in text or "登录" in text):
                lane = "user"
                out_text = "进入首页"
            elif "成功" in text or "展示" in text:
                lane = "system"
                out_text = text if "成功" in text or "展示" in text else "返回结果"
                if "成功" in out_text and not out_text.startswith("返回"):
                    out_text = "返回数据保存成功" if "保存" in text or "数据" in text else f"返回{out_text}"
            else:
                continue
        elif frm == "db":
            continue
        else:
            continue

        nid = emit_action(lane, out_text, phase)
        if not nid:
            continue

        # 登录：查库后判断用户是否存在
        if (
            phase == "login"
            and lane == "db"
            and not login_db_seen
            and login_user_id
        ):
            login_db_seen = True
            emit_decision("用户是否存在", no_to=login_user_id, phase=phase)

        # 写路径读库后才判断「信息是否存在」；纯浏览（收藏/档案列表等）不插回环
        if (
            phase == "biz"
            and lane == "db"
            and not biz_db_read_seen
            and not saw_write_db
            and kind not in BROWSE_SEQUENCE_KINDS
            and ("查询" in (out_text or "") or "获取" in (out_text or ""))
        ):
            biz_db_read_seen = True
            back = biz_entry_id or login_user_id or start_id
            emit_decision("信息是否存在", no_to=back, phase=phase)

        if phase == "biz" and lane == "db" and any(
            x in (out_text or "") for x in ("保存", "添加", "新增", "更新", "删除", "写入")
        ):
            saw_write_db = True

    end_id = next_id("n")
    nodes.append(_node(nid=end_id, kind="end", lane="user", phase=""))
    if pending_yes_from:
        link(pending_yes_from, end_id, guard="是")
    else:
        link(prev, end_id)

    return nodes, edges


def build_activity_diagram(
    case: dict[str, Any],
    schema: dict[str, Any],
    workspace: Path | None,
    *,
    index: int,
) -> dict[str, Any]:
    side = str(case.get("side") or "user")
    actor = _short_role(str(case.get("actor") or ""), side=side)
    name = str(case.get("name") or case.get("label") or "功能").strip()
    kind = str(case.get("kind") or "")
    messages, phases = build_diagram_messages(case, schema, workspace)
    nodes, edges = _messages_to_activity(messages, phases=phases, kind=kind)
    return {
        "id": candidate_id(case),
        "index": index,
        "figure_title": f"{name}活动图",
        "kind": kind,
        "menu_key": str(case.get("menu_key") or ""),
        "side": side,
        "actor_label": actor,
        "swimlanes": [dict(x) for x in _SWIMLANES],
        "nodes": nodes,
        "edges": edges,
        "phases": phases,
    }


def activity_model(
    schema: dict[str, Any],
    workspace: Path | None = None,
    *,
    proposal_text: str = "",
    selection: list[str] | None = None,
    title_fallback: str = "管理系统",
) -> dict[str, Any]:
    from app.bake.schema.testcases import _app_title

    candidates = list_sequence_candidates(schema, proposal_text=proposal_text)
    if selection is None:
        selected = default_sequence_selection(candidates)
    else:
        try:
            selected = _validate_selection(selection, candidates)
        except ValueError as e:
            raise ValueError(str(e).replace("序列图", "活动图")) from e

    by_id = {c["id"]: c for c in candidates}
    diagrams: list[dict[str, Any]] = []
    for i, sid in enumerate(selected):
        diagrams.append(build_activity_diagram(by_id[sid], schema, workspace, index=i))

    title = _app_title(schema, title_fallback)
    return {
        "title": title,
        "figure_title": "系统活动图",
        "candidates": candidates,
        "selected": selected,
        "diagrams": diagrams,
        "source_note": (
            "功能与勾选 id 与系统序列图同源（交付 menus）；"
            "步骤文案取自 bake 包 Controller/页面/交付中文名；"
            "三泳道：用户 / 系统 / 数据库；判断条件写在菱形外侧箭头上。"
        ),
        "rules_zh": [
            "恰好 3 张核心功能活动图，可与序列图勾选同一组交付功能",
            "三泳道：用户（操作）、系统（处理/判断）、数据库（存取）",
            "开始实心点；圆角矩形为动词任务；菱形为判断（框内无字，条件写在菱形外侧；是/否标在出边旁）；结束为实心点外套圆",
            "连线一律直角折线",
            "判断「是/否」标在出边旁，不写进菱形",
        ],
    }


def load_activity_model(
    workspace: Path,
    *,
    proposal_text: str = "",
    selection: list[str] | None = None,
    title_fallback: str = "管理系统",
) -> dict[str, Any] | None:
    schema = _read_json(workspace / "domain.schema.json")
    if not schema:
        return None
    spec = _read_json(workspace / "spec.json") or {}
    fb = str(spec.get("title") or "").strip() or title_fallback
    return activity_model(
        schema,
        workspace,
        proposal_text=proposal_text,
        selection=selection,
        title_fallback=fb,
    )


# —— SVG ——
_PAD_X = 28.0
_PAD_Y = 24.0
_LANE_W = 200.0
_HEADER_H = 36.0
_NODE_H = 36.0
_NODE_W = 132.0
_ROW_GAP = 28.0
_DECISION_S = 28.0
_START_R = 7.0
_END_R = 7.0
_END_OUTER = 11.0


def _lane_center_x(lane: str) -> float:
    idx = {"user": 0, "system": 1, "db": 2}.get(lane, 0)
    return _PAD_X + idx * _LANE_W + _LANE_W / 2


def render_activity_svg(diagram: dict[str, Any]) -> str:
    nodes = list(diagram.get("nodes") or [])
    edges = list(diagram.get("edges") or [])
    title = str(diagram.get("figure_title") or "活动图")

    # 按出现顺序排 y（拓扑：用节点列表顺序）
    pos: dict[str, tuple[float, float]] = {}
    y = _PAD_Y + _HEADER_H + 28.0
    for n in nodes:
        nid = str(n["id"])
        lane = str(n.get("lane") or "user")
        cx = _lane_center_x(lane)
        kind = str(n.get("kind") or "action")
        if kind == "decision":
            y += 6
        pos[nid] = (cx, y)
        if kind in ("start", "end"):
            y += _ROW_GAP + 18
        elif kind == "decision":
            y += _ROW_GAP + _DECISION_S + 8
        else:
            y += _ROW_GAP + _NODE_H

    width = _PAD_X * 2 + _LANE_W * 3
    height = y + _PAD_Y + 20

    parts: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{_f(width)}" height="{_f(height)}" '
        f'viewBox="0 0 {_f(width)} {_f(height)}">',
        "<defs>",
        '<marker id="act-arrow" markerWidth="10" markerHeight="8" refX="9" refY="4" orient="auto">',
        '<path d="M0,0 L10,4 L0,8" fill="none" stroke="#000" stroke-width="1.2"/>',
        "</marker>",
        "</defs>",
        f'<rect x="0" y="0" width="{_f(width)}" height="{_f(height)}" fill="#fff"/>',
        f'<text x="{_f(width / 2)}" y="{_f(_PAD_Y + 4)}" text-anchor="middle" '
        f'font-family="{_FONT}" font-size="14" fill="#000">{_esc(title)}</text>',
    ]

    # 泳道框
    lane_top = _PAD_Y + 14
    lane_h = height - lane_top - _PAD_Y / 2
    for i, lane in enumerate(_SWIMLANES):
        x = _PAD_X + i * _LANE_W
        parts.append(
            f'<rect x="{_f(x)}" y="{_f(lane_top)}" width="{_f(_LANE_W)}" height="{_f(lane_h)}" '
            f'fill="none" stroke="#000" stroke-width="{_STROKE}"/>'
        )
        parts.append(
            f'<text x="{_f(x + _LANE_W / 2)}" y="{_f(lane_top + 22)}" text-anchor="middle" '
            f'font-family="{_FONT}" font-size="13" fill="#000">{_esc(lane["label"])}</text>'
        )
        parts.append(
            f'<line x1="{_f(x)}" y1="{_f(lane_top + _HEADER_H)}" x2="{_f(x + _LANE_W)}" '
            f'y2="{_f(lane_top + _HEADER_H)}" stroke="#000" stroke-width="{_STROKE}"/>'
        )

    by_id = {str(n["id"]): n for n in nodes}

    def node_anchor(nid: str, *, end: str = "center") -> tuple[float, float]:
        cx, cy = pos[nid]
        n = by_id[nid]
        kind = str(n.get("kind") or "action")
        if kind == "start":
            return (cx, cy + (_START_R if end == "bottom" else (-_START_R if end == "top" else 0)))
        if kind == "end":
            return (cx, cy + (_END_OUTER if end == "bottom" else (-_END_OUTER if end == "top" else 0)))
        if kind == "decision":
            half = _DECISION_S / 2
            if end == "bottom":
                return (cx, cy + half)
            if end == "top":
                return (cx, cy - half)
            if end == "left":
                return (cx - half, cy)
            if end == "right":
                return (cx + half, cy)
            return (cx, cy)
        # action
        half_h = _NODE_H / 2
        half_w = _NODE_W / 2
        if end == "bottom":
            return (cx, cy + half_h)
        if end == "top":
            return (cx, cy - half_h)
        if end == "left":
            return (cx - half_w, cy)
        if end == "right":
            return (cx + half_w, cy)
        return (cx, cy)

    # 边（先画，节点盖上）；一律直角折线，禁止贝塞尔弧线
    for e in edges:
        frm = str(e.get("from") or "")
        to = str(e.get("to") or "")
        guard = str(e.get("guard") or "").strip()
        if frm not in pos or to not in pos:
            continue
        fx, fy = pos[frm]
        tx, ty = pos[to]
        to_node = by_id.get(to) or {}
        # 进入菱形的边上写判断条件（外侧）；是/否仍在出边
        enter_q = ""
        if str(to_node.get("kind") or "") == "decision" and not guard:
            enter_q = _clean_text(str(to_node.get("decision_of") or ""))
        is_back = ty < fy - 8
        if is_back:
            # 否回边：左出 → 上折 → 右入（直角折线）
            x1, y1 = node_anchor(frm, end="left")
            x2, y2 = node_anchor(to, end="left")
            mid_x = min(x1, x2) - 40
            parts.append(
                f'<polyline points="{_f(x1)},{_f(y1)} {_f(mid_x)},{_f(y1)} {_f(mid_x)},{_f(y2)} {_f(x2)},{_f(y2)}" '
                f'fill="none" stroke="#000" stroke-width="{_STROKE}" marker-end="url(#act-arrow)"/>'
            )
            if guard:
                parts.append(
                    f'<text x="{_f(mid_x + 6)}" y="{_f((y1 + y2) / 2 + 4)}" '
                    f'font-family="{_FONT}" font-size="12" fill="#000">{_esc(guard)}</text>'
                )
        else:
            x1, y1 = node_anchor(frm, end="bottom")
            x2, y2 = node_anchor(to, end="top")
            if abs(fx - tx) > 8:
                mid_y = (y1 + y2) / 2
                parts.append(
                    f'<polyline points="{_f(x1)},{_f(y1)} {_f(x1)},{_f(mid_y)} {_f(x2)},{_f(mid_y)} {_f(x2)},{_f(y2)}" '
                    f'fill="none" stroke="#000" stroke-width="{_STROKE}" marker-end="url(#act-arrow)"/>'
                )
                label_x, label_y = (x1 + x2) / 2, mid_y - 4
            else:
                # 同泳道竖直也走折线点列，保持画法统一
                parts.append(
                    f'<polyline points="{_f(x1)},{_f(y1)} {_f(x2)},{_f(y2)}" '
                    f'fill="none" stroke="#000" stroke-width="{_STROKE}" marker-end="url(#act-arrow)"/>'
                )
                label_x, label_y = x1 + 10, (y1 + y2) / 2
            if guard:
                parts.append(
                    f'<text x="{_f(label_x)}" y="{_f(label_y)}" '
                    f'font-family="{_FONT}" font-size="12" fill="#000">{_esc(guard)}</text>'
                )
            elif enter_q:
                # 判断条件标在进入菱形的箭头旁（框外）
                parts.append(
                    f'<text x="{_f(label_x)}" y="{_f(label_y)}" '
                    f'font-family="{_FONT}" font-size="12" fill="#000">{_esc(enter_q)}</text>'
                )

    # 节点
    for n in nodes:
        nid = str(n["id"])
        cx, cy = pos[nid]
        kind = str(n.get("kind") or "action")
        text = str(n.get("text") or "")
        if kind == "start":
            parts.append(
                f'<circle cx="{_f(cx)}" cy="{_f(cy)}" r="{_f(_START_R)}" fill="#000"/>'
            )
        elif kind == "end":
            parts.append(
                f'<circle cx="{_f(cx)}" cy="{_f(cy)}" r="{_f(_END_OUTER)}" fill="none" '
                f'stroke="#000" stroke-width="{_STROKE}"/>'
            )
            parts.append(
                f'<circle cx="{_f(cx)}" cy="{_f(cy)}" r="{_f(_END_R)}" fill="#000"/>'
            )
        elif kind == "decision":
            half = _DECISION_S / 2
            parts.append(
                f'<path d="M {_f(cx)} {_f(cy - half)} L {_f(cx + half)} {_f(cy)} '
                f'L {_f(cx)} {_f(cy + half)} L {_f(cx - half)} {_f(cy)} Z" '
                f'fill="#fff" stroke="#000" stroke-width="{_STROKE}"/>'
            )
            # 框内不写字；条件已标在入边旁
        else:
            x = cx - _NODE_W / 2
            y0 = cy - _NODE_H / 2
            parts.append(
                f'<rect x="{_f(x)}" y="{_f(y0)}" width="{_f(_NODE_W)}" height="{_f(_NODE_H)}" '
                f'rx="10" ry="10" fill="#fff" stroke="#000" stroke-width="{_STROKE}"/>'
            )
            # 长文案缩小字号
            fs = 12 if len(text) <= 10 else 11 if len(text) <= 14 else 10
            parts.append(
                f'<text x="{_f(cx)}" y="{_f(cy + 4)}" text-anchor="middle" '
                f'font-family="{_FONT}" font-size="{fs}" fill="#000">{_esc(text)}</text>'
            )

    parts.append("</svg>")
    return "\n".join(parts)


# 供 API 复用
__all__ = [
    "ACTIVITY_COUNT",
    "activity_model",
    "build_activity_diagram",
    "load_activity_model",
    "parse_selection_ids",
    "render_activity_svg",
]
