<template>
  <div class="page">
    <el-button link type="primary" class="back" @click="goBack">← 返回</el-button>

    <section class="hero">
      <h1>个人资料</h1>
      <p>维护基本信息与业务资料；改密后需用新密码重新登录。</p>
    </section>

    <p v-if="!form.profileEditable" class="locked">顶级管理员不提供个人资料修改。</p>

    <section class="card identity">
      <div class="avatar-slot">
        <el-avatar :size="72" :src="form.avatarUrl || undefined" class="avatar">
          {{ (form.nickname || form.username || '?').slice(0, 1) }}
        </el-avatar>
        <el-upload
          v-if="form.profileEditable"
          class="avatar-up"
          :show-file-list="false"
          accept="image/*"
          :http-request="onAvatar"
        >
          <button type="button" class="avatar-btn">换头像</button>
        </el-upload>
      </div>
      <div class="who">
        <div class="nick">{{ displayName }}</div>
        <div class="uid">@{{ form.username }}</div>
      </div>
    </section>

    <section v-if="anyLoyalty && loyalty" class="card block loyalty">
      <h2 class="block-title">账户权益（演示）</h2>
      <div class="loy-grid">
        <div v-if="walletOn"><span class="k">演示余额</span><strong>¥{{ Number(loyalty.balanceYuan || 0).toFixed(2) }}</strong></div>
        <div v-if="pointsOn"><span class="k">积分</span><strong>{{ loyalty.points || 0 }}</strong></div>
        <div v-if="tierOn"><span class="k">会员</span><strong>{{ loyalty.memberTierLabel || '—' }}</strong></div>
        <div v-if="tierOn"><span class="k">累计消费</span><strong>¥{{ Number(loyalty.spendTotalYuan || 0).toFixed(2) }}</strong></div>
      </div>
      <p class="loy-hint">非真支付；余额由管理员充值，积分仅随订单完成赠送。</p>
    </section>

    <el-form
      class="form"
      :model="form"
      label-position="top"
      require-asterisk-position="right"
      :disabled="!form.profileEditable"
      @submit.prevent
    >
      <section class="card block">
        <h2 class="block-title">基本信息</h2>
        <div class="grid">
          <el-form-item label="昵称">
            <el-input v-model="form.nickname" placeholder="怎么称呼你" maxlength="32" show-word-limit />
          </el-form-item>
          <el-form-item
            v-for="f in basicFields"
            :key="f.key"
            :label="f.label"
            :required="!!f.required"
          >
            <el-select
              v-if="f.type === 'select' && f.storage !== 'phone'"
              v-model="form.extras[f.key]"
              clearable
              :placeholder="f.placeholder || `请选择${f.label}`"
              style="width: 100%"
            >
              <el-option v-for="opt in f.options || []" :key="opt" :label="opt" :value="opt" />
            </el-select>
            <el-input
              v-else-if="f.storage === 'phone'"
              v-model="form.phone"
              :maxlength="f.maxLength || 20"
              :placeholder="f.placeholder || '手机号'"
            />
            <el-input
              v-else
              v-model="form.extras[f.key]"
              :maxlength="f.maxLength || 64"
              :placeholder="f.placeholder || f.label"
            />
          </el-form-item>
        </div>
      </section>

      <section v-if="bizFields.length" class="card block">
        <h2 class="block-title">业务资料</h2>
        <div class="grid">
          <el-form-item
            v-for="f in bizFields"
            :key="f.key"
            :label="f.label"
            :required="isProfileFieldRequired(f, form.extras)"
            :class="{ wide: isWideField(f) }"
          >
            <el-select
              v-if="f.type === 'select'"
              v-model="form.extras[f.key]"
              clearable
              :placeholder="f.placeholder || `请选择${f.label}`"
              style="width: 100%"
              @change="onBizSelectChange(f)"
            >
              <el-option v-for="opt in f.options || []" :key="opt" :label="opt" :value="opt" />
            </el-select>
            <el-input
              v-else
              v-model="form.extras[f.key]"
              :maxlength="f.maxLength || 64"
              :placeholder="f.placeholder || f.label"
            />
          </el-form-item>
        </div>
      </section>

      <section class="card block">
        <h2 class="block-title">
          登录密码
          <span class="hint">不改请留空</span>
        </h2>
        <div class="grid">
          <el-form-item label="原密码" class="wide">
            <el-input
              v-model="form.oldPassword"
              type="password"
              show-password
              autocomplete="current-password"
              placeholder="修改时必填"
            />
          </el-form-item>
          <el-form-item label="新密码">
            <el-input
              v-model="form.newPassword"
              type="password"
              show-password
              autocomplete="new-password"
              placeholder="至少 6 位"
            />
          </el-form-item>
          <el-form-item label="确认密码">
            <el-input
              v-model="form.confirmPassword"
              type="password"
              show-password
              autocomplete="new-password"
              placeholder="再次输入"
            />
          </el-form-item>
        </div>
      </section>

      <div v-if="form.profileEditable" class="actions">
        <el-button type="primary" size="large" :loading="saving" @click="save">保存修改</el-button>
      </div>
    </el-form>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import http from '../api/http'
