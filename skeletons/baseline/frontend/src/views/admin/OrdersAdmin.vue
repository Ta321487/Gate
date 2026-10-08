<template>
  <div>
    <div class="toolbar">
      <el-select v-model="status" clearable placeholder="全部状态" style="width:140px" @change="load">
        <el-option v-for="(lab, key) in states" :key="key" :label="lab" :value="key" />
      </el-select>
      <el-button type="primary" @click="load">查询</el-button>
      <el-button :disabled="!list.length" @click="exportCsv">导出 CSV</el-button>
    </div>
    <p v-if="isCinema && ticketRefundCutoffHint" class="muted">{{ ticketRefundCutoffHint }}</p>
    <div class="table-scroll">
    <el-table :data="list" stripe>
      <el-table-column prop="id" label="编号" width="80" />
      <el-table-column :label="userLabel" width="120">
        <template #default="{ row }">{{ personLabel(row) }}</template>
      </el-table-column>
      <el-table-column prop="totalYuan" label="金额" width="100">
        <template #default="{ row }">¥{{ Number(row.totalYuan || 0).toFixed(2) }}</template>
      </el-table-column>
      <el-table-column v-if="!isStay && !isCinema" :label="fulfillLabel" min-width="160" show-overflow-tooltip>
        <template #default="{ row }">
          <span v-if="row.deliveryType">{{ row.deliveryType }}</span>
          <span v-if="row.deliveryType && (row.addressLine || row.receiverName)"> · </span>
          <span v-if="row.addressLine || row.receiverName">
            {{ row.receiverName }} {{ row.receiverPhone }} {{ row.addressLine }}
          </span>
          <span v-if="!row.addressLine && !row.receiverName && !row.deliveryType">—</span>
        </template>
      </el-table-column>
      <el-table-column v-if="isFood" :label="tableNoLabel" width="90" show-overflow-tooltip>
        <template #default="{ row }">{{ row.tableNo || '—' }}</template>
      </el-table-column>
      <el-table-column v-if="isFood" :label="pickupNoLabel" width="100" show-overflow-tooltip>
        <template #default="{ row }">{{ row.pickupCode || '—' }}</template>
      </el-table-column>
      <el-table-column v-if="isFood" :label="tasteNoteLabel" min-width="120" show-overflow-tooltip>
        <template #default="{ row }">{{ row.tasteNote || '—' }}</template>
      </el-table-column>
      <el-table-column v-if="isFood && mergeCodeOn" :label="mergeCodeLabel" width="100" show-overflow-tooltip>
        <template #default="{ row }">{{ row.mergeCode || '—' }}</template>
      </el-table-column>
      <el-table-column v-if="isFood && riderPoolOn" :label="riderClaimLabel" width="110" show-overflow-tooltip>
        <template #default="{ row }">{{ row.riderUsername || '—' }}</template>
      </el-table-column>
      <el-table-column v-if="isCinema" :label="pickupCodeLabel" min-width="120" show-overflow-tooltip>
        <template #default="{ row }">{{ row.pickupCode || '—' }}</template>
      </el-table-column>
      <el-table-column v-if="isCinema" :label="cinemaNoticeLabel" width="110">
        <template #default="{ row }">{{ row.noticeAgreed ? '已确认' : '—' }}</template>
      </el-table-column>
      <el-table-column v-if="isCinema && refundFeeOn" :label="refundFeeLabel" width="110">
        <template #default="{ row }">
          {{ Number(row.refundFeeYuan || 0) > 0 ? `¥${Number(row.refundFeeYuan).toFixed(2)}` : '—' }}
        </template>
      </el-table-column>
      <el-table-column v-if="invoiceOn" :label="invoiceStatusLabel" min-width="140" show-overflow-tooltip>
        <template #default="{ row }">
          <template v-if="row.invoiceTitle || row.invoiceStatus">
            {{ row.invoiceTitle || '—' }} · {{ invoiceStatusText(row.invoiceStatus) }}
          </template>
          <template v-else>—</template>
        </template>
      </el-table-column>
      <el-table-column v-if="invoiceOn" :label="invoiceStatusLabel" min-width="140" show-overflow-tooltip>
        <template #default="{ row }">
          <template v-if="row.invoiceTitle || row.invoiceStatus">
            {{ row.invoiceTitle || '—' }} · {{ invoiceStatusText(row.invoiceStatus) }}
          </template>
          <template v-else>—</template>
        </template>
      </el-table-column>
      <el-table-column v-if="deliveryWindow" label="配送时段" min-width="160">
        <template #default="{ row }">
          <span v-if="row.slotLabel">{{ row.deliveryOn }} {{ row.slotLabel }}</span>
          <span v-else>—</span>
        </template>
      </el-table-column>
      <el-table-column v-if="lineCustom" label="定制内容" min-width="220">
        <template #default="{ row }">
          <div v-for="ln in row.lines || []" :key="ln.id">
            {{ ln.title }}：{{ ln.customText || '—' }}
            <span v-if="ln.specChoice"> / {{ ln.specChoice }}</span>
            <a v-if="ln.attachUrl" :href="ln.attachUrl" target="_blank" rel="noopener noreferrer">图片</a>
          </div>
        </template>
      </el-table-column>
      <el-table-column v-if="blindBox" label="抽中" min-width="160">
        <template #default="{ row }">
          <div v-for="ln in row.lines || []" :key="ln.id">
            <span v-if="ln.drawTitle">{{ ln.title }}：{{ ln.drawTitle }}</span>
          </div>
        </template>
      </el-table-column>
      <el-table-column v-if="!isStay && !isCinema" :label="shipLabel" min-width="120" show-overflow-tooltip>
        <template #default="{ row }">
          <template v-if="isFood">
            <span v-if="row.pickupCode">{{ pickupCodeLabel }}:{{ row.pickupCode }}</span>
            <span v-else>—</span>
          </template>
          <template v-else>
            <span v-if="row.trackingNo">单号:{{ row.trackingNo }}</span>
            <span v-else>—</span>
          </template>
        </template>
      </el-table-column>
      <el-table-column prop="status" label="状态" width="110">
        <template #default="{ row }">
          {{ states[row.status] || row.status }}
          <span v-if="row.partialShip"> · {{ partialShipLabel }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="remark" :label="orderRemarkLabel" min-width="120" show-overflow-tooltip>
        <template #default="{ row }">{{ row.remark || '—' }}</template>
      </el-table-column>
      <el-table-column v-if="showLoyaltyCols" label="优惠" width="90">
        <template #default="{ row }">
          <span v-if="Number(row.discountYuan) > 0">¥{{ row.discountYuan }}</span>
          <span v-else>—</span>
        </template>
      </el-table-column>
      <el-table-column v-if="showLoyaltyCols" label="获积分" width="80">
        <template #default="{ row }">{{ Number(row.pointsEarned) > 0 ? row.pointsEarned : '—' }}</template>
      </el-table-column>
      <el-table-column label="售后" min-width="160" show-overflow-tooltip>
        <template #default="{ row }">
          <span v-if="row.refundStatus">
            {{ refundLabel(row.refundStatus) }}
            <template v-if="row.refundType"> · {{ refundTypeLabelOf(row.refundType) }}</template>
            <template v-if="row.refundReason"> · {{ row.refundReason }}</template>
            <template v-if="row.refundTrackingNo"> · {{ row.refundTrackingNo }}</template>
          </span>
          <span v-else>—</span>
        </template>
      </el-table-column>
      <el-table-column label="明细" min-width="200" show-overflow-tooltip>
        <template #default="{ row }">
          {{ formatOrderLines(row.lines) }}
        </template>
      </el-table-column>
      <el-table-column prop="createdAt" label="下单时间" width="170" />
      <el-table-column label="操作" min-width="220" fixed="right">
        <template #default="{ row }">
          <div class="table-ops">
          <el-button
            v-if="riderPoolOn && canClaimRider(row)"
            link
            type="primary"
            @click="claimRider(row)"
          >{{ riderClaimLabel }}</el-button>
          <el-button
            v-if="!marketplace && row.status === 'pending'"
            link
            type="primary"
            @click="act(row, 'confirm')"
          >{{ confirmVerb }}</el-button>
          <el-button
            v-if="row.status === 'confirmed'"
            link
            type="primary"
            @click="act(row, 'ship')"
          >{{ shipVerb }}</el-button>
          <el-button
            v-if="marketplace && row.status === 'shipped'"
            link
            type="primary"
            @click="act(row, 'transit')"
          >运输中</el-button>
          <el-button
            v-if="marketplace && (row.status === 'shipped' || row.status === 'in_transit')"
            link
            type="primary"
            @click="act(row, 'sign')"
          >已签收</el-button>
          <el-button
            v-if="canComplete(row)"
            link
            type="success"
            @click="act(row, 'complete')"
          >{{ completeVerb }}</el-button>
          <el-button
            v-if="(!marketplace && row.status === 'pending') || row.status === 'confirmed'"
            link
            type="danger"
            @click="act(row, 'cancel')"
          >取消</el-button>
          <el-button
            v-if="row.refundStatus === 'pending'"
            link
            type="success"
            @click="decideRefund(row, true)"
          >通过售后</el-button>
          <el-button
            v-if="row.refundStatus === 'pending'"
            link
            type="danger"
            @click="decideRefund(row, false)"
          >驳回售后</el-button>
          <el-button
            v-if="canFillRefundTracking(row)"
            link
            type="primary"
            @click="fillRefundTracking(row)"
          >{{ refundTrackingLabel }}</el-button>
          <el-button
            v-if="canShowRefundTrace(row)"
            link
            type="primary"
            @click="openRefundTrace(row)"
          >{{ refundTraceLabel }}</el-button>
          <el-button
            v-if="canChangeAddress(row)"
            link
            type="primary"
            @click="openChangeAddress(row)"
          >{{ changeAddressLabel }}</el-button>
          <el-button
            v-if="receiptPrintOn"
            link
            type="primary"
            @click="printReceipt(row)"
          >{{ orderReceiptPrintLabel }}</el-button>
          <el-button
            v-if="canAddShipNode(row)"
            link
            type="primary"
            @click="openShipNode(row)"
          >{{ shipNodeLabel }}</el-button>
          <el-button
            v-if="canVerifyReceive(row)"
            link
            type="primary"
            @click="openVerifyReceive(row)"
          >{{ receiveCodeVerifyLabel }}</el-button>
          <el-button
            v-if="canSetWarranty(row)"
            link
            type="primary"
            @click="openWarranty(row)"
          >{{ warrantyLabel }}</el-button>
          <el-button
            v-if="canIssueInvoice(row)"
            link
            type="primary"
            @click="issueInvoice(row)"
          >{{ invoiceIssueLabel }}</el-button>
          <el-button
            v-if="canDownloadInvoice(row)"
            link
            type="primary"
            @click="downloadInvoice(row)"
          >{{ invoiceDownloadLabel }}</el-button>
          <el-button
            v-if="canSetRefundFee(row)"
            link
            type="primary"
            @click="openRefundFee(row)"
          >{{ refundFeeLabel }}</el-button>
          <span v-if="marketplace && row.status === 'pending'" class="ops-hint">待买家付款</span>
          <span v-else-if="!hasOrderOps(row)" class="ops-empty">—</span>
          </div>
        </template>
      </el-table-column>
    </el-table>
    </div>
    <div class="pager">
      <el-pagination
        v-model:current-page="page"
        v-model:page-size="size"
        background
        layout="total, sizes, prev, pager, next"
        :page-sizes="[10, 20, 50]"
        :total="total"
        @current-change="load"
        @size-change="load"
      />
    </div>

    <el-dialog v-model="addrVisible" :title="changeAddressLabel" width="420px" destroy-on-close>
      <p v-if="changeAddressHint" class="ops-hint">{{ changeAddressHint }}</p>
      <el-form label-position="top">
        <el-form-item label="收货人">
          <el-input v-model="addrForm.receiverName" maxlength="32" />
        </el-form-item>
        <el-form-item label="电话">
          <el-input v-model="addrForm.receiverPhone" maxlength="20" />
        </el-form-item>
        <el-form-item label="地址">
          <el-input v-model="addrForm.addressLine" type="textarea" :rows="2" maxlength="255" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="addrVisible = false">取消</el-button>
        <el-button type="primary" :loading="addrSaving" @click="submitChangeAddress">保存</el-button>
      </template>
    </el-dialog>
    <OrderTraceDialog
      v-model="refundTraceVisible"
      :order-id="refundTraceOrderId"
      endpoint="refund-trace"
      :title="refundTraceLabel"
      :empty-text="refundTraceEmpty"
    />
    <el-dialog v-model="shipNodeVisible" :title="shipNodeLabel" width="440px" destroy-on-close>
      <p v-if="shipNodeHint" class="ops-hint">{{ shipNodeHint }}</p>
      <el-form label-position="top">
        <el-form-item label="进度说明" required>
          <el-input v-model="shipNodeForm.title" maxlength="64" placeholder="如：已到中转站" />
        </el-form-item>
        <el-form-item label="补充说明">
          <el-input v-model="shipNodeForm.detail" type="textarea" :rows="2" maxlength="255" />
        </el-form-item>
        <el-form-item label="发生时间">
          <el-date-picker
            v-model="shipNodeForm.happenedAt"
            type="datetime"
            value-format="YYYY-MM-DD HH:mm:ss"
            placeholder="选择时间"
            style="width:100%"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="shipNodeVisible = false">取消</el-button>
        <el-button type="primary" :loading="shipNodeSaving" @click="submitShipNode">保存</el-button>
      </template>
    </el-dialog>
    <el-dialog v-model="warrantyVisible" :title="warrantyLabel" width="400px" destroy-on-close>
      <p v-if="warrantyHint" class="ops-hint">{{ warrantyHint }}</p>
      <el-form label-position="top">
        <el-form-item :label="warrantyLabel" required>
          <el-date-picker
            v-model="warrantyForm.until"
            type="date"
            value-format="YYYY-MM-DD"
            placeholder="选择日期"
            style="width:100%"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="warrantyVisible = false">取消</el-button>
        <el-button type="primary" :loading="warrantySaving" @click="submitWarranty">保存</el-button>
      </template>
    </el-dialog>
    <el-dialog v-model="refundFeeVisible" :title="refundFeeLabel" width="400px" destroy-on-close>
      <p v-if="refundFeeHint" class="ops-hint">{{ refundFeeHint }}</p>
      <el-form label-position="top">
        <el-form-item :label="refundFeeLabel" required>
          <el-input-number v-model="refundFeeForm.fee" :min="0" :precision="2" :step="1" style="width:100%" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="refundFeeVisible = false">取消</el-button>
        <el-button type="primary" :loading="refundFeeSaving" @click="submitRefundFee">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import http from '../../api/http'
import { hasTrait, hasCap, getSchema, isPointsEnabled, isSpendDiscountEnabled, personLabel, roleLabel } from '../../utils/domainSchema.js'
import { downloadCsv } from '../../utils/csvDownload.js'
import { printOrderReceipt } from '../../utils/orderReceiptPrint.js'
import { printOrderInvoice } from '../../utils/orderInvoicePrint.js'
import OrderTraceDialog from '../../components/OrderTraceDialog.vue'

const order = computed(() => getSchema()?.entities?.order || {})
const states = computed(() => order.value.states || {})
const userLabel = computed(() => roleLabel('user', '用户'))
const isFood = computed(() => hasTrait('food'))
const lineCustom = computed(() => hasCap('line_custom'))
const deliveryWindow = computed(() => hasCap('delivery_window'))
const blindBox = computed(() => hasCap('blind_box'))
const isStay = computed(
  () =>
    hasTrait('slotHotel')
    || hasTrait('slotCarrent')
    || order.value.fulfillMode === 'stay'
    || order.value.fulfillMode === 'rental',
)
const isCinema = computed(
  () => hasTrait('seatSelect') || order.value.fulfillMode === 'cinema',
)
const showLoyaltyCols = computed(() => isPointsEnabled() || isSpendDiscountEnabled())
const fulfillLabel = computed(() => {
  const fromSchema = getSchema()?.labels?.orderFulfillColumnLabel
  if (fromSchema) return fromSchema
  return isFood.value ? '配送' : '收货信息'
})
const orderRemarkLabel = computed(() => getSchema()?.labels?.orderRemarkLabel || '备注')
const tasteNoteLabel = computed(() => getSchema()?.labels?.tasteNoteLabel || '口味')
const pickupCodeLabel = computed(() => getSchema()?.labels?.pickupCodeLabel || (isFood.value ? '取餐码' : '取票码'))
const pickupNoLabel = computed(() => getSchema()?.labels?.pickupNoLabel || pickupCodeLabel.value)
const tableNoLabel = computed(() => getSchema()?.labels?.tableNoLabel || '桌号')
const mergeCodeLabel = computed(() => getSchema()?.labels?.mergeCodeLabel || '拼单码')
const mergeCodeOn = computed(() => !!getSchema()?.tradeThicken?.tableMerge)
const riderPoolOn = computed(() => !!getSchema()?.tradeThicken?.riderPool)
const riderClaimLabel = computed(() => getSchema()?.labels?.riderClaimLabel || '接单配送')
const cinemaNoticeLabel = computed(() => getSchema()?.labels?.cinemaNoticeLabel || '观影须知')
const ticketRefundCutoffHint = computed(
  () => getSchema()?.labels?.ticketRefundCutoffHint || '',
)
const shipLabel = computed(() => {
  const fromSchema = getSchema()?.labels?.orderShipFieldLabel
  if (fromSchema) return fromSchema
  return isFood.value ? pickupCodeLabel.value : '物流单号'
})
const shipVerb = computed(() => {
  if (order.value.verbs?.ship) return order.value.verbs.ship
  if (order.value.fulfillMode === 'rental' || hasTrait('slotCarrent')) return '办理取车'
  if (isStay.value) return '办理入住'
  if (isCinema.value) return '出票'
  return isFood.value ? '出餐' : '发货'
})

function formatOrderLine(x) {
  const yuan = Number((x.lineYuan ?? x.priceYuan * x.qty) || 0).toFixed(2)
  return `${x.title} × ${x.qty}（¥${yuan}）`
}

function formatOrderLines(lines) {
  return (lines || []).map(formatOrderLine).join('；')
}

const confirmVerb = computed(() => {
  if (order.value.verbs?.confirm) return order.value.verbs.confirm
  return isFood.value ? '接单' : '确认'
})
const completeVerb = computed(() => {
  if (order.value.verbs?.complete) return order.value.verbs.complete
  return '完成'
})
const marketplace = computed(() => !!getSchema()?.shopMarketplace)
const thicken = computed(() => getSchema()?.tradeThicken || {})
const changeAddressOn = computed(() => !!thicken.value.changeAddress)
const changeAddressLabel = computed(() => getSchema()?.labels?.changeAddressLabel || '修改地址')
const changeAddressHint = computed(() => getSchema()?.labels?.changeAddressHint || '')
const receiptPrintOn = computed(() => !!thicken.value.orderReceiptPrint)
const orderReceiptPrintLabel = computed(() => getSchema()?.labels?.orderReceiptPrintLabel || '打印小票')
const refundTrackingOn = computed(() => !!thicken.value.refundTracking)
const refundTraceOn = computed(() => !!thicken.value.refundTrace)
const refundTrackingLabel = computed(() => getSchema()?.labels?.refundTrackingLabel || '退货物流单号')
const refundTrackingHint = computed(() => getSchema()?.labels?.refundTrackingHint || '')
const refundTraceLabel = computed(() => getSchema()?.labels?.refundTraceLabel || '售后进度')
const refundTraceEmpty = computed(() => getSchema()?.labels?.refundTraceEmpty || '暂无售后进度')
const refundTypeRefundOnly = computed(() => getSchema()?.labels?.refundTypeRefundOnly || '仅退款')
const refundTypeReturnRefund = computed(
  () => getSchema()?.labels?.refundTypeReturnRefund || '退货退款',
)
const refundTypeExchange = computed(() => getSchema()?.labels?.refundTypeExchange || '换货')
const refundTypeExchangeOnly = computed(
  () => getSchema()?.labels?.refundTypeExchangeOnly || '仅换货',
)
const shipNodesOn = computed(() => !!thicken.value.shipNodes)
const shipNodeLabel = computed(() => getSchema()?.labels?.shipNodeLabel || '登记物流进度')
const shipNodeHint = computed(() => getSchema()?.labels?.shipNodeHint || '')
const partialShipOn = computed(() => !!thicken.value.partialShip)
const partialShipLabel = computed(() => getSchema()?.labels?.partialShipLabel || '部分发货')
const partialShipHint = computed(() => getSchema()?.labels?.partialShipHint || '')
const receiveCodeOn = computed(() => !!thicken.value.receiveCode)
const receiveCodeVerifyLabel = computed(
  () => getSchema()?.labels?.receiveCodeVerifyLabel || '核销收货码',
)
const receiveCodeHint = computed(() => getSchema()?.labels?.receiveCodeHint || '')
const warrantyOn = computed(() => !!thicken.value.warranty)
const warrantyLabel = computed(() => getSchema()?.labels?.warrantyLabel || '延保至')
const warrantyHint = computed(() => getSchema()?.labels?.warrantyHint || '')
const invoiceOn = computed(() => !!(thicken.value.invoiceTitle || thicken.value.invoiceStatus))
const invoiceStatusLabel = computed(() => getSchema()?.labels?.invoiceStatusLabel || '开票状态')
const invoiceStatusPending = computed(() => getSchema()?.labels?.invoiceStatusPending || '申请中')
const invoiceStatusIssued = computed(() => getSchema()?.labels?.invoiceStatusIssued || '已开')
const invoiceIssueLabel = computed(() => getSchema()?.labels?.invoiceIssueLabel || '标记已开')
const invoiceDownloadLabel = computed(() => getSchema()?.labels?.invoiceDownloadLabel || '下载发票')
const invoiceDownloadHint = computed(() => getSchema()?.labels?.invoiceDownloadHint || '')
const refundFeeOn = computed(() => !!thicken.value.refundFee)
const refundFeeLabel = computed(() => getSchema()?.labels?.refundFeeLabel || '退票手续费')
const refundFeeHint = computed(() => getSchema()?.labels?.refundFeeHint || '')
function canComplete(row) {
  if (!row || row.refundStatus === 'pending') return false
  if (marketplace.value) {
    return ['shipped', 'in_transit', 'signed'].includes(row.status)
  }
  return row.status === 'shipped'
}
function canClaimRider(row) {
  if (!riderPoolOn.value || !row) return false
  if (row.riderUsername) return false
  return row.status === 'pending' || row.status === 'confirmed'
}
async function claimRider(row) {
  await http.post(`/api/orders/${row.id}/claim`)
  ElMessage.success('已接单')
  load()
}
function canChangeAddress(row) {
  if (!changeAddressOn.value || !row) return false
  return row.status === 'pending' || row.status === 'confirmed'
}
function hasOrderOps(row) {
  if (!row) return false
  if (receiptPrintOn.value) return true
  if (canChangeAddress(row)) return true
  if (canFillRefundTracking(row) || canShowRefundTrace(row)) return true
  if (canAddShipNode(row) || canVerifyReceive(row) || canSetWarranty(row) || canSetRefundFee(row)) return true
  if (canIssueInvoice(row) || canDownloadInvoice(row)) return true
  if (row.refundStatus === 'pending') return true
  if (!marketplace.value && row.status === 'pending') return true
  if (row.status === 'confirmed') return true
  if (marketplace.value && ['shipped', 'in_transit', 'signed'].includes(row.status)) return true
  if (!marketplace.value && row.status === 'shipped') return true
  return false
}
const list = ref([])
const total = ref(0)
const page = ref(1)
const size = ref(10)
const status = ref(null)
const addrVisible = ref(false)
const addrSaving = ref(false)
const addrOrder = ref(null)
const addrForm = reactive({ receiverName: '', receiverPhone: '', addressLine: '' })
const refundTraceVisible = ref(false)
const refundTraceOrderId = ref(null)
const shipNodeVisible = ref(false)
const shipNodeSaving = ref(false)
const shipNodeOrder = ref(null)
const shipNodeForm = reactive({ title: '', detail: '', happenedAt: '' })
const warrantyVisible = ref(false)
const warrantySaving = ref(false)
const warrantyOrder = ref(null)
const warrantyForm = reactive({ until: '' })
const refundFeeVisible = ref(false)
const refundFeeSaving = ref(false)
const refundFeeOrder = ref(null)
const refundFeeForm = reactive({ fee: 0 })

async function load() {
  const res = await http.get('/api/orders', {
    params: { page: page.value, size: size.value, status: status.value || undefined },
  })
  list.value = res.data?.list || []
  total.value = res.data?.total || 0
}

function openChangeAddress(row) {
  addrOrder.value = row
  addrForm.receiverName = row.receiverName || ''
  addrForm.receiverPhone = row.receiverPhone || ''
  addrForm.addressLine = row.addressLine || ''
  addrVisible.value = true
}

async function submitChangeAddress() {
  if (!addrOrder.value) return
  addrSaving.value = true
  try {
    await http.put(`/api/orders/${addrOrder.value.id}/address`, {
      receiverName: addrForm.receiverName,
      receiverPhone: addrForm.receiverPhone,
      addressLine: addrForm.addressLine,
    })
    ElMessage.success('地址已更新')
    addrVisible.value = false
    load()
  } finally {
    addrSaving.value = false
  }
}

function printReceipt(row) {
  const ok = printOrderReceipt(row, {
    labels: getSchema()?.labels || {},
    orderNoun: order.value.label || '订单',
    states: states.value,
    pickupCodeLabel: pickupCodeLabel.value,
    pickupNoLabel: pickupNoLabel.value,
    tableNoLabel: tableNoLabel.value,
    utensilOptLabel: getSchema()?.labels?.utensilOptLabel || '餐具',
    packOptLabel: getSchema()?.labels?.packOptLabel || '打包',
    mergeCodeLabel: mergeCodeLabel.value,
    etaLabel: getSchema()?.labels?.etaLabel || '预计送达',
    packagingFeeLabel: getSchema()?.labels?.packagingFeeLabel || '包装费',
    deliveryFeeLabel: getSchema()?.labels?.deliveryFeeLabel || '配送费',
  })
  if (!ok) ElMessage.warning('请允许浏览器弹出窗口后再打印')
}

async function act(row, action) {
  let body = {}
  if (action === 'ship') {
    if (isStay.value || isCinema.value) {
      try {
        await ElMessageBox.confirm(
          `确认对订单 #${row.id} 执行「${shipVerb.value}」？`,
          shipVerb.value,
        )
      } catch {
        return
      }
    } else {
      const food = isFood.value
      const { value } = await ElMessageBox.prompt(
        food ? `可填${pickupCodeLabel.value}（留空自动生成）` : '请填写物流单号（可留空）',
        shipVerb.value,
        { inputPlaceholder: food ? pickupCodeLabel.value : '物流单号', inputValue: '' },
      ).catch(() => ({ value: null }))
      if (value === null) return
      body = food ? { pickupCode: String(value || '').trim() } : { trackingNo: String(value || '').trim() }
      if (partialShipOn.value && !food) {
        try {
          await ElMessageBox.confirm(
            partialShipHint.value || '本单先发出部分商品。',
            partialShipLabel.value,
          )
          body.partialShip = true
        } catch {
          body.partialShip = false
        }
      }
    }
  }
  await http.post(`/api/orders/${row.id}/${action}`, body)
  ElMessage.success('已更新')
  load()
}

function refundLabel(st) {
  return ({ pending: '待审', approved: '已通过', rejected: '已驳回' }[st] || st)
}

function refundTypeLabelOf(t) {
  if (t === 'return_refund') return refundTypeReturnRefund.value
  if (t === 'refund_only') return refundTypeRefundOnly.value
  if (t === 'exchange_only') return refundTypeExchangeOnly.value
  if (t === 'exchange') return refundTypeExchange.value
  return t || ''
}

function canFillRefundTracking(row) {
  if (!refundTrackingOn.value || !row) return false
  if (row.refundStatus !== 'pending') return false
  if (row.refundType && row.refundType !== 'return_refund' && row.refundType !== 'exchange') {
    return false
  }
  return !row.refundTrackingNo
}

function canShowRefundTrace(row) {
  return refundTraceOn.value && !!row?.refundStatus
}

async function fillRefundTracking(row) {
  const { value } = await ElMessageBox.prompt(
    refundTrackingHint.value || '请填写退货物流单号',
    refundTrackingLabel.value,
    { inputPlaceholder: '承运单号', inputValue: row.refundTrackingNo || '' },
  ).catch(() => ({ value: null }))
  if (value == null) return
  const track = String(value).trim()
  if (!track) {
    ElMessage.warning('请填写退货物流单号')
    return
  }
  await http.put(`/api/orders/${row.id}/refund-tracking`, { trackingNo: track })
  ElMessage.success('退货单号已保存')
  load()
}

function openRefundTrace(row) {
  refundTraceOrderId.value = row.id
  refundTraceVisible.value = true
}

function canAddShipNode(row) {
  if (!shipNodesOn.value || !row) return false
  return ['shipped', 'in_transit', 'signed'].includes(row.status)
}

function openShipNode(row) {
  shipNodeOrder.value = row
  shipNodeForm.title = ''
  shipNodeForm.detail = ''
  shipNodeForm.happenedAt = ''
  shipNodeVisible.value = true
}

async function submitShipNode() {
  const title = String(shipNodeForm.title || '').trim()
  if (!title) {
    ElMessage.warning('请填写进度说明')
    return
  }
  shipNodeSaving.value = true
  try {
    await http.post(`/api/orders/${shipNodeOrder.value.id}/ship-nodes`, {
      title,
      detail: String(shipNodeForm.detail || '').trim(),
      happenedAt: shipNodeForm.happenedAt || '',
    })
    ElMessage.success('物流进度已登记')
    shipNodeVisible.value = false
    load()
  } finally {
    shipNodeSaving.value = false
  }
}

function canVerifyReceive(row) {
  if (!receiveCodeOn.value || !row) return false
  return ['shipped', 'in_transit', 'signed'].includes(row.status) && !row.receiveVerifiedAt
}

async function openVerifyReceive(row) {
  const { value } = await ElMessageBox.prompt(
    receiveCodeHint.value || '请输入买家出示的收货码',
    receiveCodeVerifyLabel.value,
    { inputPlaceholder: '收货码' },
  ).catch(() => ({ value: null }))
  if (value == null) return
  const code = String(value).trim()
  if (!code) {
    ElMessage.warning('请输入收货码')
    return
  }
  await http.post(`/api/orders/${row.id}/verify-receive`, { code })
  ElMessage.success('收货码已核销')
  load()
}

function canSetWarranty(row) {
  if (!warrantyOn.value || !row) return false
  return ['shipped', 'in_transit', 'signed', 'completed'].includes(row.status)
}

function invoiceStatusText(st) {
  if (st === 'pending') return invoiceStatusPending.value
  if (st === 'issued') return invoiceStatusIssued.value
  return st || '—'
}

function canIssueInvoice(row) {
  if (!invoiceOn.value || !row) return false
  return !!row.invoiceTitle && row.invoiceStatus !== 'issued'
}

function canDownloadInvoice(row) {
  if (!invoiceOn.value || !thicken.value.invoicePdf || !row) return false
  return !!(row.invoiceTitle || row.invoiceStatus)
}

async function issueInvoice(row) {
  await http.put(`/api/orders/${row.id}/invoice`, {
    invoiceTitle: row.invoiceTitle || '',
    invoiceStatus: 'issued',
  })
  ElMessage.success('已标记开票')
  load()
}

function downloadInvoice(row) {
  const ok = printOrderInvoice(row, {
    labels: getSchema()?.labels || {},
    orderNoun: order.value.label || '订单',
  })
  if (!ok) ElMessage.warning('请允许浏览器弹出窗口后再下载')
  void invoiceDownloadHint.value
}

function canSetRefundFee(row) {
  if (!refundFeeOn.value || !isCinema.value || !row) return false
  return ['pending', 'confirmed', 'shipped', 'cancelled', 'refunded'].includes(row.status)
    || !!row.refundStatus
}

function openWarranty(row) {
  warrantyOrder.value = row
  warrantyForm.until = String(row.warrantyUntil || '').slice(0, 10)
  warrantyVisible.value = true
}

function openRefundFee(row) {
  refundFeeOrder.value = row
  refundFeeForm.fee = Number(row.refundFeeYuan || 0)
  refundFeeVisible.value = true
}

async function submitRefundFee() {
  const fee = Number(refundFeeForm.fee)
  if (!Number.isFinite(fee) || fee < 0) {
    ElMessage.warning('请填写有效手续费')
    return
  }
  refundFeeSaving.value = true
  try {
    await http.put(`/api/orders/${refundFeeOrder.value.id}/refund-fee`, { refundFeeYuan: fee })
    ElMessage.success('手续费已登记')
    refundFeeVisible.value = false
    load()
  } finally {
    refundFeeSaving.value = false
  }
}

async function submitWarranty() {
  const day = String(warrantyForm.until || '').trim().slice(0, 10)
  if (!/^\d{4}-\d{2}-\d{2}$/.test(day)) {
    ElMessage.warning('请选择延保截止日期')
    return
  }
  warrantySaving.value = true
  try {
    await http.put(`/api/orders/${warrantyOrder.value.id}/warranty`, { warrantyUntil: day })
    ElMessage.success('延保日期已保存')
    warrantyVisible.value = false
    load()
  } finally {
    warrantySaving.value = false
  }
}

async function decideRefund(row, pass) {
  let note = ''
  if (!pass) {
    const { value } = await ElMessageBox.prompt('驳回说明（可选）', '驳回售后', {
      inputPlaceholder: '原因',
    }).catch(() => ({ value: null }))
    if (value === null) return
    note = String(value || '').trim()
  } else {
    await ElMessageBox.confirm(
      row.refundType === 'exchange' || row.refundType === 'exchange_only'
        ? `通过订单 #${row.id} 换货？订单保持原状态。`
        : `通过订单 #${row.id} 售后？将回补库存并退账户余额。`,
      '通过售后',
    )
  }
  await http.post(`/api/orders/${row.id}/refund`, { pass, note })
  ElMessage.success(pass ? '已通过售后' : '已驳回')
  load()
}

async function exportCsv() {
  const res = await http.get('/api/orders', {
    params: { page: 1, size: 5000, status: status.value || undefined },
  })
  const rows = res.data?.list || []
  if (!rows.length) {
    ElMessage.warning('当前筛选无数据可导出')
    return
  }
  const headers = isStay.value
    ? ['编号', userLabel.value, '金额', '状态', orderRemarkLabel.value, '优惠', '获积分', '明细', '下单时间']
    : isCinema.value
      ? ['编号', userLabel.value, '金额', pickupCodeLabel.value, '状态', orderRemarkLabel.value, '优惠', '获积分', '明细', '下单时间']
    : isFood.value
      ? ['编号', userLabel.value, '金额', '配送方式', '地址', tasteNoteLabel.value, pickupCodeLabel.value, '状态', orderRemarkLabel.value, '优惠', '获积分', '明细', '下单时间']
      : ['编号', userLabel.value, '金额', '配送方式', '收货信息', '物流单号', '状态', orderRemarkLabel.value, '优惠', '获积分', '明细', '下单时间']
  const data = rows.map((row) => {
    const money = Number(row.totalYuan || 0).toFixed(2)
    if (isStay.value) {
      return [
        row.id,
        personLabel(row, ''),
        money,
        states.value[row.status] || row.status,
        row.remark || '',
        Number(row.discountYuan) > 0 ? row.discountYuan : '',
        Number(row.pointsEarned) > 0 ? row.pointsEarned : '',
        (row.lines || [])
          .map((x) => formatOrderLine(x))
          .join('；'),
        row.createdAt,
      ]
    }
    if (isCinema.value) {
      return [
        row.id,
        personLabel(row, ''),
        money,
        row.pickupCode || '',
        states.value[row.status] || row.status,
        row.remark || '',
        Number(row.discountYuan) > 0 ? row.discountYuan : '',
        Number(row.pointsEarned) > 0 ? row.pointsEarned : '',
        (row.lines || [])
          .map((x) => formatOrderLine(x))
          .join('；'),
        row.createdAt,
      ]
    }
    const base = [
      row.id,
      personLabel(row, ''),
      money,
      row.deliveryType || '',
      [row.receiverName, row.receiverPhone, row.addressLine].filter(Boolean).join(' '),
    ]
    const tail = [
      states.value[row.status] || row.status,
      row.remark || '',
      Number(row.discountYuan) > 0 ? row.discountYuan : '',
      Number(row.pointsEarned) > 0 ? row.pointsEarned : '',
      (row.lines || []).map((x) => formatOrderLine(x)).join('；'),
      row.createdAt,
    ]
    if (isFood.value) {
      return [...base, row.tasteNote || '', row.pickupCode || '', ...tail]
    }
    return [...base, row.trackingNo || '', ...tail]
  })
  downloadCsv(`orders_${status.value || 'all'}_${Date.now()}.csv`, headers, data)
  ElMessage.success(`已导出 ${rows.length} 条（UTF-8，可用 Excel 直接打开）`)
}

onMounted(load)
</script>

<style scoped>
.toolbar { margin-bottom: 12px; display: flex; gap: 8px; flex-wrap: wrap; align-items: center; }
.muted { color: var(--el-text-color-secondary); font-size: 13px; margin: 0 0 12px; }
.pager { margin-top: 16px; display: flex; justify-content: flex-end; }
.ops-empty { color: var(--el-text-color-placeholder, #c0c4cc); font-size: 13px; padding: 0 4px; }
.ops-hint { color: var(--el-text-color-secondary, #909399); font-size: 12px; padding: 0 4px; }
.table-ops { display: flex; gap: 4px; flex-wrap: wrap; align-items: center; }
</style>
