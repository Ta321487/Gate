-- bake domain=DOM-INSTRUMENT · tables in [${TABLE_COUNT_MIN},${TABLE_COUNT_MAX}]
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

CREATE TABLE IF NOT EXISTS instrument (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  title VARCHAR(200) NOT NULL,
  author VARCHAR(100),
  isbn VARCHAR(256),
  category_id BIGINT,
  stock INT DEFAULT 1,
  status VARCHAR(32) DEFAULT 'available',
  cover_url VARCHAR(255),
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS instrument_loan (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  book_id BIGINT NOT NULL,
  username VARCHAR(64) NOT NULL,
  status VARCHAR(32) NOT NULL DEFAULT 'pending',
  assignee_username VARCHAR(64) NULL,
  apply_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  approve_at DATETIME NULL,
  due_at DATETIME NULL,
  return_at DATETIME NULL,
  qty INT NOT NULL DEFAULT 1,
  fine_yuan DECIMAL(10,2) NOT NULL DEFAULT 0,
  fine_status VARCHAR(16) DEFAULT 'none',
  reminded_at DATETIME NULL,
  remind_msg VARCHAR(255) DEFAULT '',
  remark VARCHAR(512),
  contact_channel VARCHAR(32) DEFAULT '',
  next_follow_at DATETIME NULL
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

CREATE TABLE IF NOT EXISTS instrument_loan_log (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  instrument_loan_id BIGINT NOT NULL,
  action VARCHAR(32) NOT NULL,
  operator VARCHAR(64),
  remark VARCHAR(255) DEFAULT '',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO sys_user (username, password, role, nickname, phone, profile_json, super_admin, profile_editable, enabled) VALUES
('admin', 'admin123', 'admin', '平台主管', '13800000000', '{}', 1, 0, 1),
('subadmin', 'sub123', 'admin', '仪器管理员', '13800000001', '{}', 0, 1, 1),
('user', 'user123', 'user', '使用人甲', '13800000002',
 '{"realName":"李同学","email":"li@demo.edu","gender":"男","studentNo":"20230001","dept":"化学学院"}',
 0, 1, 1)
ON DUPLICATE KEY UPDATE nickname=VALUES(nickname), phone=VALUES(phone), profile_json=VALUES(profile_json);

INSERT IGNORE INTO category (id, name) VALUES (1, '光谱分析'), (2, '显微表征'), (3, '色谱质谱');
INSERT IGNORE INTO instrument (id, title, author, isbn, category_id, stock, status) VALUES
(1, '核磁共振波谱仪', '分析测试中心', '400MHz', 1, 1, 'available'),
(2, '扫描电子显微镜', '材料学院', '含能谱 SEM', 2, 1, 'available'),
(3, '气相色谱质谱联用', '化学学院', 'GC-MS', 3, 1, 'available');
INSERT IGNORE INTO resource_slot (id, item_id, start_at, end_at, capacity, booked) VALUES
(1, 1, '2026-09-20 09:00:00', '2026-09-20 11:00:00', 1, 0),
(2, 1, '2026-09-20 13:00:00', '2026-09-20 15:00:00', 1, 0),
(3, 1, '2026-09-20 15:00:00', '2026-09-20 17:00:00', 1, 0),
(4, 2, '2026-09-20 09:00:00', '2026-09-20 11:00:00', 1, 0),
(5, 2, '2026-09-20 13:00:00', '2026-09-20 15:00:00', 1, 0),
(6, 2, '2026-09-20 15:00:00', '2026-09-20 17:00:00', 1, 0),
(7, 3, '2026-09-20 09:00:00', '2026-09-20 11:00:00', 1, 0),
(8, 3, '2026-09-20 13:00:00', '2026-09-20 15:00:00', 1, 0),
(9, 3, '2026-09-20 15:00:00', '2026-09-20 17:00:00', 1, 0);
INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '仪器机时须知', '请先预约机时再上机；外带仪器须另提借用申请。', 'admin', '平台主管'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='仪器机时须知');
