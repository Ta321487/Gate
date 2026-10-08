<template>
  <div>
    <section class="hero">
      <h1>{{ label }}</h1>
      <p>查看{{ orderNoun }}状态与明细。</p>
      <p v-if="stockLockHint" class="sub">{{ stockLockHint }}</p>
      <p v-if="confirmReceiveTimeoutHint" class="sub">{{ confirmReceiveTimeoutHint }}</p>
      <p v-if="inviteReviewHint" class="sub">{{ inviteReviewHint }}</p>
      <el-select v-model="status" clearable placeholder="全部状态" style="width:140px" @change="load">
        <el-option
          v-for="opt in statusOptions"
          :key="opt.value"
          :label="opt.label"
          :value="opt.value"
        />
      </el-select>
    </section>

    <PageSkeleton v-if="loading" variant="list" :rows="4" />
    <template v-else>
    <article
      v-for="row in list"
      :key="row.id"
      class="card"
    >
      <div class="hd">
        <strong class="hd-title">
          <StatusChip :tone="orderTone(row.status)" compact />
          {{ orderNoun }} #{{ row.id }}
        </strong>
        <el-tag size="small" effect="plain">{{ displayStatus(row) }}</el-tag>
      </div>
      <ImmSteps v-if="row.status !== 'cancelled'" :steps="orderProgressSteps(row.status, { marketplace, lineCustom, states: rawStates })" />
      <p class="sub">
        <span :title="row.createdAt || ''">{{ formatRelative(row.createdAt) }}</span>
        · 合计 ¥{{ row.totalYuan }}
        <template v-if="Number(row.discountYuan) > 0"> · 优惠 ¥{{ row.discountYuan }}</template>
        <template v-if="row.couponCode">
          · {{ couponRedeemCodeLabel }} {{ row.couponCode }}
        </template>
        <template v-if="Number(row.pointsEarned) > 0"> · 获积分 {{ row.pointsEarned }}</template>
      </p>
      <div v-if="groupBuyProgressOn && row.groupBuy" class="group-buy">
        <p class="sub">{{ groupBuyProgressLabel }}：{{ row.groupBuy.joined }}/{{ row.groupBuy.targetSize }}
          <template v-if="row.groupBuy.status"> · {{ groupBuyStatusText(row.groupBuy.status) }}</template>
        </p>
        <el-progress
          :percentage="groupBuyPct(row.groupBuy)"
          :stroke-width="10"
          :show-text="false"
        />
        <p v-if="groupBuyFailOn && row.groupBuy.status === 'failed' && groupBuyFailHint" class="sub">
          {{ groupBuyFailHint }}
        </p>
      </div>
      <p v-if="payCountdownText(row)" class="pay-cd" :class="{ urgent: isUrgentCountdown(paySecondsLeft(row)) }">
        {{ payCountdownText(row) }}
      </p>
      <p v-if="row.refundStatus" class="sub refund">
        售后：{{ refundLabel(row.refundStatus) }}
        <template v-if="row.refundType"> · {{ refundTypeLabelOf(row.refundType) }}</template>
        <template v-if="row.refundReason"> · {{ row.refundReason }}</template>
        <template v-if="row.refundTrackingNo"> · 退货单号 {{ row.refundTrackingNo }}</template>
      </p>
      <p v-if="afterSaleDaysHint && canRefund(row)" class="sub">{{ afterSaleDaysHint }}</p>
      <p v-if="row.partialShip" class="sub">{{ partialShipLabel }}</p>
      <p v-if="orderShareOn && row.shareToken" class="sub">
        {{ orderShareLabel }}：{{ row.shareToken }}
      </p>
      <p v-if="warrantyOn && row.warrantyUntil" class="sub">{{ warrantyLabel }}：{{ row.warrantyUntil }}</p>
      <p v-if="invoiceOn && (row.invoiceTitle || row.invoiceStatus)" class="sub">
        {{ invoiceTitleLabel }}：{{ row.invoiceTitle || '—' }}
        <template v-if="row.invoiceStatus"> · {{ invoiceStatusText(row.invoiceStatus) }}</template>
      </p>
      <p v-if="refundOriginOn && refundOriginHint && canRefund(row)" class="sub">{{ refundOriginLabel }}：{{ refundOriginHint }}</p>
      <p v-if="refundFeeOn && Number(row.refundFeeYuan || 0) > 0" class="sub">
        {{ refundFeeLabel }}：¥{{ Number(row.refundFeeYuan).toFixed(2) }}
      </p>
      <p v-if="receiveCodeOn && row.pickupCode && !isFood && !isCinema" class="sub">
        {{ receiveCodeLabel }}：{{ row.pickupCode }}
        <span v-if="row.receiveVerifiedAt"> · 已核销</span>
      </p>
      <p v-if="hasShipInfo(row)" class="ship">
        <template v-if="isStay">
          <template v-if="row.remark">{{ orderRemarkLabel }}：{{ row.remark }}</template>
        </template>
        <template v-else-if="isCinema">
          <template v-if="row.remark">{{ orderRemarkLabel }}：{{ row.remark }}</template>
          <template v-if="row.pickupCode">
            <br />{{ pickupCodeLabel }}：{{ row.pickupCode }}
            <CodeQrBlock :code="row.pickupCode" :label="pickupCodeLabel" />
          </template>
          <template v-if="pickupCodeHint && row.pickupCode"><br /><span class="muted">{{ pickupCodeHint }}</span></template>
        </template>
        <template v-else>
          <template v-if="row.deliveryType">{{ row.deliveryType }} · </template>
          <template v-if="row.receiverName || row.receiverPhone">
            {{ row.receiverName }} {{ row.receiverPhone }}
          </template>
          <template v-if="row.addressLine"> · {{ row.addressLine }}</template>
          <template v-if="row.slotLabel"><br />{{ row.deliveryOn }} {{ row.slotLabel }}<template v-if="Number(row.priceRate) > 1"> · 节日 ×{{ Number(row.priceRate).toFixed(2) }}</template></template>
          <template v-if="isFood && row.tableNo"><br />{{ tableNoLabel }}：{{ row.tableNo }}</template>
          <template v-if="isFood && row.utensilOpt"><br />{{ utensilOptLabel }}：{{ row.utensilOpt }}</template>
          <template v-if="isFood && row.packOpt"><br />{{ packOptLabel }}：{{ row.packOpt }}</template>
          <template v-if="Number(row.packagingFeeYuan || 0) > 0">
            <br />{{ packagingFeeLabel }}：¥{{ Number(row.packagingFeeYuan).toFixed(2) }}
          </template>
          <template v-if="isFood && Number(row.deliveryFeeYuan || 0) > 0">
            <br />{{ deliveryFeeLabel }}：¥{{ Number(row.deliveryFeeYuan).toFixed(2) }}
          </template>
          <template v-if="isFood && row.etaText"><br />{{ etaLabel }}：{{ row.etaText }}</template>
          <template v-if="isFood && row.mergeCode"><br />{{ mergeCodeLabel }}：{{ row.mergeCode }}</template>
          <template v-if="isFood && row.tasteNote"><br />{{ tasteNoteLabel }}：{{ row.tasteNote }}</template>
          <template v-if="!isFood && row.trackingNo"><br />物流单号：{{ row.trackingNo }}</template>
          <template v-if="isFood && row.pickupCode">
            <br />{{ pickupNoLabel }}：{{ row.pickupCode }}
            <CodeQrBlock :code="row.pickupCode" :label="pickupNoLabel" />
          </template>
          <template v-if="row.remark"><br />{{ orderRemarkLabel }}：{{ row.remark }}</template>
        </template>
      </p>
      <ul class="lines">
        <li v-for="ln in row.lines || []" :key="ln.id">
          {{ ln.title }} × {{ ln.qty }}（¥{{ Number(ln.lineYuan || 0).toFixed(2) }}）
          <template v-if="ln.customText"> · {{ customTextLabel }}：{{ ln.customText }}</template>
          <template v-if="ln.drawTitle"> · 抽中：{{ ln.drawTitle }}<template v-if="ln.pityText">（{{ ln.pityText }}）</template></template>
          <template v-if="ln.specChoice"> · {{ ln.specChoice }}</template>
          <template v-if="ln.attachUrl">
            · <a :href="ln.attachUrl" target="_blank" rel="noopener noreferrer">图片</a>
          </template>
          <template v-if="marketplace && lineShop(ln)"> · {{ lineShop(ln) }}</template>
        </li>
      </ul>
      <div class="acts">
        <el-button v-if="canPay(row)" size="small" type="primary" @click="openPay(row)">去付款</el-button>
        <el-button v-if="canShowTrace(row)" size="small" @click="openTrace(row)">{{ logisticsTraceLabel }}</el-button>
        <el-button
          v-if="canReceive(row)"
          size="small"
          type="success"
          @click="confirmReceive(row)"
        >确认收货</el-button>
        <el-button
          v-if="canChangeAddress(row)"
          size="small"
          @click="openChangeAddress(row)"
        >{{ changeAddressLabel }}</el-button>
        <el-button
          v-if="receiptPrintOn"
          size="small"
          @click="printReceipt(row)"
        >{{ orderReceiptPrintLabel }}</el-button>
        <el-button
          v-if="canRequestInvoice(row)"
          size="small"
          @click="openInvoice(row)"
        >{{ invoiceRequestLabel }}</el-button>
        <el-button
          v-if="canDownloadInvoice(row)"
          size="small"
          @click="downloadInvoice(row)"
        >{{ invoiceDownloadLabel }}</el-button>
        <el-button
          v-if="canRefund(row)"
          size="small"
          type="warning"
          @click="openRefund(row)"
        >{{ isCinema ? cinemaRefundLabel : '申请售后' }}</el-button>
        <el-button
          v-if="canFillRefundTracking(row)"
          size="small"
          @click="fillRefundTracking(row)"
        >{{ refundTrackingLabel }}</el-button>
        <el-button
          v-if="canShowRefundTrace(row)"
          size="small"
          @click="openRefundTrace(row)"
        >{{ refundTraceLabel }}</el-button>
        <el-button
          v-if="orderShareOn && row.shareToken"
          size="small"
          @click="copyShareToken(row)"
        >{{ orderShareLabel }}</el-button>
        <el-button
          v-if="canSetWarranty(row)"
          size="small"
          @click="setWarranty(row)"
        >{{ warrantyLabel }}</el-button>
        <el-button
          v-if="canSetRefundFee(row)"
          size="small"
          @click="setRefundFee(row)"
        >{{ refundFeeLabel }}</el-button>
        <el-button
          v-if="canReview(row)"
          size="small"
          type="primary"
          @click="submitReview(row)"
        >评价</el-button>
        <el-button
          v-if="row.status === 'pending' || row.status === 'confirmed'"
          size="small"
          @click="cancel(row)"
        >取消</el-button>
      </div>
    </article>
    <EmptyHint
      v-if="!list.length"
      :title="`暂无${orderNoun}`"
      desc="去逛逛，把心仪商品加进购物车吧。"
      mark="单"
      cta-label="去浏览"
      @cta="$router.push('/archive')"
    />
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
    </template>

    <el-dialog v-model="addrVisible" :title="changeAddressLabel" width="420px" destroy-on-close>
      <p v-if="changeAddressHint" class="pay-tip">{{ changeAddressHint }}</p>
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

    <OrderTraceDialog v-model="traceVisible" :order-id="traceOrderId" :title="logisticsTraceLabel" />
    <OrderTraceDialog
      v-model="refundTraceVisible"
      :order-id="refundTraceOrderId"
      endpoint="refund-trace"
      :title="refundTraceLabel"
      :empty-text="refundTraceEmpty"
    />

    <el-dialog v-model="warrantyVisible" :title="warrantyLabel" width="400px" destroy-on-close>
      <p v-if="warrantyHint" class="pay-tip">{{ warrantyHint }}</p>
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

    <el-dialog v-model="invoiceVisible" :title="invoiceRequestLabel" width="420px" destroy-on-close>
      <p v-if="invoiceTitleHint" class="pay-tip">{{ invoiceTitleHint }}</p>
      <el-form label-position="top">
        <el-form-item :label="invoiceTitleLabel" required>
          <el-input v-model="invoiceForm.title" maxlength="128" :placeholder="invoiceTitleHint || '请填写抬头'" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="invoiceVisible = false">取消</el-button>
        <el-button type="primary" :loading="invoiceSaving" @click="submitInvoice">提交申请</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="refundFeeVisible" :title="refundFeeLabel" width="400px" destroy-on-close>
      <p v-if="refundFeeHint" class="pay-tip">{{ refundFeeHint }}</p>
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

    <el-dialog v-model="refundVisible" :title="isCinema ? cinemaRefundLabel : '申请售后'" width="440px" destroy-on-close>
      <p v-if="isCinema && ticketRefundCutoffHint" class="pay-tip">{{ ticketRefundCutoffHint }}</p>
      <p v-if="refundTypeHint || refundReasonHint" class="pay-tip">
        {{ refundTypeHint || refundReasonHint }}
      </p>
      <el-form label-position="top">
        <el-form-item v-if="refundTypeOn" :label="refundTypeLabel" required>
          <el-radio-group v-model="refundForm.refundType">
            <el-radio value="refund_only">{{ refundTypeRefundOnly }}</el-radio>
            <el-radio value="return_refund">{{ refundTypeReturnRefund }}</el-radio>
            <el-radio v-if="refundExchangeOn" value="exchange">{{ refundTypeExchange }}</el-radio>
            <el-radio v-if="refundExchangeOn" value="exchange_only">{{ refundTypeExchangeOnly }}</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item :label="refundReasonLabel" required>
          <el-select
            v-if="refundReasonOptions.length"
            v-model="refundForm.reasonChip"
            clearable
            placeholder="请选择原因"
            style="width:100%"
          >
            <el-option v-for="opt in refundReasonOptions" :key="opt" :label="opt" :value="opt" />
          </el-select>
          <el-input
            v-model="refundForm.reasonDetail"
            type="textarea"
            :rows="2"
            maxlength="200"
            :placeholder="refundReasonPlaceholder"
            style="margin-top:8px"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="refundVisible = false">取消</el-button>
        <el-button type="primary" :loading="refundSaving" @click="submitRefund">提交</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="payVisible" title="去付款" width="420px" destroy-on-close>
      <p class="pay-tip">{{ demoPayHint }}</p>
      <el-form label-position="top">
        <el-form-item label="支付方式" required>
          <el-radio-group v-model="payForm.payChannel">
            <el-radio value="alipay">支付宝</el-radio>
            <el-radio value="wechat">微信</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="支付密码" required>
          <el-input
            v-model="payForm.payPassword"
            type="password"
            show-password
            maxlength="32"
            placeholder="请输入支付密码（至少 4 位）"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="payVisible = false">取消</el-button>
        <el-button type="primary" :loading="paying" @click="submitPay">确认支付</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import http from '../../api/http'
