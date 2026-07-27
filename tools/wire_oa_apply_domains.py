"""把 P-01～P-08 OA 申请域接到现网登记点（在 gen_oa_apply_domains.py 之后运行）。"""

from __future__ import annotations

import json
import re
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend" / "app" / "bake"

OA_META = [
    ("P-01", "DOM-SEAL", "seal", "seal_item", "seal_apply", "用章申请", "用章管理员", "com.campus.seal", "SealApplication", "seal-app"),
    ("P-02", "DOM-FLEET", "fleet", "fleet_vehicle", "fleet_apply", "用车申请", "调度员", "com.campus.fleet", "FleetApplication", "fleet-app"),
    ("P-03", "DOM-CERT", "cert", "cert_type", "cert_apply", "开具证明", "证明专员", "com.campus.cert", "CertApplication", "cert-app"),
    ("P-04", "DOM-PROMO", "promo", "promo_matter", "promo_apply", "宣传审批", "宣传员", "com.campus.promo", "PromoApplication", "promo-app"),
    ("P-05", "DOM-FITOUT", "fitout", "fitout_site", "fitout_apply", "装修备案", "备案员", "com.campus.fitout", "FitoutApplication", "fitout-app"),
    ("P-06", "DOM-ACAD", "acad", "acad_matter", "acad_apply", "学籍异动", "教务员", "com.campus.acad", "AcadApplication", "acad-app"),
    ("P-07", "DOM-TRIP", "trip", "trip_matter", "trip_apply", "出差加班", "考勤员", "com.campus.trip", "TripApplication", "trip-app"),
    ("P-08", "DOM-EXPENSE", "expense", "expense_project", "expense_apply", "经费报销", "报销审核员", "com.campus.expense", "ExpenseApplication", "expense-app"),
]

THEME_PALETTES = {
    "teal": ("#eef7f6", "#2d8a80", "#d6f0ec", "#12302c", "#ffffff"),
    "sand": ("#f7f3ec", "#a67c3d", "#f0e6d4", "#2a2418", "#fffdf9"),
    "slate": ("#f0f2f4", "#475569", "#e2e8f0", "#1e293b", "#ffffff"),
    "night": ("#101818", "#40817a", "#203028", "#e8f0ee", "#182020"),
}


def _patch_once(path: Path, old: str, new: str, *, label: str) -> None:
    text = path.read_text(encoding="utf-8")
    if new.strip() in text and old not in text:
        print(f"skip {label}: already wired")
        return
    if old not in text:
        raise SystemExit(f"patch miss {label}: {path}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")
    print(f"patched {label}")


def write_oa_followup_presets() -> None:
    """从 _oa_presets_generated 转成可 import 的 builder。"""
    src = (BACKEND / "schema" / "_oa_presets_generated.py").read_text(encoding="utf-8")
    # strip header comment and rename
    body = src.replace(
        "# AUTO — paste into FOLLOWUP_PRESETS\nOA_PRESET_BLOCKS = {\n",
        "",
    )
    if not body.rstrip().endswith("}"):
        raise SystemExit("unexpected oa presets file")
    # remove trailing }\n
    inner = body.rsplit("}", 1)[0]
    out = (
        '"""OA 申请域 FOLLOWUP_PRESETS（P-01～P-08）。由 tools/gen_oa_apply_domains.py 生成。"""\n\n'
        "from __future__ import annotations\n\n"
        "from typing import Any, Callable\n\n\n"
        "def build_oa_followup_presets(\n"
        "    _std_archive_fields: Callable[..., list[dict[str, Any]]],\n"
        ") -> dict[str, dict[str, Any]]:\n"
        "    return {\n"
        + inner
        + "    }\n"
    )
    path = BACKEND / "schema" / "oa_followup_presets.py"
    path.write_text(out, encoding="utf-8")
    print("wrote", path)


def merge_followup() -> None:
    path = BACKEND / "schema" / "followup_presets.py"
    text = path.read_text(encoding="utf-8")
    marker = "from app.bake.schema.oa_followup_presets import build_oa_followup_presets"
    if marker in text:
        print("skip followup merge")
        return
    # insert after FOLLOWUP_PRESETS closing `}`
    # Find the dict end before _attach_event_archive_log
    anchor = "\n\n\ndef _attach_event_archive_log"
    if anchor not in text:
        raise SystemExit("followup anchor miss")
    inject = (
        "\n\nfrom app.bake.schema.oa_followup_presets import build_oa_followup_presets\n\n"
        "FOLLOWUP_PRESETS.update(build_oa_followup_presets(_std_archive_fields))\n"
        + anchor
    )
    path.write_text(text.replace(anchor, inject, 1), encoding="utf-8")
    print("patched followup_presets merge")


