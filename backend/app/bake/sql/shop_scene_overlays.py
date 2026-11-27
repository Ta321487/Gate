"""交易皮场景种子：食堂/商城/影院/寄养等 + 条件分/农场列/多店补丁。"""

from __future__ import annotations

import re

from app.bake.sql.scene_seed_util import (
    _shop_workbench_orders_sql,
    _workbench_orders_sql,
)

_FOOD_CANTEEN = f"""\
INSERT INTO sys_user (username, password, role, nickname, phone, profile_json, super_admin, profile_editable, enabled) VALUES
('admin', 'admin123', 'admin', '食堂主管', '13800000000', '{{}}', 1, 0, 1),
('subadmin', 'sub123', 'admin', '档口店员', '13800000001', '{{}}', 0, 1, 1),
('user', 'user123', 'user', '用餐者甲', '13800000002',
 '{{"realName":"李同学","email":"li@demo.edu","gender":"女","receiverName":"李同学","pickupType":"堂食","preferredStore":"窗口A","memberNo":"S20260002"}}',
 0, 1, 1)
ON DUPLICATE KEY UPDATE nickname=VALUES(nickname), phone=VALUES(phone), profile_json=VALUES(profile_json);

INSERT IGNORE INTO category (id, name) VALUES (1, '套餐'), (2, '面食'), (3, '饮品');
INSERT IGNORE INTO dish (id, title, author, isbn, category_id, stock, status) VALUES
(1, '红烧肉套餐', '18.00', '窗口A', 1, 79, 'available'),
(2, '番茄鸡蛋面', '12.00', '窗口B', 2, 60, 'available'),
(3, '豆浆油条', '8.00', '早餐档', 1, 100, 'available'),
(4, '柠檬茶', '6.00', '饮品站', 3, 120, 'available');

INSERT IGNORE INTO user_address (id, username, contact_name, phone, address_line, tag, is_default) VALUES
(1, 'user', '李同学', '13800000002', '学生公寓 3 号楼 405', '宿舍', 1),
(2, 'user', '李同学', '13800000002', '教学楼 A 座门口', '自取', 0),
(3, 'user', '李同学', '13800000002', '二食堂北门', '食堂', 0);

INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '食堂点餐', '下单后到对应窗口取餐；外卖请选宿舍地址。', 'admin', '食堂主管'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='食堂点餐' OR title='点餐须知');
{_workbench_orders_sql(
    [
        (1, 1, "红烧肉套餐", 18.00, "pending", "窗口A取餐"),
        (2, 2, "番茄鸡蛋面", 12.00, "confirmed", "窗口B已接单"),
        (3, 3, "豆浆油条", 8.00, "shipped", "早餐配送中"),
        (4, 4, "柠檬茶", 6.00, "completed", "已取餐"),
    ],
    contact="李同学",
    address="学生公寓 3 号楼 405",
    delivery="堂食",
    taste_by_oid={1: "不辣", 2: "少油", 3: "", 4: "少冰"},
)}"""

_SHOP_RETAIL = f"""\
INSERT INTO sys_user (username, password, role, nickname, phone, profile_json, super_admin, profile_editable, enabled) VALUES
('admin', 'admin123', 'admin', '商城主管', '13800000000', '{{}}', 1, 0, 1),
('subadmin', 'sub123', 'admin', '订单管理员', '13800000001', '{{}}', 0, 1, 1),
('user', 'user123', 'user', '买家甲', '13800000002',
 '{{"realName":"王先生","email":"wang@demo.com","gender":"男","deliveryType":"配送到家","receiverName":"王先生","receiveAddress":"示例小区 3 栋 1201"}}',
 0, 1, 1)
ON DUPLICATE KEY UPDATE nickname=VALUES(nickname), phone=VALUES(phone), profile_json=VALUES(profile_json);

INSERT IGNORE INTO category (id, name) VALUES (1, '热销'), (2, '日用'), (3, '配件');
INSERT IGNORE INTO product (id, title, author, isbn, category_id, stock, status) VALUES
(1, '热销爆款套装', '99.00', 'RT-HOT01', 1, 40, 'available'),
(2, '日用收纳盒', '29.90', 'RT-DAY02', 2, 80, 'available'),
(3, '通用配件包', '19.90', 'RT-ACC03', 3, 60, 'available'),
(4, '家用小工具', '39.00', 'RT-DAY04', 2, 45, 'available');

INSERT IGNORE INTO user_address (id, username, contact_name, phone, address_line, tag, is_default) VALUES
(1, 'user', '王先生', '13800000002', '示例小区 3 栋 1201', '家', 1),
(2, 'user', '王先生', '13800000002', '科技园 A 座前台', '公司', 0),
(3, 'user', '王先生', '13800000002', '快递柜自提', '自提', 0);

INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '商城开业', '欢迎下单；支付完成后可在订单页查看进度。', 'admin', '商城主管'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='商城开业');
{_shop_workbench_orders_sql([
    (1, 1, "热销爆款套装", 99.00, "pending", "工作日送达。"),
    (2, 2, "日用收纳盒", 29.90, "shipped", "收纳盒已发出。"),
    (3, 3, "通用配件包", 19.90, "completed", "配件已签收。"),
    (4, 4, "家用小工具", 39.00, "confirmed", "请确认后发货。"),
])}"""

def _shop_retail_seed_for(catalog_kind: str) -> str:
    """retail 或 retail_* 软皮种子；壳仍走零售交易路径。"""
    if catalog_kind == "retail" or not catalog_kind.startswith("retail_"):
        return _SHOP_RETAIL
    from app.bake.shop_retail_niches import get_retail_niche

    pack = get_retail_niche(catalog_kind.removeprefix("retail_"))
    if pack is None:
        return _SHOP_RETAIL
    a, b, c = pack.categories
    admin_name, sub_name = pack.admin_name, pack.sub_name
    notice_title, notice_body = pack.notice_title, pack.notice_body
    # 单店种子须知用稍短句，避免与 schema 定制长文重复
    if pack.gift_line_custom:
        notice_body = "下单请填写刻字或上传图片；制作完成后再发货。"
    elif pack.id == "fitness":
        notice_body = "器械与护具按训练目标上架；下单后可在订单页查看进度。"
    else:
        notice_body = "欢迎选购；下单后可在订单页查看进度。"
        notice_title = "商城开业"
    cat_sql = f"(1, '{a}'), (2, '{b}'), (3, '{c}')"
    prod_lines = ",\n".join(
        f"({i}, '{title}', '{price}', '{sku}', {cid}, {50 + i * 5}, 'available')"
        for i, (title, price, sku, cid, _note) in enumerate(pack.skus, start=1)
    )
    skus = pack.skus
    # 至少 4 态订单；SKU 不足则循环取
    statuses = ("pending", "shipped", "completed", "confirmed")
    demo_specs: list[tuple[int, int, str, float | str, str, str]] = []
    for i, st in enumerate(statuses, start=1):
        title, price, _sku, _cid, _n = skus[(i - 1) % len(skus)]
        iid = ((i - 1) % len(skus)) + 1
        if pack.gift_line_custom and i == 1:
            remark = "刻字：张三；宋体 / 红色 / 大号"
        elif st == "pending":
            remark = "请确认后发货。"
        elif st == "shipped":
            remark = f"{title[:8]}已发出。"
        elif st == "completed":
            remark = "已签收。"
        else:
            remark = "商家已接单。"
        demo_specs.append((i, iid, title, price, st, remark))
    if pack.gift_line_custom:
        # 首单保留定制列；同 INSERT 其余行定制列置空
        first_title, first_price, _s, _c, _n = skus[0]
        ft = first_title.replace("'", "''")
        order_only = _shop_workbench_orders_sql(demo_specs).split(
            "INSERT IGNORE INTO order_line", 1
        )[0]
        line_rows = [
            f"(1, 1, 1, '{ft}', {first_price}, 1, '张三', '宋体 / 红色 / 大号')"
        ]
        for oid, iid, title, price, _st, _rm in demo_specs[1:]:
            ts = str(title).replace("'", "''")
            line_rows.append(
                f"({oid}, {oid}, {iid}, '{ts}', {price}, 1, '', '')"
            )
        orders_sql = (
            order_only
            + "INSERT IGNORE INTO order_line "
            "(id, order_id, item_id, title, price_yuan, qty, custom_text, spec_choice) VALUES\n"
            + ",\n".join(line_rows)
            + ";\n"
        )
    else:
        orders_sql = _shop_workbench_orders_sql(demo_specs)
    return f"""\
INSERT INTO sys_user (username, password, role, nickname, phone, profile_json, super_admin, profile_editable, enabled) VALUES
('admin', 'admin123', 'admin', '{admin_name}', '13800000000', '{{}}', 1, 0, 1),
('subadmin', 'sub123', 'admin', '{sub_name}', '13800000001', '{{}}', 0, 1, 1),
('user', 'user123', 'user', '买家甲', '13800000002',
 '{{"realName":"王先生","email":"wang@demo.com","gender":"男","deliveryType":"配送到家","receiverName":"王先生","receiveAddress":"示例小区 3 栋 1201"}}',
 0, 1, 1)
ON DUPLICATE KEY UPDATE nickname=VALUES(nickname), phone=VALUES(phone), profile_json=VALUES(profile_json);

INSERT IGNORE INTO category (id, name) VALUES {cat_sql};
INSERT IGNORE INTO product (id, title, author, isbn, category_id, stock, status) VALUES
{prod_lines};

INSERT IGNORE INTO user_address (id, username, contact_name, phone, address_line, tag, is_default) VALUES
(1, 'user', '王先生', '13800000002', '示例小区 3 栋 1201', '家', 1),
(2, 'user', '王先生', '13800000002', '科技园 A 座前台', '公司', 0),
(3, 'user', '王先生', '13800000002', '门店自提', '自提', 0);

INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '{notice_title}', '{notice_body}', 'admin', '{admin_name}'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='{notice_title}');
{orders_sql}"""


