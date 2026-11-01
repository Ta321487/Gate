<template>
  <div>
    <h1 class="page-title">Unsplash</h1>
    <p class="page-desc">
      登录氛围图与门户轮播。出包优先读本机缓存；Unsplash 只在缓存未命中时拉图。
    </p>
    <PageSkeleton v-if="!booted" variant="dashboard" :rows="2" />
    <template v-else>
      <div class="panel" style="max-width:640px">
        <div class="panel-hd">
          <h3>连接</h3>
          <span class="pill" :class="cfg.key_configured ? 'pill-green' : 'pill-amber'">
            {{ cfg.key_configured ? '已配置 Key' : '未配置 Key' }}
          </span>
          <span
            class="pill"
            :class="cfg.proxy_configured ? 'pill-green' : 'pill-muted'"
            title="UNSPLASH_HTTP_PROXY"
          >
            {{ cfg.proxy_configured ? '已配代理' : '未配代理' }}
          </span>
        </div>
        <div class="panel-bd stack">
          <n-form-item label="Access Key">
            <n-input :value="cfg.key_masked" disabled />
          </n-form-item>
          <p class="small muted">
            申请：
            <a href="https://unsplash.com/developers" target="_blank" rel="noopener">unsplash.com/developers</a>
            · 写入 <span class="mono">backend/.env</span> 的
            <span class="mono">UNSPLASH_ACCESS_KEY</span>
            ；可选 <span class="mono">UNSPLASH_HTTP_PROXY</span>。改完重启后端。
          </p>
          <p class="small">
            本机缓存：登录氛围 <strong>{{ cfg.vault_auth_heroes }}</strong> 张 · 门户轮播
            <strong>{{ cfg.vault_portal_banners }}</strong> 张
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

      <div class="panel" style="max-width:640px;margin-top:16px">
        <div class="panel-hd">
          <h3>运营提示</h3>
        </div>
        <div class="panel-bd">
          <ul class="hint-list">
            <li v-for="(h, i) in cfg.hints" :key="i">{{ h }}</li>
          </ul>
          <p v-if="!cfg.hints.length" class="small muted">{{ cfg.hint || '暂无提示' }}</p>
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
  proxy_configured: false,
  vault_auth_heroes: 0,
  vault_portal_banners: 0,
  hints: [],
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

<style scoped>
.hint-list {
  margin: 0;
  padding-left: 1.2em;
  line-height: 1.55;
}
.hint-list li + li {
  margin-top: 0.45em;
}
.pill-muted {
  opacity: 0.65;
}
</style>
