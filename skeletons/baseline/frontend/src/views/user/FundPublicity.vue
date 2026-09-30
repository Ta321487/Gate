<template>
  <div>
    <section class="hero">
      <h1>{{ title }}</h1>
      <p>{{ lead }}</p>
    </section>
    <el-table :data="list" stripe empty-text="暂无公示记录">
      <el-table-column prop="title" label="公示标题" min-width="200" />
      <el-table-column label="公示期" min-width="190">
        <template #default="{ row }">
          {{ row.startAt || '—' }} ~ {{ row.endAt || '—' }}
        </template>
      </el-table-column>
      <el-table-column label="状态" width="110">
        <template #default="{ row }">
          <el-tag :type="row.status === 'closed' ? 'info' : 'success'" size="small">
            {{ row.status === 'closed' ? '已结束' : '公示中' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="objectionDueAt" :label="objectionWindowLabel" min-width="130">
        <template #default="{ row }">{{ row.objectionDueAt || '—' }}</template>
      </el-table-column>
      <el-table-column prop="objectionNote" :label="objectionNoteLabel" min-width="180">
        <template #default="{ row }">{{ row.objectionNote || '—' }}</template>
      </el-table-column>
      <el-table-column label="操作" width="130">
        <template #default="{ row }">
          <el-button
            link
            type="warning"
            :disabled="!row.objectionDueAt || objectionClosed(row)"
            @click="openObjection(row)"
          >{{ objectionNoteLabel }}</el-button>
        </template>
      </el-table-column>
    </el-table>
    <p v-if="!list.length" class="empty">还没有公示记录，公示开始后可在此查阅。</p>

    <el-dialog v-model="objectionDlg.visible" :title="objectionNoteLabel" width="420px">
      <p class="sub">{{ objectionWindowHint }}</p>
      <el-input
        v-model="objectionDlg.note"
        type="textarea"
        :rows="3"
        maxlength="255"
        show-word-limit
        placeholder="请填写异议内容"
      />
      <template #footer>
        <el-button @click="objectionDlg.visible = false">取消</el-button>
        <el-button type="primary" :loading="objectionDlg.saving" @click="submitObjection">提交异议</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import http from '../../api/http'
import { getSchema } from '../../utils/domainSchema.js'

const labels = getSchema()?.labels || {}
const title = labels.fundPublicityMineTitle || '公示查阅'
const lead = labels.fundPublicityMineLead || '查看本人申请项目的公示状态与公示期。'
const objectionWindowLabel = labels.objectionWindowLabel || '异议登记截止日'
const objectionNoteLabel = labels.objectionNoteLabel || '异议说明'
const objectionWindowHint = labels.objectionWindowHint || '公示结束日 + N 天内可登记异议，逾期关闭入口。'

const list = ref([])
const objectionDlg = reactive({ visible: false, saving: false, row: null, note: '' })

function unwrap(res) {
  return res.data?.data ?? res.data
}

/** 已过窗口（当天为最后一天仍可提交）。 */
function objectionClosed(row) {
  const due = String(row?.objectionDueAt || '').slice(0, 10)
  if (!due) return true
  return new Date().toISOString().slice(0, 10) > due
}

function openObjection(row) {
  objectionDlg.row = row
  objectionDlg.note = ''
  objectionDlg.visible = true
}

async function submitObjection() {
  if (!objectionDlg.note.trim()) {
    ElMessage.warning('请填写异议内容')
    return
  }
  objectionDlg.saving = true
  try {
    await http.post(`/api/fund-publicity/${objectionDlg.row.id}/objection`, { note: objectionDlg.note.trim() })
    ElMessage.success('异议已登记')
    objectionDlg.visible = false
    await load()
  } catch (e) {
    ElMessage.error(e?.response?.data?.message || e.message || '异议登记失败')
  } finally {
    objectionDlg.saving = false
  }
}

async function load() {
  const res = await http.get('/api/fund-publicity/mine')
  list.value = unwrap(res) || []
}

onMounted(load)
</script>

<style scoped>
.hero { margin-bottom: 14px; }
.hero h1 { margin: 0 0 4px; font-size: 20px; }
.hero p { margin: 0; color: var(--portal-muted, #64748b); font-size: 13px; }
.empty { color: var(--el-text-color-secondary); }
.sub { margin: 0 0 8px; font-size: 13px; color: var(--el-text-color-secondary); }
</style>
