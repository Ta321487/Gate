<template>
  <div v-if="enabled" class="ai-float" aria-live="polite">
    <transition name="ai-panel">
      <div v-if="open" class="panel" role="dialog" :aria-label="pageTitle">
        <header class="panel-hd">
          <div class="hd-text">
            <strong>{{ pageTitle }}</strong>
            <span class="hint">{{
              deepseekConfigured
                ? 'DeepSeek 优先 · 知识表作上下文'
                : '未配置 Key · FAQ 回落'
            }}</span>
          </div>
          <button type="button" class="icon-btn" aria-label="关闭" @click="open = false">×</button>
        </header>

        <section v-if="hot.length" class="hot">
          <div class="hot-label">热门</div>
          <div class="hot-list">
            <button
              v-for="h in hot"
              :key="h.id"
              type="button"
              class="hot-chip"
              @click="useHot(h)"
            >
              {{ h.title }}
            </button>
          </div>
        </section>

        <div ref="scrollEl" class="msgs">
          <div v-if="!list.length" class="empty">{{ emptyHint }}</div>
          <article
            v-for="n in list"
            :key="n.id"
            class="bubble"
            :class="n.role === 'assistant' ? 'bot' : 'me'"
          >
            <p class="body">{{ n.content }}</p>
            <div v-if="n.role === 'assistant'" class="actions">
              <el-tag size="small" type="info">{{ n.source || 'faq' }}</el-tag>
              <button type="button" class="link" @click="speak(n.content)">播报</button>
              <button type="button" class="link ok" @click="feedback(n, true)">满意</button>
              <button type="button" class="link" @click="feedback(n, false)">不满意</button>
            </div>
          </article>
        </div>

        <footer v-if="canChat" class="composer">
          <div class="tools">
            <el-input
              v-model="category"
              size="small"
              clearable
              :placeholder="categoryPlaceholder"
              maxlength="32"
            />
            <el-upload :show-file-list="false" :http-request="uploadAsk" accept="image/*">
              <el-button size="small">上传图片</el-button>
            </el-upload>
          </div>
          <div class="send-row">
            <el-input
              v-model="draft"
              type="textarea"
              :rows="2"
              maxlength="1000"
              resize="none"
              placeholder="输入问题…"
              @keydown.enter.exact.prevent="ask"
            />
            <el-button type="primary" :loading="asking" @click="ask">发送</el-button>
          </div>
        </footer>
        <footer v-else class="composer guest">
          <GuestLoginHint />
        </footer>
      </div>
    </transition>

    <button
      type="button"
      class="fab"
      :class="{ active: open }"
      :title="pageTitle"
      :aria-expanded="open ? 'true' : 'false'"
      @click="toggle"
    >
      <span class="fab-ico" aria-hidden="true">{{ open ? '×' : 'AI' }}</span>
    </button>
  </div>
</template>

<script setup>
/** 门户全局 AI 助手：右下角悬浮 + 小弹窗（能力与整页一致，形态跟市面客服） */
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import http from '../api/http'
import GuestLoginHint from './GuestLoginHint.vue'
import { hasCap, schemaLabels } from '../utils/domainSchema.js'
import { isLoggedIn } from '../utils/session.js'

const OPEN_EVENT = 'thesis-open-ai-assistant'

const enabled = computed(() => hasCap('ai_assistant'))
const labels = computed(() => schemaLabels())
const pageTitle = computed(() => labels.value.aiAssistantPageTitle || 'AI智能助手')
const categoryPlaceholder = computed(() => {
  const t = pageTitle.value || ''
  if (t.includes('农产品') || t.includes('导购')) return '品类（如水果）'
  if (t.includes('阅读') || t.includes('图书')) return '分类（可选）'
  return '分类（可选）'
})
const emptyHint = computed(() =>
  canChat.value ? '先提一个问题，或点上方热门。' : '登录后可对话；可先浏览热门问答。',
)
const canChat = computed(() => isLoggedIn())

