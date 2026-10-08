<template>
  <div>
    <section class="hero">
      <h1>{{ label }}</h1>
      <p>已占坑的{{ resvNoun }}；可取消或改约到其它空闲时段，办结由管理端登记。</p>
      <p v-if="cancelFreeHint" class="hint">{{ cancelFreeHint }}</p>
      <p v-if="parkingCancelPenaltyHint" class="hint">{{ parkingCancelPenaltyHint }}</p>
      <p v-if="parkingDurationFeeHint" class="hint">{{ parkingDurationFeeHint }}</p>
      <p v-if="hospitalCancelCutoffHint" class="hint">{{ hospitalCancelCutoffHint }}</p>
      <p v-if="rescheduleMaxHint" class="hint">{{ rescheduleMaxHint }}</p>
      <p v-if="noShowLimitHint" class="hint">{{ noShowLimitHint }}</p>
      <p v-if="lateGraceHint" class="hint">{{ lateGraceHint }}</p>
      <p v-if="salonLateGraceHint" class="hint">{{ salonLateGraceHint }}</p>
      <p v-if="checkinCodeHint" class="hint">{{ checkinCodeLabel }}：{{ checkinCodeHint }}</p>
      <p v-if="queueNoHint" class="hint">{{ queueNoLabel }}：{{ queueNoHint }}</p>
      <p v-if="salonRescheduleFeeHint" class="hint">{{ salonRescheduleFeeLabel }}：{{ salonRescheduleFeeHint }}</p>
      <p v-if="salonWalletHint" class="hint">{{ salonWalletHint }}</p>
      <p v-if="salonVisitCountOn" class="hint">{{ salonVisitCountLabel }}：{{ visitCount }}（{{ salonVisitCountHint }}）</p>
      <p v-if="hotelExtendStayHint" class="hint">{{ hotelExtendStayLabel }}：{{ hotelExtendStayHint }}</p>
      <p v-if="reserveSuccessBody" class="hint">{{ reserveSuccessTitle }}：{{ reserveSuccessBody }}</p>
      <el-select v-model="status" clearable placeholder="全部状态" style="width:140px" @change="load">
        <el-option v-for="(lab, key) in states" :key="key" :label="lab" :value="key" />
      </el-select>
    </section>

    <article v-for="row in list" :key="row.id" class="card">
      <div class="hd">
        <strong>{{ row.itemTitle || row.title || (`${resvNoun} #` + row.id) }}</strong>
        <el-tag size="small" effect="plain">{{ states[row.status] || row.status }}</el-tag>
      </div>
      <p class="sub">{{ row.startAt }} ~ {{ row.endAt }}</p>
      <p v-if="row.plateNo" class="sub">车牌：{{ row.plateNo }}</p>
      <p v-if="row.entryAt && row.plateNo" class="sub">{{ parkingEntryLabel }}：{{ row.entryAt }}</p>
      <p v-if="row.exitAt" class="sub">{{ parkingExitLabel }}：{{ row.exitAt }}</p>
      <p v-if="row.durationFeeYuan != null && row.durationFeeYuan !== ''" class="sub">
        {{ parkingDurationFeeLabel }}：{{ row.durationFeeYuan }} 元
      </p>
      <p v-if="row.overtimeFeeYuan != null && Number(row.overtimeFeeYuan) > 0" class="sub">
        {{ overtimeFeeDisplayLabel }}：{{ row.overtimeFeeYuan }} 元
      </p>
      <p v-if="row.parkingPassUsed" class="sub">已使用停车次卡</p>
      <p v-if="row.patientName" class="sub">
        {{ patientLabel }}：{{ row.patientName }}
        <template v-if="row.visitType"> · {{ row.visitType }}</template>
      </p>
      <p v-if="row.symptomNote" class="sub">{{ symptomLabel }}：{{ row.symptomNote }}</p>
      <p v-if="row.subject" class="sub">主题：{{ row.subject }}<template v-if="row.partySize"> · {{ row.partySize }} 人</template></p>
      <p v-if="row.guestName" class="sub">{{ guestLabel }}：{{ row.guestName }}<template v-if="row.guestCount"> · {{ row.guestCount }} 人</template></p>
      <p v-if="hotelOpsOn && (row.stayFrom || row.stayTo)" class="sub">
        入住 {{ row.stayFrom || '—' }} ~ 离店 {{ row.stayTo || '—' }}
      </p>
      <p v-if="hotelOpsOn && row.idNoMasked" class="sub">{{ hotelIdNoMaskedLabel }}：{{ row.idNoMasked }}</p>
      <p v-if="hotelOpsOn && Number(row.depositYuan) > 0" class="sub">{{ hotelDepositLabel }}：{{ row.depositYuan }} 元</p>
      <p v-if="hotelOpsOn && Number(row.balanceYuan) > 0" class="sub">{{ hotelBalanceLabel }}：{{ row.balanceYuan }} 元</p>
      <p v-if="hotelOpsOn && Number(row.breakfastVouchers) > 0" class="sub">{{ hotelBreakfastLabel }}：{{ row.breakfastVouchers }}</p>
      <p v-if="hotelOpsOn && row.extraBed" class="sub">{{ hotelExtraBedLabel }}：是</p>
      <p v-if="hotelOpsOn && Number(row.lateCheckoutFeeYuan) > 0" class="sub">
        {{ hotelLateCheckoutLabel }}：{{ row.lateCheckoutFeeYuan }} 元
      </p>
      <p v-if="hotelOpsOn && row.checkoutChecklist" class="sub">{{ hotelCheckoutChecklistLabel }}：{{ row.checkoutChecklist }}</p>
      <p v-if="carrentOpsOn && row.licenseExpireOn" class="sub">{{ carrentLicenseExpireLabel }}：{{ row.licenseExpireOn }}</p>
      <p v-if="carrentOpsOn && row.insurancePkg" class="sub">{{ carrentInsuranceLabel }}：{{ insurancePkgText(row.insurancePkg) }}</p>
      <p v-if="carrentOpsOn && row.inspectAck" class="sub">{{ carrentInspectAckLabel }}：已确认</p>
      <p v-if="carrentOpsOn && Number(row.violationHoldYuan) > 0" class="sub">
        {{ carrentViolationHoldLabel }}：{{ row.violationHoldYuan }} 元
        <template v-if="row.violationHoldNote"> · {{ row.violationHoldNote }}</template>
      </p>
      <p v-if="carrentOpsOn && Number(row.mileageOverFeeYuan) > 0" class="sub">
        {{ carrentMileageOverLabel }}：{{ row.mileageOverFeeYuan }} 元
      </p>
      <p v-if="carrentOpsOn && Number(row.etcFeeYuan) > 0" class="sub">{{ carrentEtcFeeLabel }}：{{ row.etcFeeYuan }} 元</p>
      <p v-if="carrentOpsOn && row.violationAttach" class="sub">
        <a :href="row.violationAttach" target="_blank" rel="noopener">{{ carrentViolationAttachLabel }}</a>
      </p>
      <p v-if="instrumentOpsOn && row.trainingAck" class="sub">{{ instrumentTrainingAckLabel }}：已确认</p>
      <p v-if="instrumentOpsOn && row.consumableNote" class="sub">{{ instrumentConsumableLabel }}：{{ row.consumableNote }}</p>
      <p v-if="instrumentOpsOn && row.status === 'pending'" class="sub">{{ instrumentMentorConfirmHint }}</p>
      <p v-if="row.preferredStylist" class="sub">{{ stylistLabel }}：{{ row.preferredStylist }}</p>
      <p v-if="row.queueNo" class="sub">{{ queueNoLabel }}：{{ row.queueNo }}</p>
      <p v-if="row.status === 'waitlisted'" class="sub">{{ hospitalWaitlistHint || '候补中，有空位将按顺序转正' }}</p>
      <p v-if="row.meetingStage === 'in_progress'" class="sub">{{ meetingStageInProgress }}</p>
      <p v-if="row.meetingStage === 'ended'" class="sub">{{ meetingStageEnded }}</p>
      <p v-if="row.doorCode" class="sub">{{ meetingDoorCodeLabel }}：{{ row.doorCode }}</p>
      <p v-if="row.videoUrl" class="sub">
        <a :href="row.videoUrl" target="_blank" rel="noopener">{{ meetingVideoLabel }}</a>
      </p>
      <p v-if="row.recordingUrl" class="sub">
        <a :href="row.recordingUrl" target="_blank" rel="noopener">{{ meetingRecordingLabel }}</a>
      </p>
      <p v-if="row.checkinToken" class="sub" :title="meetingCheckinCodeHint || salonCheckinScanHint">
        {{ salonCheckinScanOn ? salonCheckinScanLabel : meetingCheckinCodeLabel }}：{{ row.checkinToken }}
      </p>
      <CodeQrBlock
        v-if="salonCheckinScanOn && row.checkinToken"
        :code="String(row.checkinToken)"
        :label="salonCheckinScanLabel"
      />
      <p v-if="Number(row.rescheduleFeeYuan) > 0" class="sub">
        {{ salonRescheduleFeeLabel }}：{{ row.rescheduleFeeYuan }} 元
      </p>
      <p v-if="row.minutesAttach" class="sub">{{ meetingMinutesLabel }}：已上传</p>
      <p v-if="row.serviceTea || row.serviceDevice || row.equipBorrow" class="sub">
        服务：
        <template v-if="row.serviceTea">{{ meetingServiceTeaLabel }} </template>
        <template v-if="row.serviceDevice">{{ meetingServiceDeviceLabel }} </template>
        <template v-if="row.equipBorrow">{{ meetingEquipBorrowLabel }}</template>
      </p>
      <p v-if="row.remark && !row.plateNo && !row.patientName && !row.subject && !row.guestName" class="sub">备注：{{ row.remark }}</p>
      <p class="sub">申请于 {{ row.createdAt }}</p>
      <p v-if="row.entryAt" class="sub">办结于 {{ row.entryAt }}</p>
      <p v-if="row.checkedInAt" class="sub">
        已签到 {{ row.checkedInAt }}
        <template v-if="row.lateFlag"> · {{ lateFlagLabel }}</template>
      </p>
      <p v-if="allowRating && row.rating" class="sub">评价：{{ row.rating }} 星<template v-if="row.ratingRemark"> · {{ row.ratingRemark }}</template></p>
      <div class="acts">
        <el-button
          v-if="canCheckIn(row)"
          size="small"
          type="success"
          @click="checkIn(row)"
        >{{ checkInLabel }}</el-button>
        <el-button
          v-if="hotelOpsOn && (row.status === 'pending' || row.status === 'confirmed')"
          size="small"
          type="primary"
          @click="extendStay(row)"
        >{{ hotelExtendStayLabel }}</el-button>
        <el-button
          v-if="row.status === 'pending' || row.status === 'confirmed'"
          size="small"
          type="primary"
          @click="openReschedule(row)"
        >改约</el-button>
        <el-button
          v-if="row.status === 'pending' || row.status === 'confirmed' || row.status === 'waitlisted'"
          size="small"
          @click="cancel(row)"
        >取消{{ resvNoun }}</el-button>
        <el-button
          v-if="canUploadMinutes(row)"
          size="small"
          @click="openMinutes(row)"
        >{{ meetingMinutesLabel }}</el-button>
        <el-button
          v-if="canRate(row)"
          size="small"
          type="warning"
          @click="openRate(row)"
        >评价</el-button>
      </div>
    </article>
    <div v-if="!list.length" class="empty">暂无{{ resvNoun }}</div>
    <div class="pager">
      <el-pagination
        v-model:current-page="page"
        v-model:page-size="size"
        background
        layout="total, sizes, prev, pager, next"
        :page-sizes="[10, 20, 50]"
        :total="total"
        @current-change="load"
        @size-change="load"
      />
    </div>

    <el-dialog v-model="dlgVisible" title="改约到新时段" width="480px" destroy-on-close>
      <p class="dlg-tip">原时段将释放；请选择同资源的其它空闲时段。</p>
      <el-select v-model="newSlotId" filterable placeholder="选择时段" style="width: 100%">
        <el-option
          v-for="s in slotOptions"
          :key="s.id"
          :label="`${s.startAt} ~ ${s.endAt}（余 ${Math.max(0, (s.capacity || 0) - (s.booked || 0))}）`"
          :value="s.id"
          :disabled="s.id === currentSlotId || (s.booked || 0) >= (s.capacity || 0)"
        />
      </el-select>
      <template #footer>
        <el-button @click="dlgVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" :disabled="!newSlotId" @click="submitReschedule">确认改约</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="minutesVisible" :title="meetingMinutesLabel" width="440px" destroy-on-close>
      <p class="dlg-tip">{{ meetingMinutesHint }}</p>
      <el-input v-model="minutesUrl" maxlength="512" placeholder="粘贴纪要文件链接或地址" />
      <template #footer>
        <el-button @click="minutesVisible = false">取消</el-button>
        <el-button type="primary" :loading="minutesSaving" @click="submitMinutes">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="checkinVisible" :title="checkinCodeLabel" width="400px" destroy-on-close>
      <p class="dlg-tip">{{ checkinCodeHint || '请输入科室报到口令完成签到' }}</p>
      <el-input
        v-model="checkinCodeInput"
        maxlength="32"
        :placeholder="checkinCodeLabel"
        @keyup.enter="submitCheckin"
      />
      <template #footer>
        <el-button @click="checkinVisible = false">取消</el-button>
        <el-button type="primary" :loading="checkinSaving" @click="submitCheckin">确认报到</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="rateVisible" title="服务评价" width="440px" destroy-on-close>
      <p v-if="rateTitle" class="dlg-tip">对「{{ rateTitle }}」评分</p>
      <el-form label-width="72px">
        <el-form-item label="评分" required>
          <el-rate v-model="rateScore" :max="5" />
        </el-form-item>
        <el-form-item label="短评">
          <el-input
            v-model="rateRemark"
            type="textarea"
            :rows="2"
            maxlength="200"
            show-word-limit
            placeholder="选填"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="rateVisible = false">取消</el-button>
        <el-button type="primary" :loading="rateSaving" @click="submitRate">提交</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import http from '../../api/http'
