-- bake domain=DOM-EVENT · tables in [${TABLE_COUNT_MIN},${TABLE_COUNT_MAX}]
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

-- ArchiveStore 兼容列；author=上报人；isbn=地点/摘要；stock=可上报标记
CREATE TABLE IF NOT EXISTS event_case (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  title VARCHAR(200) NOT NULL,
  author VARCHAR(100),
  isbn VARCHAR(256),
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

CREATE TABLE IF NOT EXISTS event_report_log (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  event_report_id BIGINT NOT NULL,
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
('admin', 'admin123', 'admin', '防控主管', '13800000000', '{}', 1, 0, 1),
('subadmin', 'sub123', 'admin', '值班员', '13800000001', '{}', 0, 1, 1),
('user', 'user123', 'user', '晨检员甲', '13800000002',
 '{"realName":"周明","email":"zhou@demo.com","gender":"男","employeeNo":"T2026008","dept":"校医院","jobTitle":"晨检员","region":"东区宿舍"}',
 0, 1, 1)
ON DUPLICATE KEY UPDATE nickname=VALUES(nickname), phone=VALUES(phone), profile_json=VALUES(profile_json);

INSERT IGNORE INTO category (id, name) VALUES (1, '传染病线索'), (2, '晨午检异常'), (3, '健康监测');
INSERT IGNORE INTO event_case (id, title, author, isbn, category_id, stock, status, stage) VALUES
(1, '南门聚集性发热报告', '校医李华', '南门广场 / 聚集性发热待核查', 1, 1, 'available', '待核查'),
(2, '食堂晨检异常', '食安员王芳', '一食堂窗口 / 晨检不合格', 2, 1, 'available', '排查中'),
(3, '宿舍楼疑似传染病报告', '楼管张敏', '3号楼 / 疑似传染病待排查', 3, 1, 'available', '处置中'),
(4, '校园消杀物资申领关联事件', '后勤赵强', '仓库区 / 消杀物资调度', 1, 1, 'available', '已闭环'),
(5, '校门口食品安全抽检', '市监联络员陈洁', '校东门商铺 / 快检阳性复核', 2, 1, 'available', '待核查');
INSERT IGNORE INTO sys_config (cfg_key, cfg_value, remark) VALUES
('report_hint', '请填写上报说明', '上报说明'),
('max_open_report', '20', '每人最大在途上报单');
INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '上报须知', '请如实登记事件要素；重大事件请及时上报并由主管确认处置。', 'admin', '防控主管'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='上报须知');
INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '本周排查', '请于周五前完成晨检异常与聚集性发热线索的复核上报。', 'admin', '防控主管'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='本周排查');
