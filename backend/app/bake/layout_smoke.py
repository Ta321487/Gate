"""起包前 UI 布局闸 · D3 冒烟管道 + D4 全表视觉覆盖率。

真源：docs/ui-layout-prebake-gate.md §3.3 / §4 D3–D4。
不 bake 学生整题；读 baseline + 工厂夹具/API mock；不为消红改学生页。
"""

from __future__ import annotations

import json
import os
import re
import socket
import subprocess
import time
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.bake.layout_inventory import LayoutRow, generate_layout_inventory

# D3 试点行：/login + AuthShell；另钉 /profile×member 换头像几何
PILOT_PAGE_ROW_ID = "page:auth:/login"
PILOT_COMPONENT_ROW_ID = "component:components/AuthShell.vue"
PILOT_PROFILE_ROW_ID = "page:user:/profile"
PILOT_ROW_IDS: frozenset[str] = frozenset(
    {PILOT_PAGE_ROW_ID, PILOT_COMPONENT_ROW_ID, PILOT_PROFILE_ROW_ID}
)

# 可点下限（px）
_MIN_HIT_W = 28.0
_MIN_HIT_H = 28.0
_IOU_MAX = 0.28
_CONTAIN_SLACK = 2.0
# 绝对定位可点控件到同槽文档流内容的最大边距（px）；再大 = 悬空/掉条底
_ABS_CTRL_NEAR_FLOW_MAX = 36.0

# 资料页账户脸探针（accountFace 由 domainGroup+壳/货架皮推导，不进台账 surfaces）
_PROFILE_FACE_PROBES: tuple[tuple[str, dict[str, str]], ...] = (
    (
        "member",
        {
            "domainGroup": "trade",
            "shellNavStyle": "storefront",
            "tradeSurfaceStyle": "shelfgrid",
        },
    ),
    (
        "stall",
        {
            "domainGroup": "trade",
            "shellNavStyle": "marketplace",
            "tradeSurfaceStyle": "shelfgrid",
        },
    ),
    (
        "showcard",
        {
            "domainGroup": "trade",
            "shellNavStyle": "storefront",
            "tradeSurfaceStyle": "showtime",
        },
    ),
    ("reader", {"domainGroup": "borrow"}),
    ("plain", {"domainGroup": "fallback"}),
)

# surface 标签 axis:id → APP_DELIVERED 字段
_SURFACE_TO_DELIVERED: dict[str, str] = {
    "portalHome": "portalHomeStyle",
    "content": "contentSurfaceStyle",
    "trade": "tradeSurfaceStyle",
    "reserve": "reserveSurfaceStyle",
    "borrow": "borrowSurfaceStyle",
    "apply": "applySurfaceStyle",
    "interact": "interactSurfaceStyle",
    "follow": "followSurfaceStyle",
    "repair": "repairSurfaceStyle",
    "approve": "approveSurfaceStyle",
    "cardVoice": "cardVoice",
}

_SHELL_REP_PATH: dict[str, str] = {
    "layouts/AdminLayout.vue": "/admin",
    "layouts/PortalLayout.vue": "/home",
    "layouts/WorkLayout.vue": "/staff",
}

_PARAM_PATH_RE = re.compile(r":[^/]+")


@dataclass(frozen=True)
class Box:
    x: float
    y: float
    w: float
    h: float

    @property
    def x2(self) -> float:
        return self.x + self.w

    @property
    def y2(self) -> float:
        return self.y + self.h

    @classmethod
    def from_dict(cls, d: dict[str, Any] | None) -> Box | None:
        if not d:
            return None
        return cls(float(d["x"]), float(d["y"]), float(d["w"]), float(d["h"]))


@dataclass(frozen=True)
class SmokeFinding:
    defect_class: str
    row_id: str
    message: str
    detail: str = ""

    def __str__(self) -> str:
        base = f"[{self.defect_class}] {self.row_id}: {self.message}"
        return f"{base} ({self.detail})" if self.detail else base

    def key(self) -> tuple[str, str, str]:
        return (self.defect_class, self.row_id, self.message)


@dataclass
class VisitSpec:
    visit_id: str
    path: str
    role: str  # none|user|admin|staff
    row_ids: list[str] = field(default_factory=list)
    delivered: dict[str, str] = field(default_factory=dict)
    try_dialog: bool = False
    expect_footer: bool = False
    kinds: list[str] = field(default_factory=list)
    must_change_password: bool = False

    def to_plan_dict(self) -> dict[str, Any]:
        return {
            "visit_id": self.visit_id,
            "path": self.path,
            "role": self.role,
            "delivered": self.delivered,
            "try_dialog": self.try_dialog,
            "expect_footer": self.expect_footer,
            "row_ids": list(self.row_ids),
            "must_change_password": self.must_change_password,
        }


