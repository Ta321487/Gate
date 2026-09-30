<template>
  <el-dialog
    :model-value="modelValue"
    :title="titleText"
    width="560px"
    destroy-on-close
    @update:model-value="emit('update:modelValue', $event)"
  >
    <p v-if="row" class="tip">办结「{{ row.title || ('编号 ' + row.id) }}」前请核对下列信息</p>
    <div v-if="row && (row.attachUrl || form.closeAttachUrl)" class="compare">
      <div class="cmp">
        <div class="cmp-lab">报修图</div>
        <a v-if="row.attachUrl" :href="row.attachUrl" target="_blank" rel="noopener noreferrer">
          <img :src="row.attachUrl" alt="报修图" />
        </a>
        <span v-else class="muted">未上传</span>
      </div>
      <div class="cmp">
        <div class="cmp-lab">完工图</div>
        <a v-if="form.closeAttachUrl" :href="form.closeAttachUrl" target="_blank" rel="noopener noreferrer">
          <img :src="form.closeAttachUrl" alt="完工图" />
        </a>
        <span v-else class="muted">办结时上传</span>
      </div>
    </div>
    <el-form label-width="120px">
      <el-form-item v-if="requireFaultReason" :label="faultReasonLabel" required>
        <el-select v-model="form.faultReason" filterable allow-create default-first-option style="width:100%">
          <el-option v-for="opt in faultReasons" :key="opt" :label="opt" :value="opt" />
        </el-select>
      </el-form-item>
      <el-form-item v-if="requireCloseSummary" :label="closeSummaryLabel" required>
        <el-input v-model="form.closeSummary" type="textarea" :rows="3" maxlength="512" show-word-limit />
      </el-form-item>
      <el-form-item v-if="requireCloseAttach" label="结案附件" required>
        <el-upload :show-file-list="false" :http-request="onUpload">
          <el-button type="primary" plain>上传</el-button>
        </el-upload>
        <a v-if="form.closeAttachUrl" :href="form.closeAttachUrl" target="_blank" rel="noopener noreferrer" class="link">已上传</a>
      </el-form-item>
      <el-form-item v-if="allowPartsNote" :label="partsNoteLabel">
        <el-input v-model="form.partsNote" maxlength="255" :placeholder="partsWarnHint" />
      </el-form-item>
      <el-form-item v-if="allowSerialNo" :label="serialNoLabel">
        <el-input v-model="form.serialNo" maxlength="64" />
      </el-form-item>
      <el-form-item v-if="allowRemoteUrl" :label="remoteUrlLabel">
        <el-input v-model="form.remoteUrl" maxlength="255" placeholder="会议号或协助说明" />
      </el-form-item>
      <el-form-item v-if="allowRouteNote" :label="routeNoteLabel">
        <el-input v-model="form.routeNote" maxlength="255" placeholder="当日路线备注" />
      </el-form-item>
      <el-form-item v-if="allowHelper" :label="helperLabel">
        <el-select v-model="form.helperUsername" clearable filterable placeholder="可选协助人" style="width:100%">
          <el-option
            v-for="t in targets"
            :key="t.username"
            :label="dispatchLabel(t)"
            :value="t.username"
          />
        </el-select>
      </el-form-item>
      <el-form-item v-if="visitFollowup" label="回访日期">
        <el-date-picker
          v-model="form.visitDueAt"
          type="datetime"
          value-format="YYYY-MM-DDTHH:mm:ss"
          placeholder="结单后回访"
          style="width:100%"
        />
      </el-form-item>
      <el-form-item v-if="allowQuote" :label="quoteLabel">
        <el-input-number v-model="form.quoteYuan" :min="0" :max="999999" :precision="2" />
      </el-form-item>
      <el-form-item v-if="allowQuote" :label="materialFeeLabel">
        <el-input-number v-model="form.materialFeeYuan" :min="0" :max="999999" :precision="2" />
      </el-form-item>
      <el-form-item v-if="allowKnowledgeDeposit" :label="knowledgeLabel">
        <el-switch v-model="form.knowledgeDeposit" />
      </el-form-item>
      <el-form-item v-if="allowTicketMerge" :label="parentTicketLabel">
        <el-input-number v-model="form.parentTicketId" :min="0" :controls="false" placeholder="主单编号" style="width:100%" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="emit('update:modelValue', false)">取消</el-button>
      <el-button type="primary" :loading="loading" @click="submit">确认办结</el-button>
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
  row: { type: Object, default: null },
})
const emit = defineEmits(['update:modelValue', 'done'])

const ticket = computed(() => getSchema()?.entities?.ticket || {})
const labels = computed(() => schemaLabels())
const verbs = computed(() => ticket.value.verbs || {})
const titleText = computed(() => verbs.value.return || '完成')

const requireFaultReason = computed(() => !!ticket.value.requireFaultReason)
const requireCloseSummary = computed(() => !!ticket.value.requireCloseSummary)
const requireCloseAttach = computed(() => !!ticket.value.requireCloseAttach)
const allowPartsNote = computed(() => !!ticket.value.allowPartsNote)
const allowSerialNo = computed(() => !!ticket.value.allowSerialNo)
const allowRemoteUrl = computed(() => !!ticket.value.allowRemoteUrl)
const allowRouteNote = computed(() => !!ticket.value.allowRouteNote || !!ticket.value.repairThicken)
const allowHelper = computed(() => !!ticket.value.allowHelper)
const visitFollowup = computed(() => !!ticket.value.visitFollowup || !!ticket.value.repairThicken)
const allowQuote = computed(() => !!ticket.value.allowQuote)
const allowKnowledgeDeposit = computed(() => !!ticket.value.allowKnowledgeDeposit)
const allowTicketMerge = computed(() => !!ticket.value.allowTicketMerge)

