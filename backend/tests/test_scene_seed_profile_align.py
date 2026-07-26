"""场景种子：演示 profile_json 键须与资料页字段对齐。"""

from __future__ import annotations

import json
import re
import unittest

from app.bake.engine_sql import domain_sql
from app.bake.profile_fields import profile_fields_for


def _user_profile_json(sql: str) -> dict:
    m = re.search(
        r"\('(?:user|patient|buyer)'[^,]*,[^,]*,[^,]*,[^,]*,[^,]*,\s*'(\{.*?\})'",
        sql,
        re.S,
    )
    assert m, "missing portal user seed"
    return json.loads(m.group(1).replace("''", "'"))


def _profile_keys(domain: str, title: str, proposal: str = "") -> set[str]:
    return {
        str(f.get("key"))
        for f in profile_fields_for(domain, title=title, proposal_text=proposal)
        if isinstance(f, dict) and f.get("key")
    }


class SceneSeedProfileAlignTests(unittest.TestCase):
    def test_hospital_default_uses_patient_no(self) -> None:
        sql = domain_sql("DOM-HOSPITAL", "thesis_test", title="医院挂号系统")
        prof = _user_profile_json(sql)
        self.assertIn("patientNo", prof)
        self.assertNotIn("cardNo", prof)
        keys = _profile_keys("DOM-HOSPITAL", "医院挂号系统")
        self.assertTrue(set(prof) <= keys | {"realName", "email", "gender"})

    def test_it_default_uses_student_no(self) -> None:
        sql = domain_sql("DOM-IT", "thesis_test", title="校园网报修系统")
        prof = _user_profile_json(sql)
        self.assertIn("studentNo", prof)
        self.assertNotIn("campusNo", prof)

    def test_food_shop_commercial_no_student_no(self) -> None:
        food = _user_profile_json(
            domain_sql("DOM-FOOD", "thesis_test", title="餐饮点餐系统")
        )
        shop = _user_profile_json(
            domain_sql("DOM-SHOP", "thesis_test", title="在线商城系统")
        )
        self.assertNotIn("studentNo", food)
        self.assertIn("receiverName", food)
        self.assertIn("pickupType", food)
        self.assertNotIn("studentNo", shop)
        self.assertIn("receiverName", shop)
        self.assertIn("deliveryType", shop)

    def test_equip_student_uses_student_no(self) -> None:
        prof = _user_profile_json(
            domain_sql("DOM-EQUIP", "thesis_test", title="实验室器材借用")
        )
        self.assertEqual(prof.get("identityType"), "学生")
        self.assertIn("studentNo", prof)
        self.assertNotIn("employeeNo", prof)

    def test_crm_campus_seed_switches(self) -> None:
        body = "高校学生团队维护合作单位档案，师生可登记联系记录；校园创业孵化场景。"
        sql = domain_sql(
            "DOM-CRM",
            "thesis_test",
            title="校园创业孵化系统",
            proposal_text=body,
        )
        prof = _user_profile_json(sql)
        self.assertEqual(prof.get("identityType"), "学生")
        self.assertIn("studentNo", prof)
        self.assertNotIn("region", prof)
        self.assertIn("校友企业", sql)

    def test_asset_campus_seed_switches(self) -> None:
        body = "高校院系教职工物资领用与耗材申领。"
        sql = domain_sql(
            "DOM-ASSET",
            "thesis_test",
            title="高校物资领用系统",
            proposal_text=body,
        )
        prof = _user_profile_json(sql)
        self.assertEqual(prof.get("identityType"), "教职工")
        self.assertIn("employeeNo", prof)
        self.assertIn("教学设备", sql)

    def test_meeting_enterprise_seed_switches(self) -> None:
        body = "公司综合办会议室预约，员工按部门预约时段。"
        sql = domain_sql(
            "DOM-MEETING",
            "thesis_test",
            title="企业会议室预约系统",
            proposal_text=body,
        )
        prof = _user_profile_json(sql)
        self.assertEqual(prof.get("identityType"), "员工")
        self.assertIn("employeeNo", prof)
        self.assertIn("洽谈室", sql)

    def test_parking_commercial_required_fields(self) -> None:
        prof = _user_profile_json(
            domain_sql("DOM-PARKING", "thesis_test", title="商业停车场车位预约")
        )
        self.assertIn("vehicleType", prof)
        self.assertIn("ownerType", prof)
        self.assertNotIn("孙同学", json.dumps(prof, ensure_ascii=False))

    def test_parking_campus_seed_switches(self) -> None:
        sql = domain_sql(
            "DOM-PARKING",
            "thesis_test",
            title="校园车位预约管理系统",
            proposal_text="教职工与学生预约校内车位。",
        )
        prof = _user_profile_json(sql)
        self.assertEqual(prof.get("ownerType"), "教职工")
        self.assertIn("employeeNo", prof)
        keys = _profile_keys(
            "DOM-PARKING",
            "校园车位预约管理系统",
            "教职工与学生预约校内车位。",
        )
        self.assertTrue(set(prof) <= keys | {"realName", "email", "gender"})
        self.assertNotIn("星河科技", sql)

    def test_property_subadmin_is_dispatcher(self) -> None:
        sql = domain_sql("DOM-PROPERTY", "thesis_test", title="小区物业报修")
        self.assertIn("'物业调度'", sql)
        self.assertNotIn("'维修员'", sql.split("INSERT INTO sys_user")[1].split("INSERT IGNORE")[0])


if __name__ == "__main__":
    unittest.main()
