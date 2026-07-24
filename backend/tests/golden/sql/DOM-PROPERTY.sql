-- bake domain=DOM-PROPERTY · tables in [6,15]
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

CREATE TABLE IF NOT EXISTS building (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  name VARCHAR(64) NOT NULL UNIQUE,
  remark VARCHAR(128) DEFAULT ''
);

CREATE TABLE IF NOT EXISTS room (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  building_id BIGINT NOT NULL,
  code VARCHAR(32) NOT NULL,
  capacity INT DEFAULT 4,
  UNIQUE KEY uk_building_code (building_id, code)
);

CREATE TABLE IF NOT EXISTS ticket_type (
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
  priority VARCHAR(16) DEFAULT '普通',
  contact_phone VARCHAR(20) DEFAULT '',
  assignee_username VARCHAR(64) NULL,
  apply_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  approve_at DATETIME NULL,
  return_at DATETIME NULL,
  remark VARCHAR(512) DEFAULT '',
  attach_url VARCHAR(255) NOT NULL DEFAULT '',
  rating INT NULL,
  rating_remark VARCHAR(255) NOT NULL DEFAULT '',
  rated_at DATETIME NULL,
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
('admin', 'admin123', 'admin', '物业管理员', '13800000000', '{}', 1, 0, 1),
('subadmin', 'sub123', 'admin', '维修员', '13800000001', '{}', 0, 1, 1),
('user', 'user123', 'user', '业主甲', '13800000002',
 '{"realName":"张业主","email":"owner@demo.com","gender":"女","houseBuilding":"A栋","houseUnit":"1","houseNo":"101","ownerType":"业主","parkingNo":"B-12","emergencyContact":"张先生","emergencyPhone":"13900000002"}',
 0, 1, 1)
ON DUPLICATE KEY UPDATE nickname=VALUES(nickname), phone=VALUES(phone), profile_json=VALUES(profile_json);

INSERT IGNORE INTO building (id, name) VALUES (1, 'A 栋'), (2, 'B 栋');
INSERT IGNORE INTO room (id, building_id, code) VALUES (1, 1, '101'), (2, 1, '102'), (3, 2, '201');
INSERT IGNORE INTO ticket_type (id, name, sort_no) VALUES (1, '水电', 1), (2, '公共设施', 2), (3, '门禁', 3);

INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '报修须知', '请填写楼栋房号与故障描述，物业将尽快受理。', 'admin', '物业管理员'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='报修须知');

-- staff posts (clerk / worker)
UPDATE sys_user SET staff_post='', staff_kind='' WHERE super_admin=1;
UPDATE sys_user SET staff_post='dispatcher', staff_kind='clerk', nickname='物业调度' WHERE username='subadmin' AND role='admin' AND IFNULL(super_admin,0)=0;
