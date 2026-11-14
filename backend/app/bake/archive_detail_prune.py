"""档案独立详情 ArchiveItemDetail：按能力主脸剪学生包页内死分支。

骨架保留全脸；出包后学生源码不得残留异域 CTA/须知话术。
主脸优先级与页面一致：order_lines > slot_reserve > ticket_flow > content。
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

DETAIL_REL = "views/user/ArchiveItemDetail.vue"

Face = str  # order | slot | ticket | content

# 各脸「不得残留」：中文话术 + 标识符（主脸自身不进本集合）
_POISON: dict[Face, tuple[str, ...]] = {
    "order": (
        "立即借阅",
        "申请床位",
        "申请取件",
        "申请借用",
        "预约带看",
        "记录跟进",
        "立即报名",
        "提交意向",
        "申请办理",
        "借阅说明",
        "取件说明",
        "床位说明",
        "借用说明",
        "跟进说明",
        "报名说明",
        "意向说明",
        "办理说明",
        "选择时段",
        "预约说明",
        "阅读说明",
        "我的借阅",
        "我的预约",
        "我的报名",
        "床位安排",
        "slotOn",
        "ticketOn",
        "contentOn",
        "goSlots",
        "goTicketApply",
        "slotCtaLabel",
        "ticketApplyLabel",
        "borrowSurface",
        "applySurfaceOn",
        "interactSurfaceOn",
        "followSurfaceOn",
        "borrowSurfaceOn",
        "aid-content",
    ),
    "slot": (
        "立即借阅",
        "申请床位",
        "申请取件",
        "申请借用",
        "预约带看",
        "记录跟进",
        "立即报名",
        "提交意向",
        "申请办理",
        "借阅说明",
        "取件说明",
        "床位说明",
        "借用说明",
        "跟进说明",
        "报名说明",
        "意向说明",
        "办理说明",
        "购买须知",
        "我的订单",
        "加入购物车",
        "阅读说明",
        "我的借阅",
        "我的报名",
        "床位安排",
        "orderOn",
        "ticketOn",
        "contentOn",
        "buyNow",
        "goTicketApply",
        "ticketApplyLabel",
        "borrowSurface",
        "applySurfaceOn",
        "interactSurfaceOn",
        "followSurfaceOn",
        "borrowSurfaceOn",
        "upsertCart",
        "aid-qty",
        "aid-content",
    ),
    "ticket": (
        "选择时段",
        "预约说明",
        "我的预约",
        "购买须知",
        "我的订单",
        "加入购物车",
        "阅读说明",
        "orderOn",
        "slotOn",
        "contentOn",
        "buyNow",
        "goSlots",
        "slotCtaLabel",
        "upsertCart",
        "aid-qty",
        "aid-content",
    ),
    "content": (
        "立即借阅",
        "申请床位",
        "申请取件",
        "申请借用",
        "预约带看",
        "记录跟进",
        "立即报名",
        "提交意向",
        "申请办理",
        "借阅说明",
        "取件说明",
        "床位说明",
        "借用说明",
        "跟进说明",
        "报名说明",
        "意向说明",
        "办理说明",
        "选择时段",
        "预约说明",
        "购买须知",
        "我的订单",
        "加入购物车",
        "我的借阅",
        "我的预约",
        "我的报名",
        "床位安排",
        "orderOn",
        "slotOn",
        "ticketOn",
        "buyNow",
        "goSlots",
        "goTicketApply",
        "slotCtaLabel",
        "ticketApplyLabel",
        "borrowSurface",
        "applySurfaceOn",
        "interactSurfaceOn",
        "followSurfaceOn",
        "borrowSurfaceOn",
        "upsertCart",
        "aid-qty",
    ),
}

_KEEP: dict[Face, tuple[str, ...]] = {
    "order": ("orderOn", "buyNow", "购买须知", "aid-buybox"),
    "slot": ("slotOn", "goSlots", "slotCtaLabel", "预约说明"),
    "ticket": ("ticketOn", "goTicketApply", "ticketApplyLabel"),
    "content": ("contentOn", "阅读说明", "aid-content"),
}


def resolve_archive_detail_face(caps: set[str] | list[str] | None) -> Face:
    c = {str(x).strip() for x in (caps or []) if str(x).strip()}
    if "order_lines" in c:
        return "order"
    if "slot_reserve" in c:
        return "slot"
    if "ticket_flow" in c:
        return "ticket"
    return "content"


def forbidden_archive_detail_markers(face: Face) -> tuple[str, ...]:
    return _POISON.get(face, _POISON["content"])


def required_archive_detail_markers(face: Face) -> tuple[str, ...]:
    return _KEEP.get(face, _KEEP["content"])


def scan_archive_detail_face_leaks(
    text: str, face: Face
) -> list[str]:
    """返回仍残留在详情源码里的异域标记。"""
    if not text:
        return []
    hits: list[str] = []
    for m in forbidden_archive_detail_markers(face):
        if m in text:
            hits.append(m)
    return hits


def _cut_el_button_by_pred(text: str, pred: str) -> str:
    """删掉带给定 v-if / v-else-if 谓词的 el-button 整块（含多行）。"""
    # self-closing unlikely; match opening tag through </el-button>
    pat = re.compile(
        rf"[ \t]*<el-button\b[^>]*(?:v-if|v-else-if)=\"{re.escape(pred)}\"[^>]*>[\s\S]*?</el-button>\s*",
        re.M,
    )
    return pat.sub("", text)


def _cut_div_vif(text: str, pred: str) -> str:
    pat = re.compile(
        rf"[ \t]*<div\b[^>]*v-if=\"{re.escape(pred)}\"[^>]*>[\s\S]*?</div>\s*",
        re.M,
    )
    return pat.sub("", text)


def _replace_between(text: str, start: str, end: str, repl: str) -> str:
    """替换 start 首次出现到 end 首次出现（不含 end）之间的内容。"""
    i = text.find(start)
    if i < 0:
        return text
    j = text.find(end, i + len(start))
    if j < 0:
        return text
    return text[:i] + repl + text[j:]


def _remove_const_block(text: str, name: str) -> str:
    """删除 `const name = ...` 到下一个顶层 const/function/watch/onMounted。"""
    m = re.search(rf"(?m)^const {re.escape(name)} = ", text)
    if not m:
        return text
    start = m.start()
    rest = text[m.end() :]
    # 找到下一个同级声明
    nxt = re.search(
        r"(?m)^(?:const |function |async function |watch\(|onMounted\()",
        rest,
    )
    if not nxt:
        return text[:start] + rest
    return text[:start] + rest[nxt.start() :]


def _remove_function(text: str, name: str) -> str:
    m = re.search(rf"(?m)^(?:async )?function {re.escape(name)}\s*\(", text)
    if not m:
        return text
    start = m.start()
    brace = text.find("{", m.end() - 1)
    if brace < 0:
        return text
    depth = 0
    i = brace
    while i < len(text):
        ch = text[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                end = i + 1
                while end < len(text) and text[end] in "\r\n":
                    end += 1
                return text[:start] + text[end:]
        i += 1
    return text


def _scrub_api_imports(text: str, *, need_cart: bool) -> str:
    if need_cart:
        return text
    text = re.sub(
        r"import \{([^}]+)\} from '../../utils/apiCalls'",
        lambda m: "import {"
        + ",".join(
            p
            for p in (x.strip() for x in m.group(1).split(","))
            if p and p != "upsertCart"
        )
        + "} from '../../utils/apiCalls'",
        text,
        count=1,
    )
    # 清理可能的多余空格/空 import
    text = re.sub(
        r"import \{\s*\} from '../../utils/apiCalls'\s*\n",
        "",
        text,
    )
    return text


def _face_glue_order() -> str:
    return """const orderOn = computed(() => hasCap('order_lines'))
