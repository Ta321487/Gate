<template>
  <div>
    <div class="toolbar">
      <el-select v-model="status" clearable placeholder="全部状态" style="width:140px" @change="onFilter">
        <el-option v-for="(lab, key) in states" :key="key" :label="lab" :value="key" />
        <el-option v-if="allowCheckin" label="未签到（缺勤）" value="absent" />
        <el-option v-if="allowCheckin" label="已签到" value="checked_in" />
      </el-select>
      <el-checkbox
        v-if="allowRating"
        v-model="ratedOnly"
        style="margin-left:4px"
        @change="onFilter"
      >仅已评分</el-checkbox>
      <el-checkbox
        v-if="todayBoardOn"
        v-model="todayOnly"
        style="margin-left:4px"
        @change="onFilter"
      >今日处理中</el-checkbox>
      <el-button type="primary" @click="load">查询</el-button>
      <el-button :disabled="!list.length" @click="exportCsv">{{ exportBtnLabel }}</el-button>
      <el-checkbox
        v-if="stuNoMaskOn"
        v-model="maskStuNo"
        style="margin-left:4px"
      >{{ stuNoMaskHint || '学号脱敏导出' }}</el-checkbox>
    </div>
    <SchemaLabelHints :keys="recordsHintKeys" />
    <p v-if="todayBoardOn && todayBoardHint" class="board-hint">{{ todayBoardHint }}</p>
    <p v-if="allowCheckin && absentExportHint" class="board-hint">{{ absentExportHint }}</p>
    <p v-if="allowSealLedgerExport && sealLedgerExportHint" class="board-hint">{{ sealLedgerExportHint }}</p>
    <p v-if="printTicketOn && activityProofHint" class="board-hint">{{ activityProofHint }}</p>
    <p v-if="allowLottery && lotteryDrawHint" class="board-hint">{{ lotteryDrawHint }}</p>
    <p v-if="allowPostGallery && postGalleryHint" class="board-hint">{{ postGalleryHint }}</p>
    <p v-if="requireCreditWritebackAck && creditWritebackHint" class="board-hint">{{ creditWritebackHint }}</p>
    <p v-if="allowProjNodeRemind && projNodeRemindHint" class="board-hint">{{ projNodeRemindHint }}</p>
    <el-button
      v-if="allowLottery"
      type="warning"
      plain
      style="margin-bottom:12px"
      :loading="lotteryLoading"
      @click="runLotteryDraw"
    >{{ lotteryDrawLabel }}</el-button>
    <div class="table-scroll">
    <el-table :data="list" stripe>
      <el-table-column prop="id" label="编号" width="70" />
      <el-table-column prop="title" :label="ticket.label || '标题'" min-width="140" show-overflow-tooltip />
      <el-table-column v-if="showTypeCol" prop="typeName" :label="typeColLabel" width="110" show-overflow-tooltip>
        <template #default="{ row }">
          <span v-if="categoryColorOn" class="type-dot" :style="{ background: typeColor(row.typeName || row.typeId) }" />
          {{ row.typeName || '—' }}
        </template>
      </el-table-column>
      <el-table-column v-if="showLocationCol" prop="location" :label="locationColLabel" min-width="140" show-overflow-tooltip />
      <el-table-column v-if="showPriorityCols" prop="priority" label="优先级" width="90" />
      <el-table-column v-if="showPriorityCols" prop="contactPhone" label="联系电话" width="120" show-overflow-tooltip />
      <el-table-column
        v-if="allowEmergencyContact"
        prop="emergencyContact"
        :label="emergencyContactLabel"
        width="120"
        show-overflow-tooltip
      />
      <el-table-column
        v-if="allowEmergencyContact"
        prop="emergencyPhone"
        :label="emergencyPhoneLabel"
        width="120"
        show-overflow-tooltip
      />
      <el-table-column
        v-if="requireInsuranceAck"
        prop="insuranceAck"
        label="保险声明"
        width="100"
      >
        <template #default="{ row }">{{ row.insuranceAck ? '已勾选' : '—' }}</template>
      </el-table-column>
      <el-table-column
        v-if="requireCreditWritebackAck"
        prop="creditWritebackAck"
        label="学分认定提示"
        width="110"
      >
        <template #default="{ row }">{{ row.creditWritebackAck ? '已确认' : '—' }}</template>
      </el-table-column>
      <el-table-column v-if="allowPostGallery" :label="postGalleryLabel" width="100">
        <template #default="{ row }">
          <span v-if="Array.isArray(row.postGalleryImages) && row.postGalleryImages.length">
            {{ row.postGalleryImages.length }} 张
          </span>
          <span v-else class="muted">—</span>
        </template>
      </el-table-column>
      <el-table-column :label="userLabel" width="110">
        <template #default="{ row }">{{ personLabel(row) }}</template>
      </el-table-column>
      <el-table-column prop="assigneeUsername" label="处理人" width="110">
        <template #default="{ row }">{{ row.assigneeUsername || '—' }}</template>
      </el-table-column>
      <el-table-column prop="status" label="状态" width="100">
        <template #default="{ row }">{{ statusLabel(row) }}</template>
      </el-table-column>
      <el-table-column v-if="allowQty" prop="qty" label="数量" width="70" />
      <el-table-column v-if="pickLoanPeriod" prop="dueAt" :label="dueLabel" width="170" />
      <el-table-column v-if="showFine" :label="fineLabel" width="100">
        <template #default="{ row }">
          <span v-if="row.fineYuan > 0">¥{{ row.fineYuan }} · {{ row.fineStatus || '—' }}</span>
          <span v-else>—</span>
        </template>
      </el-table-column>
      <el-table-column v-if="showPickup" label="领取" width="180">
        <template #default="{ row }">
          <span v-if="row.pickupAt">
            {{ row.pickupPlace || '已领' }}
            <template v-if="row.actualQty != null"> · 实发{{ row.actualQty }}</template>
            · {{ row.pickupAt }}
          </span>
          <span v-else class="muted">待登记</span>
        </template>
      </el-table-column>
      <el-table-column v-if="showScheduleCols" prop="startAt" label="开始" width="160" />
      <el-table-column v-if="showScheduleCols" prop="endAt" label="结束" width="160" />
      <el-table-column prop="remark" :label="richRemark ? '内容/说明' : '审核说明'" min-width="160" show-overflow-tooltip>
        <template #default="{ row }">{{ remarkText(row.remark) }}</template>
      </el-table-column>
      <el-table-column v-if="showFollowCols" :label="channelLabel" width="100" show-overflow-tooltip>
        <template #default="{ row }">{{ row.contactChannel || '—' }}</template>
      </el-table-column>
      <el-table-column v-if="showFollowCols" :label="nextAtLabel" width="170">
        <template #default="{ row }">{{ row.nextFollowAt || '—' }}</template>
      </el-table-column>
      <el-table-column label="附件" width="90">
        <template #default="{ row }">
          <a v-if="row.attachUrl" :href="row.attachUrl" target="_blank" rel="noopener noreferrer">查看</a>
          <span v-else class="muted">—</span>
        </template>
      </el-table-column>
      <el-table-column prop="applyAt" label="申请时间" width="170" />
      <el-table-column prop="approveAt" label="受理时间" width="170" />
      <el-table-column v-if="allowWishOrder" :label="wishOrderLabel" width="90">
        <template #default="{ row }">
          <span v-if="row.wishOrder === 1">第一志愿</span>
          <span v-else-if="row.wishOrder === 2">第二志愿</span>
          <span v-else class="muted">—</span>
        </template>
      </el-table-column>
      <el-table-column v-if="allowVolunteerRole" :label="volunteerRoleLabel" width="110" show-overflow-tooltip>
        <template #default="{ row }">{{ row.volunteerRole || '—' }}</template>
      </el-table-column>
      <el-table-column v-if="allowCompanions" :label="companionNamesLabel" min-width="140" show-overflow-tooltip>
        <template #default="{ row }">{{ row.companionNames || '—' }}</template>
      </el-table-column>
      <el-table-column v-if="allowCertPickup" :label="certPickupLabel" min-width="140" show-overflow-tooltip>
        <template #default="{ row }">
          {{ row.pickupMethod || '—' }}
          <template v-if="row.mailAddress"> · {{ row.mailAddress }}</template>
          <template v-if="row.expressNo"> · {{ expressNoLabel }} {{ row.expressNo }}</template>
          <template v-if="allowCertUrgent && row.certUrgent"> · {{ certUrgentLabel }}</template>
        </template>
      </el-table-column>
      <el-table-column v-if="allowSealCopies" :label="sealCopiesLabel" min-width="140" show-overflow-tooltip>
        <template #default="{ row }">
          {{ row.sealCopies != null ? row.sealCopies : '—' }}
          <template v-if="row.bindNote"> · {{ row.bindNote }}</template>
          <template v-if="row.sealCopyNos"> · {{ row.sealCopyNos }}</template>
          <template v-if="row.sealWitnessAck"> · 已监印</template>
        </template>
      </el-table-column>
      <el-table-column v-if="allowExpenseInvoice" :label="invoiceCountLabel" width="120">
        <template #default="{ row }">
          <template v-if="row.invoiceCount != null">{{ row.invoiceCount }} 张</template>
          <template v-else>—</template>
          <template v-if="row.fineYuan > 0"> · {{ row.fineYuan }} 元</template>
        </template>
      </el-table-column>
      <el-table-column v-if="allowVisitorCount" :label="visitorCountLabel" width="100">
        <template #default="{ row }">{{ row.visitorCount != null ? row.visitorCount : '—' }}</template>
      </el-table-column>
      <el-table-column v-if="allowAwardCertNo" :label="awardCertNoLabel" min-width="140" show-overflow-tooltip>
        <template #default="{ row }">{{ row.awardCertNo || '—' }}</template>
      </el-table-column>
      <el-table-column v-if="allowVendorQuotes" :label="vendorQuotesLabel" min-width="160" show-overflow-tooltip>
        <template #default="{ row }">{{ row.vendorQuotes || '—' }}</template>
      </el-table-column>
      <el-table-column v-if="allowFleetMileage" :label="mileageLabel" min-width="120" show-overflow-tooltip>
        <template #default="{ row }">
          {{ row.mileageKm != null ? row.mileageKm : '—' }}
          <template v-if="row.fuelNote"> · {{ row.fuelNote }}</template>
        </template>
      </el-table-column>
      <el-table-column v-if="allowFleetCrew" :label="driverNameLabel" min-width="100" show-overflow-tooltip>
        <template #default="{ row }">{{ row.driverName || '—' }}</template>
      </el-table-column>
      <el-table-column v-if="allowFleetCrew" :label="passengerNamesLabel" min-width="120" show-overflow-tooltip>
        <template #default="{ row }">{{ row.passengerNames || '—' }}</template>
      </el-table-column>
      <el-table-column v-if="allowCompHours" :label="compHoursLabel" width="120">
        <template #default="{ row }">{{ row.compHours != null ? row.compHours : '—' }}</template>
      </el-table-column>
      <el-table-column v-if="allowReturnFuel" :label="returnFuelLabel" width="110">
        <template #default="{ row }">{{ row.returnFuel != null ? row.returnFuel : '—' }}</template>
      </el-table-column>
      <el-table-column v-if="allowLaborPlace" :label="laborPlaceLabel" min-width="120" show-overflow-tooltip>
        <template #default="{ row }">{{ row.laborPlace || '—' }}</template>
      </el-table-column>
      <el-table-column v-if="allowEffectiveOn" :label="effectiveOnLabel" width="120">
        <template #default="{ row }">{{ row.effectiveOn || '—' }}</template>
      </el-table-column>
      <el-table-column v-if="allowCertIssueNo" :label="certIssueNoLabel" width="140" show-overflow-tooltip>
        <template #default="{ row }">{{ row.certIssueNo || '—' }}</template>
      </el-table-column>
      <el-table-column v-if="allowDocRev" :label="docRevLabel" width="120" show-overflow-tooltip>
        <template #default="{ row }">{{ row.docRev || '—' }}</template>
      </el-table-column>
      <el-table-column v-if="allowFitoutQuiet" :label="fitoutWindowLabel" width="140">
        <template #default="{ row }">{{ row.workStart || '—' }}–{{ row.workEnd || '—' }}</template>
      </el-table-column>
      <el-table-column v-if="allowIssueCopies" :label="issueCopiesLabel" width="100">
        <template #default="{ row }">{{ row.issueCopies != null ? row.issueCopies : '—' }}</template>
      </el-table-column>
      <el-table-column v-if="allowSignParties" :label="signPartiesLabel" min-width="140" show-overflow-tooltip>
        <template #default="{ row }">{{ row.signParties || '—' }}</template>
      </el-table-column>
      <el-table-column v-if="allowTrainHours" :label="trainHoursLabel" width="120">
        <template #default="{ row }">{{ row.trainHours != null ? row.trainHours : '—' }}</template>
      </el-table-column>
      <el-table-column v-if="allowMemberChange" :label="memberChangeNoteLabel" min-width="160" show-overflow-tooltip>
        <template #default="{ row }">{{ row.memberChangeNote || '—' }}</template>
      </el-table-column>
      <el-table-column v-if="allowProcureBudget" :label="procureAmountLabel" width="120">
        <template #default="{ row }">{{ row.procureAmount != null ? row.procureAmount : '—' }}</template>
      </el-table-column>
      <el-table-column v-if="allowCheckinException" :label="exceptionTypeLabel" width="120">
        <template #default="{ row }">{{ row.exceptionType || '—' }}</template>
      </el-table-column>
      <el-table-column v-if="allowVisitPurpose" :label="visitPurposeLabel" width="120">
        <template #default="{ row }">{{ row.visitPurpose || '—' }}</template>
      </el-table-column>
      <el-table-column v-if="allowFitoutRectify" :label="rectifyNoteLabel" min-width="160" show-overflow-tooltip>
        <template #default="{ row }">{{ row.rectifyNote || '—' }}</template>
      </el-table-column>
      <el-table-column v-if="allowFleetViolation" :label="violationPersonLabel" width="120">
        <template #default="{ row }">{{ row.violationPerson || '—' }}</template>
      </el-table-column>
      <el-table-column v-if="allowProjFundUse" :label="fundUseYuanLabel" width="120">
        <template #default="{ row }">{{ row.fundUseYuan != null ? row.fundUseYuan : '—' }}</template>
      </el-table-column>
      <el-table-column v-if="allowProjFundUse" :label="fundUseNoteLabel" min-width="160" show-overflow-tooltip>
        <template #default="{ row }">{{ row.fundUseNote || '—' }}</template>
      </el-table-column>
      <el-table-column v-if="allowVisitSlotRemain" :label="visitOnLabel" width="120">
        <template #default="{ row }">{{ row.visitOn || '—' }}</template>
      </el-table-column>
      <el-table-column v-if="allowPlagiarismUrl" :label="plagiarismUrlLabel" min-width="180" show-overflow-tooltip>
        <template #default="{ row }">{{ row.plagiarismUrl || '—' }}</template>
      </el-table-column>
      <el-table-column v-if="allowPartyStage" :label="partyStageLabel" width="130">
        <template #default="{ row }">{{ row.partyStage || '—' }}</template>
      </el-table-column>
      <el-table-column v-if="allowPartyStage" :label="stageOnLabel" width="120">
        <template #default="{ row }">{{ row.stageOn || '—' }}</template>
      </el-table-column>
      <el-table-column v-if="allowEvalObserve" :label="observeOnLabel" width="120">
        <template #default="{ row }">{{ row.observeOn || '—' }}</template>
      </el-table-column>
      <el-table-column v-if="allowEvalObserve" :label="observeNoteLabel" min-width="160" show-overflow-tooltip>
        <template #default="{ row }">{{ row.observeNote || '—' }}</template>
      </el-table-column>
      <el-table-column v-if="allowScheduleImpact" :label="scheduleImpactNoteLabel" min-width="160" show-overflow-tooltip>
        <template #default="{ row }">{{ row.scheduleImpactNote || '—' }}</template>
      </el-table-column>
      <el-table-column v-if="allowContractAmount" :label="contractAmountLabel" width="120">
        <template #default="{ row }">{{ row.contractAmount != null ? row.contractAmount : '—' }}</template>
      </el-table-column>
      <el-table-column v-if="allowExpenseLines" :label="expenseLinesLabel" min-width="200" show-overflow-tooltip>
        <template #default="{ row }">{{ formatExpenseLines(row.expenseLines) }}</template>
      </el-table-column>
      <el-table-column v-if="allowTripLegs" :label="tripLegsLabel" min-width="200" show-overflow-tooltip>
        <template #default="{ row }">{{ formatTripLegs(row.tripLegs) }}</template>
      </el-table-column>
      <el-table-column v-if="allowProjChangeLog" :label="changeLogNoteLabel" min-width="160" show-overflow-tooltip>
        <template #default="{ row }">{{ row.changeLogNote || '—' }}</template>
      </el-table-column>
      <el-table-column v-if="allowCertVerify" :label="certVerifyCodeLabel" width="140">
        <template #default="{ row }">{{ row.verifyCode || '—' }}</template>
      </el-table-column>
      <el-table-column v-if="allowVisitWalkIn" :label="visitWalkInLabel" width="100">
        <template #default="{ row }">{{ row.walkIn ? '是' : '—' }}</template>
      </el-table-column>
      <el-table-column v-if="allowCheckinProxy" :label="checkinProxyByLabel" width="120">
        <template #default="{ row }">{{ row.checkinProxyBy || '—' }}</template>
      </el-table-column>
      <el-table-column v-if="allowClubRoster" :label="clubRosterLabel" min-width="180" show-overflow-tooltip>
        <template #default="{ row }">{{ formatClubMembers(row.clubMembers) }}</template>
      </el-table-column>
      <el-table-column v-if="allowCarpassParkingMutex" :label="parkingOnLabel" width="130">
        <template #default="{ row }">{{ row.parkingOn || '—' }}</template>
      </el-table-column>
      <el-table-column v-if="allowContractRenew" :label="renewOnLabel" width="120">
        <template #default="{ row }">{{ row.renewOn || '—' }}</template>
      </el-table-column>
      <el-table-column v-if="allowContractRenew" :label="renewNoteLabel" min-width="160" show-overflow-tooltip>
        <template #default="{ row }">{{ row.renewNote || '—' }}</template>
      </el-table-column>
      <el-table-column v-if="allowCertPickupRedeem" :label="pickupRedeemCodeLabel" width="150">
        <template #default="{ row }">{{ row.pickupRedeemCode || '—' }}</template>
      </el-table-column>
      <el-table-column v-if="allowCertPickupRedeem" :label="pickupRedeemedLabel" width="90">
        <template #default="{ row }">{{ row.pickupRedeemed ? '是' : '否' }}</template>
      </el-table-column>
      <el-table-column v-if="allowProcureReturn" :label="procureReturnFailLabel" width="110">
        <template #default="{ row }">{{ row.returnFail ? '是' : '否' }}</template>
      </el-table-column>
      <el-table-column v-if="allowProcureReturn" :label="returnNoteLabel" min-width="160" show-overflow-tooltip>
        <template #default="{ row }">{{ row.returnNote || '—' }}</template>
      </el-table-column>
      <el-table-column v-if="allowMoralObjection" :label="moralObjectionLabel" min-width="160" show-overflow-tooltip>
        <template #default="{ row }">{{ row.objectionNote || '—' }}</template>
      </el-table-column>
      <el-table-column v-if="allowCheckin" label="签到" width="170">
        <template #default="{ row }">{{ row.checkedInAt || '—' }}</template>
      </el-table-column>
      <el-table-column v-if="issuePassCode" :label="passCodeLabel" width="140">
        <template #default="{ row }">
          {{ row.passCode || '—' }}
          <template v-if="allowPassExpire && row.passExpireAt"> · {{ row.passExpireAt }}</template>
          <template v-if="allowPassExpire && isPassExpired(row)"> · {{ passExpiredLabel }}</template>
        </template>
      </el-table-column>
      <el-table-column prop="returnAt" label="完成时间" width="170" />
      <el-table-column v-if="allowRating" label="评分" width="110">
        <template #default="{ row }">
          <span v-if="row.rating" class="rating">
            {{ row.rating }} 分
            <template v-if="row.ratingAnonymous"> · 匿名</template>
          </span>
          <span v-else class="muted">—</span>
        </template>
      </el-table-column>
      <el-table-column v-if="allowRating && hasRatingDims" label="维度" min-width="160" show-overflow-tooltip>
        <template #default="{ row }">{{ formatDims(row.ratingDimsJson) }}</template>
      </el-table-column>
      <el-table-column v-if="allowRating" label="短评" min-width="140" show-overflow-tooltip>
        <template #default="{ row }">{{ row.ratingRemark || '—' }}</template>
      </el-table-column>
      <el-table-column v-if="allowRating" label="评价时间" width="170">
        <template #default="{ row }">{{ row.ratedAt || '—' }}</template>
      </el-table-column>
      <el-table-column label="操作" min-width="200" fixed="right">
        <template #default="{ row }">
          <div class="table-ops">
          <el-button link type="info" @click="openProgress(row)">进度</el-button>
          <el-button
            v-if="canAdminCheckin(row)"
            link
            type="success"
            @click="openAdminCheckin(row)"
          >{{ adminCheckinLabel }}</el-button>
          <el-button
            v-if="canPickup(row)"
            link
            type="success"
            @click="doPickup(row)"
          >领取登记</el-button>
          <el-button
            v-if="canRedeemPickup(row)"
            link
            type="success"
            @click="doRedeemPickup(row)"
          >{{ pickupRedeemedLabel }}</el-button>
          <el-button
            v-if="canFinePaid(row)"
            link
            type="warning"
            @click="doFinePaid(row)"
          >{{ finePaidLabel }}</el-button>
          <el-button
            v-if="canFineWaive(row)"
            link
            type="info"
            @click="doFineWaive(row)"
          >{{ fineWaiveLabel }}</el-button>
          <el-button
            v-if="canConfirmProcure(row)"
            link
            type="primary"
            @click="doConfirmProcure(row)"
          >{{ confirmProcureLabel }}</el-button>
          <el-button
            v-if="canToStockIn(row)"
            link
            type="success"
            @click="doToStockIn(row)"
          >{{ toStockInLabel }}</el-button>
          <el-button
            v-if="canFinish(row)"
            link
            type="primary"
            @click="finish(row)"
          >{{ verbs.return || '完成' }}</el-button>
          <el-button
            v-if="printTicketOn"
            link
            @click="printTicket(row)"
          >{{ printTicketLabel }}</el-button>
          <el-button
            v-if="canCompensate(row)"
            link
            type="warning"
            @click="doCompensate(row)"
          >{{ compensateVerb }}</el-button>
          <el-button
            v-if="canHold(row)"
            link
            type="warning"
            @click="doHold(row)"
          >挂起</el-button>
          <el-button
            v-if="canResume(row)"
            link
            type="success"
            @click="doResume(row)"
          >恢复</el-button>
          <el-button
            v-if="canRejectAssign(row)"
            link
            type="danger"
            @click="doRejectAssign(row)"
          >拒单回池</el-button>
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

    <TicketProgressDialog v-model="progressVisible" :ticket-id="progressId" />
    <RepairFinishDialog
      v-model="finishVisible"
      :row="finishRow"
      @done="load"
    />
    <el-dialog v-model="adminCheckin.visible" :title="adminCheckinLabel" width="420px" destroy-on-close>
      <p class="muted" v-if="adminCheckin.row">
        为「{{ adminCheckin.row.title || ('编号 ' + adminCheckin.row.id) }}」登记补签
      </p>
      <p v-if="adminCheckinHint" class="muted" style="margin-bottom:8px">{{ adminCheckinHint }}</p>
      <label v-if="allowLateMinutes" class="audit-field" style="display:block;margin-bottom:12px">
        <span class="lab">{{ lateMinutesLabel }}</span>
        <el-input-number v-model="adminCheckin.lateMinutes" :min="0" :max="999" />
      </label>
      <label class="audit-field" style="display:block">
        <span class="lab">备注</span>
        <el-input v-model="adminCheckin.note" maxlength="200" type="textarea" :rows="2" placeholder="选填" />
      </label>
      <template #footer>
        <el-button @click="adminCheckin.visible = false">取消</el-button>
        <el-button type="primary" :loading="adminCheckin.loading" @click="submitAdminCheckin">确认补签</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import http from '../../api/http'
