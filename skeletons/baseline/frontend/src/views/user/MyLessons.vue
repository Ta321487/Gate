<template>
  <div>
    <p class="hint">选择课时包购买。约课成功扣 1 节，未开始前取消退回。</p>
    <p class="remain">剩余 {{ remain }} 节<span v-if="expireAt">，有效期至 {{ expireAt }}</span></p>
    <el-form label-position="top" class="form">
      <el-form-item label="课时包" required>
        <el-select v-model="packId" placeholder="请选择" style="width: 280px">
          <el-option
            v-for="p in packs"
            :key="p.id"
            :label="`${p.name} · ${p.sessions}节 · ${p.priceYuan}元`"
            :value="p.id"
          />
        </el-select>
        <p v-if="!packs.length" class="empty">暂无可选课时包。</p>
      </el-form-item>
      <el-button type="primary" @click="buy">购买</el-button>
    </el-form>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import http from '../../api/http'

const packs = ref([])
const packId = ref(null)
const remain = ref(0)
const expireAt = ref('')

async function load() {
  const packRes = await http.get('/api/lessons/packs')
  packs.value = packRes.data || []
  const mine = await http.get('/api/lessons/mine')
  remain.value = mine.data?.remainSessions ?? 0
  expireAt.value = mine.data?.expireAt || ''
}

async function buy() {
  if (!packId.value) {
    ElMessage.warning('请选择课时包')
    return
  }
  await http.post('/api/lessons/buy', { packId: packId.value })
  ElMessage.success('已购买')
  packId.value = null
  await load()
}

onMounted(load)
</script>

<style scoped>
.hint, .empty { color: var(--el-text-color-secondary); margin: 0 0 12px; }
.remain { margin: 0 0 12px; }
.form { max-width: 480px; }
</style>
