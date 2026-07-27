<template>
  <div>
    <section class="hero">
      <h1>附件权限</h1>
      <p class="muted">配置资料附件地址与下载权限（public / login / staff）。条目标题在「资料条目」维护。</p>
    </section>
    <el-table :data="list" stripe>
      <el-table-column prop="title" label="标题" min-width="160" />
      <el-table-column prop="accessLevel" label="权限" width="100" />
      <el-table-column prop="fileUrl" label="附件 URL" min-width="180" />
      <el-table-column label="操作" width="100">
        <template #default="{ row }">
          <el-button link type="primary" @click="edit(row)">编辑</el-button>
        </template>
      </el-table-column>
    </el-table>
    <el-dialog v-model="visible" title="附件与权限" width="480px">
      <el-form label-width="90px">
        <el-form-item label="附件 URL">
          <el-input v-model="draft.fileUrl" placeholder="/uploads/..." />
        </el-form-item>
        <el-form-item label="权限">
          <el-select v-model="draft.accessLevel" style="width: 100%">
            <el-option label="开放(public)" value="public" />
            <el-option label="登录可下(login)" value="login" />
            <el-option label="管理人员(staff)" value="staff" />
          </el-select>
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
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import http from '../../utils/http'

const list = ref([])
const visible = ref(false)
const draft = reactive({ id: null, fileUrl: '', accessLevel: 'login' })

async function load() {
  const res = await http.get('/api/doclib/items')
  list.value = res.data?.data || res.data || []
}

function edit(row) {
  draft.id = row.id
  draft.fileUrl = row.fileUrl || ''
  draft.accessLevel = row.accessLevel || 'login'
  visible.value = true
}

async function save() {
  await http.put(`/api/doclib/admin/items/${draft.id}`, {
    fileUrl: draft.fileUrl,
    accessLevel: draft.accessLevel,
  })
  ElMessage.success('已保存')
  visible.value = false
  await load()
}

onMounted(load)
</script>

<style scoped>
.hero { margin-bottom: 1rem; }
.muted { color: var(--el-text-color-secondary); }
</style>