import TicketProgressDialog from '../../components/TicketProgressDialog.vue'
import RepairFinishDialog from '../../components/RepairFinishDialog.vue'
import SchemaLabelHints from '../../components/SchemaLabelHints.vue'
import { RECORDS_HINT_KEYS } from '../../utils/labelHintMount.js'
import {
  archiveCopy,
  followChannelLabel,
  getSchema,
  hasCap,
  hasTrait,
  nextFollowLabel,
  personLabel,
  roleLabel,
  ticketCopy,
  ticketDueLabel,
  ticketFineLabel,
  ticketFinePaidLabel,
  ticketShowsFollowCols,
  ticketShowsLocationCol,
  ticketShowsPriorityCols,
  ticketShowsScheduleCols,
  ticketShowsTypeCol,
} from '../../utils/domainSchema.js'
import { plainFromHtml } from '../../utils/richHtml.js'
import { downloadCsv } from '../../utils/csvDownload.js'
import { printTicketDocument } from '../../utils/ticketFormPrint.js'

const props = defineProps({
  defaultToday: { type: Boolean, default: false },
})

const route = useRoute()
const ticket = ticketCopy()
const archive = archiveCopy()
const labels = computed(() => getSchema()?.labels || {})
const verbs = computed(() => ticket.verbs || {})
const states = computed(() => ticket.states || {})
function statusLabel(row) {
  if (row && row.checkedInAt) return '已签到'
  return states.value[row?.status] || row?.status || ''
}
const richRemark = computed(() => !!ticket.richRemark)
const allowRating = computed(() => !!ticket.allowRating)
const todayBoardOn = computed(() => !!ticket.todayBoard)
const todayBoardHint = computed(() => labels.value.todayBoardHint || '')
const printTicketOn = computed(
  () =>
    !!ticket.printTicket
    || !!ticket.allowCertFormPrint
    || !!ticket.allowSealFormPrint
    || !!ticket.allowProjMidFormPrint
    || !!ticket.allowEthicOpinionPrint
    || !!(labels.value.gradePrintHint || labels.value.bedPrintHint
      || labels.value.closedStackPrintHint || labels.value.equipQrPrintHint),
)
const printTicketLabel = computed(() => labels.value.printTicketLabel || '打印工单')
const exportAttachUrls = computed(() => !!ticket.exportAttachUrls)
const recordsHintKeys = RECORDS_HINT_KEYS
const monthExportHint = computed(() => labels.value.monthExportHint || '')
const checkExportHint = computed(() => labels.value.checkExportHint || '')
const stuNoMaskHint = computed(() => labels.value.stuNoMaskExportHint || '')
const stuNoMaskOn = computed(() => !!stuNoMaskHint.value)
const maskStuNo = ref(false)
const categoryColorOn = computed(() => !!ticket.categoryColorHint || !!ticket.repairThicken)
const repairFinishNeeded = computed(() => !!(
  ticket.repairThicken
  || ticket.requireFaultReason
  || ticket.requireCloseSummary
  || ticket.requireCloseAttach
  || ticket.allowPartsNote
  || ticket.allowSerialNo
  || ticket.allowRemoteUrl
  || ticket.allowHelper
  || ticket.allowQuote
  || ticket.allowKnowledgeDeposit
  || ticket.allowTicketMerge
  || ticket.allowFleetMileage
          || ticket.allowCompHours
          || ticket.allowReturnFuel
  || ticket.allowFleetViolation
  || ticket.allowProcureReturn
  || ticket.allowCertPickup
  || ticket.allowSealCopies
  || ticket.allowAwardCertNo
  || ticket.allowVendorQuotes
))
const hasRatingDims = computed(
  () => Array.isArray(ticket.ratingDims) && ticket.ratingDims.length > 0,
)
const ratingDimLabels = computed(() => {
  const map = {}
  for (const d of ticket.ratingDims || []) {
    if (d?.key) map[d.key] = d.label || d.key
  }
  return map
})
function formatDims(json) {
  if (!json) return '—'
  try {
    const obj = typeof json === 'string' ? JSON.parse(json) : json
    if (!obj || typeof obj !== 'object') return '—'
    return Object.entries(obj)
      .map(([k, v]) => `${ratingDimLabels.value[k] || k}:${v}`)
      .join(' · ')
  } catch {
    return '—'
  }
}
const allowCheckin = computed(() => !!ticket.allowCheckin)
const allowAdminCheckin = computed(() => !!ticket.allowAdminCheckin)
const allowLateMinutes = computed(() => !!ticket.allowLateMinutes)
const allowWishOrder = computed(() => !!ticket.allowWishOrder)
const allowVolunteerRole = computed(() => !!ticket.allowVolunteerRole)
const allowCompanions = computed(() => !!ticket.allowCompanions)
const allowCertPickup = computed(() => !!ticket.allowCertPickup)
const allowCertUrgent = computed(() => !!ticket.allowCertUrgent)
const allowSealCopies = computed(() => !!ticket.allowSealCopies)
const allowSealLedgerExport = computed(() => !!ticket.allowSealLedgerExport)
const sealLedgerExportHint = computed(() => labels.value.sealLedgerExportHint || '')
const sealLedgerExportLabel = computed(() => labels.value.sealLedgerExportLabel || '导出用印台账')
const sealCopyNosLabel = computed(() => labels.value.sealCopyNosLabel || '用印份号')
const sealWitnessAckLabel = computed(() => labels.value.sealWitnessAckLabel || '监印人已确认')
const allowExpenseInvoice = computed(() => !!ticket.allowExpenseInvoice)
const allowVisitorCount = computed(() => !!ticket.allowVisitorCount)
const allowAwardCertNo = computed(() => !!ticket.allowAwardCertNo)
const allowVendorQuotes = computed(
  () => !!ticket.allowVendorQuotes || Number(ticket.minVendorQuotes || 0) > 0,
)
const allowFleetMileage = computed(() => !!ticket.allowFleetMileage)
const allowFleetCrew = computed(() => !!ticket.allowFleetCrew)
const allowCompHours = computed(() => !!ticket.allowCompHours)
const allowReturnFuel = computed(() => !!ticket.allowReturnFuel)
const allowLaborPlace = computed(() => !!ticket.allowLaborPlace)
const allowEffectiveOn = computed(() => !!ticket.allowEffectiveOn)
const allowCertIssueNo = computed(() => !!ticket.allowCertIssueNo)
const allowDocRev = computed(() => !!ticket.allowDocRev)
const allowFitoutQuiet = computed(() => !!ticket.allowFitoutQuiet)
const allowIssueCopies = computed(() => !!ticket.allowIssueCopies)
const allowSignParties = computed(() => !!ticket.allowSignParties)
const allowTrainHours = computed(() => !!ticket.allowTrainHours)
const allowMemberChange = computed(() => !!ticket.allowMemberChange)
const allowProcureBudget = computed(() => !!ticket.allowProcureBudget)
const allowCheckinException = computed(() => !!ticket.allowCheckinException)
const allowVisitPurpose = computed(() => !!ticket.allowVisitPurpose)
const allowFitoutRectify = computed(() => !!ticket.allowFitoutRectify)
const allowFleetViolation = computed(() => !!ticket.allowFleetViolation)
const allowProjNodeRemind = computed(() => !!ticket.allowProjNodeRemind)
const allowClubCopyLast = computed(() => !!ticket.allowClubCopyLast)
const allowProcureReturn = computed(() => !!ticket.allowProcureReturn)
const allowMoralObjection = computed(() => !!ticket.allowMoralObjection)
const allowProjFundUse = computed(() => !!ticket.allowProjFundUse)
const allowEvalDimWeight = computed(() => !!ticket.allowEvalDimWeight)
const allowVisitSlotRemain = computed(() => !!ticket.allowVisitSlotRemain)
const allowPlagiarismUrl = computed(() => !!ticket.allowPlagiarismUrl)
const allowPartyStage = computed(() => !!ticket.allowPartyStage)
const allowEvalObserve = computed(() => !!ticket.allowEvalObserve)
const allowScheduleImpact = computed(() => !!ticket.allowScheduleImpact)
const allowContractAmount = computed(() => !!ticket.allowContractAmount)
const allowExpenseLines = computed(() => !!ticket.allowExpenseLines)
const allowTripLegs = computed(() => !!ticket.allowTripLegs)
const allowProjChangeLog = computed(() => !!ticket.allowProjChangeLog)
const allowCertVerify = computed(() => !!ticket.allowCertVerify)
const allowVisitWalkIn = computed(() => !!ticket.allowVisitWalkIn)
const allowCheckinProxy = computed(() => !!ticket.allowCheckinProxy)
const allowClubRoster = computed(() => !!ticket.allowClubRoster)
const allowCarpassParkingMutex = computed(() => !!ticket.allowCarpassParkingMutex)
const allowContractRenew = computed(() => !!ticket.allowContractRenew)
const allowCertPickupRedeem = computed(() => !!ticket.allowCertPickupRedeem)
const expenseLinesLabel = computed(() => labels.value.expenseLinesLabel || '报销明细')
const tripLegsLabel = computed(() => labels.value.tripLegsLabel || '出差行程')
const changeLogNoteLabel = computed(() => labels.value.changeLogNoteLabel || '变更摘要')
const certVerifyCodeLabel = computed(() => labels.value.certVerifyCodeLabel || '真伪查询码')
const visitWalkInLabel = computed(() => labels.value.visitWalkInLabel || '现场补录')
const checkinProxyByLabel = computed(() => labels.value.checkinProxyByLabel || '代登人')
const clubRosterLabel = computed(() => labels.value.clubRosterLabel || '成员名册')
const parkingOnLabel = computed(() => labels.value.parkingOnLabel || '占用车位日期')
const renewOnLabel = computed(() => labels.value.renewOnLabel || '续签日期')
const renewNoteLabel = computed(() => labels.value.renewNoteLabel || '续签说明')
const pickupRedeemCodeLabel = computed(() => labels.value.pickupRedeemCodeLabel || '领取核销码')
const pickupRedeemedLabel = computed(() => labels.value.pickupRedeemedLabel || '已核销')
const pickupRedeemHint = computed(() => labels.value.pickupRedeemHint || '')
function formatClubMembers(raw) {
  try {
    const arr = typeof raw === 'string' ? JSON.parse(raw) : raw
    if (!Array.isArray(arr)) return raw || '—'
    return arr.map((x) => `${x.name || ''}${x.studentNo ? `（${x.studentNo}）` : ''}`).join('，') || '—'
  } catch {
    return raw || '—'
  }
}
function formatExpenseLines(raw) {
  try {
    const arr = typeof raw === 'string' ? JSON.parse(raw) : raw
    if (!Array.isArray(arr)) return raw || '—'
    return arr.map((x) => `${x.category || ''} ${x.amount ?? ''}${x.note ? `（${x.note}）` : ''}`).join('；') || '—'
  } catch {
    return raw || '—'
  }
}
function formatTripLegs(raw) {
  try {
    const arr = typeof raw === 'string' ? JSON.parse(raw) : raw
    if (!Array.isArray(arr)) return raw || '—'
    return arr.map((x) => `${x.on || ''} ${x.from || ''}→${x.via ? `${x.via}→` : ''}${x.to || ''}`).join('；') || '—'
  } catch {
    return raw || '—'
  }
}
const fundUseYuanLabel = computed(() => labels.value.fundUseYuanLabel || '本次使用经费（元）')
const fundUseNoteLabel = computed(() => labels.value.fundUseNoteLabel || '经费使用说明')
const visitOnLabel = computed(() => labels.value.visitOnLabel || '来访日期')
const plagiarismUrlLabel = computed(() => labels.value.plagiarismUrlLabel || '查重报告链接')
const partyStageLabel = computed(() => labels.value.partyStageLabel || '当前发展阶段')
const stageOnLabel = computed(() => labels.value.stageOnLabel || '进入该阶段日期')
const observeOnLabel = computed(() => labels.value.observeOnLabel || '听课日期')
const observeNoteLabel = computed(() => labels.value.observeNoteLabel || '听课记录')
const scheduleImpactNoteLabel = computed(() => labels.value.scheduleImpactNoteLabel || '对课表的影响')
const contractAmountLabel = computed(() => labels.value.contractAmountLabel || '合同金额（元）')
const procureReturnFailLabel = computed(() => labels.value.procureReturnFailLabel || '验收不合格')
const returnNoteLabel = computed(() => labels.value.returnNoteLabel || '退货说明')
const moralObjectionLabel = computed(() => labels.value.moralObjectionLabel || '异议说明')
const allowPassExpire = computed(() => !!ticket.allowPassExpire)
const returnFuelLabel = computed(() => labels.value.returnFuelLabel || '回场油量')
const laborPlaceLabel = computed(() => labels.value.laborPlaceLabel || '劳动地点')
const effectiveOnLabel = computed(() => labels.value.effectiveOnLabel || '生效日期')
const certIssueNoLabel = computed(() => labels.value.certIssueNoLabel || '开具流水号')
const docRevLabel = computed(() => labels.value.docRevLabel || '正文版本号')
const fitoutWindowLabel = computed(() => labels.value.fitoutWindowLabel || '施工时段')
const issueCopiesLabel = computed(() => labels.value.issueCopiesLabel || '开具份数')
const signPartiesLabel = computed(() => labels.value.signPartiesLabel || '签署方')
const trainHoursLabel = computed(() => labels.value.trainHoursLabel || '本次培训学时')
const memberChangeNoteLabel = computed(() => labels.value.memberChangeNoteLabel || '成员变更说明')
const procureAmountLabel = computed(() => labels.value.procureAmountLabel || '本次申购金额（元）')
const exceptionTypeLabel = computed(() => labels.value.exceptionTypeLabel || '异常类型')
const visitPurposeLabel = computed(() => labels.value.visitPurposeLabel || '来访目的')
const rectifyNoteLabel = computed(() => labels.value.rectifyNoteLabel || '整改说明')
const violationPersonLabel = computed(() => labels.value.violationPersonLabel || '违章责任人')
const projNodeRemindHint = computed(() => labels.value.projNodeRemindHint || '')
const passExpireAtLabel = computed(() => labels.value.passExpireAtLabel || '通行码有效至')
const passExpiredLabel = computed(() => labels.value.passExpiredLabel || '已失效')
function isPassExpired(row) {
  if (!allowPassExpire.value || !row || !row.passExpireAt) return false
  const t = Date.parse(String(row.passExpireAt).replace('T', ' '))
  return Number.isFinite(t) && Date.now() > t
}
const adminCheckinLabel = computed(() => labels.value.adminCheckinLabel || '补签')
const adminCheckinHint = computed(() => labels.value.adminCheckinHint || '')
const lateMinutesLabel = computed(() => labels.value.lateMinutesLabel || '迟到分钟数')
const wishOrderLabel = computed(() => labels.value.wishOrderLabel || '志愿序')
const volunteerRoleLabel = computed(() => labels.value.volunteerRoleLabel || '报名岗位')
const companionNamesLabel = computed(() => labels.value.companionNamesLabel || '同行人姓名')
const certPickupLabel = computed(() => labels.value.certPickupLabel || '领取方式')
const expressNoLabel = computed(() => labels.value.expressNoLabel || '快递单号')
const certUrgentLabel = computed(() => labels.value.certUrgentLabel || '加急件')
const sealCopiesLabel = computed(() => labels.value.sealCopiesLabel || '用印份数')
const invoiceCountLabel = computed(() => labels.value.invoiceCountLabel || '发票张数')
const visitorCountLabel = computed(() => labels.value.visitorCountLabel || '随行人数')
const awardCertNoLabel = computed(() => labels.value.awardCertNoLabel || '证书编号')
const driverNameLabel = computed(() => labels.value.driverNameLabel || '驾驶员')
const passengerNamesLabel = computed(() => labels.value.passengerNamesLabel || '随车人')
const compHoursLabel = computed(() => labels.value.compHoursLabel || '核定调休小时')
const vendorQuotesLabel = computed(() => labels.value.vendorQuotesLabel || '比价供应商')
const mileageLabel = computed(() => labels.value.mileageLabel || '行驶里程')
const absentExportHint = computed(() => labels.value.absentExportHint || '')
const activityProofHint = computed(() => labels.value.activityProofHint || '')
const allowLottery = computed(() => !!ticket.allowLottery)
const lotteryDrawLabel = computed(() => labels.value.lotteryDrawLabel || '抽签录取')
const lotteryDrawHint = computed(() => labels.value.lotteryDrawHint || '')
const allowPostGallery = computed(() => !!ticket.allowPostGallery)
const postGalleryLabel = computed(() => labels.value.postGalleryLabel || '活动相册')
const postGalleryHint = computed(() => labels.value.postGalleryHint || '')
const requireCreditWritebackAck = computed(() => !!ticket.requireCreditWritebackAck)
const creditWritebackHint = computed(() => labels.value.creditWritebackHint || '')
const lotteryLoading = ref(false)
async function runLotteryDraw() {
  const itemId = list.value?.[0]?.itemId || list.value?.[0]?.archiveId
  if (!itemId) {
    ElMessage.warning('请先查询到含档案编号的记录再抽签')
    return
  }
  lotteryLoading.value = true
  try {
    const res = await http.post('/api/tickets/lottery-draw', { itemId })
    const d = res.data || {}
    ElMessage.success(`已抽取 ${d.drawn || 0} 人（池 ${d.poolSize || 0}）`)
    load()
  } finally {
    lotteryLoading.value = false
  }
}
const exportBtnLabel = computed(() => {
  if (status.value === 'absent' && (labels.value.absentExportLabel || '')) {
    return labels.value.absentExportLabel
  }
  if (allowSealLedgerExport.value && sealLedgerExportLabel.value) {
    return sealLedgerExportLabel.value
  }
  return monthExportHint.value || checkExportHint.value || '导出 CSV'
})
const issuePassCode = computed(() => !!ticket.issuePassCode)
const passCodeLabel = computed(() => ticket.passCodeLabel || '通行码')
const allowQty = computed(() => !!ticket.allowQty)
const pickLoanPeriod = computed(() => !!ticket.pickLoanPeriod)
const dueLabel = computed(() => ticketDueLabel())
const fineLabel = computed(() => ticketFineLabel())
const finePaidLabel = computed(() => ticketFinePaidLabel())
const allowFineWaive = computed(() => !!ticket.allowFineWaive)
const fineWaiveLabel = computed(() => labels.value.fineWaiveLabel || '罚款减免')
const allowProcureRef = computed(() => !!ticket.allowProcureRef)
const confirmProcureLabel = computed(
  () => labels.value.confirmProcureTransferLabel || '确认申购转入',
)
const procureToStockIn = computed(() => !!ticket.procureToStockIn)
const toStockInLabel = computed(() => labels.value.toStockInLabel || '一键入库')
const userLabel = computed(() => roleLabel('user', '申请人'))
const showPickup = computed(() => hasTrait('pickupFlow'))
const approveEndsFlow = computed(() => !!ticket.approveEndsFlow)
const showFollowCols = computed(() => ticketShowsFollowCols())
const channelLabel = computed(() => followChannelLabel())
const nextAtLabel = computed(() => nextFollowLabel())
const showScheduleCols = computed(() => ticketShowsScheduleCols(ticket, archive))
const showTypeCol = computed(() => ticketShowsTypeCol(archive))
const showLocationCol = computed(() => ticketShowsLocationCol(archive))
const showPriorityCols = computed(() => ticketShowsPriorityCols())
const allowEmergencyContact = computed(() => !!ticket.allowEmergencyContact)
const requireInsuranceAck = computed(() => !!ticket.requireInsuranceAck)
const emergencyContactLabel = computed(() => labels.value.emergencyContactLabel || '紧急联系人')
const emergencyPhoneLabel = computed(() => labels.value.emergencyPhoneLabel || '紧急联系电话')
const insuranceAckColLabel = computed(() => labels.value.insuranceAckLabel || '保险声明')
const showFine = computed(
  () => hasTrait('loanFine') || !!ticket.fineLabel || Number(ticket.noShowPenaltyYuan) > 0,
)

