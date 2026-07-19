-- bake domain=DOM-IT · tables in [${TABLE_COUNT_MIN},${TABLE_COUNT_MAX}]
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

CREATE TABLE IF NOT EXISTS campus_zone (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  name VARCHAR(64) NOT NULL UNIQUE,
  remark VARCHAR(128) DEFAULT ''
);

CREATE TABLE IF NOT EXISTS endpoint (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  building_id BIGINT NOT NULL,
  code VARCHAR(32) NOT NULL,
  capacity INT DEFAULT 4,
  UNIQUE KEY uk_building_code (building_id, code)
);

CREATE TABLE IF NOT EXISTS fault_type (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  name VARCHAR(64) NOT NULL UNIQUE,
  sort_no INT DEFAULT 0
);

CREATE TABLE IF NOT EXISTS ticket (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  username VARCHAR(64) NOT NULL,
  title VARCHAR(200) NOT NULL,
  location VARCHAR(128) DEFAULT '',
  type_id BIGINT NULL,
  room_id BIGINT NULL,
  status VARCHAR(32) NOT NULL DEFAULT 'pending',
  assignee_username VARCHAR(64) NULL,
  apply_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  approve_at DATETIME NULL,
  return_at DATETIME NULL,
  remark VARCHAR(512) DEFAULT ''
);

CREATE TABLE IF NOT EXISTS ticket_progress (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  ticket_id BIGINT NOT NULL,
  status VARCHAR(32) NOT NULL,
  operator VARCHAR(64),
  remark VARCHAR(255) DEFAULT '',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS ticket_attach (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  ticket_id BIGINT NOT NULL,
  file_url VARCHAR(255) NOT NULL,
  file_name VARCHAR(128) DEFAULT '',
  uploaded_by VARCHAR(64),
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
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
('admin', 'admin123', 'admin', '运维管理员', '13800000000', '{}', 1, 0, 1),
('subadmin', 'sub123', 'admin', '值班员', '13800000001', '{}', 0, 1, 1),
('user', 'user123', 'user', '师生甲', '13800000002',
 '{"realName":"陈同学","email":"chen@demo.edu","gender":"男","identityType":"学生","campusNo":"2023010888","dept":"计算机学院","officeOrDorm":"宿舍区201","title":"2023级"}',
 0, 1, 1)
ON DUPLICATE KEY UPDATE nickname=VALUES(nickname), phone=VALUES(phone), profile_json=VALUES(profile_json);

INSERT IGNORE INTO campus_zone (id, name) VALUES (1, '教学区'), (2, '宿舍区');
INSERT IGNORE INTO endpoint (id, building_id, code) VALUES (1, 1, '101'), (2, 1, '102'), (3, 2, '201');
INSERT IGNORE INTO fault_type (id, name, sort_no) VALUES (1, '校园网', 1), (2, '终端', 2), (3, '机房', 3);

INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '报修须知', '请描述网络/终端故障现象，运维将尽快受理。', 'admin', '运维管理员'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='报修须知');
