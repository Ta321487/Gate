/** 工厂 Ops 日/夜主题（仅工厂端，不进学生交付壳） */

import { computed, ref } from 'vue'
import { darkTheme } from 'naive-ui'

const STORAGE_KEY = 'gf-ops-theme'

function readInitial() {
  try {
    const saved = localStorage.getItem(STORAGE_KEY)
    if (saved === 'dark' || saved === 'light') return saved
  } catch {
    /* ignore */
  }
  if (typeof window !== 'undefined' && window.matchMedia?.('(prefers-color-scheme: dark)').matches) {
    return 'dark'
  }
  return 'light'
}

export const themeMode = ref(readInitial())

export const isDark = computed(() => themeMode.value === 'dark')

export const naiveTheme = computed(() => (isDark.value ? darkTheme : null))

/** Naive 主色与卡片底对齐 Ops CSS 变量，避免日夜切换后仍是默认绿/白块 */
export const naiveThemeOverrides = computed(() => {
  const dark = isDark.value
  return {
    common: {
      fontFamily:
        '"IBM Plex Sans", "Noto Sans SC", "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif',
      fontFamilyMono: '"IBM Plex Mono", "Noto Sans SC", ui-monospace, monospace',
      primaryColor: dark ? '#2dd4bf' : '#0b6e75',
      primaryColorHover: dark ? '#5eead4' : '#08545a',
      primaryColorPressed: dark ? '#14b8a6' : '#064448',
      primaryColorSuppl: dark ? '#2dd4bf' : '#0b6e75',
      infoColor: dark ? '#2dd4bf' : '#0b6e75',
      successColor: dark ? '#34d399' : '#047857',
      warningColor: dark ? '#fbbf24' : '#b45309',
      errorColor: dark ? '#f87171' : '#b91c1c',
      borderRadius: '6px',
    },
    Card: {
      color: dark ? '#151e27' : '#ffffff',
      colorModal: dark ? '#151e27' : '#ffffff',
      borderColor: dark ? '#2a3a48' : '#d5dde3',
    },
    DataTable: {
      thColor: dark ? '#1a2430' : '#f4f7f9',
      tdColor: dark ? '#151e27' : '#ffffff',
      borderColor: dark ? '#2a3a48' : '#d5dde3',
      thTextColor: dark ? '#8a9ba8' : '#6b7c8a',
      tdTextColor: dark ? '#e8eef2' : '#15202b',
    },
    Tabs: {
      tabTextColorLine: dark ? '#8a9ba8' : '#6b7c8a',
      tabTextColorActiveLine: dark ? '#5eead4' : '#08545a',
      barColor: dark ? '#2dd4bf' : '#0b6e75',
    },
    Collapse: {
      titleTextColor: dark ? '#e8eef2' : '#15202b',
      arrowColor: dark ? '#8a9ba8' : '#6b7c8a',
    },
    Input: {
      color: dark ? '#1a2430' : '#ffffff',
      colorFocus: dark ? '#1a2430' : '#ffffff',
      border: dark ? '1px solid #2a3a48' : '1px solid #d5dde3',
      borderHover: dark ? '1px solid #2dd4bf' : '1px solid #0b6e75',
      borderFocus: dark ? '1px solid #2dd4bf' : '1px solid #0b6e75',
      placeholderColor: dark ? '#8a9ba8' : '#6b7c8a',
      textColor: dark ? '#e8eef2' : '#15202b',
    },
    InternalSelection: {
      color: dark ? '#1a2430' : '#ffffff',
      border: dark ? '1px solid #2a3a48' : '1px solid #d5dde3',
      borderHover: dark ? '1px solid #2dd4bf' : '1px solid #0b6e75',
      borderActive: dark ? '1px solid #2dd4bf' : '1px solid #0b6e75',
      borderFocus: dark ? '1px solid #2dd4bf' : '1px solid #0b6e75',
      placeholderColor: dark ? '#8a9ba8' : '#6b7c8a',
      textColor: dark ? '#e8eef2' : '#15202b',
    },
  }
})

export function applyTheme(mode) {
  const next = mode === 'dark' ? 'dark' : 'light'
  themeMode.value = next
  if (typeof document !== 'undefined') {
    document.documentElement.setAttribute('data-theme', next)
    document.documentElement.style.colorScheme = next
  }
  try {
    localStorage.setItem(STORAGE_KEY, next)
  } catch {
    /* ignore */
  }
}

export function toggleTheme() {
  applyTheme(isDark.value ? 'light' : 'dark')
}

/** 启动时立刻落到 <html>，避免闪白 */
export function initTheme() {
  applyTheme(themeMode.value)
}
