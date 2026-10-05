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

    <div class="list">
      <article
        v-for="row in list"
        :key="row.id"
        class="card"
        :class="{ 'imm-overdue': row.status === 'overdue' }"
      >
        <div class="mark">{{ (row.title || '?').slice(0, 1) }}</div>
        <div class="meta">
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
            <template v-if="row.typeName"> · {{ row.typeName }}</template>
            <template v-if="row.location"> · {{ row.location }}</template>
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
          <div class="row">
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
              v-if="canWithdraw(row)"
              type="danger"
              size="small"
              plain
              :title="withdrawHint"
              @click="withdraw(row)"
            >撤销</el-button>
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
            >评分</el-button>
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
          <el-select v-model="returnDlg.faultReason" filterable allow-create default-first-option style="width:100%">
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
                allow-create
                default-first-option
                :placeholder="`请选择或填写${remarkLabel}`"
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
              allow-create
              default-first-option
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

<script setup>
import CodeQrBlock from '../../components/CodeQrBlock.vue'
import ImmSteps from '../../components/ImmSteps.vue'
import StatusChip from '../../components/StatusChip.vue'
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import http from '../../api/http'
import RichTextView from '../../components/RichTextView.vue'
import TicketRateDialog from '../../components/TicketRateDialog.vue'
import TicketProgressDialog from '../../components/TicketProgressDialog.vue'
import SchemaLabelHints from '../../components/SchemaLabelHints.vue'
import MaterialChecklistFields from '../../components/MaterialChecklistFields.vue'
import ClaimProofFields from '../../components/ClaimProofFields.vue'
import { MY_TICKETS_HINT_KEYS } from '../../utils/labelHintMount.js'
import {
  archiveCopy,
  followChannelLabel,
  followChannelOptions,
  getSchema,
  hasCap,
  hasTrait,
  nextFollowLabel,
  ticketCheckinLabel,
  ticketCopy,
  ticketDueLabel,
  ticketFineLabel,
  ticketShowsFollowCols,
  ticketShowsPriorityCols,
  ticketStatusLabel,
} from '../../utils/domainSchema.js'
import {
  filterArchiveByOwnerToken,
  filterArchiveByProfileRoom,
  matchSiteByBuilding,
  matchUnitByRoom,
  normRoomToken,
  ownerTokenFromProfile,
  profileSiteRoomFromExtras,
} from '../../utils/profileRoomMatch.js'
import {
  formatCountdownClock,
  isUrgentCountdown,
  secondsUntil,
  useNowTick,
} from '../../utils/useCountdown.js'
import { multiApproveSteps, ticketTagType, ticketTone } from '../../utils/statusTone.js'
import { downloadCsv } from '../../utils/csvDownload.js'
import { printTicketDocument } from '../../utils/ticketFormPrint.js'

const { nowMs } = useNowTick()
const ticket = ticketCopy()
const multiApproveOn = computed(() => hasCap('multi_approve'))
/** 请假天数等域内文案读 schema.labels，勿在页面写死 */
const leaveDaysLabel = computed(() => getSchema()?.labels?.leaveDaysLabel || '请假天数')
/** 周报周次：仅开启了 weekNoLabel 的域显示（DOM-INTERN） */
const weekNoOn = computed(() => !!getSchema()?.labels?.weekNoLabel)
const weekNoLabel = computed(() => getSchema()?.labels?.weekNoLabel || '周次')
const weekNoLead = computed(() => getSchema()?.labels?.weekNoLead || '')
/** 招聘：面试地点（interviewPlaceLabel 或 interviewRoomHint 开则显示并写库） */
const interviewPlaceOn = computed(
  () =>
    !!getSchema()?.labels?.interviewPlaceLabel
    || !!getSchema()?.labels?.interviewRoomHint,
)
const interviewPlaceLabel = computed(() => getSchema()?.labels?.interviewPlaceLabel || '面试地点')
const interviewPlaceLead = computed(() => getSchema()?.labels?.interviewPlaceLead || '')

function isMultiApproveStatus(st) {
  return ['pending', 'pending_mid', 'pending_final', 'approved'].includes(st)
}
const archive = archiveCopy()
const verbs = computed(() => ticket.verbs || {})
const states = computed(() => ticket.states || {})

// 未跟进 N 天列表筛（bake: ticket.staleFollowDays → ticket-stale-follow-days）
const staleFollowDays = ref(0)
const stalePoolLabel = computed(() => {
  const base = labels.value.stalePoolHint || '未跟进 N 天'
  return staleFollowDays.value > 0 ? base.replace(/N/g, String(staleFollowDays.value)) : base
})
const phoneDupHint = computed(() => labels.value.phoneDupHint || '')
const maxReviseHint = computed(() => labels.value.maxReviseHint || '')
const withdrawHint = computed(() => labels.value.withdrawHint || '')
const approveDueSoonHint = computed(() => labels.value.approveDueSoonHint || '')
const approveRemarkAttachLabel = computed(() => labels.value.approveRemarkAttachLabel || '审核意见附件')
const allowApproveCcComment = computed(() => !!ticket.allowApproveCcComment)
const approveCcCommentLabel = computed(() => labels.value.approveCcCommentLabel || '知会评论')
const approveCcCommentHint = computed(() => labels.value.approveCcCommentHint || '')
const approveAutoPassHint = computed(() => labels.value.approveAutoPassHint || '')
// 事件等级影响处理时限（bake: ticket.levelAffectsDeadline → ticket-level-sla-*-days）
const levelSlaDays = ref('')
const levelSlaHint = computed(() => labels.value.levelSlaHint || '')
const levelSlaText = computed(() => {
  const parts = String(levelSlaDays.value || '').split(',').map((s) => String(s || '').trim())
  if (parts.length < 3 || !parts[0]) return ''
  return `高 ${parts[0]} 天 / 中 ${parts[1]} 天 / 低 ${parts[2]} 天`
})
// 事件上报群发当日值班（bake: ticket.notifyDutyOnReport）
const notifyDutyHint = computed(() => labels.value.notifyDutyHint || '')
// 异议窗口（bake: ticket.allowObjectionWindow / ticket.objectionDays）
const objectionWindowHint = computed(() => labels.value.objectionWindowHint || '')
const plural = computed(() => ticket.labelPlural || ticket.label || '我的申请')
const labels = computed(() => getSchema().labels || {})
const creditOn = computed(() => !!ticket.creditOnOverdue || !!ticket.creditPoints)
const creditScoreLabel = computed(() => labels.value.creditScoreLabel || '信誉分')
const credit = reactive({
  score: 0,
  initial: 0,
  overdueDelta: 0,
  blockBelow: 0,
  rows: [],
  visible: false,
})
const wallet = reactive({ visible: false, row: null })
const transfer = reactive({ visible: false, row: null, toUsername: '', loading: false })
const postGallery = reactive({ visible: false, row: null, images: [], loading: false })
const creditBlocked = computed(
  () => creditOn.value && credit.blockBelow > 0 && credit.score < credit.blockBelow,
)

/** 我的信誉分：credit-on-overdue 未开时后端返回 enabled=false，前端不开面。 */
async function loadCredit() {
  if (!creditOn.value) return
  try {
    const res = await http.get('/api/tickets/credit/mine')
    const d = res.data || {}
    credit.score = Number(d.score) || 0
    credit.initial = Number(d.initial) || 0
    credit.overdueDelta = Number(d.overdueDelta) || 0
    credit.blockBelow = Number(d.blockBelow) || 0
    credit.rows = d.rows || []
  } catch (e) {
    credit.rows = []
  }
}

