<template>
  <div>
    <section class="hero">
      <div class="hero-row">
        <div>
          <h1>站内消息</h1>
          <p>审核结果、催还提醒与系统通知。</p>
        </div>
        <el-button v-if="unread" type="primary" plain @click="readAll">全部已读</el-button>
      </div>
    </section>

    <div v-if="loading" class="empty">加载中…</div>
    <div v-else-if="!list.length" class="empty">暂无消息。</div>
    <ul v-else class="list">
      <li
        v-for="m in list"
        :key="m.id"
        :class="{ unread: !m.read }"
        @click="openMsg(m)"
      >
        <div class="t">{{ m.title }}</div>
        <div class="b">{{ m.body }}</div>
        <div class="tm">{{ m.createdAt || '—' }}</div>
      </li>
    </ul>

    <div v-if="total > size" class="pager">
      <el-pagination
        v-model:current-page="page"
        v-model:page-size="size"
        background
        layout="total, prev, pager, next"
        :total="total"
        @current-change="load"
      />
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import http from '../../api/http'

const loading = ref(false)
const list = ref([])
const total = ref(0)
const unread = ref(0)
const page = ref(1)
const size = ref(20)

async function load() {
  loading.value = true
  try {
    const res = await http.get('/api/messages', {
      params: { page: page.value, size: size.value },
    })
    list.value = res.data?.list || []
    total.value = Number(res.data?.total || list.value.length)
    unread.value = Number(res.data?.unread ?? 0)
  } catch {
    list.value = []
    total.value = 0
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
}

async function readAll() {
  await http.post('/api/messages/read-all')
  unread.value = 0
  list.value = list.value.map((x) => ({ ...x, read: true }))
  ElMessage.success('已全部标为已读')
}

onMounted(load)
</script>

<style scoped>
.hero { margin-bottom: 18px; }
.hero-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}
.hero h1 {
  margin: 0 0 6px;
  font-size: 1.45rem;
  font-weight: 700;
}
.hero p {
  margin: 0;
  font-size: 14px;
  color: var(--portal-muted, #5b6b76);
}
.list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.list li {
  border: 1px solid var(--portal-line, #d5dde3);
  border-radius: 10px;
  padding: 12px 14px;
  background: #fff;
  cursor: pointer;
}
.list li.unread {
  border-color: color-mix(in srgb, var(--portal-accent, #0b6e75) 35%, var(--portal-line, #d5dde3));
  background: color-mix(in srgb, var(--portal-accent, #0b6e75) 6%, #fff);
}
.t { font-weight: 650; font-size: 14px; margin-bottom: 4px; }
.b {
  font-size: 13px;
  color: var(--portal-muted, #5b6b76);
  line-height: 1.45;
  white-space: pre-wrap;
}
.tm { margin-top: 6px; font-size: 12px; color: #8a97a3; }
.empty {
  padding: 28px;
  text-align: center;
  color: var(--portal-muted, #5b6b76);
  font-size: 14px;
}
.pager { margin-top: 16px; display: flex; justify-content: flex-end; }
</style>
