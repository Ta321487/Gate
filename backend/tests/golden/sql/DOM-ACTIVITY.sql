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

CREATE TABLE IF NOT EXISTS category (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  name VARCHAR(64) NOT NULL UNIQUE
);

-- ArchiveStore 兼容列；stock=剩余名额；start/end 供时间冲突；apply_deadline_at 报名截止
CREATE TABLE IF NOT EXISTS activity (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  title VARCHAR(200) NOT NULL,
  organizer VARCHAR(100),
  venue VARCHAR(128),
  category_id BIGINT,
  stock INT DEFAULT 0,
  status VARCHAR(32) DEFAULT 'available',
  cover_url VARCHAR(255),
  checkin_code VARCHAR(16) NOT NULL DEFAULT '',
  start_at DATETIME NULL,
  end_at DATETIME NULL,
  apply_deadline_at DATETIME NULL,
  service_hours DECIMAL(4,1) DEFAULT 0,
  checkin_place VARCHAR(128) DEFAULT '',
  session_group VARCHAR(64) DEFAULT '',
  apply_invite_code VARCHAR(64) DEFAULT '',
  sponsor_note VARCHAR(255) DEFAULT '',
  group_price_note TEXT NULL,
  fee_yuan DECIMAL(10,2) NULL,
  allowed_gender VARCHAR(16) DEFAULT '',
  allowed_grades VARCHAR(64) DEFAULT '',
  volunteer_role VARCHAR(64) DEFAULT '',
  admit_mode VARCHAR(32) DEFAULT '先到先得',
  seat_zones VARCHAR(255) DEFAULT '',
  pin_top TINYINT NOT NULL DEFAULT 0,
  survey_form_id BIGINT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- book_id=activity.id
CREATE TABLE IF NOT EXISTS signup (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  activity_id BIGINT NOT NULL,
  username VARCHAR(64) NOT NULL,
  status VARCHAR(32) NOT NULL DEFAULT 'pending',
  assignee_username VARCHAR(64) NULL,
  apply_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  approve_at DATETIME NULL,
  return_at DATETIME NULL,
  remark VARCHAR(255),
  notice_ack TINYINT NOT NULL DEFAULT 0,
  rating INT NULL,
  rating_remark VARCHAR(255) NOT NULL DEFAULT '',
  rated_at DATETIME NULL,
  checked_in_at DATETIME NULL,
  fine_status VARCHAR(16) DEFAULT 'none'
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
('admin', 'admin123', 'admin', '活动主管', '13800000000', '{}', 1, 0, 1),
('subadmin', 'sub123', 'admin', '活动助理', '13800000001', '{}', 0, 1, 1),
('user', 'user123', 'user', '报名者甲', '13800000002',
 '{"realName":"李同学","email":"li@demo.edu","gender":"男","studentNoOrEmp":"S20260001","dept":"计算机学院","identityType":"学生","orgOrClub":"青年志愿者协会"}',
 0, 1, 1)
ON DUPLICATE KEY UPDATE nickname=VALUES(nickname), phone=VALUES(phone), profile_json=VALUES(profile_json);

INSERT IGNORE INTO category (id, name) VALUES
(1, '社团活动'), (2, '志愿活动'), (3, '讲座'),
(4, '证书培训'), (5, '研学赛事'), (6, '票务开放日');
-- 1 与 4 时段重叠，便于校验时段冲突；截止日放在开课前
INSERT IGNORE INTO activity (id, title, organizer, venue, category_id, stock, status, start_at, end_at, apply_deadline_at) VALUES
(1, '编程马拉松校内赛', '计算机协会', '创新楼报告厅', 1, 40, 'available', '2026-10-11 09:00:00', '2026-10-11 17:00:00', '2026-10-10 23:59:59'),
(2, '校园环保志愿清扫', '青年志愿者协会', '南门集合', 2, 30, 'available', '2026-10-12 08:30:00', '2026-10-12 11:30:00', '2026-10-11 20:00:00'),
(3, '就业指导讲座', '就业指导中心', '图书馆报告厅', 3, 80, 'available', '2026-10-15 19:00:00', '2026-10-15 21:00:00', '2026-10-15 12:00:00'),
(4, '摄影社外拍活动', '摄影社', '湿地公园', 1, 20, 'available', '2026-10-11 14:00:00', '2026-10-11 17:00:00', '2026-10-10 23:59:59'),
(5, '敬老院慰问志愿', '青年志愿者协会', '校门口集合', 2, 15, 'available', '2026-10-19 09:00:00', '2026-10-19 12:00:00', '2026-10-18 18:00:00');
INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '报名须知', '请如实填写资料；名额有限，审核通过后请按时参加。', 'admin', '活动主管'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='报名须知');
INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '本周精选', '编程马拉松与环保志愿已开放报名，欢迎参加。', 'admin', '活动主管'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='本周精选');
-- 主路径样例：样例账号一条待审报名（占名额须审核通过后）
INSERT IGNORE INTO signup (id, activity_id, username, status, remark) VALUES
(1, 3, 'user', 'pending', '希望参加就业指导讲座。');

UPDATE activity SET checkin_code=CONCAT('ACT', LPAD(id, 3, '0')) WHERE checkin_code='' OR checkin_code IS NULL;

CREATE TABLE IF NOT EXISTS `signup_progress` (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  ticket_id BIGINT NOT NULL,
  status VARCHAR(32) NOT NULL,
  operator VARCHAR(64),
  remark VARCHAR(255) DEFAULT '',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  KEY idx_progress_ticket (ticket_id, id)
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

CREATE TABLE IF NOT EXISTS apply_blacklist (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  username VARCHAR(64) NOT NULL,
  reason VARCHAR(255) DEFAULT '',
  status VARCHAR(32) NOT NULL DEFAULT 'blocked',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uk_apply_blacklist_user (username)
);

-- staff posts (clerk / worker)
UPDATE sys_user SET staff_post='', staff_kind='' WHERE super_admin=1;
INSERT INTO sys_user (username, password, role, nickname, phone, profile_json, super_admin, profile_editable, enabled, staff_post, staff_kind) VALUES ('subadmin', 'sub123', 'admin', '活动助理', '13800000001', '{}', 0, 1, 1, 'assistant', 'clerk') ON DUPLICATE KEY UPDATE nickname=VALUES(nickname), staff_post=VALUES(staff_post), staff_kind=VALUES(staff_kind), role='admin', super_admin=0;

-- 空封面时补默认图（activity）
UPDATE `activity` SET cover_url = ELT(1 + MOD(GREATEST(id, 1) - 1, 8),
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
