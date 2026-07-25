<template>
  <div class="dm-page">
    <section class="hero">
      <h1>{{ pageTitle }}</h1>
      <p>{{ pageLead }}</p>
    </section>

    <div class="dm-shell">
      <aside class="pane peers">
        <div class="pane-hd">
          <strong>会话</strong>
          <el-button link type="primary" size="small" @click="openNew">新建</el-button>
        </div>
        <ul v-if="conversations.length" class="conv-list">
          <li
            v-for="c in conversations"
            :key="c.peer"
            :class="{ active: peer === c.peer }"
            @click="selectPeer(c.peer)"
          >
            <div class="name">
              {{ c.peerNickname || c.peer }}
              <el-badge v-if="c.unread" :value="c.unread" :max="99" />
            </div>
            <div class="preview">{{ c.lastMessage?.body || '—' }}</div>
          </li>
        </ul>
        <div v-else class="empty">暂无会话，点「新建」选人开聊。</div>
      </aside>

      <section class="pane chat">
        <div v-if="!peer" class="empty center">选择左侧会话，或新建私信。</div>
        <template v-else>
          <div class="chat-hd">
            <strong>{{ peerLabel }}</strong>
            <span class="muted">约每 4 秒刷新</span>
          </div>
          <div ref="scroller" class="chat-body">
            <div
              v-for="m in messages"
              :key="m.id"
              class="bubble"
              :class="{ mine: m.fromUsername === me }"
            >
              <div class="txt">{{ m.body }}</div>
              <div class="tm">{{ m.createdAt }}</div>
            </div>
          </div>
          <div class="chat-ft">
            <el-input
              v-model="draft"
              type="textarea"
              :rows="2"
              maxlength="500"
              show-word-limit
              placeholder="输入消息，Enter 发送（Shift+Enter 换行）"
              @keydown.enter.exact.prevent="send"
            />
            <el-button type="primary" :loading="sending" @click="send">发送</el-button>
          </div>
        </template>
      </section>
    </div>

    <el-dialog v-model="newOpen" title="新建私信" width="420px">
      <el-select
        v-model="newPeer"
        filterable
        placeholder="选择对方账号"
        style="width: 100%"
      >
        <el-option
          v-for="p in peerOptions"
          :key="p.username"
          :label="`${p.nickname || p.username}（${p.username}）`"
          :value="p.username"
        />
      </el-select>
      <template #footer>
        <el-button @click="newOpen = false">取消</el-button>
        <el-button type="primary" :disabled="!newPeer" @click="confirmNew">开始聊天</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import http from '../../api/http'
import { schemaLabels } from '../../utils/domainSchema.js'

const labels = computed(() => schemaLabels())
const pageTitle = computed(() => labels.value.dmPageTitle || '私信')
const pageLead = computed(
  () =>
    labels.value.dmPageLead ||
    '与其他用户一对一沟通；打开会话后自动刷新新消息（短轮询，非 WebSocket）。',
)

const me = computed(() => localStorage.getItem('username') || '')
const conversations = ref([])
const messages = ref([])
const peer = ref('')
const draft = ref('')
const sending = ref(false)
const newOpen = ref(false)
const newPeer = ref('')
const peerOptions = ref([])
const scroller = ref(null)
let pollTimer = null
let lastId = 0

const peerLabel = computed(() => {
  const hit = conversations.value.find((c) => c.peer === peer.value)
  if (hit?.peerNickname) return hit.peerNickname
  const opt = peerOptions.value.find((p) => p.username === peer.value)
  return opt?.nickname || peer.value
})

async function loadConversations() {
  const res = await http.get('/api/dm/conversations')
  conversations.value = res.data || []
}

async function loadPeers() {
  const res = await http.get('/api/dm/peers')
  peerOptions.value = res.data || []
}

