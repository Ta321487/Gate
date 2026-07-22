<template>
  <div>
    <div class="toolbar">
      <el-button type="primary" @click="openCreate">新建优惠券</el-button>
      <el-button @click="load">刷新</el-button>
    </div>
    <el-table :data="list" stripe>
      <el-table-column prop="code" label="券码" width="120" />
      <el-table-column prop="label" label="名称" min-width="140" />
      <el-table-column label="门槛/优惠" width="140">
        <template #default="{ row }">
          满{{ Number(row.minYuan || 0).toFixed(0) }}减{{ Number(row.offYuan || 0).toFixed(0) }}
        </template>
      </el-table-column>
      <el-table-column label="领取" width="100">
        <template #default="{ row }">
          {{ row.claimed || 0 }}
          <template v-if="Number(row.totalQuota) > 0">/ {{ row.totalQuota }}</template>
          <template v-else>/ ∞</template>
        </template>
      </el-table-column>
      <el-table-column prop="expireAt" label="过期" width="170" />
      <el-table-column prop="status" label="状态" width="90">
        <template #default="{ row }">{{ row.status === 'off' ? '下架' : '上架' }}</template>
      </el-table-column>
      <el-table-column label="操作" width="100" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
        </template>
      </el-table-column>
    </el-table>
    <div class="pager">
      <el-pagination
        v-model:current-page="page"
        v-model:page-size="size"
        background
        layout="total, prev, pager, next"
        :total="total"
        @current-change="load"
      />
    </div>

    <el-dialog v-model="visible" :title="form.id ? '编辑优惠券' : '新建优惠券'" width="480px">
      <el-form label-width="88px">
        <el-form-item label="券码" required>
          <el-input v-model="form.code" maxlength="32" :disabled="!!form.id" placeholder="如 SAVE10" />
        </el-form-item>
        <el-form-item label="名称">
          <el-input v-model="form.label" maxlength="64" placeholder="满50减10" />
        </el-form-item>
        <el-form-item label="门槛(元)">
          <el-input-number v-model="form.minYuan" :min="0" :precision="2" />
        </el-form-item>
        <el-form-item label="优惠(元)" required>
          <el-input-number v-model="form.offYuan" :min="0.01" :precision="2" />
        </el-form-item>
        <el-form-item label="发放上限">
          <el-input-number v-model="form.totalQuota" :min="0" />
          <span class="hint">0 表示不限</span>
        </el-form-item>
        <el-form-item label="过期时间">
          <el-input v-model="form.expireAt" placeholder="yyyy-MM-dd HH:mm:ss" />
        </el-form-item>
        <el-form-item v-if="form.id" label="状态">
          <el-select v-model="form.status" style="width: 140px">
            <el-option label="上架" value="active" />
            <el-option label="下架" value="off" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="visible = false">取消</el-button>
        <el-button type="primary" @click="save">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import http from '../../api/http'

const list = ref([])
const page = ref(1)
const size = ref(10)
const total = ref(0)
const visible = ref(false)
const form = reactive({
  id: null,
  code: '',
  label: '',
  minYuan: 0,
  offYuan: 10,
  totalQuota: 0,
  expireAt: '',
  status: 'active',
})

async function load() {
  const res = await http.get('/api/coupons/admin', {
    params: { page: page.value, size: size.value },
  })
  list.value = res.data?.list || []
  total.value = res.data?.total || 0
}

function openCreate() {
  Object.assign(form, {
    id: null,
    code: '',
    label: '',
    minYuan: 50,
    offYuan: 10,
    totalQuota: 0,
    expireAt: '',
    status: 'active',
  })
  visible.value = true
}

function openEdit(row) {
  Object.assign(form, {
    id: row.id,
    code: row.code || '',
    label: row.label || '',
    minYuan: Number(row.minYuan || 0),
    offYuan: Number(row.offYuan || 0),
    totalQuota: Number(row.totalQuota || 0),
    expireAt: row.expireAt || '',
    status: row.status === 'off' ? 'off' : 'active',
  })
  visible.value = true
}

async function save() {
  const body = {
    code: form.code.trim(),
    label: form.label.trim(),
    minYuan: form.minYuan,
    offYuan: form.offYuan,
    totalQuota: form.totalQuota,
    expireAt: form.expireAt || undefined,
    status: form.status,
  }
  if (form.id) {
    await http.put(`/api/coupons/admin/${form.id}`, body)
  } else {
    await http.post('/api/coupons/admin', body)
  }
  ElMessage.success('已保存')
  visible.value = false
  load()
}

onMounted(load)
</script>

<style scoped>
.toolbar { display: flex; gap: 8px; margin-bottom: 12px; }
.pager { margin-top: 16px; display: flex; justify-content: flex-end; }
.hint { margin-left: 8px; color: var(--portal-muted, #94a3b8); font-size: 12px; }
</style>
