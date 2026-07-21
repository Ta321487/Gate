<template>
  <div>
    <section class="hero">
      <h1>选择时段</h1>
      <p v-if="itemTitle">为「{{ itemTitle }}」{{ resvVerb }}可用时段（约满不可再约）。</p>
      <p v-else class="warn">请先从目录选择要{{ resvVerb }}的对象，再进入本页选时段。</p>
      <div class="tools">
        <el-date-picker
          v-model="day"
          type="date"
          value-format="YYYY-MM-DD"
          :disabled="!itemId"
          @change="load"
        />
        <el-button type="primary" :disabled="!itemId" @click="load">查询</el-button>
        <el-button link @click="$router.push('/archive')">{{ itemId ? '返回浏览' : '去选择' }}</el-button>
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
    <div v-if="!itemId" class="empty">请先选择后再查看可{{ resvVerb }}时段。</div>
    <div v-else-if="!list.length" class="empty">该日暂无可{{ resvVerb }}时段，请换一天试试。</div>
    <GuestLoginHint />

    <el-dialog v-model="visible" :title="`确认${resvNoun}`" width="480px" destroy-on-close>
      <p class="tip">时段 {{ pending?.startAt }} ~ {{ pending?.endAt }}</p>
      <el-form label-position="top">
        <el-form-item v-if="slotParking" label="车牌号" required>
          <el-input v-model="extra.plateNo" maxlength="16" placeholder="与资料一致" />
        </el-form-item>
        <template v-if="slotHospital">
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
        <template v-if="slotMeeting">
          <el-form-item :label="remarkLabel" required>
            <el-input v-model="remark" maxlength="64" :placeholder="`请填写${remarkLabel}`" />
          </el-form-item>
          <el-form-item label="人数">
            <el-input-number v-model="extra.partySize" :min="1" :max="200" />
          </el-form-item>
        </template>
        <template v-if="slotHotel">
          <el-form-item label="入住人" required>
            <el-input v-model="extra.guestName" maxlength="32" />
          </el-form-item>
          <el-form-item label="入住人数">
            <el-input-number v-model="extra.guestCount" :min="1" :max="20" />
          </el-form-item>
        </template>
        <el-form-item v-if="slotSalon" label="偏好技师">
          <el-input v-model="extra.preferredStylist" maxlength="32" placeholder="选填" />
        </el-form-item>
        <el-form-item
          v-if="requireRemark && !slotMeeting && !slotParking && !slotHospital && !slotHotel"
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
import GuestLoginHint from '../../components/GuestLoginHint.vue'
import { hasTrait, personLabel, reservationCopy } from '../../utils/domainSchema.js'
import { todayStr } from '../../utils/dates.js'
import {
  guestTeaserLimit,
  isGuestBrowseEnabled,
  isLoggedIn,
  requireLogin,
} from '../../utils/session.js'

const route = useRoute()
const router = useRouter()
const isGuest = computed(() => isGuestBrowseEnabled() && !isLoggedIn())
const slotParking = computed(() => hasTrait('slotParking'))
const slotHospital = computed(() => hasTrait('slotHospital'))
const slotMeeting = computed(() => hasTrait('slotMeeting'))
const slotHotel = computed(() => hasTrait('slotHotel'))
const slotSalon = computed(() => hasTrait('slotSalon'))
const itemId = computed(() => Number(route.query.itemId || 0))
const itemTitle = computed(() => String(route.query.title || ''))
const resv = reservationCopy()
const resvNoun = computed(() => resv.label || '预约')
const resvVerb = computed(() => resv.verbs?.apply || '预约')
const requireRemark = computed(() => !!resv.requireRemark)
const requireConfirm = computed(() => !!resv.requireConfirm)
const remarkLabel = computed(() => resv.remarkLabel || '备注')
const structured = computed(() =>
  slotParking.value
  || slotHospital.value
  || slotMeeting.value
  || slotHotel.value
  || slotSalon.value
  || requireRemark.value)

const day = ref(todayStr())
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
  if (!itemId.value) {
    list.value = []
    return
  }
  const res = await http.get('/api/slots', {
    params: { itemId: itemId.value, day: day.value || undefined },
  })
  let rows = res.data || []
  // 所选日无时段时，落到该资源最近有档的一天，避免种子日与「今天」错位
  if (!rows.length) {
    const all = await http.get('/api/slots', { params: { itemId: itemId.value } })
    const pool = all.data || []
    if (pool.length) {
      const nextDay = String(pool[0].startAt || '').slice(0, 10)
      if (nextDay && nextDay !== day.value) {
        day.value = nextDay
        rows = pool.filter((s) => String(s.startAt || '').startsWith(nextDay))
      }
    }
  }
  list.value = isGuest.value ? rows.slice(0, guestTeaserLimit()) : rows
}

async function openReserve(s) {
  if (!requireLogin(router)) return
  if (!structured.value) {
    await ElMessageBox.confirm(`确认${resvVerb.value} ${s.startAt} ~ ${s.endAt}？`, resvNoun.value)
    await http.post('/api/slots/reserve', { slotId: s.id })
    ElMessage.success(requireConfirm.value ? `已提交，等待确认` : `${resvNoun.value}成功`)
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
    const nick = (me.data?.nickname || '').trim()
    if (nick) {
      if (!extra.patientName) extra.patientName = nick
      if (!extra.guestName) extra.guestName = nick
    }
  } catch { /* ignore */ }
  visible.value = true
}

async function submitReserve() {
  if (!pending.value) return
  const note = (remark.value || '').trim()
  if (slotParking.value && !extra.plateNo.trim()) {
    ElMessage.warning('请填写车牌号')
    return
  }
  if (slotHospital.value && !extra.patientName.trim()) {
    ElMessage.warning('请填写就诊人')
    return
  }
  if (slotHotel.value && !extra.guestName.trim()) {
    ElMessage.warning('请填写入住人')
    return
  }
  if (slotMeeting.value && !note) {
    ElMessage.warning(`请填写${remarkLabel.value}`)
    return
  }
  if (
    requireRemark.value
    && !slotMeeting.value
    && !slotParking.value
    && !slotHospital.value
    && !slotHotel.value
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
      subject: slotMeeting.value ? note : undefined,
      partySize: extra.partySize || undefined,
      guestName: extra.guestName || undefined,
      guestCount: extra.guestCount || undefined,
      preferredStylist: extra.preferredStylist || undefined,
    })
    ElMessage.success(requireConfirm.value ? `已提交，等待确认` : `${resvNoun.value}成功`)
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
.hero p.warn { color: #b45309; }
.tools { display: flex; gap: 8px; flex-wrap: wrap; align-items: center; }
.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: 10px;
}
.slot {
  text-align: left;
  border: var(--portal-border-width, 1px) solid var(--portal-line, #e2e8f0);
  border-radius: var(--portal-radius, 10px);
  box-shadow: var(--portal-shadow, none);
  padding: var(--portal-pad, 12px);
  background: var(--portal-surface, #fff);
  cursor: pointer;
}
.slot:disabled { opacity: 0.45; cursor: not-allowed; }
.t { font-weight: 600; font-size: 14px; }
.e, .r { margin-top: 4px; font-size: 12px; color: #64748b; }
.empty { text-align: center; color: #94a3b8; padding: 40px 0; }
.tip { margin: 0 0 8px; font-size: 13px; }
</style>