import {
  anyLoyaltyEnabled,
  emptyProfileExtras,
  isMemberTierEnabled,
  isPointsEnabled,
  isWalletEnabled,
  profileFields,
} from '../utils/domainSchema.js'
import {
  validateProfileFormats,
  isProfileFieldRequired,
  isProfileFieldVisible,
} from '../utils/profileValidate.js'
import { clearAuthStorage, loginPathForRole, syncProfileDisplay } from '../utils/session.js'

const BASIC_KEYS = new Set(['realName', 'phone', 'email', 'gender'])
const WIDE_KEYS = new Set([
  'officeOrDorm', 'campusAddress', 'receiveAddress', 'deliveryAddress', 'allergyNote', 'defaultRemark',
  'skinOrPrefer', 'usualPlace', 'labOrOffice', 'officeLoc', 'workUnit', 'orgName', 'orgOrClub',
])
const router = useRouter()
const saving = ref(false)
const loyalty = ref(null)
const anyLoyalty = computed(() => anyLoyaltyEnabled())
const walletOn = computed(() => isWalletEnabled())
const pointsOn = computed(() => isPointsEnabled())
const tierOn = computed(() => isMemberTierEnabled())
const allFields = computed(() => profileFields())
const basicFields = computed(() => allFields.value.filter((f) => BASIC_KEYS.has(f.key) || f.storage === 'phone'))
const bizFields = computed(() =>
  allFields.value.filter(
    (f) => !BASIC_KEYS.has(f.key) && f.storage !== 'phone' && isProfileFieldVisible(f, form.extras),
  ),
)

const form = reactive({
  username: '',
  nickname: '',
  phone: '',
  avatarUrl: '',
  extras: emptyProfileExtras(),
  oldPassword: '',
  newPassword: '',
  confirmPassword: '',
  profileEditable: true,
})

const displayName = computed(() =>
  form.extras?.realName || form.nickname || form.username || '未设置姓名',
)

function isWideField(f) {
  return !!(f && (WIDE_KEYS.has(f.key) || (f.maxLength && f.maxLength >= 100)))
}

function onBizSelectChange(f) {
  const drivers = new Set(['identityType', 'readerType', 'ownerType', 'deliveryType', 'pickupType'])
  if (!drivers.has(f?.key)) return
  for (const x of allFields.value) {
    if (x.key === f.key || !x.visibleWhen) continue
    if (!isProfileFieldVisible(x, form.extras)) form.extras[x.key] = ''
  }
}

function clearPasswords() {
  form.oldPassword = ''
  form.newPassword = ''
  form.confirmPassword = ''
}

