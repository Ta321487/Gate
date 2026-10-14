<template>
  <AuthShell
    :template="template"
    :title="title"
    :watermark="watermark"
    eyebrow="账号激活"
    :lead="labels.mustActivateEmailHint || '请先用站内激活码完成账号激活'"
    :points="[]"
    heading="激活账号"
    sub="激活码已发到站内消息；注册成功页也会展示"
  >
    <form class="form" @submit.prevent="onSubmit">
      <label class="field">
        <span class="lab">用户名<i class="req" aria-hidden="true">*</i></span>
        <el-input v-model="form.username" size="large" autocomplete="username" />
      </label>
      <label class="field">
        <span class="lab">{{ labels.activationCodeLabel || '激活码' }}<i class="req" aria-hidden="true">*</i></span>
        <el-input v-model="form.code" size="large" maxlength="16" autocomplete="one-time-code" />
      </label>
      <el-button class="submit" type="primary" size="large" native-type="submit" :loading="loading">
        激活并去登录
      </el-button>
    </form>
    <template #footer>
      <router-link to="/login">返回登录</router-link>
    </template>
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
import { clearAuthStorage, setMustActivateEmail } from '../utils/session.js'

const router = useRouter()
const route = useRoute()
const template = ref(pickAuthTemplate())
const labels = schemaLabels()
const title = ref(labels.appName || APP_DELIVERED.title || '系统')
const watermark = computed(() => (title.value || '系统').slice(0, 4))
const loading = ref(false)
const form = reactive({
  username: typeof route.query.u === 'string' ? route.query.u : '',
  code: typeof route.query.code === 'string' ? route.query.code : '',
})

async function onSubmit() {
  if (loading.value) return
  if (!form.username || !form.code) {
    ElMessage.warning('请填写用户名与激活码')
    return
  }
  loading.value = true
  try {
    await http.post('/api/auth/activate', {
      username: form.username,
      activationCode: form.code,
    })
    setMustActivateEmail(false)
    clearAuthStorage()
    ElMessage.success('激活成功，请登录')
    router.replace({ path: '/login', query: { u: form.username } })
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.form { display: flex; flex-direction: column; gap: 0.85rem; }
.field { display: flex; flex-direction: column; gap: 0.35rem; }
.lab { font-size: 0.85rem; color: #475569; }
.req { color: #dc2626; font-style: normal; margin-left: 2px; }
.submit { width: 100%; margin-top: 0.4rem; }
</style>
