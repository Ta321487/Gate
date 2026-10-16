<template>
  <div>
    <p class="lead">{{ pageLead }}</p>
    <el-form label-position="top" class="form" v-loading="loading">
      <el-form-item :label="nameLabel">
        <el-input v-model="form.siteName" maxlength="64" clearable />
      </el-form-item>
      <el-form-item :label="logoLabel">
        <el-input v-model="form.logoUrl" maxlength="512" clearable placeholder="图片 URL 或本地路径" />
      </el-form-item>
      <el-form-item :label="bgLabel">
        <el-input v-model="form.loginBgUrl" maxlength="512" clearable placeholder="图片 URL 或本地路径" />
      </el-form-item>
      <el-form-item :label="maskLabel">
        <el-switch v-model="form.maskPhone" />
        <p class="hint">{{ maskHint }}</p>
      </el-form-item>
      <el-form-item :label="maintOnLabel">
        <el-switch v-model="form.maintenanceOn" />
      </el-form-item>
      <el-form-item :label="maintTextLabel">
        <el-input
          v-model="form.maintenanceText"
          maxlength="200"
          type="textarea"
          :rows="2"
          :placeholder="maintDefault"
        />
      </el-form-item>
      <el-button type="primary" :loading="saving" @click="save">保存</el-button>
    </el-form>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import http from '../../api/http'
import { getSchema } from '../../utils/domainSchema.js'

const labels = computed(() => getSchema()?.labels || {})
const pageLead = computed(
  () =>
    labels.value.siteSettingsLead ||
    '可调整系统名称、标志与登录页背景；敏感字段脱敏仅影响管理端列表展示。',
)
const nameLabel = computed(() => labels.value.siteNameLabel || '系统名称')
const logoLabel = computed(() => labels.value.siteLogoLabel || '标志图片地址')
const bgLabel = computed(() => labels.value.loginBgLabel || '登录页背景图地址')
const maskLabel = computed(() => labels.value.maskPhoneLabel || '管理端列表手机号脱敏')
const maskHint = computed(
  () => labels.value.maskPhoneHint || '开启后用户管理列表中的手机号中间四位显示为 *',
)
const maintOnLabel = computed(() => labels.value.maintenanceOnLabel || '维护提示条')
const maintTextLabel = computed(() => labels.value.maintenanceTextLabel || '维护提示文案')
const maintDefault = computed(
  () => labels.value.maintenanceDefaultText || '系统维护中，部分功能暂不可用',
)

const loading = ref(false)
const saving = ref(false)
const form = reactive({
  siteName: '',
  logoUrl: '',
  loginBgUrl: '',
  maskPhone: false,
  maintenanceOn: false,
  maintenanceText: '',
})

async function load() {
  loading.value = true
  try {
    const res = await http.get('/api/admin/site-settings')
    const d = res.data || {}
    form.siteName = d.siteName || ''
    form.logoUrl = d.logoUrl || ''
    form.loginBgUrl = d.loginBgUrl || ''
    form.maskPhone = !!d.maskPhone
    form.maintenanceOn = !!d.maintenanceOn
    form.maintenanceText = d.maintenanceText || ''
  } finally {
    loading.value = false
  }
}

async function save() {
  saving.value = true
  try {
    await http.put('/api/admin/site-settings', { ...form })
    ElMessage.success('已保存')
  } finally {
    saving.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.lead { margin: 0 0 16px; color: var(--el-text-color-secondary); font-size: 13px; }
.form { max-width: 560px; }
.hint { margin: 6px 0 0; font-size: 12px; color: var(--el-text-color-secondary); }
</style>
