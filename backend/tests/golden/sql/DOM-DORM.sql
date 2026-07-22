-- bake domain=DOM-DORM · tables in [6,15]
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

CREATE TABLE IF NOT EXISTS dorm_building (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  name VARCHAR(64) NOT NULL UNIQUE,
  remark VARCHAR(128) DEFAULT ''
);

CREATE TABLE IF NOT EXISTS dorm_room (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  building_id BIGINT NOT NULL,
  code VARCHAR(32) NOT NULL,
  capacity INT DEFAULT 4,
  UNIQUE KEY uk_building_code (building_id, code)
);

CREATE TABLE IF NOT EXISTS repair_type (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  name VARCHAR(64) NOT NULL UNIQUE,
  sort_no INT DEFAULT 0
);

CREATE TABLE IF NOT EXISTS repair (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  username VARCHAR(64) NOT NULL,
  title VARCHAR(200) NOT NULL,
  location VARCHAR(128) DEFAULT '',
  type_id BIGINT NULL,
  room_id BIGINT NULL,
  status VARCHAR(32) NOT NULL DEFAULT 'pending',
  priority VARCHAR(16) DEFAULT '普通',
  contact_phone VARCHAR(20) DEFAULT '',
  assignee_username VARCHAR(64) NULL,
  apply_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  approve_at DATETIME NULL,
  return_at DATETIME NULL,
  remark VARCHAR(512) DEFAULT ''
);

CREATE TABLE IF NOT EXISTS repair_progress (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  ticket_id BIGINT NOT NULL,
  status VARCHAR(32) NOT NULL,
  operator VARCHAR(64),
  remark VARCHAR(255) DEFAULT '',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS repair_attach (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  ticket_id BIGINT NOT NULL,
  file_url VARCHAR(255) NOT NULL,
  file_name VARCHAR(128) DEFAULT '',
  uploaded_by VARCHAR(64),
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
('admin', 'admin123', 'admin', '宿管', '13800000000', '{}', 1, 0, 1),
('subadmin', 'sub123', 'admin', '楼管', '13800000001', '{}', 0, 1, 1),
('student', 'student123', 'student', '学生甲', '13800000002',
 '{"realName":"李华","email":"lihua@demo.edu","gender":"男","studentNo":"2023010101","college":"计算机学院","className":"计科2301","grade":"2023级","dormBuilding":"一号楼","dormRoom":"101","bedNo":"1"}',
 0, 1, 1)
ON DUPLICATE KEY UPDATE nickname=VALUES(nickname), phone=VALUES(phone), profile_json=VALUES(profile_json);

INSERT IGNORE INTO dorm_building (id, name) VALUES (1, '一号楼'), (2, '二号楼');
INSERT IGNORE INTO dorm_room (id, building_id, code) VALUES (1, 1, '101'), (2, 1, '102'), (3, 2, '201');
INSERT IGNORE INTO repair_type (id, name, sort_no) VALUES (1, '水电', 1), (2, '门窗', 2), (3, '家具', 3);

INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '报修须知', '请如实填写宿舍与故障描述，宿管将尽快受理。', 'admin', '宿管'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='报修须知');

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
UPDATE sys_user SET staff_post='dorm_mgr', staff_kind='clerk', nickname='楼管' WHERE username='subadmin' AND role='admin' AND IFNULL(super_admin,0)=0;
INSERT INTO sys_user (username, password, role, nickname, phone, profile_json, super_admin, profile_editable, enabled, staff_post, staff_kind) VALUES ('repairer', 'repairer123', 'admin', '维修员', '13800000010', '{}', 0, 1, 1, 'repairer', 'worker') ON DUPLICATE KEY UPDATE nickname=VALUES(nickname), staff_post=VALUES(staff_post), staff_kind=VALUES(staff_kind), role='admin', super_admin=0;