def _shop_mp_retail_seed_for(catalog_kind: str) -> str:
    """多店零售软皮：由登记表 pack 渲染；无 pack 时回落通用百货多店。"""
    from app.bake.shop_retail_niches import get_retail_niche

    if catalog_kind == "retail" or not catalog_kind.startswith("retail_"):
        return _SHOP_MP_RETAIL
    pack = get_retail_niche(catalog_kind.removeprefix("retail_"))
    if pack is None:
        return _SHOP_MP_RETAIL
    a, b, c = pack.categories
    shop_a, shop_b = pack.mp_shops
    cat_sql = f"(1, '{a}'), (2, '{b}'), (3, '{c}')"
    prod_rows: list[str] = []
    for i, (title, price, sku, cid, note) in enumerate(pack.skus, start=1):
        owner = "subadmin" if cid == 1 else "merchant_b"
        stock = 40 if i < len(pack.skus) else 8
        note_s = (note or title).replace("'", "''")
        prod_rows.append(
            f"({i}, '{title}', '{price}', '{sku}', {cid}, {stock}, 'available', "
            f"'{note_s}', '{owner}')"
        )
    prod_sql = ",\n".join(prod_rows)
    # 演示订单：取各店一件 + pending + shipped
    skus = pack.skus
    o1 = skus[0]
    o2 = next((s for s in skus if s[3] != 1), skus[min(1, len(skus) - 1)])
    o3 = next((s for s in skus if s is not o1 and s is not o2), skus[-1])
    o4 = next((s for s in skus if s[3] == 1 and s is not o1), o1)
    demo_specs = [
        (1, 1, o1[0], o1[1], "confirmed", f"{o1[0][:8]}请加固包装。"),
        (
            2,
            next(i for i, s in enumerate(skus, 1) if s is o2),
            o2[0],
            o2[1],
            "completed",
            "已签收。",
        ),
        (
            3,
            next(i for i, s in enumerate(skus, 1) if s is o3),
            o3[0],
            o3[1],
            "pending",
            "待付款。",
        ),
        (
            4,
            next(i for i, s in enumerate(skus, 1) if s is o4),
            o4[0],
            o4[1],
            "shipped",
            "已发出。",
        ),
    ]
    orders_sql = _shop_workbench_orders_sql(demo_specs)
    promo_title = pack.mp_promo_title.replace("'", "''")
    promo_body = pack.mp_promo_body.replace("'", "''")
    notice_t = pack.mp_notice_title.replace("'", "''")
    notice_b = pack.mp_notice_body.replace("'", "''")
    gb_q = (o1[0][:6] if o1[0] else "商品").replace("'", "''")
    return f"""\
INSERT INTO sys_user (username, password, role, nickname, phone, profile_json, super_admin, profile_editable, enabled) VALUES
('admin', 'admin123', 'admin', '平台管理员', '13800000000', '{{}}', 1, 0, 1),
('subadmin', 'sub123', 'admin', '{shop_a.name}', '13800000001',
 '{{"shopName":"{shop_a.name}","shopIntro":"{shop_a.intro}","shopPhone":"13800000001"}}',
 0, 1, 1),
('merchant_b', 'mer123', 'admin', '{shop_b.name}', '13800000012',
 '{{"shopName":"{shop_b.name}","shopIntro":"{shop_b.intro}","shopPhone":"13800000012"}}',
 0, 1, 1),
('user', 'user123', 'user', '买家甲', '13800000002',
 '{{"realName":"王先生","email":"wang@demo.com","gender":"男","deliveryType":"配送到家","receiverName":"王先生","receiveAddress":"示例小区 3 栋 1201"}}',
 0, 1, 1)
ON DUPLICATE KEY UPDATE nickname=VALUES(nickname), phone=VALUES(phone), profile_json=VALUES(profile_json),
 enabled=VALUES(enabled);

UPDATE sys_user SET staff_post='shop_merchant', staff_kind='clerk', role='admin', super_admin=0
WHERE username IN ('subadmin', 'merchant_b');

INSERT IGNORE INTO category (id, name) VALUES {cat_sql};
INSERT IGNORE INTO product (id, title, author, isbn, category_id, stock, status, seller_note, owner_username) VALUES
{prod_sql};

INSERT IGNORE INTO user_address (id, username, contact_name, phone, address_line, tag, is_default) VALUES
(1, 'user', '王先生', '13800000002', '示例小区 3 栋 1201', '家', 1),
(2, 'user', '王先生', '13800000002', '科技园 A 座前台', '公司', 0),
(3, 'user', '王先生', '13800000002', '门店自提', '自提', 0);

INSERT INTO sys_notice (title, content, publisher_username, publisher_name, audit_status, submitter_username)
SELECT '{notice_t}', '{notice_b}', 'admin', '平台管理员', 'approved', ''
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='{notice_t}' OR title='商城开业');
INSERT INTO sys_notice (title, content, publisher_username, publisher_name, audit_status, submitter_username)
SELECT '{promo_title}', '{promo_body}', 'subadmin', '{shop_a.name}', 'pending', 'subadmin'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='{promo_title}');
{orders_sql}
INSERT IGNORE INTO order_review (id, order_id, username, rating, body, created_at) VALUES
(1, 2, 'user', 5, '质量不错，物流及时。', NOW());

INSERT INTO sys_guestbook (username, nickname, body, channel)
SELECT 'user', '买家甲', '请问{gb_q}能否货到付款？', 'user'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_guestbook WHERE username='user' AND body LIKE '请问{gb_q}%');
INSERT INTO sys_guestbook (username, nickname, body, channel)
SELECT 'subadmin', '{shop_a.name}', '申请上架{promo_title}活动，请平台审核。', 'merchant'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_guestbook WHERE username='subadmin' AND body LIKE '申请上架{promo_title}%');
"""


