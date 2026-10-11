"""骨架 Java 编译味门禁（快测，不跑 mvn）。

已拦：重复方法签名、同方法重复局部变量、裸 KeyHolder、NFE 捕序、
Binder 裸 Store、OrderStore.hasLineColumn 双份等。

出包侧仍靠 build_verify → mvn compile；加厚改骨架时再跑本文件 + slow 真编。
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

# 常见局部声明（够挡 Store 加厚；不追求完整 Java 语法）
_LOCAL_DECL = re.compile(
    r"(?<![\w.@])(?:final\s+)?"
    r"(?:"
    r"var|"
    r"String|int|long|boolean|double|float|byte|short|char|"
    r"Integer|Long|Boolean|Double|Object|Number|Timestamp|"
    r"LocalDateTime|LocalDate|BigDecimal|KeyHolder|"
    r"PreparedStatement|ResultSet|Connection|Statement|"
    r"(?:Map|List|Set|Collection|Optional|Iterator|ArrayList|LinkedHashMap|"
    r"HashMap|HashSet|LinkedList|StringBuilder|StringBuffer|"
    r"ConcurrentHashMap|TreeMap|TreeSet)"
    r"(?:\s*<[^;\n{]+?>)?"
    r"(?:\s*\[\s*\])*"
    r")"
    r"\s+([A-Za-z_]\w*)\s*(?:=|;)"
)

_FOR_DECL = re.compile(
    r"\bfor\s*\(\s*(?:final\s+)?"
    r"(?:String|int|long|boolean|Integer|Long|Object|Map|List|var|"
    r"[\w.]+(?:\s*<[^>]+>)?)"
    r"\s+([A-Za-z_]\w*)\s*[:=]"
)
_CATCH_DECL = re.compile(r"\bcatch\s*\(\s*([\w.|]+)\s+([A-Za-z_]\w*)\s*\)")

def _java_files() -> list[Path]:
    out: list[Path] = []
    for root in JAVA_ROOTS:
        if root.is_dir():
            out.extend(root.rglob("*.java"))
    return out


def _strip_comments(text: str) -> str:
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    return re.sub(r"(?m)^\s*//.*$", "", text)


def _mask_literals(text: str) -> str:
    """注释已剥；把字符串/字符字面量换成等长空格，保留换行与括号平衡。"""
    out: list[str] = []
    i = 0
    n = len(text)
    while i < n:
        c = text[i]
        if c == '"':
            j = i + 1
            while j < n:
                if text[j] == "\\":
                    j += 2
                    continue
                if text[j] == '"':
                    j += 1
                    break
                j += 1
            chunk = text[i:j]
            out.append("".join("\n" if ch == "\n" else " " for ch in chunk))
            i = j
            continue
        if c == "'":
            j = i + 1
            while j < n:
                if text[j] == "\\":
                    j += 2
                    continue
                if text[j] == "'":
                    j += 1
                    break
                j += 1
            chunk = text[i:j]
            out.append("".join("\n" if ch == "\n" else " " for ch in chunk))
            i = j
            continue
        out.append(c)
        i += 1
    return "".join(out)


def _method_bodies(text: str):
    """Yield (method_name, params, body) with brace match; text must be comment-stripped + literal-masked."""
    for m in _METHOD_LINE.finditer(text):
        name = m.group(2)
        if name in {"if", "while", "for", "switch", "catch", "return"}:
            continue
        params = m.group(3).strip()
        start = m.end() - 1
        depth = 0
        i = start
        while i < len(text):
            c = text[i]
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    yield name, params, text[start + 1 : i]
                    break
            i += 1


def _param_names(params: str) -> list[str]:
    out: list[str] = []
    if not params.strip():
        return out
    for part in params.split(","):
        part = re.sub(r"@\w+(?:\([^)]*\))?\s*", "", part.strip())
        if not part:
            continue
        toks = part.split()
        if len(toks) >= 2:
            out.append(toks[-1])
    return out


def _duplicate_locals_in_method(method: str, params: str, body: str) -> list[str]:
    """Java 不允许内层块遮蔽同方法已有局部变量 → 同名二次声明必红。"""
    scopes: list[set[str]] = [set(_param_names(params))]
    dups: list[str] = []
    i = 0
    n = len(body)
    while i < n:
        m = _CATCH_DECL.match(body, i)
        if m:
            name = m.group(2)
            rest = body[m.end() :]
            bm = re.match(r"\s*\{", rest)
            if bm:
                if any(name in s for s in scopes):
                    dups.append(f"{method}() 重复变量 `{name}`")
                scopes.append({name})
                i = m.end() + bm.end()
                continue
        m = _FOR_DECL.match(body, i)
        if m:
            name = m.group(1)
            if any(name in s for s in scopes):
                dups.append(f"{method}() 重复变量 `{name}`")
            j = m.end()
            depth_p = 0
            while j < n:
                if body[j] == "(":
                    depth_p += 1
                elif body[j] == ")":
                    if depth_p == 0:
                        j += 1
                        break
                    depth_p -= 1
                j += 1
            while j < n and body[j] in " \t\n\r":
                j += 1
            if j < n and body[j] == "{":
                scopes.append({name})
                i = j + 1
                continue
            i = j
            continue
        if body[i] == "{":
            scopes.append(set())
            i += 1
            continue
        if body[i] == "}":
            if len(scopes) > 1:
                scopes.pop()
            i += 1
            continue
        m = _LOCAL_DECL.match(body, i)
        if m:
            name = m.group(1)
            prev = body[max(0, i - 24) : i]
            if re.search(r"\b(return|throw|instanceof)\s*$", prev):
                i += 1
                continue
            if any(name in s for s in scopes):
                dups.append(f"{method}() 重复变量 `{name}`")
            else:
                scopes[-1].add(name)
            i = m.end()
            continue
        i += 1
    return dups


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


def test_no_duplicate_locals_in_method() -> None:
    """同方法内重复局部变量（含内层块）→ javac「已在方法中定义了变量」。

    典型坑：updateItem 顶部已有 `String author`，加厚块再声明一次。
    覆盖原 SlotStore.reserve / note 单点回归。
    """
    bad: list[str] = []
    for path in _java_files():
        raw = path.read_text(encoding="utf-8")
        text = _mask_literals(_strip_comments(raw))
        hits: list[str] = []
        for method, params, body in _method_bodies(text):
            hits.extend(_duplicate_locals_in_method(method, params, body))
        if hits:
            rel = str(path.relative_to(ROOT)).replace("\\", "/")
            # 去重保序
            seen: set[str] = set()
            uniq: list[str] = []
            for h in hits:
                if h not in seen:
                    seen.add(h)
                    uniq.append(h)
            bad.append(f"{rel}: {', '.join(uniq)}")
    assert not bad, "重复局部变量（javac 必红）:\n" + "\n".join(bad)


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


def test_patient_profile_store_refs_are_resolvable() -> None:
    """DomainRuntimeBinder 里 PatientProfileStore 须 import 或 FQN，裸名 → 找不到符号。"""
    bad: list[str] = []
    for root in JAVA_ROOTS:
        path = root / "com/thesis/config/DomainRuntimeBinder.java"
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        if "PatientProfileStore" not in text:
            continue
        has_import = "import com.thesis.service.PatientProfileStore;" in text
        bare = re.findall(r"(?<![\w.])PatientProfileStore\.", text)
        if bare and not has_import:
            bad.append(str(path.relative_to(ROOT)).replace("\\", "/"))
    assert not bad, "PatientProfileStore 裸用且无 import:\n" + "\n".join(bad)


def test_catch_number_format_before_illegal_argument() -> None:
    """NumberFormatException 是 IllegalArgumentException 子类，后捕 → javac「已捕获到异常」。"""
    bad: list[str] = []
    for path in _java_files():
        text = path.read_text(encoding="utf-8")
        # 同一 try 块内：先捕 IAE/ISE 再捕 NFE
        for m in re.finditer(
            r"catch\s*\(\s*IllegalArgumentException(?:\s*\|\s*IllegalStateException)?\s+\w+\s*\)"
            r"\s*\{[^}]*\}"
            r"(?:\s*catch\s*\(\s*IllegalStateException\s+\w+\s*\)\s*\{[^}]*\})?"
            r"\s*catch\s*\(\s*NumberFormatException\s+\w+\s*\)",
            text,
            re.S,
        ):
            bad.append(str(path.relative_to(ROOT)).replace("\\", "/"))
            break
    assert not bad, "NFE 写在 IAE 之后（javac 必红）:\n" + "\n".join(bad)


def test_binder_store_dots_have_import_or_fqn() -> None:
    """DomainRuntimeBinder 里 `XxxStore.` 裸调用须有 import（加厚漏 import → 找不到符号）。"""
    # 高频 Store；与 PatientProfileStore 单点互补
    store_re = re.compile(r"(?<![\w.])([A-Z][A-Za-z0-9]*Store)\.")
    bad: list[str] = []
    for root in JAVA_ROOTS:
        path = root / "com/thesis/config/DomainRuntimeBinder.java"
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        imports = set(re.findall(r"import\s+([\w.]+)\s*;", text))
        imported_simple = {i.rsplit(".", 1)[-1] for i in imports}
        pkg_m = re.search(r"^package\s+([\w.]+)\s*;", text, re.M)
        pkg = pkg_m.group(1) if pkg_m else ""
        missing: set[str] = set()
        for m in store_re.finditer(text):
            simple = m.group(1)
            # 同文件 FQN 调用
            before = text[max(0, m.start() - 40) : m.start()]
            if before.rstrip().endswith("."):
                continue
            if simple in imported_simple:
                continue
            # 同包 service/capability 少见；要求 import
            if f"{pkg}.{simple}" in imports:
                continue
            missing.add(simple)
        if missing:
            rel = str(path.relative_to(ROOT)).replace("\\", "/")
            bad.append(f"{rel}: {', '.join(sorted(missing))}")
    assert not bad, "Binder 裸 Store 无 import:\n" + "\n".join(bad)


def test_slot_store_reserve_does_not_redeclare_note() -> None:
    """兼容旧单点：reserve() 不得重复声明 note（总门禁已覆盖，留回归名）。"""
    test_no_duplicate_locals_in_method()


def test_dup_local_detector_catches_author_redeclaration() -> None:
    """回归：updateItem 顶部 author + 内层再声明 → 必须检出。"""
    sample = """
