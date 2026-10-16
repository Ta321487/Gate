<template>
  <el-container class="layout workbench">
    <el-aside width="208px" class="wb-aside" :class="{ 'wb-aside--dense': asideDense }">
      <div class="wb-brand">
        <span class="wb-brand-mark" aria-hidden="true" />
        <span>管理后台</span>
      </div>
      <div class="wb-menu-scroll">
        <el-menu :default-active="active" router class="wb-menu">
          <template v-for="group in menuGroups" :key="group.title || '_flat'">
            <el-menu-item-group v-if="group.title" :title="group.title">
              <el-menu-item
                v-for="item in group.items"
                :key="item.index"
                :index="item.index"
                :title="item.label"
              >
                <span>{{ item.label }}</span>
                <el-badge
                  v-if="menuBadge(item.key)"
                  :value="menuBadge(item.key)"
                  :max="99"
                  class="menu-badge"
                  :type="menuBadgeType(item.key)"
                />
              </el-menu-item>
            </el-menu-item-group>
            <template v-else>
              <el-menu-item
                v-for="item in group.items"
                :key="item.index"
                :index="item.index"
                :title="item.label"
              >
                <span>{{ item.label }}</span>
                <el-badge
                  v-if="menuBadge(item.key)"
                  :value="menuBadge(item.key)"
                  :max="99"
                  class="menu-badge"
                  :type="menuBadgeType(item.key)"
                />
              </el-menu-item>
            </template>
          </template>
          <el-menu-item v-if="profileEditable" index="/admin/profile">个人资料</el-menu-item>
        </el-menu>
      </div>
    </el-aside>
    <el-container>
      <el-header class="wb-header">
        <span class="wb-header-title" :title="headerTitle">
          <img v-if="logoUrl" class="wb-logo" :src="logoUrl" alt="" />
          {{ headerTitle }}
        </span>
        <el-input
          v-if="globalSearchOn"
          v-model="topQuery"
          class="wb-top-search"
          clearable
          :placeholder="topSearchPlaceholder"
          @keyup.enter="goTopSearch"
        />
        <div class="wb-header-right">
          <span class="wb-ver no-print">{{ systemVersion }}</span>
          <el-button class="no-print" link type="primary" @click="printCurrentPage">打印本页</el-button>
          <MessageBell />
          <span>{{ displayName }} · {{ adminRoleLabel }}</span>
          <el-button link type="primary" @click="logout">退出</el-button>
        </div>
      </el-header>
      <el-alert
        v-if="maintenanceOn"
        class="wb-maint"
        type="warning"
        :closable="false"
        show-icon
        :title="maintenanceText"
      />
      <el-main class="wb-main">
        <router-view />
      </el-main>
    </el-container>
    <ForceNoticeGate />
  </el-container>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import ForceNoticeGate from '../components/ForceNoticeGate.vue'
import http from '../api/http'
import MessageBell from '../components/MessageBell.vue'
import { APP_DELIVERED } from '../appDelivered.js'
import { getSchema, isSuperOnlyMenu, schemaLabels, schemaMenus } from '../utils/domainSchema.js'
import { adminLoginPath } from '../utils/authEntry.js'
import {
  clerkAllowedMenuKeys,
  currentStaffPost,
  staffPostLabel,
} from '../utils/staffPosts.js'
import { adminMenuPath } from '../utils/menuRoutes.js'
import { printCurrentPage } from '../utils/printPage.js'
import { adminAsideDense } from '../utils/navOverflow.js'
import { onProfileDisplayChange } from '../utils/session.js'

const route = useRoute()
const router = useRouter()
const labels = schemaLabels()
const systemVersion =
  labels.systemVersionLabel || import.meta.env.VITE_APP_VERSION || 'v1.0.0'
const title = labels.appName || APP_DELIVERED.title || import.meta.env.VITE_APP_TITLE || '毕设系统'
const siteName = ref('')
const logoUrl = ref('')
const maintenanceOn = ref(false)
const maintenanceText = ref(labels.maintenanceDefaultText || '系统维护中，部分功能暂不可用')
const headerTitle = computed(() => siteName.value || title)
const username = localStorage.getItem('username') || ''
const nickname = ref(localStorage.getItem('nickname') || '')
const profileEditable = localStorage.getItem('profileEditable') !== 'false'
const superAdmin = localStorage.getItem('superAdmin') === 'true'
const staffPost = currentStaffPost()
const displayName = computed(() => nickname.value || username)
const active = computed(() => route.path)
const pendingTickets = ref(0)
const menuTick = ref(0)
const pendingOrders = ref(0)
const pendingReservations = ref(0)
const missingCheckin = ref(0)

let offProfileDisplay
let dashTimer = null

function menuBadge(key) {
  if (key === 'ticket_pending') return pendingTickets.value || 0
  if (key === 'orders') return pendingOrders.value || 0
  if (key === 'reservations') return pendingReservations.value || 0
  if (key === 'archive_logs' || key === 'archive_log') return missingCheckin.value || 0
  return 0
}

function menuBadgeType(key) {
  if (key === 'archive_logs' || key === 'archive_log') return 'danger'
  return undefined
}

async function refreshPending() {
  try {
    const res = await http.get('/api/admin/dashboard/counts')
    pendingTickets.value = Number(res.data?.pendingTickets || 0)
    pendingOrders.value = Number(res.data?.pendingOrders || 0)
    pendingReservations.value = Number(res.data?.pendingReservations || 0)
    missingCheckin.value = Number(res.data?.missingCheckinToday || 0)
  } catch {
    pendingTickets.value = 0
    pendingOrders.value = 0
    pendingReservations.value = 0
    missingCheckin.value = 0
  }
}

