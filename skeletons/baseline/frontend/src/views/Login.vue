<template>
  <AuthShell
    :template="template"
    :title="title"
    :watermark="watermark"
    :eyebrow="labels.authEyebrow || '欢迎使用'"
    :lead="authLead"
    :points="authPoints"
    :heading="heading"
    :sub="sub"
    :note="note"
  >
    <form class="form" @submit.prevent="onLogin">
      <label v-if="showRolePicker" class="field">
        <span class="lab">登录身份<i class="req" aria-hidden="true">*</i></span>
        <el-radio-group v-if="roleWidget === 'radio'" v-model="form.loginAs" class="role-radio">
          <el-radio v-for="opt in roleOptions" :key="opt.id" :value="opt.id" border>
            {{ opt.label }}
          </el-radio>
        </el-radio-group>
        <el-select
          v-else
          v-model="form.loginAs"
          size="large"
          placeholder="请选择登录身份"
          style="width: 100%"
        >
          <el-option v-for="opt in roleOptions" :key="opt.id" :label="opt.label" :value="opt.id" />
        </el-select>
      </label>
      <label class="field">
        <span class="lab">用户名<i class="req" aria-hidden="true">*</i></span>
        <el-input v-model="form.username" size="large" autocomplete="username" placeholder="请输入用户名" />
      </label>
      <label class="field">
        <span class="lab">密码<i class="req" aria-hidden="true">*</i></span>
        <el-input
          v-model="form.password"
          type="password"
          size="large"
          show-password
          autocomplete="current-password"
          placeholder="请输入密码"
        />
      </label>
      <label class="field">
        <span class="lab">验证码<i class="req" aria-hidden="true">*</i></span>
        <div class="captcha-row">
          <el-input v-model="form.captcha" size="large" placeholder="验证码" maxlength="4" />
          <button type="button" class="captcha-btn" title="点击刷新" @click="loadCaptcha">
            <img v-if="captchaImg" :src="captchaImg" alt="验证码" />
            <span v-else>加载中</span>
          </button>
        </div>
      </label>
      <el-button class="submit" type="primary" size="large" native-type="submit" :loading="loading">
        登录
      </el-button>
    </form>
    <template #footer>
      <template v-if="entrySide === 'admin'">
        <span>业务用户？</span>
        <router-link to="/login">返回门户登录</router-link>
      </template>
      <template v-else>
        <span>还没有账号？</span>
        <router-link to="/register">立即注册</router-link>
        <template v-if="entryMode === 'split_entry'">
          <span class="sep">·</span>
          <router-link to="/admin/login">管理端入口</router-link>
        </template>
      </template>
    </template>
  </AuthShell>
</template>

<script setup>
/** 基线登录：入口模式 / 身份控件由工厂交付固定 */
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import http from '../api/http'
import AuthShell from '../components/AuthShell.vue'
import { pickAuthTemplate } from '../utils/authTemplates'
import {
  loginRoleOptions,
  pickAuthEntryMode,
  pickAuthRoleWidget,
} from '../utils/authEntry'
import { FACTORY_DELIVERED } from '../factoryDelivered.js'
import { schemaLabels } from '../utils/domainSchema.js'

const props = defineProps({
  /** portal | admin；路由 /admin/login 时为 admin */
  entrySide: { type: String, default: '' },
})

const router = useRouter()
const route = useRoute()
const template = ref(pickAuthTemplate())
const entryMode = pickAuthEntryMode()
const roleWidget = pickAuthRoleWidget()
const labels = schemaLabels()
const title = ref(
  labels.appName || FACTORY_DELIVERED.title || import.meta.env.VITE_APP_TITLE || '毕设系统',
)

const entrySide = computed(() => {
  if (props.entrySide === 'admin' || props.entrySide === 'portal') return props.entrySide
  if (route.path.startsWith('/admin/login')) return 'admin'
  return 'portal'
})

const roleOptions = computed(() => {
  if (entryMode === 'role_pick') return loginRoleOptions('all')
  if (entryMode === 'split_entry' && entrySide.value === 'admin') return loginRoleOptions('admin')
  return loginRoleOptions('portal')
})

const showRolePicker = computed(() => {
  if (entryMode === 'unified') return false
  if (entryMode === 'split_entry' && entrySide.value === 'portal') return false
  return roleOptions.value.length > 0
})

const needLoginAs = computed(() => entryMode !== 'unified')

const heading = computed(() => (entrySide.value === 'admin' ? '管理端登录' : '登录'))
const sub = computed(() =>
  entrySide.value === 'admin' ? '使用管理账号进入后台' : '使用已有账号进入系统',
)
const note = computed(() => {
  if (entryMode === 'role_pick') return '请选择与账号匹配的登录身份；演示账号见部署说明。'
  if (entryMode === 'split_entry' && entrySide.value === 'admin') {
    return '管理端仅接受总管/子管账号；业务用户请走门户登录。'
  }
  if (entryMode === 'split_entry') return '门户仅接受业务用户；管理员请走管理端入口。'
  return '演示账号见部署说明；新用户可先注册再登录。'
})
const authLead = computed(() => {
  if (entrySide.value === 'admin') return '管理端独立入口，按岗位身份登录后台。'
  return labels.authLead || '验证码登录，开放注册；登录后可使用系统基础能力。'
})
const authPoints = computed(() => {
  if (entrySide.value === 'admin') return ['身份校验', '总管/子管分权', '验证码登录']
  if (Array.isArray(labels.authPoints) && labels.authPoints.length) return labels.authPoints
  return ['验证码登录', '开放注册', '个人资料与头像']
})

