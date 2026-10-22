import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import http from '../../api/http'
import GuestLoginHint from '../../components/GuestLoginHint.vue'
import { APP_DELIVERED } from '../../appDelivered.js'
import { getSchema, hasCap, hasTrait, isWalletEnabled, personLabel, reservationCopy } from '../../utils/domainSchema.js'
import { todayStr } from '../../utils/dates.js'
import { slotFillTone } from '../../utils/statusTone.js'
import {
  guestTeaserLimit,
  isGuestBrowseEnabled,
  isLoggedIn,
  requireLogin,
} from '../../utils/session.js'

const route = useRoute()
const router = useRouter()
/** 预约组页内构图：slotstrip / roomstate / vehiclecard；非预约域为空 */
const reserveSurface = computed(() => {
  const s = String(
    APP_DELIVERED?.reserveSurfaceStyle
      || import.meta.env.VITE_RESERVE_SURFACE_STYLE
      || '',
  ).trim()
  if (['slotstrip', 'roomstate', 'vehiclecard'].includes(s)) return s
  return ''
})

/** 房态用「可订/紧张/已满」；号源用余量；车型保留时段余量句 */
function slotRemainText(s) {
  if (!s) return ''
  const tone = slotFillTone(s.remain, s.capacity)
  if (reserveSurface.value === 'roomstate') {
    if (s.remain <= 0) return '已满'
    if (tone === 'warn') return '紧张'
    return '可订'
  }
  if (s.remain <= 0) {
    return slotHospital.value && hospitalWaitlistOn.value ? '已满可候补' : `剩余 0 / ${s.capacity}`
  }
  if (reserveSurface.value === 'slotstrip') {
    return tone === 'warn' ? `紧张 ${s.remain}` : `有号 ${s.remain}`
  }
  return `剩余 ${s.remain} / ${s.capacity}`
}

