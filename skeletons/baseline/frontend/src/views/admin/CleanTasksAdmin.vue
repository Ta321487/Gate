<template>
  <div>
    <p class="hint">{{ hint }}</p>
    <div class="toolbar">
      <el-button @click="load">刷新</el-button>
      <el-button v-if="venueMode && canMarkDirty" type="primary" plain @click="showMark = true">
        {{ markDirtyLabel }}
      </el-button>
    </div>

    <!-- 酒店房态清洁 -->
    <el-table v-if="!venueMode" :data="list" stripe style="margin-top: 12px">
      <el-table-column prop="roomNo" label="房号" width="100" />
      <el-table-column prop="roomTypeTitle" label="房型" width="140" />
      <el-table-column prop="status" label="状态" width="100" />
      <el-table-column label="操作" min-width="140">
        <template #default="{ row }">
          <el-button link type="primary" @click="doneHotel(row)">打扫完成</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 场馆/会议室保洁 -->
    <el-table v-else :data="list" stripe style="margin-top: 12px">
      <el-table-column prop="title" label="场地" min-width="180" />
      <el-table-column prop="cleanStatus" label="状态" width="100" />
      <el-table-column label="操作" min-width="140">
        <template #default="{ row }">
          <el-button link type="primary" @click="doneVenue(row)">打扫完成</el-button>
        </template>
      </el-table-column>
    </el-table>

    <p v-if="!list.length" class="empty">{{ emptyText }}</p>

    <el-dialog v-model="showMark" title="标为待清洁" width="420px" destroy-on-close>
      <el-select v-model="markId" filterable placeholder="选择场地" style="width: 100%">
        <el-option
          v-for="it in allItems"
          :key="it.id"
          :label="it.title"
          :value="it.id"
        />
      </el-select>
      <template #footer>
        <el-button @click="showMark = false">取消</el-button>
        <el-button type="primary" :disabled="!markId" @click="markDirty">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import http from '../../api/http'
import { getSchema, hasCap } from '../../utils/domainSchema.js'
import { currentStaffPost } from '../../utils/staffPosts.js'

const list = ref([])
const allItems = ref([])
const showMark = ref(false)
const markId = ref(null)

const venueMode = computed(() => hasCap('venue_clean') && !hasCap('housekeeping'))
const hint = computed(() => {
  if (venueMode.value) {
    return getSchema()?.labels?.cleanTasksHint || '列出待清洁的场地。打扫完成后点完成。'
  }
  return getSchema()?.labels?.cleanTasksHint || '完成打扫后点完成，房间回到空房。'
})
const emptyText = computed(() => (venueMode.value ? '暂无待清洁场地。' : '暂无待打扫房间。'))
const markDirtyLabel = computed(() => getSchema()?.labels?.venueCleanMarkDirty || '标为待清洁')
const canMarkDirty = computed(() => {
  const post = currentStaffPost()
  return post !== 'venue_cleaner' && post !== 'housekeeping'
})

async function load() {
  if (venueMode.value) {
    const res = await http.get('/api/venue-clean/tasks')
    list.value = res.data || []
  } else {
    const res = await http.get('/api/hotel-pms/clean-tasks')
    list.value = res.data || []
  }
}

async function loadAllItems() {
  if (!venueMode.value) return
  const res = await http.get('/api/venue-clean/items')
  allItems.value = res.data || []
}

async function doneHotel(row) {
  await http.post(`/api/hotel-pms/rooms/${row.id}/clean-done`)
  ElMessage.success('已标为空房')
  await load()
}

async function doneVenue(row) {
  await http.post(`/api/venue-clean/items/${row.id}/clean-done`)
  ElMessage.success('已标为已清洁')
  await load()
}

async function markDirty() {
  if (!markId.value) return
  await http.post(`/api/venue-clean/items/${markId.value}/dirty`)
  ElMessage.success('已标为待清洁')
  showMark.value = false
  markId.value = null
  await load()
}

onMounted(async () => {
  await load()
  await loadAllItems()
})
</script>

<style scoped>
.hint { color: #666; margin-bottom: 12px; }
.toolbar { display: flex; gap: 8px; }
.empty { color: #999; margin-top: 16px; }
</style>
