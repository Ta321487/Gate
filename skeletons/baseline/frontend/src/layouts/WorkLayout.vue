<template>
  <el-container class="layout workbench">
    <el-aside width="200px" class="wb-aside">
      <div class="wb-brand">
        <span class="wb-brand-mark" aria-hidden="true" />
        <span>员工作业台</span>
      </div>
      <el-menu :default-active="active" router class="wb-menu">
        <el-menu-item v-for="item in menuItems" :key="item.index" :index="item.index">{{ item.label }}</el-menu-item>
      </el-menu>
    </el-aside>
    <el-container>
      <el-header class="wb-header">
        <span class="wb-header-title">{{ title }}</span>
        <div class="wb-header-right">
          <span>{{ displayName }} · {{ postLabel }}</span>
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
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { APP_DELIVERED } from '../appDelivered.js'
import { staffLoginPath } from '../utils/authEntry.js'
import { getSchema, reservationCopy, schemaLabels } from '../utils/domainSchema.js'
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
  const resvLab = reservationCopy().label || '预约'
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
</style>
