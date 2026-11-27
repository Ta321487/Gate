"""论文「系统活动图」：固定 3 张，三泳道（用户 / 控制器 / 数据库）。

真源与候选与序列图同源：domain.schema.json + bake 包 Controller/Vue。
流程操作与同 ids 序列图一致（复用 build_diagram_messages），仅改画法。
禁止：kind 中文句库、示例「自习室」题材、菱形框内写判断条件、序列图生命线/激活条。
"""

from __future__ import annotations

import html
import re
from pathlib import Path
from typing import Any, Iterable

from app.bake.schema.diagram_style import FONT_CN
from app.bake.schema.diagram_svg_util import fmt1, svg_esc
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

_esc = svg_esc
_f = fmt1

ACTIVITY_COUNT = SEQUENCE_COUNT

_SWIMLANES = (
    {"id": "user", "label": "用户"},
    {"id": "system", "label": "控制器"},
    {"id": "db", "label": "数据库"},
)

_FONT = FONT_CN
_STROKE = 1.2




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
        # 同一句回执在相邻两次「返回」上会重复（控制器→页面→角色），样例只画一步：
        # 与上一个动作同文案同泳道则合并，边不再新增。
        if not pending_yes_from and prev:
            last = nodes[-1] if nodes else {}
            if (
                str(last.get("kind") or "") == "action"
                and _clean_text(str(last.get("text") or "")) == t
                and str(last.get("lane") or "") == lane
            ):
                return str(last["id"])
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
    try:
        from app.services.diagram_titles import resolve_figure_title

        fig_title = resolve_figure_title(
            "activity",
            domain=str(schema.get("domain") or ""),
            name=name,
        )
    except Exception:  # noqa: BLE001
        fig_title = f"{name}活动图"
    return {
        "id": candidate_id(case),
        "index": index,
        "figure_title": fig_title,
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
            "三泳道：用户 / 控制器 / 数据库；判断条件写在菱形外侧箭头上。"
        ),
        "rules_zh": [
            "恰好 3 张核心功能活动图，可与序列图勾选同一组交付功能",
            "三泳道：用户（操作）、控制器（处理/判断）、数据库（存取），与序列图四槽位同名",
            "开始实心点；圆角矩形为动词任务；菱形为判断（框内无字，条件写在菱形外侧；是/否标在出边旁）；结束为实心点外套圆",
            "连线一律直角折线",
            "判断「是/否」标在出边旁，不写进菱形",
            "图内不画标题（图注写 Word，与 E-R/类图/模块图同口径）",
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
    sel = selection
    if sel is None:
        try:
            from app.bake.overrides import resolve_override_selection

            # 活动未单独勾选时跟序列勾选（与前端 openActivities 同口径）
            sel = resolve_override_selection(workspace, "activity")
            if sel is None:
                sel = resolve_override_selection(workspace, "sequence")
        except Exception:  # noqa: BLE001
            sel = None
    try:
        model = activity_model(
            schema,
            workspace,
            proposal_text=proposal_text,
            selection=sel,
            title_fallback=fb,
        )
    except ValueError:
        model = activity_model(
            schema,
            workspace,
            proposal_text=proposal_text,
            selection=None,
            title_fallback=fb,
        )
    try:
        from app.bake.overrides import (
            apply_activity_label_overrides,
            override_labels_map,
        )

        model = apply_activity_label_overrides(
            model, override_labels_map(workspace, "activity")
        )
    except Exception:  # noqa: BLE001
        pass
    return model


# —— SVG ——
_PAD_X = 28.0
_PAD_Y = 24.0
_LANE_MIN_W = 200.0      # 泳道最小宽；长文案会把三条泳道一起加宽
_HEADER_H = 36.0
_NODE_H = 36.0
_NODE_MIN_W = 132.0      # 任务框最小宽；按文案自适应
_NODE_SIDE_PAD = 13.0    # 任务框文字左右内边距
_LANE_SIDE_PAD = 24.0    # 任务框到泳道分隔线的最小间距（留给 是/否 标签）
_ACTION_FS = 11.0        # 任务框统一字号（与参考样例一致：图内字号偏小）
_ROW_GAP = 28.0
_DEC_W = 52.0     # 判定菱形横向跨度（参考样例：扁菱形，宽约为高的两倍）
_DEC_H = 26.0     # 判定菱形纵向跨度
_DECISION_S = _DEC_H  # 兼容按「最小尺寸」取值的旧引用
_START_R = 7.0
_END_R = 7.0
_END_OUTER = 11.0

# 兼容旧引用（按最小尺寸）
_LANE_W = _LANE_MIN_W
_NODE_W = _NODE_MIN_W


def _action_width(text: str) -> float:
    """任务框宽度：按文案测算，不压字也不留大片空白。"""
    return max(_NODE_MIN_W, _text_width(str(text or ""), _ACTION_FS) + 2 * _NODE_SIDE_PAD)


def _lane_center_x(lane: str, lane_w: float = _LANE_MIN_W) -> float:
    idx = {"user": 0, "system": 1, "db": 2}.get(lane, 0)
    return _PAD_X + idx * lane_w + lane_w / 2


def _lane_index(x: float, lane_w: float = _LANE_MIN_W) -> int:
    idx = int((x - _PAD_X) // lane_w)
    return max(0, min(len(_SWIMLANES) - 1, idx))


def _lane_span(x: float, lane_w: float = _LANE_MIN_W) -> tuple[float, float]:
    """x 所在泳道的左右边界。"""
    idx = _lane_index(x, lane_w)
    left = _PAD_X + idx * lane_w
    return left, left + lane_w


# —— 标签几何（是/否 + 判断条件）：贴菱形、避线、不出泳道 ——
_LABEL_FS = 11.0
_LABEL_GAP = 7.0   # 标签到连线的法向净距
_LABEL_LEAD = 14.0  # 标签到出边起点的纵向距离


def _text_width(text: str, fs: float = _LABEL_FS) -> float:
    """粗估文本宽度（全角 1fs / 半角 0.56fs），不依赖字体度量。"""
    width = 0.0
    for ch in str(text or ""):
        width += fs if ord(ch) > 0x2E7F else fs * 0.56
    return width


def _clamp_into_lane(
    x: float,
    y: float,
    anchor: str,
    width: float,
    fs: float,
    edge_x: float,
    lane_w: float = _LANE_MIN_W,
) -> tuple[float, float, str]:
    """把标签框夹在所属泳道内（离分隔线/外框 ≥ _LABEL_GAP）。"""
    left, right = _lane_span(edge_x, lane_w)
    left, right = left + _LABEL_GAP, right - _LABEL_GAP
    if anchor == "end":
        x0, x1 = x - width, x
    elif anchor == "middle":
        x0, x1 = x - width / 2, x + width / 2
    else:
        x0, x1 = x, x + width
    if x0 < left:
        x += left - x0
    elif x1 > right:
        x -= x1 - right
    return x, y, anchor


def _guard_label(
    vertex: tuple[float, float],
    direction: tuple[float, float],
    text: str,
    lane_w: float = _LANE_MIN_W,
) -> tuple[float, float, str]:
    """守卫标签（是/否）贴出边起点：竖边放右侧、横边放上方；放不下自动换侧。"""
    px, py = vertex
    dx, dy = direction
    fs = _LABEL_FS
    width = _text_width(text, fs)
    left, right = _lane_span(px, lane_w)
    usable_l, usable_r = left + _LABEL_GAP, right - _LABEL_GAP

    if abs(dy) >= abs(dx):
        y = py + (1 if dy > 0 else -1) * _LABEL_LEAD + fs * 0.36
        x, anchor = px + _LABEL_GAP, "start"
        if x + width > usable_r:
            x, anchor = px - _LABEL_GAP, "end"
    else:
        y = py - _LABEL_GAP - fs * 0.28
        if dx >= 0:
            x, anchor = px + _LABEL_LEAD / 2, "start"
            if x + width > usable_r:
                x, anchor = px - _LABEL_LEAD / 2, "end"
        else:
            x, anchor = px - _LABEL_LEAD / 2, "end"
            if x - width < usable_l:
                x, anchor = px + _LABEL_LEAD / 2, "start"
    return _clamp_into_lane(x, y, anchor, width, fs, px, lane_w)


def _box_hits_segments(
    box: tuple[float, float, float, float],
    segments: Iterable[tuple[float, float, float, float]],
    pad: float = 2.0,
) -> bool:
    x0, y0, x1, y1 = box
    x0, y0, x1, y1 = x0 - pad, y0 - pad, x1 + pad, y1 + pad
    for sx1, sy1, sx2, sy2 in segments:
        lo_x, hi_x = min(sx1, sx2), max(sx1, sx2)
        lo_y, hi_y = min(sy1, sy2), max(sy1, sy2)
        if lo_x < x1 and hi_x > x0 and lo_y < y1 and hi_y > y0:
            return True
    return False


def _decision_question_label(
    cx: float,
    cy: float,
    text: str,
    segments: Iterable[tuple[float, float, float, float]] = (),
    lane_w: float = _LANE_MIN_W,
) -> tuple[float, float, str]:
    """判断条件写在菱形入射处：优选上角右侧（紧随入射竖线），被折线占位就退到右侧。"""
    fs = _LABEL_FS
    width = _text_width(text, fs)
    half_w = _DEC_W / 2
    half_h = _DEC_H / 2
    asc, desc = fs * 0.96, fs * 0.22
    left, right = _lane_span(cx, lane_w)
    usable_r = right - _LABEL_GAP

    # 优选：上角外侧（与参考样例一致：条件贴着入射竖线、压在菱形上方）
    x = min(cx + 12.0, usable_r - width)
    y = cy - half_h - 5.0
    if not _box_hits_segments((x, y - asc, x + width, y + desc), segments):
        return _clamp_into_lane(x, y, "start", width, fs, cx, lane_w)

    # 次选：菱形右侧
    x = max(min(cx + half_w + 8.0, usable_r - width), cx + half_w + 2.0)
    y = cy + 6.0
    if not _box_hits_segments((x, y - asc, x + width, y + desc), segments):
        return _clamp_into_lane(x, y, "start", width, fs, cx, lane_w)

    # 保底：菱形下角右侧（跨出右顶点，避开两条横出边）
    return _clamp_into_lane(x, cy + half_h + fs + 2.0, "start", width, fs, cx, lane_w)


def _label_text_svg(x: float, y: float, anchor: str, text: str) -> str:
    attrs = "" if anchor == "start" else f' text-anchor="{anchor}"'
    return (
        f'<text x="{_f(x)}" y="{_f(y)}"{attrs} '
        f'font-family="{_FONT}" font-size="{_f(_LABEL_FS)}" fill="#000">{_esc(text)}</text>'
    )


def render_activity_svg(diagram: dict[str, Any]) -> str:
    nodes = list(diagram.get("nodes") or [])
    edges = list(diagram.get("edges") or [])

    # 每节点实测宽度 → 三条泳道统一加宽（长文案不压字、不跨分隔线）
    widths: dict[str, float] = {}
    for n in nodes:
        nid = str(n["id"])
        kind = str(n.get("kind") or "action")
        if kind == "decision":
            widths[nid] = _DEC_W
        elif kind == "action":
            widths[nid] = _action_width(str(n.get("text") or ""))
        else:
            widths[nid] = 2 * _END_OUTER
    lane_w = max(_LANE_MIN_W, max(widths.values(), default=0.0) + 2 * _LANE_SIDE_PAD)

    # 按出现顺序排 y（拓扑：用节点列表顺序）
    pos: dict[str, tuple[float, float]] = {}
    y = _PAD_Y + _HEADER_H + 30.0
    for n in nodes:
        nid = str(n["id"])
        lane = str(n.get("lane") or "user")
        cx = _lane_center_x(lane, lane_w)
        kind = str(n.get("kind") or "action")
        if kind == "decision":
            y += 6
        pos[nid] = (cx, y)
        if kind in ("start", "end"):
            y += _ROW_GAP + 18
        elif kind == "decision":
            y += _ROW_GAP + _DEC_H + 8
        else:
            y += _ROW_GAP + _NODE_H

    width = _PAD_X * 2 + lane_w * 3
    height = y + _PAD_Y + 20

    parts: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{_f(width)}" height="{_f(height)}" '
        f'viewBox="0 0 {_f(width)} {_f(height)}">',
        "<defs>",
        '<marker id="act-arrow" markerWidth="11" markerHeight="9" refX="10" refY="4.5" orient="auto" markerUnits="strokeWidth">',
        '<path d="M0,0 L10,4.5 L0,9 Z" fill="#000" stroke="#000" stroke-width="0.8"/>',
        "</marker>",
        "</defs>",
        f'<rect x="0" y="0" width="{_f(width)}" height="{_f(height)}" fill="#fff"/>',
    ]

    # 泳道框（图内不画标题，图注写 Word —— 与 E-R/类图/模块图同一口径）
    lane_top = _PAD_Y
    lane_h = height - lane_top - _PAD_Y / 2
    for i, lane in enumerate(_SWIMLANES):
        x = _PAD_X + i * lane_w
        parts.append(
            f'<rect x="{_f(x)}" y="{_f(lane_top)}" width="{_f(lane_w)}" height="{_f(lane_h)}" '
            f'fill="none" stroke="#000" stroke-width="{_STROKE}"/>'
        )
        parts.append(
            f'<text x="{_f(x + lane_w / 2)}" y="{_f(lane_top + 23)}" text-anchor="middle" '
            f'font-family="{_FONT}" font-size="12" fill="#000">{_esc(lane["label"])}</text>'
        )
        parts.append(
            f'<line x1="{_f(x)}" y1="{_f(lane_top + _HEADER_H)}" x2="{_f(x + lane_w)}" '
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
            half_w = _DEC_W / 2
            half_h = _DEC_H / 2
            if end == "bottom":
                return (cx, cy + half_h)
            if end == "top":
                return (cx, cy - half_h)
            if end == "left":
                return (cx - half_w, cy)
            if end == "right":
                return (cx + half_w, cy)
            return (cx, cy)
        # action
        half_h = _NODE_H / 2
        half_w = widths.get(nid, _NODE_MIN_W) / 2
        if end == "bottom":
            return (cx, cy + half_h)
        if end == "top":
            return (cx, cy - half_h)
        if end == "left":
            return (cx - half_w, cy)
        if end == "right":
            return (cx + half_w, cy)
        return (cx, cy)

    # 边：先算路径，再统一写标签（标签要能避让已经画出的线）
    routed: list[dict[str, Any]] = []
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
            # 否回边：左出 → 上折 → 右入（直角折线；折点留在泳道内，禁止压外框）
            x1, y1 = node_anchor(frm, end="left")
            x2, y2 = node_anchor(to, end="left")
            # 折点贴目标节点左侧：目标泳道内留 10px 边距，且不穿过目标节点/其它节点
            tgt_left, _tgt_right = _lane_span(x2, lane_w)
            mid_x = max(tgt_left + 10.0, x2 - 24.0)
            mid_x = min(mid_x, x1 - 20.0)
            pts = [(x1, y1), (mid_x, y1), (mid_x, y2), (x2, y2)]
            label_at: tuple[tuple[float, float], tuple[float, float]] = (
                (x1, y1),
                (-1.0, 0.0),
            )
        else:
            x1, y1 = node_anchor(frm, end="bottom")
            x2, y2 = node_anchor(to, end="top")
            if abs(fx - tx) > 8:
                mid_y = (y1 + y2) / 2
                pts = [(x1, y1), (x1, mid_y), (x2, mid_y), (x2, y2)]
            else:
                # 同泳道竖直也走折线点列，保持画法统一
                pts = [(x1, y1), (x2, y2)]
            label_at = ((x1, y1), (0.0, 1.0))
        routed.append(
            {"pts": pts, "at": label_at, "guard": guard, "q": enter_q, "qc": (tx, ty)}
        )

    segments: list[tuple[float, float, float, float]] = []
    for r in routed:
        pts = r["pts"]
        parts.append(
            f'<polyline points="{" ".join(f"{_f(px)},{_f(py)}" for px, py in pts)}" '
            f'fill="none" stroke="#000" stroke-width="{_STROKE}" marker-end="url(#act-arrow)"/>'
        )
        segments.extend((a[0], a[1], b[0], b[1]) for a, b in zip(pts, pts[1:]))

    for r in routed:
        if r["guard"]:
            lx, ly, lanchor = _guard_label(
                r["at"][0], r["at"][1], r["guard"], lane_w
            )
            parts.append(_label_text_svg(lx, ly, lanchor, r["guard"]))
        elif r["q"]:
            qx, qy, qanchor = _decision_question_label(
                r["qc"][0], r["qc"][1], r["q"], segments, lane_w
            )
            parts.append(_label_text_svg(qx, qy, qanchor, r["q"]))

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
            half_w = _DEC_W / 2
            half_h = _DEC_H / 2
            parts.append(
                f'<path d="M {_f(cx)} {_f(cy - half_h)} L {_f(cx + half_w)} {_f(cy)} '
                f'L {_f(cx)} {_f(cy + half_h)} L {_f(cx - half_w)} {_f(cy)} Z" '
                f'fill="#fff" stroke="#000" stroke-width="{_STROKE}"/>'
            )
            # 框内不写字；条件已标在入边旁
        else:
            box_w = widths[nid]
            x = cx - box_w / 2
            y0 = cy - _NODE_H / 2
            parts.append(
                f'<rect x="{_f(x)}" y="{_f(y0)}" width="{_f(box_w)}" height="{_f(_NODE_H)}" '
                f'rx="10" ry="10" fill="#fff" stroke="#000" stroke-width="{_STROKE}"/>'
            )
            # 字号统一（框宽已按字量撑开，不再靠缩字硬塞）
            parts.append(
                f'<text x="{_f(cx)}" y="{_f(cy + 4)}" text-anchor="middle" '
                f'font-family="{_FONT}" font-size="{_f(_ACTION_FS)}" fill="#000">{_esc(text)}</text>'
            )

    parts.append("</svg>")
    return "\n".join(parts)


_TEXT_RE = re.compile(
    r'<text x="([-\d.]+)" y="([-\d.]+)"'
    r'(?: text-anchor="([a-z]+)")?'
    r' font-family="[^"]*" font-size="([\d.]+)" fill="#000">([^<]*)</text>'
)
_POLY_RE = re.compile(r'<polyline points="([^"]+)"')
_DECISION_RE = re.compile(r'<path d="M ([-\d.]+) ([-\d.]+) L')
_NODE_RE = re.compile(
    r'<rect x="([-\d.]+)" y="([-\d.]+)" width="([-\d.]+)" height="([-\d.]+)" rx="10"'
)
# 泳道框：fill="none" 且描边 1.2 的矩形（背景是 fill="#fff"，节点带 rx，不会误抓）
_LANE_RE = re.compile(
    r'<rect x="([-\d.]+)" y="([-\d.]+)" width="([-\d.]+)" height="([-\d.]+)" '
    r'fill="none" stroke="#000" stroke-width="1\.2"'
)


def _lane_boxes(svg: str) -> list[tuple[float, float, float]]:
    """从 SVG 反推泳道框（左边界, 上沿, 宽），不信模块常量——泳道宽是自适应的。"""
    boxes = sorted(
        ((float(bx), float(by), float(bw)) for bx, by, bw, _bh in _LANE_RE.findall(svg)),
        key=lambda b: (b[1], b[0]),
    )
    if not boxes:
        return []
    top = boxes[0][1]
    return [b for b in boxes if abs(b[1] - top) < 2.0]


def _segments(svg: str) -> list[tuple[float, float, float, float]]:
    segs: list[tuple[float, float, float, float]] = []
    for raw in _POLY_RE.findall(svg):
        pts = []
        for pair in raw.split():
            if "," not in pair:
                continue
            a, b = pair.split(",", 1)
            pts.append((float(a), float(b)))
        for i in range(len(pts) - 1):
            x1, y1 = pts[i]
            x2, y2 = pts[i + 1]
            segs.append((x1, y1, x2, y2))
    return segs


def _decisions(svg: str) -> list[tuple[float, float]]:
    # 菱形 d 以顶点起笔（M cx cy-half_h L ...），中心 = (cx, cy)
    return [(float(mx), float(my) + _DEC_H / 2) for mx, my in _DECISION_RE.findall(svg)]


def _node_boxes(svg: str) -> list[tuple[float, float, float, float]]:
    boxes = []
    for mx, my, mw, mh in _NODE_RE.findall(svg):
        x0, y0 = float(mx), float(my)
        boxes.append((x0, y0, x0 + float(mw), y0 + float(mh)))
    return boxes


def audit_activity_edges(svg: str) -> list[str]:
    """连线门禁：折线不得穿进活动节点框（只允许贴边进出）。"""
    findings: list[str] = []
    boxes = _node_boxes(svg)
    for sx1, sy1, sx2, sy2 in _segments(svg):
        lo_x, hi_x = min(sx1, sx2), max(sx1, sx2)
        lo_y, hi_y = min(sy1, sy2), max(sy1, sy2)
        for x0, y0, x1, y1 in boxes:
            if (
                lo_x < x1 - 1.0
                and hi_x > x0 + 1.0
                and lo_y < y1 - 1.0
                and hi_y > y0 + 1.0
            ):
                findings.append(
                    f"连线 {sx1:.0f},{sy1:.0f}→{sx2:.0f},{sy2:.0f} 穿进节点框 "
                    f"({x0:.0f},{y0:.0f})-({x1:.0f},{y1:.0f})"
                )
                break
    return findings


def audit_activity_labels(svg: str) -> list[str]:
    """标签几何门禁：不出泳道、不压泳道分隔线、不压连线、是/否贴菱形。"""
    findings: list[str] = []
    segs = _segments(svg)
    decisions = _decisions(svg)
    lanes = _lane_boxes(svg)
    if len(lanes) < len(_SWIMLANES):
        return [f"活动图识别到 {len(lanes)} 条泳道框（应 {len(_SWIMLANES)} 条），无法校验标签几何"]
    lane_top = lanes[0][1]
    header_y = lane_top + _HEADER_H  # 泳道表头下沿；其上的泳道名不查
    frame_l = lanes[0][0]
    frame_r = lanes[-1][0] + lanes[-1][2]
    dividers = [b[0] for b in lanes[1:]]

    for mx, my, anchor, fs_raw, raw in _TEXT_RE.findall(svg):
        text = html.unescape(raw)
        x, y, fs = float(mx), float(my), float(fs_raw)
        if y <= header_y + 6.0:
            continue
        width = _text_width(text, fs)
        anchor = anchor or "start"
        if anchor == "end":
            x0, x1 = x - width, x
        elif anchor == "middle":
            x0, x1 = x - width / 2, x + width / 2
        else:
            x0, x1 = x, x + width
        y0, y1 = y - fs * 0.86, y + fs * 0.22

        if x0 < frame_l - 0.5 or x1 > frame_r + 0.5:
            findings.append(f"标签「{text}」越出泳道框（x {x0:.1f}~{x1:.1f}）")
        for dxv in dividers:
            if x0 < dxv < x1:
                findings.append(f"标签「{text}」压住泳道分隔线 x={dxv:.0f}")
        for sx1, sy1, sx2, sy2 in segs:
            if (
                min(sx1, sx2) - 2.5 < x1
                and max(sx1, sx2) + 2.5 > x0
                and min(sy1, sy2) - 2.5 < y1
                and max(sy1, sy2) + 2.5 > y0
            ):
                findings.append(f"标签「{text}」压线（线段 {sx1:.0f},{sy1:.0f}→{sx2:.0f},{sy2:.0f}）")
                break
        if text in ("是", "否"):
            if not decisions:
                findings.append(f"守卫「{text}」找不到所属菱形")
            else:
                near = min(
                    ((x - dxc) ** 2 + (y - dyc) ** 2) ** 0.5 for dxc, dyc in decisions
                )
                if near > 48.0:
                    findings.append(f"守卫「{text}」离最近菱形 {near:.0f}px（应 ≤48）")
    return findings


def audit_activity_nodes(svg: str) -> list[str]:
    """节点门禁：任务框（含自适应加宽后）不得跨泳道分隔线。"""
    findings: list[str] = []
    lanes = _lane_boxes(svg)
    if len(lanes) < len(_SWIMLANES):
        return [f"活动图识别到 {len(lanes)} 条泳道框（应 {len(_SWIMLANES)} 条）"]
    for x0, y0, x1, y1 in _node_boxes(svg):
        cx = (x0 + x1) / 2
        hit = [b for b in lanes if b[0] <= cx <= b[0] + b[2]]
        if not hit:
            findings.append(f"节点框 ({x0:.0f},{y0:.0f})-({x1:.0f},{y1:.0f}) 不在任何泳道内")
            continue
        lx, _ly, lw = hit[0]
        if x0 < lx - 0.5 or x1 > lx + lw + 0.5:
            findings.append(
                f"节点框 ({x0:.0f},{y0:.0f})-({x1:.0f},{y1:.0f}) 跨出泳道 "
                f"({lx:.0f}~{lx + lw:.0f})"
            )
    return findings


# 供 API 复用
__all__ = [
    "ACTIVITY_COUNT",
    "activity_model",
    "audit_activity_edges",
    "audit_activity_labels",
    "audit_activity_nodes",
    "build_activity_diagram",
    "load_activity_model",
    "parse_selection_ids",
    "render_activity_svg",
]
