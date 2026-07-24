# -*- coding: utf-8 -*-
"""Split themes.css by section comments."""
from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
css_path = REPO / "skeletons" / "baseline" / "frontend" / "src" / "styles" / "themes.css"
text = css_path.read_text(encoding="utf-8")
out_dir = css_path.parent / "themes"
out_dir.mkdir(parents=True, exist_ok=True)

parts = re.split(r"(?=\n/\* ——)", text)
shared = parts[0].rstrip() + "\n"
imports: list[str] = []

name_map = {
    "商城": "shop",
    "宿舍": "dorm",
    "设备借用": "equip",
    "点餐": "food",
    "医院": "hosp",
    "车位": "park",
    "通用": "gen",
    "物资领用": "asset",
    "客户跟进 CRM": "crm",
    "事件上报 EVENT": "event",
    "物业报修": "prop",
    "IT 报修": "it",
    "活动报名": "act",
    "失物招领": "lost",
    "选课": "course",
    "会议室": "meet",
    "服务预约": "salon",
    "客房": "hotel",
    "影视综": "media",
    "音乐": "music",
    "论坛": "forum",
    "博客": "blog",
    "考勤请假 ATTEND": "attend",
    "资助奖学金 FUND": "fund",
    "实验室安全准入 LABSAFE": "labsafe",
    "招聘 RECRUIT": "recruit",
    "教务成绩 GRADE": "grade",
    "实习 INTERN": "intern",
    "快递驿站 PARCEL": "parcel",
}

for part in parts[1:]:
    m = re.match(r"\n?/\* ——\s*(.+?)\s*—— \*/", part)
    if not m:
        print("no title", repr(part[:80]))
        continue
    title = m.group(1)
    fam = name_map.get(title)
    if not fam:
        tm = re.search(r'\[data-theme="([a-z0-9]+)-', part)
        fam = tm.group(1) if tm else "misc"
        print("unmapped", title, "->", fam)
    fname = f"{fam}.css"
    (out_dir / fname).write_text(part.lstrip("\n"), encoding="utf-8")
    imports.append(f'@import "./themes/{fname}";')
    print("section", title, "->", fname, "lines", len(part.splitlines()))

css_path.write_text(shared.rstrip() + "\n\n" + "\n".join(imports) + "\n", encoding="utf-8")
print("shared lines", len(shared.splitlines()), "imports", len(imports))