function openCredit() {
  credit.visible = true
}
const applyVerb = computed(() => verbs.value.apply || '提交')
const archiveMode = computed(() => (getSchema().capabilities || []).includes('archive'))
const applyFromList = computed(() => !!ticket.applyFromList)
const requireClaimCode = computed(() => !!ticket.requireClaimCode)
const filterByOwnerToken = computed(() => !!ticket.filterByOwnerToken)
const ownerTokenSource = computed(() => ticket.ownerTokenSource || 'phone')
const ownerTokenStrict = computed(() => !!ticket.ownerTokenStrict)
const matchProfileRoom = computed(() => !!ticket.matchProfileRoom)
const matchProfileOpts = computed(() => ({
  buildingKey: ticket.matchProfileBuildingKey || 'dormBuilding',
  roomKey: ticket.matchProfileRoomKey || 'dormRoom',
  buildingField: ticket.matchProfileBuildingField || 'author',
  roomField: ticket.matchProfileRoomField || 'title',
  looseBuilding: !!ticket.matchProfileLooseBuilding,
}))
const matchProfileNeedMessage = computed(
  () => ticket.matchProfileNeedMessage || '请先在个人资料填写楼栋与房间',
)
const matchProfileDenyMessage = computed(
  () => ticket.matchProfileDenyMessage || '只能对本寝室的查寝场次登记归寝',
)
const archiveLabel = computed(() => archive.label || '事项')
const remarkLabel = computed(() => ticket.remarkLabel || '说明')
const requireRemark = computed(() => !!ticket.requireRemark)
const remarkOptions = computed(() => {
  const opts = ticket.remarkOptions
  return Array.isArray(opts) ? opts.filter((x) => typeof x === 'string' && x.trim()) : []
})
const allowProxyPickup = computed(() => !!ticket.allowProxyPickup)
const proxyNameLabel = computed(() => labels.value.proxyNameLabel || '代取人姓名')
const proxyPhoneLabel = computed(() => labels.value.proxyPhoneLabel || '代取人手机')
const allowDeposit = computed(() => !!ticket.allowDeposit)
const depositLabel = computed(() => labels.value.depositLabel || '借用押金（元）')
const requireNoticeAck = computed(
  () =>
    !!ticket.requireNoticeAck
    || !!labels.value.contractTemplateHint
    || !!labels.value.gpaPageHint
    || !!labels.value.makeupOverlayHint
    || !!labels.value.creditRuleHint
    || !!labels.value.bedPrintHint,
)
const noticeAckLabel = computed(
  () =>
    labels.value.noticeAckLabel
    || labels.value.contractTemplateHint
    || '我已阅读并同意相关须知',
)
const requireTrainingAck = computed(() => !!ticket.requireTrainingAck)
const requireInsuranceAck = computed(() => !!ticket.requireInsuranceAck)
const insuranceAckLabel = computed(() => labels.value.insuranceAckLabel || '我已阅读设备借用保险声明')
const requireMeetingAck = computed(() => !!ticket.requireMeetingAck)
const meetingAckLabel = computed(() => labels.value.meetingAckLabel || '我已与对方约定面交时间与地点')
const requireApplyInvite = computed(() => !!ticket.requireApplyInvite)
const applyInviteLabel = computed(
  () => labels.value.visitorInviteLabel || labels.value.applyInviteLabel || '报名口令',
)
const applyInviteHint = computed(
  () => labels.value.visitorInviteHint || labels.value.applyInviteHint || '',
)
const sessionGroupHint = computed(() => labels.value.sessionGroupHint || '')
const collegeFilterHint = computed(() => labels.value.collegeFilterHint || '')
const planUrlHint = computed(() => labels.value.planUrlHint || '')
const requirePriceNoteAck = computed(() => !!ticket.requirePriceNoteAck)
const requireSponsorAck = computed(() => !!ticket.requireSponsorAck)
const requirePlanAck = computed(() => !!ticket.requirePlanAck)
const requirePrereqAck = computed(() => !!ticket.requirePrereqAck)
const requireTourNoticeAck = computed(() => !!ticket.requireTourNoticeAck)
const allowLateMinutes = computed(() => !!ticket.allowLateMinutes)
const allowWishOrder = computed(() => !!ticket.allowWishOrder)
const allowVolunteerRole = computed(() => !!ticket.allowVolunteerRole)
const allowCompanions = computed(() => !!ticket.allowCompanions)
const companionNamesLabel = computed(() => labels.value.companionNamesLabel || '同行人姓名')
const companionNamesHint = computed(() => labels.value.companionNamesHint || '')
const allowCertPickup = computed(() => !!ticket.allowCertPickup)
const certPickupLabel = computed(() => labels.value.certPickupLabel || '领取方式')
const certPickupHint = computed(() => labels.value.certPickupHint || '')
const mailAddressLabel = computed(() => labels.value.mailAddressLabel || '邮寄地址')
const expressNoLabel = computed(() => labels.value.expressNoLabel || '快递单号')
const allowCertUrgent = computed(() => !!ticket.allowCertUrgent)
const certUrgentLabel = computed(() => labels.value.certUrgentLabel || '加急件')
const certUrgentHint = computed(() => labels.value.certUrgentHint || '')
const allowSealCopies = computed(() => !!ticket.allowSealCopies)
const sealCopiesLabel = computed(() => labels.value.sealCopiesLabel || '用印份数')
const bindNoteLabel = computed(() => labels.value.bindNoteLabel || '装订说明')
const sealCopiesHint = computed(() => labels.value.sealCopiesHint || '')
const sealCopyNosLabel = computed(() => labels.value.sealCopyNosLabel || '用印份号')
const sealWitnessAckLabel = computed(() => labels.value.sealWitnessAckLabel || '监印人已确认')
const allowExpenseInvoice = computed(() => !!ticket.allowExpenseInvoice)
const invoiceCountLabel = computed(() => labels.value.invoiceCountLabel || '发票张数')
const expenseAmountLabel = computed(() => labels.value.expenseAmountLabel || '报销金额（元）')
const expenseInvoiceHint = computed(() => labels.value.expenseInvoiceHint || '')
const allowExpenseAttachCount = computed(() => !!ticket.allowExpenseAttachCount)
const expenseAttachCountHint = computed(() => labels.value.expenseAttachCountHint || '')
const fleetDriverCertHint = computed(() => labels.value.fleetDriverCertHint || '')
const allowVisitorCount = computed(() => !!ticket.allowVisitorCount)
const visitorCountLabel = computed(() => labels.value.visitorCountLabel || '随行人数')
const visitorCountHint = computed(() => labels.value.visitorCountHint || '')
const showVisitorCompanions = computed(
  () => allowVisitorCount.value && Number(form.visitorCount) > 0,
)
const allowAwardCertNo = computed(() => !!ticket.allowAwardCertNo)
const awardCertNoLabel = computed(() => labels.value.awardCertNoLabel || '证书编号')
const awardCertNoHint = computed(() => labels.value.awardCertNoHint || '')
const allowVendorQuotes = computed(
  () => !!ticket.allowVendorQuotes || Number(ticket.minVendorQuotes || 0) > 0,
)
const vendorQuotesLabel = computed(() => labels.value.vendorQuotesLabel || '比价供应商')
const vendorQuotesHint = computed(() => labels.value.vendorQuotesHint || '')
const minVendorQuotes = computed(() => Number(ticket.minVendorQuotes || 0))
const minVendorQuotesHint = computed(() => labels.value.minVendorQuotesHint || '')
const forceOnePerArchive = computed(() => !!ticket.forceOnePerArchive)
const evalOnePerCourseHint = computed(() => labels.value.evalOnePerCourseHint || '')
const archiveExpireNotifyHint = computed(() => {
  if (!(Number(ticket.notifyArchiveExpireDays || 0) > 0)) return ''
  return labels.value.archiveExpireNotifyHint || ''
})
const allowFleetMileage = computed(() => !!ticket.allowFleetMileage)
const mileageLabel = computed(() => labels.value.mileageLabel || '行驶里程（公里）')
const fuelNoteLabel = computed(() => labels.value.fuelNoteLabel || '油耗备注')
const fleetMileageHint = computed(() => labels.value.fleetMileageHint || '')
const allowEvalOpenWindow = computed(() => !!ticket.allowEvalOpenWindow)
const evalOpenWindowHint = computed(() => labels.value.evalOpenWindowHint || '')
const allowCompHours = computed(() => !!ticket.allowCompHours)
const compHoursLabel = computed(() => labels.value.compHoursLabel || '核定调休小时')
const compHoursHint = computed(() => labels.value.compHoursHint || '')
const allowFleetCrew = computed(() => !!ticket.allowFleetCrew)
const driverNameLabel = computed(() => labels.value.driverNameLabel || '驾驶员')
const passengerNamesLabel = computed(() => labels.value.passengerNamesLabel || '随车人')
const fleetCrewHint = computed(() => labels.value.fleetCrewHint || '')
const allowEthicBatch = computed(() => !!ticket.allowEthicBatch)
const ethicBatchHint = computed(() => labels.value.ethicBatchHint || '')
const batchNoLabel = computed(() => labels.value.batchNoLabel || '批件编号')
const expireOnLabel = computed(() => labels.value.expireOnLabel || '批件有效期')
const laborAttachLabel = computed(() => (labels.value.laborAttachLabel || '').trim())
const laborAttachHint = computed(() => (labels.value.laborAttachHint || '').trim())
const checkinPhotoLabel = computed(() => (labels.value.checkinPhotoLabel || '').trim())
const checkinPhotoHint = computed(() => (labels.value.checkinPhotoHint || '').trim())
const allowPassExpire = computed(() => !!ticket.allowPassExpire)
const passExpireAtLabel = computed(() => labels.value.passExpireAtLabel || '通行码有效至')
const passExpiredLabel = computed(() => labels.value.passExpiredLabel || '已失效')
const passExpireHint = computed(() => labels.value.passExpireHint || '')
const allowReturnFuel = computed(() => !!ticket.allowReturnFuel)
const returnFuelLabel = computed(() => labels.value.returnFuelLabel || '回场油量')
const returnFuelHint = computed(() => labels.value.returnFuelHint || '')
const allowLaborPlace = computed(() => !!ticket.allowLaborPlace)
const laborPlaceLabel = computed(() => labels.value.laborPlaceLabel || '劳动地点')
const laborPlaceHint = computed(() => labels.value.laborPlaceHint || '')
const allowPromoPlace = computed(() => !!ticket.allowPromoPlace)
const promoPlaceHint = computed(() => labels.value.promoPlaceHint || '')
const promoSizeLabel = computed(() => labels.value.promoSizeLabel || '尺寸')
const hangPlaceLabel = computed(() => labels.value.hangPlaceLabel || '悬挂位置')
const allowEthicMeeting = computed(() => !!ticket.allowEthicMeeting)
const ethicMeetingHint = computed(() => labels.value.ethicMeetingHint || '')
const meetingOnLabel = computed(() => labels.value.meetingOnLabel || '会议日期')
const resolutionNoteLabel = computed(() => labels.value.resolutionNoteLabel || '决议摘要')
const allowEffectiveOn = computed(() => !!ticket.allowEffectiveOn)
const effectiveOnLabel = computed(() => labels.value.effectiveOnLabel || '生效日期')
const effectiveOnHint = computed(() => labels.value.effectiveOnHint || '')
const allowCertIssueNo = computed(() => !!ticket.allowCertIssueNo)
const certIssueNoLabel = computed(() => labels.value.certIssueNoLabel || '开具流水号')
const certIssueNoHint = computed(() => labels.value.certIssueNoHint || '')
const allowDocRev = computed(() => !!ticket.allowDocRev)
const docRevLabel = computed(() => labels.value.docRevLabel || '正文版本号')
const docRevHint = computed(() => labels.value.docRevHint || '')
const allowFitoutQuiet = computed(() => !!ticket.allowFitoutQuiet)
const fitoutWindowLabel = computed(() => labels.value.fitoutWindowLabel || '施工时段')
const fitoutQuietHint = computed(() => labels.value.fitoutQuietHint || '')
const allowIssueCopies = computed(() => !!ticket.allowIssueCopies)
const issueCopiesLabel = computed(() => labels.value.issueCopiesLabel || '开具份数')
const issueCopiesHint = computed(() => labels.value.issueCopiesHint || '')
const allowSignParties = computed(() => !!ticket.allowSignParties)
const signPartiesLabel = computed(() => labels.value.signPartiesLabel || '签署方')
const signPartiesHint = computed(() => labels.value.signPartiesHint || '')
const allowTrainHours = computed(() => !!ticket.allowTrainHours)
const trainHoursLabel = computed(() => labels.value.trainHoursLabel || '本次培训学时')
const trainHoursHint = computed(() => labels.value.trainHoursHint || '')
const allowInspectExpire = computed(() => !!ticket.allowInspectExpire)
const inspectExpireOnLabel = computed(() => labels.value.inspectExpireOnLabel || '年检到期日')
const inspectExpireHint = computed(() => labels.value.inspectExpireHint || '')
const allowMemberChange = computed(() => !!ticket.allowMemberChange)
const memberChangeNoteLabel = computed(() => labels.value.memberChangeNoteLabel || '成员变更说明')
const memberChangeNoteHint = computed(() => labels.value.memberChangeNoteHint || '')
const allowProcureBudget = computed(() => !!ticket.allowProcureBudget)
const procureAmountLabel = computed(() => labels.value.procureAmountLabel || '本次申购金额（元）')
const procureBudgetHint = computed(() => labels.value.procureBudgetHint || '')
const allowCheckinException = computed(() => !!ticket.allowCheckinException)
const exceptionTypeLabel = computed(() => labels.value.exceptionTypeLabel || '异常类型')
const exceptionTypeHint = computed(() => labels.value.exceptionTypeHint || '')
const exceptionTypeOptions = computed(() => {
  const opts = ticket.exceptionTypeOptions
  return Array.isArray(opts) ? opts.filter((x) => x && String(x).trim()) : []
})
const allowVisitPurpose = computed(() => !!ticket.allowVisitPurpose)
const visitPurposeLabel = computed(() => labels.value.visitPurposeLabel || '来访目的')
const visitPurposeHint = computed(() => labels.value.visitPurposeHint || '')
const visitPurposeOptions = computed(() => {
  const opts = ticket.visitPurposeOptions
  return Array.isArray(opts) ? opts.filter((x) => x && String(x).trim()) : []
})
const allowFitoutRectify = computed(() => !!ticket.allowFitoutRectify)
const rectifyNoteLabel = computed(() => labels.value.rectifyNoteLabel || '整改说明')
const rectifyNoteHint = computed(() => labels.value.rectifyNoteHint || '')
const allowFleetViolation = computed(() => !!ticket.allowFleetViolation)
const violationPersonLabel = computed(() => labels.value.violationPersonLabel || '违章责任人')
const violationPersonHint = computed(() => labels.value.violationPersonHint || '')
const allowProjNodeRemind = computed(() => !!ticket.allowProjNodeRemind)
const midDueOnLabel = computed(() => labels.value.midDueOnLabel || '中期材料节点')
const finalDueOnLabel = computed(() => labels.value.finalDueOnLabel || '结题材料节点')
const projNodeRemindHint = computed(() => labels.value.projNodeRemindHint || '')
const allowClubCopyLast = computed(() => !!ticket.allowClubCopyLast)
const clubCopyLastLabel = computed(() => labels.value.clubCopyLastLabel || '复制上年材料')
const clubCopyLastHint = computed(() => labels.value.clubCopyLastHint || '')
const allowProcureReturn = computed(() => !!ticket.allowProcureReturn)
const procureReturnFailLabel = computed(() => labels.value.procureReturnFailLabel || '验收不合格')
const returnNoteLabel = computed(() => labels.value.returnNoteLabel || '退货说明')
const procureReturnHint = computed(() => labels.value.procureReturnHint || '')
const allowMoralObjection = computed(() => !!ticket.allowMoralObjection)
const moralObjectionLabel = computed(() => labels.value.moralObjectionLabel || '异议说明')
const moralObjectionHint = computed(() => labels.value.moralObjectionHint || '')
const allowProjFundUse = computed(() => !!ticket.allowProjFundUse)
const fundUseYuanLabel = computed(() => labels.value.fundUseYuanLabel || '本次使用经费（元）')
const fundUseNoteLabel = computed(() => labels.value.fundUseNoteLabel || '经费使用说明')
const fundUseHint = computed(() => labels.value.fundUseHint || '')
const allowEvalDimWeight = computed(() => !!ticket.allowEvalDimWeight)
const evalDimWeightHint = computed(() => labels.value.evalDimWeightHint || '')
const allowVisitSlotRemain = computed(() => !!ticket.allowVisitSlotRemain)
const visitOnLabel = computed(() => labels.value.visitOnLabel || '来访日期')
const visitSlotRemainHint = computed(() => labels.value.visitSlotRemainHint || '')
const allowPlagiarismUrl = computed(() => !!ticket.allowPlagiarismUrl)
const plagiarismUrlLabel = computed(() => labels.value.plagiarismUrlLabel || '查重报告链接')
const plagiarismUrlHint = computed(() => labels.value.plagiarismUrlHint || '')
const allowAbsentStreak = computed(() => !!ticket.allowAbsentStreak)
const absentWarnNLabel = computed(() => labels.value.absentWarnNLabel || '连续未归预警次数')
const absentStreakHint = computed(() => labels.value.absentStreakHint || '')
const allowPartyStage = computed(() => !!ticket.allowPartyStage)
const partyStageLabel = computed(() => labels.value.partyStageLabel || '当前发展阶段')
const stageOnLabel = computed(() => labels.value.stageOnLabel || '进入该阶段日期')
const partyStageHint = computed(() => labels.value.partyStageHint || '')
const partyStageOptions = computed(() => {
  const opts = ticket.partyStageOptions
  return Array.isArray(opts) ? opts.filter((x) => x && String(x).trim()) : []
})
const allowEvalObserve = computed(() => !!ticket.allowEvalObserve)
const observeOnLabel = computed(() => labels.value.observeOnLabel || '听课日期')
const observeNoteLabel = computed(() => labels.value.observeNoteLabel || '听课记录')
const evalObserveHint = computed(() => labels.value.evalObserveHint || '')
const allowScheduleImpact = computed(() => !!ticket.allowScheduleImpact)
const scheduleImpactNoteLabel = computed(() => labels.value.scheduleImpactNoteLabel || '对课表的影响')
const scheduleImpactHint = computed(() => labels.value.scheduleImpactHint || '')
const allowContractAmount = computed(() => !!ticket.allowContractAmount)
const contractAmountLabel = computed(() => labels.value.contractAmountLabel || '合同金额（元）')
const contractAmountCnLabel = computed(() => labels.value.contractAmountCnLabel || '金额大写')
const contractAmountHint = computed(() => labels.value.contractAmountHint || '')
const allowExpenseLines = computed(() => !!ticket.allowExpenseLines)
const expenseLinesLabel = computed(() => labels.value.expenseLinesLabel || '报销明细')
const expenseLineCategoryLabel = computed(() => labels.value.expenseLineCategoryLabel || '费用类别')
const expenseLineAmountLabel = computed(() => labels.value.expenseLineAmountLabel || '金额（元）')
const expenseLineNoteLabel = computed(() => labels.value.expenseLineNoteLabel || '说明')
const expenseLinesHint = computed(() => labels.value.expenseLinesHint || '')
const expenseLineCategoryOptions = computed(() => {
  const opts = ticket.expenseLineCategoryOptions
  return Array.isArray(opts) && opts.length ? opts.filter((x) => x && String(x).trim()) : ['交通', '住宿', '餐饮', '办公', '其他']
})
const allowTripLegs = computed(() => !!ticket.allowTripLegs)
const tripLegsLabel = computed(() => labels.value.tripLegsLabel || '出差行程')
const tripLegFromLabel = computed(() => labels.value.tripLegFromLabel || '出发地')
const tripLegViaLabel = computed(() => labels.value.tripLegViaLabel || '途经')
const tripLegToLabel = computed(() => labels.value.tripLegToLabel || '到达地')
const tripLegOnLabel = computed(() => labels.value.tripLegOnLabel || '行程日期')
const tripLegsHint = computed(() => labels.value.tripLegsHint || '')
const allowHideEvalResult = computed(() => !!ticket.allowHideEvalResult)
const hideEvalResultLabel = computed(() => labels.value.hideEvalResultLabel || '结果对学生不可见')
const hideEvalResultHint = computed(() => labels.value.hideEvalResultHint || '')
const allowSignRemarkVisible = computed(() => !!ticket.allowSignRemarkVisible)
const signRemarkVisibleLabel = computed(() => labels.value.signRemarkVisibleLabel || '审批意见对签署方可见')
const signApproveRemarkLabel = computed(() => labels.value.signApproveRemarkLabel || '审批意见')
const signRemarkVisibleHint = computed(() => labels.value.signRemarkVisibleHint || '')
const allowProjChangeLog = computed(() => !!ticket.allowProjChangeLog)
const changeLogNoteLabel = computed(() => labels.value.changeLogNoteLabel || '变更摘要')
const projChangeLogHint = computed(() => labels.value.projChangeLogHint || '')
const allowCertVerify = computed(() => !!ticket.allowCertVerify)
const certVerifyCodeLabel = computed(() => labels.value.certVerifyCodeLabel || '真伪查询码')
const certVerifyHint = computed(() => labels.value.certVerifyHint || '')
const allowVisitWalkIn = computed(() => !!ticket.allowVisitWalkIn)
const visitWalkInLabel = computed(() => labels.value.visitWalkInLabel || '现场补录')
const visitWalkInHint = computed(() => labels.value.visitWalkInHint || '')
const allowCheckinProxy = computed(() => !!ticket.allowCheckinProxy)
const checkinProxyByLabel = computed(() => labels.value.checkinProxyByLabel || '代登人')
const checkinProxyHint = computed(() => labels.value.checkinProxyHint || '')
const allowClubRoster = computed(() => !!ticket.allowClubRoster)
const clubRosterLabel = computed(() => labels.value.clubRosterLabel || '成员名册')
const clubMemberNameLabel = computed(() => labels.value.clubMemberNameLabel || '姓名')
const clubMemberNoLabel = computed(() => labels.value.clubMemberNoLabel || '学号')
const clubRosterHint = computed(() => labels.value.clubRosterHint || '')
const allowCarpassParkingMutex = computed(() => !!ticket.allowCarpassParkingMutex)
const parkingOnLabel = computed(() => labels.value.parkingOnLabel || '占用车位日期')
const parkingMutexLabel = computed(() => labels.value.parkingMutexLabel || '同车位同日互斥')
const carpassParkingMutexHint = computed(() => labels.value.carpassParkingMutexHint || '')
const allowEvalUrge = computed(() => !!ticket.allowEvalUrge)
const evalUrgeHint = computed(() => labels.value.evalUrgeHint || '')
const allowContractRenew = computed(() => !!ticket.allowContractRenew)
const renewOnLabel = computed(() => labels.value.renewOnLabel || '续签日期')
const renewNoteLabel = computed(() => labels.value.renewNoteLabel || '续签说明')
const contractRenewHint = computed(() => labels.value.contractRenewHint || '')
const allowContractExpireRemind = computed(() => !!ticket.allowContractExpireRemind)
const contractExpireRemindHint = computed(() => labels.value.contractExpireRemindHint || '')
const contractExpireRemindTitle = computed(() => labels.value.contractExpireRemindTitle || '合同续签提醒')
const allowCertPickupRedeem = computed(() => !!ticket.allowCertPickupRedeem)
const pickupRedeemCodeLabel = computed(() => labels.value.pickupRedeemCodeLabel || '领取核销码')
const pickupRedeemedLabel = computed(() => labels.value.pickupRedeemedLabel || '已核销')
const pickupRedeemHint = computed(() => labels.value.pickupRedeemHint || '')
const allowCertPickupQr = computed(() => !!ticket.allowCertPickupQr)
const pickupQrLabel = computed(() => labels.value.pickupQrLabel || '领取二维码')
const pickupQrHint = computed(() => labels.value.pickupQrHint || '')
const allowVisitorPassPrint = computed(() => !!ticket.allowVisitorPassPrint)
const visitorPassPrintLabel = computed(() => labels.value.visitorPassPrintLabel || '打印通行证')
const visitorPassPrintHint = computed(() => labels.value.visitorPassPrintHint || '')
const allowAttachKeepOld = computed(() => !!ticket.allowAttachKeepOld)
const attachKeepOldLabel = computed(() => labels.value.attachKeepOldLabel || '历史附件')
const attachKeepOldHint = computed(() => labels.value.attachKeepOldHint || '')
const allowCheckinDailyReport = computed(() => !!ticket.allowCheckinDailyReport)
const checkinDailyHint = computed(() => labels.value.checkinDailyHint || '')
const allowEvalCollegeExport = computed(() => !!ticket.allowEvalCollegeExport)
const evalCollegeExportHint = computed(() => labels.value.evalCollegeExportHint || '')
const allowExamPassMin = computed(() => !!ticket.allowExamPassMin)
const examPassMinLabel = computed(() => labels.value.examPassMinLabel || '准入考试及格分')
const examPassMinHint = computed(() => labels.value.examPassMinHint || '')
const allowCheckinSpot = computed(() => !!ticket.allowCheckinSpot)
const checkinSpotHint = computed(() => labels.value.checkinSpotHint || '')
const allowEvalBeforeGrade = computed(() => !!ticket.allowEvalBeforeGrade)
const evalBeforeGradeHint = computed(() => labels.value.evalBeforeGradeHint || '')
const spotCheckToday = ref(false)
function formatClubMembers(raw) {
  try {
    const arr = typeof raw === 'string' ? JSON.parse(raw) : raw
    if (!Array.isArray(arr)) return raw || ''
    return arr.map((x) => `${x.name || ''}${x.studentNo ? `（${x.studentNo}）` : ''}`).join('，')
  } catch {
    return raw || ''
  }
}
function importClubRosterCsv() {
  const text = (form.clubRosterCsv || '').trim()
  if (!text) return
  const rows = text.split(/\r?\n/).map((line) => {
    const parts = line.split(/[,，\t;；]/).map((s) => s.trim())
    return { name: parts[0] || '', studentNo: parts[1] || '' }
  }).filter((x) => x.name)
  if (rows.length) form.clubMembers = rows
}
function isApproveResultStatus(st) {
  return st === 'approved' || st === 'rejected' || st === 'returned'
}
function showRemarkForRow(row) {
  if (!row?.remark) return false
  if (allowSignRemarkVisible.value && isApproveResultStatus(row.status) && row.signRemarkVisible === false) {
    return false
  }
  return true
}
function formatExpenseLines(raw) {
  try {
    const arr = typeof raw === 'string' ? JSON.parse(raw) : raw
    if (!Array.isArray(arr)) return raw || ''
    return arr.map((x) => `${x.category || ''} ${x.amount ?? ''}${x.note ? `（${x.note}）` : ''}`).join('；')
  } catch {
    return raw || ''
  }
}
function formatTripLegs(raw) {
  try {
    const arr = typeof raw === 'string' ? JSON.parse(raw) : raw
    if (!Array.isArray(arr)) return raw || ''
    return arr.map((x) => `${x.on || ''} ${x.from || ''}→${x.via ? `${x.via}→` : ''}${x.to || ''}`).join('；')
  } catch {
    return raw || ''
  }
}
function amountToChinese(n) {
  const num = Number(n)
  if (!Number.isFinite(num) || num < 0) return ''
  const digits = ['零', '壹', '贰', '叁', '肆', '伍', '陆', '柒', '捌', '玖']
  const units = ['', '拾', '佰', '仟']
  const big = ['', '万', '亿']
  const yuan = Math.floor(num + 1e-9)
  const fen = Math.round((num - yuan) * 100)
  if (yuan === 0 && fen === 0) return '零元整'
  let intPart = ''
  if (yuan === 0) {
    intPart = '零'
  } else {
    const s = String(yuan)
    const groups = []
    for (let i = s.length; i > 0; i -= 4) groups.unshift(s.slice(Math.max(0, i - 4), i))
    groups.forEach((g, gi) => {
      let chunk = ''
      let zero = false
      for (let i = 0; i < g.length; i++) {
        const d = Number(g[i])
        const u = units[g.length - 1 - i]
        if (d === 0) {
          zero = true
        } else {
          if (zero) chunk += '零'
          chunk += digits[d] + u
          zero = false
        }
      }
      if (chunk) intPart += chunk + big[groups.length - 1 - gi]
    })
  }
  let out = `${intPart}元`
  if (fen === 0) return `${out}整`
  const jiao = Math.floor(fen / 10)
  const cent = fen % 10
  if (jiao) out += `${digits[jiao]}角`
  if (cent) out += `${digits[cent]}分`
  return out
}
const fleetTollAttachLabel = computed(() => (labels.value.fleetTollAttachLabel || '').trim())
const fleetTollAttachHint = computed(() => (labels.value.fleetTollAttachHint || '').trim())
const promoFeedbackLabel = computed(() => labels.value.promoFeedbackLabel || '投放反馈照片')
const promoFeedbackHint = computed(() => labels.value.promoFeedbackHint || '')
const sealPhotoLabel = computed(() => labels.value.sealPhotoLabel || '用印现场照片')
const sealPhotoHint = computed(() => labels.value.sealPhotoHint || '')
const closeAttachFieldLabel = computed(() =>
  ticket.allowSealClosePhoto
    ? sealPhotoLabel.value
    : ticket.allowPromoFeedback
      ? promoFeedbackLabel.value
      : (labels.value.closeAttachLabel || '结单附件'),
)
const closeAttachHint = computed(() =>
  ticket.allowSealClosePhoto
    ? sealPhotoHint.value
    : ticket.allowPromoFeedback
      ? promoFeedbackHint.value
      : (labels.value.closeAttachHint || ''),
)
const finishAttachFieldLabel = computed(() => {
  if (ticket.requireCloseAttach) return closeAttachFieldLabel.value
  if (ticket.requireReturnAttach) {
    return (labels.value.returnAttachLabel || '').trim() || '归还照片'
  }
  return closeAttachFieldLabel.value
})
const attachFieldLabel = computed(() =>
  fleetTollAttachLabel.value
    || laborAttachLabel.value
    || checkinPhotoLabel.value
    || (labels.value.attachLabel || '').trim()
    || '附件',
)
const attachFieldHint = computed(() =>
  expenseAttachCountHint.value
    || fleetTollAttachHint.value
    || laborAttachHint.value
    || checkinPhotoHint.value
    || (labels.value.homePhotoAttachHint || '').trim()
    || (labels.value.attachHint || '').trim()
    || '',
)
function isPassExpired(row) {
  if (!allowPassExpire.value || !row || !row.passExpireAt) return false
  const t = Date.parse(String(row.passExpireAt).replace('T', ' '))
  return Number.isFinite(t) && Date.now() > t
}
const allowSeatZone = computed(() => !!ticket.allowSeatZone)
const seatZoneLabel = computed(() => labels.value.seatZoneLabel || '座位分区')
const seatZoneHint = computed(() => labels.value.seatZoneHint || '')
const seatZoneOptions = computed(() => {
  const raw = (selectedApplyItem.value && selectedApplyItem.value.seatZones) || ''
  return String(raw)
    .split(/[,，、]/)
    .map((s) => s.trim())
    .filter(Boolean)
})
const allowTicketTransfer = computed(() => !!ticket.allowTicketTransfer)
const ticketTransferLabel = computed(() => labels.value.ticketTransferLabel || '转让名额')
const ticketTransferHint = computed(() => labels.value.ticketTransferHint || '')
const allowTicketWallet = computed(() => !!ticket.allowTicketWallet)
const ticketWalletLabel = computed(() => labels.value.ticketWalletLabel || '我的电子票')
const ticketWalletHint = computed(() => labels.value.ticketWalletHint || '')
const allowPostGallery = computed(() => !!ticket.allowPostGallery)
const postGalleryLabel = computed(() => labels.value.postGalleryLabel || '活动相册')
const postGalleryHint = computed(() => labels.value.postGalleryHint || '')
const requireCreditWritebackAck = computed(() => !!ticket.requireCreditWritebackAck)
const creditWritebackAckLabel = computed(
  () => labels.value.creditWritebackAckLabel || '我已知晓学分认定需另行申请（非自动回写）',
)
const creditWritebackHint = computed(() => labels.value.creditWritebackHint || '')
const creditFromActivityHint = computed(() => labels.value.creditFromActivityHint || '')
const activitySurveyLinkLabel = computed(() => labels.value.activitySurveyLinkLabel || '填写满意度问卷')
const activitySurveyLinkHint = computed(() => labels.value.activitySurveyLinkHint || '')
const visaMaterialHint = computed(() => labels.value.visaMaterialHint || '')
const materialApplyHint = computed(
  () =>
    labels.value.moralMaterialHint
    || labels.value.partyMaterialHint
    || labels.value.partyThoughtHint
    || labels.value.fleetDriverCertHint
    || visaMaterialHint.value
    || '',
)
const priceNoteAckLabel = computed(() => labels.value.priceNoteAckLabel || '我已阅读团体票价说明')
const sponsorAckLabel = computed(() => labels.value.sponsorAckLabel || '我已知晓本场赞助说明')
const planAckLabel = computed(() => labels.value.planAckLabel || '我已查阅培养方案外链')
const prereqAckLabel = computed(() => labels.value.prereqAckLabel || '我确认已具备先修基础')
const tourNoticeAckLabel = computed(() => labels.value.tourNoticeAckLabel || '我已阅读出团天气与须知')
const wishOrderLabel = computed(() => labels.value.wishOrderLabel || '志愿序')
const wishOrderHint = computed(() => labels.value.wishOrderHint || '')
const volunteerRoleLabel = computed(() => labels.value.volunteerRoleLabel || '报名岗位')
const volunteerRoleHint = computed(() => labels.value.volunteerRoleHint || '')
const lateMinutesLabel = computed(() => labels.value.lateMinutesLabel || '迟到分钟数')
const lateMinutesHint = computed(() => labels.value.lateMinutesHint || '')
const volunteerRoleOptions = computed(() => {
  const af = getSchema()?.entities?.archive?.fields || []
  const f = af.find((x) => x && x.key === 'volunteerRole')
  const opts = f && Array.isArray(f.options) ? f.options : ['不限', '引导员', '签到协助', '物资发放', '其它']
  return opts.filter((x) => x && x !== '不限')
})
const oversellGuardHint = computed(() => labels.value.oversellGuardHint || '')
const allowProjectNo = computed(() => !!ticket.allowProjectNo)
const projectNoLabel = computed(() => labels.value.projectNoLabel || '课题号')
const allowProcureRef = computed(() => !!ticket.allowProcureRef)
const procureRefLabel = computed(() => labels.value.procureRefLabel || '申购单号')
const procureToAssetHint = computed(() => labels.value.procureToAssetHint || '')
const allowDualReview = computed(() => !!ticket.allowDualReview)
const dualReviewerALabel = computed(() => labels.value.dualReviewerALabel || '复核人甲')
const dualReviewerBLabel = computed(() => labels.value.dualReviewerBLabel || '复核人乙')
const allowShipFee = computed(() => !!ticket.allowShipFee)
const shipFeeLabel = computed(() => labels.value.shipFeeLabel || '寄件运费（元）')
const allowUtilityNote = computed(() => !!ticket.allowUtilityNote)
const utilityNoteLabel = computed(() => labels.value.utilityNoteLabel || '退宿水电清算备注')
const requirePeerConfirm = computed(
  () => !!ticket.requirePeerConfirm || !!labels.value.bedSwapHint,
)
const peerUsernameLabel = computed(() => labels.value.peerUsernameLabel || '对方学号/用户名')
const peerConfirmHint = computed(() => labels.value.peerConfirmHint || '')
const allowInterviewResult = computed(() => !!ticket.allowInterviewResult)
const interviewResultLabel = computed(() => labels.value.interviewResultLabel || '面试结果')
const interviewResultOptions = computed(() => {
  const opts = labels.value.interviewResultOptions
  return Array.isArray(opts) && opts.length ? opts : ['待定', '通过', '未通过']
})
const allowWrittenScore = computed(() => !!ticket.allowWrittenScore)
const writtenScoreLabel = computed(() => labels.value.writtenScoreLabel || '笔试/机试成绩')
const allowBgCheckNote = computed(() => !!ticket.allowBgCheckNote)
const bgCheckNoteLabel = computed(() => labels.value.bgCheckNoteLabel || '背调备注')
const allowDealAmount = computed(() => !!ticket.allowDealAmount)
const dealAmountLabel = computed(() => labels.value.dealAmountLabel || '成交金额（元）')
const allowNextAction = computed(() => !!ticket.allowNextAction)
const nextActionLabel = computed(() => labels.value.nextActionLabel || '下次行动待办')
const nextActionDoneLabel = computed(() => labels.value.nextActionDoneLabel || '行动已完成')
const allowLeaveProxy = computed(() => !!ticket.allowLeaveProxy)
const leaveProxyLabel = computed(() => labels.value.leaveProxyLabel || '代理人')
const requireReturnDate = computed(() => !!ticket.requireReturnDate)
const returnDateLabel = computed(() => labels.value.returnDateLabel || '返岗日期')
const allowDefenseResult = computed(() => !!ticket.allowDefenseResult)
const defenseResultLabel = computed(() => labels.value.defenseResultLabel || '答辩/评议结果')
const defenseResultOptions = computed(() => {
  const opts = labels.value.defenseResultOptions
  return Array.isArray(opts) && opts.length ? opts : ['通过', '候补', '未通过', '待定']
})
const maskBankAccount = computed(() => !!ticket.maskBankAccount)
const bankAccountLabel = computed(() => labels.value.bankAccountLabel || '银行卡号')
const bankMaskHint = computed(() => labels.value.bankMaskHint || '')
const homeVisitTemplate = computed(() => !!ticket.homeVisitTemplate)
const homeVisitFamilyLabel = computed(() => labels.value.homeVisitFamilyLabel || '家庭情况')
const homeVisitTalkLabel = computed(() => labels.value.homeVisitTalkLabel || '谈话要点')
const homeVisitPlanLabel = computed(() => labels.value.homeVisitPlanLabel || '后续计划')
const requireFeedbackSet = computed(() => !!ticket.requireFeedbackSet)
const feedbackInterestLabel = computed(() => labels.value.feedbackInterestLabel || '客户意向')
const feedbackConcernLabel = computed(() => labels.value.feedbackConcernLabel || '顾虑点')
const feedbackNextLabel = computed(() => labels.value.feedbackNextLabel || '下一步建议')
const allowRecordUrl = computed(() => !!ticket.allowRecordUrl)
const recordUrlLabel = computed(() => labels.value.recordUrlLabel || '带看录音外链')
const requireAppraisal = computed(() => !!ticket.requireAppraisal)
const appraisalCommentLabel = computed(() => labels.value.appraisalCommentLabel || '鉴定评语')
const appraisalGradeLabel = computed(() => labels.value.appraisalGradeLabel || '鉴定等级')
const appraisalGradeOptions = computed(() => {
  const opts = labels.value.appraisalGradeOptions
  return Array.isArray(opts) && opts.length ? opts : ['优秀', '良好', '合格', '不合格']
})
const allowCompanyEval = computed(() => !!ticket.allowCompanyEval)
const allowConfidential = computed(() => !!ticket.allowConfidential)
const confidentialLabel = computed(() => labels.value.confidentialLabel || '保密事件')
const allowAssignDept = computed(() => !!ticket.allowAssignDept)
const assignDeptLabel = computed(() => labels.value.assignDeptLabel || '分拨科室')
const resumeFieldSet = computed(() => !!ticket.resumeFieldSet)
const resumeEduLabel = computed(() => labels.value.resumeEduLabel || '学历')
const resumeExpLabel = computed(() => labels.value.resumeExpLabel || '工作年限')
const resumeSkillLabel = computed(() => labels.value.resumeSkillLabel || '技能摘要')
const companyEvalLabel = computed(() => labels.value.companyEvalLabel || '单位评价')
const bedConstraint = computed(() => !!ticket.bedConstraint)
const closedLoanHint = computed(() => labels.value.closedLoanHint || '')
const offHoursPickupHint = computed(() => labels.value.offHoursPickupHint || '')
const bedReleaseHint = computed(() => labels.value.bedReleaseHint || '')
const archiveSelectPlaceholder = computed(() => {
  if (matchProfileRoom.value) return '请选择本人寝室场次'
  if (bedConstraint.value) return '请选择符合本人性别与年级的床位'
  if (requireClaimCode.value) return '凭取件码匹配待取件'
  if (filterByOwnerToken.value) return '请选择本人相关项'
  return `请选择${archiveLabel.value}`
})
const claimMatchedLine = ref('')
const ownerArchiveItems = computed(() => archiveItems.value)
const claimFilteredArchiveItems = computed(() => {
  const pool = ownerArchiveItems.value
  if (!requireClaimCode.value) return pool
  const code = normRoomToken(form.remark)
  // 未填取件码：展示本人件池（按手机筛过）；填码后再收窄
  if (!code) return pool
  return (pool || []).filter((it) => {
    const isbn = normRoomToken(it?.isbn)
    const title = normRoomToken(it?.title)
    return isbn === code || title === code || isbn.includes(code) || title.includes(code)
  })
})

