-- bake domain=DOM-FORUM · tables in [${TABLE_COUNT_MIN},${TABLE_COUNT_MAX}]
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

-- 列结构与 ArchiveStore 默认 book 表兼容（title/author/isbn/stock）；isbn=正文摘要
CREATE TABLE IF NOT EXISTS post (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  title VARCHAR(200) NOT NULL,
  author VARCHAR(100),
  isbn VARCHAR(512),
  category_id BIGINT,
  stock INT DEFAULT 1,
  status VARCHAR(32) DEFAULT 'available',
  cover_url VARCHAR(255),
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- book_id 列名兼容 TicketStore archive 模式（存 post.id）；remark=回复正文（可含 @昵称 一层引用）
CREATE TABLE IF NOT EXISTS reply (
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
  remark VARCHAR(512)
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

CREATE TABLE IF NOT EXISTS reply_log (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  reply_id BIGINT NOT NULL,
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
('admin', 'admin123', 'admin', '站长', '13800000000', '{}', 1, 0, 1),
('subadmin', 'sub123', 'admin', '版主甲', '13800000001', '{}', 0, 1, 1),
('user', 'user123', 'user', '用户甲', '13800000002',
 '{"realName":"李同学","email":"li@demo.edu","gender":"男","memberNo":"U20260001","orgName":"计算机学院","preferredGenre":"学习交流"}',
 0, 1, 1)
ON DUPLICATE KEY UPDATE nickname=VALUES(nickname), phone=VALUES(phone), profile_json=VALUES(profile_json);

INSERT IGNORE INTO category (id, name) VALUES (1, '学习交流'), (2, '校园生活'), (3, '二手信息');
INSERT IGNORE INTO post (id, title, author, isbn, category_id, stock, status) VALUES
(1, '期末复习资料汇总', '学长甲', '高等数学、数据结构复习提纲与答疑时间。', 1, 1, 'available'),
(2, '实验室开放预约说明', '版主甲', '工作日晚间机房开放，请先跟帖再入场。', 1, 1, 'available'),
(3, '周末校园徒步召集', '用户甲', '周六上午图书馆集合，路线约 5 公里。', 2, 1, 'available'),
(4, '食堂新窗口试吃反馈', '美食观察', '三食堂二楼新增轻食窗口，欢迎跟帖补充评价。', 2, 1, 'available'),
(5, '出闲置显示器一台', '用户甲', '24 寸 IPS，成色良好，面交优先。', 3, 1, 'available');
INSERT IGNORE INTO reply (id, book_id, username, status, apply_at, approve_at, remark) VALUES
(1, 1, 'user', 'approved', NOW(), NOW(), '求一份离散数学提纲，谢谢楼主！'),
(2, 1, 'subadmin', 'approved', NOW(), NOW(), '@用户甲 离散提纲已上传到网盘，见一楼补充。'),
(3, 3, 'user', 'pending', NOW(), NULL, '我报名，带相机记录路线。');
INSERT IGNORE INTO sys_config (cfg_key, cfg_value, remark) VALUES
('max_reply', '50', '每人每帖回复上限提示'),
('forum_hint', '主帖站长维护，回复可审核', '发帖方式说明');
INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '社区公约', '请文明讨论；回复经版主审核后展示。主帖由站长维护，回复可 @他人 一层引用形成楼中楼。', 'admin', '站长'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='社区公约');
INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '本周精选', '学习交流与校园生活板块已更新演示主帖，欢迎跟帖讨论。', 'admin', '站长'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='本周精选');
