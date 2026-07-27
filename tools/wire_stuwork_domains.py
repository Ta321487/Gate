"""把 P-12～P-16 学工域接到现网（在 gen_stuwork_domains.py 之后）。"""

from __future__ import annotations

import json
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend" / "app" / "bake"

STU_META = [
    ("P-12", "DOM-CREDIT", "credit", "credit_item", "credit_apply", "认定专员", "com.campus.credit", "CreditApplication", "credit-app"),
    ("P-13", "DOM-LABOR", "labor", "labor_item", "labor_apply", "劳动专员", "com.campus.labor", "LaborApplication", "labor-app"),
    ("P-14", "DOM-EVAL", "eval", "eval_course", "eval_sheet", "评教员", "com.campus.eval", "EvalApplication", "eval-app"),
    ("P-15", "DOM-MORAL", "moral", "moral_item", "moral_apply", "综测专员", "com.campus.moral", "MoralApplication", "moral-app"),
    ("P-16", "DOM-AWARD", "award", "award_item", "award_apply", "成果专员", "com.campus.award", "AwardApplication", "award-app"),
]

THEME_PALETTES = {
    "teal": ("#eef7f6", "#2d8a80", "#d6f0ec", "#12302c", "#ffffff"),
    "sand": ("#f7f3ec", "#a67c3d", "#f0e6d4", "#2a2418", "#fffdf9"),
    "slate": ("#f0f2f4", "#475569", "#e2e8f0", "#1e293b", "#ffffff"),
    "night": ("#101818", "#40817a", "#203028", "#e8f0ee", "#182020"),
}


def _patch_once(path: Path, old: str, new: str, *, label: str) -> None:
    text = path.read_text(encoding="utf-8")
    if old not in text:
        if new.strip() in text or (label.startswith("skip-ok") is False and any(
            d in text for _, d, *_ in STU_META
        ) and "DOM-CREDIT" in text and label != "catalog import"):
            # allow idempotent skips when already present
            print(f"skip {label}: already present or anchor gone")
            return
        raise SystemExit(f"patch miss {label}: {path}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")
    print(f"patched {label}")


def write_followup_module() -> None:
    src = (BACKEND / "schema" / "_stuwork_presets_generated.py").read_text(encoding="utf-8")
    body = src.replace("# AUTO\nSTU_PRESET_BLOCKS = {\n", "")
    inner = body.rsplit("}", 1)[0]
    out = (
        '"""学工预设 FOLLOWUP_PRESETS（P-12～P-16）。"""\n\n'
        "from __future__ import annotations\n\n"
        "from typing import Any, Callable\n\n\n"
        "def build_stuwork_followup_presets(\n"
        "    _std_archive_fields: Callable[..., list[dict[str, Any]]],\n"
        ") -> dict[str, dict[str, Any]]:\n"
        "    return {\n"
        + inner
        + "    }\n"
    )
    path = BACKEND / "schema" / "stuwork_followup_presets.py"
    path.write_text(out, encoding="utf-8")
    print("wrote", path)


def merge_followup() -> None:
    path = BACKEND / "schema" / "followup_presets.py"
    text = path.read_text(encoding="utf-8")
    if "build_stuwork_followup_presets" in text:
        print("skip followup merge")
        return
    inject = (
        "\nfrom app.bake.schema.stuwork_followup_presets import build_stuwork_followup_presets\n\n"
        "FOLLOWUP_PRESETS.update(build_stuwork_followup_presets(_std_archive_fields))\n\n\n"
        "def _attach_event_archive_log"
    )
    old = "\n\n\ndef _attach_event_archive_log"
    if old not in text:
        raise SystemExit("followup anchor miss")
    path.write_text(text.replace(old, inject, 1), encoding="utf-8")
    print("patched followup merge")


