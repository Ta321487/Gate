<template>
  <div>
    <section class="hero">
      <h1>{{ pageTitle }}</h1>
      <p>{{ pageLead }}</p>
      <div class="hero-actions">
        <el-button @click="load">刷新</el-button>
        <el-button v-if="list.length" type="primary" plain @click="exportList">导出清单</el-button>
        <el-button v-if="list.length" plain @click="copyList">复制清单</el-button>
      </div>
      <p v-if="shareHint" class="share-hint">{{ shareHint }}</p>
      <p v-if="favoriteGroupOn && playlistVisibilityHint" class="share-hint">{{ playlistVisibilityHint }}</p>
      <div v-if="favoriteGroupOn" class="group-filter">
        <span class="group-lab">{{ favoriteGroupLabel }}</span>
        <el-input
          v-model="groupFilter"
          clearable
          :placeholder="favoriteGroupPlaceholder"
          style="max-width:220px"
          @keyup.enter="load"
        />
        <el-button @click="load">按分组查看</el-button>
      </div>
    </section>

    <div class="grid">
      <article v-for="row in list" :key="row.id" class="card">
        <div class="cover">
          <img v-if="row.coverUrl" :src="row.coverUrl" alt="" />
          <template v-else>{{ (row.title || '?').slice(0, 1) }}</template>
        </div>
        <div class="meta">
          <h3>{{ row.title || '已下架' }}</h3>
          <p v-if="shopLabel(row)" class="muted shop">店铺：{{ shopLabel(row) }}</p>
          <p class="muted">收藏于 {{ row.createdAt || '—' }}</p>
          <div v-if="favoriteGroupOn" class="group-edit">
            <el-input
              v-model="row._groupName"
              size="small"
              :placeholder="favoriteGroupPlaceholder"
              style="max-width:140px"
            />
            <el-switch
              v-model="row._isPublic"
              size="small"
              :active-text="playlistPublicLabel"
              :inactive-text="playlistPrivateLabel"
            />
            <el-button size="small" :loading="row._saving" @click="saveMeta(row)">保存分组</el-button>
          </div>
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

    <EmptyHint
      v-if="!list.length"
      title="暂无收藏"
      desc="去浏览加一加吧。"
      mark="藏"
      cta-label="去浏览"
      @cta="$router.push('/archive')"
    />
    <div class="pager">
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
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import http from '../../api/http'
import EmptyHint from '../../components/EmptyHint.vue'
import { toggleFavorite, upsertCart } from '../../utils/apiCalls.js'
import { getSchema, menuLabel, schemaLabels } from '../../utils/domainSchema.js'
import { downloadCsv } from '../../utils/csvDownload.js'

const labels = computed(() => schemaLabels())
const thicken = computed(() => getSchema()?.contentThicken || {})
const pageTitle = computed(() => labels.value.favoritesPageTitle || '我的收藏')
const pageLead = computed(
  () => labels.value.favoritesPageLead || '收藏感兴趣的内容，便于再次查看。',
)
const shareHint = computed(
  () => labels.value.favShareHint || labels.value.listingCompareHint || '',
)
const favoriteGroupOn = computed(
  () => !!thicken.value.favoriteGroup || !!thicken.value.playlistVisibility,
)
const favoriteGroupLabel = computed(() => labels.value.favoriteGroupLabel || '分组')
const favoriteGroupPlaceholder = computed(
  () => labels.value.favoriteGroupPlaceholder || '如：通勤、考试周',
)
const playlistPublicLabel = computed(() => labels.value.playlistPublicLabel || '公开歌单')
const playlistPrivateLabel = computed(() => labels.value.playlistPrivateLabel || '仅自己可见')
const playlistVisibilityHint = computed(() => labels.value.playlistVisibilityHint || '')
const cartLabel = computed(() => menuLabel('user', 'cart', '购物车'))
const canAddCart = computed(() => (getSchema().capabilities || []).includes('order_lines'))
const marketplace = computed(() => !!getSchema()?.shopMarketplace)

function shopLabel(row) {
  if (!marketplace.value || !row) return ''
  return String(row.shopName || row.shop_name || '').trim()
}

const list = ref([])
const total = ref(0)
const page = ref(1)
const size = ref(10)
const groupFilter = ref('')

async function load() {
  const res = await http.get('/api/favorites', {
    params: {
      page: page.value,
      size: size.value,
      groupName: favoriteGroupOn.value ? (groupFilter.value || undefined) : undefined,
    },
  })
  list.value = (res.data?.list || []).map((row) => ({
    ...row,
    _groupName: row.groupName || '',
    _isPublic: !!row.isPublic,
    _saving: false,
  }))
  total.value = res.data?.total || 0
}

async function saveMeta(row) {
  if (!row?.id && !row?.itemId) return
  row._saving = true
  try {
    await http.patch(`/api/favorites/${row.id || row.itemId}`, {
      groupName: row._groupName || '',
      isPublic: !!row._isPublic,
    })
    ElMessage.success('分组已保存')
  } catch (e) {
    ElMessage.error(e?.response?.data?.message || e?.message || '保存失败')
  } finally {
    row._saving = false
  }
}

function listLines() {
  return (list.value || [])
    .map((row, i) => {
      const title = row.title || '已下架'
      const shop = shopLabel(row)
      return shop ? `${i + 1}. ${title}（${shop}）` : `${i + 1}. ${title}`
    })
    .join('\n')
}

function exportList() {
  const headers = ['标题', '店铺', '收藏时间']
  const rows = (list.value || []).map((row) => [
    row.title || '已下架',
    shopLabel(row) || '',
    row.createdAt || '',
  ])
  downloadCsv(`${pageTitle.value || '收藏清单'}.csv`, headers, rows)
  ElMessage.success('已导出清单，可发给同学查看')
}

async function copyList() {
  const text = listLines()
  if (!text) {
    ElMessage.warning('暂无收藏可复制')
    return
  }
  try {
    await navigator.clipboard.writeText(text)
    ElMessage.success('清单已复制，可粘贴分享')
  } catch {
    ElMessage.error('复制失败，请改用导出清单')
  }
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
.hero p { margin: 0 0 14px; color: var(--portal-muted, #64748b); font-size: 13px; }
.hero-actions { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 8px; }
.share-hint { margin: 0; color: var(--portal-muted, #64748b); font-size: 12px; }
.group-filter { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 10px; align-items: center; }
.group-lab { font-size: 13px; color: var(--portal-muted, #64748b); }
.group-edit { margin-top: 8px; display: flex; flex-wrap: wrap; gap: 8px; align-items: center; }
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
  display: grid; place-items: center; font-weight: 700;
  color: var(--portal-brand, #0369a1);
  background: color-mix(in srgb, var(--portal-accent, #0b6e75) 16%, var(--portal-surface, #fff));
  overflow: hidden;
}
.cover img { width: 100%; height: 100%; object-fit: cover; display: block; }
.meta { min-width: 0; flex: 1; }
.meta h3 { margin: 0 0 4px; font-size: 15px; }
.muted { margin: 0; color: var(--portal-muted, #94a3b8); font-size: 12px; }
.shop { margin: 2px 0 0; color: color-mix(in srgb, var(--portal-accent, #0b6e75) 65%, var(--portal-muted, #94a3b8)); }
.row { margin-top: 10px; display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }
.empty { margin-top: 24px; color: var(--portal-muted, #94a3b8); text-align: center; }
.pager { margin-top: 16px; display: flex; justify-content: flex-end; }
</style>
