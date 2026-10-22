import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import http from '../../api/http'
import ArchiveFieldControl from '../../components/ArchiveFieldControl.vue'
import SchemaLabelHints from '../../components/SchemaLabelHints.vue'
import { ARCHIVE_ADMIN_HINT_KEYS } from '../../utils/labelHintMount.js'
import { archiveCopy, formatArchiveScalar, getSchema, hasCap, isGalleryEnabled, softDeleteCopy } from '../../utils/domainSchema.js'
import { datePickerProps, dateTimePickerProps } from '../../utils/dateTimeField.js'
import { archiveFieldWidget } from '../../utils/archiveFieldWidget.js'
import { sanitizeHtml } from '../../utils/richHtml.js'
import { saveBlob } from '../../utils/csvDownload.js'
import { isValidIsbn } from '../../utils/isbn.js'
import { useUnsavedGuard } from '../../utils/unsavedGuard.js'

const route = useRoute()
const archive = archiveCopy()
const advancedFilterOn = computed(() => !!getSchema()?.listCrosscut?.advancedFilter)
const exportColumnsOn = computed(() => !!getSchema()?.listCrosscut?.exportColumns)
const recycleOn = computed(() => !!archive.softDelete)
const batchDeleteOn = computed(() => !!getSchema()?.listCrosscut?.batchDelete)
const softCopyBase = softDeleteCopy()
const marketplace = computed(() => !!getSchema()?.shopMarketplace)
const publishReview = computed(() => !!archive.publishReview)
const canReviewPublish = computed(() => marketplace.value || publishReview.value)
const softCopy = computed(() => {
  if (!marketplace.value) return softCopyBase
  return { ...softCopyBase, verb: '强制下架', off: '已强制下架', include: '含下架' }
})
/** 列表已有「上架」列时不再并列 softDelete「状态」，避免两套真相 */
const showShelfCol = computed(() => marketplace.value || publishReview.value)
const shelfFormLabel = computed(() => {
  if (marketplace.value) return '是否在售'
  return String(softCopy.value.verb || '').includes('下架') ? '上架状态' : '启用状态'
})
const shelfSwitchOn = computed(() => (marketplace.value ? '在售' : softCopy.value.on))
const shelfSwitchOff = computed(() => (marketplace.value ? '已下架' : softCopy.value.off))
const stockWarnBelow = computed(() => {
  const n = Number(getSchema()?.stockWarnBelow)
  return Number.isFinite(n) && n > 0 ? n : 10
})
const archiveAdminHintKeys = ARCHIVE_ADMIN_HINT_KEYS
const adminLabels = computed(() => getSchema()?.labels || {})
const thicken = computed(() => getSchema()?.tradeThicken || {})
const contentThicken = computed(() => getSchema()?.contentThicken || {})
const interactThicken = computed(() => getSchema()?.interactThicken || {})
const datingRejectReasonOn = computed(() => !!interactThicken.value.datingRejectReason)
const datingAlbumAuditOn = computed(() => !!interactThicken.value.datingAlbumAudit)
// 拼车扩展：校区字典 / 途经点 / 拼车说明 / 同行偏好 / 行李 / 出发提醒 ——
const carpoolCampusDictOn = computed(() => !!interactThicken.value.carpoolCampusDict)
const carpoolViaPointsOn = computed(() => !!interactThicken.value.carpoolViaPoints)
const carpoolShareNoteOn = computed(() => !!interactThicken.value.carpoolShareNote)
const carpoolPrefNoteOn = computed(() => !!interactThicken.value.carpoolPrefNote)
const carpoolLuggageOn = computed(() => !!interactThicken.value.carpoolLuggage)
const carpoolDepartRemindOn = computed(() => !!interactThicken.value.carpoolDepartRemind)
const carpoolCampusStartLabel = computed(
  () => adminLabels.value.carpoolCampusStartLabel || '出发校区',
)
const carpoolCampusEndLabel = computed(
  () => adminLabels.value.carpoolCampusEndLabel || '到达校区',
)
const carpoolCampusPlaceholder = computed(
  () => adminLabels.value.carpoolCampusPlaceholder || '选择校区',
)
const carpoolCampusDictHint = computed(() => adminLabels.value.carpoolCampusDictHint || '')
const carpoolViaPointsLabel = computed(() => adminLabels.value.viaPointsLabel || '途经点')
const carpoolViaPointsPlaceholder = computed(
  () => adminLabels.value.viaPointsPlaceholder || '多个途经点用逗号或换行分隔',
)
const carpoolViaPointsHint = computed(() => adminLabels.value.viaPointsHint || '')
const carpoolShareNoteLabel = computed(() => adminLabels.value.shareNoteLabel || '拼车说明')
const carpoolShareNotePlaceholder = computed(
  () => adminLabels.value.shareNotePlaceholder || '',
)
const carpoolShareNoteHint = computed(() => adminLabels.value.shareNoteHint || '')
const carpoolPrefNoteLabel = computed(() => adminLabels.value.prefNoteLabel || '同行偏好')
const carpoolPrefNotePlaceholder = computed(
  () => adminLabels.value.prefNotePlaceholder || '',
)
const carpoolPrefNoteHint = computed(() => adminLabels.value.prefNoteHint || '')
const carpoolLuggageCountLabel = computed(
  () => adminLabels.value.luggageCountLabel || '行李件数',
)
const carpoolLuggageCountHint = computed(() => adminLabels.value.luggageCountHint || '')
const carpoolDepartRemindLeadLabel = computed(
  () => adminLabels.value.carpoolDepartRemindLeadLabel || '出发前提醒',
)
const carpoolDepartRemindHint = computed(
  () => adminLabels.value.carpoolDepartRemindHint || '',
)
const carpoolDepartRemindTitle = computed(
  () => adminLabels.value.carpoolDepartRemindTitle || '出发提醒',
)
const carpoolDepartRemindBody = computed(
  () => adminLabels.value.carpoolDepartRemindBody || '',
)
const carpoolDepartRemindNoneLabel = computed(
  () => adminLabels.value.carpoolDepartRemindNoneLabel || '未设置出发提醒',
)
const carpoolCampusOptions = computed(() => {
  const set = new Set()
  const seeded = String(adminLabels.value.carpoolCampusOptions || '')
    .split(/[,，]/)
    .map((s) => s.trim())
    .filter(Boolean)
  for (const c of seeded) set.add(c)
  for (const r of list.value || []) {
    const s = String(r?.startCampus ?? '').trim()
    const e = String(r?.endCampus ?? '').trim()
    if (s) set.add(s)
    if (e) set.add(e)
  }
  return Array.from(set)
})
const labels = adminLabels
const albumAuditApproveAction = computed(
  () => adminLabels.value.albumAuditApproveAction || '通过相册',
)
const albumAuditRejectAction = computed(
  () => adminLabels.value.albumAuditRejectAction || '驳回相册',
)
const viewCountOn = computed(() => !!contentThicken.value.viewCount)
const viewCountLabel = computed(() => adminLabels.value.viewCountLabel || '阅读数')
const downloadCountOn = computed(() => !!contentThicken.value.hotByDownload)
const downloadCountLabel = computed(() => adminLabels.value.downloadCountLabel || '下载次数')
const hotRankOn = computed(() => !!contentThicken.value.hotRank)
const hotRankPageTitle = computed(() => adminLabels.value.hotRankPageTitle || '热门排行')
const hotRankPageLead = computed(() => adminLabels.value.hotRankPageLead || '按阅读次数从高到低排列。')
const hotRankToggleLabel = computed(() => adminLabels.value.hotRankToggleLabel || '看热门')
const hotRankBackLabel = computed(() => adminLabels.value.hotRankBackLabel || '全部')
const forumOpsOn = computed(
  () => !!(contentThicken.value.pinTop || contentThicken.value.essence || contentThicken.value.locked),
)
const pinTopLabel = computed(() => adminLabels.value.pinTopLabel || '置顶')
const essenceLabel = computed(() => adminLabels.value.essenceLabel || '精华')
const essencePointsRewardLabel = computed(
  () => adminLabels.value.essencePointsRewardLabel || '精华奖励积分',
)
const lockedLabel = computed(() => adminLabels.value.lockedLabel || '锁定')
const publishApproveNotifyTitle = computed(
  () => adminLabels.value.publishApproveNotifyTitle || '投稿已通过',
)
const scheduledPublishOn = computed(() => !!contentThicken.value.scheduledPublish)
const scheduledUnpublishOn = computed(() => !!contentThicken.value.scheduledUnpublish)
const publishAtLabel = computed(() => adminLabels.value.publishAtLabel || '定时发布')
const publishAtHint = computed(() => adminLabels.value.publishAtHint || '')
const unpublishAtLabel = computed(() => adminLabels.value.unpublishAtLabel || '定时撤回')
const unpublishAtHint = computed(() => adminLabels.value.unpublishAtHint || '')
const offShelfReasonOn = computed(() => !!contentThicken.value.offShelfReason)
const offShelfReasonLabel = computed(() => adminLabels.value.offShelfReasonLabel || '下架原因')
const offShelfReasonHint = computed(() => adminLabels.value.offShelfReasonHint || '')
const shareCodeOn = computed(() => !!contentThicken.value.shareCode)
const shareCodeLabel = computed(() => adminLabels.value.shareCodeLabel || '分享码')
const shareCodeHint = computed(() => adminLabels.value.shareCodeHint || '')
const episodeListOn = computed(() => !!contentThicken.value.episodeList)
const episodeAdminTitle = computed(() => adminLabels.value.episodeAdminTitle || '分集维护')
const episodeAddLabel = computed(() => adminLabels.value.episodeAddLabel || '新增分集')
const episodeUpdateNotifyHint = computed(() => adminLabels.value.episodeUpdateNotifyHint || '')
const episodeRows = ref([])
async function loadEpisodes() {
  if (!episodeListOn.value || !form.id) {
    episodeRows.value = []
    return
  }
  try {
    const res = await http.get(`/api/media-episodes/by-item/${form.id}`)
    episodeRows.value = res.data || res || []
  } catch {
    episodeRows.value = []
  }
}
async function openEpisodeEdit(row) {
  const title = row?.title || ''
  const { value } = await ElMessageBox.prompt('分集标题', row ? '编辑分集' : episodeAddLabel.value, {
    inputValue: title,
    confirmButtonText: '保存',
    cancelButtonText: '取消',
  })
  const t = (value || '').trim()
  if (!t) return
  let sortOrd = Number(row?.sortOrd) || episodeRows.value.length
  if (!row) {
    try {
      const { value: s } = await ElMessageBox.prompt('排序号', '分集排序', {
        inputValue: String(sortOrd),
        inputPattern: /^\d+$/,
        confirmButtonText: '下一步',
      })
      sortOrd = Number(s) || 0
    } catch { /* cancel sort → keep default */ }
  }
  await http.post('/api/media-episodes/admin', {
    id: row?.id || null,
    itemId: form.id,
    title: t,
    sortOrd,
    mediaUrl: row?.mediaUrl || '',
    notify: !row,
  })
  if (!row && episodeUpdateNotifyHint.value) {
    /* 新建默认通知；文案仅提示用 */
  }
  ElMessage.success('已保存分集')
  loadEpisodes()
}
async function removeEpisode(row) {
  await ElMessageBox.confirm(`删除分集「${row.title}」？`, '确认')
  await http.delete(`/api/media-episodes/admin/${row.id}`)
  ElMessage.success('已删除')
  loadEpisodes()
}
const hotMode = ref(false)
const seatAttrsOn = computed(() => !!thicken.value.seatAttrs)
const seatAttrEditLabel = computed(() => adminLabels.value.seatAttrEditLabel || '座位属性')
const seatAttrCoupleLabel = computed(() => adminLabels.value.seatAttrCoupleLabel || '情侣座')
const seatAttrAccessibleLabel = computed(() => adminLabels.value.seatAttrAccessibleLabel || '无障碍座')
const cinemaSnackOn = computed(() => !!thicken.value.cinemaSnack)
const cinemaSnackLabel = computed(() => adminLabels.value.cinemaSnackLabel || '卖品加购')
const cinemaSnackHint = computed(() => adminLabels.value.cinemaSnackHint || '')
const cinemaSnackSaveLabel = computed(() => adminLabels.value.cinemaSnackSaveLabel || '保存卖品')
const stallScoreSortOn = computed(() => !!thicken.value.stallScoreSort)
const stallScoreLabel = computed(() => adminLabels.value.stallScoreLabel || '档口评分')
const stallScoreHint = computed(() => adminLabels.value.stallScoreHint || '')
const seatAttrVisible = ref(false)
const seatAttrSaving = ref(false)
const seatAttrShowId = ref(0)
const seatAttrCols = ref(8)
const seatAttrSeats = ref([])
const snackVisible = ref(false)
const snackRows = ref([])
const tagColorOn = computed(() => !!adminLabels.value.tagColorHint)
const lastImportError = ref('')
const importErrors = ref([])
function tagColor(name) {
  const s = String(name || '')
  let h = 0
  for (let i = 0; i < s.length; i += 1) h = (h * 31 + s.charCodeAt(i)) >>> 0
  return `hsl(${h % 360} 55% 48%)`
}
const isSuper = computed(() => localStorage.getItem('superAdmin') === 'true')
function isLowStock(row) {
  if (!marketplace.value || !row || stockAsToggle.value) return false
  return Number(row.stock) < stockWarnBelow.value
}
function isPendingReview(row) {
  return String(row?.status || '') === 'pending_review'
}
function shelfLabel(row) {
  const st = String(row?.status || '')
  if (st === 'pending_review') return '待审核'
  if (st === 'rejected') return '已驳回'
  if (st === 'sold_out') return adminLabels.value.showSoldOutLabel || '已售罄'
  if (st === 'unavailable' || row?.deleted) return '已下架'
  return '已上架'
}
function shelfTagType(row) {
  const st = String(row?.status || '')
  if (st === 'pending_review') return 'warning'
  if (st === 'rejected') return 'danger'
  if (st === 'unavailable' || row?.deleted) return 'info'
  return 'success'
}
const galleryOn = computed(() => isGalleryEnabled())
const galleryLabel = computed(() => getSchema()?.labels?.galleryLabel || '图集')
const roomEquipOn = computed(() => hasCap('room_equipment'))
const equipSectionTitle = computed(
  () => getSchema()?.labels?.roomEquipmentSectionTitle || '配套设备',
)
const equipOptions = ref([])
const label = computed(() => archive.label || '对象')
const fields = computed(() => archive.fields || [])
/** 内部备注标签（用户端不可见，管理端维护） */
const adminNoteLabel = computed(() => getSchema()?.labels?.adminNoteLabel || '内部备注')
const adminNoteHint = computed(() => getSchema()?.labels?.adminNoteHint || '')
void adminNoteLabel
void adminNoteHint
const checkinCodeLabel = computed(() => getSchema()?.labels?.checkinCodeLabel || '报到口令')
const checkinCodeAdminHint = computed(() => getSchema()?.labels?.checkinCodeAdminHint || '')
const hospitalStopOn = computed(
  () => !!(getSchema()?.reserveThicken?.hospitalStopNotify || getSchema()?.labels?.hospitalStopNotifyTitle),
)
const hospitalStopNotifyTitle = computed(() => getSchema()?.labels?.hospitalStopNotifyTitle || '科室停诊通知')
const hospitalStopNotifyBody = computed(() => getSchema()?.labels?.hospitalStopNotifyBody || '')
void hospitalStopNotifyBody
const hospitalStopCalendarHint = computed(() => getSchema()?.labels?.hospitalStopCalendarHint || '')
void hospitalStopCalendarHint
const deptIntroLabel = computed(() => getSchema()?.labels?.deptIntroLabel || '科室介绍')
const deptIntroHint = computed(() => getSchema()?.labels?.deptIntroHint || '')
void deptIntroLabel
void deptIntroHint
const queueEstimateLabel = computed(() => getSchema()?.labels?.queueEstimateLabel || '排队预估')
void queueEstimateLabel
const slotKindLabel = computed(() => getSchema()?.labels?.slotKindLabel || '号源类型')
const slotKindClinic = computed(() => getSchema()?.labels?.slotKindClinic || '门诊')
const slotKindLab = computed(() => getSchema()?.labels?.slotKindLab || '检验检查')
const slotKindHint = computed(() => getSchema()?.labels?.slotKindHint || '')
void slotKindLabel
void slotKindClinic
void slotKindLab
void slotKindHint
const patientProfileMenuLabel = computed(() => getSchema()?.labels?.patientProfileMenuLabel || '就诊人')
void patientProfileMenuLabel
const passHintLabel = computed(() => getSchema()?.labels?.passHintLabel || '通行证提示')
const passHintAdminHint = computed(() => getSchema()?.labels?.passHintAdminHint || '')
const parkingCarpassHint = computed(() => getSchema()?.labels?.parkingCarpassHint || '')
void passHintLabel
void passHintAdminHint
void parkingCarpassHint
const parkingPassMenuLabel = computed(() => getSchema()?.labels?.parkingPassMenuLabel || '停车次卡')
void parkingPassMenuLabel
const CORE_FIELD_KEYS = new Set([
  'title', 'author', 'isbn', 'category', 'stock',
  'mutexCode', 'checkinCode', 'startAt', 'endAt', 'applyDeadlineAt',
])
const extraFields = computed(() => fields.value.filter((f) => f?.key && !CORE_FIELD_KEYS.has(f.key)))
/** 列表展示的扩展列（排除富文本等过宽类型） */
const listExtraFields = computed(() =>
  extraFields.value.filter((f) => f.type !== 'richtext' && f.type !== 'hidden'),
)
const isbnRich = computed(() => {
  const f = fields.value.find((x) => x.key === 'isbn')
  return f?.type === 'richtext' || archive.bodyField === 'isbn'
})
const showIsbnCol = computed(() => {
  const f = fields.value.find((x) => x.key === 'isbn')
  if (!f || f.type === 'hidden') return false
  return !isbnRich.value
})
function isbnPlain(v) {
  if (v == null || v === '') return '—'
  const s = String(v).replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim()
  return s || '—'
}
const hasSchedule = computed(() => fields.value.some((x) => x.key === 'startAt' || x.key === 'endAt'))
const hasStartAt = computed(() => fields.value.some((x) => x.key === 'startAt'))
const hasEndAt = computed(() => fields.value.some((x) => x.key === 'endAt'))
const hasDeadline = computed(() => fields.value.some((x) => x.key === 'applyDeadlineAt'))
const hasSeatLayout = computed(() => fields.value.some((x) => x.key === 'seatRows' || x.key === 'seatCols'))
const scheduleNeedsClock = computed(() =>
  ['startAt', 'endAt', 'applyDeadlineAt'].some(
    (key) => fieldType(key) === 'datetime' && fields.value.some((x) => x.key === key),
  ),
)
const hasMutex = computed(() => fields.value.some((x) => x.key === 'mutexCode'))
const hasCheckin = computed(() => fields.value.some((x) => x.key === 'checkinCode'))
const softDelete = computed(() => !!archive.softDelete)
const tagFilter = computed(() => !!archive.tagFilter)
const multiCategory = computed(() => !!archive.multiCategory || hasCap('multi_category'))
const categoriesByDimension = computed(() => {
  const groups = new Map()
  for (const c of categories.value || []) {
    const dim = (c.dimension || '').trim() || '未分组'
    if (!groups.has(dim)) groups.set(dim, [])
    groups.get(dim).push(c)
  }
  return [...groups.entries()].map(([dimension, items]) => ({ dimension, items }))
})
const stockDisplay = computed(() => archive.stockDisplay || 'count')
/** count：库存数字；available：可认领等余量；toggle：可读/可点播等开关；hidden：不展示 */
const stockAsToggle = computed(() => {
  if (stockDisplay.value === 'toggle') return true
  // 旧内容域 schema 仍写 available：无单据时按开关（失物招领等有 ticket_flow 仍用数字）
  if (stockDisplay.value === 'available') {
    const caps = getSchema()?.capabilities || []
    return !caps.includes('ticket_flow')
  }
  return false
})
const showStock = computed(() => {
  if (stockDisplay.value === 'hidden') return false
  const f = fields.value.find((x) => x.key === 'stock')
  if (f?.type === 'hidden') return false
  if (stockDisplay.value === 'available' || stockDisplay.value === 'toggle') return !!f
  return true
})

