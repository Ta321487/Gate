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
