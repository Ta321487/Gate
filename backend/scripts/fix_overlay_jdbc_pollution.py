"""把 mybatis/jpa 叠层里误拷的 JDBC 门面改回 MbSql / JpaDb。

不改业务逻辑，只换 import 与 db() 门面；TicketSql.db()（mybatis 无此方法）改为 MybatisSupport.db()。
"""

from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
MYBATIS = REPO / "skeletons/overlays/persistence-mybatis/backend/src/main/java"
JPA = REPO / "skeletons/overlays/persistence-jpa/backend/src/main/java"


def _rewrite_imports_mybatis(text: str) -> str:
    text = text.replace(
        "import com.thesis.config.JdbcSupport;\n",
        "import com.thesis.config.MbSql;\nimport com.thesis.config.MybatisSupport;\n",
    )
    text = text.replace("import org.springframework.jdbc.core.JdbcTemplate;\n", "")
    text = text.replace(
        "import org.springframework.jdbc.support.GeneratedKeyHolder;\n",
        "import com.thesis.config.GeneratedKeyHolder;\n",
    )
    text = text.replace(
        "import org.springframework.jdbc.support.KeyHolder;\n",
        "import com.thesis.config.KeyHolder;\n",
    )
    # 若已有 MbSql/MybatisSupport 重复 import，去重
    text = _dedupe_imports(text)
    return text


def _rewrite_imports_jpa(text: str) -> str:
    text = text.replace(
        "import com.thesis.config.JdbcSupport;\n",
        "import com.thesis.config.JpaDb;\nimport com.thesis.config.JpaSupport;\n",
    )
    text = text.replace("import org.springframework.jdbc.core.JdbcTemplate;\n", "")
    text = text.replace(
        "import org.springframework.jdbc.support.GeneratedKeyHolder;\n",
        "import com.thesis.config.GeneratedKeyHolder;\n",
    )
    text = text.replace(
        "import org.springframework.jdbc.support.KeyHolder;\n",
        "import com.thesis.config.KeyHolder;\n",
    )
    text = _dedupe_imports(text)
    return text


def _dedupe_imports(text: str) -> str:
    lines = text.splitlines(keepends=True)
    seen: set[str] = set()
    out: list[str] = []
    for ln in lines:
        if ln.startswith("import "):
            key = ln.strip()
            if key in seen:
                continue
            seen.add(key)
        out.append(ln)
    return "".join(out)


def _rewrite_db_mybatis(text: str) -> str:
    text = re.sub(
        r"private static JdbcTemplate db\(\)\s*\{\s*return JdbcSupport\.jdbc\(\);\s*\}",
        "private static MbSql db() {\n        return MybatisSupport.db();\n    }",
        text,
    )
    text = re.sub(
        r"static JdbcTemplate db\(\)\s*\{\s*return JdbcSupport\.jdbc\(\);\s*\}",
        "static MbSql db() {\n        return MybatisSupport.db();\n    }",
        text,
    )
    # 残留直接调用
    text = text.replace("JdbcSupport.jdbc()", "MybatisSupport.db()")
    text = text.replace("TicketSql.db()", "MybatisSupport.db()")
    text = text.replace("com.thesis.capability.TicketSql.db()", "MybatisSupport.db()")
    # 若用了 MybatisSupport.db 但缺 import
    if "MybatisSupport." in text and "import com.thesis.config.MybatisSupport;" not in text:
        text = text.replace(
            "package ",
            "package ",
            1,
        )
        text = re.sub(
            r"(package [\w.]+;\s*\n)",
            r"\1\nimport com.thesis.config.MbSql;\nimport com.thesis.config.MybatisSupport;\n",
            text,
            count=1,
        )
        text = _dedupe_imports(text)
    if "MbSql" in text and "import com.thesis.config.MbSql;" not in text:
        text = re.sub(
            r"(package [\w.]+;\s*\n)",
            r"\1\nimport com.thesis.config.MbSql;\n",
            text,
            count=1,
        )
        text = _dedupe_imports(text)
    return text


def _rewrite_db_jpa(text: str) -> str:
    text = re.sub(
        r"private static JdbcTemplate db\(\)\s*\{\s*return JdbcSupport\.jdbc\(\);\s*\}",
        "private static JpaDb db() {\n        return JpaSupport.db();\n    }",
        text,
    )
    text = re.sub(
        r"static JdbcTemplate db\(\)\s*\{\s*return JdbcSupport\.jdbc\(\);\s*\}",
        "static JpaDb db() {\n        return JpaSupport.db();\n    }",
        text,
    )
    text = text.replace("JdbcSupport.jdbc()", "JpaSupport.db()")
    # TicketSql.db() 在 jpa 叠层合法（返回 JpaDb），保留
    if "JpaSupport." in text and "import com.thesis.config.JpaSupport;" not in text:
        text = re.sub(
            r"(package [\w.]+;\s*\n)",
            r"\1\nimport com.thesis.config.JpaDb;\nimport com.thesis.config.JpaSupport;\n",
            text,
            count=1,
        )
        text = _dedupe_imports(text)
    if "JpaDb" in text and "import com.thesis.config.JpaDb;" not in text:
        text = re.sub(
            r"(package [\w.]+;\s*\n)",
            r"\1\nimport com.thesis.config.JpaDb;\n",
            text,
            count=1,
        )
        text = _dedupe_imports(text)
    return text


def _needs_fix(text: str, *, mybatis: bool) -> bool:
    if "import com.thesis.config.JdbcSupport" in text:
        return True
    if "JdbcSupport.jdbc" in text:
        return True
    if "import org.springframework.jdbc.core.JdbcTemplate" in text:
        return True
    if "JdbcTemplate" in text and "db()" in text:
        return True
    if mybatis and "TicketSql.db()" in text:
        return True
    return False


def fix_tree(root: Path, *, mybatis: bool) -> list[str]:
    changed: list[str] = []
    for path in sorted(root.rglob("*.java")):
        # MybatisSupport 注释里会提 JdbcSupport，跳过
        if path.name == "MybatisSupport.java":
            continue
        old = path.read_text(encoding="utf-8")
        if not _needs_fix(old, mybatis=mybatis):
            continue
        text = old
        if mybatis:
            text = _rewrite_imports_mybatis(text)
            text = _rewrite_db_mybatis(text)
        else:
            text = _rewrite_imports_jpa(text)
            text = _rewrite_db_jpa(text)
        if text != old:
            path.write_text(text, encoding="utf-8", newline="\n")
            changed.append(str(path.relative_to(root)).replace("\\", "/"))
    return changed


def main() -> None:
    mb = fix_tree(MYBATIS, mybatis=True)
    jp = fix_tree(JPA, mybatis=False)
    print("mybatis fixed:", len(mb))
    for p in mb:
        print(" ", p)
    print("jpa fixed:", len(jp))
    for p in jp:
        print(" ", p)


if __name__ == "__main__":
    main()