import EmptyHint from '../../components/EmptyHint.vue'
import CodeQrBlock from '../../components/CodeQrBlock.vue'
import ImmSteps from '../../components/ImmSteps.vue'
import OrderTraceDialog from '../../components/OrderTraceDialog.vue'
import PageSkeleton from '../../components/PageSkeleton.vue'
import StatusChip from '../../components/StatusChip.vue'
import { formatRelative } from '../../utils/dates.js'
import { hasCap, hasTrait, getSchema, menuLabel } from '../../utils/domainSchema.js'
import {
  deadlineFromCreated,
  formatCountdownClock,
  isUrgentCountdown,
  secondsUntil,
  useNowTick,
} from '../../utils/useCountdown.js'
import { orderProgressSteps, orderTone } from '../../utils/statusTone.js'
import { printOrderReceipt } from '../../utils/orderReceiptPrint.js'
import { printOrderInvoice } from '../../utils/orderInvoicePrint.js'

const label = menuLabel('user', 'my_orders', '我的订单')
const orderNoun = computed(() => getSchema()?.entities?.order?.label || '订单')
const rawStates = computed(() => getSchema()?.entities?.order?.states || {})
const lineCustom = computed(() => hasCap('line_custom'))
const customTextLabel = computed(() => getSchema()?.labels?.lineCustomTextLabel || '定制内容')
const noCasualRefund = computed(() => !!getSchema()?.noCasualRefund)
const isFood = computed(() => hasTrait('food'))
const isStay = computed(
  () =>
    hasTrait('slotHotel')
    || hasTrait('slotCarrent')
    || getSchema()?.entities?.order?.fulfillMode === 'stay'
    || getSchema()?.entities?.order?.fulfillMode === 'rental',
)
const isCinema = computed(
  () => hasTrait('seatSelect') || getSchema()?.entities?.order?.fulfillMode === 'cinema',
)
const showTraceBase = computed(() => !isStay.value && !isFood.value && !isCinema.value)
const reviewOn = computed(() => hasCap('order_review'))
const marketplace = computed(() => !!getSchema()?.shopMarketplace)
const demoPay = computed(() => !!getSchema()?.demoPay || marketplace.value)
const demoPayHint = computed(
  () =>
    getSchema()?.labels?.demoPayHint
    || '选择支付宝或微信，确认后从账户余额扣款。',
)
const timeoutMinutes = computed(() => {
  const n = Number(getSchema()?.orderTimeoutMinutes || 0)
  return Number.isFinite(n) && n > 0 ? n : 0
})
const timeoutHint = computed(
  () => getSchema()?.labels?.orderTimeoutHint || '',
)
const orderRemarkLabel = computed(() => getSchema()?.labels?.orderRemarkLabel || '备注')
const tasteNoteLabel = computed(() => getSchema()?.labels?.tasteNoteLabel || '口味')
const pickupCodeLabel = computed(() => getSchema()?.labels?.pickupCodeLabel || (isFood.value ? '取餐码' : '取票码'))
const pickupNoLabel = computed(() => getSchema()?.labels?.pickupNoLabel || pickupCodeLabel.value)
const pickupCodeHint = computed(() => getSchema()?.labels?.pickupCodeHint || getSchema()?.labels?.pickupNoHint || '')
const tableNoLabel = computed(() => getSchema()?.labels?.tableNoLabel || '桌号')
const utensilOptLabel = computed(() => getSchema()?.labels?.utensilOptLabel || '餐具')
const packOptLabel = computed(() => getSchema()?.labels?.packOptLabel || '打包')
const packagingFeeLabel = computed(() => getSchema()?.labels?.packagingFeeLabel || '包装费')
const deliveryFeeLabel = computed(() => getSchema()?.labels?.deliveryFeeLabel || '配送费')
const etaLabel = computed(() => getSchema()?.labels?.etaLabel || '预计送达')
const mergeCodeLabel = computed(() => getSchema()?.labels?.mergeCodeLabel || '拼单码')
const thicken = computed(() => getSchema()?.tradeThicken || {})
const couponRedeemCodeLabel = computed(
  () => getSchema()?.labels?.couponRedeemCodeLabel || '核销码',
)
const groupBuyProgressOn = computed(() => !!thicken.value.groupBuyProgress)
const groupBuyProgressLabel = computed(
  () => getSchema()?.labels?.groupBuyProgressLabel || '拼团进度',
)
const groupBuyFailOn = computed(() => !!thicken.value.groupBuyFailRefund)
const groupBuyFailHint = computed(() => getSchema()?.labels?.groupBuyFailRefundHint || '')
function groupBuyStatusText(st) {
  return ({ open: '拼团中', formed: '已成团', failed: '未成团' }[st] || st || '')
}
function groupBuyPct(gb) {
  const t = Number(gb?.targetSize || 0)
  const j = Number(gb?.joined || 0)
  if (!(t > 0)) return 0
  return Math.min(100, Math.round((j / t) * 100))
}
const cinemaRefundLabel = computed(() => getSchema()?.labels?.cinemaRefundLabel || '申请退票')
const ticketRefundCutoffHint = computed(
  () => thicken.value.ticketRefundCutoff ? (getSchema()?.labels?.ticketRefundCutoffHint || '') : '',
)
const stockLockHint = computed(() =>
  thicken.value.stockLock ? (getSchema()?.labels?.stockLockHint || '') : '',
)
const confirmReceiveTimeoutHint = computed(() =>
  thicken.value.confirmReceiveTimeout ? (getSchema()?.labels?.confirmReceiveTimeoutHint || '') : '',
)
const changeAddressOn = computed(() => !!thicken.value.changeAddress)
const changeAddressLabel = computed(() => getSchema()?.labels?.changeAddressLabel || '修改地址')
const changeAddressHint = computed(() => getSchema()?.labels?.changeAddressHint || '')
const receiptPrintOn = computed(() => !!thicken.value.orderReceiptPrint)
const orderReceiptPrintLabel = computed(() => getSchema()?.labels?.orderReceiptPrintLabel || '打印小票')
const inviteReviewHint = computed(() => {
  if (!thicken.value.inviteReview) return ''
  const title = getSchema()?.labels?.inviteReviewTitle || '邀请评价'
  const body = getSchema()?.labels?.inviteReviewBody || ''
  return body ? `${title}：${body}` : title
})
const refundTypeOn = computed(() => !!thicken.value.refundType)
const refundTrackingOn = computed(() => !!thicken.value.refundTracking)
const refundTraceOn = computed(() => !!thicken.value.refundTrace)
const refundReasonOptions = computed(() => {
  const opts = getSchema()?.entities?.order?.refundReasonOptions
  return Array.isArray(opts) ? opts.map((x) => String(x)).filter(Boolean) : []
})
const refundReasonLabel = computed(() => getSchema()?.labels?.refundReasonLabel || '售后原因')
const refundReasonHint = computed(() => getSchema()?.labels?.refundReasonHint || '')
const refundReasonRequiredHint = computed(
  () => getSchema()?.labels?.refundReasonRequiredHint || '请填写售后原因',
)
const refundReasonPlaceholder = computed(() =>
  noCasualRefund.value
    ? '如：破损、印错、少件。不支持无理由退货'
    : '补充说明（选填，选「其他」时请填写）',
)
const refundTypeLabel = computed(() => getSchema()?.labels?.refundTypeLabel || '售后类型')
const refundTypeHint = computed(() => getSchema()?.labels?.refundTypeHint || '')
const refundTypeRefundOnly = computed(() => getSchema()?.labels?.refundTypeRefundOnly || '仅退款')
const refundTypeReturnRefund = computed(
  () => getSchema()?.labels?.refundTypeReturnRefund || '退货退款',
)
const refundExchangeOn = computed(() => !!thicken.value.refundExchange)
const refundTypeExchange = computed(() => getSchema()?.labels?.refundTypeExchange || '换货')
const refundTypeExchangeOnly = computed(
  () => getSchema()?.labels?.refundTypeExchangeOnly || '仅换货',
)
const logisticsTraceLabel = computed(() => getSchema()?.labels?.logisticsTraceLabel || '物流进度')
const orderShareOn = computed(() => !!thicken.value.orderShare)
const orderShareLabel = computed(() => getSchema()?.labels?.orderShareLabel || '分享口令')
const orderShareHint = computed(() => getSchema()?.labels?.orderShareHint || '')
const receiveCodeOn = computed(() => !!thicken.value.receiveCode)
const receiveCodeLabel = computed(() => getSchema()?.labels?.receiveCodeLabel || '收货码')
const warrantyOn = computed(() => !!thicken.value.warranty)
const warrantyLabel = computed(() => getSchema()?.labels?.warrantyLabel || '延保至')
const warrantyHint = computed(() => getSchema()?.labels?.warrantyHint || '')
const invoiceOn = computed(() => !!(thicken.value.invoiceTitle || thicken.value.invoiceStatus))
const invoiceTitleLabel = computed(() => getSchema()?.labels?.invoiceTitleLabel || '发票抬头')
const invoiceTitleHint = computed(() => getSchema()?.labels?.invoiceTitleHint || '')
const invoiceStatusLabel = computed(() => getSchema()?.labels?.invoiceStatusLabel || '开票状态')
const invoiceStatusPending = computed(() => getSchema()?.labels?.invoiceStatusPending || '申请中')
const invoiceStatusIssued = computed(() => getSchema()?.labels?.invoiceStatusIssued || '已开')
const invoiceRequestLabel = computed(() => getSchema()?.labels?.invoiceRequestLabel || '申请开票')
const invoiceDownloadLabel = computed(() => getSchema()?.labels?.invoiceDownloadLabel || '下载发票')
const invoiceDownloadHint = computed(() => getSchema()?.labels?.invoiceDownloadHint || '')
const refundOriginOn = computed(() => !!thicken.value.refundOrigin)
const refundOriginLabel = computed(() => getSchema()?.labels?.refundOriginLabel || '退款说明')
const refundOriginHint = computed(() => getSchema()?.labels?.refundOriginHint || '')
const refundFeeOn = computed(() => !!thicken.value.refundFee)
const refundFeeLabel = computed(() => getSchema()?.labels?.refundFeeLabel || '退票手续费')
const refundFeeHint = computed(() => getSchema()?.labels?.refundFeeHint || '')
const partialShipLabel = computed(() => getSchema()?.labels?.partialShipLabel || '部分发货')
const refundTrackingLabel = computed(() => getSchema()?.labels?.refundTrackingLabel || '退货物流单号')
const refundTrackingHint = computed(() => getSchema()?.labels?.refundTrackingHint || '')
const afterSaleDaysHint = computed(() =>
  thicken.value.afterSaleDays ? (getSchema()?.labels?.afterSaleDaysHint || '') : '',
)
const refundTraceLabel = computed(() => getSchema()?.labels?.refundTraceLabel || '售后进度')
const refundTraceEmpty = computed(() => getSchema()?.labels?.refundTraceEmpty || '暂无售后进度')
const { nowMs } = useNowTick()
const loading = ref(false)
const list = ref([])
const total = ref(0)
const page = ref(1)
const size = ref(10)
const status = ref(null)
const traceVisible = ref(false)
const traceOrderId = ref(null)
const refundTraceVisible = ref(false)
const refundTraceOrderId = ref(null)
const reviewedIds = ref(new Set())
const payVisible = ref(false)
const paying = ref(false)
const payOrder = ref(null)
const payForm = reactive({ payChannel: 'alipay', payPassword: '' })
const warrantyVisible = ref(false)
const warrantySaving = ref(false)
const warrantyOrder = ref(null)
const warrantyForm = reactive({ until: '' })
const invoiceVisible = ref(false)
const invoiceSaving = ref(false)
const invoiceOrder = ref(null)
const invoiceForm = reactive({ title: '' })
const refundFeeVisible = ref(false)
const refundFeeSaving = ref(false)
const refundFeeOrder = ref(null)
const refundFeeForm = reactive({ fee: 0 })
const addrVisible = ref(false)
const addrSaving = ref(false)
const addrOrder = ref(null)
const addrForm = reactive({ receiverName: '', receiverPhone: '', addressLine: '' })
const refundVisible = ref(false)
const refundSaving = ref(false)
const refundOrder = ref(null)
const refundForm = reactive({
  refundType: 'refund_only',
  reasonChip: '',
  reasonDetail: '',
})

