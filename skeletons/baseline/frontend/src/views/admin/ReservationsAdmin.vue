<template>
  <div>
    <div class="toolbar">
      <el-select v-model="status" clearable placeholder="全部状态" style="width:140px" @change="load">
        <el-option v-for="(lab, key) in states" :key="key" :label="lab" :value="key" />
      </el-select>
      <el-button type="primary" @click="load">查询</el-button>
      <el-button :disabled="!list.length" @click="exportCsv">导出 CSV</el-button>
      <el-button @click="genVisible = true">生成时段</el-button>
    </div>
    <el-table :data="list" stripe>
      <el-table-column prop="id" label="编号" width="70" />
      <el-table-column prop="itemTitle" :label="archiveLabel" min-width="140" />
      <el-table-column prop="username" :label="userLabel" width="110" />
      <el-table-column prop="startAt" label="开始" width="170" />
      <el-table-column prop="endAt" label="结束" width="170" />
      <el-table-column prop="status" label="状态" width="100">
        <template #default="{ row }">{{ states[row.status] || row.status }}</template>
      </el-table-column>
      <el-table-column prop="createdAt" :label="`${resvNoun}时间`" width="170" />
      <el-table-column label="操作" width="100" fixed="right">
        <template #default="{ row }">
          <el-button
            v-if="row.status === 'pending' || row.status === 'confirmed'"
            link
            type="danger"
            @click="cancel(row)"
          >取消</el-button>
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

    <el-dialog v-model="genVisible" :title="`为${archiveLabel}生成当日时段`" width="440px">
      <el-form label-width="96px">
        <el-form-item :label="`${archiveLabel} ID`" required>
          <el-input-number v-model="gen.itemId" :min="1" />
        </el-form-item>
        <el-form-item label="日期" required>
          <el-date-picker v-model="gen.day" type="date" value-format="YYYY-MM-DD" style="width:100%" />
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
      <template #footer>
        <el-button @click="genVisible = false">取消</el-button>
        <el-button type="primary" @click="generate">生成</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import http from '../../api/http'
import { archiveCopy, getSchema, reservationCopy } from '../../utils/domainSchema.js'
import { downloadCsv } from '../../utils/csvDownload.js'

const resv = reservationCopy()
const resvNoun = computed(() => resv.label || '预约')
const archiveLabel = computed(() => archiveCopy().label || '资源')
const userLabel = computed(() => getSchema()?.roles?.user?.label || '用户')
const states = computed(() => getSchema()?.entities?.reservation?.states || {})
const list = ref([])
const total = ref(0)
const page = ref(1)
const size = ref(10)
const status = ref(null)
const genVisible = ref(false)
const gen = reactive({
  itemId: 1,
  day: '2026-09-20',
  startHour: 9,
  endHour: 17,
  slotMinutes: 60,
  capacity: 1,
})

async function load() {
  const res = await http.get('/api/slots/reservations', {
    params: { page: page.value, size: size.value, status: status.value || undefined },
  })
  list.value = res.data?.list || []
  total.value = res.data?.total || 0
}

async function cancel(row) {
  await ElMessageBox.confirm(`取消${resvNoun.value} #${row.id}？`, '取消')
  await http.post(`/api/slots/reservations/${row.id}/cancel`)
  ElMessage.success('已取消')
  load()
}

async function generate() {
  const res = await http.post('/api/slots/generate', { ...gen })
  ElMessage.success(`已生成 ${res.data?.created ?? 0} 个时段`)
  genVisible.value = false
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
  const headers = ['编号', archiveLabel.value, userLabel.value, '开始', '结束', '状态', `${resvNoun.value}时间`]
  const data = rows.map((row) => [
    row.id,
    row.itemTitle,
    row.username,
    row.startAt,
    row.endAt,
    states.value[row.status] || row.status,
    row.createdAt,
  ])
  downloadCsv(`reservations_${status.value || 'all'}_${Date.now()}.csv`, headers, data)
  ElMessage.success(`已导出 ${rows.length} 条（UTF-8，可用 Excel 直接打开）`)
}

onMounted(load)
</script>

<style scoped>
.toolbar { margin-bottom: 12px; display: flex; gap: 8px; flex-wrap: wrap; }
.pager { margin-top: 16px; display: flex; justify-content: flex-end; }
</style>
