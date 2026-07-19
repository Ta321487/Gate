<template>
  <AuthShell
    :template="template"
    :title="title"
    :watermark="watermark"
    wide
    eyebrow="开放注册"
    :lead="stepLead"
    :points="[]"
    heading="注册"
    :sub="stepSub"
  >
    <form class="form" @submit.prevent="onPrimary">
      <div v-if="hasProfileStep" class="steps" aria-label="注册步骤">
        <button type="button" class="step" :class="{ on: step === 1 }" @click="goStep(1)">
          <span class="n">1</span>账号
        </button>
        <span class="bar" />
        <button type="button" class="step" :class="{ on: step === 2 }" @click="goStep(2)">
          <span class="n">2</span>资料
        </button>
      </div>

      <!-- 步骤 1：账号与安全（一屏装下） -->
      <div v-show="step === 1" class="pane">
        <div class="grid">
          <label class="field">
            <span class="lab">用户名<i class="req" aria-hidden="true">*</i></span>
            <el-input v-model="form.username" autocomplete="username" placeholder="字母 / 数字 / 下划线" />
          </label>
          <label class="field">
            <span class="lab">昵称</span>
            <el-input v-model="form.nickname" placeholder="选填，默认与用户名相同" />
          </label>
          <label class="field">
            <span class="lab">密码<i class="req" aria-hidden="true">*</i></span>
            <el-input
              v-model="form.password"
              type="password"
              show-password
              autocomplete="new-password"
              placeholder="至少 6 位"
            />
          </label>
          <label class="field">
            <span class="lab">确认密码<i class="req" aria-hidden="true">*</i></span>
            <el-input
              v-model="form.confirmPassword"
              type="password"
              show-password
              autocomplete="new-password"
              placeholder="再次输入密码"
            />
          </label>
          <label class="field wide">
            <span class="lab">验证码<i class="req" aria-hidden="true">*</i></span>
            <div class="captcha-row">
              <el-input v-model="form.captcha" placeholder="验证码" maxlength="4" />
              <button type="button" class="captcha-btn" title="点击刷新" @click="loadCaptcha">
                <img v-if="captchaImg" :src="captchaImg" alt="验证码" />
                <span v-else>加载中</span>
              </button>
            </div>
          </label>
        </div>
      </div>

      <!-- 步骤 2：业务资料（双栏） -->
      <div v-show="step === 2 && hasProfileStep" class="pane">
        <div class="grid">
          <ProfileFieldInputs
            :fields="regFields"
            v-model:phone="form.phone"
            v-model:extras="form.extras"
          />
        </div>
      </div>

      <div class="actions">
        <el-button v-if="step === 2" class="ghost" @click="step = 1">上一步</el-button>
        <el-button
          class="submit"
          type="primary"
          native-type="submit"
          :loading="loading"
        >
          {{ primaryLabel }}
        </el-button>
      </div>
    </form>
    <template #footer>
      <span>已有账号？</span>
      <router-link to="/login">返回登录</router-link>
    </template>
  </AuthShell>
</template>

<script setup>
/**
 * 两步注册：账号安全 → 业务资料。避免一长页滚动（各领域共用基线）。
 */
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import http from '../api/http'
import AuthShell from '../components/AuthShell.vue'
import ProfileFieldInputs from '../components/ProfileFieldInputs.vue'
import { pickAuthTemplate } from '../utils/authTemplates'
import { FACTORY_DELIVERED } from '../factoryDelivered.js'
import {
  emptyProfileExtras,
  profileFieldsOnRegister,
  schemaLabels,
} from '../utils/domainSchema.js'
import { validateProfileFormats } from '../utils/profileValidate.js'

const router = useRouter()
const template = ref(pickAuthTemplate())
const labels = schemaLabels()
const title = ref(
  labels.appName || FACTORY_DELIVERED.title || import.meta.env.VITE_APP_TITLE || '毕设系统',
)
const captchaImg = ref('')
const loading = ref(false)
const step = ref(1)
const regFields = computed(() => profileFieldsOnRegister())
const hasProfileStep = computed(() => regFields.value.length > 0)
const stepLead = computed(() =>
  labels.registerRoleHint || '分步填写，完善后即可登录；管理员不开放自助注册。',
)
const stepSub = computed(() =>
  !hasProfileStep.value
    ? '创建业务账号'
    : step.value === 1
      ? '第 1 步 · 账号与安全'
      : '第 2 步 · 业务资料',
)
const primaryLabel = computed(() => {
  if (hasProfileStep.value && step.value === 1) return '下一步'
  return '注册并去登录'
})

const form = reactive({
  username: '',
  nickname: '',
  phone: '',
  password: '',
  confirmPassword: '',
  captcha: '',
  extras: emptyProfileExtras(profileFieldsOnRegister()),
})

