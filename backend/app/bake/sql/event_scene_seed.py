"""DOM-EVENT 按 scene 替换演示种子（表结构不变，只换人名/地点/公告）。

校园模板在 ``templates/DOM-EVENT.sql``；非校园开题 bake 时改写 INSERT，
避免养老/企业/随访题仍出现食堂/宿舍校园演示行。
"""

from __future__ import annotations

import re

from app.bake.scene_scan import scene_event_parts

# 与 templates/DOM-EVENT.sql 中种子块对齐；整块替换，避免半改漏行
_CAMPUS_SEED_RE = re.compile(
    r"INSERT INTO sys_user \(username, password, role, nickname, phone, profile_json, "
    r"super_admin, profile_editable, enabled\) VALUES\n"
    r".*?"
    r"INSERT INTO sys_notice \(title, content, publisher_username, publisher_name\)\n"
    r"SELECT '本周排查'.*?;\n",
    re.DOTALL,
)

_INSTITUTION_SEED = """\
INSERT INTO sys_user (username, password, role, nickname, phone, profile_json, super_admin, profile_editable, enabled) VALUES
('admin', 'admin123', 'admin', '机构主管', '13800000000', '{}', 1, 0, 1),
('subadmin', 'sub123', 'admin', '照护员', '13800000001', '{}', 0, 1, 1),
('user', 'user123', 'user', '家属甲', '13800000002',
 '{"realName":"李芳","email":"li@demo.com","gender":"女","identityType":"家属","elderName":"王德贵"}',
 0, 1, 1)
ON DUPLICATE KEY UPDATE nickname=VALUES(nickname), phone=VALUES(phone), profile_json=VALUES(profile_json);

INSERT IGNORE INTO category (id, name) VALUES (1, '体征异常'), (2, '跌倒风险'), (3, '慢病监测');
INSERT IGNORE INTO event_case (id, title, author, isbn, category_id, stock, status, stage) VALUES
(1, '王德贵', '照护员张敏', '一号楼 203 / 血压偏高待复核', 1, 1, 'available', '待核查'),
(2, '赵秀英', '照护员李华', '二号楼 105 / 夜间跌倒风险升高', 2, 1, 'available', '监测中'),
(3, '陈建华', '照护员王芳', '一号楼 311 / 血糖波动需加测', 3, 1, 'available', '处置中'),
(4, '刘桂兰', '照护员赵强', '三号楼 208 / 用药提醒已闭环', 1, 1, 'available', '已闭环'),
(5, '周明远', '照护员陈洁', '二号楼 402 / 体温偏高待观察', 2, 1, 'available', '待核查');
INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '照护须知', '请如实登记老人健康与照护要素；异常请及时上报并由主管确认处置。', 'admin', '机构主管'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='照护须知');
INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '本周排查', '请于周五前完成重点老人体征复核与跌倒风险巡查上报。', 'admin', '机构主管'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='本周排查');
"""

_COMMUNITY_SEED = """\
INSERT INTO sys_user (username, password, role, nickname, phone, profile_json, super_admin, profile_editable, enabled) VALUES
('admin', 'admin123', 'admin', '防控主管', '13800000000', '{}', 1, 0, 1),
('subadmin', 'sub123', 'admin', '值班员', '13800000001', '{}', 0, 1, 1),
('user', 'user123', 'user', '网格员甲', '13800000002',
 '{"realName":"周明","email":"zhou@demo.com","gender":"男","identityType":"网格员","communityName":"阳光小区","region":"3栋片区"}',
 0, 1, 1)
ON DUPLICATE KEY UPDATE nickname=VALUES(nickname), phone=VALUES(phone), profile_json=VALUES(profile_json);

INSERT IGNORE INTO category (id, name) VALUES (1, '传染病线索'), (2, '健康异常'), (3, '重点人群');
INSERT IGNORE INTO event_case (id, title, author, isbn, category_id, stock, status, stage) VALUES
(1, '张伟', '网格员李华', '阳光小区 3栋 / 聚集性发热待核查', 1, 1, 'available', '待核查'),
(2, '王芳', '网格员王芳', '阳光小区 2单元 / 体温异常待回访', 2, 1, 'available', '排查中'),
(3, '刘敏', '网格员张敏', '阳光小区 5栋 / 慢病随访待排查', 3, 1, 'available', '处置中'),
(4, '赵强', '网格员赵强', '阳光小区物业 / 消杀物资已闭环', 1, 1, 'available', '已闭环'),
(5, '陈洁', '网格员陈洁', '小区东门商铺 / 快检阳性复核', 2, 1, 'available', '待核查');
INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '上报须知', '请如实登记事件要素；重大事件请及时上报并由主管确认处置。', 'admin', '防控主管'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='上报须知');
INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '本周排查', '请于周五前完成网格重点对象复核与异常线索上报。', 'admin', '防控主管'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='本周排查');
"""

