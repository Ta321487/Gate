<template>
  <n-tooltip trigger="hover" placement="top-start" :delay="100">
    <template #trigger>
      <button type="button" class="soft-tip-btn" :aria-label="ariaLabel">
        <svg viewBox="0 0 24 24" width="14" height="14" aria-hidden="true">
          <path
            fill="currentColor"
            d="M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20zm0 15a1.1 1.1 0 1 1 0-2.2A1.1 1.1 0 0 1 12 17zm1.2-4.4h-2.4V7h2.4v5.6z"
          />
        </svg>
      </button>
    </template>
    <div class="soft-visual-tip surface-style-tip">
      <div class="soft-visual-tip-title">{{ tipTitle }}</div>
      <div class="surface-list-wire" :data-group="group" :data-style="styleId || fallbackId">
        <!-- 内容 -->
        <template v-if="group === 'content' && (styleId || fallbackId) === 'folio'">
          <span class="slw-hero" />
          <span class="slw-line" />
          <span class="slw-line short" />
        </template>
        <template v-else-if="group === 'content' && (styleId || fallbackId) === 'coverwall'">
          <div class="slw-grid cols-2">
            <span class="slw-tile" /><span class="slw-tile" />
            <span class="slw-tile" /><span class="slw-tile" />
          </div>
        </template>
        <template v-else-if="group === 'content' && (styleId || fallbackId) === 'ledger'">
          <span class="slw-line" /><span class="slw-line" /><span class="slw-line short" />
        </template>
        <template v-else-if="group === 'content'">
          <div class="slw-split">
            <div class="slw-split-list">
              <span class="slw-line" /><span class="slw-line short" /><span class="slw-line" />
            </div>
            <span class="slw-tile tall" />
          </div>
        </template>

        <!-- 交易 -->
        <template v-else-if="group === 'trade' && (styleId || fallbackId) === 'shelfgrid'">
          <div class="slw-grid cols-3">
            <span class="slw-tile" /><span class="slw-tile" /><span class="slw-tile" />
            <span class="slw-tile" /><span class="slw-tile" /><span class="slw-tile" />
          </div>
        </template>
        <template v-else-if="group === 'trade' && (styleId || fallbackId) === 'menuboard'">
          <div class="slw-menu-row" v-for="n in 3" :key="n">
            <span class="slw-dot" /><span class="slw-line grow" />
          </div>
        </template>
        <template v-else-if="group === 'trade'">
          <div class="slw-menu-row" v-for="n in 3" :key="n">
            <span class="slw-line grow" />
          </div>
        </template>

        <!-- 预约 -->
        <template v-else-if="group === 'reserve' && (styleId || fallbackId) === 'slotstrip'">
          <div class="slw-chips">
            <span class="slw-chip" /><span class="slw-chip" /><span class="slw-chip" /><span class="slw-chip muted" />
          </div>
        </template>
        <template v-else-if="group === 'reserve' && (styleId || fallbackId) === 'roomstate'">
          <div class="slw-grid cols-4">
            <span class="slw-cell" /><span class="slw-cell on" /><span class="slw-cell" /><span class="slw-cell on" />
            <span class="slw-cell on" /><span class="slw-cell" /><span class="slw-cell on" /><span class="slw-cell" />
          </div>
        </template>
        <template v-else-if="group === 'reserve'">
          <div class="slw-vehicle">
            <span class="slw-tile" />
            <div class="slw-vehicle-meta">
              <span class="slw-line" /><span class="slw-line short" />
            </div>
          </div>
        </template>

        <!-- 借用 -->
        <template v-else-if="group === 'borrow' && (styleId || fallbackId) === 'bookshelf'">
          <div class="slw-spines">
            <span class="slw-spine" /><span class="slw-spine tall" /><span class="slw-spine" />
            <span class="slw-spine mid" /><span class="slw-spine" /><span class="slw-spine tall" />
          </div>
        </template>
        <template v-else-if="group === 'borrow' && (styleId || fallbackId) === 'stockrow'">
          <div class="slw-menu-row" v-for="n in 3" :key="n">
            <span class="slw-line grow" /><span class="slw-dot" /><span class="slw-line short" />
          </div>
        </template>
        <template v-else-if="group === 'borrow' && (styleId || fallbackId) === 'bedblocks'">
          <div class="slw-grid cols-4">
            <span class="slw-cell on" /><span class="slw-cell" /><span class="slw-cell on" /><span class="slw-cell muted" />
            <span class="slw-cell" /><span class="slw-cell on" /><span class="slw-cell" /><span class="slw-cell on" />
          </div>
        </template>
        <template v-else-if="group === 'borrow'">
          <div class="slw-grid cols-3">
            <span class="slw-cell on" /><span class="slw-cell on" /><span class="slw-cell" />
            <span class="slw-cell" /><span class="slw-cell on" /><span class="slw-cell on" />
          </div>
        </template>

        <!-- 报名 -->
        <template v-else-if="group === 'apply' && (styleId || fallbackId) === 'eventposter'">
          <div class="slw-grid cols-2">
            <span class="slw-tile tall" /><span class="slw-tile" />
            <span class="slw-tile" /><span class="slw-tile" />
          </div>
        </template>
        <template v-else-if="group === 'apply' && (styleId || fallbackId) === 'coursetable'">
          <div class="slw-grid cols-4">
            <span class="slw-cell on" /><span class="slw-cell" /><span class="slw-cell on" /><span class="slw-cell" />
            <span class="slw-cell" /><span class="slw-cell on" /><span class="slw-cell" /><span class="slw-cell on" />
          </div>
        </template>
        <template v-else-if="group === 'apply' && (styleId || fallbackId) === 'noticeboard'">
          <div class="slw-grid cols-3">
            <span class="slw-tile" /><span class="slw-tile" /><span class="slw-tile" />
          </div>
        </template>
        <template v-else-if="group === 'apply'">
          <div class="slw-vehicle">
            <span class="slw-tile" />
            <div class="slw-vehicle-meta">
              <span class="slw-line" /><span class="slw-line short" />
            </div>
          </div>
        </template>

        <!-- 互动 -->
        <template v-else-if="group === 'interact' && (styleId || fallbackId) === 'profilegrid'">
          <div class="slw-grid cols-3">
            <span class="slw-tile tall" /><span class="slw-tile tall" /><span class="slw-tile tall" />
          </div>
        </template>
        <template v-else-if="group === 'interact' && (styleId || fallbackId) === 'mutualpick'">
          <div class="slw-menu-row" v-for="n in 3" :key="n">
            <span class="slw-dot" /><span class="slw-line grow" /><span class="slw-chip" />
          </div>
        </template>
        <template v-else-if="group === 'interact'">
          <div class="slw-menu-row" v-for="n in 3" :key="n">
            <span class="slw-line grow" /><span class="slw-line short" />
          </div>
        </template>

        <!-- 跟进 -->
        <template v-else-if="group === 'follow' && (styleId || fallbackId) === 'pipeline'">
          <div class="slw-grid cols-4">
            <span class="slw-cell on" /><span class="slw-cell on" /><span class="slw-cell" /><span class="slw-cell" />
            <span class="slw-cell" /><span class="slw-cell on" /><span class="slw-cell" /><span class="slw-cell muted" />
          </div>
        </template>
        <template v-else-if="group === 'follow' && (styleId || fallbackId) === 'listing'">
          <div class="slw-vehicle">
            <span class="slw-tile" />
            <div class="slw-vehicle-meta">
              <span class="slw-line" /><span class="slw-line short" />
            </div>
          </div>
        </template>
        <template v-else-if="group === 'follow'">
          <div class="slw-menu-row" v-for="n in 3" :key="n">
            <span class="slw-line grow" /><span class="slw-dot" /><span class="slw-line short" />
          </div>
        </template>

        <!-- 报修 -->
        <template v-else-if="group === 'repair' && (styleId || fallbackId) === 'faultboard'">
          <div class="slw-grid cols-3">
            <span class="slw-cell on" /><span class="slw-cell on" /><span class="slw-cell" />
            <span class="slw-cell" /><span class="slw-cell" /><span class="slw-cell muted" />
          </div>
        </template>
        <template v-else-if="group === 'repair'">
          <div class="slw-menu-row" v-for="n in 3" :key="n">
            <span class="slw-dot" /><span class="slw-line grow" /><span class="slw-line short" />
          </div>
        </template>

        <!-- 审批 -->
        <template v-else-if="group === 'approve' && (styleId || fallbackId) === 'inboxsteps'">
          <div class="slw-menu-row" v-for="n in 3" :key="n">
            <span class="slw-line grow" />
            <span class="slw-dot" /><span class="slw-dot" /><span class="slw-dot" />
          </div>
        </template>
        <template v-else-if="group === 'approve'">
          <div class="slw-menu-row" v-for="n in 3" :key="n">
            <span class="slw-line grow" /><span class="slw-line short" />
          </div>
        </template>
      </div>
      <p class="small muted surface-style-tip-caption">{{ caption }}</p>
    </div>
  </n-tooltip>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  group: {
    type: String,
    required: true,
    validator: (v) => ['content', 'trade', 'reserve', 'borrow', 'apply', 'interact', 'follow', 'repair', 'approve'].includes(v),
  },
  styleId: { type: String, default: '' },
})

