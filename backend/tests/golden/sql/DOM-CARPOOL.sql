-- bake domain=DOM-CARPOOL · tables in [6,15]
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

CREATE TABLE IF NOT EXISTS trip_route (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  title VARCHAR(200) NOT NULL,
  publisher_name VARCHAR(100),
  route_note VARCHAR(255),
  category_id BIGINT,
  stock INT DEFAULT 3,
  status VARCHAR(32) DEFAULT 'available',
  cover_url VARCHAR(255),
  owner_username VARCHAR(64) NOT NULL DEFAULT '',
  start_at DATETIME NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS carpool_intent (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  trip_route_id BIGINT NOT NULL,
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

INSERT INTO sys_user (username, password, role, nickname, phone, profile_json, super_admin, profile_editable, enabled) VALUES
('admin', 'admin123', 'admin', '拼车主管', '13800000000', '{}', 1, 0, 1),
('subadmin', 'sub123', 'admin', '对接员', '13800000001', '{}', 0, 1, 1),
('peer', 'user123', 'user', '车主甲', '13800000004',
 '{"realName":"王同学","email":"wang@demo.edu","gender":"男","studentNo":"20230001","dept":"交通学院"}',
 0, 1, 1),
('user', 'user123', 'user', '同行者甲', '13800000002',
 '{"realName":"周同学","email":"zhou@demo.edu","gender":"男","studentNo":"20230004","dept":"交通学院"}',
 0, 1, 1)
ON DUPLICATE KEY UPDATE nickname=VALUES(nickname), phone=VALUES(phone), profile_json=VALUES(profile_json);

INSERT IGNORE INTO category (id, name) VALUES (1, '城际'), (2, '返乡'), (3, '市内短途');
INSERT IGNORE INTO trip_route (id, title, publisher_name, route_note, category_id, stock, status, owner_username, start_at) VALUES
(1, '周五晚 学校→火车站', 'peer', '可带行李 / 校门口汇合', 3, 3, 'available', 'peer', '2026-08-08 18:30:00'),
(2, '周六上午 本市→邻市', 'peer', '顺路两座 / 非营运拼车', 1, 2, 'available', 'peer', '2026-08-09 09:00:00'),
(3, '周日下午 返乡方向', 'peer', '同方向可留言对接', 2, 4, 'available', 'peer', '2026-08-10 14:00:00');

INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '拼车须知', '发布行程时填写出发时间与地点备注；他人提交意向由车主确认或婉拒；过出发时间自动下架。本期无地图导航与真支付分账。', 'admin', '拼车主管'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='拼车须知');

CREATE TABLE IF NOT EXISTS `carpool_intent_progress` (
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
INSERT INTO sys_user (username, password, role, nickname, phone, profile_json, super_admin, profile_editable, enabled, staff_post, staff_kind) VALUES ('subadmin', 'sub123', 'admin', '对接员', '13800000001', '{}', 0, 1, 1, 'carpool_clerk', 'clerk') ON DUPLICATE KEY UPDATE nickname=VALUES(nickname), staff_post=VALUES(staff_post), staff_kind=VALUES(staff_kind), role='admin', super_admin=0;
