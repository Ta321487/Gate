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

_DATING_CAMPUS = """\
INSERT INTO sys_user (username, password, role, nickname, phone, profile_json, super_admin, profile_editable, enabled) VALUES
('admin', 'admin123', 'admin', '学工主管', '13800000000', '{}', 1, 0, 1),
('subadmin', 'sub123', 'admin', '联谊辅导员', '13800000001', '{}', 0, 1, 1),
('user', 'user123', 'user', '同学甲', '13800000002',
 '{"realName":"陈悦","email":"chen@demo.com","gender":"女","identityType":"学生","studentNo":"S20260421","dept":"软件工程","gradeYear":"大三"}',
 0, 1, 1)
ON DUPLICATE KEY UPDATE nickname=VALUES(nickname), phone=VALUES(phone), profile_json=VALUES(profile_json);

INSERT IGNORE INTO category (id, name) VALUES (1, '同城相亲'), (2, '校园联谊'), (3, '兴趣交友');
INSERT IGNORE INTO dating_profile (id, title, author, isbn, category_id, stock, status) VALUES
(1, '小雨 · 大三', '软件工程', '希望认识踏实同学', 2, 1, 'available'),
(2, '阿明 · 研一', '计算机', '喜欢户外与阅读', 2, 1, 'available'),
(3, '林同学 · 大二', '汉语言', '校园联谊友好认识', 2, 1, 'available'),
(4, '周周 · 大四', '工商管理', '认真交往，先做朋友', 2, 1, 'available'),
(5, '乐乐 · 研二', '设计学', '兴趣交友为主', 3, 1, 'available');
INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '牵线须知', '请如实填写资料；学工审核通过后可一对一私信沟通。', 'admin', '学工主管'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='牵线须知');
INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '本周联谊', '校园联谊资料已更新，可发起牵线意向。', 'admin', '学工主管'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='本周联谊');
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

_FUND_ENTERPRISE = """\
INSERT INTO sys_user (username, password, role, nickname, phone, profile_json, super_admin, profile_editable, enabled) VALUES
('admin', 'admin123', 'admin', '福利主管', '13800000000', '{}', 1, 0, 1),
('subadmin', 'sub123', 'admin', '人事专员', '13800000001', '{}', 0, 1, 1),
('user', 'user123', 'user', '员工甲', '13800000002',
 '{"realName":"陈工","email":"chen@demo.com","gender":"男","identityType":"员工","employeeNo":"E20230108","dept":"研发中心"}',
 0, 1, 1)
ON DUPLICATE KEY UPDATE nickname=VALUES(nickname), phone=VALUES(phone), profile_json=VALUES(profile_json);

INSERT IGNORE INTO category (id, name) VALUES (1, '节日慰问'), (2, '困难补助'), (3, '培训补贴');
INSERT IGNORE INTO fund_program (id, title, author, isbn, category_id, stock, status) VALUES
(1, '中秋慰问金', '综合办', '在职满 3 个月 / 名额不限', 1, 1, 'available'),
(2, '职工困难补助', '工会/人事', '困难证明 / 年审一次', 2, 1, 'available'),
(3, '外部培训补贴', '培训中心', '培训发票与结业证明', 3, 1, 'available'),
(4, '高温津贴补发', '综合办', '一线岗位名册', 1, 1, 'available'),
(5, '资格考证补贴', '人事部', '证书复印件 / 限额 2000', 3, 1, 'available');
INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '福利须知', '请按通知提交申请材料；审批通过后留意发放进度。', 'admin', '福利主管'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='福利须知');
INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '本月福利', '节日慰问与培训补贴本月开放申报。', 'admin', '福利主管'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='本月福利');
"""

_GRADE_ENTERPRISE = """\
INSERT INTO sys_user (username, password, role, nickname, phone, profile_json, super_admin, profile_editable, enabled) VALUES
('admin', 'admin123', 'admin', '培训主管', '13800000000', '{}', 1, 0, 1),
('subadmin', 'sub123', 'admin', '培训专员', '13800000001', '{}', 0, 1, 1),
('user', 'user123', 'user', '学员甲', '13800000002',
 '{"realName":"林晓","email":"lin@demo.com","gender":"女","identityType":"员工","employeeNo":"E20230421","dept":"客户成功"}',
 0, 1, 1)
