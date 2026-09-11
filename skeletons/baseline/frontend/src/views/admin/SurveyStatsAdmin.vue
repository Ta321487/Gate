<template>
  <div>
    <div class="toolbar">
      <h2>回收统计</h2>
      <el-select v-model="formId" placeholder="选择问卷" style="width: 240px" @change="load">
        <el-option v-for="f in forms" :key="f.id" :label="f.title" :value="f.id" />
      </el-select>
    </div>
    <div v-if="formId" class="recycle card block">
      <div class="recycle-hd">
        <span>已回收 {{ responses.length }} 份</span>
        <span class="muted">目标 {{ recycleGoal }} 份</span>
      </div>
      <el-progress :percentage="recyclePct" :stroke-width="10" />
    </div>
    <el-table :data="responses" stripe class="mb">
      <el-table-column prop="username" label="填写人" width="140" />
      <el-table-column prop="submittedAt" label="提交时间" />
    </el-table>
    <article v-for="s in stats" :key="s.questionId" class="card block">
      <h3>{{ s.stem }}</h3>
      <p v-if="s.type === 'text'" class="muted">有效填空 {{ s.filledCount }} 份</p>
      <ul v-else>
        <li v-for="o in s.options || []" :key="o.key">{{ o.key }}. {{ o.label }} — {{ o.count }}</li>
      </ul>
    </article>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import http from '../../api/http'

const forms = ref([])
const formId = ref(null)
const responses = ref([])
const stats = ref([])

const recycleGoal = computed(() => {
  const f = forms.value.find((x) => x.id === formId.value)
  const n = Number(f?.targetCount || f?.goalCount || f?.stock || 0)
  return Number.isFinite(n) && n > 0 ? n : 20
})
const recyclePct = computed(() =>
  Math.min(100, Math.round((responses.value.length / recycleGoal.value) * 100)),
)

async function loadForms() {
  const res = await http.get('/api/survey/forms')
  forms.value = res.data?.data || res.data || []
  if (forms.value.length && !formId.value) {
    formId.value = forms.value[0].id
    await load()
  }
}

async function load() {
  if (!formId.value) return
  const r = await http.get(`/api/survey/admin/forms/${formId.value}/responses`, {
    params: { page: 1, size: 50 },
  })
  responses.value = (r.data?.data || r.data || {}).list || []
  const s = await http.get(`/api/survey/admin/forms/${formId.value}/stats`)
  stats.value = s.data?.data || s.data || []
}

onMounted(loadForms)
</script>

<style scoped>
.toolbar { display: flex; gap: 0.75rem; align-items: center; margin-bottom: 1rem; }
.mb { margin-bottom: 1rem; }
.block { padding: 1rem; margin-bottom: 0.75rem; }
.muted { color: var(--el-text-color-secondary); }
.recycle-hd {
  display: flex;
  justify-content: space-between;
  margin-bottom: 8px;
  font-size: 14px;
}
</style>
