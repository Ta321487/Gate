import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import http from '../api/http'
import {
  anyLoyaltyEnabled,
  emptyProfileExtras,
  isMemberTierEnabled,
  isPointsEnabled,
  isWalletEnabled,
  loyaltySchema,
  profileAudienceOf,
  profileFieldsForAudience,
  getSchema,
  roleLabel,
  schemaLabels,
} from '../utils/domainSchema.js'
import {
  validateProfileFormats,
  isProfileFieldRequired,
  isProfileFieldVisible,
} from '../utils/profileValidate.js'
import { authPolicy, chromeDisplayName, clearAuthStorage, loginPathForRole, setMustChangePassword, syncProfileDisplay } from '../utils/session.js'
import { memberTierTone } from '../utils/statusTone.js'
import { userMenuPath } from '../utils/menuRoutes.js'
import { APP_DELIVERED } from '../appDelivered.js'
import {
  accountFaceFromDelivered,
  profilePageCopy,
} from '../utils/portalShellNav.js'

const BASIC_KEYS = new Set(['realName', 'phone', 'email', 'gender'])
const WIDE_KEYS = new Set([
  'officeOrDorm', 'campusAddress', 'receiveAddress', 'deliveryAddress', 'allergyNote', 'defaultRemark',
  'skinOrPrefer', 'usualPlace', 'labOrOffice', 'officeLoc', 'workUnit', 'orgName', 'orgOrClub',
])
const router = useRouter()
const route = useRoute()
const labels = schemaLabels()
const accountFace = computed(() => accountFaceFromDelivered(APP_DELIVERED))
const profileCopy = profilePageCopy()
const tabsPosition = computed(() => (accountFace.value === 'inbox' ? 'left' : 'top'))
/** §3：资料 / 安全 / 设备 / 其他 —— 禁止整页瀑布；脸只换构图 */
const TAB_NAMES = new Set(['profile', 'security', 'devices', 'other'])
const activeTab = ref(
  TAB_NAMES.has(String(route.query.tab || '')) ? String(route.query.tab) : 'profile',
)
watch(activeTab, (name) => {
  const cur = String(route.query.tab || 'profile')
  if (cur === name) return
  const q = { ...route.query }
  if (name === 'profile') delete q.tab
  else q.tab = name
  router.replace({ query: q })
})
watch(
  () => route.query.tab,
  (raw) => {
    const name = TAB_NAMES.has(String(raw || '')) ? String(raw) : 'profile'
    if (activeTab.value !== name) activeTab.value = name
  },
)
const pointsLedgerPath = computed(() => userMenuPath('points_ledger') || '')
/** 个人中心单据入口：仅买家端展示；管理/商家岗请走工作台。 */
const myDocLinks = computed(() => {
  if (audience.value !== 'user') return []
  const raw = getSchema()?.workbench?.myDocs
  if (!Array.isArray(raw) || !raw.length) return []
  return raw
    .map((d) => {
      const key = String(d?.key || '')
      const to = userMenuPath(key)
      if (!to) return null
      return { key, label: d.label || key, to }
    })
    .filter(Boolean)
})
const minPwdLen = computed(() => Math.max(1, Number(authPolicy().passwordMinLength) || 6))
const strengthHint = computed(
  () => labels.passwordStrengthHint || `密码至少 ${minPwdLen.value} 位，建议包含字母和数字`,
)
const hasSecurityQuestion = ref(false)
const saving = ref(false)
const loyalty = ref(null)
const rechargeVisible = ref(false)
const recharging = ref(false)
const rechargeTiers = [50, 100, 200, 500]
const rechargeAmount = ref(100)
const userLabel = computed(() => roleLabel('user', '用户'))
const audience = computed(() => profileAudienceOf())
const marketplace = computed(() => !!getSchema()?.shopMarketplace)
/** staff 业务区按岗位/店铺；勿把商家套成「买家资料」 */
const bizSectionTitle = computed(() => {
  if (audience.value === 'staff') {
    if (marketplace.value || bizFields.value.some((f) => f?.key === 'shopName')) {
      return '店铺资料'
    }
    const staffLab = roleLabel('subadmin', '') || roleLabel('admin', '管理')
    return `${staffLab}资料`
  }
  return `${userLabel.value}资料`
})
const anyLoyalty = computed(() => anyLoyaltyEnabled())
/** 仅终端买家展示钱包/积分；商家·管理岗不展示充值 */
const showBuyerLoyalty = computed(() => anyLoyalty.value && audience.value === 'user')
const walletOn = computed(() => isWalletEnabled())
const pointsOn = computed(() => isPointsEnabled())
const tierOn = computed(() => isMemberTierEnabled())
const pointsHint = computed(() => {
  const pts = loyalty.value || {}
  const sch = loyaltySchema()?.points || {}
  const pay = !!pts.pointsPayEnabled || !!sch.payEnabled
  const offset = !!pts.pointsOffsetEnabled || !!sch.offsetEnabled
  const checkIn = !!pts.pointsCheckInEnabled || !!sch.checkInEnabled
  const n = Number(pts.pointsCheckInAmount || sch.checkInPoints || 10)
  const bits = []
  if (pay) bits.push('本站商品可用积分兑换')
  else if (offset) bits.push('下单时可选用积分抵扣部分货款')
  else bits.push('积分随订单完成赠送')
  if (checkIn) bits.push(`每天首次登录可获得 ${n} 积分`)
  return bits.join('；') + '。'
})
const allFields = computed(() => profileFieldsForAudience(audience.value))
const basicFields = computed(() => allFields.value.filter((f) => BASIC_KEYS.has(f.key) || f.storage === 'phone'))
const bizFields = computed(() =>
  allFields.value.filter(
    (f) => !BASIC_KEYS.has(f.key) && f.storage !== 'phone' && isProfileFieldVisible(f, form.extras),
  ),
)

