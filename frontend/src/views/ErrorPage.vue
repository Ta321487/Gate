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
      <n-button quaternary @click="$router.back()">上一页</n-button>
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

const detail = computed(() => props.detail || route.query.detail || '')

const showRetry = computed(() => props.retryable || code.value === 500)

const pillClass = computed(() => (code.value === 500 ? 'pill-red' : 'pill-amber'))
const pillText = computed(() => (code.value === 500 ? 'SERVER' : 'NOT FOUND'))

function onRetry() {
  if (props.retryable) {
    emit('retry')
    return
  }
  const from = route.query.from
  if (typeof from === 'string' && from.startsWith('/')) {
    router.replace(from)
    return
  }
  router.go(0)
}
</script>
