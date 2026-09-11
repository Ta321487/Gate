<template>
  <div>
    <div class="toolbar">
      <el-button type="primary" @click="openEdit()">{{ createLabel }}</el-button>
    </div>
    <el-table :data="list" stripe>
      <el-table-column prop="title" label="标题" min-width="160" />
      <el-table-column prop="publisherName" label="发送人" width="120" />
      <el-table-column v-if="auditOn" label="提交人" width="120" show-overflow-tooltip>
        <template #default="{ row }">{{ row.submitterUsername || '—' }}</template>
      </el-table-column>
      <el-table-column v-if="auditOn" label="审核" width="100">
        <template #default="{ row }">
          <el-tag size="small" :type="auditTagType(row)" effect="plain">
            {{ auditLabel(row) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="置顶" width="90">
        <template #default="{ row }">
          <el-switch
            v-if="canEditRow(row)"
            :model-value="!!row.pinned"
            size="small"
            @change="(v) => togglePin(row, v)"
          />
          <el-tag v-else-if="row.pinned" size="small" type="warning" effect="plain">置顶</el-tag>
          <span v-else class="muted">—</span>
        </template>
      </el-table-column>
      <el-table-column prop="createdAt" label="发布时间" width="170" />
      <el-table-column prop="content" label="摘要" min-width="180" show-overflow-tooltip />
      <el-table-column label="操作" width="220" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="openView(row)">详情</el-button>
          <el-button
            v-if="canApprove && isPending(row)"
            link
            type="success"
            @click="approve(row)"
          >通过审核</el-button>
          <el-button v-if="canEditRow(row)" link type="primary" @click="openEdit(row)">编辑</el-button>
          <el-button v-if="canEditRow(row)" link type="danger" @click="remove(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
    <div class="pager">
      <el-pagination
        v-model:current-page="page"
        v-model:page-size="size"
        background
        layout="total, sizes, prev, pager, next"
        :page-sizes="[10, 20, 50]"
        :total="total"
        @current-change="load"
        @size-change="load"
      />
    </div>
    <el-dialog v-model="viewVisible" title="详情" width="560px">
      <p class="view-meta">{{ viewRow.publisherName || '—' }} · {{ viewRow.createdAt || '—' }}</p>
      <h3 class="view-title">{{ viewRow.title }}</h3>
      <div class="view-body">{{ viewRow.content || '（无正文）' }}</div>
      <template #footer>
        <el-button type="primary" @click="viewVisible = false">关闭</el-button>
      </template>
    </el-dialog>
    <el-dialog v-model="visible" :title="form.id ? '编辑' : createLabel" width="560px">
      <el-form :model="form" label-width="72px" require-asterisk-position="right">
        <el-form-item label="标题" required><el-input v-model="form.title" maxlength="128" show-word-limit /></el-form-item>
        <el-form-item label="内容" required><el-input v-model="form.content" type="textarea" :rows="6" /></el-form-item>
        <el-form-item v-if="form.id || isSuper" label="置顶">
          <el-switch v-model="form.pinned" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="visible = false">取消</el-button>
        <el-button type="primary" @click="save">{{ saveLabel }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
/** 基线公告/活动管理；多店时商家提交待审，超管审核通过 */
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import http from '../../api/http'
import { getSchema } from '../../utils/domainSchema.js'

const list = ref([])
const page = ref(1)
const size = ref(20)
const total = ref(0)
const visible = ref(false)
const viewVisible = ref(false)
const viewRow = reactive({ title: '', content: '', publisherName: '', createdAt: '' })
const form = reactive({ id: null, title: '', content: '', pinned: false })

const marketplace = computed(() => !!getSchema()?.shopMarketplace)
const auditOn = computed(() => marketplace.value)
const isSuper = computed(() => localStorage.getItem('superAdmin') === 'true')
const canApprove = computed(() => auditOn.value && isSuper.value)
const createLabel = computed(() => {
  if (!marketplace.value) return '新增公告'
  return isSuper.value ? '发布活动' : '提交活动审核'
})
const saveLabel = computed(() => {
  if (marketplace.value && !isSuper.value && !form.id) return '提交审核'
  return '保存'
})

function isPending(row) {
  const as = String(row?.auditStatus || '').trim()
  return as === 'pending'
}

function auditLabel(row) {
  const as = String(row?.auditStatus || '').trim()
  if (as === 'pending') return '待审核'
  if (as === 'approved' || !as) return '已通过'
  return as
}

function auditTagType(row) {
  return isPending(row) ? 'warning' : 'success'
}

function canEditRow(row) {
  if (!marketplace.value) return true
  if (isSuper.value) return true
  // 商家：仅可看自己待审条目的详情，编辑/删除留给超管（与后端一致）
  return false
}

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
  if (row) Object.assign(form, { id: row.id, title: row.title, content: row.content, pinned: !!row.pinned })
  else Object.assign(form, { id: null, title: '', content: '', pinned: false })
  visible.value = true
}

async function togglePin(row, on) {
  await http.post(`/api/notices/${row.id}/pin`, { pinned: !!on })
  ElMessage.success(on ? '已置顶' : '已取消置顶')
  load()
}

async function save() {
  if (!form.title?.trim()) {
    ElMessage.warning('请填写标题')
    return
  }
  if (form.id) {
    await http.put(`/api/notices/${form.id}`, {
      title: form.title,
      content: form.content,
      pinned: !!form.pinned,
    })
  } else {
    const res = await http.post('/api/notices', { title: form.title, content: form.content })
    const id = res.data?.id
    if (id && form.pinned) {
      await http.post(`/api/notices/${id}/pin`, { pinned: true })
    }
  }
  ElMessage.success(
    marketplace.value && !isSuper.value && !form.id ? '已提交，待平台审核' : '已保存',
  )
  visible.value = false
  load()
}

async function approve(row) {
  await ElMessageBox.confirm(`通过「${row.title}」的活动审核？`, '审核')
  await http.post(`/api/notices/${row.id}/approve`)
  ElMessage.success('已通过')
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
.pager { margin-top: 12px; display: flex; justify-content: flex-end; }
.muted { color: var(--portal-muted, #94a3b8); font-size: 12px; }
.view-meta { margin: 0 0 8px; color: var(--portal-muted, #909399); font-size: 13px; }
.view-title { margin: 0 0 12px; font-size: 18px; }
.view-body { white-space: pre-wrap; line-height: 1.6; }
</style>
