<template>
  <div>
    <p class="lead">{{ pageLead }}</p>
    <div class="tools">
      <el-input
        v-model="typeFilter"
        clearable
        :placeholder="typeLabel"
        style="width: 160px"
        @keyup.enter="onSearch"
      />
      <el-input
        v-model="keyword"
        clearable
        placeholder="编码 / 显示名"
        style="width: 200px"
        @keyup.enter="onSearch"
      />
      <el-button type="primary" @click="onSearch">查询</el-button>
      <el-button type="success" @click="openCreate">新增</el-button>
    </div>
    <div class="table-scroll">
      <el-table :data="list" stripe empty-text="暂无字典项">
        <el-table-column prop="dictType" :label="typeLabel" min-width="120" />
        <el-table-column prop="itemCode" :label="codeLabel" min-width="120" />
        <el-table-column prop="itemLabel" :label="labelLabel" min-width="140" />
        <el-table-column prop="sortOrder" :label="sortLabel" width="90" />
        <el-table-column :label="enabledLabel" width="90">
          <template #default="{ row }">
            <el-switch
              :model-value="!!row.enabled"
              @change="(v) => toggleEnabled(row, v)"
            />
          </template>
        </el-table-column>
        <el-table-column label="操作" width="220" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
            <el-button link @click="bump(row, -10)">上移</el-button>
            <el-button link @click="bump(row, 10)">下移</el-button>
            <el-button link type="danger" @click="remove(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>
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

    <el-dialog v-model="visible" :title="form.id ? '编辑字典项' : '新增字典项'" width="440px" destroy-on-close>
      <el-form label-position="top">
        <el-form-item :label="typeLabel" required>
          <el-input v-model="form.dictType" maxlength="64" />
        </el-form-item>
        <el-form-item :label="codeLabel" required>
          <el-input v-model="form.itemCode" maxlength="64" />
        </el-form-item>
        <el-form-item :label="labelLabel" required>
          <el-input v-model="form.itemLabel" maxlength="128" />
        </el-form-item>
        <el-form-item :label="sortLabel">
          <el-input-number v-model="form.sortOrder" :min="0" :max="9999" />
        </el-form-item>
        <el-form-item :label="enabledLabel">
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
const pageLead = computed(() => labels.value.dictPageLead || '维护状态、类型等下拉文案。')
const typeLabel = computed(() => labels.value.dictTypeLabel || '字典类型')
const codeLabel = computed(() => labels.value.dictCodeLabel || '编码')
const labelLabel = computed(() => labels.value.dictLabelLabel || '显示名')
const sortLabel = computed(() => labels.value.dictSortLabel || '排序')
const enabledLabel = computed(() => labels.value.dictEnabledLabel || '启用')

const list = ref([])
const page = ref(1)
const size = ref(20)
const total = ref(0)
const keyword = ref('')
const typeFilter = ref('')
const visible = ref(false)
const form = reactive({
  id: null,
  dictType: 'common_status',
  itemCode: '',
  itemLabel: '',
  sortOrder: 100,
  enabled: true,
})

function onSearch() {
  page.value = 1
  load()
}

async function load() {
  const res = await http.get('/api/admin/dict', {
    params: {
      type: typeFilter.value || undefined,
      keyword: keyword.value || undefined,
      page: page.value,
      size: size.value,
    },
  })
  list.value = res.data?.list || []
  total.value = res.data?.total || 0
}

function openCreate() {
  form.id = null
  form.dictType = typeFilter.value || 'common_status'
  form.itemCode = ''
  form.itemLabel = ''
  form.sortOrder = 100
  form.enabled = true
  visible.value = true
}

function openEdit(row) {
  form.id = row.id
  form.dictType = row.dictType || ''
  form.itemCode = row.itemCode || ''
  form.itemLabel = row.itemLabel || ''
  form.sortOrder = row.sortOrder ?? 100
  form.enabled = !!row.enabled
  visible.value = true
}

async function save() {
  const body = {
    dictType: form.dictType,
    itemCode: form.itemCode,
    itemLabel: form.itemLabel,
    sortOrder: form.sortOrder,
    enabled: form.enabled,
  }
  if (form.id) await http.put(`/api/admin/dict/${form.id}`, body)
  else await http.post('/api/admin/dict', body)
  ElMessage.success('已保存')
  visible.value = false
  load()
}

async function toggleEnabled(row, v) {
  await http.put(`/api/admin/dict/${row.id}`, { enabled: !!v })
  load()
}

async function bump(row, delta) {
  await http.post(`/api/admin/dict/${row.id}/sort`, { delta })
  load()
}

async function remove(row) {
  await ElMessageBox.confirm(`确认删除「${row.itemLabel}」？`, '删除')
  await http.delete(`/api/admin/dict/${row.id}`)
  ElMessage.success('已删除')
  load()
}

onMounted(load)
</script>

<style scoped>
.lead { margin: 0 0 12px; color: var(--el-text-color-secondary); font-size: 13px; }
.tools { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 12px; }
.pager { margin-top: 12px; display: flex; justify-content: flex-end; }
</style>
