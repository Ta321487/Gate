-- 业务库脚本：建库、建表与初始数据
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
  post_mute_until DATETIME NULL,
  failed_login_count INT NOT NULL DEFAULT 0,
  lock_until DATETIME NULL,
  must_change_password TINYINT NOT NULL DEFAULT 0,
  password_changed_at DATETIME NULL,
  security_question VARCHAR(128) NULL,
  security_answer_hash VARCHAR(128) NULL,
  email_activated TINYINT NOT NULL DEFAULT 0,
  activation_code VARCHAR(16) NULL,
  real_name_acked TINYINT NOT NULL DEFAULT 0,
  admin_tags VARCHAR(255) NOT NULL DEFAULT '',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 板块
CREATE TABLE IF NOT EXISTS category (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  name VARCHAR(64) NOT NULL UNIQUE,
  section_notice VARCHAR(512) NOT NULL DEFAULT ''
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
  view_count INT NOT NULL DEFAULT 0,
  pin_top TINYINT NOT NULL DEFAULT 0,
  essence TINYINT NOT NULL DEFAULT 0,
  locked TINYINT NOT NULL DEFAULT 0,
  owner_username VARCHAR(64) NOT NULL DEFAULT '',
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
  remark TEXT,
  parent_ticket_id BIGINT NULL,
  like_count INT NOT NULL DEFAULT 0
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
  deleted_at DATETIME NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  KEY idx_msg_user (username, id)
);

CREATE TABLE IF NOT EXISTS sys_notice (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  title VARCHAR(128) NOT NULL,
  content TEXT,
  publisher_username VARCHAR(64),
  publisher_name VARCHAR(64),
  pinned TINYINT NOT NULL DEFAULT 0,
  expire_at DATETIME NULL,
  force_ack TINYINT NOT NULL DEFAULT 0,
  content_fmt VARCHAR(16) NOT NULL DEFAULT 'text',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO sys_user (username, password, role, nickname, phone, profile_json, super_admin, profile_editable, enabled) VALUES
('admin', 'admin123', 'admin', '站长', '13800000000', '{}', 1, 0, 1),
('subadmin', 'sub123', 'admin', '版主甲', '13800000001', '{}', 0, 1, 1),
('user', 'user123', 'user', '居民甲', '13800000002',
 '{"realName":"王芳","email":"wang@demo.com","gender":"女","identityType":"居民","communityName":"阳光小区","preferredGenre":"邻里互助"}',
 0, 1, 1)
ON DUPLICATE KEY UPDATE nickname=VALUES(nickname), phone=VALUES(phone), profile_json=VALUES(profile_json);

INSERT IGNORE INTO category (id, name) VALUES (1, '邻里互助'), (2, '二手闲置'), (3, '活动通知');
INSERT IGNORE INTO board_moderator (id, category_id, username) VALUES
(1, 1, 'subadmin'), (2, 2, 'subadmin');
INSERT IGNORE INTO tag (id, name) VALUES (1, '求助'), (2, '闲置'), (3, '活动'), (4, '物业');
INSERT IGNORE INTO post (id, title, author, body_html, category_id, stock, status) VALUES
(1, '周末义诊与健康咨询', '业委会', '<p>本周六会所大厅开展<strong>义诊</strong>，欢迎邻里参加。</p>', 3, 1, 'available'),
(2, '出闲置折叠桌', '居民甲', '<p>九成新折叠桌，自提优先。</p>', 2, 1, 'available'),
(3, '寻周末拼车去火车站', '居民乙', '<p>周日上午出发，可拼两人。</p>', 1, 1, 'available'),
(4, '小区绿化浇水志愿者', '物业值班', '<p>本周志愿浇水时间表见楼下。</p>', 3, 1, 'available'),
(5, '求推荐靠谱开锁师傅', '居民丙', '<p>门锁偶发失灵，求邻里推荐。</p>', 1, 1, 'available');
INSERT IGNORE INTO reply (id, post_id, username, status, apply_at, approve_at, remark) VALUES
(1, 1, 'user', 'approved', NOW(), NOW(), '<p>我也想参加义诊，怎么报名？</p>'),
(2, 3, 'subadmin', 'approved', NOW(), NOW(), '<p>周日上午还可拼一人，私信楼主。</p>'),
(3, 5, 'user', 'pending', NOW(), NULL, '<p>推荐李师傅，上次换锁很快。</p>');
INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '社区公约', '请文明发帖；广告与人身攻击帖将被下架。', 'admin', '站长'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='社区公约');
INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '版块说明', '邻里互助与二手闲置请如实描述，线下交易注意安全。', 'admin', '站长'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='版块说明');

CREATE TABLE IF NOT EXISTS user_follow (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  follower VARCHAR(64) NOT NULL,
  followee VARCHAR(64) NOT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uk_uf_pair (follower, followee),
  KEY idx_uf_followee (followee)
);

CREATE TABLE IF NOT EXISTS `reply_progress` (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  ticket_id BIGINT NOT NULL,
  status VARCHAR(32) NOT NULL,
  operator VARCHAR(64),
  remark VARCHAR(255) DEFAULT '',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  KEY idx_progress_ticket (ticket_id, id)
);

