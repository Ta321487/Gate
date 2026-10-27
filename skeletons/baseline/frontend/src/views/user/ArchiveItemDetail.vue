<template>
  <div class="aid" :class="{ 'aid-content': contentOn }" v-loading="loading">
    <p v-if="!loading && !row" class="aid-empty">
      <EmptyHint title="暂无详情" desc="这条记录不存在或已下架。" mark="详" cta-label="返回目录" @cta="goList" />
    </p>
    <template v-else-if="row">
      <section class="aid-hero">
        <div class="aid-cover" :style="coverStyle">
          <span v-if="!coverUrl" class="aid-cover-letter">{{ letter }}</span>
        </div>
        <div class="aid-info">
          <p v-if="entityLabel" class="aid-kicker">{{ entityLabel }}</p>
          <h1>{{ row.title || '未命名' }}</h1>
          <p v-if="lead" class="aid-lead">{{ lead }}</p>
          <p v-if="priceOn" class="aid-price">
            <span v-if="showPriceLabel" class="aid-price-label">{{ priceLabel }}</span>
            <strong>{{ priceText }}</strong>
          </p>
          <p v-if="metaLine" class="aid-meta">{{ metaLine }}</p>
          <ul v-if="detailAttrLines.length" class="aid-attrs">
            <li v-for="line in detailAttrLines" :key="line.key">
              <span class="aid-attr-k">{{ line.label }}</span>
              <span class="aid-attr-v">{{ line.text }}</span>
            </li>
          </ul>
          <!-- 数量+主操作钉右栏底：与左图齐高时禁顶对齐留下半截空 -->
          <div class="aid-buybox">
            <div v-if="orderOn" class="aid-qty">
              <button type="button" aria-label="减少" @click="qty = Math.max(1, qty - 1)">−</button>
              <span>{{ qty }}</span>
              <button type="button" aria-label="增加" @click="qty += 1">+</button>
            </div>
            <div class="aid-acts">
              <el-button v-if="orderOn" type="primary" size="large" @click="buyNow">{{ buyLabel }}</el-button>
              <el-button
                v-else-if="slotOn"
                type="primary"
                size="large"
                @click="goSlots"
              >{{ slotCtaLabel }}</el-button>
              <el-button
                v-else-if="ticketOn"
                type="primary"
                size="large"
                @click="goTicketApply"
              >{{ ticketApplyLabel }}</el-button>
              <el-button v-if="favOn" size="large" @click="fav">{{ favored ? '已收藏' : '收藏' }}</el-button>
              <el-button size="large" plain @click="goList">返回目录</el-button>
            </div>
          </div>
        </div>
      </section>

      <section class="aid-tabs">
        <div class="aid-tabbar" role="tablist">
          <button type="button" role="tab" :class="{ on: tab === 'intro' }" @click="tab = 'intro'">{{ introTab }}</button>
          <button
            v-if="reviewOn"
            type="button"
            role="tab"
            :class="{ on: tab === 'reviews' }"
            @click="tab = 'reviews'"
          >用户评价</button>
          <button type="button" role="tab" :class="{ on: tab === 'notice' }" @click="tab = 'notice'">{{ noticeTab }}</button>
        </div>
        <div v-if="tab === 'intro'" class="aid-rich" v-html="introHtml" />
        <div v-else-if="tab === 'reviews'" class="aid-reviews">
          <p v-if="goodRate != null" class="aid-rate">好评率 {{ goodRate }}%</p>
          <p v-if="!reviews.length" class="aid-muted">暂无评价</p>
          <article v-for="rv in reviews" :key="rv.id" class="aid-rv">
            <div class="aid-rv-hd">
              <el-rate :model-value="Number(rv.rating) || 0" disabled />
              <span class="aid-muted">{{ rv.displayName || rv.username || '用户' }} · {{ rv.createdAt || '' }}</span>
            </div>
            <p>{{ rv.body || '（无文字）' }}</p>
            <p v-if="rv.followBody" class="aid-follow">追评：{{ rv.followBody }}</p>
            <p v-if="rv.reply" class="aid-reply">商家回复：{{ rv.reply }}</p>
          </article>
        </div>
        <div v-else class="aid-notice">
          <p>{{ noticeText }}</p>
        </div>
      </section>
    </template>
  </div>
</template>

<script setup>

import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import http from '../../api/http'
import EmptyHint from '../../components/EmptyHint.vue'
import { toggleFavorite, touchBrowseHistory, upsertCart } from '../../utils/apiCalls'
import { APP_DELIVERED } from '../../appDelivered.js'
import { archiveCopy, formatArchiveScalar, getSchema, hasCap, schemaLabels } from '../../utils/domainSchema.js'
import { shouldShowDetailAttr } from '../../utils/detailAttrWhen.js'
import { requireLogin } from '../../utils/session'

