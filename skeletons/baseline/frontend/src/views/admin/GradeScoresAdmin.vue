<template>
  <div>
    <div class="toolbar">
      <h2>成绩登记</h2>
      <div>
        <el-button @click="load">刷新</el-button>
        <el-button :disabled="!list.length" @click="exportCsv">导出 CSV</el-button>
      </div>
    </div>
    <el-form :inline="true" class="filters">
      <el-form-item label="学期">
        <el-select v-model="filter.termId" clearable placeholder="全部" style="width: 160px" @change="load">
          <el-option v-for="t in terms" :key="t.id" :label="t.name" :value="t.id" />
        </el-select>
      </el-form-item>
      <el-form-item label="课程">
        <el-select v-model="filter.courseId" clearable placeholder="全部" style="width: 180px" @change="load">
          <el-option v-for="c in courses" :key="c.id" :label="c.title" :value="c.id" />
        </el-select>
      </el-form-item>
    </el-form>
    <el-table :data="list" stripe>
      <el-table-column prop="termName" label="学期" width="140" />
      <el-table-column prop="courseTitle" label="课程" />
      <el-table-column prop="username" label="学生账号" width="140" />
      <el-table-column prop="score" label="分数" width="90" />
      <el-table-column prop="rankNo" label="课内名次" width="100" />
      <el-table-column label="操作" width="90">
        <template #default="{ row }">
          <el-button link type="danger" @click="remove(row.id)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
    <p v-if="!list.length" class="empty">当前筛选下没有成绩。</p>

    <h3>录入或更正</h3>
    <el-form label-width="90px" class="form">
      <el-form-item label="学生账号">
        <el-input v-model="form.username" placeholder="登录账号，如 user" />
      </el-form-item>
      <el-form-item label="学期">
        <el-select v-model="form.termId" style="width: 100%">
          <el-option v-for="t in terms" :key="t.id" :label="t.name" :value="t.id" />
        </el-select>
      </el-form-item>
      <el-form-item label="课程">
        <el-select v-model="form.courseId" style="width: 100%">
          <el-option v-for="c in courses" :key="c.id" :label="c.title" :value="c.id" />
        </el-select>
      </el-form-item>
      <el-form-item label="分数">
        <el-input-number v-model="form.score" :min="0" :max="100" :precision="2" />
      </el-form-item>
      <el-form-item>
        <el-button type="primary" :loading="saving" @click="save">保存</el-button>
      </el-form-item>
    </el-form>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import http from '../../api/http'

const terms = ref([])
const courses = ref([])
const list = ref([])
const saving = ref(false)
const filter = reactive({ termId: null, courseId: null })
const form = reactive({ username: '', termId: null, courseId: null, score: 60 })

function unwrap(res) {
  return res.data?.data ?? res.data
}

async function loadMeta() {
  const res = await http.get('/api/grade-scores/meta')
  const data = unwrap(res) || {}
  terms.value = data.terms || []
  courses.value = data.courses || []
  if (!form.termId && terms.value.length) form.termId = terms.value[0].id
  if (!form.courseId && courses.value.length) form.courseId = courses.value[0].id
}

async function load() {
  const res = await http.get('/api/grade-scores/admin', {
    params: {
      termId: filter.termId || undefined,
      courseId: filter.courseId || undefined,
    },
  })
  list.value = unwrap(res) || []
}

async function save() {
  saving.value = true
  try {
    await http.post('/api/grade-scores/admin', { ...form })
    ElMessage.success('已保存')
    await load()
  } catch (e) {
    ElMessage.error(e?.response?.data?.message || e.message || '保存失败')
  } finally {
    saving.value = false
  }
}

async function remove(id) {
  await http.delete(`/api/grade-scores/admin/${id}`)
  ElMessage.success('已删除')
  load()
}

function csvCell(v) {
  const s = v == null ? '' : String(v)
  if (/[",\n]/.test(s)) return `"${s.replace(/"/g, '""')}"`
  return s
}

function exportCsv() {
  if (!list.value.length) {
    ElMessage.warning('当前无数据可导出')
    return
  }
  const header = ['学期', '课程', '学生账号', '分数', '课内名次']
  const lines = [header.join(',')]
  for (const row of list.value) {
    lines.push([row.termName, row.courseTitle, row.username, row.score, row.rankNo].map(csvCell).join(','))
  }
  const blob = new Blob(['\uFEFF' + lines.join('\n')], { type: 'text/csv;charset=utf-8' })
  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = '成绩排名.csv'
  a.click()
  URL.revokeObjectURL(a.href)
  ElMessage.success(`已导出 ${list.value.length} 条（UTF-8，可用 Excel 直接打开）`)
}

onMounted(async () => {
  await loadMeta()
  await load()
})
</script>

<style scoped>
.toolbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.75rem; }
.toolbar h2 { margin: 0; }
.filters { margin-bottom: 0.5rem; }
.form { max-width: 420px; margin-top: 0.5rem; }
.empty { color: var(--el-text-color-secondary); }
h3 { margin: 1.25rem 0 0.5rem; font-size: 1rem; }
</style>