CREATE TABLE IF NOT EXISTS content_report (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  username VARCHAR(64) NOT NULL,
  target_type VARCHAR(32) NOT NULL DEFAULT 'archive',
  target_id BIGINT NOT NULL,
  reason VARCHAR(512) NOT NULL,
  status VARCHAR(32) NOT NULL DEFAULT 'pending',
  handler VARCHAR(64) DEFAULT '',
  handle_note VARCHAR(512) DEFAULT '',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  handled_at DATETIME NULL,
  handle_deadline_at DATETIME NULL,
  KEY idx_creport_status (status, id),
  KEY idx_creport_target (target_type, target_id)
);

-- 会话登记、登录记录、注销申请
CREATE TABLE IF NOT EXISTS sys_auth_session (
  session_id VARCHAR(128) NOT NULL,
  username VARCHAR(64) NOT NULL,
  ip VARCHAR(64) NOT NULL DEFAULT '',
  user_agent VARCHAR(255) NOT NULL DEFAULT '',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  last_seen_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  kicked TINYINT NOT NULL DEFAULT 0,
  PRIMARY KEY (session_id),
  KEY idx_auth_sess_user (username, kicked)
);

CREATE TABLE IF NOT EXISTS sys_login_log (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  username VARCHAR(64) NOT NULL,
  ip VARCHAR(64) NOT NULL DEFAULT '',
  user_agent VARCHAR(255) NOT NULL DEFAULT '',
  geo_hint VARCHAR(64) NOT NULL DEFAULT '',
  success TINYINT NOT NULL DEFAULT 1,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  KEY idx_login_log_user (username, created_at)
);

CREATE TABLE IF NOT EXISTS sys_account_cancel (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  username VARCHAR(64) NOT NULL,
  reason VARCHAR(255) NOT NULL DEFAULT '',
  status VARCHAR(16) NOT NULL DEFAULT 'pending',
  admin_note VARCHAR(255) NOT NULL DEFAULT '',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  reviewed_at DATETIME NULL,
  KEY idx_cancel_user (username, status)
);
-- 业务试用账号首次登录须改密
UPDATE sys_user SET must_change_password=1 WHERE username='user' AND IFNULL(super_admin,0)=0;
-- 种子账号一律免激活闸（新注册仍走默认未激活）
UPDATE sys_user SET email_activated=1;

-- 强制公告确认 / 广告位多槽
CREATE TABLE IF NOT EXISTS sys_notice_ack (
  notice_id BIGINT NOT NULL,
  username VARCHAR(64) NOT NULL,
  acked_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (notice_id, username),
  KEY idx_notice_ack_user (username)
);

CREATE TABLE IF NOT EXISTS sys_banner (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  slot VARCHAR(32) NOT NULL DEFAULT 'home',
  title VARCHAR(128) NOT NULL DEFAULT '',
  lead_text VARCHAR(255) NOT NULL DEFAULT '',
  image_url VARCHAR(512) NOT NULL DEFAULT '',
  link_url VARCHAR(512) NOT NULL DEFAULT '',
  sort_order INT NOT NULL DEFAULT 0,
  enabled TINYINT NOT NULL DEFAULT 1,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  KEY idx_banner_slot (slot, enabled, sort_order)
);

INSERT INTO sys_banner (slot, title, lead_text, image_url, link_url, sort_order, enabled)
SELECT 'home', '欢迎使用', '系统已就绪，可开始浏览业务入口。', '', '/notices', 0, 1 FROM DUAL
WHERE NOT EXISTS (SELECT 1 FROM sys_banner WHERE slot='home' AND title='欢迎使用');

-- 简易站点访问量（按日）
CREATE TABLE IF NOT EXISTS sys_site_stat (
  day_key VARCHAR(10) NOT NULL,
  pv INT NOT NULL DEFAULT 0,
  PRIMARY KEY (day_key)
);

-- staff posts (clerk / worker)
UPDATE sys_user SET staff_post='', staff_kind='' WHERE super_admin=1;
INSERT INTO sys_user (username, password, role, nickname, phone, profile_json, super_admin, profile_editable, enabled, staff_post, staff_kind) VALUES ('subadmin', 'sub123', 'admin', '版主', '13800000001', '{}', 0, 1, 1, 'moderator', 'clerk') ON DUPLICATE KEY UPDATE nickname=VALUES(nickname), staff_post=VALUES(staff_post), staff_kind=VALUES(staff_kind), role='admin', super_admin=0;

-- 空封面时补默认图（post）
UPDATE `post` SET cover_url = ELT(1 + MOD(GREATEST(id, 1) - 1, 8),
  '/uploads/demo/cover-01.jpg',
  '/uploads/demo/cover-02.jpg',
  '/uploads/demo/cover-03.jpg',
  '/uploads/demo/cover-04.jpg',
  '/uploads/demo/cover-05.jpg',
  '/uploads/demo/cover-06.jpg',
  '/uploads/demo/cover-07.jpg',
  '/uploads/demo/cover-08.jpg'
)
WHERE cover_url IS NULL OR TRIM(cover_url) = '';
