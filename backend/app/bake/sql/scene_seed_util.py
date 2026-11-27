"""场景种子共用：替换 user 种子尾、门户身份补丁、工作台订单/工单行。"""

from __future__ import annotations

import re

_USER_SEED_START = re.compile(
    r"INSERT INTO sys_user \(username, password, role, nickname, phone, profile_json, "
    r"super_admin, profile_editable, enabled\) VALUES\n",
)

def _replace_user_seed_tail(sql: str, seed: str) -> str:
    m = _USER_SEED_START.search(sql)
    if not m:
        return sql
    return sql[: m.start()] + seed.rstrip() + "\n"


def _patch_portal_user_identity(
    sql: str,
    *,
    nickname: str,
    profile_json: str,
) -> str:
    """仅改门户 user 昵称与 profile_json，保留模板档案/单据种子。"""
    return re.sub(
        r"\('user',\s*'user123',\s*'user',\s*'[^']*',\s*'[^']*',\s*\n\s*'\{.*?\}'",
        f"('user', 'user123', 'user', '{nickname}', '13800000002',\n"
        f" '{profile_json}'",
        sql,
        count=1,
        flags=re.S,
    )


_OA_ENTERPRISE_USER = (
    "员工甲",
    '{"realName":"陈工","email":"chen@demo.com","gender":"男",'
    '"identityType":"员工","employeeNo":"E20230108","dept":"综合管理部"}',
)
_FITOUT_COMMUNITY_USER = (
    "业主甲",
    '{"realName":"刘明","email":"liu@demo.com","gender":"男",'
    '"identityType":"业主","communityName":"阳光小区","houseBuilding":"3栋",'
    '"houseUnit":"2","houseNo":"501"}',
)
_CARPASS_ENTERPRISE_USER = (
    "员工甲",
    '{"realName":"陈工","email":"chen@demo.com","gender":"男",'
    '"identityType":"员工","employeeNo":"E20230108","dept":"行政部"}',
)


def _workbench_orders_sql(
    specs: list[tuple[int, int, str, float | str, str, str]],
    *,
    contact: str = "王先生",
    phone: str = "13800000002",
    address: str = "示例小区 3 栋 1201",
    delivery: str = "配送到家",
    username: str = "user",
    taste_by_oid: dict[int, str] | None = None,
) -> str:
    """多态订单种子：pending/confirmed/shipped/completed + 日期，工作台 KPI/趋势不空。

    specs: (order_id, item_id, title, price, status, remark)
    taste_by_oid：点餐域附带 taste_note 列。
    """
    day_by_status = {
        "pending": 0,
        "confirmed": 1,
        "shipped": 2,
        "completed": 4,
    }
    tastes = taste_by_oid or {}
    with_taste = taste_by_oid is not None
    order_rows: list[str] = []
    line_rows: list[str] = []
    for oid, iid, title, price, status, remark in specs:
        st = (status or "pending").strip()
        day = day_by_status.get(st, 1)
        title_s = str(title).replace("'", "''")
        remark_s = str(remark).replace("'", "''")
        contact_s = contact.replace("'", "''")
        address_s = address.replace("'", "''")
        delivery_s = delivery.replace("'", "''")
        user_s = username.replace("'", "''")
        created = f"DATE_SUB(NOW(), INTERVAL {day} DAY)"
        if st == "completed":
            done = f"DATE_SUB(NOW(), INTERVAL {max(day - 1, 0)} DAY)"
        else:
            done = "NULL"
        base = (
            f"({oid}, '{user_s}', '{st}', {price}, '{remark_s}', '{contact_s}', "
            f"'{phone}', '{address_s}', '{delivery_s}'"
        )
        if with_taste:
            taste_s = str(tastes.get(oid, "")).replace("'", "''")
            order_rows.append(f"{base}, '{taste_s}', {created}, {done})")
        else:
            order_rows.append(f"{base}, {created}, {done})")
        line_rows.append(
            f"({oid}, {oid}, {iid}, '{title_s}', {price}, 1)"
        )
    if with_taste:
        order_head = (
            "INSERT IGNORE INTO biz_order (id, username, status, total_yuan, remark, "
            "receiver_name, receiver_phone, address_line, delivery_type, taste_note, "
            "created_at, completed_at) VALUES\n"
        )
    else:
        order_head = (
            "INSERT IGNORE INTO biz_order (id, username, status, total_yuan, remark, "
            "receiver_name, receiver_phone, address_line, delivery_type, created_at, "
            "completed_at) VALUES\n"
        )
    return (
        order_head
        + ",\n".join(order_rows)
        + ";\n"
        "INSERT IGNORE INTO order_line (id, order_id, item_id, title, price_yuan, qty) "
        "VALUES\n"
        + ",\n".join(line_rows)
        + ";\n"
    )


# 商城皮沿用旧名
_shop_workbench_orders_sql = _workbench_orders_sql


def _workbench_tickets_sql(
    rows: list[tuple[int, str, str, str, int, int, str, str, str, str]],
) -> str:
    """报修/工单多态种子：pending / approved / returned（+ 可选 rejected）。

    rows: (id, username, title, location, type_id, room_id, status, priority, phone, remark)
    """
    line_rows: list[str] = []
    for tid, uname, title, loc, type_id, room_id, status, priority, phone, remark in rows:
        line_rows.append(
            "("
            f"{tid}, '{str(uname).replace(chr(39), chr(39)+chr(39))}', "
            f"'{str(title).replace(chr(39), chr(39)+chr(39))}', "
            f"'{str(loc).replace(chr(39), chr(39)+chr(39))}', "
            f"{type_id}, {room_id}, '{status}', '{priority}', "
            f"'{str(phone).replace(chr(39), chr(39)+chr(39))}', "
            f"'{str(remark).replace(chr(39), chr(39)+chr(39))}'"
            ")"
        )
    return (
        "INSERT IGNORE INTO ticket (id, username, title, location, type_id, room_id, "
        "status, priority, contact_phone, remark) VALUES\n"
        + ",\n".join(line_rows)
        + ";\n"
    )
