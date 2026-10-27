"""起包前 UI 布局闸 · D1 台账生成与对账。

真源：docs/ui-layout-prebake-gate.md（A–F 扫描 → page/shell/component/dialog；
import→hosts；漏页/漏组件/漏壳红灯）。

只读 skeletons/baseline/frontend；不改学生包业务逻辑、不做视觉冒烟（D3+）。
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from app.bake.menu_routes import ADMIN_MENU_PATHS, USER_MENU_PATHS
from app.bake.shell_face import _CARD_VOICES
from app.bake.themes import (
    APPLY_SURFACE_STYLES,
    APPROVE_SURFACE_STYLES,
    BORROW_SURFACE_STYLES,
    CONTENT_SURFACE_STYLES,
    FOLLOW_SURFACE_STYLES,
    INTERACT_SURFACE_STYLES,
    PORTAL_HOME_STYLES,
    REPAIR_SURFACE_STYLES,
    RESERVE_SURFACE_STYLES,
    TRADE_SURFACE_STYLES,
)

_REPO = Path(__file__).resolve().parents[3]
_FE_SRC = _REPO / "skeletons" / "baseline" / "frontend" / "src"

# 路由有、菜单无：仅真·壳内/鉴权/系统页（禁止把已在菜单里的 path 塞进来遮丑）
_PATH_EXEMPT_NO_MENU: frozenset[str] = frozenset(
    {
        "/login",
        "/register",
        "/forgot-password",
        "/force-change-password",
        "/activate",
        "/agreement",
        "/privacy",
        "/staff",
        "/staff/tickets",
        "/staff/orders",
        "/staff/slots",
        "/staff/clean",
        "/staff/login",
        "/admin",
        "/admin/login",
        "/admin/staff-login",
        "/admin/profile",
        "/",
        "/cert-verify",
        "/account",
        "/error",
        "/loading",
        "/:pathMatch(.*)*",
    }
)
_PATH_EXEMPT_PREFIXES: tuple[str, ...] = (
    "/notices/",
    "/archive/item/",
    "/special/",
    "/vote/poster",
)

_SURFACE_AXIS: dict[str, tuple[str, list[dict[str, str]]]] = {
    "portalHomeStyle": ("portalHome", PORTAL_HOME_STYLES),
    "contentSurfaceStyle": ("content", CONTENT_SURFACE_STYLES),
    "tradeSurfaceStyle": ("trade", TRADE_SURFACE_STYLES),
    "reserveSurfaceStyle": ("reserve", RESERVE_SURFACE_STYLES),
    "borrowSurfaceStyle": ("borrow", BORROW_SURFACE_STYLES),
    "applySurfaceStyle": ("apply", APPLY_SURFACE_STYLES),
    "interactSurfaceStyle": ("interact", INTERACT_SURFACE_STYLES),
    "followSurfaceStyle": ("follow", FOLLOW_SURFACE_STYLES),
    "repairSurfaceStyle": ("repair", REPAIR_SURFACE_STYLES),
    "approveSurfaceStyle": ("approve", APPROVE_SURFACE_STYLES),
}

_IMPORT_COMP_RE = re.compile(
    r"""(?:from|import)\s*\(?\s*['"]([^'"]*?/components/[^'"]+\.vue)['"]""",
)
_IMPORT_LAYOUT_RE = re.compile(
    r"""(?:from|import)\s*\(?\s*['"]([^'"]*?/layouts/[^'"]+\.vue)['"]""",
)
_ROUTE_LAZY_PAIR_RE = re.compile(
    r"""path:\s*['"]([^'"]+)['"]\s*,\s*component:\s*\(\)\s*=>\s*import\(\s*['"]([^'"]+\.vue)['"]\s*\)""",
)
_ROUTE_STATIC_COMP_RE = re.compile(
    r"""path:\s*['"]([^'"]+)['"]\s*,\s*component:\s*(\w+)""",
)
# with*Routes 助手：'path', () => import('…vue')（含 add(kids, 'path', …) 三参）
_ROUTE_LOADER_PAIR_RE = re.compile(
    r"""['"]([^'"]+)['"]\s*,\s*\(\)\s*=>\s*import\(\s*['"]([^'"]+\.vue)['"]""",
)
# adminKids.push/splice 对象里挂的 path（含复用 views/user 的 messages/dm）
_ADMIN_KIDS_ROUTE_RE = re.compile(
    r"""adminKids\.(?:push|splice)\(\s*(?:[^,{]+,\s*)*\{"""
    r"""[\s\S]{0,200}?path:\s*['"]([^'"]+)['"]"""
    r"""[\s\S]{0,200}?import\(\s*['"]([^'"]+\.vue)['"]""",
)
# 页内对话框 + 抽屉（册 §1.1 dialog；漏抽屉 = 台账未尽责）
_EL_OVERLAY_RE = re.compile(r"""<(el-dialog|el-drawer)\b([^>]*)>""", re.I)
_DIALOG_VM_RE = re.compile(r"""v-model=["']([^"']+)["']""")
_DIALOG_TITLE_RE = re.compile(r""":?title=["']([^"']+)["']""")