@dataclass
class RowVisualStatus:
    row_id: str
    status: str  # visual_ok | visual_fail | known_debt | unvisitable
    visit_id: str = ""
    findings: list[SmokeFinding] = field(default_factory=list)


@dataclass
class SmokeCoverageReport:
    total_rows: int
    visual_ok: int
    known_debt: int
    visual_fail: int
    unvisitable: int
    coverage_pct: float
    rows: list[RowVisualStatus] = field(default_factory=list)
    findings: list[SmokeFinding] = field(default_factory=list)
    crush_ok: bool = True

    @property
    def gate_ok(self) -> bool:
        """D4：覆盖率 100%（ok+known_debt+记账 unvisitable）且无未记账 fail。"""
        covered = self.visual_ok + self.known_debt + self.unvisitable
        return self.visual_fail == 0 and covered == self.total_rows and self.crush_ok


def repo_root(root: Path | None = None) -> Path:
    if root is not None:
        return Path(root)
    return Path(__file__).resolve().parents[3]


def baseline_frontend_dir(root: Path | None = None) -> Path:
    return repo_root(root) / "skeletons" / "baseline" / "frontend"


def factory_frontend_dir(root: Path | None = None) -> Path:
    return repo_root(root) / "frontend"


def smoke_harness_dir(root: Path | None = None) -> Path:
    return repo_root(root) / "backend" / "tests" / "layout_smoke"


def pilot_rows(root: Path | None = None) -> list[LayoutRow]:
    """从台账取出 D3 试点行；缺行则抛错（台账漂移）。"""
    rows = generate_layout_inventory(root)
    by_id = {r.row_id: r for r in rows}
    missing = sorted(PILOT_ROW_IDS - set(by_id))
    if missing:
        raise AssertionError(f"D3 试点行不在台账: {missing}")
    return [
        by_id[PILOT_PAGE_ROW_ID],
        by_id[PILOT_COMPONENT_ROW_ID],
        by_id[PILOT_PROFILE_ROW_ID],
    ]


def box_contains(parent: Box, child: Box, *, slack: float = _CONTAIN_SLACK) -> bool:
    return (
        child.x >= parent.x - slack
        and child.y >= parent.y - slack
        and child.x2 <= parent.x2 + slack
        and child.y2 <= parent.y2 + slack
    )


def box_iou(a: Box, b: Box) -> float:
    ix1, iy1 = max(a.x, b.x), max(a.y, b.y)
    ix2, iy2 = min(a.x2, b.x2), min(a.y2, b.y2)
    iw, ih = max(0.0, ix2 - ix1), max(0.0, iy2 - iy1)
    inter = iw * ih
    if inter <= 0:
        return 0.0
    union = a.w * a.h + b.w * b.h - inter
    return inter / union if union > 0 else 0.0


def concrete_path(path: str) -> str:
    """路由参数换成可打开的字面量。"""
    if not path:
        return "/"
    return _PARAM_PATH_RE.sub("1", path)


def page_surface_tag(row: LayoutRow) -> str:
    """从 page 行 row_id 解析 axis:id；无皮返回空。"""
    if row.kind != "page" or not row.path:
        return ""
    prefix = f"page:{row.side}:{row.path}"
    if row.row_id == prefix:
        return ""
    if row.row_id.startswith(prefix + ":"):
        return row.row_id[len(prefix) + 1 :]
    return ""


def surface_to_delivered(tag: str) -> dict[str, str]:
    if not tag or ":" not in tag:
        return {}
    axis, _, style_id = tag.partition(":")
    field_name = _SURFACE_TO_DELIVERED.get(axis)
    if not field_name or not style_id:
        return {}
    return {field_name: style_id}


def role_for_side(side: str, path: str = "") -> str:
    # 强制改密页：须已登录且 mustChangePassword，不能按 auth 清会话
    if path == "/force-change-password":
        return "user"
    if side in ("auth", "public"):
        return "none"
    if side == "admin":
        return "admin"
    if side == "staff":
        return "staff"
    if side == "user":
        return "user"
    return "user"


def _resolve_host_path(
    row: LayoutRow,
    by_id: dict[str, LayoutRow],
) -> tuple[str, str] | None:
    """返回 (concrete_path, role)；无法解析则 None。"""
    if row.kind == "page" and row.path:
        cp = concrete_path(row.path)
        return cp, role_for_side(row.side, cp)
    if row.kind == "shell":
        rep = _SHELL_REP_PATH.get(row.vue)
        if not rep:
            return None
        role = "admin" if "Admin" in row.vue else "staff" if "Work" in row.vue else "user"
        return rep, role
    if row.kind in ("component", "dialog"):
        if row.path:
            cp = concrete_path(row.path)
            return cp, role_for_side(row.side, cp)
        for hid in row.hosts:
            host = by_id.get(hid)
            if not host:
                continue
            got = _resolve_host_path(host, by_id)
            if got:
                return got
        return None
    return None


