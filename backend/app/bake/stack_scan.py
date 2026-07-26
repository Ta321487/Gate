"""开题技术栈扫描（单一真源；与 scene_scan 独立）。

复用 scene_scan.copy_scan_text / scan_has；不驱动场景或 ARCH-*。
"""

from __future__ import annotations

from typing import Any, Literal  # Any：normalize_spring_security 入参

from app.bake.scene_scan import copy_scan_text, scan_has

Persistence = Literal["jdbc", "mybatis"]

MYBATIS_HINTS = (
    "MyBatis",
    "mybatis",
    "Mybatis-Plus",
    "mybatis-plus",
    "PageHelper",
    "pagehelper",
    "Mapper 接口",
    "Mapper接口",
)
JDBC_HINTS = (
    "JdbcTemplate",
    "jdbcTemplate",
    "Spring JDBC",
    "spring-jdbc",
    "SpringJdbc",
)
UNSUPPORTED_HINTS = (
    ("Django", "Django"),
    (".NET", ".NET"),
    ("ASP.NET", "ASP.NET"),
    ("Android", "Android"),
    ("Flutter", "Flutter"),
    ("微信小程序", "微信小程序"),
    ("uni-app", "uni-app"),
    ("UniApp", "uni-app"),
)
# 规划内未落地 / 不能静默冒充已对齐
UNDELIVERED_STACK_HINTS = (
    ("Thymeleaf", "Thymeleaf（SSR 未落地，实包仍为 Vue 分离）"),
    ("AdminLTE", "AdminLTE（SSR 未落地，实包仍为 Vue 分离）"),
    ("服务端渲染", "服务端渲染（SSR 未落地，实包仍为 Vue 分离）"),
    ("SSR", "SSR（未落地，实包仍为 Vue 分离）"),
    ("JPA", "JPA（未落地，实包 persistence 仍为 JdbcTemplate/MyBatis）"),
    ("Hibernate", "Hibernate（未落地，实包 persistence 仍为 JdbcTemplate/MyBatis）"),
    ("Spring Data JPA", "Spring Data JPA（未落地，实包 persistence 仍为 JdbcTemplate/MyBatis）"),
)
SECURITY_HINTS = ("Spring Security", "spring-security", "SpringSecurity")
ECHARTS_HINTS = ("ECharts", "echarts", "Echarts")

PERSISTENCE_MODES = frozenset({"jdbc", "mybatis"})
DEFAULT_PERSISTENCE: Persistence = "jdbc"
DEFAULT_SPINE = "spa"
DEFAULT_SPRING_SECURITY = False


def normalize_persistence(mode: str | None) -> Persistence:
    m = (mode or DEFAULT_PERSISTENCE).strip().lower()
    return m if m in PERSISTENCE_MODES else DEFAULT_PERSISTENCE  # type: ignore[return-value]


def normalize_spine(mode: str | None) -> str:
    """现网仅 spa；ssr 未落地前一律落 spa。"""
    m = (mode or DEFAULT_SPINE).strip().lower()
    return DEFAULT_SPINE if m != "spa" else m


def normalize_spring_security(flag: Any = None) -> bool:
    """按需开关：开题点名推荐开；未写清默认关。"""
    if flag is None:
        return DEFAULT_SPRING_SECURITY
    if isinstance(flag, bool):
        return flag
    if isinstance(flag, (int, float)):
        return bool(flag)
    s = str(flag).strip().lower()
    if s in ("1", "true", "yes", "on", "y"):
        return True
    if s in ("0", "false", "no", "off", "n", ""):
        return False
    return DEFAULT_SPRING_SECURITY


def scan_stack(title: str, proposal_text: str = "") -> dict[str, Any]:
    """扫题名+正文 → persistence / 按需开关推荐与偏差提示（不改开题）。"""
    text = copy_scan_text(title, proposal_text)
    warnings: list[str] = []
    hits: list[str] = []

    want_mybatis = scan_has(text, MYBATIS_HINTS)
    want_jdbc = scan_has(text, JDBC_HINTS)
    if want_mybatis:
        hits.append("MyBatis")
    if want_jdbc:
        hits.append("JdbcTemplate")

    persistence: Persistence = "mybatis" if want_mybatis else DEFAULT_PERSISTENCE
    # 同时点名时开题写了 MyBatis 优先（已可 bake）
    if want_mybatis and want_jdbc:
        persistence = "mybatis"

    for needle, label in UNSUPPORTED_HINTS:
        if needle in text:
            warnings.append(f"开题点名「{label}」，工厂当前不支持该技术主线")
            if label not in hits:
                hits.append(label)

    for needle, tip in UNDELIVERED_STACK_HINTS:
        if needle in text:
            warnings.append(f"开题点名「{needle}」：{tip}")
            if needle not in hits:
                hits.append(needle)

    addons: dict[str, Any] = {}
    want_security = scan_has(text, SECURITY_HINTS)
    spring_security = want_security  # 点名且已可 bake → 推荐开
    if want_security:
        hits.append("Spring Security")
        addons["spring_security"] = {
            "named": True,
            "deliverable": True,
            "recommended": True,
            "hint": "开题点名 Spring Security，将启用过滤器链 + HttpSession 鉴权",
        }
    if scan_has(text, ECHARTS_HINTS):
        hits.append("ECharts")
        addons["echarts"] = {
            "named": True,
            "deliverable": True,
            "hint": "ECharts 已在基线常驻，论文/README 可写",
        }

    return {
        "spine": DEFAULT_SPINE,
        "persistence": persistence,
        "recommended_persistence": persistence,
        "spring_security": spring_security,
        "recommended_spring_security": spring_security,
        "hits": hits,
        "warnings": warnings,
        "addons": addons,
    }
