<template>
  <div
    :data-reserve-surface="reserveSurface || 'cards'"
    :class="{
      'reserve-slotstrip': reserveSurface === 'slotstrip',
      'reserve-roomstate': reserveSurface === 'roomstate',
      'reserve-vehiclecard': reserveSurface === 'vehiclecard',
    }"
  >
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
            <div class="r">{{ slotRemainText(s) }}</div>
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
        <div class="r">{{ slotRemainText(s) }}</div>
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

<script setup src="./SlotBook.setup.js"></script>

<style scoped src="./SlotBook.css"></style>
