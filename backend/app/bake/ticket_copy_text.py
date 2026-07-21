"""单据/档案提示文案：bake 写入 domain-ticket-copy.json 与 schema，运行时只读。"""

from __future__ import annotations


def sibling_reject_tip(archive_label: str, apply_verb: str) -> str:
    """库存扣尽时自动驳回同对象待审的说明。"""
    noun = (archive_label or "项目").strip() or "项目"
    v = apply_verb or ""
    if "认领" in v:
        tip = "已确认认领"
    elif "借阅" in v or "借用" in v:
        tip = "已借完"
    elif "申领" in v:
        tip = "已申领完毕"
    elif "选课" in v or "报名" in v:
        tip = "名额已满"
    else:
        tip = "已无法再申请"
    return f"「{noun}」{tip}，系统自动驳回"


def stock_unavailable_label(stock_label: str) -> str:
    """available 模式下库存为 0 的标签：可认领→已认领。"""
    s = (stock_label or "可用").strip() or "可用"
    if s.startswith("可"):
        return "已" + s[1:]
    return f"暂无{s}"
