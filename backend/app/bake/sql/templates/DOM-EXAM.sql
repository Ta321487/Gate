-- bake domain=DOM-EXAM · tables in [${TABLE_COUNT_MIN},${TABLE_COUNT_MAX}]
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

CREATE TABLE IF NOT EXISTS exam_subject (
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

CREATE TABLE IF NOT EXISTS exam_question (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  subject_id BIGINT NULL,
  type VARCHAR(16) NOT NULL,
  stem VARCHAR(2000) NOT NULL,
  options_json VARCHAR(2000) DEFAULT '',
  answer_key VARCHAR(500) NOT NULL,
  score INT NOT NULL DEFAULT 5,
  explain_text VARCHAR(2000) NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS exam_paper (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  title VARCHAR(200) NOT NULL,
  duration_min INT NOT NULL DEFAULT 0,
  status VARCHAR(16) NOT NULL DEFAULT 'draft',
  subject_id BIGINT NULL,
  max_attempts INT NOT NULL DEFAULT 0,
  gate_ticket TINYINT NOT NULL DEFAULT 0,
  pass_score INT NOT NULL DEFAULT 60,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS exam_paper_question (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  paper_id BIGINT NOT NULL,
  question_id BIGINT NOT NULL,
  sort_no INT NOT NULL DEFAULT 0,
  UNIQUE KEY uk_paper_q (paper_id, question_id)
);

CREATE TABLE IF NOT EXISTS exam_attempt (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  paper_id BIGINT NOT NULL,
  username VARCHAR(64) NOT NULL,
  mode VARCHAR(16) NOT NULL DEFAULT 'exam',
  status VARCHAR(16) NOT NULL DEFAULT 'in_progress',
  score INT NOT NULL DEFAULT 0,
  total_score INT NOT NULL DEFAULT 0,
  started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  submitted_at DATETIME NULL,
  timed_out TINYINT NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS exam_answer (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  attempt_id BIGINT NOT NULL,
  question_id BIGINT NOT NULL,
  answer_text VARCHAR(2000) DEFAULT '',
  is_correct TINYINT NOT NULL DEFAULT 0,
  score INT NOT NULL DEFAULT 0,
  UNIQUE KEY uk_attempt_q (attempt_id, question_id)
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
('subadmin', 'sub123', 'admin', '教务员', '13800000001', '{}', 0, 1, 1),
('user', 'user123', 'user', '考生甲', '13800000002',
 '{"realName":"王同学","email":"wang@demo.edu","gender":"女","studentNo":"20230001","dept":"计算机学院"}',
 0, 1, 1)
ON DUPLICATE KEY UPDATE nickname=VALUES(nickname), phone=VALUES(phone), profile_json=VALUES(profile_json);

INSERT IGNORE INTO category (id, name) VALUES (1, '公共基础'), (2, '专业基础'), (3, '综合测验');
INSERT IGNORE INTO exam_subject (id, title, author, isbn, category_id, stock, status) VALUES
(1, '高等数学', '教务处', '微积分 / 线性代数导论', 1, 1, 'available'),
(2, '大学英语', '外语学院', '阅读与词汇', 1, 1, 'available'),
(3, '专业综合', '计算机学院', '程序设计基础', 2, 1, 'available');

INSERT IGNORE INTO exam_question (id, subject_id, type, stem, options_json, answer_key, score, explain_text) VALUES
(1, 1, 'single', '线性代数基础中，矩阵乘法是否满足交换律？',
 '["满足","不满足","仅方阵满足","仅对角阵满足"]', 'B', 5, '一般矩阵乘法不满足交换律。'),
(2, 1, 'judge', '单位矩阵与任意同阶矩阵相乘结果仍为原矩阵。',
 '["正确","错误"]', '正确', 5, '单位矩阵是乘法单位元。'),
(3, 2, 'multi', '英语阅读理解常见题型包括哪些？',
 '["主旨大意","细节理解","词义猜测","代码调试"]', 'A,B,C', 10, '代码调试不属于英语阅读题型。'),
(4, 2, 'subjective', '请简述提高英语阅读速度的一种方法。',
 '', '略读|扫读|关键词', 10, '答出略读/扫读/关键词等方法之一即可（自动判分）。'),
(5, 3, 'single', '下列哪一项是常见的程序控制结构？',
 '["顺序","随机跳转","无条件死循环","仅递归"]', 'A', 5, '顺序、分支、循环是基本控制结构。');

INSERT IGNORE INTO exam_paper (id, title, duration_min, status, subject_id, max_attempts) VALUES
(1, '期中测验卷', 60, 'published', 1, 0),
(2, '综合练习卷', 0, 'published', 3, 3);

INSERT IGNORE INTO exam_paper_question (id, paper_id, question_id, sort_no) VALUES
(1, 1, 1, 1), (2, 1, 2, 2), (3, 1, 3, 3), (4, 1, 4, 4),
(5, 2, 5, 1), (6, 2, 1, 2), (7, 2, 2, 3);

INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '考试须知', '请独立完成作答；客观题自动判分，主观题按关键词/正则自动判分。', 'admin', '平台主管'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='考试须知');
