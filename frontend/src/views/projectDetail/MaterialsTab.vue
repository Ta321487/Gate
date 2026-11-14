<template>
  <div class="materials-pane">
    <div class="surface-main-hd">
      <h2>材料</h2>
      <span class="small muted">本单开题 / 任务书来源 · 只读</span>
    </div>
    <div class="stack">
      <template v-if="hasSource">
        <div class="file-row" style="margin:0">
          <div class="file-row-main">
            <strong>{{ sourceName }}</strong>
            <span class="small muted">建项时上传的材料文件</span>
          </div>
        </div>
        <p v-if="sourcePath" class="small muted" style="margin:0">
          本地路径仅供本机排障，履约主路径不必打开。
        </p>
      </template>
      <div v-else class="empty-hint">
        <div class="empty-title">未挂本地材料文件</div>
        <div class="empty-desc">
          可能为样例建项或材料已随工程落库。换题 / 补传请回项目列表重新上传建项。
        </div>
      </div>
      <div class="row" style="margin:0;gap:8px;flex-wrap:wrap">
        <n-button size="small" secondary @click="$router.push('/projects')">回项目列表</n-button>
        <n-button size="small" secondary @click="emit('next')">去匹配确认</n-button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, inject } from 'vue'
import { PD_KEY } from './context'

const emit = defineEmits(['next'])
const pd = inject(PD_KEY)
const p = computed(() => pd.p)

const sourceName = computed(() => {
  const row = p.value || {}
  return String(row.source_filename || row.source_name || row.source_path || '').trim() || '已关联材料'
})

const sourcePath = computed(() => String(p.value?.source_path || '').trim())

const hasSource = computed(() => {
  const row = p.value || {}
  return !!(row.source_path || row.source_filename || row.source_name)
})
</script>
