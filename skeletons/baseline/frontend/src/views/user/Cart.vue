<template>
  <div>
    <section class="hero">
      <h1>{{ cartLabel }}</h1>
      <p>确认数量后提交{{ orderNoun }}。</p>
      <p v-if="stockLockHint" class="muted">{{ stockLockHint }}</p>
      <div class="tools">
        <el-button @click="load">刷新</el-button>
        <el-button v-if="cartSelectOn && invalidCount" @click="clearInvalid">{{ cartClearInvalidLabel }}</el-button>
        <el-button type="primary" :disabled="!selectedValid.length" :loading="placing" @click="openCheckout">
          提交{{ orderNoun }}
        </el-button>
      </div>
    </section>

    <el-table :data="list" stripe empty-text="购物车为空，去浏览加购吧">
      <el-table-column v-if="cartSelectOn" width="88">
        <template #header>
          <el-checkbox
            :model-value="allValidChecked"
            :indeterminate="someValidChecked && !allValidChecked"
            @change="toggleSelectAll"
          >{{ cartSelectAllLabel }}</el-checkbox>
        </template>
        <template #default="{ row }">
          <el-checkbox
            :model-value="isSelected(row)"
            :disabled="!!row.invalid"
            @change="(v) => setSelected(row, v)"
          />
        </template>
      </el-table-column>
      <el-table-column prop="title" label="名称" min-width="160">
        <template #default="{ row }">
          <span :class="{ invalid: row.invalid }">{{ row.title || '已下架' }}</span>
          <p v-if="row.invalid" class="tip muted">{{ row.invalidReason || cartInvalidHint }}</p>
        </template>
      </el-table-column>
      <el-table-column v-if="marketplace" label="店铺" min-width="120" show-overflow-tooltip>
        <template #default="{ row }">{{ row.shopName || '—' }}</template>
      </el-table-column>
      <el-table-column prop="priceYuan" label="单价" width="100" />
      <el-table-column label="数量" width="140">
        <template #default="{ row }">
          <el-input-number
            v-model="row.qty"
            :min="1"
            :max="99"
            size="small"
            :disabled="!!row.invalid"
            @change="(v) => saveQty(row, v)"
          />
        </template>
      </el-table-column>
      <el-table-column prop="lineYuan" label="小计" width="100" />
      <el-table-column label="操作" width="150" fixed="right">
        <template #default="{ row }">
          <el-button
            v-if="cartChangeSpecOn && !row.invalid"
            link
            type="primary"
            @click="changeSpec(row)"
          >{{ cartChangeSpecLabel }}</el-button>
          <el-button link type="danger" @click="remove(row)">移除</el-button>
        </template>
      </el-table-column>
    </el-table>
    <div v-if="list.length" class="total">
      <p v-if="cartFreeShipOn && freeShipText" class="loy-line muted free-ship">{{ freeShipText }}</p>
      <template v-if="anyLoyalty">
        <div v-if="walletOn" class="loy-line">
          账户余额 ¥{{ Number(account.balanceYuan || 0).toFixed(2) }}
          <el-button link type="primary" class="recharge-link" @click="openRecharge">充值</el-button>
        </div>
        <div v-if="demoPay" class="loy-line muted">支付宝 / 微信在线支付</div>
        <div v-if="pointsOn" class="loy-line">积分 {{ account.points || 0 }}</div>
        <div v-if="tierOn && account.memberTierLabel" class="loy-line">会员 {{ account.memberTierLabel }}</div>
      </template>
      <div>合计 ¥{{ totalYuan }}</div>
      <template v-if="preview && (discountOn || tierOn || couponOn)">
        <div v-if="Number(preview.discountYuan) > 0" class="loy-line muted">满减 −¥{{ Number(preview.discountYuan).toFixed(2) }}</div>
        <div v-if="Number(preview.tierDiscountRate) < 1" class="loy-line muted">
          会员折扣 ×{{ preview.tierDiscountRate }}
        </div>
        <div v-if="Number(preview.couponOffYuan) > 0" class="loy-line muted">
          券 {{ preview.couponCode }} −¥{{ Number(preview.couponOffYuan).toFixed(2) }}
        </div>
        <div class="payable">应付 ¥{{ Number(preview.payableYuan || totalYuan).toFixed(2) }}</div>
      </template>
      <div v-else-if="preview && walletOn" class="payable">应付 ¥{{ Number(preview.payableYuan || totalYuan).toFixed(2) }}</div>
      <div v-if="walletOn && preview && preview.balanceEnough === false" class="warn">
        账户余额不足，请先充值
        <el-button link type="primary" @click="openRecharge">去充值</el-button>
      </div>
    </div>

    <el-dialog v-model="checkoutVisible" :title="`提交${orderNoun}`" :width="lineCustom ? '640px' : '520px'" destroy-on-close>
      <el-form label-position="top">
        <el-form-item :label="deliveryTypeLabel" required>
          <el-select v-model="form.deliveryType" style="width: 100%">
            <el-option v-for="opt in deliveryOptions" :key="opt" :label="opt" :value="opt" />
          </el-select>
        </el-form-item>
        <template v-if="deliveryWindow">
          <el-form-item label="配送日期" required>
            <el-date-picker
              v-model="form.deliveryOn"
              type="date"
              value-format="YYYY-MM-DD"
              placeholder="选择日期"
              style="width: 100%"
              @change="loadWindow"
            />
          </el-form-item>
          <el-form-item label="配送时段" required>
            <el-radio-group v-model="form.slotId" class="slot-list">
              <el-radio
                v-for="s in windowSlots"
                :key="s.id"
                :value="s.id"
                :disabled="s.full"
              >
                {{ s.label }} {{ s.startHm }}-{{ s.endHm }}
                · {{ s.fulfillMode === 'same_day' ? '当日达' : '预订' }}
                · 余 {{ s.remain }}
              </el-radio>
            </el-radio-group>
            <p v-if="!windowSlots.length" class="tip muted">这一天没有可送时段，请换一个日期。</p>
            <p v-if="Number(windowRate) > 1" class="tip">{{ windowPriceName || '节日' }}加价 ×{{ Number(windowRate).toFixed(2) }}，计入本单。</p>
          </el-form-item>
        </template>
        <el-form-item v-if="groupBuy" label="拼团">
          <el-radio-group v-model="form.campaignId" class="slot-list">
            <el-radio :value="null">不参团</el-radio>
            <el-radio v-for="g in groupOpens" :key="g.id" :value="g.id">
              {{ g.verb }} · {{ g.title || '商品' }} · {{ g.joined }}/{{ g.targetSize }} · 截止 {{ g.deadline }}
            </el-radio>
          </el-radio-group>
          <p v-if="!groupOpens.length" class="tip muted">暂时没有可以参加的团。</p>
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
            <el-checkbox v-model="form.saveAsDefault">{{ defaultAddressSaveLabel }}</el-checkbox>
            <el-button text type="primary" class="save-addr" @click="saveAsAddress">保存到地址簿</el-button>
            <p v-if="defaultAddressHint" class="tip muted">{{ defaultAddressHint }}</p>
          </el-form-item>
        </template>
        <template v-if="isFood && foodThicken">
          <el-form-item v-if="needTableNo" :label="tableNoLabel" required>
            <el-input v-model="form.tableNo" maxlength="16" :placeholder="tableNoHint || '如 A12'" />
            <p v-if="tableNoHint" class="tip muted">{{ tableNoHint }}</p>
          </el-form-item>
          <el-form-item v-if="utensilOpts.length" :label="utensilOptLabel">
            <el-select v-model="form.utensilOpt" clearable style="width: 100%">
              <el-option v-for="opt in utensilOpts" :key="opt" :label="opt" :value="opt" />
            </el-select>
          </el-form-item>
          <el-form-item v-if="packOpts.length" :label="packOptLabel">
            <el-select v-model="form.packOpt" clearable style="width: 100%" @change="onPackOptChange">
              <el-option v-for="opt in packOpts" :key="opt" :label="opt" :value="opt" />
            </el-select>
          </el-form-item>
          <el-form-item v-if="packagingFeeOn">
            <el-checkbox v-model="form.packagingFee">{{ packagingFeeLabel }}（¥{{ packagingFeeYuan.toFixed(2) }}）</el-checkbox>
            <p v-if="packagingFeeHint" class="tip muted">{{ packagingFeeHint }}</p>
          </el-form-item>
          <el-form-item v-if="mergeCodeOn" :label="mergeCodeLabel">
            <el-input v-model="form.mergeCode" maxlength="16" :placeholder="mergeCodeHint || '选填'" />
            <p v-if="mergeCodeHint" class="tip muted">{{ mergeCodeHint }}</p>
          </el-form-item>
          <p v-if="stallOpenHoursOn && stallOpenHoursHint" class="tip muted">{{ stallOpenHoursLabel }}：{{ stallOpenHoursHint }}</p>
          <p v-if="stallClosedHint" class="tip muted">{{ stallClosedHint }}</p>
          <p v-if="needAddress && deliveryFeeLadderBody" class="tip muted">{{ deliveryFeeLabel }}：{{ deliveryFeeLadderBody }}</p>
          <p v-if="needAddress && etaHint" class="tip muted">{{ etaLabel }}：{{ etaHint }}</p>
          <p v-if="requiredCategoryOn && requiredCategoryHint" class="tip muted">{{ requiredCategoryLabel }}：{{ requiredCategoryHint }}</p>
          <p v-if="requiredCategoryOn && requiredCategoryMissingHint" class="tip muted">{{ requiredCategoryMissingHint }}</p>
        </template>
        <el-form-item v-if="!isFood && packagingFeeOn">
          <el-checkbox v-model="form.packagingFee">{{ packagingFeeLabel }}（¥{{ packagingFeeYuan.toFixed(2) }}）</el-checkbox>
          <p v-if="packagingFeeHint" class="tip muted">{{ packagingFeeHint }}</p>
        </el-form-item>
        <el-form-item v-if="isFood" :label="tasteLabel">
          <div v-if="tasteChips.length" class="taste-chips">
            <el-check-tag
              v-for="chip in tasteChips"
              :key="chip"
              :checked="tasteNoteHas(chip)"
              @change="toggleTasteChip(chip)"
            >{{ chip }}</el-check-tag>
          </div>
          <el-input
            v-model="form.tasteNote"
            type="textarea"
            :rows="2"
            maxlength="200"
            :placeholder="tastePlaceholder"
          />
          <p v-if="tasteNoteHint" class="tip muted">{{ tasteNoteHint }}</p>
        </el-form-item>
        <template v-if="lineCustom">
          <p class="tip muted">{{ customHint }}</p>
          <div v-for="row in list" :key="row.itemId" class="custom-block">
            <p class="custom-title">{{ row.title }}</p>
            <el-form-item :label="customTextLabel" required>
              <el-input v-model="extraOf(row).customText" maxlength="200" placeholder="如：姓名、纪念日" />
            </el-form-item>
            <el-form-item v-if="customSpecLabel" :label="customSpecLabel" required>
              <el-select v-model="extraOf(row).specChoice" filterable placeholder="请选择" style="width: 100%">
                <el-option v-for="opt in specOptions" :key="opt.id" :label="opt.label" :value="opt.label" />
              </el-select>
              <p v-if="!specOptions.length" class="tip muted">暂无可选规格。</p>
            </el-form-item>
            <el-form-item v-if="customImageLabel" :label="customImageLabel" required>
              <el-upload :show-file-list="false" accept="image/*" :http-request="(opt) => onCustomImage(row, opt)">
                <el-button size="small">{{ extraOf(row).attachUrl ? '重新上传' : '上传图片' }}</el-button>
              </el-upload>
              <a v-if="extraOf(row).attachUrl" class="link" :href="extraOf(row).attachUrl" target="_blank" rel="noopener noreferrer">已上传</a>
            </el-form-item>
          </div>
        </template>
        <template v-if="weighSale && weightRows.length">
          <div v-for="row in weightRows" :key="'w-' + row.itemId" class="custom-block">
            <p class="custom-title">{{ row.title }}</p>
            <el-form-item :label="`重量（${row.weightUnit || '斤'}）`" required>
              <el-input-number v-model="extraOf(row).weightQty" :min="0.01" :step="0.1" :precision="2" />
            </el-form-item>
          </div>
        </template>
        <el-form-item v-if="couponOn" label="优惠券">
          <el-select
            v-model="form.couponCode"
            filterable
            allow-create
            clearable
            default-first-option
            placeholder="选择已领券或输入已领券码"
            style="width: 100%"
            @change="refreshPreview"
          >
            <el-option
              v-for="c in mineCoupons"
              :key="c.id"
              :label="`${c.code} · ${c.label || '满减'}（减¥${Number(c.offYuan || 0).toFixed(0)}）`"
              :value="c.code"
            />
          </el-select>
          <p v-if="preview?.couponMessage" class="warn tip">{{ preview.couponMessage }}</p>
          <p v-else-if="preview?.couponCode" class="tip muted">
            已用 {{ preview.couponCode }}
            <template v-if="Number(preview.couponOffYuan) > 0"> −¥{{ Number(preview.couponOffYuan).toFixed(2) }}</template>
          </p>
          <p class="tip muted">
            <router-link to="/coupons">去领券</router-link>
          </p>
        </el-form-item>
        <el-form-item :label="orderRemarkLabel">
          <el-input v-model="form.remark" maxlength="200" :placeholder="orderRemarkHint || '选填'" />
        </el-form-item>
        <el-form-item v-if="invoiceTitleOn" :label="invoiceTitleLabel">
          <el-input v-model="form.invoiceTitle" maxlength="128" :placeholder="invoiceTitleHint || '选填'" />
          <p v-if="invoiceTitleHint" class="tip muted">{{ invoiceTitleHint }}</p>
        </el-form-item>
        <p v-if="spendDiscountHelpOn && spendDiscountHelpBody" class="tip muted">{{ spendDiscountHelpLabel }}：{{ spendDiscountHelpBody }}</p>
        <p v-if="giftPromoOn && giftPromoBody" class="tip muted">{{ giftPromoLabel }}：{{ giftPromoBody }}</p>
        <p v-if="couponMutexOn && couponMutexBody" class="tip muted">{{ couponMutexLabel }}：{{ couponMutexBody }}</p>
        <p v-if="memberDayOn && memberDayHint" class="tip muted">{{ memberDayLabel }}：{{ memberDayHint }}</p>
        <p v-if="pointsFreightOn && pointsFreightHint" class="tip muted">{{ pointsFreightHint }}</p>
        <el-form-item v-if="demoPay" label="支付方式" required>
          <el-radio-group v-model="form.payChannel">
            <el-radio value="alipay">支付宝</el-radio>
            <el-radio value="wechat">微信支付</el-radio>
          </el-radio-group>
          <p class="tip muted">{{ demoPayHint }}</p>
        </el-form-item>
        <el-form-item v-if="demoPay" label="支付密码" required>
          <el-input
            v-model="form.payPassword"
            type="password"
            show-password
            maxlength="32"
            placeholder="请输入支付密码（至少 4 位）"
          />
        </el-form-item>
        <div v-if="anyLoyalty && preview" class="checkout-loy">
          <p v-if="walletOn">
            账户余额 ¥{{ Number(preview.balanceYuan || account.balanceYuan || 0).toFixed(2) }}
            <el-button link type="primary" @click="openRecharge">充值</el-button>
          </p>
          <p v-if="Number(preview.discountYuan) > 0">满减 −¥{{ Number(preview.discountYuan).toFixed(2) }}</p>
          <p v-if="Number(preview.couponOffYuan) > 0">券抵扣 −¥{{ Number(preview.couponOffYuan).toFixed(2) }}</p>
          <template v-if="pointsOffsetOn">
            <p>可用积分 {{ Number(account.points || 0) }}</p>
            <el-form-item label="抵扣积分">
              <el-input-number
                v-model="form.offsetPoints"
                :min="0"
                :max="Math.max(0, Number(account.points || 0))"
                :step="100"
                controls-position="right"
              />
              <span class="tip muted">100 积分抵 ¥1，最多抵应付一半</span>
            </el-form-item>
            <p v-if="Number(preview.pointsOffsetYuan) > 0">
              积分抵扣 −¥{{ Number(preview.pointsOffsetYuan).toFixed(2) }}
            </p>
            <p v-if="!pointsPayOn && Number(preview.pointsOffsetYuan) > 0" class="tip muted">
              抵扣部分由积分支付，剩余金额仍扣账户余额。
            </p>
          </template>
          <p v-if="pointsPayOn" class="payable">
            本单需 {{ Math.ceil(Number(preview.payableYuan || totalYuan)) }} 积分兑换
          </p>
          <p v-else class="payable">应付 ¥{{ Number(preview.payableYuan || totalYuan).toFixed(2) }}</p>
          <p v-if="walletOn && preview.balanceEnough === false" class="warn">余额不足，请先充值后再提交</p>
        </div>
      </el-form>
      <template #footer>
        <el-button @click="checkoutVisible = false">取消</el-button>
        <el-button
          type="primary"
          :loading="placing"
          :disabled="walletOn && preview?.balanceEnough === false"
          @click="submitOrder"
        >{{ demoPay ? '确认支付并下单' : '确认提交' }}</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="specVisible" :title="cartChangeSpecLabel" width="400px" destroy-on-close>
      <el-select v-model="specPickId" placeholder="请选择规格" style="width: 100%" filterable>
        <el-option
          v-for="a in specAlts"
          :key="a.itemId"
          :label="`${a.specLabel} · ¥${Number(a.priceYuan || 0).toFixed(2)}`"
          :value="a.itemId"
        />
      </el-select>
      <p v-if="!specAlts.length" class="tip muted">{{ cartNoSpecHint }}</p>
      <template #footer>
        <el-button @click="specVisible = false">取消</el-button>
        <el-button type="primary" :disabled="!specPickId" @click="confirmSpec">确定</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="rechargeVisible" title="账户充值" width="400px" destroy-on-close>
      <p class="tip muted">选择充值金额，到账后用于下单扣款。</p>
      <div class="recharge-tiers">
        <el-button
          v-for="amt in rechargeTiers"
          :key="amt"
          :type="rechargeAmount === amt ? 'primary' : 'default'"
          @click="rechargeAmount = amt"
        >¥{{ amt }}</el-button>
      </div>
      <template #footer>
        <el-button @click="rechargeVisible = false">取消</el-button>
        <el-button type="primary" :loading="recharging" :disabled="!rechargeAmount" @click="doRecharge">确认充值</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
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