ON DUPLICATE KEY UPDATE nickname=VALUES(nickname), phone=VALUES(phone), profile_json=VALUES(profile_json);

INSERT IGNORE INTO category (id, name) VALUES (1, '入职必修'), (2, '岗位认证'), (3, '选修内训');
INSERT IGNORE INTO course_item (id, title, author, isbn, category_id, stock, status) VALUES
(1, '信息安全合规', '张讲师', 'SEC-01 / 8 学时', 1, 1, 'available'),
(2, '产品知识认证', '李讲师', 'PROD-02 / 考核通过', 2, 1, 'available'),
(3, '沟通与协作', '赵讲师', 'SOFT-03 / 4 学时', 3, 1, 'available'),
(4, '数据报表入门', '陈讲师', 'DATA-04 / 6 学时', 3, 1, 'available'),
(5, '新员工入职营', '王讲师', 'ONB-00 / 必过', 1, 1, 'available');
INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '成绩须知', '成绩更正与补考申请由培训专员审核；不对接外部证书库。', 'admin', '培训主管'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='成绩须知');
INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '补考安排', '补考名单以培训公告为准，请按时提交申请。', 'admin', '培训主管'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='补考安排');
"""

_INTERN_ENTERPRISE = """\
INSERT INTO sys_user (username, password, role, nickname, phone, profile_json, super_admin, profile_editable, enabled) VALUES
('admin', 'admin123', 'admin', '实习主管', '13800000000', '{}', 1, 0, 1),
('subadmin', 'sub123', 'admin', '带教导师', '13800000001', '{}', 0, 1, 1),
('user', 'user123', 'user', '实习生甲', '13800000002',
 '{"realName":"小陈","email":"chen@demo.com","gender":"男","identityType":"实习生","employeeNo":"I2026001","dept":"研发中心","internOrg":"本公司"}',
 0, 1, 1)
ON DUPLICATE KEY UPDATE nickname=VALUES(nickname), phone=VALUES(phone), profile_json=VALUES(profile_json);

INSERT IGNORE INTO category (id, name) VALUES (1, '开发实习'), (2, '运维实习'), (3, '综合实习');
INSERT IGNORE INTO intern_post (id, title, author, isbn, category_id, stock, status) VALUES
(1, '后端开发实习', '王工', '研发中心 / Java', 1, 1, 'available'),
(2, '运维实习', '李工', '基础架构 / 运维', 2, 1, 'available'),
(3, '行政综合实习', '赵主管', '综合办 / 文员', 3, 1, 'available'),
(4, '测试实习', '周工', '质量部 / 测试', 1, 1, 'available'),
(5, '数据分析实习', '陈老师', '数据组 / 分析', 3, 1, 'available');
INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '周报须知', '每周日前提交周报；带教导师审阅后方可计入实习考勤。', 'admin', '实习主管'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='周报须知');
INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '鉴定提醒', '实习结束前完成鉴定材料（电子签不在本期）。', 'admin', '实习主管'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='鉴定提醒');
"""

_LABSAFE_ENTERPRISE = """\
INSERT INTO sys_user (username, password, role, nickname, phone, profile_json, super_admin, profile_editable, enabled) VALUES
('admin', 'admin123', 'admin', '安环主管', '13800000000', '{}', 1, 0, 1),
('subadmin', 'sub123', 'admin', '安全员', '13800000001', '{}', 0, 1, 1),
('user', 'user123', 'user', '员工甲', '13800000002',
 '{"realName":"周工","email":"zhou@demo.com","gender":"男","identityType":"员工","employeeNo":"E2026008","dept":"工艺研发"}',
 0, 1, 1)
