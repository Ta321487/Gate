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
            <el-avatar :size="40" :src="c.peerAvatarUrl || undefined" class="av">
              {{ initialOf(c.peerNickname || c.peer) }}
            </el-avatar>
            <div class="meta">
              <div class="name">
                <span class="nick">{{ c.peerNickname || c.peer }}</span>
                <el-badge v-if="c.unread" :value="c.unread" :max="99" />
              </div>
              <div class="preview">{{ c.lastMessage?.body || '—' }}</div>
            </div>
          </li>
        </ul>
        <div v-else class="empty">{{ emptyPeers }}</div>
      </aside>

      <section class="pane chat">
        <div v-if="!peer" class="empty center">{{ emptyChat }}</div>
        <template v-else>
          <div class="chat-hd">
            <div class="peer-who">
              <el-avatar :size="36" :src="peerAvatar || undefined">
                {{ initialOf(peerLabel) }}
              </el-avatar>
              <strong>{{ peerLabel }}</strong>
            </div>
            <span class="muted">约每 4 秒刷新</span>
          </div>
          <div ref="scroller" class="chat-body">
            <div
              v-for="m in messages"
              :key="m.id"
              class="row"
              :class="{ mine: m.fromUsername === me }"
            >
              <el-avatar
                :size="32"
                :src="avatarOf(m) || undefined"
                class="row-av"
              >
                {{ initialOf(m.fromUsername === me ? meNick : peerLabel) }}
              </el-avatar>
              <div class="bubble" :class="{ mine: m.fromUsername === me }">
                <div class="txt">{{ m.body }}</div>
                <div class="tm" :title="m.createdAt || ''">{{ formatRelative(m.createdAt) }}</div>
              </div>
            </div>
          </div>
          <div class="chat-ft">
            <div class="composer">
              <div class="emoji-bar" aria-label="常用表情">
                <button
                  v-for="e in emojiPreset"
                  :key="e"
                  type="button"
                  class="emoji-btn"
                  :title="e"
                  @click="insertEmoji(e)"
                >
                  {{ e }}
                </button>
              </div>
              <el-input
                ref="draftInput"
                v-model="draft"
                type="textarea"
                :rows="2"
                maxlength="500"
                show-word-limit
                placeholder="输入消息，Enter 发送（Shift+Enter 换行）"
                @keydown.enter.exact.prevent="send"
              />
            </div>
            <el-button type="primary" :loading="sending" @click="send">发送</el-button>
          </div>
        </template>
      </section>
    </div>

    <el-dialog v-model="newOpen" :title="newDialogTitle" width="420px">
      <el-select
        v-model="newPeer"
        filterable
        :placeholder="peerPlaceholder"
        style="width: 100%"
        popper-class="dm-peer-popper"
      >
        <el-option
          v-for="p in peerOptions"
          :key="p.username"
          :label="`${p.nickname || p.username}（${p.username}）`"
          :value="p.username"
        >
          <span class="opt-row">
            <el-avatar :size="24" :src="p.avatarUrl || undefined">
              {{ initialOf(p.nickname || p.username) }}
            </el-avatar>
            <span>{{ p.nickname || p.username }}（{{ p.username }}）</span>
          </span>
        </el-option>
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
import { formatRelative } from '../../utils/dates.js'
import { schemaLabels } from '../../utils/domainSchema.js'

/** 常用表情条：毕设沉浸，非独立表情包工程 */
const emojiPreset = [
  '😀', '😁', '😊', '🥰', '😂', '😅', '👍', '🙏',
  '❤️', '🔥', '✨', '🎉', '😢', '😮', '🤔', '👏',
]

const labels = computed(() => schemaLabels())
const merchantDesk = computed(() => {
  const path = typeof window !== 'undefined' ? window.location.pathname || '' : ''
  if (path.startsWith('/admin')) return true
  const role = localStorage.getItem('role') || ''
  const post = (localStorage.getItem('staffPost') || '').trim()
  return role === 'admin' && !!post
})
const pageTitle = computed(() => labels.value.dmPageTitle || '私信')
const pageLead = computed(() => {
  if (merchantDesk.value) {
    return labels.value.dmMerchantPageLead || '回复买家咨询，打开会话后自动刷新新消息。'
  }
  return labels.value.dmPageLead || '与其他用户一对一沟通，打开会话后自动刷新新消息。'
})
const newDialogTitle = computed(() => {
  if (merchantDesk.value) return labels.value.dmMerchantNewTitle || '联系买家'
  return labels.value.dmNewTitle || '新建私信'
})
const peerPlaceholder = computed(() => {
  if (merchantDesk.value) return labels.value.dmMerchantPeerPlaceholder || '选择买家账号'
  return labels.value.dmPeerPlaceholder || '选择对方账号'
})
const emptyPeers = computed(() => {
  if (merchantDesk.value) {
    return labels.value.dmMerchantEmptyPeers
      || '暂无会话，买家发起咨询后会出现在这里；也可点「新建」选买家。'
  }
  return labels.value.dmEmptyPeers || '暂无会话，点「新建」选人开聊。'
})
const emptyChat = computed(() => {
  if (merchantDesk.value) {
    return labels.value.dmMerchantEmptyChat || '选择左侧会话，或新建联系买家。'
  }
  return labels.value.dmEmptyChat || '选择左侧会话，或新建私信。'
})

