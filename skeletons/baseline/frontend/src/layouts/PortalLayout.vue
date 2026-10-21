<template>
  <div
    class="portal"
    :data-has-stage="hasStage ? '1' : '0'"
    :data-shell-nav="navStyle"
    :data-has-side-rail="navSideRail.length ? '1' : '0'"
  >
    <header class="top">
      <div class="top-inner">
        <div class="brand" :title="brandTitle" @click="$router.push(homePath)">
          <img v-if="logoUrl" class="brand-logo" :src="logoUrl" alt="" />
          <span v-else class="brand-mark" aria-hidden="true" />
          <span class="brand-text">{{ brandTitle }}</span>
        </div>
        <nav class="nav">
          <router-link v-for="item in navPrimary" :key="item.to" :to="item.to">{{ item.label }}</router-link>
        </nav>
        <el-input
          v-if="globalSearchOn"
          v-model="topQuery"
          class="top-search"
          clearable
          :placeholder="topSearchPlaceholder"
          @keyup.enter="goTopSearch"
        />
        <div class="user">
          <template v-if="loggedIn">
            <CartBadge v-if="showCartBadge" />
            <MessageBell />
            <el-dropdown trigger="click" class="account-menu" popper-class="portal-account-menu">
              <button type="button" class="account-trigger" :class="{ 'is-active': accountActive }">
                <el-avatar v-if="avatarUrl" :size="28" :src="avatarUrl" />
                <span v-else class="account-avatar-fallback" aria-hidden="true">{{ nameInitial }}</span>
                <span class="name">{{ displayName }}</span>
                <el-icon class="account-caret" :size="12"><ArrowDown /></el-icon>
              </button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item
                    :class="{ 'is-active': route.path === '/account' || accountHubActive }"
                    @click="router.push('/account')"
                  >{{ accountEntryLabel }}</el-dropdown-item>
                  <el-dropdown-item
                    v-if="profileEditable"
                    :class="{ 'is-active': route.path === '/profile' }"
                    @click="router.push('/profile')"
                  >{{ profileEntryLabel }}</el-dropdown-item>
                  <el-dropdown-item divided @click="logout">退出</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </template>
          <template v-else>
            <el-button
              v-if="showGuestAccountEntry"
              link
              class="btn-guest-account"
              :class="{ 'is-active': route.path === '/account' || accountHubActive }"
              @click="$router.push('/account')"
            >{{ accountEntryLabel }}</el-button>
            <el-button
              class="btn-login"
              type="primary"
              round
              @click="$router.push({ path: '/login', query: { redirect: $route.fullPath } })"
            >登录</el-button>
            <el-button class="btn-reg" round @click="$router.push('/register')">注册</el-button>
          </template>
        </div>
      </div>
    </header>
    <PortalSideRail :items="navSideRail" />

    <div v-if="hasStage" class="stage">
      <PortalCarousel />
    </div>
    <el-alert
      v-if="maintenanceOn"
      class="portal-maint"
      type="warning"
      :closable="false"
      show-icon
      :title="maintenanceText"
    />

    <main class="body">
      <router-view />
    </main>
    <footer class="foot">
      <div class="foot-inner">
        <span class="foot-brand">{{ footer.brand }}</span>
        <span class="sep">·</span>
        <span class="foot-tag">{{ footer.tagline }}</span>
        <span class="sep">·</span>
        <span class="foot-ver">{{ systemVersion }}</span>
        <el-button class="no-print foot-print" link type="primary" @click="printCurrentPage">打印本页</el-button>
      </div>
    </footer>
    <AiAssistantFloat />
    <ForceNoticeGate />
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowDown } from '@element-plus/icons-vue'
import http from '../api/http'
import { APP_DELIVERED } from '../appDelivered.js'
import AiAssistantFloat from '../components/AiAssistantFloat.vue'
import CartBadge from '../components/CartBadge.vue'
import ForceNoticeGate from '../components/ForceNoticeGate.vue'
import MessageBell from '../components/MessageBell.vue'
import PortalCarousel from '../components/PortalCarousel.vue'
import PortalSideRail from '../components/PortalSideRail.vue'
import { portalFooterCopy } from '../utils/domainFlavor.js'
import { printCurrentPage } from '../utils/printPage.js'
import { getSchema, menuLabel, schemaLabels, schemaMenus } from '../utils/domainSchema.js'
import { portalBrandHomePath, userMenuPath } from '../utils/menuRoutes.js'
import { navItemActive } from '../utils/navOverflow.js'
import {
  ACCOUNT_KEYS,
  PROFILE_ENTRY_LABEL,
  accountChromeLabel,
  accountFaceFromDelivered,
  cartUsesChromeBadge,
  classifyPortalMenus,
  shellModeFromDelivered,
  shellNavStyleFromDelivered,
} from '../utils/portalShellNav.js'
import { chromeDisplayName, isGuestBrowseEnabled, isLoggedIn, onProfileDisplayChange } from '../utils/session.js'