const form = reactive({
  username: '',
  nickname: '',
  phone: '',
  avatarUrl: '',
  extras: emptyProfileExtras(profileFieldsForAudience(profileAudienceOf())),
  oldPassword: '',
  newPassword: '',
  confirmPassword: '',
  securityQuestion: '',
  securityAnswer: '',
  realNameAcked: false,
  profileEditable: true,
  orgId: null,
})
const orgOptions = ref([])
const orgFeatureOn = computed(() => !!getSchema()?.orgCrosscut?.org)
const orgPickLabel = computed(() => labels.orgPickLabel || '所属组织')
const orgPickPlaceholder = computed(() => labels.orgPickPlaceholder || '请选择组织')

const contactField = ref('phone')
const contactValue = ref('')
const contactCaptcha = ref('')
const contactCaptchaImg = ref('')
const contactSaving = ref(false)
const loginLogs = ref([])
const mySessions = ref([])
const cancelReason = ref('')
const cancelSaving = ref(false)

const displayName = computed(() =>
  chromeDisplayName(form.nickname, form.username, '我'),
)

const datingCompletenessOn = computed(
  () => !!getSchema()?.interactThicken?.datingProfileCompleteness,
)
const profileCompletenessLabel = computed(
  () => getSchema()?.labels?.profileCompletenessLabel || '资料完善度',
)
const datingCompletenessHint = computed(() =>
  datingCompletenessOn.value ? (getSchema()?.labels?.datingCompletenessHint || '') : '',
)
const datingCompletenessMissingLead = computed(
  () => getSchema()?.labels?.datingCompletenessMissingLead || '待完善：',
)
/** 婚恋完整度额外计入城市/学历/年龄段（即使非必填） */
const DATING_EXTRA_KEYS = new Set(['city', 'education', 'ageRange'])

const profileChecklist = computed(() => {
  const items = []
  items.push({
    label: '昵称',
    ok: !!String(form.nickname || '').trim(),
  })
  items.push({
    label: '头像',
    ok: !!String(form.avatarUrl || '').trim(),
  })
  for (const f of allFields.value) {
    if (!isProfileFieldVisible(f, form.extras)) continue
    const force =
      datingCompletenessOn.value && DATING_EXTRA_KEYS.has(f.key)
    if (!force && !f.required && !isProfileFieldRequired(f, form.extras)) continue
    let ok = false
    if (f.storage === 'phone') ok = !!String(form.phone || '').trim()
    else ok = !!String(form.extras?.[f.key] || '').trim()
    items.push({ label: f.label || f.key, ok })
  }
  return items
})

const profileCompletePct = computed(() => {
  const items = profileChecklist.value
  if (!items.length) return 100
  const ok = items.filter((x) => x.ok).length
  return Math.round((ok / items.length) * 100)
})

