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
            <span class="dot" /><span>{{ item.label }}</span>
          </div>
          <div class="nav-label">系统</div>
          <div
            v-for="item in sysNav"
            :key="item.to"
            class="nav-item"
            :class="{ active: isActive(item) }"
            @click="go(item.to)"
          >
            <span class="dot" /><span>{{ item.label }}</span>
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
            <div class="crumb">
              <template v-for="(c, i) in crumbs" :key="i">
                <span v-if="i"> / </span>
                <strong v-if="i === crumbs.length - 1">{{ c }}</strong>
                <span v-else>{{ c }}</span>
              </template>
            </div>
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
  { to: '/', label: '项目', match: ['projects', 'project'] },
  { to: '/jobs', label: '任务队列', match: ['jobs'] },
  { to: '/help', label: '帮助文档', match: ['help'] },
]
const sysNav = [
  { to: '/llm', label: '大模型', match: ['llm'] },
  { to: '/unsplash', label: 'Unsplash', match: ['unsplash'] },
  { to: '/system', label: '运行环境', match: ['system'] },
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
  const base = ['毕设港']
  if (route.name === 'project') return [...base, '项目', detailCrumb.value || '详情']
  if (route.name === 'not-found' || route.name === 'error-500') {
    return [...base, route.meta.crumb || '异常']
  }
  return [...base, route.meta.crumb || '']
})
</script>
