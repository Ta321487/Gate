-- bake domain=DOM-GENERIC · ARCH-TRADE · tables in [6,15]
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

CREATE TABLE IF NOT EXISTS cart_line (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  username VARCHAR(64) NOT NULL,
  item_id BIGINT NOT NULL,
  qty INT NOT NULL DEFAULT 1,
  UNIQUE KEY uk_cart (username, item_id)
);

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
  tracking_no VARCHAR(64) DEFAULT '',
  pickup_code VARCHAR(32) DEFAULT '',
  shipped_at DATETIME NULL,
  reservation_id BIGINT NULL,
  discount_yuan DECIMAL(10,2) NOT NULL DEFAULT 0,
  pay_balance_yuan DECIMAL(10,2) NOT NULL DEFAULT 0,
  points_earned INT NOT NULL DEFAULT 0,
  coupon_code VARCHAR(32) DEFAULT '',
  refund_status VARCHAR(16) DEFAULT '',
  refund_reason VARCHAR(255) DEFAULT '',
  refund_at DATETIME NULL,
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
('subadmin', 'sub123', 'admin', '订单管理员', '13800000001', '{}', 0, 1, 1),
('user', 'user123', 'user', '用户甲', '13800000002',
 '{"realName":"王小明","email":"user@demo.edu","gender":"男","orgName":"信息中心","jobTitle":"职员","employeeNo":"E1001"}',
 0, 1, 1)
ON DUPLICATE KEY UPDATE nickname=VALUES(nickname), phone=VALUES(phone), profile_json=VALUES(profile_json);

INSERT IGNORE INTO category (id, name) VALUES (1, '一类'), (2, '二类'), (3, '三类');
INSERT IGNORE INTO biz_item (id, title, author, isbn, category_id, stock, status) VALUES
(1, '示例商品甲', '29.90', 'SKU-001', 1, 20, 'available'),
(2, '示例商品乙', '59.00', 'SKU-002', 2, 15, 'available'),
(3, '示例商品丙', '12.50', 'SKU-003', 3, 40, 'available');

INSERT IGNORE INTO user_address (id, username, contact_name, phone, address_line, tag, is_default) VALUES
(1, 'user', '王小明', '13800000002', '示例路 100 号 8 栋 501', '家', 1);

INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '交易须知', '演示环境支持购物车、收货地址与多明细订单，无真支付。', 'admin', '系统管理员'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='交易须知');

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

-- staff posts (clerk / worker)
UPDATE sys_user SET staff_post='', staff_kind='' WHERE super_admin=1;
UPDATE sys_user SET staff_post='order_clerk', staff_kind='clerk', nickname='订单办理员' WHERE username='subadmin' AND role='admin' AND IFNULL(super_admin,0)=0;