const isGuest = computed(() => isGuestBrowseEnabled() && !isLoggedIn())
const slotParking = computed(() => hasTrait('slotParking'))
const slotHospital = computed(() => hasTrait('slotHospital'))
const slotMeeting = computed(() => hasTrait('slotMeeting'))
const slotHotel = computed(() => hasTrait('slotHotel'))
const slotCarrent = computed(() => hasTrait('slotCarrent'))
const slotInstrument = computed(() => hasTrait('slotInstrument'))
const slotSalon = computed(() => hasTrait('slotSalon'))
const shoot = computed(() => hasCap('shoot'))
const boarding = computed(() => hasCap('boarding'))
const stayFrom = ref('')
const stayTo = ref('')
const petName = ref('')
const cares = ref([])
const careIds = ref([])
const photographers = ref([])
const bundles = ref([])
const bundleId = ref(null)
const bundlePrice = computed(() => {
  const row = bundles.value.find((b) => b.id === bundleId.value)
  return row ? row.priceYuan : ''
})
const itemId = computed(() => Number(route.query.itemId || 0))
const itemTitle = computed(() => String(route.query.title || ''))
const priceText = computed(() => {
  const raw = route.query.price
  if (raw == null || raw === '') return ''
  const n = Number(String(raw).replace(/[¥￥,\s]/g, ''))
  if (!Number.isFinite(n)) return ''
  return `¥${n.toFixed(2)}`
})
const unitPrice = computed(() => {
  const raw = route.query.price
  if (raw == null || raw === '') return 0
  const n = Number(String(raw).replace(/[¥￥,\s]/g, ''))
  return Number.isFinite(n) ? n : 0
})
const stayDays = computed(() => {
  if (!stayFrom.value || !stayTo.value) return 0
  const a = new Date(`${stayFrom.value}T00:00:00`)
  const b = new Date(`${stayTo.value}T00:00:00`)
  const n = Math.round((b.getTime() - a.getTime()) / 86400000)
  return n > 0 ? n : 0
})
const stayTotal = computed(() => {
  if (!stayDays.value || !unitPrice.value) return ''
  return (unitPrice.value * stayDays.value).toFixed(2)
})
const resv = reservationCopy()
const resvNoun = computed(() => resv.label || '预约')
const resvVerb = computed(() => resv.verbs?.apply || '预约')
const requireRemark = computed(() => !!resv.requireRemark)
const requireConfirm = computed(() => !!resv.requireConfirm)
const remarkLabel = computed(() => resv.remarkLabel || '备注')
const patientLabel = computed(() => resv.patientNameLabel || remarkLabel.value || '就诊人')
const visitTypeLabel = computed(
  () => getSchema()?.labels?.visitTypeLabel || resv.visitTypeLabel || '初诊/复诊',
)
const visitTypeOptions = computed(() => {
  const opts = resv.visitTypeOptions
  if (Array.isArray(opts) && opts.length) return opts
  return [
    { label: '初诊', value: '初诊' },
    { label: '复诊', value: '复诊' },
  ]
})
const visitTypeDefault = computed(() => resv.visitTypeDefault || visitTypeOptions.value[0]?.value || '初诊')
const symptomLabel = computed(() => resv.symptomNoteLabel || '症状简述')
const stylistLabel = computed(() => resv.stylistLabel || '偏好技师')
const rosterOn = computed(() => hasCap('staff_roster'))
const roomEquipOn = computed(() => hasCap('room_equipment'))
const equipSectionTitle = computed(
  () => getSchema()?.labels?.roomEquipmentSectionTitle || '配套设备',
)
const equipNames = ref([])
const onDutyLabel = computed(() => getSchema()?.labels?.staffRosterOnDutyHint || '当日当班')
const legendOk = computed(() => getSchema()?.labels?.slotCalendarLegendOk || '余量充足')
const legendWarn = computed(() => getSchema()?.labels?.slotCalendarLegendWarn || '余量紧张')
const legendFull = computed(() => getSchema()?.labels?.slotCalendarLegendFull || '已约满')
const cancelFreeHint = computed(() => getSchema()?.labels?.cancelFreeHoursHint || '')
const remindAheadHint = computed(() => getSchema()?.labels?.remindAheadHint || '')
const maintainBlockHint = computed(() => getSchema()?.labels?.maintainBlockHint || '')
const schLabels = computed(() => getSchema()?.labels || {})
const parkingCancelPenaltyHint = computed(() => schLabels.value.parkingCancelPenaltyHint || '')
const parkingShareSlotHint = computed(() => schLabels.value.parkingShareSlotHint || '')
const parkingOverlapHint = computed(() => schLabels.value.parkingOverlapHint || '')
const parkingDurationFeeHint = computed(() => schLabels.value.parkingDurationFeeHint || '')
const parkingDurationFeeLabel = computed(() => schLabels.value.parkingDurationFeeLabel || '')
void parkingDurationFeeLabel
const parkingOvertimeHint = computed(() => schLabels.value.parkingOvertimeHint || '')
const parkingOvertimeLabel = computed(() => schLabels.value.parkingOvertimeLabel || '')
void parkingOvertimeLabel
const parkingHourlyLabel = computed(() => schLabels.value.parkingHourlyLabel || '')
void parkingHourlyLabel
const parkingEntryLabel = computed(() => schLabels.value.parkingEntryLabel || '')
const parkingExitLabel = computed(() => schLabels.value.parkingExitLabel || '')
void parkingEntryLabel
void parkingExitLabel
const parkingPassRemainHint = computed(() => schLabels.value.parkingPassRemainHint || '次卡余次')
const passHintLabel = computed(() => schLabels.value.passHintLabel || '通行证提示')
void passHintLabel
const passHintAdminHint = computed(() => schLabels.value.passHintAdminHint || '')
void passHintAdminHint
const parkingPassRemain = ref(null)
const parkingCarpassText = computed(() => {
  const fromItem = String(itemMeta.value?.passHint || itemMeta.value?.pass_hint || '').trim()
  if (fromItem) return fromItem
  return schLabels.value.parkingCarpassHint || ''
})
const hospitalCancelCutoffHint = computed(() => schLabels.value.hospitalCancelCutoffHint || '')
const hospitalCancelCutoffLabel = computed(() => schLabels.value.hospitalCancelCutoffLabel || '')
void hospitalCancelCutoffLabel
const hospitalIdLimitHint = computed(() => schLabels.value.hospitalIdLimitHint || '')
const hospitalIdLimitLabel = computed(() => schLabels.value.hospitalIdLimitLabel || '')
void hospitalIdLimitLabel
const hospitalWaitlistHint = computed(() => schLabels.value.hospitalWaitlistHint || '')
const hospitalWaitlistOn = computed(() => !!(getSchema()?.hospitalWaitlist || getSchema()?.reserveThicken?.hospitalWaitlist))
const hospitalStopCalendarHint = computed(() => schLabels.value.hospitalStopCalendarHint || '')
const revisitPriorityHint = computed(() => schLabels.value.revisitPriorityHint || '')
const deptIntroLabel = computed(() => schLabels.value.deptIntroLabel || '科室介绍')
const deptIntroHint = computed(() => schLabels.value.deptIntroHint || '')
void deptIntroHint
const queueEstimateLabel = computed(() => schLabels.value.queueEstimateLabel || '排队预估')
const queueEstimateHint = computed(() => schLabels.value.queueEstimateHint || '')
void queueEstimateHint
const slotPeriodMorningLabel = computed(() => schLabels.value.slotPeriodMorningLabel || '上午')
const slotPeriodAfternoonLabel = computed(() => schLabels.value.slotPeriodAfternoonLabel || '下午')
const slotPeriodRemainHint = computed(() => schLabels.value.slotPeriodRemainHint || '本时段余号')
const slotKindLabel = computed(() => schLabels.value.slotKindLabel || '号源类型')
const slotKindClinic = computed(() => schLabels.value.slotKindClinic || '门诊')
const slotKindLab = computed(() => schLabels.value.slotKindLab || '检验检查')
const slotKindHint = computed(() => schLabels.value.slotKindHint || '')
const visitTypeHint = computed(() => schLabels.value.visitTypeHint || '')
const patientProfileOn = computed(() => !!getSchema()?.patientProfile)
const patientProfiles = ref([])
const itemMeta = ref({})
const deptIntroText = computed(() => {
  const t = itemMeta.value?.deptIntro || itemMeta.value?.dept_intro || ''
  return String(t || '').trim()
})
const queueEstimateText = computed(() => {
  const t = itemMeta.value?.queueEstimateHint || itemMeta.value?.queue_estimate_hint || ''
  const s = String(t || '').trim()
  return s || (slotHospital.value ? (schLabels.value.queueEstimateHint || '') : '')
})
const salonServiceMinutesLabel = computed(() => schLabels.value.salonServiceMinutesLabel || '')
const salonServiceMinutesHint = computed(() => (slotSalon.value ? (schLabels.value.salonServiceMinutesHint || '') : ''))
const itemServiceMinutes = computed(() => {
  const n = Number(itemMeta.value?.serviceMinutes ?? itemMeta.value?.service_minutes ?? 0)
  return Number.isFinite(n) && n > 0 ? n : 0
})
const salonTabooLabel = computed(() => schLabels.value.salonTabooLabel || '项目禁忌')
const salonTabooHint = computed(() => schLabels.value.salonTabooHint || '')
void salonTabooHint
const salonTabooText = computed(() => {
  if (!slotSalon.value) return ''
  const t = itemMeta.value?.tabooNote || itemMeta.value?.taboo_note || ''
  return String(t || '').trim()
})
const salonLateGraceHint = computed(() => (slotSalon.value ? (schLabels.value.salonLateGraceHint || '') : ''))
const salonWalletHint = computed(() => (
  slotSalon.value && getSchema()?.reserveThicken?.salonWallet
    ? (schLabels.value.salonWalletHint || '')
    : ''
))
const salonGalleryHint = computed(() => (
  slotSalon.value && getSchema()?.reserveThicken?.salonGallery
    ? (schLabels.value.salonGalleryHint || '')
    : ''
))
const salonRescheduleFeeHint = computed(() => schLabels.value.salonRescheduleFeeHint || '')
void salonRescheduleFeeHint
const salonCheckinScanHint = computed(() => schLabels.value.salonCheckinScanHint || '')
void salonCheckinScanHint
const salonVisitCountHint = computed(() => schLabels.value.salonVisitCountHint || '')
void salonVisitCountHint
const queueNoHint = computed(() => schLabels.value.queueNoHint || '')
void queueNoHint
const queueNoLabel = computed(() => schLabels.value.queueNoLabel || '')
void queueNoLabel
const slotKindFilter = ref('')
const slotKindOptions = computed(() => [
  { label: slotKindClinic.value, value: 'clinic' },
  { label: slotKindLab.value, value: 'lab' },
])
const itemSlotKind = computed(() => {
  const k = itemMeta.value?.slotKind || itemMeta.value?.slot_kind || ''
  return String(k || '').trim()
})
const filteredList = computed(() => {
  let rows = list.value || []
  if (slotHospital.value && slotKindFilter.value && itemSlotKind.value) {
    if (itemSlotKind.value !== slotKindFilter.value) rows = []
  }
  return rows
})
const periodGroups = computed(() => {
  if (!slotHospital.value) return []
  const rows = filteredList.value
  if (!rows.length) return []
  const am = []
  const pm = []
  for (const s of rows) {
    const h = Number(String(s.startAt || '').slice(11, 13))
    if (Number.isFinite(h) && h < 12) am.push(s)
    else pm.push(s)
  }
  const out = []
  if (am.length) {
    out.push({
      key: 'am',
      label: slotPeriodMorningLabel.value,
      remain: am.reduce((n, s) => n + Math.max(0, Number(s.remain) || 0), 0),
      slots: am,
    })
  }
  if (pm.length) {
    out.push({
      key: 'pm',
      label: slotPeriodAfternoonLabel.value,
      remain: pm.reduce((n, s) => n + Math.max(0, Number(s.remain) || 0), 0),
      slots: pm,
    })
  }
  return out
})
const dayFill = ref([])
const onDutyPeople = ref([])
const onDutyHint = computed(() => {
  if (!rosterOn.value || !day.value || !isLoggedIn()) return ''
  if (!onDutyPeople.value.length) return `${day.value} 暂无排班记录`
  const names = onDutyPeople.value
    .map((p) => `${p.nickname || p.username}（${p.shiftLabel || '全天'}）`)
    .join('、')
  return `${day.value} ${onDutyLabel.value}：${names}`
})
const guestLabel = computed(() => resv.guestNameLabel || (slotCarrent.value ? '驾驶人' : '入住人'))
const guestCountLabel = computed(() => {
  if (slotHotel.value && (schLabels.value.hotelRoommateLabel || resv.guestCountLabel)) {
    return schLabels.value.hotelRoommateLabel || resv.guestCountLabel
  }
  return resv.guestCountLabel || (slotCarrent.value ? '用车人数' : '入住人数')
})
const hotelOpsOn = computed(() => !!(slotHotel.value && (
  getSchema()?.reserveThicken?.hotelExtendStay
  || getSchema()?.reserveThicken?.hotelIdNo
  || getSchema()?.hotelNoticeRequired
)))
const hotelStayMultiNightHint = computed(() => (hotelOpsOn.value ? (schLabels.value.hotelStayMultiNightHint || '') : ''))
const hotelHourlyToFullHint = computed(() => (hotelOpsOn.value ? (schLabels.value.hotelHourlyToFullHint || '') : ''))
const hotelLateCheckoutHint = computed(() => (hotelOpsOn.value ? (schLabels.value.hotelLateCheckoutHint || '') : ''))
const hotelDepositBalanceHint = computed(() => (hotelOpsOn.value ? (schLabels.value.hotelDepositBalanceHint || '') : ''))
const hotelRoomKindLabel = computed(() => schLabels.value.hotelRoomKindLabel || '房时类型')
const hotelRoomKindHint = computed(() => schLabels.value.hotelRoomKindHint || '')
const hotelRoomKindText = computed(() => {
  if (!hotelOpsOn.value) return ''
  const k = itemMeta.value?.roomKind || itemMeta.value?.room_kind || ''
  if (k === 'hourly') return schLabels.value.hotelRoomKindHourly || '钟点房'
  if (k === 'full') return schLabels.value.hotelRoomKindFull || '全日房'
  return ''
})
const hotelIdNoLabel = computed(() => schLabels.value.hotelIdNoLabel || '证件号')
const hotelIdNoHint = computed(() => schLabels.value.hotelIdNoHint || '')
const hotelDepositLabel = computed(() => schLabels.value.hotelDepositLabel || '定金（元）')
const hotelBalanceLabel = computed(() => schLabels.value.hotelBalanceLabel || '尾款（元）')
const hotelBreakfastLabel = computed(() => schLabels.value.hotelBreakfastLabel || '早餐券（张）')
const hotelExtraBedLabel = computed(() => schLabels.value.hotelExtraBedLabel || '加床')
const hotelExtraBedHint = computed(() => schLabels.value.hotelExtraBedHint || '')
const hotelNoticeRequired = computed(() => !!(getSchema()?.hotelNoticeRequired || getSchema()?.entities?.reservation?.hotelNoticeRequired))
const hotelNoticeLabel = computed(() => schLabels.value.hotelNoticeLabel || '入住须知')
const hotelNoticeText = computed(() => (hotelOpsOn.value ? (schLabels.value.hotelNoticeText || '') : ''))
const hotelNoticeAckLabel = computed(() => schLabels.value.hotelNoticeAckLabel || '我已阅读并同意入住须知')
const carrentOpsOn = computed(() => !!(slotCarrent.value && (
  getSchema()?.reserveThicken?.carrentInsurance
  || getSchema()?.reserveThicken?.carrentLicenseExpire
  || getSchema()?.reserveThicken?.carrentInspectAck
)))
const carrentViolationHoldHint = computed(() => (carrentOpsOn.value ? (schLabels.value.carrentViolationHoldHint || '') : ''))
const carrentMileageOverHint = computed(() => (carrentOpsOn.value ? (schLabels.value.carrentMileageOverHint || '') : ''))
const carrentInsuranceHint = computed(() => schLabels.value.carrentInsuranceHint || '')
const carrentInsuranceLabel = computed(() => schLabels.value.carrentInsuranceLabel || '保险套餐')
const carrentInsuranceNone = computed(() => schLabels.value.carrentInsuranceNone || '不选')
const carrentInsuranceBasic = computed(() => schLabels.value.carrentInsuranceBasic || '基础险')
const carrentInsuranceFull = computed(() => schLabels.value.carrentInsuranceFull || '全险')
const carrentLicenseExpireLabel = computed(() => schLabels.value.carrentLicenseExpireLabel || '驾照有效期')
const carrentLicenseExpireHint = computed(() => schLabels.value.carrentLicenseExpireHint || '')
const carrentInspectAckLabel = computed(() => schLabels.value.carrentInspectAckLabel || '取还车验车确认')
const carrentInspectAckHint = computed(() => schLabels.value.carrentInspectAckHint || '')
const carrentNavHint = computed(() => (carrentOpsOn.value ? (schLabels.value.carrentNavHint || '') : ''))
const carrentPickupNavLabel = computed(() => schLabels.value.carrentPickupNavLabel || '取车点导航')
const carrentReturnNavLabel = computed(() => schLabels.value.carrentReturnNavLabel || '还车点导航')
const pickupNavUrl = computed(() => {
  const u = itemMeta.value?.pickupNavUrl || itemMeta.value?.pickup_nav_url || ''
  return String(u || '').trim()
})
const returnNavUrl = computed(() => {
  const u = itemMeta.value?.returnNavUrl || itemMeta.value?.return_nav_url || ''
  return String(u || '').trim()
})
const structured = computed(() =>
  slotParking.value
  || slotHospital.value
  || slotMeeting.value
  || slotHotel.value
  || slotCarrent.value
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
  idNo: '',
  depositYuan: 0,
  balanceYuan: 0,
  breakfastVouchers: 0,
  extraBed: false,
  noticeAck: false,
  licenseExpireOn: '',
  insurancePkg: '',
  inspectAck: false,
  trainingAck: false,
  videoUrl: '',
  recordingUrl: '',
  serviceTea: false,
  serviceDevice: false,
  equipBorrow: false,
})
const occupantsTip = ref('')
const hospitalRosterHint = computed(() => (
  slotHospital.value && getSchema()?.reserveThicken?.hospitalRoster
    ? (schLabels.value.hospitalRosterHint || '')
    : ''
))
const hospitalRosterLabel = computed(() => schLabels.value.hospitalRosterLabel || '')
const salonLeaveBlockHint = computed(() => (
  slotSalon.value && getSchema()?.reserveThicken?.salonLeaveBlock
    ? (schLabels.value.salonLeaveBlockHint || '')
    : ''
))
const salonLeaveBlockLabel = computed(() => schLabels.value.salonLeaveBlockLabel || '')
const salonLessonRemainOn = computed(() => !!(
  slotSalon.value && hasCap('lesson_pack') && getSchema()?.reserveThicken?.salonLessonRemain
))
const salonWalletOn = computed(() => !!(
  slotSalon.value && isWalletEnabled() && getSchema()?.reserveThicken?.salonWallet
))
const meetingEquipBorrowOn = computed(() => !!(
  slotMeeting.value && hasCap('room_equipment') && getSchema()?.reserveThicken?.meetingEquipBorrow
))
const meetingEquipBorrowLabel = computed(() => schLabels.value.meetingEquipBorrowLabel || '借用录制设备')
const meetingEquipBorrowHint = computed(() => schLabels.value.meetingEquipBorrowHint || '')
const lessonRemain = ref(null)
const walletBalance = ref(null)
const lessonRemainText = computed(() => {
  if (!salonLessonRemainOn.value || lessonRemain.value == null) return ''
  const lab = schLabels.value.salonLessonRemainLabel || '课时余次'
  const hint = schLabels.value.salonLessonRemainHint || ''
  const exp = lessonRemain.value.expireAt ? `，有效期至 ${lessonRemain.value.expireAt}` : ''
  return `${lab}：${lessonRemain.value.remainSessions ?? 0}${exp}${hint ? `（${hint}）` : ''}`
})
const walletBalanceText = computed(() => {
  if (!salonWalletOn.value || walletBalance.value == null) return ''
  const lab = schLabels.value.salonWalletLabel || '储值余额'
  return `${lab}：¥${Number(walletBalance.value || 0).toFixed(2)}`
})
const instrumentOpsOn = computed(() => !!(slotInstrument.value && (
  getSchema()?.reserveThicken?.instrumentTraining
  || getSchema()?.reserveThicken?.instrumentPurpose
  || getSchema()?.reserveThicken?.instrumentOvertime
)))
const instrumentTrainingRequired = computed(() => !!(getSchema()?.instrumentTrainingRequired
  || getSchema()?.reserveThicken?.instrumentTraining))