ON DUPLICATE KEY UPDATE nickname=VALUES(nickname), phone=VALUES(phone), profile_json=VALUES(profile_json);

INSERT IGNORE INTO category (id, name) VALUES (1, '化学实验室'), (2, '机房'), (3, '金工实训');
INSERT IGNORE INTO lab_room (id, title, author, isbn, category_id, stock, status) VALUES
(1, '中试化学实验室 L1', '一号厂区 / 张工', '二级安全 / 需 EHS 培训', 1, 1, 'available'),
(2, '自动化机房 M2', '研发楼 / 李工', '门禁卡准入', 2, 1, 'available'),
(3, '金工维修间 W3', '维修中心 / 王工', '护目镜必戴', 3, 1, 'available'),
(4, '分析检测室 L2', '一号厂区 / 赵工', '危化品柜已上锁', 1, 1, 'available'),
(5, '嵌入式调试室 M5', '研发楼 / 陈工', '示波器与开发板在架', 2, 1, 'available');
INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '准入须知', '请完成安环培训并上传证明；审核通过后方可进室。', 'admin', '安环主管'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='准入须知');
INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '本周准入', '本周开放中试与机房准入申请，请提前完成培训。', 'admin', '安环主管'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='本周准入');
"""

_PROPERTY_CAMPUS = """\
INSERT INTO sys_user (username, password, role, nickname, phone, profile_json, super_admin, profile_editable, enabled) VALUES
('admin', 'admin123', 'admin', '物业主管', '13800000000', '{}', 1, 0, 1),
('subadmin', 'sub123', 'admin', '物业调度', '13800000001', '{}', 0, 1, 1),
('user', 'user123', 'user', '师生甲', '13800000002',
 '{"realName":"张同学","email":"zhang@demo.edu","gender":"女","identityType":"学生","studentNo":"S20260101","dept":"计算机学院","dormBuilding":"学生公寓3号楼","dormRoom":"405"}',
 0, 1, 1)
ON DUPLICATE KEY UPDATE nickname=VALUES(nickname), phone=VALUES(phone), profile_json=VALUES(profile_json);

INSERT IGNORE INTO building (id, name) VALUES (1, '学生公寓3号楼'), (2, '教学楼A');
INSERT IGNORE INTO room (id, building_id, code) VALUES (1, 1, '405'), (2, 1, '406'), (3, 2, '201');
INSERT IGNORE INTO ticket_type (id, name, sort_no) VALUES (1, '水电', 1), (2, '公共设施', 2), (3, '门禁', 3);

INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '报修须知', '请填写公寓楼栋房号与故障描述，物业将尽快受理。', 'admin', '物业主管'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='报修须知');
"""

_CRM_CAMPUS = """\
INSERT INTO sys_user (username, password, role, nickname, phone, profile_json, super_admin, profile_editable, enabled) VALUES
('admin', 'admin123', 'admin', '创业导师', '13800000000', '{}', 1, 0, 1),
('subadmin', 'sub123', 'admin', '项目助理', '13800000001', '{}', 0, 1, 1),
('user', 'user123', 'user', '团队成员甲', '13800000002',
 '{"realName":"周明","email":"zhou@demo.edu","gender":"男","identityType":"学生","studentNo":"S2026008","dept":"计算机学院创业团队"}',
 0, 1, 1)
ON DUPLICATE KEY UPDATE nickname=VALUES(nickname), phone=VALUES(phone), profile_json=VALUES(profile_json);

