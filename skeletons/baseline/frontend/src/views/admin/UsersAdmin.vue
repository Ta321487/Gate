<template>
  <div>
    <div class="toolbar">
      <el-radio-group v-model="scope" size="default" @change="load">
        <el-radio-button value="users">{{ userLabel }}</el-radio-button>
        <el-radio-button value="subadmins">{{ subLabel }}</el-radio-button>
        <el-radio-button value="all">全部</el-radio-button>
      </el-radio-group>
      <el-input v-model="keyword" clearable placeholder="用户名 / 昵称 / 手机 / 资料" style="width:240px" @keyup.enter="load" />
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
      <el-table-column label="身份" width="140">
        <template #default="{ row }">
          <el-tag size="small" :type="isSub(row) ? 'warning' : 'info'" effect="plain">
            {{ identityLabel(row) }}
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
          <el-button
            v-if="walletOn && !isSub(row)"
            link
            type="success"
            @click="recharge(row)"
          >充值</el-button>
          <el-button link type="warning" @click="resetPwd(row)">重置密码</el-button>
          <el-button link :type="row.enabled ? 'danger' : 'success'" @click="toggle(row)">
            {{ row.enabled ? '停用' : '启用' }}
          </el-button>
          <el-button
            v-if="canAppointUser && !isSub(row) && scope === 'all'"
            link
            type="primary"
            @click="openAppoint(row)"
          >任命岗位</el-button>
          <el-button
            v-else-if="canAppoint && isSub(row) && canRevokeRow(row)"
            link
            type="danger"
            @click="revoke(row)"
          >撤销任命</el-button>
          <el-tooltip
            v-else-if="canAppoint && isSub(row) && !canRevokeRow(row)"
            content="该岗位唯一账号，撤销后无法再任命业务用户顶替"
            placement="top"
          >
            <el-button link type="info" disabled>撤销任命</el-button>
          </el-tooltip>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="appointVisible" title="任命岗位" width="420px" destroy-on-close>
      <p class="appoint-tip">将「{{ appointTarget?.nickname || appointTarget?.username }}」任命为：</p>
      <el-select v-model="appointPostId" placeholder="选择岗位" style="width: 100%">
        <el-option
          v-for="p in postOptions"
          :key="p.id"
          :label="`${p.label}（${p.kind === 'worker' ? '业务员工' : '子管理'}）`"
          :value="p.id"
        />
      </el-select>
      <template #footer>
        <el-button @click="appointVisible = false">取消</el-button>
        <el-button type="primary" :disabled="!appointPostId" @click="confirmAppoint">确认任命</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="visible" :title="'编辑' + (isSub(form) ? identityLabel(form) : userLabel)" width="640px" destroy-on-close>
      <el-form :model="form" label-position="top" require-asterisk-position="right" class="edit-form">
        <div class="grid">
          <el-form-item label="用户名"><el-input :model-value="form.username" disabled /></el-form-item>
          <el-form-item label="昵称"><el-input v-model="form.nickname" maxlength="32" /></el-form-item>
          <el-form-item
            v-for="f in visibleFields"
            :key="f.key"
            :label="f.label"
            :required="isProfileFieldRequired(f, form.extras)"
          >
            <el-select
              v-if="f.type === 'select' && f.storage !== 'phone'"
              v-model="form.extras[f.key]"
              clearable
              style="width: 100%"
              @change="onIdentityMaybe(f)"
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
  isWalletEnabled,
  profileAdminColumns,
  profileFields,
} from '../../utils/domainSchema.js'
import { isProfileFieldRequired, isProfileFieldVisible } from '../../utils/profileValidate.js'
import { findStaffPost, staffPostLabel, staffPosts } from '../../utils/staffPosts.js'