@dataclass
class LayoutRow:
    row_id: str
    kind: str
    side: str
    path: str
    vue: str
    hosts: list[str] = field(default_factory=list)
    mount: str = "always"
    surfaces: list[str] = field(default_factory=list)
    layout_faces: list[str] = field(default_factory=list)
    interactive: bool = True
    gate_status: str = "pending"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class LayoutIssue:
    code: str
    message: str
    detail: str = ""

    def __str__(self) -> str:
        if self.detail:
            return f"[{self.code}] {self.message}: {self.detail}"
        return f"[{self.code}] {self.message}"


def frontend_src(root: Path | None = None, *, src: Path | None = None) -> Path:
    """解析前端 src 根。

    - ``src``：直接指定（出包 workspace 的 ``frontend/src``）
    - ``root``：仓库根 → ``skeletons/baseline/frontend/src``
    - 皆空：默认基线路径
    """
    if src is not None:
        return Path(src)
    if root is not None:
        return Path(root) / "skeletons" / "baseline" / "frontend" / "src"
    return _FE_SRC


def list_vue_rel(src: Path, *parts: str) -> list[str]:
    base = src.joinpath(*parts) if parts else src
    if not base.is_dir():
        return []
    return sorted(p.relative_to(src).as_posix() for p in base.rglob("*.vue"))


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _companion_texts(src: Path, vue_rel: str) -> str:
    """页面本体 + 同名 .setup.js（Vue 拆分后 import/皮在 setup）。"""
    vue_path = src / vue_rel
    chunks = [_read(vue_path)] if vue_path.is_file() else []
    stem = vue_path.with_suffix("")
    setup = Path(str(stem) + ".setup.js")
    if setup.is_file():
        chunks.append(_read(setup))
    return "\n".join(chunks)


def _norm_import_to_src_rel(importer_rel: str, spec: str) -> str | None:
    if "/components/" in spec:
        return "components/" + spec.split("/components/", 1)[1]
    if "/layouts/" in spec:
        return "layouts/" + spec.split("/layouts/", 1)[1]
    if "/views/" in spec:
        return "views/" + spec.split("/views/", 1)[1]
    imp_dir = Path(importer_rel).parent
    parts: list[str] = []
    for part in (imp_dir / spec).as_posix().replace("\\", "/").split("/"):
        if part == "..":
            if parts:
                parts.pop()
        elif part in ("", "."):
            continue
        else:
            parts.append(part)
    rel = "/".join(parts)
    if rel.startswith(("components/", "layouts/", "views/")):
        return rel
    return None


def build_import_graph(src: Path) -> dict[str, set[str]]:
    graph: dict[str, set[str]] = {}
    for path in list(src.rglob("*.vue")) + list(src.rglob("*.js")):
        if "node_modules" in path.parts:
            continue
        try:
            rel = path.relative_to(src).as_posix()
        except ValueError:
            continue
        text = _read(path)
        for rx in (_IMPORT_COMP_RE, _IMPORT_LAYOUT_RE):
            for m in rx.finditer(text):
                target = _norm_import_to_src_rel(rel, m.group(1))
                if target:
                    graph.setdefault(target, set()).add(rel)
    return graph