function claimOptionLabel(it) {
  if (!it) return ''
  const title = it.title || ''
  const author = it.author || ''
  return author ? `${title}（${author}）` : title
}

function matchClaimFromRemark() {
  if (!requireClaimCode.value) return
  const code = normRoomToken(form.remark)
  if (code.length < 4) {
    claimMatchedLine.value = ''
    return
  }
  const hits = (ownerArchiveItems.value || []).filter((it) => {
    const isbn = normRoomToken(it?.isbn)
    const title = normRoomToken(it?.title)
    return isbn === code || title === code || isbn.includes(code) || title.includes(code)
  })
  if (hits.length === 1) {
    form.itemId = hits[0].id
    const t = hits[0].title || ''
    const codeHint = hits[0].isbn ? String(hits[0].isbn).trim() : ''
    claimMatchedLine.value = codeHint && codeHint !== t ? `${t} / ${codeHint}` : t
  } else {
    claimMatchedLine.value = ''
  }
}

function onClaimRemarkInput() {
  if (!requireClaimCode.value) return
  if (normRoomToken(form.remark).length >= 4) matchClaimFromRemark()
  else claimMatchedLine.value = ''
}
const pickDateRange = computed(() => !!ticket.pickDateRange)
const showFollowCols = computed(() => ticketShowsFollowCols())
const channelOptions = computed(() => followChannelOptions())
const channelPlaceholder = computed(
  () => ticket.contactChannelPlaceholder || '请选择',
)
const pageLead = computed(() => {
  const custom = labels.value.myTicketsPageLead
  if (custom) return custom
  if (applyFromList.value) {
    return `在此${applyVerb.value}并跟踪进度。`
  }
  if (archiveMode.value) {
    return `在检索页${applyVerb.value}后，可在此查看进度。`
  }
  return `提交${plural.value}并查看受理进度。`
})
const browseCta = computed(
  () => labels.value.myTicketsBrowseCta || `去检索${applyVerb.value}`,
)
const appliedAtLabel = computed(
  () => labels.value.ticketAppliedAtLabel || `${applyVerb.value}于`,
)
const emptyText = computed(() => {
  if (applyFromList.value) {
    return labels.value.myTicketsEmpty || `还没有记录，点击右上角${applyVerb.value}。`
  }
  if (archiveMode.value) {
    return (
      labels.value.myTicketsEmptyArchive
      || `还没有记录，请先在检索页${applyVerb.value}。`
    )
  }
  return labels.value.myTicketsEmpty || '还没有记录，点击右上角提交。'
})
const dueLabel = computed(() => ticketDueLabel())
const fineLabel = computed(() => ticketFineLabel())
const checkinLabel = computed(() => ticketCheckinLabel())
const channelLabel = computed(() => followChannelLabel())
const nextAtLabel = computed(() => nextFollowLabel())
const richRemark = computed(() => !!ticket.richRemark)
const attachByLeaveTypeOn = computed(() => !!ticket.attachByLeaveType)
const sickAttachHint = computed(() => labels.value.sickAttachHint || '')
const allowMakeupApply = computed(() => !!ticket.allowMakeupApply)
const makeupApplyLabel = computed(() => labels.value.makeupApplyLabel || '补考报名')
const makeupApplyHint = computed(() => labels.value.makeupApplyHint || '')
const makeupMode = ref(false)
const applyDialogTitle = computed(() => {
  if (makeupMode.value) return makeupApplyLabel.value
  return verbs.value.apply || '提交'
})
const selectedTypeName = computed(() => {
  const id = form.typeId
  if (id == null || id === '') return ''
  const hit = (types.value || []).find((t) => String(t.id) === String(id))
  return hit?.name || hit?.label || hit?.title || ''
})
const requireAttach = computed(() => {
  if (ticket.requireAttach) return true
  if (!attachByLeaveTypeOn.value) return false
  return /病假|医疗|住院/.test(selectedTypeName.value)
})
const requireMaterial = computed(() => !!ticket.requireMaterialChecklist)
const requireClaimProof = computed(() => !!ticket.requireClaimProof || hasCap('claim_proof'))
const matRef = ref(null)
const proofRef = ref(null)
const proofDlg = reactive({ visible: false, row: null, loading: false })
const returnDlg = reactive({
  visible: false,
  row: null,
  attachUrl: '',
  loading: false,
  faultReason: '',
  closeSummary: '',
  partsNote: '',
  mileageKm: null,
  fuelNote: '',
  compHours: null,
  returnFuel: null,
  violationPerson: '',
  returnFail: false,
  returnNote: '',
})
const objectionDlg = reactive({ visible: false, row: null, note: '', loading: false })
const allowRating = computed(() => !!ticket.allowRating)
const allowUserUrge = computed(() => !!ticket.allowUserUrge)
const allowCancelUrge = computed(() => !!ticket.allowCancelUrge)
const allowCancelDispatched = computed(() => !!ticket.allowCancelDispatched)
const allowQuote = computed(() => !!ticket.allowQuote)
const preferSlotOn = computed(() => !!ticket.preferredSlot)
const preferredSlotOn = preferSlotOn
const nightUrgentOn = computed(() => !!ticket.nightUrgent)
const progressSubscribeOn = computed(() => !!ticket.progressSubscribe)
const allowPublicArea = computed(() => !!ticket.allowPublicArea)
const allowAssetCode = computed(
  () => !!ticket.allowAssetCode || !!labels.value.equipQrPrintHint,
)
const allowTicketDraft = computed(() => !!ticket.allowTicketDraft)
const allowPartsNote = computed(() => !!ticket.allowPartsNote)
const allowFollowRateOn = computed(() => !!ticket.allowFollowRate)
const addressReuseOn = computed(() => !!ticket.addressReuse || !!ticket.repairThicken)
const allowAudioRemark = computed(() => !!ticket.allowAudioRemark || !!ticket.repairThicken)
const requireFaultReason = computed(() => !!ticket.requireFaultReason)
const requireCloseSummary = computed(() => !!ticket.requireCloseSummary)
const requireCloseAttach = computed(() => !!ticket.requireCloseAttach)
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
const urgeLabel = computed(() => labels.value.urgeLabel || '催办')
const cancelUrgeLabel = computed(() => labels.value.cancelUrgeLabel || '撤销催办')
const printTicketLabel = computed(() => labels.value.printTicketLabel || '打印工单')
const certFormPrintHint = computed(() => labels.value.certFormPrintHint || '')
const sealFormPrintHint = computed(() => labels.value.sealFormPrintHint || '')
const projMidFormPrintHint = computed(() => labels.value.projMidFormPrintHint || '')
const ethicOpinionPrintHint = computed(() => labels.value.ethicOpinionPrintHint || '')
const formPrintHint = computed(
  () =>
    certFormPrintHint.value
    || sealFormPrintHint.value
    || projMidFormPrintHint.value
    || ethicOpinionPrintHint.value
    || '',
)
const ticketNoHint = computed(() => labels.value.ticketNoHint || '')
const slaPageHint = computed(() => labels.value.slaPageHint || '')
const selfHelpHint = computed(() => labels.value.selfHelpHint || '')
const addressReuseHint = computed(() => labels.value.addressReuseHint || '')
const rateInviteHint = computed(() => labels.value.rateInviteHint || '办结后可对本次服务评分。')
const myTicketHintKeys = MY_TICKETS_HINT_KEYS
const rankSwitchHint = computed(() => labels.value.rankSwitchHint || '')
const rankSwitchOn = computed(() => !!rankSwitchHint.value)
const rankScope = ref('class')
const leaveSplitHint = computed(() => labels.value.leaveSplitHint || '')
const leaveOverlapHint = computed(() => labels.value.leaveOverlapHint || '')
const selfExportOn = computed(
  () =>
    !!(labels.value.monthExportHint
      || labels.value.checkExportHint
      || labels.value.stuNoMaskExportHint),
)
const selfExportLabel = computed(
  () => labels.value.monthExportHint || labels.value.checkExportHint || '导出我的记录',
)

