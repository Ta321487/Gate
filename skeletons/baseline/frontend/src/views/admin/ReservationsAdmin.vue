<template>
  <div>
    <div class="toolbar">
      <el-select v-model="status" clearable placeholder="全部状态" style="width:140px" @change="load">
        <el-option v-for="(lab, key) in states" :key="key" :label="lab" :value="key" />
      </el-select>
      <el-button type="primary" @click="load">查询</el-button>
      <el-button :disabled="!list.length" @click="exportCsv">导出 CSV</el-button>
      <el-button @click="openGenerate">生成时段</el-button>
    </div>
    <el-table :data="list" stripe>
      <el-table-column prop="id" label="编号" width="70" />
      <el-table-column prop="itemTitle" :label="archiveLabel" min-width="140" />
      <el-table-column :label="userLabel" width="110">
        <template #default="{ row }">{{ personLabel(row) }}</template>
      </el-table-column>
      <el-table-column prop="startAt" label="开始" width="170" />
      <el-table-column prop="endAt" label="结束" width="170" />
      <el-table-column prop="status" label="状态" width="100">
        <template #default="{ row }">{{ states[row.status] || row.status }}</template>
      </el-table-column>
      <el-table-column prop="createdAt" :label="`${resvNoun}时间`" width="170" />
      <el-table-column label="详情" min-width="160" show-overflow-tooltip>
        <template #default="{ row }">{{ resvDetail(row) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="160" fixed="right">
        <template #default="{ row }">
          <el-button
            v-if="requireConfirm && row.status === 'pending'"
            link
            type="primary"
            @click="confirmRow(row)"
          >确认</el-button>
          <el-button
            v-if="row.status === 'pending' || row.status === 'confirmed'"
            link
            type="danger"
            @click="cancel(row)"
          >{{ row.status === 'pending' && requireConfirm ? '驳回' : '取消' }}</el-button>
        </template>
      </el-table-column>
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

    <el-dialog v-model="genVisible" :title="`为${archiveLabel}生成当日时段`" width="520px">
      <el-form label-width="96px">
        <el-form-item :label="archiveLabel" required>
          <el-select
            v-model="gen.itemId"
            filterable
            clearable
            :placeholder="`选择${archiveLabel}`"
            style="width:100%"
            @change="loadSlotPreview"
          >
            <el-option
              v-for="it in archiveOptions"
              :key="it.id"
              :label="archiveOptionLabel(it)"
              :value="it.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="日期" required>
          <el-date-picker
            v-model="gen.day"
            type="date"
            value-format="YYYY-MM-DD"
            style="width:100%"
            @change="loadSlotPreview"
          />
        </el-form-item>
        <el-form-item label="起止小时">
          <el-input-number v-model="gen.startHour" :min="0" :max="23" />
          <span style="margin:0 8px">~</span>
          <el-input-number v-model="gen.endHour" :min="1" :max="24" />
        </el-form-item>
        <el-form-item label="每段分钟">
          <el-input-number v-model="gen.slotMinutes" :min="15" :step="15" />
        </el-form-item>
        <el-form-item label="容量">
          <el-input-number v-model="gen.capacity" :min="1" />
        </el-form-item>
      </el-form>
      <p class="hint">
        生成的是可预约号源，不会出现在下方「{{ resvNoun }}记录」表中；
        {{ userLabel }}在「选{{ archiveLabel }}」页可见。
      </p>
      <div v-if="genPreview.length" class="preview">
        <div class="preview-hd">当日号源（{{ genPreview.length }}）</div>
        <ul>
          <li v-for="s in genPreview" :key="s.id">
            {{ s.startAt }} ~ {{ s.endAt }}
            <span class="muted">余 {{ Math.max(0, (s.capacity || 0) - (s.booked || 0)) }}/{{ s.capacity || 0 }}</span>
          </li>
        </ul>
      </div>
      <template #footer>
        <el-button @click="genVisible = false">关闭</el-button>
        <el-button type="primary" :loading="genLoading" @click="generate">生成</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import http from '../../api/http'
import { archiveCopy, getSchema, personLabel, reservationCopy } from '../../utils/domainSchema.js'
import { todayStr } from '../../utils/dates.js'
import { downloadCsv } from '../../utils/csvDownload.js'

const resv = reservationCopy()
const resvNoun = computed(() => resv.label || '预约')
const requireConfirm = computed(() => !!resv.requireConfirm)
const archiveLabel = computed(() => archiveCopy().label || '资源')
const userLabel = computed(() => getSchema()?.roles?.user?.label || '用户')
const states = computed(() => getSchema()?.entities?.reservation?.states || {})
const list = ref([])
const total = ref(0)
const page = ref(1)
const size = ref(10)
const status = ref(null)
const genVisible = ref(false)
const genLoading = ref(false)
const genPreview = ref([])
const archiveOptions = ref([])
const gen = reactive({
  itemId: null,
  day: todayStr(),
  startHour: 9,
  endHour: 17,
  slotMinutes: 60,
  capacity: 1,
})