INSERT IGNORE INTO category (id, name) VALUES (1, '重点客户'), (2, '普通客户'), (3, '潜在线索');
INSERT IGNORE INTO customer (id, title, author, isbn, category_id, stock, status) VALUES
(1, '校友企业·星河科技', '李总', '13811110001 / 意向校企合作', 1, 1, 'available'),
(2, '青禾教育培训', '王老师', '13922220002 / 咨询联合培养', 2, 1, 'available'),
(3, '双创周展会线索', '张女士', '13733330003 / 展会名片', 3, 1, 'available'),
(4, '海川物流校招对接', '赵经理', '13644440004 / 实习岗位跟进', 1, 1, 'available'),
(5, '邻里便利店连锁', '陈店长', '13555550005 / 创业实践点', 2, 1, 'available');
INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '跟进须知', '请如实登记联系结果；重要商机请及时提交跟进单由导师确认。', 'admin', '创业导师'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='跟进须知');
INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '本周重点', '校友企业续约与双创展会线索请于周五前提交跟进。', 'admin', '创业导师'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='本周重点');
"""

_ASSET_CAMPUS = """\
INSERT INTO sys_user (username, password, role, nickname, phone, profile_json, super_admin, profile_editable, enabled) VALUES
('admin', 'admin123', 'admin', '资产主管', '13800000000', '{}', 1, 0, 1),
('subadmin', 'sub123', 'admin', '库管员', '13800000001', '{}', 0, 1, 1),
('user', 'user123', 'user', '申领人甲', '13800000002',
 '{"realName":"张老师","email":"zhang@demo.edu","gender":"男","identityType":"教职工","employeeNo":"T20230018","dept":"计算机学院","jobTitle":"实验员","officeLoc":"实训楼 205"}',
 0, 1, 1)
ON DUPLICATE KEY UPDATE nickname=VALUES(nickname), phone=VALUES(phone), profile_json=VALUES(profile_json);

INSERT IGNORE INTO category (id, name) VALUES (1, '办公耗材'), (2, '教学设备'), (3, '劳保用品');
INSERT IGNORE INTO asset (id, title, author, isbn, category_id, stock, status) VALUES
(1, 'A4 复印纸', '70g / 500 张', 'AS-PAPER-001', 1, 40, 'available'),
(2, '台式教学电脑', '联想启天 / i5', 'AS-PC-002', 2, 3, 'available'),
(3, '安全帽', 'ABS 黄色', 'AS-PPE-003', 3, 20, 'available'),
(4, '签字笔盒装', '0.5mm 黑色 / 12 支', 'AS-PEN-004', 1, 25, 'available'),
(5, '移动硬盘', '1TB USB3.0', 'AS-HDD-005', 2, 2, 'available');
INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '领用须知', '请按需申领、如实填写用途；教学设备领用后请妥善保管，耗材出库不退。', 'admin', '资产主管'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='领用须知');
INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '本周盘点', '周五下午库房盘点，请提前完成申领。', 'admin', '资产主管'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='本周盘点');
"""

_MEETING_ENTERPRISE = """\
INSERT INTO sys_user (username, password, role, nickname, phone, profile_json, super_admin, profile_editable, enabled) VALUES
('admin', 'admin123', 'admin', '行政主管', '13800000000', '{}', 1, 0, 1),
('subadmin', 'sub123', 'admin', '预约管理员', '13800000001', '{}', 0, 1, 1),
('user', 'user123', 'user', '员工甲', '13800000002',
 '{"realName":"赵工","email":"zhao@demo.com","gender":"男","identityType":"员工","employeeNo":"E1001","dept":"综合办","jobTitle":"专员"}',
 0, 1, 1)
ON DUPLICATE KEY UPDATE nickname=VALUES(nickname), phone=VALUES(phone), profile_json=VALUES(profile_json);