import CodeQrBlock from '../../components/CodeQrBlock.vue'
import { getSchema, menuLabel, reservationCopy } from '../../utils/domainSchema.js'

const resv = reservationCopy()
const resvNoun = computed(() => resv.label || '预约')
const label = menuLabel('user', 'my_reservations', `我的${resvNoun.value}`)
const patientLabel = computed(() => resv.patientNameLabel || resv.remarkLabel || '就诊人')
const symptomLabel = computed(() => resv.symptomNoteLabel || '症状')
const stylistLabel = computed(() => resv.stylistLabel || '偏好技师')
const guestLabel = computed(() => resv.guestNameLabel || '入住人')
const states = computed(() => getSchema()?.entities?.reservation?.states || {})
const allowRating = computed(() => !!getSchema()?.entities?.reservation?.allowRating)
const labels = computed(() => getSchema()?.labels || {})
const cancelFreeHint = computed(() => labels.value.cancelFreeHoursHint || '')
const parkingCancelPenaltyHint = computed(() => labels.value.parkingCancelPenaltyHint || '')
const parkingDurationFeeHint = computed(() => labels.value.parkingDurationFeeHint || '')
const parkingDurationFeeLabel = computed(() => labels.value.parkingDurationFeeLabel || '停车时长费')
const parkingOvertimeLabel = computed(() => labels.value.parkingOvertimeLabel || '超时加收')
const parkingEntryLabel = computed(() => labels.value.parkingEntryLabel || '入场时间')
const parkingExitLabel = computed(() => labels.value.parkingExitLabel || '离场时间')
const hospitalCancelCutoffHint = computed(() => labels.value.hospitalCancelCutoffHint || '')
const rescheduleMaxHint = computed(() => labels.value.rescheduleMaxHint || '')
const noShowLimitHint = computed(() => labels.value.noShowLimitHint || '')
const lateGraceHint = computed(() => labels.value.lateGraceHint || '')
const reserveSuccessTitle = computed(() => labels.value.reserveSuccessTitle || '')
const reserveSuccessBody = computed(() => labels.value.reserveSuccessBody || '')
const checkInLabel = computed(() => labels.value.checkInLabel || '签到')
const lateFlagLabel = computed(() => labels.value.lateFlagLabel || '迟到')
const checkinCodeLabel = computed(() => labels.value.checkinCodeLabel || '报到口令')
const checkinCodeHint = computed(() => labels.value.checkinCodeHint || '')
const checkinCodeAdminHint = computed(() => labels.value.checkinCodeAdminHint || '')
void checkinCodeAdminHint
const queueNoLabel = computed(() => labels.value.queueNoLabel || '候诊号')
const queueNoHint = computed(() => labels.value.queueNoHint || '')
const hospitalWaitlistHint = computed(() => labels.value.hospitalWaitlistHint || '')
const hospitalCheckinOn = computed(
  () => !!(
    getSchema()?.reserveThicken?.hospitalCheckinCode
    || getSchema()?.reserveThicken?.salonCheckinCode
    || labels.value.checkinCodeLabel
  ),
)
const salonOpsOn = computed(() => !!(getSchema()?.reserveThicken?.salonCheckinCode
  || getSchema()?.reserveThicken?.salonVisitCount
  || getSchema()?.reserveThicken?.salonRescheduleFee))
