<template>
  <div>
    <div class="toolbar">
      <h2>试卷管理</h2>
      <div class="actions">
        <el-button v-if="scoreImportOn" @click="downloadScoreTemplate">{{ scoreTemplateLabel }}</el-button>
        <el-button v-if="scoreImportOn" type="success" @click="scoreImportVisible = true">{{ scoreImportLabel }}</el-button>
        <el-button type="primary" @click="openCreate">新增试卷</el-button>
      </div>
    </div>
    <p v-if="scoreImportOn && scoreImportHint" class="hint top-hint">{{ scoreImportHint }}</p>
    <el-table :data="list" stripe>
      <el-table-column prop="id" label="ID" width="70" />
      <el-table-column prop="title" label="标题" />
      <el-table-column prop="status" label="状态" width="100" />
      <el-table-column prop="durationMin" label="限时(分)" width="100" />
      <el-table-column prop="maxAttempts" label="次数上限" width="100" />
      <el-table-column v-if="passScoreOn" prop="passScore" :label="passScoreLabel" width="100" />
      <el-table-column v-if="difficultyOn" prop="difficulty" :label="difficultyLabel" width="100" />
      <el-table-column label="操作" width="280">
        <template #default="{ row }">
          <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
          <el-button link @click="openQuestions(row)">组卷</el-button>
          <el-button v-if="drawOn" link @click="openDraw(row)">{{ drawLabel }}</el-button>
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

    <el-dialog v-model="visible" :title="form.id ? '编辑试卷' : '新增试卷'" width="560px">
      <el-form label-width="130px">
        <el-form-item label="标题">
          <el-input v-model="form.title" />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="form.status" style="width: 100%">
            <el-option label="草稿" value="draft" />
            <el-option label="已发布" value="published" />
          </el-select>
        </el-form-item>
        <el-form-item label="限时(分)">
          <el-input-number v-model="form.durationMin" :min="0" :max="300" />
        </el-form-item>
        <el-form-item label="次数上限">
          <el-input-number v-model="form.maxAttempts" :min="0" :max="20" />
          <span class="hint">0 表示不限</span>
        </el-form-item>
        <el-form-item label="准入必考">
          <el-switch v-model="form.gateTicket" />
          <span class="hint">开启后申请单据前须及格通过本卷</span>
        </el-form-item>
        <el-form-item v-if="passScoreOn || form.gateTicket" :label="passScoreLabel">
          <el-input-number v-model="form.passScore" :min="1" :max="100" />
          <span v-if="passScoreHint" class="hint">{{ passScoreHint }}</span>
        </el-form-item>
        <el-form-item v-if="shuffleOn" :label="shuffleQuestionsLabel">
          <el-switch v-model="form.shuffleQuestions" />
        </el-form-item>
        <el-form-item v-if="shuffleOn" :label="shuffleOptionsLabel">
          <el-switch v-model="form.shuffleOptions" />
          <span v-if="shuffleHint" class="hint">{{ shuffleHint }}</span>
        </el-form-item>
        <el-form-item v-if="explainOn" :label="explainAfterLabel">
          <el-switch v-model="form.explainAfterScore" />
          <span v-if="explainAfterHint" class="hint">{{ explainAfterHint }}</span>
        </el-form-item>
        <el-form-item v-if="partialOn" :label="partialMultiLabel">
          <el-switch v-model="form.partialMulti" />
          <span v-if="partialMultiHint" class="hint">{{ partialMultiHint }}</span>
        </el-form-item>
        <el-form-item v-if="lockOn" :label="lockAfterLabel">
          <el-switch v-model="form.lockAfterSubmit" />
          <span v-if="lockAfterHint" class="hint">{{ lockAfterHint }}</span>
        </el-form-item>
        <el-form-item v-if="lateOn" :label="openAtLabel">
          <el-date-picker
            v-model="form.openAt"
            type="datetime"
            value-format="YYYY-MM-DD HH:mm:ss"
            style="width: 100%"
            clearable
          />
        </el-form-item>
        <el-form-item v-if="lateOn" :label="lateEnterLabel">
          <el-input-number v-model="form.lateEnterMin" :min="0" :max="240" />
          <span v-if="lateEnterHint" class="hint">{{ lateEnterHint }}</span>
        </el-form-item>
        <el-form-item v-if="entryOn" :label="entryCodeLabel">
          <el-input v-model="form.entryCode" :placeholder="entryCodeHint" maxlength="64" />
        </el-form-item>
        <el-form-item v-if="difficultyOn" :label="difficultyLabel">
          <el-input v-model="form.difficulty" :placeholder="difficultyPlaceholder" maxlength="32" />
          <span v-if="difficultyHint" class="hint">{{ difficultyHint }}</span>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="visible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="save">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="qVisible" title="组卷：勾选题目" width="640px">
      <el-checkbox-group v-model="selectedQ">
        <div v-for="q in allQuestions" :key="q.id" class="qrow">
          <el-checkbox :label="q.id">#{{ q.id }} [{{ q.type }}] {{ q.stem }}</el-checkbox>
        </div>
      </el-checkbox-group>
      <template #footer>
        <el-button @click="qVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveQuestions">保存组卷</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="drawVisible" :title="drawLabel" width="420px">
      <p v-if="drawHint" class="hint">{{ drawHint }}</p>
      <el-form label-width="100px">
        <el-form-item :label="drawCountLabel">
          <el-input-number v-model="drawCount" :min="1" :max="100" />
        </el-form-item>
        <el-form-item label="题型筛选">
          <el-select v-model="drawType" clearable style="width: 100%" placeholder="全部题型">
            <el-option label="单选" value="single" />
            <el-option label="多选" value="multi" />
            <el-option label="判断" value="judge" />
            <el-option label="主观" value="subjective" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="drawVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="doDraw">确认抽取</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="scoreImportVisible" :title="scoreImportLabel" width="560px">
      <p v-if="scoreImportHint" class="hint">{{ scoreImportHint }}</p>
      <el-input v-model="scoreImportText" type="textarea" :rows="10" placeholder="粘贴 CSV 内容" />
      <template #footer>
        <el-button @click="scoreImportVisible = false">取消</el-button>
        <el-button type="primary" :loading="importing" @click="doScoreImport">确认导入</el-button>
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
const passScoreOn = computed(() => !!thicken.value.examPassScore)
const passScoreLabel = computed(() => labels.value.examPassScoreLabel || '及格线(%)')
const passScoreHint = computed(() => labels.value.examPassScoreHint || '')
const shuffleOn = computed(() => !!thicken.value.examShuffle)
const shuffleQuestionsLabel = computed(() => labels.value.examShuffleQuestionsLabel || '题目乱序')
const shuffleOptionsLabel = computed(() => labels.value.examShuffleOptionsLabel || '选项乱序')
const shuffleHint = computed(() => labels.value.examShuffleHint || '')
const explainOn = computed(() => !!thicken.value.examExplainAfterScore)
const explainAfterLabel = computed(() => labels.value.examExplainAfterScoreLabel || '成绩公布后显示解析')
const explainAfterHint = computed(() => labels.value.examExplainAfterScoreHint || '')
const partialOn = computed(() => !!thicken.value.examPartialMulti)
const partialMultiLabel = computed(() => labels.value.examPartialMultiLabel || '多选部分得分')
const partialMultiHint = computed(() => labels.value.examPartialMultiHint || '')
const lockOn = computed(() => !!thicken.value.examLockAfterSubmit)
const lockAfterLabel = computed(() => labels.value.examLockAfterSubmitLabel || '交卷后不可再考')
const lockAfterHint = computed(() => labels.value.examLockAfterSubmitHint || '')
const lateOn = computed(() => !!thicken.value.examLateEnter)
const openAtLabel = computed(() => labels.value.examOpenAtLabel || '开考时间')
const lateEnterLabel = computed(() => labels.value.examLateEnterMinLabel || '迟到限时(分)')
const lateEnterHint = computed(() => labels.value.examLateEnterHint || '')
const entryOn = computed(() => !!thicken.value.examEntryCode)
const entryCodeLabel = computed(() => labels.value.examEntryCodeLabel || '入场口令')
const entryCodeHint = computed(() => labels.value.examEntryCodeHint || '')
const difficultyOn = computed(() => !!thicken.value.examDifficulty)
const difficultyLabel = computed(() => labels.value.examDifficultyLabel || '难度')
const difficultyPlaceholder = computed(() => labels.value.examDifficultyPlaceholder || '')
const difficultyHint = computed(() => labels.value.examDifficultyHint || '')
const drawOn = computed(() => !!thicken.value.examRandomDraw)
const drawLabel = computed(() => labels.value.examRandomDrawLabel || '随机抽题')
const drawHint = computed(() => labels.value.examRandomDrawHint || '')
const drawCountLabel = computed(() => labels.value.examRandomDrawCountLabel || '抽取数量')
const drawDone = computed(() => labels.value.examRandomDrawDone || '已抽入试卷')
const scoreImportOn = computed(() => !!thicken.value.examScoreImport)
const scoreImportLabel = computed(() => labels.value.examScoreImportLabel || '导入成绩')
const scoreImportHint = computed(() => labels.value.examScoreImportHint || '')
const scoreTemplateLabel = computed(() => labels.value.examScoreImportTemplateLabel || '下载成绩模板')
const scoreImportDone = computed(() => labels.value.examScoreImportDone || '成绩已导入')

