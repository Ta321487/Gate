"""交付物短名：ZIP / 学生库 / Maven（ASCII；包名跟题目语义，像普通毕设）。"""

from __future__ import annotations

import re

_SLUG_RE = re.compile(r"^[a-z][a-z0-9_]{2,31}$")
# 历史工厂尾（_p215435）读旧 spec 时剥掉
_FACTORY_TAIL_RE = re.compile(r"_p[a-zA-Z0-9]{4,16}$")


def _semantic_slug(raw: str | None) -> str:
    s = (raw or "").strip().lower().replace("-", "_").replace(" ", "_")
    s = re.sub(r"[^a-z0-9_]", "", s)
    s = _FACTORY_TAIL_RE.sub("", s)
    if not s:
        return "app"
    if not s[0].isalpha():
        s = f"app_{s}"
    return s[:32].rstrip("_") or "app"


def sanitize_delivery_slug(raw: str | None, *, domain: str) -> str:
    """规范化为语义短名；非法则回落领域短码。"""
    if (raw or "").strip():
        s = _semantic_slug(raw)
        if _SLUG_RE.match(s):
            return s
    short = (domain or "DOM-GENERIC").replace("DOM-", "").lower()
    short = re.sub(r"[^a-z0-9_]", "", short) or "app"
    if not short[0].isalpha():
        short = f"app_{short}"
    return short[:32]


def project_tail(project_id: str) -> str:
    """项目 ID 末段，如 gf-20260721-215435 → 215435（仅库名 / 落盘用）。"""
    t = (project_id or "").split("-")[-1].strip()
    return t if re.match(r"^[a-zA-Z0-9]{4,16}$", t) else ""


def student_db_name(
    slug: str,
    project_id: str,
    *,
    reserved: set[str] | None = None,
) -> str:
    """学生库名：优先纯语义；本机已被占用则叠项目短尾（无 gf_ 前缀）。

    例：dorm_repair → 撞名后 dorm_repair_215435。
    """
    base = _semantic_slug(slug)[:64]
    taken = {n.lower() for n in (reserved or ()) if n}
    if base.lower() not in taken:
        return base
    tail = project_tail(project_id) or "x"
    cand = f"{base}_{tail}"[:64]
    if cand.lower() not in taken:
        return cand
    for i in range(2, 100):
        c = f"{base}_{tail}_{i}"[:64]
        if c.lower() not in taken:
            return c
    return cand


def zip_download_name(slug: str, project_id: str = "") -> str:
    """学生下载名：dorm-repair-app.zip（无流水号）。project_id 保留兼容，忽略。"""
    _ = project_id
    kebab = _semantic_slug(slug).replace("_", "-").strip("-") or "app"
    if not kebab.endswith("-app"):
        kebab = f"{kebab}-app"
    return f"{kebab}.zip"


def zip_storage_name(project_id: str, slug: str) -> str:
    """工作区落盘名（已含项目 ID，防覆盖）。"""
    kebab = _semantic_slug(slug).replace("_", "-").strip("-") or "app"
    return f"{project_id}-{kebab}.zip"


def maven_artifact_id(slug: str, project_id: str = "") -> str:
    """Maven artifactId，与下载 ZIP 主干一致。"""
    return zip_download_name(slug, project_id).removesuffix(".zip")


def java_coords_from_slug(slug: str, *, project_id: str = "") -> tuple[str, str, str]:
    """由交付 slug 推导 (package, ApplicationClass, artifactId)。

    包名只跟题目语义：com.campus.dorm_repair，不加项目流水号。
    """
    _ = project_id
    raw = _semantic_slug(slug)
    pkg = f"com.campus.{raw}"
    parts = [p for p in raw.split("_") if p]
    pascal = "".join(p[:1].upper() + p[1:] for p in parts) or "App"
    app_class = f"{pascal}Application"
    return pkg, app_class, maven_artifact_id(raw)


def resolve_slug_from_spec(spec: dict | None, domain: str) -> str:
    spec = spec or {}
    meta = spec.get("match_meta") if isinstance(spec.get("match_meta"), dict) else {}
    raw = spec.get("delivery_slug") or meta.get("delivery_slug")
    return sanitize_delivery_slug(str(raw) if raw else None, domain=domain or "DOM-GENERIC")