const profileMissingLabels = computed(() =>
  profileChecklist.value.filter((x) => !x.ok).map((x) => x.label),
)

const tierBarWidth = computed(() => {
  const tone = memberTierTone(loyalty.value?.memberTierLabel || loyalty.value?.memberTier)
  if (tone === 'ok') return '100%'
  if (tone === 'progress') return '72%'
  if (tone === 'warn') return '48%'
  return '28%'
})

function isWideField(f) {
  return !!(f && (WIDE_KEYS.has(f.key) || (f.maxLength && f.maxLength >= 100)))
}

function onBizSelectChange(f) {
  const drivers = new Set(['identityType', 'readerType', 'ownerType', 'deliveryType', 'pickupType'])
  if (!drivers.has(f?.key)) return
  for (const x of allFields.value) {
    if (x.key === f.key || !x.visibleWhen) continue
    if (!isProfileFieldVisible(x, form.extras)) form.extras[x.key] = ''
  }
}

function clearPasswords() {
  form.oldPassword = ''
  form.newPassword = ''
  form.confirmPassword = ''
  form.securityAnswer = ''
}

function goBack() {
  if (window.history.length > 1) router.back()
  else router.push('/')
}

function openRecharge() {
  rechargeAmount.value = 100
  rechargeVisible.value = true
}

async function doRecharge() {
  recharging.value = true
  try {
    const res = await http.post('/api/loyalty/demo-recharge', { amount: rechargeAmount.value })
    loyalty.value = res.data || loyalty.value
    ElMessage.success(`已充值 ¥${Number(rechargeAmount.value).toFixed(0)}`)
    rechargeVisible.value = false
  } finally {
    recharging.value = false
  }
}

async function load() {
  const res = await http.get('/api/profile')
  const data = res.data || {}
  form.username = data.username || ''
  form.nickname = data.nickname || ''
  form.phone = data.phone || ''
  form.avatarUrl = data.avatarUrl || ''
  form.profileEditable = data.profileEditable !== false
  form.extras = {
    ...emptyProfileExtras(profileFieldsForAudience(profileAudienceOf())),
    ...(data.extras || {}),
  }
  hasSecurityQuestion.value = !!data.hasSecurityQuestion
  form.realNameAcked = !!data.realNameAcked
  form.orgId = data.orgId || null
  form.securityQuestion = ''
  clearPasswords()
  if (data.mustChangePassword != null) setMustChangePassword(!!data.mustChangePassword)
  if (showBuyerLoyalty.value) {
    try {
      const loy = await http.get('/api/loyalty/me')
      loyalty.value = loy.data || null
    } catch {
      loyalty.value = null
    }
  } else {
    loyalty.value = null
  }
  await Promise.all([loadLoginLogs(), loadMySessions(), loadContactCaptcha()])
}

async function loadLoginLogs() {
  try {
    const res = await http.get('/api/auth/login-logs')
    loginLogs.value = res.data || []
  } catch {
    loginLogs.value = []
  }
}

async function loadMySessions() {
  try {
    const res = await http.get('/api/auth/my-sessions')
    mySessions.value = res.data || []
  } catch {
    mySessions.value = []
  }
}

async function loadContactCaptcha() {
  try {
    const res = await http.get('/api/auth/captcha')
    contactCaptchaImg.value = res.data?.image || ''
  } catch {
    contactCaptchaImg.value = ''
  }
}

async function submitContact() {
  if (!contactValue.value.trim()) {
    ElMessage.warning('请填写新的手机号或邮箱')
    return
  }
  if (!contactCaptcha.value) {
    ElMessage.warning('请填写验证码')
    return
  }
  contactSaving.value = true
  try {
    const res = await http.post('/api/profile/change-contact', {
      field: contactField.value,
      value: contactValue.value.trim(),
      captcha: contactCaptcha.value,
    })
    const data = res.data || {}
    form.phone = data.phone || form.phone
    form.extras = {
      ...emptyProfileExtras(profileFieldsForAudience(profileAudienceOf())),
      ...(data.extras || {}),
    }
    contactValue.value = ''
    contactCaptcha.value = ''
    ElMessage.success('已更新')
    loadContactCaptcha()
  } catch {
    contactCaptcha.value = ''
    loadContactCaptcha()
  } finally {
    contactSaving.value = false
  }
}

