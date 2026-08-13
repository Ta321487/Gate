"""开题场景单一真源：壳与资料页必须同判定。"""

from __future__ import annotations

import unittest

from app.bake.domain_schema import build_domain_schema, ensure_spec_schema
from app.bake.engine_sql import domain_sql
from app.bake.scene_scan import event_product_kind, product_kind_for, scene_for
from app.bake.schema.templates import SCHEMA_BUILDERS


class SceneScanContractTests(unittest.TestCase):
    def test_crm_sales_beats_campus_background(self) -> None:
        scene = scene_for(
            "DOM-CRM",
            "中小企业客户跟进管理系统",
            "学院创业孵化；销售人员维护客户并提交跟进。",
        )
        self.assertEqual(scene, "enterprise")
        schema = build_domain_schema(
            "中小企业客户跟进管理系统",
            "DOM-CRM",
            proposal_text="学院创业孵化；销售人员维护客户并提交跟进。",
        )
        ident = next(f for f in schema["profileFields"] if f["key"] == "identityType")
        self.assertEqual(ident["options"], ["销售", "运营", "其他"])
        self.assertNotIn("studentNo", {f["key"] for f in schema["profileFields"]})

    def test_event_elderly_institution_not_community_grid(self) -> None:
        """养老机构/照护员开题不得套社区网格壳，档案与种子跟机构档。"""
        title = "养老机构健康监测照护管理系统"
        body = "养老机构需要照护员对老人健康打卡与异常上报。"
        self.assertEqual(scene_for("DOM-EVENT", title, body), "institution")
        schema = build_domain_schema(title, "DOM-EVENT", proposal_text=body)
        self.assertEqual(schema["roles"]["subadmin"]["label"], "照护员")
        self.assertNotEqual(schema["roles"]["subadmin"]["label"], "网格员")
        self.assertEqual(schema["labels"].get("authEyebrow"), "机构照护")
        self.assertNotEqual(schema["labels"].get("authEyebrow"), "社区公卫")
        archive = schema["entities"]["archive"]
        self.assertEqual(archive.get("label"), "老人")
        author = next(f for f in archive["fields"] if f["key"] == "author")
        # attach_staff_posts 后与子管同名（照护员）
        self.assertEqual(author["label"], "照护员")
        ident = next(f for f in schema["profileFields"] if f["key"] == "identityType")
        self.assertEqual(ident["options"], ["照护员", "家属", "访客"])
        self.assertNotIn("studentNo", {f["key"] for f in schema["profileFields"]})

        from app.bake.engine_sql import domain_sql

        sql = domain_sql("DOM-EVENT", "thesis_test", title=title, proposal_text=body)
        self.assertIn("王德贵", sql)
        self.assertIn("照护员张敏", sql)
        self.assertNotIn("南门聚集性发热", sql)
        self.assertNotIn("食堂晨检", sql)
        self.assertNotIn("网格员甲", sql)

        # 社区网格仍走 community
        self.assertEqual(
            scene_for("DOM-EVENT", "社区健康监测", "社区网格员维护居民档案。"),
            "community",
        )

    def test_event_enterprise_fugong_not_community(self) -> None:
        title = "企业员工健康监测复工管理系统"
        body = "企业需要组织员工健康打卡与复工评估。"
        self.assertEqual(scene_for("DOM-EVENT", title, body), "enterprise")
        schema = build_domain_schema(title, "DOM-EVENT", proposal_text=body)
        self.assertEqual(schema["labels"].get("authEyebrow"), "企业复工")
        self.assertEqual(schema["entities"]["archive"].get("label"), "员工")
        self.assertNotIn("studentNo", {f["key"] for f in schema["profileFields"]})
        from app.bake.engine_sql import domain_sql

        sql = domain_sql("DOM-EVENT", "thesis_test", title=title, proposal_text=body)
        self.assertIn("生产一部", sql)
        self.assertNotIn("南门聚集性发热", sql)
        self.assertNotIn("阳光小区", sql)

    def test_event_default_clinic_not_campus_seed(self) -> None:
        title = "基层慢性病随访健康管理系统"
        body = "基层医疗卫生机构对高血压糖尿病患者建档随访。"
        self.assertEqual(scene_for("DOM-EVENT", title, body), "default")
        schema = build_domain_schema(title, "DOM-EVENT", proposal_text=body)
        self.assertEqual(schema["labels"].get("authEyebrow"), "健康随访")
        self.assertNotIn("studentNo", {f["key"] for f in schema["profileFields"]})
        ident = next(f for f in schema["profileFields"] if f["key"] == "identityType")
        self.assertIn("随访对象", ident["options"])
        from app.bake.engine_sql import domain_sql

        sql = domain_sql("DOM-EVENT", "thesis_test", title=title, proposal_text=body)
        self.assertIn("高血压", sql)
        self.assertNotIn("南门聚集性发热", sql)
        self.assertNotIn("食堂晨检", sql)

    def test_event_campus_and_community_archive_columns(self) -> None:
        campus = build_domain_schema(
            "校园晨午检", "DOM-EVENT", proposal_text="因病缺课上报。"
        )
        self.assertEqual(campus["entities"]["archive"].get("label"), "学生")
        community = build_domain_schema(
            "社区健康监测",
            "DOM-EVENT",
            proposal_text="社区网格员维护居民档案。",
        )
        self.assertEqual(community["entities"]["archive"].get("label"), "对象")
        # 一线填报=门户网格员；值班员确认；责任列跟网格员而非子管
        self.assertEqual(community["roles"]["user"]["label"], "网格员")
        self.assertEqual(community["roles"]["subadmin"]["label"], "值班员")
        author = next(
            f for f in community["entities"]["archive"]["fields"] if f["key"] == "author"
        )
        self.assertEqual(author["label"], "网格员")
        from app.bake.engine_sql import domain_sql

        sql = domain_sql(
            "DOM-EVENT",
            "thesis_test",
            title="社区健康监测",
            proposal_text="社区网格员维护居民档案。",
        )
        self.assertIn("网格员甲", sql)
        self.assertIn("('subadmin', 'sub123', 'admin', '值班员'", sql)
        self.assertNotIn("'居民甲'", sql)

    def test_attend_enterprise_archive_columns(self) -> None:
        schema = build_domain_schema(
            "企业员工考勤请假管理系统", "DOM-ATTEND", proposal_text=""
        )
        arch = schema["entities"]["archive"]
        self.assertEqual(arch.get("label"), "假种")
        self.assertEqual(arch.get("key"), "leave_type")
        isbn = next(f for f in arch["fields"] if f["key"] == "isbn")
        self.assertEqual(isbn["label"], "申请须知备注")
        self.assertNotIn("学号", isbn["label"])
        self.assertNotIn("工号", isbn["label"])
        title = next(f for f in arch["fields"] if f["key"] == "title")
        self.assertEqual(title["label"], "假种名称")

    def test_shell_and_profile_same_scene_asset_attend_event(self) -> None:
        cases = [
            (
                "DOM-ASSET",
                "物资领用系统",
                "企业仓储部门耗材申领出库。",
                "enterprise",
                "物资领用",
            ),
            (
                "DOM-ASSET",
                "高校固定资产申领",
                "学院行政部门物资申领。",
                "campus",
                "高校物资",
            ),
            (
                "DOM-ATTEND",
                "学生请假销假管理系统",
                "",
                "campus",
                "学生请假",
            ),
            (
                "DOM-ATTEND",
                "企业员工考勤请假管理系统",
                "",
                "enterprise",
                "人事公告",
            ),
            (
                "DOM-EVENT",
                "社区健康监测",
                "社区网格员维护居民档案。",
                "community",
                "社区公卫",
            ),
            (
                "DOM-EVENT",
                "校园晨午检",
                "因病缺课上报。",
                "campus",
                "校园晨午检",
            ),
        ]
        for domain, title, body, want_scene, eyebrow_or_notice in cases:
            with self.subTest(domain=domain, title=title):
                self.assertEqual(scene_for(domain, title, body), want_scene)
                schema = build_domain_schema(title, domain, proposal_text=body)
                labels = schema.get("labels") or {}
                blob = " ".join(
                    [
                        labels.get("authEyebrow") or "",
                        labels.get("noticePageTitle") or "",
                        (schema.get("roles") or {}).get("admin", {}).get("label") or "",
                    ]
                )
                self.assertIn(eyebrow_or_notice, blob)

    def test_parcel_community_no_campus_profile(self) -> None:
        title, body = "快递代收系统", "小区菜鸟驿站取件核销。"
        self.assertEqual(scene_for("DOM-PARCEL", title, body), "community")
        schema = build_domain_schema(title, "DOM-PARCEL", proposal_text=body)
        self.assertEqual(schema["labels"]["authEyebrow"], "快递代收")
        self.assertNotIn("campusNo", {f["key"] for f in schema["profileFields"]})

    def test_builders_accept_proposal_kw(self) -> None:
        """SCENE_COPY 域 builder 必须吃 proposal_text，避免只扫题名。"""
        from app.bake.schema.shells import _SCENE_COPY_DOMAINS

        for dom in sorted(_SCENE_COPY_DOMAINS):
            with self.subTest(dom=dom):
                fn = SCHEMA_BUILDERS[dom]
                schema = fn("测试课题", proposal_text="占位开题正文")
                self.assertTrue(schema.get("labels") or schema.get("roles"))

    def test_title_beats_pack_boilerplate_scene_for(self) -> None:
        """样例开题 scene/problem 双写不得压过题名分支。"""
        self.assertEqual(
            scene_for(
                "DOM-CRM",
                "校园创业团队客户跟进管理系统",
                "中小企业或校园创业团队在客户建档与跟进上若仅靠表格。",
            ),
            "campus",
        )
        self.assertEqual(
            scene_for(
                "DOM-EVENT",
                "社区公共卫生事件应急上报系统",
                "社区或校园在疫情排查；晨午检与因病缺课。",
            ),
            "community",
        )
        self.assertEqual(
            scene_for(
                "DOM-HOSPITAL",
                "HPV 疫苗预约系统",
                "校医院 / 宠物医院挂号；宠主为爱宠挂号。",
            ),
            "default",
        )
        self.assertEqual(
            scene_for(
                "DOM-LOST",
                "校园失物招领管理系统",
                "校园失物招领 / 宠物领养；待领养档案。",
            ),
            "campus",
        )
        self.assertEqual(
            scene_for(
                "DOM-MEETING",
                "企业会议室预约系统",
                "会议室、琴房或自习室若靠口头预约。",
            ),
            "enterprise",
        )

    def test_scene_branch_domains_wired_in_scene_for(self) -> None:
        """SCENE_COPY 域不得一律 default；壳/资料页须能按开题分档。"""
        from app.bake.schema.shells import _SCENE_COPY_DOMAINS

        cases = [
            ("DOM-FOOD", "校园食堂点餐系统", "食堂档口堂食外卖", "campus"),
            ("DOM-SHOP", "校园二手交易平台", "校内闲置物品流转", "campus"),
            ("DOM-HOSPITAL", "宠物医院挂号预约系统", "宠主为爱宠挂号", "adopt"),
            ("DOM-SALON", "美发门店预约系统", "发型师分时预约", "commercial"),
            ("DOM-CRM", "中小企业客户跟进", "销售维护客户", "enterprise"),
            ("DOM-IT", "企业内网故障报修", "员工提交终端故障", "enterprise"),
            ("DOM-LOST", "宠物领养管理系统", "待领养档案与申请", "adopt"),
            ("DOM-PARCEL", "小区快递代收", "菜鸟驿站取件", "community"),
            ("DOM-RECRUIT", "企业社会招聘系统", "HR 社招投递", "enterprise"),
            ("DOM-DATING", "社区相亲交友平台", "红娘牵线审核", "community"),
            ("DOM-ATTEND", "学生请假销假", "", "campus"),
            ("DOM-MEETING", "企业会议室预约", "部门会议室占坑", "enterprise"),
            ("DOM-PARKING", "商场车位预约", "商场地下车场", "commercial"),
            ("DOM-ASSET", "企业仓储耗材申领", "仓储出库", "enterprise"),
            ("DOM-EVENT", "养老机构健康监测", "照护员打卡上报", "institution"),
            ("DOM-FUND", "企业员工福利补助申请", "员工福利与困难补助", "enterprise"),
            ("DOM-GRADE", "企业内训成绩管理系统", "培训成绩与岗位认证", "enterprise"),
            ("DOM-INTERN", "企业带教实习生周报", "带教导师审阅周报", "enterprise"),
            ("DOM-LABSAFE", "厂区实验室安环准入", "安环准入与 EHS 培训", "enterprise"),
            ("DOM-PROPERTY", "校园物业报修系统", "学生公寓物业报修", "campus"),
            ("DOM-MEDIA", "高校校园媒资点播", "校园教学片点播", "campus"),
            ("DOM-MUSIC", "高校校园曲库试听", "校园原创曲库", "campus"),
            ("DOM-BLOG", "高校学工资讯博客", "学工与院刊资讯", "campus"),
            ("DOM-FORUM", "小区兴趣社区论坛", "邻里互助发帖回帖", "community"),
        ]
        covered = {c[0] for c in cases}
        # EXAM / EQUIP / ACTIVITY：SCENE_COPY 仅为吃 proposal_text 换产品皮，scene 仍 default
        product_copy_only = frozenset({"DOM-EXAM", "DOM-EQUIP", "DOM-ACTIVITY"})
        self.assertEqual(_SCENE_COPY_DOMAINS - product_copy_only, covered)
        for domain, title, body, want in cases:
            with self.subTest(domain=domain):
                self.assertEqual(scene_for(domain, title, body), want)

    def test_followup_audit_scene_hints(self) -> None:
        """跟进簇审计挡点：S-13 企业周报；高校课堂请假题落 campus。"""
        self.assertEqual(
            scene_for(
                "DOM-INTERN",
                "企业员工周报与工时填报管理系统",
                "企业员工周报日报工时填报审阅",
            ),
            "enterprise",
        )
        self.assertEqual(
            scene_for("DOM-ATTEND", "高校课堂考勤请假系统", ""),
            "campus",
        )

    def test_shop_retail_vs_campus_secondhand(self) -> None:
        """鲜花走 flowers 货皮；数码/社区二手走 retail；校园二手成色档。"""
        from app.bake.engine_sql import domain_sql
        from app.bake.scene_scan import shop_product_kind

        flower = "基于 Spring Boot 与 Vue 的鲜花销售管理系统的设计与实现"
        polluted = "校园商城二手教材也可参考；花店接单与配送。"
        self.assertEqual(shop_product_kind(flower, polluted), "flowers")
        self.assertEqual(scene_for("DOM-SHOP", flower, polluted), "commercial")
        schema = build_domain_schema(flower, "DOM-SHOP", proposal_text=polluted)
        self.assertEqual(schema["labels"].get("authEyebrow"), "花店商城")
        keys = {f["key"] for f in schema["entities"]["archive"]["fields"]}
        self.assertNotIn("conditionGrade", keys)
        sql = domain_sql("DOM-SHOP", "thesis_test", title=flower, proposal_text=polluted)
        self.assertIn("康乃馨", sql)
        self.assertIn("biz_order", sql)
        self.assertIn("'pending'", sql)
        self.assertNotIn("基础款商品", sql)
        self.assertNotIn("校徽帆布袋", sql)
        self.assertNotIn("condition_grade", sql)
        self.assertNotIn("成色", sql)

        # 其它社会售卖主体零售档
        self.assertEqual(
            shop_product_kind("数码配件在线销售系统", "校园二手可作对比。"),
            "retail",
        )
        # 裸「二手」无校园词 → 零售档（不成色）
        self.assertEqual(shop_product_kind("社区二手闲置交易系统", ""), "retail")

        self.assertEqual(shop_product_kind("文印打印店订单管理系统", ""), "print")
        self.assertEqual(shop_product_kind("校园跑腿代买订单管理系统", ""), "errand")
        print_sql = domain_sql(
            "DOM-SHOP",
            "t",
            title="文印打印店订单管理系统",
            proposal_text="打印装订下单",
        )
        self.assertIn("胶装", print_sql)
        errand_sql = domain_sql(
            "DOM-SHOP",
            "t",
            title="校园跑腿代买订单管理系统",
            proposal_text="代买代取",
        )
        self.assertIn("代买", errand_sql)
        self.assertNotIn("机械键盘", errand_sql)
        campus = build_domain_schema(
            "校园二手商品交易系统",
            "DOM-SHOP",
            proposal_text="校内闲置教材数码流转。",
        )
        self.assertEqual(campus["labels"].get("authEyebrow"), "校园商城")
        campus_keys = {f["key"] for f in campus["entities"]["archive"]["fields"]}
        self.assertIn("conditionGrade", campus_keys)

    def test_food_canteen_vs_restaurant(self) -> None:
        """食堂 vs 社会餐饮两档：餐厅题不被正文食堂对比句洗成档口。"""
        from app.bake.engine_sql import domain_sql
        from app.bake.scene_scan import food_product_kind

        restaurant = "基于 Spring Boot 与 Vue 的小型餐厅点餐系统的设计与实现"
        polluted = "也可参考食堂档口堂食模式；本店支持外卖配送。"
        self.assertEqual(food_product_kind(restaurant, polluted), "restaurant")
        self.assertEqual(scene_for("DOM-FOOD", restaurant, polluted), "commercial")
        schema = build_domain_schema(restaurant, "DOM-FOOD", proposal_text=polluted)
        self.assertEqual(schema["labels"].get("authEyebrow"), "点餐外卖")
        isbn = next(
            f for f in schema["entities"]["archive"]["fields"] if f["key"] == "isbn"
        )
        self.assertEqual(isbn["label"], "门店")
        posts = schema["roles"]["staff_posts"]
        self.assertEqual(posts[0]["label"], "店员")
        sql = domain_sql(
            "DOM-FOOD", "thesis_test", title=restaurant, proposal_text=polluted
        )
        self.assertIn("总店", sql)
        self.assertNotIn("窗口A", sql)

        canteen = build_domain_schema(
            "高校食堂在线点餐系统",
            "DOM-FOOD",
            proposal_text="餐品目录与下单取餐。",
        )
        self.assertEqual(canteen["labels"].get("authEyebrow"), "食堂点餐")
        self.assertEqual(canteen["roles"]["staff_posts"][0]["label"], "档口店员")
        canteen_sql = domain_sql(
            "DOM-FOOD",
            "thesis_test",
            title="高校食堂在线点餐系统",
            proposal_text="餐品目录与下单取餐。",
        )
        self.assertIn("窗口A", canteen_sql)
        self.assertIn("学生公寓", canteen_sql)

    def test_parking_campus_vs_commercial_seed(self) -> None:
        """校园车位种子与资料页对齐；题名商场不被正文校园对比句洗档。"""
        from app.bake.engine_sql import domain_sql

        mall = "商场地下车位预约系统"
        polluted = "校园或园区车位紧张时也可参考。"
        self.assertEqual(scene_for("DOM-PARKING", mall, polluted), "commercial")
        mall_sql = domain_sql(
            "DOM-PARKING", "thesis_test", title=mall, proposal_text=polluted
        )
        self.assertIn("月租", mall_sql)
        self.assertIn("星河科技", mall_sql)

        campus_sql = domain_sql(
            "DOM-PARKING",
            "thesis_test",
            title="校园车位预约管理系统",
            proposal_text="教职工与学生预约校内车位。",
        )
        self.assertIn("教职工", campus_sql)
        self.assertIn("图书馆东侧", campus_sql)
        self.assertNotIn("星河科技", campus_sql)

    def test_hospital_pet_profile_and_seed(self) -> None:
        title, body = "宠物医院挂号预约系统", "宠主为爱宠选择医生挂号。"
        self.assertEqual(scene_for("DOM-HOSPITAL", title, body), "adopt")
        schema = build_domain_schema(title, "DOM-HOSPITAL", proposal_text=body)
        self.assertEqual(schema["labels"].get("authEyebrow"), "宠物挂号")
        keys = {f["key"] for f in schema["profileFields"]}
        self.assertIn("petName", keys)
        self.assertNotIn("patientNo", keys)
        from app.bake.engine_sql import domain_sql

        sql = domain_sql("DOM-HOSPITAL", "thesis_test", title=title, proposal_text=body)
        self.assertIn("宠主甲", sql)
        self.assertIn("豆豆", sql)
        self.assertNotIn("钱患者", sql)

    def test_attend_campus_seed_not_employee(self) -> None:
        title, body = "学生请假销假管理系统", ""
        from app.bake.engine_sql import domain_sql

        sql = domain_sql("DOM-ATTEND", "thesis_test", title=title, proposal_text=body)
        self.assertIn("学生甲", sql)
        self.assertIn("学工主管", sql)
        self.assertNotIn("员工甲", sql)
        self.assertIn("leave_type", sql)
        self.assertIn("事假", sql)
        self.assertNotIn("staff_person", sql)
        self.assertNotIn("职能岗", sql)

    def test_it_enterprise_seed_not_campus_student(self) -> None:
        title, body = "企业内网故障报修系统", "员工提交办公区终端故障。"
        schema = build_domain_schema(title, "DOM-IT", proposal_text=body)
        self.assertEqual(schema["labels"].get("authEyebrow"), "企业运维")
        from app.bake.engine_sql import domain_sql

        sql = domain_sql("DOM-IT", "thesis_test", title=title, proposal_text=body)
        self.assertIn("研发中心", sql)
        self.assertNotIn("陈同学", sql)
        self.assertNotIn("宿舍区", sql)

    def test_lost_adopt_and_community_shell(self) -> None:
        adopt = build_domain_schema(
            "宠物领养管理系统", "DOM-LOST", proposal_text="待领养档案与申请审核。"
        )
        self.assertEqual(adopt["labels"].get("authEyebrow"), "宠物领养")
        community = build_domain_schema(
            "小区失物招领", "DOM-LOST", proposal_text="社区物业失物启事认领。"
        )
        self.assertEqual(community["labels"].get("authEyebrow"), "社区招领")
        from app.bake.engine_sql import domain_sql

        sql = domain_sql(
            "DOM-LOST",
            "thesis_test",
            title="宠物领养管理系统",
            proposal_text="待领养档案与申请审核。",
        )
        self.assertIn("小橘", sql)
        self.assertNotIn("校园卡", sql)

    def test_single_template_domains_build(self) -> None:
        """无场景分支域：默认题名能出壳，不抛错。"""
        single = [
            "DOM-LIBRARY",
            "DOM-EQUIP",
            "DOM-COURSE",
            "DOM-DORM",
            "DOM-HOTEL",
            "DOM-ACTIVITY",
        ]
        for dom in single:
            with self.subTest(dom=dom):
                schema = build_domain_schema("测试课题", dom, proposal_text="")
                self.assertTrue(schema.get("labels") or schema.get("roles"))

    def test_timebank_community_vs_campus_profile(self) -> None:
        from app.bake.profile_fields import profile_fields_for
        from app.bake.scene_scan import scene_for

        self.assertEqual(
            scene_for("DOM-TIMEBANK", "社区时间银行志愿时长账户", "社区互助时长核销"),
            "community",
        )
        self.assertEqual(
            scene_for("DOM-TIMEBANK", "高校校园时间银行", "学号院系志愿时长账户"),
            "campus",
        )
        community = profile_fields_for(
            "DOM-TIMEBANK",
            title="社区时间银行志愿时长账户",
            proposal_text="社区互助时长核销",
        )
        keys = {f.get("key") for f in community}
        self.assertIn("communityName", keys)
        self.assertNotIn("studentNo", keys)
        campus = profile_fields_for(
            "DOM-TIMEBANK",
            title="高校校园时间银行",
            proposal_text="学号院系志愿时长账户",
        )
        ckeys = {f.get("key") for f in campus}
        self.assertIn("studentNo", ckeys)

    def test_thin_domains_scene_shell_and_seed(self) -> None:
        """原薄域：开题可解析场景，壳与种子跟开题走。"""
        from app.bake.engine_sql import domain_sql

        fund = build_domain_schema(
            "企业员工福利补助申请系统",
            "DOM-FUND",
            proposal_text="员工福利与困难补助线上申请。",
        )
        self.assertEqual(fund["labels"].get("authEyebrow"), "员工福利")
        self.assertIn("employeeNo", {f["key"] for f in fund["profileFields"]})
        self.assertNotIn("studentNo", {f["key"] for f in fund["profileFields"]})
        fund_sql = domain_sql(
            "DOM-FUND",
            "thesis_test",
            title="企业员工福利补助申请系统",
            proposal_text="员工福利与困难补助线上申请。",
        )
        self.assertIn("中秋慰问金", fund_sql)
        self.assertNotIn("国家助学金", fund_sql)

        campus_fund = build_domain_schema(
            "高校学生资助奖学金申请系统",
            "DOM-FUND",
            proposal_text="国家助学金与校内奖学金申请审核。",
        )
        self.assertEqual(campus_fund["labels"].get("authEyebrow"), "学生资助")
        campus_sql = domain_sql(
            "DOM-FUND",
            "thesis_test",
            title="高校学生资助奖学金申请系统",
            proposal_text="国家助学金与校内奖学金申请审核。",
        )
        self.assertIn("国家助学金", campus_sql)
        self.assertIn("studentNo", campus_sql)

        prop = build_domain_schema(
            "校园物业报修系统",
            "DOM-PROPERTY",
            proposal_text="学生公寓物业报修受理。",
        )
        self.assertEqual(prop["labels"].get("authEyebrow"), "校园物业")
        self.assertIn("studentNo", {f["key"] for f in prop["profileFields"]})

        media = build_domain_schema(
            "高校校园媒资点播系统",
            "DOM-MEDIA",
            proposal_text="校园教学片与活动回放点播。",
        )
        self.assertEqual(media["labels"].get("authEyebrow"), "校园媒资")
        media_sql = domain_sql(
            "DOM-MEDIA",
            "thesis_test",
            title="高校校园媒资点播系统",
            proposal_text="校园教学片与活动回放点播。",
        )
        self.assertIn("studentNo", media_sql)
        self.assertIn("教学片", media_sql)
        self.assertNotIn("memberNo", media_sql)

        forum_campus = build_domain_schema(
            "高校校园论坛系统",
            "DOM-FORUM",
            proposal_text="学生发帖回帖，版主审核。",
        )
        self.assertEqual(forum_campus["labels"].get("authEyebrow"), "校园论坛")
        self.assertIn("studentNo", {f["key"] for f in forum_campus["profileFields"]})
        forum_community = build_domain_schema(
            "小区兴趣社区论坛",
            "DOM-FORUM",
            proposal_text="邻里互助发帖回帖，社区论坛管理。",
        )
        self.assertEqual(forum_community["labels"].get("authEyebrow"), "兴趣社区")
        self.assertIn("communityName", {f["key"] for f in forum_community["profileFields"]})
        self.assertNotIn("studentNo", {f["key"] for f in forum_community["profileFields"]})
        community_sql = domain_sql(
            "DOM-FORUM",
            "thesis_test",
            title="小区兴趣社区论坛",
            proposal_text="邻里互助发帖回帖，社区论坛管理。",
        )
        self.assertIn("邻里互助", community_sql)
        self.assertIn("居民甲", community_sql)
        self.assertNotIn("期末复习资料汇总", community_sql)

    def test_event_product_kind_incident_vs_monitor(self) -> None:
        """应急上报皮 vs 监测皮：scene 可同为 community，文案与种子分叉。"""
        self.assertEqual(
            event_product_kind("社区公共卫生事件应急上报系统", "晨午检与因病缺课对比。"),
            "incident",
        )
        self.assertEqual(
            product_kind_for(
                "DOM-EVENT", "社区公共卫生事件应急上报系统", "晨午检对比。"
            ),
            "incident",
        )
        self.assertEqual(
            event_product_kind("社区健康监测", "社区网格员维护居民档案。"),
            "monitor",
        )
        # 现网默认：监测皮不变
        mon = build_domain_schema(
            "社区健康监测",
            "DOM-EVENT",
            proposal_text="社区网格员维护居民档案。",
        )
        self.assertEqual(mon["labels"].get("authEyebrow"), "社区公卫")
        self.assertEqual(mon["entities"]["archive"].get("label"), "对象")
        self.assertEqual(mon["roles"]["user"]["label"], "网格员")

        inc = build_domain_schema(
            "社区公共卫生事件应急上报系统",
            "DOM-EVENT",
            proposal_text="社区或校园在疫情排查；晨午检与因病缺课。",
        )
        self.assertEqual(scene_for("DOM-EVENT", "社区公共卫生事件应急上报系统", ""), "community")
        self.assertEqual(inc["labels"].get("authEyebrow"), "应急上报")
        self.assertEqual(inc["entities"]["archive"].get("label"), "事件")
        self.assertEqual(inc["roles"]["user"]["label"], "网格员")
        self.assertNotIn("健康打卡", " ".join(inc["labels"].get("authPoints") or []))
        log_fields = {
            f.get("label")
            for f in ((inc.get("entities") or {}).get("archiveLog") or {}).get("fields") or []
        }
        self.assertIn("现场情况", log_fields)
        self.assertNotIn("体温℃", log_fields)
        self.assertNotIn("血压", log_fields)
        self.assertEqual(inc["labels"].get("archiveLogSectionTitle"), "巡查登记")
        self.assertEqual(inc["labels"].get("archiveLogSubmitLabel"), "登记巡查")
        user_menus = {m["key"]: m["label"] for m in (inc.get("menus") or {}).get("user") or []}
        self.assertEqual(user_menus.get("archive"), "事件列表")
        # monitor 仍保留体征字段
        mon_log = {
            f.get("label")
            for f in ((mon.get("entities") or {}).get("archiveLog") or {}).get("fields") or []
        }
        self.assertIn("体温℃", mon_log)
        sql = domain_sql(
            "DOM-EVENT",
            "thesis_test",
            title="社区公共卫生事件应急上报系统",
            proposal_text="社区网格员上报公共卫生事件。",
        )
        self.assertIn("聚集性发热线索", sql)
        self.assertNotIn("体温异常待回访", sql)

    def test_ensure_spec_schema_refreshes_stale_event_product_skin(self) -> None:
        """匹配期留下的监测壳，一键生成时须按开题重编成应急皮（勿只更新 SQL 种子）。"""
        stale = build_domain_schema(
            "社区健康监测",
            "DOM-EVENT",
            proposal_text="社区网格员维护居民档案。",
        )
        self.assertEqual(stale["entities"]["archive"].get("label"), "对象")
        out = ensure_spec_schema(
            {
                "domain": "DOM-EVENT",
                "title": "社区公共卫生事件应急上报系统",
                "proposal_text": "社区网格员上报公共卫生事件与隐患。",
                "schema": stale,
                "archetype": "ARCH-FLOW",
            }
        )
        arch = (out.get("schema") or {}).get("entities", {}).get("archive") or {}
        labels = (out.get("schema") or {}).get("labels") or {}
        self.assertEqual(arch.get("label"), "事件")
        self.assertEqual(labels.get("authEyebrow"), "应急上报")
        self.assertEqual(labels.get("archiveLogSubmitLabel"), "登记巡查")


if __name__ == "__main__":
    unittest.main()
