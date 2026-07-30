<template>
  <div>
    <div class="toolbar">
      <h2>试卷管理</h2>
      <el-button type="primary" @click="openCreate">新增试卷</el-button>
    </div>
    <el-table :data="list" stripe>
      <el-table-column prop="id" label="ID" width="70" />
      <el-table-column prop="title" label="标题" />
      <el-table-column prop="status" label="状态" width="100" />
      <el-table-column prop="durationMin" label="限时(分)" width="100" />
      <el-table-column prop="maxAttempts" label="次数上限" width="100" />
      <el-table-column label="操作" width="220">
        <template #default="{ row }">
          <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
          <el-button link @click="openQuestions(row)">组卷</el-button>
          <el-button link type="danger" @click="remove(row.id)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
    <el-pagination
      class="pager"
      v-model:current-page="page"
      layout="total, prev, pager, next"
      :total="total"
      @current-change="load"
    />

    <el-dialog v-model="visible" :title="form.id ? '编辑试卷' : '新增试卷'" width="480px">
      <el-form label-width="100px">
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
        <el-form-item v-if="form.gateTicket" label="及格线%">
          <el-input-number v-model="form.passScore" :min="1" :max="100" />
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
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import http from '../../api/http'

const list = ref([])
const page = ref(1)
const total = ref(0)
const visible = ref(false)
const qVisible = ref(false)
const saving = ref(false)
const form = reactive({
  id: null,
  title: '',
  status: 'draft',
  durationMin: 60,
  maxAttempts: 0,
  gateTicket: false,
  passScore: 60,
})
const currentPaperId = ref(null)
const allQuestions = ref([])
const selectedQ = ref([])

async function load() {
  const res = await http.get('/api/exam/admin/papers', { params: { page: page.value, size: 10 } })
  const data = res.data?.data || res.data || {}
  list.value = data.list || []
  total.value = data.total || 0
}

function openCreate() {
  Object.assign(form, {
    id: null,
    title: '',
    status: 'draft',
    durationMin: 60,
    maxAttempts: 0,
    gateTicket: false,
    passScore: 60,
  })
  visible.value = true
}

function openEdit(row) {
  Object.assign(form, {
    id: row.id,
    title: row.title,
    status: row.status,
    durationMin: row.durationMin || 0,
    maxAttempts: row.maxAttempts || 0,
    gateTicket: !!row.gateTicket,
    passScore: row.passScore || 60,
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
  const qRes = await http.get('/api/exam/admin/questions', { params: { page: 1, size: 100 } })
  allQuestions.value = (qRes.data?.data || qRes.data || {}).list || []
  const linked = await http.get(`/api/exam/admin/papers/${row.id}/questions`)
  const rows = linked.data?.data || linked.data || []
  selectedQ.value = rows.map((r) => r.id || r.questionId)
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

onMounted(load)
</script>

<style scoped>
.toolbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; }
.pager { margin-top: 1rem; }
.hint { margin-left: 0.5rem; color: var(--el-text-color-secondary); font-size: 12px; }
.qrow { margin: 0.35rem 0; }
</style>