def wire_catalog_init() -> None:
    path = BACKEND / "domains_catalog" / "__init__.py"
    _patch_once(
        path,
        "from app.bake.domains_catalog.fallback import DOMAINS as FALLBACK_DOMAINS\n",
        "from app.bake.domains_catalog.fallback import DOMAINS as FALLBACK_DOMAINS\n"
        "from app.bake.domains_catalog.oa import DOMAINS as OA_DOMAINS\n",
        label="catalog import",
    )
    _patch_once(
        path,
        "    **CONTENT_DOMAINS,\n    **FALLBACK_DOMAINS,\n}",
        "    **CONTENT_DOMAINS,\n    **OA_DOMAINS,\n    **FALLBACK_DOMAINS,\n}",
        label="catalog merge",
    )


def wire_domains_py() -> None:
    path = BACKEND / "domains.py"
    # DOMAIN_GROUPS: add after DOM-PARCEL in borrow group
    domains = ",\n            ".join(f'"{d}"' for _, d, *_ in OA_META)
    _patch_once(
        path,
        '            "DOM-PARCEL",\n        ),\n    ),\n    ("ticket", "报修/工单"',
        f'            "DOM-PARCEL",\n            {domains},\n        ),\n    ),\n    ("ticket", "报修/工单"',
        label="DOMAIN_GROUPS",
    )
    caps_block = "".join(
        f'    "{d}": ["archive", "ticket_flow", "content", "org_users"],\n'
        for _, d, *_ in OA_META
    )
    _patch_once(
        path,
        '    "DOM-PARCEL": ["archive", "ticket_flow", "quota", "content", "org_users"],\n    # B 报修/工单',
        '    "DOM-PARCEL": ["archive", "ticket_flow", "quota", "content", "org_users"],\n'
        + caps_block
        + "    # B 报修/工单",
        label="DOMAIN_CAPABILITIES",
    )


def wire_entities() -> None:
    path = BACKEND / "domain_entities.py"
    block = "".join(
        f'    "{d}": DomainEntity("{arch}", "{ticket}", "{arch}_id", "archive"),\n'
        for _, d, _fl, arch, ticket, *_ in OA_META
    )
    _patch_once(
        path,
        '    "DOM-PARCEL": DomainEntity("parcel", "parcel_claim", "parcel_id", "archive"),\n',
        '    "DOM-PARCEL": DomainEntity("parcel", "parcel_claim", "parcel_id", "archive"),\n' + block,
        label="DOMAIN_ENTITIES",
    )


def wire_templates() -> None:
    path = BACKEND / "schema" / "templates.py"
    text = path.read_text(encoding="utf-8")
    if "OA_APPLY_META" in text:
        print("skip templates SCHEMA_BUILDERS")
        return
    inject_import = (
        "from app.bake.oa_apply_meta import OA_APPLY_META\n"
        "from app.bake.schema.followup_presets import followup_builder\n"
    )
    if "from app.bake.oa_apply_meta" not in text:
        text = text.replace(
            "from __future__ import annotations\n\n",
            "from __future__ import annotations\n\n" + inject_import,
            1,
        )
    if "for _m in OA_APPLY_META" not in text:
        text = text.rstrip() + (
            "\n\nfor _m in OA_APPLY_META:\n"
            '    SCHEMA_BUILDERS[_m["domain"]] = followup_builder(_m["domain"])\n'
        )
    path.write_text(text, encoding="utf-8")
    print("patched templates SCHEMA_BUILDERS")


def wire_catalog_default_arch() -> None:
    path = BACKEND / "catalog.py"
    block = "".join(f'    "{d}": "ARCH-FLOW",\n' for _, d, *_ in OA_META)
    _patch_once(
        path,
        '    "DOM-COURSE": "ARCH-FLOW",\n',
        '    "DOM-COURSE": "ARCH-FLOW",\n' + block,
        label="_DOMAIN_DEFAULT_ARCH",
    )


