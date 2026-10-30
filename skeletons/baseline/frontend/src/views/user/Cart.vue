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

    <el-table
      :data="list"
      stripe
      empty-text="购物车为空，去浏览加购吧"
      :data-trade-surface="tradeSurface || 'cards'"
      :class="{
        'trade-shelfgrid': tradeSurface === 'shelfgrid',
        'trade-menuboard': tradeSurface === 'menuboard',
        'trade-showtime': tradeSurface === 'showtime',
      }"
    >
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
        <div v-if="demoPay" class="loy-line muted">在线支付（账户余额）</div>
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
              placeholder="请选择标签"
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
            clearable
            placeholder="选择已领取的优惠券"
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

<script setup src="./Cart.setup.js"></script>

<style scoped src="./Cart.css"></style>
