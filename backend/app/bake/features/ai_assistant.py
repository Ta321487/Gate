"""AI 助手岛（ai_assistant）：对话问答 + 知识条目 + 满意度 + 热门；Spring AI + DeepSeek。

跨域同一套能力；开题点名或 match 开关 force 时挂入。≠ doclib 文库下载、≠ 规则 recommend。
FAQ 分类名与业务 category / ticket_type 同字（商城见 scene_scan.SHOP_KIND_CATEGORIES）。
"""

from __future__ import annotations

import re
from typing import Any

from app.bake.proposal_lexicon import pattern_mentioned

AI_ASSISTANT_CAP = "ai_assistant"

# 勿用裸「知识库」（与 doclib 撞）；问答/客服/导购/大模型类才认
_AI_ASSISTANT_SIGNALS = re.compile(
    r"智能(?:客服|导购|助手|问答|答疑)|AI(?:智能)?(?:客服|导购|助手|问答|答疑)|"
    r"大模型(?:问答|客服|导购)?|chatgpt|ChatGPT|DeepSeek|deepseek|"
    r"Spring\s*AI|LangChain4j|LangChain|"
    r"对话式(?:商品)?推荐|(?:智能)?匹配知识库|知识库(?:匹配|问答)|"
    r"检索增强|(?<![A-Za-z])RAG(?![A-Za-z])|"
    r"阅读助手|(?:AI|智能)?馆员|馆员问答|智能体|AI\s*Agent|"
    r"语音播报|多轮对话|"
    r"(?:农产品|商品)?文字问答|图片上传匹配|答疑结果|"
    r"满意度反馈|热门(?:农产品)?问答"
)


def scan_ai_assistant(text: str) -> bool:
    return pattern_mentioned(text or "", _AI_ASSISTANT_SIGNALS, ignore_contrast=True)


def ai_assistant_wanted(
    *,
    capabilities: list[str] | None = None,
    proposal_text: str = "",
    force: bool = False,
) -> bool:
    if force:
        return True
    caps = list(capabilities or [])
    if AI_ASSISTANT_CAP in caps:
        return True
    return scan_ai_assistant(proposal_text)


def merge_ai_assistant_capabilities(
    caps: list[str],
    proposal_text: str = "",
    *,
    force: bool = False,
) -> list[str]:
    out = list(caps or [])
    want = ai_assistant_wanted(
        capabilities=out,
        proposal_text=proposal_text,
        force=force,
    )
    if want and AI_ASSISTANT_CAP not in out:
        out.append(AI_ASSISTANT_CAP)
    if not want:
        return [c for c in out if c != AI_ASSISTANT_CAP]
    return out


def attach_ai_assistant_menus(schema: dict[str, Any], proposal_text: str = "") -> None:
    from app.bake.schema.menu_utils import ensure_menu

    menus = schema.setdefault("menus", {})
    admin = menus.setdefault("admin", [])
    user = menus.setdefault("user", [])
    ensure_menu(
        admin,
        "ai_knowledge",
        {"key": "ai_knowledge", "label": "AI知识库", "superOnly": True},
        before_key="content",
    )
    ensure_menu(
        user,
        "ai_assistant",
        {"key": "ai_assistant", "label": "AI助手"},
        before_key="content",
    )
    if not any(m.get("key") == "ai_assistant" for m in user):
        ensure_menu(
            user,
            "ai_assistant",
            {"key": "ai_assistant", "label": "AI助手"},
            before_key="profile",
        )
    labels = schema.setdefault("labels", {})
    body = proposal_text or ""
    if re.search(r"农产品|智能导购|农产", body):
        labels.setdefault("aiAssistantPageTitle", "AI智能农产品导购")
        labels.setdefault(
            "aiAssistantPageLead",
            "对话式推荐与文字问答；图片按品类匹配知识；语音播报与满意度反馈；热门问答供选购参考。",
        )
    elif re.search(r"图书|馆员|阅读助手|借阅", body):
        labels.setdefault("aiAssistantPageTitle", "AI阅读助手")
        labels.setdefault(
            "aiAssistantPageLead",
            "图书咨询与阅读问答；可描述阅读偏好获取建议；支持语音播报与满意度反馈。",
        )
    else:
        labels.setdefault("aiAssistantPageTitle", "AI智能助手")
        labels.setdefault(
            "aiAssistantPageLead",
            "对话咨询、知识问答；可上传图片按品类匹配知识；支持语音播报与满意度反馈。",
        )
    labels.setdefault("aiKnowledgePageTitle", "AI知识库")
    ents = schema.setdefault("entities", {})
    if "ai_knowledge" not in ents:
        ents["ai_knowledge"] = {
            "key": "ai_knowledge",
            "label": "AI知识",
            "labelPlural": "AI知识条目",
        }


