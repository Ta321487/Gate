"""一次性：把单条 ticket 场景种子扩成 pending/approved/returned。跑完可删。"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCENE = ROOT / "app" / "bake" / "sql" / "domain_scene_seed.py"

# (pending_title, pending_loc, type_id, room_id, priority, remark) → 扩 3 行
REPLACEMENTS: list[tuple[str, str]] = [
    (
        """INSERT IGNORE INTO ticket (id, username, title, location, type_id, room_id, status, priority, contact_phone, remark) VALUES
(1, 'user', 'A座1208无法连接内网', '办公区 1208', 1, 2, 'pending', '普通', '13800000002', '网线已插好，指示灯不亮。');""",
        """INSERT IGNORE INTO ticket (id, username, title, location, type_id, room_id, status, priority, contact_phone, remark) VALUES
(1, 'user', 'A座1208无法连接内网', '办公区 1208', 1, 2, 'pending', '普通', '13800000002', '网线已插好，指示灯不亮。'),
(2, 'user', '打印机卡纸', '办公区 1201', 3, 1, 'approved', '普通', '13800000002', '已派工处理中。'),
(3, 'user', '终端蓝屏重启', '办公区 1208', 2, 2, 'returned', '普通', '13800000002', '已重装驱动办结。');""",
    ),
    (
        """INSERT IGNORE INTO ticket (id, username, title, location, type_id, room_id, status, priority, contact_phone, remark) VALUES
(1, 'user', '学生公寓3号楼405灯不亮', '学生公寓3号楼 405', 1, 1, 'pending', '普通', '13800000002', '卫生间灯具不亮，已换保险丝无效。');""",
        """INSERT IGNORE INTO ticket (id, username, title, location, type_id, room_id, status, priority, contact_phone, remark) VALUES
(1, 'user', '学生公寓3号楼405灯不亮', '学生公寓3号楼 405', 1, 1, 'pending', '普通', '13800000002', '卫生间灯具不亮，已换保险丝无效。'),
(2, 'user', '406水龙头漏水', '学生公寓3号楼 406', 1, 2, 'approved', '普通', '13800000002', '维修中。'),
(3, 'user', '教学楼A门禁刷卡失败', '教学楼A 201', 3, 3, 'returned', '普通', '13800000002', '已更换读卡器。');""",
    ),
    (
        """INSERT IGNORE INTO ticket (id, username, title, location, type_id, room_id, status, priority, contact_phone, remark) VALUES
(1, 'user', '东区一街路灯不亮', '东区一街 路灯12', 1, 1, 'pending', '普通', '13800000002', '夜间整段不亮，影响通行。');""",
        """INSERT IGNORE INTO ticket (id, username, title, location, type_id, room_id, status, priority, contact_phone, remark) VALUES
(1, 'user', '东区一街路灯不亮', '东区一街 路灯12', 1, 1, 'pending', '普通', '13800000002', '夜间整段不亮，影响通行。'),
(2, 'user', '西区二路井盖松动', '西区二路 井盖A3', 2, 2, 'approved', '普通', '13800000002', '已围挡待换。'),
(3, 'user', '路灯08灯罩破损', '西区二路 路灯08', 1, 3, 'returned', '普通', '13800000002', '已更换灯罩。');""",
    ),
    (
        """INSERT IGNORE INTO ticket (id, username, title, location, type_id, room_id, status, priority, contact_phone, remark) VALUES
(1, 'user', 'A栋夜间装修噪音', 'A 栋 101', 1, 1, 'pending', '普通', '13800000002', '连续三天夜间施工，请核实劝阻。');""",
        """INSERT IGNORE INTO ticket (id, username, title, location, type_id, room_id, status, priority, contact_phone, remark) VALUES
(1, 'user', 'A栋夜间装修噪音', 'A 栋 101', 1, 1, 'pending', '普通', '13800000002', '连续三天夜间施工，请核实劝阻。'),
(2, 'user', '楼道堆物占道', 'A 栋 102', 2, 2, 'approved', '普通', '13800000002', '已约谈清理中。'),
(3, 'user', '客服态度投诉', 'B 栋 201', 3, 3, 'returned', '普通', '13800000002', '已回访办结。');""",
    ),
    (
        """INSERT IGNORE INTO ticket (id, username, title, location, type_id, room_id, status, priority, contact_phone, remark) VALUES
(1, 'user', '城东门店退换货咨询', '城东门店 柜台1', 1, 1, 'pending', '普通', '13800000002', '到货外观破损，申请换货。');""",
        """INSERT IGNORE INTO ticket (id, username, title, location, type_id, room_id, status, priority, contact_phone, remark) VALUES
(1, 'user', '城东门店退换货咨询', '城东门店 柜台1', 1, 1, 'pending', '普通', '13800000002', '到货外观破损，申请换货。'),
(2, 'user', '维修进度催问', '城东门店 柜台2', 2, 2, 'approved', '普通', '13800000002', '维修中已回电。'),
(3, 'user', '服务投诉已处理', '城西网点 自提点', 3, 3, 'returned', '普通', '13800000002', '已赔付办结。');""",
    ),
    (
        """INSERT IGNORE INTO ticket (id, username, title, location, type_id, room_id, status, priority, contact_phone, remark) VALUES
(1, 'user', '机房UPS-01异响告警', '机房区 UPS-01', 2, 1, 'pending', '紧急', '13800000002', '夜间告警灯闪烁，请上门排查。');""",
        """INSERT IGNORE INTO ticket (id, username, title, location, type_id, room_id, status, priority, contact_phone, remark) VALUES
(1, 'user', '机房UPS-01异响告警', '机房区 UPS-01', 2, 1, 'pending', '紧急', '13800000002', '夜间告警灯闪烁，请上门排查。'),
(2, 'user', '空调-02定期保养', '机房区 空调-02', 1, 2, 'approved', '普通', '13800000002', '保养进行中。'),
(3, 'user', '打印-03更换硒鼓', '办公区 打印-03', 3, 3, 'returned', '普通', '13800000002', '备件已换办结。');""",
    ),
]


def main() -> None:
    text = SCENE.read_text(encoding="utf-8")
    for old, new in REPLACEMENTS:
        if old not in text:
            raise SystemExit(f"missing block:\n{old[:80]}...")
        text = text.replace(old, new, 1)
    SCENE.write_text(text, encoding="utf-8")
    print("patched", len(REPLACEMENTS), "ticket scene seeds")


if __name__ == "__main__":
    main()
