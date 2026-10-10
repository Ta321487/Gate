<template>
  <div>
    <div class="toolbar">
      <h2 class="page-title">{{ pageTitle }}</h2>
      <el-button type="primary" @click="openEdit()">新增链接</el-button>
      <el-button @click="load">刷新</el-button>
    </div>
    <el-table :data="list" stripe>
      <el-table-column prop="title" label="名称" min-width="140" />
      <el-table-column prop="url" label="链接" min-width="220" show-overflow-tooltip />
      <el-table-column prop="sortOrder" label="排序" width="80" />
      <el-table-column label="状态" width="90">
        <template #default="{ row }">{{ row.enabled ? '显示' : '隐藏' }}</template>
      </el-table-column>
      <el-table-column label="操作" width="160" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
          <el-button link type="danger" @click="remove(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
    <el-empty v-if="!list.length" :description="emptyText" />

    <el-dialog v-model="visible" :title="form.id ? '编辑链接' : '新增链接'" width="440px" destroy-on-close>
      <el-form :model="form" label-width="72px" @submit.prevent>
        <el-form-item label="名称" required>
          <el-input v-model="form.title" maxlength="128" show-word-limit />
        </el-form-item>
        <el-form-item label="链接" required>
          <el-input v-model="form.url" maxlength="512" placeholder="https://" />
        </el-form-item>
        <el-form-item label="排序">
          <el-input-number v-model="form.sortOrder" :min="0" :max="9999" />
        </el-form-item>
        <el-form-item label="显示">
          <el-switch v-model="form.enabled" />
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
import { ElMessage, ElMessageBox } from 'element-plus'
import http from '../../api/http'
import { getSchema } from '../../utils/domainSchema.js'

const labels = computed(() => getSchema()?.labels || {})
const pageTitle = computed(() => labels.value.friendLinkAdminTitle || '友情链接维护')
const emptyText = computed(() => labels.value.friendLinkEmpty || '暂无友情链接')

const list = ref([])
const visible = ref(false)
const form = reactive({ id: null, title: '', url: '', sortOrder: 0, enabled: true })

async function load() {
  const res = await http.get('/api/blog-friend-links/admin')
  list.value = res.data || res || []
}

function openEdit(row) {
  if (row) {
    Object.assign(form, {
      id: row.id,
      title: row.title || '',
      url: row.url || '',
      sortOrder: Number(row.sortOrder) || 0,
      enabled: !!row.enabled,
    })
  } else {
    Object.assign(form, { id: null, title: '', url: '', sortOrder: 0, enabled: true })
  }
  visible.value = true
}

async function save() {
  if (!(form.title || '').trim() || !(form.url || '').trim()) {
    ElMessage.warning('请填写名称和链接')
    return
  }
  await http.post('/api/blog-friend-links/admin', { ...form })
  ElMessage.success('已保存')
  visible.value = false
  load()
}

async function remove(row) {
  await ElMessageBox.confirm(`删除「${row.title}」？`, '确认')
  await http.delete(`/api/blog-friend-links/admin/${row.id}`)
  ElMessage.success('已删除')
  load()
}

onMounted(load)
</script>

<style scoped>
.toolbar { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; margin-bottom: 12px; }
.page-title { margin: 0; font-size: 18px; font-weight: 600; margin-right: auto; }
</style>