const router = useRouter()
const route = useRoute()
const labels = schemaLabels()
const title = labels.appName || APP_DELIVERED.title || import.meta.env.VITE_APP_TITLE || '毕设系统'
const siteName = ref('')
const logoUrl = ref('')
const maintenanceOn = ref(false)
const maintenanceText = ref(labels.maintenanceDefaultText || '系统维护中，部分功能暂不可用')
const brandTitle = computed(() => siteName.value || title)
const footer = computed(() => portalFooterCopy())
const systemVersion = computed(
  () =>
    labels.systemVersionLabel ||
    import.meta.env.VITE_APP_VERSION ||
    'v1.0.0',
)
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
  const k = 'gf_pv_bumped'
  if (!sessionStorage.getItem(k)) {
    sessionStorage.setItem(k, '1')
    http.post('/api/site-stat/pv').catch(() => {})
  }
  if (getSchema()?.orgCrosscut?.siteSettings) {
    http.get('/api/site-settings').then((res) => {
      const d = res.data || {}
      if (d.siteName) siteName.value = String(d.siteName).trim()
      logoUrl.value = d.logoUrl ? String(d.logoUrl).trim() : ''
      maintenanceOn.value = !!d.maintenanceOn
      if (d.maintenanceText) maintenanceText.value = String(d.maintenanceText).trim()
    }).catch(() => {})
  }
})
onUnmounted(() => offProfileDisplay?.())

const displayName = computed(() => chromeDisplayName(nickname.value, username.value, ''))
const nameInitial = computed(() => {
  const s = String(displayName.value || '我').trim()
  return s ? s.slice(0, 1) : '我'
})
const hasStage = computed(() => {
  const style = String(APP_DELIVERED?.portalHomeStyle || '').trim()
  return style !== 'editorial' && style !== 'mall'
})

const GUEST_MENU_KEYS = new Set(['home', 'archive', 'content', 'guestbook', 'slots'])

function mapUserMenus(menus) {
  return menus
    .map((m) => ({
      key: m.key,
      to: userMenuPath(m.key),
      label: m.navSection ? `${m.navSection} · ${m.label}` : m.label,
    }))
    .filter((m) => m.to)
}

/** 全量用户菜单：账户短页 / 右侧栏与登录态一致，避免登录前后壳跳脸 */
const allNavItems = computed(() => {
  const menus = schemaMenus('user').filter(
    (m) => m.key !== 'profile' && m.key !== 'home' && m.key !== 'ai_assistant',
  )
  const mapped = mapUserMenus(menus)
  if (mapped.length) return mapped
  return [{
    key: 'content',
    to: '/notices',
    label: menuLabel('user', 'content', '公告'),
  }]
})

/** 顶栏主链：游客仍只露可逛项 */
const navItems = computed(() => {
  const menus = schemaMenus('user').filter(
    (m) => m.key !== 'profile' && m.key !== 'home' && m.key !== 'ai_assistant',
  )
  let list = menus
  if (!loggedIn.value && isGuestBrowseEnabled()) {
    list = menus.filter((m) => GUEST_MENU_KEYS.has(m.key))
  } else if (!loggedIn.value) {
    list = menus.filter((m) => m.key === 'content' || m.key === 'guestbook' || m.key === 'archive')
  }
  const mapped = mapUserMenus(list)
  if (mapped.length) return mapped
  return [{
    key: 'content',
    to: '/notices',
    label: menuLabel('user', 'content', '公告'),
  }]
})

