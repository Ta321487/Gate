<template>
  <AuthShell
    :template="template"
    :title="title"
    :watermark="watermark"
    :eyebrow="labels.authEyebrow || '欢迎使用'"
    :lead="labels.authLead || '验证码登录，开放注册；登录后可使用系统基础能力。'"
    :points="authPoints"
    heading="登录"
    sub="使用已有账号进入系统"
    note="演示账号见部署说明；新用户可先注册再登录。"
  >
    <form class="form" @submit.prevent="onLogin">
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
      <span>还没有账号？</span>
      <router-link to="/register">立即注册</router-link>
    </template>
  </AuthShell>
</template>

<script setup>
/** 基线登录：随机鉴权模板（同会话固定） */
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import http from '../api/http'
import AuthShell from '../components/AuthShell.vue'
import { pickAuthTemplate } from '../utils/authTemplates'
import { FACTORY_DELIVERED } from '../factoryDelivered.js'
import { schemaLabels } from '../utils/domainSchema.js'

const router = useRouter()
const route = useRoute()
const template = ref(pickAuthTemplate())
const labels = schemaLabels()
const title = ref(
  labels.appName || FACTORY_DELIVERED.title || import.meta.env.VITE_APP_TITLE || '毕设系统',
)
const authPoints = computed(() =>
  Array.isArray(labels.authPoints) && labels.authPoints.length
    ? labels.authPoints
    : ['验证码登录', '开放注册', '个人资料与头像'],
)
const captchaImg = ref('')
const loading = ref(false)
const form = reactive({ username: '', password: '', captcha: '' })

// 水印宜短；勿截长产品名成「校园网故障报修管」
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
    const res = await http.post('/api/auth/login', form)
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
  if (typeof route.query.u === 'string' && route.query.u) form.username = route.query.u
  // 已有 schema.appName / 交付标题时勿被 /api/meta 的「毕设系统」盖掉
  const hasName = !!(labels.appName || FACTORY_DELIVERED.title)
  if (!hasName) {
    try {
      const meta = await http.get('/api/meta')
      if (meta.data?.title) title.value = meta.data.title
    } catch { /* ignore */ }
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
</style>
