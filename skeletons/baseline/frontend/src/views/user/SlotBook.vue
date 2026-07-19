<template>
  <div>
    <section class="hero">
      <h1>选择时段</h1>
      <p v-if="itemTitle">为「{{ itemTitle }}」{{ resvVerb }}可用时段（约满不可再约）。</p>
      <div class="tools">
        <el-date-picker v-model="day" type="date" value-format="YYYY-MM-DD" @change="load" />
        <el-button type="primary" @click="load">查询</el-button>
        <el-button link @click="$router.push('/archive')">返回浏览</el-button>
      </div>
    </section>

    <div class="grid">
      <button
        v-for="s in list"
        :key="s.id"
        class="slot"
        :disabled="s.remain <= 0"
        @click="openReserve(s)"
      >
        <div class="t">{{ s.startAt }}</div>
        <div class="e">至 {{ s.endAt }}</div>
        <div class="r">剩余 {{ s.remain }} / {{ s.capacity }}</div>
      </button>
    </div>
    <div v-if="!list.length" class="empty">该日暂无时段，换一天试试或联系管理员生成。</div>

    <el-dialog v-model="visible" :title="`确认${resvNoun}`" width="480px" destroy-on-close>
      <p class="tip">时段 {{ pending?.startAt }} ~ {{ pending?.endAt }}</p>
      <el-form label-position="top">
        <el-form-item v-if="domain === 'DOM-PARKING'" label="车牌号" required>
          <el-input v-model="extra.plateNo" maxlength="16" placeholder="与资料一致" />
        </el-form-item>
        <template v-if="domain === 'DOM-HOSPITAL'">
          <el-form-item label="就诊人" required>
            <el-input v-model="extra.patientName" maxlength="32" />
          </el-form-item>
          <el-form-item label="初诊/复诊">
            <el-select v-model="extra.visitType" style="width:100%">
              <el-option label="初诊" value="初诊" />
              <el-option label="复诊" value="复诊" />
            </el-select>
          </el-form-item>
          <el-form-item label="症状简述">
            <el-input v-model="extra.symptomNote" maxlength="200" />
          </el-form-item>
        </template>
        <template v-if="domain === 'DOM-MEETING'">
          <el-form-item :label="remarkLabel" required>
            <el-input v-model="remark" maxlength="64" :placeholder="`请填写${remarkLabel}`" />
          </el-form-item>
          <el-form-item label="人数">
            <el-input-number v-model="extra.partySize" :min="1" :max="200" />
          </el-form-item>
        </template>
        <template v-if="domain === 'DOM-HOTEL'">
          <el-form-item label="入住人" required>
            <el-input v-model="extra.guestName" maxlength="32" />
          </el-form-item>
          <el-form-item label="入住人数">
            <el-input-number v-model="extra.guestCount" :min="1" :max="20" />
          </el-form-item>
        </template>
        <el-form-item v-if="domain === 'DOM-SALON'" label="偏好技师">
          <el-input v-model="extra.preferredStylist" maxlength="32" placeholder="选填" />
        </el-form-item>
        <el-form-item
          v-if="requireRemark && !['DOM-MEETING', 'DOM-PARKING', 'DOM-HOSPITAL', 'DOM-HOTEL'].includes(domain)"
          :label="remarkLabel"
          required
        >
          <el-input v-model="remark" maxlength="64" :placeholder="`请填写${remarkLabel}`" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="visible = false">取消</el-button>
        <el-button type="primary" :loading="loading" @click="submitReserve">确认{{ resvNoun }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import http from '../../api/http'
import { getDomain, reservationCopy } from '../../utils/domainSchema.js'

const route = useRoute()
const router = useRouter()
const domain = computed(() => getDomain())
const itemId = computed(() => Number(route.query.itemId || 0))
const itemTitle = computed(() => String(route.query.title || ''))
const resv = reservationCopy()
const resvNoun = computed(() => resv.label || '预约')
const resvVerb = computed(() => resv.verbs?.apply || '预约')
const requireRemark = computed(() => !!resv.requireRemark)
const remarkLabel = computed(() => resv.remarkLabel || '备注')
const structured = computed(() =>
  ['DOM-PARKING', 'DOM-HOSPITAL', 'DOM-MEETING', 'DOM-HOTEL', 'DOM-SALON'].includes(domain.value)
    || requireRemark.value)
const day = ref('2026-09-20')
const list = ref([])
const visible = ref(false)
const pending = ref(null)
const remark = ref('')
const loading = ref(false)
const extra = reactive({
  plateNo: '',
  patientName: '',
  visitType: '初诊',
  symptomNote: '',
  partySize: 1,
  guestName: '',
  guestCount: 1,
  preferredStylist: '',
})

async function load() {
  if (!itemId.value) return
  const res = await http.get('/api/slots', {
    params: { itemId: itemId.value, day: day.value || undefined },
  })
  list.value = res.data || []
}

async function openReserve(s) {
  if (!structured.value) {
    await ElMessageBox.confirm(`确认${resvVerb.value} ${s.startAt} ~ ${s.endAt}？`, resvNoun.value)
    await http.post('/api/slots/reserve', { slotId: s.id })
    ElMessage.success(`${resvNoun.value}成功`)
    router.push('/reservations')
    return
  }
  pending.value = s
  remark.value = ''
  Object.assign(extra, {
    plateNo: '', patientName: '', visitType: '初诊', symptomNote: '',
    partySize: 1, guestName: '', guestCount: 1, preferredStylist: '',
  })
  try {
    const me = await http.get('/api/profile')
    const extras = me.data?.extras || {}
    if (extras.plateNo) extra.plateNo = extras.plateNo
    if (extras.guestName) extra.guestName = extras.guestName
    if (extras.realName) {
      if (!extra.patientName) extra.patientName = extras.realName
      if (!extra.guestName) extra.guestName = extras.realName
    }
  } catch { /* ignore */ }
  visible.value = true
}

async function submitReserve() {
  if (!pending.value) return
  const note = (remark.value || '').trim()
  if (domain.value === 'DOM-PARKING' && !extra.plateNo.trim()) {
    ElMessage.warning('请填写车牌号')
    return
  }
  if (domain.value === 'DOM-HOSPITAL' && !extra.patientName.trim()) {
    ElMessage.warning('请填写就诊人')
    return
  }
  if (domain.value === 'DOM-HOTEL' && !extra.guestName.trim()) {
    ElMessage.warning('请填写入住人')
    return
  }
  if (domain.value === 'DOM-MEETING' && !note) {
    ElMessage.warning(`请填写${remarkLabel.value}`)
    return
  }
  if (
    requireRemark.value
    && !['DOM-MEETING', 'DOM-PARKING', 'DOM-HOSPITAL', 'DOM-HOTEL'].includes(domain.value)
    && !note
  ) {
    ElMessage.warning(`请填写${remarkLabel.value}`)
    return
  }
  loading.value = true
  try {
    await http.post('/api/slots/reserve', {
      slotId: pending.value.id,
      remark: note || undefined,
      plateNo: extra.plateNo || undefined,
      patientName: extra.patientName || undefined,
      visitType: extra.visitType || undefined,
      symptomNote: extra.symptomNote || undefined,
      subject: domain.value === 'DOM-MEETING' ? note : undefined,
      partySize: extra.partySize || undefined,
      guestName: extra.guestName || undefined,
      guestCount: extra.guestCount || undefined,
      preferredStylist: extra.preferredStylist || undefined,
    })
    ElMessage.success(`${resvNoun.value}成功`)
    visible.value = false
    router.push('/reservations')
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.hero { margin-bottom: 16px; }
.hero h1 { margin: 0 0 6px; font-size: 22px; }
.hero p { margin: 0 0 10px; color: #64748b; font-size: 13px; }
.tools { display: flex; gap: 8px; flex-wrap: wrap; align-items: center; }
.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: 10px;
}
.slot {
  text-align: left;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 12px;
  background: #fff;
  cursor: pointer;
}
.slot:disabled { opacity: 0.45; cursor: not-allowed; }
.t { font-weight: 600; font-size: 14px; }
.e, .r { margin-top: 4px; font-size: 12px; color: #64748b; }
.empty { text-align: center; color: #94a3b8; padding: 40px 0; }
.tip { margin: 0 0 8px; font-size: 13px; }
</style>
