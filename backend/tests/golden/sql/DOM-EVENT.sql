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

CREATE TABLE IF NOT EXISTS sys_config (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  cfg_key VARCHAR(64) NOT NULL UNIQUE,
  cfg_value VARCHAR(255) NOT NULL,
  remark VARCHAR(128) DEFAULT ''
);

INSERT INTO sys_user (username, password, role, nickname, phone, profile_json, super_admin, profile_editable, enabled) VALUES
('admin', 'admin123', 'admin', '应急主管', '13800000000', '{}', 1, 0, 1),
('subadmin', 'sub123', 'admin', '网格员', '13800000001', '{}', 0, 1, 1),
('user', 'user123', 'user', '网格员甲', '13800000002',
 '{"realName":"周明","email":"zhou@demo.com","gender":"男","employeeNo":"G2026008","dept":"应急网格","jobTitle":"网格员","region":"华东"}',
 0, 1, 1)
ON DUPLICATE KEY UPDATE nickname=VALUES(nickname), phone=VALUES(phone), profile_json=VALUES(profile_json);

INSERT IGNORE INTO category (id, name) VALUES (1, '应急事件'), (2, '日常隐患'), (3, '公卫监测');
INSERT IGNORE INTO event_case (id, title, reporter_name, location_note, category_id, stock, status, stage) VALUES
(1, '南门网格聚集性发热报告', '网格员李华', '南门广场 / 聚集性发热待核查', 1, 1, 'available', '待核查'),
(2, '食堂晨检异常', '食安员王芳', '一食堂窗口 / 晨检不合格', 2, 1, 'available', '排查中'),
(3, '宿舍楼疑似传染病报告', '楼管张敏', '3号楼 / 疑似传染病待排查', 3, 1, 'available', '处置中'),
(4, '校园消杀物资申领关联事件', '后勤赵强', '仓库区 / 消杀物资调度', 1, 1, 'available', '已闭环'),
(5, '校门口食品安全抽检', '市监联络员陈洁', '校东门商铺 / 快检阳性复核', 2, 1, 'available', '待核查');
INSERT IGNORE INTO sys_config (cfg_key, cfg_value, remark) VALUES
('report_hint', '请填写上报说明', '上报说明'),
('max_open_report', '20', '每人最大在途上报单');
INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '上报须知', '请如实登记事件要素；重大事件请及时上报并由主管确认处置。', 'admin', '应急主管'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='上报须知');
INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '本周排查', '请于周五前完成晨检异常与聚集性发热线索的复核上报。', 'admin', '应急主管'
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