const open = ref(false)
const hot = ref([])
const list = ref([])
const draft = ref('')
const category = ref('')
const asking = ref(false)
const deepseekConfigured = ref(false)
const scrollEl = ref(null)

function toggle() {
  open.value = !open.value
}

function openPanel() {
  open.value = true
}

async function loadHot() {
  try {
    const res = await http.get('/api/ai-assistant/hot', { params: { limit: 6 } })
    hot.value = res.data?.list || []
    deepseekConfigured.value = !!res.data?.deepseekConfigured
  } catch {
    hot.value = []
  }
}

async function loadMessages() {
  if (!canChat.value) {
    list.value = []
    return
  }
  try {
    const res = await http.get('/api/ai-assistant/messages', {
      params: { page: 1, size: 30 },
    })
    // 弹窗里按时间正序更像聊天
    const rows = res.data?.list || []
    list.value = [...rows].reverse()
  } catch {
    list.value = []
  }
}

async function scrollBottom() {
  await nextTick()
  const el = scrollEl.value
  if (el) el.scrollTop = el.scrollHeight
}

function useHot(h) {
  draft.value = h.title || ''
  category.value = h.category || ''
  if (!canChat.value) {
    ElMessage.info('登录后即可发送')
  }
}

async function ask() {
  const question = draft.value.trim()
  if (!question) {
    ElMessage.warning('请输入问题')
    return
  }
  asking.value = true
  try {
    await http.post('/api/ai-assistant/ask', {
      question,
      category: category.value.trim(),
    })
    draft.value = ''
    await loadMessages()
    await loadHot()
    await scrollBottom()
  } finally {
    asking.value = false
  }
}

async function uploadAsk(option) {
  const fd = new FormData()
  fd.append('file', option.file)
  if (draft.value.trim()) fd.append('question', draft.value.trim())
  if (category.value.trim()) fd.append('category', category.value.trim())
  asking.value = true
  try {
    const res = await http.post('/api/ai-assistant/ask-image', fd)
    if (res.data?.resolvedCategory) {
      category.value = res.data.resolvedCategory
      ElMessage.success(`已识别品类：${res.data.resolvedCategory}`)
    }
    await loadMessages()
    await loadHot()
    await scrollBottom()
  } finally {
    asking.value = false
  }
}

function speak(text) {
  if (!window.speechSynthesis) {
    ElMessage.warning('当前浏览器不支持语音播报')
    return
  }
  window.speechSynthesis.cancel()
  const u = new SpeechSynthesisUtterance(String(text || ''))
  u.lang = 'zh-CN'
  window.speechSynthesis.speak(u)
}

async function feedback(row, satisfied) {
  await http.post('/api/ai-assistant/feedback', {
    messageId: row.id,
    satisfied,
  })
  ElMessage.success(satisfied ? '已记录满意' : '已记录不满意')
}

watch(open, async (v) => {
  if (!v) return
  await loadHot()
  await loadMessages()
  await scrollBottom()
})

onMounted(() => {
  window.addEventListener(OPEN_EVENT, openPanel)
  if (enabled.value) loadHot()
})
onUnmounted(() => {
  window.removeEventListener(OPEN_EVENT, openPanel)
})

defineExpose({ openPanel })
</script>

