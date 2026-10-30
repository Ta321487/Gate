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
  balance_yuan DECIMAL(10,2) NOT NULL DEFAULT 0,
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
  name VARCHAR(64) NOT NULL UNIQUE,
  required_pick TINYINT NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS dish (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  title VARCHAR(200) NOT NULL,
  price_yuan DECIMAL(10,2) NOT NULL DEFAULT 0,
  spec_note VARCHAR(128) DEFAULT '',
  category_id BIGINT,
  stock INT DEFAULT 0,
  status VARCHAR(32) DEFAULT 'available',
  cover_url VARCHAR(255),
  spicy_level VARCHAR(16) DEFAULT '不辣',
  is_vegetarian TINYINT DEFAULT 0,
  open_hours VARCHAR(32) DEFAULT '',
  stall_score DECIMAL(3,1) NOT NULL DEFAULT 5.0,
  deleted_at DATETIME NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS cart_line (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  username VARCHAR(64) NOT NULL,
  item_id BIGINT NOT NULL,
  qty INT NOT NULL DEFAULT 1,
  UNIQUE KEY uk_cart (username, item_id)
);

-- 收货地址簿（外卖配送用；堂食/自取可空）
CREATE TABLE IF NOT EXISTS user_address (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  username VARCHAR(64) NOT NULL,
  contact_name VARCHAR(64) NOT NULL,
  phone VARCHAR(32) NOT NULL,
  address_line VARCHAR(255) NOT NULL,
  tag VARCHAR(32) DEFAULT '默认',
  is_default TINYINT DEFAULT 0,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  KEY idx_addr_user (username)
);

CREATE TABLE IF NOT EXISTS biz_order (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  username VARCHAR(64) NOT NULL,
  status VARCHAR(32) NOT NULL DEFAULT 'pending',
  total_yuan DECIMAL(10,2) NOT NULL DEFAULT 0,
  remark VARCHAR(255) DEFAULT '',
  receiver_name VARCHAR(64) DEFAULT '',
  receiver_phone VARCHAR(32) DEFAULT '',
  address_line VARCHAR(255) DEFAULT '',
  delivery_type VARCHAR(32) DEFAULT '',
  taste_note VARCHAR(255) DEFAULT '',
  pickup_code VARCHAR(32) DEFAULT '',
  table_no VARCHAR(32) DEFAULT '',
  utensil_opt VARCHAR(32) DEFAULT '',
  pack_opt VARCHAR(32) DEFAULT '',
  delivery_fee_yuan DECIMAL(10,2) NOT NULL DEFAULT 0,
  eta_text VARCHAR(64) DEFAULT '',
  merge_code VARCHAR(16) DEFAULT '',
  rider_username VARCHAR(64) DEFAULT '',
  rider_claimed_at DATETIME NULL,
  shipped_at DATETIME NULL,
  refund_status VARCHAR(16) DEFAULT '',
  refund_reason VARCHAR(255) DEFAULT '',
  refund_at DATETIME NULL,
  refund_requested_at DATETIME NULL,
  refund_type VARCHAR(32) DEFAULT '',
  refund_tracking_no VARCHAR(64) DEFAULT '',
  completed_at DATETIME NULL,
  pay_balance_yuan DECIMAL(10,2) NOT NULL DEFAULT 0,
  packaging_fee_yuan DECIMAL(10,2) NOT NULL DEFAULT 0,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS order_line (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  order_id BIGINT NOT NULL,
  item_id BIGINT NOT NULL,
  title VARCHAR(200) NOT NULL,
  price_yuan DECIMAL(10,2) NOT NULL DEFAULT 0,
  qty INT NOT NULL DEFAULT 1
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
('admin', 'admin123', 'admin', '门店主管', '13800000000', '{}', 1, 0, 1),
('subadmin', 'sub123', 'admin', '店员', '13800000001', '{}', 0, 1, 1),
('user', 'user123', 'user', '用餐者甲', '13800000002',
 '{"realName":"李女士","email":"li@demo.com","gender":"女","receiverName":"李女士","pickupType":"堂食","preferredStore":"总店","memberNo":"M20260002"}',
 0, 1, 1)
ON DUPLICATE KEY UPDATE nickname=VALUES(nickname), phone=VALUES(phone), profile_json=VALUES(profile_json);

INSERT IGNORE INTO category (id, name, required_pick) VALUES (1, '套餐', 1), (2, '面食', 0), (3, '饮品', 0);
INSERT IGNORE INTO dish (id, title, price_yuan, spec_note, category_id, stock, status, open_hours, stall_score) VALUES
(1, '红烧肉套餐', '18.00', '总店', 1, 79, 'available', '10:00-21:00', 4.8),
(2, '番茄鸡蛋面', '12.00', '总店', 2, 60, 'available', '10:00-21:00', 4.6),
(3, '豆浆油条', '8.00', '早市档', 1, 100, 'available', '07:00-10:30', 4.5),
(4, '柠檬茶', '6.00', '饮品吧', 3, 120, 'available', '10:00-22:00', 4.7);

INSERT IGNORE INTO user_address (id, username, contact_name, phone, address_line, tag, is_default) VALUES
(1, 'user', '李女士', '13800000002', '示例小区 5 号楼 302', '家', 1),
(2, 'user', '李女士', '13800000002', '创业街 88 号写字楼', '公司', 0),
(3, 'user', '李女士', '13800000002', '阳光广场 B1 美食区', '自取', 0);

INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '点餐须知', '支持堂食/自取/外卖；外卖请选地址并填写口味备注。', 'admin', '门店主管'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='点餐须知');
-- 主路径样例：待出餐订单
INSERT IGNORE INTO biz_order (id, username, status, total_yuan, remark, receiver_name, receiver_phone, address_line, delivery_type, taste_note, created_at, completed_at) VALUES
(1, 'user', 'pending', 18.00, '少油少盐', '李女士', '13800000002', '示例小区 5 号楼 302', '外卖配送', '微辣', DATE_SUB(NOW(), INTERVAL 0 DAY), NULL),
(2, 'user', 'confirmed', 12.00, '尽快送达', '李女士', '13800000002', '示例小区 5 号楼 302', '外卖配送', '少油', DATE_SUB(NOW(), INTERVAL 1 DAY), NULL),
(3, 'user', 'shipped', 8.00, '放门口即可', '李女士', '13800000002', '示例小区 5 号楼 302', '外卖配送', '', DATE_SUB(NOW(), INTERVAL 2 DAY), NULL),
(4, 'user', 'completed', 6.00, '已取', '李女士', '13800000002', '示例小区 5 号楼 302', '外卖配送', '少冰', DATE_SUB(NOW(), INTERVAL 4 DAY), DATE_SUB(NOW(), INTERVAL 3 DAY));
INSERT IGNORE INTO order_line (id, order_id, item_id, title, price_yuan, qty) VALUES
(1, 1, 1, '红烧肉套餐', 18.00, 1),
(2, 2, 2, '番茄鸡蛋面', 12.00, 1),
(3, 3, 3, '豆浆油条', 8.00, 1),
(4, 4, 4, '柠檬茶', 6.00, 1);

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

CREATE TABLE IF NOT EXISTS sys_guestbook (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  username VARCHAR(64) NOT NULL,
  nickname VARCHAR(64) DEFAULT '',
  body VARCHAR(500) NOT NULL,
  reply VARCHAR(500) DEFAULT '',
  reply_username VARCHAR(64) DEFAULT '',
  replied_at DATETIME NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  KEY idx_gb_created (id),
  KEY idx_gb_user (username)
);

CREATE TABLE IF NOT EXISTS user_favorite (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  username VARCHAR(64) NOT NULL,
  item_id BIGINT NOT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uk_fav_user_item (username, item_id),
  KEY idx_fav_user (username, id)
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

CREATE TABLE IF NOT EXISTS order_review (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  order_id BIGINT NOT NULL,
  username VARCHAR(64) NOT NULL,
  rating INT NOT NULL,
  body VARCHAR(500) DEFAULT '',
  reply VARCHAR(500) DEFAULT '',
  replied_at DATETIME NULL,
  image_url VARCHAR(255) DEFAULT '',
  follow_body VARCHAR(500) DEFAULT '',
  follow_at DATETIME NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uk_order_review (order_id),
  KEY idx_review_user (username, id)
);

-- staff posts (clerk / worker)
UPDATE sys_user SET staff_post='', staff_kind='' WHERE super_admin=1;
INSERT INTO sys_user (username, password, role, nickname, phone, profile_json, super_admin, profile_editable, enabled, staff_post, staff_kind) VALUES ('subadmin', 'sub123', 'admin', '店员', '13800000001', '{}', 0, 1, 1, 'counter', 'clerk') ON DUPLICATE KEY UPDATE nickname=VALUES(nickname), staff_post=VALUES(staff_post), staff_kind=VALUES(staff_kind), role='admin', super_admin=0;

-- 空封面时补默认图（dish）
UPDATE `dish` SET cover_url = ELT(1 + MOD(GREATEST(id, 1) - 1, 8),
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
