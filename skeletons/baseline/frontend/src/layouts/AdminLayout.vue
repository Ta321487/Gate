<template>
  <el-container class="layout workbench">
    <el-aside width="208px" class="wb-aside">
      <div class="wb-brand">
        <span class="wb-brand-mark" aria-hidden="true" />
        <span>管理后台</span>
      </div>
      <el-menu :default-active="active" router class="wb-menu">
        <el-menu-item
          v-for="item in menuItems"
          :key="item.index"
          :index="item.index"
          :title="item.label"
        >
          <span>{{ item.label }}</span>
          <el-badge
            v-if="item.key === 'ticket_pending' && pendingTickets > 0"
            :value="pendingTickets"
            :max="99"
            class="menu-badge"
          />
          <el-badge
            v-else-if="(item.key === 'archive_logs' || item.key === 'archive_log') && missingCheckin > 0"
            :value="missingCheckin"
            :max="99"
            class="menu-badge"
            type="danger"
          />
        </el-menu-item>
        <el-menu-item v-if="profileEditable" index="/admin/profile">个人资料</el-menu-item>
      </el-menu>
    </el-aside>
    <el-container>
      <el-header class="wb-header">
        <span class="wb-header-title" :title="title">{{ title }}</span>
        <div class="wb-header-right">
          <MessageBell />
          <span>{{ displayName }} · {{ adminRoleLabel }}</span>
          <el-button link type="primary" @click="logout">退出</el-button>
        </div>
      </el-header>
      <el-main class="wb-main">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
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
import { onProfileDisplayChange } from '../utils/session.js'

const route = useRoute()
const router = useRouter()
const labels = schemaLabels()
const title = labels.appName || APP_DELIVERED.title || import.meta.env.VITE_APP_TITLE || '毕设系统'
const username = localStorage.getItem('username') || ''
const nickname = ref(localStorage.getItem('nickname') || '')
const profileEditable = localStorage.getItem('profileEditable') !== 'false'
const superAdmin = localStorage.getItem('superAdmin') === 'true'
const staffPost = currentStaffPost()
const displayName = computed(() => nickname.value || username)
const active = computed(() => route.path)
const pendingTickets = ref(0)
const missingCheckin = ref(0)

let offProfileDisplay
let dashTimer = null

async function refreshPending() {
  try {
    const res = await http.get('/api/admin/dashboard')
    pendingTickets.value = Number(res.data?.pendingTickets || 0)
    missingCheckin.value = Number(res.data?.missingCheckinToday || 0)
  } catch {
    pendingTickets.value = 0
    missingCheckin.value = 0
  }
}

onMounted(() => {
  offProfileDisplay = onProfileDisplayChange(({ nickname: n }) => {
    nickname.value = n || ''
  })
  refreshPending()
  dashTimer = setInterval(refreshPending, 60000)
})
onUnmounted(() => {
  offProfileDisplay?.()
  if (dashTimer) clearInterval(dashTimer)
})

const adminRoleLabel = computed(() => {
  const roles = getSchema()?.roles || {}
  if (superAdmin) return roles.admin?.label || '总管理员'
  return staffPostLabel(staffPost, roles.subadmin?.label || '经办员')
})

const menuItems = computed(() => {
  const menus = schemaMenus('admin')
  const raw = menus.length
    ? menus.map((m) => ({
        key: m.key,
        index: adminMenuPath(m.key),
        label: m.label,
        superOnly: isSuperOnlyMenu(m),
      })).filter((m) => m.index)
    : [
        { key: 'dashboard', index: '/admin/dashboard', label: '工作台', superOnly: false },
        { key: 'ticket_pending', index: '/admin/tickets', label: '待办受理', superOnly: false },
        { key: 'ticket_records', index: '/admin/ticket-records', label: '办理记录', superOnly: false },
        { key: 'lookup_site', index: '/admin/sites', label: '楼栋房间', superOnly: true },
        { key: 'lookup_type', index: '/admin/types', label: '类型管理', superOnly: true },
        { key: 'users', index: '/admin/users', label: '用户管理', superOnly: true },
        { key: 'guestbook', index: '/admin/guestbook', label: '留言管理', superOnly: true },
        { key: 'content', index: '/admin/notices', label: '公告管理', superOnly: true },
      ]
  let items = raw.filter((m) => superAdmin || !m.superOnly)
  if (!superAdmin) {
    const allowed = clerkAllowedMenuKeys(staffPost)
    if (allowed) {
      items = items.filter(
        (m) => allowed.has(m.key) || m.key === 'messages' || m.key === 'dm',
      )
    }
  }
  if (!items.some((m) => m.key === 'messages')) {
    const dashAt = items.findIndex((m) => m.key === 'dashboard')
    items.splice(dashAt >= 0 ? dashAt + 1 : 0, 0, {
      key: 'messages',
      index: '/admin/messages',
      label: '消息',
      superOnly: false,
    })
  }
  return items
})

function logout() {
  localStorage.clear()
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
</style>
