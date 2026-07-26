"""样例开题全包冒烟：每个 pack × title_variants 必须能 bake 且皮/种子不打架。

随机点「生成测试开题」踩雷贵；本文件把已知坑写成断言，改 pack/扫词/种子时先在这里炸。
"""

from __future__ import annotations

import json
import re
import unittest
from typing import Any

from app.bake.domain_schema import build_domain_schema
from app.bake.engine_sql import domain_sql
from app.bake.identity_align import assert_identity_aligned
from app.bake.menu_routes import assert_menu_routes_aligned
from app.bake.proposal_packs import PACKS
from app.bake.sample_proposal import render_template
from app.bake.scene_scan import (
    food_product_kind,
    hospital_product_kind,
    lost_product_kind,
    meeting_product_kind,
    product_kind_for,
    salon_product_kind,
    scene_for,
    shop_product_kind,
)


def _bake(domain: str, title: str, body: str = "") -> tuple[dict[str, Any], str]:
    schema = build_domain_schema(title, domain, proposal_text=body)
    sql = domain_sql(domain, "thesis_smoke", title=title, proposal_text=body)
    return schema, sql


_TRAILING_COMMA = re.compile(r",\s*\n\s*\)")
_USER_PROFILE = re.compile(
    r"\('(?:user|patient|buyer|reader|student)'[^,]*,[^,]*,[^,]*,[^,]*,[^,]*,\s*'(\{.*?\})'",
    re.S,
)

# pack 正文禁止再写「A / B」「A 或 B」双变体（题名优先也挡不住全是噪声时的误扫）
_DUAL_SLASH = re.compile(
    r"(会议室|琴房|自习室|校医院|宠物医院|美发|健身|失物|领养|中小企业|校园创业)"
    r"[^。]{0,8}(/|或)"
    r"[^。]{0,12}"
    r"(会议室|琴房|自习室|校医院|宠物医院|美发|健身|失物|领养|中小企业|校园创业)"
)


def _iter_pack_titles() -> list[tuple[dict[str, Any], str]]:
    out: list[tuple[dict[str, Any], str]] = []
    for pack in PACKS:
        if pack.get("kind") == "cross":
            continue
        titles = list(pack.get("title_variants") or []) or [pack["title"]]
        for title in titles:
            out.append((pack, title))
    return out


def _user_profile(sql: str) -> dict[str, Any]:
    m = _USER_PROFILE.search(sql)
    assert m, "missing portal user seed"
    return json.loads(m.group(1).replace("''", "'"))


def _archive_keys(schema: dict[str, Any]) -> set[str]:
    arch = (schema.get("entities") or {}).get("archive") or {}
    return {str(f.get("key")) for f in (arch.get("fields") or []) if f.get("key")}


def _archive_label(schema: dict[str, Any], key: str) -> str:
    arch = (schema.get("entities") or {}).get("archive") or {}
    for f in arch.get("fields") or []:
        if f.get("key") == key:
            return str(f.get("label") or "")
    return ""


def _staff_label(schema: dict[str, Any], post_id: str) -> str:
    for p in (schema.get("roles") or {}).get("staff_posts") or []:
        if isinstance(p, dict) and p.get("id") == post_id:
            return str(p.get("label") or "")
    return ""