const watermark = computed(() => {
  const brow = (labels.authEyebrow || '').trim()
  if (brow && brow.length <= 8) return brow
  const t = (title.value || '系统').trim()
  return t.length <= 6 ? t : t.slice(0, 4)
})

async function loadCaptcha() {
  const res = await http.get('/api/auth/captcha')
  captchaImg.value = res.data.image
}

function goStep(n) {
  if (n === 2 && !validateAccount()) return
  if (n === 2 && !hasProfileStep.value) return
  step.value = n
}

function validateAccount() {
  if (!form.username || !form.password) {
    ElMessage.warning('请填写用户名和密码')
    return false
  }
  if (form.password !== form.confirmPassword) {
    ElMessage.warning('两次密码不一致')
    return false
  }
  if (!form.captcha) {
    ElMessage.warning('请填写验证码')
    return false
  }
  return true
}

function validateProfile() {
  for (const f of regFields.value) {
    if (!f.required) continue
    if (f.storage === 'phone') {
      if (!form.phone?.trim()) {
        ElMessage.warning(`请填写${f.label}`)
        return false
      }
    } else if (!String(form.extras[f.key] || '').trim()) {
      ElMessage.warning(`请填写${f.label}`)
      return false
    }
  }
  const fmt = validateProfileFormats(form.phone, form.extras)
  if (fmt) {
    ElMessage.warning(fmt)
    return false
  }
  return true
}

async function onPrimary() {
  if (loading.value) return
  if (hasProfileStep.value && step.value === 1) {
    if (!validateAccount()) return
    step.value = 2
    return
  }
  if (!validateAccount()) return
  if (hasProfileStep.value && !validateProfile()) return
  loading.value = true
  try {
    await http.post('/api/auth/register', {
      username: form.username,
      nickname: form.nickname,
      phone: form.phone,
      password: form.password,
      confirmPassword: form.confirmPassword,
      captcha: form.captcha,
      extras: form.extras,
    })
    ElMessage.success('注册成功，请登录')
    router.push({ path: '/login', query: { u: form.username } })
  } catch {
    form.captcha = ''
    step.value = 1
    loadCaptcha()
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  try {
    const meta = await http.get('/api/meta')
    const hasName = !!(labels.appName || FACTORY_DELIVERED.title)
    if (!hasName && meta.data?.title) title.value = meta.data.title
  } catch { /* ignore */ }
  Object.assign(form.extras, emptyProfileExtras(profileFieldsOnRegister()))
  loadCaptcha()
})
</script>

<style scoped>
.form { display: flex; flex-direction: column; gap: 8px; }
.steps {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}
.step {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  border: none;
  background: transparent;
  padding: 0;
  cursor: pointer;
  font-size: 13px;
  font-weight: 500;
  color: var(--portal-muted, #8a9aa6);
}
.step .n {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  display: grid;
  place-items: center;
  font-size: 12px;
  font-weight: 700;
  background: var(--portal-bg, #eef3f5);
  color: var(--portal-muted, #6b7c8a);
}
.step.on { color: var(--portal-ink, #15202b); }
.step.on .n {
  background: var(--portal-accent, #0b6e75);
  color: #fff;
}
.bar {
  flex: 1;
  height: 1px;
  background: var(--portal-line, #dfe7ec);
  max-width: 48px;
}
.pane { min-height: 0; }
.grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  column-gap: 12px;
  row-gap: 10px;
}
.grid :deep(.field.wide),
.grid > .wide {
  grid-column: 1 / -1;
}
.field { display: flex; flex-direction: column; gap: 4px; min-width: 0; }
.lab {
  font-size: 12px;
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
  border-radius: 8px;
  box-shadow: 0 0 0 1px var(--portal-line, #d5dde3) inset;
  background: color-mix(in srgb, var(--portal-surface, #fff) 88%, var(--portal-bg, #eef3f5));
}
.form :deep(.el-input__wrapper:hover),
.form :deep(.el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 1px var(--portal-accent, #0b6e75) inset;
}
.captcha-row { display: flex; gap: 8px; }
.captcha-btn {
  width: 104px;
  flex-shrink: 0;
  border: 1px solid var(--portal-line, #d5dde3);
  border-radius: 8px;
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
  height: 30px;
  object-fit: cover;
  display: block;
}
.actions {
  display: flex;
  gap: 10px;
  margin-top: 10px;
}
.ghost {
  flex: 0 0 auto;
}
.submit {
  flex: 1;
  height: 38px !important;
  border-radius: 8px !important;
  font-weight: 600;
  background: var(--portal-accent, #0b6e75) !important;
  border-color: var(--portal-accent, #0b6e75) !important;
}
@media (max-width: 560px) {
  .grid { grid-template-columns: 1fr; }
}
</style>
