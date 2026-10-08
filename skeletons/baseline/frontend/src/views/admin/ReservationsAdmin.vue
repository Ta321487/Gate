<template>
  <div>
    <div class="toolbar">
      <el-select v-model="status" clearable placeholder="全部状态" style="width:140px" @change="load">
        <el-option v-for="(lab, key) in states" :key="key" :label="lab" :value="key" />
      </el-select>
      <el-button type="primary" @click="load">查询</el-button>
      <el-button :disabled="!list.length" @click="exportCsv">导出 CSV</el-button>
      <el-button
        v-if="meetingOpsOn"
        :disabled="!list.length"
        :title="meetingCheckinExportHint"
        @click="exportCheckinCsv"
      >{{ meetingCheckinExportLabel }}</el-button>
      <el-button
        v-if="instrumentOpsOn"
        :disabled="!list.length"
        :title="instrumentFeeExportHint"
        @click="exportInstrumentFeeCsv"
      >{{ instrumentFeeExportLabel }}</el-button>
      <el-button @click="openGenerate">生成时段</el-button>
    </div>
    <div class="table-scroll">
    <el-table :data="list" stripe>
      <el-table-column prop="id" label="编号" width="70" />
      <el-table-column prop="itemTitle" :label="archiveLabel" min-width="140" show-overflow-tooltip />
      <el-table-column :label="userLabel" width="110">
        <template #default="{ row }">{{ personLabel(row) }}</template>
      </el-table-column>
      <el-table-column prop="startAt" label="开始" width="170" />
      <el-table-column prop="endAt" label="结束" width="170" />
      <el-table-column prop="status" label="状态" width="100">
        <template #default="{ row }">{{ states[row.status] || row.status }}</template>
      </el-table-column>
      <el-table-column prop="createdAt" :label="`${resvNoun}时间`" width="170" />
      <el-table-column prop="entryAt" :label="parkingEntryLabel" width="170">
        <template #default="{ row }">{{ row.entryAt || '—' }}</template>
      </el-table-column>
      <el-table-column v-if="parkingOpsOn" prop="exitAt" :label="parkingExitLabel" width="170">
        <template #default="{ row }">{{ row.exitAt || '—' }}</template>
      </el-table-column>
      <el-table-column v-if="parkingOpsOn" :label="parkingDurationFeeLabel" width="110">
        <template #default="{ row }">{{ row.durationFeeYuan != null && row.durationFeeYuan !== '' ? row.durationFeeYuan : '—' }}</template>
      </el-table-column>
      <el-table-column v-if="parkingOpsOn || instrumentOpsOn" :label="overtimeFeeColumnLabel" width="110">
        <template #default="{ row }">{{ Number(row.overtimeFeeYuan) > 0 ? row.overtimeFeeYuan : '—' }}</template>
      </el-table-column>
      <el-table-column v-if="instrumentOpsOn" :label="instrumentConsumableLabel" min-width="140" show-overflow-tooltip>
        <template #default="{ row }">{{ row.consumableNote || '—' }}</template>
      </el-table-column>
      <el-table-column v-if="hotelOpsOn" label="离店日" width="120">
        <template #default="{ row }">{{ row.stayTo || '—' }}</template>
      </el-table-column>
      <el-table-column v-if="hotelOpsOn" :label="hotelLateCheckoutLabel" width="120">
        <template #default="{ row }">{{ Number(row.lateCheckoutFeeYuan) > 0 ? row.lateCheckoutFeeYuan : '—' }}</template>
      </el-table-column>
      <el-table-column v-if="carrentOpsOn" :label="carrentMileageOverLabel" width="120">
        <template #default="{ row }">{{ Number(row.mileageOverFeeYuan) > 0 ? row.mileageOverFeeYuan : '—' }}</template>
      </el-table-column>
      <el-table-column v-if="carrentOpsOn" :label="carrentEtcFeeLabel" width="110">
        <template #default="{ row }">{{ Number(row.etcFeeYuan) > 0 ? row.etcFeeYuan : '—' }}</template>
      </el-table-column>
      <el-table-column v-if="allowRating" label="评分" width="90">
        <template #default="{ row }">{{ row.rating != null && row.rating !== '' ? `${row.rating} 星` : '—' }}</template>
      </el-table-column>
      <el-table-column v-if="allowRating" label="短评" min-width="140" show-overflow-tooltip>
        <template #default="{ row }">{{ row.ratingRemark || '—' }}</template>
      </el-table-column>
      <el-table-column :label="lateFlagLabel" width="80">
        <template #default="{ row }">{{ row.lateFlag ? '是' : (row.checkedInAt ? '否' : '—') }}</template>
      </el-table-column>
      <el-table-column label="详情" min-width="160" show-overflow-tooltip>
        <template #default="{ row }">{{ resvDetail(row) }}</template>
      </el-table-column>
      <el-table-column label="操作" min-width="260" fixed="right">
        <template #default="{ row }">
          <div class="table-ops">
          <el-button
            v-if="requireConfirm && (row.status === 'pending' || row.status === 'waitlisted')"
            link
            type="primary"
            @click="confirmRow(row)"
          >确认</el-button>
          <el-button
            v-if="(row.status === 'pending' || row.status === 'confirmed') && !row.checkedInAt"
            link
            type="success"
            @click="checkInRow(row)"
          >{{ checkInLabel }}</el-button>
          <el-button
            v-if="row.status === 'confirmed'"
            link
            type="success"
            @click="completeRow(row)"
          >{{ completeVerb }}</el-button>
          <el-button
            v-if="parkingOpsOn && (row.status === 'completed' || row.status === 'confirmed') && !row.exitAt"
            link
            type="primary"
            @click="markExit(row)"
          >登记离场</el-button>
          <el-button
            v-if="parkingOpsOn && (row.status === 'completed' || row.entryAt)"
            link
            type="warning"
            @click="registerOvertime(row)"
          >{{ parkingOvertimeLabel }}</el-button>
          <el-button
            v-if="instrumentOpsOn && (row.status === 'confirmed' || row.status === 'completed')"
            link
            type="warning"
            @click="registerInstrumentOvertime(row)"
          >{{ instrumentOvertimeLabel }}</el-button>
          <el-button
            v-if="instrumentOpsOn && (row.status === 'confirmed' || row.status === 'completed')"
            link
            @click="patchInstrumentConsumable(row)"
          >{{ instrumentConsumableLabel }}</el-button>
          <el-button
            v-if="meetingOpsOn && row.status === 'confirmed'"
            link
            type="primary"
            @click="setDoorCode(row)"
          >{{ meetingDoorCodeLabel }}</el-button>
          <el-button
            v-if="meetingOpsOn && row.status === 'confirmed' && row.meetingStage !== 'in_progress'"
            link
            :title="meetingStageHint"
            @click="setStage(row, 'in_progress')"
          >{{ meetingStageInProgress }}</el-button>
          <el-button
            v-if="meetingOpsOn && row.status === 'confirmed' && row.meetingStage === 'in_progress'"
            link
            @click="setStage(row, 'ended')"
          >{{ meetingStageEnded }}</el-button>
          <el-button
            v-if="salonOpsOn && (row.status === 'confirmed' || row.status === 'completed' || Number(row.rescheduleCount) > 0)"
            link
            type="warning"
            @click="registerRescheduleFee(row)"
          >{{ salonRescheduleFeeLabel }}</el-button>
          <el-button
            v-if="hotelOpsOn && (row.status === 'pending' || row.status === 'confirmed')"
            link
            type="primary"
            @click="extendStay(row)"
          >{{ hotelExtendStayLabel }}</el-button>
          <el-button
            v-if="hotelOpsOn && (row.status === 'confirmed' || row.status === 'completed')"
            link
            type="warning"
            @click="registerLateCheckout(row)"
          >{{ hotelLateCheckoutLabel }}</el-button>
          <el-button
            v-if="hotelOpsOn && (row.status === 'confirmed' || row.status === 'completed')"
            link
            @click="patchHotelChecklist(row)"
          >{{ hotelCheckoutChecklistLabel }}</el-button>
          <el-button
            v-if="carrentOpsOn && (row.status === 'confirmed' || row.status === 'completed')"
            link
            type="warning"
            @click="registerMileageOver(row)"
          >{{ carrentMileageOverLabel }}</el-button>
          <el-button
            v-if="carrentOpsOn && (row.status === 'confirmed' || row.status === 'completed')"
            link
            type="warning"
            @click="registerEtcFee(row)"
          >{{ carrentEtcFeeLabel }}</el-button>
          <el-button
            v-if="carrentOpsOn && (row.status === 'confirmed' || row.status === 'completed')"
            link
            @click="patchCarrentHold(row)"
          >{{ carrentViolationHoldLabel }}</el-button>
          <el-button
            v-if="carrentOpsOn && (row.status === 'confirmed' || row.status === 'completed')"
            link
            @click="patchCarrentAttach(row)"
          >{{ carrentViolationAttachLabel }}</el-button>
          <el-button
            v-if="row.status === 'pending' || row.status === 'confirmed'"
            link
            type="warning"
            @click="markNoShow(row)"
          >记爽约</el-button>
          <el-button
            v-if="row.status === 'pending' || row.status === 'confirmed'"
            link
            type="danger"
            @click="cancel(row)"
          >{{ row.status === 'pending' && requireConfirm ? '驳回' : '取消' }}</el-button>
          <span v-if="!hasResvOps(row)" class="ops-empty">—</span>
          </div>
        </template>
      </el-table-column>
    </el-table>
    </div>
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

    <el-dialog v-model="genVisible" :title="`为${archiveLabel}生成当日时段`" width="520px">
      <el-form label-width="96px">
        <el-form-item :label="archiveLabel" required>
          <el-select
            v-model="gen.itemId"
            filterable
            clearable
            :placeholder="`选择${archiveLabel}`"
            style="width:100%"
            @change="loadSlotPreview"
          >
            <el-option
              v-for="it in archiveOptions"
              :key="it.id"
              :label="archiveOptionLabel(it)"
              :value="it.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="日期" required>
          <el-date-picker
            v-model="gen.day"
            type="date"
            value-format="YYYY-MM-DD"
            style="width:100%"
            @change="loadSlotPreview"
          />
        </el-form-item>
        <el-form-item label="起止小时">
          <el-input-number v-model="gen.startHour" :min="0" :max="23" />
          <span style="margin:0 8px">~</span>
          <el-input-number v-model="gen.endHour" :min="1" :max="24" />
        </el-form-item>
        <el-form-item label="每段分钟">
          <el-input-number v-model="gen.slotMinutes" :min="15" :step="15" />
        </el-form-item>
        <el-form-item label="容量">
          <el-input-number v-model="gen.capacity" :min="1" />
        </el-form-item>
        <el-form-item v-if="meetingOpsOn" :label="meetingWeeklyRepeatLabel">
          <el-input-number v-model="gen.weeks" :min="1" :max="12" />
          <p class="hint" style="margin-top:6px">{{ meetingWeeklyRepeatHint }}</p>
        </el-form-item>
      </el-form>
      <p class="hint">
        生成的是可预约号源，不会出现在下方「{{ resvNoun }}记录」表中；
        {{ userLabel }}在「选{{ archiveLabel }}」页可见。
      </p>
      <div v-if="genPreview.length" class="preview">
        <div class="preview-hd">当日号源（{{ genPreview.length }}）</div>
        <ul>
          <li v-for="s in genPreview" :key="s.id">
            {{ s.startAt }} ~ {{ s.endAt }}
            <span class="muted">余 {{ Math.max(0, (s.capacity || 0) - (s.booked || 0)) }}/{{ s.capacity || 0 }}</span>
          </li>
        </ul>
      </div>
      <template #footer>
        <el-button @click="genVisible = false">关闭</el-button>
        <el-button type="primary" :loading="genLoading" @click="generate">生成</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import http from '../../api/http'