async function refreshSiteSettings() {
  if (!getSchema()?.orgCrosscut?.siteSettings) return
  try {
    const res = await http.get('/api/site-settings')
    const d = res.data || {}
    if (d.siteName) siteName.value = String(d.siteName).trim()
    logoUrl.value = d.logoUrl ? String(d.logoUrl).trim() : ''
    maintenanceOn.value = !!d.maintenanceOn
    if (d.maintenanceText) maintenanceText.value = String(d.maintenanceText).trim()
  } catch {
    /* ignore */
  }
}

onMounted(() => {
  offProfileDisplay = onProfileDisplayChange(({ nickname: n }) => {
    nickname.value = n || ''
  })
  refreshPending()
  refreshSiteSettings()
  if (getSchema()?.orgCrosscut?.roleMenus) {
    http.get('/api/auth/menu-keys').then((res) => {
      const d = res.data || {}
      import('../utils/staffPosts.js').then((m) => {
        m.setMenuKeyOverride?.(d.keys, d.usePacks !== false)
        menuTick.value += 1
      })
    }).catch(() => {})
  }
  dashTimer = setInterval(refreshPending, 60000)
})
onUnmounted(() => {
  offProfileDisplay?.()
  if (dashTimer) clearInterval(dashTimer)
})

const globalSearchOn = computed(() => {
  if (!getSchema()?.listCrosscut?.globalSearch) return false
  return schemaMenus('admin').some((m) => m.key === 'archive') || schemaMenus('user').some((m) => m.key === 'archive')
})
const topQuery = ref('')
const topSearchPlaceholder = computed(() => schemaLabels().topSearchPlaceholder || '搜索名称')
function goTopSearch() {
  const q = topQuery.value.trim()
  if (!q) return
  router.push({ path: '/admin/archive', query: { q } })
}

const adminRoleLabel = computed(() => {
  const roles = getSchema()?.roles || {}
  if (superAdmin) return roles.admin?.label || '总管理员'
  return staffPostLabel(staffPost, roles.subadmin?.label || '经办员')
})

const menuItems = computed(() => {
  void menuTick.value
  const menus = schemaMenus('admin')
  const raw = menus.length
    ? menus.map((m) => ({
        key: m.key,
        index: adminMenuPath(m.key),
        label: m.label,
        navSection: m.navSection || '',
        superOnly: isSuperOnlyMenu(m),
      })).filter((m) => m.index)
    : [
        { key: 'dashboard', index: '/admin/dashboard', label: '工作台', navSection: '', superOnly: false },
        { key: 'ticket_pending', index: '/admin/tickets', label: '待办受理', navSection: '', superOnly: false },
        { key: 'ticket_records', index: '/admin/ticket-records', label: '办理记录', navSection: '', superOnly: false },
        { key: 'lookup_site', index: '/admin/sites', label: '楼栋房间', navSection: '', superOnly: true },
        { key: 'lookup_type', index: '/admin/types', label: '类型管理', navSection: '', superOnly: true },
        { key: 'users', index: '/admin/users', label: '用户管理', navSection: '', superOnly: true },
        { key: 'guestbook', index: '/admin/guestbook', label: '留言管理', navSection: '', superOnly: true },
        { key: 'content', index: '/admin/notices', label: '公告管理', navSection: '', superOnly: true },
      ]
  let items = raw.filter((m) => superAdmin || !m.superOnly)
  if (!superAdmin) {
    const allowed = clerkAllowedMenuKeys(staffPost)
    if (allowed) {
      items = items.filter(
        (m) => allowed.has(m.key) || m.key === 'messages' || m.key === 'dm' || m.key === 'order_reviews',
      )
    }
  }
  if (!items.some((m) => m.key === 'messages')) {
    const dashAt = items.findIndex((m) => m.key === 'dashboard')
    items.splice(dashAt >= 0 ? dashAt + 1 : 0, 0, {
      key: 'messages',
      index: '/admin/messages',
      label: '消息',
      navSection: '',
      superOnly: false,
    })
  }
  return items
})

/** 真交叉 GENERIC：按 navSection 分区；无分区时保持扁平 */
const menuGroups = computed(() => {
  const items = menuItems.value
  const hasSection = items.some((m) => m.navSection)
  if (!hasSection) return [{ title: '', items }]
  const order = []
  const buckets = new Map()
  for (const item of items) {
    const title = item.navSection || ''
    if (!buckets.has(title)) {
      buckets.set(title, [])
      order.push(title)
    }
    buckets.get(title).push(item)
  }
  return order.map((title) => ({ title, items: buckets.get(title) }))
})

const asideDense = computed(() =>
  adminAsideDense(menuItems.value.length + (profileEditable ? 1 : 0)),
)

async function logout() {
  const { logoutOnServer, clearAuthStorage } = await import('../utils/session.js')
  await logoutOnServer()
  clearAuthStorage()
  router.push(adminLoginPath())
}
</script>

<style scoped>
.layout { min-height: 100vh; }
.menu-badge {
  margin-left: 8px;
}
.wb-menu :deep(.el-menu-item) {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.wb-top-search { width: 200px; margin-left: 16px; }
.wb-ver {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  margin-right: 4px;
  font-variant-numeric: tabular-nums;
}
.wb-header-right {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-left: auto;
}
.wb-logo {
  height: 22px;
  width: auto;
  margin-right: 8px;
  vertical-align: middle;
  border-radius: 4px;
}
.wb-maint {
  margin: 0 16px 0;
  border-radius: 0;
}
</style>