const superAdmin = localStorage.getItem('superAdmin') === 'true'
const myUid = localStorage.getItem('uid') || ''

/** 驿站/失物核销流：approved/overdue 即终态；子管仅处理人可完结 */
function canFinish(row) {
  if (!row) return false
  // 报修等：须申请人确认完结，管理端不代点
  if (ticket.applicantCompleteOnly) return false
  if (approveEndsFlow.value && showPickup.value) return false
  if (!(row.status === 'approved' || row.status === 'overdue')) return false
  if (superAdmin) return true
  const asg = row.assigneeUsername
  if (!asg) return true
  return asg === myUid
}

const allowBookLost = computed(() => !!(ticket.allowBookLost || hasCap('book_lost')))
const compensateVerb = computed(
  () => ticket.verbs?.compensate || labels.value.bookCompensateVerb || '登记赔偿完成',
)

function canCompensate(row) {
  return !!allowBookLost.value && !!row && row.status === 'lost'
}

async function doCompensate(row) {
  await ElMessageBox.confirm(
    `确认「${row.title || ('编号 ' + row.id)}」赔偿已完成？`,
    compensateVerb.value,
  )
  await http.post(`/api/tickets/${row.id}/compensate`)
  ElMessage.success(labels.value.bookCompensateOkMessage || '赔偿已登记完成')
  load()
}