const route = useRoute()
const router = useRouter()
const labels = schemaLabels()
const loading = ref(false)
const row = ref(null)
const qty = ref(1)
const tab = ref('intro')
const favored = ref(false)
const reviews = ref([])
const goodRate = ref(null)

const orderOn = computed(() => hasCap('order_lines'))
const slotOn = computed(() => hasCap('slot_reserve') && !orderOn.value)
const ticketOn = computed(() => hasCap('ticket_flow') && !orderOn.value && !slotOn.value)
const applySurfaceOn = computed(() => !!String(APP_DELIVERED?.applySurfaceStyle || '').trim())
const interactSurfaceOn = computed(() => !!String(APP_DELIVERED?.interactSurfaceStyle || '').trim())
const followSurfaceOn = computed(() => !!String(APP_DELIVERED?.followSurfaceStyle || '').trim())
const borrowSurfaceOn = computed(() => !!String(APP_DELIVERED?.borrowSurfaceStyle || '').trim())
const borrowSurface = computed(() => String(APP_DELIVERED?.borrowSurfaceStyle || '').trim())
const contentOn = computed(() => {
  if (orderOn.value || slotOn.value || ticketOn.value) return false
  const s = String(APP_DELIVERED?.contentSurfaceStyle || '').trim()
  return !!s || hasCap('content')
})
const favOn = computed(() => hasCap('favorites'))
const reviewOn = computed(() => hasCap('order_review'))
const priceOn = computed(() => orderOn.value || authorLooksLikePrice.value)
const introTab = computed(() => (contentOn.value ? '正文' : '详细介绍'))
const ticketApplyLabel = computed(() => {
  if (borrowSurfaceOn.value) {
    if (borrowSurface.value === 'bookshelf') {
      return labels.applyLabel || labels.ticketApplyLabel || '立即借阅'
    }
    if (borrowSurface.value === 'bedblocks') {
      return labels.applyLabel || labels.ticketApplyLabel || '申请床位'
    }
    if (borrowSurface.value === 'parcelshelf') {
      return labels.applyLabel || labels.ticketApplyLabel || '申请取件'
    }
    return labels.applyLabel || labels.ticketApplyLabel || '申请借用'
  }
  if (followSurfaceOn.value) {
    if (String(APP_DELIVERED?.followSurfaceStyle || '') === 'listing') {
      return labels.applyLabel || '预约带看'
    }
    return labels.applyLabel || '记录跟进'
  }
  if (applySurfaceOn.value) {
    return labels.applyLabel || labels.ticketApplyLabel || '立即报名'
  }
  if (interactSurfaceOn.value) {
    return labels.applyLabel || labels.ticketApplyLabel || '提交意向'
  }
  return labels.ticketApplyLabel || labels.applyLabel || '申请办理'
})
const slotCtaLabel = computed(() => {
  const verb = getSchema()?.entities?.reservation?.verbs?.apply || '预约'
  return labels.slotBookLabel || `选择时段${verb}`
})
const entityLabel = computed(() => {
  const e = getSchema()?.entities?.archive
  return e?.label || labels.archiveItemLabel || ''
})
const priceLabel = computed(() => {
  const f = (archiveCopy().fields || []).find((x) => x?.key === 'author')
  return f?.label || '价格'
})
/** 商城价签自己会说话；「单价(元)」是表单腔，真货架详情不露 */
const showPriceLabel = computed(() => {
  if (orderOn.value) return false
  const lab = String(priceLabel.value || '').trim()
  if (!lab) return false
  if (/单价|价格|售价/.test(lab) && lab.length <= 8) return false
  return true
})
const buyLabel = computed(() => labels.buyNowLabel || '加入购物车')
const noticeTab = computed(() => {
  if (orderOn.value) return '购买须知'
  if (slotOn.value) return '预约说明'
  if (contentOn.value) return '阅读说明'
  if (borrowSurfaceOn.value) {
    if (borrowSurface.value === 'bookshelf') return '借阅说明'
    if (borrowSurface.value === 'parcelshelf') return '取件说明'
    if (borrowSurface.value === 'bedblocks') return '床位说明'
    return '借用说明'
  }
  if (followSurfaceOn.value) return '跟进说明'
  if (applySurfaceOn.value) return '报名说明'
  if (interactSurfaceOn.value) return '意向说明'
  return '办理说明'
})
const noticeText = computed(
  () =>
    labels.archiveBuyNotice
    || (orderOn.value
      ? '下单后可在「我的订单」查看进度。'
      : slotOn.value
        ? '选定时段后可在「我的预约」查看进度；约满时段不可再约。'
        : contentOn.value
          ? '可在本页阅读正文；收藏与足迹在个人中心查看。'
          : borrowSurfaceOn.value
            ? (borrowSurface.value === 'bookshelf'
              ? '提交后可在「我的借阅」查看进度与应还日期。'
              : borrowSurface.value === 'parcelshelf'
                ? '提交后可在「我的单据」查看取件进度。'
                : borrowSurface.value === 'bedblocks'
                  ? '提交后可在「我的申请」查看床位安排。'
                  : '提交后可在「我的借用」查看进度与归还说明。')
            : followSurfaceOn.value
              ? '可在本页查看跟进说明并提交下一步。'
              : applySurfaceOn.value
                ? '提交后可在「我的报名」查看进度；名额满时可能无法再报。'
                : interactSurfaceOn.value
                  ? '提交后可在「我的记录」查看意向进度。'
                  : ticketOn.value
                    ? '提交申请后可在「我的单据」查看进度与续办说明。'
                    : '请按页面说明了解办理要求。'),
)