def build_visit_plan(root: Path | None = None) -> tuple[list[VisitSpec], list[str]]:
    """台账 → 去重 visit 列表；第二返回值为无法解析 path 的 row_id（须记账）。"""
    rows = generate_layout_inventory(root)
    by_id = {r.row_id: r for r in rows}
    unvisitable: list[str] = []
    # key → VisitSpec
    bucket: dict[tuple[str, str, str, bool], VisitSpec] = {}

    for row in rows:
        resolved = _resolve_host_path(row, by_id)
        if resolved is None:
            unvisitable.append(row.row_id)
            continue
        path, role = resolved
        surf = page_surface_tag(row)
        delivered = surface_to_delivered(surf)
        try_dialog = row.kind == "dialog"
        must_pw = path == "/force-change-password"
        # 同 path+role+皮+改密态 合并；dialog 行把 try_dialog 升为 True
        delivered_key = json.dumps(delivered, sort_keys=True, ensure_ascii=False)
        key = (path, role, delivered_key, must_pw)
        spec = bucket.get(key)
        if spec is None:
            vid = f"{role}:{path}"
            if delivered:
                vid += f":{surf}"
            if must_pw:
                vid += ":must_pw"
            spec = VisitSpec(
                visit_id=vid,
                path=path,
                role=role,
                delivered=delivered,
                try_dialog=try_dialog,
                expect_footer=(row.row_id == PILOT_COMPONENT_ROW_ID or "AuthShell" in row.vue),
                must_change_password=must_pw,
            )
            bucket[key] = spec
        if row.row_id not in spec.row_ids:
            spec.row_ids.append(row.row_id)
        if row.kind not in spec.kinds:
            spec.kinds.append(row.kind)
        if try_dialog:
            spec.try_dialog = True

    # 资料页账户脸不进台账 surfaces；显式探针，否则 member stretch 病扫不到
    for face_id, delivered in _PROFILE_FACE_PROBES:
        vid = f"user:/profile:accountFace:{face_id}"
        key = (
            "/profile",
            "user",
            json.dumps(delivered, sort_keys=True, ensure_ascii=False),
            False,
        )
        if key in bucket:
            spec = bucket[key]
            if PILOT_PROFILE_ROW_ID not in spec.row_ids:
                spec.row_ids.append(PILOT_PROFILE_ROW_ID)
            continue
        bucket[key] = VisitSpec(
            visit_id=vid,
            path="/profile",
            role="user",
            delivered=dict(delivered),
            row_ids=[PILOT_PROFILE_ROW_ID],
            kinds=["page"],
        )

    visits = sorted(bucket.values(), key=lambda v: (v.role, v.path, v.visit_id))
    return visits, unvisitable


def _box_edge_gap(a: Box, b: Box) -> float:
    """两轴对齐外包矩形的外边距；相交为 0。"""
    dx = max(0.0, max(a.x - b.x2, b.x - a.x2))
    dy = max(0.0, max(a.y - b.y2, b.y - a.y2))
    if dx == 0.0 and dy == 0.0:
        return 0.0
    if dx == 0.0:
        return dy
    if dy == 0.0:
        return dx
    return (dx * dx + dy * dy) ** 0.5


def assert_abs_ctrls_near_flow(
    metrics: dict[str, Any], *, row_ids: list[str]
) -> list[SmokeFinding]:
    """通用：绝对/固定定位可点控件须贴近同槽文档流内容（禁一事一控件断言）。"""
    ctrls = metrics.get("abs_ctrls")
    if not isinstance(ctrls, list) or not ctrls:
        return []
    out: list[SmokeFinding] = []
    for item in ctrls:
        if not isinstance(item, dict):
            continue
        gap = item.get("gap")
        if gap is None:
            continue
        try:
            g = float(gap)
        except (TypeError, ValueError):
            continue
        label = str(item.get("text") or item.get("tag") or "ctrl")[:24]
        if g > _ABS_CTRL_NEAR_FLOW_MAX:
            for rid in row_ids:
                out.append(
                    SmokeFinding(
                        "misaligned",
                        rid,
                        "绝对定位可点控件远离同槽文档流内容（易悬空/掉条底）",
                        f"gap={g:.1f}px ctrl={label}",
                    )
                )
            break
        # 水平：须大致钉在文档流锚中轴（非对称 padding 把 left:50% 挤歪时必红）
        cx_delta = item.get("cx_delta")
        try:
            cxd = float(cx_delta) if cx_delta is not None else None
        except (TypeError, ValueError):
            cxd = None
        if cxd is not None and cxd > 24.0:
            for rid in row_ids:
                out.append(
                    SmokeFinding(
                        "misaligned",
                        rid,
                        "绝对定位可点控件未水平居中于同槽文档流锚点",
                        f"cx_delta={cxd:.1f}px ctrl={label}",
                    )
                )
            break
    return out