def _abs_path_for_vue(leaf: str, vue: str) -> str:
    """相对 children path 按 vue 落点升格为绝对 path（admin/staff/门户）。"""
    p = (leaf or "").strip()
    if not p or p.startswith("http"):
        return ""
    if p.startswith("/"):
        return p.rstrip("/") or "/"
    if vue.startswith("views/admin/"):
        return f"/admin/{p}"
    if vue.startswith("views/staff/"):
        return f"/staff/{p}"
    if vue.startswith("layouts/AdminLayout"):
        return "/admin" if p in {"", "admin"} else f"/admin/{p}"
    if vue.startswith("layouts/WorkLayout"):
        return "/staff" if p in {"", "staff"} else f"/staff/{p}"
    if vue.startswith("layouts/PortalLayout"):
        return "/" if p in {"", "/"} else f"/{p}"
    return f"/{p}"


def parse_router_path_vue(src: Path) -> dict[str, str]:
    """绝对 path → views/...|layouts/...（同 path 多挂时：门户用户页优先于 staff）。"""
    text = _read(src / "router" / "index.js")
    static_map: dict[str, str] = {}
    for m in re.finditer(
        r"""import\s+(\w+)\s+from\s+['"](\.\./(?:views|layouts)/[^'"]+\.vue)['"]""",
        text,
    ):
        static_map[m.group(1)] = (
            _norm_import_to_src_rel("router/index.js", m.group(2)) or ""
        )

    candidates: dict[str, list[str]] = {}

    def _remember(leaf: str, vue: str) -> None:
        if not vue:
            return
        abs_path = _abs_path_for_vue(leaf, vue)
        if not abs_path:
            return
        candidates.setdefault(abs_path, []).append(vue)

    for leaf, vue_spec in _ROUTE_LAZY_PAIR_RE.findall(text):
        vue = _norm_import_to_src_rel("router/index.js", vue_spec)
        if vue:
            _remember(leaf, vue)

    for leaf, name in _ROUTE_STATIC_COMP_RE.findall(text):
        vue = static_map.get(name, "")
        if vue:
            _remember(leaf, vue)

    for leaf, vue_spec in _ROUTE_LOADER_PAIR_RE.findall(text):
        vue = _norm_import_to_src_rel("router/index.js", vue_spec)
        if vue:
            _remember(leaf, vue)

    for leaf, vue_spec in _ADMIN_KIDS_ROUTE_RE.findall(text):
        vue = _norm_import_to_src_rel("router/index.js", vue_spec)
        if not vue:
            continue
        abs_path = f"/admin/{leaf}" if not str(leaf).startswith("/") else str(leaf)
        candidates.setdefault(abs_path.rstrip("/") or "/admin", []).append(vue)

    out: dict[str, str] = {}
    for path, vues in candidates.items():
        # 优先非 staff、非 layout
        ranked = sorted(
            vues,
            key=lambda v: (
                0 if v.startswith("views/user/") else 1,
                0 if v.startswith("views/") and "/staff/" not in v else 2,
                0 if not v.startswith("layouts/") else 3,
                v,
            ),
        )
        out[path] = ranked[0]
    return out


def collect_router_paths(src: Path) -> set[str]:
    """菜单对账用的路由绝对 path 集合（只信解析结果，禁止硬编码补洞）。"""
    paths = set(parse_router_path_vue(src).keys())
    text = _read(src / "router" / "index.js")
    for m in re.finditer(r"""redirect:\s*['"]([^'"]+)['"]""", text):
        raw = m.group(1)
        if raw.startswith("/"):
            paths.add(raw.rstrip("/") or "/")
    return {p for p in paths if p}


def _side_for(vue_rel: str, path: str) -> str:
    if vue_rel.startswith("layouts/"):
        name = Path(vue_rel).stem.lower()
        if "admin" in name:
            return "admin"
        if "work" in name or "staff" in name:
            return "staff"
        return "user"
    if vue_rel.startswith("components/"):
        return "shared"
    if vue_rel.startswith("views/admin/"):
        return "admin"
    if vue_rel.startswith("views/staff/"):
        return "staff"
    leaf = Path(vue_rel).stem.lower()
    if leaf in {
        "login",
        "register",
        "forgotpassword",
        "forcechangepassword",
        "activateaccount",
        "agreement",
        "privacy",
    }:
        return "auth"
    if path.startswith("/admin"):
        return "admin"
    if path.startswith("/staff"):
        return "staff"
    if path in {
        "/login",
        "/register",
        "/forgot-password",
        "/force-change-password",
        "/activate",
    }:
        return "auth"
    if vue_rel.startswith("views/user/") or vue_rel.startswith("views/special/"):
        return "user"
    return "user" if path else "public"


