<template>
  <div class="portal" :data-has-stage="hasStage ? '1' : '0'">
    <header class="top">
      <div class="top-inner">
        <div class="brand" @click="$router.push(homePath)">
          <span class="brand-mark" aria-hidden="true" />
          <span class="brand-text">{{ title }}</span>
        </div>
        <nav class="nav">
          <router-link v-for="item in nav" :key="item.to" :to="item.to">{{ item.label }}</router-link>
        </nav>
        <div class="user">
          <template v-if="loggedIn">
            <MessageBell />
            <el-avatar v-if="avatarUrl" :size="28" :src="avatarUrl" />
            <span class="name">{{ displayName }}</span>
            <el-button v-if="profileEditable" link @click="$router.push('/profile')">资料</el-button>
            <el-button link @click="logout">退出</el-button>
          </template>
          <template v-else>
            <el-button link type="primary" @click="$router.push({ path: '/login', query: { redirect: $route.fullPath } })">登录</el-button>
            <el-button link @click="$router.push('/register')">注册</el-button>
          </template>
        </div>
      </div>
    </header>

    <div v-if="hasStage" class="stage">
      <PortalCarousel />
    </div>

    <main class="body">
      <router-view />
    </main>
    <footer class="foot">
      <div class="foot-inner">
        <span class="foot-brand">{{ footer.brand }}</span>
        <span class="sep">·</span>
        <span class="foot-tag">{{ footer.tagline }}</span>
      </div>
    </footer>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { APP_DELIVERED } from '../appDelivered.js'
import MessageBell from '../components/MessageBell.vue'
import PortalCarousel from '../components/PortalCarousel.vue'
import { portalFooterCopy } from '../utils/domainFlavor.js'
import { menuLabel, schemaLabels, schemaMenus } from '../utils/domainSchema.js'
import { isGuestBrowseEnabled, isLoggedIn, onProfileDisplayChange } from '../utils/session.js'

const router = useRouter()
const route = useRoute()
const labels = schemaLabels()
const title = labels.appName || APP_DELIVERED.title || import.meta.env.VITE_APP_TITLE || '毕设系统'
const footer = computed(() => portalFooterCopy())
const profileEditable = localStorage.getItem('profileEditable') !== 'false'
const loggedIn = ref(isLoggedIn())
const username = ref(localStorage.getItem('username') || '')
const nickname = ref(localStorage.getItem('nickname') || '')
const avatarUrl = ref(localStorage.getItem('avatarUrl') || '')

function refreshUserDisplay() {
  loggedIn.value = isLoggedIn()
  username.value = localStorage.getItem('username') || ''
  nickname.value = localStorage.getItem('nickname') || ''
  avatarUrl.value = localStorage.getItem('avatarUrl') || ''
}

watch(() => route.fullPath, refreshUserDisplay)

let offProfileDisplay
onMounted(() => {
  offProfileDisplay = onProfileDisplayChange(({ nickname: n, avatarUrl: a }) => {
    nickname.value = n || ''
    avatarUrl.value = a || ''
  })
})
onUnmounted(() => offProfileDisplay?.())

const displayName = computed(() => nickname.value || username.value)
const hasStage = computed(() => {
  const list = APP_DELIVERED?.portalBanners
  return Array.isArray(list) && list.some((x) => x && x.src)
})

const MENU_TO = {
  home: '/home',
  my_tickets: '/tickets',
  content: '/notices',
  guestbook: '/guestbook',
  profile: '/profile',
  archive: '/archive',
  my_archive: '/my-archive',
  favorites: '/favorites',
  browse_history: '/browse-history',
  coupons: '/coupons',
  cart: '/cart',
  my_orders: '/orders',
  order_reviews: '/order-reviews',
  addresses: '/addresses',
  my_reservations: '/reservations',
  slots: '/slots',
  week_calendar: '/week',
  messages: '/messages',
}

const GUEST_MENU_KEYS = new Set(['archive', 'content', 'guestbook', 'slots'])