const list = ref([])
const page = ref(1)
const total = ref(0)
const visible = ref(false)
const qVisible = ref(false)
const drawVisible = ref(false)
const scoreImportVisible = ref(false)
const saving = ref(false)
const importing = ref(false)
const emptyForm = () => ({
  id: null,
  title: '',
  status: 'draft',
  durationMin: 60,
  maxAttempts: 0,
  gateTicket: false,
  passScore: 60,
  shuffleQuestions: false,
  shuffleOptions: false,
  explainAfterScore: true,
  partialMulti: false,
  lockAfterSubmit: false,
  openAt: null,
  lateEnterMin: 0,
  entryCode: '',
  difficulty: '',
})
const form = reactive(emptyForm())
const currentPaperId = ref(null)
const allQuestions = ref([])
const selectedQ = ref([])
const drawCount = ref(10)
const drawType = ref('')
const scoreImportText = ref('')

async function load() {
  const res = await http.get('/api/exam/admin/papers', { params: { page: page.value, size: 10 } })
  const data = res.data?.data || res.data || {}
  list.value = data.list || []
  total.value = data.total || 0
}

function openCreate() {
  Object.assign(form, emptyForm())
  visible.value = true
}

function openEdit(row) {
  Object.assign(form, emptyForm(), {
    id: row.id,
    title: row.title,
    status: row.status,
    durationMin: row.durationMin || 0,
    maxAttempts: row.maxAttempts || 0,
    gateTicket: !!row.gateTicket,
    passScore: row.passScore || 60,
    shuffleQuestions: !!row.shuffleQuestions,
    shuffleOptions: !!row.shuffleOptions,
    explainAfterScore: row.explainAfterScore !== false,
    partialMulti: !!row.partialMulti,
    lockAfterSubmit: !!row.lockAfterSubmit,
    openAt: row.openAt || null,
    lateEnterMin: row.lateEnterMin || 0,
    entryCode: row.entryCode || '',
    difficulty: row.difficulty || '',
  })
  visible.value = true
}

