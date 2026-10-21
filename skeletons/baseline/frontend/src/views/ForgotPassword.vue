<template>
  <AuthShell
    :template="template"
    :title="title"
    :watermark="watermark"
    :eyebrow="labels.forgotPasswordLink || '忘记密码'"
    lead="通过密保问题重设密码后，请使用新密码登录。"
    :points="[]"
    heading="找回密码"
    sub="请依次填写用户名、密保答案与新密码"
  >
    <form class="form" @submit.prevent="onSubmit">
      <label class="field">
        <span class="lab">用户名<i class="req" aria-hidden="true">*</i></span>
        <el-input v-model="form.username" autocomplete="username" @blur="loadQuestion" />
      </label>
      <label class="field">
        <span class="lab">{{ labels.securityQuestionLabel || '密保问题' }}</span>
        <el-input :model-value="question || '请先填写用户名'" disabled />
      </label>
      <label class="field">
        <span class="lab">{{ labels.securityAnswerLabel || '密保答案' }}<i class="req" aria-hidden="true">*</i></span>
        <el-input v-model="form.securityAnswer" autocomplete="off" />
      </label>
      <label class="field">
        <span class="lab">新密码<i class="req" aria-hidden="true">*</i></span>
        <el-input v-model="form.newPassword" type="password" show-password autocomplete="new-password" />
        <span class="hint">{{ strengthHint }}</span>
      </label>
      <label class="field">
        <span class="lab">确认密码<i class="req" aria-hidden="true">*</i></span>
        <el-input v-model="form.confirmPassword" type="password" show-password autocomplete="new-password" />
      </label>
      <label class="field">
        <span class="lab">验证码<i class="req" aria-hidden="true">*</i></span>
        <div class="captcha-row">
          <el-input v-model="form.captcha" maxlength="4" />
          <button type="button" class="captcha-btn" @click="loadCaptcha">
            <img v-if="captchaImg" :src="captchaImg" alt="验证码" />
            <span v-else>加载中</span>
          </button>
        </div>
      </label>
      <el-button class="submit" type="primary" native-type="submit" :loading="loading">
        重设密码
      </el-button>
    </form>
    <template #footer>
      <router-link to="/login">返回登录</router-link>
    </template>
  </AuthShell>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import http from '../api/http'
import AuthShell from '../components/AuthShell.vue'
import { pickAuthTemplate } from '../utils/authTemplates'
import { APP_DELIVERED } from '../appDelivered.js'
import { schemaLabels } from '../utils/domainSchema.js'
import { authPolicy } from '../utils/session.js'

const router = useRouter()
const template = ref(pickAuthTemplate())
const labels = schemaLabels()
const title = ref(labels.appName || APP_DELIVERED.title || '系统')
const watermark = computed(() => (title.value || '系统').slice(0, 4))
const strengthHint = computed(() => {
  const n = Number(authPolicy().passwordMinLength) || 6
  return labels.passwordStrengthHint || `密码至少 ${n} 位，建议包含字母和数字`
})

const captchaImg = ref('')
const question = ref('')
const loading = ref(false)
const form = reactive({
  username: '',
  securityAnswer: '',
  newPassword: '',
  confirmPassword: '',
  captcha: '',
})

async function loadCaptcha() {
  const res = await http.get('/api/auth/captcha')
  captchaImg.value = res.data.image
}

async function loadQuestion() {
  const u = form.username.trim()
  if (!u) {
    question.value = ''
    return
  }
  try {
    const res = await http.get('/api/auth/security-question', { params: { username: u } })
    question.value = res.data?.question || ''
  } catch {
    question.value = ''
  }
}

async function onSubmit() {
  if (loading.value) return
  if (!form.username || !form.securityAnswer || !form.newPassword || !form.captcha) {
    ElMessage.warning('请填写完整信息')
    return
  }
  if (form.newPassword !== form.confirmPassword) {
    ElMessage.warning('两次密码不一致')
    return
  }
  loading.value = true
  try {
    await http.post('/api/auth/reset-by-security', {
      username: form.username.trim(),
      securityAnswer: form.securityAnswer,
      newPassword: form.newPassword,
      confirmPassword: form.confirmPassword,
      captcha: form.captcha,
    })
    ElMessage.success('密码已重设，请重新登录')
    router.replace({ path: '/login', query: { reason: 'password' } })
  } catch {
    form.captcha = ''
    loadCaptcha()
  } finally {
    loading.value = false
  }
}

onMounted(loadCaptcha)
</script>

<style scoped>
.form { display: flex; flex-direction: column; gap: 0.85rem; }
.field { display: flex; flex-direction: column; gap: 0.35rem; }
.lab { font-size: 0.9rem; color: var(--el-text-color-regular); }
.req { color: var(--el-color-danger); margin-left: 0.15rem; font-style: normal; }
.hint { font-size: 0.8rem; color: var(--el-text-color-secondary); }
.captcha-row { display: flex; gap: 0.5rem; align-items: center; }
.captcha-btn {
  border: 1px solid var(--el-border-color);
  background: #fff;
  border-radius: 6px;
  padding: 0;
  width: 108px;
  height: 40px;
  overflow: hidden;
  cursor: pointer;
}
.captcha-btn img { width: 100%; height: 100%; object-fit: cover; display: block; }
.submit { width: 100%; margin-top: 0.25rem; }
</style>