const nav = computed(() => {
  // 资料留在右侧按钮，避免与顶栏重复
  const menus = schemaMenus('user').filter((m) => m.key !== 'profile' && m.key !== 'home')
  let list = menus
  if (!loggedIn.value && isGuestBrowseEnabled()) {
    list = menus.filter((m) => GUEST_MENU_KEYS.has(m.key))
  } else if (!loggedIn.value) {
    list = menus.filter((m) => m.key === 'content' || m.key === 'guestbook' || m.key === 'archive')
  }
  if (!list.length) {
    return [{ to: '/notices', label: menuLabel('user', 'content', '公告') }]
  }
  return list
    .map((m) => ({ to: MENU_TO[m.key], label: m.label }))
    .filter((m) => m.to)
})

/** 品牌点击回门户根，走各壳默认 redirect（业务页） */
const homePath = computed(() => '/')

function logout() {
  localStorage.clear()
  router.push('/login')
}
</script>

<style scoped>
.portal {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background:
    radial-gradient(1100px 380px at 8% -8%, var(--portal-bg-glow, rgba(11, 110, 117, 0.14)), transparent 58%),
    radial-gradient(800px 280px at 96% 12%, color-mix(in srgb, var(--portal-accent, #0b6e75) 10%, transparent), transparent 50%),
    linear-gradient(180deg, var(--portal-bg, #eef3f5) 0%, color-mix(in srgb, var(--portal-bg, #eef3f5) 88%, var(--portal-mix, #fff)) 100%);
  color: var(--portal-ink, #15202b);
  font-family: var(--portal-font-ui);
}
.top {
  position: sticky; top: 0; z-index: 20;
  background: color-mix(in srgb, var(--portal-surface, #fff) 88%, transparent);
  backdrop-filter: blur(12px) saturate(1.1);
  border-bottom: var(--portal-border-width, 1px) solid var(--portal-line, #d5dde3);
}
.top-inner {
  max-width: 1080px; margin: 0 auto;
  height: 60px; padding: 0 20px;
  display: flex; align-items: center; gap: 20px;
}
.brand {
  display: flex; align-items: center; gap: 10px;
  cursor: pointer; flex-shrink: 1; min-width: 0; max-width: 42%;
}
.brand-mark {
  width: 22px; height: 22px; border-radius: var(--portal-radius-sm, 6px); flex-shrink: 0;
  background: linear-gradient(135deg, var(--portal-accent, #0b6e75), color-mix(in srgb, var(--portal-accent, #0b6e75) 40%, var(--portal-mix, #fff)));
}
.brand-text {
  font-family: var(--portal-font-display);
  font-weight: 700; font-size: 15px; letter-spacing: var(--portal-display-tracking, 0.02em);
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.nav { display: flex; gap: 4px; flex: 1; flex-wrap: nowrap; min-width: 0; overflow-x: auto; }
.nav a {
  padding: 6px 12px; border-radius: var(--portal-radius-sm, 8px); font-size: 13px; font-weight: 500;
  color: var(--portal-muted, #5b6b76); text-decoration: none;
}
.nav a.router-link-active,
.nav a:hover { color: var(--portal-ink, #15202b); background: color-mix(in srgb, var(--portal-accent, #0b6e75) 12%, transparent); }
.user { display: flex; align-items: center; gap: 8px; margin-left: auto; }
.name { font-size: 13px; color: var(--portal-muted, #5b6b76); max-width: 120px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.body { flex: 1; max-width: 1080px; width: 100%; margin: 0 auto; padding: 20px 20px 40px; box-sizing: border-box; }
.foot {
  padding: 16px 20px; text-align: center; font-size: 12px;
  color: var(--portal-muted, #5b6b76); border-top: var(--portal-border-width, 1px) solid var(--portal-line, #d5dde3);
}
.foot-inner {
  max-width: 1080px;
  margin: 0 auto;
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  align-items: baseline;
  gap: 0 2px;
}
.foot-brand {
  font-family: var(--portal-font-display);
  font-weight: 600;
  color: var(--portal-ink, #15202b);
}
.foot-tag { opacity: 0.92; }
.sep { margin: 0 6px; opacity: 0.5; }
</style>
