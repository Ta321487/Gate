"""非商城/内容/预约族的具名域场景种子（考勤/失物/活动/CRM/设备等）。"""

from __future__ import annotations

_ATTEND_CAMPUS = """\
INSERT INTO sys_user (username, password, role, nickname, phone, profile_json, super_admin, profile_editable, enabled) VALUES
('admin', 'admin123', 'admin', '学工主管', '13800000000', '{}', 1, 0, 1),
('subadmin', 'sub123', 'admin', '辅导员', '13800000001', '{}', 0, 1, 1),
('user', 'user123', 'user', '学生甲', '13800000002',
 '{"realName":"周明","email":"zhou@demo.edu","gender":"男","identityType":"学生","studentNo":"S2026008","dept":"计算机学院"}',
 0, 1, 1)
ON DUPLICATE KEY UPDATE nickname=VALUES(nickname), phone=VALUES(phone), profile_json=VALUES(profile_json);

INSERT IGNORE INTO category (id, name) VALUES (1, '事假类'), (2, '病假类'), (3, '其它假');
INSERT IGNORE INTO leave_type (id, title, author, isbn, category_id, stock, status) VALUES
(1, '事假', '因私事务离校', '须提前申请；说明起止时间与事由', 1, 1, 'available'),
(2, '病假', '因病休养', '可补交医院证明；急症可先口头报备', 2, 1, 'available'),
(3, '实习离校', '校外实习/见习', '须附实习证明与辅导员意见', 3, 1, 'available'),
(4, '公假', '因公/参赛离校', '填写活动证明与同行人；返校当日销假', 3, 1, 'available'),
(5, '丧假', '直系亲属丧事', '按学工规定天数；可补交证明', 1, 1, 'available');
INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '请假须知', '事假须提前申请；病假可补交证明；销假请在返校当日确认。请假单归属登录账号本人，不得代同学请假。', 'admin', '学工主管'
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
 '{"realName":"刘明","email":"liu@demo.com","gender":"男","receiveAddress":"阳光小区3栋2单元501","contactWechat":"liu_demo","usualPlace":"3栋驿站"}',
 0, 1, 1)
ON DUPLICATE KEY UPDATE nickname=VALUES(nickname), phone=VALUES(phone), profile_json=VALUES(profile_json);

INSERT IGNORE INTO category (id, name) VALUES (1, '普通件'), (2, '生鲜件'), (3, '大件');
INSERT IGNORE INTO parcel (id, title, author, isbn, category_id, stock, status) VALUES
(1, '圆通YT8821001', '阳光小区驿站', '取件码 3182 / A12 柜 / 13800000002', 1, 1, 'available'),
(2, '中通ZT9912002', '阳光小区驿站', '取件码 5521 / 冷藏区 / 13800000002', 2, 1, 'available'),
(3, '顺丰SF1003003', '物业代收点', '取件码 7740 / 大件区 / 13800000099', 3, 1, 'available'),
(4, '韵达YD2204004', '阳光小区驿站', '取件码 1098 / B03 柜 / 13800000002', 1, 1, 'available'),
(5, '极兔JT3305005', '阳光小区驿站', '取件码 6644 / A08 柜 / 13800000099', 1, 1, 'available');
INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '取件须知', '请凭取件码与本人手机号取件；本人件按登录手机号匹配。超时未取将移至逾期架。', 'admin', '驿站主管'
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
INSERT IGNORE INTO claim (id, book_id, username, status, remark) VALUES
(1, 2, 'user', 'pending', '耳机盒特征吻合，请审核认领。');
"""

_LOST_BAGGAGE = """\
INSERT INTO sys_user (username, password, role, nickname, phone, profile_json, super_admin, profile_editable, enabled) VALUES
('admin', 'admin123', 'admin', '行李服务主管', '13800000000', '{}', 1, 0, 1),
('subadmin', 'sub123', 'admin', '行李专员', '13800000001', '{}', 0, 1, 1),
('user', 'user123', 'user', '旅客甲', '13800000002',
 '{"realName":"王芳","email":"wang@demo.com","gender":"女","contactWechat":"wang_demo","usualPlace":"T2到达","orgName":"航班 CA1234"}',
 0, 1, 1)
ON DUPLICATE KEY UPDATE nickname=VALUES(nickname), phone=VALUES(phone), profile_json=VALUES(profile_json);

INSERT IGNORE INTO category (id, name) VALUES (1, '托运行李'), (2, '登机箱'), (3, '随身物品');
INSERT IGNORE INTO lost_item (id, title, author, isbn, category_id, stock, status) VALUES
(1, '黑色24寸拉杆箱', '到达服务台', 'CA1234 / 箱面有红绳', 1, 1, 'available'),
(2, '灰色双肩包', '安检口', '无航班牌 / 内有水杯', 2, 1, 'available'),
(3, '儿童推车折叠件', '行李转盘 B', 'MU5678 / 蓝色绑带', 1, 1, 'available'),
(4, '银色登机箱', '旅客服务中心', 'HO7890 / 箱体有贴纸', 2, 1, 'available'),
(5, '黑色公文包', '值机柜台', '内有文件夹 / 无锁', 3, 1, 'available');
INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '行李认领须知', '认领时请提供有效身份与行李特征；审核通过后到服务台领取。', 'admin', '行李服务主管'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='行李认领须知');
INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '本周公示', '托运行李与登机箱启事已更新，请及时认领。', 'admin', '行李服务主管'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='本周公示');
INSERT IGNORE INTO claim (id, book_id, username, status, remark) VALUES
(1, 1, 'user', 'pending', '箱面红绳与航班号吻合，请审核认领。');
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
INSERT IGNORE INTO claim (id, book_id, username, status, remark) VALUES
(1, 1, 'user', 'pending', '家中可养，申请领养小橘。');
"""

_LOST_DONATE = """\
INSERT INTO sys_user (username, password, role, nickname, phone, profile_json, super_admin, profile_editable, enabled) VALUES
('admin', 'admin123', 'admin', '捐赠站主管', '13800000000', '{}', 1, 0, 1),
('subadmin', 'sub123', 'admin', '认领专员', '13800000001', '{}', 0, 1, 1),
('user', 'user123', 'user', '申请人甲', '13800000002',
 '{"realName":"王芳","email":"wang@demo.com","gender":"女","contactWechat":"wang_demo","claimPurpose":"支教物资","orgName":"志愿队"}',
 0, 1, 1)
ON DUPLICATE KEY UPDATE nickname=VALUES(nickname), phone=VALUES(phone), profile_json=VALUES(profile_json);

INSERT IGNORE INTO category (id, name) VALUES (1, '衣物被褥'), (2, '学习用品'), (3, '生活家电');
INSERT IGNORE INTO lost_item (id, title, author, isbn, category_id, stock, status) VALUES
(1, '冬衣礼包 A01', '捐赠站李华', '成人外套 3 件 / 已消毒', 1, 1, 'available'),
(2, '文具套装 B03', '捐赠站王芳', '笔记本与笔袋 / 适合中小学', 2, 1, 'available'),
(3, '小台灯 C02', '捐赠站张敏', 'LED 台灯 / 配件齐全', 3, 1, 'available'),
(4, '棉被一套 D01', '捐赠站赵强', '单人被芯被套 / 已清洗', 1, 1, 'available'),
(5, '科普读物礼包 E01', '捐赠站陈洁', '少儿读物 5 本', 2, 1, 'available');
INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '认领须知', '请如实填写用途与联系方式；审核通过后按通知到站领取。', 'admin', '捐赠站主管'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='认领须知');
INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '本周物资', '衣物与学习用品名录已更新，欢迎申请认领。', 'admin', '捐赠站主管'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='本周物资');
INSERT IGNORE INTO claim (id, book_id, username, status, remark) VALUES
(1, 2, 'user', 'pending', '用于支教，申请认领文具套装。');
"""

_ACTIVITY_CERT = """\
INSERT INTO sys_user (username, password, role, nickname, phone, profile_json, super_admin, profile_editable, enabled) VALUES
('admin', 'admin123', 'admin', '培训主管', '13800000000', '{}', 1, 0, 1),
('subadmin', 'sub123', 'admin', '报名助理', '13800000001', '{}', 0, 1, 1),
('user', 'user123', 'user', '报考人甲', '13800000002',
 '{"realName":"李同学","email":"li@demo.edu","gender":"男","studentNoOrEmp":"S20260001","dept":"计算机学院","identityType":"学生","orgOrClub":"考证小组"}',
 0, 1, 1)
ON DUPLICATE KEY UPDATE nickname=VALUES(nickname), phone=VALUES(phone), profile_json=VALUES(profile_json);

INSERT IGNORE INTO category (id, name) VALUES
(1, '证书报考'), (2, '培训班'), (3, '四六级');
-- 1 与 4 时段重叠，便于校验时段冲突；截止日放在开课前
INSERT IGNORE INTO activity (id, title, author, isbn, category_id, stock, status, start_at, end_at, apply_deadline_at) VALUES
(1, '大学英语四级报名', '教务处', '主教学楼考场', 3, 80, 'available', '2026-10-11 09:00:00', '2026-10-11 11:30:00', '2026-10-10 23:59:59'),
(2, '计算机二级培训班', '继续教育学院', '实验楼机房', 2, 40, 'available', '2026-10-12 14:00:00', '2026-10-12 17:00:00', '2026-10-11 20:00:00'),
(3, '教师资格证笔试报考', '教师发展中心', '第三教学楼', 1, 60, 'available', '2026-10-15 09:00:00', '2026-10-15 12:00:00', '2026-10-14 18:00:00'),
(4, '英语口语强化班', '外国语学院', '外语楼语音室', 2, 30, 'available', '2026-10-11 14:00:00', '2026-10-11 16:00:00', '2026-10-10 23:59:59'),
(5, '普通话水平测试报名', '教务处', '图书馆报告厅', 1, 50, 'available', '2026-10-19 09:00:00', '2026-10-19 12:00:00', '2026-10-18 18:00:00');
INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '报考须知', '请如实填写报考信息；名额有限。', 'admin', '培训主管'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='报考须知');
INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '本周开放', '四级报名与计算机二级培训班已开放，欢迎报名。', 'admin', '培训主管'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='本周开放');
INSERT IGNORE INTO signup (id, book_id, username, status, remark) VALUES
(1, 3, 'user', 'pending', '希望报考教师资格证笔试。');

UPDATE activity SET checkin_code=CONCAT('ACT', LPAD(id, 3, '0')) WHERE checkin_code='' OR checkin_code IS NULL;
"""

