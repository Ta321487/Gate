<template>
  <el-dialog
    :model-value="modelValue"
    title="处理进度"
    width="480px"
    destroy-on-close
    @update:model-value="emit('update:modelValue', $event)"
  >
    <el-timeline v-if="list.length">
      <el-timeline-item
        v-for="p in list"
        :key="p.id"
        :timestamp="p.createdAt"
        placement="top"
      >
        <strong>{{ progressStatusLabel(p.status) }}</strong>
        <span v-if="p.operator"> · {{ p.operator }}</span>
        <div v-if="showRemark(p)" class="note">{{ p.remark }}</div>
      </el-timeline-item>
    </el-timeline>
    <p v-else class="empty">{{ emptyText }}</p>
  </el-dialog>
</template>

<script setup>
import { ref, watch } from 'vue'
import http from '../api/http'
import { ticketCopy, ticketProgressStatusLabel } from '../utils/domainSchema.js'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  ticketId: { type: [Number, String], default: null },
  emptyText: { type: String, default: '暂无进度记录' },
})

const emit = defineEmits(['update:modelValue'])

const list = ref([])

function progressStatusLabel(status) {
  return ticketProgressStatusLabel(status)
}

/** 备注与状态文案相同时不重复；旧库写死的「已完结」等交给 states 展示 */
function showRemark(p) {
  const r = (p.remark || '').trim()
  if (!r) return false
  const lab = progressStatusLabel(p.status)
  if (r === lab) return false
  const stateVals = Object.values(ticketCopy().states || {})
  if (stateVals.includes(r)) return false
  const st = String(p.status || '')
  if ((st === 'returned' || st === 'overdue' || st === 'noshow')
      && (r === '已完结' || r === '已完成')) {
    return false
  }
  return true
}

watch(
  () => [props.modelValue, props.ticketId],
  async ([open, id]) => {
    if (!open || !id) {
      list.value = []
      return
    }
    list.value = []
    try {
      const res = await http.get(`/api/tickets/${id}/progress`)
      list.value = res.data || []
    } catch {
      list.value = []
    }
  },
)
</script>

<style scoped>
.note { margin-top: 4px; font-size: 13px; color: var(--portal-muted, #64748b); }
.empty { margin: 0; color: var(--portal-muted, #94a3b8); font-size: 13px; }
</style>
