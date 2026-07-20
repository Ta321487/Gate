<template>
  <div>
    <section class="hero">
      <h1>{{ cartLabel }}</h1>
      <p>确认数量后提交{{ orderNoun }}。</p>
      <div class="tools">
        <el-button @click="load">刷新</el-button>
        <el-button type="primary" :disabled="!list.length" :loading="placing" @click="openCheckout">
          提交{{ orderNoun }}
        </el-button>
      </div>
    </section>

    <el-table :data="list" stripe empty-text="购物车为空，去浏览加购吧">
      <el-table-column prop="title" label="名称" min-width="160" />
      <el-table-column prop="priceYuan" label="单价" width="100" />
      <el-table-column label="数量" width="140">
        <template #default="{ row }">
          <el-input-number v-model="row.qty" :min="1" :max="99" size="small" @change="(v) => saveQty(row, v)" />
        </template>
      </el-table-column>
      <el-table-column prop="lineYuan" label="小计" width="100" />
      <el-table-column label="操作" width="90">
        <template #default="{ row }">
          <el-button link type="danger" @click="remove(row)">移除</el-button>
        </template>
      </el-table-column>
    </el-table>
    <div v-if="list.length" class="total">
      <template v-if="anyLoyalty">
        <div v-if="walletOn" class="loy-line">演示余额 ¥{{ Number(account.balanceYuan || 0).toFixed(2) }}</div>
        <div v-if="pointsOn" class="loy-line">积分 {{ account.points || 0 }}</div>
        <div v-if="tierOn && account.memberTierLabel" class="loy-line">会员 {{ account.memberTierLabel }}</div>
      </template>
      <div>合计 ¥{{ totalYuan }}</div>
      <template v-if="preview && (discountOn || tierOn)">
        <div v-if="Number(preview.discountYuan) > 0" class="loy-line muted">满减 −¥{{ Number(preview.discountYuan).toFixed(2) }}</div>
        <div v-if="Number(preview.tierDiscountRate) < 1" class="loy-line muted">
          会员折扣 ×{{ preview.tierDiscountRate }}
        </div>
        <div class="payable">应付 ¥{{ Number(preview.payableYuan || totalYuan).toFixed(2) }}</div>
        <div v-if="walletOn && preview.balanceEnough === false" class="warn">演示余额不足，请联系管理员充值</div>
      </template>
    </div>

    <el-dialog v-model="checkoutVisible" :title="`提交${orderNoun}`" width="520px" destroy-on-close>
      <el-form label-position="top">
        <el-form-item label="履约方式" required>
          <el-select v-model="form.deliveryType" style="width: 100%">
            <el-option v-for="opt in deliveryOptions" :key="opt" :label="opt" :value="opt" />
          </el-select>
        </el-form-item>
        <template v-if="needAddress">
          <el-form-item label="收货地址" required>
            <el-select
              v-model="form.addressId"
              clearable
              filterable
              placeholder="选择已有地址"
              style="width: 100%"
              @change="onPickAddress"
            >
              <el-option
                v-for="a in addresses"
                :key="a.id"
                :label="`${a.isDefault ? '★ ' : ''}${a.tag || '地址'} · ${a.contactName} ${a.phone} · ${a.addressLine}`"
                :value="a.id"
              />
            </el-select>
            <div class="addr-links">
              <router-link class="link" to="/addresses">管理地址簿</router-link>
            </div>
          </el-form-item>
          <div class="addr-grid">
            <el-form-item label="收货人" required>
              <el-input v-model="form.receiverName" maxlength="32" />
            </el-form-item>
            <el-form-item label="手机" required>
              <el-input v-model="form.receiverPhone" maxlength="20" />
            </el-form-item>
          </div>
          <el-form-item label="详细地址" required>
            <el-input v-model="form.addressLine" type="textarea" :rows="2" maxlength="200" />
          </el-form-item>
          <el-form-item label="地址标签">
            <el-select
              v-model="form.tag"
              filterable
              allow-create
              default-first-option
              placeholder="家 / 学校 / 公司…"
              style="width: 100%"
            >
              <el-option v-for="t in tagOptions" :key="t" :label="t" :value="t" />
            </el-select>
          </el-form-item>
          <el-form-item>
            <el-checkbox v-model="form.saveAsDefault">保存时设为默认</el-checkbox>
            <el-button text type="primary" class="save-addr" @click="saveAsAddress">保存到地址簿</el-button>
          </el-form-item>
        </template>
        <el-form-item v-if="isFood" :label="tasteLabel">
          <el-input
            v-model="form.tasteNote"
            type="textarea"
            :rows="2"
            maxlength="200"
            :placeholder="tastePlaceholder"
          />
        </el-form-item>
        <el-form-item label="订单备注">
          <el-input v-model="form.remark" maxlength="200" placeholder="选填" />
        </el-form-item>
        <div v-if="anyLoyalty && preview" class="checkout-loy">
          <p v-if="walletOn">演示余额 ¥{{ Number(preview.balanceYuan || 0).toFixed(2) }}（非真支付）</p>
          <p v-if="Number(preview.discountYuan) > 0">满减 −¥{{ Number(preview.discountYuan).toFixed(2) }}</p>
          <p class="payable">应付 ¥{{ Number(preview.payableYuan || totalYuan).toFixed(2) }}</p>
          <p v-if="walletOn && preview.balanceEnough === false" class="warn">余额不足，无法提交</p>
        </div>
      </el-form>
      <template #footer>
        <el-button @click="checkoutVisible = false">取消</el-button>
        <el-button
          type="primary"
          :loading="placing"
          :disabled="walletOn && preview?.balanceEnough === false"
          @click="submitOrder"
        >确认提交</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import http from '../../api/http'
