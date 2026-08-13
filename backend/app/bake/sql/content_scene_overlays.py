"""内容族深皮种子（BLOG 记者站 / MEDIA 点播课 / MUSIC 点歌台 / FORUM 表白墙）。"""

from __future__ import annotations

BLOG_PRESS = """\
INSERT INTO sys_user (username, password, role, nickname, phone, profile_json, super_admin, profile_editable, enabled) VALUES
('admin', 'admin123', 'admin', '记者站主编', '13800000000', '{}', 1, 0, 1),
('subadmin', 'sub123', 'admin', '编辑甲', '13800000001', '{}', 0, 1, 1),
('user', 'user123', 'user', '读者甲', '13800000002',
 '{"realName":"王同学","email":"wang@demo.edu","gender":"女","identityType":"学生","studentNo":"S20260021","dept":"文学院","preferredGenre":"广播稿"}',
 0, 1, 1)
ON DUPLICATE KEY UPDATE nickname=VALUES(nickname), phone=VALUES(phone), profile_json=VALUES(profile_json);

INSERT IGNORE INTO category (id, name) VALUES (1, '广播稿'), (2, '图文报道'), (3, '专题');
INSERT IGNORE INTO article (id, title, author, isbn, category_id, stock, status) VALUES
(1, '本周校园要闻联播稿', '记者站', '<p>周一至周五早间联播要点。</p>', 1, 1, 'available'),
(2, '运动会开幕式现场报道', '记者乙', '<p>开幕式流程与精彩瞬间。</p>', 2, 1, 'available'),
(3, '心理健康月专题稿', '记者丙', '<p>讲座预告与采访摘要。</p>', 3, 1, 'available'),
(4, '食堂新窗口试吃短讯', '记者丁', '<p>三食堂轻食窗口试吃反馈。</p>', 2, 1, 'available'),
(5, '期末温馨提示广播稿', '记者站', '<p>复习周开放机房与图书馆延时。</p>', 1, 1, 'available');
INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '投稿须知', '稿件由编辑上架发布；读者可浏览收藏。转载请注明出处。', 'admin', '记者站主编'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='投稿须知' OR title='阅读须知');
INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '本周上新', '广播稿与图文报道已更新，欢迎收藏订阅。', 'admin', '记者站主编'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='本周上新');
"""

MEDIA_COURSEVOD = """\
INSERT INTO sys_user (username, password, role, nickname, phone, profile_json, super_admin, profile_editable, enabled) VALUES
('admin', 'admin123', 'admin', '课程视频库主管', '13800000000', '{}', 1, 0, 1),
('subadmin', 'sub123', 'admin', '运营编辑', '13800000001', '{}', 0, 1, 1),
('user', 'user123', 'user', '学员甲', '13800000002',
 '{"realName":"周同学","email":"zhou@demo.edu","gender":"女","identityType":"学生","studentNo":"S20260001","dept":"计算机学院","preferredGenre":"点播课"}',
 0, 1, 1)
ON DUPLICATE KEY UPDATE nickname=VALUES(nickname), phone=VALUES(phone), profile_json=VALUES(profile_json);

INSERT IGNORE INTO category (id, name) VALUES (1, '专业课'), (2, '通识课'), (3, '实验演示');
INSERT IGNORE INTO media (id, title, author, isbn, category_id, stock, status) VALUES
(1, '数据结构第 1 讲', '张老师', 'https://www.w3schools.com/html/mov_bbb.mp4', 1, 1, 'available'),
(2, '高等数学微课：极限', '李老师', 'https://www.w3schools.com/html/mov_bbb.mp4', 2, 1, 'available'),
(3, '电路实验操作演示', '王老师', 'https://www.w3schools.com/html/mov_bbb.mp4', 3, 1, 'available'),
(4, 'Python 入门第 3 讲', '赵老师', 'https://www.w3schools.com/html/mov_bbb.mp4', 1, 1, 'available'),
(5, '大学写作通识精讲', '陈老师', 'https://www.w3schools.com/html/mov_bbb.mp4', 2, 1, 'available');
INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '点播须知', '课程视频仅供学习点播；非选课占名额。请勿传播未授权内容。', 'admin', '课程视频库主管'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='点播须知' OR title='观影须知');
INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '本周上新', '专业课与实验演示已更新，欢迎收藏想看。', 'admin', '课程视频库主管'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='本周上新');
"""

