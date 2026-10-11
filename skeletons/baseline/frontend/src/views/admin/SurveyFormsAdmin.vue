<template>
  <div>
    <div class="toolbar">
      <h2>问卷题目</h2>
      <el-select v-model="formId" placeholder="选择问卷项目" style="width: 240px" @change="onFormChange">
        <el-option v-for="f in forms" :key="f.id" :label="f.title" :value="f.id" />
      </el-select>
      <el-button type="primary" :disabled="!formId" @click="openCreate">新增题目</el-button>
    </div>

    <div v-if="formId && settingsOn" class="card settings">
      <h3>问卷设置</h3>
      <el-form label-width="140px" class="settings-form">
        <el-form-item v-if="thicken.surveySchedule" :label="labels.surveyOpenAtLabel || '开放时间'">
          <el-date-picker v-model="settings.openAt" type="datetime" value-format="YYYY-MM-DD HH:mm:ss" />
        </el-form-item>
        <el-form-item v-if="thicken.surveySchedule" :label="labels.surveyCloseAtLabel || '截止时间'">
          <el-date-picker v-model="settings.closeAt" type="datetime" value-format="YYYY-MM-DD HH:mm:ss" />
        </el-form-item>
        <el-form-item v-if="thicken.surveyAnonymous" :label="labels.surveyAnonymousLabel || '匿名填写'">
          <el-switch v-model="settings.anonymous" />
        </el-form-item>
        <el-form-item v-if="thicken.surveyOnceOnly" :label="labels.surveyOnceOnlyLabel || '每人限填一次'">
          <el-switch v-model="settings.onceOnly" />
        </el-form-item>
        <el-form-item v-if="thicken.surveyTargetOrg" :label="labels.surveyTargetOrgLabel || '投放组织'">
          <el-input v-model="settings.targetOrg" :placeholder="labels.surveyTargetOrgHint || ''" />
        </el-form-item>
        <el-form-item v-if="thicken.surveyCloseRemind" :label="labels.surveyRemindHoursLabel || '截止前提醒(小时)'">
          <el-input-number v-model="settings.remindBeforeHours" :min="0" />
        </el-form-item>
        <el-form-item v-if="thicken.surveyRecycleCard" :label="labels.surveyTargetCountLabel || '回收目标份数'">
          <el-input-number v-model="settings.targetCount" :min="0" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="savingSettings" @click="saveSettings">保存设置</el-button>
        </el-form-item>
      </el-form>
      <p v-if="thicken.surveySchedule" class="muted">{{ labels.surveyScheduleHint }}</p>
    </div>

    <el-table :data="list" stripe>
      <el-table-column prop="sortNo" label="#" width="60" />
      <el-table-column prop="type" label="题型" width="90" />
      <el-table-column prop="stem" label="题干" />
      <el-table-column label="必答" width="70">
        <template #default="{ row }">{{ row.required ? '是' : '否' }}</template>
      </el-table-column>
      <el-table-column label="操作" width="100">
        <template #default="{ row }">
          <el-button link type="danger" @click="remove(row.id)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="visible" title="新增题目" width="560px">
      <el-form label-width="110px">
        <el-form-item label="题型">
          <el-select v-model="draft.type" style="width: 100%">
            <el-option label="单选" value="single" />
            <el-option label="多选" value="multi" />
            <el-option label="填空" value="text" />
            <el-option v-if="thicken.surveyMatrix" :label="labels.surveyMatrixLabel || '矩阵题'" value="matrix" />
          </el-select>
        </el-form-item>
        <el-form-item label="题干"><el-input v-model="draft.stem" type="textarea" :rows="2" /></el-form-item>
        <el-form-item label="选项JSON">
          <el-input v-model="draft.optionsJson" type="textarea" :rows="2" placeholder='["选项A","选项B"]' />
        </el-form-item>
        <el-form-item v-if="draft.type === 'matrix'" :label="labels.surveyMatrixRowsLabel || '行标签 JSON'">
          <el-input v-model="draft.matrixRows" type="textarea" :rows="2" placeholder='["行1","行2"]' />
        </el-form-item>
        <el-form-item label="排序"><el-input-number v-model="draft.sortNo" :min="0" /></el-form-item>
        <el-form-item v-if="thicken.surveyRequired" :label="labels.surveyRequiredLabel || '必答'">
          <el-switch v-model="draft.required" />
        </el-form-item>
        <el-form-item v-if="thicken.surveySkip" :label="labels.surveySkipWhenLabel || '选中则跳题'">
          <el-input v-model="draft.skipWhenLabel" placeholder="如 A" style="width: 80px" />
        </el-form-item>
        <el-form-item v-if="thicken.surveySkip" :label="labels.surveySkipToSortLabel || '跳至题号'">
          <el-input-number v-model="draft.skipToSort" />
        </el-form-item>
        <el-form-item v-if="thicken.surveyShowIf" :label="labels.surveyShowWhenQidLabel || '依赖题目ID'">
          <el-input-number v-model="draft.showWhenQid" :min="0" />
        </el-form-item>
        <el-form-item v-if="thicken.surveyShowIf" :label="labels.surveyShowWhenLabel || '依赖选项'">
          <el-input v-model="draft.showWhenLabel" placeholder="如 A" style="width: 80px" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="visible = false">取消</el-button>
        <el-button type="primary" @click="save">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import http from '../../api/http'