/** 多店买家筛选项：四态；pending 兜底仍可选「待付款」 */
const statusOptions = computed(() => {
  if (!marketplace.value) {
    return Object.entries(rawStates.value).map(([value, lab]) => ({ value, label: lab }))
  }
  const opts = [
    { value: 'confirmed', label: '待发货' },
    { value: 'shipped', label: '已发货' },
    { value: 'completed', label: '已完成' },
    { value: 'cancelled', label: '已取消' },
  ]
  if (rawStates.value.pending) opts.unshift({ value: 'pending', label: '待付款' })
  return opts
})

function displayStatus(row) {
  if (!row) return ''
  if (!marketplace.value) return rawStates.value[row.status] || row.status
  const st = row.status
  if (st === 'pending') return '待付款'
  if (st === 'confirmed') return '待发货'
  if (st === 'shipped' || st === 'in_transit' || st === 'signed') return '已发货'
  if (st === 'completed') return '已完成'
  if (st === 'cancelled') return '已取消'
  return rawStates.value[st] || st
}

function lineShop(ln) {
  return String(ln?.shopName || ln?.shop_name || '').trim()
}

function refundLabel(st) {
  return ({ pending: '待审核', approved: '已通过', rejected: '已驳回' }[st] || st)
}

function refundTypeLabelOf(t) {
  if (t === 'return_refund') return refundTypeReturnRefund.value
  if (t === 'refund_only') return refundTypeRefundOnly.value
  if (t === 'exchange_only') return refundTypeExchangeOnly.value
  if (t === 'exchange') return refundTypeExchange.value
  return t || ''
}