function exportMineCsv() {
  if (!list.value.length) {
    ElMessage.warning('暂无可导出记录')
    return
  }
  const headers = ['编号', '标题', '状态', '申请时间', '完成时间']
  const data = list.value.map((row) => [
    row.id,
    row.title || '',
    statusText(row),
    row.applyAt || '',
    row.returnAt || '',
  ])
  downloadCsv(`my_tickets_${Date.now()}.csv`, headers, data)
  ElMessage.success(`已导出 ${data.length} 条`)
}
const lastLocations = ref([])
const rateFollowMode = ref(false)
const faultReasonLabel = computed(() => labels.value.faultReasonLabel || '故障原因')
const closeSummaryLabel = computed(() => labels.value.closeSummaryLabel || '处理过程摘要')
const preferredSlotLabel = computed(() => labels.value.preferredSlotLabel || '期望上门时段')
const allowMeetingPlace = computed(() => !!ticket.allowMeetingPlace)
const meetingPlaceLabel = computed(() => labels.value.meetingPlaceLabel || '约定面交地点')
const allowEmergencyContact = computed(() => !!ticket.allowEmergencyContact)
const emergencyContactLabel = computed(() => labels.value.emergencyContactLabel || '紧急联系人')
const emergencyPhoneLabel = computed(() => labels.value.emergencyPhoneLabel || '紧急联系电话')
const claimAutoOffHint = computed(() => labels.value.claimAutoOffHint || '')
const expireOffHint = computed(() => labels.value.expireOffHint || '')
const stockTightHint = computed(() => labels.value.stockTightHint || '')
const cancelBeforeHint = computed(() => labels.value.cancelBeforeHint || '')
const claimCooldownHint = computed(() => labels.value.claimCooldownHint || '')
const creditCapHint = computed(() => labels.value.creditCapHint || '')
const creditWarnHint = computed(() => labels.value.creditWarnHint || '')
const maxDropHint = computed(() => labels.value.maxDropHint || '')
const prereqHint = computed(() => labels.value.prereqHint || '')
const courseKindHint = computed(() => labels.value.courseKindHint || '')
const minGroupHint = computed(() => labels.value.minGroupHint || '')
const waitlistPromoteHint = computed(() => labels.value.waitlistPromoteHint || '')
const applySuccessInboxTitle = computed(() => labels.value.applySuccessInboxTitle || '')
const applySuccessInboxBody = computed(() => labels.value.applySuccessInboxBody || '')
const rejectReasonRequired = computed(() => labels.value.rejectReasonRequired || '请填写驳回原因')
const publicAreaLabel = computed(() => labels.value.publicAreaLabel || '公共区域')
const assetCodeLabel = computed(() => labels.value.assetCodeLabel || '资产编号')
const partsNoteLabel = computed(() => labels.value.partsNoteLabel || '备件/耗材出库')
const partsWarnHint = computed(() => labels.value.partsWarnHint || '选填出库说明')
const faultReasons = computed(() => {
  const list = ticket.faultReasons
  return Array.isArray(list) && list.length ? list : ['线路故障', '漏水渗水', '其他']
})
const allowCheckin = computed(() => !!ticket.allowCheckin)
const allowRenew = computed(() => !!(ticket.allowRenew || hasCap('loan_renew')))
const allowBookHold = computed(() => !!(ticket.allowBookHold || hasCap('book_hold')))
const allowBookLost = computed(() => !!(ticket.allowBookLost || hasCap('book_lost')))
// 域外字段必须走 allow* 开关分支：未开的域不得渲染数量/到期/罚金列（1014/12/6 同族）
const allowQty = computed(() => !!ticket.allowQty)
const showDueCols = computed(
  () => !!(ticket.pickLoanPeriod || ticket.dueLabel || allowRenew.value || allowBookHold.value),
)
const showFineCols = computed(() => !!(ticket.fineLabel || ticket.dueLabel || allowRenew.value))
const requireReturnAttach = computed(() => !!ticket.requireReturnAttach)
const renewVerb = computed(() => verbs.value.renew || labels.value.renewVerb || '续借')
const lostVerb = computed(() => verbs.value.reportLost || labels.value.bookLostVerb || '申报丢失')
const claimHoldVerb = computed(() => verbs.value.claimHold || labels.value.bookHoldClaimVerb || '确认借阅')
const maxRenew = computed(() => {
  const n = Number(ticket.maxRenew)
  return Number.isFinite(n) && n > 0 ? n : 1
})
const passCodeLabel = computed(() => ticket.passCodeLabel || '通行码')
const codeQrOn = computed(() => hasCap('code_qr'))
const showPickup = computed(() => hasTrait('pickupFlow'))
const approveEndsFlow = computed(() => !!ticket.approveEndsFlow)
const showPriorityCols = computed(() => ticketShowsPriorityCols())

/** 驿站/失物核销流：approved/overdue 即终态，不展示「取消取件」 */
function canFinish(row) {
  if (!row) return false
  if (approveEndsFlow.value && showPickup.value) return false
  // 查寝等：returned=已签到，通过后只走口令签到，不走「撤销/完结」误标已签到
  if (allowCheckin.value && row.status === 'approved' && states.value.returned === '已签到') {
    return false
  }
  return row.status === 'approved' || row.status === 'overdue'
}

function canReportLost(row) {
  if (!allowBookLost.value || !row) return false
  return row.status === 'approved' || row.status === 'overdue'
}

const finishVerb = computed(() => {
  if (ticket.applicantCompleteOnly) return '确认完结'
  return verbs.value.return || '完成'
})

function canUrge(row) {
  if (!allowUserUrge.value || !row) return false
  if (row.rating) return false
  return row.status === 'approved' || row.status === 'overdue' || row.status === 'paused'
}

function canCancelUrge(row) {
  if (!allowCancelUrge.value || !row) return false
  return !!(row.urgeCount && Number(row.urgeCount) > 0 && !row.urgeCancelled)
}

