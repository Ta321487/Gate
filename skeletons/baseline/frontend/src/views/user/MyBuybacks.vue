<template>
  <div>
    <p class="hint">先等报价。同意后按所选时段上门。不同意后这单结束。</p>
    <el-form label-position="top" class="form">
      <el-form-item label="书名" required>
        <el-input v-model="form.bookTitle" maxlength="80" />
      </el-form-item>
      <el-form-item label="成色说明">
        <el-input v-model="form.conditionNote" maxlength="200" type="textarea" />
      </el-form-item>
      <el-form-item label="上门时段" required>
        <el-select v-model="form.slotId" placeholder="请选择" style="width: 220px">
          <el-option v-for="s in slots" :key="s.id" :label="s.name" :value="s.id" />
        </el-select>
        <p v-if="!slots.length" class="empty">暂无可选上门时段。</p>
      </el-form-item>
      <el-button type="primary" @click="submit">提交</el-button>
    </el-form>
    <el-table :data="list" stripe>
      <el-table-column prop="bookTitle" label="书名" min-width="120" />
      <el-table-column prop="slotName" label="上门时段" width="120" />
      <el-table-column prop="quoteYuan" label="报价" width="90" />
      <el-table-column label="状态" width="100">
        <template #default="{ row }">{{ statusText(row.status) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="160">
        <template #default="{ row }">
          <template v-if="row.status === 'quoted'">
            <el-button link type="primary" @click="decide(row, true)">同意</el-button>
            <el-button link @click="decide(row, false)">不同意</el-button>
          </template>
        </template>
      </el-table-column>
    </el-table>
    <p v-if="!list.length" class="empty">还没有回收单。</p>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import http from '../../api/http'

const STATUS = {
  pending: '待估价',
  quoted: '已报价',
  agreed: '已同意',
  picked: '已上门',
  stocked: '已入库',
  listed: '已上架',
  closed: '已结束',
}

const list = ref([])
const slots = ref([])
const form = reactive({ bookTitle: '', conditionNote: '', slotId: null })

function statusText(status) {
  return STATUS[status] || status || ''
}

async function load() {
  const mine = await http.get('/api/buybacks/mine')
  list.value = mine.data || []
  const slotRes = await http.get('/api/buybacks/slots')
  slots.value = slotRes.data || []
}

async function submit() {
  if (!String(form.bookTitle || '').trim()) {
    ElMessage.warning('请填写书名')
    return
  }
  if (!form.slotId) {
    ElMessage.warning('请选择上门时段')
    return
  }
  await http.post('/api/buybacks', { ...form })
  ElMessage.success('已提交')
  form.bookTitle = ''
  form.conditionNote = ''
  form.slotId = null
  await load()
}

async function decide(row, agree) {
  await http.post(`/api/buybacks/${row.id}/decide`, { agree })
  ElMessage.success(agree ? '已同意' : '已结束')
  await load()
}

onMounted(load)
</script>

<style scoped>
.hint, .empty { color: var(--el-text-color-secondary); margin: 0 0 12px; }
.form { max-width: 480px; margin-bottom: 16px; }
</style>
