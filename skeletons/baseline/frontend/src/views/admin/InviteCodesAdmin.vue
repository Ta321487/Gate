<template>
  <div>
    <div class="toolbar">
      <h2 class="title">{{ labels.inviteCodesMenu || '邀请码' }}</h2>
      <el-button type="primary" @click="openCreate">新建</el-button>
      <el-button @click="load">刷新</el-button>
    </div>
    <div class="table-scroll">
      <el-table :data="list" stripe v-loading="loading">
        <el-table-column prop="code" label="邀请码" width="140" />
        <el-table-column prop="label" label="说明" min-width="140" />
        <el-table-column label="用量" width="120">
          <template #default="{ row }">
            {{ row.usedCount }}{{ row.maxUses > 0 ? ` / ${row.maxUses}` : ' / 不限' }}
          </template>
        </el-table-column>
        <el-table-column label="状态" width="90">
          <template #default="{ row }">
            <el-tag size="small" :type="row.enabled ? 'success' : 'info'">
              {{ row.enabled ? '启用' : '停用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="createdAt" label="创建时间" width="170" />
        <el-table-column label="操作" width="100" fixed="right">
          <template #default="{ row }">
            <el-button link type="warning" @click="toggle(row)">
              {{ row.enabled ? '停用' : '启用' }}
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <el-dialog v-model="dlg" title="新建邀请码" width="420px">
      <el-form label-width="80px">
        <el-form-item label="邀请码" required>
          <el-input v-model="form.code" maxlength="64" />
        </el-form-item>
        <el-form-item label="说明">
          <el-input v-model="form.label" maxlength="128" />
        </el-form-item>
        <el-form-item label="次数上限">
          <el-input-number v-model="form.maxUses" :min="0" />
          <span class="hint">0 表示不限制</span>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dlg = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="create">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import http from '../../api/http'
import { schemaLabels } from '../../utils/domainSchema.js'

const labels = schemaLabels()
const list = ref([])
const loading = ref(false)
const dlg = ref(false)
const saving = ref(false)
const form = reactive({ code: '', label: '', maxUses: 0 })

async function load() {
  loading.value = true
  try {
    const res = await http.get('/api/admin/invite-codes')
    list.value = res.data || []
  } finally {
    loading.value = false
  }
}

function openCreate() {
  form.code = ''
  form.label = ''
  form.maxUses = 0
  dlg.value = true
}

async function create() {
  if (!form.code.trim()) {
    ElMessage.warning('请填写邀请码')
    return
  }
  saving.value = true
  try {
    await http.post('/api/admin/invite-codes', {
      code: form.code.trim(),
      label: form.label.trim(),
      maxUses: form.maxUses,
    })
    ElMessage.success('已创建')
    dlg.value = false
    load()
  } finally {
    saving.value = false
  }
}

async function toggle(row) {
  await http.post(`/api/admin/invite-codes/${encodeURIComponent(row.code)}/enabled`, {
    enabled: !row.enabled,
  })
  ElMessage.success(row.enabled ? '已停用' : '已启用')
  load()
}

onMounted(load)
</script>

<style scoped>
.toolbar { display: flex; align-items: center; gap: 12px; margin-bottom: 12px; }
.title { margin: 0; font-size: 1.1rem; flex: 1; }
.table-scroll { overflow-x: auto; }
.hint { margin-left: 8px; color: #64748b; font-size: 12px; }
</style>
