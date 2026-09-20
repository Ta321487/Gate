<template>
  <div>
    <p class="hint">退房时汇总挂账，退还剩余押金，房间转入待打扫。</p>
    <el-button @click="load">刷新</el-button>
    <el-table :data="list" stripe style="margin-top: 12px">
      <el-table-column prop="id" label="登记" width="80" />
      <el-table-column prop="roomNo" label="房号" width="90" />
      <el-table-column prop="guestName" label="入住人" width="120" />
      <el-table-column prop="depositYuan" label="押金" width="90" />
      <el-table-column label="操作" min-width="220">
        <template #default="{ row }">
          <el-button link type="primary" @click="openConsume(row)">挂账</el-button>
          <el-button link type="warning" @click="doCheckout(row)">退房结算</el-button>
        </template>
      </el-table-column>
    </el-table>
    <p v-if="!list.length" class="empty">暂无在住登记。</p>
    <el-dialog v-model="consumeVisible" title="消费挂账" width="420px">
      <el-form label-width="88px">
        <el-form-item label="项目">
          <el-input v-model="consume.title" maxlength="64" />
        </el-form-item>
        <el-form-item label="金额">
          <el-input-number v-model="consume.amountYuan" :min="0" :precision="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="consumeVisible = false">取消</el-button>
        <el-button type="primary" @click="saveConsume">添加</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import http from '../../api/http'

const list = ref([])
const consumeVisible = ref(false)
const consume = reactive({ checkinId: null, title: '', amountYuan: 0 })

async function load() {
  const res = await http.get('/api/hotel-pms/checkout/pending')
  list.value = res.data || []
}

function openConsume(row) {
  Object.assign(consume, { checkinId: row.id, title: '', amountYuan: 0 })
  consumeVisible.value = true
}

async function saveConsume() {
  await http.post(`/api/hotel-pms/consumption/${consume.checkinId}`, {
    title: consume.title,
    amountYuan: consume.amountYuan,
  })
  ElMessage.success('已挂账')
  consumeVisible.value = false
}

async function doCheckout(row) {
  await ElMessageBox.confirm(`确认结算房号 ${row.roomNo || ''} 并退房？`, '退房结算')
  await http.post(`/api/hotel-pms/checkout/${row.id}`, { note: '' })
  ElMessage.success('已退房')
  await load()
}

onMounted(load)
</script>

<style scoped>
.hint { color: #666; margin-bottom: 12px; }
.empty { color: #999; margin-top: 16px; }
</style>
