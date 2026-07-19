"""One-shot generator for D/E domain SQL. Run: python backend/scripts/_gen_l2_sql.py"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "app" / "bake" / "sql"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.bake.engine import assert_table_budget, count_create_tables  # noqa: E402

SYS_USER = """CREATE TABLE IF NOT EXISTS sys_user (
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
"""

SYS_MSG = """CREATE TABLE IF NOT EXISTS sys_message (
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
"""

SYS_NOTICE = """CREATE TABLE IF NOT EXISTS sys_notice (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  title VARCHAR(128) NOT NULL,
  content TEXT,
  publisher_username VARCHAR(64),
  publisher_name VARCHAR(64),
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
"""


def header(domain: str) -> str:
    return f"""-- bake domain={domain} · tables in [${{TABLE_COUNT_MIN}},${{TABLE_COUNT_MAX}}]
CREATE DATABASE IF NOT EXISTS `${{DB_NAME}}` DEFAULT CHARACTER SET utf8mb4;
USE `${{DB_NAME}}`;

"""


def order_tables() -> str:
    return """CREATE TABLE IF NOT EXISTS cart_line (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  username VARCHAR(64) NOT NULL,
  item_id BIGINT NOT NULL,
  qty INT NOT NULL DEFAULT 1,
  UNIQUE KEY uk_cart (username, item_id)
);

CREATE TABLE IF NOT EXISTS biz_order (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  username VARCHAR(64) NOT NULL,
  status VARCHAR(32) NOT NULL DEFAULT 'pending',
  total_yuan DECIMAL(10,2) NOT NULL DEFAULT 0,
  remark VARCHAR(255) DEFAULT '',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS order_line (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  order_id BIGINT NOT NULL,
  item_id BIGINT NOT NULL,
  title VARCHAR(200) NOT NULL,
  price_yuan DECIMAL(10,2) NOT NULL DEFAULT 0,
  qty INT NOT NULL DEFAULT 1
);

"""


def slot_tables() -> str:
    return """CREATE TABLE IF NOT EXISTS resource_slot (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  item_id BIGINT NOT NULL,
  start_at DATETIME NOT NULL,
  end_at DATETIME NOT NULL,
  capacity INT NOT NULL DEFAULT 1,
  booked INT NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS reservation (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  slot_id BIGINT NOT NULL,
  username VARCHAR(64) NOT NULL,
  status VARCHAR(32) NOT NULL DEFAULT 'confirmed',
  remark VARCHAR(255) DEFAULT '',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

"""


def item_table(name: str) -> str:
    return f"""CREATE TABLE IF NOT EXISTS category (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  name VARCHAR(64) NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS {name} (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  title VARCHAR(200) NOT NULL,
  author VARCHAR(100),
  isbn VARCHAR(128),
  category_id BIGINT,
  stock INT DEFAULT 0,
  status VARCHAR(32) DEFAULT 'available',
  cover_url VARCHAR(255),
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

"""


def users(role_user: str, nick: str, profile: str) -> str:
    return f"""INSERT INTO sys_user (username, password, role, nickname, phone, profile_json, super_admin, profile_editable, enabled) VALUES
('admin', 'admin123', 'admin', '系统管理员', '13800000000', '{{}}', 1, 0, 1),
('subadmin', 'sub123', 'admin', '业务管理员', '13800000001', '{{}}', 0, 1, 1),
('{role_user}', '{role_user}123', '{role_user}', '{nick}', '13800000002',
 '{profile}',
 0, 1, 1)
ON DUPLICATE KEY UPDATE nickname=VALUES(nickname), phone=VALUES(phone), profile_json=VALUES(profile_json);

"""


def notice(title: str, body: str) -> str:
    return f"""INSERT INTO sys_notice (title, content, publisher_username, publisher_name)
SELECT '{title}', '{body}', 'admin', '系统管理员'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_notice WHERE title='{title}');
"""


def slots_seed(item_ids, day="2026-09-20", hours=((9, 10), (10, 11), (14, 15), (15, 16)), capacity=2):
    rows = []
    i = 1
    for item_id in item_ids:
        for h0, h1 in hours:
            rows.append(
                f"({i}, {item_id}, '{day} {h0:02d}:00:00', '{day} {h1:02d}:00:00', {capacity}, 0)"
            )
            i += 1
    return (
        "INSERT IGNORE INTO resource_slot (id, item_id, start_at, end_at, capacity, booked) VALUES\n"
        + ",\n".join(rows)
        + ";\n"
    )


def write_slot_domain(
    domain,
    item,
    role,
    nick,
    profile,
    cats,
    items,
    notice_t,
    notice_b,
    capacity=2,
    with_order=False,
):
    body = header(domain) + SYS_USER + item_table(item) + slot_tables()
    if with_order:
        body += order_tables()
    body += SYS_MSG + SYS_NOTICE
    body += users(role, nick, profile)
    body += cats + items
    body += slots_seed([1, 2, 3], capacity=capacity)
    body += notice(notice_t, notice_b)
    (ROOT / f"{domain}.sql").write_text(body, encoding="utf-8")


def main():
    shop = header("DOM-SHOP") + SYS_USER + item_table("product") + order_tables() + SYS_MSG + SYS_NOTICE
    shop += users(
        "user",
        "买家甲",
        '{"realName":"王同学","email":"wang@demo.edu","gender":"男","studentNo":"20260001","college":"计算机学院"}',
    )
    shop += """INSERT IGNORE INTO category (id, name) VALUES (1, '数码'), (2, '日用'), (3, '文创');
INSERT IGNORE INTO product (id, title, author, isbn, category_id, stock, status) VALUES
(1, '机械键盘', '199.00', 'KB-01', 1, 20, 'available'),
(2, '桌面台灯', '59.90', 'LAMP-02', 2, 35, 'available'),
(3, '校徽帆布袋', '29.00', 'BAG-03', 3, 50, 'available'),
(4, '无线鼠标', '89.00', 'MS-04', 1, 15, 'available');
"""
    shop += notice("商城开业", "欢迎选购校园好物；演示下单无真支付。")
    (ROOT / "DOM-SHOP.sql").write_text(shop, encoding="utf-8")

    food = header("DOM-FOOD") + SYS_USER + item_table("dish") + order_tables() + SYS_MSG + SYS_NOTICE
    food += users(
        "user",
        "用餐者甲",
        '{"realName":"李同学","email":"li@demo.edu","gender":"女","studentNo":"20260002","college":"经管学院"}',
    )
    food += """INSERT IGNORE INTO category (id, name) VALUES (1, '套餐'), (2, '面食'), (3, '饮品');
INSERT IGNORE INTO dish (id, title, author, isbn, category_id, stock, status) VALUES
(1, '红烧肉套餐', '18.00', '窗口A', 1, 80, 'available'),
(2, '番茄鸡蛋面', '12.00', '窗口B', 2, 60, 'available'),
(3, '豆浆油条', '8.00', '早餐档', 1, 100, 'available'),
(4, '柠檬茶', '6.00', '饮品站', 3, 120, 'available');
"""
    food += notice("食堂点餐", "下单后到窗口取餐；演示环境无真支付。")
    (ROOT / "DOM-FOOD.sql").write_text(food, encoding="utf-8")

    write_slot_domain(
        "DOM-MEETING",
        "room",
        "user",
        "预约人甲",
        '{"realName":"赵老师","email":"zhao@demo.edu","gender":"男","employeeNo":"T1001","dept":"教务处"}',
        "INSERT IGNORE INTO category (id, name) VALUES (1, '小型'), (2, '中型'), (3, '大型');\n",
        """INSERT IGNORE INTO room (id, title, author, isbn, category_id, stock, status) VALUES
(1, 'A101 研讨室', '0', '楼A-101 / 6人', 1, 1, 'available'),
(2, 'B203 会议室', '0', '楼B-203 / 12人', 2, 1, 'available'),
(3, '报告厅', '0', '图文中心 / 80人', 3, 1, 'available');
""",
        "会议室预约须知",
        "请按预约时段使用并按时离开；可取消释放名额。",
        capacity=1,
    )
    write_slot_domain(
        "DOM-HOSPITAL",
        "doctor",
        "patient",
        "患者甲",
        '{"realName":"钱患者","email":"qian@demo.edu","gender":"女","cardNo":"H20260001"}',
        "INSERT IGNORE INTO category (id, name) VALUES (1, '内科'), (2, '外科'), (3, '口腔');\n",
        """INSERT IGNORE INTO doctor (id, title, author, isbn, category_id, stock, status) VALUES
(1, '张医生', '15.00', '主任医师 / 上午门诊', 1, 1, 'available'),
(2, '李医生', '15.00', '副主任医师', 2, 1, 'available'),
(3, '王医生', '20.00', '口腔专科', 3, 1, 'available');
""",
        "挂号须知",
        "选择医生与时段挂号；号源有限，约满不可再约。",
        capacity=3,
    )
    write_slot_domain(
        "DOM-PARKING",
        "space",
        "user",
        "车主甲",
        '{"realName":"孙同学","email":"sun@demo.edu","gender":"男","plateNo":"粤B12345"}',
        "INSERT IGNORE INTO category (id, name) VALUES (1, '地上'), (2, '地下');\n",
        """INSERT IGNORE INTO space (id, title, author, isbn, category_id, stock, status) VALUES
(1, 'A区-01', '5.00', '地上东侧', 1, 1, 'available'),
(2, 'A区-02', '5.00', '地上东侧', 1, 1, 'available'),
(3, 'B区-地下-08', '8.00', '地下二层', 2, 1, 'available');
""",
        "车位预约",
        "预约成功后请按时入场；取消后释放车位时段。",
        capacity=1,
    )
    write_slot_domain(
        "DOM-SALON",
        "service",
        "user",
        "顾客甲",
        '{"realName":"周同学","email":"zhou@demo.edu","gender":"女"}',
        "INSERT IGNORE INTO category (id, name) VALUES (1, '剪发'), (2, '护理');\n",
        """INSERT IGNORE INTO service (id, title, author, isbn, category_id, stock, status) VALUES
(1, '基础剪发', '45.00', '约45分钟', 1, 1, 'available'),
(2, '精致烫染咨询', '0', '到店面议', 1, 1, 'available'),
(3, '头皮护理', '68.00', '约60分钟', 2, 1, 'available');
""",
        "服务预约",
        "请选择服务与时段；迟到可能需改约。",
        capacity=2,
    )
    write_slot_domain(
        "DOM-HOTEL",
        "room_type",
        "user",
        "住客甲",
        '{"realName":"吴旅客","email":"wu@demo.edu","gender":"男"}',
        "INSERT IGNORE INTO category (id, name) VALUES (1, '标准间'), (2, '大床房');\n",
        """INSERT IGNORE INTO room_type (id, title, author, isbn, category_id, stock, status) VALUES
(1, '标准双床房', '268.00', '含早 / 2人', 1, 5, 'available'),
(2, '舒适大床房', '328.00', '含早 / 2人', 2, 4, 'available'),
(3, '行政大床房', '488.00', '含早 / 景观', 2, 2, 'available');
""",
        "客房预订",
        "选择房型与入住时段预订；演示无真支付，预约成功生成订单。",
        capacity=3,
        with_order=True,
    )

    for name in [
        "DOM-SHOP",
        "DOM-FOOD",
        "DOM-MEETING",
        "DOM-HOSPITAL",
        "DOM-PARKING",
        "DOM-SALON",
        "DOM-HOTEL",
    ]:
        t = (ROOT / f"{name}.sql").read_text(encoding="utf-8")
        n = count_create_tables(t)
        assert_table_budget(t, name)
        print(name, n, "OK")


if __name__ == "__main__":
    main()
