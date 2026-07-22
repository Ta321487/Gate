<template>
  <div>
    <el-table :data="list" stripe>
      <el-table-column prop="orderId" label="订单" width="90" />
      <el-table-column label="用户" width="120">
        <template #default="{ row }">{{ row.displayName || row.username || '—' }}</template>
      </el-table-column>
      <el-table-column label="评分" width="140">
        <template #default="{ row }"><el-rate :model-value="row.rating" disabled /></template>
      </el-table-column>
      <el-table-column prop="body" label="评价" min-width="180" show-overflow-tooltip />
      <el-table-column prop="reply" label="回复" min-width="140" show-overflow-tooltip>
        <template #default="{ row }">{{ row.reply || '—' }}</template>
      </el-table-column>
      <el-table-column prop="createdAt" label="时间" width="170" />
      <el-table-column label="操作" width="100" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="openReply(row)">回复</el-button>
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
    <el-dialog v-model="visible" title="回复评价" width="520px">
      <p class="quote">{{ current.body || '（无文字）' }}</p>
      <el-input
        v-model="replyText"
        type="textarea"
        :rows="4"
        maxlength="500"
        show-word-limit
        placeholder="简短回复"
      />
      <template #footer>
        <el-button @click="visible = false">取消</el-button>
        <el-button type="primary" @click="saveReply">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import http from '../../api/http'

const list = ref([])
const page = ref(1)
const size = ref(20)
const total = ref(0)
const visible = ref(false)
const replyText = ref('')
const current = reactive({ id: null, body: '' })

async function load() {
  const res = await http.get('/api/order-reviews', {
    params: { page: page.value, size: size.value },
  })
  list.value = res.data?.list || []
  total.value = res.data?.total || 0
}

function openReply(row) {
  Object.assign(current, { id: row.id, body: row.body || '' })
  replyText.value = row.reply || ''
  visible.value = true
}

async function saveReply() {
  if (!replyText.value.trim()) {
    ElMessage.warning('请填写回复')
    return
  }
  await http.post(`/api/order-reviews/${current.id}/reply`, { reply: replyText.value.trim() })
  ElMessage.success('已回复')
  visible.value = false
  load()
}

onMounted(load)
</script>

<style scoped>
.pager { margin-top: 16px; display: flex; justify-content: flex-end; }
.quote {
  margin: 0 0 12px;
  padding: 10px 12px;
  background: color-mix(in srgb, var(--portal-bg, #f5f7fa) 85%, var(--portal-mix, #fff));
  border: var(--portal-border-width, 1px) solid var(--portal-line, #e2e8f0);
  border-radius: var(--portal-radius-sm, 4px);
  white-space: pre-wrap;
  line-height: 1.55;
  font-size: 13px;
  color: var(--portal-muted, #606266);
}
</style>
