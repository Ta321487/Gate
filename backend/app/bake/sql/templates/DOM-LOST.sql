-- bake domain=DOM-LOST · tables in [${TABLE_COUNT_MIN},${TABLE_COUNT_MAX}]
CREATE DATABASE IF NOT EXISTS `${DB_NAME}` DEFAULT CHARACTER SET utf8mb4;
USE `${DB_NAME}`;

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
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS category (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  name VARCHAR(64) NOT NULL UNIQUE
);

-- ArchiveStore 兼容列；isbn=地点/特征；stock=可认领(1/0)
CREATE TABLE IF NOT EXISTS lost_item (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  title VARCHAR(200) NOT NULL,
  author VARCHAR(100),
  isbn VARCHAR(256),
  category_id BIGINT,
  stock INT DEFAULT 1,
  status VARCHAR(32) DEFAULT 'available',
  cover_url VARCHAR(255),
  item_kind VARCHAR(16) DEFAULT '招领',
  found_at DATETIME NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- book_id=lost_item.id
CREATE TABLE IF NOT EXISTS claim (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  book_id BIGINT NOT NULL,
  username VARCHAR(64) NOT NULL,
  status VARCHAR(32) NOT NULL DEFAULT 'pending',
  assignee_username VARCHAR(64) NULL,
  apply_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  approve_at DATETIME NULL,
  due_at DATETIME NULL,
  return_at DATETIME NULL,
  fine_yuan DECIMAL(10,2) NOT NULL DEFAULT 0,
  fine_status VARCHAR(16) DEFAULT 'none',
  reminded_at DATETIME NULL,
  remind_msg VARCHAR(255) DEFAULT '',
  remark VARCHAR(255),
  pickup_at DATETIME NULL,
  pickup_place VARCHAR(128) DEFAULT ''
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

CREATE TABLE IF NOT EXISTS claim_log (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  claim_id BIGINT NOT NULL,
  action VARCHAR(32) NOT NULL,
  operator VARCHAR(64),
  remark VARCHAR(255) DEFAULT '',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS sys_config (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  cfg_key VARCHAR(64) NOT NULL UNIQUE,
  cfg_value VARCHAR(255) NOT NULL,
  remark VARCHAR(128) DEFAULT ''
);

INSERT INTO sys_user (username, password, role, nickname, phone, profile_json, super_admin, profile_editable, enabled) VALUES
('admin', 'admin123', 'admin', '招领主管', '13800000000', '{}', 1, 0, 1),
('subadmin', 'sub123', 'admin', '招领管理员', '13800000001', '{}', 0, 1, 1),
('user', 'user123', 'user', '用户甲', '13800000002',
 '{"realName":"王同学","email":"wang@demo.edu","gender":"女","campusNo":"S20260002","dept":"文学院","contactWechat":"wang_demo","usualPlace":"图书馆"}',
 0, 1, 1)
ON DUPLICATE KEY UPDATE nickname=VALUES(nickname), phone=VALUES(phone), profile_json=VALUES(profile_json);

INSERT IGNORE INTO category (id, name) VALUES (1, '证件卡类'), (2, '电子数码'), (3, '生活用品');
INSERT IGNORE INTO lost_item (id, title, author, isbn, category_id, stock, status) VALUES
(1, '校园卡（尾号 8821）', '保卫处', '一食堂窗口拾获 / 蓝色挂绳', 1, 1, 'available'),
(2, '黑色无线耳机盒', '图书馆值班', '三楼阅览室 / AirPods 样式', 2, 1, 'available'),
(3, '蓝色水杯', '学生甲', '实验楼 B201 / 杯身有贴纸', 3, 1, 'available'),
(4, '学生证', '宿舍楼管', '3 栋门厅 / 计算机学院', 1, 1, 'available'),
(5, '充电器一套', '教室保洁', '教学楼 305 / Type-C 线', 2, 1, 'available');
INSERT IGNORE INTO sys_config (cfg_key, cfg_value, remark) VALUES
('claim_hint', '需核对特征', '认领说明'),
('pickup_place', '保卫处失物点', '领取地点');
INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '招领须知', '认领时请提供有效身份与物品特征；审核通过后到指定地点领取。', 'admin', '招领主管'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='招领须知');
INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '本周公示', '证件与数码类启事已更新，请及时认领。', 'admin', '招领主管'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='本周公示');
