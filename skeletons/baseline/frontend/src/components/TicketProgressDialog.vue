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
        <strong>{{ p.status }}</strong>
        <span v-if="p.operator"> · {{ p.operator }}</span>
        <div v-if="p.remark" class="note">{{ p.remark }}</div>
      </el-timeline-item>
    </el-timeline>
    <p v-else class="empty">{{ emptyText }}</p>
  </el-dialog>
</template>

<script setup>
import { ref, watch } from 'vue'
import http from '../api/http'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  ticketId: { type: [Number, String], default: null },
  emptyText: { type: String, default: '暂无进度记录' },
})

const emit = defineEmits(['update:modelValue'])

const list = ref([])

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
.note { margin-top: 4px; font-size: 13px; color: #64748b; }
.empty { margin: 0; color: #94a3b8; font-size: 13px; }
</style>