INSERT IGNORE INTO category (id, name) VALUES (1, '小型'), (2, '中型'), (3, '大型');
INSERT IGNORE INTO room (id, title, author, isbn, category_id, stock, status) VALUES
(1, 'A101 洽谈室', '0', 'A座-101 / 6人', 1, 1, 'available'),
(2, 'B203 会议室', '0', 'B座-203 / 12人', 2, 1, 'available'),
(3, '多功能厅', '0', '一层大厅 / 80人', 3, 1, 'available');
INSERT IGNORE INTO resource_slot (id, item_id, start_at, end_at, capacity, booked) VALUES
(1, 1, '2026-09-20 09:00:00', '2026-09-20 10:00:00', 1, 0),
(2, 1, '2026-09-20 10:00:00', '2026-09-20 11:00:00', 1, 0),
(3, 1, '2026-09-20 14:00:00', '2026-09-20 15:00:00', 1, 0),
(4, 1, '2026-09-20 15:00:00', '2026-09-20 16:00:00', 1, 0),
(5, 2, '2026-09-20 09:00:00', '2026-09-20 10:00:00', 1, 0),
(6, 2, '2026-09-20 10:00:00', '2026-09-20 11:00:00', 1, 0),
(7, 2, '2026-09-20 14:00:00', '2026-09-20 15:00:00', 1, 0),
(8, 2, '2026-09-20 15:00:00', '2026-09-20 16:00:00', 1, 0),
(9, 3, '2026-09-20 09:00:00', '2026-09-20 10:00:00', 1, 0),
(10, 3, '2026-09-20 10:00:00', '2026-09-20 11:00:00', 1, 0),
(11, 3, '2026-09-20 14:00:00', '2026-09-20 15:00:00', 1, 0),
(12, 3, '2026-09-20 15:00:00', '2026-09-20 16:00:00', 1, 0);
INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '会议室预约须知', '请按预约时段使用并按时离开；可取消释放名额。', 'admin', '行政主管'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='会议室预约须知');
"""

_FORUM_COMMUNITY = """\
INSERT INTO sys_user (username, password, role, nickname, phone, profile_json, super_admin, profile_editable, enabled) VALUES
('admin', 'admin123', 'admin', '站长', '13800000000', '{}', 1, 0, 1),
('subadmin', 'sub123', 'admin', '版主甲', '13800000001', '{}', 0, 1, 1),
('user', 'user123', 'user', '居民甲', '13800000002',
 '{"realName":"王芳","email":"wang@demo.com","gender":"女","identityType":"居民","communityName":"阳光小区","preferredGenre":"邻里互助"}',
 0, 1, 1)
ON DUPLICATE KEY UPDATE nickname=VALUES(nickname), phone=VALUES(phone), profile_json=VALUES(profile_json);

INSERT IGNORE INTO category (id, name) VALUES (1, '邻里互助'), (2, '二手闲置'), (3, '活动通知');
INSERT IGNORE INTO board_moderator (id, category_id, username) VALUES
(1, 1, 'subadmin'), (2, 2, 'subadmin');
INSERT IGNORE INTO tag (id, name) VALUES (1, '求助'), (2, '闲置'), (3, '活动'), (4, '物业');
INSERT IGNORE INTO post (id, title, author, isbn, category_id, stock, status) VALUES
(1, '周末义诊与健康咨询', '业委会', '<p>本周六会所大厅开展<strong>义诊</strong>，欢迎邻里参加。</p>', 3, 1, 'available'),
(2, '出闲置折叠桌', '居民甲', '<p>九成新折叠桌，自提优先。</p>', 2, 1, 'available'),
(3, '寻周末拼车去火车站', '居民乙', '<p>周日上午出发，可拼两人。</p>', 1, 1, 'available'),
(4, '小区绿化浇水志愿者', '物业值班', '<p>本周志愿浇水时间表见楼下。</p>', 3, 1, 'available'),
(5, '求推荐靠谱开锁师傅', '居民丙', '<p>门锁偶发失灵，求邻里推荐。</p>', 1, 1, 'available');
INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '社区公约', '请文明发帖；广告与人身攻击帖将被下架。', 'admin', '站长'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='社区公约');
INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '版块说明', '邻里互助与二手闲置请如实描述，线下交易注意安全。', 'admin', '站长'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='版块说明');
"""

_MEDIA_CAMPUS = """\
INSERT INTO sys_user (username, password, role, nickname, phone, profile_json, super_admin, profile_editable, enabled) VALUES
('admin', 'admin123', 'admin', '媒资主管', '13800000000', '{}', 1, 0, 1),
('subadmin', 'sub123', 'admin', '运营编辑', '13800000001', '{}', 0, 1, 1),
('user', 'user123', 'user', '师生甲', '13800000002',
 '{"realName":"周同学","email":"zhou@demo.edu","gender":"女","identityType":"学生","studentNo":"S20260001","dept":"传媒学院","preferredGenre":"教学片"}',
 0, 1, 1)
