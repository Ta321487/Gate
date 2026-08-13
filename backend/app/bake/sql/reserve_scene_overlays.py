"""预约族深皮种子（HOSPITAL / SALON / MEETING / PARKING 行业叠层）。

表结构不变，只换人名/业务对象/公告，并含一条已确认预约（占坑）。
"""

from __future__ import annotations

_SLOTS_C3 = """\
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
"""

_SLOTS_C1 = """\
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
"""

_SLOTS_C2 = """\
INSERT IGNORE INTO resource_slot (id, item_id, start_at, end_at, capacity, booked) VALUES
(1, 1, '2026-09-20 09:00:00', '2026-09-20 10:00:00', 2, 0),
(2, 1, '2026-09-20 10:00:00', '2026-09-20 11:00:00', 2, 0),
(3, 1, '2026-09-20 14:00:00', '2026-09-20 15:00:00', 2, 0),
(4, 1, '2026-09-20 15:00:00', '2026-09-20 16:00:00', 2, 0),
(5, 2, '2026-09-20 09:00:00', '2026-09-20 10:00:00', 2, 0),
(6, 2, '2026-09-20 10:00:00', '2026-09-20 11:00:00', 2, 0),
(7, 2, '2026-09-20 14:00:00', '2026-09-20 15:00:00', 2, 0),
(8, 2, '2026-09-20 15:00:00', '2026-09-20 16:00:00', 2, 0),
(9, 3, '2026-09-20 09:00:00', '2026-09-20 10:00:00', 2, 0),
(10, 3, '2026-09-20 10:00:00', '2026-09-20 11:00:00', 2, 0),
(11, 3, '2026-09-20 14:00:00', '2026-09-20 15:00:00', 2, 0),
(12, 3, '2026-09-20 15:00:00', '2026-09-20 16:00:00', 2, 0);
"""

_HOSP_RESV = """\
INSERT IGNORE INTO reservation (id, slot_id, username, status, remark, patient_name, visit_type, symptom_note) VALUES
(1, 1, 'patient', 'confirmed', '', '{name}', '{vtype}', '{note}');
UPDATE resource_slot SET booked = 1 WHERE id = 1;
"""

_SALON_RESV = """\
INSERT IGNORE INTO reservation (id, slot_id, username, status, remark, preferred_stylist) VALUES
(1, 1, 'user', 'confirmed', '', '{stylist}');
UPDATE resource_slot SET booked = 1 WHERE id = 1;
"""

_MEET_RESV = """\
INSERT IGNORE INTO reservation (id, slot_id, username, status, remark, subject, party_size) VALUES
(1, 1, 'user', 'confirmed', '', '{subject}', {party});
UPDATE resource_slot SET booked = 1 WHERE id = 1;
"""

_PARK_RESV = """\
INSERT IGNORE INTO reservation (id, slot_id, username, status, remark, plate_no) VALUES
(1, 1, 'user', 'confirmed', '', '{plate}');
UPDATE resource_slot SET booked = 1 WHERE id = 1;
"""

HOSPITAL_WINDOW = f"""\
INSERT INTO sys_user (username, password, role, nickname, phone, profile_json, super_admin, profile_editable, enabled) VALUES
('admin', 'admin123', 'admin', '大厅主管', '13800000000', '{{}}', 1, 0, 1),
('subadmin', 'sub123', 'admin', '窗口员', '13800000001', '{{}}', 0, 1, 1),
('patient', 'patient123', 'patient', '办事人甲', '13800000002',
 '{{"realName":"钱办事","email":"qian@demo.com","gender":"女","idNo":"440100199001011234","bizPrefer":"社保卡"}}',
 0, 1, 1)
ON DUPLICATE KEY UPDATE nickname=VALUES(nickname), phone=VALUES(phone), profile_json=VALUES(profile_json);

INSERT IGNORE INTO category (id, name) VALUES (1, '社保'), (2, '户籍'), (3, '车管');
INSERT IGNORE INTO doctor (id, title, author, isbn, category_id, stock, status) VALUES
(1, '社保卡补换窗口', '0', '携带身份证原件', 1, 1, 'available'),
(2, '居住证办理窗口', '0', '居住证明 / 照片', 2, 1, 'available'),
(3, '驾驶证业务窗口', '15.00', '工本费另计', 3, 1, 'available');
{_SLOTS_C3}{_HOSP_RESV.format(name="钱办事", vtype="初办", note="社保卡补办")}INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '取号须知', '请按时到窗；过号请重新取号。本期无真政务专网对接。', 'admin', '大厅主管'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='取号须知' OR title='挂号须知');
"""