_ACTIVITY_TICKET = """\
INSERT INTO sys_user (username, password, role, nickname, phone, profile_json, super_admin, profile_editable, enabled) VALUES
('admin', 'admin123', 'admin', '票务主管', '13800000000', '{}', 1, 0, 1),
('subadmin', 'sub123', 'admin', '票务助理', '13800000001', '{}', 0, 1, 1),
('user', 'user123', 'user', '观众甲', '13800000002',
 '{"realName":"李同学","email":"li@demo.edu","gender":"男","studentNoOrEmp":"S20260001","dept":"艺术学院","identityType":"学生","orgOrClub":"观众"}',
 0, 1, 1)
ON DUPLICATE KEY UPDATE nickname=VALUES(nickname), phone=VALUES(phone), profile_json=VALUES(profile_json);

INSERT IGNORE INTO category (id, name) VALUES
(1, '景区场次'), (2, '演出场次'), (3, '歌剧院场次');
-- 1 与 4 时段重叠，便于校验时段冲突；截止日放在开课前
INSERT IGNORE INTO activity (id, title, author, isbn, category_id, stock, status, start_at, end_at, apply_deadline_at) VALUES
(1, '古城夜游场次', '文旅中心', '南门售票处 / 须知见公告', 1, 100, 'available', '2026-10-11 19:00:00', '2026-10-11 21:00:00', '2026-10-10 23:59:59'),
(2, '校园音乐会', '团委', '大礼堂', 2, 200, 'available', '2026-10-12 19:30:00', '2026-10-12 21:30:00', '2026-10-11 20:00:00'),
(3, '茶花女精选场', '歌剧院', '一号厅 / 领票须知见公告', 3, 80, 'available', '2026-10-15 19:00:00', '2026-10-15 21:30:00', '2026-10-14 18:00:00'),
(4, '园林日场参观', '文旅中心', '西门检票口', 1, 60, 'available', '2026-10-11 14:00:00', '2026-10-11 17:00:00', '2026-10-10 23:59:59'),
(5, '图兰朵片段专场', '歌剧院', '二号厅', 3, 120, 'available', '2026-10-19 19:00:00', '2026-10-19 21:00:00', '2026-10-18 18:00:00');
INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '领票须知', '请如实填写联系方式；票额有限。', 'admin', '票务主管'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='领票须知');
INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '本周场次', '古城夜游与校园音乐会已开放领票。', 'admin', '票务主管'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='本周场次');
INSERT IGNORE INTO signup (id, book_id, username, status, remark) VALUES
(1, 2, 'user', 'pending', '希望领取校园音乐会票。');

UPDATE activity SET checkin_code=CONCAT('ACT', LPAD(id, 3, '0')) WHERE checkin_code='' OR checkin_code IS NULL;
"""

_ACTIVITY_BLOOD = """\
INSERT INTO sys_user (username, password, role, nickname, phone, profile_json, super_admin, profile_editable, enabled) VALUES
('admin', 'admin123', 'admin', '场次主管', '13800000000', '{}', 1, 0, 1),
('subadmin', 'sub123', 'admin', '场次助理', '13800000001', '{}', 0, 1, 1),
('user', 'user123', 'user', '报名者甲', '13800000002',
 '{"realName":"李同学","email":"li@demo.edu","gender":"男","studentNoOrEmp":"S20260001","dept":"医学院","identityType":"学生","orgOrClub":"红十字会"}',
 0, 1, 1)
ON DUPLICATE KEY UPDATE nickname=VALUES(nickname), phone=VALUES(phone), profile_json=VALUES(profile_json);

INSERT IGNORE INTO category (id, name) VALUES
(1, '献血场次'), (2, '校园开放日'), (3, '其它公益');
-- 1 与 4 时段重叠，便于校验时段冲突；截止日放在开课前
INSERT IGNORE INTO activity (id, title, author, isbn, category_id, stock, status, start_at, end_at, apply_deadline_at) VALUES
(1, '无偿献血进校园', '校红十字会', '体育馆一层 / 请带身份证', 1, 50, 'available', '2026-10-11 09:00:00', '2026-10-11 12:00:00', '2026-10-10 23:59:59'),
(2, '实验室开放日上午场', '实验中心', '实验楼大厅', 2, 40, 'available', '2026-10-12 09:00:00', '2026-10-12 11:30:00', '2026-10-11 20:00:00'),
(3, '无偿献血补报场', '校医院', '校医院采血室', 1, 30, 'available', '2026-10-15 14:00:00', '2026-10-15 17:00:00', '2026-10-14 18:00:00'),
(4, '实验室开放日下午场', '实验中心', '实验楼大厅', 2, 40, 'available', '2026-10-11 14:00:00', '2026-10-11 16:30:00', '2026-10-10 23:59:59'),
(5, '公益健康咨询开放日', '校医院', '校医院一楼', 3, 60, 'available', '2026-10-19 09:00:00', '2026-10-19 12:00:00', '2026-10-18 18:00:00');
INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '报名须知', '请如实填写资料；名额有限。', 'admin', '场次主管'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='报名须知');
INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '本周场次', '无偿献血与实验室开放日已开放报名。', 'admin', '场次主管'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='本周场次');
INSERT IGNORE INTO signup (id, book_id, username, status, remark) VALUES
(1, 2, 'user', 'pending', '希望报名实验室开放日上午场。');

UPDATE activity SET checkin_code=CONCAT('ACT', LPAD(id, 3, '0')) WHERE checkin_code='' OR checkin_code IS NULL;
"""

_ACTIVITY_CAMP = """\
INSERT INTO sys_user (username, password, role, nickname, phone, profile_json, super_admin, profile_editable, enabled) VALUES
('admin', 'admin123', 'admin', '项目主管', '13800000000', '{}', 1, 0, 1),
('subadmin', 'sub123', 'admin', '项目助理', '13800000001', '{}', 0, 1, 1),
('user', 'user123', 'user', '报名者甲', '13800000002',
 '{"realName":"李同学","email":"li@demo.edu","gender":"男","studentNoOrEmp":"S20260001","dept":"教育学院","identityType":"学生","orgOrClub":"研学社"}',
 0, 1, 1)
ON DUPLICATE KEY UPDATE nickname=VALUES(nickname), phone=VALUES(phone), profile_json=VALUES(profile_json);

INSERT IGNORE INTO category (id, name) VALUES
(1, '研学营'), (2, '夏令营'), (3, '赛事');
-- 1 与 4 时段重叠，便于校验时段冲突；截止日放在开课前
INSERT IGNORE INTO activity (id, title, author, isbn, category_id, stock, status, start_at, end_at, apply_deadline_at) VALUES
(1, '红色基地研学两日营', '团委', '南门集合 / 含保险说明', 1, 40, 'available', '2026-10-11 08:00:00', '2026-10-12 17:00:00', '2026-10-09 23:59:59'),
(2, '科创夏令营一周营', '创新创业学院', '创客中心报到', 2, 35, 'available', '2026-10-12 09:00:00', '2026-10-18 17:00:00', '2026-10-10 20:00:00'),
(3, '程序设计校内赛', '计算机学院', '创新楼机房', 3, 80, 'available', '2026-10-15 09:00:00', '2026-10-15 17:00:00', '2026-10-14 18:00:00'),
(4, '博物馆研学半日营', '教务处', '东门集合', 1, 45, 'available', '2026-10-11 13:00:00', '2026-10-11 17:00:00', '2026-10-09 23:59:59'),
(5, '创新创业大赛报名', '团委', '大礼堂答辩', 3, 60, 'available', '2026-10-19 09:00:00', '2026-10-19 17:00:00', '2026-10-18 18:00:00');
INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '报名须知', '请如实填写资料；名额有限；到场请向主办方索取签到码。', 'admin', '项目主管'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='报名须知');
INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '本周项目', '红色基地研学与程序设计校内赛已开放报名。', 'admin', '项目主管'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='本周项目');
INSERT IGNORE INTO signup (id, book_id, username, status, remark) VALUES
(1, 3, 'user', 'pending', '希望报名程序设计校内赛。');

UPDATE activity SET checkin_code=CONCAT('ACT', LPAD(id, 3, '0')) WHERE checkin_code='' OR checkin_code IS NULL;
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

INSERT IGNORE INTO ticket (id, username, title, location, type_id, room_id, status, priority, contact_phone, remark) VALUES
(1, 'user', 'A座1208无法连接内网', '办公区 1208', 1, 2, 'pending', '普通', '13800000002', '网线已插好，指示灯不亮。'),
(2, 'user', '打印机卡纸', '办公区 1201', 3, 1, 'approved', '普通', '13800000002', '已派工处理中。'),
(3, 'user', '终端蓝屏重启', '办公区 1208', 2, 2, 'returned', '普通', '13800000002', '已重装驱动办结。');

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
SELECT '投递须知', '请如实填写经历；初筛通过后由 HR 预约面试。', 'admin', '招聘主管'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='投递须知');
INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '本周岗位', '技术岗与职能岗已更新，请及时投递。', 'admin', '招聘主管'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='本周岗位');
"""

