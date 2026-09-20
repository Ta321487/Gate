"""同一 try 里先 catch 父类再 catch 子类，javac 会报「已捕获到异常错误」。"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
JAVA_ROOTS = (
    ROOT / "skeletons/baseline/backend/src/main/java",
    ROOT / "skeletons/overlays/persistence-jpa/backend/src/main/java",
    ROOT / "skeletons/overlays/persistence-mybatis/backend/src/main/java",
)

# 直接父类。只用来判断「同一 catch 链里子类写在父类后面」。
_CHILD_OF = {
    "NumberFormatException": "IllegalArgumentException",
    "IllegalFormatException": "IllegalArgumentException",
    "PatternSyntaxException": "IllegalArgumentException",
    "DateTimeParseException": "DateTimeException",
    "EOFException": "IOException",
    "FileNotFoundException": "IOException",
    "SQLException": "Exception",
    "IllegalArgumentException": "RuntimeException",
    "IllegalStateException": "RuntimeException",
    "RuntimeException": "Exception",
}


def _adjacent_catch_chains(text: str) -> list[list[str]]:
    spans: list[tuple[int, int, list[str]]] = []
    i = 0
    n = len(text)
    while True:
        m = re.search(r"\bcatch\s*\(", text[i:])
        if not m:
            break
        p = i + m.end()
        depth = 1
        while p < n and depth:
            if text[p] == "(":
                depth += 1
            elif text[p] == ")":
                depth -= 1
            p += 1
        types: list[str] = []
        for part in text[i + m.end() : p - 1].split("|"):
            tok = part.strip().split()
            if tok:
                types.append(tok[0].split(".")[-1])
        while p < n and text[p].isspace():
            p += 1
        if p >= n or text[p] != "{":
            i = p
            continue
        depth = 0
        q = p
        while q < n:
            if text[q] == "{":
                depth += 1
            elif text[q] == "}":
                depth -= 1
                if depth == 0:
                    q += 1
                    break
            q += 1
        spans.append((i + m.start(), q, types))
        i = q
    groups: list[list[str]] = []
    cur: list[str] = []
    prev_end = -1
    for start, end, types in spans:
        gap = text[prev_end:start] if prev_end >= 0 else "\n"
        if prev_end >= 0 and gap.strip() == "":
            cur.extend(types)
        else:
            if cur:
                groups.append(cur)
            cur = list(types)
        prev_end = end
    if cur:
        groups.append(cur)
    return groups


def _unreachable(chain: list[str]) -> list[str]:
    bad: list[str] = []
    seen: set[str] = set()
    for name in chain:
        anc = _CHILD_OF.get(name)
        while anc:
            if anc in seen:
                bad.append(f"{anc} 已捕获，其后的 {name} 不可达")
                break
            anc = _CHILD_OF.get(anc)
        seen.add(name)
    return bad


def test_no_unreachable_subclass_catch_in_skeletons() -> None:
    hits: list[str] = []
    for root in JAVA_ROOTS:
        if not root.is_dir():
            continue
        for path in root.rglob("*.java"):
            text = path.read_text(encoding="utf-8")
            rel = str(path.relative_to(ROOT)).replace("\\", "/")
            for chain in _adjacent_catch_chains(text):
                for msg in _unreachable(chain):
                    hits.append(f"{rel}: {msg}")
    assert not hits, "不可达 catch（javac 会挂）:\n" + "\n".join(hits)
