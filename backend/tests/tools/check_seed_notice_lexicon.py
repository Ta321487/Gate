"""普查：学生包 SQL 里的种子公告正文，是否与实体口径分叉 / 串了别域招牌词。

种子公告（sys_notice）由 sql/domain_scene_seed.py 手写，属可见文案的第四个来源；
本脚本对每个具名域生成 SQL，抽出公告标题/正文，与 schema 槽位（category_axis /
ticket_noun）及跨域专属名词表比对。Run from backend/:
python tests/tools/check_seed_notice_lexicon.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import os
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from app.bake.domain_vocab import notice_slot_findings, seed_notices  # noqa: E402
from app.bake.engine import domain_sql  # noqa: E402
from app.bake.schema.templates import SCHEMA_BUILDERS  # noqa: E402


def main() -> int:
    total = 0
    hits: list[str] = []
    out_path = Path(tempfile.gettempdir()) / "gf_seed_notice_report.txt"
    for domain, builder in sorted(SCHEMA_BUILDERS.items()):
        try:
            sql = domain_sql(domain, "thesis_test")
        except Exception as exc:  # noqa: BLE001
            hits.append(f"SKIP {domain}: {exc}")
            continue
        schema = builder("测试课题")
        notices = seed_notices(sql)
        total += len(notices)
        for f in notice_slot_findings(sql, schema, domain=domain):
            hits.append(f"{domain}: {f['level']} {f['msg']}")
    lines = [f"种子公告总数 {total}", f"命中 {len(hits)}"] + [f"   - {h}" for h in hits]
    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"种子公告总数 {total}，命中 {len(hits)}（详见 {out_path.name}）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
