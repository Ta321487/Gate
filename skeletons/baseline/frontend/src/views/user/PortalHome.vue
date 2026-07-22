<template>
  <div class="home">
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

    <p v-if="!loggedIn && guestBrowse" class="hint">
      部分内容需登录后使用 ·
      <router-link :to="{ path: '/login', query: { redirect: '/home' } }">去登录</router-link>
    </p>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
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

const MENU_TO = {
  home: '/home',
  archive: '/archive',
  my_archive: '/my-archive',
  my_tickets: '/tickets',
  content: '/notices',
  guestbook: '/guestbook',
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
  const lead = labels.messagesPageLead
  if (lead) return lead.replace(/。$/, '')
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
  // 资料常放在顶栏按钮，首页卡片仍露出，避免「功能少」观感
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

function go(card) {
  if (card.needLogin && !requireLogin(router, card.to)) return
  router.push(card.to)
}
</script>

<style scoped>
.home { max-width: 920px; }
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
</style>