function goBack() {
  if (window.history.length > 1) router.back()
  else router.push('/')
}

async function load() {
  const res = await http.get('/api/profile')
  const data = res.data || {}
  form.username = data.username || ''
  form.nickname = data.nickname || ''
  form.phone = data.phone || ''
  form.avatarUrl = data.avatarUrl || ''
  form.profileEditable = data.profileEditable !== false
  form.extras = { ...emptyProfileExtras(), ...(data.extras || {}) }
  clearPasswords()
  if (anyLoyalty.value) {
    try {
      const loy = await http.get('/api/loyalty/me')
      loyalty.value = loy.data || null
    } catch {
      loyalty.value = null
    }
  } else {
    loyalty.value = null
  }
}

async function save() {
  for (const f of allFields.value) {
    if (!isProfileFieldVisible(f, form.extras)) continue
    if (!isProfileFieldRequired(f, form.extras)) continue
    if (f.storage === 'phone') {
      if (!form.phone?.trim()) {
        ElMessage.warning(`请填写${f.label}`)
        return
      }
    } else if (!String(form.extras[f.key] || '').trim()) {
      ElMessage.warning(`请填写${f.label}`)
      return
    }
  }
  const fmt = validateProfileFormats(form.phone, form.extras)
  if (fmt) {
    ElMessage.warning(fmt)
    return
  }
  const changingPwd = !!(form.newPassword || form.oldPassword || form.confirmPassword)
  if (changingPwd) {
    if (!form.oldPassword) {
      ElMessage.warning('请填写原密码')
      return
    }
    if (!form.newPassword) {
      ElMessage.warning('请填写新密码')
      return
    }
    if (form.newPassword.length < 6) {
      ElMessage.warning('新密码至少 6 位')
      return
    }
    if (form.newPassword !== form.confirmPassword) {
      ElMessage.warning('两次输入的新密码不一致')
      return
    }
  }
  saving.value = true
  try {
    const body = {
      nickname: form.nickname,
      phone: form.phone,
      extras: form.extras,
    }
    if (changingPwd) {
      body.oldPassword = form.oldPassword
      body.newPassword = form.newPassword
      body.confirmPassword = form.confirmPassword
    }
    const res = await http.put('/api/profile', body)
    const data = res.data || {}
    if (changingPwd || data.requireRelogin) {
      const role = localStorage.getItem('role') || ''
      const staffKind = localStorage.getItem('staffKind') || ''
      clearAuthStorage()
      ElMessage.success('密码已修改，请重新登录')
      router.replace({ path: loginPathForRole(role, staffKind), query: { reason: 'password' } })
      return
    }
    form.extras = { ...emptyProfileExtras(), ...(data.extras || {}) }
    form.phone = data.phone || form.phone
    form.nickname = data.nickname || form.nickname
    form.avatarUrl = data.avatarUrl || form.avatarUrl
    clearPasswords()
    syncProfileDisplay({ nickname: form.nickname, avatarUrl: form.avatarUrl })
    ElMessage.success('已保存')
  } finally {
    saving.value = false
  }
}

async function onAvatar(opt) {
  const fd = new FormData()
  fd.append('file', opt.file)
  const res = await http.post('/api/profile/avatar', fd)
  Object.assign(form, {
    avatarUrl: res.data?.avatarUrl,
    nickname: res.data?.nickname ?? form.nickname,
  })
  clearPasswords()
  syncProfileDisplay({ nickname: form.nickname, avatarUrl: form.avatarUrl })
  ElMessage.success('头像已更新')
}

onMounted(load)
</script>

