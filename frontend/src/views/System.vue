<template>
  <div>
    <h1 class="page-title">运行环境</h1>
    <p class="page-desc">
      本机依赖与端口池（限制同时预览数，不限制选题库存）。服务器部署时设置 GF_PUBLIC_HOST 为对外 IP/域名。
      工作台后端接口文档见
      <a href="/docs" target="_blank" rel="noopener">/docs</a>
      ·
      <a href="/redoc" target="_blank" rel="noopener">/redoc</a>
      （与学生端交付包无关）。
    </p>
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
          <div class="panel-hd">
            <h3>端口池</h3>
            <n-button size="small" :loading="loading" @click="load">刷新</n-button>
          </div>
          <div class="panel-bd">
            <div class="small mb-12"><span class="muted">对外地址</span> {{ info.public_host || '127.0.0.1' }} · 监听 {{ info.bind_host || '127.0.0.1' }}</div>
            <div class="small mb-12">
              <span class="muted">后端</span> {{ info.backend_ports }}
              · 占用 {{ formatPorts(info.used_backend) }}
              <span class="muted">（运行中 {{ formatPorts(info.managed_backend) }} · 可释放 {{ formatPorts(info.idle_backend) }}）</span>
            </div>
            <div class="small mb-12">
              <span class="muted">前端</span> {{ info.frontend_ports }}
              · 占用 {{ formatPorts(info.used_frontend) }}
              <span class="muted">（运行中 {{ formatPorts(info.managed_frontend) }} · 可释放 {{ formatPorts(info.idle_frontend) }}）</span>
            </div>
            <p class="small muted mb-12">「释放」只清理工作台未托管但仍占端口的进程，不会停止正在预览的项目。</p>
            <n-button size="small" :loading="freeing" :disabled="!hasIdle" @click="free">
              释放异常占用{{ hasIdle ? `（${idleCount}）` : '' }}
            </n-button>
          </div>
        </div>
        <div class="panel">
          <div class="panel-hd"><h3>路径 / 库</h3></div>
          <div class="panel-bd stack">
            <div class="small path-row">
              <div><span class="muted">运营库</span><br /><span class="mono">{{ info.factory_db || '—' }}</span></div>
              <CopyIconButton v-if="info.factory_db" :text="info.factory_db" tip="复制" />
            </div>
            <div class="small path-row">
              <div><span class="muted">工作区</span><br /><span class="mono">{{ info.workspace }}</span></div>
              <CopyIconButton v-if="info.workspace" :text="info.workspace" tip="复制路径" />
            </div>
            <div class="small path-row">
              <div><span class="muted">上传</span><br /><span class="mono">{{ info.uploads }}</span></div>
              <CopyIconButton v-if="info.uploads" :text="info.uploads" tip="复制路径" />
            </div>
            <div class="small path-row">
              <div><span class="muted">骨架</span><br /><span class="mono">{{ info.skeletons }}</span></div>
              <CopyIconButton v-if="info.skeletons" :text="info.skeletons" tip="复制路径" />
            </div>
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
import { computed, onMounted, ref } from 'vue'
import { api, message } from '../api'
import PageSkeleton from '../components/PageSkeleton.vue'
import ErrorPage from './ErrorPage.vue'
import CopyIconButton from '../components/CopyIconButton.vue'

const info = ref(null)
const freeing = ref(false)
const loading = ref(false)
const booted = ref(false)

function formatPorts(ports) {
  return (ports && ports.length) ? ports.join(', ') : '无'
}

const idleCount = computed(
  () => (info.value?.idle_backend?.length || 0) + (info.value?.idle_frontend?.length || 0),
)
const hasIdle = computed(() => idleCount.value > 0)

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
    const cleaned = res?.data?.cleaned || 0
    if (cleaned) message.success(res.message)
    else message.info(res.message)
    await load()
  } finally {
    freeing.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.path-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 8px;
}
</style>
