<template>
  <div class="page" :data-account-face="accountFace">
    <el-button link type="primary" class="back" @click="goBack">← 返回</el-button>

    <div class="af-page-bg">
    <div class="af-shell">
      <div class="af-side">
        <section class="hero af-hero">
          <h1>{{ profileCopy.title }}</h1>
          <p>{{ profileCopy.lead }}</p>
        </section>

        <p v-if="!form.profileEditable" class="locked">顶级管理员不提供个人资料修改。</p>

        <section class="card identity af-identity">
          <div class="avatar-slot">
            <el-avatar :size="72" :src="form.avatarUrl || undefined" class="avatar">
              {{ (form.nickname || form.username || '?').slice(0, 1) }}
            </el-avatar>
            <el-upload
              v-if="form.profileEditable"
              class="avatar-up"
              :show-file-list="false"
              accept="image/*"
              :http-request="onAvatar"
            >
              <button type="button" class="avatar-btn">换头像</button>
            </el-upload>
          </div>
          <div class="who">
            <div class="nick">{{ displayName }}</div>
            <div class="uid">@{{ form.username }}</div>
            <div v-if="form.profileEditable" class="complete">
              <div class="complete-row">
                <span>{{ profileCompletenessLabel }}</span>
                <strong>{{ profileCompletePct }}%</strong>
              </div>
              <el-progress :percentage="profileCompletePct" :stroke-width="8" :show-text="false" />
              <p v-if="datingCompletenessHint" class="complete-hint">{{ datingCompletenessHint }}</p>
              <p v-if="profileMissingLabels.length" class="complete-hint">
                {{ datingCompletenessMissingLead }}{{ profileMissingLabels.slice(0, 4).join('、') }}
                <template v-if="profileMissingLabels.length > 4">等</template>
              </p>
            </div>
          </div>
        </section>
      </div>

      <div class="af-main">
    <el-tabs v-model="activeTab" class="settings-tabs" :tab-position="tabsPosition">
      <el-tab-pane label="资料" name="profile">
        <section v-if="form.profileEditable && orgFeatureOn" class="card">
          <el-form label-position="top">
            <el-form-item :label="orgPickLabel">
              <el-select v-model="form.orgId" clearable filterable style="max-width: 320px" :placeholder="orgPickPlaceholder">
                <el-option v-for="o in orgOptions" :key="o.id" :label="o.name" :value="o.id" />
              </el-select>
            </el-form-item>
          </el-form>
        </section>

        <!-- 余额/积分摘要；流水不嵌本页（避免瀑布） -->
        <section v-if="showBuyerLoyalty && loyalty" class="card block loyalty">
          <h2 class="block-title">账户权益</h2>
          <div class="loy-grid">
            <div v-if="walletOn"><span class="k">账户余额</span><strong>¥{{ Number(loyalty.balanceYuan || 0).toFixed(2) }}</strong></div>
            <div v-if="pointsOn"><span class="k">积分</span><strong>{{ loyalty.points || 0 }}</strong></div>
            <div v-if="tierOn"><span class="k">会员</span><strong>{{ loyalty.memberTierLabel || '—' }}</strong></div>
            <div v-if="tierOn"><span class="k">累计消费</span><strong>¥{{ Number(loyalty.spendTotalYuan || 0).toFixed(2) }}</strong></div>
          </div>
          <div
            v-if="tierOn"
            class="tier-bar"
            :class="`tone-${memberTierTone(loyalty.memberTierLabel || loyalty.memberTier)}`"
            :title="loyalty.memberTierLabel || ''"
          >
            <i :style="{ width: tierBarWidth }" />
          </div>
          <div class="recharge-row">
            <el-button v-if="walletOn" type="primary" plain size="small" @click="openRecharge">充值</el-button>
            <el-button
              v-if="pointsOn && pointsLedgerPath"
              link
              type="primary"
              size="small"
              @click="router.push(pointsLedgerPath)"
            >积分流水</el-button>
          </div>
          <p class="loy-hint">
            <template v-if="walletOn">余额可在此充值；</template>
            {{ pointsHint }}
          </p>
        </section>

        <el-form
          class="form"
          :model="form"
          label-position="top"
          require-asterisk-position="right"
          :disabled="!form.profileEditable"
          @submit.prevent
        >
          <section class="card block">
            <h2 class="block-title">基本信息</h2>
            <div class="grid">
              <el-form-item label="昵称">
                <el-input v-model="form.nickname" placeholder="怎么称呼你" maxlength="32" show-word-limit />
              </el-form-item>
              <el-form-item
                v-for="f in basicFields"
                :key="f.key"
                :label="f.label"
                :required="!!f.required"
              >
                <el-select
                  v-if="f.type === 'select' && f.storage !== 'phone'"
                  v-model="form.extras[f.key]"
                  clearable
                  :placeholder="f.placeholder || `请选择${f.label}`"
                  style="width: 100%"
                >
                  <el-option v-for="opt in f.options || []" :key="opt" :label="opt" :value="opt" />
                </el-select>
                <el-input
                  v-else-if="f.storage === 'phone'"
                  v-model="form.phone"
                  disabled
                  :maxlength="f.maxLength || 20"
                  :placeholder="f.placeholder || '手机号'"
                />
                <el-input
                  v-else-if="f.key === 'email'"
                  v-model="form.extras[f.key]"
                  disabled
                  :maxlength="f.maxLength || 64"
                  :placeholder="f.placeholder || f.label"
                />
                <el-input
                  v-else
                  v-model="form.extras[f.key]"
                  :maxlength="f.maxLength || 64"
                  :placeholder="f.placeholder || f.label"
                />
              </el-form-item>
            </div>
          </section>

          <section v-if="bizFields.length" class="card block">
            <h2 class="block-title">{{ bizSectionTitle }}</h2>
            <div class="grid">
              <el-form-item
                v-for="f in bizFields"
                :key="f.key"
                :label="f.label"
                :required="isProfileFieldRequired(f, form.extras)"
                :class="{ wide: isWideField(f) }"
              >
                <el-select
                  v-if="f.type === 'select'"
                  v-model="form.extras[f.key]"
                  clearable
                  :placeholder="f.placeholder || `请选择${f.label}`"
                  style="width: 100%"
                  @change="onBizSelectChange(f)"
                >
                  <el-option v-for="opt in f.options || []" :key="opt" :label="opt" :value="opt" />
                </el-select>
                <el-input
                  v-else
                  v-model="form.extras[f.key]"
                  :maxlength="f.maxLength || 64"
                  :placeholder="f.placeholder || f.label"
                />
              </el-form-item>
            </div>
          </section>

          <section v-if="form.profileEditable" class="card block">
            <h2 class="block-title">实名确认</h2>
            <el-checkbox v-model="form.realNameAcked" :label="labels.realNameAckLabel || '我确认以上姓名信息属实'" />
            <p class="hint">非公安核验，仅本系统内勾选确认。</p>
          </section>

          <div v-if="form.profileEditable" class="actions">
            <el-button type="primary" :loading="saving" @click="save">保存修改</el-button>
          </div>
        </el-form>
      </el-tab-pane>

      <el-tab-pane label="安全" name="security">
        <el-form
          class="form"
          :model="form"
          label-position="top"
          require-asterisk-position="right"
          :disabled="!form.profileEditable"
          @submit.prevent
        >
          <section class="card block">
            <h2 class="block-title">
              登录密码
              <span class="hint">不改请留空</span>
            </h2>
            <div class="grid">
              <el-form-item label="原密码" class="wide">
                <el-input
                  v-model="form.oldPassword"
                  type="password"
                  show-password
                  autocomplete="current-password"
                  placeholder="修改时必填"
                />
              </el-form-item>
              <el-form-item label="新密码">
                <el-input
                  v-model="form.newPassword"
                  type="password"
                  show-password
                  autocomplete="new-password"
                  :placeholder="strengthHint"
                />
              </el-form-item>
              <el-form-item label="确认密码">
                <el-input
                  v-model="form.confirmPassword"
                  type="password"
                  show-password
                  autocomplete="new-password"
                  placeholder="再次输入"
                />
              </el-form-item>
              <p class="pwd-hint">{{ strengthHint }}</p>
            </div>
          </section>

          <section class="card block">
            <h2 class="block-title">
              {{ labels.securityQuestionLabel || '密保问题' }}
              <span class="hint">用于找回密码；不改请留空</span>
            </h2>
            <div class="grid">
              <el-form-item :label="labels.securityQuestionLabel || '密保问题'" class="wide">
                <el-input v-model="form.securityQuestion" :placeholder="hasSecurityQuestion ? '已设置，填写则覆盖' : '选填'" />
              </el-form-item>
              <el-form-item :label="labels.securityAnswerLabel || '密保答案'" class="wide">
                <el-input v-model="form.securityAnswer" placeholder="填写问题后必填" autocomplete="off" />
              </el-form-item>
            </div>
          </section>

          <section v-if="form.profileEditable" class="card block">
            <h2 class="block-title">改绑手机 / 邮箱 <span class="hint">{{ labels.changeContactHint || '修改手机号或邮箱需填写验证码' }}</span></h2>
            <div class="grid">
              <el-form-item label="改绑字段">
                <el-select v-model="contactField" style="width: 100%">
                  <el-option label="手机号" value="phone" />
                  <el-option label="邮箱" value="email" />
                </el-select>
              </el-form-item>
              <el-form-item label="新值">
                <el-input v-model="contactValue" :placeholder="contactField === 'phone' ? (labels.phoneFormatHint || '11 位手机号') : (labels.emailFormatHint || '邮箱')" />
              </el-form-item>
              <el-form-item label="验证码" class="wide">
                <div class="captcha-row">
                  <el-input v-model="contactCaptcha" maxlength="4" placeholder="验证码" />
                  <button
                    type="button"
                    class="captcha-btn"
                    :aria-label="labels.captchaRefreshHint || '点击刷新验证码'"
                    @click="loadContactCaptcha"
                  >
                    <img v-if="contactCaptchaImg" :src="contactCaptchaImg" alt="验证码图片，点击可刷新" />
                    <span v-else>加载</span>
                  </button>
                </div>
              </el-form-item>
            </div>
            <el-button type="primary" plain :loading="contactSaving" @click="submitContact">提交改绑</el-button>
          </section>

          <div v-if="form.profileEditable" class="actions">
            <el-button type="primary" :loading="saving" @click="save">保存安全设置</el-button>
          </div>
        </el-form>
      </el-tab-pane>

      <el-tab-pane label="设备" name="devices">
        <section class="card block">
          <h2 class="block-title">最近登录 <span class="hint">{{ labels.remoteLoginHint || '' }}</span></h2>
          <el-table :data="loginLogs" size="small" stripe empty-text="暂无登录记录">
            <el-table-column prop="createdAt" label="时间" width="170" />
            <el-table-column prop="geoHint" label="来源" width="100" />
            <el-table-column prop="ip" label="IP" width="130" />
            <el-table-column prop="userAgent" label="设备" min-width="160" show-overflow-tooltip />
          </el-table>
        </section>

        <section class="card block">
          <h2 class="block-title">登录设备</h2>
          <el-table :data="mySessions" size="small" stripe empty-text="暂无在线会话">
            <el-table-column prop="createdAt" label="登录时间" width="170" />
            <el-table-column prop="ip" label="IP" width="130" />
            <el-table-column prop="userAgent" label="设备" min-width="160" show-overflow-tooltip />
            <el-table-column label="操作" width="100">
              <template #default="{ row }">
                <el-tag v-if="row.current" size="small">当前</el-tag>
                <el-button v-else link type="danger" @click="kickSession(row)">下线</el-button>
              </template>
            </el-table-column>
          </el-table>
        </section>
      </el-tab-pane>

      <el-tab-pane label="其他" name="other">
        <section v-if="myDocLinks.length" class="card block">
          <h2 class="block-title">{{ labels.myDocsTitle || '我的单据' }}</h2>
          <div class="doc-links">
            <el-button
              v-for="d in myDocLinks"
              :key="d.key"
              plain
              @click="router.push(d.to)"
            >{{ d.label }}</el-button>
          </div>
        </section>

        <section v-if="form.profileEditable" class="card block">
          <h2 class="block-title">{{ labels.cancelAccountLabel || '申请注销账号' }}</h2>
          <el-input v-model="cancelReason" type="textarea" :rows="2" placeholder="说明注销原因（选填）" />
          <el-button class="mt" type="danger" plain :loading="cancelSaving" @click="submitCancel">提交申请</el-button>
        </section>

        <el-empty v-if="!myDocLinks.length && !form.profileEditable" description="暂无其他设置" />
      </el-tab-pane>
    </el-tabs>
      </div>
    </div>
    </div>

    <el-dialog v-model="rechargeVisible" title="账户充值" width="400px" destroy-on-close>
      <p class="loy-hint">选择充值金额，即时到账。</p>
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
        <el-button type="primary" :loading="recharging" @click="doRecharge">确认充值</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup src="./Profile.setup.js"></script>

<style scoped src="./Profile.css"></style>
