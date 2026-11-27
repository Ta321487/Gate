"""基线壳菜单（key 真源）。

时序 demote、论文模块图过滤、终稿「相近」剔噪共用此处。
禁止在 absorb / sequence / modules 再抄平行中文名单。
"""

from __future__ import annotations

# kind=open 且属壳入口时，时序候选 demote（业务主入口不因 open 被挤）
SHELL_OPEN_MENU_KEYS: frozenset[str] = frozenset(
    {
        "users",
        "profile",
        "messages",
        "banners",
        "online_sessions",
        "schedule_jobs",
        "site_stat",
        "content",
        "addresses",
        "lookup",
        "guestbook",
    }
)

# 运维壳：论文模块图默认不进；开题点名（广告位/定时/在线用户）才留
THESIS_DIAGRAM_SHELL_KEYS: frozenset[str] = frozenset(
    {"banners", "schedule_jobs", "scheduled_tasks", "online_sessions"}
)

# 终稿相近剔噪用的壳 key（比时序 demote 窄：不含地址/字典等可成业务点的）
NEAR_DUP_SHELL_MENU_KEYS: frozenset[str] = frozenset(
    {
        "users",
        "profile",
        "messages",
        "content",
        "banners",
        "guestbook",
        "dashboard",
        "home",
        "schedule_jobs",
        "scheduled_tasks",
        "online_sessions",
        "site_stat",
    }
)

# key → 终稿 feature_lines 常见中文写法（含变体）；只服务壳 key，不发明业务词
_SHELL_LABEL_ALIASES: dict[str, frozenset[str]] = {
    "users": frozenset({"用户管理", "系统用户管理"}),
    "profile": frozenset({"个人中心", "个人信息管理", "个人资料", "资料管理"}),
    "messages": frozenset({"消息中心", "站内信", "我的消息"}),
    "content": frozenset({"公告管理", "通知公告", "通知公告管理", "资讯管理"}),
    "banners": frozenset(
        {"轮播图管理", "轮播管理", "广告位管理", "横幅管理", "Banner管理"}
    ),
    "guestbook": frozenset({"留言管理", "留言反馈", "留言板管理"}),
    "dashboard": frozenset({"工作台", "管理首页"}),
    "home": frozenset({"系统首页", "系统首页管理", "首页", "首页管理"}),
    "schedule_jobs": frozenset({"定时任务", "定时任务管理", "计划任务"}),
    "scheduled_tasks": frozenset({"定时任务", "定时任务管理", "计划任务"}),
    "online_sessions": frozenset({"在线用户", "在线用户管理", "在线会话"}),
    "site_stat": frozenset({"站点统计", "访问统计"}),
}

# 非菜单壳入口（登录页等）
_SHELL_CHROME_LABELS: frozenset[str] = frozenset(
    {"登录", "注册", "登录注册", "关于我们"}
)


def near_dup_shell_feature_labels() -> frozenset[str]:
    """终稿跨记录相近计分要剔除的壳文案（由壳 key 展开，禁止旁路手写表）。"""
    out: set[str] = set(_SHELL_CHROME_LABELS)
    for key in NEAR_DUP_SHELL_MENU_KEYS:
        out |= set(_SHELL_LABEL_ALIASES.get(key, frozenset()))
    return frozenset(out)
