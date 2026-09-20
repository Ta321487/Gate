<template>
  <div>
    <p class="hint">{{ hint }}</p>
    <el-button @click="load">刷新</el-button>
    <el-table :data="list" stripe style="margin-top: 12px">
      <el-table-column prop="id" label="订单" width="80" />
      <el-table-column prop="username" label="住客" width="120" />
      <el-table-column prop="status" label="订单状态" width="100" />
      <el-table-column prop="totalAmount" label="金额" width="100" />
      <el-table-column label="操作" min-width="120">
        <template #default="{ row }">
          <el-button link type="primary" @click="open(row)">登记入住</el-button>
        </template>
      </el-table-column>
    </el-table>
    <p v-if="!list.length" class="empty">暂无待登记订单。</p>
    <el-dialog v-model="visible" title="前台登记" width="480px">
      <el-form label-width="96px">
        <el-form-item label="房间">
          <el-select v-model="form.roomId" filterable style="width: 100%">
            <el-option
              v-for="r in rooms"
              :key="r.id"
              :label="`${r.roomNo}（${r.status}）`"
              :value="r.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="入住人">
          <el-input v-model="form.guestName" maxlength="32" />
        </el-form-item>
        <el-form-item label="证件号">
          <el-input v-model="form.idNo" maxlength="32" />
        </el-form-item>
        <el-form-item label="押金(元)">
          <el-input-number v-model="form.depositYuan" :min="0" :precision="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="visible = false">取消</el-button>
        <el-button type="primary" @click="submit">确认登记</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import http from '../../api/http'
import { getSchema, hasCap } from '../../utils/domainSchema.js'

const list = ref([])
const rooms = ref([])
const visible = ref(false)
const form = reactive({
  orderId: null,
  roomId: null,
  guestName: '',
  idNo: '',
  depositYuan: 200,
})
const hint = computed(() => getSchema()?.labels?.frontDeskHint || '为住客登记入住并收取押金。')

async function load() {
  const res = await http.get('/api/hotel-pms/checkin/pending')
  list.value = res.data || []
  if (hasCap('room_board')) {
    const rr = await http.get('/api/hotel-pms/rooms')
    rooms.value = (rr.data || []).filter((r) => r.status === '空房' || r.status === '已订')
  }
}

function open(row) {
  Object.assign(form, {
    orderId: row.id,
    roomId: null,
    guestName: row.nickname || row.username || '',
    idNo: '',
    depositYuan: 200,
  })
  visible.value = true
}

async function submit() {
  await http.post('/api/hotel-pms/checkin', { ...form })
  ElMessage.success('已登记')
  visible.value = false
  await load()
}

onMounted(load)
</script>

<style scoped>
.hint { color: #666; margin-bottom: 12px; }
.empty { color: #999; margin-top: 16px; }
</style>