function paySecondsLeft(row) {
  if (!row || row.status !== 'pending' || !timeoutMinutes.value) return null
  const deadline = deadlineFromCreated(row.createdAt, timeoutMinutes.value)
  if (deadline == null) return null
  return secondsUntil(deadline, nowMs.value)
}

function payCountdownText(row) {
  const sec = paySecondsLeft(row)
  if (sec == null) return ''
  if (sec <= 0) return timeoutHint.value || '支付已超时，订单将自动取消'
  const clock = formatCountdownClock(sec)
  return demoPay.value || marketplace.value
    ? `请在 ${clock} 内完成支付`
    : `请在 ${clock} 内确认，超时将自动取消`
}

function hasShipInfo(row) {
  if (!row) return false
  if (isStay.value) return !!row.remark
  if (isCinema.value) return !!(row.remark || row.pickupCode)
  if (row.deliveryType || row.addressLine || row.receiverName || row.receiverPhone || row.remark) return true
  if (isFood.value) {
    return !!(
      row.tasteNote || row.pickupCode || row.tableNo || row.utensilOpt || row.packOpt
      || row.mergeCode || row.etaText || Number(row.packagingFeeYuan || 0) > 0
      || Number(row.deliveryFeeYuan || 0) > 0
    )
  }
  return !!row.trackingNo
}