def assert_avatar_edit_geometry(
    metrics: dict[str, Any], *, row_id: str
) -> list[SmokeFinding]:
    """兼容旧测：把换头像样例折成 abs_ctrls 再走通用断言。"""
    if metrics.get("abs_ctrls"):
        return assert_abs_ctrls_near_flow(metrics, row_ids=[row_id])
    btn = Box.from_dict(metrics.get("avatar_btn"))
    av = Box.from_dict(metrics.get("avatar")) or Box.from_dict(metrics.get("avatar_slot"))
    if not metrics.get("not_blank"):
        return [SmokeFinding("chrome_break", row_id, "资料页空白或头像槽未挂载")]
    if btn is None or av is None:
        return [
            SmokeFinding(
                "clip_hide",
                row_id,
                "可编辑资料页缺少可见「换头像」或圆头像几何",
            )
        ]
    synth = {
        "abs_ctrls": [
            {
                "gap": _box_edge_gap(btn, av),
                "text": "换头像",
            }
        ]
    }
    return assert_abs_ctrls_near_flow(synth, row_ids=[row_id])


def assert_metrics_ok(metrics: dict[str, Any], *, row_ids: set[str] | None = None) -> list[SmokeFinding]:
    """D3 试点几何断言（login / AuthShell / profile×member）；返回 findings（空=绿）。"""
    rows = row_ids or set(PILOT_ROW_IDS)
    out: list[SmokeFinding] = []
    page_id = PILOT_PAGE_ROW_ID
    comp_id = PILOT_COMPONENT_ROW_ID
    profile_id = PILOT_PROFILE_ROW_ID

    # 登录段（顶层字段）；资料段在 profile_member
    login_blank = not metrics.get("not_blank")
    if login_blank and page_id in rows:
        out.append(SmokeFinding("chrome_break", page_id, "页面空白或关键壳未挂载"))
        # 仍尝试资料段
    elif not login_blank:
        auth = Box.from_dict(metrics.get("auth"))
        panel = Box.from_dict(metrics.get("panel"))
        cta = Box.from_dict(metrics.get("cta"))
        footer = Box.from_dict(metrics.get("footer"))

        if page_id in rows:
            if auth is None:
                out.append(SmokeFinding("chrome_break", page_id, "缺 layout_faces 壳节点 .auth"))
            if cta is None:
                out.append(SmokeFinding("clip_hide", page_id, "主 CTA（.submit）未找到或不可见"))
            elif cta.w < _MIN_HIT_W or cta.h < _MIN_HIT_H:
                out.append(
                    SmokeFinding(
                        "crushed",
                        page_id,
                        "主 CTA 可点尺寸过小",
                        f"{cta.w:.1f}x{cta.h:.1f}",
                    )
                )
            if panel is not None and cta is not None and not box_contains(panel, cta):
                out.append(
                    SmokeFinding(
                        "overflow",
                        page_id,
                        "主 CTA 外包矩形未落在 .panel 内容盒内",
                        f"cta={cta} panel={panel}",
                    )
                )
            if metrics.get("cta_full_ellipsis"):
                out.append(
                    SmokeFinding(
                        "clip_hide",
                        page_id,
                        "主 CTA 文案整段单一 ellipsis（挤破可读性）",
                    )
                )

        if comp_id in rows:
            if auth is None:
                out.append(SmokeFinding("chrome_break", comp_id, "AuthShell 根 .auth 未挂载"))
            if footer is None and metrics.get("expect_footer"):
                out.append(
                    SmokeFinding("chrome_break", comp_id, "AuthShell card_foot（.panel-ft）缺失")
                )
            brand = Box.from_dict(metrics.get("brand"))
            if brand is not None and panel is not None:
                iou = box_iou(brand, panel)
                if iou > _IOU_MAX:
                    out.append(
                        SmokeFinding(
                            "overlap",
                            comp_id,
                            "AuthShell brand 与 panel 叠穿过重",
                            f"iou={iou:.2f}",
                        )
                    )

    if profile_id in rows:
        prof = metrics.get("profile_member")
        if not isinstance(prof, dict):
            out.append(
                SmokeFinding(
                    "chrome_break",
                    profile_id,
                    "试点未采集 profile_member（账户脸/绝对可点探针）",
                )
            )
        else:
            if not prof.get("not_blank"):
                out.append(
                    SmokeFinding("chrome_break", profile_id, "资料页空白或头像槽未挂载")
                )
            out.extend(assert_abs_ctrls_near_flow(prof, row_ids=[profile_id]))

    return out