const instrumentTrainingAckLabel = computed(() => schLabels.value.instrumentTrainingAckLabel || '已完成上机培训')
const instrumentTrainingAckHint = computed(() => schLabels.value.instrumentTrainingAckHint || '')
const instrumentConflictHint = computed(() => (instrumentOpsOn.value ? (schLabels.value.instrumentConflictHint || '') : ''))
const instrumentMentorConfirmHint = computed(() => (instrumentOpsOn.value ? (schLabels.value.instrumentMentorConfirmHint || '') : ''))
const instrumentPurposeHint = computed(() => (instrumentOpsOn.value ? (schLabels.value.instrumentPurposeHint || '') : ''))
const instrumentOvertimeHint = computed(() => (instrumentOpsOn.value ? (schLabels.value.instrumentOvertimeHint || '') : ''))
const meetingConflictHint = computed(() => schLabels.value.meetingConflictHint || '')
const meetingMinDurationHint = computed(() => schLabels.value.meetingMinDurationHint || '')
const meetingMinDurationLabel = computed(() => schLabels.value.meetingMinDurationLabel || '')
  const meetingBlacklistHint = computed(() => schLabels.value.meetingBlacklistHint || '')
const meetingRequireConfirmHint = computed(() => schLabels.value.meetingRequireConfirmHint || '')
const meetingVideoLabel = computed(() => schLabels.value.meetingVideoLabel || '视频会议链接')
const meetingVideoHint = computed(() => schLabels.value.meetingVideoHint || '')
const meetingRecordingLabel = computed(() => schLabels.value.meetingRecordingLabel || '录屏链接')
const meetingRecordingHint = computed(() => schLabels.value.meetingRecordingHint || '')
const meetingServiceTeaLabel = computed(() => schLabels.value.meetingServiceTeaLabel || '需要茶水')
const meetingServiceDeviceLabel = computed(() => schLabels.value.meetingServiceDeviceLabel || '需要设备支持')
const meetingServiceHint = computed(() => schLabels.value.meetingServiceHint || '')

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
  await loadOnDuty()
  await loadEquip()
  await loadLessonRemain()
  await loadWalletBalance()
  await loadItemMeta()
  await loadParkingPassRemain()
  await loadDayFill()
}