function fieldMeta(key) {
  return fields.value.find((x) => x.key === key) || { key }
}
function fieldType(key) {
  return fieldMeta(key).type || 'string'
}
function fieldLabel(key, fallback) {
  return fieldMeta(key).label || fallback
}
const searchPlaceholder = computed(() => {
  const parts = [fieldLabel('title', '名称'), fieldLabel('author', '型号')]
  const isbnF = fields.value.find((x) => x.key === 'isbn')
  if (isbnF && isbnF.type !== 'richtext' && isbnF.type !== 'hidden') {
    parts.push(isbnF.label || '编号')
  }
  const regionF = fields.value.find((x) => x.key === 'region')
  if (regionF && regionF.type !== 'hidden') {
    parts.push(regionF.label || '产地')
  }
  const harvestF = fields.value.find((x) => x.key === 'harvest_on')
  if (harvestF && harvestF.type !== 'hidden') {
    parts.push(harvestF.label || '采摘时间')
  }
  return `搜索${parts.join(' / ')}`
})
function pickerProps(key) {
  const meta = fieldMeta(key)
  if (meta.type === 'date') return datePickerProps(meta)
  return dateTimePickerProps(meta)
}

/** 纯日期字段：API 若带回时分，截成 YYYY-MM-DD 喂给 date picker */
function calendarFormValue(key, raw) {
  if (raw == null || raw === '') return ''
  const s = String(raw).trim()
  if (fieldType(key) === 'date' && s.length >= 10) return s.slice(0, 10)
  return s
}

