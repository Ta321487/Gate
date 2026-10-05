<template>
  <div>
    <div class="toolbar">
      <el-alert type="info" :closable="false" show-icon :title="todoHint" />
    </div>
    <p v-if="levelSlaText" class="sub">{{ levelSlaHint }}（{{ levelSlaText }}）</p>
    <p v-if="dutyNotifyOn" class="sub">{{ notifyDutyHint }}</p>
    <p v-if="ticket.allowApproveAutoPass && approveAutoPassHint" class="sub">{{ approveAutoPassHint }}</p>
    <div class="toolbar">
      <el-button type="primary" @click="load">刷新待办</el-button>
      <el-button v-if="allowApproveDelegate" @click="openDelegate">{{ approveDelegateLabel }}</el-button>
      <template v-if="allowBatchHire">
        <el-button
          type="success"
          :disabled="!selectedIds.length"
          @click="batchHire(true)"
        >{{ batchHireLabel }}（{{ selectedIds.length }}）</el-button>
        <el-button
          type="danger"
          :disabled="!selectedIds.length"
          @click="batchHire(false)"
        >{{ batchRejectLabel }}（{{ selectedIds.length }}）</el-button>
      </template>
      <el-button v-if="allowVisitWalkIn" @click="openWalkIn">{{ visitWalkInLabel }}</el-button>
      <el-button v-if="allowCheckinProxy" @click="openCheckinProxy">{{ checkinProxyLabel }}</el-button>
      <el-button v-if="allowEvalUrge" @click="openEvalUrge">{{ evalUrgeLabel }}</el-button>
      <el-button v-if="allowCheckinSpot" @click="openSpotCheck">{{ checkinSpotLabel }}</el-button>
      <el-button v-if="allowCheckinDailyReport" @click="openCheckinDaily">{{ checkinDailyLabel }}</el-button>
      <el-button v-if="allowEvalCollegeExport" @click="openEvalCollege">{{ evalCollegeExportLabel }}</el-button>
    </div>
    <div v-if="allowApproveDurationStats" class="toolbar" style="display:block;margin-bottom:12px">
      <div style="display:flex;align-items:center;gap:12px;margin-bottom:8px">
        <strong style="font-size:13px">{{ approveDurationStatsLabel }}</strong>
        <el-button link type="primary" @click="loadDurationStats">刷新</el-button>
      </div>
      <p v-if="approveDurationStatsHint" class="sub">{{ approveDurationStatsHint }}</p>
      <el-table :data="durationRows" size="small" stripe max-height="240">
        <el-table-column prop="handler" label="办理人" width="140" />
        <el-table-column prop="count" label="办结数" width="90" />
        <el-table-column prop="avgMinutes" label="平均分钟" width="110" />
        <template #empty>暂无已办结单据</template>
      </el-table>
    </div>
    <div v-if="creditOn" class="toolbar" style="display:block;margin-bottom:12px">
      <div style="display:flex;align-items:center;gap:12px;margin-bottom:8px">
        <strong style="font-size:13px">{{ creditScoreLabel }}台账</strong>
        <el-button link type="primary" @click="loadCredit">刷新</el-button>
        <el-button link type="primary" @click="openCredit">人工调整</el-button>
      </div>
      <el-table :data="creditRows" size="small" stripe max-height="240">
        <el-table-column prop="username" :label="userLabel" width="120" />
        <el-table-column prop="delta" label="变动" width="80">
          <template #default="{ row }">
            <span :style="{ color: row.delta < 0 ? '#f56c6c' : '#67c23a', fontWeight: 600 }">
              {{ row.delta > 0 ? '+' + row.delta : row.delta }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="scoreAfter" :label="creditScoreLabel" width="90" />
        <el-table-column prop="reason" label="事由" min-width="160" show-overflow-tooltip />
        <el-table-column prop="operator" label="操作人" width="110" />
        <el-table-column prop="createdAt" label="时间" width="170" />
        <template #empty>暂无信誉分变动</template>
      </el-table>
    </div>
    <div class="table-scroll">
    <el-table :data="list" stripe @selection-change="onSelectionChange">
      <el-table-column v-if="allowBatchHire" type="selection" width="48" />
      <el-table-column prop="id" label="编号" width="70" />
      <el-table-column prop="title" :label="ticket.label || '标题'" min-width="160" show-overflow-tooltip />
      <el-table-column v-if="showTypeCol" prop="typeName" :label="typeColLabel" width="110" show-overflow-tooltip>
        <template #default="{ row }">
          <span v-if="categoryColorOn" class="type-dot" :style="{ background: typeColor(row.typeName || row.typeId) }" />
          {{ row.typeName || '—' }}
        </template>
      </el-table-column>
      <el-table-column v-if="showLocationCol" prop="location" :label="locationColLabel" min-width="140" show-overflow-tooltip />
      <el-table-column v-if="showPriorityCols" prop="priority" label="优先级" width="90" />
      <el-table-column v-if="showPriorityCols" prop="contactPhone" label="联系电话" width="120" show-overflow-tooltip />
      <el-table-column :label="userLabel" width="110">
        <template #default="{ row }">{{ personLabel(row) }}</template>
      </el-table-column>
      <el-table-column prop="assigneeUsername" label="处理人" width="110">
        <template #default="{ row }">{{ row.assigneeUsername || '—' }}</template>
      </el-table-column>
      <el-table-column v-if="requireRemark" :label="remarkLabel" min-width="140" show-overflow-tooltip>
        <template #default="{ row }">
          <span v-if="row.remark">{{ remarkPlain(row.remark) }}</span>
          <span v-else class="muted">—</span>
        </template>
      </el-table-column>
      <el-table-column v-if="showFollowCols" :label="channelLabel" width="100" show-overflow-tooltip>
        <template #default="{ row }">{{ row.contactChannel || '—' }}</template>
      </el-table-column>
      <el-table-column v-if="showFollowCols" :label="nextAtLabel" width="170">
        <template #default="{ row }">{{ row.nextFollowAt || '—' }}</template>
      </el-table-column>
      <el-table-column label="附件" width="110">
        <template #default="{ row }">
          <a v-if="row.attachUrl" :href="row.attachUrl" target="_blank" rel="noopener noreferrer">申请</a>
          <a
            v-if="row.approveAttachUrl"
            :href="row.approveAttachUrl"
            target="_blank"
            rel="noopener noreferrer"
            style="margin-left:4px"
          >审核</a>
          <span v-if="!row.attachUrl && !row.approveAttachUrl" class="muted">—</span>
        </template>
      </el-table-column>
      <el-table-column v-if="allowQty" prop="qty" label="数量" width="70" />
      <el-table-column v-if="pickLoanPeriod || slaDeadline" prop="dueAt" :label="dueLabel" width="170" />
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag
            size="small"
            :type="row.status === 'pending_final' ? '' : row.status === 'pending_mid' ? 'info' : 'warning'"
            effect="plain"
          >
            {{ statusText(row.status) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="applyAt" label="申请时间" width="170" />
      <el-table-column label="操作" min-width="200" fixed="right">
        <template #default="{ row }">
          <div class="table-ops">
          <el-button link type="primary" @click="openProgress(row)">进度</el-button>
          <el-button
            v-if="requireClaimProof && row.status === 'verifying'"
            link
            type="warning"
            @click="openProofVerify(row)"
          >核验凭证</el-button>
          <el-button
            link
            type="success"
            :disabled="!canPass(row)"
            @click="openAudit(row, true)"
          >{{ passLabel(row) }}</el-button>
          <el-button link type="danger" @click="openAudit(row, false)">{{ verbs.reject || '驳回' }}</el-button>
          <el-button
            v-if="['pending','pending_mid','pending_final'].includes(row.status)"
            link
            type="warning"
            @click="returnRevise(row)"
          >退回修改</el-button>
          <el-button
            v-if="canReassign(row)"
            link
            type="primary"
            @click="openReassign(row)"
          >{{ reassignActionLabel }}</el-button>
          <el-button
            v-if="canCcComment(row)"
            link
            type="primary"
            @click="openCcComment(row)"
          >{{ approveCcCommentLabel }}</el-button>
          </div>
        </template>
      </el-table-column>
      <template #empty>暂无待办</template>
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

    <el-dialog
      v-model="audit.visible"
      :title="audit.pass ? passLabel(audit.row) : (verbs.reject || '驳回')"
      width="440px"
      destroy-on-close
      @closed="resetAudit"
    >
      <p class="audit-tip">
        {{ audit.pass ? `确认${passLabel(audit.row)}该${ticketNoun}？` : `确认${verbs.reject || '驳回'}该${ticketNoun}？` }}
        <template v-if="audit.row">「{{ audit.row.title || ('编号 ' + audit.row.id) }}」</template>
      </p>
      <p v-if="interviewRoomHint" class="audit-meta hint-line">{{ interviewRoomHint }}</p>
      <div v-if="audit.row?.attachUrl || audit.row?.approveAttachUrl" class="audit-body">
        <div class="lab">附件</div>
        <a v-if="audit.row.attachUrl" :href="audit.row.attachUrl" target="_blank" rel="noopener noreferrer">申请附件</a>
        <a
          v-if="audit.row.approveAttachUrl"
          :href="audit.row.approveAttachUrl"
          target="_blank"
          rel="noopener noreferrer"
          style="margin-left:8px"
        >审核附件</a>
      </div>
      <div v-if="audit.row?.typeName || audit.row?.location" class="audit-body">
        <div class="lab">{{ archive.label || '档案' }}信息</div>
        <p v-if="audit.row.typeName" class="audit-meta">{{ typeColLabel }}：{{ audit.row.typeName }}</p>
        <p v-if="audit.row.location" class="audit-meta">{{ locationColLabel }}：{{ audit.row.location }}</p>
      </div>
      <div v-if="showFollowCols && (audit.row?.contactChannel || audit.row?.nextFollowAt)" class="audit-body">
        <div class="lab">补充信息</div>
        <p v-if="audit.row.contactChannel" class="audit-meta">{{ channelLabel }}：{{ audit.row.contactChannel }}</p>
        <p v-if="audit.row.nextFollowAt" class="audit-meta">{{ nextAtLabel }}：{{ audit.row.nextFollowAt }}</p>
      </div>
      <div v-if="audit.row?.remark" class="audit-body">
        <div class="lab">{{ remarkLabel }}</div>
        <RichTextView v-if="richRemark" :html="audit.row.remark" />
        <p v-else class="audit-meta">{{ audit.row.remark }}</p>
      </div>
      <label class="audit-field">
        <span class="lab">
          {{ audit.pass ? '审核备注' : '驳回原因' }}
          <i v-if="!audit.pass || minApproveRemarkWords > 0" class="req" aria-hidden="true">*</i>
          <template v-else>（选填）</template>
        </span>
        <el-select
          v-if="approvePhrases.length"
          v-model="audit.phrasePick"
          clearable
          filterable
          :placeholder="approvePhraseLabel"
          style="width: 100%; margin-bottom: 8px"
          @change="applyApprovePhrase"
        >
          <el-option v-for="p in approvePhrases" :key="p" :label="p" :value="p" />
        </el-select>
        <p v-if="approvePhraseHint && approvePhrases.length" class="audit-meta hint-line">{{ approvePhraseHint }}</p>
        <el-input
          v-model="audit.remark"
          type="textarea"
          :rows="3"
          maxlength="200"
          show-word-limit
          :placeholder="approveRemarkPlaceholder"
        />
        <p v-if="minApproveRemarkHint && minApproveRemarkWords > 0" class="audit-meta hint-line">{{ minApproveRemarkHint }}</p>
      </label>
      <label v-if="allowApproveRemarkAttach" class="audit-field" style="margin-top: 12px">
        <span class="lab">{{ approveRemarkAttachLabel }}（选填）</span>
        <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap">
          <el-upload :show-file-list="false" :http-request="uploadApproveAttach" accept="image/*,.pdf,.doc,.docx">
            <el-button size="small">{{ audit.approveAttachUrl ? '重新上传' : '上传附件' }}</el-button>
          </el-upload>
          <a
            v-if="audit.approveAttachUrl"
            :href="audit.approveAttachUrl"
            target="_blank"
            rel="noopener noreferrer"
          >已上传</a>
        </div>
        <p v-if="approveRemarkAttachHint" class="audit-meta hint-line">{{ approveRemarkAttachHint }}</p>
      </label>
      <label v-if="allowApproveCc" class="audit-field" style="margin-top: 12px">
        <span class="lab">{{ approveCcLabel }}</span>
        <el-select
          v-model="audit.ccUsernames"
          multiple
          filterable
          clearable
          :placeholder="approveCcHint || '选填，抄送人仅收站内通知'"
          style="width: 100%"
        >
          <el-option
            v-for="t in dispatchTargets"
            :key="'cc-' + t.username"
            :label="dispatchLabel(t)"
            :value="t.username"
          />
        </el-select>
        <p v-if="approveDueSoonHint" class="audit-meta hint-line" style="margin-top:8px">{{ approveDueSoonHint }}</p>
      </label>
      <label v-if="audit.pass && showDispatch && isFinalPass(audit.row)" class="audit-field" style="margin-top: 12px">
        <span class="lab">派给（选填）</span>
        <el-alert
          v-if="dispatchHint"
          type="info"
          :closable="false"
          show-icon
          :title="dispatchHint"
          style="margin-bottom:8px"
        />
        <el-select
          v-if="allowSkillTag"
          v-model="audit.skillFilter"
          clearable
          filterable
          allow-create
          default-first-option
          :placeholder="skillFilterHint"
          style="width: 100%; margin-bottom: 8px"
        >
          <el-option v-for="s in skillOptions" :key="s" :label="s" :value="s" />
        </el-select>
        <el-input
          v-if="locationFilterOn"
          v-model="audit.locationFilter"
          clearable
          :placeholder="locationFilterHint"
          style="width: 100%; margin-bottom: 8px"
        />
        <el-select
          v-model="audit.assigneeUsername"
          clearable
          filterable
          placeholder="默认派给当前操作人"
          style="width: 100%"
        >
          <el-option
            v-for="t in filteredDispatchTargets"
            :key="t.username"
            :label="dispatchLabel(t)"
            :value="t.username"
          />
        </el-select>
      </label>
      <label v-if="audit.pass && allowHelper" class="audit-field" style="margin-top: 12px">
        <span class="lab">协助人（选填）</span>
        <el-select v-model="audit.helperUsername" clearable filterable placeholder="可选" style="width:100%">
          <el-option
            v-for="t in dispatchTargets"
            :key="'h-' + t.username"
            :label="dispatchLabel(t)"
            :value="t.username"
          />
        </el-select>
      </label>
      <label v-if="audit.pass && allowQuote" class="audit-field" style="margin-top: 12px">
        <span class="lab">{{ quoteLabel }}</span>
        <el-input-number v-model="audit.quoteYuan" :min="0" :max="999999" :precision="2" />
      </label>
      <label v-if="audit.pass && allowQuote" class="audit-field" style="margin-top: 12px">
        <span class="lab">{{ materialFeeLabel }}</span>
        <el-input-number v-model="audit.materialFeeYuan" :min="0" :max="999999" :precision="2" />
      </label>
      <label v-if="audit.pass && allowDisburseBatch" class="audit-field" style="margin-top: 12px">
        <span class="lab">{{ disburseBatchLabel }}</span>
        <el-input v-model="audit.disburseBatch" maxlength="64" :placeholder="`选填${disburseBatchLabel}`" />
      </label>
      <label v-if="audit.pass && allowExcellentMark" class="audit-field" style="margin-top: 12px">
        <el-checkbox v-model="audit.excellentMark">{{ excellentMarkLabel }}</el-checkbox>
      </label>
      <label v-if="audit.pass && requireMeetingAck" class="audit-field" style="margin-top: 12px">
        <el-checkbox v-model="audit.ownerMeetingAck">{{ ownerMeetingAckLabel }}</el-checkbox>
      </label>
      <label v-if="audit.pass && allowAssignDept" class="audit-field" style="margin-top: 12px">
        <span class="lab">{{ assignDeptLabel }}</span>
        <el-input v-model="audit.assignDept" maxlength="64" :placeholder="`选填${assignDeptLabel}`" />
      </label>
      <label v-if="audit.pass && allowExceptionClose" class="audit-field" style="margin-top: 12px">
        <span class="lab">{{ exceptionReasonLabel }}</span>
        <el-input v-model="audit.exceptionReason" maxlength="128" :placeholder="`异常件原因（选填）`" />
      </label>
      <label v-if="audit.pass && allowExceptionClose" class="audit-field" style="margin-top: 12px">
        <span class="lab">{{ damageClaimLabel }}</span>
        <el-input v-model="audit.damageClaimNote" type="textarea" :rows="2" maxlength="255" />
      </label>
      <template #footer>
        <el-button @click="audit.visible = false">取消</el-button>
        <el-button
          type="primary"
          :loading="audit.loading"
          :disabled="!audit.pass && !audit.remark.trim()"
          @click="submitAudit"
        >确定</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="proofDlg.visible" title="核验认领凭证" width="520px" destroy-on-close>
      <el-table :data="proofDlg.list" stripe size="small">
        <el-table-column prop="proofType" label="类型" width="90">
          <template #default="{ row }">
            {{ ({ photo: '照片', desc: '描述', receipt: '购买凭证' })[row.proofType] || row.proofType }}
          </template>
        </el-table-column>
        <el-table-column prop="proofContent" label="内容" min-width="180" show-overflow-tooltip />
        <el-table-column prop="verifyStatus" label="状态" width="90" />
        <el-table-column label="操作" width="140">
          <template #default="{ row }">
            <template v-if="row.verifyStatus === 'pending'">
              <el-button link type="success" @click="verifyProof(row, true)">通过</el-button>
              <el-button link type="danger" @click="verifyProof(row, false)">驳回</el-button>
            </template>
            <span v-else class="muted">已处理</span>
          </template>
        </el-table-column>
      </el-table>
      <template #footer>
        <el-button @click="proofDlg.visible = false">关闭</el-button>
      </template>
    </el-dialog>

    <TicketProgressDialog v-model="progressVisible" :ticket-id="progressId" />

    <el-dialog v-model="reassign.visible" :title="reassignDialogTitle" width="420px" destroy-on-close>
      <p class="audit-tip" v-if="reassign.row">
        将「{{ reassign.row.title || ('编号 ' + reassign.row.id) }}」{{ allowApproveTransfer ? '转给其他审核人' : '转给其他处理人' }}
      </p>
      <p v-if="allowApproveTransfer && approveTransferHint" class="audit-meta hint-line">{{ approveTransferHint }}</p>
      <el-alert
        v-if="dispatchHint"
        type="info"
        :closable="false"
        show-icon
        :title="dispatchHint"
        style="margin-bottom:8px"
      />
      <el-select
        v-if="allowSkillTag"
        v-model="reassign.skillFilter"
        clearable
        filterable
        allow-create
        default-first-option
        :placeholder="skillFilterHint"
        style="width:100%;margin-bottom:8px"
      >
        <el-option v-for="s in skillOptions" :key="s" :label="s" :value="s" />
      </el-select>
      <el-input
        v-if="locationFilterOn"
        v-model="reassign.locationFilter"
        clearable
        :placeholder="locationFilterHint"
        style="width:100%;margin-bottom:8px"
      />
      <el-select
        v-model="reassign.to"
        filterable
        placeholder="选择处理人"
        style="width:100%"
      >
        <el-option
          v-for="t in filteredReassignTargets"
          :key="t.username"
          :label="dispatchLabel(t)"
          :value="t.username"
        />
      </el-select>
      <el-input
        v-model="reassign.remark"
        type="textarea"
        :rows="2"
        maxlength="200"
        placeholder="转派说明（选填）"
        style="margin-top:12px"
      />
      <template #footer>
        <el-button @click="reassign.visible = false">取消</el-button>
        <el-button type="primary" :loading="reassign.loading" @click="submitReassign">确认转派</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="credit.visible" :title="`人工调整${creditScoreLabel}`" width="440px" destroy-on-close>
      <label class="audit-field">
        <span class="lab">用户名</span>
        <el-input v-model="credit.username" maxlength="64" placeholder="填写用户登录名" />
      </label>
      <label class="audit-field" style="margin-top:12px">
        <span class="lab">调整分值（正数加分 / 负数扣分）</span>
        <el-input-number v-model="credit.delta" :min="-100" :max="100" :step="1" />
      </label>
      <label class="audit-field" style="margin-top:12px">
        <span class="lab">事由（选填）</span>
        <el-input v-model="credit.reason" maxlength="128" placeholder="如：逾期归还扣分 / 申诉恢复" />
      </label>
      <template #footer>
        <el-button @click="credit.visible = false">取消</el-button>
        <el-button type="primary" :loading="credit.loading" @click="submitCredit">确定</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="delegate.visible" :title="approveDelegateLabel" width="420px" destroy-on-close>
      <p v-if="approveDelegateHint" class="audit-tip">{{ approveDelegateHint }}</p>
      <p v-if="delegate.current?.delegateUsername" class="audit-meta hint-line" style="margin-bottom:12px">
        当前代审：{{ delegate.current.delegateUsername }}
        <template v-if="delegate.current.untilAt"> · 至 {{ delegate.current.untilAt }}</template>
        <template v-if="delegate.current.active"> · 生效中</template>
      </p>
      <label class="audit-field">
        <span class="lab">代审人</span>
        <el-select
          v-model="delegate.to"
          filterable
          clearable
          placeholder="选择代审人"
          style="width:100%"
        >
          <el-option
            v-for="t in dispatchTargets"
            :key="'dlg-' + t.username"
            :label="dispatchLabel(t)"
            :value="t.username"
          />
        </el-select>
      </label>
      <label class="audit-field" style="margin-top:12px">
        <span class="lab">截止日期</span>
        <el-date-picker
          v-model="delegate.untilAt"
          type="datetime"
          value-format="YYYY-MM-DD HH:mm:ss"
          placeholder="选择截止日期"
          style="width:100%"
        />
      </label>
      <template #footer>
        <el-button v-if="delegate.current?.delegateUsername" @click="clearDelegate">取消代审</el-button>
        <el-button @click="delegate.visible = false">关闭</el-button>
        <el-button type="primary" :loading="delegate.loading" @click="submitDelegate">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="ccComment.visible" :title="approveCcCommentLabel" width="420px" destroy-on-close>
      <p v-if="approveCcCommentHint" class="audit-tip">{{ approveCcCommentHint }}</p>
      <p class="audit-tip" v-if="ccComment.row">
        「{{ ccComment.row.title || ('编号 ' + ccComment.row.id) }}」
      </p>
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

    <el-dialog v-model="walkIn.visible" :title="visitWalkInLabel" width="440px" destroy-on-close>
      <p v-if="visitWalkInHint" class="audit-tip">{{ visitWalkInHint }}</p>
      <label class="audit-field">
        <span class="lab">来访对象</span>
        <el-select v-model="walkIn.itemId" filterable placeholder="请选择" style="width:100%">
          <el-option v-for="it in archiveItems" :key="it.id" :label="it.title || ('编号 ' + it.id)" :value="it.id" />
        </el-select>
      </label>
      <label class="audit-field" style="margin-top:12px">
        <span class="lab">{{ visitWalkInForLabel }}</span>
        <el-select v-model="walkIn.forUsername" filterable placeholder="请选择" style="width:100%">
          <el-option v-for="u in userOptions" :key="u.username" :label="u.nickname ? `${u.nickname}（${u.username}）` : u.username" :value="u.username" />
        </el-select>
      </label>
      <label class="audit-field" style="margin-top:12px">
        <span class="lab">来访日期</span>
        <el-date-picker v-model="walkIn.visitOn" type="date" value-format="YYYY-MM-DD" placeholder="请选择" style="width:100%" />
      </label>
      <label class="audit-field" style="margin-top:12px">
        <span class="lab">说明</span>
        <el-input v-model="walkIn.remark" maxlength="200" />
      </label>
      <template #footer>
        <el-button @click="walkIn.visible = false">取消</el-button>
        <el-button type="primary" :loading="walkIn.loading" @click="submitWalkIn">确定</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="checkinProxy.visible" :title="checkinProxyLabel" width="440px" destroy-on-close>
      <p v-if="checkinProxyHint" class="audit-tip">{{ checkinProxyHint }}</p>
      <label class="audit-field">
        <span class="lab">查寝对象</span>
        <el-select v-model="checkinProxy.itemId" filterable placeholder="请选择" style="width:100%">
          <el-option v-for="it in archiveItems" :key="'c' + it.id" :label="it.title || ('编号 ' + it.id)" :value="it.id" />
        </el-select>
      </label>
      <label class="audit-field" style="margin-top:12px">
        <span class="lab">{{ checkinProxyForLabel }}</span>
        <el-select v-model="checkinProxy.forUsername" filterable placeholder="请选择" style="width:100%">
          <el-option v-for="u in userOptions" :key="'c' + u.username" :label="u.nickname ? `${u.nickname}（${u.username}）` : u.username" :value="u.username" />
        </el-select>
      </label>
      <label class="audit-field" style="margin-top:12px">
        <span class="lab">说明</span>
        <el-input v-model="checkinProxy.remark" maxlength="200" />
      </label>
      <template #footer>
        <el-button @click="checkinProxy.visible = false">取消</el-button>
        <el-button type="primary" :loading="checkinProxy.loading" @click="submitCheckinProxy">确定</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="evalUrge.visible" :title="evalUrgeLabel" width="440px" destroy-on-close>
      <p v-if="evalUrgeHint" class="audit-tip">{{ evalUrgeHint }}</p>
      <label class="audit-field">
        <span class="lab">课程</span>
        <el-select v-model="evalUrge.itemId" filterable placeholder="请选择" style="width:100%">
          <el-option v-for="it in archiveItems" :key="'e' + it.id" :label="it.title || ('编号 ' + it.id)" :value="it.id" />
        </el-select>
      </label>
      <template #footer>
        <el-button @click="evalUrge.visible = false">取消</el-button>
        <el-button type="primary" :loading="evalUrge.loading" @click="submitEvalUrge">发送催评</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="spotCheck.visible" :title="checkinSpotLabel" width="520px" destroy-on-close>
      <p v-if="checkinSpotHint" class="audit-tip">{{ checkinSpotHint }}</p>
      <label class="audit-field">
        <span class="lab">查寝对象</span>
        <el-select v-model="spotCheck.itemId" filterable placeholder="请选择" style="width:100%">
          <el-option v-for="it in archiveItems" :key="'s' + it.id" :label="it.title || ('编号 ' + it.id)" :value="it.id" />
        </el-select>
      </label>
      <label class="audit-field" style="margin-top:12px">
        <span class="lab">{{ checkinSpotOnLabel }}</span>
        <el-date-picker v-model="spotCheck.onDate" type="date" value-format="YYYY-MM-DD" placeholder="请选择" style="width:100%" />
      </label>
      <label class="audit-field" style="margin-top:12px">
        <span class="lab">{{ checkinSpotSampleLabel }}</span>
        <el-input-number v-model="spotCheck.sampleN" :min="1" :max="200" :step="1" />
      </label>
      <template #footer>
        <el-button @click="spotCheck.visible = false">取消</el-button>
        <el-button type="primary" :loading="spotCheck.loading" @click="submitSpotCheck">生成名单</el-button>
      </template>
      <el-table :data="spotCheck.list" size="small" stripe style="margin-top:16px" max-height="240">
        <el-table-column prop="onDate" :label="checkinSpotOnLabel" width="120" />
        <el-table-column prop="sampleN" :label="checkinSpotSampleLabel" width="90" />
        <el-table-column label="名单" min-width="180" show-overflow-tooltip>
          <template #default="{ row }">{{ formatSpotMembers(row.members) }}</template>
        </el-table-column>
        <template #empty>还没有抽查任务</template>
      </el-table>
    </el-dialog>

    <el-dialog v-model="checkinDaily.visible" :title="checkinDailyLabel" width="560px" destroy-on-close>
      <p v-if="checkinDailyHint" class="audit-tip">{{ checkinDailyHint }}</p>
      <label class="audit-field">
        <span class="lab">{{ checkinDailyOnLabel }}</span>
        <el-date-picker v-model="checkinDaily.onDate" type="date" value-format="YYYY-MM-DD" placeholder="请选择" style="width:100%" />
      </label>
      <p class="sub" style="margin-top:12px">当日共 {{ checkinDaily.total }} 条 · 待审 {{ checkinDaily.pending }} · 已登记 {{ checkinDaily.approved }} · 未归 {{ checkinDaily.absent }}</p>
      <el-table :data="checkinDaily.list" size="small" stripe max-height="280" style="margin-top:8px">
        <el-table-column prop="username" label="账号" width="120" />
        <el-table-column prop="title" label="说明" min-width="160" show-overflow-tooltip />
        <el-table-column prop="status" label="状态" width="100" />
        <template #empty>这一天还没有查寝登记</template>
      </el-table>
      <template #footer>
        <el-button @click="checkinDaily.visible = false">关闭</el-button>
        <el-button type="primary" :loading="checkinDaily.loading" @click="loadCheckinDaily">刷新</el-button>
        <el-button :disabled="!checkinDaily.list.length" @click="exportCheckinDaily">导出</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="evalCollege.visible" :title="evalCollegeExportLabel" width="480px" destroy-on-close>
      <p v-if="evalCollegeExportHint" class="audit-tip">{{ evalCollegeExportHint }}</p>
      <el-table :data="evalCollege.list" size="small" stripe max-height="320">
        <el-table-column prop="college" :label="evalCollegeLabel" min-width="160" />
        <el-table-column prop="count" label="已评份数" width="110" />
        <template #empty>还没有评教记录</template>
      </el-table>
      <template #footer>
        <el-button @click="evalCollege.visible = false">关闭</el-button>
        <el-button :disabled="!evalCollege.list.length" @click="exportEvalCollege">导出</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import http from '../../api/http'
import RichTextView from '../../components/RichTextView.vue'
import TicketProgressDialog from '../../components/TicketProgressDialog.vue'
import {
  archiveCopy,
  followChannelLabel,
  getSchema,
  hasCap,
  menuLabel,
  nextFollowLabel,
  personLabel,
  roleLabel,
  ticketCopy,
  ticketDueLabel,
  ticketShowsFollowCols,
  ticketShowsLocationCol,
  ticketShowsPriorityCols,
  ticketShowsTypeCol,
} from '../../utils/domainSchema.js'
import { plainFromHtml } from '../../utils/richHtml.js'

const ticket = ticketCopy()
const archive = archiveCopy()
const verbs = computed(() => ticket.verbs || {})
const states = computed(() => ticket.states || {})
const ticketNoun = computed(() => ticket.label || '申请')
const richRemark = computed(() => !!ticket.richRemark)
const requireRemark = computed(() => !!ticket.requireRemark)
const requireClaimProof = computed(() => !!ticket.requireClaimProof || hasCap('claim_proof'))
const remarkLabel = computed(() => ticket.remarkLabel || '说明')
const twoLevel = computed(() => !!ticket.twoLevelApprove || !!ticket.threeLevelApprove)
const threeLevel = computed(() => !!ticket.threeLevelApprove)
const allowBookHold = computed(() => !!(ticket.allowBookHold || hasCap('book_hold')))
const allowQty = computed(() => !!ticket.allowQty)
const pickLoanPeriod = computed(() => !!ticket.pickLoanPeriod)
const slaDeadline = computed(() => !!ticket.slaDeadline)
const applicantCompleteOnly = computed(() => !!ticket.applicantCompleteOnly)
const dueLabel = computed(() => ticketDueLabel(slaDeadline.value ? '处理时限' : '到期日'))
const userLabel = computed(() => roleLabel('user', '用户'))
const recordsLabel = computed(() => menuLabel('admin', 'ticket_records', ticket.recordsMenu || '记录'))
const showFollowCols = computed(() => ticketShowsFollowCols())
const channelLabel = computed(() => followChannelLabel())
const nextAtLabel = computed(() => nextFollowLabel())
const showTypeCol = computed(() => ticketShowsTypeCol(archive))
const showLocationCol = computed(() => ticketShowsLocationCol(archive))
const showPriorityCols = computed(() => ticketShowsPriorityCols())
const labels = computed(() => getSchema()?.labels || {})
const rejectReasonRequired = computed(
  () => labels.value.rejectReasonRequired || '请填写驳回原因，申请人可见',
)
const approvePhrases = computed(() => {
  const raw = ticket.approvePhrases
  if (Array.isArray(raw)) return raw.map((x) => String(x || '').trim()).filter(Boolean)
  return []
})
const approvePhraseLabel = computed(() => labels.value.approvePhraseLabel || '常用意见')
const approvePhraseHint = computed(() => labels.value.approvePhraseHint || '')
const minApproveRemarkWords = computed(() => Math.max(0, Number(ticket.minApproveRemarkWords) || 0))
const minApproveRemarkHint = computed(() => labels.value.minApproveRemarkHint || '')
const allowApproveCc = computed(() => !!ticket.allowApproveCc)
const approveCcLabel = computed(() => labels.value.approveCcLabel || '抄送知会')
const approveCcHint = computed(() => labels.value.approveCcHint || '')
const approveDueSoonHint = computed(() => labels.value.approveDueSoonHint || '')
const allowApproveTransfer = computed(() => !!ticket.allowApproveTransfer)
const approveTransferLabel = computed(() => labels.value.approveTransferLabel || '转审')
const approveTransferHint = computed(() => labels.value.approveTransferHint || '')
const allowApproveDelegate = computed(() => !!ticket.allowApproveDelegate)
const approveDelegateLabel = computed(() => labels.value.approveDelegateLabel || '请假代审')
const approveDelegateHint = computed(() => labels.value.approveDelegateHint || '')
const allowApproveRemarkAttach = computed(() => !!ticket.allowApproveRemarkAttach)
const approveRemarkAttachLabel = computed(() => labels.value.approveRemarkAttachLabel || '审核意见附件')
const approveRemarkAttachHint = computed(() => labels.value.approveRemarkAttachHint || '')
const allowApproveCcComment = computed(() => !!ticket.allowApproveCcComment)
const approveCcCommentLabel = computed(() => labels.value.approveCcCommentLabel || '知会评论')
const approveCcCommentHint = computed(() => labels.value.approveCcCommentHint || '')
const approveAutoPassHint = computed(() => labels.value.approveAutoPassHint || '')
const reassignActionLabel = computed(() =>
  allowApproveTransfer.value && !repairThickenOn.value
    ? approveTransferLabel.value
    : (allowApproveTransfer.value ? approveTransferLabel.value : '转派'),
)
const reassignDialogTitle = computed(() =>
  allowApproveTransfer.value ? approveTransferLabel.value : '转派处理人',
)
const approveRemarkPlaceholder = computed(() => {
  if (!audit.pass) return rejectReasonRequired.value
  if (minApproveRemarkWords.value > 0) return minApproveRemarkHint.value || '请填写审核意见'
  return '可填写受理说明，留空则保留申请说明'
})
function applyApprovePhrase(v) {
  const text = String(v || '').trim()
  if (!text) return
  audit.remark = text
  audit.phrasePick = ''
}
// 事件等级 → 处理时限（bake: ticket-level-sla-*-days 由 /api/tickets 回显）
const levelSlaDays = ref('')
const dutyNotifyOn = ref(false)
const levelSlaHint = computed(() => labels.value.levelSlaHint || '')
const notifyDutyHint = computed(() => labels.value.notifyDutyHint || '')
const levelSlaText = computed(() => {
  const parts = String(levelSlaDays.value || '').split(',').map((s) => String(s || '').trim())
  if (parts.length < 3 || !parts[0]) return ''
  return `高 ${parts[0]} 天 / 中 ${parts[1]} 天 / 低 ${parts[2]} 天`
})
const creditOn = computed(() => !!ticket.creditOnOverdue || !!ticket.creditPoints)
const creditScoreLabel = computed(() => labels.value.creditScoreLabel || '信誉分')
const creditRows = ref([])
const credit = reactive({
  visible: false,
  username: '',
  delta: -5,
  reason: '',
  loading: false,
})

/** 管理端信誉分台账：credit-on-overdue 未开时不开面。 */
async function loadCredit() {
  if (!creditOn.value) return
  const res = await http.get('/api/tickets/credit/ledger')
  creditRows.value = res.data?.rows || []
}

function openCredit() {
  Object.assign(credit, { visible: true, username: '', delta: -5, reason: '' })
}

/** 人工调整：正数加分 / 负数扣分，落 credit_ledger 留痕。 */
async function submitCredit() {
  const username = credit.username.trim()
  if (!username) {
    ElMessage.warning('请填写用户名')
    return
  }
  if (!credit.delta) {
    ElMessage.warning('调整分值不能为 0')
    return
  }
  credit.loading = true
  try {
    await http.post('/api/tickets/credit/adjust', {
      username,
      delta: credit.delta,
      reason: credit.reason.trim(),
    })
    ElMessage.success(`${creditScoreLabel.value}已调整`)
    credit.visible = false
    loadCredit()
  } finally {
    credit.loading = false
  }
}
const repairThickenOn = computed(() => !!ticket.repairThicken || !!ticket.allowUserUrge)
const allowSkillTag = computed(() => !!ticket.allowSkillTag || !!ticket.repairThicken)
const allowHelper = computed(() => !!ticket.allowHelper)
const allowQuote = computed(() => !!ticket.allowQuote)
const allowDisburseBatch = computed(() => !!ticket.allowDisburseBatch)
const disburseBatchLabel = computed(() => labels.value.disburseBatchLabel || '发放批次号')
const allowExcellentMark = computed(() => !!ticket.allowExcellentMark)
const excellentMarkLabel = computed(() => labels.value.excellentMarkLabel || '优秀周报')
const requireMeetingAck = computed(() => !!ticket.requireMeetingAck)
const ownerMeetingAckLabel = computed(
  () => labels.value.ownerMeetingAckLabel || '启事方确认面交安排',
)
const allowAssignDept = computed(() => !!ticket.allowAssignDept)
const assignDeptLabel = computed(() => labels.value.assignDeptLabel || '分拨科室')
const allowExceptionClose = computed(() => !!ticket.allowExceptionClose)
const exceptionReasonLabel = computed(() => labels.value.exceptionReasonLabel || '异常件原因')
const damageClaimLabel = computed(() => labels.value.damageClaimLabel || '破损理赔说明')
const categoryColorOn = computed(() => !!ticket.categoryColorHint || !!ticket.repairThicken)
const locationFilterOn = computed(() => !!(labels.value.dispatchFilterHint || ticket.repairThicken))
const skillFilterHint = computed(() => labels.value.skillFilterHint || '按技能标签筛选处理人')
const locationFilterHint = computed(() => labels.value.dispatchFilterHint || '可按地点/楼栋关键词筛选处理人')
const interviewRoomHint = computed(() => labels.value.interviewRoomHint || '')
const dispatchHint = computed(
  () => labels.value.dispatchFilterHint || labels.value.rosterConflictHint || '',
)
const quoteLabel = computed(() => labels.value.quoteLabel || '维修报价（元）')
const materialFeeLabel = computed(() => labels.value.materialFeeLabel || '材料费（元）')
const skillOptions = computed(() => {
  const list = ticket.skillTags || ticket.faultReasons
  return Array.isArray(list) && list.length
    ? list.slice(0, 12)
    : ['水电', '门锁', '网络', '照明', '综合']
})
function typeColor(key) {
  const s = String(key || '')
  let h = 0
  for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) >>> 0
  return `hsl(${h % 360} 55% 48%)`
}
const superAdmin = localStorage.getItem('superAdmin') === 'true'
/** 终审/单级受理时可选派给维修员等子管 */
const showDispatch = computed(() => applicantCompleteOnly.value || slaDeadline.value)
const allowBatchHire = computed(() => !!ticket.allowBatchHire)
const allowVisitWalkIn = computed(() => !!ticket.allowVisitWalkIn)
const visitWalkInLabel = computed(() => labels.value.visitWalkInLabel || '现场补录')
const visitWalkInForLabel = computed(() => labels.value.visitWalkInForLabel || '被访人账号')
const visitWalkInHint = computed(() => labels.value.visitWalkInHint || '')
const allowCheckinProxy = computed(() => !!ticket.allowCheckinProxy)
const checkinProxyLabel = computed(() => labels.value.checkinProxyLabel || '楼栋长代登记')
const checkinProxyForLabel = computed(() => labels.value.checkinProxyForLabel || '学生账号')
const checkinProxyHint = computed(() => labels.value.checkinProxyHint || '')
const allowEvalUrge = computed(() => !!ticket.allowEvalUrge)
const evalUrgeLabel = computed(() => labels.value.evalUrgeLabel || '催评')
const evalUrgeHint = computed(() => labels.value.evalUrgeHint || '')
const allowCheckinSpot = computed(() => !!ticket.allowCheckinSpot)
const checkinSpotLabel = computed(() => labels.value.checkinSpotLabel || '抽查任务')
const checkinSpotSampleLabel = computed(() => labels.value.checkinSpotSampleLabel || '抽查人数')
const checkinSpotOnLabel = computed(() => labels.value.checkinSpotOnLabel || '抽查日期')
const checkinSpotHint = computed(() => labels.value.checkinSpotHint || '')
const allowApproveDurationStats = computed(() => !!ticket.allowApproveDurationStats)
const approveDurationStatsLabel = computed(() => labels.value.approveDurationStatsLabel || '人均办理耗时')
const approveDurationStatsHint = computed(() => labels.value.approveDurationStatsHint || '')
const allowCheckinDailyReport = computed(() => !!ticket.allowCheckinDailyReport)
const checkinDailyLabel = computed(() => labels.value.checkinDailyLabel || '楼长日报')
const checkinDailyOnLabel = computed(() => labels.value.checkinDailyOnLabel || '汇总日期')
const checkinDailyHint = computed(() => labels.value.checkinDailyHint || '')
const allowEvalCollegeExport = computed(() => !!ticket.allowEvalCollegeExport)
const evalCollegeExportLabel = computed(() => labels.value.evalCollegeExportLabel || '院系汇总导出')
const evalCollegeLabel = computed(() => labels.value.evalCollegeLabel || '开课学院')
const evalCollegeExportHint = computed(() => labels.value.evalCollegeExportHint || '')
const archiveItems = ref([])
const userOptions = ref([])
const walkIn = reactive({ visible: false, loading: false, itemId: null, forUsername: '', visitOn: '', remark: '' })
const checkinProxy = reactive({ visible: false, loading: false, itemId: null, forUsername: '', remark: '' })
const evalUrge = reactive({ visible: false, loading: false, itemId: null })
const spotCheck = reactive({ visible: false, loading: false, itemId: null, onDate: '', sampleN: 3, list: [] })
const durationRows = ref([])
const checkinDaily = reactive({ visible: false, loading: false, onDate: '', total: 0, pending: 0, approved: 0, absent: 0, list: [] })
const evalCollege = reactive({ visible: false, list: [] })
const batchHireLabel = computed(() => labels.value.batchHireLabel || '批量录用')
const batchRejectLabel = computed(() => labels.value.batchRejectLabel || '批量淘汰')
const selectedIds = ref([])

function onSelectionChange(rows) {
  selectedIds.value = (rows || []).map((r) => r.id).filter((id) => id != null)
}

async function batchHire(pass) {
  if (!selectedIds.value.length) {
    ElMessage.warning('请先勾选单据')
    return
  }
  const action = pass ? batchHireLabel.value : batchRejectLabel.value
  let remark = pass ? '' : '批量淘汰'
  if (!pass) {
    try {
      const { value } = await ElMessageBox.prompt('请填写淘汰原因', action, {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        inputPattern: /\S+/,
        inputErrorMessage: '原因不能为空',
      })
      remark = String(value || '').trim()
    } catch {
      return
    }
  }
  const res = await http.post('/api/tickets/batch-hire', {
    ids: selectedIds.value,
    pass,
    remark,
  })
  const data = res.data || res
  const ok = data.okCount || 0
  const fail = data.failCount || 0
  if (fail > 0) {
    ElMessage.warning(`${action}完成：成功 ${ok} 条，失败 ${fail} 条`)
  } else {
    ElMessage.success(`${action}成功 ${ok} 条`)
  }
  selectedIds.value = []
  load()
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

function remarkPlain(v) {
  if (!v) return ''
  return richRemark.value ? plainFromHtml(String(v)) : String(v)
}

const todoHint = computed(() => {
  const base = `待受理 · 历史见「${recordsLabel.value}」`
  return twoLevel.value ? `${base} · 二级审批（终审需总管）` : base
})

const list = ref([])
const total = ref(0)
const page = ref(1)
const size = ref(10)

const audit = reactive({
  visible: false,
  loading: false,
  pass: true,
  remark: '',
  phrasePick: '',
  ccUsernames: [],
  approveAttachUrl: '',
  assigneeUsername: '',
  helperUsername: '',
  skillFilter: '',
  locationFilter: '',
  quoteYuan: null,
  materialFeeYuan: null,
  disburseBatch: '',
  excellentMark: false,
  ownerMeetingAck: false,
  assignDept: '',
  exceptionReason: '',
  damageClaimNote: '',
  row: null,
})
const delegate = reactive({
  visible: false,
  loading: false,
  to: '',
  untilAt: '',
  current: null,
})
const ccComment = reactive({
  visible: false,
  loading: false,
  row: null,
  text: '',
})
const reassign = reactive({
  visible: false,
  loading: false,
  row: null,
  to: '',
  remark: '',
  skillFilter: '',
  locationFilter: '',
})

const progressVisible = ref(false)
const progressId = ref(null)
const proofDlg = reactive({ visible: false, list: [], claimId: 0 })
const dispatchTargets = ref([])

const filteredDispatchTargets = computed(() =>
  filterTargets(dispatchTargets.value, audit.skillFilter, audit.locationFilter || audit.row?.location),
)
const filteredReassignTargets = computed(() =>
  filterTargets(dispatchTargets.value, reassign.skillFilter, reassign.locationFilter || reassign.row?.location),
)

function filterTargets(list, skill, locationKey) {
  let out = list || []
  const s = String(skill || '').trim()
  if (s) {
    out = out.filter((t) => {
      const blob = `${t.username || ''} ${t.nickname || ''} ${t.staffPost || ''} ${t.staffKind || ''}`
      return blob.includes(s)
    })
  }
  const loc = String(locationKey || '').trim()
  if (loc) {
    // 取地点前缀（楼栋/小区）做关键词；与处理人昵称/岗位匹配
    const token = loc.split(/[\s\-_/|，,]/)[0] || loc
    if (token.length >= 2) {
      const keyed = out.filter((t) => {
        const blob = `${t.username || ''} ${t.nickname || ''} ${t.staffPost || ''} ${t.staffKind || ''}`
        return blob.includes(token)
      })
      if (keyed.length) out = keyed
    }
  }
  return out
}

function statusText(s) {
  return (
    states.value[s]
    || ({
      pending: '待交凭证',
      verifying: '待核验',
      pending_mid: '待复审',
      pending_final: '待终审',
    }[s])
    || s
  )
}

function passLabel(row) {
  if (allowBookHold.value && row?.status === 'hold_ready') return '确认出借'
  if (row?.status === 'verifying') return verbs.value.approve || '受理'
  if (!twoLevel.value || !row) return verbs.value.approve || '受理'
  if (row.status === 'pending_final') return '终审通过'
  if (threeLevel.value && row.status === 'pending_mid') return '复审通过'
  if (threeLevel.value && row.status === 'pending') return '初审通过'
  // 二级首关：跟 verbs 文案（报修「受理」、借阅「通过」）；勿写死「初审」
  return verbs.value.approve || '受理'
}

function canPass(row) {
  if (requireClaimProof.value && row?.status === 'pending') return false
  if (!twoLevel.value) return true
  if (row?.status === 'pending_final') return superAdmin
  return true
}

/** 仅进入「处理中」的那一关展示派单 */
function isFinalPass(row) {
  if (!row) return false
  if (allowBookHold.value && row.status === 'hold_ready') return true
  if (!twoLevel.value) return true
  return row.status === 'pending_final'
}

function dispatchLabel(t) {
  const name = t.nickname || t.username
  const post = t.staffPost ? ` · ${t.staffPost}` : ''
  const duty = t.onDutyToday ? ' · 当日当班' : ''
  return `${name}${post}${duty}`
}

async function loadDispatchTargets() {
  try {
    const res = await http.get('/api/tickets/dispatch-targets')
    dispatchTargets.value = Array.isArray(res.data) ? res.data : []
  } catch {
    dispatchTargets.value = []
  }
}

async function load() {
  const res = await http.get('/api/tickets', {
    params: { page: page.value, size: size.value, status: 'todo' },
  })
  list.value = res.data.list
  total.value = res.data.total
  levelSlaDays.value = res.data.levelSlaDays || ''
  dutyNotifyOn.value = !!res.data.dutyNotify
}

async function returnRevise(row) {
  try {
    const { value } = await ElMessageBox.prompt('请填写退回修改说明', '退回修改', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      inputPlaceholder: '如：附件缺失，请补充后重交',
    })
    await http.post(`/api/tickets/${row.id}/return-revise`, { note: value || '' })
    ElMessage.success('已退回修改')
    await load()
  } catch (e) {
    if (e === 'cancel' || e === 'close') return
    ElMessage.error(e?.response?.data?.message || e?.message || '退回修改失败')
  }
}

function openAudit(row, pass) {
  if (pass && requireClaimProof.value && row.status === 'pending') {
    ElMessage.warning('请先等待用户提交认领凭证')
    return
  }
  if (pass && !canPass(row)) {
    ElMessage.warning('终审通过需总管操作')
    return
  }
  audit.row = row
  audit.pass = pass
  audit.remark = ''
  audit.phrasePick = ''
  audit.ccUsernames = []
  audit.approveAttachUrl = ''
  audit.assigneeUsername = ''
  audit.helperUsername = ''
  audit.skillFilter = ''
  audit.locationFilter = row?.location || ''
  audit.quoteYuan = row?.quoteYuan != null ? Number(row.quoteYuan) : null
  audit.materialFeeYuan = row?.materialFeeYuan != null ? Number(row.materialFeeYuan) : null
  audit.disburseBatch = row?.disburseBatch || ''
  audit.excellentMark = !!row?.excellentMark
  audit.assignDept = row?.assignDept || ''
  audit.exceptionReason = row?.exceptionReason || ''
  audit.damageClaimNote = row?.damageClaimNote || ''
  audit.visible = true
  if ((pass && showDispatch.value && isFinalPass(row)) || allowApproveCc.value || allowApproveDelegate.value) {
    loadDispatchTargets()
  }
}

function canReassign(row) {
  if (!row) return false
  if (!(repairThickenOn.value || allowApproveTransfer.value)) return false
  return ['pending', 'pending_mid', 'pending_final', 'approved', 'overdue', 'paused'].includes(row.status)
}

function canCcComment(row) {
  if (!allowApproveCcComment.value || !row) return false
  const me = (localStorage.getItem('username') || '').trim().toLowerCase()
  if (!me) return false
  const raw = String(row.ccUsernames || '')
  return raw.split(/[,;\s]+/).some((p) => p.trim().toLowerCase() === me)
}

async function loadPickLists() {
  try {
    const [a, u] = await Promise.all([
      http.get('/api/archive', { params: { page: 1, size: 200 } }),
      http.get('/api/tickets/apply-targets'),
    ])
    archiveItems.value = a.data?.list || []
    userOptions.value = Array.isArray(u.data) ? u.data : (u.data?.list || [])
  } catch {
    archiveItems.value = []
    userOptions.value = []
  }
}

async function openWalkIn() {
  walkIn.itemId = null
  walkIn.forUsername = ''
  walkIn.visitOn = ''
  walkIn.remark = ''
  walkIn.visible = true
  await loadPickLists()
}

async function submitWalkIn() {
  if (!walkIn.itemId) {
    ElMessage.warning('请选择来访对象')
    return
  }
  if (!walkIn.forUsername) {
    ElMessage.warning(`请选择${visitWalkInForLabel.value}`)
    return
  }
  if (!walkIn.visitOn) {
    ElMessage.warning('请选择来访日期')
    return
  }
  walkIn.loading = true
  try {
    await http.post('/api/tickets/walk-in', {
      itemId: walkIn.itemId,
      forUsername: walkIn.forUsername,
      visitOn: walkIn.visitOn,
      remark: walkIn.remark,
      walkIn: true,
    })
    ElMessage.success('已补录')
    walkIn.visible = false
    load()
  } finally {
    walkIn.loading = false
  }
}

async function openCheckinProxy() {
  checkinProxy.itemId = null
  checkinProxy.forUsername = ''
  checkinProxy.remark = ''
  checkinProxy.visible = true
  await loadPickLists()
}

async function submitCheckinProxy() {
  if (!checkinProxy.itemId) {
    ElMessage.warning('请选择查寝对象')
    return
  }
  if (!checkinProxy.forUsername) {
    ElMessage.warning(`请选择${checkinProxyForLabel.value}`)
    return
  }
  checkinProxy.loading = true
  try {
    await http.post('/api/tickets/checkin-proxy', {
      itemId: checkinProxy.itemId,
      forUsername: checkinProxy.forUsername,
      remark: checkinProxy.remark,
    })
    ElMessage.success('已代登记')
    checkinProxy.visible = false
    load()
  } finally {
    checkinProxy.loading = false
  }
}

async function openEvalUrge() {
  evalUrge.itemId = null
  evalUrge.visible = true
  await loadPickLists()
}

async function submitEvalUrge() {
  if (!evalUrge.itemId) {
    ElMessage.warning('请选择课程')
    return
  }
  evalUrge.loading = true
  try {
    const res = await http.post('/api/tickets/eval-urge', { itemId: evalUrge.itemId })
    const n = res.data?.sent
    ElMessage.success(n != null ? `已向 ${n} 位同学发送催评` : '已发送催评')
    evalUrge.visible = false
  } finally {
    evalUrge.loading = false
  }
}

function formatSpotMembers(raw) {
  if (!Array.isArray(raw)) return ''
  return raw.map((x) => x.username || '').filter(Boolean).join('，')
}

async function loadDurationStats() {
  if (!allowApproveDurationStats.value) {
    durationRows.value = []
    return
  }
  try {
    const res = await http.get('/api/tickets/approve-duration-stats')
    durationRows.value = res.data?.data || res.data || []
  } catch {
    durationRows.value = []
  }
}

function downloadCsv(filename, headers, rows) {
  const lines = [headers.join(','), ...rows.map((r) => r.map((c) => `"${String(c ?? '').replace(/"/g, '""')}"`).join(','))]
  const blob = new Blob(['\ufeff' + lines.join('\n')], { type: 'text/csv;charset=utf-8' })
  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = filename
  a.click()
  URL.revokeObjectURL(a.href)
}

async function openCheckinDaily() {
  checkinDaily.onDate = ''
  checkinDaily.visible = true
  await loadCheckinDaily()
}

async function loadCheckinDaily() {
  checkinDaily.loading = true
  try {
    const res = await http.get('/api/tickets/checkin-daily', {
      params: { onDate: checkinDaily.onDate || undefined },
    })
    const data = res.data?.data || res.data || {}
    checkinDaily.onDate = data.onDate || checkinDaily.onDate
    checkinDaily.total = Number(data.total || 0)
    checkinDaily.pending = Number(data.pending || 0)
    checkinDaily.approved = Number(data.approved || 0)
    checkinDaily.absent = Number(data.absent || 0)
    checkinDaily.list = data.list || []
  } finally {
    checkinDaily.loading = false
  }
}

function exportCheckinDaily() {
  downloadCsv(
    `checkin-daily-${checkinDaily.onDate || 'export'}.csv`,
    ['账号', '说明', '状态'],
    (checkinDaily.list || []).map((r) => [r.username, r.title, r.status]),
  )
}

async function openEvalCollege() {
  evalCollege.visible = true
  try {
    const res = await http.get('/api/tickets/eval-college-stats')
    evalCollege.list = res.data?.data || res.data || []
  } catch {
    evalCollege.list = []
  }
}

function exportEvalCollege() {
  downloadCsv(
    'eval-college.csv',
    [evalCollegeLabel.value, '已评份数'],
    (evalCollege.list || []).map((r) => [r.college, r.count]),
  )
}

async function openSpotCheck() {
  spotCheck.itemId = null
  spotCheck.onDate = ''
  spotCheck.sampleN = 3
  spotCheck.visible = true
  await loadPickLists()
  await loadSpotList()
}

async function loadSpotList() {
  try {
    const res = await http.get('/api/tickets/spot-check', {
      params: { itemId: spotCheck.itemId || undefined },
    })
    spotCheck.list = res.data?.data || res.data || []
  } catch {
    spotCheck.list = []
  }
}

async function submitSpotCheck() {
  if (!spotCheck.itemId) {
    ElMessage.warning('请选择查寝对象')
    return
  }
  if (!spotCheck.onDate) {
    ElMessage.warning(`请选择${checkinSpotOnLabel.value}`)
    return
  }
  spotCheck.loading = true
  try {
    await http.post('/api/tickets/spot-check', {
      itemId: spotCheck.itemId,
      onDate: spotCheck.onDate,
      sampleN: spotCheck.sampleN,
    })
    ElMessage.success('已生成抽查名单')
    await loadSpotList()
  } finally {
    spotCheck.loading = false
  }
}

async function openDelegate() {
  delegate.to = ''
  delegate.untilAt = ''
  delegate.current = null
  delegate.visible = true
  await loadDispatchTargets()
  try {
    const res = await http.get('/api/tickets/approve-delegate')
    delegate.current = res.data || null
    if (delegate.current?.delegateUsername) {
      delegate.to = delegate.current.delegateUsername
      delegate.untilAt = delegate.current.untilAt || ''
    }
  } catch {
    delegate.current = null
  }
}

async function submitDelegate() {
  if (!delegate.to) {
    ElMessage.warning('请选择代审人')
    return
  }
  if (!delegate.untilAt) {
    ElMessage.warning('请选择截止日期')
    return
  }
  delegate.loading = true
  try {
    await http.post('/api/tickets/approve-delegate', {
      delegateUsername: delegate.to,
      untilAt: delegate.untilAt,
    })
    ElMessage.success('已保存代审')
    delegate.visible = false
  } finally {
    delegate.loading = false
  }
}

async function clearDelegate() {
  delegate.loading = true
  try {
    await http.post('/api/tickets/approve-delegate/clear')
    ElMessage.success('已取消代审')
    delegate.visible = false
  } finally {
    delegate.loading = false
  }
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

async function uploadApproveAttach(opt) {
  const fd = new FormData()
  fd.append('file', opt.file)
  const res = await http.post('/api/upload', fd)
  audit.approveAttachUrl = res.data?.url || res.data?.data?.url || ''
  if (!audit.approveAttachUrl) ElMessage.warning('上传失败')
}

async function openReassign(row) {
  reassign.row = row
  reassign.to = ''
  reassign.remark = ''
  reassign.skillFilter = row.skillTag || ''
  reassign.locationFilter = row.location || ''
  reassign.visible = true
  await loadDispatchTargets()
}

async function submitReassign() {
  if (!reassign.row) return
  if (!reassign.to) {
    ElMessage.warning('请选择转派对象')
    return
  }
  reassign.loading = true
  try {
    const body = {
      assigneeUsername: reassign.to,
      remark: reassign.remark,
    }
    if (allowSkillTag.value && reassign.skillFilter) {
      body.skillTag = reassign.skillFilter
    }
    await http.post(`/api/tickets/${reassign.row.id}/reassign`, body)
    ElMessage.success('已转派')
    reassign.visible = false
    load()
  } finally {
    reassign.loading = false
  }
}

async function openProofVerify(row) {
  proofDlg.claimId = row.id
  proofDlg.visible = true
  const res = await http.get('/api/lost/proof', { params: { claimId: row.id } })
  proofDlg.list = res.data || []
}

async function verifyProof(row, pass) {
  await http.post(`/api/lost/proof/${row.id}/verify`, { pass })
  ElMessage.success(pass ? '凭证已通过，可继续受理' : '凭证已驳回，用户可重交')
  const res = await http.get('/api/lost/proof', { params: { claimId: proofDlg.claimId } })
  proofDlg.list = res.data || []
  load()
}

function resetAudit() {
  audit.row = null
  audit.remark = ''
  audit.phrasePick = ''
  audit.ccUsernames = []
  audit.approveAttachUrl = ''
  audit.assigneeUsername = ''
  audit.helperUsername = ''
  audit.skillFilter = ''
  audit.locationFilter = ''
  audit.quoteYuan = null
  audit.materialFeeYuan = null
  audit.disburseBatch = ''
  audit.excellentMark = false
  audit.ownerMeetingAck = false
  audit.assignDept = ''
  audit.exceptionReason = ''
  audit.damageClaimNote = ''
  audit.loading = false
}

async function submitAudit() {
  if (!audit.row) return
  const remark = audit.remark.trim()
  if (!audit.pass && !remark) {
    ElMessage.warning(rejectReasonRequired.value)
    return
  }
  if (minApproveRemarkWords.value > 0) {
    const words = remark.replace(/\s+/g, '').length
    if (words < minApproveRemarkWords.value) {
      ElMessage.warning(minApproveRemarkHint.value || `审核意见不少于 ${minApproveRemarkWords.value} 字`)
      return
    }
  }
  if (audit.pass && requireMeetingAck.value && !audit.ownerMeetingAck) {
    ElMessage.warning(ownerMeetingAckLabel.value || '请勾选启事方确认面交安排')
    return
  }
  audit.loading = true
  try {
    const body = {
      pass: audit.pass,
      remark,
    }
    if (allowApproveCc.value && Array.isArray(audit.ccUsernames) && audit.ccUsernames.length) {
      body.ccUsernames = audit.ccUsernames
    }
    if (allowApproveRemarkAttach.value && audit.approveAttachUrl) {
      body.approveAttachUrl = audit.approveAttachUrl
    }
    if (audit.pass && showDispatch.value && isFinalPass(audit.row) && audit.assigneeUsername) {
      body.assigneeUsername = audit.assigneeUsername
    }
    if (audit.pass && allowHelper.value && audit.helperUsername) {
      body.helperUsername = audit.helperUsername
    }
    if (audit.pass && allowSkillTag.value && audit.skillFilter) {
      body.skillTag = audit.skillFilter
    }
    if (audit.pass && allowQuote.value) {
      if (audit.quoteYuan != null) body.quoteYuan = audit.quoteYuan
      if (audit.materialFeeYuan != null) body.materialFeeYuan = audit.materialFeeYuan
    }
    if (audit.pass && allowDisburseBatch.value && (audit.disburseBatch || '').trim()) {
      body.disburseBatch = audit.disburseBatch.trim()
    }
    if (audit.pass && allowExcellentMark.value) {
      body.excellentMark = !!audit.excellentMark
    }
    if (audit.pass && requireMeetingAck.value) {
      body.ownerMeetingAck = !!audit.ownerMeetingAck
    }
    if (audit.pass && allowAssignDept.value && (audit.assignDept || '').trim()) {
      body.assignDept = audit.assignDept.trim()
    }
    if (audit.pass && allowExceptionClose.value) {
      if ((audit.exceptionReason || '').trim()) body.exceptionReason = audit.exceptionReason.trim()
      if ((audit.damageClaimNote || '').trim()) body.damageClaimNote = audit.damageClaimNote.trim()
    }
    const res = await http.post(`/api/tickets/${audit.row.id}/approve`, body)
    const n = Number(res?.data?.autoRejectedCount) || 0
    ElMessage.success(
      audit.pass && n > 0
        ? `已处理；另有 ${n} 条同对象待审已自动驳回`
        : '已处理',
    )
    audit.visible = false
    load()
  } finally {
    audit.loading = false
  }
}

function openProgress(row) {
  progressId.value = row.id
  progressVisible.value = true
}

onMounted(() => {
  load()
  loadCredit()
  loadDurationStats()
})
</script>

<style scoped>
.toolbar { margin-bottom: 12px; display: flex; gap: 8px; flex-wrap: wrap; align-items: center; }
.sub { margin: 0 0 8px; font-size: 13px; color: var(--el-text-color-secondary); }
.pager { margin-top: 16px; display: flex; justify-content: flex-end; }
.audit-tip {
  margin: 0 0 14px;
  font-size: 14px;
  color: var(--el-text-color-regular);
  line-height: 1.5;
}
.audit-field {
  display: flex;
  flex-direction: column;
  gap: 8px;
  font-size: 13px;
  color: var(--el-text-color-primary);
}
.lab { font-weight: 500; }
.audit-body {
  margin: 0 0 14px;
  padding: 10px 12px;
  border-radius: var(--portal-radius-sm, 8px);
  background: color-mix(in srgb, var(--portal-bg, #f8fafc) 72%, var(--portal-surface, #fff));
  border: var(--portal-border-width, 1px) solid var(--portal-line, #e2e8f0);
}
.audit-body .lab { margin-bottom: 6px; font-size: 13px; color: var(--portal-muted, #64748b); }
.audit-body a { color: var(--portal-accent, #0369a1); font-size: 13px; }
.audit-meta {
  margin: 0 0 4px;
  font-size: 13px;
  color: var(--portal-ink, #334155);
  line-height: 1.5;
  white-space: pre-wrap;
  word-break: break-word;
}
.audit-meta:last-child { margin-bottom: 0; }
.req {
  color: var(--el-color-danger, #f56c6c);
  margin-left: 2px;
  font-style: normal;
  font-weight: 600;
}
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