const captchaImg = ref('')
const loading = ref(false)
const form = reactive({ username: '', password: '', captcha: '', loginAs: '' })

watch(
  roleOptions,
  (opts) => {
    if (!opts.length) return
    if (!opts.some((o) => o.id === form.loginAs)) form.loginAs = opts[0].id
  },
  { immediate: true },
)

const watermark = computed(() => {
  const brow = (labels.authEyebrow || '').trim()
  if (brow && brow.length <= 8) return brow
  const t = (title.value || '系统').trim()
  return t.length <= 6 ? t : t.slice(0, 4)
})

function persist(user) {
  localStorage.setItem('token', user.token)
  localStorage.setItem('role', user.role)
  localStorage.setItem('username', user.username)
  localStorage.setItem('nickname', user.nickname || '')
  localStorage.setItem('avatarUrl', user.avatarUrl || '')
  localStorage.setItem('profileEditable', String(!!user.profileEditable))
  localStorage.setItem('superAdmin', String(!!user.superAdmin))
}

async function loadCaptcha() {
  const res = await http.get('/api/auth/captcha')
  captchaImg.value = res.data.image
}

async function onLogin() {
  if (loading.value) return
  if (showRolePicker.value && !form.loginAs) {
    ElMessage.warning('请选择登录身份')
    return
  }
  if (!form.username || !form.password) {
    ElMessage.warning('请填写用户名和密码')
    return
  }
  if (!form.captcha) {
    ElMessage.warning('请填写验证码')
    return
  }
  loading.value = true
  try {
    const payload = {
      username: form.username,
      password: form.password,
      captcha: form.captcha,
    }
    if (needLoginAs.value) {
      // split 门户无选择器时仍带 loginAs=user，防止管理号误登
      payload.loginAs =
        form.loginAs || (entrySide.value === 'admin' ? 'staff' : 'user')
    }
    const res = await http.post('/api/auth/login', payload)
    persist(res.data)
    ElMessage.success('登录成功')
    router.push(res.data.role === 'admin' ? '/admin' : '/')
  } catch {
    form.captcha = ''
    loadCaptcha()
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  // 非分端模式不提供独立管理登录页
  if (entryMode !== 'split_entry' && entrySide.value === 'admin') {
    router.replace('/login')
    return
  }
  if (typeof route.query.u === 'string' && route.query.u) form.username = route.query.u
  // 已有 schema.appName / 交付标题时勿被 /api/meta 的「毕设系统」盖掉
  const hasName = !!(labels.appName || FACTORY_DELIVERED.title)
  if (!hasName) {
    try {
      const meta = await http.get('/api/meta')
      if (meta.data?.title) title.value = meta.data.title
    } catch { /* ignore */ }
  }
  // 分端时已登录用户打开对方登录页 → 按角色回跳
  const token = localStorage.getItem('token')
  const role = localStorage.getItem('role')
  if (token && role === 'admin' && entrySide.value === 'admin') {
    router.replace('/admin')
    return
  }
  if (token && role !== 'admin' && entrySide.value === 'portal') {
    router.replace('/')
    return
  }
  loadCaptcha()
})
</script>

<style scoped>
.form { display: flex; flex-direction: column; gap: 14px; }
.field { display: flex; flex-direction: column; gap: 6px; }
.lab {
  font-size: 13px;
  font-weight: 500;
  color: var(--portal-ink, #15202b);
}
.req {
  color: var(--el-color-danger, #f56c6c);
  margin-left: 2px;
  font-style: normal;
  font-weight: 600;
}
.form :deep(.el-input__wrapper) {
  border-radius: 10px;
  box-shadow: 0 0 0 1px var(--portal-line, #d5dde3) inset;
  background: color-mix(in srgb, var(--portal-surface, #fff) 88%, var(--portal-bg, #eef3f5));
}
.form :deep(.el-input__wrapper:hover),
.form :deep(.el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 1px var(--portal-accent, #0b6e75) inset;
}
.role-radio {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.role-radio :deep(.el-radio) {
  margin-right: 0;
  border-radius: 10px;
}
.captcha-row { display: flex; gap: 10px; align-items: stretch; }
.captcha-btn {
  width: 112px;
  flex-shrink: 0;
  border: 1px solid var(--portal-line, #d5dde3);
  border-radius: 10px;
  background: var(--portal-accent-soft, #d7eef0);
  cursor: pointer;
  padding: 0;
  overflow: hidden;
  display: grid;
  place-items: center;
  color: var(--portal-accent, #0b6e75);
  font-size: 12px;
}
.captcha-btn img {
  width: 100%;
  height: 40px;
  object-fit: cover;
  display: block;
}
.submit {
  margin-top: 8px;
  height: 44px !important;
  border-radius: 10px !important;
  font-weight: 600;
  background: var(--portal-accent, #0b6e75) !important;
  border-color: var(--portal-accent, #0b6e75) !important;
}
.sep { margin: 0 6px; color: var(--portal-muted, #8a9aa6); }
</style>
