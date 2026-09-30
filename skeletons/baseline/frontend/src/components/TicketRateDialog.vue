<template>
  <el-dialog
    :model-value="modelValue"
    :title="dialogTitle"
    width="440px"
    destroy-on-close
    @update:model-value="emit('update:modelValue', $event)"
    @closed="onClosed"
  >
    <p v-if="title" class="tip">对「{{ title }}」{{ followMode ? '追评' : '评分' }}</p>
    <p v-if="lowHint && needLowRemark" class="hint">{{ lowHint }}</p>
    <el-form label-width="88px">
      <template v-if="dims.length">
        <el-form-item
          v-for="d in dims"
          :key="d.key"
          :label="d.label"
          required
        >
          <el-rate v-model="dimScores[d.key]" :max="5" />
        </el-form-item>
      </template>
      <el-form-item v-else label="评分" required>
        <el-rate v-model="rating" :max="5" />
      </el-form-item>
      <el-form-item v-if="tagOptions.length" label="评价标签">
        <el-checkbox-group v-model="selectedTags">
          <el-checkbox v-for="t in tagOptions" :key="t" :label="t" :value="t">{{ t }}</el-checkbox>
        </el-checkbox-group>
      </el-form-item>
      <el-form-item :label="needLowRemark ? '原因' : '短评'" :required="needLowRemark">
        <el-input
          v-model="remark"
          type="textarea"
          :rows="2"
          maxlength="200"
          show-word-limit
          :placeholder="needLowRemark ? '评分较低时请写明原因' : '选填'"
        />
      </el-form-item>
      <el-form-item v-if="allowAnonymous" label="匿名">
        <el-checkbox v-model="anonymous">匿名提交</el-checkbox>
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="emit('update:modelValue', false)">取消</el-button>
      <el-button type="primary" :loading="loading" @click="submit">提交</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { computed, reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import http from '../api/http'
import { getSchema, schemaLabels } from '../utils/domainSchema.js'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  ticketId: { type: [Number, String], default: null },
  title: { type: String, default: '' },
  followMode: { type: Boolean, default: false },
})

const emit = defineEmits(['update:modelValue', 'done'])

const ticket = computed(() => getSchema()?.entities?.ticket || {})
const labels = computed(() => schemaLabels())
const dims = computed(() => {
  const list = ticket.value.ratingDims
  return Array.isArray(list)
    ? list.filter((d) => d && d.key && d.label)
    : []
})
const allowAnonymous = computed(() => !!ticket.value.allowAnonymousRating)
const tagOptions = computed(() => {
  if (!ticket.value.allowRatingTags) return []
  const list = ticket.value.ratingTags
  return Array.isArray(list) ? list.filter(Boolean) : []
})
const requireLow = computed(() => !!ticket.value.requireLowRatingRemark)
const lowHint = computed(() => labels.value.lowRatingReasonHint || '')
const dialogTitle = computed(() => {
  if (props.followMode) return '追评'
  return dims.value.length ? '多维评分' : '评分'
})

const rating = ref(5)
const remark = ref('')
const anonymous = ref(false)
const selectedTags = ref([])
const dimScores = reactive({})
const loading = ref(false)

const overallScore = computed(() => {
  if (!dims.value.length) return Number(rating.value) || 0
  const vals = dims.value.map((d) => Number(dimScores[d.key]) || 0).filter((n) => n > 0)
  if (!vals.length) return 0
  return Math.round(vals.reduce((a, b) => a + b, 0) / vals.length)
})
const needLowRemark = computed(() => requireLow.value && overallScore.value > 0 && overallScore.value <= 2)

function resetForm() {
  rating.value = 5
  remark.value = ''
  anonymous.value = false
  selectedTags.value = []
  Object.keys(dimScores).forEach((k) => delete dimScores[k])
  for (const d of dims.value) {
    dimScores[d.key] = 5
  }
}

watch(
  () => props.modelValue,
  (open) => {
    if (open) resetForm()
  },
)

function onClosed() {
  loading.value = false
}

async function submit() {
  if (!props.ticketId) return
  const body = { remark: remark.value }
  if (allowAnonymous.value) body.anonymous = !!anonymous.value
  if (dims.value.length) {
    const payload = {}
    for (const d of dims.value) {
      const v = dimScores[d.key]
      if (!v || v < 1) {
        ElMessage.warning(`请完成「${d.label}」评分`)
        return
      }
      payload[d.key] = v
    }
    body.dims = payload
  } else {
    if (!rating.value || rating.value < 1) {
      ElMessage.warning('请选择 1～5 分')
      return
    }
    body.rating = rating.value
  }
  if (needLowRemark.value && !(remark.value || '').trim()) {
    ElMessage.warning('评分较低时请填写原因')
    return
  }
  if (tagOptions.value.length && selectedTags.value.length) {
    body.ratingTags = selectedTags.value.join(',')
  }
  loading.value = true
  try {
    await http.post(`/api/tickets/${props.ticketId}/rate`, body)
    ElMessage.success(props.followMode ? '追评已提交' : '感谢评价')
    emit('update:modelValue', false)
    emit('done')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.tip { margin: 0 0 12px; color: var(--portal-ink, #334155); font-size: 14px; }
.hint { margin: 0 0 12px; color: #b45309; font-size: 13px; }
</style>
