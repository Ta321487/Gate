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
          <template v-for="sec in navSections" :key="sec.label">
            <div class="nav-label">{{ sec.label }}</div>
            <div
              v-for="item in sec.items"
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
          </template>
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
          <div class="theme-controls">
            <div class="accent-swatches" role="radiogroup" aria-label="主题色">
              <button
                v-for="p in ACCENT_PRESETS"
                :key="p.id"
                type="button"
                class="accent-swatch"
                role="radio"
                :aria-checked="accentId === p.id ? 'true' : 'false'"
                :aria-label="p.label"
                :title="p.label"
                :class="{ active: accentId === p.id }"
                :style="{ '--swatch': accentSwatch(p) }"
                @click="applyAccent(p.id)"
              />
            </div>
            <button
              type="button"
              class="theme-toggle"
              :title="isDark ? '切换日间模式' : '切换夜间模式'"
              @click="toggleTheme"
            >
              {{ isDark ? '日间' : '夜间' }}
            </button>
          </div>
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
import {
  ACCENT_PRESETS,
  accentId,
  applyAccent,
  accentColors,
  isDark,
  naiveTheme,
  naiveThemeOverrides,
  toggleTheme,
} from './theme'

function accentSwatch(preset) {
  return accentColors(isDark.value ? 'dark' : 'light', preset.id).primary
}

const route = useRoute()
const router = useRouter()
const navOpen = ref(false)

const navSections = [
  {
    label: '工作台',
    items: [
      { to: '/', label: '开工台', desc: '今日待办总览', match: ['ops-home'] },
      { to: '/projects', label: '项目', desc: '建项与履约管理', match: ['projects', 'project'] },
      {
        to: '/thesis-absorb',
        label: '终稿吸收',
        desc: '从终稿抽出要点，对照能力补齐',
        match: ['thesis-absorb', 'thesis-absorb-detail'],
      },
      { to: '/jobs', label: '任务队列', desc: '任务进度与重试', match: ['jobs'] },
      { to: '/fail-analysis', label: '失败分析', desc: '失败类型与排修', match: ['fail-analysis'] },
      { to: '/help', label: '帮助文档', desc: '流程说明与索引', match: ['help'] },
    ],
  },
  {
    label: '运行与连接',
    items: [
      { to: '/llm', label: '大模型', desc: '连接与用量', match: ['llm'] },
      { to: '/unsplash', label: 'Unsplash', desc: '图床配置', match: ['unsplash'] },
      { to: '/system', label: '运行环境', desc: '工具链与端口', match: ['system'] },
    ],
  },
  {
    label: '资产台',
    items: [
      { to: '/zh-lexicon', label: '词表维护', desc: '列/表中文 COMMENT', match: ['zh-lexicon'] },
      { to: '/status-copy', label: '状态话术', desc: '状态码中文与空态', match: ['status-copy'] },
      { to: '/dict-values', label: '字典台', desc: '业务枚举与下拉选项', match: ['dict-values'] },
      { to: '/demo-scripts', label: '演示剧本', desc: '答辩步骤与所需数据', match: ['demo-scripts'] },
      { to: '/addon-suggest', label: '开关建议', desc: '开题扫词与开关证据', match: ['addon-suggest'] },
      { to: '/cap-cards', label: '能力说明', desc: 'README 说明与菜单入口', match: ['cap-cards'] },
      { to: '/error-copy', label: '错误码中文', desc: '业务错误默认中文', match: ['error-copy'] },
      { to: '/widget-hints', label: '控件语义', desc: '字段标签到控件映射', match: ['widget-hints'] },
      { to: '/menu-matrix', label: '菜单矩阵', desc: '岗位 × 菜单入口', match: ['menu-matrix'] },
      { to: '/rule-params', label: '规则参数', desc: '超时 / 提前量 / 倍率', match: ['rule-params'] },
      { to: '/er-edge-copy', label: '表关系叙事', desc: '表边一句人话', match: ['er-edge-copy'] },
      { to: '/demo-accounts', label: '测试账号', desc: '三端演示账号', match: ['demo-accounts'] },
      { to: '/diagram-titles', label: '论文图题', desc: '图种标题模板', match: ['diagram-titles'] },
    ],
  },
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