def assert_row_metrics(metrics: dict[str, Any], row_ids: list[str]) -> list[SmokeFinding]:
    """D4：对一次 visit 的 metrics，给挂在该 visit 上的每行出 findings。"""
    out: list[SmokeFinding] = []
    if metrics.get("overlay") or metrics.get("nav_error"):
        for rid in row_ids:
            out.append(
                SmokeFinding(
                    "chrome_break",
                    rid,
                    "页面加载失败或 Vite overlay",
                    str(metrics.get("nav_error") or "overlay"),
                )
            )
        return out
    if not metrics.get("not_blank"):
        for rid in row_ids:
            out.append(SmokeFinding("chrome_break", rid, "页面空白或关键壳未挂载"))
        return out

    # 登录误跳（想进业务页却落在 login）
    path = str(metrics.get("path") or "")
    want = str(metrics.get("want_path") or "")
    if want and path in ("/login", "/admin/login", "/staff/login") and want not in (
        "/login",
        "/admin/login",
        "/staff/login",
        "/register",
        "/forgot-password",
        "/activate",
        "/agreement",
        "/privacy",
    ):
        for rid in row_ids:
            out.append(
                SmokeFinding(
                    "chrome_break",
                    rid,
                    "未登录会话被踢回登录页",
                    f"want={want} got={path}",
                )
            )
        return out

    if metrics.get("overflow_x"):
        for rid in row_ids:
            out.append(SmokeFinding("overflow", rid, "文档出现横向滚动（整页撑破）"))

    root = Box.from_dict(metrics.get("root"))
    cta = Box.from_dict(metrics.get("cta"))
    if cta is not None and (cta.w < _MIN_HIT_W or cta.h < _MIN_HIT_H):
        for rid in row_ids:
            out.append(
                SmokeFinding(
                    "crushed",
                    rid,
                    "主 CTA 可点尺寸过小",
                    f"{cta.w:.1f}x{cta.h:.1f}",
                )
            )
    if root is not None and cta is not None and not box_contains(root, cta, slack=4.0):
        for rid in row_ids:
            out.append(
                SmokeFinding(
                    "overflow",
                    rid,
                    "主 CTA 未落在 #app 内容盒内",
                    f"cta={cta} root={root}",
                )
            )
    if metrics.get("cta_full_ellipsis"):
        for rid in row_ids:
            out.append(
                SmokeFinding(
                    "clip_hide",
                    rid,
                    "主 CTA 文案整段单一 ellipsis（挤破可读性）",
                )
            )

    # 全页通用：绝对定位可点 ↔ 同槽文档流（换头像等只是样例）
    out.extend(assert_abs_ctrls_near_flow(metrics, row_ids=list(row_ids)))

    # 多 CTA 叠穿
    raw_ctas = metrics.get("ctas") or []
    boxes: list[Box] = []
    for item in raw_ctas:
        b = Box.from_dict(item.get("box") if isinstance(item, dict) else item)
        if b:
            boxes.append(b)
    for i in range(len(boxes)):
        for j in range(i + 1, len(boxes)):
            iou = box_iou(boxes[i], boxes[j])
            if iou > _IOU_MAX:
                for rid in row_ids:
                    out.append(
                        SmokeFinding(
                            "overlap",
                            rid,
                            "邻接主按钮叠穿过重",
                            f"iou={iou:.2f}",
                        )
                    )
                break
        else:
            continue
        break

    # AuthShell 试点行若挂在本 visit，补壳断言
    if PILOT_COMPONENT_ROW_ID in row_ids or PILOT_PAGE_ROW_ID in row_ids:
        auth = Box.from_dict(metrics.get("auth"))
        panel = Box.from_dict(metrics.get("panel"))
        brand = Box.from_dict(metrics.get("brand"))
        footer = Box.from_dict(metrics.get("footer"))
        if PILOT_PAGE_ROW_ID in row_ids and want in ("/login", "") and path == "/login":
            if auth is None:
                out.append(SmokeFinding("chrome_break", PILOT_PAGE_ROW_ID, "缺 layout_faces 壳节点 .auth"))
        if PILOT_COMPONENT_ROW_ID in row_ids and path == "/login":
            if auth is None:
                out.append(
                    SmokeFinding("chrome_break", PILOT_COMPONENT_ROW_ID, "AuthShell 根 .auth 未挂载")
                )
            if footer is None and metrics.get("expect_footer"):
                out.append(
                    SmokeFinding(
                        "chrome_break",
                        PILOT_COMPONENT_ROW_ID,
                        "AuthShell card_foot（.panel-ft）缺失",
                    )
                )
            if brand is not None and panel is not None:
                iou = box_iou(brand, panel)
                if iou > _IOU_MAX:
                    out.append(
                        SmokeFinding(
                            "overlap",
                            PILOT_COMPONENT_ROW_ID,
                            "AuthShell brand 与 panel 叠穿过重",
                            f"iou={iou:.2f}",
                        )
                    )

    return out


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def _wait_http(url: str, *, timeout_s: float = 45.0) -> None:
    deadline = time.time() + timeout_s
    last: Exception | None = None
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as resp:
                if 200 <= getattr(resp, "status", 200) < 500:
                    return
        except Exception as exc:  # noqa: BLE001 — 启动探针
            last = exc
            time.sleep(0.35)
    raise TimeoutError(f"等待前端就绪超时: {url} ({last})")


