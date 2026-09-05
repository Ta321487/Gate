-- bake domain=DOM-BED · tables in [6,15]
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

-- ArchiveStore：title=床位号；author=楼栋；isbn=布局说明；stock=可占用(1/0)
CREATE TABLE IF NOT EXISTS bed (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  title VARCHAR(200) NOT NULL,
  building_name VARCHAR(100),
  layout_note VARCHAR(255),
  category_id BIGINT,
  stock INT DEFAULT 1,
  status VARCHAR(32) DEFAULT 'available',
  cover_url VARCHAR(255),
  stage VARCHAR(32) DEFAULT '空闲',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS bed_apply (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  bed_id BIGINT NOT NULL,
  username VARCHAR(64) NOT NULL,
  status VARCHAR(32) NOT NULL DEFAULT 'pending',
  assignee_username VARCHAR(64) NULL,
  apply_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  approve_at DATETIME NULL,
  return_at DATETIME NULL,
  remark VARCHAR(512),
  contact_channel VARCHAR(32) DEFAULT '',
  next_follow_at DATETIME NULL
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
('admin', 'admin123', 'admin', '宿管主管', '13800000000', '{}', 1, 0, 1),
('subadmin', 'sub123', 'admin', '宿管员', '13800000001', '{}', 0, 1, 1),
('user', 'user123', 'user', '学生甲', '13800000002',
 '{"realName":"样例学生","email":"stu@demo.edu","gender":"男","studentNo":"20230001","dept":"计算机学院"}',
 0, 1, 1)
ON DUPLICATE KEY UPDATE nickname=VALUES(nickname), phone=VALUES(phone), profile_json=VALUES(profile_json);

INSERT IGNORE INTO category (id, name) VALUES (1, '四人间'), (2, '六人间'), (3, '调宿退宿');
INSERT IGNORE INTO bed (id, title, building_name, layout_note, category_id, stock, status, stage) VALUES
(1, '1栋101-1', '1号楼', '靠窗', 1, 1, 'available', '空闲'),
(2, '1栋101-2', '1号楼', '靠门', 1, 1, 'available', '空闲'),
(3, '2栋205-3', '2号楼', '中铺', 2, 1, 'available', '空闲'),
(4, '3栋312-4', '3号楼', '下铺', 1, 1, 'available', '空闲'),
(5, '调宿窗口', '宿管中心', '调宿/退宿事项（无实体床）', 3, 99, 'available', '开放');
INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '床位申请须知', '选房通过后占用床位库存；调宿/退宿请选择对应事项并写明原床位。', 'admin', '宿管主管'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='床位申请须知');

CREATE TABLE IF NOT EXISTS `bed_apply_progress` (
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
INSERT INTO sys_user (username, password, role, nickname, phone, profile_json, super_admin, profile_editable, enabled, staff_post, staff_kind) VALUES ('subadmin', 'sub123', 'admin', '宿管员', '13800000001', '{}', 0, 1, 1, 'bed_clerk', 'clerk') ON DUPLICATE KEY UPDATE nickname=VALUES(nickname), staff_post=VALUES(staff_post), staff_kind=VALUES(staff_kind), role='admin', super_admin=0;
