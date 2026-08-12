-- bake domain=DOM-DATING · tables in [6,15]
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

-- ArchiveStore 兼容列；author=所在城市；isbn=择偶意向；stock=可牵线
CREATE TABLE IF NOT EXISTS dating_profile (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  title VARCHAR(200) NOT NULL,
  city_name VARCHAR(100),
  intent_note VARCHAR(255),
  category_id BIGINT,
  stock INT DEFAULT 1,
  status VARCHAR(32) DEFAULT 'available',
  cover_url VARCHAR(255),
  stage VARCHAR(32) DEFAULT '征婚中',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- book_id=dating_profile.id
CREATE TABLE IF NOT EXISTS match_apply (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  dating_profile_id BIGINT NOT NULL,
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
('admin', 'admin123', 'admin', '红娘主管', '13800000000', '{}', 1, 0, 1),
('subadmin', 'sub123', 'admin', '红娘专员', '13800000001', '{}', 0, 1, 1),
('user', 'user123', 'user', '会员甲', '13800000002',
 '{"realName":"陈悦","email":"chen@demo.com","gender":"女","identityType":"会员","city":"杭州","education":"本科","ageRange":"26-30"}',
 0, 1, 1)
ON DUPLICATE KEY UPDATE nickname=VALUES(nickname), phone=VALUES(phone), profile_json=VALUES(profile_json);

INSERT IGNORE INTO category (id, name) VALUES (1, '同城相亲'), (2, '校园联谊'), (3, '兴趣交友');
INSERT IGNORE INTO dating_profile (id, title, city_name, intent_note, category_id, stock, status) VALUES
(1, '小雨 · 26岁', '杭州', '希望对方踏实上进', 1, 1, 'available'),
(2, '阿明 · 28岁', '南京', '喜欢户外与阅读', 1, 1, 'available'),
(3, '林同学 · 22岁', '合肥', '校园联谊友好认识', 2, 1, 'available'),
(4, '周周 · 30岁', '苏州', '稳定工作，期待认真交往', 1, 1, 'available'),
(5, '乐乐 · 24岁', '上海', '兴趣交友，先做朋友', 3, 1, 'available');
INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '牵线须知', '请如实填写资料；红娘审核通过后可一对一私信沟通（本期无视频相亲）。', 'admin', '红娘主管'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='牵线须知');
INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '本周联谊', '同城与校园资料已更新，可发起牵线意向。', 'admin', '红娘主管'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='本周联谊');

CREATE TABLE IF NOT EXISTS `match_apply_progress` (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  ticket_id BIGINT NOT NULL,
  status VARCHAR(32) NOT NULL,
  operator VARCHAR(64),
  remark VARCHAR(255) DEFAULT '',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  KEY idx_progress_ticket (ticket_id, id)
);

CREATE TABLE IF NOT EXISTS sys_dm_message (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  from_username VARCHAR(64) NOT NULL,
  to_username VARCHAR(64) NOT NULL,
  body VARCHAR(500) NOT NULL,
  read_at DATETIME NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  KEY idx_dm_from (from_username, id),
  KEY idx_dm_to (to_username, id),
  KEY idx_dm_pair (from_username, to_username, id),
  KEY idx_dm_unread (to_username, read_at, id)
);

INSERT INTO sys_user (username, password, role, nickname, phone, profile_json, super_admin, profile_editable, enabled)
SELECT 'user2', 'user123', 'user', '用户乙', '13800000003', '{}', 0, 1, 1
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_user WHERE username='user2');
INSERT INTO sys_dm_message (from_username, to_username, body, created_at)
SELECT 'user', 'user2', '你好，方便私信问下帖子细节吗？', DATE_SUB(NOW(), INTERVAL 10 MINUTE)
FROM DUAL
WHERE EXISTS (SELECT 1 FROM sys_user WHERE username='user')
  AND EXISTS (SELECT 1 FROM sys_user WHERE username='user2')
  AND NOT EXISTS (SELECT 1 FROM sys_dm_message LIMIT 1);
INSERT INTO sys_dm_message (from_username, to_username, body, created_at)
SELECT 'user2', 'user', '可以，你说。', DATE_SUB(NOW(), INTERVAL 8 MINUTE)
FROM DUAL
WHERE EXISTS (SELECT 1 FROM sys_user WHERE username='user')
  AND EXISTS (SELECT 1 FROM sys_user WHERE username='user2')
  AND (SELECT COUNT(*) FROM sys_dm_message) < 2;
INSERT INTO sys_dm_message (from_username, to_username, body, created_at)
SELECT 'user', 'user2', '谢谢，本期用两个浏览器窗口就能互发。', DATE_SUB(NOW(), INTERVAL 5 MINUTE)
FROM DUAL
WHERE EXISTS (SELECT 1 FROM sys_user WHERE username='user')
  AND EXISTS (SELECT 1 FROM sys_user WHERE username='user2')
  AND (SELECT COUNT(*) FROM sys_dm_message) < 3;

-- staff posts (clerk / worker)
UPDATE sys_user SET staff_post='', staff_kind='' WHERE super_admin=1;
INSERT INTO sys_user (username, password, role, nickname, phone, profile_json, super_admin, profile_editable, enabled, staff_post, staff_kind) VALUES ('subadmin', 'sub123', 'admin', '红娘专员', '13800000001', '{}', 0, 1, 1, 'matchmaker', 'clerk') ON DUPLICATE KEY UPDATE nickname=VALUES(nickname), staff_post=VALUES(staff_post), staff_kind=VALUES(staff_kind), role='admin', super_admin=0;
