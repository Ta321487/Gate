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
          {{ orderNoun }} #<CopyableId :value="row.id" />
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
      <div class="card-foot">
        <div class="card-acts">
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

<script setup src="./MyOrders.setup.js"></script>

<style scoped src="./MyOrders.css"></style>
