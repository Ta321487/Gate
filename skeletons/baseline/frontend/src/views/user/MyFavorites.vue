<template>
  <div>
    <section class="hero">
      <h1>{{ pageTitle }}</h1>
      <p>{{ pageLead }}</p>
      <el-button @click="load">刷新</el-button>
    </section>

    <div class="grid">
      <article v-for="row in list" :key="row.id" class="card">
        <div class="cover">
          <img v-if="row.coverUrl" :src="row.coverUrl" alt="" />
          <template v-else>{{ (row.title || '?').slice(0, 1) }}</template>
        </div>
        <div class="meta">
          <h3>{{ row.title || '已下架' }}</h3>
          <p class="muted">收藏于 {{ row.createdAt || '—' }}</p>
          <div class="row">
            <el-button size="small" type="primary" :disabled="!row.title || row.title === '已下架'" @click="addCart(row)">
              加入{{ cartLabel }}
            </el-button>
            <el-button size="small" @click="toggle(row)">取消收藏</el-button>
          </div>
        </div>
      </article>
    </div>

    <div v-if="!list.length" class="empty">暂无收藏，去浏览加一加吧。</div>
    <div class="pager">
      <el-pagination
        v-model:current-page="page"
        v-model:page-size="size"
        background
        layout="total, prev, pager, next"
        :total="total"
        @current-change="load"
      />
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import http from '../../api/http'
import { menuLabel, schemaLabels } from '../../utils/domainSchema.js'

const labels = computed(() => schemaLabels())
const pageTitle = computed(() => labels.value.favoritesPageTitle || '我的收藏')
const pageLead = computed(
  () => labels.value.favoritesPageLead || '收藏感兴趣的商品，便于再次加购。',
)
const cartLabel = computed(() => menuLabel('user', 'cart', '购物车'))

const list = ref([])
const total = ref(0)
const page = ref(1)
const size = ref(10)

async function load() {
  const res = await http.get('/api/favorites', {
    params: { page: page.value, size: size.value },
  })
  list.value = res.data?.list || []
  total.value = res.data?.total || 0
}

async function addCart(row) {
  await http.post('/api/cart', { itemId: row.id || row.itemId, qty: 1 })
  ElMessage.success(`已加入${cartLabel.value}`)
}

async function toggle(row) {
  await http.post(`/api/favorites/${row.id || row.itemId}/toggle`)
  ElMessage.success('已取消收藏')
  load()
}

onMounted(load)
</script>

<style scoped>
.hero { margin-bottom: 16px; display: flex; flex-wrap: wrap; justify-content: space-between; gap: 8px; }
.hero h1 { margin: 0 0 6px; font-size: 22px; width: 100%; }
.hero p { margin: 0; color: #64748b; font-size: 13px; width: 100%; }
.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: var(--portal-gap, 12px);
}
.card {
  display: flex;
  gap: 12px;
  background: var(--portal-surface, #fff);
  border: var(--portal-border-width, 1px) solid var(--portal-line, #e2e8f0);
  border-radius: var(--portal-radius, 12px);
  box-shadow: var(--portal-shadow, none);
  padding: var(--portal-pad, 12px);
}
.cover {
  width: 72px;
  height: 72px;
  flex-shrink: 0;
  border-radius: var(--portal-radius-sm, 8px);
  background: color-mix(in srgb, var(--portal-bg, #f1f5f9) 70%, #fff);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 22px;
  color: #94a3b8;
  overflow: hidden;
}
.cover img { width: 100%; height: 100%; object-fit: cover; }
.meta { flex: 1; min-width: 0; }
.meta h3 { margin: 0 0 4px; font-size: 15px; }
.muted { margin: 0 0 8px; color: #94a3b8; font-size: 12px; }
.row { display: flex; flex-wrap: wrap; gap: 6px; }
.empty { text-align: center; color: #94a3b8; padding: 40px 0; }
.pager { margin-top: 16px; display: flex; justify-content: flex-end; }
</style>
