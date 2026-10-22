"""拆一页 Vue，并把 tests 里对该 .vue 的 read_text 改为 vue_src 合读。"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
TESTS = REPO / "backend" / "tests"
sys.path.insert(0, str(REPO / "scripts"))
from _split_vue_sfc import split_vue  # noqa: E402


def ensure_import(text: str) -> str:
    if "from tests._vue_src import vue_src" in text:
        return text
    needle = "from __future__ import annotations\n"
    if needle in text:
        return text.replace(
            needle,
            needle + "\nfrom tests._vue_src import vue_src\n",
            1,
        )
    return "from tests._vue_src import vue_src\n" + text


def patch_tests_for(vue_rel: str) -> None:
    """vue_rel like views/admin/TicketsAdmin.vue — match basename reads."""
    name = Path(vue_rel).name  # TicketsAdmin.vue
    stem = Path(vue_rel).stem
    changed = []
    for p in TESTS.glob("test_*.py"):
        t = p.read_text(encoding="utf-8")
        if name not in t and stem not in t:
            continue
        orig = t
        t2 = t
        # Common patterns: Path(.../Name.vue).read_text(...)
        # Also: some_var.read_text where var ends with Name.vue assignment — harder
        patterns = [
            (
                rf'(\([^)]*{re.escape(name)}[^)]*\))\s*\.read_text\(\s*encoding=["\']utf-8["\']\s*\)',
                r"vue_src(\1)",
            ),
            (
                rf'(\([^)]*{re.escape(name)}[^)]*\))\s*\.read_text\(\s*\n\s*encoding=["\']utf-8["\']\s*\n\s*\)',
                r"vue_src(\1)",
            ),
        ]
        for pat, repl in patterns:
            t2 = re.sub(pat, repl, t2)
        # VAR = ... Name.vue then VAR.read_text — leave if already vue_src(VAR)
        # Simple: X.read_text when X is known constant pointing to this file
        # Handle ADMIN.read_text / similar when assignment line contains name
        assign_vars = re.findall(
            rf'^(\w+)\s*=\s*[^\n]*{re.escape(name)}',
            t2,
            re.M,
        )
        for var in assign_vars:
            t2 = t2.replace(
                f'{var}.read_text(encoding="utf-8")',
                f"vue_src({var})",
            )
            t2 = t2.replace(
                f"{var}.read_text(encoding='utf-8')",
                f"vue_src({var})",
            )
        if t2 != orig:
            t2 = ensure_import(t2)
            p.write_text(t2, encoding="utf-8", newline="\n")
            changed.append(p.name)
    print(f"patched tests: {changed or 'none'}")


def update_batch_doc(vue_rel: str) -> None:
    doc = REPO / "docs" / "vue-split-batch.md"
    text = doc.read_text(encoding="utf-8")
    # mark row with this path as 已齐
    needle = f"`{vue_rel}`"
    lines = []
    for line in text.splitlines(keepends=True):
        if needle in line and "待拆" in line:
            line = line.replace("待拆", "**已齐**")
        lines.append(line)
    doc.write_text("".join(lines), encoding="utf-8", newline="\n")


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit("usage: _split_vue_and_patch_tests.py <relpath under frontend/src>")
    rel = sys.argv[1].replace("\\", "/")
    vue = REPO / "skeletons" / "baseline" / "frontend" / "src" / rel
    if not vue.is_file():
        raise SystemExit(f"missing {vue}")
    split_vue(vue)
    patch_tests_for(rel)
    update_batch_doc(rel)


if __name__ == "__main__":
    main()
