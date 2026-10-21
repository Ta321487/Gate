import { createApp } from 'vue'
import ElementPlus, { ElDialog, ElDrawer, ElMessageBox } from 'element-plus'
import zhCn from 'element-plus/dist/locale/zh-cn.mjs'
import 'element-plus/dist/index.css'
import 'element-plus/theme-chalk/dark/css-vars.css'
import './styles/themes.css'
import './styles/chrome.css'
import './styles/layout.css'
import './styles/type.css'
import './styles/thesis-display.css'
import './styles/immersion.css'
import './styles/cardVoice.css'
import './styles/accountFace.css'
import './styles/print.css'
import App from './App.vue'
import router from './router'
import { APP_DELIVERED } from './appDelivered.js'
import { isDarkTheme } from './utils/themeScheme.js'

const theme = APP_DELIVERED.theme || import.meta.env.VITE_THEME || 'lib-ink'
const chrome = APP_DELIVERED.chrome || import.meta.env.VITE_CHROME || 'soft'
const layout = APP_DELIVERED.layout || import.meta.env.VITE_LAYOUT || 'topbar'
const typeface = APP_DELIVERED.typeface || import.meta.env.VITE_TYPEFACE || 'clean'
const scheme = isDarkTheme(theme) ? 'dark' : 'light'
document.documentElement.setAttribute('data-theme', theme)
document.documentElement.setAttribute('data-chrome', chrome)
document.documentElement.setAttribute('data-layout', layout)
document.documentElement.setAttribute('data-typeface', typeface)
document.documentElement.setAttribute('data-scheme', scheme)
document.documentElement.classList.toggle('dark', scheme === 'dark')
const cardVoice = APP_DELIVERED.cardVoice || import.meta.env.VITE_CARD_VOICE || 'catalog'
document.documentElement.setAttribute('data-card-voice', cardVoice)
/**
 * 行业配色 × 壳色叠用（浅色/夜间/影院等全部适用，不只夜间）：
 * - data-theme：底色、字色、线色（整站氛围）
 * - shellColors：只叠 brand/accent/cover/glow（软皮主色角色 + Element primary）
 * 禁止再用壳色的浅 bg/surface/ink 盖掉任一行业皮。
 */
const shellColors = APP_DELIVERED.shellColors || {}
const darkShell = scheme === 'dark'
const shellVarMap = {
  brand: '--portal-brand',
  accent: '--portal-accent',
  cover: '--portal-cover',
}
for (const [key, cssVar] of Object.entries(shellVarMap)) {
  const val = shellColors[key]
  if (val) document.documentElement.style.setProperty(cssVar, val)
}
if (shellColors.accent) {
  const brand = shellColors.brand || shellColors.accent
  const accent = shellColors.accent
  // 跟当前主题变量混，浅色皮/夜间皮/影院皮都能搭
  const bg = 'var(--portal-bg)'
  const surface = 'var(--portal-surface)'
  const ink = 'var(--portal-ink)'
  // 盖死 Element 默认蓝：主色 + 深浅阶，避免按钮/链接仍冒蓝
  document.documentElement.style.setProperty('--el-color-primary', accent)
  document.documentElement.style.setProperty(
    '--el-color-primary-light-3',
    `color-mix(in srgb, ${accent} 70%, ${surface})`,
  )
  document.documentElement.style.setProperty(
    '--el-color-primary-light-5',
    `color-mix(in srgb, ${accent} 50%, ${surface})`,
  )
  document.documentElement.style.setProperty(
    '--el-color-primary-light-7',
    `color-mix(in srgb, ${accent} 30%, ${surface})`,
  )
  document.documentElement.style.setProperty(
    '--el-color-primary-light-8',
    `color-mix(in srgb, ${accent} 20%, ${surface})`,
  )
  document.documentElement.style.setProperty(
    '--el-color-primary-light-9',
    `color-mix(in srgb, ${accent} 12%, ${surface})`,
  )
  document.documentElement.style.setProperty(
    '--el-color-primary-dark-2',
    `color-mix(in srgb, ${accent} 78%, #000)`,
  )
  document.documentElement.style.setProperty(
    '--portal-accent-soft',
    darkShell
      ? `color-mix(in srgb, ${accent} 28%, ${surface})`
      : `color-mix(in srgb, ${accent} 14%, ${bg})`,
  )
  document.documentElement.style.setProperty(
    '--portal-line',
    darkShell
      ? `color-mix(in srgb, ${accent} 22%, ${surface})`
      : `color-mix(in srgb, ${accent} 12%, ${bg})`,
  )
  document.documentElement.style.setProperty(
    '--portal-skel-base',
    darkShell
      ? `color-mix(in srgb, ${ink} 12%, ${surface})`
      : `color-mix(in srgb, ${ink} 7%, ${surface})`,
  )
  document.documentElement.style.setProperty(
    '--portal-skel-shine',
    `color-mix(in srgb, ${accent} 14%, ${surface})`,
  )
  if (!shellColors.cover) {
    document.documentElement.style.setProperty(
      '--portal-cover',
      `linear-gradient(160deg, ${accent}, ${brand})`,
    )
  }
  const glow = shellColors.glow || accent
  document.documentElement.style.setProperty(
    '--portal-bg-glow',
    `color-mix(in srgb, ${glow} ${darkShell ? 14 : 12}%, transparent)`,
  )
}
const appName = APP_DELIVERED?.schema?.labels?.appName || APP_DELIVERED.title
if (appName) document.title = appName

// 点遮罩不关闭：各域 Dialog / Drawer / MessageBox 统一，避免填表或确认时误关
ElDialog.props.closeOnClickModal.default = false
ElDrawer.props.closeOnClickModal.default = false
for (const method of ['confirm', 'prompt']) {
  const original = ElMessageBox[method]
  ElMessageBox[method] = (message, title, options, appContext) => {
    if (title !== null && typeof title === 'object') {
      return original(message, { closeOnClickModal: false, ...title }, options)
    }
    return original(message, title, { closeOnClickModal: false, ...(options || {}) }, appContext)
  }
}

const app = createApp(App)
app.use(router)
app.use(ElementPlus, { locale: zhCn })
app.mount('#app')
