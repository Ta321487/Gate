"""接线 DOM-BED（C-08 / P-20 / P-21）。"""

from __future__ import annotations

import json
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
B = ROOT / "backend" / "app" / "bake"


def patch(path: Path, old: str, new: str, label: str) -> None:
    t = path.read_text(encoding="utf-8")
    if old not in t:
        if "DOM-BED" in t:
            print("skip", label)
            return
        raise SystemExit(f"miss {label}: {path}")
    path.write_text(t.replace(old, new, 1), encoding="utf-8")
    print("ok", label)


def main() -> None:
    patch(
        B / "domains_catalog" / "__init__.py",
        "from app.bake.domains_catalog.stuwork import DOMAINS as STUWORK_DOMAINS\n",
        "from app.bake.domains_catalog.stuwork import DOMAINS as STUWORK_DOMAINS\n"
        "from app.bake.domains_catalog.bed import DOMAINS as BED_DOMAINS\n",
        "cat import",
    )
    patch(
        B / "domains_catalog" / "__init__.py",
        "    **STUWORK_DOMAINS,\n    **FALLBACK_DOMAINS,\n}",
        "    **STUWORK_DOMAINS,\n    **BED_DOMAINS,\n    **FALLBACK_DOMAINS,\n}",
        "cat merge",
    )
    patch(
        B / "domains.py",
        '            "DOM-AWARD",\n        ),\n    ),\n    ("ticket", "报修/工单"',
        '            "DOM-AWARD",\n            "DOM-BED",\n        ),\n    ),\n    ("ticket", "报修/工单"',
        "groups",
    )
    patch(
        B / "domains.py",
        '    "DOM-AWARD": ["archive", "ticket_flow", "content", "org_users"],\n    # B 报修/工单',
        '    "DOM-AWARD": ["archive", "ticket_flow", "content", "org_users"],\n'
        '    "DOM-BED": ["archive", "ticket_flow", "quota", "content", "org_users", "bed_occupy"],\n'
        "    # B 报修/工单",
        "caps",
    )
    patch(
        B / "domain_entities.py",
        '    "DOM-AWARD": DomainEntity("award_item", "award_apply", "award_item_id", "archive"),\n',
        '    "DOM-AWARD": DomainEntity("award_item", "award_apply", "award_item_id", "archive"),\n'
        '    "DOM-BED": DomainEntity("bed", "bed_apply", "bed_id", "archive"),\n',
        "entities",
    )

    fp = B / "schema" / "followup_presets.py"
    t = fp.read_text(encoding="utf-8")
    if "build_bed_followup_presets" not in t:
        t = t.replace(
            "FOLLOWUP_PRESETS.update(build_stuwork_followup_presets(_std_archive_fields))\n",
            "FOLLOWUP_PRESETS.update(build_stuwork_followup_presets(_std_archive_fields))\n\n"
            "from app.bake.schema.bed_followup_presets import build_bed_followup_presets\n\n"
            "FOLLOWUP_PRESETS.update(build_bed_followup_presets(_std_archive_fields))\n",
            1,
        )
        fp.write_text(t, encoding="utf-8")
        print("ok followup")
    else:
        print("skip followup")

    tp = B / "schema" / "templates.py"
    tt = tp.read_text(encoding="utf-8")
    if "DOM-BED" not in tt:
        tp.write_text(tt.rstrip() + '\n\nSCHEMA_BUILDERS["DOM-BED"] = followup_builder("DOM-BED")\n', encoding="utf-8")
        print("ok templates")
    else:
        print("skip templates")

    patch(B / "catalog.py", '    "DOM-AWARD": "ARCH-FLOW",\n', '    "DOM-AWARD": "ARCH-FLOW",\n    "DOM-BED": "ARCH-FLOW",\n', "arch")
    patch(B / "domain_skin.py", '    "DOM-AWARD": "award",\n', '    "DOM-AWARD": "award",\n    "DOM-BED": "bed",\n', "flavor")
    patch(
        B / "domain_skin.py",
        '    "DOM-AWARD": {"followUp": True},\n',
        '    "DOM-AWARD": {"followUp": True},\n    "DOM-BED": {"followUp": True},\n',
        "traits",
    )
    patch(
        B / "domain_skin.py",
        '    "DOM-AWARD": "campus competition award innovation credit desk",\n',
        '    "DOM-AWARD": "campus competition award innovation credit desk",\n'
        '    "DOM-BED": "university dormitory bed assignment room selection",\n',
        "auth",
    )
    patch(
        B / "java_package.py",
        '    "DOM-AWARD": ("com.campus.award", "AwardApplication", "award-app"),\n',
        '    "DOM-AWARD": ("com.campus.award", "AwardApplication", "award-app"),\n'
        '    "DOM-BED": ("com.campus.bed", "BedApplication", "bed-app"),\n',
        "java",
    )
    patch(
        B / "staff_posts.py",
        '    "DOM-AWARD": [_clerk("award_clerk", "成果专员", "ticket_ops")],\n',
        '    "DOM-AWARD": [_clerk("award_clerk", "成果专员", "ticket_ops")],\n'
        '    "DOM-BED": [_clerk("bed_clerk", "宿管员", "ticket_ops")],\n',
        "staff",
    )
    patch(
        B / "staff_posts.py",
        '    "DOM-AWARD": ("学生", "申请人"),\n',
        '    "DOM-AWARD": ("学生", "申请人"),\n    "DOM-BED": ("学生", "住宿学生"),\n',
        "ulabel",
    )
    patch(
        B / "sql" / "fragments.py",
        '    "DOM-AWARD": ["contact_channel", "next_follow_at"],\n',
        '    "DOM-AWARD": ["contact_channel", "next_follow_at"],\n'
        '    "DOM-BED": ["contact_channel", "next_follow_at"],\n',
        "frag",
    )
    patch(
        B / "archive_columns.py",
        '    "DOM-AWARD": (\n        ("dept_name", "VARCHAR(100)"),\n        ("note_hint", "VARCHAR(255)"),\n    ),\n',
        '    "DOM-AWARD": (\n        ("dept_name", "VARCHAR(100)"),\n        ("note_hint", "VARCHAR(255)"),\n    ),\n'
        '    "DOM-BED": (\n        ("building_name", "VARCHAR(100)"),\n        ("room_note", "VARCHAR(255)"),\n    ),\n',
        "acol",
    )
    patch(
        B / "ticket_rules.py",
        '    "DOM-AWARD": {"max_active": 8},\n',
        '    "DOM-AWARD": {"max_active": 8},\n    "DOM-BED": {"max_active": 2},\n',
        "trules",
    )

    pf = B / "profile_fields.py"
    pt = pf.read_text(encoding="utf-8")
    if "DOM-BED" not in pt:
        block = textwrap.dedent(
            """\
            "DOM-BED": [
                _pf("studentNo", "学号", required=True, on_register=True, max_length=32),
                _pf("dept", "院系/班级", required=True, on_register=True, max_length=64),
                _pf("gradeYear", "年级", on_register=True, max_length=16),
            ],
        """
        )
        # keep indent of dict entries
        block = '    "DOM-BED": [\n        _pf("studentNo", "学号", required=True, on_register=True, max_length=32),\n' \
                '        _pf("dept", "院系/班级", required=True, on_register=True, max_length=64),\n' \
                '        _pf("gradeYear", "年级", on_register=True, max_length=16),\n    ],\n'
        pt = pt.replace('    "DOM-GENERIC": [\n', block + '    "DOM-GENERIC": [\n', 1)
        pf.write_text(pt, encoding="utf-8")
        print("ok profile")
    else:
        print("skip profile")

    # capability
    caps = B / "capabilities.py"
    ct = caps.read_text(encoding="utf-8")
    if "bed_occupy" not in ct:
        ct = ct.replace(
            '    "rating_dims": {\n',
            '    "bed_occupy": {\n'
            '        "label": "床位占用",\n'
            '        "status": "implemented",\n'
            '        "desc": "床位档案库存占用 + 选房/调宿申请（C-08；挂 DOM-BED，复用 quota）",\n'
            "    },\n"
            '    "rating_dims": {\n',
            1,
        )
        caps.write_text(ct, encoding="utf-8")
        print("ok capability")
    else:
        print("skip capability")

    # DORM hint
    ticket = B / "domains_catalog" / "ticket.py"
    tt = ticket.read_text(encoding="utf-8")
    old = (
        '            "勿与宿舍床位分配/选房/调宿混淆（床位预设未落地前勿宣称本域已覆盖分床）。"\n'
    )
    new = (
        '            "勿与宿舍床位分配/选房/调宿（DOM-BED）混淆；本域仅报修卫生工单。"\n'
    )
    if old in tt:
        ticket.write_text(tt.replace(old, new, 1), encoding="utf-8")
        print("ok dorm hint")
    else:
        print("skip dorm hint")

    # themes css + swatches (minimal: reuse intern palette as bed-*)
    themes_dir = ROOT / "skeletons" / "baseline" / "frontend" / "src" / "styles" / "themes"
    if not (themes_dir / "bed.css").exists():
        (themes_dir / "bed.css").write_text(
            (themes_dir / "credit.css").read_text(encoding="utf-8")
            .replace("DOM-CREDIT credit", "DOM-BED bed")
            .replace("credit-", "bed-"),
            encoding="utf-8",
        )
        themes_css = themes_dir.parent / "themes.css"
        tc = themes_css.read_text(encoding="utf-8")
        if "bed.css" not in tc:
            themes_css.write_text(
                tc.replace(
                    '@import "./themes/award.css";\n',
                    '@import "./themes/award.css";\n@import "./themes/bed.css";\n',
                    1,
                ),
                encoding="utf-8",
            )
        print("ok themes")
    sw = ROOT / "frontend" / "src" / "softThemeSwatches.js"
    st = sw.read_text(encoding="utf-8")
    if '"bed-teal"' not in st:
        chunk = ""
        for tid, src in [
            ("bed-teal", "credit-teal"),
            ("bed-sand", "credit-sand"),
            ("bed-slate", "credit-slate"),
            ("bed-night", "credit-night"),
        ]:
            # copy block from credit if present
            pass
        # simple append using credit colors
        insert = textwrap.dedent(
            """\
              "bed-teal": {
                "bg": "#eef7f6",
                "accent": "#2d8a80",
                "soft": "#d6f0ec",
                "ink": "#12302c",
                "surface": "#ffffff"
              },
              "bed-sand": {
                "bg": "#f7f3ec",
                "accent": "#a67c3d",
                "soft": "#f0e6d4",
                "ink": "#2a2418",
                "surface": "#fffdf9"
              },
              "bed-slate": {
                "bg": "#f0f2f4",
                "accent": "#475569",
                "soft": "#e2e8f0",
                "ink": "#1e293b",
                "surface": "#ffffff"
              },
              "bed-night": {
                "bg": "#101818",
                "accent": "#40817a",
                "soft": "#203028",
                "ink": "#e8f0ee",
                "surface": "#182020"
              },
            """
        )
        st = st.replace("\n}\n\nconst FALLBACK", ",\n" + insert.rstrip().rstrip(",") + "\n}\n\nconst FALLBACK", 1)
        sw.write_text(st, encoding="utf-8")
        print("ok swatches")

    # corpus sample
    sample_title = "高校宿舍床位分配与调宿管理系统"
    sample_text = textwrap.dedent(
        f"""\
        本科毕业设计（论文）开题报告

        题目：基于 Spring Boot 与 Vue 的{sample_title}的设计与实现

        开题年份：2025
        清单编号：P-20
        挂靠领域：DOM-BED

        一、选题背景与意义
        围绕「新生宿舍床位在线选择分配与调宿退宿申请审批」建设系统，支撑床位建档、选房申请与审核占用。

        三、研究目标
        实现床位档案、选房/调宿申请审核、库存占用与公告。

        四、技术方案
        Spring Boot + Vue 3 + Element Plus + MySQL。

        五、非本期范围
        智能排宿算法、门锁硬件不在本期。
        """
    )
    samples = ROOT / "data" / "samples" / "学工预设开题"
    samples.mkdir(parents=True, exist_ok=True)
    (samples / f"P-20-DOM-BED-{sample_title}.txt").write_text(sample_text, encoding="utf-8")
    (samples / "P-21-DOM-BED-学生宿舍调宿退宿申请审批系统.txt").write_text(
        sample_text.replace("P-20", "P-21").replace("新生宿舍床位在线选择分配与调宿退宿申请审批", "学生宿舍调宿退宿申请审批"),
        encoding="utf-8",
    )

    corpus = ROOT / "backend" / "tests" / "fixtures" / "domain_opening_corpus.json"
    data = json.loads(corpus.read_text(encoding="utf-8"))
    if not any(s.get("domain") == "DOM-BED" for s in data["samples"]):
        data["samples"].append(
            {"domain": "DOM-BED", "title": sample_title, "year": 2025, "text": sample_text}
        )
        corpus.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print("ok corpus")
    else:
        print("skip corpus")

    # update stuwork_p skeleton: P-20/21 done, P-22 remains
    reg = B / "stuwork_p.py"
    reg.write_text(
        '"""学工预设 P-12～P-16；P-20/P-21 床位已挂 DOM-BED；P-22 骨架待 C-10。"""\n\n'
        "from __future__ import annotations\n\n"
        "from app.bake.stuwork_meta import STUWORK_META\n\n"
        "STUWORK_CASES: list[tuple[str, str, str, str]] = [\n"
        '    (m["pid"], m["phrase"], m["domain"], m["title"]) for m in STUWORK_META\n'
        "]\n\n"
        "BED_CASES: list[tuple[str, str, str, str]] = [\n"
        '    ("P-20", "新生宿舍床位在线选择分配", "DOM-BED", "高校宿舍床位分配与调宿管理系统"),\n'
        '    ("P-21", "学生宿舍调宿退宿申请审批", "DOM-BED", "学生宿舍调宿退宿申请审批系统"),\n'
        "]\n\n"
        "STUWORK_BED_SKELETON: list[tuple[str, str, str, str]] = [\n"
        '    ("P-22", "宿舍查寝归寝签到缺勤记录", "DOM-CHECKIN", "C-10"),\n'
        "]\n",
        encoding="utf-8",
    )
    print("ok registry")
    print("done")


if __name__ == "__main__":
    main()
