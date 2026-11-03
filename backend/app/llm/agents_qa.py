"""Agent D：交付 QA（LLM 主审；无模型时结构回退）。"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.llm.agents_common import *  # noqa: F403
from app.llm.client import (
    append_deepseek_log,
    budget_ok,
    chat,
    format_usage_detail,
)
from app.llm.temperature import temperature_for

_SYS = (
    "你是毕设交付 QA Agent（Drift/Consistency）。"
    "只报「真真切切影响程序运行或答辩演示」的问题；禁止改代码；少说；无把握宁可不报。\n"
    "只输出 JSON：\n"
    '{"ok":boolean,"summary":string,'
    '"findings":[{"level":"error|warn|info","msg":string,"where":string}],'
    '"priorities":string[]}\n'
    "何谓影响程序（仅这些可进 warn/error）：\n"
    "· 某角色实际打开的页面会显示错误导语/错误菜单（角色串台、关键 labels 缺失且该角色菜单已挂）；\n"
    "· 开题/capabilities 未挂却在可见文案宣称已支持（假功能）；\n"
    "· 错域串台导致演示像另一套系统；空壳/写死工厂腔/占位导致演示走不通。\n"
    "一律不报：措辞好不好听、建议补充、体验优化、文案润色、开题没写的功能遐想、"
    "双口径里「买家键仍是买家句」（管理端另有 Admin/Staff 键时）。\n"
    "说话纪律：\n"
    "A) 默认 findings/priorities 为空。\n"
    "B) 禁止「建议/宜/不妨/可以更好/优化体验」句式。\n"
    "C) 禁止臆造 capabilities 未挂的缺口。\n"
    "D) 说不清会挡哪条演示路径 → 不报或 info。\n"
    "level=error 仅误导答辩/明显错域；where 填文件路径或 schema 字段名。\n"
    "必须以结构化字段为准：entityKeys / menuKeys / staffPackMenus / traits / capabilities / labels；"
    "文件摘录可能被截断，禁止凭摘录臆造未出现在结构化字段里的实体或菜单。\n"
    "工厂口径（勿误报）：\n"
    "1) entities 槽位常见为 archive/ticket/reservation/order/category；"
    "menus.admin 含 category 且 entityKeys 含 category → 不算缺口；"
    "staffPackMenus 只含本域岗位已挂 pack，勿把未列出的 pack/菜单名当成实体；"
    "menuKeys 未含 my_tickets/cart/orders 时，勿审 MyTickets/Cart/MyOrders 等未挂路由骨架页"
    "（baseline 会保留文件供 Vite 静态分析，不代表本期交付页）。"
    "实体 states 里没有的状态，若摘录里只出现在 allow* 或 hasCap 开关分支中，不是本期文案，勿报错域残留。\n"
    "2) traits.followUp（或旧包 traits.crm）表示跟进表单能力（渠道/下次复核），"
    "是跨域 UI 特征，不是「必须等于 CRM 行业域」；勿因 flavor/题名不含 CRM 而报错。\n"
    "3) NoticeDetail 正文小标题允许 labels.noticeBodyHeading 或中性「正文」。\n"
    "诚实口径（Q-04，必须遵守）：\n"
    "4) 禁止用错域实体名：INTERN≠投递/入职多家；RECRUIT≠周报岗；EVAL≠成绩更正；"
    "MORAL≠评教；BED≠宿舍报修；PARCEL≠跑腿商城；HOTEL≠会议室+小卖部交叉壳；"
    "INSTRUMENT≠纯场地预约；EXAM≠问卷/评教；LOST≠宠物挂号。\n"
    "5) capabilities 未列出的能力不得宣称「已支持/已集成」："
    "人脸/指纹/GPS、真微信支付/支付宝、法大大/CA、RFID/多仓ERP、小程序原生等硬边界"
    "若出现在交付文案且当作本期功能 → level=error；若仅「非本期/不做」说明 → 不算问题。\n"
    "6) accept=reject 或 out_of_mvp 已标缺口时，禁止在 summary 写「可全文答辩/已支持该能力」。\n"
    "7) 订单评价双口径：orderReviewPageTitle/Lead=买家；"
    "orderReviewAdminPageLead=总管；orderReviewStaffPageLead=商家/办理员回复。"
    "已有 Staff/Admin 评价导语时，勿因买家键仍是「我的评价」再报商家菜单文案不匹配。"
    "同类双口径（ordersAdminLead/ordersStaffLead、tickets*Lead 等）同理：勿把买家/用户键当成管理端缺文案。\n"
    "8) summary 只概括是否发现会影响程序/演示的问题；无则写「未发现影响程序运行或答辩演示的问题」。"
)

# LLM warn/error 须命中「影响程序」信号，否则当噪声（结构闸另走，不经此滤）
_PROGRAM_IMPACT_RE = re.compile(
    r"缺失|缺少|缺\s*labels\.|labels\.\w+\s*缺失|"
    r"错域|跨域|串台|串邻|串成|残留|"
    r"假宣称|宣称已支持|已集成|已对接|未挂能力|capabilities|"
    r"空壳|写死|工厂腔|占位|"
    r"未挂|未路由|无入口|走不通|"
    r"管理员确认发货|总管.*(?:发货|物流)|"
    r"角色冲突|口径相反|不匹配|只有买家|买家口径"
)

# 硬边界种子（短、稳定；不是域文案穷举）。单独出现不算宣称已支持。
_HARD_BOUNDARY_AS_SUPPORTED = (
    (re.compile(r"(人脸识别|指纹闸机|GPS\s*轨迹|真门禁开锁)"), "生物识别/硬件定位"),
    (re.compile(r"(微信支付|支付宝(支付|对接)|真实支付)"), "真支付对接"),
    (re.compile(r"(法大大|上上签|第三方电子签|CA\s*证书)"), "第三方电子签/CA"),
    (re.compile(r"(RFID\s*盘点|多仓\s*WMS|ERP\s*财务)"), "RFID/多仓ERP"),
)

# 同窗「宣称已支持」搭配（小集合）。无搭配 → 不升 error（避免否定句/背景调研误杀）。
# 排除「不支持/非支持」：前缀否定用 lookbehind。
_CLAIM_AS_SUPPORTED = re.compile(
    r"(?<![不非未勿])("
    r"已支持|已集成|已对接|已接入|已开通|已上线|可全文答辩|已完整实现|"
    r"支持(?!期)|集成了|对接了|接入了|本期可用"
    r")"
)

# 「非本期 / 不做 / 不接」及常见划界，不算宣称支持
_HONEST_SCOPE = re.compile(
    r"(非本期|本期不|不做|不接|不在本期|不作为本期|不纳入|超出|硬边界|演示级替代|"
    r"仅作为背景|背景对比|调研阶段|扩展能力|必实现项|不实现|"
    r"非法大大|非\s*CA|非真支付|非真门禁|并非|不是本期|仅作查阅|演示级)"
)

# 命中词紧前短窗内的否定（「非 CA…第三方电子签」「未对接微信支付」）
_PREFIX_NEGATION = re.compile(r"(非|不|勿|禁止|未|并非)[\w\s、，,．.]*$")

# 域 → 错域实体词（出现在 labels/菜单且像主叙事时 warn）
_WRONG_DOMAIN_ENTITY: dict[str, tuple[str, ...]] = {
    "DOM-INTERN": ("简历投递", "多单位入职", "同时入职多家"),
    "DOM-RECRUIT": ("提交周报", "实习鉴定", "在岗填报"),
    "DOM-EVAL": ("成绩更正", "成绩复核"),
    "DOM-GRADE": ("网上评教", "多维评分"),
    "DOM-BED": ("宿舍报修", "水电维修"),
    "DOM-DORM": ("床位分配", "调宿申请", "选房"),
    "DOM-PARCEL": ("跑腿代买", "外卖配送"),
    "DOM-HOTEL": ("会议室预约", "小卖部下单"),
    "DOM-LOST": ("门诊挂号", "宠物医院"),
    "DOM-HOSPITAL": ("流浪动物领养", "认领申请"),
}


def _read_clip(path: Path, limit: int = 1800) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")[:limit]


def _menu_keys(menus: Any) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    if not isinstance(menus, dict):
        return out
    for side, items in menus.items():
        if not isinstance(items, list):
            continue
        keys = [str(m.get("key")) for m in items if isinstance(m, dict) and m.get("key")]
        out[str(side)] = keys
    return out


def _delivered_skin(workspace: Path) -> dict[str, Any]:
    """从 appDelivered 抽 traits/flavor（截断摘录读不到文件尾部）。"""
    path = workspace / "frontend" / "src" / "appDelivered.js"
    if not path.exists():
        return {}
    text = path.read_text(encoding="utf-8", errors="ignore")
    out: dict[str, Any] = {}
    fm = re.search(r'"flavor"\s*:\s*"([^"]*)"', text)
    if fm:
        out["flavor"] = fm.group(1)
    dm = re.search(r'"domainLabel"\s*:\s*"([^"]*)"', text)
    if dm:
        out["domainLabel"] = dm.group(1)
    tm = re.search(r'"traits"\s*:\s*(\{[^{}]*\})', text)
    if tm:
        blob = re.sub(r",\s*}", "}", tm.group(1))
        try:
            traits = json.loads(blob)
            if isinstance(traits, dict):
                out["traits"] = traits
        except json.JSONDecodeError:
            pass
    return out


# 仅当菜单挂载时才喂 QA 摘录（archive 壳仍可能磁盘保留这些 baseline 文件）
_QA_MENU_GATED_FILES: dict[str, frozenset[str]] = {
    "frontend/src/views/user/MyTickets.vue": frozenset({"my_tickets", "tickets"}),
}


def _qa_file_relevant(rel: str, menu_flat: set[str]) -> bool:
    need = _QA_MENU_GATED_FILES.get(rel)
    if not need:
        return True
    return bool(need & menu_flat)


def _collect_qa_context(workspace: Path, spec: dict[str, Any]) -> dict[str, Any]:
    """只采集上下文，不做领域词硬编码判定。"""
    schema = spec.get("schema") if isinstance(spec.get("schema"), dict) else {}
    menus = schema.get("menus") or {}
    menu_keys = _menu_keys(menus)
    menu_flat = {k for keys in menu_keys.values() for k in keys}

    files: dict[str, Any] = {}
    missing: list[str] = []
    for rel in _QA_FILES:
        if not _qa_file_relevant(rel, menu_flat):
            continue
        path = workspace / rel
        if not path.exists():
            missing.append(rel)
            continue
        files[rel] = _read_clip(path)

    entities_raw = schema.get("entities") if isinstance(schema.get("entities"), dict) else {}
    entities = {
        k: {
            "label": (v or {}).get("label"),
            "labelPlural": (v or {}).get("labelPlural"),
            "verbs": (v or {}).get("verbs"),
            "states": (v or {}).get("states"),
        }
        for k, v in entities_raw.items()
        if isinstance(v, dict)
    }
    skin = _delivered_skin(workspace)
    traits = skin.get("traits") if isinstance(skin.get("traits"), dict) else {}
    if not traits and isinstance(spec.get("traits"), dict):
        traits = dict(spec["traits"])

    # 种子公告在 SQL 里（不进 schema）：留给话术层第四条判据（公告与实体口径一致性）
    seed_parts: list[str] = []
    sql_dir = workspace / "sql"
    if sql_dir.is_dir():
        for path in sorted(sql_dir.glob("*.sql")):
            try:
                seed_parts.append(path.read_text(encoding="utf-8", errors="ignore"))
            except OSError:
                continue
    seed_sql = "\n".join(seed_parts)[:400_000]

    return {
        "schema": schema,
        "domain": spec.get("domain"),
        "title": spec.get("title"),
        "accept": spec.get("accept"),
        "out_of_mvp": list(spec.get("out_of_mvp") or []),
        "proposal": _proposal_text(spec)[:1500],
        "labels": schema.get("labels") or {},
        "seeds": schema.get("seeds") or {},
        "menus": menus,
        "menuKeys": menu_keys,
        "entities": entities,
        "entityKeys": sorted(entities.keys()),
        "capabilities": list(schema.get("capabilities") or []),
        "staffPackMenus": schema.get("staffPackMenus") or {},
        "staffPackPages": schema.get("staffPackPages") or {},
        "traits": traits,
        "flavor": skin.get("flavor") or "",
        "domainLabel": skin.get("domainLabel") or "",
        "missing_files": missing,
        "files": files,
        "seed_sql": seed_sql,
    }


def _flatten_label_text(ctx: dict[str, Any]) -> str:
    parts: list[str] = []
    labels = ctx.get("labels") or {}
    if isinstance(labels, dict):
        for v in labels.values():
            if isinstance(v, str):
                parts.append(v)
            elif isinstance(v, list):
                parts.extend(str(x) for x in v)
    menus = ctx.get("menus") or {}
    if isinstance(menus, dict):
        for items in menus.values():
            if not isinstance(items, list):
                continue
            for m in items:
                if isinstance(m, dict):
                    parts.append(str(m.get("label") or ""))
    parts.append(str(ctx.get("domainLabel") or ""))
    parts.append(str(ctx.get("proposal") or "")[:800])
    return "\n".join(parts)


def _honesty_hard_boundary_hit(blob: str, match: re.Match[str]) -> bool:
    """硬边界词 + 同窗宣称搭配，且无划界/前缀否定 → 才视为「写成已支持」。"""
    # 宣称窗收紧；划界窗略宽（开题 out_scope / 研究现状）
    claim_win = blob[max(0, match.start() - 32) : min(len(blob), match.end() + 32)]
    scope_win = blob[max(0, match.start() - 100) : min(len(blob), match.end() + 100)]
    before = blob[max(0, match.start() - 24) : match.start()]
    if _HONEST_SCOPE.search(scope_win):
        return False
    if _PREFIX_NEGATION.search(before):
        return False
    return bool(_CLAIM_AS_SUPPORTED.search(claim_win))


def _honesty_findings(ctx: dict[str, Any]) -> list[dict[str, str]]:
    """Q-04：硬边界不得写成已支持；错域实体名本地可拦。

    本地不穷举域措辞、也不替代 LLM：只拦「硬边界种子 ∩ 宣称搭配」的强信号；
    词单独出现或否定/划界句（如「非 CA…第三方电子签平台」）不升 error。
    """
    findings: list[dict[str, str]] = []
    blob = _flatten_label_text(ctx)
    for rx, name in _HARD_BOUNDARY_AS_SUPPORTED:
        for m in rx.finditer(blob):
            if not _honesty_hard_boundary_hit(blob, m):
                continue
            near = blob[max(0, m.start() - 24) : min(len(blob), m.end() + 24)].strip()
            findings.append(
                {
                    "level": "error",
                    "msg": (
                        f"交付文案将硬边界「{name}」写成本期可用"
                        f"（命中：{m.group(0)} · 附近：{near[:72]}）"
                    ),
                    "where": "schema.labels|proposal",
                }
            )
            break

    domain = str(ctx.get("domain") or "")
    forbidden = _WRONG_DOMAIN_ENTITY.get(domain) or ()
    for term in forbidden:
        if term and term in blob:
            # 仅当像主叙事：出现在 labels/菜单短文，且无「≠/不是/非」划界
            idx = blob.find(term)
            window = blob[max(0, idx - 12) : idx + len(term) + 12]
            if re.search(r"(≠|不是|非|勿|禁止|易混)", window):
                continue
            findings.append(
                {
                    "level": "warn",
                    "msg": f"疑似错域实体词「{term}」出现在 {domain} 交付文案",
                    "where": "schema.labels|menus",
                }
            )

    accept = str(ctx.get("accept") or "")
    if accept in ("reject", "partial") or ctx.get("out_of_mvp"):
        # 本地只拦强宣称；细节交给 LLM QA（若开启）
        if re.search(r"(已支持|可全文答辩|已完整实现).{0,8}(人脸|微信支付|法大大|RFID)", blob):
            findings.append(
                {
                    "level": "error",
                    "msg": "accept/缺口未就绪却宣称硬边界能力已支持",
                    "where": "spec.accept",
                }
            )
    return findings


# 支付渠道口口径：无余额/模拟/不对接划界却点名支付宝/微信 → 结构闸 error（关 LLM QA 也挡包）
_PAY_CHANNEL_IN_COPY = re.compile(r"支付宝|微信支付|微信\s*支付")
_PAY_HONEST_SCOPE = re.compile(
    r"余额|模拟|不对接|不接入|演示支付|系统内|账户扣款|扣减.{0,6}余额"
)
_PAY_CHANNEL_DENIED = re.compile(
    r"不(对接|接入|支持|开通).{0,12}(支付宝|微信)|非真支付|假的就行"
)


def _payment_copy_findings(ctx: dict[str, Any]) -> list[dict[str, str]]:
    """demoPayHint 等把支付宝/微信写成下单渠道且无诚实划界 → error。"""
    findings: list[dict[str, str]] = []
    labels = ctx.get("labels") if isinstance(ctx.get("labels"), dict) else {}
    caps = {str(c) for c in (ctx.get("capabilities") or []) if c}
    # 真支付能力岛若将来挂上可放行；现网无第三方渠道 cap
    if caps & {"wechat_pay", "alipay", "third_party_pay"}:
        return findings
    for key, val in labels.items():
        if not isinstance(val, str) or not val.strip():
            continue
        if not _PAY_CHANNEL_IN_COPY.search(val):
            continue
        if _PAY_HONEST_SCOPE.search(val) or _PAY_CHANNEL_DENIED.search(val):
            continue
        findings.append(
            {
                "level": "error",
                "msg": (
                    f"labels.{key} 将支付宝/微信写成本期支付能力，"
                    "但未见余额/模拟/不对接划界（capabilities 亦无真支付渠道）"
                ),
                "where": f"schema.labels.{key}",
            }
        )
    return findings


# 多店：管理员订单页不得写商家发货/物流职责（与 proposal 角色树对齐）
_MERCHANT_OPS_IN_ADMIN_ORDER = re.compile(r"发货|物流")
# 多店须知不得再写单店「管理员确认发货」（扫成多店后仍沿用单店 notice）
_ADMIN_SHIP_IN_MARKETPLACE_NOTICE = re.compile(r"管理员确认发货|由管理员确认发货")
# 点餐：主管订单页不得写档口/店员一线接单出餐（与 _food_tree 对齐）
_FOOD_STALL_OPS_IN_ADMIN_ORDER = re.compile(r"接单|出餐|发餐")


def _marketplace_role_copy_findings(ctx: dict[str, Any]) -> list[dict[str, str]]:
    """shopMarketplace：admin 订单 lead 与单店 notice 串台 → error（关 LLM 也挡）。"""
    findings: list[dict[str, str]] = []
    schema = ctx.get("schema") if isinstance(ctx.get("schema"), dict) else {}
    if not schema.get("shopMarketplace"):
        return findings
    labels = ctx.get("labels") if isinstance(ctx.get("labels"), dict) else {}
    lead = str(labels.get("ordersAdminLead") or "").strip()
    if lead and _MERCHANT_OPS_IN_ADMIN_ORDER.search(lead):
        findings.append(
            {
                "level": "error",
                "msg": (
                    "labels.ordersAdminLead 写「"
                    f"{lead.rstrip('。')}」，"
                    "把商家运营职责放到管理员订单页；"
                    "与多店管理员仅做全平台订单与售后监督相冲突"
                ),
                "where": "schema.labels.ordersAdminLead",
            }
        )
    seeds = schema.get("seeds") if isinstance(schema.get("seeds"), dict) else {}
    notice_body = str(seeds.get("noticeBody") or "").strip()
    if notice_body and _ADMIN_SHIP_IN_MARKETPLACE_NOTICE.search(notice_body):
        findings.append(
            {
                "level": "error",
                "msg": (
                    "多店 schema.seeds.noticeBody 写「"
                    f"{notice_body.rstrip('。')}」，"
                    "仍是单店「管理员确认发货」口径；"
                    "与多店商家发货、平台监督角色树相冲突"
                ),
                "where": "schema.seeds.noticeBody",
            }
        )
    return findings


def _food_role_copy_findings(ctx: dict[str, Any]) -> list[dict[str, str]]:
    """DOM-FOOD 时 ordersAdminLead 若写接单/出餐/发餐 → error（关 LLM 也挡）。"""
    findings: list[dict[str, str]] = []
    if str(ctx.get("domain") or "") != "DOM-FOOD":
        return findings
    labels = ctx.get("labels") if isinstance(ctx.get("labels"), dict) else {}
    lead = str(labels.get("ordersAdminLead") or "").strip()
    if not lead or not _FOOD_STALL_OPS_IN_ADMIN_ORDER.search(lead):
        return findings
    findings.append(
        {
            "level": "error",
            "msg": (
                "labels.ordersAdminLead 写「"
                f"{lead.rstrip('。')}」，"
                "把档口/店员接单出餐写到主管订单页；"
                "与食堂/门店主管仅做全场订单与退单监督相冲突"
            ),
            "where": "schema.labels.ordersAdminLead",
        }
    )
    return findings


# 订单评价：买家「星级评价」不得充当商家/办理员页导语
_ORDER_REVIEW_BUYER_COPY = re.compile(r"我的评价|星级与文字评价|对已完成订单进行")
_ORDER_REVIEW_CLERK_PACKS = frozenset({"merchant_ops", "order_ops", "slot_ops"})


def _order_review_role_copy_findings(ctx: dict[str, Any]) -> list[dict[str, str]]:
    """order_review + 商家/办理岗：须拆 Admin/Staff 评价页文案（关 LLM 也挡）。"""
    findings: list[dict[str, str]] = []
    caps = ctx.get("capabilities") or []
    if isinstance(caps, dict):
        cap_keys = set(caps.keys())
    else:
        cap_keys = {str(c) for c in (caps or [])}
    if "order_review" not in cap_keys:
        return findings

    schema = ctx.get("schema") if isinstance(ctx.get("schema"), dict) else {}
    roles = schema.get("roles") if isinstance(schema.get("roles"), dict) else {}
    posts = roles.get("staff_posts")
    if not isinstance(posts, list) or not posts:
        return findings
    has_review_clerk = False
    for p in posts:
        if not isinstance(p, dict):
            continue
        packs = {str(x) for x in (p.get("packs") or [])}
        if packs & _ORDER_REVIEW_CLERK_PACKS:
            has_review_clerk = True
            break
    if not has_review_clerk:
        return findings

    labels = ctx.get("labels") if isinstance(ctx.get("labels"), dict) else {}
    admin_lead = str(labels.get("orderReviewAdminPageLead") or "").strip()
    staff_lead = str(labels.get("orderReviewStaffPageLead") or "").strip()
    if not admin_lead:
        findings.append(
            {
                "level": "error",
                "msg": (
                    "已挂 order_review 且有商家/办理岗，却缺 labels.orderReviewAdminPageLead；"
                    "总管评价页不能共用买家「我的评价」口径"
                ),
                "where": "schema.labels.orderReviewAdminPageLead",
            }
        )
    elif _ORDER_REVIEW_BUYER_COPY.search(admin_lead):
        findings.append(
            {
                "level": "error",
                "msg": (
                    f"labels.orderReviewAdminPageLead 写「{admin_lead.rstrip('。')}」，"
                    "仍是买家评价口径；总管应是查看/删评监督"
                ),
                "where": "schema.labels.orderReviewAdminPageLead",
            }
        )
    if not staff_lead:
        findings.append(
            {
                "level": "error",
                "msg": (
                    "merchant_ops/order_ops 等含 order_reviews，却缺 labels.orderReviewStaffPageLead；"
                    "商家进入评价菜单会看到买家「星级评价」导语"
                ),
                "where": "schema.labels.orderReviewStaffPageLead",
            }
        )
    elif _ORDER_REVIEW_BUYER_COPY.search(staff_lead):
        findings.append(
            {
                "level": "error",
                "msg": (
                    f"labels.orderReviewStaffPageLead 写「{staff_lead.rstrip('。')}」，"
                    "仍是买家口径；商家应是查看并回复评价"
                ),
                "where": "schema.labels.orderReviewStaffPageLead",
            }
        )
    elif "回复" not in staff_lead:
        findings.append(
            {
                "level": "error",
                "msg": (
                    f"labels.orderReviewStaffPageLead 写「{staff_lead.rstrip('。')}」，"
                    "未写明回复评价；与开题商家端评价回复不符"
                ),
                "where": "schema.labels.orderReviewStaffPageLead",
            }
        )
    return findings


_NO_SHIP_FULFILL_MODES = frozenset({"stay", "rental", "cinema"})
_SHIP_OR_LOGISTICS = re.compile(r"发货|物流")


def _strip_no_ship_negation(text: str) -> str:
    return (
        str(text or "")
        .replace("无物流发货", "")
        .replace("无物流", "")
        .replace("无发货", "")
    )


def _reserve_fulfill_copy_findings(ctx: dict[str, Any]) -> list[dict[str, str]]:
    """stay/rental/cinema：履约句与主管 lead 不得串商城发货/物流（关 LLM 也挡）。"""
    findings: list[dict[str, str]] = []
    schema = ctx.get("schema") if isinstance(ctx.get("schema"), dict) else {}
    ents = schema.get("entities") if isinstance(schema.get("entities"), dict) else {}
    order = ents.get("order") if isinstance(ents.get("order"), dict) else {}
    mode = str(order.get("fulfillMode") or "")
    if mode not in _NO_SHIP_FULFILL_MODES:
        return findings
    verbs = order.get("verbs") if isinstance(order.get("verbs"), dict) else {}
    if str(verbs.get("ship") or "") == "发货":
        findings.append(
            {
                "level": "error",
                "msg": (
                    f"订单 fulfillMode={mode} 但 verbs.ship 仍是「发货」；"
                    "客房/租车/影院不得复用商城发货叙事"
                ),
                "where": "schema.entities.order.verbs.ship",
            }
        )
    labels = ctx.get("labels") if isinstance(ctx.get("labels"), dict) else {}
    for key in ("orderFulfillHint", "ordersAdminLead", "reservationsAdminLead"):
        raw = str(labels.get(key) or "").strip()
        if not raw:
            continue
        if _SHIP_OR_LOGISTICS.search(_strip_no_ship_negation(raw)):
            findings.append(
                {
                    "level": "error",
                    "msg": (
                        f"labels.{key} 写「{raw.rstrip('。')}」，"
                        f"在 fulfillMode={mode} 下仍含发货/物流叙事"
                    ),
                    "where": f"schema.labels.{key}",
                }
            )
    return findings


_BOOK_HOLD_LABEL_KEY = re.compile(r"^bookHold")
_LIBRARY_HOLD_COPY = re.compile(r"待取书|索书号|借阅额度")


def _borrow_role_copy_findings(ctx: dict[str, Any]) -> list[dict[str, str]]:
    """borrow 组：图书预约/取书不得串邻域；有岗位时须拆 Admin/Staff lead。"""
    from app.bake.domains import domain_group_of

    findings: list[dict[str, str]] = []
    domain = str(ctx.get("domain") or "")
    if domain_group_of(domain) != "borrow":
        return findings
    schema = ctx.get("schema") if isinstance(ctx.get("schema"), dict) else {}
    labels = ctx.get("labels") if isinstance(ctx.get("labels"), dict) else {}
    ents = schema.get("entities") if isinstance(schema.get("entities"), dict) else {}
    ticket = ents.get("ticket") if isinstance(ents.get("ticket"), dict) else {}
    states = ticket.get("states") if isinstance(ticket.get("states"), dict) else {}

    if domain != "DOM-LIBRARY":
        if ticket.get("allowBookHold") or "hold_ready" in states:
            findings.append(
                {
                    "level": "error",
                    "msg": (
                        f"{domain} 挂了图书预约/待取书状态；"
                        "取书预约仅 DOM-LIBRARY，禁止串到设备/驿站等借用邻域"
                    ),
                    "where": "schema.entities.ticket",
                }
            )
        for key, val in labels.items():
            sk = str(key)
            sv = str(val or "")
            if _BOOK_HOLD_LABEL_KEY.match(sk) or "待取书" in sv:
                findings.append(
                    {
                        "level": "error",
                        "msg": (
                            f"{domain} labels.{sk} 含图书取书预约文案；"
                            "与非图书借用域角色口径冲突"
                        ),
                        "where": f"schema.labels.{sk}",
                    }
                )
                break
        for key in ("ticketsAdminLead", "ticketsStaffLead", "messagesPageLead"):
            raw = str(labels.get(key) or "")
            if _LIBRARY_HOLD_COPY.search(raw):
                findings.append(
                    {
                        "level": "error",
                        "msg": (
                            f"{domain} labels.{key} 写「{raw.rstrip('。')}」，"
                            "串了图书取书/借阅额度口径"
                        ),
                        "where": f"schema.labels.{key}",
                    }
                )

    roles = schema.get("roles") if isinstance(schema.get("roles"), dict) else {}
    posts = roles.get("staff_posts")
    if isinstance(posts, list) and posts:
        if not str(labels.get("ticketsAdminLead") or "").strip():
            findings.append(
                {
                    "level": "error",
                    "msg": f"{domain} 有岗位表却缺 labels.ticketsAdminLead（总管单据页导语）",
                    "where": "schema.labels.ticketsAdminLead",
                }
            )
        if not str(labels.get("ticketsStaffLead") or "").strip():
            findings.append(
                {
                    "level": "error",
                    "msg": f"{domain} 有岗位表却缺 labels.ticketsStaffLead（一线单据页导语）",
                    "where": "schema.labels.ticketsStaffLead",
                }
            )
    return findings


# 报修/工单组禁止商城订单口吻
_REPAIR_SHOP_COPY = re.compile(r"发货|物流|购物车|商城|确认发货|下单支付")


def _ticket_role_copy_findings(ctx: dict[str, Any]) -> list[dict[str, str]]:
    """ticket 组：禁商城订单口吻；有岗位时须拆 Admin/Staff lead。"""
    from app.bake.domains import domain_group_of

    findings: list[dict[str, str]] = []
    domain = str(ctx.get("domain") or "")
    if domain_group_of(domain) != "ticket":
        return findings
    schema = ctx.get("schema") if isinstance(ctx.get("schema"), dict) else {}
    labels = ctx.get("labels") if isinstance(ctx.get("labels"), dict) else {}
    ents = schema.get("entities") if isinstance(schema.get("entities"), dict) else {}
    ticket = ents.get("ticket") if isinstance(ents.get("ticket"), dict) else {}

    for key in (
        "ticketsAdminLead",
        "ticketsStaffLead",
        "authLead",
        "messagesPageLead",
        "noticePageLead",
    ):
        raw = str(labels.get(key) or "").strip()
        if raw and _REPAIR_SHOP_COPY.search(raw):
            findings.append(
                {
                    "level": "error",
                    "msg": (
                        f"{domain} labels.{key} 写「{raw.rstrip('。')}」，"
                        "串了商城发货/购物车口吻；报修工单应是受理派单办结"
                    ),
                    "where": f"schema.labels.{key}",
                }
            )
    verbs = ticket.get("verbs") if isinstance(ticket.get("verbs"), dict) else {}
    for vk, vv in verbs.items():
        if _REPAIR_SHOP_COPY.search(str(vv or "")):
            findings.append(
                {
                    "level": "error",
                    "msg": (
                        f"{domain} ticket.verbs.{vk} 写「{str(vv).rstrip('。')}」，"
                        "串了商城订单口吻"
                    ),
                    "where": f"schema.entities.ticket.verbs.{vk}",
                }
            )
            break

    roles = schema.get("roles") if isinstance(schema.get("roles"), dict) else {}
    posts = roles.get("staff_posts")
    if isinstance(posts, list) and posts:
        if not str(labels.get("ticketsAdminLead") or "").strip():
            findings.append(
                {
                    "level": "error",
                    "msg": f"{domain} 有岗位表却缺 labels.ticketsAdminLead（总管工单页导语）",
                    "where": "schema.labels.ticketsAdminLead",
                }
            )
        if not str(labels.get("ticketsStaffLead") or "").strip():
            findings.append(
                {
                    "level": "error",
                    "msg": f"{domain} 有岗位表却缺 labels.ticketsStaffLead（一线工单页导语）",
                    "where": "schema.labels.ticketsStaffLead",
                }
            )
    return findings


# 跟进组：禁商城/借阅/报修一线串台
_FOLLOW_FOREIGN_COPY = re.compile(
    r"发货|物流|购物车|商城|待取书|索书号|借阅额度|确认发货"
)


def _follow_role_copy_findings(ctx: dict[str, Any]) -> list[dict[str, str]]:
    """follow 组：禁邻组口吻；有岗位时须拆 Admin/Staff lead。"""
    from app.bake.domains import domain_group_of

    findings: list[dict[str, str]] = []
    domain = str(ctx.get("domain") or "")
    if domain_group_of(domain) != "follow":
        return findings
    schema = ctx.get("schema") if isinstance(ctx.get("schema"), dict) else {}
    labels = ctx.get("labels") if isinstance(ctx.get("labels"), dict) else {}

    for key in (
        "ticketsAdminLead",
        "ticketsStaffLead",
        "authLead",
        "messagesPageLead",
        "noticePageLead",
    ):
        raw = str(labels.get(key) or "").strip()
        if raw and _FOLLOW_FOREIGN_COPY.search(raw):
            findings.append(
                {
                    "level": "error",
                    "msg": (
                        f"{domain} labels.{key} 写「{raw.rstrip('。')}」，"
                        "串了商城/借阅邻组口吻；跟进域应是审阅催办办结"
                    ),
                    "where": f"schema.labels.{key}",
                }
            )

    roles = schema.get("roles") if isinstance(schema.get("roles"), dict) else {}
    posts = roles.get("staff_posts")
    if isinstance(posts, list) and posts:
        if not str(labels.get("ticketsAdminLead") or "").strip():
            findings.append(
                {
                    "level": "error",
                    "msg": f"{domain} 有岗位表却缺 labels.ticketsAdminLead（总管跟进页导语）",
                    "where": "schema.labels.ticketsAdminLead",
                }
            )
        if not str(labels.get("ticketsStaffLead") or "").strip():
            findings.append(
                {
                    "level": "error",
                    "msg": f"{domain} 有岗位表却缺 labels.ticketsStaffLead（一线跟进页导语）",
                    "where": "schema.labels.ticketsStaffLead",
                }
            )
    return findings


# 审批组：禁商城/借阅/报修一线串台
_APPROVE_FOREIGN_COPY = re.compile(
    r"发货|物流|购物车|商城|待取书|索书号|借阅额度|确认发货"
)


def _approve_role_copy_findings(ctx: dict[str, Any]) -> list[dict[str, str]]:
    """approve 组：禁邻组口吻；有岗位时须拆 Admin/Staff lead。"""
    from app.bake.domains import domain_group_of

    findings: list[dict[str, str]] = []
    domain = str(ctx.get("domain") or "")
    if domain_group_of(domain) != "approve":
        return findings
    schema = ctx.get("schema") if isinstance(ctx.get("schema"), dict) else {}
    labels = ctx.get("labels") if isinstance(ctx.get("labels"), dict) else {}

    for key in (
        "ticketsAdminLead",
        "ticketsStaffLead",
        "authLead",
        "messagesPageLead",
        "noticePageLead",
    ):
        raw = str(labels.get(key) or "").strip()
        if raw and _APPROVE_FOREIGN_COPY.search(raw):
            findings.append(
                {
                    "level": "error",
                    "msg": (
                        f"{domain} labels.{key} 写「{raw.rstrip('。')}」，"
                        "串了商城/借阅邻组口吻；审批域应是材料审核与办结"
                    ),
                    "where": f"schema.labels.{key}",
                }
            )

    roles = schema.get("roles") if isinstance(schema.get("roles"), dict) else {}
    posts = roles.get("staff_posts")
    if isinstance(posts, list) and posts:
        if not str(labels.get("ticketsAdminLead") or "").strip():
            findings.append(
                {
                    "level": "error",
                    "msg": f"{domain} 有岗位表却缺 labels.ticketsAdminLead（总管审批页导语）",
                    "where": "schema.labels.ticketsAdminLead",
                }
            )
        if not str(labels.get("ticketsStaffLead") or "").strip():
            findings.append(
                {
                    "level": "error",
                    "msg": f"{domain} 有岗位表却缺 labels.ticketsStaffLead（承办岗审批页导语）",
                    "where": "schema.labels.ticketsStaffLead",
                }
            )
    return findings


# 报名组：禁商城/借阅/报修一线串台；报名态勿写成审批填报腔过重可另册
_APPLY_FOREIGN_COPY = re.compile(
    r"发货|物流|购物车|商城|待取书|索书号|借阅额度|确认发货"
)


def _apply_role_copy_findings(ctx: dict[str, Any]) -> list[dict[str, str]]:
    """apply 组：禁邻组口吻；有岗位时须拆 Admin/Staff lead。"""
    from app.bake.domains import domain_group_of

    findings: list[dict[str, str]] = []
    domain = str(ctx.get("domain") or "")
    if domain_group_of(domain) != "apply":
        return findings
    schema = ctx.get("schema") if isinstance(ctx.get("schema"), dict) else {}
    labels = ctx.get("labels") if isinstance(ctx.get("labels"), dict) else {}

    for key in (
        "ticketsAdminLead",
        "ticketsStaffLead",
        "authLead",
        "messagesPageLead",
        "noticePageLead",
    ):
        raw = str(labels.get(key) or "").strip()
        if raw and _APPLY_FOREIGN_COPY.search(raw):
            findings.append(
                {
                    "level": "error",
                    "msg": (
                        f"{domain} labels.{key} 写「{raw.rstrip('。')}」，"
                        "串了商城/借阅邻组口吻；报名域应是名额审核与办结"
                    ),
                    "where": f"schema.labels.{key}",
                }
            )

    roles = schema.get("roles") if isinstance(schema.get("roles"), dict) else {}
    posts = roles.get("staff_posts")
    if isinstance(posts, list) and posts:
        if not str(labels.get("ticketsAdminLead") or "").strip():
            findings.append(
                {
                    "level": "error",
                    "msg": f"{domain} 有岗位表却缺 labels.ticketsAdminLead（总管报名页导语）",
                    "where": "schema.labels.ticketsAdminLead",
                }
            )
        if not str(labels.get("ticketsStaffLead") or "").strip():
            findings.append(
                {
                    "level": "error",
                    "msg": f"{domain} 有岗位表却缺 labels.ticketsStaffLead（助理报名页导语）",
                    "where": "schema.labels.ticketsStaffLead",
                }
            )
    return findings


# 内容组：禁商城/借阅/报名一线串台；审核下架勿写成发货履约
_CONTENT_FOREIGN_COPY = re.compile(
    r"发货|物流|购物车|商城|待取书|索书号|借阅额度|确认发货|报名名额|差旅报销"
)


def _content_role_copy_findings(ctx: dict[str, Any]) -> list[dict[str, str]]:
    """content 组：禁邻组口吻；有岗位时须拆 Admin/Staff lead。"""
    from app.bake.domains import domain_group_of

    findings: list[dict[str, str]] = []
    domain = str(ctx.get("domain") or "")
    if domain_group_of(domain) != "content":
        return findings
    schema = ctx.get("schema") if isinstance(ctx.get("schema"), dict) else {}
    labels = ctx.get("labels") if isinstance(ctx.get("labels"), dict) else {}

    for key in (
        "ticketsAdminLead",
        "ticketsStaffLead",
        "authLead",
        "messagesPageLead",
        "noticePageLead",
        "myArchivePageLead",
        "contentReportsPageLead",
    ):
        raw = str(labels.get(key) or "").strip()
        if raw and _CONTENT_FOREIGN_COPY.search(raw):
            findings.append(
                {
                    "level": "error",
                    "msg": (
                        f"{domain} labels.{key} 写「{raw.rstrip('。')}」，"
                        "串了商城/借阅/报名邻组口吻；内容域应是审核下架与整理"
                    ),
                    "where": f"schema.labels.{key}",
                }
            )

    roles = schema.get("roles") if isinstance(schema.get("roles"), dict) else {}
    posts = roles.get("staff_posts")
    if isinstance(posts, list) and posts:
        if not str(labels.get("ticketsAdminLead") or "").strip():
            findings.append(
                {
                    "level": "error",
                    "msg": f"{domain} 有岗位表却缺 labels.ticketsAdminLead（站长内容页导语）",
                    "where": "schema.labels.ticketsAdminLead",
                }
            )
        if not str(labels.get("ticketsStaffLead") or "").strip():
            findings.append(
                {
                    "level": "error",
                    "msg": f"{domain} 有岗位表却缺 labels.ticketsStaffLead（版主/运营页导语）",
                    "where": "schema.labels.ticketsStaffLead",
                }
            )
    return findings


# 互动组：禁商城/借阅/报名履约串台；牵线互选勿写成发货
_INTERACT_FOREIGN_COPY = re.compile(
    r"发货|物流|购物车|商城|待取书|索书号|借阅额度|确认发货|报名名额|差旅报销"
)


def _interact_role_copy_findings(ctx: dict[str, Any]) -> list[dict[str, str]]:
    """interact 组：禁邻组口吻；有岗位时须拆 Admin/Staff lead。"""
    from app.bake.domains import domain_group_of

    findings: list[dict[str, str]] = []
    domain = str(ctx.get("domain") or "")
    if domain_group_of(domain) != "interact":
        return findings
    schema = ctx.get("schema") if isinstance(ctx.get("schema"), dict) else {}
    labels = ctx.get("labels") if isinstance(ctx.get("labels"), dict) else {}

    for key in (
        "ticketsAdminLead",
        "ticketsStaffLead",
        "authLead",
        "messagesPageLead",
        "noticePageLead",
        "peerInboxLead",
        "myTicketsPageLead",
    ):
        raw = str(labels.get(key) or "").strip()
        if raw and _INTERACT_FOREIGN_COPY.search(raw):
            findings.append(
                {
                    "level": "error",
                    "msg": (
                        f"{domain} labels.{key} 写「{raw.rstrip('。')}」，"
                        "串了商城/借阅/报名邻组口吻；互动域应是牵线、互选、对接或核销"
                    ),
                    "where": f"schema.labels.{key}",
                }
            )

    roles = schema.get("roles") if isinstance(schema.get("roles"), dict) else {}
    posts = roles.get("staff_posts")
    if isinstance(posts, list) and posts:
        if not str(labels.get("ticketsAdminLead") or "").strip():
            findings.append(
                {
                    "level": "error",
                    "msg": f"{domain} 有岗位表却缺 labels.ticketsAdminLead（总管互动页导语）",
                    "where": "schema.labels.ticketsAdminLead",
                }
            )
        if not str(labels.get("ticketsStaffLead") or "").strip():
            findings.append(
                {
                    "level": "error",
                    "msg": f"{domain} 有岗位表却缺 labels.ticketsStaffLead（一线互动页导语）",
                    "where": "schema.labels.ticketsStaffLead",
                }
            )
    return findings


# 兜底 GENERIC：禁行业专名串进 lead；禁总管/公告「管理员确认发货」
_FALLBACK_FOREIGN_COPY = re.compile(
    r"借阅额度|待取书|索书号|楼管|报修派单|报名名额|差旅报销|版主下架"
)
_FALLBACK_ADMIN_SHIP = re.compile(r"管理员确认发货|管理员.*(?:发货|物流)")


def _fallback_role_copy_findings(ctx: dict[str, Any]) -> list[dict[str, str]]:
    """fallback 组：禁行业串台与总管发货；有岗位时按实体路径拆 lead。"""
    from app.bake.domains import domain_group_of

    findings: list[dict[str, str]] = []
    domain = str(ctx.get("domain") or "")
    if domain_group_of(domain) != "fallback":
        return findings
    schema = ctx.get("schema") if isinstance(ctx.get("schema"), dict) else {}
    labels = ctx.get("labels") if isinstance(ctx.get("labels"), dict) else {}
    seeds = schema.get("seeds") if isinstance(schema.get("seeds"), dict) else {}
    ents = schema.get("entities") if isinstance(schema.get("entities"), dict) else {}

    for key in (
        "ticketsAdminLead",
        "ticketsStaffLead",
        "ordersAdminLead",
        "ordersStaffLead",
        "reservationsAdminLead",
        "reservationsStaffLead",
        "authLead",
        "messagesPageLead",
        "noticePageLead",
    ):
        raw = str(labels.get(key) or "").strip()
        if raw and _FALLBACK_FOREIGN_COPY.search(raw):
            findings.append(
                {
                    "level": "error",
                    "msg": (
                        f"{domain} labels.{key} 写「{raw.rstrip('。')}」，"
                        "串了具名行业口吻；兜底壳应保持通用办理口径"
                    ),
                    "where": f"schema.labels.{key}",
                }
            )

    for blob, where in (
        (str(labels.get("ordersAdminLead") or ""), "schema.labels.ordersAdminLead"),
        (str(labels.get("noticePageLead") or ""), "schema.labels.noticePageLead"),
        (str(seeds.get("noticeBody") or ""), "schema.seeds.noticeBody"),
    ):
        if blob and _FALLBACK_ADMIN_SHIP.search(blob):
            findings.append(
                {
                    "level": "error",
                    "msg": (
                        f"{domain} {where} 把发货写给管理员；"
                        "总管只监督，履约归办理员"
                    ),
                    "where": where,
                }
            )

    roles = schema.get("roles") if isinstance(schema.get("roles"), dict) else {}
    posts = roles.get("staff_posts")
    if not (isinstance(posts, list) and posts):
        return findings

    if "ticket" in ents:
        if not str(labels.get("ticketsAdminLead") or "").strip():
            findings.append(
                {
                    "level": "error",
                    "msg": f"{domain} 有岗位表却缺 labels.ticketsAdminLead（总管申请页导语）",
                    "where": "schema.labels.ticketsAdminLead",
                }
            )
        if not str(labels.get("ticketsStaffLead") or "").strip():
            findings.append(
                {
                    "level": "error",
                    "msg": f"{domain} 有岗位表却缺 labels.ticketsStaffLead（审核员申请页导语）",
                    "where": "schema.labels.ticketsStaffLead",
                }
            )
    if "order" in ents:
        if not str(labels.get("ordersAdminLead") or "").strip():
            findings.append(
                {
                    "level": "error",
                    "msg": f"{domain} 有岗位表却缺 labels.ordersAdminLead（总管订单页导语）",
                    "where": "schema.labels.ordersAdminLead",
                }
            )
        if not str(labels.get("ordersStaffLead") or "").strip():
            findings.append(
                {
                    "level": "error",
                    "msg": f"{domain} 有岗位表却缺 labels.ordersStaffLead（办理员订单页导语）",
                    "where": "schema.labels.ordersStaffLead",
                }
            )
    if "reservation" in ents:
        if not str(labels.get("reservationsAdminLead") or "").strip():
            findings.append(
                {
                    "level": "error",
                    "msg": f"{domain} 有岗位表却缺 labels.reservationsAdminLead（总管预约页导语）",
                    "where": "schema.labels.reservationsAdminLead",
                }
            )
        if not str(labels.get("reservationsStaffLead") or "").strip():
            findings.append(
                {
                    "level": "error",
                    "msg": f"{domain} 有岗位表却缺 labels.reservationsStaffLead（办理员预约页导语）",
                    "where": "schema.labels.reservationsStaffLead",
                }
            )
    return findings


def _structural_findings(ctx: dict[str, Any]) -> list[dict[str, str]]:
    """本地确定性检查（不依赖 LLM）。"""
    findings: list[dict[str, str]] = []
    for rel in ctx.get("missing_files") or []:
        findings.append({"level": "warn", "msg": f"缺失文件 {rel}", "where": rel})
    labels = ctx.get("labels") or {}
    if not labels.get("noticePageTitle"):
        findings.append({"level": "warn", "msg": "labels.noticePageTitle 缺失", "where": "schema.labels"})
    if not labels.get("appName"):
        findings.append({"level": "warn", "msg": "labels.appName 缺失", "where": "schema.labels"})

    menu_keys = ctx.get("menuKeys") or {}
    admin_keys = set(menu_keys.get("admin") or [])
    entity_keys = set(ctx.get("entityKeys") or [])
    if "category" in admin_keys and "category" not in entity_keys:
        findings.append(
            {
                "level": "warn",
                "msg": "admin 菜单有 category，但 entities 缺少 category 字典实体",
                "where": "schema.entities",
            }
        )

    notice = (ctx.get("files") or {}).get("frontend/src/views/NoticeDetail.vue") or ""
    if ">公告正文<" in notice or "公告正文</h2>" in notice:
        findings.append(
            {
                "level": "warn",
                "msg": "公告详情页写死文案「公告正文」",
                "where": "frontend/src/views/NoticeDetail.vue",
            }
        )
    findings.extend(_payment_copy_findings(ctx))
    findings.extend(_marketplace_role_copy_findings(ctx))
    findings.extend(_food_role_copy_findings(ctx))
    findings.extend(_order_review_role_copy_findings(ctx))
    findings.extend(_reserve_fulfill_copy_findings(ctx))
    findings.extend(_borrow_role_copy_findings(ctx))
    findings.extend(_ticket_role_copy_findings(ctx))
    findings.extend(_follow_role_copy_findings(ctx))
    findings.extend(_approve_role_copy_findings(ctx))
    findings.extend(_apply_role_copy_findings(ctx))
    findings.extend(_content_role_copy_findings(ctx))
    findings.extend(_interact_role_copy_findings(ctx))
    findings.extend(_fallback_role_copy_findings(ctx))
    findings.extend(_honesty_findings(ctx))
    findings.extend(_lexicon_findings(ctx))
    return findings


def _lexicon_findings(ctx: dict[str, Any]) -> list[dict[str, str]]:
    """C 批 error 级：跨域专属名词 / 同 slot 口径分叉 / 域外字段缺 allow* 分支。"""
    schema = ctx.get("schema")
    if not isinstance(schema, dict) or not schema:
        return []
    from app.bake.domain_vocab import lexicon_findings

    return lexicon_findings(
        schema,
        domain=str(ctx.get("domain") or ""),
        files=ctx.get("files") or {},
        title=str(ctx.get("title") or ""),
        seed_sql=str(ctx.get("seed_sql") or ""),
    )


def _fallback_qa(ctx: dict[str, Any]) -> dict[str, Any]:
    """无 Key / 关 QA 时的结构回退（不写死领域错词表）。

    仅对强信号 error 挡包；弱措辞不做穷举、也不假装 LLM 已审。
    """
    findings = _structural_findings(ctx)
    errors = [f for f in findings if f.get("level") == "error"]
    summary = "未启用 LLM QA，仅做结构回退检查"
    if errors:
        summary = f"{summary} · {str(errors[0].get('msg') or '')[:120]}"
    elif findings:
        summary = f"{summary} · {len(findings)} 条非挡包发现"
    return {
        "summary": summary,
        "findings": findings,
        "ok": not errors,
        "mode": "fallback",
    }


def _normalize_findings(raw: Any) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    if not isinstance(raw, list):
        return out
    for item in raw[:24]:
        if isinstance(item, str):
            out.append({"level": "warn", "msg": item[:200], "where": ""})
            continue
        if not isinstance(item, dict):
            continue
        level = str(item.get("level") or "warn").lower()
        if level not in ("error", "warn", "info"):
            level = "warn"
        out.append(
            {
                "level": level,
                "msg": str(item.get("msg") or item.get("message") or "")[:200],
                "where": str(item.get("where") or item.get("file") or "")[:120],
            }
        )
    return [f for f in out if f["msg"]]


def _switch_hides_absent_states(msg: str, ctx: dict[str, Any], where: str = "") -> bool:
    """状态不在实体 states 里，且摘录中只出现在 allow* / hasCap 分支 → 开关未开，不是错域。"""
    if not re.search(r"残留|错域|写死|未定义", msg or ""):
        return False
    known: set[str] = set()
    for ent in (ctx.get("entities") or {}).values():
        if isinstance(ent, dict) and isinstance(ent.get("states"), dict):
            known.update(str(k) for k in ent["states"])
    cited = set(re.findall(r"\b([a-z][a-z0-9]*_[a-z0-9_]+)\b", msg or ""))
    absent = {tok for tok in cited if tok not in known}
    if not absent:
        return False
    files = ctx.get("files") or {}
    chunks: list[str] = []
    for rel, body in files.items():
        if not isinstance(body, str) or not body:
            continue
        if (where and (rel in where or where.endswith(rel) or rel.endswith(where))) or any(
            tok in body for tok in absent
        ):
            chunks.append(body)
    if not chunks:
        return False
    lines = "\n".join(chunks).splitlines()
    checked = False
    for tok in absent:
        hits = [i for i, line in enumerate(lines) if tok in line]
        if not hits:
            continue
        checked = True
        for i in hits:
            window = "\n".join(lines[max(0, i - 6) : i + 1])
            if not re.search(r"\ballow[A-Z][A-Za-z0-9]*\b|hasCap\s*\(", window):
                return False
    return checked


def _is_noise_finding(msg: str, ctx: dict[str, Any], *, where: str = "") -> bool:
    """滤掉与结构化真相矛盾的 LLM 臆造（全厂规则，不绑单一域）。"""
    text = msg or ""
    loc = f"{text}\n{where or ''}"
    entity_keys = set(ctx.get("entityKeys") or [])
    menu_flat = {k for keys in (ctx.get("menuKeys") or {}).values() for k in keys}
    pack_menus = ctx.get("staffPackMenus") or {}
    pack_flat = {k for keys in pack_menus.values() for k in (keys or [])}
    traits = ctx.get("traits") or {}

    # 结构化里根本没有 reservation，却报「未使用的 reservation 实体」
    if re.search(r"\breservations?\b", text, re.I):
        if (
            "reservation" not in entity_keys
            and "reservations" not in menu_flat
            and "reservations" not in pack_flat
            and "my_reservations" not in menu_flat
        ):
            if re.search(r"未使用|多余|无关|残留|不该|未定义", text):
                return True

    # 已有 category 实体仍报未定义（只认英文 key，避免误伤正文「分类」文案问题）
    if "category" in entity_keys and re.search(r"\bcategory\b", text, re.I):
        if re.search(r"未定义|缺少|缺失|没有", text):
            return True

    # followUp/crm 是 UI 特征，不是行业名；结构化已开则勿报「与领域无关」
    if traits.get("followUp") or traits.get("crm"):
        if re.search(r"traits\.(crm|followUp)|crm\s*:\s*true|followUp\s*:\s*true", text, re.I):
            if re.search(r"无关|不符|错域|不该|不应", text):
                return True
        if re.search(r"特征标记.*crm|系统特征.*crm", text, re.I) and re.search(
            r"无关|不符|错域", text
        ):
            return True

    # 未挂菜单的票务/购物骨架页：baseline 残留文案不挡 archive 等壳
    # where 常带路径而 msg 只写「文件内…」，须合并判断
    if re.search(r"MyTickets\.vue|my_tickets", loc, re.I):
        if "my_tickets" not in menu_flat and "tickets" not in menu_flat:
            return True
    if re.search(r"Cart\.vue|(?<![\w.])/cart\b|\bcart\b", loc, re.I) and "cart" not in menu_flat:
        if re.search(r"残留|错域|未路由|未挂|不该|工厂|不对接", loc):
            return True
    if re.search(r"MyOrders\.vue|my_orders", loc, re.I) and "orders" not in menu_flat:
        if re.search(r"残留|错域|未路由|未挂|不该|工厂|不对接", loc):
            return True

    # 详情页已用动态正文小标题
    notice = (ctx.get("files") or {}).get("frontend/src/views/NoticeDetail.vue") or ""
    if "公告正文" in text and ("bodyHeading" in notice or ">公告正文<" not in notice):
        return True

    # 订单评价：买家键本就是「我的评价」；商家看 Staff/Admin 键。已拆则 LLM 勿再报不匹配
    if re.search(
        r"orderReviewPage(Title|Lead)|我的评价|星级与文字评价|评价回复|评价管理",
        text,
    ):
        labels = ctx.get("labels") if isinstance(ctx.get("labels"), dict) else {}
        staff_lead = str(labels.get("orderReviewStaffPageLead") or "").strip()
        admin_lead = str(labels.get("orderReviewAdminPageLead") or "").strip()
        if (
            staff_lead
            and admin_lead
            and "回复" in staff_lead
            and not _ORDER_REVIEW_BUYER_COPY.search(staff_lead)
            and not _ORDER_REVIEW_BUYER_COPY.search(admin_lead)
            and re.search(
                r"买家口径|不匹配|建议按角色|只有买家|商家进入|补充商家",
                text,
            )
        ):
            return True

    if _switch_hides_absent_states(text, ctx, where):
        return True

    # 纯润色/体验建议（无硬伤用词）→ 噪声
    if re.search(r"建议(?:优化|改进|润色|补充)|可以考虑|不妨|宜增加|优化体验|措辞更好", text):
        if not _PROGRAM_IMPACT_RE.search(text):
            return True

    # 说不清影响哪条运行/演示路径的闲话
    if not _PROGRAM_IMPACT_RE.search(text):
        if re.search(
            r"建议|宜|不妨|可以|更好|润色|贴切|专业|语气|观感|可读性|一致性更好",
            text,
        ):
            return True

    return False


def _llm_finding_affects_program(msg: str) -> bool:
    """LLM 的 warn/error 必须能对上「影响程序/演示」信号。"""
    return bool(_PROGRAM_IMPACT_RE.search(msg or ""))


def _filter_findings(findings: list[dict[str, str]], ctx: dict[str, Any]) -> list[dict[str, str]]:
    kept: list[dict[str, str]] = []
    for f in findings:
        level = str(f.get("level") or "")
        msg = str(f.get("msg") or "")
        where = str(f.get("where") or "")
        if level == "info":
            kept.append(f)
            continue
        if _is_noise_finding(msg, ctx, where=where):
            continue
        # 只约束 LLM 侧：无程序影响信号的 warn/error 丢掉（不挡包）
        if level in ("warn", "error") and not _llm_finding_affects_program(msg):
            continue
        kept.append(f)
    return kept


def _merge_findings(*groups: list[dict[str, str]]) -> list[dict[str, str]]:
    seen: set[str] = set()
    out: list[dict[str, str]] = []
    for group in groups:
        for f in group:
            key = f"{f.get('level')}|{f.get('where')}|{f.get('msg')}"
            if key in seen:
                continue
            seen.add(key)
            out.append(f)
    return out


async def run_qa_agent(
    db: AsyncSession,
    rt: LlmRuntime,
    *,
    project_id: str,
    workspace: Path,
    spec: dict[str, Any],
) -> dict[str, Any]:
    ctx = _collect_qa_context(workspace, spec)
    use_llm = rt.stage_on("qa_report") and rt.configured and await budget_ok(db, project_id, rt)

    if not use_llm:
        report = _fallback_qa(ctx)
        await record_call(
            db,
            project_id=project_id,
            stage="qa_report",
            tokens=0,
            ok=True,
            detail="回退：仅结构扫描（未调用大模型）",
        )
        write_qa_report(
            workspace, {**report, "domain": ctx.get("domain"), "title": ctx.get("title")}
        )
        return report

    payload = {
        "domain": ctx["domain"],
        "title": ctx["title"],
        "flavor": ctx.get("flavor"),
        "domainLabel": ctx.get("domainLabel"),
        "traits": ctx.get("traits") or {},
        "capabilities": ctx.get("capabilities") or [],
        "accept": ctx["accept"],
        "proposal": ctx["proposal"],
        "labels": ctx["labels"],
        "seeds": ctx["seeds"],
        "menuKeys": ctx.get("menuKeys") or {},
        "entityKeys": ctx.get("entityKeys") or [],
        "entities": ctx["entities"],
        "staffPackMenus": ctx.get("staffPackMenus") or {},
        "staffPackPages": ctx.get("staffPackPages") or {},
        "missing_files": ctx["missing_files"],
        "file_excerpts": ctx["files"],
    }
    messages = [
        {"role": "system", "content": _SYS},
        {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
    ]
    res = await chat(
        rt, messages, json_mode=True, temperature=temperature_for("qa_report"), timeout=120.0
    )
    append_deepseek_log(project_id, f"qa ok={res.ok} {format_usage_detail(res)}")

    if not res.ok or not res.data:
        report = _fallback_qa(ctx)
        report["summary"] = f"LLM QA 失败，回退结构检查 · {res.error or 'no json'}"
        report["mode"] = "fallback_after_llm_error"
        await record_call(
            db,
            project_id=project_id,
            stage="qa_report",
            tokens=res.tokens,
            ok=False,
            detail=format_usage_detail(res, "质量摘要：大模型失败"),
        )
        write_qa_report(
            workspace, {**report, "domain": ctx.get("domain"), "title": ctx.get("title")}
        )
        return report

    data = res.data
    llm_findings = _normalize_findings(data.get("findings"))
    for p in data.get("priorities") or []:
        llm_findings.append({"level": "info", "msg": str(p)[:200], "where": "priority"})
    llm_findings = _filter_findings(llm_findings, ctx)
    findings = _merge_findings(_structural_findings(ctx), llm_findings)

    # ok 以过滤后的 error 为准，避免模型对 warn 也打 ok=False
    ok = not any(f.get("level") == "error" for f in findings)
    summary = str(data.get("summary") or "").strip()
    warn_n = len([f for f in findings if f.get("level") in ("error", "warn")])
    if not summary:
        summary = (
            f"LLM QA 完成 · {warn_n} 条发现" if warn_n else "LLM QA 未发现明显问题"
        )
    elif ok and warn_n == 0:
        # 模型摘要可能仍写着旧误报；过滤后无问题则改写
        if re.search(
            r"不一致|写死|无关|未使用|未定义|残留|不建议|需修正|MyTickets|错域",
            summary,
        ):
            summary = "LLM QA 未发现明显问题"
    report = {
        "domain": ctx.get("domain"),
        "title": ctx.get("title"),
        "summary": summary[:800],
        "findings": findings,
        "ok": ok,
        "mode": "llm",
    }
    await record_call(
        db,
        project_id=project_id,
        stage="qa_report",
        tokens=res.tokens,
        ok=True,
        detail=format_usage_detail(res, summary[:400]),
    )
    write_qa_report(workspace, report)
    return report
