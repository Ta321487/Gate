<template>
  <div class="account-center" :data-account-face="accountFace">
    <div class="af-page-bg">
      <div class="af-shell">
        <div class="af-side">
          <section class="hero af-hero">
            <h1>{{ faceCopy.title }}</h1>
            <p>{{ faceCopy.lead }}</p>
          </section>

          <section class="card identity af-identity">
            <template v-if="loggedIn">
              <div class="avatar-slot">
                <el-avatar :size="72" :src="avatarUrl || undefined" class="avatar">
                  {{ nameInitial }}
                </el-avatar>
              </div>
              <div class="who">
                <div class="nick">{{ displayName }}</div>
                <div class="uid">@{{ username }}</div>
                <div v-if="profileEditable" class="id-actions">
                  <el-button type="primary" link @click="$router.push('/profile')">{{ profileEntryLabel }}</el-button>
                </div>
              </div>
            </template>
            <template v-else>
              <div class="avatar-slot">
                <el-avatar :size="72" class="avatar">游</el-avatar>
              </div>
              <div class="who">
                <div class="nick">游客</div>
                <div class="uid">登录后可改资料并使用账户功能</div>
                <div class="id-actions">
                  <el-button type="primary" @click="goLogin">登录</el-button>
                  <el-button link @click="$router.push('/register')">注册</el-button>
                </div>
              </div>
            </template>
          </section>
        </div>

        <div class="af-main">
          <el-empty v-if="!groups.length" description="暂无账户入口" />

          <section v-for="g in groups" :key="g.id" class="block">
            <h2 class="block-title">{{ g.title }}</h2>
            <div class="hub-grid af-hub-grid">
              <a
                v-for="item in g.items"
                :key="item.key"
                href="#"
                class="hub-tile af-hub-tile"
                @click.prevent="goHub(item)"
              >
                <span class="hub-label">{{ item.label }}</span>
              </a>
            </div>
          </section>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { APP_DELIVERED } from '../../appDelivered.js'
import { schemaMenus } from '../../utils/domainSchema.js'
import { userMenuPath } from '../../utils/menuRoutes.js'
import {
  PROFILE_ENTRY_LABEL,
  accountFaceCopy,
  accountFaceFromDelivered,
  collectAccountHubItems,
  groupAccountHubItems,
} from '../../utils/portalShellNav.js'
import { chromeDisplayName, isLoggedIn, onProfileDisplayChange, requireLogin } from '../../utils/session.js'

const router = useRouter()
const route = useRoute()
const profileEditable = localStorage.getItem('profileEditable') !== 'false'
const accountFace = computed(() => accountFaceFromDelivered(APP_DELIVERED))
const faceCopy = computed(() => accountFaceCopy(accountFace.value))
const profileEntryLabel = PROFILE_ENTRY_LABEL

const loggedIn = ref(isLoggedIn())
const username = ref(localStorage.getItem('username') || '')
const nickname = ref(localStorage.getItem('nickname') || '')
const avatarUrl = ref(localStorage.getItem('avatarUrl') || '')

function refreshUser() {
  loggedIn.value = isLoggedIn()
  username.value = localStorage.getItem('username') || ''
  nickname.value = localStorage.getItem('nickname') || ''
  avatarUrl.value = localStorage.getItem('avatarUrl') || ''
}

watch(() => route.fullPath, refreshUser)

let offProfile
onMounted(() => {
  refreshUser()
  offProfile = onProfileDisplayChange(({ nickname: n, avatarUrl: a }) => {
    nickname.value = n || ''
    avatarUrl.value = a || ''
  })
})
onUnmounted(() => offProfile?.())

const displayName = computed(() => chromeDisplayName(nickname.value, username.value, '我'))
const nameInitial = computed(() => {
  const s = String(displayName.value || '我').trim()
  return s ? s.slice(0, 1) : '我'
})

const hubItems = computed(() => {
  const menus = schemaMenus('user')
    .filter((m) => m && m.key)
    .map((m) => ({
      key: m.key,
      to: userMenuPath(m.key),
      label: m.label || m.key,
    }))
    .filter((m) => m.to)
  return collectAccountHubItems(menus)
})

const groups = computed(() => groupAccountHubItems(hubItems.value))

function goLogin() {
  router.push({ path: '/login', query: { redirect: '/account' } })
}

function goHub(item) {
  if (!item?.to) return
  if (!requireLogin(router, item.to)) return
  router.push(item.to)
}
</script>

