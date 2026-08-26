"""proposal_match 规则层单元测试。"""



from __future__ import annotations



import unittest



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



    def test_generic_only_not_matched(self):

        features = [{"name": "用户管理", "status": "module"}]

        kind, _ = classify_line_match("系统信息管理", features)

        self.assertIn(kind, ("review", "unmatched"))





if __name__ == "__main__":

    unittest.main()


