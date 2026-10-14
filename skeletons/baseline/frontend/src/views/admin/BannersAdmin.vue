<template>
  <div>
    <div class="toolbar">
      <h2 class="title">{{ labels.bannersMenu || '广告位' }}</h2>
      <el-button type="primary" @click="openEdit()">新增</el-button>
      <el-button @click="load">刷新</el-button>
    </div>
    <el-table :data="list" stripe v-loading="loading">
      <el-table-column prop="slot" :label="labels.bannerSlotLabel || '槽位'" width="100" />
      <el-table-column prop="title" label="标题" min-width="140" />
      <el-table-column prop="lead" label="导语" min-width="160" show-overflow-tooltip />
      <el-table-column prop="imageUrl" label="图片地址" min-width="180" show-overflow-tooltip />
      <el-table-column prop="sortOrder" label="排序" width="80" />
      <el-table-column label="启用" width="90">
        <template #default="{ row }">
          <el-tag size="small" :type="row.enabled ? 'success' : 'info'">
            {{ row.enabled ? '启用' : '停用' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="160" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
          <el-button link type="danger" @click="remove(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
    <p v-if="!loading && !list.length" class="empty">{{ labels.bannerEmptyHint || '暂无广告位' }}</p>

    <el-dialog v-model="dlg" :title="form.id ? '编辑广告位' : '新增广告位'" width="520px">
      <el-form label-width="88px">
        <el-form-item :label="labels.bannerSlotLabel || '槽位'">
          <el-select v-model="form.slot" style="width: 100%">
            <el-option label="首页 home" value="home" />
            <el-option label="门户 portal" value="portal" />
          </el-select>
        </el-form-item>
        <el-form-item label="标题" required>
          <el-input v-model="form.title" maxlength="128" show-word-limit />
        </el-form-item>
        <el-form-item label="导语">
          <el-input v-model="form.lead" maxlength="255" />
        </el-form-item>
        <el-form-item label="图片地址">
          <el-input v-model="form.imageUrl" placeholder="本地路径或 http(s) 地址" />
        </el-form-item>
        <el-form-item label="跳转链接">
          <el-input v-model="form.linkUrl" placeholder="如 /notices" />
        </el-form-item>
        <el-form-item label="排序">
          <el-input-number v-model="form.sortOrder" :min="0" :max="9999" />
        </el-form-item>
        <el-form-item label="启用">
          <el-switch v-model="form.enabled" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dlg = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="save">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import http from '../../api/http'
import { schemaLabels } from '../../utils/domainSchema.js'

const labels = schemaLabels()
const list = ref([])
const loading = ref(false)
const dlg = ref(false)
const saving = ref(false)
const form = reactive({
  id: null,
  slot: 'home',
  title: '',
  lead: '',
  imageUrl: '',
  linkUrl: '',
  sortOrder: 0,
  enabled: true,
})

async function load() {
  loading.value = true
  try {
    const res = await http.get('/api/banners', { params: { all: true } })
    list.value = Array.isArray(res.data) ? res.data : []
  } finally {
    loading.value = false
  }
}

function openEdit(row) {
  if (row) {
    Object.assign(form, {
      id: row.id,
      slot: row.slot || 'home',
      title: row.title || '',
      lead: row.lead || '',
      imageUrl: row.imageUrl || row.src || '',
      linkUrl: row.linkUrl || '',
      sortOrder: Number(row.sortOrder) || 0,
      enabled: !!row.enabled,
    })
  } else {
    Object.assign(form, {
      id: null,
      slot: 'home',
      title: '',
      lead: '',
      imageUrl: '',
      linkUrl: '',
      sortOrder: 0,
      enabled: true,
    })
  }
  dlg.value = true
}

async function save() {
  if (!form.title?.trim()) {
    ElMessage.warning('请填写标题')
    return
  }
  saving.value = true
  try {
    const body = {
      slot: form.slot,
      title: form.title,
      lead: form.lead,
      imageUrl: form.imageUrl,
      linkUrl: form.linkUrl,
      sortOrder: form.sortOrder,
      enabled: form.enabled,
    }
    if (form.id) await http.put(`/api/banners/${form.id}`, body)
    else await http.post('/api/banners', body)
    ElMessage.success('已保存')
    dlg.value = false
    load()
  } finally {
    saving.value = false
  }
}

async function remove(row) {
  await ElMessageBox.confirm('确认删除该广告位？', '删除')
  await http.delete(`/api/banners/${row.id}`)
  ElMessage.success('已删除')
  load()
}

onMounted(load)
</script>

<style scoped>
.toolbar {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
}
.title { margin: 0; flex: 1; font-size: 18px; }
.empty { margin-top: 16px; color: var(--portal-muted, #909399); font-size: 13px; }
</style>