def wire_all() -> None:
    # catalog
    _patch_once(
        BACKEND / "domains_catalog" / "__init__.py",
        "from app.bake.domains_catalog.oa import DOMAINS as OA_DOMAINS\n",
        "from app.bake.domains_catalog.oa import DOMAINS as OA_DOMAINS\n"
        "from app.bake.domains_catalog.stuwork import DOMAINS as STUWORK_DOMAINS\n",
        label="catalog import",
    )
    _patch_once(
        BACKEND / "domains_catalog" / "__init__.py",
        "    **OA_DOMAINS,\n    **FALLBACK_DOMAINS,\n}",
        "    **OA_DOMAINS,\n    **STUWORK_DOMAINS,\n    **FALLBACK_DOMAINS,\n}",
        label="catalog merge",
    )

    domains = ",\n            ".join(f'"{d}"' for _, d, *_ in STU_META)
    _patch_once(
        BACKEND / "domains.py",
        '            "DOM-EXPENSE",\n        ),\n    ),\n    ("ticket", "报修/工单"',
        f'            "DOM-EXPENSE",\n            {domains},\n        ),\n    ),\n    ("ticket", "报修/工单"',
        label="DOMAIN_GROUPS",
    )
    caps = "".join(
        f'    "{d}": ["archive", "ticket_flow", "content", "org_users"],\n' for _, d, *_ in STU_META
    )
    _patch_once(
        BACKEND / "domains.py",
        '    "DOM-EXPENSE": ["archive", "ticket_flow", "content", "org_users"],\n    # B 报修/工单',
        '    "DOM-EXPENSE": ["archive", "ticket_flow", "content", "org_users"],\n'
        + caps
        + "    # B 报修/工单",
        label="DOMAIN_CAPABILITIES",
    )

    ents = "".join(
        f'    "{d}": DomainEntity("{arch}", "{ticket}", "{arch}_id", "archive"),\n'
        for _, d, _fl, arch, ticket, *_ in STU_META
    )
    _patch_once(
        BACKEND / "domain_entities.py",
        '    "DOM-EXPENSE": DomainEntity("expense_project", "expense_apply", "expense_project_id", "archive"),\n',
        '    "DOM-EXPENSE": DomainEntity("expense_project", "expense_apply", "expense_project_id", "archive"),\n'
        + ents,
        label="DOMAIN_ENTITIES",
    )

    # templates
    tp = BACKEND / "schema" / "templates.py"
    tt = tp.read_text(encoding="utf-8")
    if "STUWORK_META" not in tt:
        tt = tt.replace(
            "from app.bake.oa_apply_meta import OA_APPLY_META\n",
            "from app.bake.oa_apply_meta import OA_APPLY_META\n"
            "from app.bake.stuwork_meta import STUWORK_META\n",
            1,
        )
        tt = tt.rstrip() + (
            "\n\nfor _m in STUWORK_META:\n"
            '    SCHEMA_BUILDERS[_m["domain"]] = followup_builder(_m["domain"])\n'
        )
        tp.write_text(tt, encoding="utf-8")
        print("patched templates")
    else:
        print("skip templates")

    arch_block = "".join(f'    "{d}": "ARCH-FLOW",\n' for _, d, *_ in STU_META)
    _patch_once(
        BACKEND / "catalog.py",
        '    "DOM-EXPENSE": "ARCH-FLOW",\n',
        '    "DOM-EXPENSE": "ARCH-FLOW",\n' + arch_block,
        label="_DOMAIN_DEFAULT_ARCH",
    )

    from app.bake.stuwork_meta import STUWORK_META as meta  # type: ignore

    flav = "".join(f'    "{d}": "{fl}",\n' for _, d, fl, *_ in STU_META)
    traits = "".join(f'    "{d}": {{"followUp": True}},\n' for _, d, *_ in STU_META)
    auth = "".join(f'    "{m["domain"]}": "{m["auth_q"]}",\n' for m in meta)
    skin = BACKEND / "domain_skin.py"
    _patch_once(skin, '    "DOM-EXPENSE": "expense",\n', '    "DOM-EXPENSE": "expense",\n' + flav, label="flavor")
    _patch_once(
        skin,
        '    "DOM-EXPENSE": {"followUp": True},\n',
        '    "DOM-EXPENSE": {"followUp": True},\n' + traits,
        label="traits",
    )
    _patch_once(
        skin,
        '    "DOM-EXPENSE": "expense reimbursement finance desk",\n',
        '    "DOM-EXPENSE": "expense reimbursement finance desk",\n' + auth,
        label="auth_q",
    )

    java = "".join(
        f'    "{d}": ("{pkg}", "{app}", "{art}"),\n'
        for _, d, _fl, _a, _t, _c, pkg, app, art in STU_META
    )
    _patch_once(
        BACKEND / "java_package.py",
        '    "DOM-EXPENSE": ("com.campus.expense", "ExpenseApplication", "expense-app"),\n',
        '    "DOM-EXPENSE": ("com.campus.expense", "ExpenseApplication", "expense-app"),\n' + java,
        label="java",
    )

    staff = "".join(
        f'    "{d}": [_clerk("{fl}_clerk", "{clerk}", "ticket_ops")],\n'
        for _, d, fl, _a, _t, clerk, *_ in STU_META
    )
    _patch_once(
        BACKEND / "staff_posts.py",
        '    "DOM-EXPENSE": [_clerk("expense_clerk", "报销审核员", "ticket_ops")],\n',
        '    "DOM-EXPENSE": [_clerk("expense_clerk", "报销审核员", "ticket_ops")],\n' + staff,
        label="staff",
    )
    ulines = "".join(f'    "{d}": ("学生", "申请人"),\n' for _, d, *_ in STU_META)
    _patch_once(
        BACKEND / "staff_posts.py",
        '    "DOM-EXPENSE": ("报销人", "申请人"),\n',
        '    "DOM-EXPENSE": ("报销人", "申请人"),\n' + ulines,
        label="user labels",
    )

    frag = "".join(
        f'    "{d}": ["contact_channel", "next_follow_at"],\n' for _, d, *_ in STU_META
    )
    # EVAL also needs rating columns via allow_rating flag in schema; domain columns stay contact
    _patch_once(
        BACKEND / "sql" / "fragments.py",
        '    "DOM-EXPENSE": ["contact_channel", "next_follow_at"],\n',
        '    "DOM-EXPENSE": ["contact_channel", "next_follow_at"],\n' + frag,
        label="fragments",
    )
    # DOM-EVAL rating via ticket flags — also list in TICKET_DOMAIN_COLUMNS if needed
    ft = (BACKEND / "sql" / "fragments.py").read_text(encoding="utf-8")
    if '"DOM-EVAL": ["contact_channel", "next_follow_at"]' in ft:
        ft = ft.replace(
            '"DOM-EVAL": ["contact_channel", "next_follow_at"]',
            '"DOM-EVAL": ["contact_channel", "next_follow_at", "rating", "rating_remark", "rated_at"]',
            1,
        )
        (BACKEND / "sql" / "fragments.py").write_text(ft, encoding="utf-8")
        print("patched EVAL rating columns")

    ablock = "".join(
        f'    "{d}": (\n'
        f'        ("dept_name", "VARCHAR(100)"),\n'
        f'        ("note_hint", "VARCHAR(255)"),\n'
        f"    ),\n"
        for _, d, *_ in STU_META
    )
    _patch_once(
        BACKEND / "archive_columns.py",
        '    "DOM-EXPENSE": (\n        ("dept_name", "VARCHAR(100)"),\n        ("note_hint", "VARCHAR(255)"),\n    ),\n',
        '    "DOM-EXPENSE": (\n        ("dept_name", "VARCHAR(100)"),\n        ("note_hint", "VARCHAR(255)"),\n    ),\n'
        + ablock,
        label="archive_columns",
    )

    rules = "".join(f'    "{d}": {{"max_active": 8}},\n' for _, d, *_ in STU_META)
    _patch_once(
        BACKEND / "ticket_rules.py",
        '    "DOM-EXPENSE": {"max_active": 5},\n',
        '    "DOM-EXPENSE": {"max_active": 5},\n' + rules,
        label="ticket_rules",
    )

    # profile — student fields
    pf = BACKEND / "profile_fields.py"
    pt = pf.read_text(encoding="utf-8")
    if "DOM-CREDIT" not in pt:
        fields = textwrap.dedent(
            """\
                _pf("studentNo", "学号", required=True, on_register=True, max_length=32),
                _pf("dept", "院系/班级", required=True, on_register=True, max_length=64),
                _pf("gradeYear", "年级", on_register=True, max_length=16),
        """
        )
        block = "".join(f'    "{d}": [\n{fields}    ],\n' for _, d, *_ in STU_META)
        pf.write_text(pt.replace('    "DOM-GENERIC": [\n', block + '    "DOM-GENERIC": [\n', 1), encoding="utf-8")
        print("patched profile")
    else:
        print("skip profile")


