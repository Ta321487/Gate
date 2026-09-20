"""骨架：PreparedStatementCreator lambda 不得捕获「先赋后改」的局部变量。"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
JAVA_ROOTS = (
    ROOT / "skeletons/baseline/backend/src/main/java",
    ROOT / "skeletons/overlays/persistence-jpa/backend/src/main/java",
    ROOT / "skeletons/overlays/persistence-mybatis/backend/src/main/java",
)

# 声明后经 if 再赋（成团 status 翻车同类）
_REASSIGN_IF = re.compile(
    r"(?:^|\n)\s*(?:String|int|long|double|boolean)\s+(\w+)\s*=[^\n]+;\s*\n"
    r"\s*if\s*\([^)]+\)\s*\1\s*=",
    re.MULTILINE,
)


def test_order_store_initial_status_is_effectively_final() -> None:
    """成团把 initialStatus 再赋一次后，javac 拒绝 lambda 捕获。"""
    for root in JAVA_ROOTS:
        path = root / "com/thesis/capability/OrderStore.java"
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        assert not re.search(
            r"String\s+initialStatus\s*=.*\n\s*if\s*\(.*\)\s*initialStatus\s*=",
            text,
        ), f"OrderStore 勿对 initialStatus 先赋后改后再进 lambda: {path}"
        if "GeneratedKeyHolder" in text and "db().update(con ->" in text:
            assert "final String initialStatus" in text, path


def test_slot_store_slot_id_effectively_final_for_lambda() -> None:
    """boarding 会改写 slotId；JdbcTemplate lambda 内须用 final 副本。"""
    for rel in (
        "skeletons/baseline/backend/src/main/java/com/thesis/capability/SlotStore.java",
        "skeletons/overlays/persistence-jpa/backend/src/main/java/com/thesis/capability/SlotStore.java",
    ):
        path = ROOT / rel
        text = path.read_text(encoding="utf-8")
        if "db().update(con ->" not in text:
            continue
        assert "final long slotIdFinal = slotId" in text, path
        assert "args.add(slotIdFinal)" in text, path
        assert not re.search(
            r"db\(\)\.update\(con\s*->\s*\{[^}]*args\.add\(slotId\)",
            text,
            re.DOTALL,
        ), path


def test_no_if_reassign_then_capture_in_con_lambda() -> None:
    """
    典型翻车：String x = a; if (cond) x = b; 随后 con -> { ... x ... }
    （截断后再赋给 finalX 的写法不在此列。）
    """
    bad: list[str] = []
    for root in JAVA_ROOTS:
        if not root.is_dir():
            continue
        for path in root.rglob("*.java"):
            text = path.read_text(encoding="utf-8")
            if "con ->" not in text:
                continue
            rel = str(path.relative_to(ROOT)).replace("\\", "/")
            for m in _REASSIGN_IF.finditer(text):
                name = m.group(1)
                after = text[m.end() : m.end() + 2500]
                lam = re.search(r"con\s*->\s*\{", after)
                if not lam:
                    continue
                body = after[lam.end() : lam.end() + 1200]
                body_stripped = re.sub(r'"(?:\\.|[^"\\])*"', '""', body)
                if re.search(rf"(?<![\w]){name}(?![\w])", body_stripped) and not re.search(
                    rf"\b(?:String|int|long|double|boolean)\s+{name}\b", body_stripped
                ):
                    prefix = after[: lam.start()]
                    if re.search(rf"\bfinal\s+\w+\s+\w+\s*=\s*{name}\b", prefix):
                        continue
                    bad.append(f"{rel}: {name}")
    assert not bad, "if 再赋后被 con->lambda 捕获:\n" + "\n".join(sorted(set(bad)))