async function kickSession(row) {
  await ElMessageBox.confirm('确定将该设备下线？', '提示', { type: 'warning' })
  await http.post(`/api/auth/my-sessions/${encodeURIComponent(row.sessionId)}/kick`)
  ElMessage.success('已下线')
  loadMySessions()
}

async function submitCancel() {
  await ElMessageBox.confirm('提交后需管理员审核，通过后账号将停用。确定继续？', '注销申请', {
    type: 'warning',
  })
  cancelSaving.value = true
  try {
    await http.post('/api/profile/cancel-request', { reason: cancelReason.value })
    ElMessage.success('已提交注销申请')
    cancelReason.value = ''
  } finally {
    cancelSaving.value = false
  }
}

async function save() {
  for (const f of allFields.value) {
    if (!isProfileFieldVisible(f, form.extras)) continue
    if (!isProfileFieldRequired(f, form.extras)) continue
    if (f.storage === 'phone') {
      if (!form.phone?.trim()) {
        ElMessage.warning(`请填写${f.label}`)
        return
      }
    } else if (!String(form.extras[f.key] || '').trim()) {
      ElMessage.warning(`请填写${f.label}`)
      return
    }
  }
  const fmt = validateProfileFormats(form.phone, form.extras)
  if (fmt) {
    ElMessage.warning(fmt)
    return
  }
  const changingPwd = !!(form.newPassword || form.oldPassword || form.confirmPassword)
  if (changingPwd) {
    if (!form.oldPassword) {
      ElMessage.warning('请填写原密码')
      return
    }
    if (!form.newPassword) {
      ElMessage.warning('请填写新密码')
      return
    }
    if (form.newPassword.length < minPwdLen.value) {
      ElMessage.warning(strengthHint.value)
      return
    }
    if (form.newPassword !== form.confirmPassword) {
      ElMessage.warning('两次输入的新密码不一致')
      return
    }
  }
  if ((form.securityQuestion && !form.securityAnswer) || (!form.securityQuestion && form.securityAnswer)) {
    ElMessage.warning('密保问题与答案需同时填写')
    return
  }
  saving.value = true
  try {
    const body = {
      nickname: form.nickname,
      phone: form.phone,
      extras: form.extras,
      realNameAcked: !!form.realNameAcked,
      orgId: form.orgId || null,
    }
    if (changingPwd) {
      body.oldPassword = form.oldPassword
      body.newPassword = form.newPassword
      body.confirmPassword = form.confirmPassword
    }
    if (form.securityQuestion && form.securityAnswer) {
      body.securityQuestion = form.securityQuestion
      body.securityAnswer = form.securityAnswer
    }
    const res = await http.put('/api/profile', body)
    const data = res.data || {}
    if (changingPwd || data.requireRelogin) {
      const role = localStorage.getItem('role') || ''
      const staffKind = localStorage.getItem('staffKind') || ''
      clearAuthStorage()
      ElMessage.success('密码已修改，请重新登录')
      router.replace({ path: loginPathForRole(role, staffKind), query: { reason: 'password' } })
      return
    }
    form.extras = {
      ...emptyProfileExtras(profileFieldsForAudience(profileAudienceOf())),
      ...(data.extras || {}),
    }
    form.phone = data.phone || form.phone
    form.nickname = data.nickname || form.nickname
    form.avatarUrl = data.avatarUrl || form.avatarUrl
    hasSecurityQuestion.value = !!data.hasSecurityQuestion
    form.securityQuestion = ''
    clearPasswords()
    syncProfileDisplay({ nickname: form.nickname, avatarUrl: form.avatarUrl })
    ElMessage.success('已保存')
  } finally {
    saving.value = false
  }
}

async function onAvatar(opt) {
  const fd = new FormData()
  fd.append('file', opt.file)
  const res = await http.post('/api/profile/avatar', fd)
  Object.assign(form, {
    avatarUrl: res.data?.avatarUrl,
    nickname: res.data?.nickname ?? form.nickname,
  })
  clearPasswords()
  syncProfileDisplay({ nickname: form.nickname, avatarUrl: form.avatarUrl })
  ElMessage.success('头像已更新')
}

onMounted(() => {
  if (orgFeatureOn.value) {
    http.get('/api/org/options').then((res) => {
      orgOptions.value = res.data || []
    }).catch(() => {})
  }
  load()
})
