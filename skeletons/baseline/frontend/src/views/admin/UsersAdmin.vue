<template>
  <div>
    <div class="toolbar">
      <el-radio-group v-model="scope" size="default" @change="load">
        <el-radio-button value="users">{{ userLabel }}</el-radio-button>
        <el-radio-button value="subadmins">{{ subLabel }}</el-radio-button>
        <el-radio-button value="all">全部</el-radio-button>
      </el-radio-group>
      <el-input v-model="keyword" clearable placeholder="用户名 / 昵称 / 手机 / 档案" style="width:240px" @keyup.enter="load" />
      <el-button type="primary" @click="load">查询</el-button>
      <el-button @click="load">刷新</el-button>
    </div>
    <el-table :data="list" stripe>
      <el-table-column prop="username" label="用户名" width="110" />
      <el-table-column label="姓名" width="100">
        <template #default="{ row }">{{ extraOf(row, 'realName') || row.nickname || '—' }}</template>
      </el-table-column>
      <el-table-column prop="phone" label="手机" width="120" />
      <el-table-column
        v-for="col in adminCols"
        :key="col.key"
        :label="col.label"
        min-width="110"
        show-overflow-tooltip
      >
        <template #default="{ row }">{{ extraOf(row, col.key) || '—' }}</template>
      </el-table-column>
      <el-table-column label="身份" width="110">
        <template #default="{ row }">
          <el-tag size="small" :type="isSub(row) ? 'warning' : 'info'" effect="plain">
            {{ isSub(row) ? subLabel : userLabel }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="enabled" label="状态" width="90">
        <template #default="{ row }">
          <el-tag size="small" :type="row.enabled ? 'success' : 'info'" effect="plain">
            {{ row.enabled ? '正常' : '已停用' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" min-width="280" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
          <el-button link type="warning" @click="resetPwd(row)">重置密码</el-button>
          <el-button link :type="row.enabled ? 'danger' : 'success'" @click="toggle(row)">
            {{ row.enabled ? '停用' : '启用' }}
          </el-button>
          <el-button v-if="!isSub(row)" link type="primary" @click="appoint(row)">任命{{ subLabel }}</el-button>
          <el-button v-else link type="danger" @click="revoke(row)">撤销任命</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="visible" :title="'编辑' + (isSub(form) ? subLabel : userLabel)" width="640px" destroy-on-close>
      <el-form :model="form" label-position="top" require-asterisk-position="right" class="edit-form">
        <div class="grid">
          <el-form-item label="用户名"><el-input :model-value="form.username" disabled /></el-form-item>
          <el-form-item label="昵称"><el-input v-model="form.nickname" maxlength="32" /></el-form-item>
          <el-form-item
            v-for="f in allFields"
            :key="f.key"
            :label="f.label"
            :required="!!f.required"
          >
            <el-select
              v-if="f.type === 'select' && f.storage !== 'phone'"
              v-model="form.extras[f.key]"
              clearable
              style="width: 100%"
            >
              <el-option v-for="opt in f.options || []" :key="opt" :label="opt" :value="opt" />
            </el-select>
            <el-input
              v-else-if="f.storage === 'phone'"
              v-model="form.phone"
              maxlength="20"
            />
            <el-input
              v-else
              v-model="form.extras[f.key]"
              :maxlength="f.maxLength || 64"
            />
          </el-form-item>
        </div>
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
import {
  emptyProfileExtras,
  getSchema,
  profileAdminColumns,
  profileFields,
} from '../../utils/domainSchema.js'

const roles = computed(() => getSchema()?.roles || {})
const userLabel = computed(() => roles.value.user?.label || '用户')
const subLabel = computed(() => roles.value.subadmin?.label || '子管')
const adminCols = computed(() => profileAdminColumns(2))
const allFields = computed(() => profileFields())

const list = ref([])
const keyword = ref('')
const scope = ref('users')
const visible = ref(false)
const form = reactive({
  username: '',
  nickname: '',
  phone: '',
  role: '',
  extras: emptyProfileExtras(),
})

function isSub(row) {
  return row && row.role === 'admin' && !row.superAdmin
}

function extraOf(row, key) {
  if (!row) return ''
  if (row.extras && row.extras[key] != null) return row.extras[key]
  return row[key] || ''
}

async function load() {
  const res = await http.get('/api/admin/users', {
    params: { keyword: keyword.value || undefined, scope: scope.value },
  })
  list.value = res.data
}

function openEdit(row) {
  Object.assign(form, {
    username: row.username,
    nickname: row.nickname || '',
    phone: row.phone || '',
    role: row.role || '',
    extras: { ...emptyProfileExtras(), ...(row.extras || {}) },
  })
  visible.value = true
}

async function save() {
  await http.put(`/api/admin/users/${form.username}`, {
    nickname: form.nickname,
    phone: form.phone,
    extras: form.extras,
  })
  ElMessage.success('已保存')
  visible.value = false
  load()
}

async function toggle(row) {
  const next = !row.enabled
  await ElMessageBox.confirm(next ? '确认启用？' : '停用后将无法登录，确认？', '状态')
  await http.put(`/api/admin/users/${row.username}`, { enabled: next })
  ElMessage.success('已更新')
  load()
}

async function resetPwd(row) {
  const { value } = await ElMessageBox.prompt('请输入新密码', '重置密码', {
    inputValue: '123456',
    inputPattern: /.{6,}/,
    inputErrorMessage: '至少 6 位',
  })
  await http.post(`/api/admin/users/${row.username}/reset-password`, { password: value })
  ElMessage.success('已重置')
}

async function appoint(row) {
  await ElMessageBox.confirm(`任命「${row.nickname || row.username}」为${subLabel.value}？`, '任命')
  await http.post(`/api/admin/users/${row.username}/appoint`)
  ElMessage.success(`已任命为${subLabel.value}`)
  scope.value = 'subadmins'
  load()
}

async function revoke(row) {
  await ElMessageBox.confirm(`撤销「${row.nickname || row.username}」的${subLabel.value}？`, '撤销', {
    type: 'warning',
  })
  await http.post(`/api/admin/users/${row.username}/revoke`)
  ElMessage.success('已撤销任命')
  load()
}

onMounted(load)
</script>

<style scoped>
.toolbar { margin-bottom: 8px; display: flex; flex-wrap: wrap; gap: 8px; align-items: center; }
.grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  column-gap: 16px;
  row-gap: 2px;
}
.edit-form :deep(.el-form-item) { margin-bottom: 12px; }
.edit-form :deep(.el-form-item__label) { margin-bottom: 4px !important; }
@media (max-width: 560px) {
  .grid { grid-template-columns: 1fr; }
}
</style>
