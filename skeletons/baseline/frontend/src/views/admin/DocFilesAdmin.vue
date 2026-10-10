<template>
  <div>
    <section class="hero">
      <h1>附件权限</h1>
      <p class="muted">配置资料附件、预览与下载规则。条目标题在「资料条目」维护。</p>
    </section>
    <el-table :data="list" stripe>
      <el-table-column prop="title" label="标题" min-width="160" />
      <el-table-column prop="accessLevel" label="权限" width="100" />
      <el-table-column prop="fileUrl" label="附件 URL" min-width="160" />
      <el-table-column v-if="previewOn" prop="previewUrl" label="预览地址" min-width="140" />
      <el-table-column label="操作" width="100">
        <template #default="{ row }">
          <el-button link type="primary" @click="edit(row)">编辑</el-button>
        </template>
      </el-table-column>
    </el-table>
    <el-dialog v-model="visible" title="附件与权限" width="520px">
      <el-form label-width="110px">
        <el-form-item label="附件 URL">
          <el-input v-model="draft.fileUrl" placeholder="/uploads/..." />
        </el-form-item>
        <el-form-item label="权限">
          <el-select v-model="draft.accessLevel" style="width: 100%">
            <el-option label="开放(public)" value="public" />
            <el-option label="登录可下(login)" value="login" />
            <el-option label="管理人员(staff)" value="staff" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="previewOn" :label="labels.previewLabel || '在线预览'">
          <el-input v-model="draft.previewUrl" :placeholder="labels.previewHint || '预览链接'" />
        </el-form-item>
        <el-form-item v-if="trialReadOn" :label="labels.trialReadLabel || '试读说明'">
          <el-input v-model="draft.trialReadNote" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item v-if="rolesOn" :label="labels.downloadRolesLabel || '可下载角色'">
          <el-input
            v-model="draft.downloadRoles"
            :placeholder="labels.downloadRolesHint || '多个角色用逗号分隔，留空表示登录即可'"
          />
        </el-form-item>
        <el-form-item v-if="watermarkOn" :label="labels.watermarkLabel || '预览水印'">
          <el-switch v-model="draft.watermarkOn" />
          <span class="hint">{{ labels.watermarkHint || '' }}</span>
        </el-form-item>
        <el-form-item v-if="auditOn" :label="labels.downloadAuditLabel || '下载需审核'">
          <el-switch v-model="draft.needsDownloadAudit" />
        </el-form-item>
        <el-form-item v-if="quotaOn" :label="labels.dailyDownloadLimitLabel || '每日下载上限'">
          <el-input-number v-model="draft.dailyDownloadLimit" :min="0" :max="9999" />
        </el-form-item>
        <el-form-item v-if="pointsDownloadOn" :label="labels.downloadCostPointsLabel || '下载所需积分'">
          <el-input-number v-model="draft.downloadCostPoints" :min="0" :max="999999" />
          <span class="hint">{{ labels.downloadCostHint || '' }}</span>
        </el-form-item>
        <el-form-item v-if="tagCloudOn" :label="labels.tagCloudLabel || '标签'">
          <el-input v-model="draft.tagsText" placeholder="多个标签用逗号分隔" />
        </el-form-item>
      </el-form>

      <template v-if="chapterOn && draft.id">
        <h4>{{ labels.chapterLabel || '章节目录' }}</h4>
        <div class="sub-row" v-for="c in chapters" :key="c.id">
          <span>{{ c.sortOrd }}. {{ c.title }}</span>
          <el-button link type="danger" @click="removeChapter(c)">删</el-button>
        </div>
        <el-form inline class="sub-form">
          <el-form-item label="标题">
            <el-input v-model="chapterDraft.title" />
          </el-form-item>
          <el-form-item label="锚点">
            <el-input v-model="chapterDraft.anchor" />
          </el-form-item>
          <el-form-item label="排序">
            <el-input-number v-model="chapterDraft.sortOrd" :min="0" />
          </el-form-item>
          <el-button type="primary" @click="addChapter">添加章节</el-button>
        </el-form>

        <h4>{{ labels.versionLabel || '版本记录' }}</h4>
        <div class="sub-row" v-for="v in versions" :key="v.id">
          <span>{{ v.versionNo }} · {{ v.note || '—' }}</span>
        </div>
        <el-form inline class="sub-form">
          <el-form-item label="版本号">
            <el-input v-model="versionDraft.versionNo" />
          </el-form-item>
          <el-form-item label="说明">
            <el-input v-model="versionDraft.note" />
          </el-form-item>
          <el-button type="primary" @click="addVersion">登记版本</el-button>
        </el-form>
      </template>

      <template #footer>
        <el-button @click="visible = false">取消</el-button>
        <el-button type="primary" @click="save">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import http from '../../api/http'
import { getSchema } from '../../utils/domainSchema'

const list = ref([])
const visible = ref(false)
const chapters = ref([])
const versions = ref([])
const draft = reactive({
  id: null,
  fileUrl: '',
  accessLevel: 'login',
  previewUrl: '',
  trialReadNote: '',
  downloadRoles: '',
  watermarkOn: false,
  needsDownloadAudit: false,
  dailyDownloadLimit: 0,
  downloadCostPoints: 0,
  tagsText: '',
})
const chapterDraft = reactive({ title: '', anchor: '', sortOrd: 0 })
const versionDraft = reactive({ versionNo: '', note: '' })

