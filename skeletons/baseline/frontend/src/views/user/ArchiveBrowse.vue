<template>
  <div>
    <section class="hero">
      <h1>{{ plural }}检索</h1>
      <p>按名称检索{{ playUrlField ? '、在线播放' : '' }}，提交{{ verbs.apply || '申请' }}。</p>
      <div class="search">
        <el-input
          v-model="keyword"
          size="large"
          clearable
          :placeholder="`搜索${fieldLabel('title', '名称')} / ${fieldLabel('author', '型号')} / ${fieldLabel('isbn', '编号')}`"
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
      :apply-label="verbs.apply || '申请'"
      @apply="apply"
    />

    <div class="grid">
      <article v-for="row in list" :key="row.id" class="card">
        <div class="cover">{{ (row.title || '?').slice(0, 1) }}</div>
        <div class="meta">
          <h3>{{ row.title }}</h3>
          <p>{{ row.author || '—' }} · {{ row.categoryName || '未分类' }}</p>
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
              size="small"
              type="primary"
              :disabled="stockDisplay === 'count' && !stockOk(row)"
              @click="apply(row)"
            >{{ verbs.apply || '申请' }}</el-button>
          </div>
        </div>
      </article>
    </div>

    <div v-if="!list.length" class="empty">暂无记录，换个关键词试试。</div>
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
import { ElMessage, ElMessageBox } from 'element-plus'
import http from '../../api/http'
import RecommendStrip from '../../components/RecommendStrip.vue'
import { archiveCopy, ticketCopy } from '../../utils/domainSchema.js'

const archive = archiveCopy()
const ticket = ticketCopy()
const verbs = computed(() => ticket.verbs || {})
const plural = computed(() => archive.labelPlural || archive.label || '业务对象')
const fields = computed(() => archive.fields || [])
const stockDisplay = computed(() => archive.stockDisplay || 'count')
const playUrlField = computed(() => archive.playUrlField || '')

function fieldLabel(key, fallback) {
  const f = fields.value.find((x) => x.key === key)
  return (f && f.label) || fallback
}

function stockOk(row) {
  return Number(row.stock) > 0
}

function stockText(row) {
  if (stockDisplay.value === 'available') {
    const ok = fieldLabel('stock', '可播放')
    return stockOk(row) ? ok : `暂不${ok.replace(/^可/, '')}`
  }
  return stockOk(row) ? `可借 ${row.stock}` : '暂无库存'
}

function playUrlOf(row) {
  const key = playUrlField.value
  if (!key || !row) return ''
  // ArchiveStore 暴露 isbn；schema 用 playUrlField 指向该列
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
const recRef = ref(null)

async function loadCats() {
  const res = await http.get('/api/categories')
  categories.value = res.data || res || []
}

async function load() {
  const res = await http.get('/api/archive', {
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
  await ElMessageBox.confirm(
    `确认${verbs.value.apply || '申请'}「${row.title}」？`,
    verbs.value.apply || '申请',
  )
  await http.post('/api/tickets/apply', { itemId: row.id })
  ElMessage.success('已提交申请，等待审核')
  recRef.value?.reload?.()
}

onMounted(async () => {
  await loadCats()
  await load()
})
</script>

<style scoped>
.hero { margin-bottom: 18px; }
.hero h1 { margin: 0 0 6px; font-size: 22px; }
.hero p { margin: 0 0 14px; color: #64748b; font-size: 13px; }
.search { display: flex; gap: 10px; flex-wrap: wrap; }
.grid {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 14px;
}
.card {
  display: flex; gap: 14px; padding: 16px; background: #fff;
  border: 1px solid #e2e8f0; border-radius: 12px;
}
.cover {
  width: 48px; height: 48px; border-radius: 10px; flex-shrink: 0;
  display: grid; place-items: center; font-weight: 700; color: #0369a1;
  background: #e0f2fe;
}
.meta { flex: 1; min-width: 0; }
.meta h3 { margin: 0 0 4px; font-size: 16px; }
.meta p { margin: 0; color: #64748b; font-size: 12px; }
.row { margin-top: 10px; display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }
.empty { text-align: center; color: #94a3b8; padding: 40px 0; }
.pager { margin-top: 16px; display: flex; justify-content: flex-end; }
</style>
