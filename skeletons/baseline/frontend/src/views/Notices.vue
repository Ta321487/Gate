<template>
  <div>
    <section class="hero">
      <h1>{{ pageTitle }}</h1>
      <p>{{ pageLead }}</p>
    </section>

    <PageSkeleton v-if="loading" variant="list" :rows="4" />
    <div v-else class="list">
      <article
        v-for="n in list"
        :key="n.id"
        class="card"
        :class="{ pinned: !!n.pinned }"
        role="button"
        tabindex="0"
        @click="$router.push(`/notices/${n.id}`)"
        @keyup.enter="$router.push(`/notices/${n.id}`)"
      >
        <div class="main">
          <h3>
            <el-tag v-if="n.pinned" size="small" type="warning" effect="plain" class="pin-tag">置顶</el-tag>
            <el-tag v-else-if="isFresh(n)" size="small" type="danger" effect="plain" class="pin-tag">新</el-tag>
            {{ n.title }}
          </h3>
          <p class="excerpt">{{ excerpt(n.content) }}</p>
        </div>
        <div class="aside">
          <span>{{ n.publisherName || n.publisherUsername || '系统' }}</span>
          <time>{{ n.createdAt || '—' }}</time>
        </div>
      </article>
    </div>

    <EmptyHint v-if="!loading && !list.length" title="暂无公告" desc="有通知时会出现在这里。" mark="告" />
    <div v-if="!isGuest" class="pager">
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
    <GuestLoginHint />
  </div>
</template>

<script setup>
/** 公告：标题/导语来自 Domain Schema，勿写死某一行业文案 */
import { computed, onMounted, ref } from 'vue'
import http from '../api/http'
import EmptyHint from '../components/EmptyHint.vue'
import GuestLoginHint from '../components/GuestLoginHint.vue'
import PageSkeleton from '../components/PageSkeleton.vue'
import { parseDateMs } from '../utils/dates.js'
import { schemaLabels } from '../utils/domainSchema.js'
import { guestTeaserLimit, isGuestBrowseEnabled, isLoggedIn } from '../utils/session.js'

const labels = computed(() => schemaLabels())
const pageTitle = computed(() => labels.value.noticePageTitle || '公告')
const pageLead = computed(() => labels.value.noticePageLead || '通知与须知，点击条目阅读全文。')
const isGuest = computed(() => isGuestBrowseEnabled() && !isLoggedIn())

const list = ref([])
const total = ref(0)
const page = ref(1)
const size = ref(10)
const loading = ref(false)

function excerpt(text, n = 88) {
  const s = (text || '').replace(/\s+/g, ' ').trim()
  if (s.length <= n) return s || '（无正文）'
  return s.slice(0, n) + '…'
}

/** 未置顶时：48 小时内发布标「新」 */
function isFresh(n) {
  if (n?.pinned) return false
  const t = parseDateMs(n?.createdAt)
  if (t == null) return false
  return Date.now() - t < 48 * 3600 * 1000
}

async function load() {
  loading.value = true
  try {
    const pageSize = isGuest.value ? guestTeaserLimit() : size.value
    const res = await http.get('/api/notices', {
      params: { page: isGuest.value ? 1 : page.value, size: pageSize },
    })
    list.value = res.data.list
    total.value = res.data.total
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.hero {
  margin-bottom: 22px;
  padding: 8px 0 4px;
}
.hero h1 {
  margin: 0 0 8px;
  font-family: var(--portal-font-display);
  font-size: 28px;
  letter-spacing: -0.03em;
  color: var(--portal-ink, #15202b);
}
.hero p {
  margin: 0;
  color: var(--portal-muted, #64748b);
  font-size: 14px;
  line-height: 1.55;
  max-width: 36em;
}
.list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.card {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  padding: 16px 18px;
  background: var(--portal-surface, #fff);
  border: var(--portal-border-width, 1px) solid var(--portal-line, #e2e8f0);
  border-left: 3px solid transparent;
  border-radius: var(--portal-radius, 0);
  box-shadow: var(--portal-shadow, none);
  cursor: pointer;
  transition: border-color 0.2s ease, transform 0.2s ease;
}
.card:hover {
  border-color: color-mix(in srgb, var(--portal-accent, #0b6e75) 45%, var(--portal-line, #e2e8f0));
  border-left-color: var(--portal-accent, #0b6e75);
  transform: translateX(2px);
}
.card.pinned {
  border-left-color: #d97706;
  background: color-mix(in srgb, #d97706 6%, var(--portal-surface, #fff));
}
.pin-tag { margin-right: 6px; vertical-align: middle; }
.main h3 {
  margin: 0 0 6px;
  font-size: 16px;
  font-family: var(--portal-font-display);
  color: var(--portal-ink, #15202b);
}
.excerpt {
  margin: 0;
  font-size: 13px;
  color: var(--portal-muted, #64748b);
  line-height: 1.5;
}
.aside {
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 4px;
  font-size: 12px;
  color: var(--portal-muted, #94a3b8);
  white-space: nowrap;
}
.empty {
  padding: 40px 0;
  text-align: center;
  color: var(--portal-muted, #94a3b8);
  font-size: 14px;
}
.pager {
  margin-top: 18px;
  display: flex;
  justify-content: flex-end;
}
@media (max-width: 560px) {
  .hero h1 { font-size: 22px; }
  .card { flex-direction: column; }
  .aside { align-items: flex-start; }
}
</style>
