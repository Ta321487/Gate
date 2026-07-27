-- bake domain=DOM-DOCLIB · tables in [${TABLE_COUNT_MIN},${TABLE_COUNT_MAX}]
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

CREATE TABLE IF NOT EXISTS doc_item (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  title VARCHAR(200) NOT NULL,
  author VARCHAR(100),
  isbn VARCHAR(256),
  category_id BIGINT,
  stock INT DEFAULT 1,
  status VARCHAR(32) DEFAULT 'available',
  cover_url VARCHAR(255),
  file_url VARCHAR(255) DEFAULT '',
  access_level VARCHAR(16) NOT NULL DEFAULT 'login',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS download_log (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  item_id BIGINT NOT NULL,
  username VARCHAR(64) NOT NULL,
  downloaded_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  KEY idx_dl_item (item_id),
  KEY idx_dl_user (username, id)
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
('admin', 'admin123', 'admin', '平台主管', '13800000000', '{}', 1, 0, 1),
('subadmin', 'sub123', 'admin', '资料员', '13800000001', '{}', 0, 1, 1),
('user', 'user123', 'user', '读者甲', '13800000002',
 '{"realName":"孙同学","email":"sun@demo.edu","gender":"女","studentNo":"20230003","dept":"信息学院"}',
 0, 1, 1)
ON DUPLICATE KEY UPDATE nickname=VALUES(nickname), phone=VALUES(phone), profile_json=VALUES(profile_json);

INSERT IGNORE INTO category (id, name) VALUES (1, '制度文件'), (2, '课件资料'), (3, '表格模板');
INSERT IGNORE INTO doc_item (id, title, author, isbn, category_id, stock, status, file_url, access_level) VALUES
(1, '学生手册（节选）', '学工处', '校内制度节选文稿', 1, 1, 'available', '/uploads/demo-handbook.pdf', 'login'),
(2, '实验报告模板', '教务处', 'Word 模板下载链接', 3, 1, 'available', '/uploads/demo-report.docx', 'public'),
(3, '教职工内部制度汇编', '人事处', '仅管理人员可下载', 1, 1, 'available', '/uploads/demo-staff.pdf', 'staff');

INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '文库须知', '下载将记入台账；附件为占位 URL，无真对象存储签名与全文检索。', 'admin', '平台主管'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='文库须知');
