-- bake domain=DOM-SURVEY · tables in [${TABLE_COUNT_MIN},${TABLE_COUNT_MAX}]
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

CREATE TABLE IF NOT EXISTS survey_form (
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

CREATE TABLE IF NOT EXISTS survey_question (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  form_id BIGINT NOT NULL,
  type VARCHAR(16) NOT NULL,
  stem VARCHAR(2000) NOT NULL,
  options_json VARCHAR(2000) DEFAULT '',
  sort_no INT NOT NULL DEFAULT 0,
  required TINYINT NOT NULL DEFAULT 1,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS survey_response (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  form_id BIGINT NOT NULL,
  username VARCHAR(64) NOT NULL,
  submitted_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uk_survey_user_form (form_id, username)
);

CREATE TABLE IF NOT EXISTS survey_answer (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  response_id BIGINT NOT NULL,
  question_id BIGINT NOT NULL,
  answer_text VARCHAR(2000) DEFAULT '',
  UNIQUE KEY uk_survey_ans (response_id, question_id)
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
('subadmin', 'sub123', 'admin', '调研员', '13800000001', '{}', 0, 1, 1),
('user', 'user123', 'user', '受访者甲', '13800000002',
 '{"realName":"赵同学","email":"zhao@demo.edu","gender":"女","studentNo":"20230001","dept":"管理学院"}',
 0, 1, 1)
ON DUPLICATE KEY UPDATE nickname=VALUES(nickname), phone=VALUES(phone), profile_json=VALUES(profile_json);

INSERT IGNORE INTO category (id, name) VALUES (1, '满意度'), (2, '需求调研'), (3, '活动反馈');
INSERT IGNORE INTO survey_form (id, title, author, isbn, category_id, stock, status) VALUES
(1, '食堂满意度调查', '后勤处', '关于食堂服务的简易问卷', 1, 1, 'available'),
(2, '图书馆服务反馈', '图书馆', '阅览与借阅体验', 3, 1, 'available');

INSERT IGNORE INTO survey_question (id, form_id, type, stem, options_json, sort_no, required) VALUES
(1, 1, 'single', '您对食堂整体满意度？', '["非常满意","满意","一般","不满意"]', 1, 1),
(2, 1, 'multi', '您关注哪些改进点？', '["口味","价格","卫生","排队"]', 2, 1),
(3, 1, 'text', '其他建议（选填）', '', 3, 0),
(4, 2, 'single', '您是否常去图书馆？', '["经常","偶尔","很少"]', 1, 1),
(5, 2, 'text', '最希望增加的服务？', '', 2, 1);

INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '问卷须知', '请如实填写；每人每卷限填一次。本期无跳题逻辑与 SPSS 导出。', 'admin', '平台主管'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='问卷须知');
