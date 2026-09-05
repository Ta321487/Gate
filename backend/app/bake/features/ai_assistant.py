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
    """商城 FAQ：分类名 = SHOP_KIND_CATEGORIES；热门标题按货皮开题口吻，忌千篇一律「选购说明」。"""
    from app.bake.scene_scan import SHOP_KIND_CATEGORIES

    a, b, c = SHOP_KIND_CATEGORIES[kind]
    packs: dict[str, list[tuple[str, str, str, str, int]]] = {
        "farm": [
            _faq(
                a,
                "如何挑选新鲜农产品",
                f"选购「{a}」等鲜品时看色泽是否均匀、有无破损与异味；打开详情查看产地与说明后再加入购物车。",
                "挑选,新鲜,农产品,选购,水果",
                12,
            ),
            _faq(
                a,
                "水果保存与食用建议",
                f"「{a}」宜阴凉通风或按品种冷藏；洗净后再食用。未熟果可常温催熟，变质果请勿食用。",
                "水果,保存,食用,建议",
                10,
            ),
            _faq(
                b,
                "叶菜与根茎保存常识",
                f"「{b}」中叶菜吸去水分后冷藏保鲜，根茎类放阴凉干燥处；下单流程与其它商品相同，请在订单页查看状态。",
                "叶菜,根茎,蔬菜,保存,常识",
                8,
            ),
            _faq(
                c,
                "粮油储存要点",
                f"「{c}」看生产日期与包装完好，开封后密封防潮；大米面粉宜干燥处存放。售后请在订单详情按流程申请。",
                "粮油,储存,大米,食用油",
                6,
            ),
        ],
        "retail": [
            _faq(
                a,
                "热销商品怎么选",
                f"在「{a}」分类浏览推荐款，对比价格与库存后加入购物车；详情页看清规格再下单。",
                f"{a},热销,选购,推荐",
                12,
            ),
            _faq(
                b,
                "日用商品购买须知",
                f"「{b}」多为日常用品，请确认规格与库存；提交订单后可在「我的订单」查看进度。",
                f"{b},日用,下单,规格",
                10,
            ),
            _faq(
                c,
                "配件缺货怎么办",
                f"「{c}」可挑选通用配件；缺货时关注库存或换相近商品，也可留言咨询管理员。",
                f"{c},配件,缺货,库存",
                8,
            ),
            _faq(
                a,
                "下单后如何查进度",
                "支付完成后打开「我的订单」查看发货与收货状态；售后在订单详情按流程发起。",
                "下单,订单,物流,售后,支付",
                6,
            ),
        ],
        "campus": [
            _faq(
                a,
                "教材教辅怎么买",
                f"在「{a}」分类按书名检索，详情页看成色与说明后再加购；支持校园自提。",
                f"{a},教材,教辅,二手,成色",
                12,
            ),
            _faq(
                b,
                "数码成色怎么看",
                f"「{b}」含耳机、键鼠等；请如实查看成色描述与自提说明，当面验收后再确认收货。",
                f"{b},数码,成色,自提",
                10,
            ),
            _faq(
                c,
                "自提点怎么选",
                f"「{c}」等商品支持校园自提；请在收货地址中选好取件位置并保持电话畅通。",
                f"{c},自提,地址,文创",
                8,
            ),
            _faq(
                a,
                "校园二手交易须知",
                "下单后在「我的订单」查看状态；请按页面提示到约定地点交接。",
                "二手,订单,交接,自提,校园",
                6,
            ),
        ],
        "print": [
            _faq(
                a,
                "黑白打印怎么下单",
                f"在「{a}」选择页数套餐加入购物车，备注纸张与单双面要求；到店取件或约定配送。",
                f"{a},打印,页数,下单",
                12,
            ),
            _faq(
                b,
                "彩印胶装怎么备注",
                f"「{b}」支持彩印与胶装；下单请在备注写清封面、页数与装订方式。",
                f"{b},彩印,胶装,装订",
                10,
            ),
            _faq(
                c,
                "耗材库存怎么看",
                f"「{c}」可购买纸张等耗材；库存以商品页为准，缺货时可换相近规格。",
                f"{c},耗材,纸张,库存",
                8,
            ),
            _faq(
                a,
                "取件与配送说明",
                "提交订单后关注订单状态，按约定到店自取或等待配送；取件请携带订单号。",
                "取件,配送,订单,文印",
                6,
            ),
        ],
        "flowers": [
            _faq(
                a,
                "花束怎么选购",
                f"在「{a}」浏览花束与切花，详情页查看枝数与送达说明后再下单；备注送达时间。",
                f"{a},花束,切花,选购",
                12,
            ),
            _faq(
                b,
                "盆栽养护注意什么",
                f"「{b}」含盆栽绿植，请确认养护说明与配送方式；到货后按说明浇水光照。",
                f"{b},盆栽,绿植,养护",
                10,
            ),
            _faq(
                c,
                "特产礼盒能一起买吗",
                f"「{c}」为地方特产礼盒等，可与鲜花一并加购；礼品卡语可写在订单备注。",
                f"{c},特产,礼盒,加购",
                8,
            ),
            _faq(
                a,
                "鲜花配送怎么写备注",
                "支付完成后可在「我的订单」查看进度；配送时间、门牌与联系人请在备注中写清。",
                "配送,备注,订单,鲜花",
                6,
            ),
        ],
        "errand": [
            _faq(
                a,
                "代买餐饮怎么下单",
                f"在「{a}」下单食堂等代买套餐（含跑腿费），备注写清档口、份数与送达宿舍。",
                f"{a},代买,餐饮,跑腿",
                12,
            ),
            _faq(
                b,
                "超市日用代买须知",
                f"「{b}」用于超市日用代买，请在备注写清品牌、规格与数量，便于跑腿员采购。",
                f"{b},代买,日用,超市",
                10,
            ),
            _faq(
                c,
                "代取快递怎么写",
                f"「{c}」可代取快递或打印店资料；请写清驿站名称、取件码与联系电话。",
                f"{c},代取,快递,取件码",
                8,
            ),
            _faq(
                a,
                "跑腿单进度怎么查",
                "下单后由跑腿员接单；请在「我的订单」查看状态并保持电话畅通，变更地址请及时留言。",
                "跑腿,订单,进度,电话",
                6,
            ),
        ],
        "points": [
            _faq(
                a,
                "积分怎么兑换文创",
                f"在「{a}」用积分兑换文创礼品，以商品页所需积分与库存为准；积分不足请先积攒。",
                f"{a},积分,兑换,文创",
                12,
            ),
            _faq(
                b,
                "生活类兑换怎么领",
                f"「{b}」为生活类兑换；兑换成功后按页面提示领取或到自提点核销。",
                f"{b},兑换,领取,自提",
                10,
            ),
            _faq(
                c,
                "虚拟权益兑换说明",
                f"「{c}」含虚拟权益类兑换，成功后请在订单或个人中心查看凭证。",
                f"{c},虚拟,权益,兑换",
                8,
            ),
            _faq(
                a,
                "兑换后如何查进度",
                "确认兑换并提交后，可在订单列表查看进度；积分变动以个人中心余额为准。",
                "兑换,订单,积分,进度",
                6,
            ),
        ],
    }
    if kind not in packs:
        raise KeyError(f"unknown shop AI skin kind: {kind}")
    return packs[kind]