async function loadMessages({ full = false } = {}) {
  if (!peer.value) return
  const since = full ? 0 : lastId
  const res = await http.get('/api/dm/messages', {
    params: { peer: peer.value, sinceId: since },
  })
  const list = res.data || []
  if (full) {
    messages.value = list
  } else if (list.length) {
    messages.value = [...messages.value, ...list]
  }
  if (messages.value.length) {
    lastId = Math.max(...messages.value.map((m) => Number(m.id) || 0))
  }
  await http.post('/api/dm/read', { peer: peer.value })
  await nextTick()
  if (scroller.value) scroller.value.scrollTop = scroller.value.scrollHeight
}

async function selectPeer(p) {
  peer.value = p
  lastId = 0
  messages.value = []
  await loadMessages({ full: true })
  await loadConversations()
}

async function send() {
  const text = draft.value.trim()
  if (!peer.value || !text || sending.value) return
  sending.value = true
  try {
    await http.post('/api/dm/messages', { toUsername: peer.value, body: text })
    draft.value = ''
    await loadMessages()
    await loadConversations()
  } catch (e) {
    ElMessage.error(e?.response?.data?.message || e?.message || '发送失败')
  } finally {
    sending.value = false
  }
}

async function openNew() {
  await loadPeers()
  newPeer.value = ''
  newOpen.value = true
}

function confirmNew() {
  if (!newPeer.value) return
  newOpen.value = false
  selectPeer(newPeer.value)
}

function startPoll() {
  stopPoll()
  pollTimer = setInterval(async () => {
    if (!peer.value) {
      await loadConversations()
      return
    }
    await loadMessages()
    await loadConversations()
  }, 4000)
}

function stopPoll() {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

watch(peer, () => {
  draft.value = ''
})

onMounted(async () => {
  await loadPeers()
  await loadConversations()
  if (conversations.value.length) {
    await selectPeer(conversations.value[0].peer)
  }
  startPoll()
})

onUnmounted(stopPoll)
</script>

<style scoped>
.hero { margin-bottom: 14px; }
.hero h1 { margin: 0 0 6px; font-size: 22px; }
.hero p { margin: 0; color: #64748b; font-size: 13px; }
.dm-shell {
  display: grid;
  grid-template-columns: 260px 1fr;
  gap: 12px;
  min-height: 480px;
}
.pane {
  border: 1px solid var(--portal-line, #e2e8f0);
  border-radius: var(--portal-radius, 12px);
  background: #fff;
  display: flex;
  flex-direction: column;
  min-height: 480px;
}
.pane-hd, .chat-hd {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 14px;
  border-bottom: 1px solid var(--portal-line, #e2e8f0);
}
.muted { color: #94a3b8; font-size: 12px; }
.conv-list { list-style: none; margin: 0; padding: 0; overflow: auto; flex: 1; }
.conv-list li {
  padding: 12px 14px;
  border-bottom: 1px solid #f1f5f9;
  cursor: pointer;
}
.conv-list li:hover, .conv-list li.active { background: #f8fafc; }
.conv-list .name {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  font-weight: 600;
  font-size: 14px;
}
.conv-list .preview {
  margin-top: 4px;
  color: #64748b;
  font-size: 12px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.empty { padding: 24px 14px; color: #94a3b8; font-size: 13px; }
.empty.center { margin: auto; text-align: center; }
.chat-body {
  flex: 1;
  overflow: auto;
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  background: #f8fafc;
}
.bubble {
  max-width: 75%;
  align-self: flex-start;
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 8px 12px;
}
.bubble.mine {
  align-self: flex-end;
  background: #eff6ff;
  border-color: #bfdbfe;
}
.bubble .txt { white-space: pre-wrap; word-break: break-word; font-size: 14px; }
.bubble .tm { margin-top: 4px; color: #94a3b8; font-size: 11px; }
.chat-ft {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 10px;
  padding: 12px 14px;
  border-top: 1px solid var(--portal-line, #e2e8f0);
  align-items: end;
}
@media (max-width: 800px) {
  .dm-shell { grid-template-columns: 1fr; }
  .peers { min-height: 180px; }
}
</style>