import { archiveCopy, getSchema, personLabel, reservationCopy, roleLabel } from '../../utils/domainSchema.js'
import { todayStr } from '../../utils/dates.js'
import { downloadCsv } from '../../utils/csvDownload.js'

const resv = reservationCopy()
const resvNoun = computed(() => resv.label || '预约')
const requireConfirm = computed(() => !!resv.requireConfirm)
const completeVerb = computed(() => resv.completeVerb || '办结')
const archiveLabel = computed(() => archiveCopy().label || '资源')
const userLabel = computed(() => roleLabel('user', '用户'))
const patientLabel = computed(() => resv.patientNameLabel || resv.remarkLabel || '就诊人')
const guestLabel = computed(() => resv.guestNameLabel || '入住人')
const stylistShort = computed(() => {
  const raw = (resv.stylistLabel || '偏好技师').replace(/^偏好/, '')
  return raw || '技师'
})
const states = computed(() => getSchema()?.entities?.reservation?.states || {})
const allowRating = computed(() => !!getSchema()?.entities?.reservation?.allowRating)
const labels = computed(() => getSchema()?.labels || {})
const checkInLabel = computed(() => labels.value.checkInLabel || '签到')
const lateFlagLabel = computed(() => labels.value.lateFlagLabel || '迟到')
const waitlistPromoteTitle = computed(() => labels.value.waitlistPromoteTitle || '候补已转正')
void waitlistPromoteTitle
const queueNoLabel = computed(() => labels.value.queueNoLabel || '候诊号')
const hospitalWaitlistHint = computed(() => labels.value.hospitalWaitlistHint || '')
void hospitalWaitlistHint
const hospitalCancelCutoffHint = computed(() => labels.value.hospitalCancelCutoffHint || '')
void hospitalCancelCutoffHint
const hospitalIdLimitHint = computed(() => labels.value.hospitalIdLimitHint || '')
void hospitalIdLimitHint
const revisitPriorityHint = computed(() => labels.value.revisitPriorityHint || '')
void revisitPriorityHint
const checkinCodeLabel = computed(() => labels.value.checkinCodeLabel || '报到口令')
void checkinCodeLabel
const parkingOpsOn = computed(
  () => !!(getSchema()?.parkingPass || getSchema()?.reserveThicken?.parkingDurationFee || getSchema()?.parkingHourlyYuan),
)
const parkingEntryLabel = computed(() => labels.value.parkingEntryLabel || '入场时间')
const parkingExitLabel = computed(() => labels.value.parkingExitLabel || '离场时间')
const parkingDurationFeeLabel = computed(() => labels.value.parkingDurationFeeLabel || '停车时长费')
const parkingOvertimeLabel = computed(() => labels.value.parkingOvertimeLabel || '超时加收')
const parkingOvertimeHint = computed(() => labels.value.parkingOvertimeHint || '')
void parkingOvertimeHint
const parkingShareSlotHint = computed(() => labels.value.parkingShareSlotHint || '')
void parkingShareSlotHint
const parkingCarpassHint = computed(() => labels.value.parkingCarpassHint || '')
void parkingCarpassHint
const meetingOpsOn = computed(
  () => !!(getSchema()?.reserveThicken?.meetingRequireConfirm
    || getSchema()?.meetingMinutesRequired
    || getSchema()?.traits?.slotMeeting
    || hasTraitMeeting()),
)
function hasTraitMeeting() {
  try {
    const t = getSchema()?.traits || {}
    return !!t.slotMeeting
  } catch {
    return false
  }
}
const meetingDoorCodeLabel = computed(() => labels.value.meetingDoorCodeLabel || '门禁密码')
const meetingDoorCodeHint = computed(() => labels.value.meetingDoorCodeHint || '')
  const meetingStageInProgress = computed(() => labels.value.meetingStageInProgress || '召开中')
  const meetingStageHint = computed(() => labels.value.meetingStageHint || '')
  const meetingStageLabel = computed(() => labels.value.meetingStageLabel || '会议状态')
  const meetingStageEnded = computed(() => labels.value.meetingStageEnded || '已结束')
  const meetingCheckinExportLabel = computed(() => labels.value.meetingCheckinExportLabel || '导出签到表')
  const meetingCheckinExportHint = computed(() => labels.value.meetingCheckinExportHint || '')
  const meetingWeeklyRepeatLabel = computed(() => labels.value.meetingWeeklyRepeatLabel || '按周重复生成')
  const meetingWeeklyRepeatHint = computed(() => labels.value.meetingWeeklyRepeatHint || '')
  const meetingMinutesLabel = computed(() => labels.value.meetingMinutesLabel || '会议纪要附件')
  void meetingMinutesLabel
  const meetingMinutesHint = computed(() => labels.value.meetingMinutesHint || '')
  void meetingMinutesHint
  const meetingConflictHint = computed(() => labels.value.meetingConflictHint || '')
  void meetingConflictHint
  const meetingRequireConfirmHint = computed(() => labels.value.meetingRequireConfirmHint || '')
  void meetingRequireConfirmHint
  const meetingBlacklistHint = computed(() => labels.value.meetingBlacklistHint || '')
  void meetingBlacklistHint
  const meetingVideoLabel = computed(() => labels.value.meetingVideoLabel || '视频会议链接')
  void meetingVideoLabel
  const meetingRecordingLabel = computed(() => labels.value.meetingRecordingLabel || '录屏链接')
  void meetingRecordingLabel
  const meetingCheckinCodeLabel = computed(() => labels.value.meetingCheckinCodeLabel || '签到码')
  const meetingServiceHint = computed(() => labels.value.meetingServiceHint || '')
  void meetingServiceHint
  const meetingMinDurationHint = computed(() => labels.value.meetingMinDurationHint || '')
  void meetingMinDurationHint
