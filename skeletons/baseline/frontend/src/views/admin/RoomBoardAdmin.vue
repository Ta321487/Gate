<template>
  <div>
    <p class="hint">{{ hint }}</p>
    <el-button @click="load">刷新</el-button>
    <div class="board">
      <div
        v-for="r in list"
        :key="r.id"
        class="cell"
        :class="statusClass(r.status)"
        @click="open(r)"
      >
        <div class="no">{{ r.roomNo }}</div>
        <div class="type">{{ r.roomTypeTitle || '房型' }}</div>
        <div class="st">{{ r.status }}</div>
      </div>
    </div>
    <p v-if="!list.length" class="empty">暂无房间。</p>
    <el-dialog v-model="visible" title="改房态" width="420px">
      <el-form label-width="88px">
        <el-form-item label="房号">{{ form.roomNo }}</el-form-item>
        <el-form-item label="状态">
          <el-select v-model="form.status" style="width: 100%">
            <el-option v-for="s in statuses" :key="s" :label="s" :value="s" />
          </el-select>
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="form.note" maxlength="100" />
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
import { getSchema } from '../../utils/domainSchema.js'

const list = ref([])
const visible = ref(false)
const statuses = ['空房', '已订', '入住中', '待打扫', '维修']
const form = reactive({ id: null, roomNo: '', status: '空房', note: '' })
const hint = computed(() => getSchema()?.labels?.roomBoardHint || '按房间查看状态，点格子可改。')

function statusClass(st) {
  const map = {
    空房: 'vacant',
    已订: 'booked',
    入住中: 'staying',
    待打扫: 'dirty',
    维修: 'repair',
  }
  return map[st] || ''
}

async function load() {
  const res = await http.get('/api/hotel-pms/rooms')
  list.value = res.data || []
}

function open(row) {
  Object.assign(form, {
    id: row.id,
    roomNo: row.roomNo,
    status: row.status,
    note: row.note || '',
  })
  visible.value = true
}

async function save() {
  await http.post(`/api/hotel-pms/rooms/${form.id}/status`, {
    status: form.status,
    note: form.note,
  })
  ElMessage.success('已更新')
  visible.value = false
  await load()
}

onMounted(load)
</script>

<style scoped>
.hint { color: #666; margin-bottom: 12px; }
.board {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(110px, 1fr));
  gap: 12px;
  margin-top: 16px;
}
.cell {
  border-radius: 8px;
  padding: 12px;
  cursor: pointer;
  color: #fff;
  min-height: 88px;
}
.cell.vacant { background: #67c23a; }
.cell.booked { background: #409eff; }
.cell.staying { background: #e6a23c; }
.cell.dirty { background: #909399; }
.cell.repair { background: #f56c6c; }
.no { font-size: 18px; font-weight: 600; }
.type { font-size: 12px; opacity: 0.9; margin-top: 4px; }
.st { margin-top: 8px; font-size: 13px; }
.empty { color: #999; margin-top: 16px; }
</style>
