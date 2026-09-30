<template>
  <div>
    <section class="hero">
      <div class="hero-row">
        <div>
          <h1>{{ plural }}</h1>
          <p>{{ pageLead }}</p>
        </div>
        <div class="tools">
          <el-select v-model="status" clearable placeholder="全部状态" style="width:140px" @change="load">
            <el-option v-for="(lab, key) in states" :key="key" :label="lab" :value="key" />
          </el-select>
          <el-button v-if="!archiveMode || applyFromList" type="primary" @click="openApply">{{ verbs.apply || '提交' }}</el-button>
          <el-button v-else type="primary" @click="$router.push('/archive')">{{ browseCta }}</el-button>
          <el-button @click="load">刷新</el-button>
        </div>
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
          <p v-if="row.startAt || row.endAt" class="sub sched">
            {{ row.periodStart || row.periodEnd ? '起止' : '时段' }}
            {{ row.startAt || '—' }} ~ {{ row.endAt || '—' }}
            <template v-if="row.leaveDays"> · {{ leaveDaysLabel }} {{ row.leaveDays }} 天</template>
            <template v-if="row.weekNo"> · {{ weekNoLabel }} {{ row.weekNo }}</template>
          </p>
          <p v-if="showPriorityCols && row.contactPhone" class="sub">电话 {{ row.contactPhone }}</p>
          <p v-if="row.interviewPlace" class="sub">{{ interviewPlaceLabel }}：{{ row.interviewPlace }}</p>
          <div v-if="row.remark" class="tip">
            <template v-if="row.status === 'rejected'">驳回原因：</template>
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
              v-if="canWithdraw(row)"
              type="danger"
              size="small"
              plain
              @click="withdraw(row)"
            >撤销</el-button>
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
              @click="openRate(row)"
            >评分</el-button>
            <span v-else-if="row.rating" class="rated">已评 {{ row.rating }} 分</span>
          </div>
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
            <el-button link type="primary" size="small" @click="copyPass(row.passCode)">复制</el-button>
            <span class="muted">到访时出示即可</span>
            <CodeQrBlock v-if="codeQrOn" :code="row.passCode" :label="passCodeLabel" />
          </p>
          <p v-if="row.attachUrl" class="sub">
            附件 <a :href="row.attachUrl" target="_blank" rel="noopener noreferrer">查看</a>
          </p>
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

    <el-dialog v-model="returnDlg.visible" :title="finishVerb" width="440px">
      <p class="sub">{{ labels.returnAttachHint || '归还时请上传设备外观/配件照片，便于验收。' }}</p>
      <div class="attach-row">
        <el-upload :show-file-list="false" accept="image/*" :http-request="onReturnUpload">
          <el-button size="small">{{ returnDlg.attachUrl ? '重新上传' : '上传照片' }}</el-button>
        </el-upload>
        <a v-if="returnDlg.attachUrl" :href="returnDlg.attachUrl" target="_blank" rel="noopener noreferrer">已上传</a>
      </div>
      <template #footer>
        <el-button @click="returnDlg.visible = false">取消</el-button>
        <el-button type="primary" :loading="returnDlg.loading" @click="confirmReturn">确认归还</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="visible" :title="verbs.apply || '提交'" width="520px">
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
          <el-form-item v-if="requireNoticeAck">
            <el-checkbox v-model="form.noticeAck">{{ noticeAckLabel }}</el-checkbox>
          </el-form-item>
          <el-form-item v-if="requireTrainingAck">
            <el-checkbox v-model="form.trainingAck">我已完成相关培训</el-checkbox>
          </el-form-item>
          <el-form-item v-if="requireInsuranceAck">
            <el-checkbox v-model="form.insuranceAck">{{ insuranceAckLabel }}</el-checkbox>
          </el-form-item>
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
          <el-form-item v-if="requireAttach" label="附件" required>
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
          </el-form-item>
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
            <el-input v-model="form.location" maxlength="64" placeholder="请填写地点" />
          </el-form-item>
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
            </el-form-item>
          </template>
          <el-form-item label="说明">
            <el-input v-model="form.remark" type="textarea" :rows="3" maxlength="400" />
          </el-form-item>
          <el-form-item v-if="requireAttach" label="附件" required>
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
          </el-form-item>
          <MaterialChecklistFields v-if="requireMaterial" ref="matRef" />
        </template>
      </el-form>
      <template #footer>
        <el-button @click="visible = false">取消</el-button>
        <el-button type="primary" @click="submit">提交</el-button>
      </template>
    </el-dialog>

    <TicketRateDialog
      v-model="rateVisible"
      :ticket-id="rateRow?.id"
      :title="rateRow ? (rateRow.title || ('编号 ' + rateRow.id)) : ''"
      @done="load"
    />

    <el-dialog v-model="checkinVisible" :title="checkinLabel" width="400px" destroy-on-close>
      <p class="rate-tip" v-if="checkinRow">对「{{ checkinRow.title || ('编号 ' + checkinRow.id) }}」输入签到码</p>
      <el-input v-model="checkinCode" maxlength="16" placeholder="请输入签到码" @keyup.enter="submitCheckin" />
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

    <TicketProgressDialog v-model="progressVisible" :ticket-id="progressId" />
  </div>
