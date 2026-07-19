<template>
  <div class="browse">
    <section class="rail">
      <div class="rail-copy">
        <h1>馆藏目录</h1>
        <p>按书名、作者或 ISBN 检索，在线提交借阅申请。</p>
      </div>
      <div class="search">
        <el-input
          v-model="keyword"
          size="large"
          clearable
          placeholder="搜索书名 / 作者 / ISBN"
          @keyup.enter="load"
        />
        <el-select v-model="categoryId" clearable placeholder="分类" size="large" style="width:140px" @change="load">
          <el-option v-for="c in categories" :key="c.id" :label="c.name" :value="c.id" />
        </el-select>
        <el-button type="primary" size="large" @click="load">搜索</el-button>
      </div>
    </section>

    <RecommendStrip
      ref="recRef"
      apply-label="申请借阅"
      detail-prefix="/books/"
      @apply="apply"
    />

    <div class="meta-bar">
      <span>共 {{ total }} 册</span>
      <span v-if="categoryId || keyword" class="filter-hint">已筛选</span>
    </div>

    <div class="list">
      <article
        v-for="(row, i) in list"
        :key="row.id"
        class="row-item"
        :style="{ '--delay': `${Math.min(i, 8) * 40}ms` }"
        @click="$router.push(`/books/${row.id}`)"
      >
        <div class="glyph" aria-hidden="true">{{ (row.title || '?').slice(0, 1) }}</div>
        <div class="meta">
          <h3>{{ row.title }}</h3>
          <p>{{ row.author || '佚名' }} · {{ row.categoryName || '未分类' }}</p>
        </div>
        <div class="actions" @click.stop>
          <span class="stock" :data-ok="row.stock > 0 ? '1' : '0'">
            {{ row.stock > 0 ? `可借 ${row.stock}` : '暂无' }}
          </span>
          <el-button
            type="primary"
            :disabled="row.stock <= 0"
            @click="apply(row)"
          >申请借阅</el-button>
        </div>
      </article>
    </div>

    <div v-if="!list.length" class="empty">暂无图书，换个关键词试试。</div>
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
import { onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import http from '../../api/http'
import RecommendStrip from '../../components/RecommendStrip.vue'

const route = useRoute()
const list = ref([])
const total = ref(0)
const page = ref(1)
const size = ref(9)
const keyword = ref('')
const categoryId = ref(null)
const categories = ref([])
const recRef = ref(null)

async function loadCats() {
  const res = await http.get('/api/categories')
  categories.value = res.data
}

async function load() {
  const res = await http.get('/api/books', {
    params: {
      page: page.value,
      size: size.value,
      keyword: keyword.value || undefined,
      categoryId: categoryId.value || undefined,
    },
  })
  list.value = res.data.list
  total.value = res.data.total
}

async function apply(row) {
  await ElMessageBox.confirm(`确认申请借阅《${row.title}》？`, '申请借阅')
  await http.post('/api/borrows/apply', { bookId: row.id })
  ElMessage.success('已提交申请，等待审核')
  recRef.value?.reload?.()
}

function applyQuery() {
  const q = route.query.categoryId
  if (q != null && q !== '') {
    const n = Number(q)
    categoryId.value = Number.isFinite(n) ? n : null
  }
}

watch(() => route.query.categoryId, () => {
  applyQuery()
  page.value = 1
  load()
})

onMounted(async () => {
  applyQuery()
  await loadCats()
  await load()
})
</script>

<style scoped>
.browse { font-family: var(--portal-font-ui); }
.rail {
  margin: 0 0 16px;
  padding: 18px 18px 16px;
  border: 1px solid var(--portal-line);
  background:
    linear-gradient(135deg, color-mix(in srgb, var(--portal-surface) 92%, var(--portal-accent-soft)) 0%, var(--portal-surface) 60%),
    var(--portal-surface);
  box-shadow: var(--portal-shadow);
}
.rail-copy h1 {
  margin: 0 0 4px;
  font-family: var(--portal-font-display);
  font-size: 22px;
  letter-spacing: -0.03em;
  color: var(--portal-ink);
}
.rail-copy p { margin: 0 0 14px; color: var(--portal-muted); font-size: 13px; }
.search { display: flex; gap: 10px; flex-wrap: wrap; }
.meta-bar {
  display: flex; gap: 12px; align-items: center;
  margin-bottom: 10px; font-size: 12px; color: var(--portal-muted);
}
.filter-hint {
  padding: 2px 8px;
  border: 1px solid var(--portal-line);
  color: var(--portal-accent);
}
.list { display: flex; flex-direction: column; gap: 8px; }
.row-item {
  display: grid;
  grid-template-columns: 52px 1fr auto;
  gap: 14px;
  align-items: center;
  padding: 14px 16px;
  background: var(--portal-surface);
  border: 1px solid var(--portal-line);
  border-left: 3px solid transparent;
  cursor: pointer;
  animation: rowIn 0.4s ease both;
  animation-delay: var(--delay, 0ms);
  transition: border-color 0.2s, transform 0.2s;
}
.row-item:hover {
  border-color: color-mix(in srgb, var(--portal-accent) 45%, var(--portal-line));
  border-left-color: var(--portal-accent);
  transform: translateX(2px);
}
@keyframes rowIn {
  from { opacity: 0; transform: translateY(6px); }
  to { opacity: 1; transform: translateY(0); }
}
.glyph {
  width: 52px; height: 64px;
  display: grid; place-items: center;
  font-family: var(--portal-font-display);
  font-weight: 700; font-size: 22px; color: #fff;
  background: var(--portal-cover);
}
.meta { min-width: 0; }
.meta h3 {
  margin: 0 0 4px; font-size: 16px; color: var(--portal-ink);
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.meta p { margin: 0; color: var(--portal-muted); font-size: 12px; }
.actions { display: flex; align-items: center; gap: 12px; flex-shrink: 0; }
.stock {
  font-size: 12px; font-weight: 600; color: var(--portal-muted);
  min-width: 4.5em; text-align: right;
}
.stock[data-ok="1"] { color: var(--portal-accent); }
.empty { text-align: center; color: var(--portal-muted); padding: 48px 0; }
.pager { margin-top: 18px; display: flex; justify-content: flex-end; }
@media (max-width: 720px) {
  .row-item { grid-template-columns: 44px 1fr; }
  .actions { grid-column: 1 / -1; justify-content: space-between; }
  .glyph { width: 44px; height: 54px; font-size: 18px; }
}
</style>
