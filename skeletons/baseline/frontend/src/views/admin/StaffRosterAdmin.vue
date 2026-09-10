<template>
  <div>
    <p class="lead">{{ pageLead }}</p>
    <div class="tools">
      <el-input
        v-model="filters.username"
        clearable
        placeholder="员工用户名"
        style="width: 160px"
        @keyup.enter="reload"
      />
      <el-date-picker
        v-model="filters.from"
        type="date"
        value-format="YYYY-MM-DD"
        placeholder="起"
        style="width: 150px"
      />
      <el-date-picker
        v-model="filters.to"
        type="date"
        value-format="YYYY-MM-DD"
        placeholder="止"
        style="width: 150px"
      />
      <el-button type="primary" @click="reload">查询</el-button>
      <el-button type="success" @click="openCreate">新增排班</el-button>
    </div>
    <div class="table-scroll">
      <el-table :data="list" stripe>
        <el-table-column prop="username" label="员工" width="140" />
        <el-table-column prop="workDate" label="日期" width="120" />
        <el-table-column prop="shiftLabel" label="班次" width="120" />
        <el-table-column prop="note" label="备注" min-width="160" show-overflow-tooltip />
        <el-table-column prop="createdAt" label="创建时间" width="170" />
        <el-table-column label="操作" width="140" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
            <el-button link type="danger" @click="remove(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>
    <div class="pager">
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

    <el-dialog v-model="visible" :title="form.id ? '编辑排班' : '新增排班'" width="480px" destroy-on-close>
      <el-form label-position="top">
        <el-form-item v-if="!form.id" label="员工用户名" required>
          <el-select
            v-model="form.username"
            filterable
            allow-create
            default-first-option
            placeholder="选择或输入子管用户名"
            style="width: 100%"
          >
            <el-option
              v-for="t in staffOptions"
              :key="t.username"
              :label="`${t.nickname || t.username}（${t.username}）`"
              :value="t.username"
            />
          </el-select>
        </el-form-item>
        <el-form-item v-else label="员工">
          <el-input :model-value="form.username" disabled />
        </el-form-item>
        <el-form-item v-if="!form.id" label="日期" required>
          <el-date-picker
            v-model="form.workDate"
            type="date"
            value-format="YYYY-MM-DD"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item v-else label="日期">
          <el-input :model-value="form.workDate" disabled />
        </el-form-item>
        <el-form-item label="班次" required>
          <el-input v-model="form.shiftLabel" maxlength="64" placeholder="如：全天 / 上午 / 晚班" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="form.note" maxlength="256" type="textarea" :rows="2" />
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
/** 周排班：总管按员工+日期维护班次（E-09） */
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import http from '../../api/http'
import { getSchema } from '../../utils/domainSchema.js'

const labels = computed(() => getSchema()?.labels || {})
const pageLead = computed(
  () =>
    labels.value.staffRosterPageLead ||
    '按员工与日期维护班次；预约页可查看当日当班人员。',
)

const list = ref([])
const page = ref(1)
const size = ref(20)
const total = ref(0)
const filters = reactive({ username: '', from: '', to: '' })
const staffOptions = ref([])
const visible = ref(false)
const saving = ref(false)
const form = reactive({
  id: 0,
  username: '',
  workDate: '',
  shiftLabel: '全天',
  note: '',
})

function reload() {
  page.value = 1
  return load()
}

async function load() {
  const res = await http.get('/api/admin/staff-roster', {
    params: {
      page: page.value,
      size: size.value,
      username: filters.username || undefined,
      from: filters.from || undefined,
      to: filters.to || undefined,
    },
  })
  list.value = res.data?.list || []
  total.value = res.data?.total || 0
}

async function loadStaff() {
  try {
    const res = await http.get('/api/tickets/dispatch-targets')
    staffOptions.value = Array.isArray(res.data) ? res.data : []
  } catch {
    staffOptions.value = []
  }
}

function openCreate() {
  form.id = 0
  form.username = ''
  form.workDate = ''
  form.shiftLabel = '全天'
  form.note = ''
  visible.value = true
}

function openEdit(row) {
  form.id = row.id
  form.username = row.username
  form.workDate = row.workDate
  form.shiftLabel = row.shiftLabel || '全天'
  form.note = row.note || ''
  visible.value = true
}

async function save() {
  if (!form.id) {
    if (!form.username.trim() || !form.workDate) {
      ElMessage.warning('请选择员工与日期')
      return
    }
  }
  if (!form.shiftLabel.trim()) {
    ElMessage.warning('请填写班次')
    return
  }
  saving.value = true
  try {
    if (form.id) {
      await http.put(`/api/admin/staff-roster/${form.id}`, {
        shiftLabel: form.shiftLabel.trim(),
        note: form.note.trim(),
      })
    } else {
      await http.post('/api/admin/staff-roster', {
        username: form.username.trim(),
        workDate: form.workDate,
        shiftLabel: form.shiftLabel.trim(),
        note: form.note.trim(),
      })
    }
    ElMessage.success('已保存')
    visible.value = false
    await load()
  } catch (e) {
    ElMessage.error(e?.response?.data?.message || e?.message || '保存失败')
  } finally {
    saving.value = false
  }
}

async function remove(row) {
  try {
    await ElMessageBox.confirm(`确认删除 ${row.username} 在 ${row.workDate} 的排班？`, '删除排班')
  } catch {
    return
  }
  try {
    await http.delete(`/api/admin/staff-roster/${row.id}`)
    ElMessage.success('已删除')
    await load()
  } catch (e) {
    ElMessage.error(e?.response?.data?.message || e?.message || '删除失败')
  }
}

onMounted(async () => {
  await Promise.all([load(), loadStaff()])
})
</script>

<style scoped>
.lead {
  color: var(--el-text-color-secondary);
  margin: 0 0 12px;
}
.tools {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 12px;
  align-items: center;
}
.pager {
  margin-top: 12px;
  display: flex;
  justify-content: flex-end;
}
</style>