def apply_ai_assistant_to_spec(spec: dict[str, Any], proposal_text: str = "") -> dict[str, Any]:
    """合并 ai_assistant 能力、菜单、实体与 gate；匹配开关显式值优先于开题扫词。"""
    from app.bake.addons import resolve_ai_assistant

    addons = spec.get("addons") if isinstance(spec.get("addons"), dict) else {}
    has_explicit = spec.get("ai_assistant") is not None or (
        isinstance(addons, dict) and "ai_assistant" in addons
    )
    if has_explicit:
        want = resolve_ai_assistant(spec)
    else:
        caps0 = list(spec.get("capabilities") or [])
        want = AI_ASSISTANT_CAP in caps0 or scan_ai_assistant(proposal_text)

    caps = list(spec.get("capabilities") or [])
    if want and AI_ASSISTANT_CAP not in caps:
        caps.append(AI_ASSISTANT_CAP)
    if not want:
        caps = [c for c in caps if c != AI_ASSISTANT_CAP]

    spec = {**spec, "capabilities": caps}
    schema = dict(spec.get("schema") or {})
    schema["capabilities"] = caps

    if AI_ASSISTANT_CAP in caps:
        attach_ai_assistant_menus(schema, proposal_text)
        from app.bake.gate_contracts import merge_ai_assistant_gate

        gate = dict(spec.get("gate") or {})
        spec["gate"] = merge_ai_assistant_gate(gate, caps)

        features = list(spec.get("features") or [])
        names = {f.get("name") for f in features if isinstance(f, dict)}
        if "AI智能助手" not in names:
            features.append({"name": "AI智能助手", "status": "module"})
        spec["features"] = features

        ents = list(spec.get("entities") or [])
        if not any(isinstance(e, dict) and e.get("key") == "ai_knowledge" for e in ents):
            ents.append({"key": "ai_knowledge", "label": "AI知识", "labelPlural": "AI知识条目"})
        spec["entities"] = ents
    else:
        menus = schema.get("menus") if isinstance(schema.get("menus"), dict) else {}
        for side in ("admin", "user"):
            side_list = menus.get(side)
            if isinstance(side_list, list):
                menus[side] = [
                    m
                    for m in side_list
                    if not (
                        isinstance(m, dict)
                        and m.get("key") in ("ai_assistant", "ai_knowledge")
                    )
                ]
        if menus:
            schema["menus"] = menus

    spec["schema"] = schema
    on = AI_ASSISTANT_CAP in caps
    spec["ai_assistant"] = on
    addons_out = dict(addons) if isinstance(addons, dict) else {}
    addons_out["ai_assistant"] = on
    spec["addons"] = addons_out
    return spec


# —— FAQ 种子：分类名 = 业务货架 / 假别 / 工单类型同字 ——


def _faq(
    cat: str, title: str, content: str, keywords: str, hit: int
) -> tuple[str, str, str, str, int]:
    return (cat, title, content, keywords, hit)