const adminCheckin = reactive({
  visible: false,
  loading: false,
  row: null,
  lateMinutes: 0,
  note: '',
})

function canAdminCheckin(row) {
  if (!allowAdminCheckin.value || !allowCheckin.value || !row) return false
  if (row.status !== 'approved') return false
  return !row.checkedInAt
}

function openAdminCheckin(row) {
  Object.assign(adminCheckin, {
    visible: true,
    loading: false,
    row,
    lateMinutes: 0,
    note: '',
  })
}

async function submitAdminCheckin() {
  if (!adminCheckin.row) return
  adminCheckin.loading = true
  try {
    const body = { note: (adminCheckin.note || '').trim() }
    if (allowLateMinutes.value) body.lateMinutes = Number(adminCheckin.lateMinutes) || 0
    await http.post(`/api/tickets/${adminCheckin.row.id}/admin-checkin`, body)
    ElMessage.success('补签已登记')
    adminCheckin.visible = false
    load()
  } catch {
    // http 拦截器已提示
  } finally {
    adminCheckin.loading = false
  }
}

function canConfirmProcure(row) {
  return !!allowProcureRef.value && !!row && String(row.procureRefNo || '').trim()
}

async function doConfirmProcure(row) {
  await ElMessageBox.confirm(
    `确认申购单号「${row.procureRefNo}」已转入本领用单？`,
    confirmProcureLabel.value,
  )
  try {
    await http.post(`/api/tickets/${row.id}/confirm-procure-transfer`)
    ElMessage.success('已确认申购转入')
    load()
  } catch (e) {
    ElMessage.error(e?.response?.data?.message || e?.message || '操作失败')
  }
}

