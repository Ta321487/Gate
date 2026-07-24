-- bake domain=DOM-BLOG · tables in [6,15]
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

-- 列结构与 ArchiveStore 默认 book 表兼容（title/author/isbn/stock）；isbn=富文本正文 HTML
CREATE TABLE IF NOT EXISTS article (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  title VARCHAR(200) NOT NULL,
  author VARCHAR(100),
  body_html TEXT,
  category_id BIGINT,
  stock INT DEFAULT 1,
  status VARCHAR(32) DEFAULT 'available',
  cover_url VARCHAR(255),
  summary VARCHAR(512) DEFAULT '',
  published_at DATETIME NULL,
  deleted_at DATETIME NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- book_id 列名兼容 TicketStore archive 模式（存 article.id）

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
('admin', 'admin123', 'admin', '主编', '13800000000', '{}', 1, 0, 1),
('subadmin', 'sub123', 'admin', '编辑甲', '13800000001', '{}', 0, 1, 1),
('user', 'user123', 'user', '读者甲', '13800000002',
 '{"realName":"王读者","email":"wang@demo.edu","gender":"女","memberNo":"R20260001","orgName":"文学院","preferredGenre":"技术"}',
 0, 1, 1)
ON DUPLICATE KEY UPDATE nickname=VALUES(nickname), phone=VALUES(phone), profile_json=VALUES(profile_json);

INSERT IGNORE INTO category (id, name) VALUES (1, '技术'), (2, '随笔'), (3, '资讯');
INSERT IGNORE INTO article (id, title, author, body_html, category_id, stock, status) VALUES
(1, '从零搭建个人博客', '主编', '<p>用 <strong>Spring Boot</strong> + <em>Vue</em> 搭一套可演示的文章站点。</p><ol><li>建库与种子</li><li>档案与收藏单据</li><li>富文本正文</li></ol>', 1, 1, 'available'),
(2, 'JdbcTemplate 幂等种子实践', '编辑甲', '<p>重启不 Cle 业务数据：</p><ul><li><code>INSERT IGNORE</code></li><li><code>WHERE NOT EXISTS</code></li></ul>', 1, 1, 'available'),
(3, '毕业季的咖啡馆', '读者甲', '<p>期末周的一角安静时光，写给即将离开的校园。</p>', 2, 1, 'available'),
(4, '读《设计中的设计》札记', '主编', '<p>关于日常与设计的几段摘录与感想。</p><blockquote>设计在于发现，而不是创造。</blockquote>', 2, 1, 'available'),
(5, '本站上线说明', '编辑甲', '<p>演示站点已开放<strong>阅读</strong>与<strong>收藏</strong>，欢迎留言建议。</p>', 3, 1, 'available');
INSERT IGNORE INTO sys_config (cfg_key, cfg_value, remark) VALUES
('blog_hint', '主编维护文章', '发布方式说明');
INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '阅读须知', '文章仅供学习演示；转载请注明出处。内容由主编维护发布。', 'admin', '主编'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='阅读须知');
INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '本周上新', '技术与随笔栏目已更新演示文章，欢迎收藏订阅。', 'admin', '主编'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='本周上新');

CREATE TABLE IF NOT EXISTS user_favorite (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  username VARCHAR(64) NOT NULL,
  item_id BIGINT NOT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uk_fav_user_item (username, item_id),
  KEY idx_fav_user (username, id)
);

-- staff posts (clerk / worker)
UPDATE sys_user SET staff_post='', staff_kind='' WHERE super_admin=1;
UPDATE sys_user SET staff_post='editor', staff_kind='clerk', nickname='编辑' WHERE username='subadmin' AND role='admin' AND IFNULL(super_admin,0)=0;