def _detect_layout_faces(text: str, *, kind: str, vue_rel: str) -> list[str]:
    faces: list[str] = []
    low = text.lower()
    if kind == "shell" or vue_rel.startswith("layouts/"):
        faces.append("chrome")
    if 'class="toolbar"' in text or "class='toolbar'" in text or ' class="toolbar ' in text:
        faces.append("toolbar")
    if "table-ops" in text or "row-actions" in text:
        faces.append("row_actions")
    if "el-dialog" in low or "el-drawer" in low:
        faces.append("dialog")
    if any(
        x in vue_rel
        for x in (
            "AiAssistantFloat",
            "MessageBell",
            "CartBadge",
            "ForceNoticeGate",
            "PortalSideRail",
        )
    ):
        faces.append("float")
    if 'type="primary"' in text or "type='primary'" in text:
        faces.append("primary_cta")
    if "card-foot" in text or ("footer" in low and ("el-dialog" in low or "card" in low)):
        faces.append("card_foot")
    seen: set[str] = set()
    out: list[str] = []
    for f in faces:
        if f not in seen:
            seen.add(f)
            out.append(f)
    return out


def _detect_interactive(text: str) -> bool:
    return any(
        m in text
        for m in (
            "el-button",
            "@click",
            "router-link",
            "RouterLink",
            "el-switch",
            "el-dropdown",
            'type="primary"',
        )
    )


def _camel_to_kebab(name: str) -> str:
    out: list[str] = []
    for i, ch in enumerate(name):
        if ch.isupper() and i:
            out.append("-")
            out.append(ch.lower())
        else:
            out.append(ch.lower())
    return "".join(out)


def _detect_surfaces(vue_rel: str, vue_text: str, companion_text: str) -> list[str]:
    """须循环的皮，格式 ``axis:id``。

    人审口径：只认**本页脸**——模板 ``data-*-surface`` / ``data-card-voice``；
    门户首页皮只挂 PortalHome。禁止因 setup 读 Style 就扩轴。
    """
    ids: list[str] = []
    seen: set[str] = set()
    for _key, (axis, catalog) in _SURFACE_AXIS.items():
        if axis == "portalHome":
            hit = vue_rel.endswith("PortalHome.vue") and (
                "portalHomeStyle" in companion_text
                or "VITE_PORTAL_HOME_STYLE" in companion_text
                or "portalHomeStyle" in vue_text
            )
        else:
            hit = f"data-{_camel_to_kebab(axis)}-surface" in vue_text
        if not hit:
            continue
        for item in catalog:
            tagged = f"{axis}:{item['id']}"
            if tagged not in seen:
                seen.add(tagged)
                ids.append(tagged)
    # 卡面叙事（册 D / shell_face._CARD_VOICES）；与 surface_style 正交
    if "data-card-voice" in vue_text:
        for vid in sorted(_CARD_VOICES):
            tagged = f"cardVoice:{vid}"
            if tagged not in seen:
                seen.add(tagged)
                ids.append(tagged)
    return ids


def _inline_dialog_suffixes(text: str) -> list[str]:
    """页内 el-dialog / el-drawer → dialog 行后缀（册：对话框与抽屉均有行）。"""
    suffixes: list[str] = []
    for i, m in enumerate(_EL_OVERLAY_RE.finditer(text), start=1):
        tag = (m.group(1) or "el-dialog").lower()
        attrs = m.group(2) or ""
        vm = _DIALOG_VM_RE.search(attrs)
        title = _DIALOG_TITLE_RE.search(attrs)
        if vm:
            suf = re.sub(r"[^\w.-]+", "-", vm.group(1)).strip("-")
        elif title:
            suf = re.sub(r"[^\w.-]+", "-", title.group(1)).strip("-")[:40]
        else:
            suf = f"{tag}-{i}"
        suffixes.append(suf or f"{tag}-{i}")
    seen: set[str] = set()
    out: list[str] = []
    for s in suffixes:
        if s not in seen:
            seen.add(s)
            out.append(s)
    return out


