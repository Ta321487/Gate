<template>
  <div>
    <section class="hero">
      <h1>{{ pageTitle }}</h1>
      <p>{{ pageLead }}</p>
      <div class="acts">
        <el-button type="primary" @click="$router.push('/archive')">去发帖 / 浏览</el-button>
        <el-button @click="load">刷新</el-button>
      </div>
    </section>

    <div class="grid">
      <article v-for="row in list" :key="row.id" class="card">
        <div class="meta">
          <h3>{{ row.title || '（无标题）' }}</h3>
          <p class="muted">
            {{ row.categoryName || '未分类' }}
            <template v-if="row.createdAt"> · {{ row.createdAt }}</template>
          </p>
          <p v-if="row.deletedAt" class="warn">已下架 · {{ row.deletedAt }}</p>
          <RichTextView v-if="row.isbn" class="excerpt" :html="row.isbn" compact />
          <div class="row">
            <el-button size="small" :disabled="!!row.deletedAt" @click="openDetail(row)">查看</el-button>
          </div>
        </div>
      </article>
    </div>

    <div v-if="!list.length" class="empty">暂无发布记录，去检索页发一篇吧。</div>
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

    <el-drawer v-model="detailVisible" :title="detail?.title || '详情'" size="520px" destroy-on-close>
      <template v-if="detail">
        <p class="muted">{{ detail.categoryName || '未分类' }}</p>
        <p v-if="detail.deletedAt" class="warn">已下架 · {{ detail.deletedAt }}</p>
        <RichTextView :html="detail.isbn || ''" />
      </template>
    </el-drawer>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import http from '../../api/http'
import RichTextView from '../../components/RichTextView.vue'
import { archiveCopy, menuLabel, schemaLabels } from '../../utils/domainSchema.js'

const archive = archiveCopy()
const labels = computed(() => schemaLabels())
const unit = computed(() => archive.label || '主帖')
const pageTitle = computed(
  () => labels.value.myArchivePageTitle || menuLabel('user', 'my_archive', `我的${unit.value}`),
)
const pageLead = computed(
  () =>
    labels.value.myArchivePageLead ||
    `本人发布的${unit.value}即时可见；站长下架后仍可在此查看状态。`,
)

const list = ref([])
const total = ref(0)
const page = ref(1)
const size = ref(10)
const detailVisible = ref(false)
const detail = ref(null)

async function load() {
  const res = await http.get('/api/archive/mine', {
    params: { page: page.value, size: size.value },
  })
  list.value = res.data?.list || []
  total.value = res.data?.total || 0
}

async function openDetail(row) {
  if (!row?.id || row.deletedAt) return
  try {
    const res = await http.get(`/api/archive/${row.id}`)
    detail.value = res.data || row
  } catch {
    detail.value = row
  }
  detailVisible.value = true
}

onMounted(load)
</script>

<style scoped>
.hero { margin-bottom: 18px; }
.hero h1 { margin: 0 0 6px; font-size: 22px; }
.hero p { margin: 0 0 14px; color: #64748b; font-size: 13px; }
.acts { display: flex; gap: 10px; flex-wrap: wrap; }
.grid {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 14px;
}
.card {
  padding: var(--portal-pad, 16px);
  border: 1px solid var(--portal-line, #e2e8f0);
  border-radius: var(--portal-radius, 12px);
  background: var(--portal-surface, #fff);
}
.meta h3 { margin: 0 0 6px; font-size: 15px; }
.muted { margin: 0; color: #94a3b8; font-size: 12px; }
.warn { margin: 8px 0 0; color: #b45309; font-size: 12px; }
.excerpt { margin-top: 8px; max-height: 72px; overflow: hidden; }
.row { margin-top: 12px; display: flex; gap: 10px; }
.empty { margin-top: 24px; color: #94a3b8; text-align: center; }
.pager { margin-top: 16px; display: flex; justify-content: flex-end; }
</style>
