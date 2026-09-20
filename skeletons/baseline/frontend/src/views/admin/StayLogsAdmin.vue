<template>
  <div>
    <p class="hint">按天记下这一次寄养的情况，预约人可以看到。</p>
    <div class="toolbar">
      <el-button type="primary" @click="openCreate">添加记录</el-button>
      <el-button @click="load">刷新</el-button>
    </div>
    <el-table :data="list" stripe>
      <el-table-column prop="reservationId" label="寄养" width="90" />
      <el-table-column prop="dayKey" label="日期" width="120" />
      <el-table-column prop="note" label="记录" min-width="160" />
      <el-table-column label="照片" min-width="140">
        <template #default="{ row }">
          <a v-if="row.photoUrl" class="link" :href="row.photoUrl" target="_blank" rel="noopener noreferrer">查看</a>
          <span v-else>无</span>
        </template>
      </el-table-column>
    </el-table>
    <p v-if="!list.length" class="empty">还没有每日记录。</p>
    <el-dialog v-model="visible" title="添加记录" width="460px">
      <el-form label-width="72px">
        <el-form-item label="寄养" required>
          <el-select v-model="form.reservationId" placeholder="请选择" style="width: 100%">
            <el-option
              v-for="r in stays"
              :key="r.id"
              :label="stayLabel(r)"
              :value="r.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="日期" required>
          <el-date-picker v-model="form.dayKey" type="date" value-format="YYYY-MM-DD" />
        </el-form-item>
        <el-form-item label="记录">
          <el-input v-model="form.note" maxlength="200" type="textarea" />
        </el-form-item>
        <el-form-item label="照片">
          <el-input v-model="form.photoUrl" maxlength="255" placeholder="https://" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="visible = false">取消</el-button>
        <el-button type="primary" @click="save">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import http from '../../api/http'

const list = ref([])
const stays = ref([])
const visible = ref(false)
const form = reactive({ reservationId: null, dayKey: '', note: '', photoUrl: '' })

function stayLabel(row) {
  const name = row.guestName || row.username || ''
  return name ? `${row.id} ${name}` : String(row.id)
}

async function load() {
  const res = await http.get('/api/boarding/logs')
  list.value = res.data || []
  const staysRes = await http.get('/api/slots/reservations', { params: { page: 1, size: 50 } })
  stays.value = staysRes.data?.list || []
}

function openCreate() {
  Object.assign(form, { reservationId: null, dayKey: '', note: '', photoUrl: '' })
  visible.value = true
}

async function save() {
  if (!form.reservationId) {
    ElMessage.warning('请选择寄养')
    return
  }
  if (!form.dayKey) {
    ElMessage.warning('请选择日期')
    return
  }
  await http.post('/api/boarding/logs', { ...form })
  ElMessage.success('已保存')
  visible.value = false
  await load()
}

onMounted(load)
</script>

<style scoped>
.hint, .empty { color: var(--el-text-color-secondary); margin: 0 0 12px; }
.toolbar { margin-bottom: 12px; }
.link { color: var(--el-color-primary); }
</style>
