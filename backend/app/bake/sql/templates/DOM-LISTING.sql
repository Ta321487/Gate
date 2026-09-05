-- bake domain=DOM-LISTING · tables in [${TABLE_COUNT_MIN},${TABLE_COUNT_MAX}]
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

CREATE TABLE IF NOT EXISTS listing (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  title VARCHAR(200) NOT NULL,
  author VARCHAR(100),
  isbn VARCHAR(256),
  category_id BIGINT,
  stock INT DEFAULT 1,
  status VARCHAR(32) DEFAULT 'available',
  cover_url VARCHAR(255),
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS listing_follow (
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
  reminded_at DATETIME NULL,
  remind_msg VARCHAR(255) DEFAULT '',
  remark VARCHAR(512),
  contact_channel VARCHAR(32) DEFAULT '',
  next_follow_at DATETIME NULL,
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

CREATE TABLE IF NOT EXISTS listing_follow_log (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  listing_follow_id BIGINT NOT NULL,
  action VARCHAR(32) NOT NULL,
  operator VARCHAR(64),
  remark VARCHAR(255) DEFAULT '',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO sys_user (username, password, role, nickname, phone, profile_json, super_admin, profile_editable, enabled) VALUES
('admin', 'admin123', 'admin', '业务主管', '13800000000', '{}', 1, 0, 1),
('subadmin', 'sub123', 'admin', '置业顾问', '13800000001', '{}', 0, 1, 1),
('user', 'user123', 'user', '看房客户甲', '13800000002',
 '{"realName":"样例客户","email":"client@demo.com","gender":"男","clientType":"个人求租","preferArea":"城东高新区","companyOrSchool":""}',
 0, 1, 1)
ON DUPLICATE KEY UPDATE nickname=VALUES(nickname), phone=VALUES(phone), profile_json=VALUES(profile_json);

INSERT IGNORE INTO category (id, name) VALUES (1, '整租'), (2, '合租'), (3, '二手出售');
INSERT IGNORE INTO listing (id, title, author, isbn, category_id, stock, status) VALUES
(1, '阳光花园 2 室', '城东高新区', '两室一厅 / 地铁旁', 1, 1, 'available'),
(2, '学府路单间', '学府路片区', '单间 / 近学校', 2, 1, 'available'),
(3, '城南精装两房', '城南新区', '两房 / 精装拎包', 3, 1, 'available');
INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '房源带看须知', '请如实填写说明；提交后等待审核。', 'admin', '业务主管'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='房源带看须知');
