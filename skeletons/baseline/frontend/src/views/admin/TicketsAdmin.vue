<template>
  <div>
    <div class="toolbar">
      <el-alert type="info" :closable="false" show-icon :title="todoHint" />
    </div>
    <div class="toolbar">
      <el-button type="primary" @click="load">刷新待办</el-button>
    </div>
    <el-table :data="list" stripe>
      <el-table-column prop="id" label="编号" width="70" />
      <el-table-column prop="title" :label="ticket.label || '标题'" min-width="160" />
      <el-table-column prop="typeName" label="类型" width="100" />
      <el-table-column prop="location" label="地点" width="140" />
      <el-table-column prop="username" :label="userLabel" width="110" />
      <el-table-column v-if="allowQty" prop="qty" label="数量" width="70" />
      <el-table-column v-if="pickLoanPeriod" prop="dueAt" :label="dueLabel" width="170" />
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag size="small" :type="row.status === 'pending_final' ? '' : 'warning'" effect="plain">
            {{ statusText(row.status) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="applyAt" label="申请时间" width="170" />
      <el-table-column label="操作" width="280" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="openProgress(row)">进度</el-button>
          <el-button
            link
            type="success"
            :disabled="!canPass(row)"
            @click="openAudit(row, true)"
          >{{ passLabel(row) }}</el-button>
          <el-button link type="danger" @click="openAudit(row, false)">{{ verbs.reject || '驳回' }}</el-button>
        </template>
      </el-table-column>
      <template #empty>暂无待办</template>
    </el-table>
    <div class="pager">
      <el-pagination
        v-model:current-page="page"
        v-model:page-size="size"
        background
        layout="total, prev, pager, next"
        :total="total"
        @current-change="load"
      />
    </div>

    <el-dialog
      v-model="audit.visible"
      :title="audit.pass ? passLabel(audit.row) : (verbs.reject || '驳回')"
      width="440px"
      destroy-on-close
      @closed="resetAudit"
    >
      <p class="audit-tip">
        {{ audit.pass ? `确认${passLabel(audit.row)}该${ticketNoun}？` : `确认${verbs.reject || '驳回'}该${ticketNoun}？` }}
        <template v-if="audit.row">「{{ audit.row.title || ('编号 ' + audit.row.id) }}」</template>
      </p>
      <div v-if="audit.row?.attachUrl" class="audit-body">
        <div class="lab">附件</div>
        <a :href="audit.row.attachUrl" target="_blank" rel="noopener noreferrer">查看附件</a>
      </div>
      <div v-if="richRemark && audit.row?.remark" class="audit-body">
        <div class="lab">申请内容</div>
        <RichTextView :html="audit.row.remark" />
      </div>
      <label class="audit-field">
        <span class="lab">
          {{ audit.pass ? '审核备注' : '驳回原因' }}
          <i v-if="!audit.pass" class="req" aria-hidden="true">*</i>
          <template v-else>（选填）</template>
        </span>
        <el-input
          v-model="audit.remark"
          type="textarea"
          :rows="3"
          maxlength="200"
          show-word-limit
          :placeholder="audit.pass ? '可填写受理说明，留空则保留申请说明' : '请说明驳回原因，申请人可见'"
        />
      </label>
      <template #footer>
        <el-button @click="audit.visible = false">取消</el-button>
        <el-button
          type="primary"
          :loading="audit.loading"
          :disabled="!audit.pass && !audit.remark.trim()"
          @click="submitAudit"
        >确定</el-button>
      </template>
    </el-dialog>

    <TicketProgressDialog v-model="progressVisible" :ticket-id="progressId" />
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import http from '../../api/http'
import RichTextView from '../../components/RichTextView.vue'
import TicketProgressDialog from '../../components/TicketProgressDialog.vue'
import { getSchema, menuLabel, ticketCopy, ticketDueLabel } from '../../utils/domainSchema.js'

const ticket = ticketCopy()
const verbs = computed(() => ticket.verbs || {})
const states = computed(() => ticket.states || {})
const ticketNoun = computed(() => ticket.label || '申请')
const richRemark = computed(() => !!ticket.richRemark)
const twoLevel = computed(() => !!ticket.twoLevelApprove)
const allowQty = computed(() => !!ticket.allowQty)
const pickLoanPeriod = computed(() => !!ticket.pickLoanPeriod)
const dueLabel = computed(() => ticketDueLabel())
const userLabel = computed(() => getSchema()?.roles?.user?.label || '用户')
const recordsLabel = computed(() => menuLabel('admin', 'ticket_records', ticket.recordsMenu || '记录'))
const superAdmin = localStorage.getItem('superAdmin') === 'true'

const todoHint = computed(() => {
  const base = `待受理 · 历史见「${recordsLabel.value}」`
  return twoLevel.value ? `${base} · 二级审批（终审需总管）` : base
})

const list = ref([])
const total = ref(0)
const page = ref(1)
const size = ref(10)

const audit = reactive({
  visible: false,
  loading: false,
  pass: true,
  remark: '',
  row: null,
})

const progressVisible = ref(false)
const progressId = ref(null)

function statusText(s) {
  return states.value[s] || ({ pending: '待初审', pending_final: '待终审' }[s]) || s
}

function passLabel(row) {
  if (!twoLevel.value || !row) return verbs.value.approve || '受理'
  if (row.status === 'pending_final') return '终审通过'
  return '初审通过'
}

function canPass(row) {
  if (!twoLevel.value) return true
  if (row?.status === 'pending_final') return superAdmin
  return true
}

async function load() {
  const res = await http.get('/api/tickets', {
    params: { page: page.value, size: size.value, status: 'todo' },
  })
  list.value = res.data.list
  total.value = res.data.total
}

function openAudit(row, pass) {
  if (pass && !canPass(row)) {
    ElMessage.warning('终审通过需总管操作')
    return
  }
  audit.row = row
  audit.pass = pass
  audit.remark = ''
  audit.visible = true
}

function resetAudit() {
  audit.row = null
  audit.remark = ''
  audit.loading = false
}

async function submitAudit() {
  if (!audit.row) return
  const remark = audit.remark.trim()
  if (!audit.pass && !remark) {
    ElMessage.warning('请填写驳回原因')
    return
  }
  audit.loading = true
  try {
    await http.post(`/api/tickets/${audit.row.id}/approve`, {
      pass: audit.pass,
      remark,
    })
    ElMessage.success('已处理')
    audit.visible = false
    load()
  } finally {
    audit.loading = false
  }
}

function openProgress(row) {
  progressId.value = row.id
  progressVisible.value = true
}

onMounted(load)
</script>

<style scoped>
.toolbar { margin-bottom: 12px; }
.pager { margin-top: 16px; display: flex; justify-content: flex-end; }
.audit-tip {
  margin: 0 0 14px;
  font-size: 14px;
  color: var(--el-text-color-regular);
  line-height: 1.5;
}
.audit-field {
  display: flex;
  flex-direction: column;
  gap: 8px;
  font-size: 13px;
  color: var(--el-text-color-primary);
}
.lab { font-weight: 500; }
.audit-body {
  margin: 0 0 14px;
  padding: 10px 12px;
  border-radius: 8px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
}
.audit-body .lab { margin-bottom: 6px; font-size: 13px; color: #64748b; }
.audit-body a { color: #0369a1; font-size: 13px; }
.req {
  color: var(--el-color-danger, #f56c6c);
  margin-left: 2px;
  font-style: normal;
  font-weight: 600;
}
</style>
