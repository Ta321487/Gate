<template>
  <div class="banner warn mb-12">
    <h4>工程已更新，业务内容可能不一致</h4>
    <p class="small muted" style="margin:6px 0 12px">{{ message || defaultMsg }}</p>
    <div class="row" style="gap:8px;flex-wrap:wrap">
      <n-button size="small" @click="emit('diff')">查看差异</n-button>
      <n-button size="small" type="primary" :loading="syncing" @click="emit('sync')">按工程更新业务页</n-button>
      <n-button size="small" quaternary @click="emit('dismiss')">稍后</n-button>
    </div>
  </div>
</template>

<script setup>
import { PPT_DIRTY_BANNER } from '../../ppt/types.js'

defineProps({
  message: { type: String, default: '' },
  syncing: { type: Boolean, default: false },
})
const emit = defineEmits(['diff', 'sync', 'dismiss'])
const defaultMsg = PPT_DIRTY_BANNER
</script>
