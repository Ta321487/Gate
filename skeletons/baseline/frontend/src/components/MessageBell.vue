<template>
  <el-popover placement="bottom-end" :width="340" trigger="click" @show="loadList">
    <template #reference>
      <el-badge :value="unread || undefined" :hidden="!unread" :max="99" class="bell-badge">
        <el-button link class="bell-btn" title="消息" aria-label="消息">
          <span class="bell-ico" aria-hidden="true">✉</span>
        </el-button>
      </el-badge>
    </template>
    <div class="panel">
      <div class="hd">
        <strong>站内消息</strong>
        <div class="hd-actions">
          <el-button v-if="unread" link type="primary" size="small" @click="readAll">全部已读</el-button>
          <el-button link type="primary" size="small" @click="goInbox">查看全部</el-button>
        </div>
      </div>
      <div v-if="loading" class="empty">加载中…</div>
      <div v-else-if="!list.length" class="empty">暂无消息</div>
      <ul v-else class="list">
        <li
          v-for="m in list"
          :key="m.id"
          :class="{ unread: !m.read }"
          @click="openMsg(m)"
        >
          <div class="t">{{ m.title }}</div>
          <div class="b">{{ m.body }}</div>
          <div class="tm">{{ m.createdAt }}</div>
        </li>
      </ul>
    </div>
  </el-popover>
</template>

<script setup>
import { onMounted, onUnmounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import http from '../api/http'
import { messageAdminTarget, messageInboxPath } from '../utils/messages.js'

const route = useRoute()
const router = useRouter()
const loading = ref(false)
const list = ref([])
const unread = ref(0)
let timer = null

async function refreshCount() {
  try {
    const res = await http.get('/api/messages/unread-count')
    unread.value = Number(res.data?.count || 0)
  } catch {
    unread.value = 0
  }
}

async function loadList() {
  loading.value = true
  try {
    const res = await http.get('/api/messages', { params: { page: 1, size: 20 } })
    list.value = res.data?.list || []
    unread.value = Number(res.data?.unread ?? unread.value)
  } catch {
    list.value = []
  } finally {
    loading.value = false
  }
}

async function openMsg(m) {
  if (!m.read) {
    try {
      await http.post(`/api/messages/${m.id}/read`)
      m.read = true
      unread.value = Math.max(0, unread.value - 1)
    } catch {
      /* ignore */
    }
  }
  const go = messageAdminTarget(m, route.path, { fallback: true })
  if (go) {
    document.body.click()
    router.push(go)
    return
  }
  if (m.body) ElMessage.info(m.body)
}

async function readAll() {
  await http.post('/api/messages/read-all')
  unread.value = 0
  list.value = list.value.map((x) => ({ ...x, read: true }))
  ElMessage.success('已全部标为已读')
}

function goInbox() {
  document.body.click()
  router.push(messageInboxPath(route.path))
}

onMounted(() => {
  refreshCount()
  timer = setInterval(refreshCount, 60000)
})

onUnmounted(() => {
  if (timer) clearInterval(timer)
})
</script>

<style scoped>
.bell-badge { margin-right: 2px; }
.bell-btn { font-size: 13px; padding: 0 4px; }
.bell-ico { font-size: 15px; line-height: 1; }
.panel { margin: -4px 0; }
.hd {
  display: flex; justify-content: space-between; align-items: center;
  margin-bottom: 8px; font-size: 13px; gap: 8px;
}
.hd-actions { display: flex; align-items: center; gap: 2px; flex-shrink: 0; }
.empty { color: #94a3b8; font-size: 13px; padding: 16px 0; text-align: center; }
.list { list-style: none; margin: 0; padding: 0; max-height: 320px; overflow: auto; }
.list li {
  padding: 10px 8px;
  border-top: var(--portal-border-width, 1px) solid var(--portal-line, #f1f5f9);
  cursor: pointer;
  border-radius: var(--portal-radius-sm, 6px);
}
.list li:hover { background: #f8fafc; }
.list li.unread { background: #f0fdfa; }
.t { font-size: 13px; font-weight: 600; color: #0f172a; }
.b {
  margin-top: 4px; font-size: 12px; color: #64748b;
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;
}
.tm { margin-top: 4px; font-size: 11px; color: #94a3b8; }
</style>