def start_baseline_vite(root: Path | None = None, *, port: int | None = None) -> tuple[subprocess.Popen[Any], str]:
    """起 baseline Vite；返回 (proc, base_url)。调用方负责 terminate。"""
    fe = baseline_frontend_dir(root)
    if not (fe / "node_modules").is_dir():
        raise FileNotFoundError(f"baseline 未装依赖: {fe / 'node_modules'}")
    port = port or _free_port()
    env = os.environ.copy()
    env["BROWSER"] = "none"
    log_dir = repo_root(root) / ".runtime-tmp"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f"layout-smoke-vite-{port}.log"
    log_f = open(log_path, "w", encoding="utf-8", errors="replace")
    npm = "npm.cmd" if os.name == "nt" else "npm"
    smoke_cfg = smoke_harness_dir(root) / "vite.smoke.config.mjs"
    proc = subprocess.Popen(
        [
            npm,
            "run",
            "dev",
            "--",
            "--config",
            str(smoke_cfg),
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
        ],
        cwd=str(fe),
        env=env,
        stdout=log_f,
        stderr=subprocess.STDOUT,
    )
    setattr(proc, "_layout_smoke_log", log_f)
    base = f"http://127.0.0.1:{port}"
    try:
        _wait_http(base + "/")
        _wait_http(base + "/src/main.js")
    except Exception:
        stop_proc(proc)
        raise
    return proc, base


def stop_proc(proc: subprocess.Popen[Any] | None) -> None:
    if proc is None:
        return
    log_f = getattr(proc, "_layout_smoke_log", None)
    pid = getattr(proc, "pid", None)
    # Windows：npm 拉起的 vite 是子树，只 terminate 父进程会留僵尸占端口
    if os.name == "nt" and pid:
        subprocess.run(
            ["taskkill", "/PID", str(pid), "/T", "/F"],
            capture_output=True,
            check=False,
        )
    else:
        proc.terminate()
        try:
            proc.wait(timeout=8)
        except subprocess.TimeoutExpired:
            proc.kill()
    try:
        proc.wait(timeout=3)
    except Exception:  # noqa: BLE001
        pass
    if log_f is not None:
        try:
            log_f.close()
        except Exception:  # noqa: BLE001
            pass


def run_playwright_pilot(
    base_url: str,
    *,
    root: Path | None = None,
    crush: bool = False,
) -> dict[str, Any]:
    """跑 Node 冒烟脚本，返回 metrics JSON（含 findings 由 Python 再判）。"""
    harness = smoke_harness_dir(root)
    fe = factory_frontend_dir(root)
    node = "node.exe" if os.name == "nt" else "node"
    script = harness / "collect_pilot_metrics.mjs"
    if not script.is_file():
        raise FileNotFoundError(script)
    env = os.environ.copy()
    env["LAYOUT_SMOKE_BASE_URL"] = base_url.rstrip("/")
    env["LAYOUT_SMOKE_CRUSH"] = "1" if crush else "0"
    env["LAYOUT_SMOKE_FE_ROOT"] = str(fe)
    env["NODE_PATH"] = str(fe / "node_modules")
    proc = subprocess.run(
        [node, str(script)],
        cwd=str(harness),
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
        check=False,
    )
    out = proc.stdout or ""
    err = proc.stderr or ""
    if proc.returncode != 0:
        raise RuntimeError(
            "layout smoke playwright 失败:\n"
            f"stdout={out[-2000:]}\nstderr={err[-2000:]}"
        )
    line = out.strip().splitlines()
    if not line:
        raise RuntimeError(f"layout smoke 无 metrics 输出\nstderr={err[-2000:]}")
    return json.loads(line[-1])


