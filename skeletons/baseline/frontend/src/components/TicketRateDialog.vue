<template>
  <el-dialog
    :model-value="modelValue"
    title="评分"
    width="420px"
    destroy-on-close
    @update:model-value="emit('update:modelValue', $event)"
    @closed="onClosed"
  >
    <p v-if="title" class="tip">对「{{ title }}」评分</p>
    <el-form label-width="72px">
      <el-form-item label="评分" required>
        <el-rate v-model="rating" :max="5" />
      </el-form-item>
      <el-form-item label="短评">
        <el-input
          v-model="remark"
          type="textarea"
          :rows="2"
          maxlength="200"
          show-word-limit
          placeholder="选填"
        />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="emit('update:modelValue', false)">取消</el-button>
      <el-button type="primary" :loading="loading" @click="submit">提交</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import http from '../api/http'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  ticketId: { type: [Number, String], default: null },
  title: { type: String, default: '' },
})

const emit = defineEmits(['update:modelValue', 'done'])

const rating = ref(5)
const remark = ref('')
const loading = ref(false)

watch(
  () => props.modelValue,
  (open) => {
    if (open) {
      rating.value = 5
      remark.value = ''
    }
  },
)

function onClosed() {
  loading.value = false
}

async function submit() {
  if (!props.ticketId) return
  if (!rating.value || rating.value < 1) {
    ElMessage.warning('请选择 1～5 分')
    return
  }
  loading.value = true
  try {
    await http.post(`/api/tickets/${props.ticketId}/rate`, {
      rating: rating.value,
      remark: remark.value,
    })
    ElMessage.success('感谢评价')
    emit('update:modelValue', false)
    emit('done')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.tip { margin: 0 0 12px; color: #334155; font-size: 14px; }
</style>
