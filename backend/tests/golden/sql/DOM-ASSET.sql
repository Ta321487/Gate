-- 业务库脚本：建库、建表与初始数据
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
  failed_login_count INT NOT NULL DEFAULT 0,
  lock_until DATETIME NULL,
  must_change_password TINYINT NOT NULL DEFAULT 0,
  password_changed_at DATETIME NULL,
  security_question VARCHAR(128) NULL,
  security_answer_hash VARCHAR(128) NULL,
  email_activated TINYINT NOT NULL DEFAULT 0,
  activation_code VARCHAR(16) NULL,
  real_name_acked TINYINT NOT NULL DEFAULT 0,
  admin_tags VARCHAR(255) NOT NULL DEFAULT '',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS category (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  name VARCHAR(64) NOT NULL UNIQUE
);

-- 列结构与 ArchiveStore 默认 book 表兼容（title/author/isbn/stock）
CREATE TABLE IF NOT EXISTS asset (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  title VARCHAR(200) NOT NULL,
  spec_model VARCHAR(100),
  asset_no VARCHAR(64),
  category_id BIGINT,
  stock INT DEFAULT 0,
  status VARCHAR(32) DEFAULT 'available',
  cover_url VARCHAR(255),
  deleted_at DATETIME NULL,
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

-- book_id 列名兼容 TicketStore archive 模式（存 asset.id）
CREATE TABLE IF NOT EXISTS requisition (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  asset_id BIGINT NOT NULL,
  username VARCHAR(64) NOT NULL,
  status VARCHAR(32) NOT NULL DEFAULT 'pending',
  assignee_username VARCHAR(64) NULL,
  apply_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  approve_at DATETIME NULL,
  return_at DATETIME NULL,
  qty INT NOT NULL DEFAULT 1,
  remark VARCHAR(255),
  pickup_at DATETIME NULL,
  pickup_place VARCHAR(128) DEFAULT '',
  actual_qty INT NULL,
  project_no VARCHAR(64) DEFAULT '',
  procure_ref_no VARCHAR(64) DEFAULT '',
  dual_reviewer_a VARCHAR(64) DEFAULT '',
  dual_reviewer_b VARCHAR(64) DEFAULT ''
);

CREATE TABLE IF NOT EXISTS sys_message (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  username VARCHAR(64) NOT NULL,
  title VARCHAR(128) NOT NULL,
  body VARCHAR(512) DEFAULT '',
  ref_type VARCHAR(32) DEFAULT '',
  ref_id BIGINT NULL,
  read_at DATETIME NULL,
  deleted_at DATETIME NULL,
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
  expire_at DATETIME NULL,
  force_ack TINYINT NOT NULL DEFAULT 0,
  content_fmt VARCHAR(16) NOT NULL DEFAULT 'text',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO sys_user (username, password, role, nickname, phone, profile_json, super_admin, profile_editable, enabled) VALUES
('admin', 'admin123', 'admin', '仓管主管', '13800000000', '{}', 1, 0, 1),
('subadmin', 'sub123', 'admin', '库管员', '13800000001', '{}', 0, 1, 1),
('user', 'user123', 'user', '申领人甲', '13800000002',
 '{"realName":"张工","email":"zhang@demo.com","gender":"男","identityType":"员工","employeeNo":"E20230018","dept":"行政办公室","jobTitle":"科员","officeLoc":"行政楼 205"}',
 0, 1, 1)
ON DUPLICATE KEY UPDATE nickname=VALUES(nickname), phone=VALUES(phone), profile_json=VALUES(profile_json);

INSERT IGNORE INTO category (id, name) VALUES
(1, '办公耗材'), (2, '固定资产'), (3, '劳保用品'), (4, '实验试剂');
INSERT IGNORE INTO asset (id, title, spec_model, asset_no, category_id, stock, status) VALUES
(1, 'A4 复印纸', '70g / 500 张', 'AS-PAPER-001', 1, 40, 'available'),
(2, '台式办公电脑', '联想启天 / i5', 'AS-PC-002', 2, 3, 'available'),
(3, '安全帽', 'ABS 黄色', 'AS-PPE-003', 3, 20, 'available'),
(4, '签字笔盒装', '0.5mm 黑色 / 12 支', 'AS-PEN-004', 1, 25, 'available'),
(5, '移动硬盘', '1TB USB3.0', 'AS-HDD-005', 2, 2, 'available'),
(6, '乙醇分析纯', '500ml / 危化品柜', 'AS-CHEM-006', 4, 8, 'available');
INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '领用须知', '请按需申领、如实填写用途；固定资产领用后请妥善保管，耗材/试剂出库不退；准入许可另走安全准入域。', 'admin', '仓管主管'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='领用须知');
INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '本周盘点', '周五下午库房盘点，请提前完成申领。', 'admin', '仓管主管'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='本周盘点');

CREATE TABLE IF NOT EXISTS `requisition_progress` (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  ticket_id BIGINT NOT NULL,
  status VARCHAR(32) NOT NULL,
  operator VARCHAR(64),
  remark VARCHAR(255) DEFAULT '',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  KEY idx_progress_ticket (ticket_id, id)
);