_SHOP_FARM = """\
INSERT INTO sys_user (username, password, role, nickname, phone, profile_json, super_admin, profile_editable, enabled) VALUES
('admin', 'admin123', 'admin', '农产主管', '13800000000', '{}', 1, 0, 1),
('subadmin', 'sub123', 'admin', '烟台果园店', '13800000001',
 '{"shopName":"烟台果园店","shopIntro":"胶东鲜果与时蔬","shopPhone":"13800000001"}', 0, 1, 1),
('user', 'user123', 'user', '买家甲', '13800000002',
 '{"realName":"王先生","email":"wang@demo.com","gender":"男","deliveryType":"配送到家","receiverName":"王先生","receiveAddress":"示例小区 3 栋 1201"}',
 0, 1, 1)
ON DUPLICATE KEY UPDATE nickname=VALUES(nickname), phone=VALUES(phone), profile_json=VALUES(profile_json);

INSERT IGNORE INTO category (id, name) VALUES (1, '水果'), (2, '蔬菜'), (3, '粮油');
-- 封面空着：由 ensure_demo_cover_urls_sql 补 /uploads/demo/cover-NN.jpg（禁 twemoji）
INSERT IGNORE INTO product (id, title, author, isbn, category_id, stock, status, seller_note, region, harvest_on, owner_username) VALUES
(1, '红富士苹果', '39.90', '5 斤装', 1, 50, 'available', '脆甜多汁，适合鲜食与礼盒。', '山东烟台', DATE_FORMAT(DATE_SUB(CURDATE(), INTERVAL 2 DAY), '%Y-%m-%d'), 'subadmin'),
(2, '应季草莓', '28.00', '盒装 500g', 1, 35, 'available', '当季鲜摘，建议冷藏保存。', '辽宁丹东', DATE_FORMAT(DATE_SUB(CURDATE(), INTERVAL 1 DAY), '%Y-%m-%d'), 'subadmin'),
(3, '有机生菜', '8.50', '约 300g/份', 2, 60, 'available', '叶嫩清香，适合沙拉与火锅。', '本地基地', DATE_FORMAT(DATE_SUB(CURDATE(), INTERVAL 0 DAY), '%Y-%m-%d'), 'subadmin'),
(4, '五常大米', '68.00', '5kg 真空袋', 3, 40, 'available', '东北五常产区，常温阴凉存放。', '黑龙江五常', DATE_FORMAT(DATE_SUB(CURDATE(), INTERVAL 6 DAY), '%Y-%m-%d'), 'subadmin'),
(5, '红富士苹果', '72.00', '10 斤装', 1, 30, 'available', '家庭装，同果园直供。', '山东烟台', DATE_FORMAT(DATE_SUB(CURDATE(), INTERVAL 2 DAY), '%Y-%m-%d'), 'subadmin'),
(6, '赣南脐橙', '32.00', '5 斤装', 1, 45, 'available', '皮薄多汁，现摘现发。', '江西赣州', DATE_FORMAT(DATE_SUB(CURDATE(), INTERVAL 3 DAY), '%Y-%m-%d'), 'subadmin'),
(7, '阳光玫瑰葡萄', '48.00', '盒装 1kg', 1, 28, 'available', '脆甜无籽，冷藏保存。', '云南建水', DATE_FORMAT(DATE_SUB(CURDATE(), INTERVAL 1 DAY), '%Y-%m-%d'), 'subadmin'),
(8, '有机土豆', '12.80', '2.5kg', 2, 70, 'available', '沙面适中，适合炖煮。', '内蒙古乌兰察布', DATE_FORMAT(DATE_SUB(CURDATE(), INTERVAL 4 DAY), '%Y-%m-%d'), 'subadmin'),
(9, '胡萝卜', '9.90', '1kg', 2, 55, 'available', '根粗色匀，煲汤凉拌均可。', '山东潍坊', DATE_FORMAT(DATE_SUB(CURDATE(), INTERVAL 2 DAY), '%Y-%m-%d'), 'subadmin'),
(10, '东北黄豆', '22.00', '2kg', 3, 48, 'available', '颗粒饱满，打豆浆或炖菜。', '黑龙江绥化', DATE_FORMAT(DATE_SUB(CURDATE(), INTERVAL 5 DAY), '%Y-%m-%d'), 'subadmin');

INSERT IGNORE INTO user_address (id, username, contact_name, phone, address_line, tag, is_default) VALUES
(1, 'user', '王先生', '13800000002', '示例小区 3 栋 1201', '家', 1),
(2, 'user', '王先生', '13800000002', '科技园 A 座前台', '公司', 0),
(3, 'user', '王先生', '13800000002', '门店自提', '自提', 0);

INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '农产选购', '水果、蔬菜、粮油分类上架；支持配送到家与到店自提。', 'admin', '农产主管'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='农产选购' OR title='商城开业');
INSERT IGNORE INTO biz_order (id, username, status, total_yuan, remark, receiver_name, receiver_phone, address_line, delivery_type, created_at, completed_at) VALUES
(1, 'user', 'pending', 39.90, '苹果请选中等果。', '王先生', '13800000002', '示例小区 3 栋 1201', '配送到家', DATE_SUB(NOW(), INTERVAL 1 DAY), NULL),
(2, 'user', 'shipped', 28.00, '草莓请冷藏发货。', '王先生', '13800000002', '示例小区 3 栋 1201', '配送到家', DATE_SUB(NOW(), INTERVAL 2 DAY), NULL),
(3, 'user', 'completed', 8.50, '生菜请当天送达。', '王先生', '13800000002', '示例小区 3 栋 1201', '配送到家', DATE_SUB(NOW(), INTERVAL 3 DAY), DATE_SUB(NOW(), INTERVAL 2 DAY)),
(4, 'user', 'completed', 68.00, '大米放门口即可。', '王先生', '13800000002', '示例小区 3 栋 1201', '配送到家', DATE_SUB(NOW(), INTERVAL 5 DAY), DATE_SUB(NOW(), INTERVAL 4 DAY)),
(5, 'user', 'confirmed', 34.00, '门店自提，今晚六点取。', '王先生', '13800000002', '门店自提', '到店自提', DATE_SUB(NOW(), INTERVAL 0 DAY), NULL),
(6, 'user', 'completed', 32.00, '脐橙请装礼盒袋。', '王先生', '13800000002', '示例小区 3 栋 1201', '配送到家', DATE_SUB(NOW(), INTERVAL 4 DAY), DATE_SUB(NOW(), INTERVAL 3 DAY)),
(7, 'user', 'shipped', 48.00, '葡萄请加冰袋。', '王先生', '13800000002', '示例小区 3 栋 1201', '配送到家', DATE_SUB(NOW(), INTERVAL 1 DAY), NULL),
(8, 'user', 'confirmed', 22.70, '土豆胡萝卜一起送。', '王先生', '13800000002', '科技园 A 座前台', '配送到家', DATE_SUB(NOW(), INTERVAL 0 DAY), NULL);
INSERT IGNORE INTO order_line (id, order_id, item_id, title, price_yuan, qty) VALUES
(1, 1, 1, '红富士苹果', 39.90, 1),
(2, 2, 2, '应季草莓', 28.00, 1),
(3, 3, 3, '有机生菜', 8.50, 1),
(4, 4, 4, '五常大米', 68.00, 1),
(5, 5, 3, '有机生菜', 8.50, 4),
(6, 6, 6, '赣南脐橙', 32.00, 1),
(7, 7, 7, '阳光玫瑰葡萄', 48.00, 1),
(8, 8, 8, '有机土豆', 12.80, 1),
(9, 8, 9, '胡萝卜', 9.90, 1);
"""