const hotelOpsOn = computed(() => !!(getSchema()?.reserveThicken?.hotelExtendStay
  || getSchema()?.reserveThicken?.hotelIdNo
  || getSchema()?.hotelNoticeRequired))
const hotelExtendStayLabel = computed(() => labels.value.hotelExtendStayLabel || '续住')
const hotelExtendStayHint = computed(() => (hotelOpsOn.value ? (labels.value.hotelExtendStayHint || '') : ''))
const hotelIdNoMaskedLabel = computed(() => labels.value.hotelIdNoMaskedLabel || '证件号（脱敏）')
const hotelDepositLabel = computed(() => labels.value.hotelDepositLabel || '定金（元）')
const hotelBalanceLabel = computed(() => labels.value.hotelBalanceLabel || '尾款（元）')
const hotelBreakfastLabel = computed(() => labels.value.hotelBreakfastLabel || '早餐券（张）')
const hotelExtraBedLabel = computed(() => labels.value.hotelExtraBedLabel || '加床')
const hotelLateCheckoutLabel = computed(() => labels.value.hotelLateCheckoutLabel || '延迟退房加收')
const hotelCheckoutChecklistLabel = computed(() => labels.value.hotelCheckoutChecklistLabel || '查房清单')
const carrentOpsOn = computed(() => !!(getSchema()?.reserveThicken?.carrentEtcFee
  || getSchema()?.reserveThicken?.carrentInsurance
  || getSchema()?.reserveThicken?.carrentMileageOver))
