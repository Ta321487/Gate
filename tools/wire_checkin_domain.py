"""接线 DOM-CHECKIN（C-10 / P-22）并挂 checkin 能力到 ACTIVITY。"""

from __future__ import annotations

import json
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
B = ROOT / "backend" / "app" / "bake"


def patch(path: Path, old: str, new: str, label: str) -> None:
    t = path.read_text(encoding="utf-8")
    if old not in t:
        if "DOM-CHECKIN" in t and label != "act caps":
            print("skip", label)
            return
        raise SystemExit(f"miss {label}: {path}")
    path.write_text(t.replace(old, new, 1), encoding="utf-8")
    print("ok", label)


def main() -> None:
    patch(
        B / "domains_catalog" / "__init__.py",
        "from app.bake.domains_catalog.bed import DOMAINS as BED_DOMAINS\n",
        "from app.bake.domains_catalog.bed import DOMAINS as BED_DOMAINS\n"
        "from app.bake.domains_catalog.checkin import DOMAINS as CHECKIN_DOMAINS\n",
        "cat import",
    )
    patch(
        B / "domains_catalog" / "__init__.py",
        "    **BED_DOMAINS,\n    **FALLBACK_DOMAINS,\n}",
        "    **BED_DOMAINS,\n    **CHECKIN_DOMAINS,\n    **FALLBACK_DOMAINS,\n}",
        "cat merge",
    )
    patch(
        B / "domains.py",
        '            "DOM-BED",\n        ),\n    ),\n    ("ticket", "报修/工单"',
        '            "DOM-BED",\n            "DOM-CHECKIN",\n        ),\n    ),\n    ("ticket", "报修/工单"',
        "groups",
    )
    patch(
        B / "domains.py",
        '    "DOM-BED": ["archive", "ticket_flow", "quota", "content", "org_users", "bed_occupy"],\n'
        "    # B 报修/工单",
        '    "DOM-BED": ["archive", "ticket_flow", "quota", "content", "org_users", "bed_occupy"],\n'
        '    "DOM-CHECKIN": ["archive", "ticket_flow", "quota", "content", "org_users", "checkin"],\n'
        "    # B 报修/工单",
        "caps",
    )
    patch(
        B / "domains.py",
        '    "DOM-ACTIVITY": ["archive", "ticket_flow", "quota", "content", "org_users", "time_conflict"],\n',
        '    "DOM-ACTIVITY": ["archive", "ticket_flow", "quota", "content", "org_users", "time_conflict", "checkin"],\n',
        "act caps",
    )
    patch(
        B / "domain_entities.py",
        '    "DOM-BED": DomainEntity("bed", "bed_apply", "bed_id", "archive"),\n',
        '    "DOM-BED": DomainEntity("bed", "bed_apply", "bed_id", "archive"),\n'
        '    "DOM-CHECKIN": DomainEntity("dorm_room", "checkin_apply", "dorm_room_id", "archive"),\n',
        "entities",
    )

    fp = B / "schema" / "followup_presets.py"
    t = fp.read_text(encoding="utf-8")
    if "build_checkin_followup_presets" not in t:
        t = t.replace(
            "FOLLOWUP_PRESETS.update(build_bed_followup_presets(_std_archive_fields))\n",
            "FOLLOWUP_PRESETS.update(build_bed_followup_presets(_std_archive_fields))\n\n"
            "from app.bake.schema.checkin_followup_presets import build_checkin_followup_presets\n\n"
            "FOLLOWUP_PRESETS.update(build_checkin_followup_presets(_std_archive_fields))\n",
            1,
        )
        fp.write_text(t, encoding="utf-8")
        print("ok followup")
    else:
        print("skip followup")

    tp = B / "schema" / "templates.py"
    tt = tp.read_text(encoding="utf-8")
    if "DOM-CHECKIN" not in tt:
        tp.write_text(
            tt.rstrip() + '\n\nSCHEMA_BUILDERS["DOM-CHECKIN"] = followup_builder("DOM-CHECKIN")\n',
            encoding="utf-8",
        )
        print("ok templates")
    else:
        print("skip templates")

    patch(
        B / "catalog.py",
        '    "DOM-BED": "ARCH-FLOW",\n',
        '    "DOM-BED": "ARCH-FLOW",\n    "DOM-CHECKIN": "ARCH-FLOW",\n',
        "arch",
    )
    patch(B / "domain_skin.py", '    "DOM-BED": "bed",\n', '    "DOM-BED": "bed",\n    "DOM-CHECKIN": "checkin",\n', "flavor")
    patch(
        B / "domain_skin.py",
        '    "DOM-BED": {"followUp": True},\n',
        '    "DOM-BED": {"followUp": True},\n    "DOM-CHECKIN": {"followUp": True},\n',
        "traits",
    )
    patch(
        B / "domain_skin.py",
        '    "DOM-BED": "university dormitory bed assignment room selection",\n',
        '    "DOM-BED": "university dormitory bed assignment room selection",\n'
        '    "DOM-CHECKIN": "university dormitory night check return checkin",\n',
        "auth",
    )
    patch(
        B / "java_package.py",
        '    "DOM-BED": ("com.campus.bed", "BedApplication", "bed-app"),\n',
        '    "DOM-BED": ("com.campus.bed", "BedApplication", "bed-app"),\n'
        '    "DOM-CHECKIN": ("com.campus.checkin", "CheckinApplication", "checkin-app"),\n',
        "java",
    )
    patch(
        B / "staff_posts.py",
        '    "DOM-BED": [_clerk("bed_clerk", "宿管员", "ticket_ops")],\n',
        '    "DOM-BED": [_clerk("bed_clerk", "宿管员", "ticket_ops")],\n'
        '    "DOM-CHECKIN": [_clerk("checkin_clerk", "查寝员", "ticket_ops")],\n',
        "staff",
    )
    patch(
        B / "staff_posts.py",
        '    "DOM-BED": ("学生", "住宿学生"),\n',
        '    "DOM-BED": ("学生", "住宿学生"),\n    "DOM-CHECKIN": ("学生", "住宿学生"),\n',
        "ulabel",
    )
    patch(
        B / "sql" / "fragments.py",
        '    "DOM-BED": ["contact_channel", "next_follow_at"],\n',
        '    "DOM-BED": ["contact_channel", "next_follow_at"],\n'
        '    "DOM-CHECKIN": ["contact_channel", "next_follow_at"],\n',
        "frag",
    )
    patch(
        B / "archive_columns.py",
        '    "DOM-BED": (\n        ("building_name", "VARCHAR(100)"),\n        ("room_note", "VARCHAR(255)"),\n    ),\n',
        '    "DOM-BED": (\n        ("building_name", "VARCHAR(100)"),\n        ("room_note", "VARCHAR(255)"),\n    ),\n'
        '    "DOM-CHECKIN": (\n        ("building_name", "VARCHAR(100)"),\n        ("room_note", "VARCHAR(255)"),\n    ),\n',
        "acol",
    )
    patch(
        B / "ticket_rules.py",
        '    "DOM-BED": {"max_active": 2},\n',
        '    "DOM-BED": {"max_active": 2},\n    "DOM-CHECKIN": {"max_active": 3},\n',
        "trules",
    )

    pf = B / "profile_fields.py"
    pt = pf.read_text(encoding="utf-8")
    if "DOM-CHECKIN" not in pt:
        block = (
            '    "DOM-CHECKIN": [\n'
            '        _pf("studentNo", "学号", required=True, on_register=True, max_length=32),\n'
            '        _pf("dept", "院系/班级", required=True, on_register=True, max_length=64),\n'
            '        _pf("gradeYear", "年级", on_register=True, max_length=16),\n'
            "    ],\n"
        )
        pt = pt.replace('    "DOM-GENERIC": [\n', block + '    "DOM-GENERIC": [\n', 1)
        pf.write_text(pt, encoding="utf-8")
        print("ok profile")
    else:
        print("skip profile")

    caps = B / "capabilities.py"
    ct = caps.read_text(encoding="utf-8")
    if '"checkin":' not in ct and "'checkin':" not in ct:
        ct = ct.replace(
            '    "bed_occupy": {\n',
            '    "checkin": {\n'
            '        "label": "口令签到",\n'
            '        "status": "implemented",\n'
            '        "desc": "单据口令/列表签到；结束未签到可记爽约或缺勤（C-10；挂 ACTIVITY/CHECKIN）",\n'
            "    },\n"
            '    "bed_occupy": {\n',
            1,
        )
        caps.write_text(ct, encoding="utf-8")
        print("ok capability")
    else:
        print("skip capability")

    # engine_sql: schedule columns when allowCheckin (not only time_conflict)
    es = B / "engine_sql.py"
    et = es.read_text(encoding="utf-8")
    old_sched = "        schedule=TIME_CONFLICT_CAP in caps,\n"
    new_sched = (
        "        schedule=TIME_CONFLICT_CAP in caps or bool(flags.get(\"allowCheckin\")),\n"
    )
    if old_sched in et:
        es.write_text(et.replace(old_sched, new_sched, 1), encoding="utf-8")
        print("ok schedule")
    else:
        print("skip schedule")

    # neighbor hints
    apply_p = B / "domains_catalog" / "apply.py"
    at = apply_p.read_text(encoding="utf-8")
    old_act = (
        '            "勿与第二课堂学分认定、劳动/志愿时长认定（学工预设）或公选课选课混淆。"\n'
    )
    new_act = (
        '            "勿与第二课堂学分认定、劳动/志愿时长认定、宿舍查寝归寝签到（查寝签到）或公选课选课混淆。"\n'
    )
    if old_act in at:
        apply_p.write_text(at.replace(old_act, new_act, 1), encoding="utf-8")
        print("ok act hint")
    else:
        print("skip act hint")

    ticket = B / "domains_catalog" / "ticket.py"
    tt = ticket.read_text(encoding="utf-8")
    old_d = (
        '            "勿与宿舍床位分配/选房/调宿（DOM-BED）混淆；本域仅报修卫生工单。"\n'
    )
    new_d = (
        '            "勿与宿舍床位分配/选房/调宿（DOM-BED）或查寝归寝签到（DOM-CHECKIN）混淆；本域仅报修卫生工单。"\n'
    )
    if old_d in tt:
        ticket.write_text(tt.replace(old_d, new_d, 1), encoding="utf-8")
        print("ok dorm hint")
    else:
        print("skip dorm hint")

    bed = B / "domains_catalog" / "bed.py"
    bt = bed.read_text(encoding="utf-8")
    old_b = (
        '            "勿与宿舍水电报修工单（宿舍报修）或请假考勤混淆。"\n'
    )
    new_b = (
        '            "勿与宿舍水电报修（宿舍报修）、查寝归寝签到（查寝签到）或请假考勤混淆。"\n'
    )
    if old_b in bt:
        bed.write_text(bt.replace(old_b, new_b, 1), encoding="utf-8")
        print("ok bed hint")
    else:
        print("skip bed hint")

    attend = B / "domains_catalog" / "borrow.py"
    ad = attend.read_text(encoding="utf-8")
    old_a = (
        '            "勿与出差/加班审批（DOM-TRIP）、用车申请或公卫健康打卡/晨午检（事件上报）混淆。"\n'
    )
    new_a = (
        '            "勿与宿舍查寝归寝签到（查寝签到）、出差/加班（DOM-TRIP）、用车申请或公卫健康打卡/晨午检混淆。"\n'
    )
    if old_a in ad:
        attend.write_text(ad.replace(old_a, new_a, 1), encoding="utf-8")
        print("ok attend hint")
    else:
        print("skip attend hint")

    # themes
    themes_dir = ROOT / "skeletons" / "baseline" / "frontend" / "src" / "styles" / "themes"
    if not (themes_dir / "checkin.css").exists():
        (themes_dir / "checkin.css").write_text(
            (themes_dir / "bed.css")
            .read_text(encoding="utf-8")
            .replace("DOM-BED bed", "DOM-CHECKIN checkin")
            .replace("bed-", "checkin-"),
            encoding="utf-8",
        )
        themes_css = themes_dir.parent / "themes.css"
        tc = themes_css.read_text(encoding="utf-8")
        if "checkin.css" not in tc:
            themes_css.write_text(
                tc.replace(
                    '@import "./themes/bed.css";\n',
                    '@import "./themes/bed.css";\n@import "./themes/checkin.css";\n',
                    1,
                ),
                encoding="utf-8",
            )
        print("ok themes")
    else:
        print("skip themes")

    sw = ROOT / "frontend" / "src" / "softThemeSwatches.js"
    st = sw.read_text(encoding="utf-8")
    if '"checkin-teal"' not in st:
        insert = textwrap.dedent(
            """\
              "checkin-teal": {
                "bg": "#eef7f6",
                "accent": "#2d8a80",
                "soft": "#d6f0ec",
                "ink": "#12302c",
                "surface": "#ffffff"
              },
              "checkin-sand": {
                "bg": "#f7f3ec",
                "accent": "#a67c3d",
                "soft": "#f0e6d4",
                "ink": "#2a2418",
                "surface": "#fffdf9"
              },
              "checkin-slate": {
                "bg": "#f0f2f4",
                "accent": "#475569",
                "soft": "#e2e8f0",
                "ink": "#1e293b",
                "surface": "#ffffff"
              },
              "checkin-night": {
                "bg": "#101818",
                "accent": "#40817a",
                "soft": "#203028",
                "ink": "#e8f0ee",
                "surface": "#182020"
              }
            """
        )
        st = st.replace(
            '\n  "bed-night": {\n    "bg": "#101818",\n    "accent": "#40817a",\n    "soft": "#203028",\n    "ink": "#e8f0ee",\n    "surface": "#182020"\n  }\n}',
            '\n  "bed-night": {\n    "bg": "#101818",\n    "accent": "#40817a",\n    "soft": "#203028",\n    "ink": "#e8f0ee",\n    "surface": "#182020"\n  },\n'
            + insert.rstrip()
            + "\n}",
            1,
        )
        sw.write_text(st, encoding="utf-8")
        print("ok swatches")
    else:
        print("skip swatches")

    sample_title = "高校宿舍查寝归寝签到管理系统"
    sample_text = textwrap.dedent(
        f"""\
        本科毕业设计（论文）开题报告

        题目：基于 Spring Boot 与 Vue 的{sample_title}的设计与实现

        开题年份：2025
        清单编号：P-22
        挂靠领域：DOM-CHECKIN

        一、选题背景与意义
        围绕「宿舍查寝归寝签到缺勤记录」建设系统，支撑寝室建档、归寝登记与口令签到。

        三、研究目标
        实现寝室档案、归寝登记审核、口令签到与缺勤标记、公告。

        四、技术方案
        Spring Boot + Vue 3 + Element Plus + MySQL。

        五、非本期范围
        人脸签到、GPS 轨迹打卡不在本期。
        """
    )
    samples = ROOT / "data" / "samples" / "学工预设开题"
    samples.mkdir(parents=True, exist_ok=True)
    (samples / f"P-22-DOM-CHECKIN-{sample_title}.txt").write_text(sample_text, encoding="utf-8")

    corpus = ROOT / "backend" / "tests" / "fixtures" / "domain_opening_corpus.json"
    data = json.loads(corpus.read_text(encoding="utf-8"))
    if not any(s.get("domain") == "DOM-CHECKIN" for s in data["samples"]):
        data["samples"].append(
            {"domain": "DOM-CHECKIN", "title": sample_title, "year": 2025, "text": sample_text}
        )
        corpus.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print("ok corpus")
    else:
        print("skip corpus")

    reg = B / "stuwork_p.py"
    reg.write_text(
        '"""学工预设 P-12～P-16；P-20/P-21 床位；P-22 查寝签到。"""\n\n'
        "from __future__ import annotations\n\n"
        "from app.bake.stuwork_meta import STUWORK_META\n\n"
        "STUWORK_CASES: list[tuple[str, str, str, str]] = [\n"
        '    (m["pid"], m["phrase"], m["domain"], m["title"]) for m in STUWORK_META\n'
        "]\n\n"
        "BED_CASES: list[tuple[str, str, str, str]] = [\n"
        '    ("P-20", "新生宿舍床位在线选择分配", "DOM-BED", "高校宿舍床位分配与调宿管理系统"),\n'
        '    ("P-21", "学生宿舍调宿退宿申请审批", "DOM-BED", "学生宿舍调宿退宿申请审批系统"),\n'
        "]\n\n"
        "CHECKIN_CASES: list[tuple[str, str, str, str]] = [\n"
        '    ("P-22", "宿舍查寝归寝签到缺勤记录", "DOM-CHECKIN", "高校宿舍查寝归寝签到管理系统"),\n'
        "]\n\n"
        "STUWORK_BED_SKELETON: list[tuple[str, str, str, str]] = []\n",
        encoding="utf-8",
    )
    print("ok registry")
    print("done")


if __name__ == "__main__":
    main()
