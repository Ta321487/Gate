<template>
  <div>
    <div class="toolbar">
      <el-input v-model="keyword" placeholder="搜索" clearable style="width:200px" @keyup.enter="load" />
      <el-switch
        v-if="softDelete"
        v-model="includeDeleted"
        inline-prompt
        :active-text="softCopy.include"
        :inactive-text="softCopy.on"
        @change="load"
      />
      <el-button type="primary" @click="load">查询</el-button>
      <el-button type="success" @click="openEdit()">新增{{ label }}</el-button>
      <el-button @click="exportCsv">导出 CSV</el-button>
      <el-button @click="downloadTemplate">导入模板</el-button>
      <el-upload
        :show-file-list="false"
        accept=".csv,text/csv"
        :http-request="onImport"
      >
        <el-button type="warning">导入 CSV</el-button>
      </el-upload>
    </div>
    <el-table :data="list" stripe>
      <el-table-column prop="id" label="ID" width="70" />
      <el-table-column prop="title" :label="fieldLabel('title', '名称')" />
      <el-table-column prop="author" :label="fieldLabel('author', '型号')" width="140" />
      <el-table-column prop="categoryName" label="分类" width="100" />
      <el-table-column v-if="hasMutex" prop="mutexCode" :label="fieldLabel('mutexCode', '互斥码')" width="110" />
      <el-table-column v-if="tagFilter" label="标签" min-width="120">
        <template #default="{ row }">{{ (row.tagNames || []).join('、') || '—' }}</template>
      </el-table-column>
      <el-table-column prop="stock" :label="fieldLabel('stock', '数量')" width="90" />
      <el-table-column v-if="hasSchedule" prop="startAt" :label="fieldLabel('startAt', '开始')" width="170" />
      <el-table-column v-if="hasSchedule" prop="endAt" :label="fieldLabel('endAt', '结束')" width="170" />
      <el-table-column v-if="softDelete" label="状态" width="80">
        <template #default="{ row }">
          <el-tag v-if="row.deleted" size="small" type="info">{{ softCopy.off }}</el-tag>
          <el-tag v-else size="small" type="success" effect="plain">{{ softCopy.on }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="200">
        <template #default="{ row }">
          <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
          <el-button v-if="softDelete && row.deleted" link type="success" @click="restore(row)">恢复</el-button>
          <el-button v-else link type="danger" @click="remove(row)">{{ softDelete ? softCopy.verb : '删除' }}</el-button>
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
          <el-input-number
            v-if="fieldType('author') === 'number'"
            v-model="authorNum"
            :min="0"
            :precision="2"
            :step="1"
            controls-position="right"
            style="width:100%"
          />
          <el-input v-else v-model="form.author" />
        </el-form-item>
        <el-form-item :label="fieldLabel('isbn', '编号')">
          <RichTextEditor
            v-if="isbnRich"
            v-model="form.isbn"
            :placeholder="`请输入${fieldLabel('isbn', '正文')}`"
          />
          <el-input
            v-else-if="fieldType('isbn') === 'url'"
            v-model="form.isbn"
            type="url"
            placeholder="https://"
          />
          <el-input
            v-else-if="fieldType('isbn') === 'textarea'"
            v-model="form.isbn"
            type="textarea"
            :rows="3"
          />
          <el-input v-else v-model="form.isbn" />
        </el-form-item>
        <el-form-item :label="fieldLabel('category', '分类')" required>
          <el-select v-model="form.categoryId" style="width:100%" placeholder="请选择分类">
            <el-option v-for="c in categories" :key="c.id" :label="c.name" :value="c.id" />
          </el-select>
        </el-form-item>
        <el-form-item
          v-if="showStock"
          :label="fieldLabel('stock', '数量')"
          required
        >
          <el-input-number v-model="form.stock" :min="0" :step="1" controls-position="right" style="width:100%" />
        </el-form-item>
        <el-form-item v-if="hasMutex" :label="fieldLabel('mutexCode', '互斥码')">
          <el-input v-model="form.mutexCode" maxlength="32" :placeholder="`相同互斥码的${label}不可同选，可留空`" />
        </el-form-item>
        <el-form-item v-if="hasCheckin" :label="fieldLabel('checkinCode', '签到码')">
          <div class="attach-row">
            <el-input v-model="form.checkinCode" maxlength="16" placeholder="到场口令" style="flex:1" />
            <el-button size="small" @click="genCheckin">生成</el-button>
          </div>
        </el-form-item>
        <el-form-item v-if="tagFilter" label="标签">
          <el-select v-model="form.tagIds" multiple filterable clearable placeholder="可选多个" style="width:100%">
            <el-option v-for="t in tags" :key="t.id" :label="t.name" :value="t.id" />
          </el-select>
        </el-form-item>
        <template v-if="hasSchedule">
          <el-form-item :label="fieldLabel('startAt', '开始时间')" required>
            <el-date-picker
              v-model="form.startAt"
              type="datetime"
              value-format="YYYY-MM-DD HH:mm:ss"
              style="width:100%"
            />
          </el-form-item>
          <el-form-item :label="fieldLabel('endAt', '结束时间')" required>
            <el-date-picker
              v-model="form.endAt"
              type="datetime"
              value-format="YYYY-MM-DD HH:mm:ss"
              style="width:100%"
            />
          </el-form-item>
          <el-form-item v-if="hasDeadline" :label="fieldLabel('applyDeadlineAt', '报名截止')">
            <el-date-picker
              v-model="form.applyDeadlineAt"
              type="datetime"
              value-format="YYYY-MM-DD HH:mm:ss"
              style="width:100%"
            />
          </el-form-item>
        </template>
        <el-form-item
          v-for="f in extraFields"
          :key="f.key"
          :label="f.label || f.key"
        >
          <el-date-picker
            v-if="f.type === 'datetime'"
            v-model="form[f.key]"
            type="datetime"
            value-format="YYYY-MM-DD HH:mm:ss"
            style="width:100%"
          />
          <el-input-number
            v-else-if="f.type === 'number'"
            v-model="form[f.key]"
            :min="0"
            controls-position="right"
            style="width:100%"
          />
          <el-input
            v-else-if="f.type === 'url'"
            v-model="form[f.key]"
            type="url"
            placeholder="https://"
          />
          <el-input v-else v-model="form[f.key]" />
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
import { archiveCopy, softDeleteCopy } from '../../utils/domainSchema.js'
import { sanitizeHtml } from '../../utils/richHtml.js'
import { downloadCsv, stripBom } from '../../utils/csvDownload.js'

const archive = archiveCopy()
const softCopy = softDeleteCopy()
const label = computed(() => archive.label || '对象')
const fields = computed(() => archive.fields || [])
const CORE_FIELD_KEYS = new Set([
  'title', 'author', 'isbn', 'category', 'stock',
  'mutexCode', 'checkinCode', 'startAt', 'endAt', 'applyDeadlineAt',
])
const extraFields = computed(() => fields.value.filter((f) => f?.key && !CORE_FIELD_KEYS.has(f.key)))
const isbnRich = computed(() => {
  const f = fields.value.find((x) => x.key === 'isbn')
  return f?.type === 'richtext' || archive.bodyField === 'isbn'
})
const hasSchedule = computed(() => fields.value.some((x) => x.key === 'startAt' || x.key === 'endAt'))
const hasDeadline = computed(() => fields.value.some((x) => x.key === 'applyDeadlineAt'))
const hasMutex = computed(() => fields.value.some((x) => x.key === 'mutexCode'))
const hasCheckin = computed(() => fields.value.some((x) => x.key === 'checkinCode'))
const softDelete = computed(() => !!archive.softDelete)
const tagFilter = computed(() => !!archive.tagFilter)
const showStock = computed(() => {
  const f = fields.value.find((x) => x.key === 'stock')
  return !f || f.type !== 'hidden'
})

function fieldMeta(key) {
  return fields.value.find((x) => x.key === key) || {}
}
function fieldType(key) {
  return fieldMeta(key).type || 'string'
}
function fieldLabel(key, fallback) {
  return fieldMeta(key).label || fallback
}

/** author 列存单价时用数字控件，提交仍写回字符串（后端 OrderStore 认 author） */
const authorNum = computed({
  get() {
    const n = Number(String(form.author ?? '').replace(/[¥￥,\s]/g, ''))
    return Number.isFinite(n) ? n : 0
  },
  set(v) {
    form.author = v == null || v === '' ? '' : String(v)
  },
})

const list = ref([])
const total = ref(0)
const page = ref(1)
const size = ref(10)
const keyword = ref('')
const includeDeleted = ref(false)
const categories = ref([])
const tags = ref([])
const visible = ref(false)
const form = reactive({
  id: null,
  title: '',
  author: '',
  isbn: '',
  categoryId: null,
  stock: 1,
  coverUrl: '',
  startAt: '',
  endAt: '',
  applyDeadlineAt: '',
  mutexCode: '',
  checkinCode: '',
  tagIds: [],
})

async function load() {
  const res = await http.get('/api/archive', {
    params: {
      page: page.value,
      size: size.value,
      keyword: keyword.value || undefined,
      includeDeleted: softDelete.value && includeDeleted.value ? true : undefined,
    },
  })
  list.value = res.data.list
  total.value = res.data.total
}

async function loadCats() {
  const res = await http.get('/api/categories')
  categories.value = res.data || res || []
}

async function loadTags() {
  if (!tagFilter.value) return
  try {
    const res = await http.get('/api/tags')
    tags.value = res.data || res || []
  } catch {
    tags.value = []
  }
}

function genCheckin() {
  const n = Math.floor(1000 + Math.random() * 9000)
  form.checkinCode = `ACT${n}`
}

function openEdit(row) {
  const extras = {}
  for (const f of extraFields.value) {
    extras[f.key] = row?.[f.key] ?? (f.type === 'number' ? 0 : '')
  }
  if (row) {
    Object.assign(form, {
      id: row.id,
      title: row.title || '',
      author: row.author || '',
      isbn: row.isbn || '',
      categoryId: row.categoryId,
      stock: row.stock ?? 1,
      coverUrl: row.coverUrl || '',
      startAt: row.startAt || '',
      endAt: row.endAt || '',
      applyDeadlineAt: row.applyDeadlineAt || '',
      mutexCode: row.mutexCode || '',
      checkinCode: row.checkinCode || '',
      tagIds: [...(row.tagIds || [])],
      ...extras,
    })
  } else {
    Object.assign(form, {
      id: null,
      title: '',
      author: '',
      isbn: '',
      categoryId: categories.value[0]?.id || null,
      stock: 1,
      coverUrl: '',
      startAt: '',
      endAt: '',
      applyDeadlineAt: '',
      mutexCode: '',
      checkinCode: hasCheckin.value ? `ACT${Math.floor(1000 + Math.random() * 9000)}` : '',
      tagIds: [],
      ...extras,
    })
  }
  visible.value = true
}

async function save() {
  if (!form.title?.trim()) {
    ElMessage.warning('请填写名称')
    return
  }
  if (hasSchedule.value && (!form.startAt || !form.endAt)) {
    ElMessage.warning('请填写开始与结束时间')
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
  const verb = softDelete.value ? softCopy.verb : '删除'
  await ElMessageBox.confirm(`确认${verb}「${row.title}」？`, '确认')
  await http.delete(`/api/archive/${row.id}`)
  ElMessage.success(softDelete.value ? `已${softCopy.verb}` : '已删除')
  load()
}

async function restore(row) {
  await http.post(`/api/archive/${row.id}/restore`)
  ElMessage.success('已恢复')
  load()
}

async function onCover(opt) {
  const fd = new FormData()
  fd.append('file', opt.file)
  const res = await http.post('/api/upload', fd)
  form.coverUrl = res.data.url
  ElMessage.success('已上传')
}

function downloadTemplate() {
  downloadCsv(
    `${label.value || 'archive'}_import_template.csv`,
    ['title', 'author', 'isbn', 'category', 'stock'],
    [['示例名称', '规格或责任人', '编号说明', '默认分类', '1']],
  )
  ElMessage.success('已下载导入模板（UTF-8 BOM，Excel 可直接打开）')
}

async function exportCsv() {
  const res = await http.get('/api/archive', {
    params: { page: 1, size: 5000, keyword: keyword.value || undefined },
  })
  const rows = res.data?.list || []
  if (!rows.length) {
    ElMessage.warning('当前无数据可导出')
    return
  }
  const headers = [
    fieldLabel('title', '名称'),
    fieldLabel('author', '型号'),
    fieldLabel('isbn', '编号'),
    '分类',
    fieldLabel('stock', '数量'),
  ]
  if (hasSchedule.value) {
    headers.push(fieldLabel('startAt', '开始'), fieldLabel('endAt', '结束'))
  }
  const data = rows.map((row) => {
    const line = [
      row.title,
      row.author,
      row.isbn,
      row.categoryName,
      row.stock,
    ]
    if (hasSchedule.value) line.push(row.startAt, row.endAt)
    return line
  })
  downloadCsv(`${label.value || 'archive'}_${Date.now()}.csv`, headers, data)
  ElMessage.success(`已导出 ${rows.length} 条（UTF-8，可用 Excel 直接打开）`)
}

async function onImport(opt) {
  const file = opt.file
  if (!file) return
  const text = stripBom(await file.text())
  if (!text.trim()) {
    ElMessage.warning('文件为空')
    return
  }
  try {
    const res = await http.post('/api/archive/import', { csv: text })
    const r = res.data || {}
    const ok = r.ok || 0
    const fail = r.fail || 0
    if (fail > 0) {
      const sample = (r.errors || []).slice(0, 3).map((e) => `第${e.line}行: ${e.message}`).join('；')
      ElMessage.warning(`成功 ${ok} 条，失败 ${fail} 条。${sample}`)
    } else {
      ElMessage.success(`成功导入 ${ok} 条`)
    }
    await loadCats()
    await load()
  } catch (e) {
    ElMessage.error(e?.response?.data?.message || e?.message || '导入失败')
  }
}

onMounted(async () => {
  await loadCats()
  await loadTags()
  await load()
})
</script>

<style scoped>
.toolbar { display: flex; gap: 8px; margin-bottom: 12px; flex-wrap: wrap; align-items: center; }
.pager { margin-top: 16px; display: flex; justify-content: flex-end; }
.muted { margin-left: 8px; color: #909399; font-size: 12px; }
.attach-row { display: flex; gap: 8px; width: 100%; align-items: center; }
</style>