async function loadItemMeta() {
  if (!itemId.value || (!slotHospital.value && !slotParking.value && !slotSalon.value)) {
    itemMeta.value = {}
    return
  }
  try {
    const res = await http.get(`/api/archive/${itemId.value}`)
    itemMeta.value = res.data || res || {}
  } catch {
    itemMeta.value = {}
  }
}

async function loadParkingPassRemain() {
  if (!slotParking.value || !getSchema()?.parkingPass || !isLoggedIn()) {
    parkingPassRemain.value = null
    return
  }
  try {
    const res = await http.get('/api/parking-passes/remain')
    parkingPassRemain.value = res.data?.remain ?? res?.remain ?? 0
  } catch {
    parkingPassRemain.value = null
  }
}

async function loadPatientProfiles() {
  if (!patientProfileOn.value || !isLoggedIn()) {
    patientProfiles.value = []
    return
  }
  try {
    const res = await http.get('/api/patient-profiles')
    patientProfiles.value = Array.isArray(res.data) ? res.data : []
  } catch {
    patientProfiles.value = []
  }
}

async function loadDayFill() {
  if (!itemId.value || !isLoggedIn()) {
    dayFill.value = []
    return
  }
  try {
    const month = String(day.value || todayStr()).slice(0, 7)
    const res = await http.get('/api/slots/day-fill', {
      params: { itemId: itemId.value, month },
    })
    dayFill.value = Array.isArray(res.data) ? res.data : []
  } catch {
    dayFill.value = []
  }
}