def run_layout_smoke_pilot(
    root: Path | None = None,
    *,
    base_url: str | None = None,
) -> list[SmokeFinding]:
    """端到端：必要时起 Vite → 采集 → 断言（含一次窄视口挤破探针）。"""
    pilot_rows(root)  # 台账钉住
    own_proc: subprocess.Popen[Any] | None = None
    url = base_url
    try:
        if not url:
            own_proc, url = start_baseline_vite(root)
        findings: list[SmokeFinding] = []
        for crush in (False, True):
            metrics = run_playwright_pilot(url, root=root, crush=crush)
            tag = "crush" if crush else "wide"
            hits = assert_metrics_ok(metrics)
            for f in hits:
                findings.append(
                    SmokeFinding(
                        f.defect_class,
                        f.row_id,
                        f"{f.message} [{tag}]",
                        f.detail,
                    )
                )
        seen: set[tuple[str, str, str]] = set()
        out: list[SmokeFinding] = []
        for f in findings:
            k = (f.defect_class, f.row_id, f.message)
            if k in seen:
                continue
            seen.add(k)
            out.append(f)
        return out
    finally:
        stop_proc(own_proc)


def assert_layout_smoke_pilot_ok(
    root: Path | None = None,
    *,
    base_url: str | None = None,
    known: set[tuple[str, str, str]] | None = None,
) -> list[SmokeFinding]:
    findings = run_layout_smoke_pilot(root, base_url=base_url)
    known = known or set()
    unexpected = [
        f for f in findings if (f.defect_class, f.row_id, f.message) not in known
    ]
    if unexpected:
        preview = "\n".join(str(f) for f in unexpected[:40])
        raise AssertionError(f"布局视觉冒烟红灯 {len(unexpected)} 条:\n{preview}")
    return findings


def run_playwright_full(
    base_url: str,
    visits: list[VisitSpec],
    *,
    root: Path | None = None,
    crush_probe: VisitSpec | None = None,
) -> list[dict[str, Any]]:
    """跑全表采集脚本；返回 results 列表。"""
    harness = smoke_harness_dir(root)
    fe = factory_frontend_dir(root)
    node = "node.exe" if os.name == "nt" else "node"
    script = harness / "collect_full_metrics.mjs"
    if not script.is_file():
        raise FileNotFoundError(script)
    plan = {
        "visits": [v.to_plan_dict() for v in visits],
        "crush_probe": crush_probe.to_plan_dict() if crush_probe else None,
    }
    log_dir = repo_root(root) / ".runtime-tmp"
    log_dir.mkdir(parents=True, exist_ok=True)
    plan_path = log_dir / "layout-smoke-plan.json"
    plan_path.write_text(json.dumps(plan, ensure_ascii=False), encoding="utf-8")
    env = os.environ.copy()
    env["LAYOUT_SMOKE_BASE_URL"] = base_url.rstrip("/")
    env["LAYOUT_SMOKE_FE_ROOT"] = str(fe)
    env["LAYOUT_SMOKE_PLAN_PATH"] = str(plan_path)
    env["NODE_PATH"] = str(fe / "node_modules")
    progress = os.environ.get("LAYOUT_SMOKE_PROGRESS")
    if progress:
        env["LAYOUT_SMOKE_PROGRESS"] = progress
    # 全表可能数分钟
    timeout_s = int(os.environ.get("LAYOUT_SMOKE_FULL_TIMEOUT", "1200"))
    proc = subprocess.run(
        [node, str(script)],
        cwd=str(harness),
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout_s,
        check=False,
    )
    out = proc.stdout or ""
    err = proc.stderr or ""
    if proc.returncode != 0:
        raise RuntimeError(
            "layout smoke full 失败:\n"
            f"stdout={out[-3000:]}\nstderr={err[-3000:]}"
        )
    line = out.strip().splitlines()
    if not line:
        raise RuntimeError(f"layout smoke full 无输出\nstderr={err[-2000:]}")
    summary = json.loads(line[-1])
    return list(summary.get("results") or [])