const salonOpsOn = computed(() => !!(getSchema()?.reserveThicken?.salonRescheduleFee
  || getSchema()?.reserveThicken?.salonCheckinCode))
const hotelOpsOn = computed(() => !!(getSchema()?.reserveThicken?.hotelExtendStay
  || getSchema()?.reserveThicken?.hotelLateCheckout
  || getSchema()?.hotelNoticeRequired))
const hotelExtendStayLabel = computed(() => labels.value.hotelExtendStayLabel || '续住')
const hotelExtendStayHint = computed(() => labels.value.hotelExtendStayHint || '')
const hotelLateCheckoutLabel = computed(() => labels.value.hotelLateCheckoutLabel || '延迟退房加收')
const hotelLateCheckoutHint = computed(() => labels.value.hotelLateCheckoutHint || '')
const hotelCheckoutChecklistLabel = computed(() => labels.value.hotelCheckoutChecklistLabel || '查房清单')
const hotelCheckoutChecklistHint = computed(() => labels.value.hotelCheckoutChecklistHint || '')
const carrentOpsOn = computed(() => !!(getSchema()?.reserveThicken?.carrentEtcFee
  || getSchema()?.reserveThicken?.carrentMileageOver
  || getSchema()?.reserveThicken?.carrentViolationHold))
