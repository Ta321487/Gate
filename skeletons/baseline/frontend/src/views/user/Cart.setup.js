import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import http from '../../api/http'
import { removeCart, upsertCart } from '../../utils/apiCalls.js'
import {
  anyLoyaltyEnabled,
  hasTrait,
  getSchema,
  hasCap,
  isCouponEnabled,
  isMemberTierEnabled,
  isPointsEnabled,
  isSpendDiscountEnabled,
  isWalletEnabled,
  loyaltySchema,
  menuLabel,
} from '../../utils/domainSchema.js'
import { addressTagOptions, normalizeAddressTag } from '../../utils/addressTags.js'
import { APP_DELIVERED } from '../../appDelivered.js'

const router = useRouter()
const tradeSurface = computed(() => {
  const s = String(
    APP_DELIVERED?.tradeSurfaceStyle
      || import.meta.env.VITE_TRADE_SURFACE_STYLE
      || '',
  ).trim()
  if (['shelfgrid', 'menuboard', 'showtime'].includes(s)) return s
  return ''
})
const tagOptions = computed(() => addressTagOptions())
const cartLabel = menuLabel('user', 'cart', '购物车')
const orderNoun = computed(() => getSchema()?.entities?.order?.label || '订单')
const isFood = computed(() => hasTrait('food'))
const deliveryTypeLabel = computed(() => (isFood.value ? '用餐方式' : '收货方式'))
const anyLoyalty = computed(() => anyLoyaltyEnabled())
const walletOn = computed(() => isWalletEnabled())
const demoPay = computed(() => !!getSchema()?.demoPay || !!getSchema()?.shopMarketplace)
const marketplace = computed(() => !!getSchema()?.shopMarketplace)
const demoPayHint = computed(
  () =>
    getSchema()?.labels?.demoPayHint
    || '选择支付宝或微信，确认后从账户余额扣款。',
)
const pointsOn = computed(() => isPointsEnabled())
const pointsPayOn = computed(() => !!account.value.pointsPayEnabled || !!loyaltySchema()?.points?.payEnabled)
const pointsOffsetOn = computed(
  () => !!account.value.pointsOffsetEnabled || !!loyaltySchema()?.points?.offsetEnabled,
)
const discountOn = computed(() => isSpendDiscountEnabled())
const tierOn = computed(() => isMemberTierEnabled())
const couponOn = computed(() => isCouponEnabled())
const mineCoupons = ref([])
const lineCustom = computed(() => hasCap('line_custom'))
const weighSale = computed(() => hasCap('weigh_sale'))
const weightRows = computed(() => selectedValid.value.filter((row) => Number(row.sellByWeight) === 1))
const deliveryWindow = computed(() => hasCap('delivery_window'))
const groupBuy = computed(() => hasCap('group_buy'))
const groupOpens = ref([])
const specOptions = ref([])
const windowSlots = ref([])
const windowRate = ref(1)
const windowPriceName = ref('')
const customTextLabel = computed(() => getSchema()?.labels?.lineCustomTextLabel || '定制文字')
const customSpecLabel = computed(() => getSchema()?.labels?.lineCustomSpecLabel || '')
const customImageLabel = computed(() => getSchema()?.labels?.lineCustomImageLabel || '')
const customHint = computed(
  () => getSchema()?.labels?.lineCustomHint || '填写后会记在本订单上。',
)
const lineExtraMap = reactive({})
const deliveryOptions = computed(() =>
  isFood.value ? ['外卖配送', '到店自取', '堂食'] : ['配送到家', '到店自提'],
)
const tasteLabel = computed(() => getSchema()?.labels?.tasteNoteLabel || '口味 / 忌口')
const tastePlaceholder = computed(
  () => getSchema()?.labels?.tasteNotePlaceholder || '如：少辣、不要香菜、多糖少冰',
)
const tasteNoteHint = computed(() => getSchema()?.labels?.tasteNoteHint || '')
const tasteChips = computed(() => {
  const raw = getSchema()?.entities?.order?.tasteNoteChips
  return Array.isArray(raw) ? raw.map((x) => String(x || '').trim()).filter(Boolean) : []
})
const orderRemarkLabel = computed(() => getSchema()?.labels?.orderRemarkLabel || '订单备注')
const orderRemarkHint = computed(() => getSchema()?.labels?.orderRemarkHint || '')
const thicken = computed(() => getSchema()?.tradeThicken || {})
const invoiceTitleOn = computed(() => !!thicken.value.invoiceTitle)
const invoiceTitleLabel = computed(() => getSchema()?.labels?.invoiceTitleLabel || '发票抬头')
const invoiceTitleHint = computed(() => getSchema()?.labels?.invoiceTitleHint || '')
const spendDiscountHelpOn = computed(() => !!thicken.value.spendDiscountHelp && isSpendDiscountEnabled())
const spendDiscountHelpLabel = computed(() => getSchema()?.labels?.spendDiscountHelpLabel || '满减规则')
const spendDiscountHelpBody = computed(() => getSchema()?.labels?.spendDiscountHelpBody || '')
const giftPromoOn = computed(() => !!thicken.value.giftPromo)
const giftPromoLabel = computed(() => getSchema()?.labels?.giftPromoLabel || '满赠说明')
const giftPromoBody = computed(() => getSchema()?.labels?.giftPromoBody || '')
const couponMutexOn = computed(() => !!thicken.value.couponMutex && couponOn.value)
const couponMutexLabel = computed(() => getSchema()?.labels?.couponMutexLabel || '优惠券说明')
const couponMutexBody = computed(() => getSchema()?.labels?.couponMutexBody || '')
const memberDayOn = computed(() => !!thicken.value.memberDay && tierOn.value)
const memberDayLabel = computed(() => getSchema()?.labels?.memberDayLabel || '会员日')
const memberDayHint = computed(() => getSchema()?.labels?.memberDayHint || '')
const pointsFreightOn = computed(() => !!thicken.value.pointsFreight)
const pointsFreightHint = computed(() => getSchema()?.labels?.pointsFreightHint || '')
const defaultAddressLabel = computed(() => getSchema()?.labels?.defaultAddressLabel || '设为默认')
const defaultAddressHint = computed(() => getSchema()?.labels?.defaultAddressHint || '')
const defaultAddressSaveLabel = computed(() => `保存时${defaultAddressLabel.value}`)
const cartSelectOn = computed(() => !!thicken.value.cartSelectAll)
const cartChangeSpecOn = computed(() => !!thicken.value.cartChangeSpec)
const cartFreeShipOn = computed(() => !!thicken.value.cartFreeShip)
const cartSelectAllLabel = computed(() => getSchema()?.labels?.cartSelectAllLabel || '全选')
const cartClearInvalidLabel = computed(() => getSchema()?.labels?.cartClearInvalidLabel || '清理失效')
const cartInvalidHint = computed(() => getSchema()?.labels?.cartInvalidHint || '已下架或无货，不参与结算。')
const cartChangeSpecLabel = computed(() => getSchema()?.labels?.cartChangeSpecLabel || '换规格')
const cartNoSpecHint = computed(() => getSchema()?.labels?.cartNoSpecHint || '当前没有可换规格。')
const cartFreeShipHint = computed(() => getSchema()?.labels?.cartFreeShipHint || '再买 ¥{n} 即可包邮')
const cartFreeShipOkHint = computed(() => getSchema()?.labels?.cartFreeShipOkHint || '已满包邮门槛')
const stockLockHint = computed(() =>
  thicken.value.stockLock ? (getSchema()?.labels?.stockLockHint || '') : '',
)
const selectedIds = ref([])
const validRows = computed(() => list.value.filter((r) => !r.invalid))
const invalidCount = computed(() => list.value.filter((r) => r.invalid).length)
const selectedValid = computed(() =>
  cartSelectOn.value
    ? validRows.value.filter((r) => selectedIds.value.includes(r.itemId))
    : validRows.value,
)
const allValidChecked = computed(
  () => validRows.value.length > 0 && validRows.value.every((r) => selectedIds.value.includes(r.itemId)),
)
const someValidChecked = computed(() => validRows.value.some((r) => selectedIds.value.includes(r.itemId)))
const freeShipThreshold = computed(() => {
  const fromItems = selectedValid.value
    .map((r) => Number(r.freeShipYuan))
    .filter((n) => n > 0)
  if (fromItems.length) return Math.min(...fromItems)
  return Number(getSchema()?.freeShipYuan || 0)
})
const freeShipText = computed(() => {
  const th = freeShipThreshold.value
  if (!(th > 0)) return ''
  const gap = th - Number(totalYuan.value)
  if (gap <= 0) return cartFreeShipOkHint.value
  return String(cartFreeShipHint.value || '').replace('{n}', gap.toFixed(2))
})

