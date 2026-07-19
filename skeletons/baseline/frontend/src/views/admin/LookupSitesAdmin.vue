<template>
  <div>
    <div class="toolbar">
      <el-button type="primary" @click="openSite()">新增{{ siteLabel }}</el-button>
      <el-button @click="load">刷新</el-button>
    </div>

    <h3 class="sec">{{ siteLabel }}</h3>
    <el-table :data="sites" stripe>
      <el-table-column prop="id" label="ID" width="70" />
      <el-table-column prop="name" :label="siteLabel + '名称'" min-width="140" />
      <el-table-column prop="remark" label="备注" min-width="160" />
      <el-table-column label="操作" width="160" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="openSite(row)">编辑</el-button>
          <el-button link type="danger" @click="removeSite(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <div class="toolbar mid">
      <el-select v-model="filterSiteId" clearable :placeholder="'筛选' + siteLabel" style="width:180px" @change="loadUnits">
        <el-option v-for="s in sites" :key="s.id" :label="s.name" :value="s.id" />
      </el-select>
      <el-button type="primary" @click="openUnit()">新增{{ unitLabel }}</el-button>
    </div>
    <h3 class="sec">{{ unitLabel }}</h3>
    <el-table :data="units" stripe>
      <el-table-column prop="id" label="ID" width="70" />
      <el-table-column :label="siteLabel" min-width="120">
        <template #default="{ row }">{{ siteName(row.siteId) }}</template>
      </el-table-column>
      <el-table-column prop="code" :label="unitLabel + '编号'" min-width="120" />
      <el-table-column prop="capacity" label="容量" width="90" />
      <el-table-column label="操作" width="160" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="openUnit(row)">编辑</el-button>
          <el-button link type="danger" @click="removeUnit(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="siteVisible" :title="(siteForm.id ? '编辑' : '新增') + siteLabel" width="420px">
      <el-form :model="siteForm" label-width="88px" require-asterisk-position="right">
        <el-form-item :label="siteLabel + '名称'" required>
          <el-input v-model="siteForm.name" maxlength="64" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="siteForm.remark" maxlength="128" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="siteVisible = false">取消</el-button>
        <el-button type="primary" @click="saveSite">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="unitVisible" :title="(unitForm.id ? '编辑' : '新增') + unitLabel" width="420px">
      <el-form :model="unitForm" label-width="88px" require-asterisk-position="right">
        <el-form-item :label="siteLabel" required>
          <el-select v-model="unitForm.siteId" style="width:100%">
            <el-option v-for="s in sites" :key="s.id" :label="s.name" :value="s.id" />
          </el-select>
        </el-form-item>
        <el-form-item :label="unitLabel + '编号'" required>
          <el-input v-model="unitForm.code" maxlength="32" />
        </el-form-item>
        <el-form-item label="容量">
          <el-input-number v-model="unitForm.capacity" :min="1" :max="99" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="unitVisible = false">取消</el-button>
        <el-button type="primary" @click="saveUnit">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import http from '../../api/http'

const siteLabel = ref('楼栋')
const unitLabel = ref('房间')
const sites = ref([])
const units = ref([])
const filterSiteId = ref(null)
const siteVisible = ref(false)
const unitVisible = ref(false)
const siteForm = reactive({ id: null, name: '', remark: '' })
const unitForm = reactive({ id: null, siteId: null, code: '', capacity: 4 })

function siteName(id) {
  const s = sites.value.find((x) => x.id === id)
  return s ? s.name : id
}

async function loadMeta() {
  const res = await http.get('/api/admin/lookups/meta')
  siteLabel.value = res.data.siteLabel || '楼栋'
  unitLabel.value = res.data.unitLabel || '房间'
}

async function load() {
  await loadMeta()
  const res = await http.get('/api/admin/lookups/sites')
  sites.value = res.data
  await loadUnits()
}

async function loadUnits() {
  const res = await http.get('/api/admin/lookups/units', {
    params: { siteId: filterSiteId.value || undefined },
  })
  units.value = res.data
}

function openSite(row) {
  Object.assign(siteForm, row
    ? { id: row.id, name: row.name || '', remark: row.remark || '' }
    : { id: null, name: '', remark: '' })
  siteVisible.value = true
}

async function saveSite() {
  if (!siteForm.name.trim()) {
    ElMessage.warning('请填写名称')
    return
  }
  const body = { name: siteForm.name, remark: siteForm.remark }
  if (siteForm.id) await http.put(`/api/admin/lookups/sites/${siteForm.id}`, body)
  else await http.post('/api/admin/lookups/sites', body)
  ElMessage.success('已保存')
  siteVisible.value = false
  load()
}

async function removeSite(row) {
  await ElMessageBox.confirm(`确认删除${siteLabel.value}「${row.name}」？`, '删除')
  await http.delete(`/api/admin/lookups/sites/${row.id}`)
  ElMessage.success('已删除')
  load()
}

function openUnit(row) {
  Object.assign(unitForm, row
    ? { id: row.id, siteId: row.siteId, code: row.code || '', capacity: row.capacity || 4 }
    : { id: null, siteId: filterSiteId.value || (sites.value[0] && sites.value[0].id) || null, code: '', capacity: 4 })
  unitVisible.value = true
}

async function saveUnit() {
  if (!unitForm.siteId || !unitForm.code.trim()) {
    ElMessage.warning('请填写完整')
    return
  }
  const body = { siteId: unitForm.siteId, code: unitForm.code, capacity: unitForm.capacity }
  if (unitForm.id) await http.put(`/api/admin/lookups/units/${unitForm.id}`, body)
  else await http.post('/api/admin/lookups/units', body)
  ElMessage.success('已保存')
  unitVisible.value = false
  loadUnits()
}

async function removeUnit(row) {
  await ElMessageBox.confirm(`确认删除${unitLabel.value}「${row.code}」？`, '删除')
  await http.delete(`/api/admin/lookups/units/${row.id}`)
  ElMessage.success('已删除')
  loadUnits()
}

onMounted(load)
</script>

<style scoped>
.toolbar { margin-bottom: 12px; display: flex; gap: 8px; }
.toolbar.mid { margin-top: 28px; }
.sec { margin: 0 0 10px; font-size: 15px; font-weight: 600; color: #303133; }
</style>