const favOn = computed(() => hasCap('favorites'))
const reviewOn = computed(() => hasCap('order_review'))
const priceOn = computed(() => orderOn.value || authorLooksLikePrice.value)
const introTab = computed(() => '详细介绍')
const entityLabel = computed(() => {
  const e = getSchema()?.entities?.archive
  return e?.label || labels.archiveItemLabel || ''
})
const priceLabel = computed(() => {
  const f = (archiveCopy().fields || []).find((x) => x?.key === 'author')
  return f?.label || '价格'
})
const showPriceLabel = computed(() => {
  if (orderOn.value) return false
  const lab = String(priceLabel.value || '').trim()
  if (!lab) return false
  if (/单价|价格|售价/.test(lab) && lab.length <= 8) return false
  return true
})
const buyLabel = computed(() => labels.buyNowLabel || '加入购物车')
const noticeTab = computed(() => '购买须知')
const noticeText = computed(
  () =>
    labels.archiveBuyNotice
    || '下单后可在「我的订单」查看进度。',
)

"""


def _face_glue_slot() -> str:
    return """const slotOn = computed(() => hasCap('slot_reserve'))
const favOn = computed(() => hasCap('favorites'))
const reviewOn = computed(() => hasCap('order_review'))
const priceOn = computed(() => authorLooksLikePrice.value)
const introTab = computed(() => '详细介绍')
const slotCtaLabel = computed(() => {
  const verb = getSchema()?.entities?.reservation?.verbs?.apply || '预约'
  return labels.slotBookLabel || `选择时段${verb}`
})
const entityLabel = computed(() => {
  const e = getSchema()?.entities?.archive
  return e?.label || labels.archiveItemLabel || ''
})
const priceLabel = computed(() => {
  const f = (archiveCopy().fields || []).find((x) => x?.key === 'author')
  return f?.label || '价格'
})
const showPriceLabel = computed(() => {
  const lab = String(priceLabel.value || '').trim()
  if (!lab) return false
  if (/单价|价格|售价/.test(lab) && lab.length <= 8) return false
  return true
})
const noticeTab = computed(() => '预约说明')
const noticeText = computed(
  () =>
    labels.archiveBuyNotice
    || '选定时段后可在「我的预约」查看进度；约满时段不可再约。',
)

