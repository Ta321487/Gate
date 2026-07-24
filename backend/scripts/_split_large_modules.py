# -*- coding: utf-8 -*-
"""Batch-split large bake modules. Run from backend/."""
from __future__ import annotations

import ast
import re
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def slim_domains() -> None:
    path = ROOT / "app" / "bake" / "domains.py"
    text = path.read_text(encoding="utf-8")
    if "from app.bake.domains_catalog import CATALOG_DOMAINS" in text and "DOMAINS = dict(CATALOG_DOMAINS)" in text:
        print("domains.py already slim", len(text.splitlines()))
        return
    # Keep everything before DOMAINS = {
    m = re.search(r"^DOMAINS = \{", text, re.M)
    if not m:
        raise SystemExit("DOMAINS not found")
    head = text[: m.start()]
    # Drop unused gate imports from head if present — catalog owns gates
    head = re.sub(
        r"from app\.bake\.gate_contracts import \([^)]+\)\n\n",
        "",
        head,
        count=1,
        flags=re.S,
    )
    new = (
        head.rstrip()
        + "\n\n"
        + "from app.bake.domains_catalog import CATALOG_DOMAINS\n\n"
        + "DOMAINS = dict(CATALOG_DOMAINS)\n\n"
        + "# 档案表 / 单据表 / ticket_mode 以 domain_entities 为准（覆盖上方 runtime 同名字段）\n"
        + "from app.bake.domain_entities import bind_runtime_tables  # noqa: E402\n\n"
        + "bind_runtime_tables(DOMAINS)\n"
    )
    path.write_text(new, encoding="utf-8")
    print("domains.py lines", len(new.splitlines()))


def split_domain_sql() -> None:
    out = ROOT / "app" / "bake" / "sql" / "templates"
    loader_path = ROOT / "app" / "bake" / "sql" / "domain_templates.py"
    text = loader_path.read_text(encoding="utf-8")
    if out.exists() and any(out.glob("DOM-*.sql")) and "Path(__file__)" in text:
        print("sql already split", len(list(out.glob("DOM-*.sql"))))
        return
    # Import while the big inline dict still exists
    import sys

    sys.path.insert(0, str(ROOT))
    from app.bake.sql.domain_templates import DOMAIN_SQL_TEMPLATES

    out.mkdir(parents=True, exist_ok=True)
    for key, sql in DOMAIN_SQL_TEMPLATES.items():
        (out / f"{key}.sql").write_text(sql, encoding="utf-8")
        print("wrote", key, len(sql))
    n = len(DOMAIN_SQL_TEMPLATES)
    loader = '''"""Per-domain SQL templates（正文在 templates/DOM-*.sql）。"""

from __future__ import annotations

from pathlib import Path

_DIR = Path(__file__).resolve().parent / "templates"

DOMAIN_SQL_TEMPLATES: dict[str, str] = {
    p.stem: p.read_text(encoding="utf-8")
    for p in sorted(_DIR.glob("DOM-*.sql"))
}
'''
    loader_path.write_text(loader, encoding="utf-8")
    print("sql keys", n)