const carrentLicenseExpireLabel = computed(() => labels.value.carrentLicenseExpireLabel || '驾照有效期')
const carrentInsuranceLabel = computed(() => labels.value.carrentInsuranceLabel || '保险套餐')
const carrentInspectAckLabel = computed(() => labels.value.carrentInspectAckLabel || '取还车验车确认')
const carrentViolationHoldLabel = computed(() => labels.value.carrentViolationHoldLabel || '违章预留押（元）')
const carrentMileageOverLabel = computed(() => labels.value.carrentMileageOverLabel || '里程超支加收')
const carrentEtcFeeLabel = computed(() => labels.value.carrentEtcFeeLabel || 'ETC 通行费')
const carrentViolationAttachLabel = computed(() => labels.value.carrentViolationAttachLabel || '违章附件')
const instrumentOpsOn = computed(() => !!(getSchema()?.reserveThicken?.instrumentOvertime
  || getSchema()?.reserveThicken?.instrumentTraining
  || getSchema()?.reserveThicken?.instrumentMentor
  || getSchema()?.traits?.slotInstrument))
const instrumentOvertimeLabel = computed(() => labels.value.instrumentOvertimeLabel || '超时机时费')
const instrumentTrainingAckLabel = computed(() => labels.value.instrumentTrainingAckLabel || '已完成上机培训')
const instrumentConsumableLabel = computed(() => labels.value.instrumentConsumableLabel || '耗材领用')
const instrumentMentorConfirmHint = computed(() => labels.value.instrumentMentorConfirmHint || '提交后须导师或管理员确认后方可使用。')
const overtimeFeeDisplayLabel = computed(() => (
  instrumentOpsOn.value ? instrumentOvertimeLabel.value : parkingOvertimeLabel.value
))
function insurancePkgText(v) {
  if (v === 'basic') return labels.value.carrentInsuranceBasic || '基础险'
  if (v === 'full') return labels.value.carrentInsuranceFull || '全险'
  return v || ''
}
const salonLateGraceHint = computed(() => (salonOpsOn.value ? (labels.value.salonLateGraceHint || '') : ''))
const salonRescheduleFeeLabel = computed(() => labels.value.salonRescheduleFeeLabel || '改约手续费（元）')
const salonRescheduleFeeHint = computed(() => labels.value.salonRescheduleFeeHint || '')
const salonWalletHint = computed(() => labels.value.salonWalletHint || '')
const salonVisitCountOn = computed(() => !!(getSchema()?.reserveThicken?.salonVisitCount))
const salonVisitCountLabel = computed(() => labels.value.salonVisitCountLabel || '到店次数')
const salonVisitCountHint = computed(() => labels.value.salonVisitCountHint || '')
const salonCheckinScanOn = computed(() => !!(getSchema()?.reserveThicken?.salonCheckinScan))
const salonCheckinScanLabel = computed(() => labels.value.salonCheckinScanLabel || '到店签到码')
const salonCheckinScanHint = computed(() => labels.value.salonCheckinScanHint || '')
const visitCount = ref(0)
const meetingMinutesOn = computed(
  () => !!(getSchema()?.meetingMinutesRequired || getSchema()?.reserveThicken?.meetingMinutes),
)
const meetingMinutesLabel = computed(() => labels.value.meetingMinutesLabel || '会议纪要附件')
const meetingMinutesHint = computed(() => labels.value.meetingMinutesHint || '')
const meetingDoorCodeLabel = computed(() => labels.value.meetingDoorCodeLabel || '门禁密码')
const meetingDoorCodeHint = computed(() => labels.value.meetingDoorCodeHint || '')
void meetingDoorCodeHint
const meetingVideoLabel = computed(() => labels.value.meetingVideoLabel || '视频会议链接')
const meetingRecordingLabel = computed(() => labels.value.meetingRecordingLabel || '录屏链接')
const meetingCheckinCodeLabel = computed(() => labels.value.meetingCheckinCodeLabel || '签到码')
const meetingCheckinCodeHint = computed(() => labels.value.meetingCheckinCodeHint || '')
  const meetingStageInProgress = computed(() => labels.value.meetingStageInProgress || '召开中')
  const meetingStageEnded = computed(() => labels.value.meetingStageEnded || '已结束')
