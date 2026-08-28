"""Checklist 能力项关键词：开题文本对照与包后门禁判定的共享词表。

- **文本层**（`feature_hints`）：生成前 proposal diff 用，匹配开题措辞 ↔ checklist 项名。
- **实装层**（`gate_keyword_triggers` + `evaluate._checklist_feature_ok`）：包后门禁用，查 workspace 路由/文件/API。

两层职责不同，但共享同一套能力触发词，避免「措辞核对绿了、实装验收仍红」因词表漂移。
"""

from __future__ import annotations

import re

# 短词白名单：子串匹配时允许 <4 字
SHORT_TERMS = frozenset(
    {
        "登录",
        "注册",
        "公告",
        "分类",
        "审核",
        "驳回",
        "归还",
        "借阅",
        "报修",
        "预约",
        "下单",
        "跟进",
        "档案",
        "销假",
        "请假",
        "投递",
        "检索",
        "浏览",
        "签到",
        "归寝",
        "缺勤",
        "寝室",
        "查寝",
        "床位",
        "调宿",
        "选房",
        "退宿",
        "楼栋",
        "行程",
        "拼车",
        "意向",
        "余座",
        "路线",
        "访客",
        "到访",
        "通行",
        "被访",
        "订单",
        "取餐",
        "配送",
        "发帖",
        "回帖",
        "帖子",
        "商品",
        "菜品",
        "餐品",
        "岗位",
        "投递",
        "周报",
        "包裹",
        "取件",
        "核销",
        "补考",
        "成绩",
        "销假",
        "假勤",
        "派单",
        "完结",
        "跟进",
        "客户",
        "线索",
        "投票",
        "问卷",
        "选座",
        "挂号",
        "号源",
        "对接",
        "发布",
        "跟帖",
        "楼中楼",
        "回复",
        "余座",
        "占用",
        "释放",
        "会员",
        "牵线",
        "私信",
        "题库",
        "组卷",
        "判分",
        "作答",
        "科目",
        "服务",
        "时段",
        "事项",
        "登记",
        "工单",
        "站点",
        "说明",
        "评教",
        "问卷",
        "填写",
        "回收",
        "时段",
        "取消",
        "退库",
        "回补",
        "文档",
        "时长",
        "账户",
        "互选",
        "婉拒",
        "科室",
        "挂号",
        "挂牌",
        "房源",
        "资料",
        "下载",
    }
)

# 单独命中不足以认定对照（同名不同义时宁可漏报、不误绿）
GENERIC_TOKENS = frozenset(
    {
        "管理",
        "查询",
        "统计",
        "信息",
        "系统",
        "功能",
        "模块",
        "业务",
        "数据",
        "维护",
        "发布",
        "查阅",
        "展示",
        "用户",
        "记录",
        "申请",
        "提交",
        "审核",
        "浏览",
        "检索",
        "查看",
        "台账",
        "通知",
        "资料",
        "详情",
        "列表",
        "操作",
    }
)

# evaluate._checklist_feature_ok 分支触发词（按项名子串）
GATE_NAME_TRIGGERS = (
    "借阅记录",
    "借用记录",
    "申领记录",
    "报修记录",
    "报修",
    "借用",
    "借阅",
    "提醒",
    "罚款",
    "归还",
    "逾期",
    "分类",
    "读者",
    "学生管理",
    "用户管理",
    "患者管理",
    "会员管理",
    "楼栋",
    "房间管理",
    "区域终端",
    "报修类型",
    "故障类型",
    "工作台",
    "设备",
    "图书",
    "物资",
    "菜品",
    "商品",
    "号源",
    "车位",
    "场地",
    "公告",
    "登录",
    "注册",
    "个人资料",
    "头像",
    "购物车",
    "下单",
    "订单",
    "预约",
    "猜你喜欢",
    "推荐",
    "故障",
    "受理",
)

_CJK_RE = re.compile(r"[\u4e00-\u9fff]{2,8}")


def normalize_text(text: str) -> str:
    s = re.sub(r"\s+", "", (text or "").strip().lower())
    return s[:120]


