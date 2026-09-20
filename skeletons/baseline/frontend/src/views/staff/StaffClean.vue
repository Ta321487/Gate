<template>
  <div>
    <div class="toolbar">
      <el-alert type="info" :closable="false" show-icon :title="hint" />
    </div>
    <CleanTasksAdmin />
  </div>
</template>

<script setup>
import { computed } from 'vue'
import CleanTasksAdmin from '../admin/CleanTasksAdmin.vue'
import { getSchema } from '../../utils/domainSchema.js'

const hint = computed(() => getSchema()?.labels?.cleanTasksHint || '清洁任务：完成待打扫房间')
</script>

<style scoped>
.toolbar { margin-bottom: 12px; }
</style>