_AI_SEED_PACKS: dict[str, list[tuple[str, str, str, str, int]]] = {
    # 图书默认皮 category：计算机 / 文学 / 历史（与 DOM-LIBRARY 模板一致）
    "library_book": [
        _faq(
            "计算机",
            "想借计算机类书怎么找",
            "在图书列表选择「计算机」分类或关键词检索，打开详情查看在馆与可借数量后再申请借阅。",
            "计算机,检索,借阅,怎么找",
            12,
        ),
        _faq(
            "文学",
            "文学书借阅要注意什么",
            "「文学」分类可浏览小说与文集；提交借阅后由管理员确认，请在期限内归还，可收藏方便再找。",
            "文学,借阅,归还,收藏",
            10,
        ),
        _faq(
            "历史",
            "历史书如何检索",
            "可用「历史」分类或书名/作者筛选；在馆状态以详情页为准，也可先收藏再借。",
            "历史,检索,在馆,筛选",
            8,
        ),
        _faq(
            "计算机",
            "续借与逾期怎么办",
            "临近到期可在「我的借阅」申请续借；逾期可能限制新借，请及时处理并关注催还通知。",
            "续借,逾期,借阅,催还",
            6,
        ),
    ],
    "library_archive": [
        _faq(
            "学籍档案",
            "学籍档案如何查阅",
            "在「学籍档案」分类找到卷宗后提交借阅/查阅申请，按馆内规定办理，注意归还期限。",
            "学籍档案,查阅,借阅,申请",
            12,
        ),
        _faq(
            "文书档案",
            "文书档案能查哪些",
            "「文书档案」含纪要等材料；请按页面提示申请并按时归还，涉密材料按权限开放。",
            "文书档案,查阅,纪要",
            10,
        ),
        _faq(
            "科研档案",
            "科研档案怎么检索",
            "可用「科研档案」分类定位建设与验收类材料，详情页查看卷号与状态后再申请。",
            "科研档案,检索,卷号",
            8,
        ),
        _faq(
            "人事档案",
            "档案借阅须知",
            "人事与其它档案仅限按规定查阅；请关注申请状态并遵守归还期限，不得擅自转借。",
            "人事档案,借阅,归还,须知",
            6,
        ),
    ],
    "library_drift": [
        _faq(
            "文学",
            "漂流文学书怎么取阅",
            "在「文学」等分类选择漂流图书，提交借阅登记后按站点说明取还，读完请及时归还。",
            "文学,漂流,借阅,取阅",
            12,
        ),
        _faq(
            "社科",
            "社科漂流书在哪",
            "「社科」分类可浏览相关漂流册；书架位置见详情备注，读完请按时归还方便下一位。",
            "社科,漂流,归还,书架",
            10,
        ),
        _faq(
            "科普",
            "科普漂流书怎么搜",
            "可用「科普」分类或书名筛选；找到后提交登记，按站点规则取还。",
            "科普,检索,漂流,筛选",
            8,
        ),
        _faq(
            "教材",
            "教材漂流与归还",
            "「教材」类漂流册请爱护使用并按时归还；逾期会影响后续取阅，请关注到期提醒。",
            "教材,漂流,归还,逾期",
            6,
        ),
    ],
    # 报修 ticket_type：水电 / 公共设施 / 门禁
    "dorm": [
        _faq(
            "水电",
            "水电报修怎么提交",
            "报修时选择类型「水电」，填写楼栋房间与故障描述，可附照片；提交后在进度页查看受理状态。",
            "水电,报修,进度,故障",
            12,
        ),
        _faq(
            "公共设施",
            "楼道灯坏了怎么报",
            "楼道灯、电梯厅等请选「公共设施」并写清位置；紧急情况先联系值班电话，再在系统留痕。",
            "公共设施,报修,楼道,电梯",
            10,
        ),
        _faq(
            "门禁",
            "门禁刷不了怎么报",
            "门禁刷卡异常请选「门禁」类型报修，写清楼栋与卡号情况，等待后台派单处理。",
            "门禁,报修,刷卡,卡号",
            8,
        ),
        _faq(
            "水电",
            "如何查看维修进度",
            "登录后打开「我的报修/工单」查看状态变更；长时间未更新可留言补充说明或联系值班。",
            "进度,工单,报修,维修",
            6,
        ),
    ],
    # 请假假别：事假类 / 病假类 / 其它假
    "attend": [
        _faq(
            "事假类",
            "如何提交事假",
            "选择假别「事假类」，填写起止时间与事由后提交；审批通过后生效，请提前申请。",
            "事假类,请假,审批,提交",
            12,
        ),
        _faq(
            "病假类",
            "病假怎么请",
            "选择「病假类」并写清时间；如需证明材料按学校要求上传，关注审批状态与销假要求。",
            "病假类,请假,材料,证明",
            10,
        ),
        _faq(
            "其它假",
            "其它假别怎么选",
            "不在事假/病假范围的可选用「其它假」，事由请写清楚，被驳回后可按意见修改再提。",
            "其它假,请假,驳回,假别",
            8,
        ),
        _faq(
            "事假类",
            "销假流程说明",
            "请假结束后在系统发起销假或由管理员确认；未销假可能影响后续请假，请返校当日处理。",
            "销假,确认,考勤,返校",
            6,
        ),
    ],
    # 点餐 category：套餐 / 面食 / 饮品
    "food": [
        _faq(
            "套餐",
            "如何点套餐",
            "在「套餐」分类选择菜品加入购物车并提交订单，取餐请关注订单状态与窗口提示。",
            "套餐,点餐,购物车,取餐",
            12,
        ),
        _faq(
            "面食",
            "面食档口怎么点",
            "「面食」分类可选面类档口商品；高峰期建议错峰，备注口味与忌口后下单。",
            "面食,点餐,档口,口味",
            10,
        ),
        _faq(
            "饮品",
            "饮品能单独下单吗",
            "「饮品」可单独加购；支付完成后在订单列表查看取餐信息，注意杯型备注。",
            "饮品,订单,取餐,加购",
            8,
        ),
        _faq(
            "套餐",
            "餐品问题怎么反馈",
            "可在订单评价或留言说明情况；紧急食品安全问题请线下联系食堂值班并保留凭证。",
            "评价,留言,反馈,食品安全",
            6,
        ),
    ],
    # 文库：制度文件 / 课件资料 / 表格模板
    "doclib": [
        _faq(
            "制度文件",
            "如何下载制度文件",
            "在「制度文件」分类打开条目，按权限下载附件；下载记录便于管理与追溯。",
            "制度文件,下载,附件,权限",
            12,
        ),
        _faq(
            "课件资料",
            "课件资料谁能下",
            "「课件资料」按登录与角色权限开放；无权限时请联系管理员开通后再下载。",
            "课件资料,下载,权限,角色",
            10,
        ),
        _faq(
            "表格模板",
            "怎样找表格模板",
            "用「表格模板」分类或标题关键词筛选；常用模板可收藏，下载后按说明填写。",
            "表格模板,检索,下载,收藏",
            8,
        ),
        _faq(
            "制度文件",
            "文库和 AI 问答有何不同",
            "文库负责附件下载与台账；AI 助手回答本系统流程与知识条目问题，请分别使用、勿混为一谈。",
            "文库,问答,助手,知识库",
            6,
        ),
    ],
    "generic": [
        _faq(
            "通用",
            "如何登录与修改资料",
            "登录后可在个人中心修改昵称等资料。忘记密码请联系管理员重置，勿使用他人账号。",
            "登录,资料,密码,个人中心",
            12,
        ),
        _faq(
            "流程",
            "业务申请一般怎么走",
            "在对应菜单填写表单并提交，随后在「我的××」查看进度；管理员在后台审批或处理。",
            "申请,进度,审批,流程",
            10,
        ),
        _faq(
            "公告",
            "公告与消息在哪看",
            "门户公告列表可浏览通知；站内消息可查看系统提醒。请及时阅读以免错过截止时间。",
            "公告,消息,通知,截止",
            8,
        ),
        _faq(
            "助手",
            "AI 助手能做什么",
            "可咨询本系统常见操作与已维护的知识条目；命中知识库后会据此回答。"
            "未匹配到相关知识时请换问法，或由管理员在知识库补充条目。",
            "助手,FAQ,知识库,流程,问答",
            6,
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
    if dom in ("DOM-LISTING", "DOM-CINEMA", "DOM-HOTEL", "DOM-TOUR", "DOM-CARRENT"):
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
