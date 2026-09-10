"""学生可见文案禁工厂说明书口吻（双通道/开题/bake/DOM-* 等）。"""

from __future__ import annotations

import unittest
from pathlib import Path

from app.bake.domain_schema import (
    FACTORY_UI_FORBIDDEN,
    attach_accept,
    factory_ui_polluted,
    find_factory_ui_hits,
    scrub_factory_ui_text,
    scrub_schema_student_copy,
)

_REPO = Path(__file__).resolve().parents[2]
_SKELETON_FE = _REPO / "skeletons" / "baseline" / "frontend" / "src"


def _walk_strings(obj, path: str = "") -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            out.extend(_walk_strings(v, f"{path}.{k}" if path else str(k)))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            out.extend(_walk_strings(v, f"{path}[{i}]"))
    elif isinstance(obj, str):
        out.append((path, obj))
    return out


class StudentFacingCopyTests(unittest.TestCase):
    def test_shop_marketplace_schema_has_no_factory_meta(self) -> None:
        spec = attach_accept(
            {
                "domain": "DOM-SHOP",
                "title": "多商家电商平台",
                "archetype": "ARCH-TRADE",
                "capabilities": [],
            },
            "多商家入驻与店铺管理；客服模块（与商家在线沟通）；留言反馈",
        )
        schema = scrub_schema_student_copy(spec.get("schema") or {})
        surfaces = {
            "labels": schema.get("labels"),
            "menus": schema.get("menus"),
            "auth": schema.get("auth"),
            "registerHint": schema.get("registerHint"),
            "homeCards": schema.get("homeCards"),
            "notice": schema.get("notice"),
            "seeds": schema.get("seeds"),
        }
        for path, text in _walk_strings(surfaces):
            for bad in FACTORY_UI_FORBIDDEN:
                self.assertNotIn(bad, text, msg=f"{path}: {text!r}")
            self.assertFalse(factory_ui_polluted(text), msg=f"{path}: {text!r}")
        self.assertEqual(find_factory_ui_hits(surfaces), [])

    def test_guestbook_lead_is_product_copy(self) -> None:
        from app.bake.schema.builders_slot import _shop_schema

        schema = _shop_schema("多商家电商平台", "商家入驻与店铺管理")
        lead = (schema.get("labels") or {}).get("guestbookPageLead") or ""
        self.assertTrue(lead)
        self.assertNotIn("商家端", lead)
        self.assertNotIn("双通道", lead)
        self.assertNotIn("分通道", lead)

    def test_scrub_strips_legacy_factory_leads(self) -> None:
        dirty = {
            "dmShopCs": True,
            "dmPeerMode": "merchant",
            "labels": {
                "guestbookPageLead": "买家向平台留言；商家走商家端「留言反馈」与平台沟通（双通道，非即时通讯）。",
                "dmPageLead": "与店铺客服一对一沟通（短轮询私信，非即时通讯）。",
                "demoPayHint": "在线支付完成本单（本系统内支付流程，不对接银行）。",
                "dmPageTitle": "客服",
                "eSignLead": "上传签章图完成签署；非 CA、非法大大等第三方电子签平台。",
            },
            "seeds": {
                "noticeBody": "提供留言反馈双轨沟通机制；支持模拟支付。",
            },
        }
        clean = scrub_schema_student_copy(dirty)
        self.assertNotIn("dmPeerMode", clean)
        labs = clean["labels"]
        # 脏句不拆分硬凑，整句回退到各键产品 fallback
        self.assertEqual(labs["guestbookPageLead"], "有问题可向平台留言，我们会尽快回复。")
        self.assertFalse(factory_ui_polluted(labs["dmPageLead"]))
        self.assertNotIn("非即时", labs["dmPageLead"])
        self.assertNotIn("短轮询", labs["dmPageLead"])
        self.assertNotIn("本系统内", labs["demoPayHint"])
        self.assertNotIn("非 CA", labs["eSignLead"])
        self.assertNotIn("双轨", clean["seeds"]["noticeBody"])
        self.assertNotIn("模拟支付", clean["seeds"]["noticeBody"])

    def test_scrub_full_dirty_guestbook_falls_back(self) -> None:
        dirty = {
            "labels": {
                "guestbookPageLead": "商家走商家端「留言反馈」与平台沟通（双通道，非即时通讯）。",
            }
        }
        clean = scrub_schema_student_copy(dirty)
        self.assertEqual(
            clean["labels"]["guestbookPageLead"],
            "有问题可向平台留言，我们会尽快回复。",
        )

    def test_scrub_keeps_clean_short_titles(self) -> None:
        self.assertEqual(scrub_factory_ui_text("客服", fallback="私信"), "客服")
        self.assertEqual(
            scrub_factory_ui_text(
                "与店铺客服一对一沟通（短轮询私信，非即时通讯）。",
                fallback="与其他用户一对一沟通。",
            ),
            "与店铺客服一对一沟通。",
        )

    def test_skeleton_vue_has_no_factory_meta(self) -> None:
        """基线前端硬编码也不准带说明书腔（scrub 扫不到骨架）。"""
        self.assertTrue(_SKELETON_FE.is_dir(), msg=str(_SKELETON_FE))
        offenders: list[str] = []
        for p in _SKELETON_FE.rglob("*.vue"):
            text = p.read_text(encoding="utf-8", errors="ignore")
            for bad in FACTORY_UI_FORBIDDEN:
                if bad in text:
                    if p.name == "Login.vue" and bad.startswith("开题"):
                        continue
                    offenders.append(f"{p.relative_to(_SKELETON_FE)}: {bad}")
                    break
        self.assertEqual(offenders, [], msg="\n".join(offenders[:20]))

    def test_refresh_polluted_vue_from_baseline(self) -> None:
        """旧工作区 Vue 脏、现网骨架干净 → 覆写，不必重 bake。"""
        import tempfile
        from unittest.mock import patch

        from app.bake.domain_schema import refresh_polluted_vue_from_baseline

        with tempfile.TemporaryDirectory() as td:
            ws = Path(td)
            dirty = ws / "frontend" / "src" / "views" / "ESignMine.vue"
            dirty.parent.mkdir(parents=True)
            dirty.write_text(
                '<p class="lead">上传签章图；非 CA、非法大大等第三方电子签平台。</p>\n',
                encoding="utf-8",
            )
            base = Path(td) / "sk_root" / "baseline" / "frontend" / "src" / "views"
            base.mkdir(parents=True)
            (base / "ESignMine.vue").write_text(
                '<p class="lead">{{ eSignLead }}</p>\n',
                encoding="utf-8",
            )
            with patch(
                "app.core.config.get_settings",
                return_value=type("S", (), {"skeletons_dir": Path(td) / "sk_root"})(),
            ):
                written = refresh_polluted_vue_from_baseline(ws)
            self.assertEqual(written, ["frontend/src/views/ESignMine.vue"])
            self.assertNotIn("非 CA", dirty.read_text(encoding="utf-8"))

    def test_refresh_polluted_vue_replaces_demo_wording(self) -> None:
        """工作区「演示密码」脏、骨架已净 → 清洗覆写，不必重 bake。"""
        import tempfile
        from unittest.mock import patch

        from app.bake.domain_schema import refresh_polluted_vue_from_baseline

        with tempfile.TemporaryDirectory() as td:
            ws = Path(td)
            dirty = ws / "frontend" / "src" / "views" / "user" / "MyOrders.vue"
            dirty.parent.mkdir(parents=True)
            dirty.write_text(
                '<el-input placeholder="演示密码，至少 4 位" />\n',
                encoding="utf-8",
            )
            base = Path(td) / "sk_root" / "baseline" / "frontend" / "src" / "views" / "user"
            base.mkdir(parents=True)
            (base / "MyOrders.vue").write_text(
                '<el-input placeholder="支付密码，任意不少于 4 位" />\n',
                encoding="utf-8",
            )
            with patch(
                "app.core.config.get_settings",
                return_value=type("S", (), {"skeletons_dir": Path(td) / "sk_root"})(),
            ):
                written = refresh_polluted_vue_from_baseline(ws)
            self.assertEqual(written, ["frontend/src/views/user/MyOrders.vue"])
            self.assertNotIn("演示密码", dirty.read_text(encoding="utf-8"))

    def test_scrub_demo_password_phrase(self) -> None:
        from app.bake.domain_schema import scrub_factory_ui_text

        self.assertEqual(
            scrub_factory_ui_text("演示密码，至少 4 位", fallback="支付密码"),
            "支付密码，至少 4 位。",
        )
    def test_scrub_project_student_copy_rewrites_disk(self) -> None:
        """出包后一键清洗：只编排 emit（内含 scrub），不另写清洗规则。"""
        import json
        import tempfile
        from types import SimpleNamespace
        from unittest.mock import patch

        from app.services.student_copy import scrub_project_student_copy

        dirty_lead = "买家向平台留言；商家走商家端「留言反馈」与平台沟通（双通道，非即时通讯）。"
        schema = {
            "version": 1,
            "title": "测试店",
            "capabilities": [],
            "labels": {
                "appName": "测试店",
                "guestbookPageLead": dirty_lead,
            },
            "menus": {"admin": [], "portal": []},
        }
        with tempfile.TemporaryDirectory() as td:
            ws = Path(td)
            (ws / "domain.schema.json").write_text(
                json.dumps(schema, ensure_ascii=False), encoding="utf-8"
            )
            proj = SimpleNamespace(
                spec={"title": "测试店", "domain": "DOM-GENERIC", "schema": schema},
                gates={},
                checklist=[],
                zip_path=str(ws / "out.zip"),
                zip_ready=True,
                workspace_path=str(ws),
                status="generated",
                delivery_mark="none",
            )

            def _fake_emit(workspace, spec):
                # 与真实 emit 一致：调用同源 scrub 再落盘
                cleaned = scrub_schema_student_copy(dict(spec.get("schema") or {}))
                (workspace / "domain.schema.json").write_text(
                    json.dumps(cleaned, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
                return ["domain.schema.json"]

            with (
                patch(
                    "app.services.student_copy.project_svc.workspace_or_reason",
                    return_value=(ws, None),
                ),
                patch(
                    "app.services.student_copy.emit_schema_to_workspace",
                    side_effect=_fake_emit,
                ),
                patch(
                    "app.services.student_copy.refresh_polluted_vue_from_baseline",
                    return_value=[],
                ),
                patch(
                    "app.services.student_copy.project_svc.sync_checklist_from_workspace",
                    side_effect=lambda p: setattr(
                        p,
                        "gates",
                        {
                            "p3copy": {
                                "ok": True,
                                "label": "学生可见文案无工厂腔",
                                "desc": "ok",
                                "detail": {"hits": []},
                            },
                            "overall": True,
                            "zip_allowed": True,
                        },
                    )
                    or True,
                ),
                patch(
                    "app.services.student_copy.project_svc.gates_allow_delivery",
                    return_value=True,
                ),
                patch(
                    "app.services.student_copy.project_svc.delivery_block_reason",
                    return_value=None,
                ),
                patch(
                    "app.bake.gates.evaluate.evaluate_domain_gates",
                    return_value={
                        "p3copy": {
                            "ok": True,
                            "label": "学生可见文案无工厂腔",
                            "desc": "ok",
                            "detail": {"hits": []},
                        },
                        "p3s": {"ok": True, "label": "语义", "desc": "ok", "detail": {}},
                        "overall": True,
                        "zip_allowed": True,
                    },
                ),
            ):
                out = scrub_project_student_copy(proj)

            disk = json.loads((ws / "domain.schema.json").read_text(encoding="utf-8"))
            self.assertNotIn("双通道", disk["labels"]["guestbookPageLead"])
            self.assertTrue(out["copy_ok"])
            self.assertFalse(proj.zip_ready)


if __name__ == "__main__":
    unittest.main()