class SamplePackBakeSmokeTests(unittest.TestCase):
    def test_every_pack_title_bakes_clean(self) -> None:
        cases = _iter_pack_titles()
        self.assertGreaterEqual(len(cases), 20)
        for pack, title in cases:
            domain = str(pack["anchor_domain"])
            with self.subTest(pack=pack["id"], title=title[-24:]):
                text = render_template(pack, digressions=[], l1_extras=[], title=title)
                schema = build_domain_schema(title, domain, proposal_text=text)
                sql = domain_sql(
                    domain, "thesis_smoke", title=title, proposal_text=text
                )
                self.assertFalse(
                    _TRAILING_COMMA.search(sql),
                    "schema.sql 末列拖尾逗号（near ')'）",
                )
                assert_identity_aligned(
                    domain,
                    title=title,
                    proposal_text=text,
                    sql=sql,
                    schema=schema,
                    profile_fields=schema.get("profileFields"),
                )
                assert_menu_routes_aligned(
                    schema,
                    domain=domain,
                    proposal_text=text,
                )
                self._assert_domain_invariants(domain, title, text, schema, sql)

    def test_pack_boilerplate_no_dual_variant_slash(self) -> None:
        """样例 pack 的 scene/problem 禁止「美发 / 健身」类双写，避免洗皮。"""
        for pack in PACKS:
            if pack.get("kind") == "cross":
                continue
            blob = "\n".join(
                str(pack.get(k) or "")
                for k in ("scene", "problem", "value", "focus")
            )
            with self.subTest(pack=pack["id"]):
                m = _DUAL_SLASH.search(blob)
                self.assertIsNone(
                    m,
                    f"pack 正文含双变体写法，请拆到 title_variants/overlays: {m.group(0) if m else ''}",
                )

    def _assert_domain_invariants(
        self,
        domain: str,
        title: str,
        text: str,
        schema: dict[str, Any],
        sql: str,
    ) -> None:
        brow = str((schema.get("labels") or {}).get("authEyebrow") or "")
        user = str(((schema.get("roles") or {}).get("user") or {}).get("label") or "")
        kind = product_kind_for(domain, title, text)
        scene = scene_for(domain, title, text)

        if domain == "DOM-SHOP":
            pk = shop_product_kind(title, text)
            keys = _archive_keys(schema)
            if pk == "retail":
                self.assertNotIn("conditionGrade", keys)
                self.assertNotIn("condition_grade", sql)
                self.assertNotIn("成色", sql)
                self.assertNotIn("校徽帆布袋", sql)
                self.assertEqual(brow, "在线商城")
            else:
                self.assertIn("conditionGrade", keys)
                self.assertIn("condition_grade", sql)
                self.assertEqual(brow, "校园商城")

        if domain == "DOM-FOOD":
            pk = food_product_kind(title, text)
            if pk == "restaurant":
                self.assertEqual(_archive_label(schema, "isbn"), "门店")
                self.assertEqual(_staff_label(schema, "counter"), "店员")
                self.assertNotIn("窗口A", sql)
                self.assertEqual(brow, "点餐外卖")
            else:
                self.assertEqual(_archive_label(schema, "isbn"), "窗口")
                self.assertIn(_staff_label(schema, "counter"), ("档口店员", "窗口服务员", "食堂窗口", "档口"))
                self.assertEqual(brow, "食堂点餐")
                self.assertIn("窗口", sql)

        if domain == "DOM-PARKING":
            if scene == "campus":
                self.assertNotIn("星河科技", sql)
                self.assertIn(_user_profile(sql).get("ownerType"), ("教职工", "学生", "访客"))
                self.assertEqual(brow, "校园车位")
            else:
                self.assertNotIn("图书馆东侧", sql)
                self.assertEqual(brow, "车位预约")

        if domain == "DOM-HOSPITAL":
            pk = hospital_product_kind(title, text)
            if pk == "pet":
                self.assertEqual(user, "宠主")
                self.assertIn("宠", brow)
                self.assertIn("豆豆", sql)
            elif pk == "vaccine":
                self.assertEqual(user, "接种人")
                self.assertIn("疫苗", brow)
                self.assertIn("HPV", sql)
                self.assertNotIn("口腔专科", sql)
                self.assertEqual(_staff_label(schema, "registrar"), "预约管理员")
            else:
                self.assertNotEqual(user, "宠主")

        if domain == "DOM-SALON":
            pk = salon_product_kind(title, text)
            if pk == "fitness":
                self.assertIn("健身", brow)
                self.assertIn("私教", sql)
                self.assertNotIn("基础剪发", sql)
            else:
                self.assertNotIn("健身", brow)
                self.assertIn("剪发", sql)

        if domain == "DOM-LOST":
            pk = lost_product_kind(title, text)
            if pk == "adopt":
                self.assertIn("领养", brow)
            else:
                self.assertNotIn("领养", brow)

        if domain == "DOM-MEETING":
            pk = meeting_product_kind(title, text)
            arch_label = str(
                ((schema.get("entities") or {}).get("archive") or {}).get("label") or ""
            )
            if pk == "study":
                self.assertNotEqual(arch_label, "琴房")
            if pk == "piano":
                self.assertEqual(arch_label, "琴房")

        if domain == "DOM-MEDIA" and scene == "commercial":
            self.assertNotIn("校园青春", sql)
            self.assertNotIn("宿舍日记", sql)
        if domain == "DOM-MUSIC" and scene == "commercial":
            self.assertNotIn("校园晚风", sql)
            self.assertNotIn("图书馆角落", sql)
        if domain == "DOM-BLOG" and scene == "commercial":
            self.assertNotIn("文学院", sql)
            self.assertNotIn("离开的校园", sql)

        # 题名已点名社会/企业主体时，不得仍落校园档（有双档的域）
        if scene == "campus" and any(
            k in title
            for k in ("商场", "餐厅", "企业", "公司", "鲜花销售", "商业停车")
        ) and domain in {
            "DOM-FOOD",
            "DOM-SHOP",
            "DOM-PARKING",
            "DOM-CRM",
            "DOM-IT",
            "DOM-MEETING",
        }:
            self.fail(f"题名偏社会/企业却 scene=campus (kind={kind})")

    def test_adversarial_body_cannot_wash_title(self) -> None:
        """正文对比句不得压过题名（主动挖坑，不靠点开题发现）。"""
        cases = [
            (
                "DOM-MEDIA",
                "在线影视点播系统",
                "也可参考校园教学片点播与宿舍放映。",
                "commercial",
                "影视点播",
            ),
            (
                "DOM-BLOG",
                "个人技术博客管理系统",
                "教研室院刊与学工资讯亦可参考。",
                "commercial",
                "个人博客",
            ),
            (
                "DOM-FOOD",
                "小型餐厅点餐系统",
                "食堂档口堂食模式可作对比。",
                "commercial",
                "点餐外卖",
            ),
            (
                "DOM-SHOP",
                "社区二手闲置交易系统",
                "校园二手教材也可参考。",
                "commercial",
                "在线商城",
            ),
            (
                "DOM-ATTEND",
                "企业员工请假管理系统",
                "学生请假销假流程可作对比。",
                "enterprise",
                None,
            ),
            (
                "DOM-PROPERTY",
                "写字楼物业报修系统",
                "校园物业报修亦可参考。",
                "community",
                "物业报修",
            ),
            (
                "DOM-IT",
                "企业内网故障报修系统",
                "校园网报修流程可作对比。",
                "enterprise",
                None,
            ),
            (
                "DOM-PARCEL",
                "小区快递代收点管理系统",
                "校园驿站取件也可参考。",
                "community",
                None,
            ),
            (
                "DOM-MEETING",
                "企业会议室预约系统",
                "琴房或自习室口头预约问题类似。",
                "enterprise",
                None,
            ),
        ]
        for domain, title, body, want_scene, want_brow in cases:
            with self.subTest(domain=domain, title=title):
                schema, sql = _bake(domain, title, body)
                self.assertEqual(scene_for(domain, title, body), want_scene)
                if want_brow:
                    self.assertEqual(schema["labels"].get("authEyebrow"), want_brow)
                self.assertFalse(_TRAILING_COMMA.search(sql))

    def test_meeting_campus_seed_and_overlays(self) -> None:
        from app.bake.sample_proposal import apply_title_variant_pack, render_template
        from app.bake.proposal_packs import PACKS

        pack = next(p for p in PACKS if p["id"] == "meeting")
        piano = next(t for t in pack["title_variants"] if "琴房" in t)
        overlay = apply_title_variant_pack(pack, piano)
        self.assertIn("琴房", overlay.get("scene", ""))
        text = render_template(pack, digressions=[], l1_extras=[], title=piano)
        self.assertIn("琴房", text)
        _, sql = _bake("DOM-MEETING", piano, text)
        self.assertIn("赵老师", sql)
        self.assertNotIn("赵工", sql)

        _, ent_sql = _bake(
            "DOM-MEETING",
            "企业会议室预约系统",
            "员工预约部门会议室。",
        )
        self.assertIn("赵工", ent_sql)
        self.assertNotIn("赵老师", ent_sql)

    def test_product_kind_seeds_match_shell(self) -> None:
        vax_title = "基于 Spring Boot 与 Vue 的 HPV 疫苗预约系统的设计与实现"
        schema, sql = _bake("DOM-HOSPITAL", vax_title, "接种人预约针次。")
        self.assertEqual(hospital_product_kind(vax_title, ""), "vaccine")
        self.assertEqual(schema["labels"].get("authEyebrow"), "疫苗预约")
        self.assertIn("HPV", sql)
        self.assertNotIn("口腔专科", sql)

        fit_title = "基于 Spring Boot 与 Vue 的健身房私教预约管理系统的设计与实现"
        schema, sql = _bake("DOM-SALON", fit_title, "会员预约私教课。")
        self.assertEqual(salon_product_kind(fit_title, ""), "fitness")
        self.assertEqual(schema["labels"].get("authEyebrow"), "健身预约")
        self.assertIn("私教", sql)
        self.assertNotIn("基础剪发", sql)


if __name__ == "__main__":
    unittest.main()