function canToStockIn(row) {
  if (!procureToStockIn.value || !row) return false
  return row.status === 'approved' || row.status === 'returned' || row.status === 'completed'
}

async function doToStockIn(row) {
  await ElMessageBox.confirm(
    `将申购单「${row.title || row.id}」明细一键转入库存？`,
    toStockInLabel.value,
  )
  try {
    const res = await http.post(`/api/tickets/${row.id}/to-stock-in`)
    const data = res.data?.data || res.data || {}
    const n = data.stockIn?.count ?? data.count
    ElMessage.success(n != null ? `已入库 ${n} 行` : '已入库')
    load()
  } catch (e) {
    ElMessage.error(e?.response?.data?.message || e?.message || '入库失败')
  }
}

function archiveFieldLabel(key, fallback) {
  const f = (archive.fields || []).find((x) => x.key === key)
  return f?.label || fallback
}

const typeColLabel = computed(() => {
  if ((archive.fields || []).some((f) => f.key === 'itemKind')) {
    return archiveFieldLabel('itemKind', '类型')
  }
  if ((archive.fields || []).some((f) => f.key === 'category')) {
    return archiveFieldLabel('category', '类型')
  }
  return '类型'
})

const locationColLabel = computed(() => {
  if ((archive.fields || []).some((f) => f.key === 'isbn')) {
    return archiveFieldLabel('isbn', '地点')
  }
  return '地点'
})

