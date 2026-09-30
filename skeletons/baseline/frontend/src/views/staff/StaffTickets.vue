<template>
  <div>
    <div class="toolbar">
      <el-alert type="info" :closable="false" show-icon :title="hint" />
      <el-radio-group
        v-if="repairBoard"
        v-model="mode"
        size="small"
        style="margin-left:12px"
      >
        <el-radio-button value="todo">待办受理</el-radio-button>
        <el-radio-button value="today">今日处理中</el-radio-button>
      </el-radio-group>
    </div>
    <TicketsAdmin v-if="mode === 'todo'" />
    <TicketRecordsAdmin v-else :default-today="true" />
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import TicketsAdmin from '../admin/TicketsAdmin.vue'
import TicketRecordsAdmin from '../admin/TicketRecordsAdmin.vue'
import { getSchema } from '../../utils/domainSchema.js'
import { currentStaffPost } from '../../utils/staffPosts.js'

const ticketNoun = computed(() => getSchema()?.entities?.ticket?.label || '工单')
const ticket = computed(() => getSchema()?.entities?.ticket || {})
const postId = computed(() => currentStaffPost())
const repairBoard = computed(() => {
  const post = postId.value
  return (post === 'repairer' || post === 'field_tech')
    && !!(ticket.value.todayBoard || ticket.value.repairThicken)
})
const mode = ref('todo')

const hint = computed(() => {
  const post = postId.value
  const noun = ticketNoun.value
  if (post === 'repairer' || post === 'field_tech') {
    return repairBoard.value
      ? `维修任务：待办受理新${noun}；「今日处理中」查看本人当天工单并可挂起/拒单/办结。`
      : `维修任务：查看待办${noun}，受理后办理并完结（与后台受理同源）`
  }
  if (post === 'courier') {
    return `派件任务：处理待派${noun}，确认派送并完结`
  }
  return `作业台：查看待办并办理（与后台受理同源接口）`
})
</script>

<style scoped>
.toolbar {
  margin-bottom: 12px;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}
</style>
