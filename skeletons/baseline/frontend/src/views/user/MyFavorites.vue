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
            <el-button
              v-if="canAddCart"
              size="small"
              type="primary"
              :disabled="!row.title || row.title === '已下架'"
              @click="addCart(row)"
            >
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
import { toggleFavorite, upsertCart } from '../../utils/apiCalls.js'
import { getSchema, menuLabel, schemaLabels } from '../../utils/domainSchema.js'

const labels = computed(() => schemaLabels())
const pageTitle = computed(() => labels.value.favoritesPageTitle || '我的收藏')
const pageLead = computed(
  () => labels.value.favoritesPageLead || '收藏感兴趣的商品，便于再次加购。',
)
const cartLabel = computed(() => menuLabel('user', 'cart', '购物车'))
const canAddCart = computed(() => (getSchema().capabilities || []).includes('order_lines'))

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
  await upsertCart(row.id || row.itemId, 1)
  ElMessage.success(`已加入${cartLabel.value}`)
}

async function toggle(row) {
  await toggleFavorite(row.id || row.itemId)
  ElMessage.success('已取消收藏')
  load()
}

onMounted(load)
</script>

<style scoped>
.hero { margin-bottom: 18px; }
.hero h1 { margin: 0 0 6px; font-size: 22px; }
.hero p { margin: 0 0 14px; color: #64748b; font-size: 13px; }
.grid {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 14px;
}
.card {
  display: flex; gap: 14px; padding: var(--portal-pad, 16px);
  border: 1px solid var(--portal-line, #e2e8f0);
  border-radius: var(--portal-radius, 12px);
  background: var(--portal-surface, #fff);
}
.cover {
  width: 72px; height: 72px; border-radius: 10px; flex-shrink: 0;
  display: grid; place-items: center; font-weight: 700; color: #0369a1;
  background: #e0f2fe; overflow: hidden;
}
.cover img { width: 100%; height: 100%; object-fit: cover; display: block; }
.meta { min-width: 0; flex: 1; }
.meta h3 { margin: 0 0 4px; font-size: 15px; }
.muted { margin: 0; color: #94a3b8; font-size: 12px; }
.row { margin-top: 10px; display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }
.empty { margin-top: 24px; color: #94a3b8; text-align: center; }
.pager { margin-top: 16px; display: flex; justify-content: flex-end; }
</style>