_RECRUIT_WITKEY = """\
INSERT INTO sys_user (username, password, role, nickname, phone, profile_json, super_admin, profile_editable, enabled) VALUES
('admin', 'admin123', 'admin', '任务主管', '13800000000', '{}', 1, 0, 1),
('subadmin', 'sub123', 'admin', '审核专员', '13800000001', '{}', 0, 1, 1),
('user', 'user123', 'user', '接单者甲', '13800000002',
 '{"realName":"林晓","email":"lin@demo.com","gender":"女","identityType":"自由职业","dept":"平面设计","jobTitle":"接单","workYears":"2年"}',
 0, 1, 1)
ON DUPLICATE KEY UPDATE nickname=VALUES(nickname), phone=VALUES(phone), profile_json=VALUES(profile_json);

INSERT IGNORE INTO category (id, name) VALUES (1, '设计类'), (2, '开发类'), (3, '文案类');
INSERT IGNORE INTO job_post (id, title, author, isbn, category_id, stock, status) VALUES
(1, 'Logo 初稿设计', '品牌方甲', '报酬说明 / 3 日内交付', 1, 3, 'available'),
(2, '落地页切图', '电商工作室', '报酬说明 / PSD 交付', 1, 2, 'available'),
(3, '小程序页面开发', '创业团队', '报酬说明 / Vue 页面', 2, 2, 'available'),
(4, '活动文案撰写', '运营组', '报酬说明 / 800 字内', 3, 5, 'available'),
(5, '接口联调协助', '技术外包', '报酬说明 / 文档对接', 2, 1, 'available');
INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '接单须知', '请如实填写接单说明；平台审核通过后按交付要求沟通。', 'admin', '任务主管'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='接单须知');
INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '本周任务', '设计类与开发类任务已更新，可投递接单。', 'admin', '任务主管'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='本周任务');
"""

_PROCURE_JOURNAL = """\
INSERT INTO sys_user (username, password, role, nickname, phone, profile_json, super_admin, profile_editable, enabled) VALUES
('admin', 'admin123', 'admin', '期刊主管', '13800000000', '{}', 1, 0, 1),
('subadmin', 'sub123', 'admin', '遴选专员', '13800000001', '{}', 0, 1, 1),
('user', 'user123', 'user', '荐购人甲', '13800000002',
 '{"realName":"周研","email":"zhou@demo.edu","gender":"女","employeeNo":"L2026001","dept":"图书馆资源建设部"}',
 0, 1, 1)
ON DUPLICATE KEY UPDATE nickname=VALUES(nickname), phone=VALUES(phone), profile_json=VALUES(profile_json);

INSERT IGNORE INTO category (id, name) VALUES (1, '理工外刊'), (2, '社科外刊'), (3, '综合索引');
INSERT IGNORE INTO procure_item (id, title, author, isbn, category_id, stock, status) VALUES
(1, 'Nature Communications', '自然科学', 'ISSN 2041-1723 / 英', 1, 1, 'available'),
(2, 'IEEE Transactions on Software Engineering', '计算机', 'ISSN 0098-5589 / 英', 1, 1, 'available'),
(3, 'The Lancet', '医学', 'ISSN 0140-6736 / 英', 1, 1, 'available'),
(4, 'American Economic Review', '经济学', 'ISSN 0002-8282 / 英', 2, 1, 'available'),
(5, 'Web of Science 核心合集说明', '综索', '数据库入口说明 / 非算法匹配', 3, 1, 'available');
INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '期刊遴选须知', '请如实填写荐购理由；审核通过后纳入馆藏计划。', 'admin', '期刊主管'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='期刊遴选须知');
INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '本周开放', '理工外刊与社科外刊品目已更新，可提交遴选。', 'admin', '期刊主管'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='本周开放');
INSERT IGNORE INTO procure_apply (id, book_id, username, status, remark) VALUES
(1, 2, 'user', 'pending', '软件工程学科教学科研需要，建议续订。');
"""

_ACTIVITY_SECURITY = """\
INSERT INTO sys_user (username, password, role, nickname, phone, profile_json, super_admin, profile_editable, enabled) VALUES
('admin', 'admin123', 'admin', '培训主管', '13800000000', '{}', 1, 0, 1),
('subadmin', 'sub123', 'admin', '培训助理', '13800000001', '{}', 0, 1, 1),
('user', 'user123', 'user', '学员甲', '13800000002',
 '{"realName":"李同学","email":"li@demo.edu","gender":"男","studentNoOrEmp":"S20260001","dept":"保卫处协同","identityType":"学生","orgOrClub":"志愿巡防队"}',
 0, 1, 1)
ON DUPLICATE KEY UPDATE nickname=VALUES(nickname), phone=VALUES(phone), profile_json=VALUES(profile_json);

INSERT IGNORE INTO category (id, name) VALUES
(1, '防暴恐培训'), (2, '应急疏散'), (3, '安全常识');
INSERT IGNORE INTO activity (id, title, author, isbn, category_id, stock, status, start_at, end_at, apply_deadline_at) VALUES
(1, '校园防暴恐应急处置培训', '保卫处', '大礼堂 / 须知见公告', 1, 120, 'available', '2026-10-11 09:00:00', '2026-10-11 11:30:00', '2026-10-10 23:59:59'),
(2, '宿舍楼疏散演练报名', '学工处', '各宿舍楼集合点', 2, 200, 'available', '2026-10-12 15:00:00', '2026-10-12 17:00:00', '2026-10-11 20:00:00'),
(3, '反恐安全常识专题课', '马克思主义学院', '教学楼 A301', 3, 80, 'available', '2026-10-15 14:00:00', '2026-10-15 16:00:00', '2026-10-14 18:00:00'),
(4, '实验室危险处置培训', '实验室与设备处', '实验楼报告厅', 3, 60, 'available', '2026-10-16 09:00:00', '2026-10-16 11:00:00', '2026-10-15 18:00:00'),
(5, '安保志愿者岗前培训', '保卫处', '保卫楼会议室', 1, 40, 'available', '2026-10-18 09:00:00', '2026-10-18 12:00:00', '2026-10-17 18:00:00');
INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '培训须知', '请按时到场；名额有限；结业考核以当期公告为准。', 'admin', '培训主管'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='培训须知');
INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '本周开放', '防暴恐应急处置与疏散演练已开放报名。', 'admin', '培训主管'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='本周开放');
INSERT IGNORE INTO signup (id, book_id, username, status, remark) VALUES
(1, 1, 'user', 'pending', '希望参加校园防暴恐应急处置培训。');

UPDATE activity SET checkin_code=CONCAT('ACT', LPAD(id, 3, '0')) WHERE checkin_code='' OR checkin_code IS NULL;
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
INSERT IGNORE INTO reservation (id, slot_id, username, status, remark, patient_name, visit_type, symptom_note) VALUES
(1, 1, 'patient', 'confirmed', '', '钱女士', '初诊', '豆豆皮肤过敏复诊'),
(2, 2, 'patient', 'pending', '', '钱女士', '复诊', '待确认'),
(3, 5, 'patient', 'completed', '', '钱女士', '复诊', '已就诊');
UPDATE resource_slot SET booked = 1 WHERE id IN (1, 2);
INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '挂号须知', '号源有限；请填写宠物昵称与就诊人；按时到诊；就诊完成后由前台办结。', 'admin', '宠物医院主管'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='挂号须知');
"""

_HOSPITAL_VACCINE = """\
INSERT INTO sys_user (username, password, role, nickname, phone, profile_json, super_admin, profile_editable, enabled) VALUES
('admin', 'admin123', 'admin', '接种点主管', '13800000000', '{}', 1, 0, 1),
('subadmin', 'sub123', 'admin', '预约管理员', '13800000001', '{}', 0, 1, 1),
('patient', 'patient123', 'patient', '接种人甲', '13800000002',
 '{"realName":"钱女士","email":"qian@demo.com","gender":"女","patientNo":"V20260001"}',
 0, 1, 1)
ON DUPLICATE KEY UPDATE nickname=VALUES(nickname), phone=VALUES(phone), profile_json=VALUES(profile_json);

INSERT IGNORE INTO category (id, name) VALUES (1, 'HPV'), (2, '流感'), (3, '狂犬病');
INSERT IGNORE INTO doctor (id, title, author, isbn, category_id, stock, status) VALUES
(1, 'HPV九价接种', '0', '三针疗程 / 预约到点', 1, 1, 'available'),
(2, '季节性流感疫苗', '0', '单针 / 成人', 2, 1, 'available'),
(3, '狂犬病暴露后免疫', '0', '按医嘱针次', 3, 1, 'available');
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
INSERT IGNORE INTO reservation (id, slot_id, username, status, remark, patient_name, visit_type, symptom_note) VALUES
(1, 1, 'patient', 'confirmed', '', '钱女士', '首针', 'HPV九价第一针'),
(2, 2, 'patient', 'pending', '', '钱女士', '第二针', '待确认'),
(3, 5, 'patient', 'completed', '', '钱女士', '流感', '已接种');
UPDATE resource_slot SET booked = 1 WHERE id IN (1, 2);
INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '预约须知', '请按时到点接种；取消请提前释放号源。', 'admin', '接种点主管'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='预约须知' OR title='挂号须知');
"""

