"""骨架 Java 编译味门禁：重复方法、裸 KeyHolder。

出包侧靠 mvn compile，但 CI 默认不真编整套骨架；这些静态门禁挡「一加厚全栈炸」。
"""

from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
JAVA_ROOTS = (
    ROOT / "skeletons/baseline/backend/src/main/java",
    ROOT / "skeletons/overlays/persistence-jpa/backend/src/main/java",
    ROOT / "skeletons/overlays/persistence-mybatis/backend/src/main/java",
)

# 行首可见性修饰的方法声明（避免灾难回溯）
_METHOD_LINE = re.compile(
    r"^\s*(?:public|private|protected)\s+(?:static\s+)?"
    r"(?:final\s+)?"
    r"([\w.<>,\[\]\s]+?)\s+(\w+)\s*\(([^;{]*)\)\s*\{",
    re.MULTILINE,
)


def _java_files() -> list[Path]:
    out: list[Path] = []
    for root in JAVA_ROOTS:
        if root.is_dir():
            out.extend(root.rglob("*.java"))
    return out


def _strip_comments(text: str) -> str:
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    return re.sub(r"(?m)^\s*//.*$", "", text)


def test_no_duplicate_instance_method_signatures() -> None:
    """同一类里重复方法签名 → javac「已在类中定义了方法」。"""
    bad: list[str] = []
    for path in _java_files():
        text = _strip_comments(path.read_text(encoding="utf-8"))
        sigs: list[str] = []
        for m in _METHOD_LINE.finditer(text):
            ret, name, params = m.group(1).strip(), m.group(2), m.group(3).strip()
            if name in {"if", "while", "for", "switch", "catch", "return"}:
                continue
            if ret.endswith("."):  # 误伤
                continue
            types: list[str] = []
            if params:
                for part in params.split(","):
                    part = part.strip()
                    if not part:
                        continue
                    toks = part.split()
                    types.append(" ".join(toks[:-1]) if len(toks) >= 2 else toks[0])
            sigs.append(f"{name}({','.join(types)})")
        dup = [s for s, n in Counter(sigs).items() if n > 1]
        if dup:
            rel = str(path.relative_to(ROOT)).replace("\\", "/")
            bad.append(f"{rel}: {', '.join(sorted(dup))}")
    assert not bad, "重复方法签名（javac 必红）:\n" + "\n".join(bad)


def test_keyholder_usage_has_import_or_fqn() -> None:
    """裸 KeyHolder 类型须 import 或全限定，否则「找不到符号」。

    跳过 KeyHolder 定义本身，以及同包 com.thesis.config（无需 import）。
    """
    bad: list[str] = []
    for path in _java_files():
        if path.name in {"KeyHolder.java", "GeneratedKeyHolder.java"}:
            continue
        text = path.read_text(encoding="utf-8")
        if "KeyHolder" not in text:
            continue
        pkg_m = re.search(r"^package\s+([\w.]+)\s*;", text, re.M)
        pkg = pkg_m.group(1) if pkg_m else ""
        if pkg.endswith(".config"):
            continue  # 与 com.thesis.config.KeyHolder 同包
        has_import = (
            "import org.springframework.jdbc.support.KeyHolder;" in text
            or "import com.thesis.config.KeyHolder;" in text
        )
        bare = len(re.findall(r"(?<![\w.])KeyHolder\b", text))
        fqn = len(
            re.findall(
                r"(?:org\.springframework\.jdbc\.support|com\.thesis\.config)\.KeyHolder\b",
                text,
            )
        )
        if not has_import and bare > fqn:
            bad.append(str(path.relative_to(ROOT)).replace("\\", "/"))
    assert not bad, "使用 KeyHolder 但未 import / 未 FQN:\n" + "\n".join(bad)


def test_order_store_has_single_has_line_column() -> None:
    """OrderStore.hasLineColumn 只能有一份定义（谁加厚复制第二份都会让全栈 javac 红）。"""
    for root in JAVA_ROOTS:
        path = root / "com/thesis/capability/OrderStore.java"
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        n = len(
            re.findall(
                r"\b(?:private|public|protected)\s+static\s+boolean\s+hasLineColumn\s*\(",
                text,
            )
        )
        assert n == 1, f"{path}: hasLineColumn 定义数={n}，须恰好 1"
