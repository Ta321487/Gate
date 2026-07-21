<template>
  <div>
    <section class="hero">
      <h1>{{ plural }}检索</h1>
      <p>
        按名称检索{{ playUrlField ? '、在线播放' : '' }}{{ bodyRich ? '、阅读正文' : '' }}，{{ actionHint }}。
        <template v-if="ruleHint"> {{ ruleHint }}</template>
      </p>
      <div class="search">
        <el-input
          v-model="keyword"
          size="large"
          clearable
          :placeholder="searchPlaceholder"
          @keyup.enter="load"
        />
        <el-select v-model="categoryId" clearable :placeholder="fieldLabel('category', '分类')" size="large" style="width:140px" @change="load">
          <el-option v-for="c in categories" :key="c.id" :label="c.name" :value="c.id" />
        </el-select>
        <el-select
          v-if="tagFilter"
          v-model="tagIds"
          multiple
          collapse-tags
          collapse-tags-tooltip
          clearable
          placeholder="标签（同时满足）"
          size="large"
          style="min-width:200px"
          @change="load"
        >
          <el-option v-for="t in tags" :key="t.id" :label="t.name" :value="t.id" />
        </el-select>
        <el-button type="primary" size="large" @click="load">搜索</el-button>
      </div>
    </section>

    <RecommendStrip
      v-if="hasRecommend && !isGuest"
      ref="recRef"
      :apply-label="primaryActionLabel"
      @apply="onPrimary"
    />

    <div class="grid">
      <article v-for="row in list" :key="row.id" class="card">
        <div class="cover">
          <img v-if="row.coverUrl" :src="row.coverUrl" alt="" />
          <template v-else>{{ (row.title || '?').slice(0, 1) }}</template>
        </div>
        <div class="meta">
          <h3>{{ row.title }}</h3>
          <p>{{ formatAuthor(row.author) }} · {{ row.categoryName || '未分类' }}</p>
          <p
            v-for="f in cardDetailFields"
            :key="f.key"
            class="detail-line muted"
          >{{ f.label }}：{{ formatFieldValue(row, f) }}</p>
          <p v-if="row.tagNames?.length" class="sched muted">{{ row.tagNames.join(' · ') }}</p>
          <p v-if="row.mutexCode" class="sched muted">互斥组 {{ row.mutexCode }}</p>
          <p v-if="scheduleText(row)" class="sched">{{ scheduleText(row) }}</p>
          <RichTextView v-if="bodyRich && row.isbn" class="excerpt" :html="row.isbn" compact />
          <div class="row">
            <el-tag
              v-if="stockDisplay !== 'hidden'"
              :type="stockOk(row) ? 'success' : 'info'"
              size="small"
              effect="plain"
            >
              {{ stockText(row) }}
            </el-tag>
            <el-button
              v-if="playUrlOf(row)"
              size="small"
              @click="play(row)"
            >播放</el-button>
            <el-button
              v-if="bodyRich"
              size="small"
              @click="openDetail(row)"
            >阅读</el-button>
            <el-button
              size="small"
              type="primary"
              :disabled="!isSlotMode && !stockOk(row)"
              @click="onPrimary(row)"
            >{{ primaryActionLabel }}</el-button>
          </div>
        </div>
      </article>
    </div>

    <div v-if="!list.length" class="empty">暂无记录，换个关键词试试。</div>
    <div v-if="!isGuest" class="pager">
      <el-pagination
        v-model:current-page="page"
        v-model:page-size="size"
        background
        layout="total, prev, pager, next"
        :total="total"
        @current-change="load"
      />
    </div>
    <GuestLoginHint />

    <el-drawer v-model="detailVisible" :title="detail?.title || '详情'" size="520px" destroy-on-close>
      <template v-if="detail">
        <img v-if="detail.coverUrl" :src="detail.coverUrl" class="detail-cover" alt="" />
        <p class="sub">{{ formatAuthor(detail.author) }} · {{ detail.categoryName || '未分类' }}</p>
        <p
          v-for="f in cardDetailFields"
          :key="f.key"
          class="detail-line"
        >{{ f.label }}：{{ formatFieldValue(detail, f) }}</p>
        <p v-if="scheduleText(detail)" class="sched">{{ scheduleText(detail) }}</p>
        <p v-if="detail.applyDeadlineAt" class="sched muted">截止 {{ detail.applyDeadlineAt }}</p>
        <RichTextView v-if="bodyRich" :html="detail.isbn || ''" />
        <div class="drawer-acts">
          <el-button
            type="primary"
            :disabled="!isSlotMode && !stockOk(detail)"
            @click="onPrimary(detail)"
          >{{ primaryActionLabel }}</el-button>
        </div>
      </template>
    </el-drawer>

    <el-dialog
      v-model="applyVisible"
      :title="verbs.apply || '申请'"
      :width="richRemark ? '640px' : '440px'"
      destroy-on-close
    >
      <p class="apply-tip">对「{{ applyRow?.title }}」{{ verbs.apply || '提交申请' }}</p>
      <p v-if="scheduleText(applyRow)" class="apply-tip muted">{{ scheduleText(applyRow) }}</p>
      <el-form label-position="top">
        <el-form-item v-if="allowQty" label="数量" required>
          <el-input-number
            v-model="applyQty"
            :min="1"
            :max="qtyMax"
            controls-position="right"
          />
          <span v-if="stockDisplay === 'count'" class="apply-tip muted" style="margin-left:8px">
            {{ stockCountLabel }} {{ applyRow?.stock ?? 0 }}
          </span>
        </el-form-item>
        <el-form-item v-if="pickLoanPeriod" :label="dueLabel" required>
          <el-date-picker
            v-model="applyDueAt"
            type="date"
            value-format="YYYY-MM-DD"
            :placeholder="`选择${dueLabel}`"
            :disabled-date="dueDisabledDate"
            style="width:100%"
          />
        </el-form-item>
        <el-form-item v-if="pickDateRange" label="起止日期" required>
          <el-date-picker
            v-model="applyPeriod"
            type="daterange"
            value-format="YYYY-MM-DD"
            start-placeholder="开始"
            end-placeholder="结束"
            :disabled-date="dueDisabledDate"
            style="width:100%"
          />
        </el-form-item>
        <el-form-item v-if="isCrm" label="联系渠道">
          <el-select v-model="applyChannel" style="width:100%" clearable placeholder="电话/微信/到访等">
            <el-option label="电话" value="电话" />
            <el-option label="微信" value="微信" />
            <el-option label="邮件" value="邮件" />
            <el-option label="到访" value="到访" />
            <el-option label="其他" value="其他" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="isCrm" label="下次跟进">
          <el-date-picker
            v-model="applyNextFollow"
            type="datetime"
            value-format="YYYY-MM-DD HH:mm:ss"
            style="width:100%"
            placeholder="选填"
          />
        </el-form-item>
        <el-form-item v-if="requireRemark && !richRemark" :label="remarkLabel" required>
          <el-input
            v-model="applyRemark"
            type="textarea"
            :rows="3"
            maxlength="255"
            :placeholder="`请填写${remarkLabel}`"
          />
        </el-form-item>
        <el-form-item v-if="richRemark" :label="ticket.label || '内容'" required>
          <RichTextEditor v-model="applyRemark" placeholder="请输入回复内容，可用工具栏排版；可 @昵称 引用" />
        </el-form-item>
        <el-form-item v-if="requireAttach" label="证明附件" required>
          <div class="attach-row">
            <el-upload
              :show-file-list="false"
              accept="image/*,.pdf,.doc,.docx"
              :http-request="onAttach"
            >
              <el-button size="small">{{ applyAttachUrl ? '重新上传' : '上传附件' }}</el-button>
            </el-upload>
            <a v-if="applyAttachUrl" :href="applyAttachUrl" target="_blank" rel="noopener noreferrer">已上传</a>
          </div>
        </el-form-item>
      </el-form>
      <p v-if="!needApplyDialog" class="apply-tip muted">确认后提交，等待审核。</p>
      <template #footer>
        <el-button @click="applyVisible = false">取消</el-button>
        <el-button type="primary" :loading="applyLoading" @click="submitApply">提交</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import http from '../../api/http'
