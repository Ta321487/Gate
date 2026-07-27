"""接线 DOM-VISITOR（C-09 / P-17）。"""

from __future__ import annotations

import json
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
B = ROOT / "backend" / "app" / "bake"


def patch(path: Path, old: str, new: str, label: str) -> None:
    t = path.read_text(encoding="utf-8")
    if old not in t:
        if "DOM-VISITOR" in t:
            print("skip", label)
            return
        raise SystemExit(f"miss {label}: {path}")
    path.write_text(t.replace(old, new, 1), encoding="utf-8")
    print("ok", label)


def main() -> None:
    patch(
        B / "domains_catalog" / "__init__.py",
        "from app.bake.domains_catalog.mutual import DOMAINS as MUTUAL_DOMAINS\n",
        "from app.bake.domains_catalog.mutual import DOMAINS as MUTUAL_DOMAINS\n"
        "from app.bake.domains_catalog.visitor import DOMAINS as VISITOR_DOMAINS\n",
        "cat import",
    )
    patch(
        B / "domains_catalog" / "__init__.py",
        "    **MUTUAL_DOMAINS,\n    **FALLBACK_DOMAINS,\n}",
        "    **MUTUAL_DOMAINS,\n    **VISITOR_DOMAINS,\n    **FALLBACK_DOMAINS,\n}",
        "cat merge",
    )
    patch(
        B / "domains.py",
        '            "DOM-MUTUAL-TEAM",\n        ),\n    ),\n    ("ticket", "报修/工单"',
        '            "DOM-MUTUAL-TEAM",\n            "DOM-VISITOR",\n        ),\n    ),\n    ("ticket", "报修/工单"',
        "groups",
    )
    # caps after mutual team line
    t = (B / "domains.py").read_text(encoding="utf-8")
    if '"DOM-VISITOR"' not in t.split("DOMAIN_CAPABILITIES")[1][:4000]:
        patch(
            B / "domains.py",
            '    "DOM-MUTUAL-TEAM": ["archive", "ticket_flow", "quota", "content", "org_users", "mutual_select"],\n',
            '    "DOM-MUTUAL-TEAM": ["archive", "ticket_flow", "quota", "content", "org_users", "mutual_select"],\n'
            '    "DOM-VISITOR": ["archive", "ticket_flow", "quota", "content", "org_users", "pass_code"],\n',
            "caps",
        )
    else:
        print("skip caps")

    patch(
        B / "domain_entities.py",
        '    "DOM-MUTUAL-TEAM": DomainEntity("team_profile", "team_wish", "team_profile_id", "archive"),\n',
        '    "DOM-MUTUAL-TEAM": DomainEntity("team_profile", "team_wish", "team_profile_id", "archive"),\n'
        '    "DOM-VISITOR": DomainEntity("visit_zone", "visitor_apply", "visit_zone_id", "archive"),\n',
        "entities",
    )

    fp = B / "schema" / "followup_presets.py"
    ft = fp.read_text(encoding="utf-8")
    if "build_visitor_followup_presets" not in ft:
        anchor = "FOLLOWUP_PRESETS.update(build_mutual_followup_presets(_std_archive_fields))\n"
        if anchor not in ft:
            anchor = "FOLLOWUP_PRESETS.update(build_checkin_followup_presets(_std_archive_fields))\n"
        fp.write_text(
            ft.replace(
                anchor,
                anchor
                + "\nfrom app.bake.schema.visitor_followup_presets import build_visitor_followup_presets\n\n"
                + "FOLLOWUP_PRESETS.update(build_visitor_followup_presets(_std_archive_fields))\n",
                1,
            ),
            encoding="utf-8",
        )
        print("ok followup")
    else:
        print("skip followup")

    tp = B / "schema" / "templates.py"
    tt = tp.read_text(encoding="utf-8")
    if "DOM-VISITOR" not in tt:
        tp.write_text(
            tt.rstrip() + '\n\nSCHEMA_BUILDERS["DOM-VISITOR"] = followup_builder("DOM-VISITOR")\n',
            encoding="utf-8",
        )
        print("ok templates")
    else:
        print("skip templates")

    patch(B / "catalog.py", '    "DOM-MUTUAL-TEAM": "ARCH-FLOW",\n', '    "DOM-MUTUAL-TEAM": "ARCH-FLOW",\n    "DOM-VISITOR": "ARCH-FLOW",\n', "arch")
    patch(B / "domain_skin.py", '    "DOM-MUTUAL-TEAM": "team",\n', '    "DOM-MUTUAL-TEAM": "team",\n    "DOM-VISITOR": "visitor",\n', "flavor")
    patch(
        B / "domain_skin.py",
        '    "DOM-MUTUAL-TEAM": {"followUp": True},\n',
        '    "DOM-MUTUAL-TEAM": {"followUp": True},\n    "DOM-VISITOR": {"followUp": True},\n',
        "traits",
    )
    patch(
        B / "domain_skin.py",
        '    "DOM-MUTUAL-TEAM": "campus team mutual selection dual choice",\n',
        '    "DOM-MUTUAL-TEAM": "campus team mutual selection dual choice",\n'
        '    "DOM-VISITOR": "campus visitor registration temporary pass",\n',
        "auth",
    )
    patch(
        B / "java_package.py",
        '    "DOM-MUTUAL-TEAM": ("com.campus.team", "TeamApplication", "team-app"),\n',
        '    "DOM-MUTUAL-TEAM": ("com.campus.team", "TeamApplication", "team-app"),\n'
        '    "DOM-VISITOR": ("com.campus.visitor", "VisitorApplication", "visitor-app"),\n',
        "java",
    )
    patch(
        B / "staff_posts.py",
        '    "DOM-MUTUAL-TEAM": [_clerk("team_clerk", "组队协调员", "ticket_ops")],\n',
        '    "DOM-MUTUAL-TEAM": [_clerk("team_clerk", "组队协调员", "ticket_ops")],\n'
        '    "DOM-VISITOR": [_clerk("visitor_clerk", "接待员", "ticket_ops")],\n',
        "staff",
    )
    patch(
        B / "staff_posts.py",
        '    "DOM-MUTUAL-TEAM": ("学生", "申请人"),\n',
        '    "DOM-MUTUAL-TEAM": ("学生", "申请人"),\n    "DOM-VISITOR": ("来访人", "访客"),\n',
        "ulabel",
    )
    patch(
        B / "sql" / "fragments.py",
        '    "DOM-MUTUAL-TEAM": ["contact_channel", "next_follow_at"],\n',
        '    "DOM-MUTUAL-TEAM": ["contact_channel", "next_follow_at"],\n'
        '    "DOM-VISITOR": ["contact_channel", "next_follow_at"],\n',
        "frag",
    )
    patch(
        B / "ticket_rules.py",
        '    "DOM-MUTUAL-TEAM": {"max_active": 3},\n',
        '    "DOM-MUTUAL-TEAM": {"max_active": 3},\n    "DOM-VISITOR": {"max_active": 5},\n',
        "trules",
    )

    pf = B / "profile_fields.py"
    pt = pf.read_text(encoding="utf-8")
    if "DOM-VISITOR" not in pt:
        block = (
            '    "DOM-VISITOR": [\n'
            '        _pf("realName", "姓名", required=True, on_register=True, max_length=32),\n'
            '        _pf("phone", "联系电话", required=True, on_register=True, max_length=20),\n'
            '        _pf("orgOrClub", "来访单位", on_register=True, max_length=64),\n'
            "    ],\n"
        )
        pt = pt.replace('    "DOM-GENERIC": [\n', block + '    "DOM-GENERIC": [\n', 1)
        pf.write_text(pt, encoding="utf-8")
        print("ok profile")
    else:
        print("skip profile")

    # LABSAFE hint
    borrow = B / "domains_catalog" / "borrow.py"
    bt = borrow.read_text(encoding="utf-8")
    if "访客登记" not in bt.split("DOM-LABSAFE", 1)[-1][:600]:
        old = None
        for cand in [
            '            "勿与物资领用（资产领用）混淆。"\n',
            '            "勿与资产领用/耗材申领混淆。"\n',
        ]:
            if cand in bt:
                old = cand
                break
        if old:
            borrow.write_text(
                bt.replace(
                    old,
                    '            "勿与访客到访预约（访客登记）或物资领用混淆。"\n',
                    1,
                ),
                encoding="utf-8",
            )
            print("ok labsafe hint")
        else:
            print("skip labsafe hint")
    else:
        print("skip labsafe hint")

    themes_dir = ROOT / "skeletons" / "baseline" / "frontend" / "src" / "styles" / "themes"
    if not (themes_dir / "visitor.css").exists():
        (themes_dir / "visitor.css").write_text(
            (themes_dir / "checkin.css")
            .read_text(encoding="utf-8")
            .replace("DOM-CHECKIN checkin", "DOM-VISITOR visitor")
            .replace("checkin-", "visitor-"),
            encoding="utf-8",
        )
        themes_css = themes_dir.parent / "themes.css"
        tc = themes_css.read_text(encoding="utf-8")
        if "visitor.css" not in tc:
            themes_css.write_text(
                tc.replace(
                    '@import "./themes/tutor.css";\n',
                    '@import "./themes/tutor.css";\n@import "./themes/visitor.css";\n',
                    1,
                ),
                encoding="utf-8",
            )
        print("ok themes")

    sw = ROOT / "frontend" / "src" / "softThemeSwatches.js"
    st = sw.read_text(encoding="utf-8")
    if '"visitor-teal"' not in st:
        insert = textwrap.dedent(
            """\
              "visitor-teal": {
                "bg": "#eef7f6",
                "accent": "#2d8a80",
                "soft": "#d6f0ec",
                "ink": "#12302c",
                "surface": "#ffffff"
              },
              "visitor-sand": {
                "bg": "#f7f3ec",
                "accent": "#a67c3d",
                "soft": "#f0e6d4",
                "ink": "#2a2418",
                "surface": "#fffdf9"
              },
              "visitor-slate": {
                "bg": "#f0f2f4",
                "accent": "#475569",
                "soft": "#e2e8f0",
                "ink": "#1e293b",
                "surface": "#ffffff"
              },
              "visitor-night": {
                "bg": "#101818",
                "accent": "#40817a",
                "soft": "#203028",
                "ink": "#e8f0ee",
                "surface": "#182020"
              }
            """
        )
        # append before closing of swatches object — find last night block
        for key in ("team-night", "tutor-night", "checkin-night"):
            needle = f'  "{key}": {{\n    "bg": "#101818",\n    "accent": "#40817a",\n    "soft": "#203028",\n    "ink": "#e8f0ee",\n    "surface": "#182020"\n  }}\n}}'
            if needle in st:
                st = st.replace(
                    needle,
                    needle.replace("\n}", ",\n" + insert.rstrip() + "\n}", 1),
                    1,
                )
                break
        else:
            st = st.replace(
                "\n}\n\nconst FALLBACK",
                ",\n" + insert.rstrip().rstrip(",") + "\n}\n\nconst FALLBACK",
                1,
            )
        sw.write_text(st, encoding="utf-8")
        print("ok swatches")
    else:
        print("skip swatches")

    title = "高校访客预约登记与通行码管理系统"
    sample = textwrap.dedent(
        f"""\
        本科毕业设计（论文）开题报告

        题目：基于 Spring Boot 与 Vue 的{title}的设计与实现

        开题年份：2025
        清单编号：P-17
        挂靠领域：DOM-VISITOR

        一、选题背景与意义
        围绕「访客登记 / 临时门禁申请」建设系统，支撑到访区域、预约审核与演示通行码。

        三、研究目标
        实现区域档案、访客申请审核、演示通行码签发与公告。

        四、技术方案
        Spring Boot + Vue 3 + Element Plus + MySQL。

        五、非本期范围
        真门禁硬件、人脸闸机不在本期。
        """
    )
    samples = ROOT / "data" / "samples" / "申请预设开题"
    samples.mkdir(parents=True, exist_ok=True)
    (samples / f"P-17-DOM-VISITOR-{title}.txt").write_text(sample, encoding="utf-8")

    corpus = ROOT / "backend" / "tests" / "fixtures" / "domain_opening_corpus.json"
    data = json.loads(corpus.read_text(encoding="utf-8"))
    if not any(s.get("domain") == "DOM-VISITOR" for s in data["samples"]):
        data["samples"].append({"domain": "DOM-VISITOR", "title": title, "year": 2025, "text": sample})
        corpus.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print("ok corpus")
    else:
        print("skip corpus")

    print("done")


if __name__ == "__main__":
    main()
