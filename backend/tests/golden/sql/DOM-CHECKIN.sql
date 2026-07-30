-- bake domain=DOM-CHECKIN · tables in [6,15]
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

-- ArchiveStore：title=寝室号；author=楼栋；stock=应签人数；checkin_code + 起止窗口
CREATE TABLE IF NOT EXISTS dorm_room (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  title VARCHAR(200) NOT NULL,
  building_name VARCHAR(100),
  room_note VARCHAR(255),
  category_id BIGINT,
  stock INT DEFAULT 0,
  status VARCHAR(32) DEFAULT 'available',
  cover_url VARCHAR(255),
  checkin_code VARCHAR(16) NOT NULL DEFAULT '',
  start_at DATETIME NULL,
  end_at DATETIME NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS checkin_apply (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  dorm_room_id BIGINT NOT NULL,
  username VARCHAR(64) NOT NULL,
  status VARCHAR(32) NOT NULL DEFAULT 'pending',
  assignee_username VARCHAR(64) NULL,
  apply_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  approve_at DATETIME NULL,
  return_at DATETIME NULL,
  remark VARCHAR(512),
  contact_channel VARCHAR(32) DEFAULT '',
  next_follow_at DATETIME NULL,
  checked_in_at DATETIME NULL,
  fine_status VARCHAR(32) DEFAULT ''
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
('admin', 'admin123', 'admin', '宿管主管', '13800000000', '{}', 1, 0, 1),
('subadmin', 'sub123', 'admin', '查寝员', '13800000001', '{}', 0, 1, 1),
('user', 'user123', 'user', '学生甲', '13800000002',
 '{"realName":"样例学生","email":"stu@demo.edu","gender":"男","studentNo":"20230001","dept":"计算机学院"}',
 0, 1, 1)
ON DUPLICATE KEY UPDATE nickname=VALUES(nickname), phone=VALUES(phone), profile_json=VALUES(profile_json);

INSERT IGNORE INTO category (id, name) VALUES (1, '一号楼'), (2, '二号楼'), (3, '集中查寝');
INSERT IGNORE INTO dorm_room (id, title, building_name, room_note, category_id, stock, status, checkin_code, start_at, end_at) VALUES
(1, '1栋101', '1号楼', '四人间 · 晚查', 1, 4, 'available', 'CK101', DATE_ADD(CURDATE(), INTERVAL 22 HOUR), DATE_ADD(CURDATE(), INTERVAL 23 HOUR)),
(2, '1栋102', '1号楼', '四人间 · 晚查', 1, 4, 'available', 'CK102', DATE_ADD(CURDATE(), INTERVAL 22 HOUR), DATE_ADD(CURDATE(), INTERVAL 23 HOUR)),
(3, '2栋205', '2号楼', '六人间 · 晚查', 2, 6, 'available', 'CK205', DATE_ADD(CURDATE(), INTERVAL 22 HOUR), DATE_ADD(CURDATE(), INTERVAL 23 HOUR)),
(4, '集中查寝点', '宿管中心', '临时批次', 3, 30, 'available', 'CK999', DATE_ADD(CURDATE(), INTERVAL 21 HOUR), DATE_ADD(CURDATE(), INTERVAL 23 HOUR));
UPDATE dorm_room SET checkin_code=CONCAT('CK', LPAD(id, 3, '0')) WHERE checkin_code='' OR checkin_code IS NULL;
INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '查寝须知', '请在查寝窗口内完成口令签到；人脸/GPS 不在本期。窗口结束后未签到记缺勤。', 'admin', '宿管主管'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='查寝须知');

CREATE TABLE IF NOT EXISTS `checkin_apply_progress` (
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
UPDATE sys_user SET staff_post='checkin_clerk', staff_kind='clerk', nickname='查寝员' WHERE username='subadmin' AND role='admin' AND IFNULL(super_admin,0)=0;