function pickDay(d) {
  day.value = d
  load()
}

async function loadEquip() {
  if (!roomEquipOn.value || !itemId.value) {
    equipNames.value = []
    return
  }
  try {
    const res = await http.get(`/api/archive/${itemId.value}`)
    const row = res.data || res || {}
    const n = row.equipmentNames
    equipNames.value = Array.isArray(n) ? n.filter(Boolean) : []
  } catch {
    equipNames.value = []
  }
}

async function loadOnDuty() {
  if (!rosterOn.value || !day.value) {
    onDutyPeople.value = []
    return
  }
  if (!isLoggedIn()) {
    onDutyPeople.value = []
    return
  }
  try {
    const res = await http.get('/api/staff-roster/on-duty', { params: { date: day.value } })
    onDutyPeople.value = Array.isArray(res.data) ? res.data : []
  } catch {
    onDutyPeople.value = []
  }
}

async function loadLessonRemain() {
  if (!salonLessonRemainOn.value || !isLoggedIn()) {
    lessonRemain.value = null
    return
  }
  try {
    const res = await http.get('/api/lessons/mine')
    lessonRemain.value = res.data || res || null
  } catch {
    lessonRemain.value = null
  }
}

async function loadWalletBalance() {
  if (!salonWalletOn.value || !isLoggedIn()) {
    walletBalance.value = null
    return
  }
  try {
    const res = await http.get('/api/loyalty/me')
    walletBalance.value = res.data?.balanceYuan ?? res?.balanceYuan ?? 0
  } catch {
    walletBalance.value = null
  }
}

