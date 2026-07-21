<template>
  <el-container class="layout workbench">
    <el-aside width="208px" class="wb-aside">
      <div class="wb-brand">
        <span class="wb-brand-mark" aria-hidden="true" />
        <span>管理后台</span>
      </div>
      <el-menu :default-active="active" router class="wb-menu">
        <el-menu-item v-for="item in menuItems" :key="item.index" :index="item.index">{{ item.label }}</el-menu-item>
        <el-menu-item v-if="profileEditable" index="/admin/profile">个人资料</el-menu-item>
      </el-menu>
    </el-aside>
    <el-container>
      <el-header class="wb-header">
        <span class="wb-header-title">{{ title }}</span>
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
import MessageBell from '../components/MessageBell.vue'
import { APP_DELIVERED } from '../appDelivered.js'
import { getSchema, isSuperOnlyMenu, schemaLabels, schemaMenus } from '../utils/domainSchema.js'
import { adminLoginPath } from '../utils/authEntry.js'
import {
  clerkAllowedMenuKeys,
  currentStaffPost,
  staffPostLabel,
} from '../utils/staffPosts.js'
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

let offProfileDisplay
onMounted(() => {
  offProfileDisplay = onProfileDisplayChange(({ nickname: n }) => {
    nickname.value = n || ''
  })
})
onUnmounted(() => offProfileDisplay?.())

const adminRoleLabel = computed(() => {
  const roles = getSchema()?.roles || {}
  if (superAdmin) return roles.admin?.label || '总管理员'
  return staffPostLabel(staffPost, roles.subadmin?.label || '经办员')
})

const MENU_TO = {
  dashboard: '/admin/dashboard',
  messages: '/admin/messages',
  ticket_pending: '/admin/tickets',
  ticket_records: '/admin/ticket-records',
  users: '/admin/users',
  content: '/admin/notices',
  guestbook: '/admin/guestbook',
  lookup_site: '/admin/sites',
  lookup_type: '/admin/types',
  archive: '/admin/archive',
  category: '/admin/categories',
  deadline: '/admin/overdue',
  coupons: '/admin/coupons',
  orders: '/admin/orders',
  order_reviews: '/admin/order-reviews',
  reservations: '/admin/reservations',
}

const menuItems = computed(() => {
  const menus = schemaMenus('admin')
  const raw = menus.length
    ? menus.map((m) => ({
        key: m.key,
        index: MENU_TO[m.key],
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
    if (allowed) items = items.filter((m) => allowed.has(m.key) || m.key === 'messages')
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
</style>