-- 会话登记、登录记录、注销申请
CREATE TABLE IF NOT EXISTS sys_auth_session (
  session_id VARCHAR(128) NOT NULL,
  username VARCHAR(64) NOT NULL,
  ip VARCHAR(64) NOT NULL DEFAULT '',
  user_agent VARCHAR(255) NOT NULL DEFAULT '',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  last_seen_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  kicked TINYINT NOT NULL DEFAULT 0,
  PRIMARY KEY (session_id),
  KEY idx_auth_sess_user (username, kicked)
);

CREATE TABLE IF NOT EXISTS sys_login_log (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  username VARCHAR(64) NOT NULL,
  ip VARCHAR(64) NOT NULL DEFAULT '',
  user_agent VARCHAR(255) NOT NULL DEFAULT '',
  geo_hint VARCHAR(64) NOT NULL DEFAULT '',
  success TINYINT NOT NULL DEFAULT 1,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  KEY idx_login_log_user (username, created_at)
);

CREATE TABLE IF NOT EXISTS sys_account_cancel (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  username VARCHAR(64) NOT NULL,
  reason VARCHAR(255) NOT NULL DEFAULT '',
  status VARCHAR(16) NOT NULL DEFAULT 'pending',
  admin_note VARCHAR(255) NOT NULL DEFAULT '',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  reviewed_at DATETIME NULL,
  KEY idx_cancel_user (username, status)
);
-- 业务试用账号首次登录须改密
UPDATE sys_user SET must_change_password=1 WHERE username='user' AND IFNULL(super_admin,0)=0;
-- 种子账号一律免激活闸（新注册仍走默认未激活）
UPDATE sys_user SET email_activated=1;

-- 强制公告确认 / 广告位多槽
CREATE TABLE IF NOT EXISTS sys_notice_ack (
  notice_id BIGINT NOT NULL,
  username VARCHAR(64) NOT NULL,
  acked_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (notice_id, username),
  KEY idx_notice_ack_user (username)
);

CREATE TABLE IF NOT EXISTS sys_banner (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  slot VARCHAR(32) NOT NULL DEFAULT 'home',
  title VARCHAR(128) NOT NULL DEFAULT '',
  lead_text VARCHAR(255) NOT NULL DEFAULT '',
  image_url VARCHAR(512) NOT NULL DEFAULT '',
  link_url VARCHAR(512) NOT NULL DEFAULT '',
  sort_order INT NOT NULL DEFAULT 0,
  enabled TINYINT NOT NULL DEFAULT 1,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  KEY idx_banner_slot (slot, enabled, sort_order)
);

INSERT INTO sys_banner (slot, title, lead_text, image_url, link_url, sort_order, enabled)
SELECT 'home', '欢迎使用', '系统已就绪，可开始浏览业务入口。', '', '/notices', 0, 1 FROM DUAL
WHERE NOT EXISTS (SELECT 1 FROM sys_banner WHERE slot='home' AND title='欢迎使用');

-- 简易站点访问量（按日）
CREATE TABLE IF NOT EXISTS sys_site_stat (
  day_key VARCHAR(10) NOT NULL,
  pv INT NOT NULL DEFAULT 0,
  PRIMARY KEY (day_key)
);

CREATE TABLE IF NOT EXISTS stock_move (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  move_type VARCHAR(16) NOT NULL,
  item_id BIGINT NOT NULL,
  item_title VARCHAR(200) DEFAULT '',
  qty INT NOT NULL,
  remark VARCHAR(255) DEFAULT '',
  operator VARCHAR(64) NOT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  KEY idx_stock_move_item (item_id, id),
  KEY idx_stock_move_type (move_type, id)
);

CREATE TABLE IF NOT EXISTS stock_location (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  name VARCHAR(100) NOT NULL,
  remark VARCHAR(255) DEFAULT '',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
INSERT IGNORE INTO stock_location (id, name, remark) VALUES (1, '主仓', '单仓演示');

CREATE TABLE IF NOT EXISTS stock_bin (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  location_id BIGINT NOT NULL DEFAULT 1,
  name VARCHAR(64) NOT NULL,
  remark VARCHAR(255) DEFAULT '',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  KEY idx_stock_bin_loc (location_id)
);
INSERT IGNORE INTO stock_bin (id, location_id, name, remark) VALUES (1, 1, '默认货位', '单仓演示');

-- staff posts (clerk / worker)
UPDATE sys_user SET staff_post='', staff_kind='' WHERE super_admin=1;
INSERT INTO sys_user (username, password, role, nickname, phone, profile_json, super_admin, profile_editable, enabled, staff_post, staff_kind) VALUES ('subadmin', 'sub123', 'admin', '库管员', '13800000001', '{}', 0, 1, 1, 'storekeeper', 'clerk') ON DUPLICATE KEY UPDATE nickname=VALUES(nickname), staff_post=VALUES(staff_post), staff_kind=VALUES(staff_kind), role='admin', super_admin=0;

-- 空封面时补默认图（asset）
UPDATE `asset` SET cover_url = ELT(1 + MOD(GREATEST(id, 1) - 1, 8),
  '/uploads/demo/cover-01.jpg',
  '/uploads/demo/cover-02.jpg',
  '/uploads/demo/cover-03.jpg',
  '/uploads/demo/cover-04.jpg',
  '/uploads/demo/cover-05.jpg',
  '/uploads/demo/cover-06.jpg',
  '/uploads/demo/cover-07.jpg',
  '/uploads/demo/cover-08.jpg'
)
WHERE cover_url IS NULL OR TRIM(cover_url) = '';