const shellMode = computed(() => shellModeFromDelivered(APP_DELIVERED))
const navStyle = computed(() => shellNavStyleFromDelivered(APP_DELIVERED))
const accountFace = computed(() => accountFaceFromDelivered(APP_DELIVERED))
const accountEntryLabel = computed(() => accountChromeLabel(accountFace.value))
const profileEntryLabel = PROFILE_ENTRY_LABEL
const navClassified = computed(() =>
  classifyPortalMenus(navItems.value, shellMode.value, navStyle.value, APP_DELIVERED),
)
const navClassifiedFull = computed(() =>
  classifyPortalMenus(allNavItems.value, shellMode.value, navStyle.value, APP_DELIVERED),
)
const navPrimary = computed(() => navClassified.value.primary)
/** 头像入口高亮只跟账户向键；市集右侧栏里的超额业务不算「账户中心」 */
const accountHubItems = computed(() => {
  const account = navClassifiedFull.value.account || []
  const rail = (navClassifiedFull.value.sideRail || []).filter((m) => ACCOUNT_KEYS.has(m?.key))
  const seen = new Set()
  const out = []
  for (const m of [...account, ...rail]) {
    if (!m?.key || seen.has(m.key)) continue
    seen.add(m.key)
    out.push(m)
  }
  return out
})
const showGuestAccountEntry = computed(() => accountHubItems.value.length > 0)
const navSideRail = computed(() => navClassifiedFull.value.sideRail || [])
const accountHubActive = computed(() =>
  accountHubItems.value.some((item) => navItemActive(route.path, item.to)),
)
const accountActive = computed(() =>
  route.path === '/account'
  || accountHubActive.value
  || (profileEditable && route.path === '/profile'),
)
/** storefront/FOOD：购物车角标；marketplace 购物车在文字短链里 */
const showCartBadge = computed(() =>
  cartUsesChromeBadge(shellMode.value, navStyle.value, APP_DELIVERED),
)

const homePath = computed(() => portalBrandHomePath())
const globalSearchOn = computed(() => {
  if (!getSchema()?.listCrosscut?.globalSearch) return false
  const menus = [...schemaMenus('user'), ...schemaMenus('admin')]
  return menus.some((m) => m.key === 'archive')
})
const topQuery = ref('')
const topSearchPlaceholder = computed(() => schemaLabels().topSearchPlaceholder || '搜索名称')
watch(
  () => [route.path, route.query?.q],
  () => {
    if (route.path === '/archive') {
      topQuery.value = route.query?.q != null ? String(route.query.q) : ''
    }
  },
  { immediate: true },
)
function goTopSearch() {
  const q = topQuery.value.trim()
  if (route.path === '/archive') {
    const next = { ...route.query }
    if (q) next.q = q
    else delete next.q
    router.push({ path: '/archive', query: next })
    return
  }
  if (!q) return
  router.push({ path: '/archive', query: { q } })
}

async function logout() {
  const { logoutOnServer, clearAuthStorage } = await import('../utils/session.js')
  await logoutOnServer()
  clearAuthStorage()
  router.push('/login')
}
</script>

