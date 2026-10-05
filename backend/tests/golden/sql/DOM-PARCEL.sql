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
  holding_loc VARCHAR(128) DEFAULT '',
  campus_zone VARCHAR(64) DEFAULT '',
  shelf_no VARCHAR(64) DEFAULT '',
  batch_no VARCHAR(64) DEFAULT '',
  expire_on VARCHAR(32) DEFAULT '',
  supplier_contact VARCHAR(64) DEFAULT '',
  allowed_gender VARCHAR(16) DEFAULT '',
  allowed_grades VARCHAR(64) DEFAULT '',
  maintain_due VARCHAR(32) DEFAULT '',
  loan_org VARCHAR(128) DEFAULT '',
  clc_code VARCHAR(32) DEFAULT '',
  calib_cert_url VARCHAR(255) DEFAULT '',
  calib_due VARCHAR(32) DEFAULT '',
  repair_ticket_no VARCHAR(64) DEFAULT '',
  slot_status VARCHAR(16) DEFAULT '',
  building_zone VARCHAR(64) DEFAULT '',
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
  due_at DATETIME NULL,
  return_at DATETIME NULL,
  fine_status VARCHAR(16) DEFAULT 'none',
  remark VARCHAR(255),
  pickup_at DATETIME NULL,
  pickup_place VARCHAR(128) DEFAULT '',
  proxy_name VARCHAR(64) DEFAULT '',
  proxy_phone VARCHAR(20) DEFAULT '',
  exception_reason VARCHAR(128) DEFAULT '',
  damage_claim_note VARCHAR(255) DEFAULT '',
  notice_ack TINYINT NOT NULL DEFAULT 0,
  ship_fee_yuan DECIMAL(10,2) NULL,
  rating INT NULL,
  rating_remark VARCHAR(255) NOT NULL DEFAULT '',
  rated_at DATETIME NULL
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
  pinned TINYINT NOT NULL DEFAULT 0,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO sys_user (username, password, role, nickname, phone, profile_json, super_admin, profile_editable, enabled) VALUES
('admin', 'admin123', 'admin', '驿站主管', '13800000000', '{}', 1, 0, 1),
('subadmin', 'sub123', 'admin', '驿站店员', '13800000001', '{}', 0, 1, 1),
('user', 'user123', 'user', '取件人甲', '13800000002',
 '{"realName":"刘同学","email":"liu@demo.edu","gender":"男","campusNo":"S20260101","dept":"计算机学院","contactWechat":"liu_demo","usualPlace":"东门驿站"}',
 0, 1, 1)
ON DUPLICATE KEY UPDATE nickname=VALUES(nickname), phone=VALUES(phone), profile_json=VALUES(profile_json);

INSERT IGNORE INTO category (id, name) VALUES (1, '普通件'), (2, '生鲜件'), (3, '大件');
INSERT IGNORE INTO parcel (id, title, station_name, pickup_code, category_id, stock, status, stage) VALUES
(1, '圆通YT8821001', '东门驿站', '取件码 3182 / A12 柜 / 13800000002', 1, 1, 'available', '待取'),
(2, '中通ZT9912002', '东门驿站', '取件码 5521 / 冷藏区 / 13800000002', 2, 1, 'available', '待取'),
(3, '顺丰SF1003003', '南区代收点', '取件码 7740 / 大件区 / 13800000099', 3, 1, 'available', '待取'),
(4, '韵达YD2204004', '东门驿站', '取件码 1098 / B03 柜 / 13800000002', 1, 1, 'available', '待取'),
(5, '极兔JT3305005', '东门驿站', '取件码 6644 / A08 柜 / 13800000099', 1, 1, 'available', '待取'),
(6, '申通ST4406006', '东门驿站', '取件码 8821 / 异常架 / 13800000002', 1, 1, 'available', '损坏');
INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '取件须知', '请凭取件码与本人手机号取件；本人件按登录手机号匹配。超时未取将移至逾期架。', 'admin', '驿站主管'
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

CREATE TABLE IF NOT EXISTS parcel_shelf (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  code VARCHAR(32) NOT NULL UNIQUE,
  remark VARCHAR(255) DEFAULT ''
);
CREATE TABLE IF NOT EXISTS parcel_pickup_log (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  ticket_id BIGINT NOT NULL,
  username VARCHAR(64) NOT NULL,
  code_used VARCHAR(32) DEFAULT '',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS parcel_station (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  name VARCHAR(100) NOT NULL,
  address VARCHAR(255) DEFAULT ''
);

-- staff posts (clerk / worker)
UPDATE sys_user SET staff_post='', staff_kind='' WHERE super_admin=1;
INSERT INTO sys_user (username, password, role, nickname, phone, profile_json, super_admin, profile_editable, enabled, staff_post, staff_kind) VALUES ('subadmin', 'sub123', 'admin', '驿站店员', '13800000001', '{}', 0, 1, 1, 'parcel_clerk', 'clerk') ON DUPLICATE KEY UPDATE nickname=VALUES(nickname), staff_post=VALUES(staff_post), staff_kind=VALUES(staff_kind), role='admin', super_admin=0;
