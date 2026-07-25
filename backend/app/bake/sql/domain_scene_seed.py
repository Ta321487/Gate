"""具名域按 scene 替换演示种子（表结构不变，只换人名/地点/公告）。

DOM-EVENT 仍走 ``event_scene_seed``；本模块覆盖其余易与校园模板打架的域。
"""

from __future__ import annotations

import re

from app.bake.scene_scan import scene_for

# 模板种子均从 sys_user INSERT 起至文件末；整块替换，避免半改漏行
_USER_SEED_START = re.compile(
    r"INSERT INTO sys_user \(username, password, role, nickname, phone, profile_json, "
    r"super_admin, profile_editable, enabled\) VALUES\n",
)

def _replace_user_seed_tail(sql: str, seed: str) -> str:
    m = _USER_SEED_START.search(sql)
    if not m:
        return sql
    return sql[: m.start()] + seed.rstrip() + "\n"

_ATTEND_CAMPUS = """\
INSERT INTO sys_user (username, password, role, nickname, phone, profile_json, super_admin, profile_editable, enabled) VALUES
('admin', 'admin123', 'admin', '学工主管', '13800000000', '{}', 1, 0, 1),
('subadmin', 'sub123', 'admin', '辅导员', '13800000001', '{}', 0, 1, 1),
('user', 'user123', 'user', '学生甲', '13800000002',
 '{"realName":"周明","email":"zhou@demo.edu","gender":"男","studentNo":"S2026008","dept":"计算机学院","className":"软工2301"}',
 0, 1, 1)
ON DUPLICATE KEY UPDATE nickname=VALUES(nickname), phone=VALUES(phone), profile_json=VALUES(profile_json);

INSERT IGNORE INTO category (id, name) VALUES (1, '本科生'), (2, '研究生'), (3, '留学生');
INSERT IGNORE INTO staff_person (id, title, author, isbn, category_id, stock, status) VALUES
(1, '周明', '计算机学院 / 软工2301', 'S2026008 / 在校', 1, 1, 'available'),
(2, '李芳', '外国语学院 / 英译2202', 'S2022012 / 在校', 1, 1, 'available'),
(3, '王强', '计算机学院 / 研一', 'G2026003 / 请假中', 2, 1, 'available'),
(4, '赵敏', '经济学院 / 国贸2301', 'S2026044 / 在校', 1, 1, 'available'),
(5, '陈浩', '国际教育学院', 'L2026088 / 在校', 3, 1, 'available');
INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '请假须知', '事假须提前申请；病假可补交证明；销假请在返校当日确认。', 'admin', '学工主管'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='请假须知');
INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '本月考勤', '月底前提交未销假单据，逾期将记入学工考勤异常。', 'admin', '学工主管'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='本月考勤');
"""

_PARCEL_COMMUNITY = """\
INSERT INTO sys_user (username, password, role, nickname, phone, profile_json, super_admin, profile_editable, enabled) VALUES
('admin', 'admin123', 'admin', '驿站主管', '13800000000', '{}', 1, 0, 1),
('subadmin', 'sub123', 'admin', '驿站店员', '13800000001', '{}', 0, 1, 1),
('user', 'user123', 'user', '居民甲', '13800000002',
 '{"realName":"刘明","email":"liu@demo.com","gender":"男","communityName":"阳光小区","contactWechat":"liu_demo","usualPlace":"3栋驿站"}',
 0, 1, 1)
ON DUPLICATE KEY UPDATE nickname=VALUES(nickname), phone=VALUES(phone), profile_json=VALUES(profile_json);

INSERT IGNORE INTO category (id, name) VALUES (1, '普通件'), (2, '生鲜件'), (3, '大件');
INSERT IGNORE INTO parcel (id, title, author, isbn, category_id, stock, status) VALUES
(1, '圆通YT8821001', '阳光小区驿站', '取件码 3182 / A12 柜', 1, 1, 'available'),
(2, '中通ZT9912002', '阳光小区驿站', '取件码 5521 / 冷藏区', 2, 1, 'available'),
(3, '顺丰SF1003003', '物业代收点', '取件码 7740 / 大件区', 3, 1, 'available'),
(4, '韵达YD2204004', '阳光小区驿站', '取件码 1098 / B03 柜', 1, 1, 'available'),
(5, '极兔JT3305005', '阳光小区驿站', '取件码 6644 / A08 柜', 1, 1, 'available');
INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '取件须知', '请凭取件码与本人手机号取件；超时未取将移至逾期架。', 'admin', '驿站主管'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='取件须知');
INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '营业时间', '驿站工作日 8:00-21:00，周末 9:00-20:00。', 'admin', '驿站主管'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='营业时间');
"""

