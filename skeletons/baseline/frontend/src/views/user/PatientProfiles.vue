<template>
  <div>
    <section class="hero">
      <div>
        <h1>{{ pageTitle }}</h1>
        <p>{{ pageLead }}</p>
      </div>
      <div class="tools">
        <el-button @click="load">刷新</el-button>
        <el-button type="primary" @click="openCreate">新增就诊人</el-button>
      </div>
    </section>

    <el-table :data="list" stripe empty-text="暂无就诊人，请新增">
      <el-table-column :label="nameLabel" prop="patientName" min-width="120" />
      <el-table-column :label="relationLabel" prop="relationLabel" width="100" />
      <el-table-column :label="idHintLabel" prop="idHint" width="120" />
      <el-table-column label="操作" width="100" fixed="right">
        <template #default="{ row }">
          <el-button link type="danger" @click="remove(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="visible" title="新增就诊人" width="440px" destroy-on-close>
      <el-form label-position="top" require-asterisk-position="right">
        <el-form-item :label="nameLabel" required>
          <el-input v-model="form.patientName" maxlength="32" />
        </el-form-item>
        <el-form-item :label="relationLabel">
          <el-select v-model="form.relationLabel" style="width: 100%">
            <el-option v-for="r in relationOptions" :key="r" :label="r" :value="r" />
          </el-select>
        </el-form-item>
        <el-form-item :label="idHintLabel">
          <el-input v-model="form.idHint" maxlength="32" placeholder="选填，如证件后四位" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="visible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="save">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import http from '../../api/http'
import { getSchema, menuLabel } from '../../utils/domainSchema.js'

const labels = computed(() => getSchema()?.labels || {})
const pageTitle = computed(
  () => labels.value.patientProfileTitle || menuLabel('user', 'patient_profile', '我的就诊人'),
)
const pageLead = computed(
  () => labels.value.patientProfileLead || '可维护本人与家属就诊人，预约时直接选用。',
)
const nameLabel = computed(() => labels.value.patientProfileNameLabel || '就诊人姓名')
const relationLabel = computed(() => labels.value.patientProfileRelationLabel || '关系')
const idHintLabel = computed(() => labels.value.patientProfileIdHintLabel || '证件后四位')
const relationOptions = ['本人', '配偶', '子女', '父母', '其它']

const list = ref([])
const visible = ref(false)
const saving = ref(false)
const form = reactive({
  patientName: '',
  relationLabel: '本人',
  idHint: '',
})

async function load() {
  const res = await http.get('/api/patient-profiles')
  list.value = Array.isArray(res.data) ? res.data : []
}

function openCreate() {
  form.patientName = ''
  form.relationLabel = '本人'
  form.idHint = ''
  visible.value = true
}

async function save() {
  if (!form.patientName.trim()) {
    ElMessage.warning(`请填写${nameLabel.value}`)
    return
  }
  saving.value = true
  try {
    await http.post('/api/patient-profiles', {
      patientName: form.patientName.trim(),
      relationLabel: form.relationLabel,
      idHint: form.idHint.trim(),
    })
    ElMessage.success('已保存')
    visible.value = false
    load()
  } finally {
    saving.value = false
  }
}

async function remove(row) {
  await ElMessageBox.confirm(`删除就诊人「${row.patientName}」？`, '删除')
  await http.post(`/api/patient-profiles/${row.id}/delete`)
  ElMessage.success('已删除')
  load()
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
.tools { display: flex; gap: 8px; flex-shrink: 0; }
</style>
