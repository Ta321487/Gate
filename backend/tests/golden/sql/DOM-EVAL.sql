-- bake domain=DOM-EVAL · tables in [6,15]
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

CREATE TABLE IF NOT EXISTS eval_course (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  title VARCHAR(200) NOT NULL,
  lecturer_name VARCHAR(100),
  course_note VARCHAR(255),
  category_id BIGINT,
  stock INT DEFAULT 1,
  status VARCHAR(32) DEFAULT 'available',
  cover_url VARCHAR(255),
  stage VARCHAR(32) DEFAULT '开放',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS eval_sheet (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  eval_course_id BIGINT NOT NULL,
  username VARCHAR(64) NOT NULL,
  status VARCHAR(32) NOT NULL DEFAULT 'pending',
  assignee_username VARCHAR(64) NULL,
  apply_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  approve_at DATETIME NULL,
  return_at DATETIME NULL,
  remark VARCHAR(512),
  contact_channel VARCHAR(32) DEFAULT '',
  next_follow_at DATETIME NULL,
  rating INT NULL,
  rating_remark VARCHAR(255) DEFAULT '',
  rated_at DATETIME NULL,
  rating_dims_json VARCHAR(1024) DEFAULT '',
  rating_anonymous TINYINT NOT NULL DEFAULT 0
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

INSERT INTO sys_user (username, password, role, nickname, phone, profile_json, super_admin, profile_editable, enabled) VALUES
('admin', 'admin123', 'admin', '教务主管', '13800000000', '{}', 1, 0, 1),
('user', 'user123', 'user', '学生甲', '13800000002',
 '{"realName":"样例学生","email":"stu@demo.edu","gender":"男","studentNo":"20230001","dept":"计算机学院"}',
 0, 1, 1)
ON DUPLICATE KEY UPDATE nickname=VALUES(nickname), phone=VALUES(phone), profile_json=VALUES(profile_json);

INSERT IGNORE INTO category (id, name) VALUES (1, '公共课'), (2, '专业课'), (3, '实验课');
INSERT IGNORE INTO eval_course (id, title, lecturer_name, course_note, category_id, stock, status) VALUES
(1, '高等数学A', '张老师', '2025 秋 / 公共课', 1, 1, 'available'),
(2, '程序设计基础', '李老师', '2025 秋 / 专业课', 2, 1, 'available'),
(3, '大学英语', '王老师', '2025 秋 / 公共课', 3, 1, 'available'),
(4, '电路实验', '赵老师', '2025 秋 / 实验课', 1, 1, 'available'),
(5, '形势与政策', '陈老师', '2025 秋 / 公共课', 2, 1, 'available');
INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '评教卷须知', '请如实按维度评分并填写评语；提交后即时入档。', 'admin', '教务主管'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='评教卷须知');

CREATE TABLE IF NOT EXISTS `eval_sheet_progress` (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  ticket_id BIGINT NOT NULL,
  status VARCHAR(32) NOT NULL,
  operator VARCHAR(64),
  remark VARCHAR(255) DEFAULT '',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  KEY idx_progress_ticket (ticket_id, id)
);
