<template>
  <div class="dash">
    <header class="hd">
      <h2>工作台</h2>
      <p>馆藏与借阅概览；待办可一键进入对应模块。</p>
    </header>

    <div class="stats">
      <div class="stat" v-for="s in cards" :key="s.key">
        <div class="num">{{ s.value }}</div>
        <div class="label">{{ s.label }}</div>
      </div>
    </div>

    <section class="todo card">
      <h3>待办</h3>
      <div class="todo-row">
        <span>待审核借阅 {{ data.pendingBorrow || 0 }} 单</span>
        <el-button type="primary" link @click="$router.push('/admin/borrows')">去审核</el-button>
      </div>
      <div class="todo-row">
        <span>逾期未还 {{ data.overdueBorrow || 0 }} 单 · 预估罚款 {{ data.openFineYuan || 0 }} 元</span>
        <el-button type="warning" link @click="$router.push('/admin/overdue')">去处理</el-button>
      </div>
    </section>

    <section class="card">
      <h3>规则摘要</h3>
      <p class="muted">借期 {{ data.loanDays || 14 }} 天 · 逾期 {{ data.finePerDay || 0.5 }} 元/天</p>
      <div class="links">
        <el-button @click="$router.push('/admin/books')">图书管理</el-button>
        <el-button @click="$router.push('/admin/readers')">读者管理</el-button>
        <el-button @click="$router.push('/admin/borrow-records')">借阅记录</el-button>
        <el-button @click="$router.push('/admin/notices')">公告管理</el-button>
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import http from '../../api/http'

const data = ref({})
const cards = computed(() => [
  { key: 'book', label: '图书种数', value: data.value.bookTotal ?? '—' },
  { key: 'stock', label: '在架库存', value: data.value.stockTotal ?? '—' },
  { key: 'cat', label: '分类数', value: data.value.categoryTotal ?? '—' },
  { key: 'reader', label: '读者数', value: data.value.readerTotal ?? '—' },
  { key: 'loan', label: '在借中', value: data.value.onLoan ?? '—' },
  { key: 'over', label: '逾期中', value: data.value.overdueBorrow ?? '—' },
])

async function load() {
  const res = await http.get('/api/admin/dashboard')
  data.value = res.data || {}
}

onMounted(load)
</script>

<style scoped>
.hd { margin-bottom: 18px; }
.hd h2 { margin: 0 0 6px; font-size: 20px; }
.hd p { margin: 0; color: #8a9aa6; font-size: 13px; }
.stats {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: 12px;
  margin-bottom: 16px;
}
.stat {
  background: #fff;
  border: 1px solid #e4eaf0;
  border-radius: 10px;
  padding: 14px 12px;
}
.num { font-size: 22px; font-weight: 700; letter-spacing: -0.02em; }
.label { margin-top: 4px; font-size: 12px; color: #8a9aa6; }
.card {
  background: #fff;
  border: 1px solid #e4eaf0;
  border-radius: 10px;
  padding: 16px 18px;
  margin-bottom: 12px;
}
.card h3 { margin: 0 0 12px; font-size: 15px; }
.todo-row {
  display: flex; justify-content: space-between; align-items: center;
  padding: 10px 0; border-top: 1px solid #f0f3f6; font-size: 14px;
}
.todo-row:first-of-type { border-top: none; padding-top: 0; }
.muted { margin: 0 0 12px; color: #8a9aa6; font-size: 13px; }
.links { display: flex; flex-wrap: wrap; gap: 8px; }
@media (max-width: 1100px) {
  .stats { grid-template-columns: repeat(3, 1fr); }
}
@media (max-width: 640px) {
  .stats { grid-template-columns: repeat(2, 1fr); }
}
</style>