function remarkText(v) {
  if (!v) return '—'
  return plainFromHtml(String(v)) || '—'
}

function canPickup(row) {
  if (!showPickup.value || !row) return false
  if (row.pickupAt) return false
  // 与后端一致：退库后不可再登记，避免库存回补错乱
  return row.status === 'approved' || row.status === 'overdue'
}

function canRedeemPickup(row) {
  if (!allowCertPickupRedeem.value || !row) return false
  if (!row.pickupRedeemCode || row.pickupRedeemed) return false
  return row.status === 'approved' || row.status === 'returned'
}

function canFinePaid(row) {
  if (!showFine.value || !row) return false
  if (!(Number(row.fineYuan) > 0)) return false
  if (row.fineStatus === 'paid' || row.fineStatus === 'waived') return false
  return ['approved', 'overdue', 'returned'].includes(row.status)
}

function canFineWaive(row) {
  if (!allowFineWaive.value || !showFine.value || !row) return false
  if (row.fineStatus === 'paid' || row.fineStatus === 'waived') return false
  if (!(Number(row.fineYuan) > 0) && row.status !== 'overdue') return false
  return ['approved', 'overdue', 'returned'].includes(row.status)
}

const list = ref([])
const total = ref(0)
const page = ref(1)
const size = ref(10)
const status = ref(null)
const ratedOnly = ref(false)
const todayOnly = ref(!!props.defaultToday)
const progressVisible = ref(false)
const progressId = ref(null)
const finishVisible = ref(false)
const finishRow = ref(null)

function typeColor(key) {
  const s = String(key || '')
  let h = 0
  for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) >>> 0
  const hue = h % 360
  return `hsl(${hue} 55% 48%)`
}

function listParams(extra = {}) {
  const params = {
    page: page.value,
    size: size.value,
    status: status.value || undefined,
    ...extra,
  }
  if (allowRating.value && ratedOnly.value) params.rated = true
  if (todayBoardOn.value && todayOnly.value) params.todayAssigned = true
  return params
}

function onFilter() {
  page.value = 1
  load()
}

async function load() {
  const res = await http.get('/api/tickets', { params: listParams() })
  list.value = res.data.list
  total.value = res.data.total
}

async function finish(row) {
  if (repairFinishNeeded.value) {
    finishRow.value = row
    finishVisible.value = true
    return
  }
  const body = {}
  if (ticket.allowExceptionClose) {
    const { value: er } = await ElMessageBox.prompt(
      '异常件可填写原因；正常办结可留空',
      labels.value.exceptionReasonLabel || '异常件原因',
      {
        confirmButtonText: '继续',
        cancelButtonText: '取消',
        inputPlaceholder: '选填',
      },
    ).catch(() => ({ value: null }))
    if (er === null) return
    if (String(er || '').trim()) body.exceptionReason = String(er).trim()
    const { value: dn } = await ElMessageBox.prompt(
      '如有破损理赔说明可填写',
      labels.value.damageClaimLabel || '破损理赔说明',
      {
        confirmButtonText: '办结',
        cancelButtonText: '取消',
        inputPlaceholder: '选填',
        inputType: 'textarea',
      },
    ).catch(() => ({ value: null }))
    if (dn === null) return
    if (String(dn || '').trim()) body.damageClaimNote = String(dn).trim()
  } else {
    await ElMessageBox.confirm(`确认标记「${row.title}」为已完成？`, '完成')
  }
  await http.post(`/api/tickets/${row.id}/complete`, body)
  ElMessage.success('已完成')
  load()
}

function printTicket(row) {
  const ok = printTicketDocument(row, {
    ticket,
    labels: labels.value,
    statusText: statusLabel,
    personLabel,
    remarkText: (r) => plainFromHtml(r || ''),
  })
  if (!ok) ElMessage.warning('请允许弹出窗口以打印')
}

const repairThickenOn = computed(() => !!ticket.repairThicken || !!ticket.allowHoldResume)

function canHold(row) {
  if (!repairThickenOn.value || !ticket.allowHoldResume || !row) return false
  return row.status === 'approved' || row.status === 'overdue'
}

function canResume(row) {
  return !!(repairThickenOn.value && ticket.allowHoldResume && row && row.status === 'paused')
}

