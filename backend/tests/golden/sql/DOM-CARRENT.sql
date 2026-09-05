-- bake domain=DOM-CARRENT · tables in [6,15]
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

CREATE TABLE IF NOT EXISTS vehicle (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  title VARCHAR(200) NOT NULL,
  price_yuan DECIMAL(10,2) NOT NULL DEFAULT 0,
  vehicle_note VARCHAR(128) DEFAULT '',
  category_id BIGINT,
  stock INT DEFAULT 0,
  status VARCHAR(32) DEFAULT 'available',
  cover_url VARCHAR(255),
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
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
  guest_name VARCHAR(32) DEFAULT '',
  guest_count INT DEFAULT 0,
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
  reservation_id BIGINT NULL,
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
('admin', 'admin123', 'admin', '门店主管', '13800000000', '{}', 1, 0, 1),
('subadmin', 'sub123', 'admin', '门店店员', '13800000001', '{}', 0, 1, 1),
('user', 'user123', 'user', '租车人甲', '13800000002',
 '{"realName":"周租客","email":"zhou@demo.edu","gender":"男","driverName":"周租客","licenseNo":"A123456789"}',
 0, 1, 1)
ON DUPLICATE KEY UPDATE nickname=VALUES(nickname), phone=VALUES(phone), profile_json=VALUES(profile_json);

INSERT IGNORE INTO category (id, name) VALUES (1, '经济型'), (2, '舒适型'), (3, '新能源');
INSERT IGNORE INTO vehicle (id, title, price_yuan, vehicle_note, category_id, stock, status) VALUES
(1, '大众朗逸 自动挡', '168.00', '5座 / 油车', 1, 4, 'available'),
(2, '丰田卡罗拉 双擎', '228.00', '5座 / 混动', 2, 3, 'available'),
(3, '比亚迪秦 PLUS EV', '258.00', '5座 / 纯电', 3, 3, 'available');
INSERT IGNORE INTO resource_slot (id, item_id, start_at, end_at, capacity, booked) VALUES
(1, 1, '2026-09-20 09:00:00', '2026-09-21 09:00:00', 2, 0),
(2, 1, '2026-09-21 09:00:00', '2026-09-22 09:00:00', 2, 0),
(3, 1, '2026-09-22 09:00:00', '2026-09-23 09:00:00', 2, 0),
(4, 2, '2026-09-20 09:00:00', '2026-09-21 09:00:00', 2, 0),
(5, 2, '2026-09-21 09:00:00', '2026-09-22 09:00:00', 2, 0),
(6, 2, '2026-09-22 09:00:00', '2026-09-23 09:00:00', 2, 0),
(7, 3, '2026-09-20 09:00:00', '2026-09-21 09:00:00', 2, 0),
(8, 3, '2026-09-21 09:00:00', '2026-09-22 09:00:00', 2, 0),
(9, 3, '2026-09-22 09:00:00', '2026-09-23 09:00:00', 2, 0);
INSERT IGNORE INTO reservation (id, slot_id, username, status, remark, guest_name, guest_count) VALUES
(1, 1, 'user', 'confirmed', '周租客', '周租客', 1);
UPDATE resource_slot SET booked = 1 WHERE id = 1;
INSERT IGNORE INTO biz_order (id, username, status, total_yuan, remark, reservation_id) VALUES
(1, 'user', 'confirmed', 168.00, 'reservation:1', 1);
INSERT IGNORE INTO order_line (id, order_id, item_id, title, price_yuan, qty) VALUES
(1, 1, 1, '大众朗逸 自动挡', 168.00, 1);
INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '汽车租赁', '选择车型与租期下单；下单成功即生成订单，门店办理取车与还车。', 'admin', '门店主管'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='汽车租赁');

-- staff posts (clerk / worker)
UPDATE sys_user SET staff_post='', staff_kind='' WHERE super_admin=1;
INSERT INTO sys_user (username, password, role, nickname, phone, profile_json, super_admin, profile_editable, enabled, staff_post, staff_kind) VALUES ('subadmin', 'sub123', 'admin', '门店店员', '13800000001', '{}', 0, 1, 1, 'front', 'clerk') ON DUPLICATE KEY UPDATE nickname=VALUES(nickname), staff_post=VALUES(staff_post), staff_kind=VALUES(staff_kind), role='admin', super_admin=0;
