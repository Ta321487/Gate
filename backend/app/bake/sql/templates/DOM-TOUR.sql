-- bake domain=DOM-TOUR · tables in [${TABLE_COUNT_MIN},${TABLE_COUNT_MAX}]
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

-- ArchiveStore 兼容列；stock=余位；stage=线路状态（开放报名/满员/已出团/下架）；apply_deadline_at 报名截止
CREATE TABLE IF NOT EXISTS tour_line (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  title VARCHAR(200) NOT NULL,
  author VARCHAR(100),
  isbn VARCHAR(256),
  category_id BIGINT,
  stock INT DEFAULT 20,
  status VARCHAR(32) DEFAULT 'available',
  cover_url VARCHAR(255),
  stage VARCHAR(32) DEFAULT '开放报名',
  apply_deadline_at DATETIME NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- book_id=tour_line.id
CREATE TABLE IF NOT EXISTS tour_signup (
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

CREATE TABLE IF NOT EXISTS tour_signup_log (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  tour_signup_id BIGINT NOT NULL,
  action VARCHAR(32) NOT NULL,
  operator VARCHAR(64),
  remark VARCHAR(255) DEFAULT '',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO sys_user (username, password, role, nickname, phone, profile_json, super_admin, profile_editable, enabled) VALUES
('admin', 'admin123', 'admin', '计调主管', '13800000000', '{}', 1, 0, 1),
('subadmin', 'sub123', 'admin', '计调员', '13800000001', '{}', 0, 1, 1),
('user', 'user123', 'user', '游客甲', '13800000002',
 '{"realName":"张游客","email":"zhang@demo.com","gender":"女","memberNo":"M20260088","orgName":"个人客户","idTypeHint":"身份证","emergencyPhone":"13900000002"}',
 0, 1, 1)
ON DUPLICATE KEY UPDATE nickname=VALUES(nickname), phone=VALUES(phone), profile_json=VALUES(profile_json);

INSERT IGNORE INTO category (id, name) VALUES
(1, '周边游'), (2, '省内跟团'), (3, '跨省跟团'), (4, '研学游'), (5, '其他');
INSERT IGNORE INTO tour_line (id, title, author, isbn, category_id, stock, status, stage, apply_deadline_at) VALUES
(1, '周末古镇一日游', '计调甲', '含门票 / 往返大巴', 1, 28, 'available', '开放报名', '2026-10-11 18:00:00'),
(2, '省内山水三日团', '计调乙', '含两晚住宿 / 导游', 2, 18, 'available', '开放报名', '2026-10-18 20:00:00'),
(3, '跨省海岛五日游', '计调甲', '含机票参考价说明 / 无真支付', 3, 12, 'available', '开放报名', '2026-10-25 12:00:00'),
(4, '中学生研学两日营', '研学部', '含课程与保险说明', 4, 35, 'available', '开放报名', '2026-10-20 17:00:00'),
(5, '亲子农场半日体验', '计调乙', '含采摘体验 / 亲子适合', 1, 20, 'available', '开放报名', '2026-10-12 12:00:00');
INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '报名须知', '请如实填写出行人数与联系方式；余位有限，过报名截止将无法提交；取消报名将回补余位；本期无地图导航、OTA 同步与真支付。', 'admin', '计调主管'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='报名须知');
INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '本周线路', '古镇一日游与山水三日团余位充足，欢迎报名。', 'admin', '计调主管'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='本周线路');
-- 主路径样例：样例账号一条待审报名
INSERT IGNORE INTO tour_signup (id, book_id, username, status, remark, contact_channel) VALUES
(1, 2, 'user', 'pending', '两人出行，请确认报名。', '手机电话');