ON DUPLICATE KEY UPDATE nickname=VALUES(nickname), phone=VALUES(phone), profile_json=VALUES(profile_json);

INSERT IGNORE INTO category (id, name) VALUES (1, '教学片'), (2, '纪录片'), (3, '活动回放');
INSERT IGNORE INTO media (id, title, author, isbn, category_id, stock, status) VALUES
(1, '实验室安全演示', '教务处 / 主讲甲', 'https://www.w3schools.com/html/mov_bbb.mp4', 1, 1, 'available'),
(2, '校史纪录片', '宣传部', 'https://www.w3schools.com/html/mov_bbb.mp4', 2, 1, 'available'),
(3, '运动会开幕式回放', '体育部', 'https://www.w3schools.com/html/mov_bbb.mp4', 3, 1, 'available'),
(4, '新生入学教育', '学工处', 'https://www.w3schools.com/html/mov_bbb.mp4', 1, 1, 'available'),
(5, '毕业季特辑', '团委', 'https://www.w3schools.com/html/mov_bbb.mp4', 3, 1, 'available');
INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '观影须知', '片源仅供学习演示；请文明观影，勿传播未授权内容。', 'admin', '媒资主管'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='观影须知');
INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '本周上新', '教学片与活动回放已更新，欢迎收藏想看。', 'admin', '媒资主管'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='本周上新');
"""

_MUSIC_CAMPUS = """\
INSERT INTO sys_user (username, password, role, nickname, phone, profile_json, super_admin, profile_editable, enabled) VALUES
('admin', 'admin123', 'admin', '曲库主管', '13800000000', '{}', 1, 0, 1),
('subadmin', 'sub123', 'admin', '运营编辑', '13800000001', '{}', 0, 1, 1),
('user', 'user123', 'user', '师生甲', '13800000002',
 '{"realName":"陈同学","email":"chen@demo.edu","gender":"男","identityType":"学生","studentNo":"S20260011","dept":"艺术学院","preferredGenre":"合唱"}',
 0, 1, 1)
ON DUPLICATE KEY UPDATE nickname=VALUES(nickname), phone=VALUES(phone), profile_json=VALUES(profile_json);

