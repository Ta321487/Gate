<template>
  <div>
    <section class="hero">
      <h1>{{ pageTitle }}</h1>
      <p>{{ pageLead }}</p>
    </section>

    <section v-if="canPost" class="composer card">
      <el-input
        v-model="draft"
        type="textarea"
        :rows="3"
        maxlength="500"
        show-word-limit
        placeholder="写下你的建议或咨询…"
      />
      <div class="composer-actions">
        <el-button type="primary" :loading="posting" @click="submit">发表留言</el-button>
      </div>
    </section>
    <GuestLoginHint v-else />

    <div class="list">
      <article v-for="n in list" :key="n.id" class="card item">
        <div class="meta">
          <strong>{{ n.nickname || n.username || '用户' }}</strong>
          <time>{{ n.createdAt || '—' }}</time>
        </div>
        <p class="body">{{ n.body }}</p>
        <div v-if="n.reply" class="reply">
          <span class="reply-tag">管理员回复</span>
          <p>{{ n.reply }}</p>
          <time v-if="n.repliedAt">{{ n.repliedAt }}</time>
        </div>
      </article>
    </div>

    <div v-if="!list.length" class="empty">暂无留言，欢迎抢沙发。</div>
    <div v-if="!isGuest" class="pager">
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
/** 门户留言板：列表可读；发表需登录 */
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import http from '../api/http'
import GuestLoginHint from '../components/GuestLoginHint.vue'
import { schemaLabels } from '../utils/domainSchema.js'
import { guestTeaserLimit, isGuestBrowseEnabled, isLoggedIn } from '../utils/session.js'

const labels = computed(() => schemaLabels())
const pageTitle = computed(() => labels.value.guestbookPageTitle || '留言板')
const pageLead = computed(
  () => labels.value.guestbookPageLead || '欢迎留下建议或咨询；管理员可简短回复。',
)
const isGuest = computed(() => isGuestBrowseEnabled() && !isLoggedIn())
const canPost = computed(() => isLoggedIn())

const list = ref([])
const total = ref(0)
const page = ref(1)
const size = ref(10)
const draft = ref('')
const posting = ref(false)

async function load() {
  const pageSize = isGuest.value ? guestTeaserLimit() : size.value
  const res = await http.get('/api/guestbook', {
    params: { page: isGuest.value ? 1 : page.value, size: pageSize },
  })
  list.value = res.data?.list || []
  total.value = res.data?.total || 0
}

async function submit() {
  const body = draft.value.trim()
  if (!body) {
    ElMessage.warning('请填写留言内容')
    return
  }
  posting.value = true
  try {
    await http.post('/api/guestbook', { body })
    ElMessage.success('已发表')
    draft.value = ''
    page.value = 1
    await load()
  } finally {
    posting.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.hero {
  margin-bottom: 22px;
  padding: 8px 0 4px;
}
.hero h1 {
  margin: 0 0 8px;
  font-family: var(--portal-font-display);
  font-size: 28px;
  letter-spacing: -0.03em;
  color: var(--portal-ink, #15202b);
}
.hero p {
  margin: 0;
  color: var(--portal-muted, #64748b);
  font-size: 14px;
  line-height: 1.55;
  max-width: 36em;
}
.composer {
  margin-bottom: 16px;
  padding: 16px 18px;
}
.composer-actions {
  margin-top: 10px;
  display: flex;
  justify-content: flex-end;
}
.list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.card {
  background: var(--portal-surface, #fff);
  border: var(--portal-border-width, 1px) solid var(--portal-line, #e2e8f0);
  border-radius: var(--portal-radius, 12px);
  box-shadow: var(--portal-shadow, none);
}
.item {
  padding: 16px 18px;
}
.meta {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  font-size: 13px;
  color: var(--portal-muted, #64748b);
  margin-bottom: 8px;
}
.meta strong {
  color: var(--portal-ink, #15202b);
}
.body {
  margin: 0;
  white-space: pre-wrap;
  line-height: 1.65;
  font-size: 14px;
  color: var(--portal-ink, #15202b);
}
.reply {
  margin-top: 12px;
  padding: 10px 12px;
  background: color-mix(in srgb, var(--portal-accent, #0b6e75) 8%, #fff);
  border-left: 3px solid var(--portal-accent, #0b6e75);
}
.reply-tag {
  display: inline-block;
  font-size: 12px;
  color: var(--portal-accent, #0b6e75);
  margin-bottom: 4px;
}
.reply p {
  margin: 0;
  white-space: pre-wrap;
  font-size: 13px;
  line-height: 1.55;
}
.reply time {
  display: block;
  margin-top: 6px;
  font-size: 12px;
  color: var(--portal-muted, #94a3b8);
}
.empty {
  padding: 40px 0;
  text-align: center;
  color: var(--portal-muted, #94a3b8);
  font-size: 14px;
}
.pager {
  margin-top: 18px;
  display: flex;
  justify-content: flex-end;
}
@media (max-width: 560px) {
  .hero h1 { font-size: 22px; }
}
</style>
