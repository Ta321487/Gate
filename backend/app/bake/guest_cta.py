"""门户游客 CTA：按域文案池 + 题号稳定抽一条。"""

from __future__ import annotations

import hashlib
from typing import Any

# 无公开目录 / 偏内部填报的域：不开游客逛
GUEST_BROWSE_EXCLUDE = frozenset({"DOM-DORM", "DOM-PROPERTY", "DOM-IT", "DOM-EVENT"})

GUEST_TEASER_LIMIT = 3

# 每域 4～6 条，贴合业务；缺省走 DEFAULT
CTA_BY_DOMAIN: dict[str, list[str]] = {
    "DOM-LIBRARY": [
        "登录后查看全部图书并申请借阅",
        "登录解锁完整书目与借阅记录",
        "登录查看更多馆藏与可借状态",
        "登录后继续检索并提交借阅申请",
    ],
    "DOM-EQUIP": [
        "登录后查看全部设备并申请借用",
        "登录解锁完整器材目录",
        "登录查看更多可借设备",
        "登录后提交借用申请",
    ],
    "DOM-ASSET": [
        "登录后查看全部物资并提交申领",
        "登录解锁完整物资台账",
        "登录查看更多库存物资",
        "登录后继续申领流程",
    ],

    "DOM-ATTEND": [
        "登录后提交请假并跟踪销假",
        "登录查看考勤公告与销假说明",
        "登录后继续请假申请流程",
        "登录查看更多请假须知",
    ],
    "DOM-RECRUIT": [
        "登录后浏览岗位并投递",
        "登录解锁完整职位列表",
        "登录查看更多在招岗位",
        "登录后提交投递单",
    ],
    "DOM-GRADE": [
        "登录后查看课程并申请更正",
        "登录解锁成绩与补考入口",
        "登录查看教务公告",
        "登录后继续成绩申请",
    ],
    "DOM-INTERN": [
        "登录后查看实习岗位",
        "登录解锁实习单位与导师",
        "登录后按周提交周报",
        "登录查看更多实习安排",
    ],
    "DOM-PARCEL": [
        "登录后查询包裹并取件",
        "登录解锁运单与取件码",
        "登录查看更多待取包裹",
        "登录后提交取件单",
    ],

    "DOM-CRM": [
        "登录后查看全部客户档案并跟进",
        "登录解锁完整客户列表",
        "登录查看更多客户详情",
        "登录后提交跟进记录",
    ],
    "DOM-EVENT": [
        "登录后查看全部事件档案并上报",
        "登录解锁完整事件列表",
        "登录查看更多事件详情",
        "登录后提交上报记录",
    ],
    "DOM-ACTIVITY": [
        "登录后查看全部活动并报名",
        "登录解锁更多社团活动",
        "登录查看完整活动日程",
        "登录后继续报名与签到",
        "登录查看更多可报名活动",
    ],
    "DOM-LOST": [
        "登录后查看全部启事并申请认领",
        "登录解锁完整失物列表",
        "登录查看更多失物详情",
        "登录后提交认领申请",
    ],
    "DOM-COURSE": [
        "登录后查看全部课程并选课",
        "登录解锁完整课表与名额",
        "登录查看更多公选课",
        "登录后提交选课申请",
    ],
    "DOM-SHOP": [
        "登录后查看全部商品并下单",
        "登录解锁完整商品目录",
        "登录查看更多好物",
        "登录后加入购物车结算",
    ],
    "DOM-FOOD": [
        "登录后查看全部菜品并下单",
        "登录解锁完整菜单",
        "登录查看更多今日供应",
        "登录后加入清单下单",
    ],
    "DOM-HOSPITAL": [
        "登录后查看全部号源并挂号",
        "登录解锁完整科室医生列表",
        "登录查看更多可约时段",
        "登录后预约就诊",
    ],
    "DOM-PARKING": [
        "登录后查看全部车位并预约",
        "登录解锁完整车位列表",
        "登录查看更多可约车位",
        "登录后占坑预约",
    ],
    "DOM-MEETING": [
        "登录后查看全部场地并预约",
        "登录解锁完整会议室列表",
        "登录查看更多可约时段",
        "登录后提交场地预约",
    ],
    "DOM-SALON": [
        "登录后查看全部服务并预约",
        "登录解锁完整项目列表",
        "登录查看更多可约时段",
        "登录后预约到店",
    ],
    "DOM-HOTEL": [
        "登录后查看全部房型并预订",
        "登录解锁完整客房列表",
        "登录查看更多可订日期",
        "登录后提交住宿预订",
    ],
    "DOM-MEDIA": [
        "登录后查看全部片单并收藏",
        "登录解锁完整影视库",
        "登录查看更多精彩内容",
        "登录后继续播放与收藏",
    ],
    "DOM-MUSIC": [
        "登录后查看全部曲库并收藏",
        "登录解锁完整歌单",
        "登录试听更多歌曲",
        "登录后继续收藏喜欢",
    ],
    "DOM-FORUM": [
        "登录后查看全部帖子并参与讨论",
        "登录解锁完整板块内容",
        "登录查看更多主帖与回复",
        "登录后发表回复",
    ],
    "DOM-BLOG": [
        "登录后阅读全部文章并收藏",
        "登录解锁完整博客目录",
        "登录查看更多博文",
        "登录后继续阅读与订阅",
    ],
}

CTA_DEFAULT = [
    "登录查看更多",
    "登录后解锁完整内容",
    "登录继续浏览全部数据",
    "登录查看完整列表",
]


def portal_guest_browse_enabled(domain: str, dom_meta: dict[str, Any] | None = None) -> bool:
    """目录型域默认开；宿舍/物业/IT/事件上报等内部填报域不开。显式 portal_guest_browse 优先。"""
    meta = dom_meta or {}
    if "portal_guest_browse" in meta:
        return bool(meta.get("portal_guest_browse"))
    if domain in GUEST_BROWSE_EXCLUDE:
        return False
    from app.bake.domains import DOMAIN_CAPABILITIES

    caps = DOMAIN_CAPABILITIES.get(domain) or []
    return "archive" in caps


def pick_guest_login_cta(domain: str, seed: str) -> str:
    pool = CTA_BY_DOMAIN.get(domain) or CTA_DEFAULT
    raw = f"{seed}|{domain}|guest-cta".encode()
    h = int(hashlib.md5(raw).hexdigest()[:8], 16)
    return pool[h % len(pool)]