_SALON_FITNESS = """\
INSERT INTO sys_user (username, password, role, nickname, phone, profile_json, super_admin, profile_editable, enabled) VALUES
('admin', 'admin123', 'admin', '场馆主管', '13800000000', '{}', 1, 0, 1),
('subadmin', 'sub123', 'admin', '前台', '13800000001', '{}', 0, 1, 1),
('user', 'user123', 'user', '会员甲', '13800000002',
 '{"realName":"周先生","email":"zhou@demo.com","gender":"男"}',
 0, 1, 1)
ON DUPLICATE KEY UPDATE nickname=VALUES(nickname), phone=VALUES(phone), profile_json=VALUES(profile_json);

INSERT IGNORE INTO category (id, name) VALUES (1, '私教'), (2, '团课');
INSERT IGNORE INTO service (id, title, author, isbn, category_id, stock, status) VALUES
(1, '力量私教体验', '128.00', '约60分钟', 1, 1, 'available'),
(2, '减脂私教课', '168.00', '约60分钟', 1, 1, 'available'),
(3, '瑜伽团课', '49.00', '约45分钟', 2, 1, 'available');
INSERT IGNORE INTO resource_slot (id, item_id, start_at, end_at, capacity, booked) VALUES
(1, 1, '2026-09-20 09:00:00', '2026-09-20 10:00:00', 2, 0),
(2, 1, '2026-09-20 10:00:00', '2026-09-20 11:00:00', 2, 0),
(3, 1, '2026-09-20 14:00:00', '2026-09-20 15:00:00', 2, 0),
(4, 1, '2026-09-20 15:00:00', '2026-09-20 16:00:00', 2, 0),
(5, 2, '2026-09-20 09:00:00', '2026-09-20 10:00:00', 2, 0),
(6, 2, '2026-09-20 10:00:00', '2026-09-20 11:00:00', 2, 0),
(7, 2, '2026-09-20 14:00:00', '2026-09-20 15:00:00', 2, 0),
(8, 2, '2026-09-20 15:00:00', '2026-09-20 16:00:00', 2, 0),
(9, 3, '2026-09-20 09:00:00', '2026-09-20 10:00:00', 8, 0),
(10, 3, '2026-09-20 10:00:00', '2026-09-20 11:00:00', 8, 0),
(11, 3, '2026-09-20 14:00:00', '2026-09-20 15:00:00', 8, 0),
(12, 3, '2026-09-20 15:00:00', '2026-09-20 16:00:00', 8, 0);
INSERT IGNORE INTO reservation (id, slot_id, username, status, remark, preferred_stylist) VALUES
(1, 1, 'user', 'confirmed', '', '力量教练甲'),
(2, 2, 'user', 'pending', '', '力量教练甲'),
(3, 9, 'user', 'completed', '', '瑜伽教练');
UPDATE resource_slot SET booked = 1 WHERE id IN (1, 2);
INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '健身预约', '请选择课程与时段到馆；迟到可能需改约。', 'admin', '场馆主管'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='健身预约' OR title='服务预约');
"""

_SALON_PHOTO = """\
INSERT INTO sys_user (username, password, role, nickname, phone, profile_json, super_admin, profile_editable, enabled) VALUES
('admin', 'admin123', 'admin', '门店主管', '13800000000', '{}', 1, 0, 1),
('subadmin', 'sub123', 'admin', '前台', '13800000001', '{}', 0, 1, 1),
('user', 'user123', 'user', '预约人甲', '13800000002',
 '{"realName":"周女士","email":"zhou@demo.com","gender":"女"}',
 0, 1, 1)
ON DUPLICATE KEY UPDATE nickname=VALUES(nickname), phone=VALUES(phone), profile_json=VALUES(profile_json);

INSERT IGNORE INTO category (id, name) VALUES (1, '人像');
INSERT IGNORE INTO service (id, title, author, isbn, category_id, stock, status) VALUES
(1, '林可', '0', '人像', 1, 1, 'available'),
(2, '周宁', '0', '人像', 1, 1, 'available');
INSERT IGNORE INTO resource_slot (id, item_id, start_at, end_at, capacity, booked) VALUES
(1, 1, '2026-09-21 10:00:00', '2026-09-21 11:00:00', 1, 0),
(2, 1, '2026-09-21 14:00:00', '2026-09-21 15:00:00', 1, 0),
(3, 2, '2026-09-21 10:00:00', '2026-09-21 11:00:00', 1, 0),
(4, 2, '2026-09-21 14:00:00', '2026-09-21 15:00:00', 1, 0);
INSERT IGNORE INTO reservation (id, slot_id, username, status, remark) VALUES
(1, 1, 'user', 'confirmed', ''),
(2, 3, 'user', 'pending', ''),
(3, 2, 'user', 'completed', '');
UPDATE resource_slot SET booked = 1 WHERE id IN (1, 3);
INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '约拍预约', '请选择摄影师、套餐和时段。', 'admin', '门店主管'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='约拍预约' OR title='服务预约');
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
SELECT '成绩须知', '成绩更正与补考申请由培训专员审核。', 'admin', '培训主管'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='成绩须知');
INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '补考安排', '补考名单以培训公告为准，请按时提交申请。', 'admin', '培训主管'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='补考安排');
"""

_INTERN_ENTERPRISE = """\
INSERT INTO sys_user (username, password, role, nickname, phone, profile_json, super_admin, profile_editable, enabled) VALUES
('admin', 'admin123', 'admin', '实习主管', '13800000000', '{}', 1, 0, 1),
('subadmin', 'sub123', 'admin', '企业导师', '13800000001', '{}', 0, 1, 1),
('user', 'user123', 'user', '实习生甲', '13800000002',
 '{"realName":"小陈","email":"chen@demo.com","gender":"男","identityType":"实习生","employeeNo":"I2026001","dept":"研发中心","internOrg":"研发中心","internPost":"后端开发实习"}',
 0, 1, 1)
ON DUPLICATE KEY UPDATE nickname=VALUES(nickname), phone=VALUES(phone), profile_json=VALUES(profile_json);

INSERT IGNORE INTO category (id, name) VALUES (1, '开发实习'), (2, '运维实习'), (3, '综合实习');
-- 岗 1=演示关联岗；其余示范目录默认待上岗
INSERT IGNORE INTO intern_post (id, title, author, isbn, category_id, stock, status, stage) VALUES
(1, '后端开发实习', '王工', '研发中心 / Java', 1, 1, 'available', '实习中'),
(2, '运维实习', '李工', '基础架构 / 运维', 2, 1, 'available', '待上岗'),
(3, '行政综合实习', '赵主管', '综合办 / 文员', 3, 1, 'available', '待上岗'),
(4, '测试实习', '周工', '质量部 / 测试', 1, 1, 'available', '待上岗'),
(5, '数据分析实习', '陈老师', '数据组 / 分析', 3, 1, 'available', '待上岗');
INSERT IGNORE INTO week_report (id, book_id, username, status, remark, contact_channel) VALUES
(1, 1, 'user', 'pending', '第1周：熟悉部门规范与代码库，完成环境搭建。', '在线填写');
INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '周报须知',
  '每周日前提交周报；企业导师审阅后方可计入实习考勤。岗位列表为示范目录，「实习中」仅标关联岗。',
  'admin', '实习主管'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='周报须知');
INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '鉴定提醒', '实习结束前完成鉴定材料；可在「鉴定签署」上传签章图并勾选同意。', 'admin', '实习主管'
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
INSERT IGNORE INTO ticket_type (id, name, sort_no) VALUES
(1, '水电', 1), (2, '公共设施', 2), (3, '门禁', 3), (4, '投诉建议', 4);

INSERT IGNORE INTO ticket (id, username, title, location, type_id, room_id, status, priority, contact_phone, remark) VALUES
(1, 'user', '学生公寓3号楼405灯不亮', '学生公寓3号楼 405', 1, 1, 'pending', '普通', '13800000002', '卫生间灯具不亮，已换保险丝无效。'),
(2, 'user', '406水龙头漏水', '学生公寓3号楼 406', 1, 2, 'approved', '普通', '13800000002', '维修中。'),
(3, 'user', '教学楼A门禁刷卡失败', '教学楼A 201', 3, 3, 'returned', '普通', '13800000002', '已更换读卡器。');

INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '报修须知', '请填写公寓楼栋房号与故障描述，物业将尽快受理。投诉建议请选对应类型。', 'admin', '物业主管'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='报修须知');
"""

