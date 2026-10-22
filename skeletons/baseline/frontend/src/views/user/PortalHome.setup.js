import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import http from '../../api/http'
import EmptyHint from '../../components/EmptyHint.vue'
import { APP_DELIVERED } from '../../appDelivered.js'
import {
  archiveCopy,
  formatArchiveScalar,
  getSchema,
  hasCap,
  schemaLabels,
  schemaMenus,
  ticketCopy,
} from '../../utils/domainSchema.js'
import {
  formatCountdownClock,
  secondsUntil,
  useNowTick,
} from '../../utils/useCountdown.js'
import { userMenuPath } from '../../utils/menuRoutes.js'
import { isGuestBrowseEnabled, isLoggedIn, requireLogin } from '../../utils/session.js'

const router = useRouter()
const labels = schemaLabels()
const appName = labels.appName || APP_DELIVERED.title || '业务门户'
const industrySkinHint = computed(() => String(labels.industrySkinHint || '').trim())
const lead = computed(
  () =>
    labels.portalHomeLead ||
    labels.authLead ||
    '浏览目录、处理申请，或先看公告。',
)
const loggedIn = computed(() => isLoggedIn())
const guestBrowse = computed(() => isGuestBrowseEnabled())
const homeStyle = computed(() => {
  const s = (APP_DELIVERED?.portalHomeStyle || import.meta.env.VITE_PORTAL_HOME_STYLE || 'cards')
    .toString()
    .trim()
  if (s === 'editorial' || s === 'mall') return s
  return 'cards'
})

const FLAVOR_NEWS = {
  blog: { kicker: 'NEWS & UPDATES', title: '资讯动态', claim: '记录与分享本站原创内容' },
  media: { kicker: 'NOW SHOWING', title: '本周上新', claim: '精选片库，随时开看' },
  music: { kicker: 'NEW TRACKS', title: '新歌速递', claim: '听见喜欢的声音' },
  forum: { kicker: 'COMMUNITY', title: '社区动态', claim: '文明发帖，互助交流' },
}

const newsMeta = computed(() => {
  const flavor = (APP_DELIVERED?.flavor || getSchema()?.flavor || '').toString()
  return FLAVOR_NEWS[flavor] || FLAVOR_NEWS.blog
})
const newsKicker = computed(() => labels.portalNewsKicker || newsMeta.value.kicker)
const newsTitle = computed(() => labels.portalNewsTitle || newsMeta.value.title)
const claimText = computed(
  () =>
    labels.portalHomeClaim ||
    labels.authEyebrow ||
    newsMeta.value.claim ||
    appName,
)

/** 管理端 sys_banner（slot=home）优先，预置首页横幅 垫底；与 PortalCarousel 同源 */
const apiBanners = ref([])
const banners = computed(() => {
  const baked = Array.isArray(APP_DELIVERED?.portalBanners) ? APP_DELIVERED.portalBanners : []
  const fromApi = apiBanners.value.map((b) => ({
    src: b.src || b.imageUrl || '',
    title: b.title || '',
    lead: b.lead || '',
  }))
  // 有图优先；无图但有标题的也保留（mall 纯色兜底文案）
  const merged = [...fromApi, ...baked].filter((x) => x && (x.src || x.title))
  const withSrc = merged.filter((x) => x.src)
  return withSrc.length ? withSrc : merged
})
const claimCover = computed(() => banners.value[0]?.src || APP_DELIVERED?.authHero || '')

const newsItems = ref([])

async function loadHomeBanners() {
  try {
    const res = await http.get('/api/banners', { params: { slot: 'home' } })
    apiBanners.value = Array.isArray(res.data) ? res.data : []
  } catch {
    apiBanners.value = []
  }
}

async function loadNews() {
  await loadHomeBanners()
  const covers = banners.value.map((b) => b.src).filter(Boolean)
  try {
    const res = await http.get('/api/notices', { params: { page: 1, size: 4 } })
    const rows = res.data?.list || res.data?.items || res.data || []
    const list = Array.isArray(rows) ? rows : []
    if (list.length) {
      newsItems.value = list.slice(0, 4).map((row, i) => ({
        id: row.id,
        title: row.title || '未命名',
        lead: String(row.content || row.summary || row.lead || '')
          .replace(/<[^>]+>/g, '')
          .slice(0, 72),
        cover: covers[i % Math.max(covers.length, 1)] || '',
        kind: 'notice',
      }))
      return
    }
  } catch {
    /* 访客或接口失败时用轮播文案兜底 */
  }
  newsItems.value = banners.value.slice(0, 4).map((b, i) => ({
    id: `b${i}`,
    title: b.title || '欢迎使用',
    lead: b.lead || '',
    cover: b.src || '',
    kind: 'banner',
  }))
}