_SHOP_PRINT = f"""\
INSERT INTO sys_user (username, password, role, nickname, phone, profile_json, super_admin, profile_editable, enabled) VALUES
('admin', 'admin123', 'admin', '文印店长', '13800000000', '{{}}', 1, 0, 1),
('subadmin', 'sub123', 'admin', '店员', '13800000001', '{{}}', 0, 1, 1),
('user', 'user123', 'user', '顾客甲', '13800000002',
 '{{"realName":"王同学","email":"wang@demo.edu","gender":"男","deliveryType":"到店自取","receiverName":"王同学","receiveAddress":"文印店前台"}}',
 0, 1, 1)
ON DUPLICATE KEY UPDATE nickname=VALUES(nickname), phone=VALUES(phone), profile_json=VALUES(profile_json);

INSERT IGNORE INTO category (id, name) VALUES (1, '黑白打印'), (2, '彩印装订'), (3, '耗材');
INSERT IGNORE INTO product (id, title, author, isbn, category_id, stock, status) VALUES
(1, 'A4 黑白单面（50 页）', '5.00', 'PRT-BW50', 1, 99, 'available'),
(2, '毕业论文胶装', '25.00', 'PRT-BIND', 2, 39, 'available'),
(3, '彩打封面（10 张）', '12.00', 'PRT-CV10', 2, 60, 'available'),
(4, 'A4 复印纸（500 张）', '28.00', 'PRT-PAPER', 3, 20, 'available');

INSERT IGNORE INTO user_address (id, username, contact_name, phone, address_line, tag, is_default) VALUES
(1, 'user', '王同学', '13800000002', '文印店前台自取', '自取', 1),
(2, 'user', '王同学', '13800000002', '教学楼 A 座门口', '配送', 0),
(3, 'user', '王同学', '13800000002', '宿舍 3 号楼宿管台', '宿舍', 0);

INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '文印须知', '下单后到店取件或约定配送。', 'admin', '文印店长'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='文印须知' OR title='商城开业');
{_shop_workbench_orders_sql(
    [
        (1, 2, "毕业论文胶装", 25.00, "pending", "胶装蓝色封面，今晚取。"),
        (2, 1, "A4 黑白单面（50 页）", 5.00, "shipped", "黑白件已出，可来取。"),
        (3, 3, "彩打封面（10 张）", 12.00, "completed", "彩打封面已取走。"),
        (4, 4, "A4 复印纸（500 张）", 28.00, "confirmed", "复印纸已备好。"),
    ],
    contact="王同学",
    address="文印店前台自取",
    delivery="到店自取",
)}"""

_SHOP_FLOWERS = f"""\
INSERT INTO sys_user (username, password, role, nickname, phone, profile_json, super_admin, profile_editable, enabled) VALUES
('admin', 'admin123', 'admin', '花店主管', '13800000000', '{{}}', 1, 0, 1),
('subadmin', 'sub123', 'admin', '店员', '13800000001', '{{}}', 0, 1, 1),
('user', 'user123', 'user', '买家甲', '13800000002',
 '{{"realName":"王先生","email":"wang@demo.com","gender":"男","deliveryType":"配送到家","receiverName":"王先生","receiveAddress":"示例小区 3 栋 1201"}}',
 0, 1, 1)
ON DUPLICATE KEY UPDATE nickname=VALUES(nickname), phone=VALUES(phone), profile_json=VALUES(profile_json);

INSERT IGNORE INTO category (id, name) VALUES (1, '鲜切花'), (2, '盆花绿植'), (3, '地方特产');
INSERT IGNORE INTO product (id, title, author, isbn, category_id, stock, status) VALUES
(1, '康乃馨花束（11 枝）', '68.00', 'FL-CN11', 1, 19, 'available'),
(2, '向日葵桌花', '88.00', 'FL-SF01', 1, 15, 'available'),
(3, '绿萝盆栽', '39.00', 'FL-LV01', 2, 30, 'available'),
(4, '本地蜂蜜礼盒', '58.00', 'SP-HN01', 3, 25, 'available');

INSERT IGNORE INTO user_address (id, username, contact_name, phone, address_line, tag, is_default) VALUES
(1, 'user', '王先生', '13800000002', '示例小区 3 栋 1201', '家', 1),
(2, 'user', '王先生', '13800000002', '科技园 A 座前台', '公司', 0),
(3, 'user', '王先生', '13800000002', '花店门店自提', '自提', 0);

INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '花店须知', '鲜花与特产下单后由店员确认配送。', 'admin', '花店主管'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='花店须知' OR title='商城开业');
{_shop_workbench_orders_sql([
    (1, 1, "康乃馨花束（11 枝）", 68.00, "pending", "周六上午送达。"),
    (2, 2, "向日葵桌花", 88.00, "shipped", "向日葵已发出。"),
    (3, 3, "绿萝盆栽", 39.00, "completed", "绿萝已签收。"),
    (4, 4, "本地蜂蜜礼盒", 58.00, "confirmed", "蜂蜜礼盒备货中。"),
])}"""

_SHOP_ERRAND = f"""\
INSERT INTO sys_user (username, password, role, nickname, phone, profile_json, super_admin, profile_editable, enabled) VALUES
('admin', 'admin123', 'admin', '跑腿调度', '13800000000', '{{}}', 1, 0, 1),
('subadmin', 'sub123', 'admin', '跑腿员', '13800000001', '{{}}', 0, 1, 1),
('user', 'user123', 'user', '下单同学', '13800000002',
 '{{"realName":"王同学","email":"wang@demo.edu","gender":"男","deliveryType":"宿舍配送","receiverName":"王同学","receiveAddress":"学生公寓 3 号楼 405"}}',
 0, 1, 1)
ON DUPLICATE KEY UPDATE nickname=VALUES(nickname), phone=VALUES(phone), profile_json=VALUES(profile_json);

INSERT IGNORE INTO category (id, name) VALUES (1, '代买餐饮'), (2, '代买日用'), (3, '代取快递');
INSERT IGNORE INTO product (id, title, author, isbn, category_id, stock, status) VALUES
(1, '食堂代买套餐（含跑腿费）', '22.00', 'ER-MEAL', 1, 49, 'available'),
(2, '超市代买日用品', '15.00', 'ER-DAILY', 2, 40, 'available'),
(3, '东门驿站代取件', '8.00', 'ER-PICK', 3, 80, 'available'),
(4, '打印店代取资料', '6.00', 'ER-PRINT', 3, 60, 'available');

INSERT IGNORE INTO user_address (id, username, contact_name, phone, address_line, tag, is_default) VALUES
(1, 'user', '王同学', '13800000002', '学生公寓 3 号楼 405', '宿舍', 1),
(2, 'user', '王同学', '13800000002', '教学楼 A 座门口', '教学楼', 0),
(3, 'user', '王同学', '13800000002', '图书馆南门', '图书馆', 0);

INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '跑腿须知', '代买代取下单后由跑腿员接单送达；请填写送达地点与联系方式。', 'admin', '跑腿调度'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='跑腿须知' OR title='商城开业');
{_shop_workbench_orders_sql(
    [
        (1, 1, "食堂代买套餐（含跑腿费）", 22.00, "pending", "红烧肉套餐，少辣，送到 405。"),
        (2, 2, "超市代买日用品", 15.00, "shipped", "日用品配送中。"),
        (3, 3, "东门驿站代取件", 8.00, "completed", "快递已送到宿舍。"),
        (4, 4, "打印店代取资料", 6.00, "confirmed", "打印店资料已接单。"),
    ],
    contact="王同学",
    address="学生公寓 3 号楼 405",
    delivery="宿舍配送",
)}"""

