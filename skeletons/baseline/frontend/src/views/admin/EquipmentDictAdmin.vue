<template>
  <div>
    <p class="lead">{{ pageLead }}</p>
    <div class="tools">
      <el-input
        v-model="keyword"
        clearable
        placeholder="设备名称"
        style="width: 200px"
        @keyup.enter="onSearch"
      />
      <el-button type="primary" @click="onSearch">查询</el-button>
      <el-button type="success" @click="openCreate">新增设备</el-button>
    </div>
    <div class="table-scroll">
      <el-table :data="list" stripe>
        <el-table-column prop="name" label="名称" min-width="160" />
        <el-table-column prop="sortOrder" label="排序" width="100" />
        <el-table-column label="启用" width="90">
          <template #default="{ row }">
            <el-tag :type="row.enabled ? 'success' : 'info'" size="small">
              {{ row.enabled ? '是' : '否' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="createdAt" label="创建时间" width="170" />
        <el-table-column label="操作" width="140" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
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

    <el-dialog v-model="visible" :title="form.id ? '编辑设备' : '新增设备'" width="420px" destroy-on-close>
      <el-form label-position="top">
        <el-form-item label="名称" required>
          <el-input v-model="form.name" maxlength="64" />
        </el-form-item>
        <el-form-item label="排序">
          <el-input-number v-model="form.sortOrder" :min="0" :max="9999" />
        </el-form-item>
        <el-form-item label="启用">
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
/** 会议室配套设备字典（E-10 room_equipment） */
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import http from '../../api/http'
import { getSchema } from '../../utils/domainSchema.js'

const labels = computed(() => getSchema()?.labels || {})
const pageLead = computed(
  () =>
    labels.value.equipmentDictPageLead ||
    '维护会议室可勾选的配套设备名称；档案详情与预约页展示已选清单。',
)

const list = ref([])
const page = ref(1)
const size = ref(20)
const total = ref(0)
const keyword = ref('')
const visible = ref(false)
const form = reactive({
  id: null,
  name: '',
  sortOrder: 100,
  enabled: true,
})

function onSearch() {
  page.value = 1
  load()
}

async function load() {
  const res = await http.get('/api/admin/equipment-dict', {
    params: {
      page: page.value,
      size: size.value,
      keyword: keyword.value || undefined,
    },
  })
  list.value = res.data?.list || []
  total.value = res.data?.total || 0
}

function openCreate() {
  Object.assign(form, { id: null, name: '', sortOrder: 100, enabled: true })
  visible.value = true
}

function openEdit(row) {
  Object.assign(form, {
    id: row.id,
    name: row.name || '',
    sortOrder: row.sortOrder ?? 100,
    enabled: !!row.enabled,
  })
  visible.value = true
}

async function save() {
  if (!form.name?.trim()) {
    ElMessage.warning('请填写名称')
    return
  }
  const body = {
    name: form.name.trim(),
    sortOrder: form.sortOrder,
    enabled: form.enabled,
  }
  if (form.id) await http.put(`/api/admin/equipment-dict/${form.id}`, body)
  else await http.post('/api/admin/equipment-dict', body)
  ElMessage.success('已保存')
  visible.value = false
  await load()
}

async function remove(row) {
  await ElMessageBox.confirm(`删除设备「${row.name}」？不影响已写入档案的清单文案。`, '确认', {
    type: 'warning',
  })
  await http.delete(`/api/admin/equipment-dict/${row.id}`)
  ElMessage.success('已删除')
  await load()
}

onMounted(load)
</script>

<style scoped>
.lead {
  margin: 0 0 12px;
  color: var(--el-text-color-secondary);
  font-size: 14px;
}
.tools {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 12px;
}
.table-scroll {
  overflow-x: auto;
}
.pager {
  margin-top: 12px;
  display: flex;
  justify-content: flex-end;
}
</style>