function canPay(row) {
  return demoPay.value && row?.status === 'pending'
}

function canShowTrace(row) {
  if (!showTraceBase.value || !row) return false
  if (row.status === 'pending' || row.status === 'cancelled') return false
  return ['confirmed', 'shipped', 'in_transit', 'signed', 'completed'].includes(row.status)
}

function canRefund(row) {
  if (!row) return false
  const ok = isCinema.value
    ? ['pending', 'confirmed', 'shipped', 'in_transit', 'signed', 'completed'].includes(row.status)
    : ['shipped', 'in_transit', 'signed', 'completed'].includes(row.status)
  if (!ok) return false
  const rs = row.refundStatus || ''
  return !rs || rs === 'rejected'
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

function canReceive(row) {
  if (!marketplace.value || !row) return false
  return ['shipped', 'in_transit', 'signed'].includes(row.status) && row.refundStatus !== 'pending'
}

function canChangeAddress(row) {
  if (!changeAddressOn.value || !row) return false
  return row.status === 'pending' || row.status === 'confirmed'
}

function canReview(row) {
  if (!reviewOn.value || !row) return false
  if (!['signed', 'completed'].includes(row.status)) return false
  return !reviewedIds.value.has(row.id)
}

async function loadReviewsHint(orders) {
  if (!reviewOn.value) {
    reviewedIds.value = new Set()
    return
  }
  const done = new Set()
  await Promise.all(
    (orders || [])
      .filter((o) => ['signed', 'completed'].includes(o.status))
      .map(async (o) => {
        try {
          const res = await http.get(`/api/order-reviews/by-order/${o.id}`)
          if (res.data?.id) done.add(o.id)
        } catch { /* ignore */ }
      }),
  )
  reviewedIds.value = done
}

async function load() {
  loading.value = true
  try {
    const res = await http.get('/api/orders', {
      params: { page: page.value, size: size.value, status: status.value || undefined },
    })
    list.value = res.data?.list || []
    total.value = res.data?.total || 0
    await loadReviewsHint(list.value)
  } finally {
    loading.value = false
  }
}

async function cancel(row) {
  await ElMessageBox.confirm(`取消${orderNoun.value} #${row.id}？`, '取消')
  await http.post(`/api/orders/${row.id}/cancel`)
  ElMessage.success('已取消')
  load()
}

async function confirmReceive(row) {
  await ElMessageBox.confirm(`确认已收到${orderNoun.value} #${row.id}？`, '确认收货')
  await http.post(`/api/orders/${row.id}/receive`)
  ElMessage.success('已确认收货')
  load()
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
    orderNoun: orderNoun.value,
    states: rawStates.value,
    pickupCodeLabel: pickupCodeLabel.value,
    pickupNoLabel: pickupNoLabel.value,
    tableNoLabel: tableNoLabel.value,
    utensilOptLabel: utensilOptLabel.value,
    packOptLabel: packOptLabel.value,
    mergeCodeLabel: mergeCodeLabel.value,
    etaLabel: etaLabel.value,
    packagingFeeLabel: packagingFeeLabel.value,
    deliveryFeeLabel: deliveryFeeLabel.value,
  })
  if (!ok) ElMessage.warning('请允许浏览器弹出窗口后再打印')
}

