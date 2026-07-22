-- bake domain=DOM-FOOD · tables in [6,15]
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

CREATE TABLE IF NOT EXISTS dish (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  title VARCHAR(200) NOT NULL,
  author VARCHAR(100),
  isbn VARCHAR(128),
  category_id BIGINT,
  stock INT DEFAULT 0,
  status VARCHAR(32) DEFAULT 'available',
  cover_url VARCHAR(255),
  spicy_level VARCHAR(16) DEFAULT '不辣',
  is_vegetarian TINYINT DEFAULT 0,
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
('subadmin', 'sub123', 'admin', '业务管理员', '13800000001', '{}', 0, 1, 1),
('user', 'user123', 'user', '用餐者甲', '13800000002',
 '{"realName":"李同学","email":"li@demo.edu","gender":"女","studentNo":"20260002","college":"经管学院"}',
 0, 1, 1)
ON DUPLICATE KEY UPDATE nickname=VALUES(nickname), phone=VALUES(phone), profile_json=VALUES(profile_json);

INSERT IGNORE INTO category (id, name) VALUES (1, '套餐'), (2, '面食'), (3, '饮品');
INSERT IGNORE INTO dish (id, title, author, isbn, category_id, stock, status) VALUES
(1, '红烧肉套餐', '18.00', '窗口A', 1, 80, 'available'),
(2, '番茄鸡蛋面', '12.00', '窗口B', 2, 60, 'available'),
(3, '豆浆油条', '8.00', '早餐档', 1, 100, 'available'),
(4, '柠檬茶', '6.00', '饮品站', 3, 120, 'available');

INSERT IGNORE INTO user_address (id, username, contact_name, phone, address_line, tag, is_default) VALUES
(1, 'user', '李同学', '13800000002', '示例宿舍 5 号楼 302', '学校', 1),
(2, 'user', '李同学', '13800000002', '创业街 88 号写字楼', '公司', 0),
(3, 'user', '李同学', '13800000002', '阳光小区 3 栋 1201', '家', 0);

INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '点餐须知', '支持堂食/自取/外卖；外卖请选地址并填写口味备注，演示无真支付。', 'admin', '系统管理员'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='点餐须知' OR title='食堂点餐');

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

-- staff posts (clerk / worker)
UPDATE sys_user SET staff_post='', staff_kind='' WHERE super_admin=1;
UPDATE sys_user SET staff_post='counter', staff_kind='clerk', nickname='档口店员' WHERE username='subadmin' AND role='admin' AND IFNULL(super_admin,0)=0;
INSERT INTO sys_user (username, password, role, nickname, phone, profile_json, super_admin, profile_editable, enabled, staff_post, staff_kind) VALUES ('rider', 'rider123', 'admin', '骑手', '13800000010', '{}', 0, 1, 1, 'rider', 'worker') ON DUPLICATE KEY UPDATE nickname=VALUES(nickname), staff_post=VALUES(staff_post), staff_kind=VALUES(staff_kind), role='admin', super_admin=0;
