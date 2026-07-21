<template>
  <section v-if="list.length" class="rec">
    <div class="rec-hd">
      <h2>{{ title }}</h2>
      <span class="hint">{{ modeHint }}</span>
    </div>
    <div class="rec-grid">
      <article
        v-for="row in list"
        :key="row.id"
        class="rec-card"
        @click="onCardClick(row)"
      >
        <div class="glyph">
          <img v-if="row.coverUrl" :src="row.coverUrl" alt="" />
          <template v-else>{{ (row.title || '?').slice(0, 1) }}</template>
        </div>
        <div class="meta">
          <h3>{{ row.title }}</h3>
          <p>{{ row.author || '—' }} · {{ row.categoryName || '未分类' }}</p>
          <div class="acts" @click.stop>
            <el-button size="small" type="primary" @click="emit('apply', row)">
              {{ applyLabel }}
            </el-button>
          </div>
        </div>
      </article>
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
  limit: { type: Number, default: 6 },
})

const emit = defineEmits(['apply'])
const router = useRouter()
const list = ref([])
const mode = ref('cold')
const labels = schemaLabels()

const title = computed(
  () => labels.recommendSectionTitle || labels.recommendTitle || '猜你喜欢',
)

const modeHint = computed(() => {
  if (mode.value === 'personalized') return '根据你的偏好与历史'
  if (mode.value === 'hot') return '当前热门'
  if (mode.value === 'latest') return labels.recommendLatestHint || '最新发布'
  return ''
})

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
.rec { margin: 0 0 20px; }
.rec-hd {
  display: flex; align-items: baseline; gap: 10px; margin-bottom: 12px;
}
.rec-hd h2 {
  margin: 0; font-size: 17px; font-weight: 650; letter-spacing: -0.02em;
}
.hint { font-size: 12px; color: #94a3b8; }
.rec-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 10px;
}
.rec-card {
  display: flex; gap: 12px; padding: 12px 14px;
  background: var(--portal-surface, #fff);
  border: var(--portal-border-width, 1px) solid var(--portal-line, #e2e8f0);
  border-radius: var(--portal-radius, 10px);
  box-shadow: var(--portal-shadow, none);
  cursor: default;
}
.rec-card:hover {
  border-color: color-mix(in srgb, var(--portal-accent, #0b6e75) 35%, var(--portal-line, #e2e8f0));
}
.glyph {
  width: 40px; height: 40px; border-radius: var(--portal-radius-sm, 8px); flex-shrink: 0;
  display: grid; place-items: center; font-weight: 700; color: #0369a1;
  background: #e0f2fe; overflow: hidden;
}
.glyph img {
  width: 100%; height: 100%; object-fit: cover; display: block;
}
.meta { flex: 1; min-width: 0; }
.meta h3 {
  margin: 0 0 2px; font-size: 14px;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.meta p { margin: 0; color: #64748b; font-size: 12px; }
.acts { margin-top: 8px; }
</style>