function isSelected(row) {
  return selectedIds.value.includes(row.itemId)
}
function setSelected(row, on) {
  if (row.invalid) return
  const id = row.itemId
  if (on) {
    if (!selectedIds.value.includes(id)) selectedIds.value = [...selectedIds.value, id]
  } else {
    selectedIds.value = selectedIds.value.filter((x) => x !== id)
  }
}
function toggleSelectAll(on) {
  selectedIds.value = on ? validRows.value.map((r) => r.itemId) : []
}
function syncSelection() {
  const valid = new Set(validRows.value.map((r) => r.itemId))
  const keep = selectedIds.value.filter((id) => valid.has(id))
  if (cartSelectOn.value) {
    selectedIds.value = keep.length ? keep : validRows.value.map((r) => r.itemId)
  } else {
    selectedIds.value = validRows.value.map((r) => r.itemId)
  }
}

function tasteNoteHas(chip) {
  const note = form.tasteNote || ''
  return note.split(/[、,，/\s]+/).map((s) => s.trim()).includes(chip)
}
function toggleTasteChip(chip) {
  const parts = (form.tasteNote || '')
    .split(/[、,，/\s]+/)
    .map((s) => s.trim())
    .filter(Boolean)
  const i = parts.indexOf(chip)
  if (i >= 0) parts.splice(i, 1)
  else parts.push(chip)
  form.tasteNote = parts.join('、')
}
const needAddress = computed(() => {
  const t = form.deliveryType || ''
  return t.includes('配送') || t === '配送到家'
})