_CRM_CAMPUS = """\
INSERT INTO sys_user (username, password, role, nickname, phone, profile_json, super_admin, profile_editable, enabled) VALUES
('admin', 'admin123', 'admin', '创业导师', '13800000000', '{}', 1, 0, 1),
('user', 'user123', 'user', '团队成员甲', '13800000002',
 '{"realName":"周明","email":"zhou@demo.edu","gender":"男","identityType":"学生","studentNo":"S2026008","dept":"计算机学院创业团队"}',
 0, 1, 1)
ON DUPLICATE KEY UPDATE nickname=VALUES(nickname), phone=VALUES(phone), profile_json=VALUES(profile_json);

INSERT IGNORE INTO category (id, name) VALUES (1, '重点客户'), (2, '普通客户'), (3, '潜在线索');
INSERT IGNORE INTO customer (id, title, author, isbn, category_id, stock, status, owner_username) VALUES
(1, '校友企业·星河科技', '李总', '13811110001 / 意向校企合作', 1, 1, 'available', 'user'),
(2, '青禾教育培训', '王老师', '13922220002 / 咨询联合培养', 2, 1, 'available', ''),
(3, '双创周展会线索', '张女士', '13733330003 / 展会名片', 3, 1, 'available', ''),
(4, '海川物流校招对接', '赵经理', '13644440004 / 实习岗位跟进', 1, 1, 'available', ''),
(5, '邻里便利店连锁', '陈店长', '13555550005 / 创业实践点', 2, 1, 'available', '');
INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '跟进须知', '请如实登记联系结果；跟进提交后即时入档，办结后可在记录中查阅。', 'admin', '创业导师'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='跟进须知');
INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '本周重点', '校友企业续约与双创展会线索请于周五前完成跟进登记。', 'admin', '创业导师'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='本周重点');
"""

_CRM_LEGAL = """\
INSERT INTO sys_user (username, password, role, nickname, phone, profile_json, super_admin, profile_editable, enabled) VALUES
('admin', 'admin123', 'admin', '律所主管', '13800000000', '{}', 1, 0, 1),
('user', 'user123', 'user', '承办人甲', '13800000002',
 '{"realName":"周律师","email":"zhou@demo.com","gender":"男","identityType":"其他","orgName":"城区法律援助中心","jobTitle":"律师","dept":"民事部","region":"城区"}',
 0, 1, 1)
ON DUPLICATE KEY UPDATE nickname=VALUES(nickname), phone=VALUES(phone), profile_json=VALUES(profile_json);

INSERT IGNORE INTO category (id, name) VALUES (1, '民事'), (2, '劳动'), (3, '援助');
INSERT IGNORE INTO customer (id, title, author, isbn, category_id, stock, status, owner_username) VALUES
(1, '张某劳动争议援助', '张某', '拖欠工资 / 调解中', 2, 1, 'available', 'user'),
(2, '李某离婚咨询', '李某', '财产分割 / 接待', 1, 1, 'available', ''),
(3, '社区法律体检', '居委会', '普法咨询 / 结案', 3, 1, 'available', ''),
(4, '王某合同纠纷', '王某', '买卖合同 / 办理中', 1, 1, 'available', ''),
(5, '赵某工伤认定', '赵某', '工伤援助 / 立案', 2, 1, 'available', '');
INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '办案须知', '请如实登记会见与办理进展；跟进提交后即时入档。', 'admin', '律所主管'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='办案须知');
INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '本周重点', '劳动争议与援助案件请于周五前完成跟进登记。', 'admin', '律所主管'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='本周重点');
"""

_CRM_HOMEVISIT = """\
INSERT INTO sys_user (username, password, role, nickname, phone, profile_json, super_admin, profile_editable, enabled) VALUES
('admin', 'admin123', 'admin', '学工主管', '13800000000', '{}', 1, 0, 1),
('user', 'user123', 'user', '学工甲', '13800000002',
 '{"realName":"周明","email":"zhou@demo.edu","gender":"男","identityType":"教职工","employeeNo":"T2026008","dept":"计算机学院","jobTitle":"辅导员"}',
 0, 1, 1)
ON DUPLICATE KEY UPDATE nickname=VALUES(nickname), phone=VALUES(phone), profile_json=VALUES(profile_json);

INSERT IGNORE INTO category (id, name) VALUES (1, '学业关注'), (2, '心理关注'), (3, '家庭联系');
INSERT IGNORE INTO customer (id, title, author, isbn, category_id, stock, status, owner_username) VALUES
(1, '王同学', '计科2201 / 家长王女士', '学业预警 / 待家访', 1, 1, 'available', 'user'),
(2, '李同学', '软工2202 / 家长李先生', '谈心谈话 / 需回访', 2, 1, 'available', ''),
(3, '张同学', '网安2203 / 宿舍长', '违纪回访 / 已闭环', 1, 1, 'available', ''),
(4, '赵同学', '计科2201 / 家长赵女士', '家庭变故 / 已家访', 3, 1, 'available', ''),
(5, '陈同学', '软工2202 / 班主任', '适应性谈话 / 待家访', 2, 1, 'available', '');
INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '家访须知', '请如实登记家访或谈心内容；记录提交后即时入档。', 'admin', '学工主管'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='家访须知');
INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '本周重点', '学业预警学生家访请于周五前完成记录。', 'admin', '学工主管'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='本周重点');
"""

_CRM_COOP = """\
INSERT INTO sys_user (username, password, role, nickname, phone, profile_json, super_admin, profile_editable, enabled) VALUES
('admin', 'admin123', 'admin', '合作主管', '13800000000', '{}', 1, 0, 1),
('user', 'user123', 'user', '联络员甲', '13800000002',
 '{"realName":"周明","email":"zhou@demo.edu","gender":"男","identityType":"教职工","employeeNo":"T2026008","dept":"就业指导中心","jobTitle":"联络员"}',
 0, 1, 1)
ON DUPLICATE KEY UPDATE nickname=VALUES(nickname), phone=VALUES(phone), profile_json=VALUES(profile_json);

INSERT IGNORE INTO category (id, name) VALUES (1, '战略合作'), (2, '实习基地'), (3, '意向接触');
INSERT IGNORE INTO customer (id, title, author, isbn, category_id, stock, status, owner_username) VALUES
(1, '星河科技股份', '李总', '联合实验室 / 履约', 1, 1, 'available', 'user'),
(2, '青禾教育集团', '王主任', '实习基地 / 签约', 2, 1, 'available', ''),
(3, '海川物流', '赵经理', '校招对接 / 意向', 2, 1, 'available', ''),
(4, '邻里便利连锁', '陈店长', '创业实践点 / 接触', 3, 1, 'available', ''),
(5, '云帆软件', '刘经理', '产学研课题 / 履约', 1, 1, 'available', '');
INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '合作须知', '请如实登记对接进展；跟进提交后即时入档。', 'admin', '合作主管'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='合作须知');
INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '本周重点', '实习基地续约与战略合作请于周五前完成跟进。', 'admin', '合作主管'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='本周重点');
"""

_LIBRARY_ARCHIVE = """\
INSERT INTO sys_user (username, password, role, nickname, phone, profile_json, super_admin, profile_editable, enabled) VALUES
('admin', 'admin123', 'admin', '档案馆长', '13800000000', '{}', 1, 0, 1),
('subadmin', 'sub123', 'admin', '档案员', '13800000001', '{}', 0, 1, 1),
('reader', 'reader123', 'reader', '查阅人甲', '13800000002',
 '{"realName":"赵查阅","email":"zhao@demo.edu","gender":"女","cardNo":"A20230088","readerType":"教职工","dept":"教务处","major":"","enrollYear":"2020"}',
 0, 1, 1)
ON DUPLICATE KEY UPDATE nickname=VALUES(nickname), phone=VALUES(phone), profile_json=VALUES(profile_json);

INSERT IGNORE INTO category (id, name) VALUES
(1, '学籍档案'), (2, '文书档案'), (3, '科研档案'), (4, '人事档案'), (5, '其他');
INSERT IGNORE INTO book (id, title, author, isbn, category_id, stock, status) VALUES
(1, '2023 级计算机学院学籍卷宗', '教务处', 'ARCH-XJ-2023-001', 1, 1, 'available'),
(2, '党委会纪要 2024 年第 3 期', '党委办', 'ARCH-WS-2024-003', 2, 1, 'available'),
(3, '重点实验室建设验收材料', '科技处', 'ARCH-KY-2022-018', 3, 1, 'available'),
(4, '教职工履历归档（样例）', '人事处', 'ARCH-RS-2021-007', 4, 1, 'available'),
(5, '本科教学评估支撑材料', '评建办', 'ARCH-WS-2020-011', 2, 1, 'available');
INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '开放查阅通知', '工作日可申请卷宗借阅，请按时归还。', 'admin', '档案馆长'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='开放查阅通知');
INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '借阅须知', '卷宗仅限馆内或按规定外借；逾期请及时归还。', 'admin', '档案馆长'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='借阅须知');
"""

