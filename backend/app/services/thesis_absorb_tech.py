"""终稿吸收：正文技术栈采矿（只认点名，禁止默认栈）。"""

from __future__ import annotations

import re

from app.services.proposal import strip_non_dev_sections

_TECH_HEADING_RE = re.compile(
    r"(?:相关技术|技术综述|开发工具|技术及环境|框架介绍|开发环境|关键技术|"
    r"技术选型|关键工具|运行环境|系统环境|关键语言|数据库技术|关键平台|"
    r"(?:Flask|Django|Spring|Vue|MySQL|Redis|MyBatis|Node).{0,16}(?:简介|介绍|概述))"
)


_TECH_STACK_TERMS: list[tuple[tuple[str, ...], str]] = [
    (("Spring Boot", "SpringBoot", "spring-boot"), "Spring Boot"),
    (("Spring Cloud", "SpringCloud"), "Spring Cloud"),
    (("Spring Security", "SpringSecurity"), "Spring Security"),
    (("Spring Data JPA", "spring-data-jpa", "SpringDataJPA"), "Spring Data JPA"),
    (("Spring MVC", "SpringMVC"), "Spring MVC"),
    (("Spring",), "Spring"),
    (("JdbcTemplate", "Spring JDBC", "spring-jdbc"), "JdbcTemplate"),
    (("MyBatis-Plus", "MyBatis Plus", "mybatis-plus", "MybatisPlus"), "MyBatis-Plus"),
    (("MyBatis", "mybatis"), "MyBatis"),
    (("Hibernate",), "Hibernate"),
    (("JPA",), "JPA"),
    (("Element Plus", "ElementPlus", "element-plus"), "Element Plus"),
    (("Element UI", "ElementUI", "element-ui"), "Element UI"),
    (("Ant Design Vue", "Ant Design of Vue", "ant-design-vue"), "Ant Design Vue"),
    (("Vue 3", "Vue3", "vue3", "Vue.js 3"), "Vue 3"),
    (("Vue 2", "Vue2", "vue2"), "Vue 2"),
    (("Vue.js", "VueJS"), "Vue"),
    (("Vue",), "Vue"),
    (("React", "React.js", "ReactJS"), "React"),
    (("Angular",), "Angular"),
    (("Bootstrap",), "Bootstrap"),
    (("jQuery", "JQuery"), "jQuery"),
    (("Axios",), "Axios"),
    (("ECharts", "echarts"), "ECharts"),
    (("Node.js", "NodeJS", "Node js"), "Node.js"),
    (("Express", "Express.js"), "Express"),
    (("Django",), "Django"),
    (("Flask",), "Flask"),
    (("FastAPI",), "FastAPI"),
    (("MySQL", "mysql"), "MySQL"),
    (("MariaDB",), "MariaDB"),
    (("PostgreSQL", "Postgres"), "PostgreSQL"),
    (("SQL Server", "SQLServer", "SqlServer"), "SQL Server"),
    (("Oracle",), "Oracle"),
    (("MongoDB", "Mongo DB"), "MongoDB"),
    (("Redis",), "Redis"),
    (("Maven",), "Maven"),
    (("Gradle",), "Gradle"),
    (("Tomcat",), "Tomcat"),
    (("Nginx", "NGINX"), "Nginx"),
    (("Docker",), "Docker"),
    (("微信小程序",), "微信小程序"),
    (("uni-app", "UniApp", "uniapp"), "uni-app"),
    (("Flutter",), "Flutter"),
    (("Android",), "Android"),
    ((".NET", "ASP.NET", "AspNet"), ".NET"),
    (("Java",), "Java"),
    (("TypeScript", "Typescript"), "TypeScript"),
    (("JavaScript", "Javascript"), "JavaScript"),
    (("Python",), "Python"),
]


_TECH_STACK_SUBSUMED: dict[str, tuple[str, ...]] = {
    "Spring": (
        "Spring Boot",
        "Spring Cloud",
        "Spring MVC",
        "Spring Security",
        "Spring Data JPA",
    ),
    "Vue": ("Vue 3", "Vue 2"),
    "MyBatis": ("MyBatis-Plus",),
    "JPA": ("Spring Data JPA",),
    "Hibernate": ("Spring Data JPA",),
    "JavaScript": ("TypeScript",),
}


def _find_tech_needle_pos(hay: str, hay_lower: str, needle: str) -> int:
    if not needle:
        return -1
    i = hay.find(needle)
    if i >= 0:
        return i
    if needle.isascii():
        return hay_lower.find(needle.lower())
    return -1


_TECH_NEG_BEFORE = re.compile(
    r"(?:不采用|不使用|不用|并非|没有使用|未使用|拒绝使用).{0,10}$"
)


def _tech_needle_ok(hay: str, pos: int, needle: str) -> bool:
    """短英词要求左右非 ASCII 字母数字，避免 Java⊂JavaScript、Vue⊂Vuex。"""
    if not needle.isascii() or len(needle) > 4:
        return True
    before = hay[pos - 1] if pos > 0 else " "
    after_i = pos + len(needle)
    after = hay[after_i] if after_i < len(hay) else " "
    if before.isascii() and before.isalnum():
        return False
    if after.isascii() and after.isalnum():
        return False
    return True


