-- bake domain=DOM-ACTIVITY · tables in [${TABLE_COUNT_MIN},${TABLE_COUNT_MAX}]
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

-- ArchiveStore 兼容列；stock=剩余名额；start/end 供时间冲突；apply_deadline_at 报名截止
CREATE TABLE IF NOT EXISTS activity (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  title VARCHAR(200) NOT NULL,
  author VARCHAR(100),
  isbn VARCHAR(128),
  category_id BIGINT,
  stock INT DEFAULT 0,
  status VARCHAR(32) DEFAULT 'available',
  cover_url VARCHAR(255),
  start_at DATETIME NULL,
  end_at DATETIME NULL,
  apply_deadline_at DATETIME NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- book_id=activity.id
CREATE TABLE IF NOT EXISTS signup (
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
  remark VARCHAR(255)
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

CREATE TABLE IF NOT EXISTS signup_log (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  signup_id BIGINT NOT NULL,
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
('admin', 'admin123', 'admin', '活动主管', '13800000000', '{}', 1, 0, 1),
('subadmin', 'sub123', 'admin', '活动助理', '13800000001', '{}', 0, 1, 1),
('user', 'user123', 'user', '报名者甲', '13800000002',
 '{"realName":"李同学","email":"li@demo.edu","gender":"男","studentNoOrEmp":"S20260001","dept":"计算机学院","identityType":"学生","orgOrClub":"青年志愿者协会"}',
 0, 1, 1)
ON DUPLICATE KEY UPDATE nickname=VALUES(nickname), phone=VALUES(phone), profile_json=VALUES(profile_json);

INSERT IGNORE INTO category (id, name) VALUES (1, '社团活动'), (2, '志愿活动'), (3, '讲座');
-- 1 与 4 时段重叠，便于演示冲突；截止日放在开课前
INSERT IGNORE INTO activity (id, title, author, isbn, category_id, stock, status, start_at, end_at, apply_deadline_at) VALUES
(1, '编程马拉松校内赛', '计算机协会', '创新楼报告厅', 1, 40, 'available', '2026-10-11 09:00:00', '2026-10-11 17:00:00', '2026-10-10 23:59:59'),
(2, '校园环保志愿清扫', '青年志愿者协会', '南门集合', 2, 30, 'available', '2026-10-12 08:30:00', '2026-10-12 11:30:00', '2026-10-11 20:00:00'),
(3, '就业指导讲座', '就业指导中心', '图书馆报告厅', 3, 80, 'available', '2026-10-15 19:00:00', '2026-10-15 21:00:00', '2026-10-15 12:00:00'),
(4, '摄影社外拍活动', '摄影社', '湿地公园', 1, 20, 'available', '2026-10-11 14:00:00', '2026-10-11 17:00:00', '2026-10-10 23:59:59'),
(5, '敬老院慰问志愿', '青年志愿者协会', '校门口集合', 2, 15, 'available', '2026-10-19 09:00:00', '2026-10-19 12:00:00', '2026-10-18 18:00:00');
INSERT IGNORE INTO sys_config (cfg_key, cfg_value, remark) VALUES
('max_signup', '5', '每人同时进行中报名上限提示'),
('signup_hint', '审核通过占名额', '报名说明');
INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '报名须知', '请如实填写资料；名额有限，审核通过后请按时参加。', 'admin', '活动主管'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='报名须知');
INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '本周精选', '编程马拉松与环保志愿已开放报名，欢迎参加。', 'admin', '活动主管'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='本周精选');
