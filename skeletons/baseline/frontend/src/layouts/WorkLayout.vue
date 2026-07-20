<template>
  <el-container class="layout">
    <el-aside width="200px" class="aside">
      <div class="brand">员工作业台</div>
      <el-menu :default-active="active" router background-color="#1a242e" text-color="#a8b8c4" active-text-color="#7dd3c7">
        <el-menu-item v-for="item in menuItems" :key="item.index" :index="item.index">{{ item.label }}</el-menu-item>
      </el-menu>
    </el-aside>
    <el-container>
      <el-header class="header">
        <span class="muted">{{ title }}</span>
        <div class="right">
          <span>{{ displayName }} · {{ postLabel }}</span>
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
import { APP_DELIVERED } from '../appDelivered.js'
import { staffLoginPath } from '../utils/authEntry.js'
import { getSchema, schemaLabels } from '../utils/domainSchema.js'
import {
  currentStaffPost,
  staffPostLabel,
  workerAllowedPages,
} from '../utils/staffPosts.js'

const route = useRoute()
const router = useRouter()
const labels = schemaLabels()
const title = labels.appName || APP_DELIVERED.title || import.meta.env.VITE_APP_TITLE || '毕设系统'
const username = localStorage.getItem('username') || ''
const nickname = localStorage.getItem('nickname') || ''
const displayName = computed(() => nickname || username)
const active = computed(() => route.path)
const postId = currentStaffPost()
const postLabel = computed(() => staffPostLabel(postId, '业务员工'))

const menuItems = computed(() => {
  const schema = getSchema()
  const orderLab = schema?.entities?.order?.label || '订单'
  const resvLab = schema?.entities?.reservation?.label || '预约'
  const meta = {
    tickets: { index: '/staff/tickets', label: '工单作业' },
    orders: { index: '/staff/orders', label: `${orderLab}作业` },
    slots: { index: '/staff/slots', label: `${resvLab}作业` },
  }
  const pages = workerAllowedPages(postId)
  const items = pages.map((p) => meta[p]).filter(Boolean)
  return items.length ? items : [{ index: '/staff/tickets', label: '作业台' }]
})

function logout() {
  localStorage.clear()
  router.push(staffLoginPath())
}
</script>

<style scoped>
.layout { min-height: 100vh; }
.aside { background: #1a242e; }
.brand {
  padding: 20px 16px; font-weight: 700; color: #fff; font-size: 15px;
  border-bottom: 1px solid #2a3844;
}
.aside :deep(.el-menu) { border-right: none; }
.header {
  display: flex; justify-content: space-between; align-items: center;
  background: #fff; border-bottom: 1px solid #ebeef5;
}
.right { display: flex; gap: 12px; align-items: center; font-size: 13px; color: #606266; }
.muted { color: #909399; font-size: 13px; }
.main { background: #f3f5f7; }
</style>
