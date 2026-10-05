-- bake domain=DOM-GRADE · tables in [6,15]
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

-- ArchiveStore 兼容列；author=授课教师；isbn=课号/学分；stock=可申请更正
CREATE TABLE IF NOT EXISTS course_item (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  title VARCHAR(200) NOT NULL,
  teacher_name VARCHAR(100),
  course_code VARCHAR(255),
  category_id BIGINT,
  stock INT DEFAULT 1,
  status VARCHAR(32) DEFAULT 'available',
  cover_url VARCHAR(255),
  stage VARCHAR(32) DEFAULT '已结课',
  tags VARCHAR(255) DEFAULT '',
  lead_source VARCHAR(64) DEFAULT '',
  payment_plan VARCHAR(255) DEFAULT '',
  location_desc VARCHAR(255) DEFAULT '',
  fund_form VARCHAR(32) DEFAULT '',
  expire_on VARCHAR(32) DEFAULT '',
  hire_dept VARCHAR(64) DEFAULT '',
  price_history VARCHAR(255) DEFAULT '',
  vr_url VARCHAR(255) DEFAULT '',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- book_id=course_item.id
CREATE TABLE IF NOT EXISTS grade_apply (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  course_item_id BIGINT NOT NULL,
  username VARCHAR(64) NOT NULL,
  status VARCHAR(32) NOT NULL DEFAULT 'pending',
  assignee_username VARCHAR(64) NULL,
  apply_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  approve_at DATETIME NULL,
  return_at DATETIME NULL,
  remark VARCHAR(512),
  contact_channel VARCHAR(32) DEFAULT '',
  next_follow_at DATETIME NULL,
  notice_ack TINYINT NOT NULL DEFAULT 0,
  rank_scope VARCHAR(16) DEFAULT ''
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
  pinned TINYINT NOT NULL DEFAULT 0,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO sys_user (username, password, role, nickname, phone, profile_json, super_admin, profile_editable, enabled) VALUES
('admin', 'admin123', 'admin', '教务主管', '13800000000', '{}', 1, 0, 1),
('subadmin', 'sub123', 'admin', '教务员', '13800000001', '{}', 0, 1, 1),
('user', 'user123', 'user', '学生甲', '13800000002',
 '{"realName":"王同学","email":"wang@demo.edu","gender":"女","studentNo":"S20260002","dept":"计算机学院"}',
 0, 1, 1)
ON DUPLICATE KEY UPDATE nickname=VALUES(nickname), phone=VALUES(phone), profile_json=VALUES(profile_json);

INSERT IGNORE INTO category (id, name) VALUES (1, '专业必修'), (2, '公共必修'), (3, '选修');
INSERT IGNORE INTO course_item (id, title, teacher_name, course_code, category_id, stock, status) VALUES
(1, '数据结构', '张老师', 'CS2101 / 3学分 / S20260002', 1, 1, 'available'),
(2, '大学英语', '李老师', 'EN1002 / 2学分 / S20269999', 2, 1, 'available'),
(3, '软件工程导论', '赵老师', 'SE3001 / 3学分 / S20260002', 1, 1, 'available'),
(4, '线性代数', '陈老师', 'MA1203 / 3学分 / S20269999', 2, 1, 'available'),
(5, 'Python 程序设计', '周老师', 'CS1050 / 2学分 / S20260002', 3, 1, 'available');
INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '成绩须知', '请优先选择本人相关课程（预置课程按学号标注）；成绩更正与补考由教务审核。', 'admin', '教务主管'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='成绩须知');
INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '补考安排', '补考名单以教务公告为准，请按时提交申请。', 'admin', '教务主管'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='补考安排');

CREATE TABLE IF NOT EXISTS `grade_apply_progress` (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  ticket_id BIGINT NOT NULL,
  status VARCHAR(32) NOT NULL,
  operator VARCHAR(64),
  remark VARCHAR(255) DEFAULT '',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  KEY idx_progress_ticket (ticket_id, id)
);

CREATE TABLE IF NOT EXISTS grade_term (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  name VARCHAR(64) NOT NULL UNIQUE
);
CREATE TABLE IF NOT EXISTS grade_score (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  username VARCHAR(64) NOT NULL,
  course_id BIGINT NOT NULL,
  term_id BIGINT NOT NULL,
  score DECIMAL(5,2) NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  KEY idx_grade_user (username)
);
CREATE TABLE IF NOT EXISTS grade_apply_attach (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  ticket_id BIGINT NOT NULL,
  file_url VARCHAR(255) DEFAULT ''
);
CREATE TABLE IF NOT EXISTS grade_score_history (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  score_id BIGINT NOT NULL,
  username VARCHAR(64) NOT NULL DEFAULT '',
  course_id BIGINT NULL,
  term_id BIGINT NULL,
  old_score DECIMAL(5,2) NULL,
  new_score DECIMAL(5,2) NULL,
  action VARCHAR(16) NOT NULL DEFAULT 'update',
  operator VARCHAR(64) NOT NULL DEFAULT '',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  KEY idx_grade_history_score (score_id)
);
INSERT IGNORE INTO grade_term (id, name) VALUES (1, '2025-2026-1');
INSERT IGNORE INTO grade_score (id, username, course_id, term_id, score) VALUES
(1, 'user', 1, 1, 86.00),
(2, 'user', 3, 1, 91.50),
(3, 'peer', 1, 1, 92.00);

-- staff posts (clerk / worker)
UPDATE sys_user SET staff_post='', staff_kind='' WHERE super_admin=1;
INSERT INTO sys_user (username, password, role, nickname, phone, profile_json, super_admin, profile_editable, enabled, staff_post, staff_kind) VALUES ('subadmin', 'sub123', 'admin', '教务员', '13800000001', '{}', 0, 1, 1, 'grade_clerk', 'clerk') ON DUPLICATE KEY UPDATE nickname=VALUES(nickname), staff_post=VALUES(staff_post), staff_kind=VALUES(staff_kind), role='admin', super_admin=0;
