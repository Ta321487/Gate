<template>
  <div>
    <h2>时长账户</h2>
    <el-card class="adjust" shadow="never">
      <template #header>调整存入</template>
      <el-form inline @submit.prevent>
        <el-form-item label="用户名">
          <el-input v-model="form.username" style="width: 140px" />
        </el-form-item>
        <el-form-item label="小时">
          <el-input-number v-model="form.hours" :min="0.5" :max="500" :step="0.5" />
        </el-form-item>
        <el-form-item label="说明">
          <el-input v-model="form.reason" style="width: 180px" />
        </el-form-item>
        <el-button type="primary" :loading="busy" @click="earn">存入</el-button>
      </el-form>
    </el-card>
    <el-table :data="list" stripe>
      <el-table-column prop="username" label="用户" width="140" />
      <el-table-column prop="balanceHours" label="余额(小时)" width="120" />
      <el-table-column prop="updatedAt" label="更新时间" />
    </el-table>
    <el-pagination
      v-if="total > size"
      class="pager"
      layout="prev, pager, next"
      :total="total"
      :page-size="size"
      v-model:current-page="page"
      @current-change="load"
    />
  </div>
</template>

<script setup>
import { onMounted, reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import http from '../../utils/http'

const list = ref([])
const total = ref(0)
const page = ref(1)
const size = 20
const busy = ref(false)
const form = reactive({ username: 'user', hours: 1, reason: '管理端调整' })

async function load() {
  const res = await http.get('/api/timebank/admin/accounts', { params: { page: page.value, size } })
  const data = res.data?.data || res.data || {}
  list.value = data.list || []
  total.value = data.total || 0
}

async function earn() {
  if (!form.username) {
    ElMessage.warning('请填写用户名')
    return
  }
  busy.value = true
  try {
    await http.post('/api/timebank/admin/earn', { ...form })
    ElMessage.success('已存入')
    await load()
  } catch (e) {
    ElMessage.error(e?.response?.data?.message || e.message || '失败')
  } finally {
    busy.value = false
  }
}

watch(page, load)
onMounted(load)
</script>

<style scoped>
.adjust { margin: 1rem 0; }
.pager { margin-top: 1rem; }
</style>
