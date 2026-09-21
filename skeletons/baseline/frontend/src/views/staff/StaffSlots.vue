<template>
  <div>
    <div class="toolbar">
      <el-alert type="info" :closable="false" show-icon :title="hint" />
    </div>
    <ReservationsAdmin />
  </div>
</template>

<script setup>
import { computed } from 'vue'
import ReservationsAdmin from '../admin/ReservationsAdmin.vue'
import { getSchema, reservationCopy } from '../../utils/domainSchema.js'
import { currentStaffPost } from '../../utils/staffPosts.js'

const resvNoun = computed(() => reservationCopy().label || '预约')
const postId = computed(() => currentStaffPost())

const hint = computed(() => {
  const post = postId.value
  const noun = resvNoun.value
  // 毕设技师/教练：当日预约与服务队列
  if (post === 'stylist') {
    return `今日服务队列：查看${noun}并现场办结`
  }
  // 毕设导诊护士：挂号/分诊队列
  if (post === 'nurse') {
    return `分诊队列：查看当日${noun}并办理`
  }
  return `作业台：查看${noun}与现场服务状态`
})
</script>

<style scoped>
.toolbar { margin-bottom: 12px; }
</style>
