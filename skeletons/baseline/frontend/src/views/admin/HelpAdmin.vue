<template>
  <div class="card">
    <h2>使用说明</h2>
    <el-form label-width="72px">
      <el-form-item :label="titleLabel">
        <el-input v-model="form.title" maxlength="64" @input="markDirty" />
      </el-form-item>
      <el-form-item :label="bodyLabel">
        <el-input v-model="form.body" type="textarea" :rows="12" maxlength="4000" show-word-limit @input="markDirty" />
      </el-form-item>
      <el-form-item>
        <el-button type="primary" @click="save">保存</el-button>
      </el-form-item>
    </el-form>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import http from '../../api/http'
import { getSchema } from '../../utils/domainSchema.js'
import { useUnsavedGuard } from '../../utils/unsavedGuard.js'

const labels = computed(() => getSchema()?.labels || {})
const titleLabel = computed(() => labels.value.helpTitleLabel || '标题')
const bodyLabel = computed(() => labels.value.helpBodyLabel || '正文')
const form = reactive({ title: '', body: '' })
const dirty = ref(false)
useUnsavedGuard(dirty)

onMounted(async () => {
  const res = await http.get('/api/help')
  form.title = res.data?.title || ''
  form.body = res.data?.body || ''
  dirty.value = false
})

async function save() {
  await http.put('/api/admin/help', { title: form.title, body: form.body })
  dirty.value = false
  ElMessage.success('已保存')
}

function markDirty() {
  dirty.value = true
}
</script>