import GuestLoginHint from '../../components/GuestLoginHint.vue'
import RecommendStrip from '../../components/RecommendStrip.vue'
import RichTextEditor from '../../components/RichTextEditor.vue'
import RichTextView from '../../components/RichTextView.vue'
import { archiveCopy, formatArchiveScalar, hasTrait, getSchema, menuLabel, ticketCopy, ticketDueLabel } from '../../utils/domainSchema.js'
import { plainFromHtml, sanitizeHtml } from '../../utils/richHtml.js'
import {
  guestTeaserLimit,
  isGuestBrowseEnabled,
  isLoggedIn,
  requireLogin,
} from '../../utils/session.js'

const router = useRouter()
const isGuest = computed(() => isGuestBrowseEnabled() && !isLoggedIn())
const archive = archiveCopy()
const ticket = ticketCopy()
const isCrm = computed(() => hasTrait('crm'))
const caps = computed(() => getSchema().capabilities || [])
const verbs = computed(() => ticket.verbs || {})
const plural = computed(() => archive.labelPlural || archive.label || '业务对象')
const fields = computed(() => archive.fields || [])
const stockDisplay = computed(() => archive.stockDisplay || 'count')
const playUrlField = computed(() => archive.playUrlField || '')
const bodyRich = computed(() => {
  const f = fields.value.find((x) => x.key === 'isbn')
  return f?.type === 'richtext' || archive.bodyField === 'isbn'
})
const richRemark = computed(() => !!ticket.richRemark)
const requireAttach = computed(() => !!ticket.requireAttach)
const requireRemark = computed(() => !!ticket.requireRemark)
const remarkLabel = computed(() => ticket.remarkLabel || '说明')
const dueLabel = computed(() => ticketDueLabel('到期日'))
const pickLoanPeriod = computed(() => !!ticket.pickLoanPeriod)
const pickDateRange = computed(() => !!ticket.pickDateRange)
const allowQty = computed(() => !!ticket.allowQty)
const needApplyDialog = computed(
  () =>
    richRemark.value
    || requireAttach.value
    || requireRemark.value
    || pickLoanPeriod.value
    || pickDateRange.value
    || allowQty.value
    || isCrm.value,
)
const checkMutex = computed(() => !!ticket.checkMutex)
const categoryLimit = computed(() => Number(ticket.categoryLimit) || 0)
const tagFilter = computed(() => !!archive.tagFilter)
const stockCountLabel = computed(() => {
  if (archive.stockCountLabel) return archive.stockCountLabel
  const stockField = fields.value.find((x) => x.key === 'stock')
  if (stockField?.label) return stockField.label
  return '余量'
})

