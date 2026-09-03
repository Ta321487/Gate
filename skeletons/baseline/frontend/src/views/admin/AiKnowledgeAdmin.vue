<template>
  <div class="page">
    <div class="hd">
      <div>
        <h2>{{ pageTitle }}</h2>
        <p class="muted">维护 FAQ / 科普条目；命中后供助手检索，并可作 DeepSeek 上下文。</p>
      </div>
      <el-button type="primary" @click="openEdit()">新增条目</el-button>
    </div>

    <el-row :gutter="12" class="stats">
      <el-col :span="6"><el-statistic title="知识条目" :value="stats.knowledgeCount || 0" /></el-col>
      <el-col :span="6"><el-statistic title="对话消息" :value="stats.messageCount || 0" /></el-col>
      <el-col :span="6"><el-statistic title="反馈数" :value="stats.feedbackCount || 0" /></el-col>
      <el-col :span="6"><el-statistic title="满意率%" :value="stats.satisfiedRate || 0" /></el-col>
    </el-row>

    <div class="toolbar">
      <el-input v-model="category" clearable placeholder="按分类筛选" style="width: 200px" @keyup.enter="load" />
      <el-button @click="load">查询</el-button>
    </div>

    <el-table :data="list" stripe>
      <el-table-column prop="id" label="ID" width="70" />
      <el-table-column prop="category" label="分类" width="100" />
      <el-table-column prop="title" label="标题" min-width="140" />
      <el-table-column prop="keywords" label="关键词" min-width="120" />
      <el-table-column prop="hitCount" label="热度" width="80" />
      <el-table-column label="启用" width="80">
        <template #default="{ row }">{{ row.enabled ? '是' : '否' }}</template>
      </el-table-column>
      <el-table-column label="操作" width="160" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
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

    <el-dialog v-model="visible" :title="form.id ? '编辑知识' : '新增知识'" width="560px">
      <el-form label-width="80px">
        <el-form-item label="分类">
          <el-input v-model="form.category" maxlength="64" />
        </el-form-item>
        <el-form-item label="标题">
          <el-input v-model="form.title" maxlength="128" />
        </el-form-item>
        <el-form-item label="关键词">
          <el-input v-model="form.keywords" placeholder="逗号分隔" maxlength="255" />
        </el-form-item>
        <el-form-item label="内容">
          <el-input v-model="form.content" type="textarea" :rows="6" maxlength="2000" show-word-limit />
        </el-form-item>
        <el-form-item label="启用">
          <el-switch v-model="form.enabled" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="visible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="save">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import http from '../../api/http'
import { schemaLabels } from '../../utils/domainSchema.js'

const labels = computed(() => schemaLabels())
const pageTitle = computed(() => labels.value.aiKnowledgePageTitle || 'AI知识库')

const list = ref([])
const total = ref(0)
const page = ref(1)
const size = ref(10)
const category = ref('')
const stats = ref({})
const visible = ref(false)
const saving = ref(false)
const form = reactive({
  id: null,
  category: '通用',
  title: '',
  content: '',
  keywords: '',
  enabled: true,
})

async function loadStats() {
  const res = await http.get('/api/ai-assistant/stats')
  stats.value = res.data || {}
}

async function load() {
  const res = await http.get('/api/ai-assistant/knowledge', {
    params: { page: page.value, size: size.value, category: category.value || undefined },
  })
  list.value = res.data?.list || []
  total.value = res.data?.total || 0
}

function openEdit(row) {
  if (row) {
    form.id = row.id
    form.category = row.category || '通用'
    form.title = row.title || ''
    form.content = row.content || ''
    form.keywords = row.keywords || ''
    form.enabled = row.enabled !== false
  } else {
    form.id = null
    form.category = '通用'
    form.title = ''
    form.content = ''
    form.keywords = ''
    form.enabled = true
  }
  visible.value = true
}

async function save() {
  if (!form.title.trim() || !form.content.trim()) {
    ElMessage.warning('标题与内容不能为空')
    return
  }
  saving.value = true
  try {
    const payload = {
      category: form.category,
      title: form.title,
      content: form.content,
      keywords: form.keywords,
      enabled: form.enabled,
    }
    if (form.id) await http.put(`/api/ai-assistant/knowledge/${form.id}`, payload)
    else await http.post('/api/ai-assistant/knowledge', payload)
    ElMessage.success('已保存')
    visible.value = false
    await load()
    await loadStats()
  } finally {
    saving.value = false
  }
}

async function remove(row) {
  await ElMessageBox.confirm(`删除「${row.title}」？`, '确认')
  await http.delete(`/api/ai-assistant/knowledge/${row.id}`)
  ElMessage.success('已删除')
  await load()
  await loadStats()
}

onMounted(async () => {
  await loadStats()
  await load()
})
</script>

<style scoped>
.page { padding: 4px 2px 24px; }
.hd {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 14px;
}
.hd h2 { margin: 0 0 6px; font-size: 20px; }
.muted { margin: 0; color: #64748b; font-size: 13px; }
.stats { margin-bottom: 14px; }
.toolbar { display: flex; gap: 8px; margin-bottom: 12px; }
.pager { margin-top: 14px; display: flex; justify-content: flex-end; }
</style>
