<template>
  <div class="portal" :data-has-stage="hasStage ? '1' : '0'">
    <header class="top">
      <div class="top-inner">
        <div class="brand" :title="title" @click="$router.push(homePath)">
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
    <AiAssistantFloat />
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { APP_DELIVERED } from '../appDelivered.js'
import AiAssistantFloat from '../components/AiAssistantFloat.vue'
import MessageBell from '../components/MessageBell.vue'
import PortalCarousel from '../components/PortalCarousel.vue'
import { portalFooterCopy } from '../utils/domainFlavor.js'
import { menuLabel, schemaLabels, schemaMenus } from '../utils/domainSchema.js'
import { userMenuPath } from '../utils/menuRoutes.js'
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
  const style = String(APP_DELIVERED?.portalHomeStyle || '').trim()
  if (style === 'editorial' || style === 'mall') return false
  const list = APP_DELIVERED?.portalBanners
  return Array.isArray(list) && list.some((x) => x && x.src)
})

const GUEST_MENU_KEYS = new Set(['home', 'archive', 'content', 'guestbook', 'slots'])

const nav = computed(() => {
  // 资料留在右侧按钮；AI 助手走右下角悬浮弹窗，避免顶栏再占一项
  const menus = schemaMenus('user').filter(
    (m) => m.key !== 'profile' && m.key !== 'home' && m.key !== 'ai_assistant',
  )
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
    .map((m) => ({ to: userMenuPath(m.key), label: m.label }))
    .filter((m) => m.to)
})

/** 品牌点击：资讯/商城首页落 /home，其它壳走根 redirect */
const homePath = computed(() => {
  const style = String(APP_DELIVERED?.portalHomeStyle || '').trim()
  return style === 'editorial' || style === 'mall' ? '/home' : '/'
})

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
    linear-gradient(180deg, var(--portal-bg, #eef3f5) 0%, color-mix(in srgb, var(--portal-bg, #eef3f5) 88%, var(--portal-surface, #fff)) 100%);
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
  min-height: 60px; height: auto; padding: 8px 20px;
  display: flex; align-items: center; gap: 12px 20px;
  flex-wrap: wrap;
}
.brand {
  display: flex; align-items: center; gap: 10px;
  cursor: pointer; flex-shrink: 1; min-width: 0; max-width: 36%;
}
.brand-mark {
  width: 22px; height: 22px; border-radius: var(--portal-radius-sm, 6px); flex-shrink: 0;
  background: linear-gradient(135deg, var(--portal-accent, #0b6e75), color-mix(in srgb, var(--portal-accent, #0b6e75) 40%, var(--portal-brand, #08545a)));
}
.brand-text {
  font-family: var(--portal-font-display);
  font-weight: 700; font-size: 15px; letter-spacing: var(--portal-display-tracking, 0.02em);
  min-width: 0;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
/* 项多时整词换行到下一行，禁止挤成竖排、也不靠横滑藏菜单 */
.nav { display: flex; gap: 4px; flex: 1 1 280px; flex-wrap: wrap; min-width: 0; }
.nav a {
  padding: 6px 12px; border-radius: var(--portal-radius-sm, 8px); font-size: 13px; font-weight: 500;
  color: var(--portal-muted, #5b6b76); text-decoration: none;
  white-space: nowrap;
  flex-shrink: 0;
}
.nav a.router-link-active,
.nav a:hover { color: var(--portal-ink, #15202b); background: color-mix(in srgb, var(--portal-accent, #0b6e75) 12%, transparent); }
.user { display: flex; align-items: center; gap: 8px; margin-left: auto; }
.user :deep(.el-button.is-link),
.user :deep(.el-button.is-text) {
  height: auto;
  min-height: 0;
  padding: 4px 6px;
}
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
  max-width: 100%;
  overflow-wrap: anywhere;
}
.foot-tag { opacity: 0.92; }
.sep { margin: 0 6px; opacity: 0.5; }
</style>
