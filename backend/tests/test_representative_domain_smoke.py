# -*- coding: utf-8 -*-
"""代表域静态冒烟：不打 ZIP，只验 schema + SQL + 身份。

用途：怕全域出大问题时，先绿这一组再挑题真开预览。
真预览清单见各用例 docstring / REPRESENTATIVE_CASES。
"""

from __future__ import annotations

import unittest

from app.bake.domain_schema import build_domain_schema
from app.bake.engine_sql import domain_sql
from app.bake.identity_align import assert_identity_aligned
from app.bake.menu_routes import assert_menu_routes_aligned
from app.bake.scene_scan import scene_for

# (domain, title, body, expect_scene|None)
# 人工预览：上传同题名开题 → bake → 走登录→主路径→我的/待审
REPRESENTATIVE_CASES: list[tuple[str, str, str, str | None]] = [
    (
        "DOM-LIBRARY",
        "基于 Spring Boot 与 Vue 的高校图书借阅管理系统的设计与实现",
        "学生借阅图书，管理员审核与归还。",
        None,  # 图书域无 scene 分支，壳走 default
    ),
    (
        "DOM-DORM",
        "基于 Spring Boot 与 Vue 的高校宿舍报修管理系统的设计与实现",
        "学生提交宿舍报修，宿管受理完结。",
        None,
    ),
    (
        "DOM-IT",
        "基于 Spring Boot 与 Vue 的校园IT报修服务台系统的设计与实现",
        "师生提交网络报修与终端故障工单。",
        None,
    ),
    (
        "DOM-ACTIVITY",
        "基于 Spring Boot 与 Vue 的高校社团活动报名系统的设计与实现",
        "学生浏览活动并报名，管理员审核占名额。",
        None,
    ),
    (
        "DOM-COURSE",
        "基于 Spring Boot 与 Vue 的高校公选课在线选课管理系统的设计与实现",
        "学生选课申请，教务审核占名额并检测冲突。",
        None,
    ),
    (
        "DOM-HOSPITAL",
        "基于 Spring Boot 与 Vue 的医院门诊挂号预约系统的设计与实现",
        "患者预约号源时段，到院就诊办结。",
        None,
    ),
    (
        "DOM-SHOP",
        "基于 Spring Boot 与 Vue 的校园二手闲置交易系统的设计与实现",
        "同学浏览二手商品，加入购物车并提交订单。",
        None,
    ),
    (
        "DOM-EXPENSE",
        "基于 Spring Boot 与 Vue 的企业差旅经费报销管理系统的设计与实现",
        "公司员工提交报销单，财务审批完结。",
        "enterprise",
    ),
]


class RepresentativeDomainSmokeTests(unittest.TestCase):
    def test_representative_schema_sql_identity(self) -> None:
        for domain, title, body, want_scene in REPRESENTATIVE_CASES:
            with self.subTest(domain=domain):
                if want_scene:
                    self.assertEqual(scene_for(domain, title, body), want_scene)
                schema = build_domain_schema(title, domain, proposal_text=body)
                self.assertTrue(schema.get("entities") or schema.get("modules"))
                sql = domain_sql(domain, "rep_smoke", title=title, proposal_text=body)
                self.assertIn("CREATE TABLE", sql)
                self.assertIn("sys_user", sql)
                assert_identity_aligned(
                    domain,
                    title=title,
                    proposal_text=body,
                    sql=sql,
                    schema=schema,
                )
                assert_menu_routes_aligned(schema)

    def test_expense_approve_ends_no_dead_overdue(self) -> None:
        title = REPRESENTATIVE_CASES[-1][1]
        body = REPRESENTATIVE_CASES[-1][2]
        schema = build_domain_schema(title, "DOM-EXPENSE", proposal_text=body)
        ticket = (schema.get("entities") or {}).get("ticket") or {}
        self.assertTrue(ticket.get("approveEndsFlow"))
        self.assertNotIn("overdue", ticket.get("states") or {})


if __name__ == "__main__":
    unittest.main()
