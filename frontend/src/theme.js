/** 工厂 Ops 日/夜 + 主题色（仅工厂端，不进学生交付壳） */

import { computed, ref } from 'vue'
import { darkTheme } from 'naive-ui'

const STORAGE_KEY = 'gf-ops-theme'
const ACCENT_KEY = 'gf-ops-accent'

/**
 * 主色板：偏 Naive / Element 系可用主色，避开默认紫渐变与奶油陶土套路。
 * light/dark 各给 primary / deep / soft / tint / pressed。
 */
export const ACCENT_PRESETS = [
  {
    id: 'harbor',
    label: '港湾',
    light: {
      primary: '#0f766e',
      deep: '#115e59',
      soft: '#ccfbf1',
      tint: 'rgba(15, 118, 110, 0.05)',
      pressed: '#134e4a',
      dropHover: '#f0fdfa',
    },
    dark: {
      primary: '#2dd4bf',
      deep: '#5eead4',
      soft: '#115e59',
      tint: 'rgba(45, 212, 191, 0.07)',
      pressed: '#14b8a6',
      dropHover: '#102624',
    },
  },
  {
    id: 'tide',
    label: '潮汐',
    light: {
      primary: '#1d4ed8',
      deep: '#1e40af',
      soft: '#dbeafe',
      tint: 'rgba(29, 78, 216, 0.05)',
      pressed: '#1e3a8a',
      dropHover: '#eff6ff',
    },
    dark: {
      primary: '#60a5fa',
      deep: '#93c5fd',
      soft: '#1e3a8a',
      tint: 'rgba(96, 165, 250, 0.08)',
      pressed: '#3b82f6',
      dropHover: '#0f1f36',
    },
  },
  {
    id: 'berry',
    label: '莓果',
    light: {
      primary: '#be123c',
      deep: '#9f1239',
      soft: '#ffe4e6',
      tint: 'rgba(190, 18, 60, 0.05)',
      pressed: '#881337',
      dropHover: '#fff1f2',
    },
    dark: {
      primary: '#fb7185',
      deep: '#fda4af',
      soft: '#881337',
      tint: 'rgba(251, 113, 133, 0.08)',
      pressed: '#f43f5e',
      dropHover: '#2a1218',
    },
  },
  {
    id: 'bamboo',
    label: '竹青',
    light: {
      primary: '#16a34a',
      deep: '#15803d',
      soft: '#bbf7d0',
      tint: 'rgba(22, 163, 74, 0.05)',
      pressed: '#166534',
      dropHover: '#f0fdf4',
    },
    dark: {
      primary: '#4ade80',
      deep: '#86efac',
      soft: '#14532d',
      tint: 'rgba(74, 222, 128, 0.08)',
      pressed: '#22c55e',
      dropHover: '#102418',
    },
  },
  {
    id: 'cinnabar',
    label: '朱砂',
    light: {
      primary: '#ea580c',
      deep: '#c2410c',
      soft: '#fed7aa',
      tint: 'rgba(234, 88, 12, 0.05)',
      pressed: '#9a3412',
      dropHover: '#fff7ed',
    },
    dark: {
      primary: '#fb923c',
      deep: '#fdba74',
      soft: '#9a3412',
      tint: 'rgba(251, 146, 60, 0.08)',
      pressed: '#f97316',
      dropHover: '#2a160c',
    },
  },
  {
    id: 'slate',
    label: '岩灰',
    light: {
      primary: '#334155',
      deep: '#1e293b',
      soft: '#cbd5e1',
      tint: 'rgba(51, 65, 85, 0.05)',
      pressed: '#0f172a',
      dropHover: '#f1f5f9',
    },
    dark: {
      primary: '#cbd5e1',
      deep: '#e2e8f0',
      soft: '#334155',
      tint: 'rgba(203, 213, 225, 0.07)',
      pressed: '#94a3b8',
      dropHover: '#141a22',
    },
  },
]