_SHOP_POINTS = f"""\
INSERT INTO sys_user (username, password, role, nickname, phone, profile_json, super_admin, profile_editable, enabled) VALUES
('admin', 'admin123', 'admin', '积分商城主管', '13800000000', '{{}}', 1, 0, 1),
('subadmin', 'sub123', 'admin', '订单管理员', '13800000001', '{{}}', 0, 1, 1),
('user', 'user123', 'user', '会员甲', '13800000002',
 '{{"realName":"王同学","email":"wang@demo.edu","gender":"男","deliveryType":"到店自提","receiverName":"王同学","receiveAddress":"学生活动中心"}}',
 0, 1, 1)
ON DUPLICATE KEY UPDATE nickname=VALUES(nickname), phone=VALUES(phone), profile_json=VALUES(profile_json);

INSERT IGNORE INTO category (id, name) VALUES (1, '文创兑换'), (2, '生活兑换'), (3, '虚拟权益');
INSERT IGNORE INTO product (id, title, author, isbn, category_id, stock, status) VALUES
(1, '校徽帆布袋（500 积分）', '0.00', 'PT-BAG', 1, 39, 'available'),
(2, '保温杯（800 积分）', '0.00', 'PT-CUP', 2, 20, 'available'),
(3, '打印券 20 页（200 积分）', '0.00', 'PT-PRT', 3, 100, 'available'),
(4, '体育馆次卡（1200 积分）', '0.00', 'PT-GYM', 3, 30, 'available');

INSERT IGNORE INTO user_address (id, username, contact_name, phone, address_line, tag, is_default) VALUES
(1, 'user', '王同学', '13800000002', '学生活动中心兑换点', '自提', 1),
(2, 'user', '王同学', '13800000002', '学生公寓 3 号楼宿管台', '宿舍', 0),
(3, 'user', '王同学', '13800000002', '东门驿站', '驿站', 0);

INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '积分兑换须知', '兑换下单后由管理员确认发放；积分扣减以系统账户为准。', 'admin', '积分商城主管'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='积分兑换须知' OR title='商城开业');
{_shop_workbench_orders_sql(
    [
        (1, 1, "校徽帆布袋（500 积分）", 0.00, "pending", "兑换帆布袋，活动中心自提。"),
        (2, 2, "保温杯（800 积分）", 0.00, "shipped", "保温杯待发放。"),
        (3, 3, "打印券 20 页（200 积分）", 0.00, "completed", "打印券已发放。"),
        (4, 4, "体育馆次卡（1200 积分）", 0.00, "confirmed", "次卡兑换已确认。"),
    ],
    contact="王同学",
    address="学生活动中心兑换点",
    delivery="到店自提",
)}"""

# 校园二手：成色列由 apply 注入；种子含校内二手货
_SHOP_CAMPUS = f"""\
INSERT INTO sys_user (username, password, role, nickname, phone, profile_json, super_admin, profile_editable, enabled) VALUES
('admin', 'admin123', 'admin', '商城主管', '13800000000', '{{}}', 1, 0, 1),
('subadmin', 'sub123', 'admin', '订单管理员', '13800000001', '{{}}', 0, 1, 1),
('user', 'user123', 'user', '买家甲', '13800000002',
 '{{"realName":"王同学","email":"wang@demo.edu","gender":"男","deliveryType":"到店自提","receiverName":"王同学","receiveAddress":"学生公寓 3 号楼","pickupPoint":"东门驿站"}}',
 0, 1, 1)
ON DUPLICATE KEY UPDATE nickname=VALUES(nickname), phone=VALUES(phone), profile_json=VALUES(profile_json);

INSERT IGNORE INTO category (id, name) VALUES (1, '教材教辅'), (2, '数码'), (3, '日用文创');
INSERT IGNORE INTO product (id, title, author, isbn, category_id, stock, status, condition_grade, seller_note) VALUES
(1, '高等数学上下册', '35.00', 'BOOK-MATH', 1, 9, 'available', '九成新', '宿舍自提'),
(2, '机械键盘', '199.00', 'KB-01', 2, 20, 'available', '九成新', '宿舍自提'),
(3, '桌面台灯', '59.90', 'LAMP-02', 3, 35, 'available', '全新', '未拆封'),
(4, '无线鼠标', '89.00', 'MS-04', 2, 15, 'available', '八成新', '轻微使用痕迹');

INSERT IGNORE INTO user_address (id, username, contact_name, phone, address_line, tag, is_default) VALUES
(1, 'user', '王同学', '13800000002', '学生公寓 3 号楼 405', '宿舍', 1),
(2, 'user', '王同学', '13800000002', '教学楼 A 座前台', '自提', 0),
(3, 'user', '王同学', '13800000002', '东门驿站', '驿站', 0);

INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '校园商城', '校内闲置流转；请如实填写成色与自提点。', 'admin', '商城主管'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='校园商城' OR title='商城开业');
{_shop_workbench_orders_sql(
    [
        (1, 1, "高等数学上下册", 35.00, "pending", "教材两本，宿舍自提。"),
        (2, 2, "机械键盘", 199.00, "shipped", "键盘已备好，可来取。"),
        (3, 3, "桌面台灯", 59.90, "completed", "台灯已取走。"),
        (4, 4, "无线鼠标", 89.00, "confirmed", "鼠标已确认，待自提。"),
    ],
    contact="王同学",
    address="学生公寓 3 号楼 405",
    delivery="到店自提",
)}"""


def _shop_sql_condition_grade(sql: str, *, campus: bool) -> str:
    """零售包不得残留成色列；校园二手才注入 condition_grade。"""
    # 先剥掉（模板误留或旧片段）
    sql = re.sub(
        r"\n\s*condition_grade\s+VARCHAR\([^)]+\)[^,\n]*,?",
        "",
        sql,
        flags=re.I,
    )
    if not campus:
        return sql
    if re.search(r"\bcondition_grade\b", sql, re.I):
        return sql
    return re.sub(
        r"(CREATE TABLE IF NOT EXISTS\s+product\s*\([^;]*?)(\n\s*created_at\b)",
        r"\1\n  condition_grade VARCHAR(16) DEFAULT '全新',\2",
        sql,
        count=1,
        flags=re.I | re.S,
    )


def _shop_sql_farm_attrs(sql: str, *, farm: bool) -> str:
    """仅农产皮注入产地/采摘时间；其它商城皮剥掉，避免串列。"""
    sql = re.sub(
        r"\n\s*region\s+VARCHAR\([^)]+\)[^,\n]*,?",
        "",
        sql,
        flags=re.I,
    )
    sql = re.sub(
        r"\n\s*harvest_on\s+VARCHAR\([^)]+\)[^,\n]*,?",
        "",
        sql,
        flags=re.I,
    )
    if not farm:
        return sql
    if not re.search(r"\bregion\b", sql, re.I):
        sql = re.sub(
            r"(CREATE TABLE IF NOT EXISTS\s+product\s*\([^;]*?)(\n\s*created_at\b)",
            r"\1\n  region VARCHAR(64) DEFAULT '',\2",
            sql,
            count=1,
            flags=re.I | re.S,
        )
    if not re.search(r"\bharvest_on\b", sql, re.I):
        sql = re.sub(
            r"(CREATE TABLE IF NOT EXISTS\s+product\s*\([^;]*?)(\n\s*created_at\b)",
            r"\1\n  harvest_on VARCHAR(32) DEFAULT '',\2",
            sql,
            count=1,
            flags=re.I | re.S,
        )
    return sql


def _shop_sql_marketplace(sql: str, *, farm: bool = False) -> str:
    """多店 DDL：公告待审列。owner_username 由 ensure_archive_flag_columns 注入。

    默认单店模板不得残留这些列；仅 marketplace 开题才补。
    """
    _ = farm  # 农产列仍由 _shop_sql_farm_attrs 负责
    sql = re.sub(
        r"\n\s*audit_status\s+VARCHAR\([^)]+\)[^,\n]*,?",
        "",
        sql,
        flags=re.I,
    )
    sql = re.sub(
        r"\n\s*submitter_username\s+VARCHAR\([^)]+\)[^,\n]*,?",
        "",
        sql,
        flags=re.I,
    )
    if not re.search(
        r"CREATE TABLE IF NOT EXISTS\s+sys_notice\s*\([^;]*\baudit_status\b",
        sql,
        re.I | re.S,
    ):
        sql = re.sub(
            r"(CREATE TABLE IF NOT EXISTS\s+sys_notice\s*\([^;]*?)(\n\s*created_at\b)",
            r"\1\n  audit_status VARCHAR(32) DEFAULT 'approved',\n"
            r"  submitter_username VARCHAR(64) DEFAULT '',\2",
            sql,
            count=1,
            flags=re.I | re.S,
        )
    # 多店留言表须在种子 INSERT 之前建好（ensure_guestbook 在更后才追加 DDL）
    _gb_ddl = """
CREATE TABLE IF NOT EXISTS sys_guestbook (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  username VARCHAR(64) NOT NULL,
  nickname VARCHAR(64) DEFAULT '',
  body VARCHAR(500) NOT NULL,
  reply VARCHAR(500) DEFAULT '',
  reply_username VARCHAR(64) DEFAULT '',
  replied_at DATETIME NULL,
  channel VARCHAR(16) DEFAULT 'user',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  KEY idx_gb_created (id),
  KEY idx_gb_user (username)
);
"""
    if not re.search(
        r"CREATE TABLE IF NOT EXISTS\s+sys_guestbook\s*\(",
        sql,
        re.I,
    ):
        m = re.search(r"INSERT INTO sys_user\b", sql, re.I)
        if m:
            sql = sql[: m.start()] + _gb_ddl.strip() + "\n\n" + sql[m.start() :]
        else:
            sql = sql.rstrip() + "\n" + _gb_ddl
    elif not re.search(
        r"CREATE TABLE IF NOT EXISTS\s+sys_guestbook\s*\([^;]*\bchannel\b",
        sql,
        re.I | re.S,
    ):
        sql = re.sub(
            r"(CREATE TABLE IF NOT EXISTS\s+sys_guestbook\s*\([^;]*?)(\n\s*created_at\b)",
            r"\1\n  channel VARCHAR(16) DEFAULT 'user',\2",
            sql,
            count=1,
            flags=re.I | re.S,
        )
    return sql