const carrentMileageOverLabel = computed(() => labels.value.carrentMileageOverLabel || '里程超支加收')
const carrentMileageOverHint = computed(() => labels.value.carrentMileageOverHint || '')
const carrentEtcFeeLabel = computed(() => labels.value.carrentEtcFeeLabel || 'ETC 通行费')
const carrentEtcFeeHint = computed(() => labels.value.carrentEtcFeeHint || '')
const carrentViolationHoldLabel = computed(() => labels.value.carrentViolationHoldLabel || '违章预留押')
const carrentViolationHoldHint = computed(() => labels.value.carrentViolationHoldHint || '')
const carrentViolationAttachLabel = computed(() => labels.value.carrentViolationAttachLabel || '违章附件')
const carrentViolationAttachHint = computed(() => labels.value.carrentViolationAttachHint || '')
const instrumentOpsOn = computed(() => !!(getSchema()?.reserveThicken?.instrumentOvertime
  || getSchema()?.reserveThicken?.instrumentFeeExport
  || getSchema()?.reserveThicken?.instrumentConsumable
  || getSchema()?.traits?.slotInstrument))
const instrumentOvertimeLabel = computed(() => labels.value.instrumentOvertimeLabel || '超时机时费')
const instrumentOvertimeHint = computed(() => labels.value.instrumentOvertimeHint || '')
const instrumentConsumableLabel = computed(() => labels.value.instrumentConsumableLabel || '耗材领用')
const instrumentConsumableHint = computed(() => labels.value.instrumentConsumableHint || '')
const instrumentFeeExportLabel = computed(() => labels.value.instrumentFeeExportLabel || '导出机时费')
const instrumentFeeExportHint = computed(() => labels.value.instrumentFeeExportHint || '')
const instrumentMentorConfirmHint = computed(() => labels.value.instrumentMentorConfirmHint || '')
void instrumentMentorConfirmHint
const instrumentTrainingAckLabel = computed(() => labels.value.instrumentTrainingAckLabel || '已完成上机培训')
void instrumentTrainingAckLabel
const instrumentTrainingAckHint = computed(() => labels.value.instrumentTrainingAckHint || '')
void instrumentTrainingAckHint
const instrumentConflictHint = computed(() => labels.value.instrumentConflictHint || '')
void instrumentConflictHint
const instrumentPurposeLabel = computed(() => labels.value.instrumentPurposeLabel || '实验目的')
void instrumentPurposeLabel
const instrumentPurposeHint = computed(() => labels.value.instrumentPurposeHint || '')
void instrumentPurposeHint
const meetingEquipBorrowLabel = computed(() => labels.value.meetingEquipBorrowLabel || '借用录制设备')
const meetingEquipBorrowHint = computed(() => labels.value.meetingEquipBorrowHint || '')
void meetingEquipBorrowHint
const hospitalRosterHint = computed(() => labels.value.hospitalRosterHint || '')
void hospitalRosterHint
const hospitalRosterLabel = computed(() => labels.value.hospitalRosterLabel || '')
void hospitalRosterLabel
const salonLeaveBlockHint = computed(() => labels.value.salonLeaveBlockHint || '')
void salonLeaveBlockHint
const salonLessonRemainLabel = computed(() => labels.value.salonLessonRemainLabel || '')
void salonLessonRemainLabel
const salonLessonRemainHint = computed(() => labels.value.salonLessonRemainHint || '')
void salonLessonRemainHint
const salonLessonExpireTitle = computed(() => labels.value.salonLessonExpireTitle || '')
void salonLessonExpireTitle
const salonLessonExpireBody = computed(() => labels.value.salonLessonExpireBody || '')
void salonLessonExpireBody
const salonWalletLabel = computed(() => labels.value.salonWalletLabel || '')
void salonWalletLabel
const salonGalleryLabel = computed(() => labels.value.salonGalleryLabel || '')
void salonGalleryLabel
const overtimeFeeColumnLabel = computed(() => (
  instrumentOpsOn.value ? instrumentOvertimeLabel.value : parkingOvertimeLabel.value
))
const salonRescheduleFeeLabel = computed(() => labels.value.salonRescheduleFeeLabel || '改约手续费（元）')
const salonRescheduleFeeHint = computed(() => labels.value.salonRescheduleFeeHint || '')
const salonServiceMinutesHint = computed(() => labels.value.salonServiceMinutesHint || '')
void salonServiceMinutesHint
const salonServiceMinutesLabel = computed(() => labels.value.salonServiceMinutesLabel || '')
void salonServiceMinutesLabel
const salonTabooLabel = computed(() => labels.value.salonTabooLabel || '')
void salonTabooLabel
const salonTabooHint = computed(() => labels.value.salonTabooHint || '')
void salonTabooHint
const salonWalletHint = computed(() => labels.value.salonWalletHint || '')
void salonWalletHint
const salonLateGraceHint = computed(() => labels.value.salonLateGraceHint || '')
void salonLateGraceHint
const salonCheckinScanLabel = computed(() => labels.value.salonCheckinScanLabel || '')
void salonCheckinScanLabel
const salonCheckinScanHint = computed(() => labels.value.salonCheckinScanHint || '')
void salonCheckinScanHint
const salonVisitCountLabel = computed(() => labels.value.salonVisitCountLabel || '')
void salonVisitCountLabel
const salonVisitCountHint = computed(() => labels.value.salonVisitCountHint || '')
void salonVisitCountHint
const salonGalleryHint = computed(() => labels.value.salonGalleryHint || '')
void salonGalleryHint
const checkinCodeAdminHint = computed(() => labels.value.checkinCodeAdminHint || '')
void checkinCodeAdminHint
const checkinCodeHint = computed(() => labels.value.checkinCodeHint || '')
void checkinCodeHint
function hasResvOps(row) {
  if (!row) return false
  if (requireConfirm.value && (row.status === 'pending' || row.status === 'waitlisted')) return true
  if (row.status === 'confirmed') return true
  if (!requireConfirm.value && row.status === 'pending') return true
  return false
}
const list = ref([])
const total = ref(0)
const page = ref(1)
const size = ref(10)
const status = ref(null)
const genVisible = ref(false)
const genLoading = ref(false)
const genPreview = ref([])
const archiveOptions = ref([])
const gen = reactive({
  itemId: null,
  day: todayStr(),
  startHour: 9,
  endHour: 17,
  slotMinutes: 60,
  capacity: 1,
  weeks: 1,
})