function onDutyOptionLabel(p) {
  const name = p.nickname || p.username
  const shift = p.shiftLabel ? ` · ${p.shiftLabel}` : ''
  return `${name}${shift}`
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
    plateNo: '', patientName: '', visitType: visitTypeDefault.value, symptomNote: '',
    partySize: 1, guestName: '', guestCount: 1, preferredStylist: '',
    idNo: '', depositYuan: 0, balanceYuan: 0, breakfastVouchers: 0,
    extraBed: false, noticeAck: false,
    licenseExpireOn: '', insurancePkg: '', inspectAck: false,
    videoUrl: '', recordingUrl: '', serviceTea: false, serviceDevice: false,
    equipBorrow: false, trainingAck: false,
  })
  occupantsTip.value = ''
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
  await loadOnDuty()
  await loadPatientProfiles()
  if (patientProfiles.value.length && !extra.patientName) {
    extra.patientName = patientProfiles.value[0].patientName || ''
  }
  if (slotMeeting.value && s.id) {
    try {
      const res = await http.get(`/api/slots/${s.id}/occupants`)
      const rows = Array.isArray(res.data) ? res.data : []
      if (rows.length) {
        const names = rows.map((r) => r.username).filter(Boolean).join('、')
        occupantsTip.value = names ? `本时段已约：${names}` : ''
      }
    } catch { /* ignore */ }
  }
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
    ElMessage.warning(`请填写${patientLabel.value}`)
    return
  }
  if ((slotHotel.value || slotCarrent.value) && !extra.guestName.trim()) {
    ElMessage.warning(`请填写${guestLabel.value}`)
    return
  }
  if (hotelOpsOn.value && hotelNoticeRequired.value && !extra.noticeAck) {
    ElMessage.warning(hotelNoticeAckLabel.value || '请先勾选同意入住须知')
    return
  }
  if (instrumentOpsOn.value && instrumentTrainingRequired.value && !extra.trainingAck) {
    ElMessage.warning(instrumentTrainingAckLabel.value || '请先勾选已完成上机培训')
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
    && !slotCarrent.value
    && !note
  ) {
    ElMessage.warning(`请填写${remarkLabel.value}`)
    return
  }
  if (shoot.value && !bundleId.value) {
    ElMessage.warning('请选择套餐')
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
      idNo: hotelOpsOn.value ? (extra.idNo || undefined) : undefined,
      depositYuan: hotelOpsOn.value ? extra.depositYuan : undefined,
      balanceYuan: hotelOpsOn.value ? extra.balanceYuan : undefined,
      breakfastVouchers: hotelOpsOn.value ? extra.breakfastVouchers : undefined,
      extraBed: hotelOpsOn.value && extra.extraBed ? 1 : undefined,
      noticeAck: hotelOpsOn.value && extra.noticeAck ? 1 : undefined,
      licenseExpireOn: carrentOpsOn.value ? (extra.licenseExpireOn || undefined) : undefined,
      insurancePkg: carrentOpsOn.value ? (extra.insurancePkg || undefined) : undefined,
      inspectAck: carrentOpsOn.value && extra.inspectAck ? 1 : undefined,
      trainingAck: instrumentOpsOn.value && extra.trainingAck ? 1 : undefined,
      videoUrl: slotMeeting.value ? (extra.videoUrl || undefined) : undefined,
      recordingUrl: slotMeeting.value ? (extra.recordingUrl || undefined) : undefined,
      serviceTea: slotMeeting.value && extra.serviceTea ? 1 : undefined,
      serviceDevice: slotMeeting.value && extra.serviceDevice ? 1 : undefined,
      equipBorrow: meetingEquipBorrowOn.value && extra.equipBorrow ? 1 : undefined,
      bundleId: shoot.value ? bundleId.value : undefined,
    })
    ElMessage.success(requireConfirm.value ? `已提交，等待确认` : `${resvNoun.value}成功`)
    visible.value = false
    router.push('/reservations')
  } finally {
    loading.value = false
  }
}

