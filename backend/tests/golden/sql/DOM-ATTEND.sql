-- bake domain=DOM-ATTEND · tables in [6,15]
CREATE DATABASE IF NOT EXISTS `thesis_test` DEFAULT CHARACTER SET utf8mb4;
USE `thesis_test`;

CREATE TABLE IF NOT EXISTS sys_user (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  username VARCHAR(64) NOT NULL UNIQUE,
  password VARCHAR(128) NOT NULL,
  role VARCHAR(32) NOT NULL,
  nickname VARCHAR(64),
  phone VARCHAR(32),
  avatar_url VARCHAR(255),
  profile_json VARCHAR(2048) DEFAULT '{}',
  super_admin TINYINT DEFAULT 0,
  profile_editable TINYINT DEFAULT 1,
  enabled TINYINT DEFAULT 1,
  staff_post VARCHAR(64) DEFAULT '',
  staff_kind VARCHAR(16) DEFAULT '',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS category (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  name VARCHAR(64) NOT NULL UNIQUE
);

-- ArchiveStore 兼容列；author=部门；isbn=工号/备注；stock=可请假
CREATE TABLE IF NOT EXISTS staff_person (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  title VARCHAR(200) NOT NULL,
  dept_name VARCHAR(100),
  badge_note VARCHAR(255),
  category_id BIGINT,
  stock INT DEFAULT 1,
  status VARCHAR(32) DEFAULT 'available',
  cover_url VARCHAR(255),
  stage VARCHAR(32) DEFAULT '在岗',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- book_id=staff_person.id
CREATE TABLE IF NOT EXISTS leave_req (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  staff_person_id BIGINT NOT NULL,
  username VARCHAR(64) NOT NULL,
  status VARCHAR(32) NOT NULL DEFAULT 'pending',
  assignee_username VARCHAR(64) NULL,
  apply_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  approve_at DATETIME NULL,
  return_at DATETIME NULL,
  remark VARCHAR(512),
  contact_channel VARCHAR(32) DEFAULT '',
  next_follow_at DATETIME NULL
);

CREATE TABLE IF NOT EXISTS sys_message (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  username VARCHAR(64) NOT NULL,
  title VARCHAR(128) NOT NULL,
  body VARCHAR(512) DEFAULT '',
  ref_type VARCHAR(32) DEFAULT '',
  ref_id BIGINT NULL,
  read_at DATETIME NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  KEY idx_msg_user (username, id)
);

CREATE TABLE IF NOT EXISTS sys_notice (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  title VARCHAR(128) NOT NULL,
  content TEXT,
  publisher_username VARCHAR(64),
  publisher_name VARCHAR(64),
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS sys_config (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  cfg_key VARCHAR(64) NOT NULL UNIQUE,
  cfg_value VARCHAR(255) NOT NULL,
  remark VARCHAR(128) DEFAULT ''
);

INSERT INTO sys_user (username, password, role, nickname, phone, profile_json, super_admin, profile_editable, enabled) VALUES
('admin', 'admin123', 'admin', '人事主管', '13800000000', '{}', 1, 0, 1),
('subadmin', 'sub123', 'admin', '考勤员', '13800000001', '{}', 0, 1, 1),
('user', 'user123', 'user', '员工甲', '13800000002',
 '{"realName":"周明","email":"zhou@demo.com","gender":"男","employeeNo":"E2026008","dept":"行政办","jobTitle":"科员"}',
 0, 1, 1)
ON DUPLICATE KEY UPDATE nickname=VALUES(nickname), phone=VALUES(phone), profile_json=VALUES(profile_json);

INSERT IGNORE INTO category (id, name) VALUES (1, '教学岗'), (2, '行政岗'), (3, '后勤岗');
INSERT IGNORE INTO staff_person (id, title, dept_name, badge_note, category_id, stock, status) VALUES
(1, '周明', '行政办', 'E2026008 / 坐班', 2, 1, 'available'),
(2, '李芳', '计算机学院', 'T2026012 / 教师', 1, 1, 'available'),
(3, '王强', '后勤处', 'L2026003 / 维修', 3, 1, 'available'),
(4, '赵敏', '教务处', 'A2026044 / 教务员', 2, 1, 'available'),
(5, '陈浩', '外国语学院', 'T2026088 / 教师', 1, 1, 'available');
INSERT IGNORE INTO sys_config (cfg_key, cfg_value, remark) VALUES
('leave_hint', '请填写请假事由与起止时间', '请假说明'),
('max_open_leave', '3', '每人最大在途请假单');
INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '请假须知', '事假须提前申请；病假可补交证明；销假请在返回当日确认。', 'admin', '人事主管'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='请假须知');
INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '本月考勤', '月底前提交未销假单据，逾期将记入考勤异常。', 'admin', '人事主管'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='本月考勤');

CREATE TABLE IF NOT EXISTS `leave_req_progress` (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  ticket_id BIGINT NOT NULL,
  status VARCHAR(32) NOT NULL,
  operator VARCHAR(64),
  remark VARCHAR(255) DEFAULT '',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  KEY idx_progress_ticket (ticket_id, id)
);

-- staff posts (clerk / worker)
UPDATE sys_user SET staff_post='', staff_kind='' WHERE super_admin=1;
UPDATE sys_user SET staff_post='attend_clerk', staff_kind='clerk', nickname='考勤员' WHERE username='subadmin' AND role='admin' AND IFNULL(super_admin,0)=0;