import { getSchema } from '../../utils/domainSchema.js'

const schema = computed(() => getSchema() || {})
const labels = computed(() => schema.value.labels || {})
const thicken = computed(() => schema.value.interactThicken || {})
const settingsOn = computed(
  () =>
    thicken.value.surveySchedule
    || thicken.value.surveyAnonymous
    || thicken.value.surveyOnceOnly
    || thicken.value.surveyTargetOrg
    || thicken.value.surveyCloseRemind
    || thicken.value.surveyRecycleCard,
)

const forms = ref([])
const formId = ref(null)
const list = ref([])
const visible = ref(false)
const savingSettings = ref(false)
const settings = reactive({
  openAt: null,
  closeAt: null,
  anonymous: false,
  onceOnly: true,
  targetOrg: '',
  remindBeforeHours: 0,
  targetCount: 0,
})
const draft = reactive({
  type: 'single',
  stem: '',
  optionsJson: '["选项A","选项B","选项C"]',
  matrixRows: '["行1","行2"]',
  sortNo: 1,
  required: true,
  skipWhenLabel: '',
  skipToSort: null,
  showWhenQid: null,
  showWhenLabel: '',
})

async function loadForms() {
  const res = await http.get('/api/survey/admin/forms')
  forms.value = res.data?.data || res.data || []
  if (forms.value.length && !formId.value) {
    formId.value = forms.value[0].id
    await onFormChange()
  }
}

function applySettings(f) {
  if (!f) return
  settings.openAt = f.openAt || null
  settings.closeAt = f.closeAt || null
  settings.anonymous = !!f.anonymous
  settings.onceOnly = f.onceOnly !== false
  settings.targetOrg = f.targetOrg || ''
  settings.remindBeforeHours = Number(f.remindBeforeHours || 0)
  settings.targetCount = Number(f.targetCount || 0)
}

async function onFormChange() {
  await load()
  const f = forms.value.find((x) => x.id === formId.value)
  applySettings(f)
}

async function load() {
  if (!formId.value) return
  const res = await http.get(`/api/survey/admin/forms/${formId.value}/questions`, {
    params: { page: 1, size: 100 },
  })
  list.value = (res.data?.data || res.data || {}).list || []
}

async function saveSettings() {
  savingSettings.value = true
  try {
    const res = await http.patch(`/api/survey/admin/forms/${formId.value}`, { ...settings })
    const updated = res.data?.data || res.data
    const idx = forms.value.findIndex((x) => x.id === formId.value)
    if (idx >= 0 && updated) forms.value[idx] = { ...forms.value[idx], ...updated }
    ElMessage.success('设置已保存')
  } catch (e) {
    ElMessage.error(e?.response?.data?.message || e.message || '保存失败')
  } finally {
    savingSettings.value = false
  }
}

function openCreate() {
  Object.assign(draft, {
    type: 'single',
    stem: '',
    optionsJson: '["选项A","选项B","选项C"]',
    matrixRows: '["行1","行2"]',
    sortNo: (list.value.length || 0) + 1,
    required: true,
    skipWhenLabel: '',
    skipToSort: null,
    showWhenQid: null,
    showWhenLabel: '',
  })
  visible.value = true
}

async function save() {
  try {
    await http.post('/api/survey/admin/questions', { ...draft, formId: formId.value })
    visible.value = false
    ElMessage.success('已保存')
    await load()
  } catch (e) {
    ElMessage.error(e?.response?.data?.message || e.message || '保存失败')
  }
}

async function remove(id) {
  await http.delete(`/api/survey/admin/questions/${id}`)
  ElMessage.success('已删除')
  await load()
}

onMounted(loadForms)
</script>

<style scoped>
.toolbar { display: flex; gap: 0.75rem; align-items: center; margin-bottom: 1rem; flex-wrap: wrap; }
.settings { padding: 1rem; margin-bottom: 1rem; }
.settings-form { max-width: 560px; }
.muted { color: var(--el-text-color-secondary); font-size: 0.9rem; }
</style>
