<template>
  <div>
    <section class="hero">
      <div>
        <h1>{{ pageTitle }}</h1>
        <p>管理收货地址；下单时优先使用默认地址。</p>
      </div>
      <div class="tools">
        <el-button @click="load">刷新</el-button>
        <el-button type="primary" @click="openCreate">新增地址</el-button>
      </div>
    </section>

    <el-table :data="list" stripe empty-text="暂无地址，请新增">
      <el-table-column label="标签" width="100">
        <template #default="{ row }">
          <el-tag size="small" effect="plain">{{ row.tag || '其它' }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="contactName" label="联系人" width="110" />
      <el-table-column prop="phone" label="手机" width="130" />
      <el-table-column prop="addressLine" label="详细地址" min-width="200" show-overflow-tooltip />
      <el-table-column label="默认" width="90">
        <template #default="{ row }">
          <el-tag v-if="row.isDefault" size="small" type="success" effect="plain">默认</el-tag>
          <span v-else class="muted">—</span>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="220" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
          <el-button
            v-if="!row.isDefault"
            link
            type="success"
            @click="setDefault(row)"
          >设为默认</el-button>
          <el-button link type="danger" @click="remove(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="visible" :title="form.id ? '编辑地址' : '新增地址'" width="480px" destroy-on-close>
      <el-form label-position="top" require-asterisk-position="right">
        <el-form-item label="标签" required>
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
        <div class="grid">
          <el-form-item label="联系人" required>
            <el-input v-model="form.contactName" maxlength="32" />
          </el-form-item>
          <el-form-item label="手机" required>
            <el-input v-model="form.phone" maxlength="20" />
          </el-form-item>
        </div>
        <el-form-item label="详细地址" required>
          <el-input v-model="form.addressLine" type="textarea" :rows="2" maxlength="200" />
        </el-form-item>
        <el-form-item>
          <el-checkbox v-model="form.isDefault">设为默认地址</el-checkbox>
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
import { menuLabel } from '../../utils/domainSchema.js'
import { addressTagOptions, normalizeAddressTag } from '../../utils/addressTags.js'

const pageTitle = computed(() => menuLabel('user', 'addresses', '收货地址'))
const tagOptions = computed(() => addressTagOptions())
const list = ref([])
const visible = ref(false)
const saving = ref(false)
const form = reactive({
  id: null,
  tag: '家',
  contactName: '',
  phone: '',
  addressLine: '',
  isDefault: false,
})

async function load() {
  const res = await http.get('/api/addresses')
  list.value = res.data || []
}

function resetForm() {
  form.id = null
  form.tag = tagOptions.value[0] || '家'
  form.contactName = ''
  form.phone = ''
  form.addressLine = ''
  form.isDefault = !list.value.length
}

function openCreate() {
  resetForm()
  visible.value = true
}

function openEdit(row) {
  form.id = row.id
  form.tag = row.tag || tagOptions.value[0] || '家'
  form.contactName = row.contactName || ''
  form.phone = row.phone || ''
  form.addressLine = row.addressLine || ''
  form.isDefault = !!row.isDefault
  visible.value = true
}

async function save() {
  if (!form.contactName.trim() || !form.phone.trim() || !form.addressLine.trim()) {
    ElMessage.warning('请填写联系人、手机与详细地址')
    return
  }
  saving.value = true
  try {
    const body = {
      contactName: form.contactName.trim(),
      phone: form.phone.trim(),
      addressLine: form.addressLine.trim(),
      tag: normalizeAddressTag(form.tag),
      isDefault: !!form.isDefault,
    }
    if (form.id) {
      await http.put(`/api/addresses/${form.id}`, body)
    } else {
      await http.post('/api/addresses', body)
    }
    ElMessage.success('已保存')
    visible.value = false
    await load()
  } finally {
    saving.value = false
  }
}

async function setDefault(row) {
  await http.put(`/api/addresses/${row.id}`, { isDefault: true })
  ElMessage.success(`已将「${row.tag || '地址'}」设为默认`)
  load()
}

async function remove(row) {
  await ElMessageBox.confirm(`删除地址「${row.tag || ''} ${row.addressLine}」？`, '删除', {
    type: 'warning',
  })
  await http.delete(`/api/addresses/${row.id}`)
  ElMessage.success('已删除')
  load()
}

onMounted(load)
</script>

<style scoped>
.hero {
  margin-bottom: 16px;
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  gap: 12px;
  align-items: flex-start;
}
.hero h1 { margin: 0 0 6px; font-size: 22px; }
.hero p { margin: 0; color: #64748b; font-size: 13px; }
.tools { display: flex; gap: 8px; }
.muted { color: #94a3b8; }
.grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0 12px;
}
@media (max-width: 520px) {
  .grid { grid-template-columns: 1fr; }
}
</style>