def _shop_pack(kind: str) -> list[tuple[str, str, str, str, int]]:
    """商城 FAQ：三条分类名 = SHOP_KIND_CATEGORIES，第四条复用首分类讲下单。"""
    from app.bake.scene_scan import SHOP_KIND_CATEGORIES

    a, b, c = SHOP_KIND_CATEGORIES[kind]
    tips = {
        "farm": (
            f"本平台「{a}」分类可浏览应季鲜果，打开详情查看产地与说明后再加入购物车下单。挑选可参考色泽与有无破损。",
            f"「{b}」分类下叶菜宜吸湿后冷藏，根茎类放阴凉处；下单流程与其它商品相同，请在订单页查看状态。",
            f"「{c}」分类选购时看生产日期与包装完好；开封后密封存放。售后请在订单详情按流程申请。",
            "选好商品加入购物车并提交订单，按页面提示完成支付；支付后可在「我的订单」查看进度。",
        ),
        "retail": (
            f"在「{a}」分类查看推荐商品，对比价格与库存后加入购物车结算。",
            f"「{b}」分类多为日常用品，详情页看清规格说明再下单。",
            f"「{c}」分类可挑选通用配件；缺货时关注库存或换相近商品。",
            "提交订单并支付后，可在「我的订单」查看发货与收货进度；售后在订单详情发起。",
        ),
        "campus": (
            f"「{a}」分类可浏览教材与教辅，详情页可看成色说明。",
            f"「{b}」分类含耳机、键鼠等；请如实查看成色与自提说明后再下单。",
            f"「{c}」分类为日用与文创；支持校园自提点，请在地址中选好取件位置。",
            "下单后可在「我的订单」查看状态；请按页面提示到约定地点交接。",
        ),
        "print": (
            f"「{a}」可下单黑白打印页数套餐，到店取件或约定配送。",
            f"「{b}」支持彩印与胶装等装订服务，下单备注封面与页数要求。",
            f"「{c}」可购买纸张等耗材；库存以商品页为准。",
            "提交订单后请关注订单状态，按约定到店自取或等待配送。",
        ),
        "flowers": (
            f"「{a}」可浏览花束与切花，详情页查看枝数与送达说明后再下单。",
            f"「{b}」含盆栽绿植，请确认养护说明与配送方式。",
            f"「{c}」为地方特产礼盒等，可与鲜花一并加购。",
            "支付完成后可在「我的订单」查看进度；配送时间请在备注中写清。",
        ),
        "errand": (
            f"「{a}」可下单食堂等代买套餐（含跑腿费），写清送达宿舍或地点。",
            f"「{b}」用于超市日用代买，请在备注写清品牌与数量。",
            f"「{c}」可代取快递或打印店资料，写清驿站或取件码。",
            "下单后由跑腿员接单；请在「我的订单」查看状态并保持电话畅通。",
        ),
        "points": (
            f"「{a}」可用积分兑换文创礼品，以商品页积分与库存为准。",
            f"「{b}」为生活类兑换；兑换成功后按页面提示领取或自提。",
            f"「{c}」含虚拟权益类兑换，兑换后请在订单或个人中心查看。",
            "确认兑换并提交后，可在订单列表查看进度；积分不足时请先积攒。",
        ),
    }[kind]
    t0, t1, t2, t3 = tips
    return [
        _faq(a, f"「{a}」选购说明", t0, f"{a},选购,下单", 12),
        _faq(b, f"「{b}」选购说明", t1, f"{b},选购,咨询", 8),
        _faq(c, f"「{c}」选购说明", t2, f"{c},选购,售后", 6),
        _faq(a, "下单与订单进度", t3, "下单,购物车,订单,支付", 4),
    ]


