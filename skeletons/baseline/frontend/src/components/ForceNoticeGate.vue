<template>
  <el-dialog
    v-model="open"
    :title="current?.title || labels.noticeForceAckLabel || '须阅读公告'"
    width="560px"
    :close-on-click-modal="false"
    :close-on-press-escape="false"
    :show-close="false"
    append-to-body
  >
    <p class="hint">{{ labels.noticeForceAckHint || '登录后须确认阅读才能关闭' }}</p>
    <div v-if="isHtml" class="body html" v-html="safeHtml" />
    <div v-else class="body text">{{ current?.content || '（无正文）' }}</div>
    <template #footer>
      <el-button type="primary" :loading="acking" @click="ack">
        {{ labels.noticeForceAckConfirm || '我已阅读' }}
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup>
/** 强制公告弹窗，未确认不可关 */
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import http from '../api/http'
import { schemaLabels } from '../utils/domainSchema.js'
import { isLoggedIn } from '../utils/session.js'

const labels = schemaLabels()
const route = useRoute()
const queue = ref([])
const open = ref(false)
const acking = ref(false)

const current = computed(() => queue.value[0] || null)
const isHtml = computed(() => String(current.value?.contentFmt || '') === 'html')
const safeHtml = computed(() => stripScripts(String(current.value?.content || '')))

function stripScripts(html) {
  return html
    .replace(/<script[\s\S]*?>[\s\S]*?<\/script>/gi, '')
    .replace(/\son\w+\s*=\s*(['"]).*?\1/gi, '')
    .replace(/\son\w+\s*=\s*[^\s>]+/gi, '')
}

async function load() {
  if (!isLoggedIn()) {
    queue.value = []
    open.value = false
    return
  }
  try {
    const res = await http.get('/api/notices/force-pending')
    queue.value = Array.isArray(res.data) ? res.data : []
    open.value = queue.value.length > 0
  } catch {
    queue.value = []
    open.value = false
  }
}

async function ack() {
  const n = current.value
  if (!n?.id) return
  acking.value = true
  try {
    await http.post(`/api/notices/${n.id}/ack`)
    queue.value = queue.value.slice(1)
    open.value = queue.value.length > 0
  } finally {
    acking.value = false
  }
}

watch(() => route.fullPath, () => {
  if (isLoggedIn()) load()
})

onMounted(load)

defineExpose({ reload: load })
</script>

<style scoped>
.hint {
  margin: 0 0 12px;
  font-size: 13px;
  color: var(--portal-muted, #6b7c8a);
}
.body {
  line-height: 1.7;
  font-size: 15px;
  color: var(--portal-ink, #15202b);
  max-height: 50vh;
  overflow: auto;
}
.body.text { white-space: pre-wrap; }
.body.html :deep(a) { color: var(--portal-accent, #0b6e75); }
</style>