def write_themes() -> None:
    themes_dir = ROOT / "skeletons" / "baseline" / "frontend" / "src" / "styles" / "themes"
    imports = []
    for _, d, fl, *_ in STU_META:
        lines = [f"/* —— {d} {fl} —— */"]
        for variant, (bg, accent, soft, ink, surface) in THEME_PALETTES.items():
            tid = f"{fl}-{variant}"
            if variant == "night":
                lines.append(
                    f'[data-theme="{tid}"] {{\n'
                    f"  --portal-scheme: dark;\n  --portal-mix: #000000;\n"
                    f"  --portal-bg: {bg};\n  --portal-bg-glow: rgba(64, 129, 122, 0.08);\n"
                    f"  --portal-surface: {surface};\n  --portal-ink: {ink};\n"
                    f"  --portal-muted: #9ab0ac;\n  --portal-line: #2a3836;\n"
                    f"  --portal-brand: {accent};\n  --portal-accent: {accent};\n"
                    f"  --portal-accent-soft: {soft};\n"
                    f"  --portal-cover: linear-gradient(160deg, {accent}, #1a3030);\n"
                    f"  --portal-shadow-color: rgba(0, 0, 0, 0.4);\n  color-scheme: dark;\n}}"
                )
            else:
                lines.append(
                    f'[data-theme="{tid}"] {{\n'
                    f"  --portal-scheme: light;\n  --portal-mix: #ffffff;\n"
                    f"  --portal-bg: {bg};\n  --portal-bg-glow: rgba(45, 138, 128, 0.1);\n"
                    f"  --portal-surface: {surface};\n  --portal-ink: {ink};\n"
                    f"  --portal-muted: #5a706c;\n  --portal-line: #d0e0dc;\n"
                    f"  --portal-brand: {accent};\n  --portal-accent: {accent};\n"
                    f"  --portal-accent-soft: {soft};\n"
                    f"  --portal-cover: linear-gradient(160deg, {accent}, {ink});\n"
                    f"  --portal-shadow-color: rgba(45, 138, 128, 0.1);\n  color-scheme: light;\n}}"
                )
        (themes_dir / f"{fl}.css").write_text("\n".join(lines) + "\n", encoding="utf-8")
        imports.append(f'@import "./themes/{fl}.css";')
        print("wrote theme", fl)

    themes_css = ROOT / "skeletons" / "baseline" / "frontend" / "src" / "styles" / "themes.css"
    text = themes_css.read_text(encoding="utf-8")
    if "credit.css" not in text:
        text = text.replace(
            '@import "./themes/expense.css";\n',
            '@import "./themes/expense.css";\n' + "\n".join(imports) + "\n",
            1,
        )
        themes_css.write_text(text, encoding="utf-8")
        print("patched themes.css")
    else:
        print("skip themes.css")

    sw = ROOT / "frontend" / "src" / "softThemeSwatches.js"
    st = sw.read_text(encoding="utf-8")
    if '"credit-teal"' in st:
        print("skip softThemeSwatches")
        return
    chunk_lines = []
    for _, _d, fl, *_ in STU_META:
        for variant, (bg, accent, soft, ink, surface) in THEME_PALETTES.items():
            tid = f"{fl}-{variant}"
            chunk_lines.append(
                f'  "{tid}": {{\n    "bg": "{bg}",\n    "accent": "{accent}",\n'
                f'    "soft": "{soft}",\n    "ink": "{ink}",\n    "surface": "{surface}"\n  }},'
            )
    # append before final `}` of SOFT_THEME_SWATCHES — find last theme block
    # insert before `\n}\n\nconst FALLBACK`
    marker = "\n}\n\nconst FALLBACK"
    if marker not in st:
        raise SystemExit("softTheme marker miss")
    chunk = "\n".join(chunk_lines).rstrip().rstrip(",")
    # need comma after previous last entry
    st = st.replace(marker, ",\n" + chunk + marker, 1)
    sw.write_text(st, encoding="utf-8")
    print("patched softThemeSwatches")


