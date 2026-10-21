<template>
  <div class="home" :data-home="homeStyle">
    <!-- 商城货架：分类栏 + Banner + 新品 -->
    <template v-if="homeStyle === 'mall'">
      <div class="mall">
        <section class="mall-hero" aria-label="分类与推荐">
          <aside class="mall-cats" aria-label="商品分类">
            <button
              v-for="c in mallCategories"
              :key="c.id"
              type="button"
              class="mall-cat"
              @click="goCategory(c)"
            >
              {{ c.name }}
            </button>
            <p v-if="!mallCategories.length" class="mall-cat-empty">暂无分类</p>
          </aside>
          <div class="mall-banner" aria-roledescription="carousel" aria-label="首页推荐">
            <button
              type="button"
              class="mall-banner-slide"
              :aria-label="mallBannerTitle"
              :style="mallBannerStyle"
              @click="onMallBanner"
            >
              <div v-if="!mallBannerSrc" class="mall-banner-fallback">
                <p class="mall-banner-kicker">{{ mallBannerTitle }}</p>
                <p class="mall-banner-lead">{{ mallBannerLead }}</p>
              </div>
            </button>
            <div v-if="mallSlides.length > 1" class="mall-dots">
              <button
                v-for="(s, i) in mallSlides"
                :key="'bd' + i"
                type="button"
                :class="{ on: i === mallIndex }"
                :aria-label="'第' + (i + 1) + '张'"
                @click="showMallSlide(i)"
              />
            </div>
          </div>
        </section>

        <section class="mall-new" aria-label="新品上架">
          <div class="mall-new-hd">
            <h2 class="mall-new-title">新品上架</h2>
            <button type="button" class="more" @click="goArchive">查看更多 &gt;&gt;</button>
          </div>
          <div class="mall-grid">
            <button
              v-for="item in mallProducts"
              :key="item.id"
              type="button"
              class="mall-card"
              @click="goProduct(item)"
            >
              <div
                class="mall-cover"
                :style="item.cover ? { backgroundImage: `url('${item.cover}')` } : undefined"
              >
                <span v-if="!item.cover" class="mall-cover-letter">{{ item.letter }}</span>
              </div>
              <div class="mall-copy">
                <h3>{{ item.title }}</h3>
                <p>{{ item.lead }}</p>
                <div class="mall-foot">
                  <span class="mall-price">{{ item.price }}</span>
                  <span class="mall-meta">{{ item.salesText || (item.shop ? item.shop : item.meta) }}</span>
                </div>
              </div>
            </button>
          </div>
          <div v-if="!mallProducts.length" class="mall-empty">
            <EmptyHint
              title="暂无商品"
              desc="货架还空着，去逛逛全部目录吧。"
              mark="购"
              cta-label="去逛逛"
              @cta="goArchive"
            />
          </div>
        </section>

        <section v-if="mallHot.length" class="mall-new" aria-label="热销商品">
          <div class="mall-new-hd">
            <h2 class="mall-new-title">热销商品</h2>
            <button type="button" class="more" @click="goArchive">查看更多 &gt;&gt;</button>
          </div>
          <div class="mall-grid">
            <button
              v-for="item in mallHot"
              :key="'hot-' + item.id"
              type="button"
              class="mall-card"
              @click="goProduct(item)"
            >
              <div
                class="mall-cover"
                :style="item.cover ? { backgroundImage: `url('${item.cover}')` } : undefined"
              >
                <span v-if="!item.cover" class="mall-cover-letter">{{ item.letter }}</span>
              </div>
              <div class="mall-copy">
                <h3>{{ item.title }}</h3>
                <p>{{ item.lead }}</p>
                <div class="mall-foot">
                  <span class="mall-price">{{ item.price }}</span>
                  <span class="mall-meta">{{ item.salesText || (item.shop ? item.shop : item.meta) }}</span>
                </div>
              </div>
            </button>
          </div>
        </section>

        <!-- 挂 flash_price 且有窗内活动价才出；点进详情按下单活动价走 -->
        <section v-if="flashOn && mallFlashProducts.length" class="mall-flash" aria-label="限时特价">
          <div class="mall-new-hd">
            <h2 class="mall-new-title">{{ mallFlashTitle }}</h2>
            <button type="button" class="more" @click="goArchive">{{ mallFlashMore }} &gt;&gt;</button>
          </div>
          <div class="mall-grid">
            <button
              v-for="item in mallFlashProducts"
              :key="'flash-' + item.id"
              type="button"
              class="mall-card"
              @click="goProduct(item)"
            >
              <div
                class="mall-cover"
                :style="item.cover ? { backgroundImage: `url('${item.cover}')` } : undefined"
              >
                <span class="mall-flash-badge">{{ flashBadge }}</span>
                <span v-if="!item.cover" class="mall-cover-letter">{{ item.letter }}</span>
              </div>
              <div class="mall-copy">
                <h3>{{ item.title }}</h3>
                <p v-if="item.countdown" class="mall-flash-cd">{{ item.countdown }}</p>
                <p v-else>{{ item.lead }}</p>
                <div class="mall-foot">
                  <span class="mall-price">
                    {{ item.price }}
                    <span v-if="item.listPrice" class="mall-list-price">{{ item.listPrice }}</span>
                  </span>
                  <span class="mall-meta">{{ item.shop ? item.shop : item.meta }}</span>
                </div>
              </div>
            </button>
          </div>
        </section>
      </div>
    </template>

    <!-- 默认首页：品牌首屏 + 主行动 + 短链轨（禁止功能方卡墙） -->
    <template v-else-if="homeStyle !== 'editorial'">
      <section class="cards-hero" aria-label="门户首屏">
        <div class="cards-hero-panel">
          <p class="cards-kicker">{{ appName }}</p>
          <h1>{{ cardsHeroTitle }}</h1>
          <p class="cards-lead">{{ lead }}</p>
          <p v-if="industrySkinHint" class="skin-hint">{{ industrySkinHint }}</p>
          <div class="cards-cta-row">
            <button
              v-if="primaryHomeCard"
              type="button"
              class="cards-cta"
              @click="go(primaryHomeCard)"
            >{{ primaryHomeCard.label }}</button>
            <button
              v-if="secondaryHomeCard"
              type="button"
              class="cards-cta ghost"
              @click="go(secondaryHomeCard)"
            >{{ secondaryHomeCard.label }}</button>
          </div>
        </div>
      </section>
      <nav v-if="railHomeCards.length" class="cards-rail" aria-label="更多入口">
        <button
          v-for="card in railHomeCards"
          :key="card.to"
          type="button"
          class="cards-rail-btn"
          @click="go(card)"
        >{{ card.label }}</button>
      </nav>
    </template>

    <!-- 资讯 + 侧栏（内容域） -->
    <template v-else>
      <div class="editorial">
        <section class="news" aria-label="资讯动态">
          <div class="news-hd">
            <div>
              <p class="news-kicker">{{ newsKicker }}</p>
              <h2 class="news-title">{{ newsTitle }}</h2>
            </div>
            <button type="button" class="more" @click="goNotices">+ 查看更多</button>
          </div>
          <div class="news-track">
            <button
              v-for="(item, i) in newsItems"
              :key="item.id || i"
              type="button"
              class="news-card"
              @click="openNews(item)"
            >
              <div
                class="news-cover"
                :style="item.cover ? { backgroundImage: `url('${item.cover}')` } : undefined"
              />
              <div class="news-copy">
                <h3>{{ item.title }}</h3>
                <p>{{ item.lead }}</p>
              </div>
            </button>
            <div v-if="!newsItems.length" class="news-empty">
              <EmptyHint
                title="暂无资讯"
                desc="可先浏览目录或公告。"
                mark="讯"
                cta-label="去逛逛"
                @cta="goArchive"
              />
            </div>
          </div>
          <div class="quick" aria-label="快捷入口">
            <button
              v-for="card in quickCards"
              :key="card.to"
              type="button"
              class="quick-btn"
              @click="go(card)"
            >
              {{ card.label }}
            </button>
          </div>
        </section>

        <aside class="claim" aria-label="门户主张">
          <div
            class="claim-photo"
            :style="claimCover ? { backgroundImage: `url('${claimCover}')` } : undefined"
          />
          <div class="claim-box">
            <p class="claim-text">{{ claimText }}</p>
          </div>
        </aside>
      </div>
    </template>

    <p v-if="!loggedIn && guestBrowse" class="hint">
      部分内容需登录后使用 ·
      <router-link :to="{ path: '/login', query: { redirect: '/home' } }">去登录</router-link>
    </p>
  </div>