# 多店种子：平台超管 + subadmin(店长甲，岗位由 append_staff 绑定) + merchant_b + 买家
_SHOP_MP_FARM = """\
INSERT INTO sys_user (username, password, role, nickname, phone, profile_json, super_admin, profile_editable, enabled) VALUES
('admin', 'admin123', 'admin', '平台管理员', '13800000000', '{}', 1, 0, 1),
('subadmin', 'sub123', 'admin', '烟台果园店', '13800000001',
 '{"shopName":"烟台果园店","shopIntro":"胶东鲜果直供","shopPhone":"13800000001"}',
 0, 1, 1),
('merchant_b', 'mer123', 'admin', '丹东莓园店', '13800000012',
 '{"shopName":"丹东莓园店","shopIntro":"应季浆果","shopPhone":"13800000012"}',
 0, 1, 1),
('user', 'user123', 'user', '买家甲', '13800000002',
 '{"realName":"王先生","email":"wang@demo.com","gender":"男","deliveryType":"配送到家","receiverName":"王先生","receiveAddress":"示例小区 3 栋 1201"}',
 0, 1, 1)
ON DUPLICATE KEY UPDATE nickname=VALUES(nickname), phone=VALUES(phone), profile_json=VALUES(profile_json),
 enabled=VALUES(enabled);

UPDATE sys_user SET staff_post='shop_merchant', staff_kind='clerk', role='admin', super_admin=0
WHERE username IN ('subadmin', 'merchant_b');

INSERT IGNORE INTO category (id, name) VALUES (1, '水果'), (2, '蔬菜'), (3, '粮油');
-- 封面空着：由 ensure_demo_cover_urls_sql 补 /uploads/demo/cover-NN.jpg（禁 twemoji）
INSERT IGNORE INTO product (id, title, author, isbn, category_id, stock, status, seller_note, region, harvest_on, owner_username) VALUES
(1, '红富士苹果', '39.90', '5 斤装', 1, 50, 'available', '脆甜多汁，适合鲜食与礼盒。', '山东烟台', DATE_FORMAT(DATE_SUB(CURDATE(), INTERVAL 2 DAY), '%Y-%m-%d'), 'subadmin'),
(2, '应季草莓', '28.00', '盒装 500g', 1, 35, 'available', '当季鲜摘，建议冷藏保存。', '辽宁丹东', DATE_FORMAT(DATE_SUB(CURDATE(), INTERVAL 1 DAY), '%Y-%m-%d'), 'merchant_b'),
(3, '有机生菜', '8.50', '约 300g/份', 2, 60, 'available', '叶嫩清香，适合沙拉与火锅。', '本地基地', DATE_FORMAT(DATE_SUB(CURDATE(), INTERVAL 0 DAY), '%Y-%m-%d'), 'subadmin'),
(4, '五常大米', '68.00', '5kg 真空袋', 3, 40, 'available', '东北五常产区，常温阴凉存放。', '黑龙江五常', DATE_FORMAT(DATE_SUB(CURDATE(), INTERVAL 6 DAY), '%Y-%m-%d'), 'merchant_b'),
(5, '红富士苹果', '72.00', '10 斤装', 1, 30, 'available', '家庭装，同果园直供。', '山东烟台', DATE_FORMAT(DATE_SUB(CURDATE(), INTERVAL 2 DAY), '%Y-%m-%d'), 'subadmin'),
(6, '赣南脐橙', '32.00', '5 斤装', 1, 45, 'available', '皮薄多汁，现摘现发。', '江西赣州', DATE_FORMAT(DATE_SUB(CURDATE(), INTERVAL 3 DAY), '%Y-%m-%d'), 'subadmin'),
(7, '阳光玫瑰葡萄', '48.00', '盒装 1kg', 1, 28, 'available', '脆甜无籽，冷藏保存。', '云南建水', DATE_FORMAT(DATE_SUB(CURDATE(), INTERVAL 1 DAY), '%Y-%m-%d'), 'merchant_b'),
(8, '有机土豆', '12.80', '2.5kg', 2, 70, 'available', '沙面适中，适合炖煮。', '内蒙古乌兰察布', DATE_FORMAT(DATE_SUB(CURDATE(), INTERVAL 4 DAY), '%Y-%m-%d'), 'subadmin'),
(9, '胡萝卜', '9.90', '1kg', 2, 55, 'available', '根粗色匀，煲汤凉拌均可。', '山东潍坊', DATE_FORMAT(DATE_SUB(CURDATE(), INTERVAL 2 DAY), '%Y-%m-%d'), 'merchant_b'),
(10, '东北黄豆', '22.00', '2kg', 3, 48, 'available', '颗粒饱满，打豆浆或炖菜。', '黑龙江绥化', DATE_FORMAT(DATE_SUB(CURDATE(), INTERVAL 5 DAY), '%Y-%m-%d'), 'merchant_b');

INSERT IGNORE INTO user_address (id, username, contact_name, phone, address_line, tag, is_default) VALUES
(1, 'user', '王先生', '13800000002', '示例小区 3 栋 1201', '家', 1),
(2, 'user', '王先生', '13800000002', '科技园 A 座前台', '公司', 0),
(3, 'user', '王先生', '13800000002', '门店自提', '自提', 0);

INSERT INTO sys_notice (title, content, publisher_username, publisher_name, audit_status, submitter_username)
SELECT '农产选购', '多店直供；下单后可在订单页查看进度。', 'admin', '平台管理员', 'approved', ''
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='农产选购' OR title='商城开业');
INSERT INTO sys_notice (title, content, publisher_username, publisher_name, audit_status, submitter_username)
SELECT '金秋苹果促销', '烟台红富士满 2 件减 5 元（待平台审核）。', 'subadmin', '烟台果园店', 'pending', 'subadmin'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='金秋苹果促销');
INSERT IGNORE INTO biz_order (id, username, status, total_yuan, remark, receiver_name, receiver_phone, address_line, delivery_type, created_at, completed_at) VALUES
(1, 'user', 'confirmed', 39.90, '苹果请选中等果。', '王先生', '13800000002', '示例小区 3 栋 1201', '配送到家', DATE_SUB(NOW(), INTERVAL 1 DAY), NULL),
(2, 'user', 'completed', 28.00, '草莓请冷藏发货。', '王先生', '13800000002', '示例小区 3 栋 1201', '配送到家', DATE_SUB(NOW(), INTERVAL 3 DAY), DATE_SUB(NOW(), INTERVAL 2 DAY)),
(3, 'user', 'pending', 8.50, '待付款（可去付款）。', '王先生', '13800000002', '示例小区 3 栋 1201', '配送到家', DATE_SUB(NOW(), INTERVAL 0 DAY), NULL),
(4, 'user', 'shipped', 68.00, '大米已发出。', '王先生', '13800000002', '示例小区 3 栋 1201', '配送到家', DATE_SUB(NOW(), INTERVAL 2 DAY), NULL),
(5, 'user', 'completed', 32.00, '脐橙请装礼盒袋。', '王先生', '13800000002', '示例小区 3 栋 1201', '配送到家', DATE_SUB(NOW(), INTERVAL 5 DAY), DATE_SUB(NOW(), INTERVAL 4 DAY)),
(6, 'user', 'shipped', 48.00, '葡萄请加冰袋。', '王先生', '13800000002', '示例小区 3 栋 1201', '配送到家', DATE_SUB(NOW(), INTERVAL 1 DAY), NULL),
(7, 'user', 'confirmed', 22.70, '土豆胡萝卜一起送。', '王先生', '13800000002', '科技园 A 座前台', '配送到家', DATE_SUB(NOW(), INTERVAL 0 DAY), NULL),
(8, 'user', 'completed', 72.00, '家庭装苹果，放家门口。', '王先生', '13800000002', '示例小区 3 栋 1201', '配送到家', DATE_SUB(NOW(), INTERVAL 6 DAY), DATE_SUB(NOW(), INTERVAL 5 DAY));
INSERT IGNORE INTO order_line (id, order_id, item_id, title, price_yuan, qty) VALUES
(1, 1, 1, '红富士苹果', 39.90, 1),
(2, 2, 2, '应季草莓', 28.00, 1),
(3, 3, 3, '有机生菜', 8.50, 1),
(4, 4, 4, '五常大米', 68.00, 1),
(5, 5, 6, '赣南脐橙', 32.00, 1),
(6, 6, 7, '阳光玫瑰葡萄', 48.00, 1),
(7, 7, 8, '有机土豆', 12.80, 1),
(8, 7, 9, '胡萝卜', 9.90, 1),
(9, 8, 5, '红富士苹果', 72.00, 1);
INSERT IGNORE INTO order_review (id, order_id, username, rating, body, created_at) VALUES
(1, 2, 'user', 5, '草莓很新鲜，冷链到位。', DATE_SUB(NOW(), INTERVAL 2 DAY)),
(2, 5, 'user', 4, '脐橙甜度不错，包装严实。', DATE_SUB(NOW(), INTERVAL 4 DAY)),
(3, 8, 'user', 5, '十斤装分量足，果个均匀。', DATE_SUB(NOW(), INTERVAL 5 DAY));

INSERT INTO sys_guestbook (username, nickname, body, channel)
SELECT 'user', '买家甲', '请问草莓能否冷链配送？', 'user'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_guestbook WHERE username='user' AND body LIKE '请问草莓%');
INSERT INTO sys_guestbook (username, nickname, body, channel)
SELECT 'subadmin', '烟台果园店', '申请上架金秋促销活动，请平台审核。', 'merchant'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_guestbook WHERE username='subadmin' AND body LIKE '申请上架金秋%');
"""