<style scoped>
/* 公共壳：店面顶栏 + 干净底，少毛玻璃双光晕（模板/SaaS 味） */
.portal {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background: var(--portal-bg, #f4f6f5);
  color: var(--portal-ink, #15202b);
  font-family: var(--portal-font-ui);
}
.top {
  position: sticky;
  top: 0;
  z-index: 20;
  background: var(--portal-surface, #fff);
  border-bottom: 1px solid var(--portal-line, #e2e8e6);
  box-shadow: 0 1px 0 color-mix(in srgb, var(--portal-accent, #0b6e75) 18%, transparent);
}
.top-inner {
  max-width: 1120px;
  margin: 0 auto;
  min-height: 58px;
  height: auto;
  padding: 10px 22px;
  display: flex;
  align-items: center;
  gap: 14px 22px;
  flex-wrap: wrap;
}
.brand {
  display: flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
  flex-shrink: 1;
  min-width: 0;
  max-width: 40%;
}
.brand-mark {
  width: 28px;
  height: 28px;
  border-radius: 8px;
  flex-shrink: 0;
  background: linear-gradient(
    145deg,
    var(--portal-accent, #0b6e75),
    var(--portal-brand, #08545a)
  );
  box-shadow: 0 2px 8px color-mix(in srgb, var(--portal-accent, #0b6e75) 28%, transparent);
}
.brand-logo {
  width: 28px;
  height: 28px;
  border-radius: 8px;
  flex-shrink: 0;
  object-fit: cover;
}
.top-search {
  width: 200px;
  flex: 0 1 200px;
}
.top-search :deep(.el-input__wrapper) {
  border-radius: 999px;
  box-shadow: 0 0 0 1px var(--portal-line, #e2e8e6) inset;
  background: color-mix(in srgb, var(--portal-bg, #f4f6f5) 70%, var(--portal-surface, #fff));
}
.top-search :deep(.el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 1px var(--portal-accent, #0b6e75) inset;
}
.portal-maint { border-radius: 0; }
.brand-text {
  font-family: var(--portal-font-display);
  font-weight: 750;
  font-size: 17px;
  letter-spacing: var(--portal-display-tracking, -0.01em);
  color: var(--portal-ink, #15202b);
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.nav {
  display: flex;
  gap: 2px;
  flex: 1 1 280px;
  flex-wrap: nowrap;
  align-items: center;
  min-width: 0;
}
.nav a {
  position: relative;
  padding: 8px 12px;
  border-radius: 0;
  font-size: 14px;
  font-weight: 550;
  color: var(--portal-muted, #5b6b76);
  text-decoration: none;
  white-space: nowrap;
  flex-shrink: 0;
  background: transparent;
}
.nav a:hover {
  color: var(--portal-ink, #15202b);
  background: transparent;
}
.nav a.router-link-active {
  color: var(--portal-brand, #08545a);
  font-weight: 650;
  background: transparent;
}
.nav a.router-link-active::after {
  content: '';
  position: absolute;
  left: 12px;
  right: 12px;
  bottom: 2px;
  height: 2px;
  border-radius: 1px;
  background: var(--portal-accent, #0b6e75);
}
.user {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-left: auto;
}
.user :deep(.el-button.is-link),
.user :deep(.el-button.is-text) {
  height: auto;
  min-height: 0;
  padding: 4px 6px;
}
.btn-login {
  --el-button-bg-color: var(--portal-accent, #0b6e75);
  --el-button-border-color: var(--portal-accent, #0b6e75);
  --el-button-hover-bg-color: var(--portal-brand, #08545a);
  --el-button-hover-border-color: var(--portal-brand, #08545a);
  font-weight: 600;
}
.btn-reg {
  --el-button-bg-color: var(--portal-surface, #fff);
  --el-button-text-color: var(--portal-brand, #08545a);
  --el-button-border-color: color-mix(in srgb, var(--portal-accent, #0b6e75) 45%, var(--portal-line, #e2e8e6));
  --el-button-hover-bg-color: var(--portal-accent-soft, #e8f3f2);
  --el-button-hover-text-color: var(--portal-brand, #08545a);
  --el-button-hover-border-color: var(--portal-accent, #0b6e75);
  font-weight: 600;
}
.btn-guest-account.is-active {
  color: var(--portal-brand, #08545a);
}
.account-trigger {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  margin: 0;
  padding: 2px 8px 2px 2px;
  border: 1px solid transparent;
  border-radius: 999px;
  background: transparent;
  color: inherit;
  cursor: pointer;
}
.account-trigger:hover,
.account-trigger.is-active {
  background: var(--portal-accent-soft, #e8f3f2);
  border-color: color-mix(in srgb, var(--portal-accent, #0b6e75) 22%, transparent);
}
.account-avatar-fallback {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  display: grid;
  place-items: center;
  font-size: 12px;
  font-weight: 600;
  color: #fff;
  background: var(--portal-accent, #0b6e75);
}
.account-caret { color: var(--portal-muted, #94a3b8); }
.account-guest-trig {
  padding: 6px 10px;
  border-radius: var(--portal-radius-sm, 8px);
  font-size: 13px;
  color: var(--portal-muted, #5b6b76);
  cursor: pointer;
}
.account-guest-trig:hover,
.account-guest-trig.is-active {
  color: var(--portal-ink, #15202b);
  background: var(--portal-accent-soft, #e8f3f2);
}
.name {
  font-size: 13px;
  color: var(--portal-ink, #334155);
  max-width: 96px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.portal[data-has-side-rail='1'] .body,
.portal[data-has-side-rail='1'] .stage,
.portal[data-has-side-rail='1'] .foot {
  padding-right: 72px;
}
.portal[data-has-side-rail='1'] :deep(.ai-float) {
  right: 84px;
}
.body {
  flex: 1;
  max-width: 1120px;
  width: 100%;
  margin: 0 auto;
  padding: 22px 22px 48px;
  box-sizing: border-box;
}
.foot {
  padding: 18px 22px;
  text-align: center;
  font-size: 12px;
  color: var(--portal-muted, #5b6b76);
  border-top: 1px solid var(--portal-line, #e2e8e6);
  background: color-mix(in srgb, var(--portal-surface, #fff) 88%, var(--portal-bg, #f4f6f5));
}
.foot-inner {
  max-width: 1120px;
  margin: 0 auto;
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  align-items: baseline;
  gap: 0 2px;
}
.foot-brand {
  font-family: var(--portal-font-display);
  font-weight: 650;
  color: var(--portal-ink, #15202b);
  max-width: 100%;
  overflow-wrap: anywhere;
}
.foot-tag { opacity: 0.92; }
.foot-ver { opacity: 0.85; font-variant-numeric: tabular-nums; }
.foot-print { margin-left: 8px; font-size: 12px; }
.sep { margin: 0 6px; opacity: 0.5; }
</style>