function archiveOptionLabel(it) {
  const title = (it.title || it.name || `${archiveLabel.value}#${it.id}`).toString().trim()
  const cat = (it.categoryName || '').toString().trim()
  return cat ? `${title} · ${cat}` : title
}

function resvDetail(row) {
  const parts = []
  if (row.plateNo) parts.push(`车牌 ${row.plateNo}`)
  if (row.patientName) parts.push(`${patientLabel.value} ${row.patientName}${row.visitType ? '/' + row.visitType : ''}`)
  if (row.subject) parts.push(`主题 ${row.subject}${row.partySize ? ' ·' + row.partySize + '人' : ''}`)
  if (row.guestName) parts.push(`${guestLabel.value} ${row.guestName}`)
  if (row.preferredStylist) parts.push(`${stylistShort.value} ${row.preferredStylist}`)
  if (row.queueNo) parts.push(`${queueNoLabel.value} ${row.queueNo}`)
  if (row.doorCode) parts.push(`${meetingDoorCodeLabel.value} ${row.doorCode}`)
  if (row.checkinToken) parts.push(`${meetingCheckinCodeLabel.value} ${row.checkinToken}`)
  if (row.meetingStage === 'in_progress') parts.push(meetingStageInProgress.value)
  if (row.minutesAttach) parts.push('纪要已传')
  if (row.equipBorrow) parts.push(meetingEquipBorrowLabel.value)
  if (Number(row.rescheduleFeeYuan) > 0) {
    parts.push(`${salonRescheduleFeeLabel.value} ${row.rescheduleFeeYuan}`)
  }
  if (!parts.length && row.remark) parts.push(row.remark)
  return parts.join(' · ') || '—'
}