"""


def _face_glue_ticket() -> str:
    return """const ticketOn = computed(() => hasCap('ticket_flow'))
const applySurfaceOn = computed(() => !!String(APP_DELIVERED?.applySurfaceStyle || '').trim())
const interactSurfaceOn = computed(() => !!String(APP_DELIVERED?.interactSurfaceStyle || '').trim())
const followSurfaceOn = computed(() => !!String(APP_DELIVERED?.followSurfaceStyle || '').trim())
const borrowSurfaceOn = computed(() => !!String(APP_DELIVERED?.borrowSurfaceStyle || '').trim())
const borrowSurface = computed(() => String(APP_DELIVERED?.borrowSurfaceStyle || '').trim())
const favOn = computed(() => hasCap('favorites'))
const reviewOn = computed(() => hasCap('order_review'))
const priceOn = computed(() => authorLooksLikePrice.value)
const introTab = computed(() => '详细介绍')
const ticketApplyLabel = computed(() => {
  if (borrowSurfaceOn.value) {
    if (borrowSurface.value === 'bookshelf') {
      return labels.applyLabel || labels.ticketApplyLabel || '立即借阅'
    }
    if (borrowSurface.value === 'bedblocks') {
      return labels.applyLabel || labels.ticketApplyLabel || '申请床位'
    }
    if (borrowSurface.value === 'parcelshelf') {
      return labels.applyLabel || labels.ticketApplyLabel || '申请取件'
    }
    return labels.applyLabel || labels.ticketApplyLabel || '申请借用'
  }
  if (followSurfaceOn.value) {
    if (String(APP_DELIVERED?.followSurfaceStyle || '') === 'listing') {
      return labels.applyLabel || '预约带看'
    }
    return labels.applyLabel || '记录跟进'
  }
  if (applySurfaceOn.value) {
    return labels.applyLabel || labels.ticketApplyLabel || '立即报名'
  }
  if (interactSurfaceOn.value) {
    return labels.applyLabel || labels.ticketApplyLabel || '提交意向'
  }
  return labels.ticketApplyLabel || labels.applyLabel || '申请办理'
})
const entityLabel = computed(() => {
  const e = getSchema()?.entities?.archive
  return e?.label || labels.archiveItemLabel || ''
})
const priceLabel = computed(() => {
  const f = (archiveCopy().fields || []).find((x) => x?.key === 'author')
  return f?.label || '价格'
})
const showPriceLabel = computed(() => {
  const lab = String(priceLabel.value || '').trim()
  if (!lab) return false
  if (/单价|价格|售价/.test(lab) && lab.length <= 8) return false
  return true
})
const noticeTab = computed(() => {
  if (borrowSurfaceOn.value) {
    if (borrowSurface.value === 'bookshelf') return '借阅说明'
    if (borrowSurface.value === 'parcelshelf') return '取件说明'
    if (borrowSurface.value === 'bedblocks') return '床位说明'
    return '借用说明'
  }
  if (followSurfaceOn.value) return '跟进说明'
  if (applySurfaceOn.value) return '报名说明'
  if (interactSurfaceOn.value) return '意向说明'
  return '办理说明'
})
const noticeText = computed(
  () =>
    labels.archiveBuyNotice
    || (borrowSurfaceOn.value
      ? (borrowSurface.value === 'bookshelf'
        ? '提交后可在「我的借阅」查看进度与应还日期。'
        : borrowSurface.value === 'parcelshelf'
          ? '提交后可在「我的单据」查看取件进度。'
          : borrowSurface.value === 'bedblocks'
            ? '提交后可在「我的申请」查看床位安排。'
            : '提交后可在「我的借用」查看进度与归还说明。')
      : followSurfaceOn.value
        ? '可在本页查看跟进说明并提交下一步。'
        : applySurfaceOn.value
          ? '提交后可在「我的报名」查看进度；名额满时可能无法再报。'
          : interactSurfaceOn.value
            ? '提交后可在「我的记录」查看意向进度。'
            : ticketOn.value
              ? '提交申请后可在「我的单据」查看进度与续办说明。'
              : '请按页面说明了解办理要求。'),
)

