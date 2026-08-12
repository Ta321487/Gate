<template>
  <div>
    <section class="hero">
      <div class="hero-row">
        <div>
          <h1>{{ pageTitle }}</h1>
          <p>{{ pageLead }}</p>
        </div>
        <div class="tools">
          <el-button @click="load">刷新</el-button>
        </div>
      </div>
    </section>

    <div class="list">
      <article v-for="row in list" :key="row.id" class="card">
        <div class="mark">{{ (row.title || '?').slice(0, 1) }}</div>
        <div class="meta">
          <h3>{{ row.title || ('编号 ' + row.id) }}</h3>
          <p class="sub">
            编号 {{ row.id }} · 申请人 {{ row.displayUsername || row.username }} · {{ row.applyAt }}
          </p>
          <div v-if="row.remark" class="tip">说明：{{ row.remark }}</div>
          <div class="row">
            <el-tag size="small" type="warning" effect="plain">{{ statusText(row.status) }}</el-tag>
            <el-button type="success" size="small" @click="respond(row, true)">确认</el-button>
            <el-button type="danger" size="small" plain @click="respond(row, false)">婉拒</el-button>
          </div>
        </div>
      </article>
      <el-empty v-if="!list.length" :description="emptyText" />
    </div>

    <div v-if="total > size" class="pager">
      <el-pagination
        background
        layout="prev, pager, next"
        :total="total"
        :page-size="size"
        :current-page="page"
        @current-change="(p) => { page = p; load() }"
      />
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import http from '../../api/http'
import { getSchema, ticketStatusLabel } from '../../utils/domainSchema'

const schema = getSchema()
const ticket = schema.entities?.ticket || {}
const labels = computed(() => schema.labels || {})
const states = computed(() => ticket.states || {})
const pageTitle = computed(() => labels.value.peerInboxTitle || '待我确认')
const pageLead = computed(
  () => labels.value.peerInboxLead || '他人向你发起的志愿，确认后即互选成功；也可婉拒。',
)
const emptyText = computed(() => labels.value.peerInboxEmpty || '暂无待确认志愿')

const list = ref([])
const total = ref(0)
const page = ref(1)
const size = ref(10)

function statusText(s) {
  return ticketStatusLabel(s, states.value[s] || s)
}

async function load() {
  const res = await http.get('/api/tickets/peer-inbox', { params: { page: page.value, size: size.value } })
  const data = res.data || res
  list.value = data.list || []
  total.value = data.total || 0
}

async function respond(row, pass) {
  let remark = ''
  const rejectTitle = labels.value.peerRejectDialogTitle || '婉拒志愿'
  const confirmTitle = labels.value.peerConfirmDialogTitle || '确认互选'
  const confirmMsg = labels.value.peerConfirmDialogMessage || '确认接受该志愿？'
  if (!pass) {
    const { value } = await ElMessageBox.prompt('请填写婉拒原因', rejectTitle, {
      confirmButtonText: '确认婉拒',
      cancelButtonText: '取消',
      inputPattern: /\S+/,
      inputErrorMessage: '请填写原因',
    })
    remark = value
  } else {
    await ElMessageBox.confirm(confirmMsg, confirmTitle, { type: 'success' })
  }
  await http.post(`/api/tickets/${row.id}/peer-respond`, { pass, remark })
  ElMessage.success(pass ? '已确认' : '已婉拒')
  await load()
}

onMounted(load)
</script>

<style scoped>
.hero { margin-bottom: 1rem; }
.hero-row { display: flex; justify-content: space-between; gap: 1rem; align-items: flex-start; }
.list { display: flex; flex-direction: column; gap: 0.75rem; }
.card { display: flex; gap: 0.75rem; padding: 0.9rem 1rem; background: var(--portal-surface, #fff); border: 1px solid var(--portal-line, #e5e7eb); border-radius: 10px; }
.mark { width: 2.2rem; height: 2.2rem; border-radius: 8px; background: var(--portal-accent-soft, #eef2ff); color: var(--portal-accent, #334155); display: grid; place-items: center; font-weight: 700; }
.meta { flex: 1; min-width: 0; }
.meta h3 { margin: 0 0 0.25rem; font-size: 1.05rem; }
.sub { margin: 0; color: var(--portal-muted, #64748b); font-size: 0.9rem; }
.tip { margin: 0.4rem 0; color: var(--portal-ink, #0f172a); font-size: 0.92rem; }
.row { display: flex; flex-wrap: wrap; gap: 0.5rem; align-items: center; margin-top: 0.5rem; }
.pager { margin-top: 1rem; display: flex; justify-content: center; }
.tools { display: flex; gap: 0.5rem; }
</style>
