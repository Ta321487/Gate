<template>
  <div>
    <div class="toolbar">
      <el-alert type="info" :closable="false" show-icon :title="`待受理 · 历史见「${recordsLabel}」`" />
    </div>
    <div class="toolbar">
      <el-button type="primary" @click="load">刷新待办</el-button>
    </div>
    <el-table :data="list" stripe>
      <el-table-column prop="id" label="单号" width="70" />
      <el-table-column prop="title" :label="ticket.label || '标题'" min-width="160" />
      <el-table-column prop="typeName" label="类型" width="100" />
      <el-table-column prop="location" label="地点" width="140" />
      <el-table-column prop="username" :label="userLabel" width="110" />
      <el-table-column prop="applyAt" label="申请时间" width="170" />
      <el-table-column label="操作" width="180" fixed="right">
        <template #default="{ row }">
          <el-button link type="success" @click="openAudit(row, true)">{{ verbs.approve || '受理' }}</el-button>
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
      :title="audit.pass ? (verbs.approve || '受理') : (verbs.reject || '驳回')"
      width="440px"
      destroy-on-close
      @closed="resetAudit"
    >
      <p class="audit-tip">
        {{ audit.pass ? `确认${verbs.approve || '受理'}该单据？` : `确认${verbs.reject || '驳回'}该单据？` }}
        <template v-if="audit.row">「{{ audit.row.title || ('单号 ' + audit.row.id) }}」</template>
      </p>
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
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import http from '../../api/http'
import RichTextView from '../../components/RichTextView.vue'
import { getSchema, menuLabel, ticketCopy } from '../../utils/domainSchema.js'

const ticket = ticketCopy()
const verbs = computed(() => ticket.verbs || {})
const richRemark = computed(() => !!ticket.richRemark)
const userLabel = computed(() => getSchema()?.roles?.user?.label || '用户')
const recordsLabel = computed(() => menuLabel('admin', 'ticket_records', '单据记录'))

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

async function load() {
  const res = await http.get('/api/tickets', {
    params: { page: page.value, size: size.value, status: 'pending' },
  })
  list.value = res.data.list
  total.value = res.data.total
}

function openAudit(row, pass) {
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
.req {
  color: var(--el-color-danger, #f56c6c);
  margin-left: 2px;
  font-style: normal;
  font-weight: 600;
}
</style>