/** 卡片/详情副文案：schema 里除标题作者分类外的短字段（地点、类型、编号等） */
const cardDetailFields = computed(() => {
  const skip = new Set([
    'title', 'author', 'category', 'stock', 'coverUrl',
    'mutexCode', 'checkinCode', 'startAt', 'endAt', 'applyDeadlineAt',
  ])
  return fields.value.filter((f) => {
    if (!f?.key || skip.has(f.key)) return false
    if (f.type === 'hidden' || f.type === 'richtext' || f.type === 'select') return false
    // 正文/播放链路由摘要或播放按钮承担，避免卡片再堆一长串 URL
    if (f.key === 'isbn' && (bodyRich.value || playUrlField.value === 'isbn')) return false
    const t = f.type || 'string'
    return ['string', 'number', 'datetime', 'date', 'url', 'textarea'].includes(t)
  })
})

const searchPlaceholder = computed(() => {
  const parts = [fieldLabel('title', '名称'), fieldLabel('author', '型号')]
  const isbnF = fields.value.find((x) => x.key === 'isbn')
  if (isbnF && isbnF.type !== 'richtext' && isbnF.type !== 'hidden' && playUrlField.value !== 'isbn') {
    parts.push(isbnF.label || '编号')
  }
  return `搜索${parts.join(' / ')}`
})