const list = ref([])
const addresses = ref([])
const placing = ref(false)
const checkoutVisible = ref(false)
const rechargeVisible = ref(false)
const specVisible = ref(false)
const specFromId = ref(0)
const specPickId = ref(null)
const specAlts = ref([])
const recharging = ref(false)
const rechargeTiers = [50, 100, 200, 500]
const rechargeAmount = ref(100)
const account = ref({})
const preview = ref(null)
const form = reactive({
  deliveryType: '',
  addressId: null,
  receiverName: '',
  receiverPhone: '',
  addressLine: '',
  tag: '家',
  saveAsDefault: false,
  tasteNote: '',
  remark: '',
  invoiceTitle: '',
  couponCode: '',
  offsetPoints: 0,
  payChannel: 'alipay',
  payPassword: '',
  deliveryOn: '',
  slotId: null,
  campaignId: null,
  tableNo: '',
  utensilOpt: '',
  packOpt: '',
  packagingFee: false,
  mergeCode: '',
})
const foodThicken = computed(() => {
  const t = getSchema()?.tradeThicken || {}
  return !!(t.tableNo || t.utensilPack || t.packagingFee || t.tableMerge
    || t.deliveryFeeLadder || t.etaText || t.requiredCategory || t.stallOpenHours)
})
const tableNoLabel = computed(() => getSchema()?.labels?.tableNoLabel || '桌号')
const tableNoHint = computed(() => getSchema()?.labels?.tableNoHint || '')
const utensilOptLabel = computed(() => getSchema()?.labels?.utensilOptLabel || '餐具')
const packOptLabel = computed(() => getSchema()?.labels?.packOptLabel || '打包')
const packagingFeeLabel = computed(() => getSchema()?.labels?.packagingFeeLabel || '包装费')
const packagingFeeHint = computed(() => getSchema()?.labels?.packagingFeeHint || '')
const packagingFeeOn = computed(() => !!getSchema()?.tradeThicken?.packagingFee)
const packagingFeeYuan = computed(() => Number(getSchema()?.packagingFeeYuan || 0))
const mergeCodeOn = computed(() => !!getSchema()?.tradeThicken?.tableMerge)
const mergeCodeLabel = computed(() => getSchema()?.labels?.mergeCodeLabel || '拼单码')
const mergeCodeHint = computed(() => getSchema()?.labels?.mergeCodeHint || '')
const deliveryFeeLabel = computed(() => getSchema()?.labels?.deliveryFeeLabel || '配送费')
const deliveryFeeLadderBody = computed(() => getSchema()?.labels?.deliveryFeeLadderBody || '')
const etaLabel = computed(() => getSchema()?.labels?.etaLabel || '预计送达')
const etaHint = computed(() => getSchema()?.labels?.etaHint || '')
const stallOpenHoursOn = computed(() => !!getSchema()?.tradeThicken?.stallOpenHours)
const stallOpenHoursLabel = computed(() => getSchema()?.labels?.stallOpenHoursLabel || '营业时段')
const stallOpenHoursHint = computed(() => getSchema()?.labels?.stallOpenHoursHint || '')
const stallClosedHint = computed(() => getSchema()?.labels?.stallClosedHint || '')
const requiredCategoryOn = computed(() => !!getSchema()?.tradeThicken?.requiredCategory)
const requiredCategoryLabel = computed(() => getSchema()?.labels?.requiredCategoryLabel || '必选品类')
const requiredCategoryHint = computed(() => getSchema()?.labels?.requiredCategoryHint || '')
const requiredCategoryMissingHint = computed(() => getSchema()?.labels?.requiredCategoryMissingHint || '')
const utensilOpts = computed(() => {
  const raw = getSchema()?.entities?.order?.utensilOpts
  return Array.isArray(raw) ? raw.filter(Boolean) : []
})
const packOpts = computed(() => {
  const raw = getSchema()?.entities?.order?.packOpts
  return Array.isArray(raw) ? raw.filter(Boolean) : []
})
const needTableNo = computed(() => {
  const t = form.deliveryType || ''
  return !!getSchema()?.tradeThicken?.tableNo && t.includes('堂食')
})
function onPackOptChange() {
  if ((form.packOpt || '').includes('打包') && packagingFeeOn.value) {
    form.packagingFee = true
  }
}

