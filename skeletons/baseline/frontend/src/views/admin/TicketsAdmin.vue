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
      <el-table-column prop="typeName" :label="typeColLabel" width="110" show-overflow-tooltip />
      <el-table-column prop="location" :label="locationColLabel" min-width="140" show-overflow-tooltip />
      <el-table-column :label="userLabel" width="110">
        <template #default="{ row }">{{ personLabel(row) }}</template>
      </el-table-column>
      <el-table-column prop="assigneeUsername" label="处理人" width="110">
        <template #default="{ row }">{{ row.assigneeUsername || '—' }}</template>
      </el-table-column>
      <el-table-column v-if="requireRemark" :label="remarkLabel" min-width="140" show-overflow-tooltip>
        <template #default="{ row }">
          <span v-if="row.remark">{{ remarkPlain(row.remark) }}</span>
          <span v-else class="muted">—</span>
        </template>
      </el-table-column>
      <el-table-column v-if="showFollowCols" :label="channelLabel" width="100" show-overflow-tooltip>
        <template #default="{ row }">{{ row.contactChannel || '—' }}</template>
      </el-table-column>
      <el-table-column v-if="showFollowCols" :label="nextAtLabel" width="170">
        <template #default="{ row }">{{ row.nextFollowAt || '—' }}</template>
      </el-table-column>
      <el-table-column label="附件" width="90">
        <template #default="{ row }">
          <a v-if="row.attachUrl" :href="row.attachUrl" target="_blank" rel="noopener noreferrer">查看</a>
          <span v-else class="muted">—</span>
        </template>
      </el-table-column>
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
      <div v-if="audit.row?.typeName || audit.row?.location" class="audit-body">
        <div class="lab">{{ archive.label || '档案' }}信息</div>
        <p v-if="audit.row.typeName" class="audit-meta">{{ typeColLabel }}：{{ audit.row.typeName }}</p>
        <p v-if="audit.row.location" class="audit-meta">{{ locationColLabel }}：{{ audit.row.location }}</p>
      </div>
      <div v-if="showFollowCols && (audit.row?.contactChannel || audit.row?.nextFollowAt)" class="audit-body">
        <div class="lab">补充信息</div>
        <p v-if="audit.row.contactChannel" class="audit-meta">{{ channelLabel }}：{{ audit.row.contactChannel }}</p>
        <p v-if="audit.row.nextFollowAt" class="audit-meta">{{ nextAtLabel }}：{{ audit.row.nextFollowAt }}</p>
      </div>
      <div v-if="audit.row?.remark" class="audit-body">
        <div class="lab">{{ remarkLabel }}</div>
        <RichTextView v-if="richRemark" :html="audit.row.remark" />
        <p v-else class="audit-meta">{{ audit.row.remark }}</p>
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
import {
  archiveCopy,
  followChannelLabel,
  getSchema,
  hasTrait,
  menuLabel,
  nextFollowLabel,
  personLabel,
  ticketCopy,
  ticketDueLabel,
} from '../../utils/domainSchema.js'
import { plainFromHtml } from '../../utils/richHtml.js'

const ticket = ticketCopy()
const archive = archiveCopy()
const verbs = computed(() => ticket.verbs || {})
const states = computed(() => ticket.states || {})
const ticketNoun = computed(() => ticket.label || '申请')
const richRemark = computed(() => !!ticket.richRemark)
const requireRemark = computed(() => !!ticket.requireRemark)
const remarkLabel = computed(() => ticket.remarkLabel || '说明')
const twoLevel = computed(() => !!ticket.twoLevelApprove)
const allowQty = computed(() => !!ticket.allowQty)
const pickLoanPeriod = computed(() => !!ticket.pickLoanPeriod)
const dueLabel = computed(() => ticketDueLabel())
const userLabel = computed(() => getSchema()?.roles?.user?.label || '用户')
const recordsLabel = computed(() => menuLabel('admin', 'ticket_records', ticket.recordsMenu || '记录'))
const showFollowCols = computed(() => hasTrait('crm'))
const channelLabel = computed(() => followChannelLabel())
const nextAtLabel = computed(() => nextFollowLabel())
const superAdmin = localStorage.getItem('superAdmin') === 'true'

function archiveFieldLabel(key, fallback) {
  const f = (archive.fields || []).find((x) => x.key === key)
  return f?.label || fallback
}

const typeColLabel = computed(() => {
  if ((archive.fields || []).some((f) => f.key === 'itemKind')) {
    return archiveFieldLabel('itemKind', '类型')
  }
  if ((archive.fields || []).some((f) => f.key === 'category')) {
    return archiveFieldLabel('category', '类型')
  }
  return '类型'
})

const locationColLabel = computed(() => {
  if ((archive.fields || []).some((f) => f.key === 'isbn')) {
    return archiveFieldLabel('isbn', '地点')
  }
  return '地点'
})

function remarkPlain(v) {
  if (!v) return ''
  return richRemark.value ? plainFromHtml(String(v)) : String(v)
}

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
    const res = await http.post(`/api/tickets/${audit.row.id}/approve`, {
      pass: audit.pass,
      remark,
    })
    const n = Number(res?.data?.autoRejectedCount) || 0
    ElMessage.success(
      audit.pass && n > 0
        ? `已处理；另有 ${n} 条同对象待审已自动驳回`
        : '已处理',
    )
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
  border-radius: var(--portal-radius-sm, 8px);
  background: #f8fafc;
  border: var(--portal-border-width, 1px) solid var(--portal-line, #e2e8f0);
}
.audit-body .lab { margin-bottom: 6px; font-size: 13px; color: var(--portal-muted, #64748b); }
.audit-body a { color: #0369a1; font-size: 13px; }
.audit-meta {
  margin: 0 0 4px;
  font-size: 13px;
  color: var(--portal-ink, #334155);
  line-height: 1.5;
  white-space: pre-wrap;
  word-break: break-word;
}
.audit-meta:last-child { margin-bottom: 0; }
.req {
  color: var(--el-color-danger, #f56c6c);
  margin-left: 2px;
  font-style: normal;
  font-weight: 600;
}
.muted { color: var(--portal-muted, #94a3b8); }
</style>
