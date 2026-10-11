<template>
  <div>
    <section class="hero">
      <div class="hero-row">
        <div>
          <h1>{{ pageTitle }}</h1>
          <p>{{ pageLead }}</p>
          <p v-if="mutualBlindPhaseOn" class="muted">{{ mutualBlindPhaseHint }}</p>
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
            编号 {{ row.id }} · 申请人
            {{
              row.blindMasked
                ? (labels.mutualBlindMaskedName || mutualBlindPhaseLabel || '盲选申请人')
                : (row.displayUsername || row.username)
            }}
            · {{ row.applyAt }}
          </p>
          <el-tag v-if="row.blindMasked" size="small" type="info" effect="plain">{{ mutualBlindPhaseLabel }}</el-tag>
          <div v-if="row.remark && !row.blindMasked" class="tip">说明：{{ row.remark }}</div>
          <div class="row">
            <el-tag size="small" type="warning" effect="plain">{{ statusText(row.status) }}</el-tag>
            <el-button type="success" size="small" @click="respond(row, true)">确认</el-button>
            <el-button type="danger" size="small" plain @click="respond(row, false)">婉拒</el-button>
          </div>
        </div>
      </article>
      <el-empty v-if="!list.length" :description="emptyText" />
    </div>

    <section v-if="teamExitNeedOwnerOn" class="exit-box">
      <h2>{{ teamExitPendingLabel }}</h2>
      <p class="muted">{{ teamExitRequestHint }}</p>
      <div class="list">
        <article v-for="row in exitList" :key="'ex-' + row.id" class="card">
          <div class="mark">退</div>
          <div class="meta">
            <h3>{{ row.title || ('编号 ' + row.id) }}</h3>
            <p class="sub">编号 {{ row.id }} · {{ row.displayUsername || row.username }}</p>
            <div class="row">
              <el-button type="success" size="small" @click="exitRespond(row, true)">{{ teamExitApproveLabel }}</el-button>
              <el-button type="danger" size="small" plain @click="exitRespond(row, false)">{{ teamExitRejectLabel }}</el-button>
            </div>
          </div>
        </article>
        <el-empty v-if="!exitList.length" description="暂无退出申请" />
      </div>
    </section>

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
const peerConfirmMode = computed(() => !!ticket.requirePeerConfirm && !ticket.peerAccept)
const mutualBlindPhaseOn = computed(() => !!getSchema()?.interactThicken?.mutualBlindPhase)
const teamExitNeedOwnerOn = computed(
  () => !!getSchema()?.interactThicken?.mutualTeamExitNeedOwner,
)
const mutualBlindPhaseLabel = computed(() => labels.value.mutualBlindPhaseLabel || '盲选中')
const mutualBlindPhaseHint = computed(
  () =>
    labels.value.mutualBlindPhaseHint
    || '志愿截止前为盲选阶段，确认人暂不可见申请人详情；截止后自动揭晓。',
)
const teamExitPendingLabel = computed(
  () => labels.value.teamExitPendingLabel || '退出待确认',
)
const teamExitRequestHint = computed(
  () => labels.value.teamExitRequestHint || '退出须队长同意后生效。',
)
const teamExitApproveLabel = computed(
  () => labels.value.teamExitApproveLabel || '同意退出',
)
const teamExitRejectLabel = computed(
  () => labels.value.teamExitRejectLabel || '挽留/拒绝退出',
)
const pageTitle = computed(() => labels.value.peerInboxTitle || '待我确认')
const pageLead = computed(() =>
  peerConfirmMode.value
    ? (labels.value.peerInboxLead || '他人发起的调宿/互换意向，确认后宿管才可审核；也可婉拒。')
    : (labels.value.peerInboxLead || '他人向你发起的志愿，确认后即互选成功；也可婉拒。'),
)
const emptyText = computed(() => labels.value.peerInboxEmpty || '暂无待确认事项')

const list = ref([])
const exitList = ref([])
const total = ref(0)
const page = ref(1)
const size = ref(10)

function statusText(s) {
  return ticketStatusLabel(s, states.value[s] || s)
}

async function load() {
  const url = peerConfirmMode.value ? '/api/tickets/peer-confirm-inbox' : '/api/tickets/peer-inbox'
  const res = await http.get(url, { params: { page: page.value, size: size.value } })
  const data = res.data || res
  list.value = data.list || []
  total.value = data.total || 0
  if (teamExitNeedOwnerOn.value) {
    const ex = await http.get('/api/tickets/exit-inbox', { params: { page: 1, size: 20 } })
    const ed = ex.data || ex
    exitList.value = ed.list || []
  } else {
    exitList.value = []
  }
}

async function exitRespond(row, pass) {
  let remark = ''
  if (!pass) {
    const { value } = await ElMessageBox.prompt('可填写说明', teamExitRejectLabel.value, {
      confirmButtonText: '确认',
      cancelButtonText: '取消',
    })
    remark = value || ''
  } else {
    await ElMessageBox.confirm('确认同意该成员退出？', teamExitApproveLabel.value, {
      type: 'warning',
    })
  }
  await http.post(`/api/tickets/${row.id}/peer-exit-respond`, { pass, remark })
  ElMessage.success(pass ? '已同意退出' : '已拒绝退出')
  await load()
}

async function respond(row, pass) {
  let remark = ''
  const rejectTitle = labels.value.peerRejectDialogTitle || '婉拒'
  const confirmTitle = labels.value.peerConfirmDialogTitle || '确认'
  const confirmMsg = labels.value.peerConfirmDialogMessage || (peerConfirmMode.value ? '确认同意该调宿/互换意向？' : '确认接受该志愿？')
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
  const path = peerConfirmMode.value
    ? `/api/tickets/${row.id}/peer-confirm`
    : `/api/tickets/${row.id}/peer-respond`
  await http.post(path, { pass, remark })
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
.muted { color: var(--portal-muted, #64748b); font-size: 0.9rem; margin: 0.35rem 0 0; }
.exit-box { margin-top: 1.5rem; }
.exit-box h2 { margin: 0 0 0.35rem; font-size: 1.1rem; }
</style>