function formatAuthorCell(v) {
  return formatArchiveScalar({ ...fieldMeta('author'), key: 'author' }, v)
}

function extraDefault(f) {
  const w = archiveFieldWidget(f, { bodyField: archive.bodyField || '' })
  if (w === 'switch' || w === 'number' || w === 'money') return 0
  return ''
}

const list = ref([])
const total = ref(0)
const page = ref(1)
const size = ref(10)
const keyword = ref('')
const listStatus = ref('')
const createdFrom = ref('')
const createdTo = ref('')
const exportPickOpen = ref(false)
const exportPickKeys = ref([])
const recycleMode = ref(false)
const pickedIds = ref([])
const exportColumnOptions = computed(() => importColumns())

function listFilterParams() {
  if (!advancedFilterOn.value || recycleMode.value) return {}
  return {
    listStatus: listStatus.value || undefined,
    createdFrom: createdFrom.value || undefined,
    createdTo: createdTo.value || undefined,
  }
}

function toggleRecycle() {
  recycleMode.value = !recycleMode.value
  page.value = 1
  pickedIds.value = []
  load()
}

function onPicked(rows) {
  pickedIds.value = (rows || []).map((r) => r.id).filter((id) => id != null)
}

async function batchRemove() {
  if (!pickedIds.value.length) return
  await ElMessageBox.confirm(`删除选中的 ${pickedIds.value.length} 条？`, '批量删除', { type: 'warning' })
  await http.post('/api/archive/batch-delete', {
    ids: pickedIds.value,
    ...(getSchema()?.uxCrosscut?.confirm ? { confirm: true } : {}),
  })
  ElMessage.success(`已删除 ${res.data?.ok || 0} 条`)
  pickedIds.value = []
  await load()
}
const includeDeleted = ref(false)
const categories = ref([])
const tags = ref([])
const visible = ref(false)
useUnsavedGuard(visible)
const form = reactive({
  id: null,
  title: '',
  author: '',
  isbn: '',
  categoryId: null,
  categoryIds: [],
  stock: 1,
  status: '',
  onShelf: true,
  _wasDeleted: false,
  coverUrl: '',
  galleryImages: [],
  equipmentNames: [],
  startAt: '',
  endAt: '',
  applyDeadlineAt: '',
  mutexCode: '',
  checkinCode: '',
  tagIds: [],
  viaPoints: '',
  shareNote: '',
  prefNote: '',
  luggageCount: null,
  startCampus: '',
  endCampus: '',
  remindBeforeMinutes: null,
})

