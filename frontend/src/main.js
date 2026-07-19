import { createApp } from 'vue'
import naive from 'naive-ui'
import App from './App.vue'
import router from './router'
import './styles.css'

const app = createApp(App)
app.use(router).use(naive)

app.config.errorHandler = (err, _instance, info) => {
  console.error('[毕设港]', err, info)
  const path = router.currentRoute.value.fullPath
  if (router.currentRoute.value.name === 'error-500') return
  router.replace({
    name: 'error-500',
    query: {
      from: path,
      detail: (err && (err.message || String(err))) || info || '未知错误',
    },
  })
}

app.mount('#app')