INSERT IGNORE INTO category (id, name) VALUES (1, '合唱'), (2, '器乐'), (3, '校园原创');
INSERT IGNORE INTO track (id, title, author, isbn, category_id, stock, status) VALUES
(1, '校歌合唱版', '校合唱团', 'https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3', 1, 1, 'available'),
(2, '琴房练习曲', '音乐系', 'https://www.soundhelix.com/examples/mp3/SoundHelix-Song-2.mp3', 2, 1, 'available'),
(3, '图书馆角落', '原创社', 'https://www.soundhelix.com/examples/mp3/SoundHelix-Song-3.mp3', 3, 1, 'available'),
(4, '毕业季合唱', '合唱团', 'https://www.soundhelix.com/examples/mp3/SoundHelix-Song-4.mp3', 1, 1, 'available'),
(5, '运动会进行曲', '军乐队', 'https://www.soundhelix.com/examples/mp3/SoundHelix-Song-5.mp3', 2, 1, 'available');
INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '试听须知', '曲源仅供学习演示；请尊重版权，勿传播未授权内容。', 'admin', '曲库主管'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='试听须知');
INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '本周上新', '合唱与校园原创已更新，欢迎收藏喜欢。', 'admin', '曲库主管'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='本周上新');
"""

_BLOG_CAMPUS = """\
INSERT INTO sys_user (username, password, role, nickname, phone, profile_json, super_admin, profile_editable, enabled) VALUES
('admin', 'admin123', 'admin', '主编', '13800000000', '{}', 1, 0, 1),
('subadmin', 'sub123', 'admin', '编辑甲', '13800000001', '{}', 0, 1, 1),
('user', 'user123', 'user', '师生甲', '13800000002',
 '{"realName":"王同学","email":"wang@demo.edu","gender":"女","identityType":"学生","studentNo":"S20260021","dept":"文学院","preferredGenre":"学工"}',
 0, 1, 1)
ON DUPLICATE KEY UPDATE nickname=VALUES(nickname), phone=VALUES(phone), profile_json=VALUES(profile_json);

INSERT IGNORE INTO category (id, name) VALUES (1, '教学'), (2, '学工'), (3, '活动');
INSERT IGNORE INTO article (id, title, author, isbn, category_id, stock, status) VALUES
(1, '本周教学安排说明', '教务处', '<p>本周调课与实验安排见正文。</p>', 1, 1, 'available'),
(2, '资助申报材料清单', '学工处', '<p>国家助学与校内奖学金材料要求。</p>', 2, 1, 'available'),
(3, '校园文化节志愿者招募', '团委', '<p>报名截止与岗位说明。</p>', 3, 1, 'available'),
(4, '实验室开放时间调整', '资产处', '<p>本月机房与实训室开放时段。</p>', 1, 1, 'available'),
(5, '心理健康月活动预告', '学工处', '<p>讲座与团体辅导安排。</p>', 2, 1, 'available');
INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '阅读须知', '文章仅供学习演示；转载请注明出处。内容由主编维护发布。', 'admin', '主编'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='阅读须知');
INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '本周上新', '教学与学工栏目已更新，欢迎收藏订阅。', 'admin', '主编'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='本周上新');
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
    elif domain == "DOM-DATING" and scene == "campus":
        seed = _DATING_CAMPUS
    elif domain == "DOM-HOSPITAL" and scene == "adopt":
        seed = _HOSPITAL_PET
    elif domain == "DOM-FUND" and scene == "enterprise":
        seed = _FUND_ENTERPRISE
    elif domain == "DOM-GRADE" and scene == "enterprise":
        seed = _GRADE_ENTERPRISE
    elif domain == "DOM-INTERN" and scene == "enterprise":
        seed = _INTERN_ENTERPRISE
    elif domain == "DOM-LABSAFE" and scene == "enterprise":
        seed = _LABSAFE_ENTERPRISE
    elif domain == "DOM-PROPERTY" and scene == "campus":
        seed = _PROPERTY_CAMPUS
    elif domain == "DOM-CRM" and scene == "campus":
        seed = _CRM_CAMPUS
    elif domain == "DOM-ASSET" and scene == "campus":
        seed = _ASSET_CAMPUS
    elif domain == "DOM-MEETING" and scene == "enterprise":
        seed = _MEETING_ENTERPRISE
    elif domain == "DOM-FORUM" and scene == "community":
        seed = _FORUM_COMMUNITY
    elif domain == "DOM-MEDIA" and scene == "campus":
        seed = _MEDIA_CAMPUS
    elif domain == "DOM-MUSIC" and scene == "campus":
        seed = _MUSIC_CAMPUS
    elif domain == "DOM-BLOG" and scene == "campus":
        seed = _BLOG_CAMPUS
    if seed is None:
        return sql
    return _replace_user_seed_tail(sql, seed)