function archiveOptionLabel(it) {
  const title = (it.title || it.name || `${archiveLabel.value}#${it.id}`).toString().trim()
  const cat = (it.categoryName || '').toString().trim()
  return cat ? `${title} · ${cat}` : title
}

function resvDetail(row) {
  const parts = []
  if (row.plateNo) parts.push(`车牌 ${row.plateNo}`)
  if (row.patientName) parts.push(`就诊人 ${row.patientName}${row.visitType ? '/' + row.visitType : ''}`)
  if (row.subject) parts.push(`主题 ${row.subject}${row.partySize ? ' ·' + row.partySize + '人' : ''}`)
  if (row.guestName) parts.push(`入住人 ${row.guestName}`)
  if (row.preferredStylist) parts.push(`技师 ${row.preferredStylist}`)
  if (row.queueNo) parts.push(`排队号 ${row.queueNo}`)
  if (!parts.length && row.remark) parts.push(row.remark)
  return parts.join(' · ') || '—'
}

async function load() {
  const res = await http.get('/api/slots/reservations', {
    params: { page: page.value, size: size.value, status: status.value || undefined },
  })
  list.value = res.data?.list || []
  total.value = res.data?.total || 0
}

async function loadArchiveOptions() {
  const res = await http.get('/api/archive', { params: { page: 1, size: 200 } })
  const rows = res.data?.list || []
  archiveOptions.value = rows
  const ids = new Set(rows.map((r) => r.id))
  if (gen.itemId != null && !ids.has(gen.itemId)) gen.itemId = null
  if (gen.itemId == null && rows.length) gen.itemId = rows[0].id
}

async function openGenerate() {
  genPreview.value = []
  genVisible.value = true
  await loadArchiveOptions()
  await loadSlotPreview()
}

async function loadSlotPreview() {
  if (!gen.itemId || !gen.day) {
    genPreview.value = []
    return
  }
  const res = await http.get('/api/slots', { params: { itemId: gen.itemId, day: gen.day } })
  const rows = Array.isArray(res.data) ? res.data : (res.data?.list || [])
  genPreview.value = rows
}

async function cancel(row) {
  const reject = requireConfirm.value && row.status === 'pending'
  await ElMessageBox.confirm(
    reject ? `驳回${resvNoun.value} #${row.id}？号源将释放。` : `取消${resvNoun.value} #${row.id}？`,
    reject ? '驳回' : '取消',
  )
  await http.post(`/api/slots/reservations/${row.id}/cancel`)
  ElMessage.success(reject ? '已驳回' : '已取消')
  load()
}

async function confirmRow(row) {
  await ElMessageBox.confirm(`确认${resvNoun.value} #${row.id}？`, '确认')
  await http.post(`/api/slots/reservations/${row.id}/confirm`)
  ElMessage.success('已确认')
  load()
}

async function generate() {
  if (!gen.itemId || !gen.day) {
    ElMessage.warning(`请选择${archiveLabel.value}并填写日期`)
    return
  }
  genLoading.value = true
  try {
    const res = await http.post('/api/slots/generate', { ...gen })
    const n = res.data?.created ?? 0
    await loadSlotPreview()
    if (n > 0) {
      ElMessage.success(`已生成 ${n} 个号源时段（见弹窗列表；下方表格仍是已${resvNoun.value}记录）`)
    } else {
      ElMessage.warning('未新增时段（可能该日号源已存在），已刷新弹窗内当日号源列表')
    }
  } finally {
    genLoading.value = false
  }
}

async function exportCsv() {
  const res = await http.get('/api/slots/reservations', {
    params: { page: 1, size: 5000, status: status.value || undefined },
  })
  const rows = res.data?.list || []
  if (!rows.length) {
    ElMessage.warning('当前筛选无数据可导出')
    return
  }
  const headers = ['编号', archiveLabel.value, userLabel.value, '开始', '结束', '状态', `${resvNoun.value}时间`, '详情']
  const data = rows.map((row) => [
    row.id,
    row.itemTitle,
    personLabel(row, ''),
    row.startAt,
    row.endAt,
    states.value[row.status] || row.status,
    row.createdAt,
    resvDetail(row),
  ])
  downloadCsv(`reservations_${status.value || 'all'}_${Date.now()}.csv`, headers, data)
  ElMessage.success(`已导出 ${rows.length} 条（UTF-8，可用 Excel 直接打开）`)
}

onMounted(load)
</script>

<style scoped>
.toolbar { margin-bottom: 12px; display: flex; gap: 8px; flex-wrap: wrap; }
.pager { margin-top: 16px; display: flex; justify-content: flex-end; }
.hint { margin: 0 0 12px; color: #64748b; font-size: 13px; line-height: 1.5; }
.preview {
  max-height: 220px; overflow: auto; border: 1px solid #e2e8f0; border-radius: 8px; padding: 10px 12px;
  background: #f8fafc;
}
.preview-hd { font-weight: 600; margin-bottom: 6px; font-size: 13px; }
.preview ul { margin: 0; padding-left: 18px; }
.preview li { font-size: 13px; margin: 4px 0; }
.muted { color: #94a3b8; margin-left: 8px; }
</style>
