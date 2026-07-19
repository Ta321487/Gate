<template>
  <el-container class="layout">
    <el-aside width="208px" class="aside">
      <div class="brand">管理后台</div>
      <el-menu :default-active="active" router background-color="#101820" text-color="#9aadb8" active-text-color="#5eead4">
        <el-menu-item index="/admin/dashboard">{{ m('dashboard', '工作台') }}</el-menu-item>
        <el-menu-item v-if="superAdmin" index="/admin/books">{{ m('archive', '图书管理') }}</el-menu-item>
        <el-menu-item v-if="superAdmin" index="/admin/categories">{{ m('category', '分类管理') }}</el-menu-item>
        <el-menu-item v-if="superAdmin" index="/admin/readers">{{ m('users', '读者管理') }}</el-menu-item>
        <el-menu-item index="/admin/borrows">{{ m('ticket_pending', '借阅审核') }}</el-menu-item>
        <el-menu-item index="/admin/borrow-records">{{ m('ticket_records', '借阅记录') }}</el-menu-item>
        <el-menu-item index="/admin/overdue">{{ m('deadline', '逾期罚款') }}</el-menu-item>
        <el-menu-item v-if="superAdmin" index="/admin/notices">{{ m('content', '公告管理') }}</el-menu-item>
        <el-menu-item v-if="profileEditable" index="/admin/profile">个人资料</el-menu-item>
      </el-menu>
    </el-aside>
    <el-container>
      <el-header class="header">
        <span class="muted">{{ title }}</span>
        <div class="right">
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
import { FACTORY_DELIVERED } from '../factoryDelivered.js'
import { getSchema, menuLabel, schemaLabels } from '../utils/domainSchema.js'

const route = useRoute()
const router = useRouter()
const labels = schemaLabels()
const title = labels.appName || FACTORY_DELIVERED.title || import.meta.env.VITE_APP_TITLE || '毕设系统'
const username = localStorage.getItem('username') || ''
const nickname = localStorage.getItem('nickname') || ''
const profileEditable = localStorage.getItem('profileEditable') !== 'false'
const superAdmin = localStorage.getItem('superAdmin') === 'true'
const displayName = computed(() => nickname || username)
const active = computed(() => route.path)
const adminRoleLabel = computed(() => {
  const roles = getSchema()?.roles || {}
  if (superAdmin) return roles.admin?.label || '总管理员'
  return roles.subadmin?.label || '经办员'
})

function m(key, fallback) {
  return menuLabel('admin', key, fallback)
}

function logout() {
  localStorage.clear()
  router.push('/login')
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