const ruleHint = computed(() => {
  const parts = []
  const catLab = fieldLabel('category', '分类')
  const unit = archive.label || '项'
  if (checkMutex.value) parts.push('同互斥码不可同选')
  if (categoryLimit.value > 0) parts.push(`每${catLab}最多 ${categoryLimit.value} ${unit}`)
  if (tagFilter.value) parts.push('可多标签组合筛选')
  if (pickLoanPeriod.value) parts.push(`须选择${dueLabel.value}`)
  if (pickDateRange.value) parts.push('须选择起止日期')
  if (allowQty.value) parts.push('可填申请数量')
  if (requireRemark.value) parts.push(`须填写${remarkLabel.value}`)
  return parts.length ? parts.join('；') + '。' : ''
})
const qtyMax = computed(() => {
  const stock = Number(applyRow.value?.stock)
  if (Number.isFinite(stock) && stock > 0) return Math.min(99, stock)
  return 99
})
const hasSchedule = computed(() => fields.value.some((x) => x.key === 'startAt'))
const hasRecommend = computed(() => caps.value.includes('recommend'))
const isOrderMode = computed(() => caps.value.includes('order_lines') && !caps.value.includes('ticket_flow') && !caps.value.includes('slot_reserve'))
const isSlotMode = computed(() => caps.value.includes('slot_reserve') && !caps.value.includes('ticket_flow'))
const cartLabel = computed(() => menuLabel('user', 'cart', '购物车'))
const resvVerb = computed(() => getSchema()?.entities?.reservation?.verbs?.apply || '预约')
const primaryActionLabel = computed(() => {
  if (isOrderMode.value) return `加入${cartLabel.value}`
  if (isSlotMode.value) return '选时段'
  return verbs.value.apply || '申请'
})
const actionHint = computed(() => {
  if (isOrderMode.value) return `加入${cartLabel.value}并下单`
  if (isSlotMode.value) return `选择时段${resvVerb.value}`
  return `提交${verbs.value.apply || '申请'}`
})

function fieldLabel(key, fallback) {
  const f = fields.value.find((x) => x.key === key)
  return (f && f.label) || fallback
}

function formatAuthor(v) {
  const f = fields.value.find((x) => x.key === 'author') || { key: 'author', type: 'string' }
  return formatArchiveScalar(f, v)
}

function formatFieldValue(row, field) {
  if (!row || !field) return '—'
  return formatArchiveScalar(field, row[field.key], '—')
}

function scheduleText(row) {
  if (!row || !hasSchedule.value) return ''
  if (!row.startAt && !row.endAt) return ''
  if (row.startAt && row.endAt) return `${row.startAt} ~ ${row.endAt}`
  return row.startAt || row.endAt || ''
}

function stockOk(row) {
  return Number(row.stock) > 0
}

function stockText(row) {
  if (stockDisplay.value === 'available') {
    const ok = fieldLabel('stock', stockCountLabel.value)
    if (!stockOk(row)) {
      return archive.stockUnavailableLabel || stockUnavailableFrom(ok)
    }
    const n = Number(row.stock)
    // 同款多件登记在一条时展示余量，便于区分「仅一件」与「可多认领」
    if (Number.isFinite(n) && n > 1) return `${ok} · 余 ${n}`
    return ok
  }
  return stockOk(row) ? `${stockCountLabel.value} ${row.stock}` : `暂无${stockCountLabel.value}`
}

/** 与 bake ticket_copy_text.stock_unavailable_label 同规则，无 schema 字段时兜底 */
function stockUnavailableFrom(stockLabel) {
  const s = String(stockLabel || '可用').trim() || '可用'
  if (s.startsWith('可')) return `已${s.slice(1)}`
  return `暂无${s}`
}

