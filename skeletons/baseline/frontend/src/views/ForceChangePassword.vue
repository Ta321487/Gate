<template>
  <AuthShell
    :template="template"
    :title="title"
    :watermark="watermark"
    eyebrow="安全提示"
    :lead="labels.mustChangePasswordHint || '请先修改密码后再使用系统'"
    :points="[]"
    heading="修改密码"
    sub="设置新密码后需重新登录"
  >
    <form class="form" @submit.prevent="onSubmit">
      <label class="field">
        <span class="lab">新密码<i class="req" aria-hidden="true">*</i></span>
        <el-input v-model="form.newPassword" type="password" show-password size="large" autocomplete="new-password" />
        <span class="hint">{{ strengthHint }}</span>
      </label>
      <label class="field">
        <span class="lab">确认密码<i class="req" aria-hidden="true">*</i></span>
        <el-input v-model="form.confirmPassword" type="password" show-password size="large" autocomplete="new-password" />
      </label>
      <el-button class="submit" type="primary" size="large" native-type="submit" :loading="loading">
        确认修改
      </el-button>
    </form>
  </AuthShell>
</template>

<script setup>
import { computed, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import http from '../api/http'
import AuthShell from '../components/AuthShell.vue'
import { pickAuthTemplate } from '../utils/authTemplates'
import { APP_DELIVERED } from '../appDelivered.js'
import { schemaLabels } from '../utils/domainSchema.js'
import { authPolicy, clearAuthStorage, setMustChangePassword } from '../utils/session.js'

const router = useRouter()
const route = useRoute()
const template = ref(pickAuthTemplate())
const labels = schemaLabels()
const title = ref(labels.appName || APP_DELIVERED.title || '系统')
const watermark = computed(() => (title.value || '系统').slice(0, 4))
const strengthHint = computed(() => {
  const n = Number(authPolicy().passwordMinLength) || 6
  return labels.passwordStrengthHint || `密码至少 ${n} 位，建议包含字母和数字`
})
const loading = ref(false)
const form = reactive({ newPassword: '', confirmPassword: '' })

async function onSubmit() {
  if (loading.value) return
  if (!form.newPassword || form.newPassword !== form.confirmPassword) {
    ElMessage.warning('请确认两次密码一致')
    return
  }
  loading.value = true
  try {
    await http.post('/api/auth/force-change-password', {
      newPassword: form.newPassword,
      confirmPassword: form.confirmPassword,
    })
    setMustChangePassword(false)
    clearAuthStorage()
    ElMessage.success('密码已修改，请重新登录')
    const redir = typeof route.query.redirect === 'string' ? route.query.redirect : ''
    router.replace({
      path: '/login',
      query: { reason: 'password', ...(redir ? { redirect: redir } : {}) },
    })
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.form { display: flex; flex-direction: column; gap: 0.85rem; }
.field { display: flex; flex-direction: column; gap: 0.35rem; }
.lab { font-size: 0.9rem; color: var(--el-text-color-regular); }
.req { color: var(--el-color-danger); margin-left: 0.15rem; font-style: normal; }
.hint { font-size: 0.8rem; color: var(--el-text-color-secondary); }
.submit { width: 100%; margin-top: 0.25rem; }
</style>