_LIBRARY_DRIFT = """\
INSERT INTO sys_user (username, password, role, nickname, phone, profile_json, super_admin, profile_editable, enabled) VALUES
('admin', 'admin123', 'admin', '漂流站长', '13800000000', '{}', 1, 0, 1),
('subadmin', 'sub123', 'admin', '站务员', '13800000001', '{}', 0, 1, 1),
('reader', 'reader123', 'reader', '读者甲', '13800000002',
 '{"realName":"赵读者","email":"zhao@demo.edu","gender":"女","cardNo":"R20230088","readerType":"本科生","dept":"文学院","major":"汉语言文学","enrollYear":"2023"}',
 0, 1, 1)
ON DUPLICATE KEY UPDATE nickname=VALUES(nickname), phone=VALUES(phone), profile_json=VALUES(profile_json);

INSERT IGNORE INTO category (id, name) VALUES
(1, '文学'), (2, '社科'), (3, '科普'), (4, '教材'), (5, '其他');
INSERT IGNORE INTO book (id, title, author, isbn, category_id, stock, status) VALUES
(1, '漂流·平凡的世界', '路遥', 'DRIFT-001 / 一号楼书架', 1, 1, 'available'),
(2, '漂流·三体', '刘慈欣', 'DRIFT-002 / 图书馆大厅', 3, 1, 'available'),
(3, '漂流·围城', '钱钟书', 'DRIFT-003 / 二号楼', 1, 1, 'available'),
(4, '漂流·高等数学辅导', '同济', 'DRIFT-004 / 教学楼', 4, 1, 'available'),
(5, '漂流·乡土中国', '费孝通', 'DRIFT-005 / 三号楼', 2, 1, 'available');
INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '漂流开放通知', '欢迎取阅漂流图书并提交借阅登记。', 'admin', '漂流站长'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='漂流开放通知');
INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '漂流须知', '读完请按时归还，方便下一位同学继续漂流。', 'admin', '漂流站长'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='漂流须知');
"""

_EQUIP_LIGHT = """\
INSERT INTO sys_user (username, password, role, nickname, phone, profile_json, super_admin, profile_editable, enabled) VALUES
('admin', 'admin123', 'admin', '后勤主管', '13800000000', '{}', 1, 0, 1),
('subadmin', 'sub123', 'admin', '物资管理员', '13800000001', '{}', 0, 1, 1),
('user', 'user123', 'user', '借用人甲', '13800000002',
 '{"realName":"李同学","email":"li@demo.edu","gender":"男","studentNo":"S20230001","dept":"机电工程学院","identityType":"学生","labOrOffice":"一号楼大厅"}',
 0, 1, 1)
ON DUPLICATE KEY UPDATE nickname=VALUES(nickname), phone=VALUES(phone), profile_json=VALUES(profile_json);

INSERT IGNORE INTO category (id, name) VALUES
(1, '雨伞'), (2, '充电宝'), (3, '门禁卡'), (4, '钥匙'), (5, '其他');
INSERT IGNORE INTO equip (id, title, author, isbn, category_id, stock, status) VALUES
(1, '共享雨伞', '学生会物资组', 'UMBRELLA-01', 1, 20, 'available'),
(2, '共享充电宝', '后勤中心', 'POWERBANK-02', 2, 15, 'available'),
(3, '临时门禁卡', '保卫处', 'ACCESS-03', 3, 10, 'available'),
(4, '教室钥匙', '教务处', 'KEY-ROOM-04', 4, 8, 'available'),
(5, '储物柜钥匙', '后勤中心', 'KEY-LOCKER-05', 4, 12, 'available');
INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '租借须知', '请按需申请、按时归还；逾期将登记催还。', 'admin', '后勤主管'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='租借须知');
INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '开放时间', '工作日 8:30–17:30 办理借用与归还。', 'admin', '后勤主管'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='开放时间');
"""

_EQUIP_COSTUME = """\
INSERT INTO sys_user (username, password, role, nickname, phone, profile_json, super_admin, profile_editable, enabled) VALUES
('admin', 'admin123', 'admin', '艺术团主管', '13800000000', '{}', 1, 0, 1),
('subadmin', 'sub123', 'admin', '道具管理员', '13800000001', '{}', 0, 1, 1),
('user', 'user123', 'user', '借用人甲', '13800000002',
 '{"realName":"李同学","email":"li@demo.edu","gender":"女","studentNo":"S20230001","dept":"艺术学院","identityType":"学生","labOrOffice":"艺术楼排练厅"}',
 0, 1, 1)
ON DUPLICATE KEY UPDATE nickname=VALUES(nickname), phone=VALUES(phone), profile_json=VALUES(profile_json);

INSERT IGNORE INTO category (id, name) VALUES
(1, '演出服装'), (2, '舞台道具'), (3, '音响灯光'), (4, '化妆用品'), (5, '其他');
INSERT IGNORE INTO equip (id, title, author, isbn, category_id, stock, status) VALUES
(1, '古装戏服套装', '话剧社', 'COSTUME-01', 1, 6, 'available'),
(2, '晚会礼服', '艺术团', 'COSTUME-02', 1, 4, 'available'),
(3, '道具刀剑组', '舞美组', 'PROP-SWORD-03', 2, 3, 'available'),
(4, '无线麦套装', '艺术团', 'PROP-AUDIO-04', 3, 2, 'available'),
(5, '追光灯', '舞美组', 'PROP-LIGHT-05', 3, 2, 'available');
INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '租借须知', '请爱护服装道具、按时归还；损坏须登记说明。', 'admin', '艺术团主管'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='租借须知');
INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '排练档期', '汇演前一周集中办理领用与归还，详见公告。', 'admin', '艺术团主管'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='排练档期');
"""


def _equip_kind_seed(
    *,
    admin: str,
    sub: str,
    dept: str,
    place: str,
    gender: str,
    cats: tuple[str, ...],
    items: tuple[tuple[str, str, str, int, int], ...],
    notice: str,
    notice2_title: str,
    notice2_body: str,
) -> str:
    """EQUIP 深皮种子：岗名/分类/样例器材随 kind 换，表结构不变。"""
    cat_sql = ", ".join(f"({i}, '{n}')" for i, n in enumerate(cats, 1))
    item_rows = []
    for i, (title, author, isbn, cat_id, stock) in enumerate(items, 1):
        item_rows.append(
            f"({i}, '{title}', '{author}', '{isbn}', {cat_id}, {stock}, 'available')"
        )
    items_sql = ",\n".join(item_rows)
    return f"""\
INSERT INTO sys_user (username, password, role, nickname, phone, profile_json, super_admin, profile_editable, enabled) VALUES
('admin', 'admin123', 'admin', '{admin}', '13800000000', '{{}}', 1, 0, 1),
('subadmin', 'sub123', 'admin', '{sub}', '13800000001', '{{}}', 0, 1, 1),
('user', 'user123', 'user', '借用人甲', '13800000002',
 '{{"realName":"李同学","email":"li@demo.edu","gender":"{gender}","studentNo":"S20230001","dept":"{dept}","identityType":"学生","labOrOffice":"{place}"}}',
 0, 1, 1)
ON DUPLICATE KEY UPDATE nickname=VALUES(nickname), phone=VALUES(phone), profile_json=VALUES(profile_json);

INSERT IGNORE INTO category (id, name) VALUES
{cat_sql};
INSERT IGNORE INTO equip (id, title, author, isbn, category_id, stock, status) VALUES
{items_sql};
INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '{notice}', '请按需申请、按时归还；逾期将登记催还。', 'admin', '{admin}'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='{notice}');
INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '{notice2_title}', '{notice2_body}', 'admin', '{admin}'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='{notice2_title}');
"""


_EQUIP_SPORTS = _equip_kind_seed(
    admin="体育部主管",
    sub="器材管理员",
    dept="体育学院",
    place="体育馆器材室",
    gender="男",
    cats=("球类", "健身", "田径", "防护", "其他"),
    items=(
        ("羽毛球拍套装", "尤尼克斯", "SP-BAD-01", 1, 12),
        ("篮球", "斯伯丁", "SP-BB-02", 1, 10),
        ("跳绳", "李宁", "SP-ROPE-03", 3, 20),
        ("哑铃 5kg", "学校体育部", "SP-DB-04", 2, 8),
        ("护膝", "迪卡侬", "SP-PAD-05", 4, 15),
    ),
    notice="借用须知",
    notice2_title="开放时间",
    notice2_body="工作日与课余时段办理领用与归还。",
)

_EQUIP_MEDIA = _equip_kind_seed(
    admin="传媒中心主管",
    sub="器材管理员",
    dept="新闻传播学院",
    place="融媒体中心",
    gender="女",
    cats=("相机", "摄像", "录音", "附件", "其他"),
    items=(
        ("单反相机套机", "佳能", "AV-DSL-01", 1, 4),
        ("摄像机", "索尼", "AV-CAM-02", 2, 3),
        ("无线麦", "罗德", "AV-MIC-03", 3, 6),
        ("三脚架", "曼富图", "AV-TRI-04", 4, 8),
        ("稳定器", "大疆", "AV-GIM-05", 4, 2),
    ),
    notice="借用须知",
    notice2_title="开放时间",
    notice2_body="工作日办理领用；拍摄档期请提前申请。",
)

_EQUIP_MUSIC = _equip_kind_seed(
    admin="音乐系主管",
    sub="乐器管理员",
    dept="音乐学院",
    place="琴房管理室",
    gender="女",
    cats=("弦乐", "管乐", "键盘", "打击", "其他"),
    items=(
        ("古典吉他", "雅马哈", "MU-GIT-01", 1, 6),
        ("小提琴", "曹氏", "MU-VLN-02", 1, 4),
        ("电子琴", "卡西欧", "MU-KEY-03", 3, 3),
        ("非洲鼓", "学校乐器库", "MU-DRM-04", 4, 5),
        ("尤克里里", "恩雅", "MU-UKE-05", 1, 8),
    ),
    notice="租借须知",
    notice2_title="琴房须知",
    notice2_body="请爱护乐器、按时归还；损坏须登记说明。",
)

