-- bake domain=DOM-GENERIC · ARCH-RESERVE · tables in [6,15]
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
  balance_yuan DECIMAL(10,2) NOT NULL DEFAULT 0,
  points INT NOT NULL DEFAULT 0,
  member_tier VARCHAR(32) DEFAULT '',
  spend_total_yuan DECIMAL(10,2) NOT NULL DEFAULT 0,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS category (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  name VARCHAR(64) NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS biz_item (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  title VARCHAR(200) NOT NULL,
  author VARCHAR(100),
  isbn VARCHAR(255),
  category_id BIGINT,
  stock INT DEFAULT 0,
  status VARCHAR(32) DEFAULT 'available',
  cover_url VARCHAR(255),
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS resource_slot (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  item_id BIGINT NOT NULL,
  start_at DATETIME NOT NULL,
  end_at DATETIME NOT NULL,
  capacity INT NOT NULL DEFAULT 1,
  booked INT NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS reservation (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  slot_id BIGINT NOT NULL,
  username VARCHAR(64) NOT NULL,
  status VARCHAR(32) NOT NULL DEFAULT 'confirmed',
  remark VARCHAR(255) DEFAULT '',
  plate_no VARCHAR(16) DEFAULT '',
  patient_name VARCHAR(32) DEFAULT '',
  visit_type VARCHAR(16) DEFAULT '',
  symptom_note VARCHAR(255) DEFAULT '',
  subject VARCHAR(128) DEFAULT '',
  party_size INT DEFAULT 0,
  guest_name VARCHAR(32) DEFAULT '',
  guest_count INT DEFAULT 0,
  preferred_stylist VARCHAR(32) DEFAULT '',
  queue_no INT DEFAULT 0,
  entry_at DATETIME NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
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
('admin', 'admin123', 'admin', '系统管理员', '13800000000', '{}', 1, 0, 1),
('subadmin', 'sub123', 'admin', '预约管理员', '13800000001', '{}', 0, 1, 1),
('user', 'user123', 'user', '用户甲', '13800000002',
 '{"realName":"王小明","email":"user@demo.edu","gender":"男","orgName":"信息中心","jobTitle":"职员","employeeNo":"E1001"}',
 0, 1, 1)
ON DUPLICATE KEY UPDATE nickname=VALUES(nickname), phone=VALUES(phone), profile_json=VALUES(profile_json);

INSERT IGNORE INTO category (id, name) VALUES (1, '一类'), (2, '二类'), (3, '三类');
INSERT IGNORE INTO biz_item (id, title, author, isbn, category_id, stock, status) VALUES
(1, '示例资源甲', '0', '位置A', 1, 1, 'available'),
(2, '示例资源乙', '0', '位置B', 2, 1, 'available'),
(3, '示例资源丙', '10.00', '位置C', 3, 1, 'available');

INSERT IGNORE INTO resource_slot (id, item_id, start_at, end_at, capacity, booked) VALUES
(1, 1, '2026-09-20 09:00:00', '2026-09-20 10:00:00', 2, 0),
(2, 1, '2026-09-20 10:00:00', '2026-09-20 11:00:00', 2, 0),
(3, 2, '2026-09-20 14:00:00', '2026-09-20 15:00:00', 1, 0),
(4, 2, '2026-09-20 15:00:00', '2026-09-20 16:00:00', 1, 0),
(5, 3, '2026-09-20 09:00:00', '2026-09-20 10:00:00', 3, 0),
(6, 3, '2026-09-20 10:00:00', '2026-09-20 11:00:00', 3, 0);

INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '预约须知', '选择资源与时段占坑预约；约满后不可再约。', 'admin', '系统管理员'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='预约须知');

CREATE TABLE IF NOT EXISTS user_ledger (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  username VARCHAR(64) NOT NULL,
  kind VARCHAR(16) NOT NULL,
  delta DECIMAL(12,2) NOT NULL,
  balance_after DECIMAL(12,2) NOT NULL DEFAULT 0,
  reason VARCHAR(64) DEFAULT '',
  ref_type VARCHAR(32) DEFAULT '',
  ref_id BIGINT NULL,
  operator VARCHAR(64) DEFAULT '',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  KEY idx_ledger_user (username, id)
);

-- staff posts (clerk / worker)
UPDATE sys_user SET staff_post='', staff_kind='' WHERE super_admin=1;
UPDATE sys_user SET staff_post='booking_clerk', staff_kind='clerk', nickname='预约办理员' WHERE username='subadmin' AND role='admin' AND IFNULL(super_admin,0)=0;