_SHOP_MP_RETAIL = f"""\
INSERT INTO sys_user (username, password, role, nickname, phone, profile_json, super_admin, profile_editable, enabled) VALUES
('admin', 'admin123', 'admin', '平台管理员', '13800000000', '{{}}', 1, 0, 1),
('subadmin', 'sub123', 'admin', '日用优选店', '13800000001',
 '{{"shopName":"日用优选店","shopIntro":"百货日用","shopPhone":"13800000001"}}',
 0, 1, 1),
('merchant_b', 'mer123', 'admin', '数码配件店', '13800000012',
 '{{"shopName":"数码配件店","shopIntro":"手机周边","shopPhone":"13800000012"}}',
 0, 1, 1),
('user', 'user123', 'user', '买家甲', '13800000002',
 '{{"realName":"王先生","email":"wang@demo.com","gender":"男","deliveryType":"配送到家","receiverName":"王先生","receiveAddress":"示例小区 3 栋 1201"}}',
 0, 1, 1)
ON DUPLICATE KEY UPDATE nickname=VALUES(nickname), phone=VALUES(phone), profile_json=VALUES(profile_json),
 enabled=VALUES(enabled);

UPDATE sys_user SET staff_post='shop_merchant', staff_kind='clerk', role='admin', super_admin=0
WHERE username IN ('subadmin', 'merchant_b');

INSERT IGNORE INTO category (id, name) VALUES (1, '热销'), (2, '日用'), (3, '配件');
INSERT IGNORE INTO product (id, title, author, isbn, category_id, stock, status, seller_note, owner_username) VALUES
(1, '日用收纳盒', '29.90', 'SKU-A01', 2, 29, 'available', '多格收纳', 'subadmin'),
(2, '蓝牙耳机套装', '129.00', 'SKU-B02', 1, 40, 'available', '续航升级', 'merchant_b'),
(3, '保温杯 500ml', '59.00', 'SKU-C03', 2, 20, 'available', '锁温不锈钢', 'subadmin'),
(4, '手机支架', '19.90', 'SKU-D04', 3, 50, 'available', '桌面懒人支架', 'merchant_b');

INSERT IGNORE INTO user_address (id, username, contact_name, phone, address_line, tag, is_default) VALUES
(1, 'user', '王先生', '13800000002', '示例小区 3 栋 1201', '家', 1),
(2, 'user', '王先生', '13800000002', '科技园 A 座前台', '公司', 0),
(3, 'user', '王先生', '13800000002', '门店自提', '自提', 0);

INSERT INTO sys_notice (title, content, publisher_username, publisher_name, audit_status, submitter_username)
SELECT '商城开业', '多店入驻；下单后可在订单页查看进度。', 'admin', '平台管理员', 'approved', ''
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='商城开业');
{_shop_workbench_orders_sql([
    (1, 1, "日用收纳盒", 29.90, "confirmed", "请加固包装。"),
    (2, 3, "保温杯 500ml", 59.00, "shipped", "保温杯已发出。"),
    (3, 4, "手机支架", 19.90, "pending", "待付款。"),
    (4, 2, "蓝牙耳机套装", 129.00, "completed", "耳机已签收。"),
])}
INSERT INTO sys_guestbook (username, nickname, body, channel)
SELECT 'user', '买家甲', '收货地址能否修改？', 'user'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_guestbook WHERE username='user' AND body LIKE '收货地址%');
INSERT INTO sys_guestbook (username, nickname, body, channel)
SELECT 'subadmin', '日用优选店', '申请参加平台百货周活动。', 'merchant'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_guestbook WHERE username='subadmin' AND body LIKE '申请参加平台百货%');
"""

_HOTEL_BOARDING = """\
INSERT INTO sys_user (username, password, role, nickname, phone, profile_json, super_admin, profile_editable, enabled) VALUES
('admin', 'admin123', 'admin', '寄养主管', '13800000000', '{}', 1, 0, 1),
('subadmin', 'sub123', 'admin', '前台', '13800000001', '{}', 0, 1, 1),
('user', 'user123', 'user', '寄养人甲', '13800000002',
 '{"realName":"周女士","email":"zhou@demo.com","gender":"女"}',
 0, 1, 1)
ON DUPLICATE KEY UPDATE nickname=VALUES(nickname), phone=VALUES(phone), profile_json=VALUES(profile_json);

INSERT IGNORE INTO category (id, name) VALUES (1, '小型'), (2, '大型');
INSERT IGNORE INTO room_type (id, title, author, isbn, category_id, stock, status) VALUES
(1, '小单间', '80.00', '适合小型犬猫', 1, 1, 'available'),
(2, '大单间', '120.00', '适合中大型', 2, 2, 'available');
INSERT IGNORE INTO resource_slot (id, item_id, start_at, end_at, capacity, booked) VALUES
(1, 1, '2026-09-21 12:00:00', '2026-09-21 18:00:00', 1, 1),
(2, 1, '2026-09-22 12:00:00', '2026-09-22 18:00:00', 1, 1),
(3, 1, '2026-09-23 12:00:00', '2026-09-23 18:00:00', 1, 1),
(4, 1, '2026-09-24 12:00:00', '2026-09-24 18:00:00', 1, 0),
(5, 2, '2026-09-21 12:00:00', '2026-09-21 18:00:00', 2, 0),
(6, 2, '2026-09-22 12:00:00', '2026-09-22 18:00:00', 2, 0),
(7, 2, '2026-09-23 12:00:00', '2026-09-23 18:00:00', 2, 0),
(8, 2, '2026-09-24 12:00:00', '2026-09-24 18:00:00', 2, 0);
INSERT IGNORE INTO reservation (id, slot_id, username, status, remark, guest_name, guest_count, stay_from, stay_to, care_ids) VALUES
(1, 1, 'user', 'confirmed', '', '豆豆', 1, '2026-09-21', '2026-09-24', '1'),
(2, 5, 'user', 'pending', '', '球球', 1, '2026-09-22', '2026-09-23', ''),
(3, 4, 'user', 'completed', '', '豆豆', 1, '2026-09-10', '2026-09-12', '1');
INSERT IGNORE INTO biz_order (id, username, status, total_yuan, remark, reservation_id, created_at, completed_at) VALUES
(1, 'user', 'confirmed', 240.00, 'reservation:1', 1, DATE_SUB(NOW(), INTERVAL 1 DAY), NULL),
(2, 'user', 'pending', 120.00, 'reservation:2', 2, DATE_SUB(NOW(), INTERVAL 0 DAY), NULL),
(3, 'user', 'completed', 160.00, 'reservation:3', 3, DATE_SUB(NOW(), INTERVAL 5 DAY), DATE_SUB(NOW(), INTERVAL 4 DAY));
INSERT IGNORE INTO order_line (id, order_id, item_id, title, price_yuan, qty) VALUES
(1, 1, 1, '小单间', 80.00, 3),
(2, 2, 2, '大单间', 120.00, 1),
(3, 3, 1, '小单间', 80.00, 2);
INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '寄养预约', '选择寄养位和日期。金额按天数计算。', 'admin', '寄养主管'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='寄养预约' OR title='客房预订');
"""