function canCancelDispatched(row) {
  if (!allowCancelDispatched.value || !row) return false
  return row.status === 'approved' || row.status === 'overdue' || row.status === 'paused'
}

function canConfirmQuote(row) {
  if (!allowQuote.value || !row) return false
  if (row.quoteConfirmed) return false
  return row.quoteYuan != null && Number(row.quoteYuan) > 0
}

async function doUrge(row) {
  await http.post(`/api/tickets/${row.id}/urge`)
  ElMessage.success('已催办，处理人将收到站内提醒')
  load()
}

async function doCancelUrge(row) {
  await http.post(`/api/tickets/${row.id}/cancel-urge`)
  ElMessage.success('已撤销催办')
  load()
}

async function doCancelDispatched(row) {
  const { value } = await ElMessageBox.prompt('请填写取消原因', '取消已派单', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    inputPattern: /\S+/,
    inputErrorMessage: '请填写原因',
  })
  await http.post(`/api/tickets/${row.id}/cancel-dispatched`, { reason: value })
  ElMessage.success('已取消')
  load()
}

async function doConfirmQuote(row) {
  await ElMessageBox.confirm(
    `确认维修报价 ¥${row.quoteYuan}${row.materialFeeYuan ? `（材料费 ¥${row.materialFeeYuan}）` : ''}？`,
    '确认报价',
  )
  await http.post(`/api/tickets/${row.id}/confirm-quote`, { payMaterial: !!row.materialFeeYuan })
  ElMessage.success('已确认报价')
  load()
}

function printTicket(row) {
  const ok = printTicketDocument(row, {
    ticket,
    labels: labels.value,
    statusText,
    personLabel: (r) => r?.applicantName || r?.nickname || r?.username || '',
    remarkText: (r) => String(r || '').replace(/<[^>]+>/g, ''),
  })
  if (!ok) ElMessage.warning('请允许弹窗后重试')
}

function canShowWallet(row) {
  return allowTicketWallet.value && row && ['approved', 'returned'].includes(String(row.status || ''))
}
function openWallet(row) {
  wallet.row = row
  wallet.visible = true
}
function canTransfer(row) {
  return allowTicketTransfer.value && row && String(row.status || '') === 'approved'
}
function openTransfer(row) {
  transfer.row = row
  transfer.toUsername = ''
  transfer.visible = true
}
function postGalleryUrls(row) {
  const g = row && row.postGalleryImages
  return Array.isArray(g) ? g.filter(Boolean) : []
}
function canShowPostGallery(row) {
  return allowPostGallery.value && row && ['returned', 'completed'].includes(String(row.status || ''))
}
function openPostGallery(row) {
  postGallery.row = row
  postGallery.images = [...postGalleryUrls(row)]
  postGallery.visible = true
}
async function onPostGalleryUpload(option) {
  if (postGallery.images.length >= 9) {
    ElMessage.warning('最多上传 9 张')
    return
  }
  const fd = new FormData()
  fd.append('file', option.file)
  const res = await http.post('/api/upload', fd)
  const url = res.data?.url
  if (url) postGallery.images.push(url)
}
async function submitPostGallery() {
  if (!postGallery.row) return
  postGallery.loading = true
  try {
    await http.post(`/api/tickets/${postGallery.row.id}/post-gallery`, {
      images: postGallery.images,
    })
    ElMessage.success('相册已保存')
    postGallery.visible = false
    load()
  } finally {
    postGallery.loading = false
  }
}
function canAckCreditWriteback(row) {
  return (
    requireCreditWritebackAck.value
    && row
    && !row.creditWritebackAck
    && ['returned', 'completed', 'approved'].includes(String(row.status || ''))
  )
}
async function ackCreditWriteback(row) {
  await http.post(`/api/tickets/${row.id}/credit-writeback-ack`)
  ElMessage.success('已确认')
  load()
}
function canOpenActivitySurvey(row) {
  const sid = Number(row?.surveyFormId || 0)
  return sid > 0 && row && ['returned', 'completed'].includes(String(row.status || ''))
}
function openActivitySurvey(row) {
  const sid = Number(row?.surveyFormId || 0)
  if (!sid) return
  if (activitySurveyLinkHint.value) ElMessage.info(activitySurveyLinkHint.value)
  window.location.hash = `#/survey/fill/${sid}`
}
async function submitTransfer() {
  if (!transfer.row) return
  const to = (transfer.toUsername || '').trim()
  if (!to) {
    ElMessage.warning('请填写接收账号')
    return
  }
  transfer.loading = true
  try {
    await http.post(`/api/tickets/${transfer.row.id}/transfer`, { toUsername: to })
    ElMessage.success('已转让')
    transfer.visible = false
    load()
  } finally {
    transfer.loading = false
  }
}

function leaveSplitText(row) {
  const a = row.startAt || row.periodStart || ''
  const b = row.endAt || row.periodEnd || ''
  if (!a || !b) return ''
  const da = String(a).slice(0, 10)
  const db = String(b).slice(0, 10)
  if (!da || !db || da === db) return ''
  return `${da} 至 ${db}`
}

function canWithdraw(row) {
  if (!row) return false
  if (row.status === 'pending' || row.status === 'pending_mid'
    || row.status === 'pending_final' || row.status === 'waitlisted'
    || row.status === 'verifying') return true
  return !!(allowBookHold.value && (row.status === 'held' || row.status === 'hold_ready'))
}

