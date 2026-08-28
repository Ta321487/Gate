-- bake domain=DOM-CHECKIN · tables in [${TABLE_COUNT_MIN},${TABLE_COUNT_MAX}]
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

-- ArchiveStore：title=寝室号；author=楼栋；stock=应签人数；checkin_code + 起止窗口
CREATE TABLE IF NOT EXISTS dorm_room (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  title VARCHAR(200) NOT NULL,
  author VARCHAR(100),
  isbn VARCHAR(256),
  category_id BIGINT,
  stock INT DEFAULT 0,
  status VARCHAR(32) DEFAULT 'available',
  cover_url VARCHAR(255),
  checkin_code VARCHAR(16) NOT NULL DEFAULT '',
  start_at DATETIME NULL,
  end_at DATETIME NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS checkin_apply (
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
  next_follow_at DATETIME NULL,
  checked_in_at DATETIME NULL,
  fine_status VARCHAR(32) DEFAULT ''
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

CREATE TABLE IF NOT EXISTS checkin_apply_log (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  checkin_apply_id BIGINT NOT NULL,
  action VARCHAR(32) NOT NULL,
  operator VARCHAR(64),
  remark VARCHAR(255) DEFAULT '',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO sys_user (username, password, role, nickname, phone, profile_json, super_admin, profile_editable, enabled) VALUES
('admin', 'admin123', 'admin', '宿管主管', '13800000000', '{}', 1, 0, 1),
('subadmin', 'sub123', 'admin', '查寝员', '13800000001', '{}', 0, 1, 1),
('user', 'user123', 'user', '学生甲', '13800000002',
 '{"realName":"样例学生","email":"stu@demo.edu","gender":"男","studentNo":"20230001","dept":"计算机学院","dormBuilding":"1号楼","dormRoom":"101"}',
 0, 1, 1)
ON DUPLICATE KEY UPDATE nickname=VALUES(nickname), phone=VALUES(phone), profile_json=VALUES(profile_json);

INSERT IGNORE INTO category (id, name) VALUES (1, '一号楼'), (2, '二号楼'), (3, '集中查寝');
INSERT IGNORE INTO dorm_room (id, title, author, isbn, category_id, stock, status, checkin_code, start_at, end_at) VALUES
(1, '1栋101', '1号楼', '四人间', 1, 4, 'available', 'CK101', DATE_ADD(CURDATE(), INTERVAL 22 HOUR), DATE_ADD(CURDATE(), INTERVAL 23 HOUR)),
(2, '1栋102', '1号楼', '四人间', 1, 4, 'available', 'CK102', DATE_ADD(CURDATE(), INTERVAL 22 HOUR), DATE_ADD(CURDATE(), INTERVAL 23 HOUR)),
(3, '2栋205', '2号楼', '六人间', 2, 6, 'available', 'CK205', DATE_ADD(CURDATE(), INTERVAL 22 HOUR), DATE_ADD(CURDATE(), INTERVAL 23 HOUR)),
(4, '集中查寝点', '宿管中心', '临时批次', 3, 30, 'available', 'CK999', DATE_ADD(CURDATE(), INTERVAL 21 HOUR), DATE_ADD(CURDATE(), INTERVAL 23 HOUR));
UPDATE dorm_room SET checkin_code=CONCAT('CK', LPAD(id, 3, '0')) WHERE checkin_code='' OR checkin_code IS NULL;
INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '查寝须知', '请先在个人资料填写本人楼栋与房间，再提交归寝登记并等待宿管审核；通过后在查寝窗口内凭签到码完成归寝签到。只能对本寝室场次登记。人脸/GPS 不在本期。窗口结束后仍未签到记缺勤。', 'admin', '宿管主管'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='查寝须知');
