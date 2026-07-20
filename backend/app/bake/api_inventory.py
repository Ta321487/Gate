"""从学生工作区 Controller 静态扫描 REST 映射，供工厂产物页对照。

不依赖运行中的后端；不写入学生 ZIP。
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

_CLASS_RE = re.compile(r"(?:public\s+)?class\s+(\w+)\b")
_CLASS_REQ_RE = re.compile(
    r"@RequestMapping\s*\(\s*(?:value\s*=\s*|path\s*=\s*)?[\"']([^\"']*)[\"']",
)
_MAP_HEAD_RE = re.compile(
    r"@(Get|Post|Put|Patch|Delete|Request)Mapping\b(?:\s*\((.*?)\))?",
    re.DOTALL,
)
_PATH_IN_ARGS_RE = re.compile(
    r"(?:value|path)\s*=\s*[\"']([^\"']*)[\"']"
    r"|[\"'](/[^\"']*)[\"']"
    r"|[\"']([^\"']*)[\"']",
)
_METHOD_IN_ARGS_RE = re.compile(
    r"RequestMethod\.(GET|POST|PUT|PATCH|DELETE)",
    re.IGNORECASE,
)
_PATH_VAR_RE = re.compile(r"\{(\w+)(?::[^}]*)?\}")
_HANDLER_RE = re.compile(
    r"(?:public|protected|private)\s+(?:static\s+)?(.+?)\b(\w+)\s*\(",
    re.DOTALL,
)
_SKIP_HANDLER = frozenset(
    {
        "if",
        "for",
        "while",
        "switch",
        "catch",
        "return",
        "new",
        "class",
        "record",
        "enum",
        "interface",
    }
)

_SURFACE_LABEL = {
    "portal": "门户",
    "admin": "管理端",
    "baseline": "基线",
    "gate": "门禁自检",
}


def _strip_java_noise(src: str) -> str:
    """去掉块注释 / 行注释，减少误匹配。"""
    out: list[str] = []
    i, n = 0, len(src)
    while i < n:
        if src.startswith("/*", i):
            j = src.find("*/", i + 2)
            i = n if j < 0 else j + 2
            continue
        if src.startswith("//", i):
            j = src.find("\n", i)
            i = n if j < 0 else j
            continue
        if src[i] in "\"'":
            q = src[i]
            out.append(q)
            i += 1
            while i < n:
                ch = src[i]
                out.append(ch)
                if ch == "\\" and i + 1 < n:
                    out.append(src[i + 1])
                    i += 2
                    continue
                i += 1
                if ch == q:
                    break
            continue
        out.append(src[i])
        i += 1
    return "".join(out)


def _join_spring(base: str, rel: str) -> str:
    """Spring 风格拼接：类前缀 + 方法路径（方法以 / 开头仍拼接）。"""
    b = (base or "").strip()
    r = (rel or "").strip()
    if not b:
        return r or "/"
    if not r:
        return b
    return (b.rstrip("/") + "/" + r.lstrip("/")).replace("//", "/")


def _normalize_path(path: str) -> str:
    p = _PATH_VAR_RE.sub(r"{\1}", path or "/")
    if not p.startswith("/"):
        p = "/" + p
    return p.rstrip("/") or "/"


def _surface_for(path: str) -> str:
    p = path.lower()
    if p.startswith("/api/admin"):
        return "admin"
    if p.startswith("/api/gate"):
        return "gate"
    if p.startswith("/api/auth") or p.startswith("/api/profile"):
        return "baseline"
    if p in ("/api/meta", "/api/upload", "/api/items") or p.startswith("/api/items"):
        return "baseline"
    return "portal"


def _parse_map_args(kind: str, args: str | None) -> tuple[str, str]:
    http = kind.upper() if kind != "Request" else "GET"
    path = ""
    raw = (args or "").strip()
    if raw:
        m = _METHOD_IN_ARGS_RE.search(raw)
        if m:
            http = m.group(1).upper()
        pm = _PATH_IN_ARGS_RE.search(raw)
        if pm:
            path = next(g for g in pm.groups() if g is not None)
    return http, path


def _next_handler(src: str, start: int) -> str | None:
    """mapping 结束后找下一个方法名；若是类级 RequestMapping 则返回 None。"""
    rest = src[start:]
    if re.match(r"\s*(?:public\s+|final\s+)*class\b", rest):
        return None
    # 截到下一个 Mapping / class，避免跨方法吞吞
    cut = re.search(r"@(?:Get|Post|Put|Patch|Delete|Request)Mapping\b|(?:public\s+)?class\b", rest[1:])
    window = rest if not cut else rest[: cut.start() + 1]
    for m in _HANDLER_RE.finditer(window):
        name = m.group(2)
        if name in _SKIP_HANDLER:
            continue
        # 返回类型片段里不应像语句
        ret = m.group(1)
        if "{" in ret or ";" in ret:
            continue
        return name
    return None


def _flow_keys_for(path: str, method_name: str, flow_api: dict[str, Any]) -> list[str]:
    hits: list[str] = []
    path_l = path.lower()
    name_l = method_name.lower()
    for key, rule in (flow_api or {}).items():
        if not isinstance(rule, dict):
            continue
        for need in rule.get("need") or []:
            token = str(need).strip().lower()
            if not token:
                continue
            if token.startswith("/") and token in path_l:
                hits.append(key)
                break
            if not token.startswith("/") and (token in name_l or token in path_l):
                hits.append(key)
                break
    seen: set[str] = set()
    out: list[str] = []
    for k in hits:
        if k not in seen:
            seen.add(k)
            out.append(k)
    return out


def parse_controller_source(
    src: str, *, rel_file: str, flow_api: dict[str, Any] | None = None
) -> dict[str, Any] | None:
    clean = _strip_java_noise(src)
    cm = _CLASS_RE.search(clean)
    if not cm:
        return None
    class_name = cm.group(1)
    if "Controller" not in class_name and "@RestController" not in clean:
        return None

    class_base = ""
    before = clean[: cm.start()]
    for m in _CLASS_REQ_RE.finditer(before):
        class_base = m.group(1)

    endpoints: list[dict[str, Any]] = []
    for m in _MAP_HEAD_RE.finditer(clean):
        kind, args = m.group(1), m.group(2)
        handler = _next_handler(clean, m.end())
        if handler is None:
            continue
        http, rel = _parse_map_args(kind, args)
        full = _normalize_path(_join_spring(class_base, rel))
        surface = _surface_for(full)
        endpoints.append(
            {
                "method": http,
                "path": full,
                "handler": handler,
                "surface": surface,
                "surface_label": _SURFACE_LABEL.get(surface, surface),
                "flow_keys": _flow_keys_for(full, handler, flow_api or {}),
            }
        )

    if not endpoints:
        return None

    return {
        "controller": class_name,
        "file": rel_file.replace("\\", "/"),
        "base": _normalize_path(class_base) if class_base else "",
        "endpoints": endpoints,
    }


def load_api_inventory(workspace: Path, spec: dict[str, Any] | None = None) -> dict[str, Any] | None:
    """扫描 workspace 下 Controller，返回分组清单。无 Java 控制器时返回 None。"""
    be = workspace / "backend" / "src" / "main" / "java"
    if not be.is_dir():
        return None

    flow_api = ((spec or {}).get("gate") or {}).get("flow_api") or {}
    controllers: list[dict[str, Any]] = []
    for path in sorted(be.rglob("*Controller.java")):
        try:
            rel = str(path.relative_to(workspace))
        except ValueError:
            rel = path.name
        src = path.read_text(encoding="utf-8", errors="ignore")
        parsed = parse_controller_source(src, rel_file=rel, flow_api=flow_api)
        if parsed:
            controllers.append(parsed)

    if not controllers:
        return None

    all_eps: list[dict[str, Any]] = []
    for c in controllers:
        for ep in c["endpoints"]:
            all_eps.append({**ep, "controller": c["controller"], "file": c["file"]})

    by_surface: dict[str, int] = {}
    for ep in all_eps:
        by_surface[ep["surface"]] = by_surface.get(ep["surface"], 0) + 1

    return {
        "controllers": controllers,
        "endpoints": all_eps,
        "count": len(all_eps),
        "controller_count": len(controllers),
        "by_surface": by_surface,
        "flow_marked": sum(1 for ep in all_eps if ep.get("flow_keys")),
        "flow_api_keys": list(flow_api.keys()) if isinstance(flow_api, dict) else [],
        "surfaces": [
            {"id": sid, "label": _SURFACE_LABEL.get(sid, sid), "count": by_surface.get(sid, 0)}
            for sid in ("portal", "admin", "baseline", "gate")
            if by_surface.get(sid)
        ],
    }