_AI_SEED_PACKS: dict[str, list[tuple[str, str, str, str, int]]] = {
    # 图书默认皮 category：计算机 / 文学 / 历史（与 DOM-LIBRARY 模板一致）
    "library_book": [
        _faq(
            "计算机",
            "计算机类图书怎么找",
            "在图书列表选择「计算机」分类或关键词检索，打开详情查看在馆与可借数量后再申请借阅。",
            "计算机,检索,借阅",
            12,
        ),
        _faq(
            "文学",
            "文学类图书借阅说明",
            "「文学」分类可浏览小说与文集；提交借阅后由管理员确认，请在期限内归还。",
            "文学,借阅,归还",
            8,
        ),
        _faq(
            "历史",
            "历史类图书检索提示",
            "可用「历史」分类或书名/作者筛选；收藏后方便再次查找。",
            "历史,检索,收藏",
            6,
        ),
        _faq(
            "计算机",
            "续借与逾期怎么办",
            "临近到期可在「我的借阅」申请续借；逾期可能限制新借，请及时处理。",
            "续借,逾期,借阅",
            4,
        ),
    ],
    "library_archive": [
        _faq(
            "学籍档案",
            "学籍档案如何查阅",
            "在「学籍档案」分类找到卷宗后提交借阅/查阅申请，按馆内规定办理。",
            "学籍档案,查阅,借阅",
            12,
        ),
        _faq(
            "文书档案",
            "文书档案查阅说明",
            "「文书档案」含纪要等材料；请按页面提示申请并按时归还。",
            "文书档案,查阅",
            8,
        ),
        _faq(
            "科研档案",
            "科研档案检索",
            "可用「科研档案」分类定位建设与验收类材料，详情页查看卷号与状态。",
            "科研档案,检索",
            6,
        ),
        _faq(
            "人事档案",
            "档案借阅须知",
            "人事与其它档案仅限按规定查阅；请关注申请状态并遵守归还期限。",
            "人事档案,借阅,归还",
            4,
        ),
    ],
    "library_drift": [
        _faq(
            "文学",
            "漂流文学书怎么取阅",
            "在「文学」等分类选择漂流图书，提交借阅登记后按站点说明取还。",
            "文学,漂流,借阅",
            12,
        ),
        _faq(
            "社科",
            "社科类漂流书",
            "「社科」分类可浏览相关漂流册；读完请按时归还方便下一位同学。",
            "社科,漂流,归还",
            8,
        ),
        _faq(
            "科普",
            "科普漂流书检索",
            "可用「科普」分类或书名筛选；书架位置见详情备注。",
            "科普,检索,漂流",
            6,
        ),
        _faq(
            "教材",
            "教材漂流与归还",
            "「教材」类漂流册请爱护使用并按时归还；逾期会影响后续取阅。",
            "教材,漂流,归还",
            4,
        ),
    ],
    # 报修 ticket_type：水电 / 公共设施 / 门禁（DOM-PROPERTY）
    "dorm": [
        _faq(
            "水电",
            "水电报修怎么提交",
            "报修时选择类型「水电」，填写楼栋房间与故障描述，可附照片；提交后在进度页查看受理状态。",
            "水电,报修,进度",
            12,
        ),
        _faq(
            "公共设施",
            "公共设施故障报修",
            "楼道灯、电梯厅等请选「公共设施」并写清位置；紧急情况先联系值班电话。",
            "公共设施,报修",
            8,
        ),
        _faq(
            "门禁",
            "门禁问题怎么报",
            "门禁刷卡异常请选「门禁」类型报修，写清楼栋与卡号情况，等待后台派单。",
            "门禁,报修",
            6,
        ),
        _faq(
            "水电",
            "如何查看维修进度",
            "登录后打开「我的报修/工单」查看状态变更；长时间未更新可留言补充说明。",
            "进度,工单,报修",
            4,
        ),
    ],
    # 请假假别：事假类 / 病假类 / 其它假
    "attend": [
        _faq(
            "事假类",
            "如何提交事假",
            "选择假别「事假类」，填写起止时间与事由后提交；审批通过后生效。",
            "事假类,请假,审批",
            12,
        ),
        _faq(
            "病假类",
            "病假怎么请",
            "选择「病假类」并写清时间；如需证明材料按学校要求上传，关注审批状态。",
            "病假类,请假,材料",
            8,
        ),
        _faq(
            "其它假",
            "其它假别说明",
            "不在事假/病假范围的可选用「其它假」，事由请写清楚，被驳回后可按意见修改再提。",
            "其它假,请假,驳回",
            6,
        ),
        _faq(
            "事假类",
            "销假流程说明",
            "请假结束后在系统发起销假或由管理员确认；未销假可能影响后续请假。",
            "销假,确认,考勤",
            4,
        ),
    ],
    # 点餐 category：套餐 / 面食 / 饮品
    "food": [
        _faq(
            "套餐",
            "如何点套餐",
            "在「套餐」分类选择菜品加入购物车并提交订单，取餐请关注订单状态与窗口提示。",
            "套餐,点餐,购物车",
            12,
        ),
        _faq(
            "面食",
            "面食怎么点",
            "「面食」分类可选面类档口商品；高峰期建议错峰，备注口味后下单。",
            "面食,点餐,档口",
            8,
        ),
        _faq(
            "饮品",
            "饮品下单说明",
            "「饮品」可单独加购；支付完成后在订单列表查看取餐信息。",
            "饮品,订单,取餐",
            6,
        ),
        _faq(
            "套餐",
            "餐品问题怎么反馈",
            "可在订单评价或留言说明情况；紧急食品安全问题请线下联系食堂值班。",
            "评价,留言,反馈",
            4,
        ),
    ],
    # 文库：制度文件 / 课件资料 / 表格模板
    "doclib": [
        _faq(
            "制度文件",
            "如何下载制度文件",
            "在「制度文件」分类打开条目，按权限下载附件；下载记录便于管理。",
            "制度文件,下载,附件",
            12,
        ),
        _faq(
            "课件资料",
            "课件资料下载",
            "「课件资料」按登录与角色权限开放；无权限时请联系管理员开通。",
            "课件资料,下载,权限",
            8,
        ),
        _faq(
            "表格模板",
            "怎样找表格模板",
            "用「表格模板」分类或标题关键词筛选；常用模板可收藏。",
            "表格模板,检索,下载",
            6,
        ),
        _faq(
            "制度文件",
            "文库与 AI 问答的区别",
            "文库负责附件下载与管理；AI 助手回答本系统流程与知识条目问题，请分别使用。",
            "文库,问答,助手",
            4,
        ),
    ],
    "generic": [
        _faq(
            "通用",
            "如何登录与修改资料",
            "登录后可在个人中心修改昵称等资料。忘记密码请联系管理员重置。",
            "登录,资料,密码",
            12,
        ),
        _faq(
            "流程",
            "业务申请一般怎么走",
            "在对应菜单填写表单并提交，随后在「我的××」查看进度；管理员在后台审批或处理。",
            "申请,进度,审批",
            8,
        ),
        _faq(
            "公告",
            "公告与消息在哪看",
            "门户公告列表可浏览通知；站内消息可查看系统提醒。请及时阅读以免错过截止时间。",
            "公告,消息,通知",
            6,
        ),
        _faq(
            "助手",
            "AI 助手能做什么",
            "可咨询本系统常见操作与已维护的知识条目；命中知识库后会据此回答。"
            "未匹配到相关知识时请换问法，或由管理员补充知识库。",
            "助手,FAQ,知识库,流程",
            4,
        ),
    ],
}

