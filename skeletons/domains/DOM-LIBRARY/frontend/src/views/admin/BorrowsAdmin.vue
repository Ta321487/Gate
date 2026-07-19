<template>
  <div>
    <div class="toolbar">
      <el-alert type="info" :closable="false" show-icon title="待审核 · 历史见「借阅记录」" />
    </div>
    <div class="toolbar">
      <el-button type="primary" @click="load">刷新待审</el-button>
    </div>
    <el-table :data="list" stripe>
      <el-table-column prop="id" label="单号" width="70" />
      <el-table-column prop="bookTitle" label="书名" min-width="160" />
      <el-table-column prop="username" label="读者" width="110" />
      <el-table-column prop="applyAt" label="申请时间" width="170" />
      <el-table-column label="操作" width="180" fixed="right">
        <template #default="{ row }">
          <el-button link type="success" @click="openAudit(row, true)">通过</el-button>
          <el-button link type="danger" @click="openAudit(row, false)">驳回</el-button>
        </template>
      </el-table-column>
      <template #empty>暂无待审核申请</template>
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
      :title="audit.pass ? '通过' : '驳回'"
      width="440px"
      destroy-on-close
      @closed="resetAudit"
    >
      <p class="audit-tip">
        {{ audit.pass ? '确认通过？借期 14 天。' : '确认驳回该申请？' }}
        <template v-if="audit.row">「{{ audit.row.bookTitle || ('单号 ' + audit.row.id) }}」</template>
      </p>
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
          :placeholder="audit.pass ? '可填写通过说明' : '请说明驳回原因，读者可见'"
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
/** 借阅审核：只盯 pending；驳回须填原因 */
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import http from '../../api/http'

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
  const res = await http.get('/api/borrows', {
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
    await http.post(`/api/borrows/${audit.row.id}/approve`, {
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
.req {
  color: var(--el-color-danger, #f56c6c);
  margin-left: 2px;
  font-style: normal;
  font-weight: 600;
}
</style>
