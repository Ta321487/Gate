"""§0 X-AUTH 通识横切：列注入 / AppPolicy / labels 契约（XA-00～XA-02）。"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

from app.bake.domain_schema import attach_accept
from app.bake.domains import DOMAIN_CAPABILITIES
from app.bake.engine_sql import domain_sql
from app.bake.features.auth_crosscut import (
    AUTH_CROSSCUT_COLUMNS,
    AUTH_CROSSCUT_TABLES,
    apply_auth_crosscut_to_spec,
)
from app.bake.runtime_policy import FIELDS, render as render_app_policy

REPO = Path(__file__).resolve().parents[2]

_AUTH_CONSTANTS = (
    "AUTH_LOCK_MAX_ATTEMPTS",
    "AUTH_LOCK_MINUTES",
    "AUTH_PASSWORD_MAX_DAYS",
    "AUTH_REMEMBER_DAYS",
    "AUTH_PASSWORD_MIN_LENGTH",
    "AUTH_SESSION_IDLE_MINUTES",
    "AUTH_MAX_SESSIONS",
    "AUTH_REQUIRE_INVITE",
    "AUTH_REQUIRE_EMAIL_ACTIVATE",
)

_AUTH_LABEL_KEYS = (
    "passwordStrengthHint",
    "accountLockedHint",
    "mustChangePasswordHint",
    "forgotPasswordLink",
    "rememberLoginLabel",
    "trialLoginFillLabel",
    "sessionIdleHint",
    "securityQuestionLabel",
    "securityAnswerLabel",
    "phoneDupHint",
    "studentNoDupHint",
    "phoneFormatHint",
    "emailFormatHint",
    "captchaRefreshHint",
    "captchaFailHint",
    "inviteCodeLabel",
    "inviteCodeHint",
    "agreeTermsLabel",
    "mustActivateEmailHint",
    "activationCodeLabel",
    "changeContactHint",
    "realNameAckLabel",
    "remoteLoginHint",
    "cancelAccountLabel",
    "onlineSessionsMenu",
    "inviteCodesMenu",
)


def _spec(domain: str = "DOM-LIBRARY", title: str = "图书借阅管理系统") -> dict:
    return attach_accept(
        {
            "domain": domain,
            "title": title,
            "capabilities": list(DOMAIN_CAPABILITIES[domain]),
            "features": [],
            "archetype": "ARCH-FLOW",
        },
        "",
    )


class AuthCrosscutFeatureTests(unittest.TestCase):
    def test_sys_user_columns_injected_on_bake(self) -> None:
        sql = domain_sql("DOM-LIBRARY", "thesis_auth_x", title="图书借阅管理系统")
        m = re.search(
            r"CREATE TABLE IF NOT EXISTS\s+`?sys_user`?\s*\((.*?)\)\s*;",
            sql,
            flags=re.IGNORECASE | re.DOTALL,
        )
        self.assertIsNotNone(m, "sys_user DDL missing")
        body = m.group(1).lower()
        for col, _ddl in AUTH_CROSSCUT_COLUMNS:
            self.assertIn(col.lower(), body, f"missing column {col}")

    def test_xa02_tables_without_invite_seed_by_default(self) -> None:
        from app.bake.features.auth_crosscut import AUTH_CROSSCUT_TABLES_CORE

        sql = domain_sql("DOM-LIBRARY", "thesis_auth_x", title="图书借阅管理系统")
        low = sql.lower()
        for table in AUTH_CROSSCUT_TABLES_CORE:
            self.assertIn(f"create table if not exists {table}", low, table)
        self.assertNotIn("create table if not exists sys_invite_code", low)
        self.assertNotIn("campus2026", low)
        self.assertNotIn("invite2026", low)
        self.assertIn("email_activated=1", sql.replace(" ", "").lower())

    def test_invite_seed_when_opening_mentions_invite(self) -> None:
        sql = domain_sql(
            "DOM-LIBRARY",
            "thesis_auth_inv",
            title="图书借阅管理系统",
            proposal_text="本校学生须凭邀请码注册后方可借阅。",
        )
        low = sql.lower()
        self.assertIn("create table if not exists sys_invite_code", low)
        self.assertIn("invite2026", low)
        self.assertIn("welcome01", low)

    def test_must_change_seed_patch_present(self) -> None:
        sql = domain_sql("DOM-ATTEND", "thesis_auth_x", title="学生请假管理系统")
        self.assertIn("must_change_password=1", sql.replace(" ", "").lower())
        self.assertIn("username='user'", sql.lower())

    def test_labels_and_auth_policy_on_spec_without_invite(self) -> None:
        out = apply_auth_crosscut_to_spec(_spec(), "")
        labels = (out.get("schema") or {}).get("labels") or {}
        for key in _AUTH_LABEL_KEYS:
            if key in ("inviteCodeLabel", "inviteCodeHint", "inviteCodesMenu"):
                self.assertFalse(labels.get(key), f"invite label leaked {key}")
                continue
            self.assertTrue(labels.get(key), f"label {key}")
        policy = (out.get("schema") or {}).get("authPolicy") or {}
        self.assertEqual(policy.get("lockMaxAttempts"), 5)
        self.assertEqual(policy.get("passwordMinLength"), 6)
        self.assertEqual(policy.get("sessionIdleMinutes"), 30)
        self.assertEqual(policy.get("maxSessions"), 5)
        self.assertEqual(policy.get("requireInvite"), 0)
        self.assertEqual(policy.get("requireEmailActivate"), 1)
        admin = ((out.get("schema") or {}).get("menus") or {}).get("admin") or []
        keys = {m.get("key") for m in admin}
        self.assertIn("online_sessions", keys)
        self.assertNotIn("invite_codes", keys)

    def test_invite_menu_when_opening_mentions_invite(self) -> None:
        out = apply_auth_crosscut_to_spec(
            _spec(),
            "注册须填写邀请码，限本校师生使用。",
        )
        policy = (out.get("schema") or {}).get("authPolicy") or {}
        self.assertEqual(policy.get("requireInvite"), 1)
        admin = ((out.get("schema") or {}).get("menus") or {}).get("admin") or []
        keys = {m.get("key") for m in admin}
        self.assertIn("invite_codes", keys)
        labels = (out.get("schema") or {}).get("labels") or {}
        self.assertTrue(labels.get("inviteCodesMenu"))

    def test_agri_shop_opening_has_no_invite_menu(self) -> None:
        body = (
            "当前农产品电子商务发展迅速，建设农产品电商信息系统，"
            "将水果蔬菜货架、购物车下单、订单办理与发货集中管理。"
        )
        out = apply_auth_crosscut_to_spec(
            {
                "domain": "DOM-SHOP",
                "title": "超新农产品销售网站",
                "capabilities": list(DOMAIN_CAPABILITIES["DOM-SHOP"]),
                "schema": {"menus": {"admin": []}, "labels": {}},
            },
            body,
        )
        admin = ((out.get("schema") or {}).get("menus") or {}).get("admin") or []
        keys = {m.get("key") for m in admin}
        self.assertNotIn("invite_codes", keys)
        self.assertEqual(((out.get("schema") or {}).get("authPolicy") or {}).get("requireInvite"), 0)

    def test_student_no_dup_hint_follows_profile_fields(self) -> None:
        """商城无学号档案 → 不得校园「学号或工号」句；图书有学号 → 可用校园句。"""
        from app.bake.features.auth_crosscut import (
            _STUDENT_NO_DUP_CAMPUS,
            _STUDENT_NO_DUP_GENERIC,
        )

        shop = apply_auth_crosscut_to_spec(
            {
                "domain": "DOM-SHOP",
                "title": "方木健身用品电商平台",
                "capabilities": list(DOMAIN_CAPABILITIES["DOM-SHOP"]),
                "schema": {
                    "menus": {"admin": []},
                    "labels": {},
                    "profileFields": [
                        {"key": "receiverName", "label": "收货人"},
                        {"key": "receiveAddress", "label": "收货地址"},
                    ],
                },
            },
            "健身用品商城，购物车下单与订单发货。",
        )
        shop_hint = ((shop.get("schema") or {}).get("labels") or {}).get("studentNoDupHint")
        self.assertEqual(shop_hint, _STUDENT_NO_DUP_GENERIC)
        self.assertNotIn("学号", shop_hint)
        self.assertNotIn("工号", shop_hint)

        lib = apply_auth_crosscut_to_spec(
            {
                "domain": "DOM-LIBRARY",
                "title": "图书借阅管理系统",
                "capabilities": list(DOMAIN_CAPABILITIES["DOM-LIBRARY"]),
                "schema": {
                    "menus": {"admin": []},
                    "labels": {},
                    "profileFields": [
                        {"key": "studentNo", "label": "学号"},
                        {"key": "college", "label": "学院"},
                    ],
                },
            },
            "",
        )
        lib_hint = ((lib.get("schema") or {}).get("labels") or {}).get("studentNoDupHint")
        self.assertEqual(lib_hint, _STUDENT_NO_DUP_CAMPUS)

    def test_userstore_no_campus_dup_literal(self) -> None:
        """三骨架异常文案不得写死学号/工号（商城包会被交付质量摘要打红）。"""
        needle = "该学号或工号已被绑定"
        for rel in (
            "skeletons/baseline/backend/src/main/java/com/thesis/service/UserStore.java",
            "skeletons/overlays/persistence-mybatis/backend/src/main/java/com/thesis/service/UserStore.java",
            "skeletons/overlays/persistence-jpa/backend/src/main/java/com/thesis/service/UserStore.java",
        ):
            text = (REPO / rel).read_text(encoding="utf-8")
            self.assertNotIn(needle, text, rel)
            self.assertIn("该账号资料已被使用，请更换", text, rel)

    def test_app_policy_fields_and_skeletons(self) -> None:
        names = {f[1] for f in FIELDS}
        for c in _AUTH_CONSTANTS:
            self.assertIn(c, names, c)
        expected = render_app_policy({})
        for tag, tree in (
            ("baseline", "skeletons/baseline"),
            ("mybatis", "skeletons/overlays/persistence-mybatis"),
            ("jpa", "skeletons/overlays/persistence-jpa"),
        ):
            text = (
                REPO / tree / "backend/src/main/java/com/thesis/config/AppPolicy.java"
            ).read_text(encoding="utf-8")
            self.assertEqual(text, expected, f"{tag} AppPolicy drift")
            for c in _AUTH_CONSTANTS:
                self.assertIn(c, text, f"{tag} missing {c}")

    def test_no_thesis_auth_yml_binder(self) -> None:
        rel = "backend/src/main/java/com/thesis/config/DomainRuntimeBinder.java"
        for tag, tree in (
            ("baseline", "skeletons/baseline"),
            ("mybatis", "skeletons/overlays/persistence-mybatis"),
            ("jpa", "skeletons/overlays/persistence-jpa"),
        ):
            text = (REPO / tree / rel).read_text(encoding="utf-8")
            self.assertNotIn("thesis.auth-", text, tag)

    def test_error_code_account_locked(self) -> None:
        text = (
            REPO
            / "skeletons/baseline/backend/src/main/java/com/thesis/common/ErrorCode.java"
        ).read_text(encoding="utf-8")
        self.assertIn("ACCOUNT_LOCKED(40103)", text)

    def test_userstore_auth_hooks_present(self) -> None:
        """三套 UserStore 须具备锁定 / 强制改密 / 密保 / XA-02 写方法（源码门禁）。"""
        needles = (
            "recordFailedLogin",
            "clearLoginFailures",
            "lockRemainMinutes",
            "forceChangePassword",
            "resetPasswordBySecurity",
            "setSecurityQuestion",
            "mustChangePassword",
            "AppPolicy.AUTH_LOCK_MAX_ATTEMPTS",
            "issueActivationCode",
            "activateByCode",
            "changeContact",
            "assertPhoneUnique",
            "setRealNameAcked",
            "effectiveMustActivate",
        )
        for tag, tree in (
            ("baseline", "skeletons/baseline"),
            ("mybatis", "skeletons/overlays/persistence-mybatis"),
            ("jpa", "skeletons/overlays/persistence-jpa"),
        ):
            text = (
                REPO / tree / "backend/src/main/java/com/thesis/service/UserStore.java"
            ).read_text(encoding="utf-8")
            for n in needles:
                self.assertIn(n, text, f"{tag} missing {n}")

    def test_session_stores_and_filter_present(self) -> None:
        base = REPO / "skeletons/baseline/backend/src/main/java/com/thesis"
        for rel in (
            "service/AuthSessionStore.java",
            "service/LoginLogStore.java",
            "service/InviteCodeStore.java",
            "service/AccountCancelStore.java",
            "config/AuthSessionFilter.java",
            "controller/AuthSessionController.java",
        ):
            self.assertTrue((base / rel).is_file(), rel)

    def test_menu_paths_online_and_invite(self) -> None:
        from app.bake.menu_routes import ADMIN_MENU_PATHS, effective_paths

        self.assertEqual(ADMIN_MENU_PATHS.get("online_sessions"), "/admin/online-sessions")
        self.assertEqual(ADMIN_MENU_PATHS.get("invite_codes"), "/admin/invite-codes")
        paths = effective_paths(list(DOMAIN_CAPABILITIES["DOM-LIBRARY"]))
        self.assertIn("/admin/online-sessions", paths)
        self.assertIn("/admin/invite-codes", paths)
        js = (
            REPO / "skeletons/baseline/frontend/src/utils/menuRoutes.js"
        ).read_text(encoding="utf-8")
        self.assertIn("online_sessions", js)
        self.assertIn("invite_codes", js)

    def test_fe_reads_auth_labels(self) -> None:
        fe = REPO / "skeletons/baseline/frontend/src"
        blob = "\n".join(
            p.read_text(encoding="utf-8")
            for p in fe.rglob("*")
            if p.suffix in {".vue", ".js"} and p.is_file()
        )
        for key in _AUTH_LABEL_KEYS:
            self.assertIn(key, blob, f"FE must reference labels.{key}")

    def test_activate_page_reachable_before_login(self) -> None:
        """注册未登录就能停在激活页；返回登录须清掉未激活会话，避免被闸弹回。"""
        fe = REPO / "skeletons/baseline/frontend/src"
        router = (fe / "router/index.js").read_text(encoding="utf-8")
        public = router.split("const publicPaths", 1)[1].split("])", 1)[0]
        self.assertIn("'/activate'", public)
        activate = (fe / "views/ActivateAccount.vue").read_text(encoding="utf-8")
        self.assertIn("backToLogin", activate)
        self.assertIn("clearAuthStorage", activate)
        login = (fe / "views/Login.vue").read_text(encoding="utf-8")
        self.assertIn("!mustActivateEmail()", login)


if __name__ == "__main__":
    unittest.main()
