-- bake domain=DOM-COURSE · tables in [6,15]
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

-- ArchiveStore 兼容列；stock=剩余名额；isbn=课号/教室；start/end 供选课冲突；mutex_code 互斥组
CREATE TABLE IF NOT EXISTS course (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  title VARCHAR(200) NOT NULL,
  teacher VARCHAR(100),
  course_code VARCHAR(128),
  category_id BIGINT,
  stock INT DEFAULT 0,
  status VARCHAR(32) DEFAULT 'available',
  cover_url VARCHAR(255),
  mutex_code VARCHAR(32) NOT NULL DEFAULT '',
  start_at DATETIME NULL,
  end_at DATETIME NULL,
  apply_deadline_at DATETIME NULL,
  credit DECIMAL(3,1) DEFAULT 0,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- book_id=course.id
CREATE TABLE IF NOT EXISTS enrollment (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  course_id BIGINT NOT NULL,
  username VARCHAR(64) NOT NULL,
  status VARCHAR(32) NOT NULL DEFAULT 'pending',
  assignee_username VARCHAR(64) NULL,
  apply_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  approve_at DATETIME NULL,
  return_at DATETIME NULL,
  remark VARCHAR(255)
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
('admin', 'admin123', 'admin', '教务主管', '13800000000', '{}', 1, 0, 1),
('subadmin', 'sub123', 'admin', '选课管理员', '13800000001', '{}', 0, 1, 1),
('student', 'student123', 'student', '学生甲', '13800000002',
 '{"realName":"赵同学","email":"zhao@demo.edu","gender":"男","studentNo":"2026123456","college":"计算机学院","major":"软件工程","className":"软工2301","grade":"2023"}',
 0, 1, 1)
ON DUPLICATE KEY UPDATE nickname=VALUES(nickname), phone=VALUES(phone), profile_json=VALUES(profile_json);

INSERT IGNORE INTO category (id, name) VALUES (1, '人文素养'), (2, '艺术审美'), (3, '创新创业');
-- 1 与 4 时段重叠；2 与 3 同互斥码 MX-ELECTIVE；分类限额默认每类 1 门（schema categoryLimit）
INSERT IGNORE INTO course (id, title, teacher, course_code, category_id, stock, status, mutex_code, start_at, end_at, apply_deadline_at) VALUES
(1, '中国古典诗词鉴赏', '张老师', 'GX2301 / 文楼 301', 1, 60, 'available', '', '2026-09-10 14:00:00', '2026-09-10 15:40:00', '2026-09-08 23:59:59'),
(2, '摄影基础与构图', '李老师', 'GX2302 / 艺术楼 102', 2, 40, 'available', 'MX-ELECTIVE', '2026-09-11 10:00:00', '2026-09-11 11:40:00', '2026-09-08 23:59:59'),
(3, '大学生创新创业导论', '王老师', 'GX2303 / 经管楼 205', 3, 80, 'available', 'MX-ELECTIVE', '2026-09-12 19:00:00', '2026-09-12 20:40:00', '2026-09-08 23:59:59'),
(4, '影视作品赏析', '陈老师', 'GX2304 / 文楼 502', 2, 50, 'available', '', '2026-09-10 15:00:00', '2026-09-10 16:40:00', '2026-09-08 23:59:59'),
(5, '批判性思维训练', '刘老师', 'GX2305 / 文楼 208', 1, 45, 'available', '', '2026-09-13 08:00:00', '2026-09-13 09:40:00', '2026-09-08 23:59:59');
INSERT IGNORE INTO sys_config (cfg_key, cfg_value, remark) VALUES
('max_enrollment', '3', '每人同时选课上限提示'),
('category_limit', '1', '每分类最多门数（与运行时 ticket-category-limit 一致）'),
('enroll_hint', '审核通过占名额；互斥码相同不可同选', '选课说明');
INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '选课须知', '请在开放时段内选课；名额有限，审核通过后请按时上课。', 'admin', '教务主管'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='选课须知');
INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '本学期开放', '公选课已开放申请，请登录系统选课。', 'admin', '教务主管'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='本学期开放');

CREATE TABLE IF NOT EXISTS `enrollment_progress` (
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
UPDATE sys_user SET staff_post='course_clerk', staff_kind='clerk', nickname='选课管理员' WHERE username='subadmin' AND role='admin' AND IFNULL(super_admin,0)=0;
