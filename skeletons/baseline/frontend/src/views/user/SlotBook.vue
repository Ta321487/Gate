<template>
  <div>
    <section class="hero">
      <h1>选择时段</h1>
      <p v-if="itemTitle">为「{{ itemTitle }}」{{ resvVerb }}可用时段（约满不可再约）。</p>
      <p v-else class="warn">请先从目录选择要{{ resvVerb }}的对象，再进入本页选时段。</p>
      <p v-if="roomEquipOn && equipNames.length" class="equip-line">
        {{ equipSectionTitle }}：{{ equipNames.join('、') }}
      </p>
      <div class="tools">
        <div v-if="!boarding" class="day-wrap" :class="{ 'has-duty': rosterOn && onDutyPeople.length }">
          <el-date-picker
            v-model="day"
            type="date"
            value-format="YYYY-MM-DD"
            :disabled="!itemId"
            @change="load"
          />
          <i v-if="rosterOn && onDutyPeople.length" class="duty-dot" title="当日有当班" />
        </div>
        <el-select
          v-if="shoot"
          :model-value="itemId || null"
          placeholder="请选择摄影师"
          style="width: 180px"
          @change="pickPhotographer"
        >
          <el-option v-for="p in photographers" :key="p.id" :label="p.title" :value="p.id" />
        </el-select>
        <el-button v-if="!boarding" type="primary" :disabled="!itemId" @click="load">查询</el-button>
        <el-button link @click="$router.push('/archive')">{{ itemId ? '返回浏览' : '去选择' }}</el-button>
      </div>
    </section>

    <p v-if="cancelFreeHint" class="rule-hint">{{ cancelFreeHint }}</p>
    <p v-if="remindAheadHint" class="rule-hint">{{ remindAheadHint }}</p>
    <p v-if="maintainBlockHint" class="rule-hint">{{ maintainBlockHint }}</p>
    <p v-if="meetingMinDurationHint" class="rule-hint">
      <template v-if="meetingMinDurationLabel">{{ meetingMinDurationLabel }}：</template>{{ meetingMinDurationHint }}
    </p>
    <p v-if="meetingConflictHint" class="rule-hint">{{ meetingConflictHint }}</p>
    <p v-if="instrumentConflictHint" class="rule-hint">{{ instrumentConflictHint }}</p>
    <p v-if="instrumentMentorConfirmHint" class="rule-hint">{{ instrumentMentorConfirmHint }}</p>
    <p v-if="instrumentPurposeHint" class="rule-hint">{{ instrumentPurposeHint }}</p>
    <p v-if="instrumentOvertimeHint" class="rule-hint">{{ instrumentOvertimeHint }}</p>
    <p v-if="meetingBlacklistHint" class="rule-hint">{{ meetingBlacklistHint }}</p>
    <p v-if="parkingCancelPenaltyHint" class="rule-hint">{{ parkingCancelPenaltyHint }}</p>
    <p v-if="parkingShareSlotHint" class="rule-hint">{{ parkingShareSlotHint }}</p>
    <p v-if="parkingOverlapHint" class="rule-hint">{{ parkingOverlapHint }}</p>
    <p v-if="parkingDurationFeeHint" class="rule-hint">{{ parkingDurationFeeHint }}</p>
    <p v-if="parkingOvertimeHint" class="rule-hint">{{ parkingOvertimeHint }}</p>
    <p v-if="parkingCarpassText" class="rule-hint">{{ parkingCarpassText }}</p>
    <p v-if="slotParking && parkingPassRemain != null" class="rule-hint">
      {{ parkingPassRemainHint }}：{{ parkingPassRemain }}
    </p>
    <p v-if="hospitalCancelCutoffHint" class="rule-hint">{{ hospitalCancelCutoffHint }}</p>
    <p v-if="hospitalIdLimitHint" class="rule-hint">{{ hospitalIdLimitHint }}</p>
    <p v-if="hospitalWaitlistHint" class="rule-hint">{{ hospitalWaitlistHint }}</p>
    <p v-if="hospitalStopCalendarHint" class="rule-hint">{{ hospitalStopCalendarHint }}</p>
    <p v-if="revisitPriorityHint" class="rule-hint">{{ revisitPriorityHint }}</p>
    <p v-if="deptIntroText" class="rule-hint">{{ deptIntroLabel }}：{{ deptIntroText }}</p>
    <p v-if="queueEstimateText" class="rule-hint">{{ queueEstimateLabel }}：{{ queueEstimateText }}</p>
    <p v-if="salonServiceMinutesHint" class="rule-hint">
      <template v-if="salonServiceMinutesLabel">{{ salonServiceMinutesLabel }}：</template>{{ salonServiceMinutesHint }}
      <template v-if="itemServiceMinutes">（本项目 {{ itemServiceMinutes }} 分钟）</template>
    </p>
    <p v-if="salonTabooText" class="rule-hint">{{ salonTabooLabel }}：{{ salonTabooText }}</p>
    <p v-if="salonLateGraceHint" class="rule-hint">{{ salonLateGraceHint }}</p>
    <p v-if="hospitalRosterHint" class="rule-hint">
      <template v-if="hospitalRosterLabel">{{ hospitalRosterLabel }}：</template>{{ hospitalRosterHint }}
    </p>
    <p v-if="salonLeaveBlockHint" class="rule-hint">
      <template v-if="salonLeaveBlockLabel">{{ salonLeaveBlockLabel }}：</template>{{ salonLeaveBlockHint }}
    </p>
    <p v-if="salonLessonRemainOn && lessonRemainText" class="rule-hint">{{ lessonRemainText }}</p>
    <p v-if="salonWalletOn && walletBalanceText" class="rule-hint">{{ walletBalanceText }}</p>
    <p v-if="salonWalletHint" class="rule-hint">{{ salonWalletHint }}</p>
    <p v-if="salonGalleryHint" class="rule-hint">{{ salonGalleryHint }}</p>
    <p v-if="hotelStayMultiNightHint" class="rule-hint">{{ hotelStayMultiNightHint }}</p>
    <p v-if="hotelHourlyToFullHint" class="rule-hint">{{ hotelHourlyToFullHint }}</p>
    <p v-if="hotelRoomKindHint && hotelRoomKindText" class="rule-hint">
      {{ hotelRoomKindLabel }}：{{ hotelRoomKindText }}（{{ hotelRoomKindHint }}）
    </p>
    <p v-if="hotelLateCheckoutHint" class="rule-hint">{{ hotelLateCheckoutHint }}</p>
    <p v-if="hotelDepositBalanceHint" class="rule-hint">{{ hotelDepositBalanceHint }}</p>
    <p v-if="carrentViolationHoldHint" class="rule-hint">{{ carrentViolationHoldHint }}</p>
    <p v-if="carrentMileageOverHint" class="rule-hint">{{ carrentMileageOverHint }}</p>
    <p v-if="carrentInsuranceHint" class="rule-hint">{{ carrentInsuranceHint }}</p>
    <p v-if="carrentNavHint && (pickupNavUrl || returnNavUrl)" class="rule-hint">
      <template v-if="pickupNavUrl">
        <a :href="pickupNavUrl" target="_blank" rel="noopener">{{ carrentPickupNavLabel }}</a>
      </template>
      <template v-if="pickupNavUrl && returnNavUrl"> · </template>
      <template v-if="returnNavUrl">
        <a :href="returnNavUrl" target="_blank" rel="noopener">{{ carrentReturnNavLabel }}</a>
      </template>
      <span v-if="carrentNavHint">（{{ carrentNavHint }}）</span>
    </p>
    <div v-if="slotHospital && slotKindOptions.length" class="kind-bar">
      <span class="kind-lab">{{ slotKindLabel }}</span>
      <el-radio-group v-model="slotKindFilter" size="small" @change="load">
        <el-radio-button label="">全部</el-radio-button>
        <el-radio-button
          v-for="opt in slotKindOptions"
          :key="opt.value"
          :label="opt.value"
        >{{ opt.label }}</el-radio-button>
      </el-radio-group>
      <span v-if="slotKindHint" class="tip">{{ slotKindHint }}</span>
    </div>
    <div v-if="!boarding && itemId" class="cal-legend">
      <span class="leg tone-ok">{{ legendOk }}</span>
      <span class="leg tone-warn">{{ legendWarn }}</span>
      <span class="leg tone-full">{{ legendFull }}</span>
    </div>
    <div v-if="!boarding && dayFill.length" class="day-fill">
      <button
        v-for="d in dayFill"
        :key="d.day"
        type="button"
        class="day-chip"
        :class="`tone-${d.tone || 'ok'}`"
        :disabled="d.tone === 'full'"
        @click="pickDay(d.day)"
      >
        {{ String(d.day).slice(8) }}
      </button>
    </div>
    <template v-if="!boarding && slotHospital && periodGroups.length">
      <section v-for="g in periodGroups" :key="g.key" class="period-block">
        <h3 class="period-hd">
          {{ g.label }}
          <span class="period-remain">{{ slotPeriodRemainHint }} {{ g.remain }}</span>
        </h3>
        <div class="grid">
          <button
            v-for="s in g.slots"
            :key="s.id"
            class="slot"
            :class="`tone-${slotFillTone(s.remain, s.capacity)}`"
            :disabled="s.remain <= 0 && !hospitalWaitlistOn"
            @click="openReserve(s)"
          >
            <div class="t">{{ s.startAt }}</div>
            <div class="e">至 {{ s.endAt }}</div>
            <div class="r">
              <template v-if="s.remain > 0">剩余 {{ s.remain }} / {{ s.capacity }}</template>
              <template v-else>{{ hospitalWaitlistOn ? '已满可候补' : `剩余 0 / ${s.capacity}` }}</template>
            </div>
          </button>
        </div>
      </section>
    </template>
    <div v-else-if="!boarding" class="grid">
      <button
        v-for="s in list"
        :key="s.id"
        class="slot"
        :class="`tone-${slotFillTone(s.remain, s.capacity)}`"
        :disabled="s.remain <= 0 && !(slotHospital && hospitalWaitlistOn)"
        @click="openReserve(s)"
      >
        <div class="t">{{ s.startAt }}</div>
        <div class="e">至 {{ s.endAt }}</div>
        <div class="r">剩余 {{ s.remain }} / {{ s.capacity }}</div>
      </button>
    </div>
    <div v-if="!boarding && !itemId" class="empty">请先选择后再查看可{{ resvVerb }}时段。</div>
    <div v-else-if="!boarding && !list.length" class="empty">该日暂无可{{ resvVerb }}时段，请换一天试试。</div>
    <section v-if="boarding" class="boarding">
      <p v-if="!itemId" class="empty">请先选择寄养位。</p>
      <el-form v-else label-position="top">
        <el-form-item label="入住日期" required>
          <el-date-picker v-model="stayFrom" type="date" value-format="YYYY-MM-DD" />
        </el-form-item>
        <el-form-item label="离店日期" required>
          <el-date-picker v-model="stayTo" type="date" value-format="YYYY-MM-DD" />
        </el-form-item>
        <el-form-item :label="guestLabel" required>
          <el-input v-model="petName" maxlength="32" />
        </el-form-item>
        <el-form-item label="特殊要求">
          <el-checkbox-group v-model="careIds">
            <el-checkbox v-for="c in cares" :key="c.id" :label="c.id">{{ c.name }}</el-checkbox>
          </el-checkbox-group>
          <p v-if="!cares.length" class="tip">暂无可选要求。</p>
        </el-form-item>
        <p v-if="stayTotal" class="tip">金额 {{ stayTotal }} 元（日价 × {{ stayDays }} 天）</p>
        <el-button type="primary" :loading="loading" @click="submitStay">确认{{ resvNoun }}</el-button>
      </el-form>
    </section>
    <p v-if="rosterOn && onDutyHint" class="duty-hint">{{ onDutyHint }}</p>
    <GuestLoginHint />

    <el-dialog v-model="visible" :title="`确认${resvNoun}`" width="480px" destroy-on-close>
      <p class="tip">时段 {{ pending?.startAt }} ~ {{ pending?.endAt }}</p>
      <p v-if="(slotHotel || slotCarrent) && priceText" class="tip price">
        {{ slotCarrent ? '日租金' : '房价' }} {{ priceText }}（将计入订单金额）
      </p>
      <el-form label-position="top">
        <el-form-item v-if="slotParking" label="车牌号" required>
          <el-input v-model="extra.plateNo" maxlength="16" placeholder="与资料一致" />
          <p v-if="parkingOverlapHint" class="tip">{{ parkingOverlapHint }}</p>
        </el-form-item>
        <template v-if="slotHospital">
          <el-form-item :label="patientLabel" required>
            <el-select
              v-if="patientProfileOn && patientProfiles.length"
              v-model="extra.patientName"
              filterable
              allow-create
              default-first-option
              style="width:100%"
              :placeholder="`选择或填写${patientLabel}`"
            >
              <el-option
                v-for="p in patientProfiles"
                :key="p.id"
                :label="`${p.patientName}（${p.relationLabel || '本人'}）`"
                :value="p.patientName"
              />
            </el-select>
            <el-input v-else v-model="extra.patientName" maxlength="32" />
          </el-form-item>
          <el-form-item :label="visitTypeLabel">
            <el-select v-model="extra.visitType" style="width:100%">
              <el-option
                v-for="opt in visitTypeOptions"
                :key="opt.value"
                :label="opt.label"
                :value="opt.value"
              />
            </el-select>
            <p v-if="visitTypeHint" class="tip">{{ visitTypeHint }}</p>
          </el-form-item>
          <el-form-item :label="symptomLabel">
            <el-input v-model="extra.symptomNote" maxlength="200" />
          </el-form-item>
          <p v-if="pending && pending.remain <= 0 && hospitalWaitlistOn" class="tip">
            {{ hospitalWaitlistHint || '号源已满，确认后将加入候补' }}
          </p>
        </template>
        <template v-if="slotMeeting">
          <el-form-item :label="remarkLabel" required>
            <el-input v-model="remark" maxlength="64" :placeholder="`请填写${remarkLabel}`" />
          </el-form-item>
          <el-form-item label="人数">
            <el-input-number v-model="extra.partySize" :min="1" :max="200" />
          </el-form-item>
          <el-form-item :label="meetingVideoLabel">
            <el-input v-model="extra.videoUrl" maxlength="255" :placeholder="meetingVideoHint || '选填外链'" />
          </el-form-item>
          <el-form-item :label="meetingRecordingLabel">
            <el-input v-model="extra.recordingUrl" maxlength="255" :placeholder="meetingRecordingHint || '选填外链'" />
          </el-form-item>
          <el-form-item :label="meetingServiceHint || '附加服务'">
            <el-checkbox v-model="extra.serviceTea">{{ meetingServiceTeaLabel }}</el-checkbox>
            <el-checkbox v-model="extra.serviceDevice">{{ meetingServiceDeviceLabel }}</el-checkbox>
          </el-form-item>
          <el-form-item v-if="meetingEquipBorrowOn" :label="meetingEquipBorrowLabel">
            <el-checkbox v-model="extra.equipBorrow">{{ meetingEquipBorrowHint || meetingEquipBorrowLabel }}</el-checkbox>
          </el-form-item>
          <p v-if="meetingRequireConfirmHint" class="tip">{{ meetingRequireConfirmHint }}</p>
          <p v-if="meetingConflictHint" class="tip">{{ meetingConflictHint }}</p>
          <p v-if="occupantsTip" class="tip">{{ occupantsTip }}</p>
        </template>
        <template v-if="slotHotel || slotCarrent">
          <el-form-item :label="guestLabel" required>
            <el-input v-model="extra.guestName" maxlength="32" />
          </el-form-item>
          <el-form-item :label="guestCountLabel">
            <el-input-number v-model="extra.guestCount" :min="1" :max="20" />
          </el-form-item>
        </template>
        <template v-if="hotelOpsOn">
          <el-form-item :label="hotelIdNoLabel">
            <el-input v-model="extra.idNo" maxlength="32" :placeholder="hotelIdNoHint || '选填'" />
          </el-form-item>
          <el-form-item :label="hotelDepositLabel">
            <el-input-number v-model="extra.depositYuan" :min="0" :precision="2" :step="10" />
          </el-form-item>
          <el-form-item :label="hotelBalanceLabel">
            <el-input-number v-model="extra.balanceYuan" :min="0" :precision="2" :step="10" />
          </el-form-item>
          <el-form-item :label="hotelBreakfastLabel">
            <el-input-number v-model="extra.breakfastVouchers" :min="0" :max="99" />
          </el-form-item>
          <el-form-item :label="hotelExtraBedLabel">
            <el-switch v-model="extra.extraBed" />
            <span v-if="hotelExtraBedHint" class="tip" style="margin-left:8px">{{ hotelExtraBedHint }}</span>
          </el-form-item>
          <p v-if="hotelNoticeText" class="tip">{{ hotelNoticeLabel }}：{{ hotelNoticeText }}</p>
          <el-form-item v-if="hotelNoticeRequired" :label="hotelNoticeAckLabel" required>
            <el-checkbox v-model="extra.noticeAck">{{ hotelNoticeAckLabel }}</el-checkbox>
          </el-form-item>
        </template>
        <template v-if="carrentOpsOn">
          <el-form-item :label="carrentLicenseExpireLabel">
            <el-date-picker
              v-model="extra.licenseExpireOn"
              type="date"
              value-format="YYYY-MM-DD"
              :placeholder="carrentLicenseExpireHint || '选择日期'"
              style="width: 100%"
            />
          </el-form-item>
          <el-form-item :label="carrentInsuranceLabel">
            <el-select v-model="extra.insurancePkg" clearable :placeholder="carrentInsuranceHint || '选填'" style="width: 100%">
              <el-option :label="carrentInsuranceNone" value="" />
              <el-option :label="carrentInsuranceBasic" value="basic" />
              <el-option :label="carrentInsuranceFull" value="full" />
            </el-select>
          </el-form-item>
          <el-form-item :label="carrentInspectAckLabel">
            <el-checkbox v-model="extra.inspectAck">{{ carrentInspectAckHint || carrentInspectAckLabel }}</el-checkbox>
          </el-form-item>
        </template>
        <el-form-item v-if="shoot" label="套餐" required>
          <el-select v-model="bundleId" placeholder="请选择" style="width: 100%">
            <el-option v-for="b in bundles" :key="b.id" :label="`${b.name}  ${b.priceYuan} 元`" :value="b.id" />
          </el-select>
          <p v-if="!bundles.length" class="tip">暂无可选套餐。</p>
          <p v-else-if="bundlePrice" class="tip">套餐金额 {{ bundlePrice }} 元</p>
        </el-form-item>
        <el-form-item v-if="slotSalon && !shoot" :label="stylistLabel">
          <el-select
            v-if="rosterOn"
            v-model="extra.preferredStylist"
            clearable
            filterable
            allow-create
            default-first-option
            placeholder="可选当日当班技师"
            style="width: 100%"
          >
            <el-option
              v-for="p in onDutyPeople"
              :key="p.username"
              :label="onDutyOptionLabel(p)"
              :value="p.username"
            />
          </el-select>
          <el-input
            v-else
            v-model="extra.preferredStylist"
            maxlength="32"
            placeholder="选填"
          />
        </el-form-item>
        <p v-if="rosterOn && onDutyPeople.length" class="duty-list">
          {{ onDutyLabel }}：
          <span v-for="(p, i) in onDutyPeople" :key="p.username">
            {{ i ? '、' : '' }}{{ p.nickname || p.username }}（{{ p.shiftLabel || '全天' }}）
          </span>
        </p>
        <el-form-item
          v-if="requireRemark && !slotMeeting && !slotParking && !slotHospital && !slotHotel && !slotCarrent"
          :label="remarkLabel"
          required
        >
          <el-input v-model="remark" maxlength="64" :placeholder="`请填写${remarkLabel}`" />
        </el-form-item>
        <template v-if="instrumentOpsOn">
          <el-form-item v-if="instrumentTrainingRequired" :label="instrumentTrainingAckLabel" required>
            <el-checkbox v-model="extra.trainingAck">{{ instrumentTrainingAckHint || instrumentTrainingAckLabel }}</el-checkbox>
          </el-form-item>
        </template>
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
</script>

