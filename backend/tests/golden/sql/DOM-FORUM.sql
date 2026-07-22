-- bake domain=DOM-FORUM · tables in [6,15] · 顶格样板（含 sys_message）
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

-- 板块
CREATE TABLE IF NOT EXISTS category (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  name VARCHAR(64) NOT NULL UNIQUE
);

-- 版主任职（子管可挂多板块）
CREATE TABLE IF NOT EXISTS board_moderator (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  category_id BIGINT NOT NULL,
  username VARCHAR(64) NOT NULL,
  assigned_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uk_board_mod (category_id, username)
);

-- 主帖（ArchiveStore 兼容列：title/author/isbn/stock）；isbn=富文本正文 HTML
CREATE TABLE IF NOT EXISTS post (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  title VARCHAR(200) NOT NULL,
  author VARCHAR(100),
  body_html TEXT,
  category_id BIGINT,
  stock INT DEFAULT 1,
  status VARCHAR(32) DEFAULT 'available',
  cover_url VARCHAR(255),
  deleted_at DATETIME NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS post_attach (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  post_id BIGINT NOT NULL,
  file_url VARCHAR(255) NOT NULL,
  file_name VARCHAR(128) DEFAULT '',
  uploaded_by VARCHAR(64),
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS tag (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  name VARCHAR(64) NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS post_tag (
  post_id BIGINT NOT NULL,
  tag_id BIGINT NOT NULL,
  PRIMARY KEY (post_id, tag_id)
);

-- 回复楼层（TicketStore archive 模式；book_id=post.id；remark=富文本回复 HTML）
CREATE TABLE IF NOT EXISTS reply (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  post_id BIGINT NOT NULL,
  username VARCHAR(64) NOT NULL,
  status VARCHAR(32) NOT NULL DEFAULT 'pending',
  assignee_username VARCHAR(64) NULL,
  apply_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  approve_at DATETIME NULL,
  return_at DATETIME NULL,
  remark TEXT
);

CREATE TABLE IF NOT EXISTS reply_attach (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  ticket_id BIGINT NOT NULL,
  file_url VARCHAR(255) NOT NULL,
  file_name VARCHAR(128) DEFAULT '',
  uploaded_by VARCHAR(64),
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
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

CREATE TABLE IF NOT EXISTS sys_config (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  cfg_key VARCHAR(64) NOT NULL UNIQUE,
  cfg_value VARCHAR(255) NOT NULL,
  remark VARCHAR(128) DEFAULT ''
);

INSERT INTO sys_user (username, password, role, nickname, phone, profile_json, super_admin, profile_editable, enabled) VALUES
('admin', 'admin123', 'admin', '站长', '13800000000', '{}', 1, 0, 1),
('subadmin', 'sub123', 'admin', '版主甲', '13800000001', '{}', 0, 1, 1),
('user', 'user123', 'user', '用户甲', '13800000002',
 '{"realName":"李同学","email":"li@demo.edu","gender":"男","memberNo":"U20260001","orgName":"计算机学院","preferredGenre":"学习交流"}',
 0, 1, 1)
ON DUPLICATE KEY UPDATE nickname=VALUES(nickname), phone=VALUES(phone), profile_json=VALUES(profile_json);

INSERT IGNORE INTO category (id, name) VALUES (1, '学习交流'), (2, '校园生活'), (3, '二手信息');
INSERT IGNORE INTO board_moderator (id, category_id, username) VALUES
(1, 1, 'subadmin'), (2, 2, 'subadmin');
INSERT IGNORE INTO tag (id, name) VALUES (1, '期末'), (2, '资料'), (3, '活动'), (4, '闲置');
INSERT IGNORE INTO post (id, title, author, body_html, category_id, stock, status) VALUES
(1, '期末复习资料汇总', '学长甲', '<p>本帖汇总<strong>高等数学</strong>与<em>数据结构</em>复习提纲。</p><ul><li>答疑时间见楼下</li><li>附件可下载</li></ul>', 1, 1, 'available'),
(2, '实验室开放预约说明', '版主甲', '<p>工作日晚间机房开放，请先<strong>跟帖</strong>再入场。</p>', 1, 1, 'available'),
(3, '周末校园徒步召集', '用户甲', '<p>周六上午图书馆集合，路线约 5 公里。</p><p>欢迎带相机记录路线。</p>', 2, 1, 'available'),
(4, '食堂新窗口试吃反馈', '美食观察', '<p>三食堂二楼新增轻食窗口，欢迎跟帖补充评价。</p>', 2, 1, 'available'),
(5, '出闲置显示器一台', '用户甲', '<p>24 寸 IPS，成色良好，面交优先。</p>', 3, 1, 'available');
INSERT IGNORE INTO post_tag (post_id, tag_id) VALUES (1, 1), (1, 2), (3, 3), (5, 4);
INSERT IGNORE INTO post_attach (id, post_id, file_url, file_name, uploaded_by) VALUES
(1, 1, '/uploads/demo/math-outline.pdf', '高数提纲.pdf', 'admin'),
(2, 5, '/uploads/demo/monitor.jpg', '显示器实拍.jpg', 'user');
INSERT IGNORE INTO reply (id, post_id, username, status, apply_at, approve_at, remark) VALUES
(1, 1, 'user', 'approved', NOW(), NOW(), '<p>求一份<strong>离散数学</strong>提纲，谢谢楼主！</p>'),
(2, 1, 'subadmin', 'approved', NOW(), NOW(), '<p>@用户甲 离散提纲已上传附件，见主帖。</p>'),
(3, 3, 'user', 'pending', NOW(), NULL, '<p>我报名，带相机记录路线。</p>');
INSERT IGNORE INTO reply_attach (id, ticket_id, file_url, file_name, uploaded_by) VALUES
(1, 2, '/uploads/demo/discrete-outline.pdf', '离散提纲.pdf', 'subadmin');
INSERT IGNORE INTO sys_config (cfg_key, cfg_value, remark) VALUES
('max_reply', '50', '每人每帖回复上限提示'),
('forum_hint', '主帖站长维护，回复可审核', '发帖方式说明');
INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '社区公约', '请文明讨论；回复经版主审核后展示。主帖由站长维护，回复可 @他人 一层引用形成楼中楼。', 'admin', '站长'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='社区公约');
INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '本周精选', '学习交流与校园生活板块已更新演示主帖，欢迎跟帖讨论。', 'admin', '站长'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='本周精选');

CREATE TABLE IF NOT EXISTS `reply_progress` (
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
UPDATE sys_user SET staff_post='moderator', staff_kind='clerk', nickname='版主' WHERE username='subadmin' AND role='admin' AND IFNULL(super_admin,0)=0;