const authorLooksLikePrice = computed(() => {
  const f = (archiveCopy().fields || []).find((x) => x?.key === 'author')
  return f?.format === 'money' || f?.type === 'number'
})

const coverUrl = computed(() => String(row.value?.coverUrl || '').trim())
const coverStyle = computed(() =>
  coverUrl.value ? { backgroundImage: `url('${coverUrl.value}')` } : undefined,
)
const letter = computed(() => String(row.value?.title || '?').slice(0, 1))
const priceText = computed(() => {
  const f = (archiveCopy().fields || []).find((x) => x?.key === 'author') || {
    key: 'author',
    type: 'number',
    format: 'money',
  }
  if (row.value?.promoActive && row.value?.promoPrice != null) {
    return `¥${Number(row.value.promoPrice).toFixed(2)}`
  }
  return formatArchiveScalar(f, row.value?.author, '¥ —')
})
const lead = computed(() => {
  const note = stripHtml(row.value?.sellerNote || row.value?.seller_note)
  if (note) return note.slice(0, 120)
  const isbn = stripHtml(row.value?.isbn)
  if (isbn && !/^[A-Z]{1,4}-?[A-Z0-9]+$/i.test(isbn)) return isbn.slice(0, 80)
  return ''
})
const metaLine = computed(() => {
  if (!row.value) return ''
  const bits = []
  if (contentOn.value) {
    const author = String(row.value.author || '').trim()
    if (author && !/^\d+(\.\d+)?$/.test(author)) bits.push(author)
    const views = Number(row.value.viewCount)
    if (Number.isFinite(views) && views > 0) bits.push(`阅读 ${views}`)
    const cat = row.value.categoryName || (row.value.categoryNames || []).join(' · ')
    if (cat) bits.push(cat)
    return bits.join(' · ')
  }
  const stock = Number(row.value.stock)
  if (Number.isFinite(stock)) bits.push(`库存 ${stock}`)
  const sales = Number(row.value.salesCount ?? row.value.soldCount ?? row.value.sales)
  if (Number.isFinite(sales) && sales > 0) bits.push(`累计销量 ${sales}`)
  const region = String(row.value.region || '').trim()
  if (region) bits.push(`产地 ${region}`)
  const harvest = String(row.value.harvestOn || row.value.harvest_on || '').trim()
  if (harvest) bits.push(`采摘 ${harvest}`)
  const cat = row.value.categoryName || (row.value.categoryNames || []).join(' · ')
  if (cat) bits.push(cat)
  return bits.join(' · ')
})
/** 详情属性：适用且有值才露（有皮表按类裁；无表则空不露） */
const detailAttrLines = computed(() => {
  if (!row.value || contentOn.value) return []
  const skip = new Set([
    'title', 'author', 'isbn', 'category', 'categoryIds', 'stock', 'coverUrl',
    'sellerNote', 'promoPrice', 'promoStart', 'promoEnd',
  ])
  const names = Array.isArray(row.value.categoryNames) && row.value.categoryNames.length
    ? row.value.categoryNames.map((x) => String(x || '').trim()).filter(Boolean)
    : (String(row.value.categoryName || '').trim() ? [String(row.value.categoryName).trim()] : [])
  const fields = archiveCopy().fields || []
  const lines = []
  for (const f of fields) {
    if (!f?.key || skip.has(f.key)) continue
    if (f.type === 'hidden' || f.type === 'richtext') continue
    if (!shouldShowDetailAttr(row.value, f.key, names)) continue
    const text = formatArchiveScalar(f, row.value[f.key], '')
    if (!text || text === '—') continue
    lines.push({ key: f.key, label: f.label || f.key, text })
  }
  return lines.slice(0, 8)
})
const introHtml = computed(() => {
  const raw = String(row.value?.sellerNote || row.value?.content || '').trim()
  if (!raw) return contentOn.value ? '<p>暂无正文</p>' : '<p>暂无详细介绍</p>'
  if (/<[a-z][\s\S]*>/i.test(raw)) return raw
  return `<p>${raw.replace(/</g, '&lt;')}</p>`
})

