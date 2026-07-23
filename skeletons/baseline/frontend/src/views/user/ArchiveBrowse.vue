<template>
  <div>
    <section class="hero">
      <h1>{{ plural }}检索</h1>
      <p>
        按名称检索{{ playUrlField ? '、在线播放' : '' }}{{ bodyRich ? '、阅读正文' : '' }}，{{ actionHint }}。
        <template v-if="ruleHint"> {{ ruleHint }}</template>
      </p>
      <div class="search">
        <el-autocomplete
          v-if="searchAssist"
          v-model="keyword"
          size="large"
          clearable
          :fetch-suggestions="fetchSuggest"
          :placeholder="searchPlaceholder"
          style="flex:1; min-width:180px"
          @keyup.enter="load"
          @select="onSuggestSelect"
        />
        <el-input
          v-else
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
        <el-button
          v-if="userPublish && !isGuest"
          size="large"
          @click="openPublish"
        >发帖</el-button>
      </div>
      <div v-if="searchAssist && hotKeywords.length" class="hot">
        <span class="hot-lab">热搜</span>
        <button
          v-for="(w, i) in hotKeywords"
          :key="i"
          type="button"
          class="hot-chip"
          @click="applyHot(w)"
        >{{ w }}</button>
      </div>
    </section>

    <RecommendStrip
      v-if="hasRecommend && !isGuest"
      ref="recRef"
      :apply-label="favOn && !showPrimaryApply ? '收藏' : primaryActionLabel"
      @apply="onRecommendApply"
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
              v-if="bodyRich || galleryOn || browseOn"
              size="small"
              @click="openDetail(row)"
            >{{ bodyRich ? '阅读' : '详情' }}</el-button>
            <el-button
              v-if="showPrimaryApply"
              size="small"
              type="primary"
              :disabled="!isSlotMode && !stockOk(row)"
              @click="onPrimary(row)"
            >{{ primaryActionLabel }}</el-button>
            <el-button
              v-if="favOn && !isGuest"
              size="small"
              :type="favIds.includes(row.id) ? 'warning' : 'default'"
              @click="toggleFav(row)"
            >{{ favIds.includes(row.id) ? '已收藏' : '收藏' }}</el-button>
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
        <div v-if="galleryUrls.length" class="gallery">
          <el-carousel height="220px" indicator-position="outside">
            <el-carousel-item v-for="(u, i) in galleryUrls" :key="i">
              <img :src="u" class="detail-cover" alt="" />
            </el-carousel-item>
          </el-carousel>
        </div>
        <img v-else-if="detail.coverUrl" :src="detail.coverUrl" class="detail-cover" alt="" />
        <p class="sub">{{ formatAuthor(detail.author) }} · {{ detail.categoryName || '未分类' }}</p>
        <p
          v-for="f in cardDetailFields"
          :key="f.key"
          class="detail-line"
        >{{ f.label }}：{{ formatFieldValue(detail, f) }}</p>
        <p v-if="scheduleText(detail)" class="sched">{{ scheduleText(detail) }}</p>
        <p v-if="detail.applyDeadlineAt" class="sched muted">截止 {{ detail.applyDeadlineAt }}</p>
        <RichTextView v-if="bodyRich" :html="detail.isbn || ''" />
        <div v-if="showThread" class="thread">
          <h4 class="thread-title">{{ threadTitle }}</h4>
          <div v-if="threadLoading" class="thread-empty muted">加载中…</div>
          <div v-else-if="!threadList.length" class="thread-empty muted">暂无回复</div>
          <article v-for="r in threadList" :key="r.id" class="thread-item">
            <p class="thread-meta">
              <span>{{ r.username || '用户' }}</span>
              <span class="muted">{{ r.approveAt || r.applyAt || '' }}</span>
            </p>
            <RichTextView v-if="r.remark" :html="r.remark" />
            <p v-else class="muted">（无内容）</p>
          </article>
        </div>
        <div class="drawer-acts">
          <el-button
            v-if="showPrimaryApply"
            type="primary"
            :disabled="!isSlotMode && !stockOk(detail)"
            @click="onPrimary(detail)"
          >{{ primaryActionLabel }}</el-button>
          <el-button
            v-if="favOn && !isGuest"
            :type="favIds.includes(detail.id) ? 'warning' : 'default'"
            @click="toggleFav(detail)"
          >{{ favIds.includes(detail.id) ? '已收藏' : '收藏' }}</el-button>
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
        <el-form-item v-if="isCrm" :label="channelLabel">
          <el-select v-model="applyChannel" style="width:100%" clearable :placeholder="channelPlaceholder">
            <el-option v-for="opt in channelOptions" :key="opt" :label="opt" :value="opt" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="isCrm" :label="nextAtLabel">
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
      <p v-if="!needApplyDialog" class="apply-tip muted">
        {{ autoApprove ? '确认后立即生效。' : '确认后提交，等待审核。' }}
      </p>
      <template #footer>
        <el-button @click="applyVisible = false">取消</el-button>
        <el-button type="primary" :loading="applyLoading" @click="submitApply">提交</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="publishVisible" title="发帖" width="640px" destroy-on-close>
      <el-form label-position="top">
        <el-form-item :label="fieldLabel('title', '标题')" required>
          <el-input v-model="publishTitle" maxlength="80" show-word-limit placeholder="请输入标题" />
        </el-form-item>
        <el-form-item :label="fieldLabel('category', '板块')" required>
          <el-select v-model="publishCategoryId" style="width:100%" placeholder="选择板块">
            <el-option v-for="c in categories" :key="c.id" :label="c.name" :value="c.id" />
          </el-select>
        </el-form-item>
        <el-form-item :label="fieldLabel('isbn', '正文')" required>
          <RichTextEditor v-model="publishBody" placeholder="请输入正文，可用工具栏排版" />
        </el-form-item>
      </el-form>
      <p class="apply-tip muted">发布后即时可见，无需审核；违规由站长下架。</p>
      <template #footer>
        <el-button @click="publishVisible = false">取消</el-button>
        <el-button type="primary" :loading="publishLoading" @click="submitPublish">发布</el-button>
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
import { toggleFavorite, touchBrowseHistory, upsertCart } from '../../utils/apiCalls.js'
import {
  archiveCopy,
  formatArchiveScalar,
  followChannelLabel,
  followChannelOptions,
  followChannelPlaceholder,
  hasTrait,
  getSchema,
  isBrowseHistoryEnabled,
  isGalleryEnabled,
  isSearchAssistEnabled,
  menuLabel,
  nextFollowLabel,
  searchHotKeywords,
  ticketCopy,
  ticketDueLabel,
} from '../../utils/domainSchema.js'
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
const channelLabel = computed(() => followChannelLabel())
const nextAtLabel = computed(() => nextFollowLabel())
const channelPlaceholder = computed(() => followChannelPlaceholder())
const channelOptions = computed(() => followChannelOptions())
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
const autoApprove = computed(() => !!ticket.autoApprove)
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
const userPublish = computed(() => !!archive.userPublish)
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
/** 即时收藏：交易域或内容流（无单据审核） */
const favOn = computed(() => {
  if (!caps.value.includes('favorites')) return false
  if (isOrderMode.value) return true
  return !caps.value.includes('ticket_flow') && !caps.value.includes('slot_reserve')
})
/** 有单据/下单/预约时才显示主操作；内容流只保留播放/阅读 + 收藏 */
const showPrimaryApply = computed(
  () => isOrderMode.value || isSlotMode.value || caps.value.includes('ticket_flow'),
)
const favIds = ref([])
const searchAssist = computed(() => isSearchAssistEnabled())
const hotKeywords = computed(() => searchHotKeywords())
const galleryOn = computed(() => isGalleryEnabled())
const browseOn = computed(() => isBrowseHistoryEnabled())
const cartLabel = computed(() => menuLabel('user', 'cart', '购物车'))
const galleryUrls = computed(() => {
  if (!detail.value) return []
  const g = detail.value.galleryImages
  if (galleryOn.value && Array.isArray(g) && g.length) return g
  if (detail.value.coverUrl) return [detail.value.coverUrl]
  return []
})
const resvVerb = computed(() => getSchema()?.entities?.reservation?.verbs?.apply || '预约')
const primaryActionLabel = computed(() => {
  if (isOrderMode.value) return `加入${cartLabel.value}`
  if (isSlotMode.value) return '选时段'
  if (!showPrimaryApply.value) return '收藏'
  return verbs.value.apply || '申请'
})
const actionHint = computed(() => {
  if (isOrderMode.value) return `加入${cartLabel.value}并下单`
  if (isSlotMode.value) return `选择时段${resvVerb.value}`
  if (favOn.value && !showPrimaryApply.value) return '一键收藏感兴趣的内容'
  if (userPublish.value) return `发帖后可${verbs.value.apply || '回复'}`
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
  if (stockDisplay.value === 'toggle' || stockDisplay.value === 'available') {
    const ok = fieldLabel('stock', stockCountLabel.value)
    if (!stockOk(row)) {
      return archive.stockUnavailableLabel || stockUnavailableFrom(ok)
    }
    if (stockDisplay.value === 'toggle') return ok
    const n = Number(row.stock)
    // available：同款多件登记在一条时展示余量
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
const publishVisible = ref(false)
const publishTitle = ref('')
const publishBody = ref('')
const publishCategoryId = ref(null)
const publishLoading = ref(false)
const threadList = ref([])
const threadLoading = ref(false)
const showThread = computed(() => richRemark.value && !!detail.value?.id)
const threadTitle = computed(() => {
  const plural = ticket.labelPlural || ticket.label || '回复'
  return `${plural}（${threadList.value.length}）`
})

async function loadThread(itemId) {
  if (!richRemark.value || !itemId) {
    threadList.value = []
    return
  }
  threadLoading.value = true
  try {
    const res = await http.get(`/api/tickets/thread/${itemId}`, { params: { page: 1, size: 50 } })
    threadList.value = res.data?.list || []
  } catch {
    threadList.value = []
  } finally {
    threadLoading.value = false
  }
}

async function openDetail(row) {
  detail.value = row
  detailVisible.value = true
  threadList.value = []
  if (!row?.id) return
  try {
    const res = await http.get(`/api/archive/${row.id}`)
    if (res.data) detail.value = { ...row, ...res.data }
  } catch { /* keep list row */ }
  await loadThread(row.id)
  if (browseOn.value && isLoggedIn()) {
    try {
      await touchBrowseHistory(row.id)
    } catch { /* ignore */ }
  }
}

async function fetchSuggest(query, cb) {
  const q = String(query || '').trim()
  if (!q) {
    cb([])
    return
  }
  try {
    const res = await http.get('/api/archive/suggest', { params: { q, limit: 8 } })
    const list = Array.isArray(res.data) ? res.data : []
    cb(list.map((x) => ({ value: x.title || x.value, id: x.id })))
  } catch {
    cb([])
  }
}

function onSuggestSelect(item) {
  keyword.value = item?.value || ''
  load()
}

function applyHot(w) {
  keyword.value = String(w || '')
  load()
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

async function loadFavIds() {
  if (!favOn.value || isGuest.value) {
    favIds.value = []
    return
  }
  try {
    const res = await http.get('/api/favorites/ids')
    favIds.value = (res.data?.ids || []).map(Number)
  } catch {
    favIds.value = []
  }
}

async function toggleFav(row) {
  if (!requireLogin(router)) return
  const res = await toggleFavorite(row.id)
  const on = !!res.data?.favorited
  if (on) {
    if (!favIds.value.includes(row.id)) favIds.value = [...favIds.value, row.id]
    ElMessage.success('已收藏')
  } else {
    favIds.value = favIds.value.filter((x) => x !== row.id)
    ElMessage.success('已取消收藏')
  }
}

async function onPrimary(row) {
  if (!requireLogin(router)) return
  if (isOrderMode.value) {
    await upsertCart(row.id, 1)
    ElMessage.success(`已加入${cartLabel.value}`)
    return
  }
  if (isSlotMode.value) {
    router.push({ path: '/slots', query: { itemId: row.id, title: row.title || '' } })
    return
  }
  await apply(row)
}

async function onRecommendApply(row) {
  if (favOn.value && !showPrimaryApply.value) {
    if (!requireLogin(router)) return
    await toggleFav(row)
    return
  }
  await onPrimary(row)
}

function openPublish() {
  if (!requireLogin(router)) return
  publishTitle.value = ''
  publishBody.value = ''
  publishCategoryId.value = categories.value[0]?.id || null
  publishVisible.value = true
}

async function submitPublish() {
  const title = publishTitle.value.trim()
  if (!title) {
    ElMessage.warning('请填写标题')
    return
  }
  if (!publishCategoryId.value) {
    ElMessage.warning(`请选择${fieldLabel('category', '板块')}`)
    return
  }
  const plain = plainFromHtml(publishBody.value || '')
  if (!plain.trim()) {
    ElMessage.warning('请填写正文')
    return
  }
  publishLoading.value = true
  try {
    await http.post('/api/archive/publish', {
      title,
      categoryId: publishCategoryId.value,
      isbn: sanitizeHtml(publishBody.value || ''),
    })
    ElMessage.success('已发布')
    publishVisible.value = false
    await load()
    recRef.value?.reload?.()
  } finally {
    publishLoading.value = false
  }
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
    ElMessage.success(autoApprove.value ? `已${verbs.value.apply || '提交'}` : '已提交，等待审核')
    applyVisible.value = false
    if (autoApprove.value && detailVisible.value && applyRow.value?.id) {
      await loadThread(applyRow.value.id)
    }
    if (!richRemark.value) detailVisible.value = false
    recRef.value?.reload?.()
  } finally {
    applyLoading.value = false
  }
}

onMounted(async () => {
  await loadCats()
  await loadTags()
  await load()
  await loadFavIds()
})
</script>

<style scoped>
.hero { margin-bottom: 18px; }
.hero h1 { margin: 0 0 6px; font-size: 22px; }
.hero p { margin: 0 0 14px; color: var(--portal-muted, #64748b); font-size: 13px; }
.search { display: flex; gap: 10px; flex-wrap: wrap; }
.hot { margin-top: 10px; display: flex; flex-wrap: wrap; gap: 8px; align-items: center; }
.hot-lab { font-size: 12px; color: var(--portal-muted, #94a3b8); }
.hot-chip {
  border: 1px solid var(--portal-line, #e2e8f0);
  background: var(--portal-surface, #fff);
  border-radius: 999px;
  padding: 2px 10px;
  font-size: 12px;
  color: var(--portal-muted, #475569);
  cursor: pointer;
}
.hot-chip:hover { border-color: var(--el-color-primary); color: var(--el-color-primary); }
.gallery { margin-bottom: 12px; }
.gallery .detail-cover { width: 100%; height: 220px; object-fit: cover; border-radius: 8px; }
.grid {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 14px;
}
.card {
  display: flex; gap: 14px; padding: var(--portal-pad, 16px);
  background: var(--portal-surface, #fff);
  border: var(--portal-border-width, 1px) solid var(--portal-line, #e2e8f0);
  border-radius: var(--portal-radius, 12px);
  box-shadow: var(--portal-shadow, none);
}
.cover {
  width: 48px; height: 48px; border-radius: var(--portal-radius-sm, 10px); flex-shrink: 0;
  display: grid; place-items: center; font-weight: 700; color: #0369a1;
  background: #e0f2fe; overflow: hidden;
}
.cover img {
  width: 100%; height: 100%; object-fit: cover; display: block;
}
.meta { flex: 1; min-width: 0; }
.meta h3 { margin: 0 0 4px; font-size: 16px; }
.meta p { margin: 0; color: var(--portal-muted, #64748b); font-size: 12px; }
.detail-line { margin-top: 4px !important; line-height: 1.4; }
.detail-line.muted { color: var(--portal-muted, #64748b) !important; }
.sched { margin-top: 4px !important; color: #0f766e !important; }
.sched.muted { color: var(--portal-muted, #94a3b8) !important; }
.excerpt { margin-top: 8px; color: var(--portal-muted, #64748b); }
.row { margin-top: 10px; display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }
.empty { text-align: center; color: var(--portal-muted, #94a3b8); padding: 40px 0; }
.pager { margin-top: 16px; display: flex; justify-content: flex-end; }
.sub { margin: 0 0 16px; color: var(--portal-muted, #64748b); font-size: 13px; }
.detail-cover {
  width: 100%; max-height: 220px; object-fit: cover;
  border-radius: var(--portal-radius, 10px);
  margin-bottom: 12px; background: #e0f2fe;
}
.drawer-acts { margin-top: 24px; }
.thread { margin-top: 20px; padding-top: 16px; border-top: 1px solid var(--portal-line, #e2e8f0); }
.thread-title { margin: 0 0 12px; font-size: 15px; }
.thread-empty { font-size: 13px; }
.thread-item {
  padding: 10px 0;
  border-bottom: 1px solid var(--portal-line, #e2e8f0);
}
.thread-item:last-child { border-bottom: 0; }
.thread-meta {
  margin: 0 0 6px;
  display: flex; gap: 10px; justify-content: space-between;
  font-size: 12px; color: var(--portal-ink, #334155);
}
.apply-tip { margin: 0 0 12px; color: var(--portal-ink, #334155); font-size: 14px; }
.apply-tip.muted { color: var(--portal-muted, #64748b); }
.attach-row { display: flex; gap: 12px; align-items: center; }
.attach-row a { font-size: 13px; color: #0369a1; }
</style>
