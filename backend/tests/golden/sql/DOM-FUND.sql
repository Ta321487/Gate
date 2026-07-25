-- bake domain=DOM-FUND · tables in [6,15]
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

-- ArchiveStore 兼容列；author=归口单位；isbn=名额/条件备注；stock=可申请
CREATE TABLE IF NOT EXISTS fund_program (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  title VARCHAR(200) NOT NULL,
  dept_name VARCHAR(100),
  quota_note VARCHAR(255),
  category_id BIGINT,
  stock INT DEFAULT 1,
  status VARCHAR(32) DEFAULT 'available',
  cover_url VARCHAR(255),
  stage VARCHAR(32) DEFAULT '在岗',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- book_id=fund_program.id
CREATE TABLE IF NOT EXISTS fund_apply (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  fund_program_id BIGINT NOT NULL,
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
('admin', 'admin123', 'admin', '资助主管', '13800000000', '{}', 1, 0, 1),
('subadmin', 'sub123', 'admin', '资助专员', '13800000001', '{}', 0, 1, 1),
('user', 'user123', 'user', '学生甲', '13800000002',
 '{"realName":"周明","email":"zhou@demo.edu","gender":"男","studentNo":"S2026008","dept":"计算机学院","gradeYear":"2023"}',
 0, 1, 1)
ON DUPLICATE KEY UPDATE nickname=VALUES(nickname), phone=VALUES(phone), profile_json=VALUES(profile_json);

INSERT IGNORE INTO category (id, name) VALUES (1, '国家助学'), (2, '校内奖学金'), (3, '困难补助');
INSERT IGNORE INTO fund_program (id, title, dept_name, quota_note, category_id, stock, status) VALUES
(1, '国家助学金（一等）', '学生资助中心', '家庭经济困难认定 / 名额 120', 1, 1, 'available'),
(2, '校长奖学金', '学工处', '综合测评前 5% / 名额 30', 2, 1, 'available'),
(3, '临时困难补助', '各学院学工办', '突发困难证明 / 随到随审', 3, 1, 'available'),
(4, '单项奖学金·科研', '教务处/学工处', '发表论文或竞赛获奖证明', 2, 1, 'available'),
(5, '勤工助学岗位津贴', '学生资助中心', '在岗考核合格 / 按月发放', 3, 1, 'available');
INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '资助须知', '请按通知提交申请材料；审批通过后留意发放进度。', 'admin', '资助主管'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='资助须知');
INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '本学期资助', '本学期奖助学金申报已开放，请在截止日前完成材料提交。', 'admin', '资助主管'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='本学期资助');

CREATE TABLE IF NOT EXISTS `fund_apply_progress` (
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
UPDATE sys_user SET staff_post='fund_clerk', staff_kind='clerk', nickname='资助专员' WHERE username='subadmin' AND role='admin' AND IFNULL(super_admin,0)=0;