function canMoralObjection(row) {
  if (!allowMoralObjection.value || !row) return false
  if (row.status !== 'approved') return false
  if (row.objectionAt || (row.objectionNote || '').trim()) return false
  const due = String(row.objectionDueAt || '').trim()
  if (due.length >= 10) {
    const today = new Date()
    const ymd = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`
    if (ymd > due.slice(0, 10)) return false
  }
  return true
}

function openMoralObjection(row) {
  objectionDlg.row = row
  objectionDlg.note = ''
  objectionDlg.visible = true
}

async function submitMoralObjection() {
  if (!objectionDlg.row) return
  if (!(objectionDlg.note || '').trim()) {
    ElMessage.warning(`请填写${moralObjectionLabel.value}`)
    return
  }
  objectionDlg.loading = true
  try {
    await http.post(`/api/tickets/${objectionDlg.row.id}/objection`, { note: objectionDlg.note.trim() })
    ElMessage.success('已提交')
    objectionDlg.visible = false
    load()
  } finally {
    objectionDlg.loading = false
  }
}

async function copyLastYear() {
  try {
    const res = await http.get('/api/tickets/last-approved-mine')
    const d = res.data?.data || res.data || {}
    if (!(d.remark || d.attachUrl)) {
      ElMessage.warning('没有找到上年已通过的材料，请直接填写')
      return
    }
    if (d.remark) form.remark = d.remark
    if (d.attachUrl) form.attachUrl = d.attachUrl
    ElMessage.success('已带入上年材料，请核对后提交')
  } catch (e) {
    ElMessage.warning('没有找到上年已通过的材料，请直接填写')
  }
}

function canSubmitProof(row) {
  return !!requireClaimProof.value && !!row
    && (row.status === 'pending' || row.status === 'verifying')
}

function openProof(row) {
  proofDlg.row = row
  proofDlg.visible = true
  proofDlg.loading = false
  if (proofRef.value) proofRef.value.reset()
}

async function submitProof() {
  if (!proofDlg.row) return
  const p = proofRef.value?.payload?.() || {}
  if (!p.proofContent) {
    ElMessage.warning('请填写凭证内容')
    return
  }
  proofDlg.loading = true
  try {
    await http.post('/api/lost/proof', {
      claimId: proofDlg.row.id,
      proofType: p.proofType,
      proofContent: p.proofContent,
    })
    ElMessage.success('凭证已提交，等待核验')
    proofDlg.visible = false
    await load()
  } finally {
    proofDlg.loading = false
  }
}

function canRate(row) {
  if (!allowRating.value || !row) return false
  const r = row.rating
  if (!(r == null || r === 0 || r === '0' || r === '')) return false
  if (row.status === 'returned') return true
  return !!(approveEndsFlow.value && row.status === 'approved')
}

function canFollowRate(row) {
  if (!allowFollowRateOn.value || !row) return false
  if (!row.rating || row.followRated) return false
  if (row.status === 'returned') return true
  return !!(approveEndsFlow.value && row.status === 'approved')
}

function openRate(row, follow = false) {
  rateRow.value = row
  rateFollowMode.value = !!follow
  rateVisible.value = true
}

function reuseLastLocation() {
  if (lastLocations.value[0]) form.location = lastLocations.value[0]
}

async function refreshAddressBook() {
  if (!addressReuseOn.value) {
    lastLocations.value = []
    return
  }
  try {
    const res = await http.get('/api/tickets', { params: { page: 1, size: 50 } })
    const rows = res.data?.list || []
    const seen = new Set()
    const out = []
    for (const r of rows) {
      const loc = String(r.location || '').trim()
      if (!loc || seen.has(loc)) continue
      seen.add(loc)
      out.push(loc)
      if (out.length >= 8) break
    }
    lastLocations.value = out
  } catch {
    lastLocations.value = []
  }
}

async function onAudioUpload(opt) {
  const fd = new FormData()
  fd.append('file', opt.file)
  const res = await http.post('/api/upload', fd)
  form.audioUrl = res.data?.url || res.data?.data?.url || ''
  if (!form.audioUrl) ElMessage.warning('上传失败')
}

function statusText(rowOrStatus) {
  const row = rowOrStatus && typeof rowOrStatus === 'object' ? rowOrStatus : null
  const s = row ? row.status : rowOrStatus
  // 口令签到成功后须显示「已签到」（status 可能仍为 approved，或已推进到 returned）
  if (row && row.checkedInAt) return '已签到'
  return ticketStatusLabel(s, states.value[s] || s)
}
function tagType(s) {
  return ticketTagType(s)
}

function holdSecondsLeft(row) {
  if (!row?.holdExpireAt) return null
  return secondsUntil(row.holdExpireAt, nowMs.value)
}

function holdCountdownText(row) {
  const sec = holdSecondsLeft(row)
  if (sec == null) return ''
  if (sec <= 0) return '已过期'
  return `剩 ${formatCountdownClock(sec)}`
}

async function copyPass(code) {
  const text = String(code || '').trim()
  if (!text) return
  try {
    await navigator.clipboard.writeText(text)
    ElMessage.success('已复制')
  } catch {
    ElMessage.info(text)
  }
}

function canCheckin(row) {
  if (!allowCheckin.value || !row) return false
  if (row.status !== 'approved') return false
  return !row.checkedInAt
}

function canRenew(row) {
  if (!allowRenew.value || !row) return false
  if (row.status !== 'approved' && row.status !== 'overdue') return false
  if (!row.dueAt) return false
  const used = Number(row.renewCount) || 0
  return used < maxRenew.value
}

function canClaimHold(row) {
  return !!(allowBookHold.value && row && row.status === 'hold_ready')
}

function pickupPending(row) {
  if (!showPickup.value || !row || row.pickupAt) return false
  return row.status === 'approved' || row.status === 'overdue'
}

const list = ref([])
const total = ref(0)
const page = ref(1)
const size = ref(10)
const status = ref(null)
const visible = ref(false)
const lookup = reactive({
  enabled: false,
  siteLabel: '楼栋',
  unitLabel: '房间',
  typeLabel: '类型',
})
const sites = ref([])
const units = ref([])
const types = ref([])
const archiveItems = ref([])
const form = reactive({
  title: '',
  location: '',
  remark: '',
  attachUrl: '',
  typeId: null,
  siteId: null,
  roomId: null,
  itemId: null,
  period: null,
  contactChannel: '',
  nextFollowAt: '',
  weekNo: null,
  interviewPlace: '',
  priority: '普通',
  contactPhone: '',
  proxyName: '',
  proxyPhone: '',
  depositYuan: null,
  pickupPlace: '',
  emergencyContact: '',
  emergencyPhone: '',
  noticeAck: false,
  trainingAck: false,
  insuranceAck: false,
  meetingAck: false,
  inviteCode: '',
  priceNoteAck: false,
  sponsorAck: false,
  planAck: false,
  prereqAck: false,
  tourNoticeAck: false,
  wishOrder: 1,
  volunteerRole: '',
  companionNames: '',
  pickupMethod: '',
  mailAddress: '',
  certUrgent: false,
  sealCopies: 1,
  bindNote: '',
  invoiceCount: 1,
  fineYuan: null,
  visitorCount: 0,
  awardCertNo: '',
  vendorQuotes: '',
  driverName: '',
  passengerNames: '',
  laborPlace: '',
  effectiveOn: '',
  docRev: '',
  workStart: '',
  workEnd: '',
  issueCopies: 1,
  signParties: [],
  trainHours: null,
  memberChangeNote: '',
  procureAmount: null,
  exceptionType: '',
  visitPurpose: '',
  rectifyNote: '',
  fundUseYuan: null,
  fundUseNote: '',
  visitOn: '',
  plagiarismUrl: '',
  partyStage: '',
  stageOn: '',
  observeOn: '',
  observeNote: '',
  scheduleImpactNote: '',
  contractAmount: null,
  expenseLines: [{ category: '', amount: null, note: '' }],
  tripLegs: [{ from: '', via: '', to: '', on: '' }],
  clubMembers: [{ name: '', studentNo: '' }],
  clubRosterCsv: '',
  parkingOn: '',
  renewOn: '',
  renewNote: '',
  changeLogNote: '',
  seatZone: '',
  projectNo: '',
  procureRefNo: '',
  dualReviewerA: '',
  dualReviewerB: '',
  shipFeeYuan: null,
  utilityNote: '',
  peerUsername: '',
  interviewResult: '',
  writtenScore: null,
  bgCheckNote: '',
  dealAmountYuan: null,
  nextAction: '',
  nextActionDone: false,
  returnDate: '',
  defenseResult: '',
  bankAccount: '',
  homeVisitFamily: '',
  homeVisitTalk: '',
  homeVisitPlan: '',
  feedbackInterest: '',
  feedbackConcern: '',
  feedbackNext: '',
  recordUrl: '',
  appraisalComment: '',
  appraisalGrade: '',
  companyEval: '',
  preferredSlot: '',
  addressType: '',
  nightUrgent: false,
  assetCode: '',
  subscribeProgress: false,
  audioUrl: '',
  confidential: false,
  assignDept: '',
  resumeEdu: '',
  resumeExp: '',
  resumeSkill: '',
})

const selectedApplyItem = computed(() => {
  const id = form.itemId
  if (!id) return null
  return (archiveItems.value || []).find((it) => Number(it.id) === Number(id)) || null
})
const applyItemNotes = computed(() => {
  const it = selectedApplyItem.value || {}
  return {
    sponsor: String(it.sponsorNote || '').trim(),
    price: String(it.groupPriceNote || '').trim(),
    room: String(it.singleRoomNote || '').trim(),
    planUrl: String(it.planUrl || '').trim(),
    prereqCode: String(it.prereqCode || '').trim(),
    weather: String(it.weatherNote || '').trim(),
    feeYuan: it.feeYuan,
  }
})
const needPriceNoteAck = computed(
  () => requirePriceNoteAck.value && !!(applyItemNotes.value.price || applyItemNotes.value.room),
)
const needSponsorAck = computed(
  () => requireSponsorAck.value && !!applyItemNotes.value.sponsor,
)
const needPlanAck = computed(
  () => requirePlanAck.value && !!applyItemNotes.value.planUrl,
)
const needPrereqAck = computed(
  () => requirePrereqAck.value && !!applyItemNotes.value.prereqCode,
)
const needTourNoticeAck = computed(
  () => requireTourNoticeAck.value && !!applyItemNotes.value.weather,
)
watch(
  () => form.itemId,
  () => {
    form.priceNoteAck = false
    form.sponsorAck = false
    form.planAck = false
    form.prereqAck = false
    form.tourNoticeAck = false
    form.wishOrder = 1
    form.volunteerRole = ''
    const fee = Number(applyItemNotes.value.feeYuan)
    if (allowDeposit.value && Number.isFinite(fee) && fee > 0) {
      form.depositYuan = fee
    }
  },
)

const rateVisible = ref(false)
const rateRow = ref(null)
const checkinVisible = ref(false)
const checkinLoading = ref(false)
const checkinRow = ref(null)
const checkinCode = ref('')
const checkinLateMinutes = ref(0)
const progressVisible = ref(false)
const progressId = ref(null)
const ccComment = reactive({
  visible: false,
  loading: false,
  row: null,
  text: '',
})

function canCcComment(row) {
  if (!allowApproveCcComment.value || !row) return false
  const me = (localStorage.getItem('username') || '').trim().toLowerCase()
  if (!me) return false
  const raw = String(row.ccUsernames || '')
  return raw.split(/[,;\s]+/).some((p) => p.trim().toLowerCase() === me)
}

function openCcComment(row) {
  ccComment.row = row
  ccComment.text = ''
  ccComment.visible = true
}

async function submitCcComment() {
  if (!ccComment.row) return
  const text = (ccComment.text || '').trim()
  if (!text) {
    ElMessage.warning('请填写评论')
    return
  }
  ccComment.loading = true
  try {
    await http.post(`/api/tickets/${ccComment.row.id}/cc-comment`, { comment: text })
    ElMessage.success('已提交')
    ccComment.visible = false
    load()
  } finally {
    ccComment.loading = false
  }
}

async function loadLookup() {
  try {
    const meta = await http.get('/api/lookups/meta')
    const m = meta.data || meta
    Object.assign(lookup, {
      enabled: !!m.enabled,
      siteLabel: m.siteLabel || '楼栋',
      unitLabel: m.unitLabel || '房间',
      typeLabel: m.typeLabel || '类型',
    })
    if (!lookup.enabled) return
    const [sRes, tRes] = await Promise.all([
      http.get('/api/lookups/sites'),
      http.get('/api/lookups/types'),
    ])
    sites.value = sRes.data || sRes || []
    types.value = tRes.data || tRes || []
  } catch {
    lookup.enabled = false
  }
}

async function loadArchiveItems() {
  if (!applyFromList.value) return
  try {
    const res = await http.get('/api/archive', { params: { page: 1, size: 100 } })
    let list = res.data?.list || res.list || []
    let profile = null
    if (matchProfileRoom.value || filterByOwnerToken.value) {
      try {
        const me = await http.get('/api/profile')
        profile = me.data || {}
      } catch {
        profile = {}
      }
    }
    if (matchProfileRoom.value) {
      const extras = profile?.extras || {}
      const opts = matchProfileOpts.value
      if (!(extras[opts.buildingKey] || '').trim() || !(extras[opts.roomKey] || '').trim()) {
        ElMessage.warning(matchProfileNeedMessage.value)
        archiveItems.value = []
        return
      }
      list = filterArchiveByProfileRoom(list, extras, opts)
      if (!list.length) {
        ElMessage.warning(matchProfileDenyMessage.value)
      }
    }
    if (filterByOwnerToken.value) {
      const token = ownerTokenFromProfile(profile || {}, ownerTokenSource.value)
      const strict = ownerTokenStrict.value
      if (strict && (!token || token.length < 4)) {
        ElMessage.warning(
          ownerTokenSource.value === 'phone'
            ? '请先在个人资料填写手机号以查看本人件'
            : '请先在个人资料填写学号以查看本人相关项',
        )
        archiveItems.value = []
        return
      }
      list = filterArchiveByOwnerToken(list, token, { strict })
      if (strict && !list.length) {
        ElMessage.warning('暂无匹配到本人待取件，请核对手机号或取件码')
      }
    }
    archiveItems.value = list
  } catch {
    archiveItems.value = []
  }
}

async function onSiteChange() {
  form.roomId = null
  units.value = []
  if (!form.siteId) return
  const res = await http.get('/api/lookups/units', { params: { siteId: form.siteId } })
  units.value = res.data || res || []
}

/** 报修壳：资料已有楼栋/房间时预填 lookup（可改选；比对复用 profileRoomMatch）。 */
async function prefillLookupFromProfile() {
  if (!lookup.enabled || !sites.value.length) return
  let extras = {}
  try {
    const me = await http.get('/api/profile')
    extras = me.data?.extras || me.extras || {}
  } catch {
    return
  }
  const { building, room } = profileSiteRoomFromExtras(extras)
  if (!building || !room) return
  const site = matchSiteByBuilding(sites.value, building, true)
  if (!site) return
  form.siteId = site.id
  await onSiteChange()
  const unit = matchUnitByRoom(units.value, building, room, site.name, true)
  if (unit) form.roomId = unit.id
}

async function onAttach(opt) {
  const fd = new FormData()
  fd.append('file', opt.file)
  const res = await http.post('/api/upload', fd)
  form.attachUrl = res.data.url
  ElMessage.success('附件已上传')
}

async function resubmitTicket(row) {
  try {
    let attachUrl = ''
    if (allowAttachKeepOld.value) {
      try {
        const { value } = await ElMessageBox.prompt(
          attachKeepOldHint.value || '如需更换附件可粘贴新地址，留空则沿用原附件',
          attachKeepOldLabel.value,
          {
            confirmButtonText: '重新提交',
            cancelButtonText: '取消',
            inputPlaceholder: '附件地址（可选）',
            inputValue: row.attachUrl || '',
          },
        )
        attachUrl = String(value || '').trim()
      } catch {
        return
      }
    }
    await http.post(`/api/tickets/${row.id}/resubmit`, {
      remark: '',
      attachUrl: attachUrl || undefined,
    })
    ElMessage.success('已重新提交，等待受理')
    await load()
  } catch (e) {
    ElMessage.error(e?.response?.data?.message || e?.message || '重新提交失败')
  }
}

async function openAttachRevs(row) {
  try {
    const res = await http.get(`/api/tickets/${row.id}/attach-revs`)
    const list = res.data?.data || res.data || []
    if (!list.length) {
      ElMessage.info('还没有历史附件')
      return
    }
    const lines = list
      .map((x, i) => `${i + 1}. ${x.createdAt || ''} ${x.attachUrl || ''}`)
      .join('\n')
    await ElMessageBox.alert(lines, attachKeepOldLabel.value, { confirmButtonText: '关闭' })
  } catch (e) {
    ElMessage.error(e?.response?.data?.message || e?.message || '加载失败')
  }
}

function printVisitorPass(row) {
  if (!row?.passCode) return
  const w = window.open('', '_blank', 'width=420,height=560')
  if (!w) {
    ElMessage.warning('请允许弹窗后重试')
    return
  }
  const hint = visitorPassPrintHint.value || ''
  w.document.write(
    `<!doctype html><html><head><meta charset="utf-8"><title>${visitorPassPrintLabel.value}</title>` +
      '<style>body{font-family:sans-serif;text-align:center;padding:24px}h1{font-size:18px}' +
      '.code{font-size:22px;font-weight:700;letter-spacing:.08em;margin:16px 0}' +
      '.hint{color:#64748b;font-size:12px}</style></head><body>' +
      `<h1>${visitorPassPrintLabel.value}</h1>` +
      `<p>${row.title || ''}</p>` +
      `<p class="code">${row.passCode}</p>` +
      (row.passExpireAt ? `<p>有效至 ${row.passExpireAt}</p>` : '') +
      (hint ? `<p class="hint">${hint}</p>` : '') +
      '<script>window.onload=()=>{window.print()}<\/script></body></html>',
  )
  w.document.close()
}

async function load() {
  const res = await http.get('/api/tickets', {
    params: { page: page.value, size: size.value, status: status.value || undefined },
  })
  list.value = res.data.list
  total.value = res.data.total
  staleFollowDays.value = Number(res.data.staleFollowDays || 0)
  levelSlaDays.value = res.data.levelSlaDays || ''
  spotCheckToday.value = !!res.data.spotCheckToday
  loadCredit()
}

async function openApply(opts = {}) {
  makeupMode.value = !!opts?.makeup
  Object.assign(form, {
    title: makeupMode.value ? makeupApplyLabel.value : '',
    location: '',
    remark: '',
    attachUrl: '',
    typeId: null,
    siteId: null,
    roomId: null,
    itemId: null,
    period: null,
    contactChannel: '',
    nextFollowAt: '',
    priority: '普通',
    contactPhone: '',
    proxyName: '',
    proxyPhone: '',
    depositYuan: null,
    pickupPlace: '',
    emergencyContact: '',
    emergencyPhone: '',
    noticeAck: false,
    trainingAck: false,
    insuranceAck: false,
    meetingAck: false,
    inviteCode: '',
    priceNoteAck: false,
    sponsorAck: false,
    planAck: false,
    prereqAck: false,
    tourNoticeAck: false,
    wishOrder: 1,
    volunteerRole: '',
    companionNames: '',
    pickupMethod: '',
    mailAddress: '',
    certUrgent: false,
    sealCopies: 1,
    bindNote: '',
    invoiceCount: 1,
    fineYuan: null,
    visitorCount: 0,
    awardCertNo: '',
    vendorQuotes: '',
    driverName: '',
    passengerNames: '',
    laborPlace: '',
    effectiveOn: '',
    docRev: '',
    workStart: '',
    workEnd: '',
    issueCopies: 1,
    signParties: [],
    trainHours: null,
    memberChangeNote: '',
    procureAmount: null,
    exceptionType: '',
    visitPurpose: '',
    rectifyNote: '',
    fundUseYuan: null,
    fundUseNote: '',
    visitOn: '',
    plagiarismUrl: '',
    partyStage: '',
    stageOn: '',
    observeOn: '',
    observeNote: '',
    scheduleImpactNote: '',
    contractAmount: null,
    expenseLines: [{ category: '', amount: null, note: '' }],
    tripLegs: [{ from: '', via: '', to: '', on: '' }],
    clubMembers: [{ name: '', studentNo: '' }],
    clubRosterCsv: '',
    parkingOn: '',
    renewOn: '',
    renewNote: '',
    changeLogNote: '',
    seatZone: '',
    projectNo: '',
    procureRefNo: '',
    dualReviewerA: '',
    dualReviewerB: '',
    shipFeeYuan: null,
    utilityNote: '',
    peerUsername: '',
    interviewResult: '',
    writtenScore: null,
    bgCheckNote: '',
    dealAmountYuan: null,
    nextAction: '',
    nextActionDone: false,
    returnDate: '',
    defenseResult: '',
    bankAccount: '',
    homeVisitFamily: '',
    homeVisitTalk: '',
    homeVisitPlan: '',
    feedbackInterest: '',
    feedbackConcern: '',
    feedbackNext: '',
    recordUrl: '',
    appraisalComment: '',
    appraisalGrade: '',
    companyEval: '',
    preferredSlot: '',
    addressType: '',
    nightUrgent: false,
    assetCode: '',
    subscribeProgress: false,
    audioUrl: '',
    confidential: false,
    assignDept: '',
    resumeEdu: '',
    resumeExp: '',
    resumeSkill: '',
  })
  claimMatchedLine.value = ''
  units.value = []
  if (applyFromList.value) {
    await loadArchiveItems()
    if (matchProfileRoom.value && archiveItems.value.length === 1) {
      form.itemId = archiveItems.value[0].id
    }
  } else if (lookup.enabled) {
    await prefillLookupFromProfile()
  }
  await refreshAddressBook()
  visible.value = true
}

async function submit(asDraft = false) {
  if (leaveOverlapHint.value && (form.startAt || form.period?.[0])) {
    const start = String(form.startAt || form.period?.[0] || '').slice(0, 10)
    const end = String(form.endAt || form.period?.[1] || start).slice(0, 10)
    const hit = (list.value || []).some((r) => {
      if (!r || r.status === 'cancelled' || r.status === 'rejected') return false
      const a = String(r.startAt || r.periodStart || '').slice(0, 10)
      const b = String(r.endAt || r.periodEnd || a).slice(0, 10)
      if (!a || !start) return false
      return a <= end && b >= start
    })
    if (hit) {
      ElMessage.warning(leaveOverlapHint.value)
      return
    }
  }
  if (applyFromList.value) {
    if (!form.itemId) {
      ElMessage.warning(`请选择${archiveLabel.value}`)
      return
    }
    if (pickDateRange.value) {
      const range = form.period
      if (!Array.isArray(range) || !range[0] || !range[1]) {
        ElMessage.warning('请选择起止日期')
        return
      }
    }
    if (weekNoOn.value && !form.weekNo) {
      ElMessage.warning(`请填写${weekNoLabel.value}`)
      return
    }
    if (requireRemark.value && !(form.remark || '').trim()) {
      ElMessage.warning(`请填写${remarkLabel.value}`)
      return
    }
    if (requireNoticeAck.value && !form.noticeAck) {
      ElMessage.warning(noticeAckLabel.value || '请先勾选须知')
      return
    }
    if (requireTrainingAck.value && !form.trainingAck) {
      ElMessage.warning('请确认已完成相关培训')
      return
    }
    if (requireInsuranceAck.value && !form.insuranceAck) {
      ElMessage.warning(insuranceAckLabel.value || '请先勾选保险声明')
      return
    }
    if (requireMeetingAck.value && !form.meetingAck) {
      ElMessage.warning(meetingAckLabel.value || '请确认已约定面交')
      return
    }
    if (requireApplyInvite.value && !(form.inviteCode || '').trim()) {
      ElMessage.warning(applyInviteHint.value || `请填写${applyInviteLabel.value}`)
      return
    }
    if (needPriceNoteAck.value && !form.priceNoteAck) {
      ElMessage.warning(priceNoteAckLabel.value || '请确认已阅读票价说明')
      return
    }
    if (needSponsorAck.value && !form.sponsorAck) {
      ElMessage.warning(sponsorAckLabel.value || '请确认已知晓赞助说明')
      return
    }
    if (needPlanAck.value && !form.planAck) {
      ElMessage.warning(planAckLabel.value || '请确认已查阅培养方案')
      return
    }
    if (needPrereqAck.value && !form.prereqAck) {
      ElMessage.warning(prereqAckLabel.value || '请确认已具备先修基础')
      return
    }
    if (needTourNoticeAck.value && !form.tourNoticeAck) {
      ElMessage.warning(tourNoticeAckLabel.value || '请确认已阅读出团须知')
      return
    }
    if (allowWishOrder.value && !(form.wishOrder === 1 || form.wishOrder === 2)) {
      ElMessage.warning(wishOrderHint.value || '请选择志愿序')
      return
    }
    if (requirePeerConfirm.value && !(form.peerUsername || '').trim()) {
      ElMessage.warning(`请填写${peerUsernameLabel.value}`)
      return
    }
    if (allowEmergencyContact.value) {
      if (!(form.emergencyContact || '').trim()) {
        ElMessage.warning(`请填写${emergencyContactLabel.value}`)
        return
      }
      if (!(form.emergencyPhone || '').trim()) {
        ElMessage.warning(`请填写${emergencyPhoneLabel.value}`)
        return
      }
    }
    if (requireAttach.value && !form.attachUrl) {
      ElMessage.warning('请上传附件')
      return
    }
    if (requireMaterial.value) {
      const miss = matRef.value?.missingTitle?.() || ''
      if (miss) {
        ElMessage.warning(`请上传必传材料：${miss}`)
        return
      }
    }
    const body = {
      itemId: form.itemId,
      remark: (form.remark || '').trim(),
      attachUrl: form.attachUrl || undefined,
    }
    if (requireMaterial.value && matRef.value) {
      body.materials = matRef.value.payload()
    }
    if (pickDateRange.value && Array.isArray(form.period)) {
      body.periodStart = form.period[0]
      body.periodEnd = form.period[1]
    }
    if (weekNoOn.value && form.weekNo) {
      body.weekNo = form.weekNo
    }
    if (interviewPlaceOn.value && (form.interviewPlace || '').trim()) {
      body.interviewPlace = form.interviewPlace.trim()
    }
    if (showFollowCols.value) {
      if (form.contactChannel) body.contactChannel = form.contactChannel
      if (form.nextFollowAt) body.nextFollowAt = form.nextFollowAt
    }
    if (allowProxyPickup.value) {
      if ((form.proxyName || '').trim()) body.proxyName = form.proxyName.trim()
      if ((form.proxyPhone || '').trim()) body.proxyPhone = form.proxyPhone.trim()
    }
    if (allowDeposit.value && form.depositYuan != null && form.depositYuan !== '') {
      body.depositYuan = form.depositYuan
    }
    if (preferredSlotOn.value && (form.preferredSlot || '').trim()) {
      body.preferredSlot = form.preferredSlot.trim()
    }
    if (allowMeetingPlace.value && (form.pickupPlace || '').trim()) {
      body.pickupPlace = form.pickupPlace.trim()
    }
    if (allowEmergencyContact.value) {
      body.emergencyContact = (form.emergencyContact || '').trim()
      body.emergencyPhone = (form.emergencyPhone || '').trim()
    }
    if (requireNoticeAck.value) body.noticeAck = !!form.noticeAck
    if (rankSwitchOn.value && (rankScope.value || '').trim()) {
      body.rankScope = String(rankScope.value).trim()
    }
    if (requireTrainingAck.value) body.trainingAck = !!form.trainingAck
    if (requireInsuranceAck.value) body.insuranceAck = !!form.insuranceAck
    if (requireMeetingAck.value) body.meetingAck = !!form.meetingAck
    if (requireApplyInvite.value && (form.inviteCode || '').trim()) {
      body.inviteCode = form.inviteCode.trim()
    }
    if (needPriceNoteAck.value) body.priceNoteAck = !!form.priceNoteAck
    if (needSponsorAck.value) body.sponsorAck = !!form.sponsorAck
    if (needPlanAck.value) body.planAck = !!form.planAck
    if (needPrereqAck.value) body.prereqAck = !!form.prereqAck
    if (needTourNoticeAck.value) body.tourNoticeAck = !!form.tourNoticeAck
    if (allowWishOrder.value) body.wishOrder = form.wishOrder === 2 ? 2 : 1
    if (allowVolunteerRole.value && (form.volunteerRole || '').trim()) {
      body.volunteerRole = form.volunteerRole.trim()
    }
    if (allowCompanions.value && (form.companionNames || '').trim()) {
      body.companionNames = form.companionNames.trim()
    }
    if (allowVisitorCount.value && Number(form.visitorCount) > 0) {
      if (!(form.companionNames || '').trim()) {
        ElMessage.warning(`有随行请填写${companionNamesLabel.value}`)
        return
      }
      body.companionNames = form.companionNames.trim()
    }
    if (allowCertPickup.value) {
      if (!(form.pickupMethod || '').trim()) {
        ElMessage.warning(certPickupHint.value || '请选择领取方式')
        return
      }
      body.pickupMethod = form.pickupMethod.trim()
      if (form.pickupMethod === '邮寄') {
        if (!(form.mailAddress || '').trim()) {
          ElMessage.warning(`请填写${mailAddressLabel.value}`)
          return
        }
        body.mailAddress = form.mailAddress.trim()
      }
    }
    if (allowCertUrgent.value) body.certUrgent = !!form.certUrgent
    if (allowSealCopies.value) {
      if (!(form.sealCopies >= 1)) {
        ElMessage.warning(`请填写${sealCopiesLabel.value}`)
        return
      }
      body.sealCopies = form.sealCopies
      if ((form.bindNote || '').trim()) body.bindNote = form.bindNote.trim()
    }
    if (allowExpenseInvoice.value) {
      if (!(form.invoiceCount >= 1)) {
        ElMessage.warning(`请填写${invoiceCountLabel.value}`)
        return
      }
      if (!(Number(form.fineYuan) > 0)) {
        ElMessage.warning(`请填写${expenseAmountLabel.value}`)
        return
      }
      body.invoiceCount = form.invoiceCount
      body.fineYuan = form.fineYuan
    }
    if (allowVisitorCount.value && form.visitorCount != null && form.visitorCount !== '') {
      body.visitorCount = form.visitorCount
    }
    if (allowAwardCertNo.value) {
      if (!(form.awardCertNo || '').trim()) {
        ElMessage.warning(awardCertNoHint.value || `请填写${awardCertNoLabel.value}`)
        return
      }
      body.awardCertNo = form.awardCertNo.trim()
    }
    if (allowVendorQuotes.value) {
      const raw = (form.vendorQuotes || '').trim()
      if (!raw) {
        ElMessage.warning(vendorQuotesHint.value || `请填写${vendorQuotesLabel.value}`)
        return
      }
      const n = raw.split(/\r?\n/).map((s) => s.trim()).filter(Boolean).length
      if (minVendorQuotes.value > 0 && n < minVendorQuotes.value) {
        ElMessage.warning(minVendorQuotesHint.value || `比价供应商至少 ${minVendorQuotes.value} 家`)
        return
      }
      body.vendorQuotes = raw
    }
    if (allowFleetCrew.value) {
      if (!(form.driverName || '').trim()) {
        ElMessage.warning(fleetCrewHint.value || `请填写${driverNameLabel.value}`)
        return
      }
      body.driverName = form.driverName.trim()
      if ((form.passengerNames || '').trim()) {
        body.passengerNames = form.passengerNames.trim()
      }
    }
    if (allowLaborPlace.value) {
      if (!(form.laborPlace || '').trim()) {
        ElMessage.warning(laborPlaceHint.value || `请填写${laborPlaceLabel.value}`)
        return
      }
      body.laborPlace = form.laborPlace.trim()
    }
    if (allowEffectiveOn.value) {
      if (!(form.effectiveOn || '').trim()) {
        ElMessage.warning(effectiveOnHint.value || `请选择${effectiveOnLabel.value}`)
        return
      }
      body.effectiveOn = form.effectiveOn.trim()
    }
    if (allowDocRev.value) {
      if (!(form.docRev || '').trim()) {
        ElMessage.warning(docRevHint.value || `请填写${docRevLabel.value}`)
        return
      }
      body.docRev = form.docRev.trim()
    }
    if (allowFitoutQuiet.value) {
      if (!(form.workStart || '').trim() || !(form.workEnd || '').trim()) {
        ElMessage.warning(fitoutQuietHint.value || `请选择${fitoutWindowLabel.value}`)
        return
      }
      body.workStart = form.workStart.trim()
      body.workEnd = form.workEnd.trim()
    }
    if (allowIssueCopies.value) {
      const n = Number(form.issueCopies)
      if (!Number.isFinite(n) || n < 1) {
        ElMessage.warning(issueCopiesHint.value || `请填写${issueCopiesLabel.value}`)
        return
      }
      body.issueCopies = n
    }
    if (allowSignParties.value) {
      const parts = Array.isArray(form.signParties) ? form.signParties.filter(Boolean) : []
      if (!parts.length) {
        ElMessage.warning(signPartiesHint.value || `请勾选${signPartiesLabel.value}`)
        return
      }
      body.signParties = parts.join('、')
    }
    if (allowTrainHours.value) {
      const h = Number(form.trainHours)
      if (!Number.isFinite(h) || h <= 0) {
        ElMessage.warning(trainHoursHint.value || `请填写${trainHoursLabel.value}`)
        return
      }
      body.trainHours = h
    }
    if (allowMemberChange.value) {
      if (!(form.memberChangeNote || '').trim()) {
        ElMessage.warning(memberChangeNoteHint.value || `请填写${memberChangeNoteLabel.value}`)
        return
      }
      body.memberChangeNote = form.memberChangeNote.trim()
    }
    if (allowProcureBudget.value) {
      const n = Number(form.procureAmount)
      if (!Number.isFinite(n) || n <= 0) {
        ElMessage.warning(procureBudgetHint.value || `请填写${procureAmountLabel.value}`)
        return
      }
      body.procureAmount = n
    }
    if (allowCheckinException.value) {
      if (!(form.exceptionType || '').trim()) {
        ElMessage.warning(exceptionTypeHint.value || `请选择${exceptionTypeLabel.value}`)
        return
      }
      body.exceptionType = form.exceptionType.trim()
    }
    if (allowVisitPurpose.value) {
      if (!(form.visitPurpose || '').trim()) {
        ElMessage.warning(visitPurposeHint.value || `请选择${visitPurposeLabel.value}`)
        return
      }
      body.visitPurpose = form.visitPurpose.trim()
    }
    if (allowFitoutRectify.value) {
      if (!(form.rectifyNote || '').trim()) {
        ElMessage.warning(rectifyNoteHint.value || `请填写${rectifyNoteLabel.value}`)
        return
      }
      body.rectifyNote = form.rectifyNote.trim()
    }
    if (allowProjFundUse.value) {
      const n = Number(form.fundUseYuan)
      if (!Number.isFinite(n) || n <= 0) {
        ElMessage.warning(fundUseHint.value || `请填写${fundUseYuanLabel.value}`)
        return
      }
      if (!(form.fundUseNote || '').trim()) {
        ElMessage.warning(fundUseHint.value || `请填写${fundUseNoteLabel.value}`)
        return
      }
      body.fundUseYuan = n
      body.fundUseNote = form.fundUseNote.trim()
    }
    if (allowVisitSlotRemain.value) {
      if (!(form.visitOn || '').trim()) {
        ElMessage.warning(visitSlotRemainHint.value || `请选择${visitOnLabel.value}`)
        return
      }
      body.visitOn = String(form.visitOn).trim().slice(0, 10)
    }
    if (allowPlagiarismUrl.value) {
      const url = (form.plagiarismUrl || '').trim()
      if (!url || !(url.startsWith('http://') || url.startsWith('https://'))) {
        ElMessage.warning(plagiarismUrlHint.value || `请填写以 http:// 或 https:// 开头的${plagiarismUrlLabel.value}`)
        return
      }
      body.plagiarismUrl = url
    }
    if (allowPartyStage.value) {
      if (!(form.partyStage || '').trim() || !(form.stageOn || '').trim()) {
        ElMessage.warning(partyStageHint.value || `请选择${partyStageLabel.value}并填写${stageOnLabel.value}`)
        return
      }
      body.partyStage = form.partyStage.trim()
      body.stageOn = String(form.stageOn).trim().slice(0, 10)
    }
    if (allowEvalObserve.value) {
      if (!(form.observeOn || '').trim() || !(form.observeNote || '').trim()) {
        ElMessage.warning(evalObserveHint.value || `请填写${observeOnLabel.value}和${observeNoteLabel.value}`)
        return
      }
      body.observeOn = String(form.observeOn).trim().slice(0, 10)
      body.observeNote = form.observeNote.trim()
    }
    if (allowScheduleImpact.value) {
      if (!(form.scheduleImpactNote || '').trim()) {
        ElMessage.warning(scheduleImpactHint.value || `请填写${scheduleImpactNoteLabel.value}`)
        return
      }
      body.scheduleImpactNote = form.scheduleImpactNote.trim()
    }
    if (allowContractAmount.value) {
      const n = Number(form.contractAmount)
      if (!Number.isFinite(n) || n <= 0) {
        ElMessage.warning(contractAmountHint.value || `请填写${contractAmountLabel.value}`)
        return
      }
      body.contractAmount = n
    }
    if (allowExpenseLines.value) {
      const lines = (form.expenseLines || [])
        .map((x) => ({
          category: (x.category || '').trim(),
          amount: Number(x.amount),
          note: (x.note || '').trim(),
        }))
        .filter((x) => x.category || x.amount || x.note)
      if (!lines.length || lines.some((x) => !x.category || !(x.amount > 0))) {
        ElMessage.warning(expenseLinesHint.value || `请完整填写${expenseLinesLabel.value}`)
        return
      }
      body.expenseLines = lines
    }
    if (allowTripLegs.value) {
      const legs = (form.tripLegs || [])
        .map((x) => ({
          from: (x.from || '').trim(),
          via: (x.via || '').trim(),
          to: (x.to || '').trim(),
          on: String(x.on || '').trim().slice(0, 10),
        }))
        .filter((x) => x.from || x.to || x.on || x.via)
      if (!legs.length || legs.some((x) => !x.from || !x.to || !x.on)) {
        ElMessage.warning(tripLegsHint.value || `请完整填写${tripLegsLabel.value}`)
        return
      }
      body.tripLegs = legs
    }
    if (allowClubRoster.value) {
      const members = (form.clubMembers || [])
        .map((x) => ({ name: (x.name || '').trim(), studentNo: (x.studentNo || '').trim() }))
        .filter((x) => x.name || x.studentNo)
      if (!members.length || members.some((x) => !x.name)) {
        ElMessage.warning(clubRosterHint.value || `请完整填写${clubRosterLabel.value}`)
        return
      }
      body.clubMembers = members
    }
    if (allowCarpassParkingMutex.value) {
      if (!(form.parkingOn || '').trim()) {
        ElMessage.warning(carpassParkingMutexHint.value || `请选择${parkingOnLabel.value}`)
        return
      }
      body.parkingOn = String(form.parkingOn).trim().slice(0, 10)
    }
    if (allowContractRenew.value) {
      if (!(form.renewOn || '').trim() || !(form.renewNote || '').trim()) {
        ElMessage.warning(contractRenewHint.value || `请填写${renewOnLabel.value}和${renewNoteLabel.value}`)
        return
      }
      body.renewOn = String(form.renewOn).trim().slice(0, 10)
      body.renewNote = form.renewNote.trim()
    }
    if (allowProjChangeLog.value) {
      if (!(form.changeLogNote || '').trim()) {
        ElMessage.warning(projChangeLogHint.value || `请填写${changeLogNoteLabel.value}`)
        return
      }
      body.changeLogNote = form.changeLogNote.trim()
    }
    if (allowSeatZone.value && (form.seatZone || '').trim()) {
      body.seatZone = form.seatZone.trim()
    }
    if (allowProjectNo.value && (form.projectNo || '').trim()) body.projectNo = form.projectNo.trim()
    if (allowProcureRef.value && (form.procureRefNo || '').trim()) {
      body.procureRefNo = form.procureRefNo.trim()
    }
    if (allowDualReview.value) {
      if ((form.dualReviewerA || '').trim()) body.dualReviewerA = form.dualReviewerA.trim()
      if ((form.dualReviewerB || '').trim()) body.dualReviewerB = form.dualReviewerB.trim()
    }
    if (allowShipFee.value && form.shipFeeYuan != null && form.shipFeeYuan !== '') {
      body.shipFeeYuan = form.shipFeeYuan
    }
    if (allowUtilityNote.value && (form.utilityNote || '').trim()) {
      body.utilityNote = form.utilityNote.trim()
    }
    if (requirePeerConfirm.value) body.peerUsername = (form.peerUsername || '').trim()
    if (allowInterviewResult.value && form.interviewResult) body.interviewResult = form.interviewResult
    if (allowWrittenScore.value && form.writtenScore != null) body.writtenScore = form.writtenScore
    if (allowBgCheckNote.value && (form.bgCheckNote || '').trim()) body.bgCheckNote = form.bgCheckNote.trim()
    if (allowDealAmount.value && form.dealAmountYuan != null) body.dealAmountYuan = form.dealAmountYuan
    if (allowNextAction.value) {
      if ((form.nextAction || '').trim()) body.nextAction = form.nextAction.trim()
      body.nextActionDone = !!form.nextActionDone
    }
    if (allowLeaveProxy.value && (form.proxyName || '').trim()) body.proxyName = form.proxyName.trim()
    if (requireReturnDate.value && form.returnDate) body.returnDate = form.returnDate
    if (allowDefenseResult.value && form.defenseResult) body.defenseResult = form.defenseResult
    if (maskBankAccount.value && (form.bankAccount || '').trim()) body.bankAccount = form.bankAccount.trim()
    if (homeVisitTemplate.value) {
      const parts = []
      if ((form.homeVisitFamily || '').trim()) parts.push(`${homeVisitFamilyLabel.value}：${form.homeVisitFamily.trim()}`)
      if ((form.homeVisitTalk || '').trim()) parts.push(`${homeVisitTalkLabel.value}：${form.homeVisitTalk.trim()}`)
      if ((form.homeVisitPlan || '').trim()) parts.push(`${homeVisitPlanLabel.value}：${form.homeVisitPlan.trim()}`)
      if (parts.length) {
        const extra = parts.join('\n')
        body.remark = body.remark ? `${body.remark}\n${extra}` : extra
      }
    }
    if (requireFeedbackSet.value) {
      if ((form.feedbackInterest || '').trim()) body.feedbackInterest = form.feedbackInterest.trim()
      if ((form.feedbackConcern || '').trim()) body.feedbackConcern = form.feedbackConcern.trim()
      if ((form.feedbackNext || '').trim()) body.feedbackNext = form.feedbackNext.trim()
    }
    if (allowRecordUrl.value && (form.recordUrl || '').trim()) body.recordUrl = form.recordUrl.trim()
    if (requireAppraisal.value) {
      if ((form.appraisalComment || '').trim()) body.appraisalComment = form.appraisalComment.trim()
      if (form.appraisalGrade) body.appraisalGrade = form.appraisalGrade
    }
    if (allowCompanyEval.value && (form.companyEval || '').trim()) body.companyEval = form.companyEval.trim()
    if (allowConfidential.value) body.confidential = !!form.confidential
    if (allowAssignDept.value && (form.assignDept || '').trim()) body.assignDept = form.assignDept.trim()
    if (resumeFieldSet.value) {
      const parts = []
      if ((form.resumeEdu || '').trim()) parts.push(`${resumeEduLabel.value}：${form.resumeEdu.trim()}`)
      if ((form.resumeExp || '').trim()) parts.push(`${resumeExpLabel.value}：${form.resumeExp.trim()}`)
      if ((form.resumeSkill || '').trim()) parts.push(`${resumeSkillLabel.value}：${form.resumeSkill.trim()}`)
      if (parts.length) {
        const extra = parts.join('\n')
        body.remark = body.remark ? `${body.remark}\n${extra}` : extra
      }
    }
    await http.post('/api/tickets/apply', body)
    ElMessage.success('已提交，等待审核')
    visible.value = false
    load()
    return
  }
  if (!form.title.trim()) {
    ElMessage.warning('请填写标题')
    return
  }
  if (lookup.enabled) {
    if (!form.typeId) {
      ElMessage.warning(`请选择${lookup.typeLabel}`)
      return
    }
    if (!form.siteId) {
      ElMessage.warning(`请选择${lookup.siteLabel}`)
      return
    }
    if (!form.roomId) {
      ElMessage.warning(`请选择${lookup.unitLabel}`)
      return
    }
  } else if (!form.location.trim()) {
    ElMessage.warning('请填写地点')
    return
  }
  if (requireAttach.value && !form.attachUrl) {
    ElMessage.warning('请上传附件')
    return
  }
  if (requireMaterial.value) {
    const miss = matRef.value?.missingTitle?.() || ''
    if (miss) {
      ElMessage.warning(`请上传必传材料：${miss}`)
      return
    }
  }
  const body = {
    title: form.title,
    remark: form.remark,
    location: form.location,
    typeId: form.typeId,
    roomId: form.roomId,
    attachUrl: form.attachUrl || undefined,
    priority: showPriorityCols.value ? form.priority : undefined,
    contactPhone: showPriorityCols.value ? (form.contactPhone || undefined) : undefined,
    preferredSlot: preferredSlotOn.value ? (form.preferredSlot || undefined) : undefined,
    addressType: allowPublicArea.value ? (form.addressType || undefined) : undefined,
    nightUrgent: nightUrgentOn.value ? !!form.nightUrgent : undefined,
    assetCode: allowAssetCode.value ? (form.assetCode || undefined) : undefined,
    subscribeProgress: progressSubscribeOn.value ? !!form.subscribeProgress : undefined,
    audioUrl: allowAudioRemark.value ? (form.audioUrl || undefined) : undefined,
    asDraft: asDraft || undefined,
  }
  if (requireMaterial.value && matRef.value) body.materials = matRef.value.payload()
  const res = await http.post('/api/tickets/apply', body)
  const data = res.data?.data || res.data || {}
  if (data.dupRepairHint) ElMessage.warning(data.dupRepairHint)
  if (data.creditWarnHint) ElMessage.warning(data.creditWarnHint)
  if (data.prereqHint) ElMessage.warning(data.prereqHint)
  if (data.dutyNotified) ElMessage.success(`已群发当日值班 ${data.dutyNotified} 人`)
  ElMessage.success(asDraft ? '草稿已保存' : '已提交')
  visible.value = false
  load()
}

