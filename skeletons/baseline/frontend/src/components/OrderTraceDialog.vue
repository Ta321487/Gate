<template>
  <el-dialog
    :model-value="modelValue"
    :title="title"
    width="480px"
    destroy-on-close
    @update:model-value="emit('update:modelValue', $event)"
  >
    <el-timeline v-if="list.length">
      <el-timeline-item
        v-for="(n, i) in list"
        :key="i"
        :timestamp="n.at || '—'"
        placement="top"
      >
        <strong>{{ n.title }}</strong>
        <div v-if="n.detail" class="note">{{ n.detail }}</div>
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
  orderId: { type: [Number, String], default: null },
  title: { type: String, default: '物流进度' },
  emptyText: { type: String, default: '暂无轨迹记录' },
  /** 默认物流轨迹；售后进度传 refund-trace */
  endpoint: { type: String, default: 'trace' },
})

const emit = defineEmits(['update:modelValue'])

const list = ref([])

watch(
  () => [props.modelValue, props.orderId, props.endpoint],
  async ([open, id, ep]) => {
    if (!open || !id) {
      list.value = []
      return
    }
    list.value = []
    const path = ep === 'refund-trace' ? 'refund-trace' : 'trace'
    try {
      const res = await http.get(`/api/orders/${id}/${path}`)
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