_LOST_COMMUNITY = """\
INSERT INTO sys_user (username, password, role, nickname, phone, profile_json, super_admin, profile_editable, enabled) VALUES
('admin', 'admin123', 'admin', '招领主管', '13800000000', '{}', 1, 0, 1),
('subadmin', 'sub123', 'admin', '招领管理员', '13800000001', '{}', 0, 1, 1),
('user', 'user123', 'user', '居民甲', '13800000002',
 '{"realName":"王芳","email":"wang@demo.com","gender":"女","contactWechat":"wang_demo","usualPlace":"阳光小区","orgName":"3栋2单元"}',
 0, 1, 1)
ON DUPLICATE KEY UPDATE nickname=VALUES(nickname), phone=VALUES(phone), profile_json=VALUES(profile_json);

INSERT IGNORE INTO category (id, name) VALUES (1, '证件卡类'), (2, '电子数码'), (3, '生活用品');
INSERT IGNORE INTO lost_item (id, title, author, isbn, category_id, stock, status) VALUES
(1, '门禁卡（尾号 8821）', '物业值班', '阳光小区门岗 / 蓝色挂绳', 1, 1, 'available'),
(2, '黑色无线耳机盒', '快递驿站', '3栋大厅 / AirPods 样式', 2, 1, 'available'),
(3, '蓝色水杯', '居民甲', '健身步道 / 杯身有贴纸', 3, 1, 'available'),
(4, '身份证复印件套', '保洁员', '地下车库电梯口', 1, 1, 'available'),
(5, '充电器一套', '业委会', '会所阅览室 / Type-C 线', 2, 1, 'available');
INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '招领须知', '认领时请提供有效身份与物品特征；审核通过后到物业领取。', 'admin', '招领主管'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='招领须知');
INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '本周公示', '证件与数码类启事已更新，请及时认领。', 'admin', '招领主管'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='本周公示');
"""

_LOST_ADOPT = """\
INSERT INTO sys_user (username, password, role, nickname, phone, profile_json, super_admin, profile_editable, enabled) VALUES
('admin', 'admin123', 'admin', '领养站主管', '13800000000', '{}', 1, 0, 1),
('subadmin', 'sub123', 'admin', '领养专员', '13800000001', '{}', 0, 1, 1),
('user', 'user123', 'user', '申请人甲', '13800000002',
 '{"realName":"王芳","email":"wang@demo.com","gender":"女","contactWechat":"wang_demo","homeAddress":"阳光小区3栋","petExperience":"养过猫"}',
 0, 1, 1)
ON DUPLICATE KEY UPDATE nickname=VALUES(nickname), phone=VALUES(phone), profile_json=VALUES(profile_json);

INSERT IGNORE INTO category (id, name) VALUES (1, '猫'), (2, '狗'), (3, '其他');
INSERT IGNORE INTO lost_item (id, title, author, isbn, category_id, stock, status) VALUES
(1, '小橘 / A01', '领养专员李华', '已绝育 / 疫苗齐全 / 亲人', 1, 1, 'available'),
(2, '豆豆 / B03', '领养专员王芳', '中型犬 / 需户外散步', 2, 1, 'available'),
(3, '奶茶 / A07', '领养专员张敏', '英短混血 / 室内饲养', 1, 1, 'available'),
(4, '阿黄 / C02', '领养专员赵强', '已驱虫 / 适合有院落家庭', 2, 1, 'available'),
(5, '团子 / D01', '领养专员陈洁', '垂耳兔 / 需笼养空间', 3, 1, 'available');
INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '领养须知', '请如实填写养宠条件与联系方式；审核通过后按通知办理交接。', 'admin', '领养站主管'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='领养须知');
INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '本周待领养', '猫咪与犬只档案已更新，欢迎预约看宠。', 'admin', '领养站主管'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='本周待领养');
"""

