<template>
  <div>
    <div class="toolbar">
      <el-alert type="info" :closable="false" show-icon :title="todoHint" />
    </div>
    <p v-if="levelSlaText" class="sub">{{ levelSlaHint }}（{{ levelSlaText }}）</p>
    <p v-if="dutyNotifyOn" class="sub">{{ notifyDutyHint }}</p>
    <div class="toolbar">
      <el-button type="primary" @click="load">刷新待办</el-button>
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
      <el-table-column label="附件" width="90">
        <template #default="{ row }">
          <a v-if="row.attachUrl" :href="row.attachUrl" target="_blank" rel="noopener noreferrer">查看</a>
          <span v-else class="muted">—</span>
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
          >转派</el-button>
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
      <div v-if="audit.row?.attachUrl" class="audit-body">
        <div class="lab">附件</div>
        <a :href="audit.row.attachUrl" target="_blank" rel="noopener noreferrer">查看附件</a>
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
          <i v-if="!audit.pass" class="req" aria-hidden="true">*</i>
          <template v-else>（选填）</template>
        </span>
        <el-input
          v-model="audit.remark"
          type="textarea"
          :rows="3"
          maxlength="200"
          show-word-limit
          :placeholder="audit.pass ? '可填写受理说明，留空则保留申请说明' : '请说明驳回原因，申请人可见'"
        />
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

    <el-dialog v-model="reassign.visible" title="转派处理人" width="420px" destroy-on-close>
      <p class="audit-tip" v-if="reassign.row">
        将「{{ reassign.row.title || ('编号 ' + reassign.row.id) }}」转给其他处理人
      </p>
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
  assigneeUsername: '',
  helperUsername: '',
  skillFilter: '',
  locationFilter: '',
  quoteYuan: null,
  materialFeeYuan: null,
  disburseBatch: '',
  excellentMark: false,
  assignDept: '',
  exceptionReason: '',
  damageClaimNote: '',
  row: null,
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
  if (pass && showDispatch.value && isFinalPass(row)) {
    loadDispatchTargets()
  }
}

function canReassign(row) {
  if (!repairThickenOn.value || !row) return false
  return ['pending', 'pending_mid', 'pending_final', 'approved', 'overdue', 'paused'].includes(row.status)
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
  audit.assigneeUsername = ''
  audit.helperUsername = ''
  audit.skillFilter = ''
  audit.locationFilter = ''
  audit.quoteYuan = null
  audit.materialFeeYuan = null
  audit.disburseBatch = ''
  audit.excellentMark = false
  audit.assignDept = ''
  audit.exceptionReason = ''
  audit.damageClaimNote = ''
  audit.loading = false
}

async function submitAudit() {
  if (!audit.row) return
  const remark = audit.remark.trim()
  if (!audit.pass && !remark) {
    ElMessage.warning('请填写驳回原因')
    return
  }
  audit.loading = true
  try {
    const body = {
      pass: audit.pass,
      remark,
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