const router = useRouter()
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
    await http.post('/api/orders', payload)
    ElMessage.success(demoPay.value ? '支付成功，已下单' : '下单成功')
    checkoutVisible.value = false
    form.payPassword = ''
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
.hero p { margin: 0; color: var(--portal-muted, #64748b); font-size: 13px; width: 100%; }
.tools { display: flex; gap: 8px; flex-wrap: wrap; }
.invalid { color: var(--portal-muted, #94a3b8); text-decoration: line-through; }
.free-ship { font-weight: 600; }
.total { margin-top: 14px; text-align: right; font-weight: 700; font-size: 16px; }
.loy-line { font-weight: 500; font-size: 13px; color: var(--portal-muted, #475569); margin-bottom: 4px; }
.loy-line.muted { color: var(--portal-muted, #64748b); }
.recharge-link { margin-left: 6px; vertical-align: baseline; }
.recharge-tiers { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 12px; }
.payable { margin-top: 4px; color: #0f766e; }
.warn { color: #b91c1c; font-size: 13px; font-weight: 600; margin-top: 4px; }
.checkout-loy {
  margin-top: 8px;
  padding: 10px 12px;
  background: color-mix(in srgb, var(--portal-bg, #f8fafc) 72%, var(--portal-surface, #fff));
  border: var(--portal-border-width, 1px) solid var(--portal-line, #e2e8f0);
  border-radius: var(--portal-radius-sm, 8px);
  font-size: 13px;
  color: var(--portal-ink, #334155);
}
.checkout-loy p { margin: 0 0 4px; }
.checkout-loy .payable { font-weight: 700; font-size: 15px; }
.tip { margin: 4px 0 0; font-size: 12px; }
.tip.muted { color: var(--portal-muted, #64748b); }
.addr-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0 12px;
}
.addr-links { margin-top: 4px; }
.link { font-size: 13px; color: var(--el-color-primary); text-decoration: none; }
.save-addr { margin-left: 8px; }
.taste-chips { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 8px; }
@media (max-width: 520px) {
  .addr-grid { grid-template-columns: 1fr; }
}
</style>