def _invert_path_vue(path_vue: dict[str, str]) -> dict[str, str]:
    inv: dict[str, list[str]] = {}
    for path, vue in path_vue.items():
        if vue.startswith("layouts/"):
            continue
        inv.setdefault(vue, []).append(path)
    out: dict[str, str] = {}
    for vue, paths in inv.items():
        paths_sorted = sorted(paths, key=lambda p: (p.count("/"), len(p), p))
        solid = [p for p in paths_sorted if ":" not in p]
        out[vue] = (solid or paths_sorted)[0]
    return out


def _row_id_page(side: str, path: str, surface: str = "") -> str:
    base = f"page:{side}:{path or '/'}"
    return f"{base}:{surface}" if surface else base


def _row_id_shell(vue_rel: str) -> str:
    return f"shell:{vue_rel}"


def _row_id_component(vue_rel: str) -> str:
    return f"component:{vue_rel}"


def _row_id_dialog(vue_rel: str, suffix: str = "") -> str:
    if suffix:
        return f"dialog:{vue_rel}#{suffix}"
    return f"dialog:{vue_rel}"


def _hosts_for(
    target_vue: str,
    import_graph: dict[str, set[str]],
    row_id_by_vue: dict[str, str],
) -> list[str]:
    hosts: set[str] = set()
    for importer in import_graph.get(target_vue, ()):
        vue_key = importer
        if importer.endswith(".setup.js"):
            vue_key = importer[: -len(".setup.js")] + ".vue"
        elif importer.endswith(".js"):
            cand = importer[:-3] + ".vue"
            if cand in row_id_by_vue:
                vue_key = cand
        rid = row_id_by_vue.get(vue_key)
        if rid:
            hosts.add(rid)
    return sorted(hosts)


def generate_layout_inventory(
    root: Path | None = None, *, src: Path | None = None
) -> list[LayoutRow]:
    """从 A–F 吐出全表台账（D1：gate_status 一律 pending）。

    ``src`` 可指向出包 ``frontend/src``（不经基线路径）。
    """
    src = frontend_src(root, src=src)
    views = list_vue_rel(src, "views")
    layouts = list_vue_rel(src, "layouts")
    components = list_vue_rel(src, "components")
    path_vue = parse_router_path_vue(src)
    vue_path = _invert_path_vue(path_vue)
    import_graph = build_import_graph(src)

    rows: list[LayoutRow] = []
    # 宿主索引：永远指向无皮后缀的规范行（多脸页 hosts 不绑某一皮）
    primary_id: dict[str, str] = {}

    for vue_rel in layouts:
        text = _companion_texts(src, vue_rel)
        rid = _row_id_shell(vue_rel)
        primary_id[vue_rel] = rid
        rows.append(
            LayoutRow(
                row_id=rid,
                kind="shell",
                side=_side_for(vue_rel, ""),
                path="",
                vue=vue_rel,
                layout_faces=_detect_layout_faces(text, kind="shell", vue_rel=vue_rel),
                interactive=_detect_interactive(text),
            )
        )

    for vue_rel in views:
        vue_only = _read(src / vue_rel) if (src / vue_rel).is_file() else ""
        text = _companion_texts(src, vue_rel)
        path = vue_path.get(vue_rel, "")
        side = _side_for(vue_rel, path)
        surfaces = _detect_surfaces(vue_rel, vue_only, text)
        faces = _detect_layout_faces(text, kind="page", vue_rel=vue_rel)
        interactive = _detect_interactive(text)
        # 规范行（hosts / 漏页对账锚点）
        rid = _row_id_page(side, path)
        primary_id[vue_rel] = rid
        rows.append(
            LayoutRow(
                row_id=rid,
                kind="page",
                side=side,
                path=path,
                vue=vue_rel,
                surfaces=list(surfaces),
                layout_faces=faces,
                interactive=interactive,
            )
        )
        # 同页多脸：path × 皮 分行（D3+ 视觉用；D1 已入账）
        for surf in surfaces:
            rows.append(
                LayoutRow(
                    row_id=_row_id_page(side, path, surf),
                    kind="page",
                    side=side,
                    path=path,
                    vue=vue_rel,
                    surfaces=list(surfaces),
                    layout_faces=faces,
                    interactive=interactive,
                )
            )
        for suf in _inline_dialog_suffixes(text):
            rows.append(
                LayoutRow(
                    row_id=_row_id_dialog(vue_rel, suf),
                    kind="dialog",
                    side=side,
                    path=path,
                    vue=vue_rel,
                    hosts=[rid],
                    layout_faces=["dialog"],
                    interactive=True,
                )
            )

    for vue_rel in components:
        text = _companion_texts(src, vue_rel)
        stem = Path(vue_rel).stem
        is_dialog = "Dialog" in stem or "Drawer" in stem
        kind = "dialog" if is_dialog else "component"
        rid = _row_id_dialog(vue_rel) if is_dialog else _row_id_component(vue_rel)
        primary_id[vue_rel] = rid
        rows.append(
            LayoutRow(
                row_id=rid,
                kind=kind,
                side="shared",
                path="",
                vue=vue_rel,
                layout_faces=_detect_layout_faces(text, kind=kind, vue_rel=vue_rel),
                interactive=_detect_interactive(text),
            )
        )

    for row in rows:
        if row.kind not in ("component", "dialog"):
            continue
        if row.hosts and row.vue.startswith("views/"):
            continue
        row.hosts = _hosts_for(row.vue, import_graph, primary_id)

    return rows


