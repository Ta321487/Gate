<template>
  <div>
    <div class="toolbar">
      <h2>问卷题目</h2>
      <el-select v-model="formId" placeholder="选择问卷项目" style="width: 240px" @change="load">
        <el-option v-for="f in forms" :key="f.id" :label="f.title" :value="f.id" />
      </el-select>
      <el-button type="primary" :disabled="!formId" @click="openCreate">新增题目</el-button>
    </div>
    <el-table :data="list" stripe>
      <el-table-column prop="sortNo" label="#" width="60" />
      <el-table-column prop="type" label="题型" width="90" />
      <el-table-column prop="stem" label="题干" />
      <el-table-column label="操作" width="100">
        <template #default="{ row }">
          <el-button link type="danger" @click="remove(row.id)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="visible" title="新增题目" width="520px">
      <el-form label-width="90px">
        <el-form-item label="题型">
          <el-select v-model="draft.type" style="width: 100%">
            <el-option label="单选" value="single" />
            <el-option label="多选" value="multi" />
            <el-option label="填空" value="text" />
          </el-select>
        </el-form-item>
        <el-form-item label="题干"><el-input v-model="draft.stem" type="textarea" :rows="2" /></el-form-item>
        <el-form-item label="选项JSON">
          <el-input v-model="draft.optionsJson" type="textarea" :rows="2" placeholder='["选项A","选项B"]' />
        </el-form-item>
        <el-form-item label="排序"><el-input-number v-model="draft.sortNo" :min="0" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="visible = false">取消</el-button>
        <el-button type="primary" @click="save">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import http from '../../api/http'

const forms = ref([])
const formId = ref(null)
const list = ref([])
const visible = ref(false)
const draft = reactive({
  type: 'single',
  stem: '',
  optionsJson: '["选项A","选项B","选项C"]',
  sortNo: 1,
})

async function loadForms() {
  // 管理端复用开放列表接口；档案页也可维护 survey_form
  const res = await http.get('/api/survey/forms')
  forms.value = res.data?.data || res.data || []
  if (forms.value.length && !formId.value) {
    formId.value = forms.value[0].id
    await load()
  }
}

async function load() {
  if (!formId.value) return
  const res = await http.get(`/api/survey/admin/forms/${formId.value}/questions`, {
    params: { page: 1, size: 100 },
  })
  list.value = (res.data?.data || res.data || {}).list || []
}

function openCreate() {
  Object.assign(draft, {
    type: 'single',
    stem: '',
    optionsJson: '["选项A","选项B","选项C"]',
    sortNo: (list.value.length || 0) + 1,
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
</style>