const meetingServiceTeaLabel = computed(() => labels.value.meetingServiceTeaLabel || '茶水')
const meetingServiceDeviceLabel = computed(() => labels.value.meetingServiceDeviceLabel || '设备')
const meetingEquipBorrowLabel = computed(() => labels.value.meetingEquipBorrowLabel || '借用录制设备')
const minutesVisible = ref(false)
const minutesSaving = ref(false)
const minutesId = ref(0)
const minutesUrl = ref('')
const list = ref([])
const total = ref(0)
const page = ref(1)
const size = ref(10)
const status = ref(null)
const checkinVisible = ref(false)
const checkinSaving = ref(false)
const checkinId = ref(0)
const checkinCodeInput = ref('')

const dlgVisible = ref(false)
const saving = ref(false)
const currentId = ref(0)
const currentSlotId = ref(0)
const newSlotId = ref(null)
const slotOptions = ref([])

const rateVisible = ref(false)
const rateSaving = ref(false)
const rateId = ref(0)
const rateTitle = ref('')
const rateScore = ref(5)
const rateRemark = ref('')

function canRate(row) {
  if (!allowRating.value || !row) return false
  if (row.status !== 'completed') return false
  return row.rating == null || row.rating === '' || row.rating === undefined
}

function canCheckIn(row) {
  if (!row) return false
  if (row.status !== 'pending' && row.status !== 'confirmed') return false
  return !row.checkedInAt || row.checkedInAt === 'null'
}

