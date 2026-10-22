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
      >{{ ratingFilterRatedLabel }}</el-checkbox>
      <span v-if="allowRating && ratingAdminLead" class="muted rating-lead">{{ ratingAdminLead }}</span>
      <el-checkbox
        v-if="todayBoardOn"
        v-model="todayOnly"
        style="margin-left:4px"
        @change="onFilter"
      >今日处理中</el-checkbox>
      <el-button type="primary" @click="load">查询</el-button>
      <el-button :disabled="!list.length" @click="exportCsv">{{ exportBtnLabel }}</el-button>
      <el-button
        v-if="mutualAdjustLogOn"
        plain
        @click="openAdjustLog"
      >{{ mutualAdjustLogTitle }}</el-button>
      <el-button
        v-if="mutualResultExportNotifyOn"
        plain
        @click="exportMutualResults"
      >{{ mutualResultExportLabel }}</el-button>
      <el-button
        v-if="mutualResultExportNotifyOn"
        type="success"
        plain
        :loading="mutualNotifyLoading"
        @click="notifyMutualResults"
      >{{ mutualResultNotifyLabel }}</el-button>
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
    <el-dialog v-model="adjustLogVisible" :title="mutualAdjustLogTitle" width="640px" destroy-on-close>
      <p class="muted" style="margin-bottom:8px">
        {{ labels.mutualAdjustLogLead || '查看管理端对志愿的调剂确认与驳回留痕。' }}
      </p>
      <p v-if="labels.mutualAdjustCapDeny" class="muted" style="margin-bottom:8px">
        {{ labels.mutualAdjustCapDeny }}
      </p>
      <p v-if="labels.onePerArchiveDenyMessage" class="muted" style="margin-bottom:8px">
        {{ labels.onePerArchiveDenyMessage }}
      </p>
      <p v-if="labels.mutualResultNotifyBody" class="muted" style="margin-bottom:8px">
        {{ labels.mutualResultNotifyBody }}
      </p>
      <el-table :data="adjustLogList" stripe size="small">
        <el-table-column prop="ticketId" label="单据" width="80" />
        <el-table-column prop="operator" label="操作人" width="100" />
        <el-table-column prop="remark" label="说明" min-width="160" show-overflow-tooltip />
        <el-table-column prop="createdAt" label="时间" width="160" />
      </el-table>
      <el-empty v-if="!adjustLogList.length" :description="labels.mutualAdjustLogEmpty || '暂无调剂记录'" />
      <div v-if="adjustLogTotal > 10" style="margin-top:12px;text-align:right">
        <el-pagination
          background
          layout="prev, pager, next"
          :total="adjustLogTotal"
          :page-size="10"
          :current-page="adjustLogPage"
          @current-change="(p) => { adjustLogPage = p; loadAdjustLog() }"
        />
      </div>
    </el-dialog>
  </div>
</template>

<script setup src="./TicketRecordsAdmin.setup.js"></script>

<style scoped src="./TicketRecordsAdmin.css"></style>