async function save() {
  saving.value = true
  try {
    if (form.id) await http.put(`/api/exam/admin/papers/${form.id}`, { ...form })
    else await http.post('/api/exam/admin/papers', { ...form })
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
    await http.delete(`/api/exam/admin/papers/${id}`)
    ElMessage.success('已删除')
    await load()
  } catch (e) {
    ElMessage.error(e?.response?.data?.message || e.message || '删除失败')
  }
}

async function openQuestions(row) {
  currentPaperId.value = row.id
  const [allRes, paperRes] = await Promise.all([
    http.get('/api/exam/admin/questions', { params: { page: 1, size: 200 } }),
    http.get(`/api/exam/admin/papers/${row.id}/questions`),
  ])
  const allData = allRes.data?.data || allRes.data || {}
  allQuestions.value = allData.list || allData || []
  const pq = paperRes.data?.data || paperRes.data || []
  selectedQ.value = (Array.isArray(pq) ? pq : []).map((q) => q.id || q.questionId)
  qVisible.value = true
}

async function saveQuestions() {
  saving.value = true
  try {
    const body = selectedQ.value.map((id, i) => ({ questionId: id, sortNo: i + 1 }))
    await http.put(`/api/exam/admin/papers/${currentPaperId.value}/questions`, body)
    qVisible.value = false
    ElMessage.success('组卷已保存')
  } catch (e) {
    ElMessage.error(e?.response?.data?.message || e.message || '组卷失败')
  } finally {
    saving.value = false
  }
}

function openDraw(row) {
  currentPaperId.value = row.id
  drawCount.value = 10
  drawType.value = ''
  drawVisible.value = true
}

async function doDraw() {
  saving.value = true
  try {
    const body = { count: drawCount.value }
    if (drawType.value) body.type = drawType.value
    const res = await http.post(`/api/exam/admin/papers/${currentPaperId.value}/random-draw`, body)
    const data = res.data?.data || res.data || {}
    ElMessage.success(`${drawDone.value}：${data.added || 0} 题`)
    drawVisible.value = false
  } catch (e) {
    ElMessage.error(e?.response?.data?.message || e.message || '抽题失败')
  } finally {
    saving.value = false
  }
}

async function downloadScoreTemplate() {
  try {
    const res = await http.get('/api/exam/admin/scores/import-template', { responseType: 'blob' })
    const blob = new Blob([res.data], { type: 'text/csv;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'exam_scores_template.csv'
    a.click()
    URL.revokeObjectURL(url)
  } catch (e) {
    ElMessage.error(e?.response?.data?.message || e.message || '下载失败')
  }
}

async function doScoreImport() {
  importing.value = true
  try {
    const res = await http.post('/api/exam/admin/scores/import', { csv: scoreImportText.value })
    const data = res.data?.data || res.data || {}
    ElMessage.success(`${scoreImportDone.value}：成功 ${data.imported || 0}，跳过 ${data.skipped || 0}`)
    scoreImportVisible.value = false
    scoreImportText.value = ''
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
.toolbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; }
.actions { display: flex; gap: 0.5rem; flex-wrap: wrap; }
.pager { margin-top: 1rem; }
.hint { margin-left: 0.5rem; color: var(--el-text-color-secondary); font-size: 12px; }
.top-hint { margin: 0 0 0.75rem; margin-left: 0; }
.qrow { margin-bottom: 0.35rem; }
</style>
