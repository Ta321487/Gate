<template>
  <EntityDetailLayout
    :loading="loading"
    :found="!!book"
    meta-title="书目信息"
    body-title="借阅须知"
    related-title="同分类可借"
  >
    <template #back>
      <el-button link type="primary" @click="$router.push('/books')">← 返回找书</el-button>
    </template>

    <template #empty>
      <p>图书不存在或已下架</p>
      <el-button type="primary" @click="$router.push('/books')">去找书</el-button>
    </template>

    <template v-if="book" #media>
      <img v-if="book.coverUrl" class="ed-cover" :src="book.coverUrl" :alt="book.title" />
      <div v-else class="ed-cover">{{ (book.title || '?').slice(0, 1) }}</div>
    </template>

    <template v-if="book" #kicker>{{ book.categoryName || '未分类' }}</template>
    <template v-if="book" #title>{{ book.title }}</template>
    <template v-if="book" #subtitle>{{ book.author || '佚名' }}</template>

    <template v-if="book" #status>
      <el-tag :type="canBorrow ? 'success' : 'info'" effect="plain">
        {{ canBorrow ? `可借 · 库存 ${book.stock}` : '暂不可借' }}
      </el-tag>
      <el-tag v-if="book.status" effect="plain" type="info">
        {{ statusLabel }}
      </el-tag>
    </template>

    <template v-if="book" #actions>
      <el-button type="primary" size="large" :disabled="!canBorrow" :loading="applying" @click="apply">
        申请借阅
      </el-button>
      <el-button size="large" @click="$router.push('/my-borrows')">我的借阅</el-button>
    </template>

    <template v-if="book" #meta>
      <dt>作者</dt><dd>{{ book.author || '佚名' }}</dd>
      <dt>分类</dt><dd>{{ book.categoryName || '未分类' }}</dd>
      <dt>ISBN</dt><dd>{{ book.isbn || '—' }}</dd>
      <dt>库存</dt><dd>{{ book.stock ?? 0 }}</dd>
      <dt>状态</dt><dd>{{ statusLabel }}</dd>
    </template>

    <template #body>
      <p class="ed-tip">
        提交申请后需管理员审核；通过后方可取书。请按时归还，逾期将影响后续借阅。
      </p>
    </template>

    <template v-if="related.length" #relatedExtra>
      <el-button link type="primary" @click="goCategory">查看该分类全部</el-button>
    </template>
    <template v-if="related.length" #related>
      <button
        v-for="row in related"
        :key="row.id"
        type="button"
        class="ed-rel"
        @click="$router.push(`/books/${row.id}`)"
      >
        <img v-if="row.coverUrl" class="ed-rel-cover" :src="row.coverUrl" alt="" />
        <div v-else class="ed-rel-cover">{{ (row.title || '?').slice(0, 1) }}</div>
        <div style="min-width:0">
          <p class="ed-rel-title">{{ row.title }}</p>
          <p class="ed-rel-sub">{{ row.author || '佚名' }} · 库存 {{ row.stock }}</p>
        </div>
      </button>
    </template>
  </EntityDetailLayout>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import http from '../../api/http'
import EntityDetailLayout from '../../components/EntityDetailLayout.vue'

const route = useRoute()
const router = useRouter()
const book = ref(null)
const related = ref([])
const loading = ref(true)
const applying = ref(false)

const canBorrow = computed(() => (book.value?.stock ?? 0) > 0 && book.value?.status !== 'unavailable')
const statusLabel = computed(() => {
  const s = book.value?.status
  if (s === 'unavailable') return '不可用'
  if (s === 'available' || !s) return '在架'
  return s
})

async function load() {
  loading.value = true
  book.value = null
  related.value = []
  try {
    const res = await http.get(`/api/books/${route.params.id}`)
    book.value = res.data
    await loadRelated()
  } catch {
    book.value = null
  } finally {
    loading.value = false
  }
}

async function loadRelated() {
  if (!book.value?.categoryId) return
  const res = await http.get('/api/books', {
    params: { page: 1, size: 6, categoryId: book.value.categoryId },
  })
  related.value = (res.data.list || [])
    .filter((x) => x.id !== book.value.id)
    .slice(0, 4)
}

function goCategory() {
  router.push({ path: '/books', query: { categoryId: book.value.categoryId } })
}

async function apply() {
  await ElMessageBox.confirm(`确认申请借阅《${book.value.title}》？`, '申请借阅')
  applying.value = true
  try {
    await http.post('/api/borrows/apply', { bookId: book.value.id })
    ElMessage.success('已提交申请，请在「我的借阅」查看进度')
    router.push('/my-borrows')
  } finally {
    applying.value = false
  }
}

watch(() => route.params.id, load)
onMounted(load)
</script>