def wire_skin() -> None:
    path = BACKEND / "domain_skin.py"
    flav = "".join(f'    "{d}": "{fl}",\n' for _, d, fl, *_ in OA_META)
    traits = "".join(f'    "{d}": {{"followUp": True}},\n' for _, d, *_ in OA_META)
    # auth queries from oa_apply_meta
    from app.bake.oa_apply_meta import OA_APPLY_META as meta  # type: ignore

    auth = "".join(
        f'    "{m["domain"]}": "{m["auth_q"]}",\n' for m in meta
    )
    _patch_once(
        path,
        '    "DOM-PARCEL": "parcel",\n',
        '    "DOM-PARCEL": "parcel",\n' + flav,
        label="flavor",
    )
    _patch_once(
        path,
        '    "DOM-PARCEL": {"pickupFlow": True},\n',
        '    "DOM-PARCEL": {"pickupFlow": True},\n' + traits,
        label="traits",
    )
    _patch_once(
        path,
        '    "DOM-PARCEL": "campus parcel pickup station courier lockers",\n',
        '    "DOM-PARCEL": "campus parcel pickup station courier lockers",\n' + auth,
        label="auth_q",
    )


def wire_java() -> None:
    path = BACKEND / "java_package.py"
    block = "".join(
        f'    "{d}": ("{pkg}", "{app}", "{art}"),\n'
        for _, d, _fl, _a, _t, _lab, _clerk, pkg, app, art in OA_META
    )
    _patch_once(
        path,
        '    "DOM-PARCEL": ("com.campus.parcel", "ParcelApplication", "parcel-app"),\n',
        '    "DOM-PARCEL": ("com.campus.parcel", "ParcelApplication", "parcel-app"),\n' + block,
        label="java_package",
    )


def wire_staff() -> None:
    path = BACKEND / "staff_posts.py"
    block = "".join(
        f'    "{d}": [_clerk("{fl}_clerk", "{clerk}", "ticket_ops")],\n'
        for _, d, fl, _a, _t, _lab, clerk, *_ in OA_META
    )
    _patch_once(
        path,
        '    "DOM-PARCEL": [_clerk("parcel_clerk", "驿站店员", "ticket_ops")],\n',
        '    "DOM-PARCEL": [_clerk("parcel_clerk", "驿站店员", "ticket_ops")],\n' + block,
        label="staff_posts",
    )
    # user labels
    ulines = "".join(
        f'    "{d}": ("申请人", "办理人"),\n' for _, d, *_ in OA_META
    )
    if '"DOM-SEAL"' not in path.read_text(encoding="utf-8"):
        text = path.read_text(encoding="utf-8")
        anchor = '    "DOM-ATTEND": ("考勤对象", "员工"),\n'
        if anchor in text:
            path.write_text(text.replace(anchor, anchor + ulines, 1), encoding="utf-8")
            print("patched staff user labels")


def wire_fragments_archive() -> None:
    path = BACKEND / "sql" / "fragments.py"
    block = "".join(
        f'    "{d}": ["contact_channel", "next_follow_at"],\n' for _, d, *_ in OA_META
    )
    _patch_once(
        path,
        '    "DOM-INTERN": ["contact_channel", "next_follow_at"],\n',
        '    "DOM-INTERN": ["contact_channel", "next_follow_at"],\n' + block,
        label="TICKET_DOMAIN_COLUMNS",
    )
    path2 = BACKEND / "archive_columns.py"
    ablock = "".join(
        f'    "{d}": (\n'
        f'        ("dept_name", "VARCHAR(100)"),\n'
        f'        ("note_hint", "VARCHAR(255)"),\n'
        f"    ),\n"
        for _, d, *_ in OA_META
    )
    _patch_once(
        path2,
        '    "DOM-PARCEL": (\n        ("station_name", "VARCHAR(100)"),\n        ("pickup_code", "VARCHAR(255)"),\n    ),\n',
        '    "DOM-PARCEL": (\n        ("station_name", "VARCHAR(100)"),\n        ("pickup_code", "VARCHAR(255)"),\n    ),\n'
        + ablock,
        label="ARCHIVE_EXTRA",
    )


def wire_ticket_rules() -> None:
    path = BACKEND / "ticket_rules.py"
    text = path.read_text(encoding="utf-8")
    if "DOM-SEAL" in text:
        print("skip ticket_rules")
        return
    block = "".join(f'    "{d}": {{"max_active": 5}},\n' for _, d, *_ in OA_META)
    _patch_once(
        path,
        '    "DOM-GRADE": {"max_active": 2},\n',
        '    "DOM-GRADE": {"max_active": 2},\n' + block,
        label="ticket_rules",
    )