const mallCategories = ref([])
const mallProducts = ref([])
const mallHot = ref([])
const mallIndex = ref(0)
let mallTimer = null
const mallFlashRows = ref([])
const flashOn = computed(() => hasCap('flash_price'))
const mallFlashTitle = computed(() => labels.mallFlashTitle || '限时特价')
const mallFlashMore = computed(() => labels.mallFlashMore || '查看更多')
const flashBadge = computed(() => labels.flashPriceBadge || '活动价')
const flashCountdownLabel = computed(() => labels.flashCountdownLabel || '距结束')
const flashCountdownEnded = computed(() => labels.flashCountdownEnded || '已结束')
const { nowMs } = useNowTick()

const mallFlashProducts = computed(() =>
  mallFlashRows.value.map((row) => {
    const sec = row.promoEnd ? secondsUntil(row.promoEnd, nowMs.value) : null
    let countdown = ''
    if (sec != null) {
      countdown = sec <= 0 ? flashCountdownEnded.value : `${flashCountdownLabel.value} ${formatCountdownClock(sec)}`
    }
    const promo = Number(row.promoPrice)
    const list = Number(row.author)
    return {
      id: row.id,
      title: row.title || '未命名',
      lead: mallLeadText(row),
      price:
        Number.isFinite(promo) && promo > 0
          ? `¥${promo.toFixed(2)}`
          : mallPriceText(row),
      listPrice:
        Number.isFinite(list) && list > 0 && Number.isFinite(promo) && promo > 0 && list > promo
          ? `¥${list.toFixed(2)}`
          : '',
      meta: mallMetaText(row),
      shop: String(row.shopName || row.shop_name || '').trim(),
      cover: row.coverUrl || '',
      letter: String(row.title || '?').slice(0, 1),
      countdown,
    }
  }),
)

const mallSlides = computed(() => {
  const fromApi = banners.value.filter((b) => b && (b.src || b.title))
  if (fromApi.length) return fromApi
  const hero = APP_DELIVERED?.authHero
  if (hero) return [{ src: hero, title: appName, lead: lead.value }]
  return [{ src: '', title: appName, lead: lead.value }]
})
const mallHero = computed(() => mallSlides.value[mallIndex.value] || mallSlides.value[0] || null)
const mallBannerSrc = computed(() => mallHero.value?.src || '')
const mallBannerTitle = computed(() => mallHero.value?.title || appName)
const mallBannerLead = computed(() => mallHero.value?.lead || lead.value)
const mallBannerStyle = computed(() =>
  mallBannerSrc.value ? { backgroundImage: `url('${mallBannerSrc.value}')` } : undefined,
)

function showMallSlide(i) {
  const n = mallSlides.value.length
  if (!n) return
  mallIndex.value = ((i % n) + n) % n
}

function onMallBanner() {
  const slide = mallHero.value
  const link = String(slide?.linkUrl || slide?.href || '').trim()
  if (link.startsWith('/')) {
    router.push(link)
    return
  }
  if (slide?.itemId) {
    goProduct({ id: slide.itemId })
    return
  }
  goArchive()
}

function startMallRotate() {
  stopMallRotate()
  if (mallSlides.value.length < 2) return
  mallTimer = setInterval(() => {
    showMallSlide(mallIndex.value + 1)
  }, 4800)
}

function stopMallRotate() {
  if (mallTimer) {
    clearInterval(mallTimer)
    mallTimer = null
  }
}