function openTrace(row) {
  traceOrderId.value = row.id
  traceVisible.value = true
}

function openPay(row) {
  payOrder.value = row
  payForm.payChannel = 'alipay'
  payForm.payPassword = ''
  payVisible.value = true
}

async function submitPay() {
  if (!payOrder.value) return
  if (!['alipay', 'wechat'].includes(payForm.payChannel)) {
    ElMessage.warning('请选择支付方式')
    return
  }
  if (String(payForm.payPassword || '').trim().length < 4) {
    ElMessage.warning('请输入支付密码（至少 4 位）')
    return
  }
  paying.value = true
  try {
    await http.post(`/api/orders/${payOrder.value.id}/pay`, {
      payChannel: payForm.payChannel,
      payPassword: payForm.payPassword,
    })
    ElMessage.success('支付成功')
    payVisible.value = false
    load()
  } finally {
    paying.value = false
  }
}

function openRefund(row) {
  refundOrder.value = row
  refundForm.refundType = 'refund_only'
  refundForm.reasonChip = refundReasonOptions.value[0] || ''
  refundForm.reasonDetail = ''
  refundVisible.value = true
}

function composeRefundReason() {
  const chip = String(refundForm.reasonChip || '').trim()
  const detail = String(refundForm.reasonDetail || '').trim()
  if (chip && chip !== '其他') {
    return detail ? `${chip}：${detail}` : chip
  }
  return detail || chip
}

