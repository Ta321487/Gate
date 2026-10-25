<template>
  <div
    class="approve-desk"
    :class="{
      'surface-typelist': approveSurface === 'typelist',
      'surface-inboxsteps': approveSurface === 'inboxsteps',
    }"
    :data-approve-surface="approveSurface || undefined"
  >
    <div class="toolbar">
      <el-alert type="info" :closable="false" show-icon :title="todoHint" />
    </div>
    <div
      v-if="approveSurface === 'inboxsteps' && approveInboxStats"
      class="approve-inbox-bar"
      data-approve-inbox="stats"
    >
      <span class="inbox-stat" data-stat="total">待我审 {{ approveInboxStats.total }}</span>
      <span class="inbox-stat" data-stat="pending">待初审 {{ approveInboxStats.pending }}</span>
      <span class="inbox-stat" data-stat="mid">待复审 {{ approveInboxStats.mid }}</span>
      <span class="inbox-stat" data-stat="final">待终审 {{ approveInboxStats.final }}</span>
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
      <el-table-column label="编号" width="110">
        <template #default="{ row }"><CopyableId :value="row.id" /></template>
      </el-table-column>
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
          :placeholder="skillFilterHint || '按技能筛选'"
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
        :placeholder="skillFilterHint || '按技能筛选'"
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

<script setup src="./TicketsAdmin.setup.js"></script>

<style scoped src="./TicketsAdmin.css"></style>