async function load() {
  const res = await http.get('/api/slots/reservations', {
    params: { page: page.value, size: size.value, status: status.value || undefined },
  })
  list.value = res.data?.list || []
  total.value = res.data?.total || 0
}

async function loadArchiveOptions() {
  const res = await http.get('/api/archive', { params: { page: 1, size: 200 } })
  const rows = res.data?.list || []
  archiveOptions.value = rows
  const ids = new Set(rows.map((r) => r.id))
  if (gen.itemId != null && !ids.has(gen.itemId)) gen.itemId = null
  if (gen.itemId == null && rows.length) gen.itemId = rows[0].id
}

async function openGenerate() {
  genPreview.value = []
  genVisible.value = true
  await loadArchiveOptions()
  await loadSlotPreview()
}

async function loadSlotPreview() {
  if (!gen.itemId || !gen.day) {
    genPreview.value = []
    return
  }
  const res = await http.get('/api/slots', { params: { itemId: gen.itemId, day: gen.day } })
  const rows = Array.isArray(res.data) ? res.data : (res.data?.list || [])
  genPreview.value = rows
}

async function cancel(row) {
  const reject = requireConfirm.value && row.status === 'pending'
  await ElMessageBox.confirm(
    reject ? `驳回${resvNoun.value} #${row.id}？号源将释放。` : `取消${resvNoun.value} #${row.id}？`,
    reject ? '驳回' : '取消',
  )
  await http.post(`/api/slots/reservations/${row.id}/cancel`)
  ElMessage.success(reject ? '已驳回' : '已取消')
  load()
}

async function confirmRow(row) {
  await ElMessageBox.confirm(`确认${resvNoun.value} #${row.id}？`, '确认')
  await http.post(`/api/slots/reservations/${row.id}/confirm`)
  ElMessage.success('已确认')
  load()
}

async function completeRow(row) {
  await ElMessageBox.confirm(
    `对「${row.itemTitle || resvNoun.value}」执行「${completeVerb.value}」？`,
    completeVerb.value,
  )
  await http.post(`/api/slots/reservations/${row.id}/complete`)
  ElMessage.success(`已${completeVerb.value}`)
  load()
}

async function markExit(row) {
  await ElMessageBox.confirm(
    `登记「${row.itemTitle || row.plateNo || resvNoun.value}」离场并估算时长费？`,
    parkingExitLabel.value,
  )
  await http.post(`/api/slots/reservations/${row.id}/exit`)
  ElMessage.success('已登记离场')
  load()
}

async function registerOvertime(row) {
  const { value } = await ElMessageBox.prompt(
    parkingOvertimeHint.value || '请输入超时加收金额（元），留空用默认',
    parkingOvertimeLabel.value,
    {
      inputPlaceholder: '金额（元）',
      inputValue: '',
      confirmButtonText: '登记',
      cancelButtonText: '取消',
    },
  )
  const body = {}
  if (value != null && String(value).trim() !== '') {
    body.yuan = String(value).trim()
  }
  await http.post(`/api/slots/reservations/${row.id}/overtime-fee`, body)
  ElMessage.success('已登记超时加收')
  load()
}

async function registerInstrumentOvertime(row) {
  const { value } = await ElMessageBox.prompt(
    instrumentOvertimeHint.value || '请输入超时机时费（元），留空用默认',
    instrumentOvertimeLabel.value,
    {
      inputPlaceholder: '金额（元）',
      inputValue: '',
      confirmButtonText: '登记',
      cancelButtonText: '取消',
    },
  )
  const body = {}
  if (value != null && String(value).trim() !== '') {
    body.yuan = String(value).trim()
  }
  await http.post(`/api/slots/reservations/${row.id}/overtime-fee`, body)
  ElMessage.success('已登记超时机时费')
  load()
}

async function patchInstrumentConsumable(row) {
  const { value } = await ElMessageBox.prompt(
    instrumentConsumableHint.value || '请填写耗材领用说明',
    instrumentConsumableLabel.value,
    {
      inputValue: row.consumableNote || '',
      confirmButtonText: '保存',
      cancelButtonText: '取消',
    },
  )
  await http.post(`/api/slots/reservations/${row.id}/instrument-patch`, {
    consumableNote: value || '',
  })
  ElMessage.success('已保存耗材领用')
  load()
}