function canUploadMinutes(row) {
  if (!meetingMinutesOn.value || !row) return false
  if (row.status !== 'confirmed' && row.status !== 'completed') return false
  return !row.minutesAttach
}

function openMinutes(row) {
  minutesId.value = row.id
  minutesUrl.value = row.minutesAttach || ''
  minutesVisible.value = true
}

async function submitMinutes() {
  const url = minutesUrl.value.trim()
  if (!url) {
    ElMessage.warning('请填写纪要附件地址')
    return
  }
  minutesSaving.value = true
  try {
    await http.post(`/api/slots/reservations/${minutesId.value}/meeting`, {
      minutesAttach: url,
    })
    ElMessage.success('纪要已保存')
    minutesVisible.value = false
    load()
  } finally {
    minutesSaving.value = false
  }
}

async function checkIn(row) {
  if (hospitalCheckinOn.value) {
    checkinId.value = row.id
    checkinCodeInput.value = ''
    checkinVisible.value = true
    return
  }
  await http.post(`/api/slots/reservations/${row.id}/checkin`, {})
  ElMessage.success('签到成功')
  load()
}

async function submitCheckin() {
  const code = checkinCodeInput.value.trim()
  if (!code) {
    ElMessage.warning(`请填写${checkinCodeLabel.value}`)
    return
  }
  checkinSaving.value = true
  try {
    await http.post(`/api/slots/reservations/${checkinId.value}/checkin`, {
      checkinCode: code,
    })
    ElMessage.success('报到成功')
    checkinVisible.value = false
    load()
  } finally {
    checkinSaving.value = false
  }
}