const roles = computed(() => getSchema()?.roles || {})
const userLabel = computed(() => roles.value.user?.label || '用户')
const subLabel = computed(() => roles.value.subadmin?.label || '子管')
const postOptions = computed(() => staffPosts())
/** 有岗位表；撤销仍可用 */
const canAppoint = computed(() => postOptions.value.length > 0)
/** 是否允许把门户业务用户升岗；缺省按 false（须 bake 显式 true） */
const allowAppointFromUsers = computed(() => roles.value.allowAppointFromUsers === true)
const canAppointUser = computed(() => canAppoint.value && allowAppointFromUsers.value)
const walletOn = computed(() => isWalletEnabled())
const adminCols = computed(() => profileAdminColumns())
const allFields = computed(() => profileFields())
const visibleFields = computed(() =>
  allFields.value.filter((f) => isProfileFieldVisible(f, form.extras)),
)
const appointVisible = ref(false)
const appointTarget = ref(null)
const appointPostId = ref('')

/** 禁任命域：同岗仅剩一名启用中账号时不可撤/停用（与后端 assertNotSoleActiveStaff 一致） */
function isSoleActiveStaff(row) {
  if (allowAppointFromUsers.value) return false
  if (!isSub(row) || !row.enabled) return false
  const post = (row.staffPost || '').toString()
  const peers = list.value.filter(
    (r) => isSub(r) && r.enabled && (r.staffPost || '').toString() === post,
  )
  return peers.length <= 1
}

function canRevokeRow(row) {
  if (!isSub(row)) return false
  if (allowAppointFromUsers.value) return true
  return !isSoleActiveStaff(row)
}

async function toggle(row) {
  const next = !row.enabled
  if (!next && isSoleActiveStaff(row)) {
    ElMessage.warning('该岗位唯一启用账号，停用后无法再任命业务用户顶替')
    return
  }
  await ElMessageBox.confirm(next ? '确认启用？' : '停用后将无法登录，确认？', '状态')
  await http.put(`/api/admin/users/${row.username}`, { enabled: next })
  ElMessage.success('已更新')
  load()
}

function onIdentityMaybe(f) {
  const drivers = new Set(['identityType', 'readerType', 'ownerType', 'deliveryType', 'pickupType'])
  if (!drivers.has(f?.key)) return
  for (const x of allFields.value) {
    if (x.key === f.key || !x.visibleWhen) continue
    if (!isProfileFieldVisible(x, form.extras)) form.extras[x.key] = ''
  }
}

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

function identityLabel(row) {
  if (!isSub(row)) return userLabel.value
  return staffPostLabel(row.staffPost, subLabel.value)
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

async function resetPwd(row) {
  const { value } = await ElMessageBox.prompt('请输入新密码', '重置密码', {
    inputValue: '123456',
    inputPattern: /.{6,}/,
    inputErrorMessage: '至少 6 位',
  })
  await http.post(`/api/admin/users/${row.username}/reset-password`, { password: value })
  ElMessage.success('已重置，对方需用新密码重新登录')
}

async function recharge(row) {
  const { value } = await ElMessageBox.prompt(
    `为「${row.nickname || row.username}」充值演示余额（元，非真支付）`,
    '演示余额充值',
    {
      inputValue: '100',
      inputPattern: /^\d+(\.\d{1,2})?$/,
      inputErrorMessage: '请输入有效金额',
    },
  )
  const amount = Number(value)
  if (!(amount > 0)) {
    ElMessage.warning('金额须大于 0')
    return
  }
  await http.post('/api/admin/loyalty/recharge', { username: row.username, amount })
  ElMessage.success(`已充值 ¥${amount.toFixed(2)}`)
}

function openAppoint(row) {
  appointTarget.value = row
  appointPostId.value = postOptions.value[0]?.id || ''
  appointVisible.value = true
}

async function confirmAppoint() {
  const row = appointTarget.value
  const post = findStaffPost(appointPostId.value) || postOptions.value.find((p) => p.id === appointPostId.value)
  if (!row || !post) return
  await http.post(`/api/admin/users/${row.username}/appoint`, {
    staffPost: post.id,
    staffKind: post.kind || 'clerk',
  })
  ElMessage.success(`已任命为${post.label}`)
  appointVisible.value = false
  scope.value = 'subadmins'
  load()
}

async function revoke(row) {
  const label = identityLabel(row)
  await ElMessageBox.confirm(`撤销「${row.nickname || row.username}」的${label}？`, '撤销', {
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
.appoint-tip { margin: 0 0 12px; color: #606266; font-size: 14px; }
@media (max-width: 560px) {
  .grid { grid-template-columns: 1fr; }
}
</style>
