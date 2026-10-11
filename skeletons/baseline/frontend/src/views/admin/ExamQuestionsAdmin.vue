<template>
  <div>
    <div class="toolbar">
      <h2>题库管理</h2>
      <div class="actions">
        <el-button v-if="importOn" @click="downloadTemplate">{{ templateLabel }}</el-button>
        <el-button v-if="importOn" type="success" @click="importVisible = true">{{ importLabel }}</el-button>
        <el-button type="primary" @click="openCreate">新增题目</el-button>
      </div>
    </div>
    <p v-if="importOn && importHint" class="hint">{{ importHint }}</p>
    <el-table :data="list" stripe>
      <el-table-column prop="id" label="ID" width="70" />
      <el-table-column prop="type" label="题型" width="90" />
      <el-table-column prop="stem" label="题干" show-overflow-tooltip />
      <el-table-column prop="answerKey" label="答案" width="120" />
      <el-table-column prop="score" label="分值" width="70" />
      <el-table-column label="操作" width="160">
        <template #default="{ row }">
          <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
          <el-button link type="danger" @click="remove(row.id)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
    <el-pagination
      class="pager"
      v-model:current-page="page"
      layout="total, sizes, prev, pager, next"
      :page-sizes="[10, 20, 50]"
      :total="total"
      @current-change="load"
      @size-change="load"
    />

    <el-dialog v-model="visible" :title="form.id ? '编辑题目' : '新增题目'" width="560px">
      <el-form label-width="90px">
        <el-form-item label="题型">
          <el-select v-model="form.type" style="width: 100%">
            <el-option label="单选" value="single" />
            <el-option label="多选" value="multi" />
            <el-option label="判断" value="judge" />
            <el-option label="主观" value="subjective" />
          </el-select>
        </el-form-item>
        <el-form-item label="题干">
          <el-input v-model="form.stem" type="textarea" :rows="3" />
        </el-form-item>
        <el-form-item label="选项JSON">
          <el-input v-model="form.optionsJson" type="textarea" :rows="2" placeholder='["A选项","B选项"]' />
        </el-form-item>
        <el-form-item label="答案">
          <el-input v-model="form.answerKey" placeholder="单选如 A；多选如 A,B；主观填参考答案，不参与自动判分" />
        </el-form-item>
        <el-form-item label="分值">
          <el-input-number v-model="form.score" :min="1" :max="100" />
        </el-form-item>
        <el-form-item label="解析">
          <el-input v-model="form.explainText" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item v-if="rubricOn && form.type === 'subjective'" :label="rubricLabel">
          <el-input
            v-model="form.markRubric"
            type="textarea"
            :rows="2"
            :placeholder="rubricPlaceholder"
          />
          <span v-if="rubricHint" class="hint">{{ rubricHint }}</span>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="visible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="save">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="importVisible" :title="importLabel" width="560px">
      <p v-if="importHint" class="hint">{{ importHint }}</p>
      <el-input v-model="importText" type="textarea" :rows="10" placeholder="粘贴 CSV 内容" />
      <template #footer>
        <el-button @click="importVisible = false">取消</el-button>
        <el-button type="primary" :loading="importing" @click="doImport">确认导入</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import http from '../../api/http'
import { getSchema } from '../../utils/domainSchema'

const labels = computed(() => getSchema()?.labels || {})
const thicken = computed(() => getSchema()?.interactThicken || {})
const importOn = computed(() => !!thicken.value.examQuestionImport)
const importLabel = computed(() => labels.value.examQuestionImportLabel || '导入题目')
const importHint = computed(() => labels.value.examQuestionImportHint || '')
const templateLabel = computed(() => labels.value.examQuestionImportTemplateLabel || '下载导入模板')
const importDone = computed(() => labels.value.examQuestionImportDone || '题目已导入')
const rubricOn = computed(() => !!thicken.value.examMarkRubric)
const rubricLabel = computed(() => labels.value.examMarkRubricLabel || '评分细则')
const rubricHint = computed(() => labels.value.examMarkRubricHint || '')
const rubricPlaceholder = computed(() => labels.value.examMarkRubricPlaceholder || '')

const list = ref([])
const page = ref(1)
const total = ref(0)
const visible = ref(false)
const saving = ref(false)
const importVisible = ref(false)
const importing = ref(false)
const importText = ref('')
const form = reactive({
  id: null,
  type: 'single',
  stem: '',
  optionsJson: '[]',
  answerKey: '',
  score: 5,
  explainText: '',
  markRubric: '',
})

async function load() {
  const res = await http.get('/api/exam/admin/questions', { params: { page: page.value, size: 10 } })
  const data = res.data?.data || res.data || {}
  list.value = data.list || []
  total.value = data.total || 0
}

function openCreate() {
  Object.assign(form, {
    id: null,
    type: 'single',
    stem: '',
    optionsJson: '["选项A","选项B","选项C","选项D"]',
    answerKey: 'A',
    score: 5,
    explainText: '',
    markRubric: '',
  })
  visible.value = true
}

function openEdit(row) {
  Object.assign(form, {
    id: row.id,
    type: row.type,
    stem: row.stem,
    optionsJson: row.optionsJson || '[]',
    answerKey: row.answerKey || '',
    score: row.score || 5,
    explainText: row.explainText || '',
    markRubric: row.markRubric || '',
  })
  visible.value = true
}

async function save() {
  saving.value = true
  try {
    const body = { ...form }
    if (form.id) await http.put(`/api/exam/admin/questions/${form.id}`, body)
    else await http.post('/api/exam/admin/questions', body)
    visible.value = false
    ElMessage.success('已保存')
    await load()
  } catch (e) {
    ElMessage.error(e?.response?.data?.message || e.message || '保存失败')
  } finally {
    saving.value = false
  }
}

async function remove(id) {
  try {
    await http.delete(`/api/exam/admin/questions/${id}`)
    ElMessage.success('已删除')
    await load()
  } catch (e) {
    ElMessage.error(e?.response?.data?.message || e.message || '删除失败')
  }
}

async function downloadTemplate() {
  try {
    const res = await http.get('/api/exam/admin/questions/import-template', { responseType: 'blob' })
    const blob = new Blob([res.data], { type: 'text/csv;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'exam_questions_template.csv'
    a.click()
    URL.revokeObjectURL(url)
  } catch (e) {
    ElMessage.error(e?.response?.data?.message || e.message || '下载失败')
  }
}

async function doImport() {
  importing.value = true
  try {
    const res = await http.post('/api/exam/admin/questions/import', { csv: importText.value })
    const data = res.data?.data || res.data || {}
    ElMessage.success(`${importDone.value}：成功 ${data.imported || 0}，跳过 ${data.skipped || 0}`)
    importVisible.value = false
    importText.value = ''
    await load()
  } catch (e) {
    ElMessage.error(e?.response?.data?.message || e.message || '导入失败')
  } finally {
    importing.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.toolbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem; }
.actions { display: flex; gap: 0.5rem; flex-wrap: wrap; }
.pager { margin-top: 1rem; }
.hint { color: var(--el-text-color-secondary); font-size: 12px; margin: 0 0 0.75rem; }
</style>