public class T {
    public static void updateItem(long id) {
        String author = "a";
        if (id > 0) {
            String author = "b";
        }
    }
}
"""
    text = _mask_literals(_strip_comments(sample))
    hits: list[str] = []
    for method, params, body in _method_bodies(text):
        hits.extend(_duplicate_locals_in_method(method, params, body))
    assert any("author" in h for h in hits), hits


def test_favorite_store_report_lambda_uses_final_type() -> None:
    """submitReport 里 type 会改写，进 lambda 必须用 finalType（否则 javac 必红）。"""
    bad: list[str] = []
    for root in JAVA_ROOTS:
        path = root / "com/thesis/capability/FavoriteStore.java"
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        m = re.search(
            r"public static Map<[^>]+>\s+submitReport\s*\([^)]*\)\s*\{",
            text,
        )
        if not m:
            continue
        start = m.end()
        nxt = re.search(r"\n    public static ", text[start:])
        body = text[start : start + (nxt.start() if nxt else len(text))]
        # 粗拦：lambda 里 setString(..., type) 且没有 finalType
        if re.search(r"setString\s*\(\s*2\s*,\s*type\s*\)", body) and "finalType" not in body:
            bad.append(str(path.relative_to(ROOT)).replace("\\", "/"))
    assert not bad, "FavoriteStore.submitReport lambda 仍引用可变 type:\n" + "\n".join(bad)


_STORE_CALL = re.compile(r"\b([A-Z][A-Za-z0-9]*Store)\.([A-Za-z_]\w*)\s*\(")
_PUBLIC_STATIC_METHOD = re.compile(
    r"(?:public|protected)\s+static\s+[\w.<>,\[\]\s]+?\s+(\w+)\s*\(",
)


def _store_public_methods(java_root: Path, store_simple: str) -> set[str] | None:
    """在 capability/service 下找 Store 的 public/protected static 方法名；找不到文件则 None。"""
    candidates = [
        java_root / "com/thesis/capability" / f"{store_simple}.java",
        java_root / "com/thesis/service" / f"{store_simple}.java",
    ]
    path = next((p for p in candidates if p.is_file()), None)
    if path is None:
        return None
    text = _strip_comments(path.read_text(encoding="utf-8"))
    return set(_PUBLIC_STATIC_METHOD.findall(text))


def test_baseline_controller_store_calls_resolve() -> None:
    """Controller 调用 XxxStore.foo 时，同栈 Store 必须有 public static foo（防「找不到符号」）。

    只扫 baseline（Controller 只在 baseline）；overlay Store 另由三套同改纪律保证。
    这是通用门禁，不绑某个方法名。
    """
    java_root = ROOT / "skeletons/baseline/backend/src/main/java"
    ctrl_root = java_root / "com/thesis/controller"
    if not ctrl_root.is_dir():
        return
    bad: list[str] = []
    cache: dict[str, set[str] | None] = {}
    for path in sorted(ctrl_root.rglob("*.java")):
        text = _strip_comments(path.read_text(encoding="utf-8"))
        missing: set[str] = set()
        for m in _STORE_CALL.finditer(text):
            store, method = m.group(1), m.group(2)
            if store not in cache:
                cache[store] = _store_public_methods(java_root, store)
            methods = cache[store]
            if methods is None:
                continue  # Store 文件不在本栈（少见），不误杀
            if method not in methods:
                missing.add(f"{store}.{method}")
        if missing:
            rel = str(path.relative_to(ROOT)).replace("\\", "/")
            bad.append(f"{rel}: {', '.join(sorted(missing))}")
    assert not bad, "Controller 调用了 Store 不存在的方法（javac 必红）:\n" + "\n".join(bad)
