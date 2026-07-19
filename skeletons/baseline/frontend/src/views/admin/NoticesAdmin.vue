<template>
  <div>
    <div class="toolbar">
      <el-button type="primary" @click="openEdit()">新增公告</el-button>
    </div>
    <el-table :data="list" stripe>
      <el-table-column prop="title" label="标题" min-width="160" />
      <el-table-column prop="publisherName" label="发送人" width="120" />
      <el-table-column prop="createdAt" label="发布时间" width="170" />
      <el-table-column prop="content" label="摘要" min-width="180" show-overflow-tooltip />
      <el-table-column label="操作" width="180" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="openView(row)">详情</el-button>
          <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
          <el-button link type="danger" @click="remove(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
    <div class="pager">
      <el-pagination
        v-model:current-page="page"
        v-model:page-size="size"
        background
        layout="total, prev, pager, next"
        :total="total"
        @current-change="load"
      />
    </div>
    <el-dialog v-model="viewVisible" title="公告详情" width="560px">
      <p class="view-meta">{{ viewRow.publisherName || '—' }} · {{ viewRow.createdAt || '—' }}</p>
      <h3 class="view-title">{{ viewRow.title }}</h3>
      <div class="view-body">{{ viewRow.content || '（无正文）' }}</div>
      <template #footer>
        <el-button type="primary" @click="viewVisible = false">关闭</el-button>
      </template>
    </el-dialog>
    <el-dialog v-model="visible" :title="form.id ? '编辑公告' : '新增公告'" width="560px">
      <el-form :model="form" label-width="72px" require-asterisk-position="right">
        <el-form-item label="标题" required><el-input v-model="form.title" maxlength="128" show-word-limit /></el-form-item>
        <el-form-item label="内容" required><el-input v-model="form.content" type="textarea" :rows="6" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="visible = false">取消</el-button>
        <el-button type="primary" @click="save">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
/** 基线公告管理 */
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import http from '../../api/http'

const list = ref([])
const page = ref(1)
const size = ref(20)
const total = ref(0)
const visible = ref(false)
const viewVisible = ref(false)
const viewRow = reactive({ title: '', content: '', publisherName: '', createdAt: '' })
const form = reactive({ id: null, title: '', content: '' })

async function load() {
  const res = await http.get('/api/notices', { params: { page: page.value, size: size.value } })
  list.value = res.data.list
  total.value = res.data.total
}

function openView(row) {
  Object.assign(viewRow, {
    title: row.title || '',
    content: row.content || '',
    publisherName: row.publisherName || '',
    createdAt: row.createdAt || '',
  })
  viewVisible.value = true
}

function openEdit(row) {
  if (row) Object.assign(form, { id: row.id, title: row.title, content: row.content })
  else Object.assign(form, { id: null, title: '', content: '' })
  visible.value = true
}

async function save() {
  if (!form.title?.trim()) {
    ElMessage.warning('请填写标题')
    return
  }
  if (form.id) await http.put(`/api/notices/${form.id}`, { title: form.title, content: form.content })
  else await http.post('/api/notices', { title: form.title, content: form.content })
  ElMessage.success('已保存')
  visible.value = false
  load()
}

async function remove(row) {
  await ElMessageBox.confirm('确认删除该公告？', '删除')
  await http.delete(`/api/notices/${row.id}`)
  ElMessage.success('已删除')
  load()
}

onMounted(load)
</script>

<style scoped>
.toolbar { margin-bottom: 12px; }
.pager { margin-top: 16px; display: flex; justify-content: flex-end; }
.view-meta { margin: 0 0 8px; color: #6b7c8a; font-size: 13px; }
.view-title { margin: 0 0 14px; font-size: 18px; line-height: 1.35; }
.view-body { white-space: pre-wrap; line-height: 1.7; font-size: 14px; }
</style>