def wire_profile() -> None:
    path = BACKEND / "profile_fields.py"
    text = path.read_text(encoding="utf-8")
    if "DOM-SEAL" in text:
        print("skip profile")
        return
    fields = textwrap.dedent(
        """\
            _pf("identityType", "身份", required=True, on_register=True, field_type="select",
                options=["教职工", "学生", "其他"]),
            _pf("employeeNo", "工号", required=True, on_register=True, max_length=32,
                required_when=_when("identityType", ["教职工"]),
                visible_when=_when("identityType", ["教职工"]),
                placeholder="请填写工号"),
            _pf("studentNo", "学号", required=True, on_register=True, max_length=32,
                required_when=_when("identityType", ["学生"]),
                visible_when=_when("identityType", ["学生"]),
                placeholder="请填写学号"),
            _pf("dept", "部门/院系", required=True, on_register=True, max_length=64),
    """
    )
    block = "".join(
        f'    "{d}": [\n{fields}    ],\n' for _, d, *_ in OA_META
    )
    anchor = '    "DOM-GENERIC": [\n'
    if anchor not in text:
        raise SystemExit("profile anchor miss")
    path.write_text(text.replace(anchor, block + anchor, 1), encoding="utf-8")
    print("patched profile_fields")


def write_themes() -> None:
    themes_dir = ROOT / "skeletons" / "baseline" / "frontend" / "src" / "styles" / "themes"
    imports = []
    for _, d, fl, *_ in OA_META:
        lines = [f"/* —— {d} {fl} —— */"]
        for variant, (bg, accent, soft, ink, surface) in THEME_PALETTES.items():
            tid = f"{fl}-{variant}"
            if variant == "night":
                lines.append(
                    f'[data-theme="{tid}"] {{\n'
                    f"  --portal-scheme: dark;\n"
                    f"  --portal-mix: #000000;\n"
                    f"  --portal-bg: {bg};\n"
                    f"  --portal-bg-glow: rgba(64, 129, 122, 0.08);\n"
                    f"  --portal-surface: {surface};\n"
                    f"  --portal-ink: {ink};\n"
                    f"  --portal-muted: #9ab0ac;\n"
                    f"  --portal-line: #2a3836;\n"
                    f"  --portal-brand: {accent};\n"
                    f"  --portal-accent: {accent};\n"
                    f"  --portal-accent-soft: {soft};\n"
                    f"  --portal-cover: linear-gradient(160deg, {accent}, #1a3030);\n"
                    f"  --portal-shadow-color: rgba(0, 0, 0, 0.4);\n"
                    f"  color-scheme: dark;\n"
                    f"}}"
                )
            else:
                lines.append(
                    f'[data-theme="{tid}"] {{\n'
                    f"  --portal-scheme: light;\n"
                    f"  --portal-mix: #ffffff;\n"
                    f"  --portal-bg: {bg};\n"
                    f"  --portal-bg-glow: rgba(45, 138, 128, 0.1);\n"
                    f"  --portal-surface: {surface};\n"
                    f"  --portal-ink: {ink};\n"
                    f"  --portal-muted: #5a706c;\n"
                    f"  --portal-line: #d0e0dc;\n"
                    f"  --portal-brand: {accent};\n"
                    f"  --portal-accent: {accent};\n"
                    f"  --portal-accent-soft: {soft};\n"
                    f"  --portal-cover: linear-gradient(160deg, {accent}, {ink});\n"
                    f"  --portal-shadow-color: rgba(45, 138, 128, 0.1);\n"
                    f"  color-scheme: light;\n"
                    f"}}"
                )
        (themes_dir / f"{fl}.css").write_text("\n".join(lines) + "\n", encoding="utf-8")
        imports.append(f'@import "./themes/{fl}.css";')
        print("wrote theme", fl)

    themes_css = ROOT / "skeletons" / "baseline" / "frontend" / "src" / "styles" / "themes.css"
    text = themes_css.read_text(encoding="utf-8")
    if "seal.css" in text:
        print("skip themes.css imports")
    else:
        block = "\n".join(imports) + "\n"
        text = text.replace(
            '@import "./themes/dating.css";\n',
            '@import "./themes/dating.css";\n' + block,
            1,
        )
        themes_css.write_text(text, encoding="utf-8")
        print("patched themes.css imports")

    # factory softThemeSwatches
    sw = ROOT / "frontend" / "src" / "softThemeSwatches.js"
    st = sw.read_text(encoding="utf-8")
    if '"seal-teal"' in st:
        print("skip softThemeSwatches")
        return
    chunk_lines = []
    for _, _d, fl, *_ in OA_META:
        for variant, (bg, accent, soft, ink, surface) in THEME_PALETTES.items():
            tid = f"{fl}-{variant}"
            chunk_lines.append(
                f'  "{tid}": {{\n'
                f'    "bg": "{bg}",\n'
                f'    "accent": "{accent}",\n'
                f'    "soft": "{soft}",\n'
                f'    "ink": "{ink}",\n'
                f'    "surface": "{surface}"\n'
                f"  }},"
            )
    chunk = "\n".join(chunk_lines) + "\n"
    # insert before closing of SOFT_THEME_SWATCHES
    st = st.replace(
        '  "shop-night": {\n'
        '    "bg": "#12141c",\n'
        '    "accent": "#f43f5e",\n'
        '    "soft": "#4c1d2a",\n'
        '    "ink": "#f1eef4",\n'
        '    "surface": "#1c2030"\n'
        "  }\n}",
        '  "shop-night": {\n'
        '    "bg": "#12141c",\n'
        '    "accent": "#f43f5e",\n'
        '    "soft": "#4c1d2a",\n'
        '    "ink": "#f1eef4",\n'
        '    "surface": "#1c2030"\n'
        "  },\n" + chunk.rstrip().rstrip(",") + "\n}",
        1,
    )
    sw.write_text(st, encoding="utf-8")
    print("patched softThemeSwatches")