_ENTERPRISE_SEED = """\
INSERT INTO sys_user (username, password, role, nickname, phone, profile_json, super_admin, profile_editable, enabled) VALUES
('admin', 'admin123', 'admin', '企管主管', '13800000000', '{}', 1, 0, 1),
('subadmin', 'sub123', 'admin', '监测员', '13800000001', '{}', 0, 1, 1),
('user', 'user123', 'user', '员工甲', '13800000002',
 '{"realName":"周明","email":"zhou@demo.com","gender":"男","identityType":"员工","employeeNo":"E2026008","dept":"生产一部"}',
 0, 1, 1)
ON DUPLICATE KEY UPDATE nickname=VALUES(nickname), phone=VALUES(phone), profile_json=VALUES(profile_json);

INSERT IGNORE INTO category (id, name) VALUES (1, '体温异常'), (2, '暴露风险'), (3, '复工评估');
INSERT IGNORE INTO event_case (id, title, author, isbn, category_id, stock, status, stage) VALUES
(1, '周明', '监测员李华', '生产一部 / 晨检体温偏高', 1, 1, 'available', '待核查'),
(2, '王芳', '监测员王芳', '仓储组 / 同班次暴露待评估', 2, 1, 'available', '监测中'),
(3, '张敏', '监测员张敏', '行政办 / 复工材料待复核', 3, 1, 'available', '处置中'),
(4, '赵强', '监测员赵强', '生产二部 / 防护物资已闭环', 1, 1, 'available', '已闭环'),
(5, '陈洁', '监测员陈洁', '质检组 / 健康异常待观察', 2, 1, 'available', '待核查');
INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '监测须知', '请如实登记体温与健康状况；异常请及时上报并由主管确认复工评估。', 'admin', '企管主管'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='监测须知');
INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '本周排查', '请于周五前完成异常员工复核与复工评估上报。', 'admin', '企管主管'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='本周排查');
"""

_CLINIC_SEED = """\
INSERT INTO sys_user (username, password, role, nickname, phone, profile_json, super_admin, profile_editable, enabled) VALUES
('admin', 'admin123', 'admin', '公卫主管', '13800000000', '{}', 1, 0, 1),
('subadmin', 'sub123', 'admin', '随访员', '13800000001', '{}', 0, 1, 1),
('user', 'user123', 'user', '随访对象甲', '13800000002',
 '{"realName":"周明","email":"zhou@demo.com","gender":"男","identityType":"随访对象","patientNo":"P2026008","dept":"慢病管理站"}',
 0, 1, 1)
ON DUPLICATE KEY UPDATE nickname=VALUES(nickname), phone=VALUES(phone), profile_json=VALUES(profile_json);

INSERT IGNORE INTO category (id, name) VALUES (1, '高血压'), (2, '糖尿病'), (3, '高风险随访');
INSERT IGNORE INTO event_case (id, title, author, isbn, category_id, stock, status, stage) VALUES
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
"""

def apply_event_scene_seed(
    sql: str,
    *,
    title: str = "",
    proposal_text: str = "",
) -> str:
    """按 ``scene_event`` 替换 DOM-EVENT 演示种子；校园档保留模板原文。"""
    scene = scene_event_parts(title, proposal_text)
    if scene == "institution":
        seed = _INSTITUTION_SEED
    elif scene == "community":
        seed = _COMMUNITY_SEED
    elif scene == "enterprise":
        seed = _ENTERPRISE_SEED
    elif scene == "default":
        seed = _CLINIC_SEED
    else:
        return sql
    if not _CAMPUS_SEED_RE.search(sql):
        return sql
    return _CAMPUS_SEED_RE.sub(seed.rstrip() + "\n", sql, count=1)