<style scoped>
.hero { margin-bottom: 16px; }
.hero h1 { margin: 0 0 6px; font-size: 22px; }
.hero p { margin: 0 0 10px; color: var(--portal-muted, #64748b); font-size: 13px; }
.hero p.warn { color: #b45309; }
.rule-hint { margin: 0 0 6px; font-size: 12px; color: var(--portal-muted, #64748b); }
.equip-line { margin: 0 0 10px !important; font-size: 13px; color: #0f766e; }
.duty-hint { margin: 8px 0 0; font-size: 13px; color: var(--portal-muted, #64748b); }
.duty-list { margin: 0 0 8px; font-size: 12px; color: var(--el-text-color-secondary); }
.day-wrap { position: relative; display: inline-flex; align-items: center; }
.duty-dot {
  position: absolute;
  top: 6px;
  right: 10px;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #059669;
  box-shadow: 0 0 0 2px color-mix(in srgb, #059669 25%, transparent);
  pointer-events: none;
}
.tools { display: flex; gap: 8px; flex-wrap: wrap; align-items: center; }
.cal-legend { display: flex; gap: 12px; flex-wrap: wrap; margin: 0 0 8px; font-size: 12px; color: var(--portal-muted, #64748b); }
.cal-legend .leg::before {
  content: '';
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  margin-right: 4px;
  vertical-align: middle;
}
.cal-legend .tone-ok::before { background: #059669; }
.cal-legend .tone-warn::before { background: #d97706; }
.cal-legend .tone-full::before { background: #94a3b8; }
.day-fill { display: flex; flex-wrap: wrap; gap: 6px; margin: 0 0 12px; }
.day-chip {
  min-width: 36px;
  padding: 4px 8px;
  border-radius: 6px;
  border: 1px solid var(--portal-line, #e2e8f0);
  background: #fff;
  cursor: pointer;
  font-size: 12px;
}
.day-chip.tone-ok { border-color: #059669; color: #047857; }
.day-chip.tone-warn { border-color: #d97706; color: #b45309; }
.day-chip.tone-full { opacity: 0.45; cursor: not-allowed; }
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
.slot.tone-ok { border-color: color-mix(in srgb, #059669 45%, var(--portal-line, #e2e8f0)); }
.slot.tone-warn { border-color: color-mix(in srgb, #d97706 55%, var(--portal-line, #e2e8f0)); }
.slot.tone-full { border-color: #cbd5e1; }
.slot:disabled { opacity: 0.45; cursor: not-allowed; }
.t { font-weight: 600; font-size: 14px; }
.e, .r { margin-top: 4px; font-size: 12px; color: var(--portal-muted, #64748b); }
.empty { text-align: center; color: var(--portal-muted, #94a3b8); padding: 40px 0; }
.tip { margin: 0 0 8px; font-size: 13px; }
.tip.price { color: var(--el-color-primary); font-weight: 600; }
.kind-bar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  margin: 0 0 10px;
  font-size: 13px;
}
.kind-lab { color: var(--portal-muted, #64748b); }
.period-block { margin-bottom: 16px; }
.period-hd {
  margin: 0 0 8px;
  font-size: 15px;
  font-weight: 600;
  display: flex;
  align-items: baseline;
  gap: 10px;
}
.period-remain { font-size: 12px; font-weight: 400; color: var(--portal-muted, #64748b); }
</style>