<style scoped>
.page {
  max-width: 880px;
  margin: 0 auto;
}
.back {
  margin: 0 0 8px;
  padding-left: 0;
}
.hero {
  margin-bottom: 20px;
  padding: 4px 0;
}
.hero h1 {
  margin: 0 0 8px;
  font-size: 28px;
  letter-spacing: -0.03em;
  color: var(--portal-ink, #15202b);
}
.hero p {
  margin: 0;
  color: var(--portal-muted, #6b7c8a);
  font-size: 14px;
  line-height: 1.55;
  max-width: 36em;
}
.locked {
  margin: 0 0 16px;
  padding: 12px 14px;
  border-radius: 10px;
  border: 1px solid var(--portal-line, #dfe7ec);
  background: var(--portal-surface, #fff);
  color: var(--portal-muted, #6b7c8a);
  font-size: 13px;
}
.card {
  background: var(--portal-surface, #fff);
  border: 1px solid var(--portal-line, #dfe7ec);
  border-radius: 12px;
  padding: 20px 22px;
  margin-bottom: 14px;
}
.identity {
  display: flex;
  align-items: center;
  gap: 18px;
}
.avatar-slot { position: relative; flex-shrink: 0; }
.avatar {
  background: var(--portal-cover, linear-gradient(160deg, #0b6e75, #08545a));
  color: #fff;
  font-size: 26px;
  font-weight: 700;
}
.avatar-up {
  position: absolute;
  left: 50%;
  bottom: -6px;
  transform: translateX(-50%);
}
.avatar-btn {
  padding: 2px 10px;
  border: 1px solid var(--portal-line, #dfe7ec);
  border-radius: 8px;
  background: var(--portal-surface, #fff);
  color: var(--portal-accent, #0b6e75);
  font-size: 11px;
  font-weight: 600;
  cursor: pointer;
  white-space: nowrap;
}
.avatar-btn:hover { border-color: var(--portal-accent, #0b6e75); }
.who .nick {
  font-size: 20px;
  font-weight: 700;
  letter-spacing: -0.02em;
  color: var(--portal-ink, #15202b);
  margin-bottom: 4px;
}
.who .uid {
  font-size: 13px;
  color: var(--portal-muted, #6b7c8a);
}
.loy-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
  gap: 12px 16px;
}
.loy-grid .k {
  display: block;
  font-size: 12px;
  color: var(--portal-muted, #6b7c8a);
  margin-bottom: 4px;
}
.loy-grid strong {
  font-size: 18px;
  color: var(--portal-ink, #15202b);
}
.loy-hint {
  margin: 12px 0 0;
  font-size: 12px;
  color: var(--portal-muted, #6b7c8a);
}
.block-title {
  display: flex;
  align-items: baseline;
  gap: 10px;
  margin: 0 0 16px;
  padding-bottom: 10px;
  border-bottom: 1px solid var(--portal-line, #e8eef2);
  font-size: 15px;
  font-weight: 650;
  color: var(--portal-ink, #15202b);
}
.block-title .hint {
  font-size: 12px;
  font-weight: 400;
  color: var(--portal-muted, #8a9aa6);
}
.grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  column-gap: 20px;
  row-gap: 4px;
}
.grid :deep(.el-form-item.wide),
.grid > .wide {
  grid-column: 1 / -1;
}
.form :deep(.el-form-item) {
  margin-bottom: 14px;
}
.form :deep(.el-form-item__label) {
  color: var(--portal-ink, #15202b);
  font-weight: 500;
  line-height: 1.3;
  margin-bottom: 6px !important;
}
.form :deep(.el-input__wrapper) {
  border-radius: 8px;
  box-shadow: 0 0 0 1px var(--portal-line, #d5dde3) inset;
  background: color-mix(in srgb, var(--portal-surface, #fff) 92%, var(--portal-bg, #eef3f5));
}
.form :deep(.el-input__wrapper:hover),
.form :deep(.el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 1px var(--portal-accent, #0b6e75) inset;
}
.actions { padding-top: 4px; }
@media (max-width: 720px) {
  .grid { grid-template-columns: 1fr; }
  .hero h1 { font-size: 22px; }
}
</style>
