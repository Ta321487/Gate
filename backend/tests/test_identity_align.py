"""全域身份对齐硬闸。"""

from __future__ import annotations

import unittest

from app.bake.catalog import DOMAINS
from app.bake.domain_schema import build_domain_schema
from app.bake.engine_sql import domain_sql
from app.bake.identity_align import assert_identity_aligned, check_identity_alignment
from app.bake.proposal_packs import PACKS
from app.bake.sample_proposal import render_template

# 有双档的域：额外用对侧题名再闸一次
_BRANCH_CASES: list[tuple[str, str, str]] = [
    ("DOM-CRM", "校园创业孵化系统", "高校学生团队维护合作单位档案"),
    ("DOM-CRM", "中小企业客户管理系统", "销售跟进客户线索与合同"),
    ("DOM-IT", "校园网报修系统", "师生报修校园网"),
    ("DOM-IT", "企业内部IT报修系统", "员工报修办公电脑"),
    ("DOM-ATTEND", "高校学生请销假系统", "学生请假销假"),
    ("DOM-ATTEND", "企业员工请销假系统", "员工请假销假"),
    ("DOM-RECRUIT", "校园招聘管理系统", "学生投递简历"),
    ("DOM-RECRUIT", "企业社会招聘系统", "社会求职者投递"),
    ("DOM-FUND", "高校奖助学金系统", "学生申请奖助学金"),
    ("DOM-FUND", "企业员工福利补助系统", "员工申请福利补助"),
    ("DOM-MEETING", "高校会议室预约系统", "师生预约教室"),
    ("DOM-MEETING", "企业会议室预约系统", "员工按部门预约"),
    ("DOM-PARKING", "校园车位预约管理系统", "教职工预约校内车位"),
    ("DOM-PARKING", "商业停车场车位预约", "商场顾客预约车位"),
    ("DOM-FOOD", "高校食堂点餐系统", "食堂档口堂食"),
    ("DOM-FOOD", "小型餐厅点餐系统", "外卖配送"),
    ("DOM-SHOP", "校园二手闲置交易系统", "同学间二手教材"),
    ("DOM-SHOP", "在线商城系统", "零售商品下单"),
    ("DOM-ASSET", "高校物资领用系统", "教职工物资领用"),
    ("DOM-ASSET", "企业物资领用系统", "员工领用办公耗材"),
    ("DOM-MEDIA", "校园教学片点播系统", "宿舍放映教学片"),
    ("DOM-MEDIA", "在线影视点播系统", "会员点播影视"),
    ("DOM-EVENT", "社区健康监测系统", "社区网格员维护居民档案"),
    ("DOM-EVENT", "企业复工健康打卡系统", "员工每日健康打卡"),
    ("DOM-EVENT", "高校晨午检系统", "校医院晨午检登记"),
    ("DOM-PARCEL", "校园快递驿站系统", "学生取件"),
    ("DOM-PARCEL", "社区菜鸟驿站系统", "小区居民取件"),
    ("DOM-GRADE", "高校成绩管理系统", "学生查询成绩"),
    ("DOM-GRADE", "企业员工培训考核系统", "员工培训成绩"),
    ("DOM-INTERN", "高校实习周报管理系统", "学生提交周报"),
    ("DOM-INTERN", "企业带教实习周报系统", "员工带教与周报"),
    ("DOM-DATING", "婚恋交友管理系统", "会员牵线与沟通"),
    ("DOM-DATING", "校园联谊交友系统", "同学联谊匹配"),
]


class IdentityAlignTests(unittest.TestCase):
    def test_shell_forbids_campus_words_on_enterprise(self) -> None:
        title = "企业内部IT报修系统"
        body = "员工报修办公电脑"
        schema = build_domain_schema(title, "DOM-IT", proposal_text=body)
        sql = domain_sql("DOM-IT", "t", title=title, proposal_text=body)
        issues = check_identity_alignment(
            "DOM-IT",
            title=title,
            proposal_text=body,
            sql=sql,
            schema=schema,
        )
        self.assertEqual(issues, [])

    def test_shell_forbids_enterprise_words_on_campus(self) -> None:
        title = "高校食堂点餐系统"
        body = "食堂档口堂食"
        schema = build_domain_schema(title, "DOM-FOOD", proposal_text=body)
        sql = domain_sql("DOM-FOOD", "t", title=title, proposal_text=body)
        issues = check_identity_alignment(
            "DOM-FOOD",
            title=title,
            proposal_text=body,
            sql=sql,
            schema=schema,
        )
        self.assertEqual(issues, [])

        title = "高校学生请销假系统"
        body = "学生请假销假"
        sql = domain_sql("DOM-ATTEND", "t", title=title, proposal_text=body)
        issues = check_identity_alignment(
            "DOM-ATTEND", title=title, proposal_text=body, sql=sql
        )
        self.assertEqual(issues, [])

    def test_recruit_campus_seed_has_identity(self) -> None:
        title = "校园招聘管理系统"
        sql = domain_sql("DOM-RECRUIT", "t", title=title, proposal_text="")
        issues = check_identity_alignment(
            "DOM-RECRUIT", title=title, proposal_text="", sql=sql
        )
        self.assertEqual(issues, [])

    def test_every_pack_title_identity_aligned(self) -> None:
        for pack in PACKS:
            if pack.get("kind") == "cross":
                continue
            domain = str(pack["anchor_domain"])
            titles = list(pack.get("title_variants") or []) or [pack["title"]]
            for title in titles:
                with self.subTest(pack=pack["id"], title=title[-24:]):
                    text = render_template(
                        pack, digressions=[], l1_extras=[], title=title
                    )
                    schema = build_domain_schema(
                        title, domain, proposal_text=text
                    )
                    sql = domain_sql(
                        domain, "thesis_id", title=title, proposal_text=text
                    )
                    assert_identity_aligned(
                        domain,
                        title=title,
                        proposal_text=text,
                        sql=sql,
                        schema=schema,
                        profile_fields=schema.get("profileFields"),
                    )

    def test_branch_matrix_identity_aligned(self) -> None:
        for domain, title, body in _BRANCH_CASES:
            with self.subTest(domain=domain, title=title[-20:]):
                sql = domain_sql(domain, "t", title=title, proposal_text=body)
                assert_identity_aligned(
                    domain, title=title, proposal_text=body, sql=sql
                )

    def test_all_catalog_domains_default_title(self) -> None:
        for domain, meta in DOMAINS.items():
            if domain == "DOM-GENERIC":
                continue
            label = str((meta or {}).get("label") or domain)
            title = f"{label}管理系统"
            with self.subTest(domain=domain):
                sql = domain_sql(domain, "t", title=title, proposal_text="")
                assert_identity_aligned(
                    domain, title=title, proposal_text="", sql=sql
                )


if __name__ == "__main__":
    unittest.main()