async function submitRefund() {
  if (!refundOrder.value) return
  const reason = composeRefundReason()
  if (!reason) {
    ElMessage.warning(refundReasonRequiredHint.value)
    return
  }
  if (noCasualRefund.value && /无理由|不想要|不喜欢|拍错|买错/.test(reason)) {
    ElMessage.warning('不支持无理由退货')
    return
  }
  refundSaving.value = true
  try {
    await http.post(`/api/orders/${refundOrder.value.id}/refund`, {
      reason,
      refundType: refundTypeOn.value ? refundForm.refundType : '',
    })
    ElMessage.success('已提交售后申请')
    refundVisible.value = false
    load()
  } finally {
    refundSaving.value = false
  }
}

async function fillRefundTracking(row) {
  const { value } = await ElMessageBox.prompt(
    refundTrackingHint.value || '请填写退货物流单号',
    refundTrackingLabel.value,
    { inputPlaceholder: '承运单号' },
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

function canSetWarranty(row) {
  if (!warrantyOn.value || !row) return false
  return ['shipped', 'in_transit', 'signed', 'completed'].includes(row.status)
}

function invoiceStatusText(st) {
  if (st === 'pending') return invoiceStatusPending.value
  if (st === 'issued') return invoiceStatusIssued.value
  return st || '—'
}

function canRequestInvoice(row) {
  if (!invoiceOn.value || !row) return false
  if (row.invoiceStatus === 'issued') return false
  return ['confirmed', 'shipped', 'in_transit', 'signed', 'completed', 'pending'].includes(row.status)
}

function canDownloadInvoice(row) {
  if (!invoiceOn.value || !thicken.value.invoicePdf || !row) return false
  return !!(row.invoiceTitle || row.invoiceStatus)
}

function openInvoice(row) {
  invoiceOrder.value = row
  invoiceForm.title = String(row.invoiceTitle || '').trim()
  invoiceVisible.value = true
}

async function submitInvoice() {
  const title = String(invoiceForm.title || '').trim()
  if (!title) {
    ElMessage.warning(`请填写${invoiceTitleLabel.value}`)
    return
  }
  invoiceSaving.value = true
  try {
    await http.put(`/api/orders/${invoiceOrder.value.id}/invoice`, {
      invoiceTitle: title,
      invoiceStatus: 'pending',
    })
    ElMessage.success('已提交开票申请')
    invoiceVisible.value = false
    load()
  } finally {
    invoiceSaving.value = false
  }
}

function downloadInvoice(row) {
  const ok = printOrderInvoice(row, {
    labels: getSchema()?.labels || {},
    orderNoun: orderNoun.value,
  })
  if (!ok) ElMessage.warning('请允许浏览器弹出窗口后再下载')
  void invoiceDownloadHint.value
  void invoiceStatusLabel.value
}

function canSetRefundFee(row) {
  if (!refundFeeOn.value || !isCinema.value || !row) return false
  return ['pending', 'confirmed', 'shipped', 'cancelled', 'refunded'].includes(row.status)
    || !!row.refundStatus
}

async function copyShareToken(row) {
  const token = String(row?.shareToken || '').trim()
  if (!token) return
  try {
    await navigator.clipboard.writeText(token)
    ElMessage.success(orderShareHint.value || '口令已复制')
  } catch {
    ElMessage.info(`${orderShareLabel.value}：${token}`)
  }
}

function setWarranty(row) {
  warrantyOrder.value = row
  warrantyForm.until = String(row.warrantyUntil || '').slice(0, 10)
  warrantyVisible.value = true
}

function setRefundFee(row) {
  refundFeeOrder.value = row
  refundFeeForm.fee = Number(row.refundFeeYuan || 0)
  refundFeeVisible.value = true
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

async function submitReview(row) {
  const { value: rating } = await ElMessageBox.prompt('请输入评分 1～5', '订单评价', {
    inputValue: '5',
    inputPattern: /^[1-5]$/,
    inputErrorMessage: '请输入 1～5',
  }).catch(() => ({ value: null }))
  if (rating == null) return
  const { value: body } = await ElMessageBox.prompt('评价内容（选填）', '订单评价', {
    inputPlaceholder: '口味、包装、配送体验…',
    inputValue: '',
  }).catch(() => ({ value: null }))
  if (body == null) return
  let imageUrl = ''
  if (thicken.value.reviewImage) {
    const imgLabel = getSchema()?.labels?.reviewImageLabel || '晒图'
    const imgHint = getSchema()?.labels?.reviewImageHint || '可填写一张图片链接（选填）'
    const { value: img } = await ElMessageBox.prompt(imgHint, imgLabel, {
      inputPlaceholder: 'https://…',
      inputValue: '',
    }).catch(() => ({ value: null }))
    if (img == null) return
    imageUrl = String(img || '').trim()
  }
  await http.post('/api/order-reviews', {
    orderId: row.id,
    rating: Number(rating),
    body: String(body || '').trim(),
    imageUrl,
  })
  ElMessage.success('评价已提交')
  load()
}

onMounted(() => {
  load()
})
</script>

<style scoped>
.hero { margin-bottom: 16px; }
.hero h1 { margin: 0 0 6px; font-size: 22px; }
.hero p { margin: 0 0 10px; color: var(--portal-muted, #64748b); font-size: 13px; }
.card {
  background: var(--portal-surface, #fff);
  border: var(--portal-border-width, 1px) solid var(--portal-line, #e2e8f0);
  border-radius: var(--portal-radius, 12px);
  box-shadow: var(--portal-shadow, none);
  padding: var(--portal-pad, 14px) 16px;
  margin-bottom: var(--portal-gap, 12px);
}
.hd { display: flex; justify-content: space-between; gap: 8px; align-items: center; }
.hd-title { display: inline-flex; align-items: center; gap: 8px; }
.sub { margin: 6px 0; color: var(--portal-muted, #64748b); font-size: 12px; }
.sub.refund { color: #b45309; }
.pay-cd { margin: 0 0 6px; color: #b45309; font-size: 13px; font-weight: 600; }
.pay-cd.urgent { color: #b91c1c; }
.group-buy { margin: 6px 0 10px; max-width: 280px; }
.ship { margin: 0 0 8px; color: var(--portal-muted, #475569); font-size: 12px; line-height: 1.5; }
.lines { margin: 0; padding-left: 18px; color: var(--portal-ink, #334155); font-size: 13px; }
.acts { margin-top: 10px; display: flex; flex-wrap: wrap; gap: 6px; }
.empty { text-align: center; color: var(--portal-muted, #94a3b8); padding: 40px 0; }
.pager { margin-top: 16px; display: flex; justify-content: flex-end; }
.pay-tip { margin: 0 0 12px; color: var(--portal-muted, #64748b); font-size: 13px; }
.muted { color: var(--portal-muted, #64748b); }
</style>