function toggleHotMode() {
  hotMode.value = !hotMode.value
  page.value = 1
  load()
}

async function load() {
  const url = hotMode.value && hotRankOn.value ? '/api/archive/hot' : '/api/archive'
  const res = await http.get(url, {
    params: {
      page: page.value,
      size: size.value,
      keyword: hotMode.value ? undefined : (keyword.value || undefined),
      ...listFilterParams(),
      includeDeleted:
        !hotMode.value && ((softDelete.value && includeDeleted.value) || recycleMode.value) ? true : undefined,
      deletedOnly: !hotMode.value && recycleMode.value ? true : undefined,
      sortBy: hotMode.value && downloadCountOn.value
        ? 'downloadCount'
        : (hotMode.value && contentThicken.value.hotByPlay ? 'playCount' : undefined),
    },
  })
  list.value = res.data.list
  total.value = res.data.total
}

async function loadCats() {
  const res = await http.get('/api/categories')
  categories.value = res.data || res || []
}

async function loadTags() {
  if (!tagFilter.value) return
  try {
    const res = await http.get('/api/tags')
    tags.value = res.data || res || []
  } catch {
    tags.value = []
  }
}

async function loadEquipOptions() {
  if (!roomEquipOn.value) {
    equipOptions.value = []
    return
  }
  try {
    const res = await http.get('/api/equipment-dict/options')
    equipOptions.value = res.data || res || []
  } catch {
    equipOptions.value = []
  }
}

