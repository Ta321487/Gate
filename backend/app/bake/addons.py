"""Bake：按需实现开关叠层（与 persistence 正交；复用 _merge_tree）。"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from app.bake.stack_scan import normalize_ai_assistant, normalize_spring_security

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


def resolve_ai_assistant(spec: dict) -> bool:
    """从 spec 顶层或 addons 取 AI 助手开关（能力岛在 baseline，开则挂 cap/SQL/菜单）。"""
    if spec.get("ai_assistant") is not None:
        return normalize_ai_assistant(spec.get("ai_assistant"))
    addons = spec.get("addons")
    if isinstance(addons, dict) and "ai_assistant" in addons:
        raw = addons["ai_assistant"]
        if isinstance(raw, dict):
            return normalize_ai_assistant(raw.get("enabled"))
        return normalize_ai_assistant(raw)
    caps = spec.get("capabilities") or []
    if "ai_assistant" in caps:
        return True
    schema = spec.get("schema") if isinstance(spec.get("schema"), dict) else {}
    return "ai_assistant" in (schema.get("capabilities") or [])


def apply_addons_overlays(dest: Path, spec: dict, *, merge_tree) -> dict[str, Any]:
    """按 spec.addons / spring_security 叠按需实现；回写归一化后的字段。"""
    enabled = resolve_spring_security(spec)
    ai_on = resolve_ai_assistant(spec)
    addons = dict(spec.get("addons") or {}) if isinstance(spec.get("addons"), dict) else {}
    addons["spring_security"] = enabled
    addons["ai_assistant"] = ai_on
    spec["addons"] = addons
    spec["spring_security"] = enabled
    spec["ai_assistant"] = ai_on
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
    """返回 (backend_stack_cell, auth_line, faq)。正文真源：能力说明卡 spring_security。"""
    from app.services import cap_cards as cards

    return cards.security_auth_bits(enabled, persistence_backend)


def ai_assistant_readme_bits(enabled: bool) -> str:
    """返回 README FAQ 段（空=未启用）。正文真源：能力说明卡 ai_assistant。"""
    from app.services import cap_cards as cards

    return cards.readme_faq_body("ai_assistant", enabled=enabled)
