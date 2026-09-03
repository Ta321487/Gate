"""答辩 PPT Plan：页级 TaskUnit，挂 unit_flow runner（非第二套编排）。"""

from __future__ import annotations

from typing import Any

from app.llm.unit_flow.models import DeliveryPlan, FrozenSpec, TaskUnit, UnitKind, UnitStatus
from app.models import Project

from .themes import PPT_UNIT_DEFS


def _menu_labels(menus: Any, limit: int = 10) -> list[str]:
    labels: list[str] = []

    def walk(node: Any) -> None:
        if len(labels) >= limit:
            return
        if isinstance(node, dict):
            lab = node.get("label") or node.get("title") or node.get("name")
            key = node.get("key") or node.get("id")
            if lab and key not in ("home", "dashboard"):
                labels.append(str(lab))
            for child in node.get("children") or node.get("items") or []:
                walk(child)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(menus)
    return labels[:limit]


def _persistence_label(persistence: str) -> str:
    p = (persistence or "jdbc").lower()
    return {
        "jdbc": "JdbcTemplate（手写分页）",
        "mybatis": "MyBatis + PageHelper",
        "jpa": "Spring Data JPA",
    }.get(p, p)


def _tech_allowlist(persistence: str, spring_security: bool) -> list[str]:
    out = [
        "Spring Boot",
        "Vue",
        "Vue 3",
        "Element Plus",
        "MySQL",
        "JdbcTemplate",
        "MyBatis",
        "PageHelper",
        "JPA",
        "Spring Data JPA",
        "jdbc",
        "mybatis",
        "jpa",
        "security",
        "Spring Security",
    ]
    out.append(_persistence_label(persistence))
    out.append(persistence or "jdbc")
    if spring_security:
        out.append("Spring Security")
    return out


def _proposal_snip(proposal: str, max_len: int = 72) -> str:
    text = " ".join(str(proposal or "").split())
    if not text:
        return "围绕开题材料中的业务背景与痛点展开"
    return text[:max_len] + ("…" if len(text) > max_len else "")


def _testcase_rows(tc: Any, limit: int = 6) -> list[list[str]]:
    rows_out: list[list[str]] = []
    if not isinstance(tc, dict):
        return rows_out
    rows = tc.get("rows") or tc.get("cases") or tc.get("items") or []
    for r in rows[:limit]:
        if isinstance(r, dict):
            name = str(r.get("name") or r.get("title") or r.get("case") or "用例")
            steps = str(r.get("steps") or r.get("step") or r.get("summary") or "按主路径操作")
            expect = str(r.get("expect") or r.get("expected") or r.get("result") or "状态正确")
            rows_out.append([name[:40], steps[:60], expect[:40]])
        elif isinstance(r, (list, tuple)) and len(r) >= 2:
            rows_out.append([str(x)[:60] for x in list(r)[:3]])
    return rows_out


def _bullet(bid: str, text: str, refs: list[str] | None = None) -> dict[str, Any]:
    return {"id": bid, "text": text, "locked": False, "source_refs": list(refs or [])}


def build_allowlist(ctx: dict[str, Any]) -> dict[str, Any]:
    menus = _menu_labels(ctx.get("menus"))
    persistence = str(ctx.get("persistence") or "jdbc")
    spring_security = bool(ctx.get("spring_security"))
    entities: list[str] = []
    er = ctx.get("er")
    if isinstance(er, dict):
        for t in er.get("tables") or er.get("entities") or []:
            if isinstance(t, dict):
                entities.append(str(t.get("zh") or t.get("label") or t.get("name") or ""))
    return {
        "menus": menus,
        "tech": _tech_allowlist(persistence, spring_security),
        "entities": [e for e in entities if e][:40],
        "persistence": persistence,
        "spring_security": spring_security,
    }


