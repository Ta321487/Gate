-- bake domain=DOM-MUSIC · tables in [${TABLE_COUNT_MIN},${TABLE_COUNT_MAX}]
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

-- 列结构与 ArchiveStore 默认 book 表兼容（title/author/isbn/stock）；isbn=播放链接
CREATE TABLE IF NOT EXISTS track (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  title VARCHAR(200) NOT NULL,
  author VARCHAR(100),
  isbn VARCHAR(512),
  category_id BIGINT,
  stock INT DEFAULT 1,
  status VARCHAR(32) DEFAULT 'available',
  cover_url VARCHAR(255),
  deleted_at DATETIME NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- book_id 列名兼容 TicketStore archive 模式（存 track.id）
CREATE TABLE IF NOT EXISTS favorite (
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
  remark VARCHAR(255)
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

CREATE TABLE IF NOT EXISTS favorite_log (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  favorite_id BIGINT NOT NULL,
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
('admin', 'admin123', 'admin', '曲库主管', '13800000000', '{}', 1, 0, 1),
('subadmin', 'sub123', 'admin', '运营编辑', '13800000001', '{}', 0, 1, 1),
('user', 'user123', 'user', '听众甲', '13800000002',
 '{"realName":"陈听友","email":"chen@demo.edu","gender":"男","memberNo":"M20260011","orgName":"艺术学院","preferredGenre":"流行"}',
 0, 1, 1)
ON DUPLICATE KEY UPDATE nickname=VALUES(nickname), phone=VALUES(phone), profile_json=VALUES(profile_json);

INSERT IGNORE INTO category (id, name) VALUES (1, '流行'), (2, '摇滚'), (3, '民谣');
INSERT IGNORE INTO track (id, title, author, isbn, category_id, stock, status) VALUES
(1, '校园晚风', '歌手甲 / 青春专辑', 'https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3', 1, 1, 'available'),
(2, '实验室节奏', '乐队乙', 'https://www.soundhelix.com/examples/mp3/SoundHelix-Song-2.mp3', 2, 1, 'available'),
(3, '图书馆角落', '歌手丙', 'https://www.soundhelix.com/examples/mp3/SoundHelix-Song-3.mp3', 3, 1, 'available'),
(4, '毕业季合唱', '合唱团丁', 'https://www.soundhelix.com/examples/mp3/SoundHelix-Song-4.mp3', 1, 1, 'available'),
(5, '夜跑歌单', '制作人戊', 'https://www.soundhelix.com/examples/mp3/SoundHelix-Song-5.mp3', 2, 1, 'available');
INSERT IGNORE INTO sys_config (cfg_key, cfg_value, remark) VALUES
('max_favorite', '30', '每人最大收藏数提示'),
('play_hint', '外链演示', '播放方式说明');
INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '试听须知', '曲源仅供学习演示；请尊重版权，勿传播未授权内容。', 'admin', '曲库主管'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='试听须知');
INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '本周上新', '流行与民谣栏目已更新演示曲目，欢迎收藏喜欢。', 'admin', '曲库主管'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='本周上新');