HOSPITAL_VISIT = f"""\
INSERT INTO sys_user (username, password, role, nickname, phone, profile_json, super_admin, profile_editable, enabled) VALUES
('admin', 'admin123', 'admin', '病区主管', '13800000000', '{{}}', 1, 0, 1),
('subadmin', 'sub123', 'admin', '护士站', '13800000001', '{{}}', 0, 1, 1),
('patient', 'patient123', 'patient', '探视人甲', '13800000002',
 '{{"realName":"赵探视","email":"zhao@demo.com","gender":"男","patientRelation":"子女","wardPrefer":"内科三病区"}}',
 0, 1, 1)
ON DUPLICATE KEY UPDATE nickname=VALUES(nickname), phone=VALUES(phone), profile_json=VALUES(profile_json);

INSERT IGNORE INTO category (id, name) VALUES (1, '普通探视'), (2, '陪护'), (3, '养老探访');
INSERT IGNORE INTO doctor (id, title, author, isbn, category_id, stock, status) VALUES
(1, '内科三病区探视', '0', '14:00–16:00 / 限两人', 1, 1, 'available'),
(2, '外科一病区探视', '0', '需戴口罩', 1, 1, 'available'),
(3, '养老院日间探访', '0', '一楼会客区', 3, 1, 'available');
{_SLOTS_C3}{_HOSP_RESV.format(name="赵探视", vtype="普通探视", note="探望父亲 12 床")}INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '探视须知', '探视名额有限；请填写探视人与被访信息；按时到访。', 'admin', '病区主管'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='探视须知' OR title='挂号须知');
"""

SALON_COUNSEL = f"""\
INSERT INTO sys_user (username, password, role, nickname, phone, profile_json, super_admin, profile_editable, enabled) VALUES
('admin', 'admin123', 'admin', '咨询中心主管', '13800000000', '{{}}', 1, 0, 1),
('subadmin', 'sub123', 'admin', '预约管理员', '13800000001', '{{}}', 0, 1, 1),
('user', 'user123', 'user', '来访者甲', '13800000002',
 '{{"realName":"周同学","email":"zhou@demo.edu","gender":"女","memberNo":"C2026001"}}',
 0, 1, 1)
ON DUPLICATE KEY UPDATE nickname=VALUES(nickname), phone=VALUES(phone), profile_json=VALUES(profile_json);

INSERT IGNORE INTO category (id, name) VALUES (1, '个体咨询'), (2, '团体辅导');
INSERT IGNORE INTO service (id, title, author, isbn, category_id, stock, status, stylist_name) VALUES
(1, '学业压力个体咨询', '0', '约50分钟', 1, 1, 'available', '王咨询师'),
(2, '情绪调节个体咨询', '0', '约50分钟', 1, 1, 'available', '李咨询师'),
(3, '新生适应团体辅导', '0', '约90分钟', 2, 1, 'available', '团体带领者');
{_SLOTS_C2}{_SALON_RESV.format(stylist="王咨询师")}INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '咨询预约', '请准时到谈；改约请先取消原时段。保密与危机转介按校规执行。', 'admin', '咨询中心主管'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='咨询预约' OR title='服务预约');
"""

SALON_DRIVE = f"""\
INSERT INTO sys_user (username, password, role, nickname, phone, profile_json, super_admin, profile_editable, enabled) VALUES
('admin', 'admin123', 'admin', '驾校主管', '13800000000', '{{}}', 1, 0, 1),
('subadmin', 'sub123', 'admin', '前台', '13800000001', '{{}}', 0, 1, 1),
('user', 'user123', 'user', '学员甲', '13800000002',
 '{{"realName":"周学员","email":"zhou@demo.com","gender":"男","memberNo":"D2026001"}}',
 0, 1, 1)
ON DUPLICATE KEY UPDATE nickname=VALUES(nickname), phone=VALUES(phone), profile_json=VALUES(profile_json);

INSERT IGNORE INTO category (id, name) VALUES (1, '科目二'), (2, '科目三');
INSERT IGNORE INTO service (id, title, author, isbn, category_id, stock, status, stylist_name) VALUES
(1, '科目二场地练车', '80.00', '约60分钟', 1, 1, 'available', '张教练'),
(2, '科目三路考陪驾', '100.00', '约60分钟', 2, 1, 'available', '李教练'),
(3, '模拟考强化', '90.00', '约45分钟', 1, 1, 'available', '王教练');
{_SLOTS_C2}{_SALON_RESV.format(stylist="张教练")}INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '练车预约', '请带学员证按时到场；迟到可能需改约。', 'admin', '驾校主管'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='练车预约' OR title='服务预约');
"""

