"""接线长尾预设 P-18、P-23～P-29（先跑 gen_tail_domains.py）。"""

from __future__ import annotations

import json
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
B = ROOT / "backend" / "app" / "bake"


def patch(path: Path, old: str, new: str, label: str) -> None:
    t = path.read_text(encoding="utf-8")
    if old not in t:
        if "DOM-CARPASS" in t:
            print("skip", label)
            return
        raise SystemExit(f"miss {label}: {path}")
    path.write_text(t.replace(old, new, 1), encoding="utf-8")
    print("ok", label)


def main() -> None:
    import sys

    sys.path.insert(0, str(ROOT / "backend"))
    from app.bake.tail_meta import TAIL_META as META

    domains = [m["domain"] for m in META]

    patch(
        B / "domains_catalog" / "__init__.py",
        "from app.bake.domains_catalog.visitor import DOMAINS as VISITOR_DOMAINS\n",
        "from app.bake.domains_catalog.visitor import DOMAINS as VISITOR_DOMAINS\n"
        "from app.bake.domains_catalog.tail import DOMAINS as TAIL_DOMAINS\n",
        "cat import",
    )
    patch(
        B / "domains_catalog" / "__init__.py",
        "    **VISITOR_DOMAINS,\n    **FALLBACK_DOMAINS,\n}",
        "    **VISITOR_DOMAINS,\n    **TAIL_DOMAINS,\n    **FALLBACK_DOMAINS,\n}",
        "cat merge",
    )

    group = ",\n            ".join(f'"{d}"' for d in domains)
    patch(
        B / "domains.py",
        '            "DOM-VISITOR",\n        ),\n    ),\n    ("ticket", "报修/工单"',
        '            "DOM-VISITOR",\n'
        f"            {group},\n"
        '        ),\n    ),\n    ("ticket", "报修/工单"',
        "groups",
    )

    caps = "".join(
        '    "{}": [{}],\n'.format(m["domain"], ", ".join(f'"{c}"' for c in m["caps"]))
        for m in META
    )
    patch(
        B / "domains.py",
        '    "DOM-VISITOR": ["archive", "ticket_flow", "quota", "content", "org_users", "pass_code"],\n',
        '    "DOM-VISITOR": ["archive", "ticket_flow", "quota", "content", "org_users", "pass_code"],\n'
        + caps,
        "caps",
    )

    ents = "".join(
        f'    "{m["domain"]}": DomainEntity("{m["archive"]}", "{m["ticket"]}", "{m["archive"]}_id", "archive"),\n'
        for m in META
    )
    patch(
        B / "domain_entities.py",
        '    "DOM-VISITOR": DomainEntity("visit_zone", "visitor_apply", "visit_zone_id", "archive"),\n',
        '    "DOM-VISITOR": DomainEntity("visit_zone", "visitor_apply", "visit_zone_id", "archive"),\n'
        + ents,
        "entities",
    )

    fp = B / "schema" / "followup_presets.py"
    ft = fp.read_text(encoding="utf-8")
    if "build_tail_followup_presets" not in ft:
        for anchor in [
            "FOLLOWUP_PRESETS.update(build_visitor_followup_presets(_std_archive_fields))\n",
            "FOLLOWUP_PRESETS.update(build_mutual_followup_presets(_std_archive_fields))\n",
        ]:
            if anchor in ft:
                fp.write_text(
                    ft.replace(
                        anchor,
                        anchor
                        + "\nfrom app.bake.schema.tail_followup_presets import build_tail_followup_presets\n\n"
                        + "FOLLOWUP_PRESETS.update(build_tail_followup_presets(_std_archive_fields))\n",
                        1,
                    ),
                    encoding="utf-8",
                )
                print("ok followup")
                break
        else:
            raise SystemExit("miss followup anchor")
    else:
        print("skip followup")

    tp = B / "schema" / "templates.py"
    tt = tp.read_text(encoding="utf-8")
    if "DOM-CARPASS" not in tt:
        extra = "\n".join(
            f'SCHEMA_BUILDERS["{m["domain"]}"] = followup_builder("{m["domain"]}")' for m in META
        )
        tp.write_text(tt.rstrip() + "\n\n" + extra + "\n", encoding="utf-8")
        print("ok templates")
    else:
        print("skip templates")

    arch = "".join(f'    "{d}": "ARCH-FLOW",\n' for d in domains)
    patch(B / "catalog.py", '    "DOM-VISITOR": "ARCH-FLOW",\n', '    "DOM-VISITOR": "ARCH-FLOW",\n' + arch, "arch")

    flavor = "".join(f'    "{m["domain"]}": "{m["flavor"]}",\n' for m in META)
    patch(B / "domain_skin.py", '    "DOM-VISITOR": "visitor",\n', '    "DOM-VISITOR": "visitor",\n' + flavor, "flavor")
    traits = "".join(f'    "{d}": {{"followUp": True}},\n' for d in domains)
    patch(
        B / "domain_skin.py",
        '    "DOM-VISITOR": {"followUp": True},\n',
        '    "DOM-VISITOR": {"followUp": True},\n' + traits,
        "traits",
    )
    auth = "".join(f'    "{m["domain"]}": "{m["auth_q"]}",\n' for m in META)
    patch(
        B / "domain_skin.py",
        '    "DOM-VISITOR": "campus visitor registration temporary pass",\n',
        '    "DOM-VISITOR": "campus visitor registration temporary pass",\n' + auth,
        "auth",
    )

    java = "".join(
        f'    "{m["domain"]}": ("{m["pkg"][0]}", "{m["pkg"][1]}", "{m["pkg"][2]}"),\n' for m in META
    )
    patch(
        B / "java_package.py",
        '    "DOM-VISITOR": ("com.campus.visitor", "VisitorApplication", "visitor-app"),\n',
        '    "DOM-VISITOR": ("com.campus.visitor", "VisitorApplication", "visitor-app"),\n' + java,
        "java",
    )

    staff = "".join(
        f'    "{m["domain"]}": [_clerk("{m["flavor"]}_clerk", "{m["clerk"]}", "ticket_ops")],\n'
        for m in META
    )
    patch(
        B / "staff_posts.py",
        '    "DOM-VISITOR": [_clerk("visitor_clerk", "接待员", "ticket_ops")],\n',
        '    "DOM-VISITOR": [_clerk("visitor_clerk", "接待员", "ticket_ops")],\n' + staff,
        "staff",
    )
    ulabel = "".join(f'    "{d}": ("申请人", "用户"),\n' for d in domains)
    patch(
        B / "staff_posts.py",
        '    "DOM-VISITOR": ("来访人", "访客"),\n',
        '    "DOM-VISITOR": ("来访人", "访客"),\n' + ulabel,
        "ulabel",
    )

    frag = "".join(f'    "{d}": ["contact_channel", "next_follow_at"],\n' for d in domains)
    patch(
        B / "sql" / "fragments.py",
        '    "DOM-VISITOR": ["contact_channel", "next_follow_at"],\n',
        '    "DOM-VISITOR": ["contact_channel", "next_follow_at"],\n' + frag,
        "frag",
    )
    trules = "".join(f'    "{d}": {{"max_active": 5}},\n' for d in domains)
    patch(
        B / "ticket_rules.py",
        '    "DOM-VISITOR": {"max_active": 5},\n',
        '    "DOM-VISITOR": {"max_active": 5},\n' + trules,
        "trules",
    )

    pf = B / "profile_fields.py"
    pt = pf.read_text(encoding="utf-8")
    if "DOM-CARPASS" not in pt:
        block = "".join(
            '    "%s": [\n'
            '        _pf("studentNo", "学号/工号", required=True, on_register=True, max_length=32),\n'
            '        _pf("dept", "院系/部门", required=True, on_register=True, max_length=64),\n'
            "    ],\n" % d
            for d in domains
        )
        anchor = (
            '    "DOM-VISITOR": [\n'
            '        _pf("orgOrClub", "来访单位", required=True, on_register=True, max_length=64),\n'
            '        _pf("idCardLast4", "证件后四位", on_register=True, max_length=8),\n'
            '        _pf("hostDept", "被访部门", on_register=True, max_length=64),\n'
            "    ],\n"
        )
        if anchor not in pt:
            raise SystemExit("miss profile anchor")
        pf.write_text(pt.replace(anchor, anchor + block, 1), encoding="utf-8")
        print("ok profile")
    else:
        print("skip profile")

    # neighbor hints
    park = B / "domains_catalog" / "reserve.py"
    if park.is_file():
        rt = park.read_text(encoding="utf-8")
        old = (
            '            "适用：停车场车位时段预约；充电桩/共享车位长尾亦挂本域。"\n'
            '            "勿与场地预约（会议室/球馆）或客房预订混淆。"\n'
        )
        new = (
            '            "适用：停车场车位时段预约；充电桩/共享车位长尾亦挂本域。"\n'
            '            "勿与场地预约（会议室/球馆）、客房预订或车辆通行证/车牌备案混淆。"\n'
        )
        if old in rt:
            park.write_text(rt.replace(old, new, 1), encoding="utf-8")
            print("ok parking hint")
        else:
            print("skip parking hint")

    # themes + swatches (reuse visitor palette)
    themes_dir = ROOT / "skeletons" / "baseline" / "frontend" / "src" / "styles" / "themes"
    base = (themes_dir / "visitor.css").read_text(encoding="utf-8")
    themes_css = themes_dir.parent / "themes.css"
    tc = themes_css.read_text(encoding="utf-8")
    for m in META:
        css = f'{m["flavor"]}.css'
        if not (themes_dir / css).exists():
            (themes_dir / css).write_text(
                base.replace("DOM-VISITOR visitor", f'{m["domain"]} {m["flavor"]}').replace(
                    "visitor-", f'{m["flavor"]}-'
                ),
                encoding="utf-8",
            )
        if css not in tc:
            tc = tc.replace(
                '@import "./themes/visitor.css";\n',
                f'@import "./themes/visitor.css";\n@import "./themes/{css}";\n',
                1,
            )
    themes_css.write_text(tc, encoding="utf-8")
    print("ok themes")

    sw = ROOT / "frontend" / "src" / "softThemeSwatches.js"
    st = sw.read_text(encoding="utf-8")
    if "carpass-teal" not in st:
        parts = []
        for m in META:
            p = m["flavor"]
            for tid, bg, accent, soft, ink, surface in [
                ("teal", "#eef7f6", "#2d8a80", "#d6f0ec", "#12302c", "#ffffff"),
                ("sand", "#f7f3ec", "#a67c3d", "#f0e6d4", "#2a2418", "#fffdf9"),
                ("slate", "#f0f2f4", "#475569", "#e2e8f0", "#1e293b", "#ffffff"),
                ("night", "#101818", "#40817a", "#203028", "#e8f0ee", "#182020"),
            ]:
                parts.append(
                    f'"{p}-{tid}": {{\n'
                    f'  "bg": "{bg}",\n'
                    f'  "accent": "{accent}",\n'
                    f'  "soft": "{soft}",\n'
                    f'  "ink": "{ink}",\n'
                    f'  "surface": "{surface}"\n'
                    f"}},\n"
                )
        insert = "".join(parts).rstrip().rstrip(",")
        anchor = (
            '"visitor-night": {\n'
            '  "bg": "#101818",\n'
            '  "accent": "#40817a",\n'
            '  "soft": "#203028",\n'
            '  "ink": "#e8f0ee",\n'
            '  "surface": "#182020"\n'
            "}\n}"
        )
        if anchor not in st:
            raise SystemExit("miss swatches anchor")
        st = st.replace(
            anchor,
            '"visitor-night": {\n'
            '  "bg": "#101818",\n'
            '  "accent": "#40817a",\n'
            '  "soft": "#203028",\n'
            '  "ink": "#e8f0ee",\n'
            '  "surface": "#182020"\n'
            "},\n"
            + insert
            + "\n}",
            1,
        )
        sw.write_text(st, encoding="utf-8")
        print("ok swatches")
    else:
        print("skip swatches")

    samples = ROOT / "data" / "samples" / "长尾预设开题"
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
            围绕「{m['phrase']}」建设系统。

            三、研究目标
            实现档案、申请审批与公告。

            四、技术方案
            Spring Boot + Vue 3 + Element Plus + MySQL。

            五、非本期范围
            外部系统对接、电子签章 CA 不在本期。
            """
        )
        (samples / f"{m['pid']}-{m['domain']}-{m['title']}.txt").write_text(text, encoding="utf-8")
        if not any(s.get("domain") == m["domain"] for s in data["samples"]):
            data["samples"].append(
                {"domain": m["domain"], "title": m["title"], "year": 2025, "text": text}
            )
    corpus.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("ok samples/corpus")

    # registry
    (B / "tail_p.py").write_text(
        '"""长尾预设 P-18、P-23～P-29 验收表。"""\n\n'
        "from __future__ import annotations\n\n"
        "from app.bake.tail_meta import TAIL_META\n\n"
        "TAIL_CASES: list[tuple[str, str, str, str]] = [\n"
        '    (m["pid"], m["phrase"], m["domain"], m["title"]) for m in TAIL_META\n'
        "]\n",
        encoding="utf-8",
    )
    print("ok registry")

    # P-30: document-only — mark via help note in gap doc later
    print("done")


if __name__ == "__main__":
    main()