const me = computed(() => localStorage.getItem('username') || '')
const meNick = computed(
  () => localStorage.getItem('nickname') || localStorage.getItem('username') || '我',
)
const meAvatar = computed(() => localStorage.getItem('avatarUrl') || '')
const conversations = ref([])
const messages = ref([])
const peer = ref('')
const draft = ref('')
const sending = ref(false)
const newOpen = ref(false)
const newPeer = ref('')
const peerOptions = ref([])
const scroller = ref(null)
const draftInput = ref(null)
let pollTimer = null
let lastId = 0

const peerLabel = computed(() => {
  const hit = conversations.value.find((c) => c.peer === peer.value)
  if (hit?.peerNickname) return hit.peerNickname
  const opt = peerOptions.value.find((p) => p.username === peer.value)
  return opt?.nickname || peer.value
})

const peerAvatar = computed(() => {
  const hit = conversations.value.find((c) => c.peer === peer.value)
  if (hit?.peerAvatarUrl) return hit.peerAvatarUrl
  const opt = peerOptions.value.find((p) => p.username === peer.value)
  return opt?.avatarUrl || ''
})

function initialOf(name) {
  const s = String(name || '?').trim()
  return s ? s.slice(0, 1) : '?'
}

function avatarOf(m) {
  if (!m) return ''
  if (m.fromUsername === me.value) return meAvatar.value
  return m.fromAvatarUrl || peerAvatar.value || ''
}

function insertEmoji(e) {
  draft.value = `${draft.value || ''}${e}`
  nextTick(() => {
    const el = draftInput.value?.textarea || draftInput.value?.$el?.querySelector?.('textarea')
    el?.focus?.()
  })
}

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
.hero p { margin: 0; color: var(--portal-muted, #64748b); font-size: 13px; }
.dm-shell {
  display: grid;
  grid-template-columns: 280px 1fr;
  gap: 12px;
  min-height: 480px;
}
.pane {
  border: 1px solid var(--portal-line, #e2e8f0);
  border-radius: var(--portal-radius, 12px);
  background: var(--portal-surface, #fff);
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
.peer-who {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}
.peer-who strong {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.muted { color: var(--portal-muted, #94a3b8); font-size: 12px; }
.conv-list { list-style: none; margin: 0; padding: 0; overflow: auto; flex: 1; }
.conv-list li {
  display: flex;
  gap: 10px;
  align-items: center;
  padding: 12px 14px;
  border-bottom: 1px solid var(--portal-line, #f1f5f9);
  cursor: pointer;
}
.conv-list li:hover, .conv-list li.active {
  background: color-mix(in srgb, var(--portal-bg, #f8fafc) 65%, var(--portal-surface, #fff));
}
.conv-list .av { flex-shrink: 0; }
.conv-list .meta { min-width: 0; flex: 1; }
.conv-list .name {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  font-weight: 600;
  font-size: 14px;
}
.conv-list .nick {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.conv-list .preview {
  margin-top: 4px;
  color: var(--portal-muted, #64748b);
  font-size: 12px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.empty { padding: 24px 14px; color: var(--portal-muted, #94a3b8); font-size: 13px; }
.empty.center { margin: auto; text-align: center; }
.chat-body {
  flex: 1;
  overflow: auto;
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  background: color-mix(in srgb, var(--portal-bg, #f8fafc) 72%, var(--portal-surface, #fff));
}
.row {
  display: flex;
  align-items: flex-end;
  gap: 8px;
  max-width: 88%;
  align-self: flex-start;
}
.row.mine {
  align-self: flex-end;
  flex-direction: row-reverse;
}
.row-av { flex-shrink: 0; }
.bubble {
  min-width: 0;
  background: var(--portal-surface, #fff);
  border: 1px solid var(--portal-line, #e2e8f0);
  border-radius: 12px;
  padding: 8px 12px;
  color: var(--portal-ink, #15202b);
}
.bubble.mine {
  background: color-mix(in srgb, var(--portal-accent, #0b6e75) 14%, var(--portal-surface, #fff));
  border-color: color-mix(in srgb, var(--portal-accent, #0b6e75) 35%, var(--portal-line, #e2e8f0));
}
.bubble .txt { white-space: pre-wrap; word-break: break-word; font-size: 14px; }
.bubble .tm { margin-top: 4px; color: var(--portal-muted, #94a3b8); font-size: 11px; }
.chat-ft {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 10px;
  padding: 12px 14px;
  border-top: 1px solid var(--portal-line, #e2e8f0);
  align-items: end;
}
.composer { display: flex; flex-direction: column; gap: 8px; min-width: 0; }
.emoji-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}
.emoji-btn {
  border: 0;
  background: color-mix(in srgb, var(--portal-bg, #f8fafc) 80%, var(--portal-surface, #fff));
  border-radius: 8px;
  width: 30px;
  height: 30px;
  cursor: pointer;
  font-size: 16px;
  line-height: 1;
  padding: 0;
}
.emoji-btn:hover {
  background: color-mix(in srgb, var(--portal-accent, #0b6e75) 12%, var(--portal-surface, #fff));
}
.opt-row {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}
@media (max-width: 800px) {
  .dm-shell { grid-template-columns: 1fr; }
  .peers { min-height: 180px; }
}
</style>
