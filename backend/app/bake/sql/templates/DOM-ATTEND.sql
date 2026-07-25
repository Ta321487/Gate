-- bake domain=DOM-ATTEND · tables in [${TABLE_COUNT_MIN},${TABLE_COUNT_MAX}]
CREATE DATABASE IF NOT EXISTS `${DB_NAME}` DEFAULT CHARACTER SET utf8mb4;
USE `${DB_NAME}`;

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
  author VARCHAR(100),
  isbn VARCHAR(256),
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
  book_id BIGINT NOT NULL,
  username VARCHAR(64) NOT NULL,
  status VARCHAR(32) NOT NULL DEFAULT 'pending',
  assignee_username VARCHAR(64) NULL,
  apply_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  approve_at DATETIME NULL,
  due_at DATETIME NULL,
  return_at DATETIME NULL,
  fine_yuan DECIMAL(10,2) NOT NULL DEFAULT 0,
  reminded_at DATETIME NULL,
  remind_msg VARCHAR(255) DEFAULT '',
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

CREATE TABLE IF NOT EXISTS leave_req_log (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  leave_req_id BIGINT NOT NULL,
  action VARCHAR(32) NOT NULL,
  operator VARCHAR(64),
  remark VARCHAR(255) DEFAULT '',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO sys_user (username, password, role, nickname, phone, profile_json, super_admin, profile_editable, enabled) VALUES
('admin', 'admin123', 'admin', '人事主管', '13800000000', '{}', 1, 0, 1),
('subadmin', 'sub123', 'admin', '考勤员', '13800000001', '{}', 0, 1, 1),
('user', 'user123', 'user', '员工甲', '13800000002',
 '{"realName":"周明","email":"zhou@demo.com","gender":"男","identityType":"员工","employeeNo":"E2026008","dept":"行政办"}',
 0, 1, 1)
ON DUPLICATE KEY UPDATE nickname=VALUES(nickname), phone=VALUES(phone), profile_json=VALUES(profile_json);

INSERT IGNORE INTO category (id, name) VALUES (1, '职能岗'), (2, '业务岗'), (3, '一线岗');
INSERT IGNORE INTO staff_person (id, title, author, isbn, category_id, stock, status) VALUES
(1, '周明', '行政办', 'E2026008 / 坐班', 1, 1, 'available'),
(2, '李芳', '研发中心', 'E2026012 / 工程师', 2, 1, 'available'),
(3, '王强', '后勤保障', 'E2026003 / 维修', 3, 1, 'available'),
(4, '赵敏', '人事部', 'E2026044 / 专员', 1, 1, 'available'),
(5, '陈浩', '客户成功', 'E2026088 / 顾问', 2, 1, 'available');
INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '请假须知', '事假须提前申请；病假可补交证明；销假请在返回当日确认。', 'admin', '人事主管'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='请假须知');
INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '本月考勤', '月底前提交未销假单据，逾期将记入考勤异常。', 'admin', '人事主管'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='本月考勤');