def build_fallback_pages(
    project: Project,
    ctx: dict[str, Any],
    *,
    cover: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    """确定性兜底文案（LLM 关/失败时用）；禁止发明栈外技术名。"""
    title = str(ctx.get("title") or project.title or "毕业设计答辩")
    proposal = str(ctx.get("proposal") or "")
    allow = build_allowlist(ctx)
    menu_labs = allow["menus"]
    persistence = allow["persistence"]
    spring_security = allow["spring_security"]
    tc_rows = _testcase_rows(ctx.get("testcases"))
    if not tc_rows:
        tc_rows = [
            ["登录", "演示账号登录", "进入工作台"],
            ["主流程", "按用例表走通", "状态正确落库"],
            ["权限", "角色切换", "菜单与操作隔离"],
        ]
    tech_rows = [
        ["后端", "Spring Boot", "与实包一致"],
        ["前端", "Vue 3 + Element Plus", "与实包一致"],
        ["持久层", _persistence_label(persistence), "跟项目 persistence"],
        ["数据库", "MySQL", "演示库种子同源"],
    ]
    if spring_security:
        tech_rows.append(["安全", "Spring Security", "开题点名 · 实包已集成"])

    return {
        "cover": {"page_id": "cover", "title": "封面", "cover": dict(cover)},
        "toc": {
            "page_id": "toc",
            "title": "目录",
            "toc_items": [
                "背景与需求",
                "方案与技术选型",
                "系统设计",
                "实现与演示",
                "测试",
                "总结与致谢",
            ],
        },
        "background": {
            "page_id": "background",
            "title": "背景与需求",
            "bullets": [
                _bullet("bg-1", _proposal_snip(proposal), ["proposal"]),
                _bullet(
                    "bg-2",
                    "目标用户与菜单能力："
                    + ("、".join(menu_labs[:5]) if menu_labs else "与实包菜单一致"),
                    ["proposal", "menu"],
                ),
                _bullet("bg-3", "非功能约束：可演示、可交付、可答辩讲解", ["proposal"]),
            ],
        },
        "tech": {
            "page_id": "tech",
            "title": "技术选型",
            "table": {"headers": ["层次", "技术", "说明"], "rows": tech_rows},
            "bullets": [
                _bullet(
                    "tech-1",
                    "技术名仅取自开题可交付项与实包扫描，禁止编造中间件",
                    ["stack"],
                )
            ],
        },
        "arch": {
            "page_id": "arch",
            "title": "系统架构",
            "bullets": [
                _bullet("arch-1", "前后端分离交付：frontend + backend + sql", ["arch"]),
                _bullet(
                    "arch-2",
                    "角色与菜单按域能力挂载"
                    + (f"（示例：{menu_labs[0]}）" if menu_labs else ""),
                    ["menu"],
                ),
                _bullet("arch-3", "数据层与门禁扫描对齐，保证可下载口径", ["gates"]),
            ],
        },
        "modules": {
            "page_id": "modules",
            "title": "功能模块",
            "bullets": [
                _bullet(
                    "mod-1",
                    "模块划分与实包菜单/能力树一致"
                    + (f"：{'、'.join(menu_labs[:4])}" if menu_labs else ""),
                    ["modules"],
                )
            ],
        },
        "er": {
            "page_id": "er",
            "title": "E-R 图",
            "bullets": [
                _bullet("er-1", "实体中文名与表结构来自实包 schema", ["schema"])
            ],
        },
        "demo": {
            "page_id": "demo",
            "title": "实现与演示",
            "bullets": [
                _bullet(
                    "demo-1",
                    "演示账号与 README 一致；截图跟 bake 种子同源",
                    ["runtime", "seed"],
                ),
                _bullet(
                    "demo-2",
                    "登录 → 主列表 → 关键业务动作（域主路径）",
                    ["flows"],
                ),
            ],
        },
        "test": {
            "page_id": "test",
            "title": "测试",
            "table": {"headers": ["用例", "步骤摘要", "预期"], "rows": tc_rows},
            "bullets": [
                _bullet("test-1", "用例要点来自产物用例表", ["testcases"])
            ],
        },
        "summary": {
            "page_id": "summary",
            "title": "总结与致谢",
            "bullets": [
                _bullet("sum-1", f"完成「{title}」的设计、实现与可演示交付"),
                _bullet("sum-2", "感谢导师与同学的指导与帮助"),
            ],
        },
    }


def build_ppt_plan(
    project: Project,
    ctx: dict[str, Any],
    *,
    cover: dict[str, Any],
) -> DeliveryPlan:
    allow = build_allowlist(ctx)
    fallbacks = build_fallback_pages(project, ctx, cover=cover)
    proposal = str(ctx.get("proposal") or "")[:6000]
    frozen = FrozenSpec(
        domain=str(ctx.get("domain") or project.domain or ""),
        title=str(ctx.get("title") or project.title or ""),
        persistence=str(ctx.get("persistence") or "jdbc"),
        spring_security=bool(ctx.get("spring_security")),
        capabilities=list(allow["menus"][:12]),
        archetypes=[str(ctx.get("archetype") or project.archetype or "")],
    )

    units: list[TaskUnit] = []
    for key, title in PPT_UNIT_DEFS:
        page_id = key.replace("ppt.", "", 1) if key.startswith("ppt.") else key
        fb = fallbacks.get(page_id) or {"page_id": page_id, "title": title}
        if page_id in ("cover", "toc"):
            units.append(
                TaskUnit(
                    id=key,
                    kind=UnitKind.ppt_page,
                    payload={
                        "page_id": page_id,
                        "page_title": title,
                        "role": page_id,
                        "deterministic": True,
                        "patch": fb,
                    },
                    source_refs=["cover"] if page_id == "cover" else ["outline"],
                    budget_chars=400,
                    status=UnitStatus.pending,
                )
            )
            continue

        bullets = fb.get("bullets") or []
        bullet_ids = [str(b.get("id")) for b in bullets if isinstance(b, dict)]
        role = "table" if fb.get("table") else "bullets"
        if page_id in ("modules", "er", "demo"):
            role = page_id
        table = fb.get("table")
        table_shape = None
        if isinstance(table, dict):
            rows = table.get("rows") or []
            headers = table.get("headers") or []
            table_shape = {
                "cols": len(headers)
                or (len(rows[0]) if rows and isinstance(rows[0], (list, tuple)) else 0),
                "rows": len(rows),
            }
        evidence_snip = {
            "menus": allow["menus"][:8],
            "tech": allow["tech"][:10],
            "entities": allow["entities"][:8],
            "proposal_head": _proposal_snip(proposal, 120),
        }
        allowed_refs = [
            "proposal",
            "menu",
            "stack",
            "modules",
            "schema",
            "testcases",
            "arch",
            "gates",
            "runtime",
            "seed",
            "flows",
        ]
        units.append(
            TaskUnit(
                id=key,
                kind=UnitKind.ppt_page,
                payload={
                    "page_id": page_id,
                    "page_title": title,
                    "role": role,
                    "bullet_ids": bullet_ids,
                    "table_shape": table_shape,
                    "allowlist": allow,
                    "allowed_refs": allowed_refs,
                    "evidence_snip": evidence_snip,
                    "fallback_patch": fb,
                    "fallback_hint": "无 LLM 时用开题∪实包确定性要点",
                },
                source_refs=["proposal", "menu", "stack"],
                budget_chars=2800 if role == "table" else 2200,
                status=UnitStatus.pending,
            )
        )

    return DeliveryPlan(frozen=frozen, units=units, proposal_excerpt=proposal)