# 影院多主办方（影院皮）：平台超管 + 两影城 + 观影者
_CINEMA_MP = """\
INSERT INTO sys_user (username, password, role, nickname, phone, profile_json, super_admin, profile_editable, enabled) VALUES
('admin', 'admin123', 'admin', '平台管理员', '13800000000', '{}', 1, 0, 1),
('subadmin', 'sub123', 'admin', '潮汐影城', '13800000001',
 '{"shopName":"潮汐影城","shopIntro":"校园排片与特效厅","shopPhone":"13800000001"}',
 0, 1, 1),
('merchant_b', 'mer123', 'admin', '星海影城', '13800000012',
 '{"shopName":"星海影城","shopIntro":"巨幕周末场","shopPhone":"13800000012"}',
 0, 1, 1),
('user', 'user123', 'user', '观影者甲', '13800000002',
 '{"realName":"周观影","email":"zhou@demo.com","gender":"男","memberNo":"M20230015","orgName":"艺术学院"}',
 0, 1, 1)
ON DUPLICATE KEY UPDATE nickname=VALUES(nickname), phone=VALUES(phone), profile_json=VALUES(profile_json),
 enabled=VALUES(enabled);

UPDATE sys_user SET staff_post='shop_merchant', staff_kind='clerk', role='admin', super_admin=0
WHERE username IN ('subadmin', 'merchant_b');

INSERT IGNORE INTO category (id, name) VALUES (1, '普通厅'), (2, '巨幕厅'), (3, 'IMAX'), (4, '杜比');
INSERT IGNORE INTO cinema_show (id, title, author, isbn, category_id, stock, status, seat_rows, seat_cols, start_at, owner_username) VALUES
(1, '春日校园·晚场', '35', '1号厅', 1, 48, 'available', 6, 8, '2026-08-08 19:30:00', 'subadmin'),
(2, '科幻巨幕·周末场', '45', '巨幕1厅', 2, 50, 'available', 5, 10, '2026-08-09 14:00:00', 'merchant_b'),
(3, '学生特惠午场', '25', '2号厅', 3, 32, 'available', 4, 8, '2026-08-08 11:00:00', 'subadmin');

INSERT INTO sys_notice (title, content, publisher_username, publisher_name, audit_status, submitter_username)
SELECT '选座购票须知', '多主办方入驻；选座确认后即时占座并生成订单；过开场时间自动下架不可售。', 'admin', '平台管理员', 'approved', 'admin'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='选座购票须知');
"""

# 演艺单场馆（演艺皮）
_CINEMA_PERF = """\
INSERT INTO sys_user (username, password, role, nickname, phone, profile_json, super_admin, profile_editable, enabled) VALUES
('admin', 'admin123', 'admin', '场馆主管', '13800000000', '{}', 1, 0, 1),
('subadmin', 'sub123', 'admin', '售票员', '13800000001', '{}', 0, 1, 1),
('user', 'user123', 'user', '观众甲', '13800000002',
 '{"realName":"周观众","email":"zhou@demo.com","gender":"男","memberNo":"M20230015","orgName":"艺术学院"}',
 0, 1, 1)
ON DUPLICATE KEY UPDATE nickname=VALUES(nickname), phone=VALUES(phone), profile_json=VALUES(profile_json);

INSERT IGNORE INTO category (id, name) VALUES (1, '话剧'), (2, '音乐会'), (3, '脱口秀'), (4, '喜剧');
INSERT IGNORE INTO cinema_show (id, title, author, isbn, category_id, stock, status, seat_rows, seat_cols, start_at) VALUES
(1, '春江话剧夜', '88', '黑匣子', 1, 28, 'available', 6, 8, '2026-12-01 19:30:00'),
(2, '弦乐室内乐', '128', '室内乐厅', 2, 64, 'available', 8, 12, '2026-12-02 20:00:00'),
(3, '午夜脱口秀', '68', '地下剧场', 3, 18, 'available', 5, 10, '2026-12-02 22:30:00');

INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '选座购票须知', '选座确认后即时占座并生成订单；过开场时间自动下架不可售。', 'admin', '场馆主管'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='选座购票须知');
"""

# 演艺多主办方（演艺皮）
_CINEMA_PERF_MP = """\
INSERT INTO sys_user (username, password, role, nickname, phone, profile_json, super_admin, profile_editable, enabled) VALUES
('admin', 'admin123', 'admin', '平台管理员', '13800000000', '{}', 1, 0, 1),
('subadmin', 'sub123', 'admin', '潮汐剧场', '13800000001',
 '{"shopName":"潮汐剧场","shopIntro":"话剧与音乐会主办","shopPhone":"13800000001"}',
 0, 1, 1),
('merchant_b', 'mer123', 'admin', '星海演艺', '13800000012',
 '{"shopName":"星海演艺","shopIntro":"室内乐与脱口秀","shopPhone":"13800000012"}',
 0, 1, 1),
('user', 'user123', 'user', '观众甲', '13800000002',
 '{"realName":"周观众","email":"zhou@demo.com","gender":"男","memberNo":"M20230015","orgName":"艺术学院"}',
 0, 1, 1)
ON DUPLICATE KEY UPDATE nickname=VALUES(nickname), phone=VALUES(phone), profile_json=VALUES(profile_json),
 enabled=VALUES(enabled);

UPDATE sys_user SET staff_post='shop_merchant', staff_kind='clerk', role='admin', super_admin=0
WHERE username IN ('subadmin', 'merchant_b');

INSERT IGNORE INTO category (id, name) VALUES (1, '话剧'), (2, '音乐会'), (3, '脱口秀'), (4, '喜剧');
INSERT IGNORE INTO cinema_show (id, title, author, isbn, category_id, stock, status, seat_rows, seat_cols, start_at, owner_username) VALUES
(1, '春江话剧夜', '88', '黑匣子', 1, 28, 'available', 6, 8, '2026-12-01 19:30:00', 'subadmin'),
(2, '弦乐室内乐', '128', '室内乐厅', 2, 64, 'available', 8, 12, '2026-12-02 20:00:00', 'merchant_b'),
(3, '午夜脱口秀', '68', '地下剧场', 3, 18, 'available', 5, 10, '2026-12-02 22:30:00', 'subadmin');

INSERT INTO sys_notice (title, content, publisher_username, publisher_name, audit_status, submitter_username)
SELECT '选座购票须知', '多主办方入驻；选座确认后即时占座并生成订单；过开场时间自动下架不可售。', 'admin', '平台管理员', 'approved', 'admin'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='选座购票须知');
"""