def extract_tokens(text: str) -> set[str]:
    norm = normalize_text(text)
    tokens = set(_CJK_RE.findall(norm))
    for short in SHORT_TERMS:
        if short in norm:
            tokens.add(short)
    return {t for t in tokens if t}


def gate_keyword_triggers(feature_name: str) -> set[str]:
    """包后门禁 `_checklist_feature_ok` 会对该项名触发的关键词分支。"""
    name = (feature_name or "").strip()
    if not name:
        return set()
    return {t for t in GATE_NAME_TRIGGERS if t in name}


def feature_hints(feature_name: str) -> set[str]:
    """从 checklist 项名派生可命中开题多样措辞的提示词（跨域通用）。"""
    name = (feature_name or "").strip()
    if not name:
        return set()
    hints: set[str] = {name}

    if "登录" in name or "注册" in name:
        hints.update({"登录", "注册", "鉴权", "签到"})
    if "个人资料" in name or "头像" in name:
        hints.update({"个人资料", "资料维护", "资料", "头像", "读者证", "班级信息"})
    if "工作台" in name or "概览" in name or "驾驶舱" in name:
        hints.update({"工作台", "概览", "驾驶舱", "业务概览", "统计图表", "统计"})
    if "公告" in name:
        hints.update({"公告", "通知", "公示"})
    if any(k in name for k in ("用户管理", "读者管理", "学生管理", "会员管理", "患者管理")):
        hints.update(
            {
                "用户管理",
                "用户信息",
                "人员档案",
                "读者管理",
                "学生管理",
                "会员管理",
                "人员管理",
            }
        )
    if "分类" in name:
        hints.update({"分类", "类别"})
    if "记录" in name:
        hints.update({"记录", "台账", "历史", "查询"})
    if any(
        k in name
        for k in (
            "档案",
            "检索",
            "详情",
            "书目",
            "器材",
            "物资",
            "商品",
            "岗位",
            "客户",
            "会员",
            "图书",
            "设备",
            "菜品",
            "号源",
            "车位",
            "场地",
            "建档",
        )
    ):
        hints.update({"档案", "检索", "浏览", "录入", "维护", "详情", "书目", "建档"})
    if any(
        k in name
        for k in (
            "跟进",
            "借阅",
            "报修",
            "申领",
            "请假",
            "投递",
            "预约",
            "下单",
            "购物车",
            "订单",
            "销假",
            "归还",
            "审核",
        )
    ):
        hints.update(
            {
                "提交",
                "审核",
                "审批",
                "驳回",
                "办结",
                "完结",
                "入档",
                "销假",
                "归还",
                "占用",
                "出库",
                "派工",
            }
        )
    if "推荐" in name or "猜你喜欢" in name:
        hints.update({"推荐", "猜你喜欢", "书目展示"})
    if "逾期" in name or "罚款" in name or "提醒" in name:
        hints.update({"逾期", "罚款", "提醒", "应还"})
    if "购物车" in name or "下单" in name or ("订单" in name and "记录" not in name):
        hints.update({"购物车", "下单", "订单", "结算"})
    if "预约" in name:
        hints.update({"预约", "号源", "场次", "名额"})
    if "归寝" in name or "查寝" in name:
        hints.update(
            {
                "归寝",
                "查寝",
                "归寝登记",
                "晚归登记",
                "归寝审核",
                "查寝签到",
                "宿舍签到",
                "查寝安排",
                "查寝场次",
                "本人寝室",
            }
        )
    if "口令" in name and "签到" in name:
        hints.update({"口令签到", "签到", "宿舍签到", "查寝签到", "参与签到", "口令"})
    if "缺勤" in name or "未签到" in name:
        hints.update({"缺勤", "未签到", "缺勤记录", "查看缺勤", "缺勤统计", "缺勤标记"})
    if "寝室" in name:
        hints.update({
            "寝室",
            "查寝场次",
            "查寝安排",
            "查寝窗口",
            "寝室信息",
            "本人寝室",
            "楼栋",
            "寝室目录",
        })

    # —— 跨域通用：档案 / 目录 / 浏览 ——
    if "档案" in name or name.endswith("区域") or name.endswith("浏览") or name.endswith("检索"):
        stem = name.replace("档案", "").replace("浏览", "").replace("检索", "")
        if stem:
            hints.update({stem, f"{stem}目录", f"浏览{stem}", f"{stem}与"})
        hints.update(
            {
                "基础数据",
                "空余",
                "余座",
                "情况",
                "楼栋",
                "台账",
                "目录维护",
                "数据维护",
                "基础台账",
            }
        )
        if "床位" in name:
            hints.update({"床位", "楼栋", "选房", "调宿", "退宿", "宿舍床位", "空余情况"})
        if "行程" in name:
            hints.update({"行程", "拼车", "路线", "余座", "时间", "基础数据维护"})
        if "到访" in name or "区域" in name:
            hints.update({"到访", "访客", "被访", "来访", "区域维护"})

    # —— 申请审核 / 审批流 ——
    if "申请审核" in name or (name.endswith("审核") and "管理" not in name):
        stem = name.replace("申请审核", "").replace("审核", "")
        hints.update(
            {
                f"{stem}申请",
                "提交申请",
                "管理侧",
                "审批",
                "通过",
                "驳回",
                "占用",
                "释放",
            }
        )
        if "床位" in name or "床位" in stem:
            hints.update({"选房", "调宿", "退宿", "床位", "退宿申请", "调宿申请"})
        if "访客" in name:
            hints.update({"访客登记", "访客预约", "被访", "到访", "通行"})
        if "借阅" in name or "借用" in name:
            hints.update({"借阅", "借用", "归还", "应还"})

    # —— 记录 / 台账查询 ——
    if "记录" in name:
        hints.update({"本人记录", "查询本人", "本人", "本人意向", "历史", "查询", "台账查询"})
        if "访客" in name:
            hints.update({"访客", "来访", "预约"})
        if "意向" in name:
            hints.update({"意向", "同行", "拼车"})
        if "申请" in name or "床位" in name:
            hints.update({"选房", "调宿", "退宿"})
        if "借阅" in name or "借用" in name or "报修" in name:
            hints.update({"借阅", "借用", "报修", "历史查询"})
        if "订单" in name:
            hints.update({"订单", "本人订单", "配送", "取餐"})

    # —— 发布 / 对接（拼车、用户发帖等）——
    if "发布" in name and "公告" not in name:
        stem = name.replace("发布", "")
        hints.update({"发布", "填写", "登记", stem, f"发布{stem}"})
        if "行程" in name:
            hints.update({"拼车", "行程", "路线", "余座", "时间", "发布拼车"})
    if "对接" in name:
        hints.update({"对接", "意向", "同行", "确认", "婉拒", "提交", "浏览行程", "同行意向"})
    if "通行码" in name:
        hints.update({"通行码", "签到", "签离", "临时通行", "签发", "通行说明"})

    # —— 交易 / 论坛 ——
    if "订单管理" in name:
        hints.update({"订单", "本人订单", "查询本人", "配送", "取餐", "发货", "状态", "取货", "骑手"})
    if "购物车" in name or "下单取餐" in name or name == "下单取餐":
        hints.update({"购物车", "下单", "加购", "结算", "取餐", "提交订单"})
    if "商品浏览" in name:
        hints.update({"商品", "分类浏览", "检索", "浏览", "可购"})
    if "菜品浏览" in name:
        hints.update({"菜品", "餐品", "分类浏览", "检索", "浏览", "选菜", "档口", "餐品与分类"})
    if "发帖" in name:
        hints.update({"发帖", "帖子", "发布帖", "撰写", "主题"})
    if "回复" in name or "回帖" in name or "楼中楼" in name:
        hints.update({"回复", "回帖", "楼中楼", "跟帖", "评论", "资源帖"})
    if "分类" in name:
        hints.update(
            {
                "分类维护",
                "基础台账",
                "台账维护",
                "菜品分类",
                "商品分类",
                "书目分类",
                "餐品与分类",
                "事件分类",
                "周报分类",
                "包裹分类",
                "合同分类",
                "资助项目与分类",
                "房型与基础数据",
                "事项档案维护",
                "区域与事项维护",
                "事项与车辆档案",
            }
        )

    # —— 跟进 / 投递 / 周报 / parcel 等单据措辞 ——
    if "跟进" in name:
        hints.update({"跟进", "线索", "客户", "阶段", "完结", "沟通"})
    if "投递" in name:
        hints.update({"投递", "简历", "岗位", "初筛", "招聘"})
    if "周报" in name or "审阅" in name:
        hints.update({"周报", "审阅", "提交", "导师", "实习"})
    if "取件" in name or "包裹" in name or "入库" in name:
        hints.update({"取件", "包裹", "入库", "核销", "取件码", "滞留"})
    if "投票" in name:
        hints.update({"投票", "评选", "候选人", "票数"})
    if "问卷" in name:
        hints.update({"问卷", "填写", "提交", "题目"})
    if "选座" in name or "场次" in name:
        hints.update({"选座", "场次", "座位", "影厅"})
    if "补考" in name or "成绩" in name:
        hints.update({"补考", "成绩", "更正", "科目", "查询"})
    if "销假" in name or "请假" in name:
        hints.update({"销假", "请假", "假勤", "假单", "返校"})
    if "报修" in name or "派单" in name:
        hints.update({"报修", "派单", "受理", "完结", "维修", "工单"})
    if "预约" in name and "访客" not in name:
        hints.update({"预约", "号源", "取消预约", "核销", "占号", "时段", "释放时段", "本人预约", "取消"})

    # —— 类型/项目/事项（无「档案」后缀的目录项）——
    if name.endswith("类型") or name.endswith("项目") or "事项" in name:
        hints.update(
            {
                "事项",
                "登记事项",
                "浏览",
                "类型",
                "事项档案",
                "档案维护",
                "基础数据维护",
                "创新学分",
                "竞赛获奖",
                "学科竞赛",
            }
        )
    if "成果" in name:
        hints.update({"成果", "创新学分", "竞赛", "获奖", "登记"})

    # —— 工单 / 物业报修 ——
    if "工单" in name:
        hints.update(
            {
                "报修",
                "工单",
                "受理",
                "完结",
                "提交报修",
                "填写说明",
                "选择",
                "处理",
                "维修",
            }
        )
    if "位置" in name:
        hints.update({"位置", "站点", "楼栋", "房间", "站点信息"})

    # —— 婚恋交友 ——
    if "交友资料" in name or "会员资料" in name:
        hints.update({"会员资料", "资料浏览", "检索", "会员", "浏览"})
    if "牵线" in name:
        hints.update({"牵线", "关注", "红娘", "撮合", "发起"})
    if "私信" in name:
        hints.update({"私信", "沟通", "短轮询", "刷新", "一对一"})

    # —— 在线考试 ——
    if "题库" in name or "组卷" in name:
        hints.update({"题库", "组卷", "发布试卷", "维护题库", "录题", "试卷"})
    if "作答" in name or "判分" in name:
        hints.update({"开考", "作答", "判分", "客观题", "主观题", "关键词", "考生", "成绩", "错题本"})
    if "考试科目" in name or ("科目" in name and "考试" in name):
        hints.update({"考试科目", "科目分类", "浏览", "检索"})

    # —— 问卷 / 评教 ——
    if "问卷" in name:
        hints.update({"问卷", "填写", "回收", "统计", "选项", "限填", "每人"})
    if "评教" in name or "教学评价" in name:
        hints.update({"评教", "教学评价", "提交评语", "问卷", "汇总"})

    # —— 服务/场地预约 ——
    if "服务" in name and ("浏览" in name or "预约" in name):
        hints.update({"服务项目", "项目浏览", "检索", "时段", "预约", "取消", "释放时段", "本人预约"})
    if name == "服务与预约" or "与预约" in name:
        hints.update({"选择时段", "提交预约", "本人预约", "取消", "释放时段"})

    # —— 登记类 OA（成果/证书/报销等）——
    if "登记" in name and "审核" in name:
        hints.update({"在线提交", "提交登记", "填写说明", "登记", "审批", "驳回"})
    if name.endswith("目录") or "目录" in name:
        hints.update({"目录", "目录维护", "维护", "事项档案"})

    # —— 互选 / 组队 ——
    if "互选" in name or "组队" in name or "搭子" in name or "双选" in name:
        hints.update({"互选", "组队", "搭子", "对方", "确认", "婉拒", "完成对接"})
    if "时长" in name or "时间银行" in name:
        hints.update({"志愿", "时长", "账户", "余额", "服务"})
    if "文档" in name or "资料库" in name:
        hints.update({"文档", "上传", "下载", "查阅", "台账"})
    if "退库" in name or "回补" in name or "申领" in name:
        hints.update({"退库", "回补", "申领", "出库", "库存"})
    if "科室" in name or "号源" in name or "挂号" in name:
        hints.update({"科室", "号源", "挂号", "按科室", "医生", "排班"})
    if "入库" in name or "在库" in name:
        hints.update({"入库", "在库", "货位", "滞留", "催取", "出库", "逾期"})

    # —— 施工 / 装修 / 德育 / 车辆等 OA 长尾 ——
    if "施工" in name:
        hints.update({"装修", "备案", "进场", "说明", "装修备案", "进场说明", "浏览"})
    if "德育" in name or ("指标" in name and "德育" not in name):
        hints.update({"综测", "加减分", "申报事项", "德育", "加分", "减分"})
    if name == "车辆" or name.startswith("车"):
        hints.update({"车辆", "用车", "公务用车", "可用车", "派车", "事项", "档案"})
    if "资助" in name:
        hints.update({"资助", "申请", "办结", "审核", "通过", "驳回", "管理侧", "项目"})
    if "预订订单" in name:
        hints.update({"入住", "退房", "房态", "办理", "状态", "预约", "占用", "订单"})
    if "房型" in name:
        hints.update({"房型", "客房", "基础数据", "浏览", "检索"})
    if "周报" in name and "审阅" in name:
        hints.update({"点评", "退回修改", "通过", "管理侧", "审阅"})
    if "包裹台账" in name or (name.startswith("包裹") and "记录" not in name):
        hints.update({"包裹", "入库", "出库", "逾期", "取件码", "浏览", "台账"})
    if "合同" in name:
        hints.update({"合同", "单级", "完结", "办理", "登记", "类型目录", "类型档案"})
    if "事件上报" in name:
        hints.update({"上报", "确认", "完结", "驳回", "处置", "管理侧", "填写说明"})
    if "事件档案" in name:
        hints.update({"事件", "档案", "分类浏览", "检索", "维护"})
    if "资料条目" in name or ("资料" in name and "下载" not in name):
        hints.update({"资料", "条目", "上传", "维护", "维护资料", "分类浏览", "检索", "附件", "权限"})
    if "资料下载" in name:
        hints.update({"下载", "下载台账", "台账", "权限", "附件", "在线查看", "查看下载"})
    if "房源" in name:
        hints.update({"房源", "挂牌", "带看", "类型与挂牌", "房源类型", "中介"})
    if name.endswith("区域") or "到访" in name:
        hints.update({"区域说明", "可访问", "浏览", "说明", "区域与事项", "站点", "事项维护"})
    if "准入" in name or "实验室" in name:
        hints.update({"准入", "审批", "办结", "通过", "驳回", "管理侧"})

    # —— 内容组：选课 / 影视 / 音乐 / 博客 ——
    if "课程" in name or "选课" in name:
        hints.update({"选课", "课表", "冲突", "学分", "占名额", "课程", "提交"})
    if "片单" in name or "影视" in name or "媒资" in name or "视频" in name:
        hints.update({"片单", "播放", "收藏", "广播", "静态文件", "视频", "点播"})
    if "曲库" in name or ("音乐" in name and "收藏" not in name):
        hints.update({"曲库", "歌单", "收藏", "播放", "歌曲", "音频", "流媒体"})
    if "收藏" in name or "喜欢" in name:
        hints.update({"收藏", "喜欢", "取消收藏", "我的收藏", "片单", "歌单"})
    if "文章" in name or "博文" in name or "资讯" in name:
        hints.update({"文章", "博文", "资讯", "编辑", "发布", "浏览", "稿件"})

    hints.update(extract_tokens(name))
    return {normalize_text(h) for h in hints if h and normalize_text(h)}
