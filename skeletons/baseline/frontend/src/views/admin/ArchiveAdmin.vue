<template>
  <div>
    <div class="toolbar">
      <el-input v-model="keyword" placeholder="搜索" clearable style="width:200px" @keyup.enter="load" />
      <el-button type="primary" @click="load">查询</el-button>
      <el-button type="success" @click="openEdit()">新增{{ label }}</el-button>
    </div>
    <el-table :data="list" stripe>
      <el-table-column prop="id" label="ID" width="70" />
      <el-table-column prop="title" :label="fieldLabel('title', '名称')" />
      <el-table-column prop="author" :label="fieldLabel('author', '型号')" width="140" />
      <el-table-column prop="categoryName" label="分类" width="100" />
      <el-table-column prop="stock" :label="fieldLabel('stock', '库存')" width="90" />
      <el-table-column label="操作" width="160">
        <template #default="{ row }">
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
    <el-dialog
      v-model="visible"
      :title="form.id ? `编辑${label}` : `新增${label}`"
      :width="isbnRich ? '720px' : '480px'"
      destroy-on-close
    >
      <el-form :model="form" label-width="96px" require-asterisk-position="right">
        <el-form-item :label="fieldLabel('title', '名称')" required>
          <el-input v-model="form.title" />
        </el-form-item>
        <el-form-item :label="fieldLabel('author', '型号')">
          <el-input v-model="form.author" />
        </el-form-item>
        <el-form-item :label="fieldLabel('isbn', '编号')">
          <RichTextEditor
            v-if="isbnRich"
            v-model="form.isbn"
            :placeholder="`请输入${fieldLabel('isbn', '正文')}`"
          />
          <el-input v-else v-model="form.isbn" />
        </el-form-item>
        <el-form-item label="分类" required>
          <el-select v-model="form.categoryId" style="width:100%">
            <el-option v-for="c in categories" :key="c.id" :label="c.name" :value="c.id" />
          </el-select>
        </el-form-item>
        <el-form-item :label="fieldLabel('stock', '库存')" required>
          <el-input-number v-model="form.stock" :min="0" />
        </el-form-item>
        <el-form-item label="封面">
          <el-upload :show-file-list="false" accept="image/*" :http-request="onCover">
            <el-button size="small">上传</el-button>
          </el-upload>
          <span v-if="form.coverUrl" class="muted">{{ form.coverUrl }}</span>
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
import RichTextEditor from '../../components/RichTextEditor.vue'
import { archiveCopy } from '../../utils/domainSchema.js'
import { sanitizeHtml } from '../../utils/richHtml.js'

const archive = archiveCopy()
const label = computed(() => archive.label || '对象')
const fields = computed(() => archive.fields || [])
const isbnRich = computed(() => {
  const f = fields.value.find((x) => x.key === 'isbn')
  return f?.type === 'richtext' || archive.bodyField === 'isbn'
})

function fieldLabel(key, fallback) {
  const f = fields.value.find((x) => x.key === key)
  return (f && f.label) || fallback
}

const list = ref([])
const total = ref(0)
const page = ref(1)
const size = ref(10)
const keyword = ref('')
const categories = ref([])
const visible = ref(false)
const form = reactive({
  id: null, title: '', author: '', isbn: '', categoryId: null, stock: 1, coverUrl: '',
})

async function load() {
  const res = await http.get('/api/archive', {
    params: { page: page.value, size: size.value, keyword: keyword.value || undefined },
  })
  list.value = res.data.list
  total.value = res.data.total
}

async function loadCats() {
  const res = await http.get('/api/categories')
  categories.value = res.data || res || []
}

function openEdit(row) {
  if (row) Object.assign(form, row)
  else {
    Object.assign(form, {
      id: null, title: '', author: '', isbn: '',
      categoryId: categories.value[0]?.id || null, stock: 1, coverUrl: '',
    })
  }
  visible.value = true
}

async function save() {
  if (!form.title?.trim()) {
    ElMessage.warning('请填写名称')
    return
  }
  const payload = { ...form }
  if (isbnRich.value) payload.isbn = sanitizeHtml(form.isbn || '')
  if (form.id) await http.put(`/api/archive/${form.id}`, payload)
  else await http.post('/api/archive', payload)
  ElMessage.success('已保存')
  visible.value = false
  load()
}

async function remove(row) {
  await ElMessageBox.confirm(`删除「${row.title}」？`, '确认')
  await http.delete(`/api/archive/${row.id}`)
  ElMessage.success('已删除')
  load()
}

async function onCover(opt) {
  const fd = new FormData()
  fd.append('file', opt.file)
  const res = await http.post('/api/upload', fd)
  form.coverUrl = res.data.url
  ElMessage.success('已上传')
}

onMounted(async () => {
  await loadCats()
  await load()
})
</script>

<style scoped>
.toolbar { display: flex; gap: 8px; margin-bottom: 12px; flex-wrap: wrap; }
.pager { margin-top: 16px; display: flex; justify-content: flex-end; }
.muted { margin-left: 8px; color: #909399; font-size: 12px; }
</style>