async function withdraw(row) {
  await ElMessageBox.confirm(`确认撤销「${row.title || ('编号 ' + row.id)}」？`, '确认撤销')
  await http.post(`/api/tickets/${row.id}/withdraw`)
  ElMessage.success('已撤销')
  load()
}

async function finish(row) {
  if (requireReturnAttach.value || requireFaultReason.value || requireCloseSummary.value || requireCloseAttach.value || allowFleetMileage.value || allowCompHours.value || allowReturnFuel.value || allowFleetViolation.value || allowProcureReturn.value) {
    returnDlg.row = row
    returnDlg.attachUrl = ''
    returnDlg.faultReason = row.faultReason || ''
    returnDlg.closeSummary = row.closeSummary || ''
    returnDlg.partsNote = row.partsNote || ''
    returnDlg.mileageKm = row.mileageKm != null ? Number(row.mileageKm) : null
    returnDlg.fuelNote = row.fuelNote || ''
    returnDlg.compHours = row.compHours != null ? Number(row.compHours) : null
    returnDlg.returnFuel = row.returnFuel != null ? Number(row.returnFuel) : null
    returnDlg.violationPerson = row.violationPerson || ''
    returnDlg.returnFail = !!row.returnFail
    returnDlg.returnNote = row.returnNote || ''
    returnDlg.visible = true
    return
  }
  await ElMessageBox.confirm(`确认${verbs.value.return || '完结'}「${row.title}」？`, '确认')
  await http.post(`/api/tickets/${row.id}/complete`, {})
  ElMessage.success('已更新')
  load()
}