function genCheckin() {
  const n = Math.floor(1000 + Math.random() * 9000)
  form.checkinCode = `ACT${n}`
}

function openEdit(row) {
  const extras = {}
  for (const f of extraFields.value) {
    const raw = row?.[f.key] ?? extraDefault(f)
    extras[f.key] = f.type === 'date' && raw ? String(raw).slice(0, 10) : raw
  }
  if (row) {
    Object.assign(form, {
      id: row.id,
      title: row.title || '',
      author: row.author || '',
      isbn: row.isbn || '',
      categoryId: row.categoryId,
      categoryIds: [...(row.categoryIds || [])],
      stock: row.stock ?? 1,
      status: row.status || '',
      onShelf: !row.deleted,
      _wasDeleted: !!row.deleted,
      coverUrl: row.coverUrl || '',
      galleryImages: Array.isArray(row.galleryImages) ? [...row.galleryImages] : [],
      equipmentNames: Array.isArray(row.equipmentNames) ? [...row.equipmentNames] : [],
      startAt: calendarFormValue('startAt', row.startAt || ''),
      endAt: calendarFormValue('endAt', row.endAt || ''),
      applyDeadlineAt: calendarFormValue('applyDeadlineAt', row.applyDeadlineAt || ''),
      mutexCode: row.mutexCode || '',
      checkinCode: row.checkinCode || '',
      tagIds: [...(row.tagIds || [])],
      viaPoints: row.viaPoints || '',
      shareNote: row.shareNote || '',
      prefNote: row.prefNote || '',
      luggageCount: row.luggageCount ?? null,
      startCampus: row.startCampus || '',
      endCampus: row.endCampus || '',
      remindBeforeMinutes: row.remindBeforeMinutes ?? null,
      ...extras,
    })
  } else {
    Object.assign(form, {
      id: null,
      title: '',
      author: '',
      isbn: '',
      categoryId: categories.value[0]?.id || null,
      categoryIds: [],
      stock: 1,
      status: '',
      onShelf: true,
      _wasDeleted: false,
      coverUrl: '',
      galleryImages: [],
      equipmentNames: [],
      startAt: '',
      endAt: '',
      applyDeadlineAt: '',
      mutexCode: '',
      checkinCode: hasCheckin.value ? `ACT${Math.floor(1000 + Math.random() * 9000)}` : '',
      tagIds: [],
      viaPoints: '',
      shareNote: '',
      prefNote: '',
      luggageCount: null,
      startCampus: '',
      endCampus: '',
      remindBeforeMinutes: null,
      ...extras,
    })
  }
  visible.value = true
  episodeRows.value = []
  if (form.id && episodeListOn.value) loadEpisodes()
}

