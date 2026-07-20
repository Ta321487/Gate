import { createApp } from 'vue'
import ElementPlus from 'element-plus'
import zhCn from 'element-plus/dist/locale/zh-cn.mjs'
import 'element-plus/dist/index.css'
import './styles/themes.css'
import App from './App.vue'
import router from './router'
import { APP_DELIVERED } from './appDelivered.js'

const theme = APP_DELIVERED.theme || import.meta.env.VITE_THEME || 'lib-ink'
document.documentElement.setAttribute('data-theme', theme)
const appName = APP_DELIVERED?.schema?.labels?.appName || APP_DELIVERED.title
if (appName) document.title = appName

const app = createApp(App)
app.use(router)
app.use(ElementPlus, { locale: zhCn })
app.mount('#app')
