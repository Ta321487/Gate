<template>
  <section v-if="visibleList.length" class="rec" aria-label="个性化推荐">
    <div class="rec-band">
      <div class="rec-hd">
        <div class="rec-title-row">
          <span class="rec-mark" aria-hidden="true" />
          <h2>{{ title }}</h2>
          <span v-if="modeLabel" class="mode-pill">{{ modeLabel }}</span>
        </div>
        <p class="rec-lead">{{ modeHint }}</p>
      </div>
      <div class="rec-rail" role="list">
        <article
          v-for="row in visibleList"
          :key="row.id"
          class="rec-tile"
          role="listitem"
          @click="onCardClick(row)"
        >
          <div class="poster">
            <img v-if="row.coverUrl" :src="row.coverUrl" alt="" />
            <span v-else class="poster-fallback">{{ (row.title || '?').slice(0, 1) }}</span>
            <span v-if="reasonOf(row)" class="why">{{ reasonOf(row) }}</span>
          </div>
          <div class="tile-meta">
            <h3 :title="row.title">{{ row.title }}</h3>
            <p>{{ row.categoryName || '未分类' }}</p>
            <button type="button" class="tile-cta" @click.stop="emit('apply', row)">
              {{ applyLabel }}
            </button>
          </div>
        </article>
      </div>
    </div>
  </section>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import http from '../api/http'
import { schemaLabels } from '../utils/domainSchema.js'

const props = defineProps({
  applyLabel: { type: String, default: '申请' },
  detailPrefix: { type: String, default: '' },
  limit: { type: Number, default: 8 },
  /** 当前页列表 id，避免推荐区与下方检索结果撞车 */
  excludeIds: { type: Array, default: () => [] },
})

const emit = defineEmits(['apply'])
const router = useRouter()
const list = ref([])
const mode = ref('cold')
const labels = schemaLabels()

const title = computed(
  () => labels.recommendSectionTitle || labels.recommendTitle || '猜你喜欢',
)

const modeLabel = computed(() => {
  if (mode.value === 'personalized') return '为你精选'
  if (mode.value === 'hot') return '热门'
  if (mode.value === 'latest') return labels.recommendLatestHint || '上新'
  return ''
})

const modeHint = computed(() => {
  if (mode.value === 'personalized') return '根据浏览、收藏与办理记录挑选，与下方完整列表不同'
  if (mode.value === 'hot') return '按近期热度排序，略过已办与当前页条目'
  if (mode.value === 'latest') return '补充上新条目，已避开当前检索结果'
  return '个性化推荐条'
})

const excludeSet = computed(() => {
  const s = new Set()
  for (const id of props.excludeIds || []) {
    const n = Number(id)
    if (n > 0) s.add(n)
  }
  return s
})

const visibleList = computed(() =>
  (list.value || []).filter((row) => !excludeSet.value.has(Number(row.id))),
)

function reasonOf(row) {
  return row.recommendReason || row.reason || ''
}

function onCardClick(row) {
  if (props.detailPrefix) {
    router.push(`${props.detailPrefix}${row.id}`)
  }
}

async function load() {
  try {
    const res = await http.get('/api/recommend', { params: { limit: props.limit } })
    const data = res.data || res || {}
    list.value = data.list || []
    mode.value = data.mode || 'cold'
  } catch {
    list.value = []
  }
}

onMounted(load)

defineExpose({ reload: load })
</script>