"""


def _face_glue_content() -> str:
    return """const contentOn = computed(() => {
  const s = String(APP_DELIVERED?.contentSurfaceStyle || '').trim()
  return !!s || hasCap('content')
})
const favOn = computed(() => hasCap('favorites'))
const reviewOn = computed(() => hasCap('order_review'))
const priceOn = computed(() => authorLooksLikePrice.value)
const introTab = computed(() => (contentOn.value ? '正文' : '详细介绍'))
const entityLabel = computed(() => {
  const e = getSchema()?.entities?.archive
  return e?.label || labels.archiveItemLabel || ''
})
const priceLabel = computed(() => {
  const f = (archiveCopy().fields || []).find((x) => x?.key === 'author')
  return f?.label || '价格'
})
const showPriceLabel = computed(() => {
  const lab = String(priceLabel.value || '').trim()
  if (!lab) return false
  if (/单价|价格|售价/.test(lab) && lab.length <= 8) return false
  return true
})
const noticeTab = computed(() => '阅读说明')
const noticeText = computed(
  () =>
    labels.archiveBuyNotice
    || '可在本页阅读正文；收藏与足迹在个人中心查看。',
)

"""


def _meta_line_order_or_trade() -> str:
    return """const metaLine = computed(() => {
  if (!row.value) return ''
  const bits = []
  const stock = Number(row.value.stock)
  if (Number.isFinite(stock)) bits.push(`库存 ${stock}`)
  const sales = Number(row.value.salesCount ?? row.value.soldCount ?? row.value.sales)
  if (Number.isFinite(sales) && sales > 0) bits.push(`累计销量 ${sales}`)
  const cat = row.value.categoryName || (row.value.categoryNames || []).join(' · ')
  if (cat) bits.push(cat)
  return bits.join(' · ')
})
"""


def _meta_line_content() -> str:
    return """const metaLine = computed(() => {
  if (!row.value) return ''
  const bits = []
  const author = String(row.value.author || '').trim()
  if (author && !/^\\d+(\\.\\d+)?$/.test(author)) bits.push(author)
  const views = Number(row.value.viewCount)
  if (Number.isFinite(views) && views > 0) bits.push(`阅读 ${views}`)
  const cat = row.value.categoryName || (row.value.categoryNames || []).join(' · ')
  if (cat) bits.push(cat)
  return bits.join(' · ')
})
"""


def _detail_attrs(face: Face) -> str:
    guard = "if (!row.value) return []" if face == "content" else "if (!row.value) return []"
    # content face: still skip attrs when reading body-first; keep empty list for content
    if face == "content":
        return """const detailAttrLines = computed(() => {
  return []
})
"""
    return f"""const detailAttrLines = computed(() => {{
  {guard}
  const skip = new Set([
    'title', 'author', 'isbn', 'category', 'categoryIds', 'stock', 'coverUrl',
    'sellerNote', 'promoPrice', 'promoStart', 'promoEnd',
  ])
  const names = Array.isArray(row.value.categoryNames) && row.value.categoryNames.length
    ? row.value.categoryNames.map((x) => String(x || '').trim()).filter(Boolean)
    : (String(row.value.categoryName || '').trim() ? [String(row.value.categoryName).trim()] : [])
  const fields = archiveCopy().fields || []
  const lines = []
  for (const f of fields) {{
    if (!f?.key || skip.has(f.key)) continue
    if (f.type === 'hidden' || f.type === 'richtext') continue
    if (!shouldShowDetailAttr(row.value, f.key, names)) continue
    const text = formatArchiveScalar(f, row.value[f.key], '')
    if (!text || text === '—') continue
    lines.push({{ key: f.key, label: f.label || f.key, text }})
  }}
  return lines.slice(0, 8)
}})
"""


def _intro_html(face: Face) -> str:
    if face == "content":
        empty = "暂无正文"
    else:
        empty = "暂无详细介绍"
    return f"""const introHtml = computed(() => {{
  const raw = String(row.value?.sellerNote || row.value?.content || '').trim()
  if (!raw) return '<p>{empty}</p>'
  if (/<[a-z][\\s\\S]*>/i.test(raw)) return raw
  return `<p>${{raw.replace(/</g, '&lt;')}}</p>`
}})
"""


def _scrub_template(text: str, face: Face) -> str:
    if face == "content":
        text = text.replace(
            '<div class="aid" :class="{ \'aid-content\': contentOn }" v-loading="loading">',
            '<div class="aid aid-content" v-loading="loading">',
        )
    else:
        text = text.replace(
            '<div class="aid" :class="{ \'aid-content\': contentOn }" v-loading="loading">',
            '<div class="aid" v-loading="loading">',
        )

    if face == "order":
        text = _cut_el_button_by_pred(text, "slotOn")
        text = _cut_el_button_by_pred(text, "ticketOn")
        # order 按钮保留 v-if="orderOn"
    elif face == "slot":
        text = _cut_div_vif(text, "orderOn")
        text = _cut_el_button_by_pred(text, "orderOn")
        text = _cut_el_button_by_pred(text, "ticketOn")
        text = text.replace('v-else-if="slotOn"', 'v-if="slotOn"')
    elif face == "ticket":
        text = _cut_div_vif(text, "orderOn")
        text = _cut_el_button_by_pred(text, "orderOn")
        text = _cut_el_button_by_pred(text, "slotOn")
        text = text.replace('v-else-if="ticketOn"', 'v-if="ticketOn"')
    else:  # content
        text = _cut_div_vif(text, "orderOn")
        text = _cut_el_button_by_pred(text, "orderOn")
        text = _cut_el_button_by_pred(text, "slotOn")
        text = _cut_el_button_by_pred(text, "ticketOn")
    return text


def _scrub_style(text: str, face: Face) -> str:
    if face != "content":
        text = re.sub(
            r"/\* 内容阅读脸：[\s\S]*?\.aid-content \.aid-rich \{[\s\S]*?\}\n",
            "",
            text,
            count=1,
        )
    if face != "order":
        text = re.sub(
            r"\.aid-qty \{[\s\S]*?\.aid-qty span \{[\s\S]*?\}\n",
            "",
            text,
            count=1,
        )
    return text


def _scrub_script(text: str, face: Face) -> str:
    glue = {
        "order": _face_glue_order,
        "slot": _face_glue_slot,
        "ticket": _face_glue_ticket,
        "content": _face_glue_content,
    }[face]()

    # 替换从 orderOn 到 noticeText 结束（下一个 const authorLooksLikePrice）
    text = _replace_between(
        text,
        "const orderOn = computed",
        "const authorLooksLikePrice = computed",
        glue,
    )

    # metaLine
    meta = _meta_line_content() if face == "content" else _meta_line_order_or_trade()
    text = _replace_between(
        text,
        "const metaLine = computed",
        "const detailAttrLines = computed",
        meta,
    )
    # 若工厂注释挡在 detailAttrLines 前
    text = re.sub(
        r"/\*\* 详情属性：[\s\S]*?\*/\s*(?=const detailAttrLines)",
        "",
        text,
        count=1,
    )

    text = _replace_between(
        text,
        "const detailAttrLines = computed",
        "const introHtml = computed",
        _detail_attrs(face),
    )
    text = _replace_between(
        text,
        "const introHtml = computed",
        "function stripHtml",
        _intro_html(face),
    )

    if face != "ticket":
        text = _remove_function(text, "goTicketApply")
    if face != "slot":
        text = _remove_function(text, "goSlots")
    if face != "order":
        text = _remove_function(text, "buyNow")

    text = _scrub_api_imports(text, need_cart=(face == "order"))

    # content 脸不用 price 强依赖 order；保留 authorLooksLikePrice
    # ticket 脸仍用 APP_DELIVERED；其它脸若未引用可保留 import（无害）

    if face != "ticket":
        # 非 ticket 可不留 APP_DELIVERED，除非 content 还要用 contentSurfaceStyle
        if face == "content":
            pass
        else:
            text = re.sub(
                r"import \{ APP_DELIVERED \} from '../../appDelivered\.js'\s*\n",
                "",
                text,
                count=1,
            )

    if face == "content":
        # shouldShowDetailAttr 若 detailAttrLines 恒空仍可能被 tree；保留 import 无害
        # 去掉未用 shouldShowDetailAttr / formatArchiveScalar? detail empty 仍可能用 format in price
        pass

    return text


def scrub_archive_item_detail_vue(text: str, face: Face) -> str:
    """把全脸详情页改写成单一主脸；幂等。"""
    if not text or "aid-buybox" not in text:
        return text
    # 已剪过：根节点无 contentOn 绑定且缺异域 glue 时仍再跑一遍安全
    text = _scrub_template(text, face)
    text = _scrub_script(text, face)
    text = _scrub_style(text, face)
    # 压缩多余空行
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text


def prune_archive_item_detail_in_fe(
    fe_src: Path, caps: set[str] | list[str] | None
) -> str | None:
    """剪 frontend/src 下详情页；成功返回相对 fe 路径，否则 None。"""
    if not fe_src or not Path(fe_src).is_dir():
        return None
    path = Path(fe_src) / "views" / "user" / "ArchiveItemDetail.vue"
    if not path.is_file():
        return None
    face = resolve_archive_detail_face(caps)
    raw = path.read_text(encoding="utf-8")
    new = scrub_archive_item_detail_vue(raw, face)
    if new != raw:
        path.write_text(new, encoding="utf-8", newline="\n")
        return DETAIL_REL
    # 已是目标脸或无可写变更时：仍回报路径便于统计；泄漏由 scan 把关
    if scan_archive_detail_face_leaks(new, face):
        path.write_text(new, encoding="utf-8", newline="\n")
    return DETAIL_REL if path.is_file() else None


def scan_archive_detail_leaks_in_workspace(
    workspace: Path, spec: dict[str, Any] | None = None
) -> list[str]:
    """p3lean：详情页异域残留 → 路径:标记。"""
    ws = Path(workspace)
    fe = ws / "frontend" / "src"
    path = fe / "views" / "user" / "ArchiveItemDetail.vue"
    if not path.is_file():
        return []
    caps: set[str] = set()
    if isinstance(spec, dict):
        raw = spec.get("capabilities")
        if isinstance(raw, list):
            caps = {str(x).strip() for x in raw if str(x).strip()}
        else:
            sch = spec.get("schema") if isinstance(spec.get("schema"), dict) else {}
            raw2 = sch.get("capabilities") if isinstance(sch.get("capabilities"), list) else []
            caps = {str(x).strip() for x in raw2 if str(x).strip()}
    face = resolve_archive_detail_face(caps)
    text = path.read_text(encoding="utf-8")
    return [f"{DETAIL_REL}:{m}" for m in scan_archive_detail_face_leaks(text, face)]