const totalYuan = computed(() =>
  selectedValid.value.reduce((s, x) => s + Number(x.lineYuan || 0), 0).toFixed(2),
)

async function loadLoyalty() {
  if (!anyLoyalty.value) {
    account.value = {}
    preview.value = null
    return
  }
  try {
    const me = await http.get('/api/loyalty/me')
    account.value = me.data || {}
  } catch {
    account.value = {}
  }
  await refreshPreview()
}

function openRecharge() {
  rechargeAmount.value = 100
  rechargeVisible.value = true
}

async function doRecharge() {
  if (!rechargeAmount.value) {
    ElMessage.warning('请选择充值金额')
    return
  }
  recharging.value = true
  try {
    const res = await http.post('/api/loyalty/demo-recharge', { amount: rechargeAmount.value })
    account.value = res.data || account.value
    ElMessage.success(`已充值 ¥${Number(rechargeAmount.value).toFixed(0)}`)
    rechargeVisible.value = false
    await refreshPreview()
  } finally {
    recharging.value = false
  }
}

async function refreshPreview() {
  if (!anyLoyalty.value || !list.value.length) {
    preview.value = null
    return
  }
  try {
    const res = await http.post('/api/loyalty/preview', {
      subtotalYuan: Number(totalYuan.value),
      couponCode: form.couponCode?.trim() || undefined,
      offsetPoints: pointsOffsetOn.value ? Number(form.offsetPoints || 0) : undefined,
    })
    preview.value = res.data || null
  } catch {
    preview.value = null
  }
}

async function load() {
  const res = await http.get('/api/cart')
  list.value = res.data || []
  syncSelection()
  await loadLoyalty()
}

watch(totalYuan, () => {
  if (anyLoyalty.value) refreshPreview()
})

watch(
  () => form.offsetPoints,
  () => {
    if (pointsOffsetOn.value) refreshPreview()
  },
)

async function loadAddresses() {
  try {
    const res = await http.get('/api/addresses')
    addresses.value = res.data || []
  } catch {
    addresses.value = []
  }
}

async function saveQty(row, qty) {
  await upsertCart(row.itemId, qty)
  await load()
}

async function remove(row) {
  await removeCart(row.itemId)
  ElMessage.success('已移除')
  load()
}

async function clearInvalid() {
  const res = await http.post('/api/cart/clear-invalid')
  const n = Number(res.data?.removed || 0)
  ElMessage.success(n ? `已清理 ${n} 件` : '没有失效商品')
  await load()
}

function changeSpec(row) {
  const alts = Array.isArray(row.specAlts) ? row.specAlts : []
  if (!alts.length) {
    ElMessage.info(cartNoSpecHint.value)
    return
  }
  specFromId.value = row.itemId
  specAlts.value = alts
  specPickId.value = alts[0].itemId
  specVisible.value = true
}

async function confirmSpec() {
  if (!specPickId.value) {
    ElMessage.warning(cartNoSpecHint.value)
    return
  }
  await http.post('/api/cart/replace', { fromItemId: specFromId.value, toItemId: specPickId.value })
  ElMessage.success('已换规格')
  specVisible.value = false
  await load()
}

async function loadMineCoupons() {
  if (!couponOn.value) {
    mineCoupons.value = []
    return
  }
  try {
    const res = await http.get('/api/coupons/mine', {
      params: { status: 'unused', page: 1, size: 50 },
    })
    mineCoupons.value = res.data?.list || []
  } catch {
    mineCoupons.value = []
  }
}

