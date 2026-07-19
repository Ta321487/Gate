<template>
  <el-popover placement="bottom-end" :width="340" trigger="click" @show="loadList">
    <template #reference>
      <el-badge :value="unread || undefined" :hidden="!unread" :max="99" class="bell-badge">
        <el-button link class="bell-btn">消息</el-button>
      </el-badge>
    </template>
    <div class="panel">
      <div class="hd">
        <strong>站内消息</strong>
        <el-button v-if="unread" link type="primary" size="small" @click="readAll">全部已读</el-button>
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
import { ElMessage } from 'element-plus'
import http from '../api/http'

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
  if (m.body) ElMessage.info(m.body)
}

async function readAll() {
  await http.post('/api/messages/read-all')
  unread.value = 0
  list.value = list.value.map((x) => ({ ...x, read: true }))
  ElMessage.success('已全部标为已读')
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
.bell-btn { font-size: 13px; }
.panel { margin: -4px 0; }
.hd {
  display: flex; justify-content: space-between; align-items: center;
  margin-bottom: 8px; font-size: 13px;
}
.empty { color: #94a3b8; font-size: 13px; padding: 16px 0; text-align: center; }
.list { list-style: none; margin: 0; padding: 0; max-height: 320px; overflow: auto; }
.list li {
  padding: 10px 8px; border-top: 1px solid #f1f5f9; cursor: pointer; border-radius: 6px;
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