function canRejectAssign(row) {
  if (!repairThickenOn.value || !row) return false
  return row.status === 'approved' || row.status === 'overdue' || row.status === 'paused'
}

async function doHold(row) {
  const { value } = await ElMessageBox.prompt('请填写挂起原因', '挂起工单', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    inputPattern: /\S+/,
    inputErrorMessage: '请填写原因',
  })
  await http.post(`/api/tickets/${row.id}/hold`, { reason: value })
  ElMessage.success('已挂起')
  load()
}

async function doResume(row) {
  await ElMessageBox.confirm(`确认恢复「${row.title || row.id}」继续处理？`, '恢复')
  await http.post(`/api/tickets/${row.id}/resume`)
  ElMessage.success('已恢复')
  load()
}

async function doRejectAssign(row) {
  const { value } = await ElMessageBox.prompt('请填写拒单原因（将回池待受理）', '拒单回池', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    inputPattern: /\S+/,
    inputErrorMessage: '请填写原因',
  })
  await http.post(`/api/tickets/${row.id}/reject-assignment`, { reason: value })
  ElMessage.success('已回池')
  load()
}

function openProgress(row) {
  progressId.value = row.id
  progressVisible.value = true
}

async function doPickup(row) {
  const applied = Math.max(1, Number(row.qty) || 1)
  const { value } = await ElMessageBox.prompt(
    '领取地点（可留空则使用系统默认配置；两者皆空将无法登记）',
    '领取登记',
    {
      confirmButtonText: '下一步',
      cancelButtonText: '取消',
      inputPlaceholder: '如 行政楼地下库房',
      inputValue: row.pickupPlace || '',
      inputValidator: (v) => {
        if (String(v || '').trim().length > 128) return '领取地点过长'
        return true
      },
    },
  ).catch(() => ({ value: null }))
  if (value === null) return
  const body = { pickupPlace: String(value || '').trim() }
  if (allowQty.value) {
    const { value: qty } = await ElMessageBox.prompt(
      `实发数量（申领 ${applied}，不可超过）`,
      '领取登记',
      {
        confirmButtonText: '登记',
        cancelButtonText: '取消',
        inputValue: String(applied),
        inputValidator: (v) => {
          const s = String(v ?? '').trim()
          if (!/^[1-9]\d*$/.test(s)) return '请输入正整数'
          const n = Number(s)
          if (n > applied) return `不能超过申领数量 ${applied}`
          return true
        },
      },
    ).catch(() => ({ value: null }))
    if (qty === null) return
    body.actualQty = Number(qty)
  }
  try {
    await http.post(`/api/tickets/${row.id}/pickup`, body)
    ElMessage.success('已登记领取，已通知申请人')
    load()
  } catch {
    // http 拦截器已提示业务错误
  }
}

async function doRedeemPickup(row) {
  const { value } = await ElMessageBox.prompt(
    pickupRedeemHint.value || `请填写${pickupRedeemCodeLabel.value}`,
    pickupRedeemedLabel.value,
    {
      confirmButtonText: '核销',
      cancelButtonText: '取消',
      inputPlaceholder: pickupRedeemCodeLabel.value,
      inputValidator: (v) => {
        if (!String(v || '').trim()) return `请填写${pickupRedeemCodeLabel.value}`
        return true
      },
    },
  ).catch(() => ({ value: null }))
  if (value === null) return
  try {
    await http.post(`/api/tickets/${row.id}/redeem-pickup`, { code: String(value || '').trim() })
    ElMessage.success('已核销领取')
    load()
  } catch {
    // http 拦截器已提示业务错误
  }
}

async function doFinePaid(row) {
  await ElMessageBox.confirm(`确认「${row.title || row.id}」${finePaidLabel.value}？`, finePaidLabel.value)
  await http.post(`/api/tickets/${row.id}/fine-paid`)
  ElMessage.success(`已标记${finePaidLabel.value}`)
  load()
}

async function doFineWaive(row) {
  const { value } = await ElMessageBox.prompt('请填写减免原因', fineWaiveLabel.value, {
    confirmButtonText: '确认减免',
    cancelButtonText: '取消',
    inputPattern: /\S+/,
    inputErrorMessage: '请填写原因',
  })
  await http.post(`/api/tickets/${row.id}/fine-waive`, { reason: value })
  ElMessage.success('已登记罚款减免')
  load()
}

