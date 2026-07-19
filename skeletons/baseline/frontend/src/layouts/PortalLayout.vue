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
          <MessageBell />
          <el-avatar v-if="avatarUrl" :size="28" :src="avatarUrl" />
          <span class="name">{{ displayName }}</span>
          <el-button v-if="profileEditable" link @click="$router.push('/profile')">资料</el-button>
          <el-button link @click="logout">退出</el-button>
        </div>
      </div>
    </header>

    <PortalCarousel v-if="hasStage" />

    <main class="body">
      <router-view />
    </main>
    <footer class="foot">
      <span>{{ title }}</span>
      <span class="sep">·</span>
      <span>{{ userRoleLabel }}门户</span>
    </footer>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { FACTORY_DELIVERED } from '../factoryDelivered.js'
import MessageBell from '../components/MessageBell.vue'
import PortalCarousel from '../components/PortalCarousel.vue'
import { getSchema, menuLabel, schemaLabels, schemaMenus } from '../utils/domainSchema.js'

const router = useRouter()
const labels = schemaLabels()
const title = labels.appName || FACTORY_DELIVERED.title || import.meta.env.VITE_APP_TITLE || '毕设系统'
const username = localStorage.getItem('username') || ''
const nickname = localStorage.getItem('nickname') || ''
const avatarUrl = localStorage.getItem('avatarUrl') || ''
const profileEditable = localStorage.getItem('profileEditable') !== 'false'
const displayName = computed(() => nickname || username)
const userRoleLabel = computed(() => getSchema()?.roles?.user?.label || '用户')
const hasStage = computed(() => {
  const list = FACTORY_DELIVERED?.portalBanners
  return Array.isArray(list) && list.some((x) => x && x.src)
})

const MENU_TO = {
  my_tickets: '/tickets',
  content: '/notices',
  profile: '/profile',
  archive: '/archive',
  cart: '/cart',
  my_orders: '/orders',
  my_reservations: '/reservations',
  slots: '/slots',
}

const nav = computed(() => {
  const menus = schemaMenus('user').filter((m) => m.key !== 'profile')
  if (!menus.length) {
    return [
      { to: '/tickets', label: menuLabel('user', 'my_tickets', '我的单据') },
      { to: '/notices', label: menuLabel('user', 'content', '公告') },
    ]
  }
  return menus
    .map((m) => ({ to: MENU_TO[m.key], label: m.label }))
    .filter((m) => m.to)
})

const homePath = computed(() => nav.value[0]?.to || '/tickets')

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
    linear-gradient(180deg, var(--portal-bg, #eef3f5) 0%, color-mix(in srgb, var(--portal-bg, #eef3f5) 88%, #fff) 100%);
  color: var(--portal-ink, #15202b);
  font-family: var(--portal-font-ui);
}
.top {
  position: sticky; top: 0; z-index: 20;
  background: color-mix(in srgb, var(--portal-surface, #fff) 88%, transparent);
  backdrop-filter: blur(12px) saturate(1.1);
  border-bottom: 1px solid var(--portal-line, #d5dde3);
}
.top-inner {
  max-width: 1080px; margin: 0 auto;
  height: 60px; padding: 0 20px;
  display: flex; align-items: center; gap: 28px;
}
.brand {
  display: flex; align-items: center; gap: 10px;
  cursor: pointer; white-space: nowrap;
  min-width: 0;
}
.brand-mark {
  width: 10px; height: 10px; border-radius: 2px;
  background: var(--portal-accent, #0b6e75);
  box-shadow: 3px 3px 0 color-mix(in srgb, var(--portal-brand, #08545a) 55%, transparent);
  flex-shrink: 0;
}
.brand-text {
  font-family: var(--portal-font-display);
  font-weight: 700; font-size: 17px; letter-spacing: -0.03em;
  color: var(--portal-brand, #08545a);
  overflow: hidden; text-overflow: ellipsis;
}
.nav { display: flex; gap: 4px; flex: 1; min-width: 0; }
.nav a {
  color: var(--portal-muted, #6b7c8a);
  text-decoration: none; font-size: 14px; font-weight: 550;
  padding: 8px 12px; border-radius: 8px;
  transition: color 0.2s, background 0.2s;
}
.nav a:hover { color: var(--portal-ink, #15202b); background: color-mix(in srgb, var(--portal-accent-soft, #d7eef0) 70%, transparent); }
.nav a.router-link-active {
  color: var(--portal-accent, #0b6e75);
  background: var(--portal-accent-soft, #d7eef0);
}
.user { display: flex; align-items: center; gap: 8px; color: var(--portal-muted, #6b7c8a); font-size: 13px; flex-shrink: 0; }
.name { max-width: 120px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: var(--portal-ink, #15202b); }
.body {
  flex: 1; max-width: 1080px; width: 100%; margin: 0 auto;
  padding: 22px 20px 48px;
  animation: bodyIn 0.45s ease both;
}
.portal[data-has-stage="1"] .body { padding-top: 18px; }
@keyframes bodyIn {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}
.foot {
  display: flex; justify-content: center; align-items: center; gap: 8px;
  padding: 18px; color: var(--portal-muted, #6b7c8a); font-size: 12px;
  border-top: 1px solid var(--portal-line, #d5dde3);
  letter-spacing: 0.02em;
}
.sep { opacity: 0.45; }
@media (max-width: 720px) {
  .top-inner { gap: 10px; }
  .nav { gap: 2px; overflow-x: auto; }
  .nav a { padding: 8px 10px; font-size: 13px; }
  .brand-text { font-size: 15px; max-width: 132px; }
}
</style>