def run_layout_smoke_full(
    root: Path | None = None,
    *,
    base_url: str | None = None,
    known: set[tuple[str, str, str]] | None = None,
    known_unvisitable: set[str] | None = None,
) -> SmokeCoverageReport:
    """D4：全表视觉；返回覆盖率报告。known = 真阳性记账（不改页）。"""
    known = known or set()
    known_unvisitable = known_unvisitable or set()
    visits, unvisitable = build_visit_plan(root)
    rows = generate_layout_inventory(root)

    own_proc: subprocess.Popen[Any] | None = None
    url = base_url
    try:
        if not url:
            own_proc, url = start_baseline_vite(root)
        crush = VisitSpec(
            visit_id="crush:/login",
            path="/login",
            role="none",
            expect_footer=True,
            row_ids=[PILOT_PAGE_ROW_ID, PILOT_COMPONENT_ROW_ID],
        )
        results = run_playwright_full(url, visits, root=root, crush_probe=crush)
    finally:
        stop_proc(own_proc)

    # visit_id → metrics（非 crush）
    metrics_by_visit: dict[str, dict[str, Any]] = {}
    crush_metrics: dict[str, Any] | None = None
    for m in results:
        if m.get("crush_probe"):
            crush_metrics = m
            continue
        vid = str(m.get("visit_id") or "")
        if vid:
            metrics_by_visit[vid] = m

    row_status: dict[str, RowVisualStatus] = {}
    all_findings: list[SmokeFinding] = []

    for rid in unvisitable:
        if rid in known_unvisitable:
            row_status[rid] = RowVisualStatus(rid, "unvisitable")
        else:
            row_status[rid] = RowVisualStatus(
                rid,
                "visual_fail",
                findings=[
                    SmokeFinding("chrome_break", rid, "无法解析可打开 path（缺 hosts/代表路由）")
                ],
            )
            all_findings.extend(row_status[rid].findings)

    for v in visits:
        m = metrics_by_visit.get(v.visit_id)
        if m is None:
            for rid in v.row_ids:
                f = SmokeFinding("chrome_break", rid, "全表采集缺少该 visit 结果")
                row_status[rid] = RowVisualStatus(rid, "visual_fail", v.visit_id, [f])
                all_findings.append(f)
            continue
        # 合并 plan 上的 expect_footer
        m = dict(m)
        m["expect_footer"] = v.expect_footer
        m["want_path"] = v.path
        hits = assert_row_metrics(m, v.row_ids)
        by_row: dict[str, list[SmokeFinding]] = {rid: [] for rid in v.row_ids}
        for f in hits:
            by_row.setdefault(f.row_id, []).append(f)
            all_findings.append(f)
        for rid in v.row_ids:
            rf = by_row.get(rid) or []
            unexpected = [f for f in rf if f.key() not in known]
            known_hits = [f for f in rf if f.key() in known]
            if unexpected:
                row_status[rid] = RowVisualStatus(rid, "visual_fail", v.visit_id, unexpected)
            elif known_hits:
                row_status[rid] = RowVisualStatus(rid, "known_debt", v.visit_id, known_hits)
            else:
                row_status[rid] = RowVisualStatus(rid, "visual_ok", v.visit_id)

    # 挤破探针：须能判定且无未记账红
    crush_ok = True
    if crush_metrics is not None:
        crush_metrics = dict(crush_metrics)
        crush_metrics["expect_footer"] = True
        crush_hits = assert_metrics_ok(crush_metrics, row_ids=set(PILOT_ROW_IDS))
        for f in crush_hits:
            tagged = SmokeFinding(
                f.defect_class, f.row_id, f"{f.message} [crush]", f.detail
            )
            if tagged.key() not in known and f.key() not in known:
                crush_ok = False
                all_findings.append(tagged)

    # 台账每一行必须有状态
    for r in rows:
        if r.row_id not in row_status:
            row_status[r.row_id] = RowVisualStatus(
                r.row_id,
                "visual_fail",
                findings=[SmokeFinding("chrome_break", r.row_id, "未纳入 visit plan")],
            )
            all_findings.extend(row_status[r.row_id].findings)

    statuses = list(row_status.values())
    ok_n = sum(1 for s in statuses if s.status == "visual_ok")
    debt_n = sum(1 for s in statuses if s.status == "known_debt")
    fail_n = sum(1 for s in statuses if s.status == "visual_fail")
    un_n = sum(1 for s in statuses if s.status == "unvisitable")
    total = len(statuses)
    covered = ok_n + debt_n + un_n
    pct = (100.0 * covered / total) if total else 0.0
    return SmokeCoverageReport(
        total_rows=total,
        visual_ok=ok_n,
        known_debt=debt_n,
        visual_fail=fail_n,
        unvisitable=un_n,
        coverage_pct=pct,
        rows=statuses,
        findings=all_findings,
        crush_ok=crush_ok,
    )


def assert_layout_smoke_coverage_ok(
    root: Path | None = None,
    *,
    base_url: str | None = None,
    known: set[tuple[str, str, str]] | None = None,
    known_unvisitable: set[str] | None = None,
) -> SmokeCoverageReport:
    report = run_layout_smoke_full(
        root,
        base_url=base_url,
        known=known,
        known_unvisitable=known_unvisitable,
    )
    if not report.gate_ok:
        fails = [s for s in report.rows if s.status == "visual_fail"]
        preview = "\n".join(
            f"{s.row_id}: " + "; ".join(str(f) for f in s.findings[:2])
            for s in fails[:30]
        )
        raise AssertionError(
            f"D4 视觉覆盖未齐: ok={report.visual_ok} debt={report.known_debt} "
            f"fail={report.visual_fail} unvisitable={report.unvisitable} "
            f"coverage={report.coverage_pct:.1f}% crush_ok={report.crush_ok}\n{preview}"
        )
    return report