_IT_ENTERPRISE = """\
INSERT INTO sys_user (username, password, role, nickname, phone, profile_json, super_admin, profile_editable, enabled) VALUES
('admin', 'admin123', 'admin', '运维主管', '13800000000', '{}', 1, 0, 1),
('subadmin', 'sub123', 'admin', '运维员', '13800000001', '{}', 0, 1, 1),
('user', 'user123', 'user', '员工甲', '13800000002',
 '{"realName":"陈工","email":"chen@demo.com","gender":"男","identityType":"员工","employeeNo":"E20230108","dept":"研发中心","officeOrDorm":"A座1208","title":"工程师"}',
 0, 1, 1)
ON DUPLICATE KEY UPDATE nickname=VALUES(nickname), phone=VALUES(phone), profile_json=VALUES(profile_json);

INSERT IGNORE INTO campus_zone (id, name) VALUES (1, '办公区'), (2, '机房区');
INSERT IGNORE INTO endpoint (id, building_id, code) VALUES (1, 1, '1201'), (2, 1, '1208'), (3, 2, 'M01');
INSERT IGNORE INTO fault_type (id, name, sort_no) VALUES (1, '内网', 1), (2, '终端', 2), (3, '打印机', 3);

INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '报修须知', '请写明办公区、终端与故障现象并上传截图，运维将尽快受理。', 'admin', '运维主管'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='报修须知');
"""

_RECRUIT_ENTERPRISE = """\
INSERT INTO sys_user (username, password, role, nickname, phone, profile_json, super_admin, profile_editable, enabled) VALUES
('admin', 'admin123', 'admin', '招聘主管', '13800000000', '{}', 1, 0, 1),
('subadmin', 'sub123', 'admin', 'HR专员', '13800000001', '{}', 0, 1, 1),
('user', 'user123', 'user', '求职者甲', '13800000002',
 '{"realName":"林晓","email":"lin@demo.com","gender":"女","identityType":"社会求职","dept":"Java开发","jobTitle":"中级开发","workYears":"3年"}',
 0, 1, 1)
ON DUPLICATE KEY UPDATE nickname=VALUES(nickname), phone=VALUES(phone), profile_json=VALUES(profile_json);

INSERT IGNORE INTO category (id, name) VALUES (1, '技术岗'), (2, '职能岗'), (3, '实习岗');
INSERT IGNORE INTO job_post (id, title, author, isbn, category_id, stock, status) VALUES
(1, 'Java 开发工程师', '研发中心', '15-22k / 3年经验', 1, 1, 'available'),
(2, '前端工程师', '数字化办', '12-18k / 2年经验', 1, 1, 'available'),
(3, '行政助理', '综合办', '6-8k / 大专及以上', 2, 1, 'available'),
(4, '测试工程师', '质量部', '10-15k / 社招', 1, 1, 'available'),
(5, '产品助理实习', '产品组', '面议 / 周报实习', 3, 1, 'available');
INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '投递须知', '请如实填写经历；初筛通过后由 HR 预约面试（演示环境无视频面试）。', 'admin', '招聘主管'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='投递须知');
INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '本周岗位', '技术岗与职能岗已更新，请及时投递。', 'admin', '招聘主管'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='本周岗位');
"""

