"""开题技术栈扫描（单一真源；与 scene_scan 独立）。

复用 scene_scan.copy_scan_text / scan_has；不驱动场景或 ARCH-*。
按需开关（Security / AI 助手等）扫词真源见 services.addon_suggest。
"""

from __future__ import annotations

from typing import Any, Literal  # Any：normalize_* 入参

from app.bake.scene_scan import copy_scan_text, scan_has

Persistence = Literal["jdbc", "mybatis", "jpa"]

MYBATIS_HINTS = (
    "MyBatis",
    "mybatis",
    "MyBatis-Plus",
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
JPA_HINTS = (
    "Spring Data JPA",
    "spring-data-jpa",
    "SpringDataJPA",
    "Hibernate",
    "JPA",
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
# 规划内未落地 / 不能静默冒充已对齐（JPA 已可 bake，勿再列入）
UNDELIVERED_STACK_HINTS = (
    ("Thymeleaf", "Thymeleaf（SSR 未落地，实包仍为 Vue 分离）"),
    ("AdminLTE", "AdminLTE（SSR 未落地，实包仍为 Vue 分离）"),
    ("服务端渲染", "服务端渲染（SSR 未落地，实包仍为 Vue 分离）"),
    ("SSR", "SSR（未落地，实包仍为 Vue 分离）"),
)

PERSISTENCE_MODES = frozenset({"jdbc", "mybatis", "jpa"})
DEFAULT_PERSISTENCE: Persistence = "jdbc"
DEFAULT_SPINE = "spa"
DEFAULT_SPRING_SECURITY = False
DEFAULT_AI_ASSISTANT = False


def normalize_persistence(mode: str | None) -> Persistence:
    m = (mode or DEFAULT_PERSISTENCE).strip().lower()
    if m in ("spring_data_jpa", "spring-data-jpa", "hibernate"):
        return "jpa"
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


def normalize_ai_assistant(flag: Any = None) -> bool:
    """AI 助手按需开关：开题点名推荐开；未写清默认关。"""
    if flag is None:
        return DEFAULT_AI_ASSISTANT
    if isinstance(flag, bool):
        return flag
    if isinstance(flag, (int, float)):
        return bool(flag)
    s = str(flag).strip().lower()
    if s in ("1", "true", "yes", "on", "y"):
        return True
    if s in ("0", "false", "no", "off", "n", ""):
        return False
    return DEFAULT_AI_ASSISTANT


def scan_stack(title: str, proposal_text: str = "") -> dict[str, Any]:
    """扫题名+正文 → persistence / 按需开关推荐与偏差提示（不改开题）。"""
    from app.services.addon_suggest import suggest_addons
    from app.services.proposal import strip_non_dev_sections

    # 与匹配同裁：参考文献里的「微信小程序」等勿当技术主线点名
    body = strip_non_dev_sections(proposal_text or "")
    text = copy_scan_text(title, body)
    warnings: list[str] = []
    hits: list[str] = []

    want_jpa = scan_has(text, JPA_HINTS)
    want_mybatis = scan_has(text, MYBATIS_HINTS)
    want_jdbc = scan_has(text, JDBC_HINTS)
    if want_jpa:
        hits.append("JPA")
    if want_mybatis:
        hits.append("MyBatis")
    if want_jdbc:
        hits.append("JdbcTemplate")

    # 开题优先：JPA > MyBatis > 默认 jdbc（已可 bake 的跟开题）
    persistence: Persistence = DEFAULT_PERSISTENCE
    if want_jpa:
        persistence = "jpa"
    elif want_mybatis:
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

    suggestions = suggest_addons(title, proposal_text)
    addons: dict[str, Any] = {}
    spring_security = DEFAULT_SPRING_SECURITY
    ai_assistant = DEFAULT_AI_ASSISTANT

    for sug in suggestions:
        aid = sug.get("addon_id") or ""
        label = sug.get("addon_label") or aid
        recommended = bool(sug.get("recommended")) and bool(sug.get("deliverable", True))
        entry = {
            "named": True,
            "deliverable": bool(sug.get("deliverable", True)),
            "recommended": recommended,
            "hint": sug.get("summary_zh") or "",
            "evidences": list(sug.get("evidences") or []),
        }
        addons[aid] = entry
        if aid == "spring_security":
            spring_security = recommended
            if "Spring Security" not in hits:
                hits.append("Spring Security")
        elif aid == "ai_assistant":
            ai_assistant = recommended
            if "AI助手" not in hits:
                hits.append("AI助手")
        elif aid == "echarts":
            if "ECharts" not in hits:
                hits.append("ECharts")
        elif label and label not in hits:
            hits.append(label)

    return {
        "spine": DEFAULT_SPINE,
        "persistence": persistence,
        "recommended_persistence": persistence,
        "spring_security": spring_security,
        "recommended_spring_security": spring_security,
        "ai_assistant": ai_assistant,
        "recommended_ai_assistant": ai_assistant,
        "hits": hits,
        "warnings": warnings,
        "addons": addons,
        "addon_suggestions": suggestions,
    }