<style scoped>
.account-center {
  max-width: 880px;
  margin: 0 auto;
  padding: 8px 4px 32px;
}
.af-page-bg {
  min-width: 0;
}
.af-shell {
  min-width: 0;
}
.af-main {
  min-width: 0;
}
.hero {
  margin-bottom: 20px;
  padding: 4px 0;
}
.hero h1 {
  margin: 0 0 8px;
  font-family: var(--portal-font-display);
  font-size: 28px;
  letter-spacing: -0.03em;
  color: var(--portal-ink, #15202b);
}
.hero p {
  margin: 0;
  color: var(--portal-muted, #6b7c8a);
  font-size: 14px;
  line-height: 1.55;
  max-width: 36em;
}
.card {
  background: var(--portal-surface, #fff);
  border: var(--portal-border-width, 1px) solid var(--portal-line, #dfe7ec);
  border-radius: var(--portal-radius, 12px);
  box-shadow: var(--portal-shadow, none);
  padding: 20px 22px;
  margin-bottom: 14px;
}
.identity {
  display: flex;
  align-items: center;
  gap: 18px;
}
.avatar-slot {
  position: relative;
  flex-shrink: 0;
}
.avatar {
  background: var(--portal-cover, linear-gradient(160deg, #0b6e75, #08545a));
  color: #fff;
  font-size: 26px;
  font-weight: 700;
}
.who .nick {
  font-size: 20px;
  font-weight: 700;
  letter-spacing: -0.02em;
  color: var(--portal-ink, #15202b);
  margin-bottom: 4px;
}
.who .uid {
  font-size: 13px;
  color: var(--portal-muted, #6b7c8a);
}
.id-actions {
  margin-top: 10px;
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  align-items: center;
}
.block {
  margin-bottom: 22px;
}
.block-title {
  margin: 0 0 10px;
  font-size: 13px;
  font-weight: 600;
  color: var(--portal-muted, #5b6b76);
}
.hub-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(168px, 1fr));
  gap: 10px;
}
.hub-tile {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  min-height: 52px;
  padding: 12px 14px 12px 12px;
  border-radius: var(--portal-radius-sm, 8px);
  border: 1px solid color-mix(in srgb, var(--portal-line, #d5dde3) 65%, var(--portal-accent, #0b6e75) 35%);
  border-left: 3px solid var(--portal-accent, #0b6e75);
  background: var(--portal-surface, #fff);
  box-shadow: 0 1px 2px color-mix(in srgb, var(--portal-ink, #15202b) 7%, transparent);
  color: var(--portal-ink, #15202b);
  text-decoration: none;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: border-color 0.15s ease, background 0.15s ease, box-shadow 0.15s ease, transform 0.15s ease;
}
.hub-tile::after {
  content: '';
  width: 7px;
  height: 7px;
  flex-shrink: 0;
  border-right: 2px solid color-mix(in srgb, var(--portal-muted, #5b6b76) 80%, transparent);
  border-bottom: 2px solid color-mix(in srgb, var(--portal-muted, #5b6b76) 80%, transparent);
  transform: rotate(-45deg);
  opacity: 0.7;
}
.hub-tile:hover {
  border-color: var(--portal-accent, #0b6e75);
  background: color-mix(in srgb, var(--portal-accent, #0b6e75) 12%, var(--portal-surface, #fff));
  box-shadow: 0 2px 8px color-mix(in srgb, var(--portal-accent, #0b6e75) 22%, transparent);
  transform: translateY(-1px);
}
.hub-label {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  min-width: 0;
}
:global(html[data-scheme='dark']) .hub-tile,
:global([data-scheme='dark']) .hub-tile {
  background: color-mix(in srgb, var(--portal-surface, #1c2430) 72%, #fff 28%);
  border-color: color-mix(in srgb, var(--portal-line, #3a4554) 40%, var(--portal-accent, #0b6e75) 60%);
  border-left-color: var(--portal-accent, #5ec8d0);
  color: #f2f5f8;
  box-shadow: 0 1px 0 color-mix(in srgb, #fff 10%, transparent);
}
:global(html[data-scheme='dark']) .hub-tile:hover,
:global([data-scheme='dark']) .hub-tile:hover {
  background: color-mix(in srgb, var(--portal-accent, #0b6e75) 28%, var(--portal-surface, #1c2430) 72%);
  color: #fff;
}
:global(html[data-scheme='dark']) .hub-tile::after,
:global([data-scheme='dark']) .hub-tile::after {
  border-color: color-mix(in srgb, #fff 70%, transparent);
}
@media (max-width: 720px) {
  .hero h1 {
    font-size: 22px;
  }
}
</style>
