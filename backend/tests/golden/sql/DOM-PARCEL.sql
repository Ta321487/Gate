-- bake domain=DOM-PARCEL · tables in [6,15]
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

-- ArchiveStore 兼容列；author=站点；isbn=取件码/柜号；stock=可取件
CREATE TABLE IF NOT EXISTS parcel (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  title VARCHAR(200) NOT NULL,
  station_name VARCHAR(100),
  pickup_code VARCHAR(255),
  category_id BIGINT,
  stock INT DEFAULT 1,
  status VARCHAR(32) DEFAULT 'available',
  cover_url VARCHAR(255),
  stage VARCHAR(32) DEFAULT '待取',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- book_id=parcel.id
CREATE TABLE IF NOT EXISTS parcel_claim (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  parcel_id BIGINT NOT NULL,
  username VARCHAR(64) NOT NULL,
  status VARCHAR(32) NOT NULL DEFAULT 'pending',
  assignee_username VARCHAR(64) NULL,
  apply_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  approve_at DATETIME NULL,
  return_at DATETIME NULL,
  fine_status VARCHAR(16) DEFAULT 'none',
  remark VARCHAR(255),
  pickup_at DATETIME NULL,
  pickup_place VARCHAR(128) DEFAULT '',
  rating INT NULL,
  rating_remark VARCHAR(255) NOT NULL DEFAULT '',
  rated_at DATETIME NULL,
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
('admin', 'admin123', 'admin', '驿站主管', '13800000000', '{}', 1, 0, 1),
('subadmin', 'sub123', 'admin', '驿站店员', '13800000001', '{}', 0, 1, 1),
('user', 'user123', 'user', '取件人甲', '13800000002',
 '{"realName":"刘同学","email":"liu@demo.edu","gender":"男","campusNo":"S20260101","dept":"计算机学院","contactWechat":"liu_demo","usualPlace":"东门驿站"}',
 0, 1, 1)
ON DUPLICATE KEY UPDATE nickname=VALUES(nickname), phone=VALUES(phone), profile_json=VALUES(profile_json);

INSERT IGNORE INTO category (id, name) VALUES (1, '普通件'), (2, '生鲜件'), (3, '大件');
INSERT IGNORE INTO parcel (id, title, station_name, pickup_code, category_id, stock, status) VALUES
(1, '圆通YT8821001', '东门驿站', '取件码 3182 / A12 柜', 1, 1, 'available'),
(2, '中通ZT9912002', '东门驿站', '取件码 5521 / 冷藏区', 2, 1, 'available'),
(3, '顺丰SF1003003', '南区代收点', '取件码 7740 / 大件区', 3, 1, 'available'),
(4, '韵达YD2204004', '东门驿站', '取件码 1098 / B03 柜', 1, 1, 'available'),
(5, '极兔JT3305005', '东门驿站', '取件码 6644 / A08 柜', 1, 1, 'available');
INSERT IGNORE INTO sys_config (cfg_key, cfg_value, remark) VALUES
('claim_hint', '核验取件码与手机尾号', '取件说明'),
('pickup_place', '东门校园驿站前台', '取件地点');
INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '取件须知', '请凭取件码与本人手机号取件；超时未取将移至逾期架。', 'admin', '驿站主管'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='取件须知');
INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '营业时间', '驿站工作日 8:00-21:00，周末 9:00-20:00。', 'admin', '驿站主管'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='营业时间');

CREATE TABLE IF NOT EXISTS `parcel_claim_progress` (
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
UPDATE sys_user SET staff_post='parcel_clerk', staff_kind='clerk', nickname='驿站店员' WHERE username='subadmin' AND role='admin' AND IFNULL(super_admin,0)=0;
