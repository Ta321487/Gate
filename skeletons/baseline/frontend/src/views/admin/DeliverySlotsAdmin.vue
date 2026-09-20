<template>
  <div>
    <div class="toolbar">
      <el-button type="primary" @click="openCreate">新建时段</el-button>
      <el-button @click="load">刷新</el-button>
    </div>
    <el-table :data="list" stripe>
      <el-table-column prop="label" label="名称" min-width="120" />
      <el-table-column label="时间" width="140">
        <template #default="{ row }">{{ row.startHm }}-{{ row.endHm }}</template>
      </el-table-column>
      <el-table-column prop="capacity" label="容量" width="80" />
      <el-table-column label="方式" width="100">
        <template #default="{ row }">{{ modeText(row.fulfillMode) }}</template>
      </el-table-column>
      <el-table-column prop="cutoffHm" label="截单" width="90" />
      <el-table-column label="状态" width="80">
        <template #default="{ row }">{{ row.enabled ? '启用' : '停用' }}</template>
      </el-table-column>
      <el-table-column label="操作" width="90">
        <template #default="{ row }">
          <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
        </template>
      </el-table-column>
    </el-table>
    <el-dialog v-model="visible" :title="form.id ? '编辑时段' : '新建时段'" width="460px">
      <el-form label-width="88px">
        <el-form-item label="名称" required>
          <el-input v-model="form.label" maxlength="64" />
        </el-form-item>
        <el-form-item label="开始">
          <el-time-picker v-model="form.startHm" format="HH:mm" value-format="HH:mm" placeholder="09:00" />
        </el-form-item>
        <el-form-item label="结束">
          <el-time-picker v-model="form.endHm" format="HH:mm" value-format="HH:mm" placeholder="12:00" />
        </el-form-item>
        <el-form-item label="容量" required>
          <el-input-number v-model="form.capacity" :min="1" />
        </el-form-item>
        <el-form-item label="方式" required>
          <el-select v-model="form.fulfillMode" style="width: 160px">
            <el-option label="当日达" value="same_day" />
            <el-option label="预订" value="preorder" />
            <el-option v-if="weighSale" label="次日达" value="next_day" />
          </el-select>
        </el-form-item>
        <el-form-item label="截单">
          <el-time-picker v-model="form.cutoffHm" format="HH:mm" value-format="HH:mm" placeholder="当日达可填" clearable />
        </el-form-item>
        <el-form-item label="排序">
          <el-input-number v-model="form.sortNo" :min="0" />
        </el-form-item>
        <el-form-item label="启用">
          <el-switch v-model="form.enabled" />
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
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import http from '../../api/http'
import { hasCap } from '../../utils/domainSchema.js'

const weighSale = computed(() => hasCap('weigh_sale'))
const list = ref([])
const visible = ref(false)
const form = reactive({
  id: null,
  label: '',
  startHm: '',
  endHm: '',
  capacity: 8,
  fulfillMode: 'preorder',
  cutoffHm: '',
  sortNo: 0,
  enabled: true,
})

function modeText(v) {
  if (v === 'same_day') return '当日达'
  if (v === 'next_day') return '次日达'
  return '预订'
}

async function load() {
  const res = await http.get('/api/delivery-windows/slots')
  list.value = res.data || []
}

function openCreate() {
  Object.assign(form, {
    id: null, label: '', startHm: '', endHm: '', capacity: 8,
    fulfillMode: 'preorder', cutoffHm: '', sortNo: 0, enabled: true,
  })
  visible.value = true
}

function openEdit(row) {
  Object.assign(form, {
    id: row.id,
    label: row.label,
    startHm: row.startHm,
    endHm: row.endHm,
    capacity: row.capacity,
    fulfillMode: row.fulfillMode,
    cutoffHm: row.cutoffHm,
    sortNo: row.sortNo,
    enabled: !!row.enabled,
  })
  visible.value = true
}

async function save() {
  await http.post('/api/delivery-windows/slots', {
    ...form,
    startHm: form.startHm || '',
    endHm: form.endHm || '',
    cutoffHm: form.cutoffHm || '',
    enabled: form.enabled ? 1 : 0,
  })
  ElMessage.success('已保存')
  visible.value = false
  load()
}

onMounted(load)
</script>