async function openCheckout() {
  if (!selectedValid.value.length) {
    ElMessage.warning('请先勾选要结算的商品')
    return
  }
  form.deliveryType = deliveryOptions.value[0]
  form.addressId = null
  form.receiverName = ''
  form.receiverPhone = ''
  form.addressLine = ''
  form.tag = tagOptions.value[0] || '家'
  form.saveAsDefault = false
  form.tasteNote = ''
  form.remark = ''
  form.invoiceTitle = ''
  form.couponCode = ''
  form.offsetPoints = 0
  form.tableNo = ''
  form.utensilOpt = utensilOpts.value[0] || ''
  form.packOpt = packOpts.value[0] || ''
  form.packagingFee = false
  form.mergeCode = ''
  await loadAddresses()
  await loadMineCoupons()
  await loadLoyalty()
  try {
    const me = await http.get('/api/profile')
    const extras = me.data?.extras || {}
    const phone = me.data?.phone || ''
    if (isFood.value && extras.pickupType && deliveryOptions.value.includes(extras.pickupType)) {
      form.deliveryType = extras.pickupType
    }
    if (extras.receiverName) form.receiverName = extras.receiverName
    if (extras.allergyNote && isFood.value) form.tasteNote = extras.allergyNote
    if (extras.deliveryAddress) form.addressLine = extras.deliveryAddress
    if (extras.receiveAddress) form.addressLine = extras.receiveAddress
    if (phone && !form.receiverPhone) form.receiverPhone = phone
  } catch { /* ignore */ }
  const def = addresses.value.find((a) => a.isDefault) || addresses.value[0]
  if (def) {
    form.addressId = def.id
    onPickAddress(def.id)
  }
  checkoutVisible.value = true
  if (groupBuy.value) {
    const res = await http.get('/api/group-buys/open')
    groupOpens.value = res.data || []
    form.campaignId = null
  }
  if (customSpecLabel.value) {
    const res = await http.get('/api/line-specs/options')
    specOptions.value = res.data || []
  }
}

function onPickAddress(id) {
  const a = addresses.value.find((x) => x.id === id)
  if (!a) return
  form.receiverName = a.contactName || ''
  form.receiverPhone = a.phone || ''
  form.addressLine = a.addressLine || ''
  form.tag = a.tag || tagOptions.value[0] || '家'
}

async function saveAsAddress() {
  if (!form.receiverName?.trim() || !form.receiverPhone?.trim() || !form.addressLine?.trim()) {
    ElMessage.warning('请先填写收货人、手机与地址')
    return
  }
  const name = form.receiverName.trim()
  const phone = form.receiverPhone.trim()
  const line = form.addressLine.trim()
  const existed = addresses.value.find(
    (a) =>
      String(a.contactName || '').trim() === name
      && String(a.phone || '').trim() === phone
      && String(a.addressLine || '').trim() === line,
  )
  if (existed) {
    form.addressId = existed.id
    onPickAddress(existed.id)
    ElMessage.warning('地址簿中已有相同收货信息')
    return
  }
  const asDefault = form.saveAsDefault || !addresses.value.length
  const res = await http.post('/api/addresses', {
    contactName: name,
    phone,
    addressLine: line,
    tag: normalizeAddressTag(form.tag),
    isDefault: asDefault,
  })
  await loadAddresses()
  if (res.data?.id) {
    form.addressId = res.data.id
    ElMessage.success(asDefault ? '已保存并设为默认' : '已保存到地址簿')
  }
}

function extraOf(row) {
  const id = String(row?.itemId)
  if (!lineExtraMap[id]) lineExtraMap[id] = { customText: '', specChoice: '', attachUrl: '', weightQty: null }
  return lineExtraMap[id]
}

async function onCustomImage(row, opt) {
  const fd = new FormData()
  fd.append('file', opt.file)
  const res = await http.post('/api/upload', fd)
  extraOf(row).attachUrl = res.data?.url || ''
  ElMessage.success('图片已上传')
}

async function loadWindow() {
  if (!deliveryWindow.value || !form.deliveryOn) {
    windowSlots.value = []
    windowRate.value = 1
    windowPriceName.value = ''
    return
  }
  const res = await http.get('/api/delivery-windows/options', { params: { day: form.deliveryOn } })
  windowSlots.value = res.data?.slots || []
  windowRate.value = Number(res.data?.priceRate || 1)
  windowPriceName.value = res.data?.priceName || ''
  if (!windowSlots.value.some((s) => s.id === form.slotId && !s.full)) form.slotId = null
}