async function save() {
  if (!form.title?.trim()) {
    ElMessage.warning('请填写名称')
    return
  }
  if (multiCategory.value) {
    if (!form.categoryIds?.length) {
      ElMessage.warning(`请选择${fieldLabel('categoryIds', '分类')}`)
      return
    }
  } else if (!form.categoryId) {
    ElMessage.warning(`请选择${fieldLabel('category', '分类')}`)
    return
  }
  if (hasStartAt.value && !form.startAt) {
    ElMessage.warning(`请填写${fieldLabel('startAt', '开始时间')}`)
    return
  }
  if (hasEndAt.value && !form.endAt) {
    ElMessage.warning(`请填写${fieldLabel('endAt', '结束时间')}`)
    return
  }
  if (getSchema()?.borrowThicken?.isbnValidate && !isValidIsbn(form.isbn)) {
    ElMessage.warning('ISBN 格式不正确，请核对后重试')
    return
  }
  const payload = { ...form }
  if (multiCategory.value) {
    payload.categoryId = form.categoryIds[0] || null
  } else {
    delete payload.categoryIds
  }
  delete payload.onShelf
  delete payload._wasDeleted
  if (isbnRich.value) payload.isbn = sanitizeHtml(form.isbn || '')
  let id = form.id
  if (form.id) await http.put(`/api/archive/${form.id}`, payload)
  else {
    const created = await http.post('/api/archive', payload)
    id = created?.id ?? created?.data?.id ?? null
  }
  if (softDelete.value && id && !isPendingReview(form)) {
    const wantOn = !!form.onShelf
    const wasOff = !!form._wasDeleted
    if (wantOn && wasOff) await http.post(`/api/archive/${id}/restore`)
    else if (!wantOn && !wasOff) {
      const reason = offShelfReasonOn.value ? String(form.offShelfReason || '').trim() : ''
      await http.delete(`/api/archive/${id}`, {
        data: {
          offShelfReason: reason,
          ...(getSchema()?.uxCrosscut?.confirm ? { confirm: true } : {}),
        },
      })
    }
  }
  ElMessage.success('已保存')
  visible.value = false
  load()
}

function canStopNotify(row) {
  if (!row || !row.id) return false
  const from = String(row.maintainFrom || row.maintain_from || '').trim()
  const to = String(row.maintainTo || row.maintain_to || '').trim()
  return !!(from || to)
}

async function stopNotify(row) {
  await ElMessageBox.confirm(
    `${hospitalStopNotifyTitle.value}：将取消维护期内预约并站内信通知用户。继续？`,
    '停诊退号',
    { type: 'warning' },
  )
  const res = await http.post(`/api/slots/items/${row.id}/stop-notify`)
  const n = res.data?.cancelled ?? res?.cancelled ?? 0
  ElMessage.success(`已退号 ${n} 笔`)
}

async function remove(row) {
  const verb = softDelete.value ? softCopy.value.verb : '删除'
  let reason = ''
  if (softDelete.value && offShelfReasonOn.value) {
    try {
      const { value } = await ElMessageBox.prompt(offShelfReasonHint.value || '请填写下架原因（可留空）', `${verb}「${row.title}」`, {
        inputValue: row.offShelfReason || '',
        confirmButtonText: verb,
        cancelButtonText: '取消',
      })
      reason = (value || '').trim()
    } catch {
      return
    }
  } else {
    await ElMessageBox.confirm(`确认${verb}「${row.title}」？`, '确认')
  }
  await http.delete(`/api/archive/${row.id}`, {
    data: {
      offShelfReason: reason,
      ...(getSchema()?.uxCrosscut?.confirm ? { confirm: true } : {}),
    },
  })
  ElMessage.success(softDelete.value ? `已${softCopy.value.verb}` : '已删除')
  load()
}

async function restore(row) {
  await http.post(`/api/archive/${row.id}/restore`)
  ElMessage.success('已恢复')
  load()
}

async function approve(row) {
  await ElMessageBox.confirm(`审核通过并上架「${row.title}」？`, publishReview.value ? '投稿审核' : '商品审核')
  await http.post(`/api/archive/${row.id}/approve`)
  ElMessage.success(
    publishReview.value
      ? `${publishApproveNotifyTitle.value}，已上架`
      : '已审核上架',
  )
  load()
}

