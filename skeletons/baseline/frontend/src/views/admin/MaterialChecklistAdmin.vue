<template>
  <div>
    <h2>{{ title }}</h2>
    <p class="lead">{{ lead }}</p>
    <el-form inline @submit.prevent>
      <el-form-item label="材料名">
        <el-input v-model="form.title" maxlength="60" placeholder="如身份证明" style="width: 220px" />
      </el-form-item>
      <el-form-item label="必传">
        <el-switch v-model="form.required" />
      </el-form-item>
      <el-button type="primary" @click="add">新增</el-button>
    </el-form>
    <el-table :data="list" stripe>
      <el-table-column prop="title" label="材料" />
      <el-table-column label="必传" width="90">
        <template #default="{ row }">{{ row.required ? '是' : '否' }}</template>
      </el-table-column>
      <el-table-column prop="sortOrder" label="排序" width="80" />
    </el-table>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import http from '../../api/http'
import { getSchema } from '../../utils/domainSchema'

const labels = computed(() => getSchema().labels || {})
const title = computed(() => labels.value.materialChecklistTitle || '材料清单')
const lead = computed(
  () => labels.value.materialChecklistLead || '维护必传材料项；申请人须按清单上传，缺件不可提交。',
)
const list = ref([])
const form = reactive({ title: '', required: true })

async function load() {
  const res = await http.get('/api/material/checklist')
  list.value = res.data || []
}

async function add() {
  const titleText = (form.title || '').trim()
  if (!titleText) {
    ElMessage.warning('请填写材料名')
    return
  }
  await http.post('/api/material/checklist', { title: titleText, required: form.required })
  ElMessage.success('已新增')
  form.title = ''
  await load()
}

onMounted(load)
</script>
