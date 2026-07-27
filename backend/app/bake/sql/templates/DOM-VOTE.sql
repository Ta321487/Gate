-- bake domain=DOM-VOTE · tables in [${TABLE_COUNT_MIN},${TABLE_COUNT_MAX}]
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

CREATE TABLE IF NOT EXISTS vote_campaign (
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

CREATE TABLE IF NOT EXISTS vote_candidate (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  campaign_id BIGINT NOT NULL,
  name VARCHAR(128) NOT NULL,
  intro VARCHAR(1000) DEFAULT '',
  sort_no INT NOT NULL DEFAULT 0,
  status VARCHAR(32) DEFAULT 'available',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  KEY idx_vote_cand_camp (campaign_id)
);

CREATE TABLE IF NOT EXISTS vote_ballot (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  campaign_id BIGINT NOT NULL,
  username VARCHAR(64) NOT NULL,
  candidate_id BIGINT NOT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uk_vote_user_cand (campaign_id, username, candidate_id),
  KEY idx_vote_ball_user (campaign_id, username)
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
('subadmin', 'sub123', 'admin', '评选员', '13800000001', '{}', 0, 1, 1),
('user', 'user123', 'user', '投票人甲', '13800000002',
 '{"realName":"钱同学","email":"qian@demo.edu","gender":"男","studentNo":"20230002","dept":"学生会"}',
 0, 1, 1)
ON DUPLICATE KEY UPDATE nickname=VALUES(nickname), phone=VALUES(phone), profile_json=VALUES(profile_json);

INSERT IGNORE INTO category (id, name) VALUES (1, '十佳评选'), (2, '榜样人物'), (3, '作品评选');
INSERT IGNORE INTO vote_campaign (id, title, author, isbn, category_id, stock, status) VALUES
(1, '校园十佳大学生评选', '团委', '每人限投 1 票；结果实时公示', 1, 1, 'available'),
(2, '优秀社团作品评选', '社团联', '每人可投 2 票给不同作品', 3, 2, 'available');

INSERT IGNORE INTO vote_candidate (id, campaign_id, name, intro, sort_no, status) VALUES
(1, 1, '候选人甲', '志愿服务与学业并重', 1, 'available'),
(2, 1, '候选人乙', '科研竞赛突出', 2, 'available'),
(3, 1, '候选人丙', '文艺体育全能', 3, 'available'),
(4, 2, '作品《春晓》', '原创歌曲', 1, 'available'),
(5, 2, '作品《校园印象》', '短视频', 2, 'available'),
(6, 2, '作品《志愿足迹》', '摄影集', 3, 'available');

INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '投票须知', '请公正投票；每人按活动限票数投给不同候选人。本期无刷票防护与短信验证。', 'admin', '平台主管'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='投票须知');
