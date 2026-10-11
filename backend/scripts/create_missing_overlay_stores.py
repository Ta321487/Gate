"""为 mybatis/jpa 叠层补齐仍只存在于 baseline 的 JDBC Store。"""

from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
BASE = REPO / "skeletons/baseline/backend/src/main/java"
FILES = [
    "com/thesis/service/BlogFriendLinkStore.java",
    "com/thesis/service/CategoryFollowStore.java",
    "com/thesis/service/MediaEpisodeStore.java",
    "com/thesis/service/MediaPlayProgressStore.java",
    "com/thesis/service/UserFollowStore.java",
]


def convert(text: str, kind: str) -> str:
    if kind == "mybatis":
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
        text = re.sub(
            r"private static JdbcTemplate db\(\)\s*\{\s*return JdbcSupport\.jdbc\(\);\s*\}",
            "private static MbSql db() {\n        return MybatisSupport.db();\n    }",
            text,
        )
        text = text.replace("JdbcSupport.jdbc()", "MybatisSupport.db()")
        text = text.replace("JdbcTemplate", "MbSql")
    else:
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
        text = re.sub(
            r"private static JdbcTemplate db\(\)\s*\{\s*return JdbcSupport\.jdbc\(\);\s*\}",
            "private static JpaDb db() {\n        return JpaSupport.db();\n    }",
            text,
        )
        text = text.replace("JdbcSupport.jdbc()", "JpaSupport.db()")
        text = text.replace("JdbcTemplate", "JpaDb")

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


MYBATIS_CHOICE = r'''package com.thesis.service;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.thesis.config.MbSql;

import java.util.ArrayList;
import java.util.List;

/** 试卷/问卷选项：子表一行一项，API 仍收发 optionsJson 数组（MyBatis 叠层）。 */
final class ChoiceOptionOps {

    private static final ObjectMapper JSON = new ObjectMapper();

    private ChoiceOptionOps() {}

    static String loadJson(MbSql db, String table, long questionId) {
        try {
            List<String> texts = db.query(
                    "SELECT content FROM " + table + " WHERE question_id=? ORDER BY sort_no",
                    (rs, i) -> rs.getString("content"),
                    questionId);
            return JSON.writeValueAsString(texts == null ? List.of() : texts);
        } catch (Exception e) {
            return "[]";
        }
    }

    static void replace(MbSql db, String table, long questionId, String optionsJson) {
        db.update("DELETE FROM " + table + " WHERE question_id=?", questionId);
        List<String> items = parse(optionsJson);
        int no = 1;
        for (String text : items) {
            String label = String.valueOf((char) ('A' + no - 1));
            db.update(
                    "INSERT INTO " + table + " (question_id,sort_no,label,content) VALUES (?,?,?,?)",
                    questionId, no, label, text);
            no++;
        }
    }

    private static List<String> parse(String raw) {
        if (raw == null || raw.isBlank()) return List.of();
        String s = raw.trim();
        try {
            List<String> list = JSON.readValue(s, new TypeReference<>() {});
            List<String> out = new ArrayList<>();
            if (list == null) return out;
            for (String t : list) {
                if (t == null) continue;
                String u = t.trim();
                if (!u.isBlank()) out.add(u.length() > 500 ? u.substring(0, 500) : u);
            }
            return out;
        } catch (Exception e) {
            return List.of();
        }
    }
}
'''


def main() -> None:
    for kind, root in (
        ("mybatis", REPO / "skeletons/overlays/persistence-mybatis/backend/src/main/java"),
        ("jpa", REPO / "skeletons/overlays/persistence-jpa/backend/src/main/java"),
    ):
        for rel in FILES:
            src = BASE / rel
            dst = root / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_text(convert(src.read_text(encoding="utf-8"), kind), encoding="utf-8", newline="\n")
            print("wrote", kind, rel)

    choice = (
        REPO
        / "skeletons/overlays/persistence-mybatis/backend/src/main/java/com/thesis/service/ChoiceOptionOps.java"
    )
    choice.write_text(MYBATIS_CHOICE, encoding="utf-8", newline="\n")
    print("wrote mybatis ChoiceOptionOps")


if __name__ == "__main__":
    main()