async function loadVisitCount() {
  if (!salonVisitCountOn.value) {
    visitCount.value = 0
    return
  }
  try {
    const res = await http.get('/api/slots/my-visit-count')
    visitCount.value = Number(res.data?.visitCount ?? res?.visitCount ?? 0) || 0
  } catch {
    visitCount.value = 0
  }
}

async function load() {
  const res = await http.get('/api/slots/reservations', {
    params: { page: page.value, size: size.value, status: status.value || undefined },
  })
  list.value = res.data?.list || []
  total.value = res.data?.total || 0
  await loadVisitCount()
}

async function extendStay(row) {
  const { value } = await ElMessageBox.prompt(
    hotelExtendStayHint.value || '请填写新的离店日期',
    hotelExtendStayLabel.value,
    {
      inputPlaceholder: 'YYYY-MM-DD',
      inputValue: row.stayTo || '',
      confirmButtonText: '确认续住',
      cancelButtonText: '取消',
    },
  )
  const stayTo = String(value || '').trim()
  if (!stayTo) {
    ElMessage.warning('请填写离店日期')
    return
  }
  await http.post(`/api/slots/reservations/${row.id}/extend-stay`, { stayTo })
  ElMessage.success('已续住')
  load()
}

async function cancel(row) {
  await ElMessageBox.confirm(`取消「${row.itemTitle}」的${resvNoun.value}？`, '取消')
  await http.post(`/api/slots/reservations/${row.id}/cancel`)
  ElMessage.success('已取消')
  load()
}

async function openReschedule(row) {
  currentId.value = row.id
  currentSlotId.value = Number(row.slotId) || 0
  newSlotId.value = null
  slotOptions.value = []
  dlgVisible.value = true
  if (!row.itemId) {
    ElMessage.warning('无法加载时段')
    return
  }
  try {
    const res = await http.get('/api/slots', { params: { itemId: row.itemId } })
    slotOptions.value = Array.isArray(res.data) ? res.data : (res.data?.list || [])
  } catch {
    slotOptions.value = []
  }
}

async function submitReschedule() {
  if (!newSlotId.value) return
  saving.value = true
  try {
    await http.post(`/api/slots/reservations/${currentId.value}/reschedule`, {
      slotId: newSlotId.value,
    })
    ElMessage.success('改约成功')
    dlgVisible.value = false
    load()
  } finally {
    saving.value = false
  }
}

function openRate(row) {
  rateId.value = row.id
  rateTitle.value = row.itemTitle || row.title || `${resvNoun.value} #${row.id}`
  rateScore.value = 5
  rateRemark.value = ''
  rateVisible.value = true
}

async function submitRate() {
  if (!rateScore.value || rateScore.value < 1) {
    ElMessage.warning('请选择 1～5 分')
    return
  }
  rateSaving.value = true
  try {
    await http.post(`/api/slots/reservations/${rateId.value}/rate`, {
      rating: rateScore.value,
      remark: rateRemark.value,
    })
    ElMessage.success('感谢评价')
    rateVisible.value = false
    load()
  } finally {
    rateSaving.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.hero { margin-bottom: 16px; }
.hero h1 { margin: 0 0 6px; font-size: 22px; }
.hero p { margin: 0 0 10px; color: var(--portal-muted, #64748b); font-size: 13px; }
.hero .hint { margin: 0 0 6px; font-size: 12px; }
.card {
  background: var(--portal-surface, #fff);
  border: var(--portal-border-width, 1px) solid var(--portal-line, #e2e8f0);
  border-radius: var(--portal-radius, 12px);
  box-shadow: var(--portal-shadow, none);
  padding: var(--portal-pad, 14px) 16px;
  margin-bottom: var(--portal-gap, 12px);
}
.hd { display: flex; justify-content: space-between; gap: 8px; align-items: center; }
.sub { margin: 4px 0 0; color: var(--portal-muted, #64748b); font-size: 12px; }
.acts { margin-top: 10px; display: flex; flex-wrap: wrap; gap: 6px; }
.empty { text-align: center; color: var(--portal-muted, #94a3b8); padding: 40px 0; }
.pager { margin-top: 16px; display: flex; justify-content: flex-end; }
.dlg-tip { margin: 0 0 12px; color: var(--portal-muted, #64748b); font-size: 13px; }
</style>