def split_domain_builders() -> None:
    src = ROOT / "app" / "bake" / "schema" / "domain_builders.py"
    schema_dir = ROOT / "app" / "bake" / "schema"
    if (schema_dir / "builders_archive.py").exists() and "builders_archive" in src.read_text(encoding="utf-8"):
        print("domain_builders already split")
        return
    text = src.read_text(encoding="utf-8")
    # Find all def _xxx_schema
    matches = list(re.finditer(r"^def (_\w+_schema)\(", text, re.M))
    chunks: dict[str, str] = {}
    for i, m in enumerate(matches):
        name = m.group(1)
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        chunks[name] = text[start:end].rstrip() + "\n\n"

    groups = {
        "builders_archive.py": [
            "_library_schema",
            "_equip_schema",
            "_asset_schema",
            "_crm_schema",
            "_event_schema",
            "_attend_schema",
            "_fund_schema",
            "_labsafe_schema",
            "_recruit_schema",
            "_grade_schema",
            "_intern_schema",
            "_parcel_schema",
            "_activity_schema",
            "_lost_schema",
            "_course_schema",
        ],
        "builders_slot.py": [
            "_shop_schema",
            "_food_schema",
            "_meeting_schema",
            "_hospital_schema",
            "_parking_schema",
            "_salon_schema",
            "_hotel_schema",
        ],
        "builders_content.py": [
            "_media_schema",
            "_music_schema",
            "_forum_schema",
            "_blog_schema",
        ],
        "builders_ticket.py": [
            "_dorm_schema",
            "_property_schema",
            "_it_schema",
        ],
    }

    header_archive = '''"""档案 / followup / 报名申请类域 builder。"""

from __future__ import annotations

from typing import Any

from app.bake.domains import DOMAIN_CAPABILITIES
from app.bake.schema.shells import (
    _CAMPUS_HINTS,
    _COMMUNITY_HINTS,
    _copy_scan_text,
    _scan_has,
    _with_portal_banners,
    archive_ticket_schema,
    product_name_from_title,
)

'''
    header_slot = '''"""交易 / 预约类域 builder。"""

from __future__ import annotations

from typing import Any

from app.bake.schema.shells import (
    _CAMPUS_HINTS,
    _copy_scan_text,
    _scan_has,
    order_shell_schema,
    slot_shell_schema,
)

'''
    header_content = '''"""内容 / 媒资 / 社区域 builder。"""

from __future__ import annotations

from typing import Any

from app.bake.schema.shells import (
    _with_portal_banners,
    archive_favorites_schema,
    archive_ticket_schema,
)

'''
    header_ticket = '''"""独立工单域 builder（宿舍/物业/IT）。"""

from __future__ import annotations

from typing import Any

from app.bake.schema.shells import standalone_ticket_schema

'''
    headers = {
        "builders_archive.py": header_archive,
        "builders_slot.py": header_slot,
        "builders_content.py": header_content,
        "builders_ticket.py": header_ticket,
    }

    schema_dir = ROOT / "app" / "bake" / "schema"
    all_names: list[str] = []
    for fname, names in groups.items():
        body = headers[fname]
        for n in names:
            if n not in chunks:
                raise SystemExit(f"missing builder {n}")
            body += chunks[n]
            all_names.append(n)
        (schema_dir / fname).write_text(body, encoding="utf-8")
        print("wrote", fname, len(names))

    # thin re-export
    export_lines = "\n".join(f'    "{n}",' for n in all_names)
    src.write_text(
        f'''"""各具名域 Domain Schema builder（再导出）。

实现见 builders_archive / builders_slot / builders_content / builders_ticket。
"""

from __future__ import annotations

from app.bake.schema.builders_archive import (  # noqa: F401
    _activity_schema,
    _asset_schema,
    _attend_schema,
    _course_schema,
    _crm_schema,
    _equip_schema,
    _event_schema,
    _fund_schema,
    _grade_schema,
    _intern_schema,
    _labsafe_schema,
    _library_schema,
    _lost_schema,
    _parcel_schema,
    _recruit_schema,
)
from app.bake.schema.builders_content import (  # noqa: F401
    _blog_schema,
    _forum_schema,
    _media_schema,
    _music_schema,
)
from app.bake.schema.builders_slot import (  # noqa: F401
    _food_schema,
    _hospital_schema,
    _hotel_schema,
    _meeting_schema,
    _parking_schema,
    _salon_schema,
    _shop_schema,
)
from app.bake.schema.builders_ticket import (  # noqa: F401
    _dorm_schema,
    _it_schema,
    _property_schema,
)

__all__ = [
{export_lines}
]
''',
        encoding="utf-8",
    )
    print("domain_builders reexport", len(all_names))


if __name__ == "__main__":
    slim_domains()
    split_domain_sql()
    split_domain_builders()
