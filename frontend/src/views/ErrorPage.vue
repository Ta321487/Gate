<template>
  <div class="status-page">
    <div class="status-mark">
      <span class="status-code mono">{{ code }}</span>
      <span class="pill" :class="pillClass">{{ pillText }}</span>
    </div>
    <h1 class="page-title">{{ title }}</h1>
    <p class="page-desc">{{ description }}</p>
    <p v-if="detail" class="status-detail mono">{{ detail }}</p>
    <div class="row status-actions">
      <n-button type="primary" @click="$router.push('/')">返回项目</n-button>
      <n-button v-if="showRetry" @click="onRetry">重试</n-button>
      <n-button @click="onBack">上一页</n-button>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const props = defineProps({
  code: { type: [Number, String], default: '' },
  title: { type: String, default: '' },
  description: { type: String, default: '' },
  detail: { type: String, default: '' },
  /** 嵌入页用法：配合 @retry 重新拉数；全局 /error/500 不要靠这个 */
  retryable: { type: Boolean, default: false },
})

const emit = defineEmits(['retry'])
const route = useRoute()
const router = useRouter()

const resolvedCode = computed(() => {
  const c = props.code || route.meta.code || route.params.code || 404
  return Number(c) || 404
})

const code = resolvedCode

const title = computed(() => {
  if (props.title) return props.title
  if (route.meta.title) return route.meta.title
  return code.value === 500 ? '服务异常' : '页面不存在'
})

const description = computed(() => {
  if (props.description) return props.description
  if (route.meta.description) return route.meta.description
  if (code.value === 500) {
    return '请求处理失败，或上游服务暂时不可用。可稍后重试，或从侧栏回到工作台。'
  }
  return '当前地址未匹配到路由，链接可能已失效或项目 ID 有误。'
})

/** 优先 props；其次 history.state（干净 URL）；兼容旧 ?detail= */
const detail = computed(() => {
  if (props.detail) return props.detail
  const st = typeof history !== 'undefined' ? history.state : null
  if (st && typeof st.gfErrorDetail === 'string' && st.gfErrorDetail) return st.gfErrorDetail
  const q = route.query.detail
  return typeof q === 'string' ? q : ''
})

const showRetry = computed(() => props.retryable || code.value === 500 || code.value === 404)

const pillClass = computed(() => (code.value === 500 ? 'pill-red' : 'pill-amber'))
const pillText = computed(() => (code.value === 500 ? 'SERVER' : 'NOT FOUND'))

function safeFrom(raw) {
  if (typeof raw !== 'string' || !raw.startsWith('/') || raw.startsWith('//')) return ''
  if (raw.startsWith('/error')) return ''
  return raw
}

function resolveFrom() {
  const st = typeof history !== 'undefined' ? history.state : null
  return (
    safeFrom(st?.gfErrorFrom) ||
    safeFrom(typeof route.query.from === 'string' ? route.query.from : '')
  )
}

/** 真重试：嵌页 emit；全局错误页回到来源路由（或首页） */
function onRetry() {
  if (props.retryable) {
    emit('retry')
    return
  }
  const from = resolveFrom()
  if (from) {
    router.replace(from)
    return
  }
  if (code.value === 404) {
    router.replace('/')
    return
  }
  router.go(0)
}

function onBack() {
  if (window.history.length > 1) {
    router.back()
    return
  }
  router.replace('/')
}
</script>