async function exportCsv() {
  const res = await http.get('/api/tickets', {
    params: listParams({ page: 1, size: 5000 }),
  })
  const rows = res.data?.list || []
  if (!rows.length) {
    ElMessage.warning('当前筛选无数据可导出')
    return
  }
  const headers = ['编号', '标题']
  if (showTypeCol.value) headers.push(typeColLabel.value)
  if (showLocationCol.value) headers.push(locationColLabel.value)
  if (showPriorityCols.value) headers.push('优先级', '联系电话')
  if (allowEmergencyContact.value) headers.push(emergencyContactLabel.value, emergencyPhoneLabel.value)
  if (requireInsuranceAck.value) headers.push(insuranceAckColLabel.value)
  if (allowWishOrder.value) headers.push(wishOrderLabel.value)
  if (allowVolunteerRole.value) headers.push(volunteerRoleLabel.value)
  if (allowCompanions.value) headers.push(companionNamesLabel.value)
  if (allowCertPickup.value) headers.push(certPickupLabel.value, '邮寄地址')
  if (allowSealCopies.value) headers.push(sealCopiesLabel.value, '装订说明')
  if (allowSealLedgerExport.value) {
    headers.push(sealCopyNosLabel.value, sealWitnessAckLabel.value)
  }
  if (allowExpenseInvoice.value) headers.push(invoiceCountLabel.value, '报销金额')
  if (allowVisitorCount.value) headers.push(visitorCountLabel.value)
  if (allowAwardCertNo.value) headers.push(awardCertNoLabel.value)
  if (allowVendorQuotes.value) headers.push(vendorQuotesLabel.value)
  if (allowFleetMileage.value) headers.push(mileageLabel.value, '油耗备注')
  if (allowFleetCrew.value) headers.push(driverNameLabel.value, passengerNamesLabel.value)
  if (allowCompHours.value) headers.push(compHoursLabel.value)
  if (allowReturnFuel.value) headers.push(returnFuelLabel.value)
  if (allowLaborPlace.value) headers.push(laborPlaceLabel.value)
  if (allowEffectiveOn.value) headers.push(effectiveOnLabel.value)
  if (allowCertIssueNo.value) headers.push(certIssueNoLabel.value)
  if (allowDocRev.value) headers.push(docRevLabel.value)
  if (allowFitoutQuiet.value) headers.push(fitoutWindowLabel.value)
  if (allowIssueCopies.value) headers.push(issueCopiesLabel.value)
  if (allowSignParties.value) headers.push(signPartiesLabel.value)
  if (allowTrainHours.value) headers.push(trainHoursLabel.value)
  if (allowMemberChange.value) headers.push(memberChangeNoteLabel.value)
  if (allowProcureBudget.value) headers.push(procureAmountLabel.value)
  if (allowCheckinException.value) headers.push(exceptionTypeLabel.value)
  if (allowVisitPurpose.value) headers.push(visitPurposeLabel.value)
  if (allowFitoutRectify.value) headers.push(rectifyNoteLabel.value)
  if (allowFleetViolation.value) headers.push(violationPersonLabel.value)
  if (allowProjFundUse.value) headers.push(fundUseYuanLabel.value, fundUseNoteLabel.value)
  if (allowVisitSlotRemain.value) headers.push(visitOnLabel.value)
  if (allowPlagiarismUrl.value) headers.push(plagiarismUrlLabel.value)
  if (allowPartyStage.value) headers.push(partyStageLabel.value, stageOnLabel.value)
  if (allowEvalObserve.value) headers.push(observeOnLabel.value, observeNoteLabel.value)
  if (allowScheduleImpact.value) headers.push(scheduleImpactNoteLabel.value)
  if (allowContractAmount.value) headers.push(contractAmountLabel.value)
  if (allowExpenseLines.value) headers.push(expenseLinesLabel.value)
  if (allowTripLegs.value) headers.push(tripLegsLabel.value)
  if (allowProjChangeLog.value) headers.push(changeLogNoteLabel.value)
  if (allowCertVerify.value) headers.push(certVerifyCodeLabel.value)
  if (allowVisitWalkIn.value) headers.push(visitWalkInLabel.value)
  if (allowCheckinProxy.value) headers.push(checkinProxyByLabel.value)
  if (allowClubRoster.value) headers.push(clubRosterLabel.value)
  if (allowCarpassParkingMutex.value) headers.push(parkingOnLabel.value)
  if (allowContractRenew.value) headers.push(renewOnLabel.value, renewNoteLabel.value)
  if (allowCertPickupRedeem.value) headers.push(pickupRedeemCodeLabel.value, pickupRedeemedLabel.value)
  if (allowProcureReturn.value) headers.push(procureReturnFailLabel.value, returnNoteLabel.value)
  if (allowMoralObjection.value) headers.push(moralObjectionLabel.value)
  if (issuePassCode.value && allowPassExpire.value) headers.push(passExpireAtLabel.value)
  headers.push(userLabel.value, '处理人', '状态')
  if (allowQty.value) headers.push('数量')
  if (pickLoanPeriod.value) headers.push(dueLabel.value)
  if (showFine.value) headers.push(fineLabel.value)
  if (showPickup.value) {
    headers.push('领取地点', '领取时间')
    if (allowQty.value) headers.push('实发数量')
  }
  if (showScheduleCols.value) headers.push('开始', '结束')
  headers.push('说明', '附件')
  if (exportAttachUrls.value) headers.push('结单附件')
  if (showFollowCols.value) headers.push(channelLabel.value, nextAtLabel.value)
  headers.push('申请时间', '受理时间')
  if (allowCheckin.value) headers.push('签到时间')
  headers.push('完成时间')
  if (allowRating.value) headers.push('评分', '短评', '评价时间')

  const data = rows.map((row) => {
    let person = personLabel(row, '')
    if (maskStuNo.value && person) {
      person = String(person).replace(/\d{4,}/g, (m) => `${m.slice(0, 2)}****${m.slice(-2)}`)
    }
    const line = [row.id, row.title]
    if (showTypeCol.value) line.push(row.typeName)
    if (showLocationCol.value) line.push(row.location)
    if (showPriorityCols.value) line.push(row.priority || '', row.contactPhone || '')
    if (allowEmergencyContact.value) {
      line.push(row.emergencyContact || '', row.emergencyPhone || '')
    }
    if (requireInsuranceAck.value) {
      line.push(row.insuranceAck ? '已勾选' : '')
    }
    if (allowWishOrder.value) {
      line.push(row.wishOrder === 1 ? '第一志愿' : row.wishOrder === 2 ? '第二志愿' : '')
    }
    if (allowVolunteerRole.value) {
      line.push(row.volunteerRole || '')
    }
    if (allowCompanions.value) {
      line.push(row.companionNames || '')
    }
    if (allowCertPickup.value) {
      line.push(row.pickupMethod || '', row.mailAddress || '')
    }
    if (allowSealCopies.value) {
      line.push(row.sealCopies != null ? row.sealCopies : '', row.bindNote || '')
    }
    if (allowSealLedgerExport.value) {
      line.push(row.sealCopyNos || '', row.sealWitnessAck ? '已监印' : '')
    }
    if (allowExpenseInvoice.value) {
      line.push(row.invoiceCount != null ? row.invoiceCount : '', row.fineYuan > 0 ? row.fineYuan : '')
    }
    if (allowVisitorCount.value) {
      line.push(row.visitorCount != null ? row.visitorCount : '')
    }
    if (allowAwardCertNo.value) {
      line.push(row.awardCertNo || '')
    }
    if (allowVendorQuotes.value) {
      line.push(row.vendorQuotes || '')
    }
    if (allowFleetMileage.value) {
      line.push(row.mileageKm != null ? row.mileageKm : '', row.fuelNote || '')
    }
    if (allowFleetCrew.value) {
      line.push(row.driverName || '', row.passengerNames || '')
    }
    if (allowCompHours.value) {
      line.push(row.compHours != null ? row.compHours : '')
    }
    if (allowReturnFuel.value) {
      line.push(row.returnFuel != null ? row.returnFuel : '')
    }
    if (allowLaborPlace.value) {
      line.push(row.laborPlace || '')
    }
    if (allowEffectiveOn.value) {
      line.push(row.effectiveOn || '')
    }
    if (allowCertIssueNo.value) {
      line.push(row.certIssueNo || '')
    }
    if (allowDocRev.value) {
      line.push(row.docRev || '')
    }
    if (allowFitoutQuiet.value) {
      line.push([row.workStart, row.workEnd].filter(Boolean).join('-'))
    }
    if (allowIssueCopies.value) {
      line.push(row.issueCopies ?? '')
    }
    if (allowSignParties.value) {
      line.push(row.signParties || '')
    }
    if (allowTrainHours.value) {
      line.push(row.trainHours ?? '')
    }
    if (allowMemberChange.value) {
      line.push(row.memberChangeNote || '')
    }
    if (allowProcureBudget.value) {
      line.push(row.procureAmount ?? '')
    }
    if (allowCheckinException.value) {
      line.push(row.exceptionType || '')
    }
    if (allowVisitPurpose.value) {
      line.push(row.visitPurpose || '')
    }
    if (allowFitoutRectify.value) {
      line.push(row.rectifyNote || '')
    }
    if (allowFleetViolation.value) {
      line.push(row.violationPerson || '')
    }
    if (allowProjFundUse.value) {
      line.push(row.fundUseYuan ?? '', row.fundUseNote || '')
    }
    if (allowVisitSlotRemain.value) {
      line.push(row.visitOn || '')
    }
    if (allowPlagiarismUrl.value) {
      line.push(row.plagiarismUrl || '')
    }
    if (allowPartyStage.value) {
      line.push(row.partyStage || '', row.stageOn || '')
    }
    if (allowEvalObserve.value) {
      line.push(row.observeOn || '', row.observeNote || '')
    }
    if (allowScheduleImpact.value) {
      line.push(row.scheduleImpactNote || '')
    }
    if (allowContractAmount.value) {
      line.push(row.contractAmount ?? '')
    }
    if (allowExpenseLines.value) {
      line.push(formatExpenseLines(row.expenseLines))
    }
    if (allowTripLegs.value) {
      line.push(formatTripLegs(row.tripLegs))
    }
    if (allowProjChangeLog.value) {
      line.push(row.changeLogNote || '')
    }
    if (allowCertVerify.value) {
      line.push(row.verifyCode || '')
    }
    if (allowVisitWalkIn.value) {
      line.push(row.walkIn ? '是' : '')
    }
    if (allowCheckinProxy.value) {
      line.push(row.checkinProxyBy || '')
    }
    if (allowClubRoster.value) {
      line.push(formatClubMembers(row.clubMembers))
    }
    if (allowCarpassParkingMutex.value) {
      line.push(row.parkingOn || '')
    }
    if (allowContractRenew.value) {
      line.push(row.renewOn || '', row.renewNote || '')
    }
    if (allowCertPickupRedeem.value) {
      line.push(row.pickupRedeemCode || '', row.pickupRedeemed ? '是' : '否')
    }
    if (allowProcureReturn.value) {
      line.push(row.returnFail ? '是' : '否', row.returnNote || '')
    }
    if (allowMoralObjection.value) {
      line.push(row.objectionNote || '')
    }
    if (issuePassCode.value && allowPassExpire.value) {
      line.push(row.passExpireAt || '')
    }
    line.push(
      person,
      row.assigneeUsername || '',
      statusLabel(row),
    )
    if (allowQty.value) line.push(row.qty ?? 1)
    if (pickLoanPeriod.value) line.push(row.dueAt || '')
    if (showFine.value) {
      line.push(Number(row.fineYuan) > 0 ? `¥${row.fineYuan} · ${row.fineStatus || ''}` : '')
    }
    if (showPickup.value) {
      line.push(row.pickupPlace || '', row.pickupAt || '')
      if (allowQty.value) line.push(row.actualQty ?? '')
    }
    if (showScheduleCols.value) line.push(row.startAt, row.endAt)
    line.push(remarkText(row.remark), row.attachUrl || '')
    if (exportAttachUrls.value) line.push(row.closeAttachUrl || '')
    if (showFollowCols.value) {
      line.push(row.contactChannel || '', row.nextFollowAt || '')
    }
    line.push(row.applyAt, row.approveAt)
    if (allowCheckin.value) line.push(row.checkedInAt || '')
    line.push(row.returnAt)
    if (allowRating.value) {
      line.push(row.rating || '', row.ratingRemark || '', row.ratedAt || '')
    }
    return line
  })
  const tag = ratedOnly.value ? 'rated' : (status.value || 'all')
  downloadCsv(`tickets_${tag}_${Date.now()}.csv`, headers, data)
  ElMessage.success(`已导出 ${rows.length} 条（UTF-8，可用 Excel 直接打开）`)
}

onMounted(() => {
  if (allowRating.value && String(route.query.rated || '') === '1') {
    ratedOnly.value = true
  }
  const st = String(route.query.status || '').trim()
  if (st && Object.prototype.hasOwnProperty.call(states.value, st)) {
    status.value = st
  }
  load()
})
</script>

<style scoped>
.toolbar { margin-bottom: 12px; display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
.board-hint { margin: 0 0 10px; color: #64748b; font-size: 13px; }
.pager { margin-top: 16px; display: flex; justify-content: flex-end; }
.rating { color: #b45309; font-weight: 600; }
.muted { color: var(--portal-muted, #94a3b8); }
.type-dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  margin-right: 6px;
  vertical-align: middle;
}
</style>