def menu_paths() -> set[str]:
    return set(USER_MENU_PATHS.values()) | set(ADMIN_MENU_PATHS.values())


def _path_exempt_from_menu(path: str) -> bool:
    if path in _PATH_EXEMPT_NO_MENU:
        return True
    for prefix in _PATH_EXEMPT_PREFIXES:
        if path.startswith(prefix):
            return True
    if ":" in path:
        return True
    return False


def reconcile_layout_inventory(
    rows: list[LayoutRow] | None = None,
    *,
    root: Path | None = None,
    src: Path | None = None,
    skip_menu_route_reconcile: bool = False,
) -> list[LayoutIssue]:
    """对账红灯（D1：漏页/漏组件/漏壳、hosts 空或不一致、A↔B）。

    出包 workspace：传 ``src`` 且 ``skip_menu_route_reconcile=True``，
    避免用工厂全量菜单表去审已剪枝包（会误红）。
    """
    src = frontend_src(root, src=src)
    rows = rows if rows is not None else generate_layout_inventory(root, src=src)
    issues: list[LayoutIssue] = []

    disk_views = set(list_vue_rel(src, "views"))
    disk_layouts = set(list_vue_rel(src, "layouts"))
    disk_components = set(list_vue_rel(src, "components"))
    disk_all = disk_views | disk_layouts | disk_components
    ledger_vues = {r.vue for r in rows if r.vue}

    for rel in sorted(disk_all - ledger_vues):
        if rel in disk_components:
            code = "missing_component"
        elif rel in disk_layouts:
            code = "missing_shell"
        else:
            code = "missing_page"
        issues.append(LayoutIssue(code, f"基线 {rel} 未入台账", rel))

    for rel in sorted(ledger_vues - disk_all):
        issues.append(LayoutIssue("stale_vue", "台账指向已删文件", rel))

    # 视图在磁盘但路由解析不到 → 人审也会问「这页怎么进」；与组件孤儿同级红
    path_vue = parse_router_path_vue(src)
    routed_views = {v for v in path_vue.values() if v.startswith("views/")}
    for rel in sorted(disk_views - routed_views):
        issues.append(
            LayoutIssue("unrouted_page", "视图未挂到 router（人审进不去）", rel)
        )

    import_graph = build_import_graph(src)
    # 规范页行 = 无皮后缀；皮分行不进 hosts 锚点
    primary: dict[str, str] = {}
    for r in rows:
        if r.kind == "page":
            if r.row_id == _row_id_page(r.side, r.path):
                primary[r.vue] = r.row_id
        elif r.kind in ("shell", "component", "dialog") and "#" not in r.row_id:
            primary[r.vue] = r.row_id

    for row in rows:
        if row.kind not in ("component", "dialog"):
            continue
        if row.vue.startswith("views/"):
            if not row.hosts:
                issues.append(
                    LayoutIssue("empty_hosts", "页内 dialog 缺 hosts", row.row_id)
                )
            continue
        expected = set(_hosts_for(row.vue, import_graph, primary))
        actual = set(row.hosts)
        if not actual:
            issues.append(
                LayoutIssue(
                    "empty_hosts",
                    "component/dialog hosts 为空（孤儿或未挂回）",
                    row.row_id,
                )
            )
            continue
        if expected != actual:
            missing = sorted(expected - actual)
            extra = sorted(actual - expected)
            detail = row.row_id
            if missing:
                detail += f"; missing={missing}"
            if extra:
                detail += f"; extra={extra}"
            issues.append(
                LayoutIssue("hosts_mismatch", "hosts 与 import 图不一致", detail)
            )

    if not skip_menu_route_reconcile:
        menus = menu_paths()
        router_paths = collect_router_paths(src)
        for mp in sorted(menus):
            if mp in router_paths:
                continue
            if any(rp == mp or rp.startswith(mp + "/") for rp in router_paths):
                continue
            issues.append(LayoutIssue("menu_without_route", "菜单 path 无对应路由", mp))

        for rp in sorted(router_paths):
            if _path_exempt_from_menu(rp):
                continue
            if rp in menus:
                continue
            if any(rp.startswith(p.rstrip("/") + "/") for p in menus):
                continue
            issues.append(
                LayoutIssue("route_without_menu", "业务路由不在菜单且未标豁免", rp)
            )

    return issues


