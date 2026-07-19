<template>
  <div>
    <div class="row" style="justify-content:space-between;align-items:flex-start;margin-bottom:4px">
      <h1 class="page-title" style="margin-bottom:0">运行环境</h1>
      <n-button size="small" :loading="loading" :disabled="!booted" @click="load">刷新</n-button>
    </div>
    <p class="page-desc">本机依赖与端口池。</p>
    <PageSkeleton v-if="!booted" variant="dashboard" :rows="4" />
    <template v-else-if="info">
      <div class="stats">
        <div class="stat"><div class="label">JDK</div><div class="value" style="font-size:16px">{{ info.jdk }}</div></div>
        <div class="stat"><div class="label">Maven</div><div class="value" style="font-size:16px">{{ info.maven }}</div></div>
        <div class="stat"><div class="label">Node</div><div class="value" style="font-size:16px">{{ info.node }}</div></div>
        <div class="stat"><div class="label">学生 MySQL</div><div class="value" style="font-size:14px">{{ info.mysql }}</div></div>
      </div>
      <div class="grid-2">
        <div class="panel">
          <div class="panel-hd"><h3>端口池</h3></div>
          <div class="panel-bd">
            <div class="small mb-12"><span class="muted">后端</span> {{ info.backend_ports }} · 占用中 {{ info.used_backend.join(', ') || '无' }}</div>
            <div class="small mb-12"><span class="muted">前端</span> {{ info.frontend_ports }} · 占用中 {{ info.used_frontend.join(', ') || '无' }}</div>
            <n-button size="small" :loading="freeing" @click="free">释放空闲占用</n-button>
          </div>
        </div>
        <div class="panel">
          <div class="panel-hd"><h3>路径 / 库</h3></div>
          <div class="panel-bd stack">
            <div class="small"><span class="muted">运营库</span><br /><span class="mono">{{ info.factory_db || '—' }}</span></div>
            <div class="small"><span class="muted">工作区</span><br /><span class="mono">{{ info.workspace }}</span></div>
            <div class="small"><span class="muted">上传</span><br /><span class="mono">{{ info.uploads }}</span></div>
            <div class="small"><span class="muted">骨架</span><br /><span class="mono">{{ info.skeletons }}</span></div>
          </div>
        </div>
      </div>
    </template>
    <ErrorPage
      v-else
      :code="500"
      title="环境信息不可用"
      description="无法读取本机依赖与端口池，请确认后端已启动后重试。"
      retryable
      @retry="load"
    />
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { api, message } from '../api'
import PageSkeleton from '../components/PageSkeleton.vue'
import ErrorPage from './ErrorPage.vue'

const info = ref(null)
const freeing = ref(false)
const loading = ref(false)
const booted = ref(false)

async function load() {
  loading.value = true
  try {
    info.value = await api.system()
  } catch {
    info.value = null
  } finally {
    loading.value = false
    booted.value = true
  }
}

async function free() {
  freeing.value = true
  try {
    const res = await api.freePorts()
    message.success(res.message)
    await load()
  } finally {
    freeing.value = false
  }
}

onMounted(load)
</script>