function stripHtml(s) {
  return String(s || '')
    .replace(/<[^>]+>/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
}

function mallPriceText(row) {
  const fields = archiveCopy().fields || []
  const authorField = fields.find((x) => x?.key === 'author') || {
    key: 'author',
    type: 'number',
    format: 'money',
  }
  return formatArchiveScalar(authorField, row?.author, '¥ —')
}

function mallLeadText(row) {
  const note = stripHtml(row?.sellerNote || row?.seller_note)
  if (note) return note.slice(0, 48)
  const raw = stripHtml(row?.isbn)
  // 货号（如 FR-AP01）不作简介；优先分类名
  if (raw && !/^[A-Z]{1,4}-?[A-Z0-9]+$/i.test(raw) && !/^SKU[-_]/i.test(raw)) {
    return raw.slice(0, 48)
  }
  return row?.categoryName || '精选好物'
}

function mallMetaText(row) {
  const stock = Number(row?.stock)
  if (Number.isFinite(stock)) return `库存 ${stock}`
  return row?.categoryName || ''
}

function mallSalesOf(row) {
  const n = Number(row?.salesCount ?? row?.soldCount ?? row?.sales)
  return Number.isFinite(n) && n > 0 ? n : 0
}

function mapMallCard(row) {
  const sales = mallSalesOf(row)
  return {
    id: row.id,
    title: row.title || '未命名',
    lead: mallLeadText(row),
    price: mallPriceText(row),
    meta: mallMetaText(row),
    shop: String(row.shopName || row.shop_name || '').trim(),
    cover: row.coverUrl || '',
    letter: String(row.title || '?').slice(0, 1),
    sales,
    salesText: sales > 0 ? `累计销量: ${sales}` : '',
  }
}

/** 门户侧栏只挂品类维；用途/目标等其它维留给目录筛选，避免扁列表长得像子菜单。 */
function mallRailCategories(raw) {
  const rows = (Array.isArray(raw) ? raw : []).filter((c) => c && c.id != null)
  const hasDim = rows.some((c) => String(c.dimension || '').trim())
  const rail = hasDim
    ? rows.filter((c) => {
        const d = String(c.dimension || '').trim()
        return !d || d === '品类'
      })
    : rows
  const list = (rail.length ? rail : rows).slice(0, 12)
  return list.map((c) => ({ id: c.id, name: c.name || '分类' }))
}

async function loadMall() {
  await loadHomeBanners()
  try {
    const catRes = await http.get('/api/categories')
    const cats = catRes.data || catRes || []
    mallCategories.value = mallRailCategories(cats)
  } catch {
    mallCategories.value = []
  }
  try {
    const res = await http.get('/api/archive', { params: { page: 1, size: 12 } })
    const rows = res.data?.list || res.data?.items || res.data || []
    const list = (Array.isArray(rows) ? rows : []).map(mapMallCard)
    mallProducts.value = list.slice(0, 4)
    const bySales = [...list].sort((a, b) => b.sales - a.sales || String(a.title).localeCompare(String(b.title)))
    const newIds = new Set(mallProducts.value.map((x) => x.id))
    const hotPrefer = bySales.filter((x) => !newIds.has(x.id))
    mallHot.value = (hotPrefer.length >= 4 ? hotPrefer : bySales).slice(0, 4)
  } catch {
    mallProducts.value = []
    mallHot.value = []
  }
  mallFlashRows.value = []
  if (!flashOn.value) return
  try {
    const res = await http.get('/api/archive', {
      params: { page: 1, size: 4, promoActive: true },
    })
    const rows = res.data?.list || res.data?.items || res.data || []
    mallFlashRows.value = (Array.isArray(rows) ? rows : []).slice(0, 4)
  } catch {
    mallFlashRows.value = []
  }
}

function goArchive() {
  router.push('/archive')
}

function goCategory(cat) {
  if (!cat?.id) {
    goArchive()
    return
  }
  if (!loggedIn.value && guestBrowse.value) {
    requireLogin(router)
    return
  }
  router.push({ path: '/archive', query: { categoryId: String(cat.id) } })
}

function goProduct(item) {
  if (!item?.id) {
    goArchive()
    return
  }
  router.push({ path: `/archive/item/${item.id}` })
}

onMounted(() => {
  if (homeStyle.value === 'editorial') loadNews()
  if (homeStyle.value === 'mall') {
    loadMall().then(() => startMallRotate())
  }
})
onUnmounted(() => stopMallRotate())

const LEADS = {
  archive: '浏览与检索业务目录',
  my_archive: '查看本人发布的内容',
  my_tickets: '查看办理进度与记录',
  content: '通知、须知与临时公告',
  guestbook: '发表建议或咨询，查看管理员回复',
  dm: '与其他用户一对一私信沟通',
  favorites: '收藏的内容，便于再次查看',
  browse_history: '最近看过的记录',
  coupons: '领取与查看可用优惠券',
  order_reviews: '已完成订单的评价与商家回复',
  profile: '昵称、头像与个人资料',
  my_reservations: '查看与管理预约',
  slots: '选择时段并提交预约',
  week_calendar: '按周查看日程安排',
}

function messagesLead() {
  const pageLead = labels.messagesPageLead
  if (pageLead) return pageLead.replace(/。$/, '')
  const ticket = ticketCopy()
  const remind = ticket.verbs?.remind
  if (remind && remind !== '提醒') return `审核结果、${remind}提醒与系统通知`
  if (ticket.allowCheckin) return '审核结果、活动提醒与系统通知'
  return '审核结果与系统通知'
}

function cardLead(key, menuLabelText) {
  if (key === 'my_tickets') {
    const lab = String(menuLabelText || '').replace(/^我的/, '').trim()
    return lab ? `查看${lab}进度与办理记录` : LEADS.my_tickets
  }
  if (key === 'messages') return messagesLead()
  if (key === 'cart') {
    const cart = menuLabelText || '购物车'
    return `查看已选内容并结算（${cart}）`
  }
  if (key === 'my_orders') {
    const order = getSchema()?.entities?.order?.label || '订单'
    return `跟踪${order}状态`
  }
  if (key === 'favorites') {
    const custom = labels.favoritesPageLead || labels.favoritesLead
    if (custom) return String(custom).replace(/。$/, '')
    if ((getSchema()?.capabilities || []).includes('order_lines')) {
      return '收藏的商品，便于再次加购'
    }
  }
  if (key === 'dm') {
    const custom = labels.dmPageLead
    if (custom) return String(custom).replace(/。$/, '')
  }
  return LEADS[key] || `进入${menuLabelText}`
}

const GUEST_OK = new Set(['archive', 'content', 'guestbook', 'slots', 'home'])
const NEED_LOGIN = new Set([
  'my_tickets',
  'profile',
  'cart',
  'my_orders',
  'my_reservations',
  'week_calendar',
  'messages',
  'dm',
])

const cards = computed(() => {
  const menus = schemaMenus('user').filter((m) => m.key !== 'home')
  const out = []
  for (const m of menus) {
    const to = userMenuPath(m.key)
    if (!to) continue
    if (!loggedIn.value && guestBrowse.value && !GUEST_OK.has(m.key)) continue
    out.push({
      key: m.key,
      to,
      label: m.label,
      lead: cardLead(m.key, m.label),
      needLogin: NEED_LOGIN.has(m.key),
    })
  }
  if (loggedIn.value && !out.some((c) => c.key === 'profile')) {
    out.push({
      key: 'profile',
      to: '/profile',
      label: '个人资料',
      lead: LEADS.profile,
      needLogin: true,
    })
  }
  if (!out.length) {
    out.push({
      key: 'content',
      to: '/notices',
      label: '公告',
      lead: LEADS.content,
      needLogin: false,
    })
  }
  return out
})

const quickCards = computed(() => {
  const prefer = ['archive', 'favorites', 'content', 'guestbook']
  const byKey = Object.fromEntries(cards.value.map((c) => [c.key, c]))
  const out = []
  for (const k of prefer) {
    if (byKey[k]) out.push(byKey[k])
  }
  for (const c of cards.value) {
    if (out.length >= 4) break
    if (!out.some((x) => x.key === c.key)) out.push(c)
  }
  return out.slice(0, 4)
})

/** cards 首页：主路径优先 archive/slots，其余进短链轨 */
const PRIMARY_HOME_KEYS = ['archive', 'slots', 'content', 'my_tickets']
const primaryHomeCard = computed(() => {
  for (const k of PRIMARY_HOME_KEYS) {
    const hit = cards.value.find((c) => c.key === k)
    if (hit) return hit
  }
  return cards.value[0] || null
})
const secondaryHomeCard = computed(() => {
  const p = primaryHomeCard.value
  const prefer = ['content', 'my_tickets', 'slots', 'guestbook']
  for (const k of prefer) {
    const hit = cards.value.find((c) => c.key === k && c !== p)
    if (hit) return hit
  }
  return cards.value.find((c) => c !== p) || null
})
const railHomeCards = computed(() => {
  const skip = new Set(
    [primaryHomeCard.value?.key, secondaryHomeCard.value?.key].filter(Boolean),
  )
  return cards.value.filter((c) => !skip.has(c.key))
})
const cardsHeroTitle = computed(
  () =>
    labels.portalHomeHeadline ||
    primaryHomeCard.value?.label ||
    '开始使用',
)

function go(card) {
  if (card.needLogin && !requireLogin(router, card.to)) return
  router.push(card.to)
}

function goNotices() {
  router.push('/notices')
}

function openNews(item) {
  if (item.kind === 'notice' && item.id) {
    router.push(`/notices/${item.id}`)
    return
  }
  goNotices()
}
