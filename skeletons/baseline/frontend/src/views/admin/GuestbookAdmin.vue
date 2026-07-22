<template>
  <div>
    <el-table :data="list" stripe>
      <el-table-column prop="nickname" label="留言人" width="120">
        <template #default="{ row }">{{ row.nickname || row.username || '—' }}</template>
      </el-table-column>
      <el-table-column prop="body" label="内容" min-width="200" show-overflow-tooltip />
      <el-table-column prop="reply" label="回复" min-width="160" show-overflow-tooltip>
        <template #default="{ row }">{{ row.reply || '—' }}</template>
      </el-table-column>
      <el-table-column prop="createdAt" label="时间" width="170" />
      <el-table-column label="操作" width="160" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="openReply(row)">回复</el-button>
          <el-button link type="danger" @click="remove(row)">删除</el-button>
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
    <el-dialog v-model="visible" title="回复留言" width="520px">
      <p class="quote">{{ current.body }}</p>
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
/** 留言管理：总管列表 / 回复 / 删除 */
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import http from '../../api/http'

const list = ref([])
const page = ref(1)
const size = ref(20)
const total = ref(0)
const visible = ref(false)
const replyText = ref('')
const current = reactive({ id: null, body: '' })

async function load() {
  const res = await http.get('/api/guestbook', { params: { page: page.value, size: size.value } })
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
  await http.put(`/api/guestbook/${current.id}/reply`, { reply: replyText.value.trim() })
  ElMessage.success('已回复')
  visible.value = false
  load()
}

async function remove(row) {
  await ElMessageBox.confirm('确认删除该留言？', '删除')
  await http.delete(`/api/guestbook/${row.id}`)
  ElMessage.success('已删除')
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