MUSIC_KARAOKE = """\
INSERT INTO sys_user (username, password, role, nickname, phone, profile_json, super_admin, profile_editable, enabled) VALUES
('admin', 'admin123', 'admin', '点歌台主管', '13800000000', '{}', 1, 0, 1),
('subadmin', 'sub123', 'admin', '运营编辑', '13800000001', '{}', 0, 1, 1),
('user', 'user123', 'user', '听众甲', '13800000002',
 '{"realName":"陈同学","email":"chen@demo.edu","gender":"男","identityType":"学生","studentNo":"S20260011","dept":"艺术学院","preferredGenre":"点歌"}',
 0, 1, 1)
ON DUPLICATE KEY UPDATE nickname=VALUES(nickname), phone=VALUES(phone), profile_json=VALUES(profile_json);

INSERT IGNORE INTO category (id, name) VALUES (1, '热门点歌'), (2, '校园原创'), (3, '合唱');
INSERT IGNORE INTO track (id, title, author, isbn, category_id, stock, status) VALUES
(1, '晚自习点歌 · 晴天', '点歌台曲库', 'https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3', 1, 1, 'available'),
(2, '图书馆角落', '原创社', 'https://www.soundhelix.com/examples/mp3/SoundHelix-Song-2.mp3', 2, 1, 'available'),
(3, '校歌合唱版', '校合唱团', 'https://www.soundhelix.com/examples/mp3/SoundHelix-Song-3.mp3', 3, 1, 'available'),
(4, '毕业季点歌 · 同行', '点歌台曲库', 'https://www.soundhelix.com/examples/mp3/SoundHelix-Song-4.mp3', 1, 1, 'available'),
(5, '运动会进行曲', '军乐队', 'https://www.soundhelix.com/examples/mp3/SoundHelix-Song-5.mp3', 3, 1, 'available');
INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '点歌须知', '曲库供点歌试听；非直播连麦。请尊重版权。', 'admin', '点歌台主管'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='点歌须知' OR title='试听须知');
INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '本周上新', '热门点歌与校园原创已更新，欢迎收藏喜欢。', 'admin', '点歌台主管'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='本周上新');
"""

FORUM_WALL = """\
INSERT INTO sys_user (username, password, role, nickname, phone, profile_json, super_admin, profile_editable, enabled) VALUES
('admin', 'admin123', 'admin', '站长', '13800000000', '{}', 1, 0, 1),
('subadmin', 'sub123', 'admin', '版主甲', '13800000001', '{}', 0, 1, 1),
('user', 'user123', 'user', '用户甲', '13800000002',
 '{"realName":"李同学","email":"li@demo.edu","gender":"男","identityType":"学生","studentNo":"S20260001","dept":"计算机学院","preferredGenre":"表白墙"}',
 0, 1, 1)
ON DUPLICATE KEY UPDATE nickname=VALUES(nickname), phone=VALUES(phone), profile_json=VALUES(profile_json);

INSERT IGNORE INTO category (id, name) VALUES (1, '表白墙'), (2, '树洞'), (3, '失物招领墙');
INSERT IGNORE INTO board_moderator (id, category_id, username) VALUES
(1, 1, 'subadmin'), (2, 2, 'subadmin');
INSERT IGNORE INTO tag (id, name) VALUES (1, '表白'), (2, '树洞'), (3, '祝福'), (4, '寻物');
INSERT IGNORE INTO post (id, title, author, isbn, category_id, stock, status) VALUES
(1, '图书馆三楼的那位同学', '匿名甲', '<p>谢谢你那天借我充电宝，想认识一下。</p>', 1, 1, 'available'),
(2, '最近压力有点大', '匿名乙', '<p>期末周睡不好，求安慰与作息建议。</p>', 2, 1, 'available'),
(3, '祝室友生日快乐', '用户甲', '<p>宿舍 405，今晚小蛋糕！</p>', 1, 1, 'available'),
(4, '树洞：实习选择困难', '匿名丙', '<p>两家实习 offer 怎么选，求过来人经验。</p>', 2, 1, 'available'),
(5, '寻：蓝色水杯落在二食堂', '用户甲', '<p>杯身有贴纸，看到请跟帖。</p>', 3, 1, 'available');
INSERT IGNORE INTO post_tag (post_id, tag_id) VALUES (1, 1), (2, 2), (3, 3), (5, 4);
INSERT IGNORE INTO reply (id, book_id, username, status, apply_at, approve_at, remark) VALUES
(1, 1, 'user', 'approved', NOW(), NOW(), '<p>加油！图书馆常去也可以再偶遇。</p>'),
(2, 2, 'subadmin', 'approved', NOW(), NOW(), '<p>心理中心有开放日，可预约聊聊。</p>'),
(3, 5, 'user', 'pending', NOW(), NULL, '<p>好像在二食堂失物柜见过，待确认。</p>');
INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '表白墙公约', '请文明发言；回复经版主审核后展示。禁止人身攻击与广告。', 'admin', '站长'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='表白墙公约' OR title='社区公约');
INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '本周精选', '表白墙与树洞已更新，欢迎跟帖互动。', 'admin', '站长'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='本周精选');
"""