import {
  anyLoyaltyEnabled,
  hasTrait,
  getSchema,
  isMemberTierEnabled,
  isPointsEnabled,
  isSpendDiscountEnabled,
  isWalletEnabled,
  menuLabel,
} from '../../utils/domainSchema.js'
import { addressTagOptions, normalizeAddressTag } from '../../utils/addressTags.js'

const router = useRouter()
const cartLabel = menuLabel('user', 'cart', '购物车')
const orderNoun = computed(() => getSchema()?.entities?.order?.label || '订单')
const isFood = computed(() => hasTrait('food'))
const anyLoyalty = computed(() => anyLoyaltyEnabled())
const walletOn = computed(() => isWalletEnabled())
const pointsOn = computed(() => isPointsEnabled())
const discountOn = computed(() => isSpendDiscountEnabled())
const tierOn = computed(() => isMemberTierEnabled())
const tagOptions = computed(() => addressTagOptions())
const deliveryOptions = computed(() =>
  isFood.value ? ['外卖配送', '到店自取', '堂食'] : ['配送到家', '到店自提'],
)
const tasteLabel = computed(() => '口味 / 忌口')
const tastePlaceholder = computed(() => '如：少辣、不要香菜、多糖少冰')
const needAddress = computed(() => {
  const t = form.deliveryType || ''
  return t.includes('配送') || t === '配送到家'
})

const list = ref([])
const addresses = ref([])
const placing = ref(false)
const checkoutVisible = ref(false)
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
})

const totalYuan = computed(() =>
  list.value.reduce((s, x) => s + Number(x.lineYuan || 0), 0).toFixed(2),
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

async function refreshPreview() {
  if (!anyLoyalty.value || !list.value.length) {
    preview.value = null
    return
  }
  try {
    const res = await http.post('/api/loyalty/preview', { subtotalYuan: Number(totalYuan.value) })
    preview.value = res.data || null
  } catch {
    preview.value = null
  }
}

async function load() {
  const res = await http.get('/api/cart')
  list.value = res.data || []
  await loadLoyalty()
}

watch(totalYuan, () => {
  if (anyLoyalty.value) refreshPreview()
})

async function loadAddresses() {
  try {
    const res = await http.get('/api/addresses')
    addresses.value = res.data || []
  } catch {
    addresses.value = []
  }
}

async function saveQty(row, qty) {
  await http.post('/api/cart', { itemId: row.itemId, qty })
  await load()
}

async function remove(row) {
  await http.delete(`/api/cart/${row.itemId}`)
  ElMessage.success('已移除')
  load()
}

async function openCheckout() {
  form.deliveryType = deliveryOptions.value[0]
  form.addressId = null
  form.receiverName = ''
  form.receiverPhone = ''
  form.addressLine = ''
  form.tag = tagOptions.value[0] || '家'
  form.saveAsDefault = false
  form.tasteNote = ''
  form.remark = ''
  await loadAddresses()
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
  const asDefault = form.saveAsDefault || !addresses.value.length
  const res = await http.post('/api/addresses', {
    contactName: form.receiverName.trim(),
    phone: form.receiverPhone.trim(),
    addressLine: form.addressLine.trim(),
    tag: normalizeAddressTag(form.tag),
    isDefault: asDefault,
  })
  await loadAddresses()
  if (res.data?.id) {
    form.addressId = res.data.id
    ElMessage.success(asDefault ? '已保存并设为默认' : '已保存到地址簿')
  }
}

async function submitOrder() {
  if (needAddress.value) {
    if (!form.receiverName?.trim() || !form.receiverPhone?.trim() || !form.addressLine?.trim()) {
      ElMessage.warning('请填写收货人、手机与详细地址')
      return
    }
  }
  if (walletOn.value && preview.value?.balanceEnough === false) {
    ElMessage.warning(preview.value?.message || '演示余额不足')
    return
  }
  placing.value = true
  try {
    await http.post('/api/orders', {
      deliveryType: form.deliveryType,
      addressId: form.addressId || undefined,
      receiverName: form.receiverName.trim(),
      receiverPhone: form.receiverPhone.trim(),
      addressLine: form.addressLine.trim(),
      tasteNote: form.tasteNote.trim(),
      remark: form.remark.trim(),
    })
    ElMessage.success('下单成功')
    checkoutVisible.value = false
    router.push('/orders')
  } finally {
    placing.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.hero { margin-bottom: 16px; display: flex; flex-wrap: wrap; justify-content: space-between; gap: 12px; }
.hero h1 { margin: 0 0 6px; font-size: 22px; }
.hero p { margin: 0; color: #64748b; font-size: 13px; width: 100%; }
.tools { display: flex; gap: 8px; }
.total { margin-top: 14px; text-align: right; font-weight: 700; font-size: 16px; }
.loy-line { font-weight: 500; font-size: 13px; color: #475569; margin-bottom: 4px; }
.loy-line.muted { color: #64748b; }
.payable { margin-top: 4px; color: #0f766e; }
.warn { color: #b91c1c; font-size: 13px; font-weight: 600; margin-top: 4px; }
.checkout-loy {
  margin-top: 8px;
  padding: 10px 12px;
  background: #f8fafc;
  border-radius: 8px;
  font-size: 13px;
  color: #334155;
}
.checkout-loy p { margin: 0 0 4px; }
.checkout-loy .payable { font-weight: 700; font-size: 15px; }
.addr-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0 12px;
}
.addr-links { margin-top: 4px; }
.link { font-size: 13px; color: var(--el-color-primary); text-decoration: none; }
.save-addr { margin-left: 8px; }
@media (max-width: 520px) {
  .addr-grid { grid-template-columns: 1fr; }
}
</style>
