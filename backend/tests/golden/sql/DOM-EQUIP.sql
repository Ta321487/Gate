-- bake domain=DOM-EQUIP · tables in [6,15]
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

-- 列结构与 ArchiveStore 默认 book 表兼容（title/author/isbn/stock）
CREATE TABLE IF NOT EXISTS equip (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  title VARCHAR(200) NOT NULL,
  brand_model VARCHAR(100),
  asset_no VARCHAR(64),
  category_id BIGINT,
  stock INT DEFAULT 0,
  status VARCHAR(32) DEFAULT 'available',
  cover_url VARCHAR(255),
  requires_training TINYINT DEFAULT 0,
  owner_name VARCHAR(64) DEFAULT '',
  deleted_at DATETIME NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- book_id 列名兼容 TicketStore archive 模式（存 equip.id）
CREATE TABLE IF NOT EXISTS loan (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  equip_id BIGINT NOT NULL,
  username VARCHAR(64) NOT NULL,
  status VARCHAR(32) NOT NULL DEFAULT 'pending',
  assignee_username VARCHAR(64) NULL,
  apply_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  approve_at DATETIME NULL,
  due_at DATETIME NULL,
  return_at DATETIME NULL,
  qty INT NOT NULL DEFAULT 1,
  fine_yuan DECIMAL(10,2) NOT NULL DEFAULT 0,
  fine_status VARCHAR(16) DEFAULT 'none',
  reminded_at DATETIME NULL,
  remind_msg VARCHAR(255) DEFAULT '',
  remark VARCHAR(255)
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
('admin', 'admin123', 'admin', '实验室主管', '13800000000', '{}', 1, 0, 1),
('subadmin', 'sub123', 'admin', '器材管理员', '13800000001', '{}', 0, 1, 1),
('user', 'user123', 'user', '借用人甲', '13800000002',
 '{"realName":"李同学","email":"li@demo.edu","gender":"男","studentNo":"S20230001","dept":"机电工程学院","identityType":"学生","labOrOffice":"机电楼 301"}',
 0, 1, 1)
ON DUPLICATE KEY UPDATE nickname=VALUES(nickname), phone=VALUES(phone), profile_json=VALUES(profile_json);

INSERT IGNORE INTO category (id, name) VALUES
(1, '测量仪器'), (2, '电子器材'), (3, '机械工具'),
(4, '校园轻资产'), (5, '演出道具');
INSERT IGNORE INTO equip (id, title, brand_model, asset_no, category_id, stock, status) VALUES
(1, '数字万用表', 'Fluke 15B+', 'EQ-DMM-001', 1, 5, 'available'),
(2, '示波器', 'Rigol DS1054Z', 'EQ-OSC-002', 1, 3, 'available'),
(3, '电钻套装', 'Bosch', 'EQ-TOOL-003', 3, 2, 'available'),
(4, '共享雨伞', '学生会物资组', 'UMBRELLA-01', 4, 20, 'available'),
(5, '共享充电宝', '后勤中心', 'POWERBANK-02', 4, 15, 'available'),
(6, '演出音响套装', '艺术团', 'PROP-AUDIO-03', 5, 2, 'available');
INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '设备借用须知', '请按需申请、按时归还；逾期将登记催还。轻资产与演出道具同走借用审核。', 'admin', '实验室主管'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='设备借用须知');
INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '开放时间', '工作日 8:30–17:30 办理领用与归还。', 'admin', '实验室主管'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='开放时间');

CREATE TABLE IF NOT EXISTS `loan_progress` (
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
UPDATE sys_user SET staff_post='keeper', staff_kind='clerk', nickname='器材管理员' WHERE username='subadmin' AND role='admin' AND IFNULL(super_admin,0)=0;
