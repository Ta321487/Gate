<template>
  <n-config-provider :locale="zhCN" :date-locale="dateZhCN" :theme="naiveTheme">
    <div class="app-shell">
      <aside class="sidebar">
        <div class="brand">
          <div class="brand-mark">毕设港</div>
          <div class="brand-sub">Thesis Harbor · Ops</div>
        </div>
        <nav class="nav">
          <div class="nav-label">工作台</div>
          <div
            v-for="item in workNav"
            :key="item.to"
            class="nav-item"
            :class="{ active: isActive(item) }"
            @click="$router.push(item.to)"
          >
            <span class="dot" /><span>{{ item.label }}</span>
          </div>
          <div class="nav-label">系统</div>
          <div
            v-for="item in sysNav"
            :key="item.to"
            class="nav-item"
            :class="{ active: isActive(item) }"
            @click="$router.push(item.to)"
          >
            <span class="dot" /><span>{{ item.label }}</span>
          </div>
        </nav>
        <div class="sidebar-foot">毕设港 · Ops</div>
      </aside>
      <div class="main">
        <header class="topbar">
          <div class="crumb">
            <template v-for="(c, i) in crumbs" :key="i">
              <span v-if="i"> / </span>
              <strong v-if="i === crumbs.length - 1">{{ c }}</strong>
              <span v-else>{{ c }}</span>
            </template>
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
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { zhCN, dateZhCN } from 'naive-ui'
import { detailCrumb } from './opsShared'
import { isDark, naiveTheme, toggleTheme } from './theme'

const route = useRoute()
const workNav = [
  { to: '/', label: '项目', match: ['projects', 'project'] },
  { to: '/jobs', label: '任务队列', match: ['jobs'] },
]
const sysNav = [
  { to: '/deepseek', label: 'DeepSeek', match: ['deepseek'] },
  { to: '/system', label: '运行环境', match: ['system'] },
]

function isActive(item) {
  return item.match.includes(route.name)
}

const crumbs = computed(() => {
  const base = ['毕设港']
  if (route.name === 'project') return [...base, '项目', detailCrumb.value || '详情']
  if (route.name === 'not-found' || route.name === 'error-500') {
    return [...base, route.meta.crumb || '异常']
  }
  return [...base, route.meta.crumb || '']
})
</script>
