"""Bake：按需实现开关叠层（与 persistence 正交；复用 _merge_tree）。"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from app.bake.stack_scan import normalize_spring_security

_CRYPTO_DEP = """    <!-- 仅 BCrypt 编码器，不启用 Spring Security 过滤器链 -->
    <dependency>
      <groupId>org.springframework.security</groupId>
      <artifactId>spring-security-crypto</artifactId>
    </dependency>"""

_STARTER_DEP = """    <!-- Spring Security：过滤器链 + 会话鉴权（含 crypto） -->
    <dependency>
      <groupId>org.springframework.boot</groupId>
      <artifactId>spring-boot-starter-security</artifactId>
    </dependency>"""


def resolve_spring_security(spec: dict) -> bool:
    """从 spec 顶层或 addons 取开关。"""
    if spec.get("spring_security") is not None:
        return normalize_spring_security(spec.get("spring_security"))
    addons = spec.get("addons")
    if isinstance(addons, dict) and "spring_security" in addons:
        raw = addons["spring_security"]
        if isinstance(raw, dict):
            return normalize_spring_security(raw.get("enabled"))
        return normalize_spring_security(raw)
    return False


def apply_addons_overlays(dest: Path, spec: dict, *, merge_tree) -> dict[str, Any]:
    """按 spec.addons / spring_security 叠按需实现；回写归一化后的字段。"""
    enabled = resolve_spring_security(spec)
    addons = dict(spec.get("addons") or {}) if isinstance(spec.get("addons"), dict) else {}
    addons["spring_security"] = enabled
    spec["addons"] = addons
    spec["spring_security"] = enabled
    if enabled:
        apply_spring_security_overlay(dest, merge_tree=merge_tree)
    return addons


def apply_spring_security_overlay(dest: Path, *, merge_tree) -> None:
    from app.core.config import get_settings

    settings = get_settings()
    overlay = settings.skeletons_dir / "overlays" / "addon-spring-security"
    if not overlay.is_dir():
        raise FileNotFoundError(f"缺少 Spring Security 叠层: {overlay}")
    merge_tree(overlay, dest)
    ensure_security_pom(dest)
    assert_security_files(dest)


def ensure_security_pom(dest: Path) -> None:
    """crypto-only → spring-boot-starter-security（兼容 jdbc / mybatis / jpa 的 pom）。"""
    pom = dest / "backend" / "pom.xml"
    if not pom.is_file():
        raise FileNotFoundError(f"缺少 pom.xml: {pom}")
    text = pom.read_text(encoding="utf-8")
    if "spring-boot-starter-security" in text:
        return
    if _CRYPTO_DEP in text:
        text = text.replace(_CRYPTO_DEP, _STARTER_DEP)
    elif "spring-security-crypto" in text:
        text = re.sub(
            r"\s*<!--[^>]*-->\s*"
            r"<dependency>\s*"
            r"<groupId>org\.springframework\.security</groupId>\s*"
            r"<artifactId>spring-security-crypto</artifactId>\s*"
            r"</dependency>",
            "\n" + _STARTER_DEP,
            text,
            count=1,
            flags=re.IGNORECASE,
        )
        if "spring-boot-starter-security" not in text:
            # 粗替换：artifactId + groupId（仅第一处 crypto）
            text = re.sub(
                r"(<dependency>\s*<groupId>)org\.springframework\.security(</groupId>\s*"
                r"<artifactId>)spring-security-crypto(</artifactId>\s*</dependency>)",
                r"\1org.springframework.boot\2spring-boot-starter-security\3",
                text,
                count=1,
            )
    else:
        text = text.replace("</dependencies>", _STARTER_DEP + "\n  </dependencies>", 1)
    if "spring-boot-starter-security" not in text:
        raise RuntimeError("未能把 spring-boot-starter-security 写入 pom.xml")
    pom.write_text(text, encoding="utf-8")


def assert_security_files(dest: Path) -> None:
    be = dest / "backend" / "src" / "main" / "java"
    java_names = {p.name for p in be.rglob("*.java")} if be.is_dir() else set()
    missing = [n for n in ("SecurityConfig.java", "SessionAuthFilter.java") if n not in java_names]
    if missing:
        raise RuntimeError("Spring Security 叠层缺少: " + ", ".join(missing))


def security_readme_bits(enabled: bool, persistence_backend: str) -> tuple[str, str, str]:
    """返回 (backend_stack_cell, auth_line, faq)。"""
    if enabled:
        backend = persistence_backend.rstrip("。") + " + Spring Security"
        auth = (
            "登录鉴权由 **Spring Security 过滤器链** 与 **HttpSession** 共同完成；"
            "`SessionAuthFilter` 把会话用户桥进 Security 上下文，角色细粒度仍由业务层 `AdminAuth` 校验。"
        )
        faq = (
            "**Q：Spring Security 做了什么？**  \n"
            "启用了 `spring-boot-starter-security` 与 `SecurityFilterChain`："
            "未登录访问受保护接口返回 401；公开接口（登录/验证码、游客可读列表等）在配置中放行。"
            "答辩请讲过滤器链 + Session，不要只说「用了 crypto」。"
        )
        return backend, auth, faq
    auth = (
        "前后端分离：Vue 负责界面，Spring Boot 提供 REST API，"
        "**HttpSession** 维持登录态（本包未启用 Spring Security 过滤器链）。"
    )
    return persistence_backend, auth, ""