# 基线真阳性记账（不改页消红）。工厂摘要与 D1 测共用。(code, detail)
# 2026-10-25：EntityDetailLayout 孤儿已删；空集 = 无登记例外。
BASELINE_KNOWN_ISSUES: frozenset[tuple[str, str]] = frozenset()


def issue_key(issue: LayoutIssue) -> tuple[str, str]:
    return (issue.code, issue.detail or issue.message)


def assert_layout_inventory_ok(
    root: Path | None = None,
    *,
    known: frozenset[tuple[str, str]] | None = None,
    src: Path | None = None,
    skip_menu_route_reconcile: bool = False,
) -> list[LayoutRow]:
    rows = generate_layout_inventory(root, src=src)
    issues = reconcile_layout_inventory(
        rows,
        root=root,
        src=src,
        skip_menu_route_reconcile=skip_menu_route_reconcile,
    )
    allow = known if known is not None else BASELINE_KNOWN_ISSUES
    unexpected = [i for i in issues if issue_key(i) not in allow]
    if unexpected:
        preview = "\n".join(str(i) for i in unexpected[:40])
        more = f"\n... (+{len(unexpected) - 40})" if len(unexpected) > 40 else ""
        raise AssertionError(f"布局台账对账红灯 {len(unexpected)} 条:\n{preview}{more}")
    return rows


def inventory_coverage(
    rows: list[LayoutRow] | None = None,
    root: Path | None = None,
    *,
    src: Path | None = None,
) -> dict[str, Any]:
    src = frontend_src(root, src=src)
    rows = rows if rows is not None else generate_layout_inventory(root, src=src)
    by_kind: dict[str, int] = {}
    for r in rows:
        by_kind[r.kind] = by_kind.get(r.kind, 0) + 1
    return {
        "rows": len(rows),
        "by_kind": by_kind,
        "views_on_disk": len(list_vue_rel(src, "views")),
        "layouts_on_disk": len(list_vue_rel(src, "layouts")),
        "components_on_disk": len(list_vue_rel(src, "components")),
        "views_in_ledger": len({r.vue for r in rows if r.vue.startswith("views/")}),
        "layouts_in_ledger": len({r.vue for r in rows if r.vue.startswith("layouts/")}),
        "components_in_ledger": len(
            {r.vue for r in rows if r.vue.startswith("components/")}
        ),
    }