_EQUIP_TEACH = _equip_kind_seed(
    admin="教务主管",
    sub="教具管理员",
    dept="教务处",
    place="教具室",
    gender="男",
    cats=("模型", "挂图", "实验演示", "多媒体教具", "其他"),
    items=(
        ("人体模型", "教务处", "TE-MOD-01", 1, 3),
        ("中国地图挂图", "教务处", "TE-MAP-02", 2, 5),
        ("电路演示板", "电工教研室", "TE-CIR-03", 3, 4),
        ("地球仪", "地理教研室", "TE-GLB-04", 1, 6),
        ("显微镜教具", "生物教研室", "TE-MIC-05", 3, 2),
    ),
    notice="借用须知",
    notice2_title="开放时间",
    notice2_body="工作日办理教具领用与归还。",
)

_EQUIP_OUTDOOR = _equip_kind_seed(
    admin="团委主管",
    sub="装备管理员",
    dept="校团委",
    place="拓展装备库",
    gender="男",
    cats=("露营", "登山", "拓展", "防护", "其他"),
    items=(
        ("双人帐篷", "探路者", "OD-TENT-01", 1, 6),
        ("登山杖", "黑钻", "OD-POLE-02", 2, 10),
        ("安全绳套装", "团委", "OD-ROPE-03", 3, 4),
        ("头灯", "奈特科尔", "OD-LAMP-04", 4, 12),
        ("防潮垫", "牧高笛", "OD-MAT-05", 1, 8),
    ),
    notice="借用须知",
    notice2_title="活动须知",
    notice2_body="户外活动请提前登记领用，归还时检查完好。",
)

_EQUIP_GEAR = _equip_kind_seed(
    admin="设备主管",
    sub="器材管理员",
    dept="资产处",
    place="公用器材室",
    gender="男",
    cats=("通用设备", "工具", "电子", "办公外设", "其他"),
    items=(
        ("便携投影仪", "爱普生", "GE-PJ-01", 1, 4),
        ("对讲机套装", "摩托罗拉", "GE-RAD-02", 3, 8),
        ("电钻工具箱", "博世", "GE-TOOL-03", 2, 3),
        ("移动音箱", "JBL", "GE-SPK-04", 3, 5),
        ("延长线盘", "后勤", "GE-CBL-05", 4, 10),
    ),
    notice="借用须知",
    notice2_title="开放时间",
    notice2_body="工作日 8:30–17:30 办理借用与归还。",
)

_EQUIP_SEEDS = {
    "light": _EQUIP_LIGHT,
    "costume": _EQUIP_COSTUME,
    "sports": _EQUIP_SPORTS,
    "media": _EQUIP_MEDIA,
    "music": _EQUIP_MUSIC,
    "teach": _EQUIP_TEACH,
    "outdoor": _EQUIP_OUTDOOR,
    "gear": _EQUIP_GEAR,
}

_PROPERTY_MUNICIPAL = """\
INSERT INTO sys_user (username, password, role, nickname, phone, profile_json, super_admin, profile_editable, enabled) VALUES
('admin', 'admin123', 'admin', '市政主管', '13800000000', '{}', 1, 0, 1),
('subadmin', 'sub123', 'admin', '巡查员', '13800000001', '{}', 0, 1, 1),
('user', 'user123', 'user', '市民甲', '13800000002',
 '{"realName":"张市民","email":"zhang@demo.com","gender":"女","houseBuilding":"东区","houseUnit":"一街","houseNo":"路灯12号","ownerType":"居民","parkingNo":"","emergencyContact":"张先生","emergencyPhone":"13900000002"}',
 0, 1, 1)
ON DUPLICATE KEY UPDATE nickname=VALUES(nickname), phone=VALUES(phone), profile_json=VALUES(profile_json);

INSERT IGNORE INTO building (id, name) VALUES (1, '东区一街'), (2, '西区二路');
INSERT IGNORE INTO room (id, building_id, code) VALUES (1, 1, '路灯12'), (2, 1, '井盖A3'), (3, 2, '路灯08');
INSERT IGNORE INTO ticket_type (id, name, sort_no) VALUES
(1, '路灯', 1), (2, '井盖', 2), (3, '市政设施', 3), (4, '其他', 4);

INSERT IGNORE INTO ticket (id, username, title, location, type_id, room_id, status, priority, contact_phone, remark) VALUES
(1, 'user', '东区一街路灯不亮', '东区一街 路灯12', 1, 1, 'pending', '普通', '13800000002', '夜间整段不亮，影响通行。'),
(2, 'user', '西区二路井盖松动', '西区二路 井盖A3', 2, 2, 'approved', '普通', '13800000002', '已围挡待换。'),
(3, 'user', '路灯08灯罩破损', '西区二路 路灯08', 1, 3, 'returned', '普通', '13800000002', '已更换灯罩。');

INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '报修须知', '请写明片区路段与设施位置并上传现场照片，市政将尽快受理。', 'admin', '市政主管'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='报修须知');
"""

_PROPERTY_COMPLAINT = """\
INSERT INTO sys_user (username, password, role, nickname, phone, profile_json, super_admin, profile_editable, enabled) VALUES
('admin', 'admin123', 'admin', '物业主管', '13800000000', '{}', 1, 0, 1),
('subadmin', 'sub123', 'admin', '物业调度', '13800000001', '{}', 0, 1, 1),
('user', 'user123', 'user', '业主甲', '13800000002',
 '{"realName":"张业主","email":"owner@demo.com","gender":"女","houseBuilding":"A栋","houseUnit":"1","houseNo":"101","ownerType":"业主","parkingNo":"B-12","emergencyContact":"张先生","emergencyPhone":"13900000002"}',
 0, 1, 1)
ON DUPLICATE KEY UPDATE nickname=VALUES(nickname), phone=VALUES(phone), profile_json=VALUES(profile_json);

INSERT IGNORE INTO building (id, name) VALUES (1, 'A 栋'), (2, 'B 栋');
INSERT IGNORE INTO room (id, building_id, code) VALUES (1, 1, '101'), (2, 1, '102'), (3, 2, '201');
INSERT IGNORE INTO ticket_type (id, name, sort_no) VALUES
(1, '噪音扰民', 1), (2, '环境卫生', 2), (3, '服务态度', 3), (4, '其他投诉', 4);

INSERT IGNORE INTO ticket (id, username, title, location, type_id, room_id, status, priority, contact_phone, remark) VALUES
(1, 'user', 'A栋夜间装修噪音', 'A 栋 101', 1, 1, 'pending', '普通', '13800000002', '连续三天夜间施工，请核实劝阻。'),
(2, 'user', '楼道堆物占道', 'A 栋 102', 2, 2, 'approved', '普通', '13800000002', '已约谈清理中。'),
(3, 'user', '客服态度投诉', 'B 栋 201', 3, 3, 'returned', '普通', '13800000002', '已回访办结。');

INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '投诉须知', '请如实填写地址与诉求描述，物业将尽快受理办结。', 'admin', '物业主管'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='投诉须知');
"""

_IT_AFTERSALES = """\
INSERT INTO sys_user (username, password, role, nickname, phone, profile_json, super_admin, profile_editable, enabled) VALUES
('admin', 'admin123', 'admin', '客服主管', '13800000000', '{}', 1, 0, 1),
('subadmin', 'sub123', 'admin', '客服专员', '13800000001', '{}', 0, 1, 1),
('user', 'user123', 'user', '客户甲', '13800000002',
 '{"realName":"陈客户","email":"chen@demo.com","gender":"男","identityType":"个人客户","memberNo":"M20230108","officeOrDorm":"城东门店","emergencyPhone":"13900000002"}',
 0, 1, 1)
ON DUPLICATE KEY UPDATE nickname=VALUES(nickname), phone=VALUES(phone), profile_json=VALUES(profile_json);

INSERT IGNORE INTO campus_zone (id, name) VALUES (1, '城东门店'), (2, '城西网点');
INSERT IGNORE INTO endpoint (id, building_id, code) VALUES (1, 1, '柜台1'), (2, 1, '柜台2'), (3, 2, '自提点');
INSERT IGNORE INTO fault_type (id, name, sort_no) VALUES
(1, '退换货', 1), (2, '维修咨询', 2), (3, '服务投诉', 3), (4, '其他售后', 4);

INSERT IGNORE INTO ticket (id, username, title, location, type_id, room_id, status, priority, contact_phone, remark) VALUES
(1, 'user', '城东门店退换货咨询', '城东门店 柜台1', 1, 1, 'pending', '普通', '13800000002', '到货外观破损，申请换货。'),
(2, 'user', '维修进度催问', '城东门店 柜台2', 2, 2, 'approved', '普通', '13800000002', '维修中已回电。'),
(3, 'user', '服务投诉已处理', '城西网点 自提点', 3, 3, 'returned', '普通', '13800000002', '已赔付办结。');

INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '售后须知', '请写明网点与问题描述并上传凭证，客服将尽快受理。', 'admin', '客服主管'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='售后须知');
"""