def merge_corpus() -> None:
    corpus_path = ROOT / "backend" / "tests" / "fixtures" / "domain_opening_corpus.json"
    extra_path = ROOT / "backend" / "tests" / "fixtures" / "oa_opening_corpus_extra.json"
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
    corpus_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"corpus +{added} OA samples")


def write_registry_and_tests() -> None:
    cases = []
    for pid, d, _fl, _a, _t, label, *_ in OA_META:
        from app.bake.oa_apply_meta import OA_APPLY_META

        m = next(x for x in OA_APPLY_META if x["domain"] == d)
        cases.append(
            f'    ("{pid}", "{m["phrase"]}", "{d}", "{m["title"].replace("的设计与实现", "").rstrip("系统")}"),'
        )
    # Fix titles from meta
    case_lines = []
    for m in __import__("app.bake.oa_apply_meta", fromlist=["OA_APPLY_META"]).OA_APPLY_META:
        title = m["title"]
        if title.endswith("系统"):
            sample_title = title
        else:
            sample_title = title + "系统"
        # match sample filenames from gen script
        case_lines.append(
            f'    ("{m["pid"]}", "{m["phrase"]}", "{m["domain"]}", "{m["title"]}"),'
        )
    reg = (
        '"""OA 申请预设 P-01～P-08 验收表（泳道 C）。"""\n\n'
        "from __future__ import annotations\n\n"
        "OA_APPLY_CASES: list[tuple[str, str, str, str]] = [\n"
        + "\n".join(case_lines)
        + "\n]\n\n"
        "# P-09～P-11 互选：待 C-05 互选引擎，仅骨架（不标已齐）\n"
        "OA_MUTUAL_SKELETON: list[tuple[str, str, str]] = [\n"
        '    ("P-09", "研究生导师双向选择志愿与确认", "DOM-MUTUAL-TUTOR"),\n'
        '    ("P-10", "毕业论文选题双选志愿与确认", "DOM-MUTUAL-TOPIC"),\n'
        '    ("P-11", "竞赛组队学习搭子意向匹配", "DOM-MUTUAL-TEAM"),\n'
        "]\n"
    )
    (BACKEND / "oa_apply_p.py").write_text(reg, encoding="utf-8")
    print("wrote oa_apply_p.py")

    test = textwrap.dedent(
        '''\
        """泳道 C：P-01～P-08 具名申请域正命中；P-09～P-11 仅骨架。"""

        from __future__ import annotations

        import unittest
        from pathlib import Path

        from app.bake.catalog import match_text
        from app.bake.domain_schema import build_domain_schema, validate_schema
        from app.bake.domains import DOMAIN_CAPABILITIES, DOMAINS
        from app.bake.oa_apply_p import OA_APPLY_CASES, OA_MUTUAL_SKELETON
        from app.bake.schema.followup_presets import FOLLOWUP_PRESETS
        from app.bake.schema.templates import SCHEMA_BUILDERS

        SAMPLES = Path(__file__).resolve().parents[2] / "data" / "samples" / "申请预设开题"


        class OaApplyPTests(unittest.TestCase):
            def test_domains_registered(self) -> None:
                for sid, _phrase, domain, _title in OA_APPLY_CASES:
                    with self.subTest(id=sid):
                        self.assertIn(domain, DOMAINS)
                        self.assertIn(domain, DOMAIN_CAPABILITIES)
                        self.assertIn(domain, FOLLOWUP_PRESETS)
                        self.assertIn(domain, SCHEMA_BUILDERS)

            def test_all_p01_p08_hit_named_domain(self) -> None:
                self.assertEqual(len(OA_APPLY_CASES), 8)
                for sid, phrase, want, title in OA_APPLY_CASES:
                    with self.subTest(id=sid, title=title):
                        text = f"基于 Spring Boot 的{title}的设计与实现。主要功能：{phrase}。"
                        got = match_text(text)
                        self.assertEqual(got.domain, want, f"hits={got.hits[:10]}")

            def test_neighbors_do_not_steal(self) -> None:
                cases = [
                    ("学校行政印章使用申请审批", "DOM-SEAL", "DOM-FUND"),
                    ("公务用车申请审批管理", "DOM-FLEET", "DOM-PARKING"),
                    ("在读成绩单在职证明开具申请", "DOM-CERT", "DOM-GRADE"),
                    ("横幅海报户外宣传方案审批", "DOM-PROMO", "DOM-ACTIVITY"),
                    ("装修进场施工备案申请审批", "DOM-FITOUT", "DOM-PROPERTY"),
                    ("学籍异动转专业缓考申请审批", "DOM-ACAD", "DOM-GRADE"),
                    ("出差加班申请审批与销结", "DOM-TRIP", "DOM-ATTEND"),
                    ("经费差旅报销单填写与审批", "DOM-EXPENSE", "DOM-FUND"),
                ]
                for phrase, want, avoid in cases:
                    with self.subTest(phrase=phrase):
                        got = match_text(f"基于 Spring Boot 的{phrase}系统的设计与实现")
                        self.assertEqual(got.domain, want, f"hits={got.hits[:10]}")
                        self.assertNotEqual(got.domain, avoid)

            def test_sample_files_exist(self) -> None:
                self.assertTrue(SAMPLES.is_dir(), SAMPLES)
                for sid, _phrase, domain, title in OA_APPLY_CASES:
                    with self.subTest(id=sid):
                        path = SAMPLES / f"{sid}-{domain}-{title}.txt"
                        self.assertTrue(path.is_file(), path)

            def test_schema_builds(self) -> None:
                for sid, _phrase, domain, title in OA_APPLY_CASES:
                    with self.subTest(id=sid):
                        schema = build_domain_schema(title, domain)
                        ok, errs = validate_schema(schema)
                        self.assertTrue(ok, errs[:5])
                        labels = schema.get("labels") or {}
                        self.assertTrue(labels.get("authEyebrow"), labels)

            def test_mutual_skeleton_not_registered(self) -> None:
                """P-09～P-11 待 C-05：只留骨架 ID，禁止假注册。"""
                self.assertEqual(len(OA_MUTUAL_SKELETON), 3)
                for sid, phrase, phantom in OA_MUTUAL_SKELETON:
                    with self.subTest(id=sid):
                        self.assertNotIn(phantom, DOMAINS)
                        got = match_text(f"基于 Spring Boot 的{phrase}系统的设计与实现")
                        # 未落地前可落近邻，但不得假装已有互选 DOM
                        self.assertNotEqual(got.domain, phantom)


        if __name__ == "__main__":
            unittest.main()
        '''
    )
    (ROOT / "backend" / "tests" / "test_oa_apply_p.py").write_text(test, encoding="utf-8")
    print("wrote test_oa_apply_p.py")


def main() -> None:
    import sys

    sys.path.insert(0, str(ROOT / "backend"))
    write_oa_followup_presets()
    merge_followup()
    wire_catalog_init()
    wire_domains_py()
    wire_entities()
    wire_templates()
    wire_catalog_default_arch()
    wire_skin()
    wire_java()
    wire_staff()
    wire_fragments_archive()
    wire_ticket_rules()
    wire_profile()
    write_themes()
    merge_corpus()
    write_registry_and_tests()
    print("wire done")


if __name__ == "__main__":
    main()
