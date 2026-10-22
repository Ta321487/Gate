"""把内联 <script setup> / <style scoped> 外提为同名 .setup.js + .css。"""

from __future__ import annotations

import re
import sys
from pathlib import Path


def split_vue(vue_path: Path) -> None:
    text = vue_path.read_text(encoding="utf-8")
    if re.search(r"<script\s+setup\s+src=", text):
        raise SystemExit(f"already split: {vue_path}")
    m_script = re.search(r"<script\s+setup\s*>\s*\n?(.*?)\n?</script>", text, re.S)
    m_style = re.search(r"<style\s+scoped\s*>\s*\n?(.*?)\n?</style>", text, re.S)
    if not m_script:
        raise SystemExit(f"no inline script setup: {vue_path}")
    if not m_style:
        raise SystemExit(f"no inline style scoped: {vue_path}")
    setup_body = m_script.group(1)
    if setup_body.startswith("\n"):
        setup_body = setup_body[1:]
    if not setup_body.endswith("\n"):
        setup_body += "\n"
    css_body = m_style.group(1)
    if css_body.startswith("\n"):
        css_body = css_body[1:]
    if not css_body.endswith("\n"):
        css_body += "\n"
    setup_path = vue_path.with_name(f"{vue_path.stem}.setup.js")
    css_path = vue_path.with_name(f"{vue_path.stem}.css")
    setup_path.write_text(setup_body, encoding="utf-8", newline="\n")
    css_path.write_text(css_body, encoding="utf-8", newline="\n")
    before = text[: m_script.start()].rstrip() + "\n\n"
    new_vue = (
        before
        + f'<script setup src="./{vue_path.stem}.setup.js"></script>\n\n'
        + f'<style scoped src="./{vue_path.stem}.css"></style>\n'
    )
    vue_path.write_text(new_vue, encoding="utf-8", newline="\n")
    print(
        f"OK {vue_path}: setup={setup_path.stat().st_size} "
        f"css={css_path.stat().st_size} vue={vue_path.stat().st_size}"
    )


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit("usage: _split_vue_sfc.py <path.vue> ...")
    for arg in sys.argv[1:]:
        split_vue(Path(arg))