function readInitialMode() {
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

const ACCENT_ALIASES = { element: 'berry', sky: 'tide' }

function readInitialAccent() {
  try {
    const saved = localStorage.getItem(ACCENT_KEY)
    const mapped = ACCENT_ALIASES[saved] || saved
    if (mapped && ACCENT_PRESETS.some((p) => p.id === mapped)) return mapped
  } catch {
    /* ignore */
  }
  return 'harbor'
}

function hexToRgb(hex) {
  const h = String(hex || '').replace('#', '')
  const full = h.length === 3 ? h.split('').map((c) => c + c).join('') : h
  const n = parseInt(full, 16)
  if (Number.isNaN(n)) return { r: 11, g: 110, b: 117 }
  return { r: (n >> 16) & 255, g: (n >> 8) & 255, b: n & 255 }
}

function rgba(hex, alpha) {
  const { r, g, b } = hexToRgb(hex)
  return `rgba(${r}, ${g}, ${b}, ${alpha})`
}

export const themeMode = ref(readInitialMode())
export const accentId = ref(readInitialAccent())

export const isDark = computed(() => themeMode.value === 'dark')

export const naiveTheme = computed(() => (isDark.value ? darkTheme : null))

export const activeAccent = computed(() => {
  return ACCENT_PRESETS.find((p) => p.id === accentId.value) || ACCENT_PRESETS[0]
})

export function accentColors(mode = themeMode.value, id = accentId.value) {
  const preset = ACCENT_PRESETS.find((p) => p.id === id) || ACCENT_PRESETS[0]
  return mode === 'dark' ? preset.dark : preset.light
}

function paintAccentVars() {
  if (typeof document === 'undefined') return
  const c = accentColors()
  const root = document.documentElement
  root.setAttribute('data-accent', accentId.value)
  root.style.setProperty('--teal', c.primary)
  root.style.setProperty('--teal-deep', c.deep)
  root.style.setProperty('--teal-soft', c.soft)
  root.style.setProperty('--accent', c.primary)
  root.style.setProperty('--main-tint', c.tint)
  root.style.setProperty('--dropzone-hover', c.dropHover)
}

/** Naive 主色与卡片底对齐 Ops CSS 变量，避免日夜切换后仍是默认绿/白块 */
export const naiveThemeOverrides = computed(() => {
  const dark = isDark.value
  const c = accentColors()
  return {
    common: {
      fontFamily:
        '"IBM Plex Sans", "Noto Sans SC", "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif',
      fontFamilyMono: '"IBM Plex Mono", "Noto Sans SC", ui-monospace, monospace',
      primaryColor: c.primary,
      primaryColorHover: c.deep,
      primaryColorPressed: c.pressed,
      primaryColorSuppl: c.primary,
      infoColor: c.primary,
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
      tabTextColorActiveLine: c.deep,
      barColor: c.primary,
    },
    // radio-button：未选中禁止主色描边/主色字，否则像「双选中」（库表论文稿、测例字段数、E-R 等）
    Radio: {
      buttonBorderColor: dark ? '#2a3a48' : '#d5dde3',
      buttonBorderColorHover: dark ? '#2a3a48' : '#d5dde3',
      buttonBorderColorActive: c.primary,
      buttonColor: dark ? '#151e27' : '#ffffff',
      buttonColorActive: rgba(c.primary, dark ? 0.18 : 0.12),
      buttonTextColor: dark ? '#e8eef2' : '#15202b',
      buttonTextColorHover: dark ? '#e8eef2' : '#15202b',
      buttonTextColorActive: c.deep,
      buttonBoxShadow: 'inset 0 0 0 1px transparent',
      buttonBoxShadowHover: 'inset 0 0 0 1px transparent',
      buttonBoxShadowFocus: 'inset 0 0 0 1px transparent',
    },
    Collapse: {
      titleTextColor: dark ? '#e8eef2' : '#15202b',
      arrowColor: dark ? '#8a9ba8' : '#6b7c8a',
    },
    Input: {
      color: dark ? '#1a2430' : '#ffffff',
      colorFocus: dark ? '#1a2430' : '#ffffff',
      border: dark ? '1px solid #2a3a48' : '1px solid #d5dde3',
      borderHover: `1px solid ${c.primary}`,
      borderFocus: `1px solid ${c.primary}`,
      placeholderColor: dark ? '#8a9ba8' : '#6b7c8a',
      textColor: dark ? '#e8eef2' : '#15202b',
    },
    InternalSelection: {
      color: dark ? '#1a2430' : '#ffffff',
      border: dark ? '1px solid #2a3a48' : '1px solid #d5dde3',
      borderHover: `1px solid ${c.primary}`,
      borderActive: `1px solid ${c.primary}`,
      borderFocus: `1px solid ${c.primary}`,
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
  paintAccentVars()
}

export function applyAccent(id) {
  const next = ACCENT_PRESETS.some((p) => p.id === id) ? id : 'harbor'
  accentId.value = next
  try {
    localStorage.setItem(ACCENT_KEY, next)
  } catch {
    /* ignore */
  }
  paintAccentVars()
}

export function toggleTheme() {
  applyTheme(isDark.value ? 'light' : 'dark')
}

/** 启动时立刻落到 <html>，避免闪白 */
export function initTheme() {
  applyTheme(themeMode.value)
  applyAccent(accentId.value)
}
