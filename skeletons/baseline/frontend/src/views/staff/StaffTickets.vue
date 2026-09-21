<template>
  <div>
    <div class="toolbar">
      <el-alert type="info" :closable="false" show-icon :title="hint" />
    </div>
    <TicketsAdmin />
  </div>
</template>

<script setup>
import { computed } from 'vue'
import TicketsAdmin from '../admin/TicketsAdmin.vue'
import { getSchema } from '../../utils/domainSchema.js'
import { currentStaffPost } from '../../utils/staffPosts.js'

const ticketNoun = computed(() => getSchema()?.entities?.ticket?.label || '工单')
const postId = computed(() => currentStaffPost())

const hint = computed(() => {
  const post = postId.value
  const noun = ticketNoun.value
  // 毕设维修员：我的维修任务 接单→处理→完结
  if (post === 'repairer' || post === 'field_tech') {
    return `维修任务：查看待办${noun}，受理后办理并完结（与后台受理同源）`
  }
  // 毕设驿站派件：待派列表 + 确认派送
  if (post === 'courier') {
    return `派件任务：处理待派${noun}，确认派送并完结`
  }
  return `作业台：查看待办并办理（与后台受理同源接口）`
})
</script>

<style scoped>
.toolbar { margin-bottom: 12px; }
</style>
