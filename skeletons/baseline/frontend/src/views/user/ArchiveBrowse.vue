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
        >{{ publishCtaLabel }}</el-button>
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
      :exclude-ids="list.map((r) => r.id)"
      @apply="onRecommendApply"
    />

    <div class="list-hd">
      <h2>{{ plural }}列表</h2>
      <span class="list-hd-hint">检索与筛选结果</span>
    </div>
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
              v-if="bodyRich || galleryOn || browseOn || logOn"
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
        <div v-if="logOn && !isGuest" class="alog">
          <h4 class="thread-title">{{ logSectionTitle }}</h4>
          <el-form label-position="top" class="alog-form" @submit.prevent>
            <el-form-item
              v-for="f in logFields"
              :key="f.key"
              :label="f.label || f.key"
            >
              <el-input
                v-if="f.type === 'textarea'"
                v-model="logForm.payload[f.key]"
                type="textarea"
                :rows="2"
              />
              <el-input v-else v-model="logForm.payload[f.key]" />
            </el-form-item>
            <el-form-item label="异常">
              <el-switch v-model="logForm.abnormal" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :loading="logSubmitting" @click="submitLog">{{ logSubmitLabel }}</el-button>
            </el-form-item>
          </el-form>
          <div v-if="logLoading" class="thread-empty muted">加载中…</div>
          <div v-else-if="!logList.length" class="thread-empty muted">暂无记录</div>
          <article v-for="r in logList" :key="r.id" class="thread-item">
            <p class="thread-meta">
              <span>{{ r.logDate }} · {{ r.username || '—' }}</span>
              <el-tag v-if="r.abnormal" type="danger" size="small" effect="plain">异常</el-tag>
            </p>
            <p class="detail-line">{{ logPayloadText(r) }}</p>
            <p v-if="r.remark" class="muted">{{ r.remark }}</p>
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
        <el-form-item v-if="allowQty" :label="qtyLabel" required>
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
        <el-form-item v-if="rateOnApply" label="多维评分" required>
          <div class="rate-dims">
            <div v-for="d in ratingDims" :key="d.key" class="rate-dim-row">
              <span class="rate-dim-lab">{{ d.label }}</span>
              <el-rate v-model="applyDimScores[d.key]" :max="5" />
            </div>
          </div>
        </el-form-item>
        <el-form-item v-if="rateOnApply && allowAnonymousRating" label="匿名">
          <el-checkbox v-model="applyAnonymous">匿名提交</el-checkbox>
        </el-form-item>
        <el-form-item v-if="checkinOnApply" :label="checkinLabel" required>
          <el-input
            v-model="applyCheckinCode"
            maxlength="16"
            placeholder="向宿管/值班员索取签到码"
            @keyup.enter="submitApply"
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

    <el-dialog v-model="publishVisible" :title="publishDialogTitle" width="520px" destroy-on-close>
      <el-form label-position="top">
        <el-form-item :label="fieldLabel('title', '名称')" required>
          <el-input
            v-model="publishTitle"
            maxlength="80"
            show-word-limit
            :placeholder="publishTitlePlaceholder"
          />
        </el-form-item>
        <el-form-item v-if="publishShowAuthor" :label="fieldLabel('author', '联系人')" required>
          <el-input
            v-model="publishAuthor"
            maxlength="64"
            :placeholder="`请填写${fieldLabel('author', '联系人')}`"
          />
        </el-form-item>
        <el-form-item :label="fieldLabel('category', '分类')" required>
          <el-select v-model="publishCategoryId" style="width:100%" :placeholder="`选择${fieldLabel('category', '分类')}`">
            <el-option v-for="c in categories" :key="c.id" :label="c.name" :value="c.id" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="publishShowStock" :label="fieldLabel('stock', '余座')" required>
          <el-input-number v-model="publishStock" :min="1" :max="99" controls-position="right" />
        </el-form-item>
        <el-form-item :label="fieldLabel('isbn', publishUsesRichBody ? '正文' : '备注')" required>
          <RichTextEditor
            v-if="publishUsesRichBody"
            v-model="publishBody"
            placeholder="请输入正文，可用工具栏排版"
          />
          <el-input
            v-else
            v-model="publishBody"
            type="textarea"
            :rows="3"
            maxlength="255"
            show-word-limit
            :placeholder="publishIsbnPlaceholder"
          />
        </el-form-item>
      </el-form>
      <p class="apply-tip muted">{{ publishTip }}</p>
      <template #footer>
        <el-button @click="publishVisible = false">取消</el-button>
        <el-button type="primary" :loading="publishLoading" @click="submitPublish">{{ publishSubmitLabel }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
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
  archiveLogCopy,
  formatArchiveScalar,
  followChannelLabel,
  followChannelOptions,
  followChannelPlaceholder,
  hasTrait,
  getSchema,
  isArchiveLogEnabled,
  isBrowseHistoryEnabled,
  isGalleryEnabled,
  isSearchAssistEnabled,
  menuLabel,
  nextFollowLabel,
  searchHotKeywords,
  ticketCopy,
  ticketCheckinLabel,
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
const isCrm = computed(() => hasTrait('followUp') || hasTrait('crm'))
const channelLabel = computed(() => followChannelLabel())
const nextAtLabel = computed(() => nextFollowLabel())
const channelPlaceholder = computed(() => followChannelPlaceholder())
const channelOptions = computed(() => followChannelOptions())
const caps = computed(() => getSchema().capabilities || [])
const verbs = computed(() => ticket.verbs || {})
const plural = computed(() => archive.labelPlural || archive.label || '对象')
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
const qtyLabel = computed(() => ticket.qtyLabel || '数量')
const ratingDims = computed(() => {
  const list = ticket.ratingDims
  return Array.isArray(list) ? list.filter((d) => d && d.key && d.label) : []
})
const allowAnonymousRating = computed(() => !!ticket.allowAnonymousRating)
const rateOnApply = computed(
  () => !!autoApprove.value && !!ticket.allowRating && ratingDims.value.length > 0,
)
const checkinOnApply = computed(() => !!autoApprove.value && !!ticket.allowCheckin)
const checkinLabel = computed(() => ticketCheckinLabel('签到'))
const needApplyDialog = computed(
  () =>
    richRemark.value
    || requireAttach.value
    || requireRemark.value
    || pickLoanPeriod.value
    || pickDateRange.value
    || allowQty.value
    || isCrm.value
    || rateOnApply.value
    || checkinOnApply.value,
)
const checkMutex = computed(() => !!ticket.checkMutex)
const categoryLimit = computed(() => Number(ticket.categoryLimit) || 0)
const tagFilter = computed(() => !!archive.tagFilter)
const userPublish = computed(() => !!archive.userPublish)
/** 论坛类：isbn 富文本；CRM/拼车等：纯文本业务表单 */
const publishUsesRichBody = computed(() => bodyRich.value)
/** 联系人等可填；「发布人/作者」由登录账号自动写入 */
const publishShowAuthor = computed(() => {
  if (!userPublish.value || publishUsesRichBody.value) return false
  const lab = fieldLabel('author', '')
  if (/发布人|作者|发帖/.test(lab)) return false
  return true
})
const publishShowStock = computed(
  () => userPublish.value && !publishUsesRichBody.value && stockDisplay.value === 'number',
)
const publishDialogTitle = computed(() => {
  if (publishUsesRichBody.value) return '发帖'
  if (publishShowStock.value) return `发布${archive.label || '行程'}`
  return `登记${archive.label || '内容'}`
})
const publishCtaLabel = computed(() => {
  if (publishUsesRichBody.value) return '发帖'
  if (publishShowStock.value) return `发布${archive.label || '行程'}`
  return `登记${archive.label || '内容'}`
})
const publishSubmitLabel = computed(() => {
  if (publishUsesRichBody.value) return '发布'
  if (publishShowStock.value) return '发布'
  return '保存'
})
const publishTitlePlaceholder = computed(() => `请填写${fieldLabel('title', '名称')}`)
const publishIsbnPlaceholder = computed(() => {
  const lab = fieldLabel('isbn', '备注')
  if (lab.includes('时间') || lab.includes('地点')) return '例如：周五 18:30 学校东门出发，可带行李'
  if (lab.includes('电话') || lab.includes('备注')) return '电话、微信或跟进备注'
  return `请填写${lab}`
})
const publishTip = computed(() => {
  if (publishUsesRichBody.value) return '发布后即时可见，无需审核；违规可由管理员下架。'
  if (publishShowStock.value) return '行程发布后即时可见；他人提交意向后由你确认或婉拒。'
  return `登记后即时入档，可在「我的${archive.label || '内容'}」中查看；随后可提交跟进。`
})
const stockCountLabel = computed(() => {
  if (archive.stockCountLabel) return archive.stockCountLabel
  const stockField = fields.value.find((x) => x.key === 'stock')
  if (stockField?.label) return stockField.label
  return '余量'
})

/** 卡片/详情副文案：schema 里除标题作者分类外的短字段（地点、阶段、编号等） */
const cardDetailFields = computed(() => {
  const skip = new Set([
    'title', 'author', 'category', 'stock', 'coverUrl',
    'mutexCode', 'checkinCode', 'startAt', 'endAt', 'applyDeadlineAt',
  ])
  return fields.value.filter((f) => {
    if (!f?.key || skip.has(f.key)) return false
    if (f.type === 'hidden' || f.type === 'richtext') return false
    // 正文/播放链路由摘要或播放按钮承担，避免卡片再堆一长串 URL
    if (f.key === 'isbn' && (bodyRich.value || playUrlField.value === 'isbn')) return false
    const t = f.type || 'string'
    return ['string', 'number', 'datetime', 'date', 'url', 'textarea', 'select'].includes(t)
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
const isSlotMode = computed(() => {
  if (!caps.value.includes('slot_reserve')) return false
  // C-07 仪器机时等：借+约并存时主按钮走约时段（traits.slotPrimary）
  if (hasTrait('slotPrimary')) return true
  return !caps.value.includes('ticket_flow')
})
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
const logOn = computed(() => isArchiveLogEnabled())
const logEnt = computed(() => archiveLogCopy())
const logFields = computed(() => logEnt.value.fields || [])
const logSectionTitle = computed(
  () => getSchema()?.labels?.archiveLogSectionTitle || logEnt.value.labelPlural || '打卡与随访',
)
const logSubmitLabel = computed(
  () => getSchema()?.labels?.archiveLogSubmitLabel || '提交登记',
)
const logList = ref([])
const logLoading = ref(false)
const logSubmitting = ref(false)
const logForm = ref({ payload: {}, abnormal: false })

function resetLogForm() {
  const payload = {}
  for (const f of logFields.value) {
    if (f?.key) payload[f.key] = ''
  }
  logForm.value = { payload, abnormal: false }
}

function logPayloadText(row) {
  const p = row.payload || {}
  const parts = []
  for (const f of logFields.value) {
    const val = p[f.key]
    if (val != null && String(val).trim() !== '') parts.push(`${f.label || f.key}:${val}`)
  }
  return parts.join(' · ') || '—'
}

async function loadLogs(itemId) {
  if (!logOn.value || !itemId) return
  logLoading.value = true
  try {
    const res = await http.get('/api/archive-logs', { params: { itemId, page: 1, size: 20 } })
    logList.value = res.data?.list || []
  } finally {
    logLoading.value = false
  }
}

async function submitLog() {
  if (!detail.value?.id) return
  if (!requireLogin(router)) return
  logSubmitting.value = true
  try {
    await http.post('/api/archive-logs', {
      itemId: detail.value.id,
      logType: logEnt.value.defaultType || 'checkin',
      payload: { ...logForm.value.payload },
      abnormal: !!logForm.value.abnormal,
    })
    ElMessage.success('已提交')
    resetLogForm()
    await loadLogs(detail.value.id)
  } finally {
    logSubmitting.value = false
  }
}
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
  if (userPublish.value) {
    return publishUsesRichBody.value
      ? `发帖后可${verbs.value.apply || '回复'}`
      : `登记后可${verbs.value.apply || '提交'}`
  }
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
const applyCheckinCode = ref('')
const applyAnonymous = ref(false)
const applyDimScores = reactive({})
const applyLoading = ref(false)
const publishVisible = ref(false)
const publishTitle = ref('')
const publishAuthor = ref('')
const publishBody = ref('')
const publishStock = ref(2)
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
  logList.value = []
  resetLogForm()
  if (!row?.id) return
  try {
    const res = await http.get(`/api/archive/${row.id}`)
    if (res.data) detail.value = { ...row, ...res.data }
  } catch { /* keep list row */ }
  await loadThread(row.id)
  if (logOn.value && isLoggedIn()) await loadLogs(row.id)
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
    router.push({
      path: '/slots',
      query: {
        itemId: row.id,
        title: row.title || '',
        price: row.author != null && row.author !== '' ? String(row.author) : '',
      },
    })
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
  publishAuthor.value = ''
  publishBody.value = ''
  publishStock.value = publishShowStock.value ? 2 : 1
  publishCategoryId.value = categories.value[0]?.id || null
  publishVisible.value = true
}

async function submitPublish() {
  const title = publishTitle.value.trim()
  if (!title) {
    ElMessage.warning(`请填写${fieldLabel('title', '名称')}`)
    return
  }
  if (publishShowAuthor.value && !publishAuthor.value.trim()) {
    ElMessage.warning(`请填写${fieldLabel('author', '联系人')}`)
    return
  }
  if (!publishCategoryId.value) {
    ElMessage.warning(`请选择${fieldLabel('category', '分类')}`)
    return
  }
  if (publishShowStock.value) {
    const n = Number(publishStock.value) || 0
    if (n < 1) {
      ElMessage.warning(`${fieldLabel('stock', '余座')}至少为 1`)
      return
    }
  }
  let isbn = ''
  if (publishUsesRichBody.value) {
    isbn = sanitizeHtml(publishBody.value || '')
    if (!plainFromHtml(isbn).trim()) {
      ElMessage.warning(`请填写${fieldLabel('isbn', '正文')}`)
      return
    }
  } else {
    isbn = (publishBody.value || '').trim()
    if (!isbn) {
      ElMessage.warning(`请填写${fieldLabel('isbn', '备注')}`)
      return
    }
  }
  publishLoading.value = true
  try {
    const body = {
      title,
      categoryId: publishCategoryId.value,
      isbn,
    }
    if (publishShowAuthor.value) body.author = publishAuthor.value.trim()
    if (publishShowStock.value) body.stock = Number(publishStock.value) || 1
    await http.post('/api/archive/publish', body)
    ElMessage.success(publishUsesRichBody.value || publishShowStock.value ? '已发布' : '已登记')
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
  applyCheckinCode.value = ''
  applyAnonymous.value = false
  Object.keys(applyDimScores).forEach((k) => delete applyDimScores[k])
  for (const d of ratingDims.value) {
    applyDimScores[d.key] = 5
  }
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
  if (checkinOnApply.value) {
    if (!applyCheckinCode.value.trim()) {
      ElMessage.warning(`请输入${checkinLabel.value}码`)
      return
    }
  }
  let dimsPayload = null
  if (rateOnApply.value) {
    dimsPayload = {}
    for (const d of ratingDims.value) {
      const v = applyDimScores[d.key]
      if (!v || v < 1) {
        ElMessage.warning(`请完成「${d.label}」评分`)
        return
      }
      dimsPayload[d.key] = v
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
    if (checkinOnApply.value) body.checkinCode = applyCheckinCode.value.trim()
    if (dimsPayload) {
      body.dims = dimsPayload
      if (allowAnonymousRating.value) body.anonymous = !!applyAnonymous.value
    }
    await http.post('/api/tickets/apply', body)
    const okMsg = checkinOnApply.value
      ? '已签到'
      : (autoApprove.value ? `已${verbs.value.apply || '提交'}` : '已提交，等待审核')
    ElMessage.success(okMsg)
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
.list-hd {
  display: flex;
  align-items: baseline;
  gap: 10px;
  margin: 4px 0 12px;
}
.list-hd h2 {
  margin: 0;
  font-size: 16px;
  font-weight: 650;
  letter-spacing: -0.02em;
}
.list-hd-hint {
  font-size: 12px;
  color: var(--portal-muted, #94a3b8);
}
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
.alog { margin-top: 20px; padding-top: 16px; border-top: 1px solid var(--portal-line, #e2e8f0); }
.alog-form { margin-bottom: 12px; }
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
.rate-dims { display: flex; flex-direction: column; gap: 8px; width: 100%; }
.rate-dim-row { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
.rate-dim-lab { font-size: 13px; color: var(--portal-ink, #334155); min-width: 72px; }
</style>
