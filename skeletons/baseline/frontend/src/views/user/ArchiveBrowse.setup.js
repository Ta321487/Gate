import { computed, onMounted, onUnmounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import http from '../../api/http'
import GuestLoginHint from '../../components/GuestLoginHint.vue'
import EmptyHint from '../../components/EmptyHint.vue'
import RecommendStrip from '../../components/RecommendStrip.vue'
import StatusChip from '../../components/StatusChip.vue'
import RichTextEditor from '../../components/RichTextEditor.vue'
import RichTextView from '../../components/RichTextView.vue'
import MaterialChecklistFields from '../../components/MaterialChecklistFields.vue'
import SchemaLabelHints from '../../components/SchemaLabelHints.vue'
import CodeQrBlock from '../../components/CodeQrBlock.vue'
import { ARCHIVE_BROWSE_HINT_KEYS } from '../../utils/labelHintMount.js'
import { toggleFavorite, touchBrowseHistory, upsertCart } from '../../utils/apiCalls.js'
import {
  archiveCopy,
  archiveLogCopy,
  formatArchiveScalar,
  followChannelLabel,
  followChannelOptions,
  followChannelPlaceholder,
  hasTrait,
  hasCap,
  getSchema,
  isArchiveLogEnabled,
  isBrowseHistoryEnabled,
  isGalleryEnabled,
  isSearchAssistEnabled,
  menuLabel,
  nextFollowLabel,
  searchHotKeywords,
  ticketCopy,
  ticketCheckinLabel,
  ticketDueLabel,
  ticketFineLabel,
} from '../../utils/domainSchema.js'
import { plainFromHtml, sanitizeHtml } from '../../utils/richHtml.js'
import { profileRoomMatches, filterArchiveByOwnerToken, ownerTokenFromProfile } from '../../utils/profileRoomMatch.js'
import {
  formatCountdownClock,
  isUrgentCountdown,
  secondsUntil,
  useNowTick,
} from '../../utils/useCountdown.js'
import { equipmentMark } from '../../utils/equipmentMark.js'
import {
  guestTeaserLimit,
  isGuestBrowseEnabled,
  isLoggedIn,
  requireLogin,
} from '../../utils/session.js'
import { APP_DELIVERED } from '../../appDelivered.js'

const router = useRouter()
const route = useRoute()
const isGuest = computed(() => isGuestBrowseEnabled() && !isLoggedIn())
const archive = archiveCopy()
const ticket = ticketCopy()
const isCrm = computed(() => hasTrait('followUp') || hasTrait('crm'))
const channelLabel = computed(() => followChannelLabel())
const nextAtLabel = computed(() => nextFollowLabel())
const channelPlaceholder = computed(() => followChannelPlaceholder())
const channelOptions = computed(() => followChannelOptions())
const caps = computed(() => getSchema().capabilities || [])
const browseHintKeys = ARCHIVE_BROWSE_HINT_KEYS
const browseLabels = computed(() => getSchema()?.labels || {})
const shelfAnnounceHint = computed(() => browseLabels.value.shelfAnnounceHint || '')
const tagColorOn = computed(() => !!browseLabels.value.tagColorHint)
const intentCountHint = computed(() => browseLabels.value.intentCountHint || '')
const intentCountOn = computed(() => !!intentCountHint.value)
const quotaRemainHint = computed(() => browseLabels.value.quotaRemainHint || '')
const quotaRemainOn = computed(() => !!quotaRemainHint.value)

function tagColor(name) {
  const s = String(name || '')
  let h = 0
  for (let i = 0; i < s.length; i += 1) h = (h * 31 + s.charCodeAt(i)) >>> 0
  const hue = h % 360
  return `hsl(${hue} 55% 48%)`
}
function intentCountOf(row) {
  const v = row?.intentCount ?? row?.intent_count ?? row?.favCount
  return v == null || v === '' ? null : v
}
function skillTagsOf(row) {
  const raw = row?.skillTags || row?.skill_tags || ''
  return String(raw)
    .split(/[,，;；、\s]+/)
    .map((s) => s.trim())
    .filter(Boolean)
}

function tutorQuotaPercent(row) {
  if (!row) return null
  const cap = Number(row.quotaCap ?? row.quota_cap ?? 0)
  const stock = Number(row.stock ?? 0)
  if (!(cap > 0)) return null
  const used = Math.max(0, Math.min(cap, cap - stock))
  return Math.round((used / cap) * 100)
}

function tutorQuotaText(row) {
  const cap = Number(row?.quotaCap ?? row?.quota_cap ?? 0)
  const stock = Number(row?.stock ?? 0)
  if (!(cap > 0)) return ''
  const used = Math.max(0, cap - stock)
  return `${used}/${cap}`
}

/** 总费用 ÷ 座位数（余座+已占近似 = 初始 stock 不可得时用余座+1） */
function aaPerPerson(row) {
  if (!carpoolAaCalcOn.value || !row) return null
  const total = Number(row.fareTotalYuan ?? row.fare_total_yuan ?? 0)
  if (!(total > 0)) return null
  const remain = Number(row.stock ?? 0)
  const seats = Math.max(1, remain > 0 ? remain : 1)
  return (total / seats).toFixed(2)
}

function skillMatchCount(row) {
  if (!teamSkillMatchOn.value) return null
  const mine = String(mySkillTagsInput.value || '')
    .split(/[,，;；、\s]+/)
    .map((s) => s.trim().toLowerCase())
    .filter(Boolean)
  if (!mine.length) return null
  const theirs = skillTagsOf(row).map((s) => s.toLowerCase())
  if (!theirs.length) return 0
  return mine.filter((t) => theirs.includes(t)).length
}

function rowMatchesSkillFilter(row) {
  const q = String(skillTagFilter.value || '').trim().toLowerCase()
  if (!q) return true
  const tags = skillTagsOf(row).map((s) => s.toLowerCase())
  if (!tags.length) return false
  return q.split(/[,，;；、\s]+/).filter(Boolean).every((t) => tags.some((x) => x.includes(t)))
}

async function sendTeamInvite(row) {
  const { value } = await ElMessageBox.prompt(
    teamInviteHint.value || '请输入对方账号',
    teamInviteLabel.value,
    {
      confirmButtonText: '发送',
      cancelButtonText: '取消',
      inputPattern: /\S+/,
      inputErrorMessage: '请填写账号',
      inputValue: inviteToUsername.value,
    },
  )
  inviteToUsername.value = value
  await http.post('/api/tickets/team-invite', {
    toUsername: value,
    itemId: row.id,
    note: teamInviteBody.value || '',
  })
  ElMessage.success(
    (teamInviteTitle.value ? `${teamInviteTitle.value}：` : '')
      + (browseLabels.value.teamInviteDone || '邀请已发送'),
  )
}

function quotaRemainOf(row) {
  const v = row?.quotaRemain ?? row?.quota_remain ?? row?.remainQuota
  if (v != null && v !== '') return v
  if (row?.stock != null && row?.stock !== '') return row.stock
  return null
}
const purchaseGateOn = computed(() => caps.value.includes('purchase_gate'))
const blindBoxOn = computed(() => caps.value.includes('blind_box'))
const boxIds = ref(new Set())
const boxInfo = ref(new Map())
const prizeIds = ref(new Set())
function isBlindBox(row) {
  return boxIds.value.has(Number(row?.id))
}
function blindBoxLine(row) {
  const info = boxInfo.value.get(Number(row?.id))
  return info?.text || '付款后开盒，奖品以开出结果为准'
}
async function loadBlindBoxes() {
  if (!blindBoxOn.value) return
  try {
    const [boxes, prizes] = await Promise.all([
      http.get('/api/blind-boxes/boxes'),
      http.get('/api/blind-boxes/prizes'),
    ])
    const map = new Map()
    for (const x of boxes.data || []) map.set(Number(x.id), x)
    boxInfo.value = map
    boxIds.value = new Set(map.keys())
    prizeIds.value = new Set((prizes.data || []).map((x) => Number(x.id)))
  } catch {
    boxInfo.value = new Map()
    boxIds.value = new Set()
    prizeIds.value = new Set()
  }
}
const verbs = computed(() => ticket.verbs || {})
const plural = computed(() => archive.labelPlural || archive.label || '对象')
const fields = computed(() =>
  (archive.fields || []).filter(
    (f) => f && f.key !== 'adminNote' && !f.adminOnly,
  ),
)
const stockDisplay = computed(() => archive.stockDisplay || 'count')
const showStageChip = computed(() => {
  const fields = archive.fields || []
  return fields.some((f) => f && f.key === 'stage')
})

function stageTone(stage) {
  const s = String(stage || '').trim()
  if (!s) return 'muted'
  if (/空闲|在库|待取|开放报名|^开放$|可/.test(s)) return 'free'
  if (/已分配|借出|已取出|已预约|满员|已满|已认领/.test(s)) return 'taken'
  if (/维修|损坏|误领|拒收|下架|逾期|停开/.test(s)) return 'warn'
  return 'muted'
}
const playUrlField = computed(() => archive.playUrlField || '')
const bodyRich = computed(() => {
  const f = fields.value.find((x) => x.key === 'isbn')
  return f?.type === 'richtext' || archive.bodyField === 'isbn'
})
const richRemark = computed(() => !!ticket.richRemark)
const autoApprove = computed(() => !!ticket.autoApprove)
const requireAttach = computed(() => !!ticket.requireAttach)
const requireMaterial = computed(
  () => !!ticket.requireMaterialChecklist || hasCap('material_check'),
)
const matRef = ref(null)
const requireRemark = computed(() => !!ticket.requireRemark)
const remarkLabel = computed(() => ticket.remarkLabel || '说明')
const dueLabel = computed(() => ticketDueLabel('到期日'))
const fineLabel = computed(() => ticketFineLabel('金额'))
const pickLoanPeriod = computed(() => !!ticket.pickLoanPeriod)
/** 报销等：有 fineLabel 且非借阅到期/SLA 时，提交表单收金额 */
const collectAmount = computed(
  () => !!ticket.fineLabel && !pickLoanPeriod.value && !ticket.slaDeadline,
)
const pickDateRange = computed(() => !!ticket.pickDateRange)
const allowQty = computed(() => !!ticket.allowQty)
const qtyLabel = computed(() => ticket.qtyLabel || '数量')
const ratingDims = computed(() => {
  const list = ticket.ratingDims
  return Array.isArray(list) ? list.filter((d) => d && d.key && d.label) : []
})
const allowAnonymousRating = computed(() => !!ticket.allowAnonymousRating)
const rateOnApply = computed(
  () => !!autoApprove.value && !!ticket.allowRating && ratingDims.value.length > 0,
)
const checkinOnApply = computed(() => !!autoApprove.value && !!ticket.allowCheckin)
const checkinLabel = computed(() => ticketCheckinLabel('签到'))
const matchProfileRoom = computed(() => !!ticket.matchProfileRoom)
const matchProfileOpts = computed(() => ({
  buildingKey: ticket.matchProfileBuildingKey || 'dormBuilding',
  roomKey: ticket.matchProfileRoomKey || 'dormRoom',
  buildingField: ticket.matchProfileBuildingField || 'author',
  roomField: ticket.matchProfileRoomField || 'title',
  looseBuilding: !!ticket.matchProfileLooseBuilding,
}))
const matchProfileNeedMessage = computed(
  () => ticket.matchProfileNeedMessage || '请先在个人资料填写楼栋与房间',
)
const matchProfileDenyMessage = computed(
  () => ticket.matchProfileDenyMessage || '只能对本寝室的查寝场次登记归寝',
)
const filterByOwnerToken = computed(() => !!ticket.filterByOwnerToken)
const ownerTokenSource = computed(() => ticket.ownerTokenSource || 'phone')
const ownerTokenStrict = computed(() => !!ticket.ownerTokenStrict)
const needApplyDialog = computed(
  () =>
    richRemark.value
    || requireAttach.value
    || requireMaterial.value
    || requireRemark.value
    || pickLoanPeriod.value
    || pickDateRange.value
    || collectAmount.value
    || allowQty.value
    || isCrm.value
    || rateOnApply.value
    || checkinOnApply.value,
)
const checkMutex = computed(() => !!ticket.checkMutex)
const categoryLimit = computed(() => Number(ticket.categoryLimit) || 0)
const tagFilter = computed(() => !!archive.tagFilter)
const multiCategory = computed(() => !!archive.multiCategory || hasCap('multi_category'))
const userPublish = computed(() => !!archive.userPublish)
/** 论坛类：isbn 富文本；CRM/拼车等：纯文本业务表单 */
const publishUsesRichBody = computed(() => bodyRich.value)
/** 联系人等可填；「发布人/作者」由登录账号自动写入 */
const publishShowAuthor = computed(() => {
  if (!userPublish.value || publishUsesRichBody.value) return false
  const lab = fieldLabel('author', '')
  if (/发布人|作者|发帖/.test(lab)) return false
  return true
})
const publishShowStock = computed(
  () => userPublish.value && !publishUsesRichBody.value && stockDisplay.value === 'number',
)
const publishShowStartAt = computed(
  () => userPublish.value && !publishUsesRichBody.value && hasSchedule.value,
)
const publishDialogTitle = computed(() => {
  const custom = getSchema()?.labels?.publishDialogTitle
  if (custom) return custom
  if (publishUsesRichBody.value) return '发帖'
  if (publishShowStock.value) return `发布${archive.label || '行程'}`
  return `登记${archive.label || '内容'}`
})
const publishCtaLabel = computed(() => {
  const custom = getSchema()?.labels?.publishCtaLabel
  if (custom) return custom
  if (publishUsesRichBody.value) return '发帖'
  if (publishShowStock.value) return `发布${archive.label || '行程'}`
  return `登记${archive.label || '内容'}`
})
const publishSubmitLabel = computed(() => {
  const custom = getSchema()?.labels?.publishSubmitLabel
  if (custom) return custom
  if (publishUsesRichBody.value) return '发布'
  if (publishShowStock.value) return '发布'
  return '保存'
})
const publishTitlePlaceholder = computed(() => `请填写${fieldLabel('title', '名称')}`)
const publishIsbnPlaceholder = computed(() => {
  const lab = fieldLabel('isbn', '备注')
  if (lab.includes('时间') || lab.includes('地点')) return '例如：周五 18:30 学校东门出发，可带行李'
  if (lab.includes('电话') || lab.includes('备注')) return '电话、微信或跟进备注'
  return `请填写${lab}`
})
const publishTip = computed(() => {
  const custom = getSchema()?.labels?.publishTip
  if (custom) return custom
  if (publishUsesRichBody.value) return '发布后即时可见，无需审核；违规可由管理员下架。'
  if (publishShowStock.value) return '行程发布后即时可见；他人提交意向后由你确认或婉拒。'
  return `登记后即时入档，可在「我的${archive.label || '内容'}」中查看；随后可提交跟进。`
})
const stockCountLabel = computed(() => {
  if (archive.stockCountLabel) return archive.stockCountLabel
  const stockField = fields.value.find((x) => x.key === 'stock')
  if (stockField?.label) return stockField.label
  return '余量'
})

/** 卡片/详情副文案：schema 里除标题作者分类外的短字段（地点、阶段、编号等） */
const cardDetailFields = computed(() => {
  const skip = new Set([
    'title', 'author', 'category', 'stock', 'coverUrl',
    'mutexCode', 'checkinCode', 'startAt', 'endAt', 'applyDeadlineAt',
  ])
  // 挂 product_spec 时规格进短签，避免与 schema 字段重复堆行
  if (productSpecOn.value) {
    const src = getSchema()?.entities?.archive?.productSpecSource || 'specNote'
    skip.add(src === 'isbn' ? 'isbn' : 'specNote')
  }
  return fields.value.filter((f) => {
    if (!f?.key || skip.has(f.key)) return false
    if (f.type === 'hidden' || f.type === 'richtext') return false
    // 正文/播放链路由摘要或播放按钮承担，避免卡片再堆一长串 URL
    if (f.key === 'isbn' && (bodyRich.value || playUrlField.value === 'isbn')) return false
    const t = f.type || 'string'
    return ['string', 'number', 'datetime', 'date', 'url', 'textarea', 'select'].includes(t)
  })
})
/** §2.5 叙事脸：catalog 多参数 / story 少短签 / board 几乎不堆字段 */
const cardVoice = computed(() => {
  const v = String(APP_DELIVERED?.cardVoice || 'catalog').toLowerCase()
  return v === 'story' || v === 'board' ? v : 'catalog'
})
const cardPreviewFields = computed(() => {
  // §2.5：catalog 至多 2 短签；story 2 句料；board 不堆
  const n = cardVoice.value === 'story' ? 2 : cardVoice.value === 'board' ? 0 : 2
  return cardDetailFields.value.slice(0, n)
})
const cardMoreFieldCount = computed(() => {
  if (cardVoice.value !== 'catalog') return 0
  return Math.max(0, cardDetailFields.value.length - cardPreviewFields.value.length)
})

/** catalog 短签：值优先芯片，禁止十行「标签：值」同灰（§2.5 至多 2） */
function cardShortTags(row) {
  if (!row || cardVoice.value !== 'catalog') return []
  const out = []
  const budget = 2
  if (productSpecOn.value) {
    const spec = productSpecText(row)
    if (spec) {
      const lab = String(productSpecLabel.value || '').trim()
      const text = lab && lab.length <= 4 ? `${lab} ${spec}` : spec
      out.push({
        key: 'productSpec',
        text: text.length > 18 ? `${text.slice(0, 18)}…` : text,
      })
    }
  }
  for (const f of cardPreviewFields.value) {
    if (out.length >= budget) break
    const v = formatFieldValue(row, f)
    if (!v || v === '—') continue
    const lab = String(f.label || '').trim()
    const raw = lab && lab.length <= 4 ? `${lab} ${v}` : v
    out.push({
      key: f.key,
      text: raw.length > 18 ? `${raw.slice(0, 18)}…` : raw,
    })
  }
  return out.slice(0, budget)
}

function storyLeadOf(row) {
  if (!row) return ''
  const raw = row.excerpt || row.summary || row.lead || row.bodyPlain || ''
  const s = String(raw).replace(/<[^>]+>/g, '').trim()
  if (s) return s.length > 72 ? `${s.slice(0, 72)}…` : s
  const bits = cardDetailFields.value
    .slice(0, 2)
    .map((f) => formatFieldValue(row, f))
    .filter((x) => x && x !== '—')
  return bits.length ? bits.join(' · ') : ''
}

function categoryTextOf(row) {
  if (!row) return ''
  if (row.categoryNames?.length) return row.categoryNames.join(' · ')
  return String(row.categoryName || '').trim()
}

/** 主信号：价/作者/分类择一突出，禁止「作者 · 未分类」灰墙同构 */
function primarySignalOf(row) {
  if (!row) return ''
  /* 预约三档主信号各异：号源看有号、房态看可订、车型看日价 */
  if (reserveSurface.value === 'roomstate') {
    const t = reserveRoomTone(row)
    if (t === 'busy') return '已满'
    if (t === 'hold') return '紧张'
    if (t === 'free') return '可订'
  }
  if (reserveSurface.value === 'slotstrip') {
    if (!stockOk(row)) return '约满'
    const n = Number(row.stock)
    if (stockTight(row) && Number.isFinite(n)) return `余号紧张 · ${n}`
    if (Number.isFinite(n)) return `有号 · 余 ${n}`
    return '有号可约'
  }
  if (reserveSurface.value === 'vehiclecard' && authorFieldIsMoney.value) {
    const n = Number(row.author)
    if (Number.isFinite(n)) return `¥${n.toFixed(2)}/天`
    const raw = formatAuthor(row.author)
    return raw && raw !== '—' ? `${raw}/天` : ''
  }
  /* 内容：刊头/清单看作者·阅读；封面墙极简分类；双栏留给右侧 pane */
  if (contentSurface.value === 'folio' || contentSurface.value === 'ledger') {
    const bits = []
    const author = formatAuthor(row.author)
    if (author && author !== '—') bits.push(author)
    const views = Number(row.viewCount)
    if (Number.isFinite(views) && (viewCountOn.value || views > 0)) {
      bits.push(`${viewCountLabel.value} ${views}`)
    }
    if (bits.length) return bits.join(' · ')
    return categoryTextOf(row) || ''
  }
  if (coverWallActive.value) {
    return categoryTextOf(row) || ''
  }
  /* 报名四档：海报看余位、课表看时段、启事看类型、线路看出团/余位 */
  if (applySurface.value === 'eventposter') {
    if (!stockOk(row)) return '名额已满'
    const n = Number(row.stock)
    if (stockTight(row) && Number.isFinite(n)) return `名额紧张 · 余 ${n}`
    if (quotaRemainOn.value && quotaRemainOf(row) != null) {
      const q = Number(quotaRemainOf(row))
      if (Number.isFinite(q)) return q <= 0 ? '名额已满' : `余位 ${q}`
    }
    if (Number.isFinite(n)) return `余位 ${n}`
    return '报名进行中'
  }
  if (applySurface.value === 'coursetable') {
    const sched = scheduleText(row)
    if (sched) return sched
    const n = Number(row.stock)
    if (Number.isFinite(n)) return n <= 0 ? '已满' : `余量 ${n}`
    return categoryTextOf(row) || ''
  }
  if (applySurface.value === 'noticeboard') {
    const kind = String(row.lostCategory || row.categoryName || '').trim()
    if (kind) return kind
    return categoryTextOf(row) || '启事'
  }
  if (applySurface.value === 'tourcard') {
    const bits = []
    if (authorFieldIsMoney.value) {
      const n = Number(row.author)
      if (Number.isFinite(n)) bits.push(`¥${n.toFixed(0)}起`)
    }
    const n = Number(row.stock)
    if (Number.isFinite(n)) bits.push(n <= 0 ? '满员' : `余位 ${n}`)
    const days = String(row.durationDays || row.days || row.tourDays || '').trim()
    if (days) bits.push(`${days}日`)
    if (bits.length) return bits.join(' · ')
    return categoryTextOf(row) || ''
  }
  /* 互动三档：资料看城市·简介；双选看名额；行程看时刻·路线·余座 */
  if (interactSurface.value === 'profilegrid') {
    const bits = []
    const city = String(row.city || row.region || row.campus || '').trim()
    if (city) bits.push(city)
    const age = row.age ?? row.birthYear
    if (age != null && String(age).trim()) bits.push(String(age))
    if (bits.length) return bits.join(' · ')
    return categoryTextOf(row) || formatAuthor(row.author) || ''
  }
  if (interactSurface.value === 'mutualpick') {
    if (quotaRemainOn.value && quotaRemainOf(row) != null) {
      const q = Number(quotaRemainOf(row))
      if (Number.isFinite(q)) return q <= 0 ? '名额已满' : `名额余 ${q}`
    }
    const n = Number(row.stock)
    if (Number.isFinite(n)) return n <= 0 ? '名额已满' : `名额余 ${n}`
    const qt = tutorQuotaText(row)
    if (qt) return qt
    return categoryTextOf(row) || '可填志愿'
  }
  if (interactSurface.value === 'triprow') {
    const bits = []
    const when = String(row.startAt || row.departAt || row.schedule || '').trim()
    if (when) bits.push(when.length > 16 ? when.slice(0, 16) : when)
    const start = String(row.startCampus || row.fromPlace || row.origin || '').trim()
    const end = String(row.endCampus || row.toPlace || row.destination || '').trim()
    if (start || end) bits.push(`${start || '—'}→${end || '—'}`)
    const n = Number(row.stock)
    if (Number.isFinite(n)) bits.push(n <= 0 ? '已满' : `余座 ${n}`)
    if (bits.length) return bits.join(' · ')
    return categoryTextOf(row) || ''
  }
  if (authorFieldIsMoney.value) {
    if (flashOn.value && row.promoActive) {
      const promo = Number(row.promoPrice)
      if (Number.isFinite(promo)) return `¥${promo.toFixed(2)}`
    }
    const n = Number(row.author)
    if (Number.isFinite(n)) return `¥${n.toFixed(2)}`
    const raw = formatAuthor(row.author)
    return raw && raw !== '—' ? raw : ''
  }
  if (cardVoice.value === 'story') {
    return categoryTextOf(row) || formatAuthor(row.author) || ''
  }
  const author = formatAuthor(row.author)
  if (author && author !== '—') return author
  return categoryTextOf(row) || ''
}

function boardToneOf(row) {
  if (!row) return ''
  const stock = Number(row.stock)
  if (Number.isFinite(stock)) {
    if (stock <= 0) return 'warn'
    if (stock <= 3) return 'pending'
    return 'ok'
  }
  const st = String(row.status || row.stage || '').toLowerCase()
  if (/满|占|借出|售罄|closed|full|taken/.test(st)) return 'warn'
  if (/可|空|有号|open|free|available/.test(st)) return 'ok'
  if (quotaRemainOn.value && quotaRemainOf(row) != null) {
    const q = Number(quotaRemainOf(row))
    if (q <= 0) return 'warn'
    if (q <= 3) return 'pending'
    return 'ok'
  }
  return ''
}

function boardLabelOf(row) {
  const stock = Number(row.stock)
  if (Number.isFinite(stock)) {
    if (stock <= 0) return '已满/无余'
    if (stock <= 3) return `余 ${stock}`
    return `可取 · 余 ${stock}`
  }
  const st = String(row.status || row.stage || '').trim()
  if (st) return st
  if (quotaRemainOn.value && quotaRemainOf(row) != null) {
    const q = Number(quotaRemainOf(row))
    return q <= 0 ? '名额已满' : `余 ${q}`
  }
  return '可办理'
}

/** 金额走价区间，不进关键词搜框（禁止「搜索单价」糊弄）。 */
const authorFieldIsMoney = computed(() => {
  const f = fields.value.find((x) => x.key === 'author')
  if (!f || f.type === 'hidden') return false
  if (f.format === 'money') return true
  const lab = String(f.label || '')
  return /单价|价格|费用|票价|积分价|服务费/.test(lab)
})

const priceRangeFilterOn = computed(() => authorFieldIsMoney.value)
const priceMinPlaceholder = computed(
  () => browseLabels.value.priceMinPlaceholder || '最低价',
)
const priceMaxPlaceholder = computed(
  () => browseLabels.value.priceMaxPlaceholder || '最高价',
)

const searchPlaceholder = computed(() => {
  if (titleSearchOn.value && titleSearchPlaceholder.value) {
    return titleSearchPlaceholder.value
  }
  const parts = [fieldLabel('title', '名称')]
  if (!authorFieldIsMoney.value) {
    parts.push(fieldLabel('author', '型号'))
  }
  const isbnF = fields.value.find((x) => x.key === 'isbn')
  if (isbnF && isbnF.type !== 'richtext' && isbnF.type !== 'hidden' && playUrlField.value !== 'isbn') {
    parts.push(isbnF.label || '编号')
  }
  const regionF = fields.value.find((x) => x.key === 'region')
  if (regionF && regionF.type !== 'hidden') {
    parts.push(regionF.label || '产地')
  }
  const harvestF = fields.value.find((x) => x.key === 'harvest_on')
  if (harvestF && harvestF.type !== 'hidden') {
    parts.push(harvestF.label || '采摘时间')
  }
  const base = `搜索${parts.join(' / ')}`
  if (titleSuggestOn.value && searchSuggestHint.value) {
    return `${base}（${searchSuggestHint.value}）`
  }
  return base
})

function toggleHotMode() {
  hotMode.value = !hotMode.value
  page.value = 1
  load()
}

const ruleHint = computed(() => {
  const parts = []
  const catLab = fieldLabel('category', '分类')
  const unit = archive.label || '项'
  if (checkMutex.value) parts.push('同互斥码不可同选')
  if (categoryLimit.value > 0) parts.push(`每${catLab}最多 ${categoryLimit.value} ${unit}`)
  if (tagFilter.value) parts.push('可多标签组合筛选')
  if (pickLoanPeriod.value) parts.push(`须选择${dueLabel.value}`)
  if (pickDateRange.value) parts.push('须选择起止日期')
  if (allowQty.value) parts.push('可填申请数量')
  if (requireRemark.value) parts.push(`须填写${remarkLabel.value}`)
  return parts.length ? parts.join('；') + '。' : ''
})
const qtyMax = computed(() => {
  const stock = Number(applyRow.value?.stock)
  if (Number.isFinite(stock) && stock > 0) return Math.min(99, stock)
  return 99
})
const hasSchedule = computed(() => fields.value.some((x) => x.key === 'startAt'))
const hasRecommend = computed(() => caps.value.includes('recommend'))
/** 影院选座：有 seat_select / seatSelect 时主路径进座位图，禁止当商城加购 */
const isSeatSelectMode = computed(
  () => caps.value.includes('seat_select') || hasTrait('seatSelect'),
)
const isOrderMode = computed(
  () =>
    caps.value.includes('order_lines')
    && !caps.value.includes('ticket_flow')
    && !caps.value.includes('slot_reserve')
    && !isSeatSelectMode.value,
)
const isSlotMode = computed(() => {
  if (!caps.value.includes('slot_reserve')) return false
  //  仪器机时等：借+约并存时主按钮走约时段（traits.slotPrimary）
  if (hasTrait('slotPrimary')) return true
  return !caps.value.includes('ticket_flow')
})
/** 即时收藏：交易/内容流；婚恋心动可与单据并存（收藏/心动） */
const favOn = computed(() => {
  if (!caps.value.includes('favorites')) return false
  if (isOrderMode.value || isSeatSelectMode.value) return true
  if (getSchema()?.interactThicken?.datingFavorites) return true
  return !caps.value.includes('ticket_flow') && !caps.value.includes('slot_reserve')
})
const likeOn = computed(() => hasCap('post_like'))
const flashOn = computed(() => hasCap('flash_price'))
const productSpecOn = computed(() => hasCap('product_spec'))
const productSpecLabel = computed(() => getSchema()?.labels?.productSpecLabel || '规格')
const flashBadge = computed(() => getSchema()?.labels?.flashPriceBadge || '活动价')
const flashCountdownLabel = computed(
  () => getSchema()?.labels?.flashCountdownLabel || '距结束',
)
const flashCountdownEnded = computed(
  () => getSchema()?.labels?.flashCountdownEnded || '已结束',
)
const favoritesVerb = computed(() => getSchema()?.labels?.favoritesVerb || '收藏')
const favoritedVerb = computed(() => getSchema()?.labels?.favoritedVerb || '已收藏')
const applyDeadlineLabel = computed(
  () => getSchema()?.labels?.applyDeadlineLabel || '截止',
)
const mutualDeadlineCountdownOn = computed(
  () => !!getSchema()?.interactThicken?.mutualDeadlineCountdown,
)
const mutualDeadlineCountdownLabel = computed(
  () => getSchema()?.labels?.mutualDeadlineCountdownLabel || '距志愿截止',
)
const mutualDeadlinePassedLabel = computed(
  () => getSchema()?.labels?.mutualDeadlinePassedLabel || '志愿已截止',
)
const mutualDeadlineHint = computed(() => {
  if (!mutualDeadlineCountdownOn.value) return ''
  return getSchema()?.labels?.mutualDeadlineHint || ''
})
const { nowMs } = useNowTick()

function flashSecondsLeft(row) {
  if (!row?.promoActive || !row.promoEnd) return null
  return secondsUntil(row.promoEnd, nowMs.value)
}

function flashCountdownText(row) {
  const sec = flashSecondsLeft(row)
  if (sec == null) return ''
  if (sec <= 0) return flashCountdownEnded.value
  return `${flashCountdownLabel.value} ${formatCountdownClock(sec)}`
}

function mutualDeadlineText(row) {
  if (!mutualDeadlineCountdownOn.value || !row?.applyDeadlineAt) return ''
  const sec = secondsUntil(row.applyDeadlineAt, nowMs.value)
  if (sec == null) return ''
  if (sec <= 0) return mutualDeadlinePassedLabel.value
  return `${mutualDeadlineCountdownLabel.value} ${formatCountdownClock(sec)}`
}
const reportOn = computed(() => hasCap('content_report'))
const likeVerb = computed(() => getSchema()?.labels?.likeVerb || '点赞')
const likedVerb = computed(() => getSchema()?.labels?.likedVerb || '已赞')
const reportVerb = computed(() => getSchema()?.labels?.reportVerb || '举报')
const applyFromList = computed(() => !!ticket.applyFromList)
/** 有单据/下单/预约/选座时才显示主操作；applyFromList（请假/归寝）主路径在「我的*」，档案页仅查阅 */
const showPrimaryApply = computed(
  () =>
    !applyFromList.value
    && (
      isOrderMode.value
      || isSeatSelectMode.value
      || isSlotMode.value
      || caps.value.includes('ticket_flow')
    ),
)
const favIds = ref([])
const likeIds = ref([])
const reportedIds = ref(new Set())
const favPulseId = ref(null)
const likePulseId = ref(null)
const reportVisible = ref(false)
const reportRow = ref(null)
const reportTargetType = ref('archive')
const reportReason = ref('')
const reportReasonCode = ref('')
const reportSubmitting = ref(false)
const reportTargetLabel = computed(() => {
  const row = reportRow.value
  if (!row) return ''
  if (reportTargetType.value === 'ticket') {
    return `回复 #${row.id}${row.username ? ' · ' + row.username : ''}`
  }
  if (reportTargetType.value === 'comment') {
    const who = row.nickname || row.username || ''
    return `评论 #${row.id}${who ? ' · ' + who : ''}`
  }
  return row.title || `#${row.id}`
})
const contentThicken = computed(() => getSchema()?.contentThicken || {})
const reportReasonDictOn = computed(() => !!contentThicken.value.reportReasonDict)
const commentReportOn = computed(() => !!contentThicken.value.commentReport)
const followersOnlyCommentOn = computed(() => !!contentThicken.value.followersOnlyComment)
const interactThicken = computed(() => getSchema()?.interactThicken || {})
const datingUserFollowOn = computed(() => !!interactThicken.value.datingUserFollow)
const datingMeetIntentOn = computed(() => !!interactThicken.value.datingMeetIntent)
const datingIdealFilterOn = computed(() => !!interactThicken.value.datingIdealFilter)
const datingActivityEntryOn = computed(() => !!interactThicken.value.datingActivityEntry)
const mutualInterviewEntryOn = computed(() => !!interactThicken.value.mutualInterviewEntry)
const mutualIntroPackOn = computed(() => !!interactThicken.value.mutualIntroPack)
const tutorQuotaBarOn = computed(() => !!interactThicken.value.mutualTutorQuotaBar)
const teamSkillTagsOn = computed(() => !!interactThicken.value.mutualTeamSkillTags)
const teamSkillMatchOn = computed(() => !!interactThicken.value.mutualTeamSkillMatch)
const teamInviteOn = computed(() => !!interactThicken.value.mutualTeamInvite)
const carpoolFullCloseOn = computed(() => !!interactThicken.value.carpoolFullClose)
const carpoolSeatRemainOn = computed(() => !!interactThicken.value.carpoolSeatRemain)
const carpoolCampusDictOn = computed(() => !!interactThicken.value.carpoolCampusDict)
const carpoolViaPointsOn = computed(() => !!interactThicken.value.carpoolViaPoints)
const carpoolShareNoteOn = computed(() => !!interactThicken.value.carpoolShareNote)
const carpoolPrefNoteOn = computed(() => !!interactThicken.value.carpoolPrefNote)
const carpoolLuggageOn = computed(() => !!interactThicken.value.carpoolLuggage)
const carpoolAaCalcOn = computed(() => !!interactThicken.value.carpoolAaCalc)
const carpoolDepartRemindOn = computed(() => !!interactThicken.value.carpoolDepartRemind)
const carpoolFullStageHint = computed(() => browseLabels.value.carpoolFullStageHint || '')
const carpoolSeatRemainLabel = computed(
  () => browseLabels.value.carpoolSeatRemainLabel || '剩余座位',
)
const carpoolSeatRemainHint = computed(() => browseLabels.value.carpoolSeatRemainHint || '')
const carpoolCampusStartLabel = computed(
  () => browseLabels.value.carpoolCampusStartLabel || '出发校区',
)
const carpoolCampusEndLabel = computed(
  () => browseLabels.value.carpoolCampusEndLabel || '到达校区',
)
const carpoolCampusPlaceholder = computed(
  () => browseLabels.value.carpoolCampusPlaceholder || '选择校区',
)
const carpoolCampusOptions = computed(() => {
  const raw = String(browseLabels.value.carpoolCampusOptions || '')
  return raw.split(/[,，]/).map((s) => s.trim()).filter(Boolean)
})
const carpoolViaPointsLabel = computed(() => browseLabels.value.viaPointsLabel || '途经点')
const carpoolViaPointsPlaceholder = computed(
  () => browseLabels.value.viaPointsPlaceholder || '多个途经点用逗号或换行分隔',
)
const carpoolShareNoteLabel = computed(() => browseLabels.value.shareNoteLabel || '费用分摊说明')
const carpoolShareNotePlaceholder = computed(
  () => browseLabels.value.shareNotePlaceholder || '',
)
const carpoolPrefNoteLabel = computed(() => browseLabels.value.prefNoteLabel || '同行偏好')
const carpoolPrefNotePlaceholder = computed(
  () => browseLabels.value.prefNotePlaceholder || '',
)
const carpoolLuggageCountLabel = computed(
  () => browseLabels.value.luggageCountLabel || '行李件数',
)
const fareTotalLabel = computed(() => browseLabels.value.fareTotalLabel || '预计总费用')
const fareTotalHint = computed(() => browseLabels.value.fareTotalHint || '')
const carpoolAaLabel = computed(() => browseLabels.value.carpoolAaLabel || '人均分摊')
const carpoolAaHint = computed(() => browseLabels.value.carpoolAaHint || '')
const carpoolDepartRemindLeadLabel = computed(
  () => browseLabels.value.carpoolDepartRemindLeadLabel || '出发前提醒',
)
const carpoolDepartRemindHint = computed(
  () => browseLabels.value.carpoolDepartRemindHint || '',
)
const carpoolDupTripDeny = computed(
  () => browseLabels.value.carpoolDupTripDeny || '你已发布相近出发时间的同行行程，请勿重复发布。',
)
const tutorQuotaBarLabel = computed(
  () => browseLabels.value.tutorQuotaBarLabel || '名额占用',
)
const tutorQuotaBarHint = computed(() => browseLabels.value.tutorQuotaBarHint || '')
const skillTagsLabel = computed(() => browseLabels.value.skillTagsLabel || '技能标签')
const skillTagsFilterPlaceholder = computed(
  () => browseLabels.value.skillTagsFilterPlaceholder || '按技能标签筛选',
)
const teamSkillMatchLabel = computed(
  () => browseLabels.value.teamSkillMatchLabel || '技能匹配',
)
const teamSkillMatchHint = computed(
  () => browseLabels.value.teamSkillMatchHint || '按标签重合数量提示匹配度，仅供参考。',
)
const skillTagsPlaceholder = computed(
  () => browseLabels.value.skillTagsPlaceholder || '多个标签用逗号分隔',
)
const teamInviteLabel = computed(() => browseLabels.value.teamInviteLabel || '邀请组队')
const teamInviteHint = computed(() => browseLabels.value.teamInviteHint || '')
const teamInviteTitle = computed(() => browseLabels.value.teamInviteTitle || '组队邀请')
const teamInviteBody = computed(() => browseLabels.value.teamInviteBody || '')
const teamFullStageHint = computed(() => browseLabels.value.teamFullStageHint || '')
const teamRemarkRequired = computed(
  () => browseLabels.value.teamRemarkRequired || '请填写申请附言后再提交',
)
const teamSkillMatchEmpty = computed(
  () => browseLabels.value.teamSkillMatchEmpty || '填写技能标签后可看重合数',
)
const skillTagFilter = ref('')
const mySkillTagsInput = ref('')
const inviteToUsername = ref('')
const filteredList = computed(() => {
  const rows = list.value || []
  if (!teamSkillTagsOn.value || !String(skillTagFilter.value || '').trim()) return rows
  return rows.filter((r) => rowMatchesSkillFilter(r))
})
const mutualInterviewEntryTitle = computed(
  () => browseLabels.value.mutualInterviewEntryTitle || '',
)
const mutualInterviewEntryHint = computed(
  () =>
    browseLabels.value.mutualInterviewEntryHint
    || '面试时段安排见互选公告；如需预约会议室请按当期公告指引办理。',
)
const mutualInterviewEntryCta = computed(
  () => browseLabels.value.mutualInterviewEntryCta || '查看互选公告',
)
const introPackLabel = computed(() => browseLabels.value.introPackLabel || '附件简介包')
const introPackOpenLabel = computed(
  () => browseLabels.value.introPackOpenLabel || '查看简介包',
)
const introPackHint = computed(() => browseLabels.value.introPackHint || '')
const datingAlbumAuditOn = computed(() => !!interactThicken.value.datingAlbumAudit)
const userFollowUiOn = computed(() => followersOnlyCommentOn.value || datingUserFollowOn.value)
const datingFilterCityPlaceholder = computed(
  () => browseLabels.value.datingFilterCityPlaceholder || '按城市筛选',
)
const datingFilterAgeMinPlaceholder = computed(
  () => browseLabels.value.datingFilterAgeMinPlaceholder || '最小',
)
const datingFilterAgeMaxPlaceholder = computed(
  () => browseLabels.value.datingFilterAgeMaxPlaceholder || '最大',
)
const datingActivityEntryTitle = computed(
  () => browseLabels.value.datingActivityEntryTitle || '',
)
const datingActivityEntryHint = computed(
  () => browseLabels.value.datingActivityEntryHint || '线下联谊安排见交友公告。',
)
const datingActivityEntryCta = computed(
  () => browseLabels.value.datingActivityEntryCta || '查看交友公告',
)
const albumAuditHiddenHint = computed(
  () => browseLabels.value.albumAuditHiddenHint || '相册审核通过后才会公开展示。',
)
const meetIntentLabel = computed(() => browseLabels.value.meetIntentLabel || '见面意向')
const meetIntentPlaceholder = computed(
  () => browseLabels.value.meetIntentPlaceholder || '请选择见面意向',
)
const meetIntentOptions = computed(() => {
  const raw = ticket.meetIntentOptions || getSchema()?.entities?.ticket?.meetIntentOptions
  return Array.isArray(raw) && raw.length ? raw : ['线上沟通', '线下见面', '参加联谊', '暂不确定']
})
const datingCityFilter = ref('')
const datingAgeMinFilter = ref(null)
const datingAgeMaxFilter = ref(null)
const priceMinFilter = ref(null)
const priceMaxFilter = ref(null)
const applyMeetIntent = ref('')
const reportReasonOptions = computed(() => {
  const raw = getSchema()?.reportReasons
  return Array.isArray(raw) ? raw : []
})
const itemCommentFollowersOnly = ref(false)
const followingUsers = ref(new Set())
const viewCountOn = computed(() => !!contentThicken.value.viewCount)
const viewCountLabel = computed(() => browseLabels.value.viewCountLabel || '阅读数')
const downloadCountOn = computed(() => !!contentThicken.value.hotByDownload)
const downloadCountLabel = computed(() => browseLabels.value.downloadCountLabel || '下载次数')
const hotRankOn = computed(() => !!contentThicken.value.hotRank)
const hotRankPageTitle = computed(() => browseLabels.value.hotRankPageTitle || '热门排行')
const hotRankPageLead = computed(() => browseLabels.value.hotRankPageLead || '按阅读次数从高到低排列。')
const hotRankToggleLabel = computed(() => browseLabels.value.hotRankToggleLabel || '看热门')
const hotRankBackLabel = computed(() => browseLabels.value.hotRankBackLabel || '全部')
const titleSearchOn = computed(() => !!contentThicken.value.titleSearch)
const titleSearchPlaceholder = computed(() => browseLabels.value.titleSearchPlaceholder || '')
const searchSuggestHint = computed(() => browseLabels.value.searchSuggestHint || '')
const draftBoxOn = computed(() => !!contentThicken.value.draftBox)
const draftAutoSaveOn = computed(() => !!contentThicken.value.draftAutoSave && draftBoxOn.value)
const draftAutoSaveHint = computed(
  () => browseLabels.value.draftAutoSaveHint || '编辑时会自动保存草稿，可稍后在「我的」里继续。',
)
const draftAutoSavedLabel = computed(() => browseLabels.value.draftAutoSavedLabel || '草稿已自动保存')
const essenceOn = computed(() => !!contentThicken.value.essence)
const lockedOn = computed(() => !!contentThicken.value.locked)
const sectionNoticeOn = computed(() => !!contentThicken.value.sectionNotice)
const nestedReplyOn = computed(() => !!contentThicken.value.nestedReply)
const commentFoldOn = computed(() => !!contentThicken.value.commentFold)
const commentFoldAfter = computed(() => Math.max(1, Number(getSchema()?.commentFoldAfter) || 3))
const nestedReplyLabel = computed(() => browseLabels.value.nestedReplyLabel || '回复楼中楼')
const mentionNotifyHint = computed(() => browseLabels.value.mentionNotifyHint || '')
const commentFoldMoreLabel = computed(() => browseLabels.value.commentFoldMoreLabel || '展开更多回复')
const commentFoldLessLabel = computed(() => browseLabels.value.commentFoldLessLabel || '收起')
const sensitiveWordHint = computed(() => browseLabels.value.sensitiveWordHint || '')
const categoryFollowOn = computed(() => !!contentThicken.value.categoryFollow)
const categoryFollowerCountOn = computed(() => !!contentThicken.value.categoryFollowerCount)
const categoryFollowLabel = computed(() => browseLabels.value.categoryFollowLabel || '订阅专栏')
const categoryUnfollowLabel = computed(() => browseLabels.value.categoryUnfollowLabel || '取消订阅')
const categoryFollowHint = computed(() => browseLabels.value.categoryFollowHint || '')
const categoryFollowerCountLabel = computed(() => browseLabels.value.categoryFollowerCountLabel || '订阅数')
const archiveYearMonthOn = computed(() => !!contentThicken.value.archiveYearMonth)
const archiveYearMonthLabel = computed(() => browseLabels.value.archiveYearMonthLabel || '按年月归档')
const archiveYearMonthAllLabel = computed(() => browseLabels.value.archiveYearMonthAllLabel || '全部月份')
const seriesNavOn = computed(() => !!contentThicken.value.seriesNav)
const seriesPrevLabel = computed(() => browseLabels.value.seriesPrevLabel || '上一篇')
const seriesNextLabel = computed(() => browseLabels.value.seriesNextLabel || '下一篇')
const seriesHint = computed(() => browseLabels.value.seriesHint || '')
const originKindOn = computed(() => !!contentThicken.value.originKind)
const originKindLabel = computed(() => browseLabels.value.originKindLabel || '原创声明')
const originOriginalLabel = computed(() => browseLabels.value.originOriginalLabel || '原创')
const originReprintLabel = computed(() => browseLabels.value.originReprintLabel || '转载')
const authorPageOn = computed(() => !!contentThicken.value.authorPage)
const authorPageTitle = computed(() => browseLabels.value.authorPageTitle || '作者主页')
const accessPasswordOn = computed(() => !!contentThicken.value.accessPassword)
const accessPasswordLabel = computed(() => browseLabels.value.accessPasswordLabel || '访问口令')
const accessPasswordHint = computed(() => browseLabels.value.accessPasswordHint || '')
const accessPasswordPrompt = computed(() => browseLabels.value.accessPasswordPrompt || '请输入访问口令')
const accessPasswordUnlockLabel = computed(() => browseLabels.value.accessPasswordUnlockLabel || '解锁')
const friendLinksOn = computed(() => !!contentThicken.value.friendLinks)
const friendLinkPageTitle = computed(() => browseLabels.value.friendLinkPageTitle || '友情链接')
const commentAuthorNotifyOn = computed(() => !!contentThicken.value.commentAuthorNotify)
const commentAuthorNotifyHint = computed(() => browseLabels.value.commentAuthorNotifyHint || '')
const authorPageEntryLabel = computed(() => browseLabels.value.authorPageEntryLabel || '看作者')
const playProgressOn = computed(() => !!contentThicken.value.playProgress)
const playProgressHint = computed(() => browseLabels.value.playProgressHint || '')
const playProgressSaveLabel = computed(() => browseLabels.value.playProgressSaveLabel || '记下进度')
const episodeCompletedLabel = computed(() => browseLabels.value.episodeCompletedLabel || '已看完')
const episodeContinueLabel = computed(() => browseLabels.value.episodeContinueLabel || '继续看')
const episodeListOn = computed(() => !!contentThicken.value.episodeList)
const episodeListTitle = computed(() => browseLabels.value.episodeListTitle || '选集')
const episodeListEmpty = computed(() => browseLabels.value.episodeListEmpty || '暂无分集')
const posterWallOn = computed(() => !!contentThicken.value.posterWall)
const posterWallTitle = computed(() => browseLabels.value.posterWallTitle || '海报墙')
const posterWallLead = computed(() => browseLabels.value.posterWallLead || '')
/** 交易组页内构图：shelfgrid / menuboard / showtime；非交易域为空 */
const tradeSurface = computed(() => {
  const s = String(
    APP_DELIVERED?.tradeSurfaceStyle
      || import.meta.env.VITE_TRADE_SURFACE_STYLE
      || '',
  ).trim()
  if (['shelfgrid', 'menuboard', 'showtime'].includes(s)) return s
  return ''
})
/** 预约组页内构图：slotstrip / roomstate / vehiclecard；非预约域为空 */
const reserveSurface = computed(() => {
  const s = String(
    APP_DELIVERED?.reserveSurfaceStyle
      || import.meta.env.VITE_RESERVE_SURFACE_STYLE
      || '',
  ).trim()
  if (['slotstrip', 'roomstate', 'vehiclecard'].includes(s)) return s
  return ''
})
/** 借用组页内构图：bookshelf / stockrow / bedblocks / parcelshelf；非借用域为空 */
const borrowSurface = computed(() => {
  const s = String(
    APP_DELIVERED?.borrowSurfaceStyle
      || import.meta.env.VITE_BORROW_SURFACE_STYLE
      || '',
  ).trim()
  if (['bookshelf', 'stockrow', 'bedblocks', 'parcelshelf'].includes(s)) return s
  return ''
})
/** 报名组页内构图：eventposter / coursetable / noticeboard / tourcard；非报名域为空 */
const applySurface = computed(() => {
  const s = String(
    APP_DELIVERED?.applySurfaceStyle
      || import.meta.env.VITE_APPLY_SURFACE_STYLE
      || '',
  ).trim()
  if (['eventposter', 'coursetable', 'noticeboard', 'tourcard'].includes(s)) return s
  return ''
})
/** 互动组页内构图：profilegrid / mutualpick / triprow；考试问卷投票不进本轴 */
const interactSurface = computed(() => {
  const s = String(
    APP_DELIVERED?.interactSurfaceStyle
      || import.meta.env.VITE_INTERACT_SURFACE_STYLE
      || '',
  ).trim()
  if (['profilegrid', 'mutualpick', 'triprow'].includes(s)) return s
  return ''
})
/** 跟进组页内构图：pipeline / dossier / listing；非跟进域为空 */
const followSurface = computed(() => {
  const s = String(
    APP_DELIVERED?.followSurfaceStyle
      || import.meta.env.VITE_FOLLOW_SURFACE_STYLE
      || '',
  ).trim()
  if (['pipeline', 'dossier', 'listing'].includes(s)) return s
  return ''
})
/** 内容组页内构图：folio / coverwall / ledger / splitdesk；非内容域为空 */
const contentSurface = computed(() => {
  const s = String(
    APP_DELIVERED?.contentSurfaceStyle
      || import.meta.env.VITE_CONTENT_SURFACE_STYLE
      || '',
  ).trim()
  if (['folio', 'coverwall', 'ledger', 'splitdesk'].includes(s)) return s
  return ''
})
/** MEDIA posterWall 并入 coverwall；有手选则 coverwall 优先于 thicken 旗标 */
const coverWallActive = computed(
  () => contentSurface.value === 'coverwall' || (!contentSurface.value && posterWallOn.value),
)
const splitSelected = ref(null)
const splitSelectedId = computed(() => splitSelected.value?.id ?? null)
const splitNarrow = ref(false)
let splitNarrowMq = null
function syncSplitNarrow() {
  splitNarrow.value = !!splitNarrowMq?.matches
}
function onContentSurfaceCardClick(row, ev) {
  if (contentSurface.value !== 'splitdesk') return
  if (ev?.target?.closest?.('button, a, .el-button, .el-tag, input, textarea')) return
  if (splitNarrow.value) {
    openDetail(row)
    return
  }
  splitSelected.value = row
}
const hotByPlayOn = computed(() => !!contentThicken.value.hotByPlay)
const playCountOn = computed(() => !!contentThicken.value.hotByPlay || !!contentThicken.value.playProgress)
const playCountLabel = computed(() => browseLabels.value.playCountLabel || '播放次数')
const shareCodeOn = computed(() => !!contentThicken.value.shareCode)
const shareCodeLabel = computed(() => browseLabels.value.shareCodeLabel || '分享码')
const shareCodeEntryLabel = computed(() => browseLabels.value.shareCodeEntryLabel || '凭码打开')
const shareCodePrompt = computed(() => browseLabels.value.shareCodePrompt || '请输入分享码')
const shareCodeInput = ref('')
const artistAlbumFilterOn = computed(() => !!contentThicken.value.artistAlbumFilter)
const artistFilterPlaceholder = computed(() => browseLabels.value.artistFilterPlaceholder || '按歌手筛选')
const albumFilterPlaceholder = computed(() => browseLabels.value.albumFilterPlaceholder || '按专辑筛选')
const lyricsOn = computed(() => !!contentThicken.value.lyrics)
const lyricsLabel = computed(() => browseLabels.value.lyricsLabel || '歌词')
const lyricsEmpty = computed(() => browseLabels.value.lyricsEmpty || '暂无歌词')
const coverMarkOn = computed(() => !!contentThicken.value.coverMark)
const coverMarkLabel = computed(() => browseLabels.value.coverMarkLabel || '翻唱')
const audioQualityOn = computed(() => !!contentThicken.value.audioQualitySwitch)
const audioQualityLabel = computed(() => browseLabels.value.audioQualityLabel || '音质')
const audioQualityHint = computed(() => browseLabels.value.audioQualityHint || '')
const audioQualityOptions = computed(() => {
  const raw = browseLabels.value.audioQualityOptions || '标准,较高,无损'
  return String(raw).split(/[,，]/).map((s) => s.trim()).filter(Boolean)
})
const audioQualityPick = ref('')
const artistFilter = ref('')
const albumFilter = ref('')
const episodes = ref([])
const episodeProgressMap = ref({})
const activeEpisodeId = ref(0)
const progressSec = ref(0)
const progressSaving = ref(false)
const currentProgress = computed(() => epProgress({ id: activeEpisodeId.value }))
function epProgress(ep) {
  const id = Number(ep?.id) || 0
  return episodeProgressMap.value[id] || null
}
async function loadTrackProgress(itemId) {
  if (!playProgressOn.value || isGuest.value || !itemId) return
  try {
    const pr = await http.get('/api/media-progress', { params: { itemId, episodeId: 0 } })
    episodeProgressMap.value = { ...episodeProgressMap.value, 0: pr.data || pr }
    progressSec.value = Number(pr.data?.positionSec || pr?.positionSec) || 0
  } catch { /* ignore */ }
}
async function loadEpisodes(itemId) {
  episodes.value = []
  episodeProgressMap.value = {}
  activeEpisodeId.value = 0
  if (!itemId) return
  if (!episodeListOn.value) {
    await loadTrackProgress(itemId)
    return
  }
  try {
    const res = await http.get(`/api/media-episodes/by-item/${itemId}`)
    episodes.value = res.data || res || []
    if (episodes.value.length) {
      activeEpisodeId.value = episodes.value[0].id
      if (playProgressOn.value && !isGuest.value) {
        for (const ep of episodes.value) {
          try {
            const pr = await http.get('/api/media-progress', { params: { itemId, episodeId: ep.id } })
            episodeProgressMap.value = { ...episodeProgressMap.value, [ep.id]: pr.data || pr }
          } catch { /* ignore */ }
        }
        const cur = epProgress({ id: activeEpisodeId.value })
        progressSec.value = Number(cur?.positionSec) || 0
      }
    } else if (playProgressOn.value && !isGuest.value) {
      await loadTrackProgress(itemId)
    }
  } catch {
    episodes.value = []
  }
}
function selectEpisode(ep) {
  activeEpisodeId.value = ep.id
  const cur = epProgress(ep)
  progressSec.value = Number(cur?.positionSec) || 0
}
async function saveProgress(completed) {
  if (!requireLogin(router) || !detail.value?.id) return
  progressSaving.value = true
  try {
    const res = await http.post('/api/media-progress', {
      itemId: detail.value.id,
      episodeId: activeEpisodeId.value || 0,
      positionSec: Number(progressSec.value) || 0,
      completed: !!completed,
    })
    const data = res.data || res
    episodeProgressMap.value = { ...episodeProgressMap.value, [activeEpisodeId.value || 0]: data }
    if (detail.value.playCount != null) detail.value.playCount = Number(detail.value.playCount || 0) + 1
    ElMessage.success(completed ? episodeCompletedLabel.value : '已记下进度')
  } finally {
    progressSaving.value = false
  }
}
async function openByShareCode() {
  const code = (shareCodeInput.value || '').trim()
  if (!code) {
    ElMessage.warning(shareCodePrompt.value)
    return
  }
  try {
    const res = await http.get('/api/archive/by-share-code', { params: { code } })
    if (res.data) await openDetail(res.data)
    else ElMessage.warning(browseLabels.value.shareCodeBlocked || '分享码无效')
  } catch {
    ElMessage.warning(browseLabels.value.shareCodeBlocked || '分享码无效')
  }
}
const archiveYear = ref(null)
const archiveMonth = ref(null)
const archiveYearOptions = computed(() => {
  const y = new Date().getFullYear()
  return [y, y - 1, y - 2, y - 3, y - 4]
})
const categoryFollowing = ref(false)
const categoryFollowerCount = ref(0)
const followLoading = ref(false)
const friendLinks = ref([])
const authorFilter = ref('')
const seriesPrev = ref(null)
const seriesNext = ref(null)
const unlockPassword = ref('')
const unlockLoading = ref(false)
const publishOriginKind = ref('original')
const publishAccessPassword = ref('')
const activeFollowCategoryId = computed(() => {
  if (!categoryFollowOn.value) return null
  if (multiCategory.value) {
    return categoryIds.value?.length === 1 ? categoryIds.value[0] : null
  }
  return categoryId.value || null
})
function originKindText(v) {
  if (v === 'reprint') return originReprintLabel.value
  if (v === 'original') return originOriginalLabel.value
  return String(v || '')
}
function authorKey(row) {
  return String(row?.ownerUsername || row?.author || '').trim()
}
function onYearMonthChange() {
  if (!archiveYear.value) archiveMonth.value = null
  page.value = 1
  load()
}
async function refreshFollowStatus() {
  const cid = activeFollowCategoryId.value
  if (!categoryFollowOn.value || !cid) {
    categoryFollowing.value = false
    categoryFollowerCount.value = 0
    return
  }
  try {
    const res = await http.get(`/api/category-follow/status/${cid}`)
    categoryFollowing.value = !!res.data?.following
    categoryFollowerCount.value = Number(res.data?.count) || 0
  } catch {
    categoryFollowing.value = false
    categoryFollowerCount.value = 0
  }
}
async function toggleCategoryFollow() {
  if (!requireLogin(router)) return
  const cid = activeFollowCategoryId.value
  if (!cid) return
  followLoading.value = true
  try {
    const res = await http.post(`/api/category-follow/${cid}/toggle`)
    categoryFollowing.value = !!res.data?.following
    categoryFollowerCount.value = Number(res.data?.count) || 0
    ElMessage.success(categoryFollowing.value ? '已订阅' : '已取消订阅')
  } finally {
    followLoading.value = false
  }
}
async function loadFriendLinks() {
  if (!friendLinksOn.value) {
    friendLinks.value = []
    return
  }
  try {
    const res = await http.get('/api/blog-friend-links')
    friendLinks.value = res.data || res || []
  } catch {
    friendLinks.value = []
  }
}
function openAuthorPage(row) {
  const u = authorKey(row)
  if (!u) return
  authorFilter.value = u
  detailVisible.value = false
  page.value = 1
  load()
}
function clearAuthorFilter() {
  authorFilter.value = ''
  page.value = 1
  load()
}
async function loadSeriesNeighbors(id) {
  seriesPrev.value = null
  seriesNext.value = null
  if (!seriesNavOn.value || !id) return
  try {
    const res = await http.get(`/api/archive/${id}/series-neighbors`)
    seriesPrev.value = res.data?.prev || null
    seriesNext.value = res.data?.next || null
  } catch {
    seriesPrev.value = null
    seriesNext.value = null
  }
}
async function unlockDetail() {
  if (!detail.value?.id) return
  const pw = (unlockPassword.value || '').trim()
  if (!pw) {
    ElMessage.warning(accessPasswordPrompt.value)
    return
  }
  unlockLoading.value = true
  try {
    const res = await http.post(`/api/archive/${detail.value.id}/unlock`, { password: pw })
    if (res.data) detail.value = { ...detail.value, ...res.data, contentLocked: false }
    unlockPassword.value = ''
    ElMessage.success('已解锁')
  } catch (e) {
    const msg = String(e?.message || e?.response?.data?.message || browseLabels.value.accessPasswordBlocked || '口令不正确')
    ElMessage.warning(msg)
  } finally {
    unlockLoading.value = false
  }
}
const applyParentTicketId = ref(null)
const threadExpanded = ref(false)
const threadRoots = computed(() =>
  (threadList.value || []).filter((r) => !Number(r.parentTicketId)),
)
const visibleThreadRoots = computed(() => {
  if (!commentFoldOn.value || threadExpanded.value) return threadRoots.value
  return threadRoots.value.slice(0, commentFoldAfter.value)
})
function childrenOf(parentId) {
  return (threadList.value || []).filter((r) => Number(r.parentTicketId) === Number(parentId))
}
function openNestedReply(parent) {
  if (!detail.value) return
  if (Number(parent?.parentTicketId) > 0) {
    ElMessage.warning(browseLabels.value.nestedReplyBlocked || '该回复下不能再盖楼')
    return
  }
  applyParentTicketId.value = parent.id
  apply(detail.value)
}
function clearNestedParent() {
  applyParentTicketId.value = null
}
const pinTopLabel = computed(() => browseLabels.value.pinTopLabel || '置顶')
const essenceLabel = computed(() => browseLabels.value.essenceLabel || '精华')
const lockedLabel = computed(() => browseLabels.value.lockedLabel || '锁定')
const essenceHint = computed(() => browseLabels.value.essenceHint || '')
const lockedHint = computed(() => browseLabels.value.lockedHint || '')
const saveDraftLabel = computed(() => browseLabels.value.saveDraftLabel || '存草稿')
const dailyPostLimitHint = computed(() => browseLabels.value.dailyPostLimitHint || '')
const activeSectionNotice = computed(() => {
  if (!sectionNoticeOn.value) return ''
  const id = multiCategory.value
    ? (categoryIds.value?.length === 1 ? categoryIds.value[0] : null)
    : categoryId.value
  if (!id) return ''
  const cat = (categories.value || []).find((c) => Number(c.id) === Number(id))
  return String(cat?.sectionNotice || '').trim()
})
const searchAssist = computed(() => isSearchAssistEnabled())
const titleSuggestOn = computed(() => searchAssist.value || titleSearchOn.value)
/** 与顶栏检索槽同开时隐藏页内关键词，避免双搜框（§3.0.4） */
const topBarSearchOn = computed(() => !!getSchema()?.listCrosscut?.globalSearch)
const hotKeywords = computed(() => searchHotKeywords())
const hotMode = ref(false)
const galleryOn = computed(() => isGalleryEnabled())
const roomEquipOn = computed(() => hasCap('room_equipment'))
const equipSectionTitle = computed(
  () => getSchema()?.labels?.roomEquipmentSectionTitle || '配套设备',
)
const detailEquipNames = computed(() => {
  if (!roomEquipOn.value || !detail.value) return []
  const n = detail.value.equipmentNames
  return Array.isArray(n) ? n.filter(Boolean) : []
})
const browseOn = computed(() => isBrowseHistoryEnabled())
const logOn = computed(() => isArchiveLogEnabled())
const logEnt = computed(() => archiveLogCopy())
const logFields = computed(() => logEnt.value.fields || [])
const logSectionTitle = computed(
  () => getSchema()?.labels?.archiveLogSectionTitle || logEnt.value.labelPlural || '打卡与随访',
)
const logSubmitLabel = computed(
  () => getSchema()?.labels?.archiveLogSubmitLabel || '提交登记',
)
const logList = ref([])
const logLoading = ref(false)
const logSubmitting = ref(false)
const logForm = ref({ payload: {}, abnormal: false })

function resetLogForm() {
  const payload = {}
  for (const f of logFields.value) {
    if (f?.key) payload[f.key] = ''
  }
  logForm.value = { payload, abnormal: false }
}

function logPayloadText(row) {
  const p = row.payload || {}
  const parts = []
  for (const f of logFields.value) {
    const val = p[f.key]
    if (val != null && String(val).trim() !== '') parts.push(`${f.label || f.key}:${val}`)
  }
  return parts.join(' · ') || '—'
}

async function loadLogs(itemId) {
  if (!logOn.value || !itemId) return
  logLoading.value = true
  try {
    const res = await http.get('/api/archive-logs', { params: { itemId, page: 1, size: 20 } })
    logList.value = res.data?.list || []
  } finally {
    logLoading.value = false
  }
}

async function submitLog() {
  if (!detail.value?.id) return
  if (!requireLogin(router)) return
  logSubmitting.value = true
  try {
    await http.post('/api/archive-logs', {
      itemId: detail.value.id,
      logType: logEnt.value.defaultType || 'checkin',
      payload: { ...logForm.value.payload },
      abnormal: !!logForm.value.abnormal,
    })
    ElMessage.success('已提交')
    resetLogForm()
    await loadLogs(detail.value.id)
  } finally {
    logSubmitting.value = false
  }
}
const cartLabel = computed(() => menuLabel('user', 'cart', '购物车'))
const galleryUrls = computed(() => {
  if (!detail.value) return []
  const g = detail.value.galleryImages
  if (galleryOn.value && Array.isArray(g) && g.length) return g
  if (detail.value.coverUrl) return [detail.value.coverUrl]
  return []
})
const resvVerb = computed(() => getSchema()?.entities?.reservation?.verbs?.apply || '预约')
const primaryActionLabel = computed(() => {
  if (isSeatSelectMode.value) {
    return getSchema()?.labels?.seatSelectCta || '选座'
  }
  if (isOrderMode.value) return `加入${cartLabel.value}`
  if (isSlotMode.value) return '选时段'
  if (!showPrimaryApply.value) return '收藏'
  return verbs.value.apply || '申请'
})
const actionHint = computed(() => {
  if (isSeatSelectMode.value) return '进入座位图选座下单'
  if (isOrderMode.value) return `加入${cartLabel.value}并下单`
  if (isSlotMode.value) return `选择时段${resvVerb.value}`
  if (favOn.value && !showPrimaryApply.value) return '一键收藏感兴趣的内容'
  if (userPublish.value) {
    return publishUsesRichBody.value
      ? `发帖后可${verbs.value.apply || '回复'}`
      : `登记后可${verbs.value.apply || '提交'}`
  }
  return `提交${verbs.value.apply || '申请'}`
})

function fieldLabel(key, fallback) {
  const f = fields.value.find((x) => x.key === key)
  return (f && f.label) || fallback
}

function formatAuthor(v) {
  const f = fields.value.find((x) => x.key === 'author') || { key: 'author', type: 'string' }
  return formatArchiveScalar(f, v)
}

function formatFieldValue(row, field) {
  if (!row || !field) return '—'
  return formatArchiveScalar(field, row[field.key], '—')
}

function scheduleText(row) {
  if (!row || !hasSchedule.value) return ''
  if (!row.startAt && !row.endAt) return ''
  if (row.startAt && row.endAt) return `${row.startAt} ~ ${row.endAt}`
  return row.startAt || row.endAt || ''
}

const conflictHighlightOn = computed(() => !!ticket.conflictHighlight)
const conflictHighlightLabel = computed(
  () => browseLabels.value.conflictHighlightLabel || '课表冲突',
)
const conflictHighlightHint = computed(() => browseLabels.value.conflictHighlightHint || '')
const mySchedule = ref([])

function toMs(s) {
  if (!s) return null
  const t = Date.parse(String(s).replace(' ', 'T'))
  return Number.isNaN(t) ? null : t
}

function rangeOverlap(aStart, aEnd, bStart, bEnd) {
  const a0 = toMs(aStart)
  const a1 = toMs(aEnd)
  const b0 = toMs(bStart)
  const b1 = toMs(bEnd)
  if (a0 == null || a1 == null || b0 == null || b1 == null) return false
  return a0 < b1 && b0 < a1
}

function wouldConflict(row) {
  if (!conflictHighlightOn.value || !row?.startAt || !row?.endAt) return false
  return mySchedule.value.some((t) => rangeOverlap(row.startAt, row.endAt, t.startAt, t.endAt))
}

async function loadMySchedule() {
  if (!conflictHighlightOn.value) {
    mySchedule.value = []
    return
  }
  try {
    const res = await http.get('/api/tickets', { params: { page: 1, size: 200 } })
    mySchedule.value = (res.data?.list || []).filter(
      (x) => x.startAt && x.endAt && ['pending', 'approved', 'returned'].includes(String(x.status || '')),
    )
  } catch {
    mySchedule.value = []
  }
}

function stockOk(row) {
  if (Number(row.stock) <= 0) return false
  if (row.status === 'unavailable') return false
  return true
}

const stockTightBelow = computed(() => {
  const sch = getSchema() || {}
  const n = Number(sch.stockTightBelow)
  return Number.isFinite(n) && n > 0 ? n : 3
})
const stockTightHint = computed(() => {
  const sch = getSchema() || {}
  return (sch.labels && sch.labels.stockTightHint) || ''
})
const minGroupHint = computed(() => {
  const sch = getSchema() || {}
  return (sch.labels && sch.labels.minGroupHint) || ''
})
const collegeFilterOn = computed(() => fields.value.some((f) => f?.key === 'college'))
const collegeFilter = ref('')
const collegeOptions = computed(() => {
  const set = new Set()
  for (const r of list.value || []) {
    const c = String(r?.college || '').trim()
    if (c) set.add(c)
  }
  if (collegeFilter.value && !set.has(collegeFilter.value)) set.add(collegeFilter.value)
  return [...set].sort()
})
function minGroupHintOf(row) {
  const n = Number(row?.minGroupSize)
  if (!Number.isFinite(n) || n <= 0) return ''
  const base = minGroupHint.value || '成团最低人数提示'
  return `${base}（最低 ${n} 人）`
}

function stockTight(row) {
  const n = Number(row?.stock)
  const below = stockTightBelow.value
  return Number.isFinite(n) && n > 0 && n <= below
}

const allowWaitlist = computed(() => !!(ticket.allowWaitlist || hasCap('waitlist')))
const allowBookHold = computed(() => !!(ticket.allowBookHold || hasCap('book_hold')))

function canApplyOrWait(row) {
  if (!row) return false
  if (row.status === 'unavailable') return false
  if (stockOk(row)) return true
  return allowWaitlist.value || allowBookHold.value
}

function applyActionLabel(row) {
  if (row && !stockOk(row) && row.status !== 'unavailable') {
    if (allowBookHold.value) {
      return verbs.value.bookHold || labelsBookHoldVerb.value || '预约'
    }
    if (allowWaitlist.value) {
      return verbs.value.waitlist || labelsWaitlistVerb.value || '候补报名'
    }
  }
  return primaryActionLabel.value
}

const labelsWaitlistVerb = computed(() => {
  const sch = getSchema() || {}
  return (sch.labels && sch.labels.waitlistVerb) || ''
})

const labelsBookHoldVerb = computed(() => {
  const sch = getSchema() || {}
  return (sch.labels && sch.labels.bookHoldVerb) || ''
})

function stockText(row) {
  if (stockDisplay.value === 'toggle' || stockDisplay.value === 'available') {
    const ok = fieldLabel('stock', stockCountLabel.value)
    if (!stockOk(row)) {
      return archive.stockUnavailableLabel || stockUnavailableFrom(ok)
    }
    if (stockDisplay.value === 'toggle') return stockTight(row) ? `${ok}·紧张` : ok
    const n = Number(row.stock)
    if (Number.isFinite(n) && n > 1) {
      return stockTight(row) ? `${ok} · 仅余 ${n}` : `${ok} · 余 ${n}`
    }
    return ok
  }
  if (stockTight(row)) return `${stockCountLabel.value}仅余 ${row.stock}`
  return stockOk(row) ? `${stockCountLabel.value} ${row.stock}` : `暂无${stockCountLabel.value}`
}

/** 库存不足文案：与 schema 库存标签同规则，无字段时兜底 */
function stockUnavailableFrom(stockLabel) {
  const s = String(stockLabel || '可用').trim() || '可用'
  if (s.startsWith('可')) return `已${s.slice(1)}`
  return `暂无${s}`
}

function playUrlOf(row) {
  const key = playUrlField.value
  if (!key || !row) return ''
  const raw = key === 'isbn' ? row.isbn : row[key]
  const s = raw == null ? '' : String(raw).trim()
  if (!s) return ''
  if (/^https?:\/\//i.test(s) || s.startsWith('/') || s.startsWith('blob:')) return s
  return ''
}

function play(row) {
  const url = playUrlOf(row)
  if (!url) {
    ElMessage.warning('暂无播放链接')
    return
  }
  window.open(url, '_blank', 'noopener,noreferrer')
}

const list = ref([])
const total = ref(0)
const page = ref(1)
const size = ref(10)
const keyword = ref('')
const categoryId = ref(null)
const categoryIds = ref([])
const categories = ref([])
const tagIds = ref([])
const tags = ref([])
const categoriesByDimension = computed(() => {
  const groups = new Map()
  for (const c of categories.value || []) {
    const dim = (c.dimension || '').trim() || '未分组'
    if (!groups.has(dim)) groups.set(dim, [])
    groups.get(dim).push(c)
  }
  return [...groups.entries()].map(([dimension, items]) => ({ dimension, items }))
})
const recRef = ref(null)
const detailVisible = ref(false)
const detail = ref(null)
const itemReviews = ref([])
const itemGoodRate = ref(null)
const itemQaList = ref([])
const itemQaDraft = ref('')
const itemQaSubmitting = ref(false)
const stockNotifySubscribed = ref(false)
const stockNotifyLoading = ref(false)
const thicken = computed(() => getSchema()?.tradeThicken || {})
const stockNotifyOn = computed(() => !!thicken.value.stockNotify)
const goodRateOn = computed(() => !!thicken.value.goodRate)
const itemQaOn = computed(() => !!thicken.value.itemQa)
const specStockOn = computed(() => !!thicken.value.specStock)
const presaleNoteOn = computed(() => !!thicken.value.presaleNote)
const siblingSpecs = computed(() => {
  const list = detail.value?.siblingSpecStock
  return Array.isArray(list) ? list : []
})
const reviewOn = computed(() => hasCap('order_review'))
const itemCommentOn = computed(() => hasCap('item_comment'))
const codeQrOn = computed(() => hasCap('code_qr'))
const checkinCodeLabel = computed(() => browseLabels.value.codeQrShowVerb || ticketCheckinLabel() || '签到码')
const pinTopHint = computed(() => browseLabels.value.pinTopHint || '')
const visaMaterialHint = computed(() => browseLabels.value.visaMaterialHint || '')
const materialApplyHint = computed(
  () =>
    browseLabels.value.moralMaterialHint
    || browseLabels.value.partyMaterialHint
    || browseLabels.value.partyThoughtHint
    || browseLabels.value.fleetDriverCertHint
    || visaMaterialHint.value
    || '',
)
const lotteryResultOn = computed(() => !!ticket.allowLottery)
const lotteryResultTitle = computed(() => browseLabels.value.lotteryResultTitle || '抽签结果公示')
const lotteryResultHint = computed(() => browseLabels.value.lotteryResultHint || '')
const lotteryRows = ref([])
async function loadLotteryResult(itemId) {
  lotteryRows.value = []
  if (!lotteryResultOn.value || !itemId) return
  try {
    const res = await http.get('/api/tickets/lottery-result', { params: { itemId } })
    lotteryRows.value = res.data || []
  } catch (e) {
    lotteryRows.value = []
  }
}
const lostClueOn = computed(() => hasCap('lost_clue'))
const clueList = ref([])
const clueLoading = ref(false)
const clueSubmitting = ref(false)
const clueForm = reactive({ guestName: '', guestContact: '', type: 'clue', content: '' })
const itemComments = ref([])
const itemCommentLoading = ref(false)
const itemCommentDraft = ref('')
const itemCommentSubmitting = ref(false)
const itemCommentTitle = computed(
  () => getSchema()?.labels?.itemCommentSectionTitle || '用户评论',
)
const itemCommentSubmitLabel = computed(
  () => getSchema()?.labels?.itemCommentSubmitLabel || '发表评论',
)
const itemCommentEmpty = computed(
  () => getSchema()?.labels?.itemCommentEmpty || '暂无评论',
)
const marketplace = computed(() => !!getSchema()?.shopMarketplace)
/** 评价/多店商品字段/正文图集等任一需要详情时给出入口 */
const showDetailBtn = computed(
  () =>
    bodyRich.value
    || galleryOn.value
    || browseOn.value
    || logOn.value
    || roomEquipOn.value
    || reviewOn.value
    || itemCommentOn.value
    || marketplace.value,
)
function shopLabel(row) {
  if (!row) return ''
  return String(row.shopName || row.shop_name || '').trim()
}
function onCategoryChange() {
  if (isGuest.value) {
    categoryId.value = null
    requireLogin(router)
    return
  }
  page.value = 1
  load()
  refreshFollowStatus()
}
function onMultiCategoryChange() {
  if (isGuest.value) {
    categoryIds.value = []
    requireLogin(router)
    return
  }
  page.value = 1
  load()
  refreshFollowStatus()
}
function onTagFilterChange() {
  if (isGuest.value) {
    tagIds.value = []
    requireLogin(router)
    return
  }
  page.value = 1
  load()
}
const applyVisible = ref(false)
const applyRow = ref(null)
const applyRemark = ref('')
const applyAttachUrl = ref('')
const applyQty = ref(1)
const applyDueAt = ref('')
const applyAmount = ref(null)
const applyPeriod = ref(null)
const applyChannel = ref('')
const applyNextFollow = ref('')
const applyCheckinCode = ref('')
const applyAnonymous = ref(false)
const applyDimScores = reactive({})
const applyLoading = ref(false)
const conflictTip = ref('')
const publishVisible = ref(false)
const publishTitle = ref('')
const publishAuthor = ref('')
const publishBody = ref('')
const publishStock = ref(2)
const publishStartAt = ref('')
const publishStartCampus = ref('')
const publishEndCampus = ref('')
const publishViaPoints = ref('')
const publishShareNote = ref('')
const publishPrefNote = ref('')
const publishLuggageCount = ref(0)
const publishFareTotalYuan = ref(null)
const publishRemindBeforeMinutes = ref(0)
const publishCategoryId = ref(null)
const publishLoading = ref(false)
const publishDraftId = ref(null)
const draftAutoSavedAt = ref('')
let draftAutoSaveTimer = null
let draftAutoSaving = false
const threadList = ref([])
const threadLoading = ref(false)
const showThread = computed(() => richRemark.value && !!detail.value?.id)
const threadTitle = computed(() => {
  const plural = ticket.labelPlural || ticket.label || '回复'
  return `${plural}（${threadList.value.length}）`
})

async function loadThread(itemId) {
  if (!richRemark.value || !itemId) {
    threadList.value = []
    return
  }
  threadLoading.value = true
  try {
    const res = await http.get(`/api/tickets/thread/${itemId}`, { params: { page: 1, size: 50 } })
    threadList.value = res.data?.list || []
  } catch {
    threadList.value = []
  } finally {
    threadLoading.value = false
  }
}

/** §3：交易/商城/借用/预约/内容/报名主路径进独立详情页，避免抽屉交差 */
function preferArchiveItemPage() {
  if (route.query?.openApply === '1') return false
  if (hasCap('order_lines')) return true
  const home = String(APP_DELIVERED?.portalHomeStyle || '').trim()
  if (home === 'mall') return true
  const trade = String(APP_DELIVERED?.tradeSurfaceStyle || '').trim()
  if (trade) return true
  const borrow = String(APP_DELIVERED?.borrowSurfaceStyle || '').trim()
  if (borrow) return true
  const reserve = String(APP_DELIVERED?.reserveSurfaceStyle || '').trim()
  if (reserve) return true
  const content = String(APP_DELIVERED?.contentSurfaceStyle || '').trim()
  /* splitdesk 宽屏靠右侧预览，不整卡跳详情；窄屏仍走 openDetail */
  if (content === 'splitdesk') return false
  if (content) return true
  const apply = String(APP_DELIVERED?.applySurfaceStyle || '').trim()
  if (apply) return true
  const interact = String(APP_DELIVERED?.interactSurfaceStyle || '').trim()
  return !!interact
}

/** 启事板：寻物 / 招领 / 线索分色 */
function lostBoardTone(row) {
  if (applySurface.value !== 'noticeboard') return ''
  const raw = String(row?.lostCategory || row?.categoryName || row?.title || '').trim()
  if (/招领|拾获|待领/.test(raw)) return 'claim'
  if (/线索|目击|见过/.test(raw)) return 'clue'
  if (/寻物|丢失|寻找|走失/.test(raw)) return 'find'
  return 'find'
}

/** 床位色块：有余量=可申请，0=已占，紧张=保留感 */
function borrowBedTone(row) {
  if (borrowSurface.value !== 'bedblocks') return ''
  if (!stockOk(row)) return 'busy'
  if (stockTight(row)) return 'hold'
  return 'free'
}

/** 房态格：同床位逻辑，空/住/紧张 */
function reserveRoomTone(row) {
  if (reserveSurface.value !== 'roomstate') return ''
  if (!stockOk(row)) return 'busy'
  if (stockTight(row)) return 'hold'
  return 'free'
}

async function openDetail(row) {
  if (row?.id && preferArchiveItemPage()) {
    router.push({ path: `/archive/item/${row.id}` })
    return
  }
  detail.value = row
  detailVisible.value = true
  threadList.value = []
  logList.value = []
  itemReviews.value = []
  itemGoodRate.value = null
  itemQaList.value = []
  itemQaDraft.value = ''
  stockNotifySubscribed.value = false
  itemComments.value = []
  itemCommentDraft.value = ''
  clueList.value = []
  clueForm.guestName = ''
  clueForm.guestContact = ''
  clueForm.type = 'clue'
  clueForm.content = ''
  unlockPassword.value = ''
  seriesPrev.value = null
  seriesNext.value = null
  resetLogForm()
  if (!row?.id) return
  try {
    const res = await http.get(`/api/archive/${row.id}`)
    if (res.data) detail.value = { ...row, ...res.data }
  } catch { /* keep list row */ }
  await loadSeriesNeighbors(row.id)
  await loadEpisodes(row.id)
  await loadLotteryResult(row.id)
  await loadThread(row.id)
  if (logOn.value && isLoggedIn()) await loadLogs(row.id)
  if (browseOn.value && isLoggedIn()) {
    try {
      await touchBrowseHistory(row.id)
    } catch { /* ignore */ }
  }
  if (reviewOn.value) {
    try {
      const rr = await http.get(`/api/order-reviews/by-item/${row.id}`, { params: { page: 1, size: 20 } })
      itemReviews.value = rr.data?.list || []
      itemGoodRate.value = rr.data?.goodRate ?? null
    } catch {
      itemReviews.value = []
      itemGoodRate.value = null
    }
  }
  if (itemQaOn.value) {
    await loadItemQa(row.id)
  }
  if (stockNotifyOn.value && isLoggedIn() && !stockOk(detail.value || row)) {
    try {
      const sr = await http.get('/api/stock-notify/status', { params: { itemId: row.id } })
      stockNotifySubscribed.value = !!sr.data?.subscribed
    } catch { /* ignore */ }
  }
  if (itemCommentOn.value) {
    await loadItemComments(row.id)
  }
  if (lostClueOn.value) {
    await loadClues(row.id)
  }
}

async function loadItemQa(itemId) {
  if (!itemQaOn.value || !itemId) {
    itemQaList.value = []
    return
  }
  try {
    const res = await http.get('/api/guestbook', { params: { itemId, page: 1, size: 20 } })
    itemQaList.value = res.data?.list || []
  } catch {
    itemQaList.value = []
  }
}

async function submitItemQa() {
  if (!detail.value?.id) return
  if (!requireLogin(router)) return
  const body = (itemQaDraft.value || '').trim()
  if (!body) {
    ElMessage.warning('请填写问题')
    return
  }
  itemQaSubmitting.value = true
  try {
    await http.post('/api/guestbook', { body, itemId: detail.value.id })
    ElMessage.success('已提交')
    itemQaDraft.value = ''
    await loadItemQa(detail.value.id)
  } finally {
    itemQaSubmitting.value = false
  }
}

async function subscribeStockNotify(row) {
  if (!row?.id) return
  if (!requireLogin(router)) return
  stockNotifyLoading.value = true
  try {
    await http.post('/api/stock-notify', { itemId: row.id })
    stockNotifySubscribed.value = true
    ElMessage.success(browseLabels.value.stockNotifyDoneLabel || '已登记到货提醒')
  } finally {
    stockNotifyLoading.value = false
  }
}

async function loadClues(itemId) {
  if (!lostClueOn.value || !itemId) {
    clueList.value = []
    return
  }
  clueLoading.value = true
  try {
    const res = await http.get('/api/lost/message', { params: { lostItemId: itemId } })
    clueList.value = res.data || []
  } catch {
    clueList.value = []
  } finally {
    clueLoading.value = false
  }
}

async function submitClue() {
  if (!detail.value?.id) return
  const content = (clueForm.content || '').trim()
  if (!content) {
    ElMessage.warning('请填写留言内容')
    return
  }
  if (isGuest.value && !(clueForm.guestName || '').trim()) {
    ElMessage.warning('游客请填写称呼')
    return
  }
  clueSubmitting.value = true
  try {
    await http.post('/api/lost/message', {
      lostItemId: detail.value.id,
      guestName: clueForm.guestName,
      guestContact: clueForm.guestContact,
      content,
      type: clueForm.type || 'clue',
    })
    ElMessage.success('已发表')
    clueForm.content = ''
    await loadClues(detail.value.id)
  } finally {
    clueSubmitting.value = false
  }
}

async function loadItemComments(itemId) {
  if (!itemCommentOn.value || !itemId) {
    itemComments.value = []
    return
  }
  itemCommentLoading.value = true
  try {
    const res = await http.get(`/api/item-comments/by-item/${itemId}`, { params: { page: 1, size: 50 } })
    itemComments.value = res.data?.list || []
  } catch {
    itemComments.value = []
  } finally {
    itemCommentLoading.value = false
  }
}

async function submitItemComment() {
  if (!itemCommentOn.value || isGuest.value || !detail.value?.id) {
    requireLogin(router)
    return
  }
  const text = String(itemCommentDraft.value || '').trim()
  if (!text) {
    ElMessage.warning('请填写评论内容')
    return
  }
  itemCommentSubmitting.value = true
  try {
    await http.post('/api/item-comments', {
      itemId: detail.value.id,
      body: text,
      followersOnly: followersOnlyCommentOn.value ? !!itemCommentFollowersOnly.value : false,
    })
    itemCommentDraft.value = ''
    itemCommentFollowersOnly.value = false
    ElMessage.success('已发表')
    await loadItemComments(detail.value.id)
  } catch (e) {
    ElMessage.error(e?.response?.data?.message || '发表失败')
  } finally {
    itemCommentSubmitting.value = false
  }
}

function followBtnLabel(username) {
  if (followingUsers.value.has(username)) {
    return browseLabels.value.unfollowUserLabel || '取消关注'
  }
  return browseLabels.value.followUserLabel || '关注作者'
}

async function toggleFollowUser(followee) {
  if (!requireLogin(router) || !followee) return
  const on = followingUsers.value.has(followee)
  try {
    if (on) {
      await http.delete('/api/user-follow', { params: { followee } })
      const next = new Set(followingUsers.value)
      next.delete(followee)
      followingUsers.value = next
      ElMessage.success(
        browseLabels.value.datingUnfollowDone
          || browseLabels.value.unfollowUserLabel
          || '已取消关注',
      )
    } else {
      await http.post('/api/user-follow', { followee })
      const next = new Set(followingUsers.value)
      next.add(followee)
      followingUsers.value = next
      ElMessage.success(
        browseLabels.value.datingFollowDone
          || browseLabels.value.followUserLabel
          || '已关注',
      )
    }
  } catch (e) {
    ElMessage.error(e?.response?.data?.message || e?.message || '操作失败')
  }
}

async function fetchSuggest(query, cb) {
  const q = String(query || '').trim()
  if (!q) {
    cb([])
    return
  }
  try {
    const res = await http.get('/api/archive/suggest', { params: { q, limit: 8 } })
    const list = Array.isArray(res.data) ? res.data : []
    cb(list.map((x) => ({ value: x.title || x.value, id: x.id })))
  } catch {
    cb([])
  }
}

function onSuggestSelect(item) {
  keyword.value = item?.value || ''
  load()
}

function applyHot(w) {
  keyword.value = String(w || '')
  load()
}

async function onAttach(opt) {
  const fd = new FormData()
  fd.append('file', opt.file)
  const res = await http.post('/api/upload', fd)
  applyAttachUrl.value = res.data.url
  ElMessage.success('附件已上传')
}

async function loadCats() {
  const res = await http.get('/api/categories')
  categories.value = res.data || res || []
}

async function loadTags() {
  if (!tagFilter.value) return
  try {
    const res = await http.get('/api/tags')
    tags.value = res.data || res || []
  } catch {
    tags.value = []
  }
}

async function load() {
  const pageSize = isGuest.value ? guestTeaserLimit() : size.value
  let url = '/api/archive'
  let params = {
    page: isGuest.value ? 1 : page.value,
    size: pageSize,
    keyword: keyword.value || undefined,
    categoryId: multiCategory.value ? undefined : (categoryId.value || undefined),
    categoryIds:
      multiCategory.value && categoryIds.value?.length
        ? categoryIds.value.join(',')
        : undefined,
    tagIds: tagIds.value?.length ? tagIds.value.join(',') : undefined,
    artist: artistAlbumFilterOn.value ? (artistFilter.value || undefined) : undefined,
    album: artistAlbumFilterOn.value ? (albumFilter.value || undefined) : undefined,
    city: datingIdealFilterOn.value ? (datingCityFilter.value || undefined) : undefined,
    ageMin: datingIdealFilterOn.value && datingAgeMinFilter.value
      ? Number(datingAgeMinFilter.value)
      : undefined,
    ageMax: datingIdealFilterOn.value && datingAgeMaxFilter.value
      ? Number(datingAgeMaxFilter.value)
      : undefined,
    priceMin:
      priceRangeFilterOn.value && priceMinFilter.value != null && priceMinFilter.value !== ''
        ? Number(priceMinFilter.value)
        : undefined,
    priceMax:
      priceRangeFilterOn.value && priceMaxFilter.value != null && priceMaxFilter.value !== ''
        ? Number(priceMaxFilter.value)
        : undefined,
  }
  if (hotMode.value && hotRankOn.value) {
    url = '/api/archive/hot'
    params = {
      page: isGuest.value ? 1 : page.value,
      size: pageSize,
      sortBy: downloadCountOn.value
        ? 'downloadCount'
        : (hotByPlayOn.value ? 'playCount' : undefined),
    }
  } else if (authorPageOn.value && (authorFilter.value || '').trim()) {
    url = '/api/archive/by-author'
    params = {
      page: isGuest.value ? 1 : page.value,
      size: pageSize,
      username: authorFilter.value.trim(),
    }
  } else if (archiveYearMonthOn.value && archiveYear.value) {
    params.year = archiveYear.value
    if (archiveMonth.value) params.month = archiveMonth.value
  }
  const res = await http.get(url, { params })
  let rows = res.data.list || []
  // 本人件/本人课：登录后按手机/学号软筛（访客仍看 teaser 全量）
  if (filterByOwnerToken.value && !isGuest.value) {
    try {
      const me = await http.get('/api/profile')
      const token = ownerTokenFromProfile(me.data || {}, ownerTokenSource.value)
      rows = filterArchiveByOwnerToken(rows, token, { strict: ownerTokenStrict.value })
    } catch {
      if (ownerTokenStrict.value) rows = []
    }
  }
  if (blindBoxOn.value && prizeIds.value.size) {
    rows = rows.filter((r) => !prizeIds.value.has(Number(r.id)))
  }
  if (collegeFilterOn.value && (collegeFilter.value || '').trim()) {
    const want = collegeFilter.value.trim()
    rows = rows.filter((r) => String(r?.college || '').trim() === want)
  }
  list.value = rows
  total.value = (
    (filterByOwnerToken.value && !isGuest.value) || (collegeFilterOn.value && (collegeFilter.value || '').trim())
  )
    ? rows.length
    : res.data.total
}

async function loadFavIds() {
  if (!favOn.value || isGuest.value) {
    favIds.value = []
    return
  }
  try {
    const res = await http.get('/api/favorites/ids')
    favIds.value = (res.data?.ids || []).map(Number)
  } catch {
    favIds.value = []
  }
}

async function loadLikeIds() {
  if (!likeOn.value || isGuest.value) {
    likeIds.value = []
    return
  }
  try {
    const res = await http.get('/api/likes/ids')
    likeIds.value = (res.data?.ids || []).map(Number)
  } catch {
    likeIds.value = []
  }
}


function productSpecText(row) {
  if (!row) return ''
  const src = getSchema()?.entities?.archive?.productSpecSource || 'specNote'
  if (src === 'isbn') return String(row.isbn || '').trim()
  return String(row.specNote || row.isbn || '').trim()
}

function likeCountText(row) {
  const n = Number(row?.likeCount)
  if (!Number.isFinite(n) || n <= 0) return ''
  return ` ${n}`
}

async function toggleLike(row) {
  if (!requireLogin(router)) return
  const res = await http.post(`/api/likes/${row.id}/toggle`)
  const on = !!res.data?.liked
  likePulseId.value = row.id
  setTimeout(() => { if (likePulseId.value === row.id) likePulseId.value = null }, 360)
  if (on) {
    if (!likeIds.value.includes(row.id)) likeIds.value = [...likeIds.value, row.id]
    row.likeCount = Number(row.likeCount || 0) + 1
    if (detail.value?.id === row.id) detail.value.likeCount = row.likeCount
    ElMessage.success(likedVerb.value)
  } else {
    likeIds.value = likeIds.value.filter((x) => x !== row.id)
    row.likeCount = Math.max(0, Number(row.likeCount || 0) - 1)
    if (detail.value?.id === row.id) detail.value.likeCount = row.likeCount
    ElMessage.success('已取消')
  }
}

function openReport(row, targetType = 'archive') {
  if (!requireLogin(router)) return
  reportRow.value = row
  if (targetType === 'ticket') reportTargetType.value = 'ticket'
  else if (targetType === 'comment') reportTargetType.value = 'comment'
  else reportTargetType.value = 'archive'
  reportReason.value = ''
  reportReasonCode.value = ''
  reportVisible.value = true
}

async function submitReport() {
  const detailNote = reportReason.value.trim()
  const code = String(reportReasonCode.value || '').trim()
  let reason = detailNote
  if (reportReasonDictOn.value) {
    if (!code) {
      ElMessage.warning(browseLabels.value.reportReasonRequired || '请选择举报原因')
      return
    }
    reason = detailNote ? `${code}：${detailNote}` : code
  } else if (!reason) {
    ElMessage.warning('请填写举报理由')
    return
  }
  reportSubmitting.value = true
  try {
    await http.post('/api/content-reports', {
      targetType: reportTargetType.value,
      targetId: reportRow.value?.id,
      reason,
    })
    ElMessage.success(
      reportTargetType.value === 'comment'
        ? (browseLabels.value.commentReportDone || '已提交评论举报')
        : '已提交举报，等待处理',
    )
    if (reportTargetType.value === 'archive' && reportRow.value?.id != null) {
      const next = new Set(reportedIds.value)
      next.add(Number(reportRow.value.id))
      reportedIds.value = next
    }
    reportVisible.value = false
  } catch (e) {
    ElMessage.error(e?.response?.data?.message || e?.message || '提交失败')
  } finally {
    reportSubmitting.value = false
  }
}

async function toggleFav(row) {
  if (!requireLogin(router)) return
  const res = await toggleFavorite(row.id)
  const on = !!res.data?.favorited
  favPulseId.value = row.id
  setTimeout(() => { if (favPulseId.value === row.id) favPulseId.value = null }, 360)
  if (on) {
    if (!favIds.value.includes(row.id)) favIds.value = [...favIds.value, row.id]
    ElMessage.success(favoritedVerb.value)
  } else {
    favIds.value = favIds.value.filter((x) => x !== row.id)
    ElMessage.success(getSchema()?.labels?.favoritesCancelLabel || '已取消收藏')
  }
}

async function onPrimary(row) {
  applyParentTicketId.value = null
  if (!requireLogin(router)) return
  if (isSeatSelectMode.value) {
    router.push(`/seats/map/${row.id}`)
    return
  }
  if (isOrderMode.value) {
    if (hasCap('purchase_gate') && Number(row.needPermit) === 1) {
      const chk = await http.get('/api/purchase-permits/check', { params: { itemId: row.id, qty: 1 } })
      if (!chk.data?.approved) {
        ElMessage.warning(chk.data?.message || '需审核通过后才能购买')
        router.push({ path: '/permits', query: { itemId: String(row.id) } })
        return
      }
    }
    await upsertCart(row.id, 1)
    ElMessage.success(`已加入${cartLabel.value}`)
    return
  }
  if (isSlotMode.value) {
    router.push({
      path: '/slots',
      query: {
        itemId: row.id,
        title: row.title || '',
        price: row.author != null && row.author !== '' ? String(row.author) : '',
      },
    })
    return
  }
  // 请假/归寝：主路径在「我的*」填单，档案页不发起申请
  if (applyFromList.value) {
    const menus = getSchema()?.menus?.user || []
    const myLab = menus.find((m) => m?.key === 'my_tickets')?.label
      || ticket.labelPlural
      || ticket.label
      || '我的申请'
    ElMessage.info(`请到「${myLab}」提交`)
    router.push('/tickets')
    return
  }
  await apply(row)
}

async function onRecommendApply(row) {
  if (favOn.value && !showPrimaryApply.value) {
    if (!requireLogin(router)) return
    await toggleFav(row)
    return
  }
  await onPrimary(row)
}

function clearDraftAutoSaveTimer() {
  if (draftAutoSaveTimer) {
    clearTimeout(draftAutoSaveTimer)
    draftAutoSaveTimer = null
  }
}

function openPublish() {
  if (!requireLogin(router)) return
  clearDraftAutoSaveTimer()
  publishTitle.value = ''
  publishAuthor.value = ''
  publishBody.value = ''
  publishStock.value = publishShowStock.value ? 2 : 1
  publishStartAt.value = ''
  publishStartCampus.value = ''
  publishEndCampus.value = ''
  publishViaPoints.value = ''
  publishShareNote.value = ''
  publishPrefNote.value = ''
  publishLuggageCount.value = 0
  publishFareTotalYuan.value = null
  publishRemindBeforeMinutes.value = 0
  publishCategoryId.value = categories.value[0]?.id || null
  publishOriginKind.value = 'original'
  publishAccessPassword.value = ''
  publishDraftId.value = null
  draftAutoSavedAt.value = ''
  publishVisible.value = true
}

function scheduleDraftAutoSave() {
  if (!draftAutoSaveOn.value || !publishVisible.value) return
  clearDraftAutoSaveTimer()
  draftAutoSaveTimer = setTimeout(() => {
    silentAutoSaveDraft()
  }, 2000)
}

async function silentAutoSaveDraft() {
  if (!draftAutoSaveOn.value || !publishVisible.value || draftAutoSaving || publishLoading.value) return
  const title = publishTitle.value.trim()
  if (!title || !publishCategoryId.value) return
  let isbn = ''
  if (publishUsesRichBody.value) {
    isbn = sanitizeHtml(publishBody.value || '')
  } else {
    isbn = (publishBody.value || '').trim()
  }
  draftAutoSaving = true
  try {
    const body = {
      title,
      categoryId: publishCategoryId.value,
      isbn,
      draft: true,
    }
    if (publishDraftId.value) body.id = publishDraftId.value
    if (originKindOn.value) body.originKind = publishOriginKind.value
    if (accessPasswordOn.value && (publishAccessPassword.value || '').trim()) {
      body.accessPassword = publishAccessPassword.value.trim()
    }
    const res = await http.post('/api/archive/publish', body)
    const data = res.data?.data || res.data || {}
    if (data.id) publishDraftId.value = data.id
    const now = new Date()
    draftAutoSavedAt.value = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}`
  } catch {
    /* 自动保存失败不打扰；用户仍可手点存草稿 */
  } finally {
    draftAutoSaving = false
  }
}

watch(
  [publishTitle, publishBody, publishCategoryId, publishVisible],
  () => {
    if (publishVisible.value) scheduleDraftAutoSave()
    else clearDraftAutoSaveTimer()
  },
)

onUnmounted(() => {
  clearDraftAutoSaveTimer()
  if (splitNarrowMq) {
    splitNarrowMq.removeEventListener('change', syncSplitNarrow)
    splitNarrowMq = null
  }
})

async function submitPublish(asDraft = false) {
  const title = publishTitle.value.trim()
  if (!title) {
    ElMessage.warning(`请填写${fieldLabel('title', '名称')}`)
    return
  }
  if (!asDraft && publishShowAuthor.value && !publishAuthor.value.trim()) {
    ElMessage.warning(`请填写${fieldLabel('author', '联系人')}`)
    return
  }
  if (!publishCategoryId.value) {
    ElMessage.warning(`请选择${fieldLabel('category', '分类')}`)
    return
  }
  if (!asDraft && publishShowStock.value) {
    const n = Number(publishStock.value) || 0
    if (n < 1) {
      ElMessage.warning(`${fieldLabel('stock', '余座')}至少为 1`)
      return
    }
  }
  if (!asDraft && publishShowStartAt.value && !String(publishStartAt.value || '').trim()) {
    ElMessage.warning(`请填写${fieldLabel('startAt', '出发时间')}`)
    return
  }
  if (!asDraft && carpoolCampusDictOn.value) {
    if (!String(publishStartCampus.value || '').trim() || !String(publishEndCampus.value || '').trim()) {
      ElMessage.warning('请选择出发校区与到达校区')
      return
    }
  }
  let isbn = ''
  if (publishUsesRichBody.value) {
    isbn = sanitizeHtml(publishBody.value || '')
    if (!asDraft && !plainFromHtml(isbn).trim()) {
      ElMessage.warning(`请填写${fieldLabel('isbn', '正文')}`)
      return
    }
  } else {
    isbn = (publishBody.value || '').trim()
    if (!asDraft && !isbn) {
      ElMessage.warning(`请填写${fieldLabel('isbn', '备注')}`)
      return
    }
  }
  clearDraftAutoSaveTimer()
  publishLoading.value = true
  try {
    const body = {
      title,
      categoryId: publishCategoryId.value,
      isbn,
    }
    if (asDraft) {
      body.draft = true
      if (publishDraftId.value) body.id = publishDraftId.value
    }
    if (publishShowAuthor.value) body.author = publishAuthor.value.trim()
    if (!asDraft && publishShowStock.value) body.stock = Number(publishStock.value) || 1
    if (!asDraft && publishShowStartAt.value) body.startAt = String(publishStartAt.value).trim()
    if (carpoolCampusDictOn.value) {
      body.startCampus = String(publishStartCampus.value || '').trim()
      body.endCampus = String(publishEndCampus.value || '').trim()
    }
    if (carpoolViaPointsOn.value && String(publishViaPoints.value || '').trim()) {
      body.viaPoints = String(publishViaPoints.value).trim()
    }
    if (carpoolShareNoteOn.value && String(publishShareNote.value || '').trim()) {
      body.shareNote = String(publishShareNote.value).trim()
    }
    if (carpoolPrefNoteOn.value && String(publishPrefNote.value || '').trim()) {
      body.prefNote = String(publishPrefNote.value).trim()
    }
    if (carpoolLuggageOn.value) body.luggageCount = Number(publishLuggageCount.value) || 0
    if (carpoolAaCalcOn.value && publishFareTotalYuan.value != null) {
      body.fareTotalYuan = Number(publishFareTotalYuan.value)
    }
    if (carpoolDepartRemindOn.value) {
      body.remindBeforeMinutes = Number(publishRemindBeforeMinutes.value) || 0
    }
    if (originKindOn.value) body.originKind = publishOriginKind.value
    if (accessPasswordOn.value && (publishAccessPassword.value || '').trim()) {
      body.accessPassword = publishAccessPassword.value.trim()
    }
    const res = await http.post('/api/archive/publish', body)
    const data = res.data?.data || res.data || {}
    if (asDraft) {
      if (data.id) publishDraftId.value = data.id
      ElMessage.success('已存草稿，可在「我的」里发布')
    } else {
      const review = !!archive.publishReview
      ElMessage.success(
        review
          ? '已提交审核，通过后公开展示'
          : publishUsesRichBody.value || publishShowStock.value
            ? '已发布'
            : '已登记',
      )
    }
    publishVisible.value = false
    publishDraftId.value = null
    draftAutoSavedAt.value = ''
    await load()
    recRef.value?.reload?.()
  } catch (e) {
    const msg = String(e?.message || e?.response?.data?.message || '')
    if (/禁言|发帖已达上限/.test(msg)) {
      /* http 已提示或下方兜底 */
      if (/发帖已达上限/.test(msg)) ElMessage.warning(msg)
    } else if (msg && !e?.code) {
      ElMessage.error(msg)
    }
  } finally {
    publishLoading.value = false
  }
}

async function apply(row) {
  if (lockedOn.value && Number(row?.locked) === 1) {
    ElMessage.warning(browseLabels.value.lockedReplyBlocked || '该帖已锁定，暂时不能回复')
    return
  }
  if (matchProfileRoom.value) {
    try {
      const me = await http.get('/api/profile')
      const extras = me.data?.extras || {}
      const opts = matchProfileOpts.value
      const building = (extras[opts.buildingKey] || '').trim()
      const room = (extras[opts.roomKey] || '').trim()
      if (!building || !room) {
        ElMessage.warning(matchProfileNeedMessage.value)
        return
      }
      const itemBuilding = row?.[opts.buildingField]
      const itemRoom = row?.[opts.roomField]
      if (!profileRoomMatches(building, room, itemBuilding, itemRoom, opts.looseBuilding)) {
        ElMessage.warning(matchProfileDenyMessage.value)
        return
      }
    } catch {
      ElMessage.warning('无法读取个人资料，请重新登录后再试')
      return
    }
  }
  applyRow.value = row
  conflictTip.value = ''
  applyRemark.value = ''
  applyAttachUrl.value = ''
  applyQty.value = 1
  applyDueAt.value = ''
  applyAmount.value = null
  applyPeriod.value = null
  applyChannel.value = ''
  applyMeetIntent.value = ''
  applyNextFollow.value = ''
  applyCheckinCode.value = ''
  applyAnonymous.value = false
  Object.keys(applyDimScores).forEach((k) => delete applyDimScores[k])
  for (const d of ratingDims.value) {
    applyDimScores[d.key] = 5
  }
  if (needApplyDialog.value) {
    applyVisible.value = true
    return
  }
  await ElMessageBox.confirm(
    `确认${verbs.value.apply || '申请'}「${row.title}」？`,
    verbs.value.apply || '申请',
  )
  await submitApply()
}

function dueDisabledDate(date) {
  const start = new Date()
  start.setHours(0, 0, 0, 0)
  const max = new Date(start)
  max.setDate(max.getDate() + 90)
  return date.getTime() < start.getTime() || date.getTime() > max.getTime()
}

async function submitApply() {
  if (!applyRow.value) return
  let remark = ''
  if (richRemark.value) {
    remark = sanitizeHtml(applyRemark.value || '')
    if (!plainFromHtml(remark)) {
      ElMessage.warning('请填写内容')
      return
    }
  } else if (requireRemark.value) {
    remark = (applyRemark.value || '').trim()
    if (!remark) {
      ElMessage.warning(
        interactThicken.value.mutualTeamRemarkRequired
          ? teamRemarkRequired.value
          : `请填写${remarkLabel.value}`,
      )
      return
    }
  }
  if (requireAttach.value && !applyAttachUrl.value) {
    ElMessage.warning('请上传证明附件')
    return
  }
  if (requireMaterial.value) {
    const miss = matRef.value?.missingTitle?.() || ''
    if (miss) {
      ElMessage.warning(`请上传必传材料：${miss}`)
      return
    }
  }
  if (pickLoanPeriod.value && !applyDueAt.value) {
    ElMessage.warning(`请选择${dueLabel.value}`)
    return
  }
  if (collectAmount.value) {
    const amt = Number(applyAmount.value)
    if (!(amt > 0)) {
      ElMessage.warning(`请填写${fineLabel.value}`)
      return
    }
  }
  if (pickDateRange.value) {
    const range = applyPeriod.value
    if (!Array.isArray(range) || range.length < 2 || !range[0] || !range[1]) {
      ElMessage.warning('请选择起止日期')
      return
    }
  }
  if (allowQty.value) {
    const n = Number(applyQty.value) || 0
    if (n < 1) {
      ElMessage.warning('数量至少为 1')
      return
    }
    if (n > qtyMax.value) {
      ElMessage.warning(`数量不能超过 ${qtyMax.value}`)
      return
    }
  }
  if (checkinOnApply.value) {
    if (!applyCheckinCode.value.trim()) {
      ElMessage.warning(`请输入${checkinLabel.value}码`)
      return
    }
  }
  let dimsPayload = null
  if (rateOnApply.value) {
    dimsPayload = {}
    for (const d of ratingDims.value) {
      const v = applyDimScores[d.key]
      if (!v || v < 1) {
        ElMessage.warning(`请完成「${d.label}」评分`)
        return
      }
      dimsPayload[d.key] = v
    }
  }
  if (datingMeetIntentOn.value && !applyMeetIntent.value) {
    ElMessage.warning(browseLabels.value.meetIntentRequired || '请选择见面意向')
    return
  }
  applyLoading.value = true
  try {
    const body = {
      itemId: applyRow.value.id,
      remark,
      attachUrl: applyAttachUrl.value || undefined,
    }
    if (applyParentTicketId.value) body.parentTicketId = applyParentTicketId.value
    if (requireMaterial.value && matRef.value) body.materials = matRef.value.payload()
    if (allowQty.value) body.qty = Number(applyQty.value) || 1
    if (pickLoanPeriod.value) body.dueAt = applyDueAt.value
    if (collectAmount.value) body.fineYuan = Number(applyAmount.value)
    if (pickDateRange.value && Array.isArray(applyPeriod.value)) {
      body.periodStart = applyPeriod.value[0]
      body.periodEnd = applyPeriod.value[1]
    }
    if (isCrm.value) {
      if (applyChannel.value) body.contactChannel = applyChannel.value
      if (applyNextFollow.value) body.nextFollowAt = applyNextFollow.value
    }
    if (datingMeetIntentOn.value) body.meetIntent = applyMeetIntent.value
    if (checkinOnApply.value) body.checkinCode = applyCheckinCode.value.trim()
    if (dimsPayload) {
      body.dims = dimsPayload
      if (allowAnonymousRating.value) body.anonymous = !!applyAnonymous.value
    }
    const { data } = await http.post('/api/tickets/apply', body)
    const st = data?.status || data?.data?.status
    let okMsg
    if (st === 'held') {
      okMsg = (getSchema()?.labels?.bookHoldOkMessage) || '暂无库存，已加入预约队列'
    } else if (st === 'waitlisted') {
      const rank = data?.waitlistRank || data?.waitlistPos || data?.queueNo
      okMsg = rank
        ? `名额已满，已加入候补（约第 ${rank} 位）`
        : ((getSchema()?.labels?.waitlistOkMessage) || '名额已满，已加入候补队列')
    } else if (checkinOnApply.value) {
      okMsg = '已签到'
    } else {
      okMsg = autoApprove.value ? `已${verbs.value.apply || '提交'}` : '已提交，等待审核'
    }
    ElMessage.success(okMsg)
    applyVisible.value = false
    applyParentTicketId.value = null
    if (detailVisible.value && applyRow.value?.id) {
      await loadThread(applyRow.value.id)
    }
    if (!richRemark.value) detailVisible.value = false
    recRef.value?.reload?.()
  } catch (e) {
    const msg = String(e?.message || e?.response?.data?.message || '')
    if (/冲突|时段重叠|时间冲突/.test(msg)) {
      conflictTip.value = msg.includes('冲突') ? msg : `时段冲突：${msg}`
      ElMessage.warning(conflictTip.value)
    }
  } finally {
    applyLoading.value = false
  }
}

onMounted(async () => {
  if (typeof window !== 'undefined' && window.matchMedia) {
    splitNarrowMq = window.matchMedia('(max-width: 900px)')
    syncSplitNarrow()
    splitNarrowMq.addEventListener('change', syncSplitNarrow)
  }
  const qWord = route.query?.q
  if (qWord != null && String(qWord).trim() !== '') {
    keyword.value = String(qWord).trim()
  }
  const qCat = route.query?.categoryId
  if (qCat != null && String(qCat).trim() !== '') {
    const n = Number(qCat)
    categoryId.value = Number.isFinite(n) ? n : qCat
  }
  const qAuthor = route.query?.author
  if (qAuthor != null && String(qAuthor).trim() !== '') {
    authorFilter.value = String(qAuthor).trim()
  }
  await loadBlindBoxes()
  await loadCats()
  await loadTags()
  await loadFriendLinks()
  await load()
  await refreshFollowStatus()
  await loadMySchedule()
  await loadFavIds()
  await loadLikeIds()
  await openHighlightFromRoute()
})

watch(
  () => route.query?.q,
  async (q, prev) => {
    if (q === prev) return
    keyword.value = q == null ? '' : String(q).trim()
    page.value = 1
    await load()
  },
)

watch(
  () => [route.query?.highlight, route.query?.categoryId, route.query?.openApply],
  async ([hl, cat], [prevHl, prevCat]) => {
    if (cat !== prevCat && cat != null && String(cat).trim() !== '') {
      const n = Number(cat)
      categoryId.value = Number.isFinite(n) ? n : cat
      await load()
    }
    if (hl !== prevHl || route.query?.openApply === '1') await openHighlightFromRoute()
  },
)

/** 门户新品 / 足迹等带 ?highlight=id 进入时打开详情；openApply=1 时直接开申请单 */
async function openHighlightFromRoute() {
  const raw = route.query?.highlight
  if (raw == null || String(raw).trim() === '') return
  const id = Number(raw)
  if (!Number.isFinite(id) || id <= 0) return
  let row = list.value.find((x) => Number(x.id) === id)
  if (!row) {
    try {
      const res = await http.get(`/api/archive/${id}`)
      row = res.data || { id }
    } catch {
      row = { id }
    }
  }
  if (route.query?.openApply === '1') {
    await apply(row)
    const next = { ...route.query }
    delete next.openApply
    delete next.highlight
    router.replace({ path: '/archive', query: next })
    return
  }
  await openDetail(row)
}
