<template>
  <div>
    <section class="hero">
      <div>
        <h1>{{ pageTitle }}</h1>
        <p>为车主发放或累加包月次卡次数。</p>
      </div>
      <div class="tools">
        <el-button @click="load">刷新</el-button>
        <el-button type="primary" @click="openGrant">发放次卡</el-button>
      </div>
    </section>
    <el-table :data="list" stripe empty-text="暂无次卡记录">
      <el-table-column label="用户" prop="username" width="140" />
      <el-table-column :label="packLabel" prop="packName" min-width="140" />
      <el-table-column :label="remainLabel" prop="remainCount" width="120" />
    </el-table>

    <el-dialog v-model="visible" :title="pageTitle" width="440px" destroy-on-close>
      <el-form label-position="top">
        <el-form-item label="用户名" required>
          <el-input v-model="form.username" maxlength="64" />
        </el-form-item>
        <el-form-item :label="packLabel">
          <el-input v-model="form.packName" maxlength="64" />
        </el-form-item>
        <el-form-item :label="remainLabel" required>
          <el-input-number v-model="form.remainCount" :min="1" :max="999" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="visible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="save">发放</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import http from '../../api/http'
import { getSchema, menuLabel } from '../../utils/domainSchema.js'

const labels = computed(() => getSchema()?.labels || {})
const pageTitle = computed(
  () => labels.value.parkingPassGrantLabel || menuLabel('admin', 'parking_pass_admin', '发放次卡'),
)
const packLabel = computed(() => labels.value.parkingPassPackLabel || '套餐名称')
const remainLabel = computed(() => labels.value.parkingPassRemainLabel || '剩余次数')
const list = ref([])
const visible = ref(false)
const saving = ref(false)
const form = reactive({
  username: '',
  packName: '包月次卡',
  remainCount: 10,
})

async function load() {
  const res = await http.get('/api/parking-passes/admin')
  list.value = Array.isArray(res.data) ? res.data : []
}

function openGrant() {
  form.username = ''
  form.packName = '包月次卡'
  form.remainCount = 10
  visible.value = true
}

async function save() {
  if (!form.username.trim()) {
    ElMessage.warning('请填写用户名')
    return
  }
  saving.value = true
  try {
    await http.post('/api/parking-passes/grant', {
      username: form.username.trim(),
      packName: form.packName.trim() || '包月次卡',
      remainCount: form.remainCount,
    })
    ElMessage.success('已发放')
    visible.value = false
    load()
  } finally {
    saving.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.hero {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 16px;
}
.hero h1 { margin: 0 0 6px; font-size: 22px; }
.hero p { margin: 0; color: var(--portal-muted, #64748b); font-size: 13px; }
.tools { display: flex; gap: 8px; }
</style>