function stripHtml(s) {
  return String(s || '')
    .replace(/<[^>]+>/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
}

function goList() {
  router.push('/archive')
}

function goTicketApply() {
  if (!row.value?.id || !requireLogin(router)) return
  router.push({
    path: '/archive',
    query: { highlight: String(row.value.id), openApply: '1' },
  })
}

function goSlots() {
  if (!row.value?.id || !requireLogin(router)) return
  router.push({
    path: '/slots',
    query: {
      itemId: String(row.value.id),
      title: row.value.title || '',
      price: row.value.author != null && row.value.author !== '' ? String(row.value.author) : '',
    },
  })
}

async function loadReviews(id) {
  if (!reviewOn.value) {
    reviews.value = []
    goodRate.value = null
    return
  }
  try {
    const rr = await http.get(`/api/order-reviews/by-item/${id}`, { params: { page: 1, size: 20 } })
    reviews.value = rr.data?.list || []
    goodRate.value = rr.data?.goodRate ?? null
  } catch {
    reviews.value = []
    goodRate.value = null
  }
}

async function load() {
  loading.value = true
  reviews.value = []
  goodRate.value = null
  qty.value = 1
  tab.value = 'intro'
  try {
    const res = await http.get(`/api/archive/${route.params.id}`)
    row.value = res.data || null
    if (row.value?.id) {
      await loadReviews(row.value.id)
      if (hasCap('browse_history')) {
        try {
          await touchBrowseHistory(row.value.id)
        } catch { /* ignore */ }
      }
    }
  } catch {
    row.value = null
    ElMessage.error('记录不存在或已下架')
  } finally {
    loading.value = false
  }
}

async function buyNow() {
  if (!row.value || !requireLogin(router)) return
  await upsertCart(row.value.id, qty.value)
  ElMessage.success('已加入购物车')
  router.push('/cart')
}

async function fav() {
  if (!row.value || !requireLogin(router)) return
  const res = await toggleFavorite(row.value.id)
  favored.value = !!res.data?.favorited
  ElMessage.success(favored.value ? '已收藏' : '已取消收藏')
}

watch(() => route.params.id, load)
onMounted(load)
</script>

<style scoped>
.aid {
  display: flex;
  flex-direction: column;
  gap: 18px;
}
.aid-empty { margin: 24px 0; }
.aid-hero {
  display: grid;
  grid-template-columns: minmax(240px, 420px) minmax(0, 1fr);
  gap: 28px;
  align-items: stretch;
  padding: 22px;
  background: var(--portal-surface, #fff);
  border: 1px solid var(--portal-line, #e2e8e6);
  border-radius: 14px;
  box-shadow: 0 8px 24px color-mix(in srgb, var(--portal-brand, #08545a) 6%, transparent);
}
.aid-cover {
  aspect-ratio: 1;
  border-radius: 12px;
  background:
    color-mix(in srgb, var(--portal-accent, #0b6e75) 12%, var(--portal-bg, #f4f6f5)) center / cover no-repeat;
  display: grid;
  place-items: center;
}
.aid-info {
  display: flex;
  flex-direction: column;
  min-height: 0;
  min-width: 0;
}
.aid-buybox {
  margin-top: auto;
  padding-top: 18px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  align-items: flex-start;
}
/* 内容阅读脸：宽封 + 正文优先，异于商城方图价签 */
.aid-content .aid-hero {
  grid-template-columns: minmax(200px, 320px) minmax(0, 1fr);
  gap: 24px;
  padding: 0 0 20px;
  border: none;
  border-radius: 0;
  box-shadow: none;
  background: transparent;
  border-bottom: 1px solid var(--portal-line, #e2e8e6);
}
.aid-content .aid-cover {
  aspect-ratio: 16 / 10;
  border-radius: 12px;
}
.aid-content .aid-info h1 {
  font-size: clamp(1.5rem, 2.6vw, 2rem);
  font-family: var(--portal-font-display, inherit);
}
.aid-content .aid-tabs {
  border: none;
  border-radius: 0;
  padding: 8px 0 24px;
  background: transparent;
}
.aid-content .aid-rich {
  font-size: 15px;
  line-height: 1.85;
  max-width: 42em;
}
.aid-cover-letter {
  font-size: 3rem;
  font-weight: 750;
  font-family: var(--portal-font-display, inherit);
  color: var(--portal-accent, #0b6e75);
  opacity: 0.4;
}
.aid-kicker {
  margin: 0 0 6px;
  font-size: 12px;
  font-weight: 650;
  letter-spacing: 0.06em;
  color: var(--portal-muted, #5b6b76);
}
.aid-info h1 {
  margin: 0 0 10px;
  font-size: clamp(1.35rem, 2.2vw, 1.75rem);
  font-weight: 750;
  font-family: var(--portal-font-display, inherit);
  color: var(--portal-ink, #15202b);
  line-height: 1.3;
}
.aid-lead {
  margin: 0 0 14px;
  font-size: 14px;
  line-height: 1.55;
  color: var(--portal-muted, #5b6b76);
}
.aid-price {
  margin: 0 0 10px;
  display: flex;
  align-items: baseline;
  gap: 8px;
}
.aid-price-label {
  font-size: 13px;
  color: var(--portal-muted, #5b6b76);
}
.aid-price strong {
  font-size: 1.85rem;
  font-weight: 800;
  color: var(--portal-accent, #0b6e75);
  font-variant-numeric: tabular-nums;
  letter-spacing: -0.02em;
}
.aid-meta {
  margin: 0;
  font-size: 13px;
  color: var(--portal-muted, #5b6b76);
  line-height: 1.5;
}
.aid-attrs {
  margin: 10px 0 0;
  padding: 0;
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.aid-attrs li {
  display: flex;
  gap: 8px;
  font-size: 13px;
  line-height: 1.45;
}
.aid-attr-k {
  flex-shrink: 0;
  color: var(--portal-muted, #5b6b76);
}
.aid-attr-k::after {
  content: '：';
}
.aid-attr-v {
  color: var(--portal-ink, #15202b);
  font-weight: 550;
  min-width: 0;
}
.aid-qty {
  display: inline-flex;
  align-items: center;
  gap: 0;
  margin: 0;
  border: 1px solid var(--portal-line, #e2e8e6);
  border-radius: 8px;
  overflow: hidden;
}
.aid-qty button {
  width: 36px;
  height: 36px;
  border: 0;
  background: var(--portal-bg, #f4f6f5);
  cursor: pointer;
  font-size: 16px;
  color: var(--portal-ink, #15202b);
}
.aid-qty span {
  min-width: 40px;
  text-align: center;
  font-variant-numeric: tabular-nums;
  font-weight: 600;
}
.aid-acts {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}
.aid-tabs {
  padding: 18px 22px 22px;
  background: var(--portal-surface, #fff);
  border: 1px solid var(--portal-line, #e2e8e6);
  border-radius: 14px;
}
.aid-tabbar {
  display: flex;
  gap: 20px;
  border-bottom: 1px solid var(--portal-line, #e2e8e6);
  margin-bottom: 16px;
}
.aid-tabbar button {
  border: 0;
  background: transparent;
  padding: 10px 0;
  cursor: pointer;
  font-size: 14px;
  font-weight: 550;
  color: var(--portal-muted, #5b6b76);
  border-bottom: 2px solid transparent;
  margin-bottom: -1px;
}
.aid-tabbar button.on {
  color: var(--portal-brand, #08545a);
  border-bottom-color: var(--portal-accent, #0b6e75);
  font-weight: 650;
}
.aid-rich {
  font-size: 14px;
  line-height: 1.7;
  color: var(--portal-ink, #15202b);
}
.aid-rich :deep(img) { max-width: 100%; border-radius: 8px; }
.aid-notice p {
  margin: 0;
  font-size: 14px;
  line-height: 1.7;
  color: var(--portal-ink, #334155);
}
.aid-reviews { display: flex; flex-direction: column; gap: 14px; }
.aid-rate {
  margin: 0;
  font-weight: 650;
  color: var(--portal-accent, #0b6e75);
}
.aid-muted { margin: 0; color: var(--portal-muted, #5b6b76); font-size: 13px; }
.aid-rv {
  margin: 0;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--portal-line, #e2e8e6);
}
.aid-rv p { margin: 6px 0 0; font-size: 14px; }
.aid-rv-hd { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; }
.aid-follow, .aid-reply { color: var(--portal-muted, #5b6b76); font-size: 13px; }
@media (max-width: 800px) {
  .aid-hero { grid-template-columns: 1fr; }
}
</style>