const schema = computed(() => getSchema() || {})
const labels = computed(() => schema.value.labels || {})
const thicken = computed(() => schema.value.contentThicken || {})
const previewOn = computed(() => !!thicken.value.docPreview)
const trialReadOn = computed(() => !!thicken.value.trialRead)
const rolesOn = computed(() => !!thicken.value.downloadRoles)
const watermarkOn = computed(() => !!thicken.value.watermark)
const auditOn = computed(() => !!thicken.value.downloadAudit)
const quotaOn = computed(() => !!thicken.value.downloadQuota)
const chapterOn = computed(() => !!thicken.value.docChapter)
const tagCloudOn = computed(() => !!thicken.value.docTagCloud)
const pointsDownloadOn = computed(() => !!thicken.value.docPointsDownload || !!thicken.value.docPaidDownload)

async function load() {
  const res = await http.get('/api/doclib/items')
  list.value = res.data?.data || res.data || []
}

async function edit(row) {
  draft.id = row.id
  draft.fileUrl = row.fileUrl || ''
  draft.accessLevel = row.accessLevel || 'login'
  draft.previewUrl = row.previewUrl || ''
  draft.trialReadNote = row.trialReadNote || ''
  draft.downloadRoles = row.downloadRoles || ''
  draft.watermarkOn = !!row.watermarkOn
  draft.needsDownloadAudit = !!row.needsDownloadAudit
  draft.dailyDownloadLimit = Number(row.dailyDownloadLimit || 0)
  draft.downloadCostPoints = Number(row.downloadCostPoints || 0)
  draft.tagsText = ''
  chapters.value = []
  versions.value = []
  visible.value = true
  try {
    const res = await http.get(`/api/doclib/items/${row.id}`)
    const full = res.data?.data || res.data || {}
    draft.previewUrl = full.previewUrl || draft.previewUrl
    draft.trialReadNote = full.trialReadNote || draft.trialReadNote
    draft.downloadRoles = full.downloadRoles || draft.downloadRoles
    draft.watermarkOn = !!full.watermarkOn
    draft.needsDownloadAudit = !!full.needsDownloadAudit
    draft.dailyDownloadLimit = Number(full.dailyDownloadLimit || 0)
    draft.downloadCostPoints = Number(full.downloadCostPoints || 0)
    draft.tagsText = (full.tags || []).map((t) => t.name).join(',')
    chapters.value = full.chapters || []
    versions.value = full.versions || []
  } catch {
    /* 列表字段已够用 */
  }
}

async function save() {
  const body = {
    fileUrl: draft.fileUrl,
    accessLevel: draft.accessLevel,
  }
  if (previewOn.value) body.previewUrl = draft.previewUrl
  if (trialReadOn.value) body.trialReadNote = draft.trialReadNote
  if (rolesOn.value) body.downloadRoles = draft.downloadRoles
  if (watermarkOn.value) body.watermarkOn = draft.watermarkOn
  if (auditOn.value) body.needsDownloadAudit = draft.needsDownloadAudit
  if (quotaOn.value) body.dailyDownloadLimit = draft.dailyDownloadLimit
  if (pointsDownloadOn.value) body.downloadCostPoints = draft.downloadCostPoints
  if (tagCloudOn.value) body.tags = draft.tagsText
  await http.put(`/api/doclib/admin/items/${draft.id}`, body)
  ElMessage.success('已保存')
  visible.value = false
  await load()
}

async function addChapter() {
  if (!draft.id || !chapterDraft.title.trim()) return
  await http.post(`/api/doclib/admin/items/${draft.id}/chapters`, {
    title: chapterDraft.title,
    anchor: chapterDraft.anchor,
    sortOrd: chapterDraft.sortOrd,
  })
  chapterDraft.title = ''
  chapterDraft.anchor = ''
  chapterDraft.sortOrd = 0
  const res = await http.get(`/api/doclib/items/${draft.id}/chapters`)
  chapters.value = res.data?.data || res.data || []
  ElMessage.success('已添加章节')
}

async function removeChapter(c) {
  await http.delete(`/api/doclib/admin/items/${draft.id}/chapters/${c.id}`)
  chapters.value = chapters.value.filter((x) => x.id !== c.id)
}

async function addVersion() {
  if (!draft.id || !versionDraft.versionNo.trim()) return
  await http.post(`/api/doclib/admin/items/${draft.id}/versions`, {
    versionNo: versionDraft.versionNo,
    note: versionDraft.note,
  })
  versionDraft.versionNo = ''
  versionDraft.note = ''
  const res = await http.get(`/api/doclib/items/${draft.id}/versions`)
  versions.value = res.data?.data || res.data || []
  ElMessage.success('已登记版本')
}

onMounted(load)
</script>

<style scoped>
.hero { margin-bottom: 1rem; }
.muted { color: var(--el-text-color-secondary); }
.hint { margin-left: 0.5rem; font-size: 0.85rem; color: var(--el-text-color-secondary); }
.sub-row { display: flex; justify-content: space-between; padding: 0.25rem 0; }
.sub-form { margin: 0.5rem 0 1rem; }
h4 { margin: 0.75rem 0 0.35rem; font-size: 0.95rem; }
</style>