<style scoped>
.rec {
  margin: 0 0 22px;
}
.rec-band {
  padding: 14px 14px 12px;
  border-radius: calc(var(--portal-radius, 12px) + 2px);
  background:
    linear-gradient(
      135deg,
      color-mix(in srgb, var(--portal-accent, #0b6e75) 12%, transparent),
      color-mix(in srgb, var(--portal-accent, #0b6e75) 4%, var(--portal-bg, #f8fafc)) 55%,
      var(--portal-bg, #f1f5f9)
    );
  border: 1px solid color-mix(in srgb, var(--portal-accent, #0b6e75) 22%, var(--portal-line, #e2e8f0));
}
.rec-hd { margin-bottom: 12px; }
.rec-title-row {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.rec-mark {
  width: 8px;
  height: 18px;
  border-radius: 999px;
  background: var(--portal-accent, #0b6e75);
  flex-shrink: 0;
}
.rec-hd h2 {
  margin: 0;
  font-size: 16px;
  font-weight: 700;
  letter-spacing: -0.02em;
  color: var(--portal-ink, #0f172a);
}
.mode-pill {
  font-size: 11px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 999px;
  color: var(--portal-accent, #0b6e75);
  background: var(--portal-accent-soft, #d7eef0);
  border: 1px solid color-mix(in srgb, var(--portal-accent, #0b6e75) 28%, transparent);
}
.rec-lead {
  margin: 6px 0 0 16px;
  font-size: 12px;
  color: var(--portal-muted, #64748b);
  line-height: 1.4;
}
.rec-rail {
  display: flex;
  gap: 12px;
  overflow-x: auto;
  padding: 2px 2px 8px;
  scroll-snap-type: x mandatory;
  -webkit-overflow-scrolling: touch;
}
.rec-rail::-webkit-scrollbar { height: 6px; }
.rec-rail::-webkit-scrollbar-thumb {
  background: color-mix(in srgb, var(--portal-accent, #0b6e75) 35%, var(--portal-line, #cbd5e1));
  border-radius: 999px;
}
.rec-tile {
  flex: 0 0 132px;
  width: 132px;
  scroll-snap-align: start;
  cursor: default;
  background: transparent;
  border: none;
  padding: 0;
}
.poster {
  position: relative;
  width: 100%;
  aspect-ratio: 3 / 4;
  border-radius: 10px;
  overflow: hidden;
  background: color-mix(in srgb, var(--portal-accent, #0b6e75) 18%, var(--portal-line, #e2e8f0));
  box-shadow: 0 6px 16px color-mix(in srgb, var(--portal-ink, #0f172a) 12%, transparent);
}
.poster img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}
.poster-fallback {
  position: absolute;
  inset: 0;
  display: grid;
  place-items: center;
  font-size: 28px;
  font-weight: 700;
  color: color-mix(in srgb, var(--portal-accent, #0b6e75) 70%, var(--portal-ink, #0f172a));
}
.why {
  position: absolute;
  left: 6px;
  bottom: 6px;
  max-width: calc(100% - 12px);
  padding: 2px 6px;
  border-radius: 6px;
  font-size: 10px;
  font-weight: 650;
  line-height: 1.3;
  color: #fff;
  background: color-mix(in srgb, var(--portal-ink, #0f172a) 72%, transparent);
  backdrop-filter: blur(4px);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.tile-meta { margin-top: 8px; }
.tile-meta h3 {
  margin: 0;
  font-size: 13px;
  font-weight: 650;
  line-height: 1.35;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  min-height: 2.7em;
}
.tile-meta p {
  margin: 4px 0 0;
  font-size: 11px;
  color: var(--portal-muted, #64748b);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.tile-cta {
  margin-top: 8px;
  width: 100%;
  border: 1px solid color-mix(in srgb, var(--portal-accent, #0b6e75) 40%, var(--portal-line, #e2e8f0));
  background: var(--portal-accent-soft, #d7eef0);
  color: var(--portal-accent, #0b6e75);
  border-radius: 8px;
  padding: 5px 0;
  font-size: 12px;
  font-weight: 650;
  cursor: pointer;
}
.tile-cta:hover {
  background: color-mix(in srgb, var(--portal-accent, #0b6e75) 22%, var(--portal-accent-soft, #d7eef0));
}
@media (max-width: 560px) {
  .rec-tile { flex-basis: 118px; width: 118px; }
}
</style>