async function registerRescheduleFee(row) {
  const { value } = await ElMessageBox.prompt(
    salonRescheduleFeeHint.value || '请输入改约手续费（元），留空用默认',
    salonRescheduleFeeLabel.value,
    {
      inputPlaceholder: '金额（元）',
      inputValue: row.rescheduleFeeYuan != null ? String(row.rescheduleFeeYuan) : '',
      confirmButtonText: '登记',
      cancelButtonText: '取消',
    },
  )
  const body = {}
  if (value != null && String(value).trim() !== '') {
    body.rescheduleFeeYuan = String(value).trim()
  }
  await http.post(`/api/slots/reservations/${row.id}/reschedule-fee`, body)
  ElMessage.success('已登记改约手续费')
  load()
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

async function registerLateCheckout(row) {
  const { value } = await ElMessageBox.prompt(
    hotelLateCheckoutHint.value || '请输入延迟退房加收金额（元），留空用默认',
    hotelLateCheckoutLabel.value,
    {
      inputPlaceholder: '金额（元）',
      inputValue: '',
      confirmButtonText: '登记',
      cancelButtonText: '取消',
    },
  )
  const body = {}
  if (value != null && String(value).trim() !== '') {
    body.yuan = String(value).trim()
  }
  await http.post(`/api/slots/reservations/${row.id}/late-checkout-fee`, body)
  ElMessage.success('已登记延迟退房加收')
  load()
}

async function patchHotelChecklist(row) {
  const { value } = await ElMessageBox.prompt(
    hotelCheckoutChecklistHint.value || '请填写查房清单',
    hotelCheckoutChecklistLabel.value,
    {
      inputPlaceholder: '如：迷你吧、毛巾、电器',
      inputValue: row.checkoutChecklist || '',
      confirmButtonText: '保存',
      cancelButtonText: '取消',
    },
  )
  await http.post(`/api/slots/reservations/${row.id}/hotel-patch`, {
    checkoutChecklist: String(value || '').trim(),
  })
  ElMessage.success('已保存查房清单')
  load()
}

async function registerMileageOver(row) {
  const { value } = await ElMessageBox.prompt(
    carrentMileageOverHint.value || '请输入里程超支加收金额（元），留空用默认',
    carrentMileageOverLabel.value,
    {
      inputPlaceholder: '金额（元）',
      inputValue: '',
      confirmButtonText: '登记',
      cancelButtonText: '取消',
    },
  )
  const body = {}
  if (value != null && String(value).trim() !== '') {
    body.yuan = String(value).trim()
  }
  await http.post(`/api/slots/reservations/${row.id}/mileage-over-fee`, body)
  ElMessage.success('已登记里程超支加收')
  load()
}

async function registerEtcFee(row) {
  const { value } = await ElMessageBox.prompt(
    carrentEtcFeeHint.value || '请输入 ETC 通行费金额（元）',
    carrentEtcFeeLabel.value,
    {
      inputPlaceholder: '金额（元）',
      inputValue: '',
      confirmButtonText: '登记',
      cancelButtonText: '取消',
    },
  )
  const yuan = String(value || '').trim()
  if (!yuan) {
    ElMessage.warning('请填写通行费金额')
    return
  }
  await http.post(`/api/slots/reservations/${row.id}/etc-fee`, { yuan })
  ElMessage.success('已登记 ETC 通行费')
  load()
}

async function patchCarrentHold(row) {
  const { value } = await ElMessageBox.prompt(
    carrentViolationHoldHint.value || '请填写违章预留押金额（元）',
    carrentViolationHoldLabel.value,
    {
      inputPlaceholder: '金额（元）',
      inputValue: row.violationHoldYuan != null ? String(row.violationHoldYuan) : '',
      confirmButtonText: '保存',
      cancelButtonText: '取消',
    },
  )
  await http.post(`/api/slots/reservations/${row.id}/carrent-patch`, {
    violationHoldYuan: String(value || '').trim() || '0',
  })
  ElMessage.success('已保存违章预留押')
  load()
}

async function patchCarrentAttach(row) {
  const { value } = await ElMessageBox.prompt(
    carrentViolationAttachHint.value || '请填写违章附件链接',
    carrentViolationAttachLabel.value,
    {
      inputPlaceholder: '附件 URL',
      inputValue: row.violationAttach || '',
      confirmButtonText: '保存',
      cancelButtonText: '取消',
    },
  )
  await http.post(`/api/slots/reservations/${row.id}/carrent-patch`, {
    violationAttach: String(value || '').trim(),
  })
  ElMessage.success('已保存违章附件')
  load()
}

async function checkInRow(row) {
  await http.post(`/api/slots/reservations/${row.id}/checkin`)
  ElMessage.success('已签到')
  load()
}

async function markNoShow(row) {
  await ElMessageBox.confirm(`将「${row.itemTitle || resvNoun.value}」记为爽约？号源将释放。`, '记爽约')
  await http.post(`/api/slots/reservations/${row.id}/no-show`)
  ElMessage.success('已记爽约')
  load()
}

async function generate() {
  if (!gen.itemId || !gen.day) {
    ElMessage.warning(`请选择${archiveLabel.value}并填写日期`)
    return
  }
  genLoading.value = true
  try {
    const res = await http.post('/api/slots/generate', { ...gen })
    const n = res.data?.created ?? 0
    await loadSlotPreview()
    if (n > 0) {
      ElMessage.success(`已生成 ${n} 个号源时段（见弹窗列表；下方表格仍是已${resvNoun.value}记录）`)
    } else {
      ElMessage.warning('未新增时段（可能该日号源已存在），已刷新弹窗内当日号源列表')
    }
  } finally {
    genLoading.value = false
  }
}

async function exportCsv() {
  const res = await http.get('/api/slots/reservations', {
    params: { page: 1, size: 5000, status: status.value || undefined },
  })
  const rows = res.data?.list || []
  if (!rows.length) {
    ElMessage.warning('当前筛选无数据可导出')
    return
  }
  const headers = ['编号', archiveLabel.value, userLabel.value, '开始', '结束', '状态', `${resvNoun.value}时间`, '详情']
  const data = rows.map((row) => [
    row.id,
    row.itemTitle,
    personLabel(row, ''),
    row.startAt,
    row.endAt,
    states.value[row.status] || row.status,
    row.createdAt,
    resvDetail(row),
  ])
  downloadCsv(`reservations_${status.value || 'all'}_${Date.now()}.csv`, headers, data)
  ElMessage.success(`已导出 ${rows.length} 条（UTF-8，可用 Excel 直接打开）`)
}

async function exportCheckinCsv() {
  const res = await http.get('/api/slots/reservations', {
    params: { page: 1, size: 5000, status: status.value || 'confirmed' },
  })
  const rows = res.data?.list || []
  if (!rows.length) {
    ElMessage.warning('当前筛选无数据可导出')
    return
  }
  const headers = ['编号', '主题', userLabel.value, '开始', '结束', '签到码', '人数', '状态']
  const data = rows.map((row) => [
    row.id,
    row.subject || row.itemTitle || '',
    personLabel(row, ''),
    row.startAt,
    row.endAt,
    row.checkinToken || '',
    row.partySize || '',
    states.value[row.status] || row.status,
  ])
  downloadCsv(`meeting_checkin_${Date.now()}.csv`, headers, data)
  ElMessage.success(`已导出签到表 ${rows.length} 条`)
}

function hoursBetween(startAt, endAt) {
  try {
    const a = new Date(String(startAt || '').replace(' ', 'T'))
    const b = new Date(String(endAt || '').replace(' ', 'T'))
    if (Number.isNaN(a.getTime()) || Number.isNaN(b.getTime()) || b <= a) return ''
    return ((b - a) / 3600000).toFixed(2)
  } catch {
    return ''
  }
}

async function exportInstrumentFeeCsv() {
  const res = await http.get('/api/slots/reservations', {
    params: { page: 1, size: 5000, status: status.value || undefined },
  })
  const rows = res.data?.list || []
  if (!rows.length) {
    ElMessage.warning('当前筛选无数据可导出')
    return
  }
  const headers = [
    '编号',
    archiveLabel.value,
    userLabel.value,
    '开始',
    '结束',
    '机时（小时）',
    instrumentOvertimeLabel.value,
    instrumentConsumableLabel.value,
    instrumentPurposeLabel.value,
    '状态',
  ]
  const data = rows.map((row) => [
    row.id,
    row.itemTitle || '',
    personLabel(row, ''),
    row.startAt,
    row.endAt,
    hoursBetween(row.startAt, row.endAt),
    row.overtimeFeeYuan != null ? row.overtimeFeeYuan : '',
    row.consumableNote || '',
    row.remark || '',
    states.value[row.status] || row.status,
  ])
  downloadCsv(`instrument_fee_${Date.now()}.csv`, headers, data)
  ElMessage.success(`已导出机时费 ${rows.length} 条`)
}

async function setDoorCode(row) {
  const { value } = await ElMessageBox.prompt(
    meetingDoorCodeHint.value || '请输入门禁密码（手发）',
    meetingDoorCodeLabel.value,
    { inputValue: row.doorCode || '', confirmButtonText: '保存' },
  )
  await http.post(`/api/slots/reservations/${row.id}/meeting`, { doorCode: value || '' })
  ElMessage.success('已保存门禁密码')
  load()
}

async function setStage(row, stage) {
  await ElMessageBox.confirm(`将「${row.subject || row.itemTitle}」标为${meetingStageInProgress.value}？`, meetingStageLabel.value)
  await http.post(`/api/slots/reservations/${row.id}/meeting`, { meetingStage: stage })
  ElMessage.success('已更新会议状态')
  load()
}

onMounted(load)
</script>

<style scoped>
.toolbar { margin-bottom: 12px; display: flex; gap: 8px; flex-wrap: wrap; }
.pager { margin-top: 16px; display: flex; justify-content: flex-end; }
.ops-empty { color: var(--el-text-color-placeholder, #c0c4cc); font-size: 13px; padding: 0 4px; }
.hint { margin: 0 0 12px; color: var(--portal-muted, #64748b); font-size: 13px; line-height: 1.5; }
.preview {
  max-height: 220px; overflow: auto;
  border: var(--portal-border-width, 1px) solid var(--portal-line, #e2e8f0);
  border-radius: var(--portal-radius-sm, 8px);
  padding: 10px 12px;
  background: color-mix(in srgb, var(--portal-bg, #f8fafc) 72%, var(--portal-surface, #fff));
}
.preview-hd { font-weight: 600; margin-bottom: 6px; font-size: 13px; }
.preview ul { margin: 0; padding-left: 18px; }
.preview li { font-size: 13px; margin: 4px 0; }
.muted { color: var(--portal-muted, #94a3b8); margin-left: 8px; }
</style>
