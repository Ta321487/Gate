<template>
  <el-container class="layout">
    <el-aside width="208px" class="aside">
      <div class="brand">管理后台</div>
      <el-menu :default-active="active" router background-color="#101820" text-color="#9aadb8" active-text-color="#5eead4">
        <el-menu-item v-for="item in menuItems" :key="item.index" :index="item.index">{{ item.label }}</el-menu-item>
        <el-menu-item v-if="profileEditable" index="/admin/profile">个人资料</el-menu-item>
      </el-menu>
    </el-aside>
    <el-container>
      <el-header class="header">
        <span class="muted">{{ title }}</span>
        <div class="right">
          <MessageBell />
          <span>{{ displayName }} · {{ adminRoleLabel }}</span>
          <el-button link type="primary" @click="logout">退出</el-button>
        </div>
      </el-header>
      <el-main class="main">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { computed } from 'vue'
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

const route = useRoute()
const router = useRouter()
const labels = schemaLabels()
const title = labels.appName || APP_DELIVERED.title || import.meta.env.VITE_APP_TITLE || '毕设系统'
const username = localStorage.getItem('username') || ''
const nickname = localStorage.getItem('nickname') || ''
const profileEditable = localStorage.getItem('profileEditable') !== 'false'
const superAdmin = localStorage.getItem('superAdmin') === 'true'
const staffPost = currentStaffPost()
const displayName = computed(() => nickname || username)
const active = computed(() => route.path)

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
  lookup_site: '/admin/sites',
  lookup_type: '/admin/types',
  archive: '/admin/archive',
  category: '/admin/categories',
  deadline: '/admin/overdue',
  orders: '/admin/orders',
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
.aside { background: #101820; }
.brand {
  padding: 20px 16px; font-weight: 700; color: #fff; font-size: 15px;
  border-bottom: 1px solid #243140;
}
.aside :deep(.el-menu) { border-right: none; }
.header {
  display: flex; justify-content: space-between; align-items: center;
  background: #fff; border-bottom: 1px solid #ebeef5;
}
.right { display: flex; gap: 12px; align-items: center; font-size: 13px; color: #606266; }
.muted { color: #909399; font-size: 13px; }
.main { background: #f5f7fa; }
</style>