</template>

<script setup>
import CodeQrBlock from '../../components/CodeQrBlock.vue'
import ImmSteps from '../../components/ImmSteps.vue'
import StatusChip from '../../components/StatusChip.vue'
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import http from '../../api/http'
import RichTextView from '../../components/RichTextView.vue'
import TicketRateDialog from '../../components/TicketRateDialog.vue'
import TicketProgressDialog from '../../components/TicketProgressDialog.vue'
import MaterialChecklistFields from '../../components/MaterialChecklistFields.vue'
import ClaimProofFields from '../../components/ClaimProofFields.vue'
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

const { nowMs } = useNowTick()
const ticket = ticketCopy()
const multiApproveOn = computed(() => hasCap('multi_approve'))
/** 请假天数等域内文案读 schema.labels，勿在页面写死 */
const leaveDaysLabel = computed(() => getSchema()?.labels?.leaveDaysLabel || '请假天数')
/** 周报周次：仅开启了 weekNoLabel 的域显示（DOM-INTERN） */
const weekNoOn = computed(() => !!getSchema()?.labels?.weekNoLabel)
const weekNoLabel = computed(() => getSchema()?.labels?.weekNoLabel || '周次')
const weekNoLead = computed(() => getSchema()?.labels?.weekNoLead || '')
/** 招聘：面试地点（仅开启 interviewPlaceLabel 的域显示） */
const interviewPlaceOn = computed(() => !!getSchema()?.labels?.interviewPlaceLabel)
const interviewPlaceLabel = computed(() => getSchema()?.labels?.interviewPlaceLabel || '面试地点')
const interviewPlaceLead = computed(() => getSchema()?.labels?.interviewPlaceLead || '')

function isMultiApproveStatus(st) {
  return ['pending', 'pending_mid', 'pending_final', 'approved'].includes(st)
}
const archive = archiveCopy()
const verbs = computed(() => ticket.verbs || {})
const states = computed(() => ticket.states || {})
const plural = computed(() => ticket.labelPlural || ticket.label || '我的申请')
const labels = computed(() => getSchema().labels || {})
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
const requireNoticeAck = computed(() => !!ticket.requireNoticeAck)
const noticeAckLabel = computed(() => labels.value.noticeAckLabel || '我已阅读并同意相关须知')
const requireTrainingAck = computed(() => !!ticket.requireTrainingAck)
const requireInsuranceAck = computed(() => !!ticket.requireInsuranceAck)
const insuranceAckLabel = computed(() => labels.value.insuranceAckLabel || '我已阅读设备借用保险声明')
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
const requirePeerConfirm = computed(() => !!ticket.requirePeerConfirm)
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
const requireAttach = computed(() => !!ticket.requireAttach)
const requireMaterial = computed(() => !!ticket.requireMaterialChecklist)
const requireClaimProof = computed(() => !!ticket.requireClaimProof || hasCap('claim_proof'))
const matRef = ref(null)
const proofRef = ref(null)
const proofDlg = reactive({ visible: false, row: null, loading: false })
const returnDlg = reactive({ visible: false, row: null, attachUrl: '', loading: false })
const allowRating = computed(() => !!ticket.allowRating)
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