SALON_HOME = f"""\
INSERT INTO sys_user (username, password, role, nickname, phone, profile_json, super_admin, profile_editable, enabled) VALUES
('admin', 'admin123', 'admin', '家政站主管', '13800000000', '{{}}', 1, 0, 1),
('subadmin', 'sub123', 'admin', '调度员', '13800000001', '{{}}', 0, 1, 1),
('user', 'user123', 'user', '住户甲', '13800000002',
 '{{"realName":"周先生","email":"zhou@demo.com","gender":"男","memberNo":"H2026001"}}',
 0, 1, 1)
ON DUPLICATE KEY UPDATE nickname=VALUES(nickname), phone=VALUES(phone), profile_json=VALUES(profile_json);

INSERT IGNORE INTO category (id, name) VALUES (1, '上门保洁'), (2, '上门维修');
INSERT IGNORE INTO service (id, title, author, isbn, category_id, stock, status, stylist_name) VALUES
(1, '两小时上门保洁', '128.00', '约120分钟', 1, 1, 'available', '保洁师傅甲'),
(2, '水管疏通上门', '98.00', '约60分钟', 2, 1, 'available', '维修师傅乙'),
(3, '家电清洗上门', '158.00', '约90分钟', 2, 1, 'available', '维修师傅丙');
{_SLOTS_C2}{_SALON_RESV.format(stylist="保洁师傅甲")}INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '上门预约', '请填写上门地址与联系人；师傅按预约时段上门。', 'admin', '家政站主管'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='上门预约' OR title='服务预约');
"""

SALON_TUTOR = f"""\
INSERT INTO sys_user (username, password, role, nickname, phone, profile_json, super_admin, profile_editable, enabled) VALUES
('admin', 'admin123', 'admin', '辅导站主管', '13800000000', '{{}}', 1, 0, 1),
('subadmin', 'sub123', 'admin', '教务', '13800000001', '{{}}', 0, 1, 1),
('user', 'user123', 'user', '学员甲', '13800000002',
 '{{"realName":"周家长","email":"zhou@demo.com","gender":"女","memberNo":"T2026001"}}',
 0, 1, 1)
ON DUPLICATE KEY UPDATE nickname=VALUES(nickname), phone=VALUES(phone), profile_json=VALUES(profile_json);

INSERT IGNORE INTO category (id, name) VALUES (1, '学科辅导'), (2, '技能辅导');
INSERT IGNORE INTO service (id, title, author, isbn, category_id, stock, status, stylist_name) VALUES
(1, '高中数学一对一', '200.00', '约60分钟', 1, 1, 'available', '陈老师'),
(2, '英语口语陪练', '160.00', '约45分钟', 1, 1, 'available', '刘老师'),
(3, '钢琴入门辅导', '180.00', '约45分钟', 2, 1, 'available', '赵老师');
{_SLOTS_C2}{_SALON_RESV.format(stylist="陈老师")}INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '辅导预约', '请准时到课；改约请先取消原时段。', 'admin', '辅导站主管'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='辅导预约' OR title='服务预约');
"""

MEETING_EXHIBIT = f"""\
INSERT INTO sys_user (username, password, role, nickname, phone, profile_json, super_admin, profile_editable, enabled) VALUES
('admin', 'admin123', 'admin', '场馆主管', '13800000000', '{{}}', 1, 0, 1),
('subadmin', 'sub123', 'admin', '预约管理员', '13800000001', '{{}}', 0, 1, 1),
('user', 'user123', 'user', '参观者甲', '13800000002',
 '{{"realName":"赵参观","email":"zhao@demo.com","gender":"男","identityType":"校外","orgName":"社区志愿队"}}',
 0, 1, 1)
ON DUPLICATE KEY UPDATE nickname=VALUES(nickname), phone=VALUES(phone), profile_json=VALUES(profile_json);

INSERT IGNORE INTO category (id, name) VALUES (1, '常设展'), (2, '临展'), (3, '讲解场次');
INSERT IGNORE INTO room (id, title, author, isbn, category_id, stock, status) VALUES
(1, '党史馆一楼展厅', '0', '限流 40 人 / 场', 1, 1, 'available'),
(2, '非遗临展厅', '0', '限流 30 人 / 场', 2, 1, 'available'),
(3, '馆长讲解专场', '0', '需集合签到', 3, 1, 'available');
{_SLOTS_C1}{_MEET_RESV.format(subject="党史馆参观", party=4)}INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '参观预约须知', '请按预约场次入馆；过时不候，可取消释放名额。', 'admin', '场馆主管'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='参观预约须知' OR title='会议室预约须知');
"""

