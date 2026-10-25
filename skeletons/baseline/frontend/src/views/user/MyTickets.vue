<template>
  <div>
    <section class="hero">
      <div class="hero-row">
        <div>
          <h1>{{ plural }}</h1>
          <p>{{ pageLead }}</p>
          <p v-if="ticketNoHint" class="page-hint">{{ ticketNoHint }}</p>
          <p v-if="allowCheckinSpot && spotCheckToday" class="page-hint">{{ checkinSpotHint }}</p>
          <p v-if="slaPageHint" class="page-hint">{{ slaPageHint }}</p>
          <p v-if="mutualWishLockOn && mutualWishLockHint" class="page-hint">{{ mutualWishLockHint }}</p>
          <p v-if="mutualWishMutexHint" class="page-hint">{{ mutualWishMutexHint }}</p>
          <p v-if="mutualAdjustCapHint" class="page-hint">{{ mutualAdjustCapHint }}</p>
          <p v-if="mutualPeerTimeoutHint" class="page-hint">{{ mutualPeerTimeoutHint }}</p>
          <p v-if="carpoolCancelPenaltyOn && carpoolNoShowCountHint" class="page-hint">
            {{ carpoolNoShowCountLabel }}：{{ myNoShowCount }}
            <template v-if="carpoolNoShowCountHint"> · {{ carpoolNoShowCountHint }}</template>
          </p>
          <p v-if="carpoolSeatLockOn && carpoolSeatLockedHint" class="page-hint">{{ carpoolSeatLockedHint }}</p>
          <p v-if="creditFromActivityHint" class="page-hint">{{ creditFromActivityHint }}</p>
          <p v-if="creditWritebackHint && requireCreditWritebackAck" class="page-hint">{{ creditWritebackHint }}</p>
          <SchemaLabelHints :keys="myTicketHintKeys" />
          <p v-if="creditOn" class="page-hint">
            {{ creditScoreLabel }} {{ credit.score }} 分
            <template v-if="credit.overdueDelta"> · 每逾期一单扣 {{ credit.overdueDelta }} 分</template>
            <template v-if="creditBlocked"> · 低于 {{ credit.blockBelow }} 分暂不可再借</template>
          </p>
          <div v-if="rankSwitchOn" class="rank-switch">
            <span class="rank-lab">{{ rankSwitchHint || '排名范围' }}</span>
            <el-radio-group v-model="rankScope" size="small">
              <el-radio-button value="class">班级</el-radio-button>
              <el-radio-button value="major">专业</el-radio-button>
            </el-radio-group>
          </div>
        </div>
        <div class="tools">
          <el-select v-model="status" clearable placeholder="全部状态" style="width:140px" @change="load">
            <el-option v-for="(lab, key) in states" :key="key" :label="lab" :value="key" />
            <el-option v-if="staleFollowDays > 0" :label="stalePoolLabel" value="stale" />
          </el-select>
          <el-button v-if="!archiveMode || applyFromList" type="primary" @click="openApply()">{{ verbs.apply || '提交' }}</el-button>
          <el-button
            v-if="allowMakeupApply && (!archiveMode || applyFromList)"
            @click="openApply({ makeup: true })"
          >{{ makeupApplyLabel }}</el-button>
          <el-button v-else-if="archiveMode && !applyFromList" type="primary" @click="$router.push('/archive')">{{ browseCta }}</el-button>
          <el-button v-if="selfExportOn" :disabled="!list.length" @click="exportMineCsv">{{ selfExportLabel }}</el-button>
          <el-button v-if="creditOn" @click="openCredit">我的{{ creditScoreLabel }}</el-button>
          <el-button @click="load">刷新</el-button>
        </div>
        <p v-if="levelSlaText" class="sub">{{ levelSlaHint }}（{{ levelSlaText }}）</p>
        <p v-if="notifyDutyHint" class="sub">{{ notifyDutyHint }}</p>
        <p v-if="objectionWindowHint" class="sub">{{ objectionWindowHint }}</p>
      </div>
    </section>

    <div
      v-if="repairSurface === 'faultboard' && repairBoardStats"
      class="repair-board-bar"
      data-repair-board="stats"
    >
      <span class="board-stat" data-stat="pending">待派 {{ repairBoardStats.pending }}</span>
      <span class="board-stat" data-stat="progress">处理中 {{ repairBoardStats.progress }}</span>
      <span class="board-stat" data-stat="overdue">超时 {{ repairBoardStats.overdue }}</span>
    </div>

    <div
      class="list"
      :class="{
        'surface-ticketfeed': repairSurface === 'ticketfeed',
        'surface-faultboard': repairSurface === 'faultboard',
        'surface-typelist': approveSurface === 'typelist',
        'surface-inboxsteps': approveSurface === 'inboxsteps',
      }"
      :data-repair-surface="repairSurface || undefined"
      :data-approve-surface="approveSurface || undefined"
    >
      <article
        v-for="row in list"
        :key="row.id"
        class="card"
        :class="{ 'imm-overdue': row.status === 'overdue' }"
        :data-ticket-tone="(repairSurface || approveSurface) ? ticketTone(row.status) : undefined"
      >
        <div class="mark">{{ (row.title || '?').slice(0, 1) }}</div>
        <div class="meta">
          <p v-if="repairSurface === 'faultboard' && row.typeName" class="fault-cat">{{ row.typeName }}</p>
          <p
            v-else-if="repairSurface === 'ticketfeed' && (row.location || row.typeName)"
            class="ticket-chip"
          >{{ row.location || row.typeName }}</p>
          <p
            v-if="(approveSurface === 'typelist' || approveSurface === 'inboxsteps') && row.typeName"
            class="matter-type"
          >{{ row.typeName }}</p>
          <h3>{{ row.title || ('编号 ' + row.id) }}</h3>
          <p class="sub">
            编号 {{ row.id }} · {{ appliedAtLabel }} {{ row.applyAt }}
            <template v-if="allowQty && row.qty && row.qty > 1"> · 数量 {{ row.qty }}</template>
            <template v-if="showDueCols && row.dueAt"> · {{ dueLabel }} {{ row.dueAt }}</template>
            <template v-if="allowRenew && row.renewCount"> · 已续借 {{ row.renewCount }} 次</template>
            <template v-if="allowBookHold && row.holdExpireAt && (row.status === 'hold_ready' || row.status === 'held')">
              · 取书截止 {{ row.holdExpireAt }}
              <span
                v-if="holdCountdownText(row)"
                class="hold-cd"
                :class="{ 'cd-urgent': isUrgentCountdown(holdSecondsLeft(row), 3600) }"
              >（{{ holdCountdownText(row) }}）</span>
            </template>
            <template v-if="mutualDeadlineCountdownOn && row.applyDeadlineAt">
              · {{ applyDeadlineLabel }} {{ row.applyDeadlineAt }}
              <span
                v-if="mutualWishLockOn ? mutualWishLockText(row) : mutualDeadlineText(row)"
                class="hold-cd"
                :class="{ 'cd-urgent': isUrgentCountdown(mutualDeadlineSeconds(row), 3600) }"
              >（{{ mutualWishLockOn ? mutualWishLockText(row) : mutualDeadlineText(row) }}）</span>
            </template>
            <template
              v-if="row.typeName && repairSurface !== 'faultboard' && approveSurface !== 'typelist' && approveSurface !== 'inboxsteps' && !(repairSurface === 'ticketfeed' && !row.location)"
            > · {{ row.typeName }}</template>
            <template v-if="row.location && repairSurface !== 'ticketfeed'"> · {{ row.location }}</template>
            <template v-if="showPriorityCols && row.priority"> · {{ row.priority }}</template>
          </p>
          <p v-if="leaveSplitHint && leaveSplitText(row)" class="sub">{{ leaveSplitHint }}：{{ leaveSplitText(row) }}</p>
          <p v-if="row.startAt || row.endAt" class="sub sched">
            {{ row.periodStart || row.periodEnd ? '起止' : '时段' }}
            {{ row.startAt || '—' }} ~ {{ row.endAt || '—' }}
            <template v-if="row.leaveDays"> · {{ leaveDaysLabel }} {{ row.leaveDays }} 天</template>
            <template v-if="row.weekNo"> · {{ weekNoLabel }} {{ row.weekNo }}</template>
          </p>
          <p v-if="showPriorityCols && row.contactPhone" class="sub">电话 {{ row.contactPhone }}</p>
          <p v-if="row.interviewPlace" class="sub">{{ interviewPlaceLabel }}：{{ row.interviewPlace }}</p>
          <p v-if="row.rankScope" class="sub">排名范围：{{ row.rankScope === 'major' ? '专业' : '班级' }}</p>
          <div v-if="row.remark && showRemarkForRow(row)" class="tip">
            <template v-if="allowSignRemarkVisible && isApproveResultStatus(row.status)">{{ signApproveRemarkLabel }}：</template>
            <template v-else-if="row.status === 'rejected'">驳回原因：</template>
            <template v-else-if="richRemark">内容：</template>
            <template v-else-if="row.status === 'approved' || row.status === 'returned' || row.status === 'overdue'">说明：</template>
            <RichTextView v-if="richRemark" :html="row.remark" compact />
            <template v-else>{{ row.remark }}</template>
          </div>
          <div class="card-foot">
          <div class="card-meta">
            <StatusChip :tone="ticketTone(row.status)" compact />
            <el-tag size="small" :type="tagType(row.status)" effect="plain">{{ statusText(row) }}</el-tag>
            <ImmSteps
              v-if="multiApproveOn && isMultiApproveStatus(row.status)"
              :steps="multiApproveSteps(row.status)"
              aria-label="审批进度"
            />
            <template v-if="row.status === 'waitlisted'">
              <span v-if="row.waitlistRank || row.waitlistPos || row.queueNo" class="rated">
                候补第 {{ row.waitlistRank || row.waitlistPos || row.queueNo }} 位
              </span>
            </template>
            <el-tag
              v-if="teamExitNeedOwnerOn && Number(row.exitRequest) > 0 && row.status === 'approved'"
              size="small"
              type="warning"
              effect="plain"
            >{{ teamExitPendingLabel }}</el-tag>
            <el-tag
              v-if="carpoolSeatLockOn && Number(row.seatLocked) > 0 && row.status === 'approved'"
              size="small"
              type="success"
              effect="plain"
            >{{ carpoolSeatLockedLabel }}</el-tag>
          </div>
          <div class="card-acts">
            <el-button type="info" size="small" plain @click="openProgress(row)">进度</el-button>
        <el-button
          v-if="row.status === 'returned'"
          type="warning"
          size="small"
          plain
          :title="maxReviseHint"
          @click="resubmitTicket(row)"
        >重新提交</el-button>
            <el-button
              v-if="canEditWish(row)"
              type="primary"
              size="small"
              plain
              :title="mutualEditWishHint"
              @click="editWish(row)"
            >{{ mutualEditWishLabel }}</el-button>
            <el-button
              v-if="canRequestTeamExit(row)"
              type="warning"
              size="small"
              plain
              :title="teamExitRequestHint"
              @click="requestTeamExit(row)"
            >{{ teamExitRequestLabel }}</el-button>
            <el-button
              v-if="canWithdraw(row)"
              type="danger"
              size="small"
              plain
              :title="canCancelLockedSeat(row) ? carpoolCancelPenaltyHint : withdrawHint"
              @click="withdraw(row)"
            >{{ canCancelLockedSeat(row) ? carpoolCancelPenaltyLabel : '撤销' }}</el-button>
            <p
              v-if="carpoolCancelPenaltyOn && canCancelLockedSeat(row)"
              class="sub"
            >{{ carpoolCancelPenaltyHint }}</p>
            <p
              v-if="carpoolPhoneMaskAfterRateOn && row.ratedAt && carpoolPhoneMaskedHint"
              class="sub"
            >{{ carpoolPhoneMaskedHint }}</p>
            <el-button
              v-if="canMoralObjection(row)"
              type="warning"
              size="small"
              plain
              @click="openMoralObjection(row)"
            >{{ moralObjectionLabel }}</el-button>
            <el-button
              v-if="canSubmitProof(row)"
              type="warning"
              size="small"
              @click="openProof(row)"
            >提交凭证</el-button>
            <el-button
              v-if="canFinish(row)"
              type="primary"
              size="small"
              @click="finish(row)"
            >{{ finishVerb }}</el-button>
            <el-button
              v-if="canReportLost(row)"
              type="danger"
              size="small"
              plain
              @click="reportLost(row)"
            >{{ lostVerb }}</el-button>
            <el-button
              v-if="canRenew(row)"
              type="success"
              size="small"
              plain
              @click="renew(row)"
            >{{ renewVerb }}</el-button>
            <el-button
              v-if="canClaimHold(row)"
              type="success"
              size="small"
              @click="claimHold(row)"
            >{{ claimHoldVerb }}</el-button>
            <el-button
              v-if="canCheckin(row)"
              type="success"
              size="small"
              plain
              @click="openCheckin(row)"
            >签到</el-button>
            <span v-else-if="row.checkedInAt" class="rated">已签到 {{ row.checkedInAt }}</span>
            <el-button
              v-if="canRate(row)"
              type="warning"
              size="small"
              plain
              @click="openRate(row, false)"
            >{{ ratingLabel }}</el-button>
            <el-button
              v-else-if="canFollowRate(row)"
              type="warning"
              size="small"
              plain
              @click="openRate(row, true)"
            >追评</el-button>
            <span v-else-if="row.rating && !row.hideEvalResult" class="rated">
              已评 {{ row.rating }} 分
              <template v-if="row.followRated"> · 已追评</template>
            </span>
            <span v-else-if="row.hideEvalResult" class="rated">评分已提交</span>
            <p v-if="canRate(row) && rateInviteHint" class="sub">{{ rateInviteHint }}</p>
            <el-button
              v-if="canUrge(row)"
              type="danger"
              size="small"
              plain
              @click="doUrge(row)"
            >{{ urgeLabel }}</el-button>
            <el-button
              v-if="canCancelUrge(row)"
              size="small"
              plain
              @click="doCancelUrge(row)"
            >{{ cancelUrgeLabel }}</el-button>
            <el-button
              v-if="canCancelDispatched(row)"
              type="danger"
              size="small"
              plain
              @click="doCancelDispatched(row)"
            >取消报修</el-button>
            <el-button
              v-if="canConfirmQuote(row)"
              type="success"
              size="small"
              plain
              @click="doConfirmQuote(row)"
            >确认报价</el-button>
            <el-button
              v-if="printTicketOn"
              size="small"
              plain
              @click="printTicket(row)"
            >{{ printTicketLabel }}</el-button>
            <span v-if="printTicketOn && formPrintHint" class="sub" style="margin-left:4px">{{ formPrintHint }}</span>
            <el-button
              v-if="canShowWallet(row)"
              size="small"
              plain
              @click="openWallet(row)"
            >{{ ticketWalletLabel }}</el-button>
            <el-button
              v-if="canTransfer(row)"
              size="small"
              plain
              @click="openTransfer(row)"
            >{{ ticketTransferLabel }}</el-button>
            <el-button
              v-if="canShowPostGallery(row)"
              size="small"
              plain
              @click="openPostGallery(row)"
            >{{ postGalleryLabel }}</el-button>
            <el-button
              v-if="canAckCreditWriteback(row)"
              size="small"
              plain
              @click="ackCreditWriteback(row)"
            >{{ creditWritebackAckLabel }}</el-button>
            <el-button
              v-if="canOpenActivitySurvey(row)"
              size="small"
              plain
              @click="openActivitySurvey(row)"
            >{{ activitySurveyLinkLabel }}</el-button>
          </div>
          </div>
          <p v-if="row.creditWritebackAck && creditWritebackHint" class="sub">{{ creditWritebackHint }}</p>
          <p v-if="postGalleryUrls(row).length" class="sub">相册 {{ postGalleryUrls(row).length }} 张</p>
          <p v-if="row.preferredSlot" class="sub">期望上门 {{ row.preferredSlot }}</p>
          <p v-if="row.responseDueAt" class="sub">响应时限 {{ row.responseDueAt }}</p>
          <p v-if="row.urgeCount" class="sub">
            已催办 {{ row.urgeCount }} 次
            <template v-if="row.urgeCancelled"> · 已撤催</template>
          </p>
          <p v-if="row.quoteYuan != null" class="sub">
            报价 ¥{{ row.quoteYuan }}
            <template v-if="row.quoteConfirmed"> · 已确认</template>
          </p>
          <p
            v-if="pickupPending(row)"
            class="sub pickup-tip"
          >已出库待领取：请查看站内消息中的领取地点，到场后由工作人员登记实发。</p>
          <p v-if="showPickup && row.pickupAt" class="sub">
            已领取 {{ row.pickupPlace || '' }}
            <template v-if="allowQty && row.actualQty != null"> · 实发 {{ row.actualQty }}</template>
            · {{ row.pickupAt }}
          </p>
          <p v-if="showFineCols && row.fineYuan > 0" class="sub">
            {{ fineLabel }} ¥{{ row.fineYuan }}
            <template v-if="row.fineStatus"> · {{ row.fineStatus === 'paid' ? '已结清' : row.fineStatus }}</template>
          </p>
          <p v-if="row.meetIntent" class="sub">{{ meetIntentLabel }} {{ row.meetIntent }}</p>
          <p v-if="row.contactChannel || row.nextFollowAt" class="sub">
            <template v-if="row.contactChannel">{{ channelLabel }} {{ row.contactChannel }}</template>
            <template v-if="row.nextFollowAt"> · {{ nextAtLabel }} {{ row.nextFollowAt }}</template>
          </p>
          <p v-if="row.passCode" class="sub pass-code">
            {{ passCodeLabel }} <strong>{{ row.passCode }}</strong>
            <template v-if="allowPassExpire && row.passExpireAt"> · {{ passExpireAtLabel }} {{ row.passExpireAt }}</template>
            <span v-if="allowPassExpire && isPassExpired(row)" class="muted"> {{ passExpiredLabel }}</span>
            <el-button v-if="!isPassExpired(row)" link type="primary" size="small" @click="copyPass(row.passCode)">复制</el-button>
            <span v-if="!isPassExpired(row)" class="muted">到访时出示即可</span>
            <CodeQrBlock v-if="codeQrOn && !isPassExpired(row)" :code="row.passCode" :label="passCodeLabel" />
            <el-button
              v-if="allowVisitorPassPrint && row.passCode && !isPassExpired(row)"
              link
              type="primary"
              size="small"
              @click="printVisitorPass(row)"
            >{{ visitorPassPrintLabel }}</el-button>
          </p>
          <p v-if="row.attachUrl" class="sub">
            附件 <a :href="row.attachUrl" target="_blank" rel="noopener noreferrer">查看</a>
          </p>
          <p v-if="row.approveAttachUrl" class="sub">
            {{ approveRemarkAttachLabel }}
            <a :href="row.approveAttachUrl" target="_blank" rel="noopener noreferrer">查看</a>
          </p>
          <p v-if="allowCertPickup && row.pickupMethod" class="sub">
            {{ certPickupLabel }} {{ row.pickupMethod }}
            <template v-if="row.mailAddress"> · {{ row.mailAddress }}</template>
            <template v-if="row.expressNo"> · {{ expressNoLabel }} {{ row.expressNo }}</template>
            <template v-if="row.certUrgent"> · {{ certUrgentLabel }}</template>
          </p>
          <p v-if="allowSealCopies && row.sealCopies != null" class="sub">
            {{ sealCopiesLabel }} {{ row.sealCopies }}
            <template v-if="row.bindNote"> · {{ row.bindNote }}</template>
            <template v-if="row.sealCopyNos"> · {{ sealCopyNosLabel }} {{ row.sealCopyNos }}</template>
            <template v-if="row.sealWitnessAck"> · {{ sealWitnessAckLabel }}</template>
          </p>
          <p v-if="allowExpenseInvoice && (row.invoiceCount != null || row.fineYuan > 0)" class="sub">
            <template v-if="row.invoiceCount != null">{{ invoiceCountLabel }} {{ row.invoiceCount }}</template>
            <template v-if="row.fineYuan > 0"> · {{ expenseAmountLabel }} ¥{{ row.fineYuan }}</template>
          </p>
          <p v-if="allowVisitorCount && row.visitorCount != null" class="sub">
            {{ visitorCountLabel }} {{ row.visitorCount }}
            <template v-if="row.companionNames"> · {{ companionNamesLabel }} {{ row.companionNames }}</template>
          </p>
          <p v-if="allowAwardCertNo && row.awardCertNo" class="sub">
            {{ awardCertNoLabel }} {{ row.awardCertNo }}
          </p>
          <p v-if="allowVendorQuotes && row.vendorQuotes" class="sub">
            {{ vendorQuotesLabel }} {{ row.vendorQuotes }}
          </p>
          <p v-if="allowFleetMileage && row.mileageKm != null" class="sub">
            {{ mileageLabel }} {{ row.mileageKm }}
            <template v-if="row.fuelNote"> · {{ row.fuelNote }}</template>
          </p>
          <p v-if="allowFleetCrew && (row.driverName || row.passengerNames)" class="sub">
            <template v-if="row.driverName">{{ driverNameLabel }} {{ row.driverName }}</template>
            <template v-if="row.passengerNames"> · {{ passengerNamesLabel }} {{ row.passengerNames }}</template>
          </p>
          <p v-if="allowCompHours && row.compHours != null" class="sub">
            {{ compHoursLabel }} {{ row.compHours }}
          </p>
          <p v-if="allowReturnFuel && row.returnFuel != null" class="sub">
            {{ returnFuelLabel }} {{ row.returnFuel }}
          </p>
          <p v-if="allowLaborPlace && row.laborPlace" class="sub">
            {{ laborPlaceLabel }} {{ row.laborPlace }}
          </p>
          <p v-if="allowEffectiveOn && row.effectiveOn" class="sub">
            {{ effectiveOnLabel }} {{ row.effectiveOn }}
          </p>
          <p v-if="allowCertIssueNo && row.certIssueNo" class="sub">
            {{ certIssueNoLabel }} {{ row.certIssueNo }}
            <span v-if="certIssueNoHint" class="muted"> · {{ certIssueNoHint }}</span>
          </p>
          <p v-if="allowDocRev && row.docRev" class="sub">
            {{ docRevLabel }} {{ row.docRev }}
          </p>
          <p v-if="allowFitoutQuiet && (row.workStart || row.workEnd)" class="sub">
            {{ fitoutWindowLabel }} {{ row.workStart || '—' }}–{{ row.workEnd || '—' }}
          </p>
          <p v-if="allowIssueCopies && row.issueCopies != null" class="sub">
            {{ issueCopiesLabel }} {{ row.issueCopies }}
          </p>
          <p v-if="allowSignParties && row.signParties" class="sub">
            {{ signPartiesLabel }} {{ row.signParties }}
          </p>
          <p v-if="allowTrainHours && row.trainHours != null" class="sub">
            {{ trainHoursLabel }} {{ row.trainHours }}
          </p>
          <p v-if="allowMemberChange && row.memberChangeNote" class="sub">
            {{ memberChangeNoteLabel }} {{ row.memberChangeNote }}
          </p>
          <p v-if="allowProcureBudget && row.procureAmount != null" class="sub">
            {{ procureAmountLabel }} {{ row.procureAmount }}
          </p>
          <p v-if="allowCheckinException && row.exceptionType" class="sub">
            {{ exceptionTypeLabel }} {{ row.exceptionType }}
          </p>
          <p v-if="allowVisitPurpose && row.visitPurpose" class="sub">
            {{ visitPurposeLabel }} {{ row.visitPurpose }}
          </p>
          <p v-if="allowFitoutRectify && row.rectifyNote" class="sub">{{ rectifyNoteLabel }} {{ row.rectifyNote }}</p>
          <p v-if="allowProjFundUse && (row.fundUseYuan != null || row.fundUseNote)" class="sub">
            <template v-if="row.fundUseYuan != null">{{ fundUseYuanLabel }} {{ row.fundUseYuan }}</template>
            <template v-if="row.fundUseNote"> · {{ row.fundUseNote }}</template>
          </p>
          <p v-if="allowVisitSlotRemain && row.visitOn" class="sub">{{ visitOnLabel }} {{ row.visitOn }}</p>
          <p v-if="allowPlagiarismUrl && row.plagiarismUrl" class="sub">
            {{ plagiarismUrlLabel }}
            <a :href="row.plagiarismUrl" target="_blank" rel="noopener">{{ row.plagiarismUrl }}</a>
          </p>
          <p v-if="allowPartyStage && (row.partyStage || row.stageOn)" class="sub">
            <template v-if="row.partyStage">{{ partyStageLabel }} {{ row.partyStage }}</template>
            <template v-if="row.stageOn"> · {{ stageOnLabel }} {{ row.stageOn }}</template>
          </p>
          <p v-if="allowEvalObserve && (row.observeOn || row.observeNote)" class="sub">
            <template v-if="row.observeOn">{{ observeOnLabel }} {{ row.observeOn }}</template>
            <template v-if="row.observeNote"> · {{ row.observeNote }}</template>
          </p>
          <p v-if="allowScheduleImpact && row.scheduleImpactNote" class="sub">
            {{ scheduleImpactNoteLabel }} {{ row.scheduleImpactNote }}
          </p>
          <p v-if="allowContractAmount && row.contractAmount != null" class="sub">
            {{ contractAmountLabel }} {{ row.contractAmount }}
            <template v-if="amountToChinese(row.contractAmount)">
              · {{ contractAmountCnLabel }} {{ amountToChinese(row.contractAmount) }}
            </template>
          </p>
          <p v-if="allowExpenseLines && row.expenseLines && row.expenseLines.length" class="sub">
            {{ expenseLinesLabel }} {{ formatExpenseLines(row.expenseLines) }}
          </p>
          <p v-if="allowTripLegs && row.tripLegs && row.tripLegs.length" class="sub">
            {{ tripLegsLabel }} {{ formatTripLegs(row.tripLegs) }}
          </p>
          <p v-if="allowProjChangeLog && row.changeLogNote" class="sub">
            {{ changeLogNoteLabel }} {{ row.changeLogNote }}
          </p>
          <p v-if="allowCertVerify && row.verifyCode" class="sub">
            {{ certVerifyCodeLabel }} {{ row.verifyCode }}
            · <router-link to="/cert-verify">真伪查询</router-link>
          </p>
          <p v-if="allowVisitWalkIn && row.walkIn" class="sub">{{ visitWalkInLabel }}</p>
          <p v-if="allowCheckinProxy && row.checkinProxyBy" class="sub">
            {{ checkinProxyByLabel }} {{ row.checkinProxyBy }}
          </p>
          <p v-if="allowClubRoster && row.clubMembers && row.clubMembers.length" class="sub">
            {{ clubRosterLabel }} {{ formatClubMembers(row.clubMembers) }}
          </p>
          <p v-if="allowCarpassParkingMutex && row.parkingOn" class="sub">
            {{ parkingOnLabel }} {{ row.parkingOn }}
          </p>
          <p v-if="allowContractRenew && (row.renewOn || row.renewNote)" class="sub">
            {{ renewOnLabel }} {{ row.renewOn || '—' }}
            <template v-if="row.renewNote"> · {{ renewNoteLabel }} {{ row.renewNote }}</template>
          </p>
          <p v-if="allowCertPickupRedeem && row.pickupRedeemCode" class="sub">
            {{ pickupRedeemCodeLabel }} {{ row.pickupRedeemCode }}
            <template v-if="row.pickupRedeemed"> · {{ pickupRedeemedLabel }}</template>
            <CodeQrBlock
              v-if="allowCertPickupQr && !row.pickupRedeemed"
              :code="row.pickupRedeemCode"
              :label="pickupQrLabel"
            />
          </p>
          <p v-if="allowAttachKeepOld && attachKeepOldHint" class="sub">{{ attachKeepOldHint }}</p>
          <el-button
            v-if="allowAttachKeepOld && row.attachUrl"
            size="small"
            plain
            @click="openAttachRevs(row)"
          >{{ attachKeepOldLabel }}</el-button>
          <p v-if="allowProcureReturn && (row.returnFail || row.returnNote)" class="sub">
            {{ procureReturnFailLabel }} {{ row.returnFail ? '是' : '否' }}
            <template v-if="row.returnNote"> · {{ returnNoteLabel }} {{ row.returnNote }}</template>
          </p>
          <p v-if="allowMoralObjection && row.objectionNote" class="sub">{{ moralObjectionLabel }} {{ row.objectionNote }}</p>
          <p v-if="allowFleetViolation && row.violationPerson" class="sub">
            {{ violationPersonLabel }} {{ row.violationPerson }}
          </p>
          <el-button
            v-if="canCcComment(row)"
            size="small"
            plain
            @click="openCcComment(row)"
          >{{ approveCcCommentLabel }}</el-button>
        </div>
      </article>
    </div>

    <div v-if="!list.length" class="empty">
      {{ emptyText }}
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

    <el-dialog v-model="returnDlg.visible" :title="finishVerb" width="480px">
      <p class="sub" v-if="requireReturnAttach && !requireFaultReason">
        {{ labels.returnAttachHint || '归还时请上传设备外观/配件照片，便于验收。' }}
      </p>
      <p class="sub" v-else-if="requireFaultReason || requireCloseSummary">
        办结前请补全处理信息；上传维修后照片便于对照。
      </p>
      <el-form label-position="top">
        <el-form-item v-if="requireFaultReason" :label="faultReasonLabel" required>
          <el-select v-model="returnDlg.faultReason" filterable clearable placeholder="请选择原因" style="width:100%">
            <el-option v-for="opt in faultReasons" :key="opt" :label="opt" :value="opt" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="requireCloseSummary" :label="closeSummaryLabel" required>
          <el-input v-model="returnDlg.closeSummary" type="textarea" :rows="3" maxlength="512" />
        </el-form-item>
        <el-form-item v-if="allowPartsNote" :label="partsNoteLabel">
          <el-input v-model="returnDlg.partsNote" maxlength="255" :placeholder="partsWarnHint" />
        </el-form-item>
        <el-form-item v-if="allowFleetMileage" :label="mileageLabel" required>
          <el-input-number v-model="returnDlg.mileageKm" :min="0.1" :max="999999" :precision="1" />
        </el-form-item>
        <el-form-item v-if="allowFleetMileage" :label="fuelNoteLabel" required>
          <el-input v-model="returnDlg.fuelNote" maxlength="255" :placeholder="fleetMileageHint || `请填写${fuelNoteLabel}`" />
        </el-form-item>
        <el-form-item v-if="allowCompHours" :label="compHoursLabel" required>
          <el-input-number v-model="returnDlg.compHours" :min="0.1" :max="9999" :precision="1" />
        </el-form-item>
        <p v-if="allowCompHours && compHoursHint" class="sub">{{ compHoursHint }}</p>
        <el-form-item v-if="allowReturnFuel" :label="returnFuelLabel" required>
          <el-input-number v-model="returnDlg.returnFuel" :min="0" :max="100" :precision="1" />
        </el-form-item>
        <p v-if="allowReturnFuel && returnFuelHint" class="sub">{{ returnFuelHint }}</p>
        <el-form-item v-if="allowFleetViolation" :label="violationPersonLabel" required>
          <el-input v-model="returnDlg.violationPerson" maxlength="64" :placeholder="violationPersonHint || `请填写${violationPersonLabel}`" />
        </el-form-item>
        <p v-if="allowFleetViolation && violationPersonHint" class="sub">{{ violationPersonHint }}</p>
        <el-form-item v-if="allowProcureReturn" :label="procureReturnFailLabel">
          <el-switch v-model="returnDlg.returnFail" />
        </el-form-item>
        <el-form-item v-if="allowProcureReturn && returnDlg.returnFail" :label="returnNoteLabel" required>
          <el-input
            v-model="returnDlg.returnNote"
            type="textarea"
            :rows="3"
            maxlength="512"
            show-word-limit
            :placeholder="procureReturnHint || `请填写${returnNoteLabel}`"
          />
        </el-form-item>
        <p v-if="allowProcureReturn && procureReturnHint" class="sub">{{ procureReturnHint }}</p>
        <p v-if="requireCloseAttach && closeAttachHint" class="sub">{{ closeAttachHint }}</p>
        <el-form-item v-if="requireReturnAttach || requireCloseAttach" :label="finishAttachFieldLabel" :required="requireReturnAttach || requireCloseAttach">
          <div class="attach-row">
            <el-upload :show-file-list="false" accept="image/*" :http-request="onReturnUpload">
              <el-button size="small">{{ returnDlg.attachUrl ? '重新上传' : '上传照片' }}</el-button>
            </el-upload>
            <a v-if="returnDlg.attachUrl" :href="returnDlg.attachUrl" target="_blank" rel="noopener noreferrer">已上传</a>
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="returnDlg.visible = false">取消</el-button>
        <el-button type="primary" :loading="returnDlg.loading" @click="confirmReturn">确认</el-button>
      </template>
    </el-dialog>
    <el-dialog v-model="objectionDlg.visible" :title="moralObjectionLabel" width="420px">
      <p v-if="moralObjectionHint" class="sub">{{ moralObjectionHint }}</p>
      <el-input
        v-model="objectionDlg.note"
        type="textarea"
        :rows="4"
        maxlength="512"
        show-word-limit
        :placeholder="`请填写${moralObjectionLabel}`"
      />
      <template #footer>
        <el-button @click="objectionDlg.visible = false">取消</el-button>
        <el-button type="primary" :loading="objectionDlg.loading" @click="submitMoralObjection">提交</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="visible" :title="applyDialogTitle" width="520px">
      <p v-if="makeupApplyHint && makeupMode" class="page-hint">{{ makeupApplyHint }}</p>
      <p v-if="sickAttachHint && attachByLeaveTypeOn" class="page-hint">{{ sickAttachHint }}</p>
      <el-form :model="form" label-position="top" require-asterisk-position="right">
        <template v-if="applyFromList">
          <!-- 驿站取件：取件码优先，档案下拉仅作兜底 -->
          <template v-if="requireClaimCode">
            <el-form-item :label="remarkLabel" :required="requireRemark">
              <el-input
                v-model="form.remark"
                maxlength="64"
                :placeholder="`请填写${remarkLabel}`"
                @blur="matchClaimFromRemark"
                @input="onClaimRemarkInput"
              />
            </el-form-item>
            <p v-if="claimMatchedLine" class="sub claim-match">已匹配：{{ claimMatchedLine }}</p>
            <el-form-item :label="archiveLabel" required>
              <el-select
                v-model="form.itemId"
                filterable
                clearable
                :placeholder="claimFilteredArchiveItems.length ? (normRoomToken(form.remark) ? '已匹配待取件，可改选' : '本人待取件，可改选') : '请先填写取件码或确认资料手机号'"
                style="width:100%"
              >
                <el-option
                  v-for="it in claimFilteredArchiveItems"
                  :key="it.id"
                  :label="claimOptionLabel(it)"
                  :value="it.id"
                />
              </el-select>
            </el-form-item>
          </template>
          <template v-else>
            <el-form-item :label="archiveLabel" required>
              <el-select v-model="form.itemId" filterable :placeholder="archiveSelectPlaceholder" style="width:100%">
                <el-option
                  v-for="it in archiveItems"
                  :key="it.id"
                  :label="it.author ? `${it.title}（${it.author}）` : it.title"
                  :value="it.id"
                />
              </el-select>
            </el-form-item>
            <el-form-item :label="remarkLabel" :required="requireRemark">
              <el-select
                v-if="remarkOptions.length"
                v-model="form.remark"
                filterable
                clearable
                :placeholder="`请选择${remarkLabel}`"
                style="width:100%"
              >
                <el-option v-for="opt in remarkOptions" :key="opt" :label="opt" :value="opt" />
              </el-select>
              <el-input
                v-else
                v-model="form.remark"
                type="textarea"
                :rows="3"
                maxlength="400"
                :placeholder="`请填写${remarkLabel}`"
              />
            </el-form-item>
          </template>
          <el-form-item v-if="allowProxyPickup" :label="proxyNameLabel">
            <el-input v-model="form.proxyName" maxlength="64" :placeholder="`选填${proxyNameLabel}`" />
          </el-form-item>
          <el-form-item v-if="allowProxyPickup" :label="proxyPhoneLabel">
            <el-input v-model="form.proxyPhone" maxlength="20" :placeholder="`选填${proxyPhoneLabel}`" />
          </el-form-item>
          <el-form-item v-if="allowDeposit" :label="depositLabel">
            <el-input-number v-model="form.depositYuan" :min="0" :max="999999" :precision="2" />
          </el-form-item>
          <el-form-item v-if="requireApplyInvite" :label="applyInviteLabel" required>
            <el-input v-model="form.inviteCode" maxlength="64" :placeholder="applyInviteHint || `请填写${applyInviteLabel}`" />
          </el-form-item>
          <el-form-item v-if="requireNoticeAck">
            <el-checkbox v-model="form.noticeAck">{{ noticeAckLabel }}</el-checkbox>
          </el-form-item>
          <el-form-item v-if="requireTrainingAck">
            <el-checkbox v-model="form.trainingAck">我已完成相关培训</el-checkbox>
          </el-form-item>
          <el-form-item v-if="requireInsuranceAck">
            <el-checkbox v-model="form.insuranceAck">{{ insuranceAckLabel }}</el-checkbox>
          </el-form-item>
          <el-form-item v-if="requireMeetingAck">
            <el-checkbox v-model="form.meetingAck">{{ meetingAckLabel }}</el-checkbox>
          </el-form-item>
          <div
            v-if="applyItemNotes.sponsor || applyItemNotes.price || applyItemNotes.room || applyItemNotes.planUrl || applyItemNotes.weather"
            class="sub"
          >
            <p v-if="applyItemNotes.sponsor">赞助：{{ applyItemNotes.sponsor }}</p>
            <p v-if="applyItemNotes.price">票价说明：{{ applyItemNotes.price }}</p>
            <p v-if="applyItemNotes.room">单房差：{{ applyItemNotes.room }}</p>
            <p v-if="applyItemNotes.planUrl">
              <a :href="applyItemNotes.planUrl" target="_blank" rel="noopener noreferrer">打开培养方案</a>
            </p>
            <p v-if="applyItemNotes.weather">出团须知：{{ applyItemNotes.weather }}</p>
          </div>
          <el-form-item v-if="needPriceNoteAck">
            <el-checkbox v-model="form.priceNoteAck">{{ priceNoteAckLabel }}</el-checkbox>
          </el-form-item>
          <el-form-item v-if="needSponsorAck">
            <el-checkbox v-model="form.sponsorAck">{{ sponsorAckLabel }}</el-checkbox>
          </el-form-item>
          <el-form-item v-if="needPlanAck">
            <el-checkbox v-model="form.planAck">{{ planAckLabel }}</el-checkbox>
          </el-form-item>
          <el-form-item v-if="needPrereqAck">
            <el-checkbox v-model="form.prereqAck">{{ prereqAckLabel }}</el-checkbox>
          </el-form-item>
          <el-form-item v-if="needTourNoticeAck">
            <el-checkbox v-model="form.tourNoticeAck">{{ tourNoticeAckLabel }}</el-checkbox>
          </el-form-item>
          <el-form-item v-if="allowWishOrder" :label="wishOrderLabel" required>
            <el-select v-model="form.wishOrder" style="width:100%" :placeholder="wishOrderHint || '请选择志愿序'">
              <el-option :value="1" label="第一志愿" />
              <el-option :value="2" label="第二志愿" />
            </el-select>
          </el-form-item>
          <el-form-item v-if="allowVolunteerRole" :label="volunteerRoleLabel">
            <el-select v-model="form.volunteerRole" clearable style="width:100%" :placeholder="volunteerRoleHint || '选填岗位'">
              <el-option v-for="opt in volunteerRoleOptions" :key="opt" :label="opt" :value="opt" />
            </el-select>
          </el-form-item>
          <el-form-item v-if="allowCompanions || showVisitorCompanions" :label="companionNamesLabel" :required="showVisitorCompanions">
            <el-input
              v-model="form.companionNames"
              type="textarea"
              :rows="2"
              maxlength="255"
              :placeholder="companionNamesHint || (showVisitorCompanions ? '有随行须填写姓名，逗号分隔' : '选填同行人，逗号分隔')"
            />
          </el-form-item>
          <p v-if="(allowCompanions || showVisitorCompanions) && companionNamesHint" class="sub">{{ companionNamesHint }}</p>
          <el-form-item v-if="allowCertPickup" :label="certPickupLabel" required>
            <el-select v-model="form.pickupMethod" style="width:100%" :placeholder="certPickupHint || '请选择领取方式'">
              <el-option label="自取" value="自取" />
              <el-option label="邮寄" value="邮寄" />
            </el-select>
          </el-form-item>
          <el-form-item v-if="allowCertPickup && form.pickupMethod === '邮寄'" :label="mailAddressLabel" required>
            <el-input v-model="form.mailAddress" maxlength="255" :placeholder="`请填写${mailAddressLabel}`" />
          </el-form-item>
          <p v-if="allowCertPickup && certPickupHint" class="sub">{{ certPickupHint }}</p>
          <el-form-item v-if="allowCertUrgent">
            <el-switch v-model="form.certUrgent" :active-text="certUrgentLabel" />
          </el-form-item>
          <p v-if="allowCertUrgent && certUrgentHint" class="sub">{{ certUrgentHint }}</p>
          <el-form-item v-if="allowSealCopies" :label="sealCopiesLabel" required>
            <el-input-number v-model="form.sealCopies" :min="1" :max="999" />
          </el-form-item>
          <el-form-item v-if="allowSealCopies" :label="bindNoteLabel">
            <el-input v-model="form.bindNote" maxlength="255" :placeholder="sealCopiesHint || `选填${bindNoteLabel}`" />
          </el-form-item>
          <el-form-item v-if="allowExpenseInvoice" :label="invoiceCountLabel" required>
            <el-input-number v-model="form.invoiceCount" :min="1" :max="999" />
          </el-form-item>
          <el-form-item v-if="allowExpenseInvoice" :label="expenseAmountLabel" required>
            <el-input-number v-model="form.fineYuan" :min="0.01" :max="99999999" :precision="2" />
          </el-form-item>
          <p v-if="allowExpenseInvoice && expenseInvoiceHint" class="sub">{{ expenseInvoiceHint }}</p>
          <p v-if="allowExpenseAttachCount && expenseAttachCountHint" class="sub">{{ expenseAttachCountHint }}</p>
          <template v-if="allowExpenseLines">
            <el-form-item :label="expenseLinesLabel" required>
              <div v-for="(line, idx) in form.expenseLines" :key="idx" class="line-row">
                <el-select v-model="line.category" :placeholder="expenseLineCategoryLabel" style="width:120px">
                  <el-option v-for="opt in expenseLineCategoryOptions" :key="opt" :label="opt" :value="opt" />
                </el-select>
                <el-input-number v-model="line.amount" :min="0.01" :max="99999999" :precision="2" :step="10" :placeholder="expenseLineAmountLabel" />
                <el-input v-model="line.note" maxlength="128" :placeholder="expenseLineNoteLabel" style="flex:1" />
                <el-button v-if="form.expenseLines.length > 1" link type="danger" @click="form.expenseLines.splice(idx, 1)">删</el-button>
              </div>
              <el-button type="primary" plain size="small" @click="form.expenseLines.push({ category: '', amount: null, note: '' })">加一行</el-button>
            </el-form-item>
            <p v-if="expenseLinesHint" class="sub">{{ expenseLinesHint }}</p>
          </template>
          <template v-if="allowTripLegs">
            <el-form-item :label="tripLegsLabel" required>
              <div v-for="(leg, idx) in form.tripLegs" :key="idx" class="line-row">
                <el-input v-model="leg.from" maxlength="64" :placeholder="tripLegFromLabel" style="width:110px" />
                <el-input v-model="leg.via" maxlength="64" :placeholder="tripLegViaLabel" style="width:110px" />
                <el-input v-model="leg.to" maxlength="64" :placeholder="tripLegToLabel" style="width:110px" />
                <el-date-picker v-model="leg.on" type="date" value-format="YYYY-MM-DD" :placeholder="tripLegOnLabel" style="width:140px" />
                <el-button v-if="form.tripLegs.length > 1" link type="danger" @click="form.tripLegs.splice(idx, 1)">删</el-button>
              </div>
              <el-button type="primary" plain size="small" @click="form.tripLegs.push({ from: '', via: '', to: '', on: '' })">加一段</el-button>
            </el-form-item>
            <p v-if="tripLegsHint" class="sub">{{ tripLegsHint }}</p>
          </template>
          <template v-if="allowClubRoster">
            <el-form-item :label="clubRosterLabel" required>
              <div v-for="(mem, idx) in form.clubMembers" :key="idx" class="line-row">
                <el-input v-model="mem.name" maxlength="64" :placeholder="clubMemberNameLabel" style="width:140px" />
                <el-input v-model="mem.studentNo" maxlength="32" :placeholder="clubMemberNoLabel" style="flex:1" />
                <el-button v-if="form.clubMembers.length > 1" link type="danger" @click="form.clubMembers.splice(idx, 1)">删</el-button>
              </div>
              <el-button type="primary" plain size="small" @click="form.clubMembers.push({ name: '', studentNo: '' })">加一行</el-button>
              <el-input
                v-model="form.clubRosterCsv"
                type="textarea"
                :rows="2"
                maxlength="4000"
                :placeholder="'也可粘贴表格：每行「姓名,学号」'"
                style="margin-top:8px"
                @change="importClubRosterCsv"
              />
            </el-form-item>
            <p v-if="clubRosterHint" class="sub">{{ clubRosterHint }}</p>
          </template>
          <el-form-item v-if="allowCarpassParkingMutex" :label="parkingOnLabel" required>
            <el-date-picker
              v-model="form.parkingOn"
              type="date"
              value-format="YYYY-MM-DD"
              placeholder="请选择"
              style="width:100%"
            />
          </el-form-item>
          <p v-if="allowCarpassParkingMutex && carpassParkingMutexHint" class="sub">
            {{ parkingMutexLabel }}：{{ carpassParkingMutexHint }}
          </p>
          <el-form-item v-if="allowContractRenew" :label="renewOnLabel" required>
            <el-date-picker
              v-model="form.renewOn"
              type="date"
              value-format="YYYY-MM-DD"
              placeholder="请选择"
              style="width:100%"
            />
          </el-form-item>
          <el-form-item v-if="allowContractRenew" :label="renewNoteLabel" required>
            <el-input
              v-model="form.renewNote"
              type="textarea"
              :rows="3"
              maxlength="512"
              show-word-limit
              :placeholder="contractRenewHint || `请填写${renewNoteLabel}`"
            />
          </el-form-item>
          <p v-if="allowContractRenew && contractRenewHint" class="sub">{{ contractRenewHint }}</p>
          <p v-if="allowContractExpireRemind && contractExpireRemindHint" class="sub">
            {{ contractExpireRemindTitle }}：{{ contractExpireRemindHint }}
          </p>
          <p v-if="allowExamPassMin && examPassMinHint" class="sub">
            {{ examPassMinLabel }}：{{ examPassMinHint }}
          </p>
          <p v-if="allowEvalBeforeGrade && evalBeforeGradeHint" class="sub">{{ evalBeforeGradeHint }}</p>
          <p v-if="allowCheckinSpot && checkinSpotHint" class="sub">{{ checkinSpotHint }}</p>
          <p v-if="allowCertPickupRedeem && pickupRedeemHint" class="sub">{{ pickupRedeemHint }}</p>
          <p v-if="allowCertPickupQr && pickupQrHint" class="sub">{{ pickupQrHint }}</p>
          <p v-if="allowVisitorPassPrint && visitorPassPrintHint" class="sub">{{ visitorPassPrintHint }}</p>
          <p v-if="allowCheckinDailyReport && checkinDailyHint" class="sub">{{ checkinDailyHint }}</p>
          <p v-if="allowEvalCollegeExport && evalCollegeExportHint" class="sub">{{ evalCollegeExportHint }}</p>
          <p v-if="allowAttachKeepOld && attachKeepOldHint" class="sub">{{ attachKeepOldHint }}</p>
          <p v-if="allowEvalUrge && evalUrgeHint" class="sub">{{ evalUrgeHint }}</p>
          <el-form-item v-if="allowProjChangeLog" :label="changeLogNoteLabel" required>
            <el-input
              v-model="form.changeLogNote"
              type="textarea"
              :rows="3"
              maxlength="512"
              show-word-limit
              :placeholder="projChangeLogHint || `请填写${changeLogNoteLabel}`"
            />
          </el-form-item>
          <p v-if="allowProjChangeLog && projChangeLogHint" class="sub">{{ projChangeLogHint }}</p>
          <p v-if="allowHideEvalResult && hideEvalResultHint" class="sub">{{ hideEvalResultLabel }}：{{ hideEvalResultHint }}</p>
          <p v-if="allowSignRemarkVisible && signRemarkVisibleHint" class="sub">{{ signRemarkVisibleLabel }}：{{ signRemarkVisibleHint }}</p>
          <p v-if="allowCertVerify && certVerifyHint" class="sub">{{ certVerifyHint }}</p>
          <el-form-item v-if="allowVisitorCount" :label="visitorCountLabel">
            <el-input-number v-model="form.visitorCount" :min="0" :max="99" />
          </el-form-item>
          <p v-if="allowVisitorCount && visitorCountHint" class="sub">{{ visitorCountHint }}</p>
          <el-form-item v-if="allowAwardCertNo" :label="awardCertNoLabel" required>
            <el-input v-model="form.awardCertNo" maxlength="64" :placeholder="awardCertNoHint || `请填写${awardCertNoLabel}`" />
          </el-form-item>
          <el-form-item v-if="allowVendorQuotes" :label="vendorQuotesLabel" required>
            <el-input
              v-model="form.vendorQuotes"
              type="textarea"
              :rows="Math.max(3, minVendorQuotes || 3)"
              maxlength="2000"
              :placeholder="vendorQuotesHint || '每行一家供应商名称'"
            />
          </el-form-item>
          <p v-if="allowVendorQuotes && minVendorQuotesHint" class="sub">{{ minVendorQuotesHint }}</p>
          <p v-if="forceOnePerArchive && evalOnePerCourseHint" class="sub">{{ evalOnePerCourseHint }}</p>
          <p v-if="allowEvalOpenWindow && evalOpenWindowHint" class="sub">{{ evalOpenWindowHint }}</p>
          <p v-if="allowEthicBatch && (ethicBatchHint || batchNoLabel)" class="sub">
            <template v-if="ethicBatchHint">{{ ethicBatchHint }}</template>
            <template v-else>{{ batchNoLabel }} / {{ expireOnLabel }}</template>
          </p>
          <p v-if="allowPassExpire && passExpireHint" class="sub">{{ passExpireHint }}</p>
          <p v-if="allowPromoPlace && (promoPlaceHint || promoSizeLabel)" class="sub">
            {{ promoPlaceHint || (`${promoSizeLabel} / ${hangPlaceLabel}`) }}
          </p>
          <p v-if="allowEthicMeeting && (ethicMeetingHint || meetingOnLabel)" class="sub">
            {{ ethicMeetingHint || (`${meetingOnLabel} / ${resolutionNoteLabel}`) }}
          </p>
          <el-form-item v-if="allowLaborPlace" :label="laborPlaceLabel" required>
            <el-input v-model="form.laborPlace" maxlength="128" :placeholder="laborPlaceHint || `请填写${laborPlaceLabel}`" />
          </el-form-item>
          <el-form-item v-if="allowEffectiveOn" :label="effectiveOnLabel" required>
            <el-date-picker
              v-model="form.effectiveOn"
              type="date"
              value-format="YYYY-MM-DD"
              style="width:100%"
              :placeholder="effectiveOnHint || `请选择${effectiveOnLabel}`"
            />
          </el-form-item>
          <p v-if="allowEffectiveOn && effectiveOnHint" class="sub">{{ effectiveOnHint }}</p>
          <el-form-item v-if="allowDocRev" :label="docRevLabel" required>
            <el-input v-model="form.docRev" maxlength="32" :placeholder="docRevHint || `请填写${docRevLabel}`" />
          </el-form-item>
          <p v-if="allowDocRev && docRevHint" class="sub">{{ docRevHint }}</p>
          <el-form-item v-if="allowFitoutQuiet" :label="fitoutWindowLabel" required>
            <div class="attach-row">
              <el-time-picker
                v-model="form.workStart"
                format="HH:mm"
                value-format="HH:mm"
                placeholder="开始"
                style="width:48%"
              />
              <el-time-picker
                v-model="form.workEnd"
                format="HH:mm"
                value-format="HH:mm"
                placeholder="结束"
                style="width:48%"
              />
            </div>
          </el-form-item>
          <p v-if="allowFitoutQuiet && fitoutQuietHint" class="sub">{{ fitoutQuietHint }}</p>
          <el-form-item v-if="allowIssueCopies" :label="issueCopiesLabel" required>
            <el-input-number v-model="form.issueCopies" :min="1" :max="99" :precision="0" />
          </el-form-item>
          <p v-if="allowIssueCopies && issueCopiesHint" class="sub">{{ issueCopiesHint }}</p>
          <el-form-item v-if="allowSignParties" :label="signPartiesLabel" required>
            <el-checkbox-group v-model="form.signParties">
              <el-checkbox label="甲方">甲方</el-checkbox>
              <el-checkbox label="乙方">乙方</el-checkbox>
              <el-checkbox label="丙方">丙方</el-checkbox>
            </el-checkbox-group>
          </el-form-item>
          <p v-if="allowSignParties && signPartiesHint" class="sub">{{ signPartiesHint }}</p>
          <el-form-item v-if="allowTrainHours" :label="trainHoursLabel" required>
            <el-input-number v-model="form.trainHours" :min="0.5" :max="999" :precision="1" :step="0.5" />
          </el-form-item>
          <p v-if="allowTrainHours && trainHoursHint" class="sub">{{ trainHoursHint }}</p>
          <el-form-item v-if="allowMemberChange" :label="memberChangeNoteLabel" required>
            <el-input
              v-model="form.memberChangeNote"
              type="textarea"
              :rows="3"
              maxlength="512"
              show-word-limit
              :placeholder="memberChangeNoteHint || `请填写${memberChangeNoteLabel}`"
            />
          </el-form-item>
          <p v-if="allowMemberChange && memberChangeNoteHint" class="sub">{{ memberChangeNoteHint }}</p>
          <el-form-item v-if="allowProcureBudget" :label="procureAmountLabel" required>
            <el-input-number v-model="form.procureAmount" :min="0.01" :max="99999999" :precision="2" :step="100" />
          </el-form-item>
          <p v-if="allowProcureBudget && procureBudgetHint" class="sub">{{ procureBudgetHint }}</p>
          <el-form-item v-if="allowCheckinException" :label="exceptionTypeLabel" required>
            <el-select v-model="form.exceptionType" placeholder="请选择" style="width:100%">
              <el-option v-for="opt in exceptionTypeOptions" :key="opt" :label="opt" :value="opt" />
            </el-select>
          </el-form-item>
          <p v-if="allowCheckinException && exceptionTypeHint" class="sub">{{ exceptionTypeHint }}</p>
          <el-form-item v-if="allowVisitPurpose" :label="visitPurposeLabel" required>
            <el-select v-model="form.visitPurpose" placeholder="请选择" style="width:100%">
              <el-option v-for="opt in visitPurposeOptions" :key="opt" :label="opt" :value="opt" />
            </el-select>
          </el-form-item>
          <p v-if="allowVisitPurpose && visitPurposeHint" class="sub">{{ visitPurposeHint }}</p>
          <el-form-item v-if="allowClubCopyLast">
            <el-button type="primary" plain @click="copyLastYear">{{ clubCopyLastLabel }}</el-button>
            <p v-if="clubCopyLastHint" class="sub">{{ clubCopyLastHint }}</p>
          </el-form-item>
          <el-form-item v-if="allowProjFundUse" :label="fundUseYuanLabel" required>
            <el-input-number v-model="form.fundUseYuan" :min="0.01" :max="99999999" :precision="2" :step="100" />
          </el-form-item>
          <el-form-item v-if="allowProjFundUse" :label="fundUseNoteLabel" required>
            <el-input
              v-model="form.fundUseNote"
              type="textarea"
              :rows="3"
              maxlength="512"
              show-word-limit
              :placeholder="fundUseHint || `请填写${fundUseNoteLabel}`"
            />
          </el-form-item>
          <p v-if="allowProjFundUse && fundUseHint" class="sub">{{ fundUseHint }}</p>
          <el-form-item v-if="allowVisitSlotRemain" :label="visitOnLabel" required>
            <el-date-picker
              v-model="form.visitOn"
              type="date"
              value-format="YYYY-MM-DD"
              placeholder="请选择"
              style="width:100%"
            />
          </el-form-item>
          <p v-if="allowVisitSlotRemain && visitSlotRemainHint" class="sub">{{ visitSlotRemainHint }}</p>
          <p v-if="allowEvalDimWeight && evalDimWeightHint" class="sub">{{ evalDimWeightHint }}</p>
          <el-form-item v-if="allowPlagiarismUrl" :label="plagiarismUrlLabel" required>
            <el-input
              v-model="form.plagiarismUrl"
              maxlength="512"
              :placeholder="plagiarismUrlHint || `请填写${plagiarismUrlLabel}`"
            />
          </el-form-item>
          <p v-if="allowPlagiarismUrl && plagiarismUrlHint" class="sub">{{ plagiarismUrlHint }}</p>
          <p v-if="allowAbsentStreak && absentStreakHint" class="sub">{{ absentWarnNLabel }}：{{ absentStreakHint }}</p>
          <el-form-item v-if="allowPartyStage" :label="partyStageLabel" required>
            <el-select v-model="form.partyStage" placeholder="请选择" style="width:100%">
              <el-option v-for="opt in partyStageOptions" :key="opt" :label="opt" :value="opt" />
            </el-select>
          </el-form-item>
          <el-form-item v-if="allowPartyStage" :label="stageOnLabel" required>
            <el-date-picker
              v-model="form.stageOn"
              type="date"
              value-format="YYYY-MM-DD"
              placeholder="请选择"
              style="width:100%"
            />
          </el-form-item>
          <p v-if="allowPartyStage && partyStageHint" class="sub">{{ partyStageHint }}</p>
          <el-form-item v-if="allowEvalObserve" :label="observeOnLabel" required>
            <el-date-picker
              v-model="form.observeOn"
              type="date"
              value-format="YYYY-MM-DD"
              placeholder="请选择"
              style="width:100%"
            />
          </el-form-item>
          <el-form-item v-if="allowEvalObserve" :label="observeNoteLabel" required>
            <el-input
              v-model="form.observeNote"
              type="textarea"
              :rows="3"
              maxlength="512"
              show-word-limit
              :placeholder="evalObserveHint || `请填写${observeNoteLabel}`"
            />
          </el-form-item>
          <p v-if="allowEvalObserve && evalObserveHint" class="sub">{{ evalObserveHint }}</p>
          <el-form-item v-if="allowScheduleImpact" :label="scheduleImpactNoteLabel" required>
            <el-input
              v-model="form.scheduleImpactNote"
              type="textarea"
              :rows="3"
              maxlength="512"
              show-word-limit
              :placeholder="scheduleImpactHint || `请填写${scheduleImpactNoteLabel}`"
            />
          </el-form-item>
          <p v-if="allowScheduleImpact && scheduleImpactHint" class="sub">{{ scheduleImpactHint }}</p>
          <el-form-item v-if="allowContractAmount" :label="contractAmountLabel" required>
            <el-input-number v-model="form.contractAmount" :min="0.01" :max="99999999" :precision="2" :step="100" />
          </el-form-item>
          <p v-if="allowContractAmount && form.contractAmount != null" class="sub">
            {{ contractAmountCnLabel }} {{ amountToChinese(form.contractAmount) || '—' }}
          </p>
          <p v-if="allowContractAmount && contractAmountHint" class="sub">{{ contractAmountHint }}</p>
          <el-form-item v-if="allowFitoutRectify" :label="rectifyNoteLabel" required>
            <el-input
              v-model="form.rectifyNote"
              type="textarea"
              :rows="3"
              maxlength="512"
              show-word-limit
              :placeholder="rectifyNoteHint || `请填写${rectifyNoteLabel}`"
            />
          </el-form-item>
          <p v-if="allowFitoutRectify && rectifyNoteHint" class="sub">{{ rectifyNoteHint }}</p>
          <p v-if="allowProjNodeRemind && projNodeRemindHint" class="sub">{{ midDueOnLabel }} / {{ finalDueOnLabel }}：{{ projNodeRemindHint }}</p>
          <el-form-item v-if="allowFleetCrew" :label="driverNameLabel" required>
            <el-input v-model="form.driverName" maxlength="64" :placeholder="fleetCrewHint || `请填写${driverNameLabel}`" />
          </el-form-item>
          <el-form-item v-if="allowFleetCrew" :label="passengerNamesLabel">
            <el-input v-model="form.passengerNames" maxlength="255" :placeholder="'有随车人时填写，逗号分隔'" />
          </el-form-item>
          <p v-if="allowFleetCrew && fleetCrewHint" class="sub">{{ fleetCrewHint }}</p>
          <p v-if="archiveExpireNotifyHint" class="sub">{{ archiveExpireNotifyHint }}</p>
          <el-form-item v-if="allowSeatZone" :label="seatZoneLabel">
            <el-select v-model="form.seatZone" clearable style="width:100%" :placeholder="seatZoneHint || '请选择分区'">
              <el-option v-for="opt in seatZoneOptions" :key="opt" :label="opt" :value="opt" />
            </el-select>
          </el-form-item>
          <p v-if="allowSeatZone && seatZoneHint" class="sub">{{ seatZoneHint }}</p>
          <el-form-item v-if="allowProjectNo" :label="projectNoLabel">
            <el-input v-model="form.projectNo" maxlength="64" :placeholder="`选填${projectNoLabel}`" />
          </el-form-item>
          <el-form-item v-if="allowProcureRef" :label="procureRefLabel">
            <el-input v-model="form.procureRefNo" maxlength="64" :placeholder="`选填${procureRefLabel}`" />
          </el-form-item>
          <p v-if="allowProcureRef && procureToAssetHint" class="hint-inline">{{ procureToAssetHint }}</p>
          <el-form-item v-if="allowDualReview" :label="dualReviewerALabel">
            <el-input v-model="form.dualReviewerA" maxlength="64" />
          </el-form-item>
          <el-form-item v-if="allowDualReview" :label="dualReviewerBLabel">
            <el-input v-model="form.dualReviewerB" maxlength="64" />
          </el-form-item>
          <el-form-item v-if="allowShipFee" :label="shipFeeLabel">
            <el-input-number v-model="form.shipFeeYuan" :min="0" :max="999999" :precision="2" />
          </el-form-item>
          <el-form-item v-if="allowUtilityNote" :label="utilityNoteLabel">
            <el-input v-model="form.utilityNote" type="textarea" :rows="2" maxlength="255" />
          </el-form-item>
          <el-form-item v-if="requirePeerConfirm" :label="peerUsernameLabel" required>
            <el-input v-model="form.peerUsername" maxlength="64" :placeholder="`请填写${peerUsernameLabel}`" />
          </el-form-item>
          <p v-if="peerConfirmHint" class="sub">{{ peerConfirmHint }}</p>
          <p v-if="closedLoanHint" class="sub">{{ closedLoanHint }}</p>
          <p v-if="offHoursPickupHint" class="sub">{{ offHoursPickupHint }}</p>
          <p v-if="bedReleaseHint" class="sub">{{ bedReleaseHint }}</p>
          <p v-if="claimAutoOffHint" class="sub">{{ claimAutoOffHint }}</p>
          <p v-if="expireOffHint" class="sub">{{ expireOffHint }}</p>
          <p v-if="stockTightHint" class="sub">{{ stockTightHint }}</p>
          <p v-if="oversellGuardHint" class="sub">{{ oversellGuardHint }}</p>
          <p v-if="cancelBeforeHint" class="sub">{{ cancelBeforeHint }}</p>
          <p v-if="claimCooldownHint" class="sub">{{ claimCooldownHint }}</p>
          <p v-if="creditCapHint" class="sub">{{ creditCapHint }}</p>
          <p v-if="creditWarnHint" class="sub">{{ creditWarnHint }}</p>
          <p v-if="maxDropHint" class="sub">{{ maxDropHint }}</p>
          <p v-if="prereqHint" class="sub">{{ prereqHint }}</p>
          <p v-if="courseKindHint" class="sub">{{ courseKindHint }}</p>
          <p v-if="minGroupHint" class="sub">{{ minGroupHint }}</p>
          <p v-if="waitlistPromoteHint" class="sub">{{ waitlistPromoteHint }}</p>
          <p v-if="sessionGroupHint" class="sub">{{ sessionGroupHint }}</p>
          <p v-if="collegeFilterHint" class="sub">{{ collegeFilterHint }}</p>
          <p v-if="planUrlHint" class="sub">{{ planUrlHint }}</p>
          <p v-if="applyInviteHint && requireApplyInvite" class="sub">{{ applyInviteHint }}</p>
          <p v-if="applySuccessInboxTitle && applySuccessInboxBody" class="sub">
            {{ applySuccessInboxTitle }}：提交后将收到站内信提醒。
          </p>
          <el-form-item v-if="pickDateRange" label="起止日期" required>
            <el-date-picker
              v-model="form.period"
              type="datetimerange"
              value-format="YYYY-MM-DD HH:mm:ss"
              range-separator="至"
              start-placeholder="开始"
              end-placeholder="结束"
              style="width:100%"
            />
          </el-form-item>
          <el-form-item v-if="weekNoOn" :label="weekNoLabel" required>
            <el-input-number v-model="form.weekNo" :min="1" :max="60" />
            <span class="sub">{{ weekNoLead }}</span>
          </el-form-item>
          <el-form-item v-if="interviewPlaceOn" :label="interviewPlaceLabel">
            <el-input v-model="form.interviewPlace" :placeholder="interviewPlaceLead" />
          </el-form-item>
          <el-form-item v-if="allowInterviewResult" :label="interviewResultLabel">
            <el-select v-model="form.interviewResult" clearable style="width:100%">
              <el-option v-for="opt in interviewResultOptions" :key="opt" :label="opt" :value="opt" />
            </el-select>
          </el-form-item>
          <el-form-item v-if="allowWrittenScore" :label="writtenScoreLabel">
            <el-input-number v-model="form.writtenScore" :min="0" :max="999" :precision="1" />
          </el-form-item>
          <el-form-item v-if="allowBgCheckNote" :label="bgCheckNoteLabel">
            <el-input v-model="form.bgCheckNote" type="textarea" :rows="2" maxlength="255" />
          </el-form-item>
          <el-form-item v-if="allowDealAmount" :label="dealAmountLabel">
            <el-input-number v-model="form.dealAmountYuan" :min="0" :max="99999999" :precision="2" />
          </el-form-item>
          <el-form-item v-if="allowNextAction" :label="nextActionLabel">
            <el-input v-model="form.nextAction" maxlength="255" :placeholder="`选填${nextActionLabel}`" />
          </el-form-item>
          <el-form-item v-if="allowNextAction">
            <el-checkbox v-model="form.nextActionDone">{{ nextActionDoneLabel }}</el-checkbox>
          </el-form-item>
          <el-form-item v-if="allowLeaveProxy" :label="leaveProxyLabel">
            <el-input v-model="form.proxyName" maxlength="64" :placeholder="`选填${leaveProxyLabel}`" />
          </el-form-item>
          <el-form-item v-if="requireReturnDate" :label="returnDateLabel">
            <el-date-picker
              v-model="form.returnDate"
              type="date"
              value-format="YYYY-MM-DD"
              placeholder="返岗日期"
              style="width:100%"
            />
          </el-form-item>
          <el-form-item v-if="allowDefenseResult" :label="defenseResultLabel">
            <el-select v-model="form.defenseResult" clearable style="width:100%">
              <el-option v-for="opt in defenseResultOptions" :key="opt" :label="opt" :value="opt" />
            </el-select>
          </el-form-item>
          <el-form-item v-if="maskBankAccount" :label="bankAccountLabel">
            <el-input v-model="form.bankAccount" maxlength="64" :placeholder="`请填写${bankAccountLabel}`" />
          </el-form-item>
          <p v-if="maskBankAccount && bankMaskHint" class="sub">{{ bankMaskHint }}</p>
          <el-form-item v-if="homeVisitTemplate" :label="homeVisitFamilyLabel">
            <el-input v-model="form.homeVisitFamily" type="textarea" :rows="2" maxlength="255" />
          </el-form-item>
          <el-form-item v-if="homeVisitTemplate" :label="homeVisitTalkLabel">
            <el-input v-model="form.homeVisitTalk" type="textarea" :rows="2" maxlength="255" />
          </el-form-item>
          <el-form-item v-if="homeVisitTemplate" :label="homeVisitPlanLabel">
            <el-input v-model="form.homeVisitPlan" type="textarea" :rows="2" maxlength="255" />
          </el-form-item>
          <el-form-item v-if="requireFeedbackSet" :label="feedbackInterestLabel">
            <el-input v-model="form.feedbackInterest" maxlength="128" />
          </el-form-item>
          <el-form-item v-if="requireFeedbackSet" :label="feedbackConcernLabel">
            <el-input v-model="form.feedbackConcern" maxlength="255" />
          </el-form-item>
          <el-form-item v-if="requireFeedbackSet" :label="feedbackNextLabel">
            <el-input v-model="form.feedbackNext" maxlength="255" />
          </el-form-item>
          <el-form-item v-if="allowRecordUrl" :label="recordUrlLabel">
            <el-input v-model="form.recordUrl" maxlength="255" placeholder="外链地址" />
          </el-form-item>
          <el-form-item v-if="requireAppraisal" :label="appraisalCommentLabel">
            <el-input v-model="form.appraisalComment" type="textarea" :rows="3" maxlength="512" />
          </el-form-item>
          <el-form-item v-if="requireAppraisal" :label="appraisalGradeLabel">
            <el-select v-model="form.appraisalGrade" clearable style="width:100%">
              <el-option v-for="opt in appraisalGradeOptions" :key="opt" :label="opt" :value="opt" />
            </el-select>
          </el-form-item>
          <el-form-item v-if="allowCompanyEval" :label="companyEvalLabel">
            <el-input v-model="form.companyEval" type="textarea" :rows="2" maxlength="512" />
          </el-form-item>
          <el-form-item v-if="allowConfidential">
            <el-checkbox v-model="form.confidential">{{ confidentialLabel }}</el-checkbox>
          </el-form-item>
          <el-form-item v-if="allowAssignDept" :label="assignDeptLabel">
            <el-input v-model="form.assignDept" maxlength="64" :placeholder="`选填${assignDeptLabel}`" />
          </el-form-item>
          <el-form-item v-if="resumeFieldSet" :label="resumeEduLabel">
            <el-input v-model="form.resumeEdu" maxlength="64" />
          </el-form-item>
          <el-form-item v-if="resumeFieldSet" :label="resumeExpLabel">
            <el-input v-model="form.resumeExp" maxlength="64" />
          </el-form-item>
          <el-form-item v-if="resumeFieldSet" :label="resumeSkillLabel">
            <el-input v-model="form.resumeSkill" type="textarea" :rows="2" maxlength="255" />
          </el-form-item>
          <el-form-item v-if="showFollowCols" :label="channelLabel">
            <el-select v-model="form.contactChannel" clearable :placeholder="channelPlaceholder" style="width:100%">
              <el-option v-for="opt in channelOptions" :key="opt" :label="opt" :value="opt" />
            </el-select>
          </el-form-item>
          <el-form-item v-if="showFollowCols" :label="nextAtLabel">
            <el-date-picker
              v-model="form.nextFollowAt"
              type="datetime"
              value-format="YYYY-MM-DD HH:mm:ss"
              placeholder="选填"
              style="width:100%"
            />
          </el-form-item>
          <el-form-item v-if="requireAttach" :label="attachFieldLabel" required>
            <div class="attach-row">
              <el-upload
                :show-file-list="false"
                accept="image/*,.pdf,.doc,.docx"
                :http-request="onAttach"
              >
                <el-button size="small">{{ form.attachUrl ? '重新上传' : '上传附件' }}</el-button>
              </el-upload>
              <a v-if="form.attachUrl" :href="form.attachUrl" target="_blank" rel="noopener noreferrer">已上传</a>
            </div>
            <p v-if="attachFieldHint" class="sub">{{ attachFieldHint }}</p>
          </el-form-item>
          <p v-if="requireMaterial && materialApplyHint" class="sub">{{ materialApplyHint }}</p>
          <MaterialChecklistFields v-if="requireMaterial" ref="matRef" />
        </template>
        <template v-else>
          <el-form-item label="标题" required>
            <el-input v-model="form.title" maxlength="80" placeholder="请输入标题" />
          </el-form-item>
          <template v-if="lookup.enabled">
            <el-form-item :label="lookup.typeLabel" required>
              <el-select v-model="form.typeId" filterable placeholder="请选择" style="width:100%">
                <el-option v-for="t in types" :key="t.id" :label="t.name" :value="t.id" />
              </el-select>
            </el-form-item>
            <el-form-item :label="lookup.siteLabel" required>
              <el-select v-model="form.siteId" filterable placeholder="请选择" style="width:100%" @change="onSiteChange">
                <el-option v-for="s in sites" :key="s.id" :label="s.name" :value="s.id" />
              </el-select>
            </el-form-item>
            <el-form-item :label="lookup.unitLabel" required>
              <el-select v-model="form.roomId" filterable placeholder="请先选上级" style="width:100%" :disabled="!form.siteId">
                <el-option v-for="u in units" :key="u.id" :label="u.code || u.name" :value="u.id" />
              </el-select>
            </el-form-item>
          </template>
          <el-form-item v-else label="地点" required>
            <div class="loc-row">
              <el-input v-model="form.location" maxlength="64" placeholder="请填写地点" />
              <el-button
                v-if="addressReuseOn && lastLocations.length"
                @click="reuseLastLocation"
              >沿用上次</el-button>
            </div>
            <p v-if="addressReuseOn && addressReuseHint" class="field-hint">{{ addressReuseHint }}</p>
            <el-select
              v-if="addressReuseOn && lastLocations.length"
              v-model="form.location"
              clearable
              filterable
              placeholder="从地址簿点选"
              style="width:100%;margin-top:8px"
            >
              <el-option v-for="loc in lastLocations" :key="loc" :label="loc" :value="loc" />
            </el-select>
          </el-form-item>
          <el-alert
            v-if="selfHelpHint || slaPageHint"
            type="info"
            :closable="false"
            show-icon
            :title="selfHelpHint || slaPageHint"
            style="margin-bottom:12px"
          />
          <template v-if="showPriorityCols">
            <el-form-item label="优先级">
              <el-select v-model="form.priority" style="width:100%">
                <el-option label="普通" value="普通" />
                <el-option label="紧急" value="紧急" />
                <el-option label="高" value="高" />
              </el-select>
            </el-form-item>
            <el-form-item label="联系电话">
              <el-input v-model="form.contactPhone" maxlength="20" placeholder="便于回访联系" />
              <p v-if="phoneDupHint" class="sub">{{ phoneDupHint }}</p>
            </el-form-item>
          </template>
          <el-form-item v-if="preferredSlotOn" :label="preferredSlotLabel">
            <el-input v-model="form.preferredSlot" maxlength="64" placeholder="如：工作日 14:00-16:00" />
          </el-form-item>
          <el-form-item v-if="allowMeetingPlace" :label="meetingPlaceLabel">
            <el-input v-model="form.pickupPlace" maxlength="128" :placeholder="`请填写${meetingPlaceLabel}`" />
          </el-form-item>
          <el-form-item v-if="allowEmergencyContact" :label="emergencyContactLabel" required>
            <el-input v-model="form.emergencyContact" maxlength="64" :placeholder="`请填写${emergencyContactLabel}`" />
          </el-form-item>
          <el-form-item v-if="allowEmergencyContact" :label="emergencyPhoneLabel" required>
            <el-input v-model="form.emergencyPhone" maxlength="20" :placeholder="`请填写${emergencyPhoneLabel}`" />
          </el-form-item>
          <el-form-item v-if="allowPublicArea" :label="publicAreaLabel">
            <el-select v-model="form.addressType" clearable style="width:100%">
              <el-option label="室内" value="室内" />
              <el-option :label="publicAreaLabel" value="公区" />
            </el-select>
          </el-form-item>
          <el-form-item v-if="nightUrgentOn" label="夜间/节假日">
            <el-switch v-model="form.nightUrgent" active-text="加急" />
          </el-form-item>
          <el-form-item v-if="allowAssetCode" :label="assetCodeLabel">
            <el-input v-model="form.assetCode" maxlength="64" placeholder="可手输资产编号" />
          </el-form-item>
          <el-form-item v-if="progressSubscribeOn">
            <el-checkbox v-model="form.subscribeProgress">进度变更时站内提醒我</el-checkbox>
          </el-form-item>
          <el-form-item v-if="allowAudioRemark" label="语音备注">
            <el-input v-model="form.audioUrl" maxlength="255" placeholder="可填录音链接，或先上传附件后粘贴地址" />
            <el-upload :show-file-list="false" :http-request="onAudioUpload" style="margin-top:8px">
              <el-button plain size="small">上传音频</el-button>
            </el-upload>
          </el-form-item>
          <el-form-item label="说明">
            <el-input v-model="form.remark" type="textarea" :rows="3" maxlength="400" />
          </el-form-item>
          <el-form-item v-if="requireAttach" :label="attachFieldLabel" required>
            <div class="attach-row">
              <el-upload
                :show-file-list="false"
                accept="image/*,.pdf,.doc,.docx"
                :http-request="onAttach"
              >
                <el-button size="small">{{ form.attachUrl ? '重新上传' : '上传附件' }}</el-button>
              </el-upload>
              <a v-if="form.attachUrl" :href="form.attachUrl" target="_blank" rel="noopener noreferrer">已上传</a>
            </div>
            <p v-if="attachFieldHint" class="sub">{{ attachFieldHint }}</p>
          </el-form-item>
          <p v-if="requireMaterial && materialApplyHint" class="sub">{{ materialApplyHint }}</p>
          <MaterialChecklistFields v-if="requireMaterial" ref="matRef" />
        </template>
      </el-form>
      <template #footer>
        <el-button @click="visible = false">取消</el-button>
        <el-button v-if="allowTicketDraft" @click="submit(true)">存草稿</el-button>
        <el-button type="primary" @click="submit(false)">提交</el-button>
      </template>
    </el-dialog>

    <TicketRateDialog
      v-model="rateVisible"
      :ticket-id="rateRow?.id"
      :title="rateRow ? (rateRow.title || ('编号 ' + rateRow.id)) : ''"
      :follow-mode="rateFollowMode"
      @done="load"
    />

    <el-dialog v-model="checkinVisible" :title="checkinLabel" width="400px" destroy-on-close>
      <p class="rate-tip" v-if="checkinRow">对「{{ checkinRow.title || ('编号 ' + checkinRow.id) }}」输入签到码</p>
      <el-form label-width="100px">
        <el-form-item label="签到码" required>
          <el-input v-model="checkinCode" maxlength="16" placeholder="请输入签到码" @keyup.enter="submitCheckin" />
        </el-form-item>
        <el-form-item v-if="allowLateMinutes" :label="lateMinutesLabel">
          <el-input-number v-model="checkinLateMinutes" :min="0" :max="999" />
        </el-form-item>
      </el-form>
      <p v-if="allowLateMinutes && lateMinutesHint" class="sub">{{ lateMinutesHint }}</p>
      <template #footer>
        <el-button @click="checkinVisible = false">取消</el-button>
        <el-button type="primary" :loading="checkinLoading" @click="submitCheckin">签到</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="proofDlg.visible" title="提交认领凭证" width="480px" destroy-on-close>
      <p class="rate-tip" v-if="proofDlg.row">对「{{ proofDlg.row.title || ('编号 ' + proofDlg.row.id) }}」提交凭证后进入待核验</p>
      <ClaimProofFields ref="proofRef" />
      <template #footer>
        <el-button @click="proofDlg.visible = false">取消</el-button>
        <el-button type="primary" :loading="proofDlg.loading" @click="submitProof">提交凭证</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="wallet.visible" :title="ticketWalletLabel" width="420px" destroy-on-close>
      <p class="rate-tip" v-if="wallet.row">「{{ wallet.row.title || ('编号 ' + wallet.row.id) }}」</p>
      <p v-if="ticketWalletHint" class="sub">{{ ticketWalletHint }}</p>
      <p class="sub">通行码：{{ wallet.row?.passCode || wallet.row?.checkinCode || '—' }}</p>
      <template #footer>
        <el-button @click="wallet.visible = false">关闭</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="transfer.visible" :title="ticketTransferLabel" width="420px" destroy-on-close>
      <p class="rate-tip" v-if="transfer.row">将「{{ transfer.row.title || ('编号 ' + transfer.row.id) }}」转让给站内账号</p>
      <p v-if="ticketTransferHint" class="sub">{{ ticketTransferHint }}</p>
      <el-form label-width="100px">
        <el-form-item label="接收账号" required>
          <el-input v-model="transfer.toUsername" maxlength="64" placeholder="对方用户名" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="transfer.visible = false">取消</el-button>
        <el-button type="primary" :loading="transfer.loading" @click="submitTransfer">确认转让</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="postGallery.visible" :title="postGalleryLabel" width="480px" destroy-on-close>
      <p class="rate-tip" v-if="postGallery.row">「{{ postGallery.row.title || ('编号 ' + postGallery.row.id) }}」</p>
      <p v-if="postGalleryHint" class="sub">{{ postGalleryHint }}</p>
      <div class="gallery-edit">
        <el-upload :show-file-list="false" accept="image/*" :http-request="onPostGalleryUpload">
          <el-button size="small" :disabled="postGallery.images.length >= 9">添加图片</el-button>
        </el-upload>
        <div class="gallery-list">
          <div v-for="(u, i) in postGallery.images" :key="i" class="gallery-item">
            <img :src="u" alt="" />
            <el-button link type="danger" size="small" @click="postGallery.images.splice(i, 1)">移除</el-button>
          </div>
        </div>
      </div>
      <template #footer>
        <el-button @click="postGallery.visible = false">取消</el-button>
        <el-button type="primary" :loading="postGallery.loading" @click="submitPostGallery">保存相册</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="credit.visible" :title="`我的${creditScoreLabel}`" width="520px" destroy-on-close>
      <p class="rate-tip">
        当前 {{ credit.score }} 分，初始 {{ credit.initial }} 分
        <template v-if="credit.overdueDelta">，逾期每单扣 {{ credit.overdueDelta }} 分</template>
        <template v-if="creditBlocked">；低于 {{ credit.blockBelow }} 分暂不可再借</template>
      </p>
      <el-table :data="credit.rows" size="small" stripe max-height="320">
        <el-table-column prop="delta" label="变动" width="80">
          <template #default="{ row }">
            <span :style="{ color: row.delta < 0 ? '#f56c6c' : '#67c23a', fontWeight: 600 }">
              {{ row.delta > 0 ? '+' + row.delta : row.delta }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="scoreAfter" :label="creditScoreLabel" width="90" />
        <el-table-column prop="reason" label="事由" min-width="160" show-overflow-tooltip />
        <el-table-column prop="createdAt" label="时间" width="170" />
        <template #empty>暂无信誉分变动</template>
      </el-table>
      <template #footer>
        <el-button @click="credit.visible = false">关闭</el-button>
      </template>
    </el-dialog>

    <TicketProgressDialog v-model="progressVisible" :ticket-id="progressId" />

    <el-dialog v-model="ccComment.visible" :title="approveCcCommentLabel" width="420px" destroy-on-close>
      <p v-if="approveCcCommentHint" class="sub">{{ approveCcCommentHint }}</p>
      <el-input
        v-model="ccComment.text"
        type="textarea"
        :rows="3"
        maxlength="200"
        show-word-limit
        placeholder="填写知会评论"
      />
      <template #footer>
        <el-button @click="ccComment.visible = false">取消</el-button>
        <el-button type="primary" :loading="ccComment.loading" @click="submitCcComment">提交</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup src="./MyTickets.setup.js"></script>

<style scoped src="./MyTickets.css"></style>
