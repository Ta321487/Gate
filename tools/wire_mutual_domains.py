"""接线 DOM-MUTUAL-*（C-05 / P-09～P-11）。先跑 gen_mutual_domains.py。"""

from __future__ import annotations

import json
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
B = ROOT / "backend" / "app" / "bake"


def patch(path: Path, old: str, new: str, label: str) -> None:
    t = path.read_text(encoding="utf-8")
    if old not in t:
        if "DOM-MUTUAL-TUTOR" in t:
            print("skip", label)
            return
        raise SystemExit(f"miss {label}: {path}")
    path.write_text(t.replace(old, new, 1), encoding="utf-8")
    print("ok", label)


def main() -> None:
    import sys

    sys.path.insert(0, str(ROOT / "backend"))
    from app.bake.mutual_meta import MUTUAL_META as META  # noqa: WPS433

    domains = [m["domain"] for m in META]

    patch(
        B / "domains_catalog" / "__init__.py",
        "from app.bake.domains_catalog.checkin import DOMAINS as CHECKIN_DOMAINS\n",
        "from app.bake.domains_catalog.checkin import DOMAINS as CHECKIN_DOMAINS\n"
        "from app.bake.domains_catalog.mutual import DOMAINS as MUTUAL_DOMAINS\n",
        "cat import",
    )
    patch(
        B / "domains_catalog" / "__init__.py",
        "    **CHECKIN_DOMAINS,\n    **FALLBACK_DOMAINS,\n}",
        "    **CHECKIN_DOMAINS,\n    **MUTUAL_DOMAINS,\n    **FALLBACK_DOMAINS,\n}",
        "cat merge",
    )

    group_ids = ",\n            ".join(f'"{d}"' for d in domains)
    patch(
        B / "domains.py",
        '            "DOM-CHECKIN",\n        ),\n    ),\n    ("ticket", "报修/工单"',
        '            "DOM-CHECKIN",\n'
        f"            {group_ids},\n"
        '        ),\n    ),\n    ("ticket", "报修/工单"',
        "groups",
    )

    caps_block = "".join(
        f'    "{m["domain"]}": ["archive", "ticket_flow", "quota", "content", "org_users", "mutual_select"],\n'
        for m in META
    )
    patch(
        B / "domains.py",
        '    "DOM-CHECKIN": ["archive", "ticket_flow", "quota", "content", "org_users", "checkin"],\n'
        "    # B 报修/工单",
        '    "DOM-CHECKIN": ["archive", "ticket_flow", "quota", "content", "org_users", "checkin"],\n'
        + caps_block
        + "    # B 报修/工单",
        "caps",
    )

    ent_block = "".join(
        f'    "{m["domain"]}": DomainEntity("{m["archive"]}", "{m["ticket"]}", "{m["archive"]}_id", "archive"),\n'
        for m in META
    )
    patch(
        B / "domain_entities.py",
        '    "DOM-CHECKIN": DomainEntity("dorm_room", "checkin_apply", "dorm_room_id", "archive"),\n',
        '    "DOM-CHECKIN": DomainEntity("dorm_room", "checkin_apply", "dorm_room_id", "archive"),\n'
        + ent_block,
        "entities",
    )

    fp = B / "schema" / "followup_presets.py"
    t = fp.read_text(encoding="utf-8")
    if "build_mutual_followup_presets" not in t:
        t = t.replace(
            "FOLLOWUP_PRESETS.update(build_checkin_followup_presets(_std_archive_fields))\n",
            "FOLLOWUP_PRESETS.update(build_checkin_followup_presets(_std_archive_fields))\n\n"
            "from app.bake.schema.mutual_followup_presets import build_mutual_followup_presets\n\n"
            "FOLLOWUP_PRESETS.update(build_mutual_followup_presets(_std_archive_fields))\n",
            1,
        )
        fp.write_text(t, encoding="utf-8")
        print("ok followup")
    else:
        print("skip followup")

    tp = B / "schema" / "templates.py"
    tt = tp.read_text(encoding="utf-8")
    if "DOM-MUTUAL-TUTOR" not in tt:
        extra = "\n".join(
            f'SCHEMA_BUILDERS["{m["domain"]}"] = followup_builder("{m["domain"]}")' for m in META
        )
        tp.write_text(tt.rstrip() + "\n\n" + extra + "\n", encoding="utf-8")
        print("ok templates")
    else:
        print("skip templates")

    arch_block = "".join(f'    "{d}": "ARCH-FLOW",\n' for d in domains)
    patch(
        B / "catalog.py",
        '    "DOM-CHECKIN": "ARCH-FLOW",\n',
        '    "DOM-CHECKIN": "ARCH-FLOW",\n' + arch_block,
        "arch",
    )

    flavor = "".join(f'    "{m["domain"]}": "{m["flavor"]}",\n' for m in META)
    patch(B / "domain_skin.py", '    "DOM-CHECKIN": "checkin",\n', '    "DOM-CHECKIN": "checkin",\n' + flavor, "flavor")
    traits = "".join(f'    "{d}": {{"followUp": True}},\n' for d in domains)
    patch(
        B / "domain_skin.py",
        '    "DOM-CHECKIN": {"followUp": True},\n',
        '    "DOM-CHECKIN": {"followUp": True},\n' + traits,
        "traits",
    )
    auth = "".join(
        f'    "{m["domain"]}": "campus {m["flavor"]} mutual selection dual choice",\n' for m in META
    )
    patch(
        B / "domain_skin.py",
        '    "DOM-CHECKIN": "university dormitory night check return checkin",\n',
        '    "DOM-CHECKIN": "university dormitory night check return checkin",\n' + auth,
        "auth",
    )

    java = "".join(
        f'    "{m["domain"]}": {m["pkg"]!r},\n'.replace("'", '"') if False else
        f'    "{m["domain"]}": ("{m["pkg"][0]}", "{m["pkg"][1]}", "{m["pkg"][2]}"),\n'
        for m in META
    )
    patch(
        B / "java_package.py",
        '    "DOM-CHECKIN": ("com.campus.checkin", "CheckinApplication", "checkin-app"),\n',
        '    "DOM-CHECKIN": ("com.campus.checkin", "CheckinApplication", "checkin-app"),\n' + java,
        "java",
    )

    staff = "".join(
        f'    "{m["domain"]}": [_clerk("{m["flavor"]}_clerk", "{m["clerk"]}", "ticket_ops")],\n'
        for m in META
    )
    patch(
        B / "staff_posts.py",
        '    "DOM-CHECKIN": [_clerk("checkin_clerk", "查寝员", "ticket_ops")],\n',
        '    "DOM-CHECKIN": [_clerk("checkin_clerk", "查寝员", "ticket_ops")],\n' + staff,
        "staff",
    )
    ulabel = "".join(f'    "{d}": ("学生", "申请人"),\n' for d in domains)
    patch(
        B / "staff_posts.py",
        '    "DOM-CHECKIN": ("学生", "住宿学生"),\n',
        '    "DOM-CHECKIN": ("学生", "住宿学生"),\n' + ulabel,
        "ulabel",
    )

    frag = "".join(f'    "{d}": ["contact_channel", "next_follow_at"],\n' for d in domains)
    patch(
        B / "sql" / "fragments.py",
        '    "DOM-CHECKIN": ["contact_channel", "next_follow_at"],\n',
        '    "DOM-CHECKIN": ["contact_channel", "next_follow_at"],\n' + frag,
        "frag",
    )
    acol = "".join(
        f'    "{d}": (\n        ("owner_username", "VARCHAR(64) NOT NULL DEFAULT \'\'"),\n    ),\n'
        for d in domains
    )
    # archive_columns uses semantic extras — owner_username already in SQL; use note columns
    acol = "".join(
        f'    "{d}": (\n        ("dept_name", "VARCHAR(100)"),\n        ("note_hint", "VARCHAR(255)"),\n    ),\n'
        for d in domains
    )
    patch(
        B / "archive_columns.py",
        '    "DOM-CHECKIN": (\n        ("building_name", "VARCHAR(100)"),\n        ("room_note", "VARCHAR(255)"),\n    ),\n',
        '    "DOM-CHECKIN": (\n        ("building_name", "VARCHAR(100)"),\n        ("room_note", "VARCHAR(255)"),\n    ),\n'
        + acol,
        "acol",
    )
    trules = "".join(f'    "{d}": {{"max_active": 3}},\n' for d in domains)
    patch(
        B / "ticket_rules.py",
        '    "DOM-CHECKIN": {"max_active": 3},\n',
        '    "DOM-CHECKIN": {"max_active": 3},\n' + trules,
        "trules",
    )

    pf = B / "profile_fields.py"
    pt = pf.read_text(encoding="utf-8")
    if "DOM-MUTUAL-TUTOR" not in pt:
        block = "".join(
            '    "%s": [\n'
            '        _pf("studentNo", "学号", required=True, on_register=True, max_length=32),\n'
            '        _pf("dept", "院系/班级", required=True, on_register=True, max_length=64),\n'
            '        _pf("gradeYear", "年级", on_register=True, max_length=16),\n'
            "    ],\n" % d
            for d in domains
        )
        pt = pt.replace('    "DOM-GENERIC": [\n', block + '    "DOM-GENERIC": [\n', 1)
        pf.write_text(pt, encoding="utf-8")
        print("ok profile")
    else:
        print("skip profile")

    # neighbor hints
    dating = B / "domains_catalog" / "borrow.py"
    dt = dating.read_text(encoding="utf-8")
    old = (
        '            "勿与导师双选/毕设选题互选（另有互选预设）或招聘投递、客户跟进（CRM）混淆。"\n'
    )
    new = (
        '            "勿与导师双选/毕设选题/组队匹配（DOM-MUTUAL-*）或招聘投递、客户跟进（CRM）混淆。"\n'
    )
    if old in dt:
        dating.write_text(dt.replace(old, new, 1), encoding="utf-8")
        print("ok dating hint")
    else:
        print("skip dating hint")

    recruit_old = '            "招聘岗位", "双选会", "求职投递",\n'
    # leave recruit keywords; update hint if present
    if "导师双选" not in dt.split("DOM-RECRUIT")[1][:800] if "DOM-RECRUIT" in dt else "":
        pass

    # themes from checkin.css
    themes_dir = ROOT / "skeletons" / "baseline" / "frontend" / "src" / "styles" / "themes"
    base_css = (themes_dir / "checkin.css").read_text(encoding="utf-8")
    themes_css = themes_dir.parent / "themes.css"
    tc = themes_css.read_text(encoding="utf-8")
    for m in META:
        pref = m["theme_prefix"]
        css_name = f"{pref}.css"
        if not (themes_dir / css_name).exists():
            (themes_dir / css_name).write_text(
                base_css.replace("DOM-CHECKIN checkin", f"{m['domain']} {pref}").replace(
                    "checkin-", f"{pref}-"
                ),
                encoding="utf-8",
            )
        if f"{pref}.css" not in tc:
            tc = tc.replace(
                '@import "./themes/checkin.css";\n',
                f'@import "./themes/checkin.css";\n@import "./themes/{pref}.css";\n',
                1,
            )
    themes_css.write_text(tc, encoding="utf-8")
    print("ok themes")

    sw = ROOT / "frontend" / "src" / "softThemeSwatches.js"
    st = sw.read_text(encoding="utf-8")
    if '"tutor-teal"' not in st:
        insert_parts = []
        for m in META:
            p = m["theme_prefix"]
            insert_parts.append(
                textwrap.dedent(
                    f"""\
                      "{p}-teal": {{
                        "bg": "#eef7f6",
                        "accent": "#2d8a80",
                        "soft": "#d6f0ec",
                        "ink": "#12302c",
                        "surface": "#ffffff"
                      }},
                      "{p}-sand": {{
                        "bg": "#f7f3ec",
                        "accent": "#a67c3d",
                        "soft": "#f0e6d4",
                        "ink": "#2a2418",
                        "surface": "#fffdf9"
                      }},
                      "{p}-slate": {{
                        "bg": "#f0f2f4",
                        "accent": "#475569",
                        "soft": "#e2e8f0",
                        "ink": "#1e293b",
                        "surface": "#ffffff"
                      }},
                      "{p}-night": {{
                        "bg": "#101818",
                        "accent": "#40817a",
                        "soft": "#203028",
                        "ink": "#e8f0ee",
                        "surface": "#182020"
                      }},
                    """
                )
            )
        insert = "".join(insert_parts).rstrip().rstrip(",")
        st = st.replace(
            '\n  "checkin-night": {\n    "bg": "#101818",\n    "accent": "#40817a",\n    "soft": "#203028",\n    "ink": "#e8f0ee",\n    "surface": "#182020"\n  }\n}',
            '\n  "checkin-night": {\n    "bg": "#101818",\n    "accent": "#40817a",\n    "soft": "#203028",\n    "ink": "#e8f0ee",\n    "surface": "#182020"\n  },\n'
            + insert
            + "\n}",
            1,
        )
        sw.write_text(st, encoding="utf-8")
        print("ok swatches")
    else:
        print("skip swatches")

    samples = ROOT / "data" / "samples" / "申请预设开题"
    samples.mkdir(parents=True, exist_ok=True)
    corpus = ROOT / "backend" / "tests" / "fixtures" / "domain_opening_corpus.json"
    data = json.loads(corpus.read_text(encoding="utf-8"))
    for m in META:
        text = textwrap.dedent(
            f"""\
            本科毕业设计（论文）开题报告

            题目：基于 Spring Boot 与 Vue 的{m['title']}的设计与实现

            开题年份：2025
            清单编号：{m['pid']}
            挂靠领域：{m['domain']}

            一、选题背景与意义
            围绕「{m['phrase']}」建设系统，支撑档案浏览、志愿提交与对方确认。

            三、研究目标
            实现档案、志愿互选确认、管理调剂与公告。

            四、技术方案
            Spring Boot + Vue 3 + Element Plus + MySQL。

            五、非本期范围
            智能推荐算法、多轮志愿排序引擎不在本期。
            """
        )
        (samples / f"{m['pid']}-{m['domain']}-{m['title']}.txt").write_text(text, encoding="utf-8")
        if not any(s.get("domain") == m["domain"] for s in data["samples"]):
            data["samples"].append(
                {"domain": m["domain"], "title": m["title"], "year": 2025, "text": text}
            )
    corpus.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("ok samples/corpus")

    # oa_apply_p registry
    (B / "oa_apply_p.py").write_text(
        '"""OA 申请预设 P-01～P-08；互选 P-09～P-11（C-05）。"""\n\n'
        "from __future__ import annotations\n\n"
        "OA_APPLY_CASES: list[tuple[str, str, str, str]] = [\n"
        '    ("P-01", "行政印章使用申请审批", "DOM-SEAL", "学校行政印章使用申请审批系统"),\n'
        '    ("P-02", "公务用车选车申请审批", "DOM-FLEET", "公务用车申请审批管理系统"),\n'
        '    ("P-03", "在读成绩单在职证明开具申请审批", "DOM-CERT", "在读成绩单在职证明开具申请系统"),\n'
        '    ("P-04", "横幅海报户外宣传方案审批", "DOM-PROMO", "横幅海报户外宣传审批管理系统"),\n'
        '    ("P-05", "装修进场施工备案申请审批", "DOM-FITOUT", "装修进场施工备案审批系统"),\n'
        '    ("P-06", "学籍异动转专业缓考申请审批", "DOM-ACAD", "学籍异动转专业缓考申请系统"),\n'
        '    ("P-07", "出差加班申请审批与销结", "DOM-TRIP", "出差加班申请审批管理系统"),\n'
        '    ("P-08", "经费差旅报销单填写与审批", "DOM-EXPENSE", "经费报销申请审批管理系统"),\n'
        "]\n\n"
        "MUTUAL_CASES: list[tuple[str, str, str, str]] = [\n"
        + "".join(
            f'    ("{m["pid"]}", "{m["phrase"]}", "{m["domain"]}", "{m["title"]}"),\n' for m in META
        )
        + "]\n\n"
        "OA_MUTUAL_SKELETON: list[tuple[str, str, str]] = []\n",
        encoding="utf-8",
    )
    print("ok registry")
    print("done")


if __name__ == "__main__":
    main()