</template>

<script setup>
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
</script>

<style scoped>
.home { max-width: 920px; }
.home[data-home='editorial'] { max-width: 1100px; }
.home[data-home='mall'] { max-width: 1100px; }
.home[data-home='cards'] { max-width: 720px; }
.cards-hero { margin-bottom: 18px; }
.cards-hero-panel {
  padding: clamp(22px, 4vw, 36px);
  border-radius: var(--portal-radius, 14px);
  color: #fff;
  background: var(--portal-cover, linear-gradient(160deg, #0b6e75, #08545a));
  box-shadow: var(--portal-shadow, none);
}
.cards-kicker {
  margin: 0 0 8px;
  font-size: clamp(1.35rem, 2.6vw, 1.75rem);
  font-weight: 750;
  letter-spacing: -0.02em;
  font-family: var(--portal-font-display, var(--portal-font-ui));
  overflow-wrap: anywhere;
}
.cards-hero-panel h1 {
  margin: 0 0 10px;
  font-size: 1.05rem;
  font-weight: 600;
  opacity: 0.92;
}
.cards-lead {
  margin: 0;
  font-size: 14px;
  line-height: 1.55;
  max-width: 36em;
  opacity: 0.88;
}
.skin-hint {
  margin-top: 8px;
  font-size: 0.85rem;
  opacity: 0.75;
}
.cards-cta-row {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 18px;
}
.cards-cta {
  border: none;
  border-radius: 8px;
  padding: 10px 18px;
  font-size: 14px;
  font-weight: 650;
  cursor: pointer;
  background: #fff;
  color: var(--portal-brand, #08545a);
}
.cards-cta.ghost {
  background: transparent;
  color: #fff;
  border: 1px solid color-mix(in srgb, #fff 55%, transparent);
}
.cards-cta:hover { filter: brightness(1.03); }
.cards-rail {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.cards-rail-btn {
  border: 1px solid var(--portal-line, #d5dde3);
  background: var(--portal-surface, #fff);
  color: var(--portal-ink, #15202b);
  border-radius: 999px;
  padding: 7px 14px;
  font-size: 13px;
  cursor: pointer;
}
.cards-rail-btn:hover {
  border-color: var(--portal-accent, #0b6e75);
  color: var(--portal-accent, #0b6e75);
}
.hint {
  margin: 20px 0 0;
  font-size: 13px;
  color: var(--portal-muted, #5b6b76);
}
.hint a { color: var(--portal-accent, #0b6e75); }

.editorial {
  display: grid;
  grid-template-columns: minmax(0, 1.7fr) minmax(240px, 0.95fr);
  gap: 18px;
  align-items: stretch;
}
.news {
  min-width: 0;
  padding: 4px 2px 0;
}
.news-hd {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 14px;
}
.news-kicker {
  margin: 0 0 4px;
  font-size: 11px;
  letter-spacing: 0.14em;
  font-weight: 700;
  color: var(--portal-muted, #5b6b76);
  text-transform: uppercase;
}
.news-title {
  margin: 0;
  font-size: clamp(1.25rem, 2vw, 1.55rem);
  font-weight: 750;
  color: var(--portal-ink, #15202b);
  font-family: var(--portal-font-display, var(--portal-font-ui));
}
.more {
  border: 0;
  background: transparent;
  color: var(--portal-accent, #0b6e75);
  font-size: 13px;
  cursor: pointer;
  white-space: nowrap;
  padding: 4px 0;
}
.more:hover { text-decoration: underline; }
.news-track {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}
.news-card {
  text-align: left;
  border: var(--portal-border-width, 1px) solid var(--portal-line, #d5dde3);
  background: var(--portal-surface, #fff);
  border-radius: var(--portal-radius, 12px);
  overflow: hidden;
  cursor: pointer;
  padding: 0;
  display: flex;
  flex-direction: column;
  transition: transform 0.15s ease, border-color 0.15s ease;
}
.news-card:hover {
  transform: translateY(-1px);
  border-color: color-mix(in srgb, var(--portal-accent, #0b6e75) 40%, var(--portal-line));
}
.news-cover {
  aspect-ratio: 16 / 10;
  background:
    linear-gradient(160deg, color-mix(in srgb, var(--portal-accent, #0b6e75) 35%, #123) 0%, var(--portal-brand, #08545a) 100%);
  background-size: cover;
  background-position: center;
}
.news-copy { padding: 12px 14px 14px; }
.news-copy h3 {
  margin: 0 0 6px;
  font-size: 14px;
  font-weight: 650;
  line-height: 1.35;
  color: var(--portal-ink, #15202b);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.news-copy p {
  margin: 0;
  font-size: 12px;
  line-height: 1.45;
  color: var(--portal-muted, #5b6b76);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.news-empty {
  grid-column: 1 / -1;
  padding: 28px 16px;
  text-align: center;
  color: var(--portal-muted, #5b6b76);
  font-size: 13px;
  border: 1px dashed var(--portal-line, #d5dde3);
  border-radius: var(--portal-radius, 12px);
}
.quick {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 16px;
}
.quick-btn {
  border: 1px solid var(--portal-line, #d5dde3);
  background: color-mix(in srgb, var(--portal-surface, #fff) 88%, transparent);
  color: var(--portal-ink, #15202b);
  border-radius: 999px;
  padding: 7px 14px;
  font-size: 12px;
  cursor: pointer;
}
.quick-btn:hover {
  border-color: var(--portal-accent, #0b6e75);
  color: var(--portal-accent, #0b6e75);
}
.claim {
  position: relative;
  border-radius: var(--portal-radius, 14px);
  overflow: hidden;
  min-height: 360px;
  border: var(--portal-border-width, 1px) solid var(--portal-line, #d5dde3);
  background: var(--portal-brand, #08545a);
}
.claim-photo {
  position: absolute;
  inset: 0;
  background:
    linear-gradient(180deg, transparent 35%, rgba(0, 0, 0, 0.45) 100%),
    linear-gradient(160deg, color-mix(in srgb, var(--portal-accent, #0b6e75) 50%, #0a1a22), var(--portal-brand, #08545a));
  background-size: cover;
  background-position: center;
}
.claim-box {
  position: absolute;
  left: 14px;
  right: 14px;
  bottom: 14px;
  padding: 16px 16px 18px;
  background: var(--portal-accent, #0b6e75);
  color: #fff;
  border-radius: 4px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.18);
}
.claim-text {
  margin: 0;
  font-size: 15px;
  font-weight: 650;
  line-height: 1.45;
}

@media (max-width: 860px) {
  .editorial { grid-template-columns: 1fr; }
  .claim { min-height: 220px; }
  .news-track { grid-template-columns: 1fr; }
  .mall-hero { grid-template-columns: 1fr; }
  .mall-cats { flex-direction: row; flex-wrap: wrap; max-height: none; }
  .mall-cat { flex: 1 1 40%; }
  .mall-banner { min-height: 180px; }
  .mall-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}

/* —— 商城货架首页 —— */
.mall { display: flex; flex-direction: column; gap: 22px; }
.mall-hero {
  display: grid;
  grid-template-columns: minmax(160px, 200px) minmax(0, 1fr);
  gap: 0;
  border: 1px solid var(--portal-line, #e5e7eb);
  border-radius: var(--portal-radius, 10px);
  overflow: hidden;
  background: var(--portal-surface, #fff);
}
.mall-cats {
  display: flex;
  flex-direction: column;
  background:
    linear-gradient(
      165deg,
      color-mix(in srgb, var(--portal-brand, #08545a) 90%, #0a0a0a) 0%,
      color-mix(in srgb, var(--portal-ink, #15202b) 82%, #000) 100%
    );
  color: #f8fafc;
  min-height: 280px;
}
.mall-cat {
  display: block;
  width: 100%;
  border: 0;
  background: transparent;
  color: inherit;
  font: inherit;
  text-align: left;
  padding: 11px 14px;
  font-size: 13px;
  cursor: pointer;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
  border-left: 3px solid transparent;
}
.mall-cat:hover {
  background: color-mix(in srgb, var(--portal-accent, #0b6e75) 28%, transparent);
  border-left-color: var(--portal-accent, #0b6e75);
}
.mall-cat-empty {
  margin: auto;
  padding: 16px;
  font-size: 12px;
  opacity: 0.65;
}
.mall-banner {
  min-height: 280px;
  position: relative;
  background: var(--portal-surface, #fff);
}
.mall-banner-slide {
  display: block;
  width: 100%;
  min-height: 280px;
  border: 0;
  padding: 0;
  cursor: pointer;
  text-align: left;
  background:
    var(--portal-cover, linear-gradient(135deg, #14b8a6, #0b6e75)) center / cover no-repeat;
  position: relative;
}
.mall-dots {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 12px;
  display: flex;
  justify-content: center;
  gap: 6px;
  z-index: 2;
}
.mall-dots button {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  border: 0;
  padding: 0;
  cursor: pointer;
  background: rgba(255, 255, 255, 0.45);
}
.mall-dots button.on {
  background: #fff;
  box-shadow: 0 0 0 1px color-mix(in srgb, var(--portal-accent, #0b6e75) 35%, transparent);
}
.mall-banner-fallback {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  justify-content: flex-end;
  padding: 28px;
  color: #fff;
  background: linear-gradient(180deg, transparent 30%, rgba(0, 0, 0, 0.45));
}
.mall-banner-kicker {
  margin: 0 0 6px;
  font-size: clamp(1.2rem, 2vw, 1.6rem);
  font-weight: 750;
  font-family: var(--portal-font-display, var(--portal-font-ui));
}
.mall-banner-lead {
  margin: 0;
  font-size: 13px;
  line-height: 1.5;
  max-width: 36em;
  opacity: 0.92;
}
.mall-new-hd {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 14px;
}
.mall-new-title {
  margin: 0;
  font-size: 1.15rem;
  font-weight: 750;
  color: var(--portal-ink, #15202b);
  font-family: var(--portal-font-display, var(--portal-font-ui));
  display: flex;
  align-items: center;
  gap: 10px;
}
.mall-new-title::before {
  content: '';
  width: 4px;
  height: 1.05em;
  border-radius: 2px;
  background: var(--portal-accent, #0b6e75);
}
.mall-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}
.mall-card {
  font: inherit;
  color: inherit;
  text-align: left;
  border: 1px solid var(--portal-line, #e5e7eb);
  background: var(--portal-surface, #fff);
  border-radius: 12px;
  padding: 0;
  overflow: hidden;
  cursor: pointer;
  display: flex;
  flex-direction: column;
  transition: border-color 0.15s ease, transform 0.15s ease, box-shadow 0.15s ease;
}
.mall-card:hover {
  border-color: color-mix(in srgb, var(--portal-accent, #0b6e75) 45%, var(--portal-line, #e5e7eb));
  transform: translateY(-3px);
  box-shadow: 0 12px 28px color-mix(in srgb, var(--portal-accent, #0b6e75) 14%, transparent);
}
.mall-cover {
  aspect-ratio: 1 / 1;
  background:
    color-mix(in srgb, var(--portal-accent, #0b6e75) 10%, var(--portal-surface, #fff)) center / cover no-repeat;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
}
.mall-cover-letter {
  font-size: 2.2rem;
  font-weight: 750;
  font-family: var(--portal-font-display, inherit);
  color: #fff;
  opacity: 0.92;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.18);
}
.mall-cover:not([style*='background-image']) {
  background:
    linear-gradient(
      145deg,
      color-mix(in srgb, var(--portal-accent, #0b6e75) 78%, #0a0a0a),
      var(--portal-brand, #08545a)
    );
}
.mall-flash-badge {
  position: absolute;
  top: 8px;
  left: 8px;
  z-index: 1;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 650;
  color: #fff;
  background: var(--portal-accent, #0b6e75);
}
.mall-flash-cd {
  color: var(--portal-accent, #0b6e75) !important;
  font-weight: 600;
}
.mall-list-price {
  margin-left: 6px;
  font-size: 12px;
  font-weight: 400;
  color: var(--portal-muted, #9ca3af);
  text-decoration: line-through;
}
.mall-copy {
  padding: 12px 12px 14px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-height: 0;
}
.mall-copy h3 {
  margin: 0;
  font-size: 14px;
  font-weight: 700;
  color: var(--portal-ink, #15202b);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.mall-copy > p {
  margin: 0;
  font-size: 12px;
  line-height: 1.4;
  color: var(--portal-muted, #6b7280);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  min-height: 2.8em;
}
.mall-foot {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 8px;
  margin-top: 6px;
  min-width: 0;
}
.mall-price {
  font-size: 16px;
  font-weight: 750;
  color: var(--portal-accent, #0b6e75);
  font-variant-numeric: tabular-nums;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.mall-meta {
  font-size: 11px;
  color: var(--portal-muted, #9ca3af);
  white-space: nowrap;
  flex-shrink: 0;
}
.mall-empty {
  padding: 28px 12px;
  text-align: center;
  color: var(--portal-muted, #6b7280);
  font-size: 13px;
  border: 1px dashed var(--portal-line, #e5e7eb);
  border-radius: var(--portal-radius, 10px);
}
</style>