_IT_MAINTENANCE = """\
INSERT INTO sys_user (username, password, role, nickname, phone, profile_json, super_admin, profile_editable, enabled) VALUES
('admin', 'admin123', 'admin', '维保主管', '13800000000', '{}', 1, 0, 1),
('subadmin', 'sub123', 'admin', '维保员', '13800000001', '{}', 0, 1, 1),
('user', 'user123', 'user', '报修人甲', '13800000002',
 '{"realName":"陈工","email":"chen@demo.com","gender":"男","identityType":"员工","employeeNo":"E20230108","dept":"设备部","officeOrDorm":"机房A","title":"设备员"}',
 0, 1, 1)
ON DUPLICATE KEY UPDATE nickname=VALUES(nickname), phone=VALUES(phone), profile_json=VALUES(profile_json);

INSERT IGNORE INTO campus_zone (id, name) VALUES (1, '机房区'), (2, '办公区');
INSERT IGNORE INTO endpoint (id, building_id, code) VALUES (1, 1, 'UPS-01'), (2, 1, '空调-02'), (3, 2, '打印-03');
INSERT IGNORE INTO fault_type (id, name, sort_no) VALUES
(1, '定期保养', 1), (2, '故障维修', 2), (3, '备件更换', 3), (4, '其他维保', 4);

INSERT IGNORE INTO ticket (id, username, title, location, type_id, room_id, status, priority, contact_phone, remark) VALUES
(1, 'user', '机房UPS-01异响告警', '机房区 UPS-01', 2, 1, 'pending', '紧急', '13800000002', '夜间告警灯闪烁，请上门排查。'),
(2, 'user', '空调-02定期保养', '机房区 空调-02', 1, 2, 'approved', '普通', '13800000002', '保养进行中。'),
(3, 'user', '打印-03更换硒鼓', '办公区 打印-03', 3, 3, 'returned', '普通', '13800000002', '备件已换办结。');

INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '维保须知', '请写明设备区域、资产编号与现象并上传照片，维保将尽快受理。', 'admin', '维保主管'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='维保须知');
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

# 模板默认企业会议室；校园/琴房/自习室等题叠校园种子
_MEETING_CAMPUS = """\
INSERT INTO sys_user (username, password, role, nickname, phone, profile_json, super_admin, profile_editable, enabled) VALUES
('admin', 'admin123', 'admin', '后勤主管', '13800000000', '{}', 1, 0, 1),
('subadmin', 'sub123', 'admin', '预约管理员', '13800000001', '{}', 0, 1, 1),
('user', 'user123', 'user', '预约人甲', '13800000002',
 '{"realName":"赵老师","email":"zhao@demo.edu","gender":"男","identityType":"教职工","employeeNo":"T1001","dept":"教务处","jobTitle":"教务员"}',
 0, 1, 1)
ON DUPLICATE KEY UPDATE nickname=VALUES(nickname), phone=VALUES(phone), profile_json=VALUES(profile_json);

INSERT IGNORE INTO category (id, name) VALUES (1, '小型'), (2, '中型'), (3, '大型');
INSERT IGNORE INTO room (id, title, author, isbn, category_id, stock, status) VALUES
(1, 'A101 研讨室', '0', '楼A-101 / 6人', 1, 1, 'available'),
(2, 'B203 会议室', '0', '楼B-203 / 12人', 2, 1, 'available'),
(3, '报告厅', '0', '图文中心 / 80人', 3, 1, 'available');
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
INSERT IGNORE INTO reservation (id, slot_id, username, status, remark, subject, party_size) VALUES
(1, 1, 'user', 'confirmed', '', '教研例会', 4),
(2, 2, 'user', 'pending', '', '答辩排练', 6),
(3, 5, 'user', 'completed', '', '系务会议', 8);
UPDATE resource_slot SET booked = 1 WHERE id IN (1, 2);
INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '会议室预约须知', '请按预约时段使用并按时离开；可取消释放名额。', 'admin', '后勤主管'
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
INSERT IGNORE INTO reply (id, book_id, username, status, apply_at, approve_at, remark) VALUES
(1, 1, 'user', 'approved', NOW(), NOW(), '<p>我也想参加义诊，怎么报名？</p>'),
(2, 3, 'subadmin', 'approved', NOW(), NOW(), '<p>周日上午还可拼一人，私信楼主。</p>'),
(3, 5, 'user', 'pending', NOW(), NULL, '<p>推荐李师傅，上次换锁很快。</p>');
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
(1, '实验室安全培训', '教务处 / 主讲甲', 'https://www.w3schools.com/html/mov_bbb.mp4', 1, 1, 'available'),
(2, '校史纪录片', '宣传部', 'https://www.w3schools.com/html/mov_bbb.mp4', 2, 1, 'available'),
(3, '运动会开幕式回放', '体育部', 'https://www.w3schools.com/html/mov_bbb.mp4', 3, 1, 'available'),
(4, '新生入学教育', '学工处', 'https://www.w3schools.com/html/mov_bbb.mp4', 1, 1, 'available'),
(5, '毕业季特辑', '团委', 'https://www.w3schools.com/html/mov_bbb.mp4', 3, 1, 'available');
INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '观影须知', '片源仅供学习使用；请文明观影，勿传播未授权内容。', 'admin', '媒资主管'
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
SELECT '试听须知', '曲源仅供学习使用；请尊重版权，勿传播未授权内容。', 'admin', '曲库主管'
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
SELECT '阅读须知', '文章仅供学习使用；转载请注明出处。内容由主编维护发布。', 'admin', '主编'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='阅读须知');
INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '本周上新', '教学与学工栏目已更新，欢迎收藏订阅。', 'admin', '主编'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='本周上新');
"""

_TIMEBANK_CAMPUS = """\
INSERT INTO sys_user (username, password, role, nickname, phone, profile_json, super_admin, profile_editable, enabled) VALUES
('admin', 'admin123', 'admin', '时间银行主管', '13800000000', '{}', 1, 0, 1),
('subadmin', 'sub123', 'admin', '核销员', '13800000001', '{}', 0, 1, 1),
('user', 'user123', 'user', '志愿者甲', '13800000002',
 '{"realName":"吴同学","email":"wu@demo.edu","gender":"女","studentNo":"20230005","dept":"社会学院"}',
 0, 1, 1)
ON DUPLICATE KEY UPDATE nickname=VALUES(nickname), phone=VALUES(phone), profile_json=VALUES(profile_json);

INSERT IGNORE INTO category (id, name) VALUES (1, '社区服务'), (2, '校园志愿'), (3, '结对互助');
INSERT IGNORE INTO tb_service (id, title, author, isbn, category_id, stock, status) VALUES
(1, '图书馆整理志愿服务', '图书馆', '可登记存入时长', 2, 1, 'available'),
(2, '社区陪伴老人', '社区站', '结对服务存入', 1, 1, 'available'),
(3, '互助兑换：作业辅导时段', '学生会', '核销扣减事项', 3, 1, 'available');

INSERT IGNORE INTO tb_account (username, balance_hours) VALUES ('user', 8.00);
INSERT INTO tb_ledger (username, delta_hours, reason, ref_type, ref_id)
SELECT 'user', 8.00, '初始存入', 'seed', NULL
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM tb_ledger WHERE username='user' AND reason='初始存入');

INSERT IGNORE INTO tb_redeem (id, username, book_id, status, qty, remark, apply_at) VALUES
(1, 'user', 3, 'pending', 2, '兑换作业辅导 2 小时', NOW());

INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '时间银行须知', '存入即时入账；核销须审批且余额充足。', 'admin', '时间银行主管'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='时间银行须知');
"""

# 校园车位：模板默认商业月租；校园档整块替换（学号/教职工与资料页对齐）
_PARKING_CAMPUS = """\
INSERT INTO sys_user (username, password, role, nickname, phone, profile_json, super_admin, profile_editable, enabled) VALUES
('admin', 'admin123', 'admin', '后勤主管', '13800000000', '{}', 1, 0, 1),
('subadmin', 'sub123', 'admin', '车场管理员', '13800000001', '{}', 0, 1, 1),
('user', 'user123', 'user', '车主甲', '13800000002',
 '{"realName":"周明","email":"zhou@demo.edu","gender":"男","plateNo":"粤A12345","vehicleType":"小型车","ownerType":"教职工","employeeNo":"T2026001","dept":"计算机学院"}',
 0, 1, 1)
ON DUPLICATE KEY UPDATE nickname=VALUES(nickname), phone=VALUES(phone), profile_json=VALUES(profile_json);

INSERT IGNORE INTO category (id, name) VALUES (1, '地上'), (2, '地下');
INSERT IGNORE INTO space (id, title, author, isbn, category_id, stock, status) VALUES
(1, '教工A区-01', '0', '图书馆东侧', 1, 1, 'available'),
(2, '教工A区-02', '0', '图书馆东侧', 1, 1, 'available'),
(3, '学生B区-08', '0', '宿舍区地下', 2, 1, 'available');
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
INSERT IGNORE INTO reservation (id, slot_id, username, status, remark, plate_no) VALUES
(1, 1, 'user', 'confirmed', '', '粤A12345'),
(2, 2, 'user', 'pending', '', '粤A12345'),
(3, 5, 'user', 'completed', '', '粤A67890');
UPDATE resource_slot SET booked = 1 WHERE id IN (1, 2);
INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '校园车位预约', '预约成功后请按时入场；取消后释放车位时段。访客请选访客身份。', 'admin', '后勤主管'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='校园车位预约' OR title='车位预约');
"""

# 高校食堂：模板默认社会餐饮；食堂档整块替换（窗口/宿舍地址）
