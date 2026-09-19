<template>
  <template v-if="items.length">
    <el-form-item v-for="item in items" :key="item.id" :label="item.title" :required="!!item.required">
      <div class="attach-row">
        <el-upload :show-file-list="false" accept="image/*,.pdf,.doc,.docx" :http-request="(opt) => onUpload(item, opt)">
          <el-button size="small">{{ files[item.id] ? '重新上传' : '上传' }}</el-button>
        </el-upload>
        <a v-if="files[item.id]" :href="files[item.id]" target="_blank" rel="noopener noreferrer">已上传</a>
      </div>
    </el-form-item>
  </template>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import http from '../api/http'

const items = ref([])
const files = reactive({})

async function load() {
  const res = await http.get('/api/material/checklist')
  items.value = Array.isArray(res.data) ? res.data : []
}

async function onUpload(item, opt) {
  const fd = new FormData()
  fd.append('file', opt.file)
  const res = await http.post('/api/upload', fd)
  files[item.id] = res.data?.url || ''
  ElMessage.success('已上传')
}

function missingTitle() {
  for (const item of items.value) {
    if (item.required && !files[item.id]) return item.title || '材料'
  }
  return ''
}

function payload() {
  return items.value
    .filter((item) => files[item.id])
    .map((item) => ({ checklistId: item.id, fileUrl: files[item.id] }))
}

onMounted(load)
defineExpose({ missingTitle, payload })
</script>
