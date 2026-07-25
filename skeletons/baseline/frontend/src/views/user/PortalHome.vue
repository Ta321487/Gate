<template>
  <div class="home" :data-home="homeStyle">
    <!-- 功能卡片（默认） -->
    <template v-if="homeStyle !== 'editorial'">
      <section class="hero">
        <h1>{{ appName }}</h1>
        <p>{{ lead }}</p>
      </section>

      <section class="grid" aria-label="功能入口">
        <button
          v-for="card in cards"
          :key="card.to"
          type="button"
          class="card"
          @click="go(card)"
        >
          <span class="card-label">{{ card.label }}</span>
          <span class="card-lead">{{ card.lead }}</span>
        </button>
      </section>
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
            <div v-if="!newsItems.length" class="news-empty">暂无资讯，可先浏览目录或公告。</div>
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
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import http from '../../api/http'
import { APP_DELIVERED } from '../../appDelivered.js'
import { getSchema, schemaLabels, schemaMenus, ticketCopy } from '../../utils/domainSchema.js'
import { isGuestBrowseEnabled, isLoggedIn, requireLogin } from '../../utils/session.js'

const router = useRouter()
const labels = schemaLabels()
const appName = labels.appName || APP_DELIVERED.title || '业务门户'
const lead = computed(
  () =>
    labels.portalHomeLead ||
    labels.authLead ||
    '从下方入口进入检索、申请、公告与个人中心。',
)
const loggedIn = computed(() => isLoggedIn())
const guestBrowse = computed(() => isGuestBrowseEnabled())
const homeStyle = computed(() => {
  const s = (APP_DELIVERED?.portalHomeStyle || import.meta.env.VITE_PORTAL_HOME_STYLE || 'cards')
    .toString()
    .trim()
  return s === 'editorial' ? 'editorial' : 'cards'
})

const DOMAIN_NEWS = {
  'DOM-BLOG': { kicker: 'NEWS & UPDATES', title: '资讯动态', claim: '记录与分享本站原创内容' },
  'DOM-MEDIA': { kicker: 'NOW SHOWING', title: '本周上新', claim: '精选片库，随时开看' },
  'DOM-MUSIC': { kicker: 'NEW TRACKS', title: '新歌速递', claim: '听见喜欢的声音' },
  'DOM-FORUM': { kicker: 'COMMUNITY', title: '社区动态', claim: '文明发帖，互助交流' },
}

const domainId = computed(
  () => getSchema()?.domain || APP_DELIVERED?.domain || APP_DELIVERED?.schema?.domain || '',
)
const newsMeta = computed(() => DOMAIN_NEWS[domainId.value] || DOMAIN_NEWS['DOM-BLOG'])
const newsKicker = computed(() => labels.portalNewsKicker || newsMeta.value.kicker)
const newsTitle = computed(() => labels.portalNewsTitle || newsMeta.value.title)
const claimText = computed(
  () =>
    labels.portalHomeClaim ||
    labels.authEyebrow ||
    newsMeta.value.claim ||
    appName,
)

const banners = computed(() => {
  const list = APP_DELIVERED?.portalBanners
  return Array.isArray(list) ? list.filter((x) => x && x.src) : []
})
const claimCover = computed(() => banners.value[0]?.src || APP_DELIVERED?.authHero || '')

const newsItems = ref([])

async function loadNews() {
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

onMounted(() => {
  if (homeStyle.value === 'editorial') loadNews()
})

const MENU_TO = {
  home: '/home',
  archive: '/archive',
  my_archive: '/my-archive',
  my_tickets: '/tickets',
  content: '/notices',
  guestbook: '/guestbook',
  dm: '/dm',
  profile: '/profile',
  favorites: '/favorites',
  browse_history: '/browse-history',
  coupons: '/coupons',
  cart: '/cart',
  my_orders: '/orders',
  order_reviews: '/order-reviews',
  my_reservations: '/reservations',
  slots: '/slots',
  week_calendar: '/week',
  messages: '/messages',
}

const LEADS = {
  archive: '浏览与检索业务目录',
  my_archive: '查看本人发布的内容',
  my_tickets: '查看申请进度与办理记录',
  content: '通知、须知与临时公告',
  guestbook: '发表建议或咨询，查看管理员回复',
  dm: '与其他用户一对一私信沟通',
  favorites: '收藏的商品，便于再次加购',
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
  if (key === 'messages') return messagesLead()
  if (key === 'cart') {
    const cart = menuLabelText || '购物车'
    return `查看已选内容并结算（${cart}）`
  }
  if (key === 'my_orders') {
    const order = getSchema()?.entities?.order?.label || '订单'
    return `跟踪${order}状态`
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
    const to = MENU_TO[m.key]
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
.hero { margin-bottom: 22px; }
.hero h1 {
  margin: 0 0 8px;
  font-size: clamp(1.45rem, 2.4vw, 1.85rem);
  font-weight: 700;
  letter-spacing: 0.01em;
  font-family: var(--portal-font-display, var(--portal-font-ui));
}
.hero p {
  margin: 0;
  font-size: 14px;
  line-height: 1.55;
  color: var(--portal-muted, #5b6b76);
  max-width: 40em;
}
.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 12px;
}
.card {
  text-align: left;
  border: var(--portal-border-width, 1px) solid var(--portal-line, #d5dde3);
  background: color-mix(in srgb, var(--portal-surface, #fff) 92%, transparent);
  border-radius: var(--portal-radius, 12px);
  box-shadow: var(--portal-shadow, none);
  padding: var(--portal-pad, 16px) 16px 18px;
  cursor: pointer;
  display: flex;
  flex-direction: column;
  gap: 6px;
  transition: border-color 0.15s ease, transform 0.15s ease, background 0.15s ease;
}
.card:hover {
  border-color: color-mix(in srgb, var(--portal-accent, #0b6e75) 45%, var(--portal-line, #d5dde3));
  background: var(--portal-surface, #fff);
  transform: translateY(-1px);
}
.card-label {
  font-size: 15px;
  font-weight: 650;
  color: var(--portal-ink, #15202b);
}
.card-lead {
  font-size: 12px;
  line-height: 1.45;
  color: var(--portal-muted, #5b6b76);
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
}
</style>
