<template>
  <div>
    <section class="hero">
      <h1>{{ title }}</h1>
      <p>{{ lead }}</p>
    </section>

    <div v-if="tagCloudOn && tagCloud.length" class="tag-cloud">
      <span class="tag-title">{{ labels.tagCloudLabel || '标签' }}</span>
      <span v-for="t in tagCloud" :key="t.id" class="tag">
        {{ t.name }}
        <em>{{ t.useCount }}</em>
      </span>
    </div>

    <div class="list">
      <article v-for="d in list" :key="d.id" class="card item">
        <span class="file-mark" aria-hidden="true">{{ fileTypeMark(d.fileUrl || d.title) }}</span>
        <div class="body">
          <strong>{{ d.title }}</strong>
          <div class="muted">{{ d.author || '—' }} · 权限 {{ levelLabel(d.accessLevel) }}</div>
          <div v-if="d.isbn" class="muted">{{ d.isbn }}</div>
          <div v-if="trialReadOn && d.trialReadNote" class="trial">
            {{ labels.trialReadLabel || '试读说明' }}：{{ d.trialReadNote }}
          </div>
          <div v-if="downloadCountOn && d.downloadCount != null" class="muted">
            已下载 {{ d.downloadCount }} 次
          </div>
          <div v-if="pointsDownloadOn && Number(d.downloadCostPoints || 0) > 0" class="muted">
            {{ labels.downloadCostPointsLabel || '下载所需积分' }}：{{ d.downloadCostPoints }}
          </div>
        </div>
        <div class="ops">
          <el-button v-if="previewOn && d.previewUrl" @click="openPreview(d)">
            {{ labels.previewLabel || '在线预览' }}
          </el-button>
          <el-button type="primary" :loading="busyId === d.id" @click="dl(d)">下载</el-button>
          <el-button v-if="feedbackOn" link type="primary" @click="openFeedback(d)">反馈</el-button>
          <el-button link @click="openDetail(d)">详情</el-button>
        </div>
      </article>
    </div>
    <div v-if="!list.length">
      <EmptyHint title="暂无开放资料" desc="有开放文件时会出现在这里。" mark="档" />
    </div>

    <el-dialog v-model="detailVisible" :title="detail?.title || '资料详情'" width="560px">
      <template v-if="detail">
        <p v-if="trialReadOn && detail.trialReadNote" class="trial">{{ detail.trialReadNote }}</p>
        <div v-if="chapterOn">
          <h4>{{ labels.chapterLabel || '章节目录' }}</h4>
          <ul v-if="(detail.chapters || []).length" class="chapters">
            <li v-for="c in detail.chapters" :key="c.id">
              <a v-if="c.anchor" :href="'#' + c.anchor">{{ c.title }}</a>
              <span v-else>{{ c.title }}</span>
            </li>
          </ul>
          <p v-else class="muted">{{ labels.chapterEmpty || '暂无章节' }}</p>
          <h4>{{ labels.versionLabel || '版本记录' }}</h4>
          <ul v-if="(detail.versions || []).length" class="versions">
            <li v-for="v in detail.versions" :key="v.id">
              {{ v.versionNo }} · {{ v.note || '—' }}
              <span class="muted">{{ v.createdAt }}</span>
            </li>
          </ul>
          <p v-else class="muted">{{ labels.versionEmpty || '暂无版本记录' }}</p>
        </div>
        <div v-if="tagCloudOn && (detail.tags || []).length" class="tag-row">
          <span v-for="t in detail.tags" :key="t.id" class="tag">{{ t.name }}</span>
        </div>
      </template>
    </el-dialog>

    <el-dialog v-model="previewVisible" :title="labels.previewLabel || '在线预览'" width="720px" destroy-on-close>
      <div class="preview-wrap">
        <div v-if="watermarkOn && previewItem?.watermarkOn" class="watermark" aria-hidden="true">
          {{ watermarkText }}
        </div>
        <p class="muted">{{ labels.previewHint || '打开链接预览，本系统不负责转码。' }}</p>
        <iframe v-if="previewUrl" class="preview-frame" :src="previewUrl" title="preview" />
        <p v-else class="muted">{{ labels.previewEmpty || '暂无预览地址' }}</p>
      </div>
      <template #footer>
        <el-button v-if="previewUrl" type="primary" @click="windowOpen(previewUrl)">新窗口打开</el-button>
        <el-button @click="previewVisible = false">关闭</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="fbVisible" :title="fbKind === 'infringement' ? (labels.infringementLabel || '侵权投诉') : (labels.correctionLabel || '纠错反馈')" width="480px">
      <el-form label-width="72px">
        <el-form-item label="类型">
          <el-radio-group v-model="fbKind">
            <el-radio value="correction">{{ labels.correctionLabel || '纠错反馈' }}</el-radio>
            <el-radio value="infringement">{{ labels.infringementLabel || '侵权投诉' }}</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="内容">
          <el-input v-model="fbBody" type="textarea" :rows="4" maxlength="1000" show-word-limit />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="fbVisible = false">取消</el-button>
        <el-button type="primary" :loading="fbBusy" @click="submitFeedback">
          {{ fbKind === 'infringement' ? (labels.infringementSubmit || '提交投诉') : (labels.correctionSubmit || '提交纠错') }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import http from '../api/http'
import EmptyHint from '../components/EmptyHint.vue'
import { getSchema } from '../utils/domainSchema'
import { fileTypeMark } from '../utils/statusTone.js'

const list = ref([])
const tagCloud = ref([])
const busyId = ref(null)
const detailVisible = ref(false)
const detail = ref(null)
const previewVisible = ref(false)
const previewItem = ref(null)
const previewUrl = ref('')
const fbVisible = ref(false)
const fbItem = ref(null)
const fbKind = ref('correction')
const fbBody = ref('')
const fbBusy = ref(false)

const schema = computed(() => getSchema() || {})
const labels = computed(() => schema.value.labels || {})
const thicken = computed(() => schema.value.contentThicken || {})
const title = computed(() => labels.value.docBrowseTitle || '文库浏览')
const lead = computed(
  () => labels.value.docBrowseLead || '浏览开放资料，按权限下载；下载将记入台账。',
)
const previewOn = computed(() => !!thicken.value.docPreview)
const trialReadOn = computed(() => !!thicken.value.trialRead)
const watermarkOn = computed(() => !!thicken.value.watermark)
const chapterOn = computed(() => !!thicken.value.docChapter)
const tagCloudOn = computed(() => !!thicken.value.docTagCloud)
const feedbackOn = computed(() => !!thicken.value.docFeedback)
const downloadCountOn = computed(() => !!thicken.value.hotByDownload || !!thicken.value.downloadLog)
const pointsDownloadOn = computed(() => !!thicken.value.docPointsDownload || !!thicken.value.docPaidDownload)

const watermarkText = computed(() => {
  try {
    const u = JSON.parse(localStorage.getItem('user') || '{}')
    return u.username || u.name || '预览水印'
  } catch {
    return '预览水印'
  }
})

function levelLabel(lv) {
  if (lv === 'staff') return '管理人员'
  if (lv === 'public') return '开放'
  return '登录可下'
}

function windowOpen(url) {
  window.open(url, '_blank')
}

async function load() {
  const res = await http.get('/api/doclib/items')
  list.value = res.data?.data || res.data || []
  if (tagCloudOn.value) {
    try {
      const tr = await http.get('/api/doclib/tags/cloud', { params: { limit: 30 } })
      tagCloud.value = tr.data?.data || tr.data || []
    } catch {
      tagCloud.value = []
    }
  }
}

async function openDetail(d) {
  try {
    const res = await http.get(`/api/doclib/items/${d.id}`)
    detail.value = res.data?.data || res.data || d
    detailVisible.value = true
  } catch (e) {
    ElMessage.error(e?.response?.data?.message || e.message || '加载失败')
  }
}

function openPreview(d) {
  if (!d.previewUrl) {
    ElMessage.info(labels.value.previewEmpty || '暂无预览地址')
    return
  }
  previewItem.value = d
  previewUrl.value = d.previewUrl
  previewVisible.value = true
}

async function dl(d) {
  busyId.value = d.id
  try {
    const res = await http.post(`/api/doclib/items/${d.id}/download`)
    const data = res.data?.data || res.data || {}
    const cost = Number(d.downloadCostPoints || 0)
    if (pointsDownloadOn.value && cost > 0) {
      ElMessage.success(labels.value.downloadPointsDebited || '已扣积分并记入台账')
    } else {
      ElMessage.success('已记入台账')
    }
    if (data.url) window.open(data.url, '_blank')
  } catch (e) {
    const msg = e?.response?.data?.message || e.message || '下载失败'
    if (msg.includes('积分')) {
      ElMessage.error(labels.value.downloadPointsShortage || msg)
    } else if (msg.includes('上限') || msg.includes('次数')) {
      ElMessage.error(labels.value.downloadQuotaExceeded || msg)
    } else {
      ElMessage.error(msg)
    }
  } finally {
    busyId.value = null
  }
}

function openFeedback(d) {
  fbItem.value = d
  fbKind.value = 'correction'
  fbBody.value = ''
  fbVisible.value = true
}

async function submitFeedback() {
  if (!fbItem.value) return
  fbBusy.value = true
  try {
    await http.post(`/api/doclib/items/${fbItem.value.id}/feedback`, {
      kind: fbKind.value,
      body: fbBody.value,
    })
    ElMessage.success(
      fbKind.value === 'infringement'
        ? labels.value.infringementDone || '投诉已登记，管理员将处理'
        : labels.value.correctionDone || '已收到纠错，感谢反馈',
    )
    fbVisible.value = false
  } catch (e) {
    ElMessage.error(e?.response?.data?.message || e.message || '提交失败')
  } finally {
    fbBusy.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.hero { margin-bottom: 1rem; }
.list { display: grid; gap: 0.75rem; }
.item { padding: 1rem; display: flex; gap: 1rem; align-items: center; justify-content: space-between; flex-wrap: wrap; }
.body { flex: 1; min-width: 180px; }
.ops { display: flex; flex-wrap: wrap; gap: 0.35rem; align-items: center; }
.muted { color: var(--el-text-color-secondary); font-size: 0.9rem; margin-top: 0.25rem; }
.trial { margin-top: 0.35rem; font-size: 0.9rem; color: var(--el-color-warning); }
.tag-cloud { display: flex; flex-wrap: wrap; gap: 0.4rem; align-items: center; margin-bottom: 1rem; }
.tag-title { font-size: 0.9rem; color: var(--el-text-color-secondary); margin-right: 0.25rem; }
.tag {
  border: 1px solid var(--el-border-color);
  background: transparent;
  border-radius: 4px;
  padding: 0.15rem 0.5rem;
  font-size: 0.85rem;
}
.tag em { font-style: normal; opacity: 0.65; margin-left: 0.25rem; }
.tag-row { display: flex; flex-wrap: wrap; gap: 0.35rem; margin-top: 0.75rem; }
.chapters, .versions { padding-left: 1.1rem; margin: 0.35rem 0 0.75rem; }
.preview-wrap { position: relative; min-height: 200px; }
.preview-frame { width: 100%; height: 420px; border: 1px solid var(--el-border-color); }
.watermark {
  pointer-events: none;
  position: absolute;
  inset: 0;
  display: grid;
  place-items: center;
  font-size: 2rem;
  color: rgba(0, 0, 0, 0.12);
  transform: rotate(-18deg);
  z-index: 1;
}
.file-mark {
  display: inline-grid;
  place-items: center;
  width: 36px;
  height: 36px;
  border-radius: 8px;
  font-size: 12px;
  font-weight: 700;
  color: var(--portal-accent, #0b6e75);
  background: color-mix(in srgb, var(--portal-accent, #0b6e75) 12%, transparent);
}
</style>
