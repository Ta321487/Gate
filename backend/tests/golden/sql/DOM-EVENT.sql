-- bake domain=DOM-EVENT · tables in [6,15]
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

-- ArchiveStore 兼容列；author=上报人；isbn=地点/摘要；stock=可上报标记
CREATE TABLE IF NOT EXISTS event_case (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  title VARCHAR(200) NOT NULL,
  reporter_name VARCHAR(100),
  location_note VARCHAR(255),
  category_id BIGINT,
  stock INT DEFAULT 1,
  status VARCHAR(32) DEFAULT 'available',
  cover_url VARCHAR(255),
  stage VARCHAR(32) DEFAULT '待核查',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- event_id=event_case.id
CREATE TABLE IF NOT EXISTS event_report (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  event_id BIGINT NOT NULL,
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
('admin', 'admin123', 'admin', '公卫主管', '13800000000', '{}', 1, 0, 1),
('subadmin', 'sub123', 'admin', '随访员', '13800000001', '{}', 0, 1, 1),
('user', 'user123', 'user', '随访对象甲', '13800000002',
 '{"realName":"周明","email":"zhou@demo.com","gender":"男","identityType":"随访对象","patientNo":"P2026008","dept":"慢病管理站"}',
 0, 1, 1)
ON DUPLICATE KEY UPDATE nickname=VALUES(nickname), phone=VALUES(phone), profile_json=VALUES(profile_json);

INSERT IGNORE INTO category (id, name) VALUES (1, '高血压'), (2, '糖尿病'), (3, '高风险随访');
INSERT IGNORE INTO event_case (id, title, reporter_name, location_note, category_id, stock, status, stage) VALUES
(1, '周明', '随访员李华', '高血压 / 血压偏高待复核', 1, 1, 'available', '待核查'),
(2, '王芳', '随访员王芳', '糖尿病 / 血糖波动待回访', 2, 1, 'available', '随访中'),
(3, '张敏', '随访员张敏', '冠心病 / 用药依从待排查', 3, 1, 'available', '处置中'),
(4, '赵强', '随访员赵强', '高血压 / 季度随访已闭环', 1, 1, 'available', '已闭环'),
(5, '陈洁', '随访员陈洁', '糖尿病 / 并发症筛查待观察', 2, 1, 'available', '待核查');
INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '随访须知', '请如实登记随访要素与指标；异常请及时上报并由主管确认处置。', 'admin', '公卫主管'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='随访须知');
INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '本周排查', '请于周五前完成高风险对象指标复核与随访上报。', 'admin', '公卫主管'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='本周排查');

CREATE TABLE IF NOT EXISTS `event_report_progress` (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  ticket_id BIGINT NOT NULL,
  status VARCHAR(32) NOT NULL,
  operator VARCHAR(64),
  remark VARCHAR(255) DEFAULT '',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  KEY idx_progress_ticket (ticket_id, id)
);

CREATE TABLE IF NOT EXISTS archive_log (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  item_id BIGINT NOT NULL,
  username VARCHAR(64) NOT NULL,
  log_date DATE NOT NULL,
  log_type VARCHAR(32) NOT NULL DEFAULT 'checkin',
  payload_json TEXT,
  abnormal TINYINT DEFAULT 0,
  remark VARCHAR(512) DEFAULT '',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  KEY idx_alog_item_date (item_id, log_date),
  KEY idx_alog_date_type (log_date, log_type),
  KEY idx_alog_user (username, id)
);

-- staff posts (clerk / worker)
UPDATE sys_user SET staff_post='', staff_kind='' WHERE super_admin=1;
UPDATE sys_user SET staff_post='duty_clerk', staff_kind='clerk', nickname='值班员' WHERE username='subadmin' AND role='admin' AND IFNULL(super_admin,0)=0;