async function reject(row) {
  const title = publishReview.value ? '投稿审核' : '商品审核'
  let reason = ''
  if (datingRejectReasonOn.value) {
    const { value } = await ElMessageBox.prompt(
      labels.value.rejectReasonPlaceholder || '请填写驳回理由，便于对方修改后再提交',
      title,
      {
        confirmButtonText: '驳回',
        cancelButtonText: '取消',
        inputPlaceholder: labels.value.rejectReasonLabel || '驳回理由',
        inputValidator: (v) => (!!String(v || '').trim() ? true : (labels.value.rejectReasonRequired || '请填写驳回理由')),
      },
    )
    reason = String(value || '').trim()
  } else {
    await ElMessageBox.confirm(`驳回「${row.title}」？驳回后不公开展示。`, title)
  }
  await http.post(`/api/archive/${row.id}/reject`, {
    ...(reason ? { rejectReason: reason } : {}),
    ...(getSchema()?.uxCrosscut?.confirm ? { confirm: true } : {}),
  })
  ElMessage.success('已驳回')
  load()
}

async function albumAudit(row, status) {
  const tip = status === 'approved' ? `通过「${row.title}」的相册？` : `驳回「${row.title}」的相册？`
  await ElMessageBox.confirm(tip, labels.value.albumAuditLabel || '相册审核')
  await http.post(`/api/archive/${row.id}/album-audit`, { status })
  ElMessage.success(status === 'approved' ? '相册已通过' : '相册已驳回')
  load()
}

function albumAuditStatusText(row) {
  const st = String(row?.albumAuditStatus || '')
  if (st === 'pending') return adminLabels.value.albumAuditPending || '相册待审'
  if (st === 'approved') return adminLabels.value.albumAuditApproved || '相册已通过'
  if (st === 'rejected') return adminLabels.value.albumAuditRejected || '相册未通过'
  return ''
}

async function onCover(opt) {
  const fd = new FormData()
  fd.append('file', opt.file)
  const res = await http.post('/api/upload', fd)
  form.coverUrl = res.data.url
  ElMessage.success('已上传')
}

async function onGalleryAdd(opt) {
  if (form.galleryImages.length >= 9) {
    ElMessage.warning('最多 9 张')
    return
  }
  const fd = new FormData()
  fd.append('file', opt.file)
  const res = await http.post('/api/upload', fd)
  form.galleryImages.push(res.data.url)
  if (!form.coverUrl) form.coverUrl = res.data.url
  ElMessage.success('已加入图集')
}

/** 核心列兜底中文名（schema 缺 label 时用） */
const FIELD_FALLBACK_LABELS = {
  title: '名称',
  author: '型号',
  isbn: '编号',
  category: '分类',
  stock: '库存',
  mutexCode: '互斥码',
  checkinCode: '签到码',
  startAt: '开始时间',
  endAt: '结束时间',
  applyDeadlineAt: '截止',
}

/**
 * 导入/导出列 = 当前领域 archive.fields 全量（hidden 除外）+ 可选标签。
 * 表头用领域中文 label；键与 ArchiveStore / updateItem 一致。
 */
function importColumns() {
  const cols = []
  const seen = new Set()
  for (const f of fields.value) {
    if (!f?.key || f.type === 'hidden') continue
    if (seen.has(f.key)) continue
    seen.add(f.key)
    cols.push({
      key: f.key,
      label: (f.label || FIELD_FALLBACK_LABELS[f.key] || f.key).trim(),
      type: f.type || 'string',
    })
  }
  for (const k of ['title', 'author', 'isbn', 'category', 'stock']) {
    if (seen.has(k)) continue
    if (k === 'stock' && !showStock.value) continue
    const meta = fields.value.find((f) => f?.key === k)
    if (meta?.type === 'hidden') continue
    seen.add(k)
    cols.push({ key: k, label: FIELD_FALLBACK_LABELS[k], type: k === 'stock' ? 'number' : 'string' })
  }
  if (tagFilter.value && !seen.has('tags')) {
    cols.push({ key: 'tags', label: '标签', type: 'string' })
  }
  return cols
}

function sampleForCol(col) {
  if (col.key === 'category') return `默认${col.label || fieldLabel('category', '分类')}`
  if (col.key === 'stock') return '1'
  if (col.key === 'tags') return ''
  if (col.key === 'checkinCode') return 'ACT1001'
  if (col.type === 'boolean' || col.type === 'switch') return '1'
  if (col.type === 'number') return '1'
  if (col.type === 'datetime') return '2026-07-21 09:00'
  if (col.type === 'date') return '2026-07-21'
  if (col.type === 'url') return 'https://example.com'
  if (col.type === 'textarea') return '示例说明'
  if (col.type === 'select' && Array.isArray(col.options) && col.options.length) {
    const o = col.options[0]
    return typeof o === 'object' && o != null ? (o.value ?? o.label) : o
  }
  return `示例${col.label}`
}

function exportCell(row, col) {
  if (col.key === 'category') return row.categoryName ?? ''
  if (col.key === 'tags') return (row.tagNames || []).join('、')
  const v = row[col.key]
  if (v == null || v === '') return ''
  const meta = { key: col.key, label: col.label, type: col.type }
  const shown = formatArchiveScalar(meta, v, '')
  return shown
}

async function downloadTemplate() {
  const columns = importColumns().map((c) => ({
    key: c.key,
    label: c.label,
    sample: sampleForCol(c),
  }))
  const blob = await http.post('/api/archive/import-template', { columns }, { responseType: 'blob' })
  saveBlob(`${label.value || 'archive'}_import_template.xlsx`, blob)
  ElMessage.success('已下载导入模板，请在「导入」表从第 2 行填写')
}

