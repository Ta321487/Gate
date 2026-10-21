<template>
  <n-config-provider
    :locale="zhCN"
    :date-locale="dateZhCN"
    :theme="naiveTheme"
    :theme-overrides="naiveThemeOverrides"
  >
    <div class="app-shell" :class="{ 'nav-open': navOpen }">
      <div
        class="nav-backdrop"
        :hidden="!navOpen"
        @click="closeNav"
      />
      <aside class="sidebar" id="ops-sidebar">
        <div class="brand">
          <div class="brand-mark">毕设港</div>
          <div class="brand-sub">Gate · 运营台</div>
        </div>
        <nav class="nav">
          <div class="nav-label">工作台</div>
          <div
            v-for="item in workNav"
            :key="item.to"
            class="nav-item"
            :class="{ active: isActive(item) }"
            @click="go(item.to)"
          >
            <span class="dot" />
            <span class="nav-item-text">
              <span class="nav-item-label">{{ item.label }}</span>
              <span v-if="item.desc" class="nav-item-desc">{{ item.desc }}</span>
            </span>
          </div>
          <div class="nav-label">系统</div>
          <div
            v-for="item in sysNav"
            :key="item.to"
            class="nav-item"
            :class="{ active: isActive(item) }"
            @click="go(item.to)"
          >
            <span class="dot" />
            <span class="nav-item-text">
              <span class="nav-item-label">{{ item.label }}</span>
              <span v-if="item.desc" class="nav-item-desc">{{ item.desc }}</span>
            </span>
          </div>
        </nav>
        <div class="sidebar-foot">毕设港 · 运营台</div>
      </aside>
      <div class="main">
        <header class="topbar">
          <div class="topbar-left">
            <button
              type="button"
              class="nav-toggle"
              :aria-label="navOpen ? '关闭菜单' : '打开菜单'"
              :aria-expanded="navOpen ? 'true' : 'false'"
              aria-controls="ops-sidebar"
              @click="toggleNav"
            >
              <span class="nav-toggle-bar" />
              <span class="nav-toggle-bar" />
              <span class="nav-toggle-bar" />
            </button>
            <nav class="crumb" aria-label="面包屑">
              <template v-for="(c, i) in crumbs" :key="i">
                <span v-if="i" class="crumb-sep"> / </span>
                <strong v-if="i === crumbs.length - 1">{{ c.label }}</strong>
                <router-link v-else-if="c.to" class="crumb-link" :to="c.to">{{ c.label }}</router-link>
                <span v-else>{{ c.label }}</span>
              </template>
            </nav>
          </div>
          <button
            type="button"
            class="theme-toggle"
            :title="isDark ? '切换日间模式' : '切换夜间模式'"
            @click="toggleTheme"
          >
            {{ isDark ? '日间' : '夜间' }}
          </button>
        </header>
        <div class="content">
          <router-view />
        </div>
      </div>
    </div>
  </n-config-provider>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { zhCN, dateZhCN } from 'naive-ui'
import { detailCrumb } from './opsShared'
import { isDark, naiveTheme, naiveThemeOverrides, toggleTheme } from './theme'

const route = useRoute()
const router = useRouter()
const navOpen = ref(false)

const workNav = [
  { to: '/', label: '开工台', desc: '今日待办总览', match: ['ops-home'] },
  { to: '/projects', label: '项目', desc: '建项与履约管理', match: ['projects', 'project'] },
  { to: '/jobs', label: '任务队列', desc: '任务进度与重试', match: ['jobs'] },
  { to: '/fail-analysis', label: '失败分析', desc: '失败类型与排修', match: ['fail-analysis'] },
  { to: '/help', label: '帮助文档', desc: '流程说明与索引', match: ['help'] },
]
const sysNav = [
  { to: '/llm', label: '大模型', desc: '填岛与用量', match: ['llm'] },
  { to: '/unsplash', label: 'Unsplash', desc: '图床配置', match: ['unsplash'] },
  { to: '/system', label: '运行环境', desc: '工具链与端口', match: ['system'] },
]

function isActive(item) {
  return item.match.includes(route.name)
}

function closeNav() {
  navOpen.value = false
}

function toggleNav() {
  navOpen.value = !navOpen.value
}

function go(to) {
  router.push(to)
  closeNav()
}

watch(navOpen, (open) => {
  document.body.classList.toggle('nav-lock', open)
})

function onKey(e) {
  if (e.key === 'Escape') closeNav()
}

function onResize() {
  if (window.matchMedia('(min-width: 901px)').matches) closeNav()
}

onMounted(() => {
  window.addEventListener('keydown', onKey)
  window.addEventListener('resize', onResize)
})

onUnmounted(() => {
  window.removeEventListener('keydown', onKey)
  window.removeEventListener('resize', onResize)
  document.body.classList.remove('nav-lock')
})

const crumbs = computed(() => {
  const root = { label: '毕设港', to: '/' }
  if (route.name === 'project') {
    return [root, { label: '项目', to: '/projects' }, { label: detailCrumb.value || '详情' }]
  }
  if (route.name === 'not-found' || route.name === 'error-500') {
    return [root, { label: route.meta.crumb || '异常' }]
  }
  return [root, { label: route.meta.crumb || '' }]
})
</script>
