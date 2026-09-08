<template>
  <div>
    <p class="lead">{{ pageLead }}</p>
    <div class="table-scroll">
      <el-table :data="list" stripe>
        <el-table-column prop="code" label="编码" width="160" />
        <el-table-column prop="title" label="标题" min-width="140" show-overflow-tooltip />
        <el-table-column prop="body" label="正文" min-width="220" show-overflow-tooltip />
        <el-table-column label="启用" width="90">
          <template #default="{ row }">
            <el-tag :type="row.enabled ? 'success' : 'info'" size="small">
              {{ row.enabled ? '启用' : '停用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="updatedAt" label="更新时间" width="170" />
        <el-table-column label="操作" width="100" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>
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
    <el-dialog v-model="visible" title="编辑消息模板" width="560px" destroy-on-close>
      <el-form label-position="top">
        <el-form-item label="编码">
          <el-input :model-value="form.code" disabled />
        </el-form-item>
        <el-form-item label="标题" required>
          <el-input v-model="form.title" maxlength="128" show-word-limit />
        </el-form-item>
        <el-form-item label="正文" required>
          <el-input v-model="form.body" type="textarea" :rows="5" maxlength="512" show-word-limit />
          <p class="hint">占位符：{{ '{{subject}}' }} {{ '{{note}}' }} {{ '{{note_suffix}}' }} {{ '{{passCode}}' }}</p>
        </el-form-item>
        <el-form-item label="启用">
          <el-switch v-model="form.enabled" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="visible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="save">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
/** 站内消息模板：总管维护审单通过/驳回文案（E-06） */
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import http from '../../api/http'
import { getSchema } from '../../utils/domainSchema.js'

const labels = computed(() => getSchema()?.labels || {})
const pageLead = computed(
  () =>
    labels.value.messageTemplatesPageLead ||
    '维护站内消息标题与正文模板；审核通过/驳回时优先使用模板。',
)

const list = ref([])
const page = ref(1)
const size = ref(20)
const total = ref(0)
const visible = ref(false)
const saving = ref(false)
const form = reactive({ id: 0, code: '', title: '', body: '', enabled: true })

async function load() {
  const res = await http.get('/api/admin/message-templates', {
    params: { page: page.value, size: size.value },
  })
  list.value = res.data?.list || []
  total.value = res.data?.total || 0
}

function openEdit(row) {
  form.id = row.id
  form.code = row.code
  form.title = row.title || ''
  form.body = row.body || ''
  form.enabled = !!row.enabled
  visible.value = true
}

async function save() {
  if (!form.title.trim() || !form.body.trim()) {
    ElMessage.warning('标题与正文不能为空')
    return
  }
  saving.value = true
  try {
    await http.put(`/api/admin/message-templates/${form.id}`, {
      title: form.title.trim(),
      body: form.body.trim(),
      enabled: form.enabled,
    })
    ElMessage.success('已保存')
    visible.value = false
    await load()
  } catch (e) {
    ElMessage.error(e?.response?.data?.message || e?.message || '保存失败')
  } finally {
    saving.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.lead { margin: 0 0 10px; color: var(--portal-muted, #606266); font-size: 13px; }
.pager { margin-top: 12px; display: flex; justify-content: flex-end; }
.hint { margin: 6px 0 0; color: var(--portal-muted, #94a3b8); font-size: 12px; }
</style>