def merge_corpus() -> None:
    corpus_path = ROOT / "backend" / "tests" / "fixtures" / "domain_opening_corpus.json"
    extra_path = ROOT / "backend" / "tests" / "fixtures" / "stuwork_opening_corpus_extra.json"
    data = json.loads(corpus_path.read_text(encoding="utf-8"))
    extra = json.loads(extra_path.read_text(encoding="utf-8"))
    have = {s["domain"] for s in data["samples"]}
    added = 0
    for s in extra:
        if s["domain"] in have:
            continue
        data["samples"].append(s)
        have.add(s["domain"])
        added += 1
    corpus_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"corpus +{added}")


def write_registry_tests() -> None:
    import sys

    sys.path.insert(0, str(ROOT / "backend"))
    from app.bake.stuwork_meta import STUWORK_META

    case_lines = [
        f'    ("{m["pid"]}", "{m["phrase"]}", "{m["domain"]}", "{m["title"]}"),'
        for m in STUWORK_META
    ]
    reg = (
        '"""学工预设 P-12～P-16；P-20～P-22 骨架（泳道 D）。"""\n\n'
        "from __future__ import annotations\n\n"
        "STUWORK_CASES: list[tuple[str, str, str, str]] = [\n"
        + "\n".join(case_lines)
        + "\n]\n\n"
        "# P-20～P-22：待 C-08 床位占用 / C-10 通用签到\n"
        "STUWORK_BED_SKELETON: list[tuple[str, str, str, str]] = [\n"
        '    ("P-20", "新生宿舍床位在线选择分配", "DOM-BED", "C-08"),\n'
        '    ("P-21", "学生宿舍调宿退宿申请审批", "DOM-BED", "C-08"),\n'
        '    ("P-22", "宿舍查寝归寝签到缺勤记录", "DOM-CHECKIN", "C-10"),\n'
        "]\n"
    )
    (BACKEND / "stuwork_p.py").write_text(reg, encoding="utf-8")

    samples_note = ROOT / "data" / "samples" / "学工预设开题" / "00-床位查寝骨架-P20-P22.txt"
    samples_note.write_text(
        textwrap.dedent(
            """\
            床位 / 查寝骨架（泳道 D · P-20～P-22）
            ====================================

            状态：部分有 — 仅登记验收句与期望 DOM，**未**注册可 bake 域。
            阻塞：C-08 床位占用（P-20/P-21）；C-10 通用签到（P-22）。

            | ID   | 开题短句                   | 期望落点（规划） | 依赖 |
            |------|----------------------------|------------------|------|
            | P-20 | 新生宿舍床位在线选择分配   | DOM-BED 等       | C-08 |
            | P-21 | 学生宿舍调宿退宿申请审批   | DOM-BED 等       | C-08 |
            | P-22 | 宿舍查寝归寝签到缺勤记录   | DOM-CHECKIN 等  | C-10 |

            代码：`backend/app/bake/stuwork_p.py` → `STUWORK_BED_SKELETON`
            测试：`backend/tests/test_stuwork_p.py` → `test_bed_skeleton_not_registered`
            """
        ),
        encoding="utf-8",
    )

    test = textwrap.dedent(
        '''\
        """泳道 D：P-12～P-16 学工预设；P-20～P-22 骨架。"""

        from __future__ import annotations

        import unittest
        from pathlib import Path

        from app.bake.catalog import match_text
        from app.bake.domain_schema import build_domain_schema, validate_schema
        from app.bake.domains import DOMAIN_CAPABILITIES, DOMAINS
        from app.bake.schema.followup_presets import FOLLOWUP_PRESETS
        from app.bake.schema.templates import SCHEMA_BUILDERS
        from app.bake.stuwork_p import STUWORK_BED_SKELETON, STUWORK_CASES

        SAMPLES = Path(__file__).resolve().parents[2] / "data" / "samples" / "学工预设开题"


        class StuworkPTests(unittest.TestCase):
            def test_domains_registered(self) -> None:
                for sid, _p, domain, _t in STUWORK_CASES:
                    with self.subTest(id=sid):
                        self.assertIn(domain, DOMAINS)
                        self.assertIn(domain, DOMAIN_CAPABILITIES)
                        self.assertIn(domain, FOLLOWUP_PRESETS)
                        self.assertIn(domain, SCHEMA_BUILDERS)

            def test_p12_p16_hit(self) -> None:
                self.assertEqual(len(STUWORK_CASES), 5)
                for sid, phrase, want, title in STUWORK_CASES:
                    with self.subTest(id=sid):
                        text = f"基于 Spring Boot 的{title}的设计与实现。主要功能：{phrase}。"
                        got = match_text(text)
                        self.assertEqual(got.domain, want, f"hits={got.hits[:10]}")

            def test_neighbors(self) -> None:
                cases = [
                    ("第二课堂学分项目认定申请审批", "DOM-CREDIT", "DOM-ACTIVITY"),
                    ("劳动教育志愿时长登记认定审批", "DOM-LABOR", "DOM-ACTIVITY"),
                    ("学期末学生网上评教评分与评语", "DOM-EVAL", "DOM-GRADE"),
                    ("综合测评德育分加减分申报审批", "DOM-MORAL", "DOM-GRADE"),
                    ("创新学分竞赛获奖成果登记审批", "DOM-AWARD", "DOM-FUND"),
                ]
                for phrase, want, avoid in cases:
                    with self.subTest(phrase=phrase):
                        got = match_text(f"基于 Spring Boot 的{phrase}系统的设计与实现")
                        self.assertEqual(got.domain, want, f"hits={got.hits[:10]}")
                        self.assertNotEqual(got.domain, avoid)

            def test_samples_exist(self) -> None:
                for sid, _p, domain, title in STUWORK_CASES:
                    with self.subTest(id=sid):
                        path = SAMPLES / f"{sid}-{domain}-{title}.txt"
                        self.assertTrue(path.is_file(), path)

            def test_schema_builds(self) -> None:
                for sid, _p, domain, title in STUWORK_CASES:
                    with self.subTest(id=sid):
                        schema = build_domain_schema(title, domain)
                        ok, errs = validate_schema(schema)
                        self.assertTrue(ok, errs[:5])

            def test_eval_has_rating(self) -> None:
                schema = build_domain_schema("高校学生网上评教管理系统", "DOM-EVAL")
                ticket = (schema.get("entities") or {}).get("ticket") or {}
                self.assertTrue(ticket.get("allowRating") or ticket.get("allow_rating")
                                or (schema.get("labels") or {}).get("authEyebrow") == "网上评教")

            def test_bed_skeleton_not_registered(self) -> None:
                self.assertEqual(len(STUWORK_BED_SKELETON), 3)
                for sid, phrase, phantom, dep in STUWORK_BED_SKELETON:
                    with self.subTest(id=sid):
                        self.assertNotIn(phantom, DOMAINS)
                        got = match_text(f"基于 Spring Boot 的{phrase}系统的设计与实现")
                        self.assertNotEqual(got.domain, phantom, f"dep={dep}")


        if __name__ == "__main__":
            unittest.main()
        '''
    )
    (ROOT / "backend" / "tests" / "test_stuwork_p.py").write_text(test, encoding="utf-8")
    print("wrote registry + tests")


def main() -> None:
    import sys

    sys.path.insert(0, str(ROOT / "backend"))
    write_followup_module()
    merge_followup()
    wire_all()
    write_themes()
    merge_corpus()
    write_registry_tests()
    print("wire stuwork done")


if __name__ == "__main__":
    main()
