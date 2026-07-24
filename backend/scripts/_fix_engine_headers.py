# -*- coding: utf-8 -*-
from pathlib import Path

for name in [
    "engine_sql.py",
    "engine_bake.py",
    "engine_resources.py",
    "engine_islands.py",
]:
    p = Path(__file__).resolve().parents[1] / "app" / "bake" / name
    t = p.read_text(encoding="utf-8")
    # Remove leading string-literal statements before from __future__
    if t.startswith('"""'):
        end = t.find('"""', 3)
        if end > 0:
            first = t[: end + 3]
            rest = t[end + 3 :].lstrip()
            while rest.startswith('"""'):
                e2 = rest.find('"""', 3)
                if e2 < 0:
                    break
                rest = rest[e2 + 3 :].lstrip()
            t = first + "\n\n" + rest
            p.write_text(t, encoding="utf-8")
            print("fixed", name)
    # verify compile
    compile(t, str(p), "exec")
    print("compile ok", name)
