"""Bake：spa 内 persistence 叠层（复用 _merge_tree，不另起管线）。"""

from __future__ import annotations

import re
from pathlib import Path

from app.bake.stack_scan import normalize_persistence

# mybatis 包禁止残留的 JDBC / 过渡桥入口（洁净契约）
_JDBC_PURGE_REL = (
    "backend/src/main/java/com/thesis/config/JdbcSupport.java",
    "backend/src/main/java/com/thesis/config/MbBridge.java",
)

_MYBATIS_YML = """
# persistence=mybatis（bake 注入）
mybatis:
  mapper-locations: classpath:mapper/*.xml
  type-aliases-package: {pkg}
  configuration:
    map-underscore-to-camel-case: true
pagehelper:
  helper-dialect: mysql
  reasonable: true
  support-methods-arguments: true
"""


def apply_persistence_overlay(dest: Path, spec: dict, *, merge_tree) -> str:
    """按 spec.persistence 叠 overlay；返回归一化后的 persistence。"""
    from app.core.config import get_settings

    persistence = normalize_persistence(spec.get("persistence"))
    spec["persistence"] = persistence
    spec["spine"] = "spa"
    if persistence != "mybatis":
        return persistence

    settings = get_settings()
    overlay = settings.skeletons_dir / "overlays" / "persistence-mybatis"
    if not overlay.is_dir():
        raise FileNotFoundError(f"缺少 MyBatis 叠层: {overlay}")
    merge_tree(overlay, dest)
    purge_jdbc_persistence(dest)
    ensure_mybatis_application_yml(dest)
    return persistence


def purge_jdbc_persistence(dest: Path) -> None:
    """删掉 JdbcSupport/MbBridge；断言无 JdbcSupport / JdbcTemplate / MbBridge import。"""
    for rel in _JDBC_PURGE_REL:
        path = dest / rel
        if path.is_file():
            path.unlink()
    bad: list[str] = []
    java_root = dest / "backend" / "src" / "main" / "java"
    if java_root.is_dir():
        for path in java_root.rglob("*.java"):
            text = path.read_text(encoding="utf-8")
            if "JdbcSupport" in text and "对标原 JdbcSupport" not in text and "保证 MybatisSupport" not in text:
                # 允许注释提及旧名；禁止仍引用类
                if "import com.thesis.config.JdbcSupport" in text or "JdbcSupport.jdbc" in text:
                    bad.append(str(path.relative_to(dest)).replace("\\", "/"))
            if "import org.springframework.jdbc.core.JdbcTemplate" in text:
                bad.append(str(path.relative_to(dest)).replace("\\", "/"))
            if "import com.thesis.config.MbBridge" in text or "MbBridge." in text:
                bad.append(str(path.relative_to(dest)).replace("\\", "/"))
    if bad:
        raise RuntimeError(
            "persistence=mybatis 包仍含 JdbcSupport/JdbcTemplate/MbBridge，请补 overlay 覆盖: "
            + ", ".join(sorted(set(bad))[:12])
            + ("…" if len(set(bad)) > 12 else "")
        )


def ensure_mybatis_application_yml(dest: Path, java_package: str | None = None) -> None:
    """注入 mybatis/pagehelper 段；已存在则跳过。java_package 默认 com.thesis（重映射前）。"""
    yml = dest / "backend" / "src" / "main" / "resources" / "application.yml"
    if not yml.is_file():
        return
    text = yml.read_text(encoding="utf-8")
    if re.search(r"(?m)^mybatis:\s*$", text):
        return
    pkg = (java_package or "com.thesis").strip() or "com.thesis"
    text = text.rstrip() + "\n" + _MYBATIS_YML.format(pkg=pkg)
    yml.write_text(text, encoding="utf-8")


def persistence_readme_bits(persistence: str) -> tuple[str, str, str, str]:
    """返回 (backend_stack_cell, note, store_line, faq_mapper)。"""
    p = normalize_persistence(persistence)
    if p == "mybatis":
        return (
            "Spring Boot 3 + MyBatis + PageHelper",
            "本项目使用 **MyBatis Mapper** 访问数据库，分页用 **PageHelper**。"
            "业务入口仍是 `*Store`（薄封装），SQL 在 `mapper/*.xml` 或 Mapper 注解里。"
            "答辩请讲 Mapper，不要说成 JdbcTemplate。",
            "**\\*Store → \\*Mapper（MyBatis）**：Store 调 Mapper；分页先 `PageHelper.startPage`。"
            " XML 在 `backend/src/main/resources/mapper/`。",
            "**Q：JdbcTemplate 呢？**  \n本包持久层是 MyBatis，没有使用 `JdbcTemplate`。以 Mapper 为准。",
        )
    return (
        "Spring Boot 3 + Spring JDBC（`JdbcTemplate`）",
        "本项目**没有使用 MyBatis / Mapper 接口**。持久化统一写在 `*Store` 类里，用 `JdbcTemplate` 执行 SQL。"
        "答辩时不要说「MyBatis 自动生成 Mapper」——目录里也没有空的 `mapper`/`entity` 包。",
        "**\\*Store（JdbcTemplate）**：真正访问数据库。  \n"
        "例如 `ArchiveStore`、`TicketStore`、`OrderStore`、`SlotStore`、`UserStore`。",
        "**Q：为什么没有 Mapper 文件夹？**  \n本系统使用 `JdbcTemplate`，不生成 MyBatis Mapper。以 `*Store` 为准即可。",
    )