function playUrlOf(row) {
  const key = playUrlField.value
  if (!key || !row) return ''
  const raw = key === 'isbn' ? row.isbn : row[key]
  const s = raw == null ? '' : String(raw).trim()
  if (!s) return ''
  if (/^https?:\/\//i.test(s) || s.startsWith('/') || s.startsWith('blob:')) return s
  return ''
}

function play(row) {
  const url = playUrlOf(row)
  if (!url) {
    ElMessage.warning('暂无播放链接')
    return
  }
  window.open(url, '_blank', 'noopener,noreferrer')
}

const list = ref([])
const total = ref(0)
const page = ref(1)
const size = ref(9)
const keyword = ref('')
const categoryId = ref(null)
const categories = ref([])
const tagIds = ref([])
const tags = ref([])
const recRef = ref(null)
const detailVisible = ref(false)
const detail = ref(null)
const applyVisible = ref(false)
const applyRow = ref(null)
const applyRemark = ref('')
const applyAttachUrl = ref('')
const applyQty = ref(1)
const applyDueAt = ref('')
const applyPeriod = ref(null)
const applyChannel = ref('')
const applyNextFollow = ref('')
const applyLoading = ref(false)

function openDetail(row) {
  detail.value = row
  detailVisible.value = true
}

async function onAttach(opt) {
  const fd = new FormData()
  fd.append('file', opt.file)
  const res = await http.post('/api/upload', fd)
  applyAttachUrl.value = res.data.url
  ElMessage.success('附件已上传')
}

async function loadCats() {
  const res = await http.get('/api/categories')
  categories.value = res.data || res || []
}

async function loadTags() {
  if (!tagFilter.value) return
  try {
    const res = await http.get('/api/tags')
    tags.value = res.data || res || []
  } catch {
    tags.value = []
  }
}

async function load() {
  const pageSize = isGuest.value ? guestTeaserLimit() : size.value
  const res = await http.get('/api/archive', {
    params: {
      page: isGuest.value ? 1 : page.value,
      size: pageSize,
      keyword: keyword.value || undefined,
      categoryId: categoryId.value || undefined,
      tagIds: tagIds.value?.length ? tagIds.value.join(',') : undefined,
    },
  })
  list.value = res.data.list
  total.value = res.data.total
}

async function onPrimary(row) {
  if (!requireLogin(router)) return
  if (isOrderMode.value) {
    await http.post('/api/cart', { itemId: row.id, qty: 1 })
    ElMessage.success(`已加入${cartLabel.value}`)
    return
  }
  if (isSlotMode.value) {
    router.push({ path: '/slots', query: { itemId: row.id, title: row.title || '' } })
    return
  }
  await apply(row)
}

async function apply(row) {
  applyRow.value = row
  applyRemark.value = ''
  applyAttachUrl.value = ''
  applyQty.value = 1
  applyDueAt.value = ''
  applyPeriod.value = null
  applyChannel.value = ''
  applyNextFollow.value = ''
  if (needApplyDialog.value) {
    applyVisible.value = true
    return
  }
  await ElMessageBox.confirm(
    `确认${verbs.value.apply || '申请'}「${row.title}」？`,
    verbs.value.apply || '申请',
  )
  await submitApply()
}

function dueDisabledDate(date) {
  const start = new Date()
  start.setHours(0, 0, 0, 0)
  const max = new Date(start)
  max.setDate(max.getDate() + 90)
  return date.getTime() < start.getTime() || date.getTime() > max.getTime()
}

async function submitApply() {
  if (!applyRow.value) return
  let remark = ''
  if (richRemark.value) {
    remark = sanitizeHtml(applyRemark.value || '')
    if (!plainFromHtml(remark)) {
      ElMessage.warning('请填写内容')
      return
    }
  } else if (requireRemark.value) {
    remark = (applyRemark.value || '').trim()
    if (!remark) {
      ElMessage.warning(`请填写${remarkLabel.value}`)
      return
    }
  }
  if (requireAttach.value && !applyAttachUrl.value) {
    ElMessage.warning('请上传证明附件')
    return
  }
  if (pickLoanPeriod.value && !applyDueAt.value) {
    ElMessage.warning(`请选择${dueLabel.value}`)
    return
  }
  if (pickDateRange.value) {
    const range = applyPeriod.value
    if (!Array.isArray(range) || range.length < 2 || !range[0] || !range[1]) {
      ElMessage.warning('请选择起止日期')
      return
    }
  }
  if (allowQty.value) {
    const n = Number(applyQty.value) || 0
    if (n < 1) {
      ElMessage.warning('数量至少为 1')
      return
    }
    if (n > qtyMax.value) {
      ElMessage.warning(`数量不能超过 ${qtyMax.value}`)
      return
    }
  }
  applyLoading.value = true
  try {
    const body = {
      itemId: applyRow.value.id,
      remark,
      attachUrl: applyAttachUrl.value || undefined,
    }
    if (allowQty.value) body.qty = Number(applyQty.value) || 1
    if (pickLoanPeriod.value) body.dueAt = applyDueAt.value
    if (pickDateRange.value && Array.isArray(applyPeriod.value)) {
      body.periodStart = applyPeriod.value[0]
      body.periodEnd = applyPeriod.value[1]
    }
    if (isCrm.value) {
      if (applyChannel.value) body.contactChannel = applyChannel.value
      if (applyNextFollow.value) body.nextFollowAt = applyNextFollow.value
    }
    await http.post('/api/tickets/apply', body)
    ElMessage.success('已提交，等待审核')
    applyVisible.value = false
    detailVisible.value = false
    recRef.value?.reload?.()
  } finally {
    applyLoading.value = false
  }
}

onMounted(async () => {
  await loadCats()
  await loadTags()
  await load()
})
</script>

<style scoped>
.hero { margin-bottom: 18px; }
.hero h1 { margin: 0 0 6px; font-size: 22px; }
.hero p { margin: 0 0 14px; color: #64748b; font-size: 13px; }
.search { display: flex; gap: 10px; flex-wrap: wrap; }
.grid {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 14px;
}
.card {
  display: flex; gap: 14px; padding: 16px; background: #fff;
  border: 1px solid #e2e8f0; border-radius: 12px;
}
.cover {
  width: 48px; height: 48px; border-radius: 10px; flex-shrink: 0;
  display: grid; place-items: center; font-weight: 700; color: #0369a1;
  background: #e0f2fe; overflow: hidden;
}
.cover img {
  width: 100%; height: 100%; object-fit: cover; display: block;
}
.meta { flex: 1; min-width: 0; }
.meta h3 { margin: 0 0 4px; font-size: 16px; }
.meta p { margin: 0; color: #64748b; font-size: 12px; }
.detail-line { margin-top: 4px !important; line-height: 1.4; }
.detail-line.muted { color: #64748b !important; }
.sched { margin-top: 4px !important; color: #0f766e !important; }
.sched.muted { color: #94a3b8 !important; }
.excerpt { margin-top: 8px; color: #64748b; }
.row { margin-top: 10px; display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }
.empty { text-align: center; color: #94a3b8; padding: 40px 0; }
.pager { margin-top: 16px; display: flex; justify-content: flex-end; }
.sub { margin: 0 0 16px; color: #64748b; font-size: 13px; }
.detail-cover {
  width: 100%; max-height: 220px; object-fit: cover; border-radius: 10px;
  margin-bottom: 12px; background: #e0f2fe;
}
.drawer-acts { margin-top: 24px; }
.apply-tip { margin: 0 0 12px; color: #334155; font-size: 14px; }
.apply-tip.muted { color: #64748b; }
.attach-row { display: flex; gap: 12px; align-items: center; }
.attach-row a { font-size: 13px; color: #0369a1; }
</style>