async function onReturnUpload(opt) {
  const fd = new FormData()
  fd.append('file', opt.file)
  const res = await http.post('/api/upload', fd)
  returnDlg.attachUrl = res.data?.url || res.data?.data?.url || ''
  if (!returnDlg.attachUrl) ElMessage.warning('上传失败')
}

async function confirmReturn() {
  if (!returnDlg.row) return
  if (requireFaultReason.value && !(returnDlg.faultReason || '').trim()) {
    ElMessage.warning(`请选择${faultReasonLabel.value}`)
    return
  }
  if (requireCloseSummary.value && !(returnDlg.closeSummary || '').trim()) {
    ElMessage.warning(`请填写${closeSummaryLabel.value}`)
    return
  }
  if ((requireReturnAttach.value || requireCloseAttach.value) && !returnDlg.attachUrl) {
    ElMessage.warning('请先上传结单附件')
    return
  }
  if (allowFleetMileage.value && !(Number(returnDlg.mileageKm) > 0)) {
    ElMessage.warning(`请填写大于 0 的${mileageLabel.value}`)
    return
  }
  if (allowFleetMileage.value && !(returnDlg.fuelNote || '').trim()) {
    ElMessage.warning(`请填写${fuelNoteLabel.value}`)
    return
  }
  if (allowCompHours.value && !(Number(returnDlg.compHours) > 0)) {
    ElMessage.warning(`请填写大于 0 的${compHoursLabel.value}`)
    return
  }
  if (allowReturnFuel.value) {
    const fuel = Number(returnDlg.returnFuel)
    if (!(fuel >= 0 && fuel <= 100)) {
      ElMessage.warning(`请填写 0–100 的${returnFuelLabel.value}`)
      return
    }
  }
  if (allowFleetViolation.value && !(returnDlg.violationPerson || '').trim()) {
    ElMessage.warning(violationPersonHint.value || `请填写${violationPersonLabel.value}`)
    return
  }
  if (allowProcureReturn.value && returnDlg.returnFail && !(returnDlg.returnNote || '').trim()) {
    ElMessage.warning(procureReturnHint.value || `请填写${returnNoteLabel.value}`)
    return
  }
  returnDlg.loading = true
  try {
    await http.post(`/api/tickets/${returnDlg.row.id}/complete`, {
      attachUrl: returnDlg.attachUrl || undefined,
      closeAttachUrl: returnDlg.attachUrl || undefined,
      faultReason: returnDlg.faultReason || undefined,
      closeSummary: returnDlg.closeSummary || undefined,
      partsNote: returnDlg.partsNote || undefined,
      mileageKm: allowFleetMileage.value ? returnDlg.mileageKm : undefined,
      fuelNote: allowFleetMileage.value ? (returnDlg.fuelNote || undefined) : undefined,
      compHours: allowCompHours.value ? returnDlg.compHours : undefined,
      returnFuel: allowReturnFuel.value ? returnDlg.returnFuel : undefined,
      violationPerson: allowFleetViolation.value ? (returnDlg.violationPerson || undefined) : undefined,
      returnFail: allowProcureReturn.value ? !!returnDlg.returnFail : undefined,
      returnNote: allowProcureReturn.value ? (returnDlg.returnNote || undefined) : undefined,
    })
    ElMessage.success('已更新')
    returnDlg.visible = false
    load()
  } finally {
    returnDlg.loading = false
  }
}

async function reportLost(row) {
  await ElMessageBox.confirm(
    `确认对「${row.title || ('编号 ' + row.id)}」申报丢失？库存不回补，请按馆规办理赔偿。`,
    lostVerb.value,
  )
  await http.post(`/api/tickets/${row.id}/report-lost`)
  ElMessage.success(labels.value.bookLostOkMessage || '已登记丢失申报')
  load()
}

async function renew(row) {
  const used = Number(row.renewCount) || 0
  await ElMessageBox.confirm(
    `确认对「${row.title || ('编号 ' + row.id)}」${renewVerb.value}？当前已续 ${used}/${maxRenew.value} 次。`,
    renewVerb.value,
  )
  const res = await http.post(`/api/tickets/${row.id}/renew`)
  const due = res.data?.dueAt || res.data?.data?.dueAt
  ElMessage.success(
    due
      ? `续借成功，新应还日 ${due}`
      : (labels.value.renewOkMessage || '续借成功，应还日已延长'),
  )
  load()
}

async function claimHold(row) {
  await ElMessageBox.confirm(
    `确认借阅「${row.title || ('编号 ' + row.id)}」？`
      + (row.holdExpireAt ? `取书截止 ${row.holdExpireAt}。` : ''),
    claimHoldVerb.value,
  )
  await http.post(`/api/tickets/${row.id}/claim-hold`)
  ElMessage.success(labels.value.bookHoldClaimOkMessage || '已确认借阅')
  load()
}

function openCheckin(row) {
  checkinRow.value = row
  checkinCode.value = ''
  checkinLateMinutes.value = 0
  checkinVisible.value = true
}

async function submitCheckin() {
  if (!checkinRow.value) return
  if (!checkinCode.value.trim()) {
    ElMessage.warning('请输入签到码')
    return
  }
  checkinLoading.value = true
  try {
    const body = { code: checkinCode.value.trim() }
    if (allowLateMinutes.value) body.lateMinutes = Number(checkinLateMinutes.value) || 0
    await http.post(`/api/tickets/${checkinRow.value.id}/checkin`, body)
    ElMessage.success({ message: '签到成功 ✓', duration: 2000 })
    checkinVisible.value = false
    load()
  } finally {
    checkinLoading.value = false
  }
}

function openProgress(row) {
  progressId.value = row.id
  progressVisible.value = true
}

onMounted(async () => {
  await loadLookup()
  await load()
  await loadCredit()
})
</script>

<style scoped>
.hero { margin-bottom: 18px; }
.hero-row { display: flex; justify-content: space-between; gap: 16px; align-items: flex-start; flex-wrap: wrap; }
.hero h1 { margin: 0 0 6px; font-size: 22px; }
.hero p { margin: 0; color: var(--portal-muted, #64748b); font-size: 13px; }
.page-hint { margin-top: 6px !important; color: #64748b; font-size: 12px !important; }
.rank-switch { display: flex; align-items: center; gap: 10px; margin-top: 8px; flex-wrap: wrap; }
.rank-lab { font-size: 12px; color: #64748b; }
.field-hint { margin: 6px 0 0; color: #64748b; font-size: 12px; }
.loc-row { display: flex; gap: 8px; width: 100%; }
.loc-row .el-input { flex: 1; }
.line-row { display: flex; gap: 8px; width: 100%; align-items: center; flex-wrap: wrap; margin-bottom: 8px; }
.hint-inline { margin: -4px 0 12px; color: var(--portal-muted, #64748b); font-size: 12px; }
.tools { display: flex; gap: 8px; flex-wrap: wrap; }
.list { display: flex; flex-direction: column; gap: 12px; }
.card {
  display: flex; gap: 14px; padding: var(--portal-pad, 16px);
  background: var(--portal-surface, #fff);
  border: var(--portal-border-width, 1px) solid var(--portal-line, #e2e8f0);
  border-radius: var(--portal-radius, 12px);
  box-shadow: var(--portal-shadow, none);
}
.mark {
  width: 44px; height: 44px; border-radius: var(--portal-radius-sm, 10px); flex-shrink: 0;
  display: grid; place-items: center; font-weight: 700; color: #0369a1;
  background: #e0f2fe;
}
.meta { flex: 1; min-width: 0; }
.meta h3 { margin: 0 0 4px; font-size: 16px; }
.sub { margin: 0; color: var(--portal-muted, #64748b); font-size: 12px; }
.sub.claim-match { margin: -4px 0 10px 88px; color: #0f766e; }
.sub.sched { margin-top: 2px; color: #0f766e; }
.sub.pickup-tip { margin-top: 6px; color: #b45309; }
.sub a { color: #0369a1; }
.tip { margin: 6px 0 0; color: var(--portal-muted, #475569); font-size: 13px; }
.row { margin-top: 10px; display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }
.gallery-edit { display: flex; flex-direction: column; gap: 8px; width: 100%; }
.gallery-list { display: flex; flex-wrap: wrap; gap: 8px; }
.gallery-item {
  width: 96px; display: flex; flex-direction: column; gap: 4px; align-items: flex-start;
}
.gallery-item img { width: 96px; height: 72px; object-fit: cover; border-radius: 6px; }
.rated { font-size: 12px; color: #b45309; }
.attach-row { display: flex; gap: 12px; align-items: center; }
.attach-row a { font-size: 13px; color: #0369a1; }
.rate-tip { margin: 0 0 12px; color: var(--portal-ink, #334155); font-size: 14px; }
.empty { text-align: center; color: var(--portal-muted, #94a3b8); padding: 40px 0; }
.pager { margin-top: 16px; display: flex; justify-content: flex-end; }
</style>
