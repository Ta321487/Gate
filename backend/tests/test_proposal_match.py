"""proposal_match 规则层单元测试。"""

from __future__ import annotations

import unittest

from app.bake.domains import DOMAINS
from app.bake.gates.feature_keywords import feature_hints, gate_keyword_triggers
from app.services.proposal_match import classify_line_match, score_line_feature


class ProposalMatchTests(unittest.TestCase):
    def test_login_profile_line(self):
        features = [
            {"name": "登录", "status": "baseline"},
            {"name": "个人资料与头像", "status": "baseline"},
        ]
        kind, links = classify_line_match("用户注册、登录与个人资料维护", features)
        self.assertEqual(kind, "matched")
        self.assertGreaterEqual(len(links), 2)

    def test_notice_wording(self):
        score, conf, _ = score_line_feature("公告发布与查阅", "公告管理")
        self.assertGreater(score, 0)
        self.assertIn(conf, ("hint", "substring", "exact"))

    def test_checkin_dorm_lines(self):
        features = list((DOMAINS.get("DOM-CHECKIN") or {}).get("features") or [])
        lines = [
            "查阅查寝安排与窗口。",
            "对本寝室提交归寝登记或晚归登记；窗口内口令签到。",
            "管理侧审核并查看未签到缺勤。",
            "寝室与查寝场次维护。",
        ]
        for line in lines:
            kind, links = classify_line_match(line, features)
            self.assertNotEqual(kind, "unmatched", msg=f"{line} -> {links}")

    def test_generic_only_not_matched(self):
        features = [{"name": "用户管理", "status": "module"}]
        kind, _ = classify_line_match("系统信息管理", features)
        self.assertIn(kind, ("review", "unmatched"))

    def test_feature_hints_cover_gate_triggers(self):
        """文本层 hints 应覆盖门禁层对该项名的触发词。"""
        for name in ("报修申请", "图书借阅", "登录注册", "购物车下单"):
            hints = feature_hints(name)
            triggers = gate_keyword_triggers(name)
            self.assertTrue(triggers, msg=name)
            overlap = {t for t in triggers if normalize_trigger(t, hints)}
            self.assertTrue(
                overlap or any(t in name for t in triggers),
                msg=f"{name} hints={hints} triggers={triggers}",
            )


def normalize_trigger(token: str, hints: set[str]) -> bool:
    norm_token = token.replace(" ", "")
    return any(norm_token in h or h in norm_token for h in hints) or norm_token in "".join(hints)


if __name__ == "__main__":
    unittest.main()
