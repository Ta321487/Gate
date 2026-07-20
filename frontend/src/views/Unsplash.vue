<template>
  <div>
    <h1 class="page-title">Unsplash</h1>
    <p class="page-desc">
      登录氛围图与门户轮播配图。Access Key 仅环境变量，与 DeepSeek 相同；未配置时按领域用公开图直链兜底。
    </p>
    <PageSkeleton v-if="!booted" variant="dashboard" :rows="2" />
    <template v-else>
      <div class="panel" style="max-width:560px">
        <div class="panel-hd">
          <h3>连接</h3>
          <span class="pill" :class="cfg.key_configured ? 'pill-green' : 'pill-amber'">
            {{ cfg.key_configured ? '已配置' : '未配置 Key' }}
          </span>
        </div>
        <div class="panel-bd stack">
          <n-form-item label="Access Key">
            <n-input :value="cfg.key_masked" disabled />
          </n-form-item>
          <p class="small muted">{{ cfg.hint }}</p>
          <p class="small muted">
            申请地址：
            <a href="https://unsplash.com/developers" target="_blank" rel="noopener">unsplash.com/developers</a>
            · 写入 <span class="mono">backend/.env</span> 的
            <span class="mono">UNSPLASH_ACCESS_KEY</span> 后重启后端。
          </p>
          <div class="row">
            <n-button type="primary" size="small" :loading="testing" :disabled="!cfg.key_configured" @click="test">
              测试连接
            </n-button>
            <n-button size="small" :loading="loading" @click="load">刷新</n-button>
            <span class="small muted">{{ latency }}</span>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { api, message } from '../api'
import PageSkeleton from '../components/PageSkeleton.vue'

const cfg = reactive({
  key_configured: false,
  key_masked: '',
  hint: '',
})
const booted = ref(false)
const loading = ref(false)
const testing = ref(false)
const latency = ref('')

async function load() {
  loading.value = true
  try {
    Object.assign(cfg, await api.unsplash())
  } catch (e) {
    message.error(e?.message || '读取 Unsplash 配置失败')
  } finally {
    loading.value = false
    booted.value = true
  }
}

async function test() {
  if (testing.value) return
  testing.value = true
  latency.value = '测试中…'
  try {
    const res = await api.testUnsplash()
    latency.value = res.message
    if (res.ok) message.success(res.message)
    else message.error(res.message)
  } finally {
    testing.value = false
  }
}

onMounted(load)
</script>