const LABELS = {
  content: {
    folio: '刊头阅读流',
    coverwall: '封面墙',
    ledger: '条目清单',
    splitdesk: '双栏阅读台',
  },
  trade: {
    shelfgrid: '货架密铺',
    menuboard: '档口菜单板',
    showtime: '排片选座行',
  },
  reserve: {
    slotstrip: '时段条/号源行',
    roomstate: '房态格',
    vehiclecard: '车型档期卡',
  },
  borrow: {
    bookshelf: '书架脊列',
    stockrow: '库存台账行',
    bedblocks: '床位色块墙',
    parcelshelf: '驿站货架格',
  },
  apply: {
    eventposter: '活动海报墙',
    coursetable: '课表网',
    noticeboard: '启事板',
    tourcard: '线路行程卡',
  },
  interact: {
    profilegrid: '资料卡片墙',
    mutualpick: '双选志愿卡',
    triprow: '行程同行行',
  },
  follow: {
    pipeline: '阶段看板',
    dossier: '档案行+下次跟进',
    listing: '挂牌价签卡',
  },
  repair: {
    ticketfeed: '我的工单进度流',
    faultboard: '分类故障看板',
  },
  approve: {
    typelist: '事项类型清单+申请',
    inboxsteps: '待审收件箱+步骤条',
  },
}

const GROUP_TITLE = {
  content: '内容列表示意',
  trade: '商品列表示意',
  reserve: '预约列表示意',
  borrow: '借用列表示意',
  apply: '报名列表示意',
  interact: '互动列表示意',
  follow: '跟进列表示意',
  repair: '报修列表示意',
  approve: '审批列表示意',
}

const FALLBACK = {
  content: 'folio',
  trade: 'shelfgrid',
  reserve: 'slotstrip',
  borrow: 'bookshelf',
  apply: 'eventposter',
  interact: 'profilegrid',
  follow: 'dossier',
  repair: 'ticketfeed',
  approve: 'typelist',
}

const fallbackId = computed(() => FALLBACK[props.group])
const tipTitle = computed(() => GROUP_TITLE[props.group] || '列表示意')
const ariaLabel = computed(() => `预览${tipTitle.value}`)
const caption = computed(() => {
  const map = LABELS[props.group] || {}
  const id = props.styleId || fallbackId.value
  return map[id] || id
})
</script>