function pickPhotographer(id) {
  const row = photographers.value.find((p) => p.id === id)
  router.replace({ path: route.path, query: { ...route.query, itemId: id, title: row?.title || '' } })
}

async function loadShoot() {
  if (!shoot.value) return
  const people = await http.get('/api/shoot/photographers')
  photographers.value = people.data || []
  const packs = await http.get('/api/shoot/bundles')
  bundles.value = packs.data || []
}

async function loadCares() {
  if (!boarding.value) return
  const res = await http.get('/api/boarding/cares')
  cares.value = res.data || []
}

async function submitStay() {
  if (!requireLogin(router)) return
  if (!itemId.value) {
    ElMessage.warning('请先选择寄养位')
    return
  }
  if (!stayFrom.value || !stayTo.value || stayDays.value < 1) {
    ElMessage.warning('离店须晚于入住')
    return
  }
  if (!petName.value.trim()) {
    ElMessage.warning(`请填写${guestLabel.value}`)
    return
  }
  loading.value = true
  try {
    await http.post('/api/slots/reserve', {
      itemId: itemId.value,
      stayFrom: stayFrom.value,
      stayTo: stayTo.value,
      guestName: petName.value.trim(),
      careIds: careIds.value,
    })
    ElMessage.success(`${resvNoun.value}成功`)
    router.push('/reservations')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  load()
  loadShoot()
  loadCares()
})