_HOSPITAL_PET = """\
INSERT INTO sys_user (username, password, role, nickname, phone, profile_json, super_admin, profile_editable, enabled) VALUES
('admin', 'admin123', 'admin', '宠物医院主管', '13800000000', '{}', 1, 0, 1),
('subadmin', 'sub123', 'admin', '挂号员', '13800000001', '{}', 0, 1, 1),
('patient', 'patient123', 'patient', '宠主甲', '13800000002',
 '{"realName":"钱女士","email":"qian@demo.com","gender":"女","petName":"豆豆","petSpecies":"狗","ownerName":"钱女士"}',
 0, 1, 1)
ON DUPLICATE KEY UPDATE nickname=VALUES(nickname), phone=VALUES(phone), profile_json=VALUES(profile_json);

INSERT IGNORE INTO category (id, name) VALUES (1, '内科'), (2, '外科'), (3, '皮肤科');
INSERT IGNORE INTO doctor (id, title, author, isbn, category_id, stock, status) VALUES
(1, '张医生', '15.00', '宠物内科 / 上午门诊', 1, 1, 'available'),
(2, '李医生', '15.00', '软组织外科', 2, 1, 'available'),
(3, '王医生', '20.00', '皮肤与过敏专科', 3, 1, 'available');
INSERT IGNORE INTO resource_slot (id, item_id, start_at, end_at, capacity, booked) VALUES
(1, 1, '2026-09-20 09:00:00', '2026-09-20 10:00:00', 3, 0),
(2, 1, '2026-09-20 10:00:00', '2026-09-20 11:00:00', 3, 0),
(3, 1, '2026-09-20 14:00:00', '2026-09-20 15:00:00', 3, 0),
(4, 1, '2026-09-20 15:00:00', '2026-09-20 16:00:00', 3, 0),
(5, 2, '2026-09-20 09:00:00', '2026-09-20 10:00:00', 3, 0),
(6, 2, '2026-09-20 10:00:00', '2026-09-20 11:00:00', 3, 0),
(7, 2, '2026-09-20 14:00:00', '2026-09-20 15:00:00', 3, 0),
(8, 2, '2026-09-20 15:00:00', '2026-09-20 16:00:00', 3, 0),
(9, 3, '2026-09-20 09:00:00', '2026-09-20 10:00:00', 3, 0),
(10, 3, '2026-09-20 10:00:00', '2026-09-20 11:00:00', 3, 0),
(11, 3, '2026-09-20 14:00:00', '2026-09-20 15:00:00', 3, 0),
(12, 3, '2026-09-20 15:00:00', '2026-09-20 16:00:00', 3, 0);
INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '挂号须知', '号源有限；请填写宠物昵称与就诊人；按时到诊；就诊完成后由前台办结。', 'admin', '宠物医院主管'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='挂号须知');
"""

def apply_domain_scene_seed(
    domain: str,
    sql: str,
    *,
    title: str = "",
    proposal_text: str = "",
) -> str:
    """按 scene_for 替换演示种子；默认/校园档保留模板原文（除非另有覆盖）。"""
    if domain == "DOM-EVENT":
        from app.bake.sql.event_scene_seed import apply_event_scene_seed

        return apply_event_scene_seed(sql, title=title, proposal_text=proposal_text)

    scene = scene_for(domain, title, proposal_text)
    seed: str | None = None
    if domain == "DOM-ATTEND" and scene == "campus":
        seed = _ATTEND_CAMPUS
    elif domain == "DOM-PARCEL" and scene == "community":
        seed = _PARCEL_COMMUNITY
    elif domain == "DOM-LOST" and scene == "community":
        seed = _LOST_COMMUNITY
    elif domain == "DOM-LOST" and scene == "adopt":
        seed = _LOST_ADOPT
    elif domain == "DOM-IT" and scene == "enterprise":
        seed = _IT_ENTERPRISE
    elif domain == "DOM-RECRUIT" and scene == "enterprise":
        seed = _RECRUIT_ENTERPRISE
    elif domain == "DOM-HOSPITAL" and scene == "adopt":
        seed = _HOSPITAL_PET
    if seed is None:
        return sql
    return _replace_user_seed_tail(sql, seed)
