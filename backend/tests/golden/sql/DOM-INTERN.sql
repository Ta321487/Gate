-- bake domain=DOM-INTERN · tables in [6,15]
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

-- ArchiveStore 兼容列；author=企业导师；isbn=单位/岗位；stock=可交周报
CREATE TABLE IF NOT EXISTS intern_post (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  title VARCHAR(200) NOT NULL,
  mentor_name VARCHAR(100),
  org_note VARCHAR(255),
  category_id BIGINT,
  stock INT DEFAULT 1,
  status VARCHAR(32) DEFAULT 'available',
  cover_url VARCHAR(255),
  -- 默认待上岗：禁止目录项一律「实习中」造成多单位入职误读（M-01 / §18）
  stage VARCHAR(32) DEFAULT '待上岗',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- book_id=intern_post.id
CREATE TABLE IF NOT EXISTS week_report (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  intern_post_id BIGINT NOT NULL,
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
('admin', 'admin123', 'admin', '就业办主管', '13800000000', '{}', 1, 0, 1),
('subadmin', 'sub123', 'admin', '实习辅导员', '13800000001', '{}', 0, 1, 1),
('user', 'user123', 'user', '实习生甲', '13800000002',
 '{"realName":"小陈","email":"chen@demo.edu","gender":"男","studentNo":"S20260333","dept":"信息学院","internOrg":"星河科技","internPost":"后端开发实习"}',
 0, 1, 1)
ON DUPLICATE KEY UPDATE nickname=VALUES(nickname), phone=VALUES(phone), profile_json=VALUES(profile_json);

INSERT IGNORE INTO category (id, name) VALUES (1, '开发实习'), (2, '运维实习'), (3, '综合实习');
-- 岗 1=样例账号关联岗（实习中）；其余为可选示范目录（待上岗），勿理解为一人入职五家
INSERT IGNORE INTO intern_post (id, title, mentor_name, org_note, category_id, stock, status, stage) VALUES
(1, '后端开发实习', '王工', '星河科技 / Java', 1, 1, 'available', '实习中'),
(2, '网络运维实习', '李工', '校园信息中心 / 运维', 2, 1, 'available', '待上岗'),
(3, '行政综合实习', '赵主管', '区政务中心 / 文员', 3, 1, 'available', '待上岗'),
(4, '测试实习', '周工', '青禾软件 / 测试', 1, 1, 'available', '待上岗'),
(5, '数据分析实习', '陈老师', '学院实验室 / 数据', 3, 1, 'available', '待上岗');
-- 样例账号 user 仅关联岗 1 的周报主路径
INSERT IGNORE INTO week_report (id, intern_post_id, username, status, remark, contact_channel) VALUES
(1, 1, 'user', 'pending', '第1周：熟悉项目结构与编码规范，完成环境搭建。', '在线填写');
INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '周报须知',
  '每周日前提交周报；导师审阅后方可计入实习考勤。岗位列表为示范目录，「实习中」仅标关联岗。开题要求岗位与学生绑定时，请在个人资料填写实习单位与岗位后再交周报。',
  'admin', '就业办主管'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='周报须知');
INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '鉴定提醒', '实习结束前完成鉴定材料；可在「鉴定签署」上传签章图并勾选同意（非 CA）。', 'admin', '就业办主管'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='鉴定提醒');

CREATE TABLE IF NOT EXISTS `week_report_progress` (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  ticket_id BIGINT NOT NULL,
  status VARCHAR(32) NOT NULL,
  operator VARCHAR(64),
  remark VARCHAR(255) DEFAULT '',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  KEY idx_progress_ticket (ticket_id, id)
);

CREATE TABLE IF NOT EXISTS e_sign_record (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  username VARCHAR(64) NOT NULL,
  title VARCHAR(200) NOT NULL,
  ticket_id BIGINT NULL,
  sign_image_url VARCHAR(255) NOT NULL DEFAULT '',
  agreed TINYINT NOT NULL DEFAULT 0,
  remark VARCHAR(255) DEFAULT '',
  signed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  KEY idx_e_sign_user (username, id)
);

-- staff posts (clerk / worker)
UPDATE sys_user SET staff_post='', staff_kind='' WHERE super_admin=1;
INSERT INTO sys_user (username, password, role, nickname, phone, profile_json, super_admin, profile_editable, enabled, staff_post, staff_kind) VALUES ('subadmin', 'sub123', 'admin', '实习辅导员', '13800000001', '{}', 0, 1, 1, 'intern_tutor', 'clerk') ON DUPLICATE KEY UPDATE nickname=VALUES(nickname), staff_post=VALUES(staff_post), staff_kind=VALUES(staff_kind), role='admin', super_admin=0;