function canWithdraw(row) {
  if (!row) return false
  if (row.status === 'pending' || row.status === 'pending_mid'
    || row.status === 'pending_final' || row.status === 'waitlisted'
    || row.status === 'verifying') return true
  return !!(allowBookHold.value && (row.status === 'held' || row.status === 'hold_ready'))
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
  // 核销即终态的域：通过后即可评
  return !!(approveEndsFlow.value && row.status === 'approved')
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
  noticeAck: false,
  trainingAck: false,
  insuranceAck: false,
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
})

const rateVisible = ref(false)
const rateRow = ref(null)
const checkinVisible = ref(false)
const checkinLoading = ref(false)
const checkinRow = ref(null)
const checkinCode = ref('')
const progressVisible = ref(false)
const progressId = ref(null)

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

async function load() {
  const res = await http.get('/api/tickets', {
    params: { page: page.value, size: size.value, status: status.value || undefined },
  })
  list.value = res.data.list
  total.value = res.data.total
}

async function openApply() {
  Object.assign(form, {
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
    priority: '普通',
    contactPhone: '',
    proxyName: '',
    proxyPhone: '',
    depositYuan: null,
    noticeAck: false,
    trainingAck: false,
    insuranceAck: false,
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
  visible.value = true
}

async function submit() {
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
    if (requirePeerConfirm.value && !(form.peerUsername || '').trim()) {
      ElMessage.warning(`请填写${peerUsernameLabel.value}`)
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
    if (requireNoticeAck.value) body.noticeAck = !!form.noticeAck
    if (requireTrainingAck.value) body.trainingAck = !!form.trainingAck
    if (requireInsuranceAck.value) body.insuranceAck = !!form.insuranceAck
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
  }
  if (requireMaterial.value && matRef.value) body.materials = matRef.value.payload()
  await http.post('/api/tickets/apply', body)
  ElMessage.success('已提交')
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
  if (requireReturnAttach.value) {
    returnDlg.row = row
    returnDlg.attachUrl = ''
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
  if (!returnDlg.attachUrl) {
    ElMessage.warning('请上传归还照片')
    return
  }
  returnDlg.loading = true
  try {
    await http.post(`/api/tickets/${returnDlg.row.id}/complete`, { attachUrl: returnDlg.attachUrl })
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

function openRate(row) {
  rateRow.value = row
  rateVisible.value = true
}

function openCheckin(row) {
  checkinRow.value = row
  checkinCode.value = ''
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
    await http.post(`/api/tickets/${checkinRow.value.id}/checkin`, { code: checkinCode.value.trim() })
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
})
</script>

<style scoped>
.hero { margin-bottom: 18px; }
.hero-row { display: flex; justify-content: space-between; gap: 16px; align-items: flex-start; flex-wrap: wrap; }
.hero h1 { margin: 0 0 6px; font-size: 22px; }
.hero p { margin: 0; color: var(--portal-muted, #64748b); font-size: 13px; }
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
.rated { font-size: 12px; color: #b45309; }
.attach-row { display: flex; gap: 12px; align-items: center; }
.attach-row a { font-size: 13px; color: #0369a1; }
.rate-tip { margin: 0 0 12px; color: var(--portal-ink, #334155); font-size: 14px; }
.empty { text-align: center; color: var(--portal-muted, #94a3b8); padding: 40px 0; }
.pager { margin-top: 16px; display: flex; justify-content: flex-end; }
</style>
