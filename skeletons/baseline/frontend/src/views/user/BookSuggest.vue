<template>
  <div>
    <section class="hero">
      <h1>{{ pageTitle }}</h1>
      <p>{{ pageLead }}</p>
    </section>

    <section v-if="canPost" class="composer card">
      <el-form label-position="top" class="form">
        <el-form-item label="书名" required>
          <el-input v-model="form.title" maxlength="200" show-word-limit placeholder="拟购图书题名" />
        </el-form-item>
        <div class="grid">
          <el-form-item label="ISBN">
            <el-input v-model="form.isbn" maxlength="32" placeholder="可选" />
          </el-form-item>
          <el-form-item label="作者">
            <el-input v-model="form.author" maxlength="100" placeholder="可选" />
          </el-form-item>
        </div>
        <el-form-item label="荐购理由">
          <el-input
            v-model="form.reason"
            type="textarea"
            :rows="3"
            maxlength="512"
            show-word-limit
            placeholder="教学/科研用途等（可选）"
          />
        </el-form-item>
        <el-button type="primary" :loading="posting" @click="submit">提交荐购</el-button>
      </el-form>
    </section>
    <GuestLoginHint v-else />

    <h2 class="sec">我的荐购</h2>
    <div class="table-scroll">
      <el-table :data="list" stripe>
        <el-table-column prop="title" label="书名" min-width="160" show-overflow-tooltip />
        <el-table-column prop="isbn" label="ISBN" width="130" show-overflow-tooltip />
        <el-table-column prop="author" label="作者" width="120" show-overflow-tooltip />
        <el-table-column label="状态" width="100">
          <template #default="{ row }">{{ statusLabel(row.status) }}</template>
        </el-table-column>
        <el-table-column prop="createdAt" label="提交时间" width="170" />
        <el-table-column prop="handleNote" label="审核说明" min-width="140" show-overflow-tooltip />
      </el-table>
    </div>
    <div v-if="!list.length" class="empty">暂无荐购记录</div>
    <div v-if="canPost" class="pager">
      <el-pagination
        v-model:current-page="page"
        v-model:page-size="size"
        background
        layout="total, sizes, prev, pager, next"
        :page-sizes="[10, 20, 50]"
        :total="total"
        @current-change="load"
        @size-change="load"
      />
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import http from '../api/http'
import GuestLoginHint from '../components/GuestLoginHint.vue'
import { getSchema } from '../utils/domainSchema.js'
import { isLoggedIn } from '../utils/session.js'

const labels = computed(() => getSchema()?.labels || {})
const pageTitle = computed(() => labels.value.bookSuggestPageTitle || '图书荐购')
const pageLead = computed(
  () =>
    labels.value.bookSuggestPageLead ||
    '填写拟购书目与理由提交荐购；管理员审核通过后记入台账（不自动建档入库）。',
)
const okMsg = computed(() => labels.value.bookSuggestOkMessage || '荐购已提交，请等待审核')
const canPost = computed(() => isLoggedIn())

const form = reactive({ title: '', isbn: '', author: '', reason: '' })
const posting = ref(false)
const list = ref([])
const page = ref(1)
const size = ref(10)
const total = ref(0)

function statusLabel(s) {
  if (s === 'pending') return '待审核'
  if (s === 'approved') return '已通过'
  if (s === 'rejected') return '已驳回'
  return s || '—'
}

async function load() {
  if (!canPost.value) {
    list.value = []
    total.value = 0
    return
  }
  const res = await http.get('/api/book-suggest/mine', {
    params: { page: page.value, size: size.value },
  })
  list.value = res.data?.list || []
  total.value = res.data?.total || 0
}

async function submit() {
  if (!form.title.trim()) {
    ElMessage.warning('请填写书名')
    return
  }
  posting.value = true
  try {
    await http.post('/api/book-suggest', { ...form })
    ElMessage.success(okMsg.value)
    form.title = ''
    form.isbn = ''
    form.author = ''
    form.reason = ''
    page.value = 1
    await load()
  } finally {
    posting.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.hero { margin-bottom: 16px; }
.hero h1 { margin: 0 0 6px; font-size: 22px; }
.hero p { margin: 0; color: var(--portal-muted, #606266); font-size: 14px; }
.card {
  background: var(--el-bg-color);
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 16px;
}
.grid { display: grid; grid-template-columns: 1fr 1fr; gap: 0 16px; }
.sec { margin: 8px 0 12px; font-size: 16px; }
.empty { color: var(--portal-muted, #94a3b8); padding: 12px 0; }
.pager { margin-top: 12px; display: flex; justify-content: flex-end; }
@media (max-width: 640px) {
  .grid { grid-template-columns: 1fr; }
}
</style>