const faultReasonLabel = computed(() => labels.value.faultReasonLabel || '故障原因')
const closeSummaryLabel = computed(() => labels.value.closeSummaryLabel || '处理过程摘要')
const partsNoteLabel = computed(() => labels.value.partsNoteLabel || '备件/耗材出库')
const partsWarnHint = computed(() => labels.value.partsWarnHint || '选填出库说明')
const serialNoLabel = computed(() => labels.value.serialNoLabel || '备件序列号')
const remoteUrlLabel = computed(() => labels.value.remoteUrlLabel || '远程协助备注')
const routeNoteLabel = computed(() => labels.value.routeNoteLabel || '当日路线备注')
const helperLabel = computed(() => labels.value.helperLabel || '协助人')
const quoteLabel = computed(() => labels.value.quoteLabel || '维修报价（元）')
const materialFeeLabel = computed(() => labels.value.materialFeeLabel || '材料费（元）')
const knowledgeLabel = computed(() => labels.value.knowledgeDepositLabel || '写入常见问题')
const parentTicketLabel = computed(() => labels.value.parentTicketLabel || '合并到主单编号')
const faultReasons = computed(() => {
  const list = ticket.value.faultReasons
  return Array.isArray(list) && list.length ? list : ['线路故障', '漏水渗水', '其他']
})

const form = reactive({
  faultReason: '',
  closeSummary: '',
  closeAttachUrl: '',
  partsNote: '',
  serialNo: '',
  remoteUrl: '',
  routeNote: '',
  helperUsername: '',
  visitDueAt: '',
  quoteYuan: null,
  materialFeeYuan: null,
  knowledgeDeposit: false,
  parentTicketId: null,
})
const targets = ref([])
const loading = ref(false)

function dispatchLabel(t) {
  const name = t.nickname || t.username
  const post = t.staffPost ? ` · ${t.staffPost}` : ''
  const duty = t.onDutyToday ? ' · 今日当班' : ''
  return `${name}${post}${duty}`
}

async function loadTargets() {
  if (!allowHelper.value) return
  try {
    const res = await http.get('/api/tickets/dispatch-targets')
    targets.value = res.data || []
  } catch {
    targets.value = []
  }
}

function resetFromRow() {
  const row = props.row || {}
  form.faultReason = row.faultReason || ''
  form.closeSummary = row.closeSummary || ''
  form.closeAttachUrl = row.closeAttachUrl || ''
  form.partsNote = row.partsNote || ''
  form.serialNo = row.serialNo || ''
  form.remoteUrl = row.remoteUrl || ''
  form.routeNote = row.routeNote || ''
  form.helperUsername = row.helperUsername || ''
  form.visitDueAt = row.visitDueAt ? String(row.visitDueAt).replace(' ', 'T') : ''
  form.quoteYuan = row.quoteYuan != null ? Number(row.quoteYuan) : null
  form.materialFeeYuan = row.materialFeeYuan != null ? Number(row.materialFeeYuan) : null
  form.knowledgeDeposit = !!row.knowledgeDeposit
  form.parentTicketId = row.parentTicketId || null
}

watch(
  () => props.modelValue,
  async (open) => {
    if (!open) return
    resetFromRow()
    await loadTargets()
  },
)

async function onUpload(opt) {
  const fd = new FormData()
  fd.append('file', opt.file)
  const res = await http.post('/api/upload', fd)
  form.closeAttachUrl = res.data?.url || res.data?.data?.url || ''
  if (!form.closeAttachUrl) ElMessage.warning('上传失败')
}

async function submit() {
  if (!props.row?.id) return
  if (requireFaultReason.value && !(form.faultReason || '').trim()) {
    ElMessage.warning(`请选择${faultReasonLabel.value}`)
    return
  }
  if (requireCloseSummary.value && !(form.closeSummary || '').trim()) {
    ElMessage.warning(`请填写${closeSummaryLabel.value}`)
    return
  }
  if (requireCloseAttach.value && !(form.closeAttachUrl || '').trim()) {
    ElMessage.warning('请上传结案附件')
    return
  }
  loading.value = true
  try {
    const extras = {
      attachUrl: form.closeAttachUrl || undefined,
      closeAttachUrl: form.closeAttachUrl || undefined,
      faultReason: form.faultReason || undefined,
      closeSummary: form.closeSummary || undefined,
      partsNote: form.partsNote || undefined,
      serialNo: form.serialNo || undefined,
      remoteUrl: form.remoteUrl || undefined,
      routeNote: form.routeNote || undefined,
      helperUsername: form.helperUsername || undefined,
      visitDueAt: form.visitDueAt || undefined,
      knowledgeDeposit: allowKnowledgeDeposit.value ? !!form.knowledgeDeposit : undefined,
    }
    if (allowQuote.value) {
      if (form.quoteYuan != null) extras.quoteYuan = form.quoteYuan
      if (form.materialFeeYuan != null) extras.materialFeeYuan = form.materialFeeYuan
    }
    if (allowTicketMerge.value && form.parentTicketId) {
      extras.parentTicketId = form.parentTicketId
    }
    await http.post(`/api/tickets/${props.row.id}/complete`, extras)
    ElMessage.success('已办结')
    emit('update:modelValue', false)
    emit('done')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.tip { margin: 0 0 12px; color: #475569; font-size: 14px; }
.link { margin-left: 8px; font-size: 13px; }
.compare {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  margin: 0 0 14px;
}
.cmp {
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 8px;
  min-height: 96px;
}
.cmp-lab { font-size: 12px; color: #64748b; margin-bottom: 6px; }
.cmp img { max-width: 100%; max-height: 140px; object-fit: contain; display: block; }
.muted { color: #94a3b8; font-size: 13px; }
</style>