<style scoped>
.ai-float {
  position: fixed;
  right: 20px;
  bottom: 24px;
  z-index: 40;
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 12px;
  pointer-events: none;
}
.ai-float > * {
  pointer-events: auto;
}
.fab {
  width: 52px;
  height: 52px;
  border: none;
  border-radius: 50%;
  cursor: pointer;
  color: #fff;
  font-weight: 700;
  font-size: 14px;
  letter-spacing: 0.04em;
  background: linear-gradient(
    135deg,
    var(--portal-accent, #0b6e75),
    color-mix(in srgb, var(--portal-accent, #0b6e75) 45%, #0a3d42)
  );
  box-shadow: 0 8px 24px color-mix(in srgb, var(--portal-accent, #0b6e75) 35%, transparent);
}
.fab.active {
  background: var(--portal-ink, #15202b);
}
.fab-ico {
  display: block;
  line-height: 1;
}
.panel {
  width: min(380px, calc(100vw - 32px));
  height: min(520px, calc(100vh - 120px));
  display: flex;
  flex-direction: column;
  background: var(--portal-surface, #fff);
  border: 1px solid var(--portal-line, #e2e8f0);
  border-radius: 16px;
  box-shadow: 0 16px 48px rgba(15, 23, 42, 0.18);
  overflow: hidden;
}
.panel-hd {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 8px;
  padding: 12px 14px;
  border-bottom: 1px solid var(--portal-line, #e2e8f0);
  background: color-mix(in srgb, var(--portal-accent, #0b6e75) 8%, #fff);
}
.hd-text {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}
.hd-text strong {
  font-size: 14px;
  color: var(--portal-ink, #15202b);
}
.hint {
  font-size: 11px;
  color: var(--portal-muted, #64748b);
}
.icon-btn {
  border: none;
  background: transparent;
  font-size: 22px;
  line-height: 1;
  cursor: pointer;
  color: var(--portal-muted, #64748b);
  padding: 0 4px;
}
.hot {
  padding: 8px 12px 0;
  flex-shrink: 0;
}
.hot-label {
  font-size: 11px;
  color: var(--portal-muted, #64748b);
  margin-bottom: 6px;
}
.hot-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  max-height: 72px;
  overflow: auto;
}
.hot-chip {
  border: 1px solid var(--portal-line, #e2e8f0);
  background: var(--portal-accent-soft, #f0f9fa);
  border-radius: 999px;
  padding: 4px 10px;
  font-size: 12px;
  cursor: pointer;
  color: var(--portal-ink, #15202b);
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.msgs {
  flex: 1;
  overflow: auto;
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  background: color-mix(in srgb, var(--portal-bg, #eef3f5) 70%, #fff);
}
.empty {
  margin: auto;
  font-size: 13px;
  color: var(--portal-muted, #94a3b8);
  text-align: center;
  padding: 24px 12px;
}
.bubble {
  max-width: 92%;
  padding: 10px 12px;
  border-radius: 12px;
  font-size: 13px;
  line-height: 1.55;
  background: #fff;
  border: 1px solid var(--portal-line, #e2e8f0);
}
.bubble.me {
  align-self: flex-end;
  background: color-mix(in srgb, var(--portal-accent, #0b6e75) 14%, #fff);
}
.bubble.bot {
  align-self: flex-start;
  border-left: 3px solid var(--portal-accent, #0b6e75);
}
.body {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
}
.actions {
  margin-top: 8px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}
.link {
  border: none;
  background: none;
  padding: 0;
  font-size: 12px;
  color: var(--portal-accent, #0b6e75);
  cursor: pointer;
}
.link.ok {
  color: #15803d;
}
.composer {
  padding: 10px 12px 12px;
  border-top: 1px solid var(--portal-line, #e2e8f0);
  background: #fff;
}
.composer.guest {
  padding: 8px 12px 12px;
}
.tools {
  display: flex;
  gap: 8px;
  margin-bottom: 8px;
  align-items: center;
}
.send-row {
  display: flex;
  gap: 8px;
  align-items: flex-end;
}
.send-row :deep(.el-textarea) {
  flex: 1;
}
.ai-panel-enter-active,
.ai-panel-leave-active {
  transition: opacity 0.16s ease, transform 0.16s ease;
}
.ai-panel-enter-from,
.ai-panel-leave-to {
  opacity: 0;
  transform: translateY(8px) scale(0.98);
}
@media (max-width: 480px) {
  .ai-float {
    right: 12px;
    bottom: 16px;
  }
  .panel {
    width: calc(100vw - 24px);
    height: min(70vh, 560px);
  }
}
</style>