def _tech_negated_at(hay: str, pos: int) -> bool:
    """「不用 JdbcTemplate」等否定点名不进栈。"""
    window = hay[max(0, pos - 18) : pos]
    return bool(_TECH_NEG_BEFORE.search(window))


def _repair_tech_soft_wraps(text: str) -> str:
    """拼回 PDF 把 Vue/Spring Boot 等拆到两行的软折行。"""
    t = text or ""
    reps = (
        (r"Vue\s*[\r\n]+\s*([23３２])", r"Vue \1"),
        (r"Spring\s*[\r\n]+\s*Boot", "Spring Boot"),
        (r"Spring\s*[\r\n]+\s*Cloud", "Spring Cloud"),
        (r"Spring\s*[\r\n]+\s*MVC", "Spring MVC"),
        (r"Spring\s*[\r\n]+\s*Security", "Spring Security"),
        (r"Element\s*[\r\n]+\s*Plus", "Element Plus"),
        (r"Element\s*[\r\n]+\s*UI", "Element UI"),
        (r"MyBatis\s*[\r\n]+\s*Plus", "MyBatis-Plus"),
        (r"Node\s*[\r\n]+\s*\.?js", "Node.js"),
        (r"Spring\s*Boot", "Spring Boot"),  # SpringBoot 粘连已由针覆盖；此处收空白
    )
    for pat, repl in reps[:-1]:
        t = re.sub(pat, repl, t, flags=re.I)
    return t


def extract_tech_stack_lines(text: str, *, limit: int = 24) -> list[str]:
    """从正文采技术点名；未点名则空，禁止默认栈。"""
    raw = _repair_tech_soft_wraps(text or "")
    if not raw.strip():
        return []
    hay_lower = raw.lower()
    hits: list[tuple[int, str]] = []
    seen: set[str] = set()
    for needles, label in _TECH_STACK_TERMS:
        if label in seen:
            continue
        best = -1
        for n in needles:
            pos = _find_tech_needle_pos(raw, hay_lower, n)
            if pos < 0 or not _tech_needle_ok(raw, pos, n):
                continue
            if _tech_negated_at(raw, pos):
                continue
            if best < 0 or pos < best:
                best = pos
        if best < 0:
            continue
        seen.add(label)
        hits.append((best, label))
    hits.sort(key=lambda x: x[0])
    labels = [lab for _p, lab in hits]
    present = set(labels)
    out: list[str] = []
    for lab in labels:
        parents = _TECH_STACK_SUBSUMED.get(lab) or ()
        if any(p in present for p in parents):
            continue
        out.append(lab)
        if len(out) >= limit:
            break
    return out


_STACK_CLAIM_RE = re.compile(
    r"(?:本系统|本文|本课题|本研究|本项目).{0,48}"
    r"(?:采用|使用|基于|选用|以.{0,12}为|搭建|结合)"
)


_STACK_SURVEY_LINE_RE = re.compile(
    r"(?:主流|常见|流行|还有|或者是|例如|比如|对比|不同于|"
    r"传统(?:的)?系统|现有(?:的)?系统|其他(?:的)?系统|"
    r"可以选择|也可采用|也可以使用|分别是|包括 Vue、React)"
)


def _tech_section_lines(
    buckets: dict[str, list[tuple[str, list[str]]]],
) -> list[str]:
    parts: list[str] = []
    for heading, lines in buckets.get("discard") or []:
        h = str(heading or "")
        if not _TECH_HEADING_RE.search(h):
            continue
        parts.append(h)
        for ln in lines:
            s = str(ln or "").strip()
            if not s or _STACK_SURVEY_LINE_RE.search(s):
                continue
            parts.append(s)
    return parts


def build_tech_stack_corpus(
    *,
    buckets: dict[str, list[tuple[str, list[str]]]],
    abstract_lines: list[str],
    intro_lines: list[str],
    full_text: str,
) -> str:
    """优先「本系统采用」类陈述；陈述过少再补相关技术章非综述行。"""
    claim_parts: list[str] = []
    body = strip_non_dev_sections(full_text or "")
    for ln in body.splitlines():
        s = ln.strip()
        if s and _STACK_CLAIM_RE.search(s):
            claim_parts.append(s)
    for x in abstract_lines or []:
        s = str(x).strip()
        if s and s not in claim_parts:
            claim_parts.append(s)
    claim_blob = "\n".join(claim_parts).strip()
    # 陈述已能点名 ≥2 项技术 → 不再并入相关技术调研章
    if len(extract_tech_stack_lines(claim_blob, limit=8)) >= 2:
        return claim_blob
    parts = list(claim_parts)
    parts.extend(_tech_section_lines(buckets))
    blob = "\n".join(parts).strip()
    if len(blob) >= 12:
        return blob
    return "\n".join(x for x in (intro_lines or []) if str(x).strip())