MEETING_GYM = f"""\
INSERT INTO sys_user (username, password, role, nickname, phone, profile_json, super_admin, profile_editable, enabled) VALUES
('admin', 'admin123', 'admin', '场馆主管', '13800000000', '{{}}', 1, 0, 1),
('subadmin', 'sub123', 'admin', '场馆管理员', '13800000001', '{{}}', 0, 1, 1),
('user', 'user123', 'user', '预约人甲', '13800000002',
 '{{"realName":"赵同学","email":"zhao@demo.edu","gender":"男","identityType":"学生","studentNo":"S20260001","dept":"体育学院"}}',
 0, 1, 1)
ON DUPLICATE KEY UPDATE nickname=VALUES(nickname), phone=VALUES(phone), profile_json=VALUES(profile_json);

INSERT IGNORE INTO category (id, name) VALUES (1, '球类'), (2, '水上'), (3, '琴房');
INSERT IGNORE INTO room (id, title, author, isbn, category_id, stock, status) VALUES
(1, '羽毛球馆 3 号场', '0', '需自备球拍', 1, 1, 'available'),
(2, '游泳馆标准泳道', '0', '凭学生证入馆', 2, 1, 'available'),
(3, '琴房 B203', '0', '限一人 / 时段', 3, 1, 'available');
{_SLOTS_C1}{_MEET_RESV.format(subject="羽毛球训练", party=2)}INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '场地预约须知', '请按预约时段使用并按时离开；可取消释放名额。', 'admin', '场馆主管'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='场地预约须知' OR title='会议室预约须知');
"""

PARKING_CHARGE = f"""\
INSERT INTO sys_user (username, password, role, nickname, phone, profile_json, super_admin, profile_editable, enabled) VALUES
('admin', 'admin123', 'admin', '充电站主管', '13800000000', '{{}}', 1, 0, 1),
('subadmin', 'sub123', 'admin', '场站管理员', '13800000001', '{{}}', 0, 1, 1),
('user', 'user123', 'user', '车主甲', '13800000002',
 '{{"realName":"孙先生","email":"sun@demo.com","gender":"男","plateNo":"粤B88EV1","vehicleType":"新能源","ownerType":"月租"}}',
 0, 1, 1)
ON DUPLICATE KEY UPDATE nickname=VALUES(nickname), phone=VALUES(phone), profile_json=VALUES(profile_json);

INSERT IGNORE INTO category (id, name) VALUES (1, '快充桩'), (2, '慢充桩');
INSERT IGNORE INTO space (id, title, author, isbn, category_id, stock, status) VALUES
(1, '快充桩 A-01', '2.00', '地上东侧 / 120kW', 1, 1, 'available'),
(2, '快充桩 A-02', '2.00', '地上东侧 / 120kW', 1, 1, 'available'),
(3, '慢充桩 B-08', '1.00', '地下二层 / 7kW', 2, 1, 'available');
{_SLOTS_C1}{_PARK_RESV.format(plate="粤B88EV1")}INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '充电预约', '预约成功后请按时入位充电；取消后释放桩位时段。无真支付与硬件联控。', 'admin', '充电站主管'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='充电预约' OR title='车位预约');
"""

HOTEL_HOMESTAY = f"""\
INSERT INTO sys_user (username, password, role, nickname, phone, profile_json, super_admin, profile_editable, enabled) VALUES
('admin', 'admin123', 'admin', '民宿老板', '13800000000', '{{}}', 1, 0, 1),
('subadmin', 'sub123', 'admin', '前台', '13800000001', '{{}}', 0, 1, 1),
('user', 'user123', 'user', '住客甲', '13800000002',
 '{{"realName":"吴旅客","email":"wu@demo.com","gender":"男","guestName":"吴旅客","companyOrSchool":"自驾游"}}',
 0, 1, 1)
ON DUPLICATE KEY UPDATE nickname=VALUES(nickname), phone=VALUES(phone), profile_json=VALUES(profile_json);

INSERT IGNORE INTO category (id, name) VALUES (1, '山景房'), (2, '亲子房');
INSERT IGNORE INTO room_type (id, title, author, isbn, category_id, stock, status) VALUES
(1, '山景双床客栈房', '198.00', '含早 / 2人', 1, 3, 'available'),
(2, '亲子榻榻米房', '268.00', '含早 / 可加床', 2, 2, 'available'),
(3, '露台大床套房', '358.00', '含早 / 景观阳台', 1, 1, 'available');
{_SLOTS_C3}INSERT IGNORE INTO reservation (id, slot_id, username, status, remark, guest_name, guest_count) VALUES
(1, 1, 'user', 'confirmed', '吴旅客', '吴旅客', 2);
UPDATE resource_slot SET booked = 1 WHERE id = 1;
INSERT IGNORE INTO biz_order (id, username, status, total_yuan, remark, reservation_id) VALUES
(1, 'user', 'confirmed', 198.00, 'reservation:1', 1);
INSERT IGNORE INTO order_line (id, order_id, item_id, title, price_yuan, qty) VALUES
(1, 1, 1, '山景双床客栈房', 198.00, 1);
INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '民宿预订', '选择房型与入住时段预订；无真支付，预约成功生成订单。', 'admin', '民宿老板'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='民宿预订' OR title='客房预订');
"""
