<template>
  <div>
    <section class="hero">
      <h1>{{ pageTitle }}</h1>
      <p>{{ pageLead }}</p>
    </section>

    <section v-if="canPost" class="composer card">
      <el-form label-position="top" class="form">
        <div class="grid">
          <el-form-item label="收件人" required>
            <el-input v-model="form.receiverName" maxlength="64" placeholder="收件人姓名" />
          </el-form-item>
          <el-form-item label="收件电话" required>
            <el-input v-model="form.receiverPhone" maxlength="32" placeholder="手机号" />
          </el-form-item>
        </div>
        <el-form-item label="收件地址" required>
          <el-input v-model="form.destAddress" maxlength="255" placeholder="省市区及详细地址" />
        </el-form-item>
        <el-form-item label="物品说明" required>
          <el-input
            v-model="form.itemDesc"
            type="textarea"
            :rows="3"
            maxlength="255"
            show-word-limit
            placeholder="寄递物品名称、数量等"
          />
        </el-form-item>
        <el-button type="primary" :loading="posting" @click="submit">提交寄件</el-button>
      </el-form>
    </section>
    <GuestLoginHint v-else />

    <h2 class="sec">我的寄件</h2>
    <div class="table-scroll">
      <el-table :data="list" stripe>
        <el-table-column prop="receiverName" label="收件人" width="100" />
        <el-table-column prop="receiverPhone" label="电话" width="120" />
        <el-table-column prop="destAddress" label="地址" min-width="160" show-overflow-tooltip />
        <el-table-column prop="itemDesc" label="物品" min-width="120" show-overflow-tooltip />
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag size="small" :type="shipStatusTagType(row.status)" effect="plain">
              {{ statusLabel(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="trackingNo" label="运单号" width="130" show-overflow-tooltip />
        <el-table-column prop="createdAt" label="提交时间" width="170" />
        <el-table-column prop="handleNote" label="说明" min-width="120" show-overflow-tooltip />
      </el-table>
    </div>
    <div v-if="!list.length" class="empty">暂无寄件记录</div>
    <div v-if="canPost" class="pager">
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
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import http from '../../api/http'
import GuestLoginHint from '../../components/GuestLoginHint.vue'
import { getSchema } from '../../utils/domainSchema.js'
import { isLoggedIn } from '../../utils/session.js'

const labels = computed(() => getSchema()?.labels || {})
const pageTitle = computed(() => labels.value.parcelShipPageTitle || '寄件登记')
const pageLead = computed(
  () =>
    labels.value.parcelShipPageLead ||
    '填写收件信息与物品说明提交寄件；到站后由店员受理并登记寄出。',
)
const okMsg = computed(() => labels.value.parcelShipOkMessage || '寄件已提交，请等待驿站受理')
const canPost = computed(() => isLoggedIn())

const form = reactive({ receiverName: '', receiverPhone: '', destAddress: '', itemDesc: '' })
const posting = ref(false)
const list = ref([])
const page = ref(1)
const size = ref(10)
const total = ref(0)

function statusLabel(s) {
  if (s === 'pending') return '待受理'
  if (s === 'accepted') return '已受理'
  if (s === 'shipped') return '已寄出'
  if (s === 'rejected') return '已驳回'
  return s || '—'
}

function shipStatusTagType(s) {
  if (s === 'pending') return 'warning'
  if (s === 'accepted') return 'info'
  if (s === 'shipped') return 'success'
  if (s === 'rejected') return 'danger'
  return ''
}

async function load() {
  if (!canPost.value) {
    list.value = []
    total.value = 0
    return
  }
  const res = await http.get('/api/parcel-ship/mine', {
    params: { page: page.value, size: size.value },
  })
  list.value = res.data?.list || []
  total.value = res.data?.total || 0
}

async function submit() {
  if (!form.receiverName.trim()) {
    ElMessage.warning('请填写收件人')
    return
  }
  if (!form.receiverPhone.trim()) {
    ElMessage.warning('请填写收件电话')
    return
  }
  if (!form.destAddress.trim()) {
    ElMessage.warning('请填写收件地址')
    return
  }
  if (!form.itemDesc.trim()) {
    ElMessage.warning('请填写物品说明')
    return
  }
  posting.value = true
  try {
    await http.post('/api/parcel-ship', { ...form })
    ElMessage.success(okMsg.value)
    form.receiverName = ''
    form.receiverPhone = ''
    form.destAddress = ''
    form.itemDesc = ''
    page.value = 1
    await load()
  } finally {
    posting.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.hero { margin-bottom: 16px; }
.hero h1 { margin: 0 0 6px; font-size: 22px; }
.hero p { margin: 0; color: var(--portal-muted, #606266); font-size: 14px; }
.card {
  background: var(--el-bg-color);
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 16px;
}
.grid { display: grid; grid-template-columns: 1fr 1fr; gap: 0 16px; }
.sec { margin: 8px 0 12px; font-size: 16px; }
.empty { color: var(--portal-muted, #94a3b8); padding: 12px 0; }
.pager { margin-top: 12px; display: flex; justify-content: flex-end; }
@media (max-width: 640px) {
  .grid { grid-template-columns: 1fr; }
}
</style>
