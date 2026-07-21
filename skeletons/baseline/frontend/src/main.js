import { createApp } from 'vue'
import ElementPlus from 'element-plus'
import zhCn from 'element-plus/dist/locale/zh-cn.mjs'
import 'element-plus/dist/index.css'
import './styles/themes.css'
import './styles/chrome.css'
import App from './App.vue'
import router from './router'
import { APP_DELIVERED } from './appDelivered.js'

const theme = APP_DELIVERED.theme || import.meta.env.VITE_THEME || 'lib-ink'
const chrome = APP_DELIVERED.chrome || import.meta.env.VITE_CHROME || 'soft'
document.documentElement.setAttribute('data-theme', theme)
document.documentElement.setAttribute('data-chrome', chrome)
const appName = APP_DELIVERED?.schema?.labels?.appName || APP_DELIVERED.title
if (appName) document.title = appName

const app = createApp(App)
app.use(router)
app.use(ElementPlus, { locale: zhCn })
app.mount('#app')