# 商城各货皮动态挂入（与 SQL 种子同分类名）
for _kind in ("farm", "retail", "campus", "print", "flowers", "errand", "points"):
    _AI_SEED_PACKS[f"shop_{_kind}"] = _shop_pack(_kind)


def resolve_ai_knowledge_skin(
    domain: str = "",
    title: str = "",
    proposal_text: str = "",
) -> str:
    """选定 FAQ 种子皮：与 shop/library 货皮及业务分类名对齐。"""
    from app.bake.scene_scan import library_product_kind, shop_product_kind

    text = f"{title or ''}\n{proposal_text or ''}"
    dom = (domain or "").strip().upper()

    def _shop_skin() -> str:
        return f"shop_{shop_product_kind(title, proposal_text)}"

    def _library_skin() -> str:
        pk = library_product_kind(title, proposal_text)
        if pk == "archive":
            return "library_archive"
        if pk == "drift":
            return "library_drift"
        return "library_book"

    if dom == "DOM-SHOP":
        return _shop_skin()
    if dom == "DOM-LIBRARY":
        return _library_skin()
    if dom in ("DOM-DORM", "DOM-PROPERTY", "DOM-IT", "DOM-FITOUT"):
        return "dorm"
    if dom == "DOM-ATTEND":
        return "attend"
    if dom == "DOM-FOOD":
        return "food"
    if dom == "DOM-DOCLIB":
        return "doclib"
    if dom in ("DOM-LISTING", "DOM-CINEMA", "DOM-HOTEL", "DOM-TOUR"):
        return _shop_skin()

    # 无明确域：按开题词选皮（优先级：报修/请假/点餐/文库/图书 > 商城）
    if re.search(r"宿舍|报修|宿管|水电故障|物业报修", text):
        return "dorm"
    if re.search(r"请假|销假|考勤", text):
        return "attend"
    if re.search(r"点餐|食堂|档口|外卖", text):
        return "food"
    if re.search(r"文库|资料下载|制度文件|课件下载", text):
        return "doclib"
    if re.search(r"图书|借阅|馆员|阅读助手|图书馆|档案卷宗|漂流", text):
        return _library_skin()
    if re.search(
        r"农产品|农产|生鲜|果蔬|助农|商城|电商|二手|文印|打印|鲜花|花店|跑腿|积分兑换|选购|购物",
        text,
    ):
        return _shop_skin()
    return "generic"


def _sql_escape(s: str) -> str:
    return (s or "").replace("\\", "\\\\").replace("'", "''")


def build_ai_knowledge_seed_sql(
    domain: str = "",
    title: str = "",
    proposal_text: str = "",
) -> str:
    """生成幂等 INSERT 种子 SQL（4 条）。"""
    skin = resolve_ai_knowledge_skin(domain, title, proposal_text)
    rows = _AI_SEED_PACKS.get(skin) or _AI_SEED_PACKS["generic"]
    parts: list[str] = []
    for i, (cat, title_s, content, keywords, hit) in enumerate(rows):
        cond = (
            "NOT EXISTS (SELECT 1 FROM sys_ai_knowledge LIMIT 1)"
            if i == 0
            else f"(SELECT COUNT(*) FROM sys_ai_knowledge) < {i + 1}"
        )
        parts.append(
            "INSERT INTO sys_ai_knowledge (category, title, content, keywords, hit_count)\n"
            f"SELECT '{_sql_escape(cat)}', '{_sql_escape(title_s)}', "
            f"'{_sql_escape(content)}', '{_sql_escape(keywords)}', {int(hit)}\n"
            f"FROM DUAL WHERE {cond};"
        )
    return "\n".join(parts) + "\n"
