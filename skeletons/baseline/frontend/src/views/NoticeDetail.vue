<template>
  <div>
    <el-button link type="primary" class="back" @click="$router.push('/notices')">← 返回公告</el-button>

    <div v-if="loading" class="state-skel"><PageSkeleton variant="text" /></div>
    <div v-else-if="!notice" class="state">
      <p>公告不存在或已删除</p>
      <el-button type="primary" @click="$router.push('/notices')">返回列表</el-button>
    </div>

    <template v-else>
      <section class="hero card">
        <p class="kicker">{{ pageTitle }}</p>
        <h1>{{ notice.title }}</h1>
        <p class="sub">
          {{ notice.publisherName || notice.publisherUsername || '系统' }}
          · {{ notice.createdAt || '—' }}
          <template v-if="notice.updatedAt && notice.updatedAt !== notice.createdAt">
            · 更新 {{ notice.updatedAt }}
          </template>
        </p>
      </section>

      <section class="card body-block">
        <h2>公告正文</h2>
        <div class="body">{{ notice.content || '（无正文）' }}</div>
      </section>
    </template>
  </div>
</template>

<script setup>
/** 基线公告详情：门户同壳；kicker 来自 Domain Schema */
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import http from '../api/http'
import PageSkeleton from '../components/PageSkeleton.vue'
import { schemaLabels } from '../utils/domainSchema.js'

const pageTitle = computed(() => schemaLabels().noticePageTitle || '公告')

const route = useRoute()
const notice = ref(null)
const loading = ref(true)

async function load() {
  loading.value = true
  notice.value = null
  try {
    const res = await http.get(`/api/notices/${route.params.id}`)
    notice.value = res.data
  } catch {
    notice.value = null
  } finally {
    loading.value = false
  }
}

watch(() => route.params.id, load)
onMounted(load)
</script>

<style scoped>
.back { margin: 0 0 10px; padding-left: 0; }
.state-skel { max-width: 720px; }
.state {
  padding: 48px 16px;
  text-align: center;
  color: var(--portal-muted, #6b7c8a);
  background: var(--portal-surface, #fff);
  border: var(--portal-border-width, 1px) dashed var(--portal-line, #dfe7ec);
  border-radius: var(--portal-radius, 12px);
}
.card {
  background: var(--portal-surface, #fff);
  border: var(--portal-border-width, 1px) solid var(--portal-line, #dfe7ec);
  border-radius: var(--portal-radius, 12px);
  box-shadow: var(--portal-shadow, none);
  padding: 20px 22px;
}
.hero { margin-bottom: 14px; }
.kicker {
  margin: 0 0 8px;
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: var(--portal-accent, #0b6e75);
}
.hero h1 {
  margin: 0 0 10px;
  font-size: 26px;
  line-height: 1.3;
  letter-spacing: -0.03em;
  color: var(--portal-ink, #15202b);
}
.sub {
  margin: 0;
  color: var(--portal-muted, #6b7c8a);
  font-size: 13px;
}
.body-block h2 {
  margin: 0 0 14px;
  font-size: 14px;
  font-weight: 650;
  color: var(--portal-ink, #15202b);
}
.body {
  white-space: pre-wrap;
  line-height: 1.75;
  font-size: 15px;
  color: var(--portal-ink, #15202b);
}
@media (max-width: 560px) {
  .hero h1 { font-size: 22px; }
}
</style>
