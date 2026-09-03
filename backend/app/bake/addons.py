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


def ai_assistant_readme_bits(enabled: bool) -> str:
    """返回 README FAQ 段（空=未启用）。"""
    if not enabled:
        return ""
    return (
        "**Q：AI 智能助手怎么用？**  \n"
        "门户右下角悬浮按钮打开对话弹窗（亦可从 AI 助手说明页一键打开）。"
        "本包用 **Spring AI**（`spring-ai-deepseek`）对接 **DeepSeek** 大模型"
        "（`DEEPSEEK_API_KEY` 环境变量自配）。"
        "**仅当命中知识库条目或可只读查询到业务数据时**才会调用大模型，并按摘录/数据回答；"
        "可查询本系统已开通能力下的分类与在架条目、本人购物车/订单、本人借阅或报修等办理进度（只读，不下单不改状态）。"
        "未命中或无关闲聊（写诗/写代码等）固定提示换问法，不自由发挥。"
        "无 Key 时直接返回知识条目原文或业务数据摘要。"
        "调用入口唯一：`DeepSeekClient` → `DeepSeekChatModel`；业务摘录唯一：`AiBizContext`（复用 Archive/Order/Ticket/Doclib Store）。"
        "支持知识条目维护、热门问答、满意度反馈、浏览器语音播报，"
        "以及图片按品类匹配知识的入口。"
        "管理端「AI知识库」维护 FAQ 与查看咨询统计，不是用户同款聊天窗。"
        "答辩请讲「Spring AI + DeepSeek + 知识表约束」，"
        "不要写成自研大模型或 CNN 视觉引擎。\n"
    )