async function openSeatAttrs(row) {
  if (!row?.id) return
  seatAttrShowId.value = row.id
  seatAttrSaving.value = false
  try {
    const res = await http.get(`/api/seats/shows/${row.id}/map`)
    const data = res.data?.data || res.data || {}
    seatAttrCols.value = data.cols || row.seatCols || 8
    seatAttrSeats.value = (data.seats || []).map((s) => ({
      seatCode: s.seatCode,
      seatAttr: String(s.seatAttr || ''),
    }))
    seatAttrVisible.value = true
  } catch (e) {
    ElMessage.error(e?.response?.data?.message || e.message || '无法加载座位图')
  }
}

function cycleSeatAttr(seat) {
  const cur = String(seat.seatAttr || '')
  if (cur === 'couple') seat.seatAttr = 'accessible'
  else if (cur === 'accessible') seat.seatAttr = ''
  else seat.seatAttr = 'couple'
}

async function saveSeatAttrs() {
  const attrs = {}
  for (const s of seatAttrSeats.value) {
    attrs[s.seatCode] = String(s.seatAttr || '')
  }
  seatAttrSaving.value = true
  try {
    await http.put(`/api/seats/shows/${seatAttrShowId.value}/attrs`, { attrs })
    ElMessage.success('座位属性已保存')
    seatAttrVisible.value = false
  } catch (e) {
    ElMessage.error(e?.response?.data?.message || e.message || '保存失败')
  } finally {
    seatAttrSaving.value = false
  }
}

async function openSnackAdmin() {
  try {
    const res = await http.get('/api/seats/snacks/all')
    const list = res.data?.data || res.data || []
    snackRows.value = (Array.isArray(list) ? list : []).map((s) => ({
      id: s.id,
      title: s.title || '',
      priceYuan: Number(s.priceYuan || 0),
      stock: Number(s.stock || 0),
      onSale: String(s.status || 'on') === 'on',
      _saving: false,
    }))
    snackVisible.value = true
  } catch (e) {
    ElMessage.error(e?.response?.data?.message || e.message || '无法加载卖品')
  }
}

function addSnackRow() {
  snackRows.value = [
    ...snackRows.value,
    { id: 0, title: '', priceYuan: 0, stock: 0, onSale: true, _saving: false },
  ]
}

async function saveSnackRow(row) {
  if (!String(row.title || '').trim()) {
    ElMessage.warning('请填写卖品名称')
    return
  }
  row._saving = true
  try {
    const res = await http.put('/api/seats/snacks', {
      id: row.id || undefined,
      title: String(row.title).trim(),
      priceYuan: Number(row.priceYuan || 0),
      stock: Number(row.stock || 0),
      status: row.onSale ? 'on' : 'off',
    })
    const saved = res.data?.data || res.data || {}
    if (saved.id) row.id = saved.id
    ElMessage.success('已保存')
  } catch (e) {
    ElMessage.error(e?.response?.data?.message || e.message || '保存失败')
  } finally {
    row._saving = false
  }
}

function onExportClick() {
  if (!exportColumnsOn.value) {
    exportCsv()
    return
  }
  const cols = importColumns()
  exportPickKeys.value = cols.map((c) => c.key)
  exportPickOpen.value = true
}

function confirmExport() {
  exportPickOpen.value = false
  exportCsv(exportPickKeys.value)
}

async function exportCsv(onlyKeys) {
  const res = await http.get('/api/archive', {
    params: { page: 1, size: 5000, keyword: keyword.value || undefined, ...listFilterParams() },
  })
  const rows = res.data?.list || []
  if (!rows.length) {
    ElMessage.warning('当前无数据可导出')
    return
  }
  let cols = importColumns()
  if (Array.isArray(onlyKeys) && onlyKeys.length) {
    const allow = new Set(onlyKeys)
    cols = cols.filter((c) => allow.has(c.key))
  }
  if (!cols.length) {
    ElMessage.warning('请选择导出列')
    return
  }
  const headers = cols.map((c) => c.label)
  const body = rows.map((row) => cols.map((c) => exportCell(row, c)))
  const blob = await http.post(
    '/api/archive/export-xlsx',
    { headers, rows: body },
    { responseType: 'blob' },
  )
  saveBlob(`${label.value || 'archive'}_${Date.now()}.xlsx`, blob)
  ElMessage.success(`已导出 ${rows.length} 条`)
}

async function onImport(opt) {
  const file = opt.file
  if (!file) return
  const name = String(file.name || '').toLowerCase()
  if (!name.endsWith('.xlsx')) {
    ElMessage.warning('请上传 xlsx 文件（先下载导入模板）')
    return
  }
  lastImportError.value = ''
  importErrors.value = []
  const fd = new FormData()
  fd.append('file', file)
  try {
    const res = await http.post('/api/archive/import-xlsx', fd)
    const r = res.data || {}
    const ok = r.ok || 0
    const fail = r.fail || 0
    importErrors.value = r.errors || []
    if (fail > 0) {
      ElMessage.warning(`成功 ${ok} 条，失败 ${fail} 条`)
    } else {
      ElMessage.success(`成功导入 ${ok} 条`)
    }
    await loadCats()
    await load()
  } catch (e) {
    lastImportError.value = e?.message || '导入失败'
    ElMessage.error(lastImportError.value)
  }
}

watch(
  () => route.query.q,
  (q) => {
    if (typeof q !== 'string') return
    keyword.value = q.trim()
    page.value = 1
    load()
  },
)

onMounted(async () => {
  if (typeof route.query.q === 'string' && route.query.q.trim()) {
    keyword.value = route.query.q.trim()
  }
  await loadCats()
  await loadTags()
  await loadEquipOptions()
  await load()
})