async function submitOrder() {
  if (deliveryWindow.value) {
    if (!form.deliveryOn) {
      ElMessage.warning('请选择配送日期')
      return
    }
    if (!form.slotId) {
      ElMessage.warning('请选择配送时段')
      return
    }
  }
  if (lineCustom.value) {
    for (const row of selectedValid.value) {
      const ex = extraOf(row)
      if (!String(ex.customText || '').trim()) {
        ElMessage.warning(`请填写「${row.title}」的${customTextLabel.value}`)
        return
      }
      if (customSpecLabel.value && !String(ex.specChoice || '').trim()) {
        ElMessage.warning(`请选择「${row.title}」的${customSpecLabel.value}`)
        return
      }
      if (customImageLabel.value && !ex.attachUrl) {
        ElMessage.warning(`请上传「${row.title}」的${customImageLabel.value}`)
        return
      }
    }
  }
  if (weighSale.value) {
    for (const row of weightRows.value) {
      if (!(Number(extraOf(row).weightQty) > 0)) {
        ElMessage.warning(`请填写「${row.title}」的重量`)
        return
      }
    }
  }
  if (needAddress.value) {
    if (!form.receiverName?.trim() || !form.receiverPhone?.trim() || !form.addressLine?.trim()) {
      ElMessage.warning('请填写收货人、手机与详细地址')
      return
    }
  }
  if (needTableNo.value && !form.tableNo?.trim()) {
    ElMessage.warning(`请填写${tableNoLabel.value}`)
    return
  }
  if (demoPay.value) {
    if (!form.payChannel) {
      ElMessage.warning('请选择支付方式')
      return
    }
    if (!form.payPassword || form.payPassword.trim().length < 4) {
      ElMessage.warning('请输入支付密码（至少 4 位）')
      return
    }
  }
  if (walletOn.value && preview.value?.balanceEnough === false) {
    ElMessage.warning(preview.value?.message || '账户余额不足')
    return
  }
  placing.value = true
  try {
    const payload = {
      deliveryType: form.deliveryType,
      addressId: form.addressId || undefined,
      receiverName: form.receiverName.trim(),
      receiverPhone: form.receiverPhone.trim(),
      addressLine: form.addressLine.trim(),
      tasteNote: form.tasteNote.trim(),
      remark: form.remark.trim(),
      couponCode: form.couponCode.trim() || undefined,
      offsetPoints: pointsOffsetOn.value && form.offsetPoints > 0 ? form.offsetPoints : undefined,
      deliveryOn: deliveryWindow.value ? form.deliveryOn : undefined,
      slotId: deliveryWindow.value ? form.slotId : undefined,
      campaignId: groupBuy.value ? form.campaignId : undefined,
      itemIds: selectedValid.value.map((r) => r.itemId),
      lineExtras: lineCustom.value || weighSale.value
        ? selectedValid.value.map((row) => ({
          itemId: row.itemId,
          customText: extraOf(row).customText.trim(),
          specChoice: extraOf(row).specChoice.trim(),
          attachUrl: extraOf(row).attachUrl,
          weightQty: extraOf(row).weightQty,
        }))
        : undefined,
    }
    if (demoPay.value) {
      payload.payChannel = form.payChannel
      payload.payPassword = form.payPassword.trim()
    }
    if (invoiceTitleOn.value && form.invoiceTitle.trim()) {
      payload.invoiceTitle = form.invoiceTitle.trim()
    }
    if (isFood.value && foodThicken.value) {
      payload.tableNo = form.tableNo.trim() || undefined
      payload.utensilOpt = form.utensilOpt || undefined
      payload.packOpt = form.packOpt || undefined
      payload.mergeCode = form.mergeCode.trim() || undefined
      payload.packagingFee = !!form.packagingFee
    } else if (packagingFeeOn.value) {
      payload.packagingFee = !!form.packagingFee
    }
    const placed = await http.post('/api/orders', payload)
    const splitMsg =
      placed?.data && typeof placed.data.message === 'string' ? placed.data.message.trim() : ''
    ElMessage.success(
      splitMsg || (demoPay.value ? '支付成功，已下单' : '下单成功'),
    )
    checkoutVisible.value = false
    form.payPassword = ''
    router.push('/orders')
  } finally {
    placing.value = false
  }
}

onMounted(load)
